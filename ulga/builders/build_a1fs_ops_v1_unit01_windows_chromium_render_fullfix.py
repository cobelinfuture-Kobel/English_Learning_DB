#!/usr/bin/env python3
"""Run Unit01 local-private materialization with approved Pre-Learning V2.

The accepted Unit01 authority and QuestionBank remain unchanged. This entry
installs the learner-facing seven-page Pre-Learning V2 projection, applies a
print-only compact layout contract so Chromium materializes exactly seven
Pre-Learning pages, and replaces only the Chromium process boundary. On Windows
it first uses the minimal headless command proven by the local Edge smoke test,
then falls back to isolated-profile compatibility modes. All attempts remain
bounded and fail closed.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_prelearning_v2_fullfix as prelearning_v2,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as acceptance,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_local_private_materialization_operator_readback
    as local_operator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Installs the approved learner-facing Unit01 Pre-Learning V2 projection, "
    "applies only a print-layout projection required to preserve the approved "
    "seven-page learner package, and adapts only the Windows Chromium process "
    "boundary. It creates no canonical learner content, question, answer, bank, "
    "planner, renderer authority, learner state, score, image asset, audio, A2 "
    "content, Unit02-24 artifact, production activation, or public delivery."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = "A1FS-OPS-V1_Unit01WindowsChromiumRenderFullFix"
PASS_STATUS = local_operator.PASS_STATUS
HEADLESS_MODES = ("--headless=new", "--headless")
OUTPUT_WAIT_SECONDS = 12.0
OUTPUT_POLL_SECONDS = 0.20
MIN_OUTPUT_BYTES = 1024
PREFER_MINIMAL_WINDOWS_COMMAND = os.name == "nt"
DEFAULT_OUTPUT_NAMES = {
    "PDF": "output.pdf",
    "PNG": "screenshot.png",
}
EXACT_PRELEARNING_PAGE_COUNT = prelearning_v2.EXPECTED_PRINT_PAGE_COUNT
EXACT_SEVEN_PAGE_PRINT_MARKER = "UNIT01_PRELEARNING_V2_EXACT_SEVEN_PAGE_PRINT"
EXACT_SEVEN_PAGE_PRINT_CSS = r"""
/* UNIT01_PRELEARNING_V2_EXACT_SEVEN_PAGE_PRINT */
@media print{
  @page{size:A4;margin:8mm}
  body:has(.prelearning-goal){font-size:10.5px;line-height:1.2}
  body:has(.prelearning-goal) .print-page{
    width:auto!important;
    min-height:0!important;
    margin:0!important;
    padding:0!important;
    box-shadow:none!important;
    break-after:page!important;
    page-break-after:always!important;
    break-inside:avoid-page!important;
    page-break-inside:avoid!important;
  }
  body:has(.prelearning-goal) .print-page:last-of-type{
    break-after:auto!important;
    page-break-after:auto!important;
  }
  body:has(.prelearning-goal) h1{font-size:21px;line-height:1.08;margin:0 0 5px}
  body:has(.prelearning-goal) h2{font-size:15px;line-height:1.1;margin:7px 0 4px}
  body:has(.prelearning-goal) h3{font-size:12.5px;line-height:1.1;margin:5px 0 3px}
  body:has(.prelearning-goal) p{margin:2px 0}
  body:has(.prelearning-goal) .routine-list{margin:4px 0 7px;padding-left:20px}
  body:has(.prelearning-goal) .routine-list li{margin:1px 0}
  body:has(.prelearning-goal) .grid2,
  body:has(.prelearning-goal) .grid3,
  body:has(.prelearning-goal) .context-grid,
  body:has(.prelearning-goal) .learner-frame-grid,
  body:has(.prelearning-goal) .support-grid,
  body:has(.prelearning-goal) .practice-grid,
  body:has(.prelearning-goal) .reference-grid{gap:5px}
  body:has(.prelearning-goal) .rule-card,
  body:has(.prelearning-goal) .phrase-card,
  body:has(.prelearning-goal) .category-card,
  body:has(.prelearning-goal) .learning-group,
  body:has(.prelearning-goal) .context-card,
  body:has(.prelearning-goal) .learner-frame,
  body:has(.prelearning-goal) .guided-check,
  body:has(.prelearning-goal) .writing-step,
  body:has(.prelearning-goal) .worked-example,
  body:has(.prelearning-goal) .degree-card,
  body:has(.prelearning-goal) .ready-check{padding:6px}
  body:has(.prelearning-goal) .learning-group{margin:5px 0}
  body:has(.prelearning-goal) .guided-check{margin:5px 0}
  body:has(.prelearning-goal) .degree-card{margin-top:7px}
  body:has(.prelearning-goal) .ready-check{margin-top:6px}
  body:has(.prelearning-goal) .callout,
  body:has(.prelearning-goal) .stimulus{padding:6px 8px;margin:6px 0}
  body:has(.prelearning-goal) .scope-note{padding:6px 8px}
  body:has(.prelearning-goal) .visual-card{grid-template-columns:30px 1fr auto;gap:5px}
  body:has(.prelearning-goal) .visual-cue{font-size:22px}
  body:has(.prelearning-goal) .phrase-card strong{font-size:14px}
  body:has(.prelearning-goal) .learner-frame .frame-model{font-size:14px}
  body:has(.prelearning-goal) .support-card{padding:6px 8px}
  body:has(.prelearning-goal) .checklist{gap:4px;margin-top:6px;padding-top:5px}
  body:has(.prelearning-goal) table{margin:4px 0}
  body:has(.prelearning-goal) th,
  body:has(.prelearning-goal) td{padding:2px 3px;line-height:1.12}
  body:has(.prelearning-goal) .compact-table{font-size:9.2px}
  body:has(.prelearning-goal) .answer-line{height:20px}
  body:has(.prelearning-goal) .teacher-system-note{font-size:9px}
}
"""


def install_exact_seven_page_print_layout() -> str:
    """Append a print-only V2 layout contract without altering QuestionBank data."""
    if EXACT_SEVEN_PAGE_PRINT_MARKER not in student_builder.STUDENT_CSS:
        student_builder.STUDENT_CSS = (
            student_builder.STUDENT_CSS + "\n" + EXACT_SEVEN_PAGE_PRINT_CSS
        )
    return EXACT_SEVEN_PAGE_PRINT_MARKER


def _output_ready(path: Path) -> bool:
    try:
        return Path(path).is_file() and Path(path).stat().st_size >= MIN_OUTPUT_BYTES
    except OSError:
        return False


def _wait_for_output(path: Path) -> bool:
    deadline = time.monotonic() + max(0.0, float(OUTPUT_WAIT_SECONDS))
    while True:
        if _output_ready(path):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(max(0.001, float(OUTPUT_POLL_SECONDS)))


def _command(
    *,
    chromium: Path,
    profile: Path,
    headless_mode: str,
    source_html: Path,
    output_path: Path,
    mode: str,
) -> list[str]:
    common = [
        str(chromium),
        headless_mode,
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        "--no-first-run",
        "--no-default-browser-check",
        "--allow-file-access-from-files",
        "--run-all-compositor-stages-before-draw",
        f"--user-data-dir={profile}",
    ]
    if mode == "PDF":
        return [
            *common,
            "--print-to-pdf-no-header",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            source_html.resolve().as_uri(),
        ]
    if mode == "PNG":
        return [
            *common,
            "--hide-scrollbars",
            "--window-size=1440,1200",
            f"--screenshot={output_path}",
            source_html.resolve().as_uri(),
        ]
    raise acceptance.StudentEntryAcceptanceError(f"browser_mode_invalid:{mode}")


def _minimal_windows_command(
    *,
    chromium: Path,
    source_html: Path,
    output_path: Path,
    mode: str,
) -> list[str]:
    """Mirror the local Windows Edge smoke command with no profile-only flags."""
    common = [
        str(chromium),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if mode == "PDF":
        return [
            *common,
            f"--print-to-pdf={output_path}",
            source_html.resolve().as_uri(),
        ]
    if mode == "PNG":
        return [
            *common,
            "--hide-scrollbars",
            "--window-size=1440,1200",
            f"--screenshot={output_path}",
            source_html.resolve().as_uri(),
        ]
    raise acceptance.StudentEntryAcceptanceError(f"browser_mode_invalid:{mode}")


def _tail(value: str, limit: int = 1200) -> str:
    return str(value or "")[-limit:].replace("\r", "\\r").replace("\n", "\\n")


def _execute_attempt(
    command: Sequence[str],
    *,
    output_path: Path,
    fallback_path: Path | None,
    cwd: Path | None,
) -> tuple[int | str, str, str, bool, bool]:
    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd is not None else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        return_code: int | str = int(result.returncode)
        stdout = str(result.stdout or "")
        stderr = str(result.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return_code = "TIMEOUT"
        stdout = str(exc.stdout or "")
        stderr = str(exc.stderr or "")

    target_ready = _wait_for_output(output_path)
    fallback_promoted = False
    if (
        not target_ready
        and fallback_path is not None
        and fallback_path != output_path
    ):
        fallback_ready = _wait_for_output(fallback_path)
        if fallback_ready:
            os.replace(fallback_path, output_path)
            target_ready = _output_ready(output_path)
            fallback_promoted = target_ready
    return return_code, stdout, stderr, target_ready, fallback_promoted


def _prelearning_page_count_if_applicable(
    *,
    source_html: Path,
    output_path: Path,
    mode: str,
) -> int | None:
    if mode != "PDF" or Path(source_html).name != "prelearning.html":
        return None
    return int(acceptance._pdf_page_count(output_path))


def _run_browser_windows_safe(
    chromium: Path,
    *,
    source_html: Path,
    output_path: Path,
    mode: str,
) -> dict[str, Any]:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if mode not in DEFAULT_OUTPUT_NAMES:
        raise acceptance.StudentEntryAcceptanceError(f"browser_mode_invalid:{mode}")

    attempts: list[dict[str, Any]] = []
    fallback_path = output_path.parent / DEFAULT_OUTPUT_NAMES[mode]

    if PREFER_MINIMAL_WINDOWS_COMMAND:
        output_path.unlink(missing_ok=True)
        started = time.monotonic()
        command = _minimal_windows_command(
            chromium=Path(chromium),
            source_html=Path(source_html),
            output_path=output_path,
            mode=mode,
        )
        return_code, stdout, stderr, target_ready, fallback_promoted = _execute_attempt(
            command,
            output_path=output_path,
            fallback_path=None,
            cwd=None,
        )
        page_count = (
            _prelearning_page_count_if_applicable(
                source_html=source_html,
                output_path=output_path,
                mode=mode,
            )
            if target_ready
            else None
        )
        exact_page_contract = (
            page_count is None or page_count == EXACT_PRELEARNING_PAGE_COUNT
        )
        attempt = {
            "attempt_mode": "minimal_windows",
            "headless_mode": "--headless=new",
            "return_code": return_code,
            "target_output_present": output_path.is_file(),
            "target_output_ready": target_ready,
            "prelearning_pdf_page_count": page_count,
            "exact_prelearning_page_contract": exact_page_contract,
            "fallback_output_promoted": fallback_promoted,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
        attempts.append(attempt)
        if return_code == 0 and target_ready and exact_page_contract:
            identity = acceptance.file_identity(output_path)
            return {
                "mode": mode,
                "source_name": Path(source_html).name,
                "output_name": output_path.name,
                "attempt_mode": "minimal_windows",
                "headless_mode": "--headless=new",
                "render_attempt_count": len(attempts),
                "fallback_output_promoted": False,
                "post_process_wait_seconds": attempt["elapsed_seconds"],
                "prelearning_pdf_page_count": page_count,
                **identity,
            }

    for headless_mode in HEADLESS_MODES:
        output_path.unlink(missing_ok=True)
        if fallback_path != output_path:
            fallback_path.unlink(missing_ok=True)
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="a1fs-chromium-") as profile_name:
            command = _command(
                chromium=Path(chromium),
                profile=Path(profile_name),
                headless_mode=headless_mode,
                source_html=Path(source_html),
                output_path=output_path,
                mode=mode,
            )
            return_code, stdout, stderr, target_ready, fallback_promoted = _execute_attempt(
                command,
                output_path=output_path,
                fallback_path=fallback_path,
                cwd=output_path.parent,
            )

        page_count = (
            _prelearning_page_count_if_applicable(
                source_html=source_html,
                output_path=output_path,
                mode=mode,
            )
            if target_ready
            else None
        )
        exact_page_contract = (
            page_count is None or page_count == EXACT_PRELEARNING_PAGE_COUNT
        )
        attempt = {
            "attempt_mode": "isolated_profile",
            "headless_mode": headless_mode,
            "return_code": return_code,
            "target_output_present": output_path.is_file(),
            "target_output_ready": target_ready,
            "prelearning_pdf_page_count": page_count,
            "exact_prelearning_page_contract": exact_page_contract,
            "fallback_output_promoted": fallback_promoted,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
        attempts.append(attempt)
        if return_code == 0 and target_ready and exact_page_contract:
            identity = acceptance.file_identity(output_path)
            return {
                "mode": mode,
                "source_name": Path(source_html).name,
                "output_name": output_path.name,
                "attempt_mode": "isolated_profile",
                "headless_mode": headless_mode,
                "render_attempt_count": len(attempts),
                "fallback_output_promoted": fallback_promoted,
                "post_process_wait_seconds": attempt["elapsed_seconds"],
                "prelearning_pdf_page_count": page_count,
                **identity,
            }

    raise acceptance.StudentEntryAcceptanceError(
        "chromium_render_failed:"
        + mode
        + ":"
        + json.dumps(attempts, ensure_ascii=False, sort_keys=True)
    )


def install_fullfix() -> Any:
    """Install the bounded Windows-safe renderer into the accepted pipeline."""
    previous = acceptance._run_browser
    acceptance._run_browser = _run_browser_windows_safe
    return previous


def main(argv: Sequence[str] | None = None) -> int:
    prelearning_v2.install_fullfix()
    install_exact_seven_page_print_layout()
    install_fullfix()
    return local_operator.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
