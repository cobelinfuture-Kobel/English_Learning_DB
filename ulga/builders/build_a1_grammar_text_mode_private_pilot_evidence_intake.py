#!/usr/bin/env python3
"""Validate and normalize real A1/A1+ private-pilot text-mode evidence.

This intake is read-only with respect to learner state. It accepts evidence only
when every attempt can be traced to the approved M105O package and when the
payload explicitly declares that it is non-synthetic, non-production, and does
not write persistent learner state.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)

TASK_ID = "R7-M105P_A1A1PlusTextModePrivatePilotExecutionEvidenceIntake"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_RESUME_TASK = "R7-M105P02_A1A1PlusTextModePrivatePilotRealAttemptImport"
NEXT_SHORT_STEP = "R7-M105Q_A1A1PlusTextModeEvidenceProjectionAndReviewRouting"

INTAKE_PATH = (
    REPO_ROOT
    / "ulga/evidence/a1_grammar_text_mode_private_pilot_evidence_intake.json"
)
OUTPUT_PATH = (
    REPO_ROOT
    / "ulga/graph/a1_grammar_text_mode_private_pilot_evidence_normalized.json"
)
REPORT_PATH = (
    REPO_ROOT
    / "ulga/reports/a1_grammar_text_mode_private_pilot_evidence_intake_validation.json"
)

EXPECTED_INTAKE_SCHEMA = "a1_grammar_text_mode_private_pilot_evidence_intake.v1"
EXPECTED_PACKAGE_ID = "a1_grammar_text_mode_private_pilot_package"
EXPECTED_PACKAGE_SCHEMA = "a1_grammar_text_mode_private_pilot_package.v1"
ALLOWED_EVALUATORS = {"MANUAL", "RULE", "HYBRID"}
GENERIC_ERROR_TAGS = {
    "ERR_RESPONSE_MISSING",
    "ERR_UNCLASSIFIED_GRAMMAR_FAILURE",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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


def _validated_package() -> dict[str, Any]:
    package, report = build_package_source()
    if report.get("validation_status") != "PASS":
        raise RuntimeError("private_pilot_package_validation_failed")
    if package.get("artifact_id") != EXPECTED_PACKAGE_ID:
        raise RuntimeError("private_pilot_package_artifact_id_mismatch")
    if package.get("schema_version") != EXPECTED_PACKAGE_SCHEMA:
        raise RuntimeError("private_pilot_package_schema_version_mismatch")
    if package.get("release_gates", {}).get(
        "text_mode_private_pilot_package_gate"
    ) != "PASS_READY":
        raise RuntimeError("private_pilot_package_gate_not_ready")
    return package


def _item_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    items = package.get("item_bank", [])
    index = {
        item.get("item_id"): item
        for item in items
        if isinstance(item, Mapping) and _nonempty_string(item.get("item_id"))
    }
    if len(items) != 192 or len(index) != 192:
        raise ValueError("private_pilot_package_item_index_not_192")
    return index


def _unit_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    units = package.get("learning_units", [])
    index = {
        unit.get("grammar_unit_id"): unit
        for unit in units
        if isinstance(unit, Mapping)
        and _nonempty_string(unit.get("grammar_unit_id"))
    }
    if len(units) != 24 or len(index) != 24:
        raise ValueError("private_pilot_package_unit_index_not_24")
    return index


def _allowed_error_tags(package: Mapping[str, Any]) -> set[str]:
    tags = set(GENERIC_ERROR_TAGS)
    for unit in package.get("learning_units", []):
        content = unit.get("learning_content", {})
        for error in content.get("common_error_tags", []):
            tag = error.get("tag")
            if _nonempty_string(tag):
                tags.add(tag)
    return tags


def _derived_completion_claim(
    attempt_count: int,
    attempted_item_ids: set[str],
    package_item_count: int,
) -> str:
    if attempt_count == 0:
        return "NOT_STARTED"
    if len(attempted_item_ids) == package_item_count:
        return "COMPLETE"
    return "PARTIAL"


def _validate_session(
    session: Any,
    *,
    has_attempts: bool,
    derived_claim: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(session, Mapping):
        return ["session_not_object"]
    if session.get("delivery_environment") != "LOCAL_PRIVATE_TEXT_MODE":
        errors.append("delivery_environment_not_local_private_text_mode")
    if has_attempts:
        for field in (
            "session_id",
            "learner_ref",
            "operator_ref",
            "started_at",
            "evidence_source_ref",
        ):
            if not _nonempty_string(session.get(field)):
                errors.append(f"session_field_missing:{field}")
        learner_ref = session.get("learner_ref")
        if isinstance(learner_ref, str) and "@" in learner_ref:
            errors.append("learner_ref_must_be_pseudonymous_not_email")
        if derived_claim == "COMPLETE" and not _nonempty_string(
            session.get("completed_at")
        ):
            errors.append("complete_session_missing_completed_at")
    else:
        if session.get("session_id") is not None:
            errors.append("not_started_session_id_must_be_null")
        if session.get("learner_ref") is not None:
            errors.append("not_started_learner_ref_must_be_null")
        if session.get("started_at") is not None:
            errors.append("not_started_started_at_must_be_null")
        if session.get("completed_at") is not None:
            errors.append("not_started_completed_at_must_be_null")
        if session.get("evidence_source_ref") is not None:
            errors.append("not_started_evidence_source_ref_must_be_null")
    return errors


def normalize_and_validate(
    payload: Mapping[str, Any],
    package: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    item_index = _item_index(package)
    unit_index = _unit_index(package)
    allowed_error_tags = _allowed_error_tags(package)

    if payload.get("task_id") != TASK_ID:
        errors.append("intake_task_id_mismatch")
    if payload.get("intake_schema_version") != EXPECTED_INTAKE_SCHEMA:
        errors.append("intake_schema_version_mismatch")
    if payload.get("package_artifact_id") != EXPECTED_PACKAGE_ID:
        errors.append("intake_package_artifact_id_mismatch")
    if payload.get("package_schema_version") != EXPECTED_PACKAGE_SCHEMA:
        errors.append("intake_package_schema_version_mismatch")

    attempts = payload.get("attempts", [])
    if not isinstance(attempts, list):
        attempts = []
        errors.append("attempts_not_array")

    normalized_attempts: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    item_sequence_keys: set[tuple[str, int]] = set()
    attempted_item_ids: set[str] = set()
    represented_unit_ids: set[str] = set()
    represented_row_ids: set[str] = set()
    pass_count = 0
    fail_count = 0
    skill_counts: defaultdict[str, int] = defaultdict(int)
    assessment_attempt_count = 0

    for index, raw in enumerate(attempts):
        prefix = f"attempt[{index}]"
        if not isinstance(raw, Mapping):
            errors.append(f"{prefix}:not_object")
            continue

        event_id = raw.get("event_id")
        item_id = raw.get("item_id")
        sequence = raw.get("attempt_sequence")
        if not _nonempty_string(event_id):
            errors.append(f"{prefix}:event_id_missing")
        elif event_id in event_ids:
            errors.append(f"{prefix}:duplicate_event_id:{event_id}")
        else:
            event_ids.add(event_id)

        source_item = item_index.get(item_id)
        if source_item is None:
            errors.append(f"{prefix}:unknown_item_id:{item_id}")
            continue

        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            errors.append(f"{prefix}:attempt_sequence_invalid")
        else:
            key = (item_id, sequence)
            if key in item_sequence_keys:
                errors.append(
                    f"{prefix}:duplicate_item_attempt_sequence:{item_id}:{sequence}"
                )
            item_sequence_keys.add(key)

        if not _nonempty_string(raw.get("submitted_at")):
            errors.append(f"{prefix}:submitted_at_missing")

        score = raw.get("score")
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= float(score) <= 1
        ):
            errors.append(f"{prefix}:score_out_of_range")

        passed = raw.get("passed")
        outcome = raw.get("outcome")
        if not isinstance(passed, bool):
            errors.append(f"{prefix}:passed_not_boolean")
        if outcome not in {"PASS", "FAIL"}:
            errors.append(f"{prefix}:outcome_invalid")
        elif isinstance(passed, bool) and ((outcome == "PASS") != passed):
            errors.append(f"{prefix}:outcome_passed_mismatch")

        raw_tags = raw.get("error_tags")
        if not isinstance(raw_tags, list):
            errors.append(f"{prefix}:error_tags_not_array")
            tags: list[str] = []
        else:
            tags = _unique_strings(raw_tags)
            if len(tags) != len(raw_tags):
                errors.append(f"{prefix}:error_tags_duplicate_or_invalid")
        unknown_tags = sorted(set(tags) - allowed_error_tags)
        if unknown_tags:
            errors.append(
                f"{prefix}:unknown_error_tags:{','.join(unknown_tags)}"
            )
        if passed is True and tags:
            errors.append(f"{prefix}:passed_attempt_has_error_tags")
        if passed is False and not tags:
            errors.append(f"{prefix}:failed_attempt_missing_error_tag")

        response_text = raw.get("response_text")
        if not isinstance(response_text, str):
            errors.append(f"{prefix}:response_text_not_string")
            response_text = ""
        if not response_text.strip() and "ERR_RESPONSE_MISSING" not in tags:
            errors.append(f"{prefix}:empty_response_without_missing_tag")

        if raw.get("evaluator_type") not in ALLOWED_EVALUATORS:
            errors.append(f"{prefix}:evaluator_type_invalid")
        if not _nonempty_string(raw.get("evaluator_ref")):
            errors.append(f"{prefix}:evaluator_ref_missing")
        if not _nonempty_string(raw.get("evidence_ref")):
            errors.append(f"{prefix}:evidence_ref_missing")
        if raw.get("synthetic_fixture") is not False:
            errors.append(f"{prefix}:synthetic_fixture_forbidden")
        if raw.get("persistent_learner_state_write") is not False:
            errors.append(f"{prefix}:persistent_learner_state_write_forbidden")
        if raw.get("production_runtime_event") is not False:
            errors.append(f"{prefix}:production_runtime_event_forbidden")

        binding = source_item.get("content_binding", {})
        grammar_focus = binding.get("grammar_focus", [])
        row_ids = binding.get("canonical_egp_row_ids", [])
        grammar_id = grammar_focus[0] if len(grammar_focus) == 1 else None
        if grammar_id not in unit_index:
            errors.append(f"{prefix}:package_grammar_identity_invalid")
            continue

        attempted_item_ids.add(item_id)
        represented_unit_ids.add(grammar_id)
        represented_row_ids.update(row_ids)
        skill = source_item.get("skill")
        skill_counts[str(skill)] += 1
        if source_item.get("item_role") == "assessment":
            assessment_attempt_count += 1
        if passed is True:
            pass_count += 1
        elif passed is False:
            fail_count += 1

        normalized = deepcopy(dict(raw))
        normalized.update(
            {
                "grammar_unit_id": grammar_id,
                "canonical_egp_row_ids": list(row_ids),
                "skill": skill,
                "item_role": source_item.get("item_role"),
                "evidence_dimension": source_item.get("evidence_dimension"),
                "package_item_trace_status": "MATCHED",
                "learner_state_write": False,
            }
        )
        normalized_attempts.append(normalized)

    derived_claim = _derived_completion_claim(
        len(attempts),
        attempted_item_ids,
        len(item_index),
    )
    claimed = payload.get("pilot_completion_claim")
    if claimed not in {"NOT_STARTED", "PARTIAL", "COMPLETE"}:
        errors.append("pilot_completion_claim_invalid")
    elif claimed != derived_claim:
        errors.append(
            f"pilot_completion_claim_mismatch:{claimed}:{derived_claim}"
        )

    errors.extend(
        _validate_session(
            payload.get("session"),
            has_attempts=bool(attempts),
            derived_claim=derived_claim,
        )
    )

    if not attempts:
        evidence_status = "READY_AWAITING_REAL_ATTEMPTS"
        warnings.append(
            "The intake contract is ready, but no real learner attempt evidence was supplied."
        )
    elif derived_claim == "COMPLETE":
        evidence_status = "FULL_PACKAGE_REAL_EVIDENCE_ACCEPTED"
    else:
        evidence_status = "PARTIAL_REAL_EVIDENCE_ACCEPTED"

    completed_unit_ids = {
        grammar_id
        for grammar_id, unit in unit_index.items()
        if set(unit.get("delivery_plan", {}).get("practice_item_ids", []))
        .union(unit.get("delivery_plan", {}).get("assessment_item_ids", []))
        .issubset(attempted_item_ids)
    }

    status = "PASS" if not errors else "FAIL"
    pilot_started = bool(attempts) and status == "PASS"
    full_package_attempted = (
        len(attempted_item_ids) == len(item_index) and status == "PASS"
    )

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_private_pilot_evidence_normalized",
        "artifact_type": "validated_real_private_pilot_attempt_evidence",
        "schema_version": "a1_grammar_text_mode_private_pilot_evidence_normalized.v1",
        "source_refs": {
            "package_artifact_id": package.get("artifact_id"),
            "package_schema_version": package.get("schema_version"),
            "intake_schema_version": payload.get("intake_schema_version"),
        },
        "session": deepcopy(payload.get("session", {})),
        "intake_status": evidence_status if status == "PASS" else "REJECTED",
        "derived_completion_claim": derived_claim,
        "coverage_summary": {
            "package_unit_count": len(unit_index),
            "package_row_count": len(package.get("by_egp_row_id", {})),
            "package_item_count": len(item_index),
            "actual_attempt_count": len(normalized_attempts),
            "unique_attempted_item_count": len(attempted_item_ids),
            "represented_unit_count": len(represented_unit_ids),
            "completed_unit_count": len(completed_unit_ids),
            "represented_row_count": len(represented_row_ids),
            "reading_attempt_count": skill_counts.get("reading", 0),
            "writing_attempt_count": skill_counts.get("writing", 0),
            "assessment_attempt_count": assessment_attempt_count,
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
        "accepted_attempts": normalized_attempts if status == "PASS" else [],
        "release_gates": {
            "evidence_intake_contract_gate": "PASS" if status == "PASS" else "FAIL",
            "pilot_execution_gate": (
                "PASS_STARTED_WITH_REAL_EVIDENCE"
                if pilot_started
                else "BLOCKED_NOT_STARTED"
            ),
            "actual_learner_evidence_gate": (
                evidence_status if status == "PASS" else "REJECTED"
            ),
            "mastery_projection_gate": (
                "READY_FOR_PROJECTION"
                if pilot_started
                else "BLOCKED_NO_REAL_EVIDENCE"
            ),
            "audio_scope_gate": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
            "production_runtime_gate": "BLOCKED_NOT_APPROVED",
        },
        "claim_boundaries": {
            "evidence_intake_pipeline_complete": True,
            "text_mode_private_pilot_started": pilot_started,
            "actual_learner_attempts_collected": pilot_started,
            "full_package_attempt_coverage_complete": full_package_attempted,
            "actual_mastery_measured": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "production_runtime_complete": False,
            "no_persistent_learner_state_write": True,
            "no_a2_a2plus_expansion": True,
        },
    }

    report = {
        "task_id": TASK_ID,
        "validation_status": status,
        "intake_status": artifact["intake_status"],
        "coverage_summary": artifact["coverage_summary"],
        "gate_checks": artifact["release_gates"],
        "errors": errors,
        "warnings": warnings,
        "stop_reason": (
            "REAL_LEARNER_EVIDENCE_REQUIRED"
            if status == "PASS" and not pilot_started
            else "NONE"
            if status == "PASS"
            else "VALIDATION_FAILURE"
        ),
        "next_resume_task": (
            NEXT_RESUME_TASK
            if status == "PASS" and not pilot_started
            else NEXT_SHORT_STEP
            if status == "PASS"
            else None
        ),
        "validation_mode": "STATIC_INTAKE_CONTRACT_REVIEW_CI_NOT_VERIFIED",
    }
    return artifact, report


def build_and_validate_from_repo(
    intake_path: Path = INTAKE_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    package = _validated_package()
    payload = load_json(intake_path)
    return normalize_and_validate(payload, package)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intake", type=Path, default=INTAKE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact, report = build_and_validate_from_repo(args.intake)
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
