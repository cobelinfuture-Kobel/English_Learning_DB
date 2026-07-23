from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04
from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as builder
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.validators import validate_a1fs_v1_cp05_private_candidate_materialization_and_admission as validator


def _with_hash(value: dict) -> dict:
    value["package_sha256"] = deep.sha256_value(value)
    return value


def _registry() -> dict:
    rows = [
        {
            "material_id": "RAZ_A1A1PLUS_MATERIAL_000000000000000000000001",
            "semantic_duplicate_group_id": "G1",
            "selected_source_unit_ref": "A_PAGE_001",
            "source_level": "A",
            "source_book_id": "BOOK_A",
            "authority_links": [],
            "candidate_cefr_scope": "A1",
            "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
            "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
        },
        {
            "material_id": "RAZ_A1A1PLUS_MATERIAL_000000000000000000000002",
            "semantic_duplicate_group_id": "G2",
            "selected_source_unit_ref": "B_PAGE_002",
            "source_level": "B",
            "source_book_id": "BOOK_B",
            "authority_links": [],
            "candidate_cefr_scope": "A1_PLUS",
            "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
            "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
        },
    ]
    return _with_hash(
        {
            "task_id": registry.TASK_ID,
            "schema_version": registry.SCHEMA_VERSION,
            "validation_status": registry.PASS_STATUS,
            "promoted_material_registry": rows,
            "aggregate_summary": {"final_promoted_material_count": 2},
            "errors": [],
        }
    )


def _dedup() -> dict:
    rows = [
        {
            "semantic_duplicate_group_id": "G1",
            "selected_source_unit_ref": "A_PAGE_001",
            "four_skill_affordances": ["READING_SOURCE", "WRITING_MODEL"],
        },
        {
            "semantic_duplicate_group_id": "G2",
            "selected_source_unit_ref": "B_PAGE_002",
            "four_skill_affordances": ["LISTENING_ADAPTATION", "SPEAKING_PROMPT"],
        },
    ]
    return _with_hash(
        {
            "task_id": dedup.TASK_ID,
            "schema_version": dedup.SCHEMA_VERSION,
            "validation_status": dedup.PASS_STATUS,
            "semantic_representatives": rows,
            "errors": [],
        }
    )


def _unit(index: int) -> dict:
    learning_id = f"UNIT_{index:02d}"
    grammar_id = f"GRAMMAR_{index:02d}"
    content = []
    exercises = []
    if index == 1:
        content.append(
            {
                "content_candidate_id": "CONTENT_M11B_1",
                "source_kind": "M11B_REVIEWED_SHARED_ITEM",
                "source_ref": "M11B_ITEM_1",
                "skill": "reading",
            }
        )
        exercises.append(
            {
                "exercise_candidate_id": "EXERCISE_M11B_1",
                "content_candidate_id": "CONTENT_M11B_1",
                "source_kind": "M11B_REVIEWED_SHARED_ITEM",
                "source_ref": "M11B_ITEM_1",
                "target_skill_lanes": ["reading"],
            }
        )
    material_ids = []
    if index in {1, 2}:
        material_ids.append("RAZ_A1A1PLUS_MATERIAL_000000000000000000000001")
    if index == 2:
        material_ids.append("RAZ_A1A1PLUS_MATERIAL_000000000000000000000002")
    for pos, material_id in enumerate(material_ids, start=1):
        content_id = f"CONTENT_RAZ_{index}_{pos}"
        exercise_id = f"EXERCISE_RAZ_{index}_{pos}"
        content.append(
            {
                "content_candidate_id": content_id,
                "source_kind": "RAZ_PROMOTED_MATERIAL",
                "source_ref": material_id,
                "grammar_authority_ref": grammar_id,
            }
        )
        exercises.append(
            {
                "exercise_candidate_id": exercise_id,
                "content_candidate_id": content_id,
                "source_kind": "RAZ_PROMOTED_MATERIAL",
                "source_ref": material_id,
                "target_skill_lanes": [],
            }
        )
    return {
        "learning_unit_id": learning_id,
        "grammar_unit_id": grammar_id,
        "sequence_index": index,
        "internal_stage": "A1" if index <= 14 else "A1_PLUS",
        "canonical_egp_row_ids": [f"EGP_{index:02d}"],
        "content_candidates": content,
        "exercise_candidates": exercises,
        "scene_candidates": [],
    }


def _cp04() -> dict:
    units = [_unit(index) for index in range(1, 25)]
    content_count = sum(len(row["content_candidates"]) for row in units)
    exercise_count = sum(len(row["exercise_candidates"]) for row in units)
    return {
        "task_id": cp04.TASK_ID,
        "program_id": cp04.PROGRAM_ID,
        "schema_version": cp04.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {
            "existing_learning_unit_count": 24,
            "new_learning_unit_count": 0,
            "content_candidate_count": content_count,
            "exercise_candidate_count": exercise_count,
            "ready_reuse_exercise_candidate_count": 1,
            "pending_raz_exercise_derivation_candidate_count": 3,
        },
        "learning_units": units,
        "stop_reason": "NONE",
        "next_short_step": builder.TASK_ID,
    }


