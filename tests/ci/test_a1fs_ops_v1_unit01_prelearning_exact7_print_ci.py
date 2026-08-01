from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as acceptance,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_windows_chromium_render_fullfix as fullfix,
)


def _pdf_payload() -> bytes:
    return b"%PDF" + (b"x" * 4096)


def test_exact_seven_page_print_css_is_prelearning_scoped(monkeypatch) -> None:
    original_css = student_builder.STUDENT_CSS
    try:
        fullfix.prelearning_v2.install_fullfix()
        marker = fullfix.install_exact_seven_page_print_layout()
        css = student_builder.STUDENT_CSS
        assert marker == fullfix.EXACT_SEVEN_PAGE_PRINT_MARKER
        assert fullfix.EXACT_SEVEN_PAGE_PRINT_MARKER in css
        assert "body:has(.prelearning-goal)" in css
        assert "@page{size:A4;margin:8mm}" in css
        assert "break-inside:avoid-page" in css
        assert "font-size:10.5px" in css
        assert fullfix.EXACT_PRELEARNING_PAGE_COUNT == 7
    finally:
        monkeypatch.setattr(student_builder, "STUDENT_CSS", original_css)


def test_prelearning_pdf_requires_exact_seven_pages(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "prelearning.html"
    source.write_text("<html><body>prelearning</body></html>", encoding="utf-8")
    target = tmp_path / "prelearning.pdf"
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        target.write_bytes(_pdf_payload())
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fullfix, "PREFER_MINIMAL_WINDOWS_COMMAND", True)
    monkeypatch.setattr(fullfix.subprocess, "run", fake_run)
    monkeypatch.setattr(fullfix, "OUTPUT_WAIT_SECONDS", 0.001)
    monkeypatch.setattr(fullfix, "OUTPUT_POLL_SECONDS", 0.001)
    monkeypatch.setattr(acceptance, "_pdf_page_count", lambda _path: 10)

    try:
        fullfix._run_browser_windows_safe(
            tmp_path / "msedge.exe",
            source_html=source,
            output_path=target,
            mode="PDF",
        )
    except acceptance.StudentEntryAcceptanceError as exc:
        message = str(exc)
        assert '"prelearning_pdf_page_count": 10' in message
        assert '"exact_prelearning_page_contract": false' in message
        assert len(calls) == 3
    else:
        raise AssertionError("ten-page Pre-Learning incorrectly passed exact-page gate")


def test_prelearning_pdf_accepts_exact_seven_pages(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "prelearning.html"
    source.write_text("<html><body>prelearning</body></html>", encoding="utf-8")
    target = tmp_path / "prelearning.pdf"

    def fake_run(command, **kwargs):
        target.write_bytes(_pdf_payload())
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fullfix, "PREFER_MINIMAL_WINDOWS_COMMAND", True)
    monkeypatch.setattr(fullfix.subprocess, "run", fake_run)
    monkeypatch.setattr(fullfix, "OUTPUT_WAIT_SECONDS", 0.001)
    monkeypatch.setattr(fullfix, "OUTPUT_POLL_SECONDS", 0.001)
    monkeypatch.setattr(acceptance, "_pdf_page_count", lambda _path: 7)

    result = fullfix._run_browser_windows_safe(
        tmp_path / "msedge.exe",
        source_html=source,
        output_path=target,
        mode="PDF",
    )
    assert result["prelearning_pdf_page_count"] == 7
    assert result["render_attempt_count"] == 1
