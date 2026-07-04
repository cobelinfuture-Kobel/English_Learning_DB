"""Tests for Reading V1 manual review queue artifact builder."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
BUILDER_PATH = TOOLS_DIR / "build_reading_v1_manual_review_queue.py"
CANDIDATES_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_pilot_candidates.json"
VALIDATION_REPORT_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_validation_report.json"
QUEUE_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_manual_review_queue.json"
SUMMARY_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_manual_review_queue_summary.json"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_reading_v1_manual_review_queue", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReadingV1ManualReviewQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = load_builder()
        self.candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
        self.validation_report = json.loads(VALIDATION_REPORT_PATH.read_text(encoding="utf-8"))
        self.queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        self.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_static_queue_artifact_has_one_item_per_candidate(self) -> None:
        self.assertEqual(self.queue["schema_version"], "READING_V1_MANUAL_REVIEW_QUEUE_V1")
        self.assertEqual(self.queue["candidate_count"], 3)
        self.assertEqual(self.queue["queue_item_count"], 3)
        self.assertEqual(len(self.queue["items"]), 3)
        self.assertEqual(
            {item["candidate_id"] for item in self.queue["items"]},
            {"reading_v1_pilot_001", "reading_v1_pilot_002", "reading_v1_pilot_003"},
        )

    def test_all_queue_items_start_pending_without_output_approval(self) -> None:
        for item in self.queue["items"]:
            self.assertEqual(item["review_status"], "pending")
            self.assertEqual(item["decision"], "pending")
            self.assertEqual(item["handoff_gate"], "manual_review_pending")
            self.assertFalse(item["learner_facing_allowed"])
            self.assertFalse(item["worksheet_allowed"])
            self.assertFalse(item["public_preview_allowed"])
            self.assertFalse(item["authority_upgrade_allowed"])

    def test_queue_carries_validation_warning_refs_for_each_candidate(self) -> None:
        for item in self.queue["items"]:
            codes = {warning["code"] for warning in item["validator_warning_refs"]}
            self.assertEqual(codes, {"READING_V1_MANUAL_REVIEW_PENDING", "READING_V1_LEVEL_BAND_UNKNOWN"})
            self.assertEqual(item["review_priority"], "P2_level_or_metadata_review")
            self.assertEqual(item["level_review"]["status"], "needs_review")

    def test_queue_dimensions_match_design_contract(self) -> None:
        required_dimensions = {
            "source_trace_review",
            "payload_policy_review",
            "question_review",
            "answer_review",
            "evidence_review",
            "level_review",
            "situation_skill_review",
            "blocked_output_review",
        }
        for item in self.queue["items"]:
            self.assertTrue(required_dimensions.issubset(item.keys()))
            for dimension in required_dimensions:
                self.assertIn("status", item[dimension])
                self.assertFalse(item[dimension]["learner_facing_authorized"])
                self.assertTrue(item[dimension]["requires_human_confirmation"])

    def test_builder_rebuilds_equivalent_queue_shape_from_inputs(self) -> None:
        rebuilt = self.builder.build_queue(
            self.candidates,
            self.validation_report,
            Path("ulga/reports/reading_v1_pilot_candidates.json"),
            Path("ulga/reports/reading_v1_validation_report.json"),
        )
        self.assertEqual(rebuilt["candidate_count"], 3)
        self.assertEqual(rebuilt["queue_item_count"], 3)
        self.assertEqual(rebuilt["learner_facing_allowed"], False)
        self.assertEqual(rebuilt["items"][0]["review_status"], "pending")
        self.assertEqual(rebuilt["items"][0]["decision"], "pending")
        self.assertEqual(self.builder.validate_queue(rebuilt), [])

    def test_summary_records_pending_counts_and_blocked_output(self) -> None:
        self.assertEqual(self.summary["schema_version"], "READING_V1_MANUAL_REVIEW_QUEUE_SUMMARY_V1")
        self.assertEqual(self.summary["candidate_count"], 3)
        self.assertEqual(self.summary["queue_item_count"], 3)
        self.assertEqual(self.summary["pending_count"], 3)
        self.assertEqual(self.summary["passed_internal_review_count"], 0)
        self.assertEqual(self.summary["validation_status"], "PASS_WITH_WARNINGS")
        self.assertFalse(self.summary["learner_facing_allowed"])
        self.assertFalse(self.summary["worksheet_allowed"])
        self.assertFalse(self.summary["public_preview_allowed"])
        self.assertFalse(self.summary["authority_upgrade_allowed"])
        self.assertEqual(self.summary["next_shortest_step"], "SourcePayloadDisplayPolicy_DesignScan")

    def test_reviewer_fields_exclude_learner_private_data_and_answer_history(self) -> None:
        forbidden_terms = ["learner_private_data", "learner_answer_history", "student_answer_history"]
        for item in self.queue["items"]:
            serialized = json.dumps(item["reviewer_fields"], ensure_ascii=False)
            for term in forbidden_terms:
                self.assertNotIn(term, serialized)
            self.assertIn("No learner private data or learner answer history", serialized)

    def test_invalid_output_approval_fails_validation(self) -> None:
        queue = json.loads(json.dumps(self.queue))
        queue["items"][0]["learner_facing_allowed"] = True
        errors = self.builder.validate_queue(queue)
        self.assertTrue(any("learner_facing_allowed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
