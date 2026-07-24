#!/usr/bin/env python3
"""Validate deterministic KET99 teacher-delivery/remediation asset intake."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ulga.builders import build_ket99_pku_teacher_delivery_remediation_asset_intake as builder

FAIL_STATUS = "FAIL_KET99_PK_M4A_TEACHER_DELIVERY_REMEDIATION_ASSET_MAINLINE_INTAKE"
REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m4a/teacher_delivery_remediation_asset_intake.validation.json"


def validate_paths(
    *, artifact_path: Path, m4_path: Path, coverage_path: Path
) -> dict:
    artifact = builder.read_json(artifact_path)
    expected = builder.build_artifact(
        builder.read_json(m4_path), builder.read_json(coverage_path)
    )
    errors: list[str] = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    counts = artifact.get("counts", {})
    if counts.get("asset_candidate_count") != counts.get("source_optional_reference_count"):
        errors.append("asset_candidate_source_count_mismatch")
    if (
        counts.get("learning_value_evaluated_count") != 0
        or counts.get("teacher_delivery_activated_count") != 0
        or counts.get("remediation_activated_count") != 0
    ):
        errors.append("unevaluated_intake_activation_boundary_violated")
    if counts.get("private_text_exposure_count") != 0:
        errors.append("private_text_exposure_detected")
    try:
        builder.walk_forbidden(artifact)
    except ValueError as exc:
        errors.append(str(exc))
    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--m4-overlay", type=Path, default=builder.M4_OVERLAY)
    parser.add_argument("--m4-coverage", type=Path, default=builder.M4_COVERAGE)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_paths(
            artifact_path=args.artifact,
            m4_path=args.m4_overlay,
            coverage_path=args.m4_coverage,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {
            "task_id": builder.TASK_ID,
            "validation_status": FAIL_STATUS,
            "error_count": 1,
            "errors": [str(exc)],
            "stop_reason": "VALIDATION_FAILURE",
            "next_short_step": builder.TASK_ID,
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
