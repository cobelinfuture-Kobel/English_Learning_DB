from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as m12
from ulga.builders import build_e4s_a1v1_m12c_real_learner_pilot_evidence_qa as m12c
from ulga.builders import build_e4s_a1v1_m12d_representative_pilot_expansion as m12d
from ulga.builders import build_e4s_a1v1_m12e_representative_pilot_evidence_qa as m12e
from ulga.builders import build_e4s_a1v1_m12e1_human_review_decision_materialization as builder
from ulga.validators import validate_e4s_a1v1_m12e1_human_review_decision_materialization as validator


def _response_for(item: dict) -> object:
    contract = item["private_scoring_contract"]
    mode = contract["scoring_mode"]
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        return contract["accepted_texts"][0]
    if mode == "EXACT_SEQUENCE":
        return contract["accepted_sequence"]
    return "Representative human-review fixture response."


def _build_chain(base: Path) -> tuple[Path, Path, Path, Path]:
    input_root = base / "m12"
    qa_root = base / "m12c"
    representative_root = base / "m12d"
    m12e_root = base / "m12e"
    prepared = m12.prepare_capture(input_root)
    manifest = prepared["manifest"]
    bank = json.loads(
        (input_root / "runtime/source_m08/text_mode_session_bank.private.json").read_text(encoding="utf-8")
    )
    allowed = set(manifest["selection"]["selectable_item_ids"])
    prior_item = next(
        row for row in bank["items"]
        if row["item_id"] in allowed
        and row["private_scoring_contract"]["scoring_mode"] != "FEATURE_RUBRIC"
    )
    prior = m12.m08.empty_attempt_registry(bank)
    prior["session_id"] = "m12e1-prior-fixture"
    prior["learner_ref"] = "fixture-learner"
    prior["attempts"] = [{
        "item_id": prior_item["item_id"],
        "attempt_sequence": 1,
        "response": _response_for(prior_item),
        "submitted_at": "2026-07-16T00:01:00.000Z",
        "operator_review": m12.m08._empty_review(),
    }]
    prior_path = base / "prior.private.json"
    prior_path.write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m12.import_evidence(input_root, prior_path, evidence_origin="TEST_FIXTURE")
    m12c.build_qa(input_root, qa_root, expected_origin="TEST_FIXTURE")

    m12d_prepared = m12d.prepare_batch(
        input_root,
        qa_root,
        representative_root,
        expected_origin="TEST_FIXTURE",
    )
    item_ids = list(m12d_prepared["manifest"]["batch_selection"]["item_ids"])
    by_id = {row["item_id"]: row for row in bank["items"]}
    batch = m12.m08.empty_attempt_registry(bank)
    batch["session_id"] = "m12e1-representative-fixture"
    batch["learner_ref"] = prior["learner_ref"]
    batch["attempts"] = [
        {
            "item_id": item_id,
            "attempt_sequence": index,
            "response": _response_for(by_id[item_id]),
            "submitted_at": f"2026-07-16T00:{10 + index:02d}:00.000Z",
            "operator_review": m12.m08._empty_review(),
        }
        for index, item_id in enumerate(item_ids, start=1)
    ]
    batch_path = base / "batch.private.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m12d.import_batch(
        input_root,
        qa_root,
        representative_root,
        batch_path,
        expected_origin="TEST_FIXTURE",
    )
    report = m12e.build_qa(
        input_root,
        qa_root,
        representative_root,
        m12e_root,
        expected_origin="TEST_FIXTURE",
    )
    assert report["evidence_summary"]["pending_human_review_count"] > 0
    assert report["next_short_step"] == builder.TASK_ID
    return input_root, qa_root, representative_root, m12e_root


