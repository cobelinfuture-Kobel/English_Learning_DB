from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.validators.validate_reading_v1_p2_review_tag import validate_review_tag


def valid_review_tag() -> dict:
    return {
        "schema_version": "reading_v1_p2_review_tag.v1",
        "item_id": "p2_item_001",
        "review_tag": "literal_detail_miss",
        "review_boundary": "local_private_review_only",
        "private_homework_only": True,
        "public_ready": False,
        "learner_state_write": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }


class ReadingV1P2ReviewTagValidatorTests(unittest.TestCase):
    def test_valid_review_tag_passes(self) -> None:
        report = validate_review_tag(valid_review_tag())
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertTrue(report["computed_ready"])
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_invalid_tag_blocks_record(self) -> None:
        record = deepcopy(valid_review_tag())
        record["review_tag"] = "main_idea_gap"
        report = validate_review_tag(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_TAG_ERR_TAG", codes)

    def test_boundary_mismatch_blocks_record(self) -> None:
        record = deepcopy(valid_review_tag())
        record["review_boundary"] = "long_term_profile"
        report = validate_review_tag(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_TAG_ERR_BOUNDARY", codes)

    def test_learner_state_write_blocks_record(self) -> None:
        record = deepcopy(valid_review_tag())
        record["learner_state_write"] = True
        report = validate_review_tag(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_TAG_ERR_STATE_WRITE", codes)

    def test_public_ready_guard_blocks_record(self) -> None:
        record = deepcopy(valid_review_tag())
        record["public_ready"] = True
        report = validate_review_tag(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_TAG_ERR_GUARD", codes)


if __name__ == "__main__":
    unittest.main()
