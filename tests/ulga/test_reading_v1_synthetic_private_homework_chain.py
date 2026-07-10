from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_reading_v1_synthetic_private_homework_chain import (
    DEFAULT_VALID_GRAMMAR_TEXT,
    main,
    run_synthetic_private_homework_chain,
)


class ReadingV1SyntheticPrivateHomeworkChainRunnerTests(unittest.TestCase):
    def test_default_chain_passes_all_six_items(self) -> None:
        result = run_synthetic_private_homework_chain()

        self.assertEqual(result["chain_status"], "PASS", result)
        self.assertTrue(result["chain_pass"])
        self.assertFalse(result["safe_block"])
        self.assertEqual(
            result["stage_status"],
            {
                "practice_bank_validator": "PASS",
                "overlay_validator": "PASS",
                "output_gate_validator": "PASS",
                "renderer": "PASS",
                "html_export_validator": "PASS",
            },
        )
        self.assertEqual(result["stage_counts"]["practice_item_count"], 6)
        self.assertEqual(result["stage_counts"]["grammar_gate_pass_count"], 6)
        self.assertEqual(result["stage_counts"]["grammar_gate_fail_count"], 0)
        self.assertEqual(result["stage_counts"]["overlay_ready_count"], 6)
        self.assertEqual(result["stage_counts"]["output_allowed_item_count"], 6)
        self.assertEqual(result["stage_counts"]["rendered_item_count"], 6)
        self.assertEqual(result["failure_codes"], [])
        self.assertEqual(result["html_export"]["render_status"], "PASS")
        self.assertEqual(result["html_export"]["validator_status"], "PASS")
        self.assertTrue(result["html_export"]["html"])
        self.assertEqual(
            result["html_export"]["gate_evidence"]["rendered_item_ids"],
            result["item_ids"],
        )

    def test_invalid_grammar_target_fails_closed_with_empty_html(self) -> None:
        result = run_synthetic_private_homework_chain(
            first_item_grammar_text="She is playing tennis."
        )

        self.assertEqual(result["chain_status"], "BLOCKED", result)
        self.assertFalse(result["chain_pass"])
        self.assertTrue(result["safe_block"])
        self.assertEqual(
            result["stage_status"]["practice_bank_validator"], "FAIL"
        )
        self.assertEqual(result["stage_status"]["overlay_validator"], "FAIL")
        self.assertEqual(
            result["stage_status"]["output_gate_validator"], "FAIL"
        )
        self.assertEqual(result["stage_status"]["renderer"], "BLOCKED")
        self.assertEqual(
            result["stage_status"]["html_export_validator"], "PASS"
        )
        self.assertEqual(result["stage_counts"]["grammar_gate_fail_count"], 1)
        self.assertEqual(result["stage_counts"]["rendered_item_count"], 0)
        self.assertEqual(result["html_export"]["html"], "")
        self.assertIn(
            "A1_PI_GRAMMAR_GATE_ERR_NO_MATCH",
            result["failure_codes"],
        )
        self.assertIn(
            "RV1_HTML_ERR_OUTPUT_GATE_NOT_ALLOWED",
            result["failure_codes"],
        )

    def test_explicit_valid_grammar_target_matches_default(self) -> None:
        default_result = run_synthetic_private_homework_chain()
        explicit_result = run_synthetic_private_homework_chain(
            first_item_grammar_text=DEFAULT_VALID_GRAMMAR_TEXT
        )

        self.assertEqual(explicit_result["chain_status"], "PASS")
        self.assertEqual(
            explicit_result["stage_counts"],
            default_result["stage_counts"],
        )
        self.assertEqual(
            explicit_result["html_export"]["gate_evidence"],
            default_result["html_export"]["gate_evidence"],
        )

    def test_safety_boundaries_remain_false(self) -> None:
        result = run_synthetic_private_homework_chain()

        self.assertTrue(result["safety"]["private_homework_only"])
        self.assertFalse(result["safety"]["public_ready"])
        for key in (
            "source_payload_persisted",
            "raw_raz_text_read",
            "full_passage_text_read",
            "learner_state_write",
            "production_runtime_validator",
            "external_nlp_dependency",
            "a2plus_grammar_authority_modified",
        ):
            self.assertFalse(result["safety"][key], key)

    def test_cli_writes_a_valid_synthetic_audit_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "chain_result.json"
            exit_code = main(["--output", str(output)])
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["chain_status"], "PASS")
        self.assertEqual(payload["stage_counts"]["practice_item_count"], 6)
        self.assertEqual(payload["html_export"]["render_status"], "PASS")

    def test_cli_returns_two_for_safe_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "blocked_chain_result.json"
            exit_code = main(
                [
                    "--output",
                    str(output),
                    "--first-item-grammar-text",
                    "She is playing tennis.",
                ]
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["chain_status"], "BLOCKED")
        self.assertTrue(payload["safe_block"])
        self.assertEqual(payload["html_export"]["html"], "")


if __name__ == "__main__":
    unittest.main()
