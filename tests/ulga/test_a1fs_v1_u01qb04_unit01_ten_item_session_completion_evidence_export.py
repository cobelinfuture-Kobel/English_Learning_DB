from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

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
        for index, (skill, lesson_id) in enumerate(qb02.UNIT01_LESSONS.items(), 1):
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
        for learner_id in ("learner-1", "learner-2", "learner-3", "learner-4"):
            connection.execute(
                "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
                (
                    learner_id,
                    learner_id,
                    "zh-TW",
                    "Asia/Taipei",
                    "ACTIVE",
                    1,
                    "2026-07-30T00:00:00Z",
                    "2026-07-30T00:00:00Z",
                ),
            )
    qb02.Unit01ApprovedVariantSessionRuntime(database).initialize()
    return database


def start(database: Path, learner_id: str, skill: str, session_id: str) -> dict:
    return m3.LearnerStateStore(database).start_session(
        learner_id=learner_id,
        lesson_id=qb02.UNIT01_LESSONS[skill],
        session_id=session_id,
        at="2026-07-30T00:01:00Z",
    )


def plan_responses(database: Path, learner_id: str, session_id: str) -> tuple[dict, dict[str, object]]:
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    plan = runtime.assemble_session(
        learner_id=learner_id,
        session_id=session_id,
        selected_at="2026-07-30T00:02:00Z",
    )
    responses: dict[str, object] = {}
    with sqlite3.connect(database) as connection:
        for item in plan["items"]:
            contract = json.loads(
                connection.execute(
                    "SELECT contract_json FROM response_contracts WHERE asset_key=?",
                    (item["asset_key"],),
                ).fetchone()[0]
            )
            responses[item["item_id"]] = (
                list(contract["accepted_sequence"])
                if contract["response_type"] == "string_array"
                else contract["accepted_texts"][0]
            )
    return plan, responses


def test_u01qb04_completes_all_ten_items_and_exports_existing_m6_m12_evidence(tmp_path: Path):
    database = fixture_database(tmp_path)
    start(database, "learner-1", "READING", "session-r1")
    plan, responses = plan_responses(database, "learner-1", "session-r1")
    responses[plan["items"][0]["item_id"]] = "definitely wrong"
    output = tmp_path / "completion"
    readback = builder.complete_session(
        database=database,
        learner_id="learner-1",
        session_id="session-r1",
        responses=responses,
        output_root=output,
        completed_at="2026-07-30T00:30:00Z",
    )
    report = validator.validate(database=database, output_root=output)

    assert readback["validation_status"] == builder.PASS_STATUS
    assert readback["session"]["session_state"] == "COMPLETED"
    assert readback["session"]["session_version"] == 22
    assert readback["counts"] == {
        "planned_item_count": 10,
        "completed_item_count": 10,
        "exposure_count": 10,
        "attempt_count": 10,
        "scoring_result_count": 10,
        "m6_registry_entry_count": 10,
        "m12_attempt_count": 10,
    }
    assert readback["outcome_distribution"] == {"AUTO_FAIL": 1, "AUTO_PASS": 9}
    assert readback["legacy_allowlist_import_ready"] is False
    assert report["status"] == builder.PASS_STATUS
    assert report["error_count"] == 0, report["errors"]
    assert report["selected_item_count"] == 10
    assert report["exposure_count"] == 10
    assert report["attempt_count"] == 10
    assert report["scoring_result_count"] == 10
    assert report["evidence_export_count"] == 1
    assert report["m6_registry_entry_count"] == 10
    assert report["m12_attempt_count"] == 10


def test_u01qb04_rejects_incomplete_response_map_before_exposure_or_attempt(tmp_path: Path):
    database = fixture_database(tmp_path)
    start(database, "learner-2", "READING", "session-r2")
    plan, responses = plan_responses(database, "learner-2", "session-r2")
    responses.pop(plan["items"][0]["item_id"])
    with pytest.raises(builder.SessionCompletionError, match="response_map_identity_invalid"):
        builder.complete_session(
            database=database,
            learner_id="learner-2",
            session_id="session-r2",
            responses=responses,
            output_root=tmp_path / "incomplete",
        )
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT session_state FROM learning_sessions WHERE session_id='session-r2'"
        ).fetchone()[0] == "ACTIVE"
        assert connection.execute(
            "SELECT session_version FROM learning_sessions WHERE session_id='session-r2'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id='session-r2'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM response_attempts WHERE session_id='session-r2'"
        ).fetchone()[0] == 0


def test_u01qb04_rejects_speaking_completion_because_capture_is_deferred(tmp_path: Path):
    database = fixture_database(tmp_path)
    start(database, "learner-3", "SPEAKING", "session-s1")
    with pytest.raises(builder.SessionCompletionError, match="session_skill_not_ten_item_capture_eligible"):
        builder.complete_session(
            database=database,
            learner_id="learner-3",
            session_id="session-s1",
            responses={},
            output_root=tmp_path / "speaking",
        )


def test_u01qb04_safe_readback_contains_no_private_responses_or_contracts(tmp_path: Path):
    database = fixture_database(tmp_path)
    start(database, "learner-4", "READING", "session-r4")
    _plan, responses = plan_responses(database, "learner-4", "session-r4")
    output = tmp_path / "safe"
    builder.complete_session(
        database=database,
        learner_id="learner-4",
        session_id="session-r4",
        responses=responses,
        output_root=output,
    )
    safe = json.loads((output / builder.READBACK_NAME).read_text(encoding="utf-8"))
    rendered = json.dumps(safe, ensure_ascii=False)
    for key in builder.SAFE_READBACK_BLOCKED_KEYS:
        assert f'"{key}"' not in rendered
    private_registry = json.loads(
        (output / builder.PRIVATE_EVIDENCE_DIR / "a1fs_v1_m6_evidence_registry.private.json").read_text(
            encoding="utf-8"
        )
    )
    assert private_registry["attempt_count"] == 10
    assert all("response" in entry for entry in private_registry["entries"])


def test_u01qb04_validator_detects_private_evidence_digest_tampering(tmp_path: Path):
    database = fixture_database(tmp_path)
    start(database, "learner-1", "READING", "session-tamper")
    _plan, responses = plan_responses(database, "learner-1", "session-tamper")
    output = tmp_path / "tamper"
    builder.complete_session(
        database=database,
        learner_id="learner-1",
        session_id="session-tamper",
        responses=responses,
        output_root=output,
    )
    registry_path = output / builder.PRIVATE_EVIDENCE_DIR / "a1fs_v1_m6_evidence_registry.private.json"
    registry_path.write_text(registry_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report = validator.validate(database=database, output_root=output)
    assert "artifact_digest_invalid:m6_registry" in report["errors"]
