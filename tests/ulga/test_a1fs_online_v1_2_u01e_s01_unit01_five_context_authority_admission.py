from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as builder,
)
from ulga.validators import (
    validate_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as validator,
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
            rows.append((key, builder.m01.LESSON_IDS["READING"], "READING", role, 1, json.dumps(contract), f"digest:{key}"))
        writing = (
            ("U01-W-01", "PRD", {"scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["a bag"], "accepted_sequence": []}),
            ("U01-W-02", "PRD", {"scoring_mode": "EXACT_SEQUENCE", "response_type": "sequence", "accepted_texts": [], "accepted_sequence": ["an", "apple"]}),
            ("U01-W-03", "PRD", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"grammar_target_match": True}}),
            ("U01-W-04", "CHK", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"complete_response": True}}),
        )
        for key, role, contract in writing:
            rows.append((key, builder.m01.LESSON_IDS["WRITING"], "WRITING", role, 1, json.dumps(contract), f"digest:{key}"))
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
            rows.append((key, builder.m01.LESSON_IDS["SPEAKING"], "SPEAKING", "PRD", 0, json.dumps(contract), f"digest:{key}"))
        connection.executemany("INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", rows)
        connection.commit()
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def built(tmp_path: Path) -> tuple[Path, dict, dict]:
    db = database(tmp_path / "learner.sqlite3")
    candidate = builder.build_candidate(db)
    approved = builder.admit_candidate(candidate)
    return db, candidate, approved


def test_admits_five_fixed_contexts_with_material_first_authority_targets(tmp_path: Path) -> None:
    _, candidate, approved = built(tmp_path)
    report = validator.validate_approved(candidate, approved)
    assert report["error_count"] == 0, report
    payload = approved["payload"]
    assert len(payload["contexts"]) == 5
    assert {row["role"] for row in payload["contexts"]} == {
        "ANCHOR_CONTEXT",
        "NEAR_TRANSFER",
        "EXTENDED_CONTEXT",
        "FUNCTIONAL_DIALOGUE_CONTEXT",
        "UNSEEN_TRANSFER",
    }
    assert " ".join(payload["contexts"][0]["sentences"]) == builder.m01.PASSAGE
    load = payload["learning_load"]
    assert 6 <= load["new_productive_vocabulary_count"] <= 10
    assert 5 <= load["new_receptive_vocabulary_count"] <= 10
    assert 1 <= load["new_canonical_chunk_count"] <= 8
    assert load["new_context_phrase_count"] > 0
    assert 4 <= load["new_chunk_or_phrase_count"] <= 10
    assert 3 <= load["core_sentence_count"] <= 6
    assert load["pattern_count"] > 0


def test_selected_vocabulary_canonical_chunks_and_context_phrases_are_separated(tmp_path: Path) -> None:
    _, _, approved = built(tmp_path)
    payload = approved["payload"]
    material = f" {builder.phrase(builder.all_context_text())} "
    vocabulary = payload["language_targets"]["vocabulary"]
    chunks = payload["language_targets"]["canonical_chunks"]
    context_phrases = payload["language_targets"]["context_phrases"]
    assert len({row["authority_id"] for row in vocabulary}) == len(vocabulary)
    assert all(row["sense_binding_status"] == "UNIQUE_A1_SOURCE_RECORD_ID_BOUND" for row in vocabulary)
    assert all(builder.phrase(row["label"]) in set(builder.words(material)) for row in vocabulary)
    assert len({row["authority_id"] for row in chunks}) == len(chunks)
    assert all(f" {builder.phrase(row['label'])} " in material for row in chunks)
    assert all(row["selection_method"] == "EXACT_A1_GENERATOR_SAFE_CHUNK_IN_FIXED_MATERIAL" for row in chunks)
    assert all(row["coverage_eligible_as_canonical_chunk"] is True for row in chunks)
    assert len({row["phrase_id"] for row in context_phrases}) == len(context_phrases)
    assert all(row["authority_status"] == "PROJECT_PHRASE_NOT_CANONICAL_CHUNK" for row in context_phrases)
    assert all(row["coverage_eligible_as_canonical_chunk"] is False for row in context_phrases)
    assert all(f" {builder.phrase(row['label'])} " in material for row in context_phrases)
    canonical_labels = {builder.phrase(row["label"]) for row in chunks}
    assert all(builder.phrase(row["label"]) not in canonical_labels for row in context_phrases)


