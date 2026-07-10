#!/usr/bin/env python3
"""Materialize and validate A1/A1+ Reading/Writing grammar closure."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item

TASK_ID = "R7-M105D_A1GrammarReadingWritingClosedLoop"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105E_A1GrammarLearnerMasteryReviewLoop"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_reading_writing_closed_loop.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_reading_writing_closed_loop_validation.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _activity_role(activity_id: str) -> str:
    return "assessment" if "__A" in activity_id else "practice"


def _normalize_activity(unit: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    activity_id = item["item_id"]
    skill = item["skill"]
    role = _activity_role(activity_id)
    return {
        "activity_id": activity_id,
        "activity_role": role,
        "grammar_unit_id": unit["grammar_unit_id"],
        "official_egp_level": "A1",
        "internal_stage": unit["internal_stage"],
        "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
        "skill": skill,
        "evidence_dimension": item["evidence_dimension"],
        "task_type": item["task_type"],
        "prompt": item["prompt"],
        "response_mode": item["response_mode"],
        "options": deepcopy(item.get("options", [])),
        "answer_key": deepcopy(item["answer_key"]),
        "content_binding": deepcopy(item["content_binding"]),
        "grammar_gate": deepcopy(item["grammar_gate"]),
        "source_trace": {
            "source_activity_id": activity_id,
            "source_milestone": "R7-M105C_A1A1PlusFullTeachableCoverage",
            "content_origin": "project_authored_derived_content",
            "raw_external_source_text_copied": False,
            "restricted_source_payload_persisted": False,
        },
        "closure_evidence": {
            "receptive": skill == "reading",
            "productive": skill == "writing",
            "checkpoint": role == "assessment",
            "candidate_evidence_only": True,
            "learner_attempt_evidence": False,
        },
    }


def build_artifact(candidate: dict[str, Any]) -> dict[str, Any]:
    source_summary = candidate.get("coverage_summary", {})
    if source_summary.get("candidate_teaching_ready_unit_count") != 24:
        raise ValueError("candidate_source_not_24_units")
    if source_summary.get("candidate_teachable_unique_egp_row_count") != 109:
        raise ValueError("candidate_source_not_109_rows")
    if source_summary.get("promoted_private_learning_unit_count") != 0:
        raise ValueError("candidate_source_already_promoted")

    reading: list[dict[str, Any]] = []
    writing: list[dict[str, Any]] = []
    unit_index: dict[str, dict[str, Any]] = {}
    row_work: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "grammar_unit_ids": set(),
            "reading_activity_ids": [],
            "writing_activity_ids": [],
            "reading_assessment_ids": [],
            "writing_assessment_ids": [],
            "reading_evidence_dimensions": set(),
            "writing_evidence_dimensions": set(),
        }
    )

    for unit in candidate["learning_units"]:
        grammar_id = unit["grammar_unit_id"]
        items = unit["practice_items"] + unit["assessment_items"]
        normalized = [_normalize_activity(unit, item) for item in items]
        unit_reading = [item for item in normalized if item["skill"] == "reading"]
        unit_writing = [item for item in normalized if item["skill"] == "writing"]
        reading.extend(unit_reading)
        writing.extend(unit_writing)
        unit_index[grammar_id] = {
            "grammar_unit_id": grammar_id,
            "internal_stage": unit["internal_stage"],
            "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
            "reading_activity_ids": [item["activity_id"] for item in unit_reading],
            "writing_activity_ids": [item["activity_id"] for item in unit_writing],
            "reading_assessment_ids": [item["activity_id"] for item in unit_reading if item["activity_role"] == "assessment"],
            "writing_assessment_ids": [item["activity_id"] for item in unit_writing if item["activity_role"] == "assessment"],
            "reading_closure_status": "CANDIDATE_PATH_READY",
            "writing_closure_status": "CANDIDATE_PATH_READY",
            "cross_skill_closure_status": "CANDIDATE_READING_WRITING_CLOSED",
        }
        for row_id in unit["canonical_egp_row_ids"]:
            row = row_work[row_id]
            row["grammar_unit_ids"].add(grammar_id)
            for item in unit_reading:
                row["reading_activity_ids"].append(item["activity_id"])
                row["reading_evidence_dimensions"].add(item["evidence_dimension"])
                if item["activity_role"] == "assessment":
                    row["reading_assessment_ids"].append(item["activity_id"])
            for item in unit_writing:
                row["writing_activity_ids"].append(item["activity_id"])
                row["writing_evidence_dimensions"].add(item["evidence_dimension"])
                if item["activity_role"] == "assessment":
                    row["writing_assessment_ids"].append(item["activity_id"])

    by_row = {}
    for row_id, value in sorted(row_work.items()):
        by_row[row_id] = {
            "egp_row_id": row_id,
            "grammar_unit_ids": sorted(value["grammar_unit_ids"]),
            "reading_activity_ids": sorted(set(value["reading_activity_ids"])),
            "writing_activity_ids": sorted(set(value["writing_activity_ids"])),
            "reading_assessment_ids": sorted(set(value["reading_assessment_ids"])),
            "writing_assessment_ids": sorted(set(value["writing_assessment_ids"])),
            "reading_evidence_dimensions": sorted(value["reading_evidence_dimensions"]),
            "writing_evidence_dimensions": sorted(value["writing_evidence_dimensions"]),
            "reading_path_status": "CANDIDATE_RECEPTIVE_PATH_READY",
            "writing_path_status": "CANDIDATE_PRODUCTIVE_PATH_READY",
            "cross_skill_closure_status": "CANDIDATE_READING_WRITING_CLOSED",
            "learner_mastery_status": "NOT_MEASURED",
        }

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_reading_writing_closed_loop",
        "artifact_type": "a1_a1plus_candidate_reading_writing_activity_bank",
        "schema_version": "a1_grammar_reading_writing_closed_loop.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "source_artifact_id": candidate["artifact_id"],
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "reading_activity_count": len(reading),
            "writing_activity_count": len(writing),
            "reading_practice_count": sum(item["activity_role"] == "practice" for item in reading),
            "writing_practice_count": sum(item["activity_role"] == "practice" for item in writing),
            "reading_assessment_count": sum(item["activity_role"] == "assessment" for item in reading),
            "writing_assessment_count": sum(item["activity_role"] == "assessment" for item in writing),
            "rows_with_reading_path": len(by_row),
            "rows_with_writing_path": len(by_row),
            "rows_with_reading_assessment": len(by_row),
            "rows_with_writing_assessment": len(by_row),
            "candidate_cross_skill_closed_row_count": len(by_row),
            "candidate_cross_skill_row_coverage_percent": 100.0,
            "promoted_private_learning_row_count": 0,
            "mastery_measured_row_count": 0,
        },
        "reading_activity_bank": reading,
        "writing_activity_bank": writing,
        "by_grammar_unit_id": unit_index,
        "by_egp_row_id": by_row,
        "claim_boundaries": {
            "candidate_reading_writing_closure_complete": True,
            "operator_review_complete": False,
            "private_learning_promotion_complete": False,
            "learner_attempt_collection_complete": False,
            "learner_mastery_runtime_complete": False,
            "listening_integration_complete": False,
            "speaking_integration_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(artifact: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    reading = artifact.get("reading_activity_bank", [])
    writing = artifact.get("writing_activity_bank", [])
    all_items = reading + writing
    ids = [item.get("activity_id") for item in all_items]
    source_units = {unit["grammar_unit_id"]: unit for unit in candidate.get("learning_units", [])}
    source_ids = {
        item["item_id"]
        for unit in source_units.values()
        for item in unit.get("practice_items", []) + unit.get("assessment_items", [])
    }

    if len(reading) != 96 or len(writing) != 96:
        errors.append("reading_writing_activity_count_mismatch")
    if len(ids) != 192 or len(set(ids)) != 192 or set(ids) != source_ids:
        errors.append("activity_identity_partition_mismatch")

    for item in all_items:
        activity_id = item.get("activity_id")
        skill = item.get("skill")
        if skill not in {"reading", "writing"}:
            errors.append(f"invalid_skill:{activity_id}")
            continue
        if skill == "reading" and item not in reading:
            errors.append(f"reading_partition_mismatch:{activity_id}")
        if skill == "writing" and item not in writing:
            errors.append(f"writing_partition_mismatch:{activity_id}")
        grammar_id = item.get("grammar_unit_id")
        source_unit = source_units.get(grammar_id)
        if not source_unit:
            errors.append(f"unknown_grammar_unit:{activity_id}")
            continue
        if item.get("canonical_egp_row_ids") != source_unit.get("canonical_egp_row_ids"):
            errors.append(f"activity_row_binding_mismatch:{activity_id}")
        gate_item = {
            "item_id": activity_id,
            "content_binding": item.get("content_binding"),
            "grammar_gate": item.get("grammar_gate"),
        }
        gate = validate_practice_item(gate_item)
        if gate.get("gate_status") != "PASS":
            errors.append(f"activity_grammar_gate_fail:{activity_id}")
        trace = item.get("source_trace", {})
        if trace.get("raw_external_source_text_copied") is not False or trace.get("restricted_source_payload_persisted") is not False:
            errors.append(f"unsafe_source_payload:{activity_id}")
        evidence = item.get("closure_evidence", {})
        if evidence.get("learner_attempt_evidence") is not False:
            errors.append(f"false_learner_evidence_claim:{activity_id}")

    by_unit = artifact.get("by_grammar_unit_id", {})
    if len(by_unit) != 24 or set(by_unit) != set(source_units):
        errors.append("unit_closure_index_mismatch")
    for grammar_id, unit in by_unit.items():
        if len(unit.get("reading_activity_ids", [])) != 4:
            errors.append(f"unit_reading_path_incomplete:{grammar_id}")
        if len(unit.get("writing_activity_ids", [])) != 4:
            errors.append(f"unit_writing_path_incomplete:{grammar_id}")
        if len(unit.get("reading_assessment_ids", [])) != 1:
            errors.append(f"unit_reading_assessment_missing:{grammar_id}")
        if len(unit.get("writing_assessment_ids", [])) != 1:
            errors.append(f"unit_writing_assessment_missing:{grammar_id}")

    source_rows = set(candidate.get("by_egp_row_id", {}))
    by_row = artifact.get("by_egp_row_id", {})
    if len(by_row) != 109 or set(by_row) != source_rows:
        errors.append("row_closure_index_not_109_of_109")
    for row_id, row in by_row.items():
        if not row.get("reading_activity_ids") or not row.get("writing_activity_ids"):
            errors.append(f"row_cross_skill_path_missing:{row_id}")
        if not row.get("reading_assessment_ids") or not row.get("writing_assessment_ids"):
            errors.append(f"row_assessment_path_missing:{row_id}")
        if row.get("learner_mastery_status") != "NOT_MEASURED":
            errors.append(f"false_row_mastery_claim:{row_id}")

    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "reading_activity_count": 96,
        "writing_activity_count": 96,
        "reading_practice_count": 72,
        "writing_practice_count": 72,
        "reading_assessment_count": 24,
        "writing_assessment_count": 24,
        "rows_with_reading_path": 109,
        "rows_with_writing_path": 109,
        "rows_with_reading_assessment": 109,
        "rows_with_writing_assessment": 109,
        "candidate_cross_skill_closed_row_count": 109,
        "candidate_cross_skill_row_coverage_percent": 100.0,
        "promoted_private_learning_row_count": 0,
        "mastery_measured_row_count": 0,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("coverage_summary_mismatch")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("operator_review_complete") is not False or boundaries.get("private_learning_promotion_complete") is not False:
        errors.append("false_review_or_promotion_claim")
    if boundaries.get("learner_mastery_runtime_complete") is not False:
        errors.append("false_mastery_runtime_claim")
    for field in (
        "no_a2_a2plus_expansion",
        "no_learner_state_write",
        "no_external_nlp_dependency",
        "no_restricted_source_payload_copy",
    ):
        if boundaries.get(field) is not True:
            errors.append(f"scope_boundary_missing:{field}")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_reading_writing_closed_loop_validation",
        "validation_status": status,
        "coverage_summary": expected_summary,
        "gate_checks": {
            "units_24_of_24": len(by_unit) == 24,
            "rows_109_of_109": len(by_row) == 109,
            "reading_items_96": len(reading) == 96,
            "writing_items_96": len(writing) == 96,
            "activity_identity_preserved": set(ids) == source_ids,
            "all_activity_grammar_gates_pass": not any(error.startswith("activity_grammar_gate_fail") for error in errors),
            "all_rows_have_reading_writing_assessments": not any(error.startswith("row_assessment_path_missing") for error in errors),
            "promotion_still_blocked": boundaries.get("private_learning_promotion_complete") is False,
            "mastery_still_unmeasured": expected_summary["mastery_measured_row_count"] == 0,
            "no_a2plus_scope": boundaries.get("no_a2_a2plus_expansion") is True,
            "no_learner_state_write": boundaries.get("no_learner_state_write") is True,
        },
        "errors": errors,
        "warnings": [
            "Reading/Writing closure represents candidate activity and assessment paths, not learner mastery.",
            "Listening, Speaking, operator review, and private-learning promotion remain incomplete.",
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, candidate_report = build_candidate_source()
    if candidate_report.get("validation_status") != "PASS":
        raise RuntimeError("candidate_source_validation_failed")
    artifact = build_artifact(candidate)
    report = validate_artifact(artifact, candidate)
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
