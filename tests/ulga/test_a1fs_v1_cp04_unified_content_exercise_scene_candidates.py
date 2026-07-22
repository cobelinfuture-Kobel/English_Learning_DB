from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as cp03
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as builder
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.validators import validate_a1fs_v1_cp04_unified_content_exercise_scene_candidates as validator


def _material(material_id: str, grammar_refs: list[str], scope: str) -> dict:
    return {
        "material_id": material_id,
        "semantic_duplicate_group_id": f"GROUP_{material_id}",
        "selected_source_unit_ref": f"SOURCE_{material_id}",
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "authority_links": [
            {
                "authority_type": "GRAMMAR",
                "authority_ref": grammar_ref,
                "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
            }
            for grammar_ref in grammar_refs
        ],
        "candidate_cefr_scope": scope,
        "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
        "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
    }


def _registry_package() -> dict:
    promoted = [
        _material(
            "RAZ_A1A1PLUS_MATERIAL_000000000000000000000001",
            ["GRAMMAR_ARTICLES_BASIC"],
            "A1",
        ),
        _material(
            "RAZ_A1A1PLUS_MATERIAL_000000000000000000000002",
            ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_OBJECT_PRONOUNS_BASIC"],
            "A1_PLUS",
        ),
    ]
    package = {
        "task_id": registry.TASK_ID,
        "schema_version": registry.SCHEMA_VERSION,
        "validation_status": registry.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {},
        "promoted_material_registry": promoted,
        "remediation_queue": [],
        "support_registry": [],
        "rejected_registry": [],
        "duplicate_bindings": [],
        "aggregate_summary": {"final_promoted_material_count": len(promoted)},
        "material_registry_gate": {
            "decision": "A1_A1PLUS_MATERIAL_REGISTRY_READY",
            "ready_for_final_coverage_reconciliation": True,
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _cp03_artifact() -> dict:
    cp01_artifact = cp03._read(cp03.CP01_PATH)
    cp02_artifact = cp03._read(cp03.CP02_PATH)
    return cp03.build_artifact(cp01_artifact, cp02_artifact, _registry_package())


def _build() -> tuple[dict, dict]:
    source = _cp03_artifact()
    return builder.build_artifact(source), source


def test_cp04_builds_unified_candidate_envelopes_without_new_units() -> None:
    artifact, source = _build()
    report = validator.validate_artifact(artifact, source)

    assert report["validation_status"] == builder.PASS_STATUS
    assert report["errors"] == []
    assert len(artifact["learning_units"]) == 24
    assert artifact["coverage_summary"]["new_learning_unit_count"] == 0
    assert artifact["coverage_summary"]["m11b_reviewed_content_candidate_count"] == 184
    assert artifact["coverage_summary"]["raz_material_binding_candidate_count"] == 3
    assert artifact["coverage_summary"]["distinct_raz_material_source_count"] == 2
    assert artifact["coverage_summary"]["content_candidate_count"] == 187
    assert artifact["coverage_summary"]["exercise_candidate_count"] == 187
    assert artifact["coverage_summary"]["ready_reuse_exercise_candidate_count"] == 184
    assert artifact["coverage_summary"][
        "pending_raz_exercise_derivation_candidate_count"
    ] == 3


def test_cp04_reuses_m11b_exercises_and_keeps_raz_derivation_pending() -> None:
    artifact, _ = _build()
    m11b_exercises = [
        exercise
        for unit in artifact["learning_units"]
        for exercise in unit["exercise_candidates"]
        if exercise["source_kind"] == "M11B_REVIEWED_SHARED_ITEM"
    ]
    raz_exercises = [
        exercise
        for unit in artifact["learning_units"]
        for exercise in unit["exercise_candidates"]
        if exercise["source_kind"] == "RAZ_PROMOTED_MATERIAL"
    ]

    assert len(m11b_exercises) == 184
    assert all(
        row["candidate_state"] == "READY_FOR_PRIVATE_POPULATION"
        and row["new_content_authoring_required"] is False
        and len(row["target_skill_lanes"]) == 1
        for row in m11b_exercises
    )
    assert len(raz_exercises) == 3
    assert all(
        row["candidate_state"] == "PENDING_PRIVATE_SOURCE_AND_SKILL_AFFORDANCE"
        and row["new_content_authoring_required"] is True
        and row["target_skill_lanes"] == []
        for row in raz_exercises
    )


def test_cp04_scenes_use_only_cp02_source_proven_theme_refs() -> None:
    artifact, source = _build()
    source_by_id = {row["learning_unit_id"]: row for row in source["learning_units"]}
    expected_scene_count = 0

    for unit in artifact["learning_units"]:
        expected_refs = source_by_id[unit["learning_unit_id"]]["cp02_authority_bindings"][
            "theme_situation"
        ]["selected_refs"]
        actual_refs = [row["theme_situation_ref"] for row in unit["scene_candidates"]]
        assert actual_refs == expected_refs
        assert all(row["scene_materialized"] is False for row in unit["scene_candidates"])
        expected_scene_count += len(expected_refs)

    assert artifact["coverage_summary"]["scene_candidate_count"] == expected_scene_count


def test_cp04_validator_rejects_25th_unit_and_private_content_leak() -> None:
    artifact, source = _build()
    extra = deepcopy(artifact["learning_units"][0])
    extra["learning_unit_id"] = "RAZ_PARALLEL_UNIT"
    extra["grammar_unit_id"] = "RAZ_PARALLEL_GRAMMAR"
    extra["sequence_index"] = 25
    artifact["learning_units"].append(extra)
    artifact["learning_units"][0]["content_candidates"][0]["prompt"] = "forbidden"

    report = validator.validate_artifact(artifact, source)
    assert report["validation_status"] == "FAIL"
    assert "output_learning_unit_count_not_24" in report["errors"]
    assert "existing_24_unit_identity_set_mismatch" in report["errors"]
    assert "private_or_learner_content_leak:prompt" in report["errors"]


def test_cp04_fails_closed_when_cp03_lineage_is_not_current() -> None:
    source = _cp03_artifact()
    source["next_short_step"] = "STALE_TASK"

    try:
        builder.build_artifact(source)
    except builder.CandidateBuildError as exc:
        assert str(exc) == "cp03_next_short_step_mismatch"
    else:
        raise AssertionError("stale CP03 lineage must fail closed")


def test_cp04_is_metadata_only_policy_exempt_builder() -> None:
    assert builder.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert builder.A1FS_CONTENT_POLICY_EXEMPTION
