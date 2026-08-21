#!/usr/bin/env python3
"""Build the Unit02 plain-s governed QuestionBank candidate pool.

U02QB02 consumes the source-reconciled U02QB01 162-noun plain-s inventory,
reuses the approved Unit01 adjective+noun pairs only where their noun remains
inside that inventory, and materializes deterministic A1 task families for
KP011-KP014. It does not connect items to learner runtime or mutate Unit01.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as u01_contract

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02QB02_Unit02PlainSQuestionBankCandidatePoolAndAdmission"
SCHEMA_VERSION = "a1fs.v1.u02qb02.unit02_plain_s_questionbank_candidate_pool.v1"
PASS_STATUS = "PASS_A1FS_V1_U02QB02_UNIT02_PLAIN_S_QUESTIONBANK_CANDIDATE_POOL"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-22:U02QB02"
UNIT_ID = "GRAMMAR_REGULAR_PLURAL_NOUNS"
BANK_ID = "A1FS_V1_UNIT02_PLAIN_S_APPROVED_VARIANT_POOL"
BANK_VERSION = "1.0.0"
DIRECT_PATTERN_ID = "SP_000002"
DETERMINER = "two"

KP011 = "1741163711539x318006443369482940"
KP012 = "1741163711539x336320676887564860"
KP013 = "1741163711539x384428957229715900"
KP014 = "1741163711821x759916598484829700"
TARGET_EGP_ROWS = (KP011, KP012, KP013, KP014)
PREREQUISITE_KP009 = "1741163709012x117638123076284200"

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO_ROOT / "ulga/reports/a1fs_v1_u02qb01_exact_plain_s_active_vocabulary_inventory.json"

EXPECTED_NOUN_SURFACES = 162
EXPECTED_EXACT_NOUN_REFS = 171
EXPECTED_CANDIDATES = 660
EXPECTED_APPROVED = 658
EXPECTED_REJECTED = 2
UNIT01_RUNTIME_BASE_COUNT = 474
NEXT_SHORT_STEP = (
    "A1FS-V1-U02QB03_"
    "Unit02CumulativeQuestionBankRuntimeIntegration"
)

REJECT_OUTSIDE_PLAIN_S = "NOUN_OUTSIDE_U02QB01_PLAIN_S_INVENTORY"

FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "family_id": "U02-PF01-PLURAL-FORM-PRODUCTION",
        "skill": "WRITING",
        "question_type": "gap_fill",
        "egp_row_id": KP014,
        "candidate_count": 162,
        "approved_count": 162,
    },
    {
        "family_id": "U02-PF02-PLURAL-FORM-CHOICE",
        "skill": "READING",
        "question_type": "multiple_choice",
        "egp_row_id": KP014,
        "candidate_count": 162,
        "approved_count": 162,
    },
    {
        "family_id": "U02-PF03-ADJECTIVE-PLURAL-NOUN",
        "skill": "WRITING",
        "question_type": "word_order",
        "egp_row_id": KP011,
        "candidate_count": 6,
        "approved_count": 5,
    },
    {
        "family_id": "U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN",
        "skill": "WRITING",
        "question_type": "word_order",
        "egp_row_id": KP012,
        "candidate_count": 6,
        "approved_count": 5,
    },
    {
        "family_id": "U02-PF05-NUMBER-PLURAL-NOUN",
        "skill": "WRITING",
        "question_type": "word_order",
        "egp_row_id": KP013,
        "candidate_count": 162,
        "approved_count": 162,
    },
    {
        "family_id": "U02-PF06-SPEAK-PLURAL-FORM",
        "skill": "SPEAKING",
        "question_type": "guided_sentence",
        "egp_row_id": KP014,
        "candidate_count": 162,
        "approved_count": 162,
    },
)


class Unit02QuestionBankBuildError(ValueError):
    """Fail-closed U02QB02 construction error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")


