"""Regression checks for inclusive through-month questions."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from app.database import SCHEMA, RELATIONS
from app.datasources import DataSourceRuntime
from app.datasources.contracts import CatalogSnapshot, SourceIdentity
from app.querying.constraint_planner import ConstraintPlanner
from app.querying.constraint_validator import ConstraintValidator
from app.querying.metric_planner import MetricPlanner


CASES = Path(__file__).resolve().parents[1] / "evaluation/cases/all_cases.jsonl"
GRAPH = {"tables": [{"name": "ad_daily_stats"}]}


class M1EMonthUpperBoundTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {
            case["case_id"]: case
            for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()
            for case in [json.loads(line)]
        }

    def setUp(self) -> None:
        self.planner = ConstraintPlanner()
        self.validator = ConstraintValidator()
        self.metrics = MetricPlanner()

    def check(self, question: str, sql: str):
        metrics = self.metrics.plan(question, GRAPH)
        plan = self.planner.plan_for_sql(question, metrics, GRAPH, sql)
        result = self.validator.validate(sql, "short_video_ops", plan, question)
        return plan, result

    def test_all_existing_through_month_gold_queries_pass(self) -> None:
        for number in (*range(21, 26), *range(71, 76)):
            case = self.cases[f"CHANNEL_OPS-{number:03d}"]
            with self.subTest(case_id=case["case_id"]):
                plan, result = self.check(
                    case["query"], case["gold_sql_by_dialect"]["postgres"]
                )
                self.assertEqual([item["operator"] for item in plan.time_constraints],
                                 ["month_on_or_before"])
                self.assertEqual(result.status, "PASS")

    def test_saved_failure_shape_accepts_next_month_exclusive_bound(self) -> None:
        question = self.cases["CHANNEL_OPS-025"]["query"]
        sql = (
            "WITH monthly_spend AS ("
            "SELECT TO_CHAR(DATE_TRUNC('month', stat_date), 'YYYY-MM') AS month, "
            "SUM(spend) AS total_spend FROM ad_daily_stats "
            "WHERE stat_date < DATE '2026-06-01' "
            "GROUP BY DATE_TRUNC('month', stat_date)) "
            "SELECT month, total_spend FROM monthly_spend ORDER BY month"
        )
        plan, result = self.check(question, sql)
        self.assertEqual(plan.time_constraints[0]["field"], "ad_daily_stats.stat_date")
        self.assertEqual(result.status, "PASS")

    def test_wrong_or_missing_cutoff_stays_blocked(self) -> None:
        question = self.cases["CHANNEL_OPS-025"]["query"]
        predicates = (
            "stat_date < DATE '2026-05-01'",
            "stat_date >= DATE '2026-05-01' AND stat_date < DATE '2026-06-01'",
            "stat_date < DATE '2026-06-01' OR spend > 0",
            "stat_date <= DATE '2026-06-01'",
            "spend >= 0",
        )
        for predicate in predicates:
            with self.subTest(predicate=predicate):
                sql = f"SELECT SUM(spend) FROM ad_daily_stats WHERE {predicate}"
                _, result = self.check(question, sql)
                self.assertEqual(result.status, "BLOCK")
                self.assertEqual(result.missing_constraints[0]["field"],
                                 "ad_daily_stats.stat_date")

    def test_single_month_request_keeps_existing_rule(self) -> None:
        question = "2026-05 每天的广告消耗"
        sql = (
            "SELECT stat_date, SUM(spend) FROM ad_daily_stats "
            "WHERE stat_date >= DATE '2026-05-01' "
            "AND stat_date < DATE '2026-06-01' GROUP BY stat_date"
        )
        plan, result = self.check(question, sql)
        self.assertEqual(plan.time_constraints[0]["operator"], "month_equals")
        self.assertEqual(result.status, "PASS")

    def test_chinese_month_and_cutoff_words(self) -> None:
        sql = (
            "SELECT SUM(spend) FROM ad_daily_stats "
            "WHERE stat_date < DATE '2026-06-01'"
        )
        for question in ("截至2026年5月各月广告消耗", "截止到2026/05各月广告消耗"):
            with self.subTest(question=question):
                plan, result = self.check(question, sql)
                self.assertEqual(plan.time_constraints[0]["operator"],
                                 "month_on_or_before")
                self.assertEqual(result.status, "PASS")

    def test_postgres_runtime_accepts_saved_cutoff_and_gold(self) -> None:
        catalog = CatalogSnapshot(json.dumps({
            "tables": SCHEMA, "relations": RELATIONS,
        }, ensure_ascii=False, sort_keys=True))
        identity = SourceIdentity(
            "short_video_ops", "m1_e_test_postgres", "postgresql", "postgres",
            "PostgreSQL", "askdata_ops", catalog.version, "2" * 64,
        )
        runtime = DataSourceRuntime(
            identity, catalog, Mock(source_identity=identity),
            SimpleNamespace(load_catalog=lambda: catalog),
        )
        try:
            case = self.cases["CHANNEL_OPS-025"]
            candidate = (
                "WITH monthly_spend AS ("
                "SELECT TO_CHAR(DATE_TRUNC('month', stat_date), 'YYYY-MM') AS month, "
                "SUM(spend) AS total_spend FROM askdata_ops.ad_daily_stats "
                "WHERE stat_date < DATE '2026-06-01' "
                "GROUP BY DATE_TRUNC('month', stat_date)) "
                "SELECT month, total_spend FROM monthly_spend ORDER BY month"
            )
            planner = ConstraintPlanner(runtime=runtime)
            validator = ConstraintValidator(runtime=runtime)
            metrics = MetricPlanner(runtime=runtime).plan(case["query"], GRAPH)
            for sql in (candidate, case["gold_sql_by_dialect"]["postgres"]):
                with self.subTest(sql=sql[:40]):
                    plan = planner.plan_for_sql(case["query"], metrics, GRAPH, sql)
                    self.assertEqual(plan.time_constraints[0]["operator"],
                                     "month_on_or_before")
                    self.assertEqual(validator.validate(
                        sql, "short_video_ops", plan, case["query"],
                    ).status, "PASS")
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
