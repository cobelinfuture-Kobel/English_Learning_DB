from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as builder,
)
from ulga.validators import (
    validate_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as validator,
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
            rows.append((key, builder.s02.s01.m01.LESSON_IDS["READING"], "READING", role, 1, json.dumps(contract), f"digest:{key}"))
        writing = (
            ("U01-W-01", "PRD", {"scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["a bag"], "accepted_sequence": []}),
            ("U01-W-02", "PRD", {"scoring_mode": "EXACT_SEQUENCE", "response_type": "sequence", "accepted_texts": [], "accepted_sequence": ["an", "apple"]}),
            ("U01-W-03", "PRD", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"grammar_target_match": True}}),
            ("U01-W-04", "CHK", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"complete_response": True}}),
        )
        for key, role, contract in writing:
            rows.append((key, builder.s02.s01.m01.LESSON_IDS["WRITING"], "WRITING", role, 1, json.dumps(contract), f"digest:{key}"))
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
            rows.append((key, builder.s02.s01.m01.LESSON_IDS["SPEAKING"], "SPEAKING", "PRD", 0, json.dumps(contract), f"digest:{key}"))
        connection.executemany("INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", rows)
        connection.commit()
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def built(tmp_path: Path) -> tuple[Path, dict, dict, dict]:
    db = database(tmp_path / "learner.sqlite3")
    candidate, safe = builder.build_candidate(db)
    approved = builder.admit_candidate(candidate, safe)
    return db, safe, candidate, approved


def test_builds_thirteen_fixed_items_with_exact_distribution(tmp_path: Path) -> None:
    _, _, candidate, approved = built(tmp_path)
    report = validator.validate_approved(candidate, approved, builder.s02.build_safe_pack(builder.s02.verified_s01_approved(database(tmp_path / "second.sqlite3"))))
    assert report["error_count"] == 0, report
    payload = approved["payload"]
    assert payload["generation_mode"] == "FIXED_OFFLINE_CANDIDATE_BANK"
    assert payload["existing_activity_count"] == 11
    assert payload["new_candidate_item_count"] == 13
    assert payload["target_total_activity_count"] == 24
    assert payload["distribution_counts"]["skill"] == {"READING": 6, "SPEAKING": 3, "WRITING": 4}
    assert payload["distribution_counts"]["context"] == builder.s02.NEW_CONTEXT_DISTRIBUTION
    assert payload["distribution_counts"]["question_type"] == builder.s02.NEW_QUESTION_TYPE_DISTRIBUTION
    assert payload["distribution_counts"]["learning_role"] == builder.s02.LEARNING_ROLE_DISTRIBUTION
    assert payload["distribution_counts"]["support_level"] == builder.s02.SUPPORT_LEVEL_DISTRIBUTION


def test_item_identities_and_semantic_signatures_are_stable_and_unique(tmp_path: Path) -> None:
    db, safe, candidate, _ = built(tmp_path)
    repeated, repeated_safe = builder.build_candidate(db)
    assert repeated == candidate
    assert repeated_safe == safe
    items = candidate["payload"]["candidate_items"]
    assert [row["candidate_item_id"] for row in items] == sorted(row["candidate_item_id"] for row in builder.ITEM_SPECS)
    assert len({row["candidate_item_id"] for row in items}) == 13
    assert len({row["semantic_signature"] for row in items}) == 13
    assert not {row["semantic_signature"] for row in items}.intersection(safe["existing_semantic_signatures"])
    assert all(row["runtime_generation_used"] is False for row in items)
    assert all(row["learner_delivery_status"] == "CANDIDATE_NOT_RUNTIME" for row in items)


