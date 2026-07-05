from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ulga.test_reading_v1_p2_assessment_item import valid_item
from ulga.validators.validate_reading_v1_p2_assessment_package import validate_package


def valid_package() -> dict:
    item_one = valid_item()
    item_two = deepcopy(valid_item())
    item_two["item_id"] = "p2_item_002"
    item_two["question_type"] = "literal_what"
    item_two["display_payload"]["prompt"] = "What is in the story?"
    item_two["answer_model"]["answer_key"] = "a ball"
    return {
        "schema_version": "reading_v1_p2_assessment_package.v1",
        "package_id": "p2_package_001",
        "items": [item_one, item_two],
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "feedback_boundary": "local_private_practice_only",
        "learner_state_write": False,
    }


class ReadingV1P2AssessmentPackageValidatorTests(unittest.TestCase):
    def test_valid_package_passes(self) -> None:
        report = validate_package(valid_package())
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertEqual(report["summary"]["item_count"], 2)
        self.assertEqual(report["summary"]["ready_item_count"], 2)
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_empty_items_blocks_package(self) -> None:
        package = valid_package()
        package["items"] = []
        report = validate_package(package)
        codes = {error["code"] for error in report["package_errors"]}
        self.assertIn("RV1_P2_PKG_ERR_ITEMS", codes)

    def test_public_ready_guard_blocks_package(self) -> None:
        package = valid_package()
        package["public_ready"] = True
        report = validate_package(package)
        codes = {error["code"] for error in report["package_errors"]}
        self.assertIn("RV1_P2_PKG_ERR_GUARD", codes)

    def test_invalid_child_item_blocks_package(self) -> None:
        package = valid_package()
        package["items"][0]["source_trace"]["source_payload_persisted"] = True
        report = validate_package(package)
        self.assertEqual(report["validator_status"], "FAIL")
        self.assertGreater(report["summary"]["error_count"], 0)

    def test_learner_state_write_blocks_package(self) -> None:
        package = valid_package()
        package["learner_state_write"] = True
        report = validate_package(package)
        codes = {error["code"] for error in report["package_errors"]}
        self.assertIn("RV1_P2_PKG_ERR_GUARD", codes)


if __name__ == "__main__":
    unittest.main()
