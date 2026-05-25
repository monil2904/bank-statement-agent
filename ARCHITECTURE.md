# ARCHITECTURE.md
# Complete architecture for the Bank Statement Auto-Tag & Metrics Agent

## Problem statement
Indian MSME lenders require manual bank statement analysis for every loan application.
A credit analyst spends 30–45 minutes per statement classifying transactions and computing metrics.
At scale this is slow, inconsistent, and expensive.
This agent reduces that to under 15 seconds with consistent, auditable output.

---

## System overview

```
[User] → uploads CSV → [React Frontend]
                              ↓ POST /analyze (multipart form)
                        [FastAPI Backend]
                              ↓
               ┌──────────────────────────────┐
               │        3-Stage Pipeline       │
               │                              │
               │  Stage 1: CLASSIFY           │
               │  → classifier.py             │
               │  → Claude claude-sonnet-4-20250514      │
               │  → batches of 20 rows        │
               │  → output: category +        │
               │    confidence + reason        │
               │                              │
               │  Stage 2: METRICS            │
               │  → metrics.py                │
               │  → pure pandas math          │
               │  → NO LLM calls here         │
               │  → output: ABB, BTO,         │
               │    bounce ratio, FOIR         │
               │                              │
               │  Stage 3: ANOMALY            │
               │  → anomaly.py                │
               │  → rule-based detection      │
               │  → LLM explanation only      │
               │    when pattern found         │
               │  → output: anomaly list      │
               └──────────────────────────────┘
                              ↓
                    StatementAnalysisResult (JSON)
                              ↓
               [React Frontend renders 4 components]
                  - AnomalyAlert (if anomalies found)
                  - MetricsGrid (4 cards)
                  - Summary paragraph
                  - TransactionTable (color-coded rows)
```

---

## Data flow — step by step

### Input
CSV file with these required columns:
```
date        : YYYY-MM-DD string
description : transaction narration text
amount      : float, positive = credit, negative = debit
balance     : float, running account balance
```

Optional columns (ignored if present): `type`, `reference`, `branch`

### Stage 1 — Classification
- `classifier.py` reads the DataFrame
- Assigns a sequential `row_id` (0-indexed)
- Splits into batches of exactly 20 rows
- Each batch → one API call to Claude with `SYSTEM_PROMPT` from `MASTER_PROMPT.md`
- Response parsed as JSON array
- Result merged back into DataFrame as 3 new columns: `category`, `confidence`, `reason`
- Rows with `confidence < 0.6` are flagged for human review (shown in red in UI)

**Why batches of 20?**
- Reduces API calls from ~110 to 6 per statement
- Keeps each call under 1000 input tokens (cost control)
- Allows Claude to see enough context to detect circular transfers within a batch

### Stage 2 — Metrics (deterministic, no LLM)
Computed from the classified DataFrame:

| Metric | Formula | Purpose |
|--------|---------|---------|
| ABB (Average Bank Balance) | mean of all `balance` values | Financial stability signal |
| Monthly BTO (Bank Turnover) | sum of credits per calendar month | Business activity proxy |
| Avg BTO | mean of monthly BTOs | Normalised income indicator |
| Bounce Ratio | count(bounce rows) / count(debit rows) | Payment discipline |
| FOIR approx | sum(emi_payment amounts) / sum(all credits) | Debt obligation ratio |
| Low confidence count | count(confidence < 0.6) | Data quality indicator |

### Stage 3 — Anomaly Detection
Two checks run in sequence:

**Check A — Circular flow detection**
- Rule: find any alphanumeric string (len ≥ 10) appearing in both a debit and a credit description within 15 days
- If found → call LLM once to generate a plain-English explanation for the underwriter
- Severity: HARD (blocks auto-approval)

**Check B — Bounce cluster**
- Rule: 2 or more bounce-category rows in the same calendar month
- If found → call LLM once for explanation
- Severity: HARD

**LLM is called only when a pattern is confirmed by rules.**
This keeps anomaly detection cost near zero for clean statements.

---

## API design

### POST /analyze
```
Request  : multipart/form-data, field "file" = CSV
Response : StatementAnalysisResult (see models.py)
Errors   :
  400 — not a CSV file
  400 — missing required columns
  500 — LLM API error (propagated with detail)
```

### GET /health
```
Response : {"status": "ok"}
Purpose  : liveness check, smoke test
```

---

## Model decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| LLM model | claude-sonnet-4-20250514 | Best JSON instruction-following at mid cost. GPT-4o is 2x cost for no accuracy gain on classification. |
| Batch size | 20 rows | Balances context window efficiency vs circular transfer detection window |
| Metrics engine | Pure pandas, no LLM | Deterministic, fast, zero cost, auditable |
| Anomaly explanation | LLM only when rule fires | Avoids speculative LLM calls. Rules are cheap; LLM is the last step. |
| Frontend state | useState only | No Redux/Zustand needed for a single-flow tool |

---

## Cost model

| Scale | API calls/statement | Cost/statement | Daily cost (50k statements) |
|-------|-------------------|----------------|----------------------------|
| MVP (sequential) | ~6 calls | ~$0.08 | ~$4,000 |
| Optimised (concurrent) | ~6 calls | ~$0.08 | ~$4,000 |
| Hybrid (small model + LLM fallback) | ~1 call avg | ~$0.01 | ~$500 |

**Hybrid path for production:**
- Use a fine-tuned DistilBERT or similar for 95% of rows (cost ~$0.001/statement)
- Call Claude only for rows where small model confidence < 0.7
- Claude handles ~5% of rows → cost drops 20x

---

## Latency model

| Mode | Latency per statement |
|------|-----------------------|
| Sequential batches (MVP) | ~9 seconds |
| Concurrent batches (asyncio.gather) | ~2–3 seconds |
| With streaming response | ~1.5 seconds to first token |

Sequential is acceptable for hackathon. Concurrent is required for production.

---

## Failure modes and mitigations

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| LLM returns invalid JSON | try/except on json.loads | Strip markdown fences, retry once |
| LLM skips a row | len(result) != len(batch) | Fill missing row_ids with category="other", confidence=0.3 |
| CSV missing columns | Column check before pipeline | Return 400 with exact missing column name |
| API key not set | anthropic.Anthropic() raises | Fail fast at startup with clear error message |
| Circular transfer pair split across batches | Pattern not detected | Post-processing pass across full classified DataFrame |

---

## Planted patterns in synthetic data (for demo verification)

The generator plants 3 verifiable patterns. After running the full pipeline, confirm:

1. **Bounces in month 4 (April 2024)**
   - 2 rows with description containing "RETURN" or "INSUFFICIENT FUNDS"
   - Must be classified as `bounce`

2. **Circular flow in month 5 (May 2024)**
   - Account "ACCT9988776655" appears as debit (-50000) then credit (+50000) then debit (-50000)
   - Must trigger `circular_flow` anomaly

3. **Regular EMI every month**
   - "NACH DR HDFC HOMELOAN EMI" appears 6 times
   - Must all be classified as `emi_payment`

If any of these are wrong after a full run, the system has a bug. Fix before demo.
