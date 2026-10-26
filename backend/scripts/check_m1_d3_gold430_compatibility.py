"""Execute originals and rendered variants in DuckDB; never PG acceptance."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from app.config import BASE_DIR
from app.querying.duckdb_engine import DuckDbEngine
from app.security import AccessController
from evaluation.run_manifest import data_digest
from evaluation.run_benchmark import compare_results_strict
from evaluation.gold_sql import select_gold_sql
from scripts.check_m1_d3_duckdb_compatibility import diagnostic_sql, compare
from scripts.audit_m1_d3_gold430 import audit
from scripts.audit_m1_d3_gold79 import CASE_PATH, BASELINE_PATH, POSTGRES_SOURCE, load_rows, require, sha256


def check():
    provenance = audit()
    version = data_digest(BASE_DIR)
    originals = {c['case_id']:c for c in load_rows(BASELINE_PATH)}
    current = load_rows(CASE_PATH)
    engine, controller = DuckDbEngine(), AccessController()
    results = []
    started = time.perf_counter()
    try:
        with engine.connect('short_video_ops') as connection:
            def execute(sql, scope):
                cursor = connection.execute(engine._validate_sql('short_video_ops',sql,scope))
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchmany(10001)
                require(len(rows)<=10000, 'Scoring result was truncated')
                return columns,[{c:engine._json_value(v) for c,v in zip(columns,row)} for row in rows]
            for index,case in enumerate(current,1):
                original = originals[case['case_id']]
                scope = controller.resolve(f"demo_{case['scenario']}")
                pg_sql = select_gold_sql(case,POSTGRES_SOURCE).sql
                rendered = diagnostic_sql(pg_sql)
                old_cols,old_rows = execute(original['gold_sql'],scope)
                new_cols,new_rows = execute(rendered,scope)
                old_ok,old_reason = compare(old_cols,old_rows,original)
                new_ok,new_reason = compare(new_cols,new_rows,original)
                pair_ok,pair_reason = compare_results_strict(new_cols,new_rows,old_cols,old_rows,
                    original.get('order_sensitive',True),order_by_column=original.get('order_by_column'),
                    column_aliases=original.get('column_aliases'),
                    allowed_auxiliary_columns=original.get('allowed_auxiliary_columns'),
                    top_n_tie_policy=original.get('top_n_tie_policy'))
                row = {'case_id':case['case_id'],'original_strict_correct':old_ok,
                    'rendered_variant_strict_correct':new_ok,'pair_strict_correct':pair_ok,
                    'original_reason':old_reason,'variant_reason':new_reason,'pair_reason':pair_reason,
                    'original_row_count':len(old_rows),'variant_row_count':len(new_rows),
                    'postgres_sql_sha256':sha256(pg_sql),'diagnostic_duckdb_sql':rendered}
                if not all((old_ok,new_ok,pair_ok)):
                    row.update(original_rows=old_rows,variant_rows=new_rows)
                results.append(row)
                if index%25==0 or index==len(current) or not all((old_ok,new_ok,pair_ok)):
                    print(f"[{index}/430] {case['case_id']} original={old_ok} rendered={new_ok} pair={pair_ok}",flush=True)
    finally:
        engine.close()
    require(data_digest(BASE_DIR)==version,'CSV inputs changed during diagnostics')
    passed = sum(all((r['original_strict_correct'],r['rendered_variant_strict_correct'],r['pair_strict_correct'])) for r in results)
    return {'stage':'M1 D3 full430 local DuckDB compatibility diagnostics',
        'run_status':'complete' if passed==430 else 'failed','case_count':len(results),'pass_count':passed,
        'original_strict_pass_count':sum(r['original_strict_correct'] for r in results),
        'rendered_variant_strict_pass_count':sum(r['rendered_variant_strict_correct'] for r in results),
        'pair_strict_pass_count':sum(r['pair_strict_correct'] for r in results),
        'elapsed_seconds':round(time.perf_counter()-started,3),'recorded_at':datetime.now(timezone.utc).isoformat(),
        'data_version':version,'dataset_sha256':provenance['dataset_sha256'],
        'actual_execution_backend':'duckdb','postgresql_connected':False,'postgres_execution_verified':False,
        'new_model_request_count':0,'numeric_emulation':'Diagnostic DECIMAL(38,15); not PostgreSQL rounding proof',
        'cases':results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    require(not args.output.exists(),'Output exists; choose an independent filename')
    result = check()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))
    if result['run_status']!='complete':raise SystemExit(1)


if __name__=='__main__':main()
