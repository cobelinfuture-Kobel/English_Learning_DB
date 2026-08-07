from __future__ import annotations

import inspect
import sqlite3

import pytest

from product.a1fs_v1_2_1 import u01qb18a_form01_fresh_learner_materialization_export as exporter


def _fixture_payloads():
    skill_payloads = {}
    blueprint_rows = []
    counters = {"READING": 0, "WRITING": 0, "SPEAKING": 0}
    items_by_skill = {"READING": [], "WRITING": [], "SPEAKING": []}

    # Match the logical Form shape: 4 scenes x (2 Reading + 2 Writing + 1 Speaking).
    activity_number = 0
    for scene_number in range(1, 5):
        scene_ref = f"SCENE-{scene_number:02d}"
        setting = f"Setting {scene_number}"
        for skill in ("READING", "READING", "WRITING", "WRITING", "SPEAKING"):
            activity_number += 1
            counters[skill] += 1
            activity_id = f"F01-S{scene_number:02d}-A{activity_number:02d}"
            blueprint_rows.append(
                {
                    "activity_id": activity_id,
                    "form_id": "U01-FORM-01",
                    "form_ordinal": 1,
                    "scene_ref_id": scene_ref,
                    "situation_family": "HOME" if scene_number % 2 else "SCHOOL",
                    "setting": setting,
                    "skill": skill,
                    "task_angle": "FIXTURE_ANGLE",
                    "support_level": "GUIDED",
                }
            )
            speaking = skill == "SPEAKING"
            items_by_skill[skill].append(
                {
                    "activity_id": activity_id,
                    "item_id": f"ITEM-{skill}-{counters[skill]:02d}",
                    "scene_ref_id": scene_ref,
                    "setting": setting,
                    "skill": skill,
                    "stimulus": "" if speaking else f"Stimulus {activity_number}",
                    "prompt": f"Prompt {activity_number}",
                    "options": [] if speaking else ["a", "an", "the"],
                    "response_mode": "practice_only" if speaking else "select_one",
                    "capture_enabled": not speaking,
                    "practice_only": speaking,
                }
            )

    for skill in exporter.SKILLS:
        skill_payloads[skill] = {
            "form_id": "U01-FORM-01",
            "form_ordinal": 1,
            "skill": skill,
            "items": items_by_skill[skill],
        }
    return skill_payloads, blueprint_rows


def test_form01_export_contract_is_exactly_four_scenes_and_twenty_learner_activities() -> None:
    skill_payloads, blueprint_rows = _fixture_payloads()
    value = exporter._compose_export(
        learner_id=exporter.DEFAULT_LEARNER_ID,
        cutover={
            "questionbank_revision": "U01QB15-R1",
            "runtime_item_count": 474,
            "extension_item_count": 186,
            "real62_artifact_sha256": "a" * 64,
        },
        source_snapshot_sha256="b" * 64,
        skill_payloads=skill_payloads,
        blueprint_rows=blueprint_rows,
    )

    student = value["student_form"]
    assert value["validation_status"] == exporter.PASS_STATUS
    assert student["form_ordinal"] == 1
    assert student["learner_mode"] == "FRESH"
    assert student["scene_count"] == 4
    assert student["learner_visible_activity_count"] == 20
    assert student["skill_counts"] == {"READING": 8, "WRITING": 8, "SPEAKING": 4}
    assert [row["question_number"] for row in student["activities"]] == [
        f"Q{index:02d}" for index in range(1, 21)
    ]
    assert {row["scene_ref_id"] for row in student["activities"]} == {
        "SCENE-01",
        "SCENE-02",
        "SCENE-03",
        "SCENE-04",
    }


