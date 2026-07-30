from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as validator,
)


def fixture_database(tmp_path: Path) -> Path:
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
                (
                    lesson_id,
                    f"LESSON:U01:{index}",
                    skill,
                    "A1",
                    json.dumps(["CHK" if skill == "READING" else "PRD"]),
                    "[]",
                    1,
                ),
            )
        connection.execute(
            "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
            ("A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:READING", "LESSON:OTHER:1", "READING", "A1", "[\"CHK\"]", "[]", 1),
        )
        for learner in ("learner-1", "learner-2", "learner-3", "learner-4"):
            connection.execute(
                "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
                (learner, learner, "zh-TW", "Asia/Taipei", "ACTIVE", 1, "2026-07-30T00:00:00Z", "2026-07-30T00:00:00Z"),
            )
    return database


def start_session(database: Path, *, learner_id: str, skill: str, session_id: str) -> dict:
    return m3.LearnerStateStore(database).start_session(
        learner_id=learner_id,
        lesson_id=builder.UNIT01_LESSONS[skill],
        session_id=session_id,
        at="2026-07-30T00:01:00Z",
    )


def test_u01qb02_registers_all_approved_items_into_existing_m3_m6_tables(tmp_path: Path):
    database = fixture_database(tmp_path)
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    result = runtime.initialize()
    assert result["validation_status"] == builder.PASS_STATUS
    assert result["registered_item_count"] == 288
    assert result["response_contract_count"] == 288
    assert result["parallel_runtime_created"] is False
    assert result["a2_unlocked"] is False
    report = validator.validate(database)
    assert report["error_count"] == 0, report["errors"]
    assert report["registered_item_count"] == 288
    assert report["response_contract_count"] == 288
    assert report["skill_distribution"] == {"READING": 166, "SPEAKING": 25, "WRITING": 97}


def test_u01qb02_assembles_ten_learner_safe_items_idempotently(tmp_path: Path):
    database = fixture_database(tmp_path)
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    runtime.initialize()
    start_session(database, learner_id="learner-1", skill="READING", session_id="session-r1")
    plan = runtime.assemble_session(
        learner_id="learner-1",
        session_id="session-r1",
        selected_at="2026-07-30T00:02:00Z",
    )
    assert plan["item_count"] == 10
    assert len({row["item_id"] for row in plan["items"]}) == 10
    assert all(row["skill"] == "READING" for row in plan["items"])
    assert plan["answer_keys_exposed"] is False
    for row in plan["items"]:
        assert "correct_answer" not in row
        assert "accepted_answers" not in row
        assert "response_contract" not in row
    replay = runtime.assemble_session(learner_id="learner-1", session_id="session-r1")
    assert replay["plan_digest"] == plan["plan_digest"]
    assert replay["items"] == plan["items"]


def test_u01qb02_reuses_m3_exposure_m6_scoring_and_selects_remediation(tmp_path: Path):
    database = fixture_database(tmp_path)
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    runtime.initialize()
    session = start_session(database, learner_id="learner-1", skill="READING", session_id="session-r1")
    plan = runtime.assemble_session(learner_id="learner-1", session_id="session-r1")
    item = plan["items"][0]
    exposure = runtime.record_item_exposure(
        session_id="session-r1",
        item_id=item["item_id"],
        expected_session_version=session["session_version"],
        exposure_id="exposure-r1-1",
        at="2026-07-30T00:03:00Z",
    )
    assert exposure["m3_exposure_recorded"] is True
    assert exposure["session_version"] == 2
    attempt = runtime.capture_response(
        learner_id="learner-1",
        session_id="session-r1",
        item_id=item["item_id"],
        response="definitely wrong",
        expected_session_version=2,
        attempt_id="attempt-r1-1",
        submitted_at="2026-07-30T00:04:00Z",
    )
    assert attempt["outcome"] == "AUTO_FAIL"
    assert attempt["m6_response_capture_reused"] is True
    assert attempt["parallel_scoring_created"] is False
    m3.LearnerStateStore(database).end_session(
        session_id="session-r1",
        outcome="COMPLETED",
        expected_session_version=3,
        at="2026-07-30T00:05:00Z",
    )
    start_session(database, learner_id="learner-1", skill="READING", session_id="session-r2")
    next_plan = runtime.assemble_session(learner_id="learner-1", session_id="session-r2")
    selected = {row["item_id"]: row["selection_reason"] for row in next_plan["items"]}
    assert selected[item["item_id"]] == "REMEDIATION"
    report = validator.validate(database)
    assert report["error_count"] == 0, report["errors"]
    assert report["attempt_count"] == 1
    assert report["item_exposure_count"] == 1


