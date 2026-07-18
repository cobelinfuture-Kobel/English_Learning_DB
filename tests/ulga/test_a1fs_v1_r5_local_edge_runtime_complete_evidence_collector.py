from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders.build_a1fs_v1_m3_learner_profile_session_state_storage import LearnerStateStore
from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.validators import validate_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as validator

CELL_ID = "BREADTH_CELL_ASK_LOCATION_TRAVEL"


def _item(item_id: str, *, purpose: str = "CORE_PRACTICE", feature: bool = False):
    learner = {
        "prompt": "Ask where the bus stop is." if feature else f"Where is the bus stop? ({item_id})",
        "response_mode": "short_text" if feature else "select_one",
        "context": {"situation": "You are in a new town."} if feature else {},
    }
    if not feature:
        learner["options"] = ["It is next to the bank.", "It is eight o'clock.", "It is blue."]
    scoring = (
        {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "rubric": {"grammar": "where question", "meaning": "asks location"},
            "human_review_fallback": True,
        }
        if feature
        else {
            "scoring_mode": "EXACT_OPTION",
            "response_type": "string",
            "accepted_texts": ["It is next to the bank."],
            "case_insensitive": True,
            "punctuation_tolerance": True,
            "human_review_fallback": False,
        }
    )
    item = {
        "item_id": item_id,
        "breadth_cell_id": CELL_ID,
        "capability_id": "CAP_ASK_LOCATION",
        "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
        "domain": "TRAVEL_TRANSPORT",
        "level": "A1",
        "skill": "SPEAKING",
        "purpose": purpose,
        "task_type": "GUIDED_RESPONSE" if feature else "SELECT_ONE",
        "support_level": "S1_KEYWORD_OR_VISUAL",
        "initiative_level": "GUIDED_INITIATION",
        "interaction_variation": "EXPECTED_SCRIPT",
        "transfer_distance": "NONE",
        "template_family": f"TEMPLATE_{item_id}",
        "stimulus_fingerprint": hashlib.sha256(item_id.encode()).hexdigest(),
        "media_payload_state": "AVAILABLE",
        "source_refs": [f"SOURCE_{item_id}"],
        "authority_refs": ["AUTHORITY_ASK_LOCATION_A1"],
        "provenance": "EXISTING_AUTHORITY_REVIEWED",
        "learner_contract": learner,
        "private_scoring_contract": scoring,
        "validator_status": "PASS",
        "candidate_sha256": hashlib.sha256((item_id + "candidate").encode()).hexdigest(),
        "authority_review": {
            "status": "APPROVED",
            "reviewer_id": "authority-reviewer",
            "reviewed_at": "2026-07-19T00:00:00+08:00",
            "criteria": {},
            "candidate_sha256": hashlib.sha256((item_id + "candidate").encode()).hexdigest(),
        },
        "admission": {
            "status": "APPROVED",
            "learner_fingerprint": hashlib.sha256((item_id + "learner").encode()).hexdigest(),
            "candidate_sha256": hashlib.sha256((item_id + "candidate").encode()).hexdigest(),
        },
    }
    return item


