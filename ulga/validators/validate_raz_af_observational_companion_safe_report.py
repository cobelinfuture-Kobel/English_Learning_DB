#!/usr/bin/env python3
"""Fail-closed validation for the S12A observational companion safe index."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_raz_af_observational_companion_inventory import (  # noqa: E402
    CURRENT_CONSUMER_ID,
    EXPECTED_BOOK_COUNT,
    EXPECTED_LEVELS,
    EXPECTED_PAGE_UNIT_COUNT,
    EXPECTED_SELECTED_SOURCE_COUNT,
    PASS_STATUS,
    SAFE_INDEX_SCHEMA,
    SOURCE_REF_RE,
    TASK_ID,
    _canonical_json,
    _format_schema_errors,
    _schema_validators,
    _sha256_text,
    scan_forbidden_safe_fields,
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _schema_errors(payload: Mapping[str, Any]) -> list[str]:
    _, safe_index_validator = _schema_validators()
    return _format_schema_errors(safe_index_validator, payload, "schema")


def _record_accounting(records: list[Any]) -> dict[str, Any]:
    levels: Counter[str] = Counter()
    books: set[tuple[str, str]] = set()
    refs: dict[str, tuple[Any, ...]] = {}
    duplicate_count = 0
    conflict_count = 0
    errors: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            errors.append(f"record:{index}:not_object")
            continue
        source_ref = record.get("source_unit_ref")
        source_level = record.get("source_level")
        source_book_id = record.get("source_book_id")
        source_page_number = record.get("source_page_number")
        if isinstance(source_level, str):
            levels[source_level] += 1
        if isinstance(source_level, str) and isinstance(source_book_id, str):
            books.add((source_level, source_book_id))
        identity = (
            source_level,
            source_book_id,
            source_page_number,
            record.get("source_content_sha256"),
            record.get("source_record_sha256"),
        )
        if isinstance(source_ref, str) and source_ref in refs:
            duplicate_count += 1
            if refs[source_ref] != identity:
                conflict_count += 1
        elif isinstance(source_ref, str):
            refs[source_ref] = identity
        expected_id = f"RAZ_AF_OBS_V1__{source_ref}"
        if record.get("observational_record_id") != expected_id:
            errors.append(f"record:{index}:observational_record_id_not_deterministic")
        ref_match = SOURCE_REF_RE.fullmatch(source_ref) if isinstance(source_ref, str) else None
        if ref_match is None:
            errors.append(f"record:{index}:source_unit_ref_malformed")
            continue
        if ref_match.group(1) != source_level:
            errors.append(f"record:{index}:source_unit_ref_level_mismatch")
        if ref_match.group(2) != source_book_id:
            errors.append(f"record:{index}:source_unit_ref_book_mismatch")
        if not isinstance(source_page_number, int) or isinstance(source_page_number, bool):
            errors.append(f"record:{index}:source_page_number_invalid")
        elif int(ref_match.group(3)) != source_page_number:
            errors.append(f"record:{index}:source_unit_ref_page_mismatch")
    return {
        "record_count": len(records),
        "levels": sorted(levels),
        "level_counts": {level: levels[level] for level in EXPECTED_LEVELS},
        "represented_book_count": len(books),
        "duplicate_source_unit_ref_count": duplicate_count,
        "conflicting_source_unit_ref_count": conflict_count,
        "errors": errors,
    }


def validate_safe_index(
    payload: Mapping[str, Any],
    *,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
    expected_levels: tuple[str, ...] = EXPECTED_LEVELS,
    expected_current_consumer_counts: tuple[int, int, int] = (
        EXPECTED_SELECTED_SOURCE_COUNT,
        EXPECTED_SELECTED_SOURCE_COUNT,
        0,
    ),
) -> dict[str, Any]:
    errors = _schema_errors(payload)
    if payload.get("task_id") != TASK_ID:
        errors.append("task_id_mismatch")
    if payload.get("schema_version") != SAFE_INDEX_SCHEMA:
        errors.append("safe_index_schema_mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
        records = []
    accounting = _record_accounting(records)
    errors.extend(accounting["errors"])
    if accounting["record_count"] != expected_page_unit_count:
        errors.append(
            f"actual_record_count:expected={expected_page_unit_count}:actual={accounting['record_count']}"
        )
    if accounting["represented_book_count"] != expected_book_count:
        errors.append(
            f"actual_represented_book_count:expected={expected_book_count}:"
            f"actual={accounting['represented_book_count']}"
        )
    if accounting["levels"] != sorted(expected_levels):
        errors.append(
            f"actual_levels:expected={sorted(expected_levels)}:actual={accounting['levels']}"
        )
    if accounting["duplicate_source_unit_ref_count"]:
        errors.append(
            f"actual_duplicate_source_unit_ref_count:{accounting['duplicate_source_unit_ref_count']}"
        )
    if accounting["conflicting_source_unit_ref_count"]:
        errors.append(
            f"actual_conflicting_source_unit_ref_count:{accounting['conflicting_source_unit_ref_count']}"
        )
    if payload.get("records_sha256") != _sha256_text(_canonical_json(records)):
        errors.append("records_sha256_mismatch")

    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    derived_summary = {
        "discovered_level_count": len(accounting["levels"]),
        "discovered_levels": accounting["levels"],
        "discovered_page_unit_count": accounting["record_count"],
        "represented_book_count": accounting["represented_book_count"],
        "page_unit_counts_by_level": accounting["level_counts"],
        "duplicate_source_unit_ref_count": accounting["duplicate_source_unit_ref_count"],
        "conflicting_source_unit_ref_count": accounting["conflicting_source_unit_ref_count"],
    }
    for key, actual in derived_summary.items():
        if summary.get(key) != actual:
            errors.append(f"summary:{key}:derived={actual!r}:declared={summary.get(key)!r}")
    zero_summary = {
        "source_record_mutation_count": 0,
        "source_content_hash_drift_count": 0,
        "source_record_hash_drift_count": 0,
    }
    for key, expected in zero_summary.items():
        if summary.get(key) != expected:
            errors.append(f"summary:{key}:expected={expected}:actual={summary.get(key)!r}")
    compatibility = payload.get("consumer_compatibility")
    if not isinstance(compatibility, list):
        compatibility = []
    consumer_ids: set[str] = set()
    current_consumer_entries: list[Mapping[str, Any]] = []
    for index, consumer in enumerate(compatibility):
        if not isinstance(consumer, Mapping):
            continue
        consumer_id = str(consumer.get("consumer_id", ""))
        if consumer_id in consumer_ids:
            errors.append(f"consumer_compatibility:{index}:duplicate_consumer_id")
        consumer_ids.add(consumer_id)
        if consumer_id == CURRENT_CONSUMER_ID:
            current_consumer_entries.append(consumer)
        source_count = consumer.get("source_ref_count")
        resolved_count = consumer.get("resolvable_source_ref_count")
        unresolved_count = consumer.get("unresolved_source_ref_count")
        if all(isinstance(value, int) and not isinstance(value, bool) for value in (
            source_count, resolved_count, unresolved_count
        )):
            if source_count != resolved_count + unresolved_count:
                errors.append(f"consumer_compatibility:{index}:resolution_count_mismatch")
            if payload.get("validation_status") == PASS_STATUS and unresolved_count != 0:
                errors.append(f"consumer_compatibility:{index}:pass_with_unresolved_sources")
    if len(current_consumer_entries) != 1:
        errors.append(f"current_consumer_entry_count:expected=1:actual={len(current_consumer_entries)}")
    else:
        current = current_consumer_entries[0]
        declared_counts = (
            current.get("source_ref_count"),
            current.get("resolvable_source_ref_count"),
            current.get("unresolved_source_ref_count"),
        )
        if declared_counts != expected_current_consumer_counts:
            errors.append(
                f"current_consumer_counts:expected={expected_current_consumer_counts}:actual={declared_counts}"
            )

    text_count, payload_count, scan_errors = scan_forbidden_safe_fields(payload)
    errors.extend(scan_errors)
    for key, actual in (
        ("source_text_field_count", text_count),
        ("forbidden_payload_field_count", payload_count),
    ):
        if summary.get(key) != actual:
            errors.append(f"summary:{key}:derived={actual}:declared={summary.get(key)!r}")
        if actual:
            errors.append(f"{key}_actual:{actual}")
    boundaries = payload.get("claim_boundaries") if isinstance(payload.get("claim_boundaries"), Mapping) else {}
    if boundaries.get("metadata_and_hashes_only") is not True:
        errors.append("metadata_and_hashes_only_boundary_missing")
    for key in (
        "raw_source_text_included", "source_payload_copied", "semantic_extraction_performed",
        "authority_import_allowed", "learner_facing_original_text_allowed",
        "canonical_graph_write_performed", "source_files_rewritten",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"false_boundary_invalid:{key}")
    if payload.get("validation_status") != PASS_STATUS:
        errors.append("safe_index_execution_not_pass")
    if payload.get("errors") != []:
        errors.append("safe_index_contains_execution_errors")
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "discovered_page_unit_count": len(records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the text-free S12A companion safe index.")
    parser.add_argument(
        "--safe-report",
        type=Path,
        default=REPO_ROOT / ".local/raz_af/observational_companion_safe_index.json",
    )
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = _load_json(args.safe_report)
        if not isinstance(payload, Mapping):
            raise ValueError("safe_report_not_object")
        report = validate_safe_index(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "task_id": TASK_ID,
            "validation_status": "FAIL",
            "error_count": 1,
            "errors": [f"safe_report_unreadable:{exc}"],
            "discovered_page_unit_count": 0,
        }
    if args.validation_report:
        args.validation_report.parent.mkdir(parents=True, exist_ok=True)
        args.validation_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
