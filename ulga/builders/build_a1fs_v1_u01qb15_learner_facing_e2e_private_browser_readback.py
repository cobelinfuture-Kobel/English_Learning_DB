#!/usr/bin/env python3
"""Governance-bound entry point for the U01QB15 disposable Chromium readback."""
from __future__ import annotations

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runs only a disposable-state Chromium acceptance over the already-approved U01QB15 learner product; it authors no canonical learner content or learner-state authority."

from ulga.builders._a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback_impl import *  # noqa: F401,F403,E402


if __name__ == "__main__":
    raise SystemExit(main())
