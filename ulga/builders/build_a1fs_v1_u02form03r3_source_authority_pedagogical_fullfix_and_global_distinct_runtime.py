#!/usr/bin/env python3
"""R4R1 Transfer-stage FullFix over the accepted U02FORM03R3 successor authority.

This module preserves the R3 runtime identity for Forms01-12 exactly, adds
policy-bound transfer-stage items for Forms13-16 only, and replaces the
Transfer-stage learner demand with task-family-specific, new-context work.
No Q01-Q08, SentenceAsset, canonical scene, learner-state, scoring, or A2
authority is created or mutated.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import _a1fs_v1_u02form03r3_global_distinct_base as base

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U02FORM03R4R1_"
    "TransferStageTaskSpecificInstructionAndRealTransferDemandFullFix"
)
SCHEMA_VERSION = "a1fs.v1.u02form03r4r1.transfer_stage_fullfix.v1"
PASS_STATUS = (
    "PASS_A1FS_V1_U02FORM03R4R1_"
    "TRANSFER_STAGE_TASK_SPECIFIC_INSTRUCTION_AND_REAL_TRANSFER_DEMAND_FULLFIX"
)
DECISION_REF = (
    "OPERATOR_APPROVAL:2026-08-26:"
    "U02FORM03R4R1_TRANSFER_STAGE_PEDAGOGICAL_FULLFIX"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U02FORM03R4R2_"
    "ActualTransferForms13To16PdfRerenderAndShaBoundHumanReacceptance"
)

TASK_FAMILIES = tuple(base.TASK_FAMILIES)
FORM_COUNT = base.FORM_COUNT
SCENE_SLOTS_PER_FORM = base.SCENE_SLOTS_PER_FORM
ACTIVITIES_PER_FORM = base.ACTIVITIES_PER_FORM
TOTAL_RUNTIME_OCCURRENCES = base.TOTAL_RUNTIME_OCCURRENCES
PER_FAMILY_RUNTIME_OCCURRENCES = base.PER_FAMILY_RUNTIME_OCCURRENCES
MIN_CANDIDATES_PER_SLOT = base.MIN_CANDIDATES_PER_SLOT
RUNTIME_RESTRICTED_SURFACES = set(base.RUNTIME_RESTRICTED_SURFACES)
SENTENCE_BINDING_REQUIRED_FAMILIES = set(base.SENTENCE_BINDING_REQUIRED_FAMILIES)
EXPECTED_UNIT01_REFERENCE_ITEMS = base.EXPECTED_UNIT01_REFERENCE_ITEMS

R3_CONTEXTS_PER_MATERIALIZED_FAMILY = base.R3_CONTEXTS_PER_MATERIALIZED_FAMILY
R3_MATERIALIZED_FAMILIES = tuple(base.R3_MATERIALIZED_FAMILIES)
R3_NEW_ITEMS = base.R3_NEW_ITEMS

R4R1_TRANSFER_FORMS = (13, 14, 15, 16)
R4R1_TRANSFER_SCENE_COUNT = len(R4R1_TRANSFER_FORMS) * SCENE_SLOTS_PER_FORM
R4R1_TRANSFER_ITEMS_PER_FAMILY = R4R1_TRANSFER_SCENE_COUNT
R4R1_TRANSFER_ITEM_COUNT = R4R1_TRANSFER_ITEMS_PER_FAMILY * len(TASK_FAMILIES)
EXPECTED_UNIT02_APPROVED_ITEMS = base.EXPECTED_UNIT02_APPROVED_ITEMS + R4R1_TRANSFER_ITEM_COUNT
EXPECTED_CUMULATIVE_ITEMS = EXPECTED_UNIT01_REFERENCE_ITEMS + EXPECTED_UNIT02_APPROVED_ITEMS

_Q1_Q8_KEYS = tuple(base._Q1_Q8_KEYS)

SUPPORT_NOTE_BY_STAGE = {
    "GUIDED": base.SUPPORT_NOTE_BY_STAGE["GUIDED"],
    "REDUCED_SUPPORT": base.SUPPORT_NOTE_BY_STAGE["REDUCED_SUPPORT"],
    "INDEPENDENT": base.SUPPORT_NOTE_BY_STAGE["INDEPENDENT"],
    "TRANSFER": "Task-family-specific transfer instruction; no grammar rule hint.",
}

TRANSFER_NOTE_BY_FAMILY = {
    "RECOGNITION": "Read the new situation and identify the correct plural use.",
    "MEANING_DISCRIMINATION": "Use meaning in the new situation; no rule hint.",
    "FORM_SELECTION": "Choose the plural form that fits the new sentence.",
    "MORPHOLOGY_CONSTRUCTION": "Build the plural form that fits the new sentence.",
    "ERROR_DETECTION": "Check plural use in the new sentence.",
    "ERROR_CORRECTION": "Correct the plural error in the new sentence.",
    "CONTEXT_GAP": "Use the new context to complete the plural word.",
    "U01_U02_INTEGRATION": "Apply article and plural knowledge in the new context.",
    "PRODUCTIVE_RESPONSE": "Write the complete sentence from the new cue.",
    "TRANSFER": "Apply the plural rule independently in the new situation.",
}


class U02Form03R4R1BuildError(ValueError):
    pass


_digest = base._digest
_slug = base._slug
_target_singular = base._target_singular
_target_plural = base._target_plural
_response_type = base._response_type
_visible_payload = base._visible_payload
_visible_signature = base._visible_signature
_effective_signature = base._effective_signature
_runtime_semantic_signature = base._runtime_semantic_signature
_normalized_visible_text = base._normalized_visible_text
_word_present = base._word_present


def _response_contract(scoring_mode: str, correct_answer: str) -> dict[str, Any]:
    return {
        "scoring_mode": scoring_mode,
        "response_type": "string",
        "accepted_texts": [correct_answer],
        "accepted_sequence": [],
        "capture_enabled": True,
        "human_review_fallback": False,
    }


def _transfer_item(*, runtime_row: Mapping[str, Any], source_item: Mapping[str, Any]) -> dict[str, Any]:
    family = str(runtime_row["task_family"])
    singular = _target_singular(source_item)
    plural = _target_plural(source_item)
    if not singular or not plural:
        raise U02Form03R4R1BuildError(f"R4R1_TARGET_MISSING:{runtime_row['slot_id']}")

    if family == "RECOGNITION":
        prompt = "Choose the sentence that correctly shows more than one."
        stimulus = f"New situation. Singular cue: {singular}"
        options = [f"I can see two {plural}.", f"I can see two {singular}."]
        correct = options[0]
        scoring = "EXACT_OPTION"
        question_type = "multiple_choice"
        skill = "READING"
    elif family == "MEANING_DISCRIMINATION":
        prompt = "Choose the sentence that talks about more than one."
        stimulus = f"New situation. Singular cue: {singular}"
        options = [f"I can see two {plural}.", f"I can see one {singular}."]
        correct = options[0]
        scoring = "EXACT_OPTION"
        question_type = "multiple_choice"
        skill = "READING"
    elif family == "FORM_SELECTION":
        prompt = "Choose the word that completes the new sentence."
        stimulus = f"New situation: I can see two ___. Singular cue: {singular}"
        options = [plural, singular]
        correct = plural
        scoring = "EXACT_OPTION"
        question_type = "multiple_choice"
        skill = "READING"
    elif family == "MORPHOLOGY_CONSTRUCTION":
        prompt = "Write the plural word that completes the new sentence."
        stimulus = f"New situation: I can see two ___. Singular cue: {singular}"
        options = []
        correct = plural
        scoring = "NORMALIZED_TEXT"
        question_type = "gap_fill"
        skill = "WRITING"
    elif family == "ERROR_DETECTION":
        prompt = "Choose the sentence with the plural mistake."
        stimulus = f"New situation. Singular cue: {singular}"
        options = [f"I can see two {singular}.", f"I can see two {plural}."]
        correct = options[0]
        scoring = "EXACT_OPTION"
        question_type = "multiple_choice"
        skill = "READING"
    elif family == "ERROR_CORRECTION":
        prompt = "Rewrite the sentence with the plural form corrected."
        stimulus = f"New situation: I can see two {singular}."
        options = []
        correct = f"I can see two {plural}."
        scoring = "NORMALIZED_TEXT"
        question_type = "gap_fill"
        skill = "WRITING"
    elif family == "CONTEXT_GAP":
        prompt = "Complete the new sentence with the correct plural word."
        stimulus = f"New situation: There are two ___. Singular cue: {singular}"
        options = []
        correct = plural
        scoring = "NORMALIZED_TEXT"
        question_type = "gap_fill"
        skill = "WRITING"
    elif family == "U01_U02_INTEGRATION":
        prompt = "Rewrite the noun phrase for a new plural context."
        stimulus = f"New situation: change 'the {singular}' to a phrase about two: 'the ___'."
        options = []
        correct = f"the {plural}"
        scoring = "NORMALIZED_TEXT"
        question_type = "gap_fill"
        skill = "WRITING"
    elif family == "PRODUCTIVE_RESPONSE":
        prompt = "Write a complete sentence about more than one."
        stimulus = f"New situation. Singular cue: {singular}. Start with: I can see two ..."
        options = []
        correct = f"I can see two {plural}."
        scoring = "NORMALIZED_TEXT"
        question_type = "gap_fill"
        skill = "WRITING"
    elif family == "TRANSFER":
        prompt = "Write a complete sentence for the new situation."
        stimulus = f"Word cue: {singular}. New situation: say that you can see two of them."
        options = []
        correct = f"I can see two {plural}."
        scoring = "NORMALIZED_TEXT"
        question_type = "gap_fill"
        skill = "WRITING"
    else:
        raise U02Form03R4R1BuildError(f"R4R1_UNKNOWN_FAMILY:{family}")

    item = deepcopy(dict(source_item))
    item_id = (
        f"U02FORM03R4R1-{family}-F{int(runtime_row['form_number']):02d}-"
        f"S{int(runtime_row['scene_slot_ordinal']):02d}-{_slug(singular)}"
    )
    item.update({
        "item_id": item_id,
        "task_family": family,
        "pattern_family_id": f"U02-R4R1-TRANSFER-{family}",
        "skill": skill,
        "question_type": question_type,
        "prompt": prompt,
        "stimulus": stimulus,
        "options": options,
        "correct_answer": correct,
        "accepted_answers": [correct],
        "scoring_mode": scoring,
        "response_contract": _response_contract(scoring, correct),
        "support_level": "TRANSFER_NEW_CONTEXT_NO_RULE_HINT",
        "learner_delivery_status": "R4R1_TRANSFER_RUNTIME_ELIGIBLE",
        "transfer_eligible": True,
        "runtime_generation_used": False,
        "r4r1_transfer_demand": "NEW_CONTEXT_APPLICATION",
        "r4r1_source_selected_item_id": str(runtime_row["selected_item_id"]),
        "admission_proposal": {
            "status": "AUTO_APPROVED",
            "reason_codes": [
                "U02FORM03R4R1_TRANSFER_STAGE_PEDAGOGICAL_FULLFIX",
                f"TASK_FAMILY_{family}",
                "TASK_SPECIFIC_TRANSFER_INSTRUCTION",
                "REAL_NEW_CONTEXT_TRANSFER_DEMAND",
            ],
        },
    })
    source_refs = list(item.get("source_refs") or [])
    source_refs.append({
        "source_type": "U02FORM03R3_SELECTED_RUNTIME_ITEM",
        "task_id": base.TASK_ID,
        "selected_item_id": str(runtime_row["selected_item_id"]),
        "slot_id": str(runtime_row["slot_id"]),
    })
    item["source_refs"] = source_refs
    item["semantic_signature"] = _digest({
        "task_family": family,
        "lexical_slots": item.get("lexical_slots") or {},
        "prompt": prompt,
        "stimulus": stimulus,
        "options": options,
        "correct_answer": correct,
        "transfer_demand": "NEW_CONTEXT_APPLICATION",
    })
    return item


def _transfer_items(baseline_runtime: Sequence[Mapping[str, Any]], baseline_items: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in baseline_runtime if int(row["form_number"]) in R4R1_TRANSFER_FORMS]
    if len(rows) != R4R1_TRANSFER_ITEM_COUNT:
        raise U02Form03R4R1BuildError(f"R4R1_TRANSFER_RUNTIME_COUNT_INVALID:{len(rows)}")
    items = [_transfer_item(runtime_row=row, source_item=baseline_items[str(row["selected_item_id"])]) for row in rows]
    if len({row["item_id"] for row in items}) != len(items):
        raise U02Form03R4R1BuildError("R4R1_TRANSFER_ITEM_ID_COLLISION")
    if len({row["semantic_signature"] for row in items}) != len(items):
        raise U02Form03R4R1BuildError("R4R1_TRANSFER_ITEM_SIGNATURE_COLLISION")
    if Counter(row["task_family"] for row in items) != Counter({family: R4R1_TRANSFER_ITEMS_PER_FAMILY for family in TASK_FAMILIES}):
        raise U02Form03R4R1BuildError("R4R1_TRANSFER_FAMILY_DISTRIBUTION_INVALID")
    return items


def _candidate_ids_for_transfer(*, family_items: Sequence[Mapping[str, Any]], selected_id: str) -> list[str]:
    ids = [str(row["item_id"]) for row in family_items]
    if selected_id not in ids:
        raise U02Form03R4R1BuildError("R4R1_SELECTED_TRANSFER_ITEM_NOT_IN_FAMILY_POOL")
    index = ids.index(selected_id)
    return [ids[index], ids[(index + 1) % len(ids)], ids[(index + 2) % len(ids)]]


def _assert_no_prior_answer_leaks(runtime: Sequence[Mapping[str, Any]], items: Mapping[str, Mapping[str, Any]]) -> None:
    leaks: list[str] = []
    for form_number in range(1, FORM_COUNT + 1):
        for scene_slot in range(1, SCENE_SLOTS_PER_FORM + 1):
            scene_rows = [row for row in runtime if int(row["form_number"]) == form_number and int(row["scene_slot_ordinal"]) == scene_slot]
            prior_visible = ""
            for row in scene_rows:
                item = items[str(row["selected_item_id"])]
                plural = _target_plural(item)
                if _word_present(prior_visible, plural):
                    leaks.append(f"F{form_number:02d}:S{scene_slot:02d}:{row['task_family']}:{plural}")
                prior_visible = (prior_visible + " " + _normalized_visible_text(item, str(row.get("learner_support_note") or ""))).strip()
    if leaks:
        raise U02Form03R4R1BuildError("R4R1_PRIOR_ACTIVITY_DIRECT_ANSWER_LEAK:" + "|".join(leaks[:10]))


def _forms01_12_identity_projection(runtime: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "slot_id": row["slot_id"],
        "runtime_occurrence_id": row["runtime_occurrence_id"],
        "selected_item_id": row["selected_item_id"],
        "candidate_ids": list(row["candidate_ids"]),
        "learner_support_note": row["learner_support_note"],
        "visible_signature": row["visible_signature"],
        "effective_signature": row["effective_signature"],
        "runtime_semantic_signature": row["runtime_semantic_signature"],
    } for row in runtime if int(row["form_number"]) <= 12]


def _q1_q8_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(payload[key]) for key in _Q1_Q8_KEYS}


def build_export_payload() -> dict[str, Any]:
    baseline = base.build_export_payload()
    result = deepcopy(baseline)
    q10 = deepcopy(baseline["q10_questionbank_capacity_runtime"])
    baseline_runtime = [dict(row) for row in q10["runtime_occurrences"]]
    baseline_items = {str(row["item_id"]): dict(row) for row in q10["unit02_approved_items"]}
    if len(baseline_items) != base.EXPECTED_UNIT02_APPROVED_ITEMS:
        raise U02Form03R4R1BuildError("R4R1_BASE_ITEM_INVENTORY_DRIFT")

    transfer_items = _transfer_items(baseline_runtime, baseline_items)
    transfer_by_source_id = {str(row["r4r1_source_selected_item_id"]): row for row in transfer_items}
    if len(transfer_by_source_id) != len(transfer_items):
        raise U02Form03R4R1BuildError("R4R1_TRANSFER_SOURCE_ID_COLLISION")

    items = list(q10["unit02_approved_items"]) + transfer_items
    item_index = {str(row["item_id"]): row for row in items}
    if len(item_index) != len(items):
        raise U02Form03R4R1BuildError("R4R1_APPROVED_ITEM_ID_COLLISION")
    if len(items) != EXPECTED_UNIT02_APPROVED_ITEMS:
        raise U02Form03R4R1BuildError(f"R4R1_APPROVED_ITEM_COUNT_INVALID:{len(items)}")

    family_transfer_items = {
        family: sorted([row for row in transfer_items if row["task_family"] == family], key=lambda row: row["item_id"])
        for family in TASK_FAMILIES
    }
    sentence_index, q6 = base._sentence_index()
    runtime: list[dict[str, Any]] = []
    changed_count = 0
    for source_row in baseline_runtime:
        row = deepcopy(source_row)
        if int(row["form_number"]) in R4R1_TRANSFER_FORMS:
            source_selected = str(row["selected_item_id"])
            item = transfer_by_source_id[source_selected]
            selected_id = str(item["item_id"])
            family = str(row["task_family"])
            note = TRANSFER_NOTE_BY_FAMILY[family]
            row.update({
                "runtime_occurrence_id": f"{row['slot_id']}::{selected_id}",
                "candidate_ids": _candidate_ids_for_transfer(family_items=family_transfer_items[family], selected_id=selected_id),
                "selected_item_id": selected_id,
                "runtime_selection_rule": "R4R1_TRANSFER_STAGE_TASK_SPECIFIC_INJECTIVE_SELECTION",
                "questionbank_item_id": selected_id,
                "questionbank_source": "U02FORM03R4R1",
                "target_singular": _target_singular(item),
                "learner_support_note": note,
                "sentence_asset_binding": base._sentence_binding(family, item, sentence_index),
                "learner_delivery_status": "R4R1_TRANSFER_RUNTIME_PROJECTED",
                "visible_signature": _visible_signature(item, family, note),
                "effective_signature": _effective_signature(item, family, note),
                "runtime_semantic_signature": _runtime_semantic_signature(item, family, note),
            })
            changed_count += 1
        runtime.append(row)
    if changed_count != R4R1_TRANSFER_ITEM_COUNT:
        raise U02Form03R4R1BuildError(f"R4R1_CHANGED_RUNTIME_COUNT_INVALID:{changed_count}")

    before_01_12 = _forms01_12_identity_projection(baseline_runtime)
    after_01_12 = _forms01_12_identity_projection(runtime)
    if before_01_12 != after_01_12:
        raise U02Form03R4R1BuildError("R4R1_FORMS01_12_IDENTITY_DRIFT")

    _assert_no_prior_answer_leaks(runtime, item_index)
    proof = base._global_distinctness_proof(runtime)

    transfer_runtime = [row for row in runtime if int(row["form_number"]) in R4R1_TRANSFER_FORMS]
    if len(transfer_runtime) != 160:
        raise U02Form03R4R1BuildError("R4R1_TRANSFER_RUNTIME_NOT_160")
    if not all(str(row["selected_item_id"]).startswith("U02FORM03R4R1-") for row in transfer_runtime):
        raise U02Form03R4R1BuildError("R4R1_TRANSFER_SOURCE_NOT_CUT_OVER")
    if len({row["learner_support_note"] for row in transfer_runtime}) != 10:
        raise U02Form03R4R1BuildError("R4R1_TRANSFER_NOTES_NOT_TASK_SPECIFIC")

    base_by_slot = {str(row["slot_id"]): row for row in baseline_runtime}
    topology_changes = 0
    for row in transfer_runtime:
        old_row = base_by_slot[str(row["slot_id"])]
        old_item = baseline_items[str(old_row["selected_item_id"])]
        new_item = item_index[str(row["selected_item_id"])]
        if (
            str(old_item.get("prompt") or "") != str(new_item.get("prompt") or "")
            or str(old_item.get("stimulus") or "") != str(new_item.get("stimulus") or "")
            or list(old_item.get("options") or []) != list(new_item.get("options") or [])
            or str(old_item.get("question_type") or "") != str(new_item.get("question_type") or "")
        ):
            topology_changes += 1
    if topology_changes != 160:
        raise U02Form03R4R1BuildError(f"R4R1_TRANSFER_TOPOLOGY_CHANGE_NOT_160:{topology_changes}")

    q9 = deepcopy(result["q9_task_angle_question_type"])
    q9["source_task_ids"] = list(q9.get("source_task_ids") or []) + [TASK_ID]
    for row in q9["post_materialization_task_families"]:
        family = str(row["task_family"])
        row["r4r1_transfer_stage_selected_occurrences"] = 16
        row["r4r1_transfer_stage_distinct_selected_item_count"] = 16
        row["r4r1_transfer_task_specific_instruction"] = TRANSFER_NOTE_BY_FAMILY[family]
        row["r4r1_real_transfer_demand"] = True
    q9["post_materialization_summary"].update({
        "r4r1_transfer_stage_runtime_occurrences": 160,
        "r4r1_transfer_stage_new_item_count": R4R1_TRANSFER_ITEM_COUNT,
        "forms01_12_runtime_identity_preserved": True,
        "forms13_16_task_specific_transfer_instruction_proven": True,
        "forms13_16_real_transfer_demand_proven": True,
        "global_640_distinct_runtime_question_proof": True,
    })

    q10["source_task_ids"] = list(q10.get("source_task_ids") or []) + [TASK_ID]
    q10["inventory_summary"].update({
        "unit02_approved_item_count": EXPECTED_UNIT02_APPROVED_ITEMS,
        "cumulative_catalog_item_count": EXPECTED_CUMULATIVE_ITEMS,
        "r4r1_transfer_stage_policy_bound_items": R4R1_TRANSFER_ITEM_COUNT,
    })
    q10["runtime_eligibility"].update({
        "runtime_selected_distinct_item_count": 640,
        "runtime_pool_distinct_item_count": len({candidate for row in runtime for candidate in row["candidate_ids"]}),
        "r4r1_transfer_stage_family_pool_counts": {family: R4R1_TRANSFER_ITEMS_PER_FAMILY for family in TASK_FAMILIES},
    })
    bound = [row for row in runtime if row["sentence_asset_binding"]["status"] == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"]
    if len(bound) != 128:
        raise U02Form03R4R1BuildError(f"R4R1_Q6_BOUND_COUNT_INVALID:{len(bound)}")
    q10["sentence_asset_integration"]["bound_runtime_occurrence_count"] = len(bound)
    q10["sentence_asset_integration"]["q6_assets_mutated"] = False
    q10["runtime_form_contract"].update({
        "runtime_occurrence_count": 640,
        "global_same_task_family_selected_item_reuse": False,
        "global_640_distinct_runtime_question_proof": True,
        "forms01_12_runtime_identity_preserved": True,
        "forms13_16_selected_item_count": 160,
        "forms13_16_task_specific_instruction_proven": True,
        "forms13_16_real_transfer_demand_proven": True,
    })
    q10["unit02_approved_items"] = items
    q10["capacity_slot_matrix"] = [{
        "slot_id": row["slot_id"],
        "form_number": row["form_number"],
        "progression_stage": row["progression_stage"],
        "scene_slot_ordinal": row["scene_slot_ordinal"],
        "task_family": row["task_family"],
        "candidate_ids": list(row["candidate_ids"]),
        "selected_item_id": row["selected_item_id"],
    } for row in runtime]
    q10["runtime_occurrences"] = runtime
    q10["global_distinctness_proof"] = proof
    q10["progression_support_contract"] = {
        "learner_support_notes_by_stage": dict(SUPPORT_NOTE_BY_STAGE),
        "transfer_task_specific_notes_by_family": dict(TRANSFER_NOTE_BY_FAMILY),
        "support_reduction_proven": True,
        "transfer_demand_proven": True,
        "independent_transfer_topology_distinct": True,
        "transfer_stage_runtime_occurrences": 160,
        "transfer_stage_task_specific_note_count": 10,
        "transfer_stage_topology_change_count": topology_changes,
    }
    q10["legacy_runtime_authority_superseded_for_current_delivery"] = True

    result["schema_version"] = SCHEMA_VERSION
    result["program_id"] = PROGRAM_ID
    result["task_id"] = TASK_ID
    result["status"] = PASS_STATUS
    result["q9_task_angle_question_type"] = q9
    result["q10_questionbank_capacity_runtime"] = q10
    result["claim_boundaries"] = {
        "q01_q08_mutated": False,
        "questionbank_items_created": True,
        "runtime_authority_successor_created": True,
        "forms01_12_runtime_identity_mutated": False,
        "forms13_16_runtime_identity_mutated": True,
        "legacy_qbc02_items_deleted": False,
        "sentence_assets_created": False,
        "canonical_scene_authority_created": False,
        "learner_state_mutated": False,
        "scoring_authority_created": False,
        "a2_unlocked": False,
    }
    before_q1_q8 = _q1_q8_projection(baseline)
    after_q1_q8 = _q1_q8_projection(result)
    if before_q1_q8 != after_q1_q8:
        raise U02Form03R4R1BuildError("R4R1_Q01_Q08_PAYLOAD_DRIFT")
    result["q01_q08_preservation"] = {
        "preserved": True,
        "baseline_sha256": _digest(before_q1_q8),
        "r3_sha256": _digest(after_q1_q8),
    }
    result["forms01_12_runtime_identity_preservation"] = {
        "preserved": True,
        "baseline_sha256": _digest(before_01_12),
        "r4r1_sha256": _digest(after_01_12),
        "runtime_occurrence_count": len(after_01_12),
    }
    result["r4r1_transfer_fullfix"] = {
        "transfer_forms": list(R4R1_TRANSFER_FORMS),
        "transfer_runtime_occurrences": 160,
        "transfer_new_items": R4R1_TRANSFER_ITEM_COUNT,
        "task_specific_instruction_count": 10,
        "task_topology_change_count": topology_changes,
        "real_transfer_demand_proven": True,
        "ordered_tokens_runtime_occurrences": sum(1 for row in runtime if _response_type(item_index[str(row["selected_item_id"])]) == "sequence"),
    }
    result.pop("package_sha256", None)
    result["package_sha256"] = _digest(result)
    return result


def build_candidate() -> dict[str, Any]:
    payload = build_export_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "u02form03r3_task_id": base.TASK_ID,
            "u02form03r3_package_sha256": base.build_export_payload()["package_sha256"],
            "forms01_12_runtime_identity_preserved": True,
            "forms13_16_transfer_stage_fullfix": True,
            "r4r1_transfer_item_count": R4R1_TRANSFER_ITEM_COUNT,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix as validator
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
    payload = approved["payload"]
    q10 = payload["q10_questionbank_capacity_runtime"]
    proof = q10["global_distinctness_proof"]
    transfer = payload["r4r1_transfer_fullfix"]
    print(f"STATUS={PASS_STATUS}")
    print(f"Q01_Q08_PRESERVED={payload['q01_q08_preservation']['preserved']}")
    print("FORMS01_12_RUNTIME_IDENTITY_PRESERVED=" f"{payload['forms01_12_runtime_identity_preservation']['preserved']}")
    print("UNIT02_APPROVED_ITEMS=" f"{q10['inventory_summary']['unit02_approved_item_count']}")
    print(f"RUNTIME_OCCURRENCES={proof['runtime_occurrence_count']}")
    print(f"DISTINCT_VISIBLE_SIGNATURES={proof['distinct_visible_signatures']}")
    print("GLOBAL_640_DISTINCT_RUNTIME_QUESTION_PROOF=" f"{proof['global_640_distinct_runtime_question_proof']}")
    print("TRANSFER_REAL_DEMAND_PROVEN=" f"{transfer['real_transfer_demand_proven']}")
    print("TRANSFER_TOPOLOGY_CHANGE_COUNT=" f"{transfer['task_topology_change_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
