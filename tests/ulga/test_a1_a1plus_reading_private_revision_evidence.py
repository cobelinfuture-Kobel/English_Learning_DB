from __future__ import annotations

import copy

import pytest

from ulga.builders import build_a1_a1plus_reading_private_revision_evidence as module


def _candidate(selection_id: str, question_type: str, answer: str = "play") -> dict:
    if question_type == "cloze_vocabulary":
        return {
            "item_id": f"{selection_id}__CLOZE",
            "question_type": question_type,
            "status": "PRIVATE_REVIEW_CANDIDATE",
            "prompt": f"Complete the local source sentence: We ____.",
            "answer_model": {
                "answer_type": "normalized_text",
                "answer_key": answer,
                "case_sensitive": False,
            },
            "source_sentence_ids": ["S1"],
            "deterministic_scoring_ready": True,
        }
    return {
        "item_id": f"{selection_id}__ORDER",
        "question_type": question_type,
        "status": "PRIVATE_REVIEW_CANDIDATE",
        "prompt": "Put the local source sentences in their original order.",
        "display_order": [{"sentence_id": "S1", "sentence": "placeholder"}],
        "answer_model": {"answer_type": "ordered_ids", "answer_key": ["S1"]},
        "source_sentence_ids": ["S1"],
        "deterministic_scoring_ready": True,
    }


def _record(selection_number: int, source_text: str = "Unused.", answer: str = "unused") -> dict:
    selection_id = f"E4S_A1V1_READING_SOURCE_{selection_number:03d}"
    candidates = [
        _candidate(selection_id, "cloze_vocabulary", answer),
        _candidate(selection_id, "sentence_ordering"),
    ]
    return {
        "selection": {
            "selection_id": selection_id,
            "content_sha256": f"{selection_number % 16:x}" * 64,
        },
        "source_text": source_text,
        "source_sentences": [{"sentence_id": "S1", "sentence": source_text}],
        "source_integrity": {"status": "PASS", "errors": []},
        "deterministic_items": candidates,
    }


def _artifacts() -> tuple[dict, dict, dict]:
    records = [_record(index) for index in range(1, 55)]
    records[32] = _record(33, '"We play." Then we rest.', "play")
    records[33] = _record(34, 'Katie said, "Run!" We ran home.', "ran")
    private_bank = {
        "artifact_type": "local_private_source_grounded_reading_review_candidates",
        "records": records,
    }

    entries = []
    decisions = []
    for source_number, answer in ((33, "play"), (34, "ran")):
        selection_id = f"E4S_A1V1_READING_SOURCE_{source_number:03d}"
        record = records[source_number - 1]
        source_hash = record["selection"]["content_sha256"]
        for question_type in module.TARGET_QUESTION_TYPES:
            candidate = _candidate(selection_id, question_type, answer)
            candidate_id = candidate["item_id"]
            entry_id = f"M04B3_REVIEW_{source_number:02X}{question_type.encode().hex().upper()[:18]:0<18}"
            entry_id = entry_id[:33]
            entries.append({
                "review_entry_id": entry_id,
                "selection_id": selection_id,
                "source_unit_ref": f"RAZ_TEST_{source_number}",
                "candidate_id": candidate_id,
                "question_type": question_type,
                "source_integrity": {"content_sha256": source_hash},
                "candidate_payload_sha256": module.sha256_value(candidate),
                "candidate_content": candidate,
                "source_evidence": {"source_sentence_ids": ["S1"]},
            })
            decisions.append({
                "review_entry_id": entry_id,
                "candidate_id": candidate_id,
                "source_content_sha256": source_hash,
                "candidate_payload_sha256": module.sha256_value(candidate),
                "decision": "PENDING",
                "reviewer_id": None,
                "reviewed_at": None,
                "criteria": {},
                "revision": None,
                "rejection_reasons": [],
                "review_notes": (
                    "OPERATOR_BATCH_DISPOSITION_ACKNOWLEDGED;"
                    "TARGET_DECISION=APPROVE_WITH_REVISION;"
                    "REVISION_EVIDENCE_REQUIRED;NOT_YET_FORMALLY_APPROVED"
                ),
            })
    queue = {
        "review_entry_count": len(entries),
        "review_entries": entries,
        "review_entries_sha256": module.sha256_value(entries),
    }
    registry = {
        "review_queue_sha256": module.sha256_value(queue),
        "decisions": decisions,
    }
    return private_bank, queue, registry


