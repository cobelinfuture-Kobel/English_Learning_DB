#!/usr/bin/env python3
"""Compatibility entrypoint with precise English stimulus-dependency detection."""
from __future__ import annotations

import re

from ulga.builders import _a1fs_v1_shared_learner_stimulus_contract_renderer_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates and renders learner-visible stimuli without producing canonical or four-skill content."
)

_core.PROMPT_PATTERNS = dict(_core.PROMPT_PATTERNS)
_core.PROMPT_PATTERNS["TEXT"] = tuple(_core.PROMPT_PATTERNS["TEXT"]) + (
    re.compile(r"\b(?:the|this)\s+article\b", re.I),
    re.compile(r"\b(?:read|reread|according\s+to|based\s+on|from)\s+(?:the|this|an?)?\s*article\b", re.I),
)

# A bare English noun "table" commonly names furniture (for example,
# "There is a book on the table").  It must not imply a DATA_TABLE stimulus.
# Require instructional/data-reference syntax while retaining the established
# Chinese table/chart vocabulary and all explicit table-reading instructions.
_core.PROMPT_PATTERNS["TABLE"] = (
    re.compile(r"表格|圖表|資料表"),
    re.compile(
        r"\b(?:read|reread|look\s+at|use|complete|study|check|compare|refer\s+to|consult|examine)"
        r"\s+(?:the|this|that|a|an)?\s*(?:data\s+)?(?:table|chart)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:according\s+to|based\s+on|from|in)\s+(?:the|this|that)\s+"
        r"(?:data\s+)?(?:table|chart)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:the|this|that)\s+(?:following\s+|given\s+|provided\s+)?"
        r"(?:data\s+)?(?:table|chart)\s+"
        r"(?:below|above|shows?|lists?|contains?|gives?|provides?|compares?)\b",
        re.I,
    ),
    re.compile(r"\b(?:table|chart)\s+(?:below|above)\b", re.I),
)

PROMPT_PATTERNS = _core.PROMPT_PATTERNS
