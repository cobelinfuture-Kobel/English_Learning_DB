from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.make_reading_v1_p4_plan import make_plan, make_synthetic_plan
from ulga.validators.check_reading_v1_p4_plan import check_plan


class ReadingV1P4LocalPlanTests(unittest.TestCase):
    def test_synthetic_plan_passes_checker(self) -> None:
        report = check_plan(make_synthetic_plan())
        self.assertEqual(report["validator_status"], "PASS", report)

    def test_plan_ranks_focus_groups_by_count(self) -> None:
        plan = make_plan(
            {
                "package_id": "pkg",
                "item_count": 4,
                "group_counts": {"b": 1, "a": 3, "c": 2},
            },
            max_groups=2,
        )
        self.assertEqual(plan["focus_groups"], ["a", "c"])

    def test_checker_blocks_empty_focus_groups(self) -> None:
        plan = make_plan({"package_id": "pkg", "item_count": 0, "group_counts": {}})
        report = check_plan(plan)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P4_PLAN_ERR_FOCUS", codes)

    def test_checker_blocks_public_ready(self) -> None:
        plan = make_synthetic_plan()
        plan["public_ready"] = True
        report = check_plan(plan)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P4_PLAN_ERR_PUBLIC", codes)

    def test_plan_guard_values(self) -> None:
        plan = make_synthetic_plan()
        self.assertTrue(plan["local_only"])
        self.assertTrue(plan["private_homework_only"])
        self.assertFalse(plan["public_ready"])
        self.assertFalse(plan["learner_state_write"])


if __name__ == "__main__":
    unittest.main()
