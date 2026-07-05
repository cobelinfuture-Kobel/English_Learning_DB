from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.validators.validate_reading_v1_p2_assessment_item import validate_item


def valid_item() -> dict:
    return {
        "schema_version": "reading_v1_p2_assessment_item.v1",
        "item_id": "p2_item_001",
        "level_stage": "RV1-S1",
        "pattern_family": "literal_comprehension",
        "question_type": "literal_who",
        "display_payload": {
            "prompt": "Who is in the story?",
            "learner_visible_text": "Tom is in the story.",
            "source_payload_visible": False,
        },
        "answer_model": {
            "answer_key": "Tom",
            "accepted_answers": ["Tom"],
            "answer_visible_to_student": False,
        },
        "feedback_policy": {
            "feedback_boundary": "local_private_practice_only",
            "learner_state_write": False,
            "allowed_labels": ["correct", "incorrect", "needs_review", "not_answered"],
        },
        "source_trace": {
            "source_unit_ref": "operator_reviewed_seed:p2_item_001",
            "source_payload_persisted": False,
        },
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }


class ReadingV1P2AssessmentItemValidatorTests(unittest.TestCase):
    def test_valid_item_passes(self) -> None:
        report = validate_item(valid_item())
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertTrue(report["computed_ready"])
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_public_ready_guard_blocks_item(self) -> None:
        item = deepcopy(valid_item())
        item["public_ready"] = True
        report = validate_item(item)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_ITEM_ERR_GUARD", codes)

    def test_pattern_family_question_type_mismatch_blocks_item(self) -> None:
        item = deepcopy(valid_item())
        item["pattern_family"] = "vocabulary_in_context"
        item["question_type"] = "literal_who"
        report = validate_item(item)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_ITEM_ERR_FAMILY_TYPE", codes)

    def test_true_false_requires_boolean_key(self) -> None:
        item = deepcopy(valid_item())
        item["question_type"] = "true_false_text_check"
        item["answer_model"]["answer_key"] = "true"
        report = validate_item(item)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_ITEM_ERR_BOOLEAN", codes)

    def test_source_payload_persistence_blocks_item(self) -> None:
        item = deepcopy(valid_item())
        item["source_trace"]["source_payload_persisted"] = True
        report = validate_item(item)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P2_ITEM_ERR_TRACE_POLICY", codes)


if __name__ == "__main__":
    unittest.main()
