"""Positive and negative public-input boundaries for the offline E04 probe."""
import unittest

from evaluation.bird.scalar_count_shape import public_contract, shape_issues


def public(question: str, evidence: str = "") -> dict:
    return {"case_id": "BIRD-PG-0092", "database_id": "financial", "dialect": "postgres",
            "question": question, "evidence": evidence}


class ScalarCountShapeTest(unittest.TestCase):
    def test_0092_outer_group_rejected_without_reference_answer(self):
        p = public("List out the no. of districts that have female average salary is more than 6000 but less than 10000?",
                   "A11 refers to average salary; Female mapps to gender = 'F'")
        contract = public_contract(p)
        self.assertEqual(contract["enforcement"], "hard_for_simple_outer_select")
        grouped = ("SELECT COUNT(DISTINCT d.district_id) FROM district d "
                   "JOIN client c ON d.district_id=c.district_id WHERE c.gender='F' "
                   "GROUP BY d.district_id,d.a11 HAVING d.a11>6000 AND d.a11<10000")
        self.assertEqual([i["code"] for i in shape_issues(contract, grouped)],
                         ["scalar_count_outer_group"])
        scalar = ("SELECT COUNT(DISTINCT d.district_id) FROM district d "
                  "JOIN client c ON d.district_id=c.district_id "
                  "WHERE c.gender='F' AND d.a11>6000 AND d.a11<10000")
        self.assertEqual(shape_issues(contract, scalar), [])

    def test_grouped_eligibility_subquery_is_allowed(self):
        contract = public_contract(public("How many districts have at least three clients?"))
        sql = ("WITH eligible AS (SELECT district_id FROM client GROUP BY district_id "
               "HAVING COUNT(*)>=3) SELECT COUNT(*) FROM eligible")
        self.assertEqual(shape_issues(contract, sql), [])

    def test_explicit_group_and_detail_requests_remain_advisory(self):
        for question in (
            "How many districts per region?",
            "List each district and its number of clients",
            "How many clients by year?",
            "How many districts? Also list their names.",
            "How many districts? List the number of clients too?",
        ):
            with self.subTest(question=question):
                contract = public_contract(public(question))
                self.assertNotEqual(contract["enforcement"], "hard_for_simple_outer_select")
                self.assertEqual(shape_issues(contract, "SELECT district_id,COUNT(*) FROM client GROUP BY district_id"), [])

    def test_rank_average_difference_and_contact_number_are_not_scalar_counts(self):
        for question in (
            "Which district has the highest number of clients?",
            "What is the average number of crimes per region?",
            "How many more SMEs pay in CZK than EUR?",
            "Give the full name and contact number of members",
        ):
            with self.subTest(question=question):
                self.assertNotEqual(public_contract(public(question))["enforcement"],
                                    "hard_for_simple_outer_select")

    def test_public_identity_only_and_single_output(self):
        p = public("How many cards have infinite power?")
        old = public_contract(p)
        p["case_id"] = "BIRD-PG-8888"
        self.assertEqual(old, public_contract(p))
        self.assertEqual([i["code"] for i in shape_issues(old,
            "SELECT category,COUNT(*) FROM cards GROUP BY category")],
            ["scalar_count_outer_group", "scalar_count_multiple_outputs"])
        with self.assertRaises(ValueError):
            public_contract({**p, "gold_sql": "SELECT 1"})

    def test_single_count_phrasings_and_aggregate_implementation_are_allowed(self):
        for question in (
            "HOW MANY districts have at least three clients?",
            "Show the number of qualifying districts.",
            "Return the count of active accounts",
            "List out the no. of eligible districts?",
        ):
            with self.subTest(question=question):
                contract = public_contract(public(question))
                self.assertEqual(contract["enforcement"], "hard_for_simple_outer_select")
                self.assertEqual(shape_issues(contract, "SELECT SUM(active_flag) FROM accounts"), [])
                self.assertEqual(shape_issues(contract, "SELECT COUNT(*) FROM eligible"), [])

    def test_question_or_evidence_explicit_multi_output_is_never_hard(self):
        cases = (
            ("How many districts and their names?", ""),
            ("How many districts and what are their names?", ""),
            ("How many districts and their IDs?", ""),
            ("How many districts? Show the names as well.", ""),
            ("How many districts?", "Report the results for each region."),
            ("How many districts?", "Output the count grouped by year."),
            ("How many districts?", "Show the result per province."),
        )
        for question, evidence in cases:
            with self.subTest(question=question, evidence=evidence):
                contract = public_contract(public(question, evidence))
                self.assertNotEqual(contract["enforcement"], "hard_for_simple_outer_select")
                self.assertEqual(shape_issues(contract, "SELECT region,COUNT(*) FROM t GROUP BY region"), [])

    def test_sql_shape_uses_outer_select_only_and_does_not_rewrite_sql(self):
        contract = public_contract(public("How many districts have at least three clients?"))
        for sql in (
            "SELECT COUNT(*) FROM (SELECT district_id FROM client GROUP BY district_id HAVING COUNT(*)>=3) x",
            "SELECT COUNT(*) FROM (SELECT a,COUNT(*) FROM t GROUP BY a) x",
        ):
            with self.subTest(sql=sql):
                self.assertEqual(shape_issues(contract, sql), [])
        self.assertEqual([i["code"] for i in shape_issues(contract,
            "SELECT region, COUNT(*) FROM t GROUP BY region")],
            ["scalar_count_outer_group", "scalar_count_multiple_outputs"])
        self.assertEqual(shape_issues(contract, "SELECT FROM"), [])


if __name__ == "__main__":
    unittest.main()
