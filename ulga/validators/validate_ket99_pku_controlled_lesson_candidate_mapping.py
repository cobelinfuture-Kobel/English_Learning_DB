#!/usr/bin/env python3
"""Validate a deterministic KET99-PK-M3 controlled candidate mapping."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ulga.builders import build_ket99_pku_controlled_lesson_candidate_mapping as builder

FAIL_STATUS = "FAIL_KET99_PK_M3_CONTROLLED_LESSON_CANDIDATE_MAPPING"
REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m3/controlled_lesson_candidate_mapping.validation.json"


def validate_paths(*, artifact_path: Path, m1_csv: Path, bridge: Path, consumer: Path, r3g: Path) -> dict:
    artifact = builder.read_json(artifact_path)
    expected = builder.build_artifact(builder.read_json(bridge), builder.read_csv(m1_csv), builder.read_json(consumer), builder.read_json(r3g))
    errors = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    if artifact.get("artifact_sha256") != builder.digest({key: value for key, value in artifact.items() if key != "artifact_sha256"}):
        errors.append("artifact_sha256_invalid")
    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors), "errors": errors,
        "counts": artifact.get("counts", {}),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--m1-csv", type=Path, default=builder.M1_CSV)
    parser.add_argument("--m2-bridge", type=Path, default=builder.M2_BRIDGE)
    parser.add_argument("--m2-consumer", type=Path, default=builder.M2_CONSUMER)
    parser.add_argument("--r3g", type=Path, default=builder.R3G)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_paths(artifact_path=args.artifact, m1_csv=args.m1_csv, bridge=args.m2_bridge, consumer=args.m2_consumer, r3g=args.r3g)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"task_id": builder.TASK_ID, "validation_status": FAIL_STATUS, "error_count": 1, "errors": [str(exc)], "stop_reason": "VALIDATION_FAILURE", "next_short_step": builder.TASK_ID}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
