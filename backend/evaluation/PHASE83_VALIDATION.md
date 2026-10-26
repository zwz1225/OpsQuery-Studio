# Phase 8.3.1 — Expanded Schema Retrieval Validation

This phase fixes a 30-case validation cohort in
`evaluation/cases/phase83_validation.json`. The cases are selected from the 381
non-classic cases already in `all_cases.jsonl`: 10 growth, 10 channel, and 10
content cases. They include questions with and without explicit time cues,
single- and multi-table queries, and different difficulty levels. Every case
has Gold SQL and Gold fields. All 30 Gold SQL queries executed successfully
against the local project data and returned nonempty results when the cohort
was created.

The cohort does **not** constitute an external generalization benchmark: the
cases share the project's synthetic dataset and case-authoring style. Keep
the original classic 49-case result as a separate regression guard.

## Run on the server

Run from `backend`, after syncing this code and manifest. Use distinct output
paths and do not use `--resume` when establishing a baseline.

```bash
python -m unittest tests.test_retrieval_validation -q

# Verify Gold SQL against the server's current data (no model calls).
python -m evaluation.run_benchmark \
  --mode gold --scope all --no-use-cached-gold \
  --case-list evaluation/cases/phase83_validation.json \
  --output evaluation/results/phase83_gold_check.json

# Capture BM25, embedding, RRF, rerank, and raw final-selection timings.
python -m evaluation.retrieval_diagnosis \
  --scope all --case-list evaluation/cases/phase83_validation.json \
  --output evaluation/results/phase83_retrieval_diagnosis.json

# Working baseline for Phase 8.3: include the successful Phase 8.2 time-field
# experiment, while leaving its project default disabled.
TIME_FIELD_SUPPLEMENT_ENABLED=true python -m evaluation.run_benchmark \
  --mode live --scope all --workers 1 --save-snapshot \
  --case-list evaluation/cases/phase83_validation.json \
  --output evaluation/results/phase83_live_baseline.json

# This report only reads the saved files; it makes no model or SQL calls.
python -m evaluation.retrieval_validation \
  --case-list evaluation/cases/phase83_validation.json \
  --benchmark evaluation/results/phase83_live_baseline.json \
  --diagnosis evaluation/results/phase83_retrieval_diagnosis.json \
  --output evaluation/results/phase83_validation_baseline.json
```

Read `evaluation/results/phase83_validation_baseline.md`. It reports Gold
coverage, Schema recall and precision, average/median/P95 field counts, the
number of cases with at least 20 fields, benchmark retrieval latency, SQL
execution success, result accuracy, and the raw retrieval stage timings.
The JSON report also has per-case records and groups by scenario, difficulty,
single versus multiple Gold tables, and explicit time cue.

Benchmark `retrieval_ms` and diagnosis stage timings come from separate runs;
do not add them together. SQL execution latency is not retrieval latency.
Check `phase83_gold_check.json` for 30 successful Gold SQL executions before
interpreting live result accuracy. The benchmark and diagnosis CLIs validate
that all IDs in the manifest exist in the selected `--scope`.

For a strict flag-off control, run the same 30 cases with
`TIME_FIELD_SUPPLEMENT_ENABLED=false` and a new output path. Use the same
manifest, model settings, database, and Gold cache conditions. Later Schema
selection experiments should be compared against the flag-on working baseline
and the classic 49-case regression guard.
