#!/usr/bin/env python3
"""Governed entrypoint for the Unit01 learner renderer and real-attempt adapter."""
from __future__ import annotations

from typing import Any, Sequence

from ulga.builders import u01qb03_renderer_runtime_impl as _impl

# Governance parser requires both protected-builder declarations as one-line literals.
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Consumes the U01QB02 learner-safe session plan and existing M3/M6 runtime; no learner content, planner, learner database, exposure authority, response capture, scoring authority, audio, A2 content, or Unit02-Unit24 content is produced."


def main(argv: Sequence[str] | None = None) -> int:
    return _impl.main(argv)


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


if __name__ == "__main__":
    raise SystemExit(main())
