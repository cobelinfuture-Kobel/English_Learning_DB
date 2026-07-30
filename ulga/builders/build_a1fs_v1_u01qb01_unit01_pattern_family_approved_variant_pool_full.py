#!/usr/bin/env python3
"""Expand the Unit01 seed pool to the complete capacity supported by current authority."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as seed,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB01_Unit01PatternFamilyAndApprovedVariantPoolFullBuildV2"
SCHEMA_VERSION = "a1fs.v1.u01qb01.unit01_pattern_family_approved_variant_pool.v2"
PASS_STATUS = "PASS_A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL_FULL_V2"
DECISION_REF = "OPERATOR_APPROVAL:2026-07-30:U01QB01_FULL_V2"
UNIT_ID = seed.UNIT_ID
BANK_ID = seed.BANK_ID
BANK_VERSION = "1.1.0"
BASELINE_ACTIVITY_COUNT = seed.BASELINE_ACTIVITY_COUNT
APPROVED_CONTRACT_SHA256 = seed.APPROVED_CONTRACT_SHA256
EXPECTED_SEED_COUNT = 109
EXPECTED_EXPANSION_COUNT = 199
EXPECTED_ITEM_COUNT = 308
RAW_COMBINATORIAL_CAPACITY = 944
DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb01_unit01_variant_pool_v2.candidate.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb01_unit01_variant_pool_v2.approved.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb01_unit01_variant_pool_v2_validation.json")
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB02_"
    "Unit01ApprovedVariantSessionAssemblerAndExposureHistoryRuntimeIntegration"
)

PATTERN_NOUN = seed.PATTERN_NOUN
PATTERN_ADJECTIVE = seed.PATTERN_ADJECTIVE
PATTERN_VERY = seed.PATTERN_VERY
FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS = seed.FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS

def family(fid: str, skill: str, qtype: str, pattern: str, count: int) -> dict[str, Any]:
    return {
        "family_id": fid,
        "skill": skill,
        "question_type": qtype,
        "pattern_id": pattern,
        "expected_count": count,
    }

EXPANSION_FAMILY_CONTRACTS: tuple[dict[str, Any], ...] = (
    family("U01-PF11-I-SEE-NOUN-GAP", "WRITING", "gap_fill", PATTERN_NOUN, 16),
    family("U01-PF12-THERE-IS-NOUN-CHOICE", "READING", "multiple_choice", PATTERN_NOUN, 16),
    family("U01-PF13-I-SEE-NOUN-ORDER", "WRITING", "word_order", PATTERN_NOUN, 16),
    family("U01-PF14-KNOWN-THE-GAP", "WRITING", "gap_fill", PATTERN_NOUN, 16),
    family("U01-PF15-KNOWN-THE-ERROR", "READING", "error_discrimination", PATTERN_NOUN, 16),
    family("U01-PF16-MIA-SEES-NOUN-CHOICE", "READING", "multiple_choice", PATTERN_NOUN, 16),
    family("U01-PF17-THERE-IS-NOUN-ORDER", "WRITING", "word_order", PATTERN_NOUN, 16),
    family("U01-PF18-SPEAK-I-SEE-NOUN", "SPEAKING", "guided_sentence", PATTERN_NOUN, 16),
    family("U01-PF19-FIRST-KNOWN-EXTENSION", "READING", "context_match", PATTERN_NOUN, 8),
    family("U01-PF20-AAN-ADJ-NOUN-CHOICE", "READING", "multiple_choice", PATTERN_ADJECTIVE, 6),
    family("U01-PF21-ADJ-NOUN-ERROR", "READING", "error_discrimination", PATTERN_ADJECTIVE, 6),
    family("U01-PF22-I-SEE-ADJ-NOUN-GAP", "WRITING", "gap_fill", PATTERN_ADJECTIVE, 6),
    family("U01-PF23-THERE-IS-ADJ-NOUN-CHOICE", "READING", "multiple_choice", PATTERN_ADJECTIVE, 6),
    family("U01-PF24-I-SEE-ADJ-NOUN-ORDER", "WRITING", "word_order", PATTERN_ADJECTIVE, 6),
    family("U01-PF25-THERE-IS-ADJ-NOUN-ORDER", "WRITING", "word_order", PATTERN_ADJECTIVE, 6),
    family("U01-PF26-SPEAK-I-SEE-ADJ-NOUN", "SPEAKING", "guided_sentence", PATTERN_ADJECTIVE, 6),
    family("U01-PF27-A-VERY-ADJ-NOUN-GAP", "WRITING", "gap_fill", PATTERN_VERY, 3),
    family("U01-PF28-A-VERY-ADJ-NOUN-CHOICE", "READING", "multiple_choice", PATTERN_VERY, 3),
    family("U01-PF29-VERY-ADJ-NOUN-ERROR", "READING", "error_discrimination", PATTERN_VERY, 3),
    family("U01-PF30-I-SEE-VERY-ADJ-NOUN-GAP", "WRITING", "gap_fill", PATTERN_VERY, 3),
    family("U01-PF31-THERE-IS-VERY-ADJ-NOUN-CHOICE", "READING", "multiple_choice", PATTERN_VERY, 3),
    family("U01-PF32-SPEAK-VERY-ADJ-NOUN", "SPEAKING", "guided_sentence", PATTERN_VERY, 3),
    family("U01-PF33-SPEAK-I-SEE-VERY-ADJ-NOUN", "SPEAKING", "guided_sentence", PATTERN_VERY, 3),
)
FAMILY_CONTRACTS = tuple(deepcopy(row) for row in seed.FAMILY_CONTRACTS) + EXPANSION_FAMILY_CONTRACTS

class FullVariantPoolBuildError(ValueError):
    """Fail-closed Unit01 full-pool construction error."""

def canonical(value: Any) -> str:
    return seed.canonical(value)

def digest(value: Any) -> str:
    return seed.digest(value)

def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass

def family_contract(family_id: str) -> Mapping[str, Any]:
    return next(row for row in FAMILY_CONTRACTS if row["family_id"] == family_id)

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
    contract = family_contract(family_id)
    speaking = contract["skill"] == "SPEAKING"
    item = {
        "item_id": f"U01QB01-{seed.slug(family_id)}-{seed.slug(token)}",
        "unit_id": UNIT_ID,
        "pattern_family_id": family_id,
        "unit_pattern_ids": [target_pattern_id],
        "grammar_target_ids": [
            "ARTICLE_NOUN_PHRASE_CONTROL",
            "ARTICLE_FIRST_TO_KNOWN_REFERENCE"
            if "KNOWN" in family_id
            else "ARTICLE_FORM_SELECTION",
        ],
        "target_egp_row_ids": sorted(str(value) for value in target_egp_row_ids),
        "target_evp_sense_ids": sorted(str(value) for value in target_evp_sense_ids),
        "skill": contract["skill"],
        "question_type": contract["question_type"],
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
                "task_id": seed.contract_builder.TASK_ID,
                "contract_sha256": APPROVED_CONTRACT_SHA256,
            },
            {
                "source_type": "UNIT01_LOCAL_PATTERN_AUTHORITY",
                "task_id": seed.pattern_authority.TASK_ID,
                "pattern_id": target_pattern_id,
            },
            {
                "source_type": "U01QB01_SEED_VARIANT_POOL",
                "task_id": seed.TASK_ID,
                "seed_item_count": EXPECTED_SEED_COUNT,
            },
        ],
    }
    item["semantic_signature"] = digest(
        {
            "family": family_id,
            "pattern": target_pattern_id,
            "prompt": prompt,
            "stimulus": stimulus,
            "options": list(options),
            "correct_answer": correct_answer,
            "evp": item["target_evp_sense_ids"],
            "egp": item["target_egp_row_ids"],
        }
    )
    item["response_contract"] = seed.response_contract(
        scoring_mode=scoring_mode,
        correct_answer=correct_answer,
        accepted_answers=accepted_answers,
        speaking=speaking,
    )
    return item

def noun_expansion_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    egp = [seed.contract_builder.CORE_EGP_ROWS[0]]
    omitted = set(row["lemma"] for row in seed.active_nouns()) - set(seed.DISCOURSE_NOUNS)
    for row in seed.active_nouns():
        lemma, sense = row["lemma"], row["evp_sense_id"]
        phrase, definite = row["indefinite_phrase"], row["definite_phrase"]
        article = seed.article_from_phrase(phrase)
        rows = [
            ("U01-PF11-I-SEE-NOUN-GAP", "Complete the sentence with a or an.", f"I can see ___ {lemma}.", [], article, [article], "NORMALIZED_TEXT", "GUIDED", False),
            ("U01-PF12-THERE-IS-NOUN-CHOICE", "Choose the article.", f"There is ___ {lemma} here.", ["a", "an"], article, [article], "EXACT_OPTION", "GUIDED", False),
            ("U01-PF13-I-SEE-NOUN-ORDER", "Put the words in order.", "", ["I", "can", "see", lemma, article], ["I", "can", "see", article, lemma], [], "EXACT_SEQUENCE", "REDUCED_SUPPORT", False),
            ("U01-PF14-KNOWN-THE-GAP", "Complete the second mention.", f"I can see {phrase}. ___ {lemma} is easy to see.", [], "the", ["the"], "NORMALIZED_TEXT", "INDEPENDENT", True),
            ("U01-PF15-KNOWN-THE-ERROR", "Choose the phrase for the known item.", f"I can see {phrase}.", [definite, phrase], definite, [definite], "EXACT_OPTION", "INDEPENDENT", True),
            ("U01-PF16-MIA-SEES-NOUN-CHOICE", "Choose the article.", f"Mia sees ___ {lemma}.", ["a", "an"], article, [article], "EXACT_OPTION", "REDUCED_SUPPORT", True),
            ("U01-PF17-THERE-IS-NOUN-ORDER", "Put the words in order.", "", ["There", "is", lemma, article, "here"], ["There", "is", article, lemma, "here"], [], "EXACT_SEQUENCE", "REDUCED_SUPPORT", True),
            ("U01-PF18-SPEAK-I-SEE-NOUN", f"Say a sentence about one {lemma}.", lemma, [], None, [f"I can see {phrase}."], "FEATURE_RUBRIC", "REDUCED_SUPPORT", True),
        ]
        for fid, prompt, stimulus, options, answer, accepted, mode, support, transfer in rows:
            items.append(
                make_item(
                    family_id=fid,
                    token=lemma,
                    prompt=prompt,
                    stimulus=stimulus,
                    options=options,
                    correct_answer=answer,
                    accepted_answers=accepted,
                    target_evp_sense_ids=[sense],
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_NOUN,
                    scoring_mode=mode,
                    support_level=support,
                    transfer_eligible=transfer,
                )
            )
        if lemma in omitted:
            items.append(
                make_item(
                    family_id="U01-PF19-FIRST-KNOWN-EXTENSION",
                    token=lemma,
                    prompt="Choose the article for the same noun the second time.",
                    stimulus=f"I can see {phrase}. ___ {lemma} is easy to see.",
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

def adjective_expansion_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    egp = [seed.contract_builder.CORE_EGP_ROWS[1]]
    for row in seed.direct_adjective_phrases():
        phrase, article = row["phrase"], row["article"]
        adjective, noun = row["adjective"], row["noun"]
        wrong = seed.wrong_indefinite(article)
        senses = [row["adjective_evp_sense_id"], row["noun_evp_sense_id"]]
        token = f"{adjective}-{noun}"
        rows = [
            ("U01-PF20-AAN-ADJ-NOUN-CHOICE", "Choose the article.", f"___ {adjective} {noun}", ["a", "an"], article, [article], "EXACT_OPTION", "GUIDED", False),
            ("U01-PF21-ADJ-NOUN-ERROR", "Choose the correct noun phrase.", "", [phrase, f"{wrong} {adjective} {noun}"], phrase, [phrase], "EXACT_OPTION", "REDUCED_SUPPORT", False),
            ("U01-PF22-I-SEE-ADJ-NOUN-GAP", "Complete the sentence with a or an.", f"I can see ___ {adjective} {noun}.", [], article, [article], "NORMALIZED_TEXT", "GUIDED", True),
            ("U01-PF23-THERE-IS-ADJ-NOUN-CHOICE", "Choose the article.", f"There is ___ {adjective} {noun} here.", ["a", "an"], article, [article], "EXACT_OPTION", "GUIDED", True),
            ("U01-PF24-I-SEE-ADJ-NOUN-ORDER", "Put the words in order.", "", ["I", "can", "see", noun, article, adjective], ["I", "can", "see", article, adjective, noun], [], "EXACT_SEQUENCE", "REDUCED_SUPPORT", True),
            ("U01-PF25-THERE-IS-ADJ-NOUN-ORDER", "Put the words in order.", "", ["There", "is", noun, article, adjective, "here"], ["There", "is", article, adjective, noun, "here"], [], "EXACT_SEQUENCE", "REDUCED_SUPPORT", True),
            ("U01-PF26-SPEAK-I-SEE-ADJ-NOUN", f"Say a sentence about one {adjective} {noun}.", f"{adjective} {noun}", [], None, [f"I can see {phrase}."], "FEATURE_RUBRIC", "REDUCED_SUPPORT", True),
        ]
        for fid, prompt, stimulus, options, answer, accepted, mode, support, transfer in rows:
            items.append(
                make_item(
                    family_id=fid,
                    token=token,
                    prompt=prompt,
                    stimulus=stimulus,
                    options=options,
                    correct_answer=answer,
                    accepted_answers=accepted,
                    target_evp_sense_ids=senses,
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_ADJECTIVE,
                    scoring_mode=mode,
                    support_level=support,
                    transfer_eligible=transfer,
                )
            )
    return items

def very_expansion_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    egp = [seed.contract_builder.GUIDED_EGP_ROWS[0]]
    for row in seed.very_adjective_phrases():
        phrase, article = row["phrase"], row["article"]
        adjective, noun = row["adjective"], row["noun"]
        senses = [row["adjective_evp_sense_id"], row["noun_evp_sense_id"]]
        token = f"{adjective}-{noun}"
        rows = [
            ("U01-PF27-A-VERY-ADJ-NOUN-GAP", "Complete with a or an.", f"___ very {adjective} {noun}", [], article, [article], "NORMALIZED_TEXT", "GUIDED_EXTENSION", False),
            ("U01-PF28-A-VERY-ADJ-NOUN-CHOICE", "Choose the article.", f"___ very {adjective} {noun}", ["a", "an"], article, [article], "EXACT_OPTION", "GUIDED_EXTENSION", False),
            ("U01-PF29-VERY-ADJ-NOUN-ERROR", "Choose the correct guided phrase.", "", [phrase, f"an very {adjective} {noun}"], phrase, [phrase], "EXACT_OPTION", "GUIDED_EXTENSION", False),
            ("U01-PF30-I-SEE-VERY-ADJ-NOUN-GAP", "Complete the sentence with a or an.", f"I can see ___ very {adjective} {noun}.", [], article, [article], "NORMALIZED_TEXT", "GUIDED_EXTENSION", True),
            ("U01-PF31-THERE-IS-VERY-ADJ-NOUN-CHOICE", "Choose the article.", f"There is ___ very {adjective} {noun} here.", ["a", "an"], article, [article], "EXACT_OPTION", "GUIDED_EXTENSION", True),
            ("U01-PF32-SPEAK-VERY-ADJ-NOUN", f"Say the guided phrase for one very {adjective} {noun}.", f"very {adjective} {noun}", [], None, [phrase], "FEATURE_RUBRIC", "GUIDED_EXTENSION", False),
            ("U01-PF33-SPEAK-I-SEE-VERY-ADJ-NOUN", f"Say a guided sentence about one very {adjective} {noun}.", f"very {adjective} {noun}", [], None, [f"I can see {phrase}."], "FEATURE_RUBRIC", "GUIDED_EXTENSION", True),
        ]
        for fid, prompt, stimulus, options, answer, accepted, mode, support, transfer in rows:
            items.append(
                make_item(
                    family_id=fid,
                    token=token,
                    prompt=prompt,
                    stimulus=stimulus,
                    options=options,
                    correct_answer=answer,
                    accepted_answers=accepted,
                    target_evp_sense_ids=senses,
                    target_egp_row_ids=egp,
                    target_pattern_id=PATTERN_VERY,
                    scoring_mode=mode,
                    support_level=support,
                    transfer_eligible=transfer,
                )
            )
    return items

def expansion_items() -> list[dict[str, Any]]:
    items = noun_expansion_items() + adjective_expansion_items() + very_expansion_items()
    items.sort(key=lambda row: row["item_id"])
    if len(items) != EXPECTED_EXPANSION_COUNT:
        raise FullVariantPoolBuildError(f"EXPANSION_COUNT_INVALID:{len(items)}")
    return items

def build_items() -> list[dict[str, Any]]:
    seed_items = seed.build_items()
    if len(seed_items) != EXPECTED_SEED_COUNT:
        raise FullVariantPoolBuildError(f"SEED_COUNT_INVALID:{len(seed_items)}")
    items = [deepcopy(row) for row in seed_items] + expansion_items()
    items.sort(key=lambda row: row["item_id"])
    ids = [row["item_id"] for row in items]
    signatures = [row["semantic_signature"] for row in items]
    if len(items) != EXPECTED_ITEM_COUNT:
        raise FullVariantPoolBuildError(f"ITEM_COUNT_INVALID:{len(items)}")
    if len(ids) != len(set(ids)):
        raise FullVariantPoolBuildError("DUPLICATE_ITEM_ID")
    if len(signatures) != len(set(signatures)):
        raise FullVariantPoolBuildError("DUPLICATE_SEMANTIC_SIGNATURE")
    return items

def design_space_capacity() -> dict[str, Any]:
    return {
        "theoretical_raw_combinatorial_capacity": RAW_COMBINATORIAL_CAPACITY,
        "seed_authority_grounded_count": EXPECTED_SEED_COUNT,
        "expansion_authority_grounded_count": EXPECTED_EXPANSION_COUNT,
        "authority_grounded_candidate_count": EXPECTED_ITEM_COUNT,
        "theoretical_candidates_not_admitted_without_additional_authority": RAW_COMBINATORIAL_CAPACITY - EXPECTED_ITEM_COUNT,
        "approved_direct_adjective_phrase_count": len(seed.direct_adjective_phrases()),
        "approved_very_adjective_phrase_count": len(seed.very_adjective_phrases()),
        "excluded_space_reason": "NO_APPROVED_ADJECTIVE_NOUN_COMPATIBILITY_MATRIX_OR_CONTEXT_REALIZATION_AUTHORITY",
    }

def candidate_payload() -> dict[str, Any]:
    items = build_items()
    family_counts = dict(sorted(Counter(row["pattern_family_id"] for row in items).items()))
    skill_counts = dict(sorted(Counter(row["skill"] for row in items).items()))
    type_counts = dict(sorted(Counter(row["question_type"] for row in items).items()))
    pattern_counts = dict(sorted(Counter(pattern for row in items for pattern in row["unit_pattern_ids"]).items()))
    evp = sorted({sense for row in items for sense in row["target_evp_sense_ids"]})
    egp = sorted({target for row in items for target in row["target_egp_row_ids"]})
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
        "source_seed_contract": {
            "seed_task_id": seed.TASK_ID,
            "seed_bank_version": seed.BANK_VERSION,
            "seed_item_count": EXPECTED_SEED_COUNT,
            "seed_is_runtime_authority": False,
            "full_v2_bank_is_runtime_candidate_authority": True,
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
            "question_type": type_counts,
            "unit_pattern": pattern_counts,
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
            "pool_source": "APPROVED_FULL_V2_VARIANTS_ONLY",
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
    return policy_artifact.build_candidate(
        payload=candidate_payload(),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "seed_task_id": seed.TASK_ID,
            "seed_item_count": EXPECTED_SEED_COUNT,
            "unit01_approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "u01data05b_task_id": seed.pattern_authority.TASK_ID,
            "unit_local_pattern_ids": [PATTERN_NOUN, PATTERN_ADJECTIVE, PATTERN_VERY],
            "baseline_activity_count": BASELINE_ACTIVITY_COUNT,
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "operator_decision_ref": DECISION_REF,
        },
    )

def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool_full as validator,
    )
    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )

def materialize(*, candidate_path: Path, approved_path: Path, report_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import (
        validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool_full as validator,
    )
    report = validator.validate_approved(candidate, approved)
    if report["error_count"]:
        raise FullVariantPoolBuildError("APPROVED_VALIDATION_FAILED:" + "|".join(report["errors"]))
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
        FullVariantPoolBuildError,
        policy_artifact.ContentPolicyBuildError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL_FULL_V2")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"APPROVED_VARIANT_COUNT={len(payload['candidate_items'])}")
    print(f"PATTERN_FAMILY_COUNT={len(payload['pattern_family_contracts'])}")
    print(f"SEED_VARIANT_COUNT={payload['design_space_capacity']['seed_authority_grounded_count']}")
    print(f"EXPANSION_VARIANT_COUNT={payload['design_space_capacity']['expansion_authority_grounded_count']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
