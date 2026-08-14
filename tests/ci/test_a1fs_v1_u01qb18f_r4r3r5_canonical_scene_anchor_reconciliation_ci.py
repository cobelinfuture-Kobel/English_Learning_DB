from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as authority
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r3r4_unbound_reading_formal_selector_parity_fullfix as r4r3r4
from ulga.builders import _u01qb18f_r4r3r5_canonical_scene_anchor_reconciliation_fullfix as r4r3r5
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)


def _prepare_base_288_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.execute(
            "INSERT INTO metadata(key,value) VALUES('validation_status',?)",
            (m3.STATUS,),
        )
        for skill, lesson_id in qb02.UNIT01_LESSONS.items():
            connection.execute(
                """INSERT INTO lesson_catalog
                (lesson_id,lesson_node_id,skill,level,roles_json,
                 requirement_node_ids_json,payload_access_allowed)
                VALUES(?,?,?,?,?,?,1)""",
                (lesson_id, f"NODE:{lesson_id}", skill, "A1", "[]", "[]"),
            )
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(path)
    initialized = runtime.initialize()
    assert initialized["registered_item_count"] == 288


def _shop04_reading_rows(anchor_json: str) -> list[dict[str, object]]:
    return [
        {
            "activity_id": f"R4R3R5-SHOP04-A{index:02d}",
            "form_ordinal": 8,
            "scene_ref_id": r4r3r5.SHOP04_REF,
            "situation_family": "SHOPPING",
            "setting": "TOY_SHOP",
            "skill": "READING",
            "task_angle": angle,
            "support_level": "INDEPENDENT",
            "scored": 1,
            "assessment_candidate": 0,
            "pattern_family_ids_json": "[]",
            "scene_anchors_json": anchor_json,
            "activity_digest": f"D-{index}",
        }
        for index, angle in enumerate(
            ("REFERENCE_EVIDENCE", "TRANSFER_DECISION"),
            start=1,
        )
    ]


def test_r4r3r5_compound_object_tokenization_preserves_scene_scope() -> None:
    assert r4r3r5.installed() is True
    package = authority.canonical_scene_package(r4r3r5.SHOP04_REF)
    assert package["scene_core"]["objects"] == ["ROBOT", "SHOP_WINDOW"]
    assert package["anchors"] == ["shop", "window"]
    assert package["unit_runtime_bindable"] is True

    report = authority.require_authority_pass()
    assert report["canonical_scene_count"] == 32
    assert report["unit01_runtime_bindable_scene_count"] == 31
    assert report["deferred_scene_refs"] == ["U01-MA-FOOD-04"]

    u13_index = u13._scene_semantic_index()
    assert u13_index[r4r3r5.SHOP04_REF]["anchors"] == ["shop", "window"]


def test_r4r3r5_public_288_e2e_proves_old_vs_canonical_shop04_reading_capacity(
    tmp_path: Path,
) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _prepare_base_288_database(database)
    catalog, scoring = r4r3r4._reading_state(database)

    old_options = r4r3r4._scene_options(
        _shop04_reading_rows('["shop"]'),
        prior=set(),
        catalog=catalog,
        scoring=scoring,
        session_id="R4R3R5-OLD-SHOP04",
    )
    canonical_options = r4r3r4._scene_options(
        _shop04_reading_rows('["shop","window"]'),
        prior=set(),
        catalog=catalog,
        scoring=scoring,
        session_id="R4R3R5-CANONICAL-SHOP04",
    )

    assert old_options == []
    assert canonical_options
    assert all(len(option) == 2 for option in canonical_options)


