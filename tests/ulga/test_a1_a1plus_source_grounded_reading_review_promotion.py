from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (
    BANK_SCHEMA,
    CLAIM_BOUNDARIES,
    CRITERIA,
    DECISIONS_SCHEMA,
    DECISION_VALUES,
    EXPECTED_DETERMINISTIC,
    EXPECTED_LITERAL,
    QUEUE_SCHEMA,
    REPORT_SCHEMA,
    TASK_ID,
    PromotionBuildError,
    _validate_nonpending,
    _ordering_is_identity,
    apply_artifacts,
    prepare_artifacts,
    sha256_file,
    sha256_value,
)
from ulga.validators.validate_a1_a1plus_source_grounded_reading_review_promotion import (
    _identity_errors,
    safe_scan,
    validate_apply,
)

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / ".local/e4s_a1v1/reading/m04b3"
QTYPES = [
    *("true_false" for _ in range(54)),
    *("cloze_vocabulary" for _ in range(54)),
    *("sentence_ordering" for _ in range(36)),
    *("literal_who" for _ in range(49)),
    *("literal_what" for _ in range(54)),
    *("literal_where" for _ in range(34)),
]


def _entry(index: int, qtype: str) -> dict:
    literal = qtype.startswith("literal_")
    candidate = {
        "candidate_id": f"CAND_{index:03d}", "question_type": qtype,
        "source_sentence_ids": ["S1"], "auto_answer_generated": False,
        "status": "PENDING_OPERATOR_QUESTION_AND_ANSWER_REVIEW",
    } if literal else {
        "item_id": f"CAND_{index:03d}", "question_type": qtype,
        "source_sentence_ids": ["S1"], "prompt": f"Prompt {index}",
        "answer_model": {"answer_type": "normalized_text", "answer_key": f"answer-{index}"},
        "deterministic_scoring_ready": True, "status": "PRIVATE_REVIEW_CANDIDATE",
    }
    if qtype == "cloze_vocabulary":
        candidate["prompt"] = f"Complete: ____ {index}"
    if qtype == "sentence_ordering":
        candidate["display_order"] = ["S2", "S1"]
        candidate["answer_model"] = {"answer_type": "ordered_ids", "correct_order": ["S1", "S2"]}
        candidate["source_sentence_ids"] = ["S1", "S2"]
    requirement_key = "literal" if literal else qtype
    return {
        "review_entry_id": f"M04B3_REVIEW_{index:020X}",
        "selection_id": f"E4S_A1V1_READING_SOURCE_{index % 54 + 1:03d}",
        "source_unit_ref": f"RAZ_A_{index + 1}_P1", "candidate_id": f"CAND_{index:03d}",
        "question_type": qtype,
        "candidate_origin": "M04B2_LITERAL_REVIEW" if literal else "M04B2_DETERMINISTIC",
        "source_integrity": {"content_sha256": "a" * 64, "record_sha256": "b" * 64, "status": "PASS"},
        "candidate_payload_sha256": sha256_value(candidate), "candidate_content": candidate,
        "source_evidence": {"source_sentence_ids": list(candidate["source_sentence_ids"])},
        "canonical_context": {},
        "observational_support": {"binding_sha256": "c" * 64, "consumer_decision": {}, "observations": {}},
        "automated_prechecks": {"overall_status": "PASS", "checks": [
            {"name": f"check_{number}", "status": "PASS", "code": "PASS"} for number in range(14)
        ]},
        "review_requirements": list(CRITERIA[requirement_key]),
        "review_status": "PENDING_OPERATOR_REVIEW", "promotion_status": "not_promoted",
    }


