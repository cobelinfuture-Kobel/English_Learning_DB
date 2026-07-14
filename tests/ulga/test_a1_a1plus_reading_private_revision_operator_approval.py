from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.builders import materialize_a1_a1plus_reading_private_revision_operator_approval as module


def _decision(index: int, entry: dict) -> dict:
    base = {
        "review_entry_id": entry["review_entry_id"],
        "candidate_id": entry["candidate_id"],
        "source_content_sha256": entry["source_integrity"]["content_sha256"],
        "candidate_payload_sha256": entry["candidate_payload_sha256"],
        "reviewer_id": "operator:cobelinfuture-Kobel",
        "reviewed_at": "2026-07-15T00:30:00+08:00",
        "criteria": {key: True for key in entry["review_requirements"]},
        "revision": None,
        "rejection_reasons": [],
        "review_notes": "PRIOR_OPERATOR_DECISION",
    }
    if index < 77:
        base["decision"] = "APPROVE_AS_IS"
    elif index < 81:
        base.update(
            decision="PENDING",
            reviewer_id=None,
            reviewed_at=None,
            criteria={},
            review_notes=(
                "OPERATOR_BATCH_DISPOSITION_ACKNOWLEDGED;"
                "TARGET_DECISION=APPROVE_WITH_REVISION;"
                "REASON_CODES=PRIVATE_SOURCE_REVISION_REQUIRED;"
                "REVISION_EVIDENCE_REQUIRED;NOT_YET_FORMALLY_APPROVED"
            ),
        )
    elif index < 143:
        base.update(decision="REJECT", rejection_reasons=["ALL_TRUE_BANK_BIAS"])
    else:
        base.update(decision="DEFER", rejection_reasons=["PRIVATE_EVIDENCE_REVIEW_REQUIRED"])
    return base


def _reviewed_item(index: int) -> dict:
    return {
        "reviewed_item_id": f"ITEM_{index:03d}",
        "stable_payload": f"prior-{index:03d}",
    }


def _artifacts() -> tuple[dict, dict, dict, dict, dict]:
    entries = []
    for index in range(281):
        entry_id = f"M04B3_REVIEW_{index:020X}"
        entries.append({
            "review_entry_id": entry_id,
            "selection_id": f"E4S_A1V1_READING_SOURCE_{index % 54 + 1:03d}",
            "source_unit_ref": f"SOURCE_{index:03d}",
            "candidate_id": f"CAND_{index:03d}",
            "question_type": "cloze_vocabulary" if index % 2 == 0 else "sentence_ordering",
            "source_integrity": {"content_sha256": f"{index % 16:x}" * 64},
            "candidate_payload_sha256": f"{(index + 1) % 16:x}" * 64,
            "source_evidence": {"source_sentence_ids": ["S1"]},
            "review_requirements": ["source_grounding_verified", "copyright_boundary_accepted"],
        })
    queue = {
        "review_entry_count": 281,
        "review_entries": entries,
        "review_entries_sha256": module.sha256_value(entries),
    }
    prior_decisions = {
        "review_queue_sha256": module.sha256_value(queue),
        "decisions": [_decision(index, entry) for index, entry in enumerate(entries)],
    }
    prior_items = [_reviewed_item(index) for index in range(77)]
    prior_bank = {
        "source_review_queue_sha256": module.sha256_value(queue),
        "source_decisions_sha256": module.sha256_value(prior_decisions),
        "reviewed_item_count": 77,
        "reviewed_items": prior_items,
        "reviewed_items_sha256": module.sha256_value(prior_items),
    }
    revisions = []
    for index in range(77, 81):
        entry = entries[index]
        revisions.append({
            "review_entry_id": entry["review_entry_id"],
            "candidate_id": entry["candidate_id"],
            "selection_id": entry["selection_id"],
            "source_unit_ref": entry["source_unit_ref"],
            "question_type": entry["question_type"],
            "source_content_sha256": entry["source_integrity"]["content_sha256"],
            "candidate_payload_sha256": entry["candidate_payload_sha256"],
            "proposed_revision": {
                "prompt": f"Revised private prompt {index}",
                "answer_model": {"answer_type": "normalized_text", "answer_key": "test"},
                "accepted_answers": ["test"],
                "source_sentence_ids": ["S1"],
            },
            "revision_status": "READY_FOR_OPERATOR_REVIEW",
            "formal_decision": "PENDING",
            "operator_approval_recorded": False,
        })
    revision_private = {
        "revision_entry_count": 4,
        "revision_entries": revisions,
    }
    revision_safe = {"validation_status": "PASS_PRIVATE_REVISION_EVIDENCE_READY_FOR_OPERATOR_REVIEW"}
    return queue, prior_decisions, prior_bank, revision_private, revision_safe


