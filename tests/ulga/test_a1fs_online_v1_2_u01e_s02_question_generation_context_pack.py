from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s02_question_generation_context_pack as builder,
)
from ulga.validators import (
    validate_a1fs_online_v1_2_u01e_s02_question_generation_context_pack as validator,
)


def database(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              role TEXT NOT NULL,
              capture_enabled INTEGER NOT NULL,
              contract_json TEXT NOT NULL,
              contract_digest TEXT NOT NULL
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              asset_key TEXT NOT NULL,
              attempt_sequence INTEGER NOT NULL,
              response_json TEXT NOT NULL,
              submitted_at TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              attempt_hash TEXT NOT NULL
            );
            CREATE TABLE scoring_results(
              attempt_id TEXT PRIMARY KEY,
              scoring_mode TEXT NOT NULL,
              outcome TEXT NOT NULL,
              score REAL,
              human_review_required INTEGER NOT NULL,
              scored_at TEXT NOT NULL,
              contract_digest TEXT NOT NULL
            );
            """
        )
        contracts: list[tuple] = []
        reading = (
            ("U01-R-01", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["a cat"], "accepted_sequence": []}),
            ("U01-R-02", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["the book"], "accepted_sequence": []}),
            ("U01-R-03", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["an apple"], "accepted_sequence": []}),
            ("U01-R-04", "CHK", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["a cat"], "accepted_sequence": []}),
        )
        for key, role, contract in reading:
            contracts.append(
                (
                    key,
                    builder.s01.m01.LESSON_IDS["READING"],
                    "READING",
                    role,
                    1,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
        writing = (
            ("U01-W-01", "PRD", {"scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["a bag"], "accepted_sequence": []}),
            ("U01-W-02", "PRD", {"scoring_mode": "EXACT_SEQUENCE", "response_type": "sequence", "accepted_texts": [], "accepted_sequence": ["an", "apple"]}),
            ("U01-W-03", "PRD", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"grammar_target_match": True}}),
            ("U01-W-04", "CHK", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"complete_response": True}}),
        )
        for key, role, contract in writing:
            contracts.append(
                (
                    key,
                    builder.s01.m01.LESSON_IDS["WRITING"],
                    "WRITING",
                    role,
                    1,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
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
            contracts.append(
                (
                    key,
                    builder.s01.m01.LESSON_IDS["SPEAKING"],
                    "SPEAKING",
                    "PRD",
                    0,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
        connection.executemany(
            "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", contracts
        )
        attempts = [
            (
                "ATTEMPT-JAMES-READING",
                "JAMES",
                "SESSION-JAMES-R",
                builder.s01.m01.LESSON_IDS["READING"],
                "U01-R-01",
                1,
                '"SECRET RAW READING RESPONSE"',
                "2026-07-28T01:00:00Z",
                "0",
                "hash-r",
            ),
            (
                "ATTEMPT-JAMES-WRITING",
                "JAMES",
                "SESSION-JAMES-W",
                builder.s01.m01.LESSON_IDS["WRITING"],
                "U01-W-01",
                1,
                '"SECRET RAW WRITING RESPONSE"',
                "2026-07-28T02:00:00Z",
                "0",
                "hash-w",
            ),
            (
                "ATTEMPT-OTHER-READING",
                "OTHER",
                "SESSION-OTHER-R",
                builder.s01.m01.LESSON_IDS["READING"],
                "U01-R-02",
                1,
                '"OTHER PRIVATE RESPONSE"',
                "2026-07-28T03:00:00Z",
                "0",
                "hash-o",
            ),
        ]
        connection.executemany(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)", attempts
        )
        results = [
            (
                "ATTEMPT-JAMES-READING",
                "EXACT_OPTION",
                "AUTO_PASS",
                1.0,
                0,
                "2026-07-28T01:00:01Z",
                "digest:U01-R-01",
            ),
            (
                "ATTEMPT-JAMES-WRITING",
                "NORMALIZED_TEXT",
                "AUTO_FAIL",
                0.0,
                0,
                "2026-07-28T02:00:01Z",
                "digest:U01-W-01",
            ),
            (
                "ATTEMPT-OTHER-READING",
                "EXACT_OPTION",
                "AUTO_PASS",
                1.0,
                0,
                "2026-07-28T03:00:01Z",
                "digest:U01-R-02",
            ),
        ]
        connection.executemany(
            "INSERT INTO scoring_results VALUES(?,?,?,?,?,?,?)", results
        )
        connection.commit()
    return path


def built(tmp_path: Path) -> tuple[Path, dict, dict, dict]:
    db = database(tmp_path / "learner.sqlite3")
    approved = builder.verified_s01_approved(db)
    safe = builder.build_safe_pack(approved)
    private = builder.build_private_pack(
        safe_pack=safe,
        database_path=db,
        learner_id="JAMES",
    )
    return db, approved, safe, private


def test_safe_pack_is_deterministic_and_contains_no_learner_data(tmp_path: Path) -> None:
    db, approved, safe, _ = built(tmp_path)
    repeated = builder.build_safe_pack(approved)
    assert repeated == safe
    assert safe["pack_role"] == builder.SAFE_PACK_ROLE
    assert safe["private"] is False
    assert len(safe["approved_contexts"]) == 5
    assert len(safe["existing_asset_target_index"]) == 11
    assert len(safe["existing_semantic_signatures"]) == 11
    assert len(set(safe["existing_semantic_signatures"])) == 11
    encoded = json.dumps(safe, ensure_ascii=False).casefold()
    assert '"learner_id"' not in encoded
    assert '"attempt_id"' not in encoded
    assert '"outcome_counts"' not in encoded
    assert "secret raw" not in encoded
    assert builder.file_digest(db) not in encoded


def test_generation_budget_requests_thirteen_fixed_candidates(tmp_path: Path) -> None:
    _, _, safe, _ = built(tmp_path)
    policy = safe["generation_policy"]
    assert policy["existing_activity_count"] == 11
    assert policy["target_total_activity_count"] == 24
    assert policy["requested_new_candidate_count"] == 13
    assert sum(policy["skill_distribution"].values()) == 13
    assert sum(policy["context_distribution"].values()) == 13
    assert sum(policy["question_type_distribution"].values()) == 13
    assert sum(policy["learning_role_distribution"].values()) == 13
    assert sum(policy["support_level_distribution"].values()) == 13
    assert policy["randomization_policy"]["free_runtime_generation_allowed"] is False
    assert policy["randomization_policy"]["approved_item_selection_allowed"] is True
    assert safe["output_contract"]["candidate_only"] is True
    assert safe["output_contract"]["canonical_write_allowed"] is False


def test_private_pack_aggregates_only_selected_learner_target_evidence(tmp_path: Path) -> None:
    _, _, _, private = built(tmp_path)
    assert private["pack_role"] == builder.PRIVATE_PACK_ROLE
    assert private["private"] is True
    assert private["learner_id"] == "JAMES"
    summary = private["learner_attempt_summary"]
    assert summary["attempt_count"] == 2
    assert summary["distinct_attempted_asset_count"] == 2
    assert summary["outcome_counts"] == {"AUTO_FAIL": 1, "AUTO_PASS": 1}
    assert summary["recent_context_ids"] == ["U01-C1-CLASSROOM-BAG"]
    assert "guided_sentence" in summary["weak_question_types"]
    state = private["learner_target_state"]
    assert state["practised_target_ids"]
    assert state["weak_target_ids"]
    assert state["stable_target_ids"] == {}
    assert state["mastered_target_ids"] == {}
    assert state["stable_status"] == "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE"
    assert state["mastery_status"] == "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE"


def test_private_pack_never_contains_raw_responses_hidden_answers_or_attempt_ids(tmp_path: Path) -> None:
    _, _, _, private = built(tmp_path)
    encoded = json.dumps(private, ensure_ascii=False).casefold()
    assert "secret raw" not in encoded
    assert "other private response" not in encoded
    assert '"attempt_id"' not in encoded
    assert '"response_json"' not in encoded
    assert '"accepted_texts"' not in encoded
    assert '"accepted_sequence"' not in encoded
    assert "attempt-james" not in encoded
    assert private["claim_boundaries"]["raw_responses_included"] is False
    assert private["claim_boundaries"]["attempt_ids_included"] is False
    assert private["claim_boundaries"]["mastery_inferred"] is False


def test_safe_and_private_prompts_are_deterministic_candidate_only_inputs(tmp_path: Path) -> None:
    _, _, safe, private = built(tmp_path)
    safe_prompt = builder.render_prompt(safe)
    private_prompt = builder.render_prompt(private)
    assert safe_prompt == builder.render_prompt(safe)
    assert private_prompt == builder.render_prompt(private)
    assert f"CONTEXT_PACK_SHA256={safe['pack_sha256']}" in safe_prompt
    assert f"CONTEXT_PACK_SHA256={private['pack_sha256']}" in private_prompt
    assert "Return exactly one JSON object with a candidate_items array" in safe_prompt
    assert "canonical write permission" in safe_prompt
    assert "SECRET RAW" not in private_prompt


def test_validator_accepts_reproducible_packs_and_rejects_stale_database(tmp_path: Path) -> None:
    db, approved, safe, private = built(tmp_path)
    safe_prompt = builder.render_prompt(safe)
    private_prompt = builder.render_prompt(private)
    report = validator.validate_packs(
        safe_pack=safe,
        private_pack=private,
        approved=approved,
        database_path=db,
        safe_prompt=safe_prompt,
        private_prompt=private_prompt,
    )
    assert report["error_count"] == 0, report
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE scoring_results SET outcome='AUTO_PASS' WHERE attempt_id='ATTEMPT-JAMES-WRITING'"
        )
        connection.commit()
    stale = validator.validate_packs(
        safe_pack=safe,
        private_pack=private,
        approved=approved,
        database_path=db,
        safe_prompt=safe_prompt,
        private_prompt=private_prompt,
    )
    assert stale["error_count"] > 0
    assert any(
        "private_database_binding_invalid" in error
        or "private_pack_not_reproducible" in error
        for error in stale["errors"]
    )


def test_validator_rejects_tampered_safe_pack(tmp_path: Path) -> None:
    db, approved, safe, private = built(tmp_path)
    tampered = copy.deepcopy(safe)
    tampered["generation_policy"]["requested_new_candidate_count"] = 99
    report = validator.validate_packs(
        safe_pack=tampered,
        private_pack=private,
        approved=approved,
        database_path=db,
        safe_prompt=builder.render_prompt(tampered),
        private_prompt=builder.render_prompt(private),
    )
    assert report["error_count"] > 0
    assert any("safe_pack_digest_mismatch" in error for error in report["errors"])
