from __future__ import annotations

from copy import deepcopy
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as projection
from ulga.validators import validate_a1fs_v1_u01data04a_unit01_canonical_chunk_alias_reconciliation as validator


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


def test_reconciles_exact_three_chunk_aliases_and_keeps_only_real_phrase_gaps(tmp_path: Path) -> None:
    report = built(tmp_path)
    result = validator.validate_report(report)
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["reconciled_alias_count"] == 3
    assert result["remaining_external_support_count"] == 3
    assert result["activity_asset_link_count"] == 60
    assert result["unique_activity_binding_count"] == 20
    assert set(report["linkage_summary"]["unlinked_external_support_target_ids"]) == validator.EXPECTED_EXTERNAL_SUPPORT


def test_aliases_map_to_exact_existing_registry_bindings(tmp_path: Path) -> None:
    report = built(tmp_path)
    rows = report["linkage_summary"]["canonical_chunk_alias_reconciliations"]
    assert {row["source_alias_id"]: row["registry_binding_id"] for row in rows} == validator.EXPECTED_ALIAS_TO_BINDING
    assert all(row["reconciliation_method"] == "EXACT_NORMALIZED_LABEL_UNIQUE_CANONICAL_CHUNK" for row in rows)


def test_activity_status_and_link_counts_match_operator_readback(tmp_path: Path) -> None:
    report = built(tmp_path)
    summary = report["linkage_summary"]
    assert summary["activity_linkage_status_counts"] == validator.EXPECTED_STATUS_COUNTS
    assert summary["activity_asset_link_count"] == 60
    assert summary["unique_activity_linked_registry_binding_count"] == 20


def test_pattern_frame_bridge_stays_unresolved_and_scope_stays_locked(tmp_path: Path) -> None:
    report = built(tmp_path)
    assert report["linkage_summary"]["canonical_pattern_to_unit_frame_bridge_status"] == "UNRESOLVED_RECORDED_NOT_INFERRED"
    assert all(value is False for value in report["boundaries"].values())


def test_alias_reconciliation_fails_closed_on_ambiguous_canonical_surface() -> None:
    indexes = {
        "by_asset": {},
        "by_surface": {
            "ice cream": [
                {"asset_kind": "CANONICAL_CHUNK", "asset_id": "A", "binding_id": "B1"},
                {"asset_kind": "CANONICAL_CHUNK", "asset_id": "C", "binding_id": "B2"},
            ]
        },
    }
    with pytest.raises(projection.ProjectionBuildError, match="CANONICAL_CHUNK_ALIAS_AMBIGUOUS"):
        projection.target_linkage(
            {"target_chunk_ids": ["chunk:ice_cream"]},
            indexes=indexes,
            phrase_labels={},
            chunk_alias_labels={"chunk:ice_cream": "ice cream"},
        )


def test_validator_fails_closed_when_alias_returns_to_external_support(tmp_path: Path) -> None:
    report = built(tmp_path)
    drifted = deepcopy(report)
    drifted["linkage_summary"]["unlinked_external_support_target_ids"].append("chunk:ice_cream")
    unsigned = dict(drifted)
    unsigned.pop("projection_sha256", None)
    drifted["projection_sha256"] = projection.digest(unsigned)
    with pytest.raises(validator.AliasReconciliationValidationError, match="remaining_external_support_set_invalid"):
        validator.validate_report(drifted)
