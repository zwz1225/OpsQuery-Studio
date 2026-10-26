"""Full coverage, immutable first79, approved syntax changes and E2E Gold gates."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import sqlglot
from sqlglot import exp

from app.config import BASE_DIR
from app.database import SCHEMA
from app.datasources.sql_policy import validate_readonly_sql
from app.security import AccessController
from evaluation.gold_sql import select_gold_sql,GoldSqlSelectionError,gold_selection_identity
from evaluation.run_e2e import load_e2e_cases
from scripts.audit_m1_d3_gold430 import (
    audit,BEFORE_PATH,FULL_LIST_PATH,REMAINING_LIST_PATH,FULL_REVIEW_PATH,
    ACCEPTED_D3_CASES_PATH,
)
from scripts.audit_m1_d3_gold79 import (
    BASELINE_PATH,CASE_PATH,POSTGRES_SOURCE,check_variant,load_rows,load_types,sha256,
)
from scripts.check_m1_d3_duckdb_compatibility import diagnostic_sql


class D3Gold430Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = {c['case_id']:c for c in load_rows(ACCEPTED_D3_CASES_PATH)}
        cls.originals = {c['case_id']:c for c in load_rows(BASELINE_PATH)}
        cls.records = {r['case_id']:r for r in json.loads(FULL_REVIEW_PATH.read_text(encoding='utf-8'))['cases']}
        cls.types = load_types()

    def reject_variant_change(self,cid,transform):
        case,record=deepcopy(self.current[cid]),deepcopy(self.records[cid])
        case['gold_sql_by_dialect']['postgres']=transform(case['gold_sql_by_dialect']['postgres'])
        record['postgres_sql_sha256']=sha256(case['gold_sql_by_dialect']['postgres'])
        with self.assertRaises(ValueError):check_variant(self.originals[cid],case,record,self.types)

    def test_full430_audit_and_first79_bytes_preserved(self):
        r=audit()
        self.assertEqual((r['reviewed_case_count'],r['new_variant_count'],r['first79_byte_preserved_count']),(430,351,79))
        self.assertEqual(r['unchanged_expected_and_scoring_case_count'],430)
        self.assertFalse(r['postgres_execution_verified'])

    def test_full_and_remaining_lists_are_exact_ordered_partitions(self):
        full=json.loads(FULL_LIST_PATH.read_text(encoding='utf-8'))['case_ids']
        remaining=json.loads(REMAINING_LIST_PATH.read_text(encoding='utf-8'))['case_ids']
        before=load_rows(BEFORE_PATH)
        self.assertEqual(full,list(self.current))
        self.assertEqual(remaining,[c['case_id'] for c in before if not c.get('gold_sql_by_dialect')])
        self.assertEqual(remaining,list(self.records))

    def test_all430_select_explicit_pg_and_keep_original_duckdb_sql(self):
        for cid,case in self.current.items():
            with self.subTest(cid=cid):
                self.assertEqual(select_gold_sql(case,POSTGRES_SOURCE).selection_key,'gold_sql_by_dialect.postgres')
                self.assertEqual(select_gold_sql(case).sql,self.originals[cid]['gold_sql'])

    def test_missing_new_variant_cannot_fall_back_to_original_or_expected(self):
        case=deepcopy(self.current['GROWTH_OPS-091']);del case['gold_sql_by_dialect']
        with self.assertRaises(GoldSqlSelectionError):select_gold_sql(case,POSTGRES_SOURCE)

    def test_every_original_result_alias_and_scoring_field_is_frozen(self):
        for cid,case in self.current.items():
            self.assertEqual({k:v for k,v in case.items() if k!='gold_sql_by_dialect'},self.originals[cid])

    def test_remaining_changes_are_explicit_numeric_and_bigint(self):
        totals={k:0 for k in ('integer_truth_tests','round_numeric_cast_count','floating_division_count')}
        for record in self.records.values():
            for key in totals:
                value=record['changes'][key];totals[key]+=len(value) if isinstance(value,list) else value
            for flag in record['changes']['integer_truth_tests']:
                self.assertEqual(self.types[flag['table']][flag['column']],'bigint')
            tree=sqlglot.parse_one(self.current[record['case_id']]['gold_sql_by_dialect']['postgres'],read='postgres')
            self.assertTrue(all(n.this.args['to'].this==exp.DataType.Type.DECIMAL for n in tree.find_all(exp.Round)))
            self.assertTrue(all(n.this.args['to'].this==exp.DataType.Type.DOUBLE for n in tree.find_all(exp.Div)))
        self.assertEqual(totals,{'integer_truth_tests':78,'round_numeric_cast_count':235,'floating_division_count':136})

    def test_new_month_filter_change_rejected_with_refreshed_hash(self):
        self.reject_variant_change('GROWTH_OPS-052',lambda s:s.replace('2026-02','2026-03'))

    def test_new_nonzero_truth_cannot_be_narrowed_to_one(self):
        self.reject_variant_change('GROWTH_OPS-091',lambda s:s.replace('is_valid_active <> 0','is_valid_active = 1'))

    def test_new_limit_change_and_null_order_change_rejected(self):
        self.reject_variant_change('CONTENT_OPS-021',lambda s:s.replace('LIMIT 10','LIMIT 20'))
        self.reject_variant_change('CONTENT_OPS-021',lambda s:s.replace('NULLS LAST','NULLS FIRST'))

    def test_unrounded_cte_gap_and_window_guards_preserved(self):
        tree=sqlglot.parse_one(self.current['GROWTH_OPS-141']['gold_sql_by_dialect']['postgres'],read='postgres')
        gap=next(n for n in tree.find_all(exp.Alias) if n.alias=='gap')
        self.assertIsInstance(gap.this.this.this,exp.Sub)
        self.assertFalse(list(gap.this.this.this.find_all(exp.Round)))
        tree=sqlglot.parse_one(self.current['CHANNEL_OPS-021']['gold_sql_by_dialect']['postgres'],read='postgres')
        self.assertEqual(len(list(tree.find_all(exp.Lag))),2)
        self.assertEqual(len(list(tree.find_all(exp.Nullif))),1)

    def test_numeric_diagnostic_never_changes_persisted_postgres_sql(self):
        sql=self.current['CHANNEL_OPS-052']['gold_sql_by_dialect']['postgres']
        rendered=diagnostic_sql(sql)
        self.assertIn('DECIMAL(38, 15)',rendered)
        self.assertEqual(self.current['CHANNEL_OPS-052']['gold_sql_by_dialect']['postgres'],sql)

    def test_changed_first79_snapshot_or_extra_variants_are_rejected(self):
        rows=load_rows(ACCEPTED_D3_CASES_PATH);rows[0]['gold_sql_by_dialect']['postgres']+=' LIMIT 1'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.jsonl'
            path.write_text('\n'.join(json.dumps(c,ensure_ascii=False) for c in rows)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError):audit(cases_path=path)

    def test_pg_behavior_cases_have_explicit_scored_gold_only(self):
        path=BASE_DIR/'evaluation/cases/e2e_behavior_postgres.json'
        cases=load_e2e_cases(path)
        selected=gold_selection_identity(cases,POSTGRES_SOURCE)
        self.assertEqual(len(cases),8)
        # Both scored cases have explicit SQL. Non-scored behavior cases need no invented Gold.
        for case in cases:
            if case.get('score_result') is not False:
                self.assertEqual(select_gold_sql(case,POSTGRES_SOURCE).selection_key,'gold_sql_by_dialect.postgres')
        empty=next(c for c in cases if c['case_id']=='E2E-EMPTY-RESULT')
        self.assertEqual(empty['gold_sql_by_dialect']['postgres'],empty['gold_sql'])
        validate_readonly_sql('short_video_ops',empty['gold_sql_by_dialect']['postgres'],SCHEMA,
            AccessController().resolve('demo_growth_ops'),dialect='postgres',physical_schema='askdata_ops')

    def test_pg_behavior_specs_preserve_all_original_expectations(self):
        old=json.loads((BASE_DIR/'evaluation/cases/e2e_behavior.json').read_text(encoding='utf-8'))['cases']
        new=json.loads((BASE_DIR/'evaluation/cases/e2e_behavior_postgres.json').read_text(encoding='utf-8'))['cases']
        self.assertEqual([{k:v for k,v in c.items() if k!='gold_sql_by_dialect'} for c in new],old)


if __name__=='__main__':unittest.main()
