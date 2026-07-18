from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.validators import validate_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as validator


def _complete_contract():
    contract = r2.empty_contract(
        deployment_id="EDGE_DEPLOYMENT_ASK_LOCATION_TRAVEL_SPEAKING_S1",
        capability_id="CAP_ASK_LOCATION",
        life_task_id="LIFE_TASK_FIND_BUS_STOP",
    )
    values = {
        "level": "A1",
        "grammar_targets": ["GRAMMAR_WHERE_BE_A1"],
        "vocabulary_targets": ["VOCAB_BUS_STOP_A1"],
        "chunk_targets": ["CHUNK_EXCUSE_ME_A1"],
        "pattern_targets": ["PATTERN_WHERE_IS_X_A1"],
        "pragmatic_targets": ["PRAGMATIC_POLITE_ATTENTION_A1"],
        "domain": "TRAVEL_TRANSPORT",
        "situation_family": "SITUATION_FINDING_PUBLIC_TRANSPORT",
        "micro_situation": "MICRO_FINDING_BUS_STOP",
        "speaker_role": "SELF",
        "listener_role": "TRANSPORT_STAFF",
        "relationship": "SERVICE_RELATION",
        "familiarity": "KNOWN_ROLE",
        "authority_difference": "NONE",
        "register": "SERVICE_POLITE",
        "locale_variant": "UK_ENGLISH",
        "communicative_intent": "ASK_INFORMATION",
        "desired_outcome": "INFORMATION_OBTAINED",
        "success_condition": {
            "condition_type": "REQUIRED_INFORMATION_POINTS_OBTAINED",
            "required_information_point_count": 1,
            "task_end_state": "BUS_STOP_LOCATION_CONFIRMED",
        },
        "information_given": [],
        "information_missing": [{"information_id": "INFO_BUS_STOP_LOCATION", "semantic_type": "PLACE", "required_for_success": True}],
        "information_requested": [{"information_id": "INFO_BUS_STOP_LOCATION", "semantic_type": "PLACE", "required_for_success": True}],
        "information_confirmed": [],
        "information_corrected": [],
        "information_gap_type": "LOCATION_GAP",
        "skill": "SPEAKING",
        "task_type": "ROLE_PLAY",
        "cognitive_operation": "LOCATE",
        "discourse_operation": "TWO_TURN_EXCHANGE",
        "task_step_count": 2,
        "step_dependency": "LINEAR_DEPENDENCY",
        "initiative_level": "GUIDED_INITIATION",
        "support_level": "S1_KEYWORD_OR_VISUAL",
        "interaction_channel": "FACE_TO_FACE",
        "real_world_artifact_type": "MAP",
        "input_complexity": "C1_SINGLE_UNIT",
        "output_complexity": "C1_SINGLE_UNIT",
        "turn_complexity": "T2_TWO_TURN",
        "unexpected_event": "PARTNER_MISUNDERSTANDS",
        "interaction_variation": "REPAIR_REQUIRED",
        "repair_requirement": "REPHRASE",
        "adaptation_step": "REPHRASE",
        "environment_condition": "PUBLIC_SPACE",
        "time_pressure": "LOW",
        "risk_level": "EVERYDAY_CONSEQUENCE",
        "accessibility_support": ["NONE"],
        "transfer_distance": "MEDIUM",
        "transfer_dimensions_changed": ["DOMAIN", "PARTICIPANT_ROLE"],
        "novelty_level": "NEW_CONTEXT_SAME_CAPABILITY",
        "template_family": "TEMPLATE_LOCATION_INFORMATION_GAP",
        "stimulus_fingerprint": "a" * 64,
        "context_seen_before": "UNSEEN",
        "evidence_level": "E3_INDEPENDENT_PRODUCTION",
        "accuracy_result": "NOT_EVALUATED",
        "meaning_result": "NOT_EVALUATED",
        "task_completion_result": "NOT_EVALUATED",
        "pragmatic_result": "NOT_EVALUATED",
        "independence_result": "NOT_EVALUATED",
        "initiative_result": "NOT_EVALUATED",
        "repair_result": "NOT_EVALUATED",
        "retention_stage": "NOT_SCHEDULED",
        "evidence_validity": "VALID",
        "system_error_status": "NONE",
        "media_requirement": "OPTIONAL",
        "media_payload_state": "DEFERRED_MEDIA_PAYLOAD",
        "transcript_state": "NOT_POPULATED",
        "recording_requirement": "REQUIRED",
        "recording_state": "DEFERRED_MEDIA_PAYLOAD",
        "consent_requirement": "REQUIRED_NOT_CAPTURED",
        "source_refs": ["A1_C1_CONTEXT_TRAVEL_TRANSPORT"],
        "authority_refs": ["EGP_A1_WHERE_QUESTIONS"],
        "validator_status": "NOT_EVALUATED",
        "created_at": "2026-07-19T00:00:00Z",
        "updated_at": "2026-07-19T00:00:00Z",
    }
    for field, value in values.items():
        contract[field] = value
        contract["field_states"][field] = "POPULATED"
    contract["field_states"]["media_payload_state"] = "DEFERRED_MEDIA_PAYLOAD"
    contract["field_states"]["recording_state"] = "DEFERRED_MEDIA_PAYLOAD"
    for field in ("information_given", "information_confirmed", "information_corrected"):
        contract["field_states"][field] = "NOT_APPLICABLE_WITH_JUSTIFICATION"
        contract["field_justifications"][field] = "This one-way location request does not require this information state."
    return contract


