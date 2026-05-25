# main.py
# FastAPI application entry point.
# Two endpoints only: GET /health and POST /analyze
# Orchestrates the 3-stage pipeline: classify → metrics → anomaly

import io
import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
load_dotenv()

from classifier import classify_statement
from metrics import compute_metrics
from anomaly import run_all_anomaly_checks
from models import StatementAnalysisResult, MetricsOutput

# ── Startup check ───────────────────────────────────────────────────────────────
if not os.environ.get("GEMINI_API_KEY"):
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Run: export GEMINI_API_KEY=your_key_here"
    )

# ── App setup ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Bank Statement Agent",
    description="Auto-classify transactions, compute lending metrics, detect anomalies",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:3002", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUIRED_COLUMNS = {"date", "description", "amount", "balance"}


# ── Endpoints ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok"}


@app.post("/analyze", response_model=StatementAnalysisResult)
async def analyze(file: UploadFile = File(...)):
    """
    Full pipeline:
    1. Parse and validate CSV
    2. Classify transactions with Claude (batched)
    3. Compute underwriting metrics (deterministic)
    4. Detect anomalies (rule-based + LLM explanation)
    5. Return structured result
    """
    # ── Validate file type ────────────────────────────────────────────────────
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    # ── Parse CSV ─────────────────────────────────────────────────────────────
    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    # ── Validate required columns ─────────────────────────────────────────────
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {missing}. "
                   f"Found columns: {list(df.columns)}"
        )

    # ── Sanitise ──────────────────────────────────────────────────────────────
    df = df.dropna(subset=["date", "description"]).reset_index(drop=True)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce").fillna(0.0)
    df["description"] = df["description"].astype(str).str.strip()

    if len(df) == 0:
        raise HTTPException(status_code=400, detail="CSV has no valid rows after parsing.")

    # ── Stage 1: Classify ─────────────────────────────────────────────────────
    print(f"\n=== Analyzing {file.filename} ({len(df)} rows) ===")
    print("Stage 1: Classification")
    classified_df = classify_statement(df)

    # ── Stage 2: Metrics ──────────────────────────────────────────────────────
    print("Stage 2: Metrics")
    metrics: MetricsOutput = compute_metrics(classified_df)

    # ── Stage 3: Anomaly detection ────────────────────────────────────────────
    print("Stage 3: Anomaly detection")
    anomalies = run_all_anomaly_checks(classified_df)

    # ── Build summary ──────────────────────────────────────────────────────────
    anomaly_note = ""
    if anomalies:
        types = ", ".join(a.anomaly_type.replace("_", " ") for a in anomalies)
        anomaly_note = f" ALERT: {len(anomalies)} anomaly/anomalies detected ({types})."

    summary = (
        f"Analysed {len(df)} transactions over "
        f"{classified_df['date'].nunique()} unique days. "
        f"Average bank balance: Rs.{metrics.abb:,.0f}. "
        f"Average monthly turnover: Rs.{metrics.avg_bto:,.0f}. "
        f"Bounce ratio: {metrics.bounce_ratio:.1%}. "
        f"FOIR (approx): {metrics.foir_approx:.1%}. "
        f"Low-confidence rows requiring review: {metrics.low_confidence_count}."
        f"{anomaly_note}"
    )

    print(f"=== Complete. {summary} ===\n")

    return StatementAnalysisResult(
        transactions=classified_df.to_dict("records"),
        metrics=metrics,
        anomalies=anomalies,
        summary=summary,
    )
