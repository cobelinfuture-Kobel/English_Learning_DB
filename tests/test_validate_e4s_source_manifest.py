"""Tests for the E4S source manifest validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_e4s_source_manifest.py"
MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_e4s_source_manifest", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ValidateE4SSourceManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def assert_issue_code(self, manifest: dict, code: str) -> None:
        issues = self.validator.validate_manifest(manifest)
        self.assertIn(code, {issue.code for issue in issues})

    def test_current_manifest_passes(self) -> None:
        issues = self.validator.validate_manifest(self.manifest)
        self.assertEqual([], issues)

    def test_duplicate_source_id_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["records"][1]["source_id"] = manifest["records"][0]["source_id"]
        self.assert_issue_code(manifest, "E4S_SOURCE_DUPLICATE_ID")

    def test_non_deterministic_order_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["records"][0], manifest["records"][1] = manifest["records"][1], manifest["records"][0]
        self.assert_issue_code(manifest, "E4S_SOURCE_NON_DETERMINISTIC_ORDER")

    def test_unknown_enum_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["records"][0]["source_family"] = "bad_family"
        self.assert_issue_code(manifest, "E4S_SOURCE_UNKNOWN_ENUM")

    def test_allowed_blocked_conflict_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["records"][0]["allowed_use"].append("learner_facing_output")
        self.assert_issue_code(manifest, "E4S_SOURCE_ALLOWED_BLOCKED_CONFLICT")

    def test_empty_allowed_use_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["records"][0]["allowed_use"] = []
        self.assert_issue_code(manifest, "E4S_SOURCE_EMPTY_ALLOWED_USE")

    def test_restricted_reference_without_public_distribution_block_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        record = next(item for item in manifest["records"] if item["license_status"] == "restricted_reference_only")
        record["blocked_use"] = [item for item in record["blocked_use"] if item != "public_distribution"]
        self.assert_issue_code(manifest, "E4S_SOURCE_RESTRICTED_WITHOUT_PUBLIC_BLOCK")

    def test_raz_wordlist_direct_vocab_authority_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        record = next(item for item in manifest["records"] if item["source_family"] == "raz_wordlist")
        record["authority_role"] = "primary_authority"
        self.assert_issue_code(manifest, "E4S_RAZ_WORDLIST_BAD_AUTHORITY_ROLE")

    def test_generated_content_without_promotion_blocks_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        record = next(item for item in manifest["records"] if item["source_family"] == "generated_content_candidate")
        record["blocked_use"] = [item for item in record["blocked_use"] if item != "automatic_promotion"]
        self.assert_issue_code(manifest, "E4S_GENERATED_PROMOTION_NOT_BLOCKED")

    def test_status_artifact_as_reading_authority_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        record = next(item for item in manifest["records"] if item["source_family"] == "status_artifact")
        record["authority_role"] = "reading_corpus_candidate"
        self.assert_issue_code(manifest, "E4S_STATUS_BAD_AUTHORITY_ROLE")

    def test_bad_artifact_policy_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact_policy"]["authority_promotion"] = "allowed"
        self.assert_issue_code(manifest, "E4S_MANIFEST_BAD_ARTIFACT_POLICY")

    def test_cli_report_output_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "validation_report.json"
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

            loaded = self.validator.load_manifest(manifest_path)
            report = self.validator.build_report(self.validator.validate_manifest(loaded))
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

            parsed = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["status"], "PASS")
            self.assertEqual(parsed["next_shortest_step"], "E4S-P0-S4_AuthorityMappingMatrix_DesignScan")


if __name__ == "__main__":
    unittest.main()
