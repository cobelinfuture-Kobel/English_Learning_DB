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


SOURCE_ITEM_ID = "RV1_ITEM_000001"


def _practice_bank_report() -> dict:
    return validate_package(build_synthetic_practice_bank())


def _overlay_report(source_item_id: str = SOURCE_ITEM_ID) -> dict:
    return {
        "validator_status": "PASS",
        "item_reports": [
            {
                "source_item_id": source_item_id,
                "overlay_item_id": "RV1_OVERLAY_ITEM_000001",
                "validator_status": "PASS",
                "computed_overlay_ready": True,
                "errors": [],
                "warnings": [],
            }
        ],
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


def _validated_output_gate(pb_report: dict | None = None) -> dict:
    raw_gate = build_gate_report(
        pb_report or _practice_bank_report(),
        _overlay_report(),
        {"resolver_status": "PASS"},
    )
    return validate_output_gate_report(raw_gate)


def _render(pb_report: dict | None = None) -> dict:
    return render_private_homework_page(
        _validated_output_gate(pb_report),
        _overlay_package(),
        {SOURCE_ITEM_ID: "The child goes to school."},
    )


class ReadingV1HTMLExportGrammarEvidenceTests(unittest.TestCase):
    def test_full_grammar_gated_chain_exports_and_validates(self) -> None:
        rendered = _render()
        validation = validate_html_export_result(rendered)

        self.assertEqual(rendered["render_status"], "PASS", rendered)
        self.assertEqual(validation["validator_status"], "PASS", validation)
        self.assertTrue(validation["gate_evidence_present"])
        self.assertTrue(validation["grammar_gate_evidence_pass"])

        evidence = rendered["gate_evidence"]
        self.assertEqual(
            evidence["evidence_version"],
            "reading_v1_html_export_gate_evidence.v1",
        )
        self.assertEqual(
            evidence["output_gate_task_id"],
            "R7-M104E24A_A1PracticeBankGrammarGatedHTMLExportIntegration",
        )
        self.assertEqual(
            evidence["practice_bank_grammar_gate_status"], "PASS"
        )
        self.assertEqual(
            evidence["practice_bank_grammar_gate_fail_count"], 0
        )
        self.assertEqual(
            evidence["practice_bank_grammar_gate_pass_count"],
            evidence["practice_bank_item_report_count"],
        )
        self.assertEqual(evidence["rendered_item_ids"], [SOURCE_ITEM_ID])
        self.assertEqual(evidence["source_item_ids"], [SOURCE_ITEM_ID])
        self.assertEqual(evidence["rendered_item_count"], 1)

    def test_forged_pass_without_gate_evidence_is_rejected(self) -> None:
        forged = {
            "schema_version": "reading_v1_html_export_result.v1",
            "render_status": "PASS",
            "html": "<main>Forged page</main>",
            "errors": [],
        }

        validation = validate_html_export_result(forged)

        self.assertEqual(validation["validator_status"], "FAIL")
        codes = {error["code"] for error in validation["errors"]}
        self.assertIn("RV1_HTML_ERR_GATE_EVIDENCE_MISSING", codes)

    def test_tampered_grammar_gate_status_is_rejected(self) -> None:
        rendered = _render()
        rendered["gate_evidence"]["practice_bank_grammar_gate_status"] = "FAIL"

        validation = validate_html_export_result(rendered)

        self.assertEqual(validation["validator_status"], "FAIL")
        codes = {error["code"] for error in validation["errors"]}
        self.assertIn(
            "RV1_HTML_ERR_GRAMMAR_GATE_EVIDENCE_NOT_PASS", codes
        )

    def test_tampered_grammar_gate_accounting_is_rejected(self) -> None:
        rendered = _render()
        rendered["gate_evidence"]["practice_bank_grammar_gate_pass_count"] = 5

        validation = validate_html_export_result(rendered)

        self.assertEqual(validation["validator_status"], "FAIL")
        codes = {error["code"] for error in validation["errors"]}
        self.assertIn(
            "RV1_HTML_ERR_GRAMMAR_GATE_EVIDENCE_NOT_PASS", codes
        )

    def test_tampered_output_item_accounting_is_rejected(self) -> None:
        rendered = _render()
        rendered["gate_evidence"]["allowed_item_count"] = 0

        validation = validate_html_export_result(rendered)

        self.assertEqual(validation["validator_status"], "FAIL")
        codes = {error["code"] for error in validation["errors"]}
        self.assertIn("RV1_HTML_ERR_OUTPUT_GATE_ITEM_ACCOUNTING", codes)

    def test_rendered_item_ids_must_match_output_gate_items(self) -> None:
        rendered = _render()
        rendered["gate_evidence"]["rendered_item_ids"] = ["RV1_ITEM_OTHER"]

        validation = validate_html_export_result(rendered)

        self.assertEqual(validation["validator_status"], "FAIL")
        codes = {error["code"] for error in validation["errors"]}
        self.assertIn("RV1_HTML_ERR_RENDERED_ITEM_EVIDENCE_INVALID", codes)

    def test_grammar_gate_failure_produces_valid_blocked_export(self) -> None:
        pb_report = _practice_bank_report()
        pb_report["grammar_gate_summary"]["all_items_pass"] = False
        pb_report["grammar_gate_summary"]["pass_count"] = 5
        pb_report["grammar_gate_summary"]["fail_count"] = 1

        rendered = _render(pb_report)
        validation = validate_html_export_result(rendered)

        self.assertEqual(rendered["render_status"], "BLOCKED")
        self.assertEqual(rendered["html"], "")
        self.assertEqual(validation["validator_status"], "PASS", validation)
        self.assertTrue(validation["gate_evidence_present"])
        self.assertFalse(validation["grammar_gate_evidence_pass"])

    def test_blocked_export_with_html_is_rejected(self) -> None:
        pb_report = _practice_bank_report()
        pb_report["grammar_gate_summary"]["all_items_pass"] = False
        pb_report["grammar_gate_summary"]["pass_count"] = 5
        pb_report["grammar_gate_summary"]["fail_count"] = 1
        rendered = _render(pb_report)
        rendered["html"] = "<main>Should not exist</main>"

        validation = validate_html_export_result(rendered)

        self.assertEqual(validation["validator_status"], "FAIL")
        codes = {error["code"] for error in validation["errors"]}
        self.assertIn("RV1_HTML_ERR_BLOCKED_WITH_PAGE", codes)

    def test_student_view_leak_is_still_rejected(self) -> None:
        rendered = _render()
        rendered["html"] += '<div class="student-answer-key">secret</div>'

        validation = validate_html_export_result(rendered)

        self.assertEqual(validation["validator_status"], "FAIL")
        codes = {error["code"] for error in validation["errors"]}
        self.assertIn("RV1_HTML_ERR_STUDENT_VIEW_LEAK", codes)

    def test_renderer_does_not_mutate_gate_report(self) -> None:
        gate_report = _validated_output_gate()
        before = deepcopy(gate_report)

        rendered = render_private_homework_page(
            gate_report,
            _overlay_package(),
            {SOURCE_ITEM_ID: "The child goes to school."},
        )

        self.assertEqual(rendered["render_status"], "PASS")
        self.assertEqual(gate_report, before)


if __name__ == "__main__":
    unittest.main()
