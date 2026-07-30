#!/usr/bin/env python3
"""Build the Unit01 authority-grounded approved variant pool.

This milestone keeps the existing 24-item U01E bank as a regression baseline and
materializes a separate policy-bound pool of deterministic, prevalidated variants
for repeated Unit01 practice. Variants are generated offline from the approved
Unit01 vocabulary and phrase contract; learner-time free generation is forbidden.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import (
    build_a1fs_v1_u01data05b_unit01_article_noun_phrase_pattern_reconciliation as pattern_authority,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB01_Unit01PatternFamilyAndApprovedVariantPoolFullBuild"
SCHEMA_VERSION = "a1fs.v1.u01qb01.unit01_pattern_family_approved_variant_pool.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL"
DECISION_REF = "OPERATOR_APPROVAL:2026-07-30:U01QB01"
UNIT_ID = contract_builder.UNIT_ID
BANK_ID = "A1FS_V1_UNIT01_APPROVED_VARIANT_POOL"
BANK_VERSION = "1.0.0"
BASELINE_ACTIVITY_COUNT = 24
APPROVED_CONTRACT_SHA256 = "114376e997275a5ac387d69a16d9d3304096605392c6928e49863d4214efbc29"
EXPECTED_ITEM_COUNT = 109
RAW_COMBINATORIAL_CAPACITY = 944
STRICT_PREVALIDATION_CAPACITY = 848
DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb01_unit01_variant_pool.candidate.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb01_unit01_variant_pool.approved.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb01_unit01_variant_pool_validation.json")
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB02_"
    "Unit01ApprovedVariantSessionAssemblerAndExposureHistoryRuntimeIntegration"
)

PATTERN_NOUN = "U01-NP-ARTICLE-NOUN"
PATTERN_ADJECTIVE = "U01-NP-ARTICLE-ADJECTIVE-NOUN"
PATTERN_VERY = "U01-NP-A-VERY-ADJECTIVE-NOUN"
FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS = ("SP_000016", "SP_000017")

FAMILY_CONTRACTS: tuple[dict[str, Any], ...] = (
    {"family_id": "U01-PF01-AAN-NOUN-GAP", "skill": "WRITING", "question_type": "gap_fill", "pattern_id": PATTERN_NOUN, "expected_count": 16},
    {"family_id": "U01-PF02-AAN-NOUN-CHOICE", "skill": "READING", "question_type": "multiple_choice", "pattern_id": PATTERN_NOUN, "expected_count": 16},
    {"family_id": "U01-PF03-AAN-NOUN-ERROR", "skill": "READING", "question_type": "error_discrimination", "pattern_id": PATTERN_NOUN, "expected_count": 16},
    {"family_id": "U01-PF04-ARTICLE-NOUN-ORDER", "skill": "WRITING", "question_type": "word_order", "pattern_id": PATTERN_NOUN, "expected_count": 16},
    {"family_id": "U01-PF05-AAN-ADJ-NOUN-GAP", "skill": "WRITING", "question_type": "gap_fill", "pattern_id": PATTERN_ADJECTIVE, "expected_count": 6},
    {"family_id": "U01-PF06-ADJ-NOUN-ORDER", "skill": "WRITING", "question_type": "word_order", "pattern_id": PATTERN_ADJECTIVE, "expected_count": 6},
    {"family_id": "U01-PF07-VERY-ADJ-NOUN-ORDER", "skill": "WRITING", "question_type": "word_order", "pattern_id": PATTERN_VERY, "expected_count": 3},
    {"family_id": "U01-PF08-FIRST-TO-KNOWN-THE", "skill": "READING", "question_type": "context_match", "pattern_id": PATTERN_NOUN, "expected_count": 8},
    {"family_id": "U01-PF09-SPEAK-AAN-NOUN", "skill": "SPEAKING", "question_type": "guided_sentence", "pattern_id": PATTERN_NOUN, "expected_count": 16},
    {"family_id": "U01-PF10-SPEAK-ADJ-NOUN", "skill": "SPEAKING", "question_type": "guided_sentence", "pattern_id": PATTERN_ADJECTIVE, "expected_count": 6},
)

DISCOURSE_NOUNS = frozenset({"apple", "bag", "book", "box", "cat", "dog", "egg", "tree"})


class VariantPoolBuildError(ValueError):
    """Fail-closed Unit01 variant-pool construction or admission error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def active_nouns() -> list[dict[str, str]]:
    return [
        {
            "lemma": lemma,
            "evp_sense_id": sense,
            "indefinite_phrase": indefinite,
            "definite_phrase": definite,
        }
        for lemma, sense, _gloss, indefinite, definite, _group in contract_builder.ACTIVE_NOUNS
    ]


