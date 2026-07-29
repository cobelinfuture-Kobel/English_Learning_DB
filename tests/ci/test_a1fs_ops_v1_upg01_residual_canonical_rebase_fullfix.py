from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_residual_canonical_rebase_regressions_in_isolated_process() -> None:
    repository = Path(__file__).resolve().parents[2]
    target = (
        repository
        / "tests/ulga/test_a1fs_ops_v1_upg01_residual_canonical_rebase_fullfix.py"
    )
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(target)],
        cwd=repository,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, (
        completed.stdout + "\n" + completed.stderr
    )
