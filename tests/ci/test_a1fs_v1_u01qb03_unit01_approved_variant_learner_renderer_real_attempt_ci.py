import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb03_unit01_approved_variant_learner_renderer_real_attempt as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb03_unit01_approved_variant_learner_renderer_real_attempt as validator,
)


def test_u01qb03_ci_gate_real_attempt_acceptance(tmp_path: Path):
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
    session = m3.LearnerStateStore(database).start_session(
        learner_id="learner-ci",
        lesson_id=qb02.UNIT01_LESSONS["READING"],
        session_id="session-ci",
        at="2026-07-30T00:01:00Z",
    )
    output = tmp_path / "workbench"
    manifest = builder.build_workbench(
        database=database,
        learner_id="learner-ci",
        session_id="session-ci",
        output_root=output,
    )
    bundle = json.loads((output / "session.private.json").read_text(encoding="utf-8"))
    item = bundle["items"][0]
    with sqlite3.connect(database) as connection:
        contract = json.loads(
            connection.execute(
                "SELECT contract_json FROM response_contracts WHERE asset_key=?", (item["asset_key"],)
            ).fetchone()[0]
        )
    response = (
        contract["accepted_sequence"]
        if contract["response_type"] == "string_array"
        else contract["accepted_texts"][0]
    )
    attempt = builder.LearnerAttemptController(
        database, learner_id="learner-ci", session_id="session-ci"
    ).submit(
        item_id=item["item_id"],
        response=response,
        expected_session_version=session["session_version"],
    )
    report = validator.validate(database=database, output_root=output)

    assert initialized["registered_item_count"] == 288
    assert manifest["validation_status"] == builder.PASS_STATUS
    assert manifest["item_count"] == 10
    assert attempt["outcome"] == "AUTO_PASS"
    assert attempt["m3_exposure_reused"] is True
    assert attempt["m6_response_scoring_reused"] is True
    assert report["status"] == builder.PASS_STATUS
    assert report["error_count"] == 0
    assert report["session_plan_count"] == 1
    assert report["session_item_count"] == 10
    assert report["item_exposure_count"] == 1
    assert report["attempt_count"] == 1
    assert report["scoring_result_count"] == 1
    assert report["auto_pass_count"] == 1
    assert report["claim_boundaries"] == {
        "existing_m5_renderer_reused": True,
        "existing_m3_exposure_reused": True,
        "existing_m6_response_scoring_reused": True,
        "parallel_renderer_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "speaking_capture_enabled": False,
        "mastery_claimed": False,
        "a2_unlocked": False,
    }
