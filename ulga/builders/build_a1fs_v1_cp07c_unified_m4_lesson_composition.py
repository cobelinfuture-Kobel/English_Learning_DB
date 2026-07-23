#!/usr/bin/env python3
"""Governed entrypoint for CP07C metadata-only M4 lesson composition."""
from __future__ import annotations

from ulga.builders.cp07c_unified_m4_lesson_composition_impl import *  # noqa: F401,F403
from ulga.builders.cp07c_unified_m4_lesson_composition_impl import _digest

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only enrichment of an existing valid M4 plan with KET, RAZ, and M11B activity identities and lineage; no private payload, prompt, scoring contract, learner response, hard prerequisite mutation, mastery, retention, or A2 payload is produced."


if __name__ == "__main__":
    raise SystemExit(main())
