#!/usr/bin/env python3
"""Build the full Unit01 candidate space and validator-admitted variant pool."""
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
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract
from ulga.builders import (
    build_a1fs_v1_u01data05b_unit01_article_noun_phrase_pattern_reconciliation as pattern_authority,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB01_Unit01PatternFamilyAndApprovedVariantPoolFullBuild"
SCHEMA_VERSION = "a1fs.v1.u01qb01.unit01_pattern_family_approved_variant_pool.v2"
PASS_STATUS = "PASS_A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL"
DECISION_REF = "OPERATOR_APPROVAL:2026-07-30:U01QB01"
UNIT_ID = contract.UNIT_ID
BANK_ID = "A1FS_V1_UNIT01_APPROVED_VARIANT_POOL"
BANK_VERSION = "2.0.0"
BASELINE_ACTIVITY_COUNT = 24
APPROVED_CONTRACT_SHA256 = "114376e997275a5ac387d69a16d9d3304096605392c6928e49863d4214efbc29"

RAW_COMBINATORIAL_CAPACITY = 944
STRICT_PREVALIDATION_CAPACITY = 848
EXPECTED_CANDIDATE_COUNT = 873
EXPECTED_APPROVED_COUNT = 288
EXPECTED_REJECTED_COUNT = 585
LANGUAGE_ASSET_COMBINATION_COUNT = 25

PATTERN_NOUN = "U01-NP-ARTICLE-NOUN"
PATTERN_ADJECTIVE = "U01-NP-ARTICLE-ADJECTIVE-NOUN"
PATTERN_VERY = "U01-NP-A-VERY-ADJECTIVE-NOUN"
FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS = ("SP_000016", "SP_000017")
SAFE_VERY_ADJECTIVES = ("big", "new", "old", "small")

DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb01_unit01_variant_pool.candidate.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb01_unit01_variant_pool.approved.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb01_unit01_variant_pool_validation.json")
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB02_"
    "Unit01ApprovedVariantSessionAssemblerAndExposureHistoryRuntimeIntegration"
)

FAMILIES: tuple[tuple[str, str, str, int, int], ...] = (
    ("U01-PF01-AAN-NOUN-GAP", "WRITING", "gap_fill", 16, 16),
    ("U01-PF02-AAN-ADJ-NOUN-GAP", "WRITING", "gap_fill", 96, 6),
    ("U01-PF03-VERY-ADJ-NOUN-GAP", "WRITING", "gap_fill", 64, 3),
    ("U01-PF04-FIRST-MENTION-CONTEXT", "READING", "context_match", 80, 47),
    ("U01-PF05-KNOWN-REFERENCE-CONTEXT", "READING", "context_match", 80, 47),
    ("U01-PF06-ERROR-DISCRIMINATION", "READING", "error_discrimination", 176, 25),
    ("U01-PF07-WORD-ORDER", "WRITING", "word_order", 176, 25),
    ("U01-PF08-TRANSFER-FIRST-MENTION", "READING", "contextual_choice", 80, 47),
    ("U01-PF09-TRANSFER-KNOWN-REFERENCE", "WRITING", "contextual_gap", 80, 47),
    ("U01-PF10-SPEAK-NOUN", "SPEAKING", "guided_sentence", 16, 16),
    ("U01-PF11-SPEAK-ADJ-NOUN", "SPEAKING", "guided_sentence", 6, 6),
    ("U01-PF12-SPEAK-VERY-ADJ-NOUN", "SPEAKING", "guided_sentence", 3, 3),
)

