from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_four_layer_theme_sentence_scene_classification as builder
from ulga.validators import validate_raz_aw_four_layer_theme_sentence_scene_classification as validator


def _classification(refs: list[str]) -> dict:
    return {
        "task_id": "RAZ-AW_DerivedReviewBridgeThemeSentenceSceneClassification",
        "schema_version": "raz.aw.derived_review_bridge_theme_sentence_scene.v1",
        "validation_status": "PASS_RAZ_AW_DERIVED_REVIEW_BRIDGE_CLASSIFICATION",
        "source_scope": {
            "levels": list(builder.three_layer.LEVELS),
            "record_count": len(refs),
            "book_count": len(refs),
            "derived_record_count": len(refs),
            "review_candidate_count": len(refs),
            "bridge_candidate_count": len(refs),
            "source_files": [{"level": level} for level in builder.three_layer.LEVELS],
        },
        "authority_baselines": {"vocabulary": {}, "chunks": {}, "patterns": {}, "themes": {}},
        "theme_situation_candidates": [
            {
                "theme_situation_candidate_id": "TSIT_0000000000000001",
                "source_macro_domain": "School",
            }
        ],
        "sentence_seed_candidates": [
            {"source_unit_ref": ref, "sentence_seed_id": f"SSEED_{index:016X}"}
            for index, ref in enumerate(refs, 1)
        ],
        "scene_seed_candidates": [
            {"source_unit_ref": ref, "scene_seed_id": f"SCENE_{index:016X}"}
            for index, ref in enumerate(refs, 1)
        ],
        "cross_links": [
            {
                "source_unit_ref": ref,
                "theme_situation_candidate_ids": ["TSIT_0000000000000001"],
                "sentence_seed_id": f"SSEED_{index:016X}",
                "scene_seed_id": f"SCENE_{index:016X}",
                "review_candidate_uid": f"{ref}::review",
                "bridge_candidate_uid": f"{ref}::bridge",
            }
            for index, ref in enumerate(refs, 1)
        ],
        "classification_summary": {
            "theme_situation_candidate_count": 1,
            "sentence_seed_candidate_count": len(refs),
            "scene_seed_candidate_count": len(refs),
            "cross_link_count": len(refs),
        },
        "classification_gate": {
            "decision": "THREE_LAYER_CLASSIFICATION_READY_FOR_REVIEW",
            "ready_for_human_review": True,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
        },
    }


def _linkage(refs: list[str]) -> dict:
    return {
        "source_scope": {
            "levels": list(builder.linkage.LEVELS),
            "page_unit_count": len(refs),
            "page_unit_linkage_record_count": len(refs) * 2,
            "source_files": [{"level": level} for level in builder.linkage.LEVELS],
        },
        "page_unit_lineage": [
            {
                "source_unit_ref": ref,
                "source_level": "A",
                "normalized_linkage_uid": f"{ref}::authority_linkage_v1::normalized_page_units",
                "enriched_linkage_uid": f"{ref}::authority_linkage_v1::enriched_units",
                "normalized_trace_confidence": "high",
                "enriched_trace_confidence": "medium",
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
            }
            for ref in refs
        ],
        "integrity_gate": {
            "decision": "LINKAGE_READY_FOR_CLASSIFICATION_LINEAGE",
            "ready_for_classification_lineage": True,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
        },
    }


def _package(refs: list[str]) -> dict:
    return builder.bind_packages(
        _classification(refs),
        _linkage(refs),
        expected_record_count=len(refs),
    )


def test_binds_all_four_layers_by_exact_source_ref():
    refs = ["RAZ_A_1_P001", "RAZ_W_2_P001"]
    package = _package(refs)

    assert package["classification_gate"]["decision"] == "FOUR_LAYER_CLASSIFICATION_READY_FOR_REVIEW"
    assert package["source_scope"]["record_count"] == 2
    assert package["source_scope"]["linkage_page_unit_count"] == 2
    assert package["source_scope"]["linkage_record_count"] == 4
    assert len(package["four_layer_cross_links"]) == 2
    assert all(row["normalized_trace_confidence"] == "high" for row in package["four_layer_cross_links"])
    assert all(row["enriched_trace_confidence"] == "medium" for row in package["four_layer_cross_links"])


def test_ref_set_mismatch_fails_closed():
    with pytest.raises(
        builder.FourLayerClassificationError,
        match="four_layer_ref_set_mismatch",
    ):
        builder.bind_packages(
            _classification(["RAZ_A_1_P001"]),
            _linkage(["RAZ_A_2_P001"]),
            expected_record_count=1,
        )


def test_pending_candidate_and_promotion_boundaries_are_preserved():
    package = _package(["RAZ_A_1_P001"])
    row = package["four_layer_cross_links"][0]

    assert row["authority_status"] == "candidate_only"
    assert row["review_status"] == "pending"
    assert row["promotion_status"] == "promotion_blocked"
    assert "ReadingAuthority" in row["allowed_authority_targets"]
    assert "LearningOpportunityBinding" in row["blocked_authority_targets"]
    assert package["classification_gate"]["ready_for_canonical_promotion"] is False
    assert package["classification_gate"]["ready_for_learning_unit_population"] is False


def test_validator_accepts_deterministic_package_and_rejects_tampering():
    package = _package(["RAZ_A_1_P001", "RAZ_B_2_P001"])
    valid = validator.validate_package(
        package,
        rebuilt=package,
        schema_path=Path(__file__).resolve().parents[2]
        / "ulga/schemas/raz_aw_four_layer_theme_sentence_scene_classification.schema.json",
    )
    assert valid["error_count"] == 0, valid

    tampered = deepcopy(package)
    tampered["four_layer_cross_links"][0]["promotion_status"] = "promoted"
    failed = validator.validate_package(tampered)
    assert "package_sha256_mismatch" in failed["errors"]
    assert any(error.startswith("promotion_status_mismatch") for error in failed["errors"])


def test_safe_package_rejects_source_text_keys():
    package = _package(["RAZ_A_1_P001"])
    package["source_text"] = "forbidden"
    assert builder.scan_forbidden_safe_keys(package)
