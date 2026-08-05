from __future__ import annotations

from pathlib import Path

from ulga.builders.build_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback import (
    _fresh_run_output,
)


def test_replace_allocates_fresh_sibling_without_touching_stale_output(tmp_path: Path) -> None:
    requested = tmp_path / "learner_facing_e2e_browser"
    stale_profile = requested / "chromium_profile" / "Default" / "Extensions" / "edge-extension"
    stale_profile.mkdir(parents=True)
    stale_file = stale_profile / "dynamic.mp4"
    stale_file.write_bytes(b"still-active")

    fresh = _fresh_run_output(requested)

    assert fresh != requested
    assert fresh.parent == requested.parent
    assert fresh.name.startswith(requested.name + ".run-")
    assert not fresh.exists()
    assert requested.exists()
    assert stale_file.read_bytes() == b"still-active"


def test_replace_allocates_distinct_paths_for_consecutive_runs(tmp_path: Path) -> None:
    requested = tmp_path / "learner_facing_e2e_browser"
    first = _fresh_run_output(requested)
    second = _fresh_run_output(requested)
    assert first != second
    assert not first.exists()
    assert not second.exists()


def test_edge_entrypoint_no_longer_uses_in_place_rmtree_cleanup() -> None:
    source = Path(
        "ulga/builders/build_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback.py"
    ).read_text(encoding="utf-8")

    assert "_run_with_fresh_replace" in source
    assert "_fresh_run_output" in source
    assert "replace=False" in source
    assert "uuid.uuid4" in source
    assert "race_safe_rmtree" not in source
    assert "shutil.rmtree" not in source
    assert "REQUESTED_OUTPUT=" in source
    assert "ACTUAL_OUTPUT=" in source


def test_obsolete_in_place_cleanup_helper_is_removed() -> None:
    assert not Path(
        "ulga/builders/_a1fs_v1_u01qb15_edge_output_cleanup_fullfix.py"
    ).exists()
