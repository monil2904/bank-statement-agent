# models.py
# All Pydantic schemas live here. Do not define inline schemas in other files.

from pydantic import BaseModel
from typing import Optional


class Transaction(BaseModel):
    row_id: int
    date: str
    description: str
    amount: float
    balance: float


class ClassifiedTransaction(Transaction):
    category: str
    confidence: float
    reason: str


class MetricsOutput(BaseModel):
    abb: float                    # Average Bank Balance — mean of all closing balances
    monthly_bto: list[float]      # Bank Turnover per month — total inflow per calendar month
    avg_bto: float                # Average monthly BTO
    bounce_ratio: float           # bounce rows / total debit rows
    foir_approx: float            # EMI outflow / total inflow — approximation
    low_confidence_count: int     # rows where classifier confidence < 0.6


class AnomalyOutput(BaseModel):
    anomaly_type: str             # "circular_flow" | "bounce_cluster"
    severity: str                 # "soft" | "hard"
    description: str              # plain-English explanation from LLM
    affected_rows: list[int]      # row_id values involved in this anomaly


class StatementAnalysisResult(BaseModel):
    transactions: list[dict]      # ClassifiedTransaction dicts — keeps serialisation simple
    metrics: MetricsOutput
    anomalies: list[AnomalyOutput]
    summary: str                  # one-paragraph human-readable summary
