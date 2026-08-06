from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as product_runtime
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e


def _private_item(stimulus: str) -> str:
    return json.dumps(
        {
            "question_type": "multiple_choice",
            "prompt": "Choose the best article.",
            "stimulus": stimulus,
            "options": ["a", "an", "the"],
            "correct_answer": "an",
        },
        separators=(",", ":"),
    )


def _catalog(item_id: str, asset_key: str, stimulus: str) -> tuple[object, ...]:
    return (
        item_id,
        asset_key,
        "UNIT01-READING",
        "READING",
        "U01-PF04-FIRST-MENTION-CONTEXT",
        "PATTERN-U01",
        "GUIDED",
        1,
        0,
        1,
        _private_item(stimulus),
        f"DIGEST-{item_id}",
    )


def _database(tmp_path: Path, *, candidate_recent: bool = False) -> Path:
    path = tmp_path / ("recent.sqlite3" if candidate_recent else "consumer.sqlite3")
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              level TEXT NOT NULL,
              session_state TEXT NOT NULL,
              session_version INTEGER NOT NULL,
              started_at TEXT NOT NULL,
              ended_at TEXT
            );
            CREATE TABLE u01qb02_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE u01qb02_item_catalog(
              item_id TEXT PRIMARY KEY,
              asset_key TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              pattern_family_id TEXT NOT NULL,
              unit_pattern_id TEXT NOT NULL,
              support_level TEXT NOT NULL,
              assessment_eligible INTEGER NOT NULL,
              transfer_eligible INTEGER NOT NULL,
              capture_enabled INTEGER NOT NULL,
              private_item_json TEXT NOT NULL,
              item_digest TEXT NOT NULL
            );
            CREATE TABLE u01qb02_session_plans(
              session_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              item_count INTEGER NOT NULL,
              selected_at TEXT NOT NULL,
              recent_exposure_window INTEGER NOT NULL,
              source_bank_sha256 TEXT NOT NULL,
              plan_digest TEXT NOT NULL UNIQUE
            );
            CREATE TABLE u01qb02_session_items(
              session_id TEXT NOT NULL,
              item_position INTEGER NOT NULL,
              item_id TEXT NOT NULL,
              selection_reason TEXT NOT NULL,
              PRIMARY KEY(session_id,item_position),
              UNIQUE(session_id,item_id)
            );
            CREATE TABLE u01qb02_item_exposures(
              exposure_seq INTEGER PRIMARY KEY AUTOINCREMENT,
              learner_id TEXT NOT NULL,
              item_id TEXT NOT NULL
            );
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
              is_assessment_evidence INTEGER NOT NULL,
              PRIMARY KEY(session_id,activity_id),
              UNIQUE(session_id,item_id),
              UNIQUE(session_id,item_position)
            );
            CREATE TABLE error_diagnoses(
              diagnosis_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              attempt_id TEXT NOT NULL,
              node_ids_json TEXT NOT NULL,
              error_tags_json TEXT NOT NULL,
              severity TEXT NOT NULL,
              diagnosis_state TEXT NOT NULL,
              created_at TEXT NOT NULL,
              diagnosis_digest TEXT NOT NULL
            );
            CREATE TABLE reassessment_queue(
              reassessment_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              queue_state TEXT NOT NULL
            );
            """
        )
        connection.executescript(u16e.u16d.LINK_SQL)
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "SESSION-REASSESS",
                "LEARNER",
                "UNIT01-READING",
                "READING",
                "A1",
                "ACTIVE",
                1,
                "2026-08-06T00:00:00Z",
                None,
            ),
        )
        connection.execute(
            "INSERT INTO u01qb02_metadata VALUES(?,?)",
            ("source_bank_artifact_sha256", "SOURCE-SHA"),
        )
        failed = _catalog("ITEM-FAIL", "ASSET-FAIL", "There is ___ apple in the bag.")
        candidate = _catalog(
            "ITEM-DIFFERENT",
            "ASSET-DIFFERENT",
            "Mia can see ___ orange at the picnic.",
        )
        connection.execute("INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", failed)
        connection.execute("INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", candidate)
        for index in range(1, 10):
            row = _catalog(
                f"ITEM-FILL-{index:02d}",
                f"ASSET-FILL-{index:02d}",
                f"There is ___ apple in scene {index}.",
            )
            connection.execute("INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", row)
        connection.execute(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "ACTIVITY-1",
                "FORM-01",
                1,
                "SCENE-1",
                "FOOD_SOCIAL",
                "PICNIC",
                "READING",
                "ARTICLE_CONTROL",
                "GUIDED",
                1,
                1,
                '["U01-PF04-FIRST-MENTION-CONTEXT"]',
                '["apple","orange"]',
                "{}",
                "ACTIVITY-DIGEST-1",
            ),
        )
        connection.execute(
            "INSERT INTO error_diagnoses VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "DIAG-1",
                "LEARNER",
                "ATTEMPT-FAIL",
                '["NODE-U01"]',
                '["u01_a_an_sound_choice_error"]',
                "MEDIUM",
                "OPEN",
                "2026-08-06T00:00:00Z",
                "DIAG-DIGEST-1",
            ),
        )
        connection.execute(
            "INSERT INTO reassessment_queue VALUES(?,?,?)",
            ("REASSESS-1", "LEARNER", "PENDING"),
        )
        failed_signature = u16.learner_visible_signature(
            {"item_id": failed[0], "skill": failed[3], "private_item_json": failed[10]}
        )
        candidate_signature = u16.learner_visible_signature(
            {"item_id": candidate[0], "skill": candidate[3], "private_item_json": candidate[10]}
        )
        connection.execute(
            f"INSERT INTO {u16e.u16d.LINK_TABLE} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "DIAG-1",
                "LEARNER",
                "ATTEMPT-FAIL",
                "ITEM-FAIL",
                "ACTIVITY-1",
                1,
                "READING",
                "ARTICLE_CONTROL",
                "FIRST_MENTION_SELECTION",
                "u01_a_an_sound_choice_error",
                "RETEACH_A_AN_SOUND_CHOICE_WITH_MINIMAL_PAIRS",
                '["REMED-1"]',
                '["REASSESS-1"]',
                failed_signature,
                "ITEM-DIFFERENT",
                "ASSET-DIFFERENT",
                candidate_signature,
                "READY",
                "LINK-DIGEST-1",
            ),
        )
        if candidate_recent:
            connection.execute(
                "INSERT INTO u01qb02_item_exposures(learner_id,item_id) VALUES(?,?)",
                ("LEARNER", "ITEM-DIFFERENT"),
            )
        connection.commit()
    return path


def test_runtime_installs_u01qb16e_on_existing_e2e_objects_and_manifest_stays_single_runtime() -> None:
    manifest = json.loads(
        (Path(product_runtime.__file__).with_name("product_manifest.json")).read_text(encoding="utf-8")
    )
    assert manifest["serve_module"] == "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest["unit01_questionbank_same_item_retry_allowed"] is False
    assert manifest["unit01_questionbank_reassessment_mode"] == "DIFFERENT_EXISTING_ITEM_AFTER_M7_DIAGNOSIS"
    assert u16e.installed() is True
    assert product_runtime.impl.U01QB15ProductApplication.start_u01qb15_form is u16e._start_form_after_reassessment_gate
    assert product_runtime.impl.U01QB15ProductApplication.submit_u01qb15_response is u16e._submit_form_response_attempt_once
    assert u16e.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16e.A1FS_CONTENT_POLICY_EXEMPTION


def test_distinct_existing_item_materializes_as_the_only_bound_reassessment_item(tmp_path: Path) -> None:
    database = _database(tmp_path)
    pending = u16e.pending_reassessments(database, learner_id="LEARNER")
    assert [row["diagnosis_id"] for row in pending] == ["DIAG-1"]
    result = u16e.materialize_reassessment_session(
        database,
        learner_id="LEARNER",
        diagnosis_id="DIAG-1",
        session_id="SESSION-REASSESS",
        selected_at="2026-08-06T00:05:00Z",
    )
    assert result["validation_status"] == u16e.PASS_STATUS
    assert result["failed_item_id"] == "ITEM-FAIL"
    assert result["item"]["item_id"] == "ITEM-DIFFERENT"
    assert result["item"]["reassessment"] is True
    assert result["failed_item_replayed"] is False
    assert result["learner_visible_signature_replayed"] is False
    assert result["support_fillers_exposed_to_learner"] is False
    assert result["questionbank_modified"] is False
    assert result["scoring_modified"] is False
    with sqlite3.connect(database) as connection:
        plan = connection.execute(
            "SELECT item_position,item_id,selection_reason FROM u01qb02_session_items WHERE session_id=? ORDER BY item_position",
            ("SESSION-REASSESS",),
        ).fetchall()
        bindings = connection.execute(
            "SELECT activity_id,item_id,item_position,binding_quality,is_assessment_evidence FROM u01qb13_session_bindings WHERE session_id=?",
            ("SESSION-REASSESS",),
        ).fetchall()
    assert len(plan) == 10
    assert plan[0] == (1, "ITEM-DIFFERENT", "REMEDIATION")
    assert all(row[1] != "ITEM-FAIL" for row in plan)
    assert bindings == [
        ("ACTIVITY-1", "ITEM-DIFFERENT", 1, "U01QB16E_DIFFERENT_ITEM_REASSESSMENT", 1)
    ]


def test_recent_reassessment_candidate_fails_closed(tmp_path: Path) -> None:
    database = _database(tmp_path, candidate_recent=True)
    with pytest.raises(
        u16e.DifferentItemReassessmentError,
        match="REASSESSMENT_CANDIDATE_RECENTLY_EXPOSED",
    ):
        u16e.materialize_reassessment_session(
            database,
            learner_id="LEARNER",
            diagnosis_id="DIAG-1",
            session_id="SESSION-REASSESS",
        )


def test_attempt_once_gate_and_same_item_retry_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        u16e,
        "_ORIGINAL_READINESS",
        lambda _database, _session: {
            "skill": "READING",
            "assets": [
                {"completion_state": "PASSED"},
                {"completion_state": "RETRY_REQUIRED"},
            ],
        },
    )
    gate = u16e._completion_readiness_attempt_once(Path("unused"), "SESSION")
    assert gate["completion_allowed"] is True
    assert gate["same_item_retry_allowed"] is False
    assert gate["different_item_reassessment_required_count"] == 1

    database = tmp_path / "attempt.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE response_attempts(attempt_id TEXT PRIMARY KEY,session_id TEXT,asset_key TEXT);
            CREATE TABLE u01qb02_item_catalog(item_id TEXT PRIMARY KEY,asset_key TEXT);
            INSERT INTO u01qb02_item_catalog VALUES('ITEM-1','ASSET-1');
            INSERT INTO response_attempts VALUES('ATT-1','SESSION-1','ASSET-1');
            """
        )
        connection.commit()
    monkeypatch.setattr(
        u16e,
        "_ORIGINAL_SUBMIT_FORM_RESPONSE",
        lambda _self, _payload: {"unexpected": True},
    )
    with pytest.raises(
        u16e.DifferentItemReassessmentError,
        match="UNIT01_SAME_ITEM_RETRY_FORBIDDEN",
    ):
        u16e._submit_form_response_attempt_once(
            SimpleNamespace(database_path=database),
            {"session_id": "SESSION-1", "item_id": "ITEM-1", "response": "an"},
        )
