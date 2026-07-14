#!/usr/bin/env python3
"""Validate M04A Reading integration and the fail-closed source gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_e4s_a1v1_reading_v1_integration_gate import (
    PASS_STATUS,
    RESUME_TASK,
    V1_QUESTION_TYPES,
    build_report,
)

TASK_ID = "E4S-A1V1-M04A_ReadingGrammarIntegrationAndSourceAvailabilityGate"
VALIDATION_PASS_STATUS = "PASS_READING_INTEGRATION_SOURCE_GATE_VALIDATED"


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    reading = report.get("reading_grammar_integration", {})
    if reading.get("status") != "PASS":
        errors.append("reading_grammar_integration_not_pass")
    if reading.get("shared_reading_item_count") != 96:
        errors.append("shared_reading_item_count_not_96")
    if reading.get("learning_unit_count") != 24:
        errors.append("reading_learning_unit_count_not_24")
    if reading.get("items_per_unit") != 4:
        errors.append("reading_items_per_unit_not_4")
    if reading.get("practice_item_count") != 72:
        errors.append("reading_practice_item_count_not_72")
    if reading.get("assessment_item_count") != 24:
        errors.append("reading_assessment_item_count_not_24")
    if reading.get("source_kind_counts") != {"READING_WRITING_TEXT_MODE": 96}:
        errors.append("reading_source_kind_count_mismatch")
    if reading.get("semantic_role") != "GRAMMAR_ALIGNED_READING_RECOGNITION":
        errors.append("reading_semantic_role_mismatch")
    if reading.get("not_claimed_as") != "SOURCE_GROUNDED_PASSAGE_COMPREHENSION":
        errors.append("reading_false_comprehension_claim_boundary_missing")

    fixture = report.get("reading_v1_contract_fixture", {})
    if fixture.get("status") != "PASS" or fixture.get("validator_status") != "PASS":
        errors.append("reading_v1_fixture_not_pass")
    if fixture.get("item_count") != 6:
        errors.append("reading_v1_fixture_item_count_not_6")
    if set(fixture.get("question_types", [])) != V1_QUESTION_TYPES:
        errors.append("reading_v1_fixture_question_types_mismatch")
    if fixture.get("synthetic_fixture_only") is not True:
        errors.append("reading_v1_fixture_not_marked_synthetic")
    if fixture.get("real_source_coverage_claimed") is not False:
        errors.append("reading_v1_fixture_false_source_coverage_claim")

    source = report.get("reading_source_availability", {})
    source_count = source.get("github_ci_readable_intake_item_count")
    if source_count != 0:
        errors.append("expected_current_source_count_zero")
    if source.get("status") != "BLOCKED":
        errors.append("source_status_not_blocked")
    if source.get("github_ci_readable_levels") != []:
        errors.append("github_ci_readable_levels_not_empty")
    if source.get("drive_source_folder_discovered") is not True:
        errors.append("drive_source_folder_not_recorded")
    if source.get("drive_connector_visible_normalized_file_count") != 0:
        errors.append("drive_normalized_file_count_not_zero")
    for field in (
        "raw_source_text_persisted",
        "full_passage_text_persisted",
        "source_payload_copied_to_repo",
    ):
        if source.get(field) is not False:
            errors.append(f"unsafe_source_persistence_claim:{field}")

    gate = report.get("m04_gate", {})
    if gate.get("grammar_reading_bank_integrated") is not True:
        errors.append("grammar_reading_bank_not_integrated")
    if gate.get("reading_v1_six_type_contract_healthy") is not True:
        errors.append("reading_v1_contract_not_healthy")
    if gate.get("source_grounded_comprehension_content_available") is not False:
        errors.append("false_source_grounded_content_available")
    if gate.get("reading_v1_complete") is not False:
        errors.append("false_m04_completion")
    if gate.get("m05_progression_allowed") is not False:
        errors.append("m05_progression_not_blocked")

    if report.get("validation_status") != PASS_STATUS:
        errors.append("builder_validation_status_mismatch")
    if report.get("stop_reason") != "SOURCE_EVIDENCE_REQUIRED":
        errors.append("stop_reason_not_source_evidence_required")
    if report.get("blocker_type") != "CI_READABLE_READING_SOURCE_ARTIFACT_MISSING":
        errors.append("blocker_type_mismatch")
    if report.get("last_completed_status") != "M04A_READING_INTEGRATION_GATE_COMPLETE":
        errors.append("last_completed_status_mismatch")
    if report.get("next_short_step") is not None:
        errors.append("next_short_step_should_be_blocked")
    if report.get("next_resume_task") != RESUME_TASK:
        errors.append("next_resume_task_mismatch")
    if not report.get("required_operator_action"):
        errors.append("required_operator_action_missing")

    boundaries = report.get("claim_boundaries", {})
    if boundaries.get("m04a_integration_gate_complete") is not True:
        errors.append("m04a_completion_boundary_missing")
    for field in (
        "m04_reading_v1_complete",
        "grammar_reading_items_are_source_grounded_comprehension",
        "synthetic_fixture_is_real_source_coverage",
        "learner_mastery_claimed",
        "retention_confirmed",
        "persistent_learner_state_write",
        "production_runtime_event",
        "a2_a2plus_in_scope",
    ):
        if boundaries.get(field) is not False:
            errors.append(f"false_claim:{field}")

    status = VALIDATION_PASS_STATUS if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "errors": errors,
        "validation_counts": {
            "shared_reading_item_count": reading.get("shared_reading_item_count"),
            "reading_learning_unit_count": reading.get("learning_unit_count"),
            "reading_v1_fixture_item_count": fixture.get("item_count"),
            "github_ci_readable_source_item_count": source_count,
        },
        "gate_state": {
            "m04a_complete": not errors,
            "m04_complete": False,
            "m05_progression_allowed": False,
        },
        "stop_reason": "SOURCE_EVIDENCE_REQUIRED" if not errors else "VALIDATION_FAILURE",
        "blocker_type": (
            "CI_READABLE_READING_SOURCE_ARTIFACT_MISSING" if not errors else "M04A_VALIDATION_FAILURE"
        ),
        "next_resume_task": RESUME_TASK if not errors else None,
    }


def validate() -> dict[str, Any]:
    return validate_report(build_report())


def main() -> int:
    report = validate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == VALIDATION_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
