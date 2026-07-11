#!/usr/bin/env python3
"""Import real private-pilot responses into M105P evidence and M105Q projection.

The command is intentionally local-only. Raw learner responses and generated
learner evidence must be stored under ``.local/`` or outside the repository.
No synthetic attempts, learner-state persistence, production runtime events, or
final mastery claims are created by this importer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_evidence_projection_review_routing import (
    build_artifact as build_projection_artifact,
    validate_artifact as validate_projection_artifact,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    INTAKE_PATH,
    load_json,
    normalize_and_validate,
    write_json,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)

TASK_ID = "R7-M105P02_A1A1PlusTextModePrivatePilotRealAttemptImport"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
IMPORT_SCHEMA_VERSION = "a1_grammar_text_mode_private_pilot_response_import.v1"
NEXT_SHORT_STEP = "R7-M105Q_A1A1PlusTextModeEvidenceProjectionAndReviewRouting"

DEFAULT_RESPONSES_PATH = REPO_ROOT / ".local/a1_private_pilot_responses.json"
DEFAULT_EVIDENCE_PATH = REPO_ROOT / ".local/a1_private_pilot_evidence.json"
DEFAULT_NORMALIZED_PATH = REPO_ROOT / ".local/a1_private_pilot_evidence_normalized.json"
DEFAULT_INTAKE_REPORT_PATH = REPO_ROOT / ".local/a1_private_pilot_evidence_validation.json"
DEFAULT_PROJECTION_PATH = REPO_ROOT / ".local/a1_private_pilot_projection.json"
DEFAULT_PROJECTION_REPORT_PATH = REPO_ROOT / ".local/a1_private_pilot_projection_validation.json"
DEFAULT_IMPORT_REPORT_PATH = REPO_ROOT / ".local/a1_private_pilot_import_validation.json"

OPEN_PRODUCTIVE_TASK_TYPES = {
    "guided_contextual_writing",
    "text_mode_writing_checkpoint",
}
FORBIDDEN_EXTERNAL_IDENTITY_FIELDS = {
    "grammar_unit_id",
    "canonical_egp_row_ids",
    "skill",
    "item_role",
    "evidence_dimension",
    "package_item_trace_status",
}
ALLOWED_SOURCE_FIELDS = {
    "item_id",
    "response_text",
    "attempt_sequence",
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


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("’", "'").replace("‘", "'")
    normalized = re.sub(r"\s+", " ", normalized.strip())
    normalized = re.sub(r"[.!?]+$", "", normalized).strip()
    return normalized.casefold()


def _accepted_texts(item: Mapping[str, Any]) -> set[str]:
    values: list[str] = []
    answer_key = item.get("answer_key", {})
    values.extend(answer_key.get("accepted_texts", []))
    canonical = answer_key.get("canonical_target")
    if _nonempty_string(canonical):
        values.append(canonical)

    gap_spec = item.get("gap_spec", {})
    values.extend(gap_spec.get("accepted_missing_tokens", []))

    correct_tokens = item.get("correct_token_sequence")
    if isinstance(correct_tokens, list):
        values.append(" ".join(str(token) for token in correct_tokens))

    correct_morphemes = item.get("correct_morphology_parts")
    if isinstance(correct_morphemes, list):
        values.append("".join(str(part) for part in correct_morphemes))
        values.append(" ".join(str(part) for part in correct_morphemes))

    return {
        _normalize_text(value)
        for value in values
        if isinstance(value, str) and value.strip()
    }


def _minimum_score(item: Mapping[str, Any]) -> float:
    rubric = item.get("scoring_rubric", {})
    value = rubric.get("minimum_score", 1.0)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 1.0


def _validated_package() -> dict[str, Any]:
    package, report = build_package_source()
    if report.get("validation_status") != "PASS":
        raise RuntimeError("private_pilot_package_validation_failed")
    if len(package.get("item_bank", [])) != 192:
        raise RuntimeError("private_pilot_package_item_count_not_192")
    return package


def _item_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    items = package.get("item_bank", [])
    index = {
        item.get("item_id"): dict(item)
        for item in items
        if isinstance(item, Mapping) and _nonempty_string(item.get("item_id"))
    }
    if len(items) != 192 or len(index) != 192:
        raise ValueError("real_attempt_import_item_index_not_192")
    return index


def _session_errors(session: Any) -> list[str]:
    if not isinstance(session, Mapping):
        return ["import_session_not_object"]
    errors: list[str] = []
    for field in (
        "session_id",
        "learner_ref",
        "operator_ref",
        "started_at",
        "evidence_source_ref",
    ):
        if not _nonempty_string(session.get(field)):
            errors.append(f"import_session_field_missing:{field}")
    learner_ref = session.get("learner_ref")
    if isinstance(learner_ref, str) and "@" in learner_ref:
        errors.append("import_learner_ref_must_be_pseudonymous_not_email")
    completed_at = session.get("completed_at")
    if completed_at is not None and not _nonempty_string(completed_at):
        errors.append("import_session_completed_at_invalid")
    return errors


def _record_shape_errors(record: Any, index: int) -> list[str]:
    prefix = f"response[{index}]"
    if not isinstance(record, Mapping):
        return [f"{prefix}:not_object"]
    errors: list[str] = []
    extra = sorted(set(record) - ALLOWED_SOURCE_FIELDS)
    if extra:
        errors.append(f"{prefix}:unsupported_fields:{','.join(extra)}")
    forbidden = sorted(set(record).intersection(FORBIDDEN_EXTERNAL_IDENTITY_FIELDS))
    if forbidden:
        errors.append(f"{prefix}:external_identity_fields_forbidden:{','.join(forbidden)}")
    if not _nonempty_string(record.get("item_id")):
        errors.append(f"{prefix}:item_id_missing")
    if not isinstance(record.get("response_text"), str):
        errors.append(f"{prefix}:response_text_not_string")
    if not _nonempty_string(record.get("submitted_at")):
        errors.append(f"{prefix}:submitted_at_missing")
    sequence = record.get("attempt_sequence", 1)
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        errors.append(f"{prefix}:attempt_sequence_invalid")
    return errors


def _manual_evaluation(
    record: Mapping[str, Any],
    item: Mapping[str, Any],
    *,
    prefix: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    score = record.get("score")
    passed = record.get("passed")
    evaluator_type = record.get("evaluator_type")
    evaluator_ref = record.get("evaluator_ref")

    if (
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not 0 <= float(score) <= 1
    ):
        errors.append(f"{prefix}:manual_score_required_0_to_1")
    if not isinstance(passed, bool):
        errors.append(f"{prefix}:manual_passed_required_boolean")
    if evaluator_type not in {"MANUAL", "HYBRID"}:
        errors.append(f"{prefix}:manual_evaluator_type_required")
    if not _nonempty_string(evaluator_ref):
        errors.append(f"{prefix}:manual_evaluator_ref_required")
    if errors:
        return None, errors

    threshold = _minimum_score(item)
    expected_passed = float(score) >= threshold
    if passed is not expected_passed:
        errors.append(
            f"{prefix}:manual_passed_score_mismatch:threshold={threshold}"
        )
        return None, errors

    return {
        "score": float(score),
        "passed": passed,
        "evaluator_type": evaluator_type,
        "evaluator_ref": evaluator_ref.strip(),
    }, []


def _evaluate_record(
    record: Mapping[str, Any],
    item: Mapping[str, Any],
    session: Mapping[str, Any],
    *,
    index: int,
) -> tuple[dict[str, Any] | None, list[str]]:
    prefix = f"response[{index}]"
    response_text = record["response_text"]
    exact_match = _normalize_text(response_text) in _accepted_texts(item)
    task_type = item.get("task_type")
    manual_values_present = any(
        record.get(field) is not None
        for field in ("score", "passed", "evaluator_type", "evaluator_ref")
    )

    if task_type in OPEN_PRODUCTIVE_TASK_TYPES and not exact_match:
        evaluation, errors = _manual_evaluation(
            record,
            item,
            prefix=prefix,
        )
        if errors:
            return None, [f"{prefix}:manual_evaluation_required", *errors]
    elif manual_values_present:
        evaluation, errors = _manual_evaluation(
            record,
            item,
            prefix=prefix,
        )
        if errors:
            return None, errors
    else:
        evaluation = {
            "score": 1.0 if exact_match else 0.0,
            "passed": exact_match,
            "evaluator_type": "RULE",
            "evaluator_ref": "rule:a1_private_pilot_exact_answer.v1",
        }

    passed = bool(evaluation["passed"])
    raw_tags = record.get("error_tags", [])
    if not isinstance(raw_tags, list):
        return None, [f"{prefix}:error_tags_not_array"]
    tags = _unique_strings(raw_tags)
    if len(tags) != len(raw_tags):
        return None, [f"{prefix}:error_tags_duplicate_or_invalid"]
    if passed:
        if tags:
            return None, [f"{prefix}:passed_response_has_error_tags"]
    elif not tags:
        tags = [
            "ERR_RESPONSE_MISSING"
            if not response_text.strip()
            else "ERR_UNCLASSIFIED_GRAMMAR_FAILURE"
        ]

    sequence = record.get("attempt_sequence", 1)
    item_id = record["item_id"]
    session_id = session["session_id"]
    source_ref = session["evidence_source_ref"].rstrip("/")
    evidence_ref = record.get("evidence_ref")
    if not _nonempty_string(evidence_ref):
        evidence_ref = f"{source_ref}/item/{item_id}/attempt/{sequence}"

    return {
        "event_id": f"event:{session_id}:{item_id}:{sequence}",
        "item_id": item_id,
        "attempt_sequence": sequence,
        "submitted_at": record["submitted_at"],
        "response_text": response_text,
        "score": evaluation["score"],
        "passed": passed,
        "outcome": "PASS" if passed else "FAIL",
        "error_tags": tags,
        "evaluator_type": evaluation["evaluator_type"],
        "evaluator_ref": evaluation["evaluator_ref"],
        "evidence_ref": evidence_ref,
        "synthetic_fixture": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }, []


def build_evidence_payload(
    source: Mapping[str, Any],
    package: Mapping[str, Any],
    template: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    if source.get("import_schema_version") != IMPORT_SCHEMA_VERSION:
        errors.append("import_schema_version_mismatch")

    session = source.get("session")
    errors.extend(_session_errors(session))
    responses = source.get("responses")
    if not isinstance(responses, list):
        responses = []
        errors.append("import_responses_not_array")
    elif not responses:
        errors.append("import_real_responses_required")

    item_index = _item_index(package)
    attempts: list[dict[str, Any]] = []
    item_sequence_keys: set[tuple[str, int]] = set()
    for index, record in enumerate(responses):
        shape_errors = _record_shape_errors(record, index)
        if shape_errors:
            errors.extend(shape_errors)
            continue
        item_id = record["item_id"]
        item = item_index.get(item_id)
        if item is None:
            errors.append(f"response[{index}]:unknown_item_id:{item_id}")
            continue
        sequence = record.get("attempt_sequence", 1)
        key = (item_id, sequence)
        if key in item_sequence_keys:
            errors.append(
                f"response[{index}]:duplicate_item_attempt_sequence:{item_id}:{sequence}"
            )
            continue
        item_sequence_keys.add(key)
        if not isinstance(session, Mapping):
            continue
        attempt, evaluation_errors = _evaluate_record(
            record,
            item,
            session,
            index=index,
        )
        errors.extend(evaluation_errors)
        if attempt is not None:
            attempts.append(attempt)

    unique_items = {attempt["item_id"] for attempt in attempts}
    if not attempts:
        claim = "NOT_STARTED"
    elif len(unique_items) == len(item_index):
        claim = "COMPLETE"
    else:
        claim = "PARTIAL"

    payload = deepcopy(dict(template))
    payload["template_status"] = "REAL_VALUES_IMPORTED_LOCAL_ONLY"
    payload["session"] = {
        "session_id": session.get("session_id") if isinstance(session, Mapping) else None,
        "learner_ref": session.get("learner_ref") if isinstance(session, Mapping) else None,
        "operator_ref": session.get("operator_ref") if isinstance(session, Mapping) else None,
        "started_at": session.get("started_at") if isinstance(session, Mapping) else None,
        "completed_at": session.get("completed_at") if isinstance(session, Mapping) else None,
        "delivery_environment": "LOCAL_PRIVATE_TEXT_MODE",
        "evidence_source_ref": session.get("evidence_source_ref") if isinstance(session, Mapping) else None,
    }
    if claim == "COMPLETE" and payload["session"]["completed_at"] is None:
        payload["session"]["completed_at"] = max(
            attempt["submitted_at"] for attempt in attempts
        )
    payload["pilot_completion_claim"] = claim
    payload["attempts"] = attempts

    report = {
        "task_id": TASK_ID,
        "validation_status": "PASS" if not errors else "FAIL",
        "source_response_count": len(responses),
        "generated_attempt_count": len(attempts),
        "unique_attempted_item_count": len(unique_items),
        "derived_completion_claim": claim,
        "rule_evaluated_attempt_count": sum(
            attempt["evaluator_type"] == "RULE" for attempt in attempts
        ),
        "manual_or_hybrid_attempt_count": sum(
            attempt["evaluator_type"] in {"MANUAL", "HYBRID"}
            for attempt in attempts
        ),
        "pass_count": sum(attempt["passed"] is True for attempt in attempts),
        "fail_count": sum(attempt["passed"] is False for attempt in attempts),
        "errors": errors,
        "claim_boundaries": {
            "real_response_source_required": True,
            "synthetic_attempt_generation": False,
            "external_content_identity_trusted": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "final_mastery_claim": False,
        },
    }
    return payload, report


def _private_path_error(path: Path) -> str | None:
    resolved = path.expanduser().resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    if relative.parts and relative.parts[0] == ".local":
        return None
    return f"private_learner_path_must_be_under_dot_local_or_outside_repo:{path}"


def run_import(
    source: Mapping[str, Any],
    package: Mapping[str, Any] | None = None,
    template: Mapping[str, Any] | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    package = package or _validated_package()
    template = template or load_json(INTAKE_PATH)
    evidence, import_report = build_evidence_payload(source, package, template)
    if import_report["validation_status"] != "PASS":
        return evidence, import_report, {}, {}, {}

    normalized, intake_report = normalize_and_validate(evidence, package)
    if intake_report.get("validation_status") != "PASS":
        import_report["validation_status"] = "FAIL"
        import_report["errors"].append("generated_evidence_failed_m105p_intake")
        return evidence, import_report, normalized, intake_report, {}

    projection = build_projection_artifact(package, normalized)
    projection_report = validate_projection_artifact(
        projection,
        package,
        normalized,
    )
    if projection_report.get("validation_status") != "PASS":
        import_report["validation_status"] = "FAIL"
        import_report["errors"].append("normalized_evidence_failed_m105q_projection")
    import_report["m105p_intake_status"] = intake_report.get("intake_status")
    import_report["m105q_next_task"] = projection_report.get("next_task")
    import_report["next_short_step"] = NEXT_SHORT_STEP
    return evidence, import_report, normalized, intake_report, {
        "artifact": projection,
        "report": projection_report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES_PATH)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE_PATH)
    parser.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED_PATH)
    parser.add_argument("--intake-report", type=Path, default=DEFAULT_INTAKE_REPORT_PATH)
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION_PATH)
    parser.add_argument(
        "--projection-report",
        type=Path,
        default=DEFAULT_PROJECTION_REPORT_PATH,
    )
    parser.add_argument("--import-report", type=Path, default=DEFAULT_IMPORT_REPORT_PATH)
    args = parser.parse_args(argv)

    path_errors = [
        error
        for path in (
            args.responses,
            args.evidence,
            args.normalized,
            args.intake_report,
            args.projection,
            args.projection_report,
            args.import_report,
        )
        if (error := _private_path_error(path)) is not None
    ]
    if path_errors:
        report = {
            "task_id": TASK_ID,
            "validation_status": "FAIL",
            "errors": path_errors,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    if not args.responses.exists():
        report = {
            "task_id": TASK_ID,
            "validation_status": "BLOCKED",
            "errors": [f"real_response_source_not_found:{args.responses}"],
            "stop_reason": "REAL_LEARNER_EVIDENCE_REQUIRED",
        }
        write_json(args.import_report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    source = load_json(args.responses)
    evidence, import_report, normalized, intake_report, projection_bundle = run_import(
        source
    )
    write_json(args.evidence, evidence)
    write_json(args.import_report, import_report)
    if normalized:
        write_json(args.normalized, normalized)
    if intake_report:
        write_json(args.intake_report, intake_report)
    if projection_bundle:
        write_json(args.projection, projection_bundle["artifact"])
        write_json(args.projection_report, projection_bundle["report"])

    print(json.dumps(import_report, ensure_ascii=False, indent=2))
    return 0 if import_report.get("validation_status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
