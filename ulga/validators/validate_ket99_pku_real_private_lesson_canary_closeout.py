#!/usr/bin/env python3
"""Validate deterministic KET99-PK-M6 real private canary closeout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ulga.builders import build_ket99_pku_real_private_lesson_canary_closeout as builder

FAIL_STATUS = "FAIL_KET99_PK_M6_REAL_PRIVATE_LESSON_CANARY_CLOSEOUT"
REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m6/real_private_lesson_canary.validation.json"


def validate_paths(*, artifact_path: Path, m5_path: Path) -> dict:
    artifact = builder.read_json(artifact_path)
    expected = builder.build_artifact(builder.read_json(m5_path))
    errors = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    unsigned = dict(artifact)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != builder.digest(unsigned):
        errors.append("artifact_sha256_invalid")
    return {
        "task_id": builder.TASK_ID,
        "validation_status": (
            artifact.get("validation_status") if not errors else FAIL_STATUS
        ),
        "error_count": len(errors),
        "errors": errors,
        "pilot_closeout": artifact.get("pilot_closeout", {}),
        "stop_reason": (
            artifact.get("stop_reason") if not errors else "VALIDATION_FAILURE"
        ),
        "next_short_step": (
            artifact.get("next_short_step") if not errors else builder.TASK_ID
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--m5", type=Path, default=builder.M5)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_paths(
            artifact_path=args.artifact,
            m5_path=args.m5,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {
            "task_id": builder.TASK_ID,
            "validation_status": FAIL_STATUS,
            "error_count": 1,
            "errors": [str(exc)],
            "pilot_closeout": {"closeout_allowed": False},
            "stop_reason": "VALIDATION_FAILURE",
            "next_short_step": builder.TASK_ID,
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
