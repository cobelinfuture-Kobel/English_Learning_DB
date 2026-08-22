#!/usr/bin/env python3
"""Materialize admitted Unit02 scene candidates and recheck Q7 micro-scene coverage.

U02SC04 consumes the independently validated/approved U02SC03 structural scene
candidates. It materializes deterministic non-learner-facing scene semantics and
rechecks the Unit02 direct-scene gap denominator without mutating the existing
Unit01 32-scene authority or assigning canonical Unit02 scene identities.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import (
    build_a1fs_v1_u02sc03_unit02_coverage_gap_driven_scene_candidate_admission
    as u02sc03,
)
from ulga.validators import (
    validate_a1fs_v1_u02sc03_unit02_coverage_gap_driven_scene_candidate_admission
    as u02sc03_validator,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02SC04_Unit02AdmittedSceneCandidateMaterializationAndCoverageRecheck"
PRODUCER_ID = "build_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck"
VALIDATOR_ID = "validate_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck"
SCHEMA_VERSION = "a1fs.v1.u02sc04.admitted_scene_candidate_materialization_coverage_recheck.v1"
PASS_STATUS = "PASS_A1FS_V1_U02SC04_UNIT02_ADMITTED_SCENE_CANDIDATE_MATERIALIZATION_AND_COVERAGE_RECHECK"
VALIDATION_PASS_STATUS = "PASS_A1FS_V1_U02SC04_MATERIALIZED_SCENE_CANDIDATE_COVERAGE_VALIDATION"
UNIT_ID = u02sc03.UNIT_ID
LEVEL_SCOPE = ["A1"]

# Q7 is Micro-scene coverage. Q8 (Communicative Function) is intentionally not
# entered by this task because the operator-approved scope is Q7 only.
NEXT_SHORT_STEP = "A1FS-V1-U02CF01_Unit02CommunicativeFunctionCoverageDenominator"
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_Q7_SCOPE"

MATERIALIZATION_KIND = "ADMITTED_STRUCTURAL_SCENE_CANDIDATE_MATERIALIZATION"
SCENE_ORIGIN = "UNIT02_COVERAGE_GAP_MODEL_AUTHORED_CANDIDATE"
SOURCE_CLAIM = "PROJECT_MODEL_AUTHORED_GAP_MATERIALIZATION_NOT_SOURCE_EQUIVALENT"

FAMILY_SETTING: dict[str, str] = {
    "SCHOOL_CLASSROOM_LEARNING": "CLASSROOM",
    "HOME_BEDROOM_LIVING": "HOME",
    "BATHROOM_SELF_CARE": "BATHROOM",
    "KITCHEN_DINING": "KITCHEN",
    "FOOD_CAFE_PICNIC": "PICNIC",
    "FAMILY_PEOPLE_SOCIAL": "FAMILY_HOME",
    "BODY_APPEARANCE": "GETTING_READY",
    "CLOTHING_PERSONAL_ITEMS": "BEDROOM",
    "PETS_FARM_ZOO": "ZOO_OR_FARM",
    "PARK_GARDEN_NATURE": "PARK_OR_GARDEN",
    "SPORTS_PLAY": "PLAYGROUND_OR_SPORTS_AREA",
    "MUSIC_DANCE": "MUSIC_ROOM",
    "MEDIA_ENTERTAINMENT_TECH": "HOME_OR_CLASSROOM",
    "TOWN_PUBLIC_PLACES": "TOWN_PUBLIC_PLACE",
    "SHOP_MONEY_SERVICES": "SHOP",
    "TRANSPORT_TRAVEL": "STATION_OR_TRAVEL_SETTING",
    "COMMUNICATION_WRITING": "CLASSROOM_OR_HOME",
    "CONTEXT_DEPENDENT": "FAMILIAR_A1_SETTING",
}


class Unit02SceneMaterializationError(ValueError):
    """Fail-closed U02SC04 construction error."""


def approved_u02sc03_artifact() -> dict[str, Any]:
    candidate = u02sc03.build_candidate_artifact()
    report = u02sc03_validator.validate_candidate(candidate)
    approved = u02sc03.admit_validated_candidate(candidate, report)
    u02sc03_validator.validate_approved(approved, report)
    if approved.get("artifact_role") != content_policy.APPROVED_ROLE:
        raise Unit02SceneMaterializationError("U02SC03_APPROVED_ROLE_INVALID")
    return approved


def _materialization_id(candidate_id: str) -> str:
    prefix = "U02-SC-GAP-"
    if not candidate_id.startswith(prefix):
        raise Unit02SceneMaterializationError(f"U02SC03_CANDIDATE_ID_INVALID:{candidate_id}")
    suffix = candidate_id[len(prefix):]
    if not suffix:
        raise Unit02SceneMaterializationError("U02SC03_CANDIDATE_ID_SUFFIX_EMPTY")
    return f"U02-SC-MAT-{suffix}"


def materialize_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(row.get("candidate_id") or "")
    singular = str(row.get("target_singular") or "")
    plural = str(row.get("target_plural") or "")
    family = str(row.get("primary_scene_family") or "")
    setting = FAMILY_SETTING.get(family)
    if not setting:
        raise Unit02SceneMaterializationError(
            f"PRIMARY_SCENE_FAMILY_SETTING_UNMAPPED:{candidate_id}:{family}"
        )
    if not singular or not plural:
        raise Unit02SceneMaterializationError(f"TARGET_SURFACE_MISSING:{candidate_id}")
    if row.get("canonical_scene_identity_assigned") is not False:
        raise Unit02SceneMaterializationError(f"SOURCE_CANDIDATE_CANONICAL_IDENTITY_INVALID:{candidate_id}")
    if row.get("learner_facing") is not False:
        raise Unit02SceneMaterializationError(f"SOURCE_CANDIDATE_LEARNER_FACING_INVALID:{candidate_id}")

    semantic_core = {
        "setting_code": setting,
        "participant_roles": ["CHILD_LEARNER", "PEER_OR_ADULT"],
        "target_object_lemma": singular,
        "object_surfaces": [singular, plural],
        "actions": ["OBSERVE", "IDENTIFY"],
        "relations": ["MULTIPLE_INSTANCES_VISIBLE", "PLAIN_S_PLURAL_GROUP"],
        "information_structure": [
            "VISIBLE_TARGET_GROUP",
            "SINGULAR_TO_PLURAL_CONTRAST_AVAILABLE",
        ],
        "communicative_functions": ["OBSERVATION", "IDENTIFICATION"],
        "plural_contrast_supported": True,
    }
    signature = content_policy.digest(
        {
            "source_candidate_id": candidate_id,
            "target_singular": singular,
            "primary_scene_family": family,
            "scene_semantic_core": semantic_core,
        }
    )
    return {
        "materialization_id": _materialization_id(candidate_id),
        "materialization_kind": MATERIALIZATION_KIND,
        "source_candidate_id": candidate_id,
        "scene_origin": SCENE_ORIGIN,
        "unit_id": UNIT_ID,
        "target_singular": singular,
        "target_plural": plural,
        "vocabulary_ids": list(row.get("vocabulary_ids") or []),
        "primary_scene_family": family,
        "secondary_scene_families": list(row.get("secondary_scene_families") or []),
        "scene_semantic_core": semantic_core,
        "scene_candidate_signature_sha256": signature,
        "source_claim": SOURCE_CLAIM,
        "source_equivalence_claimed": False,
        "canonical_scene_identity_assigned": False,
        "canonical_scene_ref_id": None,
        "runtime_bindable": False,
        "learner_facing": False,
    }


def materialized_rows() -> list[dict[str, Any]]:
    approved = approved_u02sc03_artifact()
    source_rows = approved.get("payload", {}).get("candidates")
    if not isinstance(source_rows, list) or not source_rows:
        raise Unit02SceneMaterializationError("U02SC03_APPROVED_CANDIDATES_REQUIRED")
    rows = [materialize_candidate(row) for row in source_rows]
    ids = [row["materialization_id"] for row in rows]
    targets = [row["target_singular"] for row in rows]
    signatures = [row["scene_candidate_signature_sha256"] for row in rows]
    if len(ids) != len(set(ids)):
        raise Unit02SceneMaterializationError("DUPLICATE_MATERIALIZATION_ID")
    if len(targets) != len(set(targets)):
        raise Unit02SceneMaterializationError("DUPLICATE_MATERIALIZED_TARGET")
    if len(signatures) != len(set(signatures)):
        raise Unit02SceneMaterializationError("DUPLICATE_MATERIALIZED_SEMANTIC_SIGNATURE")
    return rows


def coverage_recheck_rows(
    materialized: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    projection = u02sc03.u02sc02.payload()
    vocabulary = {
        str(row["singular"]): row
        for row in u02sc03.u02sc02.u02sc01.build_rows()
    }
    materialized_by_target = {
        str(row["target_singular"]): row for row in materialized
    }
    source_gap_set = set(u02sc03.genuine_gap_singulars())
    if set(materialized_by_target) != source_gap_set:
        raise Unit02SceneMaterializationError("MATERIALIZED_TARGET_SET_SOURCE_GAP_DRIFT")

    rows: list[dict[str, Any]] = []
    for summary in projection["vocabulary_summary"]:
        singular = str(summary["singular"])
        source = vocabulary[singular]
        gate = str(source["scene_gate"])
        semantic_reuse = list(summary["semantic_reuse_scene_refs"])
        materialization = materialized_by_target.get(singular)

        if gate != "DIRECT_SCENE_ELIGIBLE":
            status = "GATED_NON_SCENE_GAP"
        elif semantic_reuse:
            status = "COVERED_BY_EXISTING_U01_SCENE_SEMANTICS"
        elif materialization is not None:
            status = "COVERED_BY_ADMITTED_U02_SCENE_CANDIDATE"
        else:
            status = "MISSING_DIRECT_SCENE_COVERAGE"

        rows.append(
            {
                "singular": singular,
                "scene_gate": gate,
                "coverage_status": status,
                "existing_semantic_reuse_scene_refs": semantic_reuse,
                "materialization_id": (
                    materialization["materialization_id"] if materialization else None
                ),
                "source_u02sc02_genuine_gap": singular in source_gap_set,
            }
        )

    remaining = sorted(
        row["singular"]
        for row in rows
        if row["coverage_status"] == "MISSING_DIRECT_SCENE_COVERAGE"
    )
    if remaining:
        raise Unit02SceneMaterializationError(
            "DIRECT_SCENE_COVERAGE_RECHECK_FAILED:" + ",".join(remaining)
        )
    return rows


def build_payload() -> dict[str, Any]:
    approved = approved_u02sc03_artifact()
    materialized = materialized_rows()
    recheck = coverage_recheck_rows(materialized)
    projection = u02sc03.u02sc02.payload()
    source_gap_set = u02sc03.genuine_gap_singulars()

    existing_direct = sum(
        row["coverage_status"] == "COVERED_BY_EXISTING_U01_SCENE_SEMANTICS"
        for row in recheck
    )
    candidate_direct = sum(
        row["coverage_status"] == "COVERED_BY_ADMITTED_U02_SCENE_CANDIDATE"
        for row in recheck
    )
    gated = sum(row["coverage_status"] == "GATED_NON_SCENE_GAP" for row in recheck)
    remaining = [
        row["singular"]
        for row in recheck
        if row["coverage_status"] == "MISSING_DIRECT_SCENE_COVERAGE"
    ]

    if candidate_direct != len(source_gap_set) or candidate_direct != len(materialized):
        raise Unit02SceneMaterializationError("CANDIDATE_ADJUSTED_GAP_CLOSURE_COUNT_INVALID")
    if remaining:
        raise Unit02SceneMaterializationError("CANDIDATE_ADJUSTED_GAP_CLOSURE_NOT_ZERO")

    current_scene_world = int(
        projection["coverage_denominators"]["unit01_cumulative_scene_count"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "artifact_semantics": (
            "APPROVED_STRUCTURAL_SCENE_CANDIDATE_MATERIALIZATION_AND_Q7_COVERAGE_RECHECK_"
            "NOT_CANONICAL_SCENE_AUTHORITY"
        ),
        "source_authority": {
            "u02sc02_task_id": u02sc03.u02sc02.TASK_ID,
            "u02sc03_task_id": u02sc03.TASK_ID,
            "u02sc03_approved_artifact_sha256": approved["artifact_sha256"],
            "current_unit01_cumulative_scene_world_count": current_scene_world,
            "source_genuine_gap_count": len(source_gap_set),
            "source_genuine_gap_singulars": source_gap_set,
        },
        "materialized_scene_candidates": materialized,
        "coverage_recheck": recheck,
        "coverage_denominators": {
            "unit02_vocabulary_surface_count": len(recheck),
            "current_canonical_scene_world_count": current_scene_world,
            "new_unit02_scene_candidate_count": len(materialized),
            "projected_cumulative_scene_world_count_if_candidates_promoted": (
                current_scene_world + len(materialized)
            ),
            "direct_eligible_covered_by_existing_scene_count": existing_direct,
            "direct_eligible_covered_by_admitted_candidate_count": candidate_direct,
            "gated_non_scene_gap_count": gated,
            "candidate_adjusted_remaining_direct_scene_gap_count": len(remaining),
            "candidate_adjusted_remaining_direct_scene_gap_singulars": remaining,
        },
        "question7_micro_scene_coverage_contract": {
            "source_gap_denominator_preserved": True,
            "one_materialization_per_admitted_gap_candidate": True,
            "all_source_genuine_gaps_have_materialized_candidates": True,
            "candidate_adjusted_remaining_direct_scene_gap_is_zero": True,
            "q7_micro_scene_denominator_resolved": True,
            "materialized_candidate_is_not_canonical_scene_identity": True,
            "materialized_candidate_is_not_runtime_bindable": True,
            "materialized_candidate_is_not_learner_facing_text": True,
        },
        "claim_boundaries": {
            "canonical_scene_authority_mutated": False,
            "unit01_scene_authority_mutated": False,
            "unit02_vocabulary_authority_mutated": False,
            "canonical_scene_created": False,
            "canonical_scene_promoted": False,
            "learner_facing_scene_created": False,
            "questionbank_mutated": False,
            "learner_runtime_connected": False,
            "a2_unlocked": False,
        },
        "next_scope": {
            "coverage_denominator_number": 8,
            "coverage_denominator": "COMMUNICATIVE_FUNCTION",
            "scope_status": NEXT_SCOPE_STATUS,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate_artifact() -> dict[str, Any]:
    payload = build_payload()
    return content_policy.build_candidate(
        payload=payload,
        producer_id=PRODUCER_ID,
        level_scope=LEVEL_SCOPE,
        source_bindings={
            "unit_id": UNIT_ID,
            "u02sc03_task_id": u02sc03.TASK_ID,
            "u02sc03_approved_artifact_sha256": payload["source_authority"]["u02sc03_approved_artifact_sha256"],
            "source_genuine_gap_count": payload["source_authority"]["source_genuine_gap_count"],
            "materialized_scene_candidate_count": payload["coverage_denominators"]["new_unit02_scene_candidate_count"],
            "canonical_scene_created": False,
            "source_equivalence_claimed": False,
        },
    )


def admit_validated_candidate(
    candidate: Mapping[str, Any], validation_report: Mapping[str, Any]
) -> dict[str, Any]:
    if validation_report.get("status") != VALIDATION_PASS_STATUS:
        raise Unit02SceneMaterializationError("VALIDATION_REPORT_NOT_PASS")
    if validation_report.get("candidate_artifact_sha256") != candidate.get("artifact_sha256"):
        raise Unit02SceneMaterializationError("VALIDATION_REPORT_CANDIDATE_MISMATCH")
    report_sha256 = validation_report.get("report_sha256")
    unsigned = dict(validation_report)
    unsigned.pop("report_sha256", None)
    if report_sha256 != content_policy.digest(unsigned):
        raise Unit02SceneMaterializationError("VALIDATION_REPORT_SHA256_INVALID")
    return content_policy.admit_candidate(
        candidate,
        validation_receipts=[
            {
                "validator_id": VALIDATOR_ID,
                "status": "PASS",
                "receipt_sha256": str(report_sha256),
            }
        ],
        decision_ref=f"{TASK_ID}:INDEPENDENT_VALIDATION_PASS",
        producer_id=PRODUCER_ID,
    )


def main() -> int:
    artifact = build_candidate_artifact()
    counts = artifact["payload"]["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(f"CURRENT_CANONICAL_SCENE_WORLD={counts['current_canonical_scene_world_count']}")
    print(f"NEW_UNIT02_SCENE_CANDIDATES={counts['new_unit02_scene_candidate_count']}")
    print(
        "PROJECTED_SCENE_WORLD_IF_PROMOTED="
        f"{counts['projected_cumulative_scene_world_count_if_candidates_promoted']}"
    )
    print(
        "REMAINING_DIRECT_SCENE_GAPS="
        f"{counts['candidate_adjusted_remaining_direct_scene_gap_count']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