@pytest.fixture()
def artifacts() -> tuple[dict, dict]:
    entries = [_entry(index, qtype) for index, qtype in enumerate(QTYPES)]
    queue = {
        "task_id": TASK_ID, "schema_version": QUEUE_SCHEMA, "artifact_type": "private_reading_review_queue",
        "policy": {"private_local_only": True, "must_not_be_committed": True, "automatic_approval": False},
        "upstream_hashes": {"m04b2_private_sha256": "d" * 64},
        "review_entry_count": 281, "review_entries": entries,
        "review_entries_sha256": sha256_value(entries), "claim_boundaries": copy.deepcopy(CLAIM_BOUNDARIES),
    }
    decisions = {
        "task_id": TASK_ID, "schema_version": DECISIONS_SCHEMA, "artifact_type": "local_operator_decision_registry",
        "policy": {"private_local_only": True, "must_not_be_committed": True, "template_is_approval": False},
        "review_queue_sha256": sha256_value(queue),
        "decisions": [{
            "review_entry_id": row["review_entry_id"], "candidate_id": row["candidate_id"],
            "source_content_sha256": row["source_integrity"]["content_sha256"],
            "candidate_payload_sha256": row["candidate_payload_sha256"], "decision": "PENDING",
            "reviewer_id": None, "reviewed_at": None, "criteria": {}, "revision": None,
            "rejection_reasons": [], "review_notes": None,
        } for row in entries],
    }
    return queue, decisions


def _sync(queue: dict, decisions: dict) -> None:
    queue["review_entry_count"] = len(queue["review_entries"])
    queue["review_entries_sha256"] = sha256_value(queue["review_entries"])
    decisions["review_queue_sha256"] = sha256_value(queue)


def _decide(queue: dict, decisions: dict, index: int, value: str, *, revision: dict | None = None) -> None:
    entry, decision = queue["review_entries"][index], decisions["decisions"][index]
    decision.update({
        "decision": value, "reviewer_id": "operator-1", "reviewed_at": "2026-07-14T12:00:00+08:00",
        "source_content_sha256": entry["source_integrity"]["content_sha256"],
        "candidate_payload_sha256": entry["candidate_payload_sha256"],
        "criteria": {key: True for key in entry["review_requirements"]}, "revision": revision,
    })


def _revision(entry: dict) -> dict:
    return {
        "prompt": "Who is in the source?", "answer_model": {"answer_type": "normalized_text", "answer_key": "Sam"},
        "accepted_answers": ["Sam"], "source_sentence_ids": list(entry["source_evidence"]["source_sentence_ids"]),
    }


def test_complete_281_entry_queue(artifacts):
    queue, _ = artifacts
    assert len(queue["review_entries"]) == 281
    assert not _identity_errors(queue)


def test_missing_review_entry(artifacts):
    queue, _ = artifacts
    queue["review_entries"].pop()
    assert any("not_281" in error for error in _identity_errors(queue))


def test_duplicate_review_entry(artifacts):
    queue, _ = artifacts
    queue["review_entries"][1] = copy.deepcopy(queue["review_entries"][0])
    assert "duplicate_review_entry" in _identity_errors(queue)


def test_extra_review_entry(artifacts):
    queue, _ = artifacts
    queue["review_entries"].append(copy.deepcopy(queue["review_entries"][0]))
    assert any("not_281" in error for error in _identity_errors(queue))


def test_candidate_hash_drift_fails(artifacts):
    queue, decisions = artifacts
    queue["review_entries"][0]["candidate_content"]["prompt"] = "tampered"
    _sync(queue, decisions)
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    with pytest.raises(PromotionBuildError, match="stale_candidate_hash"):
        apply_artifacts(queue, decisions)


def test_source_hash_drift_fails(artifacts):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    decisions["decisions"][0]["source_content_sha256"] = "e" * 64
    with pytest.raises(PromotionBuildError, match="stale_source_hash"):
        apply_artifacts(queue, decisions)


def test_missing_s12d_binding_is_detected_by_prepare_local():
    if not (LOCAL / "review_queue.json").exists():
        pytest.skip("real local M04B3 queue unavailable")
    queue = json.loads((LOCAL / "review_queue.json").read_text(encoding="utf-8"))
    assert all(row["observational_support"]["binding_sha256"] for row in queue["review_entries"])


def test_pending_promotes_nothing(artifacts):
    queue, decisions = artifacts
    bank, report = apply_artifacts(queue, decisions)
    assert bank["reviewed_item_count"] == 0
    assert report["decision_counts"]["PENDING"] == 281


@pytest.mark.parametrize("field", ["reviewer_id", "reviewed_at"])
def test_approval_requires_reviewer_evidence(artifacts, field):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    decisions["decisions"][0][field] = None
    with pytest.raises(PromotionBuildError, match=field):
        apply_artifacts(queue, decisions)


