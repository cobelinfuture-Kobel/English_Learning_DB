from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as m02
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04
from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05
from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as builder
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.validators import validate_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as validator


def _learning_id(index: int) -> str:
    return f"UNIT_{index:02d}"


def _grammar_id(index: int) -> str:
    return f"GRAMMAR_{index:02d}"


def _unit_contract() -> dict:
    units = []
    for index in range(1, 25):
        contrasts = []
        if index == 1:
            contrasts = [_learning_id(2)]
        elif index == 2:
            contrasts = [_learning_id(1)]
        prerequisites = [_learning_id(index - 1)] if index > 1 else []
        units.append(
            {
                "learning_unit_id": _learning_id(index),
                "grammar_unit_id": _grammar_id(index),
                "sequence_index": index,
                "internal_stage": "A1" if index <= 14 else "A1_PLUS",
                "canonical_egp_row_ids": [f"EGP_{index:02d}"],
                "prerequisite_unit_ids": prerequisites,
                "learning_content": {"contrast_unit_ids": contrasts},
                "error_remediation_binding": {
                    "error_tags": [f"ERROR_{index:02d}"]
                },
            }
        )
    return {
        "task_id": m02.TASK_ID,
        "scope": "A1_A1_PLUS_ONLY",
        "learning_units": units,
    }


def _cp04() -> dict:
    units = []
    for index in range(1, 25):
        scenes = []
        if index == 1:
            scenes = [
                {
                    "scene_candidate_id": "SCENE_01",
                    "theme_situation_ref": "theme:a1_animals_and_habitats",
                }
            ]
        units.append(
            {
                "learning_unit_id": _learning_id(index),
                "grammar_unit_id": _grammar_id(index),
                "sequence_index": index,
                "internal_stage": "A1" if index <= 14 else "A1_PLUS",
                "canonical_egp_row_ids": [f"EGP_{index:02d}"],
                "scene_candidates": scenes,
            }
        )
    return {
        "task_id": cp04.TASK_ID,
        "schema_version": cp04.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "stop_reason": "NONE",
        "learning_units": units,
    }


def _material(material_id: str, scope: str, themes: list[str]) -> dict:
    return {
        "material_id": material_id,
        "semantic_duplicate_group_id": f"GROUP_{material_id}",
        "selected_source_unit_ref": f"SOURCE_{material_id}",
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "candidate_cefr_scope": scope,
        "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
        "authority_links": [
            {
                "authority_type": "THEME",
                "authority_ref": theme,
                "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
            }
            for theme in themes
        ],
    }


