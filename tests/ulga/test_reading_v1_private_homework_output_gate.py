from __future__ import annotations

import json
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
from ulga.renderers.render_reading_v1_private_homework_html import (
    render_private_homework_page,
)
from ulga.validators.validate_reading_v1_practice_bank import validate_package
from ulga.validators.validate_reading_v1_private_homework_output_gate import (
    validate_output_gate_report,
)


SOURCE_ITEM_ID = "RV1_ITEM_000001"


def _pb_report() -> dict:
    return validate_package(build_synthetic_practice_bank())


def _overlay_report(
    item_status: str = "PASS",
    ready: bool = True,
    source_item_id: str = SOURCE_ITEM_ID,
) -> dict:
    return {
        "validator_status": "PASS",
        "item_reports": [
            {
                "source_item_id": source_item_id,
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


def _item_error_codes(validation: dict) -> set[str]:
    return {
        error["code"]
        for item_report in validation["item_reports"]
        for error in item_report["errors"]
    }


def _overlay_package(source_item_id: str = SOURCE_ITEM_ID) -> dict:
    return {
        "items": [
            {
                "source_item_id": source_item_id,
                "student_view": {"prompt": "Where does the child go?"},
            }
        ]
    }


class ReadingV1PrivateHomeworkOutputGateTests(unittest.TestCase):
    def test_grammar_gated_output_gate_and_renderer_pass(self) -> None:
        pb_report = _pb_report()
        report = build_gate_report(
            pb_report, _overlay_report(), _resolver_report()
        )
        validation = validate_output_gate_report(report)

        self.assertEqual(validation["validator_status"], "PASS", validation)
        self.assertTrue(validation["summary"]["html_entry_allowed"])
        self.assertEqual(validation["summary"]["allowed_item_count"], 1)
        self.assertEqual(
            report["gate_inputs"]["practice_bank_grammar_gate_status"], "PASS"
        )
        self.assertEqual(
            report["gate_inputs"]["practice_bank_grammar_gate_fail_count"], 0
        )
        checks = report["item_gate_results"][0]["checks"]
        self.assertTrue(checks["practice_bank_item_report_present"])
        self.assertTrue(checks["practice_bank_item_pass"])
        self.assertTrue(checks["practice_bank_grammar_gate_pass"])
        self.assertTrue(checks["practice_bank_html_ready"])

        rendered = render_private_homework_page(
            validation,
            _overlay_package(),
            {SOURCE_ITEM_ID: "The child goes to school."},
        )
        self.assertEqual(rendered["render_status"], "PASS", rendered)
        self.assertIn("Where does the child go?", rendered["html"])

    def test_practice_bank_not_pass_blocks_package(self) -> None:
        pb_report = _pb_report()
        pb_report["validator_status"] = "FAIL"
        report = build_gate_report(
            pb_report, _overlay_report(), _resolver_report()
        )
        validation = validate_output_gate_report(report)
        codes = {error["code"] for error in validation["package_errors"]}
        self.assertIn("RV1_OUT_ERR_PRACTICE_BANK_NOT_PASS", codes)

    def test_package_grammar_gate_failure_blocks_output_and_renderer(self) -> None:
        pb_report = _pb_report()
        pb_report["grammar_gate_summary"]["all_items_pass"] = False
        pb_report["grammar_gate_summary"]["pass_count"] = 5
        pb_report["grammar_gate_summary"]["fail_count"] = 1
        report = build_gate_report(
            pb_report, _overlay_report(), _resolver_report()
        )
        validation = validate_output_gate_report(report)

        codes = {error["code"] for error in validation["package_errors"]}
        self.assertIn(
            "RV1_OUT_ERR_PRACTICE_BANK_GRAMMAR_GATE_NOT_PASS", codes
        )
        self.assertFalse(validation["summary"]["html_entry_allowed"])

        rendered = render_private_homework_page(
            validation,
            _overlay_package(),
            {SOURCE_ITEM_ID: "The child goes to school."},
        )
        self.assertEqual(rendered["render_status"], "BLOCKED")
        self.assertEqual(rendered["html"], "")

    def test_item_grammar_gate_failure_blocks_item(self) -> None:
        pb_report = _pb_report()
        item_report = pb_report["item_reports"][0]
        item_report["grammar_gate_report"]["practice_item_gate_pass"] = False
        item_report["grammar_gate_report"]["gate_status"] = "FAIL"

        report = build_gate_report(
            pb_report, _overlay_report(), _resolver_report()
        )
        validation = validate_output_gate_report(report)

        self.assertIn(
            "RV1_OUT_ERR_PRACTICE_BANK_GRAMMAR_GATE_NOT_PASS",
            _item_error_codes(validation),
        )
        self.assertFalse(validation["summary"]["html_entry_allowed"])
        self.assertFalse(
            report["item_gate_results"][0]["checks"][
                "practice_bank_grammar_gate_pass"
            ]
        )

    def test_practice_bank_html_ready_false_blocks_item(self) -> None:
        pb_report = _pb_report()
        pb_report["item_reports"][0]["computed_html_ready"] = False

        report = build_gate_report(
            pb_report, _overlay_report(), _resolver_report()
        )
        validation = validate_output_gate_report(report)

        self.assertIn(
            "RV1_OUT_ERR_PRACTICE_BANK_HTML_READY_FALSE",
            _item_error_codes(validation),
        )

    def test_missing_practice_bank_item_mapping_blocks_item(self) -> None:
        report = build_gate_report(
            _pb_report(),
            _overlay_report(source_item_id="RV1_ITEM_UNKNOWN"),
            _resolver_report(),
        )
        validation = validate_output_gate_report(report)

        self.assertIn(
            "RV1_OUT_ERR_PRACTICE_BANK_ITEM_NOT_FOUND",
            _item_error_codes(validation),
        )
        self.assertFalse(
            report["item_gate_results"][0]["checks"][
                "practice_bank_item_report_present"
            ]
        )

    def test_duplicate_practice_bank_item_id_blocks_package(self) -> None:
        pb_report = _pb_report()
        pb_report["item_reports"].append(deepcopy(pb_report["item_reports"][0]))

        report = build_gate_report(
            pb_report, _overlay_report(), _resolver_report()
        )
        validation = validate_output_gate_report(report)

        codes = {error["code"] for error in validation["package_errors"]}
        self.assertIn("RV1_OUT_ERR_DUPLICATE_PRACTICE_BANK_ITEM_ID", codes)

    def test_overlay_ready_false_blocks_item(self) -> None:
        report = build_gate_report(
            _pb_report(), _overlay_report(ready=False), _resolver_report()
        )
        validation = validate_output_gate_report(report)
        self.assertIn(
            "RV1_OUT_ERR_OVERLAY_READY_FALSE",
            _item_error_codes(validation),
        )

    def test_student_answer_key_visibility_blocks_package(self) -> None:
        report = build_gate_report(
            _pb_report(), _overlay_report(), _resolver_report()
        )
        report["render_policy"]["allow_answer_key_display_to_student"] = True
        validation = validate_output_gate_report(report)
        codes = {error["code"] for error in validation["package_errors"]}
        self.assertIn("RV1_OUT_ERR_ANSWER_KEY_VISIBLE_TO_STUDENT", codes)

    def test_copied_material_persistence_blocks_item(self) -> None:
        report = build_gate_report(
            _pb_report(), _overlay_report(), _resolver_report()
        )
        report["item_gate_results"][0]["checks"][
            "copied_material_persisted"
        ] = True
        validation = validate_output_gate_report(report)
        self.assertIn(
            "RV1_OUT_ERR_COPIED_MATERIAL_PERSISTED",
            _item_error_codes(validation),
        )

    def test_schema_requires_practice_bank_grammar_gate_evidence(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "ulga/schemas/reading_v1_private_homework_output_gate.schema.json"
            ).read_text(encoding="utf-8")
        )
        gate_inputs = schema["properties"]["gate_inputs"]
        item_checks = schema["$defs"]["item_gate_result"]["properties"][
            "checks"
        ]

        for required in (
            "practice_bank_grammar_gate_status",
            "practice_bank_grammar_gate_pass_count",
            "practice_bank_grammar_gate_fail_count",
            "practice_bank_item_report_count",
            "practice_bank_duplicate_item_ids",
        ):
            self.assertIn(required, gate_inputs["required"])

        self.assertEqual(
            gate_inputs["properties"][
                "practice_bank_grammar_gate_status"
            ]["const"],
            "PASS",
        )
        self.assertEqual(
            gate_inputs["properties"][
                "practice_bank_grammar_gate_fail_count"
            ]["const"],
            0,
        )
        for required in (
            "practice_bank_item_report_present",
            "practice_bank_item_pass",
            "practice_bank_grammar_gate_pass",
            "practice_bank_html_ready",
        ):
            self.assertIn(required, item_checks["required"])


if __name__ == "__main__":
    unittest.main()