CONTEXTS: tuple[tuple[str, str], ...] = (
    ("U01-C1-CLASSROOM-BAG", "in the classroom"),
    ("U01-C2-HOME-TOY-BOX", "at home"),
    ("U01-C3-PICNIC-FOOD", "at the picnic"),
    ("U01-C4-TOY-SHOP", "in the shop"),
    ("U01-C5-PARK-BIRTHDAY", "in the park"),
)
CONTEXT_IDS = tuple(row[0] for row in CONTEXTS)
CONTEXT_LOCATION = dict(CONTEXTS)
CONTEXT_APPROVALS: dict[str, tuple[str, ...]] = {
    "apple": (CONTEXT_IDS[0], CONTEXT_IDS[2], CONTEXT_IDS[3], CONTEXT_IDS[4]),
    "bag": CONTEXT_IDS,
    "bed": (CONTEXT_IDS[1], CONTEXT_IDS[3]),
    "book": CONTEXT_IDS,
    "box": CONTEXT_IDS,
    "cat": (CONTEXT_IDS[0], CONTEXT_IDS[1], CONTEXT_IDS[2], CONTEXT_IDS[4]),
    "classroom": (CONTEXT_IDS[0],),
    "desk": (CONTEXT_IDS[0], CONTEXT_IDS[1], CONTEXT_IDS[3]),
    "dog": (CONTEXT_IDS[1], CONTEXT_IDS[2], CONTEXT_IDS[4]),
    "door": (CONTEXT_IDS[0], CONTEXT_IDS[1], CONTEXT_IDS[3]),
    "egg": (CONTEXT_IDS[0], CONTEXT_IDS[2], CONTEXT_IDS[3], CONTEXT_IDS[4]),
    "park": (CONTEXT_IDS[4],),
    "room": (CONTEXT_IDS[1],),
    "shop": (CONTEXT_IDS[3],),
    "tree": (CONTEXT_IDS[2], CONTEXT_IDS[4]),
    "window": (CONTEXT_IDS[0], CONTEXT_IDS[1], CONTEXT_IDS[3]),
}

REJECT_ADJ = "ADJECTIVE_NOUN_PAIR_NOT_IN_APPROVED_CONTRACT"
REJECT_VERY = "VERY_ADJECTIVE_NOUN_PAIR_NOT_IN_APPROVED_CONTRACT"
REJECT_CONTEXT = "CONTEXT_NOUN_PAIR_NOT_APPROVED"


class VariantPoolBuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def nouns() -> list[dict[str, str]]:
    return [
        {"lemma": lemma, "sense": sense, "indefinite": indefinite, "definite": definite}
        for lemma, sense, _gloss, indefinite, definite, _group in contract.ACTIVE_NOUNS
    ]


def adjectives() -> list[dict[str, str]]:
    return [
        {"lemma": lemma, "sense": sense}
        for lemma, sense, _guide, _row, _gloss, _memory, _group in contract.ACTIVE_ADJECTIVES
    ]


def article(word: str) -> str:
    return "an" if word.lower()[:1] in {"a", "e", "i", "o", "u"} else "a"


def wrong_article(value: str) -> str:
    return "an" if value == "a" else "a"


def direct_pairs() -> dict[tuple[str, str], str]:
    return {
        (adjective, noun): phrase
        for phrase, adjective, noun, _article, role in contract.ADJECTIVE_INSTRUCTIONAL_PHRASES
        if role == "DIRECT_ADJECTIVE_NOUN"
    }


def very_pairs() -> dict[tuple[str, str], str]:
    return {
        (adjective, noun): phrase
        for phrase, adjective, noun, _article, role in contract.ADJECTIVE_INSTRUCTIONAL_PHRASES
        if role == "GUIDED_VERY_ADJECTIVE_NOUN"
    }


def family_rows() -> list[dict[str, Any]]:
    return [
        {
            "family_id": family_id,
            "skill": skill,
            "question_type": question_type,
            "candidate_count": candidate_count,
            "approved_count": approved_count,
            "rejected_count": candidate_count - approved_count,
        }
        for family_id, skill, question_type, candidate_count, approved_count in FAMILIES
    ]


def family(family_id: str) -> Mapping[str, Any]:
    return next(row for row in family_rows() if row["family_id"] == family_id)


def response_contract(
    *, skill: str, scoring_mode: str, correct_answer: Any, accepted_answers: Sequence[str]
) -> dict[str, Any]:
    if skill == "SPEAKING":
        return {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "accepted_texts": list(accepted_answers),
            "accepted_sequence": [],
            "capture_enabled": False,
            "human_review_fallback": True,
            "rubric": {"practice_only": True, "article_noun_phrase_target": True},
        }
    if scoring_mode == "EXACT_SEQUENCE":
        return {
            "scoring_mode": scoring_mode,
            "response_type": "sequence",
            "accepted_texts": [],
            "accepted_sequence": list(correct_answer),
            "capture_enabled": True,
            "human_review_fallback": False,
        }
    return {
        "scoring_mode": scoring_mode,
        "response_type": "string",
        "accepted_texts": list(dict.fromkeys(str(row) for row in accepted_answers)),
        "accepted_sequence": [],
        "capture_enabled": True,
        "human_review_fallback": False,
    }


