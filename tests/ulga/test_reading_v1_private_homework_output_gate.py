from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_reading_v1_private_homework_output_gate import build_gate_report
from ulga.validators.validate_reading_v1_private_homework_output_gate import validate_output_gate_report


def _pb_report(status: str = "PASS") -> dict:
    return {"validator_status": status}


def _overlay_report(item_status: str = "PASS", ready: bool = True) -> dict:
    return {
        "validator_status": "PASS",
        "item_reports": [
            {
                "source_item_id": "RV1_ITEM_000001",
                "overlay_item_id": "RV1_OVERLAY_ITEM_000001",
                "validator_status": item_status,
                "computed_overlay_ready": ready,
                "errors": [],
                "warnings": [],
            }
        ],
    }


def _resolver_report(status: str = "PASS") -> dict:
    return {"resolver_status": status}


class ReadingV1PrivateHomeworkOutputGateTests(unittest.TestCase):
    def test_synthetic_gate_passes(self) -> None:
        report = build_gate_report(_pb_report(), _overlay_report(), _resolver_report())
        validation = validate_output_gate_report(report)
        self.assertEqual(validation["validator_status"], "PASS", validation)
        self.assertTrue(validation["summary"]["html_entry_allowed"])
        self.assertEqual(validation["summary"]["allowed_item_count"], 1)

    def test_practice_bank_not_pass_blocks_package(self) -> None:
        report = build_gate_report(_pb_report("FAIL"), _overlay_report(), _resolver_report())
        validation = validate_output_gate_report(report)
        codes = {error["code"] for error in validation["package_errors"]}
        self.assertIn("RV1_OUT_ERR_PRACTICE_BANK_NOT_PASS", codes)

    def test_overlay_ready_false_blocks_item(self) -> None:
        report = build_gate_report(_pb_report(), _overlay_report(ready=False), _resolver_report())
        validation = validate_output_gate_report(report)
        codes = {
            error["code"]
            for item_report in validation["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_OUT_ERR_OVERLAY_READY_FALSE", codes)

    def test_student_answer_key_visibility_blocks_package(self) -> None:
        report = build_gate_report(_pb_report(), _overlay_report(), _resolver_report())
        report["render_policy"]["allow_answer_key_display_to_student"] = True
        validation = validate_output_gate_report(report)
        codes = {error["code"] for error in validation["package_errors"]}
        self.assertIn("RV1_OUT_ERR_ANSWER_KEY_VISIBLE_TO_STUDENT", codes)

    def test_copied_material_persistence_blocks_item(self) -> None:
        report = build_gate_report(_pb_report(), _overlay_report(), _resolver_report())
        report["item_gate_results"][0]["checks"]["copied_material_persisted"] = True
        validation = validate_output_gate_report(report)
        codes = {
            error["code"]
            for item_report in validation["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_OUT_ERR_COPIED_MATERIAL_PERSISTED", codes)


if __name__ == "__main__":
    unittest.main()
