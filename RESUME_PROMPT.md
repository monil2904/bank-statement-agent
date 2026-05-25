
# RESUME PROMPT — Bank Statement Agent
# Give this entire file to your new coding agent as its first message.
# It contains full context, current state, and exact tasks to complete.

---

## What you are

You are a coding agent taking over a partially built project from a previous agent that stopped mid-way. All source files are already written. Your job is NOT to rewrite anything. Your job is to:

1. Read the existing files
2. Run each checkpoint in order
3. Fix only what is broken
4. Get the full system running end-to-end

Do not rewrite files that are already correct. Do not skip checkpoints. Do not assume anything works until you have verified it yourself.

---

## Project overview

You are building a **Bank Statement Auto-Tag & Metrics Agent** for the FlexiLoans Agentic Hackathon (Topic 3).

It does four things:
- Accepts a bank statement CSV upload via a React frontend
- Classifies every transaction into 8 categories using Claude claude-sonnet-4-20250514 (batched, 20 rows per API call)
- Computes 4 underwriting metrics deterministically using pandas (ABB, BTO, bounce ratio, FOIR)
- Detects anomalies using rule-based logic + LLM explanation, renders results in a React dashboard

Stack (do not change):
- Backend  : Python 3.11, FastAPI, pandas, anthropic SDK
- LLM      : claude-sonnet-4-20250514 ONLY
- Frontend : React 18 + Vite, plain fetch, no UI library
- Deploy   : Local — uvicorn port 8000, vite port 5173

---

## Current state — ALL files already exist

Every file has been written. Here is the complete file tree:

```
bank-statement-agent/
├── AGENT_CONTEXT.md
├── MASTER_PROMPT.md
├── ARCHITECTURE.md
├── BUILD_SEQUENCE.md
├── backend/
│   ├── main.py           (126 lines — FastAPI, 2 endpoints)
│   ├── generator.py      (149 lines — synthetic CSV generator)
│   ├── classifier.py     (163 lines — LLM batch classifier)
│   ├── metrics.py        (57 lines  — deterministic metrics)
│   ├── anomaly.py        (155 lines — rule-based + LLM anomaly)
│   ├── models.py         (42 lines  — Pydantic schemas)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── main.jsx
│       └── components/
│           ├── UploadPanel.jsx
│           ├── MetricsGrid.jsx
│           ├── AnomalyAlert.jsx
│           └── TransactionTable.jsx
├── data/                 (may be empty — generator.py creates the CSV)
└── docs/
    ├── SUBMISSION.md
    └── DISCUSSION_ANSWERS.md
```

---

## Your exact task — run every step below in order

Work through these steps sequentially. After each checkpoint, confirm the result before moving to the next step. If a checkpoint fails, fix it before proceeding. Do not skip ahead.

---

### STEP 1 — Verify Python and Node versions

```bash
python --version   # Must be 3.11 or higher
node --version     # Must be 18 or higher
```

CHECKPOINT: Both print the correct version. If either fails, install the correct version before continuing.

---

### STEP 2 — Verify API key is set

```bash
echo $ANTHROPIC_API_KEY
```

CHECKPOINT: Prints a non-empty string starting with sk-ant-

If empty, the user must set it:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

Do not proceed until this is set. The backend will fail to start without it.

---

### STEP 3 — Install backend dependencies

```bash
cd bank-statement-agent/backend
pip install -r requirements.txt
```

CHECKPOINT:
```bash
python -c "import fastapi, pandas, anthropic, pydantic; print('All imports OK')"
```
Must print: All imports OK

If any import fails, install the missing package individually and update requirements.txt.

---

### STEP 4 — Generate synthetic data

```bash
cd bank-statement-agent/backend
python generator.py
```

CHECKPOINT: Output must show all three lines:
- "Bounce rows planted    : 2 (expected 2, in April 2024)"
- "Circular flow rows     : 3 (expected 3, in May 2024)"
- "EMI rows               : 6 (expected 6, one per month)"

AND confirm: `bank-statement-agent/data/synthetic_statement.csv` exists with 100–130 rows.

If counts are wrong, read generator.py and fix the planted pattern logic before continuing.

---

### STEP 5 — Verify models import cleanly

```bash
cd bank-statement-agent/backend
python -c "from models import StatementAnalysisResult; print('Models OK')"
```

CHECKPOINT: Prints "Models OK" with no errors.

If it fails, read models.py carefully and fix any syntax or import issues.

---

### STEP 6 — Test classifier on first 20 rows

```bash
cd bank-statement-agent/backend
python -c "
import pandas as pd
from classifier import classify_statement
df = pd.read_csv('../data/synthetic_statement.csv')
result = classify_statement(df.head(20))
print(result[['description','category','confidence']].to_string())
print('Classifier OK — rows returned:', len(result))
"
```

