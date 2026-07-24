#!/usr/bin/env python3
"""Validate deterministic KET99-PK-M5 optional overlay consumer canary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ulga.builders import build_ket99_pku_optional_overlay_consumer_canary as builder

FAIL_STATUS = "FAIL_KET99_PK_M5_OPTIONAL_OVERLAY_CONSUMER_CANARY"
REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m5/optional_overlay_consumer_canary.validation.json"


def validate_paths(*, artifact_path: Path, r3f_path: Path, m4_path: Path) -> dict:
    artifact = builder.read_json(artifact_path)
    expected = builder.build_artifact(
        builder.read_json(r3f_path),
        builder.read_json(m4_path),
    )
    errors = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--r3f", type=Path, default=builder.R3F)
    parser.add_argument("--m4-overlay", type=Path, default=builder.M4)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_paths(
            artifact_path=args.artifact,
            r3f_path=args.r3f,
            m4_path=args.m4_overlay,
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
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