def test_complete_v1_ontology_and_schema_are_deterministic(tmp_path: Path) -> None:
    ontology_a = r2.build_ontology()
    ontology_b = r2.build_ontology()
    schema = r2.build_contract_schema()
    assert ontology_a == ontology_b
    assert ontology_a["ontology_sha256"] == r2.digest({key: value for key, value in ontology_a.items() if key != "ontology_sha256"})
    assert len(ontology_a["required_contract_fields"]) == 78
    assert len(ontology_a["enums"]) == 47
    assert len(ontology_a["domain_definitions"]) == 12
    assert ontology_a["scope"] == {
        "levels": ["A1", "A1_PLUS"],
        "architecture_complete_in_v1": True,
        "data_population_milestone_based": True,
        "a2_locked": True,
        "qwen_required": False,
        "audio_population_required_now": False,
    }
    Draft202012Validator.check_schema(schema)
    assert not validator.validate_ontology(ontology_a)
    ontology_path = tmp_path / "ontology.json"
    schema_path = tmp_path / "schema.json"
    ontology_path.write_text(json.dumps(ontology_a), encoding="utf-8")
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    report = validator.validate_files(ontology_path, schema_path)
    assert report["error_count"] == 0, report["errors"]


def test_complete_contract_covers_social_information_repair_transfer_media_and_evidence() -> None:
    contract = _complete_contract()
    errors = validator.validate_contract(contract)
    assert errors == []
    assert set(contract["field_states"]) == set(r2.REQUIRED_CONTRACT_FIELDS)
    assert contract["media_payload_state"] == "DEFERRED_MEDIA_PAYLOAD"
    assert contract["recording_state"] == "DEFERRED_MEDIA_PAYLOAD"
    assert contract["unexpected_event"] == "PARTNER_MISUNDERSTANDS"
    assert contract["repair_requirement"] == "REPHRASE"
    assert contract["transfer_distance"] == "MEDIUM"


