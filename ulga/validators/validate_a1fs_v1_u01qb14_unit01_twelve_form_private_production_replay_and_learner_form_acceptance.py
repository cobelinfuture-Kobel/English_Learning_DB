#!/usr/bin/env python3
"""Validate the U01QB14 disposable private-production replay readback."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB14_UNIT01_TWELVE_FORM_PRIVATE_PRODUCTION_REPLAY_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_U01QB14_UNIT01_TWELVE_FORM_PRIVATE_PRODUCTION_REPLAY_VALIDATION"


class PrivateProductionReplayValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PrivateProductionReplayValidationError(code)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(report.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(report.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(report.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(report.get("unit_id") == builder.u01qb13.UNIT_ID, "UNIT_INVALID")

    unsigned = dict(report)
    actual_digest = unsigned.pop("readback_sha256", None)
    require(actual_digest == builder.digest(unsigned), "READBACK_DIGEST_INVALID")

    authority = report.get("input_authority") or {}
    for key in (
        "rotation_file_sha256",
        "rotation_sha256",
        "allocation_file_sha256",
        "allocation_sha256",
        "u01qb13_blueprint_artifact_sha256",
    ):
        value = str(authority.get(key) or "")
        require(len(value) == 64 and all(char in "0123456789abcdef" for char in value), f"AUTHORITY_SHA_INVALID:{key}")
    require(
        authority.get("active_question_bank_revision") == builder.u01qb12.CANONICAL_REVISION,
        "QUESTION_BANK_REVISION_INVALID",
    )

    safety = report.get("canonical_database_safety") or {}
    require(safety.get("canonical_database_unchanged") is True, "CANONICAL_DATABASE_CHANGED")
    require(safety.get("canonical_database_opened_for_write") is False, "CANONICAL_WRITE_OPEN_INVALID")
    require(safety.get("canonical_learner_state_modified") is False, "CANONICAL_LEARNER_STATE_MODIFIED")
    require(safety.get("canonical_sha256_before") == safety.get("canonical_sha256_after"), "CANONICAL_SHA_DRIFT")
    require(safety.get("canonical_size_before") == safety.get("canonical_size_after"), "CANONICAL_SIZE_DRIFT")
    require(safety.get("canonical_mtime_ns_before") == safety.get("canonical_mtime_ns_after"), "CANONICAL_MTIME_DRIFT")

    disposable = report.get("disposable_copy") or {}
    require(disposable.get("initial_copy_matches_canonical") is True, "DISPOSABLE_INITIAL_COPY_INVALID")
    require(disposable.get("copy_modified_by_replay") is True, "DISPOSABLE_REPLAY_NOT_MATERIALIZED")
    require(disposable.get("initial_copy_sha256") == safety.get("canonical_sha256_before"), "DISPOSABLE_SOURCE_SHA_INVALID")
    require(disposable.get("final_sha256") != disposable.get("initial_copy_sha256"), "DISPOSABLE_FINAL_SHA_UNCHANGED")
    require(str(disposable.get("database") or "") != str(safety.get("canonical_database") or ""), "DISPOSABLE_PATH_EQUALS_CANONICAL")

    for runtime_key in ("runtime_before", "runtime_after"):
        runtime = report.get(runtime_key) or {}
        require(runtime.get("runtime_item_count") == builder.EXPECTED_RUNTIME_ITEMS, f"RUNTIME_COUNT_INVALID:{runtime_key}")
        require(runtime.get("extension_item_count") == builder.EXPECTED_EXTENSION_ITEMS, f"EXTENSION_COUNT_INVALID:{runtime_key}")
        require(runtime.get("u01qb12_validation_status") == builder.u01qb12.PASS_STATUS, f"U01QB12_STATUS_INVALID:{runtime_key}")
    require(report.get("runtime_before") == report.get("runtime_after"), "RUNTIME_DENOMINATOR_DRIFT")

    installation = report.get("u01qb13_installation") or {}
    require(installation.get("installed_activity_count") == builder.EXPECTED_BLUEPRINT_EXPOSURES, "BLUEPRINT_INSTALL_COUNT_INVALID")
    require(installation.get("form_count") == builder.FORM_COUNT, "BLUEPRINT_INSTALL_FORM_COUNT_INVALID")
    require(installation.get("runtime_item_count") == builder.EXPECTED_RUNTIME_ITEMS, "BLUEPRINT_INSTALL_RUNTIME_COUNT_INVALID")
    require(installation.get("second_planner_created") is False, "SECOND_PLANNER_CREATED")
    require(installation.get("second_runtime_created") is False, "SECOND_RUNTIME_CREATED")
    require(installation.get("speaking_scoring_enabled") is False, "SPEAKING_SCORING_ENABLED")

    acceptance = report.get("execution_acceptance") or {}
    require(acceptance.get("form_count") == builder.FORM_COUNT, "FORM_COUNT_INVALID")
    require(acceptance.get("session_count") == builder.EXPECTED_SESSION_COUNT, "SESSION_COUNT_INVALID")
    require(acceptance.get("runtime_session_item_count") == builder.EXPECTED_RUNTIME_SESSION_ITEMS, "SESSION_ITEM_COUNT_INVALID")
    require(acceptance.get("blueprint_binding_count") == builder.EXPECTED_BLUEPRINT_EXPOSURES, "BINDING_COUNT_INVALID")
    require(acceptance.get("blueprint_exposure_count") == builder.EXPECTED_BLUEPRINT_EXPOSURES, "EXPOSURE_COUNT_INVALID")
    require(acceptance.get("response_attempt_count") == builder.EXPECTED_SCORED_ATTEMPTS, "ATTEMPT_COUNT_INVALID")
    require(acceptance.get("support_filler_exposure_count") == 0, "SUPPORT_FILLER_EXPOSED")
    require(acceptance.get("assessment_binding_count") == builder.EXPECTED_ASSESSMENT_SCORED, "ASSESSMENT_BINDING_COUNT_INVALID")
    require(
        acceptance.get("skill_exposure_counts") == {"READING": 96, "SPEAKING": 48, "WRITING": 96},
        "SKILL_EXPOSURE_COUNTS_INVALID",
    )
    require(
        acceptance.get("outcome_counts") == {
            "AUTO_PASS": builder.EXPECTED_AUTO_PASS,
            "PENDING_HUMAN_REVIEW": builder.EXPECTED_PENDING_HUMAN,
        },
        "OUTCOME_COUNTS_INVALID",
    )
    require(acceptance.get("assessment_scored_attempt_count") == builder.EXPECTED_ASSESSMENT_SCORED, "ASSESSMENT_SCORED_COUNT_INVALID")
    require(acceptance.get("assessment_speaking_practice_count") == builder.EXPECTED_ASSESSMENT_SPEAKING, "ASSESSMENT_SPEAKING_COUNT_INVALID")
    require(acceptance.get("assessment_transfer_selection_count") == builder.EXPECTED_ASSESSMENT_SCORED, "ASSESSMENT_TRANSFER_COUNT_INVALID")

    forms = acceptance.get("forms")
    require(isinstance(forms, list) and len(forms) == builder.FORM_COUNT, "FORMS_INVALID")
    seen_ordinals: set[int] = set()
    skill_sessions = Counter()
    for form in forms:
        ordinal = int(form.get("form_ordinal", 0))
        seen_ordinals.add(ordinal)
        require(form.get("form_id") == f"U01-FORM-{ordinal:02d}", f"FORM_ID_INVALID:{ordinal}")
        require(form.get("blueprint_exposures") == 20, f"FORM_EXPOSURE_COUNT_INVALID:{ordinal}")
        require(form.get("scored_attempts") == 16, f"FORM_SCORED_COUNT_INVALID:{ordinal}")
        require(form.get("speaking_practice_exposures") == 4, f"FORM_SPEAKING_COUNT_INVALID:{ordinal}")
        expected_assessment = 16 if ordinal in builder.u01qb13.ASSESSMENT_FORM_ORDINALS else 0
        require(form.get("assessment_scored_attempts") == expected_assessment, f"FORM_ASSESSMENT_COUNT_INVALID:{ordinal}")
        sessions = form.get("sessions")
        require(isinstance(sessions, list) and len(sessions) == 3, f"FORM_SESSION_COUNT_INVALID:{ordinal}")
        for session in sessions:
            skill = str(session.get("skill") or "")
            skill_sessions[skill] += 1
            expected_activity = {"READING": 8, "WRITING": 8, "SPEAKING": 4}.get(skill)
            expected_filler = {"READING": 2, "WRITING": 2, "SPEAKING": 6}.get(skill)
            require(expected_activity is not None, f"SESSION_SKILL_INVALID:{ordinal}:{skill}")
            require(session.get("blueprint_activity_count") == expected_activity, f"SESSION_ACTIVITY_COUNT_INVALID:{ordinal}:{skill}")
            require(session.get("support_filler_count") == expected_filler, f"SESSION_FILLER_COUNT_INVALID:{ordinal}:{skill}")
            if skill == "SPEAKING":
                require(session.get("scored_attempt_count") == 0, f"SPEAKING_ATTEMPT_COUNT_INVALID:{ordinal}")
                require(session.get("speaking_practice_exposure_count") == 4, f"SPEAKING_EXPOSURE_COUNT_INVALID:{ordinal}")
            else:
                require(session.get("scored_attempt_count") == 8, f"SCORED_SESSION_COUNT_INVALID:{ordinal}:{skill}")
                require(session.get("speaking_practice_exposure_count") == 0, f"NON_SPEAKING_PRACTICE_INVALID:{ordinal}:{skill}")
    require(seen_ordinals == set(range(1, builder.FORM_COUNT + 1)), "FORM_ORDINALS_INVALID")
    require(dict(skill_sessions) == {"READING": 12, "WRITING": 12, "SPEAKING": 12}, "SKILL_SESSION_COUNTS_INVALID")

    boundaries = report.get("boundaries") or {}
    expected_false = (
        "canonical_database_mutated",
        "question_bank_total_expanded",
        "real62_extension_modified",
        "second_planner_created",
        "second_runtime_created",
        "parallel_database_authority_created",
        "parallel_scoring_created",
        "support_fillers_exposed",
        "speaking_capture_enabled",
        "speaking_scoring_enabled",
        "unit02_to_unit24_modified",
        "a2_unlocked",
    )
    require(boundaries.get("disposable_copy_used") is True, "DISPOSABLE_COPY_BOUNDARY_INVALID")
    for key in expected_false:
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")
    require(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")

    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS,
        "form_count": acceptance["form_count"],
        "session_count": acceptance["session_count"],
        "blueprint_exposure_count": acceptance["blueprint_exposure_count"],
        "response_attempt_count": acceptance["response_attempt_count"],
        "canonical_database_unchanged": True,
        "support_filler_exposure_count": 0,
        "readback_sha256": actual_digest,
    }
