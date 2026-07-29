from __future__ import annotations

from pathlib import Path

import pytest

from ulga.builders import build_a1fs_ops_v1_upg01_runtime_shutdown_fullfix as fix


def _product(tmp_path: Path, pid: int = 3668) -> Path:
    root = tmp_path / "A1FS_V1"
    pid_path = root / "shared" / "a1fs_v1.pid"
    pid_path.parent.mkdir(parents=True)
    pid_path.write_text(str(pid) + "\n", encoding="ascii")
    return root


def test_extended_wait_accepts_delayed_windows_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _product(tmp_path)
    monkeypatch.setattr(fix, "_windows_creation_token", lambda _pid: 12345)
    monkeypatch.setattr(
        fix,
        "_BASE_STOP",
        lambda **_kwargs: (_ for _ in ()).throw(
            fix.core.r01.ProductRootError("PROCESS_STILL_RUNNING=3668")
        ),
    )
    monkeypatch.setattr(
        fix,
        "_wait_for_shutdown",
        lambda **_kwargs: {
            "process_identity_exited": True,
            "health_endpoint_closed": True,
            "port_closed": True,
            "poll_count": 7,
        },
    )

    result = fix.robust_stop(product_root=root, port=8765)

    assert result["status"] == "PASS_A1FS_V1_STOPPED_EXTENDED_VERIFIED"
    assert result["shutdown_mode"] == "EXTENDED_WAIT_AFTER_BASE_TASKKILL"
    assert result["process_creation_token_captured"] is True
    assert not (root / "shared/a1fs_v1.pid").exists()


def test_second_kill_is_used_after_extended_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _product(tmp_path)
    monkeypatch.setattr(fix, "_windows_creation_token", lambda _pid: None)
    monkeypatch.setattr(
        fix,
        "_BASE_STOP",
        lambda **_kwargs: (_ for _ in ()).throw(
            fix.core.r01.ProductRootError("PROCESS_STILL_RUNNING=3668")
        ),
    )
    waits = iter(
        [
            None,
            {
                "process_identity_exited": True,
                "health_endpoint_closed": True,
                "port_closed": True,
                "poll_count": 2,
            },
        ]
    )
    monkeypatch.setattr(fix, "_wait_for_shutdown", lambda **_kwargs: next(waits))
    monkeypatch.setattr(fix.os, "kill", lambda _pid, _signal: None)

    result = fix.robust_stop(product_root=root, port=8765)

    assert result["shutdown_mode"] == "SECOND_TASKKILL_AND_EXTENDED_WAIT"
    assert result["retry_taskkill"]["returncode"] == 0
    assert not (root / "shared/a1fs_v1.pid").exists()


def test_shutdown_timeout_fails_before_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _product(tmp_path)
    monkeypatch.setattr(fix, "_windows_creation_token", lambda _pid: None)
    monkeypatch.setattr(
        fix,
        "_BASE_STOP",
        lambda **_kwargs: (_ for _ in ()).throw(
            fix.core.r01.ProductRootError("PROCESS_STILL_RUNNING=3668")
        ),
    )
    monkeypatch.setattr(fix, "_wait_for_shutdown", lambda **_kwargs: None)
    monkeypatch.setattr(fix.os, "kill", lambda _pid, _signal: None)

    with pytest.raises(fix.RuntimeShutdownFullFixError, match="RUNTIME_SHUTDOWN_TIMEOUT"):
        fix.robust_stop(product_root=root, port=8765)

    assert (root / "shared/a1fs_v1.pid").is_file()


def test_non_process_stop_error_is_not_masked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _product(tmp_path)
    monkeypatch.setattr(fix, "_windows_creation_token", lambda _pid: None)
    monkeypatch.setattr(
        fix,
        "_BASE_STOP",
        lambda **_kwargs: (_ for _ in ()).throw(
            fix.core.r01.ProductRootError("PORT_STILL_LISTENING=8765")
        ),
    )

    with pytest.raises(fix.core.r01.ProductRootError, match="PORT_STILL_LISTENING"):
        fix.robust_stop(product_root=root, port=8765)


def test_activation_patches_only_existing_r01_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    original = fix.core.r01.stop
    monkeypatch.setattr(fix.core.r01, "stop", original)
    fix.activate()
    assert fix.core.r01.stop is fix.robust_stop


def test_operator_script_routes_through_shutdown_fullfix() -> None:
    repository = Path(__file__).resolve().parents[2]
    text = (repository / "scripts/UPGRADE_A1FS.ps1").read_text(encoding="utf-8")
    assert "build_a1fs_ops_v1_upg01_runtime_shutdown_fullfix" in text
    assert "G:\\HomeWork" not in text
    assert "C:\\Users" not in text
