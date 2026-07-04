"""Tests for Reading V1 manual review decision artifacts."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "tools" / "build_reading_v1_manual_review_decisions.py"
QUEUE_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_manual_review_queue.json"
DECISIONS_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_manual_review_decisions.json"
SUMMARY_PATH = REPO_ROOT / "ulga" / "reports" / "reading_v1_manual_review_decision_summary.json"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_reading_v1_manual_review_decisions", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReadingV1ManualReviewDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = load_builder()
        self.queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        self.decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
        self.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_decision_artifact_has_one_decision_per_queue_item(self) -> None:
        self.assertEqual(self.decisions["schema_version"], "READING_V1_MANUAL_REVIEW_DECISIONS_V1")
        self.assertEqual(self.decisions["candidate_count"], 3)
        self.assertEqual(self.decisions["decision_count"], 3)
        self.assertEqual(len(self.decisions["decisions"]), 3)
        self.assertEqual(
            {decision["candidate_id"] for decision in self.decisions["decisions"]},
            {"reading_v1_pilot_001", "reading_v1_pilot_002", "reading_v1_pilot_003"},
        )

    def test_current_decisions_require_revision_and_level_review(self) -> None:
        for decision in self.decisions["decisions"]:
            self.assertTrue(decision["review_completed"])
            self.assertEqual(decision["review_status"], "needs_revision")
            self.assertEqual(decision["decision"], "needs_level_review")
            self.assertTrue(decision["candidate_can_remain_internal"])
            self.assertTrue(decision["candidate_requires_revision"])
            self.assertFalse(decision["candidate_rejected"])
            self.assertIn("level_band_unknown", decision["next_gate_blockers"])

    def test_decisions_do_not_authorize_outputs_or_source_display(self) -> None:
        top_level_false_fields = [
            "learner_facing_allowed",
            "worksheet_allowed",
            "public_preview_allowed",
            "authority_upgrade_allowed",
            "source_payload_display_allowed",
            "evidence_text_display_allowed",
        ]
        for field in top_level_false_fields:
            self.assertFalse(self.decisions[field])
        for decision in self.decisions["decisions"]:
            for field in top_level_false_fields:
                self.assertFalse(decision[field])
            self.assertFalse(decision["source_excerpt_display_allowed"])
            self.assertFalse(decision["next_gate_eligible"])
            self.assertTrue(decision["source_payload_display_blocked"])
            self.assertEqual(decision["display_outcome"], "source_payload_display_blocked")

    def test_decisions_carry_policy_and_queue_references(self) -> None:
        for decision in self.decisions["decisions"]:
            self.assertEqual(decision["manual_review_queue_ref"], "ulga/reports/reading_v1_manual_review_queue.json")
            self.assertEqual(
                decision["source_payload_display_policy_ref"],
                "docs/ulga/E4S_P1_READING_V1_SOURCE_PAYLOAD_DISPLAY_POLICY.md",
            )
            self.assertIn("ulga/reports/reading_v1_validation_report.json", decision["evidence_refs"])
            self.assertIn("ulga/reports/reading_v1_pilot_candidates.json", decision["evidence_refs"])

    def test_builder_rebuilds_same_conservative_decision_shape(self) -> None:
        rebuilt = self.builder.build_decisions(
            self.queue,
            "ulga/reports/reading_v1_manual_review_queue.json",
            "docs/ulga/E4S_P1_READING_V1_SOURCE_PAYLOAD_DISPLAY_POLICY.md",
        )
        self.assertEqual(rebuilt["candidate_count"], 3)
        self.assertEqual(rebuilt["decision_count"], 3)
        self.assertEqual(rebuilt["decisions"][0]["review_status"], "needs_revision")
        self.assertEqual(rebuilt["decisions"][0]["decision"], "needs_level_review")
        self.assertEqual(rebuilt["decisions"][0]["display_outcome"], "source_payload_display_blocked")
        self.assertEqual(self.builder.validate_decisions(rebuilt), [])

    def test_summary_records_no_next_gate_eligibility(self) -> None:
        self.assertEqual(self.summary["schema_version"], "READING_V1_MANUAL_REVIEW_DECISION_SUMMARY_V1")
        self.assertEqual(self.summary["candidate_count"], 3)
        self.assertEqual(self.summary["completed_decision_count"], 3)
        self.assertEqual(self.summary["decision_counts"], {"needs_level_review": 3})
        self.assertEqual(self.summary["review_status_counts"], {"needs_revision": 3})
        self.assertEqual(self.summary["passed_internal_review_count"], 0)
        self.assertEqual(self.summary["next_gate_eligible_count"], 0)
        self.assertEqual(self.summary["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(self.summary["next_shortest_step"], "LearnerFacingOutputGate_Reopen_DesignScan")

    def test_invalid_output_approval_fails_validation(self) -> None:
        artifact = json.loads(json.dumps(self.decisions))
        artifact["decisions"][0]["learner_facing_allowed"] = True
        errors = self.builder.validate_decisions(artifact)
        self.assertTrue(any("learner_facing_allowed" in error for error in errors))

    def test_invalid_next_gate_eligibility_fails_validation(self) -> None:
        artifact = json.loads(json.dumps(self.decisions))
        artifact["decisions"][0]["next_gate_eligible"] = True
        errors = self.builder.validate_decisions(artifact)
        self.assertTrue(any("next_gate_eligible" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