CHECKPOINT:
- Prints 20 rows
- Each row has a valid category string (one of: salary, business_inflow, emi_payment, bounce, circular_transfer, gambling_crypto, regular_expense, other)
- Each row has a confidence float between 0.0 and 1.0
- No exceptions thrown

If this fails: read classifier.py and check that SYSTEM_PROMPT is correctly copied from MASTER_PROMPT.md. The most common failure is a JSON parse error from the LLM — classifier.py has a _safe_parse function that should handle this gracefully.

---

### STEP 7 — Test classifier on full statement + verify bounce classification

```bash
cd bank-statement-agent/backend
python -c "
import pandas as pd
from classifier import classify_statement
df = pd.read_csv('../data/synthetic_statement.csv')
result = classify_statement(df)
bounces = result[result['category']=='bounce']
emis = result[result['category']=='emi_payment']
print('Total rows classified:', len(result))
print('Bounce rows found:', len(bounces))
print('EMI rows found:', len(emis))
print('Low confidence rows:', len(result[result['confidence'] < 0.6]))
print(bounces[['date','description','category']].to_string())
"
```

CHECKPOINT:
- Total rows matches CSV row count
- Bounce rows found: at least 2, all dated 2024-04-xx
- EMI rows found: 6

If bounce rows = 0: the SYSTEM_PROMPT in classifier.py is not being followed correctly. Check that it is copied exactly from MASTER_PROMPT.md without truncation.

---

### STEP 8 — Test metrics engine

```bash
cd bank-statement-agent/backend
python -c "
import pandas as pd
from classifier import classify_statement
from metrics import compute_metrics
df = pd.read_csv('../data/synthetic_statement.csv')
cdf = classify_statement(df)
m = compute_metrics(cdf)
print(m.model_dump())
print()
print('ABB:', m.abb, '— should be > 0')
print('avg_bto:', m.avg_bto, '— should be > 50000')
print('bounce_ratio:', m.bounce_ratio, '— should be > 0')
print('foir_approx:', m.foir_approx, '— should be between 0.05 and 0.40')
"
```

CHECKPOINT:
- abb > 0
- avg_bto > 50000
- bounce_ratio > 0 (bounces were planted in month 4)
- foir_approx between 0.05 and 0.40

If bounce_ratio = 0: Step 7 must have failed — go back and fix bounce classification first. The metrics engine depends on correct classification output.

---

### STEP 9 — Test anomaly detector

```bash
cd bank-statement-agent/backend
python -c "
import pandas as pd
from classifier import classify_statement
from anomaly import run_all_anomaly_checks
df = pd.read_csv('../data/synthetic_statement.csv')
cdf = classify_statement(df)
anomalies = run_all_anomaly_checks(cdf)
print('Anomalies found:', [a.anomaly_type for a in anomalies])
print('Severities:', [a.severity for a in anomalies])
for a in anomalies:
    print()
    print('Type:', a.anomaly_type)
    print('Description:', a.description[:120])
    print('Affected rows:', a.affected_rows)
"
```

CHECKPOINT:
- Anomalies list contains both 'circular_flow' AND 'bounce_cluster'
- Both severity = 'hard'
- Each description is a non-empty sentence (not blank, not an error message)

If circular_flow is missing: the account pattern "ACCT9988776655" may have been split across batches or not detected. Read anomaly.py detect_circular_flows() — it scans for alphanumeric strings of length 10–16 appearing in both debit and credit descriptions within 15 days.

If bounce_cluster is missing: go back to Step 7 and confirm bounce rows are classified correctly.

---

### STEP 10 — Start backend and verify health endpoint

Open a terminal and run:
```bash
cd bank-statement-agent/backend
uvicorn main:app --reload --port 8000
```

In a second terminal, verify:
```bash
curl http://localhost:8000/health
```

CHECKPOINT: Returns exactly: {"status":"ok"}

If uvicorn fails to start:
- Check that ANTHROPIC_API_KEY is set in the same terminal
- Check that port 8000 is not already in use: `lsof -i :8000`
- Read the error message in the uvicorn terminal carefully

---

### STEP 11 — Test full pipeline via API

With the backend still running, run:
```bash
cd bank-statement-agent
curl -s -X POST http://localhost:8000/analyze \
  -F "file=@data/synthetic_statement.csv" | python -c "
import json, sys
data = json.load(sys.stdin)
print('Status: OK')
print('Transactions:', len(data['transactions']))
print('Anomalies:', [a['anomaly_type'] for a in data['anomalies']])
print('ABB:', data['metrics']['abb'])
print('Summary:', data['summary'][:120])
"
```

