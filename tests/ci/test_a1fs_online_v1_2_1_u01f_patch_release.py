from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_u01f_patch_release_regressions_in_isolated_runtime_process() -> None:
    """Run the executable patch suite without mutating legacy runtime imports."""
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/ulga/test_a1fs_online_v1_2_1_u01f_patch_release.py",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        "U01F isolated regression failed\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
