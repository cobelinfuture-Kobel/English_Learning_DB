#!/usr/bin/env python3
"""Reconcile Unit01 production capacity from the admitted 3805-sentence pool.

R2R2 is a count-preserving successor over the already-active U01QB12 runtime.
It reads the installed 240-row U01QB13 blueprint, derives the exact 48 scored
Writing production requirements, and rematerializes exactly 48 PF13/PF14/PF15
items from the already-admitted U01SA05R2 sentence capability index.

The source database is never mutated. A SQLite backup is created first; only
the disposable clone is reconciled. The 186 Real62 extension rows, M3 learner
state, M6 attempts/scoring, Unit02-24, A2, and Speaking scoring remain untouched.
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
from typing import Any, Callable, Mapping, Sequence

from ulga.builders import _u01qb11_runtime_migration_474_replay_impl as u11
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as scene_authority
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u10
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB18H-R2R2_"
    "Unit01SentencePoolDrivenProductionCapacityReconciliation"
)
SCHEMA_VERSION = (
    "a1fs.v1.u01qb18h.r2r2."
    "unit01_sentence_pool_driven_production_capacity_reconciliation.v1"
)
PASS_STATUS = (
    "PASS_A1FS_V1_U01QB18H_R2R2_"
    "UNIT01_SENTENCE_POOL_DRIVEN_PRODUCTION_CAPACITY_RECONCILIATION"
)
DECISION_REF = "OPERATOR_APPROVAL:2026-08-20:U01QB18H-R2R2"
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB18H-R2R2_"
    "ActualTwelveFormFreshReplayAndPdfReacceptance"
)

EXPECTED_SENTENCE_POOL_TOTAL = 3805
EXPECTED_BLUEPRINT_ACTIVITY_COUNT = 240
EXPECTED_PRODUCTION_REQUIREMENT_COUNT = 48
EXPECTED_BASE_COUNT = 288
EXPECTED_EXTENSION_COUNT = 186
EXPECTED_RUNTIME_COUNT = 474

PRODUCTION_ANGLE_TO_FAMILY = {
    "ERROR_CHECK": u10.PF13,
    "COMPLETE_SENTENCE_PRODUCTION": u10.PF14,
    "CONNECTED_SENTENCE_PRODUCTION": u10.PF15,
}
EXPECTED_PRODUCTION_FAMILY_COUNTS = {
    u10.PF13: 12,
    u10.PF14: 24,
    u10.PF15: 12,
}
SOURCE_TASK_ID = (
    "A1FS-V1-U01SA05R2_"
    "Full3805SentencePoolCapabilityCoverageAndUnit01QuestionBankResidualBindingReconciliation"
)
SOURCE_STATUS = "CAPABILITY_CLASSIFIED"
METADATA_TABLE = "u01qb18h_r2r2_metadata"

_SOURCE_KIND_RANK = {
    "REAL_SOURCE": 0,
    "CANONICAL_SCENE_DERIVED": 1,
    "MODEL/TEMPLATE_DERIVED": 2,
}


class SentencePoolCapacityError(ValueError):
    """Fail-closed sentence-pool / QuestionBank reconciliation error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SentencePoolCapacityError(f"SENTENCE_POOL_UNREADABLE:{path}:{exc}") from exc


def load_sentence_pool(path: Path) -> dict[str, Any]:
    value = read_json(Path(path))
    if not isinstance(value, Mapping):
        raise SentencePoolCapacityError("SENTENCE_POOL_OBJECT_REQUIRED")
    if str(value.get("task_id") or "") != SOURCE_TASK_ID:
        raise SentencePoolCapacityError(
            f"SENTENCE_POOL_TASK_INVALID:{value.get('task_id')}"
        )
    if str(value.get("status") or "") != SOURCE_STATUS:
        raise SentencePoolCapacityError(
            f"SENTENCE_POOL_STATUS_INVALID:{value.get('status')}"
        )
    profiles = value.get("profiles")
    if not isinstance(profiles, list):
        raise SentencePoolCapacityError("SENTENCE_POOL_PROFILES_REQUIRED")
    if int(value.get("sentence_pool_total") or 0) != EXPECTED_SENTENCE_POOL_TOTAL:
        raise SentencePoolCapacityError(
            f"SENTENCE_POOL_TOTAL_INVALID:{value.get('sentence_pool_total')}"
        )
    if len(profiles) != EXPECTED_SENTENCE_POOL_TOTAL:
        raise SentencePoolCapacityError(
            f"SENTENCE_POOL_PROFILE_COUNT_INVALID:{len(profiles)}"
        )
    seen: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, Mapping):
            raise SentencePoolCapacityError("SENTENCE_PROFILE_OBJECT_REQUIRED")
        sentence_id = str(profile.get("sentence_id") or "")
        if not sentence_id or sentence_id in seen:
            raise SentencePoolCapacityError(
                f"SENTENCE_PROFILE_ID_INVALID:{sentence_id}"
            )
        seen.add(sentence_id)
        if str(profile.get("canonical_admission_status") or "") != "ADMITTED":
            raise SentencePoolCapacityError(
                f"NON_ADMITTED_SENTENCE_LEAKED:{sentence_id}"
            )
    return dict(value)


def _require_table(connection: sqlite3.Connection, table: str) -> None:
    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is None:
        raise SentencePoolCapacityError(f"REQUIRED_TABLE_MISSING:{table}")


