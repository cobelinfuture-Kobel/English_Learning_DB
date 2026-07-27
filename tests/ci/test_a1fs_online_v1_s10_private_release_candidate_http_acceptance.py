from __future__ import annotations

from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s10_private_release_candidate_http_acceptance as s10


def _bootstrap() -> dict:
    units = []
    for sequence_index in range(1, 25):
        grammar_id = f"GRAMMAR_UNIT_{sequence_index:02d}"
        units.append({
            "grammar_unit_id": grammar_id,
            "sequence_index": sequence_index,
            "lanes": [
                {
                    "skill": "READING",
                    "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:READING",
                    "asset_count": 4,
                    "assets": [],
                },
                {
                    "skill": "WRITING",
                    "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:WRITING",
                    "asset_count": 4,
                    "assets": [],
                },
                {
                    "skill": "SPEAKING",
                    "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:SPEAKING",
                    "asset_count": 3,
                    "assets": [],
                },
            ],
        })
    return {
        "task_id": s10.s09.TASK_ID,
        "validation_status": s10.s09.PASS_STATUS,
        "product_status": s10.s09.PRODUCT_STATUS,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "unit_count": 24,
        "units": units,
    }


def _progress() -> dict:
    return {
        "summary": {
            "session_count": 3,
            "completed_session_count": 2,
            "active_session_count": 0,
            "abandoned_session_count": 1,
            "exposure_count": 3,
            "attempt_count": 2,
            "auto_pass_count": 1,
            "auto_fail_count": 1,
            "pending_human_review_count": 0,
            "unit_count_with_sessions": 2,
            "skill_count_with_sessions": 3,
        },
        "last_event_hash_present": True,
    }


class _FakeApp:
    def bootstrap(self) -> dict:
        return _bootstrap()


def _write_static(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(
        "<h1>A1FS 多單元學習旅程工作台</h1>", encoding="utf-8"
    )
    (root / "app.js").write_text("const navigationLocked = () => false;", encoding="utf-8")
    (root / "styles.css").write_text("body{}", encoding="utf-8")


def test_s10_validates_complete_twentyfour_unit_bootstrap() -> None:
    assert s10._validate_bootstrap(_bootstrap()) == {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
    }


def test_s10_bootstrap_rejects_missing_last_unit() -> None:
    bootstrap = _bootstrap()
    bootstrap["units"].pop()
    with pytest.raises(s10.ReleaseCandidateError, match="http_bootstrap_unit_count_invalid"):
        s10._validate_bootstrap(bootstrap)


def test_s10_validates_exact_http_progress_contract() -> None:
    counts = s10._validate_progress(_progress())
    assert counts["session_count"] == 3
    assert counts["completed_session_count"] == 2
    assert counts["abandoned_session_count"] == 1
    assert counts["attempt_count"] == 2


def test_s10_progress_rejects_active_session_leak() -> None:
    progress = _progress()
    progress["summary"]["active_session_count"] = 1
    with pytest.raises(
        s10.ReleaseCandidateError,
        match="http_progress_count_invalid:active_session_count:1:0",
    ):
        s10._validate_progress(progress)


def test_s10_real_loopback_http_serves_health_bootstrap_and_static(tmp_path) -> None:
    static_root = tmp_path / "static"
    _write_static(static_root)
    server, thread, port = s10._start_server(_FakeApp(), static_root)
    try:
        assert s10._http(port, "GET", "/api/health") == {
            "status": "PASS",
            "loopback_only": True,
            "audio_enabled": False,
        }
        assert s10._http(port, "GET", "/api/bootstrap")["unit_count"] == 24
        assert "A1FS 多單元學習旅程工作台" in s10._http(
            port, "GET", "/index.html", expect_json=False
        )
        assert "navigationLocked" in s10._http(
            port, "GET", "/app.js", expect_json=False
        )
    finally:
        s10._stop_server(server, thread)


def test_s10_non_loopback_binding_remains_fail_closed(tmp_path) -> None:
    static_root = tmp_path / "static"
    _write_static(static_root)
    with pytest.raises(
        s10.s09.s08.JourneyQAError,
        match="non_loopback_host_forbidden:0.0.0.0",
    ):
        s10.s09.s08.JourneyWorkbenchServer(("0.0.0.0", 0), _FakeApp(), static_root)


def test_s10_safe_scan_rejects_private_learner_payload() -> None:
    with pytest.raises(s10.ReleaseCandidateError, match="private_content_leak:learner_id"):
        s10.safe_scan({"release_candidate_summary": {"learner_id": "forbidden"}})
