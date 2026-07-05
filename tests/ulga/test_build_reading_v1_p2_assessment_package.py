from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_reading_v1_p2_assessment_package import (
    build_assessment_package,
    build_synthetic_assessment_item,
    build_synthetic_assessment_package,
)
from ulga.validators.validate_reading_v1_p2_assessment_package import validate_package


class ReadingV1P2AssessmentPackageBuilderTests(unittest.TestCase):
    def test_synthetic_package_passes_package_validator(self) -> None:
        package = build_synthetic_assessment_package()
        report = validate_package(package)
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertEqual(report["summary"]["item_count"], 2)
        self.assertEqual(report["summary"]["ready_item_count"], 2)

    def test_builder_sets_required_guards(self) -> None:
        package = build_assessment_package("pkg", [build_synthetic_assessment_item()])
        self.assertTrue(package["private_homework_only"])
        self.assertFalse(package["public_ready"])
        self.assertTrue(package["not_for_public_export"])
        self.assertTrue(package["not_for_commercial_distribution"])
        self.assertEqual(package["authority_status"], "candidate_only")
        self.assertEqual(package["promotion_status"], "not_promoted")
        self.assertFalse(package["learner_state_write"])

    def test_builder_deep_copies_input_items(self) -> None:
        item = build_synthetic_assessment_item()
        package = build_assessment_package("pkg", [item])
        item["display_payload"]["prompt"] = "Changed after build"
        self.assertEqual(package["items"][0]["display_payload"]["prompt"], "Who is in the story?")

    def test_empty_builder_output_fails_package_validator(self) -> None:
        package = build_assessment_package("pkg", [])
        report = validate_package(package)
        self.assertEqual(report["validator_status"], "FAIL")
        self.assertGreater(report["summary"]["error_count"], 0)

    def test_child_item_policy_failure_blocks_package(self) -> None:
        item = build_synthetic_assessment_item()
        item["public_ready"] = True
        package = build_assessment_package("pkg", [item])
        report = validate_package(package)
        self.assertEqual(report["validator_status"], "FAIL")
        self.assertGreater(report["summary"]["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
