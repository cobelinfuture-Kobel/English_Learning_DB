from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as projection
from ulga.validators import validate_a1fs_v1_u01data04a_unit01_canonical_chunk_alias_reconciliation as validator


def _database(path: Path) -> Path:
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
            ("U01-R-01", "PRD", ["a cat"]),
            ("U01-R-02", "PRD", ["the book"]),
            ("U01-R-03", "PRD", ["an apple"]),
            ("U01-R-04", "CHK", ["a cat"]),
        )
        for key, role, accepted in reading:
            contract = {
                "scoring_mode": "EXACT_OPTION",
                "response_type": "string",
                "accepted_texts": accepted,
                "accepted_sequence": [],
            }
            rows.append(
                (
                    key,
                    projection.s01.m01.LESSON_IDS["READING"],
                    "READING",
                    role,
                    1,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
        writing = (
            ("U01-W-01", "PRD", "NORMALIZED_TEXT", ["a bag"], []),
            ("U01-W-02", "PRD", "EXACT_SEQUENCE", [], ["an", "apple"]),
            ("U01-W-03", "PRD", "FEATURE_RUBRIC", ["a cat"], []),
            ("U01-W-04", "CHK", "FEATURE_RUBRIC", ["the book"], []),
        )
        for key, role, mode, accepted_texts, accepted_sequence in writing:
            contract = {
                "scoring_mode": mode,
                "response_type": "string" if mode != "EXACT_SEQUENCE" else "sequence",
                "accepted_texts": accepted_texts,
                "accepted_sequence": accepted_sequence,
                "rubric": {"grammar_target_match": True} if mode == "FEATURE_RUBRIC" else {},
            }
            rows.append(
                (
                    key,
                    projection.s01.m01.LESSON_IDS["WRITING"],
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
            rows.append(
                (
                    key,
                    projection.s01.m01.LESSON_IDS["SPEAKING"],
                    "SPEAKING",
                    "PRD",
                    0,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
        connection.executemany("INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", rows)
        connection.commit()
    return path


def _approval() -> dict:
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


def test_u01data04a_alias_reconciliation_ci_gate(tmp_path: Path) -> None:
    report = projection.build_projection(
        database_path=_database(tmp_path / "learner.sqlite3"),
        contract=contract_builder.build_contract(),
        approval=_approval(),
    )
    result = validator.validate_report(report)
    summary = report["linkage_summary"]
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["reconciled_alias_count"] == 3
    assert result["remaining_external_support_count"] == 3
    assert summary["activity_linkage_status_counts"] == {"LINKED_TO_CUMULATIVE_REGISTRY": 17, "LINKED_WITH_EXTERNAL_SUPPORT": 7}
    assert summary["activity_asset_link_count"] == 60
    assert summary["unique_activity_linked_registry_binding_count"] == 20
    assert summary["canonical_pattern_to_unit_frame_bridge_status"] == "UNRESOLVED_RECORDED_NOT_INFERRED"
    assert all(value is False for value in report["boundaries"].values())