def test_export_contains_only_learner_render_fields_not_answers_or_engineering_metadata() -> None:
    skill_payloads, blueprint_rows = _fixture_payloads()
    value = exporter._compose_export(
        learner_id=exporter.DEFAULT_LEARNER_ID,
        cutover={
            "questionbank_revision": "U01QB15-R1",
            "runtime_item_count": 474,
            "extension_item_count": 186,
            "real62_artifact_sha256": "a" * 64,
        },
        source_snapshot_sha256="b" * 64,
        skill_payloads=skill_payloads,
        blueprint_rows=blueprint_rows,
    )
    allowed = {
        "question_number",
        "skill",
        "scene_ref_id",
        "setting",
        "stimulus",
        "prompt",
        "options",
        "response_mode",
        "capture_enabled",
        "practice_only",
    }
    for activity in value["student_form"]["activities"]:
        assert set(activity) == allowed
        assert not (set(activity) & exporter.FORBIDDEN_EXPORT_KEYS)
    assert value["pdf_contract"] == {
        "show_engineering_metadata": False,
        "show_answers": False,
        "render_stimulus": True,
        "render_options_or_answer_area": True,
    }


def test_answer_side_key_guard_fails_closed() -> None:
    with pytest.raises(exporter.Form01MaterializationError, match="ANSWER_OR_PRIVATE_KEY_EXPORTED"):
        exporter._assert_no_answer_leak(
            {
                "activities": [
                    {
                        "prompt": "Choose one.",
                        "correct_answer": "an",
                    }
                ]
            }
        )


def test_exporter_delegates_to_existing_product_selector_and_never_authors_items() -> None:
    source = inspect.getsource(exporter._materialize_skill)
    assert "impl.matching.install()" in source
    assert "u13.assemble_form_component(" in source
    assert "impl.learner_form_payload(" in source
    assert "private_item_json" not in source
    assert exporter.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert exporter.A1FS_CONTENT_POLICY_EXEMPTION


def test_runtime_proof_freezes_474_plus_real62_and_source_db_immutability() -> None:
    skill_payloads, blueprint_rows = _fixture_payloads()
    value = exporter._compose_export(
        learner_id=exporter.DEFAULT_LEARNER_ID,
        cutover={
            "questionbank_revision": "U01QB15-R1",
            "runtime_item_count": 474,
            "extension_item_count": 186,
            "real62_artifact_sha256": "c" * 64,
        },
        source_snapshot_sha256="d" * 64,
        skill_payloads=skill_payloads,
        blueprint_rows=blueprint_rows,
    )
    proof = value["runtime_proof"]
    assert proof["runtime_item_count"] == 474
    assert proof["real62_extension_item_count"] == 186
    assert proof["formal_selector"] == "U01QB13/U01QB16_PRODUCT_MATCHING_PATH"
    assert proof["support_fillers_exposed_to_learner"] is False
    assert proof["source_production_database_modified"] is False
    assert proof["questionbank_modified"] is False
    assert proof["new_question_items_authored"] == 0
    assert value["next_short_step"] == exporter.NEXT_SHORT_STEP


def test_windows_snapshot_cleanup_fullfix_uses_explicit_closing_and_gc_boundary() -> None:
    snapshot_source = inspect.getsource(exporter._sqlite_snapshot)
    absent_source = inspect.getsource(exporter._assert_fresh_learner_absent)
    blueprint_source = inspect.getsource(exporter._blueprint_order)
    materialize_source = inspect.getsource(exporter.materialize_fresh_form01)

    assert "closing(sqlite3.connect(source))" in snapshot_source
    assert "closing(" in snapshot_source and "sqlite3.connect(target)" in snapshot_source
    assert "closing(sqlite3.connect(database))" in absent_source
    assert "closing(sqlite3.connect(database))" in blueprint_source
    assert "_ClosingLearnerStateStore(snapshot)" in materialize_source
    assert "gc.collect()" in materialize_source


def test_closing_m3_session_snapshot_releases_connection(tmp_path, monkeypatch) -> None:
    database = tmp_path / "closing_store.sqlite3"
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE learning_sessions(session_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL)"
    )
    connection.execute("INSERT INTO learning_sessions VALUES(?,?)", ("S1", "L1"))
    connection.commit()

    store = exporter._ClosingLearnerStateStore(database)
    monkeypatch.setattr(store, "_connect", lambda: connection)
    assert store.session_snapshot("S1") == {"session_id": "S1", "learner_id": "L1"}

    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")
