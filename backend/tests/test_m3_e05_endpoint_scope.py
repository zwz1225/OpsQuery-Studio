"""Public evidence ownership and endpoint-scope boundaries for E05 offline work."""
import unittest

from evaluation.bird.endpoint_scope import public_contract, observe_sql


def public(question, evidence, *, case_id="BIRD-PG-0239", database_id="toxicology"):
    return {"case_id": case_id, "database_id": database_id, "dialect": "postgres",
            "question": question, "evidence": evidence}


TABLES = [
    {"database_id": "toxicology", "name": "connected",
     "columns": [{"name": n} for n in ("atom_id", "atom_id2", "bond_id")]},
    {"database_id": "toxicology", "name": "bond",
     "columns": [{"name": n} for n in ("bond_id", "molecule_id")]},
]
EVIDENCE = "connections refers to bond_id; atom 19 refers to atom_id like 'TR%_19';"


class EndpointScopeTest(unittest.TestCase):
    def test_explicit_single_endpoint_detects_broadened_or(self):
        p = public("How many connections does the atom 19 have?", EVIDENCE)
        contract = public_contract(p, TABLES)
        self.assertEqual(contract["enforcement"], "advisory_only")
        self.assertEqual(contract["predicate_field_id"], "toxicology.connected.atom_id")
        self.assertEqual(contract["metric_field_id"], "toxicology.connected.bond_id")
        widened = "SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'"
        self.assertEqual([issue["code"] for issue in observe_sql(contract, widened)],
                         ["explicit_endpoint_widened_by_or"])

    def test_preserved_endpoint_and_unrelated_sql_are_not_flagged(self):
        contract = public_contract(public("How many connections does the atom 19 have?", EVIDENCE), TABLES)
        for sql in (
            "SELECT COUNT(bond_id) FROM connected WHERE atom_id LIKE 'TR%_19'",
            "SELECT COUNT(*) FROM connected c WHERE c.atom_id LIKE 'TR%_19'",
            "SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' AND atom_id2 IS NOT NULL",
        ):
            with self.subTest(sql=sql):
                self.assertEqual(observe_sql(contract, sql), [])

    def test_generic_renamed_schema_uses_public_and_authorized_fields(self):
        tables = [{"database_id": "demo", "name": "links",
                   "fields": [{"name": n} for n in ("first_key", "second_key", "link_id")]}]
        p = public("How many links does node 7 have?",
                   "links refers to link_id; node 7 refers to first_key like 'X%_7'",
                   database_id="demo")
        contract = public_contract(p, tables)
        self.assertEqual(contract["predicate_field_id"], "demo.links.first_key")
        self.assertEqual(observe_sql(contract,
            "SELECT COUNT(*) FROM links WHERE first_key LIKE 'X%_7' OR second_key LIKE 'X%_7'")[0]["code"],
            "explicit_endpoint_widened_by_or")

    def test_ambiguous_owner_does_not_bind_or_flag(self):
        p = public("How many connections does the atom 19 have?", EVIDENCE)
        other = {"database_id": "toxicology", "name": "other_connections",
                 "columns": [{"name": "atom_id"}, {"name": "bond_id"}]}
        contract = public_contract(p, TABLES + [other])
        self.assertEqual(contract["basis"], "ambiguous_or_missing_authorized_owner")
        self.assertEqual(observe_sql(contract,
            "SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'"), [])

    def test_missing_public_role_and_explicit_two_endpoints_are_not_bound(self):
        for evidence in (
            "atom 19 refers to atom_id like 'TR%_19'",
            "connections refers to bond_id; atom 19 refers to atom_id or atom_id2 like 'TR%_19'",
            "connections refers to bond_id; atom 19 may refer to atom_id like 'TR%_19'",
            "connections refers to bond_id; atom 19 refers to atom_id like '%'",
        ):
            with self.subTest(evidence=evidence):
                contract = public_contract(public("How many connections does the atom 19 have?", evidence), TABLES)
                self.assertNotIn("predicate_field_id", contract)

    def test_bond_atoms_and_city_questions_are_outside_this_candidate(self):
        cases = (
            public("What elements are in the TR004_8_9 bond atoms?",
                   "TR004_8_9 bond atoms refers to bond_id = 'TR004_8_9';"),
            public("How many students are enrolled in Fremont?",
                   "State Special School means EdOpsCode = 'SSS'", database_id="california_schools"),
        )
        for p in cases:
            self.assertEqual(public_contract(p, TABLES)["enforcement"], "none")

    def test_case_id_does_not_choose_rule_and_private_fields_are_rejected(self):
        p = public("How many connections does the atom 19 have?", EVIDENCE)
        original = public_contract(p, TABLES)
        changed = public_contract({**p, "case_id": "BIRD-PG-8888"}, TABLES)
        self.assertEqual(original, changed)
        with self.assertRaises(ValueError):
            public_contract({**p, "gold_sql": "SELECT 1"}, TABLES)


if __name__ == "__main__":
    unittest.main()