def _decision_registry(template: dict, *, mode: str) -> dict:
    value = copy.deepcopy(template)
    decisions = value["decisions"]
    if mode == "pending":
        return value
    value["reviewer_id"] = "fixture-reviewer"
    value["reviewed_at"] = "2026-07-16T02:00:00.000Z"
    for index, row in enumerate(decisions):
        if mode == "partial" and index > 0:
            continue
        if mode == "reject-first" and index == 0:
            row["decision"] = "REJECT"
            row["criteria"] = {
                "grammar_target_match": False,
                "meaning_matches_context": True,
                "complete_response": True,
            }
            row["notes"] = "Target grammar is not sufficiently demonstrated."
        else:
            row["decision"] = "APPROVE"
            row["criteria"] = {
                "grammar_target_match": True,
                "meaning_matches_context": True,
                "complete_response": True,
            }
            row["notes"] = "Meets all three review criteria."
    return value


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def built() -> dict:
    root = builder.REPO_ROOT / ".local" / f"m12e1-test-{uuid.uuid4().hex}"
    input_root, qa_root, representative_root, m12e_root = _build_chain(root)
    prepare_root = root / "prepare"
    prepared = builder.prepare_workbench(
        input_root,
        representative_root,
        m12e_root,
        prepare_root,
        expected_origin="TEST_FIXTURE",
    )
    full_path = _write(root / "full.private.json", _decision_registry(prepared["decision_template"], mode="approve"))
    partial_path = _write(root / "partial.private.json", _decision_registry(prepared["decision_template"], mode="partial"))
    reject_path = _write(root / "reject.private.json", _decision_registry(prepared["decision_template"], mode="reject-first"))
    full_root = root / "full"
    partial_root = root / "partial"
    reject_root = root / "reject"
    full = builder.apply_decisions(
        input_root,
        qa_root,
        representative_root,
        m12e_root,
        full_root,
        full_path,
        expected_origin="TEST_FIXTURE",
    )
    partial = builder.apply_decisions(
        input_root,
        qa_root,
        representative_root,
        m12e_root,
        partial_root,
        partial_path,
        expected_origin="TEST_FIXTURE",
    )
    reject = builder.apply_decisions(
        input_root,
        qa_root,
        representative_root,
        m12e_root,
        reject_root,
        reject_path,
        expected_origin="TEST_FIXTURE",
    )
    yield {
        "root": root,
        "input_root": input_root,
        "qa_root": qa_root,
        "representative_root": representative_root,
        "m12e_root": m12e_root,
        "prepare_root": prepare_root,
        "prepared": prepared,
        "full_path": full_path,
        "partial_path": partial_path,
        "reject_path": reject_path,
        "full_root": full_root,
        "partial_root": partial_root,
        "reject_root": reject_root,
        "full": full,
        "partial": partial,
        "reject": reject,
    }
    shutil.rmtree(root, ignore_errors=True)


def test_prepare_queue_contains_only_pending_feature_rubric_items(built: dict) -> None:
    queue = built["prepared"]["queue"]
    assert queue["pending_item_count"] == len(queue["items"])
    assert queue["pending_item_count"] > 0
    assert all(row["private_scoring_contract"]["scoring_mode"] == "FEATURE_RUBRIC" for row in queue["items"])
    assert all(row["current_operator_review"]["decision"] == "PENDING" for row in queue["items"])
    assert len({row["item_id"] for row in queue["items"]}) == queue["pending_item_count"]


def test_private_queue_has_evidence_but_safe_report_does_not(built: dict) -> None:
    queue_encoded = json.dumps(built["prepared"]["queue"], ensure_ascii=False).casefold()
    assert '"learner_response"' in queue_encoded
    assert '"private_scoring_contract"' in queue_encoded
    report = built["prepared"]["safe_report"]
    safe_encoded = json.dumps(report, ensure_ascii=False).casefold()
    for forbidden in ('"response"', '"learner_response"', '"prompt"', '"rubric"', '"model_texts"', '"reviewer_id"'):
        assert forbidden not in safe_encoded
    assert report["validation_status"] == builder.PREPARE_STATUS
    assert report["stop_reason"] == "HUMAN_REVIEW_DECISIONS_REQUIRED"


