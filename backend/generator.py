# generator.py
# Generates a realistic 6-month synthetic bank statement CSV.
# Plants 3 verifiable patterns for demo validation:
#   1. Bounce cluster in month 4 (April 2024)
#   2. Circular flow in month 5 (May 2024) — account ACCT9988776655
#   3. Regular EMI every month on the 5th

import pandas as pd
import numpy as np
from datetime import date, timedelta
import random
import uuid
import os


def generate_statement(months: int = 6, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)
    np.random.seed(seed)
    rows = []

    months_list = [
        date(2024, 1, 1),
        date(2024, 2, 1),
        date(2024, 3, 1),
        date(2024, 4, 1),
        date(2024, 5, 1),
        date(2024, 6, 1),
    ]

    for m_idx, base in enumerate(months_list[:months]):

        # ── Salary credit on 1st of month ──────────────────────────────
        rows.append({
            "date": base.strftime("%Y-%m-%d"),
            "description": "NEFT CR EMPLOYER SALARY MONIL TECH SOLUTIONS",
            "amount": 85000.0,
            "balance": 0.0,
        })

        # ── Business inflows (3–4 per month) ───────────────────────────
        for _ in range(random.randint(3, 4)):
            d = base + timedelta(days=random.randint(2, 25))
            client_id = uuid.uuid4().hex[:6].upper()
            rows.append({
                "date": d.strftime("%Y-%m-%d"),
                "description": f"UPI CR CLIENT PAYMENT INV{client_id}",
                "amount": float(random.randint(15000, 45000)),
                "balance": 0.0,
            })

        # ── EMI on 5th of every month ───────────────────────────────────
        emi_date = base + timedelta(days=4)
        rows.append({
            "date": emi_date.strftime("%Y-%m-%d"),
            "description": "NACH DR HDFC HOMELOAN EMI A/C 00112233",
            "amount": -22000.0,
            "balance": 0.0,
        })

        # ── Regular expenses (8–12 per month) ──────────────────────────
        expense_descs = [
            "UPI DR SWIGGY ORDER",
            "POS DR DMART HYPERMARKET",
            "UPI DR PHONEPE TRANSFER",
            "ATM WITHDRAWAL HDFC BANK",
            "UTILITY BILL PAYMENT MSEDCL",
            "UPI DR ZOMATO FOOD ORDER",
            "UPI DR PAYTM MERCHANT",
            "DEBIT CARD PURCHASE PETROL",
        ]
        for _ in range(random.randint(10, 15)):
            d = base + timedelta(days=random.randint(1, 28))
            rows.append({
                "date": d.strftime("%Y-%m-%d"),
                "description": random.choice(expense_descs),
                "amount": float(-random.randint(500, 8000)),
                "balance": 0.0,
            })

        # ── PLANTED PATTERN 1: Bounce cluster in month 4 (April) ───────
        if m_idx == 3:
            rows.append({
                "date": (base + timedelta(days=5)).strftime("%Y-%m-%d"),
                "description": "CHQ RETURN INSUFFICIENT FUNDS CHQ NO 004512",
                "amount": 0.0,
                "balance": 0.0,
            })
            rows.append({
                "date": (base + timedelta(days=7)).strftime("%Y-%m-%d"),
                "description": "NACH RETURN NACH DR RETURN INSUFFICIENT BALANCE",
                "amount": 0.0,
                "balance": 0.0,
            })

        # ── PLANTED PATTERN 2: Circular flow in month 5 (May) ──────────
        if m_idx == 4:
            partner_acct = "ACCT9988776655"
            rows.append({
                "date": (base + timedelta(days=8)).strftime("%Y-%m-%d"),
                "description": f"NEFT DR {partner_acct} FUND TRANSFER",
                "amount": -50000.0,
                "balance": 0.0,
            })
            rows.append({
                "date": (base + timedelta(days=10)).strftime("%Y-%m-%d"),
                "description": f"NEFT CR {partner_acct} RETURN TRANSFER",
                "amount": 50000.0,
                "balance": 0.0,
            })
            rows.append({
                "date": (base + timedelta(days=12)).strftime("%Y-%m-%d"),
                "description": f"NEFT DR {partner_acct} FUND TRANSFER",
                "amount": -50000.0,
                "balance": 0.0,
            })

    # ── Sort by date and compute running balance ────────────────────────
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    running_balance = 50000.0
    for i, row in df.iterrows():
        running_balance += row["amount"]
        df.at[i, "balance"] = round(running_balance, 2)

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["row_id"] = df.index

    return df


if __name__ == "__main__":
    df = generate_statement()
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_statement.csv")
    out_path = os.path.normpath(out_path)
    df.to_csv(out_path, index=False)

    bounces = df[df["description"].str.contains("CHQ RETURN|NACH RETURN", case=False, na=False)]
    circular = df[df["description"].str.contains("ACCT9988776655", na=False)]
    emis = df[df["description"].str.contains("HOMELOAN EMI", case=False, na=False)]

    print(f"Generated {len(df)} rows -> {out_path}")
    print(f"  Bounce rows planted    : {len(bounces)} (expected 2, in April 2024)")
    print(f"  Circular flow rows     : {len(circular)} (expected 3, in May 2024)")
    print(f"  EMI rows               : {len(emis)} (expected 6, one per month)")
    print()
    print("CHECKPOINT: All 3 values should match expected counts.")
    print("If any mismatch -> fix generator.py before running classifier.")
