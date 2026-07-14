#!/usr/bin/env python3
"""Validate the unified A1/A1+ authority scope query."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.query.a1_a1plus_authority_scope_query import (
    AUTHORITIES,
    build_scope,
    query_authority,
)

PASS_STATUS = "PASS_AUTHORITY_SCOPE_QUERY_VALIDATED"


def validate() -> dict[str, Any]:
    errors: list[str] = []
    summaries = {}
    for stage, expected_theme_count in (("A1", 9), ("A1_PLUS", 10)):
        scope = build_scope(stage)
        summaries[stage] = {
            "validation_status": scope.get("validation_status"),
            "counts": scope.get("counts"),
            "source_cefr_policy": scope.get("scope", {}).get("source_cefr_policy"),
        }
        counts = scope.get("counts", {})
        expected = {
            "grammar": 109,
            "vocabulary": 784,
            "chunk": 76,
            "pattern": 27,
            "theme": expected_theme_count,
            "skill": 4,
        }
        for authority, count in expected.items():
            if counts.get(authority) != count:
                errors.append(f"{stage}:{authority}_count_not_{count}")
        if not counts.get("question_type"):
            errors.append(f"{stage}:question_type_empty")
        if scope.get("scope", {}).get("a2_a2plus_in_scope") is not False:
            errors.append(f"{stage}:a2_scope_leakage")
        if scope.get("claim_boundaries", {}).get("learner_state_joined") is not False:
            errors.append(f"{stage}:learner_state_joined")
        if scope.get("claim_boundaries", {}).get("canonical_graph_written") is not False:
            errors.append(f"{stage}:canonical_graph_write_claim")

    for authority in AUTHORITIES:
        response = query_authority(authority, stage="A1", limit=3)
        if response.get("error"):
            errors.append(f"query_failed:{authority}:{response['error'].get('code')}")
        elif response.get("query_metadata", {}).get("result_count", 0) < 1:
            errors.append(f"query_empty:{authority}")

    if query_authority("grammar", stage="A2").get("error", {}).get("code") != (
        "OUT_OF_SCOPE_LEVEL_STAGE:A2"
    ):
        errors.append("a2_request_not_rejected")
    if query_authority("grammar", static_only=False).get("error", {}).get("code") != (
        "STATIC_ONLY_REQUIRED"
    ):
        errors.append("adaptive_request_not_rejected")
    if query_authority("unknown").get("error", {}).get("code") != "UNKNOWN_AUTHORITY":
        errors.append("unknown_authority_not_rejected")

    return {
        "task_id": "E4S-A1V1-M01_AuthorityScopeAndQueryCompleteness",
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "errors": errors,
        "stage_summaries": summaries,
        "claim_boundaries": {
            "query_validation_complete": not errors,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE" if not errors else "CI_FAILURE",
        "next_short_step": "E4S-A1V1-M02_CrossSkillLearningUnitContractAndBuilder",
    }


def main() -> int:
    report = validate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