CHECKPOINT:
- Status: OK
- Transactions count matches CSV row count
- Anomalies list contains both circular_flow and bounce_cluster
- Summary is a non-empty string

If you get HTTP 422: the CSV column names don't match what models.py expects. Required columns are: date, description, amount, balance.
If you get HTTP 500: read the uvicorn terminal for the Python traceback.

---

### STEP 12 — Install frontend dependencies

```bash
cd bank-statement-agent/frontend
npm install
```

CHECKPOINT:
```bash
npm run dev
```
Vite starts without errors. Browser opens at http://localhost:5173 — you should see the app title "Bank Statement Agent".

If npm install fails: check that Node 18+ is installed. Run `node --version`.
If Vite fails to start: read the error output. Most common issue is a missing dependency — install it and try again.

---

### STEP 13 — Full end-to-end demo test

With both servers running (backend on 8000, frontend on 5173):

1. Open http://localhost:5173 in a browser
2. Upload bank-statement-agent/data/synthetic_statement.csv
3. Wait up to 20 seconds for results

CHECKPOINT — every item must pass:
- [ ] Loading indicator appears immediately after upload
- [ ] AnomalyAlert shows 2 anomalies: circular_flow and bounce_cluster
- [ ] MetricsGrid shows 4 cards with non-zero values
- [ ] Summary paragraph appears below metric cards
- [ ] TransactionTable shows all rows with colour-coded categories
- [ ] At least some rows have red confidence (< 60%)
- [ ] Category filter buttons work — clicking a category filters the table
- [ ] No errors in browser developer console (F12 → Console)
- [ ] No unhandled exceptions in uvicorn terminal

If AnomalyAlert is empty after a successful API call: the frontend AnomalyAlert component may have a rendering bug. Check that it receives and renders anomalies correctly. The API response will have anomalies in data.anomalies as an array.

If the table is empty: check TransactionTable.jsx — it receives transactions as a prop and renders them. The transactions array comes from data.transactions in App.jsx.

---

### STEP 14 — Final verification checklist

Run through this list. Every item must be confirmed before marking the project complete.

Backend:
- [ ] `curl http://localhost:8000/health` returns {"status":"ok"}
- [ ] `curl -X POST .../analyze` with the synthetic CSV returns JSON with transactions, metrics, anomalies, summary
- [ ] anomalies array contains circular_flow and bounce_cluster
- [ ] metrics.bounce_ratio > 0
- [ ] metrics.foir_approx between 0.05 and 0.40

Frontend:
- [ ] App loads at http://localhost:5173 without errors
- [ ] CSV upload triggers loading state
- [ ] All 4 metric cards show non-zero values
- [ ] Both anomalies visible in AnomalyAlert
- [ ] Transaction table shows colour-coded rows
- [ ] Category filter works

Docs:
- [ ] docs/SUBMISSION.md exists and is non-empty
- [ ] docs/DISCUSSION_ANSWERS.md exists and contains 5 prepared answers

---

## Key rules — read before touching any file

1. Do NOT rewrite files that are already working. Read → test → fix only what is broken.
2. Do NOT change the LLM model. Use claude-sonnet-4-20250514 only.
3. Do NOT hardcode ANTHROPIC_API_KEY anywhere. It must come from os.environ.
4. Do NOT add LLM calls to metrics.py. That module is pure math.
5. The SYSTEM_PROMPT in classifier.py must match MASTER_PROMPT.md exactly. Do not paraphrase it.
6. CORS in main.py allows http://localhost:5173 only. Do not widen this.
7. All Pydantic models live in models.py. Do not define schemas inline in other files.

---

## If something is broken and you cannot fix it

Read ARCHITECTURE.md — it documents every design decision and all known failure modes with mitigations.

Read BUILD_SEQUENCE.md — it has detailed troubleshooting for each phase.

The most common failures and their fixes:

| Symptom | Fix |
|---------|-----|
| Classifier returns empty list | JSON parse error — _safe_parse in classifier.py handles this; check raw LLM response |
| bounce_ratio = 0 | Bounce rows not classified correctly — verify SYSTEM_PROMPT is pasted fully |
| circular_flow not in anomalies | Account pattern split across batches — detect_circular_flows runs on full df, should still catch it |
| HTTP 422 from /analyze | CSV column mismatch — required: date, description, amount, balance |
| CORS error in browser | allow_origins in main.py must match exact Vite URL including port |
| anthropic.APIError | ANTHROPIC_API_KEY not set in the terminal running uvicorn |
| Frontend blank after upload | Check browser console for JS errors — most likely a prop not being passed correctly |
