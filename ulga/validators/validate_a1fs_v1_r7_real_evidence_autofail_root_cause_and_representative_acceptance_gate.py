#!/usr/bin/env python3
"""Independent validator for the R7 representative real-evidence gate artifact."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ulga.builders import (
    build_a1fs_v1_r7_real_evidence_autofail_root_cause_and_representative_acceptance_gate as gate,
)

STATUS = "PASS_R7_REAL_EVIDENCE_AUTOFAIL_REPRESENTATIVE_ACCEPTANCE_VALIDATION"


def validate_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    core = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    if artifact.get("artifact_sha256") != gate.digest(core):
        errors.append("artifact_digest_invalid")
    if artifact.get("task_id") != gate.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != gate.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    counts = artifact.get("counts") or {}
    replay = artifact.get("replay_results") or []
    roots = artifact.get("autofail_root_causes") or []
    root_counts = artifact.get("autofail_root_cause_counts") or {}
    if counts.get("scoring_reproducibility_count") != len(replay):
        errors.append("replay_count_mismatch")
    if counts.get("scoring_reproducibility_failure_count") != sum(
        not bool(row.get("replay_match")) for row in replay
    ):
        errors.append("replay_failure_count_mismatch")
    if any(row.get("root_cause") not in gate.ROOT_CAUSES for row in roots):
        errors.append("autofail_root_cause_invalid")
    expected_root_counts = {
        cause: sum(row.get("root_cause") == cause for row in roots)
        for cause in sorted(gate.ROOT_CAUSES)
    }
    if root_counts != expected_root_counts:
        errors.append("autofail_root_cause_counts_mismatch")
    if counts.get("auto_fail_valid_count") != len(roots):
        errors.append("autofail_detail_count_mismatch")
    identified = sum(expected_root_counts[cause] for cause in gate.ENGINEERING_DEFECT_CAUSES)
    remediated = sum(
        row.get("root_cause") in gate.ENGINEERING_DEFECT_CAUSES
        and row.get("remediation_status") == "VERIFIED_REMEDIATED_FUTURE_ONLY"
        for row in roots
    )
    unresolved = identified - remediated
    if counts.get("identified_engineering_defect_count") != identified:
        errors.append("identified_engineering_defect_count_mismatch")
    if counts.get("remediated_engineering_defect_count") != remediated:
        errors.append("remediated_engineering_defect_count_mismatch")
    if counts.get("unresolved_engineering_defect_count") != unresolved:
        errors.append("unresolved_engineering_defect_count_mismatch")
    coverage = artifact.get("coverage") or {}
    for key in ("universe", "evidenced", "missing"):
        if not isinstance(coverage.get(key), Mapping):
            errors.append(f"coverage_{key}_invalid")
    if all(isinstance(coverage.get(key), Mapping) for key in ("universe", "evidenced", "missing")):
        expected_missing = gate._missing(coverage["universe"], coverage["evidenced"])
        if coverage["missing"] != expected_missing:
            errors.append("coverage_missing_mismatch")
        complete = not any(expected_missing.values())
        if artifact.get("verification", {}).get("required_representative_coverage_complete") != complete:
            errors.append("coverage_completion_flag_mismatch")
    targeted = artifact.get("targeted_queue") or []
    if len(targeted) > 6:
        errors.append("targeted_queue_limit_exceeded")
    if counts.get("targeted_additional_real_session_count") != len(targeted):
        errors.append("targeted_queue_count_mismatch")
    if len({row.get("work_item_id") for row in targeted}) != len(targeted):
        errors.append("targeted_queue_identity_duplicate")
    serialized = gate.canonical(artifact)
    for forbidden in ('"response":', '"accepted_texts":', '"access_token":', '"private_scoring_contract":'):
        if forbidden in serialized:
            errors.append(f"private_payload_leak:{forbidden}")
    if artifact.get("a2_unlocked") is not False:
        errors.append("a2_lock_broken")
    return {
        "validation_status": STATUS if not errors else "FAIL_R7_REAL_EVIDENCE_AUTOFAIL_REPRESENTATIVE_ACCEPTANCE_VALIDATION",
        "error_count": len(errors), "errors": errors,
        "representative_acceptance_status": artifact.get("representative_acceptance_status"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--evidence-package", type=Path)
    parser.add_argument("--projection", type=Path)
    parser.add_argument("--remediation-artifact", type=Path)
    args = parser.parse_args(argv)
    artifact = gate.read_json(args.artifact)
    result = validate_artifact(artifact)
    supplied = (args.database, args.evidence_package, args.projection)
    if any(supplied) and not all(supplied):
        result["errors"].append("rebuild_inputs_must_be_supplied_together")
    elif all(supplied):
        rebuilt = gate.build(
            database_path=args.database,
            evidence_package=gate.read_json(args.evidence_package),
            projection=gate.read_json(args.projection),
            remediation=gate.read_json(args.remediation_artifact) if args.remediation_artifact else None,
        )
        if rebuilt != artifact:
            result["errors"].append("artifact_rebuild_mismatch")
    result["error_count"] = len(result["errors"])
    if result["error_count"]:
        result["validation_status"] = "FAIL_R7_REAL_EVIDENCE_AUTOFAIL_REPRESENTATIVE_ACCEPTANCE_VALIDATION"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["error_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
