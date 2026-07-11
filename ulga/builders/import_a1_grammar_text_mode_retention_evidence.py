#!/usr/bin/env python3
"""Validate real delayed retention evidence for A1/A1+ text-mode mastery candidates.

M105S consumes the local M105P normalized baseline, the local M105Q projection,
and a second-session response payload. It only accepts assessment responses for
units currently routed to RETENTION_CHECK_REQUIRED. The intake is local-only,
requires a distinct later session for the same pseudonymous learner, and never
writes persistent learner state or claims final mastery.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    INTAKE_PATH,
    load_json,
    normalize_and_validate,
    write_json,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    IMPORT_SCHEMA_VERSION as REAL_ATTEMPT_IMPORT_SCHEMA_VERSION,
    _private_path_error,
    build_evidence_payload,
)

TASK_ID = "R7-M105S_A1A1PlusTextModeRetentionEvidenceIntake"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
RETENTION_SCHEMA_VERSION = "a1_grammar_text_mode_retention_response_import.v1"
NEXT_FINAL_MASTERY_TASK = "R7-M105T_A1A1PlusTextModeFinalMasteryProjection"
NEXT_REVIEW_TASK = "R7-M105R_A1A1PlusTextModeReviewSessionPackageIntegration"

DEFAULT_BASELINE_PATH = REPO_ROOT / ".local/a1_private_pilot_evidence_normalized.json"
DEFAULT_PROJECTION_PATH = REPO_ROOT / ".local/a1_private_pilot_projection.json"
DEFAULT_RESPONSES_PATH = REPO_ROOT / ".local/a1_private_pilot_retention_responses.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / ".local/a1_private_pilot_retention_evidence.json"
DEFAULT_REPORT_PATH = REPO_ROOT / ".local/a1_private_pilot_retention_validation.json"

RETENTION_POLICY = {
    "policy_id": "a1_grammar_text_mode_retention_evidence.v1",
    "minimum_delay_hours": 24,
    "recommended_delay_hours": 168,
    "assessment_only": True,
    "reading_assessment_pass_required": True,
    "writing_assessment_pass_required": True,
    "same_pseudonymous_learner_required": True,
    "distinct_session_required": True,
    "final_mastery_claim_allowed_in_this_task": False,
    "persistent_learner_state_write": False,
}

ALLOWED_SOURCE_FIELDS = {
    "item_id",
    "response_text",
    "submitted_at",
    "score",
    "passed",
    "error_tags",
    "evaluator_type",
    "evaluator_ref",
    "evidence_ref",
}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_strings(values: Iterable[Any]) -> list[str]:
    return sorted(
        {
            value.strip()
            for value in values
            if isinstance(value, str) and value.strip()
        }
    )


def _parse_timestamp(value: Any, *, field: str, errors: list[str]) -> datetime | None:
    if not _nonempty_string(value):
        errors.append(f"retention_timestamp_missing:{field}")
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        errors.append(f"retention_timestamp_invalid:{field}")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"retention_timestamp_timezone_required:{field}")
        return None
    return parsed


def _validated_package() -> dict[str, Any]:
    package, report = build_package_source()
    if report.get("validation_status") != "PASS":
        raise RuntimeError("retention_package_validation_failed")
    if len(package.get("learning_units", [])) != 24:
        raise RuntimeError("retention_package_unit_count_not_24")
    if len(package.get("item_bank", [])) != 192:
        raise RuntimeError("retention_package_item_count_not_192")
    return package


def _item_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    items = package.get("item_bank", [])
    index = {
        item.get("item_id"): dict(item)
        for item in items
        if isinstance(item, Mapping) and _nonempty_string(item.get("item_id"))
    }
    if len(items) != 192 or len(index) != 192:
        raise ValueError("retention_item_index_not_192")
    return index


def _unit_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    units = package.get("learning_units", [])
    index = {
        unit.get("grammar_unit_id"): dict(unit)
        for unit in units
        if isinstance(unit, Mapping)
        and _nonempty_string(unit.get("grammar_unit_id"))
    }
    if len(units) != 24 or len(index) != 24:
        raise ValueError("retention_unit_index_not_24")
    return index


def _candidate_unit_ids(projection: Mapping[str, Any]) -> list[str]:
    routes = projection.get("routing", {}).get("retention_check", [])
    return _unique_strings(
        route.get("grammar_unit_id")
        for route in routes
        if isinstance(route, Mapping)
        and route.get("route") == "RETENTION_CHECK_REQUIRED"
    )


def _assessment_ids_by_unit(
    package: Mapping[str, Any],
    selected_unit_ids: Iterable[str],
) -> dict[str, list[str]]:
    unit_index = _unit_index(package)
    item_index = _item_index(package)
    result: dict[str, list[str]] = {}
    for grammar_id in selected_unit_ids:
        unit = unit_index[grammar_id]
        assessment_ids = _unique_strings(
            unit.get("delivery_plan", {}).get("assessment_item_ids", [])
        )
        if len(assessment_ids) != 2:
            raise ValueError(
                f"retention_assessment_item_count_not_2:{grammar_id}"
            )
        skills = sorted(item_index[item_id].get("skill") for item_id in assessment_ids)
        if skills != ["reading", "writing"]:
            raise ValueError(
                f"retention_assessment_skill_pair_invalid:{grammar_id}"
            )
        result[grammar_id] = assessment_ids
    return result


def _baseline_sequence_by_item(
    baseline: Mapping[str, Any],
) -> dict[str, int]:
    latest: dict[str, int] = {}
    for attempt in baseline.get("accepted_attempts", []):
        if not isinstance(attempt, Mapping):
            continue
        item_id = attempt.get("item_id")
        sequence = attempt.get("attempt_sequence")
        if _nonempty_string(item_id) and isinstance(sequence, int):
            latest[item_id] = max(sequence, latest.get(item_id, 0))
    return latest


def _validate_source_shape(source: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if source.get("retention_schema_version") != RETENTION_SCHEMA_VERSION:
        errors.append("retention_schema_version_mismatch")
    if not _nonempty_string(source.get("baseline_session_id")):
        errors.append("retention_baseline_session_id_missing")
    selected = source.get("grammar_unit_ids")
    if not isinstance(selected, list) or not selected:
        errors.append("retention_grammar_unit_ids_required")
    elif len(_unique_strings(selected)) != len(selected):
        errors.append("retention_grammar_unit_ids_duplicate_or_invalid")
    session = source.get("session")
    if not isinstance(session, Mapping):
        errors.append("retention_session_not_object")
    else:
        for field in (
            "session_id",
            "learner_ref",
            "operator_ref",
            "started_at",
            "completed_at",
            "evidence_source_ref",
        ):
            if not _nonempty_string(session.get(field)):
                errors.append(f"retention_session_field_missing:{field}")
        learner_ref = session.get("learner_ref")
        if isinstance(learner_ref, str) and "@" in learner_ref:
            errors.append("retention_learner_ref_must_be_pseudonymous_not_email")
    responses = source.get("responses")
    if not isinstance(responses, list) or not responses:
        errors.append("retention_responses_required")
    else:
        for index, record in enumerate(responses):
            prefix = f"retention_response[{index}]"
            if not isinstance(record, Mapping):
                errors.append(f"{prefix}:not_object")
                continue
            extra = sorted(set(record) - ALLOWED_SOURCE_FIELDS)
            if extra:
                errors.append(f"{prefix}:unsupported_fields:{','.join(extra)}")
            if not _nonempty_string(record.get("item_id")):
                errors.append(f"{prefix}:item_id_missing")
            if not isinstance(record.get("response_text"), str):
                errors.append(f"{prefix}:response_text_not_string")
            if not _nonempty_string(record.get("submitted_at")):
                errors.append(f"{prefix}:submitted_at_missing")
    return errors


def build_retention_artifact(
    source: Mapping[str, Any],
    package: Mapping[str, Any],
    baseline: Mapping[str, Any],
    projection: Mapping[str, Any],
    template: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors = _validate_source_shape(source)
    warnings: list[str] = []
    item_index = _item_index(package)
    unit_index = _unit_index(package)

    baseline_session = baseline.get("session", {})
    source_session = source.get("session", {})
    baseline_session_id = baseline_session.get("session_id")
    source_baseline_session_id = source.get("baseline_session_id")
    if source_baseline_session_id != baseline_session_id:
        errors.append("retention_baseline_session_id_mismatch")
    if source_session.get("session_id") == baseline_session_id:
        errors.append("retention_session_must_be_distinct")
    if source_session.get("learner_ref") != baseline_session.get("learner_ref"):
        errors.append("retention_learner_ref_mismatch")

    baseline_completed = _parse_timestamp(
        baseline_session.get("completed_at"),
        field="baseline.completed_at",
        errors=errors,
    )
    retention_started = _parse_timestamp(
        source_session.get("started_at"),
        field="session.started_at",
        errors=errors,
    )
    retention_completed = _parse_timestamp(
        source_session.get("completed_at"),
        field="session.completed_at",
        errors=errors,
    )
    if retention_started is not None and retention_completed is not None:
        if retention_completed < retention_started:
            errors.append("retention_session_completed_before_started")
    eligible_at: datetime | None = None
    elapsed_hours: float | None = None
    if baseline_completed is not None:
        eligible_at = baseline_completed + timedelta(
            hours=RETENTION_POLICY["minimum_delay_hours"]
        )
    if baseline_completed is not None and retention_started is not None:
        elapsed_hours = round(
            (retention_started - baseline_completed).total_seconds() / 3600,
            4,
        )
        if retention_started < eligible_at:
            errors.append(
                "retention_minimum_delay_not_met:"
                f"required_hours={RETENTION_POLICY['minimum_delay_hours']}:"
                f"actual_hours={elapsed_hours}"
            )
        elif elapsed_hours < RETENTION_POLICY["recommended_delay_hours"]:
            warnings.append(
                "Retention evidence meets the minimum delay but is earlier than "
                "the recommended seven-day interval."
            )

    candidate_unit_ids = _candidate_unit_ids(projection)
    selected_unit_ids = _unique_strings(source.get("grammar_unit_ids", []))
    unknown_units = sorted(set(selected_unit_ids) - set(unit_index))
    if unknown_units:
        errors.append("retention_unknown_unit_ids:" + ",".join(unknown_units))
    non_candidate_units = sorted(set(selected_unit_ids) - set(candidate_unit_ids))
    if non_candidate_units:
        errors.append(
            "retention_units_not_current_candidates:"
            + ",".join(non_candidate_units)
        )

    assessment_ids_by_unit: dict[str, list[str]] = {}
    if not unknown_units:
        assessment_ids_by_unit = _assessment_ids_by_unit(package, selected_unit_ids)
    required_item_ids = {
        item_id
        for item_ids in assessment_ids_by_unit.values()
        for item_id in item_ids
    }

    raw_responses = source.get("responses", [])
    response_item_ids = [
        record.get("item_id")
        for record in raw_responses
        if isinstance(record, Mapping)
    ]
    if len(response_item_ids) != len(set(response_item_ids)):
        errors.append("retention_duplicate_response_item_id")
    missing_item_ids = sorted(required_item_ids - set(response_item_ids))
    extra_item_ids = sorted(set(response_item_ids) - required_item_ids)
    if missing_item_ids:
        errors.append("retention_assessment_items_missing:" + ",".join(missing_item_ids))
    if extra_item_ids:
        errors.append("retention_non_assessment_or_unselected_items:" + ",".join(extra_item_ids))

    for index, record in enumerate(raw_responses):
        if not isinstance(record, Mapping):
            continue
        submitted = _parse_timestamp(
            record.get("submitted_at"),
            field=f"responses[{index}].submitted_at",
            errors=errors,
        )
        if submitted is not None and retention_started is not None:
            if submitted < retention_started:
                errors.append(f"retention_response_before_session:{index}")
        if submitted is not None and retention_completed is not None:
            if submitted > retention_completed:
                errors.append(f"retention_response_after_session:{index}")

    baseline_sequence = _baseline_sequence_by_item(baseline)
    prepared_responses: list[dict[str, Any]] = []
    for record in raw_responses:
        if not isinstance(record, Mapping):
            continue
        prepared = deepcopy(dict(record))
        item_id = prepared.get("item_id")
        prepared["attempt_sequence"] = baseline_sequence.get(item_id, 0) + 1
        prepared_responses.append(prepared)

    normalized_retention: dict[str, Any] = {}
    generated_attempt_report: dict[str, Any] = {}
    if not errors:
        p02_source = {
            "import_schema_version": REAL_ATTEMPT_IMPORT_SCHEMA_VERSION,
            "session": deepcopy(dict(source_session)),
            "responses": prepared_responses,
        }
        evidence_payload, generated_attempt_report = build_evidence_payload(
            p02_source,
            package,
            template,
        )
        if generated_attempt_report.get("validation_status") != "PASS":
            errors.append("retention_generated_attempt_contract_failed")
            errors.extend(
                f"p02:{error}"
                for error in generated_attempt_report.get("errors", [])
            )
        else:
            normalized_retention, intake_report = normalize_and_validate(
                evidence_payload,
                package,
            )
            if intake_report.get("validation_status") != "PASS":
                errors.append("retention_m105p_normalization_failed")
                errors.extend(
                    f"m105p:{error}"
                    for error in intake_report.get("errors", [])
                )

    accepted_attempts = normalized_retention.get("accepted_attempts", [])
    attempt_by_item = {
        attempt.get("item_id"): attempt
        for attempt in accepted_attempts
        if isinstance(attempt, Mapping)
    }
    by_unit: dict[str, dict[str, Any]] = {}
    for grammar_id in selected_unit_ids:
        assessment_ids = assessment_ids_by_unit.get(grammar_id, [])
        reading_ids = [
            item_id
            for item_id in assessment_ids
            if item_index[item_id].get("skill") == "reading"
        ]
        writing_ids = [
            item_id
            for item_id in assessment_ids
            if item_index[item_id].get("skill") == "writing"
        ]
        reading_pass = bool(reading_ids) and all(
            attempt_by_item.get(item_id, {}).get("passed") is True
            for item_id in reading_ids
        )
        writing_pass = bool(writing_ids) and all(
            attempt_by_item.get(item_id, {}).get("passed") is True
            for item_id in writing_ids
        )
        failed_item_ids = sorted(
            item_id
            for item_id in assessment_ids
            if attempt_by_item.get(item_id, {}).get("passed") is False
        )
        complete = bool(assessment_ids) and all(
            item_id in attempt_by_item for item_id in assessment_ids
        )
        confirmed = complete and reading_pass and writing_pass
        by_unit[grammar_id] = {
            "grammar_unit_id": grammar_id,
            "canonical_egp_row_ids": list(
                unit_index.get(grammar_id, {}).get("canonical_egp_row_ids", [])
            ),
            "required_assessment_item_ids": assessment_ids,
            "accepted_retention_attempt_count": sum(
                item_id in attempt_by_item for item_id in assessment_ids
            ),
            "reading_assessment_pass": reading_pass,
            "writing_assessment_pass": writing_pass,
            "failed_assessment_item_ids": failed_item_ids,
            "retention_status": (
                "RETENTION_CONFIRMED_PENDING_FINAL_MASTERY_PROJECTION"
                if confirmed
                else "RETENTION_FAILED_REVIEW_REQUIRED"
            ),
            "retention_confirmed": confirmed,
            "final_mastery_status": "NOT_CLAIMED",
            "persistent_learner_state_write": False,
        }

    contract_status = "PASS" if not errors else "FAIL"
    confirmed_unit_ids = sorted(
        grammar_id
        for grammar_id, result in by_unit.items()
        if result.get("retention_confirmed") is True
    )
    failed_unit_ids = sorted(set(selected_unit_ids) - set(confirmed_unit_ids))
    if contract_status == "PASS" and failed_unit_ids:
        retention_status = "RETENTION_FAILED_REVIEW_REQUIRED"
        next_task = NEXT_REVIEW_TASK
        stop_reason = "NONE"
    elif contract_status == "PASS":
        retention_status = "RETENTION_CONFIRMED_PENDING_FINAL_MASTERY_PROJECTION"
        next_task = NEXT_FINAL_MASTERY_TASK
        stop_reason = "NONE"
    else:
        retention_status = "REJECTED"
        next_task = None
        stop_reason = "VALIDATION_FAILURE"

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_retention_evidence_normalized",
        "artifact_type": "validated_delayed_text_mode_retention_assessment_evidence",
        "schema_version": "a1_grammar_text_mode_retention_evidence_normalized.v1",
        "source_refs": {
            "package_artifact_id": package.get("artifact_id"),
            "baseline_evidence_artifact_id": baseline.get("artifact_id"),
            "baseline_projection_artifact_id": projection.get("artifact_id"),
            "baseline_session_id": baseline_session_id,
        },
        "retention_policy": deepcopy(RETENTION_POLICY),
        "session": deepcopy(dict(source_session)) if isinstance(source_session, Mapping) else {},
        "timing": {
            "baseline_completed_at": baseline_session.get("completed_at"),
            "retention_eligible_at": eligible_at.isoformat() if eligible_at else None,
            "retention_started_at": source_session.get("started_at"),
            "elapsed_hours": elapsed_hours,
        },
        "retention_status": retention_status,
        "coverage_summary": {
            "candidate_unit_count": len(candidate_unit_ids),
            "selected_unit_count": len(selected_unit_ids),
            "required_assessment_item_count": len(required_item_ids),
            "accepted_retention_attempt_count": len(accepted_attempts),
            "confirmed_unit_count": len(confirmed_unit_ids),
            "failed_unit_count": len(failed_unit_ids) if contract_status == "PASS" else 0,
            "final_mastered_unit_count": 0,
            "final_mastered_row_count": 0,
        },
        "accepted_retention_attempts": (
            deepcopy(accepted_attempts) if contract_status == "PASS" else []
        ),
        "by_grammar_unit_id": by_unit if contract_status == "PASS" else {},
        "release_gates": {
            "retention_intake_contract_gate": contract_status,
            "baseline_mastery_candidate_gate": (
                "PASS" if candidate_unit_ids else "BLOCKED_NO_RETENTION_CANDIDATE"
            ),
            "minimum_delay_gate": "PASS" if contract_status == "PASS" else "FAIL",
            "assessment_coverage_gate": "PASS" if contract_status == "PASS" else "FAIL",
            "retention_outcome_gate": retention_status,
            "final_mastery_projection_gate": (
                "PASS_READY"
                if retention_status
                == "RETENTION_CONFIRMED_PENDING_FINAL_MASTERY_PROJECTION"
                else "BLOCKED_REVIEW_REQUIRED"
                if retention_status == "RETENTION_FAILED_REVIEW_REQUIRED"
                else "BLOCKED_INVALID_EVIDENCE"
            ),
            "final_mastery_gate": "BLOCKED_SEPARATE_PROJECTION_REQUIRED",
            "audio_scope_gate": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
            "production_runtime_gate": "BLOCKED_NOT_APPROVED",
        },
        "claim_boundaries": {
            "real_retention_evidence_present": bool(accepted_attempts)
            and contract_status == "PASS",
            "retention_intake_pipeline_complete": contract_status == "PASS",
            "retention_confirmed": bool(confirmed_unit_ids)
            and not failed_unit_ids
            and contract_status == "PASS",
            "actual_final_mastery_measured": False,
            "final_mastery_claimed": False,
            "persistent_learner_state_write": False,
            "production_runtime_complete": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "no_a2_a2plus_expansion": True,
        },
        "continuation_gate": {
            "stop_reason": stop_reason,
            "next_task": next_task,
        },
    }

    report = {
        "task_id": TASK_ID,
        "validation_status": contract_status,
        "retention_status": retention_status,
        "coverage_summary": artifact["coverage_summary"],
        "gate_checks": artifact["release_gates"],
        "errors": errors,
        "warnings": warnings,
        "stop_reason": stop_reason,
        "next_task": next_task,
        "validation_mode": "STATIC_RETENTION_INTAKE_CONTRACT_REVIEW_CI_NOT_VERIFIED",
    }
    return artifact, report


def run_retention_import(
    source: Mapping[str, Any],
    baseline: Mapping[str, Any],
    projection: Mapping[str, Any],
    package: Mapping[str, Any] | None = None,
    template: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    package = package or _validated_package()
    template = template or load_json(INTAKE_PATH)
    return build_retention_artifact(
        source,
        package,
        baseline,
        projection,
        template,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION_PATH)
    parser.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args(argv)

    path_errors = [
        error
        for path in (
            args.baseline,
            args.projection,
            args.responses,
            args.output,
            args.report,
        )
        if (error := _private_path_error(path)) is not None
    ]
    if path_errors:
        report = {
            "task_id": TASK_ID,
            "validation_status": "FAIL",
            "errors": path_errors,
            "stop_reason": "VALIDATION_FAILURE",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    missing = [
        str(path)
        for path in (args.baseline, args.projection, args.responses)
        if not path.exists()
    ]
    if missing:
        report = {
            "task_id": TASK_ID,
            "validation_status": "BLOCKED",
            "retention_status": "AWAITING_REAL_RETENTION_RESPONSES",
            "errors": ["retention_source_not_found:" + path for path in missing],
            "stop_reason": "RETENTION_EVIDENCE_REQUIRED",
            "next_task": TASK_ID,
        }
        write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    source = load_json(args.responses)
    baseline = load_json(args.baseline)
    projection = load_json(args.projection)
    artifact, report = run_retention_import(source, baseline, projection)
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("validation_status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
