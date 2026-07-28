#!/usr/bin/env python3
"""Validate U01E S00 multi-standard denominators and current lineage."""
from __future__ import annotations

import json
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s00_multistandard_denominator_and_lineage as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_ONLINE_V1_2_U01E_S00_MULTISTANDARD_DENOMINATOR_LINEAGE_VALIDATOR"


class S00ValidationError(ValueError):
    """Fail-closed S00 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise S00ValidationError(code)


def validate_artifact(
    artifact: Mapping[str, Any], safe_report: Mapping[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        require(artifact.get("task_id") == builder.TASK_ID, "artifact_task_invalid")
        require(artifact.get("validation_status") == builder.PASS_STATUS, "artifact_status_invalid")
        core = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
        require(artifact.get("artifact_sha256") == builder.digest(core), "artifact_digest_invalid")
        safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
        require(safe_report.get("report_sha256") == builder.digest(safe_core), "safe_digest_invalid")
        require(safe_report.get("validation_status") == builder.PASS_STATUS, "safe_status_invalid")

        denominators = artifact.get("denominators")
        require(isinstance(denominators, Mapping), "denominators_missing")
        authority = denominators.get("authority", {})
        for key, expected in builder.EXPECTED_AUTHORITY_COUNTS.items():
            require(authority.get(key) == expected, f"authority_denominator_invalid:{key}")
        require(
            int(authority.get("evp_a1_unique_lemma_count") or 0) > 0,
            "evp_unique_lemma_denominator_invalid",
        )

        ket = denominators.get("ket_prerequisite", {})
        require(
            ket.get("required_a1_a1plus_mastery_node_count")
            == builder.EXPECTED_KET_REQUIRED_MASTERY_NODE_COUNT,
            "ket_required_denominator_invalid",
        )
        require(
            ket.get("a2_handoff_lesson_count") == builder.EXPECTED_KET_A2_HANDOFF_LESSON_COUNT,
            "ket_handoff_denominator_invalid",
        )
        require(ket.get("uncovered_required_node_count") == 0, "ket_required_uncovered")
        require(ket.get("a2_lock_state") == "LOCKED_BY_DESIGN", "ket_a2_lock_invalid")
        require(
            ket.get("flyers_and_a2_handoff_excluded_from_current_completion") is True,
            "ket_handoff_in_required_completion",
        )

        cambridge = denominators.get("cambridge", {})
        require(cambridge.get("unit_alignment_count") == 24, "cambridge_unit_denominator_invalid")
        require(
            cambridge.get("required_current_path_unit_alignment_count") == 23,
            "cambridge_current_path_denominator_invalid",
        )
        require(
            cambridge.get("flyers_handoff_only_unit_alignment_count") == 1,
            "cambridge_flyers_handoff_invalid",
        )
        require(cambridge.get("unit01_cambridge_stage") == "STARTERS", "unit01_stage_invalid")
        require(cambridge.get("assessment_pattern_count") == 8, "assessment_pattern_denominator_invalid")
        require(
            cambridge.get("granular_capability_denominator_status")
            == "NOT_MATERIALIZED_IN_COMMITTED_POLICY",
            "cambridge_granular_gap_not_explicit",
        )

        context = artifact.get("unit01_current_authority_context", {})
        require(context.get("grammar_unit_id") == builder.m01.UNIT_ID, "unit01_identity_invalid")
        require(context.get("cambridge_stage") == "STARTERS", "unit01_cambridge_context_invalid")
        require(
            context.get("unit_level_bindings_are_not_asset_target_bindings") is True,
            "unit_binding_overclaimed",
        )

        runtime = artifact.get("unit01_current_runtime_lineage", {})
        require(
            runtime.get("response_contract_count") == builder.EXPECTED_UNIT01_ACTIVITY_COUNT,
            "unit01_contract_count_invalid",
        )
        require(
            runtime.get("response_contract_count_by_skill") == builder.EXPECTED_UNIT01_SKILL_COUNTS,
            "unit01_skill_count_invalid",
        )
        assets = runtime.get("assets")
        require(isinstance(assets, list) and len(assets) == 11, "unit01_asset_rows_invalid")
        require(
            runtime.get("asset_target_binding_gap_count") == 11,
            "unit01_asset_target_gap_count_invalid",
        )
        for row in assets:
            require(
                row.get("asset_target_binding_status")
                == "UNIT_LEVEL_ONLY_ASSET_TARGET_UNRESOLVED",
                f"asset_binding_guessed:{row.get('asset_key')}",
            )
            for field in (
                "target_evp_sense_ids",
                "target_egp_row_ids",
                "target_chunk_ids",
                "target_sentence_ids",
                "target_pattern_ids",
                "target_ket_prerequisite_node_ids",
            ):
                require(row.get(field) == [], f"unproven_asset_target_present:{field}")

        encoded = json.dumps(artifact, ensure_ascii=False).casefold()
        for forbidden in ('"response_json"', '"accepted_texts"', '"accepted_sequence"'):
            require(forbidden not in encoded, f"private_answer_or_response_leak:{forbidden}")
        safe_encoded = json.dumps(safe_report, ensure_ascii=False).casefold()
        for forbidden in ('"asset_key"', '"attempt_id"', '"learner_id"', '"response_json"'):
            require(forbidden not in safe_encoded, f"safe_report_private_identity_leak:{forbidden}")

        gap_codes = {row.get("gap_code") for row in artifact.get("explicit_gaps", [])}
        require(
            "UNIT01_ASSET_LEVEL_AUTHORITY_TARGET_INDEX_MISSING" in gap_codes,
            "unit01_target_index_gap_missing",
        )
        require(
            "CAMBRIDGE_GRANULAR_CAPABILITY_DENOMINATOR_NOT_MATERIALIZED" in gap_codes,
            "cambridge_capability_gap_missing",
        )
        boundaries = artifact.get("claim_boundaries", {})
        require(boundaries.get("metadata_only") is True, "metadata_only_boundary_invalid")
        for key in (
            "canonical_authority_written",
            "learner_database_written",
            "response_contract_changed",
            "response_attempt_changed",
            "mastery_inferred",
            "flyers_or_a2_in_required_completion",
            "unit02_modified",
            "audio_enabled",
            "speaking_capture_enabled",
            "a2_unlocked",
        ):
            require(boundaries.get(key) is False, f"boundary_invalid:{key}")
    except (S00ValidationError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": builder.TASK_ID,
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }
