from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

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
        for learner in ("learner-r", "learner-s"):
            connection.execute(
                "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
                (
                    learner,
                    learner,
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


def start_session(database: Path, *, learner_id: str, skill: str, session_id: str) -> dict:
    return m3.LearnerStateStore(database).start_session(
        learner_id=learner_id,
        lesson_id=qb02.UNIT01_LESSONS[skill],
        session_id=session_id,
        at="2026-07-30T00:01:00Z",
    )


def accepted_response(database: Path, asset_key: str):
    with sqlite3.connect(database) as connection:
        contract = json.loads(
            connection.execute(
                "SELECT contract_json FROM response_contracts WHERE asset_key=?", (asset_key,)
            ).fetchone()[0]
        )
    if contract["response_type"] == "string_array":
        return contract["accepted_sequence"]
    return contract["accepted_texts"][0]


def test_u01qb03_builds_m5_lineage_private_workbench_without_answer_leak(tmp_path: Path):
    database = fixture_database(tmp_path)
    start_session(database, learner_id="learner-r", skill="READING", session_id="session-r")
    output = tmp_path / "workbench"
    manifest = builder.build_workbench(
        database=database,
        learner_id="learner-r",
        session_id="session-r",
        output_root=output,
    )
    bundle = json.loads((output / "session.private.json").read_text(encoding="utf-8"))
    rendered = json.dumps(bundle, ensure_ascii=False)

    assert manifest["validation_status"] == builder.PASS_STATUS
    assert manifest["item_count"] == 10
    assert bundle["renderer_authority_task_id"] == builder.m5.TASK_ID
    assert bundle["runtime_authority_task_id"] == qb02.TASK_ID
    assert bundle["item_count"] == 10
    assert all(item["skill"] == "READING" for item in bundle["items"])
    assert all(item["capture_enabled"] is True for item in bundle["items"])
    for forbidden in builder.BLOCKED_LEARNER_KEYS:
        assert f'"{forbidden}"' not in rendered
    assert (output / "index.html").is_file()
    assert (output / "styles.css").is_file()
    assert (output / "app.js").is_file()


def test_u01qb03_real_attempt_routes_exposure_and_scoring_to_existing_m3_m6(tmp_path: Path):
    database = fixture_database(tmp_path)
    session = start_session(database, learner_id="learner-r", skill="READING", session_id="session-r")
    output = tmp_path / "workbench"
    builder.build_workbench(
        database=database,
        learner_id="learner-r",
        session_id="session-r",
        output_root=output,
    )
    bundle = json.loads((output / "session.private.json").read_text(encoding="utf-8"))
    controller = builder.LearnerAttemptController(
        database, learner_id="learner-r", session_id="session-r"
    )
    first, second = bundle["items"][:2]
    passed = controller.submit(
        item_id=first["item_id"],
        response=accepted_response(database, first["asset_key"]),
        expected_session_version=session["session_version"],
    )
    failed = controller.submit(
        item_id=second["item_id"],
        response="definitely wrong",
        expected_session_version=passed["session_version"],
    )
    report = validator.validate(database=database, output_root=output)

    assert passed["outcome"] == "AUTO_PASS"
    assert passed["m6_response_scoring_reused"] is True
    assert failed["outcome"] == "AUTO_FAIL"
    assert failed["parallel_scoring_created"] is False
    assert report["status"] == builder.PASS_STATUS
    assert report["error_count"] == 0, report["errors"]
    assert report["item_exposure_count"] == 2
    assert report["attempt_count"] == 2
    assert report["scoring_result_count"] == 2
    assert report["auto_pass_count"] == 1
    assert report["auto_fail_count"] == 1


def test_u01qb03_speaking_renders_practice_cards_but_blocks_capture(tmp_path: Path):
    database = fixture_database(tmp_path)
    session = start_session(database, learner_id="learner-s", skill="SPEAKING", session_id="session-s")
    output = tmp_path / "speaking"
    builder.build_workbench(
        database=database,
        learner_id="learner-s",
        session_id="session-s",
        output_root=output,
    )
    bundle = json.loads((output / "session.private.json").read_text(encoding="utf-8"))
    assert all(item["capture_enabled"] is False for item in bundle["items"])
    controller = builder.LearnerAttemptController(
        database, learner_id="learner-s", session_id="session-s"
    )
    with pytest.raises(qb02.SessionRuntimeError, match="item_response_capture_disabled"):
        controller.submit(
            item_id=bundle["items"][0]["item_id"],
            response="a book",
            expected_session_version=session["session_version"],
        )


def test_u01qb03_validator_detects_private_contract_leak(tmp_path: Path):
    database = fixture_database(tmp_path)
    start_session(database, learner_id="learner-r", skill="READING", session_id="session-r")
    output = tmp_path / "workbench"
    builder.build_workbench(
        database=database,
        learner_id="learner-r",
        session_id="session-r",
        output_root=output,
    )
    bundle_path = output / "session.private.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["items"][0]["accepted_texts"] = ["leak"]
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = bundle_path.read_bytes()
    manifest["files"]["session.private.json"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = validator.validate(database=database, output_root=output, require_attempts=False)
    assert any(error.startswith("private_keys_exposed:accepted_texts") for error in report["errors"])
