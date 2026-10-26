"""Run the fixed three-case captured grain-rejection audit; no model calls."""
import argparse
from pathlib import Path

from scripts.m2_b_common import PROTOCOL_DIR, digest_file
from scripts.m2_b_target import DEFAULT_CREDENTIALS, journal, live_dependencies
from scripts.m2_grain_diagnostics import run_audit
from evaluation.bird.evidence import Evidence, DEFAULT_DATA, DEFAULT_RESULTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--results-dir', type=Path, default=DEFAULT_RESULTS)
    parser.add_argument('--credentials-file', type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument('--source-report', type=Path, default=DEFAULT_RESULTS/'m2_public_intent_v3_development80_server_rerun_v2.json')
    parser.add_argument('--native-report', type=Path, default=DEFAULT_RESULTS/'m2_public_intent_v3_development80_native_server_rerun_v2.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protected = [args.data_root, PROTOCOL_DIR, args.credentials_file, args.source_report, args.native_report]
    protected += [args.results_dir/name for name in
                  ('m2_b_postgres_validation_server.json', 'm2_b_postgres_import_server.json', 'm2_b_postgres_initialization_server.json')]
    with journal(args.output, 'M2 three-case captured grain-rejection diagnostics; not a formal benchmark', protected=protected) as report:
        live_dependencies()
        evidence = Evidence.load(args.data_root, args.results_dir)
        report['audit_entrypoint_sha256'] = digest_file(Path(__file__))
        run_audit(evidence, args.source_report, args.native_report, args.credentials_file, report)
    raise SystemExit(0 if report['run_status'] == 'complete' else 1)


if __name__ == '__main__':
    main()
