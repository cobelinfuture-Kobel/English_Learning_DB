#!/usr/bin/env python3
"""Validate the policy-bound Candidate JSON for the 384 shared four-skill items."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as envelope_validator

TASK_ID = "A1FS-V1_SharedItemPolicyBoundCandidateMaterialization"
PASS_STATUS = "PASS_A1FS_V1_SHARED_ITEM_POLICY_BOUND_CANDIDATE"
EXPECTED_SKILL_COUNTS = {
    "reading": 96,
    "writing": 96,
    "listening": 96,
    "speaking": 96,
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def validate_candidate(
    candidate: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    envelope = envelope_validator.validate_artifact(
        candidate,
        policy=policy,
        expected_role="CANDIDATE_JSON",
    )
    errors.extend(f"envelope:{error}" for error in envelope.get("errors", []))

    payload = candidate.get("payload")
    source_bindings = candidate.get("source_bindings")
    if not isinstance(payload, Mapping):
        errors.append("payload_object_required")
        payload = {}
    if not isinstance(source_bindings, Mapping):
        errors.append("source_bindings_object_required")
        source_bindings = {}

    if payload.get("task_id") != "E4S-A1V1-M03_SharedItemAnswerScoringMediaContract":
        errors.append("source_task_id_invalid")
    if payload.get("artifact_id") != "e4s_a1v1_shared_item_contract":
        errors.append("source_artifact_id_invalid")
    if payload.get("schema_version") != "e4s.a1v1.shared_item.v1":
        errors.append("source_schema_version_invalid")
    if payload.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("source_scope_invalid")

    coverage = payload.get("coverage_summary")
    if not isinstance(coverage, Mapping):
        errors.append("coverage_summary_required")
        coverage = {}
    if coverage.get("shared_item_count") != 384:
        errors.append("shared_item_count_not_384")
    if coverage.get("skill_item_counts") != EXPECTED_SKILL_COUNTS:
        errors.append("skill_item_counts_invalid")

    items = payload.get("shared_items")
    if not isinstance(items, list):
        errors.append("shared_items_list_required")
        items = []
    if len(items) != 384:
        errors.append("shared_items_length_not_384")
    shared_ids = [item.get("shared_item_id") for item in items if isinstance(item, Mapping)]
    source_ids = [item.get("source_item_id") for item in items if isinstance(item, Mapping)]
    if len(set(shared_ids)) != 384:
        errors.append("shared_item_ids_not_unique_384")
    if len(set(source_ids)) != 384:
        errors.append("source_item_ids_not_unique_384")
    skill_counts = Counter(
        str(item.get("skill")) for item in items if isinstance(item, Mapping)
    )
    if dict(skill_counts) != EXPECTED_SKILL_COUNTS:
        errors.append("materialized_skill_counts_invalid")
    if any(
        item.get("official_cefr_level") not in {"A1", "A1+"}
        for item in items
        if isinstance(item, Mapping)
    ):
        errors.append("a2_or_out_of_scope_item_detected")
    if payload.get("claim_boundaries", {}).get("a2_a2plus_in_scope") is not False:
        errors.append("a2_claim_boundary_invalid")

    expected_source_sha = digest(payload)
    if source_bindings.get("source_artifact_sha256") != expected_source_sha:
        errors.append("source_artifact_sha256_mismatch")
    if source_bindings.get("source_artifact_id") != payload.get("artifact_id"):
        errors.append("source_artifact_binding_mismatch")
    if source_bindings.get("source_schema_version") != payload.get("schema_version"):
        errors.append("source_schema_binding_mismatch")
    if source_bindings.get("shared_item_count") != 384:
        errors.append("source_binding_item_count_invalid")
    if source_bindings.get("skill_item_counts") != EXPECTED_SKILL_COUNTS:
        errors.append("source_binding_skill_counts_invalid")

    if candidate.get("learner_facing") is not False:
        errors.append("candidate_learner_facing_forbidden")
    if candidate.get("admission", {}).get("status") != "PENDING_VALIDATION":
        errors.append("candidate_admission_status_invalid")

    return {
        "schema_version": "a1fs.v1.shared_item_policy_bound_candidate_validation.v1",
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "artifact_sha256": candidate.get("artifact_sha256"),
        "shared_item_count": len(items),
        "skill_item_counts": dict(skill_counts),
        "learner_facing": candidate.get("learner_facing"),
        "a2_unlocked": False,
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    candidate = load_json(args.artifact)
    policy = load_json(args.policy) if args.policy else None
    report = validate_candidate(candidate, policy=policy)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
