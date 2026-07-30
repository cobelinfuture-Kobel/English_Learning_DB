#!/usr/bin/env python3
"""Validate RAZQ01D Unit01 content admission and Unit02 reusable handoff."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as builder,
)

VALIDATOR_ID = "A1FS-V1-RAZQ01D-INDEPENDENT-VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_UNIT01_CONTENT_ADMISSION_HANDOFF_VALIDATION"


class AdmissionValidationError(ValueError):
    pass


def fail(code: str) -> None:
    raise AdmissionValidationError(code)


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("task_id") != builder.TASK_ID or payload.get("status") != builder.PASS_STATUS:
        fail("identity_invalid")
    scope = payload.get("scope") or {}
    if (
        scope.get("allowed_units") != [builder.UNIT_ID]
        or scope.get("unit02_to_unit24_modified") is not False
        or scope.get("second_question_bank_created") is not False
        or scope.get("a2_status") != "LOCKED"
        or scope.get("raw_raz_text_learner_facing_copy_allowed") is not False
    ):
        fail("scope_invalid")

    assets = payload.get("content_assets") or []
    if not isinstance(assets, list) or not assets:
        fail("assets_missing")
    if {asset.get("content_kind") for asset in assets} != set(builder.CONTENT_KINDS):
        fail("content_kinds_incomplete")
    asset_ids = [asset.get("content_asset_id") for asset in assets]
    signatures = [
        (asset.get("scene_profile") or {}).get("distinct_scene_signature")
        for asset in assets
    ]
    if (
        None in asset_ids
        or len(asset_ids) != len(set(asset_ids))
        or None in signatures
        or len(signatures) != len(set(signatures))
    ):
        fail("identity_or_scene_duplicate")

    for asset in assets:
        content = asset.get("content") or {}
        if asset.get("content_sha256") != builder.digest(content):
            fail("content_hash_invalid")
        lineage = asset.get("source_lineage") or {}
        if (
            lineage.get("source_authority") != "RAZ_READING_AUTHORITY"
            or lineage.get("original_excerpt_private") is not True
            or not lineage.get("original_excerpt_sha256")
            or lineage.get("derived_from_task_id") != builder.upstream.TASK_ID
        ):
            fail("source_lineage_invalid")
        admission = asset.get("admission") or {}
        if (
            admission.get("review_status") != "APPROVED"
            or admission.get("decision_ref") != builder.DECISION_REF
            or admission.get("template_only") is not False
            or admission.get("canonical_admission") is not True
        ):
            fail("admission_invalid")
        review_dimensions = admission.get("review_dimensions") or {}
        if (
            set(review_dimensions) != set(builder.REVIEW_DIMENSIONS)
            or any(review_dimensions[key] != "PASS" for key in builder.REVIEW_DIMENSIONS)
        ):
            fail("review_dimensions_invalid")

        reuse = asset.get("later_unit_reuse") or {}
        handoff = asset.get("unit02_reusable_handoff") or {}
        if (
            reuse.get("copy_on_reuse") is not False
            or reuse.get("reuse_identity_mode") != "REFERENCE_EXISTING_CONTENT_ASSET_ID"
            or reuse.get("reusable_in_later_units") is not True
        ):
            fail("reuse_contract_invalid")
        if (
            handoff.get("target_unit_sequence") != builder.TARGET_UNIT02_SEQUENCE
            or handoff.get("binding_status") != "AVAILABLE_NOT_BOUND"
            or handoff.get("unit02_modified") is not False
            or handoff.get("source_content_asset_id") != asset.get("content_asset_id")
        ):
            fail("unit02_handoff_invalid")

        projections = asset.get("skill_projections") or []
        if {projection.get("skill") for projection in projections} != set(builder.SKILLS):
            fail("three_skill_projection_invalid")
        for projection in projections:
            if (
                projection.get("existing_question_bank_id") != builder.qb.BANK_ID
                or projection.get("existing_question_bank_version") != builder.qb.BANK_VERSION
                or projection.get("projection_mode")
                != "REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK"
            ):
                fail("question_bank_projection_invalid")
            family_ids = set(projection.get("existing_family_ids") or [])
            if not family_ids or not family_ids.issubset(builder.FAMILY_IDS):
                fail("question_bank_family_invalid")

        dialogue = asset.get("dialogue_profile") or {}
        if asset.get("content_kind") == "SHORT_DIALOGUE":
            if (
                dialogue.get("is_real_dialogue") is not True
                or int(dialogue.get("speaker_count") or 0) < 2
                or int(dialogue.get("turn_count") or 0) < 2
                or dialogue.get("role_play_supported") is not True
            ):
                fail("dialogue_invalid")
        elif dialogue.get("is_real_dialogue") is not False:
            fail("nondialogue_invalid")

    coverage = payload.get("coverage_readback") or {}
    count = len(assets)
    for key in (
        "approved_content_asset_count",
        "reading_projection_count",
        "writing_projection_count",
        "speaking_projection_count",
        "three_skill_shared_content_count",
        "unit02_reusable_asset_count",
    ):
        if coverage.get(key) != count:
            fail(f"coverage_invalid:{key}")
    if coverage.get("template_only_content_count") != 0:
        fail("template_only_count_invalid")

    findings = {
        row.get("finding_code")
        for row in (payload.get("inspection_record") or {}).get("findings", [])
    }
    if findings != {code for code, _ in builder.FINDINGS}:
        fail("inspection_findings_incomplete")

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
        "content_kind_counts": {
            kind: sum(asset["content_kind"] == kind for asset in assets)
            for kind in builder.CONTENT_KINDS
        },
        "three_skill_shared_content_count": count,
        "unit02_reusable_asset_count": count,
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    if (
        candidate.get("artifact_role") != policy_artifact.CANDIDATE_ROLE
        or candidate.get("producer_id") != builder.TASK_ID
        or candidate.get("level_scope") != ["A1"]
        or candidate.get("learner_facing") is not False
        or (candidate.get("admission") or {}).get("status") != "PENDING_VALIDATION"
    ):
        fail("candidate_artifact_invalid")
    summary = validate_payload(candidate.get("payload") or {})
    receipt_core = {
        "validator_id": VALIDATOR_ID,
        "status": policy_artifact.PASS_STATUS,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "content_asset_count": summary["content_asset_count"],
    }
    return {
        "validator_id": VALIDATOR_ID,
        "status": policy_artifact.PASS_STATUS,
        "receipt_sha256": builder.digest(receipt_core),
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
        or (approved.get("admission") or {}).get("decision_ref") != builder.DECISION_REF
    ):
        fail("approved_artifact_invalid")
    receipts = approved.get("validation_receipts") or []
    if len(receipts) != 1 or receipts[0].get("validator_id") != VALIDATOR_ID:
        fail("approved_receipt_invalid")

    summary = validate_payload(approved.get("payload") or {})
    safe_core = {key: deepcopy(value) for key, value in safe.items() if key != "readback_sha256"}
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
            or safe_asset.get("content_asset_id") != approved_asset.get("content_asset_id")
            or safe_asset.get("content_sha256") != approved_asset.get("content_sha256")
        ):
            fail("safe_content_leak_or_identity_drift")

    return {
        "validation_status": PASS_STATUS,
        **summary,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "safe_readback_sha256": safe["readback_sha256"],
    }
