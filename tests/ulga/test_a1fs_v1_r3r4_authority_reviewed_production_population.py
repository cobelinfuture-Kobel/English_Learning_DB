from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.validators.validate_a1fs_v1_r3r4_authority_reviewed_production_population import validate


def _write(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path):
    ontology_path = _write(tmp_path / "ontology.json", r2.build_ontology())
    capability = "REF:READING:SCHOOL_OBJECT_LOCATION"
    graph = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "schema_version": "a1fs.v1.m1.prerequisite_graph_and_coverage.v1",
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "source_baseline_sha256": "a" * 64,
        "nodes": [
            {
                "node_id": capability,
                "node_type": "CAPABILITY",
                "skill": "READING",
                "level": "A1",
                "source_ref": "SCHOOL_OBJECT_LOCATION",
                "mastery_required_before_a2": True,
            },
            {
                "node_id": "LESSON:READING:R-A1-001",
                "node_type": "LESSON",
                "skill": "READING",
                "level": "A1",
                "source_ref": "R-A1-001",
                "mastery_required_before_a2": True,
            },
            {
                "node_id": "GATE:A1FS:A2_LOCK",
                "node_type": "A2_LOCK",
                "skill": "FOUR_SKILL",
                "level": "A2",
                "source_ref": "A2_ENTRY",
                "mastery_required_before_a2": False,
            },
        ],
        "edges": [
            {"from_node_id": capability, "to_node_id": "LESSON:READING:R-A1-001", "edge_type": "TAUGHT_BY"},
            {"from_node_id": capability, "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"},
            {"from_node_id": "LESSON:READING:R-A1-001", "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"},
        ],
        "coverage": [
            {
                "node_id": capability,
                "skill": "READING",
                "source_ref": "SCHOOL_OBJECT_LOCATION",
                "coverage_class": "MASTERY",
                "levels": ["A1"],
                "lesson_ids": ["R-A1-001"],
                "asset_body_ids": ["R-A1-001-CHK"],
                "roles": ["CHK"],
                "coverage_status": "COVERED",
            }
        ],
        "counts": {
            "node_count": 3,
            "edge_count": 3,
            "coverage_record_count": 1,
            "lesson_count": 1,
            "lesson_count_by_level": {"A1": 1, "A1+": 0, "A2": 0},
            "required_mastery_node_count": 2,
            "a2_handoff_lesson_count": 0,
            "uncovered_required_node_count": 0,
        },
        "a2_lock_contract": {
            "gate_node_id": "GATE:A1FS:A2_LOCK",
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": [capability, "LESSON:READING:R-A1-001"],
            "a2_handoff_lesson_node_ids": [],
            "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED",
            "runtime_unlock_implemented": False,
        },
        "claim_boundaries": {
            "source_packages_committed": False,
            "asset_body_content_modified": False,
            "learner_release_approved": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
            "runtime_planner_implemented": False,
            "human_pilot_claimed": False,
            "listening_audio_complete": False,
        },
        "errors": [],
        "next_short_step": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
    }
    graph_path = _write(tmp_path / "graph.json", graph)
    payloads = [
        {
            "question": "Choose the school object.",
            "options": ["book", "bus"],
            "private_scoring_contract": {
                "scoring_mode": "EXACT_OPTION",
                "accepted_texts": ["book"],
            },
        },
        {
            "question": "Choose the object on the classroom desk.",
            "options": ["pencil", "train"],
            "private_scoring_contract": {
                "scoring_mode": "EXACT_OPTION",
                "accepted_texts": ["pencil"],
            },
        },
    ]
    assets = []
    for index, payload in enumerate(payloads, start=1):
        assets.append({
            "asset_id": f"R-A1-001-CHK-{index}",
            "asset_key": f"READING:R-A1-001-CHK-{index}",
            "lesson_id": "R-A1-001",
            "skill": "READING",
            "level": "A1",
            "role": "CHK",
            "payload": payload,
            "content_digest": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
    consumer = {
        "task_id": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
        "schema_version": "a1fs.v1.m2.four_skill_asset_body_consumer.v1",
        "validation_status": "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY",
        "source_graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        "asset_records": assets,
        "lesson_catalog": [{
            "lesson_id": "R-A1-001",
            "lesson_node_id": "LESSON:READING:R-A1-001",
            "skill": "READING",
            "level": "A1",
            "asset_keys": [row["asset_key"] for row in assets],
            "roles": ["CHK"],
            "requirement_node_ids": [capability],
            "release_scope": "PRIVATE_INTERNAL_D0",
        }],
        "counts": {
            "asset_record_count": 2,
            "lesson_count": 1,
            "learning_lesson_count": 1,
            "a2_handoff_lesson_count": 0,
        },
        "access_contract": {
            "visibility": "PRIVATE_INTERNAL",
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
            "a2_handoff_metadata_allowed": True,
            "max_query_limit": 100,
            "filter_fields": ["skill", "level", "lesson_id", "role", "requirement_node_id"],
        },
        "claim_boundaries": {
            "learner_ui_implemented": False,
            "learner_state_implemented": False,
            "planner_implemented": False,
            "mastery_claimed": False,
            "learner_release_approved": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "next_short_step": "A1FS-V1-M3_LearnerProfileSessionAndStateStorage",
    }
    consumer_path = _write(tmp_path / "consumer.json", consumer)
    return ontology_path, graph_path, consumer_path


def test_materializes_partial_profiles_and_ready_practice_bank(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(population, "REPO_ROOT", tmp_path)
    ontology, graph, consumer = _fixture(tmp_path)
    output = tmp_path / ".local" / "population"
    report = population.materialize(
        ontology_path=ontology,
        graph_path=graph,
        consumer_path=consumer,
        output_root=output,
        reviewed_at="2026-07-19T01:00:00Z",
    )
    assert report["validation_status"] == population.STATUS
    assert report["counts"]["profile_partial_count"] == 1
    assert report["counts"]["profile_placeholder_cell_count"] == 1
    assert report["counts"]["approved_practice_item_count"] == 2
    assert report["counts"]["ready_for_local_selection_cell_count"] == 1
    assert report["claim_boundaries"]["complete_breadth_denominator_reduced"] is False

    profiles = json.loads((output / population.PROFILE_OUTPUT).read_text())
    assert profiles["profiles"][0]["profile_state"] == population.PARTIAL_PROFILE_STATE
    assert "NOT_POPULATED" in profiles["profiles"][0]["dimension_states"].values()
    coverage = json.loads((output / population.COVERAGE_OUTPUT).read_text())
    assert {row["status"] for row in coverage["cells"]} == {"DEPLOYED", "PROFILE_DEFINITION_REQUIRED"}
    bank = json.loads((output / population.BANK_OUTPUT).read_text())
    assert bank["item_count"] == 2
    population.safe_scan(report)

    result = validate(
        ontology_path=ontology,
        graph_path=graph,
        consumer_path=consumer,
        output_root=output,
    )
    assert result["error_count"] == 0, result["errors"]


def test_consumer_graph_binding_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(population, "REPO_ROOT", tmp_path)
    ontology, graph, consumer = _fixture(tmp_path)
    value = json.loads(consumer.read_text())
    value["source_graph_sha256"] = "0" * 64
    consumer.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(population.ProductionPopulationError, match="consumer_graph_binding_mismatch"):
        population.materialize(
            ontology_path=ontology,
            graph_path=graph,
            consumer_path=consumer,
            output_root=tmp_path / ".local" / "population",
            reviewed_at="2026-07-19T01:00:00Z",
        )


def test_missing_visible_option_is_rejected_without_hiding_profile_gap(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(population, "REPO_ROOT", tmp_path)
    ontology, graph, consumer = _fixture(tmp_path)
    value = json.loads(consumer.read_text())
    for asset in value["asset_records"]:
        asset["payload"].pop("options", None)
    consumer.write_text(json.dumps(value), encoding="utf-8")
    report = population.materialize(
        ontology_path=ontology,
        graph_path=graph,
        consumer_path=consumer,
        output_root=tmp_path / ".local" / "population",
        reviewed_at="2026-07-19T01:00:00Z",
    )
    assert report["counts"]["approved_practice_item_count"] == 0
    assert report["counts"]["profile_not_populated_count"] == 1
    assert report["counts"]["profile_placeholder_cell_count"] == 1
    assert report["next_short_step"] == population.TASK_ID
    assert report["counts"]["rejected_projection_counts"]["EXACT_OPTION_VISIBLE_OPTIONS_MISSING"] == 2


def test_materialization_identity_is_stable_across_review_times(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(population, "REPO_ROOT", tmp_path)
    ontology, graph, consumer = _fixture(tmp_path)
    first_root = tmp_path / ".local" / "population_first"
    second_root = tmp_path / ".local" / "population_second"
    first_report = population.materialize(
        ontology_path=ontology, graph_path=graph, consumer_path=consumer,
        output_root=first_root, reviewed_at="2026-07-19T01:00:00Z",
    )
    second_report = population.materialize(
        ontology_path=ontology, graph_path=graph, consumer_path=consumer,
        output_root=second_root, reviewed_at="2026-07-19T02:00:00Z",
    )
    first_bank = json.loads((first_root / population.BANK_OUTPUT).read_text(encoding="utf-8"))
    second_bank = json.loads((second_root / population.BANK_OUTPUT).read_text(encoding="utf-8"))
    first_supply = json.loads((first_root / population.SUPPLY_OUTPUT).read_text(encoding="utf-8"))
    second_supply = json.loads((second_root / population.SUPPLY_OUTPUT).read_text(encoding="utf-8"))
    first_candidates = json.loads((first_root / population.CANDIDATE_OUTPUT).read_text(encoding="utf-8"))
    second_candidates = json.loads((second_root / population.CANDIDATE_OUTPUT).read_text(encoding="utf-8"))

    assert first_report["reviewed_at"] != second_report["reviewed_at"]
    assert first_candidates["candidates_sha256"] != second_candidates["candidates_sha256"]
    assert first_candidates["semantic_sha256"] == second_candidates["semantic_sha256"]
    assert first_bank == second_bank
    assert first_bank["bank_sha256"] == second_bank["bank_sha256"]
    assert first_supply == second_supply
    assert first_supply["report_sha256"] == second_supply["report_sha256"]
    assert all("reviewed_at" not in item["authority_review"] for item in first_bank["items"])
