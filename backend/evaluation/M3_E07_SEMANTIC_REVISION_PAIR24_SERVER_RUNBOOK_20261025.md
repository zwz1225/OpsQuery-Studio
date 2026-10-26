# M3 E07 semantic revision: clean development24 comparison

Date: 2026-10-25  
Experiment identity: `m3_e07_semantic_revision_development24_v1`  
Scope: target `BIRD-PG-1480`, observed controls `0050`/`0173`/`0459`, and the frozen success20 regression set. This is a development-only comparison, not formal BIRD EX or holdout.

## Treatment

Baseline and candidate use identical producer code, PostgreSQL source identity, model configuration, categorical-population context, fixed 24-case order, scoring protocol, and per-case budgets. Each side rebuilds and validates its own isolated indexes. Only the candidate receives `--semantic-planning`, an advisory prompt for aggregation grain and requested projection order. It does not add SQL rejection or rewrite rules. Baseline reuse is disabled; both sides must be newly generated in this run.

The reviewer must inspect SQL semantics in addition to native result scores:

- **1480:** confirm generated SQL groups by the requested month and aggregates qualifying SME consumption (for example, `SUM(consumption)`) before ranking months. A matching result without this aggregation is not a semantic pass.
- **0050:** confirm the output projection is postal street address first and school name second, in that order.
- **0173:** preserve as a separately observed amount-versus-account-identifier failure.
- **0459:** preserve as a successful observed control.
- Confirm all 20 frozen successful regression cases remain native-correct.

## Upload and prepare on the Linux server

Upload the ZIP and checksum file to:

```text
$HOME/Python_work/askdata_studio_ops_release/
```

Run from the project root:

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"
tr -d '\r' < m3_categorical_population_pair24_v1_20261025_r7.zip.sha256 | sha256sum -c -

tools_root="$HOME/Python_work/m3_categorical_population_pair24_tools_20261025_r7"
work="$HOME/Python_work/m3_categorical_population_pair24_20261025_r7"
test ! -e "$tools_root"
test ! -e "$work"
unzip -n -q m3_categorical_population_pair24_v1_20261025_r7.zip -d "$tools_root"
bundle="$tools_root/m3_categorical_population_pair24_v1_20261025_r7"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird

python -u "$bundle/control/prepare_m3_e07_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"
```

Preparation must finish with `run_status=complete`, `model_calls=0`, and `database_connected=false`. Stop if preparation fails; preserve its directory and report.

## Preflight, bounded model probe, and clean same-round pair

Run each command in order. The probe uses one bounded embedding request and does not read question cases or connect to PostgreSQL.

```bash
python -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work" --check-only

python -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work" --model-probe

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird && \
python -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work"
```

The final run must report `run_status=complete`, `phase=complete`, `baseline_capture_reused=false`, and `strict_same_round=true`. Generation order is baseline then candidate; both captures complete before either native replay. Each side independently builds its index. Do not add `--reuse-baseline`, resume a failed generation, or rerun in the same workspace. Preserve failed evidence and use a new bundle/workspace identity for any later attempt.

## Reports to download

Download while preserving the relative paths under `$work`:

```text
reports/e07_pair24_preflight_server.json
reports/e07_pair24_transport_model_probe_server.json
reports/e07_pair24_server.json
reports/e07_pair24_comparison_server.json
transport_dependency_lock.json
transport_model_probe_receipt.json
baseline/backend/evaluation/results/m3_e07_pair24_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e07_pair24_baseline_native_server.json
candidate/backend/evaluation/results/m3_e07_pair24_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e07_pair24_candidate_native_server.json
```

## Review gate

The comparison is not accepted solely because `automatic_screen_pass` is true or native EX matches. Review the exact candidate SQL and projection order described above, then check source identity, both semantic-planning policy records, all 24 case identities, 20/20 regression retention, per-side model attempts/tokens/latency, and completed native replays. The final decision remains manual and development-only.

## Local bundle identity

- ZIP: `m3_categorical_population_pair24_v1_20261025_r7.zip`
- SHA-256: `0fefb5fea63b2a3473848237347a4d3eca5f04662ef6de93587de6fdfd54c1bd`
- Bundle ID: `a836b7ba4b0e84de15bdf71fccaea436bb29ee6177a4a88446f8edd5d0929ac8`
- Producer inventory: 103 files per side; baseline and candidate code are byte-identical.
- The archive contains no `.env`, model/database credential files, or database dump.
