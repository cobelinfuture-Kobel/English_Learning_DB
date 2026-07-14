#!/usr/bin/env python3
"""Rebuild the approved M04B3 AI-assisted triage draft from a private review queue.

The output remains a local/private proposal registry. Every formal decision stays
PENDING; reviewer identity, timestamp, criteria, and revisions are never forged.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (  # noqa: E402
    _assert_schema,
    read_json,
    sha256_value,
    write_json_atomic,
)

TASK_ID = "E4S-A1V1-M04B3_SourceGroundedReadingCandidateReviewAndPromotion"
EXPECTED_PROPOSALS = {
    "APPROVE_AS_IS": 77,
    "APPROVE_WITH_REVISION": 4,
    "REJECT": 62,
    "DEFER": 138,
}

PROPER_NAME_CLOZE_SELECTIONS = frozenset(
    f"E4S_A1V1_READING_SOURCE_{number:03d}"
    for number in (10, 11, 22, 32, 42, 47, 49, 52)
)
REVISION_SELECTIONS = frozenset(
    f"E4S_A1V1_READING_SOURCE_{number:03d}" for number in (33, 34)
)
ORDERING_CONTEXT_DEFER_SELECTIONS = frozenset({"E4S_A1V1_READING_SOURCE_053"})


class TriageRebuildError(ValueError):
    """Fail-closed triage reconstruction error."""


def proposal_for(entry: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    question_type = entry.get("question_type")
    selection_id = entry.get("selection_id")

    if question_type == "true_false":
        return "REJECT", (
            "ALL_TRUE_BANK_BIAS",
            "TRUE_FALSE_VARIATION_NOT_REVIEWED",
        )

    if isinstance(question_type, str) and question_type.startswith("literal_"):
        return "DEFER", (
            "LITERAL_REVISION_REQUIRED",
            "SOURCE_SENTENCE_TEXT_NOT_PRESENT_IN_REVIEW_ENTRY",
            "PROMPT_AND_ANSWER_REQUIRE_PRIVATE_SOURCE_REVIEW",
        )

    if question_type == "cloze_vocabulary":
        if selection_id in REVISION_SELECTIONS:
            return "APPROVE_WITH_REVISION", (
                "PRIVATE_SOURCE_REVISION_REQUIRED",
                "QUOTE_BOUNDARY_OR_SENTENCE_SEGMENTATION_REVIEW",
            )
        if selection_id in PROPER_NAME_CLOZE_SELECTIONS:
            return "REJECT", (
                "PROPER_NAME_OR_TITLE_USED_AS_VOCABULARY_TARGET",
                "RETARGET_TO_GENERALIZABLE_LEXICAL_ITEM",
            )
        return "APPROVE_AS_IS", (
            "SOURCE_RECALL_CLOZE_ACCEPTABLE",
            "ANSWER_MODEL_PRESENT",
            "NO_BLOCK_PRECHECK",
        )

    if question_type == "sentence_ordering":
        if selection_id in REVISION_SELECTIONS:
            return "APPROVE_WITH_REVISION", (
                "PRIVATE_SOURCE_REVISION_REQUIRED",
                "QUOTE_BOUNDARY_OR_SENTENCE_SEGMENTATION_REVIEW",
            )
        if selection_id in ORDERING_CONTEXT_DEFER_SELECTIONS:
            return "DEFER", (
                "SEQUENCE_RELATIONSHIP_UNCLEAR",
                "FULL_PASSAGE_CONTEXT_REQUIRED",
            )
        return "APPROVE_AS_IS", (
            "DISPLAY_ORDER_NON_IDENTITY",
            "ANSWER_ORDER_PRESENT",
            "SEQUENCE_APPEARS_MEANINGFUL",
        )

    raise TriageRebuildError(f"unsupported_question_type:{question_type}")


def proposal_note(decision: str, reasons: tuple[str, ...]) -> str:
    return (
        "AI_ASSISTED_TRIAGE_ONLY;"
        f"PROPOSED_DECISION={decision};"
        f"REASON_CODES={','.join(reasons)};"
        "NOT_OPERATOR_APPROVAL"
    )


def proposal_distribution(entries: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(proposal_for(entry)[0] for entry in entries)
    return {key: counts[key] for key in EXPECTED_PROPOSALS}


def rebuild_registry(queue: Mapping[str, Any]) -> dict[str, Any]:
    _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
    entries = queue.get("review_entries")
    if not isinstance(entries, list) or len(entries) != 281:
        actual = len(entries) if isinstance(entries, list) else None
        raise TriageRebuildError(f"review_entry_count_not_281:{actual}")
    if queue.get("review_entry_count") != 281:
        raise TriageRebuildError("declared_review_entry_count_not_281")
    if queue.get("review_entries_sha256") != sha256_value(entries):
        raise TriageRebuildError("review_queue_hash_drift")

    distribution = proposal_distribution(entries)
    if distribution != EXPECTED_PROPOSALS:
        raise TriageRebuildError(
            "proposal_distribution_mismatch:"
            + json.dumps(distribution, sort_keys=True)
        )

    decisions = []
    for entry in entries:
        decision, reasons = proposal_for(entry)
        decisions.append(
            {
                "review_entry_id": entry["review_entry_id"],
                "candidate_id": entry["candidate_id"],
                "source_content_sha256": entry["source_integrity"]["content_sha256"],
                "candidate_payload_sha256": entry["candidate_payload_sha256"],
                "decision": "PENDING",
                "reviewer_id": None,
                "reviewed_at": None,
                "criteria": {},
                "revision": None,
                "rejection_reasons": [],
                "review_notes": proposal_note(decision, reasons),
            }
        )

    registry = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.reading_operator_decisions.v1",
        "artifact_type": "local_operator_decision_registry",
        "policy": {
            "private_local_only": True,
            "must_not_be_committed": True,
            "template_is_approval": False,
        },
        "review_queue_sha256": sha256_value(queue),
        "decisions": decisions,
    }
    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", registry)
    return registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        queue = read_json(args.review_queue)
        registry = rebuild_registry(queue)
        write_json_atomic(args.output, registry)
        print(json.dumps({
            "decision_count": len(registry["decisions"]),
            "proposal_counts": EXPECTED_PROPOSALS,
            "formal_decision_count": 0,
            "validation_status": "PASS_AI_ASSISTED_TRIAGE_REBUILT",
        }, sort_keys=True))
        return 0
    except (TriageRebuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
