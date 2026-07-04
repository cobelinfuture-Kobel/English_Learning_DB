#!/usr/bin/env python3
"""Build E4S P5 listening candidate packages.

Scope:
- E4S-P5-I2 metadata-only candidate package builder implementation.
- Builds package JSON conforming to the P5-S1/S2/S3 contracts and I1 validator.
- Reads source manifest metadata and explicit seed candidate metadata.
- Does not generate audio, TTS, timing, questions, UI, learner state, or source/content promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "ulga" / "listening" / "candidates" / "e4s_listening_candidate_package.json"

EXPECTED_SOURCE_MANIFEST_SCHEMA_VERSION = "E4S_SOURCE_MANIFEST_V1"
EXPECTED_SOURCE_MANIFEST_PHASE_ID = "E4S-P0_SourceAuthorityAndCorpusRoadmap"
EXPECTED_SOURCE_MANIFEST_CONTRACT_PATH = "docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md"

PACKAGE_SCHEMA_VERSION = "E4S_LISTENING_CANDIDATE_PACKAGE_V1"
EPIC_ID = "E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem"
PHASE_ID = "E4S-P5_ListeningPracticeSystem"
TASK_ID = "E4S-P5-I2_ListeningCandidatePackageBuilderImplementation"
PACKAGE_ID = "p5_listening_candidate_package_v1"

VALIDATOR_CONTRACT_PATH = "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md"
VALIDATOR_CONTRACT_TASK_ID = "E4S-P5-S2_ListeningValidatorContract_DesignScan"
VALIDATOR_CONTRACT_VERSION = "E4S_P5_LISTENING_VALIDATOR_CONTRACT_V1"
VALIDATION_REPORT_SCHEMA_VERSION = "E4S_LISTENING_VALIDATION_REPORT_V1"

AUDIO_POLICY_PATH = "docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md"
AUDIO_POLICY_TASK_ID = "E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan"
AUDIO_POLICY_VERSION = "E4S_P5_LISTENING_AUDIO_POLICY_V1"

SOURCE_FAMILY_TO_CANDIDATE_TYPE = {
    "parent_functional_sentence_corpus": "sentence_listening_candidate",
    "story_dialogue_corpus": "dialogue_listening_candidate",
    "raz_reading_corpus": "passage_listening_candidate",
}

CANDIDATE_TYPE_TO_UNIT_TYPE = {
    "sentence_listening_candidate": "sentence",
    "dialogue_listening_candidate": "dialogue",
    "passage_listening_candidate": "passage",
}

CANDIDATE_TYPE_TO_ELIGIBILITY = {
    "sentence_listening_candidate": "P5_ELIGIBLE_VERIFIED_SENTENCE",
    "dialogue_listening_candidate": "P5_ELIGIBLE_VERIFIED_DIALOGUE",
    "passage_listening_candidate": "P5_ELIGIBLE_VERIFIED_PASSAGE",
}

APPROVED_FAMILY_ROLES = {
    "parent_functional_sentence_corpus": {"functional_sentence_corpus"},
    "story_dialogue_corpus": {"dialogue_corpus_candidate"},
    "raz_reading_corpus": {"reading_corpus_candidate"},
}

PUBLIC_BLOCKED_VALUES = {"blocked", "internal_only", "forbidden"}


@dataclass(frozen=True)
class BuilderError(Exception):
    """Deterministic builder failure."""

    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def load_json(path: Path, *, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {path}: {exc}") from exc


def load_source_manifest(path: Path) -> dict[str, Any]:
    payload = load_json(path, label="Source manifest")
    if not isinstance(payload, dict):
        raise SystemExit("Source manifest root must be a JSON object.")
    if payload.get("schema_version") != EXPECTED_SOURCE_MANIFEST_SCHEMA_VERSION:
        raise SystemExit(f"Source manifest schema_version must be {EXPECTED_SOURCE_MANIFEST_SCHEMA_VERSION}.")
    records = payload.get("records")
    if not isinstance(records, list):
        raise SystemExit("Source manifest records must be an array.")
    return payload


def load_seed_candidates(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = load_json(path, label="Listening seed candidates")
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        payload = payload["candidates"]
    if not isinstance(payload, list):
        raise SystemExit("Listening seed candidates must be a JSON array or an object with candidates array.")
    seeds: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise SystemExit(f"Seed candidate at index {index} must be an object.")
        seeds.append(item)
    return seeds


def source_records_by_id(source_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = source_manifest.get("records", [])
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            by_id[record["source_id"]] = record
    return by_id


def build_package(source_manifest: dict[str, Any], seeds: list[dict[str, Any]], *, package_id: str = PACKAGE_ID) -> dict[str, Any]:
    records_by_id = source_records_by_id(source_manifest)
    candidates = [build_candidate(seed, records_by_id) for seed in seeds]
    candidates = sorted(candidates, key=lambda candidate: candidate["candidate_id"])

    package = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "epic_id": EPIC_ID,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "package_id": package_id,
        "package_policy": build_package_policy(),
        "source_manifest_ref": build_source_manifest_ref(source_manifest),
        "validator_contract_ref": build_validator_contract_ref(),
        "audio_policy_ref": build_audio_policy_ref(),
        "public_distribution_policy": build_public_distribution_policy(),
        "learner_state_policy": build_learner_state_policy(),
        "candidate_counts": {},
        "candidates": candidates,
    }
    package["candidate_counts"] = derive_candidate_counts(candidates)
    return package


def build_candidate(seed: dict[str, Any], records_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_id = _required_str(seed, "source_id")
    source_unit_id = _required_str(seed, "source_unit_id")
    source_text = _required_str(seed, "source_text")

    record = records_by_id.get(source_id)
    if record is None:
        raise BuilderError("P5_BUILDER_UNKNOWN_SOURCE_ID", f"source_id not found in source manifest: {source_id}")

    source_family = _required_record_str(record, "source_family", source_id)
    authority_role = _required_record_str(record, "authority_role", source_id)
    candidate_type = str(seed.get("candidate_type") or SOURCE_FAMILY_TO_CANDIDATE_TYPE.get(source_family, ""))

    validate_source_for_candidate(record, candidate_type)

    source_unit_type = str(seed.get("source_unit_type") or CANDIDATE_TYPE_TO_UNIT_TYPE[candidate_type])
    eligibility_class = str(seed.get("eligibility_class") or CANDIDATE_TYPE_TO_ELIGIBILITY[candidate_type])
    candidate_id = str(seed.get("candidate_id") or deterministic_candidate_id(candidate_type, source_id, source_unit_id))
    text_segmentation_policy = str(seed.get("text_segmentation_policy") or f"{source_unit_type}_boundary_policy_v1")

    candidate: dict[str, Any] = {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "eligibility_class": eligibility_class,
        "candidate_status": "candidate_only",
        "source_trace": build_source_trace(record, source_unit_id, source_unit_type, seed),
        "source_text": build_source_text(source_text, text_segmentation_policy, seed),
        "source_metadata": build_source_metadata(record, seed),
        "level_situation_metadata": build_level_situation_metadata(seed),
        "listening_policy": build_listening_policy(candidate_type),
        "audio_policy": build_candidate_audio_policy(),
        "tts_policy": build_tts_policy(),
        "voice_policy": build_voice_policy(candidate_type),
        "storage_policy": build_storage_policy(),
        "timing_policy": build_timing_policy(),
        "public_distribution_policy": build_candidate_public_distribution_policy(record),
        "learner_state_policy": build_learner_state_policy(),
        "validator_handoff": build_validator_handoff(),
        "created_by_task_id": TASK_ID,
    }

    if candidate_type == "sentence_listening_candidate":
        candidate.update(build_sentence_variant(source_unit_id, seed))
    elif candidate_type == "dialogue_listening_candidate":
        candidate.update(build_dialogue_variant(source_unit_id, seed))
    elif candidate_type == "passage_listening_candidate":
        candidate.update(build_passage_variant(source_unit_id, seed))
    else:
        raise BuilderError("P5_BUILDER_BAD_CANDIDATE_TYPE", f"Unsupported candidate_type: {candidate_type}")

    return candidate


def validate_source_for_candidate(record: dict[str, Any], candidate_type: str) -> None:
    source_id = _required_record_str(record, "source_id", "<unknown>")
    source_family = _required_record_str(record, "source_family", source_id)
    authority_role = _required_record_str(record, "authority_role", source_id)
    license_status = _required_record_str(record, "license_status", source_id)
    blocked_use = record.get("blocked_use", [])

    expected_type = SOURCE_FAMILY_TO_CANDIDATE_TYPE.get(source_family)
    if expected_type is None:
        raise BuilderError("P5_BUILDER_SOURCE_NOT_P5_ELIGIBLE", f"source_family={source_family!r} cannot be used for P5 candidate package data.")
    if candidate_type != expected_type:
        raise BuilderError("P5_BUILDER_BAD_CANDIDATE_TYPE", f"source_family={source_family!r} requires candidate_type={expected_type!r}.")
    if authority_role not in APPROVED_FAMILY_ROLES[source_family]:
        raise BuilderError("P5_BUILDER_UNAPPROVED_AUTHORITY_ROLE", f"authority_role={authority_role!r} is not approved for {source_family!r}.")
    if license_status in {"restricted_reference_only", "not_redistributable"} and "public_distribution" not in blocked_use:
        raise BuilderError("P5_BUILDER_RESTRICTED_SOURCE_NOT_BLOCKED", f"Restricted source {source_id} must block public_distribution.")


def deterministic_candidate_id(candidate_type: str, source_id: str, source_unit_id: str) -> str:
    type_short = {
        "sentence_listening_candidate": "sentence",
        "dialogue_listening_candidate": "dialogue",
        "passage_listening_candidate": "passage",
    }.get(candidate_type, "unknown")
    return f"p5_{type_short}_{slug(source_id)}_{slug(source_unit_id)}"


def slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def stable_manifest_ref(record: dict[str, Any]) -> str:
    source_id = str(record.get("source_id", "unknown"))
    path = str(record.get("path", ""))
    digest = hashlib.sha256(f"{source_id}|{path}".encode("utf-8")).hexdigest()[:12]
    return f"manifest:{source_id}:{digest}"


def build_source_trace(record: dict[str, Any], source_unit_id: str, source_unit_type: str, seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": record["source_id"],
        "source_family": record["source_family"],
        "authority_role": record["authority_role"],
        "source_path_or_reference": record.get("path", ""),
        "source_record_hash_or_stable_ref": stable_manifest_ref(record),
        "source_unit_id": source_unit_id,
        "source_unit_type": source_unit_type,
        "source_unit_ref": str(seed.get("source_unit_ref") or f"seed:{source_unit_id}"),
        "license_status": record.get("license_status", "unknown_pending_review"),
        "review_status": str(seed.get("review_status") or record.get("review_status") or "metadata_reviewed"),
        "promotion_rule": record.get("promotion_rule", "candidate_only_until_review"),
        "allowed_use": list(record.get("allowed_use", [])),
        "blocked_use": list(record.get("blocked_use", [])),
        "manual_review_status": str(seed.get("manual_review_status") or "metadata_reviewed"),
        "public_distribution_status": "blocked",
    }


def build_source_text(source_text: str, text_segmentation_policy: str, seed: dict[str, Any]) -> dict[str, Any]:
    normalized = str(seed.get("source_text_normalized") or " ".join(source_text.split()))
    return {
        "source_text_raw": source_text,
        "source_text_normalized": normalized,
        "text_language": str(seed.get("text_language") or "en"),
        "text_normalization_policy": str(seed.get("text_normalization_policy") or "p5_text_normalization_v1"),
        "text_segmentation_policy": text_segmentation_policy,
        "text_review_status": str(seed.get("text_review_status") or "metadata_reviewed"),
        "sensitive_content_review_status": str(seed.get("sensitive_content_review_status") or "reviewed_safe"),
        "child_suitability_review_status": str(seed.get("child_suitability_review_status") or "reviewed_safe"),
    }


def build_source_metadata(record: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_title_or_display_name": str(record.get("display_name") or record.get("source_id")),
        "source_level_system": str(seed.get("source_level_system") or "internal"),
        "raw_level_code": str(seed.get("raw_level_code") or "A1"),
        "normalized_level_band": str(seed.get("normalized_level_band") or "A1"),
        "level_claim_status": str(seed.get("level_claim_status") or "reviewed"),
        "source_owner_or_origin": str(seed.get("source_owner_or_origin") or record.get("license_status", "unknown")),
        "source_license_note": str(seed.get("source_license_note") or record.get("license_status", "unknown")),
        "source_review_owner": str(seed.get("source_review_owner") or "operator"),
        "source_review_date_or_ref": str(seed.get("source_review_date_or_ref") or "seed_review"),
    }


def build_level_situation_metadata(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "normalized_level_band": str(seed.get("normalized_level_band") or "A1"),
        "level_claim_status": str(seed.get("level_claim_status") or "reviewed"),
        "situation_domain": str(seed.get("situation_domain") or "daily_life"),
        "situation_context": str(seed.get("situation_context") or "functional_communication"),
        "communicative_function": str(seed.get("communicative_function") or "request"),
        "interaction_mode": str(seed.get("interaction_mode") or "single_sentence"),
        "skill_fit": "listening_candidate",
        "situation_claim_status": str(seed.get("situation_claim_status") or "reviewed"),
        "situation_sensitivity_flag": str(seed.get("situation_sensitivity_flag") or "none"),
    }


def build_listening_policy(candidate_type: str) -> dict[str, Any]:
    type_candidates = {
        "sentence_listening_candidate": ["listen_and_choose_sentence", "dictation_lite"],
        "dialogue_listening_candidate": ["short_dialogue_listening"],
        "passage_listening_candidate": ["passage_main_idea_listening", "listen_and_order_sentences"],
    }[candidate_type]
    return {
        "listening_item_type_candidates": type_candidates,
        "listening_item_generation_status": "forbidden_in_schema_design",
        "question_generation_status": "forbidden_in_schema_design",
        "answer_generation_status": "forbidden_in_schema_design",
        "distractor_generation_status": "forbidden_in_schema_design",
        "scoring_status": "forbidden_in_schema_design",
        "student_facing_status": "forbidden_until_later_approval",
    }


def build_candidate_audio_policy() -> dict[str, Any]:
    return {
        "audio_generation_status": "forbidden",
        "audio_asset_id": None,
        "audio_asset_path": None,
        "audio_policy_version": AUDIO_POLICY_VERSION,
        "human_audio_permission_status": "not_requested",
    }


def build_tts_policy() -> dict[str, Any]:
    return {
        "tts_permission_status": "forbidden",
        "tts_generation_status": "forbidden",
        "tts_provider": None,
        "tts_voice_id": None,
        "tts_policy_version": AUDIO_POLICY_VERSION,
    }


def build_voice_policy(candidate_type: str) -> dict[str, Any]:
    speaker_mapping = "required_future" if candidate_type == "dialogue_listening_candidate" else "not_applicable"
    return {
        "voice_policy_status": "required_future",
        "voice_policy_version": "E4S_P5_VOICE_POLICY_PLACEHOLDER_V1",
        "accent_label": "not_selected",
        "speed_profile": "not_selected",
        "speaker_role_mapping_status": speaker_mapping,
        "pronunciation_override_policy_status": "not_defined",
    }


def build_storage_policy() -> dict[str, Any]:
    return {
        "storage_policy_status": "required_future",
        "storage_policy_version": "E4S_P5_STORAGE_POLICY_PLACEHOLDER_V1",
        "intended_storage_layer": "ulga/listening/candidates",
        "public_storage_status": "blocked",
        "asset_naming_policy_status": "not_applicable_without_audio",
    }


def build_timing_policy() -> dict[str, Any]:
    return {
        "timing_policy_status": "not_created",
        "timing_policy_version": "E4S_P5_TIMING_POLICY_PLACEHOLDER_V1",
        "timing_required_status": "not_applicable_without_audio",
        "timing_metadata_path": None,
        "timing_alignment_method": "none",
    }


def build_candidate_public_distribution_policy(record: dict[str, Any]) -> dict[str, Any]:
    license_status = str(record.get("license_status") or "unknown_pending_review")
    attribution_status = "not_required_internal_only" if license_status == "owned" else "required_before_public_use"
    return {
        "public_distribution_status": "blocked",
        "license_clearance_status": "not_cleared_by_default",
        "source_attribution_status": attribution_status,
        "derivative_audio_permission_status": "not_cleared_by_default",
        "child_safety_status": "reviewed_safe",
        "privacy_status": "no_learner_data",
    }


def build_learner_state_policy() -> dict[str, Any]:
    return {
        "learner_state_update_status": "forbidden",
        "learner_response_capture_status": "forbidden",
        "adaptive_assignment_status": "forbidden",
        "review_scheduling_status": "forbidden",
        "mastery_score_status": "forbidden",
        "weakness_tag_status": "forbidden",
        "placement_status": "forbidden",
    }


def build_validator_handoff() -> dict[str, Any]:
    return {
        "validator_required": True,
        "validator_contract_path": VALIDATOR_CONTRACT_PATH,
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
        "expected_report_path": "ulga/listening/reports/e4s_listening_validator_report.json",
        "blocking_error_codes_ref": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md#2.6",
        "warning_codes_ref": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md#2.7",
        "pass_fail_gate_ref": "docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md#2.9",
        "candidate_order_key": "candidate_id",
    }


def build_sentence_variant(source_unit_id: str, seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "sentence_id": str(seed.get("sentence_id") or source_unit_id),
        "sentence_boundary_policy": str(seed.get("sentence_boundary_policy") or "sentence_boundary_policy_v1"),
        "sentence_context_ref": str(seed.get("sentence_context_ref") or f"seed_context:{source_unit_id}"),
        "sentence_order_ref": str(seed.get("sentence_order_ref") or "1"),
        "sentence_audio_scope": "single_sentence",
    }


def build_dialogue_variant(source_unit_id: str, seed: dict[str, Any]) -> dict[str, Any]:
    turns = seed.get("dialogue_turns")
    if not isinstance(turns, list) or not turns:
        raise BuilderError("P5_BUILDER_DIALOGUE_TURNS_REQUIRED", "dialogue_listening_candidate requires non-empty dialogue_turns seed data.")
    normalized_turns = []
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            raise BuilderError("P5_BUILDER_DIALOGUE_TURNS_REQUIRED", f"dialogue_turns[{index}] must be an object.")
        normalized_turns.append(
            {
                "turn_id": str(turn.get("turn_id") or f"turn_{index + 1:03d}"),
                "speaker_role": str(turn.get("speaker_role") or f"speaker_{index + 1}"),
                "speaker_order": int(turn.get("speaker_order") or index + 1),
                "turn_text": str(turn.get("turn_text") or "").strip(),
                "turn_boundary_policy": str(turn.get("turn_boundary_policy") or "dialogue_turn_boundary_policy_v1"),
            }
        )
    normalized_turns = sorted(normalized_turns, key=lambda turn: turn["speaker_order"])
    if any(not turn["turn_text"] for turn in normalized_turns):
        raise BuilderError("P5_BUILDER_DIALOGUE_TURNS_REQUIRED", "Every dialogue turn requires turn_text.")
    return {
        "dialogue_id": str(seed.get("dialogue_id") or source_unit_id),
        "dialogue_turns": normalized_turns,
        "turn_count": len(normalized_turns),
        "speaker_roles": sorted({turn["speaker_role"] for turn in normalized_turns}),
        "speaker_order_policy": "speaker_order_ascending",
        "multi_speaker_audio_policy": "required_future_before_audio",
        "p4_handoff_status": str(seed.get("p4_handoff_status") or "blocked_pending_review"),
    }


def build_passage_variant(source_unit_id: str, seed: dict[str, Any]) -> dict[str, Any]:
    sentence_ids = seed.get("sentence_ids")
    sentence_order = seed.get("sentence_order")
    if not isinstance(sentence_ids, list) or not sentence_ids:
        raise BuilderError("P5_BUILDER_PASSAGE_SENTENCES_REQUIRED", "passage_listening_candidate requires non-empty sentence_ids seed data.")
    if sentence_order is None:
        sentence_order = list(range(1, len(sentence_ids) + 1))
    if not isinstance(sentence_order, list) or len(sentence_order) != len(sentence_ids):
        raise BuilderError("P5_BUILDER_PASSAGE_SENTENCES_REQUIRED", "sentence_order must align with sentence_ids.")
    ordered_pairs = sorted(zip(sentence_order, sentence_ids), key=lambda item: item[0])
    return {
        "passage_id": str(seed.get("passage_id") or source_unit_id),
        "sentence_ids": [str(sentence_id) for _, sentence_id in ordered_pairs],
        "sentence_order": [int(order) for order, _ in ordered_pairs],
        "paragraph_or_page_ref": str(seed.get("paragraph_or_page_ref") or f"seed_passage:{source_unit_id}"),
        "passage_boundary_policy": str(seed.get("passage_boundary_policy") or "passage_boundary_policy_v1"),
        "p1_handoff_status": str(seed.get("p1_handoff_status") or "blocked_pending_review"),
    }


def build_package_policy() -> dict[str, Any]:
    return {
        "package_scope": "listening_candidate_metadata_only",
        "candidate_only": True,
        "audio_generation_status": "forbidden_until_later_approval",
        "tts_generation_status": "forbidden_until_later_approval",
        "timing_generation_status": "forbidden_until_later_approval",
        "question_generation_status": "forbidden_until_later_approval",
        "learner_facing_output_status": "forbidden_until_later_approval",
        "validator_required": True,
        "source_promotion_status": "forbidden",
        "content_promotion_status": "forbidden",
        "public_distribution_default": "blocked",
    }


def build_source_manifest_ref(source_manifest: dict[str, Any]) -> dict[str, Any]:
    records = source_manifest.get("records", []) if isinstance(source_manifest.get("records"), list) else []
    return {
        "manifest_path": "ulga/graph/e4s_source_manifest.json",
        "manifest_schema_version": source_manifest.get("schema_version", EXPECTED_SOURCE_MANIFEST_SCHEMA_VERSION),
        "manifest_phase_id": source_manifest.get("phase_id", EXPECTED_SOURCE_MANIFEST_PHASE_ID),
        "manifest_record_count": len(records),
        "manifest_hash_or_commit_ref": stable_json_digest(source_manifest),
        "source_manifest_contract_path": source_manifest.get("contract_path", EXPECTED_SOURCE_MANIFEST_CONTRACT_PATH),
    }


def build_validator_contract_ref() -> dict[str, Any]:
    return {
        "validator_contract_path": VALIDATOR_CONTRACT_PATH,
        "validator_contract_task_id": VALIDATOR_CONTRACT_TASK_ID,
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
        "required_report_schema_version": VALIDATION_REPORT_SCHEMA_VERSION,
        "required_error_code_set": "E4S_P5_BLOCKING_ERRORS_V1",
        "strict_mode_default": False,
    }


def build_audio_policy_ref() -> dict[str, Any]:
    return {
        "audio_policy_path": AUDIO_POLICY_PATH,
        "audio_policy_task_id": AUDIO_POLICY_TASK_ID,
        "audio_policy_version": AUDIO_POLICY_VERSION,
        "audio_generation_default": "forbidden",
        "tts_generation_default": "forbidden",
        "timing_generation_default": "forbidden",
        "playback_ui_default": "forbidden",
        "voice_policy_required": True,
        "storage_policy_required": True,
    }


def build_public_distribution_policy() -> dict[str, Any]:
    return {
        "public_distribution_status": "blocked",
        "license_clearance_status": "not_cleared_by_default",
        "source_attribution_status": "not_required_internal_only",
        "derivative_audio_permission_status": "not_cleared_by_default",
        "child_safety_status": "reviewed_safe",
        "privacy_status": "no_learner_data",
    }


def derive_candidate_counts(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_candidates": len(candidates),
        "by_candidate_type": _counter(candidates, lambda candidate: candidate.get("candidate_type")),
        "by_eligibility_class": _counter(candidates, lambda candidate: candidate.get("eligibility_class")),
        "by_source_family": _counter(candidates, lambda candidate: candidate.get("source_trace", {}).get("source_family")),
        "by_public_distribution_status": _counter(candidates, lambda candidate: candidate.get("public_distribution_policy", {}).get("public_distribution_status")),
        "by_learner_facing_status": _counter(candidates, lambda candidate: candidate.get("listening_policy", {}).get("student_facing_status")),
        "by_audio_generation_status": _counter(candidates, lambda candidate: candidate.get("audio_policy", {}).get("audio_generation_status")),
        "by_validator_readiness": _counter(candidates, lambda candidate: candidate.get("validator_handoff", {}).get("validator_required")),
    }


def _counter(candidates: list[dict[str, Any]], getter) -> dict[str, int]:
    counter = Counter(str(getter(candidate)) for candidate in candidates)
    return {key: counter[key] for key in sorted(counter)}


def stable_json_digest(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _required_str(seed: dict[str, Any], field: str) -> str:
    value = seed.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BuilderError("P5_BUILDER_MISSING_SEED_FIELD", f"Seed candidate requires non-empty string field: {field}.")
    return value.strip()


def _required_record_str(record: dict[str, Any], field: str, source_id: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BuilderError("P5_BUILDER_BAD_SOURCE_RECORD", f"Source record {source_id} requires non-empty string field: {field}.")
    return value.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an E4S P5 listening candidate package.")
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST_PATH)
    parser.add_argument("--seed-candidates", type=Path, default=None, help="JSON array or object with candidates array. Defaults to an empty metadata package.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--package-id", default=PACKAGE_ID)
    parser.add_argument("--dry-run", action="store_true", help="Print package JSON without writing output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_manifest = load_source_manifest(args.source_manifest)
    seeds = load_seed_candidates(args.seed_candidates)
    try:
        package = build_package(source_manifest, seeds, package_id=args.package_id)
    except BuilderError as exc:
        raise SystemExit(str(exc)) from exc

    output = json.dumps(package, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(output, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