def _runtime_fixture(tmp_path: Path, *, max_recent_reuse: int = 1):
    payload = {"prompt": "placeholder"}
    asset = {
        "asset_key": "BASE:CHK",
        "asset_id": "BASE-CHK",
        "lesson_id": "BASE",
        "skill": "READING",
        "level": "A1",
        "role": "CHK",
        "payload": payload,
        "content_digest": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
    }
    lesson = {
        "lesson_id": "BASE",
        "lesson_node_id": "LESSON:READING:BASE",
        "skill": "READING",
        "level": "A1",
        "roles": ["CHK"],
        "requirement_node_ids": [],
        "asset_keys": ["BASE:CHK"],
    }
    consumer = {
        "validation_status": "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY",
        "lesson_catalog": [lesson],
        "asset_records": [asset],
        "counts": {"lesson_count": 1, "asset_record_count": 1},
    }
    consumer_path = tmp_path / "consumer.json"
    consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    database = tmp_path / "runtime.sqlite3"
    state = LearnerStateStore(database)
    state.initialize(consumer_path)
    state.create_profile(
        learner_id="learner",
        display_label="Learner",
        at="2026-07-19T00:00:00Z",
    )
    items = [
        _item("ITEM_1"),
        _item("ITEM_2"),
        _item("ITEM_REMED", purpose="REMEDIATION", feature=True),
    ]
    source_bindings = {
        "ontology_sha256": "a" * 64,
        "coverage_sha256": "b" * 64,
        "candidate_registry_sha256": "c" * 64,
        "capacity_policy_registry_sha256": "d" * 64,
    }
    bank_core = {
        "task_id": r4.TASK_ID,
        "schema_version": r4.BANK_SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "private_local_only": True,
        "source_bindings": source_bindings,
        "selection_contract": {
            "local_free_generation_enabled": False,
            "gpt_direct_item_admission_enabled": False,
            "qwen_direct_item_admission_enabled": False,
            "formal_item_requires_admission_approved": True,
            "recent_reuse_policy_source": "CELL_CAPACITY_POLICY",
        },
        "item_count": len(items),
        "items": items,
    }
    bank = {**bank_core, "bank_sha256": r4.digest(bank_core)}
    report_core = {
        "task_id": r4.TASK_ID,
        "schema_version": r4.SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "source_bindings": source_bindings,
        "counts": {
            "candidate_count": 3,
            "approved_item_count": 3,
            "rejected_or_pending_count": 0,
            "breadth_cell_count": 1,
            "capacity_policy_count": 1,
            "supply_status_counts": {"READY_FOR_LOCAL_SELECTION": 1},
            "admission_status_counts": {"APPROVED": 3},
        },
        "cell_supply": [{
            "breadth_cell_id": CELL_ID,
            "capability_id": "CAP_ASK_LOCATION",
            "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
            "domain": "TRAVEL_TRANSPORT",
            "supply_status": "READY_FOR_LOCAL_SELECTION",
            "capacity_policy_present": True,
            "approved_item_count": 3,
            "approved_item_ids": [row["item_id"] for row in items],
            "skill_projection": {"required": ["SPEAKING"], "approved": ["SPEAKING"], "missing": []},
            "purpose_capacity": {},
            "decision_counts": {"APPROVED": 3},
            "max_recent_reuse": max_recent_reuse,
        }],
        "admission_decisions": [],
        "claim_boundaries": {
            "canonical_authority_modified": False,
            "m1_graph_modified": False,
            "r3_denominator_modified": False,
            "local_free_generation_enabled": False,
            "gpt_direct_admission_enabled": False,
            "qwen_required": False,
            "a2_content_admitted": False,
            "audio_files_required": False,
            "mastery_claimed": False,
        },
        "next_short_step": r4.NEXT_SHORT_STEP,
    }
    report = {**report_core, "report_sha256": r4.digest(report_core)}
    bank_path = tmp_path / "bank.json"
    report_path = tmp_path / "report.json"
    bank_path.write_text(json.dumps(bank), encoding="utf-8")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    runtime = r5.LocalEdgeRuntime(database)
    runtime.initialize(bank_path=bank_path, supply_report_path=report_path)
    return database, runtime


