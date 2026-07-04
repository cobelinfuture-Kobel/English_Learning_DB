"""Tests for the E4S P5 listening candidate validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_e4s_listening_candidates.py"
MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_e4s_listening_candidates", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ValidateE4SListeningCandidatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def base_candidate(self, *, candidate_id: str = "p5_sentence_parent_functional_sentence_corpus_reference_sentence_001") -> dict:
        return {
            "candidate_id": candidate_id,
            "candidate_type": "sentence_listening_candidate",
            "eligibility_class": "P5_ELIGIBLE_VERIFIED_SENTENCE",
            "candidate_status": "candidate_only",
            "source_trace": {
                "source_id": "PARENT_FUNCTIONAL_SENTENCE_CORPUS_REFERENCE",
                "source_family": "parent_functional_sentence_corpus",
                "authority_role": "functional_sentence_corpus",
                "source_path_or_reference": "google_drive_reference:parent functional sentences",
                "source_record_hash_or_stable_ref": "manifest:PARENT_FUNCTIONAL_SENTENCE_CORPUS_REFERENCE",
                "source_unit_id": "sentence_001",
                "source_unit_type": "sentence",
                "source_unit_ref": "fixture:sentence_001",
                "license_status": "owned",
                "review_status": "metadata_reviewed",
                "promotion_rule": "candidate_only_until_review",
                "allowed_use": ["schema_design"],
                "blocked_use": ["learner_facing_output", "automatic_promotion", "final_authority_promotion"],
                "manual_review_status": "metadata_reviewed",
                "public_distribution_status": "blocked",
            },
            "source_text": {
                "source_text_raw": "Can I have some water?",
                "source_text_normalized": "Can I have some water?",
                "text_language": "en",
                "text_normalization_policy": "p5_text_normalization_v1",
                "text_segmentation_policy": "sentence_boundary_policy_v1",
                "text_review_status": "metadata_reviewed",
                "sensitive_content_review_status": "reviewed_safe",
                "child_suitability_review_status": "reviewed_safe",
            },
            "source_metadata": {
                "source_title_or_display_name": "Parent Functional Sentence Corpus",
                "source_level_system": "internal",
                "raw_level_code": "A1",
                "normalized_level_band": "A1",
                "level_claim_status": "reviewed",
                "source_owner_or_origin": "owned",
                "source_license_note": "owned internal source",
                "source_review_owner": "operator",
                "source_review_date_or_ref": "fixture_review",
            },
            "level_situation_metadata": {
                "normalized_level_band": "A1",
                "level_claim_status": "reviewed",
                "situation_domain": "home",
                "situation_context": "family_request",
                "communicative_function": "request",
                "interaction_mode": "single_sentence",
                "skill_fit": "listening_candidate",
                "situation_claim_status": "reviewed",
                "situation_sensitivity_flag": "none",
            },
            "listening_policy": {
                "listening_item_type_candidates": ["listen_and_choose_sentence"],
                "listening_item_generation_status": "forbidden_in_schema_design",
                "question_generation_status": "forbidden_in_schema_design",
                "answer_generation_status": "forbidden_in_schema_design",
                "distractor_generation_status": "forbidden_in_schema_design",
                "scoring_status": "forbidden_in_schema_design",
                "student_facing_status": "forbidden_until_later_approval",
            },
            "audio_policy": {
                "audio_generation_status": "forbidden",
                "audio_asset_id": None,
                "audio_asset_path": None,
                "audio_policy_version": "E4S_P5_LISTENING_AUDIO_POLICY_V1",
                "human_audio_permission_status": "not_requested",
            },
            "tts_policy": {
                "tts_permission_status": "forbidden",
                "tts_generation_status": "forbidden",
                "tts_provider": None,
                "tts_voice_id": None,
                "tts_policy_version": "E4S_P5_LISTENING_AUDIO_POLICY_V1",
            },
            "voice_policy": {
                "voice_policy_status": "required_future",
                "voice_policy_version": "E4S_P5_VOICE_POLICY_PLACEHOLDER_V1",
                "accent_label": "not_selected",
                "speed_profile": "not_selected",
                "speaker_role_mapping_status": "not_applicable",
                "pronunciation_override_policy_status": "not_defined",
            },
            "storage_policy": {
                "storage_policy_status": "required_future",
                "storage_policy_version": "E4S_P5_STORAGE_POLICY_PLACEHOLDER_V1",
                "intended_storage_layer": "ulga/listening/candidates",
                "public_storage_status": "blocked",
                "asset_naming_policy_status": "not_applicable_without_audio",
            },
            "timing_policy": {
                "timing_policy_status": "not_created",
                "timing_policy_version": "E4S_P5_TIMING_POLICY_PLACEHOLDER_V1",
                "timing_required_status": "not_applicable_without_audio",
                "timing_metadata_path": None,
                "timing_alignment_method": "none",
            },
            "public_distribution_policy": {
                "public_distribution_status": "blocked",
                "license_clearance_status": "not_cleared_by_default",
                "source_attribution_status": "not_required_internal_only",
                "derivative_audio_permission_status": "not_cleared_by_default",
                "child_safety_status": "reviewed_safe",
                "privacy_status": "no_learner_data",
            },
            "learner_state_policy": {
                "learner_state_update_status": "forbidden",
                "learner_response_capture_status": "forbidden",
                "adaptive_assignment_status": "forbidden",
                "review_scheduling_status": "forbidden",
                "mastery_score_status": "forbidden",
                "weakness_tag_status": "forbidden",
                "placement_status": "forbidden",
            },
            "validator_handoff": {
                "validator_required": True,
                "validator_contract_path": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md",
                "validator_contract_version": "E4S_P5_LISTENING_VALIDATOR_CONTRACT_V1",
                "expected_report_path": "ulga/listening/reports/e4s_listening_validator_report.json",
                "blocking_error_codes_ref": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md#2.6",
                "warning_codes_ref": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md#2.7",
                "pass_fail_gate_ref": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md#2.9",
                "candidate_order_key": "candidate_id",
            },
            "created_by_task_id": "E4S-P5-I1_ListeningValidatorImplementation_TEST_FIXTURE",
            "sentence_id": "sentence_001",
            "sentence_boundary_policy": "sentence_boundary_policy_v1",
            "sentence_context_ref": "fixture:home_request",
            "sentence_order_ref": "1",
            "sentence_audio_scope": "single_sentence",
        }

    def base_package(self, candidates: list[dict] | None = None) -> dict:
        if candidates is None:
            candidates = [self.base_candidate()]
        package = {
            "schema_version": "E4S_LISTENING_CANDIDATE_PACKAGE_V1",
            "epic_id": "E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem",
            "phase_id": "E4S-P5_ListeningPracticeSystem",
            "task_id": "E4S-P5-I1_ListeningValidatorImplementation_TEST_FIXTURE",
            "package_id": "p5_listening_candidate_package_fixture",
            "package_policy": {
                "package_scope": "listening_candidate_metadata_only",
                "candidate_only": True,
                "audio_generation_status": "forbidden_until_later_approval",
                "tts_generation_status": "forbidden_until_later_approval",
                "timing_generation_status": "forbidden_until_later_approval",
                "question_generation_status": "forbidden_until_later_approval",
                "learner_facing_output_status": "forbidden_until_later_approval",
                "validator_required": True,
                "source_promotion_status": "forbidden",
                "content_promotion_status": "forbidden",
                "public_distribution_default": "blocked",
            },
            "source_manifest_ref": {
                "manifest_path": "ulga/graph/e4s_source_manifest.json",
                "manifest_schema_version": "E4S_SOURCE_MANIFEST_V1",
                "manifest_phase_id": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
                "manifest_record_count": 16,
                "manifest_hash_or_commit_ref": "fixture",
                "source_manifest_contract_path": "docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md",
            },
            "validator_contract_ref": {
                "validator_contract_path": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md",
                "validator_contract_task_id": "E4S-P5-S2_ListeningValidatorContract_DesignScan",
                "validator_contract_version": "E4S_P5_LISTENING_VALIDATOR_CONTRACT_V1",
                "required_report_schema_version": "E4S_LISTENING_VALIDATION_REPORT_V1",
                "required_error_code_set": "E4S_P5_BLOCKING_ERRORS_V1",
                "strict_mode_default": False,
            },
            "audio_policy_ref": {
                "audio_policy_path": "docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md",
                "audio_policy_task_id": "E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan",
                "audio_policy_version": "E4S_P5_LISTENING_AUDIO_POLICY_V1",
                "audio_generation_default": "forbidden",
                "tts_generation_default": "forbidden",
                "timing_generation_default": "forbidden",
                "playback_ui_default": "forbidden",
                "voice_policy_required": True,
                "storage_policy_required": True,
            },
            "public_distribution_policy": {
                "public_distribution_status": "blocked",
                "license_clearance_status": "not_cleared_by_default",
                "source_attribution_status": "not_required_internal_only",
                "derivative_audio_permission_status": "not_cleared_by_default",
                "child_safety_status": "reviewed_safe",
                "privacy_status": "no_learner_data",
            },
            "learner_state_policy": {
                "learner_state_update_status": "forbidden",
                "learner_response_capture_status": "forbidden",
                "adaptive_assignment_status": "forbidden",
                "review_scheduling_status": "forbidden",
                "mastery_score_status": "forbidden",
                "weakness_tag_status": "forbidden",
                "placement_status": "forbidden",
            },
            "candidate_counts": {},
            "candidates": candidates,
        }
        package["candidate_counts"] = self.derived_counts(candidates)
        return package

    @staticmethod
    def derived_counts(candidates: list[dict]) -> dict:
        def count(field_getter):
            result: dict[str, int] = {}
            for candidate in candidates:
                value = field_getter(candidate)
                result[str(value)] = result.get(str(value), 0) + 1
            return dict(sorted(result.items()))

        return {
            "total_candidates": len(candidates),
            "by_candidate_type": count(lambda c: c.get("candidate_type")),
            "by_eligibility_class": count(lambda c: c.get("eligibility_class")),
            "by_source_family": count(lambda c: c.get("source_trace", {}).get("source_family")),
            "by_public_distribution_status": count(lambda c: c.get("public_distribution_policy", {}).get("public_distribution_status")),
            "by_learner_facing_status": count(lambda c: c.get("listening_policy", {}).get("student_facing_status")),
            "by_audio_generation_status": count(lambda c: c.get("audio_policy", {}).get("audio_generation_status")),
            "by_validator_readiness": count(lambda c: c.get("validator_handoff", {}).get("validator_required")),
        }

    def assert_issue_code(self, package: dict, code: str) -> None:
        issues = self.validator.validate_package(package, self.manifest)
        self.assertIn(code, {issue.code for issue in issues})

    def test_valid_fixture_passes(self) -> None:
        package = self.base_package()
        issues = self.validator.validate_package(package, self.manifest)
        self.assertEqual([], [issue for issue in issues if issue.severity == "error"])
        report = self.validator.build_report(package, issues)
        self.assertEqual("PASS", report["status"])
        self.assertEqual(1, report["candidate_count"])
        self.assertEqual("PASS", report["gate_metrics"]["source_trace_complete"])

    def test_duplicate_candidate_id_fails(self) -> None:
        first = self.base_candidate()
        second = self.base_candidate()
        package = self.base_package([first, second])
        self.assert_issue_code(package, "P5_DUPLICATE_CANDIDATE_ID")

    def test_non_deterministic_order_fails(self) -> None:
        first = self.base_candidate(candidate_id="p5_sentence_parent_functional_sentence_corpus_reference_sentence_002")
        first["source_trace"]["source_unit_id"] = "sentence_002"
        first["sentence_id"] = "sentence_002"
        second = self.base_candidate(candidate_id="p5_sentence_parent_functional_sentence_corpus_reference_sentence_001")
        package = self.base_package([first, second])
        self.assert_issue_code(package, "P5_NON_DETERMINISTIC_ORDER")

    def test_status_artifact_as_content_fails(self) -> None:
        package = self.base_package()
        candidate = package["candidates"][0]
        candidate["source_trace"].update(
            {
                "source_id": "STATUS_RAZ_AW_V1_SNAPSHOT",
                "source_family": "status_artifact",
                "authority_role": "status_only",
                "license_status": "owned",
                "promotion_rule": "status_artifact_never_content",
            }
        )
        package["candidate_counts"] = self.derived_counts(package["candidates"])
        self.assert_issue_code(package, "P5_STATUS_ARTIFACT_USED_AS_CONTENT")

    def test_raz_wordlist_as_audio_source_fails(self) -> None:
        package = self.base_package()
        candidate = package["candidates"][0]
        candidate["source_trace"].update(
            {
                "source_id": "RAZ_WORDLIST_A_T_EVIDENCE",
                "source_family": "raz_wordlist",
                "authority_role": "evidence_only",
                "license_status": "restricted_reference_only",
                "promotion_rule": "evidence_only_never_authority",
            }
        )
        package["candidate_counts"] = self.derived_counts(package["candidates"])
        self.assert_issue_code(package, "P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE")

    def test_generated_unreviewed_content_fails(self) -> None:
        package = self.base_package()
        candidate = package["candidates"][0]
        candidate["source_trace"].update(
            {
                "source_id": "GENERATED_CONTENT_CANDIDATE_POOL",
                "source_family": "generated_content_candidate",
                "authority_role": "generated_candidate",
                "license_status": "owned",
                "review_status": "not_reviewed",
                "manual_review_status": "not_reviewed",
                "promotion_rule": "candidate_only_until_review",
            }
        )
        package["candidate_counts"] = self.derived_counts(package["candidates"])
        self.assert_issue_code(package, "P5_GENERATED_UNREVIEWED_CONTENT")

    def test_restricted_source_marked_public_fails(self) -> None:
        package = self.base_package()
        candidate = package["candidates"][0]
        candidate["source_trace"].update(
            {
                "source_id": "RAZ_READING_CORPUS_A_T_CANDIDATE",
                "source_family": "raz_reading_corpus",
                "authority_role": "reading_corpus_candidate",
                "license_status": "restricted_reference_only",
            }
        )
        candidate["public_distribution_policy"]["public_distribution_status"] = "public"
        candidate["public_distribution_policy"]["license_clearance_status"] = "not_cleared_by_default"
        package["candidate_counts"] = self.derived_counts(package["candidates"])
        self.assert_issue_code(package, "P5_RESTRICTED_SOURCE_MARKED_PUBLIC")
        self.assert_issue_code(package, "P5_PUBLIC_AUDIO_WITHOUT_LICENSE_CLEARANCE")

    def test_missing_tts_permission_fails(self) -> None:
        package = self.base_package()
        del package["candidates"][0]["tts_policy"]["tts_permission_status"]
        self.assert_issue_code(package, "P5_BAD_SCHEMA_VERSION")
        self.assert_issue_code(package, "P5_MISSING_TTS_PERMISSION")

    def test_learner_state_update_attempt_fails(self) -> None:
        package = self.base_package()
        package["candidates"][0]["learner_state_policy"]["learner_state_update_status"] = "allowed"
        self.assert_issue_code(package, "P5_LEARNER_STATE_UPDATE_ATTEMPT")

    def test_content_promotion_attempt_fails(self) -> None:
        package = self.base_package()
        package["package_policy"]["content_promotion_status"] = "allowed"
        self.assert_issue_code(package, "P5_CONTENT_PROMOTION_ATTEMPT")

    def test_passage_missing_sentence_order_fails(self) -> None:
        candidate = self.base_candidate(candidate_id="p5_passage_parent_functional_sentence_corpus_reference_passage_001")
        candidate["candidate_type"] = "passage_listening_candidate"
        candidate["eligibility_class"] = "P5_ELIGIBLE_VERIFIED_PASSAGE"
        candidate["source_trace"]["source_unit_type"] = "passage"
        candidate["source_text"]["text_segmentation_policy"] = "passage_boundary_policy_v1"
        for field in ["sentence_id", "sentence_boundary_policy", "sentence_context_ref", "sentence_order_ref", "sentence_audio_scope"]:
            candidate.pop(field, None)
        candidate.update(
            {
                "passage_id": "passage_001",
                "sentence_ids": ["s2", "s1"],
                "sentence_order": [2, 1],
                "paragraph_or_page_ref": "fixture:p1",
                "passage_boundary_policy": "passage_boundary_policy_v1",
                "p1_handoff_status": "blocked_pending_review",
            }
        )
        package = self.base_package([candidate])
        self.assert_issue_code(package, "P5_BAD_SEGMENTATION_POLICY")

    def test_cli_report_output_shape_passes(self) -> None:
        package = self.base_package()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            package_path = tmp / "candidate_package.json"
            report_path = tmp / "report.json"
            package_path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
            loaded = self.validator.load_json(package_path, label="Candidate package")
            issues = self.validator.validate_package(loaded, self.manifest)
            report = self.validator.build_report(loaded, issues)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            parsed = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual("E4S_LISTENING_VALIDATION_REPORT_V1", parsed["schema_version"])
            self.assertEqual("PASS", parsed["status"])
            self.assertEqual("E4S-P5-I2_ListeningCandidatePackageBuilderImplementation", parsed["next_shortest_step"])


if __name__ == "__main__":
    unittest.main()