def load_inventory(path: Path = INVENTORY_PATH) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("task_id") != "A1FS-V1-U02QB01_ExactPlainSActiveVocabularyInventory":
        raise Unit02QuestionBankBuildError("U02QB01_TASK_ID_INVALID")
    if value.get("unit_id") != UNIT_ID:
        raise Unit02QuestionBankBuildError("U02QB01_UNIT_ID_INVALID")
    counts = value.get("counts", {})
    if counts.get("plain_s_denominator") != EXPECTED_NOUN_SURFACES:
        raise Unit02QuestionBankBuildError("U02QB01_DENOMINATOR_INVALID")
    if counts.get("plain_s_exact_active_vocabulary_refs") != EXPECTED_EXACT_NOUN_REFS:
        raise Unit02QuestionBankBuildError("U02QB01_EXACT_REF_COUNT_INVALID")
    rows = value.get("inventory")
    if not isinstance(rows, list) or len(rows) != EXPECTED_NOUN_SURFACES:
        raise Unit02QuestionBankBuildError("U02QB01_INVENTORY_COUNT_INVALID")
    singulars = [str(row["singular"]) for row in rows]
    if len(singulars) != len(set(singulars)):
        raise Unit02QuestionBankBuildError("U02QB01_DUPLICATE_SINGULAR")
    refs = [ref for row in rows for ref in row["vocabulary_ids"]]
    if len(refs) != EXPECTED_EXACT_NOUN_REFS or len(refs) != len(set(refs)):
        raise Unit02QuestionBankBuildError("U02QB01_VOCAB_REF_IDENTITY_INVALID")
    for row in rows:
        if str(row["plural"]) != str(row["singular"]) + "s":
            raise Unit02QuestionBankBuildError(f"U02QB01_NON_PLAIN_S:{row['singular']}")
    return value


def inventory_by_singular() -> dict[str, dict[str, Any]]:
    return {
        str(row["singular"]): dict(row)
        for row in load_inventory()["inventory"]
    }


def active_adjective_id(adjective: str) -> str:
    for lemma, sense, _guide, _row, _gloss, _memory, _group in u01_contract.ACTIVE_ADJECTIVES:
        if lemma == adjective:
            return str(sense).split(":")[-1]
    raise Unit02QuestionBankBuildError(f"ADJECTIVE_AUTHORITY_MISSING:{adjective}")


def direct_adjective_pairs() -> list[dict[str, str]]:
    rows = []
    for phrase, adjective, noun, _article, role in u01_contract.ADJECTIVE_INSTRUCTIONAL_PHRASES:
        if role != "DIRECT_ADJECTIVE_NOUN":
            continue
        rows.append(
            {
                "source_phrase": phrase,
                "adjective": adjective,
                "adjective_vocab_id": active_adjective_id(adjective),
                "noun": noun,
            }
        )
    if len(rows) != 6:
        raise Unit02QuestionBankBuildError(f"U01_DIRECT_PAIR_COUNT_INVALID:{len(rows)}")
    return rows


def family(family_id: str) -> Mapping[str, Any]:
    for row in FAMILIES:
        if row["family_id"] == family_id:
            return row
    raise Unit02QuestionBankBuildError(f"UNKNOWN_FAMILY:{family_id}")


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
            "rubric": {"practice_only": True, "plain_s_plural_target": True},
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
        "accepted_texts": list(dict.fromkeys(str(value) for value in accepted_answers)),
        "accepted_sequence": [],
        "capture_enabled": True,
        "human_review_fallback": False,
    }


