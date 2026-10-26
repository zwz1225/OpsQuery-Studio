from __future__ import annotations

import unittest

from evaluation.run_benchmark import compare_results


class CompareResultsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.expected_columns = ["channel", "user_count"]
        self.expected_rows = [
            {"channel": "A", "user_count": 100},
            {"channel": "B", "user_count": 200},
        ]

    def test_order_sensitive_accepts_rows_in_expected_order(self) -> None:
        correct, column_match, reason = compare_results(
            self.expected_columns,
            self.expected_rows,
            self.expected_columns,
            self.expected_rows,
            order_sensitive=True,
        )

        self.assertTrue(correct)
        self.assertTrue(column_match)
        self.assertEqual(reason, "结果一致")

    def test_order_sensitive_rejects_reordered_rows(self) -> None:
        actual_rows = [self.expected_rows[1], self.expected_rows[0]]

        correct, column_match, reason = compare_results(
            self.expected_columns,
            actual_rows,
            self.expected_columns,
            self.expected_rows,
            order_sensitive=True,
        )

        self.assertFalse(correct)
        self.assertTrue(column_match)
        self.assertEqual(reason, "返回数据与标准结果不一致")

    def test_order_insensitive_accepts_reordered_rows(self) -> None:
        actual_rows = [self.expected_rows[1], self.expected_rows[0]]

        correct, column_match, reason = compare_results(
            self.expected_columns,
            actual_rows,
            self.expected_columns,
            self.expected_rows,
            order_sensitive=False,
        )

        self.assertTrue(correct)
        self.assertTrue(column_match)
        self.assertEqual(reason, "结果一致")

    def test_float_tolerance_is_preserved(self) -> None:
        correct, _, _ = compare_results(
            ["ratio"],
            [{"ratio": 1.00002}],
            ["ratio"],
            [{"ratio": 1.00001}],
            order_sensitive=True,
        )

        self.assertTrue(correct)

    def test_duration_is_not_treated_as_ratio(self) -> None:
        correct, _, _ = compare_results(
            ["content_category", "content_count", "avg_video_duration"],
            [{"content_category": "comedy", "content_count": 1059,
              "avg_video_duration": 96.7610953729934}],
            ["category_name", "contents", "avg_duration_seconds"],
            [{"category_name": "comedy", "contents": 1059,
              "avg_duration_seconds": 96.76}],
            order_sensitive=False,
        )

        self.assertTrue(correct)

    def test_rate_still_uses_four_decimal_places(self) -> None:
        correct, _, _ = compare_results(
            ["activation_rate"],
            [{"activation_rate": 0.7818}],
            ["activation_rate"],
            [{"activation_rate": 0.7808}],
            order_sensitive=False,
        )

        self.assertFalse(correct)

    def test_extra_auxiliary_column_is_allowed(self) -> None:
        correct, column_match, reason = compare_results(
            ["channel", "user_count", "ratio"],
            [
                {"channel": "A", "user_count": 100, "ratio": 0.5},
                {"channel": "B", "user_count": 200, "ratio": 0.7},
            ],
            self.expected_columns,
            self.expected_rows,
            order_sensitive=False,
        )

        self.assertTrue(correct)
        self.assertFalse(column_match)
        self.assertEqual(reason, "结果一致（忽略列顺序和辅助列）")

    def test_column_order_is_still_ignored(self) -> None:
        correct, column_match, _ = compare_results(
            ["user_count", "channel"],
            [
                {"user_count": 100, "channel": "A"},
                {"user_count": 200, "channel": "B"},
            ],
            self.expected_columns,
            self.expected_rows,
            order_sensitive=True,
        )

        self.assertTrue(correct)
        self.assertTrue(column_match)


if __name__ == "__main__":
    unittest.main()
