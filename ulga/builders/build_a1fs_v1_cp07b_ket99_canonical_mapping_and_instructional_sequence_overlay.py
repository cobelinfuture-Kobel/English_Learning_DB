#!/usr/bin/env python3
"""Governed entrypoint for the CP07B metadata-only implementation."""
from __future__ import annotations

from ulga.builders.cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay_impl import *  # noqa: F401,F403

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only mapping and soft instructional sequence overlay over non-authoritative KET transcript evidence and existing M1/CP06 authorities; no learner content, hard prerequisite edge, canonical Authority, runtime attempt, mastery, or A2 payload is created."


if __name__ == "__main__":
    raise SystemExit(main())
