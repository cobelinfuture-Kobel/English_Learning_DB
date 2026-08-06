from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package
from ulga.builders import _u01qb16c_existing_product_unbound_form_progression_overlay as overlay
from ulga.builders import _u01qb16c_unbound_progression_runtime_hook as hook
from ulga.builders import (
    build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09,
)
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13,
)


def _insert_activity(
    connection: sqlite3.Connection,
    *,
    activity_id: str,
    form_ordinal: int,
    scene_ref_id: str,
    skill: str,
    task_angle: str,
    support: str,
) -> None:
    if skill == "READING":
        families = list(u13.EXACT_SCORED_BINDINGS[("READING", task_angle)])
        scored = 1
    elif skill == "WRITING":
        families = list(u13.EXACT_SCORED_BINDINGS[("WRITING", "WORD_ORDER")])
        scored = 1
    else:
        families = list(u13.SPEAKING_LEXICAL_FAMILIES)
        scored = 0
    connection.execute(
        """INSERT INTO u01qb13_blueprint_activities
        (activity_id,form_id,form_ordinal,scene_ref_id,situation_family,setting,skill,task_angle,
         support_level,scored,assessment_candidate,pattern_family_ids_json,scene_anchors_json,
         practice_projection_json,activity_digest)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            activity_id,
            f"U01-F{form_ordinal:02d}",
            form_ordinal,
            scene_ref_id,
            "OUTDOORS",
            "park",
            skill,
            task_angle,
            support,
            scored,
            int(form_ordinal >= 10 and scored),
            json.dumps(families, separators=(",", ":")),
            '["tree"]',
            "{}",
            f"OLD-{activity_id}",
        ),
    )


def _build_cutover_database(path: Path, *, bound_reading_form: int | None = None) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE u01qb15_product_consumer_cutover(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE u01qb13_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE u01qb02_item_catalog(item_id TEXT PRIMARY KEY);
            CREATE TABLE u01qb13_blueprint_activities(
              activity_id TEXT PRIMARY KEY,
              form_id TEXT NOT NULL,
              form_ordinal INTEGER NOT NULL,
              scene_ref_id TEXT NOT NULL,
              situation_family TEXT NOT NULL,
              setting TEXT NOT NULL,
              skill TEXT NOT NULL,
              task_angle TEXT NOT NULL,
              support_level TEXT NOT NULL,
              scored INTEGER NOT NULL,
              assessment_candidate INTEGER NOT NULL,
              pattern_family_ids_json TEXT NOT NULL,
              scene_anchors_json TEXT NOT NULL,
              practice_projection_json TEXT NOT NULL,
              activity_digest TEXT NOT NULL UNIQUE
            );
            CREATE TABLE u01qb13_session_bindings(
              session_id TEXT NOT NULL,
              activity_id TEXT NOT NULL,
              item_id TEXT NOT NULL,
              item_position INTEGER NOT NULL,
              binding_quality TEXT NOT NULL,
              is_assessment_evidence INTEGER NOT NULL
            );
            CREATE TABLE learner_profiles(learner_id TEXT PRIMARY KEY,display_name TEXT NOT NULL);
            CREATE TABLE learning_sessions(session_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL,skill TEXT NOT NULL,session_state TEXT NOT NULL);
            """
        )
        connection.execute(
            "INSERT INTO u01qb15_product_consumer_cutover VALUES(?,?)",
            ("validation_status", overlay.CUTOVER_PASS_STATUS),
        )
        connection.execute(
            "INSERT INTO u01qb13_metadata VALUES(?,?)",
            ("validation_status", u13.PASS_STATUS),
        )
        connection.execute("INSERT INTO learner_profiles VALUES('L','Learner')")
        connection.executemany(
            "INSERT INTO u01qb02_item_catalog VALUES(?)",
            [(f"ITEM-{index:03d}",) for index in range(1, 475)],
        )

        for form_ordinal in range(1, 13):
            support = u09.support_for_form(form_ordinal)
            for scene_ordinal in range(1, 5):
                scene_ref = f"F{form_ordinal:02d}-S{scene_ordinal:02d}"
                _insert_activity(
                    connection,
                    activity_id=f"F{form_ordinal:02d}-S{scene_ordinal:02d}-R01",
                    form_ordinal=form_ordinal,
                    scene_ref_id=scene_ref,
                    skill="READING",
                    task_angle="ARTICLE_CONTROL",
                    support=support,
                )
                _insert_activity(
                    connection,
                    activity_id=f"F{form_ordinal:02d}-S{scene_ordinal:02d}-R02",
                    form_ordinal=form_ordinal,
                    scene_ref_id=scene_ref,
                    skill="READING",
                    task_angle="FIRST_MENTION_CONTEXT",
                    support=support,
                )
                for index in range(1, 3):
                    _insert_activity(
                        connection,
                        activity_id=f"F{form_ordinal:02d}-S{scene_ordinal:02d}-W{index:02d}",
                        form_ordinal=form_ordinal,
                        scene_ref_id=scene_ref,
                        skill="WRITING",
                        task_angle="WORD_ORDER",
                        support=support,
                    )
                _insert_activity(
                    connection,
                    activity_id=f"F{form_ordinal:02d}-S{scene_ordinal:02d}-S01",
                    form_ordinal=form_ordinal,
                    scene_ref_id=scene_ref,
                    skill="SPEAKING",
                    task_angle="SCENE_DESCRIPTION",
                    support=support,
                )

        if bound_reading_form is not None:
            connection.execute(
                "INSERT INTO learning_sessions VALUES(?,?,?,?)",
                ("BOUND-READING", "L", "READING", "COMPLETED"),
            )
            rows = connection.execute(
                """SELECT activity_id FROM u01qb13_blueprint_activities
                   WHERE form_ordinal=? AND skill='READING' ORDER BY activity_id""",
                (bound_reading_form,),
            ).fetchall()
            for position, (activity_id,) in enumerate(rows, 1):
                connection.execute(
                    "INSERT INTO u01qb13_session_bindings VALUES(?,?,?,?,?,?)",
                    (
                        "BOUND-READING",
                        activity_id,
                        f"ITEM-{position:03d}",
                        position,
                        "TEST",
                        0,
                    ),
                )
        connection.commit()