def blueprint_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    _require_table(connection, "u01qb13_blueprint_activities")
    rows = [
        dict(row)
        for row in connection.execute(
            """SELECT activity_id,form_id,form_ordinal,scene_ref_id,situation_family,
                      setting,skill,task_angle,support_level,assessment_candidate,
                      pattern_family_ids_json
               FROM u01qb13_blueprint_activities
               ORDER BY form_ordinal,activity_id"""
        )
    ]
    if len(rows) != EXPECTED_BLUEPRINT_ACTIVITY_COUNT:
        raise SentencePoolCapacityError(
            f"BLUEPRINT_ACTIVITY_COUNT_INVALID:{len(rows)}"
        )
    return rows


def production_requirements(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("skill") or "") != "WRITING":
            continue
        task_angle = str(row.get("task_angle") or "")
        family = PRODUCTION_ANGLE_TO_FAMILY.get(task_angle)
        if family is None:
            continue
        allowed = {
            str(value)
            for value in json.loads(str(row.get("pattern_family_ids_json") or "[]"))
            if str(value)
        }
        if family not in allowed:
            raise SentencePoolCapacityError(
                f"BLUEPRINT_PRODUCTION_FAMILY_NOT_ALLOWED:"
                f"{row.get('activity_id')}:{task_angle}:{family}:{sorted(allowed)}"
            )
        requirements.append(
            {
                "activity_id": str(row["activity_id"]),
                "form_id": str(row["form_id"]),
                "form_ordinal": int(row["form_ordinal"]),
                "scene_ref_id": str(row["scene_ref_id"]),
                "situation_family": str(row["situation_family"]),
                "setting": str(row["setting"]),
                "support_level": str(row["support_level"]),
                "assessment_candidate": bool(row["assessment_candidate"]),
                "task_angle": task_angle,
                "pattern_family_id": family,
            }
        )
    counts = Counter(row["pattern_family_id"] for row in requirements)
    if len(requirements) != EXPECTED_PRODUCTION_REQUIREMENT_COUNT:
        raise SentencePoolCapacityError(
            f"PRODUCTION_REQUIREMENT_COUNT_INVALID:{len(requirements)}"
        )
    if dict(counts) != EXPECTED_PRODUCTION_FAMILY_COUNTS:
        raise SentencePoolCapacityError(
            f"PRODUCTION_REQUIREMENT_DISTRIBUTION_INVALID:"
            f"{dict(counts)}:{EXPECTED_PRODUCTION_FAMILY_COUNTS}"
        )
    return requirements


def _active_noun_senses() -> dict[str, str]:
    return {
        str(row["lemma"]).casefold(): str(row["sense"])
        for row in u10.seed.nouns()
    }


def _slot_noun(slot: Mapping[str, Any]) -> str:
    entity = str(slot.get("entity_id") or "").strip().casefold().replace("_", " ")
    if entity:
        return entity
    surface = str(
        slot.get("canonical_surface")
        or slot.get("surface")
        or slot.get("np_surface")
        or ""
    ).strip().casefold()
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", surface)
    return words[-1] if words else ""


def _usable_np_slots(
    profile: Mapping[str, Any],
    active_nouns: Mapping[str, str],
    *,
    first_mention: bool,
) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for raw in profile.get("np_slots") or []:
        if not isinstance(raw, Mapping):
            continue
        slot = dict(raw)
        noun = _slot_noun(slot)
        determiner = str(slot.get("determiner") or "").casefold()
        if noun not in active_nouns:
            continue
        if first_mention and determiner not in {"a", "an"}:
            continue
        if not first_mention and determiner != "the":
            continue
        slot["_noun"] = noun
        slots.append(slot)
    slots.sort(
        key=lambda slot: (
            str(slot.get("semantic_role") or "") != "TARGET",
            str(slot.get("syntactic_role") or "") != "SUBJECT",
            int(slot.get("char_start") or 0),
            str(slot.get("_noun") or ""),
        )
    )
    return slots


def _source_rank(profile: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _SOURCE_KIND_RANK.get(str(profile.get("source_kind") or ""), 9),
        not bool(profile.get("relation_capability")),
        bool(profile.get("legacy_unnormalized")),
        str(profile.get("sentence_id") or ""),
    )