@pytest.fixture(autouse=True)
def _stub_external_contracts(monkeypatch):
    monkeypatch.setattr(module, "_assert_schema", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        module,
        "validate_revision_evidence",
        lambda *_args, **_kwargs: {
            "validation_status": "PASS_PRIVATE_REVISION_EVIDENCE_READY_FOR_OPERATOR_REVIEW",
            "revision_entry_count": 4,
            "ready_for_operator_review_count": 4,
            "errors": [],
        },
    )

    def fake_apply(queue, registry):
        counts = module._decision_counts(registry)
        items = [_reviewed_item(index) for index in range(77)]
        revised = [row for row in registry["decisions"] if row["decision"] == "APPROVE_WITH_REVISION"]
        items.extend(
            {
                "reviewed_item_id": f"REVISED_{row['review_entry_id']}",
                "decision_sha256": module.sha256_value(row),
            }
            for row in revised
        )
        bank = {
            "source_review_queue_sha256": module.sha256_value(queue),
            "source_decisions_sha256": module.sha256_value(registry),
            "reviewed_item_count": len(items),
            "reviewed_items": items,
            "reviewed_items_sha256": module.sha256_value(items),
        }
        promotion = {
            "decision_counts": counts,
            "reviewed_item_count": len(items),
            "validation_status": "PASS" if counts["PENDING"] == 0 else "PASS_PENDING_OPERATOR_REVIEW",
        }
        return bank, promotion

    monkeypatch.setattr(module, "apply_artifacts", fake_apply)


def _run():
    queue, decisions, bank, revisions, revision_safe = _artifacts()
    outputs = module.approve_private_revisions(
        queue,
        decisions,
        bank,
        revisions,
        revision_safe,
        reviewer_id="operator:cobelinfuture-Kobel",
        reviewed_at="2026-07-15T00:45:00+08:00",
        approval_token=module.APPROVAL_TOKEN,
    )
    return (queue, decisions, bank, revisions, revision_safe), outputs


def test_approves_exact_four_revisions_and_builds_81_item_bank() -> None:
    _inputs, (decisions, bank, promotion, safe) = _run()
    assert module._decision_counts(decisions) == module.EXPECTED_AFTER
    assert bank["reviewed_item_count"] == 81
    assert promotion["validation_status"] == "PASS"
    assert safe["revised_decision_count"] == 4
    assert safe["prior_reviewed_item_preserved_count"] == 77
    assert safe["pending_decision_count"] == 0
    assert safe["validation_status"] == "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE"


def test_revised_rows_record_operator_criteria_and_private_revision() -> None:
    _inputs, (decisions, _bank, _promotion, _safe) = _run()
    rows = [row for row in decisions["decisions"] if row["decision"] == "APPROVE_WITH_REVISION"]
    assert len(rows) == 4
    assert all(row["reviewer_id"] == "operator:cobelinfuture-Kobel" for row in rows)
    assert all(row["reviewed_at"].endswith("+08:00") for row in rows)
    assert all(row["criteria"] == {
        "source_grounding_verified": True,
        "copyright_boundary_accepted": True,
    } for row in rows)
    assert all(row["revision"]["accepted_answers"] == ["test"] for row in rows)


def test_prior_77_reviewed_items_are_preserved_exactly() -> None:
    (_queue, _decisions, prior_bank, _revisions, _safe), (_final_decisions, final_bank, _promotion, _approval) = _run()
    assert final_bank["reviewed_items"][:77] == prior_bank["reviewed_items"]


def test_explicit_approval_token_and_timezone_are_required() -> None:
    queue, decisions, bank, revisions, revision_safe = _artifacts()
    with pytest.raises(module.RevisionApprovalError, match="explicit_private_revision_approval_token_required"):
        module.approve_private_revisions(
            queue, decisions, bank, revisions, revision_safe,
            reviewer_id="operator:test", reviewed_at="2026-07-15T00:45:00+08:00", approval_token="continue",
        )
    with pytest.raises(module.RevisionApprovalError, match="reviewed_at_timezone_required"):
        module.approve_private_revisions(
            queue, decisions, bank, revisions, revision_safe,
            reviewer_id="operator:test", reviewed_at="2026-07-15T00:45:00", approval_token=module.APPROVAL_TOKEN,
        )


def test_revision_hash_or_pending_set_drift_fails_closed() -> None:
    queue, decisions, bank, revisions, revision_safe = _artifacts()
    broken = copy.deepcopy(revisions)
    broken["revision_entries"][0]["candidate_payload_sha256"] = "f" * 64
    with pytest.raises(module.RevisionApprovalError, match="private_revision_candidate_hash_drift"):
        module.approve_private_revisions(
            queue, decisions, bank, broken, revision_safe,
            reviewer_id="operator:test", reviewed_at="2026-07-15T00:45:00+08:00", approval_token=module.APPROVAL_TOKEN,
        )


def test_independent_validation_reproduces_final_outputs() -> None:
    (queue, _prior_decisions, prior_bank, _revisions, _revision_safe), (decisions, bank, promotion, safe) = _run()
    result = module.validate_approval_outputs(queue, prior_bank, decisions, bank, promotion, safe)
    assert result["error_count"] == 0
    assert result["approved_with_revision_count"] == 4
    assert result["pending_count"] == 0
    assert result["reviewed_item_count"] == 81
    assert result["validation_status"] == "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE"


def test_direct_cli_help_works_outside_repository(tmp_path: Path) -> None:
    script = Path(module.__file__).resolve()
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--approval-token" in result.stdout