def test_resolves_all_eleven_existing_asset_language_targets_without_ket_overclaim(tmp_path: Path) -> None:
    _, _, approved = built(tmp_path)
    payload = approved["payload"]
    rows = payload["existing_asset_target_index"]
    context_phrase_ids = {row["phrase_id"] for row in payload["language_targets"]["context_phrases"]}
    assert len(rows) == 11
    assert len({row["asset_key"] for row in rows}) == 11
    assert {row["skill"] for row in rows} == {"READING", "WRITING", "SPEAKING"}
    assert all(row["binding_status"] == "RESOLVED_LANGUAGE_TARGETS_KET_PENDING" for row in rows)
    assert all(row["target_egp_row_ids"] for row in rows)
    assert all(row["target_pattern_ids"] for row in rows)
    assert all(set(row["target_context_phrase_ids"]).issubset(context_phrase_ids) for row in rows)
    assert all(row["target_ket_prerequisite_node_ids"] == [] for row in rows)
    assert all(
        row["ket_binding_status"] == "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE"
        for row in rows
    )
    assert all(row["cambridge_stage"] == "STARTERS" for row in rows)


def test_candidate_and_approved_never_expose_hidden_answers_or_responses(tmp_path: Path) -> None:
    db, candidate, approved = built(tmp_path)
    before = sha(db)
    encoded = json.dumps({"candidate": candidate, "approved": approved}, ensure_ascii=False).casefold()
    assert '"accepted_texts"' not in encoded
    assert '"accepted_sequence"' not in encoded
    assert '"response_json"' not in encoded
    assert '"correct_answer"' not in encoded
    assert sha(db) == before
    assert candidate["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    assert approved["admission"]["decision_ref"] == builder.DECISION_REF
    assert approved["payload"]["claim_boundaries"]["context_phrases_counted_as_canonical_chunks"] is False


def test_unselected_material_words_keep_explicit_reason(tmp_path: Path) -> None:
    _, _, approved = built(tmp_path)
    rows = approved["payload"]["unselected_material_vocabulary"]
    assert rows
    allowed = {
        "ELIGIBLE_NOT_SELECTED_AMBIGUOUS_A1_SOURCE_IDENTITY",
        "OBSERVED_IN_MATERIAL_ONLY",
        "NOT_SELECTED_NO_A1_AUTHORITY_MATCH",
    }
    assert all(row["status"] in allowed for row in rows)
    assert all("label" in row and "candidate_authority_ids" in row for row in rows)


def test_validator_rejects_invented_authority_ref(tmp_path: Path) -> None:
    _, candidate, _ = built(tmp_path)
    tampered = copy.deepcopy(candidate)
    tampered["payload"]["language_targets"]["vocabulary"][0]["authority_id"] = "vocabulary:invented"
    core = {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    tampered["artifact_sha256"] = policy_artifact.digest(core)
    try:
        validator.validate_candidate(tampered)
    except validator.S01ValidationError as exc:
        assert "vocabulary_ref_invalid" in str(exc)
    else:
        raise AssertionError("invented authority reference did not fail closed")


def test_validator_rejects_context_phrase_claimed_as_canonical_chunk(tmp_path: Path) -> None:
    _, candidate, _ = built(tmp_path)
    tampered = copy.deepcopy(candidate)
    phrase_row = tampered["payload"]["language_targets"]["context_phrases"][0]
    phrase_row["coverage_eligible_as_canonical_chunk"] = True
    core = {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    tampered["artifact_sha256"] = policy_artifact.digest(core)
    try:
        validator.validate_candidate(tampered)
    except validator.S01ValidationError as exc:
        assert "context_phrase_canonical_coverage_invalid" in str(exc)
    else:
        raise AssertionError("context phrase canonical overclaim did not fail closed")
