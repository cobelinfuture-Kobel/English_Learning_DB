from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as builder
from ulga.query import e4s_a1v1_text_mode_session_consumer as consumer
from ulga.validators import validate_e4s_a1v1_m08_text_mode_learner_session as validator


@pytest.fixture()
def prepared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict]:
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    root = tmp_path / ".local/e4s_a1v1/text_mode/m08"
    result = builder.prepare_artifacts(root, builder.M07_RECEIPT_PATH)
    return root, result


def _review(
    decision: str = "PENDING",
    *,
    all_true: bool = False,
) -> dict:
    reviewed = decision != "PENDING"
    return {
        "decision": decision,
        "reviewer_id": "operator-local-01" if reviewed else None,
        "reviewed_at": "2026-07-15T12:00:00+08:00" if reviewed else None,
        "criteria": {
            "grammar_target_match": True if all_true else None,
            "meaning_matches_context": True if all_true else None,
            "complete_response": True if all_true else None,
        },
        "notes": None,
    }


def _attempt(item: dict, response, *, review: dict | None = None) -> dict:
    return {
        "item_id": item["item_id"],
        "attempt_sequence": 1,
        "response": response,
        "submitted_at": "2026-07-15T12:00:00+08:00",
        "operator_review": review or _review(),
    }


def _registry(root: Path, attempts: list[dict]) -> dict:
    value = builder.read_json(root / "text_mode_attempt_registry.template.json")
    value["attempts"] = attempts
    return value


def _item(result: dict, mode: str) -> dict:
    return next(
        row
        for row in result["bank"]["items"]
        if row["private_scoring_contract"]["scoring_mode"] == mode
    )


def test_zero_attempt_state_materializes_and_validates(
    prepared: tuple[Path, dict],
) -> None:
    root, result = prepared
    assert result["bank"]["item_count"] == 192
    assert result["ledger"]["attempt_count"] == 0
    assert result["safe_report"]["validation_status"] == builder.ZERO_STATUS
    validation = validator.validate(root)
    assert validation["error_count"] == 0, validation["errors"]
    assert validation["validation_status"] == builder.ZERO_STATUS


