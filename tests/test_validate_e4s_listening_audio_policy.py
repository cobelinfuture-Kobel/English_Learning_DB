"""Tests for E4S P5 audio / voice / storage policy validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate_e4s_listening_audio_policy.py"
POLICY_PATH = ROOT / "ulga" / "listening" / "policies" / "e4s_p5_audio_voice_storage_policy_v1.json"
PACKAGE_PATH = ROOT / "ulga" / "listening" / "candidates" / "e4s_listening_candidate_package.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_e4s_listening_audio_policy", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ValidateE4SListeningAudioPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()
        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    def issue_codes(self, package: dict | None = None, policy: dict | None = None) -> set[str]:
        issues = self.validator.validate(policy or self.policy, package or self.package)
        return {item["code"] for item in issues}

    def errors(self, package: dict | None = None, policy: dict | None = None) -> list[dict]:
        return [item for item in self.validator.validate(policy or self.policy, package or self.package) if item["severity"] == "error"]

    def test_current_package_has_no_blocking_errors(self) -> None:
        issues = self.validator.validate(self.policy, self.package)
        self.assertEqual([], [item for item in issues if item["severity"] == "error"])
        report = self.validator.build_report(self.policy, self.package, issues)
        self.assertEqual("PASS_WITH_WARNINGS", report["status"])
        self.assertEqual(3, report["candidate_count"])
        self.assertEqual(0, report["audio_asset_count"])
        self.assertEqual("PASS", report["audio_policy_status"])
        self.assertEqual("PASS", report["storage_policy_status"])

    def test_policy_id_mismatch_fails(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["policy_id"] = "BAD_POLICY"
        self.assertIn("P5_AUDIO_POLICY_VERSION_MISSING", self.issue_codes(policy=policy))

    def test_audio_path_outside_internal_layer_fails(self) -> None:
        package = copy.deepcopy(self.package)
        candidate = package["candidates"][0]
        candidate["audio_policy"]["audio_asset_id"] = "audio_001"
        candidate["audio_policy"]["audio_asset_path"] = "site/listening/audio_001.mp3"
        self.assertIn("P5_AUDIO_ASSET_PATH_NOT_INTERNAL", self.issue_codes(package=package))
        self.assertIn("P5_LEARNER_FACING_AUDIO_ATTEMPT", self.issue_codes(package=package))

    def test_public_audio_attempt_fails(self) -> None:
        package = copy.deepcopy(self.package)
        candidate = package["candidates"][0]
        candidate["audio_policy"]["audio_asset_id"] = "audio_001"
        candidate["audio_policy"]["audio_asset_path"] = "ulga/listening/audio_internal/pkg/cand/audio_001.mp3"
        candidate["public_distribution_policy"]["public_distribution_status"] = "public"
        self.assertIn("P5_AUDIO_PUBLIC_DISTRIBUTION_ATTEMPT", self.issue_codes(package=package))

    def test_dialogue_audio_requires_speaker_mapping(self) -> None:
        package = copy.deepcopy(self.package)
        candidate = next(item for item in package["candidates"] if item["candidate_type"] == "dialogue_listening_candidate")
        candidate["audio_policy"]["audio_asset_id"] = "audio_dialogue_001"
        candidate["audio_policy"]["audio_asset_path"] = "ulga/listening/audio_internal/pkg/dialogue/audio_dialogue_001.mp3"
        candidate["voice_policy"]["speaker_role_mapping_status"] = "required_future"
        self.assertIn("P5_DIALOGUE_VOICE_MAPPING_MISSING", self.issue_codes(package=package))

    def test_timing_without_audio_asset_fails(self) -> None:
        package = copy.deepcopy(self.package)
        candidate = package["candidates"][0]
        candidate["timing_policy"]["timing_metadata_path"] = "ulga/listening/timing_internal/pkg/cand/timing.json"
        self.assertIn("P5_TIMING_WITHOUT_AUDIO_ASSET", self.issue_codes(package=package))

    def test_tts_scope_must_be_internal_only(self) -> None:
        package = copy.deepcopy(self.package)
        candidate = package["candidates"][0]
        candidate["tts_policy"]["tts_generation_status"] = "generated"
        candidate["tts_policy"]["tts_provider"] = "fixture_tts"
        self.assertIn("P5_TTS_SCOPE_NOT_INTERNAL_ONLY", self.issue_codes(package=package))


if __name__ == "__main__":
    unittest.main()
