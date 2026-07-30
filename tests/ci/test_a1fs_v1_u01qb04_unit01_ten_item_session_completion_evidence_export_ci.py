# The CI canary proves one complete clean-session write path, not synthetic count-only coverage.
import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb04_unit01_ten_item_session_completion_evidence_export as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb04_unit01_ten_item_session_completion_evidence_export as validator,
)


def test_u01qb04_ci_gate_ten_item_completion_and_evidence_export(tmp_path: Path):
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
        for index, (skill, lesson_id) in enumerate(qb02.UNIT01_LESSONS.items(), 1):
            connection.execute(
                "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (lesson_id, f"LESSON:U01:{index}", skill, "A1", json.dumps(["CHK"]), "[]", 1),
            )
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
            (
                "learner-ci",
                "Learner",
                "zh-TW",
                "Asia/Taipei",
                "ACTIVE",
                1,
                "2026-07-30T00:00:00Z",
                "2026-07-30T00:00:00Z",
            ),
        )
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    initialized = runtime.initialize()
    m3.LearnerStateStore(database).start_session(
        learner_id="learner-ci",
        lesson_id=qb02.UNIT01_LESSONS["READING"],
        session_id="session-ci",
        at="2026-07-30T00:01:00Z",
    )
    plan = runtime.assemble_session(
        learner_id="learner-ci",
        session_id="session-ci",
        selected_at="2026-07-30T00:02:00Z",
    )
    responses = {}
    with sqlite3.connect(database) as connection:
        for item in plan["items"]:
            contract = json.loads(
                connection.execute(
                    "SELECT contract_json FROM response_contracts WHERE asset_key=?",
                    (item["asset_key"],),
                ).fetchone()[0]
            )
            responses[item["item_id"]] = (
                contract["accepted_sequence"]
                if contract["response_type"] == "string_array"
                else contract["accepted_texts"][0]
            )
    responses[plan["items"][0]["item_id"]] = "definitely wrong"
    output = tmp_path / "completion"
    readback = builder.complete_session(
        database=database,
        learner_id="learner-ci",
        session_id="session-ci",
        responses=responses,
        output_root=output,
        completed_at="2026-07-30T00:30:00Z",
    )
    report = validator.validate(database=database, output_root=output)

    assert initialized["registered_item_count"] == 288
    assert readback["validation_status"] == builder.PASS_STATUS
    assert readback["session"]["session_state"] == "COMPLETED"
    assert readback["session"]["session_version"] == 22
    assert readback["outcome_distribution"] == {"AUTO_FAIL": 1, "AUTO_PASS": 9}
    assert readback["counts"]["completed_item_count"] == 10
    assert readback["counts"]["m6_registry_entry_count"] == 10
    assert readback["counts"]["m12_attempt_count"] == 10
    assert report["status"] == builder.PASS_STATUS
    assert report["error_count"] == 0, report["errors"]
    assert report["session_plan_count"] == 1
    assert report["selected_item_count"] == 10
    assert report["exposure_count"] == 10
    assert report["attempt_count"] == 10
    assert report["scoring_result_count"] == 10
    assert report["evidence_export_count"] == 1
    assert report["m6_registry_entry_count"] == 10
    assert report["m12_attempt_count"] == 10
    assert report["claim_boundaries"] == {
        "parallel_planner_created": False,
        "parallel_learner_database_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "parallel_evidence_schema_created": False,
        "unit02_to_unit24_modified": False,
        "speaking_capture_enabled": False,
        "mastery_written": False,
        "retention_confirmed": False,
        "a2_unlocked": False,
    }
