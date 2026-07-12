#!/usr/bin/env python3
"""Run a local targeted review session for an A1/A1+ text-mode pilot unit.

The runner consumes an existing private unit snapshot, selects unresolved or
evidence-quality-suspicious items, collects real retry responses, and rebuilds
the existing M105P/M105Q evidence projection. All outputs remain under
``.local``. No learner state, production event, or final mastery is written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

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
    IMPORT_SCHEMA_VERSION,
    OPEN_PRODUCTIVE_TASK_TYPES,
    _private_path_error,
    run_import,
)
from ulga.builders.run_a1_grammar_text_mode_private_pilot_next_unit import (
    _collect_response,
    _contains_linguistic_content,
    _display_item,
)

TASK_ID = "R7-M105R_A1A1PlusTextModeReviewSessionPackageIntegration"
NEXT_REVIEW_TASK = TASK_ID
NEXT_PILOT_TASK = (
    "R7-M105P03_A1A1PlusTextModePrivatePilotNextUnitExecution"
)
RETENTION_RESUME_TASK = (
    "R7-M105S_A1A1PlusTextModeRetentionEvidenceIntake_Execution"
)
DEFAULT_LOCAL_ROOT = REPO_ROOT / ".local/a1_private_pilot_units"


def _safe_unit_id(grammar_unit_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", grammar_unit_id)


def _unit_item_ids(
    package: Mapping[str, Any],
    grammar_unit_id: str,
) -> list[str]:
    for unit in package.get("learning_units", []):
        if unit.get("grammar_unit_id") != grammar_unit_id:
            continue
        plan = unit.get("delivery_plan", {})
        item_ids = list(plan.get("practice_item_ids", [])) + list(
            plan.get("assessment_item_ids", [])
        )
        if len(item_ids) != 8 or len(set(item_ids)) != 8:
            raise ValueError(
                f"review_unit_item_contract_not_8:{grammar_unit_id}"
            )
        return item_ids
    raise ValueError(f"review_unknown_grammar_unit:{grammar_unit_id}")


def _item_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index = {
        item.get("item_id"): dict(item)
        for item in package.get("item_bank", [])
        if isinstance(item, Mapping)
        and isinstance(item.get("item_id"), str)
    }
    if len(index) != 192:
        raise ValueError("review_package_item_index_not_192")
    return index


def _latest_attempts(
    normalized: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for attempt in normalized.get("accepted_attempts", []):
        if not isinstance(attempt, Mapping):
            continue
        item_id = attempt.get("item_id")
        sequence = attempt.get("attempt_sequence")
        if not isinstance(item_id, str) or not isinstance(sequence, int):
            continue
        current = latest.get(item_id)
        if current is None or sequence > current.get("attempt_sequence", 0):
            latest[item_id] = dict(attempt)
    return latest


def suspicious_productive_pass_item_ids(
    normalized: Mapping[str, Any],
    item_index: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    suspicious: list[str] = []
    for item_id, attempt in _latest_attempts(normalized).items():
        item = item_index.get(item_id, {})
        if item.get("task_type") not in OPEN_PRODUCTIVE_TASK_TYPES:
            continue
        if attempt.get("passed") is not True:
            continue
        if attempt.get("evaluator_type") not in {"MANUAL", "HYBRID"}:
            continue
        response_text = attempt.get("response_text")
        if not isinstance(response_text, str):
            response_text = ""
        if not _contains_linguistic_content(response_text):
            suspicious.append(item_id)
    return sorted(suspicious)


def select_review_item_ids(
    package: Mapping[str, Any],
    projection: Mapping[str, Any],
    normalized: Mapping[str, Any],
    grammar_unit_id: str,
) -> tuple[list[str], list[str], list[str]]:
    item_order = _unit_item_ids(package, grammar_unit_id)
    item_index = _item_index(package)
    unit_projection = projection.get("by_grammar_unit_id", {}).get(
        grammar_unit_id
    )
    if not isinstance(unit_projection, Mapping):
        raise ValueError(
            f"review_projection_unit_missing:{grammar_unit_id}"
        )
    if unit_projection.get("projection_status") != "REVIEW_REQUIRED":
        raise ValueError(
            "review_projection_status_not_review_required:"
            f"{grammar_unit_id}:"
            f"{unit_projection.get('projection_status')}"
        )

    review_reasons = [
        reason
        for reason in unit_projection.get("review_reasons", [])
        if isinstance(reason, str)
    ]
    selected = {
        item_id
        for item_id in unit_projection.get("unresolved_failure_item_ids", [])
        if isinstance(item_id, str)
    }
    suspicious = set(
        suspicious_productive_pass_item_ids(normalized, item_index)
    )
    selected.update(suspicious)

    if "READING_SCORE_BELOW_THRESHOLD" in review_reasons:
        selected.update(
            item_id
            for item_id in item_order
            if item_index[item_id].get("skill") == "reading"
        )
    if "WRITING_SCORE_BELOW_THRESHOLD" in review_reasons:
        selected.update(
            item_id
            for item_id in item_order
            if item_index[item_id].get("skill") == "writing"
        )
    if "READING_ASSESSMENT_NOT_PASSED" in review_reasons:
        selected.update(
            item_id
            for item_id in item_order
            if item_index[item_id].get("skill") == "reading"
            and item_index[item_id].get("item_role") == "assessment"
        )
    if "WRITING_ASSESSMENT_NOT_PASSED" in review_reasons:
        selected.update(
            item_id
            for item_id in item_order
            if item_index[item_id].get("skill") == "writing"
            and item_index[item_id].get("item_role") == "assessment"
        )

    ordered = [item_id for item_id in item_order if item_id in selected]
    if not ordered:
        raise ValueError(
            f"review_required_but_no_review_items_selected:{grammar_unit_id}"
        )
    return ordered, review_reasons, sorted(suspicious)


def find_latest_source_snapshot(
    local_root: Path,
    grammar_unit_id: str,
) -> Path:
    unit_root = local_root / _safe_unit_id(grammar_unit_id)
    if not unit_root.exists():
        raise FileNotFoundError(
            f"review_unit_snapshot_root_not_found:{unit_root}"
        )
    required = {"responses.json", "normalized.json", "projection.json"}
    candidates = [
        path
        for path in unit_root.iterdir()
        if path.is_dir()
        and required.issubset(
            child.name for child in path.iterdir() if child.is_file()
        )
    ]
    if not candidates:
        raise FileNotFoundError(
            f"review_source_snapshot_not_found:{unit_root}"
        )
    return sorted(candidates, key=lambda path: path.name)[-1]


def next_attempt_sequences(
    normalized: Mapping[str, Any],
) -> dict[str, int]:
    return {
        item_id: int(attempt["attempt_sequence"]) + 1
        for item_id, attempt in _latest_attempts(normalized).items()
    }


def build_combined_review_source(
    previous_source: Mapping[str, Any],
    retry_records: list[Mapping[str, Any]],
    *,
    grammar_unit_id: str,
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, Any]:
    session = previous_source.get("session", {})
    if not isinstance(session, Mapping):
        raise ValueError("review_previous_session_not_object")
    learner_ref = session.get("learner_ref")
    operator_ref = session.get("operator_ref")
    if not isinstance(learner_ref, str) or not learner_ref.strip():
        raise ValueError("review_learner_ref_missing")
    if "@" in learner_ref:
        raise ValueError("review_learner_ref_must_be_pseudonymous")
    if not isinstance(operator_ref, str) or not operator_ref.strip():
        raise ValueError("review_operator_ref_missing")

    previous_responses = previous_source.get("responses", [])
    if not isinstance(previous_responses, list) or not previous_responses:
        raise ValueError("review_previous_responses_missing")

    session_id = (
        f"session:A1_REVIEW_{grammar_unit_id}_"
        f"{started_at.strftime('%Y%m%dT%H%M%S')}"
    )
    previous_source_ref = session.get("evidence_source_ref")
    preserved_responses: list[dict[str, Any]] = []
    for source_record in previous_responses:
        if not isinstance(source_record, Mapping):
            raise ValueError("review_previous_response_not_object")
        record = deepcopy(dict(source_record))
        if (
            not record.get("evidence_ref")
            and isinstance(previous_source_ref, str)
            and previous_source_ref.strip()
        ):
            record["evidence_ref"] = (
                f"{previous_source_ref.rstrip('/')}/item/"
                f"{record.get('item_id')}/attempt/"
                f"{record.get('attempt_sequence', 1)}"
            )
        preserved_responses.append(record)

    return {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "session": {
            "session_id": session_id,
            "learner_ref": learner_ref.strip(),
            "operator_ref": operator_ref.strip(),
            "started_at": started_at.isoformat(timespec="seconds"),
            "completed_at": completed_at.isoformat(timespec="seconds"),
            "evidence_source_ref": f"local_private_review://{session_id}",
        },
        "responses": [
            *preserved_responses,
            *[dict(record) for record in retry_records],
        ],
    }


def build_preview_report(
    *,
    grammar_unit_id: str,
    source_snapshot: Path,
    review_item_ids: list[str],
    review_reasons: list[str],
    suspicious_item_ids: list[str],
) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "validation_status": "PASS",
        "execution_status": "REVIEW_SESSION_READY",
        "grammar_unit_id": grammar_unit_id,
        "source_snapshot": str(source_snapshot),
        "review_item_ids": list(review_item_ids),
        "review_item_count": len(review_item_ids),
        "review_reasons": list(review_reasons),
        "evidence_quality_suspicious_item_ids": list(
            suspicious_item_ids
        ),
        "real_learner_evidence_created": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
        "stop_reason": "NONE",
        "next_short_step": NEXT_REVIEW_TASK,
    }


def _output_root(
    local_root: Path,
    grammar_unit_id: str,
    started_at: datetime,
) -> Path:
    stamp = started_at.strftime("%Y%m%dT%H%M%S%z")
    return (
        local_root
        / _safe_unit_id(grammar_unit_id)
        / f"{stamp}_review"
    )


def _write_bundle(
    root: Path,
    *,
    source: Mapping[str, Any],
    evidence: Mapping[str, Any],
    import_report: Mapping[str, Any],
    normalized: Mapping[str, Any],
    intake_report: Mapping[str, Any],
    projection_bundle: Mapping[str, Any],
    review_report: Mapping[str, Any],
) -> None:
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "responses.json", source)
    write_json(root / "evidence.json", evidence)
    write_json(root / "import_report.json", import_report)
    write_json(root / "normalized.json", normalized)
    write_json(root / "intake_report.json", intake_report)
    write_json(root / "projection.json", projection_bundle["artifact"])
    write_json(root / "projection_report.json", projection_bundle["report"])
    write_json(root / "review_report.json", review_report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", required=True)
    parser.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL_ROOT)
    parser.add_argument("--source-snapshot", type=Path, default=None)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)

    paths = [args.local_root]
    if args.source_snapshot is not None:
        paths.append(args.source_snapshot)
    path_errors = [
        error
        for path in paths
        if (error := _private_path_error(path)) is not None
    ]
    if path_errors:
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "validation_status": "FAIL",
                    "errors": path_errors,
                    "stop_reason": "VALIDATION_FAILURE",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    package, package_report = build_package_source()
    if package_report.get("validation_status") != "PASS":
        print(json.dumps(package_report, ensure_ascii=False, indent=2))
        return 1

    try:
        source_snapshot = (
            args.source_snapshot
            if args.source_snapshot is not None
            else find_latest_source_snapshot(args.local_root, args.unit)
        )
        previous_source = load_json(source_snapshot / "responses.json")
        previous_normalized = load_json(
            source_snapshot / "normalized.json"
        )
        previous_projection = load_json(
            source_snapshot / "projection.json"
        )
        review_item_ids, review_reasons, suspicious_item_ids = (
            select_review_item_ids(
                package,
                previous_projection,
                previous_normalized,
                args.unit,
            )
        )
    except (FileNotFoundError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "validation_status": "BLOCKED",
                    "execution_status": "REVIEW_SOURCE_NOT_READY",
                    "errors": [str(exc)],
                    "stop_reason": "REVIEW_EVIDENCE_REQUIRED",
                    "next_short_step": NEXT_REVIEW_TASK,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    preview = build_preview_report(
        grammar_unit_id=args.unit,
        source_snapshot=source_snapshot,
        review_item_ids=review_item_ids,
        review_reasons=review_reasons,
        suspicious_item_ids=suspicious_item_ids,
    )
    if args.preview:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    session = previous_source.get("session", {})
    operator_ref = session.get("operator_ref")
    if not isinstance(operator_ref, str) or not operator_ref.strip():
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "validation_status": "BLOCKED",
                    "execution_status": "OPERATOR_IDENTITY_REQUIRED",
                    "errors": ["review_operator_ref_missing"],
                    "stop_reason": "REAL_LEARNER_EVIDENCE_REQUIRED",
                    "next_short_step": NEXT_REVIEW_TASK,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    item_index = _item_index(package)
    sequences = next_attempt_sequences(previous_normalized)
    started_at = datetime.now().astimezone()

    print()
    print("=" * 72)
    print(f"Targeted review unit: {args.unit}")
    print(f"Items: {len(review_item_ids)}")
    print("Review reasons:", ", ".join(review_reasons))
    if suspicious_item_ids:
        print(
            "Evidence-quality recheck:",
            ", ".join(suspicious_item_ids),
        )
    print("=" * 72)

    retries: list[dict[str, Any]] = []
    for number, item_id in enumerate(review_item_ids, start=1):
        item = item_index[item_id]
        _display_item(item, number, len(review_item_ids))
        record = _collect_response(
            item,
            operator_ref=operator_ref.strip(),
        )
        record["attempt_sequence"] = sequences.get(item_id, 1)
        retries.append(record)

    completed_at = datetime.now().astimezone()
    combined_source = build_combined_review_source(
        previous_source,
        retries,
        grammar_unit_id=args.unit,
        started_at=started_at,
        completed_at=completed_at,
    )
    evidence, import_report, normalized, intake_report, projection_bundle = (
        run_import(combined_source, package=package)
    )

    errors = list(import_report.get("errors", []))
    projection_report = projection_bundle.get("report", {})
    projection = projection_bundle.get("artifact", {})
    unit_projection = projection.get("by_grammar_unit_id", {}).get(
        args.unit, {}
    )
    if import_report.get("validation_status") != "PASS":
        errors.append("review_import_not_pass")
    if intake_report.get("validation_status") != "PASS":
        errors.append("review_intake_not_pass")
    if projection_report.get("validation_status") != "PASS":
        errors.append("review_projection_not_pass")

    status = "PASS" if not errors else "FAIL"
    projection_status = unit_projection.get("projection_status")
    if projection_status == "MASTERY_CANDIDATE_PENDING_RETENTION":
        next_short_step = NEXT_PILOT_TASK
        retention_resume_task = RETENTION_RESUME_TASK
    else:
        next_short_step = NEXT_REVIEW_TASK
        retention_resume_task = None

    review_report = {
        "task_id": TASK_ID,
        "validation_status": status,
        "execution_status": (
            "REVIEW_SESSION_COMPLETED"
            if status == "PASS"
            else "REVIEW_SESSION_FAILED"
        ),
        "grammar_unit_id": args.unit,
        "source_snapshot": str(source_snapshot),
        "review_item_ids": review_item_ids,
        "review_item_count": len(review_item_ids),
        "review_reasons": review_reasons,
        "retry_attempt_count": len(retries),
        "evidence_quality_suspicious_item_ids": suspicious_item_ids,
        "projection_status": projection_status,
        "review_required": projection_status == "REVIEW_REQUIRED",
        "retention_candidate": (
            projection_status == "MASTERY_CANDIDATE_PENDING_RETENTION"
        ),
        "final_mastery_claimed": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
        "errors": errors,
        "stop_reason": (
            "NONE" if status == "PASS" else "VALIDATION_FAILURE"
        ),
        "next_short_step": next_short_step,
        "retention_resume_task": retention_resume_task,
    }

    output_root = _output_root(
        args.local_root,
        args.unit,
        started_at,
    )
    review_report["private_output_root"] = str(output_root)
    if projection_bundle:
        _write_bundle(
            output_root,
            source=combined_source,
            evidence=evidence,
            import_report=import_report,
            normalized=normalized,
            intake_report=intake_report,
            projection_bundle=projection_bundle,
            review_report=review_report,
        )
    else:
        output_root.mkdir(parents=True, exist_ok=False)
        write_json(output_root / "responses.json", combined_source)
        write_json(output_root / "import_report.json", import_report)
        write_json(output_root / "review_report.json", review_report)

    print()
    print(json.dumps(review_report, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
