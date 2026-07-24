#!/usr/bin/env python3
"""Validate the safe readback for KET99 M4D private-chain materialization."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_m4d_private_chain_materialization as builder
from ulga.builders import build_ket99_pku_selected_reading_asset_consumer_activation_canary as m4d

FORBIDDEN_KEYS = {
    "source_text",
    "transcript_text",
    "prompt",
    "answer_key",
    "learner_response",
    "audio_bytes",
    "recording",
}
ZERO_DELTA_KEYS = (
    "composition_item_delta",
    "required_delivery_asset_delta",
    "asset_record_delta",
    "response_capture_contract_delta",
    "mastery_evidence_delta",
    "canonical_coverage_delta",
    "a2_unlock_count",
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _walk_forbidden(value: Any, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                errors.append(f"private_content_key_forbidden:{path}.{key}")
            _walk_forbidden(child, errors, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, errors, f"{path}[{index}]")


def validate_artifact(
    artifact: Mapping[str, Any], m4d_value: Mapping[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    unsigned = dict(artifact)
    stored_sha = unsigned.pop("artifact_sha256", None)
    if stored_sha != builder.digest(unsigned):
        errors.append("artifact_sha256_invalid")
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("validation_status") != builder.PASS_STATUS:
        errors.append("validation_status_invalid")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_invalid")
    if artifact.get("stage_order") != list(builder.STAGE_ORDER):
        errors.append("stage_order_invalid")
    stages = artifact.get("stages")
    if not isinstance(stages, list) or [row.get("stage") for row in stages if isinstance(row, Mapping)] != list(builder.STAGE_ORDER):
        errors.append("stage_rows_invalid")
    elif any(
        row.get("status") != "PASS"
        or not isinstance(row.get("artifact_sha256"), str)
        or len(row["artifact_sha256"]) != 64
        for row in stages
    ):
        errors.append("stage_status_or_digest_invalid")

    selected = artifact.get("selected_lesson")
    if not isinstance(selected, Mapping):
        errors.append("selected_lesson_missing")
    else:
        if not str(selected.get("lesson_id") or ""):
            errors.append("selected_lesson_id_missing")
        if selected.get("skill") not in {"LISTENING", "SPEAKING", "READING", "WRITING"}:
            errors.append("selected_skill_invalid")
        if selected.get("level") not in {"A1", "A1+"}:
            errors.append("selected_level_invalid")
        if selected.get("planner_selection_preserved") is not True:
            errors.append("planner_selection_not_preserved")
        if selected.get("preferred_skill_override_used") is not False:
            errors.append("preferred_skill_override_forbidden")

    if (
        m4d_value.get("m4d_task_id") != m4d.TASK_ID
        or m4d_value.get("m4d_validation_status") != m4d.PASS_STATUS
        or m4d_value.get("m4d_errors") != []
        or m4d_value.get("m4d_stop_reason") != "NONE"
    ):
        errors.append("m4d_contract_invalid")
    canary = m4d_value.get("m4d_private_canary")
    summary_canary = artifact.get("m4d_private_canary")
    if not isinstance(canary, Mapping) or not isinstance(summary_canary, Mapping):
        errors.append("m4d_canary_missing")
    else:
        for key in (
            "canary_status",
            "selected_lesson_has_authored_assets",
            "teacher_delivery_asset_count",
            "remediation_asset_count",
        ):
            if summary_canary.get(key) != canary.get(key):
                errors.append(f"m4d_canary_readback_drift:{key}")
        if canary.get("selected_lesson_id") != artifact.get("selected_lesson", {}).get("lesson_id"):
            errors.append("m4d_selected_lesson_drift")

    counts = m4d_value.get("m4d_counts")
    if not isinstance(counts, Mapping):
        errors.append("m4d_counts_missing")
    else:
        for key in ZERO_DELTA_KEYS:
            if counts.get(key) != 0:
                errors.append(f"m4d_zero_delta_invalid:{key}")

    identity = artifact.get("source_identity")
    if not isinstance(identity, Mapping) or any(
        not isinstance(value, str) or len(value) != 64 for value in identity.values()
    ):
        errors.append("source_identity_invalid")
    boundaries = artifact.get("claim_boundaries")
    if not isinstance(boundaries, Mapping) or any(value is not False for value in boundaries.values()):
        errors.append("claim_boundary_invalid")
    if artifact.get("errors") != [] or artifact.get("stop_reason") != "NONE":
        errors.append("artifact_not_closed")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")
    _walk_forbidden(artifact, errors)
    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_KET99_PK_M4D1_PRIVATE_RUNTIME_CHAIN",
        "error_count": len(errors),
        "errors": errors,
        "stage_count": len(stages) if isinstance(stages, list) else 0,
        "selected_lesson_id": artifact.get("selected_lesson", {}).get("lesson_id"),
        "m4d_canary_status": artifact.get("m4d_private_canary", {}).get("canary_status"),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--m4d", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(_read(args.artifact), _read(args.m4d))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
