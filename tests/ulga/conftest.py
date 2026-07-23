from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _cp07d_private_media_canary_directories(request: pytest.FixtureRequest, tmp_path: Path) -> None:
    """Create only the nested private-media dirs used by the CP07D canary module.

    This fixture is temporary until the helper itself creates its private subdirectories.
    """
    if request.node.path.name != "test_a1fs_v1_cp07d_private_four_skill_delivery_consumer.py":
        return
    (tmp_path / "listening").mkdir(parents=True, exist_ok=True)
    (tmp_path / "speaking").mkdir(parents=True, exist_ok=True)
