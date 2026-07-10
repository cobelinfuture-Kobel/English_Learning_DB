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
    build_validated_synthetic_practice_bank,
    materialize_validation,
)
from ulga.query.a1_practice_item_grammar_gate import (
    ERR_GATE_MISSING,
    ERR_NO_MATCH,
    ERR_UNKNOWN_GRAMMAR_ID,
)
from ulga.validators.validate_reading_v1_practice_bank import validate_package


class ReadingV1PracticeBankValidatorTests(unittest.TestCase):
    def _item_error_codes(self, report: dict) -> set[str]:
        return {
            error["code"]
            for item_report in report["item_reports"]
            for error in item_report["errors"]
        }

    def test_synthetic_contract_fixture_passes_with_package_grammar_accounting(self) -> None:
        package = build_synthetic_practice_bank()
        report = validate_package(package)

        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertEqual(report["summary"]["item_count"], 6)
        self.assertEqual(report["summary"]["html_ready_count"], 6)
        self.assertEqual(report["summary"]["blocked_count"], 0)
        self.assertEqual(report["summary"]["grammar_gate_pass_count"], 6)
        self.assertEqual(report["summary"]["grammar_gate_fail_count"], 0)
        self.assertEqual(report["summary"]["grammar_validation_target_count"], 6)
        self.assertEqual(report["summary"]["grammar_matched_target_count"], 6)
        self.assertEqual(report["summary"]["error_count"], 0)
        self.assertTrue(report["grammar_gate_summary"]["all_items_pass"])
        self.assertEqual(report["grammar_gate_summary"]["pass_count"], 6)
        self.assertEqual(report["grammar_gate_summary"]["fail_count"], 0)
        self.assertFalse(report["grammar_gate_summary"]["production_runtime_validator"])
        self.assertFalse(report["grammar_gate_summary"]["learner_state_write"])
        self.assertTrue(
            all(
                item_report["grammar_gate_report"]["practice_item_gate_pass"]
                for item_report in report["item_reports"]
            )
        )

    def test_validated_builder_materializes_package_and_item_statuses(self) -> None:
        package = build_validated_synthetic_practice_bank()

        self.assertEqual(package["validation_summary"]["validator_status"], "PASS")
        self.assertEqual(package["validation_summary"]["html_ready_count"], 6)
        self.assertEqual(package["validation_summary"]["blocked_count"], 0)
        self.assertEqual(package["validation_summary"]["grammar_gate_status"], "PASS")
        self.assertEqual(package["validation_summary"]["grammar_gate_pass_count"], 6)
        self.assertEqual(package["validation_summary"]["grammar_gate_fail_count"], 0)
        self.assertEqual(package["validation_summary"]["grammar_validation_target_count"], 6)
        self.assertEqual(package["validation_summary"]["grammar_matched_target_count"], 6)
        self.assertTrue(package["build_metadata"]["validated"])
        self.assertEqual(
            package["build_metadata"]["validation_task_id"],
            "R7-M104E23B_A1PracticeBankGrammarGatePackageIntegration",
        )
        self.assertTrue(all(item["html_gate"]["html_ready"] for item in package["items"]))
        self.assertTrue(all(item["html_gate"]["html_ready_reason"] is None for item in package["items"]))
        self.assertTrue(all(item["validator_status"]["status"] == "PASS" for item in package["items"]))
        self.assertTrue(all(item["validator_status"]["grammar_gate_status"] == "PASS" for item in package["items"]))
        self.assertTrue(all(item["validator_status"]["grammar_validation_target_count"] == 1 for item in package["items"]))
        self.assertTrue(all(item["validator_status"]["grammar_matched_target_count"] == 1 for item in package["items"]))

    def test_materialize_validation_is_non_mutating_and_idempotent_for_revalidation(self) -> None:
        raw_package = build_synthetic_practice_bank()
        raw_before = deepcopy(raw_package)
        report = validate_package(raw_package)
        report_before = deepcopy(report)

        materialized = materialize_validation(raw_package, report)
        revalidation = validate_package(materialized)

        self.assertEqual(raw_package, raw_before)
        self.assertEqual(report, report_before)
        self.assertEqual(materialized["validation_summary"]["validator_status"], "PASS")
        self.assertEqual(revalidation["validator_status"], "PASS")
        self.assertEqual(revalidation["summary"]["grammar_gate_pass_count"], 6)
        self.assertEqual(revalidation["summary"]["grammar_gate_fail_count"], 0)

    def test_failed_grammar_gate_materializes_blocked_item_and_package(self) -> None:
        raw_package = build_synthetic_practice_bank()
        raw_package["items"][0]["grammar_gate"]["validation_targets"][0]["text"] = "She is playing tennis."
        report = validate_package(raw_package)
        materialized = materialize_validation(raw_package, report)

        self.assertEqual(materialized["validation_summary"]["validator_status"], "FAIL")
        self.assertEqual(materialized["validation_summary"]["grammar_gate_status"], "FAIL")
        self.assertEqual(materialized["validation_summary"]["grammar_gate_pass_count"], 5)
        self.assertEqual(materialized["validation_summary"]["grammar_gate_fail_count"], 1)
        self.assertEqual(materialized["validation_summary"]["html_ready_count"], 5)
        self.assertEqual(materialized["validation_summary"]["blocked_count"], 1)
        self.assertEqual(materialized["items"][0]["validator_status"]["status"], "FAIL")
        self.assertEqual(materialized["items"][0]["validator_status"]["grammar_gate_status"], "FAIL")
        self.assertFalse(materialized["items"][0]["html_gate"]["html_ready"])
        self.assertEqual(
            materialized["items"][0]["html_gate"]["html_ready_reason"],
            "blocked_by_practice_bank_validation",
        )
        self.assertIn(
            ERR_NO_MATCH,
            {error["code"] for error in materialized["items"][0]["validator_status"]["errors"]},
        )

    def test_materialize_validation_rejects_misaligned_report(self) -> None:
        package = build_synthetic_practice_bank()
        report = validate_package(package)
        report["item_reports"] = report["item_reports"][:-1]

        with self.assertRaises(ValueError):
            materialize_validation(package, report)

    def test_missing_grammar_gate_blocks_package_and_html_readiness(self) -> None:
        package = build_synthetic_practice_bank()
        del package["items"][0]["grammar_gate"]

        report = validate_package(package)

        self.assertEqual(report["validator_status"], "FAIL")
        self.assertIn(ERR_GATE_MISSING, self._item_error_codes(report))
        self.assertEqual(report["summary"]["grammar_gate_pass_count"], 5)
        self.assertEqual(report["summary"]["grammar_gate_fail_count"], 1)
        self.assertEqual(report["summary"]["html_ready_count"], 5)
        self.assertEqual(report["summary"]["blocked_count"], 1)
        self.assertFalse(report["grammar_gate_summary"]["all_items_pass"])

    def test_unknown_grammar_id_fails_closed_at_package_level(self) -> None:
        package = build_synthetic_practice_bank()
        item = package["items"][0]
        item["content_binding"]["grammar_focus"] = ["GRAMMAR_UNKNOWN_A1"]
        item["grammar_gate"]["validation_targets"][0]["grammar_id"] = "GRAMMAR_UNKNOWN_A1"

        report = validate_package(package)

        self.assertEqual(report["validator_status"], "FAIL")
        self.assertIn(ERR_UNKNOWN_GRAMMAR_ID, self._item_error_codes(report))
        self.assertEqual(report["summary"]["grammar_gate_fail_count"], 1)
        self.assertEqual(report["summary"]["grammar_matched_target_count"], 5)

    def test_declared_grammar_no_match_blocks_package(self) -> None:
        package = build_synthetic_practice_bank()
        package["items"][0]["grammar_gate"]["validation_targets"][0]["text"] = "She is playing tennis."

        report = validate_package(package)

        self.assertEqual(report["validator_status"], "FAIL")
        self.assertIn(ERR_NO_MATCH, self._item_error_codes(report))
        self.assertEqual(report["summary"]["grammar_gate_fail_count"], 1)
        self.assertEqual(report["summary"]["html_ready_count"], 5)

    def test_package_validation_does_not_mutate_input(self) -> None:
        package = build_synthetic_practice_bank()
        before = deepcopy(package)

        report = validate_package(package)

        self.assertEqual(report["validator_status"], "PASS")
        self.assertEqual(package, before)

    def test_schema_requires_fail_closed_grammar_gate_contract(self) -> None:
        schema = json.loads(
            (ROOT / "ulga/schemas/reading_v1_practice_bank.schema.json").read_text(encoding="utf-8")
        )
        practice_item = schema["$defs"]["practice_item"]
        grammar_gate = practice_item["properties"]["grammar_gate"]

        self.assertIn("grammar_gate", practice_item["required"])
        self.assertEqual(grammar_gate["properties"]["gate_version"]["const"], "a1_practice_item_grammar_gate.v1")
        self.assertEqual(grammar_gate["properties"]["validator_mode"]["const"], "OFFLINE_STATIC_PROTOTYPE")
        self.assertTrue(grammar_gate["properties"]["require_all_focus_matches"]["const"])
        self.assertFalse(grammar_gate["properties"]["production_runtime_validator"]["const"])
        self.assertFalse(grammar_gate["properties"]["learner_state_write"]["const"])
        self.assertEqual(grammar_gate["properties"]["validation_targets"]["minItems"], 1)
        self.assertEqual(practice_item["properties"]["content_binding"]["properties"]["grammar_focus"]["minItems"], 1)
        self.assertTrue(practice_item["properties"]["content_binding"]["properties"]["grammar_focus"]["uniqueItems"])

    def test_raw_raz_text_policy_blocks_item(self) -> None:
        package = build_synthetic_practice_bank()
        package["items"][0]["policy_flags"]["raw_raz_text_persisted"] = True
        report = validate_package(package)
        self.assertEqual(report["validator_status"], "FAIL")
        self.assertIn("RV1_PB_ERR_RAW_RAZ_TEXT_PERSISTED", self._item_error_codes(report))

    def test_stage_question_type_mismatch_blocks_item(self) -> None:
        package = build_synthetic_practice_bank()
        package["items"][4]["level_stage"] = "RV1-S0"
        report = validate_package(package)
        self.assertIn("RV1_PB_ERR_QUESTION_TYPE_NOT_ALLOWED_FOR_STAGE", self._item_error_codes(report))

    def test_cloze_missing_answer_blocks_item(self) -> None:
        package = build_synthetic_practice_bank()
        package["items"][5]["answer_model"]["answer_key"] = None
        report = validate_package(package)
        self.assertIn("RV1_PB_ERR_ANSWER_KEY_MISSING", self._item_error_codes(report))

    def test_package_public_export_policy_blocks_package(self) -> None:
        package = build_synthetic_practice_bank()
        package["not_for_public_export"] = False
        report = validate_package(package)
        package_codes = {error["code"] for error in report["package_errors"]}
        self.assertIn("RV1_PB_ERR_PUBLIC_EXPORT_ALLOWED", package_codes)


if __name__ == "__main__":
    unittest.main()
