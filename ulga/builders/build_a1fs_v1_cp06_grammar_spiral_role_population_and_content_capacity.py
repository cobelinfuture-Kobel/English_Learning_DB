#!/usr/bin/env python3
"""Governed entrypoint for the CP06 metadata-only implementation."""
from __future__ import annotations

from ulga.builders.cp06_grammar_spiral_role_population_and_content_capacity_impl import *  # noqa: F401,F403
from ulga.builders.cp06_grammar_spiral_role_population_and_content_capacity_impl import _write_atomic

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Governed metadata-only entrypoint; implementation derives roles and capacity from approved sources without creating learner content or publishing runtime state."


if __name__ == "__main__":
    raise SystemExit(main())
