"""Tests for the Reading V1 metadata-only source query helper."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "tools" / "query_e4s_reading_v1_sources.py"
MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"


def load_helper():
    spec = importlib.util.spec_from_file_location("query_e4s_reading_v1_sources", HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class QueryE4SReadingV1SourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = load_helper()
        self.manifest = self.helper.load_manifest(MANIFEST_PATH)

    def query(self, mode: str) -> dict:
        return self.helper.build_report(self.manifest, MANIFEST_PATH, mode)

    def test_primary_reading_candidates_returns_raz_reading_corpus_only(self) -> None:
        report = self.query("primary_reading_candidates")
        source_ids = [record["source_id"] for record in report["records"]]

        self.assertEqual(report["status"], self.helper.PASS_WITH_WARNINGS)
        self.assertEqual(source_ids, ["RAZ_READING_CORPUS_A_T_CANDIDATE"])
        record = report["records"][0]
        self.assertEqual(record["query_class"], "PRIMARY_READING_CANDIDATE_INPUT")
        self.assertEqual(record["authority_role"], "reading_corpus_candidate")
        self.assertFalse(record["payload_access_allowed"])
        self.assertFalse(record["learner_facing_allowed"])
        self.assertFalse(record["authority_upgrade_allowed"])

    def test_supporting_evidence_sources_returns_raz_wordlist_as_evidence_only(self) -> None:
        report = self.query("supporting_evidence_sources")
        self.assertEqual([record["source_id"] for record in report["records"]], ["RAZ_WORDLIST_A_T_EVIDENCE"])
        record = report["records"][0]
        self.assertEqual(record["query_class"], "SUPPORTING_READING_EXPOSURE_EVIDENCE")
        self.assertEqual(record["authority_role"], "evidence_only")
        self.assertIn("direct_vocab_authority", record["blocked_use_snapshot"])

    def test_reference_constraint_sources_are_reference_only(self) -> None:
        report = self.query("reference_constraint_sources")
        source_ids = {record["source_id"] for record in report["records"]}

        self.assertEqual(
            source_ids,
            {
                "CHUNK_SAFE_LAYER_REFERENCE",
                "EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE",
                "EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE",
                "NGSL_SOURCE_FREQUENCY_PROFILE",
            },
        )
        for record in report["records"]:
            self.assertEqual(record["authority_role"], "reference_only")
            self.assertFalse(record["payload_access_allowed"])
            self.assertFalse(record["learner_facing_allowed"])
            self.assertFalse(record["authority_upgrade_allowed"])

    def test_blocked_sources_include_status_generated_and_out_of_scope_records(self) -> None:
        report = self.query("blocked_sources")
        by_id = {record["source_id"]: record for record in report["records"]}

        self.assertEqual(by_id["STATUS_RAZ_AW_V1_SNAPSHOT"]["query_class"], "STATUS_AUDIT_ONLY")
        self.assertEqual(
            by_id["GENERATED_CONTENT_CANDIDATE_POOL"]["query_class"],
            "GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT",
        )
        self.assertEqual(
            by_id["ASSESSMENT_PATTERN_CORPUS_REFERENCE"]["query_class"],
            "OUT_OF_SCOPE_SKILL_CANDIDATE",
        )
        self.assertEqual(by_id["ROADMAP_E4S_CORPUS_AND_FOUR_SKILL_SYSTEM"]["query_class"], "GOVERNANCE_ONLY")

    def test_candidate_trace_seed_contains_no_payload_or_generated_content_fields(self) -> None:
        report = self.query("candidate_trace_seed")
        forbidden_keys = {
            "passage_text",
            "question_text",
            "answer_text",
            "evidence_text",
            "learner_event",
            "student_html",
            "worksheet",
        }

        self.assertTrue(report["records"])
        for record in report["records"]:
            self.assertTrue(forbidden_keys.isdisjoint(record.keys()))
            self.assertEqual(record["source_payload_copied"], False)
            self.assertEqual(record["source_unit_ref_policy"], "locator_only_until_payload_policy")
            self.assertEqual(record["constraint_ref_policy"], "reference_only_no_authority_upgrade")
            self.assertFalse(record["source_policy_snapshot"]["payload_access_allowed"])
            self.assertFalse(record["source_policy_snapshot"]["learner_facing_allowed"])
            self.assertFalse(record["source_policy_snapshot"]["authority_upgrade_allowed"])

    def test_output_is_deterministically_sorted(self) -> None:
        report = self.query("eligible_reading_sources")
        records = report["records"]
        self.assertEqual(records, sorted(records, key=self.helper.deterministic_sort_key))
        self.assertEqual(records[0]["source_id"], "RAZ_READING_CORPUS_A_T_CANDIDATE")
        self.assertEqual(records[1]["source_id"], "RAZ_WORDLIST_A_T_EVIDENCE")

    def test_unknown_query_mode_returns_structured_failure_report(self) -> None:
        report = self.query("bad_mode")
        self.assertEqual(report["status"], self.helper.FAIL)
        self.assertEqual(report["issues"][0]["code"], "READING_V1_QUERY_UNKNOWN_MODE")
        self.assertEqual(report["records"], [])

    def test_missing_manifest_cli_writes_structured_report_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "query_report.json"
            missing_path = Path(tmpdir) / "missing_manifest.json"
            exit_code = self.helper.main(
                [
                    "--manifest-path",
                    str(missing_path),
                    "--query-mode",
                    "eligible_reading_sources",
                    "--output-report",
                    str(output_path),
                ]
            )
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], self.helper.FAIL)
        self.assertEqual(report["issues"][0]["code"], "READING_V1_QUERY_MANIFEST_MISSING")
        self.assertEqual(report["next_shortest_step"], "E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA")

    def test_report_summary_marks_metadata_only_and_no_unsafe_access(self) -> None:
        report = self.query("eligible_reading_sources")
        summary = report["summary"]
        self.assertTrue(summary["metadata_only"])
        self.assertFalse(summary["payload_access_allowed"])
        self.assertFalse(summary["learner_facing_allowed"])
        self.assertFalse(summary["authority_upgrade_allowed"])
        self.assertEqual(report["next_shortest_step"], "E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA")


if __name__ == "__main__":
    unittest.main()