def _complete_core_session(runtime: r5.LocalEdgeRuntime, *, count: int = 2):
    session = runtime.start_session(
        learner_id="learner",
        breadth_cell_id=CELL_ID,
        purpose="CORE_PRACTICE",
        planned_item_count=count,
        session_id=f"SESSION_CORE_{count}",
        started_at="2026-07-19T00:10:00Z",
    )
    token = session["access_token"]
    version = session["session"]["session_version"]
    item_ids = [row["item"]["item_id"] for row in session["assignments"]]
    for index, item_id in enumerate(item_ids, start=1):
        result = runtime.submit_response(
            session_id=session["session"]["session_id"],
            access_token=token,
            item_id=item_id,
            response="It is next to the bank.",
            response_time_ms=1000 * index,
            hint_count=index - 1,
            revision_count=0,
            expected_session_version=version,
            attempt_id=f"ATTEMPT_{count}_{index}",
            submitted_at=f"2026-07-19T00:1{index}:00Z",
        )
        version = result["session_version"]
    completed = runtime.complete_session(
        session_id=session["session"]["session_id"],
        access_token=token,
        expected_session_version=version,
        at="2026-07-19T00:20:00Z",
    )
    return session, completed


def test_runtime_consumes_only_admitted_items_and_hides_scoring_contract(tmp_path: Path) -> None:
    database, runtime = _runtime_fixture(tmp_path)
    started = runtime.start_session(
        learner_id="learner", breadth_cell_id=CELL_ID, purpose="CORE_PRACTICE",
        planned_item_count=2, session_id="SESSION_1", started_at="2026-07-19T00:10:00Z",
    )
    assert started["session"]["session_state"] == "ACTIVE"
    assert len(started["assignments"]) == 2
    assert all("private_scoring_contract" not in row["item"] for row in started["assignments"])
    assert all(row["item"]["purpose"] == "CORE_PRACTICE" for row in started["assignments"])
    with pytest.raises(r5.LocalEdgeRuntimeError, match="edge_session_access_denied"):
        runtime.session_payload(session_id="SESSION_1", access_token="wrong")
    report = validator.validate_database(database)
    assert report["error_count"] == 0, report["errors"]


def test_complete_session_exports_objective_private_and_safe_evidence(tmp_path: Path) -> None:
    database, runtime = _runtime_fixture(tmp_path)
    _, completed = _complete_core_session(runtime)
    assert completed["session"]["session_state"] == "COMPLETED"
    exported = runtime.export_evidence(
        learner_id="learner", output_root=tmp_path / "evidence",
        exported_at="2026-07-19T00:30:00Z",
    )
    package = json.loads(Path(exported["package_path"]).read_text())
    safe = json.loads(Path(exported["safe_summary_path"]).read_text())
    assert package["attempt_count"] == 2 and package["valid_attempt_count"] == 2
    assert all(row["outcome"] == "AUTO_PASS" for row in package["entries"])
    assert all(row["response_time_ms"] > 0 for row in package["entries"])
    assert all("response" not in row for row in safe["entries"])
    assert package["claim_boundaries"]["qwen_used"] is False
    assert package["claim_boundaries"]["mastery_written"] is False
    db_report = validator.validate_database(database)
    export_report = validator.validate_exports(
        Path(exported["package_path"]), Path(exported["safe_summary_path"]), Path(exported["jsonl_path"])
    )
    assert db_report["error_count"] == 0, db_report["errors"]
    assert export_report["error_count"] == 0, export_report["errors"]