def direct_adjective_phrases() -> list[dict[str, str]]:
    noun_sense = {row["lemma"]: row["evp_sense_id"] for row in active_nouns()}
    adjective_sense = {
        lemma: sense
        for lemma, sense, _guideword, _row, _gloss, _memory, _group
        in contract_builder.ACTIVE_ADJECTIVES
    }
    rows: list[dict[str, str]] = []
    for phrase, adjective, noun, article, role in contract_builder.ADJECTIVE_INSTRUCTIONAL_PHRASES:
        if role != "DIRECT_ADJECTIVE_NOUN":
            continue
        rows.append(
            {
                "phrase": phrase,
                "article": article,
                "adjective": adjective,
                "noun": noun,
                "adjective_evp_sense_id": adjective_sense[adjective],
                "noun_evp_sense_id": noun_sense[noun],
            }
        )
    return rows


def very_adjective_phrases() -> list[dict[str, str]]:
    noun_sense = {row["lemma"]: row["evp_sense_id"] for row in active_nouns()}
    adjective_sense = {
        lemma: sense
        for lemma, sense, _guideword, _row, _gloss, _memory, _group
        in contract_builder.ACTIVE_ADJECTIVES
    }
    rows: list[dict[str, str]] = []
    for phrase, adjective, noun, article, role in contract_builder.ADJECTIVE_INSTRUCTIONAL_PHRASES:
        if role != "GUIDED_VERY_ADJECTIVE_NOUN":
            continue
        rows.append(
            {
                "phrase": phrase,
                "article": article,
                "adjective": adjective,
                "noun": noun,
                "adjective_evp_sense_id": adjective_sense[adjective],
                "noun_evp_sense_id": noun_sense[noun],
            }
        )
    return rows


def family_contract(family_id: str) -> Mapping[str, Any]:
    return next(row for row in FAMILY_CONTRACTS if row["family_id"] == family_id)


def article_from_phrase(phrase: str) -> str:
    return phrase.split()[0].lower()


def wrong_indefinite(article: str) -> str:
    return "an" if article == "a" else "a"


def response_contract(
    *,
    scoring_mode: str,
    correct_answer: Any,
    accepted_answers: Sequence[str],
    speaking: bool = False,
) -> dict[str, Any]:
    if speaking:
        return {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "accepted_texts": list(accepted_answers),
            "accepted_sequence": [],
            "human_review_fallback": True,
            "capture_enabled": False,
            "rubric": {"practice_only": True, "article_noun_phrase_target": True},
        }
    if scoring_mode == "EXACT_SEQUENCE":
        return {
            "scoring_mode": scoring_mode,
            "response_type": "sequence",
            "accepted_texts": [],
            "accepted_sequence": list(correct_answer),
            "human_review_fallback": False,
            "capture_enabled": True,
        }
    return {
        "scoring_mode": scoring_mode,
        "response_type": "string",
        "accepted_texts": list(dict.fromkeys(str(value) for value in accepted_answers)),
        "accepted_sequence": [],
        "human_review_fallback": False,
        "capture_enabled": True,
    }


