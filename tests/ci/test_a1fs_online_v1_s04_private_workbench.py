from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime as s03
from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04
from ulga.validators.validate_a1fs_online_v1_s04_private_online_learner_workbench_execution import validate_outputs


def _s03_sources() -> tuple[dict, dict]:
    path = Path(__file__).with_name("test_a1fs_online_v1_s03_unified_runtime.py")
    spec = importlib.util.spec_from_file_location("_a1fs_s03_test_fixture", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.sources()


def _s03_receipt(tmp_path: Path) -> Path:
    admitted, shared = _s03_sources()
    root = tmp_path / "s03"
    receipt, _ = s03.materialize_runtime(
        s02_artifact=admitted,
        m03_artifact=shared,
        output_root=root,
    )
    path = root / "unified_learner_runtime.private.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_materializes_and_validates_private_loopback_workbench(tmp_path: Path) -> None:
    source = _s03_receipt(tmp_path)
    output_root = tmp_path / "s04"
    receipt, safe = s04.materialize(s03_receipt_path=source, output_root=output_root)
    report = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=output_root,
        s03_receipt_path=source,
    )
    assert report["error_count"] == 0, report["errors"]
    assert receipt["execution_summary"] == {
        "lane_count": 3,
        "learner_visible_asset_count": 11,
        "http_loopback_canary_count": 1,
        "synthetic_response_attempt_count": 1,
        "synthetic_scoring_result_count": 1,
        "synthetic_auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_item_count": 0,
        "audio_runtime_asset_count": 0,
    }
    assert receipt["http_canary"]["attempt_outcome"] == "AUTO_FAIL"
    assert receipt["http_canary"]["session_state"] == "COMPLETED"
    assert receipt["product_status"] == "PRIVATE_LOCALHOST_WORKBENCH_EXECUTABLE_NOT_PUBLIC"


def test_bootstrap_is_learner_safe_and_speaking_is_display_only(tmp_path: Path) -> None:
    source = _s03_receipt(tmp_path)
    output_root = tmp_path / "s04"
    receipt, _ = s04.materialize(s03_receipt_path=source, output_root=output_root)
    outputs = receipt["workbench_outputs"]
    bundles = s04._load_bundles(Path(outputs["ui_root"]))
    app = s04.WorkbenchApplication(
        database_path=Path(outputs["database_path"]),
        bundles=bundles,
    )
    bootstrap = app.bootstrap()
    rendered = json.dumps(bootstrap, ensure_ascii=False)
    for token in (
        "answer_contract", "private_scoring_contract", "accepted_texts",
        "accepted_sequence", "This is answer",
    ):
        assert token not in rendered
    speaking = next(lane for lane in bootstrap["lanes"] if lane["skill"] == "SPEAKING")
    assert speaking["asset_count"] == 3
    assert all(asset["learner_payload"]["response_capture_enabled"] is False for asset in speaking["assets"])
    assert bootstrap["audio_enabled"] is False
    assert bootstrap["speaking_capture_enabled"] is False


def test_non_loopback_binding_is_forbidden(tmp_path: Path) -> None:
    source = _s03_receipt(tmp_path)
    output_root = tmp_path / "s04"
    receipt, _ = s04.materialize(s03_receipt_path=source, output_root=output_root)
    outputs = receipt["workbench_outputs"]
    app = s04.WorkbenchApplication(
        database_path=Path(outputs["database_path"]),
        bundles=s04._load_bundles(Path(outputs["ui_root"])),
    )
    with pytest.raises(s04.WorkbenchError, match="non_loopback_host_forbidden"):
        s04.WorkbenchServer(("0.0.0.0", 0), app, Path(outputs["static_root"]))


def test_speaking_response_submission_fails_closed(tmp_path: Path) -> None:
    source = _s03_receipt(tmp_path)
    output_root = tmp_path / "s04"
    receipt, _ = s04.materialize(s03_receipt_path=source, output_root=output_root)
    outputs = receipt["workbench_outputs"]
    app = s04.WorkbenchApplication(
        database_path=Path(outputs["database_path"]),
        bundles=s04._load_bundles(Path(outputs["ui_root"])),
    )
    profile = app.state_store.profile_snapshot(s04.CANARY_LEARNER_ID)
    assert profile["claim_boundaries"]["mastery_recorded"] is False
    session = app.start_session({
        "skill": "speaking",
        "learner_id": s04.CANARY_LEARNER_ID,
        "session_id": "A1FS_ONLINE_V1_S04_SESSION:SPEAKING_TEST",
        "at": "2026-01-02T01:00:00Z",
    })
    asset_key = app.bundles["speaking"]["assets"][0]["asset_key"]
    session = app.record_exposure({
        "session_id": session["session_id"],
        "asset_key": asset_key,
        "expected_session_version": session["session_version"],
        "at": "2026-01-02T01:00:10Z",
    })
    with pytest.raises(Exception, match="response_capture_not_enabled_for_asset"):
        app.submit_response({
            "learner_id": s04.CANARY_LEARNER_ID,
            "session_id": session["session_id"],
            "asset_key": asset_key,
            "response": "synthetic speech text",
            "expected_session_version": session["session_version"],
            "attempt_id": "A1FS_ONLINE_V1_S04_ATTEMPT:SPEAKING_TEST",
            "submitted_at": "2026-01-02T01:00:20Z",
        })


def test_safe_readback_is_deterministic(tmp_path: Path) -> None:
    source = _s03_receipt(tmp_path)
    output_root = tmp_path / "s04"
    receipt1, safe1 = s04.materialize(s03_receipt_path=source, output_root=output_root)
    receipt2, safe2 = s04.materialize(s03_receipt_path=source, output_root=output_root)
    assert safe1 == safe2
    assert receipt1["artifact_sha256"] == receipt2["artifact_sha256"]
    rendered = json.dumps(safe1, ensure_ascii=False)
    assert "accepted_texts" not in rendered
    assert "learner_payload" not in rendered
