from __future__ import annotations

import json
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.validators import validate_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as validator


def _graph(tmp_path: Path) -> Path:
    graph = {
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "nodes": [
            {"node_id": "LESSON:SPEAKING:L1", "node_type": "LESSON", "skill": "SPEAKING", "level": "A1", "source_ref": "L1", "mastery_required_before_a2": True},
            {"node_id": "REF:SPEAKING:ASK_LOCATION", "node_type": "CAPABILITY", "skill": "SPEAKING", "level": "A1", "source_ref": "ASK_LOCATION", "mastery_required_before_a2": True},
            {"node_id": "REF:READING:UNDERSTAND_NOTICE", "node_type": "CAPABILITY", "skill": "READING", "level": "A1+", "source_ref": "UNDERSTAND_NOTICE", "mastery_required_before_a2": True},
            {"node_id": "GATE:A1FS:A2_LOCK", "node_type": "A2_LOCK", "skill": "FOUR_SKILL", "level": "A2", "source_ref": "A2_ENTRY", "mastery_required_before_a2": False},
        ],
        "edges": [],
        "coverage": [],
        "counts": {"required_mastery_node_count": 3},
        "a2_lock_contract": {
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": [
                "LESSON:SPEAKING:L1",
                "REF:SPEAKING:ASK_LOCATION",
                "REF:READING:UNDERSTAND_NOTICE",
            ],
        },
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph), encoding="utf-8")
    return path


def _ontology(tmp_path: Path) -> Path:
    path = tmp_path / "ontology.json"
    path.write_text(json.dumps(r2.build_ontology()), encoding="utf-8")
    return path


def _profile_registry(tmp_path: Path, graph_path: Path, ontology_path: Path) -> Path:
    ontology = json.loads(ontology_path.read_text())
    obligation = {
        "obligation_id": "BREADTH_OBLIGATION_ASK_LOCATION_TRAVEL",
        "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
        "domain": "TRAVEL_TRANSPORT",
        "required_skills": ["SPEAKING"],
        "required_support_levels": ["S1_KEYWORD_OR_VISUAL", "S0_INDEPENDENT"],
        "required_initiative_levels": ["GUIDED_INITIATION", "INDEPENDENT_INITIATION"],
        "required_variation_types": ["EXPECTED_SCRIPT", "REPAIR_REQUIRED"],
        "required_transfer_distances": ["MEDIUM"],
        "required_evidence_levels": ["E3_INDEPENDENT_PRODUCTION", "E4_CROSS_CONTEXT_TRANSFER", "E5_DELAYED_RETENTION"],
        "required_retention_stages": ["DAY_1", "DAY_3", "DAY_7", "RETAINED"],
        "required_media_policy": "OPTIONAL",
        "source_refs": ["A1_C1_CONTEXT_TRAVEL_TRANSPORT"],
    }
    profile = {
        "capability_node_id": "REF:SPEAKING:ASK_LOCATION",
        "capability_id": "CAP_ASK_LOCATION",
        "profile_state": "PROFILE_DEFINED",
        "dimension_states": {field: "POPULATED" for field in r3.PROFILE_DIMENSIONS},
        "dimension_justifications": {},
        "obligations": [obligation],
    }
    profiles = [profile]
    registry = {
        "task_id": r3.TASK_ID,
        "schema_version": r3.PROFILE_SCHEMA_VERSION,
        "source_graph_sha256": r3.file_digest(graph_path),
        "ontology_sha256": ontology["ontology_sha256"],
        "profiles": profiles,
        "profiles_sha256": r3.digest(profiles),
    }
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def _deployment(
    *, evidence_level: str, support: str, transfer: str, retention: str,
    interaction_variation: str = "EXPECTED_SCRIPT", media_state: str = "NOT_REQUIRED",
):
    contract = r2.empty_contract(
        deployment_id=f"EDGE_DEPLOYMENT_{evidence_level}_{support}_{transfer}_{retention}_{interaction_variation}".replace("+", "_"),
        capability_id="CAP_ASK_LOCATION",
        life_task_id="LIFE_TASK_FIND_BUS_STOP",
    )
    values = {
        "level": "A1",
        "domain": "TRAVEL_TRANSPORT",
        "skill": "SPEAKING",
        "support_level": support,
        "initiative_level": "INDEPENDENT_INITIATION" if support == "S0_INDEPENDENT" else "GUIDED_INITIATION",
        "interaction_variation": interaction_variation,
        "transfer_distance": transfer,
        "transfer_dimensions_changed": ["DOMAIN"] if transfer != "NONE" else [],
        "evidence_level": evidence_level,
        "accuracy_result": "PASS",
        "meaning_result": "PASS",
        "task_completion_result": "PASS",
        "pragmatic_result": "PASS",
        "independence_result": "PASS",
        "initiative_result": "PASS",
        "repair_result": "PASS" if interaction_variation == "REPAIR_REQUIRED" else "NOT_APPLICABLE",
        "retention_stage": retention,
        "evidence_validity": "VALID",
        "system_error_status": "NONE",
        "media_requirement": "NONE",
        "media_payload_state": media_state,
        "transcript_state": "NOT_REQUIRED",
        "recording_requirement": "NONE",
        "recording_state": "NOT_REQUIRED",
        "consent_requirement": "NOT_REQUIRED",
        "task_type": "ROLE_PLAY",
        "template_family": "TEMPLATE_LOCATION_INFORMATION_GAP",
        "stimulus_fingerprint": r3.digest([evidence_level, support, transfer, retention, interaction_variation]),
        "validator_status": "PASS",
        "source_refs": ["SOURCE_ITEM"],
        "authority_refs": ["AUTHORITY_ITEM"],
    }
    for field, value in values.items():
        contract[field] = value
        contract["field_states"][field] = "POPULATED"
    if transfer == "NONE":
        contract["field_states"]["transfer_dimensions_changed"] = "NOT_APPLICABLE_WITH_JUSTIFICATION"
        contract["field_justifications"]["transfer_dimensions_changed"] = "No transfer dimensions change when transfer distance is NONE."
    return contract


