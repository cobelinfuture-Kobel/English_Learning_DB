"""Tests for the E4S source manifest builder."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "tools" / "build_e4s_source_manifest.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_e4s_source_manifest", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildE4SSourceManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = load_builder()

    def test_manifest_records_are_deterministically_sorted(self) -> None:
        manifest = self.builder.build_manifest()
        source_ids = [record["source_id"] for record in manifest["records"]]
        self.assertEqual(source_ids, sorted(source_ids))

    def test_manifest_records_have_required_fields(self) -> None:
        manifest = self.builder.build_manifest()
        required = set(self.builder.REQUIRED_FIELDS)

        for record in manifest["records"]:
            self.assertTrue(required.issubset(record.keys()), record["source_id"])
            self.assertTrue(record["allowed_use"], record["source_id"])
            self.assertFalse(set(record["allowed_use"]) & set(record["blocked_use"]), record["source_id"])

    def test_contract_specific_safety_rules_are_seeded(self) -> None:
        manifest = self.builder.build_manifest()
        records = {record["source_id"]: record for record in manifest["records"]}

        raz_wordlist = records["RAZ_WORDLIST_A_T_EVIDENCE"]
        self.assertEqual(raz_wordlist["authority_role"], "evidence_only")
        self.assertIn("direct_vocab_authority", raz_wordlist["blocked_use"])
        self.assertEqual(raz_wordlist["promotion_rule"], "evidence_only_never_authority")

        generated = records["GENERATED_CONTENT_CANDIDATE_POOL"]
        self.assertEqual(generated["authority_role"], "generated_candidate")
        self.assertIn("automatic_promotion", generated["blocked_use"])
        self.assertIn("final_authority_promotion", generated["blocked_use"])

        status = records["STATUS_RAZ_AW_V1_SNAPSHOT"]
        self.assertEqual(status["authority_role"], "status_only")
        self.assertEqual(status["promotion_rule"], "status_artifact_never_content")
        self.assertIn("direct_reading_authority", status["blocked_use"])

    def test_summary_matches_manifest_counts(self) -> None:
        manifest = self.builder.build_manifest()
        summary = self.builder.build_summary(manifest)

        self.assertEqual(summary["record_count"], len(manifest["records"]))
        self.assertEqual(summary["gate_metrics"]["manifest_created"], "PASS")
        self.assertEqual(summary["gate_metrics"]["authority_promotion"], "NOT_PERFORMED")
        self.assertEqual(summary["next_shortest_step"], "E4S-P0-S3_SourceManifestValidator_Implementation")

    def test_builder_writes_manifest_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            manifest_path = tmp / "manifest.json"
            summary_path = tmp / "summary.json"

            self.builder.build_and_write(manifest_path, summary_path)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["schema_version"], "E4S_SOURCE_MANIFEST_V1")
            self.assertEqual(summary["source_manifest_schema_version"], manifest["schema_version"])
            self.assertEqual(summary["record_count"], len(manifest["records"]))


if __name__ == "__main__":
    unittest.main()
