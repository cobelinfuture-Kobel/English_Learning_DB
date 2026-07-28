#!/usr/bin/env python3
"""Build and admit the fixed Unit 01 multi-type candidate item bank.

S03 consumes the deterministic S02 safe authoring context and writes thirteen
stable candidate items. The items are fixed, versioned, validated, deduplicated,
and admitted before any runtime projection. There is no learner-time generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s02_question_generation_context_pack as s02,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S03_"
    "Unit01MultiTypeExerciseCandidateGenerationAndAdmission"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s03.fixed_multitype_item_bank.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S03_FIXED_MULTITYPE_ITEM_BANK"
DECISION_REF = "OPERATOR_APPROVAL:2026-07-28:U01E-S00-S05"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.2-U01E-S04_"
    "Unit01MultiStandardLearnerCoverageRuntimeReadback"
)
ITEM_BANK_ID = "A1FS_V1_2_UNIT01_FIXED_ITEM_BANK"
ITEM_BANK_VERSION = "1.0.0"

QUESTION_TYPE_CONTRACTS: dict[str, dict[str, Any]] = {
    "multiple_choice": {
        "interaction_mode": "SINGLE_SELECT",
        "response_type": "string",
        "scoring_mode": "EXACT_OPTION",
    },
    "context_match": {
        "interaction_mode": "SINGLE_SELECT",
        "response_type": "string",
        "scoring_mode": "EXACT_OPTION",
    },
    "error_discrimination": {
        "interaction_mode": "SINGLE_SELECT",
        "response_type": "string",
        "scoring_mode": "EXACT_OPTION",
    },
    "gap_fill": {
        "interaction_mode": "TEXT_INPUT",
        "response_type": "string",
        "scoring_mode": "NORMALIZED_TEXT",
    },
    "word_order": {
        "interaction_mode": "TOKEN_SEQUENCE",
        "response_type": "sequence",
        "scoring_mode": "EXACT_SEQUENCE",
    },
    "guided_sentence": {
        "interaction_mode": "ORAL_PRACTICE_NO_CAPTURE",
        "response_type": "string",
        "scoring_mode": "FEATURE_RUBRIC",
    },
    "checkpoint_choice": {
        "interaction_mode": "SINGLE_SELECT",
        "response_type": "string",
        "scoring_mode": "EXACT_OPTION",
    },
    "checkpoint_write": {
        "interaction_mode": "HUMAN_REVIEW_TEXT",
        "response_type": "string",
        "scoring_mode": "FEATURE_RUBRIC",
    },
}

ITEM_SPECS: tuple[dict[str, Any], ...] = (
    {
        "candidate_item_id": "U01E-S03-C02-R01",
        "skill": "READING",
        "question_type": "context_match",
        "context_id": "U01-C2-HOME-TOY-BOX",
        "learning_role": "NEW",
        "support_level": "GUIDED",
        "prompt": "Which place has the CD player?",
        "options": ["the living room", "the park", "the toy shop"],
        "correct_answer": "the living room",
        "acceptable_variants": ["living room"],
        "explanation": "The first sentence says the CD player is in the living room.",
        "evidence_sentence": "There is a CD player in the living room.",
        "error_tags": ["CONTEXT_LOCATION_MISMATCH"],
        "remediation_tags": ["REVIEW_LIVING_ROOM_CONTEXT"],
    },
    {
        "candidate_item_id": "U01E-S03-C02-R02",
        "skill": "READING",
        "question_type": "word_order",
        "context_id": "U01-C2-HOME-TOY-BOX",
        "learning_role": "REVIEW",
        "support_level": "REDUCED_SUPPORT",
        "prompt": "Put the words in order to make the sentence about the toy.",
        "options": ["box", "a", "in", "is", "toy", "a"],
        "correct_answer": ["a", "toy", "is", "in", "a", "box"],
        "acceptable_variants": [],
        "explanation": "The sentence names one new toy and one box.",
        "evidence_sentence": "A toy is in a box near the bed.",
        "error_tags": ["WORD_ORDER", "ARTICLE_BEFORE_SINGULAR_NOUN"],
        "remediation_tags": ["REBUILD_A_NOUN_PHRASE"],
    },
    {
        "candidate_item_id": "U01E-S03-C02-W01",
        "skill": "WRITING",
        "question_type": "gap_fill",
        "context_id": "U01-C2-HOME-TOY-BOX",
        "learning_role": "WEAK",
        "support_level": "GUIDED",
        "prompt": "Complete the sentence: A toy is in ___ box near the bed.",
        "options": [],
        "correct_answer": "a",
        "acceptable_variants": ["a"],
        "explanation": "Use a before the singular consonant-sound noun box.",
        "evidence_sentence": "A toy is in a box near the bed.",
        "error_tags": ["ARTICLE_A_AN_SELECTION"],
        "remediation_tags": ["REVIEW_A_BEFORE_CONSONANT_SOUND"],
    },
    {
        "candidate_item_id": "U01E-S03-C03-R01",
        "skill": "READING",
        "question_type": "multiple_choice",
        "context_id": "U01-C3-PICNIC-FOOD",
        "learning_role": "NEW",
        "support_level": "GUIDED",
        "prompt": "Which two foods are in the basket?",
        "options": ["an orange and an egg", "a toy and a book", "an ice cream and a robot"],
        "correct_answer": "an orange and an egg",
        "acceptable_variants": [],
        "explanation": "The first sentence names an orange and an egg in the basket.",
        "evidence_sentence": "Mia has an orange and an egg in a basket.",
        "error_tags": ["EXPLICIT_DETAIL_MISMATCH"],
        "remediation_tags": ["REREAD_PICNIC_SENTENCE"],
    },
    {
        "candidate_item_id": "U01E-S03-C03-W01",
        "skill": "WRITING",
        "question_type": "word_order",
        "context_id": "U01-C3-PICNIC-FOOD",
        "learning_role": "WEAK",
        "support_level": "REDUCED_SUPPORT",
        "prompt": "Put the words in order to name the food.",
        "options": ["egg", "an"],
        "correct_answer": ["an", "egg"],
        "acceptable_variants": [],
        "explanation": "Use an before the vowel-sound noun egg.",
        "evidence_sentence": "Mia has an orange and an egg in a basket.",
        "error_tags": ["ARTICLE_A_AN_SELECTION", "WORD_ORDER"],
        "remediation_tags": ["REBUILD_AN_NOUN_PHRASE"],
    },
    {
        "candidate_item_id": "U01E-S03-C03-S01",
        "skill": "SPEAKING",
        "question_type": "guided_sentence",
        "context_id": "U01-C3-PICNIC-FOOD",
        "learning_role": "NEW",
        "support_level": "GUIDED",
        "prompt": "Say what food Mia has for the picnic.",
        "options": [],
        "correct_answer": None,
        "acceptable_variants": ["Mia has an orange and an egg."],
        "explanation": "Use the frame Mia has an ___ and an ___.",
        "evidence_sentence": "Mia has an orange and an egg in a basket.",
        "error_tags": ["SPEAKING_ARTICLE_FRAME"],
        "remediation_tags": ["ORAL_MODEL_AN_ORANGE_AN_EGG"],
    },
    {
        "candidate_item_id": "U01E-S03-C04-R01",
        "skill": "READING",
        "question_type": "context_match",
        "context_id": "U01-C4-TOY-SHOP",
        "learning_role": "REVIEW",
        "support_level": "REDUCED_SUPPORT",
        "prompt": "Which place is near the bus stop?",
        "options": ["a toy shop", "a classroom", "a park"],
        "correct_answer": "a toy shop",
        "acceptable_variants": ["the toy shop", "toy shop"],
        "explanation": "The first sentence says a toy shop is near the bus stop.",
        "evidence_sentence": "There is a toy shop near the bus stop.",
        "error_tags": ["CONTEXT_LOCATION_MISMATCH"],
        "remediation_tags": ["REREAD_TOY_SHOP_LOCATION"],
    },
    {
        "candidate_item_id": "U01E-S03-C04-W01",
        "skill": "WRITING",
        "question_type": "error_discrimination",
        "context_id": "U01-C4-TOY-SHOP",
        "learning_role": "WEAK",
        "support_level": "GUIDED",
        "prompt": "Choose the sentence with the correct article.",
        "options": [
            "There is a toy shop near the bus stop.",
            "There is an toy shop near the bus stop.",
            "There is toy shop near the bus stop.",
        ],
        "correct_answer": "There is a toy shop near the bus stop.",
        "acceptable_variants": [],
        "explanation": "Toy begins with a consonant sound, so use a.",
        "evidence_sentence": "There is a toy shop near the bus stop.",
        "error_tags": ["ARTICLE_A_AN_SELECTION", "MISSING_ARTICLE"],
        "remediation_tags": ["CONTRAST_A_TOY_AN_EGG"],
    },
    {
        "candidate_item_id": "U01E-S03-C04-S01",
        "skill": "SPEAKING",
        "question_type": "guided_sentence",
        "context_id": "U01-C4-TOY-SHOP",
        "learning_role": "NEW",
        "support_level": "REDUCED_SUPPORT",
        "prompt": "Say what Mia sees in the shop window.",
        "options": [],
        "correct_answer": None,
        "acceptable_variants": ["Mia sees a robot in the shop window."],
        "explanation": "Use the frame Mia sees a ___ in the shop window.",
        "evidence_sentence": "Mia sees a robot in the shop window.",
        "error_tags": ["SPEAKING_ARTICLE_FRAME"],
        "remediation_tags": ["ORAL_MODEL_A_ROBOT"],
    },
    {
        "candidate_item_id": "U01E-S03-C05-R01",
        "skill": "READING",
        "question_type": "gap_fill",
        "context_id": "U01-C5-PARK-BIRTHDAY",
        "learning_role": "TRANSFER",
        "support_level": "UNSEEN_TRANSFER",
        "prompt": "Complete the new sentence: There is ___ birthday party in the park.",
        "options": [],
        "correct_answer": "a",
        "acceptable_variants": ["a"],
        "explanation": "Use a before the singular consonant-sound noun birthday party.",
        "evidence_sentence": "There is a birthday party in the park.",
        "error_tags": ["UNSEEN_ARTICLE_TRANSFER"],
        "remediation_tags": ["TRANSFER_A_TO_NEW_CONTEXT"],
    },
    {
        "candidate_item_id": "U01E-S03-C05-R02",
        "skill": "READING",
        "question_type": "checkpoint_choice",
        "context_id": "U01-C5-PARK-BIRTHDAY",
        "learning_role": "REVIEW",
        "support_level": "INDEPENDENT",
        "prompt": "Which sentence correctly introduces the animal for the first time?",
        "options": [
            "A dog is near a tree and a bench.",
            "An dog is near a tree and a bench.",
            "The dog is near a tree and a bench.",
        ],
        "correct_answer": "A dog is near a tree and a bench.",
        "acceptable_variants": [],
        "explanation": "The dog is new information, and dog begins with a consonant sound.",
        "evidence_sentence": "A dog is near a tree and a bench.",
        "error_tags": ["FIRST_MENTION_ARTICLE", "ARTICLE_A_AN_SELECTION"],
        "remediation_tags": ["REVIEW_FIRST_MENTION_A"],
    },
    {
        "candidate_item_id": "U01E-S03-C05-W01",
        "skill": "WRITING",
        "question_type": "checkpoint_write",
        "context_id": "U01-C5-PARK-BIRTHDAY",
        "learning_role": "TRANSFER",
        "support_level": "UNSEEN_TRANSFER",
        "prompt": "Write one new complete sentence about the party or park. Use a, an, or the correctly.",
        "options": [],
        "correct_answer": None,
        "acceptable_variants": [],
        "explanation": "A complete contextual sentence requires human review against the article rubric.",
        "evidence_sentence": "There is a birthday party in the park.",
        "error_tags": ["OPEN_WRITING_ARTICLE_CONTROL"],
        "remediation_tags": ["GUIDED_CONTEXTUAL_SENTENCE_REBUILD"],
    },
    {
        "candidate_item_id": "U01E-S03-C05-S01",
        "skill": "SPEAKING",
        "question_type": "guided_sentence",
        "context_id": "U01-C5-PARK-BIRTHDAY",
        "learning_role": "NEW",
        "support_level": "INDEPENDENT",
        "prompt": "Say what the dog has.",
        "options": [],
        "correct_answer": None,
        "acceptable_variants": ["The dog has a toy."],
        "explanation": "Use the known noun the dog and introduce one toy with a.",
        "evidence_sentence": "The dog has a toy.",
        "error_tags": ["KNOWN_NOUN_AND_NEW_OBJECT_ARTICLES"],
        "remediation_tags": ["ORAL_MODEL_THE_DOG_A_TOY"],
    },
)


class S03ItemBankError(ValueError):
    """Fail-closed fixed item-bank construction or admission error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


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


