#!/usr/bin/env python3
"""Run Unit01 local-private materialization with approved Pre-Learning V2.

The accepted Unit01 authority and QuestionBank remain unchanged. This entry
installs the learner-facing seven-page Pre-Learning V2 projection and replaces
only the Chromium process boundary so Windows Chrome or Edge may finish
asynchronous file creation, fall back from ``--headless=new`` to ``--headless``,
and promote the browser default output name when an otherwise successful
process ignores the explicit output path. All attempts remain bounded and fail
closed.
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
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as acceptance,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_local_private_materialization_operator_readback
    as local_operator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Installs the approved learner-facing Unit01 Pre-Learning V2 projection and "
    "adapts only the Windows Chromium process/output boundary for the already "
    "accepted Unit01 learner package. It creates no canonical learner content, "
    "question, answer, bank, planner, renderer authority, learner state, score, "
    "image asset, audio, A2 content, Unit02-24 artifact, production activation, "
    "or public delivery."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = "A1FS-OPS-V1_Unit01WindowsChromiumRenderFullFix"
PASS_STATUS = local_operator.PASS_STATUS
HEADLESS_MODES = ("--headless=new", "--headless")
OUTPUT_WAIT_SECONDS = 12.0
OUTPUT_POLL_SECONDS = 0.20
MIN_OUTPUT_BYTES = 1024
DEFAULT_OUTPUT_NAMES = {
    "PDF": "output.pdf",
    "PNG": "screenshot.png",
}


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


def _tail(value: str, limit: int = 1200) -> str:
    return str(value or "")[-limit:].replace("\r", "\\r").replace("\n", "\\n")


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
            try:
                result = subprocess.run(
                    command,
                    cwd=str(output_path.parent),
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
            if not target_ready and fallback_path != output_path:
                fallback_ready = _wait_for_output(fallback_path)
                if fallback_ready:
                    os.replace(fallback_path, output_path)
                    target_ready = _output_ready(output_path)
                    fallback_promoted = target_ready

            attempt = {
                "headless_mode": headless_mode,
                "return_code": return_code,
                "target_output_present": output_path.is_file(),
                "target_output_ready": target_ready,
                "fallback_output_promoted": fallback_promoted,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "stdout_tail": _tail(stdout),
                "stderr_tail": _tail(stderr),
            }
            attempts.append(attempt)
            if return_code == 0 and target_ready:
                identity = acceptance.file_identity(output_path)
                return {
                    "mode": mode,
                    "source_name": Path(source_html).name,
                    "output_name": output_path.name,
                    "headless_mode": headless_mode,
                    "render_attempt_count": len(attempts),
                    "fallback_output_promoted": fallback_promoted,
                    "post_process_wait_seconds": attempt["elapsed_seconds"],
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
    install_fullfix()
    return local_operator.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
