from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.renderers.render_reading_v1_private_homework_html import render_private_homework_page
from ulga.validators.validate_reading_v1_html_export import validate_html_export_result


class ReadingV1PrivatePageExportSmokeTests(unittest.TestCase):
    def test_allowed_package_returns_page_string(self) -> None:
        gate = {
            "private_homework_only": True,
            "public_ready": False,
            "render_policy": {
                "render_mode": "local_private_homework_only",
                "allow_answer_key_display_to_student": False,
            },
            "summary": {"gate_status": "HTML_ENTRY_ALLOWED", "html_entry_allowed": True, "error_count": 0},
        }
        overlay = {"items": [{"source_item_id": "RV1_ITEM_000001", "student_view": {"prompt": "What happens?"}}]}
        result = render_private_homework_page(gate, overlay, {"RV1_ITEM_000001": "The child reads."})
        self.assertEqual(result["render_status"], "PASS")
        self.assertEqual(validate_html_export_result(result)["validator_status"], "PASS")

    def test_blocked_package_returns_empty_string(self) -> None:
        gate = {
            "private_homework_only": True,
            "public_ready": False,
            "render_policy": {
                "render_mode": "local_private_homework_only",
                "allow_answer_key_display_to_student": False,
            },
            "summary": {"gate_status": "HTML_ENTRY_BLOCKED", "html_entry_allowed": False, "error_count": 1},
        }
        result = render_private_homework_page(gate, {"items": []}, {})
        self.assertEqual(result["render_status"], "BLOCKED")
        self.assertEqual(result["html"], "")


if __name__ == "__main__":
    unittest.main()
