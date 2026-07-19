from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_r5_content_error_session_recovery as recovery
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r5_production_bootstrap_first_session as bootstrap

REPO_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap_fixture(tmp_path: Path, monkeypatch):
    path = REPO_ROOT / "tests/ulga/test_a1fs_v1_r5_production_bootstrap_first_session.py"
    spec = importlib.util.spec_from_file_location("r5_bootstrap_fixture", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._bootstrap(tmp_path, monkeypatch)


def _paths(output: Path) -> tuple[Path, Path, Path]:
    return (
        output / bootstrap.PRIVATE_RECEIPT,
        output / "r3r4" / population.BANK_OUTPUT,
        output / "r3r4" / population.SUPPLY_OUTPUT,
    )


def _corrupt_assigned_item(database: Path, session_id: str) -> str:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT i.* FROM edge_assignments a JOIN edge_runtime_items i USING(item_id)
            WHERE a.session_id=? ORDER BY a.assignment_sequence LIMIT 1""",
            (session_id,),
        ).fetchone()
        assert row
        item = json.loads(row["item_json"])
        item["learner_contract"] = {
            "prompt": "文本中提到了哪個地點？",
            "response_mode": "short_text",
        }
        connection.execute(
            "UPDATE edge_runtime_items SET item_json=?,item_digest=? WHERE item_id=?",
            (r5.canonical(item), r5.digest(item), row["item_id"]),
        )
        connection.execute(
            "UPDATE r5_metadata SET value=? WHERE key='source_bank_sha256'",
            ("0" * 64,),
        )
        connection.commit()
        return str(row["item_id"])


def test_recovery_abandons_unanswerable_session_and_rebinds_bank(tmp_path: Path, monkeypatch) -> None:
    _, _, _, database, output, _ = _bootstrap_fixture(tmp_path, monkeypatch)
    receipt_path, bank_path, report_path = _paths(output)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    _corrupt_assigned_item(database, receipt["session_id"])

    safe = recovery.recover(
        database_path=database,
        bootstrap_receipt_path=receipt_path,
        bank_path=bank_path,
        supply_report_path=report_path,
        output_root=tmp_path / ".local/recovery",
        actor_id="operator-test",
        occurred_at="2026-07-19T06:00:00Z",
    )
    assert safe["validation_status"] == recovery.STATUS
    assert safe["defect_count"] == 1
    assert safe["invalidated_attempt_count"] == 0
    assert safe["new_session_state"] == "ABANDONED"

    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    with sqlite3.connect(database) as connection:
        state = connection.execute(
            "SELECT session_state FROM edge_sessions WHERE session_id=?", (receipt["session_id"],)
        ).fetchone()[0]
        metadata = dict(connection.execute("SELECT key,value FROM r5_metadata"))
    assert state == "ABANDONED"
    assert metadata["source_bank_sha256"] == bank["bank_sha256"]
    assert (tmp_path / ".local/recovery/a1fs_v1_r5_pre_content_error_recovery.sqlite3").is_file()


def test_recovery_invalidates_existing_attempt_without_rewriting_it(tmp_path: Path, monkeypatch) -> None:
    _, _, _, database, output, _ = _bootstrap_fixture(tmp_path, monkeypatch)
    receipt_path, bank_path, report_path = _paths(output)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    runtime = r5.LocalEdgeRuntime(database)
    payload = runtime.session_payload(
        session_id=receipt["session_id"], access_token=receipt["access_token"]
    )
    item_id = payload["assignments"][0]["item"]["item_id"]
    with sqlite3.connect(database) as connection:
        item = json.loads(connection.execute(
            "SELECT item_json FROM edge_runtime_items WHERE item_id=?", (item_id,)
        ).fetchone()[0])
        scoring = item["private_scoring_contract"]
        scoring.setdefault("case_insensitive", True)
        scoring.setdefault("punctuation_tolerance", True)
        connection.execute(
            "UPDATE edge_runtime_items SET item_json=?,item_digest=? WHERE item_id=?",
            (r5.canonical(item), r5.digest(item), item_id),
        )
        connection.commit()
    answer = item["private_scoring_contract"]["accepted_texts"][0]
    result = runtime.submit_response(
        session_id=receipt["session_id"],
        access_token=receipt["access_token"],
        item_id=item_id,
        response=answer,
        response_time_ms=1000,
        hint_count=0,
        revision_count=0,
        expected_session_version=1,
        submitted_at="2026-07-19T05:59:00Z",
    )
    attempt_id = result["attempt_id"]
    with sqlite3.connect(database) as connection:
        before_hash = connection.execute(
            "SELECT attempt_hash FROM edge_attempts WHERE attempt_id=?", (attempt_id,)
        ).fetchone()[0]
    _corrupt_assigned_item(database, receipt["session_id"])

    safe = recovery.recover(
        database_path=database,
        bootstrap_receipt_path=receipt_path,
        bank_path=bank_path,
        supply_report_path=report_path,
        output_root=tmp_path / ".local/recovery",
        actor_id="operator-test",
        occurred_at="2026-07-19T06:00:00Z",
    )
    assert safe["invalidated_attempt_count"] == 1
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT attempt_hash,validity_status FROM edge_attempts WHERE attempt_id=?", (attempt_id,)
        ).fetchone()
        event = connection.execute(
            "SELECT new_status,reason_code FROM edge_validity_events WHERE attempt_id=?", (attempt_id,)
        ).fetchone()
    assert row == (before_hash, "INVALIDATED_CONTENT_ERROR")
    assert event == ("INVALIDATED_CONTENT_ERROR", recovery.DEFAULT_REASON_CODE)


def test_recovery_refuses_session_without_proven_defect(tmp_path: Path, monkeypatch) -> None:
    _, _, _, database, output, _ = _bootstrap_fixture(tmp_path, monkeypatch)
    receipt_path, bank_path, report_path = _paths(output)
    with pytest.raises(recovery.ContentErrorRecoveryError, match="session_has_no_proven_answerability_defect"):
        recovery.recover(
            database_path=database,
            bootstrap_receipt_path=receipt_path,
            bank_path=bank_path,
            supply_report_path=report_path,
            output_root=tmp_path / ".local/recovery",
            actor_id="operator-test",
        )


def test_future_selection_ignores_historical_item_outside_current_supply(tmp_path: Path, monkeypatch) -> None:
    _, _, _, database, output, _ = _bootstrap_fixture(tmp_path, monkeypatch)
    receipt_path, _, _ = _paths(output)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    runtime = r5.LocalEdgeRuntime(database)
    runtime.abandon_session(
        session_id=receipt["session_id"],
        access_token=receipt["access_token"],
        expected_session_version=1,
        at="2026-07-19T06:00:00Z",
    )
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        source = connection.execute("SELECT * FROM edge_runtime_items ORDER BY item_id LIMIT 1").fetchone()
        item = json.loads(source["item_json"])
        item["item_id"] = "AAA_OBSOLETE_HISTORICAL_ITEM"
        connection.execute(
            """INSERT INTO edge_runtime_items
            (item_id,breadth_cell_id,capability_id,life_task_id,domain,level,skill,purpose,
             stimulus_fingerprint,template_family,item_json,item_digest,admission_status,media_payload_state)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item["item_id"], source["breadth_cell_id"], source["capability_id"],
                source["life_task_id"], source["domain"], source["level"], source["skill"],
                source["purpose"], "a" * 64, source["template_family"], r5.canonical(item),
                r5.digest(item), "APPROVED", source["media_payload_state"],
            ),
        )
        connection.commit()
    m3.LearnerStateStore(database).create_profile(
        learner_id="learner-anonymous-02",
        display_label="A1 Learner 2",
        at="2026-07-19T06:00:00Z",
    )
    new_session = runtime.start_session(
        learner_id="learner-anonymous-02",
        breadth_cell_id=receipt["selected_cell"]["breadth_cell_id"],
        purpose=receipt["selected_cell"]["purpose"],
        planned_item_count=1,
        started_at="2026-07-19T06:01:00Z",
    )
    assert new_session["assignments"][0]["item"]["item_id"] != "AAA_OBSOLETE_HISTORICAL_ITEM"
