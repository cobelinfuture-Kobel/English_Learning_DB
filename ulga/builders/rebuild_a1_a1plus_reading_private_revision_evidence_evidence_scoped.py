#!/usr/bin/env python3
"""Rebuild M04B3 private revision evidence with source-evidence-scoped cloze resolution.

This compatibility entry point changes only the private cloze revision selector. It
preserves the original builder's hashes, schemas, validation, output paths, decision
boundaries, and CLI arguments. It does not approve or promote any item.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_reading_private_revision_evidence as base


def build_cloze_revision_evidence_scoped(
    candidate: Mapping[str, Any],
    segments: list[Mapping[str, Any]],
    evidence_ids: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Resolve repeated answer tokens by source-sentence evidence before blanking."""
    problems: list[str] = []
    answer_model = candidate.get("answer_model")
    answer = answer_model.get("answer_key") if isinstance(answer_model, Mapping) else None
    if not isinstance(answer, str) or not answer.strip():
        return None, ["ORIGINAL_CLOZE_KEY_MISSING"]

    answer = answer.strip()
    answer_pattern = rf"\b{re.escape(answer)}\b"
    containing = [
        segment
        for segment in segments
        if re.search(answer_pattern, str(segment["sentence"]), re.IGNORECASE)
    ]
    evidence_set = {str(item) for item in evidence_ids}
    evidence_linked = [
        segment
        for segment in containing
        if evidence_set.intersection(
            str(item) for item in segment.get("source_sentence_ids", [])
        )
    ]

    if len(evidence_linked) == 1:
        segment = evidence_linked[0]
        if len(containing) > 1:
            problems.append("CLOZE_SEGMENT_RESOLVED_BY_SOURCE_EVIDENCE")
    elif len(evidence_linked) > 1:
        return None, [f"CLOZE_EVIDENCE_SEGMENT_MATCH_COUNT_{len(evidence_linked)}"]
    elif len(containing) == 1:
        segment = containing[0]
    else:
        return None, [f"CLOZE_KEY_SEGMENT_MATCH_COUNT_{len(containing)}"]

    prompt_body, replacements = re.subn(
        answer_pattern,
        "____",
        str(segment["sentence"]),
        count=1,
        flags=re.IGNORECASE,
    )
    if replacements != 1:
        return None, ["CLOZE_BLANK_REPLACEMENT_FAILED"]

    provenance = [
        item for item in segment.get("source_sentence_ids", []) if item in evidence_set
    ]
    if not provenance:
        provenance = list(evidence_ids)
        problems.append("SEGMENT_PROVENANCE_FALLBACK_TO_ORIGINAL_EVIDENCE")

    revision = {
        "prompt": f"Complete the source sentence: {prompt_body}",
        "answer_model": {
            "answer_type": "normalized_text",
            "answer_key": answer,
            "case_sensitive": False,
        },
        "accepted_answers": [answer],
        "source_sentence_ids": provenance,
    }
    return revision, problems


def install_evidence_scoped_cloze_fullfix() -> None:
    """Install the scoped selector into the original builder module."""
    base._build_cloze_revision = build_cloze_revision_evidence_scoped


def main(argv: list[str] | None = None) -> int:
    install_evidence_scoped_cloze_fullfix()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
