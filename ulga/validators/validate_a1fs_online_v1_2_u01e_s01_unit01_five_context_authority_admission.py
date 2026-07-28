#!/usr/bin/env python3
"""Validate the Unit 01 five-context material-first authority admission."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as builder,
)
from ulga.query.a1_a1plus_authority_scope_query import build_scope

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_ONLINE_V1_2_U01E_S01_FIVE_CONTEXT_AUTHORITY_ADMISSION_VALIDATOR"


class S01ValidationError(ValueError):
    """Fail-closed S01 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise S01ValidationError(code)


def receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("unit_id") == builder.m01.UNIT_ID, "unit_identity_invalid")
    require(payload.get("level_scope") == ["A1"], "level_scope_invalid")
    require(payload.get("selection_model") == "MATERIAL_FIRST_AUTHORITY_CONTROLLED", "selection_model_invalid")

    contexts = payload.get("contexts")
    require(isinstance(contexts, list) and len(contexts) == builder.EXPECTED_CONTEXT_COUNT, "context_count_invalid")
    require(len({row.get("context_id") for row in contexts}) == len(contexts), "context_identity_duplicate")
    require(
        {row.get("role") for row in contexts}
        == {"ANCHOR_CONTEXT", "NEAR_TRANSFER", "EXTENDED_CONTEXT", "FUNCTIONAL_DIALOGUE_CONTEXT", "UNSEEN_TRANSFER"},
        "context_role_set_invalid",
    )
    anchor = next(row for row in contexts if row.get("role") == "ANCHOR_CONTEXT")
    require(" ".join(anchor.get("sentences", [])) == builder.m01.PASSAGE, "anchor_passage_identity_invalid")
    material = f" {builder.phrase(' '.join(sentence for row in contexts for sentence in row.get('sentences', [])))} "

    scope = build_scope("A1")
    authority_ids = {
        name: {str(row.get("id")) for row in scope["authorities"][name]}
        for name in ("vocabulary", "chunk", "pattern", "grammar")
    }
    language = payload.get("language_targets")
    require(isinstance(language, Mapping), "language_targets_missing")

    vocabulary = language.get("vocabulary")
    require(isinstance(vocabulary, list), "vocabulary_targets_missing")
    productive = [row for row in vocabulary if row.get("learning_role") == "NEW_PRODUCTIVE"]
    receptive = [row for row in vocabulary if row.get("learning_role") == "NEW_RECEPTIVE"]
    require(builder.PRODUCTIVE_TARGET_RANGE[0] <= len(productive) <= builder.PRODUCTIVE_TARGET_RANGE[1], "productive_load_invalid")
    require(builder.RECEPTIVE_TARGET_RANGE[0] <= len(receptive) <= builder.RECEPTIVE_TARGET_RANGE[1], "receptive_load_invalid")
    require(len({row.get("authority_id") for row in vocabulary}) == len(vocabulary), "vocabulary_identity_duplicate")
    for row in vocabulary:
        ref = str(row.get("authority_id") or "")
        require(ref in authority_ids["vocabulary"], f"vocabulary_ref_invalid:{ref}")
        label = builder.phrase(str(row.get("label") or ""))
        require(label and label in set(builder.words(material)), f"vocabulary_not_in_material:{ref}")
        require(row.get("sense_binding_status") == "UNIQUE_A1_SOURCE_RECORD_ID_BOUND", f"vocabulary_sense_status_invalid:{ref}")

    chunks = language.get("canonical_chunks")
    require(isinstance(chunks, list), "canonical_chunk_targets_missing")
    require(
        builder.CANONICAL_CHUNK_TARGET_RANGE[0] <= len(chunks) <= builder.CANONICAL_CHUNK_TARGET_RANGE[1],
        "canonical_chunk_load_invalid",
    )
    require(len({row.get("authority_id") for row in chunks}) == len(chunks), "chunk_identity_duplicate")
    for row in chunks:
        ref = str(row.get("authority_id") or "")
        require(ref in authority_ids["chunk"], f"chunk_ref_invalid:{ref}")
        label = builder.phrase(str(row.get("label") or ""))
        require(label and f" {label} " in material, f"chunk_not_in_material:{ref}")
        require(row.get("coverage_eligible_as_canonical_chunk") is True, f"chunk_coverage_flag_invalid:{ref}")
        require(row.get("learning_role") == "NEW_CANONICAL_CHUNK", f"chunk_learning_role_invalid:{ref}")

    context_phrases = language.get("context_phrases")
    require(isinstance(context_phrases, list) and context_phrases, "context_phrase_targets_missing")
    require(len({row.get("phrase_id") for row in context_phrases}) == len(context_phrases), "context_phrase_identity_duplicate")
    canonical_labels = {builder.phrase(str(row.get("label") or "")) for row in chunks}
    for row in context_phrases:
        phrase_id = str(row.get("phrase_id") or "")
        label = builder.phrase(str(row.get("label") or ""))
        require(phrase_id.startswith("phrase:u01e:"), f"context_phrase_id_invalid:{phrase_id}")
        require(label and f" {label} " in material, f"context_phrase_not_in_material:{phrase_id}")
        require(label not in canonical_labels, f"context_phrase_duplicates_canonical_chunk:{phrase_id}")
        require(row.get("authority_status") == "PROJECT_PHRASE_NOT_CANONICAL_CHUNK", f"context_phrase_authority_status_invalid:{phrase_id}")
        require(row.get("coverage_eligible_as_canonical_chunk") is False, f"context_phrase_canonical_coverage_invalid:{phrase_id}")
    total_chunk_or_phrase = len(chunks) + len(context_phrases)
    require(
        builder.TOTAL_CHUNK_OR_PHRASE_RANGE[0]
        <= total_chunk_or_phrase
        <= builder.TOTAL_CHUNK_OR_PHRASE_RANGE[1],
        "combined_chunk_phrase_load_invalid",
    )

    sentences = language.get("sentences")
    require(isinstance(sentences, list) and sentences, "sentence_targets_missing")
    require(len({row.get("sentence_id") for row in sentences}) == len(sentences), "sentence_identity_duplicate")
    require(
        set(row.get("context_id") for row in sentences) == set(row.get("context_id") for row in contexts),
        "sentence_context_coverage_invalid",
    )
    core_sentences = [row for row in sentences if row.get("learning_role") == "CORE_NEW_SENTENCE"]
    require(builder.CORE_SENTENCE_RANGE[0] <= len(core_sentences) <= builder.CORE_SENTENCE_RANGE[1], "core_sentence_load_invalid")

    patterns = language.get("patterns")
    require(isinstance(patterns, list) and patterns, "pattern_targets_missing")
    for row in patterns:
        require(str(row.get("authority_id") or "") in authority_ids["pattern"], "pattern_ref_invalid")
    egp_rows = language.get("egp_row_ids")
    require(isinstance(egp_rows, list) and egp_rows, "egp_targets_missing")
    require(set(egp_rows).issubset(authority_ids["grammar"]), "egp_ref_invalid")

    cambridge = payload.get("cambridge_alignment", {})
    require(cambridge.get("cambridge_stage") == "STARTERS", "cambridge_stage_invalid")
    require(cambridge.get("policy_decision") == "AUTO_PASS", "cambridge_policy_decision_invalid")
    require(cambridge.get("granular_capability_refs") == [], "unproven_cambridge_capability_ref")
    require(
        cambridge.get("granular_capability_status") == "UNRESOLVED_COMMITTED_DENOMINATOR_NOT_AVAILABLE",
        "cambridge_capability_gap_not_explicit",
    )
    task_patterns = set(cambridge.get("task_compatibility", {}))

    asset_index = payload.get("existing_asset_target_index")
    require(isinstance(asset_index, list) and len(asset_index) == builder.EXPECTED_EXISTING_ASSET_COUNT, "asset_target_index_count_invalid")
    require(len({row.get("asset_key") for row in asset_index}) == len(asset_index), "asset_target_identity_duplicate")
    require(Counter(str(row.get("skill")) for row in asset_index) == Counter(builder.m01.EXPECTED_LANE_COUNTS), "asset_skill_denominator_invalid")
    vocabulary_refs = {str(row["authority_id"]) for row in vocabulary}
    chunk_refs = {str(row["authority_id"]) for row in chunks}
    context_phrase_refs = {str(row["phrase_id"]) for row in context_phrases}
    pattern_refs = {str(row["authority_id"]) for row in patterns}
    sentence_refs = {str(row["sentence_id"]) for row in sentences}
    for row in asset_index:
        require(row.get("binding_status") == "RESOLVED_LANGUAGE_TARGETS_KET_PENDING", "asset_language_binding_unresolved")
        require(set(row.get("target_evp_sense_ids", [])).issubset(vocabulary_refs), "asset_vocabulary_ref_invalid")
        require(set(row.get("target_chunk_ids", [])).issubset(chunk_refs), "asset_chunk_ref_invalid")
        require(set(row.get("target_context_phrase_ids", [])).issubset(context_phrase_refs), "asset_context_phrase_ref_invalid")
        require(set(row.get("target_egp_row_ids", [])) == set(egp_rows), "asset_egp_ref_invalid")
        require(set(row.get("target_pattern_ids", [])) == pattern_refs, "asset_pattern_ref_invalid")
        require(set(row.get("target_sentence_ids", [])).issubset(sentence_refs), "asset_sentence_ref_invalid")
        require(row.get("assessment_pattern_ref") in task_patterns, "asset_assessment_pattern_invalid")
        require(row.get("target_ket_prerequisite_node_ids") == [], "unproven_ket_node_ref")
        require(
            row.get("ket_binding_status") == "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
            "ket_gap_not_explicit",
        )
        require(row.get("cambridge_stage") == "STARTERS", "asset_cambridge_stage_invalid")

    load = payload.get("learning_load", {})
    require(load.get("context_count") == 5, "learning_load_context_invalid")
    require(load.get("new_productive_vocabulary_count") == len(productive), "learning_load_productive_invalid")
    require(load.get("new_receptive_vocabulary_count") == len(receptive), "learning_load_receptive_invalid")
    require(load.get("new_canonical_chunk_count") == len(chunks), "learning_load_canonical_chunk_invalid")
    require(load.get("new_context_phrase_count") == len(context_phrases), "learning_load_context_phrase_invalid")
    require(load.get("new_chunk_or_phrase_count") == total_chunk_or_phrase, "learning_load_chunk_phrase_total_invalid")
    require(load.get("core_sentence_count") == len(core_sentences), "learning_load_sentence_invalid")

    encoded = json.dumps(payload, ensure_ascii=False).casefold()
    for forbidden in ('"accepted_texts"', '"accepted_sequence"', '"response_json"', '"correct_answer"'):
        require(forbidden not in encoded, f"private_answer_or_response_leak:{forbidden}")
    source_policy = payload.get("source_policy", {})
    require(source_policy.get("raw_raz_text_copied") is False, "raw_raz_copy_forbidden")
    require(source_policy.get("raw_ket_text_copied") is False, "raw_ket_copy_forbidden")
    boundaries = payload.get("claim_boundaries", {})
    require(boundaries.get("candidate_only_until_admitted") is True, "candidate_boundary_invalid")
    for key in (
        "learner_database_written",
        "response_contract_changed",
        "existing_asset_identity_changed",
        "context_phrases_counted_as_canonical_chunks",
        "ket_coverage_claimed",
        "cambridge_granular_capability_claimed",
        "unit02_modified",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"boundary_invalid:{key}")
    return receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "candidate_role_invalid")
    require(candidate.get("learner_facing") is False, "candidate_learner_facing_forbidden")
    policy_artifact.verify_artifact_digest(candidate)
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "candidate_payload_missing")
    return validate_payload(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        candidate_receipt = validate_candidate(candidate)
        require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "approved_role_invalid")
        require(approved.get("learner_facing") is False, "approved_learner_facing_forbidden")
        require(approved.get("admission", {}).get("status") == "APPROVED", "approved_status_invalid")
        require(approved.get("admission", {}).get("decision_ref") == builder.DECISION_REF, "approved_decision_invalid")
        require(
            approved.get("source_bindings", {}).get("candidate_artifact_sha256") == candidate.get("artifact_sha256"),
            "approved_candidate_binding_invalid",
        )
        require(approved.get("payload") == candidate.get("payload"), "approved_payload_drift")
        require(
            candidate_receipt.get("receipt_sha256")
            in {row.get("receipt_sha256") for row in approved.get("validation_receipts", [])},
            "approved_validation_receipt_missing",
        )
        policy_artifact.verify_artifact_digest(approved)
    except (S01ValidationError, policy_artifact.ContentPolicyBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }
