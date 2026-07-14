from __future__ import annotations

from collections import Counter

import pytest

from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (
    is_forbidden_safe_key,
)
from ulga.builders.materialize_a1_a1plus_reading_operator_decisions import NOTE_RE
from ulga.builders.rebuild_a1_a1plus_reading_ai_assisted_triage import (
    EXPECTED_PROPOSALS,
    PROPER_NAME_CLOZE_SELECTIONS,
    REVISION_SELECTIONS,
    TriageRebuildError,
    proposal_for,
    proposal_note,
)


def _entry(source: int, question_type: str) -> dict:
    return {
        "selection_id": f"E4S_A1V1_READING_SOURCE_{source:03d}",
        "question_type": question_type,
    }


def _synthetic_entries() -> list[dict]:
    entries: list[dict] = []
    for source in range(1, 55):
        entries.append(_entry(source, "true_false"))
        entries.append(_entry(source, "cloze_vocabulary"))

    ordering_sources = [*range(1, 33), 33, 34, 53, 54]
    entries.extend(_entry(source, "sentence_ordering") for source in ordering_sources)

    entries.extend(_entry(source, "literal_who") for source in range(1, 50))
    entries.extend(_entry(source, "literal_what") for source in range(1, 55))
    entries.extend(_entry(source, "literal_where") for source in range(1, 35))
    return entries


def test_exact_281_entry_distribution() -> None:
    entries = _synthetic_entries()
    assert len(entries) == 281
    counts = Counter(proposal_for(entry)[0] for entry in entries)
    assert {key: counts[key] for key in EXPECTED_PROPOSALS} == EXPECTED_PROPOSALS


def test_exact_eight_proper_name_cloze_sources() -> None:
    assert PROPER_NAME_CLOZE_SELECTIONS == {
        "E4S_A1V1_READING_SOURCE_010",
        "E4S_A1V1_READING_SOURCE_011",
        "E4S_A1V1_READING_SOURCE_022",
        "E4S_A1V1_READING_SOURCE_032",
        "E4S_A1V1_READING_SOURCE_042",
        "E4S_A1V1_READING_SOURCE_047",
        "E4S_A1V1_READING_SOURCE_049",
        "E4S_A1V1_READING_SOURCE_052",
    }
    for selection_id in PROPER_NAME_CLOZE_SELECTIONS:
        decision, reasons = proposal_for({
            "selection_id": selection_id,
            "question_type": "cloze_vocabulary",
        })
        assert decision == "REJECT"
        assert "PROPER_NAME_OR_TITLE_USED_AS_VOCABULARY_TARGET" in reasons


def test_sources_033_and_034_require_two_revisions_each() -> None:
    assert REVISION_SELECTIONS == {
        "E4S_A1V1_READING_SOURCE_033",
        "E4S_A1V1_READING_SOURCE_034",
    }
    decisions = [
        proposal_for({"selection_id": source, "question_type": question_type})[0]
        for source in REVISION_SELECTIONS
        for question_type in ("cloze_vocabulary", "sentence_ordering")
    ]
    assert decisions == ["APPROVE_WITH_REVISION"] * 4


def test_source_053_ordering_is_deferred() -> None:
    decision, reasons = proposal_for(_entry(53, "sentence_ordering"))
    assert decision == "DEFER"
    assert "FULL_PASSAGE_CONTEXT_REQUIRED" in reasons


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (_entry(1, "true_false"), "REJECT"),
        (_entry(1, "cloze_vocabulary"), "APPROVE_AS_IS"),
        (_entry(1, "sentence_ordering"), "APPROVE_AS_IS"),
        (_entry(1, "literal_who"), "DEFER"),
        (_entry(1, "literal_what"), "DEFER"),
        (_entry(1, "literal_where"), "DEFER"),
    ],
)
def test_question_type_rules(entry: dict, expected: str) -> None:
    assert proposal_for(entry)[0] == expected


def test_notes_satisfy_materializer_contract() -> None:
    for entry in _synthetic_entries():
        decision, reasons = proposal_for(entry)
        note = proposal_note(decision, reasons)
        assert NOTE_RE.fullmatch(note)


def test_reject_and_defer_reason_codes_are_safe_report_keys() -> None:
    for entry in _synthetic_entries():
        decision, reasons = proposal_for(entry)
        if decision not in {"REJECT", "DEFER"}:
            continue
        assert all(not is_forbidden_safe_key(reason) for reason in reasons)


def test_unknown_question_type_fails_closed() -> None:
    with pytest.raises(TriageRebuildError, match="unsupported_question_type"):
        proposal_for(_entry(1, "unknown"))
