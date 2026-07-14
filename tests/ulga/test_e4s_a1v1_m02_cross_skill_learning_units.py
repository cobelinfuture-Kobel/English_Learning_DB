from copy import deepcopy
import json

import pytest

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as builder
from ulga.validators import validate_a1_a1plus_cross_skill_learning_units as validator


@pytest.fixture(scope="module")
def artifact():
    return builder.build_artifact()


def test_m02_builds_24_shared_learning_units_covering_109_rows(artifact):
    assert artifact["task_id"] == builder.TASK_ID
    assert artifact["scope"] == "A1_A1_PLUS_ONLY"
    assert artifact["schema_version"] == builder.SCHEMA_VERSION
    assert artifact["coverage_summary"] == {
        "learning_unit_count": 24,
        "canonical_egp_row_count": 109,
        "candidate_four_skill_path_complete_unit_count": 24,
        "operator_approved_text_mode_unit_count": 24,
        "selected_grammar_binding_unit_count": 24,
        "pending_content_authority_binding_unit_count": 24,
    }
    assert len(artifact["learning_units"]) == 24
    assert len(artifact["by_grammar_unit_id"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert [unit["sequence_index"] for unit in artifact["learning_units"]] == list(
        range(1, 25)
    )


def test_m02_schema_is_closed_and_matches_built_unit_contract(artifact):
    schema = json.loads(builder.SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == validator.REQUIRED_TOP_LEVEL_FIELDS
    assert schema["x_policy"]["a1_a1plus_only"] is True
    assert schema["x_policy"]["per_unit_authority_mapping_invention_allowed"] is False
    assert schema["x_policy"]["a2_a2plus_progression_allowed"] is False
    assert set(artifact["learning_units"][0]) == validator.REQUIRED_TOP_LEVEL_FIELDS


def test_m02_keeps_unproven_content_authority_mappings_pending(artifact):
    for unit in artifact["learning_units"]:
        bindings = unit["authority_bindings"]
        assert bindings["grammar"]["selection_status"] == "SELECTED"
        assert bindings["grammar"]["selected_refs"] == [unit["grammar_unit_id"]]
        for authority in validator.PENDING_AUTHORITIES:
            binding = bindings[authority]
            assert binding["selection_status"] == "PENDING_CONTENT_BINDING"
            assert binding["selected_refs"] == []
            assert binding["allowed_pool_count"] == len(binding["allowed_pool_refs"])
            assert binding["allowed_pool_count"] > 0
            assert binding["reason"] == (
                "NO_DIRECT_PER_UNIT_SOURCE_EVIDENCE_DO_NOT_INVENT_MAPPING"
            )


def test_m02_preserves_four_skill_paths_without_false_real_evidence(artifact):
    for unit in artifact["learning_units"]:
        paths = unit["skill_bindings"]
        assert set(paths) == set(builder.SKILLS)
        for skill in builder.SKILLS:
            assert len(paths[skill]["activity_ids"]) == 4
            assert len(paths[skill]["assessment_ids"]) == 1
            assert paths[skill]["actual_evidence_status"] == "NOT_COLLECTED"
        assert paths["listening"]["audio_asset_status"] == "NOT_RENDERED"
        assert paths["speaking"]["audio_capture_status"] == "NOT_IMPLEMENTED"
        assert paths["speaking"]["asr_status"] == "NOT_IMPLEMENTED"
        assert unit["answer_scoring_binding"]["shared_contract_status"] == (
            "M03_NOT_CERTIFIED"
        )
        assert unit["assessment_binding"]["mixed_assessment_status"] == (
            "M08_NOT_CERTIFIED"
        )
        assert unit["readiness"]["learning_unit_contract_complete"] is True
        assert unit["readiness"]["candidate_four_skill_paths_complete"] is True
        assert unit["readiness"]["shared_item_contract_complete"] is False
        assert all(value is False for value in unit["claim_boundaries"].values())


def test_m02_validator_passes_and_routes_to_m03(artifact):
    report = validator.validate_artifact(artifact)
    assert report["validation_status"] == validator.PASS_STATUS
    assert report["errors"] == []
    assert report["validation_counts"]["learning_unit_count"] == 24
    assert report["validation_counts"]["canonical_egp_row_count"] == 109
    assert report["validation_counts"]["a1_unit_count"] > 0
    assert report["validation_counts"]["a1_plus_unit_count"] > 0
    assert report["stop_reason"] == "NONE"
    assert report["next_short_step"] == builder.NEXT_SHORT_STEP


def test_m02_validator_fails_closed_on_invented_authority_mapping(artifact):
    tampered = deepcopy(artifact)
    unit = tampered["learning_units"][0]
    unit["authority_bindings"]["vocabulary"]["selected_refs"] = [
        "ULGA:VOCABULARY:INVENTED"
    ]
    unit["authority_bindings"]["vocabulary"]["selection_status"] = "SELECTED"
    report = validator.validate_artifact(tampered)
    assert report["validation_status"] == "FAIL"
    assert any("vocabulary_invented_selected_refs" in error for error in report["errors"])
    assert report["stop_reason"] == "VALIDATION_FAILURE"
    assert report["next_short_step"] is None
