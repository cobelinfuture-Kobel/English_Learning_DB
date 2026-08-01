from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as acceptance,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_windows_chromium_render_fullfix as fullfix,
)


def _payload(prefix: bytes) -> bytes:
    return prefix + (b"x" * 2048)


def test_windows_fullfix_prefers_smoke_proven_minimal_edge_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source.html"
    source.write_text("<html><body>ok</body></html>", encoding="utf-8")
    target = tmp_path / "expected.pdf"
    calls: list[tuple[list[str], object]] = []

    def fake_run(command, **kwargs):
        calls.append((list(command), kwargs.get("cwd")))
        target.write_bytes(_payload(b"%PDF"))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fullfix, "PREFER_MINIMAL_WINDOWS_COMMAND", True)
    monkeypatch.setattr(fullfix.subprocess, "run", fake_run)
    monkeypatch.setattr(fullfix, "OUTPUT_WAIT_SECONDS", 0.01)
    monkeypatch.setattr(fullfix, "OUTPUT_POLL_SECONDS", 0.001)

    result = fullfix._run_browser_windows_safe(
        tmp_path / "msedge.exe",
        source_html=source,
        output_path=target,
        mode="PDF",
    )

    assert len(calls) == 1
    command, cwd = calls[0]
    assert cwd is None
    assert "--headless=new" in command
    assert "--disable-gpu" in command
    assert "--no-first-run" in command
    assert "--no-default-browser-check" in command
    assert not any(value.startswith("--user-data-dir=") for value in command)
    assert "--no-sandbox" not in command
    assert "--print-to-pdf-no-header" not in command
    assert "--no-pdf-header-footer" not in command
    assert f"--print-to-pdf={target.resolve()}" in command
    assert result["attempt_mode"] == "minimal_windows"
    assert result["headless_mode"] == "--headless=new"
    assert result["render_attempt_count"] == 1
    assert target.read_bytes().startswith(b"%PDF")


def test_windows_fullfix_promotes_default_pdf_when_target_path_is_ignored(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source.html"
    source.write_text("<html><body>ok</body></html>", encoding="utf-8")
    target = tmp_path / "expected.pdf"

    def fake_run(command, **kwargs):
        assert "--headless=new" in command
        default_output = Path(kwargs["cwd"]) / "output.pdf"
        default_output.write_bytes(_payload(b"%PDF"))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fullfix, "PREFER_MINIMAL_WINDOWS_COMMAND", False)
    monkeypatch.setattr(fullfix.subprocess, "run", fake_run)
    monkeypatch.setattr(fullfix, "OUTPUT_WAIT_SECONDS", 0.01)
    monkeypatch.setattr(fullfix, "OUTPUT_POLL_SECONDS", 0.001)

    result = fullfix._run_browser_windows_safe(
        tmp_path / "chrome.exe",
        source_html=source,
        output_path=target,
        mode="PDF",
    )

    assert target.read_bytes().startswith(b"%PDF")
    assert result["attempt_mode"] == "isolated_profile"
    assert result["headless_mode"] == "--headless=new"
    assert result["render_attempt_count"] == 1
    assert result["fallback_output_promoted"] is True
    assert result["bytes"] >= fullfix.MIN_OUTPUT_BYTES


def test_windows_fullfix_falls_back_to_legacy_headless(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source.html"
    source.write_text("<html><body>ok</body></html>", encoding="utf-8")
    target = tmp_path / "expected.png"
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        if "--headless" in command and "--headless=new" not in command:
            target.write_bytes(_payload(b"\x89PNG\r\n\x1a\n"))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fullfix, "PREFER_MINIMAL_WINDOWS_COMMAND", False)
    monkeypatch.setattr(fullfix.subprocess, "run", fake_run)
    monkeypatch.setattr(fullfix, "OUTPUT_WAIT_SECONDS", 0.01)
    monkeypatch.setattr(fullfix, "OUTPUT_POLL_SECONDS", 0.001)

    result = fullfix._run_browser_windows_safe(
        tmp_path / "msedge.exe",
        source_html=source,
        output_path=target,
        mode="PNG",
    )

    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(calls) == 2
    assert result["attempt_mode"] == "isolated_profile"
    assert result["headless_mode"] == "--headless"
    assert result["render_attempt_count"] == 2
    assert result["fallback_output_promoted"] is False


def test_windows_fullfix_minimal_failure_falls_back_to_isolated_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source.html"
    source.write_text("<html><body>ok</body></html>", encoding="utf-8")
    target = tmp_path / "expected.pdf"
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        if any(value.startswith("--user-data-dir=") for value in command):
            target.write_bytes(_payload(b"%PDF"))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fullfix, "PREFER_MINIMAL_WINDOWS_COMMAND", True)
    monkeypatch.setattr(fullfix.subprocess, "run", fake_run)
    monkeypatch.setattr(fullfix, "OUTPUT_WAIT_SECONDS", 0.005)
    monkeypatch.setattr(fullfix, "OUTPUT_POLL_SECONDS", 0.001)

    result = fullfix._run_browser_windows_safe(
        tmp_path / "msedge.exe",
        source_html=source,
        output_path=target,
        mode="PDF",
    )

    assert len(calls) == 2
    assert not any(value.startswith("--user-data-dir=") for value in calls[0])
    assert any(value.startswith("--user-data-dir=") for value in calls[1])
    assert result["attempt_mode"] == "isolated_profile"
    assert result["render_attempt_count"] == 2


def test_windows_fullfix_reports_all_failed_attempts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source.html"
    source.write_text("<html><body>ok</body></html>", encoding="utf-8")

    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="no output", stderr="")

    monkeypatch.setattr(fullfix, "PREFER_MINIMAL_WINDOWS_COMMAND", True)
    monkeypatch.setattr(fullfix.subprocess, "run", fake_run)
    monkeypatch.setattr(fullfix, "OUTPUT_WAIT_SECONDS", 0.005)
    monkeypatch.setattr(fullfix, "OUTPUT_POLL_SECONDS", 0.001)

    try:
        fullfix._run_browser_windows_safe(
            tmp_path / "chrome.exe",
            source_html=source,
            output_path=tmp_path / "missing.pdf",
            mode="PDF",
        )
    except acceptance.StudentEntryAcceptanceError as exc:
        message = str(exc)
        assert "chromium_render_failed:PDF" in message
        assert '"attempt_mode": "minimal_windows"' in message
        assert '"attempt_mode": "isolated_profile"' in message
        assert '"headless_mode": "--headless=new"' in message
        assert '"headless_mode": "--headless"' in message
        assert '"return_code": 0' in message
        assert '"target_output_ready": false' in message
    else:
        raise AssertionError("missing Chromium output did not fail closed")


def test_install_fullfix_patches_only_the_process_boundary(monkeypatch) -> None:
    original = acceptance._run_browser
    try:
        previous = fullfix.install_fullfix()
        assert previous is original
        assert acceptance._run_browser is fullfix._run_browser_windows_safe
    finally:
        monkeypatch.setattr(acceptance, "_run_browser", original)