def test_approval_stale_candidate_hash(artifacts):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    decisions["decisions"][0]["candidate_payload_sha256"] = "f" * 64
    with pytest.raises(PromotionBuildError, match="stale_candidate_hash"):
        apply_artifacts(queue, decisions)


def test_approval_incomplete_criteria(artifacts):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    decisions["decisions"][0]["criteria"].pop(next(iter(decisions["decisions"][0]["criteria"])))
    with pytest.raises(PromotionBuildError, match="criteria"):
        apply_artifacts(queue, decisions)


def test_block_precheck_cannot_be_overridden(artifacts):
    queue, decisions = artifacts
    queue["review_entries"][0]["automated_prechecks"]["overall_status"] = "BLOCK"
    _sync(queue, decisions)
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    with pytest.raises(PromotionBuildError, match="block_precheck"):
        apply_artifacts(queue, decisions)


def test_literal_approve_as_is_rejected(artifacts):
    queue, decisions = artifacts
    index = 144
    _decide(queue, decisions, index, "APPROVE_AS_IS")
    with pytest.raises(PromotionBuildError, match="literal_approve_as_is"):
        apply_artifacts(queue, decisions)


@pytest.mark.parametrize("missing", ["prompt", "answer_model"])
def test_literal_revision_requires_prompt_and_answer(artifacts, missing):
    queue, decisions = artifacts
    index = 144
    revision = _revision(queue["review_entries"][index])
    revision[missing] = None
    _decide(queue, decisions, index, "APPROVE_WITH_REVISION", revision=revision)
    with pytest.raises(PromotionBuildError, match=f"missing_{missing}"):
        apply_artifacts(queue, decisions)


def test_cloze_revised_accepted_answers_required(artifacts):
    queue, decisions = artifacts
    index = 54
    revision = _revision(queue["review_entries"][index])
    revision["accepted_answers"] = []
    _decide(queue, decisions, index, "APPROVE_WITH_REVISION", revision=revision)
    with pytest.raises(PromotionBuildError, match="accepted_answers"):
        apply_artifacts(queue, decisions)


def test_ordering_identity_display_rejected_by_precheck(artifacts):
    queue, decisions = artifacts
    entry = queue["review_entries"][108]
    entry["candidate_content"]["display_order"] = entry["candidate_content"]["answer_model"]["correct_order"]
    entry["candidate_payload_sha256"] = sha256_value(entry["candidate_content"])
    _sync(queue, decisions)
    assert _ordering_is_identity(entry["candidate_content"])
    with pytest.raises(PromotionBuildError, match="identity_ordering"):
        apply_artifacts(queue, decisions)


@pytest.mark.parametrize("decision_value", ["REJECT", "DEFER"])
def test_rejected_and_deferred_absent_from_bank(artifacts, decision_value):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, decision_value)
    bank, _ = apply_artifacts(queue, decisions)
    assert bank["reviewed_item_count"] == 0


def test_eligible_approved_deterministic_promoted(artifacts):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    bank, _ = apply_artifacts(queue, decisions)
    assert bank["reviewed_items"][0]["status"] == "REVIEWED_LOCAL_PRACTICE_ITEM"


def test_eligible_revised_literal_promoted(artifacts):
    queue, decisions = artifacts
    index = 144
    _decide(queue, decisions, index, "APPROVE_WITH_REVISION", revision=_revision(queue["review_entries"][index]))
    bank, _ = apply_artifacts(queue, decisions)
    assert bank["reviewed_items"][0]["question_type"] == "literal_who"


def test_duplicate_reviewed_item_detected(artifacts):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    bank, report = apply_artifacts(queue, decisions)
    bank["reviewed_items"].append(copy.deepcopy(bank["reviewed_items"][0]))
    result = validate_apply(queue, decisions, bank, report)
    assert "duplicate_reviewed_item" in result["errors"]


def test_unapproved_reviewed_item_detected(artifacts):
    queue, decisions = artifacts
    bank, report = apply_artifacts(queue, decisions)
    bank["reviewed_items"] = [{"reviewed_item_id": "M04B3_ITEM_" + "A" * 20}]
    bank["reviewed_item_count"] = 1
    bank["reviewed_items_sha256"] = sha256_value(bank["reviewed_items"])
    result = validate_apply(queue, decisions, bank, report)
    assert "reviewed_bank_independent_reconstruction_mismatch" in result["errors"]


