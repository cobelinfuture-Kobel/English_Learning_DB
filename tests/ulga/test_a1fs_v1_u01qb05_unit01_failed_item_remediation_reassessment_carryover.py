from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb04_unit01_ten_item_session_completion_evidence_export as qb04
from ulga.builders import build_a1fs_v1_u01qb05_unit01_failed_item_remediation_reassessment_carryover as builder
from ulga.validators import validate_a1fs_v1_u01qb05_unit01_failed_item_remediation_reassessment_carryover as validator


def fixture_database(tmp_path: Path) -> Path:
    database = tmp_path / "learner.sqlite3"
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
                (lesson_id, f"U01:{index}", skill, "A1", json.dumps(["CHK"]), "[]", 1),
            )
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
            ("learner", "Learner", "zh-TW", "Asia/Taipei", "ACTIVE", 1,
             "2026-07-30T00:00:00Z", "2026-07-30T00:00:00Z"),
        )
    qb02.Unit01ApprovedVariantSessionRuntime(database).initialize()
    return database


def accepted_responses(database: Path, plan: dict) -> dict[str, object]:
    result: dict[str, object] = {}
    with sqlite3.connect(database) as connection:
        for item in plan["items"]:
            contract = json.loads(connection.execute(
                "SELECT contract_json FROM response_contracts WHERE asset_key=?",
                (item["asset_key"],),
            ).fetchone()[0])
            result[item["item_id"]] = (
                list(contract["accepted_sequence"])
                if contract["response_type"] == "string_array"
                else contract["accepted_texts"][0]
            )
    return result


def test_u01qb05_remediation_reassessment_and_recent_carryover(tmp_path: Path):
    database = fixture_database(tmp_path)
    store = m3.LearnerStateStore(database)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    store.start_session(
        learner_id="learner",
        lesson_id=qb02.UNIT01_LESSONS["READING"],
        session_id="initial",
        at="2026-07-30T00:01:00Z",
    )
    initial_plan = runtime.assemble_session(
        learner_id="learner", session_id="initial", selected_at="2026-07-30T00:02:00Z"
    )
    initial_responses = accepted_responses(database, initial_plan)
    failed_item_id = initial_plan["items"][0]["item_id"]
    initial_responses[failed_item_id] = "incorrect response"
    qb04.complete_session(
        database=database,
        learner_id="learner",
        session_id="initial",
        responses=initial_responses,
        output_root=tmp_path / "initial-output",
        completed_at="2026-07-30T00:30:00Z",
    )

    prepared = builder.prepare_reassessment(
        database=database,
        learner_id="learner",
        failed_item_id=failed_item_id,
        reassessment_session_id="reassessment",
    )
    selected = next(item for item in prepared["items"] if item["item_id"] == failed_item_id)
    assert selected["selection_reason"] == "REMEDIATION"
    output = tmp_path / "cycle"
    readback = builder.complete_reassessment_and_carryover(
        database=database,
        learner_id="learner",
        failed_item_id=failed_item_id,
        reassessment_session_id="reassessment",
        responses=accepted_responses(database, prepared),
        carryover_session_id="carryover",
        output_root=output,
        completed_at="2026-07-30T01:00:00Z",
        carryover_ended_at="2026-07-30T01:01:00Z",
    )
    report = validator.validate(database=database, output_root=output)

    assert readback["validation_status"] == builder.PASS_STATUS
    assert readback["reassessment"]["outcome"] == "AUTO_PASS"
    assert readback["carryover"]["failed_item_reselected"] is False
    assert readback["failed_item_outcome_history"] == [
        {"session_id": "initial", "outcome": "AUTO_FAIL"},
        {"session_id": "reassessment", "outcome": "AUTO_PASS"},
    ]
    assert report["status"] == builder.PASS_STATUS
    assert report["error_count"] == 0, report["errors"]
    assert report["failed_item_attempt_count"] == 2
    assert report["reassessment_exposure_count"] == 10
    assert report["reassessment_attempt_count"] == 10
    assert report["carryover_plan_item_count"] == 10
    assert report["carryover_exposure_count"] == 0
    assert report["carryover_attempt_count"] == 0
