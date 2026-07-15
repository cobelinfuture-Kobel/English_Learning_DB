from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m04_reading_promotion_closeout_receipt as module


def _artifacts() -> tuple[dict, dict, dict, dict, dict, dict]:
    entries = [
        {
            "review_entry_id": f"M04B3_REVIEW_{index:020X}",
            "selection_id": f"E4S_A1V1_READING_SOURCE_{(index % 54) + 1:03d}",
        }
        for index in range(281)
    ]
    queue = {
        "review_entry_count": 281,
        "review_entries": entries,
        "review_entries_sha256": module.sha256_value(entries),
    }

    decision_values = (
        ["APPROVE_AS_IS"] * 77
        + ["APPROVE_WITH_REVISION"] * 4
        + ["REJECT"] * 62
        + ["DEFER"] * 138
    )
    decisions = {
        "review_queue_sha256": module.sha256_value(queue),
        "decisions": [
            {
                "review_entry_id": entries[index]["review_entry_id"],
                "decision": value,
            }
            for index, value in enumerate(decision_values)
        ],
    }

    reviewed_items = [
        {
            "reviewed_item_id": f"M04B3_ITEM_{index:020X}",
            "selection_id": f"E4S_A1V1_READING_SOURCE_{(index % 54) + 1:03d}",
            "question_type": "cloze_vocabulary" if index < 46 else "sentence_ordering",
        }
        for index in range(81)
    ]
    bank = {
        "reviewed_item_count": 81,
        "reviewed_items": reviewed_items,
        "reviewed_items_sha256": module.sha256_value(reviewed_items),
    }
    promotion = {
        "decision_counts": dict(module.EXPECTED_DECISIONS),
        "reviewed_item_count": 81,
        "promotion_claim_count": 0,
        "validation_status": "PASS",
        "claim_boundaries": {
            "private_local_only": True,
            "canonical_authority_promotion": False,
            "public_learner_delivery": False,
            "source_text_public_export": False,
            "m04b1_m04b2_mutated": False,
        },
    }
    approval_safe = {
        "validation_status": "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE",
        "review_queue_sha256": module.sha256_value(queue),
        "final_registry_sha256": module.sha256_value(decisions),
        "final_bank_sha256": module.sha256_value(bank),
        "decision_counts_after": dict(module.EXPECTED_DECISIONS),
        "final_reviewed_item_count": 81,
        "pending_decision_count": 0,
        "canonical_authority_write_count": 0,
        "public_delivery_count": 0,
        "automatic_approval_performed": False,
    }
    approval_validation = {
        "validation_status": "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE",
        "approved_as_is_count": 77,
        "approved_with_revision_count": 4,
        "rejected_count": 62,
        "deferred_count": 138,
        "pending_count": 0,
        "reviewed_item_count": 81,
        "authority_write_count": 0,
        "public_delivery_count": 0,
        "error_count": 0,
    }
    return queue, decisions, bank, promotion, approval_safe, approval_validation


@pytest.fixture(autouse=True)
def _stub_contracts(monkeypatch):
    monkeypatch.setattr(module, "_assert_schema", lambda *_args, **_kwargs: None)

    def fake_apply(_queue, _decisions):
        artifacts = _artifacts()
        return copy.deepcopy(artifacts[2]), copy.deepcopy(artifacts[3])

    monkeypatch.setattr(module, "apply_artifacts", fake_apply)


def _build() -> tuple[tuple[dict, dict, dict, dict, dict, dict], dict]:
    artifacts = _artifacts()
    receipt = module.build_receipt(*artifacts)
    return artifacts, receipt


def test_builds_complete_metadata_only_closeout_receipt() -> None:
    _artifacts_tuple, receipt = _build()
    assert receipt["validation_status"] == module.PASS_STATUS
    assert receipt["reading_completion"]["review_entry_count"] == 281
    assert receipt["reading_completion"]["selected_source_count"] == 54
    assert receipt["reading_completion"]["reviewed_item_count"] == 81
    assert receipt["reading_completion"]["pending_count"] == 0
    assert receipt["reading_completion"]["final_decision_counts"] == module.EXPECTED_DECISIONS
    assert receipt["m04_gate"]["reading_v1_complete"] is True
    assert receipt["m04_gate"]["m05_progression_allowed"] is True
    assert receipt["next_short_step"] == module.NEXT_SHORT_STEP


def test_receipt_contains_no_private_content_fields() -> None:
    _artifacts_tuple, receipt = _build()
    encoded = str(receipt).lower()
    for forbidden in (
        "source_text",
        "candidate_content",
        "final_private_prompt",
        "final_private_answer_model",
        "accepted_answers",
        "review_notes",
        "proposed_revision",
        "revision_payload",
    ):
        assert forbidden not in encoded


def test_receipt_is_independently_reproducible() -> None:
    artifacts, receipt = _build()
    result = module.validate_receipt(*artifacts, receipt)
    assert result["error_count"] == 0
    assert result["reading_v1_complete"] is True
    assert result["m05_progression_allowed"] is True
    assert result["reviewed_item_count"] == 81


def test_pending_decision_fails_closed() -> None:
    artifacts = list(_artifacts())
    artifacts[1]["decisions"][0]["decision"] = "PENDING"
    artifacts[4]["final_registry_sha256"] = module.sha256_value(artifacts[1])
    with pytest.raises(module.ReadingCloseoutError, match="final_decision_distribution"):
        module.build_receipt(*artifacts)


def test_approval_hash_drift_fails_closed() -> None:
    artifacts = list(_artifacts())
    artifacts[4]["final_bank_sha256"] = "f" * 64
    with pytest.raises(module.ReadingCloseoutError, match="approval_bank_hash"):
        module.build_receipt(*artifacts)


def test_authority_or_public_boundary_fails_closed() -> None:
    artifacts = list(_artifacts())
    artifacts[4]["canonical_authority_write_count"] = 1
    with pytest.raises(module.ReadingCloseoutError, match="approval_authority_write_count"):
        module.build_receipt(*artifacts)

    artifacts = list(_artifacts())
    artifacts[3]["claim_boundaries"]["public_learner_delivery"] = True
    with pytest.raises(module.ReadingCloseoutError, match="promotion_report_not_reproducible"):
        module.build_receipt(*artifacts)


def test_tampered_receipt_is_rejected() -> None:
    artifacts, receipt = _build()
    broken = copy.deepcopy(receipt)
    broken["reading_completion"]["reviewed_item_count"] = 80
    result = module.validate_receipt(*artifacts, broken)
    assert result["error_count"] == 1
    assert "closeout_receipt_not_reproducible" in result["errors"]
    assert result["m05_progression_allowed"] is False


def test_direct_cli_help_works_outside_repository(tmp_path: Path) -> None:
    script = Path(module.__file__).resolve()
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "--approval-validation" in result.stdout