def _sources() -> dict:
    return {
        "A_PAGE_001": {"page_unit_id": "A_PAGE_001", "level": "A", "text": "A cat is on the mat."},
        "B_PAGE_002": {"page_unit_id": "B_PAGE_002", "level": "B", "text": "The children can play in the park."},
    }


def test_private_sources_materialize_once_and_bind_to_existing_units():
    candidate = builder.build_policy_candidate(_cp04(), _registry(), _dedup(), _sources())
    payload = candidate["payload"]
    assert candidate["artifact_role"] == "CANDIDATE_JSON"
    assert candidate["learner_facing"] is False
    assert len(payload["learning_units"]) == 24
    assert len(payload["materialized_raz_sources"]) == 2
    assert len(payload["raz_unit_activity_bindings"]) == 3
    assert len(payload["m11b_reuse_activities"]) == 1
    assert payload["coverage_summary"]["new_learning_unit_count"] == 0


def test_independent_candidate_and_policy_admission_round_trip_passes():
    candidate, approved, safe, report = builder.run_pipeline(
        _cp04(), _registry(), _dedup(), _sources()
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert approved["artifact_role"] == "APPROVED_CANONICAL_JSON"
    assert approved["admission"]["status"] == "APPROVED"
    assert approved["learner_facing"] is False
    assert safe["admission_gate"]["runtime_publication_allowed"] is False
    assert safe["next_short_step"] == builder.NEXT_SHORT_STEP


def test_missing_private_source_is_remediated_not_fabricated():
    sources = _sources()
    sources.pop("B_PAGE_002")
    candidate = builder.build_policy_candidate(_cp04(), _registry(), _dedup(), sources)
    payload = candidate["payload"]
    assert payload["coverage_summary"]["raz_materialized_source_count"] == 1
    assert payload["coverage_summary"]["raz_source_remediation_material_count"] == 1
    assert payload["coverage_summary"]["raz_remediation_binding_count"] == 1
    assert any(
        "PRIVATE_SOURCE_UNIT_NOT_RESOLVED" in row["reason_codes"]
        for row in payload["remediation_queue"]
    )


def test_verified_skill_affordances_drive_contracts_without_exact_answers():
    candidate = builder.build_policy_candidate(_cp04(), _registry(), _dedup(), _sources())
    by_id = {
        row["material_id"]: row for row in candidate["payload"]["materialized_raz_sources"]
    }
    first = by_id["RAZ_A1A1PLUS_MATERIAL_000000000000000000000001"]
    second = by_id["RAZ_A1A1PLUS_MATERIAL_000000000000000000000002"]
    assert {row["skill"] for row in first["skill_contracts"]} == {"READING", "WRITING"}
    assert {row["skill"] for row in second["skill_contracts"]} == {"LISTENING", "SPEAKING"}
    assert all(
        contract["scoring_contract"]["automatic_exact_answer"] is False
        for source in by_id.values()
        for contract in source["skill_contracts"]
    )
    assert all(
        not ({"answer", "answer_key", "accepted_texts"} & set(contract))
        for source in by_id.values()
        for contract in source["skill_contracts"]
    )


def test_source_text_tamper_fails_independent_digest_validation():
    candidate = builder.build_policy_candidate(_cp04(), _registry(), _dedup(), _sources())
    tampered = deepcopy(candidate)
    tampered["payload"]["materialized_raz_sources"][0]["source_content"]["text"] = "Changed."
    tampered["artifact_sha256"] = content_policy.digest(
        {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    )
    report = validator.validate_candidate(
        tampered,
        cp04_artifact=_cp04(),
        registry_package=_registry(),
        dedup_package=_dedup(),
    )
    assert report["validation_status"] == "FAIL"
    assert any("source_content_sha256_mismatch" in error for error in report["errors"])


def test_safe_readback_contains_no_private_text_prompt_or_scoring_contract():
    _, _, safe, report = builder.run_pipeline(_cp04(), _registry(), _dedup(), _sources())
    serialized = content_policy.canonical(safe)
    assert report["private_or_learner_content_absent_from_safe_readback"] is True
    assert "A cat is on the mat" not in serialized
    assert '"prompt"' not in serialized
    assert '"scoring_contract"' not in serialized
    assert '"learner_response"' not in serialized


def test_a2_injection_fails_closed():
    package = _registry()
    package["promoted_material_registry"][0]["candidate_cefr_scope"] = "A2"
    core = {key: value for key, value in package.items() if key != "package_sha256"}
    package["package_sha256"] = deep.sha256_value(core)
    with pytest.raises(builder.CP05BuildError, match="material_scope_invalid"):
        builder.build_policy_candidate(_cp04(), package, _dedup(), _sources())
