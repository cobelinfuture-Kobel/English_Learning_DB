#!/usr/bin/env python3
"""Validate post-CP07 controlled runtime usability and product-gap readback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_post_cp07_controlled_runtime_usability_product_gap_recheck as builder

FAIL_STATUS = "FAIL_POST_CP07_CONTROLLED_RUNTIME_USABILITY_PRODUCT_GAP_RECHECK"
DEFAULT_REPORT = Path(".local/a1fs_v1/post_cp07/controlled_runtime_usability_product_gap_recheck.validation.json")


def validate_artifact(
    artifact: Mapping[str, Any],
    cp07f_report: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        expected = builder.build_artifact(cp07f_report)
    except (ValueError, TypeError) as exc:
        expected = None
        errors.append(f"source_rebuild_failed:{exc}")

    if expected is not None and dict(artifact) != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("validation_status") not in {
        builder.PENDING_STATUS,
        builder.USABLE_STATUS,
    }:
        errors.append("validation_status_invalid")

    capability = artifact.get("capability_state", {})
    gate = artifact.get("mainline_distance_gate", {})
    counts = artifact.get("counts", {})
    gaps = artifact.get("remaining_product_gaps", [])
    if not isinstance(capability, Mapping) or not isinstance(gate, Mapping):
        errors.append("capability_or_gate_invalid")
    if not isinstance(counts, Mapping) or not isinstance(gaps, list):
        errors.append("counts_or_gaps_invalid")

    usable = capability.get("controlled_runtime_usable") is True
    if usable != (artifact.get("validation_status") == builder.USABLE_STATUS):
        errors.append("usable_status_mismatch")
    if gate.get("classification") != "DIRECT":
        errors.append("mainline_classification_invalid")
    if gate.get("complete_product") is not False:
        errors.append("complete_product_claim_forbidden")
    if artifact.get("claim_boundaries", {}).get("public_release_claimed") is not False:
        errors.append("public_release_claim_invalid")
    if artifact.get("claim_boundaries", {}).get("test_fixture_promoted_to_real") is not False:
        errors.append("test_fixture_promotion_invalid")
    if artifact.get("claim_boundaries", {}).get("a2_unlocked") is not False:
        errors.append("a2_unlock_invalid")

    blocking = sum(
        bool(row.get("blocks_controlled_runtime_usability"))
        for row in gaps
        if isinstance(row, Mapping)
    )
    if counts.get("blocking_gap_count") != blocking:
        errors.append("blocking_gap_count_invalid")
    if usable and blocking != 0:
        errors.append("usable_with_blocking_gap_invalid")
    if not usable and artifact.get("stop_reason") != "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED":
        errors.append("pending_stop_reason_invalid")
    if usable and artifact.get("stop_reason") != "NONE":
        errors.append("usable_stop_reason_invalid")

    unsigned = dict(artifact)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != builder.digest(unsigned):
        errors.append("artifact_sha256_invalid")
    try:
        builder.safe_scan(artifact)
    except ValueError as exc:
        errors.append(str(exc))

    return {
        "task_id": builder.TASK_ID,
        "validation_status": artifact.get("validation_status") if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": artifact.get("next_short_step", builder.TASK_ID) if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--cp07f-report", type=Path, default=builder.DEFAULT_CP07F)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        artifact = builder.read_json(args.artifact)
        cp07f_report = builder.read_json(args.cp07f_report)
        report = validate_artifact(artifact, cp07f_report)
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
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
