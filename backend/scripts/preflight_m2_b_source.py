"""Verify transferred frozen M2 sources and write an offline import manifest."""
from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

from evaluation.bird_protocol import SQL_DUMP_SHA256, load_canonical_questions
from scripts.m2_b_common import (BASE, PROTOCOL_DIR, PROTOCOL_SHA256, digest_file, digest_json,
    load_protocol, now, require, require_import_spec, safe_error, write_new_json)
from scripts.m2_b_dump import scan_dump


def prepare(data_root: Path, protocol_dir: Path=PROTOCOL_DIR) -> tuple[dict,dict]:
    require(version('sqlglot')=='30.17.0',"SQLGlot version differs from frozen application dependency")
    protocol,target=load_protocol(protocol_dir)
    lineage=json.loads((protocol_dir/'source_lineage.json').read_bytes())
    sources=[]
    for row in lineage['files']:
        if row['kind']=='archives':continue  # Original ZIP remains local; not an import input.
        path=(data_root/row['relative_to_data_root']).resolve()
        require(path.is_relative_to(data_root.resolve()),"Invalid source path")
        require(path.is_file() and path.stat().st_size==row['size_bytes'],"Missing or wrong-size source file: "+row['relative_to_data_root'])
        if row['kind']!='postgres_dump':
            require(digest_file(path)==row['sha256'],"Source hash differs: "+row['relative_to_data_root'])
        sources.append(row)
    questions_path=data_root/lineage['question_relative_path']
    questions=load_canonical_questions(questions_path.read_bytes())
    schema_path=next(data_root/r['relative_to_data_root'] for r in sources if r['kind']=='logical_schema')
    schemas=json.loads(schema_path.read_bytes());table_domains={}
    for schema in schemas:
        db=schema['db_id'];require(db in target['query_roles'],"Unknown logical database")
        for original in schema['table_names_original']:
            name=original.lower()
            require(name not in table_domains,"Physical table appears in multiple logical domains")
            table_domains[name]=db
    dump_path=next(data_root/r['relative_to_data_root'] for r in sources if r['kind']=='postgres_dump')
    inspection=scan_dump(dump_path,table_domains)
    require(inspection['dump_sha256']==SQL_DUMP_SHA256,"SQL dump differs from frozen source")
    require(len(inspection['tables'])==75 and inspection['row_count']==3898114,"Unexpected source table/row counts")
    require(len(inspection['sequences'])==24,"Unexpected sequence count")
    require(inspection['control_statement_counts'].get('owner')==99,"Unexpected ownership declaration count")
    manifest={'stage':'M2 B source import specification','version':1,'protocol_sha256':PROTOCOL_SHA256,
        'dataset_revision':protocol['dataset']['revision'],'target':target,
        'questions_sha256':protocol['dataset']['questions_sha256'],'sources':sources,
        'question_relative_path':lineage['question_relative_path'],'dump':inspection,
        'query_domains':{db:{'query_role':role,'tables':sorted(n for n,d in table_domains.items() if d==db)} for db,role in target['query_roles'].items()},
        'import_controls':{'owner_mapping':{'xiaolongli':target['import_role']},
            'source_session_settings':'replace with explicit controlled importer settings',
            'source_sql_execution':'not performed; future importer must revalidate source and specification hashes',
            'required_target_state':'independent database absent before initialization; no automatic reuse or cleanup',
            'transaction_and_recovery':'to be implemented before import',
            'data_verification':'raw COPY hashes/counts are source evidence; live typed-row verification is still required'},
        'postgresql_connected':False,'database_imported':False,'target_data_verified':False}
    summary={'table_count':75,'logical_database_count':11,'column_count':inspection['column_count'],
             'source_row_count':inspection['row_count'],'sequence_count':24,'question_count':len(questions),
             'control_statement_counts':inspection['control_statement_counts']}
    return manifest,summary


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=BASE/'data/external/bird_mini_dev')
    parser.add_argument('--protocol-dir',type=Path,default=PROTOCOL_DIR)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve();data=args.data_root.resolve()
    require(not out.exists(),"Choose a new preparation directory; preserve previous evidence")
    require(not out.is_relative_to(data) and not out.is_relative_to(args.protocol_dir.resolve()),"Reports must be outside frozen sources and protocol")
    out.mkdir(parents=True)
    report={'stage':'M2 B offline source preflight','run_status':'failed','started_at':now(),
            'postgresql_connected':False,'database_imported':False,'target_data_verified':False,'new_model_request_count':0,'errors':[]}
    try:
        manifest,summary=prepare(data,args.protocol_dir.resolve())
        require_import_spec(manifest)
        write_new_json(out/'import_manifest.json',manifest)
        report.update(run_status='complete',summary=summary,import_spec_sha256=digest_json(manifest))
    except Exception as error:report['errors'].append(safe_error(error))
    report['finished_at']=now();write_new_json(out/'source_preflight.json',report)
    if report['run_status']=='complete':
        write_new_json(out/'preparation_review.json',{'stage':'M2 B source preparation review','run_status':'complete',
            'summary':report['summary'],'import_spec_sha256':report['import_spec_sha256'],
            'input_artifact_sha256':{name:digest_file(out/name) for name in ('import_manifest.json','source_preflight.json')},
            'readiness_scope':'Source inventory only; server readiness, initialization, import and live equality are pending',
            'postgresql_connected':False,'target_data_verified':False,'new_model_request_count':0})
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['run_status']=='complete' else 1)


if __name__=='__main__':main()
