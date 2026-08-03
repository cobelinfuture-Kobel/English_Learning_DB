#!/usr/bin/env python3
"""Inventory Unit01 micro-scenes for rotation-safe multi-form QuestionBank use.

Read-only: consumes existing Unit01 approved content + canonical contexts and
emits a semantic scene inventory. The v2 signature intentionally excludes
source identity, correcting the legacy RAZQ01D signature that could inflate
scene diversity when two source records described the same scene.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only Unit01 scene inventory; no learner content or authority mutation."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB06_Unit01MicroScenePoolInventoryAndRotationReadiness"
SCHEMA_VERSION = "a1fs.v1.u01qb06.unit01_micro_scene_pool_inventory.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB06_UNIT01_MICRO_SCENE_POOL_INVENTORY"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
DEFAULT_OUTPUT = Path("ulga/reports/a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB07_Unit01MicroScenePoolSupplementationAnd12FormRotationBlueprint"

FORM_COUNT = 12
SCENES_PER_FORM = 4
TOTAL_SCENE_SLOTS = FORM_COUNT * SCENES_PER_FORM
MAX_EXPOSURES_PER_EXACT_SCENE = 2
HARD_MIN_DISTINCT_MICRO_SCENES = TOTAL_SCENE_SLOTS // MAX_EXPOSURES_PER_EXACT_SCENE
TARGET_DISTINCT_MICRO_SCENES_MIN = 28
TARGET_DISTINCT_MICRO_SCENES_MAX = 36
MIN_POOL_SITUATION_FAMILIES = 5
MIN_FORM_SITUATION_FAMILIES = 3
MAX_FORM_SCENES_FROM_SAME_FAMILY = 2
MIN_FORM_GAP_BEFORE_EXACT_SCENE_REUSE = 3
REUSED_SCENE_MIN_CHANGED_DIMENSIONS = 2

GENERIC_ACTIONS = {"", "A1_IMITATION", "PROJECT_CONTRACT_COMPLETION", "SEMANTIC_EQUIVALENT", "HUMAN_EXCEPTION"}
GENERIC_SETTINGS = {"", "UNIT01_OBJECT_SCENE", "GENERAL", "OBJECT_SCENE"}
RELATION_RE = re.compile(r"\b(in|on|near)\b", re.IGNORECASE)
FAMILY_MAP = {
    "CLASSROOM": "SCHOOL", "SCHOOL": "SCHOOL", "SCHOOL_LIBRARY": "SCHOOL",
    "HOME": "HOME", "ROOM": "HOME", "BEDROOM": "HOME", "KITCHEN": "HOME", "LIVING_ROOM": "HOME",
    "PARK": "OUTDOORS", "PLAYGROUND": "OUTDOORS", "GARDEN": "OUTDOORS",
    "PARK_AND_BIRTHDAY": "OUTDOORS_SOCIAL", "FOOD_AND_PICNIC": "FOOD_SOCIAL", "PICNIC": "FOOD_SOCIAL",
    "SHOP": "SHOPPING", "SHOPPING": "SHOPPING", "TOY_SHOP": "SHOPPING",
}

class InventoryBuildError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryBuildError(f"UNREADABLE_JSON:{path}:{exc}") from exc

def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def norm_strings(values: Iterable[Any] | None) -> list[str]:
    return sorted({str(v).strip().upper() for v in (values or []) if str(v).strip()})

def approved_assets(approved: Mapping[str, Any]) -> list[dict[str, Any]]:
    payload = approved.get("payload") if isinstance(approved.get("payload"), Mapping) else approved
    rows = payload.get("content_assets") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list) or not rows or not all(isinstance(r, Mapping) for r in rows):
        raise InventoryBuildError("CONTENT_ASSETS_REQUIRED")
    return [deepcopy(dict(r)) for r in rows]

def canonical_context_rows(value: Any) -> list[dict[str, Any]]:
    rows: Any = None
    if isinstance(value, list):
        rows = value
    elif isinstance(value, Mapping):
        if isinstance(value.get("contexts"), list):
            rows = value["contexts"]
        elif isinstance((value.get("tables") or {}).get("contexts"), list):
            rows = value["tables"]["contexts"]
        elif isinstance((value.get("payload") or {}).get("contexts"), list):
            rows = value["payload"]["contexts"]
    if not isinstance(rows, list) or not all(isinstance(r, Mapping) for r in rows):
        raise InventoryBuildError("CANONICAL_CONTEXT_ARRAY_MISSING")
    return [deepcopy(dict(r)) for r in rows]

def content_text(asset: Mapping[str, Any]) -> str:
    content = asset.get("content") or {}
    if not isinstance(content, Mapping):
        return ""
    parts = [str(v) for v in content.get("sentences") or [] if str(v).strip()]
    for turn in content.get("dialogue_turns") or []:
        if isinstance(turn, Mapping) and str(turn.get("utterance") or "").strip():
            parts.append(str(turn["utterance"]))
    return " ".join(parts)

def scene_relations(asset: Mapping[str, Any]) -> list[str]:
    return sorted({m.group(1).upper() for m in RELATION_RE.finditer(content_text(asset))})

def situation_family(setting: str, theme: str = "") -> str:
    key = str(setting or "").strip().upper().replace(" ", "_")
    if key in FAMILY_MAP:
        return FAMILY_MAP[key]
    theme_key = str(theme or "").strip().upper().replace(" ", "_")
    return {"FOOD": "FOOD_SOCIAL", "ANIMALS": "ANIMALS"}.get(theme_key, theme_key) if theme_key in {"SCHOOL", "HOME", "FOOD", "ANIMALS", "OUTDOORS", "SHOPPING"} else "UNCLASSIFIED_OBJECT"

def semantic_scene_core(*, setting: str, participants: Iterable[Any], objects: Iterable[Any], descriptors: Iterable[Any], actions: Iterable[Any], information_structure: Iterable[Any], communicative_functions: Iterable[Any], relations: Iterable[Any] = ()) -> dict[str, Any]:
    return {
        "setting": str(setting or "").strip().upper() or "UNSPECIFIED",
        "participants": norm_strings(participants),
        "objects": norm_strings(objects),
        "descriptors": norm_strings(descriptors),
        "actions": norm_strings(actions),
        "relations": norm_strings(relations),
        "information_structure": norm_strings(information_structure),
        "communicative_function_ids": norm_strings(communicative_functions),
    }

def rotation_class_for_asset(asset: Mapping[str, Any], core: Mapping[str, Any]) -> tuple[str, list[str]]:
    lineage = asset.get("source_lineage") or {}
    mode = str(lineage.get("lineage_mode") or "") if isinstance(lineage, Mapping) else ""
    admission = asset.get("admission") or {}
    if mode == "PROJECT_AUTHORED_CONTRACT_COMPLETION":
        return "COVERAGE_COMPLETION_NOT_SCENE", ["PROJECT_AUTHORED_GAP_COMPLETION"]
    if isinstance(admission, Mapping) and bool(admission.get("template_only")):
        return "TEMPLATE_ONLY_NOT_SCENE", ["TEMPLATE_ONLY"]
    reasons: list[str] = []
    if str(core["setting"]) in GENERIC_SETTINGS or str(core["setting"]) == "UNSPECIFIED":
        reasons.append("GENERIC_OR_UNSPECIFIED_SETTING")
    objects = set(core["objects"]); actions = set(core["actions"]); relations = set(core["relations"])
    if not objects:
        reasons.append("NO_SCENE_OBJECT")
    if not (actions - GENERIC_ACTIONS or relations or len(objects) >= 2):
        reasons.append("OBJECT_ONLY_OR_UNDER_SPECIFIED_EVENT")
    if not core["communicative_function_ids"]:
        reasons.append("NO_COMMUNICATIVE_FUNCTION")
    return ("SCENE_SEED_NEEDS_ENRICHMENT", reasons) if reasons else ("ROTATION_READY", [])

def asset_scene_row(asset: Mapping[str, Any]) -> dict[str, Any]:
    scene = asset.get("scene_profile") or {}; alignment = asset.get("target_alignment") or {}
    if not isinstance(scene, Mapping):
        raise InventoryBuildError(f"SCENE_PROFILE_REQUIRED:{asset.get('content_asset_id')}")
    if not isinstance(alignment, Mapping): alignment = {}
    core = semantic_scene_core(
        setting=str(scene.get("setting") or alignment.get("situation_family_id") or ""),
        participants=scene.get("participants") or [], objects=scene.get("objects") or alignment.get("active_nouns") or [],
        descriptors=scene.get("descriptors") or alignment.get("active_adjectives") or [], actions=scene.get("actions") or [],
        relations=scene_relations(asset), information_structure=scene.get("information_structure") or [],
        communicative_functions=scene.get("communicative_function_ids") or alignment.get("communicative_function_ids") or [],
    )
    klass, reasons = rotation_class_for_asset(asset, core)
    lineage = asset.get("source_lineage") or {}; mode = str(lineage.get("lineage_mode") or "") if isinstance(lineage, Mapping) else ""
    return {
        "scene_origin": "REAL62_CONTENT_ASSET", "scene_ref_id": str(asset.get("content_asset_id") or ""),
        "legacy_micro_situation_id": str(alignment.get("micro_situation_id") or ""),
        "legacy_semantic_scene_id": str(scene.get("semantic_scene_id") or ""),
        "legacy_distinct_scene_signature": str(scene.get("distinct_scene_signature") or ""),
        "semantic_scene_signature_v2": digest(core), "semantic_scene_core": core,
        "situation_family": situation_family(core["setting"], str(alignment.get("theme_id") or "")),
        "theme_id": str(alignment.get("theme_id") or ""), "content_kind": str(asset.get("content_kind") or ""),
        "lineage_mode": mode, "source_authority": str(lineage.get("source_authority") or "") if isinstance(lineage, Mapping) else "",
        "rotation_class": klass, "rotation_reason_codes": reasons, "counts_toward_scene_rotation": klass == "ROTATION_READY",
    }

def canonical_context_scene_row(row: Mapping[str, Any]) -> dict[str, Any]:
    context_id = str(row.get("context_id") or "").strip(); setting = str(row.get("setting") or "").strip().upper()
    if not context_id or not setting:
        raise InventoryBuildError("CANONICAL_CONTEXT_ID_AND_SETTING_REQUIRED")
    core = semantic_scene_core(setting=setting, participants=["LEARNER"], objects=[], descriptors=[], actions=["CANONICAL_CONTEXT_USE"], relations=[], information_structure=["FIRST_MENTION", "KNOWN_REFERENCE"], communicative_functions=["IDENTIFY", "DESCRIBE"])
    core["context_role"] = str(row.get("context_role") or row.get("role") or "").strip().upper()
    core["source_role"] = str(row.get("source_role") or "").strip().upper()
    return {
        "scene_origin": "CANONICAL_UNIT01_CONTEXT", "scene_ref_id": context_id, "legacy_micro_situation_id": context_id,
        "legacy_semantic_scene_id": "", "legacy_distinct_scene_signature": "", "semantic_scene_signature_v2": digest(core),
        "semantic_scene_core": core, "situation_family": situation_family(setting), "theme_id": "", "content_kind": "CANONICAL_CONTEXT",
        "lineage_mode": "EXISTING_UNIT01_CONTEXT_AUTHORITY", "source_authority": str(row.get("source_role") or ""),
        "rotation_class": "ROTATION_READY", "rotation_reason_codes": [], "counts_toward_scene_rotation": True,
    }

def duplicate_groups(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows: groups[str(row["semantic_scene_signature_v2"])].append(row)
    return [{"semantic_scene_signature_v2": sig, "member_count": len(members), "scene_ref_ids": sorted(str(r["scene_ref_id"]) for r in members), "rotation_ready_member_count": sum(bool(r["counts_toward_scene_rotation"]) for r in members)} for sig, members in sorted(groups.items()) if len(members) > 1]

def unique_rotation_scenes(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["counts_toward_scene_rotation"]: groups[str(row["semantic_scene_signature_v2"])].append(row)
    result = []
    for sig, members in sorted(groups.items()):
        rep = members[0]
        result.append({"semantic_scene_signature_v2": sig, "representative_scene_ref_id": str(rep["scene_ref_id"]), "member_scene_ref_ids": sorted(str(r["scene_ref_id"]) for r in members), "situation_family": str(rep["situation_family"]), "setting": str(rep["semantic_scene_core"]["setting"]), "origin_set": sorted({str(r["scene_origin"]) for r in members})})
    return result

def build_inventory(approved_content: Mapping[str, Any], canonical_context_input: Any, *, approved_content_sha256: str = "", canonical_context_sha256: str = "") -> dict[str, Any]:
    assets = approved_assets(approved_content); contexts = canonical_context_rows(canonical_context_input)
    rows = [asset_scene_row(a) for a in assets] + [canonical_context_scene_row(c) for c in contexts]
    unique = unique_rotation_scenes(rows); families = Counter(r["situation_family"] for r in unique)
    classes = Counter(r["rotation_class"] for r in rows)
    modes = Counter(r["lineage_mode"] for r in rows if r["scene_origin"] == "REAL62_CONTENT_ASSET")
    source_count = sum(r["scene_origin"] == "REAL62_CONTENT_ASSET" and r["lineage_mode"] != "PROJECT_AUTHORED_CONTRACT_COMPLETION" for r in rows)
    project_count = sum(r["scene_origin"] == "REAL62_CONTENT_ASSET" and r["lineage_mode"] == "PROJECT_AUTHORED_CONTRACT_COMPLETION" for r in rows)
    distinct = len(unique); family_count = len([k for k, v in families.items() if v and k != "UNCLASSIFIED_OBJECT"])
    hard_pass = distinct >= HARD_MIN_DISTINCT_MICRO_SCENES; family_pass = family_count >= MIN_POOL_SITUATION_FAMILIES; ready = hard_pass and family_pass
    inventory: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "program_id": PROGRAM_ID, "task_id": TASK_ID, "status": PASS_STATUS, "unit_id": UNIT_ID,
        "scope": {"unit01_only": True, "question_bank_modified": False, "parallel_question_bank_created": False, "parallel_scoring_created": False, "unit02_to_unit24_modified": False, "a2_unlocked": False},
        "source_identity": {"approved_content_sha256": approved_content_sha256, "canonical_context_sha256": canonical_context_sha256},
        "inventory_policy": {"semantic_scene_signature_version": 2, "source_identity_in_semantic_signature": False, "project_authored_gap_completion_counts_as_genuine_scene": False, "under_specified_object_only_asset_counts_as_genuine_scene": False, "canonical_unit01_context_counts_as_genuine_scene": True},
        "rotation_policy": {"form_count": FORM_COUNT, "scenes_per_form": SCENES_PER_FORM, "total_scene_slots": TOTAL_SCENE_SLOTS, "max_exposures_per_exact_micro_scene": MAX_EXPOSURES_PER_EXACT_SCENE, "hard_min_distinct_micro_scenes": HARD_MIN_DISTINCT_MICRO_SCENES, "target_distinct_micro_scenes": [TARGET_DISTINCT_MICRO_SCENES_MIN, TARGET_DISTINCT_MICRO_SCENES_MAX], "min_pool_situation_families": MIN_POOL_SITUATION_FAMILIES, "min_form_situation_families": MIN_FORM_SITUATION_FAMILIES, "max_form_scenes_from_same_family": MAX_FORM_SCENES_FROM_SAME_FAMILY, "min_form_gap_before_exact_scene_reuse": MIN_FORM_GAP_BEFORE_EXACT_SCENE_REUSE, "reused_scene_min_changed_dimensions": REUSED_SCENE_MIN_CHANGED_DIMENSIONS, "same_scene_same_skill_same_task_angle_repeat_allowed": False},
        "raw_counts": {"approved_content_asset_count": len(assets), "source_derived_asset_count": source_count, "project_authored_completion_asset_count": project_count, "canonical_context_count": len(contexts), "inventory_row_count": len(rows)},
        "classification_counts": dict(sorted(classes.items())), "lineage_mode_counts": dict(sorted(modes.items())), "situation_family_counts": dict(sorted(families.items())),
        "semantic_duplicate_groups": duplicate_groups(rows), "unique_rotation_scenes": unique, "scene_rows": rows,
        "rotation_readiness": {"genuine_distinct_micro_scene_count": distinct, "non_unclassified_situation_family_count": family_count, "maximum_scene_slots_at_two_uses_each": distinct * MAX_EXPOSURES_PER_EXACT_SCENE, "required_scene_slots": TOTAL_SCENE_SLOTS, "hard_distinct_scene_capacity_pass": hard_pass, "situation_family_capacity_pass": family_pass, "twelve_form_rotation_ready": ready, "scene_shortfall_to_hard_min": max(0, HARD_MIN_DISTINCT_MICRO_SCENES - distinct), "scene_shortfall_to_target_min": max(0, TARGET_DISTINCT_MICRO_SCENES_MIN - distinct), "family_shortfall": max(0, MIN_POOL_SITUATION_FAMILIES - family_count), "release_classification": "READY_FOR_12_FORM_ROTATION" if ready else "NOT_READY_SCENE_POOL_SUPPLEMENTATION_REQUIRED"},
        "boundaries": {"content_assets_mutated": False, "canonical_contexts_mutated": False, "question_items_mutated": False, "learner_state_mutated": False, "scoring_mutated": False, "mastery_claimed": False},
        "next_short_step": NEXT_SHORT_STEP,
    }
    inventory["inventory_sha256"] = digest(inventory)
    return inventory

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-content", type=Path, required=True); parser.add_argument("--canonical-contexts", type=Path, required=True); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        inventory = build_inventory(read_json(args.approved_content), read_json(args.canonical_contexts), approved_content_sha256=file_sha256(args.approved_content), canonical_context_sha256=file_sha256(args.canonical_contexts))
        write_json(args.output, inventory)
    except (InventoryBuildError, KeyError, TypeError, ValueError, OSError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB06_UNIT01_MICRO_SCENE_POOL_INVENTORY"); print(f"ERROR={exc}"); return 1
    r = inventory["rotation_readiness"]
    print(f"STATUS={PASS_STATUS}"); print(f"APPROVED_CONTENT_ASSETS={inventory['raw_counts']['approved_content_asset_count']}"); print(f"CANONICAL_CONTEXTS={inventory['raw_counts']['canonical_context_count']}"); print(f"GENUINE_DISTINCT_MICRO_SCENES={r['genuine_distinct_micro_scene_count']}"); print(f"SITUATION_FAMILIES={r['non_unclassified_situation_family_count']}"); print(f"TWELVE_FORM_ROTATION_READY={r['twelve_form_rotation_ready']}"); print(f"SCENE_SHORTFALL_TO_24={r['scene_shortfall_to_hard_min']}"); print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
