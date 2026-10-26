"""Guard the reviewed source reports before independent PostgreSQL alias replay."""

import unittest
from unittest.mock import patch

from app.config import BASE_DIR
from scripts.apply_m1_e_postgres_aliases import FROZEN_CASES
from scripts.rescore_m1_e_postgres_aliases import replay


class M1EAliasReplayTest(unittest.TestCase):
    def test_first_run_evidence_passes_preflight_without_changing_cases(self):
        marker = RuntimeError("preflight reached PostgreSQL runtime")
        with patch("scripts.rescore_m1_e_postgres_aliases.create_datasource_runtime",
                   side_effect=marker):
            with self.assertRaisesRegex(RuntimeError, str(marker)):
                replay(BASE_DIR / "evaluation/results/m1_e_alias_preflight_unused.json",
                       case_path=FROZEN_CASES)


if __name__ == "__main__":
    unittest.main()
