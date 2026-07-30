#!/usr/bin/env python3
"""Validate RAZQ01D FULLFIX2 composite identity, semantic modes, and Unit01 coverage."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as builder,
)

VALIDATOR_ID = "A1FS-V1-RAZQ01D-FULLFIX2-INDEPENDENT-VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_FULLFIX2_VALIDATION"


class AdmissionValidationError(ValueError):
    pass


def fail(code: str) -> None:
    raise AdmissionValidationError(code)


def _key(row: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("source_record_id") or ""),
        str(row.get("semantic_identity") or ""),
    )


def _validate_ledger_and_queue(
    payload: Mapping[str, Any],
) -> tuple[dict[str, int], set[str]]:
    ledger = payload.get("resolution_ledger") or []
    queue = payload.get("human_review_queue") or []
    if not isinstance(ledger, list) or not ledger:
        fail("resolution_ledger_missing")
    if not isinstance(queue, list):
        fail("human_review_queue_invalid")

    keys = [_key(row) for row in ledger]
    semantic_ids = [key[1] for key in keys]
    if (
        any(not all(key) for key in keys)
        or len(keys) != len(set(keys))
        or len(semantic_ids) != len(set(semantic_ids))
    ):
        fail("ledger_composite_identity_invalid")
    if any(
        row.get("candidate_composite_key")
        != f"{row.get('source_record_id')}::{row.get('semantic_identity')}"
        for row in ledger
    ):
        fail("ledger_composite_key_text_invalid")

    queue_keys = [_key(row) for row in queue]
    if any(not all(key) for key in queue_keys) or len(queue_keys) != len(
        set(queue_keys)
    ):
        fail("human_queue_composite_identity_invalid")

    ledger_by_key = {_key(row): row for row in ledger}
    for row in ledger:
        resolution = row.get("resolution_class")
        if resolution not in builder.RESOLUTION_CLASSES:
            fail("resolution_class_invalid")
        asset_ids = row.get("content_asset_ids")
        if not isinstance(asset_ids, list):
            fail("ledger_asset_ids_invalid")
        approved = resolution in {
            *builder.AUTOMATIC_APPROVAL_CLASSES,
            "HUMAN_APPROVE_EXCEPTION",
        }
        if approved != bool(asset_ids):
            fail("ledger_approval_asset_binding_invalid")
        if row.get("human_override_applied") is True and resolution not in {
            "HUMAN_APPROVE_EXCEPTION",
            "HUMAN_REJECT_EXCEPTION",
        }:
            fail("human_override_resolution_invalid")

    for row in queue:
        ledger_row = ledger_by_key.get(_key(row))
        if (
            ledger_row is None
            or ledger_row.get("resolution_class")
            != "HUMAN_REVIEW_REQUIRED"
            or ledger_row.get("human_override_applied") is not False
        ):
            fail("human_queue_not_bound_to_composite_exception")
        if (
            "text_excerpt" in row
            or "raw_text" in row
            or not row.get("source_excerpt_sha256")
            or not row.get("reason_codes")
        ):
            fail("human_queue_private_text_leak_or_reason_missing")

    counts = Counter(row["resolution_class"] for row in ledger)
    return (
        {
            name: counts[name] for name in builder.RESOLUTION_CLASSES
        },
        {
            asset_id
            for row in ledger
            for asset_id in row.get("content_asset_ids") or []
        },
    )


def _validate_asset(asset: Mapping[str, Any]) -> None:
    content = asset.get("content") or {}
    if asset.get("content_sha256") != builder.digest(content):
        fail("content_hash_invalid")
    if not builder.norm(content):
        fail("content_empty")

    kind = asset.get("content_kind")
    sentences = content.get("sentences") or []
    turns = content.get("dialogue_turns") or []
    if kind == "MICRO_SCENE" and not (1 <= len(sentences) <= 3 and not turns):
        fail("micro_scene_structure_invalid")
    if kind == "SHORT_PASSAGE" and not (2 <= len(sentences) <= 6 and not turns):
        fail("short_passage_structure_invalid")
    if kind == "SHORT_DIALOGUE":
        speakers = {row.get("speaker_id") for row in turns}
        if (
            sentences
            or not 2 <= len(turns) <= 6
            or None in speakers
            or len(speakers) < 2
        ):
            fail("short_dialogue_structure_invalid")

    lineage = asset.get("source_lineage") or {}
    source_authority = lineage.get("source_authority")
    lineage_mode = lineage.get("lineage_mode")
    resolution = (asset.get("admission") or {}).get("resolution_class")
    expected_mode = {
        "AUTO_APPROVE_SEMANTIC_EQUIVALENT": "SEMANTIC_EQUIVALENT_REWRITE",
        "AUTO_APPROVE_A1_IMITATION": "SEMANTIC_ANCHOR_A1_IMITATION",
        "AUTO_APPROVE_PROJECT_AUTHORED_COMPLETION": (
            "PROJECT_AUTHORED_CONTRACT_COMPLETION"
        ),
        "HUMAN_APPROVE_EXCEPTION": "HUMAN_EXCEPTION_REWRITE",
    }.get(resolution)
    if expected_mode is None or lineage_mode != expected_mode:
        fail("resolution_lineage_mode_invalid")
    if lineage.get("candidate_composite_key") != (
        f"{lineage.get('source_record_id')}::{lineage.get('semantic_identity')}"
    ):
        fail("asset_composite_identity_invalid")
    if not lineage.get("original_excerpt_sha256"):
        fail("source_hash_missing")

    if lineage_mode == "PROJECT_AUTHORED_CONTRACT_COMPLETION":
        if (
            source_authority != "PROJECT_AUTHORED_UNIT01_CONTRACT"
            or lineage.get("original_excerpt_private") is not False
            or lineage.get("project_authored_claimed") is not True
            or not lineage.get("gap_spec_id")
        ):
            fail("project_authored_lineage_invalid")
    else:
        if (
            source_authority != "RAZ_READING_AUTHORITY"
            or lineage.get("original_excerpt_private") is not True
            or lineage.get("derived_from_task_id") != builder.upstream.TASK_ID
        ):
            fail("raz_source_lineage_invalid")

    admission = asset.get("admission") or {}
    if (
        admission.get("canonical_admission") is not True
        or admission.get("template_only") is not False
        or admission.get("lineage_mode") != lineage_mode
    ):
        fail("admission_invalid")
    checks = admission.get("review_dimensions") or {}
    if (
        set(checks) != set(builder.REVIEW_DIMENSIONS)
        or any(checks[key] != "PASS" for key in builder.REVIEW_DIMENSIONS)
    ):
        fail("deterministic_validation_dimensions_invalid")

    scene = asset.get("scene_profile") or {}
    if (
        not scene.get("semantic_scene_id")
        or not scene.get("distinct_scene_signature")
        or not isinstance(scene.get("objects"), list)
    ):
        fail("scene_identity_invalid")

    projections = asset.get("skill_projections") or []
    if {row.get("skill") for row in projections} != set(builder.SKILLS):
        fail("three_skill_projection_invalid")
    for row in projections:
        if (
            row.get("existing_question_bank_id") != builder.qb.BANK_ID
            or row.get("existing_question_bank_version")
            != builder.qb.BANK_VERSION
            or row.get("projection_mode")
            != "REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK"
            or not set(row.get("existing_family_ids") or []).issubset(
                builder.FAMILY_IDS
            )
        ):
            fail("question_bank_projection_invalid")

    handoff = asset.get("unit02_reusable_handoff") or {}
    reuse = asset.get("later_unit_reuse") or {}
    if (
        handoff.get("target_unit_sequence") != 2
        or handoff.get("binding_status") != "AVAILABLE_NOT_BOUND"
        or handoff.get("unit02_modified") is not False
        or handoff.get("source_content_asset_id")
        != asset.get("content_asset_id")
        or reuse.get("copy_on_reuse") is not False
    ):
        fail("unit02_reference_only_handoff_invalid")


def _coverage_sets(assets: list[Mapping[str, Any]]) -> dict[str, set[str]]:
    values = {
        "active_nouns": set(),
        "active_adjectives": set(),
        "article_forms": set(),
        "sentence_frames": set(),
    }
    for asset in assets:
        alignment = asset.get("target_alignment") or {}
        values["active_nouns"].update(alignment.get("active_nouns") or [])
        values["active_adjectives"].update(
            alignment.get("active_adjectives") or []
        )
        values["article_forms"].update(alignment.get("article_forms") or [])
        values["sentence_frames"].update(
            alignment.get("sentence_frame_ids") or []
        )
    return values


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if (
        payload.get("task_id") != builder.TASK_ID
        or payload.get("parent_task_id") != builder.PARENT_TASK_ID
        or payload.get("status") != builder.PASS_STATUS
    ):
        fail("identity_invalid")
    scope = payload.get("scope") or {}
    if (
        scope.get("allowed_units") != [builder.UNIT_ID]
        or scope.get("unit02_to_unit24_modified") is not False
        or scope.get("second_question_bank_created") is not False
        or scope.get("a2_status") != "LOCKED"
        or scope.get("raw_raz_text_learner_facing_copy_allowed") is not False
        or scope.get("human_review_scope") != "TRUE_UNCERTAINTY_ONLY"
        or scope.get("additional_raz_search_allowed") is not False
    ):
        fail("scope_invalid")

    policy = payload.get("automatic_resolution_policy") or {}
    if (
        policy.get("candidate_identity_fields")
        != ["source_record_id", "semantic_identity"]
        or policy.get("source_record_id_may_repeat") is not True
        or policy.get("semantic_identity_must_be_unique") is not True
        or policy.get("semantic_equivalent_rewrite_enabled") is not True
        or policy.get("semantic_anchor_a1_imitation_enabled") is not True
        or policy.get("project_authored_contract_completion_enabled") is not True
        or policy.get("model_output_requires_deterministic_validation") is not True
        or policy.get("human_review_only_for_true_uncertainty") is not True
    ):
        fail("automatic_resolution_policy_invalid")

    resolution_counts, ledger_asset_ids = _validate_ledger_and_queue(payload)
    assets = payload.get("content_assets") or []
    if not isinstance(assets, list) or not assets:
        fail("assets_missing")
    asset_ids = [asset.get("content_asset_id") for asset in assets]
    if None in asset_ids or len(asset_ids) != len(set(asset_ids)):
        fail("asset_identity_invalid")
    if set(asset_ids) != ledger_asset_ids:
        fail("ledger_asset_binding_invalid")
    for asset in assets:
        _validate_asset(asset)

    gap_ids = payload.get("project_authored_gap_spec_ids") or []
    project_assets = [
        asset
        for asset in assets
        if asset["source_lineage"]["lineage_mode"]
        == "PROJECT_AUTHORED_CONTRACT_COMPLETION"
    ]
    if (
        len(gap_ids) != len(set(gap_ids))
        or set(gap_ids)
        != {
            asset["source_lineage"]["gap_spec_id"]
            for asset in project_assets
        }
    ):
        fail("project_gap_spec_binding_invalid")

    coverage = payload.get("coverage_readback") or {}
    count = len(assets)
    expected = {
        "resolution_ledger_count": len(payload["resolution_ledger"]),
        "auto_approve_semantic_equivalent_count": resolution_counts[
            "AUTO_APPROVE_SEMANTIC_EQUIVALENT"
        ],
        "auto_approve_a1_imitation_count": resolution_counts[
            "AUTO_APPROVE_A1_IMITATION"
        ],
        "auto_approve_project_authored_completion_count": resolution_counts[
            "AUTO_APPROVE_PROJECT_AUTHORED_COMPLETION"
        ],
        "auto_reject_count": resolution_counts["AUTO_REJECT"],
        "human_review_pending_count": len(payload["human_review_queue"]),
        "approved_content_asset_count": count,
        "reading_projection_count": count,
        "writing_projection_count": count,
        "speaking_projection_count": count,
        "three_skill_shared_content_count": count,
        "unit02_reusable_asset_count": count,
    }
    for key, value in expected.items():
        if coverage.get(key) != value:
            fail(f"coverage_count_invalid:{key}")

    kind_counts = Counter(asset["content_kind"] for asset in assets)
    if (
        coverage.get("distinct_micro_scene_count")
        != kind_counts["MICRO_SCENE"]
        or coverage.get("distinct_short_passage_count")
        != kind_counts["SHORT_PASSAGE"]
        or coverage.get("distinct_dialogue_count")
        != kind_counts["SHORT_DIALOGUE"]
    ):
        fail("content_kind_count_invalid")

    matrix = coverage.get("unit01_coverage") or {}
    actual = _coverage_sets(assets)
    for key, actual_values in actual.items():
        row = matrix.get(key) or {}
        if set(row.get("covered") or []) != actual_values:
            fail(f"coverage_matrix_drift:{key}")
        if row.get("missing"):
            fail(f"coverage_matrix_missing:{key}")
    if matrix.get("complete") is not True:
        fail("unit01_coverage_not_complete")

    if coverage.get("real44_acceptance_applied"):
        if (
            coverage.get("source_candidate_count") != 44
            or coverage.get("auto_transformed_source_count", 0) < 35
            or coverage.get("human_review_pending_count", 99) > 6
            or coverage.get("auto_reject_count") != 3
            or coverage.get("real44_acceptance_pass") is not True
        ):
            fail("real44_acceptance_invalid")

    boundaries = payload.get("boundaries") or {}
    if (
        boundaries.get("existing_question_bank_referenced") is not True
        or boundaries.get("existing_question_bank_modified") is not False
        or boundaries.get("parallel_question_bank_created") is not False
        or boundaries.get("unit02_modified") is not False
        or boundaries.get("audio_enabled") is not False
        or boundaries.get("speaking_capture_enabled") is not False
        or boundaries.get("mastery_claimed") is not False
    ):
        fail("authority_boundary_invalid")

    return {
        "content_asset_count": count,
        "resolution_counts": resolution_counts,
        "human_review_pending_count": len(payload["human_review_queue"]),
        "unit01_coverage_complete": True,
        "real44_acceptance_pass": coverage.get("real44_acceptance_pass"),
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    if (
        candidate.get("artifact_role") != policy_artifact.CANDIDATE_ROLE
        or candidate.get("producer_id") != builder.TASK_ID
        or candidate.get("level_scope") != ["A1"]
        or candidate.get("learner_facing") is not False
        or (candidate.get("admission") or {}).get("status")
        != "PENDING_VALIDATION"
    ):
        fail("candidate_artifact_invalid")
    summary = validate_payload(candidate.get("payload") or {})
    core = {
        "validator_id": VALIDATOR_ID,
        "status": policy_artifact.PASS_STATUS,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "content_asset_count": summary["content_asset_count"],
    }
    return {
        "validator_id": VALIDATOR_ID,
        "status": policy_artifact.PASS_STATUS,
        "receipt_sha256": builder.digest(core),
    }


def validate_package(
    approved: Mapping[str, Any], safe: Mapping[str, Any]
) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(approved)
    if (
        approved.get("artifact_role") != policy_artifact.APPROVED_ROLE
        or approved.get("producer_id") != builder.TASK_ID
        or approved.get("level_scope") != ["A1"]
        or approved.get("learner_facing") is not False
        or (approved.get("admission") or {}).get("status") != "APPROVED"
        or (approved.get("admission") or {}).get("decision_ref")
        != builder.AUTO_DECISION_REF
    ):
        fail("approved_artifact_invalid")
    receipts = approved.get("validation_receipts") or []
    if len(receipts) != 1 or receipts[0].get("validator_id") != VALIDATOR_ID:
        fail("approved_receipt_invalid")

    summary = validate_payload(approved.get("payload") or {})
    safe_core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key != "readback_sha256"
    }
    if safe.get("readback_sha256") != builder.digest(safe_core):
        fail("safe_hash_invalid")
    if safe.get("approved_artifact_sha256") != approved.get("artifact_sha256"):
        fail("safe_approved_binding_invalid")
    if safe.get("content_governance") != approved.get("content_governance"):
        fail("safe_governance_binding_invalid")

    approved_assets = approved.get("payload", {}).get("content_assets") or []
    safe_assets = safe.get("content_assets") or []
    if len(approved_assets) != len(safe_assets):
        fail("safe_assets_missing")
    for approved_asset, safe_asset in zip(approved_assets, safe_assets):
        if (
            "content" in safe_asset
            or safe_asset.get("content_asset_id")
            != approved_asset.get("content_asset_id")
            or safe_asset.get("content_sha256")
            != approved_asset.get("content_sha256")
        ):
            fail("safe_content_leak_or_identity_drift")

    return {
        "validation_status": PASS_STATUS,
        **summary,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "safe_readback_sha256": safe["readback_sha256"],
    }
