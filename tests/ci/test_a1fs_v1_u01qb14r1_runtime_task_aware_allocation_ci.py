from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u01qb12
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as r1
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as patch
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator


CANONICAL_FAMILY = {
    "U01-C1-CLASSROOM-BAG": "SCHOOL",
    "U01-C2-HOME-TOY-BOX": "HOME",
    "U01-C3-PICNIC-FOOD": "FOOD_SOCIAL",
    "U01-C4-TOY-SHOP": "SHOPPING",
    "U01-C5-PARK-BIRTHDAY": "OUTDOORS_SOCIAL",
}


def _legacy_rotation() -> dict:
    rows = []
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
    original = u01qb08.approved_scene_rows
    fake = {
        "artifact_sha256": "a" * 64,
        "artifact_role": "APPROVED_CANONICAL_JSON",
        "payload": {"task_id": u01qb07.TASK_ID},
    }
    try:
        u01qb08.approved_scene_rows = lambda _approved: deepcopy(rows)
        return u01qb08.build_rotation(fake)
    finally:
        u01qb08.approved_scene_rows = original


def _runtime_db(path: Path) -> None:
    base = [deepcopy(row) for row in u01qb12.reconciled_payload()["reconciled_items"]]
    assert len(base) == 288
    extension = []
    for index in range(186):
        row = deepcopy(base[index % len(base)])
        row["item_id"] = f"FIXTURE-EXT-{index:03d}"
        extension.append(row)
    rows = base + extension
    assert len(rows) == 474
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE u01qb02_item_catalog(item_id TEXT PRIMARY KEY,skill TEXT NOT NULL,pattern_family_id TEXT NOT NULL,private_item_json TEXT NOT NULL)"
        )
        connection.execute("CREATE TABLE u01qb12_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO u01qb12_metadata(key,value) VALUES('validation_status',?)",
            (u01qb12.PASS_STATUS,),
        )
        connection.executemany(
            "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?)",
            [
                (
                    row["item_id"],
                    row["skill"],
                    row["pattern_family_id"],
                    json.dumps(row, ensure_ascii=False, sort_keys=True),
                )
                for row in rows
            ],
        )


def test_pf17_is_not_universally_available_for_every_active_noun(tmp_path: Path) -> None:
    db = tmp_path / "runtime.sqlite3"
    _runtime_db(db)
    catalog = patch._catalog(db)
    active = r1.active_unit01_nouns()
    pf17_nouns = {
        str((json.loads(row["private_item_json"]).get("lexical_slots") or {}).get("noun") or "").casefold()
        for row in catalog["WRITING"]
        if row["pattern_family_id"] == u01qb13.PF17
    }
    missing = sorted(active - pf17_nouns)
    assert missing, "fixture unexpectedly gives PF17 to every active noun"
    noun = missing[0]
    assert patch._candidate_item_ids(
        skill="WRITING",
        angle="PHRASE_CONSTRUCTION",
        anchors={noun},
        situation_family="HOME",
        catalog=catalog,
    ) == ()
    assert patch._candidate_item_ids(
        skill="WRITING",
        angle="WORD_ORDER",
        anchors={noun},
        situation_family="HOME",
        catalog=catalog,
    )


def test_runtime_aware_allocation_proves_all_36_skill_sessions_have_distinct_item_capacity(tmp_path: Path) -> None:
    db = tmp_path / "runtime.sqlite3"
    _runtime_db(db)
    rotation = r1.rematerialize_rotation(_legacy_rotation())
    allocation = patch.build_runtime_aware_allocation(rotation, db)
    u01qb09_validator.validate(allocation)
    gate = allocation["runtime_task_bindability"]
    assert gate["source_runtime_item_count"] == 474
    assert gate["verified_activity_count"] == 240
    assert gate["all_240_activities_runtime_compatible"] is True
    assert gate["all_36_skill_sessions_distinct_item_capacity_proven"] is True
    metrics = allocation["allocation_metrics"]
    assert metrics["form_count"] == 12
    assert metrics["scene_exposure_count"] == 48
    assert metrics["activity_slot_count"] == 240
    assert metrics["scored_activity_slot_count"] == 192
    assert metrics["speaking_practice_slot_count"] == 48


def test_every_emitted_activity_has_real_runtime_candidates(tmp_path: Path) -> None:
    db = tmp_path / "runtime.sqlite3"
    _runtime_db(db)
    catalog = patch._catalog(db)
    rotation = r1.rematerialize_rotation(_legacy_rotation())
    allocation = patch.build_runtime_aware_allocation(rotation, db)
    semantics = r1.tolerant_scene_semantic_index()
    for form in allocation["forms"]:
        for scene in form["scene_packages"]:
            anchors = {str(row).casefold() for row in semantics[scene["scene_ref_id"]]["anchors"]}
            family = scene["situation_family"]
            for activity in scene["activities"]:
                candidates = patch._candidate_item_ids(
                    skill=activity["skill"],
                    angle=activity["task_angle"],
                    anchors=anchors,
                    situation_family=family,
                    catalog=catalog,
                )
                assert candidates
                assert activity["runtime_compatible_item_count"] == len(candidates)