def make_item(
    *,
    family_id: str,
    token: str,
    singular: str,
    plural: str,
    noun_vocab_ids: Sequence[str],
    prompt: str,
    stimulus: str,
    options: Sequence[str],
    correct_answer: Any,
    accepted_answers: Sequence[str],
    scoring_mode: str,
    support_level: str,
    approved: bool,
    reason: str,
    adjective: str | None = None,
    adjective_vocab_id: str | None = None,
) -> dict[str, Any]:
    fam = family(family_id)
    skill = str(fam["skill"])
    target_refs = list(noun_vocab_ids)
    lexical_slots: dict[str, Any] = {
        "singular_noun": singular,
        "plural_noun": plural,
    }
    if adjective:
        lexical_slots["adjective"] = adjective
        target_refs.append(str(adjective_vocab_id))
    if family_id in {
        "U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN",
        "U02-PF05-NUMBER-PLURAL-NOUN",
    }:
        lexical_slots["determiner"] = DETERMINER
    item = {
        "item_id": f"U02QB02-{slug(family_id)}-{slug(token)}",
        "unit_id": UNIT_ID,
        "pattern_family_id": family_id,
        "lexical_slots": lexical_slots,
        "unit_pattern_ids": [DIRECT_PATTERN_ID],
        "grammar_target_ids": ["REGULAR_PLURAL_NOUNS"],
        "target_egp_row_ids": [fam["egp_row_id"]],
        "prerequisite_egp_row_ids": (
            [PREREQUISITE_KP009]
            if "determiner" in lexical_slots
            else []
        ),
        "target_evp_sense_ids": sorted(set(target_refs)),
        "skill": skill,
        "question_type": fam["question_type"],
        "prompt": prompt,
        "stimulus": stimulus,
        "options": list(options),
        "correct_answer": deepcopy(correct_answer),
        "accepted_answers": list(accepted_answers),
        "scoring_mode": scoring_mode,
        "support_level": support_level,
        "learner_visible_capable": approved,
        "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
        "assessment_eligible": approved and skill != "SPEAKING",
        "transfer_eligible": False,
        "reassessment_eligible": approved and skill != "SPEAKING",
        "human_review_required": False,
        "audio_required": False,
        "speaking_capture_enabled": False,
        "runtime_generation_used": False,
        "admission_proposal": {
            "status": "AUTO_APPROVED" if approved else "AUTO_REJECTED",
            "reason_codes": [reason],
        },
        "source_refs": [
            {
                "source_type": "U02QB01_PLAIN_S_ACTIVE_VOCABULARY_INVENTORY",
                "path": str(INVENTORY_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                "task_id": "A1FS-V1-U02QB01_ExactPlainSActiveVocabularyInventory",
            },
            {
                "source_type": "UNIT01_APPROVED_ADJECTIVE_NOUN_CONTRACT_REUSE",
                "task_id": u01_contract.TASK_ID,
                "used": bool(adjective),
            },
        ],
    }
    item["response_contract"] = response_contract(
        skill=skill,
        scoring_mode=scoring_mode,
        correct_answer=correct_answer,
        accepted_answers=accepted_answers,
    )
    item["semantic_signature"] = digest(
        {
            "family_id": family_id,
            "lexical_slots": lexical_slots,
            "prompt": prompt,
            "stimulus": stimulus,
            "options": list(options),
            "correct_answer": correct_answer,
        }
    )
    return item


def generate_candidates() -> list[dict[str, Any]]:
    inventory = inventory_by_singular()
    items: list[dict[str, Any]] = []

    for singular, noun in sorted(inventory.items()):
        plural = str(noun["plural"])
        refs = list(noun["vocabulary_ids"])
        items.append(
            make_item(
                family_id="U02-PF01-PLURAL-FORM-PRODUCTION",
                token=singular,
                singular=singular,
                plural=plural,
                noun_vocab_ids=refs,
                prompt=f"Write the plural form of: {singular}",
                stimulus=singular,
                options=[],
                correct_answer=plural,
                accepted_answers=[plural],
                scoring_mode="NORMALIZED_TEXT",
                support_level="GUIDED",
                approved=True,
                reason="U02QB01_PLAIN_S_NOUN_AUTHORITY_BOUND",
            )
        )
        items.append(
            make_item(
                family_id="U02-PF02-PLURAL-FORM-CHOICE",
                token=singular,
                singular=singular,
                plural=plural,
                noun_vocab_ids=refs,
                prompt="Choose the plural form.",
                stimulus=singular,
                options=[plural, singular],
                correct_answer=plural,
                accepted_answers=[plural],
                scoring_mode="EXACT_OPTION",
                support_level="GUIDED",
                approved=True,
                reason="U02QB01_PLAIN_S_NOUN_AUTHORITY_BOUND",
            )
        )
        items.append(
            make_item(
                family_id="U02-PF05-NUMBER-PLURAL-NOUN",
                token=singular,
                singular=singular,
                plural=plural,
                noun_vocab_ids=refs,
                prompt="Put the words in order.",
                stimulus="",
                options=[plural, DETERMINER],
                correct_answer=[DETERMINER, plural],
                accepted_answers=[],
                scoring_mode="EXACT_SEQUENCE",
                support_level="REDUCED_SUPPORT",
                approved=True,
                reason="U02QB01_PLAIN_S_NOUN_WITH_A1_NUMERIC_DETERMINER",
            )
        )
        items.append(
            make_item(
                family_id="U02-PF06-SPEAK-PLURAL-FORM",
                token=singular,
                singular=singular,
                plural=plural,
                noun_vocab_ids=refs,
                prompt=f"Say the plural form of {singular}.",
                stimulus=singular,
                options=[],
                correct_answer=None,
                accepted_answers=[plural],
                scoring_mode="FEATURE_RUBRIC",
                support_level="GUIDED",
                approved=True,
                reason="U02QB01_PLAIN_S_NOUN_AUTHORITY_BOUND",
            )
        )

    for pair in direct_adjective_pairs():
        singular = pair["noun"]
        noun = inventory.get(singular)
        approved = noun is not None
        plural = str(noun["plural"]) if noun else singular + "s"
        noun_refs = list(noun["vocabulary_ids"]) if noun else []
        reason = (
            "U01_APPROVED_ADJECTIVE_NOUN_PAIR_AND_U02QB01_PLAIN_S_NOUN"
            if approved
            else REJECT_OUTSIDE_PLAIN_S
        )
        adjective = pair["adjective"]
        adjective_id = pair["adjective_vocab_id"]
        items.append(
            make_item(
                family_id="U02-PF03-ADJECTIVE-PLURAL-NOUN",
                token=f"{adjective}-{singular}",
                singular=singular,
                plural=plural,
                noun_vocab_ids=noun_refs,
                adjective=adjective,
                adjective_vocab_id=adjective_id,
                prompt="Put the words in order.",
                stimulus="",
                options=[plural, adjective],
                correct_answer=[adjective, plural],
                accepted_answers=[],
                scoring_mode="EXACT_SEQUENCE",
                support_level="REDUCED_SUPPORT",
                approved=approved,
                reason=reason,
            )
        )
        items.append(
            make_item(
                family_id="U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN",
                token=f"{adjective}-{singular}",
                singular=singular,
                plural=plural,
                noun_vocab_ids=noun_refs,
                adjective=adjective,
                adjective_vocab_id=adjective_id,
                prompt="Put the words in order.",
                stimulus="",
                options=[plural, adjective, DETERMINER],
                correct_answer=[DETERMINER, adjective, plural],
                accepted_answers=[],
                scoring_mode="EXACT_SEQUENCE",
                support_level="REDUCED_SUPPORT",
                approved=approved,
                reason=reason,
            )
        )

    items.sort(key=lambda row: row["item_id"])
    if len(items) != EXPECTED_CANDIDATES:
        raise Unit02QuestionBankBuildError(f"CANDIDATE_COUNT_INVALID:{len(items)}")
    if len({row["item_id"] for row in items}) != len(items):
        raise Unit02QuestionBankBuildError("DUPLICATE_ITEM_ID")
    if len({row["semantic_signature"] for row in items}) != len(items):
        raise Unit02QuestionBankBuildError("DUPLICATE_SEMANTIC_SIGNATURE")
    return items


def distribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "family": dict(sorted(Counter(row["pattern_family_id"] for row in rows).items())),
        "skill": dict(sorted(Counter(row["skill"] for row in rows).items())),
        "egp_row": dict(
            sorted(Counter(row_id for row in rows for row_id in row["target_egp_row_ids"]).items())
        ),
    }


