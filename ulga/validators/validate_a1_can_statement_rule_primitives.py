"""Offline prototype validator for A1 can ability affirmative statement rule primitives.

This validator intentionally avoids external NLP dependencies. It is a static
prototype that validates the rule primitive artifact's positive and negative
test cases only. It does not write canonical graph data, EGP refs, learner state,
or PracticeBank content.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CAN_NOUN_PATTERNS = (
    re.compile(r"\b(a|the|this|that)\s+can\b", re.IGNORECASE),
    re.compile(r"\bcans\b", re.IGNORECASE),
)

NEGATIVE_CAN_PATTERNS = (
    re.compile(r"\bcan\s+not\b", re.IGNORECASE),
    re.compile(r"\bcannot\b", re.IGNORECASE),
    re.compile(r"\bcan't\b", re.IGNORECASE),
)

QUESTION_START_PATTERN = re.compile(r"^\s*can\b", re.IGNORECASE)
CAN_AUX_PATTERN = re.compile(r"\bcan\s+([a-z]+)\b", re.IGNORECASE)

# Prototype-only A1-oriented lexical policy. This is not a full lexicon and
# must not be treated as a production grammar validator.
INTRANSITIVE_OR_SELF_SUFFICIENT = {
    "swim",
    "run",
    "jump",
    "sing",
    "dance",
    "skate",
    "ski",
    "walk",
    "read",
    "draw",
    "write",
}

TRANSITIVE_REQUIRES_OBJECT = {
    "make",
    "cook",
    "ride",
    "play",
    "use",
    "speak",
    "read",
    "write",
    "draw",
}

PERMISSION_CONTEXT_PATTERNS = (
    re.compile(r"\byou\s+can\s+go\b", re.IGNORECASE),
    re.compile(r"\byou\s+can\s+leave\b", re.IGNORECASE),
    re.compile(r"\byou\s+can\s+use\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class ValidationDecision:
    match: bool
    primitive_id: str | None
    reason: str


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text.lower())


def is_question(text: str) -> bool:
    return text.strip().endswith("?") or bool(QUESTION_START_PATTERN.search(text))


def has_negative_can(text: str) -> bool:
    return any(pattern.search(text) for pattern in NEGATIVE_CAN_PATTERNS)


def has_can_as_noun(text: str) -> bool:
    return any(pattern.search(text) for pattern in CAN_NOUN_PATTERNS)


def has_permission_context(text: str) -> bool:
    return any(pattern.search(text) for pattern in PERMISSION_CONTEXT_PATTERNS)


def classify_can_statement(text: str) -> ValidationDecision:
    """Classify one sentence against the current prototype can-statement rules."""
    stripped = text.strip()
    if not stripped:
        return ValidationDecision(False, None, "empty_text")
    if is_question(stripped):
        return ValidationDecision(False, None, "question_mode_not_affirmative_statement")
    if has_negative_can(stripped):
        return ValidationDecision(False, None, "negative_can_not_scope")
    if has_can_as_noun(stripped):
        return ValidationDecision(False, None, "can_as_noun")
    if has_permission_context(stripped):
        return ValidationDecision(False, None, "permission_meaning_not_ability_without_context")

    match = CAN_AUX_PATTERN.search(stripped)
    if not match:
        return ValidationDecision(False, None, "missing_modal_aux_can")

    tokens = tokenize(stripped)
    try:
        can_index = tokens.index("can")
    except ValueError:
        return ValidationDecision(False, None, "missing_modal_aux_can")

    words_after_can = tokens[can_index + 1 :]
    if not words_after_can:
        return ValidationDecision(False, None, "missing_base_verb")

    verb = words_after_can[0]
    complement_tokens = words_after_can[1:]

    if verb in {"play", "make", "use", "speak"}:
        if not complement_tokens:
            return ValidationDecision(False, None, "missing_required_activity_or_content_complement")
        return ValidationDecision(True, "CAN_AFFIRMATIVE_ACTIVITY_COMPLEMENT", "activity_complement_pattern")

    if verb in {"ride", "cook"}:
        if not complement_tokens:
            return ValidationDecision(False, None, "missing_required_object")
        return ValidationDecision(True, "CAN_AFFIRMATIVE_TRANSITIVE_ABILITY_OBJECT", "transitive_object_pattern")

    if verb in {"read", "write", "draw"}:
        if complement_tokens:
            return ValidationDecision(True, "CAN_AFFIRMATIVE_TRANSITIVE_ABILITY_OBJECT", "transitive_object_pattern")
        return ValidationDecision(True, "CAN_AFFIRMATIVE_INTRANSITIVE_ABILITY_CORE", "self_sufficient_activity_pattern")

    if verb in INTRANSITIVE_OR_SELF_SUFFICIENT:
        return ValidationDecision(True, "CAN_AFFIRMATIVE_INTRANSITIVE_ABILITY_CORE", "intransitive_or_self_sufficient_pattern")

    if verb in TRANSITIVE_REQUIRES_OBJECT and not complement_tokens:
        return ValidationDecision(False, None, "missing_required_object_or_complement")

    # Conservative default: candidate match only if the verb has a complement,
    # because the prototype cannot prove valency without a lexicon/parser.
    if complement_tokens:
        return ValidationDecision(True, "CAN_AFFIRMATIVE_TRANSITIVE_ABILITY_OBJECT", "default_object_pattern")

    return ValidationDecision(False, None, "verb_valency_unknown_without_complement")


def validate_cases(rule_artifact: dict[str, Any]) -> dict[str, Any]:
    positive = rule_artifact.get("positive_test_cases", [])
    negative = rule_artifact.get("negative_test_cases", [])

    case_results: list[dict[str, Any]] = []
    pass_count = 0
    fail_count = 0

    for polarity, cases in (("positive", positive), ("negative", negative)):
        for case in cases:
            text = case["text"]
            expected = bool(case["expected_match"])
            decision = classify_can_statement(text)
            primitive_expected = case.get("primitive_id")
            primitive_ok = (
                not expected
                or primitive_expected is None
                or decision.primitive_id == primitive_expected
            )
            passed = decision.match == expected and primitive_ok
            if passed:
                pass_count += 1
            else:
                fail_count += 1
            case_results.append(
                {
                    "polarity": polarity,
                    "text": text,
                    "expected_match": expected,
                    "actual_match": decision.match,
                    "expected_primitive_id": primitive_expected,
                    "actual_primitive_id": decision.primitive_id,
                    "reason": decision.reason,
                    "status": "PASS" if passed else "FAIL",
                }
            )

    return {
        "total_cases": len(case_results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "case_results": case_results,
    }


def build_report(rule_artifact: dict[str, Any], source_path: str) -> dict[str, Any]:
    validation = validate_cases(rule_artifact)
    test_status = "PASS" if validation["fail_count"] == 0 else "FAIL"
    return {
        "task_id": "R7-M104E17B_CANStatementRulePrimitiveValidatorPrototype_NoNewDesignDocs",
        "artifact_type": "validator_output_report",
        "validator_mode": "offline_static_prototype_no_external_nlp",
        "source_rule_artifact": source_path,
        "scope_constraints": {
            "no_new_design_docs": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_canonical_graph_write": True,
            "no_verified_egp_ref_backfill": True,
            "no_grammar_nodes_json_write": True,
            "no_grammar_coverage_matrix_write": True,
            "no_a2_a2plus_expansion": True,
            "no_external_nlp_dependency_integration": True,
        },
        "prototype_limits": {
            "uses_regex_and_small_lexical_policy_only": True,
            "not_a_runtime_validator": True,
            "not_a_full_parser": True,
            "coverage_claim_allowed": False,
        },
        "validation_summary": {
            "total_cases": validation["total_cases"],
            "pass_count": validation["pass_count"],
            "fail_count": validation["fail_count"],
            "status": test_status,
        },
        "case_results": validation["case_results"],
        "result_status": {
            "validator_prototype_status": "BUILT",
            "test_status": test_status,
            "runtime_validator_status": "NOT_IMPLEMENTED",
            "verified_mapping_status": "NOT_STARTED",
            "coverage_status": "NO_VERIFIED_COVERAGE_CLAIM",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rule-artifact",
        default="ulga/rules/a1_can_statement_rule_primitives.json",
        help="Path to the can statement rule primitive JSON artifact.",
    )
    parser.add_argument(
        "--output",
        default="ulga/reports/a1_can_statement_rule_primitive_validation.json",
        help="Path for validation report JSON.",
    )
    args = parser.parse_args()

    rule_path = Path(args.rule_artifact)
    output_path = Path(args.output)

    with rule_path.open("r", encoding="utf-8") as f:
        rule_artifact = json.load(f)

    report = build_report(rule_artifact, args.rule_artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return 0 if report["validation_summary"]["fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
