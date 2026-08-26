#!/usr/bin/env python3
"""R3 successor authority for Unit02 Q09/Q10 pedagogical/runtime FullFix.

Q01-Q08 are preserved byte-for-byte at payload level from U02FP01. R3 adds a
policy-bound QuestionBank delta and a replacement Q09/Q10 runtime projection
that proves 640 globally distinct learner-visible questions, removes direct
within-scene answer leakage, keeps legacy QBC02 items approved but runtime
ineligible, and preserves the existing 16 x 40 form denominator.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02fp01_unit02_final_package_q1_q10_export as fp01,
)
from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as qbc02,
)
from ulga.builders import (
    build_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck
    as sc04,
)
from ulga.builders import (
    build_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck
    as u02sa01,
)
from ulga.builders.a1fs_v1_u02sa01r1.common import normalize_sentence, normalize_surface

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U02FORM03R3_"
    "SourceAuthorityPedagogicalFullFixAndOrderedTokensConsumerRepair"
)
SCHEMA_VERSION = "a1fs.v1.u02form03r3.q09_q10_pedagogical_fullfix.v1"
PASS_STATUS = (
    "PASS_A1FS_V1_U02FORM03R3_"
    "SOURCE_AUTHORITY_PEDAGOGICAL_FULLFIX"
)
DECISION_REF = (
    "OPERATOR_APPROVAL:2026-08-24:"
    "U02FORM03R3_SOURCE_AUTHORITY_PEDAGOGICAL_FULLFIX"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U02FORM03R4_"
    "Actual16PdfRerenderAndShaBoundHumanReacceptance"
)

TASK_FAMILIES = tuple(qbc02.TASK_FAMILIES)
FORM_COUNT = 16
SCENE_SLOTS_PER_FORM = 4
ACTIVITIES_PER_FORM = 40
TOTAL_RUNTIME_OCCURRENCES = 640
PER_FAMILY_RUNTIME_OCCURRENCES = 64
MIN_CANDIDATES_PER_SLOT = 3

LEGACY_UNIT02_APPROVED_ITEMS = qbc02.EXPECTED_UNIT02_APPROVED_ITEMS
LEGACY_QBC02_NEW_ITEMS = qbc02.EXPECTED_NEW_ITEMS
R3_CONTEXTS_PER_MATERIALIZED_FAMILY = 72
R3_MATERIALIZED_FAMILIES = (
    "RECOGNITION",
    "MEANING_DISCRIMINATION",
    "ERROR_DETECTION",
    "ERROR_CORRECTION",
    "CONTEXT_GAP",
    "U01_U02_INTEGRATION",
    "PRODUCTIVE_RESPONSE",
    "TRANSFER",
)
R3_NEW_ITEMS = (
    R3_CONTEXTS_PER_MATERIALIZED_FAMILY * len(R3_MATERIALIZED_FAMILIES)
)
EXPECTED_UNIT02_APPROVED_ITEMS = LEGACY_UNIT02_APPROVED_ITEMS + R3_NEW_ITEMS
EXPECTED_UNIT01_REFERENCE_ITEMS = 474
EXPECTED_CUMULATIVE_ITEMS = EXPECTED_UNIT01_REFERENCE_ITEMS + EXPECTED_UNIT02_APPROVED_ITEMS

RUNTIME_RESTRICTED_SURFACES = {"beer"}
SENTENCE_BINDING_REQUIRED_FAMILIES = {"PRODUCTIVE_RESPONSE", "TRANSFER"}

QUESTION_TYPE_BY_FAMILY = {
    "RECOGNITION": "multiple_choice",
    "MEANING_DISCRIMINATION": "multiple_choice",
    "ERROR_DETECTION": "multiple_choice",
    "ERROR_CORRECTION": "gap_fill",
    "CONTEXT_GAP": "gap_fill",
    "U01_U02_INTEGRATION": "gap_fill",
    "PRODUCTIVE_RESPONSE": "gap_fill",
    "TRANSFER": "gap_fill",
}
READING_FAMILIES = {
    "RECOGNITION",
    "MEANING_DISCRIMINATION",
    "FORM_SELECTION",
    "ERROR_DETECTION",
}
SUPPORT_NOTE_BY_STAGE = {
    "GUIDED": "Hint: regular plurals usually add -s.",
    "REDUCED_SUPPORT": "Use the singular clue to choose or build the plural.",
    "INDEPENDENT": "Work independently without a rule hint.",
    "TRANSFER": "Apply the plural rule in a new sentence without a hint.",
}

_Q1_Q8_KEYS = (
    "q1_grammar",
    "q2_q3_existing_export_ref",
    "q4_chunks",
    "q5_sentence_patterns",
    "q6_existing_export_ref",
    "q7_micro_scenes",
    "q8_communicative_functions",
)


class U02Form03R3BuildError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return policy_artifact.digest(value)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", str(value).upper()).strip("-")


def _response_contract(scoring_mode: str, correct_answer: str) -> dict[str, Any]:
    return {
        "scoring_mode": scoring_mode,
        "response_type": "string",
        "accepted_texts": [correct_answer],
        "accepted_sequence": [],
        "capture_enabled": True,
        "human_review_fallback": False,
    }


def _source_context_rows() -> list[dict[str, Any]]:
    rows = sorted(
        sc04.materialized_rows(),
        key=lambda row: (str(row["target_singular"]), str(row["materialization_id"])),
    )
    if len(rows) < R3_CONTEXTS_PER_MATERIALIZED_FAMILY:
        raise U02Form03R3BuildError(
            f"R3_CONTEXT_CAPACITY_TOO_SHALLOW:{len(rows)}"
        )
    selected = [deepcopy(row) for row in rows[:R3_CONTEXTS_PER_MATERIALIZED_FAMILY]]
    singulars = [normalize_surface(row["target_singular"]) for row in selected]
    if len(singulars) != len(set(singulars)):
        raise U02Form03R3BuildError("R3_CONTEXT_SINGULAR_NOT_DISTINCT")
    return selected


def _new_item(task_family: str, row: Mapping[str, Any]) -> dict[str, Any]:
    singular = str(row["target_singular"])
    plural = str(row["target_plural"])
    vocab_ids = sorted(set(str(v) for v in row.get("vocabulary_ids") or []))
    common_prereq = [qb02.PREREQUISITE_KP009]
    grammar_targets = ["REGULAR_PLURAL_NOUNS"]
    prerequisite_rows = list(common_prereq)

    if task_family == "RECOGNITION":
        prompt = "Which word names more than one?"
        stimulus = f"Singular word: {singular}"
        options = [plural, singular]
        correct = plural
        scoring = "EXACT_OPTION"
    elif task_family == "MEANING_DISCRIMINATION":
        prompt = "Choose the phrase for more than one."
        stimulus = f"Singular word: {singular}"
        options = [f"two {plural}", f"one {singular}"]
        correct = f"two {plural}"
        scoring = "EXACT_OPTION"
    elif task_family == "ERROR_DETECTION":
        prompt = "Choose the phrase with the plural error."
        stimulus = f"Singular word: {singular}"
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
        prompt = "Complete the phrase for more than one."
        stimulus = f"Singular word: {singular}. Complete: two ___."
        options = []
        correct = plural
        scoring = "NORMALIZED_TEXT"
    elif task_family == "U01_U02_INTEGRATION":
        prompt = "Change the singular noun phrase to a plural noun phrase."
        stimulus = f"the {singular} -> the ___"
        options = []
        correct = f"the {plural}"
        scoring = "NORMALIZED_TEXT"
        grammar_targets = ["GRAMMAR_ARTICLES_BASIC", "REGULAR_PLURAL_NOUNS"]
        prerequisite_rows = sorted(
            set(common_prereq + list(qbc02.u01_contract.CORE_EGP_ROWS))
        )
    elif task_family == "PRODUCTIVE_RESPONSE":
        prompt = "Write a sentence about two of them."
        stimulus = f"Singular word: {singular}"
        options = []
        correct = f"I can see two {plural}."
        scoring = "NORMALIZED_TEXT"
    elif task_family == "TRANSFER":
        prompt = "Complete the sentence in a new situation."
        stimulus = f"Singular word: {singular}. I can see two ___."
        options = []
        correct = plural
        scoring = "NORMALIZED_TEXT"
    else:
        raise U02Form03R3BuildError(f"R3_UNKNOWN_FAMILY:{task_family}")

    lexical_slots = {
        "singular_noun": singular,
        "plural_noun": plural,
        "determiner": "two",
    }
    item = {
        "item_id": f"U02FORM03R3-{task_family}-{_slug(singular)}",
        "unit_id": qb02.UNIT_ID,
        "task_family": task_family,
        "pattern_family_id": f"U02-R3-{task_family}",
        "lexical_slots": lexical_slots,
        "unit_pattern_ids": [qb02.DIRECT_PATTERN_ID],
        "grammar_target_ids": grammar_targets,
        "target_egp_row_ids": [qb02.KP014],
        "prerequisite_egp_row_ids": prerequisite_rows,
        "target_evp_sense_ids": vocab_ids,
        "skill": "READING" if task_family in READING_FAMILIES else "WRITING",
        "question_type": QUESTION_TYPE_BY_FAMILY[task_family],
        "prompt": prompt,
        "stimulus": stimulus,
        "options": options,
        "correct_answer": correct,
        "accepted_answers": [correct],
        "scoring_mode": scoring,
        "support_level": "RUNTIME_STAGE_BOUND",
        "learner_visible_capable": True,
        "learner_delivery_status": "R3_RUNTIME_ELIGIBLE",
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
                "U02FORM03R3_PEDAGOGICAL_FULLFIX",
                f"TASK_FAMILY_{task_family}",
                "GLOBAL_640_DISTINCT_RUNTIME_CAPACITY",
            ],
        },
        "source_refs": [
            {"source_type": "U02QB02_APPROVED_POOL", "task_id": qb02.TASK_ID},
            {"source_type": "U02QBC02_LEGACY_AUTHORITY", "task_id": qbc02.TASK_ID},
            {
                "source_type": "U02SC04_STRUCTURAL_CONTEXT_EVIDENCE",
                "task_id": sc04.TASK_ID,
                "materialization_id": row["materialization_id"],
                "canonical_scene_authority": False,
            },
        ],
    }
    item["response_contract"] = _response_contract(scoring, correct)
    item["semantic_signature"] = _digest(
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


def r3_new_items() -> list[dict[str, Any]]:
    contexts = _source_context_rows()
    rows = [
        _new_item(family, context)
        for family in R3_MATERIALIZED_FAMILIES
        for context in contexts
    ]
    rows.sort(key=lambda row: row["item_id"])
    if len(rows) != R3_NEW_ITEMS:
        raise U02Form03R3BuildError(f"R3_NEW_ITEM_COUNT_INVALID:{len(rows)}")
    if len({row["item_id"] for row in rows}) != len(rows):
        raise U02Form03R3BuildError("R3_DUPLICATE_ITEM_ID")
    if len({row["semantic_signature"] for row in rows}) != len(rows):
        raise U02Form03R3BuildError("R3_DUPLICATE_ITEM_SEMANTIC_SIGNATURE")
    return rows


def _target_singular(item: Mapping[str, Any]) -> str:
    return normalize_surface(
        str((item.get("lexical_slots") or {}).get("singular_noun") or "")
    )


def _target_plural(item: Mapping[str, Any]) -> str:
    return normalize_surface(
        str((item.get("lexical_slots") or {}).get("plural_noun") or "")
    )


def _legacy_base_pool(
    legacy_items: Sequence[Mapping[str, Any]], task_family: str
) -> list[str]:
    if task_family == "FORM_SELECTION":
        allowed = {"U02-PF02-PLURAL-FORM-CHOICE"}
    elif task_family == "MORPHOLOGY_CONSTRUCTION":
        allowed = {"U02-PF01-PLURAL-FORM-PRODUCTION"}
    else:
        return []
    return sorted(
        str(row["item_id"])
        for row in legacy_items
        if row.get("learner_visible_capable") is True
        and str(row.get("pattern_family_id") or "") in allowed
    )


def _runtime_pools(
    legacy_items: Sequence[Mapping[str, Any]],
    new_items: Sequence[Mapping[str, Any]],
    item_index: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, list[str]], list[str]]:
    new_by_family = {
        family: sorted(
            str(row["item_id"])
            for row in new_items
            if str(row.get("task_family")) == family
        )
        for family in R3_MATERIALIZED_FAMILIES
    }
    pools: dict[str, list[str]] = {}
    restricted: set[str] = set()
    for family in TASK_FAMILIES:
        ids = _legacy_base_pool(legacy_items, family) or new_by_family.get(family, [])
        legal: list[str] = []
        for item_id in ids:
            item = item_index[item_id]
            if _target_singular(item) in RUNTIME_RESTRICTED_SURFACES:
                restricted.add(item_id)
                continue
            legal.append(item_id)
        if len(legal) < PER_FAMILY_RUNTIME_OCCURRENCES:
            raise U02Form03R3BuildError(
                f"R3_RUNTIME_POOL_BELOW_64:{family}:{len(legal)}"
            )
        pools[family] = legal
    return pools, sorted(restricted)


def _stage(form_number: int) -> str:
    return qbc02.progression_stage(form_number)


def _response_type(item: Mapping[str, Any]) -> str:
    contract = item.get("response_contract") or {}
    value = str(contract.get("response_type") or "")
    if value:
        return value
    return "string"


def _visible_payload(
    item: Mapping[str, Any], task_family: str, support_note: str
) -> dict[str, Any]:
    return {
        "task_family": task_family,
        "prompt": f"{str(item.get('prompt') or '').strip()} {support_note}".strip(),
        "stimulus": str(item.get("stimulus") or "").strip(),
        "options": list(item.get("options") or []),
        "response_type": _response_type(item),
    }


def _visible_signature(
    item: Mapping[str, Any], task_family: str, support_note: str
) -> str:
    return _digest(_visible_payload(item, task_family, support_note))


def _effective_signature(
    item: Mapping[str, Any], task_family: str, support_note: str
) -> str:
    return _digest(
        {
            **_visible_payload(item, task_family, support_note),
            "correct_answer": item.get("correct_answer"),
            "accepted_answers": list(item.get("accepted_answers") or []),
            "accepted_sequence": list(
                (item.get("response_contract") or {}).get("accepted_sequence") or []
            ),
        }
    )


def _runtime_semantic_signature(
    item: Mapping[str, Any], task_family: str, support_note: str
) -> str:
    return _digest(
        {
            "task_family": task_family,
            "item_semantic_signature": str(item.get("semantic_signature") or ""),
            "target_singular": _target_singular(item),
            "support_note": support_note,
        }
    )


def _candidate_ids(
    pool: Sequence[str], selected_id: str, salt: int
) -> list[str]:
    if selected_id not in pool:
        raise U02Form03R3BuildError("R3_SELECTED_NOT_IN_POOL")
    start = pool.index(selected_id)
    result = [selected_id]
    step = 1 + (salt % max(1, len(pool) - 1))
    cursor = start
    while len(result) < MIN_CANDIDATES_PER_SLOT:
        cursor = (cursor + step) % len(pool)
        candidate = pool[cursor]
        if candidate not in result:
            result.append(candidate)
        if len(result) < MIN_CANDIDATES_PER_SLOT and cursor == start:
            step += 1
    return result


def _scene_assignment(
    *,
    scene_ordinal: int,
    pools: Mapping[str, Sequence[str]],
    item_index: Mapping[str, Mapping[str, Any]],
    used_by_family: Mapping[str, set[str]],
) -> dict[str, str]:
    families = list(TASK_FAMILIES)

    def ordered_candidates(family: str, family_index: int) -> list[str]:
        pool = list(pools[family])
        start = (scene_ordinal * 11 + family_index * 7) % len(pool)
        return pool[start:] + pool[:start]

    def search(
        family_index: int,
        chosen: dict[str, str],
        singulars: set[str],
    ) -> dict[str, str] | None:
        if family_index == len(families):
            return chosen
        family = families[family_index]
        for item_id in ordered_candidates(family, family_index):
            if item_id in used_by_family[family]:
                continue
            singular = _target_singular(item_index[item_id])
            if not singular or singular in singulars:
                continue
            result = search(
                family_index + 1,
                {**chosen, family: item_id},
                singulars | {singular},
            )
            if result is not None:
                return result
        return None

    result = search(0, {}, set())
    if result is None:
        raise U02Form03R3BuildError(
            f"R3_SCENE_DISTINCT_TARGET_ASSIGNMENT_FAILED:{scene_ordinal}"
        )
    return result


def _normalized_visible_text(item: Mapping[str, Any], support_note: str) -> str:
    values = [
        str(item.get("prompt") or ""),
        support_note,
        str(item.get("stimulus") or ""),
        *[str(value) for value in item.get("options") or []],
    ]
    return normalize_surface(" ".join(values))


def _word_present(text: str, word: str) -> bool:
    if not word:
        return False
    return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) is not None


def _sentence_index() -> tuple[dict[str, dict[str, Any]], Mapping[str, Any]]:
    q6 = u02sa01.build_report()
    assets = q6["sentence_asset_delta"]["assets"]
    result: dict[str, dict[str, Any]] = {}
    for asset in assets:
        key = normalize_sentence(str(asset["text"]))
        if key in result:
            raise U02Form03R3BuildError(f"R3_Q6_SENTENCE_COLLISION:{key}")
        result[key] = dict(asset)
    return result, q6


def _sentence_binding(
    task_family: str,
    item: Mapping[str, Any],
    sentence_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if task_family not in SENTENCE_BINDING_REQUIRED_FAMILIES:
        return {
            "status": "NOT_REQUIRED_FOR_TASK_FAMILY",
            "sentence_asset_id": None,
            "binding_text": None,
        }
    plural = str((item.get("lexical_slots") or {}).get("plural_noun") or "")
    expected = f"I can see two {plural}."
    asset = sentence_index.get(normalize_sentence(expected))
    if asset is None:
        raise U02Form03R3BuildError(
            f"R3_Q6_BINDING_NOT_FOUND:{task_family}:{item['item_id']}:{expected}"
        )
    return {
        "status": "BOUND_CANONICAL_Q6_SENTENCE_ASSET",
        "sentence_asset_id": asset["sentence_id"],
        "binding_text": asset["text"],
        "sentence_asset_pattern_metadata": asset.get("pattern_id"),
    }


def _runtime_rows(
    pools: Mapping[str, Sequence[str]],
    item_index: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    used_by_family = {family: set() for family in TASK_FAMILIES}
    sentence_index, q6 = _sentence_index()
    rows: list[dict[str, Any]] = []
    scene_ordinal = 0
    direct_answer_leaks: list[str] = []

    for form_number in range(1, FORM_COUNT + 1):
        stage = _stage(form_number)
        support_note = SUPPORT_NOTE_BY_STAGE[stage]
        for scene_slot in range(1, SCENE_SLOTS_PER_FORM + 1):
            assignment = _scene_assignment(
                scene_ordinal=scene_ordinal,
                pools=pools,
                item_index=item_index,
                used_by_family=used_by_family,
            )
            prior_visible = ""
            for task_index, task_family in enumerate(TASK_FAMILIES, start=1):
                selected_id = assignment[task_family]
                item = item_index[selected_id]
                plural = _target_plural(item)
                if _word_present(prior_visible, plural):
                    direct_answer_leaks.append(
                        f"F{form_number:02d}:S{scene_slot:02d}:{task_family}:{plural}"
                    )
                slot_id = f"U02-F{form_number:02d}-S{scene_slot:02d}-T{task_index:02d}"
                candidates = _candidate_ids(
                    list(pools[task_family]),
                    selected_id,
                    salt=scene_ordinal + task_index,
                )
                rows.append(
                    {
                        "runtime_occurrence_id": f"{slot_id}::{selected_id}",
                        "slot_id": slot_id,
                        "form_number": form_number,
                        "progression_stage": stage,
                        "scene_slot_ordinal": scene_slot,
                        "task_family": task_family,
                        "candidate_ids": candidates,
                        "selected_item_id": selected_id,
                        "runtime_selection_rule": (
                            "R3_GLOBAL_INJECTIVE_FAMILY_SELECTION_"
                            "WITH_SCENE_TARGET_DISTINCTNESS"
                        ),
                        "questionbank_item_id": selected_id,
                        "questionbank_source": (
                            "U02FORM03R3"
                            if selected_id.startswith("U02FORM03R3-")
                            else "U02QB02"
                        ),
                        "target_singular": _target_singular(item),
                        "learner_support_note": support_note,
                        "sentence_asset_binding": _sentence_binding(
                            task_family, item, sentence_index
                        ),
                        "learner_delivery_status": "R3_RUNTIME_PROJECTED",
                        "visible_signature": _visible_signature(
                            item, task_family, support_note
                        ),
                        "effective_signature": _effective_signature(
                            item, task_family, support_note
                        ),
                        "runtime_semantic_signature": _runtime_semantic_signature(
                            item, task_family, support_note
                        ),
                    }
                )
                used_by_family[task_family].add(selected_id)
                prior_visible = (
                    prior_visible
                    + " "
                    + _normalized_visible_text(item, support_note)
                ).strip()
            scene_ordinal += 1

    if direct_answer_leaks:
        raise U02Form03R3BuildError(
            "R3_PRIOR_ACTIVITY_DIRECT_ANSWER_LEAK:"
            + "|".join(direct_answer_leaks[:10])
        )
    if len(rows) != TOTAL_RUNTIME_OCCURRENCES:
        raise U02Form03R3BuildError(
            f"R3_RUNTIME_COUNT_INVALID:{len(rows)}"
        )
    return rows, q6


def _global_distinctness_proof(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected_ids = [str(row["selected_item_id"]) for row in rows]
    visible = [str(row["visible_signature"]) for row in rows]
    effective = [str(row["effective_signature"]) for row in rows]
    semantic = [str(row["runtime_semantic_signature"]) for row in rows]

    per_family = {}
    for family in TASK_FAMILIES:
        family_rows = [row for row in rows if row["task_family"] == family]
        per_family[family] = {
            "runtime_occurrences": len(family_rows),
            "distinct_selected_item_ids": len(
                {row["selected_item_id"] for row in family_rows}
            ),
            "distinct_visible_signatures": len(
                {row["visible_signature"] for row in family_rows}
            ),
            "distinct_effective_signatures": len(
                {row["effective_signature"] for row in family_rows}
            ),
            "distinct_semantic_signatures": len(
                {row["runtime_semantic_signature"] for row in family_rows}
            ),
        }

    proof = {
        "runtime_occurrence_count": len(rows),
        "distinct_runtime_occurrence_ids": len(
            {str(row["runtime_occurrence_id"]) for row in rows}
        ),
        "distinct_selected_item_ids": len(set(selected_ids)),
        "distinct_visible_signatures": len(set(visible)),
        "distinct_effective_signatures": len(set(effective)),
        "distinct_semantic_signatures": len(set(semantic)),
        "exact_duplicate_groups": len(rows) - len(set(visible)),
        "normalized_duplicate_groups": len(rows) - len(set(visible)),
        "semantic_duplicate_groups": len(rows) - len(set(semantic)),
        "same_visible_different_answer_groups": 0,
        "within_form_duplicates": 0,
        "cross_form_duplicates": len(rows) - len(set(visible)),
        "prior_activity_direct_answer_leaks": 0,
        "per_family": per_family,
    }
    proof["global_640_distinct_runtime_question_proof"] = (
        proof["runtime_occurrence_count"] == 640
        and proof["distinct_runtime_occurrence_ids"] == 640
        and proof["distinct_selected_item_ids"] == 640
        and proof["distinct_visible_signatures"] == 640
        and proof["distinct_effective_signatures"] == 640
        and proof["distinct_semantic_signatures"] == 640
        and proof["exact_duplicate_groups"] == 0
        and proof["semantic_duplicate_groups"] == 0
        and proof["prior_activity_direct_answer_leaks"] == 0
        and all(
            row["runtime_occurrences"] == 64
            and row["distinct_selected_item_ids"] == 64
            and row["distinct_visible_signatures"] == 64
            and row["distinct_effective_signatures"] == 64
            and row["distinct_semantic_signatures"] == 64
            for row in per_family.values()
        )
    )
    if not proof["global_640_distinct_runtime_question_proof"]:
        raise U02Form03R3BuildError(f"R3_GLOBAL_DISTINCTNESS_NOT_PROVEN:{proof}")
    return proof


def _q1_q8_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(payload[key]) for key in _Q1_Q8_KEYS}


def build_export_payload() -> dict[str, Any]:
    baseline = fp01.build_export_payload()
    legacy_q10 = baseline["q10_questionbank_capacity_runtime"]
    legacy_items = [dict(row) for row in legacy_q10["unit02_approved_items"]]
    if len(legacy_items) != LEGACY_UNIT02_APPROVED_ITEMS:
        raise U02Form03R3BuildError(
            f"R3_LEGACY_Q10_COUNT_DRIFT:{len(legacy_items)}"
        )

    new_items = r3_new_items()
    approved_items = legacy_items + new_items
    if len(approved_items) != EXPECTED_UNIT02_APPROVED_ITEMS:
        raise U02Form03R3BuildError(
            f"R3_APPROVED_COUNT_INVALID:{len(approved_items)}"
        )
    item_index = {str(row["item_id"]): row for row in approved_items}
    if len(item_index) != len(approved_items):
        raise U02Form03R3BuildError("R3_APPROVED_ITEM_ID_COLLISION")

    pools, restricted_ids = _runtime_pools(
        legacy_items, new_items, item_index
    )
    runtime_rows, q6 = _runtime_rows(pools, item_index)
    proof = _global_distinctness_proof(runtime_rows)

    selected_counts = Counter(row["task_family"] for row in runtime_rows)
    if selected_counts != Counter({family: 64 for family in TASK_FAMILIES}):
        raise U02Form03R3BuildError(
            f"R3_TASK_FAMILY_RUNTIME_COUNT_INVALID:{dict(selected_counts)}"
        )
    bound = [
        row
        for row in runtime_rows
        if row["sentence_asset_binding"]["status"]
        == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"
    ]
    if len(bound) != 128:
        raise U02Form03R3BuildError(f"R3_Q6_BOUND_COUNT_INVALID:{len(bound)}")

    legacy_gap_ids = {
        str(row["item_id"])
        for row in legacy_items
        if str(row["item_id"]).startswith("U02QBC02-")
    }
    selected_ids = {str(row["selected_item_id"]) for row in runtime_rows}
    if legacy_gap_ids & selected_ids:
        raise U02Form03R3BuildError("R3_LEGACY_QBC02_ITEM_SELECTED")

    baseline_q9 = baseline["q9_task_angle_question_type"]
    baseline_by_family = {
        str(row["task_family"]): dict(row)
        for row in baseline_q9["baseline_task_family_denominator"]
    }
    q9_rows = []
    for family in TASK_FAMILIES:
        base = baseline_by_family[family]
        q9_rows.append(
            {
                "task_family": family,
                "q9_baseline_coverage_status": base["coverage_status"],
                "q9_baseline_coverage_reason": base["coverage_reason"],
                "r3_runtime_pool_depth": len(pools[family]),
                "r3_runtime_selected_occurrences": 64,
                "r3_distinct_selected_item_count": 64,
                "r3_distinct_visible_signature_count": 64,
                "r3_runtime_connected": True,
            }
        )

    q9 = {
        "unit_id": qb02.UNIT_ID,
        "source_task_ids": list(baseline_q9["source_task_ids"]) + [TASK_ID],
        "baseline_task_family_denominator": deepcopy(
            baseline_q9["baseline_task_family_denominator"]
        ),
        "baseline_pedagogical_role_denominator": deepcopy(
            baseline_q9["baseline_pedagogical_role_denominator"]
        ),
        "post_materialization_task_families": q9_rows,
        "post_materialization_summary": {
            "task_family_count": len(q9_rows),
            "minimum_pool_depth": min(len(ids) for ids in pools.values()),
            "all_ten_task_family_pools_have_at_least_64_runtime_eligible_items": True,
            "runtime_occurrence_count": len(runtime_rows),
            "global_640_distinct_runtime_question_proof": True,
            "interpretation": (
                "R3 supersedes the old per-slot-only capacity proof for current "
                "Unit02 runtime delivery; historical Q09 denominators remain preserved."
            ),
        },
    }

    q10 = {
        "unit_id": qb02.UNIT_ID,
        "source_task_ids": list(legacy_q10["source_task_ids"]) + [TASK_ID],
        "inventory_summary": {
            "unit01_reference_only_item_count": EXPECTED_UNIT01_REFERENCE_ITEMS,
            "unit02_approved_item_count": len(approved_items),
            "cumulative_catalog_item_count": EXPECTED_CUMULATIVE_ITEMS,
            "unit01_catalog_mutated": False,
            "legacy_qbc02_items_deleted": False,
            "r3_new_policy_bound_items": len(new_items),
            "parallel_questionbank_created": False,
        },
        "runtime_eligibility": {
            "restricted_target_surfaces": sorted(RUNTIME_RESTRICTED_SURFACES),
            "restricted_questionbank_item_ids": restricted_ids,
            "legacy_qbc02_runtime_ineligible_item_count": len(legacy_gap_ids),
            "approved_assets_deleted": False,
            "runtime_pool_distinct_item_count": len(
                {item_id for ids in pools.values() for item_id in ids}
            ),
            "runtime_selected_distinct_item_count": len(selected_ids),
            "minimum_runtime_family_pool_depth": min(
                len(ids) for ids in pools.values()
            ),
            "runtime_family_pool_counts": {
                family: len(ids) for family, ids in pools.items()
            },
        },
        "sentence_asset_integration": {
            "binding_required_task_families": sorted(
                SENTENCE_BINDING_REQUIRED_FAMILIES
            ),
            "bound_runtime_occurrence_count": len(bound),
            "bound_distinct_sentence_asset_count": len(
                {
                    row["sentence_asset_binding"]["sentence_asset_id"]
                    for row in bound
                }
            ),
            "q6_sentence_asset_count": q6["sentence_asset_delta"]["asset_count"],
            "q6_sentence_asset_digest": q6["sentence_asset_delta"]["asset_digest"],
            "q6_assets_mutated": False,
        },
        "runtime_form_contract": {
            "form_count": FORM_COUNT,
            "scene_slots_per_form": SCENE_SLOTS_PER_FORM,
            "task_family_count": len(TASK_FAMILIES),
            "activities_per_form": ACTIVITIES_PER_FORM,
            "runtime_occurrence_count": len(runtime_rows),
            "selected_count_by_task_family": dict(sorted(selected_counts.items())),
            "all_slots_retain_three_legal_candidates": all(
                len(row["candidate_ids"]) == 3 for row in runtime_rows
            ),
            "within_form_same_task_family_selected_item_reuse": False,
            "global_same_task_family_selected_item_reuse": False,
            "runtime_connected": True,
            "final_forms_materialized": True,
            "global_640_distinct_runtime_question_proof": True,
        },
        "unit02_approved_items": approved_items,
        "capacity_slot_matrix": [
            {
                "slot_id": row["slot_id"],
                "form_number": row["form_number"],
                "progression_stage": row["progression_stage"],
                "scene_slot_ordinal": row["scene_slot_ordinal"],
                "task_family": row["task_family"],
                "candidate_ids": list(row["candidate_ids"]),
                "selected_item_id": row["selected_item_id"],
            }
            for row in runtime_rows
        ],
        "runtime_occurrences": runtime_rows,
        "global_distinctness_proof": proof,
        "progression_support_contract": {
            "learner_support_notes_by_stage": dict(SUPPORT_NOTE_BY_STAGE),
            "support_reduction_proven": len(set(SUPPORT_NOTE_BY_STAGE.values())) == 4,
        },
        "legacy_runtime_authority_superseded_for_current_delivery": True,
        "full_unit02_approved_item_inventory_exported": True,
        "full_runtime_occurrence_plan_exported": True,
    }

    result = deepcopy(baseline)
    before = _q1_q8_projection(baseline)
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
        "legacy_qbc02_items_deleted": False,
        "sentence_assets_created": False,
        "canonical_scene_authority_created": False,
        "learner_state_mutated": False,
        "scoring_authority_created": False,
        "a2_unlocked": False,
    }
    after = _q1_q8_projection(result)
    if before != after:
        raise U02Form03R3BuildError("R3_Q01_Q08_PAYLOAD_DRIFT")
    result["q01_q08_preservation"] = {
        "preserved": True,
        "baseline_sha256": _digest(before),
        "r3_sha256": _digest(after),
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
            "u02fp01_task_id": fp01.TASK_ID,
            "u02qbc02_task_id": qbc02.TASK_ID,
            "u02sc04_task_id": sc04.TASK_ID,
            "r3_new_item_count": R3_NEW_ITEMS,
            "r3_runtime_occurrence_count": TOTAL_RUNTIME_OCCURRENCES,
            "q01_q08_preserved": True,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix
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
    payload = approved["payload"]
    proof = payload["q10_questionbank_capacity_runtime"]["global_distinctness_proof"]
    print(f"STATUS={PASS_STATUS}")
    print(
        "Q01_Q08_PRESERVED="
        f"{payload['q01_q08_preservation']['preserved']}"
    )
    print(
        "UNIT02_APPROVED_ITEMS="
        f"{payload['q10_questionbank_capacity_runtime']['inventory_summary']['unit02_approved_item_count']}"
    )
    print(f"RUNTIME_OCCURRENCES={proof['runtime_occurrence_count']}")
    print(f"DISTINCT_VISIBLE_SIGNATURES={proof['distinct_visible_signatures']}")
    print(
        "GLOBAL_640_DISTINCT_RUNTIME_QUESTION_PROOF="
        f"{proof['global_640_distinct_runtime_question_proof']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
