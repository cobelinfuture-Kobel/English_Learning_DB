#!/usr/bin/env python3
"""Validate U01QB11 in-place runtime migration and 474-item replay readback."""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_u01qb11_unit01_reconciled_question_bank_runtime_migration_and_474_replay as builder
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB11_UNIT01_RECONCILED_QUESTION_BANK_RUNTIME_MIGRATION_474_REPLAY_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_U01QB11_UNIT01_RECONCILED_QUESTION_BANK_RUNTIME_MIGRATION_474_REPLAY_VALIDATION"


class RuntimeMigrationValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeMigrationValidationError(code)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(report.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(report.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(report.get("status") == builder.PASS_STATUS, "STATUS_INVALID")

    unsigned = dict(report)
    readback_sha = unsigned.pop("readback_sha256", None)
    require(readback_sha == builder.digest(unsigned), "READBACK_DIGEST_INVALID")

    migration = report.get("migration")
    require(isinstance(migration, Mapping), "MIGRATION_MISSING")
    require(migration.get("validation_status") == builder.PASS_STATUS, "MIGRATION_STATUS_INVALID")
    require(migration.get("base_item_count") == builder.EXPECTED_BASE_COUNT, "BASE_COUNT_INVALID")
    require(migration.get("extension_item_count") == builder.EXPECTED_EXTENSION_COUNT, "EXTENSION_COUNT_INVALID")
    require(migration.get("combined_runtime_item_count") == builder.EXPECTED_RUNTIME_COUNT, "RUNTIME_COUNT_INVALID")
    require(migration.get("m3_learner_state_rewritten") is False, "M3_REWRITE_INVALID")
    require(migration.get("m6_attempts_or_scoring_deleted") is False, "M6_DELETE_INVALID")
    require(migration.get("historical_retired_response_contracts_preserved") is True, "HISTORICAL_CONTRACT_PRESERVATION_INVALID")
    require(isinstance(migration.get("u01qb10_artifact_sha256"), str) and len(migration["u01qb10_artifact_sha256"]) == 64, "U01QB10_SHA_INVALID")
    require(isinstance(migration.get("real62_extension_artifact_sha256"), str) and len(migration["real62_extension_artifact_sha256"]) == 64, "REAL62_SHA_INVALID")
    require(isinstance(migration.get("real62_extension_identity_sha256"), str) and len(migration["real62_extension_identity_sha256"]) == 64, "REAL62_IDENTITY_SHA_INVALID")
    require(isinstance(migration.get("combined_source_bank_sha256"), str) and len(migration["combined_source_bank_sha256"]) == 64, "COMBINED_SHA_INVALID")
    if migration.get("already_migrated") is True:
        require(migration.get("retired_base_item_count") == 0, "IDEMPOTENT_RETIRED_COUNT_INVALID")
        require(migration.get("production_item_added_count") == 0, "IDEMPOTENT_ADDED_COUNT_INVALID")
    else:
        require(migration.get("retired_base_item_count") == builder.EXPECTED_RETIRED_BASE_COUNT, "RETIRED_COUNT_INVALID")
        require(migration.get("production_item_added_count") == builder.EXPECTED_PRODUCTION_ADDED_COUNT, "PRODUCTION_ADDED_COUNT_INVALID")

    replay = report.get("replay_474")
    require(isinstance(replay, Mapping), "REPLAY_MISSING")
    require(replay.get("runtime_item_count") == builder.EXPECTED_RUNTIME_COUNT, "REPLAY_RUNTIME_COUNT_INVALID")
    require(replay.get("base_item_count") == builder.EXPECTED_BASE_COUNT, "REPLAY_BASE_COUNT_INVALID")
    require(replay.get("extension_item_count") == builder.EXPECTED_EXTENSION_COUNT, "REPLAY_EXTENSION_COUNT_INVALID")
    require(replay.get("skill_distribution") == builder.EXPECTED_SKILL_COUNTS, "REPLAY_SKILL_DISTRIBUTION_INVALID")
    require(replay.get("capture_enabled_item_count") == builder.EXPECTED_CAPTURE_ENABLED, "REPLAY_CAPTURE_COUNT_INVALID")
    require(replay.get("deterministic_auto_pass_replay_count") == builder.EXPECTED_AUTO_PASS_REPLAY, "REPLAY_AUTO_PASS_INVALID")
    require(replay.get("feature_rubric_pending_human_replay_count") == builder.EXPECTED_PENDING_HUMAN_REPLAY, "REPLAY_PENDING_HUMAN_INVALID")
    require(replay.get("speaking_practice_only_count") == builder.EXPECTED_SPEAKING_PRACTICE_ONLY, "REPLAY_SPEAKING_INVALID")
    require(replay.get("production_family_counts") == builder.EXPECTED_PRODUCTION_FAMILY_COUNTS, "REPLAY_PRODUCTION_FAMILY_INVALID")
    require(replay.get("m6_score_function_reused") is True, "M6_SCORE_REUSE_INVALID")
    require(replay.get("speaking_scoring_enabled") is False, "SPEAKING_SCORING_INVALID")
    replay_unsigned = dict(replay)
    replay_sha = replay_unsigned.pop("replay_sha256", None)
    require(replay_sha == builder.digest(replay_unsigned), "REPLAY_DIGEST_INVALID")

    canary = report.get("production_attempt_canary")
    require(isinstance(canary, Mapping), "CANARY_MISSING")
    if canary.get("executed") is not False:
        require(canary.get("attempt_count") == 3, "CANARY_ATTEMPT_COUNT_INVALID")
        require(
            canary.get("outcomes")
            == {
                u01qb10.PF13: "AUTO_PASS",
                u01qb10.PF14: "PENDING_HUMAN_REVIEW",
                u01qb10.PF15: "PENDING_HUMAN_REVIEW",
            },
            "CANARY_OUTCOME_INVALID",
        )
        require(canary.get("m3_exposure_authority_reused") is True, "CANARY_M3_REUSE_INVALID")
        require(canary.get("m6_response_capture_reused") is True, "CANARY_M6_CAPTURE_INVALID")
        require(canary.get("m6_scoring_authority_reused") is True, "CANARY_M6_SCORE_INVALID")
        require(canary.get("speaking_capture_or_scoring_used") is False, "CANARY_SPEAKING_BOUNDARY_INVALID")

    boundaries = report.get("boundaries")
    require(
        boundaries
        == {
            "question_bank_total_expanded": False,
            "second_question_bank_created": False,
            "existing_u01qb02_runtime_reused": True,
            "existing_real62_extension_reused": True,
            "m3_learner_state_rewritten": False,
            "m6_attempts_or_scoring_deleted": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "BOUNDARIES_INVALID",
    )
    require(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS,
        "runtime_item_count": replay["runtime_item_count"],
        "auto_pass_replay_count": replay["deterministic_auto_pass_replay_count"],
        "pending_human_replay_count": replay["feature_rubric_pending_human_replay_count"],
        "speaking_practice_only_count": replay["speaking_practice_only_count"],
        "production_attempt_canary_executed": canary.get("executed") is not False,
    }
