#!/usr/bin/env python3
"""Build policy-bound Unit02 scene-authoring candidates from U02SC02 genuine gaps.

U02SC03 consumes the read-only U02SC02 applicability projection and admits only
coverage-gap-driven scene-authoring candidates. It does not create canonical
scene identities, learner-facing text, QuestionBank items, or A2 content.
"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import (
    build_a1fs_v1_u02sc02_unit01_canonical_scene_to_unit02_applicability_projection
    as u02sc02,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02SC03_Unit02CoverageGapDrivenSceneCandidateAdmission"
PRODUCER_ID = "build_a1fs_v1_u02sc03_unit02_coverage_gap_driven_scene_candidate_admission"
VALIDATOR_ID = "validate_a1fs_v1_u02sc03_unit02_coverage_gap_driven_scene_candidate_admission"
SCHEMA_VERSION = "a1fs.v1.u02sc03.coverage_gap_scene_candidate_admission.v1"
PASS_STATUS = "PASS_A1FS_V1_U02SC03_UNIT02_COVERAGE_GAP_DRIVEN_SCENE_CANDIDATE_ADMISSION"
VALIDATION_PASS_STATUS = "PASS_A1FS_V1_U02SC03_COVERAGE_GAP_SCENE_CANDIDATE_VALIDATION"
UNIT_ID = u02sc02.UNIT_ID
LEVEL_SCOPE = ["A1"]
NEXT_SHORT_STEP = "A1FS-V1-U02SC04_Unit02AdmittedSceneCandidateMaterializationAndCoverageRecheck"

SOURCE_CLAIM = "PROJECT_MODEL_AUTHORED_GAP_CANDIDATE_NOT_SOURCE_EQUIVALENT"
CANDIDATE_KIND = "COVERAGE_GAP_SCENE_AUTHORING_CANDIDATE"


class Unit02SceneCandidateAdmissionError(ValueError):
    """Fail-closed U02SC03 construction error."""


def _slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    if not normalized:
        raise Unit02SceneCandidateAdmissionError("EMPTY_CANDIDATE_SLUG")
    return normalized


def source_projection() -> dict[str, Any]:
    value = u02sc02.payload()
    if value.get("task_id") != u02sc02.TASK_ID or value.get("status") != u02sc02.PASS_STATUS:
        raise Unit02SceneCandidateAdmissionError("U02SC02_SOURCE_IDENTITY_INVALID")
    return value


def source_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    projection = source_projection()
    summaries = {
        str(row["singular"]): deepcopy(row)
        for row in projection["vocabulary_summary"]
    }
    vocabulary = {
        str(row["singular"]): deepcopy(row)
        for row in u02sc02.u02sc01.build_rows()
    }
    if set(summaries) != set(vocabulary):
        raise Unit02SceneCandidateAdmissionError("U02SC02_U02SC01_VOCABULARY_IDENTITY_DRIFT")
    return summaries, vocabulary


def genuine_gap_singulars() -> list[str]:
    projection = source_projection()
    summaries = projection["vocabulary_summary"]
    gaps = sorted(
        str(row["singular"])
        for row in summaries
        if row.get("genuine_missing_new_unit02_scene_need") is True
    )
    denominator = projection["coverage_denominators"]
    if len(gaps) != denominator["genuine_missing_new_unit02_scene_need_count"]:
        raise Unit02SceneCandidateAdmissionError("U02SC02_GAP_COUNT_DRIFT")
    if gaps != sorted(denominator["genuine_missing_new_unit02_scene_need_singulars"]):
        raise Unit02SceneCandidateAdmissionError("U02SC02_GAP_SET_DRIFT")
    if not gaps:
        raise Unit02SceneCandidateAdmissionError("U02SC02_GAP_SET_EMPTY")
    return gaps


def build_candidate_rows() -> list[dict[str, Any]]:
    summaries, vocabulary = source_maps()
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for singular in genuine_gap_singulars():
        summary = summaries[singular]
        vocab = vocabulary[singular]
        if vocab["scene_gate"] != "DIRECT_SCENE_ELIGIBLE":
            raise Unit02SceneCandidateAdmissionError(
                f"NON_DIRECT_GAP_CANDIDATE_FORBIDDEN:{singular}:{vocab['scene_gate']}"
            )
        if summary["semantic_reuse_scene_refs"]:
            raise Unit02SceneCandidateAdmissionError(
                f"SEMANTIC_REUSE_GAP_CANDIDATE_FORBIDDEN:{singular}"
            )
        candidate_id = f"U02-SC-GAP-{_slug(singular)}"
        if candidate_id in seen_ids:
            raise Unit02SceneCandidateAdmissionError(f"DUPLICATE_CANDIDATE_ID:{candidate_id}")
        seen_ids.add(candidate_id)
        preferred_families = [
            str(vocab["primary_scene_family"]),
            *[str(value) for value in vocab.get("secondary_scene_families") or []],
        ]
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_kind": CANDIDATE_KIND,
                "unit_id": UNIT_ID,
                "target_singular": singular,
                "target_plural": str(vocab["plural"]),
                "vocabulary_ids": list(vocab["vocabulary_ids"]),
                "primary_scene_family": str(vocab["primary_scene_family"]),
                "secondary_scene_families": list(vocab["secondary_scene_families"]),
                "scene_gate": str(vocab["scene_gate"]),
                "source_gap_evidence": {
                    "missing_reason": str(summary["missing_reason"]),
                    "direct_scene_refs": list(summary["direct_scene_refs"]),
                    "reprojection_scene_refs": list(summary["reprojection_scene_refs"]),
                    "semantic_reuse_scene_refs": list(summary["semantic_reuse_scene_refs"]),
                    "family_compatible_scene_refs": list(summary["family_compatible_scene_refs"]),
                },
                "candidate_semantic_contract": {
                    "required_object_surface": singular,
                    "required_plural_surface": str(vocab["plural"]),
                    "preferred_scene_families": preferred_families,
                    "event_intent": f"OBSERVE_MULTIPLE_{_slug(singular)}",
                    "must_support_unit02_plural_contrast": True,
                },
                "source_claim": SOURCE_CLAIM,
                "source_equivalence_claimed": False,
                "canonical_scene_identity_assigned": False,
                "learner_facing": False,
            }
        )
    return rows


def build_payload() -> dict[str, Any]:
    projection = source_projection()
    candidates = build_candidate_rows()
    gap_set = genuine_gap_singulars()
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "artifact_semantics": "APPROVED_SCENE_AUTHORING_CANDIDATE_SET_NOT_CANONICAL_SCENE_AUTHORITY",
        "source_authority": {
            "u02sc02_task_id": u02sc02.TASK_ID,
            "u02sc02_status": u02sc02.PASS_STATUS,
            "u02sc02_projection_sha256": content_policy.digest(projection),
            "unit01_cumulative_scene_count": projection["coverage_denominators"]["unit01_cumulative_scene_count"],
            "unit02_vocabulary_surface_count": projection["coverage_denominators"]["unit02_vocabulary_surface_count"],
            "genuine_gap_count": len(gap_set),
            "genuine_gap_singulars": gap_set,
        },
        "candidates": candidates,
        "admission_denominators": {
            "source_genuine_gap_count": len(gap_set),
            "candidate_count": len(candidates),
            "one_candidate_per_genuine_gap": len(candidates) == len(gap_set),
            "candidate_target_singulars": [row["target_singular"] for row in candidates],
        },
        "candidate_contract": {
            "candidate_is_gap_driven_not_preallocated": True,
            "candidate_requires_direct_scene_eligible_gap": True,
            "semantic_reuse_precludes_candidate_creation": True,
            "family_compatibility_without_semantic_reuse_does_not_preclude_candidate": True,
            "candidate_is_not_learner_facing_scene_text": True,
            "candidate_is_not_canonical_scene_identity": True,
            "source_equivalence_is_not_claimed": True,
        },
        "claim_boundaries": {
            "canonical_scene_authority_mutated": False,
            "unit01_scene_authority_mutated": False,
            "unit02_vocabulary_authority_mutated": False,
            "canonical_scene_created": False,
            "learner_facing_scene_created": False,
            "questionbank_mutated": False,
            "learner_runtime_connected": False,
            "a2_unlocked": False,
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
            "u02sc02_task_id": u02sc02.TASK_ID,
            "u02sc02_projection_sha256": payload["source_authority"]["u02sc02_projection_sha256"],
            "source_genuine_gap_count": payload["admission_denominators"]["source_genuine_gap_count"],
            "candidate_count": payload["admission_denominators"]["candidate_count"],
            "canonical_scene_created": False,
            "source_equivalence_claimed": False,
        },
    )


def admit_validated_candidate(
    candidate: Mapping[str, Any], validation_report: Mapping[str, Any]
) -> dict[str, Any]:
    if validation_report.get("status") != VALIDATION_PASS_STATUS:
        raise Unit02SceneCandidateAdmissionError("VALIDATION_REPORT_NOT_PASS")
    if validation_report.get("candidate_artifact_sha256") != candidate.get("artifact_sha256"):
        raise Unit02SceneCandidateAdmissionError("VALIDATION_REPORT_CANDIDATE_MISMATCH")
    report_sha256 = validation_report.get("report_sha256")
    unsigned = dict(validation_report)
    unsigned.pop("report_sha256", None)
    if report_sha256 != content_policy.digest(unsigned):
        raise Unit02SceneCandidateAdmissionError("VALIDATION_REPORT_SHA256_INVALID")
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
    payload = artifact["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"SOURCE_GENUINE_GAPS={payload['admission_denominators']['source_genuine_gap_count']}")
    print(f"CANDIDATES={payload['admission_denominators']['candidate_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
