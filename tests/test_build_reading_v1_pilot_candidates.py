"""Tests for the Reading V1 metadata-only tiny pilot builder."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
BUILDER_PATH = TOOLS_DIR / "build_reading_v1_pilot_candidates.py"
MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"
CANDIDATES_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_pilot_candidates.json"
SUMMARY_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_pilot_summary.json"


def load_builder():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("build_reading_v1_pilot_candidates", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReadingV1PilotBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = load_builder()
        self.manifest = self.builder.load_manifest(MANIFEST_PATH)
        self.candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
        self.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_static_pilot_artifact_has_default_tiny_count(self) -> None:
        self.assertEqual(len(self.candidates), 3)
        self.assertLessEqual(len(self.candidates), self.builder.DEFAULT_MAX_CANDIDATE_COUNT)
        self.assertLessEqual(len(self.candidates), self.builder.HARD_MAX_CANDIDATE_COUNT)
        self.assertEqual(self.summary["candidate_count"], 3)
        self.assertEqual(self.summary["hard_max_candidate_count"], 5)

    def test_builder_hard_cap_blocks_more_than_five(self) -> None:
        with self.assertRaises(self.builder.PilotPolicyError):
            self.builder.ensure_policy_count(6)

    def test_builder_generates_metadata_only_candidates_from_query_helper(self) -> None:
        candidates, query_report = self.builder.build_candidates(self.manifest, MANIFEST_PATH, 3)
        self.assertEqual(len(candidates), 3)
        self.assertIn(query_report["status"], {self.builder.PASS, self.builder.PASS_WITH_WARNINGS})
        self.assertEqual(
            {candidate["source_trace"]["source_id"] for candidate in candidates},
            {"RAZ_READING_CORPUS_A_T_CANDIDATE"},
        )

    def test_raz_reading_source_is_trace_seed_only(self) -> None:
        for candidate in self.candidates:
            source_trace = candidate["source_trace"]
            self.assertEqual(source_trace["source_id"], "RAZ_READING_CORPUS_A_T_CANDIDATE")
            self.assertEqual(source_trace["authority_role"], "reading_corpus_candidate")
            self.assertEqual(source_trace["source_family"], "raz_reading_corpus")
            self.assertTrue(source_trace["source_trace_required"])
            self.assertFalse(source_trace["source_payload_copied"])

    def test_raz_wordlist_remains_evidence_only_reference(self) -> None:
        for candidate in self.candidates:
            refs = candidate["constraint_refs"]
            self.assertEqual(refs["wordlist_evidence_ref"], "source:RAZ_WORDLIST_A_T_EVIDENCE")
            self.assertNotEqual(candidate["source_trace"]["source_id"], "RAZ_WORDLIST_A_T_EVIDENCE")

    def test_reference_sources_remain_reference_only(self) -> None:
        for candidate in self.candidates:
            refs = candidate["constraint_refs"]
            self.assertEqual(refs["grammar_reference_ref"], "source:EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE")
            self.assertEqual(refs["vocabulary_reference_ref"], "source:EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE")
            self.assertEqual(refs["frequency_reference_ref"], "source:NGSL_SOURCE_FREQUENCY_PROFILE")
            self.assertEqual(refs["chunk_reference_ref"], "source:CHUNK_SAFE_LAYER_REFERENCE")

    def test_candidates_use_allowed_question_types_only(self) -> None:
        question_types = {candidate["question_model"]["question_type"] for candidate in self.candidates}
        self.assertEqual(question_types, {"literal_what", "literal_where", "literal_yes_no"})
        self.assertNotIn("inference", question_types)
        self.assertNotIn("multi_source_reasoning", question_types)

    def test_no_source_payload_or_excerpts_are_present(self) -> None:
        forbidden_keys = {"passage_text", "source_text", "evidence_text", "passage_excerpt"}
        for candidate in self.candidates:
            serialized = json.dumps(candidate, ensure_ascii=False)
            self.assertFalse(any(key in candidate for key in forbidden_keys))
            self.assertNotIn("source PDFs", serialized)
            self.assertFalse(candidate["reading_payload_ref"]["passage_excerpt_allowed"])
            self.assertFalse(candidate["evidence_model"]["evidence_text_allowed"])
            self.assertTrue(candidate["evidence_model"]["evidence_locator"])

    def test_all_unsafe_flags_remain_false(self) -> None:
        for candidate in self.candidates:
            source_policy = candidate["source_policy"]
            self.assertFalse(source_policy["public_distribution_allowed"])
            self.assertFalse(source_policy["learner_facing_allowed"])
            self.assertFalse(source_policy["authority_promotion_allowed"])
            self.assertFalse(candidate["level_metadata"]["learner_placement_allowed"])
            self.assertFalse(candidate["skill_metadata"]["multi_skill_expansion_allowed"])
            for value in candidate["blocked_output_state"].values():
                self.assertFalse(value)

    def test_summary_matches_policy_and_next_step(self) -> None:
        self.assertEqual(self.summary["schema_version"], "READING_V1_PILOT_SUMMARY_V1")
        self.assertTrue(self.summary["metadata_only"])
        self.assertFalse(self.summary["payload_access_allowed"])
        self.assertFalse(self.summary["learner_facing_allowed"])
        self.assertFalse(self.summary["authority_upgrade_allowed"])
        self.assertEqual(self.summary["issues"], [])
        self.assertEqual(self.summary["status"], self.builder.PASS_WITH_WARNINGS)
        self.assertEqual(self.summary["next_shortest_step"], "E4S-P1-S11_ReadingV1_PilotCandidateReadbackQA")

    def test_policy_validator_accepts_static_candidates(self) -> None:
        self.assertEqual(self.builder.validate_candidates_against_policy(self.candidates), [])


if __name__ == "__main__":
    unittest.main()
