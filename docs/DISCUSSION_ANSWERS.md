# DISCUSSION_ANSWERS.md
# Memorise all 5 answers before the hackathon presentation.
# Judges WILL ask at least 3 of these. Have crisp, specific answers ready.

---

## Q1: Why Claude Sonnet over GPT-4o?

**Answer:**
For classification tasks that require strict adherence to a JSON schema, Sonnet performs
equivalently to GPT-4o. In our testing, both models classify Indian MSME transactions with
comparable accuracy — but Sonnet costs approximately 40% less per token. Since we make
6 API calls per statement and aim to scale to 50,000 statements/day, that cost difference
is significant. GPT-4o would add cost with no measurable accuracy gain on this specific task.
We also find Sonnet's instruction-following on "return ONLY a JSON array" more consistent —
fewer cases where it wraps output in markdown fences.

---

## Q2: What is the cost per statement, and how does it scale?

**Answer:**
One 6-month statement is roughly 110 rows. At batch size 20, that's 6 API calls.
Each call uses approximately 500 input tokens + 300 output tokens = 800 tokens total.
6 calls × 800 tokens = ~4,800 tokens per statement.
At Sonnet pricing (~$3/MTok input, ~$15/MTok output): roughly $0.07–0.08 per statement.

At 50,000 statements/day that's ~$4,000/day via full LLM — too expensive for production.

The production path is a hybrid: fine-tune a small model (DistilBERT or similar) on 10,000
labelled statements. It handles 95% of rows cheaply. Call Claude only for rows where the
small model confidence is below 70% — roughly 5% of rows. Cost drops to ~$0.005/statement,
or ~$250/day at 50k volume.

---

## Q3: What is the observed latency, and is it acceptable?

**Answer:**
In our MVP with sequential batch calls: ~9 seconds for a 110-row statement.
That's 6 API calls × ~1.5 seconds each.

For a back-office analyst tool, 9 seconds is acceptable — it replaces 30 minutes of manual work.
For a real-time customer-facing product, it's too slow.

The fix is straightforward: use asyncio.gather() to send all 6 batches concurrently.
Expected latency drops to ~2–3 seconds (bounded by the slowest single call).
This is a one-function change in classifier.py — we didn't implement it in the MVP
to keep the code readable for the demo.

---

## Q4: How do you handle LLM misclassification?

**Answer:**
Two safety nets work independently of the LLM.

First: the confidence score. Any row below 0.6 is shown in red in the UI and flagged in
the MetricsOutput. The analyst knows exactly which rows need a second look.

Second: anomaly detection is rule-based, not LLM-based. The circular flow check runs on the
raw description text — it looks for alphanumeric account identifiers appearing in both a debit
and credit within 15 days. If the LLM misclassified a circular transfer row as "regular_expense",
the anomaly checker still fires because it doesn't depend on the category column.
The LLM is used only to explain the anomaly in plain English, after the rule has confirmed it.

This means misclassification can affect metrics (FOIR, bounce ratio) but cannot hide a detected anomaly.

---

## Q5: What didn't work, and what would you do with more time?

**Answer (honest):**
Three things we'd fix:

1. **Circular transfer detection across batch boundaries.** If the debit and credit for the same
account fall in different batches of 20, the LLM classifier won't see them together and can't flag
circular_transfer. Our anomaly.py handles this in post-processing (running on the full DataFrame),
but we'd want the classifier to be aware too — achieved by adding a sliding window or increasing
overlap between batches.

2. **GST cross-check.** The most valuable underwriting signal we didn't build: compare bank-derived
monthly turnover (BTO) to the GST-filed turnover for the same period. A 30%+ discrepancy is a hard
red flag for income misrepresentation. Would add this as a separate module with a structured
comparison output.

3. **Confidence calibration.** Our 0.6 threshold is heuristic. With a labelled dataset of 1,000+
statements, we'd compute a precision-recall curve and set the threshold to minimise false negatives
on bounce and circular_transfer categories — since missing those is far more costly than over-flagging.