@pytest.mark.parametrize("key", ["source_text", "answer_model"])
def test_safe_report_text_and_answer_leakage(key):
    assert safe_scan({key: "secret"}) == [f"forbidden_safe_key:$.{key}"]


def test_tampered_decision_distribution_detected(artifacts):
    queue, decisions = artifacts
    bank, report = apply_artifacts(queue, decisions)
    report["decision_counts"]["PENDING"] = 280
    result = validate_apply(queue, decisions, bank, report)
    assert "promotion_safe_report_independent_reconstruction_mismatch" in result["errors"]


def test_tampered_promotion_distribution_detected(artifacts):
    queue, decisions = artifacts
    bank, report = apply_artifacts(queue, decisions)
    report["promotion_eligibility_distribution"]["blocked"] = 1
    result = validate_apply(queue, decisions, bank, report)
    assert "promotion_safe_report_independent_reconstruction_mismatch" in result["errors"]


def test_deterministic_apply_build(artifacts):
    queue, decisions = artifacts
    assert apply_artifacts(queue, decisions) == apply_artifacts(copy.deepcopy(queue), copy.deepcopy(decisions))


def test_real_local_zero_decision_execution():
    required = [LOCAL / "review_queue.json", LOCAL / "operator_decisions.template.json"]
    if not all(path.exists() for path in required):
        pytest.skip("real local artifacts are intentionally uncommitted")
    queue, decisions = (json.loads(path.read_text(encoding="utf-8")) for path in required)
    bank, report = apply_artifacts(queue, decisions)
    assert len(queue["review_entries"]) == 281
    assert report["decision_counts"] == {key: 281 if key == "PENDING" else 0 for key in DECISION_VALUES}
    assert bank["reviewed_item_count"] == 0


def test_unknown_decision_fails(artifacts):
    queue, decisions = artifacts
    decisions["decisions"][0]["review_entry_id"] = "M04B3_REVIEW_" + "F" * 20
    with pytest.raises(PromotionBuildError, match="unknown_decision"):
        apply_artifacts(queue, decisions)


def test_duplicate_decision_fails(artifacts):
    queue, decisions = artifacts
    decisions["decisions"][1]["review_entry_id"] = decisions["decisions"][0]["review_entry_id"]
    with pytest.raises(PromotionBuildError, match="duplicate_decision"):
        apply_artifacts(queue, decisions)


def test_missing_decision_remains_pending(artifacts):
    queue, decisions = artifacts
    decisions["decisions"].pop()
    bank, report = apply_artifacts(queue, decisions)
    assert bank["reviewed_item_count"] == 0
    assert report["decision_counts"]["PENDING"] == 281


def test_authority_boundary_false(artifacts):
    queue, decisions = artifacts
    _decide(queue, decisions, 0, "APPROVE_AS_IS")
    bank, report = apply_artifacts(queue, decisions)
    assert bank["policy"]["canonical_authority_promotion"] is False
    assert report["promotion_claim_count"] == 0


def test_real_prepare_is_deterministic_when_upstreams_available():
    paths = {
        "m04b2_private": ROOT / ".local/e4s_a1v1/reading/a1_a1plus_private_reading_candidates.json",
        "m04b2_safe": ROOT / "a1_a1plus_local_reading_binding_safe_report.json",
        "s12d_private": ROOT / ".local/raz_af/a1_a1plus_observational_consumer/bindings.json",
        "s12d_safe": ROOT / ".local/raz_af/a1_a1plus_observational_consumer/safe_report.json",
    }
    if not all(path.exists() for path in paths.values()):
        pytest.skip("real local upstreams are intentionally uncommitted")
    payloads = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in paths.items()}
    hashes = {f"{key}_sha256": sha256_file(path) for key, path in paths.items()}
    first = prepare_artifacts(payloads["m04b2_private"], payloads["m04b2_safe"], payloads["s12d_private"], payloads["s12d_safe"], hashes)
    second = prepare_artifacts(payloads["m04b2_private"], payloads["m04b2_safe"], payloads["s12d_private"], payloads["s12d_safe"], hashes)
    assert first == second
