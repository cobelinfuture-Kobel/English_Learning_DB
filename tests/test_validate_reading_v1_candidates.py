"""Tests for the Reading V1 candidate validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
VALIDATOR_PATH = TOOLS_DIR / "validate_reading_v1_candidates.py"
MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"
SCHEMA_PATH = REPO_ROOT / "ulga" / "schemas" / "reading_v1_candidate.schema.json"
CANDIDATES_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_pilot_candidates.json"
REPORT_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_validation_report.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_reading_v1_candidates", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReadingV1CandidateValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()
        self.candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.manifest_ids = self.validator.load_manifest_ids(MANIFEST_PATH)

    def validate_one(self, candidate: dict):
        return self.validator.validate_candidate(candidate, self.manifest_ids)

    def build_report(self, candidates: list[dict]):
        return self.validator.build_report(candidates, SCHEMA_PATH, MANIFEST_PATH, CANDIDATES_PATH, self.manifest_ids)

    def test_static_validation_report_passes_with_warnings(self) -> None:
        self.assertEqual(self.report["schema_version"], "READING_V1_VALIDATION_REPORT_V1")
        self.assertEqual(self.report["status"], self.validator.PASS_WITH_WARNINGS)
        self.assertEqual(self.report["candidate_count"], 3)
        self.assertEqual(self.report["pass_count"], 3)
        self.assertEqual(self.report["fail_count"], 0)
        self.assertEqual(self.report["issues"], [])
        self.assertEqual(self.report["next_shortest_step"], "E4S-P1-S13_ReadingV1_CandidateValidationReport_ReadbackQA")

    def test_valid_tiny_pilot_candidates_have_no_blocking_issues(self) -> None:
        report = self.build_report(self.candidates)
        self.assertEqual(report["status"], self.validator.PASS_WITH_WARNINGS)
        self.assertEqual(report["candidate_count"], 3)
        self.assertEqual(report["pass_count"], 3)
        self.assertEqual(report["fail_count"], 0)
        self.assertEqual(report["issues"], [])
        self.assertGreaterEqual(report["warning_count"], 3)

    def test_missing_top_level_required_field_fails(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        del candidate["source_trace"]
        issues, _ = self.validate_one(candidate)
        self.assertIn("READING_V1_SCHEMA_INVALID", {issue["code"] for issue in issues})

    def test_unknown_source_id_fails(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        candidate["source_trace"]["source_id"] = "UNKNOWN_SOURCE"
        issues, _ = self.validate_one(candidate)
        codes = {issue["code"] for issue in issues}
        self.assertIn("READING_V1_UNKNOWN_SOURCE_ID", codes)
        self.assertIn("READING_V1_INELIGIBLE_SOURCE", codes)

    def test_ineligible_source_family_fails(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        candidate["source_trace"]["source_family"] = "status_artifact"
        issues, _ = self.validate_one(candidate)
        self.assertIn("READING_V1_SOURCE_FAMILY_MISMATCH", {issue["code"] for issue in issues})

    def test_raz_wordlist_as_direct_vocab_authority_fails(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        candidate["source_trace"]["source_id"] = "RAZ_WORDLIST_A_T_EVIDENCE"
        candidate["source_trace"]["source_family"] = "raz_wordlist"
        candidate["source_trace"]["authority_role"] = "direct_vocab_authority"
        issues, _ = self.validate_one(candidate)
        self.assertIn("READING_V1_AUTHORITY_ROLE_MISMATCH", {issue["code"] for issue in issues})

    def test_source_payload_copied_true_fails(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        candidate["source_trace"]["source_payload_copied"] = True
        issues, _ = self.validate_one(candidate)
        self.assertIn("READING_V1_SOURCE_PAYLOAD_COPIED", {issue["code"] for issue in issues})

    def test_unsafe_source_policy_flags_fail(self) -> None:
        for field, code in [
            ("learner_facing_allowed", "READING_V1_LEARNER_FACING_ALLOWED"),
            ("public_distribution_allowed", "READING_V1_PUBLIC_DISTRIBUTION_ALLOWED"),
            ("authority_promotion_allowed", "READING_V1_AUTHORITY_PROMOTION_ALLOWED"),
        ]:
            candidate = copy.deepcopy(self.candidates[0])
            candidate["source_policy"][field] = True
            issues, _ = self.validate_one(candidate)
            self.assertIn(code, {issue["code"] for issue in issues})

    def test_requires_evidence_false_and_missing_answer_evidence_fail(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        candidate["question_model"]["requires_evidence"] = False
        del candidate["answer_model"]["answer_evidence_ref"]
        issues, _ = self.validate_one(candidate)
        codes = {issue["code"] for issue in issues}
        self.assertIn("READING_V1_QUESTION_NOT_EVIDENCE_REQUIRED", codes)
        self.assertIn("READING_V1_ANSWER_EVIDENCE_MISSING", codes)

    def test_missing_evidence_locator_fails(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        del candidate["evidence_model"]["evidence_locator"]
        issues, _ = self.validate_one(candidate)
        self.assertIn("READING_V1_EVIDENCE_TRACE_MISSING", {issue["code"] for issue in issues})

    def test_level_and_multiskill_flags_fail(self) -> None:
        candidate = copy.deepcopy(self.candidates[0])
        candidate["level_metadata"]["learner_placement_allowed"] = True
        candidate["skill_metadata"]["multi_skill_expansion_allowed"] = True
        issues, _ = self.validate_one(candidate)
        codes = {issue["code"] for issue in issues}
        self.assertIn("READING_V1_LEVEL_AS_LEARNER_PLACEMENT", codes)
        self.assertIn("READING_V1_MULTISKILL_EXPANSION", codes)

    def test_blocked_output_fields_fail(self) -> None:
        cases = [
            ("student_html_created", "READING_V1_STUDENT_HTML_CREATED"),
            ("worksheet_created", "READING_V1_WORKSHEET_CREATED"),
            ("learner_state_updated", "READING_V1_LEARNER_STATE_UPDATED"),
            ("adaptive_recommendation_created", "READING_V1_ADAPTIVE_RECOMMENDATION_CREATED"),
            ("large_scale_generation_performed", "READING_V1_LARGE_SCALE_GENERATION"),
        ]
        for field, expected_code in cases:
            candidate = copy.deepcopy(self.candidates[0])
            candidate["blocked_output_state"][field] = True
            issues, _ = self.validate_one(candidate)
            self.assertIn(expected_code, {issue["code"] for issue in issues})

    def test_manual_review_pending_returns_warning(self) -> None:
        issues, warnings = self.validate_one(self.candidates[0])
        self.assertEqual(issues, [])
        self.assertIn("READING_V1_MANUAL_REVIEW_PENDING", {warning["code"] for warning in warnings})

    def test_invalid_json_or_missing_file_cli_emits_structured_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_candidate = Path(tmpdir) / "missing.json"
            report_path = Path(tmpdir) / "validation_report.json"
            exit_code = self.validator.main(
                [
                    "--candidate-path",
                    str(missing_candidate),
                    "--schema-path",
                    str(SCHEMA_PATH),
                    "--manifest-path",
                    str(MANIFEST_PATH),
                    "--output-report",
                    str(report_path),
                ]
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], self.validator.FAIL)
        self.assertEqual(report["issues"][0]["code"], "READING_V1_INPUT_MISSING")


if __name__ == "__main__":
    unittest.main()
