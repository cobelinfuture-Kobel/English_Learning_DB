from __future__ import annotations

from types import SimpleNamespace

import pytest

from ulga.builders import _windows_process_compat as compat


def test_tasklist_pid_alive_matches_exact_csv_pid() -> None:
    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            stdout='"python.exe","11244","Console","1","10,000 K"\n'
        )

    assert compat._tasklist_pid_alive(11244, run=fake_run) is True
    assert compat._tasklist_pid_alive(11245, run=fake_run) is False


def test_safe_kill_signal_zero_is_read_only() -> None:
    delegated: list[tuple[int, int]] = []

    def original(pid: int, signal_number: int) -> str:
        delegated.append((pid, signal_number))
        return "delegated"

    safe = compat._build_safe_kill(
        original_kill=original,
        pid_alive=lambda pid: pid == 11244,
    )

    assert safe(11244, 0) is None
    assert delegated == []

    with pytest.raises(ProcessLookupError):
        safe(11245, 0)

    assert safe(11244, 15) == "delegated"
    assert delegated == [(11244, 15)]


def test_nonpositive_pid_is_not_alive() -> None:
    assert compat._tasklist_pid_alive(0, run=lambda *args, **kwargs: None) is False
    assert compat._tasklist_pid_alive(-1, run=lambda *args, **kwargs: None) is False
