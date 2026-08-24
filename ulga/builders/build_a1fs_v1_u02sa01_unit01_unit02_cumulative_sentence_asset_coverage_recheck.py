#!/usr/bin/env python3
"""Materialize U02SA01R1 cumulative large Sentence Asset production from current authorities."""
from __future__ import annotations
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders.a1fs_v1_u02sa01r1.constants import *
from ulga.builders.a1fs_v1_u02sa01r1.engine import build_production, digest, load_manifest
from ulga.builders.a1fs_v1_u02sa01r1.payload import build_payload

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

def candidate_payload() -> dict[str, Any]:
    return build_payload(build_production())

def build_candidate() -> dict[str, Any]:
    manifest=load_manifest(); payload=candidate_payload()
    return policy_artifact.build_candidate(payload=payload, producer_id=TASK_ID, level_scope=["A1"], source_bindings={"safe_seed_manifest_shards":[str(path.relative_to(REPO_ROOT)).replace("\\","/") for path in SAFE_MANIFEST_SHARD_PATHS],"safe_seed_manifest_sha256":manifest["manifest_sha256"],"unit01_sentence_pool_sha256":UNIT01_SENTENCE_POOL_SHA256,"unit01_defer_sha256":UNIT01_DEFER_SHA256,"cambridge_yle_sha256":CAMBRIDGE_YLE_SHA256,"canonical_vocabulary_path":str(VOCABULARY_PATH.relative_to(REPO_ROOT)).replace("\\","/"),"canonical_vocabulary_git_blob_sha":VOCABULARY_GIT_BLOB_SHA,"unit02_pattern_ids":sorted(PATTERN_TEMPLATES)})

def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck as validator
    receipt=validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(candidate, validation_receipts=[receipt], decision_ref=DECISION_REF, producer_id=TASK_ID)

def build_report() -> dict[str, Any]:
    return admit_candidate(build_candidate())["payload"]

def main() -> int:
    from ulga.validators import validate_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck as validator
    candidate=build_candidate(); approved=admit_candidate(candidate); result=validator.validate_approved(candidate,approved); report=approved["payload"]; counts=report["pipeline_counts"]
    print(f"STATUS={PASS_STATUS}")
    for key in ("unit01_base_sentence_assets","unit02_generated_sentence_candidates","unit02_semantic_approved","unit02_semantic_rejected","unit02_semantic_deferred","unit02_new_admitted","cumulative_distinct_sentence_assets"):
        print(f"{key.upper()}={counts[key]}")
    print(f"ERROR_COUNT={result['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0 if result["error_count"]==0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
