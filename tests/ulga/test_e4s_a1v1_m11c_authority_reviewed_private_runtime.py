from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m11c_authority_reviewed_private_runtime as builder
from ulga.query import e4s_a1v1_m11c_authority_runtime_consumer as consumer
from ulga.validators import validate_e4s_a1v1_m11c_authority_reviewed_private_runtime as validator


@pytest.fixture(scope="module")
def built() -> tuple[Path, dict]:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11c-test-{uuid.uuid4().hex}"
    result = builder.build_runtime_artifacts(root)
    yield root, result
    shutil.rmtree(root, ignore_errors=True)


def test_runtime_filters_192_to_184_items(built: tuple[Path, dict]) -> None:
    _, result = built
    manifest = result["manifest"]
    assert manifest["text_mode_runtime"] == {
        "source_items": 192,
        "selectable_items": 184,
        "excluded_items": 8,
        "reading_items": 92,
        "writing_items": 92,
        "practice_items": 138,
        "assessment_items": 46,
        "grammar_units": 23,
        "canonical_egp_rows": 107,
        "session_entrypoint": "authority_session/index.html",
        "attempt_registry_compatibility": "M08_FULL_BANK_HASH_COMPATIBLE",
    }


def test_will_items_are_only_in_private_scoring_source(built: tuple[Path, dict]) -> None:
    root, result = built
    source_bank = builder.read_json(root / "source_m08/text_mode_session_bank.private.json")
    source_will = [row for row in source_bank["items"] if row["grammar_unit_id"] == builder.DEFERRED_GRAMMAR_ID]
    assert len(source_will) == 8
    assert all(row["grammar_unit_id"] != builder.DEFERRED_GRAMMAR_ID for row in result["learner_payload"]["items"])
    assert all(row["grammar_unit_id"] != builder.DEFERRED_GRAMMAR_ID for row in result["query_index"]["items"])
    assert result["manifest"]["deferred_units"][0]["excluded_item_count"] == 8


def test_filtered_payload_remains_m08_attempt_registry_compatible(built: tuple[Path, dict]) -> None:
    root, result = built
    source_bank = builder.read_json(root / "source_m08/text_mode_session_bank.private.json")
    payload = result["learner_payload"]
    assert payload["task_id"] == builder.m08.TASK_ID
    assert payload["session_bank_sha256"] == builder.sha256_value(source_bank)
    registry = builder.m08.empty_attempt_registry(source_bank)
    assert registry["session_bank_sha256"] == payload["session_bank_sha256"]
    selectable_ids = {row["item_id"] for row in payload["items"]}
    assert selectable_ids.issubset({row["item_id"] for row in source_bank["items"]})


def test_runtime_has_23_units_and_107_rows(built: tuple[Path, dict]) -> None:
    _, result = built
    items = result["query_index"]["items"]
    assert len({row["grammar_unit_id"] for row in items}) == 23
    assert len({row_id for row in items for row_id in row["canonical_egp_row_ids"]}) == 107
    assert result["safe_report"]["private_ready_unit_count"] == 23
    assert result["safe_report"]["private_ready_row_count"] == 107


def test_learner_payload_contains_no_private_scoring_fields(built: tuple[Path, dict]) -> None:
    _, result = built
    encoded = json.dumps(result["learner_payload"], ensure_ascii=False).casefold()
    for forbidden in (
        '"answer_key"',
        '"accepted_texts"',
        '"accepted_sequence"',
        '"private_scoring_contract"',
        '"model_texts"',
        '"correct_token_sequence"',
    ):
        assert forbidden not in encoded


def test_dashboard_is_local_safe_and_recording_free(built: tuple[Path, dict]) -> None:
    root, _ = built
    html = (root / "dashboard/index.html").read_text(encoding="utf-8").casefold()
    assert "localhost-only" in html
    assert "23" in html
    assert "184" in html
    assert "deferred at cambridge flyers/a2" in html
    for forbidden in ("mediarecorder", "getusermedia", "<audio", "websocket", "answer_key"):
        assert forbidden not in html


def test_health_and_independent_validator_pass(built: tuple[Path, dict]) -> None:
    root, _ = built
    health = builder.run_health(root)
    assert health["health_status"] == builder.RUNTIME_STATUS
    assert health["failed_check_count"] == 0, health["errors"]
    validation = validator.validate(root)
    assert validation["validation_status"] == builder.RUNTIME_STATUS
    assert validation["error_count"] == 0, validation["errors"]
    assert validation["m08_attempt_registry_compatible"] is True


