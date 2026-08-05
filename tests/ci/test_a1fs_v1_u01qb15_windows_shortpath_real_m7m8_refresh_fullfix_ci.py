from __future__ import annotations

import sqlite3
from pathlib import Path

from product.a1fs_v1_2_1 import runtime_server as base
from ulga.builders import (
    build_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback as runner,
)


LEGACY_WINDOWS_M7_PATH = (
    r"C:\Users\USER\PycharmProjects\homework\English_Learning_DB_Main"
    r"\.local\a1fs_v1\u01qb15\learner_facing_e2e_browser.run-123456789abc"
    r"\disposable_state\shared\learner_state\canonical_learning_state"
    r"\A1FS_V121_LOCAL_LEARNER\m7\a1fs_v1_m7_mastery_snapshot.private.json"
)
SHORT_WINDOWS_M7_PATH = (
    r"C:\Users\USER\AppData\Local\Temp\a1u01\r-12345678"
    r"\disposable_state\shared\learner_state\canonical_learning_state"
    r"\A1FS_V121_LOCAL_LEARNER\m7\a1fs_v1_m7_mastery_snapshot.private.json"
)


def test_windows_path_budget_regression_is_explicit_and_short_execution_root_has_margin(tmp_path: Path) -> None:
    # This is the exact path shape that crossed the traditional Windows MAX_PATH
    # boundary on the operator machine. Keep it as a regression witness.
    assert len(LEGACY_WINDOWS_M7_PATH) == 261
    assert len(SHORT_WINDOWS_M7_PATH) == 180
    assert len(SHORT_WINDOWS_M7_PATH) <= runner.WINDOWS_PROJECTED_PATH_MAX

    execution = tmp_path / "a1u01" / "r-12345678"
    lengths = runner._assert_windows_path_budget(execution)
    assert lengths["execution_root"] <= runner.WINDOWS_EXECUTION_ROOT_MAX
    assert max(lengths.values()) <= runner.WINDOWS_PROJECTED_PATH_MAX
    assert lengths["m7_snapshot"] > lengths["database"]


def test_short_execution_root_is_separate_from_repo_side_report_output(tmp_path: Path) -> None:
    report_output = tmp_path / "very" / "deep" / "repo" / "evidence" / "learner_facing_e2e_browser"
    execution, lengths = runner._fresh_short_execution_output(tmp_path / "short")
    assert execution.parent == (tmp_path / "short").resolve()
    assert execution != report_output.resolve()
    assert max(lengths.values()) <= runner.WINDOWS_PROJECTED_PATH_MAX
    projected = runner._projected_execution_paths(execution)
    assert str(projected["m7_snapshot"]).startswith(str(execution))
    assert str(projected["edge_profile_root"]).startswith(str(execution))


def test_real_m7_m8_refresh_writes_and_reloads_snapshot_under_disposable_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Execute the real S16 M7/M8 refresh; no fake refresh function is allowed here."""
    state_root = tmp_path / "s"
    monkeypatch.setenv("A1FS_V121_STATE_ROOT", str(state_root))

    app = base._app()
    result = app.refresh_canonical_learning(
        learner_id=base.DEFAULT_LEARNER_ID,
        at="2026-08-05T00:00:00Z",
    )

    assert result["a2_unlocked"] is False
    assert result["m7"]["missing_mastery_count"] >= 0
    assert result["m8"]["scheduled_node_count"] >= 0
    assert result["m8"]["retention_confirmed"] is False

    database = state_root / "shared/database/learner_runtime.sqlite3"
    m7_snapshot = (
        state_root
        / "shared/learner_state/canonical_learning_state"
        / base.DEFAULT_LEARNER_ID
        / "m7"
        / runner.M7_SNAPSHOT_NAME
    )
    assert database.is_file()
    assert m7_snapshot.is_file()
    assert m7_snapshot.stat().st_size > 0

    # M8 must have successfully read the physical M7 snapshot and persisted its
    # own authority tables. This catches the exact file-boundary missed by the
    # previous mocked post-completion test.
    with sqlite3.connect(database) as connection:
        m7_status = connection.execute(
            "SELECT value FROM m7_metadata WHERE key='validation_status'"
        ).fetchone()
        m8_status = connection.execute(
            "SELECT value FROM m8_metadata WHERE key='validation_status'"
        ).fetchone()
        mastery_snapshots = connection.execute(
            "SELECT COUNT(*) FROM mastery_snapshots WHERE learner_id=?",
            (base.DEFAULT_LEARNER_ID,),
        ).fetchone()[0]
        retention_snapshots = connection.execute(
            "SELECT COUNT(*) FROM retention_snapshots WHERE learner_id=?",
            (base.DEFAULT_LEARNER_ID,),
        ).fetchone()[0]

    assert m7_status is not None
    assert m8_status is not None
    assert mastery_snapshots >= 1
    assert retention_snapshots >= 1
