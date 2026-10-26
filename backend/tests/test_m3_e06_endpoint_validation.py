"""Public-only E06 endpoint feedback boundaries; no model or database calls."""
from __future__ import annotations

import unittest
import json
from types import SimpleNamespace

from evaluation.bird.endpoint_validation import inspect
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.repair import FEEDBACK_BYTES, RepairSession


TABLES = [{"database_id": "toxicology", "id": "toxicology.connected",
           "name": "connected", "fields": [{"name": name} for name in
               ("atom_id", "atom_id2", "bond_id")]},
          {"database_id": "toxicology", "id": "toxicology.atom",
           "name": "atom", "fields": [{"name": name} for name in ("atom_id", "element")]}]
PUBLIC = {"case_id": "BIRD-PG-0239", "database_id": "toxicology", "dialect": "postgres",
          "question": "How many connections does the atom 19 have?",
          "evidence": "connections refers to bond_id; atom 19 refers to atom_id like 'TR%_19';"}
WIDENED = "SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'"


class EndpointValidationTest(unittest.TestCase):
    def test_observed_0239_gets_explainable_bounded_feedback(self):
        result = inspect(PUBLIC, TABLES, WIDENED)
        self.assertEqual(result["status"], "candidate_repair")
        self.assertEqual(result["enforcement"], "offline_proposal_only")
        feedback = result["feedback"]
        self.assertEqual(feedback["named_filter_field_id"], "toxicology.connected.atom_id")
        self.assertEqual(feedback["additional_filter_field_id"], "toxicology.connected.atom_id2")
        self.assertEqual(feedback["metric_field_id"], "toxicology.connected.bond_id")
        self.assertEqual(feedback["pattern"], "TR%_19")
        self.assertNotIn("gold", str(result).casefold())
        self.assertNotIn("377", str(result))

    def test_correct_endpoint_and_unrelated_second_field_are_not_rejected(self):
        for sql in (
            "SELECT COUNT(bond_id) FROM connected WHERE atom_id LIKE 'TR%_19'",
            "SELECT COUNT(*) AS n FROM public.connected c WHERE c.atom_id LIKE 'TR%_19'",
            "SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' AND atom_id2 IS NOT NULL",
        ):
            with self.subTest(sql=sql):
                self.assertNotEqual(inspect(PUBLIC, TABLES, sql)["status"], "candidate_repair")

    def test_actual_0206_two_endpoint_query_stays_outside_rule(self):
        public = {"case_id": "BIRD-PG-0206", "database_id": "toxicology", "dialect": "postgres",
                  "question": "What elements are in the TR004_8_9 bond atoms?",
                  "evidence": "TR004_8_9 bond atoms refers to bond_id = 'TR004_8_9';"}
        sql = ("SELECT DISTINCT a.element FROM connected c JOIN atom a ON c.atom_id = a.atom_id "
               "WHERE c.bond_id = 'TR004_8_9' UNION SELECT DISTINCT a2.element FROM connected c2 "
               "JOIN atom a2 ON c2.atom_id2 = a2.atom_id WHERE c2.bond_id = 'TR004_8_9'")
        self.assertEqual(inspect(public, TABLES, sql)["status"], "abstain")

    def test_explicit_bilateral_question_overrides_single_field_evidence(self):
        for question in ("How many connections does atom 19 have at either endpoint?",
                         "How many connections does atom 19 have at both ends?"):
            with self.subTest(question=question):
                result = inspect({**PUBLIC, "question": question}, TABLES, WIDENED)
                self.assertEqual(result["status"], "abstain")
                self.assertEqual(result["reason_code"], "question_explicitly_mentions_multiple_endpoints")

    def test_complex_sql_or_unsupported_filter_is_not_hard_feedback(self):
        queries = (
            "SELECT COUNT(*) FROM connected c JOIN atom a ON c.atom_id=a.atom_id WHERE c.atom_id LIKE 'TR%_19' OR c.atom_id2 LIKE 'TR%_19'",
            "WITH q AS (SELECT * FROM connected) SELECT COUNT(*) FROM q WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'",
            "SELECT COUNT(*) FROM connected WHERE (atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19') AND bond_id IS NOT NULL",
            "SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_20'",
            "SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'",
            "SELECT COUNT(*) FROM connected WHERE atom_id2 LIKE 'TR%_19'",
            WIDENED + "; SELECT 1",
        )
        for sql in queries:
            with self.subTest(sql=sql):
                self.assertNotEqual(inspect(PUBLIC, TABLES, sql)["status"], "candidate_repair")

    def test_unknown_or_ambiguous_field_owner_does_not_generate_feedback(self):
        changed = [{**TABLES[0], "fields": [{"name": "atom_id"}, {"name": "bond_id"}]}, TABLES[1]]
        self.assertEqual(inspect(PUBLIC, changed, WIDENED)["status"], "abstain")
        duplicate = {**TABLES[0], "id": "toxicology.other", "name": "other"}
        self.assertEqual(inspect(PUBLIC, TABLES + [duplicate], WIDENED)["status"], "abstain")

    def test_renamed_authorized_schema_and_case_id_independence(self):
        tables = [{"database_id": "demo", "id": "demo.links", "name": "links",
                   "columns": [{"name": name} for name in ("first_key", "second_key", "link_id")]}]
        public = {"case_id": "BIRD-PG-9999", "database_id": "demo", "dialect": "postgres",
                  "question": "How many links does node 7 have?",
                  "evidence": "links refers to link_id; node 7 refers to first_key like 'X%_7'"}
        sql = "SELECT COUNT(*) FROM links WHERE first_key LIKE 'X%_7' OR second_key LIKE 'X%_7'"
        self.assertEqual(inspect(public, tables, sql)["status"], "candidate_repair")
        self.assertEqual(inspect({**public, "case_id": "BIRD-PG-8888"}, tables, sql)["feedback"],
                         inspect(public, tables, sql)["feedback"])
        with self.assertRaises(ValueError):
            inspect({**public, "gold_sql": "SELECT 1"}, tables, sql)

    def test_existing_repair_channel_carries_reason_and_blocks_repeat(self):
        proposal = inspect(PUBLIC, TABLES, WIDENED)
        tables = [{**table, "database": "toxicology"} for table in TABLES]
        runtime = SimpleNamespace(catalog=SimpleNamespace(tables=tables),
                                  identity=SimpleNamespace(public=lambda: {
                                      "logical_database_id": "toxicology",
                                      "source_id": "bird_mini_dev_postgres_toxicology",
                                      "backend": "postgresql", "physical_schema": "public"}))
        session = RepairSession(runtime, public_input=PUBLIC)
        failure = BirdFailure("intent_contract_violation")
        failure._intent_violations = [proposal["feedback"]]
        feedback = session.feedback(failure, WIDENED)
        self.assertTrue(feedback["retryable"])
        self.assertEqual(feedback["intent_violations"][0]["code"],
                         "explicit_endpoint_widened_by_or")
        self.assertIn("atom_id2", feedback["intent_violations"][0]["additional_filter_field_id"])
        self.assertLessEqual(len(json.dumps(feedback, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")), FEEDBACK_BYTES)
        session.remember(failure, WIDENED)
        repeated, repeated_feedback = session.repeated(WIDENED)
        self.assertEqual(repeated.category, "repeated_invalid_sql")
        self.assertFalse(repeated_feedback["retryable"])


if __name__ == "__main__":
    unittest.main()