def test_decision_template_is_hash_bound_and_pending(built: dict) -> None:
    template = built["prepared"]["decision_template"]
    assert template["source_review_queue_sha256"] == builder.sha256_value(built["prepared"]["queue"])
    assert template["reviewer_id"] is None
    assert template["reviewed_at"] is None
    assert all(row["decision"] == "PENDING" for row in template["decisions"])


def test_full_approval_resolves_all_pending_and_reruns_m12e(built: dict) -> None:
    result = built["full"]
    report = result["safe_report"]
    pending = built["prepared"]["queue"]["pending_item_count"]
    assert report["source_pending_count"] == pending
    assert report["materialized_decision_count"] == pending
    assert report["remaining_pending_count"] == 0
    assert report["outcome_counts"]["HUMAN_APPROVE"] == pending
    assert result["resolved_m12e"]["evidence_summary"]["pending_human_review_count"] == 0
    assert report["validation_status"] == builder.COMPLETE_STATUS
    assert report["next_short_step"] == result["resolved_m12e"]["next_short_step"]
    assert report["next_short_step"] != builder.NEXT_SELF


def test_partial_decisions_remain_on_m12e1(built: dict) -> None:
    report = built["partial"]["safe_report"]
    assert report["materialized_decision_count"] == 1
    assert report["remaining_pending_count"] == report["source_pending_count"] - 1
    assert report["validation_status"] == builder.PARTIAL_STATUS
    assert report["stop_reason"] == "HUMAN_REVIEW_DECISIONS_REQUIRED"
    assert report["next_short_step"] == builder.NEXT_SELF


def test_rejection_routes_to_remediation(built: dict) -> None:
    result = built["reject"]
    report = result["safe_report"]
    assert report["remaining_pending_count"] == 0
    assert report["outcome_counts"]["HUMAN_REJECT"] == 1
    assert result["resolved_m12e"]["quality_gate"]["remediation_required"] is True
    assert report["next_short_step"] == "E4S-A1V1-M12F_RemediationAndCoverageExpansion"
    assert report["stop_reason"] == "NONE"


def test_only_operator_review_changes_in_resolved_registry(built: dict) -> None:
    original = json.loads((built["representative_root"] / "cumulative_attempt_registry.private.json").read_text(encoding="utf-8"))
    resolved = built["full"]["resolved_registry"]
    original_by_id = {row["item_id"]: row for row in original["attempts"]}
    pending_ids = {row["item_id"] for row in built["prepared"]["queue"]["items"]}
    for row in resolved["attempts"]:
        before = copy.deepcopy(original_by_id[row["item_id"]])
        after = copy.deepcopy(row)
        before_review = before.pop("operator_review")
        after_review = after.pop("operator_review")
        assert before == after
        if row["item_id"] in pending_ids:
            assert before_review["decision"] == "PENDING"
            assert after_review["decision"] == "APPROVE"
        else:
            assert before_review == after_review


def test_prepare_and_apply_validators_pass(built: dict) -> None:
    prepared = validator.validate(
        "prepare",
        built["input_root"],
        built["qa_root"],
        built["representative_root"],
        built["m12e_root"],
        built["prepare_root"],
        expected_origin="TEST_FIXTURE",
    )
    assert prepared["error_count"] == 0, prepared["errors"]
    assert prepared["validation_status"] == builder.PREPARE_STATUS
    full = validator.validate(
        "apply-decisions",
        built["input_root"],
        built["qa_root"],
        built["representative_root"],
        built["m12e_root"],
        built["full_root"],
        expected_origin="TEST_FIXTURE",
    )
    assert full["error_count"] == 0, full["errors"]
    assert full["validation_status"] == builder.COMPLETE_STATUS
    assert full["remaining_pending_count"] == 0


