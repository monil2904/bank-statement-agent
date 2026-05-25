# classifier.py
# Sends bank statement transactions to Claude in batches of 20.
# Returns category, confidence, and reason for each row.
# DO NOT add metrics or anomaly logic here — single responsibility only.

import json
import math
import os
import pandas as pd
import requests
from dotenv import load_dotenv

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
        "generationConfig": {
            "responseMimeType": "application/json"
        }
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

# ── System prompt ──────────────────────────────────────────────────────────────
# Copied exactly from MASTER_PROMPT.md (block between ===START=== and ===END===)
# Do not edit the structure, category names, or JSON schema.
SYSTEM_PROMPT = """You are a bank statement transaction classifier for an Indian MSME lending company.

Your job: classify each transaction in the batch provided, and return ONLY a valid JSON array — no prose, no markdown, no explanation outside the JSON.

CLASSIFICATION CATEGORIES — use exactly these strings, no others:
- "salary"              : Regular salary or wage credit from employer. Keywords: SALARY, NEFT CR EMPLOYER, PAYROLL
- "business_inflow"     : Business payment received from clients or customers. Keywords: UPI CR, NEFT CR CLIENT, PAYMENT RECEIVED
- "emi_payment"         : Loan EMI debit — auto-debit, NACH, standing instruction. Keywords: NACH DR, EMI, LOAN, HDFC HOMELOAN, SBI LOAN
- "bounce"              : Cheque return, NACH return, insufficient funds. Keywords: RETURN, INSUFFICIENT FUNDS, BOUNCE, NACH RETURN, CHQ RETURN. Amount may be 0.
- "circular_transfer"   : Money sent out and returned from the SAME account within 15 days — suspicious round-tripping. Look for same account number appearing as both debit and credit.
- "gambling_crypto"     : Gambling or cryptocurrency transactions. Keywords: BET365, DREAM11, WAZIRX, COINDCX, BETWAY, MPL
- "regular_expense"     : Day-to-day personal or business spending. Keywords: SWIGGY, ZOMATO, DMART, ATM, UTILITY, PHONEPE, PAYTM, UPI DR
- "other"               : Does not clearly fit any category above. Use this when uncertain.

RESPONSE FORMAT — return ONLY this JSON array. No text before or after it. No markdown fences.
[
  {
    "row_id": <integer — must match the row_id from input exactly>,
    "category": "<one of the 8 category strings above>",
    "confidence": <float between 0.0 and 1.0>,
    "reason": "<one sentence maximum — why you chose this category>"
  }
]

RULES — follow all of these:
1. Every input row must produce exactly one output object. Never skip a row. Never add extra rows.
2. confidence = 1.0 means certain. confidence < 0.6 means the transaction is ambiguous — flag it.
3. For "bounce": the amount field may be 0 or missing. Rely entirely on description keywords.
4. For "circular_transfer": within this batch, check if any account identifier (long alphanumeric string) appears in both a debit and a credit description.
5. For "other": always assign confidence <= 0.5 to signal human review is needed.
6. Do not invent categories. Do not use synonyms for category names. Use the exact strings listed above.
7. Do not include any text, explanation, or preamble before or after the JSON array.
8. If the input contains non-transaction metadata rows (headers, blank rows), assign category "other" with confidence 0.1."""

# ── Constants ──────────────────────────────────────────────────────────────────
BATCH_SIZE = 20
MODEL = "gemini-2.5-flash"
MAX_TOKENS = 2000
VALID_CATEGORIES = {
    "salary", "business_inflow", "emi_payment", "bounce",
    "circular_transfer", "gambling_crypto", "regular_expense", "other"
}


