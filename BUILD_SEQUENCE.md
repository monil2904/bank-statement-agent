# BUILD_SEQUENCE.md
# Strict ordered build sequence for the coding agent.
# Complete every step. Verify every checkpoint. Do not skip ahead.
# If a checkpoint fails — fix it before moving to the next step.

---

## PHASE 0 — Environment setup
**Complete this before writing any code.**

### Step 0.1 — Verify Python version
```bash
python --version
# Required: 3.11 or higher
# If lower: install Python 3.11 before continuing
```
CHECKPOINT: Output shows Python 3.11.x or higher.

### Step 0.2 — Verify Node version
```bash
node --version
# Required: 18 or higher
```
CHECKPOINT: Output shows v18.x or higher.

### Step 0.3 — Verify API key
```bash
echo $ANTHROPIC_API_KEY
# Must not be empty
```
CHECKPOINT: Prints your API key (starts with sk-ant-). If empty: export ANTHROPIC_API_KEY=your_key

### Step 0.4 — Create directory structure
```bash
mkdir -p bank-statement-agent/backend
mkdir -p bank-statement-agent/frontend/src/components
mkdir -p bank-statement-agent/data
mkdir -p bank-statement-agent/docs
```
CHECKPOINT: All 4 directories exist.

### Step 0.5 — Install backend dependencies
```bash
cd bank-statement-agent/backend
pip install fastapi==0.111.0 uvicorn==0.29.0 python-multipart==0.0.9 pandas==2.2.2 anthropic==0.28.0 pydantic==2.7.1
pip freeze > requirements.txt
```
CHECKPOINT: `python -c "import fastapi, pandas, anthropic, pydantic; print('OK')"` prints OK.

### Step 0.6 — Scaffold frontend
```bash
cd bank-statement-agent/frontend
npm create vite@latest . -- --template react
npm install
```
CHECKPOINT: `npm run dev` starts without errors. Browser shows Vite + React default page.

---

## PHASE 1 — Synthetic data
**Build and verify test data before any LLM code.**

### Step 1.1 — Write backend/generator.py
Write the file exactly as specified in generator.py.
CHECKPOINT: `cd backend && python generator.py`
Expected output: "Generated X rows. Planted: bounces in month 4, circular flow in month 5."
Expected: data/synthetic_statement.csv exists with 100–130 rows.

### Step 1.2 — Verify planted patterns manually
Open data/synthetic_statement.csv and confirm:
- Search "CHQ RETURN" or "NACH RETURN" → must appear in rows with date 2024-04-xx
- Search "ACCT9988776655" → must appear exactly 3 times in rows with date 2024-05-xx
- Search "NACH DR HDFC HOMELOAN EMI" → must appear exactly 6 times (once per month)

CHECKPOINT (HARD STOP): All 3 patterns confirmed present.
If any pattern is missing → fix generator.py before proceeding. Do not move to Phase 2.

---

## PHASE 2 — Models and classifier

### Step 2.1 — Write backend/models.py
Write Pydantic models exactly as specified.
CHECKPOINT: `python -c "from models import StatementAnalysisResult; print('Models OK')"`
No ImportError = pass.

### Step 2.2 — Write backend/classifier.py
- Copy SYSTEM_PROMPT exactly from MASTER_PROMPT.md (block between ===START=== and ===END===)
- Implement classify_batch() and classify_statement() exactly as specified
CHECKPOINT:
```bash
python -c "
import pandas as pd
from classifier import classify_statement
df = pd.read_csv('../data/synthetic_statement.csv')
result = classify_statement(df.head(20))
print(result[['description','category','confidence']].to_string())
"
```
Expected: 20 rows printed, each with a valid category string and confidence float.
If any row has category=None or throws an error → fix classifier.py before proceeding.

### Step 2.3 — Verify bounce classification
```bash
python -c "
import pandas as pd
from classifier import classify_statement
df = pd.read_csv('../data/synthetic_statement.csv')
result = classify_statement(df)
bounces = result[result['category']=='bounce']
print(f'Bounce rows found: {len(bounces)}')
print(bounces[['date','description','category']].to_string())
"
```
CHECKPOINT: At least 2 bounce rows found, both with dates in 2024-04.
If 0 bounce rows → the prompt is not being followed. Check SYSTEM_PROMPT is pasted correctly.

---

## PHASE 3 — Metrics engine

### Step 3.1 — Write backend/metrics.py
Pure pandas math. No anthropic import. No LLM calls.
CHECKPOINT:
```bash
python -c "
import pandas as pd
from classifier import classify_statement
from metrics import compute_metrics
df = pd.read_csv('../data/synthetic_statement.csv')
cdf = classify_statement(df)
m = compute_metrics(cdf)
print(m.model_dump())
"
```
Expected values:
- abb > 0 (should be 50,000 to 200,000 range)
- avg_bto > 50,000
- bounce_ratio > 0 (bounces were planted)
- foir_approx between 0.05 and 0.40
- low_confidence_count >= 0

HARD STOP: If any metric is 0 when it should not be (especially bounce_ratio) → fix metrics.py.
Do not proceed to Phase 4 with broken metrics.

