from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_reading_v1_private_homework_overlay import build_overlay_from_practice_bank
from ulga.validators.validate_reading_v1_private_homework_overlay import validate_overlay_package


def _practice_bank_fixture():
    return {
        "practice_bank_id": "RV1_PB_TEST_000001",
        "scope": {
            "level_stage": "RV1-S3",
            "theme": "DailyRoutine",
            "situation": "synthetic_contract_fixture",
        },
        "items": [
            {
                "item_id": "RV1_ITEM_000001",
                "level_stage": "RV1-S3",
                "theme": "DailyRoutine",
                "question_type": "literal_what",
                "question": {
                    "prompt": "What does the child do first?",
                    "options": [],
                    "requires_image": False,
                    "requires_audio": False,
                },
                "answer_model": {
                    "answer_key": "wake up",
                },
                "answer_evidence": {
                    "evidence_refs": ["synthetic_evidence_001"],
                    "source_locator": "synthetic://reading_v1/RV1_ITEM_000001#evidence",
                },
                "source_trace": {
                    "source_locator": "synthetic://reading_v1/RV1_ITEM_000001",
                    "source_unit_ref": "synthetic_unit_001",
                },
            },
            {
                "item_id": "RV1_ITEM_000002",
                "level_stage": "RV1-S3",
                "theme": "DailyRoutine",
                "question_type": "true_false",
                "question": {
                    "prompt": "The child goes to school.",
                    "options": [],
                    "requires_image": False,
                    "requires_audio": False,
                },
                "answer_model": {
                    "answer_key": True,
                },
                "answer_evidence": {
                    "evidence_refs": ["synthetic_evidence_002"],
                    "source_locator": "synthetic://reading_v1/RV1_ITEM_000002#evidence",
                },
                "source_trace": {
                    "source_locator": "synthetic://reading_v1/RV1_ITEM_000002",
                    "source_unit_ref": "synthetic_unit_002",
                },
            },
        ],
    }


def _validation_report_fixture():
    return {
        "validator_status": "PASS",
        "item_reports": [
            {
                "item_id": "RV1_ITEM_000001",
                "validator_status": "PASS",
                "computed_html_ready": True,
                "errors": [],
                "warnings": [],
            },
            {
                "item_id": "RV1_ITEM_000002",
                "validator_status": "PASS",
                "computed_html_ready": True,
                "errors": [],
                "warnings": [],
            },
        ],
    }


class ReadingV1PrivateHomeworkOverlayValidatorTests(unittest.TestCase):
    def test_synthetic_overlay_passes(self) -> None:
        overlay = build_overlay_from_practice_bank(_practice_bank_fixture(), _validation_report_fixture())
        report = validate_overlay_package(overlay)
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertEqual(report["summary"]["item_count"], 2)
        self.assertEqual(report["summary"]["overlay_ready_count"], 2)
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_inline_display_text_blocks_item(self) -> None:
        overlay = build_overlay_from_practice_bank(_practice_bank_fixture(), _validation_report_fixture())
        overlay["items"][0]["student_view"]["display_text_inline"] = "This should not be copied."
        report = validate_overlay_package(overlay)
        codes = {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_OVERLAY_ERR_RAW_SOURCE_TEXT_INLINE", codes)

    def test_html_ready_false_blocks_item(self) -> None:
        validation_report = _validation_report_fixture()
        validation_report["item_reports"][0]["computed_html_ready"] = False
        overlay = build_overlay_from_practice_bank(_practice_bank_fixture(), validation_report)
        report = validate_overlay_package(overlay)
        codes = {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_OVERLAY_ERR_HTML_READY_FALSE", codes)

    def test_public_ready_true_blocks_package_and_item(self) -> None:
        overlay = build_overlay_from_practice_bank(_practice_bank_fixture(), _validation_report_fixture())
        overlay["public_ready"] = True
        overlay["items"][0]["policy_flags"]["public_ready"] = True
        report = validate_overlay_package(overlay)
        package_codes = {error["code"] for error in report["package_errors"]}
        item_codes = {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_OVERLAY_ERR_PUBLIC_READY_TRUE", package_codes)
        self.assertIn("RV1_OVERLAY_ERR_PUBLIC_READY_TRUE", item_codes)

    def test_missing_answer_evidence_ref_blocks_item(self) -> None:
        overlay = build_overlay_from_practice_bank(_practice_bank_fixture(), _validation_report_fixture())
        overlay["items"][0]["parent_or_teacher_view"]["answer_evidence_ref"] = None
        report = validate_overlay_package(overlay)
        codes = {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_OVERLAY_ERR_ANSWER_EVIDENCE_REF_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