def test_all_item_targets_are_inside_safe_authority_inventory(tmp_path: Path) -> None:
    _, safe, candidate, _ = built(tmp_path)
    inventory = safe["target_inventory"]
    fields = {
        "target_evp_sense_ids": set(inventory["evp_sense_ids"]),
        "target_egp_row_ids": set(inventory["egp_row_ids"]),
        "target_chunk_ids": set(inventory["canonical_chunk_ids"]),
        "target_context_phrase_ids": set(inventory["context_phrase_ids"]),
        "target_sentence_ids": set(inventory["sentence_ids"]),
        "target_pattern_ids": set(inventory["pattern_ids"]),
        "target_ket_prerequisite_node_ids": set(inventory["ket_prerequisite_node_ids"]),
    }
    for item in candidate["payload"]["candidate_items"]:
        for field, allowed in fields.items():
            assert set(item[field]).issubset(allowed), (item["candidate_item_id"], field)
        assert item["target_evp_sense_ids"]
        assert item["target_egp_row_ids"]
        assert item["target_pattern_ids"]
        assert item["target_ket_prerequisite_node_ids"] == []
        assert item["cambridge_capability_refs"] == []
        assert item["cambridge_stage"] == "STARTERS"
        assert item["assessment_pattern_ref"] == item["question_type"]


def test_type_specific_response_contracts_and_speaking_boundaries(tmp_path: Path) -> None:
    _, _, candidate, _ = built(tmp_path)
    by_type: dict[str, list[dict]] = {}
    for item in candidate["payload"]["candidate_items"]:
        by_type.setdefault(item["question_type"], []).append(item)
    assert set(by_type) == set(builder.QUESTION_TYPE_CONTRACTS)
    for item in by_type["word_order"]:
        assert isinstance(item["correct_answer"], list)
        assert item["response_contract"]["scoring_mode"] == "EXACT_SEQUENCE"
        assert item["response_contract"]["accepted_sequence"] == item["correct_answer"]
    for item in by_type["checkpoint_write"]:
        assert item["correct_answer"] is None
        assert item["response_contract"]["human_review_fallback"] is True
        assert item["response_contract"]["rubric"]["complete_response"] is True
    speaking = [row for row in candidate["payload"]["candidate_items"] if row["skill"] == "SPEAKING"]
    assert len(speaking) == 3
    assert all(row["correct_answer"] is None for row in speaking)
    assert all(row["response_contract"]["capture_enabled"] is False for row in speaking)
    assert all(row["response_contract"]["rubric"]["practice_only"] is True for row in speaking)


def test_candidate_and_approved_are_private_and_database_is_unchanged(tmp_path: Path) -> None:
    db = database(tmp_path / "learner.sqlite3")
    before = sha(db)
    candidate, safe = builder.build_candidate(db)
    approved = builder.admit_candidate(candidate, safe)
    after = sha(db)
    assert before == after
    assert candidate["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    assert candidate["learner_facing"] is False
    assert approved["learner_facing"] is False
    assert approved["admission"]["decision_ref"] == builder.DECISION_REF
    assert approved["payload"]["claim_boundaries"]["learner_database_written"] is False
    assert approved["payload"]["claim_boundaries"]["runtime_bundle_written"] is False


def test_safe_validation_report_contains_no_hidden_answers(tmp_path: Path) -> None:
    _, safe, candidate, approved = built(tmp_path)
    report = validator.validate_approved(candidate, approved, safe)
    assert report["error_count"] == 0, report
    encoded = json.dumps(report, ensure_ascii=False).casefold()
    assert "an orange and an egg" not in encoded
    assert "there is a toy shop" not in encoded
    assert '"correct_answer"' not in encoded
    assert report["hidden_answers_in_safe_report"] is False


def test_validator_rejects_runtime_generation_or_existing_signature_collision(tmp_path: Path) -> None:
    _, safe, candidate, _ = built(tmp_path)
    tampered = copy.deepcopy(candidate)
    tampered["payload"]["candidate_items"][0]["runtime_generation_used"] = True
    core = {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    tampered["artifact_sha256"] = policy_artifact.digest(core)
    try:
        validator.validate_candidate(tampered, safe)
    except validator.S03ValidationError as exc:
        assert "runtime_generation_used" in str(exc)
    else:
        raise AssertionError("runtime generation did not fail closed")

    collision = copy.deepcopy(candidate)
    collision["payload"]["candidate_items"][0]["semantic_signature"] = safe["existing_semantic_signatures"][0]
    core = {key: value for key, value in collision.items() if key != "artifact_sha256"}
    collision["artifact_sha256"] = policy_artifact.digest(core)
    try:
        validator.validate_candidate(collision, safe)
    except validator.S03ValidationError as exc:
        assert "existing_signature_collision" in str(exc) or "semantic_signature_invalid" in str(exc)
    else:
        raise AssertionError("existing semantic collision did not fail closed")
