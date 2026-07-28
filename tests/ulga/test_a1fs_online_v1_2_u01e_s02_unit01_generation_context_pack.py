from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01,
)
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s02_unit01_generation_context_pack as builder,
)
from ulga.validators import (
    validate_a1fs_online_v1_2_u01e_s02_unit01_generation_context_pack as validator,
)


def database(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE response_contracts(
                asset_key TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL,
                skill TEXT NOT NULL,
                role TEXT NOT NULL,
                capture_enabled INTEGER NOT NULL,
                contract_json TEXT NOT NULL,
                contract_digest TEXT NOT NULL
            )"""
        )
        rows: list[tuple] = []
        reading = (
            ("U01-R-01", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["a cat"], "accepted_sequence": []}),
            ("U01-R-02", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["the book"], "accepted_sequence": []}),
            ("U01-R-03", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["an apple"], "accepted_sequence": []}),
            ("U01-R-04", "CHK", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["a cat"], "accepted_sequence": []}),
        )
        for key, role, contract in reading:
            rows.append((key, s01.m01.LESSON_IDS["READING"], "READING", role, 1, json.dumps(contract), f"digest:{key}"))
        writing = (
            ("U01-W-01", "PRD", {"scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["a bag"], "accepted_sequence": []}),
            ("U01-W-02", "PRD", {"scoring_mode": "EXACT_SEQUENCE", "response_type": "sequence", "accepted_texts": [], "accepted_sequence": ["an", "apple"]}),
            ("U01-W-03", "PRD", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"grammar_target_match": True}}),
            ("U01-W-04", "CHK", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"complete_response": True}}),
        )
        for key, role, contract in writing:
            rows.append((key, s01.m01.LESSON_IDS["WRITING"], "WRITING", role, 1, json.dumps(contract), f"digest:{key}"))
        for index in range(1, 4):
            key = f"U01-S-{index:02d}"
            contract = {
                "scoring_mode": "FEATURE_RUBRIC",
                "response_type": "string",
                "accepted_texts": [],
                "accepted_sequence": [],
                "human_review_fallback": True,
                "rubric": {"practice_only": True},
            }
            rows.append((key, s01.m01.LESSON_IDS["SPEAKING"], "SPEAKING", "PRD", 0, json.dumps(contract), f"digest:{key}"))
        connection.executemany("INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", rows)
        connection.execute(
            """CREATE TABLE response_attempts(
                attempt_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                asset_key TEXT NOT NULL,
                attempt_sequence INTEGER NOT NULL,
                submitted_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE scoring_results(
                attempt_id TEXT PRIMARY KEY,
                outcome TEXT NOT NULL
            )"""
        )
        attempts = [
            ("ATTEMPT-001", "learner-1", "U01-R-01", 1, "2026-07-28T01:00:00Z"),
            ("ATTEMPT-002", "learner-1", "U01-W-02", 1, "2026-07-28T02:00:00Z"),
            ("ATTEMPT-OTHER", "learner-2", "U01-R-02", 1, "2026-07-28T03:00:00Z"),
        ]
        connection.executemany("INSERT INTO response_attempts VALUES(?,?,?,?,?)", attempts)
        connection.executemany(
            "INSERT INTO scoring_results VALUES(?,?)",
            [
                ("ATTEMPT-001", "AUTO_PASS"),
                ("ATTEMPT-002", "AUTO_FAIL"),
                ("ATTEMPT-OTHER", "AUTO_FAIL"),
            ],
        )
        connection.commit()
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approved_s01(path: Path, db: Path) -> Path:
    candidate = s01.build_candidate(db)
    approved = s01.admit_candidate(candidate)
    path.write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def built(tmp_path: Path, learner_id: str = "learner-1") -> tuple[Path, Path, dict, dict]:
    db = database(tmp_path / "learner.sqlite3")
    approved = approved_s01(tmp_path / "s01.approved.private.json", db)
    safe, private = builder.build_packs(
        approved_s01_path=approved,
        database_path=db,
        learner_id=learner_id,
    )
    return db, approved, safe, private


def test_builds_safe_and_private_deterministic_generation_context_packs(tmp_path: Path) -> None:
    _, approved, safe, private = built(tmp_path)
    report = validator.validate_packs(safe, private)
    assert report["error_count"] == 0, report
    assert safe["pack_type"] == builder.SAFE_PACK_TYPE
    assert private["pack_type"] == builder.PRIVATE_PACK_TYPE
    assert len(safe["generation_context"]["approved_contexts"]) == 5
    assert len(safe["generation_context"]["existing_item_dedup"]["semantic_signatures"]) == 11
    assert len(safe["generation_context"]["assessment_policy"]["allowed_pattern_refs"]) == 8
    safe2, private2 = builder.build_packs(
        approved_s01_path=approved,
        database_path=tmp_path / "learner.sqlite3",
        learner_id="learner-1",
    )
    assert safe2 == safe
    assert private2 == private


def test_private_pack_projects_weak_and_practised_targets_without_mastery_claim(tmp_path: Path) -> None:
    _, _, _, private = built(tmp_path)
    learner = private["generation_context"]["learner_state"]
    assert learner["learner_id"] == "learner-1"
    assert learner["attempt_count"] == 2
    assert learner["distinct_attempted_asset_count"] == 2
    assert learner["outcome_counts"] == {"AUTO_FAIL": 1, "AUTO_PASS": 1}
    assert learner["weak_asset_keys"] == ["U01-W-02"]
    assert learner["passed_asset_keys"] == ["U01-R-01"]
    assert learner["generation_learning_role_percent"] == {
        "NEW": 40,
        "WEAK_CARRYOVER": 30,
        "REVIEW": 20,
        "TRANSFER": 10,
    }
    assert learner["recent_error_tags"] == ["AUTO_FAIL:word_order"]
    assert learner["mastery_state"] == "NOT_INFERRED_FROM_ATTEMPT_OUTCOMES"
    assert private["generation_context"]["generation_budget_contract"][
        "active_learning_role_percent"
    ] == learner["generation_learning_role_percent"]


def test_safe_pack_contains_no_learner_or_attempt_identity(tmp_path: Path) -> None:
    _, _, safe, private = built(tmp_path)
    encoded = json.dumps(safe, ensure_ascii=False, sort_keys=True)
    for forbidden in (
        '"learner_id"',
        '"attempt_id"',
        '"asset_key"',
        '"learner_database_sha256"',
        "learner-1",
        "ATTEMPT-001",
    ):
        assert forbidden not in encoded
    assert "learner_state" not in safe["generation_context"]
    assert private["source_identity"]["learner_database_sha256"]
    assert private["generation_context"]["learner_state"]["latest_evidence_by_asset"]


def test_prompt_is_candidate_only_and_has_multi_standard_output_contract(tmp_path: Path) -> None:
    _, _, safe, private = built(tmp_path)
    for pack in (safe, private):
        prompt = pack["prompt_text"]
        assert "Return structured JSON candidate items only" in prompt
        assert "Do not write canonical data" in prompt
        output = pack["generation_context"]["candidate_output_contract"]
        assert output["artifact_role"] == "CANDIDATE_JSON"
        assert output["direct_canonical_write_allowed"] is False
        assert set(builder.OUTPUT_FIELDS).issubset(output["required_fields"])
        assert pack["generation_context"]["curriculum_targets"][
            "ket_prerequisite_node_ids"
        ] == []
        assert (
            pack["generation_context"]["curriculum_targets"]["ket_binding_status"]
            == "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE"
        )


def test_source_database_is_read_only_and_hidden_answers_never_enter_packs(tmp_path: Path) -> None:
    db, _, _, _ = built(tmp_path)
    before = sha(db)
    safe2, private2 = builder.build_packs(
        approved_s01_path=tmp_path / "s01.approved.private.json",
        database_path=db,
        learner_id="learner-1",
    )
    assert sha(db) == before
    encoded = json.dumps({"safe": safe2, "private": private2}, ensure_ascii=False)
    for forbidden in (
        '"accepted_texts"',
        '"accepted_sequence"',
        '"response_json"',
        '"contract_json"',
    ):
        assert forbidden not in encoded


def test_tampered_s01_approved_artifact_fails_closed(tmp_path: Path) -> None:
    db, approved_path, _, _ = built(tmp_path)
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    approved["payload"]["contexts"][0]["title"] = "tampered"
    approved_path.write_text(json.dumps(approved), encoding="utf-8")
    with pytest.raises(builder.S02ContextPackError, match="s01_approved_digest_invalid"):
        builder.build_packs(
            approved_s01_path=approved_path,
            database_path=db,
            learner_id="learner-1",
        )


def test_validator_rejects_direct_canonical_write_permission(tmp_path: Path) -> None:
    _, _, safe, private = built(tmp_path)
    tampered = copy.deepcopy(safe)
    tampered["generation_context"]["candidate_output_contract"][
        "direct_canonical_write_allowed"
    ] = True
    prompt = builder.render_prompt(
        tampered["pack_type"], tampered["generation_context"]
    )
    tampered["prompt_text"] = prompt
    tampered["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    core = {key: value for key, value in tampered.items() if key != "pack_sha256"}
    tampered["pack_sha256"] = builder.digest(core)
    report = validator.validate_packs(tampered, private)
    assert report["error_count"] > 0
    assert any("canonical_write_allowed" in error for error in report["errors"])


def test_learner_without_attempts_uses_default_budget(tmp_path: Path) -> None:
    _, _, safe, private = built(tmp_path, learner_id="learner-empty")
    learner = private["generation_context"]["learner_state"]
    assert learner["attempt_count"] == 0
    assert learner["weak_asset_keys"] == []
    assert learner["generation_learning_role_percent"] == {
        "NEW": 50,
        "WEAK_CARRYOVER": 0,
        "REVIEW": 30,
        "TRANSFER": 20,
    }
    assert validator.validate_packs(safe, private)["error_count"] == 0
