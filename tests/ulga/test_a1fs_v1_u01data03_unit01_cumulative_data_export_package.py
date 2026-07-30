from __future__ import annotations

from copy import deepcopy
import csv
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry as u01data01
from ulga.builders import build_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as u01data02
from ulga.exporters import export_a1fs_v1_u01data03_unit01_cumulative_data_package as exporter
from ulga.validators import validate_a1fs_v1_u01data03_unit01_cumulative_data_export_package as validator


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
            rows.append((key, u01data02.s01.m01.LESSON_IDS["READING"], "READING", role, 1, json.dumps(contract), f"digest:{key}"))
        writing = (
            ("U01-W-01", "PRD", {"scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["a bag"], "accepted_sequence": []}),
            ("U01-W-02", "PRD", {"scoring_mode": "EXACT_SEQUENCE", "response_type": "sequence", "accepted_texts": [], "accepted_sequence": ["an", "apple"]}),
            ("U01-W-03", "PRD", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"grammar_target_match": True}}),
            ("U01-W-04", "CHK", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"complete_response": True}}),
        )
        for key, role, contract in writing:
            rows.append((key, u01data02.s01.m01.LESSON_IDS["WRITING"], "WRITING", role, 1, json.dumps(contract), f"digest:{key}"))
        for index in range(1, 4):
            key = f"U01-S-{index:02d}"
            contract = {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "human_review_fallback": True, "rubric": {"practice_only": True}}
            rows.append((key, u01data02.s01.m01.LESSON_IDS["SPEAKING"], "SPEAKING", "PRD", 0, json.dumps(contract), f"digest:{key}"))
        connection.executemany("INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", rows)
        connection.commit()
    return path


def approval() -> dict:
    return {
        "task_id": "A1FS-V1-RAZQ01B2_Unit01V2ApprovalReplayConsumerReconciliation",
        "unit_id": u01data01.UNIT_ID,
        "decision_status": "APPROVED_AS_RECONCILED",
        "approved_contract_sha256": u01data01.APPROVED_CONTRACT_SHA256,
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


def source_reports(tmp_path: Path) -> tuple[dict, dict]:
    contract = contract_builder.build_contract()
    approved = approval()
    registry = u01data01.build_registry(contract, approved)
    projection = u01data02.build_projection(database_path=database(tmp_path / "learner.sqlite3"), contract=contract, approval=approved)
    return registry, projection


def built(tmp_path: Path) -> dict:
    registry, projection = source_reports(tmp_path)
    return exporter.build_export_package(registry, projection)


def test_builds_complete_unit01_data_tables_and_workbook_spec(tmp_path: Path) -> None:
    package = built(tmp_path)
    result = validator.validate_package(package)
    assert result["validation_status"] == validator.PASS_STATUS
    assert package["table_counts"]["assets"] == 91
    assert package["table_counts"]["contexts"] == 5
    assert package["table_counts"]["sentences"] == 18
    assert package["table_counts"]["activities"] == 24
    assert package["table_counts"]["activity_asset_links"] > 0
    assert package["table_counts"]["external_support"] > 0
    assert result["workbook_sheet_count"] == 7


def test_export_preserves_json_authority_and_blocks_excel_writeback(tmp_path: Path) -> None:
    package = built(tmp_path)
    assert package["authority_contract"] == {
        "json_is_authority": True,
        "csv_and_excel_are_one_way_exports": True,
        "excel_writeback_allowed": False,
        "stable_ids_preserved": True,
        "question_or_answer_payload_exported": False,
    }
    spec = package["workbook_spec"]
    assert spec["json_is_authority"] is True
    assert spec["excel_is_one_way_export"] is True
    assert spec["excel_writeback_allowed"] is False
    assert spec["workbook_file_name"] == "A1FS_Unit01_Cumulative_Data.xlsx"


def test_materializes_utf8_csvs_with_exact_headers_and_counts(tmp_path: Path) -> None:
    registry, projection = source_reports(tmp_path)
    registry_path = tmp_path / "registry.json"
    projection_path = tmp_path / "projection.json"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    projection_path.write_text(json.dumps(projection, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "export"
    package = exporter.materialize(registry_path=registry_path, projection_path=projection_path, output_dir=output)
    result = validator.validate_materialized(output)
    assert result["snapshot_sha256"] == package["snapshot_sha256"]
    expected_files = {exporter.SNAPSHOT_NAME, exporter.WORKBOOK_SPEC_NAME, *exporter.FILE_NAMES.values()}
    assert {path.name for path in output.iterdir()} == expected_files
    with (output / exporter.FILE_NAMES["activities"]).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 24
    assert {row["skill"] for row in rows} == {"READING", "WRITING", "SPEAKING"}


def test_activity_table_exports_identity_and_links_but_no_content(tmp_path: Path) -> None:
    package = built(tmp_path)
    rows = package["tables"]["activities"]
    assert len({row["activity_id"] for row in rows}) == 24
    assert all(row["linked_registry_binding_count"] > 0 for row in rows)
    assert all(row["copy_on_reuse"] is False for row in rows)
    encoded = json.dumps(package, ensure_ascii=False)
    for key in validator.FORBIDDEN_KEYS:
        assert f'"{key}"' not in encoded


def test_external_support_remains_review_only(tmp_path: Path) -> None:
    package = built(tmp_path)
    rows = package["tables"]["external_support"]
    assert rows
    assert all(row["promotion_status"] == "NOT_PROMOTED_TO_U01DATA01_REGISTRY" for row in rows)
    assert all(row["required_action"] == "REVIEW_BEFORE_ANY_CUMULATIVE_CORE_ADMISSION" for row in rows)


def test_export_fails_closed_when_registry_and_projection_digests_drift(tmp_path: Path) -> None:
    registry, projection = source_reports(tmp_path)
    drifted = deepcopy(projection)
    drifted["source_identity"]["u01data01_registry_sha256"] = "0" * 64
    unsigned = dict(drifted); unsigned.pop("projection_sha256", None)
    drifted["projection_sha256"] = u01data02.digest(unsigned)
    with pytest.raises(exporter.ExportError, match="REGISTRY_PROJECTION_DIGEST_MISMATCH"):
        exporter.build_export_package(registry, drifted)


def test_validator_rejects_excel_writeback_or_answer_payload(tmp_path: Path) -> None:
    package = built(tmp_path)
    drifted = deepcopy(package)
    drifted["workbook_spec"]["excel_writeback_allowed"] = True
    with pytest.raises(validator.ExportValidationError, match="workbook_authority_policy_invalid"):
        validator.validate_package(drifted)
    drifted = deepcopy(package)
    drifted["tables"]["activities"][0]["correct_answer"] = "forbidden"
    with pytest.raises(validator.ExportValidationError, match="forbidden_content_keys"):
        validator.validate_package(drifted)
