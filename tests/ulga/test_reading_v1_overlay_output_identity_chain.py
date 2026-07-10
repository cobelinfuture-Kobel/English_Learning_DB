from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_reading_v1_practice_bank import (
    build_synthetic_practice_bank,
)
from ulga.builders.build_reading_v1_private_homework_output_gate import (
    build_gate_report,
)
from ulga.builders.build_reading_v1_private_homework_overlay import (
    build_overlay_from_practice_bank,
)
from ulga.renderers.render_reading_v1_private_homework_html import (
    render_private_homework_page,
)
from ulga.validators.validate_reading_v1_html_export import (
    validate_html_export_result,
)
from ulga.validators.validate_reading_v1_practice_bank import validate_package
from ulga.validators.validate_reading_v1_private_homework_output_gate import (
    validate_output_gate_report,
)
from ulga.validators.validate_reading_v1_private_homework_overlay import (
    validate_overlay_package,
)


def _build_actual_chain() -> dict:
    practice_bank = build_synthetic_practice_bank()
    practice_bank_report = validate_package(practice_bank)
    overlay = build_overlay_from_practice_bank(
        practice_bank,
        practice_bank_report,
    )
    overlay_report = validate_overlay_package(overlay)
    raw_output_gate = build_gate_report(
        practice_bank_report,
        overlay_report,
        {"resolver_status": "PASS"},
    )
    output_gate_report = validate_output_gate_report(raw_output_gate)
    display_payloads = {
        item["item_id"]: f"Synthetic display text for {item['item_id']}."
        for item in practice_bank["items"]
    }
    render_result = render_private_homework_page(
        output_gate_report,
        overlay,
        display_payloads,
    )
    html_report = validate_html_export_result(render_result)
    return {
        "practice_bank": practice_bank,
        "practice_bank_report": practice_bank_report,
        "overlay": overlay,
        "overlay_report": overlay_report,
        "raw_output_gate": raw_output_gate,
        "output_gate_report": output_gate_report,
        "render_result": render_result,
        "html_report": html_report,
    }


class ReadingV1OverlayIdentityChainTests(unittest.TestCase):
    def test_actual_six_item_chain_preserves_identity_and_exports(self) -> None:
        chain = _build_actual_chain()

        practice_item_ids = [
            item["item_id"] for item in chain["practice_bank"]["items"]
        ]
        overlay_report_ids = [
            report["source_item_id"]
            for report in chain["overlay_report"]["item_reports"]
        ]
        output_gate_ids = [
            report["source_item_id"]
            for report in chain["output_gate_report"]["item_reports"]
        ]

        self.assertEqual(
            chain["practice_bank_report"]["validator_status"], "PASS"
        )
        self.assertEqual(chain["overlay_report"]["validator_status"], "PASS")
        self.assertTrue(
            chain["overlay_report"]["identity_summary"]["identity_join_ready"]
        )
        self.assertEqual(overlay_report_ids, practice_item_ids)
        self.assertEqual(output_gate_ids, practice_item_ids)
        self.assertEqual(
            chain["output_gate_report"]["validator_status"], "PASS"
        )
        self.assertEqual(
            chain["output_gate_report"]["summary"]["allowed_item_count"], 6
        )
        self.assertEqual(chain["render_result"]["render_status"], "PASS")
        self.assertEqual(chain["html_report"]["validator_status"], "PASS")
        self.assertEqual(
            chain["render_result"]["gate_evidence"]["rendered_item_ids"],
            practice_item_ids,
        )

    def test_overlay_report_exposes_source_and_overlay_identity(self) -> None:
        practice_bank = build_synthetic_practice_bank()
        practice_bank_report = validate_package(practice_bank)
        overlay = build_overlay_from_practice_bank(
            practice_bank,
            practice_bank_report,
        )
        report = validate_overlay_package(overlay)

        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertEqual(report["identity_summary"]["source_item_id_count"], 6)
        self.assertEqual(
            report["identity_summary"]["unique_source_item_id_count"], 6
        )
        for overlay_item, item_report in zip(
            overlay["items"], report["item_reports"]
        ):
            self.assertEqual(
                item_report["source_item_id"],
                overlay_item["source_item_id"],
            )
            self.assertEqual(
                item_report["overlay_item_id"],
                overlay_item["overlay_item_id"],
            )

    def test_duplicate_source_identity_is_blocked_before_output_gate(self) -> None:
        practice_bank = build_synthetic_practice_bank()
        practice_bank_report = validate_package(practice_bank)
        overlay = build_overlay_from_practice_bank(
            practice_bank,
            practice_bank_report,
        )
        duplicate = deepcopy(overlay["items"][0])
        duplicate["overlay_item_id"] = "RV1_OVERLAY_ITEM_DUPLICATE"
        overlay["items"].append(duplicate)

        report = validate_overlay_package(overlay)

        self.assertEqual(report["validator_status"], "FAIL")
        codes = {error["code"] for error in report["package_errors"]}
        self.assertIn("RV1_OVERLAY_ERR_DUPLICATE_SOURCE_ITEM_ID", codes)
        self.assertFalse(report["identity_summary"]["identity_join_ready"])

    def test_duplicate_overlay_identity_is_blocked(self) -> None:
        practice_bank = build_synthetic_practice_bank()
        practice_bank_report = validate_package(practice_bank)
        overlay = build_overlay_from_practice_bank(
            practice_bank,
            practice_bank_report,
        )
        overlay["items"][1]["overlay_item_id"] = overlay["items"][0][
            "overlay_item_id"
        ]

        report = validate_overlay_package(overlay)

        self.assertEqual(report["validator_status"], "FAIL")
        codes = {error["code"] for error in report["package_errors"]}
        self.assertIn("RV1_OVERLAY_ERR_DUPLICATE_OVERLAY_ITEM_ID", codes)

    def test_unknown_overlay_source_identity_fails_closed_at_output_gate(self) -> None:
        practice_bank = build_synthetic_practice_bank()
        practice_bank_report = validate_package(practice_bank)
        overlay = build_overlay_from_practice_bank(
            practice_bank,
            practice_bank_report,
        )
        overlay["items"][0]["source_item_id"] = "RV1_ITEM_UNKNOWN"
        overlay_report = validate_overlay_package(overlay)

        self.assertEqual(overlay_report["validator_status"], "PASS")
        raw_gate = build_gate_report(
            practice_bank_report,
            overlay_report,
            {"resolver_status": "PASS"},
        )
        output_gate_report = validate_output_gate_report(raw_gate)

        self.assertEqual(output_gate_report["validator_status"], "FAIL")
        codes = {
            error["code"]
            for item_report in output_gate_report["item_reports"]
            for error in item_report["errors"]
        }
        self.assertIn("RV1_OUT_ERR_PRACTICE_BANK_ITEM_NOT_FOUND", codes)


if __name__ == "__main__":
    unittest.main()
