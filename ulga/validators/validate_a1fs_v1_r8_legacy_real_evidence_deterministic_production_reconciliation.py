#!/usr/bin/env python3
"""Independent validator for the legacy-real-evidence production reconciliation."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation as reconciliation
from ulga.validators import validate_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5_validator


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_not_object:{path}")
    return value


def validate(
    *, source_bank_path: Path, resolved_root: Path, m12e1_root: Path,
    consumer_path: Path, graph_path: Path, current_bank_path: Path,
    current_supply_path: Path, output_root: Path, mode: str = "project",
) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(output_root)
    report_path = root / reconciliation.REPORT_NAME
    try:
        actual_report = _read(report_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "validation_status": "FAIL_A1FS_V1_R8_LEGACY_REAL_EVIDENCE_RECONCILIATION_VALIDATION",
            "error_count": 1,
            "errors": [f"report_unreadable:{exc}"],
        }
    core = {key: value for key, value in actual_report.items() if key != "report_sha256"}
    if actual_report.get("report_sha256") != r5.digest(core):
        errors.append("report_digest_invalid")
    rebuild = root.parent / f".{root.name}.validation_rebuild"
    shutil.rmtree(rebuild, ignore_errors=True)
    try:
        expected = reconciliation.reconcile(
            source_bank_path=source_bank_path,
            resolved_root=resolved_root,
            m12e1_root=m12e1_root,
            consumer_path=consumer_path,
            graph_path=graph_path,
            current_bank_path=current_bank_path,
            current_supply_path=current_supply_path,
            output_root=rebuild,
            mode=mode,
        )["report"]
        if actual_report != expected:
            errors.append("report_rebuild_drift")
        if mode == "project" and expected.get("validation_status") == reconciliation.PROJECTED_STATUS:
            for name in (
                reconciliation.PACKAGE_NAME,
                reconciliation.SAFE_NAME,
                reconciliation.JSONL_NAME,
            ):
                if (root / name).read_bytes() != (rebuild / name).read_bytes():
                    errors.append(f"export_rebuild_drift:{name}")
            export_validation = r5_validator.validate_exports(
                root / reconciliation.PACKAGE_NAME,
                root / reconciliation.SAFE_NAME,
                root / reconciliation.JSONL_NAME,
            )
            if export_validation.get("error_count") != 0:
                errors.extend(f"r5_export:{row}" for row in export_validation.get("errors", []))
            package = _read(root / reconciliation.PACKAGE_NAME)
            safe = _read(root / reconciliation.SAFE_NAME)
            if package.get("database_binding_type") != "LEGACY_COMPATIBILITY_PROJECTION_RECEIPT":
                errors.append("projection_binding_type_invalid")
            if package.get("projection_binding") != safe.get("projection_binding"):
                errors.append("private_safe_projection_binding_drift")
            entries = package.get("entries", [])
            if any(row.get("telemetry_status") != "NOT_CAPTURED_LEGACY_ZERO_FILLED" for row in entries):
                errors.append("legacy_telemetry_status_missing")
            if any(row.get("compatibility_projection", {}).get("mapping_basis") != "EXACT_M2_ASSET_M1_NODE_AND_NORMALIZED_CONTRACT" for row in entries):
                errors.append("mapping_basis_invalid")
    except Exception as exc:  # independent validator must report, not mask, rebuild failures
        errors.append(f"rebuild_failed:{exc}")
    finally:
        shutil.rmtree(rebuild, ignore_errors=True)
    boundaries = actual_report.get("claim_boundaries", {})
    expected_false = (
        "legacy_outcomes_modified", "new_learner_evidence_created",
        "learner_mastery_claimed", "retention_confirmed", "a2_unlocked",
        "public_delivery", "audio_or_recording_processed",
    )
    for key in expected_false:
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_broken:{key}")
    if boundaries.get("compatibility_projection_only") is not True:
        errors.append("compatibility_projection_boundary_missing")
    return {
        "validation_status": (
            reconciliation.PROJECTED_STATUS
            if not errors and actual_report.get("validation_status") == reconciliation.PROJECTED_STATUS
            else reconciliation.READY_STATUS
            if not errors and actual_report.get("validation_status") == reconciliation.READY_STATUS
            else "FAIL_A1FS_V1_R8_LEGACY_REAL_EVIDENCE_RECONCILIATION_VALIDATION"
        ),
        "error_count": len(errors),
        "errors": errors,
        "legacy_real_attempt_count": actual_report.get("counts", {}).get("legacy_real_attempt_count", 0),
        "exact_mapped_attempt_count": actual_report.get("counts", {}).get("exact_mapped_attempt_count", 0),
        "mapped_breadth_cell_count": actual_report.get("counts", {}).get("mapped_breadth_cell_count", 0),
        "stop_reason": actual_report.get("stop_reason"),
        "next_short_step": actual_report.get("next_short_step"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("inspect", "project"))
    parser.add_argument("--source-bank", type=Path, required=True)
    parser.add_argument("--resolved-root", type=Path, required=True)
    parser.add_argument("--m12e1-root", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--current-bank", type=Path, required=True)
    parser.add_argument("--current-supply", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = validate(
        source_bank_path=args.source_bank,
        resolved_root=args.resolved_root,
        m12e1_root=args.m12e1_root,
        consumer_path=args.consumer,
        graph_path=args.graph,
        current_bank_path=args.current_bank,
        current_supply_path=args.current_supply,
        output_root=args.output_root,
        mode=args.mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
