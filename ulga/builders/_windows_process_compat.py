#!/usr/bin/env python3
"""Windows-safe process liveness compatibility for ULGA builders.

On POSIX, ``os.kill(pid, 0)`` is a non-destructive liveness probe. CPython on
Windows does not provide the same guarantee. This module replaces only signal
zero on Windows with a read-only ``tasklist`` lookup and delegates every real
signal to the original ``os.kill`` implementation.
"""
from __future__ import annotations

import csv
import errno
import os
import subprocess
from collections.abc import Callable
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Provides a Windows-only process-liveness compatibility shim for builder lifecycle commands. "
    "It creates no curriculum, learner content, answer, scoring, mastery, learner state, audio, A2, "
    "external route, or parallel runtime authority."
)

_ORIGINAL_OS_KILL = os.kill


def _tasklist_pid_alive(
    pid: int,
    *,
    run: Callable[..., Any] = subprocess.run,
) -> bool:
    """Return whether ``tasklist`` reports the exact PID without mutating it."""
    pid = int(pid)
    if pid <= 0:
        return False
    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        completed = run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=creationflags,
        )
    except OSError:
        return False
    for row in csv.reader(str(completed.stdout or "").splitlines()):
        if len(row) < 2:
            continue
        try:
            reported_pid = int(str(row[1]).strip())
        except ValueError:
            continue
        if reported_pid == pid:
            return True
    return False


def _build_safe_kill(
    *,
    original_kill: Callable[[int, int], Any] = _ORIGINAL_OS_KILL,
    pid_alive: Callable[[int], bool] = _tasklist_pid_alive,
) -> Callable[[int, int], Any]:
    """Build an ``os.kill`` wrapper that treats signal zero as read-only."""

    def safe_kill(pid: int, signal_number: int) -> Any:
        pid = int(pid)
        signal_number = int(signal_number)
        if signal_number == 0:
            if pid_alive(pid):
                return None
            raise ProcessLookupError(errno.ESRCH, os.strerror(errno.ESRCH), pid)
        return original_kill(pid, signal_number)

    setattr(safe_kill, "__a1fs_windows_safe_signal_zero__", True)
    return safe_kill


def install_windows_safe_signal_zero() -> bool:
    """Install once on Windows; remain a no-op on every other platform."""
    if os.name != "nt":
        return False
    if getattr(os.kill, "__a1fs_windows_safe_signal_zero__", False):
        return False
    os.kill = _build_safe_kill()  # type: ignore[assignment]
    return True
