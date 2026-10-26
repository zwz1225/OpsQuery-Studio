"""Read-only file synchronization check; no credentials, database or model calls."""
import argparse
import json
from pathlib import Path

from scripts.m2_b_common import BASE,digest_file,write_new_json
from evaluation.bird.manifest import code_binding


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=BASE/'evaluation/m2_public_intent_v3_delivery_files_20261018.json')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();manifest=json.loads(args.manifest.read_bytes());errors=[]
    for name,sha in manifest['expected_files'].items():
        p=(BASE/name).resolve()
        if not p.is_relative_to(BASE) or not p.is_file() or digest_file(p)!=sha:errors.append('Missing or different file: '+name)
    actual=code_binding()['files']
    if actual!=manifest['expected_code_files']:errors.append('Executable code inventory differs from the delivered candidate')
    report=dict(stage='M2 public intent delivery integrity',run_status='failed' if errors else 'complete',
                checked_file_count=len(manifest['expected_files']),code_file_count=len(actual),
                manifest_sha256=digest_file(args.manifest),errors=errors,new_model_request_count=0,postgresql_connected=False)
    if args.output:write_new_json(args.output,report)
    print(json.dumps(report,indent=2));raise SystemExit(1 if errors else 0)


if __name__=='__main__':main()
