from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_upg01_regressions_in_isolated_runtime_process() -> None:
    repository = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/ulga/test_a1fs_ops_v1_upg01_portable_resumable_universal_upgrade_orchestrator_fullfix.py",
        ],
        cwd=repository,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        "UPG01 isolated regression failed\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
