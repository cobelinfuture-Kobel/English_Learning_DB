from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = (
    "ulga.builders."
    "build_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback"
)


def _run_isolated(script: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout)


def test_private_browser_runner_is_non_content_producer_and_uses_disposable_state() -> None:
    result = _run_isolated(
        f'''
import json
from {MODULE} import (
    A1FS_CONTENT_POLICY_MODE,
    A1FS_CONTENT_POLICY_EXEMPTION,
    TASK_ID,
    PASS_STATUS,
    NEXT_SHORT_STEP,
)
print(json.dumps({{
    "mode": A1FS_CONTENT_POLICY_MODE,
    "has_exemption": bool(A1FS_CONTENT_POLICY_EXEMPTION),
    "task": TASK_ID,
    "pass": PASS_STATUS,
    "next": NEXT_SHORT_STEP,
}}))
'''
    )
    assert result["mode"] == "NOT_CONTENT_PRODUCER"
    assert result["has_exemption"] is True
    assert result["task"] == "A1FS-V1-U01QB15_LearnerFacingE2EPrivateBrowserReadback"
    assert result["pass"].startswith("PASS_A1FS_V1_U01QB15_LEARNER_FACING_E2E")
    assert result["next"] == (
        "A1FS-V1-U01QB15_ProductionReleaseStateAcceptanceAndUnit01NewQuestionBankCloseout"
    )


def test_private_browser_runner_fails_before_output_when_source_database_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "empty_state"
    output = tmp_path / "output"
    source.mkdir()
    script = f'''
import json
from pathlib import Path
from {MODULE} import run_readback, PrivateBrowserReadbackError
try:
    run_readback(
        output_dir=Path({str(output)!r}),
        replace=False,
        source_state_root=Path({str(source)!r}),
    )
except PrivateBrowserReadbackError as exc:
    print(json.dumps({{"error": str(exc), "output_exists": Path({str(output)!r}).exists()}}))
else:
    raise SystemExit("missing database was not rejected")
'''
    result = _run_isolated(script)
    assert result == {
        "error": "SOURCE_LEARNER_DATABASE_MISSING",
        "output_exists": False,
    }


def test_private_browser_runner_source_declares_real_chromium_and_canonical_hash_guards() -> None:
    path = REPO_ROOT / (
        "ulga/builders/"
        "_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback_impl.py"
    )
    source = path.read_text(encoding="utf-8")
    required = [
        "chromium_support.discover_chromium",
        "--remote-debugging-port=0",
        "Page.captureScreenshot",
        "shutil.copytree(source_state, disposable_state)",
        "CANONICAL_SOURCE_STATE_CHANGED_DURING_BROWSER_READBACK",
        'env["A1FS_V121_STATE_ROOT"] = str(disposable_state)',
        '"support_filler_exposure_count"',
        '"U01QB15_ADAPTER_LEAKED_TO_NON_UNIT01"',
    ]
    for token in required:
        assert token in source


def test_private_browser_runner_cli_help_imports_in_fresh_process() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", MODULE, "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "--output-dir" in completed.stdout
    assert "--replace" in completed.stdout
    assert "--chromium" in completed.stdout
    assert "--source-state-root" in completed.stdout