def _registry() -> dict:
    promoted = [
        _material(
            "MATERIAL_1",
            "A1",
            ["theme:a1_animals_and_habitats"],
        ),
        _material("MATERIAL_2", "A1_PLUS", []),
    ]
    package = {
        "task_id": registry.TASK_ID,
        "schema_version": registry.SCHEMA_VERSION,
        "validation_status": registry.PASS_STATUS,
        "promoted_material_registry": promoted,
        "aggregate_summary": {"final_promoted_material_count": len(promoted)},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _raz_binding(binding_id: str, unit_index: int, material_id: str, skills: list[str]) -> dict:
    return {
        "activity_binding_id": binding_id,
        "learning_unit_id": _learning_id(unit_index),
        "grammar_unit_id": _grammar_id(unit_index),
        "canonical_egp_row_ids": [f"EGP_{unit_index:02d}"],
        "content_candidate_id": f"CONTENT_{binding_id}",
        "exercise_candidate_id": f"EXERCISE_{binding_id}",
        "material_id": material_id,
        "target_skill_lanes": skills,
        "admission_status": "ADMITTED_PRIVATE_SOURCE_BOUND_ACTIVITY",
        "runtime_status": "CP06_ROLE_ASSIGNMENT_REQUIRED",
    }


def _cp05_approved() -> dict:
    bindings = [
        _raz_binding("B1", 1, "MATERIAL_1", ["READING"]),
        _raz_binding("B2", 2, "MATERIAL_1", ["READING", "WRITING"]),
        _raz_binding("B3", 15, "MATERIAL_1", ["READING", "SPEAKING"]),
        _raz_binding("B4", 2, "MATERIAL_2", ["LISTENING"]),
    ]
    learning_units = [
        {
            "learning_unit_id": _learning_id(index),
            "grammar_unit_id": _grammar_id(index),
            "sequence_index": index,
            "internal_stage": "A1" if index <= 14 else "A1_PLUS",
            "canonical_egp_row_ids": [f"EGP_{index:02d}"],
        }
        for index in range(1, 25)
    ]
    payload = {
        "task_id": cp05.TASK_ID,
        "program_id": cp05.PROGRAM_ID,
        "schema_version": cp05.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
        "learning_units": learning_units,
        "materialized_raz_sources": [],
        "raz_unit_activity_bindings": bindings,
        "m11b_reuse_activities": [
            {
                "activity_id": "M11B_1",
                "learning_unit_id": _learning_id(1),
                "grammar_unit_id": _grammar_id(1),
                "target_skill": "READING",
                "admission_status": "REUSED_EXISTING_REVIEWED_ADMISSION",
            }
        ],
        "remediation_queue": [],
        "coverage_summary": {
            "existing_learning_unit_count": 24,
            "new_learning_unit_count": 0,
            "raz_distinct_candidate_material_count": 2,
            "raz_admitted_activity_binding_count": 4,
            "m11b_reused_activity_count": 1,
            "listening_audio_generation_pending_binding_count": 1,
            "skill_binding_counts": {
                "LISTENING": 1,
                "READING": 3,
                "SPEAKING": 1,
                "WRITING": 1,
            },
        },
        "claim_boundaries": {"a2_a2plus_in_scope": False},
        "stop_reason": "NONE",
        "next_short_step": builder.TASK_ID,
    }
    candidate = content_policy.build_candidate(
        payload=payload,
        producer_id="fixture_cp05",
        level_scope=["A1", "A1+"],
        source_bindings={"fixture": True},
    )
    return content_policy.admit_candidate(
        candidate,
        validation_receipts=[
            {
                "validator_id": "fixture_validator",
                "status": "PASS",
                "receipt_sha256": "a" * 64,
            }
        ],
        decision_ref="fixture:cp05",
        producer_id="fixture_cp05",
    )


def _build() -> dict:
    return builder.build_artifact(
        _cp05_approved(), _cp04(), _registry(), _unit_contract()
    )


def _by_binding(artifact: dict) -> dict[str, dict]:
    return {
        row["activity_binding_id"]: row
        for row in artifact["raz_activity_role_bindings"]
    }


def test_roles_are_derived_from_real_reappearance_contrast_and_stage_relations():
    artifact = _build()
    rows = _by_binding(artifact)
    assert rows["B1"]["content_roles"] == ["FOCUS", "CONTRAST"]
    assert rows["B2"]["content_roles"] == ["FOCUS", "RECYCLE", "CONTRAST"]
    assert rows["B3"]["content_roles"] == ["FOCUS", "RECYCLE", "TRANSFER"]
    assert rows["B4"]["content_roles"] == ["FOCUS"]


def test_lifecycle_roles_are_eligible_but_not_fabricated_as_runtime_results():
    artifact = _build()
    row = _by_binding(artifact)["B2"]
    lifecycle = row["lifecycle_role_contracts"]
    assert lifecycle["REMEDIATION"]["eligibility_status"] == "ELIGIBLE_NOT_ACTIVATED"
    assert lifecycle["REMEDIATION"]["runtime_activation_performed"] is False
    assert lifecycle["REASSESSMENT"]["runtime_activation_performed"] is False
    assert lifecycle["RETENTION"]["checkpoint_days"] == [1, 3, 7]
    assert lifecycle["RETENTION"]["runtime_schedule_created"] is False


def test_verified_raz_theme_can_close_cp04_scene_capacity_gap_without_invention():
    artifact = _build()
    by_unit = {
        row["learning_unit_id"]: row for row in artifact["unit_content_capacity"]
    }
    assert by_unit[_learning_id(1)]["scene_capacity"]["capacity_status"] == "CP04_AND_RAZ_VERIFIED_THEME"
    assert by_unit[_learning_id(2)]["scene_capacity"]["capacity_status"] == "RAZ_VERIFIED_THEME_ONLY"
    assert by_unit[_learning_id(15)]["scene_capacity"]["capacity_status"] == "RAZ_VERIFIED_THEME_ONLY"
    assert by_unit[_learning_id(3)]["scene_capacity"]["capacity_status"] == "PENDING_SOURCE_EVIDENCE"


def test_validator_passes_deterministic_rebuild_and_rejects_tampering():
    approved = _cp05_approved()
    cp04_artifact = _cp04()
    registry_package = _registry()
    unit_contract = _unit_contract()
    artifact = builder.build_artifact(
        approved, cp04_artifact, registry_package, unit_contract
    )
    report = validator.validate_artifact(
        artifact,
        cp05_approved=approved,
        cp04_artifact=cp04_artifact,
        registry_package=registry_package,
        unit_contract_artifact=unit_contract,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    tampered = deepcopy(artifact)
    tampered["raz_activity_role_bindings"][0]["content_roles"].append("TRANSFER")
    tampered_report = validator.validate_artifact(
        tampered,
        cp05_approved=approved,
        cp04_artifact=cp04_artifact,
        registry_package=registry_package,
        unit_contract_artifact=unit_contract,
    )
    assert tampered_report["validation_status"] == "FAIL"
    assert "artifact_does_not_match_deterministic_rebuild" in tampered_report["errors"]


def test_safe_cp06_output_contains_no_private_text_prompt_or_scoring_contract():
    artifact = _build()
    serialized = json_dumps(artifact)
    assert '"text"' not in serialized
    assert '"prompt"' not in serialized
    assert '"scoring_contract"' not in serialized
    assert '"learner_response"' not in serialized


def json_dumps(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_a2_stage_injection_fails_closed():
    unit_contract = _unit_contract()
    unit_contract["learning_units"][14]["internal_stage"] = "A2"
    with pytest.raises(builder.CP06BuildError, match="unit_contract_identity_or_stage_invalid"):
        builder.build_artifact(
            _cp05_approved(), _cp04(), _registry(), unit_contract
        )


def test_cp06_is_metadata_only_and_does_not_publish_runtime():
    artifact = _build()
    assert builder.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert builder.A1FS_CONTENT_POLICY_EXEMPTION
    assert artifact["capacity_gate"]["runtime_publication_allowed"] is False
    assert artifact["claim_boundaries"]["runtime_role_activation_performed"] is False
    assert artifact["next_short_step"] == builder.NEXT_SHORT_STEP