@pytest.fixture(autouse=True)
def _stub_schema(monkeypatch):
    monkeypatch.setattr(module, "_assert_schema", lambda *_args, **_kwargs: None)


def test_quote_aware_split_keeps_closing_quotes() -> None:
    assert module.split_sentences_quote_aware('"We play." Then we rest.') == [
        '"We play."',
        "Then we rest.",
    ]
    assert module.split_sentences_quote_aware('Katie said, "Run!" We ran home.') == [
        'Katie said, "Run!"',
        "We ran home.",
    ]


def test_builds_exact_four_ready_private_revisions() -> None:
    private_bank, queue, registry = _artifacts()
    private_output, safe = module.build_revision_evidence(
        private_bank,
        queue,
        registry,
        require_production_counts=False,
    )
    result = module.validate_revision_evidence(private_output, safe)
    assert result["error_count"] == 0
    assert result["revision_entry_count"] == 4
    assert result["ready_for_operator_review_count"] == 4
    assert result["manual_private_edit_required_count"] == 0
    assert result["formal_decision_count_changed"] == 0
    assert result["authority_write_count"] == 0
    assert safe["validation_status"] == "PASS_PRIVATE_REVISION_EVIDENCE_READY_FOR_OPERATOR_REVIEW"
    assert {row["formal_decision"] for row in private_output["revision_entries"]} == {"PENDING"}


def test_cloze_revisions_preserve_key_and_add_blank() -> None:
    private_bank, queue, registry = _artifacts()
    private_output, _safe = module.build_revision_evidence(
        private_bank,
        queue,
        registry,
        require_production_counts=False,
    )
    cloze = [row for row in private_output["revision_entries"] if row["question_type"] == "cloze_vocabulary"]
    assert len(cloze) == 2
    assert all("____" in row["proposed_revision"]["prompt"] for row in cloze)
    assert {row["proposed_revision"]["answer_model"]["answer_key"] for row in cloze} == {"play", "ran"}
    assert all(row["proposed_revision"]["source_sentence_ids"] == ["S1"] for row in cloze)


def test_ordering_revisions_use_nonidentity_quote_aware_segments() -> None:
    private_bank, queue, registry = _artifacts()
    private_output, _safe = module.build_revision_evidence(
        private_bank,
        queue,
        registry,
        require_production_counts=False,
    )
    ordering = [row for row in private_output["revision_entries"] if row["question_type"] == "sentence_ordering"]
    assert len(ordering) == 2
    for row in ordering:
        revision = row["proposed_revision"]
        correct = revision["answer_model"]["answer_key"]
        displayed = [item["sentence_id"] for item in revision["display_order"]]
        assert correct == ["R1", "R2"]
        assert displayed == ["R2", "R1"]
        assert revision["accepted_answers"] == [["R1", "R2"]]
        assert revision["source_sentence_ids"] == ["S1"]


def test_source_hash_drift_fails_closed() -> None:
    private_bank, queue, registry = _artifacts()
    broken = copy.deepcopy(registry)
    broken["decisions"][0]["source_content_sha256"] = "f" * 64
    with pytest.raises(module.RevisionEvidenceError, match="decision_source_hash_drift"):
        module.build_revision_evidence(
            private_bank,
            queue,
            broken,
            require_production_counts=False,
        )


def test_safe_report_contains_no_private_fields() -> None:
    private_bank, queue, registry = _artifacts()
    _private_output, safe = module.build_revision_evidence(
        private_bank,
        queue,
        registry,
        require_production_counts=False,
    )
    encoded = str(safe).lower()
    for forbidden in ("source_text", "original_source_sentences", "proposed_revision", "prompt", "answer_model"):
        assert forbidden not in encoded