def make_item(
    *,
    family_id: str,
    token: str,
    structure: str,
    noun: Mapping[str, str],
    adjective_row: Mapping[str, str] | None = None,
    context_id: str | None = None,
    prompt: str,
    stimulus: str,
    options: Sequence[str],
    correct_answer: Any,
    accepted_answers: Sequence[str],
    scoring_mode: str,
    support_level: str,
    approved: bool,
    reason: str,
) -> dict[str, Any]:
    family_row = family(family_id)
    if structure == "NOUN":
        pattern_id, egp_ids = PATTERN_NOUN, [contract.CORE_EGP_ROWS[0]]
    elif structure == "ADJECTIVE":
        pattern_id, egp_ids = PATTERN_ADJECTIVE, [contract.CORE_EGP_ROWS[1]]
    else:
        pattern_id, egp_ids = PATTERN_VERY, [contract.GUIDED_EGP_ROWS[0]]
    senses = [noun["sense"]]
    lexical_slots = {"noun": noun["lemma"]}
    if adjective_row:
        senses.append(adjective_row["sense"])
        lexical_slots["adjective"] = adjective_row["lemma"]
    if context_id:
        lexical_slots["context_id"] = context_id
    status = "AUTO_APPROVED" if approved else "AUTO_REJECTED"
    item = {
        "item_id": f"U01QB01-{slug(family_id)}-{slug(token)}",
        "unit_id": UNIT_ID,
        "pattern_family_id": family_id,
        "candidate_structure": structure,
        "context_id": context_id,
        "lexical_slots": lexical_slots,
        "unit_pattern_ids": [pattern_id],
        "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
        "target_egp_row_ids": egp_ids,
        "target_evp_sense_ids": sorted(senses),
        "skill": family_row["skill"],
        "question_type": family_row["question_type"],
        "prompt": prompt,
        "stimulus": stimulus,
        "options": list(options),
        "correct_answer": deepcopy(correct_answer),
        "accepted_answers": list(accepted_answers),
        "scoring_mode": scoring_mode,
        "support_level": support_level,
        "learner_visible_capable": approved,
        "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
        "assessment_eligible": approved and family_row["skill"] != "SPEAKING",
        "transfer_eligible": approved and family_id in {
            "U01-PF08-TRANSFER-FIRST-MENTION",
            "U01-PF09-TRANSFER-KNOWN-REFERENCE",
        },
        "reassessment_eligible": approved and family_row["skill"] != "SPEAKING",
        "human_review_required": False,
        "audio_required": False,
        "speaking_capture_enabled": False,
        "runtime_generation_used": False,
        "admission_proposal": {"status": status, "reason_codes": [reason]},
        "source_refs": [
            {
                "source_type": "UNIT01_APPROVED_CONTENT_CONTRACT",
                "task_id": contract.TASK_ID,
                "contract_sha256": APPROVED_CONTRACT_SHA256,
            },
            {
                "source_type": "UNIT01_LOCAL_PATTERN_AUTHORITY",
                "task_id": pattern_authority.TASK_ID,
                "pattern_id": pattern_id,
            },
        ],
    }
    item["response_contract"] = response_contract(
        skill=family_row["skill"],
        scoring_mode=scoring_mode,
        correct_answer=correct_answer,
        accepted_answers=accepted_answers,
    )
    item["semantic_signature"] = digest(
        {
            "family": family_id,
            "structure": structure,
            "context": context_id,
            "slots": lexical_slots,
            "prompt": prompt,
            "stimulus": stimulus,
            "options": list(options),
            "answer": correct_answer,
        }
    )
    return item


