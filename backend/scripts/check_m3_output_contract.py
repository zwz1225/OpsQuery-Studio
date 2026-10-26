"""Offline public-contract observations on saved development SQL; not native EX."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from evaluation.bird.output_contract import build_contract, observation, policy
from evaluation.bird.manifest import code_binding

BASE=Path(__file__).resolve().parents[1]
PROTOCOL=BASE/'evaluation/cases/bird_mini_dev/m2_pg_v1'
CAPTURE=BASE/'evaluation/results/m2_public_intent_v4_development80_server.json'
CAPTURE_SHA='e19e9eb40db7bc72c9bbf88ecbb31eb126aa28432c183669f4ff08ff4d8c25ef'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value,message):
    if not value:raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-report',type=Path,default=CAPTURE)
    parser.add_argument('--source-sha256',default=CAPTURE_SHA)
    parser.add_argument('--case-list',type=Path,default=BASE/'evaluation/cases/bird_mini_dev/m3_a_output_contract24.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=args.source_report.resolve();selected=args.case_list.resolve();output=args.output.resolve()
    require(not output.exists() and output not in (source,selected),'Choose a new output path and preserve source evidence')
    protected=(PROTOCOL.resolve(),(BASE/'evaluation/results/holdout_attempts').resolve())
    require(not any(root==output or root in output.parents for root in protected),'Output overlaps frozen protocol or holdout ledger')
    require(sha(source)==args.source_sha256,'Saved capture SHA differs')
    capture=json.loads(source.read_bytes());protocol=json.loads((PROTOCOL/'protocol.json').read_bytes())
    public_path=PROTOCOL/'inputs/development80.jsonl'
    require(sha(public_path)==protocol['artifact_sha256']['inputs/development80.jsonl'],'Public development input SHA differs')
    public={r['case_id']:r for r in map(json.loads,public_path.read_text(encoding='utf-8').splitlines())}
    ids=json.loads(selected.read_bytes())['case_ids']
    require(0<len(ids)<=80 and len(ids)==len(set(ids)) and set(ids)<=set(public),'Select development IDs only; holdout refused')
    require(capture['run_status']=='complete' and capture.get('errors')==[] and capture['mode']=='diagnostic'
        and capture['gold_executed'] is False and capture['holdout_live_allowed'] is False,'Complete non-Gold development capture required')
    cases={r['case_id']:r for r in capture['cases']}
    require(len(cases)==len(capture['cases']) and set(ids)<=set(cases),'Missing or duplicate saved cases')
    before={str(p):sha(p) for p in (source,selected,public_path,PROTOCOL/'protocol.json')}
    rows=[]
    for rid in ids:
        case=cases[rid];require(case['database_id']==public[rid]['database_id'],'Case source differs')
        record=case['development_diagnostics']['retrieval']['schema_graph']
        require(record['complete'] is True,'Complete authorized graph is required')
        contract=build_contract(public[rid],record['value'],case.get('intent_contract'))
        sql=case.get('generated_sql')
        rows.append(dict(case_id=rid,database_id=case['database_id'],source_status=case['status'],
            contract=contract,sql_sha256=hashlib.sha256(sql.encode()).hexdigest() if sql else None,
            observation=observation(contract,record['value'],sql) if sql else
                dict(status='not_evaluated',reason='no_saved_final_sql',report_only=True,issues=[])))
    require(all(sha(Path(p))==v for p,v in before.items()),'Source changed during observation')
    report=dict(stage='M3 E01 public output passive replay; not native EX or model validation',
        date='2026-10-21',run_status='complete',source_report_sha256=args.source_sha256,
        source_generation_code_binding=capture['code_binding'],observer_code_binding=code_binding(),
        source_sha256=before,policy=policy(),cases=rows,
        summary=dict(case_count=len(rows),status_counts=dict(Counter(r['observation']['status'] for r in rows)),
            issue_counts=dict(Counter(v['code'] for r in rows for v in r['observation']['issues'])),
            parse_complete_count=sum(r['contract']['parse_complete'] for r in rows)),
        new_model_request_count=0,postgresql_connected=False,sql_executed=False,
        native_ex_computed=False,model_improvement_verified=False,
        meaning='Only public request binding and saved SQL projection observations; not a score or live generation.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))


if __name__=='__main__':main()
