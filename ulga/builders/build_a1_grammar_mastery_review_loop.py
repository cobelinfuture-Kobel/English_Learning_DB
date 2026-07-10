#!/usr/bin/env python3
"""Pure A1/A1+ learner-attempt, mastery, review, and retention projection."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_reading_writing_closed_loop import (
    build_and_validate_from_repo as build_closure_source,
)

TASK_ID = "R7-M105E_A1GrammarLearnerMasteryReviewLoop"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105F_A1GrammarListeningSystemIntegration"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_mastery_review_loop.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_mastery_review_loop_validation.json"

RECEPTIVE_DIMENSIONS = {
    "recognition",
    "meaning",
    "contrast",
    "receptive_checkpoint",
}
PRODUCTIVE_DIMENSIONS = {
    "controlled_production",
    "contextual_production",
    "productive_checkpoint",
}
REVIEW_STAGES = (
    {"stage": "IMMEDIATE_RETRY", "due_after_attempt_steps": 1},
    {"stage": "SHORT_REVIEW", "due_after_attempt_steps": 3},
    {"stage": "SPACED_REVIEW", "due_after_attempt_steps": 7},
    {"stage": "RETENTION_CHECK", "due_after_attempt_steps": 14},
)
MASTERY_POLICY = {
    "policy_id": "a1_grammar_reading_writing_mastery.v1",
    "minimum_receptive_score": 0.75,
    "minimum_productive_score": 0.75,
    "reading_assessment_pass_required": True,
    "writing_assessment_pass_required": True,
    "unresolved_latest_failure_allowed": False,
    "retention_check_required_for_persistent_mastery": True,
    "production_runtime_promotion": False,
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def activity_index(closure: dict[str, Any]) -> dict[str, dict[str, Any]]:
    activities = closure.get("reading_activity_bank", []) + closure.get("writing_activity_bank", [])
    index = {activity.get("activity_id"): activity for activity in activities if activity.get("activity_id")}
    if len(activities) != 192 or len(index) != 192:
        raise ValueError("closure_activity_index_not_192")
    return index


def build_error_taxonomy(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    taxonomy: dict[str, dict[str, Any]] = {}
    for unit in candidate.get("learning_units", []):
        grammar_id = unit["grammar_unit_id"]
        for error in unit.get("common_error_tags", []):
            tag = error.get("tag")
            if not tag:
                continue
            entry = taxonomy.setdefault(
                tag,
                {
                    "error_tag": tag,
                    "grammar_unit_ids": [],
                    "diagnoses": [],
                    "severity": "REVIEW_REQUIRED",
                    "review_route": "TARGETED_GRAMMAR_REVIEW",
                },
            )
            entry["grammar_unit_ids"].append(grammar_id)
            diagnosis = error.get("diagnosis")
            if diagnosis:
                entry["diagnoses"].append(diagnosis)
    taxonomy["ERR_RESPONSE_MISSING"] = {
        "error_tag": "ERR_RESPONSE_MISSING",
        "grammar_unit_ids": [],
        "diagnoses": ["No usable learner response was supplied."],
        "severity": "RETRY_REQUIRED",
        "review_route": "IMMEDIATE_RETRY",
    }
    taxonomy["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"] = {
        "error_tag": "ERR_UNCLASSIFIED_GRAMMAR_FAILURE",
        "grammar_unit_ids": [],
        "diagnoses": ["The response failed the target evidence check without a more specific classified error."],
        "severity": "MANUAL_REVIEW_REQUIRED",
        "review_route": "MANUAL_OR_RULE_REVIEW",
    }
    for entry in taxonomy.values():
        entry["grammar_unit_ids"] = _unique(entry["grammar_unit_ids"])
        entry["diagnoses"] = _unique(entry["diagnoses"])
    return dict(sorted(taxonomy.items()))


def build_attempt_event(
    activity: dict[str, Any],
    *,
    learner_ref: str,
    attempt_sequence: int,
    passed: bool,
    error_tags: Iterable[str] = (),
    observed_response: str = "",
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    tags = _unique(error_tags)
    return {
        "event_id": f"{learner_ref}:{activity['activity_id']}:{attempt_sequence}",
        "event_schema_version": "a1_grammar_attempt_event.v1",
        "learner_ref": learner_ref,
        "attempt_sequence": attempt_sequence,
        "activity_id": activity["activity_id"],
        "activity_role": activity["activity_role"],
        "grammar_unit_id": activity["grammar_unit_id"],
        "canonical_egp_row_ids": list(activity["canonical_egp_row_ids"]),
        "skill": activity["skill"],
        "evidence_dimension": activity["evidence_dimension"],
        "outcome": "PASS" if passed else "FAIL",
        "passed": passed,
        "error_tags": tags,
        "observed_response": observed_response,
        "synthetic_fixture": synthetic_fixture,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }


def validate_attempt_event(
    event: dict[str, Any],
    activities: dict[str, dict[str, Any]],
    taxonomy: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    activity_id = event.get("activity_id")
    activity = activities.get(activity_id)
    if not activity:
        return [f"unknown_activity_id:{activity_id}"]
    expected = {
        "activity_role": activity["activity_role"],
        "grammar_unit_id": activity["grammar_unit_id"],
        "canonical_egp_row_ids": activity["canonical_egp_row_ids"],
        "skill": activity["skill"],
        "evidence_dimension": activity["evidence_dimension"],
    }
    for field, value in expected.items():
        if event.get(field) != value:
            errors.append(f"attempt_identity_mismatch:{activity_id}:{field}")
    if not isinstance(event.get("learner_ref"), str) or not event["learner_ref"]:
        errors.append(f"learner_ref_missing:{activity_id}")
    if not isinstance(event.get("attempt_sequence"), int) or event["attempt_sequence"] < 1:
        errors.append(f"attempt_sequence_invalid:{activity_id}")
    passed = event.get("passed")
    if passed not in {True, False}:
        errors.append(f"attempt_outcome_invalid:{activity_id}")
    if event.get("outcome") != ("PASS" if passed is True else "FAIL"):
        errors.append(f"attempt_outcome_mismatch:{activity_id}")
    tags = event.get("error_tags", [])
    if not isinstance(tags, list) or len(tags) != len(set(tags)):
        errors.append(f"attempt_error_tags_invalid:{activity_id}")
        tags = []
    unknown = sorted(set(tags) - set(taxonomy))
    if unknown:
        errors.append(f"unknown_error_tags:{activity_id}:{','.join(unknown)}")
    if passed is True and tags:
        errors.append(f"passed_attempt_has_error_tags:{activity_id}")
    if passed is False and not tags:
        errors.append(f"failed_attempt_missing_error_tags:{activity_id}")
    if event.get("persistent_learner_state_write") is not False:
        errors.append(f"unsafe_persistent_write_claim:{activity_id}")
    if event.get("production_runtime_event") is not False:
        errors.append(f"unsafe_runtime_event_claim:{activity_id}")
    return errors


def _latest_attempts(attempts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in attempts:
        activity_id = event["activity_id"]
        prior = latest.get(activity_id)
        if prior is None or event["attempt_sequence"] > prior["attempt_sequence"]:
            latest[activity_id] = event
    return latest


def project_mastery(closure: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    latest = _latest_attempts(attempts)
    by_row = closure["by_egp_row_id"]
    row_results: dict[str, dict[str, Any]] = {}
    review_queue: list[dict[str, Any]] = []
    for row_id, row in by_row.items():
        activity_ids = set(row["reading_activity_ids"] + row["writing_activity_ids"])
        events = [latest[activity_id] for activity_id in sorted(activity_ids) if activity_id in latest]
        receptive = [event for event in events if event["skill"] == "reading"]
        productive = [event for event in events if event["skill"] == "writing"]
        receptive_score = sum(event["passed"] for event in receptive) / len(row["reading_activity_ids"])
        productive_score = sum(event["passed"] for event in productive) / len(row["writing_activity_ids"])
        reading_assessment_pass = all(
            latest.get(activity_id, {}).get("passed") is True
            for activity_id in row["reading_assessment_ids"]
        )
        writing_assessment_pass = all(
            latest.get(activity_id, {}).get("passed") is True
            for activity_id in row["writing_assessment_ids"]
        )
        unresolved = [event for event in events if event["passed"] is False]
        mastered = (
            receptive_score >= MASTERY_POLICY["minimum_receptive_score"]
            and productive_score >= MASTERY_POLICY["minimum_productive_score"]
            and reading_assessment_pass
            and writing_assessment_pass
            and not unresolved
        )
        error_tags = _unique(tag for event in unresolved for tag in event["error_tags"])
        status = "SIMULATED_MASTERY_READY" if mastered else "NEEDS_REVIEW"
        row_results[row_id] = {
            "egp_row_id": row_id,
            "grammar_unit_ids": list(row["grammar_unit_ids"]),
            "attempted_activity_count": len(events),
            "required_activity_count": len(activity_ids),
            "receptive_score": round(receptive_score, 4),
            "productive_score": round(productive_score, 4),
            "reading_assessment_pass": reading_assessment_pass,
            "writing_assessment_pass": writing_assessment_pass,
            "unresolved_failure_count": len(unresolved),
            "error_tags": error_tags,
            "projection_status": status,
            "persistent_mastery_status": "NOT_ESTABLISHED",
        }
        if not mastered:
            priority = "HIGH" if not reading_assessment_pass or not writing_assessment_pass else "MEDIUM"
            review_queue.append({
                "queue_id": f"REVIEW:{row_id}",
                "egp_row_id": row_id,
                "grammar_unit_ids": list(row["grammar_unit_ids"]),
                "priority": priority,
                "error_tags": error_tags or ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"],
                "review_stages": [dict(stage) for stage in REVIEW_STAGES],
                "persistent_queue_write": False,
            })
    mastered_count = sum(result["projection_status"] == "SIMULATED_MASTERY_READY" for result in row_results.values())
    return {
        "projection_mode": "PURE_OFFLINE_SIMULATION",
        "policy_id": MASTERY_POLICY["policy_id"],
        "attempt_event_count": len(attempts),
        "latest_activity_attempt_count": len(latest),
        "row_count": len(row_results),
        "simulated_mastery_ready_row_count": mastered_count,
        "needs_review_row_count": len(row_results) - mastered_count,
        "row_results": row_results,
        "review_queue": review_queue,
        "persistent_learner_state_write": False,
        "production_runtime_projection": False,
    }


def build_synthetic_attempts(
    closure: dict[str, Any],
    *,
    failure_activity_id: str | None = None,
    failure_error_tag: str = "ERR_UNCLASSIFIED_GRAMMAR_FAILURE",
) -> list[dict[str, Any]]:
    index = activity_index(closure)
    attempts = []
    for activity_id, activity in sorted(index.items()):
        failed = activity_id == failure_activity_id
        attempts.append(
            build_attempt_event(
                activity,
                learner_ref="SYNTHETIC_LEARNER_A1",
                attempt_sequence=1,
                passed=not failed,
                error_tags=[failure_error_tag] if failed else [],
                observed_response="synthetic failure" if failed else "synthetic accepted response",
                synthetic_fixture=True,
            )
        )
    return attempts


def build_artifact(candidate: dict[str, Any], closure: dict[str, Any]) -> dict[str, Any]:
    taxonomy = build_error_taxonomy(candidate)
    activities = activity_index(closure)
    pass_attempts = build_synthetic_attempts(closure)
    pass_projection = project_mastery(closure, pass_attempts)
    failure_activity = next(
        activity_id
        for activity_id, activity in sorted(activities.items())
        if activity["skill"] == "writing" and activity["activity_role"] == "assessment"
    )
    failure_grammar_id = activities[failure_activity]["grammar_unit_id"]
    failure_tag = candidate["learning_units"][
        next(index for index, unit in enumerate(candidate["learning_units"]) if unit["grammar_unit_id"] == failure_grammar_id)
    ]["common_error_tags"][0]["tag"]
    failure_attempts = build_synthetic_attempts(
        closure,
        failure_activity_id=failure_activity,
        failure_error_tag=failure_tag,
    )
    failure_projection = project_mastery(closure, failure_attempts)
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_mastery_review_loop",
        "artifact_type": "a1_a1plus_offline_attempt_mastery_review_projection",
        "schema_version": "a1_grammar_mastery_review_loop.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "source_artifact_ids": [candidate["artifact_id"], closure["artifact_id"]],
        "mastery_policy": deepcopy(MASTERY_POLICY),
        "review_policy": {
            "review_stages": [dict(stage) for stage in REVIEW_STAGES],
            "scheduling_mode": "ATTEMPT_STEP_OFFSETS_NOT_WALL_CLOCK",
            "retention_check_required": True,
            "persistent_queue_write": False,
        },
        "error_taxonomy": taxonomy,
        "simulation_summary": {
            "activity_count": len(activities),
            "pass_scenario_attempt_count": len(pass_attempts),
            "pass_scenario_mastery_ready_row_count": pass_projection["simulated_mastery_ready_row_count"],
            "pass_scenario_review_queue_count": len(pass_projection["review_queue"]),
            "failure_scenario_activity_id": failure_activity,
            "failure_scenario_error_tag": failure_tag,
            "failure_scenario_needs_review_row_count": failure_projection["needs_review_row_count"],
            "failure_scenario_review_queue_count": len(failure_projection["review_queue"]),
        },
        "pass_scenario_projection": pass_projection,
        "failure_scenario_projection": failure_projection,
        "actual_learner_state_summary": {
            "actual_attempt_event_count": 0,
            "actual_mastery_measured_row_count": 0,
            "actual_review_queue_count": 0,
            "persistent_learner_state_write": False,
        },
        "claim_boundaries": {
            "attempt_event_contract_implemented": True,
            "error_taxonomy_implemented": True,
            "mastery_projection_implemented": True,
            "review_queue_projection_implemented": True,
            "retention_policy_implemented": True,
            "actual_learner_attempt_collection_complete": False,
            "actual_learner_mastery_complete": False,
            "production_persistence_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(
    artifact: dict[str, Any],
    candidate: dict[str, Any],
    closure: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    activities = activity_index(closure)
    taxonomy = artifact.get("error_taxonomy", {})
    required_tags = {
        error["tag"]
        for unit in candidate.get("learning_units", [])
        for error in unit.get("common_error_tags", [])
        if error.get("tag")
    }
    if not required_tags.issubset(taxonomy):
        errors.append("error_taxonomy_missing_candidate_tags")
    if not {"ERR_RESPONSE_MISSING", "ERR_UNCLASSIFIED_GRAMMAR_FAILURE"}.issubset(taxonomy):
        errors.append("error_taxonomy_missing_generic_tags")

    pass_projection = artifact.get("pass_scenario_projection", {})
    failure_projection = artifact.get("failure_scenario_projection", {})
    if pass_projection.get("attempt_event_count") != 192:
        errors.append("pass_scenario_attempt_count_mismatch")
    if pass_projection.get("simulated_mastery_ready_row_count") != 109:
        errors.append("pass_scenario_not_109_mastery_ready")
    if pass_projection.get("needs_review_row_count") != 0 or pass_projection.get("review_queue"):
        errors.append("pass_scenario_unexpected_review_queue")
    if failure_projection.get("needs_review_row_count", 0) < 1:
        errors.append("failure_scenario_did_not_trigger_review")
    if len(failure_projection.get("review_queue", [])) != failure_projection.get("needs_review_row_count"):
        errors.append("failure_review_queue_count_mismatch")
    for queue in failure_projection.get("review_queue", []):
        if queue.get("review_stages") != [dict(stage) for stage in REVIEW_STAGES]:
            errors.append(f"review_stage_policy_mismatch:{queue.get('queue_id')}")
        if queue.get("persistent_queue_write") is not False:
            errors.append(f"unsafe_review_queue_write:{queue.get('queue_id')}")

    for projection_name, projection in (("pass", pass_projection), ("failure", failure_projection)):
        if projection.get("row_count") != 109:
            errors.append(f"{projection_name}_projection_row_count_mismatch")
        if projection.get("persistent_learner_state_write") is not False:
            errors.append(f"{projection_name}_projection_persistent_write")
        if projection.get("production_runtime_projection") is not False:
            errors.append(f"{projection_name}_projection_runtime_claim")
        for row_id, row in projection.get("row_results", {}).items():
            if row.get("persistent_mastery_status") != "NOT_ESTABLISHED":
                errors.append(f"false_persistent_mastery_claim:{projection_name}:{row_id}")

    summary = artifact.get("actual_learner_state_summary", {})
    if summary != {
        "actual_attempt_event_count": 0,
        "actual_mastery_measured_row_count": 0,
        "actual_review_queue_count": 0,
        "persistent_learner_state_write": False,
    }:
        errors.append("actual_learner_state_summary_mismatch")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("actual_learner_attempt_collection_complete") is not False:
        errors.append("false_actual_attempt_collection_claim")
    if boundaries.get("actual_learner_mastery_complete") is not False:
        errors.append("false_actual_mastery_claim")
    if boundaries.get("production_persistence_complete") is not False:
        errors.append("false_production_persistence_claim")
    for field in (
        "no_a2_a2plus_expansion",
        "no_persistent_learner_state_write",
        "no_external_nlp_dependency",
        "no_restricted_source_payload_copy",
    ):
        if boundaries.get(field) is not True:
            errors.append(f"scope_boundary_missing:{field}")

    status = "PASS" if not errors else "FAIL"
    simulation = artifact.get("simulation_summary", {})
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_mastery_review_loop_validation",
        "validation_status": status,
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "activity_contract_count": len(activities),
            "error_taxonomy_tag_count": len(taxonomy),
            "simulated_attempt_event_count": simulation.get("pass_scenario_attempt_count", 0),
            "simulated_mastery_ready_row_count": simulation.get("pass_scenario_mastery_ready_row_count", 0),
            "failure_scenario_needs_review_row_count": simulation.get("failure_scenario_needs_review_row_count", 0),
            "actual_attempt_event_count": 0,
            "actual_mastery_measured_row_count": 0,
        },
        "gate_checks": {
            "activity_contracts_192": len(activities) == 192,
            "candidate_error_tags_covered": required_tags.issubset(taxonomy),
            "pass_projection_109_rows": pass_projection.get("simulated_mastery_ready_row_count") == 109,
            "failure_projection_routes_review": failure_projection.get("needs_review_row_count", 0) >= 1,
            "review_policy_has_four_stages": len(REVIEW_STAGES) == 4,
            "actual_mastery_still_zero": summary.get("actual_mastery_measured_row_count") == 0,
            "no_persistent_learner_write": boundaries.get("no_persistent_learner_state_write") is True,
            "no_a2plus_scope": boundaries.get("no_a2_a2plus_expansion") is True,
        },
        "errors": errors,
        "warnings": [
            "Mastery and review results are pure offline simulations until real learner attempts are supplied.",
            "No persistent learner profile, queue, or production runtime write is performed.",
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, candidate_report = build_candidate_source()
    closure, closure_report = build_closure_source()
    if candidate_report.get("validation_status") != "PASS":
        raise RuntimeError("candidate_source_validation_failed")
    if closure_report.get("validation_status") != "PASS":
        raise RuntimeError("closure_source_validation_failed")
    artifact = build_artifact(candidate, closure)
    report = validate_artifact(artifact, candidate, closure)
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
