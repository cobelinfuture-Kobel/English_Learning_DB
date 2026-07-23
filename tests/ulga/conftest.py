from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _cp07f_nested_negative_fixture_directory(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> None:
    """Create only the nested directory used by the CP07F REAL-claim rejection test."""
    if request.node.path.name != "test_a1fs_v1_cp07f_real_learner_end_to_end_acceptance.py":
        return
    (tmp_path / "real-claim").mkdir(parents=True, exist_ok=True)
