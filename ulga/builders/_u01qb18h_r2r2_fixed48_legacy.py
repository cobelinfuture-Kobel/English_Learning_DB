#!/usr/bin/env python3
"""Materialize the exact Unit01 Writing production slots from the admitted 3805 pool.

R2R2 reads the installed U01QB13 240-row blueprint and replaces exactly the 48
PF13/PF14/PF15 base items with sentence-backed, exact-scene items.  The source
SQLite database is never mutated; a disposable backup is reconciled instead.

Vocabulary lineage is deliberately two-tiered.  A target keeps a canonical A1
vocabulary authority only when S01 exposes a unique authority id (selected or
OBSERVED_IN_MATERIAL_ONLY).  Every target also keeps the admitted sentence-pool
entity id.  A sentence-pool entity therefore never masquerades as an EVP/A1
vocabulary authority when none is uniquely available.
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
from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u10
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18H-R2R2_Unit01SentencePoolDrivenProductionCapacityReconciliation"
SCHEMA_VERSION = "a1fs.v1.u01qb18h.r2r2.unit01_sentence_pool_driven_production_capacity_reconciliation.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB18H_R2R2_UNIT01_SENTENCE_POOL_DRIVEN_PRODUCTION_CAPACITY_RECONCILIATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-20:U01QB18H-R2R2"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18H-R2R2_ActualTwelveFormFreshReplayAndPdfReacceptance"
SOURCE_TASK_ID = "A1FS-V1-U01SA05R2_Full3805SentencePoolCapabilityCoverageAndUnit01QuestionBankResidualBindingReconciliation"
SOURCE_STATUS = "CAPABILITY_CLASSIFIED"
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
EXPECTED_PRODUCTION_FAMILY_COUNTS = {u10.PF13: 12, u10.PF14: 24, u10.PF15: 12}
METADATA_TABLE = "u01qb18h_r2r2_metadata"
_SOURCE_KIND_RANK = {"REAL_SOURCE": 0, "CANONICAL_SCENE_DERIVED": 1, "MODEL/TEMPLATE_DERIVED": 2}
_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)


class SentencePoolCapacityError(ValueError):
    pass


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
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
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
    value = read_json(path)
    if not isinstance(value, Mapping):
        raise SentencePoolCapacityError("SENTENCE_POOL_OBJECT_REQUIRED")
    if str(value.get("task_id") or "") != SOURCE_TASK_ID:
        raise SentencePoolCapacityError(f"SENTENCE_POOL_TASK_INVALID:{value.get('task_id')}")
    if str(value.get("status") or "") != SOURCE_STATUS:
        raise SentencePoolCapacityError(f"SENTENCE_POOL_STATUS_INVALID:{value.get('status')}")
    profiles = value.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != EXPECTED_SENTENCE_POOL_TOTAL:
        raise SentencePoolCapacityError(f"SENTENCE_POOL_PROFILE_COUNT_INVALID:{len(profiles or [])}")
    if int(value.get("sentence_pool_total") or 0) != EXPECTED_SENTENCE_POOL_TOTAL:
        raise SentencePoolCapacityError(f"SENTENCE_POOL_TOTAL_INVALID:{value.get('sentence_pool_total')}")
    seen: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, Mapping):
            raise SentencePoolCapacityError("SENTENCE_PROFILE_OBJECT_REQUIRED")
        sentence_id = str(profile.get("sentence_id") or "")
        if not sentence_id or sentence_id in seen:
            raise SentencePoolCapacityError(f"SENTENCE_PROFILE_ID_INVALID:{sentence_id}")
        seen.add(sentence_id)
        if str(profile.get("canonical_admission_status") or "") != "ADMITTED":
            raise SentencePoolCapacityError(f"NON_ADMITTED_SENTENCE_LEAKED:{sentence_id}")
    return dict(value)


def _require_table(connection: sqlite3.Connection, table: str) -> None:
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
        raise SentencePoolCapacityError(f"REQUIRED_TABLE_MISSING:{table}")


def blueprint_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    _require_table(connection, "u01qb13_blueprint_activities")
    rows = [dict(row) for row in connection.execute(
        """SELECT activity_id,form_id,form_ordinal,scene_ref_id,situation_family,setting,
                  skill,task_angle,support_level,assessment_candidate,pattern_family_ids_json
           FROM u01qb13_blueprint_activities ORDER BY form_ordinal,activity_id"""
    )]
    if len(rows) != EXPECTED_BLUEPRINT_ACTIVITY_COUNT:
        raise SentencePoolCapacityError(f"BLUEPRINT_ACTIVITY_COUNT_INVALID:{len(rows)}")
    return rows


def production_requirements(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("skill") or "") != "WRITING":
            continue
        angle = str(row.get("task_angle") or "")
        family = PRODUCTION_ANGLE_TO_FAMILY.get(angle)
        if family is None:
            continue
        allowed = {str(v) for v in json.loads(str(row.get("pattern_family_ids_json") or "[]")) if str(v)}
        if family not in allowed:
            raise SentencePoolCapacityError(f"BLUEPRINT_PRODUCTION_FAMILY_NOT_ALLOWED:{row.get('activity_id')}:{angle}:{family}:{sorted(allowed)}")
        result.append({
            "activity_id": str(row["activity_id"]),
            "form_id": str(row["form_id"]),
            "form_ordinal": int(row["form_ordinal"]),
            "scene_ref_id": str(row["scene_ref_id"]),
            "situation_family": str(row["situation_family"]),
            "setting": str(row["setting"]),
            "support_level": str(row["support_level"]),
            "assessment_candidate": bool(row["assessment_candidate"]),
            "task_angle": angle,
            "pattern_family_id": family,
        })
    counts = Counter(r["pattern_family_id"] for r in result)
    if len(result) != EXPECTED_PRODUCTION_REQUIREMENT_COUNT:
        raise SentencePoolCapacityError(f"PRODUCTION_REQUIREMENT_COUNT_INVALID:{len(result)}")
    if dict(counts) != EXPECTED_PRODUCTION_FAMILY_COUNTS:
        raise SentencePoolCapacityError(f"PRODUCTION_REQUIREMENT_DISTRIBUTION_INVALID:{dict(counts)}")
    return result


def _unit01_vocabulary_authority() -> dict[str, str]:
    """Return selected plus unique observed-in-material A1 authority identities."""
    scope, _unit, _authority = s01.unit_authority_context()
    selected, unselected = s01.selected_vocabulary(scope)
    result: dict[str, str] = {}
    for row in selected:
        label = s01.phrase(str(row.get("label") or ""))
        authority_id = str(row.get("authority_id") or "")
        if label and authority_id:
            result[label] = authority_id
    for row in unselected:
        label = s01.phrase(str(row.get("label") or ""))
        candidates = [str(v) for v in row.get("candidate_authority_ids") or [] if str(v)]
        if row.get("status") == "OBSERVED_IN_MATERIAL_ONLY" and label and len(candidates) == 1:
            result.setdefault(label, candidates[0])
    if not result:
        raise SentencePoolCapacityError("UNIT01_VOCABULARY_AUTHORITY_EMPTY")
    return result


def _slot_surface(slot: Mapping[str, Any]) -> str:
    return str(slot.get("canonical_surface") or slot.get("surface") or slot.get("np_surface") or slot.get("entity_id") or "").strip()


def _slot_target(slot: Mapping[str, Any], vocabulary: Mapping[str, str]) -> tuple[str, str, str] | None:
    words = [w.casefold() for w in _WORD_RE.findall(_slot_surface(slot).replace("_", " "))]
    if not words:
        return None
    noun = words[-1]
    entity_id = str(slot.get("entity_id") or noun.upper()).strip()
    if not entity_id:
        return None
    return noun, str(vocabulary.get(noun) or ""), entity_id


def _slot_role_eligible(slot: Mapping[str, Any]) -> bool:
    role = str(slot.get("semantic_role") or slot.get("syntactic_role") or "").upper()
    return role not in {"RELATION_OBJECT", "OBJECT", "CONTAINER", "LOCATION"}


def _usable_np_slots(profile: Mapping[str, Any], vocabulary: Mapping[str, str], *, first_mention: bool) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in profile.get("np_slots") or []:
        if not isinstance(raw, Mapping) or not _slot_role_eligible(raw):
            continue
        slot = dict(raw)
        target = _slot_target(slot, vocabulary)
        if target is None:
            continue
        noun, vocabulary_ref, entity_id = target
        determiner = str(slot.get("determiner") or "").casefold()
        if first_mention and determiner not in {"a", "an"}:
            continue
        if not first_mention and determiner != "the":
            continue
        slot.update({"_noun": noun, "_vocabulary_ref": vocabulary_ref, "_entity_id": entity_id})
        result.append(slot)
    result.sort(key=lambda slot: (
        str(slot.get("semantic_role") or "") not in {"TARGET", "RELATION_SUBJECT"},
        str(slot.get("syntactic_role") or "") not in {"SUBJECT", "RELATION_SUBJECT"},
        int(slot.get("char_start") or 0),
        str(slot.get("_entity_id") or ""),
    ))
    return result


def _source_rank(profile: Mapping[str, Any]) -> tuple[Any, ...]:
    return (_SOURCE_KIND_RANK.get(str(profile.get("source_kind") or ""), 9), not bool(profile.get("relation_capability")), bool(profile.get("legacy_unnormalized")), str(profile.get("sentence_id") or ""))


def _profiles_by_scene(pool: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in pool.get("profiles") or []:
        profile = dict(raw)
        ref = str(profile.get("source_scene_ref") or "")
        if ref:
            result[ref].append(profile)
    for rows in result.values():
        rows.sort(key=_source_rank)
    return result


def _options(scene_profiles: Sequence[Mapping[str, Any]], vocabulary: Mapping[str, str], *, first: bool) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    capability = "FIRST_MENTION" if first else "KNOWN_REFERENCE_TARGET"
    result: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for raw in scene_profiles:
        profile = dict(raw)
        if capability not in {str(v) for v in profile.get("discourse_capability") or []}:
            continue
        if "WRITING" not in {str(v) for v in profile.get("task_use_capability") or []}:
            continue
        result.extend((profile, slot) for slot in _usable_np_slots(profile, vocabulary, first_mention=first))
    result.sort(key=lambda pair: (_source_rank(pair[0]), str(pair[1].get("_entity_id") or "")))
    return result


def _first_mention_options(scene_profiles: Sequence[Mapping[str, Any]], vocabulary: Mapping[str, str]):
    return _options(scene_profiles, vocabulary, first=True)


def _known_reference_options(scene_profiles: Sequence[Mapping[str, Any]], vocabulary: Mapping[str, str]):
    return _options(scene_profiles, vocabulary, first=False)


def _choose_first(options, usage: Counter[str], *, scene_ref_id: str, activity_id: str):
    if not options:
        raise SentencePoolCapacityError(f"FIRST_MENTION_SENTENCE_SUPPLY_GAP:{activity_id}:{scene_ref_id}")
    ranked = sorted(options, key=lambda pair: (usage[str(pair[0]["sentence_id"])], _source_rank(pair[0]), str(pair[1].get("_entity_id") or "")))
    profile, slot = ranked[0]
    usage[str(profile["sentence_id"])] += 1
    return profile, slot


def _choose_pair(first_options, known_options, usage: Counter[str], *, scene_ref_id: str, activity_id: str):
    pairs = []
    for fp, fs in first_options:
        for kp, ks in known_options:
            if str(fs.get("_entity_id") or "") != str(ks.get("_entity_id") or ""):
                continue
            if str(fs.get("_noun") or "") != str(ks.get("_noun") or ""):
                continue
            if str(fp["sentence_id"]) == str(kp["sentence_id"]):
                continue
            pairs.append((fp, fs, kp, ks))
    if not pairs:
        raise SentencePoolCapacityError(f"CONNECTED_SENTENCE_PAIR_SUPPLY_GAP:{activity_id}:{scene_ref_id}")
    pairs.sort(key=lambda p: (usage[str(p[0]["sentence_id"])] + usage[str(p[2]["sentence_id"])], max(usage[str(p[0]["sentence_id"])], usage[str(p[2]["sentence_id"])]), _source_rank(p[0]), _source_rank(p[2]), str(p[1].get("_entity_id") or "")))
    fp, fs, kp, ks = pairs[0]
    usage[str(fp["sentence_id"])] += 1
    usage[str(kp["sentence_id"])] += 1
    return fp, fs, kp, ks


def _internal_unit_pattern(structure: str) -> str:
    return u10.seed.PATTERN_ADJECTIVE if structure == "ADJECTIVE" else u10.seed.PATTERN_VERY if structure == "VERY" else u10.seed.PATTERN_NOUN


def _target_egp_rows(structure: str) -> list[str]:
    return [str(u10.seed.contract.CORE_EGP_ROWS[1])] if structure == "ADJECTIVE" else [str(u10.seed.contract.GUIDED_EGP_ROWS[0])] if structure == "VERY" else [str(u10.seed.contract.CORE_EGP_ROWS[0])]


def _scene_pattern_refs(scene_ref_id: str, resolver: Callable[[str], Mapping[str, Any]]) -> list[str]:
    projection = resolver(scene_ref_id).get("unit_language_projection")
    if not isinstance(projection, Mapping):
        raise SentencePoolCapacityError(f"SCENE_LANGUAGE_PROJECTION_MISSING:{scene_ref_id}")
    refs = sorted({str(v) for v in projection.get("eligible_pattern_refs") or [] if str(v)})
    if not refs:
        raise SentencePoolCapacityError(f"SCENE_ELIGIBLE_PATTERN_REFS_MISSING:{scene_ref_id}")
    return refs


def _common_item(requirement: Mapping[str, Any], slot: Mapping[str, Any], source_sentence_ids: Sequence[str], source_pool_sha256: str, scene_pattern_refs: Sequence[str]) -> dict[str, Any]:
    noun = str(slot.get("_noun") or "")
    entity_id = str(slot.get("_entity_id") or "")
    vocabulary_ref = str(slot.get("_vocabulary_ref") or "")
    if not noun or not entity_id:
        raise SentencePoolCapacityError(f"SENTENCE_ENTITY_TARGET_MISSING:{requirement['activity_id']}")
    canonical_context = u13.FAMILY_CANONICAL_CONTEXT.get(str(requirement["situation_family"]))
    if not canonical_context:
        raise SentencePoolCapacityError(f"CANONICAL_CONTEXT_UNMAPPED:{requirement['activity_id']}")
    modifiers = [str(v).casefold() for v in slot.get("modifiers") or [] if str(v)]
    structure = str(slot.get("structure") or "NOUN")
    lexical_slots: dict[str, Any] = {"noun": noun, "context_id": canonical_context}
    if modifiers:
        lexical_slots["adjective"] = modifiers[-1]
    activity_id = str(requirement["activity_id"])
    item = {
        "item_id": f"U01QB18H-R2R2-{u10.seed.slug(str(requirement['pattern_family_id']))}-{u10.seed.slug(activity_id)}",
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
        "target_evp_sense_ids": [vocabulary_ref] if vocabulary_ref else [],
        "sentence_pool_target_entity_id": entity_id,
        "sentence_pool_target_noun": noun,
        "target_sentence_ids": list(source_sentence_ids),
        "target_pattern_ids": list(scene_pattern_refs),
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
        "admission_proposal": {"status": "AUTO_APPROVED", "reason_codes": ["U01SA05R2_ADMITTED_SENTENCE_MATERIALIZATION", "U01SA05R2_SENTENCE_ENTITY_BOUND", "U01QB13_EXACT_BLUEPRINT_PRODUCTION_REQUIREMENT"] + (["U01E_S01_UNIQUE_A1_VOCABULARY_AUTHORITY_BOUND"] if vocabulary_ref else [])},
        "source_refs": [{"source_type": "U01SA05R2_ADMITTED_SENTENCE_CAPABILITY", "task_id": SOURCE_TASK_ID, "sentence_id": str(sid), "source_scene_ref": str(requirement["scene_ref_id"]), "target_entity_id": entity_id, "capability_index_sha256": source_pool_sha256} for sid in source_sentence_ids],
        "sentence_pool_source_task_id": SOURCE_TASK_ID,
        "sentence_pool_capability_index_sha256": source_pool_sha256,
        "source_sentence_ids": list(source_sentence_ids),
    }
    return item


def _response_contract(*, mode: str, model_answer: str, rubric: Mapping[str, Any] | None = None):
    return u10._response_contract(mode=mode, model_answer=model_answer, rubric=rubric)


def _finalize(item: dict[str, Any]) -> dict[str, Any]:
    item["semantic_signature"] = u10.seed.digest({k: item[k] for k in ("pattern_family_id", "candidate_structure", "context_id", "production_scene_ref_id", "source_sentence_ids", "lexical_slots", "prompt", "stimulus", "options", "correct_answer", "task_angle")})
    return item


def _np_surface(slot: Mapping[str, Any]) -> str:
    return str(slot.get("np_surface") or slot.get("surface") or slot.get("canonical_surface") or "").strip()


def _production_item(requirement, first_profile, first_slot, known_profile, *, source_pool_sha256, scene_pattern_refs):
    family = str(requirement["pattern_family_id"])
    source_ids = [str(first_profile["sentence_id"])] + ([str(known_profile["sentence_id"])] if known_profile else [])
    item = _common_item(requirement, first_slot, source_ids, source_pool_sha256, scene_pattern_refs)
    if family == u10.PF13:
        correct = _np_surface(first_slot)
        det = str(first_slot.get("determiner") or "").casefold()
        wrong_det = "an" if det == "a" else "a"
        wrong = re.sub(r"^(?:a|an|the)\b", wrong_det, correct, count=1, flags=re.I)
        item.update(question_type="error_correction", task_angle="ERROR_CHECK", prompt="Correct the article error in the noun phrase.", stimulus=wrong, options=[], correct_answer=correct, accepted_answers=[correct], scoring_mode="NORMALIZED_TEXT", human_review_required=False, response_contract=_response_contract(mode="NORMALIZED_TEXT", model_answer=correct))
    elif family == u10.PF14:
        model = str(first_profile.get("text") or "").strip()
        rubric = {"practice_only": False, "concept_features": ["first_mention_article", "target_noun_present", "sentence_complete"], "surface_features": ["capitalization", "punctuation", "spelling"], "minor_surface_error_does_not_zero_concept": True}
        item.update(question_type="complete_sentence_production", task_angle="COMPLETE_SENTENCE_PRODUCTION", prompt="Write one complete sentence about this item in the scene.", stimulus=f"item: {_np_surface(first_slot)} | scene: {requirement['setting']}", options=[], correct_answer=model, accepted_answers=[model], scoring_mode="FEATURE_RUBRIC", human_review_required=True, response_contract=_response_contract(mode="FEATURE_RUBRIC", model_answer=model, rubric=rubric))
    elif family == u10.PF15:
        if known_profile is None:
            raise SentencePoolCapacityError("PF15_KNOWN_REFERENCE_REQUIRED")
        model = f"{str(first_profile.get('text') or '').strip()} {str(known_profile.get('text') or '').strip()}".strip()
        rubric = {"practice_only": False, "concept_features": ["first_mention_article", "known_reference_article", "same_referent_preserved", "sentence_1_complete", "sentence_2_complete"], "surface_features": ["capitalization", "punctuation", "spelling"], "minor_surface_error_does_not_zero_concept": True}
        item.update(question_type="connected_sentence_production", task_angle="CONNECTED_SENTENCE_PRODUCTION", prompt="Write two connected sentences. Introduce the item, then mention the same item again.", stimulus=f"item: {first_slot['_noun']} | scene: {requirement['setting']}", options=[], correct_answer=model, accepted_answers=[model], scoring_mode="FEATURE_RUBRIC", human_review_required=True, response_contract=_response_contract(mode="FEATURE_RUBRIC", model_answer=model, rubric=rubric))
    else:
        raise SentencePoolCapacityError(f"UNSUPPORTED_PRODUCTION_FAMILY:{family}")
    return _finalize(item)


def build_reconciliation_payload(*, blueprint: Sequence[Mapping[str, Any]], sentence_pool: Mapping[str, Any], sentence_pool_sha256: str, scene_resolver: Callable[[str], Mapping[str, Any]] = scene_authority.canonical_scene_package) -> dict[str, Any]:
    requirements = production_requirements(blueprint)
    by_scene = _profiles_by_scene(sentence_pool)
    vocabulary = _unit01_vocabulary_authority()
    usage: Counter[str] = Counter()
    items: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    for requirement in requirements:
        ref = str(requirement["scene_ref_id"])
        profiles = by_scene.get(ref, [])
        if not profiles:
            raise SentencePoolCapacityError(f"SCENE_SENTENCE_SUPPLY_GAP:{requirement['activity_id']}:{ref}")
        first_options = _first_mention_options(profiles, vocabulary)
        family = str(requirement["pattern_family_id"])
        known_profile = None
        if family == u10.PF15:
            fp, fs, known_profile, _ks = _choose_pair(first_options, _known_reference_options(profiles, vocabulary), usage, scene_ref_id=ref, activity_id=str(requirement["activity_id"]))
        else:
            fp, fs = _choose_first(first_options, usage, scene_ref_id=ref, activity_id=str(requirement["activity_id"]))
        item = _production_item(requirement, fp, fs, known_profile, source_pool_sha256=sentence_pool_sha256, scene_pattern_refs=_scene_pattern_refs(ref, scene_resolver))
        items.append(item)
        assignments.append({**deepcopy(dict(requirement)), "item_id": item["item_id"], "source_sentence_ids": list(item["source_sentence_ids"]), "target_pattern_ids": list(item["target_pattern_ids"])})
    family_counts = Counter(str(i["pattern_family_id"]) for i in items)
    if len(items) != 48 or dict(family_counts) != EXPECTED_PRODUCTION_FAMILY_COUNTS:
        raise SentencePoolCapacityError(f"MATERIALIZED_DISTRIBUTION_INVALID:{len(items)}:{dict(family_counts)}")
    if len({i["item_id"] for i in items}) != 48 or len({i["semantic_signature"] for i in items}) != 48:
        raise SentencePoolCapacityError("MATERIALIZED_IDENTITY_DUPLICATE")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "program_id": PROGRAM_ID, "task_id": TASK_ID, "status": PASS_STATUS, "unit_id": u10.UNIT_ID,
        "source_identity": {"sentence_pool_task_id": SOURCE_TASK_ID, "sentence_pool_capability_index_sha256": sentence_pool_sha256, "sentence_pool_total": EXPECTED_SENTENCE_POOL_TOTAL, "blueprint_task_id": u13.TASK_ID, "blueprint_activity_count": len(blueprint), "vocabulary_authority_task_id": s01.TASK_ID},
        "production_requirements": {"requirement_count": 48, "family_counts": dict(sorted(family_counts.items())), "all_requirements_exact_scene_bound": True},
        "assignments": assignments, "materialized_items": items,
        "sentence_usage": {"distinct_sentence_count": len(usage), "sentence_reference_count": sum(usage.values()), "max_reuse_count": max(usage.values(), default=0)},
        "count_preservation": {"base_count_before": 288, "retired_production_item_count": 48, "materialized_production_item_count": 48, "base_count_after": 288, "real62_extension_count": 186, "runtime_count_after": 474, "question_bank_total_expanded": False},
        "boundaries": {"source_sentence_text_mutated": False, "human_sentence_review_decision_mutated": False, "scoring_architecture_changed": False, "second_question_bank_created": False, "second_runtime_created": False, "source_database_mutated": False, "real62_extension_modified": False, "m3_learner_state_rewritten": False, "m6_attempts_or_scoring_deleted": False, "speaking_scoring_enabled": False, "unit02_to_unit24_modified": False, "a2_unlocked": False},
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = policy_artifact.digest(payload)
    return payload


def build_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return policy_artifact.build_candidate(payload=dict(payload), producer_id=TASK_ID, level_scope=["A1"], source_bindings={"sentence_pool_task_id": SOURCE_TASK_ID, "sentence_pool_capability_index_sha256": (payload.get("source_identity") or {}).get("sentence_pool_capability_index_sha256"), "blueprint_task_id": u13.TASK_ID, "vocabulary_authority_task_id": s01.TASK_ID, "count_preserving": True, "operator_decision_ref": DECISION_REF})


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation as validator
    return policy_artifact.admit_candidate(candidate, validation_receipts=[validator.validate_candidate(candidate)], decision_ref=DECISION_REF, producer_id=TASK_ID)


def _backup_sqlite(source: Path, target: Path) -> None:
    if not source.is_file():
        raise SentencePoolCapacityError(f"SOURCE_DATABASE_MISSING:{source}")
    if source.resolve() == target.resolve():
        raise SentencePoolCapacityError("DISPOSABLE_DATABASE_MUST_DIFFER_FROM_SOURCE")
    if target.exists():
        raise SentencePoolCapacityError(f"DISPOSABLE_DATABASE_ALREADY_EXISTS:{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def reconcile_disposable_runtime(*, source_database: Path, disposable_database: Path, approved: Mapping[str, Any]) -> dict[str, Any]:
    payload = approved.get("payload")
    if not isinstance(payload, Mapping) or payload.get("task_id") != TASK_ID:
        raise SentencePoolCapacityError("APPROVED_R2R2_PAYLOAD_INVALID")
    from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator
    policy_validator.validate_artifact(approved, expected_role=policy_artifact.APPROVED_ROLE)
    _backup_sqlite(Path(source_database), Path(disposable_database))
    desired = {str(r["item_id"]): deepcopy(dict(r)) for r in payload.get("materialized_items") or []}
    if len(desired) != 48:
        raise SentencePoolCapacityError("APPROVED_MATERIALIZED_ITEMS_INVALID")
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(disposable_database))
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in ("metadata", "lesson_assets", "response_contracts", "response_attempts", "scoring_results", "u01qb02_metadata", "u01qb02_item_catalog", "u01qb02_session_plans", "u01qb02_session_items", "u01qb02_item_exposures", "razq01e_metadata", "razq01e_extension_items", "u01qb12_metadata", "u01qb13_blueprint_activities"):
            _require_table(connection, table)
        connection.executescript(u11.ARCHIVE_SQL)
        connection.execute(f"CREATE TABLE IF NOT EXISTS {METADATA_TABLE}(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        extension_before = u11._extension_snapshot(connection)
        extension_ids = set(extension_before["item_ids"])
        rows = connection.execute("SELECT item_id,pattern_family_id FROM u01qb02_item_catalog").fetchall()
        current_ids = {str(r["item_id"]) for r in rows}
        if len(current_ids) != 474 or len(current_ids - extension_ids) != 288:
            raise SentencePoolCapacityError("PRE_RECONCILIATION_DENOMINATOR_INVALID")
        retired = {str(r["item_id"]) for r in rows if str(r["pattern_family_id"]) in EXPECTED_PRODUCTION_FAMILY_COUNTS and str(r["item_id"]) not in extension_ids}
        retired_counts = Counter(str(r["pattern_family_id"]) for r in rows if str(r["item_id"]) in retired)
        if len(retired) != 48 or dict(retired_counts) != EXPECTED_PRODUCTION_FAMILY_COUNTS:
            raise SentencePoolCapacityError(f"RETIRED_PRODUCTION_DISTRIBUTION_INVALID:{len(retired)}:{dict(retired_counts)}")
        if current_ids & set(desired):
            raise SentencePoolCapacityError("R2R2_ITEM_ID_COLLISION")
        marks = ",".join("?" for _ in retired)
        sessions = sorted({str(r[0]) for r in connection.execute(f"SELECT DISTINCT session_id FROM u01qb02_session_items WHERE item_id IN ({marks})", tuple(sorted(retired)))} | {str(r[0]) for r in connection.execute(f"SELECT DISTINCT session_id FROM u01qb02_item_exposures WHERE item_id IN ({marks})", tuple(sorted(retired)))})
        if sessions and _table_exists(connection, "u01qb13_session_bindings"):
            smarks = ",".join("?" for _ in sessions)
            connection.execute(f"DELETE FROM u01qb13_session_bindings WHERE session_id IN ({smarks})", tuple(sessions))
        affected_sessions, archived_records = u11._archive_affected_history(connection, retired, archived_at=u11.utc_now())
        connection.execute(f"DELETE FROM u01qb02_item_catalog WHERE item_id IN ({marks})", tuple(sorted(retired)))
        for item_id in sorted(desired):
            u11._register_base_item(connection, desired[item_id])
        extension_after = u11._extension_snapshot(connection)
        if extension_after["identity_sha256"] != extension_before["identity_sha256"]:
            raise SentencePoolCapacityError("REAL62_EXTENSION_IDENTITY_CHANGED")
        total = int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0])
        ext_count = int(connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0])
        if (total - ext_count, ext_count, total) != (288, 186, 474):
            raise SentencePoolCapacityError(f"POST_RECONCILIATION_DENOMINATOR_INVALID:{total-ext_count}:{ext_count}:{total}")
        combined_sha = digest({"r2r2_approved_artifact_sha256": approved["artifact_sha256"], "content_extension_artifact_sha256": extension_after["artifact_sha256"]})
        metadata = {"base_source_bank_artifact_sha256": str(approved["artifact_sha256"]), "source_bank_artifact_sha256": combined_sha, "approved_item_count": "288", "razq01e_extension_artifact_sha256": str(extension_after["artifact_sha256"]), "razq01e_extension_item_count": "186", "razq01e_combined_runtime_item_count": "474", "u01qb18h_r2r2_task_id": TASK_ID, "u01qb18h_r2r2_schema_version": SCHEMA_VERSION, "u01qb18h_r2r2_validation_status": PASS_STATUS, "u01qb18h_r2r2_next_short_step": NEXT_SHORT_STEP}
        connection.executemany("INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)", metadata.items())
        connection.executemany(f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)", {"task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": PASS_STATUS, "approved_artifact_sha256": str(approved["artifact_sha256"]), "source_database": str(Path(source_database).resolve()), "source_database_mutated": "false", "base_item_count": "288", "extension_item_count": "186", "runtime_item_count": "474", "retired_production_item_count": "48", "materialized_production_item_count": "48", "next_short_step": NEXT_SHORT_STEP}.items())
    return {"validation_status": PASS_STATUS, "source_database": str(Path(source_database).resolve()), "disposable_database": str(Path(disposable_database).resolve()), "source_database_mutated": False, "retired_production_item_count": 48, "materialized_production_item_count": 48, "affected_session_count": affected_sessions, "archived_runtime_history_record_count": archived_records, "base_item_count": 288, "extension_item_count": 186, "runtime_item_count": 474, "real62_extension_identity_sha256": extension_after["identity_sha256"], "approved_artifact_sha256": str(approved["artifact_sha256"]), "combined_source_bank_sha256": combined_sha}


def materialize(*, source_database: Path, disposable_database: Path, sentence_pool_capability_index: Path, candidate_path: Path, approved_path: Path, report_path: Path) -> dict[str, Any]:
    pool = load_sentence_pool(sentence_pool_capability_index)
    pool_sha = file_digest(sentence_pool_capability_index)
    with sqlite3.connect(source_database) as connection:
        connection.row_factory = sqlite3.Row
        blueprint = blueprint_rows(connection)
    payload = build_reconciliation_payload(blueprint=blueprint, sentence_pool=pool, sentence_pool_sha256=pool_sha)
    candidate = build_candidate(payload)
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation as validator
    validation = validator.validate_approved(candidate, approved)
    if validation.get("error_count"):
        raise SentencePoolCapacityError("R2R2_APPROVED_VALIDATION_FAILED:" + "|".join(validation.get("errors") or []))
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    migration = reconcile_disposable_runtime(source_database=source_database, disposable_database=disposable_database, approved=approved)
    report = {"task_id": TASK_ID, "validation_status": PASS_STATUS, "candidate_artifact_sha256": candidate["artifact_sha256"], "approved_artifact_sha256": approved["artifact_sha256"], "sentence_pool_capability_index_sha256": pool_sha, "production_requirement_count": 48, "production_family_counts": EXPECTED_PRODUCTION_FAMILY_COUNTS, "materialized_item_count": 48, "distinct_source_sentence_count": payload["sentence_usage"]["distinct_sentence_count"], "source_sentence_reference_count": payload["sentence_usage"]["sentence_reference_count"], "max_source_sentence_reuse_count": payload["sentence_usage"]["max_reuse_count"], "runtime_migration": migration, "validation_receipt": validation, "boundaries": deepcopy(payload["boundaries"]), "next_short_step": NEXT_SHORT_STEP}
    write_json(report_path, report, private=True)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--disposable-database", type=Path, required=True)
    parser.add_argument("--sentence-pool-capability-index", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = materialize(source_database=args.source_database, disposable_database=args.disposable_database, sentence_pool_capability_index=args.sentence_pool_capability_index, candidate_path=args.candidate, approved_path=args.approved, report_path=args.report)
    except Exception as exc:
        print(f"STATUS=FAIL_{TASK_ID}")
        print(f"ERROR={exc}")
        return 1
    migration = value["runtime_migration"]
    print(f"STATUS={PASS_STATUS}")
    print("PRODUCTION_REQUIREMENTS=48")
    print("MATERIALIZED_ITEMS=48")
    print(f"BASE_ITEMS={migration['base_item_count']}")
    print(f"REAL62_EXTENSION_ITEMS={migration['extension_item_count']}")
    print(f"RUNTIME_ITEMS={migration['runtime_item_count']}")
    print(f"SOURCE_DATABASE_MUTATED={migration['source_database_mutated']}")
    print(f"DISPOSABLE_DATABASE={migration['disposable_database']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
