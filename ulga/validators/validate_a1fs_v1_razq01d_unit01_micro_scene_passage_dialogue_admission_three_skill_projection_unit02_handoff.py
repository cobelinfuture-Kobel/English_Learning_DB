#!/usr/bin/env python3
"""Validate RAZQ01D FULLFIX automatic admission and exception-only human review."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as builder,
)

VALIDATOR_ID = "A1FS-V1-RAZQ01D-FULLFIX-INDEPENDENT-VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_FULLFIX_AUTO_ADMISSION_VALIDATION"


class AdmissionValidationError(ValueError):
    pass


def fail(code: str) -> None:
    raise AdmissionValidationError(code)


def _validate_ledger_and_queue(
    payload: Mapping[str, Any],
) -> dict[str, int]:
    ledger = payload.get("resolution_ledger") or []
    queue = payload.get("human_review_queue") or []
    if not isinstance(ledger, list) or not ledger:
        fail("resolution_ledger_missing")
    if not isinstance(queue, list):
        fail("human_review_queue_invalid")
    source_ids = [row.get("source_record_id") for row in ledger]
    semantic_ids = [row.get("semantic_identity") for row in ledger]
    if (
        None in source_ids
        or len(source_ids) != len(set(source_ids))
        or None in semantic_ids
        or len(semantic_ids) != len(set(semantic_ids))
    ):
        fail("ledger_identity_invalid")
    queue_ids = [row.get("source_record_id") for row in queue]
    if None in queue_ids or len(queue_ids) != len(set(queue_ids)):
        fail("human_queue_identity_invalid")
    ledger_by_source = {
        row["source_record_id"]: row for row in ledger
    }
    for row in ledger:
        resolution = row.get("resolution_class")
        if resolution not in builder.RESOLUTION_CLASSES:
            fail("resolution_class_invalid")
        asset_ids = row.get("content_asset_ids")
        if not isinstance(asset_ids, list):
            fail("ledger_asset_ids_invalid")
        if resolution in {
            "AUTO_REJECT",
            "HUMAN_REVIEW_REQUIRED",
            "HUMAN_REJECT_EXCEPTION",
        } and asset_ids:
            fail("nonapproved_resolution_has_assets")
        if resolution in {
            "AUTO_APPROVE_DIRECT",
            "AUTO_APPROVE_RULE_REWRITE",
            "HUMAN_APPROVE_EXCEPTION",
        } and not asset_ids:
            fail("approved_resolution_missing_assets")
        if (
            row.get("human_override_applied") is True
            and resolution
            not in {
                "HUMAN_APPROVE_EXCEPTION",
                "HUMAN_REJECT_EXCEPTION",
            }
        ):
            fail("human_override_resolution_invalid")
    for row in queue:
        source_id = row.get("source_record_id")
        ledger_row = ledger_by_source.get(source_id)
        if (
            ledger_row is None
            or ledger_row.get("resolution_class")
            != "HUMAN_REVIEW_REQUIRED"
            or ledger_row.get("human_override_applied") is not False
        ):
            fail("human_queue_not_bound_to_pending_exception")
        if (
            "text_excerpt" in row
            or "raw_text" in row
            or not row.get("source_excerpt_sha256")
            or not row.get("reason_codes")
        ):
            fail("human_queue_private_text_leak_or_reason_missing")
    counts = Counter(row["resolution_class"] for row in ledger)
    return {
        "ledger_count": len(ledger),
        "queue_count": len(queue),
        **{
            name: counts[name]
            for name in builder.RESOLUTION_CLASSES
        },
    }


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
        or scope.get("raw_raz_text_learner_facing_copy_allowed")
        is not False
        or scope.get("human_review_scope") != "EXCEPTION_ONLY"
        or scope.get("complete_manual_decision_manifest_required")
        is not False
    ):
        fail("scope_invalid")

    policy = payload.get("automatic_resolution_policy") or {}
    required_policy = {
        "semantic_identity_required": True,
        "semantic_fact_extraction_required": True,
        "rule_rewrite_must_preserve_source_facts": True,
        "new_source_facts_allowed": False,
        "all_six_validation_dimensions_required": True,
        "human_review_only_for_nonunique_or_unresolved_semantics": True,
        "unresolved_human_queue_blocks_auto_approved_assets": False,
    }
    if any(policy.get(key) is not value for key, value in required_policy.items()):
        fail("automatic_resolution_policy_invalid")
    if set(policy.get("resolution_classes") or []) != set(
        builder.RESOLUTION_CLASSES
    ):
        fail("resolution_classes_invalid")

    ledger_summary = _validate_ledger_and_queue(payload)
    assets = payload.get("content_assets") or []
    if not isinstance(assets, list) or not assets:
        fail("assets_missing")
    if not {
        asset.get("content_kind") for asset in assets
    }.issubset(set(builder.CONTENT_KINDS)):
        fail("content_kind_invalid")
    asset_ids = [asset.get("content_asset_id") for asset in assets]
    content_hashes = [asset.get("content_sha256") for asset in assets]
    if (
        None in asset_ids
        or len(asset_ids) != len(set(asset_ids))
        or None in content_hashes
        or len(content_hashes) != len(set(content_hashes))
    ):
        fail("asset_identity_or_content_duplicate")

    asset_ids_from_ledger = {
        asset_id
        for row in payload["resolution_ledger"]
        for asset_id in row["content_asset_ids"]
    }
    if set(asset_ids) != asset_ids_from_ledger:
        fail("ledger_asset_binding_invalid")

    for asset in assets:
        content = asset.get("content") or {}
        if asset.get("content_sha256") != builder.digest(content):
            fail("content_hash_invalid")
        lineage = asset.get("source_lineage") or {}
        if (
            lineage.get("source_authority") != "RAZ_READING_AUTHORITY"
            or lineage.get("original_excerpt_private") is not True
            or not lineage.get("original_excerpt_sha256")
            or lineage.get("derived_from_task_id")
            != builder.upstream.TASK_ID
            or lineage.get("adaptation_mode")
            not in {
                "RULE_BASED_SEMANTIC_REWRITE",
                "HUMAN_EXCEPTION_REWRITE",
            }
        ):
            fail("source_lineage_invalid")
        scene = asset.get("scene_profile") or {}
        if (
            not scene.get("semantic_scene_id")
            or not scene.get("distinct_scene_signature")
        ):
            fail("semantic_scene_identity_invalid")
        admission = asset.get("admission") or {}
        resolution = admission.get("resolution_class")
        if resolution not in {
            "AUTO_APPROVE_DIRECT",
            "AUTO_APPROVE_RULE_REWRITE",
            "HUMAN_APPROVE_EXCEPTION",
        }:
            fail("asset_resolution_invalid")
        if resolution in builder.AUTOMATIC_APPROVAL_CLASSES:
            if (
                admission.get("decision_ref")
                != builder.AUTO_DECISION_REF
                or admission.get("human_review_used") is not False
            ):
                fail("automatic_admission_binding_invalid")
        elif (
            not str(admission.get("decision_ref") or "").startswith(
                builder.HUMAN_DECISION_REF_PREFIX
            )
            or admission.get("human_review_used") is not True
        ):
            fail("human_exception_admission_binding_invalid")
        if (
            admission.get("template_only") is not False
            or admission.get("canonical_admission") is not True
        ):
            fail("admission_invalid")
        review_dimensions = admission.get("review_dimensions") or {}
        if (
            set(review_dimensions) != set(builder.REVIEW_DIMENSIONS)
            or any(
                review_dimensions[key] != "PASS"
                for key in builder.REVIEW_DIMENSIONS
            )
        ):
            fail("review_dimensions_invalid")

        reuse = asset.get("later_unit_reuse") or {}
        handoff = asset.get("unit02_reusable_handoff") or {}
        if (
            reuse.get("copy_on_reuse") is not False
            or reuse.get("reuse_identity_mode")
            != "REFERENCE_EXISTING_CONTENT_ASSET_ID"
            or reuse.get("reusable_in_later_units") is not True
        ):
            fail("reuse_contract_invalid")
        if (
            handoff.get("target_unit_sequence")
            != builder.TARGET_UNIT02_SEQUENCE
            or handoff.get("binding_status") != "AVAILABLE_NOT_BOUND"
            or handoff.get("unit02_modified") is not False
            or handoff.get("source_content_asset_id")
            != asset.get("content_asset_id")
        ):
            fail("unit02_handoff_invalid")

        projections = asset.get("skill_projections") or []
        if {
            projection.get("skill") for projection in projections
        } != set(builder.SKILLS):
            fail("three_skill_projection_invalid")
        for projection in projections:
            if (
                projection.get("existing_question_bank_id")
                != builder.qb.BANK_ID
                or projection.get("existing_question_bank_version")
                != builder.qb.BANK_VERSION
                or projection.get("projection_mode")
                != "REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK"
            ):
                fail("question_bank_projection_invalid")
            family_ids = set(
                projection.get("existing_family_ids") or []
            )
            if (
                not family_ids
                or not family_ids.issubset(builder.FAMILY_IDS)
            ):
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
    expected_counts = {
        "upstream_candidate_count": ledger_summary["ledger_count"],
        "auto_approve_direct_count": ledger_summary[
            "AUTO_APPROVE_DIRECT"
        ],
        "auto_approve_rule_rewrite_count": ledger_summary[
            "AUTO_APPROVE_RULE_REWRITE"
        ],
        "auto_reject_count": ledger_summary["AUTO_REJECT"],
        "human_review_required_count": sum(
            row.get("human_review_required") is True
            for row in payload["resolution_ledger"]
        ),
        "human_review_resolved_count": sum(
            row.get("human_override_applied") is True
            for row in payload["resolution_ledger"]
        ),
        "human_review_pending_count": ledger_summary["queue_count"],
        "human_approve_exception_count": ledger_summary[
            "HUMAN_APPROVE_EXCEPTION"
        ],
        "human_reject_exception_count": ledger_summary[
            "HUMAN_REJECT_EXCEPTION"
        ],
        "approved_content_asset_count": count,
        "reading_projection_count": count,
        "writing_projection_count": count,
        "speaking_projection_count": count,
        "three_skill_shared_content_count": count,
        "unit02_reusable_asset_count": count,
    }
    for key, expected in expected_counts.items():
        if coverage.get(key) != expected:
            fail(f"coverage_invalid:{key}")
    if coverage.get("template_only_content_count") != 0:
        fail("template_only_count_invalid")
    if coverage.get("human_review_required_count") != (
        coverage.get("human_review_resolved_count")
        + coverage.get("human_review_pending_count")
    ):
        fail("human_review_queue_reconciliation_invalid")
    semantic_scene_count = len(
        {
            asset["scene_profile"]["semantic_scene_id"]
            for asset in assets
        }
    )
    if coverage.get("distinct_semantic_scene_count") != semantic_scene_count:
        fail("semantic_scene_count_invalid")
    kind_counts = Counter(asset["content_kind"] for asset in assets)
    if (
        coverage.get("distinct_micro_scene_count")
        != kind_counts["MICRO_SCENE"]
        or coverage.get("distinct_short_passage_count")
        != kind_counts["SHORT_PASSAGE"]
        or coverage.get("distinct_dialogue_count")
        != kind_counts["SHORT_DIALOGUE"]
    ):
        fail("content_kind_coverage_invalid")

    findings = {
        row.get("finding_code")
        for row in (
            payload.get("inspection_record") or {}
        ).get("findings", [])
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
            kind: kind_counts[kind]
            for kind in builder.CONTENT_KINDS
        },
        "resolution_counts": {
            name: ledger_summary[name]
            for name in builder.RESOLUTION_CLASSES
        },
        "human_review_pending_count": ledger_summary["queue_count"],
        "three_skill_shared_content_count": count,
        "unit02_reusable_asset_count": count,
    }


def validate_candidate(
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    if (
        candidate.get("artifact_role")
        != policy_artifact.CANDIDATE_ROLE
        or candidate.get("producer_id") != builder.TASK_ID
        or candidate.get("level_scope") != ["A1"]
        or candidate.get("learner_facing") is not False
        or (candidate.get("admission") or {}).get("status")
        != "PENDING_VALIDATION"
    ):
        fail("candidate_artifact_invalid")
    summary = validate_payload(candidate.get("payload") or {})
    receipt_core = {
        "validator_id": VALIDATOR_ID,
        "status": policy_artifact.PASS_STATUS,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "content_asset_count": summary["content_asset_count"],
        "human_review_pending_count": summary[
            "human_review_pending_count"
        ],
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
        approved.get("artifact_role")
        != policy_artifact.APPROVED_ROLE
        or approved.get("producer_id") != builder.TASK_ID
        or approved.get("level_scope") != ["A1"]
        or approved.get("learner_facing") is not False
        or (approved.get("admission") or {}).get("status")
        != "APPROVED"
        or (approved.get("admission") or {}).get("decision_ref")
        != builder.AUTO_DECISION_REF
    ):
        fail("approved_artifact_invalid")
    receipts = approved.get("validation_receipts") or []
    if (
        len(receipts) != 1
        or receipts[0].get("validator_id") != VALIDATOR_ID
    ):
        fail("approved_receipt_invalid")

    summary = validate_payload(approved.get("payload") or {})
    safe_core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key != "readback_sha256"
    }
    if safe.get("readback_sha256") != builder.digest(safe_core):
        fail("safe_hash_invalid")
    if (
        safe.get("approved_artifact_sha256")
        != approved.get("artifact_sha256")
    ):
        fail("safe_approved_binding_invalid")
    if (
        safe.get("content_governance")
        != approved.get("content_governance")
    ):
        fail("safe_governance_binding_invalid")

    approved_assets = (
        approved.get("payload", {}).get("content_assets") or []
    )
    safe_assets = safe.get("content_assets") or []
    if len(approved_assets) != len(safe_assets):
        fail("safe_assets_missing")
    for approved_asset, safe_asset in zip(
        approved_assets, safe_assets
    ):
        if (
            "content" in safe_asset
            or safe_asset.get("content_asset_id")
            != approved_asset.get("content_asset_id")
            or safe_asset.get("content_sha256")
            != approved_asset.get("content_sha256")
        ):
            fail("safe_content_leak_or_identity_drift")
    for queue_row in safe.get("human_review_queue") or []:
        if "text_excerpt" in queue_row or "raw_text" in queue_row:
            fail("safe_human_queue_text_leak")

    return {
        "validation_status": PASS_STATUS,
        **summary,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "safe_readback_sha256": safe["readback_sha256"],
    }