def normalized_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(normalized_text(row) for row in value)
    return " ".join(re.findall(r"[a-z0-9']+", str(value).casefold()))


def flatten_text(spec: Mapping[str, Any], stimulus_body: str) -> str:
    values: list[Any] = [
        stimulus_body,
        spec.get("prompt"),
        spec.get("options"),
        spec.get("correct_answer"),
        spec.get("acceptable_variants"),
        spec.get("evidence_sentence"),
    ]
    return " ".join(normalized_text(value) for value in values)


def label_map(
    rows: Sequence[Mapping[str, Any]], *, id_field: str
) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        label = normalized_text(row.get("label"))
        identity = str(row.get(id_field) or "")
        if label and identity:
            result[label] = identity
    return result


def refs_in_text(text: str, labels: Mapping[str, str]) -> list[str]:
    padded = f" {normalized_text(text)} "
    return sorted(
        identity
        for label, identity in labels.items()
        if f" {label} " in padded
    )


def context_map(safe_pack: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result = {
        str(row["context_id"]): row
        for row in safe_pack.get("approved_contexts", [])
        if isinstance(row, Mapping) and row.get("context_id")
    }
    if len(result) != 5:
        raise S03ItemBankError("approved_context_map_invalid")
    return result


def sentence_map(safe_pack: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = safe_pack.get("approved_language_targets", {}).get("sentences", [])
    result = {
        str(row["text"]): row
        for row in rows
        if isinstance(row, Mapping) and row.get("text") and row.get("sentence_id")
    }
    if not result:
        raise S03ItemBankError("approved_sentence_map_missing")
    return result


def response_contract(spec: Mapping[str, Any]) -> dict[str, Any]:
    question_type = str(spec["question_type"])
    contract = QUESTION_TYPE_CONTRACTS[question_type]
    mode = str(contract["scoring_mode"])
    skill = str(spec["skill"])
    if skill == "SPEAKING":
        return {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "accepted_texts": [],
            "accepted_sequence": [],
            "human_review_fallback": True,
            "capture_enabled": False,
            "rubric": {"practice_only": True},
        }
    if question_type == "checkpoint_write":
        return {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "accepted_texts": [],
            "accepted_sequence": [],
            "human_review_fallback": True,
            "capture_enabled": True,
            "rubric": {
                "grammar_target_match": True,
                "meaning_matches_context": True,
                "complete_response": True,
            },
        }
    if mode == "EXACT_SEQUENCE":
        sequence = list(spec["correct_answer"])
        return {
            "scoring_mode": mode,
            "response_type": "sequence",
            "accepted_texts": [],
            "accepted_sequence": sequence,
            "human_review_fallback": False,
            "capture_enabled": True,
        }
    accepted = [str(spec["correct_answer"])] + [
        str(row) for row in spec.get("acceptable_variants", [])
    ]
    return {
        "scoring_mode": mode,
        "response_type": "string",
        "accepted_texts": list(dict.fromkeys(accepted)),
        "accepted_sequence": [],
        "human_review_fallback": False,
        "capture_enabled": True,
    }


def build_item(
    spec: Mapping[str, Any], safe_pack: Mapping[str, Any]
) -> dict[str, Any]:
    contexts = context_map(safe_pack)
    sentences = sentence_map(safe_pack)
    context_id = str(spec["context_id"])
    context = contexts.get(context_id)
    if not isinstance(context, Mapping):
        raise S03ItemBankError(f"item_context_missing:{context_id}")
    evidence = str(spec["evidence_sentence"])
    sentence = sentences.get(evidence)
    if not isinstance(sentence, Mapping) or sentence.get("context_id") != context_id:
        raise S03ItemBankError(
            f"item_evidence_sentence_not_approved:{spec['candidate_item_id']}"
        )
    stimulus_body = " ".join(str(row) for row in context.get("sentences", []))
    searchable = flatten_text(spec, stimulus_body)
    language = safe_pack.get("approved_language_targets", {})
    vocabulary_labels = label_map(language.get("vocabulary", []), id_field="authority_id")
    chunk_labels = label_map(language.get("canonical_chunks", []), id_field="authority_id")
    phrase_labels = label_map(language.get("context_phrases", []), id_field="phrase_id")
    evp_refs = refs_in_text(searchable, vocabulary_labels)
    if not evp_refs:
        raise S03ItemBankError(
            f"item_without_selected_evp_target:{spec['candidate_item_id']}"
        )
    question_type = str(spec["question_type"])
    interaction = QUESTION_TYPE_CONTRACTS[question_type]
    item = {
        "candidate_item_id": str(spec["candidate_item_id"]),
        "skill": str(spec["skill"]),
        "question_type": question_type,
        "stimulus": {
            "kind": "FIXED_CONTEXT_TEXT",
            "title": str(context["title"]),
            "body": stimulus_body,
        },
        "prompt": str(spec["prompt"]),
        "options": deepcopy(list(spec.get("options", []))),
        "correct_answer": deepcopy(spec.get("correct_answer")),
        "acceptable_variants": deepcopy(list(spec.get("acceptable_variants", []))),
        "explanation": str(spec["explanation"]),
        "target_evp_sense_ids": evp_refs,
        "target_egp_row_ids": sorted(
            str(row)
            for row in safe_pack.get("target_inventory", {}).get("egp_row_ids", [])
        ),
        "target_chunk_ids": refs_in_text(searchable, chunk_labels),
        "target_context_phrase_ids": refs_in_text(searchable, phrase_labels),
        "target_sentence_ids": [str(sentence["sentence_id"])],
        "target_pattern_ids": sorted(
            str(row)
            for row in safe_pack.get("target_inventory", {}).get("pattern_ids", [])
        ),
        "target_ket_prerequisite_node_ids": [],
        "cambridge_stage": "STARTERS",
        "cambridge_capability_refs": [],
        "assessment_pattern_ref": question_type,
        "learning_role": str(spec["learning_role"]),
        "support_level": str(spec["support_level"]),
        "context_id": context_id,
        "source_refs": [
            {
                "source_type": "S01_APPROVED_UNIT01_CONTEXT",
                "source_sha256": safe_pack["source_identity"]["s01_approved_sha256"],
                "context_id": context_id,
            },
            {
                "source_type": "S01_APPROVED_SENTENCE",
                "sentence_id": str(sentence["sentence_id"]),
            },
        ],
        "answerability_evidence": {
            "evidence_sentence_id": str(sentence["sentence_id"]),
            "evidence_sentence": evidence,
            "answer_present_in_supplied_context": True,
        },
        "error_tags": deepcopy(list(spec.get("error_tags", []))),
        "remediation_tags": deepcopy(list(spec.get("remediation_tags", []))),
        "interaction_contract": deepcopy(interaction),
        "response_contract": response_contract(spec),
        "learner_delivery_status": "CANDIDATE_NOT_RUNTIME",
        "runtime_generation_used": False,
    }
    signature_payload = {
        "skill": item["skill"],
        "question_type": item["question_type"],
        "context_id": item["context_id"],
        "prompt": normalized_text(item["prompt"]),
        "target_evp_sense_ids": item["target_evp_sense_ids"],
        "target_egp_row_ids": item["target_egp_row_ids"],
        "target_chunk_ids": item["target_chunk_ids"],
        "target_context_phrase_ids": item["target_context_phrase_ids"],
        "target_sentence_ids": item["target_sentence_ids"],
        "target_pattern_ids": item["target_pattern_ids"],
    }
    item["semantic_signature"] = digest(signature_payload)
    return item


def build_items(safe_pack: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = [build_item(spec, safe_pack) for spec in ITEM_SPECS]
    items.sort(key=lambda row: row["candidate_item_id"])
    if len(items) != s02.NEW_CANDIDATE_TARGET_COUNT:
        raise S03ItemBankError(f"candidate_item_count_invalid:{len(items)}")
    identities = [str(row["candidate_item_id"]) for row in items]
    signatures = [str(row["semantic_signature"]) for row in items]
    if len(identities) != len(set(identities)):
        raise S03ItemBankError("candidate_item_identity_duplicate")
    if len(signatures) != len(set(signatures)):
        raise S03ItemBankError("candidate_semantic_signature_duplicate")
    existing = set(safe_pack.get("existing_semantic_signatures", []))
    collision = sorted(existing.intersection(signatures))
    if collision:
        raise S03ItemBankError(f"existing_semantic_signature_collision:{collision[0]}")
    return items


def candidate_payload(database_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s01_approved = s02.verified_s01_approved(database_path)
    safe_pack = s02.build_safe_pack(s01_approved)
    items = build_items(safe_pack)
    counts = {
        "skill": dict(sorted(Counter(row["skill"] for row in items).items())),
        "context": dict(sorted(Counter(row["context_id"] for row in items).items())),
        "question_type": dict(
            sorted(Counter(row["question_type"] for row in items).items())
        ),
        "learning_role": dict(
            sorted(Counter(row["learning_role"] for row in items).items())
        ),
        "support_level": dict(
            sorted(Counter(row["support_level"] for row in items).items())
        ),
    }
    payload = {
        "item_bank_id": ITEM_BANK_ID,
        "item_bank_version": ITEM_BANK_VERSION,
        "unit_id": s01_approved["payload"]["unit_id"],
        "level_scope": ["A1"],
        "generation_mode": "FIXED_OFFLINE_CANDIDATE_BANK",
        "existing_activity_count": s02.EXISTING_ACTIVITY_COUNT,
        "new_candidate_item_count": len(items),
        "target_total_activity_count": s02.TARGET_TOTAL_ACTIVITY_COUNT,
        "question_type_contracts": deepcopy(QUESTION_TYPE_CONTRACTS),
        "candidate_items": items,
        "distribution_counts": counts,
        "source_context_pack": {
            "task_id": s02.TASK_ID,
            "safe_pack_sha256": safe_pack["pack_sha256"],
            "s01_approved_sha256": safe_pack["source_identity"]["s01_approved_sha256"],
            "existing_semantic_signatures": list(
                safe_pack["existing_semantic_signatures"]
            ),
        },
        "admission_policy": {
            "candidate_only": True,
            "independent_validation_required": True,
            "human_review_required_for_open_writing": True,
            "approved_bank_required_before_runtime": True,
            "runtime_free_generation_allowed": False,
            "unvalidated_variant_delivery_allowed": False,
        },
        "claim_boundaries": {
            "learner_private_state_used": False,
            "learner_database_written": False,
            "response_contract_database_written": False,
            "runtime_bundle_written": False,
            "existing_asset_identity_changed": False,
            "generated_at_learner_runtime": False,
            "ket_coverage_claimed": False,
            "cambridge_granular_capability_claimed": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
    }
    return payload, safe_pack


def build_candidate(database_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, safe_pack = candidate_payload(database_path)
    candidate = policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "s02_task_id": s02.TASK_ID,
            "s02_safe_pack_sha256": safe_pack["pack_sha256"],
            "s01_approved_sha256": safe_pack["source_identity"]["s01_approved_sha256"],
            "operator_decision_ref": DECISION_REF,
            "item_bank_id": ITEM_BANK_ID,
            "item_bank_version": ITEM_BANK_VERSION,
        },
    )
    return candidate, safe_pack


def admit_candidate(
    candidate: Mapping[str, Any], safe_pack: Mapping[str, Any]
) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as validator,
    )

    receipt = validator.validate_candidate(candidate, safe_pack)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def materialize(
    *,
    database_path: Path,
    candidate_path: Path,
    approved_path: Path,
    report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate, safe_pack = build_candidate(database_path)
    approved = admit_candidate(candidate, safe_pack)
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as validator,
    )

    report = validator.validate_approved(candidate, approved, safe_pack)
    if report["error_count"]:
        raise S03ItemBankError(
            "approved_validation_failed:" + "|".join(report["errors"])
        )
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _, _, report = materialize(
            database_path=args.database,
            candidate_path=args.candidate,
            approved_path=args.approved,
            report_path=args.report,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (
        S03ItemBankError,
        s02.S02ContextPackError,
        policy_artifact.ContentPolicyBuildError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
