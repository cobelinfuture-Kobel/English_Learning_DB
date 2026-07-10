#!/usr/bin/env python3
"""Read-only dispatcher for all canonical A1 offline sentence validators."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.validators.validate_a1_articles_number_agreement_fullfix import (
    classify_articles_number_agreement,
)
from ulga.validators.validate_a1_can_statement_rule_primitives import classify_can_statement
from ulga.validators.validate_a1_canonical_executable_batch_01 import CLASSIFIERS as BATCH_01_CLASSIFIERS
from ulga.validators.validate_a1_canonical_executable_batch_02 import CLASSIFIERS as BATCH_02_CLASSIFIERS


TASK_ID = "R7-M104E22A_A1CanonicalValidatorDispatcherImplementation"
CAN_GRAMMAR_ID = "GRAMMAR_CAN_STATEMENT"
ARTICLES_GRAMMAR_ID = "GRAMMAR_ARTICLES_BASIC"


def _registry() -> dict[str, Callable[[str], Any]]:
    registry = {CAN_GRAMMAR_ID: classify_can_statement}
    for source in (BATCH_01_CLASSIFIERS, BATCH_02_CLASSIFIERS):
        overlap = set(registry) & set(source)
        if overlap:
            raise RuntimeError(f"Duplicate canonical validator routes: {sorted(overlap)}")
        registry.update(source)

    # R7-M105N FullFix: replace the earlier batch-01 article classifier with
    # the explicit article-number agreement validator. The route remains under
    # the same canonical grammar ID, so all existing consumers receive the fix.
    registry[ARTICLES_GRAMMAR_ID] = classify_articles_number_agreement
    return registry


VALIDATOR_REGISTRY = _registry()


def available_grammar_ids() -> list[str]:
    return sorted(VALIDATOR_REGISTRY)


def validate(grammar_id: str, text: str) -> dict[str, Any]:
    classifier = VALIDATOR_REGISTRY.get(grammar_id)
    if classifier is None:
        return {
            "task_id": TASK_ID,
            "grammar_id": grammar_id,
            "text": text,
            "dispatch_status": "UNKNOWN_GRAMMAR_ID_FAIL_CLOSED",
            "match": False,
            "primitive_id": None,
            "reason": "unknown_canonical_a1_grammar_id",
            "validator_mode": "OFFLINE_STATIC_PROTOTYPE",
            "production_runtime_validator": False,
            "learner_state_write": False,
        }
    decision = classifier(text)
    return {
        "task_id": TASK_ID,
        "grammar_id": grammar_id,
        "text": text,
        "dispatch_status": "VALIDATOR_EXECUTED",
        "match": bool(decision.match),
        "primitive_id": decision.primitive_id,
        "reason": decision.reason,
        "validator_mode": "OFFLINE_STATIC_PROTOTYPE",
        "production_runtime_validator": False,
        "learner_state_write": False,
    }


def validate_many(requests: list[dict[str, str]]) -> dict[str, Any]:
    results = [validate(request.get("grammar_id", ""), request.get("text", "")) for request in requests]
    return {
        "task_id": TASK_ID,
        "request_count": len(results),
        "executed_count": sum(result["dispatch_status"] == "VALIDATOR_EXECUTED" for result in results),
        "unknown_count": sum(result["dispatch_status"] == "UNKNOWN_GRAMMAR_ID_FAIL_CLOSED" for result in results),
        "match_count": sum(result["match"] for result in results),
        "results": results,
        "learner_state_write": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grammar-id", required=True)
    parser.add_argument("--text", required=True)
    args = parser.parse_args()
    result = validate(args.grammar_id, args.text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["dispatch_status"] == "VALIDATOR_EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
