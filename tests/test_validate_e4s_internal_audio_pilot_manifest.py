"""Tests for E4S P5 internal audio pilot manifest validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate_e4s_internal_audio_pilot_manifest.py"
MANIFEST_PATH = ROOT / "ulga" / "listening" / "audio_manifests" / "e4s_p5_seed_batch_001_internal_audio_pilot_manifest.json"
PACKAGE_PATH = ROOT / "ulga" / "listening" / "candidates" / "e4s_listening_candidate_package.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_e4s_internal_audio_pilot_manifest", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ValidateE4SInternalAudioPilotManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    def codes(self, manifest: dict | None = None) -> set[str]:
        return {item["code"] for item in self.validator.validate(manifest or self.manifest, self.package)}

    def test_current_manifest_passes_with_one_metadata_asset(self) -> None:
        issues = self.validator.validate(self.manifest, self.package)
        self.assertEqual([], [item for item in issues if item["severity"] == "error"])
        report = self.validator.build_report(self.manifest, issues)
        self.assertEqual("PASS", report["status"])
        self.assertEqual(1, report["selected_candidate_count"])
        self.assertEqual(1, report["audio_asset_count"])
        self.assertEqual(1, report["internal_audio_asset_count"])
        self.assertEqual(0, report["public_audio_asset_count"])
        self.assertEqual(0, report["learner_facing_audio_count"])

    def test_bad_schema_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["schema_version"] = "BAD_SCHEMA"
        self.assertIn("P5_AUDIO_PILOT_BAD_SCHEMA", self.codes(manifest))

    def test_unknown_selected_candidate_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["selected_candidates"][0]["candidate_id"] = "missing_candidate"
        codes = self.codes(manifest)
        self.assertIn("P5_AUDIO_PILOT_UNKNOWN_CANDIDATE", codes)
        self.assertIn("P5_AUDIO_PILOT_UNAPPROVED_CANDIDATE", codes)

    def test_unapproved_dialogue_candidate_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["selected_candidates"][0]["candidate_id"] = "p5_dialogue_story_dialogue_corpus_reference_p5_dialogue_002"
        self.assertIn("P5_AUDIO_PILOT_UNAPPROVED_CANDIDATE", self.codes(manifest))

    def test_public_metadata_asset_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["audio_assets"][0]["public_distribution_status"] = "public"
        self.assertIn("P5_AUDIO_PILOT_PUBLIC_OR_LEARNER_OPEN", self.codes(manifest))

    def test_realized_audio_status_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["audio_assets"][0]["audio_generation_status"] = "done"
        self.assertIn("P5_AUDIO_PILOT_AUDIO_GENERATED", self.codes(manifest))


if __name__ == "__main__":
    unittest.main()
