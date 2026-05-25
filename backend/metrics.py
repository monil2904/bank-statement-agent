# metrics.py
# Pure deterministic metrics engine. No LLM calls. No anthropic import.
# Input: classified DataFrame (output of classifier.py)
# Output: MetricsOutput with 6 lending metrics

import pandas as pd
from models import MetricsOutput


def compute_metrics(df: pd.DataFrame) -> MetricsOutput:
    """
    Compute 4 key underwriting metrics from a classified bank statement DataFrame.

    Required columns: date, amount, balance, category, confidence
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")

    # ── 1. ABB — Average Bank Balance ─────────────────────────────────────────
    # Mean of all closing balances in the statement
    abb = round(float(df["balance"].mean()), 2)

    # ── 2. Monthly BTO — Bank Turnover ────────────────────────────────────────
    # Total inflow (positive amounts) per calendar month
    inflow_df = df[df["amount"] > 0].copy()
    monthly_bto_series = inflow_df.groupby("month")["amount"].sum()
    monthly_bto_list = [round(float(v), 2) for v in monthly_bto_series.values]
    avg_bto = round(float(monthly_bto_series.mean()), 2) if len(monthly_bto_series) > 0 else 0.0

    # ── 3. Bounce Ratio ───────────────────────────────────────────────────────
    # bounce rows / total debit rows
    # Note: bounce rows have amount = 0 in synthetic data; count by category
    debit_rows = df[(df["amount"] < 0) | (df["category"] == "bounce")]
    bounce_rows = df[df["category"] == "bounce"]
    bounce_ratio = round(
        len(bounce_rows) / max(len(debit_rows), 1), 4
    )

    # ── 4. FOIR approximation — Fixed Obligation to Income Ratio ──────────────
    # EMI outflow (absolute) / total inflow
    emi_df = df[df["category"] == "emi_payment"]
    emi_outflow = abs(float(emi_df["amount"].sum()))
    total_inflow = float(inflow_df["amount"].sum())
    foir_approx = round(emi_outflow / max(total_inflow, 1.0), 4)

    # ── 5. Low confidence count ────────────────────────────────────────────────
    low_confidence_count = int((df["confidence"] < 0.6).sum())

    return MetricsOutput(
        abb=abb,
        monthly_bto=monthly_bto_list,
        avg_bto=avg_bto,
        bounce_ratio=bounce_ratio,
        foir_approx=foir_approx,
        low_confidence_count=low_confidence_count,
    )
