from __future__ import annotations

import copy

import pytest

from ulga.builders import materialize_a1_a1plus_reading_operator_decisions as module


def _proposal(index: int) -> str:
    if index < 77:
        return "APPROVE_AS_IS"
    if index < 81:
        return "APPROVE_WITH_REVISION"
    if index < 143:
        return "REJECT"
    return "DEFER"


def _reasons(proposal: str) -> list[str]:
    return {
        "APPROVE_AS_IS": ["SOURCE_RECALL_CLOZE_ACCEPTABLE", "NO_BLOCK_PRECHECK"],
        "APPROVE_WITH_REVISION": ["PRIVATE_SOURCE_REVISION_REQUIRED"],
        "REJECT": ["ALL_TRUE_BANK_BIAS"],
        "DEFER": ["SOURCE_SENTENCE_TEXT_NOT_PRESENT_IN_REVIEW_ENTRY"],
    }[proposal]


def _artifacts() -> tuple[dict, dict]:
    entries = []
    decisions = []
    for index in range(281):
        proposal = _proposal(index)
        qtype = "cloze_vocabulary"
        if proposal == "APPROVE_WITH_REVISION":
            qtype = "sentence_ordering"
        elif proposal == "REJECT":
            qtype = "true_false"
        elif proposal == "DEFER":
            qtype = "literal_what"
        entry_id = f"M04B3_REVIEW_{index:020X}"
        candidate_id = f"CAND_{index:03d}"
        source_hash = f"{index % 16:x}" * 64
        payload_hash = f"{(index + 1) % 16:x}" * 64
        entries.append({
            "review_entry_id": entry_id,
            "candidate_id": candidate_id,
            "question_type": qtype,
            "source_integrity": {"content_sha256": source_hash},
            "candidate_payload_sha256": payload_hash,
            "automated_prechecks": {"overall_status": "WARNING" if proposal == "DEFER" else "PASS"},
            "review_requirements": ["source_grounding_verified", "copyright_boundary_accepted"],
        })
        reasons = _reasons(proposal)
        decisions.append({
            "review_entry_id": entry_id,
            "candidate_id": candidate_id,
            "source_content_sha256": source_hash,
            "candidate_payload_sha256": payload_hash,
            "decision": "PENDING",
            "reviewer_id": None,
            "reviewed_at": None,
            "criteria": {},
            "revision": None,
            "rejection_reasons": [],
            "review_notes": (
                "AI_ASSISTED_TRIAGE_ONLY;"
                f"PROPOSED_DECISION={proposal};"
                f"REASON_CODES={','.join(reasons)};"
                "NOT_OPERATOR_APPROVAL"
            ),
        })
    queue = {
        "review_entry_count": 281,
        "review_entries": entries,
        "review_entries_sha256": module.sha256_value(entries),
    }
    triage = {
        "review_queue_sha256": module.sha256_value(queue),
        "decisions": decisions,
    }
    return queue, triage


@pytest.fixture(autouse=True)
def _stub_external_contracts(monkeypatch):
    monkeypatch.setattr(module, "_assert_schema", lambda *_args, **_kwargs: None)

    def fake_apply(_queue, registry):
        counts = {key: 0 for key in module.DECISION_VALUES}
        for row in registry["decisions"]:
            counts[row["decision"]] += 1
        assert counts == module.EXPECTED_MATERIALIZED
        return (
            {"reviewed_item_count": 77, "reviewed_items": [{} for _ in range(77)]},
            {
                "decision_counts": counts,
                "validation_status": "PASS_PENDING_OPERATOR_REVIEW",
            },
        )

    monkeypatch.setattr(module, "apply_artifacts", fake_apply)


def _run(queue: dict, triage: dict):
    return module.materialize(
        queue,
        triage,
        reviewer_id="operator:cobelinfuture-Kobel",
        reviewed_at="2026-07-14T23:20:47+08:00",
        approval_token=module.APPROVAL_TOKEN,
    )


def test_materializes_77_rejects_62_defers_138_and_keeps_four_pending():
    queue, triage = _artifacts()
    decisions, bank, promotion, safe = _run(queue, triage)
    counts = {key: 0 for key in module.DECISION_VALUES}
    for row in decisions["decisions"]:
        counts[row["decision"]] += 1
    assert counts == module.EXPECTED_MATERIALIZED
    assert bank["reviewed_item_count"] == 77
    assert promotion["validation_status"] == "PASS_PENDING_OPERATOR_REVIEW"
    assert safe["proposal_counts"] == module.EXPECTED_PROPOSALS
    assert safe["pending_revision_evidence_count"] == 4
    assert safe["validation_status"] == "PASS_77_PROMOTED_4_REVISION_EVIDENCE_PENDING"


