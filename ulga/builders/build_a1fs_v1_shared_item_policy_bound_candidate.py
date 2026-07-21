#!/usr/bin/env python3
"""Materialize the existing 384-item A1/A1+ shared contract as Candidate JSON."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders.build_a1_a1plus_shared_item_contract import (
    build_artifact as build_shared_item_contract,
)
from ulga.validators.validate_a1_a1plus_shared_item_contract import (
    PASS_STATUS as SOURCE_PASS_STATUS,
    validate_artifact as validate_shared_item_contract,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
TASK_ID = "A1FS-V1_SharedItemPolicyBoundCandidateMaterialization"
PRODUCER_ID = "build_a1fs_v1_shared_item_policy_bound_candidate"
SOURCE_BUILDER_PATH = "ulga/builders/build_a1_a1plus_shared_item_contract.py"
SOURCE_VALIDATOR_PATH = "ulga/validators/validate_a1_a1plus_shared_item_contract.py"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/a1fs_v1/canonical_content/e4s_a1v1_shared_item_contract.candidate.private.json"
)


class SharedItemCandidateBuildError(RuntimeError):
    """Raised when the legacy shared-item source cannot be safely materialized."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SharedItemCandidateBuildError(message)


def _validate_source(artifact: Mapping[str, Any]) -> dict[str, Any]:
    report = validate_shared_item_contract(artifact)
    _require(isinstance(report, Mapping), "source_validation_report_required")
    _require(
        report.get("validation_status") == SOURCE_PASS_STATUS,
        "source_validation_not_pass",
    )
    _require(not report.get("errors"), "source_validation_errors_present")

    coverage = artifact.get("coverage_summary")
    _require(isinstance(coverage, Mapping), "source_coverage_summary_required")
    _require(coverage.get("shared_item_count") == 384, "source_shared_item_count_not_384")
    _require(
        coverage.get("skill_item_counts")
        == {"reading": 96, "writing": 96, "listening": 96, "speaking": 96},
        "source_skill_counts_invalid",
    )
    _require(artifact.get("scope") == "A1_A1_PLUS_ONLY", "source_scope_invalid")
    _require(
        artifact.get("claim_boundaries", {}).get("a2_a2plus_in_scope") is False,
        "source_a2_scope_detected",
    )
    return dict(report)


def build_policy_bound_candidate(
    *,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = build_shared_item_contract()
    source_report = _validate_source(source)
    source_sha256 = content_policy.digest(source)
    report_sha256 = content_policy.digest(source_report)

    return content_policy.build_candidate(
        payload=source,
        producer_id=PRODUCER_ID,
        level_scope=["A1", "A1+"],
        source_bindings={
            "source_artifact_id": source["artifact_id"],
            "source_schema_version": source["schema_version"],
            "source_artifact_sha256": source_sha256,
            "source_validation_sha256": report_sha256,
            "source_builder_path": SOURCE_BUILDER_PATH,
            "source_validator_path": SOURCE_VALIDATOR_PATH,
            "shared_item_count": 384,
            "skill_item_counts": {
                "reading": 96,
                "writing": 96,
                "listening": 96,
                "speaking": 96,
            },
        },
        policy=policy,
    )


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    candidate = build_policy_bound_candidate()
    write_json_atomic(args.output, candidate)
    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "artifact_role": candidate["artifact_role"],
                "artifact_sha256": candidate["artifact_sha256"],
                "shared_item_count": candidate["source_bindings"]["shared_item_count"],
                "learner_facing": candidate["learner_facing"],
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
