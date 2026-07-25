#!/usr/bin/env python3
"""Compatibility entrypoint with expanded English reading-dependency detection."""
from __future__ import annotations

import re

from ulga.builders import _a1fs_v1_shared_learner_stimulus_contract_renderer_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates and renders learner-visible stimuli only; does not produce canonical "
    "or four-skill content."
)

_core.PROMPT_PATTERNS = dict(_core.PROMPT_PATTERNS)
_core.PROMPT_PATTERNS["TEXT"] = tuple(_core.PROMPT_PATTERNS["TEXT"]) + (
    re.compile(r"\b(?:the|this)\s+article\b", re.I),
    re.compile(r"\b(?:read|reread|according\s+to|based\s+on|from)\s+(?:the|this|an?)?\s*article\b", re.I),
)
PROMPT_PATTERNS = _core.PROMPT_PATTERNS
