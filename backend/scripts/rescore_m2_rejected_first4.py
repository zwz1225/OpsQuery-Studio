"""Audit saved first SQLs rejected by old sample-derived conditions; no models."""
import argparse
from pathlib import Path
from scripts.m2_b_common import PROTOCOL_DIR,digest_file
from scripts.m2_b_target import journal,live_dependencies,DEFAULT_CREDENTIALS
from evaluation.bird.evidence import Evidence,DEFAULT_DATA,DEFAULT_RESULTS
from evaluation.bird.first_sql_audit import run_first_audit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=DEFAULT_DATA)
    parser.add_argument('--results-dir',type=Path,default=DEFAULT_RESULTS)
    parser.add_argument('--credentials-file',type=Path,default=DEFAULT_CREDENTIALS)
    parser.add_argument('--source-report',type=Path,default=DEFAULT_RESULTS/'m2_public_intent_diagnostics14_server.json')
    parser.add_argument('--native-report',type=Path,default=DEFAULT_RESULTS/'m2_public_intent_native14_server.json')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    protected=[args.data_root,PROTOCOL_DIR,args.credentials_file,args.source_report,args.native_report]+[args.results_dir/n for n in
               ('m2_b_postgres_validation_server.json','m2_b_postgres_import_server.json','m2_b_postgres_initialization_server.json')]
    with journal(args.output,'M2 rejected first four SQL native audit; no new generation',protected=protected) as report:
        live_dependencies();evidence=Evidence.load(args.data_root,args.results_dir)
        report['audit_entrypoint_sha256']=digest_file(Path(__file__))
        run_first_audit(evidence,args.source_report,args.native_report,args.credentials_file,report)
    raise SystemExit(0 if report['run_status']=='complete' else 1)


if __name__=='__main__':main()