def test_all_missing_dimensions_remain_explicit_and_queryable() -> None:
    contract = r2.empty_contract(
        deployment_id="EDGE_DEPLOYMENT_EMPTY_A1",
        capability_id="CAP_PENDING_DEFINITION",
        life_task_id="LIFE_TASK_PENDING_DEFINITION",
    )
    errors = validator.validate_contract(contract)
    assert errors == []
    assert len(contract["field_states"]) == 78
    assert set(contract["field_states"].values()) == {"POPULATED", "NOT_POPULATED"}
    assert contract["field_states"]["domain"] == "NOT_POPULATED"
    assert contract["field_states"]["evidence_level"] == "NOT_POPULATED"


def test_legacy_adapter_never_claims_breadth_deployment_or_mastery() -> None:
    contract = r2.adapt_legacy_record(
        {"node_id": "REF:READING:C1", "level": "A1", "skill": "READING"},
        source_type="M1_NODE",
        source_sha256="b" * 64,
    )
    errors = validator.validate_contract(contract)
    assert errors == []
    assert contract["level"] == "A1" and contract["skill"] == "READING"
    for field in (
        "domain", "micro_situation", "communicative_intent", "support_level",
        "transfer_distance", "evidence_level", "retention_stage",
    ):
        assert contract["field_states"][field] == "NOT_POPULATED"
        assert contract[field] is None


def test_a2_and_hidden_missing_fields_fail_closed() -> None:
    contract = r2.empty_contract(
        deployment_id="EDGE_DEPLOYMENT_A2_FORBIDDEN",
        capability_id="CAP_A2_FORBIDDEN",
        life_task_id="LIFE_TASK_A2_FORBIDDEN",
    )
    contract["level"] = "A2"
    contract["field_states"]["level"] = "POPULATED"
    errors = validator.validate_contract(contract)
    assert any(error.startswith("schema:level:") for error in errors)
    contract = r2.empty_contract(
        deployment_id="EDGE_DEPLOYMENT_MISSING_FIELD",
        capability_id="CAP_MISSING_FIELD",
        life_task_id="LIFE_TASK_MISSING_FIELD",
    )
    del contract["field_states"]["domain"]
    errors = validator.validate_contract(contract)
    assert any("field_states" in error and "domain" in error for error in errors)


def test_not_applicable_requires_justification_and_transfer_requires_changed_dimension() -> None:
    contract = r2.empty_contract(
        deployment_id="EDGE_DEPLOYMENT_NA_INVALID",
        capability_id="CAP_NA_INVALID",
        life_task_id="LIFE_TASK_NA_INVALID",
    )
    contract["field_states"]["information_confirmed"] = "NOT_APPLICABLE_WITH_JUSTIFICATION"
    errors = validator.validate_contract(contract)
    assert "not_applicable_justification_missing:information_confirmed" in errors
    contract["field_justifications"]["information_confirmed"] = "No confirmation is required."
    contract["transfer_distance"] = "FAR"
    contract["field_states"]["transfer_distance"] = "POPULATED"
    errors = validator.validate_contract(contract)
    assert "transfer_dimensions_required" in errors


def test_misunderstanding_requires_repair_and_deferred_media_is_not_file_completion() -> None:
    contract = r2.empty_contract(
        deployment_id="EDGE_DEPLOYMENT_REPAIR_INVALID",
        capability_id="CAP_REPAIR_INVALID",
        life_task_id="LIFE_TASK_REPAIR_INVALID",
    )
    contract["unexpected_event"] = "PARTNER_MISUNDERSTANDS"
    contract["field_states"]["unexpected_event"] = "POPULATED"
    contract["repair_requirement"] = "NONE"
    contract["field_states"]["repair_requirement"] = "POPULATED"
    assert "misunderstanding_requires_repair" in validator.validate_contract(contract)
    contract["repair_requirement"] = "REQUEST_REPETITION"
    contract["media_payload_state"] = "DEFERRED_MEDIA_PAYLOAD"
    contract["field_states"]["media_payload_state"] = "DEFERRED_MEDIA_PAYLOAD"
    assert "misunderstanding_requires_repair" not in validator.validate_contract(contract)
    assert r2.build_ontology()["claim_boundaries"]["audio_files_required"] is False