def _deployment_registry(tmp_path: Path, ontology_path: Path, contracts) -> Path:
    ontology = json.loads(ontology_path.read_text())
    registry = r3.deployment_registry(ontology["ontology_sha256"], contracts)
    path = tmp_path / "deployments.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def test_complete_denominator_accounts_for_missing_profiles_without_cartesian_product(tmp_path: Path) -> None:
    ontology = _ontology(tmp_path)
    graph = _graph(tmp_path)
    profiles = _profile_registry(tmp_path, graph, ontology)
    deployments = _deployment_registry(tmp_path, ontology, [
        _deployment(evidence_level="E2_CONTROLLED_PRODUCTION", support="S1_KEYWORD_OR_VISUAL", transfer="NONE", retention="NOT_SCHEDULED"),
    ])
    report = r3.build(ontology_path=ontology, graph_path=graph, profiles_path=profiles, deployments_path=deployments)
    assert report["counts"]["required_mastery_node_count"] == 3
    assert report["counts"]["required_capability_node_count"] == 2
    assert report["counts"]["denominator_cell_count"] == 2
    assert report["counts"]["profile_missing_count"] == 1
    assert report["claim_boundaries"]["cartesian_product_generated"] is False
    assert {row["status"] for row in report["cells"]} == {"PROFILE_DEFINITION_REQUIRED", "SUPPORTED_PASS"}
    assert report["coverage_metrics"]["retention_complete_percent"] == 0.0
    assert report["coverage_metrics"]["false_100_percent_blocked"] is True
    assert report["ranked_gaps"][0]["status"] == "PROFILE_DEFINITION_REQUIRED"


def test_gap_progresses_to_retention_only_when_every_required_dimension_is_covered(tmp_path: Path) -> None:
    ontology = _ontology(tmp_path)
    graph = _graph(tmp_path)
    profiles = _profile_registry(tmp_path, graph, ontology)
    contracts = [
        _deployment(evidence_level="E2_CONTROLLED_PRODUCTION", support="S1_KEYWORD_OR_VISUAL", transfer="NONE", retention="NOT_SCHEDULED"),
        _deployment(evidence_level="E3_INDEPENDENT_PRODUCTION", support="S0_INDEPENDENT", transfer="NONE", retention="NOT_SCHEDULED"),
        _deployment(evidence_level="E4_CROSS_CONTEXT_TRANSFER", support="S0_INDEPENDENT", transfer="MEDIUM", retention="NOT_SCHEDULED", interaction_variation="REPAIR_REQUIRED"),
        _deployment(evidence_level="E5_DELAYED_RETENTION", support="S0_INDEPENDENT", transfer="MEDIUM", retention="DAY_1", interaction_variation="REPAIR_REQUIRED"),
        _deployment(evidence_level="E5_DELAYED_RETENTION", support="S0_INDEPENDENT", transfer="MEDIUM", retention="DAY_3", interaction_variation="REPAIR_REQUIRED"),
        _deployment(evidence_level="E5_DELAYED_RETENTION", support="S0_INDEPENDENT", transfer="MEDIUM", retention="DAY_7", interaction_variation="REPAIR_REQUIRED"),
        _deployment(evidence_level="E5_DELAYED_RETENTION", support="S0_INDEPENDENT", transfer="MEDIUM", retention="RETAINED", interaction_variation="REPAIR_REQUIRED"),
    ]
    deployments = _deployment_registry(tmp_path, ontology, contracts)
    report = r3.build(ontology_path=ontology, graph_path=graph, profiles_path=profiles, deployments_path=deployments)
    cell = next(row for row in report["cells"] if row["obligation_id"])
    assert cell["status"] == "RETENTION_PASS"
    assert all(not row["missing"] for row in cell["dimension_coverage"].values())
    assert report["counts"]["status_counts"]["RETENTION_PASS"] == 1
    assert all(row["cell_id"] != cell["cell_id"] for row in report["ranked_gaps"])


