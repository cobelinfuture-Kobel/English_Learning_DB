#!/usr/bin/env python3
"""Project accepted private-pilot evidence into mastery candidates and review routes.

The builder consumes the fail-closed M105P normalized evidence and the approved
M105O text-mode package. It never creates learner attempts, never writes learner
state, and never claims final mastery. A unit can only become a mastery candidate
pending a later retention check.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    build_and_validate_from_repo as build_intake_source,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)

TASK_ID = "R7-M105Q_A1A1PlusTextModeEvidenceProjectionAndReviewRouting"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_REAL_EVIDENCE_TASK = "R7-M105P02_A1A1PlusTextModePrivatePilotRealAttemptImport"
NEXT_REVIEW_TASK = "R7-M105R_A1A1PlusTextModeReviewSessionPackageIntegration"
NEXT_RETENTION_TASK = "R7-M105S_A1A1PlusTextModeRetentionEvidenceIntake"

OUTPUT_PATH = (
    REPO_ROOT
    / "ulga/graph/a1_grammar_text_mode_evidence_projection_review_routing.json"
)
REPORT_PATH = (
    REPO_ROOT
    / "ulga/reports/a1_grammar_text_mode_evidence_projection_review_routing_validation.json"
)

REVIEW_STAGES = (
    {"stage": "IMMEDIATE_RETRY", "due_after_attempt_steps": 1},
    {"stage": "SHORT_REVIEW", "due_after_attempt_steps": 3},
    {"stage": "SPACED_REVIEW", "due_after_attempt_steps": 7},
    {"stage": "RETENTION_CHECK", "due_after_attempt_steps": 14},
)
MASTERY_POLICY = {
    "policy_id": "a1_grammar_text_mode_actual_evidence_projection.v1",
    "minimum_reading_score": 0.75,
    "minimum_writing_score": 0.75,
    "reading_assessment_pass_required": True,
    "writing_assessment_pass_required": True,
    "full_unit_item_coverage_required": True,
    "unresolved_latest_failure_allowed": False,
    "retention_check_required_for_final_mastery": True,
    "final_mastery_claim_allowed_in_this_task": False,
    "persistent_learner_state_write": False,
}


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _unique_strings(values: Iterable[Any]) -> list[str]:
    return sorted(
        {
            value.strip()
            for value in values
            if isinstance(value, str) and value.strip()
        }
    )


def _validated_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    package, package_report = build_package_source()
    if package_report.get("validation_status") != "PASS":
        raise RuntimeError("text_mode_package_validation_failed")
    intake, intake_report = build_intake_source()
    if intake_report.get("validation_status") != "PASS":
        raise RuntimeError("real_evidence_intake_validation_failed")
    return package, intake


def _item_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    items = package.get("item_bank", [])
    index = {
        item.get("item_id"): dict(item)
        for item in items
        if isinstance(item, Mapping) and isinstance(item.get("item_id"), str)
    }
    if len(items) != 192 or len(index) != 192:
        raise ValueError("projection_package_item_index_not_192")
    return index


def _unit_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    units = package.get("learning_units", [])
    index = {
        unit.get("grammar_unit_id"): dict(unit)
        for unit in units
        if isinstance(unit, Mapping)
        and isinstance(unit.get("grammar_unit_id"), str)
    }
    if len(units) != 24 or len(index) != 24:
        raise ValueError("projection_package_unit_index_not_24")
    return index


def _latest_attempts(
    attempts: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        item_id = attempt.get("item_id")
        sequence = attempt.get("attempt_sequence")
        if not isinstance(item_id, str) or not isinstance(sequence, int):
            continue
        current = latest.get(item_id)
        if current is None or sequence > current.get("attempt_sequence", 0):
            latest[item_id] = dict(attempt)
    return latest


def _mean_score(attempts: Iterable[Mapping[str, Any]]) -> float | None:
    scores = [
        float(attempt["score"])
        for attempt in attempts
        if isinstance(attempt.get("score"), (int, float))
        and not isinstance(attempt.get("score"), bool)
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 4)


def _skill_item_ids(
    item_ids: Iterable[str],
    item_index: Mapping[str, Mapping[str, Any]],
    *,
    skill: str,
    role: str | None = None,
) -> list[str]:
    return [
        item_id
        for item_id in item_ids
        if item_id in item_index
        and item_index[item_id].get("skill") == skill
        and (role is None or item_index[item_id].get("item_role") == role)
    ]


def _unit_projection(
    unit: Mapping[str, Any],
    item_index: Mapping[str, Mapping[str, Any]],
    latest: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    plan = unit.get("delivery_plan", {})
    all_item_ids = _unique_strings(
        list(plan.get("practice_item_ids", []))
        + list(plan.get("assessment_item_ids", []))
    )
    if len(all_item_ids) != 8:
        raise ValueError(f"projection_unit_item_contract_not_8:{grammar_id}")

    attempted_item_ids = [item_id for item_id in all_item_ids if item_id in latest]
    missing_item_ids = [item_id for item_id in all_item_ids if item_id not in latest]
    latest_attempts = [latest[item_id] for item_id in attempted_item_ids]

    reading_ids = _skill_item_ids(all_item_ids, item_index, skill="reading")
    writing_ids = _skill_item_ids(all_item_ids, item_index, skill="writing")
    reading_assessment_ids = _skill_item_ids(
        all_item_ids,
        item_index,
        skill="reading",
        role="assessment",
    )
    writing_assessment_ids = _skill_item_ids(
        all_item_ids,
        item_index,
        skill="writing",
        role="assessment",
    )

    reading_latest = [latest[item_id] for item_id in reading_ids if item_id in latest]
    writing_latest = [latest[item_id] for item_id in writing_ids if item_id in latest]
    reading_score = _mean_score(reading_latest)
    writing_score = _mean_score(writing_latest)
    unresolved_failures = sorted(
        item_id
        for item_id in attempted_item_ids
        if latest[item_id].get("passed") is False
    )
    error_counts: Counter[str] = Counter(
        tag
        for attempt in latest_attempts
        for tag in attempt.get("error_tags", [])
        if isinstance(tag, str)
    )

    if not attempted_item_ids:
        evidence_status = "NOT_OBSERVED"
        projection_status = "NOT_MEASURED"
        route = None
        reasons: list[str] = []
    elif missing_item_ids:
        evidence_status = "PARTIAL_EVIDENCE"
        projection_status = "INSUFFICIENT_EVIDENCE"
        route = "COMPLETE_MISSING_ITEMS"
        reasons = ["FULL_UNIT_ITEM_COVERAGE_REQUIRED"]
    else:
        evidence_status = "FULL_UNIT_EVIDENCE"
        reasons = []
        reading_assessment_pass = bool(reading_assessment_ids) and all(
            latest[item_id].get("passed") is True
            for item_id in reading_assessment_ids
        )
        writing_assessment_pass = bool(writing_assessment_ids) and all(
            latest[item_id].get("passed") is True
            for item_id in writing_assessment_ids
        )
        if reading_score is None or reading_score < MASTERY_POLICY["minimum_reading_score"]:
            reasons.append("READING_SCORE_BELOW_THRESHOLD")
        if writing_score is None or writing_score < MASTERY_POLICY["minimum_writing_score"]:
            reasons.append("WRITING_SCORE_BELOW_THRESHOLD")
        if not reading_assessment_pass:
            reasons.append("READING_ASSESSMENT_NOT_PASSED")
        if not writing_assessment_pass:
            reasons.append("WRITING_ASSESSMENT_NOT_PASSED")
        if unresolved_failures:
            reasons.append("UNRESOLVED_LATEST_FAILURE")

        if reasons:
            projection_status = "REVIEW_REQUIRED"
            route = "TARGETED_REMEDIATION"
        else:
            projection_status = "MASTERY_CANDIDATE_PENDING_RETENTION"
            route = "RETENTION_CHECK_REQUIRED"

    return {
        "grammar_unit_id": grammar_id,
        "canonical_egp_row_ids": list(unit.get("canonical_egp_row_ids", [])),
        "evidence_status": evidence_status,
        "projection_status": projection_status,
        "latest_attempt_count": len(latest_attempts),
        "attempted_item_count": len(attempted_item_ids),
        "required_item_count": len(all_item_ids),
        "missing_item_ids": missing_item_ids,
        "unresolved_failure_item_ids": unresolved_failures,
        "reading_score": reading_score,
        "writing_score": writing_score,
        "error_tag_counts": dict(sorted(error_counts.items())),
        "review_reasons": reasons,
        "next_route": route,
        "retention_confirmed": False,
        "final_mastery_status": "NOT_CLAIMED",
        "persistent_learner_state_write": False,
    }


def _row_projection(
    row_id: str,
    grammar_unit_ids: Iterable[str],
    units: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    unit_ids = _unique_strings(grammar_unit_ids)
    statuses = [units[grammar_id]["projection_status"] for grammar_id in unit_ids]
    if statuses and all(
        status == "MASTERY_CANDIDATE_PENDING_RETENTION" for status in statuses
    ):
        status = "MASTERY_CANDIDATE_PENDING_RETENTION"
    elif "REVIEW_REQUIRED" in statuses:
        status = "REVIEW_REQUIRED"
    elif any(value != "NOT_MEASURED" for value in statuses):
        status = "PARTIAL_EVIDENCE"
    else:
        status = "NOT_OBSERVED"
    return {
        "egp_row_id": row_id,
        "grammar_unit_ids": unit_ids,
        "projection_status": status,
        "retention_confirmed": False,
        "final_mastery_status": "NOT_CLAIMED",
        "persistent_learner_state_write": False,
    }


def build_artifact(
    package: Mapping[str, Any],
    intake: Mapping[str, Any],
) -> dict[str, Any]:
    item_index = _item_index(package)
    unit_index = _unit_index(package)
    accepted_attempts = intake.get("accepted_attempts", [])
    if not isinstance(accepted_attempts, list):
        raise ValueError("projection_accepted_attempts_not_array")

    latest = _latest_attempts(accepted_attempts)
    unknown_item_ids = sorted(set(latest) - set(item_index))
    if unknown_item_ids:
        raise ValueError(
            "projection_unknown_item_ids:" + ",".join(unknown_item_ids)
        )

    by_unit = {
        grammar_id: _unit_projection(unit, item_index, latest)
        for grammar_id, unit in sorted(unit_index.items())
    }
    by_row = {
        row_id: _row_projection(
            row_id,
            row.get("grammar_unit_ids", []),
            by_unit,
        )
        for row_id, row in sorted(package.get("by_egp_row_id", {}).items())
    }

    completion_routes = []
    review_routes = []
    retention_routes = []
    for grammar_id, projection in by_unit.items():
        route = projection.get("next_route")
        if route == "COMPLETE_MISSING_ITEMS":
            completion_routes.append(
                {
                    "grammar_unit_id": grammar_id,
                    "route": route,
                    "missing_item_ids": list(projection["missing_item_ids"]),
                    "persistent_queue_write": False,
                }
            )
        elif route == "TARGETED_REMEDIATION":
            review_routes.append(
                {
                    "grammar_unit_id": grammar_id,
                    "route": route,
                    "review_reasons": list(projection["review_reasons"]),
                    "unresolved_failure_item_ids": list(
                        projection["unresolved_failure_item_ids"]
                    ),
                    "error_tag_counts": dict(projection["error_tag_counts"]),
                    "review_stages": [dict(stage) for stage in REVIEW_STAGES],
                    "persistent_queue_write": False,
                }
            )
        elif route == "RETENTION_CHECK_REQUIRED":
            retention_routes.append(
                {
                    "grammar_unit_id": grammar_id,
                    "route": route,
                    "review_stages": [dict(REVIEW_STAGES[-1])],
                    "persistent_queue_write": False,
                }
            )

    projection_counts = Counter(
        unit["projection_status"] for unit in by_unit.values()
    )
    row_counts = Counter(row["projection_status"] for row in by_row.values())
    actual_attempt_count = len(accepted_attempts)
    actual_evidence_present = actual_attempt_count > 0

    if review_routes:
        continuation_status = "REVIEW_SESSION_PACKAGE_REQUIRED"
        next_task = NEXT_REVIEW_TASK
        stop_reason = "NONE"
    elif retention_routes:
        continuation_status = "RETENTION_EVIDENCE_REQUIRED"
        next_task = NEXT_RETENTION_TASK
        stop_reason = "RETENTION_EVIDENCE_REQUIRED"
    elif actual_evidence_present:
        continuation_status = "MORE_REAL_ATTEMPT_EVIDENCE_REQUIRED"
        next_task = NEXT_REAL_EVIDENCE_TASK
        stop_reason = "REAL_LEARNER_EVIDENCE_REQUIRED"
    else:
        continuation_status = "AWAITING_REAL_ATTEMPT_EVIDENCE"
        next_task = NEXT_REAL_EVIDENCE_TASK
        stop_reason = "REAL_LEARNER_EVIDENCE_REQUIRED"

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_evidence_projection_review_routing",
        "artifact_type": "actual_evidence_mastery_candidate_and_review_projection",
        "schema_version": "a1_grammar_text_mode_evidence_projection_review_routing.v1",
        "source_refs": {
            "package_artifact_id": package.get("artifact_id"),
            "normalized_evidence_artifact_id": intake.get("artifact_id"),
            "intake_status": intake.get("intake_status"),
        },
        "mastery_policy": deepcopy(MASTERY_POLICY),
        "coverage_summary": {
            "package_unit_count": len(unit_index),
            "package_row_count": len(by_row),
            "package_item_count": len(item_index),
            "actual_attempt_count": actual_attempt_count,
            "latest_attempted_item_count": len(latest),
            "not_measured_unit_count": projection_counts.get("NOT_MEASURED", 0),
            "insufficient_evidence_unit_count": projection_counts.get(
                "INSUFFICIENT_EVIDENCE", 0
            ),
            "review_required_unit_count": projection_counts.get(
                "REVIEW_REQUIRED", 0
            ),
            "mastery_candidate_unit_count": projection_counts.get(
                "MASTERY_CANDIDATE_PENDING_RETENTION", 0
            ),
            "not_observed_row_count": row_counts.get("NOT_OBSERVED", 0),
            "partial_evidence_row_count": row_counts.get("PARTIAL_EVIDENCE", 0),
            "review_required_row_count": row_counts.get("REVIEW_REQUIRED", 0),
            "mastery_candidate_row_count": row_counts.get(
                "MASTERY_CANDIDATE_PENDING_RETENTION", 0
            ),
            "completion_route_count": len(completion_routes),
            "review_route_count": len(review_routes),
            "retention_route_count": len(retention_routes),
            "final_mastered_unit_count": 0,
            "final_mastered_row_count": 0,
        },
        "by_grammar_unit_id": by_unit,
        "by_egp_row_id": by_row,
        "routing": {
            "complete_missing_items": completion_routes,
            "targeted_review": review_routes,
            "retention_check": retention_routes,
        },
        "release_gates": {
            "evidence_projection_contract_gate": "PASS",
            "actual_learner_evidence_gate": (
                "PASS_REAL_EVIDENCE_PRESENT"
                if actual_evidence_present
                else "BLOCKED_NOT_COLLECTED"
            ),
            "review_routing_gate": (
                "PASS_READY" if review_routes else "NO_REVIEW_ROUTE_YET"
            ),
            "retention_gate": (
                "PASS_READY_FOR_RETENTION_EVIDENCE"
                if retention_routes
                else "BLOCKED_NO_MASTERY_CANDIDATE"
            ),
            "final_mastery_gate": "BLOCKED_RETENTION_NOT_CONFIRMED",
            "audio_scope_gate": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
            "production_runtime_gate": "BLOCKED_NOT_APPROVED",
        },
        "claim_boundaries": {
            "evidence_projection_pipeline_complete": True,
            "actual_learner_evidence_present": actual_evidence_present,
            "mastery_candidate_projection_available": bool(retention_routes),
            "actual_final_mastery_measured": False,
            "retention_evidence_complete": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "production_runtime_complete": False,
            "no_persistent_learner_state_write": True,
            "no_a2_a2plus_expansion": True,
        },
        "continuation_gate": {
            "status": continuation_status,
            "stop_reason": stop_reason,
            "next_task": next_task,
        },
    }


def validate_artifact(
    artifact: Mapping[str, Any],
    package: Mapping[str, Any],
    intake: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    units = artifact.get("by_grammar_unit_id", {})
    rows = artifact.get("by_egp_row_id", {})
    summary = artifact.get("coverage_summary", {})

    if len(units) != 24:
        errors.append("projection_unit_count_not_24")
    if len(rows) != 109:
        errors.append("projection_row_count_not_109")
    if set(units) != {
        unit.get("grammar_unit_id") for unit in package.get("learning_units", [])
    }:
        errors.append("projection_unit_identity_mismatch")
    if set(rows) != set(package.get("by_egp_row_id", {})):
        errors.append("projection_row_identity_mismatch")

    forbidden_final_statuses = {"MASTERED", "PERSISTENT_MASTERY_CONFIRMED"}
    for grammar_id, unit in units.items():
        if unit.get("projection_status") in forbidden_final_statuses:
            errors.append(f"projection_false_final_mastery:{grammar_id}")
        if unit.get("final_mastery_status") != "NOT_CLAIMED":
            errors.append(f"projection_final_mastery_claimed:{grammar_id}")
        if unit.get("persistent_learner_state_write") is not False:
            errors.append(f"projection_unit_persistent_write:{grammar_id}")
    for row_id, row in rows.items():
        if row.get("final_mastery_status") != "NOT_CLAIMED":
            errors.append(f"projection_row_final_mastery_claimed:{row_id}")
        if row.get("persistent_learner_state_write") is not False:
            errors.append(f"projection_row_persistent_write:{row_id}")

    routes = artifact.get("routing", {})
    for route_group in (
        "complete_missing_items",
        "targeted_review",
        "retention_check",
    ):
        for route in routes.get(route_group, []):
            if route.get("grammar_unit_id") not in units:
                errors.append(
                    f"projection_route_unknown_unit:{route_group}:"
                    f"{route.get('grammar_unit_id')}"
                )
            if route.get("persistent_queue_write") is not False:
                errors.append(
                    f"projection_route_persistent_write:{route_group}:"
                    f"{route.get('grammar_unit_id')}"
                )

    if summary.get("final_mastered_unit_count") != 0:
        errors.append("projection_false_final_mastered_unit_count")
    if summary.get("final_mastered_row_count") != 0:
        errors.append("projection_false_final_mastered_row_count")

    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("evidence_projection_pipeline_complete") is not True:
        errors.append("projection_pipeline_completion_missing")
    for field in (
        "actual_final_mastery_measured",
        "retention_evidence_complete",
        "audio_scope_complete",
        "production_runtime_complete",
    ):
        if boundaries.get(field) is not False:
            errors.append(f"projection_false_completion_claim:{field}")
    if boundaries.get("audio_scope_deferred") is not True:
        errors.append("projection_audio_not_deferred")
    if boundaries.get("no_persistent_learner_state_write") is not True:
        errors.append("projection_persistent_write_boundary_missing")
    if boundaries.get("no_a2_a2plus_expansion") is not True:
        errors.append("projection_a2_scope_boundary_missing")

    accepted_attempts = intake.get("accepted_attempts", [])
    actual_attempt_count = len(accepted_attempts) if isinstance(accepted_attempts, list) else 0
    if summary.get("actual_attempt_count") != actual_attempt_count:
        errors.append("projection_actual_attempt_count_mismatch")
    if actual_attempt_count == 0:
        if summary.get("not_measured_unit_count") != 24:
            errors.append("projection_empty_intake_units_not_all_unmeasured")
        if summary.get("not_observed_row_count") != 109:
            errors.append("projection_empty_intake_rows_not_all_unobserved")
        if artifact.get("continuation_gate", {}).get("stop_reason") != (
            "REAL_LEARNER_EVIDENCE_REQUIRED"
        ):
            errors.append("projection_empty_intake_stop_reason_invalid")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "coverage_summary": summary,
        "gate_checks": artifact.get("release_gates", {}),
        "errors": errors,
        "warnings": [
            "Mastery candidates are provisional until a real retention check passes.",
            "No learner-state persistence or production runtime promotion occurs here.",
            "Audio remains deferred and outside the text-mode projection.",
        ],
        "stop_reason": (
            artifact.get("continuation_gate", {}).get("stop_reason")
            if status == "PASS"
            else "VALIDATION_FAILURE"
        ),
        "next_task": (
            artifact.get("continuation_gate", {}).get("next_task")
            if status == "PASS"
            else None
        ),
        "validation_mode": "STATIC_PROJECTION_CONTRACT_REVIEW_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    package, intake = _validated_sources()
    artifact = build_artifact(package, intake)
    report = validate_artifact(artifact, package, intake)
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