def _clean_json_response(raw: str) -> str:
    """Strip markdown fences if the model wraps output in ```json ... ```."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first line (```json or ```) and last line (```)
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return raw.strip()


def _safe_parse(raw: str, batch: list[dict]) -> list[dict]:
    """Parse JSON response. On failure, return all rows as 'other' with low confidence."""
    try:
        cleaned = _clean_json_response(raw)
        result = json.loads(cleaned)
        # Validate structure
        assert isinstance(result, list), "Response must be a JSON array"
        return result
    except Exception as e:
        print(f"  WARNING: JSON parse failed — {e}. Marking batch as 'other'.")
        print(f"  Raw response (first 200 chars): {raw[:200]}")
        return [
            {"row_id": r["row_id"], "category": "other", "confidence": 0.2,
             "reason": "Classifier parse error — flagged for human review"}
            for r in batch
        ]


def _validate_results(results: list[dict], batch: list[dict]) -> list[dict]:
    """Ensure every row in batch has a valid result. Fill gaps if model skipped rows."""
    result_map = {r["row_id"]: r for r in results}
    validated = []
    for row in batch:
        rid = row["row_id"]
        if rid in result_map:
            r = result_map[rid]
            # Normalise category — default to "other" if invalid
            if r.get("category") not in VALID_CATEGORIES:
                r["category"] = "other"
                r["confidence"] = 0.3
            validated.append(r)
        else:
            # Model skipped this row — fill with safe default
            validated.append({
                "row_id": rid, "category": "other",
                "confidence": 0.2, "reason": "Row not returned by classifier"
            })
    return validated


def _local_classify_batch(rows: list[dict]) -> list[dict]:
    """Keyword-based fallback when API is unavailable. Uses rules from SYSTEM_PROMPT."""
    import re

    def _has_keyword(text: str, keywords: list[str]) -> bool:
        """Check if any keyword appears in text. Short keywords (≤3 chars) use word boundaries."""
        for kw in keywords:
            if len(kw) <= 3:
                pat = r'\b' + re.escape(kw) + r'\b'
                if re.search(pat, text):
                    return True
            else:
                if kw in text:
                    return True
        return False

    results = []
    # First pass: classify each row individually
    for r in rows:
        desc = str(r.get("description", "")).upper()
        amt = float(r.get("amount", 0))
        category = "other"
        confidence = 0.5
        reason = "Local fallback classification — API quota exhausted"

        if _has_keyword(desc, ["BET365", "DREAM11", "WAZIRX", "COINDCX", "BETWAY", "MPL"]):
            category = "gambling_crypto"
            confidence = 0.9
        elif _has_keyword(desc, ["CHQ RETURN", "NACH RETURN", "INSUFFICIENT FUNDS", "BOUNCE"]):
            category = "bounce"
            confidence = 0.95
        elif _has_keyword(desc, ["NACH DR", "EMI", "LOAN", "HOMELOAN", "SBI LOAN"]):
            category = "emi_payment"
            confidence = 0.9
        elif _has_keyword(desc, ["SALARY", "NEFT CR EMPLOYER", "PAYROLL"]):
            category = "salary"
            confidence = 0.95
        elif _has_keyword(desc, ["UPI CR", "NEFT CR CLIENT", "PAYMENT RECEIVED"]):
            category = "business_inflow"
            confidence = 0.85
        elif _has_keyword(desc, ["SWIGGY", "ZOMATO", "DMART", "ATM", "UTILITY", "PHONEPE", "PAYTM", "UPI DR", "POS DR", "DEBIT CARD"]):
            category = "regular_expense"
            confidence = 0.85
        else:
            category = "other"
            confidence = 0.5
            reason = "Local fallback — no clear keyword match"

        results.append({
            "row_id": r["row_id"],
            "category": category,
            "confidence": confidence,
            "reason": reason,
        })

    # Second pass: detect circular transfers within this batch
    account_map: dict[str, list[dict]] = {}
    for r in rows:
        desc = str(r.get("description", ""))
        tokens = desc.upper().split()
        accts = [t for t in tokens if re.match(r'^[A-Z0-9]{10,16}$', t)]
        for acct in accts:
            if acct not in account_map:
                account_map[acct] = []
            account_map[acct].append({
                "row_id": r["row_id"],
                "amount": float(r.get("amount", 0)),
            })

    for acct, appearances in account_map.items():
        debits = [a for a in appearances if a["amount"] < 0]
        credits = [a for a in appearances if a["amount"] > 0]
        if debits and credits:
            for res in results:
                if res["row_id"] in {a["row_id"] for a in debits + credits}:
                    res["category"] = "circular_transfer"
                    res["confidence"] = 0.9
                    res["reason"] = f"Local fallback — same account {acct} appears as both debit and credit"

    return results


def classify_batch(rows: list[dict], batch_num: int = 0, total_batches: int = 0) -> list[dict]:
    """Send one batch of ≤20 rows to Gemini. Return validated classified list."""
    user_content = json.dumps(
        [{"row_id": r["row_id"], "date": r["date"],
          "description": r["description"], "amount": r["amount"]}
         for r in rows],
        indent=2
    )

    label = f"batch {batch_num}/{total_batches}" if total_batches else "batch"
    print(f"  Classifying {label} ({len(rows)} rows)...")

    try:
        raw = _call_gemini(user_content, system_instruction=SYSTEM_PROMPT)
    except Exception as e:
        print(f"  Gemini call failed: {e}. Using local keyword fallback.")
        return _validate_results(_local_classify_batch(rows), rows)

    parsed = _safe_parse(raw, rows)
    return _validate_results(parsed, rows)


def classify_statement(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify all transactions in a DataFrame.
    Adds 3 columns: category, confidence, reason.
    Returns the same DataFrame with those columns added.
    """
    df = df.copy()
    if "row_id" not in df.columns:
        df["row_id"] = df.index

    records = df.to_dict("records")
    total_batches = math.ceil(len(records) / BATCH_SIZE)

    print(f"Classifying {len(records)} transactions in {total_batches} batches...")
    all_results = []

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i: i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        results = classify_batch(batch, batch_num, total_batches)
        all_results.extend(results)

    result_map = {r["row_id"]: r for r in all_results}
    df["category"] = df["row_id"].map(lambda x: result_map.get(x, {}).get("category", "other"))
    df["confidence"] = df["row_id"].map(lambda x: result_map.get(x, {}).get("confidence", 0.3))
    df["reason"] = df["row_id"].map(lambda x: result_map.get(x, {}).get("reason", ""))

    low_conf = (df["confidence"] < 0.6).sum()
    print(f"Classification complete. Low-confidence rows: {low_conf}")
    return df