def make_item(
    *,
    family_id: str,
    token: str,
    prompt: str,
    stimulus: str,
    options: Sequence[str],
    correct_answer: Any,
    accepted_answers: Sequence[str],
    target_evp_sense_ids: Sequence[str],
    target_egp_row_ids: Sequence[str],
    target_pattern_id: str,
    scoring_mode: str,
    support_level: str,
    transfer_eligible: bool = False,
) -> dict[str, Any]:
    family = family_contract(family_id)
    speaking = family["skill"] == "SPEAKING"
    item = {
        "item_id": f"U01QB01-{slug(family_id)}-{slug(token)}",
        "unit_id": UNIT_ID,
        "pattern_family_id": family_id,
        "unit_pattern_ids": [target_pattern_id],
        "grammar_target_ids": [
            "ARTICLE_NOUN_PHRASE_CONTROL",
            "ARTICLE_FIRST_TO_KNOWN_REFERENCE" if family_id == "U01-PF08-FIRST-TO-KNOWN-THE"
            else "ARTICLE_FORM_SELECTION",
        ],
        "target_egp_row_ids": sorted(str(value) for value in target_egp_row_ids),
        "target_evp_sense_ids": sorted(str(value) for value in target_evp_sense_ids),
        "skill": family["skill"],
        "question_type": family["question_type"],
        "prompt": prompt,
        "stimulus": stimulus,
        "options": list(options),
        "correct_answer": deepcopy(correct_answer),
        "accepted_answers": list(accepted_answers),
        "scoring_mode": scoring_mode,
        "support_level": support_level,
        "learner_visible_capable": True,
        "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
        "assessment_eligible": not speaking,
        "transfer_eligible": transfer_eligible,
        "reassessment_eligible": not speaking,
        "human_review_required": False,
        "audio_required": False,
        "speaking_capture_enabled": False,
        "runtime_generation_used": False,
        "source_refs": [
            {
                "source_type": "UNIT01_APPROVED_CONTENT_CONTRACT",
                "task_id": contract_builder.TASK_ID,
                "contract_sha256": APPROVED_CONTRACT_SHA256,
            },
            {
                "source_type": "UNIT01_LOCAL_PATTERN_AUTHORITY",
                "task_id": pattern_authority.TASK_ID,
                "pattern_id": target_pattern_id,
            },
        ],
    }
    signature_payload = {
        "family": family_id,
        "pattern": target_pattern_id,
        "prompt": prompt,
        "stimulus": stimulus,
        "options": list(options),
        "correct_answer": correct_answer,
        "evp": item["target_evp_sense_ids"],
        "egp": item["target_egp_row_ids"],
    }
    item["semantic_signature"] = digest(signature_payload)
    item["response_contract"] = response_contract(
        scoring_mode=scoring_mode,
        correct_answer=correct_answer,
        accepted_answers=accepted_answers,
        speaking=speaking,
    )
    return item