def test_queue_hash_and_item_identity_tampering_are_rejected(built: dict) -> None:
    queue = built["prepared"]["queue"]
    tampered = _decision_registry(built["prepared"]["decision_template"], mode="approve")
    tampered["source_review_queue_sha256"] = "0" * 64
    with pytest.raises(builder.HumanReviewMaterializationError, match="decision_queue_hash"):
        builder._validate_decisions(queue, tampered)
    tampered = _decision_registry(built["prepared"]["decision_template"], mode="approve")
    tampered["decisions"][0]["item_id"] = "UNKNOWN_ITEM"
    with pytest.raises(builder.HumanReviewMaterializationError, match="decision_item_set"):
        builder._validate_decisions(queue, tampered)


def test_invalid_approve_reject_and_defer_criteria_are_rejected(built: dict) -> None:
    queue = built["prepared"]["queue"]
    approve = _decision_registry(built["prepared"]["decision_template"], mode="approve")
    approve["decisions"][0]["criteria"]["complete_response"] = False
    with pytest.raises(builder.HumanReviewMaterializationError, match="approve_criteria"):
        builder._validate_decisions(queue, approve)
    reject = _decision_registry(built["prepared"]["decision_template"], mode="reject-first")
    reject["decisions"][0]["criteria"] = {key: True for key in builder.CRITERIA_KEYS}
    with pytest.raises(builder.HumanReviewMaterializationError, match="reject_requires"):
        builder._validate_decisions(queue, reject)
    defer = _decision_registry(built["prepared"]["decision_template"], mode="approve")
    defer["decisions"][0]["decision"] = "DEFER"
    defer["decisions"][0]["notes"] = None
    with pytest.raises(builder.HumanReviewMaterializationError, match="defer_requires_notes"):
        builder._validate_decisions(queue, defer)


def test_non_localhost_serve_rejected_and_dry_run_passes(built: dict, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(builder.HumanReviewMaterializationError, match="non_localhost_bind_forbidden"):
        builder.serve_workbench(built["prepare_root"], host="0.0.0.0", port=8773, dry_run=True)
    assert builder.serve_workbench(built["prepare_root"], host="127.0.0.1", port=8773, dry_run=True) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["pending_item_count"] == built["prepared"]["queue"]["pending_item_count"]


def test_direct_cli_prepare_apply_and_validate() -> None:
    root = builder.REPO_ROOT / ".local" / f"m12e1-cli-{uuid.uuid4().hex}"
    try:
        input_root, qa_root, representative_root, m12e_root = _build_chain(root)
        output_root = root / "m12e1"
        prepare = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "prepare",
                "--input-root", str(input_root),
                "--qa-root", str(qa_root),
                "--representative-root", str(representative_root),
                "--m12e-root", str(m12e_root),
                "--output-root", str(output_root),
                "--expected-origin", "TEST_FIXTURE",
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        assert json.loads(prepare.stdout)["source_pending_count"] > 0
        template = json.loads((output_root / "human_review_decision_template.private.json").read_text(encoding="utf-8"))
        decisions_path = _write(root / "cli-decisions.private.json", _decision_registry(template, mode="approve"))
        apply = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "apply-decisions",
                "--input-root", str(input_root),
                "--qa-root", str(qa_root),
                "--representative-root", str(representative_root),
                "--m12e-root", str(m12e_root),
                "--output-root", str(output_root),
                "--decisions", str(decisions_path),
                "--expected-origin", "TEST_FIXTURE",
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert apply.returncode == 0, apply.stderr
        assert json.loads(apply.stdout)["remaining_pending_count"] == 0
        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "apply-decisions",
                "--input-root", str(input_root),
                "--qa-root", str(qa_root),
                "--representative-root", str(representative_root),
                "--m12e-root", str(m12e_root),
                "--output-root", str(output_root),
                "--expected-origin", "TEST_FIXTURE",
                "--validation-report", str(output_root / "validation.json"),
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validate.returncode == 0, validate.stderr
        assert json.loads(validate.stdout)["error_count"] == 0
    finally:
        shutil.rmtree(root, ignore_errors=True)
