#!/usr/bin/env python3
"""Validate the text-free RAZ G-I targeted gap expansion report."""
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

from ulga.builders import build_raz_gi_targeted_gap_source_expansion as builder  # noqa: E402
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "ulga/schemas/raz_gi_targeted_gap_source_expansion.schema.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_gi/targeted_gap_expansion/validation.safe.json"
PASS_STATUS = "PASS_RAZ_GI_TARGETED_GAP_SOURCE_EXPANSION_VALIDATION"


def validate_report(
    report: Mapping[str, Any],
    *,
    rebuilt: Mapping[str, Any] | None = None,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, Any]:
    schema = deep.read_json(schema_path)
    errors = [
        f"schema:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(report),
            key=lambda item: list(item.absolute_path),
        )
    ]
    if report.get("task_id") != builder.TASK_ID:
        errors.append("task_id_mismatch")
    if report.get("validation_status") != builder.PASS_STATUS:
        errors.append("builder_status_mismatch")
    if report.get("claim_boundaries") != builder.CLAIM_BOUNDARIES:
        errors.append("claim_boundaries_mismatch")
    if report.get("thresholds") != builder.THRESHOLDS:
        errors.append("thresholds_mismatch")
    errors.extend(deep.scan_forbidden_safe_keys(report))

    supplied = report.get("report_sha256")
    expected = deep.sha256_value({
        key: value for key, value in report.items() if key != "report_sha256"
    })
    if supplied != expected:
        errors.append("report_sha256_mismatch")

    gate = report.get("sufficiency_gate", {})
    decision = gate.get("decision")
    if decision not in {
        "BLOCKED_SOURCE_INTEGRITY",
        "AI_SUFFICIENT_FOR_CONTENT_POPULATION",
        "TARGETED_JW_EXPANSION_REQUIRED",
    }:
        errors.append("invalid_decision")
    if gate.get("a_i_sufficient_for_content_population") is not (
        decision == "AI_SUFFICIENT_FOR_CONTENT_POPULATION"
    ):
        errors.append("ai_sufficient_flag_mismatch")
    if gate.get("targeted_j_w_expansion_allowed") is not (
        decision == "TARGETED_JW_EXPANSION_REQUIRED"
    ):
        errors.append("targeted_jw_flag_mismatch")
    if decision == "TARGETED_JW_EXPANSION_REQUIRED":
        checks = gate.get("checks", {})
        if not checks.get("source_integrity"):
            errors.append("jw_expansion_without_source_integrity")
        remaining = gate.get("remaining_asset_gap_counts", {})
        weak = gate.get("remaining_weak_units", [])
        if not any(int(value) > 0 for value in remaining.values()) and not weak:
            errors.append("jw_expansion_without_proven_gap")

    if rebuilt is not None and report != rebuilt:
        errors.append("deterministic_rebuild_mismatch")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "decision": decision,
        "j_w_read_performed": report.get("source_scope", {}).get("j_w_read_performed"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, nargs="?", default=builder.DEFAULT_OUTPUT)
    parser.add_argument("--af-root", type=Path, default=builder.DEFAULT_AF_ROOT)
    parser.add_argument("--gi-root", type=Path, default=builder.DEFAULT_GI_ROOT)
    parser.add_argument("--manifest", type=Path, default=builder.DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-rebuild", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = deep.read_json(args.report)
        rebuilt = None
        if not args.skip_rebuild:
            af_records, af_index = builder.load_levels(args.af_root, builder.AF_LEVELS)
            gi_records, gi_index = builder.load_levels(args.gi_root, builder.GI_LEVELS)
            rebuilt = builder.build_report(
                af_records,
                af_index,
                gi_records,
                gi_index,
                deep.load_authorities(),
                deep.load_manifest_grammar_tags(args.manifest),
            )
        result = validate_report(report, rebuilt=rebuilt)
        deep.write_json_atomic(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["error_count"] == 0 else 1
    except (
        builder.TargetedGapError,
        deep.AlignmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
