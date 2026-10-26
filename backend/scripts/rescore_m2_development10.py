"""Replay the ten captured development SQLs against original native Gold; no model."""
import argparse
from pathlib import Path

from scripts.m2_b_common import PROTOCOL_DIR,digest_file
from scripts.m2_b_target import DEFAULT_CREDENTIALS,journal,live_dependencies
from evaluation.bird.evidence import Evidence,DEFAULT_DATA,DEFAULT_RESULTS
from evaluation.bird.replay import run_replay


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=DEFAULT_DATA)
    parser.add_argument('--results-dir',type=Path,default=DEFAULT_RESULTS)
    parser.add_argument('--credentials-file',type=Path,default=DEFAULT_CREDENTIALS)
    parser.add_argument('--source-report',type=Path,default=DEFAULT_RESULTS/'m2_schema_coverage_diagnostics14_server.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with journal(args.output,'M2 ten captured development SQL native replay; not formal benchmark',
            protected=[args.data_root,PROTOCOL_DIR,args.credentials_file,args.source_report]+[args.results_dir/n for n in
                ('m2_b_postgres_validation_server.json','m2_b_postgres_import_server.json','m2_b_postgres_initialization_server.json')]) as report:
        live_dependencies();evidence=Evidence.load(args.data_root,args.results_dir)
        report['replay_entrypoint_sha256']=digest_file(Path(__file__))
        run_replay(evidence,args.source_report,args.credentials_file,report)
    raise SystemExit(0 if report['run_status']=='complete' else 1)


if __name__=='__main__':main()