def noun_items() -> list[dict[str, Any]]:
    egp = [contract_builder.CORE_EGP_ROWS[0]]
    items: list[dict[str, Any]] = []
    for row in active_nouns():
        lemma = row["lemma"]
        sense = row["evp_sense_id"]
        phrase = row["indefinite_phrase"]
        article = article_from_phrase(phrase)
        wrong = wrong_indefinite(article)
        items.extend(
            [
                make_item(
                    family_id="U01-PF01-AAN-NOUN-GAP",
                    token=lemma,
                    prompt=f"Complete with a or an: ___ {lemma}",
                    stimulus="",
                    options=[],
                    correct_answer=article,
                    accepted_answers=[article],
                    target_evp_sense_ids=[sense],
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode="NORMALIZED_TEXT",
                    support_level="GUIDED",
                ),
                make_item(
                    family_id="U01-PF02-AAN-NOUN-CHOICE",
                    token=lemma,
                    prompt=f"Choose the article for one new {lemma}.",
                    stimulus=f"___ {lemma}",
                    options=["a", "an"],
                    correct_answer=article,
                    accepted_answers=[article],
                    target_evp_sense_ids=[sense],
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode="EXACT_OPTION",
                    support_level="GUIDED",
                ),
                make_item(
                    family_id="U01-PF03-AAN-NOUN-ERROR",
                    token=lemma,
                    prompt="Choose the correct noun phrase.",
                    stimulus="",
                    options=[phrase, f"{wrong} {lemma}"],
                    correct_answer=phrase,
                    accepted_answers=[phrase],
                    target_evp_sense_ids=[sense],
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode="EXACT_OPTION",
                    support_level="REDUCED_SUPPORT",
                ),
                make_item(
                    family_id="U01-PF04-ARTICLE-NOUN-ORDER",
                    token=lemma,
                    prompt="Put the words in order to name one item.",
                    stimulus="",
                    options=[lemma, article],
                    correct_answer=[article, lemma],
                    accepted_answers=[],
                    target_evp_sense_ids=[sense],
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode="EXACT_SEQUENCE",
                    support_level="REDUCED_SUPPORT",
                ),
                make_item(
                    family_id="U01-PF09-SPEAK-AAN-NOUN",
                    token=lemma,
                    prompt=f"Say the phrase for one {lemma}.",
                    stimulus=lemma,
                    options=[],
                    correct_answer=None,
                    accepted_answers=[phrase],
                    target_evp_sense_ids=[sense],
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode="FEATURE_RUBRIC",
                    support_level="GUIDED",
                ),
            ]
        )
        if lemma in DISCOURSE_NOUNS:
            items.append(
                make_item(
                    family_id="U01-PF08-FIRST-TO-KNOWN-THE",
                    token=lemma,
                    prompt="Choose the article for the same noun the second time.",
                    stimulus=f"There is {phrase} here. ___ {lemma} is easy to see.",
                    options=["a", "an", "the"],
                    correct_answer="the",
                    accepted_answers=["the"],
                    target_evp_sense_ids=[sense],
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode="EXACT_OPTION",
                    support_level="INDEPENDENT",
                    transfer_eligible=True,
                )
            )
    return items


def adjective_items() -> list[dict[str, Any]]:
    egp = [contract_builder.CORE_EGP_ROWS[1]]
    items: list[dict[str, Any]] = []
    for row in direct_adjective_phrases():
        phrase = row["phrase"]
        article = row["article"]
        adjective = row["adjective"]
        noun = row["noun"]
        senses = [row["adjective_evp_sense_id"], row["noun_evp_sense_id"]]
        token = f"{adjective}-{noun}"
        items.extend(
            [
                make_item(
                    family_id="U01-PF05-AAN-ADJ-NOUN-GAP",
                    token=token,
                    prompt=f"Complete with a or an: ___ {adjective} {noun}",
                    stimulus="",
                    options=[],
                    correct_answer=article,
                    accepted_answers=[article],
                    target_evp_sense_ids=senses,
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_ADJECTIVE,
                    scoring_mode="NORMALIZED_TEXT",
                    support_level="GUIDED",
                ),
                make_item(
                    family_id="U01-PF06-ADJ-NOUN-ORDER",
                    token=token,
                    prompt="Put the words in order to describe one item.",
                    stimulus="",
                    options=[noun, article, adjective],
                    correct_answer=[article, adjective, noun],
                    accepted_answers=[],
                    target_evp_sense_ids=senses,
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_ADJECTIVE,
                    scoring_mode="EXACT_SEQUENCE",
                    support_level="REDUCED_SUPPORT",
                ),
                make_item(
                    family_id="U01-PF10-SPEAK-ADJ-NOUN",
                    token=token,
                    prompt=f"Say the phrase for one {adjective} {noun}.",
                    stimulus=f"{adjective} {noun}",
                    options=[],
                    correct_answer=None,
                    accepted_answers=[phrase],
                    target_evp_sense_ids=senses,
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_ADJECTIVE,
                    scoring_mode="FEATURE_RUBRIC",
                    support_level="GUIDED",
                ),
            ]
        )
    return items