def test_pause_resume_backup_and_restore_preserve_runtime_state(tmp_path: Path) -> None:
    database, runtime = _runtime_fixture(tmp_path)
    started = runtime.start_session(
        learner_id="learner", breadth_cell_id=CELL_ID, purpose="CORE_PRACTICE",
        planned_item_count=1, session_id="SESSION_RECOVERY", started_at="2026-07-19T00:10:00Z",
    )
    token = started["access_token"]
    paused = runtime.pause_session(
        session_id="SESSION_RECOVERY", access_token=token,
        expected_session_version=1, at="2026-07-19T00:11:00Z",
    )
    assert paused["session"]["session_state"] == "PAUSED"
    resumed = runtime.resume_session(
        session_id="SESSION_RECOVERY", access_token=token,
        expected_session_version=2, at="2026-07-19T00:12:00Z",
    )
    assert resumed["session"]["session_state"] == "ACTIVE"
    backup = runtime.backup(
        backup_path=tmp_path / "backup.sqlite3",
        manifest_path=tmp_path / "backup.manifest.json",
        created_at="2026-07-19T00:13:00Z",
    )
    restored = r5.LocalEdgeRuntime.restore(
        backup_path=Path(backup["backup_path"]),
        manifest_path=Path(backup["manifest_path"]),
        target_path=tmp_path / "restored.sqlite3",
    )
    assert restored["restored_sha256"] == backup["backup_sha256"]
    restored_runtime = r5.LocalEdgeRuntime(Path(restored["target_path"]))
    payload = restored_runtime.session_payload(session_id="SESSION_RECOVERY", access_token=token)
    assert payload["session"]["session_state"] == "ACTIVE"
    assert validator.validate_database(Path(restored["target_path"]))["error_count"] == 0


def test_recent_item_exclusion_rotates_without_free_generation(tmp_path: Path) -> None:
    _, runtime = _runtime_fixture(tmp_path, max_recent_reuse=0)
    first = runtime.start_session(
        learner_id="learner", breadth_cell_id=CELL_ID, purpose="CORE_PRACTICE",
        planned_item_count=1, session_id="SESSION_ROTATE_1", started_at="2026-07-19T00:10:00Z",
    )
    first_item = first["assignments"][0]["item"]["item_id"]
    result = runtime.submit_response(
        session_id="SESSION_ROTATE_1", access_token=first["access_token"], item_id=first_item,
        response="It is next to the bank.", response_time_ms=1000, hint_count=0, revision_count=0,
        expected_session_version=1, attempt_id="ATTEMPT_ROTATE_1", submitted_at="2026-07-19T00:11:00Z",
    )
    runtime.complete_session(
        session_id="SESSION_ROTATE_1", access_token=first["access_token"],
        expected_session_version=result["session_version"], at="2026-07-19T00:12:00Z",
    )
    second = runtime.start_session(
        learner_id="learner", breadth_cell_id=CELL_ID, purpose="CORE_PRACTICE",
        planned_item_count=1, session_id="SESSION_ROTATE_2", started_at="2026-07-19T00:20:00Z",
    )
    assert second["assignments"][0]["item"]["item_id"] != first_item
    with pytest.raises(r5.LocalEdgeRuntimeError, match="CONTENT_CAPACITY_INSUFFICIENT"):
        runtime.start_session(
            learner_id="other", breadth_cell_id=CELL_ID, purpose="CORE_PRACTICE",
            planned_item_count=3,
        )


def test_feature_rubric_requires_human_review_before_completion(tmp_path: Path) -> None:
    _, runtime = _runtime_fixture(tmp_path)
    started = runtime.start_session(
        learner_id="learner", breadth_cell_id=CELL_ID, purpose="REMEDIATION",
        planned_item_count=1, session_id="SESSION_REVIEW", started_at="2026-07-19T00:10:00Z",
    )
    token = started["access_token"]
    item_id = started["assignments"][0]["item"]["item_id"]
    captured = runtime.submit_response(
        session_id="SESSION_REVIEW", access_token=token, item_id=item_id,
        response="Excuse me. Where is the bus stop?", response_time_ms=2500,
        hint_count=0, revision_count=1, expected_session_version=1,
        attempt_id="ATTEMPT_REVIEW", submitted_at="2026-07-19T00:11:00Z",
    )
    assert captured["outcome"] == "PENDING_HUMAN_REVIEW"
    with pytest.raises(r5.LocalEdgeRuntimeError, match="session_reviews_unresolved"):
        runtime.complete_session(
            session_id="SESSION_REVIEW", access_token=token,
            expected_session_version=2, at="2026-07-19T00:12:00Z",
        )
    reviewed = runtime.review_response(
        attempt_id="ATTEMPT_REVIEW", decision="APPROVE", reviewer_id="teacher",
        criteria={
            "grammar_target_match": True,
            "meaning_matches_context": True,
            "complete_response": True,
        },
        reviewed_at="2026-07-19T00:13:00Z",
    )
    assert reviewed["outcome"] == "HUMAN_APPROVE"
    completed = runtime.complete_session(
        session_id="SESSION_REVIEW", access_token=token,
        expected_session_version=2, at="2026-07-19T00:14:00Z",
    )
    assert completed["session"]["session_state"] == "COMPLETED"


