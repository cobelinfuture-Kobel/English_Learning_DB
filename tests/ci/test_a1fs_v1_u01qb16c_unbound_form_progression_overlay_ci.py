from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation,
)


def _database(tmp_path: Path, *, skill: str = "READING") -> Path:
    path = tmp_path / "learner.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              skill TEXT NOT NULL
            );
            CREATE TABLE u01qb02_session_plans(session_id TEXT PRIMARY KEY);
            CREATE TABLE u01qb02_item_catalog(item_id TEXT PRIMARY KEY);
            CREATE TABLE u01qb13_blueprint_activities(
              activity_id TEXT PRIMARY KEY,
              form_ordinal INTEGER NOT NULL,
              scene_ref_id TEXT NOT NULL,
              situation_family TEXT NOT NULL,
              skill TEXT NOT NULL,
              task_angle TEXT NOT NULL,
              support_level TEXT NOT NULL,
              pattern_family_ids_json TEXT NOT NULL,
              scene_anchors_json TEXT NOT NULL,
              activity_digest TEXT NOT NULL UNIQUE
            );
            CREATE TABLE u01qb13_session_bindings(
              session_id TEXT NOT NULL,
              activity_id TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?)",
            ("S2", "LEARNER", skill),
        )
        # Four scenes x two Reading activities. The actual migration planner is
        # separately proven by U01QB14R1/U01QB16B; these tests isolate the
        # existing-product no-history-rewrite invariant.
        for scene_index in range(1, 5):
            for activity_index in range(1, 3):
                activity_id = f"F02-S{scene_index:02d}-A{activity_index:02d}"
                angle = "ARTICLE_CONTROL" if activity_index == 1 else "FIRST_MENTION_CONTEXT"
                connection.execute(
                    "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        activity_id,
                        2,
                        f"SCENE-{scene_index}",
                        "OUTDOORS",
                        "READING",
                        angle,
                        "GUIDED",
                        '["U01-PF04-FIRST-MENTION-CONTEXT","U01-PF08-TRANSFER-FIRST-MENTION"]',
                        '["tree"]',
                        f"DIGEST-{scene_index}-{activity_index}",
                    ),
                )
        connection.commit()
    return path


def _one_change(rows):
    row = next(row for row in rows if str(row["activity_id"]) == "F02-S01-A02")
    return [
        {
            "activity_id": str(row["activity_id"]),
            "original_task_angle": str(row["task_angle"]),
            "effective_task_angle": "KNOWN_REFERENCE_CONTEXT",
            "original_pattern_family_ids_json": str(row["pattern_family_ids_json"]),
            "effective_pattern_family_ids_json": '["U01-PF05-KNOWN-REFERENCE-CONTEXT"]',
            "original_activity_digest": str(row["activity_digest"]),
            "effective_activity_digest": "U16C-EFFECTIVE-DIGEST-A02",
        }
    ]


def test_product_installs_u01qb16c_on_existing_matcher_assembler() -> None:
    assert product_package is not None
    assert u16c.installed() is True
    assert matching.assemble_form_component is u16c.assemble_form_component
    assert u16c.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16c.A1FS_CONTENT_POLICY_EXEMPTION


def test_unbound_reading_form_migrates_only_changed_activity_and_writes_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _database(tmp_path)
    monkeypatch.setattr(
        u16c,
        "_migration_plan",
        lambda database, *, form_ordinal, rows, prior: _one_change(rows),
    )

    result = u16c.migrate_unbound_reading_form(
        database,
        learner_id="LEARNER",
        session_id="S2",
        form_ordinal=2,
        applied_at="2026-08-06T12:00:00Z",
    )
    assert result["action"] == "MIGRATED_UNBOUND_READING_FORM"
    assert result["changed"] == 1
    assert result["completed_or_bound_activities_modified"] is False
    assert result["learner_attempts_modified"] is False
    assert result["questionbank_modified"] is False

    with sqlite3.connect(database) as connection:
        migrated = connection.execute(
            "SELECT task_angle,pattern_family_ids_json,activity_digest FROM u01qb13_blueprint_activities WHERE activity_id=?",
            ("F02-S01-A02",),
        ).fetchone()
        untouched = connection.execute(
            "SELECT task_angle,activity_digest FROM u01qb13_blueprint_activities WHERE activity_id=?",
            ("F02-S01-A01",),
        ).fetchone()
        lineage = connection.execute(
            f"SELECT original_task_angle,effective_task_angle,original_activity_digest,effective_activity_digest FROM {u16c.MIGRATION_TABLE} WHERE activity_id=?",
            ("F02-S01-A02",),
        ).fetchone()
    assert migrated == (
        "KNOWN_REFERENCE_CONTEXT",
        '["U01-PF05-KNOWN-REFERENCE-CONTEXT"]',
        "U16C-EFFECTIVE-DIGEST-A02",
    )
    assert untouched == ("ARTICLE_CONTROL", "DIGEST-1-1")
    assert lineage == (
        "FIRST_MENTION_CONTEXT",
        "KNOWN_REFERENCE_CONTEXT",
        "DIGEST-1-2",
        "U16C-EFFECTIVE-DIGEST-A02",
    )