def generate_candidates() -> list[dict[str, Any]]:
    noun_rows, adjective_rows = nouns(), adjectives()
    direct, very = direct_pairs(), very_pairs()
    items: list[dict[str, Any]] = []

    for noun in noun_rows:
        art = article(noun["lemma"])
        items.append(make_item(
            family_id="U01-PF01-AAN-NOUN-GAP", token=noun["lemma"], structure="NOUN",
            noun=noun, prompt=f"Complete with a or an: ___ {noun['lemma']}", stimulus="",
            options=[], correct_answer=art, accepted_answers=[art], scoring_mode="NORMALIZED_TEXT",
            support_level="GUIDED", approved=True, reason="ACTIVE_NOUN_AUTHORITY_BOUND",
        ))

    for adjective_row in adjective_rows:
        for noun in noun_rows:
            key = (adjective_row["lemma"], noun["lemma"])
            approved = key in direct
            art = article(adjective_row["lemma"])
            items.append(make_item(
                family_id="U01-PF02-AAN-ADJ-NOUN-GAP", token="-".join(key), structure="ADJECTIVE",
                noun=noun, adjective_row=adjective_row,
                prompt=f"Complete with a or an: ___ {adjective_row['lemma']} {noun['lemma']}",
                stimulus="", options=[], correct_answer=art, accepted_answers=[art],
                scoring_mode="NORMALIZED_TEXT", support_level="GUIDED", approved=approved,
                reason="APPROVED_CONTRACT_ADJECTIVE_NOUN_PAIR" if approved else REJECT_ADJ,
            ))

    for adjective_row in [row for row in adjective_rows if row["lemma"] in SAFE_VERY_ADJECTIVES]:
        for noun in noun_rows:
            key = (adjective_row["lemma"], noun["lemma"])
            approved = key in very
            items.append(make_item(
                family_id="U01-PF03-VERY-ADJ-NOUN-GAP", token="-".join(key), structure="VERY",
                noun=noun, adjective_row=adjective_row,
                prompt=f"Complete with a: ___ very {adjective_row['lemma']} {noun['lemma']}",
                stimulus="", options=[], correct_answer="a", accepted_answers=["a"],
                scoring_mode="NORMALIZED_TEXT", support_level="GUIDED_EXTENSION", approved=approved,
                reason="APPROVED_CONTRACT_VERY_ADJECTIVE_NOUN_PAIR" if approved else REJECT_VERY,
            ))

    for family_id in (
        "U01-PF04-FIRST-MENTION-CONTEXT",
        "U01-PF05-KNOWN-REFERENCE-CONTEXT",
        "U01-PF08-TRANSFER-FIRST-MENTION",
        "U01-PF09-TRANSFER-KNOWN-REFERENCE",
    ):
        first = family_id in {"U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"}
        for noun in noun_rows:
            art = article(noun["lemma"])
            for context_id in CONTEXT_IDS:
                approved = context_id in CONTEXT_APPROVALS[noun["lemma"]]
                location = CONTEXT_LOCATION[context_id]
                if first:
                    prompt = "Choose the article for the first mention."
                    stimulus = f"There is ___ {noun['lemma']} {location}."
                    answer = art
                    options = ["a", "an", "the"]
                else:
                    prompt = "Complete the second mention of the same item."
                    stimulus = (
                        f"There is {art} {noun['lemma']} {location}. "
                        f"___ {noun['lemma']} is easy to see."
                    )
                    answer = "the"
                    options = ["a", "an", "the"] if family_id.startswith("U01-PF05") else []
                mode = "EXACT_OPTION" if family(family_id)["skill"] == "READING" else "NORMALIZED_TEXT"
                items.append(make_item(
                    family_id=family_id, token=f"{context_id}-{noun['lemma']}", structure="NOUN",
                    noun=noun, context_id=context_id, prompt=prompt, stimulus=stimulus,
                    options=options, correct_answer=answer, accepted_answers=[answer],
                    scoring_mode=mode, support_level="INDEPENDENT" if family_id.startswith(("U01-PF08", "U01-PF09")) else "REDUCED_SUPPORT",
                    approved=approved,
                    reason="UNIT01_CONTEXT_NOUN_COMPATIBILITY_APPROVED" if approved else REJECT_CONTEXT,
                ))

    structures: list[tuple[str, Mapping[str, str], Mapping[str, str] | None, bool, str]] = []
    structures += [("NOUN", noun, None, True, "ACTIVE_NOUN_AUTHORITY_BOUND") for noun in noun_rows]
    structures += [
        ("ADJECTIVE", noun, adjective_row, (adjective_row["lemma"], noun["lemma"]) in direct,
         "APPROVED_CONTRACT_ADJECTIVE_NOUN_PAIR" if (adjective_row["lemma"], noun["lemma"]) in direct else REJECT_ADJ)
        for adjective_row in adjective_rows for noun in noun_rows
    ]
    structures += [
        ("VERY", noun, adjective_row, (adjective_row["lemma"], noun["lemma"]) in very,
         "APPROVED_CONTRACT_VERY_ADJECTIVE_NOUN_PAIR" if (adjective_row["lemma"], noun["lemma"]) in very else REJECT_VERY)
        for adjective_row in adjective_rows if adjective_row["lemma"] in SAFE_VERY_ADJECTIVES
        for noun in noun_rows
    ]
    for family_id in ("U01-PF06-ERROR-DISCRIMINATION", "U01-PF07-WORD-ORDER"):
        for structure, noun, adjective_row, approved, reason in structures:
            if structure == "NOUN":
                sequence = [article(noun["lemma"]), noun["lemma"]]
            elif structure == "ADJECTIVE":
                sequence = [article(adjective_row["lemma"]), adjective_row["lemma"], noun["lemma"]]
            else:
                sequence = ["a", "very", adjective_row["lemma"], noun["lemma"]]
            token = f"{structure}-{adjective_row['lemma'] + '-' if adjective_row else ''}{noun['lemma']}"
            if family_id.startswith("U01-PF06"):
                correct = " ".join(sequence)
                options = [correct, " ".join([wrong_article(sequence[0]), *sequence[1:]])]
                mode, accepted = "EXACT_OPTION", [correct]
                prompt = "Choose the correct noun phrase."
            else:
                correct = sequence
                options = list(reversed(sequence))
                mode, accepted = "EXACT_SEQUENCE", []
                prompt = "Put the words in order."
            items.append(make_item(
                family_id=family_id, token=token, structure=structure, noun=noun,
                adjective_row=adjective_row, prompt=prompt, stimulus="", options=options,
                correct_answer=correct, accepted_answers=accepted, scoring_mode=mode,
                support_level="REDUCED_SUPPORT", approved=approved, reason=reason,
            ))

    for noun in noun_rows:
        items.append(make_item(
            family_id="U01-PF10-SPEAK-NOUN", token=noun["lemma"], structure="NOUN", noun=noun,
            prompt=f"Say the phrase for one {noun['lemma']}.", stimulus=noun["lemma"], options=[],
            correct_answer=None, accepted_answers=[noun["indefinite"]], scoring_mode="FEATURE_RUBRIC",
            support_level="GUIDED", approved=True, reason="APPROVED_CONTRACT_NOUN_PHRASE",
        ))
    noun_by_lemma = {row["lemma"]: row for row in noun_rows}
    adjective_by_lemma = {row["lemma"]: row for row in adjective_rows}
    for (adj, noun_lemma), phrase in direct.items():
        items.append(make_item(
            family_id="U01-PF11-SPEAK-ADJ-NOUN", token=f"{adj}-{noun_lemma}",
            structure="ADJECTIVE", noun=noun_by_lemma[noun_lemma], adjective_row=adjective_by_lemma[adj],
            prompt=f"Say the phrase for one {adj} {noun_lemma}.", stimulus=f"{adj} {noun_lemma}",
            options=[], correct_answer=None, accepted_answers=[phrase], scoring_mode="FEATURE_RUBRIC",
            support_level="GUIDED", approved=True, reason="APPROVED_CONTRACT_ADJECTIVE_NOUN_PAIR",
        ))
    for (adj, noun_lemma), phrase in very.items():
        items.append(make_item(
            family_id="U01-PF12-SPEAK-VERY-ADJ-NOUN", token=f"{adj}-{noun_lemma}",
            structure="VERY", noun=noun_by_lemma[noun_lemma], adjective_row=adjective_by_lemma[adj],
            prompt=f"Say the guided phrase for one very {adj} {noun_lemma}.",
            stimulus=f"very {adj} {noun_lemma}", options=[], correct_answer=None,
            accepted_answers=[phrase], scoring_mode="FEATURE_RUBRIC",
            support_level="GUIDED_EXTENSION", approved=True,
            reason="APPROVED_CONTRACT_VERY_ADJECTIVE_NOUN_PAIR",
        ))

    items.sort(key=lambda row: row["item_id"])
    if len(items) != EXPECTED_CANDIDATE_COUNT:
        raise VariantPoolBuildError(f"CANDIDATE_COUNT_INVALID:{len(items)}")
    if len({row["item_id"] for row in items}) != len(items):
        raise VariantPoolBuildError("DUPLICATE_ITEM_ID")
    if len({row["semantic_signature"] for row in items}) != len(items):
        raise VariantPoolBuildError("DUPLICATE_SEMANTIC_SIGNATURE")
    return items


