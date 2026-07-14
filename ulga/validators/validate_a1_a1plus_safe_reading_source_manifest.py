#!/usr/bin/env python3
"""Validate an operator-exported metadata-only Reading source manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.export_a1_a1plus_safe_reading_source_manifest import (
    SCHEMA_VERSION,
    validate_manifest,
)

TASK_ID = "E4S-A1V1-M04B_SafeReadingSourceManifestValidation"
PASS_STATUS = "PASS_SAFE_READING_SOURCE_MANIFEST"


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("manifest_root_not_object")
    return payload


def build_report(manifest: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_manifest(manifest, require_records=True)
    records = manifest.get("records", [])
    levels = sorted(
        {
            str(record.get("source_level"))
            for record in records
            if isinstance(record, Mapping) and record.get("source_level")
        }
    )
    unsafe_policy_count = 0
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, Mapping):
            unsafe_policy_count += 1
            continue
        policy = record.get("source_policy", {})
        if not isinstance(policy, Mapping) or policy.get("metadata_and_hashes_only") is not True:
            unsafe_policy_count += 1
    status = PASS_STATUS if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "schema_version": manifest.get("schema_version"),
        "expected_schema_version": SCHEMA_VERSION,
        "validation_counts": {
            "record_count": len(records) if isinstance(records, list) else 0,
            "level_count": len(levels),
            "unsafe_policy_count": unsafe_policy_count,
            "error_count": len(errors),
        },
        "levels": levels,
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_resume_task": (
            "E4S-A1V1-M04B_SourceGroundedReadingPracticeBankCompletion"
            if not errors
            else None
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        report = build_report(manifest)
    except Exception as exc:
        report = {
            "task_id": TASK_ID,
            "validation_status": "FAIL",
            "errors": [f"manifest_load_failure:{exc}"],
            "stop_reason": "VALIDATION_FAILURE",
            "next_resume_task": None,
        }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("validation_status") == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
