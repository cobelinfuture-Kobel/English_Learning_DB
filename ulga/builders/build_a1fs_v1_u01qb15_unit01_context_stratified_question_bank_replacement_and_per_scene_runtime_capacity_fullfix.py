#!/usr/bin/env python3
"""Context-stratified, count-preserving Unit01 QuestionBank FullFix.

U01QB15 supersedes only the active source-selection policy used by historical
U01QB10/U01QB12 constructors. Historical task identities and the existing
U01QB02/M3/M6 runtime remain authoritative.

Unlike the historical global item-id prefix retirement, U01QB15 solves both
context quotas and source pairs. Each PF04/PF05/PF08/PF09 family still retires
exactly 12 items, every canonical context receives 1..4 retirements per family,
PF04/PF05/PF08 context+noun pairs are mutually disjoint, and every scene must
have two Writing activities at each actual form/support exposure without task-angle
replay. Final acceptance then replays the exact U01QB14R1 solver over the final
288 base items without Real62 assistance.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb11_runtime_migration_474_replay_impl as u01qb11
from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u01qb12
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as u01qb14r1
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_patch

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_Unit01ContextStratifiedQuestionBankReplacementAndPerSceneRuntimeCapacityFullFix"
SCHEMA_VERSION = "a1fs.v1.u01qb15.unit01_context_stratified_question_bank_fullfix.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_UNIT01_CONTEXT_STRATIFIED_QUESTION_BANK_REPLACEMENT_AND_PER_SCENE_RUNTIME_CAPACITY_FULLFIX"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-04:U01QB15"
UNIT_ID = u01qb10.UNIT_ID
BANK_ID = u01qb10.BANK_ID
BANK_VERSION = u01qb10.BANK_VERSION
CANONICAL_REVISION = "U01QB15-R1"

EXPECTED_BASE_COUNT = 288
EXPECTED_EXTENSION_COUNT = 186
EXPECTED_RUNTIME_COUNT = 474
EXPECTED_U01QB10_RETIRED = 48
EXPECTED_U01QB12_RETIRED = 36
EXPECTED_FORM_COUNT = 12
EXPECTED_SCENE_WORLD_COUNT = 32
EXPECTED_BINDABLE_SCENE_COUNT = 31
EXPECTED_DEFERRED_SCENES = ("U01-MA-FOOD-04",)
EXPECTED_SKILL_SESSION_COUNT = 36
EXPECTED_ACTIVITY_COUNT = 240
EXPECTED_FINAL_SKILL_COUNTS = {"READING": 130, "SPEAKING": 25, "WRITING": 133}
EXPECTED_FINAL_FAMILY_COUNTS = {
    "U01-PF01-AAN-NOUN-GAP": 16,
    "U01-PF02-AAN-ADJ-NOUN-GAP": 6,
    "U01-PF03-VERY-ADJ-NOUN-GAP": 3,
    "U01-PF04-FIRST-MENTION-CONTEXT": 35,
    "U01-PF05-KNOWN-REFERENCE-CONTEXT": 11,
    "U01-PF06-ERROR-DISCRIMINATION": 25,
    "U01-PF07-WORD-ORDER": 13,
    "U01-PF08-TRANSFER-FIRST-MENTION": 35,
    "U01-PF09-TRANSFER-KNOWN-REFERENCE": 35,
    "U01-PF10-SPEAK-NOUN": 16,
    "U01-PF11-SPEAK-ADJ-NOUN": 6,
    "U01-PF12-SPEAK-VERY-ADJ-NOUN": 3,
    u01qb10.PF13: 12,
    u01qb10.PF14: 24,
    u01qb10.PF15: 12,
    u01qb12.PF16: 24,
    u01qb12.PF17: 12,
}

READING_REPLACEMENT_FAMILIES = (
    "U01-PF04-FIRST-MENTION-CONTEXT",
    "U01-PF05-KNOWN-REFERENCE-CONTEXT",
    "U01-PF08-TRANSFER-FIRST-MENTION",
)
WRITING_CONTEXT_REPLACEMENT_FAMILY = "U01-PF09-TRANSFER-KNOWN-REFERENCE"
REPLACEMENT_FAMILIES = (*READING_REPLACEMENT_FAMILIES, WRITING_CONTEXT_REPLACEMENT_FAMILY)
CONTEXT_REPLACEMENT_COUNT = 12
MIN_CONTEXT_QUOTA = 1
MAX_CONTEXT_QUOTA = 4
REFERENCE_REPLACEMENT_COUNT = 24
DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb15_context_stratified_qb.candidate.private.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb15_context_stratified_qb.approved.private.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb15_context_stratified_qb_readback.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_ActualReal62Fresh474MigrationAndU01QB14R1Replay"

CANONICAL_FAMILY = {
    "U01-C1-CLASSROOM-BAG": "SCHOOL",
    "U01-C2-HOME-TOY-BOX": "HOME",
    "U01-C3-PICNIC-FOOD": "FOOD_SOCIAL",
    "U01-C4-TOY-SHOP": "SHOPPING",
    "U01-C5-PARK-BIRTHDAY": "OUTDOORS_SOCIAL",
}
SITUATION_CANONICAL_CONTEXT = {
    "SCHOOL": "U01-C1-CLASSROOM-BAG",
    "HOME": "U01-C2-HOME-TOY-BOX",
    "FOOD_SOCIAL": "U01-C3-PICNIC-FOOD",
    "SHOPPING": "U01-C4-TOY-SHOP",
    "OUTDOORS": "U01-C5-PARK-BIRTHDAY",
    "OUTDOORS_SOCIAL": "U01-C5-PARK-BIRTHDAY",
}


class ContextStratifiedFullFixError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return policy_artifact.digest(value)


def _reference_context_quota(total: int) -> dict[str, int]:
    contexts = list(u01qb10.seed.CONTEXT_IDS)
    base, remainder = divmod(total, len(contexts))
    return {context: base + int(index < remainder) for index, context in enumerate(contexts)}


U01QB12_REFERENCE_CONTEXT_QUOTA = _reference_context_quota(REFERENCE_REPLACEMENT_COUNT)


def _pair_key(row: Mapping[str, Any]) -> tuple[str, str]:
    slots = dict(row.get("lexical_slots") or {})
    return (
        str(row.get("context_id") or slots.get("context_id") or ""),
        str(slots.get("noun") or "").casefold(),
    )


def _group_context_rows(items: Sequence[Mapping[str, Any]], family_id: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in items:
        if source.get("pattern_family_id") != family_id:
            continue
        row = deepcopy(dict(source))
        context, noun = _pair_key(row)
        if context not in u01qb10.seed.CONTEXT_IDS or not noun:
            raise ContextStratifiedFullFixError(
                f"CONTEXT_SOURCE_IDENTITY_INVALID:{family_id}:{row.get('item_id')}"
            )
        grouped[context].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: str(row["item_id"]))
    return grouped


def _legacy_rotation_from_authorities() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for context in s01.CONTEXTS:
        ref = str(context["context_id"])
        rows.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": u01qb08.scene_policy.digest({"scene_ref_id": ref}),
                "situation_family": CANONICAL_FAMILY[ref],
                "setting": str(context["setting"]),
                "micro_scene_event_id": str(context["title"]),
                "scene_origin": "CANONICAL_UNIT01_CONTEXT",
            }
        )
    supplement = json.loads(u01qb07.DEFAULT_SPEC.read_text(encoding="utf-8"))
    for candidate in u01qb07.candidates(supplement):
        ref = str(candidate["candidate_id"])
        rows.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": u01qb08.scene_policy.digest({"scene_ref_id": ref}),
                "situation_family": str(candidate["large_situation_family"]),
                "setting": str(candidate["medium_setting"]),
                "micro_scene_event_id": str(candidate["small_micro_scene_event"]),
                "scene_origin": "MODEL_AUTHORED_SCENE_ENRICHMENT",
            }
        )
    if len(rows) != EXPECTED_SCENE_WORLD_COUNT:
        raise ContextStratifiedFullFixError(f"SCENE_WORLD_COUNT_INVALID:{len(rows)}")
    fake_approved = {
        "artifact_sha256": "a" * 64,
        "artifact_role": "APPROVED_CANONICAL_JSON",
        "payload": {"task_id": u01qb07.TASK_ID},
    }
    original = u01qb08.approved_scene_rows
    try:
        u01qb08.approved_scene_rows = lambda _approved: deepcopy(rows)
        return u01qb08.build_rotation(fake_approved)
    finally:
        u01qb08.approved_scene_rows = original


def _scene_requirements() -> dict[str, list[dict[str, Any]]]:
    rotation = u01qb14r1.rematerialize_rotation(_legacy_rotation_from_authorities())
    semantics = u01qb14r1.tolerant_scene_semantic_index()
    legal_by_context: dict[str, set[str]] = defaultdict(set)
    for row in u01qb10.seed_bank()[1]:
        if row.get("pattern_family_id") == READING_REPLACEMENT_FAMILIES[0]:
            context, noun = _pair_key(row)
            legal_by_context[context].add(noun)
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for usage in rotation["scene_usage_summary"]:
        ref = str(usage["scene_ref_id"])
        family = str(usage["situation_family"])
        context = SITUATION_CANONICAL_CONTEXT.get(family)
        if context is None:
            raise ContextStratifiedFullFixError(f"SCENE_CONTEXT_UNMAPPED:{ref}:{family}")
        anchors = {
            str(value).casefold()
            for value in (semantics.get(ref) or {}).get("anchors") or []
        }
        compatible = anchors & legal_by_context[context]
        if not compatible:
            raise ContextStratifiedFullFixError(f"SCENE_LEGAL_ANCHOR_MISSING:{ref}:{context}")
        result[context].append(
            {
                "scene_ref_id": ref,
                "anchors": compatible,
                "form_ordinals": tuple(int(value) for value in usage["form_ordinals"]),
            }
        )
    return {context: sorted(rows, key=lambda row: row["scene_ref_id"]) for context, rows in result.items()}


def _fixed_phrase_word_nouns() -> tuple[set[str], set[str]]:
    seed_items = u01qb10.seed_bank()[1]
    phrase_sources = u01qb12._phrase_sources(seed_items)
    phrase_ids = {str(row["item_id"]) for row in phrase_sources}
    phrase_nouns = {_pair_key(row)[1] for row in phrase_sources}
    word_nouns = {
        _pair_key(row)[1]
        for row in seed_items
        if row.get("pattern_family_id") == u01qb12.SOURCE_PHRASE_FAMILY
        and str(row["item_id"]) not in phrase_ids
    }
    return phrase_nouns, word_nouns


def _writing_angle_available(
    angle: str,
    *,
    anchors: set[str],
    phrase_nouns: set[str],
    word_nouns: set[str],
    retained_pf09_nouns: set[str],
    pf13_nouns: set[str],
    pf14_nouns: set[str],
    pf15_nouns: set[str],
) -> bool:
    sources = {
        "PHRASE_CONSTRUCTION": phrase_nouns,
        "WORD_ORDER": word_nouns,
        "CONTEXTUAL_REFERENCE_GAP": retained_pf09_nouns,
        "ERROR_CHECK": pf13_nouns,
        "COMPLETE_SENTENCE_PRODUCTION": pf14_nouns,
        "CONNECTED_SENTENCE_PRODUCTION": pf15_nouns,
    }
    return bool(anchors & sources.get(angle, set()))


def _scene_writing_stages_feasible(
    scene: Mapping[str, Any],
    *,
    phrase_nouns: set[str],
    word_nouns: set[str],
    retained_pf09_nouns: set[str],
    pf13_nouns: set[str],
    pf14_nouns: set[str],
    pf15_nouns: set[str],
) -> bool:
    anchors = set(scene["anchors"])
    available: list[tuple[str, ...]] = []
    for form_ordinal in scene["form_ordinals"]:
        support = u01qb09.support_for_form(int(form_ordinal))
        angles = tuple(
            angle
            for angle in u01qb09.SUPPORT_PROFILES[support]["candidates"]["WRITING"]
            if _writing_angle_available(
                angle,
                anchors=anchors,
                phrase_nouns=phrase_nouns,
                word_nouns=word_nouns,
                retained_pf09_nouns=retained_pf09_nouns,
                pf13_nouns=pf13_nouns,
                pf14_nouns=pf14_nouns,
                pf15_nouns=pf15_nouns,
            )
        )
        if len(angles) < 2:
            return False
        available.append(angles)
    if len(available) == 1:
        return True
    first, second = available
    return any(
        len([angle for angle in second if angle not in first_pair]) >= 2
        for first_pair in itertools.combinations(first, 2)
    )


def _context_assignment(
    *,
    context: str,
    quotas: Mapping[str, int],
    grouped_by_family: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    scenes: Sequence[Mapping[str, Any]],
    phrase_nouns: set[str],
    word_nouns: set[str],
) -> dict[str, tuple[tuple[str, str], ...]] | None:
    pair_lists = {
        family: tuple(_pair_key(row) for row in grouped_by_family[family].get(context, []))
        for family in REPLACEMENT_FAMILIES
    }
    q04, q05, q08, q09 = (quotas[family] for family in REPLACEMENT_FAMILIES)
    if any(len(pair_lists[family]) < quotas[family] for family in REPLACEMENT_FAMILIES):
        return None
    if q04 + q05 + q08 > len(set(pair_lists[READING_REPLACEMENT_FAMILIES[0]])):
        return None
    if len(pair_lists[READING_REPLACEMENT_FAMILIES[1]]) - q05 < U01QB12_REFERENCE_CONTEXT_QUOTA[context]:
        return None
    legal_nouns = {pair[1] for pair in pair_lists[WRITING_CONTEXT_REPLACEMENT_FAMILY]}

    for pf04 in itertools.combinations(pair_lists[READING_REPLACEMENT_FAMILIES[0]], q04):
        used04 = set(pf04)
        pf05_pool = [pair for pair in pair_lists[READING_REPLACEMENT_FAMILIES[1]] if pair not in used04]
        for pf05 in itertools.combinations(pf05_pool, q05):
            used05 = used04 | set(pf05)
            pf08_pool = [pair for pair in pair_lists[READING_REPLACEMENT_FAMILIES[2]] if pair not in used05]
            for pf08 in itertools.combinations(pf08_pool, q08):
                pf13_nouns = {pair[1] for pair in pf04}
                pf14_nouns = {pair[1] for pair in (*pf05, *pf08)}
                for pf09 in itertools.combinations(pair_lists[WRITING_CONTEXT_REPLACEMENT_FAMILY], q09):
                    pf15_nouns = {pair[1] for pair in pf09}
                    retained_pf09_nouns = legal_nouns - pf15_nouns
                    if all(
                        _scene_writing_stages_feasible(
                            scene,
                            phrase_nouns=phrase_nouns,
                            word_nouns=word_nouns,
                            retained_pf09_nouns=retained_pf09_nouns,
                            pf13_nouns=pf13_nouns,
                            pf14_nouns=pf14_nouns,
                            pf15_nouns=pf15_nouns,
                        )
                        for scene in scenes
                    ):
                        return {
                            READING_REPLACEMENT_FAMILIES[0]: tuple(pf04),
                            READING_REPLACEMENT_FAMILIES[1]: tuple(pf05),
                            READING_REPLACEMENT_FAMILIES[2]: tuple(pf08),
                            WRITING_CONTEXT_REPLACEMENT_FAMILY: tuple(pf09),
                        }
    return None


_ASSIGNMENT_CACHE: dict[str, dict[str, tuple[tuple[str, str], ...]]] | None = None
_QUOTA_CACHE: dict[str, dict[str, int]] | None = None


def _production_assignment_by_context(items: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    global _ASSIGNMENT_CACHE, _QUOTA_CACHE
    if _ASSIGNMENT_CACHE is not None:
        return deepcopy(_ASSIGNMENT_CACHE)

    grouped = {family: _group_context_rows(items, family) for family in REPLACEMENT_FAMILIES}
    scenes = _scene_requirements()
    phrase_nouns, word_nouns = _fixed_phrase_word_nouns()
    canonical_contexts = list(u01qb10.seed.CONTEXT_IDS)
    context_order = sorted(
        canonical_contexts,
        key=lambda context: (
            -sum(len(row["form_ordinals"]) for row in scenes.get(context, [])),
            -len(scenes.get(context, [])),
            context,
        ),
    )
    quota_preference = (3, 2, 4, 1)
    assignment_cache: dict[tuple[str, tuple[int, int, int, int]], dict[str, tuple[tuple[str, str], ...]] | None] = {}
    chosen: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {}
    chosen_quotas: dict[str, dict[str, int]] = {}
    remaining = {family: CONTEXT_REPLACEMENT_COUNT for family in REPLACEMENT_FAMILIES}

    def solve(index: int) -> bool:
        if index == len(context_order):
            return all(value == 0 for value in remaining.values())
        context = context_order[index]
        future_count = len(context_order) - index - 1
        for values in itertools.product(quota_preference, repeat=4):
            quotas = dict(zip(REPLACEMENT_FAMILIES, values))
            legal = True
            for family, quota in quotas.items():
                after = remaining[family] - quota
                if quota < MIN_CONTEXT_QUOTA or quota > MAX_CONTEXT_QUOTA or after < 0:
                    legal = False
                    break
                if not (
                    MIN_CONTEXT_QUOTA * future_count
                    <= after
                    <= MAX_CONTEXT_QUOTA * future_count
                ):
                    legal = False
                    break
            if not legal:
                continue
            key = (context, values)
            if key not in assignment_cache:
                assignment_cache[key] = _context_assignment(
                    context=context,
                    quotas=quotas,
                    grouped_by_family=grouped,
                    scenes=scenes.get(context, []),
                    phrase_nouns=phrase_nouns,
                    word_nouns=word_nouns,
                )
            local = assignment_cache[key]
            if local is None:
                continue
            chosen[context] = local
            chosen_quotas[context] = quotas
            for family, quota in quotas.items():
                remaining[family] -= quota
            if solve(index + 1):
                return True
            for family, quota in quotas.items():
                remaining[family] += quota
            del chosen[context]
            del chosen_quotas[context]
        return False

    if not solve(0):
        raise ContextStratifiedFullFixError("GLOBAL_CONTEXT_QUOTA_AND_WRITING_STAGE_ASSIGNMENT_UNSAT")
    _ASSIGNMENT_CACHE = {context: chosen[context] for context in canonical_contexts}
    _QUOTA_CACHE = {context: chosen_quotas[context] for context in canonical_contexts}
    return deepcopy(_ASSIGNMENT_CACHE)


def _quota_by_family() -> dict[str, dict[str, int]]:
    if _QUOTA_CACHE is None:
        _production_assignment_by_context(u01qb10.seed_bank()[1])
    assert _QUOTA_CACHE is not None
    return {
        family: {
            context: int(_QUOTA_CACHE[context][family])
            for context in u01qb10.seed.CONTEXT_IDS
        }
        for family in REPLACEMENT_FAMILIES
    }


def context_stratified_u01qb10_replacement_sources(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    assignment = _production_assignment_by_context(items)
    grouped = {family: _group_context_rows(items, family) for family in REPLACEMENT_FAMILIES}
    result = {family: [] for family in REPLACEMENT_FAMILIES}
    for context in u01qb10.seed.CONTEXT_IDS:
        for family in REPLACEMENT_FAMILIES:
            by_pair = {_pair_key(row): row for row in grouped[family].get(context, [])}
            for pair in assignment[context][family]:
                row = by_pair.get(pair)
                if row is None:
                    raise ContextStratifiedFullFixError(
                        f"ASSIGNED_SOURCE_ROW_MISSING:{family}:{context}:{pair[1]}"
                    )
                result[family].append(deepcopy(row))
    for family, rows in result.items():
        if len(rows) != CONTEXT_REPLACEMENT_COUNT:
            raise ContextStratifiedFullFixError(f"REPLACEMENT_COUNT_INVALID:{family}:{len(rows)}")
    reading_pairs = [
        _pair_key(row)
        for family in READING_REPLACEMENT_FAMILIES
        for row in result[family]
    ]
    if len(reading_pairs) != len(set(reading_pairs)):
        raise ContextStratifiedFullFixError("READING_CONTEXT_NOUN_RETIREMENT_OVERLAP")
    return result


def context_stratified_u01qb12_reference_sources(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_context_rows(items, u01qb12.SOURCE_REFERENCE_FAMILY)
    selected: list[dict[str, Any]] = []
    for context in u01qb10.seed.CONTEXT_IDS:
        need = U01QB12_REFERENCE_CONTEXT_QUOTA[context]
        rows = grouped.get(context, [])
        if len(rows) < need:
            raise ContextStratifiedFullFixError(
                f"REFERENCE_CONTEXT_QUOTA_CAPACITY_INVALID:{context}:need={need}:available={len(rows)}"
            )
        selected.extend(rows[:need])
    if len(selected) != REFERENCE_REPLACEMENT_COUNT:
        raise ContextStratifiedFullFixError(f"REFERENCE_REPLACEMENT_COUNT_INVALID:{len(selected)}")
    return selected


def _tag_u01qb15(item: Mapping[str, Any], *, stage: str) -> dict[str, Any]:
    row = deepcopy(dict(item))
    refs = list(row.get("source_refs") or [])
    refs.append(
        {
            "source_type": "U01QB15_CONTEXT_STRATIFIED_SUPERSEDING_SELECTION",
            "task_id": TASK_ID,
            "stage": stage,
            "historical_constructor_identity_preserved": True,
        }
    )
    row["source_refs"] = refs
    proposal = dict(row.get("admission_proposal") or {})
    proposal["reason_codes"] = list(
        dict.fromkeys([*(proposal.get("reason_codes") or []), "U01QB15_CONTEXT_STRATIFIED_SOURCE_SELECTION"])
    )
    row["admission_proposal"] = proposal
    row["semantic_signature"] = u01qb10.seed.digest(
        {
            "u01qb15": True,
            "stage": stage,
            "family": row["pattern_family_id"],
            "source_item": row.get("reconciliation_source_item_id"),
            "context": row.get("context_id"),
            "slots": row.get("lexical_slots"),
            "prompt": row.get("prompt"),
            "stimulus": row.get("stimulus"),
            "answer": row.get("correct_answer"),
            "support": row.get("support_level"),
        }
    )
    return row


def build_context_stratified_u01qb10_items() -> tuple[
    dict[str, Any], list[dict[str, Any]], dict[str, list[dict[str, Any]]]
]:
    approved_seed, seed_items = u01qb10.seed_bank()
    replacements = context_stratified_u01qb10_replacement_sources(seed_items)
    retired_ids = {str(row["item_id"]) for rows in replacements.values() for row in rows}
    retained = [deepcopy(dict(row)) for row in seed_items if str(row["item_id"]) not in retired_ids]
    added: list[dict[str, Any]] = []
    for source_family, rows in replacements.items():
        replacement_family = u01qb10.REPLACEMENT_PLAN[source_family][1]
        for row in rows:
            added.append(
                _tag_u01qb15(
                    u01qb10._production_item(row, replacement_family),
                    stage="U01QB10_CONTEXT_STRATIFIED_REPLACEMENT",
                )
            )
    items = sorted([*retained, *added], key=lambda row: str(row["item_id"]))
    if len(retired_ids) != EXPECTED_U01QB10_RETIRED or len(added) != EXPECTED_U01QB10_RETIRED:
        raise ContextStratifiedFullFixError("U01QB10_COUNT_COMPONENT_INVALID")
    if len(items) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError(f"U01QB10_BASE_COUNT_INVALID:{len(items)}")
    if len({str(row["item_id"]) for row in items}) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError("U01QB10_DUPLICATE_ITEM_ID")
    if len({str(row["semantic_signature"]) for row in items}) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError("U01QB10_DUPLICATE_SEMANTIC_SIGNATURE")
    return approved_seed, items, replacements


def build_context_stratified_u01qb12_items() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _approved, intermediate, replacements = build_context_stratified_u01qb10_items()
    reference_sources = context_stratified_u01qb12_reference_sources(intermediate)
    phrase_sources = u01qb12._phrase_sources(intermediate)
    retired_ids = {str(row["item_id"]) for row in [*reference_sources, *phrase_sources]}
    retained = [deepcopy(dict(row)) for row in intermediate if str(row["item_id"]) not in retired_ids]
    added = [
        _tag_u01qb15(
            u01qb12._reference_evidence_item(row, index),
            stage="U01QB12_CONTEXT_STRATIFIED_REFERENCE_REPLACEMENT",
        )
        for index, row in enumerate(reference_sources, start=1)
    ]
    added.extend(
        _tag_u01qb15(
            u01qb12._phrase_construction_item(row, index),
            stage="U01QB12_PHRASE_REPLACEMENT_PRESERVED",
        )
        for index, row in enumerate(phrase_sources, start=1)
    )
    final_items = sorted([*retained, *added], key=lambda row: str(row["item_id"]))
    if len(retired_ids) != EXPECTED_U01QB12_RETIRED or len(added) != EXPECTED_U01QB12_RETIRED:
        raise ContextStratifiedFullFixError("U01QB12_COUNT_COMPONENT_INVALID")
    if len(final_items) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError(f"FINAL_BASE_COUNT_INVALID:{len(final_items)}")
    if len({str(row["item_id"]) for row in final_items}) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError("FINAL_DUPLICATE_ITEM_ID")
    if len({str(row["semantic_signature"]) for row in final_items}) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError("FINAL_DUPLICATE_SEMANTIC_SIGNATURE")
    return final_items, {
        "u01qb10_replacements": replacements,
        "u01qb12_reference_sources": reference_sources,
        "u01qb12_phrase_sources": phrase_sources,
    }


def _base_catalog(items: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    catalog: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        catalog[str(item["skill"])].append(
            {
                "item_id": str(item["item_id"]),
                "skill": str(item["skill"]),
                "pattern_family_id": str(item["pattern_family_id"]),
                "private_item_json": canonical(item),
            }
        )
    return dict(catalog)


def base_only_scene_runtime_capacity_proof(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(items) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError(f"BASE_ITEM_COUNT_INVALID:{len(items)}")
    rotation = u01qb14r1.rematerialize_rotation(_legacy_rotation_from_authorities())
    semantics = u01qb14r1.tolerant_scene_semantic_index()
    catalog = _base_catalog(items)
    prior_angles: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    session_count = 0
    activity_count = 0
    support_counts: Counter[str] = Counter()
    for form in rotation["forms"]:
        support = u01qb09.support_for_form(int(form["form_ordinal"]))
        support_counts[support] += 1
        scene_infos: list[dict[str, Any]] = []
        for slot in form["scene_slots"]:
            ref = str(slot["scene_ref_id"])
            anchors = {
                str(value).casefold()
                for value in (semantics.get(ref) or {}).get("anchors") or []
            }
            if not anchors:
                raise ContextStratifiedFullFixError(f"CAPACITY_SCENE_ANCHORS_MISSING:{ref}")
            scene_infos.append(
                {
                    "scene_ref_id": ref,
                    "anchors": anchors,
                    "situation_family": str(slot["situation_family"]),
                }
            )
        for skill in ("READING", "WRITING", "SPEAKING"):
            chosen = runtime_patch._solve_form_skill(
                support=support,
                skill=skill,
                scene_infos=scene_infos,
                prior_angles=prior_angles,
                catalog=catalog,
            )
            expected = 1 if skill == "SPEAKING" else 2
            for scene in scene_infos:
                ref = str(scene["scene_ref_id"])
                angles = tuple(chosen[ref])
                if len(angles) != expected:
                    raise ContextStratifiedFullFixError(
                        f"CAPACITY_ANGLE_COUNT_INVALID:{form['form_id']}:{ref}:{skill}"
                    )
                prior_angles[ref][skill].update(angles)
                activity_count += len(angles)
            session_count += 1
    projection = rotation["runtime_bindability_projection"]
    if (
        projection["cumulative_scene_world_count"] != EXPECTED_SCENE_WORLD_COUNT
        or projection["unit_runtime_bindable_scene_count"] != EXPECTED_BINDABLE_SCENE_COUNT
        or tuple(projection["deferred_scene_refs"]) != EXPECTED_DEFERRED_SCENES
    ):
        raise ContextStratifiedFullFixError("SCENE_PROJECTION_DENOMINATOR_INVALID")
    if session_count != EXPECTED_SKILL_SESSION_COUNT or activity_count != EXPECTED_ACTIVITY_COUNT:
        raise ContextStratifiedFullFixError(
            f"BASE_CAPACITY_DENOMINATOR_INVALID:{session_count}:{activity_count}"
        )
    return {
        "proof_mode": "FINAL_288_BASE_ONLY_NO_REAL62_ASSISTANCE",
        "base_item_count": EXPECTED_BASE_COUNT,
        "cumulative_scene_world_count": EXPECTED_SCENE_WORLD_COUNT,
        "runtime_bindable_scene_count": EXPECTED_BINDABLE_SCENE_COUNT,
        "deferred_scene_refs": list(EXPECTED_DEFERRED_SCENES),
        "form_count": EXPECTED_FORM_COUNT,
        "skill_session_count": session_count,
        "verified_activity_count": activity_count,
        "all_36_skill_sessions_distinct_item_capacity_proven": True,
        "real62_used_for_capacity_proof": False,
        "support_form_counts": dict(sorted(support_counts.items())),
    }


def _context_family_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    tracked = {
        *READING_REPLACEMENT_FAMILIES,
        u01qb12.PF16,
        WRITING_CONTEXT_REPLACEMENT_FAMILY,
        u01qb10.PF13,
        u01qb10.PF14,
        u01qb10.PF15,
    }
    result: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        family = str(item["pattern_family_id"])
        context, _noun = _pair_key(item)
        if family in tracked and context:
            result[family][context] += 1
    return {family: dict(sorted(counts.items())) for family, counts in sorted(result.items())}


def _reading_pair_survival(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    tracked = {*READING_REPLACEMENT_FAMILIES, u01qb12.PF16}
    counts: Counter[tuple[str, str]] = Counter()
    for item in items:
        if str(item["pattern_family_id"]) in tracked:
            pair = _pair_key(item)
            if pair[0] and pair[1]:
                counts[pair] += 1
    seed_pairs = {
        _pair_key(row)
        for row in u01qb10.seed_bank()[1]
        if row.get("pattern_family_id") == READING_REPLACEMENT_FAMILIES[0]
    }
    missing = sorted(pair for pair in seed_pairs if counts[pair] < 2)
    if missing:
        raise ContextStratifiedFullFixError(
            "READING_CONTEXT_NOUN_SURVIVAL_BELOW_TWO:"
            + ",".join(f"{context}:{noun}" for context, noun in missing)
        )
    return {
        "approved_context_noun_pair_count": len(seed_pairs),
        "minimum_surviving_context_bound_reading_identities_per_pair": min(counts[pair] for pair in seed_pairs),
        "all_pairs_retain_at_least_two_context_bound_reading_identities": True,
    }


def build_payload() -> dict[str, Any]:
    final_items, lineage = build_context_stratified_u01qb12_items()
    replacements = lineage["u01qb10_replacements"]
    reading_retired_pairs = [
        _pair_key(row)
        for family in READING_REPLACEMENT_FAMILIES
        for row in replacements[family]
    ]
    if len(reading_retired_pairs) != len(set(reading_retired_pairs)):
        raise ContextStratifiedFullFixError("READING_CONTEXT_NOUN_RETIREMENT_OVERLAP")
    family_counts = dict(sorted(Counter(str(row["pattern_family_id"]) for row in final_items).items()))
    skill_counts = dict(sorted(Counter(str(row["skill"]) for row in final_items).items()))
    if family_counts != EXPECTED_FINAL_FAMILY_COUNTS:
        raise ContextStratifiedFullFixError("FINAL_FAMILY_COUNTS_INVALID")
    if skill_counts != EXPECTED_FINAL_SKILL_COUNTS:
        raise ContextStratifiedFullFixError("FINAL_SKILL_COUNTS_INVALID")
    assignment = _production_assignment_by_context(u01qb10.seed_bank()[1])
    quotas = _quota_by_family()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "bank_identity": {
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "canonical_revision": CANONICAL_REVISION,
            "supersedes_selection_policy": [u01qb10.CANONICAL_REVISION, u01qb12.CANONICAL_REVISION],
            "historical_task_identity_rewritten": False,
            "second_question_bank_created": False,
        },
        "source_identity": {
            "seed_task_id": u01qb10.seed.TASK_ID,
            "u01qb10_constructor_task_id": u01qb10.TASK_ID,
            "u01qb12_constructor_task_id": u01qb12.TASK_ID,
        },
        "count_preservation": {
            "base_item_count": EXPECTED_BASE_COUNT,
            "u01qb10_retired_and_added": EXPECTED_U01QB10_RETIRED,
            "u01qb12_retired_and_added": EXPECTED_U01QB12_RETIRED,
            "unchanged_real62_extension_count": EXPECTED_EXTENSION_COUNT,
            "projected_runtime_total_count": EXPECTED_RUNTIME_COUNT,
        },
        "u01qb10_context_stratified_replacement": {
            "replacement_count_per_family": CONTEXT_REPLACEMENT_COUNT,
            "minimum_context_quota": MIN_CONTEXT_QUOTA,
            "maximum_context_quota": MAX_CONTEXT_QUOTA,
            "context_quota_by_family": quotas,
            "reading_family_ids": list(READING_REPLACEMENT_FAMILIES),
            "reading_retired_context_noun_pairs_unique": True,
            "reading_retired_pair_count": len(reading_retired_pairs),
            "scene_writing_stage_assignment_proven": True,
            "assignment_pairs_by_context": {
                context: {
                    family: [list(pair) for pair in pairs]
                    for family, pairs in families.items()
                }
                for context, families in assignment.items()
            },
            "replacement_source_ids_by_family": {
                family: [str(row["item_id"]) for row in rows]
                for family, rows in replacements.items()
            },
        },
        "u01qb12_context_stratified_reference_replacement": {
            "replacement_count": REFERENCE_REPLACEMENT_COUNT,
            "context_quota": deepcopy(U01QB12_REFERENCE_CONTEXT_QUOTA),
            "source_item_ids": [str(row["item_id"]) for row in lineage["u01qb12_reference_sources"]],
            "replacement_family_id": u01qb12.PF16,
        },
        "distribution_counts": {
            "family": family_counts,
            "skill": skill_counts,
            "context_family": _context_family_counts(final_items),
        },
        "reading_context_noun_survival": _reading_pair_survival(final_items),
        "per_scene_runtime_capacity": base_only_scene_runtime_capacity_proof(final_items),
        "reconciled_items": [deepcopy(dict(row)) for row in final_items],
        "boundaries": {
            "question_bank_total_expanded": False,
            "real62_extension_modified": False,
            "new_scene_authored": False,
            "second_planner_created": False,
            "second_runtime_created": False,
            "parallel_database_created": False,
            "parallel_scoring_created": False,
            "speaking_capture_enabled": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = digest(payload)
    return payload


def build_candidate() -> dict[str, Any]:
    payload = build_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "seed_task_id": u01qb10.seed.TASK_ID,
            "u01qb10_constructor_task_id": u01qb10.TASK_ID,
            "u01qb12_constructor_task_id": u01qb12.TASK_ID,
            "canonical_revision": CANONICAL_REVISION,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as validator
    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate, validation_receipts=[receipt], decision_ref=DECISION_REF, producer_id=TASK_ID
    )


def _migrate_stage(
    database: Path,
    *,
    desired_items: Sequence[Mapping[str, Any]],
    expected_delta: int,
    archive_stage: str,
) -> dict[str, Any]:
    desired_by_id = {str(row["item_id"]): deepcopy(dict(row)) for row in desired_items}
    desired_ids = set(desired_by_id)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(database))
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in (
            "metadata", "lesson_catalog", "lesson_assets", "response_contracts", "response_attempts",
            "scoring_results", "u01qb02_metadata", "u01qb02_item_catalog", "u01qb02_session_plans",
            "u01qb02_session_items", "u01qb02_item_exposures", "razq01e_metadata", "razq01e_extension_items",
        ):
            u01qb11._require_table(connection, table)
        extension_before = u01qb11._extension_snapshot(connection)
        extension_ids = set(extension_before["item_ids"])
        current_ids = {str(row[0]) for row in connection.execute("SELECT item_id FROM u01qb02_item_catalog")}
        current_base = current_ids - extension_ids
        if len(current_base) != EXPECTED_BASE_COUNT or len(current_ids) != EXPECTED_RUNTIME_COUNT:
            raise ContextStratifiedFullFixError(
                f"{archive_stage}_PRE_MIGRATION_DENOMINATOR_INVALID:{len(current_base)}:{len(current_ids)}"
            )
        retired = current_base - desired_ids
        missing = desired_ids - current_base
        if len(retired) != expected_delta or len(missing) != expected_delta:
            raise ContextStratifiedFullFixError(
                f"{archive_stage}_DELTA_INVALID:{len(retired)}:{len(missing)}"
            )
        if archive_stage == "U01QB10":
            connection.executescript(u01qb11.ARCHIVE_SQL)
            affected_sessions, archived_records = u01qb11._archive_affected_history(
                connection, retired, archived_at=u01qb11.utc_now()
            )
        elif archive_stage == "U01QB12":
            connection.executescript(u01qb12.ARCHIVE_SQL)
            affected_sessions, archived_records = u01qb12._archive_affected_history(
                connection, retired, archived_at=u01qb12.utc_now()
            )
        else:
            raise ContextStratifiedFullFixError(f"UNKNOWN_MIGRATION_STAGE:{archive_stage}")
        if retired:
            placeholders = ",".join("?" for _ in retired)
            connection.execute(
                f"DELETE FROM u01qb02_item_catalog WHERE item_id IN ({placeholders})",
                tuple(sorted(retired)),
            )
        for item_id in sorted(missing):
            u01qb11._register_base_item(connection, desired_by_id[item_id])
        extension_after = u01qb11._extension_snapshot(connection)
        if extension_after["identity_sha256"] != extension_before["identity_sha256"]:
            raise ContextStratifiedFullFixError(f"{archive_stage}_REAL62_IDENTITY_CHANGED")
        total = int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0])
        extension_count = int(connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0])
        if (total - extension_count, extension_count, total) != (
            EXPECTED_BASE_COUNT, EXPECTED_EXTENSION_COUNT, EXPECTED_RUNTIME_COUNT
        ):
            raise ContextStratifiedFullFixError(f"{archive_stage}_POST_MIGRATION_DENOMINATOR_INVALID")
    return {
        "stage": archive_stage,
        "retired_item_count": len(retired),
        "added_item_count": len(missing),
        "affected_session_count": affected_sessions,
        "archived_runtime_history_record_count": archived_records,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "real62_extension_identity_sha256": extension_after["identity_sha256"],
    }


def migrate_fresh_legacy_runtime(database: Path, *, approved_artifact_sha256: str) -> dict[str, Any]:
    _seed, intermediate, _replacements = build_context_stratified_u01qb10_items()
    final_items, _lineage = build_context_stratified_u01qb12_items()
    stage_u10 = _migrate_stage(
        Path(database), desired_items=intermediate,
        expected_delta=EXPECTED_U01QB10_RETIRED, archive_stage="U01QB10"
    )
    replay_u11 = u01qb11.replay_474(Path(database))
    stage_u12 = _migrate_stage(
        Path(database), desired_items=final_items,
        expected_delta=EXPECTED_U01QB12_RETIRED, archive_stage="U01QB12"
    )
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        extension = u01qb11._extension_snapshot(connection)
        combined_sha = digest(
            {
                "base_question_bank_artifact_sha256": approved_artifact_sha256,
                "content_extension_artifact_sha256": extension["artifact_sha256"],
            }
        )
        connection.execute("CREATE TABLE IF NOT EXISTS u01qb12_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS u01qb15_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "base_source_bank_artifact_sha256": approved_artifact_sha256,
                "source_bank_artifact_sha256": combined_sha,
                "approved_item_count": str(EXPECTED_BASE_COUNT),
                "razq01e_extension_artifact_sha256": str(extension["artifact_sha256"]),
                "razq01e_extension_item_count": str(EXPECTED_EXTENSION_COUNT),
                "razq01e_combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "u01qb15_task_id": TASK_ID,
                "u01qb15_base_revision": CANONICAL_REVISION,
            }.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO razq01e_metadata(key,value) VALUES(?,?)",
            {
                "base_item_count": str(EXPECTED_BASE_COUNT),
                "combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "base_source_bank_artifact_sha256": approved_artifact_sha256,
                "combined_source_bank_sha256": combined_sha,
            }.items(),
        )
        common_meta = {
            "base_revision": CANONICAL_REVISION,
            "base_artifact_sha256": approved_artifact_sha256,
            "extension_artifact_sha256": str(extension["artifact_sha256"]),
            "combined_source_bank_sha256": combined_sha,
            "base_item_count": str(EXPECTED_BASE_COUNT),
            "extension_item_count": str(EXPECTED_EXTENSION_COUNT),
            "runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb12_metadata(key,value) VALUES(?,?)",
            {"task_id": u01qb12.TASK_ID, "schema_version": u01qb12.SCHEMA_VERSION,
             "validation_status": u01qb12.PASS_STATUS, **common_meta}.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb15_metadata(key,value) VALUES(?,?)",
            {"task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
             "validation_status": PASS_STATUS, "canonical_revision": CANONICAL_REVISION,
             **common_meta}.items(),
        )
    replay_u12 = u01qb12.replay_474(Path(database))
    return {
        "validation_status": PASS_STATUS,
        "database": str(database),
        "u01qb11_context_stratified_stage": stage_u10,
        "u01qb11_replay_474": replay_u11,
        "u01qb12_context_stratified_stage": stage_u12,
        "u01qb12_replay_474": replay_u12,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "per_scene_runtime_capacity": base_only_scene_runtime_capacity_proof(final_items),
        "real62_extension_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def build_candidate() -> dict[str, Any]:
    payload = build_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "seed_task_id": u01qb10.seed.TASK_ID,
            "u01qb10_constructor_task_id": u01qb10.TASK_ID,
            "u01qb12_constructor_task_id": u01qb12.TASK_ID,
            "canonical_revision": CANONICAL_REVISION,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as validator
    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate, validation_receipts=[receipt], decision_ref=DECISION_REF, producer_id=TASK_ID
    )


def materialize(
    *, candidate_path: Path, approved_path: Path, report_path: Path,
    database: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as validator
    approval = validator.validate_approved(candidate, approved)
    if approval["error_count"]:
        raise ContextStratifiedFullFixError("U01QB15_APPROVED_INVALID:" + "|".join(approval["errors"]))
    migration = (
        migrate_fresh_legacy_runtime(database, approved_artifact_sha256=str(approved["artifact_sha256"]))
        if database is not None else None
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "approved_artifact_sha256": str(approved["artifact_sha256"]),
        "approval_validation": approval,
        "runtime_migration_executed": database is not None,
        "runtime_migration": migration,
        "next_short_step": NEXT_SHORT_STEP,
    }
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args(argv)
    try:
        _candidate, approved, report = materialize(
            candidate_path=args.candidate.resolve(),
            approved_path=args.approved.resolve(),
            report_path=args.report.resolve(),
            database=args.database.resolve(strict=True) if args.database else None,
        )
    except Exception as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB15_CONTEXT_STRATIFIED_QUESTION_BANK_FULLFIX")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    capacity = payload["per_scene_runtime_capacity"]
    print(f"STATUS={PASS_STATUS}")
    print(f"BASE_ITEMS={payload['count_preservation']['base_item_count']}")
    print(f"PROJECTED_RUNTIME_TOTAL={payload['count_preservation']['projected_runtime_total_count']}")
    print("U01QB10_CONTEXT_QUOTA_BY_FAMILY=" + canonical(payload["u01qb10_context_stratified_replacement"]["context_quota_by_family"]))
    print("U01QB12_REFERENCE_CONTEXT_QUOTA=" + canonical(payload["u01qb12_context_stratified_reference_replacement"]["context_quota"]))
    print(f"BASE_ONLY_SKILL_SESSIONS_PROVEN={capacity['skill_session_count']}")
    print(f"BASE_ONLY_ACTIVITIES_PROVEN={capacity['verified_activity_count']}")
    print(f"RUNTIME_MIGRATION_EXECUTED={report['runtime_migration_executed']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
