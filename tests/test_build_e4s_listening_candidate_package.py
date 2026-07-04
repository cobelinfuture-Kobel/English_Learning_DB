"""Tests for the E4S P5 listening candidate package builder."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "tools" / "build_e4s_listening_candidate_package.py"
VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_e4s_listening_candidates.py"
MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BuildE4SListeningCandidatePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = load_module("build_e4s_listening_candidate_package", BUILDER_PATH)
        self.validator = load_module("validate_e4s_listening_candidates", VALIDATOR_PATH)
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def sentence_seed(self, *, source_unit_id: str = "sentence_001", text: str = "Can I have some water?") -> dict:
        return {
            "source_id": "PARENT_FUNCTIONAL_SENTENCE_CORPUS_REFERENCE",
            "source_unit_id": source_unit_id,
            "source_unit_ref": f"test_seed:{source_unit_id}",
            "source_text": text,
            "normalized_level_band": "A1",
            "situation_domain": "home",
            "situation_context": "family_request",
            "communicative_function": "request",
            "interaction_mode": "single_sentence",
            "sentence_context_ref": "test_seed:home_request",
        }

    def dialogue_seed(self) -> dict:
        return {
            "source_id": "STORY_DIALOGUE_CORPUS_REFERENCE",
            "source_unit_id": "dialogue_001",
            "source_unit_ref": "test_seed:dialogue_001",
            "source_text": "Can you help me? Yes, I can.",
            "normalized_level_band": "A1",
            "situation_domain": "school",
            "situation_context": "peer_help",
            "communicative_function": "request_help",
            "interaction_mode": "short_dialogue",
            "dialogue_turns": [
                {"turn_id": "turn_002", "speaker_role": "friend", "speaker_order": 2, "turn_text": "Yes, I can."},
                {"turn_id": "turn_001", "speaker_role": "learner_peer", "speaker_order": 1, "turn_text": "Can you help me?"},
            ],
        }

    def passage_seed(self) -> dict:
        return {
            "source_id": "RAZ_READING_CORPUS_A_T_CANDIDATE",
            "source_unit_id": "passage_001",
            "source_unit_ref": "test_seed:passage_001",
            "source_text": "The cat sits. The dog runs.",
            "normalized_level_band": "A1",
            "situation_domain": "animals",
            "situation_context": "simple_actions",
            "communicative_function": "describe_actions",
            "interaction_mode": "short_passage",
            "sentence_ids": ["s2", "s1"],
            "sentence_order": [2, 1],
            "paragraph_or_page_ref": "test_seed:p1",
        }

    def validate_no_errors(self, package: dict) -> list:
        issues = self.validator.validate_package(package, self.manifest)
        errors = [issue for issue in issues if issue.severity == "error"]
        self.assertEqual([], errors)
        return issues

    def test_empty_package_validates(self) -> None:
        package = self.builder.build_package(self.manifest, [])
        self.assertEqual("E4S_LISTENING_CANDIDATE_PACKAGE_V1", package["schema_version"])
        self.assertEqual(0, package["candidate_counts"]["total_candidates"])
        issues = self.validate_no_errors(package)
        report = self.validator.build_report(package, issues)
        self.assertEqual("PASS", report["status"])

    def test_sentence_seed_builds_validator_clean_package(self) -> None:
        package = self.builder.build_package(self.manifest, [self.sentence_seed()])
        self.assertEqual(1, package["candidate_counts"]["total_candidates"])
        candidate = package["candidates"][0]
        self.assertEqual("sentence_listening_candidate", candidate["candidate_type"])
        self.assertEqual("P5_ELIGIBLE_VERIFIED_SENTENCE", candidate["eligibility_class"])
        self.assertEqual("forbidden", candidate["audio_policy"]["audio_generation_status"])
        issues = self.validate_no_errors(package)
        report = self.validator.build_report(package, issues)
        self.assertEqual("PASS", report["status"])

    def test_builder_sorts_candidates_by_candidate_id(self) -> None:
        seeds = [
            self.sentence_seed(source_unit_id="sentence_002", text="Can I sit here?"),
            self.sentence_seed(source_unit_id="sentence_001", text="Can I have some water?"),
        ]
        package = self.builder.build_package(self.manifest, seeds)
        candidate_ids = [candidate["candidate_id"] for candidate in package["candidates"]]
        self.assertEqual(sorted(candidate_ids), candidate_ids)
        self.validate_no_errors(package)

    def test_dialogue_seed_builds_internal_only_package_with_warning(self) -> None:
        package = self.builder.build_package(self.manifest, [self.dialogue_seed()])
        candidate = package["candidates"][0]
        self.assertEqual("dialogue_listening_candidate", candidate["candidate_type"])
        self.assertEqual([1, 2], [turn["speaker_order"] for turn in candidate["dialogue_turns"]])
        issues = self.validate_no_errors(package)
        warnings = {issue.code for issue in issues if issue.severity == "warning"}
        self.assertIn("P5_WARN_INTERNAL_ONLY_SOURCE", warnings)
        report = self.validator.build_report(package, issues)
        self.assertEqual("PASS_WITH_WARNINGS", report["status"])

    def test_passage_seed_builds_ordered_passage_variant(self) -> None:
        package = self.builder.build_package(self.manifest, [self.passage_seed()])
        candidate = package["candidates"][0]
        self.assertEqual("passage_listening_candidate", candidate["candidate_type"])
        self.assertEqual([1, 2], candidate["sentence_order"])
        self.assertEqual(["s1", "s2"], candidate["sentence_ids"])
        issues = self.validate_no_errors(package)
        warnings = {issue.code for issue in issues if issue.severity == "warning"}
        self.assertIn("P5_WARN_INTERNAL_ONLY_SOURCE", warnings)

    def test_rejects_non_p5_source_family(self) -> None:
        seed = self.sentence_seed()
        seed["source_id"] = "EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE"
        with self.assertRaises(self.builder.BuilderError) as context:
            self.builder.build_package(self.manifest, [seed])
        self.assertEqual("P5_BUILDER_SOURCE_NOT_P5_ELIGIBLE", context.exception.code)

    def test_rejects_dialogue_without_turns(self) -> None:
        seed = self.dialogue_seed()
        seed.pop("dialogue_turns")
        with self.assertRaises(self.builder.BuilderError) as context:
            self.builder.build_package(self.manifest, [seed])
        self.assertEqual("P5_BUILDER_DIALOGUE_TURNS_REQUIRED", context.exception.code)

    def test_candidate_counts_are_derived(self) -> None:
        package = self.builder.build_package(self.manifest, [self.sentence_seed()])
        self.assertEqual({"sentence_listening_candidate": 1}, package["candidate_counts"]["by_candidate_type"])
        self.assertEqual({"P5_ELIGIBLE_VERIFIED_SENTENCE": 1}, package["candidate_counts"]["by_eligibility_class"])
        self.assertEqual({"forbidden": 1}, package["candidate_counts"]["by_audio_generation_status"])
        self.assertEqual({"True": 1}, package["candidate_counts"]["by_validator_readiness"])

    def test_cli_style_temp_output_package_validates(self) -> None:
        package = self.builder.build_package(self.manifest, [self.sentence_seed()], package_id="test_package")
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "package.json"
            output_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            loaded = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual("test_package", loaded["package_id"])
            self.validate_no_errors(loaded)


if __name__ == "__main__":
    unittest.main()
