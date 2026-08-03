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
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as builder
from ulga.builders import _razq01e_existing_qb_runtime_core as razq01e
from ulga.validators import validate_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as validator

EXTENSION_SHA = "d" * 64


def _approved_scene_pool() -> dict:
    semantics = builder._scene_semantic_index()
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
        producer_id="test_u01qb13_scene_pool",
        level_scope=["A1"],
        source_bindings={"test_fixture": True},
    )
    return content_policy.admit_candidate(
        candidate,
        validation_receipts=[
            {"validator_id": "test_scene_validator", "status": "PASS", "receipt_sha256": "0" * 64}
        ],
        decision_ref="TEST:U01QB13",
        producer_id="test_u01qb13_scene_pool_approval",
    )


def _rotation_and_allocation() -> tuple[dict, dict]:
    rotation = u01qb08.build_rotation(_approved_scene_pool())
    allocation = u01qb09.build_allocation(rotation)
    return rotation, allocation


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
        content_asset_id = f"FIXTURE-REAL62-U01QB13-{index:03d}"
        for skill in ("READING", "WRITING", "SPEAKING"):
            source = deepcopy(by_skill[skill][index % len(by_skill[skill])])
            source["item_id"] = f"U01QB01-RAZQ01E-{skill}-U01QB13-{index:03d}"
            source["content_asset_id"] = content_asset_id
            source["semantic_signature"] = qb02.digest(
                {
                    "fixture": "REAL62-U01QB13",
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


def _approved_blueprint() -> tuple[dict, dict, dict]:
    rotation, allocation = _rotation_and_allocation()
    candidate = builder.build_candidate(rotation, allocation)
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["error_count"] == 0
    return rotation, allocation, approved


def _start_session(path: Path, *, learner_id: str, skill: str, session_id: str) -> None:
    state = m3.LearnerStateStore(path)
    profile = state.create_profile(learner_id=learner_id, display_label=f"U01QB13 {skill}")
    state.start_session(
        learner_id=learner_id,
        lesson_id=qb02.UNIT01_LESSONS[skill],
        session_id=session_id,
        expected_profile_version=int(profile["profile"]["profile_version"]),
    )


def test_u01qb13_materializes_12_forms_240_activities_and_assessment_blueprint() -> None:
    _rotation, _allocation, approved = _approved_blueprint()
    payload = approved["payload"]
    assert len(payload["form_summaries"]) == 12
    assert len(payload["activities"]) == 240
    assert payload["coverage_readback"]["scored_activity_count"] == 192
    assert payload["coverage_readback"]["speaking_practice_activity_count"] == 48
    assert payload["coverage_readback"]["scored_unbound_count"] == 0
    assert payload["assessment_blueprint"]["assessment_form_ordinals"] == [10, 11, 12]
    for form in payload["form_summaries"]:
        assert form["activity_count"] == 20
        assert form["reading_activity_count"] == 8
        assert form["writing_activity_count"] == 8
        assert form["speaking_practice_count"] == 4
        assert form["scored_activity_count"] == 16
        if form["form_ordinal"] >= 10:
            assert form["formal_assessment_mode"] is True
            assert form["assessment_scored_activity_count"] == 16
        else:
            assert form["formal_assessment_mode"] is False
            assert form["assessment_scored_activity_count"] == 0


def test_u01qb13_installs_into_same_474_runtime_without_second_planner(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _install_u01qb12_runtime(database)
    _rotation, _allocation, approved = _approved_blueprint()
    installed = builder.install_blueprint(database, approved)
    assert installed["runtime_item_count"] == 474
    assert installed["installed_activity_count"] == 240
    assert installed["second_planner_created"] is False
    assert installed["second_runtime_created"] is False
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0] == 474
        assert connection.execute("SELECT COUNT(*) FROM u01qb13_blueprint_activities").fetchone()[0] == 240
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "u01qb02_session_plans" in tables
    assert "u01qb02_session_items" in tables
    assert "u01qb13_blueprint_activities" in tables
    assert "u01qb13_session_bindings" in tables


def test_u01qb13_form10_reading_and_writing_bind_exact_scene_aware_runtime_items(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _install_u01qb12_runtime(database)
    _rotation, _allocation, approved = _approved_blueprint()
    builder.install_blueprint(database, approved)

    _start_session(database, learner_id="u13-reading", skill="READING", session_id="u13-reading-session")
    reading = builder.assemble_form_component(
        database,
        learner_id="u13-reading",
        session_id="u13-reading-session",
        form_ordinal=10,
    )
    assert reading["form_id"] == "U01-FORM-10"
    assert reading["blueprint_activity_count"] == 8
    assert reading["support_filler_count"] == 2
    assert all(row["scored"] for row in reading["items"])
    assert all(row["assessment_candidate"] for row in reading["items"])
    assert all(row["selection_reason"] == "TRANSFER" for row in reading["items"])
    assert all(row["binding_quality"] in {"LEXICAL_ANCHOR", "LEXICAL_ANCHOR_AND_CONTEXT_FAMILY"} for row in reading["items"])

    _start_session(database, learner_id="u13-writing", skill="WRITING", session_id="u13-writing-session")
    writing = builder.assemble_form_component(
        database,
        learner_id="u13-writing",
        session_id="u13-writing-session",
        form_ordinal=10,
    )
    assert writing["blueprint_activity_count"] == 8
    assert writing["support_filler_count"] == 2
    assert all(row["assessment_candidate"] for row in writing["items"])
    assert all(row["selection_reason"] == "TRANSFER" for row in writing["items"])
    assert {row["task_angle"] for row in writing["items"]} >= {"CONNECTED_SENTENCE_PRODUCTION", "COMPLETE_SENTENCE_PRODUCTION"}


def test_u01qb13_speaking_is_scene_projected_practice_only_in_existing_runtime(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _install_u01qb12_runtime(database)
    _rotation, _allocation, approved = _approved_blueprint()
    builder.install_blueprint(database, approved)
    _start_session(database, learner_id="u13-speaking", skill="SPEAKING", session_id="u13-speaking-session")
    speaking = builder.assemble_form_component(
        database,
        learner_id="u13-speaking",
        session_id="u13-speaking-session",
        form_ordinal=10,
    )
    assert speaking["blueprint_activity_count"] == 4
    assert speaking["support_filler_count"] == 6
    assert speaking["speaking_scoring_enabled"] is False
    assert all(row["practice_only"] for row in speaking["items"])
    assert all(row["capture_enabled"] is False for row in speaking["items"])
    assert all(row["assessment_candidate"] is False for row in speaking["items"])
    assert all(row["prompt"].startswith("Say ") for row in speaking["items"])


def test_u01qb13_bound_items_use_existing_m3_m6_exposure_and_scoring(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _install_u01qb12_runtime(database)
    _rotation, _allocation, approved = _approved_blueprint()
    builder.install_blueprint(database, approved)
    learner_id = "u13-canary"
    session_id = "u13-canary-session"
    _start_session(database, learner_id=learner_id, skill="READING", session_id=session_id)
    component = builder.assemble_form_component(
        database,
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=10,
    )
    item = component["items"][0]
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    state = m3.LearnerStateStore(database)
    snapshot = state.session_snapshot(session_id)
    exposed = runtime.record_item_exposure(
        session_id=session_id,
        item_id=item["item_id"],
        expected_session_version=int(snapshot["session_version"]),
    )
    with sqlite3.connect(database) as connection:
        private_item = json.loads(connection.execute(
            "SELECT private_item_json FROM u01qb02_item_catalog WHERE item_id=?", (item["item_id"],)
        ).fetchone()[0])
    captured = runtime.capture_response(
        learner_id=learner_id,
        session_id=session_id,
        item_id=item["item_id"],
        response=private_item["correct_answer"],
        expected_session_version=int(exposed["session_version"]),
    )
    assert captured["outcome"] == "AUTO_PASS"
    assert captured["m6_response_capture_reused"] is True
    assert captured["parallel_scoring_created"] is False


def test_u01qb13_validator_rejects_speaking_assessment_drift() -> None:
    rotation, allocation = _rotation_and_allocation()
    candidate = builder.build_candidate(rotation, allocation)
    drifted = deepcopy(candidate)
    activity = next(row for row in drifted["payload"]["activities"] if row["skill"] == "SPEAKING")
    activity["assessment_candidate"] = True
    unsigned_payload = dict(drifted["payload"])
    unsigned_payload.pop("blueprint_sha256", None)
    drifted["payload"]["blueprint_sha256"] = builder.digest(unsigned_payload)
    unsigned_artifact = dict(drifted)
    unsigned_artifact.pop("artifact_sha256", None)
    drifted["artifact_sha256"] = content_policy.digest(unsigned_artifact)
    try:
        validator.validate_candidate(drifted)
    except validator.BlueprintIntegrationValidationError as exc:
        assert "SPEAKING_ASSESSMENT_CANDIDATE" in str(exc) or "ASSESSMENT_CANDIDATE_INVALID" in str(exc)
    else:
        raise AssertionError("validator accepted speaking assessment drift")
