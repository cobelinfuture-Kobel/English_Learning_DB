from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13


def _visible(stimulus: str, *, answer: str = "an") -> str:
    return json.dumps(
        {
            "question_type": "multiple_choice",
            "prompt": "Choose the best article.",
            "stimulus": stimulus,
            "options": ["a", "an", "the"],
            "correct_answer": answer,
        },
        separators=(",", ":"),
    )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "learner.sqlite3"
    lesson_id = qb02.UNIT01_LESSONS["READING"]
    with sqlite3.connect(path) as connection:
        connection.executescript(
            f"""
            CREATE TABLE learner_profiles(
              learner_id TEXT PRIMARY KEY,
              display_label TEXT NOT NULL,
              locale TEXT NOT NULL,
              timezone_name TEXT NOT NULL,
              profile_state TEXT NOT NULL,
              profile_version INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE lesson_catalog(
              lesson_id TEXT PRIMARY KEY,
              lesson_node_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              level TEXT NOT NULL,
              roles_json TEXT NOT NULL,
              requirement_node_ids_json TEXT NOT NULL,
              payload_access_allowed INTEGER NOT NULL
            );
            CREATE TABLE lesson_assets(
              asset_key TEXT PRIMARY KEY,
              asset_id TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content_digest TEXT NOT NULL
            );
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
              asset_key TEXT NOT NULL UNIQUE,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              pattern_family_id TEXT NOT NULL,
              unit_pattern_id TEXT NOT NULL,
              support_level TEXT NOT NULL,
              assessment_eligible INTEGER NOT NULL,
              transfer_eligible INTEGER NOT NULL,
              capture_enabled INTEGER NOT NULL,
              private_item_json TEXT NOT NULL,
              item_digest TEXT NOT NULL UNIQUE
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
              exposure_id TEXT NOT NULL UNIQUE,
              learner_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              item_id TEXT NOT NULL,
              selection_reason TEXT NOT NULL,
              exposure_at TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              exposure_hash TEXT NOT NULL UNIQUE,
              UNIQUE(session_id,item_id)
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
              diagnosis_digest TEXT NOT NULL UNIQUE
            );
            CREATE TABLE reassessment_queue(
              reassessment_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              node_id TEXT NOT NULL,
              source_remediation_id TEXT NOT NULL,
              lesson_ids_json TEXT NOT NULL,
              asset_keys_json TEXT NOT NULL,
              queue_state TEXT NOT NULL,
              created_at TEXT NOT NULL,
              queue_digest TEXT NOT NULL UNIQUE
            );
            """
        )
        connection.executescript(e2e.impl.u16d.LINK_SQL)
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
            ("LEARNER", "Learner", "zh-TW", "Asia/Taipei", "ACTIVE", 1, "2026-08-06T00:00:00Z", "2026-08-06T00:00:00Z"),
        )
        connection.execute(
            "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
            (lesson_id, "LESSON:READING:U01", "READING", "A1", "[]", "[]", 1),
        )
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?,?)",
            ("RS-1", "LEARNER", lesson_id, "READING", "A1", "ACTIVE", 1, "2026-08-06T00:00:00Z", None),
        )
        connection.execute(
            "INSERT INTO u01qb02_metadata VALUES(?,?)",
            ("source_bank_artifact_sha256", "a" * 64),
        )
        items = [
            ("ITEM-FAIL", "ASSET-FAIL", _visible("There is ___ apple in the bag.")),
            ("ITEM-NEW", "ASSET-NEW", _visible("Mia can see ___ orange at the picnic.")),
        ]
        items.extend(
            (f"ITEM-FILL-{index}", f"ASSET-FILL-{index}", _visible(f"There is ___ apple near place {index}."))
            for index in range(1, 10)
        )
        for index, (item_id, asset_key, private_json) in enumerate(items, 1):
            connection.execute(
                "INSERT INTO lesson_assets VALUES(?,?,?,?,?)",
                (asset_key, item_id, lesson_id, "CHK", f"DIGEST-ASSET-{index}"),
            )
            connection.execute(
                "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    asset_key,
                    lesson_id,
                    "READING",
                    "U01-PF04-FIRST-MENTION-CONTEXT",
                    "PATTERN-U01",
                    "GUIDED",
                    1,
                    0,
                    1,
                    private_json,
                    f"DIGEST-ITEM-{index}",
                ),
            )
        connection.execute(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "ACTIVITY-1",
                "FORM-01",
                1,
                "SCENE-1",
                "FOOD_SOCIAL",
                "picnic",
                "READING",
                "ARTICLE_CONTROL",
                "GUIDED",
                1,
                0,
                '["U01-PF04-FIRST-MENTION-CONTEXT"]',
                '["apple","orange"]',
                "{}",
                "DIGEST-ACTIVITY-1",
            ),
        )
        connection.execute(
            "INSERT INTO error_diagnoses VALUES(?,?,?,?,?,?,?,?,?)",
            ("DIAG-1", "LEARNER", "ATTEMPT-FAIL", '["NODE-U01"]', '["u01_a_an_sound_choice_error"]', "MEDIUM", "OPEN", "2026-08-06T00:00:00Z", "DIGEST-DIAG-1"),
        )
        connection.execute(
            "INSERT INTO reassessment_queue VALUES(?,?,?,?,?,?,?,?,?)",
            ("REASSESS-1", "LEARNER", "NODE-U01", "REMED-1", "[]", '["ASSET-FAIL"]', "PENDING", "2026-08-06T00:00:00Z", "DIGEST-REASSESS-1"),
        )
        failed_signature = e2e.impl.u16.learner_visible_signature(
            {
                "skill": "READING",
                "private_item_json": _visible("There is ___ apple in the bag."),
            }
        )
        new_signature = e2e.impl.u16.learner_visible_signature(
            {
                "skill": "READING",
                "private_item_json": _visible("Mia can see ___ orange at the picnic."),
            }
        )
        core = {
            "diagnosis_id": "DIAG-1",
            "learner_id": "LEARNER",
            "attempt_id": "ATTEMPT-FAIL",
            "item_id": "ITEM-FAIL",
            "activity_id": "ACTIVITY-1",
            "form_ordinal": 1,
            "skill": "READING",
            "task_angle": "ARTICLE_CONTROL",
            "capability_class": "FIRST_MENTION_SELECTION",
            "targeted_error_tag": "u01_a_an_sound_choice_error",
            "targeted_remediation_strategy": "RETEACH_A_AN_SOUND_CHOICE_WITH_MINIMAL_PAIRS",
            "remediation_ids": ["REMED-1"],
            "reassessment_ids": ["REASSESS-1"],
            "failed_learner_visible_signature": failed_signature,
            "different_item_id": "ITEM-NEW",
            "different_asset_key": "ASSET-NEW",
            "different_learner_visible_signature": new_signature,
            "candidate_state": "READY",
        }
        connection.execute(
            f"INSERT INTO {e2e.impl.u16d.LINK_TABLE} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                "ITEM-NEW",
                "ASSET-NEW",
                new_signature,
                "READY",
                e2e.impl.m7.digest(core),
            ),
        )
        connection.commit()
    return path


