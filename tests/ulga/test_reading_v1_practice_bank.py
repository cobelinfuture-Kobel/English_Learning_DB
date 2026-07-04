from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_reading_v1_practice_bank import build_synthetic_practice_bank
from ulga.validators.validate_reading_v1_practice_bank import validate_package


class ReadingV1PracticeBankValidatorTests(unittest.TestCase):
    def test_synthetic_contract_fixture_passes(self) -> None:
        package = build_synthetic_practice_bank()
        report = validate_package(package)
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertEqual(report["summary"]["item_count"], 6)
        self.assertEqual(report["summary"]["html_ready_count"], 6)
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_raw_raz_text_policy_blocks_item(self) -> None:
        package = build_synthetic_practice_bank()
        package["items"][0]["policy_flags"]["raw_raz_text_persisted"] = True
        report = validate_package(package)
        self.assertEqual(report["validator_status"], "FAIL")
        codes = {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_PB_ERR_RAW_RAZ_TEXT_PERSISTED", codes)

    def test_stage_question_type_mismatch_blocks_item(self) -> None:
        package = build_synthetic_practice_bank()
        package["items"][4]["level_stage"] = "RV1-S0"
        report = validate_package(package)
        codes = {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_PB_ERR_QUESTION_TYPE_NOT_ALLOWED_FOR_STAGE", codes)

    def test_cloze_missing_answer_blocks_item(self) -> None:
        package = build_synthetic_practice_bank()
        package["items"][5]["answer_model"]["answer_key"] = None
        report = validate_package(package)
        codes = {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_PB_ERR_ANSWER_KEY_MISSING", codes)

    def test_package_public_export_policy_blocks_package(self) -> None:
        package = build_synthetic_practice_bank()
        package["not_for_public_export"] = False
        report = validate_package(package)
        package_codes = {error["code"] for error in report["package_errors"]}
        self.assertIn("RV1_PB_ERR_PUBLIC_EXPORT_ALLOWED", package_codes)


if __name__ == "__main__":
    unittest.main()