def _migration_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL
            );
            CREATE TABLE u01qb02_session_plans(session_id TEXT PRIMARY KEY);
            CREATE TABLE u01qb13_blueprint_activities(
              activity_id TEXT PRIMARY KEY,
              form_ordinal INTEGER NOT NULL,
              scene_ref_id TEXT NOT NULL,
              scene_anchors_json TEXT NOT NULL,
              activity_digest TEXT NOT NULL
            );
            CREATE TABLE u01qb13_session_bindings(
              session_id TEXT NOT NULL,
              activity_id TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO learning_sessions(session_id,learner_id) VALUES(?,?)",
            ("S1", "L1"),
        )
        refs = [
            r4r3r5.SHOP04_REF,
            "U01-MA-SHOP-01",
            "U01-MA-OUT-01",
            "U01-MA-SCH-01",
        ]
        rows = []
        for slot, ref in enumerate(refs, start=1):
            canonical = authority.canonical_scene_package(ref)["anchors"]
            anchors = '["shop"]' if ref == r4r3r5.SHOP04_REF else json.dumps(
                canonical,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            for activity in range(1, 6):
                rows.append(
                    (
                        f"F08-S{slot:02d}-A{activity:02d}",
                        8,
                        ref,
                        anchors,
                        f"D-{slot}-{activity}",
                    )
                )
        connection.executemany(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?)",
            rows,
        )


def test_r4r3r5_migrates_only_completely_unbound_form(tmp_path: Path) -> None:
    database = tmp_path / "migration.sqlite3"
    _migration_database(database)

    result = r4r3r5.migrate_unbound_form_scene_anchors(
        database,
        learner_id="L1",
        session_id="S1",
        form_ordinal=8,
    )
    assert result["action"] == "MIGRATED_UNBOUND_FORM_TO_CANONICAL_SCENE_ANCHORS"
    assert result["changed"] == 5
    with sqlite3.connect(database) as connection:
        anchors = {
            row[0]
            for row in connection.execute(
                "SELECT scene_anchors_json FROM u01qb13_blueprint_activities WHERE scene_ref_id=?",
                (r4r3r5.SHOP04_REF,),
            )
        }
        assert anchors == {'["shop","window"]'}
        assert connection.execute(
            f"SELECT COUNT(*) FROM {r4r3r5.MIGRATION_TABLE}"
        ).fetchone()[0] == 5

        connection.execute(
            "INSERT INTO u01qb13_session_bindings(session_id,activity_id) VALUES(?,?)",
            ("BOUND", "F08-S01-A01"),
        )
        connection.execute(
            "UPDATE u01qb13_blueprint_activities SET scene_anchors_json='[\"shop\"]' WHERE scene_ref_id=?",
            (r4r3r5.SHOP04_REF,),
        )
        connection.commit()

    frozen = r4r3r5.migrate_unbound_form_scene_anchors(
        database,
        learner_id="L1",
        session_id="S1",
        form_ordinal=8,
    )
    assert frozen["action"] == "SKIP_FORM_FROZEN_BY_PRIOR_BINDING"
    with sqlite3.connect(database) as connection:
        anchors = {
            row[0]
            for row in connection.execute(
                "SELECT scene_anchors_json FROM u01qb13_blueprint_activities WHERE scene_ref_id=?",
                (r4r3r5.SHOP04_REF,),
            )
        }
        assert anchors == {'["shop"]'}


def test_r4r3r5_owner_prehook_runs_before_existing_migrations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def record(name):
        def run(*_args, **_kwargs):
            calls.append(name)
            return {"status": "PASS", "changed": 0}
        return run

    monkeypatch.setattr(owner.r4r3r5, "migrate_unbound_form_scene_anchors", record("R4R3R5"))
    monkeypatch.setattr(owner.r4r3r1, "migrate_unbound_support_stage_scene_assignment", record("R4R3R1"))
    monkeypatch.setattr(owner.r4r3, "migrate_unbound_form_reuse_scene", record("R4R3"))
    monkeypatch.setattr(owner.r4r2, "migrate_unbound_writing_form", record("R4R2"))
    monkeypatch.setattr(
        owner,
        "_ORIGINAL_U16C_ASSEMBLER",
        lambda *_args, **_kwargs: calls.append("U16C") or {"status": "PASS"},
    )

    owner.assemble_form_component_with_writing_parity(
        Path("ignored.sqlite3"),
        learner_id="L1",
        session_id="S1",
        form_ordinal=8,
    )
    assert calls == ["R4R3R5", "R4R3R1", "R4R3", "R4R2", "U16C"]


def test_r4r3r5_is_non_content_producer() -> None:
    assert r4r3r5.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "authors no content" in r4r3r5.A1FS_CONTENT_POLICY_EXEMPTION
