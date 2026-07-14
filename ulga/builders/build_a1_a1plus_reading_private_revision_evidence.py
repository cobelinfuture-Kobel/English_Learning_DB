#!/usr/bin/env python3
"""Build private revision evidence for the four pending M04B3 Reading items.

This tool reads local copyrighted source material and therefore writes its detailed
output only to an operator-selected private path.  The companion safe report contains
counts, identifiers, and hashes only.  It never changes an operator decision and never
promotes an item.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (  # noqa: E402
    _assert_schema,
    _safe_scan,
    read_json,
    sha256_value,
    write_json_atomic,
)

TASK_ID = "E4S-A1V1-M04B3_PrivateRevisionEvidenceCompletion"
PRIVATE_SCHEMA = "e4s.a1v1.reading_private_revision_evidence.v1"
SAFE_SCHEMA = "e4s.a1v1.reading_private_revision_evidence_safe_report.v1"
TARGET_SELECTIONS = (
    "E4S_A1V1_READING_SOURCE_033",
    "E4S_A1V1_READING_SOURCE_034",
)
TARGET_QUESTION_TYPES = ("cloze_vocabulary", "sentence_ordering")
EXPECTED_PAIRS = frozenset(
    (selection_id, question_type)
    for selection_id in TARGET_SELECTIONS
    for question_type in TARGET_QUESTION_TYPES
)
EXPECTED_MATERIALIZED = {
    "PENDING": 4,
    "APPROVE_AS_IS": 77,
    "APPROVE_WITH_REVISION": 0,
    "REJECT": 62,
    "DEFER": 138,
}
TARGET_NOTE = "TARGET_DECISION=APPROVE_WITH_REVISION"


class RevisionEvidenceError(ValueError):
    """Fail-closed private revision evidence error."""


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def split_sentences_quote_aware(text: str) -> list[str]:
    """Split terminal punctuation followed by optional closing quotation marks."""
    normalized = _normalize_space(text)
    if not normalized:
        return []
    marked = re.sub(
        r"([.!?](?:[\"'”’]+)?)(?:\s+)(?=(?:[\"'“‘]*[A-Z0-9]))",
        r"\1\n",
        normalized,
    )
    return [part.strip() for part in marked.splitlines() if part.strip()]


def _source_sentence_map(record: Mapping[str, Any]) -> dict[str, str]:
    rows = record.get("source_sentences")
    if not isinstance(rows, list) or not rows:
        raise RevisionEvidenceError("private_source_sentences_missing")
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RevisionEvidenceError("private_source_sentence_row_invalid")
        sentence_id = row.get("sentence_id")
        sentence = row.get("sentence")
        if not isinstance(sentence_id, str) or not isinstance(sentence, str) or not sentence.strip():
            raise RevisionEvidenceError("private_source_sentence_fields_invalid")
        if sentence_id in result:
            raise RevisionEvidenceError(f"duplicate_private_source_sentence_id:{sentence_id}")
        result[sentence_id] = _normalize_space(sentence)
    return result


def _segment_provenance(segment: str, source_sentences: Mapping[str, str]) -> list[str]:
    normalized_segment = _normalize_space(segment).casefold()
    matches = [
        sentence_id
        for sentence_id, sentence in source_sentences.items()
        if normalized_segment in sentence.casefold() or sentence.casefold() in normalized_segment
    ]
    return matches


def _quote_aware_segments(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_text = record.get("source_text")
    if not isinstance(source_text, str) or not source_text.strip():
        raise RevisionEvidenceError("private_source_text_missing")
    source_sentences = _source_sentence_map(record)
    segments = split_sentences_quote_aware(source_text)
    if not segments:
        raise RevisionEvidenceError("quote_aware_sentence_split_empty")
    return [
        {
            "segment_id": f"R{index}",
            "sentence": sentence,
            "source_sentence_ids": _segment_provenance(sentence, source_sentences),
        }
        for index, sentence in enumerate(segments, start=1)
    ]


def _find_candidate(record: Mapping[str, Any], candidate_id: str) -> Mapping[str, Any]:
    candidates = record.get("deterministic_items")
    if not isinstance(candidates, list):
        raise RevisionEvidenceError("deterministic_items_missing")
    matches = [row for row in candidates if isinstance(row, Mapping) and row.get("item_id") == candidate_id]
    if len(matches) != 1:
        raise RevisionEvidenceError(f"private_candidate_join_not_one:{candidate_id}:{len(matches)}")
    return matches[0]


def _build_cloze_revision(
    candidate: Mapping[str, Any],
    segments: list[Mapping[str, Any]],
    evidence_ids: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    problems: list[str] = []
    answer_model = candidate.get("answer_model")
    answer = answer_model.get("answer_key") if isinstance(answer_model, Mapping) else None
    if not isinstance(answer, str) or not answer.strip():
        return None, ["ORIGINAL_CLOZE_KEY_MISSING"]
    answer = answer.strip()
    containing = [segment for segment in segments if re.search(rf"\b{re.escape(answer)}\b", str(segment["sentence"]), re.IGNORECASE)]
    if len(containing) != 1:
        return None, [f"CLOZE_KEY_SEGMENT_MATCH_COUNT_{len(containing)}"]
    segment = containing[0]
    prompt_body, replacements = re.subn(
        rf"\b{re.escape(answer)}\b",
        "____",
        str(segment["sentence"]),
        count=1,
        flags=re.IGNORECASE,
    )
    if replacements != 1:
        return None, ["CLOZE_BLANK_REPLACEMENT_FAILED"]
    provenance = [item for item in segment.get("source_sentence_ids", []) if item in evidence_ids]
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


def _build_ordering_revision(
    segments: list[Mapping[str, Any]],
    evidence_ids: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    if len(segments) < 2:
        return None, ["QUOTE_AWARE_SEQUENCE_HAS_FEWER_THAN_TWO_SEGMENTS"]
    correct_ids = [str(segment["segment_id"]) for segment in segments]
    rotated = correct_ids[1:] + correct_ids[:1]
    if rotated == correct_ids:
        return None, ["ORDERING_DISPLAY_REMAINS_IDENTITY"]
    by_id = {str(segment["segment_id"]): str(segment["sentence"]) for segment in segments}
    revision = {
        "prompt": "Put the source sentences in their original order.",
        "display_order": [
            {"sentence_id": segment_id, "sentence": by_id[segment_id]}
            for segment_id in rotated
        ],
        "answer_model": {
            "answer_type": "ordered_ids",
            "answer_key": correct_ids,
        },
        "accepted_answers": [correct_ids],
        "source_sentence_ids": list(evidence_ids),
    }
    return revision, []


def _private_record_map(private_bank: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if private_bank.get("artifact_type") != "local_private_source_grounded_reading_review_candidates":
        raise RevisionEvidenceError("private_bank_artifact_type_invalid")
    records = private_bank.get("records")
    if not isinstance(records, list) or len(records) != 54:
        raise RevisionEvidenceError("private_bank_record_count_not_54")
    result: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise RevisionEvidenceError("private_bank_record_invalid")
        selection = record.get("selection")
        selection_id = selection.get("selection_id") if isinstance(selection, Mapping) else None
        if not isinstance(selection_id, str) or selection_id in result:
            raise RevisionEvidenceError(f"private_bank_selection_invalid_or_duplicate:{selection_id}")
        result[selection_id] = record
    return result


def _pending_revision_rows(
    queue: Mapping[str, Any],
    decisions: Mapping[str, Any],
    *,
    require_production_counts: bool,
) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", decisions)
    entries = queue.get("review_entries")
    decision_rows = decisions.get("decisions")
    if not isinstance(entries, list) or not isinstance(decision_rows, list):
        raise RevisionEvidenceError("queue_or_decision_rows_missing")
    if queue.get("review_entry_count") != len(entries) or queue.get("review_entries_sha256") != sha256_value(entries):
        raise RevisionEvidenceError("review_queue_accounting_or_hash_drift")
    if decisions.get("review_queue_sha256") != sha256_value(queue):
        raise RevisionEvidenceError("materialized_registry_queue_hash_mismatch")
    if require_production_counts:
        if len(entries) != 281 or len(decision_rows) != 281:
            raise RevisionEvidenceError("production_review_or_decision_count_not_281")
        counts = Counter(str(row.get("decision")) for row in decision_rows if isinstance(row, Mapping))
        actual = {key: counts[key] for key in EXPECTED_MATERIALIZED}
        if actual != EXPECTED_MATERIALIZED:
            raise RevisionEvidenceError(f"materialized_distribution_drift:{actual}")
    entries_by_id = {row["review_entry_id"]: row for row in entries}
    pending: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for decision in decision_rows:
        if not isinstance(decision, Mapping):
            raise RevisionEvidenceError("materialized_decision_row_invalid")
        note = decision.get("review_notes")
        if decision.get("decision") == "PENDING" and isinstance(note, str) and TARGET_NOTE in note:
            entry = entries_by_id.get(decision.get("review_entry_id"))
            if entry is None:
                raise RevisionEvidenceError("pending_revision_entry_join_missing")
            pending.append((entry, decision))
    if len(pending) != 4:
        raise RevisionEvidenceError(f"pending_revision_entry_count_not_4:{len(pending)}")
    pairs = {(str(entry.get("selection_id")), str(entry.get("question_type"))) for entry, _ in pending}
    if pairs != EXPECTED_PAIRS:
        raise RevisionEvidenceError(f"pending_revision_pair_set_drift:{sorted(pairs)}")
    return sorted(pending, key=lambda pair: (pair[0]["selection_id"], pair[0]["question_type"]))


def build_revision_evidence(
    private_bank: Mapping[str, Any],
    queue: Mapping[str, Any],
    decisions: Mapping[str, Any],
    *,
    require_production_counts: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    records = _private_record_map(private_bank)
    pending = _pending_revision_rows(
        queue,
        decisions,
        require_production_counts=require_production_counts,
    )
    output_entries: list[dict[str, Any]] = []
    for entry, decision in pending:
        selection_id = str(entry["selection_id"])
        record = records.get(selection_id)
        if record is None:
            raise RevisionEvidenceError(f"private_selection_missing:{selection_id}")
        if record.get("source_integrity", {}).get("status") != "PASS":
            raise RevisionEvidenceError(f"private_source_integrity_not_pass:{selection_id}")
        selection = record.get("selection", {})
        source_hash = selection.get("content_sha256")
        if source_hash != entry.get("source_integrity", {}).get("content_sha256"):
            raise RevisionEvidenceError(f"source_hash_drift:{selection_id}")
        if decision.get("source_content_sha256") != source_hash:
            raise RevisionEvidenceError(f"decision_source_hash_drift:{selection_id}")
        candidate = entry.get("candidate_content")
        if not isinstance(candidate, Mapping) or sha256_value(candidate) != entry.get("candidate_payload_sha256"):
            raise RevisionEvidenceError(f"queue_candidate_hash_drift:{entry['review_entry_id']}")
        private_candidate = _find_candidate(record, str(entry["candidate_id"]))
        if sha256_value(private_candidate) != entry.get("candidate_payload_sha256"):
            raise RevisionEvidenceError(f"private_candidate_hash_drift:{entry['review_entry_id']}")
        evidence_ids = list(entry.get("source_evidence", {}).get("source_sentence_ids", []))
        if not evidence_ids:
            raise RevisionEvidenceError(f"source_evidence_ids_missing:{entry['review_entry_id']}")
        segments = _quote_aware_segments(record)
        if entry["question_type"] == "cloze_vocabulary":
            revision, problems = _build_cloze_revision(candidate, segments, evidence_ids)
        elif entry["question_type"] == "sentence_ordering":
            revision, problems = _build_ordering_revision(segments, evidence_ids)
        else:
            raise RevisionEvidenceError(f"unexpected_revision_question_type:{entry['question_type']}")
        status = "READY_FOR_OPERATOR_REVIEW" if revision is not None else "MANUAL_PRIVATE_EDIT_REQUIRED"
        output_entries.append({
            "review_entry_id": entry["review_entry_id"],
            "candidate_id": entry["candidate_id"],
            "selection_id": selection_id,
            "source_unit_ref": entry["source_unit_ref"],
            "question_type": entry["question_type"],
            "source_content_sha256": source_hash,
            "candidate_payload_sha256": entry["candidate_payload_sha256"],
            "original_source_sentences": copy.deepcopy(record["source_sentences"]),
            "quote_aware_segments": copy.deepcopy(segments),
            "original_candidate": copy.deepcopy(candidate),
            "proposed_revision": revision,
            "evidence_problems": problems,
            "revision_status": status,
            "formal_decision": "PENDING",
            "operator_approval_recorded": False,
        })
    output_entries.sort(key=lambda row: (row["selection_id"], row["question_type"]))
    ready_count = sum(row["revision_status"] == "READY_FOR_OPERATOR_REVIEW" for row in output_entries)
    private_output = {
        "task_id": TASK_ID,
        "schema_version": PRIVATE_SCHEMA,
        "artifact_type": "local_private_reading_revision_evidence",
        "policy": {
            "private_local_only": True,
            "must_not_be_committed": True,
            "automatic_operator_approval": False,
            "canonical_authority_write": False,
            "public_learner_delivery": False,
        },
        "source_hashes": {
            "private_bank_sha256": sha256_value(private_bank),
            "review_queue_sha256": sha256_value(queue),
            "materialized_registry_sha256": sha256_value(decisions),
        },
        "revision_entry_count": len(output_entries),
        "revision_entries": output_entries,
        "revision_entries_sha256": sha256_value(output_entries),
        "operator_review_required": True,
    }
    safe_report = {
        "task_id": TASK_ID,
        "schema_version": SAFE_SCHEMA,
        "artifact_type": "reading_revision_evidence_safe_report",
        "source_hashes": dict(private_output["source_hashes"]),
        "revision_entry_count": len(output_entries),
        "selection_distribution": dict(sorted(Counter(row["selection_id"] for row in output_entries).items())),
        "question_type_distribution": dict(sorted(Counter(row["question_type"] for row in output_entries).items())),
        "readiness_distribution": dict(sorted(Counter(row["revision_status"] for row in output_entries).items())),
        "revision_entries_sha256": private_output["revision_entries_sha256"],
        "private_payload_sha256": sha256_value(private_output),
        "operator_approval_recorded": False,
        "formal_decision_count_changed": 0,
        "reviewed_item_count_changed": 0,
        "authority_write_count": 0,
        "public_delivery_count": 0,
        "validation_status": (
            "PASS_PRIVATE_REVISION_EVIDENCE_READY_FOR_OPERATOR_REVIEW"
            if ready_count == 4
            else "PASS_PRIVATE_REVISION_EVIDENCE_REQUIRES_MANUAL_EDIT"
        ),
        "errors": [],
        "next_resume_task": "E4S-A1V1-M04B3_PrivateRevisionOperatorReviewAndApproval",
    }
    _safe_scan(safe_report)
    return private_output, safe_report


def validate_revision_evidence(private_output: Mapping[str, Any], safe_report: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    entries = private_output.get("revision_entries")
    if not isinstance(entries, list) or len(entries) != 4:
        errors.append("revision_entry_count_not_4")
        entries = []
    if private_output.get("revision_entry_count") != len(entries):
        errors.append("private_revision_entry_accounting_drift")
    if private_output.get("revision_entries_sha256") != sha256_value(entries):
        errors.append("private_revision_entries_hash_drift")
    pairs = {(str(row.get("selection_id")), str(row.get("question_type"))) for row in entries if isinstance(row, Mapping)}
    if pairs != EXPECTED_PAIRS:
        errors.append("revision_pair_set_drift")
    ready_count = 0
    for row in entries:
        if not isinstance(row, Mapping):
            errors.append("revision_entry_invalid")
            continue
        revision = row.get("proposed_revision")
        if row.get("revision_status") != "READY_FOR_OPERATOR_REVIEW" or not isinstance(revision, Mapping):
            continue
        ready_count += 1
        for key in ("prompt", "answer_model", "accepted_answers", "source_sentence_ids"):
            if not revision.get(key):
                errors.append(f"revision_field_missing:{row.get('review_entry_id')}:{key}")
        allowed = {
            source_row.get("sentence_id")
            for source_row in row.get("original_source_sentences", [])
            if isinstance(source_row, Mapping)
        }
        if not set(revision.get("source_sentence_ids", [])) <= allowed:
            errors.append(f"revision_source_sentence_drift:{row.get('review_entry_id')}")
        if row.get("question_type") == "cloze_vocabulary":
            if "____" not in str(revision.get("prompt", "")):
                errors.append(f"cloze_blank_missing:{row.get('review_entry_id')}")
        if row.get("question_type") == "sentence_ordering":
            display = revision.get("display_order")
            answer_model = revision.get("answer_model")
            correct = answer_model.get("answer_key") if isinstance(answer_model, Mapping) else None
            display_ids = [item.get("sentence_id") for item in display] if isinstance(display, list) else None
            if not isinstance(correct, list) or not correct or display_ids == correct:
                errors.append(f"ordering_revision_invalid:{row.get('review_entry_id')}")
    if safe_report.get("revision_entry_count") != len(entries):
        errors.append("safe_private_revision_count_mismatch")
    if safe_report.get("revision_entries_sha256") != private_output.get("revision_entries_sha256"):
        errors.append("safe_private_revision_hash_mismatch")
    if safe_report.get("private_payload_sha256") != sha256_value(private_output):
        errors.append("safe_private_payload_hash_mismatch")
    try:
        _safe_scan(safe_report)
    except ValueError as exc:
        errors.append(str(exc))
    expected_status = (
        "PASS_PRIVATE_REVISION_EVIDENCE_READY_FOR_OPERATOR_REVIEW"
        if ready_count == 4
        else "PASS_PRIVATE_REVISION_EVIDENCE_REQUIRES_MANUAL_EDIT"
    )
    if safe_report.get("validation_status") != expected_status:
        errors.append("safe_validation_status_drift")
    return {
        "task_id": TASK_ID,
        "revision_entry_count": len(entries),
        "ready_for_operator_review_count": ready_count,
        "manual_private_edit_required_count": len(entries) - ready_count,
        "formal_decision_count_changed": safe_report.get("formal_decision_count_changed"),
        "reviewed_item_count_changed": safe_report.get("reviewed_item_count_changed"),
        "authority_write_count": safe_report.get("authority_write_count"),
        "safe_leakage_count": sum("leakage" in error for error in errors),
        "error_count": len(errors),
        "errors": errors,
        "validation_status": expected_status if not errors else "FAIL_PRIVATE_REVISION_EVIDENCE",
        "next_resume_task": "E4S-A1V1-M04B3_PrivateRevisionOperatorReviewAndApproval",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-bank", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--materialized-decisions", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--safe-report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        private_output, safe_report = build_revision_evidence(
            read_json(args.private_bank),
            read_json(args.review_queue),
            read_json(args.materialized_decisions),
        )
        validation = validate_revision_evidence(private_output, safe_report)
        if validation["error_count"]:
            raise RevisionEvidenceError(str(validation["errors"]))
        write_json_atomic(args.private_output, private_output)
        write_json_atomic(args.safe_report, safe_report)
        print(json.dumps(validation, sort_keys=True))
        print(f"private_output={args.private_output}")
        print(f"safe_report={args.safe_report}")
        return 0
    except (RevisionEvidenceError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
