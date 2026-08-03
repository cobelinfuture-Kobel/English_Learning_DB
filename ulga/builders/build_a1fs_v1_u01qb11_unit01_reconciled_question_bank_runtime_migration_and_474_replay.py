#!/usr/bin/env python3
"""Governed entry point for U01QB11 runtime migration and 474-item replay."""
from __future__ import annotations

from ulga.builders._u01qb11_runtime_migration_474_replay_impl import *  # noqa: F401,F403

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "In-place migration of approved U01QB10 items into the existing U01QB02/M3/M6/Real62 runtime; no learner content, second QuestionBank, parallel planner, parallel learner database, parallel scoring authority, audio, Speaking scoring, Unit02-Unit24 content, or A2 content is produced."


if __name__ == "__main__":
    raise SystemExit(main())
