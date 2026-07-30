#!/usr/bin/env python3
"""Build the full Unit01 candidate space and validator-admitted variant pool.

The existing 24 U01E activities remain a regression baseline. This milestone
materializes the complete strict Unit01 candidate space, records a deterministic
per-item admission proposal, and exposes only the independently validated subset
as approved variants. Learner-time free generation is forbidden.
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
SCHEMA_VERSION = "a1fs.v1.u01qb01.unit01_pattern_family_approved_variant_pool.v2"
PASS_STATUS = "PASS_A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL"
DECISION_REF = "OPERATOR_APPROVAL:2026-07-30:U01QB01"
UNIT_ID = contract_builder.UNIT_ID
BANK_ID = "A1FS_V1_UNIT01_APPROVED_VARIANT_POOL"
BANK_VERSION = "2.0.0"
BASELINE_ACTIVITY_COUNT = 24
APPROVED_CONTRACT_SHA256 = "114376e997275a5ac387d69a16d9d3304096605392c6928e49863d4214efbc29"

RAW_COMBINATORIAL_CAPACITY = 944
STRICT_PREVALIDATION_CAPACITY = 848
SPEAKING_EXTENSION_CANDIDATE_COUNT = 25
EXPECTED_CANDIDATE_COUNT = 873
EXPECTED_APPROVED_COUNT = 288
EXPECTED_REJECTED_COUNT = 585
LANGUAGE_ASSET_COMBINATION_COUNT = 25

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
SAFE_INTENSIFIER_ADJECTIVES = ("big", "new", "old", "small")

FAMILY_CONTRACTS: tuple[dict[str, Any], ...] = (
    {"family_id": "U01-PF01-AAN-NOUN-GAP", "skill": "WRITING", "question_type": "gap_fill", "candidate_count": 16, "approved_count": 16},
    {"family_id": "U01-PF02-AAN-ADJ-NOUN-GAP", "skill": "WRITING", "question_type": "gap_fill", "candidate_count": 96, "approved_count": 6},
    {"family_id": "U01-PF03-VERY-ADJ-NOUN-GAP", "skill": "WRITING", "question_type": "gap_fill", "candidate_count": 64, "approved_count": 3},
    {"family_id": "U01-PF04-FIRST-MENTION-CONTEXT", "skill": "READING", "question_type": "context_match", "candidate_count": 80, "approved_count": 47},
    {"family_id": "U01-PF05-KNOWN-REFERENCE-CONTEXT", "skill": "READING", "question_type": "context_match", "candidate_count": 80, "approved_count": 47},
    {"family_id": "U01-PF06-ERROR-DISCRIMINATION", "skill": "READING", "question_type": "error_discrimination", "candidate_count": 176, "approved_count": 25},
    {"family_id": "U01-PF07-WORD-ORDER", "skill": "WRITING", "question_type": "word_order", "candidate_count": 176, "approved_count": 25},
    {"family_id": "U01-PF08-TRANSFER-FIRST-MENTION", "skill": "READING", "question_type": "contextual_choice", "candidate_count": 80, "approved_count": 47},
    {"family_id": "U01-PF09-TRANSFER-KNOWN-REFERENCE", "skill": "WRITING", "question_type": "contextual_gap", "candidate_count": 80, "approved_count": 47},
    {"family_id": "U01-PF10-SPEAK-NOUN", "skill": "SPEAKING", "question_type": "guided_sentence", "candidate_count": 16, "approved_count": 16},
    {"family_id": "U01-PF11-SPEAK-ADJ-NOUN", "skill": "SPEAKING", "question_type": "guided_sentence", "candidate_count": 6, "approved_count": 6},
    {"family_id": "U01-PF12-SPEAK-VERY-ADJ-NOUN", "skill": "SPEAKING", "question_type": "guided_sentence", "candidate_count": 3, "approved_count": 3},
)

CONTEXTS: tuple[dict[str, str], ...] = (
    {"context_id": "U01-C1-CLASSROOM-BAG", "label": "classroom", "location_phrase": "in the classroom"},
    {"context_id": "U01-C2-HOME-TOY-BOX", "label": "home", "location_phrase": "at home"},
    {"context_id": "U01-C3-PICNIC-FOOD", "label": "picnic", "location_phrase": "at the picnic"},
    {"context_id": "U01-C4-TOY-SHOP", "label": "shop", "location_phrase": "in the shop"},
    {"context_id": "U01-C5-PARK-BIRTHDAY", "label": "park", "location_phrase": "in the park"},
)

NOUN_CONTEXT_APPROVALS: dict[str, tuple[str, ...]] = {
    "apple": ("U01-C1-CLASSROOM-BAG", "U01-C3-PICNIC-FOOD", "U01-C4-TOY-SHOP", "U01-C5-PARK-BIRTHDAY"),
    "bag": tuple(row["context_id"] for row in CONTEXTS),
    "bed": ("U01-C2-HOME-TOY-BOX", "U01-C4-TOY-SHOP"),
    "book": tuple(row["context_id"] for row in CONTEXTS),
    "box": tuple(row["context_id"] for row in CONTEXTS),
    "cat": ("U01-C1-CLASSROOM-BAG", "U01-C2-HOME-TOY-BOX", "U01-C3-PICNIC-FOOD", "U01-C5-PARK-BIRTHDAY"),
    "classroom": ("U01-C1-CLASSROOM-BAG",),
    "desk": ("U01-C1-CLASSROOM-BAG", "U01-C2-HOME-TOY-BOX", "U01-C4-TOY-SHOP"),
    "dog": ("U01-C2-HOME-TOY-BOX", "U01-C3-PICNIC-FOOD", "U01-C5-PARK-BIRTHDAY"),
    "door": ("U01-C1-CLASSROOM-BAG", "U01-C2-HOME-TOY-BOX", "U01-C4-TOY-SHOP"),
    "egg": ("U01-C1-CLASSROOM-BAG", "U01-C3-PICNIC-FOOD", "U01-C4-TOY-SHOP", "U01-C5-PARK-BIRTHDAY"),
    "park": ("U01-C5-PARK-BIRTHDAY",),
    "room": ("U01-C2-HOME-TOY-BOX",),
    "shop": ("U01-C4-TOY-SHOP",),
    "tree": ("U01-C3-PICNIC-FOOD", "U01-C5-PARK-BIRTHDAY"),
    "window": ("U01-C1-CLASSROOM-BAG", "U01-C2-HOME-TOY-BOX", "U01-C4-TOY-SHOP"),
}

REJECTION_ADJECTIVE = "ADJECTIVE_NOUN_PAIR_NOT_IN_APPROVED_CONTRACT"
REJECTION_VERY = "VERY_ADJECTIVE_NOUN_PAIR_NOT_IN_APPROVED_CONTRACT"
REJECTION_CONTEXT = "CONTEXT_NOUN_PAIR_NOT_APPROVED"


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


def active_adjectives() -> list[dict[str, str]]:
    return [
        {"lemma": lemma, "evp_sense_id": sense}
        for lemma, sense, _guideword, _row, _gloss, _memory, _group
        in contract_builder.ACTIVE_ADJECTIVES
    ]


def direct_adjective_phrases() -> list[dict[str, str]]:
    noun_sense = {row["lemma"]: row["evp_sense_id"] for row in active_nouns()}
    adjective_sense = {row["lemma"]: row["evp_sense_id"] for row in active_adjectives()}
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
    adjective_sense = {row["lemma"]: row["evp_sense_id"] for row in active_adjectives()}
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


def expected_article(next_word: str) -> str:
    return "an" if next_word.lower()[:1] in {"a", "e", "i", "o", "u"} else "a"


def wrong_indefinite(article: str) -> str:
    return "an" if article == "a" else "a"


def context_by_id(context_id: str) -> Mapping[str, str]:
    return next(row for row in CONTEXTS if row["context_id"] == context_id)


def direct_phrase_map() -> dict[tuple[str, str], dict[str, str]]:
    return {(row["adjective"], row["noun"]): row for row in direct_adjective_phrases()}


def very_phrase_map() -> dict[tuple[str, str], dict[str, str]]:
    return {(row["adjective"], row["noun"]): row for row in very_adjective_phrases()}


def response_contract(
    *,
    scoring_mode: str,
    correct_answer: Any,
    accepted_answers: Sequence[str],
    speaking: bool,
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
    candidate_structure: str,
    context_id: str | None,
    lexical_slots: Mapping[str, str],
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
    transfer_eligible: bool,
    admission_status: str,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    family = family_contract(family_id)
    speaking = family["skill"] == "SPEAKING"
    item = {
        "item_id": f"U01QB01-{slug(family_id)}-{slug(token)}",
        "unit_id": UNIT_ID,
        "pattern_family_id": family_id,
        "candidate_structure": candidate_structure,
        "context_id": context_id,
        "lexical_slots": dict(lexical_slots),
        "unit_pattern_ids": [target_pattern_id],
        "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
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
        "learner_visible_capable": admission_status == "AUTO_APPROVED",
        "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
        "assessment_eligible": admission_status == "AUTO_APPROVED" and not speaking,
        "transfer_eligible": admission_status == "AUTO_APPROVED" and transfer_eligible,
        "reassessment_eligible": admission_status == "AUTO_APPROVED" and not speaking,
        "human_review_required": admission_status == "HUMAN_REVIEW",
        "audio_required": False,
        "speaking_capture_enabled": False,
        "runtime_generation_used": False,
        "admission_proposal": {
            "status": admission_status,
            "reason_codes": list(reason_codes),
        },
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
        "structure": candidate_structure,
        "context": context_id,
        "slots": dict(lexical_slots),
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


def noun_candidates() -> list[dict[str, Any]]:
    egp = [contract_builder.CORE_EGP_ROWS[0]]
    items: list[dict[str, Any]] = []
    for row in active_nouns():
        lemma = row["lemma"]
        sense = row["evp_sense_id"]
        article = article_from_phrase(row["indefinite_phrase"])
        items.append(
            make_item(
                family_id="U01-PF01-AAN-NOUN-GAP",
                token=lemma,
                candidate_structure="DET_N",
                context_id=None,
                lexical_slots={"noun": lemma},
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
                transfer_eligible=False,
                admission_status="AUTO_APPROVED",
                reason_codes=["ACTIVE_NOUN_AUTHORITY_BOUND"],
            )
        )
    return items


def adjective_candidates() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    direct = direct_phrase_map()
    for adjective in active_adjectives():
        for noun in active_nouns():
            key = (adjective["lemma"], noun["lemma"])
            approved = key in direct
            article = expected_article(adjective["lemma"])
            senses = [adjective["evp_sense_id"], noun["evp_sense_id"]]
            items.append(
                make_item(
                    family_id="U01-PF02-AAN-ADJ-NOUN-GAP",
                    token=f"{adjective['lemma']}-{noun['lemma']}",
                    candidate_structure="DET_ADJ_N",
                    context_id=None,
                    lexical_slots={"article": article, "adjective": adjective["lemma"], "noun": noun["lemma"]},
                    prompt=f"Complete with a or an: ___ {adjective['lemma']} {noun['lemma']}",
                    stimulus="",
                    options=[],
                    correct_answer=article,
                    accepted_answers=[article],
                    target_evp_sense_ids=senses,
                    target_egp_row_ids=[contract_builder.CORE_EGP_ROWS[1]],
                    target_pattern_id=PATTERN_ADJECTIVE,
                    scoring_mode="NORMALIZED_TEXT",
                    support_level="GUIDED",
                    transfer_eligible=False,
                    admission_status="AUTO_APPROVED" if approved else "AUTO_REJECTED",
                    reason_codes=["APPROVED_CONTRACT_ADJECTIVE_NOUN_PAIR"] if approved else [REJECTION_ADJECTIVE],
                )
            )
    return items


def very_candidates() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    approved_pairs = very_phrase_map()
    adjectives = [row for row in active_adjectives() if row["lemma"] in SAFE_INTENSIFIER_ADJECTIVES]
    for adjective in adjectives:
        for noun in active_nouns():
            key = (adjective["lemma"], noun["lemma"])
            approved = key in approved_pairs
            senses = [adjective["evp_sense_id"], noun["evp_sense_id"]]
            items.append(
                make_item(
                    family_id="U01-PF03-VERY-ADJ-NOUN-GAP",
                    token=f"{adjective['lemma']}-{noun['lemma']}",
                    candidate_structure="DET_VERY_ADJ_N",
                    context_id=None,
                    lexical_slots={"article": "a", "intensifier": "very", "adjective": adjective["lemma"], "noun": noun["lemma"]},
                    prompt=f"Complete with a: ___ very {adjective['lemma']} {noun['lemma']}",
                    stimulus="",
                    options=[],
                    correct_answer="a",
                    accepted_answers=["a"],
                    target_evp_sense_ids=senses,
                    target_egp_row_ids=[contract_builder.GUIDED_EGP_ROWS[0]],
                    target_pattern_id=PATTERN_VERY,
                    scoring_mode="NORMALIZED_TEXT",
                    support_level="GUIDED_EXTENSION",
                    transfer_eligible=False,
                    admission_status="AUTO_APPROVED" if approved else "AUTO_REJECTED",
                    reason_codes=["APPROVED_CONTRACT_VERY_ADJECTIVE_NOUN_PAIR"] if approved else [REJECTION_VERY],
                )
            )
    return items


def context_candidates(family_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for noun in active_nouns():
        lemma = noun["lemma"]
        article = article_from_phrase(noun["indefinite_phrase"])
        for context in CONTEXTS:
            context_id = context["context_id"]
            approved = context_id in NOUN_CONTEXT_APPROVALS[lemma]
            if family_id in {"U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"}:
                prompt = "Choose the article for the first mention."
                stimulus = f"There is ___ {lemma} {context['location_phrase']}."
                options = ["a", "an", "the"]
                answer = article
            else:
                prompt = "Complete the second mention of the same item."
                stimulus = f"There is {article} {lemma} {context['location_phrase']}. ___ {lemma} is easy to see."
                options = ["a", "an", "the"] if family_id == "U01-PF05-KNOWN-REFERENCE-CONTEXT" else []
                answer = "the"
            skill = family_contract(family_id)["skill"]
            items.append(
                make_item(
                    family_id=family_id,
                    token=f"{context_id}-{lemma}",
                    candidate_structure="DISCOURSE_ARTICLE_NOUN",
                    context_id=context_id,
                    lexical_slots={"noun": lemma, "context": context["label"]},
                    prompt=prompt,
                    stimulus=stimulus,
                    options=options,
                    correct_answer=answer,
                    accepted_answers=[answer],
                    target_evp_sense_ids=[noun["evp_sense_id"]],
                    target_egp_row_ids=[contract_builder.CORE_EGP_ROWS[0]],
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode="EXACT_OPTION" if skill == "READING" else "NORMALIZED_TEXT",
                    support_level="INDEPENDENT" if family_id.startswith("U01-PF08") or family_id.startswith("U01-PF09") else "REDUCED_SUPPORT",
                    transfer_eligible=family_id.startswith("U01-PF08") or family_id.startswith("U01-PF09"),
                    admission_status="AUTO_APPROVED" if approved else "AUTO_REJECTED",
                    reason_codes=["UNIT01_CONTEXT_NOUN_COMPATIBILITY_APPROVED"] if approved else [REJECTION_CONTEXT],
                )
            )
    return items


def error_and_order_candidates(family_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for noun in active_nouns():
        lemma = noun["lemma"]
        article = article_from_phrase(noun["indefinite_phrase"])
        wrong = wrong_indefinite(article)
        if family_id == "U01-PF06-ERROR-DISCRIMINATION":
            prompt, options, answer, mode = "Choose the correct noun phrase.", [f"{article} {lemma}", f"{wrong} {lemma}"], f"{article} {lemma}", "EXACT_OPTION"
        else:
            prompt, options, answer, mode = "Put the words in order.", [lemma, article], [article, lemma], "EXACT_SEQUENCE"
        items.append(
            make_item(
                family_id=family_id,
                token=f"noun-{lemma}",
                candidate_structure="DET_N",
                context_id=None,
                lexical_slots={"noun": lemma},
                prompt=prompt,
                stimulus="",
                options=options,
                correct_answer=answer,
                accepted_answers=[] if mode == "EXACT_SEQUENCE" else [str(answer)],
                target_evp_sense_ids=[noun["evp_sense_id"]],
                target_egp_row_ids=[contract_builder.CORE_EGP_ROWS[0]],
                target_pattern_id=PATTERN_NOUN,
                scoring_mode=mode,
                support_level="REDUCED_SUPPORT",
                transfer_eligible=False,
                admission_status="AUTO_APPROVED",
                reason_codes=["ACTIVE_NOUN_AUTHORITY_BOUND"],
            )
        )
    direct = direct_phrase_map()
    for adjective in active_adjectives():
        for noun in active_nouns():
            key = (adjective["lemma"], noun["lemma"])
            approved = key in direct
            article = expected_article(adjective["lemma"])
            wrong = wrong_indefinite(article)
            phrase = f"{article} {adjective['lemma']} {noun['lemma']}"
            if family_id == "U01-PF06-ERROR-DISCRIMINATION":
                prompt, options, answer, mode = "Choose the correct noun phrase.", [phrase, f"{wrong} {adjective['lemma']} {noun['lemma']}"], phrase, "EXACT_OPTION"
            else:
                prompt, options, answer, mode = "Put the words in order.", [noun["lemma"], article, adjective["lemma"]], [article, adjective["lemma"], noun["lemma"]], "EXACT_SEQUENCE"
            items.append(
                make_item(
                    family_id=family_id,
                    token=f"adj-{adjective['lemma']}-{noun['lemma']}",
                    candidate_structure="DET_ADJ_N",
                    context_id=None,
                    lexical_slots={"adjective": adjective["lemma"], "noun": noun["lemma"]},
                    prompt=prompt,
                    stimulus="",
                    options=options,
                    correct_answer=answer,
                    accepted_answers=[] if mode == "EXACT_SEQUENCE" else [str(answer)],
                    target_evp_sense_ids=[adjective["evp_sense_id"], noun["evp_sense_id"]],
                    target_egp_row_ids=[contract_builder.CORE_EGP_ROWS[1]],
                    target_pattern_id=PATTERN_ADJECTIVE,
                    scoring_mode=mode,
                    support_level="REDUCED_SUPPORT",
                    transfer_eligible=False,
                    admission_status="AUTO_APPROVED" if approved else "AUTO_REJECTED",
                    reason_codes=["APPROVED_CONTRACT_ADJECTIVE_NOUN_PAIR"] if approved else [REJECTION_ADJECTIVE],
                )
            )
    approved_very = very_phrase_map()
    adjectives = [row for row in active_adjectives() if row["lemma"] in SAFE_INTENSIFIER_ADJECTIVES]
    for adjective in adjectives:
        for noun in active_nouns():
            key = (adjective["lemma"], noun["lemma"])
            approved = key in approved_very
            phrase = f"a very {adjective['lemma']} {noun['lemma']}"
            if family_id == "U01-PF06-ERROR-DISCRIMINATION":
                prompt, options, answer, mode = "Choose the correct guided phrase.", [phrase, f"an very {adjective['lemma']} {noun['lemma']}"], phrase, "EXACT_OPTION"
            else:
                prompt, options, answer, mode = "Put the words in order.", [noun["lemma"], "very", "a", adjective["lemma"]], ["a", "very", adjective["lemma"], noun["lemma"]], "EXACT_SEQUENCE"
            items.append(
                make_item(
                    family_id=family_id,
                    token=f"very-{adjective['lemma']}-{noun['lemma']}",
                    candidate_structure="DET_VERY_ADJ_N",
                    context_id=None,
                    lexical_slots={"adjective": adjective["lemma"], "noun": noun["lemma"]},
                    prompt=prompt,
                    stimulus="",
                    options=options,
                    correct_answer=answer,
                    accepted_answers=[] if mode == "EXACT_SEQUENCE" else [str(answer)],
                    target_evp_sense_ids=[adjective["evp_sense_id"], noun["evp_sense_id"]],
                    target_egp_row_ids=[contract_builder.GUIDED_EGP_ROWS[0]],
                    target_pattern_id=PATTERN_VERY,
                    scoring_mode=mode,
                    support_level="GUIDED_EXTENSION",
                    transfer_eligible=False,
                    admission_status="AUTO_APPROVED" if approved else "AUTO_REJECTED",
                    reason_codes=["APPROVED_CONTRACT_VERY_ADJECTIVE_NOUN_PAIR"] if approved else [REJECTION_VERY],
                )
            )
    return items


def speaking_candidates() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for noun in active_nouns():
        phrase = noun["indefinite_phrase"]
        items.append(
            make_item(
                family_id="U01-PF10-SPEAK-NOUN",
                token=noun["lemma"],
                candidate_structure="DET_N",
                context_id=None,
                lexical_slots={"noun": noun["lemma"]},
                prompt=f"Say the phrase for one {noun['lemma']}.",
                stimulus=noun["lemma"],
                options=[],
                correct_answer=None,
                accepted_answers=[phrase],
                target_evp_sense_ids=[noun["evp_sense_id"]],
                target_egp_row_ids=[contract_builder.CORE_EGP_ROWS[0]],
                target_pattern_id=PATTERN_NOUN,
                scoring_mode="FEATURE_RUBRIC",
                support_level="GUIDED",
                transfer_eligible=False,
                admission_status="AUTO_APPROVED",
                reason_codes=["APPROVED_CONTRACT_NOUN_PHRASE"],
            )
        )
    for row in direct_adjective_phrases():
        items.append(
            make_item(
                family_id="U01-PF11-SPEAK-ADJ-NOUN",
                token=f"{row['adjective']}-{row['noun']}",
                candidate_structure="DET_ADJ_N",
                context_id=None,
                lexical_slots={"adjective": row["adjective"], "noun": row["noun"]},
                prompt=f"Say the phrase for one {row['adjective']} {row['noun']}.",
                stimulus=f"{row['adjective']} {row['noun']}",
                options=[],
                correct_answer=None,
                accepted_answers=[row["phrase"]],
                target_evp_sense_ids=[row["adjective_evp_sense_id"], row["noun_evp_sense_id"]],
                target_egp_row_ids=[contract_builder.CORE_EGP_ROWS[1]],
                target_pattern_id=PATTERN_ADJECTIVE,
                scoring_mode="FEATURE_RUBRIC",
                support_level="GUIDED",
                transfer_eligible=False,
                admission_status="AUTO_APPROVED",
                reason_codes=["APPROVED_CONTRACT_ADJECTIVE_NOUN_PAIR"],
            )
        )
    for row in very_adjective_phrases():
        items.append(
            make_item(
                family_id="U01-PF12-SPEAK-VERY-ADJ-NOUN",
                token=f"{row['adjective']}-{row['noun']}",
                candidate_structure="DET_VERY_ADJ_N",
                context_id=None,
                lexical_slots={"adjective": row["adjective"], "noun": row["noun"]},
                prompt=f"Say the guided phrase for one very {row['adjective']} {row['noun']}.",
                stimulus=f"very {row['adjective']} {row['noun']}",
                options=[],
                correct_answer=None,
                accepted_answers=[row["phrase"]],
                target_evp_sense_ids=[row["adjective_evp_sense_id"], row["noun_evp_sense_id"]],
                target_egp_row_ids=[contract_builder.GUIDED_EGP_ROWS[0]],
                target_pattern_id=PATTERN_VERY,
                scoring_mode="FEATURE_RUBRIC",
                support_level="GUIDED_EXTENSION",
                transfer_eligible=False,
                admission_status="AUTO_APPROVED",
                reason_codes=["APPROVED_CONTRACT_VERY_ADJECTIVE_NOUN_PAIR"],
            )
        )
    return items


def build_candidates() -> list[dict[str, Any]]:
    items = (
        noun_candidates()
        + adjective_candidates()
        + very_candidates()
        + context_candidates("U01-PF04-FIRST-MENTION-CONTEXT")
        + context_candidates("U01-PF05-KNOWN-REFERENCE-CONTEXT")
        + error_and_order_candidates("U01-PF06-ERROR-DISCRIMINATION")
        + error_and_order_candidates("U01-PF07-WORD-ORDER")
        + context_candidates("U01-PF08-TRANSFER-FIRST-MENTION")
        + context_candidates("U01-PF09-TRANSFER-KNOWN-REFERENCE")
        + speaking_candidates()
    )
    items.sort(key=lambda row: row["item_id"])
    if len(items) != EXPECTED_CANDIDATE_COUNT:
        raise VariantPoolBuildError(f"CANDIDATE_COUNT_INVALID:{len(items)}")
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
    context_count = len(CONTEXTS)
    safe_count = len(SAFE_INTENSIFIER_ADJECTIVES)
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
        + noun_count * safe_count
        + noun_count * context_count
        + noun_count * context_count
        + (noun_count + noun_count * adjective_count + noun_count * safe_count)
        + (noun_count + noun_count * adjective_count + noun_count * safe_count)
        + noun_count * context_count * 2
    )
    if raw != RAW_COMBINATORIAL_CAPACITY or strict != STRICT_PREVALIDATION_CAPACITY:
        raise VariantPoolBuildError(f"DESIGN_SPACE_CAPACITY_DRIFT:{raw}:{strict}")
    return {
        "active_noun_count": noun_count,
        "active_adjective_count": adjective_count,
        "context_count": context_count,
        "safe_intensifier_adjective_count": safe_count,
        "raw_combinatorial_capacity": raw,
        "strict_prevalidation_capacity": strict,
        "speaking_extension_candidate_count": SPEAKING_EXTENSION_CANDIDATE_COUNT,
        "materialized_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "validator_approved_count": EXPECTED_APPROVED_COUNT,
        "validator_rejected_count": EXPECTED_REJECTED_COUNT,
        "canonical_language_asset_combination_count": LANGUAGE_ASSET_COMBINATION_COUNT,
        "runtime_variant_count": 0,
    }


def distribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "family": dict(sorted(Counter(row["pattern_family_id"] for row in rows).items())),
        "skill": dict(sorted(Counter(row["skill"] for row in rows).items())),
        "question_type": dict(sorted(Counter(row["question_type"] for row in rows).items())),
        "unit_pattern": dict(sorted(Counter(pattern for row in rows for pattern in row["unit_pattern_ids"]).items())),
    }


def candidate_payload() -> dict[str, Any]:
    candidates = build_candidates()
    approved = [deepcopy(row) for row in candidates if row["admission_proposal"]["status"] == "AUTO_APPROVED"]
    rejected = [row for row in candidates if row["admission_proposal"]["status"] == "AUTO_REJECTED"]
    human = [row for row in candidates if row["admission_proposal"]["status"] == "HUMAN_REVIEW"]
    if len(approved) != EXPECTED_APPROVED_COUNT or len(rejected) != EXPECTED_REJECTED_COUNT or human:
        raise VariantPoolBuildError(f"ADMISSION_COUNT_INVALID:{len(approved)}:{len(rejected)}:{len(human)}")
    reason_counts = dict(sorted(Counter(reason for row in rejected for reason in row["admission_proposal"]["reason_codes"]).items()))
    evp_sense_ids = sorted({sense for row in approved for sense in row["target_evp_sense_ids"]})
    egp_row_ids = sorted({egp for row in approved for egp in row["target_egp_row_ids"]})
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
            "generation_mode": "FULL_OFFLINE_CANDIDATE_SPACE_WITH_INDEPENDENT_VALIDATOR_ADMISSION",
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
        "candidate_items": candidates,
        "approved_items": approved,
        "admission_readback": {
            "candidate_count": len(candidates),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "human_review_count": len(human),
            "rejection_reason_counts": reason_counts,
        },
        "distribution_counts": {
            "candidate": distribution(candidates),
            "approved": distribution(approved),
        },
        "count_semantics": {
            "language_asset_count_is_not_task_count": True,
            "canonical_task_count_is_not_runtime_variant_count": True,
            "canonical_language_asset_combination_count": LANGUAGE_ASSET_COMBINATION_COUNT,
            "canonical_approved_task_count": len(approved),
            "runtime_variant_count": 0,
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
            "pool_source": "VALIDATOR_APPROVED_ITEMS_ONLY",
            "selection_quota": {"new_or_unseen": 4, "remediation": 2, "scheduled_review": 2, "transfer": 1, "guided_extension": 1},
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
            "complete_strict_candidate_space_required": True,
            "rejected_candidates_retained_with_reason_codes": True,
            "approved_contract_phrases_only_for_adjective_combinations": True,
            "approved_context_noun_matrix_required": True,
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
            "runtime_variants_materialized": False,
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
    from ulga.validators import validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator
    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(candidate, validation_receipts=[receipt], decision_ref=DECISION_REF, producer_id=TASK_ID)


def materialize(*, candidate_path: Path, approved_path: Path, report_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator
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
        _, approved, report = materialize(candidate_path=args.candidate.resolve(), approved_path=args.approved.resolve(), report_path=args.report.resolve())
    except (VariantPoolBuildError, policy_artifact.ContentPolicyBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"CANDIDATE_COUNT={len(payload['candidate_items'])}")
    print(f"APPROVED_VARIANT_COUNT={len(payload['approved_items'])}")
    print(f"REJECTED_CANDIDATE_COUNT={payload['admission_readback']['rejected_count']}")
    print(f"PATTERN_FAMILY_COUNT={len(payload['pattern_family_contracts'])}")
    print(f"ACTIVE_EVP_SENSE_COUNT={payload['coverage_denominators']['active_evp_sense_count']}")
    print(f"EXERCISE_COVERED_EGP_ROW_COUNT={payload['coverage_denominators']['exercise_covered_egp_row_count']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