def very_items() -> list[dict[str, Any]]:
    egp = [contract_builder.GUIDED_EGP_ROWS[0]]
    items: list[dict[str, Any]] = []
    for row in very_adjective_phrases():
        adjective = row["adjective"]
        noun = row["noun"]
        senses = [row["adjective_evp_sense_id"], row["noun_evp_sense_id"]]
        items.append(
            make_item(
                family_id="U01-PF07-VERY-ADJ-NOUN-ORDER",
                token=f"{adjective}-{noun}",
                prompt="Put the words in order to make the guided phrase.",
                stimulus="",
                options=[noun, "very", "a", adjective],
                correct_answer=["a", "very", adjective, noun],
                accepted_answers=[],
                target_evp_sense_ids=senses,
                target_egp_row_ids=egp,
                target_pattern_id=PATTERN_VERY,
                scoring_mode="EXACT_SEQUENCE",
                support_level="GUIDED_EXTENSION",
            )
        )
    return items


def build_items() -> list[dict[str, Any]]:
    items = noun_items() + adjective_items() + very_items()
    items.sort(key=lambda row: row["item_id"])
    if len(items) != EXPECTED_ITEM_COUNT:
        raise VariantPoolBuildError(f"ITEM_COUNT_INVALID:{len(items)}")
    identities = [row["item_id"] for row in items]
    signatures = [row["semantic_signature"] for row in items]
    if len(identities) != len(set(identities)):
        raise VariantPoolBuildError("DUPLICATE_ITEM_ID")
    if len(signatures) != len(set(signatures)):
        raise VariantPoolBuildError("DUPLICATE_SEMANTIC_SIGNATURE")
    return items


def design_space_capacity() -> dict[str, Any]:
    noun_count = len(contract_builder.ACTIVE_NOUNS)
    adjective_count = len(contract_builder.ACTIVE_ADJECTIVES)
    context_count = 5
    safe_intensifier_adjective_count = 4
    raw = (
        noun_count
        + noun_count * adjective_count
        + noun_count * adjective_count
        + noun_count * context_count
        + noun_count * context_count
        + (noun_count + noun_count * adjective_count + noun_count * adjective_count)
        + (noun_count + noun_count * adjective_count + noun_count * adjective_count)
        + noun_count * context_count * 2
    )
    strict = (
        noun_count
        + noun_count * adjective_count
        + noun_count * safe_intensifier_adjective_count
        + noun_count * context_count
        + noun_count * context_count
        + (noun_count + noun_count * adjective_count + noun_count * safe_intensifier_adjective_count)
        + (noun_count + noun_count * adjective_count + noun_count * safe_intensifier_adjective_count)
        + noun_count * context_count * 2
    )
    if raw != RAW_COMBINATORIAL_CAPACITY or strict != STRICT_PREVALIDATION_CAPACITY:
        raise VariantPoolBuildError(f"DESIGN_SPACE_CAPACITY_DRIFT:{raw}:{strict}")
    return {
        "active_noun_count": noun_count,
        "active_adjective_count": adjective_count,
        "context_count": context_count,
        "safe_intensifier_adjective_count": safe_intensifier_adjective_count,
        "raw_combinatorial_capacity": raw,
        "strict_prevalidation_capacity": strict,
        "materialized_authority_grounded_candidate_count": EXPECTED_ITEM_COUNT,
    }


