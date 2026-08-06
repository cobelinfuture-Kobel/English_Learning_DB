#!/usr/bin/env python3
"""U01QB16E facade over the existing recovery-safe Unit01 learner runtime.

This module installs the different-item reassessment consumer after all merged
U01QB15 learner-facing/recovery adapters are active.  It does not create a new
server, learner database, QuestionBank, scoring engine, mastery engine or
planner; it only adds the bounded U01QB16E reassessment routes and attempt-once
completion semantics to the existing objects.
"""
from __future__ import annotations

from typing import Any, Sequence

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Thin product facade that installs the U01QB16E runtime adapter over the "
    "existing U01QB15 E2E application/server objects; it creates no learner "
    "content, QuestionBank, second runtime/database/scoring/mastery authority, "
    "Unit02-24 content, audio, Speaking scoring or A2 unlock."
)
PROGRAM_ID = u16e.PROGRAM_ID
TASK_ID = u16e.TASK_ID
PASS_STATUS = u16e.PASS_STATUS
MODULE = "product.a1fs_v1_2_1.u01qb16e_runtime_server"
NEXT_SHORT_STEP = u16e.NEXT_SHORT_STEP

# Install after U01QB15 E2E has already patched ordered progression, authenticated
# static delivery and recovery-safe completion.  U01QB16E therefore composes on
# top of those exact production objects instead of bypassing them.
u16e.install_runtime(e2e.impl)
e2e.impl.MODULE = MODULE
e2e.impl.base.MODULE = MODULE


def main(argv: Sequence[str] | None = None) -> int:
    return e2e.main(argv)


def __getattr__(name: str) -> Any:
    return getattr(e2e, name)


if __name__ == "__main__":
    raise SystemExit(main())
