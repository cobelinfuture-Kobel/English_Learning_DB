from __future__ import annotations

from copy import deepcopy
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as projection
from ulga.validators import validate_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as validator


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
            rows.append((key, projection.s01.m01.LESSON_IDS["READING"], "READING", role, 1, json.dumps(contract), f"digest:{key}"))
        writing = (
            ("U01-W-01", "PRD", {"scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["a bag"], "accepted_sequence": []}),
            ("U01-W-02", "PRD", {"scoring_mode": "EXACT_SEQUENCE", "response_type": "sequence", "accepted_texts": [], "accepted_sequence": ["an", "apple"]}),
            ("U01-W-03", "PRD", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"grammar_target_match": True}}),
            ("U01-W-04", "CHK", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"complete_response": True}}),
        )
        for key, role, contract in writing:
            rows.append((key, projection.s01.m01.LESSON_IDS["WRITING"], "WRITING", role, 1, json.dumps(contract), f"digest:{key}"))
        for index in range(1, 4):
            key = f"U01-S-{index:02d}"
            contract = {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "human_review_fallback": True, "rubric": {"practice_only": True}}
            rows.append((key, projection.s01.m01.LESSON_IDS["SPEAKING"], "SPEAKING", "PRD", 0, json.dumps(contract), f"digest:{key}"))
        connection.executemany("INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", rows)
        connection.commit()
    return path


def approval() -> dict:
    return {
        "task_id": "A1FS-V1-RAZQ01B2_Unit01V2ApprovalReplayConsumerReconciliation",
        "unit_id": projection.UNIT_ID,
        "decision_status": "APPROVED_AS_RECONCILED",
        "approved_contract_sha256": projection.u01data01.APPROVED_CONTRACT_SHA256,
        "boundaries": {
            "unit02_to_unit24_modified": False,
            "canonical_question_bank_written": False,
            "learner_facing_content_written": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "parallel_curriculum_created": False,
        },
    }


def built(tmp_path: Path) -> dict:
    return projection.build_projection(
        database_path=database(tmp_path / "learner.sqlite3"),
        contract=contract_builder.build_contract(),
        approval=approval(),
    )


def test_links_existing_u01e_pipeline_without_parallel_bank(tmp_path: Path) -> None:
    report = built(tmp_path)
    result = validator.validate_report(report)
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["registry_binding_count"] == 91
    assert result["context_count"] == 5
    assert result["sentence_count"] == 18
    assert result["activity_count"] == 24
    assert result["activity_count_by_skill"] == {"READING": 10, "SPEAKING": 6, "WRITING": 8}
    assert report["ownership_contract"]["projection_creates_parallel_content"] is False
    assert report["ownership_contract"]["projection_copies_question_or_answer_content"] is False


def test_preserves_existing_context_sentence_and_activity_identities(tmp_path: Path) -> None:
    report = built(tmp_path)
    contexts = report["context_projections"]
    sentences = report["sentence_asset_projections"]
    groups = report["activity_projections"]
    assert {row["context_id"] for row in contexts} == {row["context_id"] for row in projection.s01.CONTEXTS}
    expected_sentences = {row["sentence_id"] for row in projection.s01.sentence_rows()}
    assert {row["sentence_id"] for row in sentences} == expected_sentences
    assert {row["activity_id"] for row in groups["existing_response_contract_activities"]} == {
        "U01-R-01", "U01-R-02", "U01-R-03", "U01-R-04",
        "U01-W-01", "U01-W-02", "U01-W-03", "U01-W-04",
        "U01-S-01", "U01-S-02", "U01-S-03",
    }
    assert {row["activity_id"] for row in groups["fixed_admitted_items"]} == {
        str(row["candidate_item_id"]) for row in projection.s03.ITEM_SPECS
    }


def test_all_activities_link_to_registry_and_external_support_stays_unpromoted(tmp_path: Path) -> None:
    report = built(tmp_path)
    activities = [
        *report["activity_projections"]["existing_response_contract_activities"],
        *report["activity_projections"]["fixed_admitted_items"],
    ]
    assert all(row["linked_registry_binding_ids"] for row in activities)
    assert all(row["linkage_status"] in {"LINKED_TO_CUMULATIVE_REGISTRY", "LINKED_WITH_EXTERNAL_SUPPORT"} for row in activities)
    assert report["linkage_summary"]["unlinked_external_support_target_ids"]
    assert report["linkage_summary"]["unlinked_external_support_is_promoted_to_registry"] is False
    assert report["linkage_summary"]["canonical_pattern_to_unit_frame_bridge_status"] == "UNRESOLVED_RECORDED_NOT_INFERRED"


def test_sentence_and_activity_reuse_is_reference_only(tmp_path: Path) -> None:
    report = built(tmp_path)
    rows = [
        *report["sentence_asset_projections"],
        *report["activity_projections"]["existing_response_contract_activities"],
        *report["activity_projections"]["fixed_admitted_items"],
    ]
    assert all(row["introduced_unit_id"] == projection.UNIT_ID for row in rows)
    assert all(row["copy_on_reuse"] is False for row in rows)
    assert all(row["future_unit_reference_allowed"] is True for row in rows)
    assert all("RECOMBINATION" in row["eligible_future_unit_roles"] for row in rows)
    assert report["cumulative_reuse_contract"]["full_cumulative_pool_may_not_be_assigned_as_one_lesson"] is True


def test_projection_contains_no_question_or_answer_payload(tmp_path: Path) -> None:
    report = built(tmp_path)
    encoded = json.dumps(report, ensure_ascii=False)
    for key in validator.FORBIDDEN_KEYS:
        assert f'"{key}"' not in encoded
    assert all(value is False for value in report["boundaries"].values())


def test_validator_fails_closed_on_identity_copy_or_a2_drift(tmp_path: Path) -> None:
    report = built(tmp_path)
    drifted = deepcopy(report)
    drifted["activity_projections"]["fixed_admitted_items"][0]["copy_on_reuse"] = True
    with pytest.raises(validator.ProjectionValidationError, match="activity_reuse_invalid"):
        validator.validate_report(drifted)
    drifted = deepcopy(report)
    drifted["boundaries"]["a2_unlocked"] = True
    with pytest.raises(validator.ProjectionValidationError, match="boundary_drift"):
        validator.validate_report(drifted)


def test_repository_approval_integrates_with_projection(tmp_path: Path) -> None:
    approved = json.loads(Path("ulga/graph/a1fs_v1_razq01b2_unit01_content_contract_approval_v2.json").read_text(encoding="utf-8"))
    report = projection.build_projection(database_path=database(tmp_path / "repository.sqlite3"), contract=contract_builder.build_contract(), approval=approved)
    result = validator.validate_report(report)
    assert result["activity_count"] == 24
    assert report["source_identity"]["s03_item_bank_id"] == projection.s03.ITEM_BANK_ID
