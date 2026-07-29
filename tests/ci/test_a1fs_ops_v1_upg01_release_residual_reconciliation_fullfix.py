from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_release_residual_fullfix_in_isolated_pytest_process() -> None:
    repository = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repository)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/ulga/test_a1fs_ops_v1_upg01_release_residual_reconciliation_fullfix.py",
        ],
        cwd=repository,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
