#!/usr/bin/env python3
"""Build the approved A1/A1+ Reading/Writing private-pilot package.

The package is static and offline. It contains approved learning content and
text-mode PracticeItems, but it does not start learner sessions, write learner
state, collect evidence, or promote production runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_derived_pedagogy_fullfix import (
    build_artifact as build_pedagogy_artifact,
)
from ulga.builders.build_a1_grammar_operator_confirmation_text_mode_pilot import (
    build_and_validate_from_repo as build_promotion_source,
)
from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import (
    build_and_validate_from_repo as build_practice_source,
)
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item

TASK_ID = "R7-M105O_A1A1PlusTextModePrivatePilotPackageIntegration"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_RESUME_TASK = "R7-M105P_A1A1PlusTextModePrivatePilotExecutionEvidenceIntake"

OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_text_mode_private_pilot_package.json"
REPORT_PATH = (
    REPO_ROOT
    / "ulga/reports/a1_grammar_text_mode_private_pilot_package_validation.json"
)

SKILLS = ("reading", "writing")


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _topological_unit_sequence(units: list[Mapping[str, Any]]) -> list[str]:
    by_id = {unit["grammar_unit_id"]: unit for unit in units}
    dependencies = {
        grammar_id: {
            dep
            for dep in unit.get("prerequisite_unit_ids", [])
            if dep in by_id and dep != grammar_id
        }
        for grammar_id, unit in by_id.items()
    }
    sequence: list[str] = []
    remaining = set(by_id)
    while remaining:
        ready = sorted(
            grammar_id
            for grammar_id in remaining
            if dependencies[grammar_id].issubset(sequence)
        )
        if not ready:
            raise ValueError(
                "pilot_unit_prerequisite_cycle:"
                + json.dumps(
                    {
                        grammar_id: sorted(dependencies[grammar_id])
                        for grammar_id in sorted(remaining)
                    },
                    ensure_ascii=False,
                )
            )
        sequence.extend(ready)
        remaining.difference_update(ready)
    return sequence


def _validated_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    practice, practice_report = build_practice_source()
    if practice_report.get("validation_status") != "PASS":
        raise RuntimeError("practice_source_validation_failed")
    pedagogy = build_pedagogy_artifact(practice)
    promotion, promotion_report = build_promotion_source()
    if promotion_report.get("validation_status") != "PASS":
        raise RuntimeError("promotion_source_validation_failed")
    return pedagogy, promotion


def build_artifact(
    pedagogy: Mapping[str, Any],
    promotion: Mapping[str, Any],
) -> dict[str, Any]:
    units = pedagogy.get("learning_units", [])
    items = pedagogy.get("item_bank", [])
    by_row_source = pedagogy.get("by_egp_row_id", {})
    approved_units = promotion.get("by_grammar_unit_id", {})
    approved_rows = promotion.get("by_egp_row_id", {})

    unit_ids = {unit["grammar_unit_id"] for unit in units}
    if len(units) != 24 or set(approved_units) != unit_ids:
        raise ValueError("pilot_package_unit_identity_mismatch")
    if len(by_row_source) != 109 or set(approved_rows) != set(by_row_source):
        raise ValueError("pilot_package_row_identity_mismatch")
    if promotion.get("release_gates", {}).get("text_mode_private_pilot_gate") != (
        "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT"
    ):
        raise ValueError("text_mode_pilot_promotion_gate_not_pass")

    item_ids: set[str] = set()
    items_by_unit: dict[str, list[dict[str, Any]]] = {
        grammar_id: [] for grammar_id in unit_ids
    }
    for source_item in items:
        item = deepcopy(source_item)
        item_id = item.get("item_id")
        if not item_id or item_id in item_ids:
            raise ValueError(f"duplicate_or_missing_pilot_item_id:{item_id}")
        item_ids.add(item_id)
        grammar_focus = item.get("content_binding", {}).get("grammar_focus", [])
        if len(grammar_focus) != 1 or grammar_focus[0] not in unit_ids:
            raise ValueError(f"pilot_item_grammar_focus_invalid:{item_id}")
        gate = validate_practice_item(item)
        if gate.get("gate_status") != "PASS":
            raise ValueError(f"pilot_item_grammar_gate_fail:{item_id}")
        item["pilot_delivery_status"] = "READY_NOT_DELIVERED"
        item["actual_attempt_count"] = 0
        item["learner_state_write"] = False
        items_by_unit[grammar_focus[0]].append(item)

    sequence = _topological_unit_sequence(units)
    source_by_id = {unit["grammar_unit_id"]: unit for unit in units}
    package_units: list[dict[str, Any]] = []
    for sequence_index, grammar_id in enumerate(sequence, start=1):
        unit = source_by_id[grammar_id]
        unit_items = items_by_unit[grammar_id]
        practice_ids = [
            item["item_id"]
            for item in unit_items
            if item.get("item_role") == "practice"
        ]
        assessment_ids = [
            item["item_id"]
            for item in unit_items
            if item.get("item_role") == "assessment"
        ]
        reading_ids = [
            item["item_id"] for item in unit_items if item.get("skill") == "reading"
        ]
        writing_ids = [
            item["item_id"] for item in unit_items if item.get("skill") == "writing"
        ]
        package_units.append(
            {
                "sequence_index": sequence_index,
                "grammar_unit_id": grammar_id,
                "official_egp_level": unit.get("official_egp_level", "A1"),
                "internal_stage": unit.get("internal_stage"),
                "prerequisite_unit_ids": list(
                    unit.get("prerequisite_unit_ids", [])
                ),
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "learning_content": {
                    "title_en": unit.get("title_en"),
                    "title_zh_tw": unit.get("title_zh_tw"),
                    "learning_objectives": deepcopy(
                        unit.get("learning_objectives", [])
                    ),
                    "form_rules": deepcopy(unit.get("form_rules", [])),
                    "meaning_functions": deepcopy(
                        unit.get("meaning_functions", [])
                    ),
                    "usage_conditions": deepcopy(
                        unit.get("usage_conditions", [])
                    ),
                    "positive_examples": deepcopy(
                        unit.get("positive_examples", [])
                    ),
                    "negative_examples": deepcopy(
                        unit.get("negative_examples", [])
                    ),
                    "common_error_tags": deepcopy(
                        unit.get("common_error_tags", [])
                    ),
                    "contrast_unit_ids": list(
                        unit.get("contrast_unit_ids", [])
                    ),
                },
                "delivery_plan": {
                    "practice_item_ids": practice_ids,
                    "assessment_item_ids": assessment_ids,
                    "reading_item_ids": reading_ids,
                    "writing_item_ids": writing_ids,
                    "practice_item_count": len(practice_ids),
                    "assessment_item_count": len(assessment_ids),
                    "reading_item_count": len(reading_ids),
                    "writing_item_count": len(writing_ids),
                    "delivery_status": "READY_NOT_STARTED",
                },
                "operator_approval_status": approved_units[grammar_id][
                    "operator_review_status"
                ],
                "text_mode_private_pilot_status": "READY_NOT_STARTED",
                "actual_learner_attempt_count": 0,
                "actual_mastery_status": "NOT_MEASURED",
            }
        )

    by_row = {
        row_id: {
            "egp_row_id": row_id,
            "grammar_unit_ids": list(
                by_row_source[row_id]["grammar_unit_ids"]
            ),
            "reading_item_ids": list(
                by_row_source[row_id]["reading_item_ids"]
            ),
            "writing_item_ids": list(
                by_row_source[row_id]["writing_item_ids"]
            ),
            "assessment_item_ids": list(
                by_row_source[row_id]["assessment_item_ids"]
            ),
            "pilot_delivery_status": "READY_NOT_DELIVERED",
            "actual_learner_evidence_status": "NOT_COLLECTED",
        }
        for row_id in sorted(by_row_source)
    }

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_private_pilot_package",
        "artifact_type": "approved_private_text_mode_learning_package",
        "schema_version": "a1_grammar_text_mode_private_pilot_package.v1",
        "package_manifest": {
            "package_mode": "PRIVATE_TEXT_MODE",
            "skills": list(SKILLS),
            "official_level": "A1",
            "internal_stages": ["A1", "A1+"],
            "unit_sequence": sequence,
            "unit_count": 24,
            "canonical_row_count": 109,
            "item_count": 192,
            "practice_item_count": 144,
            "assessment_item_count": 48,
            "reading_item_count": 96,
            "writing_item_count": 96,
            "operator_controlled": True,
            "pilot_started": False,
        },
        "source_refs": {
            "promotion_artifact_id": promotion.get("artifact_id"),
            "promotion_operator_evidence_ref": promotion.get(
                "operator_decision", {}
            ).get("operator_evidence_ref"),
            "pedagogy_artifact_id": pedagogy.get("artifact_id"),
        },
        "learning_units": package_units,
        "item_bank": [
            item
            for grammar_id in sequence
            for item in items_by_unit[grammar_id]
        ],
        "by_egp_row_id": by_row,
        "release_gates": {
            "operator_confirmation_gate": "PASS",
            "text_mode_private_pilot_package_gate": "PASS_READY",
            "pilot_execution_gate": "BLOCKED_NOT_STARTED",
            "actual_learner_evidence_gate": "BLOCKED_NOT_COLLECTED",
            "audio_scope_gate": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
            "full_four_skill_release_gate": (
                "BLOCKED_AUDIO_AND_REAL_EVIDENCE_DEFERRED"
            ),
            "production_runtime_gate": "BLOCKED_NOT_APPROVED",
        },
        "claim_boundaries": {
            "text_mode_private_pilot_package_complete": True,
            "text_mode_private_pilot_started": False,
            "actual_learner_attempts_collected": False,
            "actual_mastery_measured": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "full_four_skill_release_complete": False,
            "production_runtime_complete": False,
            "no_persistent_learner_state_write": True,
            "no_a2_a2plus_expansion": True,
        },
        "continuation_gate": {
            "status": "BLOCKED_REQUIRES_ACTUAL_PRIVATE_PILOT_EVIDENCE",
            "blocker_type": "REAL_LEARNER_EVIDENCE_REQUIRED",
            "next_resume_task": NEXT_RESUME_TASK,
        },
    }


def validate_artifact(
    artifact: Mapping[str, Any],
    pedagogy: Mapping[str, Any],
    promotion: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    manifest = artifact.get("package_manifest", {})
    units = artifact.get("learning_units", [])
    items = artifact.get("item_bank", [])
    rows = artifact.get("by_egp_row_id", {})

    if len(units) != 24:
        errors.append("pilot_package_unit_count_not_24")
    if len(rows) != 109:
        errors.append("pilot_package_row_count_not_109")
    if len(items) != 192:
        errors.append("pilot_package_item_count_not_192")
    if set(rows) != set(pedagogy.get("by_egp_row_id", {})):
        errors.append("pilot_package_row_identity_mismatch")
    if manifest.get("unit_sequence") != [
        unit.get("grammar_unit_id") for unit in units
    ]:
        errors.append("pilot_package_sequence_index_mismatch")

    sequence_positions = {
        grammar_id: index
        for index, grammar_id in enumerate(
            manifest.get("unit_sequence", [])
        )
    }
    item_ids: set[str] = set()
    for unit in units:
        grammar_id = unit.get("grammar_unit_id")
        if unit.get("operator_approval_status") != "APPROVED_TEXT_MODE":
            errors.append(f"pilot_unit_not_operator_approved:{grammar_id}")
        plan = unit.get("delivery_plan", {})
        if plan.get("practice_item_count") != 6:
            errors.append(f"pilot_unit_practice_count_not_6:{grammar_id}")
        if plan.get("assessment_item_count") != 2:
            errors.append(f"pilot_unit_assessment_count_not_2:{grammar_id}")
        if plan.get("reading_item_count") != 4:
            errors.append(f"pilot_unit_reading_count_not_4:{grammar_id}")
        if plan.get("writing_item_count") != 4:
            errors.append(f"pilot_unit_writing_count_not_4:{grammar_id}")
        for prerequisite in unit.get("prerequisite_unit_ids", []):
            if prerequisite in sequence_positions and (
                sequence_positions[prerequisite]
                >= sequence_positions.get(grammar_id, -1)
            ):
                errors.append(
                    f"pilot_prerequisite_after_unit:{grammar_id}:{prerequisite}"
                )

    for item in items:
        item_id = item.get("item_id")
        if not item_id or item_id in item_ids:
            errors.append(f"pilot_duplicate_or_missing_item_id:{item_id}")
        item_ids.add(item_id)
        if item.get("skill") not in SKILLS:
            errors.append(f"pilot_item_skill_out_of_scope:{item_id}")
        if item.get("pilot_delivery_status") != "READY_NOT_DELIVERED":
            errors.append(f"pilot_item_delivery_status_invalid:{item_id}")
        if item.get("actual_attempt_count") != 0:
            errors.append(f"pilot_item_false_attempt_count:{item_id}")
        if item.get("learner_state_write") is not False:
            errors.append(f"pilot_item_learner_write_enabled:{item_id}")

    expected_counts = {
        "unit_count": 24,
        "canonical_row_count": 109,
        "item_count": 192,
        "practice_item_count": 144,
        "assessment_item_count": 48,
        "reading_item_count": 96,
        "writing_item_count": 96,
    }
    for field, expected in expected_counts.items():
        if manifest.get(field) != expected:
            errors.append(f"pilot_manifest_count_mismatch:{field}")

    gates = artifact.get("release_gates", {})
    if gates.get("operator_confirmation_gate") != "PASS":
        errors.append("pilot_operator_confirmation_gate_not_pass")
    if gates.get("text_mode_private_pilot_package_gate") != "PASS_READY":
        errors.append("pilot_package_gate_not_pass")
    if gates.get("pilot_execution_gate") != "BLOCKED_NOT_STARTED":
        errors.append("pilot_execution_gate_forged_open")
    if gates.get("audio_scope_gate") != (
        "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"
    ):
        errors.append("pilot_audio_boundary_drift")

    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("text_mode_private_pilot_package_complete") is not True:
        errors.append("pilot_package_completion_missing")
    for field in (
        "text_mode_private_pilot_started",
        "actual_learner_attempts_collected",
        "actual_mastery_measured",
        "audio_scope_complete",
        "full_four_skill_release_complete",
        "production_runtime_complete",
    ):
        if boundaries.get(field) is not False:
            errors.append(f"pilot_false_completion_claim:{field}")
    if boundaries.get("audio_scope_deferred") is not True:
        errors.append("pilot_audio_not_deferred")
    if boundaries.get("no_persistent_learner_state_write") is not True:
        errors.append("pilot_persistent_write_boundary_missing")

    if promotion.get("release_gates", {}).get(
        "text_mode_private_pilot_gate"
    ) != "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT":
        errors.append("pilot_source_promotion_gate_not_pass")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "coverage_summary": {
            "unit_count": len(units),
            "canonical_row_count": len(rows),
            "item_count": len(items),
            "practice_item_count": sum(
                item.get("item_role") == "practice" for item in items
            ),
            "assessment_item_count": sum(
                item.get("item_role") == "assessment" for item in items
            ),
            "reading_item_count": sum(
                item.get("skill") == "reading" for item in items
            ),
            "writing_item_count": sum(
                item.get("skill") == "writing" for item in items
            ),
            "actual_learner_attempt_count": 0,
        },
        "gate_checks": {
            "operator_approval_consumed": gates.get(
                "operator_confirmation_gate"
            )
            == "PASS",
            "package_24_units_109_rows_192_items": (
                len(units) == 24 and len(rows) == 109 and len(items) == 192
            ),
            "prerequisite_order_valid": not any(
                error.startswith("pilot_prerequisite_after_unit")
                for error in errors
            ),
            "text_mode_only": not any(
                error.startswith("pilot_item_skill_out_of_scope")
                for error in errors
            ),
            "no_learner_state_write": not any(
                error.startswith("pilot_item_learner_write_enabled")
                for error in errors
            ),
            "pilot_not_started": boundaries.get(
                "text_mode_private_pilot_started"
            )
            is False,
        },
        "errors": errors,
        "warnings": [
            "The package is ready for a controlled private pilot but contains no real learner evidence.",
            "Audio remains deferred and is not included in this package.",
        ],
        "stop_reason": (
            "REAL_LEARNER_EVIDENCE_REQUIRED"
            if status == "PASS"
            else "VALIDATION_FAILURE"
        ),
        "next_resume_task": NEXT_RESUME_TASK if status == "PASS" else None,
        "validation_mode": "STATIC_PACKAGE_CONTRACT_REVIEW_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    pedagogy, promotion = _validated_sources()
    artifact = build_artifact(pedagogy, promotion)
    report = validate_artifact(artifact, pedagogy, promotion)
    return artifact, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact, report = build_and_validate_from_repo()
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
