from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u01qb12
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13
from ulga.builders import build_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance as builder
from ulga.builders import _razq01e_existing_qb_runtime_core as razq01e
from ulga.validators import validate_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance as validator

EXTENSION_SHA = "e" * 64


def _approved_scene_pool() -> dict:
    semantics = u01qb13._scene_semantic_index()
    family_by_ref = {
        "U01-C1-CLASSROOM-BAG": "SCHOOL",
        "U01-C2-HOME-TOY-BOX": "HOME",
        "U01-C3-PICNIC-FOOD": "FOOD_SOCIAL",
        "U01-C4-TOY-SHOP": "SHOPPING",
        "U01-C5-PARK-BIRTHDAY": "OUTDOORS_SOCIAL",
    }
    rows = []
    for ref in sorted(semantics):
        if ref in family_by_ref:
            family = family_by_ref[ref]
        elif ref.startswith("U01-MA-SCH-"):
            family = "SCHOOL"
        elif ref.startswith("U01-MA-HOME-"):
            family = "HOME"
        elif ref.startswith("U01-MA-SHOP-"):
            family = "SHOPPING"
        elif ref.startswith("U01-MA-OUT-"):
            family = "OUTDOORS"
        elif ref.startswith("U01-MA-FOOD-"):
            family = "FOOD_SOCIAL"
        elif ref.startswith("U01-MA-OSOC-"):
            family = "OUTDOORS_SOCIAL"
        else:
            raise AssertionError(ref)
        rows.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": u01qb08.scene_policy.digest({"scene_ref_id": ref}),
                "situation_family": family,
                "setting": semantics[ref]["setting"],
                "micro_scene_event_id": semantics[ref]["event"],
                "scene_origin": semantics[ref]["source"],
            }
        )
    assert len(rows) == 32
    payload = {
        "task_id": u01qb07.TASK_ID,
        "unit_id": u01qb07.UNIT_ID,
        "status": u01qb07.PASS_STATUS,
        "rotation_capacity": {"twelve_form_rotation_ready": True},
        "cumulative_unique_scenes": rows,
    }
    candidate = content_policy.build_candidate(
        payload=payload,
        producer_id="test_u01qb14_scene_pool",
        level_scope=["A1"],
        source_bindings={"test_fixture": True},
    )
    return content_policy.admit_candidate(
        candidate,
        validation_receipts=[
            {"validator_id": "test_scene_validator", "status": "PASS", "receipt_sha256": "0" * 64}
        ],
        decision_ref="TEST:U01QB14",
        producer_id="test_u01qb14_scene_pool_approval",
    )


