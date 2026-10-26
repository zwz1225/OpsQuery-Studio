"""Isolation gates with real files/DuckDB and explicit PG test doubles; no API."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.config import BASE_DIR, settings
from app.datasources import DataSourceRuntime, create_datasource_runtime
from app.datasources.contracts import CatalogSnapshot, SourceIdentity
from app.retrieval import SchemaIndex
from app.security import AccessController
from evaluation.compare_backends import BackendResultComparator, load_data_equivalence
from evaluation.gold_result import resolve_gold_result, gold_result_evidence
from evaluation.gold_sql import gold_selection_identity
from evaluation.regression import RegressionComparator
from evaluation.report_identity import validate_report_identity, require_resumable
from evaluation.result_policy import evidence_digest, result_policy
from evaluation.run_manifest import build_run_manifest, data_digest, EVALUATOR_FILES, _digest
from evaluation.snapshot import BenchmarkSnapshotManager


class D4IsolationTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in (*EVALUATOR_FILES, "app/query.py", "evaluation/cases/cases.jsonl",
                     "data/metrics/metric_catalog.json"):
            p = self.root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(name, encoding="utf-8")
        data = self.root / "data/databases/short_video_ops"
        data.mkdir(parents=True)
        (data / "_schema.json").write_text('{}', encoding="utf-8")
        (data / "users.csv").write_text('user_id\nu1\n', encoding="utf-8")
        self.case = {"case_id": "D4-001", "query": "Monthly values", "scenario": "growth_ops",
            "category": "trend", "query_type": "trend", "difficulty": "simple", "classic": False,
            "gold_sql": "SELECT '2026-01' AS month, 0.125 AS value",
            "gold_sql_by_dialect": {"postgres": "SELECT '2026-01' AS month, 0.125::numeric AS value"},
            "expected_columns": ["month", "value"], "expected_rows": [{"month":"2026-01", "value":0.125}],
            "order_sensitive": True, "order_by_column": "month"}
        self.scope = AccessController().resolve("demo_growth_ops")

    def runtime(self, backend="postgresql", **changes):
        catalog = CatalogSnapshot(json.dumps({"tables": [], "relations": [], "backend": backend}, sort_keys=True))
        source = SourceIdentity("short_video_ops", "short_video_ops_postgres" if backend == "postgresql" else "short_video_ops_duckdb",
            backend, "postgres" if backend == "postgresql" else "duckdb", "PostgreSQL" if backend == "postgresql" else "DuckDB",
            "askdata_ops" if backend == "postgresql" else "main", catalog.version,
            "2"*64 if backend == "postgresql" else data_digest(self.root))
        source = replace(source, **changes)
        executor = Mock(source_identity=source)
        executor.execute.return_value = SimpleNamespace(success=True, columns=self.case["expected_columns"],
            rows=deepcopy(self.case["expected_rows"]), execution_ms=1.0, truncated=False)
        metadata = SimpleNamespace(load_catalog=lambda: catalog, verification={"live_target_verified":True,
            "data_version":source.data_version,"catalog_version":source.catalog_version,"physical_schema_version":"3"*64})
        runtime = DataSourceRuntime(source, catalog, executor, metadata)
        self.addCleanup(runtime.close)
        return runtime

    def manifest(self, runtime, cases=None):
        cases = cases or [self.case]
        return build_run_manifest(cases, base_dir=self.root, mode="gold", scope="all",
            config={"user_roles":["demo_growth_ops"]}, case_source=self.root/"evaluation/cases/cases.jsonl", runtime=runtime)

    def report(self, runtime, cases=None):
        cases = cases or [self.case]
        from tests.test_gold_result import load_runner
        runner = load_runner()
        manifest = self.manifest(runtime,cases)
        rows = []
        for case in cases:
            row = runner.run_gold_case(case, runtime.executor, self.scope, use_cached_gold=False,
                gold_cache_dir=self.root/"cache").to_dict()
            row["run_id"] = manifest["run_id"]
            rows.append(row)
        return {"run_manifest":manifest, "run_status":"complete", "summary":{}, "cases":rows}

    def pair(self):
        duck, pg = self.runtime("duckdb"), self.runtime()
        return self.report(duck),self.report(pg),{"validation_evidence_verified":True,
            "logical_database_id":"short_video_ops","postgres_source_id":pg.identity.source_id,
            "postgres_physical_schema":"askdata_ops","duckdb_data_version":duck.identity.data_version,
            "postgres_data_version":pg.identity.data_version,"postgres_physical_schema_version":"3"*64}

    @staticmethod
    def rehash(report):
        m = report["run_manifest"]
        m["fingerprint"] = _digest({k:v for k,v in m.items() if k not in ("run_id","created_at","fingerprint")})

    def resolve(self, runtime, **kwargs):
        return resolve_gold_result(self.case, runtime.executor, self.scope, cache_dir=self.root/"cache", **kwargs)

    def test_gold_cache_changes_for_permissions_and_result_policy(self):
        runtime = self.runtime()
        self.assertEqual(self.resolve(runtime)["source"], "execution")
        self.assertEqual(self.resolve(runtime)["source"], "cache")
        self.case["column_aliases"] = {"value":["metric_value"]}
        self.assertEqual(self.resolve(runtime)["source"], "execution")
        with patch("evaluation.result_policy.RESULT_POLICY_VERSION", 2):
            self.assertEqual(self.resolve(runtime)["source"], "execution")
        self.scope = AccessController().resolve("demo_admin")
        self.assertEqual(self.resolve(runtime)["source"], "execution")

    def test_gold_cache_changes_for_row_limit_and_normalization_version(self):
        runtime = self.runtime()
        self.resolve(runtime)
        self.assertEqual(self.resolve(runtime,max_result_rows=200)["source"], "execution")
        with patch("evaluation.result_policy.RESULT_NORMALIZATION_VERSION", 2):
            self.assertEqual(self.resolve(runtime,max_result_rows=200)["source"], "execution")

    def test_invalid_duplicate_or_nonfinite_cached_rows_are_regenerated(self):
        runtime = self.runtime()
        for invalid in (lambda p:p.update(columns=["month","month"]),
                        lambda p:p["rows"][0].update(value=float('nan')),
                        lambda p:p.update(rows=[{}])):
            result = self.resolve(runtime)
            path = Path(result["cache_path"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            invalid(payload)
            path.write_text(json.dumps(payload),encoding="utf-8")
            self.assertEqual(self.resolve(runtime)["source"], "execution")

    def test_invalid_row_limit_does_not_execute(self):
        runtime = self.runtime()
        for limit in (0, True, 10001):
            with self.assertRaises(ValueError):self.resolve(runtime,max_result_rows=limit)
        runtime.executor.execute.assert_not_called()

    def test_embedded_gold_evidence_contains_actual_rows_and_valid_hash(self):
        result = self.resolve(self.runtime())
        evidence = gold_result_evidence(result)
        self.assertEqual(evidence['rows'],self.case['expected_rows'])
        self.assertEqual(evidence['result_policy'],result_policy(self.case))
        self.assertEqual(evidence['sha256'],evidence_digest({k:v for k,v in evidence.items() if k!='sha256'}))

    def test_manifest_records_verified_pg_versions_without_csv_dependency(self):
        runtime = self.runtime()
        with patch("evaluation.run_manifest.data_digest",side_effect=AssertionError('PG must not use CSV')):
            m = self.manifest(runtime)
        self.assertEqual(m['manifest_version'],4)
        self.assertTrue(m['source_verification']['live_target_verified'])
        self.assertEqual(m['versions']['result_policy'],_digest(m['result_policy']))

    def test_snapshot_inherits_manifest_and_is_partitioned_by_source(self):
        report = self.report(self.runtime())
        path = BenchmarkSnapshotManager.save(report,mode='gold',scope='all',snapshot_dir=self.root/'snapshots')
        self.assertEqual(path.parent.name,'short_video_ops_postgres')
        snap = BenchmarkSnapshotManager.load(path)
        self.assertEqual(snap['run_manifest'],report['run_manifest'])
        self.assertEqual(snap['cases'][0]['result_metrics']['gold_result_evidence'],report['cases'][0]['result_metrics']['gold_result_evidence'])
        self.assertEqual(validate_report_identity(snap),report['run_manifest'])

    def test_snapshots_same_timestamp_different_sources_do_not_collide(self):
        for backend in ('duckdb','postgresql'):
            report = self.report(self.runtime(backend))
            BenchmarkSnapshotManager.save(report,mode='gold',scope='all',snapshot_dir=self.root/'snapshots',
                created_at=datetime(2026,10,10,tzinfo=timezone.utc))
        self.assertEqual(len(list((self.root/'snapshots').rglob('*.json'))),2)

    def test_snapshot_rejects_relabelled_source_mode_or_dataset(self):
        report = self.report(self.runtime())
        for kwargs in ({'mode':'live'}, {'dataset':{'case_ids':['OTHER']}},
                       {'metadata':{'data_backend':'duckdb'}},
                       {'run_manifest':self.manifest(self.runtime('duckdb'))}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                BenchmarkSnapshotManager.save(report,**{'mode':'gold','scope':'all','snapshot_dir':self.root/'snap',**kwargs})

    def test_report_rejects_trace_source_mismatch(self):
        report = self.report(self.runtime())
        report['cases'][0]['trace']['sql_execution']['source_identity']=self.runtime('duckdb').identity.public()
        with self.assertRaisesRegex(ValueError,'Case source'):validate_report_identity(report)

    def test_report_rejects_invalid_fingerprint_or_verified_versions(self):
        report = self.report(self.runtime())
        bad = deepcopy(report);bad['run_manifest']['fingerprint']='0'*64
        with self.assertRaises(ValueError):validate_report_identity(bad)
        bad = deepcopy(report);bad['run_manifest']['source_verification']['live_target_verified']=False;self.rehash(bad)
        with self.assertRaises(ValueError):validate_report_identity(bad)

    def test_report_rejects_root_relabelling_and_missing_physical_verification(self):
        report = self.report(self.runtime())
        for labels in ({'source_identity': self.runtime('duckdb').identity.public()},
                       {'backend': 'duckdb'}, {'dialect': 'duckdb'}):
            bad = {**report, **labels}
            with self.assertRaises(ValueError):
                validate_report_identity(bad)
        for key in ('physical_schema',):
            bad = deepcopy(report)
            bad['run_manifest']['versions'][key] = None
            bad['run_manifest']['source_verification']['physical_schema_version'] = None
            self.rehash(bad)
            with self.assertRaises(ValueError):
                validate_report_identity(bad)

    def test_cross_backend_rejects_old_gold_evidence_format(self):
        left, right, pair = self.pair()
        evidence = right['cases'][0]['result_metrics']['gold_result_evidence']
        evidence['gold_cache_version'] = 2
        evidence['sha256'] = evidence_digest({k: v for k, v in evidence.items() if k != 'sha256'})
        with self.assertRaisesRegex(ValueError, 'cache format'):
            BackendResultComparator.compare(left, right, [self.case], pair)

    def test_resume_allows_same_source_partial_run(self):
        runtime = self.runtime();report=self.report(runtime);report['cases']=[];report['run_status']='partial'
        self.assertEqual(require_resumable(report,self.manifest(runtime)),report['run_manifest'])

    def test_resume_rejects_changed_source_even_with_same_case_ids(self):
        report=self.report(self.runtime())
        with self.assertRaisesRegex(ValueError,'across datasource'):require_resumable(report,self.manifest(self.runtime('duckdb')))
        with self.assertRaises(ValueError):require_resumable(report,self.manifest(self.runtime(source_id='other_pg')))

    def test_resume_rejects_policy_change_and_duplicate_saved_cases(self):
        runtime=self.runtime();report=self.report(runtime)
        with patch('evaluation.result_policy.RESULT_POLICY_VERSION',2):
            with self.assertRaises(ValueError):require_resumable(report,self.manifest(runtime))
        report['cases'].append(deepcopy(report['cases'][0]))
        with self.assertRaises(ValueError):require_resumable(report,self.manifest(runtime))

    def test_same_source_regression_checks_policy_identity(self):
        runtime=self.runtime();before=self.report(runtime);after=self.report(runtime)
        RegressionComparator.compare(before,after)
        with patch('evaluation.result_policy.RESULT_POLICY_VERSION',2):after=self.report(runtime)
        with self.assertRaises(ValueError):RegressionComparator.compare(before,after)

    def test_cross_backend_reports_are_rejected_by_normal_regression(self):
        left,right,_=self.pair()
        with self.assertRaisesRegex(ValueError,'source_identity differs'):RegressionComparator.compare(left,right)

    def test_cross_backend_comparator_replays_actual_rows(self):
        left,right,equivalence=self.pair()
        result=BackendResultComparator.compare(left,right,[self.case],equivalence)
        self.assertEqual(result['comparison_status'],'passed')
        self.assertEqual(result['pair_pass_count'],1)
        self.assertFalse(result['is_same_source_regression'])

    def test_cross_backend_mismatching_rows_are_not_hidden_by_pass_flags(self):
        left,right,equivalence=self.pair()
        ev=right['cases'][0]['result_metrics']['gold_result_evidence'];ev['rows'][0]['value']=99
        ev['sha256']=evidence_digest({k:v for k,v in ev.items() if k!='sha256'})
        result=BackendResultComparator.compare(left,right,[self.case],equivalence)
        self.assertEqual(result['comparison_status'],'failed')
        self.assertEqual(result['postgres_expected_pass_count'],0)

    def test_cross_backend_rejects_missing_or_corrupt_raw_evidence(self):
        left,right,equivalence=self.pair()
        corrupted=deepcopy(right);corrupted['cases'][0]['result_metrics']['gold_result_evidence']['rows'][0]['value']=99
        with self.assertRaisesRegex(ValueError,'checksum'):BackendResultComparator.compare(left,corrupted,[self.case],equivalence)
        del right['cases'][0]['result_metrics']['gold_result_evidence']
        with self.assertRaisesRegex(ValueError,'Missing embedded'):BackendResultComparator.compare(left,right,[self.case],equivalence)

    def test_cross_backend_rejects_unverified_or_changed_data_pair(self):
        left,right,equivalence=self.pair()
        for key,value in [('validation_evidence_verified',False),('postgres_data_version','9'*64),('duckdb_data_version','8'*64)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                BackendResultComparator.compare(left,right,[self.case],{**equivalence,key:value})

    def test_cross_backend_rejects_wrong_scope_policy_or_sql(self):
        left,right,equivalence=self.pair()
        for key,value in [('scope',{'allowed_tables':[]}),('gold_sql','SELECT 0'),('result_policy',{})]:
            bad=deepcopy(right);ev=bad['cases'][0]['result_metrics']['gold_result_evidence'];ev[key]=value
            ev['sha256']=evidence_digest({k:v for k,v in ev.items() if k!='sha256'})
            with self.subTest(key=key),self.assertRaises(ValueError):BackendResultComparator.compare(left,bad,[self.case],equivalence)

    def test_cross_backend_rejects_different_code_versions(self):
        left,right,equivalence=self.pair();right['run_manifest']['versions']['evaluator']='9'*64;self.rehash(right)
        with self.assertRaisesRegex(ValueError,'versions differ'):BackendResultComparator.compare(left,right,[self.case],equivalence)

    def test_real_accepted_data_equivalence_evidence_is_valid(self):
        pair=load_data_equivalence(BASE_DIR/'evaluation/results/m1_b_postgres_import_server.json',
                                   BASE_DIR/'evaluation/results/m1_b_postgres_validation_server.json')
        self.assertTrue(pair['validation_evidence_verified'])
        self.assertEqual(pair['postgres_data_version'],'882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1')

    def test_index_cache_identity_changes_with_embedding_dimensions_and_source(self):
        runtime=self.runtime('duckdb');model=Mock(enabled=True);model.embed.return_value=[[1.0,0.0]]
        index=SchemaIndex(model,replace(settings,embedding_dimensions=2),self.root/'schema.json',runtime=runtime)
        first=index.index_signature()
        other=SchemaIndex(model,replace(settings,embedding_dimensions=3),self.root/'schema.json',runtime=runtime)
        self.assertNotEqual(first,other.index_signature())
        pg=SchemaIndex(model,replace(settings,embedding_dimensions=2),self.root/'schema.json',runtime=self.runtime())
        self.assertNotEqual(first,pg.index_signature())

    def test_real_index_reuses_matching_store_and_rebuilds_changed_dimensions(self):
        runtime=create_datasource_runtime(replace(settings,data_backend='duckdb',data_source_id='short_video_ops_duckdb'))
        self.addCleanup(runtime.close)
        model=Mock(enabled=True);model.embed.side_effect=lambda texts:[[1.0,0.0] for _ in texts]
        cfg=replace(settings,embedding_dimensions=2)
        indexes=[SchemaIndex(model,cfg,self.root/'index.json',runtime=runtime) for _ in range(2)]
        for index in indexes:index.ensure_built()
        self.assertEqual(model.embed.call_count,1)
        payload=json.loads((self.root/'index.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['cache_identity']['source_identity'],runtime.identity.public())
        changed=SchemaIndex(model,replace(cfg,embedding_dimensions=3),self.root/'index.json',runtime=runtime)
        changed.ensure_built();self.assertEqual(model.embed.call_count,2)

    def test_index_does_not_accept_wrong_identity_even_with_copied_signature(self):
        from app.retrieval.store import LocalSchemaStore
        path=self.root/'store.json';store=LocalSchemaStore(path)
        store.replace_all('same',[],'embedding',cache_identity={'source_id':'other'})
        self.assertFalse(LocalSchemaStore(path).load('same',expected_identity={'source_id':'expected'}))


if __name__ == '__main__':
    unittest.main()