def test_any_prior_binding_freezes_entire_form_and_preserves_blueprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO u01qb13_session_bindings VALUES(?,?)",
            ("OLD-SESSION", "F02-S01-A01"),
        )
        connection.commit()
    monkeypatch.setattr(
        u16c,
        "_migration_plan",
        lambda *args, **kwargs: pytest.fail("planner must not run for frozen form"),
    )
    result = u16c.migrate_unbound_reading_form(
        database,
        learner_id="LEARNER",
        session_id="S2",
        form_ordinal=2,
    )
    assert result == {
        "status": u16c.PASS_STATUS,
        "action": "SKIP_FORM_FROZEN_BY_PRIOR_BINDING",
        "changed": 0,
    }
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT task_angle,activity_digest FROM u01qb13_blueprint_activities WHERE activity_id='F02-S01-A02'"
        ).fetchone()
    assert row == ("FIRST_MENTION_CONTEXT", "DIGEST-1-2")


def test_migration_is_idempotent_and_does_not_rewrite_second_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _database(tmp_path)
    monkeypatch.setattr(
        u16c,
        "_migration_plan",
        lambda database, *, form_ordinal, rows, prior: _one_change(rows),
    )
    first = u16c.migrate_unbound_reading_form(
        database,
        learner_id="LEARNER",
        session_id="S2",
        form_ordinal=2,
    )
    second = u16c.migrate_unbound_reading_form(
        database,
        learner_id="LEARNER",
        session_id="S2",
        form_ordinal=2,
    )
    assert first["changed"] == 1
    assert second == {
        "status": u16c.PASS_STATUS,
        "action": "REUSE_EXISTING_MIGRATION",
        "changed": 0,
    }


def test_nonreading_session_never_migrates_blueprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _database(tmp_path, skill="WRITING")
    monkeypatch.setattr(
        u16c,
        "_migration_plan",
        lambda *args, **kwargs: pytest.fail("planner must not run for non-reading session"),
    )
    result = u16c.migrate_unbound_reading_form(
        database,
        learner_id="LEARNER",
        session_id="S2",
        form_ordinal=2,
    )
    assert result == {
        "status": u16c.PASS_STATUS,
        "action": "SKIP_NON_READING_OR_UNKNOWN_SESSION",
        "changed": 0,
    }


def test_u16c_early_return_explicitly_closes_sqlite_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "schema_not_ready.sqlite3"
    original_connect = sqlite3.connect
    setup = original_connect(database)
    setup.execute("CREATE TABLE placeholder(id INTEGER)")
    setup.commit()
    setup.close()

    closed = []

    class TrackingConnection(sqlite3.Connection):
        def close(self):
            closed.append(True)
            return super().close()

    def tracking_connect(*args, **kwargs):
        kwargs["factory"] = TrackingConnection
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(u16c.sqlite3, "connect", tracking_connect)
    result = u16c.migrate_unbound_reading_form(
        database,
        learner_id="LEARNER",
        session_id="S2",
        form_ordinal=1,
    )
    assert result["action"] == "SKIP_SCHEMA_NOT_READY"
    assert closed == [True]


def test_runtime_allocation_catalog_explicitly_closes_sqlite_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "runtime_catalog.sqlite3"
    original_connect = sqlite3.connect
    setup = original_connect(database)
    setup.executescript(
        """
        CREATE TABLE u01qb12_metadata(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE u01qb02_item_catalog(
          item_id TEXT PRIMARY KEY,
          skill TEXT NOT NULL,
          pattern_family_id TEXT NOT NULL,
          private_item_json TEXT NOT NULL
        );
        """
    )
    setup.executemany(
        "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?)",
        [
            (f"ITEM-{index:03d}", "READING", "PF", '{"lexical_slots":{"noun":"tree"}}')
            for index in range(474)
        ],
    )
    setup.commit()
    setup.close()

    closed = []

    class TrackingConnection(sqlite3.Connection):
        def close(self):
            closed.append(True)
            return super().close()

    def tracking_connect(*args, **kwargs):
        kwargs["factory"] = TrackingConnection
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(runtime_allocation.sqlite3, "connect", tracking_connect)
    catalog = runtime_allocation._catalog(database)
    assert len(catalog["READING"]) == 474
    assert closed == [True]
