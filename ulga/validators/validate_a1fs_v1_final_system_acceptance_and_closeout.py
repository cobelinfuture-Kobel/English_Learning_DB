#!/usr/bin/env python3
"""Independent validator for the A1FS-V1 final system closeout artifact."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ulga.builders import build_a1fs_v1_final_system_acceptance_and_closeout as closeout

PASS_STATUS = "PASS_A1FS_V1_FINAL_SYSTEM_ACCEPTANCE_AND_CLOSEOUT_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_V1_FINAL_SYSTEM_ACCEPTANCE_AND_CLOSEOUT_VALIDATION"


def validate_artifact(artifact: Mapping[str, Any], safe: Mapping[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    core = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    if artifact.get("artifact_sha256") != closeout.digest(core):
        errors.append("artifact_digest_invalid")
    if artifact.get("task_id") != closeout.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != closeout.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("final_acceptance_status") != closeout.PASS_STATUS:
        errors.append("final_acceptance_not_passed")
    runtime = artifact.get("runtime_readback") or {}
    if not runtime.get("checks") or not all(runtime["checks"].values()):
        errors.append("runtime_checks_not_all_passed")
    counts = artifact.get("counts") or {}
    expected = {
        "cumulative_real_attempt_count": 11,
        "valid_real_evidence_ready_count": 11,
        "scoring_reproducibility_count": 11,
        "scoring_reproducibility_failure_count": 0,
        "identified_engineering_defect_count": 4,
        "remediated_engineering_defect_count": 4,
        "unresolved_engineering_defect_count": 0,
        "synthetic_evidence_count": 0,
    }
    if counts != expected:
        errors.append("counts_invalid")
    coverage = artifact.get("coverage") or {}
    if coverage.get("human_review_path_status") != "VERIFIED":
        errors.append("human_review_path_not_verified")
    if not all(coverage.get(key) is True for key in (
        "writing_covered", "feature_rubric_covered", "representative_coverage_complete"
    )):
        errors.append("required_coverage_not_complete")
    if any((coverage.get("missing") or {}).values()):
        errors.append("coverage_missing_not_empty")
    boundaries = artifact.get("claim_boundaries") or {}
    if boundaries != {
        "r4_bank_changed": False, "candidate_identity_changed_count": 0,
        "a2_unlocked": False, "mastery_written": False, "retention_confirmed": False,
    }:
        errors.append("claim_boundaries_invalid")
    if artifact.get("stop_reason") != "NONE" or artifact.get("blocker_type") != "NONE":
        errors.append("closeout_blocked")
    if artifact.get("next_resume_task") != "NONE" or artifact.get("mainline_distance_delta") != 0:
        errors.append("closeout_distance_invalid")
    if safe is not None:
        safe_core = {key: value for key, value in safe.items() if key != "artifact_sha256"}
        if safe.get("artifact_sha256") != closeout.digest(safe_core):
            errors.append("safe_artifact_digest_invalid")
        if safe != closeout.safe_artifact(artifact):
            errors.append("safe_artifact_mismatch")
        serialized = closeout.canonical(safe)
        for forbidden in (
            '"response"', '"notes"', '"reviewer_id"', '"attempt_id"',
            '"learner_id"', '"private_scoring_contract"', '"database_path"',
        ):
            if forbidden in serialized:
                errors.append(f"safe_private_payload_leak:{forbidden}")
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "final_acceptance_status": artifact.get("final_acceptance_status"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--safe", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--evidence-package", type=Path)
    parser.add_argument("--intake", type=Path)
    parser.add_argument("--representative-gate", type=Path)
    args = parser.parse_args(argv)
    artifact = closeout.read_json(args.artifact)
    safe = closeout.read_json(args.safe) if args.safe else None
    result = validate_artifact(artifact, safe)
    rebuild_inputs = (args.database, args.evidence_package, args.intake, args.representative_gate)
    if any(rebuild_inputs) and not all(rebuild_inputs):
        result["errors"].append("rebuild_inputs_must_be_supplied_together")
    elif all(rebuild_inputs):
        rebuilt = closeout.build(
            database_path=args.database,
            evidence_package=closeout.read_json(args.evidence_package),
            intake=closeout.read_json(args.intake),
            representative_gate=closeout.read_json(args.representative_gate),
        )
        if rebuilt != artifact:
            result["errors"].append("artifact_rebuild_mismatch")
    result["error_count"] = len(result["errors"])
    if result["errors"]:
        result["validation_status"] = FAIL_STATUS
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
