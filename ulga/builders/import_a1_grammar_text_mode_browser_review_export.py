#!/usr/bin/env python3
"""Merge a browser-exported targeted review with an existing local snapshot.

The browser export may be an explicitly approved anonymous test fixture, but
runtime output remains local-only. This module reuses the canonical importer,
intake, and projection contracts and never claims final mastery.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
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
    _private_path_error,
    run_import,
)
from ulga.builders.run_a1_grammar_text_mode_review_session import (
    NEXT_PILOT_TASK,
    NEXT_REVIEW_TASK,
    RETENTION_RESUME_TASK,
    next_attempt_sequences,
    select_review_item_ids,
)

TASK_ID = "R7-M105R1_BrowserExportReviewImporterIntegrationAndProjection"
DEFAULT_LOCAL_ROOT = REPO_ROOT / ".local/a1_private_pilot_units"


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_browser_export(
    browser_export: Mapping[str, Any],
    *,
    previous_source: Mapping[str, Any],
    previous_normalized: Mapping[str, Any],
    expected_item_ids: list[str],
) -> list[str]:
    errors: list[str] = []
    if browser_export.get("import_schema_version") != IMPORT_SCHEMA_VERSION:
        errors.append("browser_export_schema_version_mismatch")

    session = browser_export.get("session")
    previous_session = previous_source.get("session")
    if not isinstance(session, Mapping):
        errors.append("browser_export_session_not_object")
        session = {}
    if not isinstance(previous_session, Mapping):
        errors.append("previous_session_not_object")
        previous_session = {}

    for field in (
        "session_id",
        "learner_ref",
        "operator_ref",
        "started_at",
        "completed_at",
        "evidence_source_ref",
    ):
        if not _nonempty(session.get(field)):
            errors.append(f"browser_export_session_field_missing:{field}")

    learner_ref = session.get("learner_ref")
    if isinstance(learner_ref, str) and "@" in learner_ref:
        errors.append("browser_export_learner_ref_must_be_pseudonymous")
    for field in ("learner_ref", "operator_ref"):
        if session.get(field) != previous_session.get(field):
            errors.append(f"browser_export_identity_mismatch:{field}")

    responses = browser_export.get("responses")
    if not isinstance(responses, list):
        return [*errors, "browser_export_responses_not_array"]
    actual_ids = [
        record.get("item_id")
        for record in responses
        if isinstance(record, Mapping)
    ]
    if len(actual_ids) != len(set(actual_ids)):
        errors.append("browser_export_duplicate_item_id")
    if actual_ids != expected_item_ids:
        errors.append(
            "browser_export_review_item_set_mismatch:"
            f"expected={','.join(expected_item_ids)}:actual={','.join(str(v) for v in actual_ids)}"
        )

    expected_sequences = next_attempt_sequences(previous_normalized)
    for index, record in enumerate(responses):
        if not isinstance(record, Mapping):
            errors.append(f"browser_export_response_not_object:{index}")
            continue
        item_id = record.get("item_id")
        expected_sequence = expected_sequences.get(str(item_id), 1)
        if record.get("attempt_sequence") != expected_sequence:
            errors.append(
                f"browser_export_attempt_sequence_mismatch:{item_id}:"
                f"expected={expected_sequence}:actual={record.get('attempt_sequence')}"
            )
    return errors


def build_combined_source(
    previous_source: Mapping[str, Any],
    browser_export: Mapping[str, Any],
) -> dict[str, Any]:
    previous_responses = previous_source.get("responses")
    browser_responses = browser_export.get("responses")
    if not isinstance(previous_responses, list) or not previous_responses:
        raise ValueError("previous_responses_missing")
    if not isinstance(browser_responses, list) or not browser_responses:
        raise ValueError("browser_export_responses_missing")
    return {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "session": deepcopy(dict(browser_export["session"])),
        "responses": [
            *[deepcopy(dict(record)) for record in previous_responses],
            *[deepcopy(dict(record)) for record in browser_responses],
        ],
    }


def run_browser_review_import(
    *,
    grammar_unit_id: str,
    previous_source: Mapping[str, Any],
    previous_normalized: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
    browser_export: Mapping[str, Any],
    package: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if package is None:
        package, package_report = build_package_source()
        if package_report.get("validation_status") != "PASS":
            return {}, {
                "task_id": TASK_ID,
                "validation_status": "FAIL",
                "errors": ["package_validation_failed"],
            }

    review_item_ids, review_reasons, suspicious = select_review_item_ids(
        package,
        previous_projection,
        previous_normalized,
        grammar_unit_id,
    )
    errors = validate_browser_export(
        browser_export,
        previous_source=previous_source,
        previous_normalized=previous_normalized,
        expected_item_ids=review_item_ids,
    )
    if errors:
        return {}, {
            "task_id": TASK_ID,
            "validation_status": "FAIL",
            "grammar_unit_id": grammar_unit_id,
            "review_item_ids": review_item_ids,
            "errors": errors,
            "stop_reason": "VALIDATION_FAILURE",
            "next_short_step": NEXT_REVIEW_TASK,
        }

    combined_source = build_combined_source(previous_source, browser_export)
    evidence, import_report, normalized, intake_report, projection_bundle = run_import(
        combined_source,
        package=package,
    )
    projection = projection_bundle.get("artifact", {})
    projection_report = projection_bundle.get("report", {})
    unit_projection = projection.get("by_grammar_unit_id", {}).get(
        grammar_unit_id, {}
    )
    errors = list(import_report.get("errors", []))
    if import_report.get("validation_status") != "PASS":
        errors.append("browser_review_import_not_pass")
    if intake_report.get("validation_status") != "PASS":
        errors.append("browser_review_intake_not_pass")
    if projection_report.get("validation_status") != "PASS":
        errors.append("browser_review_projection_not_pass")

    projection_status = unit_projection.get("projection_status")
    retention_candidate = projection_status == "MASTERY_CANDIDATE_PENDING_RETENTION"
    report = {
        "task_id": TASK_ID,
        "validation_status": "PASS" if not errors else "FAIL",
        "execution_status": (
            "BROWSER_REVIEW_IMPORTED_AND_PROJECTED"
            if not errors
            else "BROWSER_REVIEW_IMPORT_FAILED"
        ),
        "grammar_unit_id": grammar_unit_id,
        "review_item_ids": review_item_ids,
        "review_item_count": len(review_item_ids),
        "review_reasons": review_reasons,
        "evidence_quality_suspicious_item_ids": suspicious,
        "browser_retry_attempt_count": len(browser_export.get("responses", [])),
        "projection_status": projection_status,
        "review_required": projection_status == "REVIEW_REQUIRED",
        "retention_candidate": retention_candidate,
        "final_mastery_claimed": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": NEXT_PILOT_TASK if retention_candidate else NEXT_REVIEW_TASK,
        "retention_resume_task": RETENTION_RESUME_TASK if retention_candidate else None,
    }
    return {
        "combined_source": combined_source,
        "evidence": evidence,
        "import_report": import_report,
        "normalized": normalized,
        "intake_report": intake_report,
        "projection": projection,
        "projection_report": projection_report,
    }, report


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", required=True)
    parser.add_argument("--browser-export", type=Path, required=True)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    path_errors = [
        error
        for path in (args.browser_export, args.source_snapshot, args.local_root)
        if (error := _private_path_error(path)) is not None
    ]
    if path_errors:
        print(json.dumps({"task_id": TASK_ID, "validation_status": "FAIL", "errors": path_errors}, indent=2))
        return 2

    package, package_report = build_package_source()
    if package_report.get("validation_status") != "PASS":
        print(json.dumps(package_report, ensure_ascii=False, indent=2))
        return 1
    try:
        previous_source = load_json(args.source_snapshot / "responses.json")
        previous_normalized = load_json(args.source_snapshot / "normalized.json")
        previous_projection = load_json(args.source_snapshot / "projection.json")
        browser_export = load_json(args.browser_export)
        bundle, report = run_browser_review_import(
            grammar_unit_id=args.unit,
            previous_source=previous_source,
            previous_normalized=previous_normalized,
            previous_projection=previous_projection,
            browser_export=browser_export,
            package=package,
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(json.dumps({"task_id": TASK_ID, "validation_status": "BLOCKED", "errors": [str(exc)]}, indent=2))
        return 2

    if report.get("validation_status") == "PASS" and not args.dry_run:
        session_id = str(browser_export["session"]["session_id"])
        output_root = args.local_root / _safe(args.unit) / f"{_safe(session_id)}_browser_review"
        output_root.mkdir(parents=True, exist_ok=False)
        for filename, key in (
            ("responses.json", "combined_source"),
            ("evidence.json", "evidence"),
            ("import_report.json", "import_report"),
            ("normalized.json", "normalized"),
            ("intake_report.json", "intake_report"),
            ("projection.json", "projection"),
            ("projection_report.json", "projection_report"),
        ):
            write_json(output_root / filename, bundle[key])
        report["private_output_root"] = str(output_root)
        write_json(output_root / "review_report.json", report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("validation_status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