def test_runtime_installs_u01qb16e_over_existing_e2e_authority() -> None:
    assert u16e.installed() is True
    assert e2e.impl.u01qb15_completion_readiness is u16e._completion_readiness_attempt_once
    assert e2e.impl.U01QB15ProductApplication.submit_u01qb15_response is u16e._submit_form_response_attempt_once
    assert e2e.impl.U01QB15ProductApplication.start_u01qb15_form is u16e._start_form_after_reassessment_gate
    assert e2e.MODULE == "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
    assert u16e.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16e.A1FS_CONTENT_POLICY_EXEMPTION


def test_form_failure_is_terminal_evidence_not_same_item_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        u16e,
        "_ORIGINAL_READINESS",
        lambda _database, _session: {
            "skill": "READING",
            "assets": [
                {"completion_state": "PASSED"},
                {"completion_state": "RETRY_REQUIRED"},
            ],
            "not_attempted_count": 0,
            "pending_human_review_count": 0,
        },
    )
    gate = u16e._completion_readiness_attempt_once(Path("unused"), "SESSION")
    assert gate["completion_allowed"] is True
    assert gate["same_item_retry_allowed"] is False
    assert gate["different_item_reassessment_required_count"] == 1
    assert gate["gate_mode"] == "U01QB16E_ATTEMPT_ONCE_THEN_DIAGNOSE_REASSESS"