def _install_fake_capacity_solver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(overlay.runtime_allocation, "_catalog", lambda _database: {})

    def solve(*, support, skill, scene_infos, prior_angles, catalog):
        assert skill == "READING"
        return {
            str(scene["scene_ref_id"]): (
                "ARTICLE_CONTROL",
                "KNOWN_REFERENCE_CONTEXT",
            )
            for scene in scene_infos
        }

    monkeypatch.setattr(overlay.runtime_allocation, "_solve_form_skill", solve)


def test_existing_bound_form_is_preserved_and_only_future_unbound_rows_migrate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "product.sqlite3"
    _build_cutover_database(database, bound_reading_form=1)
    _install_fake_capacity_solver(monkeypatch)

    with sqlite3.connect(database) as connection:
        before_profile = connection.execute("SELECT * FROM learner_profiles").fetchall()
        bound_before = connection.execute(
            """SELECT activity_id,task_angle,pattern_family_ids_json,activity_digest
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=1 AND skill='READING' ORDER BY activity_id"""
        ).fetchall()

    result = overlay.ensure_migrated(database)

    assert result["validation_status"] == overlay.PASS_STATUS
    assert result["idempotent_reuse"] is False
    assert result["preserved_bound_form_count"] == 1
    assert result["migrated_unbound_form_count"] == 11
    assert result["preserved_bound_reading_activity_count"] == 8
    assert result["updated_unbound_reading_activity_count"] == 44
    assert result["unchanged_unbound_reading_activity_count"] == 44
    assert result["learner_owned_state_unchanged"] is True
    assert result["historical_bound_activities_preserved"] is True
    assert result["questionbank_unchanged"] is True

    with sqlite3.connect(database) as connection:
        after_profile = connection.execute("SELECT * FROM learner_profiles").fetchall()
        bound_after = connection.execute(
            """SELECT activity_id,task_angle,pattern_family_ids_json,activity_digest
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=1 AND skill='READING' ORDER BY activity_id"""
        ).fetchall()
        future_angles = connection.execute(
            """SELECT task_angle,COUNT(*) FROM u01qb13_blueprint_activities
               WHERE form_ordinal>=2 AND skill='READING' GROUP BY task_angle ORDER BY task_angle"""
        ).fetchall()
        detail_count = connection.execute(
            f"SELECT COUNT(*) FROM {overlay.DETAIL_TABLE}"
        ).fetchone()[0]

    assert after_profile == before_profile
    assert bound_after == bound_before
    assert future_angles == [("ARTICLE_CONTROL", 44), ("KNOWN_REFERENCE_CONTEXT", 44)]
    assert detail_count == 96

    second = overlay.ensure_migrated(database)
    assert second["idempotent_reuse"] is True
    assert second["updated_unbound_reading_activity_count"] == 44


def test_partial_historical_reading_binding_fails_closed_without_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "partial.sqlite3"
    _build_cutover_database(database, bound_reading_form=1)
    _install_fake_capacity_solver(monkeypatch)
    with sqlite3.connect(database) as connection:
        activity_id = connection.execute(
            "SELECT activity_id FROM u01qb13_session_bindings ORDER BY activity_id LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "DELETE FROM u01qb13_session_bindings WHERE activity_id=?", (activity_id,)
        )
        connection.commit()

    with pytest.raises(
        overlay.UnboundProgressionOverlayError,
        match="PARTIAL_READING_FORM_BINDING:1:7",
    ):
        overlay.ensure_migrated(database)

    assert overlay.migration_status(database)["active"] is False


def test_product_runtime_installs_u01qb16c_hook_and_invokes_migration_before_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert product_package is not None
    assert hook.installed() is True
    assert u13.assemble_form_component is hook.assemble_form_component_with_progression_overlay

    database = tmp_path / "hook.sqlite3"
    database.touch()
    calls: list[Path] = []
    monkeypatch.setattr(hook.overlay, "migration_applicable", lambda _database: True)
    monkeypatch.setattr(
        hook.overlay,
        "ensure_migrated",
        lambda path: calls.append(Path(path)) or {"validation_status": overlay.PASS_STATUS},
    )
    monkeypatch.setattr(
        hook,
        "_ORIGINAL_ASSEMBLE_FORM_COMPONENT",
        lambda database, **kwargs: {"database": str(database), **kwargs},
    )

    result = hook.assemble_form_component_with_progression_overlay(
        database,
        learner_id="L",
        session_id="S",
        form_ordinal=2,
    )

    assert calls == [database]
    assert result["form_ordinal"] == 2
    assert result["learner_id"] == "L"
    assert result["session_id"] == "S"
