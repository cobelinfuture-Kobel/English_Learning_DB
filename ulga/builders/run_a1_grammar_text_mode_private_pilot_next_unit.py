#!/usr/bin/env python3
"""Run the next eligible A1/A1+ text-mode private-pilot unit locally.

Each unit execution is stored in an isolated ``.local`` snapshot. Existing
baseline/projection files are read for progression routing but are never
overwritten, so starting another unit cannot reset an earlier unit's retention
clock. No learner evidence, learner state, or production event is committed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    load_json,
    write_json,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    DEFAULT_NORMALIZED_PATH,
    DEFAULT_PROJECTION_PATH,
    IMPORT_SCHEMA_VERSION,
    OPEN_PRODUCTIVE_TASK_TYPES,
    _private_path_error,
    run_import,
)

TASK_ID = "R7-M105P03_A1A1PlusTextModePrivatePilotNextUnitExecution"
NEXT_SHORT_STEP = TASK_ID
RETENTION_RESUME_TASK = (
    "R7-M105S_A1A1PlusTextModeRetentionEvidenceIntake_Execution"
)
REVIEW_TASK = "R7-M105R_A1A1PlusTextModeReviewSessionPackageIntegration"
DEFAULT_LOCAL_ROOT = REPO_ROOT / ".local/a1_private_pilot_units"

PROGRESSION_READY_STATUSES = {
    "MASTERY_CANDIDATE_PENDING_RETENTION",
    "RETENTION_CONFIRMED_PENDING_FINAL_MASTERY_PROJECTION",
}


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def _unit_item_ids(unit: Mapping[str, Any]) -> list[str]:
    plan = unit.get("delivery_plan", {})
    item_ids = list(plan.get("practice_item_ids", [])) + list(
        plan.get("assessment_item_ids", [])
    )
    if len(item_ids) != 8 or len(set(item_ids)) != 8:
        raise ValueError(
            f"private_pilot_unit_item_contract_not_8:{unit.get('grammar_unit_id')}"
        )
    return item_ids


def projection_state(
    projection: Mapping[str, Any],
) -> tuple[set[str], set[str]]:
    """Return fully executed units and units allowed to unlock prerequisites."""

    executed: set[str] = set()
    progression_ready: set[str] = set()
    for grammar_id, unit in projection.get("by_grammar_unit_id", {}).items():
        if not isinstance(grammar_id, str) or not isinstance(unit, Mapping):
            continue
        attempted = unit.get("attempted_item_count")
        required = unit.get("required_item_count")
        if (
            isinstance(attempted, int)
            and isinstance(required, int)
            and required == 8
            and attempted >= required
        ):
            executed.add(grammar_id)
        if unit.get("projection_status") in PROGRESSION_READY_STATUSES:
            progression_ready.add(grammar_id)
    return executed, progression_ready


def discover_execution_state(
    *,
    local_root: Path,
    legacy_projection_path: Path,
) -> tuple[set[str], set[str], list[str]]:
    executed: set[str] = set()
    progression_ready: set[str] = set()
    source_paths: list[str] = []

    candidate_paths: list[Path] = []
    if legacy_projection_path.exists():
        candidate_paths.append(legacy_projection_path)
    if local_root.exists():
        candidate_paths.extend(sorted(local_root.glob("*/*/projection.json")))

    seen: set[Path] = set()
    for path in candidate_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        projection = _load_optional_json(path)
        current_executed, current_ready = projection_state(projection)
        executed.update(current_executed)
        progression_ready.update(current_ready)
        source_paths.append(str(path))

    return executed, progression_ready, source_paths


def select_next_unit(
    package: Mapping[str, Any],
    *,
    executed_unit_ids: set[str],
    progression_ready_unit_ids: set[str],
    requested_unit_id: str | None = None,
) -> Mapping[str, Any] | None:
    units = sorted(
        package.get("learning_units", []),
        key=lambda unit: unit.get("sequence_index", 10**9),
    )
    by_id = {
        unit.get("grammar_unit_id"): unit
        for unit in units
        if isinstance(unit, Mapping)
        and isinstance(unit.get("grammar_unit_id"), str)
    }

    if requested_unit_id is not None:
        if requested_unit_id not in by_id:
            raise ValueError(f"private_pilot_unknown_requested_unit:{requested_unit_id}")
        if requested_unit_id in executed_unit_ids:
            raise ValueError(
                f"private_pilot_requested_unit_already_executed:{requested_unit_id}"
            )
        unit = by_id[requested_unit_id]
        missing = sorted(
            set(unit.get("prerequisite_unit_ids", []))
            - progression_ready_unit_ids
        )
        if missing:
            raise ValueError(
                "private_pilot_requested_unit_prerequisites_not_ready:"
                f"{requested_unit_id}:{','.join(missing)}"
            )
        return unit

    remaining = [
        unit
        for unit in units
        if unit.get("grammar_unit_id") not in executed_unit_ids
    ]
    if not remaining:
        return None

    for unit in remaining:
        prerequisites = set(unit.get("prerequisite_unit_ids", []))
        if prerequisites.issubset(progression_ready_unit_ids):
            return unit

    blocked = {
        unit.get("grammar_unit_id"): sorted(
            set(unit.get("prerequisite_unit_ids", []))
            - progression_ready_unit_ids
        )
        for unit in remaining
    }
    raise RuntimeError(
        "private_pilot_no_eligible_unit:"
        + json.dumps(blocked, ensure_ascii=False, sort_keys=True)
    )


def _display_item(item: Mapping[str, Any], number: int, total: int) -> None:
    print()
    print("-" * 72)
    print(
        f"[{number}/{total}] {item.get('skill')} / "
        f"{item.get('item_role')} / {item.get('task_type')}"
    )
    print(f"Item ID: {item.get('item_id')}")
    context = item.get("context")
    if context:
        print("Context:", json.dumps(context, ensure_ascii=False))
    print("Question:", item.get("prompt", ""))
    for option_number, option in enumerate(item.get("options", []), start=1):
        print(f"  {option_number}. {option}")


def _collect_response(
    item: Mapping[str, Any],
    *,
    operator_ref: str,
    input_func: Callable[[str], str] = input,
) -> dict[str, Any]:
    options = item.get("options", [])
    raw_answer = input_func("Learner answer: ").strip()
    response_text = raw_answer
    if options and raw_answer.isdigit():
        selected = int(raw_answer)
        if 1 <= selected <= len(options):
            response_text = str(options[selected - 1])

    record: dict[str, Any] = {
        "item_id": item["item_id"],
        "response_text": response_text,
        "attempt_sequence": 1,
        "submitted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    if item.get("task_type") in OPEN_PRODUCTIVE_TASK_TYPES:
        threshold = float(
            item.get("scoring_rubric", {}).get("minimum_score", 1.0)
        )
        while True:
            raw_score = input_func(
                f"Operator score 0–1 (pass threshold {threshold}): "
            ).strip()
            try:
                score = float(raw_score)
            except ValueError:
                print("Please enter a number from 0 to 1.")
                continue
            if 0.0 <= score <= 1.0:
                break
            print("Please enter a number from 0 to 1.")
        passed = score >= threshold
        record.update(
            {
                "score": score,
                "passed": passed,
                "evaluator_type": "MANUAL",
                "evaluator_ref": operator_ref,
                "error_tags": (
                    [] if passed else ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"]
                ),
            }
        )
    return record


def _resolve_identity(
    *,
    legacy_normalized_path: Path,
    learner_ref: str | None,
    operator_ref: str | None,
) -> tuple[str, str]:
    legacy = _load_optional_json(legacy_normalized_path)
    session = legacy.get("session", {}) if isinstance(legacy, Mapping) else {}
    resolved_learner = learner_ref or session.get("learner_ref")
    resolved_operator = operator_ref or session.get("operator_ref")
    if not isinstance(resolved_learner, str) or not resolved_learner.strip():
        raise ValueError("private_pilot_learner_ref_required")
    if "@" in resolved_learner:
        raise ValueError("private_pilot_learner_ref_must_be_pseudonymous")
    if not isinstance(resolved_operator, str) or not resolved_operator.strip():
        raise ValueError("private_pilot_operator_ref_required")
    return resolved_learner.strip(), resolved_operator.strip()


def _session_directory(
    local_root: Path,
    grammar_unit_id: str,
    started_at: datetime,
) -> Path:
    safe_unit = re.sub(r"[^A-Za-z0-9_.-]+", "_", grammar_unit_id)
    stamp = started_at.strftime("%Y%m%dT%H%M%S%z")
    return local_root / safe_unit / stamp


def _write_execution_bundle(
    root: Path,
    *,
    source: Mapping[str, Any],
    evidence: Mapping[str, Any],
    import_report: Mapping[str, Any],
    normalized: Mapping[str, Any],
    intake_report: Mapping[str, Any],
    projection_bundle: Mapping[str, Any],
    execution_report: Mapping[str, Any],
) -> None:
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "responses.json", source)
    write_json(root / "evidence.json", evidence)
    write_json(root / "import_report.json", import_report)
    write_json(root / "normalized.json", normalized)
    write_json(root / "intake_report.json", intake_report)
    write_json(root / "projection.json", projection_bundle["artifact"])
    write_json(root / "projection_report.json", projection_bundle["report"])
    write_json(root / "execution_report.json", execution_report)


def _write_manifest(
    *,
    package: Mapping[str, Any],
    local_root: Path,
    legacy_projection_path: Path,
) -> None:
    executed, progression_ready, sources = discover_execution_state(
        local_root=local_root,
        legacy_projection_path=legacy_projection_path,
    )
    write_json(
        local_root / "manifest.json",
        {
            "task_id": TASK_ID,
            "package_artifact_id": package.get("artifact_id"),
            "executed_unit_ids": sorted(executed),
            "progression_ready_unit_ids": sorted(progression_ready),
            "execution_count": len(executed),
            "progression_ready_count": len(progression_ready),
            "projection_source_paths": sources,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
        },
    )


def build_preview_report(
    *,
    unit: Mapping[str, Any] | None,
    executed_unit_ids: set[str],
    progression_ready_unit_ids: set[str],
) -> dict[str, Any]:
    if unit is None:
        return {
            "task_id": TASK_ID,
            "validation_status": "PASS",
            "execution_status": "ALL_UNITS_ALREADY_EXECUTED",
            "executed_unit_count": len(executed_unit_ids),
            "progression_ready_unit_count": len(progression_ready_unit_ids),
            "real_learner_evidence_created": False,
            "persistent_learner_state_write": False,
            "stop_reason": "NONE",
            "next_short_step": RETENTION_RESUME_TASK,
        }
    return {
        "task_id": TASK_ID,
        "validation_status": "PASS",
        "execution_status": "NEXT_UNIT_READY",
        "grammar_unit_id": unit.get("grammar_unit_id"),
        "sequence_index": unit.get("sequence_index"),
        "title_en": unit.get("learning_content", {}).get("title_en"),
        "required_item_count": len(_unit_item_ids(unit)),
        "executed_unit_count": len(executed_unit_ids),
        "progression_ready_unit_count": len(progression_ready_unit_ids),
        "real_learner_evidence_created": False,
        "persistent_learner_state_write": False,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", default=None)
    parser.add_argument("--learner-ref", default=None)
    parser.add_argument("--operator-ref", default=None)
    parser.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL_ROOT)
    parser.add_argument(
        "--legacy-normalized",
        type=Path,
        default=DEFAULT_NORMALIZED_PATH,
    )
    parser.add_argument(
        "--legacy-projection",
        type=Path,
        default=DEFAULT_PROJECTION_PATH,
    )
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)

    path_errors = [
        error
        for path in (
            args.local_root,
            args.legacy_normalized,
            args.legacy_projection,
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

    package, package_report = build_package_source()
    if package_report.get("validation_status") != "PASS":
        print(json.dumps(package_report, ensure_ascii=False, indent=2))
        return 1

    executed, progression_ready, _ = discover_execution_state(
        local_root=args.local_root,
        legacy_projection_path=args.legacy_projection,
    )
    try:
        unit = select_next_unit(
            package,
            executed_unit_ids=executed,
            progression_ready_unit_ids=progression_ready,
            requested_unit_id=args.unit,
        )
    except (ValueError, RuntimeError) as exc:
        report = {
            "task_id": TASK_ID,
            "validation_status": "BLOCKED",
            "execution_status": "NO_ELIGIBLE_NEXT_UNIT",
            "errors": [str(exc)],
            "stop_reason": "PREREQUISITE_OR_REVIEW_EVIDENCE_REQUIRED",
            "next_short_step": REVIEW_TASK,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    preview = build_preview_report(
        unit=unit,
        executed_unit_ids=executed,
        progression_ready_unit_ids=progression_ready,
    )
    if args.preview or unit is None:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    try:
        learner_ref, operator_ref = _resolve_identity(
            legacy_normalized_path=args.legacy_normalized,
            learner_ref=args.learner_ref,
            operator_ref=args.operator_ref,
        )
    except ValueError as exc:
        report = {
            "task_id": TASK_ID,
            "validation_status": "BLOCKED",
            "execution_status": "IDENTITY_INPUT_REQUIRED",
            "errors": [str(exc)],
            "stop_reason": "REAL_LEARNER_EVIDENCE_REQUIRED",
            "next_short_step": TASK_ID,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    grammar_id = unit["grammar_unit_id"]
    item_index = {
        item["item_id"]: item for item in package.get("item_bank", [])
    }
    item_ids = _unit_item_ids(unit)
    started_at = datetime.now().astimezone()
    session_id = (
        f"session:A1_PILOT_{grammar_id}_{started_at.strftime('%Y%m%dT%H%M%S')}"
    )

    print()
    print("=" * 72)
    print(f"Private-pilot unit: {grammar_id}")
    print("Title:", unit.get("learning_content", {}).get("title_en", grammar_id))
    print(f"Items: {len(item_ids)}")
    print("=" * 72)

    responses = []
    for number, item_id in enumerate(item_ids, start=1):
        item = item_index[item_id]
        _display_item(item, number, len(item_ids))
        responses.append(
            _collect_response(item, operator_ref=operator_ref)
        )

    completed_at = datetime.now().astimezone()
    source = {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "session": {
            "session_id": session_id,
            "learner_ref": learner_ref,
            "operator_ref": operator_ref,
            "started_at": started_at.isoformat(timespec="seconds"),
            "completed_at": completed_at.isoformat(timespec="seconds"),
            "evidence_source_ref": f"local_private_pilot://{session_id}",
        },
        "responses": responses,
    }

    evidence, import_report, normalized, intake_report, projection_bundle = (
        run_import(source, package=package)
    )
    projection_report = projection_bundle.get("report", {})
    projection = projection_bundle.get("artifact", {})
    unit_projection = projection.get("by_grammar_unit_id", {}).get(grammar_id, {})

    errors = list(import_report.get("errors", []))
    if import_report.get("validation_status") != "PASS":
        errors.append("next_unit_import_not_pass")
    if intake_report.get("validation_status") != "PASS":
        errors.append("next_unit_intake_not_pass")
    if projection_report.get("validation_status") != "PASS":
        errors.append("next_unit_projection_not_pass")
    if unit_projection.get("attempted_item_count") != 8:
        errors.append("next_unit_attempted_item_count_not_8")

    status = "PASS" if not errors else "FAIL"
    projection_status = unit_projection.get("projection_status")
    execution_report = {
        "task_id": TASK_ID,
        "validation_status": status,
        "execution_status": (
            "UNIT_EXECUTION_COMPLETED" if status == "PASS" else "UNIT_EXECUTION_FAILED"
        ),
        "grammar_unit_id": grammar_id,
        "sequence_index": unit.get("sequence_index"),
        "real_attempt_count": len(normalized.get("accepted_attempts", [])),
        "projection_status": projection_status,
        "retention_candidate": (
            projection_status == "MASTERY_CANDIDATE_PENDING_RETENTION"
        ),
        "review_required": projection_status == "REVIEW_REQUIRED",
        "final_mastery_claimed": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
        "errors": errors,
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": (
            REVIEW_TASK
            if projection_status == "REVIEW_REQUIRED"
            else NEXT_SHORT_STEP
        ),
        "retention_resume_task": (
            RETENTION_RESUME_TASK
            if projection_status == "MASTERY_CANDIDATE_PENDING_RETENTION"
            else None
        ),
    }

    output_root = _session_directory(args.local_root, grammar_id, started_at)
    execution_report["private_output_root"] = str(output_root)
    if projection_bundle:
        _write_execution_bundle(
            output_root,
            source=source,
            evidence=evidence,
            import_report=import_report,
            normalized=normalized,
            intake_report=intake_report,
            projection_bundle=projection_bundle,
            execution_report=execution_report,
        )
        _write_manifest(
            package=package,
            local_root=args.local_root,
            legacy_projection_path=args.legacy_projection,
        )
    else:
        output_root.mkdir(parents=True, exist_ok=False)
        write_json(output_root / "responses.json", source)
        write_json(output_root / "import_report.json", import_report)
        write_json(output_root / "execution_report.json", execution_report)

    print()
    print(json.dumps(execution_report, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