def candidate_payload() -> dict[str, Any]:
    inventory = load_inventory()
    candidates = generate_candidates()
    approved = [
        deepcopy(row)
        for row in candidates
        if row["admission_proposal"]["status"] == "AUTO_APPROVED"
    ]
    rejected = [
        row
        for row in candidates
        if row["admission_proposal"]["status"] == "AUTO_REJECTED"
    ]
    if len(approved) != EXPECTED_APPROVED or len(rejected) != EXPECTED_REJECTED:
        raise Unit02QuestionBankBuildError(
            f"ADMISSION_COUNT_INVALID:{len(approved)}:{len(rejected)}"
        )
    reject_reasons = dict(
        sorted(
            Counter(
                reason
                for row in rejected
                for reason in row["admission_proposal"]["reason_codes"]
            ).items()
        )
    )
    noun_refs = {
        ref
        for row in inventory["inventory"]
        for ref in row["vocabulary_ids"]
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": ["A1"],
        "bank_identity": {
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "cumulative_authority_mode": True,
            "unit01_runtime_base_reused": True,
            "unit01_runtime_base_item_count": UNIT01_RUNTIME_BASE_COUNT,
            "parallel_questionbank_created": False,
            "runtime_status": "NOT_CONNECTED",
        },
        "grammar_authority": {
            "target_egp_row_ids": list(TARGET_EGP_ROWS),
            "direct_pattern_ids": [DIRECT_PATTERN_ID],
            "numeric_determiner_prerequisite_egp_row_ids": [PREREQUISITE_KP009],
            "numeric_determiner_used": DETERMINER,
        },
        "source_inventory": {
            "task_id": inventory["task_id"],
            "plain_s_denominator": EXPECTED_NOUN_SURFACES,
            "exact_active_vocabulary_ref_count": EXPECTED_EXACT_NOUN_REFS,
            "inventory_sha256": digest(inventory),
        },
        "pattern_family_contracts": [deepcopy(row) for row in FAMILIES],
        "candidate_items": candidates,
        "approved_items": approved,
        "admission_readback": {
            "candidate_count": len(candidates),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "rejection_reason_counts": reject_reasons,
            "human_review_count": 0,
        },
        "distribution_counts": {
            "candidate": distribution(candidates),
            "approved": distribution(approved),
        },
        "coverage_denominators": {
            "plain_s_noun_surface_count": EXPECTED_NOUN_SURFACES,
            "plain_s_exact_active_vocabulary_ref_count": len(noun_refs),
            "covered_target_egp_row_count": len(
                {row_id for row in approved for row_id in row["target_egp_row_ids"]}
            ),
            "covered_target_egp_row_ids": sorted(
                {row_id for row in approved for row_id in row["target_egp_row_ids"]}
            ),
            "learner_mastery_claimed": False,
        },
        "admission_policy": {
            "u02qb01_plain_s_inventory_required": True,
            "plain_s_only": True,
            "unit01_adjective_pair_reuse_requires_u02_noun_admission": True,
            "rejected_source_pairs_retained_with_reason": True,
            "independent_validation_required": True,
            "semantic_dedup_required": True,
            "learner_time_generation_allowed": False,
        },
        "claim_boundaries": {
            "unit01_questionbank_mutated": False,
            "unit01_item_identity_mutated": False,
            "learner_database_written": False,
            "runtime_bundle_written": False,
            "runtime_connected": False,
            "parallel_runtime_created": False,
            "new_scene_created": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate() -> dict[str, Any]:
    inventory = load_inventory()
    return policy_artifact.build_candidate(
        payload=candidate_payload(),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "u02qb01_task_id": inventory["task_id"],
            "u02qb01_inventory_path": str(INVENTORY_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "u02qb01_inventory_sha256": digest(inventory),
            "unit01_adjective_contract_task_id": u01_contract.TASK_ID,
            "target_egp_row_ids": list(TARGET_EGP_ROWS),
            "direct_pattern_ids": [DIRECT_PATTERN_ID],
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as validator,
    )

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def main() -> int:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import (
        validate_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as validator,
    )

    report = validator.validate_approved(candidate, approved)
    payload = approved["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"CANDIDATE_COUNT={payload['admission_readback']['candidate_count']}")
    print(f"APPROVED_COUNT={payload['admission_readback']['approved_count']}")
    print(f"REJECTED_COUNT={payload['admission_readback']['rejected_count']}")
    print(f"PLAIN_S_NOUN_SURFACES={payload['coverage_denominators']['plain_s_noun_surface_count']}")
    print(f"TARGET_EGP_ROWS={payload['coverage_denominators']['covered_target_egp_row_count']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