def candidate_payload() -> dict[str, Any]:
    items = build_items()
    family_counts = dict(sorted(Counter(row["pattern_family_id"] for row in items).items()))
    skill_counts = dict(sorted(Counter(row["skill"] for row in items).items()))
    question_type_counts = dict(sorted(Counter(row["question_type"] for row in items).items()))
    pattern_counts = dict(
        sorted(Counter(pattern for row in items for pattern in row["unit_pattern_ids"]).items())
    )
    evp_sense_ids = sorted({sense for row in items for sense in row["target_evp_sense_ids"]})
    egp_row_ids = sorted({egp for row in items for egp in row["target_egp_row_ids"]})
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "bank_identity": {
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "unit_id": UNIT_ID,
            "level_scope": ["A1"],
            "generation_mode": "OFFLINE_DETERMINISTIC_AUTHORITY_GROUNDED_VARIANTS",
            "learner_runtime_free_generation_allowed": False,
        },
        "design_space_capacity": design_space_capacity(),
        "baseline_bank_contract": {
            "baseline_activity_count": BASELINE_ACTIVITY_COUNT,
            "baseline_role": "REGRESSION_AND_INTEGRATION_ACCEPTANCE_ONLY",
            "baseline_items_copied_into_variant_pool": False,
            "routine_session_delivery_uses_baseline_by_default": False,
        },
        "pattern_family_contracts": [deepcopy(row) for row in FAMILY_CONTRACTS],
        "candidate_items": items,
        "distribution_counts": {
            "family": family_counts,
            "skill": skill_counts,
            "question_type": question_type_counts,
            "unit_pattern": pattern_counts,
        },
        "coverage_denominators": {
            "active_evp_sense_count": len(evp_sense_ids),
            "active_evp_sense_ids": evp_sense_ids,
            "exercise_covered_egp_row_count": len(egp_row_ids),
            "exercise_covered_egp_row_ids": egp_row_ids,
            "a1_egp_denominator": 109,
            "learner_mastery_claimed": False,
            "ket_canonical_prerequisite_node_claimed": False,
            "semantic_ket_prerequisite_capability": "ARTICLE_NOUN_PHRASE_CONTROL",
        },
        "session_assembly_metadata": {
            "runtime_status": "NOT_CONNECTED_METADATA_ONLY",
            "session_size": 10,
            "pool_source": "APPROVED_VARIANTS_ONLY",
            "selection_quota": {
                "new_or_unseen": 4,
                "remediation": 2,
                "scheduled_review": 2,
                "transfer": 1,
                "guided_extension": 1,
            },
            "recent_exposure_exclusion": {
                "same_item_within_session_forbidden": True,
                "exclude_last_n_item_exposures": 10,
                "assessment_prefers_unseen_items": True,
                "reassessment_replays_original_item_by_default": False,
            },
        },
        "admission_policy": {
            "independent_validation_required": True,
            "semantic_dedup_required": True,
            "approved_contract_phrases_only_for_adjective_combinations": True,
            "approved_bank_required_before_runtime": True,
            "unvalidated_variant_delivery_allowed": False,
            "learner_time_generation_allowed": False,
        },
        "claim_boundaries": {
            "global_pattern_authority_modified": False,
            "existing_pattern_ids_redefined": False,
            "demonstrative_patterns_in_unit01": False,
            "unit02_to_unit24_modified": False,
            "learner_database_written": False,
            "runtime_bundle_written": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "learner_mastery_claimed": False,
            "ket_granular_node_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate() -> dict[str, Any]:
    payload = candidate_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "unit01_contract_task_id": contract_builder.TASK_ID,
            "unit01_approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "u01data05b_task_id": pattern_authority.TASK_ID,
            "unit_local_pattern_ids": [PATTERN_NOUN, PATTERN_ADJECTIVE, PATTERN_VERY],
            "baseline_activity_count": BASELINE_ACTIVITY_COUNT,
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator,
    )

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def materialize(
    *,
    candidate_path: Path,
    approved_path: Path,
    report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import (
        validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator,
    )

    report = validator.validate_approved(candidate, approved)
    if report["error_count"]:
        raise VariantPoolBuildError("APPROVED_VALIDATION_FAILED:" + "|".join(report["errors"]))
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        _, approved, report = materialize(
            candidate_path=args.candidate.resolve(),
            approved_path=args.approved.resolve(),
            report_path=args.report.resolve(),
        )
    except (
        VariantPoolBuildError,
        policy_artifact.ContentPolicyBuildError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"APPROVED_VARIANT_COUNT={len(payload['candidate_items'])}")
    print(f"PATTERN_FAMILY_COUNT={len(payload['pattern_family_contracts'])}")
    print(f"ACTIVE_EVP_SENSE_COUNT={payload['coverage_denominators']['active_evp_sense_count']}")
    print(f"EXERCISE_COVERED_EGP_ROW_COUNT={payload['coverage_denominators']['exercise_covered_egp_row_count']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
