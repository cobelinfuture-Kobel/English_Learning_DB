#!/usr/bin/env python3
"""Run the existing Actual Real62 acceptance with U01QB13 whole-form matching installed."""
from __future__ import annotations

from typing import Sequence

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import (
    build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner
    as base,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Operator entrypoint that installs deterministic whole-form distinct-item matching into the existing U01QB13 runtime before delegating to the existing U01QB15 Actual Real62 disposable acceptance runner; no content, QuestionBank, planner, runtime, scoring, scene, or learner-state authority is created."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_ActualReal62Fresh474R2DistinctMatchingAcceptance"
PASS_STATUS = base.PASS_STATUS
NEXT_SHORT_STEP = base.NEXT_SHORT_STEP


def main(argv: Sequence[str] | None = None) -> int:
    matching.install()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
