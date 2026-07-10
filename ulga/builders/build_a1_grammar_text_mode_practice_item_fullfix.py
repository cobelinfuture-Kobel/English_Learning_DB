#!/usr/bin/env python3
"""Replace placeholder A1/A1+ Reading/Writing activities with reviewable items."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item

TASK_ID = "R7-M105K_A1A1PlusTextModePracticeItemFullFix"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105L_A1A1PlusDerivedPedagogyFullFix"
DECISIONS_PATH = REPO_ROOT / "ulga/reviews/a1_grammar_text_mode_review_decisions.json"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_text_mode_practice_items_fullfix.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_text_mode_practice_items_fullfix_validation.json"

GENERIC_PROMPTS = {
    "Choose the option that uses the target grammar correctly.",
    "Choose the target form that matches the short context.",
    "Identify the correctly formed target example.",
    "Complete the target form.",
    "Put the words in the correct order.",
    "Write a sentence for the context using the target grammar.",
    "Select the correct target sentence or phrase.",
    "Produce one sentence or phrase with the target grammar.",
}
PLACEHOLDER_OPTIONS = {"Not the target form", "Incorrect contrast", "Incorrect form"}

FOCUS_TOKEN_INDEX = {
    "GRAMMAR_ARTICLES_BASIC": 0,
    "GRAMMAR_SUBJECT_PRONOUNS": 0,
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": -2,
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": 0,
    "GRAMMAR_CAN_STATEMENT": 1,
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES": 1,
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS": 0,
    "GRAMMAR_THERE_IS": 1,
    "GRAMMAR_BE_INTERROGATIVES_A1": 0,
    "GRAMMAR_CAN_NEGATIVE_A1": 1,
    "GRAMMAR_WILL_FUTURE_A1": 1,
    "GRAMMAR_PAST_SIMPLE_A1": 1,
    "GRAMMAR_REGULAR_PLURAL_NOUNS": 0,
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": 0,
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS": 1,
    "GRAMMAR_BE_VERB_BASIC": 1,
    "GRAMMAR_ADJECTIVE_PHRASES_A1": 0,
    "GRAMMAR_COORDINATION_A1": 1,
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1": -3,
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1": 1,
    "GRAMMAR_ADVERB_PHRASES_A1": -2,
    "GRAMMAR_NOUN_PHRASES_A1": 0,
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1": 1,
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": 0,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value.strip()))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+|[^\w\s]", text)


def _focus_index(grammar_id: str, tokens: list[str]) -> int:
    if not tokens:
        raise ValueError(f"target_has_no_tokens:{grammar_id}")
    index = FOCUS_TOKEN_INDEX.get(grammar_id, 0)
    if index < 0:
        index = len(tokens) + index
    return max(0, min(index, len(tokens) - 1))


def _ordered_distractors(unit: Mapping[str, Any], target: str) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for item in unit.get("negative_examples", []):
        text = item.get("text")
        if not isinstance(text, str) or not text.strip() or text == target:
            continue
        values.append(
            {
                "text": text,
                "error_tag": item.get("error_tag", "ERR_NON_TARGET_FORM"),
                "rationale": item.get("correction", "This option does not match the target grammar."),
            }
        )
    if len(values) < 2:
        raise ValueError(f"insufficient_real_distractors:{unit.get('grammar_unit_id')}")
    return values


def _gate(grammar_id: str, text: str, role: str) -> dict[str, Any]:
    return {
        "gate_version": "a1_practice_item_grammar_gate.v1",
        "validation_targets": [{"grammar_id": grammar_id, "text": text, "target_role": role}],
        "require_all_focus_matches": True,
        "validator_mode": "OFFLINE_STATIC_PROTOTYPE",
        "production_runtime_validator": False,
        "learner_state_write": False,
    }


def _base_item(
    unit: Mapping[str, Any],
    *,
    code: str,
    skill: str,
    dimension: str,
    role: str,
    task_type: str,
    prompt: str,
    target: str,
    response_mode: str,
) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    return {
        "item_id": f"{grammar_id}__TFX_{code}",
        "item_role": role,
        "skill": skill,
        "evidence_dimension": dimension,
        "task_type": task_type,
        "prompt": prompt,
        "response_mode": response_mode,
        "answer_key": {"accepted_texts": [target], "canonical_target": target},
        "content_binding": {
            "grammar_focus": [grammar_id],
            "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
        },
        "grammar_gate": _gate(grammar_id, target, f"text_mode_fullfix_{skill}_{dimension}"),
        "source_trace": {
            "content_origin": "project_authored_text_mode_fullfix",
            "source_unit_id": grammar_id,
            "raw_external_source_text_copied": False,
            "restricted_source_payload_persisted": False,
        },
        "review_remediation": {
            "source_task": TASK_ID,
            "placeholder_prompt_removed": True,
            "placeholder_distractor_removed": True,
        },
    }


def _context(unit: Mapping[str, Any], target: str, *, purpose: str) -> dict[str, Any]:
    meaning = next(iter(unit.get("meaning_functions", [])), "express the target grammar meaning")
    usage = next(iter(unit.get("usage_conditions", [])), "Use the target form accurately.")
    return {
        "situation": f"A learner needs to {meaning} in a short A1 message.",
        "communicative_goal": purpose,
        "grammar_clue": usage,
        "model_target": target,
    }


def _choice_item(
    unit: Mapping[str, Any],
    *,
    code: str,
    dimension: str,
    role: str,
    target: str,
    distractors: list[dict[str, str]],
    context_required: bool,
) -> dict[str, Any]:
    title = unit.get("title_en", unit["grammar_unit_id"])
    prompt = (
        f"Read the situation and choose the option that correctly uses {title}."
        if context_required
        else f"Which option correctly uses {title}?"
    )
    item = _base_item(
        unit,
        code=code,
        skill="reading",
        dimension=dimension,
        role=role,
        task_type="context_choice" if context_required else "form_choice",
        prompt=prompt,
        target=target,
        response_mode="select_one",
    )
    options = [target, distractors[0]["text"], distractors[1]["text"]]
    item["options"] = options
    item["option_rationales"] = {
        target: "This option matches the declared grammar target.",
        distractors[0]["text"]: distractors[0]["rationale"],
        distractors[1]["text"]: distractors[1]["rationale"],
    }
    item["distractor_error_tags"] = {
        distractors[0]["text"]: distractors[0]["error_tag"],
        distractors[1]["text"]: distractors[1]["error_tag"],
    }
    if context_required:
        item["context"] = _context(unit, target, purpose="select the form that fits the intended meaning")
    return item


def _gap_item(unit: Mapping[str, Any], target: str) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    tokens = _tokens(target)
    index = _focus_index(grammar_id, tokens)
    missing = tokens[index]
    display = tokens[:]
    display[index] = "____"
    item = _base_item(
        unit,
        code="P04",
        skill="writing",
        dimension="controlled_production",
        role="practice",
        task_type="structured_gap_fill",
        prompt=f"Complete the sentence or phrase with the missing target form: {' '.join(display)}",
        target=target,
        response_mode="short_text",
    )
    item["gap_spec"] = {
        "display_tokens": display,
        "missing_token_index": index,
        "accepted_missing_tokens": [missing],
        "full_answer_tokens": tokens,
    }
    item["accepted_variation_policy"] = {
        "exact_missing_token_required": True,
        "case_insensitive": missing.lower() != "I".lower(),
        "punctuation_tolerance": True,
    }
    return item


def _word_order_item(unit: Mapping[str, Any], target: str) -> dict[str, Any]:
    tokens = _tokens(target)
    if len(tokens) < 2:
        shuffled = tokens + ["[single-token-target]"]
    else:
        shuffled = tokens[1:] + tokens[:1]
        if shuffled == tokens:
            shuffled = list(reversed(tokens))
    item = _base_item(
        unit,
        code="P05",
        skill="writing",
        dimension="controlled_production",
        role="practice",
        task_type="structured_word_order",
        prompt="Put the supplied tokens in the correct order to make the target sentence or phrase.",
        target=target,
        response_mode="ordered_tokens",
    )
    item["token_sequence"] = shuffled
    item["correct_token_sequence"] = tokens
    item["accepted_variation_policy"] = {
        "token_order_exact": True,
        "terminal_punctuation_tolerance": True,
        "contraction_variants_allowed": False,
    }
    return item


def _productive_item(
    unit: Mapping[str, Any],
    *,
    code: str,
    role: str,
    dimension: str,
    target: str,
) -> dict[str, Any]:
    title = unit.get("title_en", unit["grammar_unit_id"])
    context = _context(unit, target, purpose="produce a complete response using the target grammar")
    item = _base_item(
        unit,
        code=code,
        skill="writing",
        dimension=dimension,
        role=role,
        task_type="guided_contextual_writing" if role == "practice" else "text_mode_writing_checkpoint",
        prompt=f"Write one complete A1 sentence or phrase for the situation using {title}.",
        target=target,
        response_mode="short_text",
    )
    item["context"] = context
    item["scoring_rubric"] = {
        "grammar_target_match": {"required": True, "weight": 0.5},
        "meaning_matches_context": {"required": True, "weight": 0.3},
        "complete_response": {"required": True, "weight": 0.2},
        "minimum_score": 0.8,
    }
    item["accepted_variation_policy"] = {
        "canonical_target_is_model_not_only_answer": True,
        "lexical_substitution_allowed": True,
        "subject_or_object_substitution_allowed_when_agreement_preserved": True,
        "target_grammar_must_remain_detectable": True,
        "manual_review_required_for_non_exact_match": True,
    }
    return item


def build_unit_items(unit: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positives = _unique(item.get("text", "") for item in unit.get("positive_examples", []))
    if len(positives) < 2:
        raise ValueError(f"insufficient_positive_targets:{unit.get('grammar_unit_id')}")
    first, second = positives[0], positives[1]
    third = positives[2] if len(positives) > 2 else first
    distractors = _ordered_distractors(unit, first)
    practice = [
        _choice_item(unit, code="P01", dimension="recognition", role="practice", target=first, distractors=distractors, context_required=False),
        _choice_item(unit, code="P02", dimension="meaning", role="practice", target=second, distractors=distractors, context_required=True),
        _choice_item(unit, code="P03", dimension="contrast", role="practice", target=third, distractors=list(reversed(distractors)), context_required=False),
        _gap_item(unit, first),
        _word_order_item(unit, second),
        _productive_item(unit, code="P06", role="practice", dimension="contextual_production", target=third),
    ]
    assessments = [
        _choice_item(unit, code="A01", dimension="receptive_checkpoint", role="assessment", target=first, distractors=distractors, context_required=True),
        _productive_item(unit, code="A02", role="assessment", dimension="productive_checkpoint", target=second),
    ]
    return practice, assessments


def build_artifact(candidate: Mapping[str, Any], decisions: Mapping[str, Any]) -> dict[str, Any]:
    units = candidate.get("learning_units", [])
    decision_items = decisions.get("decisions", [])
    decision_by_id = {item["grammar_unit_id"]: item for item in decision_items}
    if len(units) != 24 or len(decision_by_id) != 24:
        raise ValueError("fullfix_source_not_24_units")
    if any(item.get("decision") != "NEEDS_REVISION" for item in decision_items):
        raise ValueError("fullfix_requires_needs_revision_decisions")

    output_units: list[dict[str, Any]] = []
    row_index: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"grammar_unit_ids": set(), "reading_item_ids": [], "writing_item_ids": [], "assessment_item_ids": []}
    )
    all_items: list[dict[str, Any]] = []
    for source_unit in units:
        unit = deepcopy(source_unit)
        practice, assessments = build_unit_items(unit)
        unit["practice_items"] = practice
        unit["assessment_items"] = assessments
        unit["text_mode_practice_fullfix_status"] = "FULLFIX_APPLIED_PENDING_PEDAGOGY_REVIEW"
        output_units.append(unit)
        for item in practice + assessments:
            all_items.append(item)
            for row_id in unit["canonical_egp_row_ids"]:
                row = row_index[row_id]
                row["grammar_unit_ids"].add(unit["grammar_unit_id"])
                if item["skill"] == "reading":
                    row["reading_item_ids"].append(item["item_id"])
                else:
                    row["writing_item_ids"].append(item["item_id"])
                if item["item_role"] == "assessment":
                    row["assessment_item_ids"].append(item["item_id"])

    by_row = {
        row_id: {
            "egp_row_id": row_id,
            "grammar_unit_ids": sorted(value["grammar_unit_ids"]),
            "reading_item_ids": sorted(set(value["reading_item_ids"])),
            "writing_item_ids": sorted(set(value["writing_item_ids"])),
            "assessment_item_ids": sorted(set(value["assessment_item_ids"])),
            "text_mode_practice_fullfix_status": "READY_FOR_PEDAGOGY_REVIEW",
        }
        for row_id, value in sorted(row_index.items())
    }
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_practice_items_fullfix",
        "artifact_type": "a1_a1plus_reviewable_text_mode_practice_and_assessment_bank",
        "schema_version": "a1_grammar_text_mode_practice_items_fullfix.v1",
        "coverage_summary": {
            "canonical_unit_count": len(output_units),
            "canonical_row_count": len(by_row),
            "practice_item_count": sum(item["item_role"] == "practice" for item in all_items),
            "assessment_item_count": sum(item["item_role"] == "assessment" for item in all_items),
            "reading_item_count": sum(item["skill"] == "reading" for item in all_items),
            "writing_item_count": sum(item["skill"] == "writing" for item in all_items),
            "total_item_count": len(all_items),
            "placeholder_prompt_count": sum(item["prompt"] in GENERIC_PROMPTS for item in all_items),
            "placeholder_option_count": sum(bool(PLACEHOLDER_OPTIONS.intersection(item.get("options", []))) for item in all_items),
            "operator_approved_unit_count": 0,
            "text_mode_pilot_eligible_row_count": 0,
        },
        "learning_units": output_units,
        "item_bank": all_items,
        "by_egp_row_id": by_row,
        "claim_boundaries": {
            "text_mode_practice_item_fullfix_complete": True,
            "derived_pedagogy_fullfix_complete": False,
            "operator_review_complete": False,
            "text_mode_private_pilot_eligible": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(artifact: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    units = artifact.get("learning_units", [])
    items = artifact.get("item_bank", [])
    rows = artifact.get("by_egp_row_id", {})
    summary = artifact.get("coverage_summary", {})
    expected_units = {unit["grammar_unit_id"] for unit in candidate.get("learning_units", [])}
    actual_units = {unit.get("grammar_unit_id") for unit in units}
    if len(units) != 24 or actual_units != expected_units:
        errors.append("fullfix_unit_set_not_24")
    if len(rows) != 109 or set(rows) != set(candidate.get("by_egp_row_id", {})):
        errors.append("fullfix_row_set_not_109")
    item_ids: set[str] = set()
    gate_count = 0
    for item in items:
        item_id = item.get("item_id")
        if not item_id or item_id in item_ids:
            errors.append(f"duplicate_or_missing_item_id:{item_id}")
        item_ids.add(item_id)
        if item.get("prompt") in GENERIC_PROMPTS:
            errors.append(f"generic_prompt_remains:{item_id}")
        if PLACEHOLDER_OPTIONS.intersection(item.get("options", [])):
            errors.append(f"placeholder_option_remains:{item_id}")
        task_type = item.get("task_type")
        if task_type == "context_choice" and not item.get("context"):
            errors.append(f"context_payload_missing:{item_id}")
        if task_type == "structured_gap_fill" and not item.get("gap_spec"):
            errors.append(f"gap_spec_missing:{item_id}")
        if task_type == "structured_word_order" and not item.get("token_sequence"):
            errors.append(f"token_sequence_missing:{item_id}")
        if item.get("skill") == "writing" and not item.get("accepted_variation_policy"):
            errors.append(f"variation_policy_missing:{item_id}")
        if task_type in {"guided_contextual_writing", "text_mode_writing_checkpoint"} and not item.get("scoring_rubric"):
            errors.append(f"scoring_rubric_missing:{item_id}")
        source = item.get("source_trace", {})
        if source.get("raw_external_source_text_copied") is not False or source.get("restricted_source_payload_persisted") is not False:
            errors.append(f"unsafe_source_payload:{item_id}")
        gate = validate_practice_item(item)
        gate_count += gate.get("validation_target_count", 0)
        if gate.get("gate_status") != "PASS":
            errors.append(f"grammar_gate_fail:{item_id}")
    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_row_count": 109,
        "practice_item_count": 144,
        "assessment_item_count": 48,
        "reading_item_count": 96,
        "writing_item_count": 96,
        "total_item_count": 192,
        "placeholder_prompt_count": 0,
        "placeholder_option_count": 0,
        "operator_approved_unit_count": 0,
        "text_mode_pilot_eligible_row_count": 0,
    }
    if summary != expected_summary:
        errors.append("coverage_summary_mismatch")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("derived_pedagogy_fullfix_complete") is not False:
        errors.append("false_derived_pedagogy_completion")
    if boundaries.get("operator_review_complete") is not False:
        errors.append("false_operator_review_completion")
    if boundaries.get("audio_scope_deferred") is not True or boundaries.get("audio_scope_complete") is not False:
        errors.append("audio_defer_boundary_drift")
    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "coverage_summary": expected_summary,
        "validation_counts": {"unique_item_id_count": len(item_ids), "grammar_gate_target_count": gate_count},
        "gate_checks": {
            "units_24_of_24": len(units) == 24,
            "rows_109_of_109": len(rows) == 109,
            "items_192_of_192": len(items) == 192,
            "placeholder_prompts_removed": not any(error.startswith("generic_prompt_remains") for error in errors),
            "placeholder_options_removed": not any(error.startswith("placeholder_option_remains") for error in errors),
            "structured_writing_payloads_present": not any(error.split(":", 1)[0] in {"gap_spec_missing", "token_sequence_missing", "variation_policy_missing", "scoring_rubric_missing"} for error in errors),
            "all_grammar_gates_pass": not any(error.startswith("grammar_gate_fail") for error in errors),
        },
        "errors": errors,
        "warnings": [
            "PracticeItem structure is full-fixed, but the 18 derived units still require unit-specific pedagogy rewrite.",
            "Operator review and text-mode pilot promotion remain blocked."
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, candidate_report = build_candidate_source()
    if candidate_report.get("validation_status") != "PASS":
        raise RuntimeError("candidate_source_validation_failed")
    decisions = load_json(DECISIONS_PATH)
    artifact = build_artifact(candidate, decisions)
    report = validate_artifact(artifact, candidate)
    return artifact, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact, report = build_and_validate_from_repo()
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
