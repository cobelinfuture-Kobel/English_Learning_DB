#!/usr/bin/env python3
"""Validate U02SC04 scene-candidate materialization and Q7 coverage recheck."""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = builder.VALIDATOR_ID


class Unit02SceneMaterializationValidationError(ValueError):
    """Fail-closed U02SC04 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit02SceneMaterializationValidationError(code)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    builder.content_policy.verify_artifact_digest(candidate)
    require(
        candidate.get("schema_version") == builder.content_policy.ARTIFACT_SCHEMA_VERSION,
        "ARTIFACT_SCHEMA_INVALID",
    )
    require(candidate.get("artifact_role") == builder.content_policy.CANDIDATE_ROLE, "ARTIFACT_ROLE_INVALID")
    require(candidate.get("producer_id") == builder.PRODUCER_ID, "PRODUCER_INVALID")
    require(candidate.get("level_scope") == builder.LEVEL_SCOPE, "LEVEL_SCOPE_INVALID")
    require(candidate.get("learner_facing") is False, "ARTIFACT_LEARNER_FACING_INVALID")
    require(candidate.get("admission", {}).get("status") == "PENDING_VALIDATION", "CANDIDATE_STATE_INVALID")

    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "PAYLOAD_OBJECT_REQUIRED")
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "PAYLOAD_SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    require(payload.get("level_scope") == builder.LEVEL_SCOPE, "PAYLOAD_LEVEL_SCOPE_INVALID")
    require(
        payload.get("artifact_semantics")
        == (
            "APPROVED_STRUCTURAL_SCENE_CANDIDATE_MATERIALIZATION_AND_Q7_COVERAGE_RECHECK_"
            "NOT_CANONICAL_SCENE_AUTHORITY"
        ),
        "ARTIFACT_SEMANTICS_INVALID",
    )

    source_approved = builder.approved_u02sc03_artifact()
    source_candidates = source_approved["payload"]["candidates"]
    source_by_id = {str(row["candidate_id"]): row for row in source_candidates}
    source_gaps = builder.u02sc03.genuine_gap_singulars()

    source = payload.get("source_authority", {})
    require(source.get("u02sc02_task_id") == builder.u02sc03.u02sc02.TASK_ID, "U02SC02_SOURCE_INVALID")
    require(source.get("u02sc03_task_id") == builder.u02sc03.TASK_ID, "U02SC03_SOURCE_INVALID")
    require(
        source.get("u02sc03_approved_artifact_sha256") == source_approved["artifact_sha256"],
        "U02SC03_APPROVED_DIGEST_INVALID",
    )
    require(source.get("current_unit01_cumulative_scene_world_count") == 32, "CURRENT_SCENE_WORLD_COUNT_INVALID")
    require(source.get("source_genuine_gap_count") == len(source_gaps), "SOURCE_GAP_COUNT_INVALID")
    require(source.get("source_genuine_gap_singulars") == source_gaps, "SOURCE_GAP_SET_INVALID")

    materialized = payload.get("materialized_scene_candidates")
    require(isinstance(materialized, list), "MATERIALIZED_ROWS_LIST_REQUIRED")
    require(len(materialized) == len(source_gaps), "MATERIALIZED_COUNT_INVALID")
    require(
        len({row.get("materialization_id") for row in materialized}) == len(materialized),
        "MATERIALIZATION_ID_DUPLICATE",
    )
    require(
        len({row.get("scene_candidate_signature_sha256") for row in materialized}) == len(materialized),
        "MATERIALIZATION_SIGNATURE_DUPLICATE",
    )
    require(
        [str(row.get("target_singular") or "") for row in materialized] == source_gaps,
        "MATERIALIZED_TARGET_SET_INVALID",
    )

    forbidden_text_fields = {"sentence", "sentences", "prompt", "learner_text", "question"}
    for row in materialized:
        candidate_id = str(row.get("source_candidate_id") or "")
        require(candidate_id in source_by_id, f"UNKNOWN_SOURCE_CANDIDATE:{candidate_id}")
        expected = builder.materialize_candidate(source_by_id[candidate_id])
        require(dict(row) == expected, f"MATERIALIZATION_DRIFT:{candidate_id}")
        require(row.get("materialization_kind") == builder.MATERIALIZATION_KIND, f"MATERIALIZATION_KIND_INVALID:{candidate_id}")
        require(row.get("scene_origin") == builder.SCENE_ORIGIN, f"SCENE_ORIGIN_INVALID:{candidate_id}")
        require(row.get("source_claim") == builder.SOURCE_CLAIM, f"SOURCE_CLAIM_INVALID:{candidate_id}")
        require(row.get("source_equivalence_claimed") is False, f"SOURCE_EQUIVALENCE_INVALID:{candidate_id}")
        require(row.get("canonical_scene_identity_assigned") is False, f"CANONICAL_IDENTITY_ASSIGNED:{candidate_id}")
        require(row.get("canonical_scene_ref_id") is None, f"CANONICAL_REF_ASSIGNED:{candidate_id}")
        require(row.get("runtime_bindable") is False, f"RUNTIME_BINDABLE_INVALID:{candidate_id}")
        require(row.get("learner_facing") is False, f"LEARNER_FACING_INVALID:{candidate_id}")
        require(not (forbidden_text_fields & set(row)), f"LEARNER_TEXT_FIELD_LEAK:{candidate_id}")
        core = row.get("scene_semantic_core")
        require(isinstance(core, Mapping), f"SEMANTIC_CORE_INVALID:{candidate_id}")
        require(bool(core.get("setting_code")), f"SETTING_EMPTY:{candidate_id}")
        require(core.get("target_object_lemma") == row.get("target_singular"), f"TARGET_OBJECT_DRIFT:{candidate_id}")
        require(
            core.get("object_surfaces") == [row.get("target_singular"), row.get("target_plural")],
            f"OBJECT_SURFACES_INVALID:{candidate_id}",
        )
        require(core.get("plural_contrast_supported") is True, f"PLURAL_CONTRAST_INVALID:{candidate_id}")

    expected_recheck = builder.coverage_recheck_rows([dict(row) for row in materialized])
    recheck = payload.get("coverage_recheck")
    require(isinstance(recheck, list), "COVERAGE_RECHECK_LIST_REQUIRED")
    require(recheck == expected_recheck, "COVERAGE_RECHECK_DRIFT")
    require(len(recheck) == builder.u02sc03.u02sc02.EXPECTED_VOCABULARY_COUNT, "COVERAGE_RECHECK_COUNT_INVALID")
    require(
        len({str(row.get("singular") or "") for row in recheck}) == len(recheck),
        "COVERAGE_RECHECK_TARGET_DUPLICATE",
    )

    materialized_targets = {str(row["target_singular"]) for row in materialized}
    for row in recheck:
        singular = str(row["singular"])
        status = str(row["coverage_status"])
        if singular in materialized_targets:
            require(status == "COVERED_BY_ADMITTED_U02_SCENE_CANDIDATE", f"MATERIALIZED_TARGET_STATUS_INVALID:{singular}")
            require(bool(row.get("materialization_id")), f"MATERIALIZED_TARGET_ID_MISSING:{singular}")
        if row.get("scene_gate") != "DIRECT_SCENE_ELIGIBLE":
            require(status == "GATED_NON_SCENE_GAP", f"GATED_STATUS_INVALID:{singular}")
            require(row.get("materialization_id") is None, f"GATED_MATERIALIZATION_LEAK:{singular}")

    counts = payload.get("coverage_denominators", {})
    require(counts.get("unit02_vocabulary_surface_count") == len(recheck), "VOCABULARY_DENOMINATOR_INVALID")
    require(counts.get("current_canonical_scene_world_count") == 32, "CANONICAL_SCENE_WORLD_INVALID")
    require(counts.get("new_unit02_scene_candidate_count") == len(materialized), "NEW_CANDIDATE_COUNT_INVALID")
    require(
        counts.get("projected_cumulative_scene_world_count_if_candidates_promoted")
        == 32 + len(materialized),
        "PROJECTED_SCENE_WORLD_INVALID",
    )
    require(
        counts.get("direct_eligible_covered_by_admitted_candidate_count") == len(materialized),
        "CANDIDATE_COVERAGE_COUNT_INVALID",
    )
    require(counts.get("candidate_adjusted_remaining_direct_scene_gap_count") == 0, "REMAINING_GAP_NOT_ZERO")
    require(counts.get("candidate_adjusted_remaining_direct_scene_gap_singulars") == [], "REMAINING_GAP_SET_NOT_EMPTY")
    require(
        counts.get("direct_eligible_covered_by_existing_scene_count")
        + counts.get("direct_eligible_covered_by_admitted_candidate_count")
        + counts.get("gated_non_scene_gap_count")
        == len(recheck),
        "COVERAGE_PARTITION_INVALID",
    )

    contract = payload.get("question7_micro_scene_coverage_contract", {})
    for key in (
        "source_gap_denominator_preserved",
        "one_materialization_per_admitted_gap_candidate",
        "all_source_genuine_gaps_have_materialized_candidates",
        "candidate_adjusted_remaining_direct_scene_gap_is_zero",
        "q7_micro_scene_denominator_resolved",
        "materialized_candidate_is_not_canonical_scene_identity",
        "materialized_candidate_is_not_runtime_bindable",
        "materialized_candidate_is_not_learner_facing_text",
    ):
        require(contract.get(key) is True, f"Q7_CONTRACT_INVALID:{key}")

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "canonical_scene_authority_mutated",
        "unit01_scene_authority_mutated",
        "unit02_vocabulary_authority_mutated",
        "canonical_scene_created",
        "canonical_scene_promoted",
        "learner_facing_scene_created",
        "questionbank_mutated",
        "learner_runtime_connected",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    next_scope = payload.get("next_scope", {})
    require(next_scope.get("coverage_denominator_number") == 8, "NEXT_DENOMINATOR_NUMBER_INVALID")
    require(next_scope.get("coverage_denominator") == "COMMUNICATIVE_FUNCTION", "NEXT_DENOMINATOR_INVALID")
    require(next_scope.get("scope_status") == builder.NEXT_SCOPE_STATUS, "NEXT_SCOPE_STATUS_INVALID")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_INVALID")

    report: dict[str, Any] = {
        "status": builder.VALIDATION_PASS_STATUS,
        "validator_id": VALIDATOR_ID,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "materialized_scene_candidate_count": len(materialized),
        "remaining_direct_scene_gap_count": 0,
        "error_count": 0,
        "errors": [],
    }
    report["report_sha256"] = builder.content_policy.digest(report)
    return report


def validate_approved(
    approved: Mapping[str, Any], validation_report: Mapping[str, Any]
) -> dict[str, Any]:
    builder.content_policy.verify_artifact_digest(approved)
    require(approved.get("artifact_role") == builder.content_policy.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
    require(approved.get("producer_id") == builder.PRODUCER_ID, "APPROVED_PRODUCER_INVALID")
    require(approved.get("learner_facing") is False, "APPROVED_LEARNER_FACING_INVALID")
    require(approved.get("admission", {}).get("status") == "APPROVED", "APPROVED_STATUS_INVALID")
    receipts = approved.get("validation_receipts")
    require(isinstance(receipts, list) and len(receipts) == 1, "APPROVED_RECEIPT_INVALID")
    require(receipts[0].get("validator_id") == VALIDATOR_ID, "APPROVED_VALIDATOR_INVALID")
    require(receipts[0].get("receipt_sha256") == validation_report.get("report_sha256"), "APPROVED_RECEIPT_DIGEST_INVALID")
    payload = approved.get("payload")
    require(isinstance(payload, Mapping), "APPROVED_PAYLOAD_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "APPROVED_TASK_INVALID")
    require(payload.get("coverage_denominators", {}).get("candidate_adjusted_remaining_direct_scene_gap_count") == 0, "APPROVED_Q7_GAP_NOT_ZERO")
    require(payload.get("claim_boundaries", {}).get("canonical_scene_created") is False, "APPROVED_CANONICAL_SCENE_WRITE")
    require(payload.get("next_scope", {}).get("scope_status") == builder.NEXT_SCOPE_STATUS, "APPROVED_NEXT_SCOPE_INVALID")
    return {
        "status": builder.PASS_STATUS,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "materialized_scene_candidate_count": len(payload["materialized_scene_candidates"]),
        "remaining_direct_scene_gap_count": 0,
        "error_count": 0,
        "errors": [],
    }


def main() -> int:
    candidate = builder.build_candidate_artifact()
    report = validate_candidate(candidate)
    approved = builder.admit_validated_candidate(candidate, report)
    approved_report = validate_approved(approved, report)
    print(f"STATUS={builder.PASS_STATUS}")
    print(f"MATERIALIZED_SCENE_CANDIDATES={approved_report['materialized_scene_candidate_count']}")
    print("REMAINING_DIRECT_SCENE_GAPS=0")
    print("Q7_MICRO_SCENE_COVERAGE=RESOLVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