def test_system_error_validity_excludes_attempt_from_valid_evidence(tmp_path: Path) -> None:
    _, runtime = _runtime_fixture(tmp_path)
    started = runtime.start_session(
        learner_id="learner", breadth_cell_id=CELL_ID, purpose="CORE_PRACTICE",
        planned_item_count=1, session_id="SESSION_INVALID", started_at="2026-07-19T00:10:00Z",
    )
    item_id = started["assignments"][0]["item"]["item_id"]
    captured = runtime.submit_response(
        session_id="SESSION_INVALID", access_token=started["access_token"], item_id=item_id,
        response="It is next to the bank.", response_time_ms=1000, hint_count=0, revision_count=0,
        expected_session_version=1, attempt_id="ATTEMPT_INVALID", submitted_at="2026-07-19T00:11:00Z",
    )
    pending = runtime.set_attempt_validity(
        attempt_id="ATTEMPT_INVALID", new_status="PENDING_VALIDITY_REVIEW",
        reason_code="UI_SERIALIZATION_SUSPECTED", actor_id="validator",
        occurred_at="2026-07-19T00:12:00Z",
    )
    assert pending["mastery_eligible"] is False
    runtime.set_attempt_validity(
        attempt_id="ATTEMPT_INVALID", new_status="INVALIDATED_SYSTEM_ERROR",
        reason_code="UI_SERIALIZATION_CONFIRMED", actor_id="validator",
        occurred_at="2026-07-19T00:13:00Z",
    )
    with pytest.raises(r5.LocalEdgeRuntimeError, match="terminal_validity_status_cannot_change"):
        runtime.set_attempt_validity(
            attempt_id="ATTEMPT_INVALID", new_status="PENDING_VALIDITY_REVIEW",
            reason_code="REOPEN", actor_id="developer",
        )
    runtime.complete_session(
        session_id="SESSION_INVALID", access_token=started["access_token"],
        expected_session_version=captured["session_version"], at="2026-07-19T00:14:00Z",
    )
    exported = runtime.export_evidence(learner_id="learner", output_root=tmp_path / "invalid-evidence")
    package = json.loads(Path(exported["package_path"]).read_text())
    assert package["attempt_count"] == 1 and package["valid_attempt_count"] == 0
    assert package["entries"][0]["validity_status"] == "INVALIDATED_SYSTEM_ERROR"


def test_local_ui_and_launcher_are_loopback_only_and_answer_safe(tmp_path: Path) -> None:
    database, runtime = _runtime_fixture(tmp_path)
    started = runtime.start_session(
        learner_id="learner", breadth_cell_id=CELL_ID, purpose="CORE_PRACTICE",
        planned_item_count=1, session_id="SESSION_UI", started_at="2026-07-19T00:10:00Z",
    )
    html = r5.learner_html().casefold()
    assert "private_scoring_contract" not in html
    assert "accepted_texts" not in html
    assert "http://" not in html and "https://" not in html
    assert r5.LOOPBACK_HOST == "127.0.0.1"
    launcher = r5.write_windows_launcher(
        path=tmp_path / "start_learning.bat",
        database_path=database,
        session_id="SESSION_UI",
        access_token=started["access_token"],
    )
    content = launcher.read_text(encoding="utf-8")
    assert " serve " in content and "--session-id" in content and "--token" in content
