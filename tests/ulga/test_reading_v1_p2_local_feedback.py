from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.validators.validate_reading_v1_p2_local_feedback import validate_feedback


def valid_feedback() -> dict:
    return {
        "schema_version": "reading_v1_p2_local_feedback.v1",
        "item_id": "p2_item_001",
        "feedback_label": "correct",
        "feedback_boundary": "local_private_practice_only",
        "learner_state_write": False,
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }


class ReadingV1P2LocalFeedbackValidatorTests(unittest.TestCase):
    def test_valid_feedback_passes(self) -> None:
        report = validate_feedback(valid_feedback())
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertTrue(report["computed_ready"])
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_invalid_label_blocks_feedback(self) -> None:
        record = deepcopy(valid_feedback())
        record["feedback_label"] = "mastered"
        report = validate_feedback(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_FB_ERR_LABEL", codes)

    def test_learner_state_write_blocks_feedback(self) -> None:
        record = deepcopy(valid_feedback())
        record["learner_state_write"] = True
        report = validate_feedback(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_FB_ERR_STATE_WRITE", codes)

    def test_public_ready_guard_blocks_feedback(self) -> None:
        record = deepcopy(valid_feedback())
        record["public_ready"] = True
        report = validate_feedback(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_FB_ERR_GUARD", codes)

    def test_missing_item_id_blocks_feedback(self) -> None:
        record = deepcopy(valid_feedback())
        record["item_id"] = ""
        report = validate_feedback(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_FB_ERR_ITEM_ID", codes)


if __name__ == "__main__":
    unittest.main()