def test_safe_queries_and_private_opt_in(built: tuple[Path, dict]) -> None:
    _, result = built
    summary = consumer.query(result["manifest"], result["query_index"], result["safe_report"], "summary")
    assert summary["selectable_item_count"] == 184
    ready_id = result["query_index"]["items"][0]["grammar_unit_id"]
    safe = consumer.query(result["manifest"], result["query_index"], result["safe_report"], "unit", ready_id)
    assert safe["match_count"] == 8
    assert "private_unit_payloads" not in safe
    private = consumer.query(result["manifest"], result["query_index"], result["safe_report"], "unit", ready_id, private=True)
    assert len(private["private_unit_payloads"]) == 1


def test_deferred_will_query_returns_no_items_or_private_payload(built: tuple[Path, dict]) -> None:
    _, result = built
    value = consumer.query(
        result["manifest"],
        result["query_index"],
        result["safe_report"],
        "unit",
        builder.DEFERRED_GRAMMAR_ID,
        private=True,
    )
    assert value["match_count"] == 0
    assert value["selectable"] is False
    assert value["items"] == []
    assert value["private_unit_payloads"] == []
    assert value["deferred_unit"]["canonical_egp_mapping_preserved"] is True


def test_payload_tampering_fails_validator(built: tuple[Path, dict]) -> None:
    root, result = built
    path = root / "authority_session/payload.json"
    original = path.read_text(encoding="utf-8")
    try:
        mutated = copy.deepcopy(result["learner_payload"])
        source_bank = builder.read_json(root / "source_m08/text_mode_session_bank.private.json")
        will_private = next(row for row in source_bank["items"] if row["grammar_unit_id"] == builder.DEFERRED_GRAMMAR_ID)
        safe_will = {
            "item_id": will_private["item_id"],
            "shared_item_id": will_private["shared_item_id"],
            "grammar_unit_id": will_private["grammar_unit_id"],
            "internal_stage": will_private["internal_stage"],
            "skill": will_private["skill"],
            "item_role": will_private["item_role"],
            "evidence_dimension": will_private["evidence_dimension"],
            "task_type": will_private["task_type"],
            **will_private["learner_contract"],
        }
        mutated["items"].append(safe_will)
        mutated["item_count"] = 185
        builder.write_json_atomic(path, mutated)
        check = validator.validate(root)
        assert check["validation_status"] == "FAIL"
        assert check["error_count"] > 0
    finally:
        path.write_text(original, encoding="utf-8")


def test_missing_runtime_file_fails_health(built: tuple[Path, dict]) -> None:
    root, _ = built
    path = root / "authority_runtime_query_index.json"
    backup = path.read_text(encoding="utf-8")
    try:
        path.unlink()
        health = builder.run_health(root)
        assert health["health_status"] == "FAIL"
        assert health["failed_check_count"] > 0
    finally:
        path.write_text(backup, encoding="utf-8")


def test_runtime_build_is_deterministic(built: tuple[Path, dict]) -> None:
    _, result = built
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11c-deterministic-{uuid.uuid4().hex}"
    try:
        rebuilt = builder.build_runtime_artifacts(root)
        assert rebuilt["manifest"] == result["manifest"]
        assert rebuilt["query_index"] == result["query_index"]
        assert rebuilt["learner_payload"] == result["learner_payload"]
        assert rebuilt["safe_report"] == result["safe_report"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_non_localhost_serve_is_rejected(built: tuple[Path, dict]) -> None:
    root, _ = built
    with pytest.raises(builder.AuthorityRuntimeError, match="non_localhost_bind_forbidden"):
        builder.serve_runtime(root, host="0.0.0.0", port=8771, dry_run=True)


def test_direct_cli_prepare_validate_query_and_serve_dry_run() -> None:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11c-cli-{uuid.uuid4().hex}"
    try:
        prepare = subprocess.run(
            [sys.executable, str(Path(builder.__file__).resolve()), "prepare", "--output-root", str(root)],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        assert json.loads(prepare.stdout)["selectable_items"] == 184
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
        summary = subprocess.run(
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
        assert summary.returncode == 0, summary.stderr
        assert json.loads(summary.stdout)["selectable_item_count"] == 184
        serve = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "serve",
                "--output-root",
                str(root),
                "--dry-run",
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert serve.returncode == 0, serve.stderr
        assert json.loads(serve.stdout)["runtime_status"] == builder.RUNTIME_STATUS
    finally:
        shutil.rmtree(root, ignore_errors=True)
