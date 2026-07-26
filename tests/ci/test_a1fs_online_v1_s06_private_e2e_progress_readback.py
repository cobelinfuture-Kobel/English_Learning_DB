from __future__ import annotations

import importlib.util
import json
import threading
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.builders import build_a1fs_online_v1_s06_private_e2e_progress_readback as s06
from ulga.validators.validate_a1fs_online_v1_s06_private_e2e_progress_readback import validate_outputs


def _s05_fixture_module():
    path = Path(__file__).with_name("test_a1fs_online_v1_s05_private_identity_progress_persistence.py")
    spec = importlib.util.spec_from_file_location("_a1fs_s05_test_fixture", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _s05_receipt(tmp_path: Path) -> tuple[Path, dict]:
    module = _s05_fixture_module()
    _, root, receipt, _ = module._materialized(tmp_path)
    path = root / "private_learner_identity_progress_persistence.private.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, receipt


def _materialized(tmp_path: Path) -> tuple[Path, Path, dict, dict]:
    source, _ = _s05_receipt(tmp_path)
    root = tmp_path / "s06"
    receipt, safe = s06.materialize(s05_receipt_path=source, output_root=root)
    report = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=root,
        s05_receipt_path=source,
    )
    assert report["error_count"] == 0, report["errors"]
    return source, root, receipt, safe


def _production_app(s05_receipt: dict) -> s05.PersistentWorkbenchApplication:
    outputs = s05_receipt["persistent_outputs"]
    return s05.PersistentWorkbenchApplication(
        database_path=Path(outputs["database_path"]),
        bundles=s04._load_bundles(Path(outputs["ui_root"])),
    )


def test_materializes_and_validates_e2e_progress_readback(tmp_path: Path) -> None:
    _, _, receipt, safe = _materialized(tmp_path)
    assert receipt["end_to_end_summary"] == {
        "session_count": 1,
        "completed_session_count": 1,
        "exposure_count": 2,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "restart_readback_count": 1,
        "restart_readback_digest_stable": True,
        "production_database_unchanged": True,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
        "audio_runtime_asset_count": 0,
    }
    assert receipt["product_status"] == s06.PRODUCT_STATUS
    assert safe["validation_status"] == s06.PASS_STATUS


def test_canary_trace_has_pass_fail_and_no_production_mutation(tmp_path: Path) -> None:
    _, _, receipt, _ = _materialized(tmp_path)
    outputs = receipt["runtime_outputs"]
    trace = json.loads(Path(outputs["session_trace_path"]).read_text(encoding="utf-8"))
    assert [row["outcome"] for row in trace["steps"]] == ["AUTO_PASS", "AUTO_FAIL"]
    assert trace["production_database_sha256_before"] == trace["production_database_sha256_after"]
    assert trace["before_readback_sha256"] != trace["after_readback_sha256"]
    assert s06.file_digest(Path(outputs["database_path"])) == trace["production_database_sha256_after"]


def test_live_progress_endpoint_reads_existing_s05_progress(tmp_path: Path) -> None:
    source, s05_receipt = _s05_receipt(tmp_path)
    fixture = _s05_fixture_module()
    before_app = _production_app(s05_receipt)
    snapshot = fixture._complete_one_reading_attempt(before_app)
    assert snapshot["summary"]["session_count"] == 1

    root = tmp_path / "s06"
    receipt, safe = s06.materialize(s05_receipt_path=source, output_root=root)
    report = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=root,
        s05_receipt_path=source,
    )
    assert report["error_count"] == 0, report["errors"]

    outputs = receipt["runtime_outputs"]
    app = s06.ProgressReadbackApplication(
        database_path=Path(outputs["database_path"]),
        bundles=s04._load_bundles(Path(outputs["ui_root"])),
    )
    server = s06.ProgressReadbackServer(("127.0.0.1", 0), app, Path(outputs["static_root"]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        progress = s04._request(int(server.server_address[1]), "GET", "/api/progress")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert progress["summary"]["session_count"] == 1
    assert progress["summary"]["completed_session_count"] == 1
    assert progress["summary"]["exposure_count"] == 1
    assert progress["summary"]["attempt_count"] == 1
    assert progress["summary"]["auto_fail_count"] == 1
    assert "learner_id" not in json.dumps(progress, ensure_ascii=False)


def test_static_workbench_contains_progress_panel_without_unsafe_dom(tmp_path: Path) -> None:
    _, _, receipt, _ = _materialized(tmp_path)
    static_root = Path(receipt["runtime_outputs"]["static_root"])
    index = (static_root / "index.html").read_text(encoding="utf-8")
    script = (static_root / "app.js").read_text(encoding="utf-8")
    assert "refresh-progress" in index
    assert 'id="progress"' in index
    assert "/api/progress" in script
    assert "loadProgress" in script
    assert "innerHTML" not in script
    assert "eval(" not in script


def test_safe_readback_excludes_identity_content_and_paths(tmp_path: Path) -> None:
    _, _, _, safe = _materialized(tmp_path)
    rendered = json.dumps(safe, ensure_ascii=False)
    for token in (
        s05.DEFAULT_LEARNER_ID,
        s06.CANARY_LEARNER_ID,
        "learner_id",
        "display_label",
        "database_path",
        "session_id",
        "asset_key",
        "accepted_texts",
        "learner_payload",
        "answer_contract",
    ):
        assert token not in rendered


def test_non_loopback_progress_server_is_forbidden(tmp_path: Path) -> None:
    _, _, receipt, _ = _materialized(tmp_path)
    outputs = receipt["runtime_outputs"]
    app = s06.ProgressReadbackApplication(
        database_path=Path(outputs["database_path"]),
        bundles=s04._load_bundles(Path(outputs["ui_root"])),
    )
    with pytest.raises(s06.ReadbackError, match="non_loopback_host_forbidden"):
        s06.ProgressReadbackServer(("0.0.0.0", 0), app, Path(outputs["static_root"]))
