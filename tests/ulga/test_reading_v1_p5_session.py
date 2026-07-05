from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.make_reading_v1_p5_session import make_session, make_synthetic_session
from ulga.validators.check_reading_v1_p5_session import check_session


class ReadingV1P5LocalSessionTests(unittest.TestCase):
    def test_synthetic_session_passes_checker(self) -> None:
        report = check_session(make_synthetic_session())
        self.assertEqual(report["validator_status"], "PASS", report)

    def test_session_uses_plan_focus_groups(self) -> None:
        session = make_session(
            {
                "schema_version": "reading_v1_p4_plan.v1",
                "package_id": "pkg",
                "focus_groups": ["review_literal_detail"],
            },
            session_id="custom_session",
        )
        self.assertEqual(session["session_id"], "custom_session")
        self.assertEqual(session["focus_groups"], ["review_literal_detail"])

    def test_checker_blocks_empty_focus_groups(self) -> None:
        session = make_session({"package_id": "pkg", "focus_groups": []})
        report = check_session(session)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P5_SESSION_ERR_FOCUS", codes)

    def test_checker_blocks_public_ready(self) -> None:
        session = make_synthetic_session()
        session["public_ready"] = True
        report = check_session(session)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P5_SESSION_ERR_PUBLIC", codes)

    def test_session_guard_values(self) -> None:
        session = make_synthetic_session()
        self.assertTrue(session["local_only"])
        self.assertTrue(session["private_homework_only"])
        self.assertFalse(session["public_ready"])
        self.assertFalse(session["learner_state_write"])


if __name__ == "__main__":
    unittest.main()
