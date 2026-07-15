from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as m12
from ulga.builders import build_e4s_a1v1_m12c_real_learner_pilot_evidence_qa as builder
from ulga.validators import validate_e4s_a1v1_m12c_real_learner_pilot_evidence_qa as validator


def _fixture_registry(root: Path) -> None:
    prepared = m12.prepare_capture(root)
    manifest = prepared["manifest"]
    bank = builder.read_json(root / "runtime/source_m08/text_mode_session_bank.private.json")
    allowed = set(manifest["selection"]["selectable_item_ids"])
    item = next(row for row in bank["items"] if row["item_id"] in allowed)
    contract = item["private_scoring_contract"]
    mode = contract["scoring_mode"]
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        response = contract["accepted_texts"][0]
    elif mode == "EXACT_SEQUENCE":
        response = contract["accepted_sequence"]
    else:
        response = "This is a test fixture response."
    registry = m08.empty_attempt_registry(bank)
    registry["session_id"] = "m12c-test-fixture"
    registry["learner_ref"] = "fixture-not-real-learner"
    registry["attempts"] = [{
        "item_id": item["item_id"],
        "attempt_sequence": 1,
        "response": response,
        "submitted_at": "2026-07-15T13:16:05.516Z",
        "operator_review": m08._empty_review(),
    }]
    path = root / "fixture_registry.private.json"
    builder.write_json_atomic(path, registry)
    m12.import_evidence(root, path, evidence_origin="TEST_FIXTURE")


@pytest.fixture()
def fixture_root() -> Path:
    root = builder.REPO_ROOT / ".local" / f"m12c-test-{uuid.uuid4().hex}"
    _fixture_registry(root)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def test_builds_privacy_safe_fixture_qa(fixture_root: Path) -> None:
    output = fixture_root.parent / f"m12c-out-{uuid.uuid4().hex}"
    try:
        report = builder.build_qa(fixture_root, output, expected_origin="TEST_FIXTURE")
        assert report["validation_status"] == builder.TEST_STATUS
        assert report["evidence_summary"]["attempt_count"] == 1
        assert report["evidence_summary"]["auto_pass_count"] == 1
        assert report["evidence_summary"]["auto_fail_count"] == 0
        assert report["evidence_summary"]["pending_human_review_count"] == 0
        assert report["stop_reason"] == "NONE"
        assert report["next_short_step"] == "E4S-A1V1-M12D_RepresentativePilotExpansion"
        assert 1 <= report["iteration_queue"]["candidate_count"] <= 8
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_safe_report_contains_no_response_or_identity(fixture_root: Path) -> None:
    output = fixture_root.parent / f"m12c-safe-{uuid.uuid4().hex}"
    try:
        report = builder.build_qa(fixture_root, output, expected_origin="TEST_FIXTURE")
        encoded = json.dumps(report, ensure_ascii=False).casefold()
        for forbidden in ('"response"', '"learner_ref"', '"session_id"', '"submitted_at"', '"answer_key"', '"private_scoring_contract"'):
            assert forbidden not in encoded
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_iteration_queue_excludes_will_and_is_deterministic(fixture_root: Path) -> None:
    first = fixture_root.parent / f"m12c-first-{uuid.uuid4().hex}"
    second = fixture_root.parent / f"m12c-second-{uuid.uuid4().hex}"
    try:
        a = builder.build_qa(fixture_root, first, expected_origin="TEST_FIXTURE")
        b = builder.build_qa(fixture_root, second, expected_origin="TEST_FIXTURE")
        assert a == b
        assert len({row["item_id"] for row in a["iteration_queue"]["items"]}) == a["iteration_queue"]["candidate_count"]
        assert all(row["grammar_unit_id"] != m12.DEFERRED_GRAMMAR_ID for row in a["iteration_queue"]["items"])
    finally:
        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)


def test_real_origin_cannot_be_claimed_from_fixture(fixture_root: Path) -> None:
    output = fixture_root.parent / f"m12c-origin-{uuid.uuid4().hex}"
    try:
        with pytest.raises(builder.EvidenceQAError, match="capture_origin"):
            builder.build_qa(fixture_root, output, expected_origin="REAL_LEARNER")
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_query_ledger_outcome_mismatch_fails(fixture_root: Path) -> None:
    query_path = fixture_root / "pilot_progress_query_index.json"
    original = query_path.read_text(encoding="utf-8")
    output = fixture_root.parent / f"m12c-tamper-{uuid.uuid4().hex}"
    try:
        query = json.loads(original)
        attempted = next(row for row in query["items"] if row["attempted"])
        attempted["outcome"] = "AUTO_FAIL" if attempted["outcome"] != "AUTO_FAIL" else "AUTO_PASS"
        builder.write_json_atomic(query_path, query)
        with pytest.raises(builder.EvidenceQAError, match="query_ledger_mismatch"):
            builder.build_qa(fixture_root, output, expected_origin="TEST_FIXTURE")
    finally:
        query_path.write_text(original, encoding="utf-8")
        shutil.rmtree(output, ignore_errors=True)


def test_independent_validator_passes(fixture_root: Path) -> None:
    output = fixture_root.parent / f"m12c-valid-{uuid.uuid4().hex}"
    try:
        builder.build_qa(fixture_root, output, expected_origin="TEST_FIXTURE")
        result = validator.validate(fixture_root, output, expected_origin="TEST_FIXTURE")
        assert result["error_count"] == 0, result["errors"]
        assert result["validation_status"] == builder.TEST_STATUS
        assert result["attempt_count"] == 1
        assert result["learner_mastery_claimed"] is False
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_pending_human_review_routes_to_m12c1(fixture_root: Path) -> None:
    ledger_path = fixture_root / "pilot_progress_ledger.private.json"
    query_path = fixture_root / "pilot_progress_query_index.json"
    capture_path = fixture_root / "pilot_evidence_capture_safe_report.json"
    originals = {path: path.read_text(encoding="utf-8") for path in (ledger_path, query_path, capture_path)}
    output = fixture_root.parent / f"m12c-pending-{uuid.uuid4().hex}"
    try:
        ledger = json.loads(originals[ledger_path])
        entry = ledger["entries"][0]
        old = entry["outcome"]
        entry["outcome"] = "PENDING_HUMAN_REVIEW"
        entry["score"] = None
        ledger["outcome_counts"][old] -= 1
        ledger["outcome_counts"]["PENDING_HUMAN_REVIEW"] += 1
        ledger["entries_sha256"] = m08.sha256_value(ledger["entries"])
        builder.write_json_atomic(ledger_path, ledger)
        query = json.loads(originals[query_path])
        next(row for row in query["items"] if row["attempted"])["outcome"] = "PENDING_HUMAN_REVIEW"
        builder.write_json_atomic(query_path, query)
        capture = json.loads(originals[capture_path])
        capture["outcome_counts"] = dict(ledger["outcome_counts"])
        capture["pending_human_review_count"] = 1
        builder.write_json_atomic(capture_path, capture)
        report = builder.build_qa(fixture_root, output, expected_origin="TEST_FIXTURE")
        assert report["quality_gate"]["human_review_required"] is True
        assert report["stop_reason"] == "HUMAN_REVIEW_DECISIONS_REQUIRED"
        assert report["next_short_step"] == "E4S-A1V1-M12C1_HumanReviewDecisionMaterialization"
    finally:
        for path, text in originals.items():
            path.write_text(text, encoding="utf-8")
        shutil.rmtree(output, ignore_errors=True)