def _rotation_and_allocation(tmp_path: Path) -> tuple[Path, Path]:
    rotation = u01qb08.build_rotation(_approved_scene_pool())
    allocation = u01qb09.build_allocation(rotation)
    rotation_path = tmp_path / "u01qb08_rotation.json"
    allocation_path = tmp_path / "u01qb09_allocation.json"
    rotation_path.write_text(json.dumps(rotation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    allocation_path.write_text(json.dumps(allocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rotation_path, allocation_path


def _prepare_m3_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.execute("INSERT INTO metadata(key,value) VALUES('validation_status',?)", (m3.STATUS,))
        for skill, lesson_id in qb02.UNIT01_LESSONS.items():
            connection.execute(
                """INSERT INTO lesson_catalog
                (lesson_id,lesson_node_id,skill,level,roles_json,requirement_node_ids_json,payload_access_allowed)
                VALUES(?,?,?,?,?,?,1)""",
                (lesson_id, f"NODE:{lesson_id}", skill, "A1", "[]", "[]"),
            )


def _fixture_extension_items() -> list[dict]:
    _approved, base_items = qb02.approved_bank()
    by_skill = {
        skill: [deepcopy(row) for row in base_items if row["skill"] == skill]
        for skill in ("READING", "WRITING", "SPEAKING")
    }
    result = []
    for index in range(62):
        content_asset_id = f"FIXTURE-REAL62-U01QB14-{index:03d}"
        for skill in ("READING", "WRITING", "SPEAKING"):
            source = deepcopy(by_skill[skill][index % len(by_skill[skill])])
            source["item_id"] = f"U01QB01-RAZQ01E-{skill}-U01QB14-{index:03d}"
            source["content_asset_id"] = content_asset_id
            source["semantic_signature"] = qb02.digest(
                {
                    "fixture": "REAL62-U01QB14",
                    "content_asset_id": content_asset_id,
                    "skill": skill,
                    "source": source["semantic_signature"],
                }
            )
            result.append(source)
    return result


def _install_u01qb12_runtime(path: Path) -> None:
    _prepare_m3_database(path)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(path)
    assert runtime.initialize()["registered_item_count"] == 288
    items = _fixture_extension_items()
    with runtime.write() as connection:
        connection.executescript(razq01e.EXTENSION_SQL)
        for item in items:
            razq01e._register_item(connection, item, approved_extension_sha256=EXTENSION_SHA)
        connection.executemany(
            "INSERT OR REPLACE INTO razq01e_metadata(key,value) VALUES(?,?)",
            {
                "task_id": razq01e.TASK_ID,
                "schema_version": razq01e.SCHEMA_VERSION,
                "validation_status": razq01e.PASS_STATUS,
                "approved_extension_artifact_sha256": EXTENSION_SHA,
                "extension_item_count": "186",
                "base_item_count": "288",
                "combined_runtime_item_count": "474",
                "existing_u01qb02_runtime_reused": "true",
                "parallel_runtime_created": "false",
                "a2_unlocked": "false",
            }.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "razq01e_extension_artifact_sha256": EXTENSION_SHA,
                "razq01e_extension_item_count": "186",
                "razq01e_combined_runtime_item_count": "474",
            }.items(),
        )
    migration = u01qb12.migrate_runtime(path)
    assert migration["combined_runtime_item_count"] == 474


def test_u01qb14_replays_all_twelve_forms_on_disposable_copy_and_never_mutates_source(tmp_path: Path) -> None:
    rotation_path, allocation_path = _rotation_and_allocation(tmp_path)
    canonical_db = tmp_path / "canonical.sqlite3"
    disposable_db = tmp_path / "disposable.sqlite3"
    _install_u01qb12_runtime(canonical_db)
    source_sha_before = builder.file_digest(canonical_db)
    source_mtime_before = canonical_db.stat().st_mtime_ns

    report = builder.run_private_replay(
        rotation_path=rotation_path,
        allocation_path=allocation_path,
        canonical_database=canonical_db,
        disposable_database=disposable_db,
    )
    validated = validator.validate_report(report)

    assert validated["canonical_database_unchanged"] is True
    assert builder.file_digest(canonical_db) == source_sha_before
    assert canonical_db.stat().st_mtime_ns == source_mtime_before
    assert builder.file_digest(disposable_db) != source_sha_before
    acceptance = report["execution_acceptance"]
    assert acceptance["form_count"] == 12
    assert acceptance["session_count"] == 36
    assert acceptance["blueprint_exposure_count"] == 240
    assert acceptance["response_attempt_count"] == 192
    assert acceptance["support_filler_exposure_count"] == 0
    assert acceptance["outcome_counts"] == {"AUTO_PASS": 156, "PENDING_HUMAN_REVIEW": 36}
    assert acceptance["assessment_scored_attempt_count"] == 48
    assert acceptance["assessment_speaking_practice_count"] == 12
    assert acceptance["assessment_transfer_selection_count"] == 48


def test_u01qb14_rejects_source_as_disposable_destination(tmp_path: Path) -> None:
    rotation_path, allocation_path = _rotation_and_allocation(tmp_path)
    canonical_db = tmp_path / "canonical.sqlite3"
    _install_u01qb12_runtime(canonical_db)
    try:
        builder.run_private_replay(
            rotation_path=rotation_path,
            allocation_path=allocation_path,
            canonical_database=canonical_db,
            disposable_database=canonical_db,
        )
    except builder.PrivateProductionReplayError as exc:
        assert "DISPOSABLE_DATABASE_MUST_DIFFER_FROM_CANONICAL" in str(exc)
    else:
        raise AssertionError("U01QB14 accepted the canonical DB as disposable destination")


def test_u01qb14_rejects_non_offline_canonical_database(tmp_path: Path) -> None:
    rotation_path, allocation_path = _rotation_and_allocation(tmp_path)
    canonical_db = tmp_path / "canonical.sqlite3"
    disposable_db = tmp_path / "disposable.sqlite3"
    _install_u01qb12_runtime(canonical_db)
    Path(str(canonical_db) + "-wal").write_bytes(b"not-offline")
    try:
        builder.run_private_replay(
            rotation_path=rotation_path,
            allocation_path=allocation_path,
            canonical_database=canonical_db,
            disposable_database=disposable_db,
        )
    except builder.PrivateProductionReplayError as exc:
        assert "CANONICAL_DATABASE_NOT_OFFLINE" in str(exc)
    else:
        raise AssertionError("U01QB14 accepted a canonical DB with a non-empty WAL")


def test_u01qb14_validator_rejects_false_canonical_safety_claim(tmp_path: Path) -> None:
    rotation_path, allocation_path = _rotation_and_allocation(tmp_path)
    canonical_db = tmp_path / "canonical.sqlite3"
    disposable_db = tmp_path / "disposable.sqlite3"
    _install_u01qb12_runtime(canonical_db)
    report = builder.run_private_replay(
        rotation_path=rotation_path,
        allocation_path=allocation_path,
        canonical_database=canonical_db,
        disposable_database=disposable_db,
    )
    drifted = deepcopy(report)
    drifted["canonical_database_safety"]["canonical_database_unchanged"] = False
    unsigned = dict(drifted)
    unsigned.pop("readback_sha256", None)
    drifted["readback_sha256"] = builder.digest(unsigned)
    try:
        validator.validate_report(drifted)
    except validator.PrivateProductionReplayValidationError as exc:
        assert "CANONICAL_DATABASE_CHANGED" in str(exc)
    else:
        raise AssertionError("validator accepted a false canonical safety claim")