def _profiles_by_scene(
    sentence_pool: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in sentence_pool.get("profiles") or []:
        profile = dict(raw)
        scene_ref = str(profile.get("source_scene_ref") or "")
        if scene_ref:
            result[scene_ref].append(profile)
    for rows in result.values():
        rows.sort(key=_source_rank)
    return result


def _first_mention_options(
    scene_profiles: Sequence[Mapping[str, Any]],
    active_nouns: Mapping[str, str],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for raw in scene_profiles:
        profile = dict(raw)
        if "FIRST_MENTION" not in {
            str(value) for value in profile.get("discourse_capability") or []
        }:
            continue
        if "WRITING" not in {
            str(value) for value in profile.get("task_use_capability") or []
        }:
            continue
        for slot in _usable_np_slots(profile, active_nouns, first_mention=True):
            result.append((profile, slot))
    result.sort(key=lambda pair: (_source_rank(pair[0]), str(pair[1].get("_noun"))))
    return result


def _known_reference_options(
    scene_profiles: Sequence[Mapping[str, Any]],
    active_nouns: Mapping[str, str],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for raw in scene_profiles:
        profile = dict(raw)
        if "KNOWN_REFERENCE_TARGET" not in {
            str(value) for value in profile.get("discourse_capability") or []
        }:
            continue
        for slot in _usable_np_slots(profile, active_nouns, first_mention=False):
            result.append((profile, slot))
    result.sort(key=lambda pair: (_source_rank(pair[0]), str(pair[1].get("_noun"))))
    return result


def _choose_first(
    options: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    usage: Counter[str],
    *,
    scene_ref_id: str,
    activity_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not options:
        raise SentencePoolCapacityError(
            f"FIRST_MENTION_SENTENCE_SUPPLY_GAP:{activity_id}:{scene_ref_id}"
        )
    ranked = sorted(
        options,
        key=lambda pair: (
            usage[str(pair[0]["sentence_id"])],
            _source_rank(pair[0]),
            str(pair[1].get("_noun") or ""),
        ),
    )
    profile, slot = ranked[0]
    usage[str(profile["sentence_id"])] += 1
    return profile, slot


def _choose_pair(
    first_options: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    known_options: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    usage: Counter[str],
    *,
    scene_ref_id: str,
    activity_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    pairs: list[
        tuple[
            dict[str, Any],
            dict[str, Any],
            dict[str, Any],
            dict[str, Any],
        ]
    ] = []
    for first_profile, first_slot in first_options:
        noun = str(first_slot.get("_noun") or "")
        for known_profile, known_slot in known_options:
            if str(known_slot.get("_noun") or "") != noun:
                continue
            if str(first_profile["sentence_id"]) == str(known_profile["sentence_id"]):
                continue
            pairs.append((first_profile, first_slot, known_profile, known_slot))
    if not pairs:
        raise SentencePoolCapacityError(
            f"CONNECTED_SENTENCE_PAIR_SUPPLY_GAP:{activity_id}:{scene_ref_id}"
        )
    pairs.sort(
        key=lambda pair: (
            usage[str(pair[0]["sentence_id"])] + usage[str(pair[2]["sentence_id"])],
            max(
                usage[str(pair[0]["sentence_id"])],
                usage[str(pair[2]["sentence_id"])],
            ),
            _source_rank(pair[0]),
            _source_rank(pair[2]),
            str(pair[1].get("_noun") or ""),
        )
    )
    first_profile, first_slot, known_profile, known_slot = pairs[0]
    usage[str(first_profile["sentence_id"])] += 1
    usage[str(known_profile["sentence_id"])] += 1
    return first_profile, first_slot, known_profile, known_slot


def _internal_unit_pattern(structure: str) -> str:
    if structure == "ADJECTIVE":
        return u10.seed.PATTERN_ADJECTIVE
    if structure == "VERY":
        return u10.seed.PATTERN_VERY
    return u10.seed.PATTERN_NOUN


def _target_egp_rows(structure: str) -> list[str]:
    if structure == "ADJECTIVE":
        return [str(u10.seed.contract.CORE_EGP_ROWS[1])]
    if structure == "VERY":
        return [str(u10.seed.contract.GUIDED_EGP_ROWS[0])]
    return [str(u10.seed.contract.CORE_EGP_ROWS[0])]


def _wrong_determiner(value: str) -> str:
    return "an" if value == "a" else "a"


def _replace_leading_determiner(np_surface: str, determiner: str) -> str:
    value = str(np_surface).strip()
    replaced = re.sub(r"^(?:a|an|the)\b", determiner, value, count=1, flags=re.I)
    return replaced if replaced != value else f"{determiner} {value}".strip()


def _scene_pattern_refs(
    scene_ref_id: str,
    resolver: Callable[[str], Mapping[str, Any]],
) -> list[str]:
    package = resolver(scene_ref_id)
    projection = package.get("unit_language_projection")
    if not isinstance(projection, Mapping):
        raise SentencePoolCapacityError(
            f"SCENE_LANGUAGE_PROJECTION_MISSING:{scene_ref_id}"
        )
    refs = sorted(
        {
            str(value)
            for value in projection.get("eligible_pattern_refs") or []
            if str(value)
        }
    )
    if not refs:
        raise SentencePoolCapacityError(
            f"SCENE_ELIGIBLE_PATTERN_REFS_MISSING:{scene_ref_id}"
        )
    return refs


def _common_item(
    requirement: Mapping[str, Any],
    *,
    primary_profile: Mapping[str, Any],
    primary_slot: Mapping[str, Any],
    source_sentence_ids: Sequence[str],
    source_pool_sha256: str,
    scene_pattern_refs: Sequence[str],
    active_nouns: Mapping[str, str],
) -> dict[str, Any]:
    noun = str(primary_slot.get("_noun") or "")
    if noun not in active_nouns:
        raise SentencePoolCapacityError(
            f"ACTIVE_NOUN_MAPPING_MISSING:{requirement['activity_id']}:{noun}"
        )
    situation_family = str(requirement["situation_family"])
    canonical_context = u13.FAMILY_CANONICAL_CONTEXT.get(situation_family)
    if not canonical_context:
        raise SentencePoolCapacityError(
            f"CANONICAL_CONTEXT_UNMAPPED:{requirement['activity_id']}:{situation_family}"
        )
    modifiers = [
        str(value).casefold()
        for value in primary_slot.get("modifiers") or []
        if str(value)
    ]
    structure = str(primary_slot.get("structure") or "NOUN")
    lexical_slots: dict[str, Any] = {
        "noun": noun,
        "context_id": canonical_context,
    }
    if modifiers:
        lexical_slots["adjective"] = modifiers[-1]
    activity_id = str(requirement["activity_id"])
    item_id = (
        "U01QB18H-R2R2-"
        f"{u10.seed.slug(str(requirement['pattern_family_id']))}-"
        f"{u10.seed.slug(activity_id)}"
    )
    item: dict[str, Any] = {
        "item_id": item_id,
        "unit_id": u10.UNIT_ID,
        "pattern_family_id": str(requirement["pattern_family_id"]),
        "candidate_structure": structure,
        "context_id": canonical_context,
        "production_scene_ref_id": str(requirement["scene_ref_id"]),
        "production_activity_id": activity_id,
        "lexical_slots": lexical_slots,
        "unit_pattern_ids": [_internal_unit_pattern(structure)],
        "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
        "target_egp_row_ids": _target_egp_rows(structure),
        "target_evp_sense_ids": [active_nouns[noun]],
        "target_sentence_ids": [str(value) for value in source_sentence_ids],
        "target_pattern_ids": [str(value) for value in scene_pattern_refs],
        "skill": "WRITING",
        "support_level": str(requirement["support_level"]),
        "learner_visible_capable": True,
        "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
        "assessment_eligible": True,
        "transfer_eligible": str(requirement["support_level"]) == "TRANSFER",
        "reassessment_eligible": True,
        "human_review_required": False,
        "audio_required": False,
        "speaking_capture_enabled": False,
        "runtime_generation_used": False,
        "admission_proposal": {
            "status": "AUTO_APPROVED",
            "reason_codes": [
                "U01SA05R2_ADMITTED_SENTENCE_MATERIALIZATION",
                "U01QB13_EXACT_BLUEPRINT_PRODUCTION_REQUIREMENT",
            ],
        },
        "source_refs": [
            {
                "source_type": "U01SA05R2_ADMITTED_SENTENCE_CAPABILITY",
                "task_id": SOURCE_TASK_ID,
                "sentence_id": str(sentence_id),
                "source_scene_ref": str(requirement["scene_ref_id"]),
                "capability_index_sha256": source_pool_sha256,
            }
            for sentence_id in source_sentence_ids
        ],
        "sentence_pool_source_task_id": SOURCE_TASK_ID,
        "sentence_pool_capability_index_sha256": source_pool_sha256,
        "source_sentence_ids": [str(value) for value in source_sentence_ids],
    }
    return item


def _response_contract(
    *,
    mode: str,
    model_answer: str,
    rubric: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return u10._response_contract(
        mode=mode,
        model_answer=model_answer,
        rubric=rubric,
    )


def _finalize_item(item: dict[str, Any]) -> dict[str, Any]:
    item["semantic_signature"] = u10.seed.digest(
        {
            "family": item["pattern_family_id"],
            "structure": item["candidate_structure"],
            "context": item["context_id"],
            "production_scene_ref_id": item["production_scene_ref_id"],
            "source_sentence_ids": item["source_sentence_ids"],
            "slots": item["lexical_slots"],
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "options": item["options"],
            "answer": item["correct_answer"],
            "task_angle": item["task_angle"],
        }
    )
    return item


def _pf13_item(
    requirement: Mapping[str, Any],
    profile: Mapping[str, Any],
    slot: Mapping[str, Any],
    *,
    source_pool_sha256: str,
    scene_pattern_refs: Sequence[str],
    active_nouns: Mapping[str, str],
) -> dict[str, Any]:
    sentence_id = str(profile["sentence_id"])
    item = _common_item(
        requirement,
        primary_profile=profile,
        primary_slot=slot,
        source_sentence_ids=[sentence_id],
        source_pool_sha256=source_pool_sha256,
        scene_pattern_refs=scene_pattern_refs,
        active_nouns=active_nouns,
    )
    correct_np = str(
        slot.get("np_surface")
        or slot.get("surface")
        or slot.get("canonical_surface")
        or ""
    ).strip()
    determiner = str(slot.get("determiner") or "").casefold()
    wrong_np = _replace_leading_determiner(
        correct_np,
        _wrong_determiner(determiner),
    )
    item.update(
        {
            "question_type": "error_correction",
            "task_angle": "ERROR_CHECK",
            "prompt": "Correct the article in the noun phrase.",
            "stimulus": wrong_np,
            "options": [],
            "correct_answer": correct_np,
            "accepted_answers": [correct_np],
            "scoring_mode": "NORMALIZED_TEXT",
            "human_review_required": False,
            "response_contract": _response_contract(
                mode="NORMALIZED_TEXT",
                model_answer=correct_np,
            ),
        }
    )
    return _finalize_item(item)


def _pf14_item(
    requirement: Mapping[str, Any],
    profile: Mapping[str, Any],
    slot: Mapping[str, Any],
    *,
    source_pool_sha256: str,
    scene_pattern_refs: Sequence[str],
    active_nouns: Mapping[str, str],
) -> dict[str, Any]:
    sentence_id = str(profile["sentence_id"])
    item = _common_item(
        requirement,
        primary_profile=profile,
        primary_slot=slot,
        source_sentence_ids=[sentence_id],
        source_pool_sha256=source_pool_sha256,
        scene_pattern_refs=scene_pattern_refs,
        active_nouns=active_nouns,
    )
    model = str(profile.get("text") or "").strip()
    noun_phrase = str(
        slot.get("np_surface")
        or slot.get("surface")
        or slot.get("canonical_surface")
        or ""
    ).strip()
    rubric = {
        "practice_only": False,
        "concept_features": [
            "first_mention_article",
            "target_noun_present",
            "sentence_complete",
        ],
        "surface_features": ["capitalization", "punctuation", "spelling"],
        "minor_surface_error_does_not_zero_concept": True,
    }
    item.update(
        {
            "question_type": "complete_sentence_production",
            "task_angle": "COMPLETE_SENTENCE_PRODUCTION",
            "prompt": "Write one complete sentence about this item in the scene.",
            "stimulus": (
                f"item: {noun_phrase} | scene: {requirement['setting']}"
            ),
            "options": [],
            "correct_answer": model,
            "accepted_answers": [model],
            "scoring_mode": "FEATURE_RUBRIC",
            "human_review_required": True,
            "response_contract": _response_contract(
                mode="FEATURE_RUBRIC",
                model_answer=model,
                rubric=rubric,
            ),
        }
    )
    return _finalize_item(item)


def _pf15_item(
    requirement: Mapping[str, Any],
    first_profile: Mapping[str, Any],
    first_slot: Mapping[str, Any],
    known_profile: Mapping[str, Any],
    *,
    source_pool_sha256: str,
    scene_pattern_refs: Sequence[str],
    active_nouns: Mapping[str, str],
) -> dict[str, Any]:
    first_id = str(first_profile["sentence_id"])
    known_id = str(known_profile["sentence_id"])
    item = _common_item(
        requirement,
        primary_profile=first_profile,
        primary_slot=first_slot,
        source_sentence_ids=[first_id, known_id],
        source_pool_sha256=source_pool_sha256,
        scene_pattern_refs=scene_pattern_refs,
        active_nouns=active_nouns,
    )
    model = " ".join(
        value
        for value in (
            str(first_profile.get("text") or "").strip(),
            str(known_profile.get("text") or "").strip(),
        )
        if value
    )
    noun = str(first_slot.get("_noun") or "")
    rubric = {
        "practice_only": False,
        "concept_features": [
            "first_mention_article",
            "known_reference_article",
            "same_referent_preserved",
            "sentence_1_complete",
            "sentence_2_complete",
        ],
        "surface_features": ["capitalization", "punctuation", "spelling"],
        "minor_surface_error_does_not_zero_concept": True,
    }
    item.update(
        {
            "question_type": "connected_sentence_production",
            "task_angle": "CONNECTED_SENTENCE_PRODUCTION",
            "prompt": (
                "Write two connected sentences. Introduce the item, "
                "then mention the same item again."
            ),
            "stimulus": f"item: {noun} | scene: {requirement['setting']}",
            "options": [],
            "correct_answer": model,
            "accepted_answers": [model],
            "scoring_mode": "FEATURE_RUBRIC",
            "human_review_required": True,
            "response_contract": _response_contract(
                mode="FEATURE_RUBRIC",
                model_answer=model,
                rubric=rubric,
            ),
        }
    )
    return _finalize_item(item)


def build_reconciliation_payload(
    *,
    blueprint: Sequence[Mapping[str, Any]],
    sentence_pool: Mapping[str, Any],
    sentence_pool_sha256: str,
    scene_resolver: Callable[[str], Mapping[str, Any]] = scene_authority.canonical_scene_package,
) -> dict[str, Any]:
    requirements = production_requirements(blueprint)
    by_scene = _profiles_by_scene(sentence_pool)
    active_nouns = _active_noun_senses()
    usage: Counter[str] = Counter()
    items: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []

    for requirement in requirements:
        scene_ref = str(requirement["scene_ref_id"])
        scene_profiles = by_scene.get(scene_ref, [])
        if not scene_profiles:
            raise SentencePoolCapacityError(
                f"SCENE_SENTENCE_SUPPLY_GAP:{requirement['activity_id']}:{scene_ref}"
            )
        first_options = _first_mention_options(scene_profiles, active_nouns)
        target_patterns = _scene_pattern_refs(scene_ref, scene_resolver)
        family = str(requirement["pattern_family_id"])
        if family == u10.PF13:
            profile, slot = _choose_first(
                first_options,
                usage,
                scene_ref_id=scene_ref,
                activity_id=str(requirement["activity_id"]),
            )
            item = _pf13_item(
                requirement,
                profile,
                slot,
                source_pool_sha256=sentence_pool_sha256,
                scene_pattern_refs=target_patterns,
                active_nouns=active_nouns,
            )
            source_ids = [str(profile["sentence_id"])]
        elif family == u10.PF14:
            profile, slot = _choose_first(
                first_options,
                usage,
                scene_ref_id=scene_ref,
                activity_id=str(requirement["activity_id"]),
            )
            item = _pf14_item(
                requirement,
                profile,
                slot,
                source_pool_sha256=sentence_pool_sha256,
                scene_pattern_refs=target_patterns,
                active_nouns=active_nouns,
            )
            source_ids = [str(profile["sentence_id"])]
        elif family == u10.PF15:
            known_options = _known_reference_options(scene_profiles, active_nouns)
            first_profile, first_slot, known_profile, _known_slot = _choose_pair(
                first_options,
                known_options,
                usage,
                scene_ref_id=scene_ref,
                activity_id=str(requirement["activity_id"]),
            )
            item = _pf15_item(
                requirement,
                first_profile,
                first_slot,
                known_profile,
                source_pool_sha256=sentence_pool_sha256,
                scene_pattern_refs=target_patterns,
                active_nouns=active_nouns,
            )
            source_ids = [
                str(first_profile["sentence_id"]),
                str(known_profile["sentence_id"]),
            ]
        else:
            raise SentencePoolCapacityError(
                f"UNSUPPORTED_PRODUCTION_FAMILY:{family}"
            )
        items.append(item)
        assignments.append(
            {
                **deepcopy(dict(requirement)),
                "item_id": str(item["item_id"]),
                "source_sentence_ids": source_ids,
                "target_pattern_ids": list(item["target_pattern_ids"]),
            }
        )

    family_counts = Counter(str(item["pattern_family_id"]) for item in items)
    if len(items) != EXPECTED_PRODUCTION_REQUIREMENT_COUNT:
        raise SentencePoolCapacityError(
            f"MATERIALIZED_ITEM_COUNT_INVALID:{len(items)}"
        )
    if dict(family_counts) != EXPECTED_PRODUCTION_FAMILY_COUNTS:
        raise SentencePoolCapacityError(
            f"MATERIALIZED_FAMILY_COUNTS_INVALID:{dict(family_counts)}"
        )
    if len({str(item["item_id"]) for item in items}) != len(items):
        raise SentencePoolCapacityError("MATERIALIZED_ITEM_ID_DUPLICATE")
    if len({str(item["semantic_signature"]) for item in items}) != len(items):
        raise SentencePoolCapacityError("MATERIALIZED_SEMANTIC_SIGNATURE_DUPLICATE")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": u10.UNIT_ID,
        "source_identity": {
            "sentence_pool_task_id": SOURCE_TASK_ID,
            "sentence_pool_capability_index_sha256": sentence_pool_sha256,
            "sentence_pool_total": EXPECTED_SENTENCE_POOL_TOTAL,
            "blueprint_task_id": u13.TASK_ID,
            "blueprint_activity_count": len(blueprint),
        },
        "production_requirements": {
            "requirement_count": len(requirements),
            "family_counts": dict(sorted(Counter(
                row["pattern_family_id"] for row in requirements
            ).items())),
            "all_requirements_exact_scene_bound": True,
        },
        "assignments": assignments,
        "materialized_items": items,
        "sentence_usage": {
            "distinct_sentence_count": len(usage),
            "sentence_reference_count": sum(usage.values()),
            "max_reuse_count": max(usage.values(), default=0),
        },
        "count_preservation": {
            "base_count_before": EXPECTED_BASE_COUNT,
            "retired_production_item_count": EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
            "materialized_production_item_count": EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
            "base_count_after": EXPECTED_BASE_COUNT,
            "real62_extension_count": EXPECTED_EXTENSION_COUNT,
            "runtime_count_after": EXPECTED_RUNTIME_COUNT,
            "question_bank_total_expanded": False,
        },
        "boundaries": {
            "source_sentence_text_mutated": False,
            "human_sentence_review_decision_mutated": False,
            "scoring_architecture_changed": False,
            "second_question_bank_created": False,
            "second_runtime_created": False,
            "source_database_mutated": False,
            "real62_extension_modified": False,
            "m3_learner_state_rewritten": False,
            "m6_attempts_or_scoring_deleted": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = policy_artifact.digest(payload)
    return payload


def build_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return policy_artifact.build_candidate(
        payload=dict(payload),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "sentence_pool_task_id": SOURCE_TASK_ID,
            "sentence_pool_capability_index_sha256": (
                payload.get("source_identity") or {}
            ).get("sentence_pool_capability_index_sha256"),
            "blueprint_task_id": u13.TASK_ID,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
        as validator,
    )

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def _backup_sqlite(source: Path, target: Path) -> None:
    source = Path(source)
    target = Path(target)
    if not source.is_file():
        raise SentencePoolCapacityError(f"SOURCE_DATABASE_MISSING:{source}")
    if source.resolve() == target.resolve():
        raise SentencePoolCapacityError("DISPOSABLE_DATABASE_MUST_DIFFER_FROM_SOURCE")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SentencePoolCapacityError(
            f"DISPOSABLE_DATABASE_ALREADY_EXISTS:{target}"
        )
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(target) as target_connection:
            source_connection.backup(target_connection)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        is not None
    )


def _delete_u13_bindings_for_sessions(
    connection: sqlite3.Connection,
    session_ids: Sequence[str],
) -> None:
    if not session_ids or not _table_exists(connection, "u01qb13_session_bindings"):
        return
    placeholders = ",".join("?" for _ in session_ids)
    connection.execute(
        f"DELETE FROM u01qb13_session_bindings "
        f"WHERE session_id IN ({placeholders})",
        tuple(session_ids),
    )


def reconcile_disposable_runtime(
    *,
    source_database: Path,
    disposable_database: Path,
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    payload = approved.get("payload")
    if not isinstance(payload, Mapping) or payload.get("task_id") != TASK_ID:
        raise SentencePoolCapacityError("APPROVED_R2R2_PAYLOAD_INVALID")
    from ulga.validators import (
        validate_a1fs_v1_policy_bound_content_artifact as policy_validator,
    )

    policy_validator.validate_artifact(
        approved,
        expected_role=policy_artifact.APPROVED_ROLE,
    )
    _backup_sqlite(Path(source_database), Path(disposable_database))
    desired_items = [
        deepcopy(dict(row))
        for row in payload.get("materialized_items") or []
    ]
    desired_by_id = {str(row["item_id"]): row for row in desired_items}
    if len(desired_by_id) != EXPECTED_PRODUCTION_REQUIREMENT_COUNT:
        raise SentencePoolCapacityError("APPROVED_MATERIALIZED_ITEMS_INVALID")

    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(disposable_database))
    archived_at = u11.utc_now()
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in (
            "metadata",
            "lesson_assets",
            "response_contracts",
            "response_attempts",
            "scoring_results",
            "u01qb02_metadata",
            "u01qb02_item_catalog",
            "u01qb02_session_plans",
            "u01qb02_session_items",
            "u01qb02_item_exposures",
            "razq01e_metadata",
            "razq01e_extension_items",
            "u01qb12_metadata",
            "u01qb13_blueprint_activities",
        ):
            _require_table(connection, table)
        connection.executescript(u11.ARCHIVE_SQL)
        connection.execute(
            f"""CREATE TABLE IF NOT EXISTS {METADATA_TABLE}(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        extension_before = u11._extension_snapshot(connection)
        extension_ids = set(extension_before["item_ids"])
        catalog_rows = connection.execute(
            "SELECT item_id,pattern_family_id FROM u01qb02_item_catalog"
        ).fetchall()
        current_ids = {str(row["item_id"]) for row in catalog_rows}
        if len(current_ids) != EXPECTED_RUNTIME_COUNT:
            raise SentencePoolCapacityError(
                f"PRE_RECONCILIATION_RUNTIME_COUNT_INVALID:{len(current_ids)}"
            )
        current_base_ids = current_ids - extension_ids
        if len(current_base_ids) != EXPECTED_BASE_COUNT:
            raise SentencePoolCapacityError(
                f"PRE_RECONCILIATION_BASE_COUNT_INVALID:{len(current_base_ids)}"
            )
        retired_ids = {
            str(row["item_id"])
            for row in catalog_rows
            if str(row["pattern_family_id"])
            in EXPECTED_PRODUCTION_FAMILY_COUNTS
            and str(row["item_id"]) not in extension_ids
        }
        if len(retired_ids) != EXPECTED_PRODUCTION_REQUIREMENT_COUNT:
            raise SentencePoolCapacityError(
                f"RETIRED_PRODUCTION_COUNT_INVALID:{len(retired_ids)}"
            )
        retired_counts = Counter(
            str(row["pattern_family_id"])
            for row in catalog_rows
            if str(row["item_id"]) in retired_ids
        )
        if dict(retired_counts) != EXPECTED_PRODUCTION_FAMILY_COUNTS:
            raise SentencePoolCapacityError(
                f"RETIRED_PRODUCTION_DISTRIBUTION_INVALID:{dict(retired_counts)}"
            )
        new_ids = set(desired_by_id)
        if current_ids & new_ids:
            raise SentencePoolCapacityError("R2R2_ITEM_ID_COLLISION")

        placeholders = ",".join("?" for _ in retired_ids)
        affected_session_ids = sorted(
            {
                str(row[0])
                for row in connection.execute(
                    f"SELECT DISTINCT session_id FROM u01qb02_session_items "
                    f"WHERE item_id IN ({placeholders})",
                    tuple(sorted(retired_ids)),
                )
            }
            | {
                str(row[0])
                for row in connection.execute(
                    f"SELECT DISTINCT session_id FROM u01qb02_item_exposures "
                    f"WHERE item_id IN ({placeholders})",
                    tuple(sorted(retired_ids)),
                )
            }
        )
        _delete_u13_bindings_for_sessions(connection, affected_session_ids)
        affected_session_count, archived_record_count = u11._archive_affected_history(
            connection,
            retired_ids,
            archived_at=archived_at,
        )
        connection.execute(
            f"DELETE FROM u01qb02_item_catalog WHERE item_id IN ({placeholders})",
            tuple(sorted(retired_ids)),
        )
        for item_id in sorted(desired_by_id):
            u11._register_base_item(connection, desired_by_id[item_id])

        extension_after = u11._extension_snapshot(connection)
        if extension_after["identity_sha256"] != extension_before["identity_sha256"]:
            raise SentencePoolCapacityError("REAL62_EXTENSION_IDENTITY_CHANGED")
        total = int(
            connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0]
        )
        extension_count = int(
            connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0]
        )
        base_count = total - extension_count
        if (base_count, extension_count, total) != (
            EXPECTED_BASE_COUNT,
            EXPECTED_EXTENSION_COUNT,
            EXPECTED_RUNTIME_COUNT,
        ):
            raise SentencePoolCapacityError(
                f"POST_RECONCILIATION_DENOMINATOR_INVALID:"
                f"{base_count}:{extension_count}:{total}"
            )
        actual_counts = Counter(
            str(row[0])
            for row in connection.execute(
                """SELECT pattern_family_id
                   FROM u01qb02_item_catalog
                   WHERE item_id NOT IN (
                     SELECT item_id FROM razq01e_extension_items
                   )
                   GROUP BY item_id"""
            )
            if str(row[0]) in EXPECTED_PRODUCTION_FAMILY_COUNTS
        )
        if dict(actual_counts) != EXPECTED_PRODUCTION_FAMILY_COUNTS:
            raise SentencePoolCapacityError(
                f"POST_RECONCILIATION_PRODUCTION_COUNTS_INVALID:{dict(actual_counts)}"
            )

        combined_sha = digest(
            {
                "r2r2_approved_artifact_sha256": approved["artifact_sha256"],
                "content_extension_artifact_sha256": extension_after["artifact_sha256"],
            }
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "base_source_bank_artifact_sha256": str(approved["artifact_sha256"]),
                "source_bank_artifact_sha256": combined_sha,
                "approved_item_count": str(EXPECTED_BASE_COUNT),
                "razq01e_extension_artifact_sha256": str(
                    extension_after["artifact_sha256"]
                ),
                "razq01e_extension_item_count": str(EXPECTED_EXTENSION_COUNT),
                "razq01e_combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "u01qb18h_r2r2_task_id": TASK_ID,
                "u01qb18h_r2r2_schema_version": SCHEMA_VERSION,
                "u01qb18h_r2r2_validation_status": PASS_STATUS,
                "u01qb18h_r2r2_next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "approved_artifact_sha256": str(approved["artifact_sha256"]),
                "source_database": str(Path(source_database).resolve()),
                "source_database_mutated": "false",
                "base_item_count": str(base_count),
                "extension_item_count": str(extension_count),
                "runtime_item_count": str(total),
                "retired_production_item_count": str(len(retired_ids)),
                "materialized_production_item_count": str(len(desired_by_id)),
                "next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )

    return {
        "validation_status": PASS_STATUS,
        "source_database": str(Path(source_database).resolve()),
        "disposable_database": str(Path(disposable_database).resolve()),
        "source_database_mutated": False,
        "retired_production_item_count": EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "materialized_production_item_count": EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "affected_session_count": affected_session_count,
        "archived_runtime_history_record_count": archived_record_count,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "real62_extension_identity_sha256": extension_after["identity_sha256"],
        "approved_artifact_sha256": str(approved["artifact_sha256"]),
        "combined_source_bank_sha256": combined_sha,
    }


def materialize(
    *,
    source_database: Path,
    disposable_database: Path,
    sentence_pool_capability_index: Path,
    candidate_path: Path,
    approved_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    sentence_pool = load_sentence_pool(sentence_pool_capability_index)
    source_pool_sha = file_digest(sentence_pool_capability_index)
    with sqlite3.connect(Path(source_database)) as connection:
        connection.row_factory = sqlite3.Row
        blueprint = blueprint_rows(connection)
    payload = build_reconciliation_payload(
        blueprint=blueprint,
        sentence_pool=sentence_pool,
        sentence_pool_sha256=source_pool_sha,
    )
    candidate = build_candidate(payload)
    approved = admit_candidate(candidate)
    from ulga.validators import (
        validate_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
        as validator,
    )

    validation = validator.validate_approved(candidate, approved)
    if validation.get("error_count"):
        raise SentencePoolCapacityError(
            "R2R2_APPROVED_VALIDATION_FAILED:"
            + "|".join(str(value) for value in validation.get("errors") or [])
        )
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    migration = reconcile_disposable_runtime(
        source_database=source_database,
        disposable_database=disposable_database,
        approved=approved,
    )
    report = {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "approved_artifact_sha256": approved["artifact_sha256"],
        "sentence_pool_capability_index_sha256": source_pool_sha,
        "production_requirement_count": EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "production_family_counts": EXPECTED_PRODUCTION_FAMILY_COUNTS,
        "materialized_item_count": len(payload["materialized_items"]),
        "distinct_source_sentence_count": payload["sentence_usage"][
            "distinct_sentence_count"
        ],
        "source_sentence_reference_count": payload["sentence_usage"][
            "sentence_reference_count"
        ],
        "max_source_sentence_reuse_count": payload["sentence_usage"][
            "max_reuse_count"
        ],
        "runtime_migration": migration,
        "validation_receipt": validation,
        "boundaries": deepcopy(payload["boundaries"]),
        "next_short_step": NEXT_SHORT_STEP,
    }
    write_json(report_path, report, private=True)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--disposable-database", type=Path, required=True)
    parser.add_argument(
        "--sentence-pool-capability-index",
        type=Path,
        required=True,
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = materialize(
            source_database=args.source_database,
            disposable_database=args.disposable_database,
            sentence_pool_capability_index=args.sentence_pool_capability_index,
            candidate_path=args.candidate,
            approved_path=args.approved,
            report_path=args.report,
        )
    except (
        SentencePoolCapacityError,
        policy_artifact.ContentPolicyBuildError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        print(f"STATUS=FAIL_{TASK_ID}")
        print(f"ERROR={exc}")
        return 1
    migration = value["runtime_migration"]
    print(f"STATUS={PASS_STATUS}")
    print(
        f"PRODUCTION_REQUIREMENTS={value['production_requirement_count']}"
    )
    print(f"MATERIALIZED_ITEMS={value['materialized_item_count']}")
    print(f"BASE_ITEMS={migration['base_item_count']}")
    print(f"REAL62_EXTENSION_ITEMS={migration['extension_item_count']}")
    print(f"RUNTIME_ITEMS={migration['runtime_item_count']}")
    print(f"SOURCE_DATABASE_MUTATED={migration['source_database_mutated']}")
    print(f"DISPOSABLE_DATABASE={migration['disposable_database']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