def test_u01qb02_excludes_last_ten_non_failed_exposures(tmp_path: Path):
    database = fixture_database(tmp_path)
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    runtime.initialize()
    session = start_session(database, learner_id="learner-2", skill="WRITING", session_id="session-w1")
    first = runtime.assemble_session(learner_id="learner-2", session_id="session-w1")
    version = session["session_version"]
    first_ids = []
    for index, item in enumerate(first["items"], 1):
        first_ids.append(item["item_id"])
        exposed = runtime.record_item_exposure(
            session_id="session-w1",
            item_id=item["item_id"],
            expected_session_version=version,
            exposure_id=f"exposure-w1-{index}",
            at=f"2026-07-30T00:{10 + index:02d}:00Z",
        )
        version = exposed["session_version"]
    m3.LearnerStateStore(database).end_session(
        session_id="session-w1",
        outcome="COMPLETED",
        expected_session_version=version,
        at="2026-07-30T00:30:00Z",
    )
    start_session(database, learner_id="learner-2", skill="WRITING", session_id="session-w2")
    second = runtime.assemble_session(learner_id="learner-2", session_id="session-w2")
    assert not set(first_ids).intersection(row["item_id"] for row in second["items"])


def test_u01qb02_speaking_remains_practice_only_without_capture(tmp_path: Path):
    database = fixture_database(tmp_path)
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    runtime.initialize()
    session = start_session(database, learner_id="learner-3", skill="SPEAKING", session_id="session-s1")
    plan = runtime.assemble_session(learner_id="learner-3", session_id="session-s1")
    item = plan["items"][0]
    assert item["capture_enabled"] is False
    exposure = runtime.record_item_exposure(
        session_id="session-s1",
        item_id=item["item_id"],
        expected_session_version=session["session_version"],
        exposure_id="exposure-s1-1",
    )
    with pytest.raises(builder.SessionRuntimeError, match="item_response_capture_disabled"):
        runtime.capture_response(
            learner_id="learner-3",
            session_id="session-s1",
            item_id=item["item_id"],
            response="a book",
            expected_session_version=exposure["session_version"],
        )


def test_u01qb02_rejects_non_unit01_session(tmp_path: Path):
    database = fixture_database(tmp_path)
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    runtime.initialize()
    session = m3.LearnerStateStore(database).start_session(
        learner_id="learner-4",
        lesson_id="A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:READING",
        session_id="session-other",
    )
    assert session["session_state"] == "ACTIVE"
    with pytest.raises(builder.SessionRuntimeError, match="session_not_unit01_supported_lesson"):
        runtime.assemble_session(learner_id="learner-4", session_id="session-other")


def test_u01qb02_validator_detects_exposure_chain_tampering(tmp_path: Path):
    database = fixture_database(tmp_path)
    runtime = builder.Unit01ApprovedVariantSessionRuntime(database)
    runtime.initialize()
    session = start_session(database, learner_id="learner-1", skill="READING", session_id="session-r1")
    plan = runtime.assemble_session(learner_id="learner-1", session_id="session-r1")
    runtime.record_item_exposure(
        session_id="session-r1",
        item_id=plan["items"][0]["item_id"],
        expected_session_version=session["session_version"],
        exposure_id="exposure-tamper",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE u01qb02_item_exposures SET exposure_hash=? WHERE exposure_id=?",
            ("f" * 64, "exposure-tamper"),
        )
    report = validator.validate(database)
    assert report["status"] == "FAIL"
    assert any(error.startswith("exposure_hash_invalid:") for error in report["errors"])
