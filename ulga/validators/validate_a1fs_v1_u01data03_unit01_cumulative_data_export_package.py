#!/usr/bin/env python3
"""Validate Unit01 cumulative JSON/CSV workbook-source export package."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.exporters import export_a1fs_v1_u01data03_unit01_cumulative_data_package as exporter

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates the one-way Unit01 JSON and CSV export package; no content, question, answer, scoring, learner state, audio, A2 target, canonical write, or parallel curriculum is created."
PASS_STATUS = "PASS_A1FS_V1_U01DATA03_UNIT01_CUMULATIVE_DATA_EXPORT_PACKAGE_VALIDATION"
FORBIDDEN_KEYS = frozenset({"prompt", "correct_answer", "acceptable_variants", "explanation", "response_contract", "options", "stimulus", "learner_id", "score"})
EXPECTED_COUNTS = {"summary": 19, "assets": 91, "contexts": 5, "sentences": 18, "activities": 24}


class ExportValidationError(ValueError):
    pass


def forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(FORBIDDEN_KEYS & set(value)) or any(forbidden(child) for child in value.values())
    if isinstance(value, list):
        return any(forbidden(child) for child in value)
    return False


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def validate_package(package: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    def check(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)
    check(package.get("schema_version") == exporter.SCHEMA_VERSION, "schema_version_invalid")
    check(package.get("program_id") == exporter.PROGRAM_ID, "program_id_invalid")
    check(package.get("task_id") == exporter.TASK_ID, "task_id_invalid")
    check(package.get("status") == exporter.PASS_STATUS, "status_invalid")
    check(package.get("unit_id") == exporter.UNIT_ID, "unit_id_invalid")
    authority = package.get("authority_contract") or {}
    check(authority.get("json_is_authority") is True, "json_authority_invalid")
    check(authority.get("csv_and_excel_are_one_way_exports") is True, "one_way_export_invalid")
    check(authority.get("excel_writeback_allowed") is False, "excel_writeback_forbidden")
    check(authority.get("stable_ids_preserved") is True, "stable_ids_not_preserved")
    check(authority.get("question_or_answer_payload_exported") is False, "question_answer_export_forbidden")
    tables = package.get("tables") or {}
    counts = package.get("table_counts") or {}
    for key, expected in EXPECTED_COUNTS.items():
        check(counts.get(key) == expected and len(tables.get(key) or []) == expected, f"table_count_invalid:{key}")
    check(counts.get("activity_asset_links", 0) > 0, "activity_asset_links_missing")
    check(counts.get("external_support", 0) > 0, "external_support_missing")
    asset_ids = [row.get("binding_id") for row in tables.get("assets", [])]
    check(len(asset_ids) == len(set(asset_ids)) == 91 and all(asset_ids), "asset_binding_ids_invalid")
    context_ids = {row.get("context_id") for row in tables.get("contexts", [])}
    sentence_ids = {row.get("sentence_id") for row in tables.get("sentences", [])}
    activity_ids = {row.get("activity_id") for row in tables.get("activities", [])}
    check(len(context_ids) == 5 and None not in context_ids, "context_ids_invalid")
    check(len(sentence_ids) == 18 and None not in sentence_ids, "sentence_ids_invalid")
    check(len(activity_ids) == 24 and None not in activity_ids, "activity_ids_invalid")
    check(all(row.get("context_id") in context_ids for row in tables.get("sentences", [])), "sentence_context_invalid")
    check(all(row.get("context_id") in context_ids for row in tables.get("activities", [])), "activity_context_invalid")
    check(all(row.get("activity_id") in activity_ids and row.get("binding_id") in set(asset_ids) for row in tables.get("activity_asset_links", [])), "activity_asset_link_invalid")
    check(all(row.get("promotion_status") == "NOT_PROMOTED_TO_U01DATA01_REGISTRY" for row in tables.get("external_support", [])), "external_support_promotion_invalid")
    spec = package.get("workbook_spec") or {}
    check(spec.get("json_is_authority") is True and spec.get("excel_is_one_way_export") is True and spec.get("excel_writeback_allowed") is False, "workbook_authority_policy_invalid")
    check(len(spec.get("sheets") or []) == 7, "workbook_sheet_count_invalid")
    check([row.get("sheet_name") for row in spec.get("sheets", [])] == spec.get("sheet_order"), "workbook_sheet_order_invalid")
    check(spec.get("snapshot_sha256") == package.get("snapshot_sha256"), "workbook_snapshot_digest_mismatch")
    check(not forbidden(package), "forbidden_content_keys")
    check(all(value is False for value in (package.get("boundaries") or {}).values()), "boundary_drift")
    unsigned = dict(package); unsigned.pop("snapshot_sha256", None); unsigned.pop("workbook_spec", None)
    check(package.get("snapshot_sha256") == exporter.digest(unsigned), "snapshot_digest_invalid")
    check(package.get("next_short_step") == exporter.NEXT_SHORT_STEP, "next_short_step_invalid")
    if errors:
        raise ExportValidationError(";".join(errors))
    return {"validation_status": PASS_STATUS, "unit_id": exporter.UNIT_ID, "snapshot_sha256": package["snapshot_sha256"], "table_counts": dict(counts), "workbook_sheet_count": len(spec["sheets"]), "next_short_step": exporter.NEXT_SHORT_STEP}


def validate_materialized(output_dir: Path) -> dict[str, Any]:
    snapshot = json.loads((output_dir / exporter.SNAPSHOT_NAME).read_text(encoding="utf-8"))
    spec = json.loads((output_dir / exporter.WORKBOOK_SPEC_NAME).read_text(encoding="utf-8"))
    package = dict(snapshot); package["workbook_spec"] = spec
    result = validate_package(package)
    for key, file_name in exporter.FILE_NAMES.items():
        headers, rows = read_csv(output_dir / file_name)
        expected_rows = package["tables"][key]
        if len(rows) != len(expected_rows):
            raise ExportValidationError(f"materialized_csv_row_count_invalid:{key}")
        expected_headers = list(expected_rows[0]) if expected_rows else []
        if headers != expected_headers:
            raise ExportValidationError(f"materialized_csv_headers_invalid:{key}")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_materialized(args.output_dir.resolve())
    except (OSError, json.JSONDecodeError, csv.Error, ExportValidationError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA03_UNIT01_CUMULATIVE_DATA_EXPORT_PACKAGE_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['validation_status']}")
    print(f"UNIT={result['unit_id']}")
    print(f"WORKBOOK_SHEETS={result['workbook_sheet_count']}")
    for key, value in result["table_counts"].items():
        print(f"{key.upper()}_ROWS={value}")
    print(f"SNAPSHOT_SHA256={result['snapshot_sha256']}")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
