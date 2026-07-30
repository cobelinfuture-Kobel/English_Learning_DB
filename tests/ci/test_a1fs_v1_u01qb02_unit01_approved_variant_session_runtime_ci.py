import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as validator,
)


def test_u01qb02_ci_gate_existing_runtime_integration(tmp_path: Path):
    database = tmp_path / "learner_progress.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.executemany(
            "INSERT INTO metadata(key,value) VALUES(?,?)",
            {
                "task_id": m3.TASK_ID,
                "schema_version": m3.SCHEMA_VERSION,
                "validation_status": m3.STATUS,
                "consumer_sha256": "a" * 64,
                "mastery_write_enabled": "false",
                "a2_session_enabled": "false",
            }.items(),
        )
        for index, (skill, lesson_id) in enumerate(builder.UNIT01_LESSONS.items(), 1):
            connection.execute(
                "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (lesson_id, f"LESSON:U01:{index}", skill, "A1", json.dumps(["CHK"]), "[]", 1),
            )
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
            ("learner-ci", "Learner", "zh-TW", "Asia/Taipei", "ACTIVE", 1, "2026-07-30T00:00:00Z", "2026-07-30T00:00:00Z"),
        )
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    initialized = runtime.initialize()
    session = m3.LearnerStateStore(database).start_session(
        learner_id="learner-ci",
        lesson_id=builder.UNIT01_LESSONS["READING"],
        session_id="session-ci",
    )
    plan = runtime.assemble_session(learner_id="learner-ci", session_id="session-ci")
    exposed = runtime.record_item_exposure(
        session_id="session-ci",
        item_id=plan["items"][0]["item_id"],
        expected_session_version=session["session_version"],
        exposure_id="exposure-ci",
    )
    report = validator.validate(database)

    assert initialized["registered_item_count"] == 288
    assert initialized["response_contract_count"] == 288
    assert plan["item_count"] == 10
    assert plan["answer_keys_exposed"] is False
    assert exposed["m3_exposure_recorded"] is True
    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["registered_item_count"] == 288
    assert report["response_contract_count"] == 288
    assert report["session_plan_count"] == 1
    assert report["item_exposure_count"] == 1
    assert report["attempt_count"] == 0
    assert report["claim_boundaries"] == {
        "parallel_planner_created": False,
        "parallel_learner_database_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "mastery_claimed": False,
    }
