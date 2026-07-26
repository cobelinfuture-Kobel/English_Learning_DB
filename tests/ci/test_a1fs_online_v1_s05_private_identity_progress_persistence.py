from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.validators.validate_a1fs_online_v1_s05_private_learner_identity_progress_persistence import validate_outputs


def _s04_receipt(tmp_path: Path) -> Path:
    fixture_path = Path(__file__).with_name("test_a1fs_online_v1_s04_private_workbench.py")
    spec = importlib.util.spec_from_file_location("_a1fs_s04_test_fixture", fixture_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = module._s03_receipt(tmp_path)
    root = tmp_path / "s04"
    receipt, _ = s04.materialize(s03_receipt_path=source, output_root=root)
    path = root / "private_online_workbench_execution.private.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _materialized(tmp_path: Path) -> tuple[Path, Path, dict, dict]:
    source = _s04_receipt(tmp_path)
    root = tmp_path / "s05"
    receipt, safe = s05.materialize(s04_receipt_path=source, output_root=root)
    report = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=root,
        s04_receipt_path=source,
    )
    assert report["error_count"] == 0, report["errors"]
    return source, root, receipt, safe


def _app(receipt: dict) -> s05.PersistentWorkbenchApplication:
    outputs = receipt["persistent_outputs"]
    return s05.PersistentWorkbenchApplication(
        database_path=Path(outputs["database_path"]),
        bundles=s04._load_bundles(Path(outputs["ui_root"])),
    )


def _complete_one_reading_attempt(app: s05.PersistentWorkbenchApplication) -> dict:
    asset_key, wrong_response = s04._select_canary_response(
        app.database_path,
        app.bundles["reading"]["assets"],
    )
    session = app.start_session({
        "skill": "reading",
        "learner_id": s05.DEFAULT_LEARNER_ID,
        "session_id": "A1FS_ONLINE_V1_S05_PERSISTENCE_TEST_SESSION",
        "at": "2026-01-05T00:00:00Z",
    })
    session = app.record_exposure({
        "session_id": session["session_id"],
        "asset_key": asset_key,
        "expected_session_version": session["session_version"],
        "at": "2026-01-05T00:00:10Z",
    })
    result = app.submit_response({
        "learner_id": s05.DEFAULT_LEARNER_ID,
        "session_id": session["session_id"],
        "asset_key": asset_key,
        "response": wrong_response,
        "expected_session_version": session["session_version"],
        "attempt_id": "A1FS_ONLINE_V1_S05_PERSISTENCE_TEST_ATTEMPT",
        "submitted_at": "2026-01-05T00:00:20Z",
    })
    completed = app.complete_session({
        "session_id": session["session_id"],
        "expected_session_version": result["session_version"],
        "at": "2026-01-05T00:00:30Z",
    })
    assert result["outcome"] == "AUTO_FAIL"
    assert completed["session_state"] == "COMPLETED"
    return app.progress_snapshot(s05.DEFAULT_LEARNER_ID)


def test_materializes_and_validates_private_identity_progress_store(tmp_path: Path) -> None:
    _, _, receipt, safe = _materialized(tmp_path)
    assert receipt["identity_summary"]["stable_identity_count"] == 1
    assert receipt["identity_summary"]["default_private_slot_ready"] is True
    assert receipt["progress_summary"] == {
        "persistent_session_count": 0,
        "persistent_completed_session_count": 0,
        "persistent_exposure_count": 0,
        "persistent_attempt_count": 0,
        "checkpoint_count": 0,
    }
    assert receipt["restart_canary"]["snapshot_digest_stable"] is True
    assert receipt["restart_canary"]["persisted_attempt_count"] == 1
    assert receipt["product_status"] == s05.PRODUCT_STATUS
    assert safe["validation_status"] == s05.PASS_STATUS


