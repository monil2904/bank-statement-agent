# anomaly.py
# Two-layer anomaly detection:
#   Layer 1 — Rule-based: fast, cheap, deterministic pattern matching
#   Layer 2 — LLM: called ONLY when a rule fires, to generate plain-English explanation
#
# IMPORTANT: Never call LLM speculatively. Rules must confirm a pattern first.

import re
import json
import os
import pandas as pd
import requests
from dotenv import load_dotenv
from models import AnomalyOutput

load_dotenv()

import time

def _call_gemini(prompt: str, system_instruction: str = None) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    contents = {
        "role": "user",
        "parts": [{"text": prompt}]
    }
    payload = {
        "contents": [contents],
        "generationConfig": {}
    }
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
    
    max_retries = 1
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif response.status_code in (429, 503):
                print(f"  Got status {response.status_code} on attempt {attempt+1}/{max_retries}. Using local fallback.")
                raise RuntimeError(f"Gemini API rate limited ({response.status_code})")
            else:
                raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"  Request exception on attempt {attempt+1}/{max_retries}: {e}. Using local fallback.")
            raise RuntimeError(f"Gemini API request failed: {e}")
            
    raise RuntimeError("Exceeded maximum retries for Gemini API due to rate limits or connection issues.")

MODEL = "gemini-2.5-flash"


def _explain_anomaly(rows_data: list[dict], anomaly_type: str) -> str:
    """
    Ask Gemini to explain a confirmed anomaly in plain English for an underwriter.
    Called only after a rule has already confirmed the pattern exists.
    """
    type_descriptions = {
        "circular_flow": "suspicious circular fund transfer (money sent out and returned from the same account within 15 days)",
        "bounce_cluster": "bounce cluster (multiple payment failures in the same month)",
    }
    type_desc = type_descriptions.get(anomaly_type, anomaly_type)

    prompt = (
        f"You are a credit analyst writing a note for an underwriter.\n"
        f"Explain this {type_desc} in exactly 2 sentences.\n"
        f"Be specific: mention the amounts, dates, and account/party involved.\n"
        f"Do not start with 'I', do not use preamble, go straight to the observation.\n\n"
        f"Transactions involved:\n{json.dumps(rows_data, indent=2)}"
    )

    try:
        explanation = _call_gemini(prompt)
    except Exception as e:
        print(f"  Gemini call failed in anomaly: {e}. Using local fallback explanation.")
        # Build a deterministic explanation from the row data
        amounts = [r.get("amount", 0) for r in rows_data]
        dates = [r.get("date", "unknown") for r in rows_data]
        descs = [r.get("description", "") for r in rows_data]
        if anomaly_type == "circular_flow":
            explanation = (
                f"Suspicious circular fund flow detected between {dates[0]} and {dates[-1]}. "
                f"Amounts involved: {', '.join(f'Rs.{abs(a):,.0f}' for a in amounts if a != 0)}. "
                f"Same account identifier appears in both debit and credit descriptions, indicating possible round-tripping."
            )
        elif anomaly_type == "bounce_cluster":
            explanation = (
                f"Multiple payment failures ({len(rows_data)} bounces) detected in the same month. "
                f"Dates: {', '.join(dates)}. "
                f"This pattern indicates poor payment discipline and potential liquidity stress."
            )
        else:
            explanation = f"Anomaly of type {type_desc} detected on the specified transaction rows."

    return explanation.strip()


def _extract_account_ids(description: str) -> list[str]:
    """
    Extract account-like identifiers from a transaction description.
    Looks for alphanumeric strings of length 10–16 (common format for account numbers).
    """
    tokens = description.upper().split()
    return [t for t in tokens if re.match(r'^[A-Z0-9]{10,16}$', t)]


def detect_circular_flows(df: pd.DataFrame) -> list[AnomalyOutput]:
    """
    Rule: same account identifier appears in both a debit and a credit
    description within a 15-day window.
    Severity: HARD
    """
    anomalies = []
    df = df.copy()
    df["_date"] = pd.to_datetime(df["date"])

    # Build maps: account_id → list of (row_index, direction, date)
    account_appearances: dict[str, list[dict]] = {}

    for idx, row in df.iterrows():
        acct_ids = _extract_account_ids(str(row["description"]))
        direction = "credit" if row["amount"] > 0 else "debit"
        for acct in acct_ids:
            if acct not in account_appearances:
                account_appearances[acct] = []
            account_appearances[acct].append({
                "row_id": idx,
                "direction": direction,
                "date": row["_date"],
                "description": row["description"],
                "amount": row["amount"],
            })

    # Check for accounts with both debit and credit within 15 days
    for acct, appearances in account_appearances.items():
        debits = [a for a in appearances if a["direction"] == "debit"]
        credits = [a for a in appearances if a["direction"] == "credit"]

        if not debits or not credits:
            continue

        for d in debits:
            for c in credits:
                delta_days = abs((d["date"] - c["date"]).days)
                if delta_days <= 15:
                    print(f"  Circular flow detected: account {acct}, "
                          f"delta {delta_days} days")
                    affected = list({d["row_id"], c["row_id"]})
                    rows_data = [
                        {"date": str(d["date"].date()), "description": d["description"], "amount": d["amount"]},
                        {"date": str(c["date"].date()), "description": c["description"], "amount": c["amount"]},
                    ]
                    explanation = _explain_anomaly(rows_data, "circular_flow")
                    anomalies.append(AnomalyOutput(
                        anomaly_type="circular_flow",
                        severity="hard",
                        description=explanation,
                        affected_rows=affected,
                    ))
                    return anomalies  # One confirmed circular flow is sufficient for MVP

    return anomalies


def detect_bounce_clusters(df: pd.DataFrame) -> list[AnomalyOutput]:
    """
    Rule: 2 or more bounce-category rows in the same calendar month.
    Severity: HARD
    """
    anomalies = []
    df = df.copy()
    df["_month"] = pd.to_datetime(df["date"]).dt.to_period("M")

    bounce_df = df[df["category"] == "bounce"]
    if bounce_df.empty:
        return anomalies

    bounce_by_month = bounce_df.groupby("_month")

    for month, group in bounce_by_month:
        if len(group) >= 2:
            print(f"  Bounce cluster detected: {len(group)} bounces in {month}")
            rows_data = group[["date", "description", "amount"]].to_dict("records")
            explanation = _explain_anomaly(rows_data, "bounce_cluster")
            anomalies.append(AnomalyOutput(
                anomaly_type="bounce_cluster",
                severity="hard",
                description=explanation,
                affected_rows=group.index.tolist(),
            ))

    return anomalies


def run_all_anomaly_checks(df: pd.DataFrame) -> list[AnomalyOutput]:
    """
    Run all anomaly checks in sequence.
    Returns combined list of all detected anomalies.
    """
    print("Running anomaly checks...")
    results: list[AnomalyOutput] = []

    results.extend(detect_circular_flows(df))
    results.extend(detect_bounce_clusters(df))

    print(f"Anomaly checks complete. Found: {[a.anomaly_type for a in results]}")
    return results
