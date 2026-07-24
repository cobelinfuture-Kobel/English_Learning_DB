#!/usr/bin/env python3
"""Validate deterministic KET99-PK-M4 optional pilot overlay admission."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ulga.builders import build_ket99_pku_controlled_pilot_overlay_admission as builder

FAIL_STATUS = "FAIL_KET99_PK_M4_CONTROLLED_PILOT_OVERLAY_ADMISSION"
REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m4/controlled_pilot_overlay_admission.validation.json"
COVERAGE_REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m4/coverage_readback.validation.json"


def validate_paths(
    *,
    artifact_path: Path,
    coverage_path: Path,
    m3_path: Path,
    consumer_path: Path,
    r3g_path: Path,
    cp07b_path: Path,
) -> dict:
    artifact = builder.read_json(artifact_path)
    coverage = builder.read_json(coverage_path)
    m3 = builder.read_json(m3_path)
    consumer = builder.read_json(consumer_path)
    expected = builder.build_artifact(
        m3,
        consumer,
        builder.read_json(r3g_path),
        builder.read_json(cp07b_path),
    )
    expected_coverage = builder.build_coverage_readback(expected, m3, consumer)
    errors = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    if coverage != expected_coverage:
        errors.append("coverage_deterministic_rebuild_mismatch")
    unsigned = dict(artifact)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != builder.digest(unsigned):
        errors.append("artifact_sha256_invalid")
    unsigned_coverage = dict(coverage)
    stored_coverage = unsigned_coverage.pop("artifact_sha256", None)
    if stored_coverage != builder.digest(unsigned_coverage):
        errors.append("coverage_artifact_sha256_invalid")
    counts = artifact.get("coverage_summary", {})
    if (
        not isinstance(counts.get("admitted_pku_count"), int)
        or counts.get("admitted_pku_count", 0) <= 0
        or counts.get("admitted_pku_count", 0)
        > counts.get("candidate_ready_pku_count", 0)
        or counts.get("pending_auto_promotion_count") != 0
        or counts.get("rejected_reentry_count") != 0
    ):
        errors.append("admission_count_semantics_invalid")
    if counts.get("source_pku_count") == 35 and (
        counts.get("controlled_candidate_ready_count") != 17
        or counts.get("unresolved_pku_count") != 15
        or counts.get("rejected_exam_procedure_count") != 3
    ):
        errors.append("production_admission_count_semantics_invalid")
    coverage_counts = coverage.get("coverage_counts", {})
    if (
        coverage_counts.get("overlay_unique_new_coverage_count") != 0
        or coverage_counts.get("coverage_double_count") != 0
        or coverage_counts.get("canonical_graph_mutation_count") != 0
        or coverage_counts.get("canonical_denominator_mutation_count") != 0
    ):
        errors.append("canonical_coverage_boundary_invalid")
    if coverage.get("no_double_count_proof", {}).get("proof_status") != "PASS":
        errors.append("no_double_count_proof_invalid")
    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "coverage_summary": artifact.get("coverage_summary", {}),
        "coverage_readback": coverage.get("coverage_counts", {}),
        "deterministic_rebuild_matches": artifact == expected,
        "coverage_deterministic_rebuild_matches": coverage == expected_coverage,
        "downstream_consumer_readiness_status": (
            "PASS" if not errors else "FAIL"
        ),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--coverage", type=Path, default=builder.COVERAGE_OUTPUT)
    parser.add_argument("--m3", type=Path, default=builder.M3)
    parser.add_argument("--m2-consumer", type=Path, default=builder.M2)
    parser.add_argument("--r3g", type=Path, default=builder.R3G)
    parser.add_argument("--cp07b", type=Path, default=builder.CP07B)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--coverage-report", type=Path, default=COVERAGE_REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_paths(
            artifact_path=args.artifact,
            coverage_path=args.coverage,
            m3_path=args.m3,
            consumer_path=args.m2_consumer,
            r3g_path=args.r3g,
            cp07b_path=args.cp07b,
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
    args.coverage_report.parent.mkdir(parents=True, exist_ok=True)
    args.coverage_report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