def test_revision_proposals_are_not_falsely_approved():
    queue, triage = _artifacts()
    decisions, _bank, _promotion, _safe = _run(queue, triage)
    rows = [row for row in decisions["decisions"] if "TARGET_DECISION=APPROVE_WITH_REVISION" in (row["review_notes"] or "")]
    assert len(rows) == 4
    assert all(row["decision"] == "PENDING" for row in rows)
    assert all(row["reviewer_id"] is None and row["reviewed_at"] is None for row in rows)
    assert all("REVISION_EVIDENCE_REQUIRED" in row["review_notes"] for row in rows)


def test_formal_rows_record_operator_and_all_review_requirements():
    queue, triage = _artifacts()
    decisions, _bank, _promotion, _safe = _run(queue, triage)
    formal = [row for row in decisions["decisions"] if row["decision"] != "PENDING"]
    assert len(formal) == 277
    assert all(row["reviewer_id"] == "operator:cobelinfuture-Kobel" for row in formal)
    assert all(row["reviewed_at"].endswith("+08:00") for row in formal)
    assert all(row["criteria"] == {"source_grounding_verified": True, "copyright_boundary_accepted": True} for row in formal)


def test_explicit_approval_token_is_required():
    queue, triage = _artifacts()
    with pytest.raises(module.MaterializationError, match="explicit_operator_approval_token_required"):
        module.materialize(
            queue,
            triage,
            reviewer_id="operator:cobelinfuture-Kobel",
            reviewed_at="2026-07-14T23:20:47+08:00",
            approval_token="continue",
        )


def test_timezone_aware_review_timestamp_is_required():
    queue, triage = _artifacts()
    with pytest.raises(module.MaterializationError, match="reviewed_at_timezone_required"):
        module.materialize(
            queue,
            triage,
            reviewer_id="operator:cobelinfuture-Kobel",
            reviewed_at="2026-07-14T23:20:47",
            approval_token=module.APPROVAL_TOKEN,
        )


def test_proposal_distribution_drift_fails_closed():
    queue, triage = _artifacts()
    triage["decisions"][0]["review_notes"] = triage["decisions"][0]["review_notes"].replace(
        "PROPOSED_DECISION=APPROVE_AS_IS", "PROPOSED_DECISION=DEFER"
    )
    with pytest.raises(module.MaterializationError, match="proposal_distribution_mismatch"):
        _run(queue, triage)


def test_source_hash_drift_fails_closed():
    queue, triage = _artifacts()
    triage["decisions"][0]["source_content_sha256"] = "f" * 64
    with pytest.raises(module.MaterializationError, match="source_hash_drift"):
        _run(queue, triage)


def test_candidate_hash_drift_fails_closed():
    queue, triage = _artifacts()
    triage["decisions"][0]["candidate_payload_sha256"] = "e" * 64
    with pytest.raises(module.MaterializationError, match="candidate_hash_drift"):
        _run(queue, triage)


def test_malformed_or_preapproved_triage_fails_closed():
    queue, triage = _artifacts()
    malformed = copy.deepcopy(triage)
    malformed["decisions"][0]["review_notes"] = "PROPOSED_DECISION=APPROVE_AS_IS"
    with pytest.raises(module.MaterializationError, match="triage_review_note_contract_invalid"):
        _run(queue, malformed)
    preapproved = copy.deepcopy(triage)
    preapproved["decisions"][0]["decision"] = "APPROVE_AS_IS"
    with pytest.raises(module.MaterializationError, match="triage_contains_formal_decision"):
        _run(queue, preapproved)


def test_literal_approve_as_is_is_forbidden_even_with_correct_distribution():
    queue, triage = _artifacts()
    queue["review_entries"][0]["question_type"] = "literal_what"
    queue["review_entries_sha256"] = module.sha256_value(queue["review_entries"])
    triage["review_queue_sha256"] = module.sha256_value(queue)
    with pytest.raises(module.MaterializationError, match="literal_approve_as_is_forbidden"):
        _run(queue, triage)
