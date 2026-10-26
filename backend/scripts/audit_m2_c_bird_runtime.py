"""Offline source/catalog/policy audit. Never connects to PostgreSQL or models."""
import argparse
from pathlib import Path

from scripts.m2_b_common import PROTOCOL_DIR,digest_json,require
from scripts.m2_b_target import journal
from scripts.m2_b_structure import expectations
from evaluation.bird.evidence import Evidence,DEFAULT_DATA,DEFAULT_RESULTS,DATA_VERSION,scorer_gold,public_cases
from evaluation.bird.runtime import BirdRuntime
from evaluation.bird.sql import validate_sql
from evaluation.bird.manifest import code_binding,source_binding


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=DEFAULT_DATA)
    parser.add_argument('--results-dir',type=Path,default=DEFAULT_RESULTS)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with journal(args.output,'M2 C offline source/catalog/SQL policy audit',protected=[args.data_root,PROTOCOL_DIR]) as report:
        evidence=Evidence.load(args.data_root,args.results_dir);expected=expectations(evidence.manifest)
        report.update(source_binding=source_binding(evidence),code_binding=code_binding(),domains=[])
        for db in evidence.manifest['query_domains']:
            context=object.__new__(BirdRuntime);context.evidence=evidence;context.database_id=db
            context.domain=evidence.domain(db);context.tables=evidence.tables(db);context.names=set(context.domain['tables']);context.expected=expected
            context._descriptions,context.description_diagnostic=evidence.descriptions(db)
            columns={t['name']:evidence.validation['structure']['verified_structure']['columns'][t['name']] for t in context.tables}
            catalog=context._catalog(columns)
            require({t['name'] for t in catalog.tables}==context.names,'Offline catalog has a foreign table')
            typed={t['name']:t['target'] for t in evidence.validation['tables'] if t['database_id']==db}
            report['domains'].append({'database_id':db,'query_role':context.domain['query_role'],'table_count':len(catalog.tables),
                'field_count':sum(len(t['fields']) for t in catalog.tables),'authorized_catalog_version':catalog.version,
                'authorized_data_version':digest_json({'accepted_data_version':DATA_VERSION,'database_id':db,'tables':typed,'digest_policy':'m2_copy_native_typed_multiset_v1'}),
                'description_diagnostic':context.description_diagnostic,'catalog_origin':'Previously accepted M2 B structure; no fresh runtime connection'})
        gold=scorer_gold()
        for row in gold.values():require(validate_sql(row['gold_sql'],set(evidence.domain(row['database_id'])['tables']))==row['gold_sql'],'Gold SQL was rewritten')
        report.update(run_status='complete',runtime_available=False,live_target_verified=False,gold110_ready=False,
            summary={'logical_database_count':11,'table_count':sum(d['table_count'] for d in report['domains']),
                'field_count':sum(d['field_count'] for d in report['domains']),'gold_sql_policy_checked_count':len(gold),
                'description_unmatched_row_count':sum(len(d['description_diagnostic']['unmatched_columns']) for d in report['domains']),
                'public_input_counts':{split:len(public_cases(split)) for split in ('smoke8','development80','holdout30')}},
            verification_scope='Offline assembly, frozen inputs and read-query policy only. Linux isolation, live PostgreSQL domain verification and Gold execution remain pending.')
    raise SystemExit(0 if report['run_status']=='complete' else 1)


if __name__=='__main__':main()