def design_space_capacity() -> dict[str, int]:
    return {
        "active_noun_count": 16,
        "active_adjective_count": 6,
        "context_count": 5,
        "safe_intensifier_adjective_count": 4,
        "raw_combinatorial_capacity": RAW_COMBINATORIAL_CAPACITY,
        "strict_prevalidation_capacity": STRICT_PREVALIDATION_CAPACITY,
        "speaking_extension_candidate_count": 25,
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
        "unit_pattern": dict(sorted(Counter(p for row in rows for p in row["unit_pattern_ids"]).items())),
    }


def candidate_payload() -> dict[str, Any]:
    candidates = generate_candidates()
    approved = [deepcopy(row) for row in candidates if row["admission_proposal"]["status"] == "AUTO_APPROVED"]
    rejected = [row for row in candidates if row["admission_proposal"]["status"] == "AUTO_REJECTED"]
    if len(approved) != EXPECTED_APPROVED_COUNT or len(rejected) != EXPECTED_REJECTED_COUNT:
        raise VariantPoolBuildError(f"ADMISSION_COUNT_INVALID:{len(approved)}:{len(rejected)}")
    reasons = dict(sorted(Counter(code for row in rejected for code in row["admission_proposal"]["reason_codes"]).items()))
    evp = sorted({sense for row in approved for sense in row["target_evp_sense_ids"]})
    egp = sorted({row_id for row in approved for row_id in row["target_egp_row_ids"]})
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
            "generation_mode": "FULL_STRICT_CANDIDATE_GENERATION_THEN_VALIDATOR_ADMISSION",
            "learner_runtime_free_generation_allowed": False,
        },
        "design_space_capacity": design_space_capacity(),
        "baseline_bank_contract": {
            "baseline_activity_count": BASELINE_ACTIVITY_COUNT,
            "baseline_role": "REGRESSION_AND_INTEGRATION_ACCEPTANCE_ONLY",
            "baseline_items_copied_into_variant_pool": False,
            "routine_session_delivery_uses_baseline_by_default": False,
        },
        "pattern_family_contracts": family_rows(),
        "candidate_items": candidates,
        "approved_items": approved,
        "admission_readback": {
            "candidate_count": len(candidates),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "human_review_count": 0,
            "rejection_reason_counts": reasons,
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
            "active_evp_sense_count": len(evp),
            "active_evp_sense_ids": evp,
            "exercise_covered_egp_row_count": len(egp),
            "exercise_covered_egp_row_ids": egp,
            "a1_egp_denominator": 109,
            "learner_mastery_claimed": False,
            "ket_canonical_prerequisite_node_claimed": False,
            "semantic_ket_prerequisite_capability": "ARTICLE_NOUN_PHRASE_CONTROL",
        },
        "session_assembly_metadata": {
            "runtime_status": "NOT_CONNECTED_METADATA_ONLY",
            "session_size": 10,
            "pool_source": "VALIDATOR_APPROVED_ITEMS_ONLY",
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
    return policy_artifact.build_candidate(
        payload=candidate_payload(),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "unit01_contract_task_id": contract.TASK_ID,
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
    *, candidate_path: Path, approved_path: Path, report_path: Path
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
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