def test_exact_item_accounting_and_coverage(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    items = result["bank"]["items"]
    assert len(items) == 192
    assert len({row["item_id"] for row in items}) == 192
    assert len({row["grammar_unit_id"] for row in items}) == 24
    assert len(
        {
            row_id
            for row in items
            for row_id in row["canonical_egp_row_ids"]
        }
    ) == 109
    assert sum(row["skill"] == "reading" for row in items) == 96
    assert sum(row["skill"] == "writing" for row in items) == 96
    assert sum(row["item_role"] == "practice" for row in items) == 144
    assert sum(row["item_role"] == "assessment" for row in items) == 48


def test_exact_option_auto_pass_and_fail(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    item = _item(result, "EXACT_OPTION")
    accepted = item["private_scoring_contract"]["accepted_texts"][0]
    correct = _registry(root, [_attempt(item, accepted)])
    ledger, report, _ = builder.build_progress_artifacts(
        result["bank"], correct
    )
    assert ledger["entries"][0]["outcome"] == "AUTO_PASS"
    assert ledger["entries"][0]["score"] == 1.0
    assert report["outcome_counts"]["AUTO_PASS"] == 1

    wrong = _registry(root, [_attempt(item, "definitely not accepted")])
    ledger, _, _ = builder.build_progress_artifacts(result["bank"], wrong)
    assert ledger["entries"][0]["outcome"] == "AUTO_FAIL"
    assert ledger["entries"][0]["score"] == 0.0


def test_exact_sequence_auto_scoring(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    item = _item(result, "EXACT_SEQUENCE")
    accepted = item["private_scoring_contract"]["accepted_sequence"]
    registry = _registry(root, [_attempt(item, accepted)])
    ledger, _, _ = builder.build_progress_artifacts(result["bank"], registry)
    assert ledger["entries"][0]["outcome"] == "AUTO_PASS"

    reversed_registry = _registry(root, [_attempt(item, list(reversed(accepted)))])
    ledger, _, _ = builder.build_progress_artifacts(
        result["bank"], reversed_registry
    )
    assert ledger["entries"][0]["outcome"] == "AUTO_FAIL"


def test_normalized_gap_text_auto_scoring(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    item = _item(result, "NORMALIZED_TEXT")
    accepted = item["private_scoring_contract"]["accepted_texts"][0]
    registry = _registry(root, [_attempt(item, f"  {accepted}.  ")])
    ledger, _, _ = builder.build_progress_artifacts(result["bank"], registry)
    assert ledger["entries"][0]["outcome"] == "AUTO_PASS"


def test_productive_writing_requires_human_review(
    prepared: tuple[Path, dict],
) -> None:
    root, result = prepared
    item = _item(result, "FEATURE_RUBRIC")
    pending = _registry(root, [_attempt(item, "I write a new A1 response.")])
    ledger, report, _ = builder.build_progress_artifacts(
        result["bank"], pending
    )
    assert ledger["entries"][0]["outcome"] == "PENDING_HUMAN_REVIEW"
    assert ledger["entries"][0]["score"] is None
    assert report["pending_human_review_count"] == 1

    approved = _registry(
        root,
        [
            _attempt(
                item,
                "I write a new A1 response.",
                review=_review("APPROVE", all_true=True),
            )
        ],
    )
    ledger, _, _ = builder.build_progress_artifacts(
        result["bank"], approved
    )
    assert ledger["entries"][0]["outcome"] == "HUMAN_APPROVE"
    assert ledger["entries"][0]["score"] == 1.0
    assert ledger["entries"][0]["mastery_claimed"] is False


def test_human_reject_and_defer_are_distinct(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    item = _item(result, "FEATURE_RUBRIC")
    rejected_review = _review("REJECT")
    rejected_review["criteria"]["grammar_target_match"] = False
    rejected = _registry(
        root, [_attempt(item, "Incorrect response", review=rejected_review)]
    )
    ledger, _, _ = builder.build_progress_artifacts(
        result["bank"], rejected
    )
    assert ledger["entries"][0]["outcome"] == "HUMAN_REJECT"

    deferred = _registry(
        root,
        [_attempt(item, "Needs context", review=_review("DEFER"))],
    )
    ledger, _, _ = builder.build_progress_artifacts(
        result["bank"], deferred
    )
    assert ledger["entries"][0]["outcome"] == "HUMAN_DEFER"
    assert ledger["entries"][0]["score"] is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("unknown", "unknown_attempt_item"),
        ("duplicate", "duplicate_attempt_item"),
        ("hash", "attempt_registry_session_hash"),
        ("timestamp", "submitted_at_invalid"),
        ("type", "response_type_invalid"),
        ("override", "deterministic_item_review_override_forbidden"),
    ],
)
def test_attempt_tampering_fails_closed(
    prepared: tuple[Path, dict], mutation: str, message: str
) -> None:
    root, result = prepared
    item = _item(result, "EXACT_OPTION")
    accepted = item["private_scoring_contract"]["accepted_texts"][0]
    attempt = _attempt(item, accepted)
    registry = _registry(root, [attempt])
    if mutation == "unknown":
        attempt["item_id"] = "UNKNOWN"
    elif mutation == "duplicate":
        registry["attempts"] = [attempt, copy.deepcopy(attempt)]
    elif mutation == "hash":
        registry["session_bank_sha256"] = "0" * 64
    elif mutation == "timestamp":
        attempt["submitted_at"] = "2026-07-15T12:00:00"
    elif mutation == "type":
        attempt["response"] = [accepted]
    elif mutation == "override":
        attempt["operator_review"] = _review("APPROVE", all_true=True)
    with pytest.raises(builder.TextModeSessionError, match=message):
        builder.build_progress_artifacts(result["bank"], registry)


def test_approval_requires_reviewer_timestamp_and_all_criteria(
    prepared: tuple[Path, dict],
) -> None:
    root, result = prepared
    item = _item(result, "FEATURE_RUBRIC")
    review = _review("APPROVE", all_true=True)
    review["reviewer_id"] = None
    with pytest.raises(builder.TextModeSessionError, match="reviewer_missing"):
        builder.build_progress_artifacts(
            result["bank"],
            _registry(root, [_attempt(item, "Response", review=review)]),
        )

    review = _review("APPROVE", all_true=True)
    review["reviewed_at"] = "2026-07-15T12:00:00"
    with pytest.raises(
        builder.TextModeSessionError, match="review_timestamp_invalid"
    ):
        builder.build_progress_artifacts(
            result["bank"],
            _registry(root, [_attempt(item, "Response", review=review)]),
        )

    review = _review("APPROVE", all_true=True)
    review["criteria"]["complete_response"] = False
    with pytest.raises(
        builder.TextModeSessionError,
        match="approved_review_criteria_not_all_true",
    ):
        builder.build_progress_artifacts(
            result["bank"],
            _registry(root, [_attempt(item, "Response", review=review)]),
        )


def test_safe_payload_report_and_query_have_no_answers_or_responses(
    prepared: tuple[Path, dict],
) -> None:
    _, result = prepared
    encoded = json.dumps(
        [result["payload"], result["safe_report"], result["query"]],
        ensure_ascii=False,
    ).casefold()
    for forbidden in (
        '"answer_key"',
        '"answer_contract"',
        '"accepted_texts"',
        '"canonical_target"',
        '"correct_token_sequence"',
        '"response":',
        '"learner_ref"',
        '"operator_notes"',
    ):
        assert forbidden not in encoded
    assert ":\\" not in encoded


def test_local_ui_is_offline_text_only(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    html = (root / "local_session/index.html").read_text(encoding="utf-8")
    lowered = html.casefold()
    assert "localstorage" in lowered
    assert "download attempt registry" in lowered
    assert "no audio is used" in lowered
    assert "getusermedia" not in lowered
    assert "mediarecorder" not in lowered
    assert "fetch('http" not in lowered
    assert "answer_key" not in lowered


def test_partial_materialization_is_deterministic(
    prepared: tuple[Path, dict],
) -> None:
    root, result = prepared
    item = _item(result, "EXACT_OPTION")
    accepted = item["private_scoring_contract"]["accepted_texts"][0]
    registry = _registry(root, [_attempt(item, accepted)])
    first = builder.build_progress_artifacts(result["bank"], registry)
    second = builder.build_progress_artifacts(result["bank"], registry)
    assert first == second
    assert builder.sha256_value(first[0]) == builder.sha256_value(second[0])


def test_query_safe_and_explicit_private_modes(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    item = _item(result, "EXACT_OPTION")
    accepted = item["private_scoring_contract"]["accepted_texts"][0]
    registry = _registry(root, [_attempt(item, accepted)])
    path = root / "attempts.private.json"
    builder.write_json_atomic(path, registry)
    materialized = builder.materialize_attempts(root, path)

    summary = consumer.query(
        materialized["safe_report"], materialized["query"], "summary"
    )
    assert summary["attempt_count"] == 1
    safe_item = consumer.query(
        materialized["safe_report"],
        materialized["query"],
        "item",
        item["item_id"],
    )
    assert "private_progress_entries" not in safe_item

    private_item = consumer.query(
        materialized["safe_report"],
        materialized["query"],
        "item",
        item["item_id"],
        private_ledger=materialized["ledger"],
    )
    assert private_item["private_progress_entries"][0]["response"] == accepted

    for command, value in (
        ("unit", item["grammar_unit_id"]),
        ("row", item["canonical_egp_row_ids"][0]),
        ("skill", item["skill"]),
        ("role", item["item_role"]),
        ("stage", item["internal_stage"]),
        ("outcome", "AUTO_PASS"),
    ):
        assert consumer.query(
            materialized["safe_report"],
            materialized["query"],
            command,
            value,
        )["match_count"] > 0


def test_unknown_query_fails_closed(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    with pytest.raises(consumer.TextModeQueryError):
        consumer.query(
            result["safe_report"], result["query"], "item", "UNKNOWN"
        )
    with pytest.raises(consumer.TextModeQueryError):
        consumer.query(
            result["safe_report"], result["query"], "skill", "speaking"
        )


def test_validator_detects_ledger_tampering(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    path = root / "text_mode_progress_ledger.private.json"
    value = builder.read_json(path)
    value["attempt_count"] = 1
    builder.write_json_atomic(path, value)
    result = validator.validate(root)
    assert result["validation_status"] == "FAIL"
    assert result["error_count"] > 0


def test_direct_cli_help_and_real_zero_state() -> None:
    for module in (builder, validator, consumer):
        result = subprocess.run(
            [sys.executable, str(Path(module.__file__).resolve()), "--help"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    root = builder.SOURCE_REPO_ROOT / ".local" / f"m08-ci-{uuid.uuid4().hex}"
    try:
        prepare = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "prepare",
                "--output-root",
                str(root),
                "--m07-receipt",
                str(builder.M07_RECEIPT_PATH),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        assert json.loads(prepare.stdout)["validation_status"] == builder.ZERO_STATUS

        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "--output-root",
                str(root),
                "--validation-report",
                str(root / "validation.json"),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validate.returncode == 0, validate.stderr
        assert json.loads(validate.stdout)["error_count"] == 0

        query = subprocess.run(
            [
                sys.executable,
                str(Path(consumer.__file__).resolve()),
                "--output-root",
                str(root),
                "summary",
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert query.returncode == 0, query.stderr
        assert json.loads(query.stdout)["available_item_count"] == 192
    finally:
        shutil.rmtree(root, ignore_errors=True)
