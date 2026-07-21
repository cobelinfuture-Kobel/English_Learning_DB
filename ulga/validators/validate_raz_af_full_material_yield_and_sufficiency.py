#!/usr/bin/env python3
"""Validate a RAZ A-F full material-yield and sufficiency report."""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
from typing import Any, Mapping, Sequence
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0, str(REPO_ROOT))
from ulga.builders import build_raz_af_full_material_yield_and_sufficiency as builder  # noqa: E402

PASS_STATUS = "PASS_RAZ_AF_FULL_MATERIAL_YIELD_AND_SUFFICIENCY_VALIDATION"
SCHEMA = REPO_ROOT / "ulga/schemas/raz_af_full_material_yield_and_sufficiency.schema.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_af/full_material_yield/validation.safe.json"

def validate_report(report: Mapping[str, Any], *, records=None, query=None, coverage=None, units=None, baselines=None, schema_path: Path = SCHEMA) -> dict[str, Any]:
    schema = builder.read_json(schema_path); errors = [f"schema:{'.'.join(map(str, e.absolute_path))}:{e.message}" for e in Draft202012Validator(schema).iter_errors(report)]
    if report.get("task_id") != builder.TASK_ID: errors.append("task_id_mismatch")
    if report.get("validation_status") != builder.PASS_STATUS: errors.append("builder_status_mismatch")
    if report.get("claim_boundaries") != builder.BOUNDARIES: errors.append("claim_boundaries_mismatch")
    if report.get("thresholds") != builder.THRESHOLDS: errors.append("thresholds_mismatch")
    errors += builder.scan_forbidden(report)
    supplied = report.get("report_sha256"); expected = builder.digest({k: v for k, v in report.items() if k != "report_sha256"})
    if supplied != expected: errors.append("report_sha256_mismatch")
    gate = report.get("sufficiency_gate", {}); decision = gate.get("decision")
    allowed = {"BLOCKED_SOURCE_INTEGRITY", "DEEPEN_AF_SEMANTIC_EXTRACTION_BEFORE_GW", "AF_SUFFICIENT_FOR_CONTENT_POPULATION", "TARGETED_GW_EXPANSION_REQUIRED"}
    if decision not in allowed: errors.append("invalid_decision")
    if gate.get("targeted_gw_expansion_allowed") is not (decision == "TARGETED_GW_EXPANSION_REQUIRED"): errors.append("gw_flag_mismatch")
    if gate.get("af_sufficient_for_content_population") is not (decision == "AF_SUFFICIENT_FOR_CONTENT_POPULATION"): errors.append("af_flag_mismatch")
    if all(x is not None for x in (records, query, coverage, units, baselines)):
        rebuilt = builder.build_report(records, query, coverage, units, baselines, expected_records=report["scope"]["expected_record_count"], expected_books=report["scope"]["expected_book_count"])
        if report != rebuilt: errors.append("deterministic_rebuild_mismatch")
    return {"task_id": builder.TASK_ID, "validation_status": PASS_STATUS if not errors else "FAIL", "error_count": len(errors), "errors": errors, "sufficiency_decision": decision, "g_w_read_performed": report.get("scope", {}).get("g_w_read_performed")}

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("report", type=Path, nargs="?", default=builder.DEFAULT_OUTPUT); parser.add_argument("--s12b-root", type=Path, default=builder.DEFAULT_S12B); parser.add_argument("--s12c-root", type=Path, default=builder.DEFAULT_S12C); parser.add_argument("--learning-units", type=Path, default=builder.DEFAULT_UNITS); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--skip-rebuild", action="store_true"); args = parser.parse_args(argv)
    try:
        report = builder.read_json(args.report); kwargs = {}
        if not args.skip_rebuild:
            kwargs = {"records": builder.load_records(args.s12b_root, builder.read_json(args.s12b_root / "inventory.json")), "query": builder.read_json(args.s12c_root / "query_index.json"), "coverage": builder.read_json(args.s12c_root / "coverage.json"), "units": builder.read_json(args.learning_units), "baselines": builder.load_baselines()}
        result = validate_report(report, **kwargs); builder.write_json(args.output, result); print(json.dumps(result, sort_keys=True)); return 0 if result["error_count"] == 0 else 1
    except (builder.MaterialYieldError, OSError, KeyError, TypeError, ValueError) as exc: print(f"FAIL:{exc}"); return 1

if __name__ == "__main__": raise SystemExit(main())
