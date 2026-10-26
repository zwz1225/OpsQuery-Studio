# Phase 8.2.2 — Controlled Time-Field Append

The online workflow and live benchmark use the same `TimeFieldPolicy` as the
Phase 8.2.1 offline experiment. The policy proposes a field only when the
question contains an explicit time cue, the metric or schema provides a time
field, the field's table is already present in the retrieved set, and the user
can access that table. The selected field must also exist in the active Schema
index. Gold labels are never used to select fields.

The flag is **off by default**. When enabled, up to two proposed fields are
appended after ranked retrieval and before Schema graph construction. Existing
ranked fields keep their order and no field is evicted. The total is capped at
22 fields, including any fields added from the user's workspace.

| Environment variable | Default | Meaning |
| --- | ---: | --- |
| `TIME_FIELD_SUPPLEMENT_ENABLED` | `false` | Enable controlled append |
| `TIME_FIELD_SUPPLEMENT_MAX_EXTRA_FIELDS` | `2` | Maximum appended fields per query |
| `TIME_FIELD_SUPPLEMENT_MAX_TOTAL_FIELDS` | `22` | Maximum final fields after append |

The runtime `retrieval.time_field_supplement` record lists `added_fields`,
`time_cue`, and `matched_metrics` when the flag is enabled. In benchmark JSON it
is saved under each case's `trace.schema_retrieval.time_field_supplement`.
Benchmark `retrieved_fields`, Schema recall/precision, and the graph passed to
the agent include the appended fields. Existing benchmark outputs are unchanged
when the flag is off.

## Verify on the remote server

Run these commands from `backend` after deploying the code. Use a fresh output
path for each run; do not use `--resume` for a before/after comparison.

```bash
python -m unittest tests.test_time_field_supplement tests.test_time_field_ablation tests.test_gold_result -q
python -m unittest discover -s tests -p 'test_*.py' -q

TIME_FIELD_SUPPLEMENT_ENABLED=true python -m evaluation.run_benchmark \
  --mode live --scope classic --workers 1 \
  --case-id GROWTH_OPS-001 --case-id GROWTH_OPS-149 \
  --case-id GROWTH_OPS-150 --case-id CONTENT_OPS-121 \
  --output evaluation/results/benchmark_phase822_targets.json
```

Inspect each case's `retrieved_fields`, `schema_recall`, `schema_precision`,
`generated_sql`, `result_correct`, and `comparison_reason`. The first three
cases test time fields; `CONTENT_OPS-121` is a control case whose missing Gold
field is a relation key, not a time field. Compare with the saved flag-off
baseline under the same code, model, data, and Gold cache conditions. If the
targeted cases are sound, run all 49 cases:

```bash
TIME_FIELD_SUPPLEMENT_ENABLED=true python -m evaluation.run_benchmark \
  --mode live --scope classic --workers 1 --save-snapshot \
  --output evaluation/results/benchmark_live_classic_phase822_append.json
```

Judge the experiment using Gold coverage, Schema recall/precision, field
count, SQL execution success, result accuracy, tool calls, and retrieval
latency. Offline coverage gains do not establish an online accuracy gain.
Turn the flag off or restart the service without it to return to the baseline.