def test_materializes_only_different_item_into_visible_reassessment_binding(tmp_path: Path) -> None:
    database = _database(tmp_path)
    pending = u16e.pending_reassessments(database, learner_id="LEARNER")
    assert len(pending) == 1
    assert pending[0]["diagnosis_id"] == "DIAG-1"
    assert pending[0]["targeted_error_tag"] == "u01_a_an_sound_choice_error"

    result = u16e.materialize_reassessment_session(
        database,
        learner_id="LEARNER",
        diagnosis_id="DIAG-1",
        session_id="RS-1",
        selected_at="2026-08-06T01:00:00Z",
    )
    assert result["validation_status"] == u16e.PASS_STATUS
    assert result["failed_item_id"] == "ITEM-FAIL"
    assert result["item"]["item_id"] == "ITEM-NEW"
    assert result["failed_item_replayed"] is False
    assert result["learner_visible_signature_replayed"] is False
    assert result["support_fillers_exposed_to_learner"] is False

    with sqlite3.connect(database) as connection:
        plan = connection.execute(
            "SELECT item_count FROM u01qb02_session_plans WHERE session_id='RS-1'"
        ).fetchone()
        selected = connection.execute(
            "SELECT item_id,selection_reason FROM u01qb02_session_items WHERE session_id='RS-1' ORDER BY item_position"
        ).fetchall()
        binding = connection.execute(
            "SELECT item_id,item_position,binding_quality,is_assessment_evidence FROM u01qb13_session_bindings WHERE session_id='RS-1'"
        ).fetchone()
    assert plan == (10,)
    assert len(selected) == 10
    assert selected[0] == ("ITEM-NEW", "REMEDIATION")
    assert "ITEM-FAIL" not in {row[0] for row in selected}
    assert binding == ("ITEM-NEW", 1, "U01QB16E_DIFFERENT_ITEM_REASSESSMENT", 1)


def test_recent_candidate_and_reused_visible_signature_fail_closed(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO u01qb02_item_exposures VALUES(NULL,?,?,?,?,?,?,?,?)",
            ("EXP-1", "LEARNER", "OLD-SESSION", "ITEM-NEW", "REMEDIATION", "2026-08-06T00:30:00Z", "0" * 64, "1" * 64),
        )
        connection.commit()
    with pytest.raises(u16e.DifferentItemReassessmentError, match="RECENTLY_EXPOSED"):
        u16e.materialize_reassessment_session(
            database,
            learner_id="LEARNER",
            diagnosis_id="DIAG-1",
            session_id="RS-1",
        )

    database = _database(tmp_path / "second")
    with sqlite3.connect(database) as connection:
        connection.executescript(u16e.SESSION_SQL)
        signature = connection.execute(
            f"SELECT different_learner_visible_signature FROM {e2e.impl.u16d.LINK_TABLE} WHERE diagnosis_id='DIAG-1'"
        ).fetchone()[0]
        connection.execute(
            f"""INSERT INTO {u16e.SESSION_TABLE}
            VALUES(?,?,?,?,?,?,?,?,'COMPLETED','AUTO_FAIL','OLD-ATTEMPT',?,?,?)""",
            (
                "OLD-RS",
                "DIAG-1",
                "LEARNER",
                '["REASSESS-1"]',
                "ITEM-FAIL",
                "OLD-ITEM",
                "ACTIVITY-1",
                signature,
                "2026-08-05T00:00:00Z",
                "2026-08-05T00:01:00Z",
                "OLD-DIGEST",
            ),
        )
        connection.commit()
    with pytest.raises(u16e.DifferentItemReassessmentError, match="SIGNATURE_ALREADY_USED"):
        u16e.materialize_reassessment_session(
            database,
            learner_id="LEARNER",
            diagnosis_id="DIAG-1",
            session_id="RS-1",
        )


def test_learner_ui_contains_adaptive_loop_routes_and_no_direct_retry() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "product/a1fs_v1_2_1/runtime/secure_static/u01qb15.js").read_text(encoding="utf-8")
    assert "/api/u01qb16e/reassessment/pending" in script
    assert "/api/u01qb16e/reassessment/start" in script
    assert "/api/u01qb16e/reassessment/response" in script
    assert "完成補救，開始換題重評" in script
    assert "原錯題不重播" in script
    assert "same_item_retry" not in script.casefold()


def test_next_step_is_learner_facing_adaptive_loop_acceptance() -> None:
    assert u16e.NEXT_SHORT_STEP == (
        "A1FS-V1-U01QB16F_Unit01AdaptiveLoopLearnerFacingAcceptanceAndPedagogicalQualityCloseout"
    )
