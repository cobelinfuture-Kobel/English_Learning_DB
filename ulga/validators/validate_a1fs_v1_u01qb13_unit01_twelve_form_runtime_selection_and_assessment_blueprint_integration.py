#!/usr/bin/env python3
"""Validate U01QB13 12-form runtime-selection and assessment blueprint integration."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB13_UNIT01_TWELVE_FORM_RUNTIME_SELECTION_AND_ASSESSMENT_BLUEPRINT_INTEGRATION_VALIDATOR"


class BlueprintIntegrationValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise BlueprintIntegrationValidationError(code)


def receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    unsigned = dict(payload)
    actual_digest = unsigned.pop("blueprint_sha256", None)
    require(actual_digest == builder.digest(unsigned), "BLUEPRINT_DIGEST_INVALID")

    source = payload.get("source_identity") or {}
    require(source.get("rotation_task_id") == builder.u01qb08.TASK_ID, "ROTATION_TASK_INVALID")
    require(source.get("allocation_task_id") == builder.u01qb09.TASK_ID, "ALLOCATION_TASK_INVALID")
    require(source.get("active_question_bank_revision") == builder.u01qb12.CANONICAL_REVISION, "QUESTION_BANK_REVISION_INVALID")
    require(source.get("runtime_authority") == builder.qb02.TASK_ID, "RUNTIME_AUTHORITY_INVALID")

    execution = payload.get("execution_contract") or {}
    require(execution.get("logical_form_count") == 12, "FORM_COUNT_INVALID")
    require(execution.get("scenes_per_form") == 4, "SCENES_PER_FORM_INVALID")
    require(execution.get("activities_per_form") == 20, "ACTIVITIES_PER_FORM_INVALID")
    require(execution.get("reading_per_form") == 8, "READING_PER_FORM_INVALID")
    require(execution.get("writing_per_form") == 8, "WRITING_PER_FORM_INVALID")
    require(execution.get("speaking_practice_per_form") == 4, "SPEAKING_PER_FORM_INVALID")
    require(execution.get("scored_per_form") == 16, "SCORED_PER_FORM_INVALID")
    require(execution.get("existing_u01qb02_session_size") == builder.qb02.SESSION_SIZE, "U01QB02_SESSION_SIZE_INVALID")
    require(execution.get("skill_session_execution_containers_per_form") == 3, "EXECUTION_CONTAINER_COUNT_INVALID")
    require(execution.get("support_filler_counts_per_skill_session") == builder.SUPPORT_FILLER_COUNTS, "SUPPORT_FILLER_COUNTS_INVALID")
    require(execution.get("support_fillers_are_form_activities") is False, "SUPPORT_FILLER_FORM_CLAIM_INVALID")
    require(execution.get("support_fillers_are_assessment_evidence") is False, "SUPPORT_FILLER_ASSESSMENT_CLAIM_INVALID")
    require(execution.get("second_planner_created") is False, "SECOND_PLANNER_CREATED")
    require(execution.get("second_runtime_created") is False, "SECOND_RUNTIME_CREATED")

    assessment = payload.get("assessment_blueprint") or {}
    require(assessment.get("assessment_form_ordinals") == [10, 11, 12], "ASSESSMENT_FORMS_INVALID")
    require(assessment.get("assessment_form_count") == 3, "ASSESSMENT_FORM_COUNT_INVALID")
    require(assessment.get("scored_reading_per_assessment_form") == 8, "ASSESSMENT_READING_COUNT_INVALID")
    require(assessment.get("scored_writing_per_assessment_form") == 8, "ASSESSMENT_WRITING_COUNT_INVALID")
    require(assessment.get("speaking_practice_per_assessment_form") == 4, "ASSESSMENT_SPEAKING_PRACTICE_INVALID")
    require(assessment.get("speaking_scored") is False, "SPEAKING_ASSESSMENT_DRIFT")
    require(assessment.get("assessment_requires_scene_anchor_binding") is True, "SCENE_ANCHOR_POLICY_INVALID")

    forms = payload.get("form_summaries")
    activities = payload.get("activities")
    require(isinstance(forms, list) and len(forms) == 12, "FORM_SUMMARIES_INVALID")
    require(isinstance(activities, list) and len(activities) == 240, "ACTIVITIES_INVALID")
    require(len({str(row.get("activity_id")) for row in activities}) == 240, "DUPLICATE_ACTIVITY_ID")
    require(len({str(row.get("activity_digest")) for row in activities}) == 240, "DUPLICATE_ACTIVITY_DIGEST")

    by_form: dict[int, list[Mapping[str, Any]]] = {}
    skill_counts = Counter()
    task_counts = Counter()
    assessment_count = 0
    scored_count = 0
    speaking_count = 0
    for activity in activities:
        ordinal = int(activity.get("form_ordinal") or 0)
        require(1 <= ordinal <= 12, f"ACTIVITY_FORM_INVALID:{activity.get('activity_id')}")
        by_form.setdefault(ordinal, []).append(activity)
        anchors = activity.get("scene_anchors")
        require(isinstance(anchors, list) and anchors and all(isinstance(row, str) and row for row in anchors), f"SCENE_ANCHORS_INVALID:{activity.get('activity_id')}")
        skill = str(activity.get("skill") or "")
        angle = str(activity.get("task_angle") or "")
        families = activity.get("allowed_pattern_family_ids")
        require(skill in {"READING", "WRITING", "SPEAKING"}, f"SKILL_INVALID:{activity.get('activity_id')}")
        require(isinstance(families, list) and families, f"PATTERN_FAMILY_BINDING_MISSING:{activity.get('activity_id')}")
        skill_counts[skill] += 1
        task_counts[(skill, angle)] += 1
        if skill == "SPEAKING":
            speaking_count += 1
            require(activity.get("scored") is False, f"SPEAKING_SCORED:{activity.get('activity_id')}")
            require(activity.get("practice_only") is True, f"SPEAKING_PRACTICE_FLAG_INVALID:{activity.get('activity_id')}")
            require(activity.get("assessment_candidate") is False, f"SPEAKING_ASSESSMENT_CANDIDATE:{activity.get('activity_id')}")
            require(activity.get("binding_mode") == "SCENE_PROJECTED_PRACTICE_OVER_EXISTING_SPEAKING_ANCHOR", f"SPEAKING_BINDING_MODE_INVALID:{activity.get('activity_id')}")
            projection = activity.get("practice_projection") or {}
            require(projection.get("capture_enabled") is False, f"SPEAKING_CAPTURE_INVALID:{activity.get('activity_id')}")
            require(projection.get("assessment_eligible") is False, f"SPEAKING_PROJECTION_ASSESSMENT_INVALID:{activity.get('activity_id')}")
            require(projection.get("scoring_enabled") is False, f"SPEAKING_SCORING_INVALID:{activity.get('activity_id')}")
        else:
            scored_count += 1
            require(activity.get("scored") is True, f"SCORED_FLAG_INVALID:{activity.get('activity_id')}")
            require(activity.get("practice_only") is False, f"SCORED_PRACTICE_FLAG_INVALID:{activity.get('activity_id')}")
            require(activity.get("binding_mode") == "EXACT_CANONICAL_QUESTIONBANK_BINDING", f"SCORED_BINDING_MODE_INVALID:{activity.get('activity_id')}")
            require(tuple(families) == builder.EXACT_SCORED_BINDINGS.get((skill, angle)), f"EXACT_BINDING_DRIFT:{skill}:{angle}")
            require(activity.get("practice_projection") == {}, f"SCORED_PROJECTION_NOT_EMPTY:{activity.get('activity_id')}")
        expected_assessment = ordinal in builder.ASSESSMENT_FORM_ORDINALS and skill != "SPEAKING"
        require(bool(activity.get("assessment_candidate")) == expected_assessment, f"ASSESSMENT_CANDIDATE_INVALID:{activity.get('activity_id')}")
        assessment_count += int(expected_assessment)

    require(scored_count == 192, "SCORED_ACTIVITY_COUNT_INVALID")
    require(speaking_count == 48, "SPEAKING_ACTIVITY_COUNT_INVALID")
    require(skill_counts == Counter({"READING": 96, "WRITING": 96, "SPEAKING": 48}), "SKILL_DISTRIBUTION_INVALID")
    require(assessment_count == 48, "ASSESSMENT_ACTIVITY_COUNT_INVALID")
    for ordinal in range(1, 13):
        rows = by_form.get(ordinal, [])
        require(len(rows) == 20, f"FORM_ACTIVITY_COUNT_INVALID:{ordinal}")
        counts = Counter(str(row["skill"]) for row in rows)
        require(counts == Counter({"READING": 8, "WRITING": 8, "SPEAKING": 4}), f"FORM_SKILL_COUNT_INVALID:{ordinal}")
        require(len({str(row["scene_ref_id"]) for row in rows}) == 4, f"FORM_SCENE_COUNT_INVALID:{ordinal}")

    coverage = payload.get("coverage_readback") or {}
    require(coverage.get("activity_count") == 240, "READBACK_ACTIVITY_COUNT_INVALID")
    require(coverage.get("scored_activity_count") == 192, "READBACK_SCORED_COUNT_INVALID")
    require(coverage.get("speaking_practice_activity_count") == 48, "READBACK_SPEAKING_COUNT_INVALID")
    require(coverage.get("scored_exact_binding_count") == 192, "READBACK_EXACT_BINDING_INVALID")
    require(coverage.get("scored_unbound_count") == 0, "SCORED_UNBOUND_REMAINS")
    require(coverage.get("speaking_capture_enabled_count") == 0, "SPEAKING_CAPTURE_READBACK_INVALID")
    require(coverage.get("question_bank_total") == 474, "QUESTION_BANK_TOTAL_INVALID")
    require(coverage.get("question_bank_expanded") is False, "QUESTION_BANK_EXPANDED")

    boundaries = payload.get("boundaries") or {}
    for key in (
        "new_scene_authored",
        "question_bank_total_expanded",
        "real62_extension_modified",
        "second_planner_created",
        "second_runtime_created",
        "parallel_database_created",
        "parallel_scoring_created",
        "speaking_capture_enabled",
        "speaking_scoring_enabled",
        "unit02_to_unit24_modified",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("learner_facing") is False, "CANDIDATE_LEARNER_FACING_INVALID")
    policy_artifact.verify_artifact_digest(candidate)
    source = candidate.get("source_bindings") or {}
    require(source.get("active_question_bank_revision") == builder.u01qb12.CANONICAL_REVISION, "SOURCE_QUESTION_BANK_INVALID")
    require(source.get("runtime_task_id") == builder.qb02.TASK_ID, "SOURCE_RUNTIME_INVALID")
    require(source.get("operator_decision_ref") == builder.DECISION_REF, "SOURCE_DECISION_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_MISSING")
    return validate_payload(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validation_receipt = validate_candidate(candidate)
        require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
        require((approved.get("admission") or {}).get("status") == "APPROVED", "APPROVED_STATUS_INVALID")
        require((approved.get("admission") or {}).get("decision_ref") == builder.DECISION_REF, "DECISION_INVALID")
        require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
        require((approved.get("source_bindings") or {}).get("candidate_artifact_sha256") == candidate.get("artifact_sha256"), "CANDIDATE_BINDING_INVALID")
        require(
            approved.get("validation_receipts") == [
                {
                    "validator_id": validation_receipt["validator_id"],
                    "status": "PASS",
                    "receipt_sha256": validation_receipt["receipt_sha256"],
                }
            ],
            "VALIDATION_RECEIPT_INVALID",
        )
        policy_artifact.verify_artifact_digest(approved)
        validate_payload(approved["payload"])
    except (BlueprintIntegrationValidationError, policy_artifact.ContentPolicyBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    payload = approved.get("payload", {})
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "candidate_artifact_sha256": candidate.get("artifact_sha256"),
        "approved_artifact_sha256": approved.get("artifact_sha256"),
        "form_count": len(payload.get("form_summaries") or []),
        "activity_count": (payload.get("coverage_readback") or {}).get("activity_count", 0),
        "scored_unbound_count": (payload.get("coverage_readback") or {}).get("scored_unbound_count"),
    }
