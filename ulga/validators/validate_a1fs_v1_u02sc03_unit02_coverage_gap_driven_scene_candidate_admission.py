#!/usr/bin/env python3
"""Validate U02SC03 coverage-gap-driven scene-authoring candidates."""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02sc03_unit02_coverage_gap_driven_scene_candidate_admission
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = builder.VALIDATOR_ID


class Unit02SceneCandidateValidationError(ValueError):
    """Fail-closed U02SC03 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit02SceneCandidateValidationError(code)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    builder.content_policy.verify_artifact_digest(candidate)
    require(candidate.get("schema_version") == builder.content_policy.ARTIFACT_SCHEMA_VERSION, "ARTIFACT_SCHEMA_INVALID")
    require(candidate.get("artifact_role") == builder.content_policy.CANDIDATE_ROLE, "ARTIFACT_ROLE_INVALID")
    require(candidate.get("producer_id") == builder.PRODUCER_ID, "PRODUCER_INVALID")
    require(candidate.get("level_scope") == builder.LEVEL_SCOPE, "LEVEL_SCOPE_INVALID")
    require(candidate.get("learner_facing") is False, "ARTIFACT_LEARNER_FACING_INVALID")
    require(candidate.get("admission", {}).get("status") == "PENDING_VALIDATION", "CANDIDATE_ADMISSION_STATE_INVALID")

    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "PAYLOAD_OBJECT_REQUIRED")
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "PAYLOAD_SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    require(payload.get("level_scope") == builder.LEVEL_SCOPE, "PAYLOAD_LEVEL_SCOPE_INVALID")
    require(
        payload.get("artifact_semantics")
        == "APPROVED_SCENE_AUTHORING_CANDIDATE_SET_NOT_CANONICAL_SCENE_AUTHORITY",
        "ARTIFACT_SEMANTICS_INVALID",
    )

    summaries, vocabulary = builder.source_maps()
    gaps = builder.genuine_gap_singulars()
    candidates = payload.get("candidates")
    require(isinstance(candidates, list), "CANDIDATES_LIST_REQUIRED")
    require(len(candidates) == len(gaps), "CANDIDATE_COUNT_INVALID")
    require(len({row.get("candidate_id") for row in candidates}) == len(candidates), "CANDIDATE_ID_DUPLICATE")
    target_singulars = [str(row.get("target_singular") or "") for row in candidates]
    require(target_singulars == gaps, "CANDIDATE_TARGET_SET_INVALID")

    for row in candidates:
        singular = str(row.get("target_singular") or "")
        require(singular in summaries and singular in vocabulary, f"UNKNOWN_TARGET:{singular}")
        summary = summaries[singular]
        vocab = vocabulary[singular]
        require(row.get("candidate_id") == f"U02-SC-GAP-{builder._slug(singular)}", f"CANDIDATE_ID_INVALID:{singular}")
        require(row.get("candidate_kind") == builder.CANDIDATE_KIND, f"CANDIDATE_KIND_INVALID:{singular}")
        require(row.get("unit_id") == builder.UNIT_ID, f"CANDIDATE_UNIT_INVALID:{singular}")
        require(row.get("target_plural") == vocab["plural"], f"PLURAL_INVALID:{singular}")
        require(row.get("vocabulary_ids") == vocab["vocabulary_ids"], f"VOCABULARY_IDS_INVALID:{singular}")
        require(row.get("primary_scene_family") == vocab["primary_scene_family"], f"PRIMARY_FAMILY_INVALID:{singular}")
        require(row.get("secondary_scene_families") == vocab["secondary_scene_families"], f"SECONDARY_FAMILIES_INVALID:{singular}")
        require(row.get("scene_gate") == "DIRECT_SCENE_ELIGIBLE", f"NON_DIRECT_CANDIDATE:{singular}")
        require(summary.get("genuine_missing_new_unit02_scene_need") is True, f"NOT_GENUINE_GAP:{singular}")
        require(summary.get("semantic_reuse_scene_refs") == [], f"SEMANTIC_REUSE_PRESENT:{singular}")

        evidence = row.get("source_gap_evidence")
        require(isinstance(evidence, Mapping), f"GAP_EVIDENCE_INVALID:{singular}")
        require(evidence.get("missing_reason") == summary["missing_reason"], f"MISSING_REASON_DRIFT:{singular}")
        require(evidence.get("direct_scene_refs") == summary["direct_scene_refs"], f"DIRECT_REFS_DRIFT:{singular}")
        require(evidence.get("reprojection_scene_refs") == summary["reprojection_scene_refs"], f"REPROJECT_REFS_DRIFT:{singular}")
        require(evidence.get("semantic_reuse_scene_refs") == [], f"SEMANTIC_REUSE_EVIDENCE_INVALID:{singular}")
        require(
            evidence.get("family_compatible_scene_refs") == summary["family_compatible_scene_refs"],
            f"FAMILY_REFS_DRIFT:{singular}",
        )

        contract = row.get("candidate_semantic_contract")
        require(isinstance(contract, Mapping), f"SEMANTIC_CONTRACT_INVALID:{singular}")
        require(contract.get("required_object_surface") == singular, f"REQUIRED_OBJECT_INVALID:{singular}")
        require(contract.get("required_plural_surface") == vocab["plural"], f"REQUIRED_PLURAL_INVALID:{singular}")
        preferred = contract.get("preferred_scene_families")
        require(isinstance(preferred, list) and preferred, f"PREFERRED_FAMILIES_INVALID:{singular}")
        require(preferred[0] == vocab["primary_scene_family"], f"PREFERRED_PRIMARY_INVALID:{singular}")
        require(contract.get("must_support_unit02_plural_contrast") is True, f"PLURAL_CONTRAST_FLAG_INVALID:{singular}")

        require(row.get("source_claim") == builder.SOURCE_CLAIM, f"SOURCE_CLAIM_INVALID:{singular}")
        require(row.get("source_equivalence_claimed") is False, f"SOURCE_EQUIVALENCE_INVALID:{singular}")
        require(row.get("canonical_scene_identity_assigned") is False, f"CANONICAL_IDENTITY_ASSIGNED:{singular}")
        require(row.get("learner_facing") is False, f"LEARNER_FACING_CANDIDATE:{singular}")

    source = payload.get("source_authority", {})
    source_projection = builder.source_projection()
    require(source.get("u02sc02_task_id") == builder.u02sc02.TASK_ID, "SOURCE_TASK_INVALID")
    require(source.get("u02sc02_status") == builder.u02sc02.PASS_STATUS, "SOURCE_STATUS_INVALID")
    require(
        source.get("u02sc02_projection_sha256") == builder.content_policy.digest(source_projection),
        "SOURCE_PROJECTION_DIGEST_INVALID",
    )
    require(source.get("genuine_gap_count") == len(gaps), "SOURCE_GAP_COUNT_INVALID")
    require(source.get("genuine_gap_singulars") == gaps, "SOURCE_GAP_SET_INVALID")

    denominators = payload.get("admission_denominators", {})
    require(denominators.get("source_genuine_gap_count") == len(gaps), "DENOMINATOR_SOURCE_GAP_INVALID")
    require(denominators.get("candidate_count") == len(gaps), "DENOMINATOR_CANDIDATE_INVALID")
    require(denominators.get("one_candidate_per_genuine_gap") is True, "ONE_TO_ONE_CANDIDATE_INVALID")
    require(denominators.get("candidate_target_singulars") == gaps, "DENOMINATOR_TARGET_SET_INVALID")

    contract = payload.get("candidate_contract", {})
    for key in (
        "candidate_is_gap_driven_not_preallocated",
        "candidate_requires_direct_scene_eligible_gap",
        "semantic_reuse_precludes_candidate_creation",
        "family_compatibility_without_semantic_reuse_does_not_preclude_candidate",
        "candidate_is_not_learner_facing_scene_text",
        "candidate_is_not_canonical_scene_identity",
        "source_equivalence_is_not_claimed",
    ):
        require(contract.get(key) is True, f"CANDIDATE_CONTRACT_INVALID:{key}")

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "canonical_scene_authority_mutated",
        "unit01_scene_authority_mutated",
        "unit02_vocabulary_authority_mutated",
        "canonical_scene_created",
        "learner_facing_scene_created",
        "questionbank_mutated",
        "learner_runtime_connected",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_INVALID")

    report: dict[str, Any] = {
        "status": builder.VALIDATION_PASS_STATUS,
        "validator_id": VALIDATOR_ID,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "candidate_count": len(candidates),
        "source_genuine_gap_count": len(gaps),
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
    require(payload.get("claim_boundaries", {}).get("canonical_scene_created") is False, "APPROVED_CANONICAL_SCENE_WRITE")
    return {
        "status": builder.PASS_STATUS,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "candidate_count": len(payload["candidates"]),
        "error_count": 0,
        "errors": [],
    }


def main() -> int:
    candidate = builder.build_candidate_artifact()
    report = validate_candidate(candidate)
    approved = builder.admit_validated_candidate(candidate, report)
    approved_report = validate_approved(approved, report)
    print(f"STATUS={builder.PASS_STATUS}")
    print(f"CANDIDATES={approved_report['candidate_count']}")
    print("POLICY_BOUND_ADMISSION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
