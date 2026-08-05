from __future__ import annotations

import shutil
from pathlib import Path

from ulga.builders._a1fs_v1_u01qb15_edge_output_cleanup_fullfix import race_safe_rmtree


def test_race_safe_rmtree_tolerates_nested_file_disappearing_mid_delete(tmp_path: Path) -> None:
    root = tmp_path / "browser-output"
    nested = root / "profile" / "Default" / "Extensions" / "edge-extension"
    nested.mkdir(parents=True)
    victim = nested / "dynamic.mp4"
    victim.write_bytes(b"temporary")

    calls = {"count": 0}

    def flaky_rmtree(path, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            victim.unlink(missing_ok=True)
            raise FileNotFoundError(3, "simulated browser-extension delete race", str(victim))
        return shutil.rmtree(path, *args, **kwargs)

    race_safe_rmtree(flaky_rmtree, root)
    assert calls["count"] >= 2
    assert not root.exists()


def test_race_safe_rmtree_is_noop_when_output_already_missing(tmp_path: Path) -> None:
    root = tmp_path / "missing"
    called = False

    def should_not_run(path, *args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError(path)

    race_safe_rmtree(should_not_run, root)
    assert called is False


def test_cleanup_fullfix_is_disposable_only() -> None:
    source = Path(
        "ulga/builders/_a1fs_v1_u01qb15_edge_output_cleanup_fullfix.py"
    ).read_text(encoding="utf-8")
    assert "learner_runtime.sqlite3" not in source
    assert "canonical_learning_state" not in source
    assert "original_rmtree(root, onerror=_onerror)" in source
    assert "FileNotFoundError" in source
    assert "PermissionError" in source
    assert "DISPOSABLE_OUTPUT_CLEANUP_FAILED" in source


def test_edge_entrypoint_uses_race_safe_cleanup_only_for_replace() -> None:
    source = Path(
        "ulga/builders/build_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback.py"
    ).read_text(encoding="utf-8")
    assert "_cleanup.race_safe_rmtree" in source
    assert "if replace:" in source
    assert "_impl.shutil.rmtree = original_rmtree" in source
    assert "output_dir=output_dir" in source
    assert "source_state_root=source_state_root" in source