def test_invalid_system_evidence_is_blocked_and_not_counted(tmp_path: Path) -> None:
    ontology = _ontology(tmp_path)
    graph = _graph(tmp_path)
    profiles = _profile_registry(tmp_path, graph, ontology)
    contract = _deployment(evidence_level="E3_INDEPENDENT_PRODUCTION", support="S0_INDEPENDENT", transfer="NONE", retention="NOT_SCHEDULED")
    contract["evidence_validity"] = "INVALIDATED_SYSTEM_ERROR"
    contract["system_error_status"] = "CONFIRMED"
    deployments = _deployment_registry(tmp_path, ontology, [contract])
    report = r3.build(ontology_path=ontology, graph_path=graph, profiles_path=profiles, deployments_path=deployments)
    cell = next(row for row in report["cells"] if row["obligation_id"])
    assert cell["status"] == "BLOCKED_SYSTEM_ERROR"
    assert cell["next_actions"] == ["ROUTE_TO_R1_EVIDENCE_GOVERNANCE_AND_RETEST"]


def test_required_media_defer_remains_visible_without_completion_claim(tmp_path: Path) -> None:
    ontology = _ontology(tmp_path)
    graph = _graph(tmp_path)
    profiles = _profile_registry(tmp_path, graph, ontology)
    profile_value = json.loads(profiles.read_text())
    profile_value["profiles"][0]["obligations"][0]["required_media_policy"] = "REQUIRED"
    profile_value["profiles_sha256"] = r3.digest(profile_value["profiles"])
    profiles.write_text(json.dumps(profile_value), encoding="utf-8")
    contract = _deployment(evidence_level="E0_EXPOSURE", support="S1_KEYWORD_OR_VISUAL", transfer="NONE", retention="NOT_SCHEDULED", media_state="DEFERRED_MEDIA_PAYLOAD")
    contract["media_requirement"] = "REQUIRED"
    contract["field_states"]["media_payload_state"] = "DEFERRED_MEDIA_PAYLOAD"
    deployments = _deployment_registry(tmp_path, ontology, [contract])
    report = r3.build(ontology_path=ontology, graph_path=graph, profiles_path=profiles, deployments_path=deployments)
    cell = next(row for row in report["cells"] if row["obligation_id"])
    assert cell["status"] == "DEFERRED_MEDIA"
    assert report["claim_boundaries"]["audio_completion_required"] is False
    assert report["coverage_metrics"]["retention_complete_percent"] == 0.0


def test_source_bindings_fail_closed_and_validator_detects_tampering(tmp_path: Path) -> None:
    ontology = _ontology(tmp_path)
    graph = _graph(tmp_path)
    profiles = _profile_registry(tmp_path, graph, ontology)
    deployments = _deployment_registry(tmp_path, ontology, [])
    report = r3.build(ontology_path=ontology, graph_path=graph, profiles_path=profiles, deployments_path=deployments)
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = validator.validate(
        ontology_path=ontology,
        graph_path=graph,
        profiles_path=profiles,
        deployments_path=deployments,
        report_path=report_path,
    )
    assert result["error_count"] == 0, result["errors"]
    report["coverage_metrics"]["retention_complete_percent"] = 100.0
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = validator.validate(
        ontology_path=ontology,
        graph_path=graph,
        profiles_path=profiles,
        deployments_path=deployments,
        report_path=report_path,
    )
    assert result["error_count"] > 0
    profile_value = json.loads(profiles.read_text())
    profile_value["source_graph_sha256"] = "0" * 64
    profiles.write_text(json.dumps(profile_value), encoding="utf-8")
    with pytest.raises(r3.BreadthCoverageError, match="profiles_graph_binding_mismatch"):
        r3.build(ontology_path=ontology, graph_path=graph, profiles_path=profiles, deployments_path=deployments)