def test_second_materialization_preserves_identity_progress_and_generation(tmp_path: Path) -> None:
    source, root, receipt1, _ = _materialized(tmp_path)
    generation1 = receipt1["identity_summary"]["database_generation_id"]
    snapshot1 = _complete_one_reading_attempt(_app(receipt1))
    assert snapshot1["summary"]["session_count"] == 1
    assert snapshot1["summary"]["exposure_count"] == 1
    assert snapshot1["summary"]["attempt_count"] == 1

    receipt2, safe2 = s05.materialize(s04_receipt_path=source, output_root=root)
    generation2 = receipt2["identity_summary"]["database_generation_id"]
    snapshot2 = _app(receipt2).progress_snapshot(s05.DEFAULT_LEARNER_ID)
    assert generation2 == generation1
    assert snapshot2["snapshot_sha256"] == snapshot1["snapshot_sha256"]
    assert receipt2["progress_summary"] == {
        "persistent_session_count": 1,
        "persistent_completed_session_count": 1,
        "persistent_exposure_count": 1,
        "persistent_attempt_count": 1,
        "checkpoint_count": 1,
    }
    report = validate_outputs(
        receipt=receipt2,
        safe_report=safe2,
        output_root=root,
        s04_receipt_path=source,
    )
    assert report["error_count"] == 0, report["errors"]


def test_private_subject_binding_is_stable_and_conflicts_fail_closed(tmp_path: Path) -> None:
    _, _, receipt, _ = _materialized(tmp_path)
    app = _app(receipt)
    first = app.enroll(
        learner_id="A1FS_PRIVATE_LEARNER_002",
        display_label="Learner 2",
        subject_key="PRIVATE_SLOT:2",
        at="2026-01-06T00:00:00Z",
    )
    second = app.enroll(
        learner_id="A1FS_PRIVATE_LEARNER_002",
        display_label="Learner 2",
        subject_key="PRIVATE_SLOT:2",
        at="2026-01-06T00:00:00Z",
    )
    assert first["identity_reused"] is False
    assert second["identity_reused"] is True
    with pytest.raises(s05.PersistenceError, match="private_subject_already_bound_to_other_learner"):
        app.enroll(
            learner_id="A1FS_PRIVATE_LEARNER_003",
            display_label="Learner 3",
            subject_key="PRIVATE_SLOT:2",
        )


def test_source_binding_tamper_does_not_reset_persistent_database(tmp_path: Path) -> None:
    source, root, receipt, _ = _materialized(tmp_path)
    database = Path(receipt["persistent_outputs"]["database_path"])
    generation = receipt["identity_summary"]["database_generation_id"]
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE s05_persistence_metadata SET value=? WHERE key='source_s04_sha256'",
            ("0" * 64,),
        )
        connection.commit()
    with pytest.raises(s05.PersistenceError, match="persistent_database_source_binding_mismatch"):
        s05.materialize(s04_receipt_path=source, output_root=root)
    with sqlite3.connect(database) as connection:
        current_generation = connection.execute(
            "SELECT value FROM s05_persistence_metadata WHERE key='database_generation_id'"
        ).fetchone()[0]
    assert current_generation == generation


def test_safe_readback_excludes_private_identity_and_content(tmp_path: Path) -> None:
    _, _, _, safe = _materialized(tmp_path)
    rendered = json.dumps(safe, ensure_ascii=False)
    for token in (
        s05.DEFAULT_LEARNER_ID,
        s05.DEFAULT_DISPLAY_LABEL,
        "learner_id",
        "display_label",
        "private_subject_digest",
        "learner_payload",
        "accepted_texts",
        "answer_contract",
    ):
        assert token not in rendered


def test_non_loopback_persistent_workbench_is_forbidden(tmp_path: Path) -> None:
    _, _, receipt, _ = _materialized(tmp_path)
    app = _app(receipt)
    static_root = Path(receipt["persistent_outputs"]["static_root"])
    with pytest.raises(s04.WorkbenchError, match="non_loopback_host_forbidden"):
        s04.WorkbenchServer(("0.0.0.0", 0), app, static_root)
