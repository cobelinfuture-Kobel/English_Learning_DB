#!/usr/bin/env python3
"""Materialize Unit02 QuestionBank capacity gaps and prove per-slot distinct capacity."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as u01_contract
from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as u02qb02,
)
from ulga.builders import (
    build_a1fs_v1_u02qbc01_unit02_questionbank_distinct_capacity_denominator as qbc01,
)
from ulga.builders import (
    build_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck
    as u02sc04,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02QBC02_Unit02QuestionBankGapMaterializationAndPerSlotDistinctCapacityProof"
SCHEMA_VERSION = "a1fs.v1.u02qbc02.questionbank_gap_materialization_per_slot_capacity.v1"
PASS_STATUS = "PASS_A1FS_V1_U02QBC02_UNIT02_QUESTIONBANK_GAP_MATERIALIZATION_AND_PER_SLOT_DISTINCT_CAPACITY_PROOF"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-23:U02QBC02"
UNIT_ID = u02qb02.UNIT_ID
LEVEL_SCOPE = ["A1"]

FORM_COUNT = 16
SCENE_SLOTS_PER_FORM = 4
TASK_FAMILIES = tuple(qbc01.u02ta01.TASK_FAMILIES)
ACTIVITIES_PER_FORM = SCENE_SLOTS_PER_FORM * len(TASK_FAMILIES)
TOTAL_SLOTS = FORM_COUNT * ACTIVITIES_PER_FORM
MIN_CANDIDATES_PER_SLOT = 3
EXPECTED_BINDINGS = TOTAL_SLOTS * MIN_CANDIDATES_PER_SLOT
GAP_ITEMS_PER_FAMILY = 48

BASE_SUPPORTED_TASK_FAMILIES = (
    "RECOGNITION",
    "FORM_SELECTION",
    "MORPHOLOGY_CONSTRUCTION",
)
MATERIALIZED_TASK_FAMILIES = (
    "MEANING_DISCRIMINATION",
    "ERROR_DETECTION",
    "ERROR_CORRECTION",
    "CONTEXT_GAP",
    "U01_U02_INTEGRATION",
    "PRODUCTIVE_RESPONSE",
    "TRANSFER",
)
EXPECTED_NEW_ITEMS = len(MATERIALIZED_TASK_FAMILIES) * GAP_ITEMS_PER_FAMILY
EXPECTED_BASE_U02_ITEMS = 658
EXPECTED_UNIT02_APPROVED_ITEMS = EXPECTED_BASE_U02_ITEMS + EXPECTED_NEW_ITEMS
EXPECTED_UNIT01_REUSABLE_ITEMS = 474
EXPECTED_CUMULATIVE_ITEMS = EXPECTED_UNIT01_REUSABLE_ITEMS + EXPECTED_UNIT02_APPROVED_ITEMS

NEXT_SHORT_STEP = "A1FS-V1-U02QB03_Unit02CumulativeQuestionBankRuntimeIntegration"
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_QBC02_SCOPE"

QUESTION_TYPE_BY_FAMILY = {
    "MEANING_DISCRIMINATION": "multiple_choice",
    "ERROR_DETECTION": "multiple_choice",
    "ERROR_CORRECTION": "gap_fill",
    "CONTEXT_GAP": "gap_fill",
    "U01_U02_INTEGRATION": "gap_fill",
    "PRODUCTIVE_RESPONSE": "gap_fill",
    "TRANSFER": "gap_fill",
}


class Unit02QBC02BuildError(ValueError):
    pass


def _base_approved_payload() -> dict[str, Any]:
    approved = u02qb02.admit_candidate(u02qb02.build_candidate())
    payload = approved.get("payload", {})
    rows = payload.get("approved_items", [])
    if len(rows) != EXPECTED_BASE_U02_ITEMS:
        raise Unit02QBC02BuildError(f"BASE_U02_COUNT_DRIFT:{len(rows)}")
    if payload.get("bank_identity", {}).get("unit01_runtime_base_item_count") != EXPECTED_UNIT01_REUSABLE_ITEMS:
        raise Unit02QBC02BuildError("UNIT01_BASE_COUNT_DRIFT")
    return payload


def _source_context_rows() -> list[dict[str, Any]]:
    rows = sorted(
        u02sc04.materialized_rows(),
        key=lambda row: (str(row["target_singular"]), str(row["materialization_id"])),
    )
    if len(rows) < GAP_ITEMS_PER_FAMILY:
        raise Unit02QBC02BuildError(f"INSUFFICIENT_CONTEXT_ROWS:{len(rows)}")
    inventory = u02qb02.inventory_by_singular()
    selected = []
    for row in rows:
        singular = str(row["target_singular"])
        if singular not in inventory:
            continue
        if str(row["target_plural"]) != str(inventory[singular]["plural"]):
            raise Unit02QBC02BuildError(f"CONTEXT_PLURAL_DRIFT:{singular}")
        selected.append(deepcopy(row))
        if len(selected) == GAP_ITEMS_PER_FAMILY:
            break
    if len(selected) != GAP_ITEMS_PER_FAMILY:
        raise Unit02QBC02BuildError(f"CONTEXT_SELECTION_COUNT_INVALID:{len(selected)}")
    return selected


def _response_contract(scoring_mode: str, correct_answer: str) -> dict[str, Any]:
    return {
        "scoring_mode": scoring_mode,
        "response_type": "string",
        "accepted_texts": [correct_answer],
        "accepted_sequence": [],
        "capture_enabled": True,
        "human_review_fallback": False,
    }


def _item_shape(task_family: str, row: Mapping[str, Any]) -> dict[str, Any]:
    singular = str(row["target_singular"])
    plural = str(row["target_plural"])
    setting = str(row["scene_semantic_core"]["setting_code"]).replace("_", " ").lower()
    vocab_ids = list(row.get("vocabulary_ids") or [])
    common_prereq = [u02qb02.PREREQUISITE_KP009]
    grammar_targets = ["REGULAR_PLURAL_NOUNS"]
    prerequisite_rows = list(common_prereq)

    if task_family == "MEANING_DISCRIMINATION":
        prompt = "Choose the phrase that matches the scene."
        stimulus = f"At the {setting}, you can see more than one {singular}."
        options = [f"two {plural}", f"one {singular}"]
        correct = f"two {plural}"
        scoring = "EXACT_OPTION"
    elif task_family == "ERROR_DETECTION":
        prompt = "Choose the phrase with a plural error."
        stimulus = f"At the {setting}."
        options = [f"two {singular}", f"two {plural}"]
        correct = f"two {singular}"
        scoring = "EXACT_OPTION"
    elif task_family == "ERROR_CORRECTION":
        prompt = "Correct the plural phrase."
        stimulus = f"two {singular}"
        options = []
        correct = f"two {plural}"
        scoring = "NORMALIZED_TEXT"
    elif task_family == "CONTEXT_GAP":
        prompt = "Complete the phrase for the scene."
        stimulus = f"At the {setting}: two ___."
        options = []
        correct = plural
        scoring = "NORMALIZED_TEXT"
    elif task_family == "U01_U02_INTEGRATION":
        prompt = "Change the known singular noun phrase to a plural noun phrase."
        stimulus = f"the {singular} -> the ___"
        options = []
        correct = f"the {plural}"
        scoring = "NORMALIZED_TEXT"
        grammar_targets = ["GRAMMAR_ARTICLES_BASIC", "REGULAR_PLURAL_NOUNS"]
        prerequisite_rows = sorted(set(common_prereq + list(u01_contract.CORE_EGP_ROWS)))
    elif task_family == "PRODUCTIVE_RESPONSE":
        prompt = "Write the sentence about the scene."
        stimulus = f"At the {setting}: two {plural} are visible."
        options = []
        correct = f"I can see two {plural}."
        scoring = "NORMALIZED_TEXT"
    elif task_family == "TRANSFER":
        prompt = "Complete the sentence in the new context."
        stimulus = f"New context - {setting}: I can see two ___."
        options = []
        correct = plural
        scoring = "NORMALIZED_TEXT"
    else:
        raise Unit02QBC02BuildError(f"UNKNOWN_MATERIALIZED_FAMILY:{task_family}")

    lexical_slots = {
        "singular_noun": singular,
        "plural_noun": plural,
        "determiner": "two",
        "context_setting": setting,
    }
    item_id = f"U02QBC02-{task_family}-{u02qb02.slug(singular)}"
    item = {
        "item_id": item_id,
        "unit_id": UNIT_ID,
        "task_family": task_family,
        "pattern_family_id": f"U02-QBC02-{task_family}",
        "lexical_slots": lexical_slots,
        "unit_pattern_ids": [u02qb02.DIRECT_PATTERN_ID],
        "grammar_target_ids": grammar_targets,
        "target_egp_row_ids": [u02qb02.KP014],
        "prerequisite_egp_row_ids": prerequisite_rows,
        "target_evp_sense_ids": sorted(set(vocab_ids)),
        "skill": "READING" if scoring == "EXACT_OPTION" else "WRITING",
        "question_type": QUESTION_TYPE_BY_FAMILY[task_family],
        "prompt": prompt,
        "stimulus": stimulus,
        "options": options,
        "correct_answer": correct,
        "accepted_answers": [correct],
        "scoring_mode": scoring,
        "support_level": "CAPACITY_NEUTRAL",
        "learner_visible_capable": True,
        "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
        "assessment_eligible": True,
        "transfer_eligible": task_family == "TRANSFER",
        "reassessment_eligible": True,
        "human_review_required": False,
        "audio_required": False,
        "speaking_capture_enabled": False,
        "runtime_generation_used": False,
        "source_scene_materialization_id": row["materialization_id"],
        "canonical_scene_ref_id": None,
        "scene_authority_claimed": False,
        "admission_proposal": {
            "status": "AUTO_APPROVED",
            "reason_codes": [
                "U02QBC02_SOURCE_BOUND_GAP_MATERIALIZATION",
                f"TASK_FAMILY_{task_family}",
            ],
        },
        "source_refs": [
            {"source_type": "U02QB02_APPROVED_POOL", "task_id": u02qb02.TASK_ID},
            {"source_type": "U02QBC01_CAPACITY_DENOMINATOR", "task_id": qbc01.TASK_ID},
            {
                "source_type": "U02SC04_STRUCTURAL_CONTEXT_EVIDENCE",
                "task_id": u02sc04.TASK_ID,
                "materialization_id": row["materialization_id"],
                "canonical_scene_authority": False,
            },
        ],
    }
    item["response_contract"] = _response_contract(scoring, correct)
    item["semantic_signature"] = policy_artifact.digest(
        {
            "task_family": task_family,
            "lexical_slots": lexical_slots,
            "prompt": prompt,
            "stimulus": stimulus,
            "options": options,
            "correct_answer": correct,
        }
    )
    return item


def materialized_gap_items() -> list[dict[str, Any]]:
    contexts = _source_context_rows()
    rows = [
        _item_shape(task_family, context)
        for task_family in MATERIALIZED_TASK_FAMILIES
        for context in contexts
    ]
    rows.sort(key=lambda row: row["item_id"])
    if len(rows) != EXPECTED_NEW_ITEMS:
        raise Unit02QBC02BuildError(f"NEW_ITEM_COUNT_INVALID:{len(rows)}")
    if len({row["item_id"] for row in rows}) != len(rows):
        raise Unit02QBC02BuildError("DUPLICATE_NEW_ITEM_ID")
    if len({row["semantic_signature"] for row in rows}) != len(rows):
        raise Unit02QBC02BuildError("DUPLICATE_NEW_SEMANTIC_SIGNATURE")
    return rows


def _base_pool_ids(base_items: Sequence[Mapping[str, Any]], task_family: str) -> list[str]:
    if task_family in {"RECOGNITION", "FORM_SELECTION"}:
        family_ids = {"U02-PF02-PLURAL-FORM-CHOICE"}
    elif task_family == "MORPHOLOGY_CONSTRUCTION":
        family_ids = {
            "U02-PF01-PLURAL-FORM-PRODUCTION",
            "U02-PF05-NUMBER-PLURAL-NOUN",
        }
    else:
        return []
    return sorted(
        str(row["item_id"])
        for row in base_items
        if str(row["pattern_family_id"]) in family_ids
        and row.get("learner_visible_capable") is True
    )


def task_family_pools(
    base_items: Sequence[Mapping[str, Any]],
    new_items: Sequence[Mapping[str, Any]],
) -> dict[str, list[str]]:
    new_by_family = {
        family: sorted(
            str(row["item_id"])
            for row in new_items
            if row["task_family"] == family
        )
        for family in MATERIALIZED_TASK_FAMILIES
    }
    pools: dict[str, list[str]] = {}
    for family in TASK_FAMILIES:
        ids = _base_pool_ids(base_items, family)
        if not ids:
            ids = new_by_family.get(family, [])
        if len(ids) < GAP_ITEMS_PER_FAMILY:
            raise Unit02QBC02BuildError(f"TASK_FAMILY_POOL_TOO_SMALL:{family}:{len(ids)}")
        pools[family] = ids
    return pools


def progression_stage(form_number: int) -> str:
    if form_number <= 4:
        return "GUIDED"
    if form_number <= 8:
        return "REDUCED_SUPPORT"
    if form_number <= 12:
        return "INDEPENDENT"
    return "TRANSFER"


def capacity_slot_matrix(pools: Mapping[str, Sequence[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for form_number in range(1, FORM_COUNT + 1):
        for scene_slot in range(1, SCENE_SLOTS_PER_FORM + 1):
            for task_index, task_family in enumerate(TASK_FAMILIES, start=1):
                pool = list(pools[task_family])
                offset = ((form_number - 1) * 12 + (scene_slot - 1) * 3) % len(pool)
                candidate_ids = [pool[(offset + i) % len(pool)] for i in range(3)]
                if len(set(candidate_ids)) != MIN_CANDIDATES_PER_SLOT:
                    raise Unit02QBC02BuildError(
                        f"SLOT_CANDIDATE_NOT_DISTINCT:F{form_number}:S{scene_slot}:{task_family}"
                    )
                rows.append(
                    {
                        "slot_id": f"U02-F{form_number:02d}-S{scene_slot:02d}-T{task_index:02d}",
                        "form_number": form_number,
                        "progression_stage": progression_stage(form_number),
                        "scene_slot_ordinal": scene_slot,
                        "canonical_scene_bound": False,
                        "task_family": task_family,
                        "candidate_ids": candidate_ids,
                        "legal_candidate_count": len(candidate_ids),
                        "learner_visible_distinct_candidates": True,
                        "runtime_selection_materialized": False,
                    }
                )
    if len(rows) != TOTAL_SLOTS:
        raise Unit02QBC02BuildError(f"SLOT_COUNT_INVALID:{len(rows)}")
    if sum(len(row["candidate_ids"]) for row in rows) != EXPECTED_BINDINGS:
        raise Unit02QBC02BuildError("BINDING_COUNT_INVALID")

    for form_number in range(1, FORM_COUNT + 1):
        for task_family in TASK_FAMILIES:
            ids = [
                candidate_id
                for row in rows
                if row["form_number"] == form_number and row["task_family"] == task_family
                for candidate_id in row["candidate_ids"]
            ]
            if len(ids) != 12 or len(set(ids)) != 12:
                raise Unit02QBC02BuildError(
                    f"WITHIN_FORM_FAMILY_REUSE_DETECTED:F{form_number}:{task_family}"
                )
    return rows


def payload() -> dict[str, Any]:
    q10 = qbc01.payload()
    if q10.get("capacity_verdict", {}).get("distinct_capacity_status") != "NOT_PROVEN":
        raise Unit02QBC02BuildError("QBC01_EXPECTED_NOT_PROVEN_DRIFT")
    base_payload = _base_approved_payload()
    base_items = list(base_payload["approved_items"])
    new_items = materialized_gap_items()
    pools = task_family_pools(base_items, new_items)
    matrix = capacity_slot_matrix(pools)

    unit02_count = len(base_items) + len(new_items)
    cumulative_count = EXPECTED_UNIT01_REUSABLE_ITEMS + unit02_count
    if unit02_count != EXPECTED_UNIT02_APPROVED_ITEMS:
        raise Unit02QBC02BuildError(f"UNIT02_APPROVED_COUNT_INVALID:{unit02_count}")
    if cumulative_count != EXPECTED_CUMULATIVE_ITEMS:
        raise Unit02QBC02BuildError(f"CUMULATIVE_COUNT_INVALID:{cumulative_count}")

    pool_counts = {family: len(ids) for family, ids in pools.items()}
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "source_authority": {
            "qbc01_task_id": qbc01.TASK_ID,
            "u02qb02_task_id": u02qb02.TASK_ID,
            "u02sc04_task_id": u02sc04.TASK_ID,
            "unit01_content_contract_task_id": u01_contract.TASK_ID,
        },
        "questionbank_inventory": {
            "unit01_reusable_runtime_items": EXPECTED_UNIT01_REUSABLE_ITEMS,
            "unit02_existing_approved_items": len(base_items),
            "unit02_new_gap_materialized_items": len(new_items),
            "unit02_approved_items_after_qbc02": unit02_count,
            "cumulative_approved_items_after_qbc02": cumulative_count,
            "parallel_questionbank_created": False,
            "runtime_status": "NOT_CONNECTED",
        },
        "materialization_contract": {
            "base_supported_task_families": list(BASE_SUPPORTED_TASK_FAMILIES),
            "materialized_task_families": list(MATERIALIZED_TASK_FAMILIES),
            "items_per_materialized_family": GAP_ITEMS_PER_FAMILY,
            "new_item_count": len(new_items),
            "source_context_candidate_count": GAP_ITEMS_PER_FAMILY,
            "structural_scene_evidence_not_promoted_to_canonical_scene": True,
        },
        "new_approved_items": new_items,
        "task_family_pool_counts": pool_counts,
        "task_family_pools": pools,
        "capacity_model": {
            "form_count": FORM_COUNT,
            "scene_slots_per_form": SCENE_SLOTS_PER_FORM,
            "task_family_count": len(TASK_FAMILIES),
            "activities_per_form": ACTIVITIES_PER_FORM,
            "total_capacity_slots": TOTAL_SLOTS,
            "minimum_candidates_per_slot": MIN_CANDIDATES_PER_SLOT,
            "slot_candidate_binding_count": EXPECTED_BINDINGS,
            "all_ten_task_families_have_at_least_48_candidates": all(
                count >= GAP_ITEMS_PER_FAMILY for count in pool_counts.values()
            ),
        },
        "capacity_slot_matrix": matrix,
        "capacity_verdict": {
            "q9_hard_gaps_materialized": True,
            "q9_partial_families_reconciled": True,
            "practice_only_full_families_reconciled_into_questionbank_capacity": [
                "MEANING_DISCRIMINATION",
                "PRODUCTIVE_RESPONSE",
            ],
            "exact_slot_candidate_matrix_materialized": True,
            "all_640_slots_have_at_least_3_legal_candidates": True,
            "all_slot_candidate_sets_are_learner_visible_distinct": True,
            "within_form_same_task_family_candidate_reuse": False,
            "distinct_capacity_status": "PROVEN",
            "unit02_640_slot_capacity_closed": True,
        },
        "claim_boundaries": {
            "unit01_questionbank_mutated": False,
            "parallel_questionbank_created": False,
            "unit02_runtime_connected": False,
            "final_forms_materialized": False,
            "learner_sessions_materialized": False,
            "canonical_scene_authority_mutated": False,
            "learner_state_mutated": False,
            "a2_unlocked": False,
        },
        "next_scope": {
            "scope_status": NEXT_SCOPE_STATUS,
            "next_short_step": NEXT_SHORT_STEP,
            "requires_runtime_integration": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate() -> dict[str, Any]:
    value = payload()
    return policy_artifact.build_candidate(
        payload=value,
        producer_id=TASK_ID,
        level_scope=LEVEL_SCOPE,
        source_bindings={
            "qbc01_task_id": qbc01.TASK_ID,
            "u02qb02_task_id": u02qb02.TASK_ID,
            "u02sc04_task_id": u02sc04.TASK_ID,
            "unit02_new_gap_item_count": EXPECTED_NEW_ITEMS,
            "unit02_total_approved_item_count": EXPECTED_UNIT02_APPROVED_ITEMS,
            "cumulative_approved_item_count": EXPECTED_CUMULATIVE_ITEMS,
            "capacity_slot_count": TOTAL_SLOTS,
            "minimum_candidates_per_slot": MIN_CANDIDATES_PER_SLOT,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
        as validator,
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
    payload_value = approved["payload"]
    verdict = payload_value["capacity_verdict"]
    print(f"STATUS={PASS_STATUS}")
    print(f"NEW_GAP_ITEMS={len(payload_value['new_approved_items'])}")
    print(
        "UNIT02_APPROVED_ITEMS="
        f"{payload_value['questionbank_inventory']['unit02_approved_items_after_qbc02']}"
    )
    print(
        "CUMULATIVE_APPROVED_ITEMS="
        f"{payload_value['questionbank_inventory']['cumulative_approved_items_after_qbc02']}"
    )
    print(f"CAPACITY_SLOTS={payload_value['capacity_model']['total_capacity_slots']}")
    print(f"SLOT_CANDIDATE_BINDINGS={payload_value['capacity_model']['slot_candidate_binding_count']}")
    print(f"DISTINCT_CAPACITY_STATUS={verdict['distinct_capacity_status']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
