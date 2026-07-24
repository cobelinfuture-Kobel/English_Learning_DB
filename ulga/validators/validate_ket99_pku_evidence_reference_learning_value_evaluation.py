#!/usr/bin/env python3
"""Validate deterministic KET99 M4B current-material learning-value evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_evidence_reference_learning_value_evaluation as builder

FAIL_STATUS = "FAIL_KET99_PK_M4B_EVIDENCE_REFERENCE_LEARNING_VALUE_EVALUATION"
DEFAULT_REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m4b/evidence_reference_learning_value_evaluation.validation.json"
FORBIDDEN_KEYS = {
    "payload", "source_content", "source_text", "text", "prompt", "correct_answer",
    "answer_key", "learner_response", "transcript_text", "audio_bytes", "recording",
}


def _walk(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                errors.append(f"private_content_key_forbidden:{path}.{key}")
            errors.extend(_walk(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk(child, f"{path}[{index}]"))
    return errors


def validate_paths(*, artifact_path: Path, intake_path: Path, consumer_path: Path, bridge_path: Path) -> dict[str, Any]:
    artifact = builder.read_json(artifact_path)
    expected = builder.build_artifact(
        builder.read_json(intake_path),
        builder.read_json(consumer_path),
        builder.read_json(bridge_path),
    )
    errors: list[str] = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    errors.extend(_walk(artifact))
    counts = artifact.get("counts", {})
    if (
        counts.get("teacher_delivery_activated_count") != 0
        or counts.get("remediation_activated_count") != 0
        or counts.get("learner_facing_asset_count") != 0
        or counts.get("mastery_evidence_delta") != 0
        or counts.get("canonical_coverage_delta") != 0
        or counts.get("private_text_exposure_count") != 0
    ):
        errors.append("evaluation_boundary_count_invalid")
    if artifact.get("evaluation_policy", {}).get("activation_allowed") is not False:
        errors.append("activation_policy_invalid")
    if artifact.get("claim_boundaries", {}).get("pedagogical_effectiveness_proven") is not False:
        errors.append("effectiveness_claim_invalid")
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
    parser.add_argument("--m4a-intake", type=Path, default=builder.DEFAULT_INTAKE)
    parser.add_argument("--m2-consumer", type=Path, default=builder.DEFAULT_M2)
    parser.add_argument("--pku-bridge", type=Path, default=builder.DEFAULT_BRIDGE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_paths(
            artifact_path=args.artifact,
            intake_path=args.m4a_intake,
            consumer_path=args.m2_consumer,
            bridge_path=args.pku_bridge,
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
