from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from ulga.builders import build_raz_aw_linkage_integrity_and_page_unit_lineage as builder
from ulga.validators import validate_raz_aw_linkage_integrity_and_page_unit_lineage as validator


def _trace(level: str, ref: str) -> dict:
    return {
        "source_type": "RAZ",
        "source_level": level,
        "source_book_id": "1",
        "source_book_uid": f"raz_{level}_1",
        "source_page_number": 1,
        "source_page_unit_id": ref,
        "source_passage_unit_id": None,
        "source_sentence_candidate_ids": [],
        "source_sentence_final_ids": [],
        "source_reuse_unit_id": None,
        "raw_file_relative_path": f"Level_{level}/1.json",
        "raw_candidate_ref": None,
        "raw_page_ref": None,
        "deterministic_index_ref": None,
        "derived_from_original_text": True,
        "generated_content": False,
        "generation_method": None,
        "generation_prompt_id": None,
        "generation_task_id": None,
        "trace_confidence": "high",
    }


def _page_record(level: str, ref: str, variant: str) -> dict:
    confidence = "high" if variant == "normalized_page_units" else "medium"
    trace = _trace(level, ref)
    trace["trace_confidence"] = confidence
    return {
        "record_uid": f"{ref}::authority_linkage_v1::{variant}",
        "artifact_layer": "page_unit",
        "source_traceability": trace,
        "authority_status": "candidate_only",
        "promotion_status": "promotion_blocked",
        "review_status": "pending",
        "required_review_before_promotion": "page_unit_review",
        "allowed_authority_targets": ["ReadingAuthority", "ContentQueryLayer"],
        "blocked_authority_targets": [
            "DialogueAuthority",
            "WritingAuthority",
            "AssessmentAuthority",
            "LearningOpportunityBinding",
        ],
        "generated_content": False,
        "derived_from_original_text": True,
        "trace_confidence": confidence,
        "content_hash": None,
        "clean_text_hash": None,
        "contract_patch_notes": ["fixture"],
    }


def _raw_record(level: str) -> dict:
    return {
        "record_uid": f"raz_{level}_1::authority_linkage_v1::raw_source_reference",
        "artifact_layer": "raw_source_reference",
        "source_traceability": _trace(level, ""),
        "authority_status": "candidate_only",
        "promotion_status": "promotion_blocked",
        "review_status": "pending",
        "required_review_before_promotion": "none",
        "allowed_authority_targets": ["None"],
        "blocked_authority_targets": [
            "SentenceAuthority",
            "ReadingAuthority",
            "DialogueAuthority",
            "WritingAuthority",
            "ExerciseAuthority",
            "AssessmentAuthority",
            "ContentQueryLayer",
            "LearningOpportunityBinding",
        ],
        "generated_content": False,
        "derived_from_original_text": True,
        "trace_confidence": "high",
        "content_hash": None,
        "clean_text_hash": None,
        "contract_patch_notes": ["fixture"],
    }


def _write_fixture(root: Path) -> None:
    for index, level in enumerate(builder.LEVELS, 1):
        ref = f"raz_{level}_{index}_p0001"
        records = [
            _raw_record(level),
            _page_record(level, ref, "normalized_page_units"),
            _page_record(level, ref, "enriched_units"),
        ]
        path = (
            root
            / "linkage"
            / f"Level_{level}"
            / f"raz_{level}_authority_linkage_view.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "raz_authority_linkage_contract.v1",
                    "records": records,
                }
            ),
            encoding="utf-8",
        )


def _package(tmp_path: Path) -> dict:
    _write_fixture(tmp_path)
    return builder.load_and_build(
        tmp_path,
        expected_page_unit_count=len(builder.LEVELS),
    )


def test_builds_one_safe_lineage_row_per_page_unit(tmp_path):
    package = _package(tmp_path)
    scope = package["source_scope"]

    assert package["validation_status"] == builder.PASS_STATUS
    assert scope["source_file_count"] == 23
    assert scope["page_unit_count"] == 23
    assert scope["page_unit_linkage_record_count"] == 46
    assert len(package["page_unit_lineage"]) == 23
    assert package["integrity_gate"]["decision"] == "LINKAGE_READY_FOR_CLASSIFICATION_LINEAGE"
    assert all(package["integrity_gate"]["source_checks"].values())


def test_lineage_preserves_candidate_only_and_blocks_learning_opportunity(tmp_path):
    package = _package(tmp_path)
    for row in package["page_unit_lineage"]:
        assert row["authority_status"] == "candidate_only"
        assert row["promotion_status"] == "promotion_blocked"
        assert row["review_status"] == "pending"
        assert row["normalized_trace_confidence"] == "high"
        assert row["enriched_trace_confidence"] == "medium"
        assert "ReadingAuthority" in row["allowed_authority_targets"]
        assert "LearningOpportunityBinding" in row["blocked_authority_targets"]


def test_builder_fails_gate_when_one_variant_is_missing(tmp_path):
    _write_fixture(tmp_path)
    path = (
        tmp_path
        / "linkage/Level_W/raz_W_authority_linkage_view.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"] = [
        row
        for row in payload["records"]
        if not row["record_uid"].endswith("::enriched_units")
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")

    package = builder.load_and_build(
        tmp_path,
        expected_page_unit_count=len(builder.LEVELS),
    )
    assert package["validation_status"] == "FAIL"
    assert package["integrity_gate"]["decision"] == "BLOCKED_LINKAGE_INTEGRITY"
    assert any("page_variant_set_mismatch:W" in error for error in package["errors"])


def test_direct_tree_validator_rejects_nested_level_folders(tmp_path):
    _write_fixture(tmp_path)
    nested = tmp_path / "linkage/Level_R/Level_J"
    nested.mkdir(parents=True)
    (nested / "duplicate.json").write_text("{}", encoding="utf-8")

    errors = validator.validate_direct_tree(tmp_path)
    assert "nested_linkage_folder_forbidden:R:Level_J" in errors


def test_independent_validator_accepts_deterministic_package_and_rejects_tamper(tmp_path):
    package = _package(tmp_path)
    valid = validator.validate_package(
        package,
        rebuilt=package,
        tree_errors=validator.validate_direct_tree(tmp_path),
        schema_path=Path(__file__).resolve().parents[2]
        / "ulga/schemas/raz_aw_linkage_integrity_and_page_unit_lineage.schema.json",
    )
    assert valid["error_count"] == 0, valid

    tampered = deepcopy(package)
    tampered["page_unit_lineage"][0]["promotion_status"] = "promoted"
    failed = validator.validate_package(tampered)
    assert "package_sha256_mismatch" in failed["errors"]
    assert any(
        error.startswith("lineage_promotion_status_mismatch:")
        for error in failed["errors"]
    )


def test_safe_output_contains_no_source_text_keys(tmp_path):
    package = _package(tmp_path)
    assert builder.scan_forbidden_keys(package) == []
    package["source_text"] = "forbidden"
    assert builder.scan_forbidden_keys(package)