---

## PHASE 4 — Anomaly detector

### Step 4.1 — Write backend/anomaly.py
Two detection functions + one LLM explanation function.
CHECKPOINT:
```bash
python -c "
import pandas as pd
from classifier import classify_statement
from anomaly import run_all_anomaly_checks
df = pd.read_csv('../data/synthetic_statement.csv')
cdf = classify_statement(df)
anomalies = run_all_anomaly_checks(cdf)
print([a.anomaly_type for a in anomalies])
print([a.severity for a in anomalies])
for a in anomalies:
    print(a.description[:100])
"
```
Expected output:
- List contains 'circular_flow' and 'bounce_cluster'
- Both severity = 'hard'
- Each description is a non-empty sentence

If circular_flow is missing: the account pattern "ACCT9988776655" may have been split across batches.
Fix: run detect_circular_flows on the full classified DataFrame.
If bounce_cluster is missing: check that bounce rows were classified correctly in Phase 2.

---

## PHASE 5 — FastAPI backend

### Step 5.1 — Write backend/main.py
Two endpoints: GET /health and POST /analyze.
CORS enabled for http://localhost:5173 only.
CHECKPOINT A:
```bash
uvicorn main:app --reload --port 8000
```
In a new terminal:
```bash
curl http://localhost:8000/health
```
Expected: {"status":"ok"}

CHECKPOINT B:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@../data/synthetic_statement.csv"
```
Expected: Large JSON response with keys: transactions, metrics, anomalies, summary.
If 422 Unprocessable Entity → check CSV column names match models.py exactly.
If 500 → check ANTHROPIC_API_KEY is set in the same terminal session.

### Step 5.2 — Test full pipeline via API
```bash
python -c "
import requests
with open('../data/synthetic_statement.csv','rb') as f:
    r = requests.post('http://localhost:8000/analyze', files={'file':('statement.csv',f,'text/csv')})
    data = r.json()
    print('Status:', r.status_code)
    print('Transaction count:', len(data['transactions']))
    print('Anomalies:', [a['anomaly_type'] for a in data['anomalies']])
    print('ABB:', data['metrics']['abb'])
    print('Summary:', data['summary'])
"
```
CHECKPOINT: Status 200, transaction count matches CSV row count, anomalies list non-empty.

---

## PHASE 6 — React frontend

### Step 6.1 — Write frontend/src/api.js
Single async function analyzeStatement(file).
CHECKPOINT: No syntax errors. File exports analyzeStatement.

### Step 6.2 — Write all 4 components
Write in this order (each depends on the previous):
1. MetricsGrid.jsx
2. AnomalyAlert.jsx
3. TransactionTable.jsx
4. UploadPanel.jsx
CHECKPOINT after each: `npm run dev` compiles without errors.

### Step 6.3 — Write frontend/src/App.jsx
Wire all 4 components together with useState.
CHECKPOINT:
- npm run dev compiles clean
- Open http://localhost:5173
- Upload data/synthetic_statement.csv
- Expected within 15 seconds:
  - AnomalyAlert shows 2 anomalies (circular_flow, bounce_cluster)
  - MetricsGrid shows 4 non-zero metric cards
  - Summary paragraph visible
  - TransactionTable shows all rows with color-coded categories
  - At least some rows show confidence < 100% (in red)

HARD STOP: If anomaly alert is empty after upload → go back to Phase 4 and debug anomaly.py.
Do not present the demo with empty anomalies — the planted patterns are the proof the agent works.

---

## PHASE 7 — Final verification and submission prep

### Step 7.1 — Full end-to-end demo run (fresh)
Kill both servers. Restart both. Upload fresh CSV. Verify all outputs.

Checklist:
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] CSV upload triggers loading state in UI
- [ ] MetricsGrid: all 4 cards have non-zero values
- [ ] AnomalyAlert: both circular_flow and bounce_cluster visible
- [ ] TransactionTable: color-coded, confidence column visible, red for < 60%
- [ ] Summary paragraph visible below metric cards
- [ ] No console errors in browser dev tools
- [ ] No unhandled errors in uvicorn terminal

### Step 7.2 — Write docs/SUBMISSION.md
See docs/SUBMISSION.md template.

### Step 7.3 — Write docs/DISCUSSION_ANSWERS.md
See docs/DISCUSSION_ANSWERS.md — memorise all 5 answers before presenting.

---

## What to do if something breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Classifier returns empty list | JSON parse error | Add try/except, strip ``` fences, print raw response |
| bounce_ratio = 0 | Bounces not classified correctly | Check SYSTEM_PROMPT is copied exactly; run Phase 2 checkpoint again |
| circular_flow not detected | Pattern split across batches | Run detect_circular_flows on full df after classification |
| 422 from /analyze | CSV column name mismatch | Print df.columns and compare to models.py required fields |
| CORS error in browser | Origin mismatch | Check allow_origins in main.py matches exact Vite URL |
| anthropic.APIError | API key not set | export ANTHROPIC_API_KEY in same terminal as uvicorn |
