from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_reading_v1_practice_bank import build_synthetic_practice_bank
from ulga.builders.build_reading_v1_private_homework_output_gate import build_gate_report
from ulga.renderers.render_reading_v1_private_homework_html import render_private_homework_page
from ulga.validators.validate_reading_v1_html_export import validate_html_export_result
from ulga.validators.validate_reading_v1_practice_bank import validate_package
from ulga.validators.validate_reading_v1_private_homework_output_gate import validate_output_gate_report


SOURCE_ITEM_ID = "RV1_ITEM_000001"


def _allowed_gate() -> dict:
    practice_bank_report = validate_package(build_synthetic_practice_bank())
    overlay_report = {
        "validator_status": "PASS",
        "item_reports": [
            {
                "source_item_id": SOURCE_ITEM_ID,
                "overlay_item_id": "RV1_OVERLAY_ITEM_000001",
                "validator_status": "PASS",
                "computed_overlay_ready": True,
                "errors": [],
                "warnings": [],
            }
        ],
    }
    gate = build_gate_report(
        practice_bank_report,
        overlay_report,
        {"resolver_status": "PASS"},
    )
    validation = validate_output_gate_report(gate)
    assert validation["validator_status"] == "PASS", validation
    return validation


class ReadingV1PrivatePageExportSmokeTests(unittest.TestCase):
    def test_allowed_package_returns_page_string(self) -> None:
        gate = _allowed_gate()
        overlay = {
            "items": [
                {
                    "source_item_id": SOURCE_ITEM_ID,
                    "student_view": {"prompt": "What happens?"},
                }
            ]
        }
        result = render_private_homework_page(
            gate,
            overlay,
            {SOURCE_ITEM_ID: "The child reads."},
        )
        self.assertEqual(result["render_status"], "PASS", result)
        self.assertEqual(validate_html_export_result(result)["validator_status"], "PASS")

    def test_blocked_package_returns_empty_string(self) -> None:
        gate = _allowed_gate()
        gate["summary"]["gate_status"] = "HTML_ENTRY_BLOCKED"
        gate["summary"]["html_entry_allowed"] = False
        gate["summary"]["error_count"] = 1
        result = render_private_homework_page(gate, {"items": []}, {})
        self.assertEqual(result["render_status"], "BLOCKED")
        self.assertEqual(result["html"], "")


if __name__ == "__main__":
    unittest.main()
