"""Contract tests for the Reading V1 candidate schema."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "ulga" / "schemas" / "reading_v1_candidate.schema.json"


class ReadingV1CandidateSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.defs = self.schema["$defs"]

    def test_schema_has_expected_identity(self) -> None:
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.schema["title"], "E4S Reading V1 Candidate Schema")
        self.assertEqual(self.schema["properties"]["schema_version"]["const"], "READING_V1_CANDIDATE_SCHEMA_V1")
        self.assertEqual(
            self.schema["properties"]["phase_id"]["const"],
            "E4S-P1_ReadingV1SourceGroundedPractice",
        )

    def test_top_level_required_fields_match_contract(self) -> None:
        expected = {
            "reading_candidate_id",
            "schema_version",
            "phase_id",
            "task_id",
            "candidate_status",
            "source_trace",
            "source_policy",
            "reading_payload_ref",
            "question_model",
            "answer_model",
            "evidence_model",
            "level_metadata",
            "situation_metadata",
            "skill_metadata",
            "constraint_refs",
            "validation_state",
            "manual_review_state",
            "blocked_output_state",
            "audit_trail",
        }
        self.assertEqual(set(self.schema["required"]), expected)
        self.assertFalse(self.schema["additionalProperties"])

    def test_candidate_status_and_question_type_are_bounded(self) -> None:
        statuses = set(self.schema["properties"]["candidate_status"]["enum"])
        self.assertIn("design_only", statuses)
        self.assertIn("validator_passed", statuses)
        self.assertIn("rejected", statuses)

        question_types = set(self.defs["question_model"]["properties"]["question_type"]["enum"])
        self.assertIn("literal_who", question_types)
        self.assertIn("vocabulary_in_context_basic", question_types)
        self.assertNotIn("inference", question_types)
        self.assertNotIn("multi_source_reasoning", question_types)

    def test_source_trace_preserves_raz_contract(self) -> None:
        source_trace = self.defs["source_trace"]
        required = set(source_trace["required"])
        self.assertIn("source_id", required)
        self.assertIn("authority_role", required)
        self.assertIn("source_payload_copied", required)
        self.assertEqual(source_trace["properties"]["source_payload_copied"]["const"], False)

        condition_blocks = source_trace["allOf"]
        raz_reading_block = condition_blocks[0]["then"]["properties"]
        self.assertEqual(raz_reading_block["source_family"]["const"], "raz_reading_corpus")
        self.assertEqual(raz_reading_block["authority_role"]["const"], "reading_corpus_candidate")
        self.assertEqual(raz_reading_block["source_trace_required"]["const"], True)
        self.assertEqual(raz_reading_block["source_payload_copied"]["const"], False)

        raz_wordlist_block = condition_blocks[1]["then"]["properties"]
        self.assertEqual(raz_wordlist_block["source_family"]["const"], "raz_wordlist")
        self.assertEqual(raz_wordlist_block["authority_role"]["const"], "evidence_only")

    def test_source_policy_blocks_promotion_and_learner_facing_use(self) -> None:
        source_policy = self.defs["source_policy"]["properties"]
        self.assertEqual(source_policy["public_distribution_allowed"]["const"], False)
        self.assertEqual(source_policy["learner_facing_allowed"]["const"], False)
        self.assertEqual(source_policy["authority_promotion_allowed"]["const"], False)

    def test_evidence_answer_and_level_safety_rules_are_present(self) -> None:
        answer_model = self.defs["answer_model"]
        self.assertIn("answer_evidence_ref", answer_model["required"])
        self.assertIn("distractors", answer_model["allOf"][0]["then"]["required"])

        evidence_model = self.defs["evidence_model"]
        self.assertIn("source_trace_ref", evidence_model["required"])
        self.assertIn("evidence_locator", evidence_model["required"])

        level_metadata = self.defs["level_metadata"]
        self.assertEqual(level_metadata["properties"]["learner_placement_allowed"]["const"], False)

    def test_blocked_output_state_requires_all_p1_blocks_to_remain_false(self) -> None:
        blocked_output_state = self.defs["blocked_output_state"]
        expected_false_fields = {
            "learner_facing_output_created",
            "student_html_created",
            "worksheet_created",
            "learner_event_created",
            "learner_state_updated",
            "adaptive_recommendation_created",
            "authority_promotion_performed",
            "large_scale_generation_performed",
        }
        self.assertEqual(set(blocked_output_state["required"]), expected_false_fields)
        for field in expected_false_fields:
            self.assertEqual(blocked_output_state["properties"][field]["const"], False, field)

    def test_skill_metadata_blocks_multiskill_expansion(self) -> None:
        skill_metadata = self.defs["skill_metadata"]["properties"]
        self.assertEqual(skill_metadata["skill_fit"]["const"], "reading_candidate")
        self.assertEqual(skill_metadata["target_phase"]["const"], "E4S-P1_ReadingV1SourceGroundedPractice")
        self.assertEqual(skill_metadata["multi_skill_expansion_allowed"]["const"], False)


if __name__ == "__main__":
    unittest.main()
