#!/usr/bin/env python3
"""Validate the text-free RAZ A-F deep semantic/material alignment report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_raz_af_deep_semantic_material_alignment as builder  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "ulga/schemas/raz_af_deep_semantic_material_alignment.schema.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_af/deep_semantic_alignment/validation.safe.json"
PASS_STATUS = "PASS_RAZ_AF_DEEP_SEMANTIC_MATERIAL_ALIGNMENT_VALIDATION"


def schema_errors(report: Mapping[str, Any], schema_path: Path = SCHEMA_PATH) -> list[str]:
    schema = builder.read_json(schema_path)
    return [
        f"schema:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(report),
            key=lambda item: list(item.absolute_path),
        )
    ]


def validate_report(
    report: Mapping[str, Any],
    *,
    rebuilt: Mapping[str, Any] | None = None,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, Any]:
    errors = schema_errors(report, schema_path)
    if report.get("task_id") != builder.TASK_ID:
        errors.append("task_id_mismatch")
    if report.get("validation_status") != builder.PASS_STATUS:
        errors.append("builder_status_mismatch")
    if report.get("claim_boundaries") != builder.CLAIM_BOUNDARIES:
        errors.append("claim_boundaries_mismatch")
    if report.get("thresholds") != builder.THRESHOLDS:
        errors.append("thresholds_mismatch")
    errors.extend(builder.scan_forbidden_safe_keys(report))

    supplied = report.get("report_sha256")
    expected = builder.sha256_value({
        key: value for key, value in report.items() if key != "report_sha256"
    })
    if supplied != expected:
        errors.append("report_sha256_mismatch")

    gate = report.get("sufficiency_gate", {})
    decision = gate.get("decision")
    allowed = {
        "BLOCKED_SOURCE_INTEGRITY",
        "DEEPEN_AF_SEMANTIC_EXTRACTION_BEFORE_GW",
        "AF_SUFFICIENT_FOR_CONTENT_POPULATION",
        "TARGETED_GW_EXPANSION_REQUIRED",
    }
    if decision not in allowed:
        errors.append("invalid_sufficiency_decision")
    if gate.get("targeted_gw_expansion_allowed") is not (
        decision == "TARGETED_GW_EXPANSION_REQUIRED"
    ):
        errors.append("targeted_gw_flag_mismatch")
    if gate.get("af_sufficient_for_content_population") is not (
        decision == "AF_SUFFICIENT_FOR_CONTENT_POPULATION"
    ):
        errors.append("af_sufficient_flag_mismatch")

    checks = gate.get("checks", {})
    if decision == "AF_SUFFICIENT_FOR_CONTENT_POPULATION" and not all(checks.values()):
        errors.append("af_sufficient_without_all_checks")
    if decision == "TARGETED_GW_EXPANSION_REQUIRED":
        if not checks.get("source_integrity"):
            errors.append("gw_expansion_without_source_integrity")
        if not checks.get("semantic_alignment_complete"):
            errors.append("gw_expansion_before_af_semantic_completion")

    if rebuilt is not None and report != rebuilt:
        errors.append("deterministic_rebuild_mismatch")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "decision": decision,
        "g_w_read_performed": report.get("source_scope", {}).get("g_w_read_performed"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, nargs="?", default=builder.DEFAULT_OUTPUT)
    parser.add_argument("--source-root", type=Path, default=builder.DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=builder.DEFAULT_MANIFEST)
    parser.add_argument("--learning-units", type=Path, default=builder.DEFAULT_UNITS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-rebuild", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = builder.read_json(args.report)
        rebuilt = None
        if not args.skip_rebuild:
            page_units, file_index = builder.load_page_units(args.source_root)
            rebuilt = builder.build_report(
                page_units,
                file_index,
                builder.load_manifest_grammar_tags(args.manifest),
                builder.load_authorities(),
                builder.read_json(args.learning_units),
            )
        result = validate_report(report, rebuilt=rebuilt)
        builder.write_json_atomic(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["error_count"] == 0 else 1
    except (builder.AlignmentError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
