from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07
from ulga.builders import build_a1fs_online_v1_s08_private_multiunit_learner_journey_qa as s08
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.validators.validate_a1fs_online_v1_s08_private_multiunit_learner_journey_qa import validate_outputs


def _contract(asset_key: str, lesson_id: str, skill: str, *, capture: bool) -> dict:
    return {
        "asset_key": asset_key,
        "lesson_id": lesson_id,
        "skill": skill,
        "role": "CHK" if capture else "MOD",
        "prompt": f"Complete {asset_key}.",
        "capture_enabled": capture,
        "response_type": "string",
        "scoring_mode": "EXACT_OPTION" if capture else "NONE",
        "accepted_texts": ["correct"] if capture else [],
        "accepted_sequence": [],
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
        "rubric": {},
        "m12_item_id": f"A1FS_ASSET:{asset_key}",
        "m12_session_bank_sha256": None,
    }


def _source_s07(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "s07_source"
    root.mkdir(parents=True)
    database = root / "learner_progress.sqlite3"
    bundle_root = root / "bundles"
    bundle_root.mkdir()
    static_root = root / "static"
    static_root.mkdir()
    (static_root / "index.html").write_text("source", encoding="utf-8")

    lessons: list[tuple[str, str, str, str]] = []
    assets: list[tuple[str, str, str, str, bool]] = []
    bundles: dict[str, str] = {}
    for unit_index, grammar_id in enumerate(("GRAMMAR_UNIT_ONE", "GRAMMAR_UNIT_TWO"), start=1):
        for skill in ("READING", "WRITING", "SPEAKING"):
            lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:{skill}"
            lesson_node_id = f"LESSON_NODE:{grammar_id}:{skill}"
            asset_key = f"ASSET:{grammar_id}:{skill}:1"
            role = "CHK" if skill in {"READING", "WRITING"} else "MOD"
            capture = skill in {"READING", "WRITING"}
            lessons.append((lesson_id, lesson_node_id, skill, "A1"))
            assets.append((asset_key, lesson_id, role, f"digest-{unit_index}-{skill}", capture))
            bundle = {
                "lesson": {"lesson_id": lesson_id, "skill": skill, "level": "A1"},
                "assets": [
                    {
                        "asset_key": asset_key,
                        "role": role,
                        "learner_payload": {
                            "prompt": f"Complete {skill.lower()}.",
                            "options": ["correct", "wrong"] if capture else [],
                            "response_capture_enabled": capture,
                        },
                    }
                ],
            }
            path = bundle_root / f"{unit_index}_{skill.lower()}.private.json"
            path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
            bundles[lesson_id] = str(path)

    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.executescript(m6.SQL)
        connection.executescript(s05.PERSISTENCE_SQL)
        metadata = {
            "task_id": m3.TASK_ID,
            "schema_version": m3.SCHEMA_VERSION,
            "validation_status": m3.STATUS,
            "mastery_write_enabled": "false",
            "a2_session_enabled": "false",
            "learner_release_approved": "false",
            "s07_task_id": s07.TASK_ID,
            "s07_schema_version": s07.SCHEMA_VERSION,
            "s07_validation_status": s07.PASS_STATUS,
        }
        connection.executemany("INSERT INTO metadata(key,value) VALUES(?,?)", metadata.items())
        for lesson_id, lesson_node_id, skill, level in lessons:
            connection.execute(
                "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (lesson_id, lesson_node_id, skill, level, "[]", "[]", 1),
            )
        for asset_key, lesson_id, role, content_digest, capture in assets:
            connection.execute(
                "INSERT INTO lesson_assets VALUES(?,?,?,?,?)",
                (asset_key, asset_key, lesson_id, role, content_digest),
            )
            skill = lesson_id.rsplit(":", 1)[1]
            contract = _contract(asset_key, lesson_id, skill, capture=capture)
            connection.execute(
                "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
                (
                    asset_key,
                    lesson_id,
                    skill,
                    role,
                    m6.canonical(contract),
                    m6.sha(contract),
                    int(capture),
                ),
            )
        connection.commit()

    bundle_index = root / "bundle_index.private.json"
    bundle_index.write_text(
        json.dumps(
            {
                "task_id": s07.TASK_ID,
                "units": [
                    {"grammar_unit_id": "GRAMMAR_UNIT_ONE", "sequence_index": 1},
                    {"grammar_unit_id": "GRAMMAR_UNIT_TWO", "sequence_index": 2},
                ],
                "lessons": bundles,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    core = {
        "task_id": s07.TASK_ID,
        "program_id": s07.PROGRAM_ID,
        "schema_version": s07.SCHEMA_VERSION,
        "validation_status": s07.PASS_STATUS,
        "release_profile": s07.RELEASE_PROFILE,
        "runtime_outputs": {
            "root": str(root),
            "database_path": str(database),
            "bundle_index_path": str(bundle_index),
            "static_root": str(static_root),
        },
        "admission_summary": {"admitted_unit_count": 2},
        "product_status": s07.PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": s07.NEXT_SHORT_STEP,
    }
    receipt = {**core, "artifact_sha256": s07.digest(core)}
    receipt_path = root / "multiunit_runtime_expansion.private.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt_path, database, bundle_index


def _materialized(tmp_path: Path) -> tuple[Path, Path, dict, dict, dict]:
    s07_path, production_database, _ = _source_s07(tmp_path)
    output_root = tmp_path / "s08"
    receipt, safe = s08.materialize(s07_receipt_path=s07_path, output_root=output_root)
    validation = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=output_root,
        s07_path=s07_path,
    )
    return s07_path, production_database, receipt, safe, validation


def test_materializes_complete_multiunit_multiskill_journey_without_mutating_production(tmp_path: Path) -> None:
    _, production_database, receipt, safe, validation = _materialized(tmp_path)
    assert validation["error_count"] == 0, validation["errors"]
    assert receipt["journey_summary"] == {
        "profile_count": 1,
        "session_count": 3,
        "completed_session_count": 2,
        "abandoned_session_count": 1,
        "active_session_count": 0,
        "exposure_count": 3,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
        "distinct_unit_count": 2,
        "distinct_skill_count": 3,
        "resume_after_process_restart": True,
        "cross_unit_switch_blocked_while_active": True,
        "cross_unit_switch_after_completion": True,
        "cross_skill_switch_after_completion": True,
        "speaking_submission_blocked": True,
        "final_progress_readback_digest_stable": True,
        "process_restart_count": 2,
    }
    assert receipt["production_safety"]["production_database_unchanged"] is True
    assert receipt["production_safety"]["database_sha256_before"] == s08.file_digest(production_database)
    assert safe["product_status"] == s08.PRODUCT_STATUS


def test_active_session_survives_application_reopen_and_can_be_abandoned_over_http(tmp_path: Path) -> None:
    s07_path, database, bundle_index = _source_s07(tmp_path)
    del s07_path
    runtime_database = tmp_path / "http_runtime.sqlite3"
    shutil.copy2(database, runtime_database)
    bundles, sequence_by_grammar = s07._load_bundle_index(bundle_index)
    app = s08.JourneyWorkbenchApplication(
        database_path=runtime_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=s08.CANARY_LEARNER_ID,
    )
    app.state_store.create_profile(
        learner_id=s08.CANARY_LEARNER_ID,
        display_label="HTTP Canary",
        at="2026-01-10T01:00:00Z",
    )
    reading_id, _ = s08._lesson_bundle(bundles, sequence_by_grammar, unit_rank=1, skill="READING")
    server_root = tmp_path / "http_static"
    s08._write_static(server_root)
    server = s08.JourneyWorkbenchServer(("127.0.0.1", 0), app, server_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        started = s04._request(port, "POST", "/api/session/start", {
            "lesson_id": reading_id,
            "learner_id": s08.CANARY_LEARNER_ID,
            "session_id": "HTTP_SESSION",
            "at": "2026-01-10T01:00:10Z",
        })
        active = s04._request(port, "GET", "/api/session/active")
        assert active["active"] is True
        assert active["session"]["session_id"] == "HTTP_SESSION"
        abandoned = s04._request(port, "POST", "/api/session/abandon", {
            "session_id": "HTTP_SESSION",
            "expected_session_version": started["session_version"],
            "at": "2026-01-10T01:00:20Z",
        })
        assert abandoned["session_state"] == "ABANDONED"
        assert s04._request(port, "GET", "/api/session/active") == {"active": False}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_non_loopback_binding_remains_forbidden(tmp_path: Path) -> None:
    _, database, bundle_index = _source_s07(tmp_path)
    bundles, sequence_by_grammar = s07._load_bundle_index(bundle_index)
    app = s08.JourneyWorkbenchApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=s08.CANARY_LEARNER_ID,
    )
    with pytest.raises(s08.JourneyQAError, match="non_loopback_host_forbidden"):
        s08.JourneyWorkbenchServer(("0.0.0.0", 0), app, tmp_path)


def test_safe_readback_is_private_free_and_deterministic(tmp_path: Path) -> None:
    s07_path, production_database, _ = _source_s07(tmp_path)
    output_root = tmp_path / "s08"
    receipt1, safe1 = s08.materialize(s07_receipt_path=s07_path, output_root=output_root)
    production_sha = s08.file_digest(production_database)
    receipt2, safe2 = s08.materialize(s07_receipt_path=s07_path, output_root=output_root)
    rendered = json.dumps(safe1, ensure_ascii=False)
    assert safe1 == safe2
    assert receipt1["artifact_sha256"] == receipt2["artifact_sha256"]
    assert s08.file_digest(production_database) == production_sha
    for token in (
        s08.CANARY_LEARNER_ID,
        s08.READING_SESSION_ID,
        "accepted_texts",
        "asset_key",
        "database_path",
        "learner_payload",
        "correct",
    ):
        assert token not in rendered
