# M3 categorical population: isolated development24 server comparison

Date: 2026-10-25  
Experiment: target BIRD-PG-1480, observed controls 0050/0173/0459, plus the frozen success20 regression set.  
The pair is development-only; it does not run or authorize holdout.

## Frozen treatment

The two sides contain byte-identical current producer code, model settings, source binding, case order, budgets, and scoring. Each side builds its own source-bound index. The baseline invokes the runner without `--categorical-population`; the candidate invokes it with that option. The candidate option is valid only with the existing `--condition-relations` path.

At 1480, the candidate should receive authorized `customers.segment` and the reviewed customer key, with the public `SME` condition marked optional and the relationship left as an incomplete candidate. No join type or database constraint is assumed. Controls 0050, 0173, and 0459 should not gain categorical context. The comparison records first SQL, native result comparison, status, identity, per-case costs, aggregate tokens/HTTP attempts, and p95 latency. Nonanswers remain failures in the fixed denominator of 24.

The local offline graph audit is recorded in [M3_CATEGORICAL_POPULATION_CANDIDATE_REVIEW_20261025.md](M3_CATEGORICAL_POPULATION_CANDIDATE_REVIEW_20261025.md). It is not a live SQL result.

## Corrected bundle and baseline recovery

The r4 run generated a complete baseline capture, but its integrity check compared the current `intent.py` policy against a stale E06 policy ID in the bundle manifest. Candidate generation did not start. The corrected r5 package freezes the current policy. Its adoption command can reuse the r4 baseline capture and the bounded transport probe only after validating the complete capture, code/source identity, policy, and probe hash. This avoids regenerating the baseline, but the recovered comparison is not a fresh same-time baseline run; that limitation is recorded and must be considered when interpreting model differences. If adoption rejects an identity check, stop and preserve both workspaces.

## Upload and verify on the Linux server

Upload the ZIP and its checksum file to:

```text
$HOME/Python_work/askdata_studio_ops_release/
```

Then run from that project root:

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"
tr -d '\r' < m3_categorical_population_pair24_v1_20261025_r5.zip.sha256 | sha256sum -c -

tools_root="$HOME/Python_work/m3_categorical_population_pair24_tools_20261025_r5"
work="$HOME/Python_work/m3_categorical_population_pair24_20261025_r5"
prior_work="$HOME/Python_work/m3_categorical_population_pair24_20261025_r4"
test ! -e "$tools_root"
test ! -e "$work"
unzip -n -q m3_categorical_population_pair24_v1_20261025_r5.zip -d "$tools_root"
bundle="$tools_root/m3_categorical_population_pair24_v1_20261025_r5"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird

python -u "$bundle/control/prepare_m3_e07_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"

python -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work" --check-only
```

Preparation should finish with `run_status=complete; model_calls=0; database_connected=false`. `--check-only` must complete its static identity checks and process DNS/HTTPS readiness before continuing. If it fails, preserve the workspace and report; do not reuse that workspace for another attempt.

## Adopt the completed baseline and generate the candidate

After check-only completes, run the no-model adoption check:

```bash
python -u "$work/control/adopt_m3_e07_pair24_baseline.py" \
  --workspace "$work" --source-workspace "$prior_work"
```

Adoption must report `run_status=complete`, `baseline_generation_reused=true`, and `new_model_request_count=0`. It reuses the successful r4 10-input transport probe only after checking its report hash and process-DNS dependency against the fresh r5 preflight.

Then generate the candidate once and compare it with the validated baseline capture:

```bash
python -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work" --reuse-baseline
```

The driver generates at most 24 candidate cases. It then runs separate no-model native replays for both captures. The baseline is reused from the completed r4 run, so this recovery comparison is not a fresh same-time baseline experiment. The candidate builds its own independent index. Preserve failed evidence and do not rerun generation in this workspace.

## Reports to download

Keep relative paths intact when downloading:

```text
reports/e07_pair24_preflight_server.json
reports/e07_pair24_server.json
reports/e07_pair24_comparison_server.json
reports/reused_transport_model_probe_server.json
transport_dependency_lock.json
transport_model_probe_receipt.json
baseline_reuse_receipt.json
baseline/backend/evaluation/results/m3_e07_pair24_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e07_pair24_baseline_native_server.json
candidate/backend/evaluation/results/m3_e07_pair24_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e07_pair24_candidate_native_server.json
```

## Review conditions

Inspect 1480's added graph fields and optional `SME` condition, first generated SQL, native result, and any retries. Check that all three observed controls avoided unintended categorical additions, and that all 20 frozen regression cases remain native-correct. Confirm the two captures use the same live source identities and model/dependency settings, while their indexes reside in separate paths. Review the fixed 24-case denominator, failures/nonanswers, HTTP attempts, tokens, and p95 latency. `automatic_screen_pass` is only a development screening signal; the comparison remains nonformal and requires human review of SQL semantics.

## Local bundle identity

- ZIP: `m3_categorical_population_pair24_v1_20261025_r5.zip`
- SHA-256: `384cabd7d373b98bc67af5c3eaa41abff17ead5357af3eb9e64c9bc994f9a513`
- Bundle ID: `f258fb96237e4d1948b7722a23c8469380f8cc613c0e5f8096c422e7062eecfe`
- Producer inventory: 103 files per side; baseline and candidate are byte-identical.
- Credentials, `.env`, and database dumps are not in the bundle.
