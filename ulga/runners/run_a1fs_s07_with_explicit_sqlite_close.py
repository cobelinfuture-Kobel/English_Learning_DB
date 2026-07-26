#!/usr/bin/env python3
"""Run S07 with SQLite connections explicitly closed at context exit.

Python's sqlite3 connection context manager commits or rolls back but does not
close the connection. On Windows those live handles prevent os.replace from
atomically promoting the validated staging database over the persistent learner
database. This entrypoint preserves the S07 CLI and makes context-managed
connections deterministic across operating systems.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from types import TracebackType
from typing import Iterator, Sequence

from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Provides cross-platform SQLite handle lifecycle control for the existing S07 runtime migration; "
    "it creates no curriculum, learner content, answer key, mastery, audio, or public delivery."
)

TARGET_MODULE = "ulga.builders.build_a1fs_online_v1_s07_multiunit_runtime_expansion"


class ClosingConnection(sqlite3.Connection):
    """SQLite connection whose context manager also releases the OS handle."""

    context_exit_closed: bool

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.context_exit_closed = False

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc_value, traceback))
        finally:
            self.close()
            self.context_exit_closed = True


_ORIGINAL_CONNECT = sqlite3.connect


def _closing_connect(*args, **kwargs):  # type: ignore[no-untyped-def]
    requested_factory = kwargs.get("factory")
    if requested_factory not in (None, sqlite3.Connection, ClosingConnection):
        return _ORIGINAL_CONNECT(*args, **kwargs)
    kwargs["factory"] = ClosingConnection
    return _ORIGINAL_CONNECT(*args, **kwargs)


@contextmanager
def explicit_sqlite_context_close() -> Iterator[None]:
    """Temporarily make every context-managed SQLite connection close itself."""

    previous_connect = sqlite3.connect
    sqlite3.connect = _closing_connect  # type: ignore[assignment]
    try:
        yield
    finally:
        sqlite3.connect = previous_connect  # type: ignore[assignment]


def main(argv: Sequence[str] | None = None) -> int:
    with explicit_sqlite_context_close():
        return s07.main(list(argv) if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main())
