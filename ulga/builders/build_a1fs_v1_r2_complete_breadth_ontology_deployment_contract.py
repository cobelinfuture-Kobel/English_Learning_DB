#!/usr/bin/env python3
"""Build the complete A1/A1+ breadth ontology and deployment contract for A1FS V1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-R2_CompleteBreadthOntologyAndDeploymentContract"
SCHEMA_VERSION = "a1fs.v1.r2.complete_breadth_ontology.v1"
CONTRACT_SCHEMA_VERSION = "a1fs.v1.r2.breadth_deployment_contract.v1"
STATUS = "PASS_A1FS_V1_R2_COMPLETE_BREADTH_ONTOLOGY_DEPLOYMENT_CONTRACT"
NEXT_SHORT_STEP = "A1FS-V1-R3_CompleteBreadthDenominatorCoverageAndGapPlanner"
IDENTIFIER_PATTERN = r"^[A-Z][A-Z0-9_]{1,127}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"

FIELD_GROUPS = {
    "identity": ["deployment_id", "capability_id", "life_task_id", "level", "contract_version"],
    "language_authority": ["grammar_targets", "vocabulary_targets", "chunk_targets", "pattern_targets", "pragmatic_targets"],
    "life_social_context": [
        "domain", "situation_family", "micro_situation", "speaker_role", "listener_role",
        "relationship", "familiarity", "authority_difference", "register", "locale_variant",
    ],
    "communication_information": [
        "communicative_intent", "desired_outcome", "success_condition", "information_given",
        "information_missing", "information_requested", "information_confirmed",
        "information_corrected", "information_gap_type",
    ],
    "task_cognition": [
        "skill", "task_type", "cognitive_operation", "discourse_operation", "task_step_count",
        "step_dependency", "initiative_level", "support_level", "interaction_channel",
        "real_world_artifact_type", "input_complexity", "output_complexity", "turn_complexity",
    ],
    "variation_repair_environment": [
        "unexpected_event", "interaction_variation", "repair_requirement", "adaptation_step",
        "environment_condition", "time_pressure", "risk_level", "accessibility_support",
    ],
    "transfer_novelty": [
        "transfer_distance", "transfer_dimensions_changed", "novelty_level", "template_family",
        "stimulus_fingerprint", "context_seen_before",
    ],
    "evidence_retention": [
        "evidence_level", "accuracy_result", "meaning_result", "task_completion_result",
        "pragmatic_result", "independence_result", "initiative_result", "repair_result",
        "retention_stage", "evidence_validity", "system_error_status",
    ],
    "media_recording": [
        "media_requirement", "media_payload_state", "transcript_state", "recording_requirement",
        "recording_state", "consent_requirement",
    ],
    "traceability": ["source_refs", "authority_refs", "validator_status", "created_at", "updated_at"],
}
REQUIRED_CONTRACT_FIELDS = [field for fields in FIELD_GROUPS.values() for field in fields]
MISSING_STATES = [
    "POPULATED", "NOT_POPULATED", "NOT_DEPLOYED", "NOT_EVALUATED",
    "INSUFFICIENT_EVIDENCE", "DEFERRED_MEDIA_PAYLOAD", "NOT_APPLICABLE_WITH_JUSTIFICATION",
]
ENUMS = {
    "levels": ["A1", "A1_PLUS"],
    "skills": ["LISTENING", "SPEAKING", "READING", "WRITING", "INTEGRATED"],
    "domains": [
        "PERSONAL_INFORMATION_SOCIAL", "DAILY_ROUTINE_TIME", "SCHOOL_CLASSROOM",
        "HOME_LIVING_ENVIRONMENT", "SHOPPING_TRANSACTIONS", "FOOD_DINING",
        "INTERESTS_LEISURE_ABILITY", "TRAVEL_TRANSPORT", "WEATHER", "HEALTH_MEDICAL",
        "PUBLIC_PLACES_COMMUNITY", "DIGITAL_COMMUNICATION",
    ],
    "participant_roles": [
        "SELF", "FAMILY_MEMBER", "FRIEND", "CLASSMATE", "TEACHER", "SCHOOL_STAFF",
        "SHOP_ASSISTANT", "FOOD_SERVICE_STAFF", "TRANSPORT_STAFF", "PUBLIC_SERVICE_STAFF",
        "HEALTH_PROFESSIONAL", "STRANGER", "PEER_GROUP", "DIGITAL_CONTACT",
    ],
    "relationships": [
        "SELF", "FAMILY", "FRIEND", "PEER", "EDUCATIONAL_AUTHORITY", "SERVICE_RELATION",
        "PROFESSIONAL_CARE", "PUBLIC_AUTHORITY", "STRANGER", "GROUP",
    ],
    "familiarity": ["SELF", "HIGHLY_FAMILIAR", "FAMILIAR", "KNOWN_ROLE", "UNFAMILIAR"],
    "authority_difference": ["NONE", "SPEAKER_HIGHER", "LISTENER_HIGHER", "INSTITUTIONAL"],
    "registers": ["CHILD_FAMILIAR", "INFORMAL", "NEUTRAL_POLITE", "SERVICE_POLITE", "SCHOOL_FORMAL"],
    "locale_variants": ["INTERNATIONAL_ENGLISH", "UK_ENGLISH", "US_ENGLISH", "TAIWAN_EFL_CONTEXT"],
    "communicative_intents": [
        "GREET", "TAKE_LEAVE", "INTRODUCE_SELF", "INTRODUCE_OTHER", "IDENTIFY", "DESCRIBE",
        "ASK_INFORMATION", "GIVE_INFORMATION", "REQUEST_ACTION", "REQUEST_PERMISSION", "OFFER",
        "ACCEPT", "DECLINE", "EXPRESS_LIKE", "EXPRESS_DISLIKE", "EXPRESS_ABILITY",
        "EXPRESS_INABILITY", "EXPRESS_NEED", "EXPRESS_WANT", "EXPRESS_FEELING", "APOLOGIZE",
        "THANK", "INVITE", "SUGGEST", "PLAN", "CONFIRM", "CORRECT", "CLARIFY",
        "REQUEST_REPETITION", "REPORT_PROBLEM", "CHOOSE_ALTERNATIVE", "COMPARE",
        "SEQUENCE_EVENTS", "EXPLAIN_SIMPLE_REASON", "NARRATE_PAST_EVENT", "RESPOND_TO_INSTRUCTION",
    ],
    "desired_outcomes": [
        "SOCIAL_CONTACT_ESTABLISHED", "IDENTITY_SHARED", "DESCRIPTION_UNDERSTOOD",
        "INFORMATION_OBTAINED", "INFORMATION_DELIVERED", "ACTION_COMPLETED",
        "PERMISSION_RESOLVED", "CHOICE_RESOLVED", "TRANSACTION_COMPLETED", "PLAN_AGREED",
        "PROBLEM_REPORTED", "MISUNDERSTANDING_REPAIRED", "ALTERNATIVE_SELECTED",
        "SEQUENCE_UNDERSTOOD", "REASON_UNDERSTOOD",
    ],
    "success_condition_types": [
        "MESSAGE_UNDERSTOOD", "REQUIRED_INFORMATION_POINTS_OBTAINED",
        "LISTENER_ACTION_MATCHES_REQUEST", "LEARNER_ACTION_MATCHES_INSTRUCTION",
        "TRANSACTION_END_STATE_REACHED", "MUTUAL_CONFIRMATION_REACHED",
        "COMMUNICATION_REPAIR_COMPLETED", "MULTI_STEP_TASK_COMPLETED",
    ],
    "information_gap_types": [
        "NONE_SHARED_INFORMATION", "ONE_WAY_MISSING_INFORMATION", "TWO_WAY_INFORMATION_GAP",
        "CHOICE_GAP", "CONFIRMATION_GAP", "CORRECTION_GAP", "SEQUENCE_GAP", "LOCATION_GAP",
        "TIME_GAP", "QUANTITY_GAP", "PREFERENCE_GAP",
    ],
    "task_types": [
        "PICTURE_TEXT_MATCHING", "SELECT_ONE", "SELECT_MULTIPLE", "TRUE_FALSE", "CLOZE",
        "GAP_FILL", "SENTENCE_ORDERING", "INFORMATION_ORDERING", "SHORT_ANSWER",
        "GUIDED_RESPONSE", "INDEPENDENT_RESPONSE", "ROLE_PLAY", "INFORMATION_GAP",
        "DIALOGUE_COMPLETION", "FORM_COMPLETION", "LABELING", "READ_THEN_SPEAK",
        "READ_THEN_WRITE", "LISTEN_THEN_SPEAK", "LISTEN_THEN_WRITE", "SPEAK_THEN_WRITE",
        "MULTI_STEP_LIFE_TASK",
    ],
    "cognitive_operations": [
        "RECOGNIZE", "IDENTIFY", "LOCATE", "MATCH", "SELECT", "CLASSIFY", "ORDER", "SEQUENCE",
        "COMPARE", "RECALL", "COMPLETE", "TRANSFORM", "INFER_SIMPLE", "EXPLAIN_SIMPLE_REASON",
        "PLAN", "MONITOR", "REPAIR",
    ],
    "discourse_operations": [
        "WORD_OR_PHRASE", "SINGLE_SENTENCE", "QUESTION_ANSWER_PAIR", "TWO_TURN_EXCHANGE",
        "MULTI_TURN_EXCHANGE", "LIST", "DESCRIPTION", "SEQUENCE", "SIMPLE_NARRATIVE",
        "SIMPLE_REASON", "INSTRUCTION_RESPONSE", "TRANSACTION_SEQUENCE",
    ],
    "step_dependencies": ["INDEPENDENT_STEPS", "LINEAR_DEPENDENCY", "BRANCHING_CHOICE", "REPAIR_LOOP"],
    "initiative_levels": [
        "RESPOND_ONLY", "CHOOSE_FROM_OPTIONS", "GUIDED_INITIATION", "INDEPENDENT_INITIATION",
        "SUSTAIN_INTERACTION", "REPAIR_AND_CLOSE_TASK",
    ],
    "support_levels": ["S3_FULL_MODEL", "S2_FRAME", "S1_KEYWORD_OR_VISUAL", "S0_INDEPENDENT"],
    "interaction_channels": [
        "FACE_TO_FACE", "AUDIO_ONLY", "VIDEO", "TEXT_CHAT", "FORM", "SIGN_NOTICE",
        "MAP_DIAGRAM", "MENU_PRICE_LIST", "TIMETABLE_SCHEDULE", "PICTURE_SCENE",
    ],
    "real_world_artifact_types": [
        "NONE", "PICTURE", "LABEL", "SIGN", "NOTICE", "MENU", "PRICE_TAG", "MAP",
        "TIMETABLE", "TICKET", "FORM", "MESSAGE", "EMAIL", "CHAT", "LIST", "CALENDAR",
    ],
    "complexity_levels": ["C0_NONE", "C1_SINGLE_UNIT", "C2_TWO_UNITS", "C3_MULTI_UNIT_CONTROLLED"],
    "turn_complexity_levels": ["T0_NO_INTERACTION", "T1_ONE_TURN", "T2_TWO_TURN", "T3_MULTI_TURN_CONTROLLED"],
    "unexpected_events": [
        "NONE", "ITEM_UNAVAILABLE", "INFORMATION_INCOMPLETE", "INFORMATION_INCORRECT",
        "TIME_CHANGED", "PLACE_CHANGED", "REQUEST_REFUSED", "CHOICE_UNAVAILABLE",
        "PARTNER_MISUNDERSTANDS", "LEARNER_MISUNDERSTANDS", "NO_RESPONSE",
        "DEVICE_OR_UI_FAILURE", "MEDIA_UNAVAILABLE",
    ],
    "interaction_variations": [
        "EXPECTED_SCRIPT", "LEXICAL_VARIATION", "ORDER_VARIATION", "ROLE_VARIATION",
        "RESPONSE_VARIATION", "UNEXPECTED_EVENT", "INTERRUPTION", "REPAIR_REQUIRED",
    ],
    "repair_requirements": [
        "NONE", "REQUEST_REPETITION", "ASK_FOR_CLARIFICATION", "CONFIRM_UNDERSTANDING",
        "CORRECT_INFORMATION", "REPHRASE", "SLOW_DOWN_REQUEST", "CHOOSE_ALTERNATIVE",
        "REPORT_TECHNICAL_PROBLEM", "RESTART_TASK_STEP",
    ],
    "adaptation_steps": [
        "NONE", "REPEAT", "CLARIFY", "CONFIRM", "CORRECT", "REPHRASE", "CHANGE_CHOICE",
        "CHANGE_PLAN", "RETURN_TO_PREVIOUS_STEP", "ESCALATE_TO_HUMAN",
    ],
    "environment_conditions": [
        "QUIET_CONTROLLED", "VISUAL_DISTRACTION", "BACKGROUND_NOISE", "MULTIPLE_SPEAKERS",
        "TIME_LIMITED", "REMOTE_CONNECTION", "PUBLIC_SPACE", "UNFAMILIAR_SETTING",
    ],
    "time_pressure_levels": ["NONE", "LOW", "MODERATE"],
    "risk_levels": ["LOW_STAKES_PRACTICE", "EVERYDAY_CONSEQUENCE", "SAFETY_RELEVANT"],
    "accessibility_supports": [
        "NONE", "LARGE_TEXT", "HIGH_CONTRAST", "KEYBOARD_ONLY", "SCREEN_READER_LABELS",
        "CAPTIONS", "TRANSCRIPT", "REPLAY_CONTROL", "SLOWED_AUDIO", "EXTRA_RESPONSE_TIME",
    ],
    "transfer_distances": ["NONE", "NEAR", "MEDIUM", "FAR"],
    "transfer_dimensions": [
        "DOMAIN", "SITUATION", "PARTICIPANT_ROLE", "COMMUNICATIVE_INTENT", "SKILL",
        "TASK_TYPE", "SUPPORT_LEVEL", "INITIATIVE_LEVEL", "INTERACTION_CHANNEL",
        "UNEXPECTED_EVENT", "REGISTER", "REAL_WORLD_ARTIFACT",
    ],
    "novelty_levels": [
        "SEEN_ITEM", "SEEN_TEMPLATE_NEW_SLOTS", "NEW_SURFACE_SAME_STRUCTURE",
        "NEW_CONTEXT_SAME_CAPABILITY", "UNSEEN_CONTEXT", "AUTHENTIC_OR_SIMULATED_LIFE_TASK",
    ],
    "context_seen_states": ["SEEN", "PARTIALLY_SEEN", "UNSEEN"],
    "evidence_levels": [
        "E0_EXPOSURE", "E1_RECOGNITION", "E2_CONTROLLED_PRODUCTION", "E3_INDEPENDENT_PRODUCTION",
        "E4_CROSS_CONTEXT_TRANSFER", "E5_DELAYED_RETENTION", "E6_AUTHENTIC_TASK_PERFORMANCE",
    ],
    "result_states": ["NOT_EVALUATED", "PASS", "PARTIAL", "FAIL", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"],
    "retention_stages": ["NOT_SCHEDULED", "DAY_1", "DAY_3", "DAY_7", "RETAINED", "LAPSED"],
    "evidence_validity_states": [
        "VALID", "PENDING_VALIDITY_REVIEW", "INVALIDATED_SYSTEM_ERROR",
        "INVALIDATED_CONTENT_ERROR", "INVALIDATED_DUPLICATE_SUBMISSION",
    ],
    "system_error_states": ["NONE", "SUSPECTED", "CONFIRMED", "RESOLVED_RETEST_REQUIRED"],
    "media_requirements": ["NONE", "OPTIONAL", "REQUIRED"],
    "media_payload_states": ["NOT_REQUIRED", "NOT_POPULATED", "DEFERRED_MEDIA_PAYLOAD", "AVAILABLE", "VALIDATED"],
    "transcript_states": ["NOT_REQUIRED", "NOT_POPULATED", "AVAILABLE", "VALIDATED"],
    "recording_requirements": ["NONE", "OPTIONAL", "REQUIRED"],
    "recording_states": ["NOT_REQUIRED", "NOT_POPULATED", "DEFERRED_MEDIA_PAYLOAD", "AVAILABLE", "VALIDATED"],
    "consent_requirements": ["NOT_REQUIRED", "REQUIRED_NOT_CAPTURED", "CAPTURED"],
    "validator_states": ["NOT_EVALUATED", "PASS", "FAIL"],
}
DOMAIN_DEFINITIONS = [
    ("PERSONAL_INFORMATION_SOCIAL", "Personal information, greetings, introductions, family and friends"),
    ("DAILY_ROUTINE_TIME", "Daily routine, meals, dates, frequency and time arrangements"),
    ("SCHOOL_CLASSROOM", "Classroom instructions, school people, objects and school-day tasks"),
    ("HOME_LIVING_ENVIRONMENT", "Rooms, household objects, locations and simple home directions"),
    ("SHOPPING_TRANSACTIONS", "Prices, quantities, choices, tickets and basic purchases"),
    ("FOOD_DINING", "Food preferences, ordering, availability and simple dining exchanges"),
    ("INTERESTS_LEISURE_ABILITY", "Hobbies, sports, invitations and ability or inability"),
    ("TRAVEL_TRANSPORT", "Transport, routes, simple travel plans and tickets"),
    ("WEATHER", "Current weather, simple forecasts and weather-related plans"),
    ("HEALTH_MEDICAL", "Body parts, common symptoms, needs and basic help-seeking"),
    ("PUBLIC_PLACES_COMMUNITY", "Facilities, locations, signs, directions and community services"),
    ("DIGITAL_COMMUNICATION", "Simple messages, chat, email-like notes and online task instructions"),
]
PROGRESSION_CONTRACTS = {
    "support_progression": ["S3_FULL_MODEL", "S2_FRAME", "S1_KEYWORD_OR_VISUAL", "S0_INDEPENDENT"],
    "initiative_progression": [
        "RESPOND_ONLY", "CHOOSE_FROM_OPTIONS", "GUIDED_INITIATION", "INDEPENDENT_INITIATION",
        "SUSTAIN_INTERACTION", "REPAIR_AND_CLOSE_TASK",
    ],
    "evidence_progression": [
        "E0_EXPOSURE", "E1_RECOGNITION", "E2_CONTROLLED_PRODUCTION", "E3_INDEPENDENT_PRODUCTION",
        "E4_CROSS_CONTEXT_TRANSFER", "E5_DELAYED_RETENTION", "E6_AUTHENTIC_TASK_PERFORMANCE",
    ],
    "retention_progression": ["NOT_SCHEDULED", "DAY_1", "DAY_3", "DAY_7", "RETAINED"],
    "transfer_progression": ["NONE", "NEAR", "MEDIUM", "FAR"],
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_ontology() -> dict[str, Any]:
    core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "scope": {
            "levels": ["A1", "A1_PLUS"],
            "architecture_complete_in_v1": True,
            "data_population_milestone_based": True,
            "a2_locked": True,
            "qwen_required": False,
            "audio_population_required_now": False,
        },
        "field_groups": deepcopy(FIELD_GROUPS),
        "required_contract_fields": list(REQUIRED_CONTRACT_FIELDS),
        "field_state_policy": {
            "states": list(MISSING_STATES),
            "every_required_field_has_state": True,
            "empty_value_without_state_forbidden": True,
            "not_applicable_requires_justification": True,
            "missing_fields_remain_in_denominator": True,
        },
        "enums": deepcopy(ENUMS),
        "domain_definitions": [
            {"domain_id": domain_id, "description": description, "levels": ["A1", "A1_PLUS"]}
            for domain_id, description in DOMAIN_DEFINITIONS
        ],
        "progression_contracts": deepcopy(PROGRESSION_CONTRACTS),
        "identifier_contract": {
            "pattern": IDENTIFIER_PATTERN,
            "deployment_id_prefix": "EDGE_DEPLOYMENT_",
            "capability_id_prefix": "CAP_",
            "life_task_id_prefix": "LIFE_TASK_",
            "template_family_prefix": "TEMPLATE_",
        },
        "compatibility_contract": {
            "legacy_source_types": ["M1_NODE", "M1_COVERAGE", "M2_ASSET_RECORD", "M4_LEARNING_OPPORTUNITY"],
            "unknown_legacy_dimensions_state": "NOT_POPULATED",
            "legacy_mapping_never_claims_deployment": True,
            "legacy_mapping_never_claims_evaluation": True,
            "legacy_mapping_never_claims_transfer_or_retention": True,
        },
        "claim_boundaries": {
            "canonical_graph_modified": False,
            "a2_content_included": False,
            "a2_unlocked": False,
            "qwen_dependency_added": False,
            "audio_files_required": False,
            "mastery_claimed": False,
            "coverage_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    return {**core, "ontology_sha256": digest(core)}


def _enum_or_missing(enum_name: str) -> dict[str, Any]:
    return {"anyOf": [{"enum": ENUMS[enum_name]}, {"type": "null"}]}


def build_contract_schema() -> dict[str, Any]:
    identifier = {"type": "string", "pattern": IDENTIFIER_PATTERN}
    string_array = {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True}
    information_array = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["information_id", "semantic_type", "required_for_success"],
            "properties": {
                "information_id": identifier,
                "semantic_type": {"enum": [
                    "PERSON", "OBJECT", "PLACE", "TIME", "DATE", "QUANTITY", "PRICE", "CHOICE",
                    "ACTION", "REASON", "FEELING", "ATTRIBUTE", "SEQUENCE_STEP",
                ]},
                "required_for_success": {"type": "boolean"},
            },
        },
    }
    properties: dict[str, Any] = {
        "deployment_id": identifier, "capability_id": identifier, "life_task_id": identifier,
        "level": _enum_or_missing("levels"),
        "contract_version": {"type": ["string", "null"], "minLength": 1},
        "grammar_targets": string_array, "vocabulary_targets": string_array,
        "chunk_targets": string_array, "pattern_targets": string_array, "pragmatic_targets": string_array,
        "domain": _enum_or_missing("domains"),
        "situation_family": {"type": ["string", "null"], "pattern": IDENTIFIER_PATTERN},
        "micro_situation": {"type": ["string", "null"], "pattern": IDENTIFIER_PATTERN},
        "speaker_role": _enum_or_missing("participant_roles"), "listener_role": _enum_or_missing("participant_roles"),
        "relationship": _enum_or_missing("relationships"), "familiarity": _enum_or_missing("familiarity"),
        "authority_difference": _enum_or_missing("authority_difference"), "register": _enum_or_missing("registers"),
        "locale_variant": _enum_or_missing("locale_variants"),
        "communicative_intent": _enum_or_missing("communicative_intents"),
        "desired_outcome": _enum_or_missing("desired_outcomes"),
        "success_condition": {"anyOf": [{
            "type": "object", "additionalProperties": False,
            "required": ["condition_type", "required_information_point_count", "task_end_state"],
            "properties": {
                "condition_type": {"enum": ENUMS["success_condition_types"]},
                "required_information_point_count": {"type": "integer", "minimum": 0, "maximum": 8},
                "task_end_state": {"type": "string", "pattern": IDENTIFIER_PATTERN},
            },
        }, {"type": "null"}]},
        "information_given": information_array, "information_missing": information_array,
        "information_requested": information_array, "information_confirmed": information_array,
        "information_corrected": information_array, "information_gap_type": _enum_or_missing("information_gap_types"),
        "skill": _enum_or_missing("skills"), "task_type": _enum_or_missing("task_types"),
        "cognitive_operation": _enum_or_missing("cognitive_operations"),
        "discourse_operation": _enum_or_missing("discourse_operations"),
        "task_step_count": {"type": ["integer", "null"], "minimum": 1, "maximum": 8},
        "step_dependency": _enum_or_missing("step_dependencies"),
        "initiative_level": _enum_or_missing("initiative_levels"), "support_level": _enum_or_missing("support_levels"),
        "interaction_channel": _enum_or_missing("interaction_channels"),
        "real_world_artifact_type": _enum_or_missing("real_world_artifact_types"),
        "input_complexity": _enum_or_missing("complexity_levels"), "output_complexity": _enum_or_missing("complexity_levels"),
        "turn_complexity": _enum_or_missing("turn_complexity_levels"),
        "unexpected_event": _enum_or_missing("unexpected_events"),
        "interaction_variation": _enum_or_missing("interaction_variations"),
        "repair_requirement": _enum_or_missing("repair_requirements"), "adaptation_step": _enum_or_missing("adaptation_steps"),
        "environment_condition": _enum_or_missing("environment_conditions"), "time_pressure": _enum_or_missing("time_pressure_levels"),
        "risk_level": _enum_or_missing("risk_levels"),
        "accessibility_support": {"type": "array", "items": {"enum": ENUMS["accessibility_supports"]}, "uniqueItems": True},
        "transfer_distance": _enum_or_missing("transfer_distances"),
        "transfer_dimensions_changed": {"type": "array", "items": {"enum": ENUMS["transfer_dimensions"]}, "uniqueItems": True},
        "novelty_level": _enum_or_missing("novelty_levels"),
        "template_family": {"type": ["string", "null"], "pattern": IDENTIFIER_PATTERN},
        "stimulus_fingerprint": {"type": ["string", "null"], "pattern": SHA256_PATTERN},
        "context_seen_before": _enum_or_missing("context_seen_states"),
        "evidence_level": _enum_or_missing("evidence_levels"),
        "accuracy_result": _enum_or_missing("result_states"), "meaning_result": _enum_or_missing("result_states"),
        "task_completion_result": _enum_or_missing("result_states"), "pragmatic_result": _enum_or_missing("result_states"),
        "independence_result": _enum_or_missing("result_states"), "initiative_result": _enum_or_missing("result_states"),
        "repair_result": _enum_or_missing("result_states"), "retention_stage": _enum_or_missing("retention_stages"),
        "evidence_validity": _enum_or_missing("evidence_validity_states"),
        "system_error_status": _enum_or_missing("system_error_states"),
        "media_requirement": _enum_or_missing("media_requirements"),
        "media_payload_state": _enum_or_missing("media_payload_states"),
        "transcript_state": _enum_or_missing("transcript_states"),
        "recording_requirement": _enum_or_missing("recording_requirements"),
        "recording_state": _enum_or_missing("recording_states"),
        "consent_requirement": _enum_or_missing("consent_requirements"),
        "source_refs": string_array, "authority_refs": string_array,
        "validator_status": _enum_or_missing("validator_states"),
        "created_at": {"type": ["string", "null"], "format": "date-time"},
        "updated_at": {"type": ["string", "null"], "format": "date-time"},
        "field_states": {
            "type": "object", "additionalProperties": False, "required": REQUIRED_CONTRACT_FIELDS,
            "properties": {field: {"enum": MISSING_STATES} for field in REQUIRED_CONTRACT_FIELDS},
        },
        "field_justifications": {"type": "object", "additionalProperties": {"type": "string", "minLength": 1}},
        "legacy_source": {"anyOf": [{
            "type": "object", "additionalProperties": False,
            "required": ["source_type", "source_id", "source_sha256"],
            "properties": {
                "source_type": {"enum": ["M1_NODE", "M1_COVERAGE", "M2_ASSET_RECORD", "M4_LEARNING_OPPORTUNITY"]},
                "source_id": {"type": "string", "minLength": 1},
                "source_sha256": {"type": "string", "pattern": SHA256_PATTERN},
            },
        }, {"type": "null"}]},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/a1fs_v1_r2_breadth_deployment_contract.schema.json",
        "title": "A1FS V1 Complete Breadth Deployment Contract",
        "type": "object", "additionalProperties": False,
        "required": REQUIRED_CONTRACT_FIELDS + ["field_states", "field_justifications", "legacy_source"],
        "properties": properties,
    }


def empty_contract(*, deployment_id: str, capability_id: str, life_task_id: str) -> dict[str, Any]:
    contract: dict[str, Any] = {field: None for field in REQUIRED_CONTRACT_FIELDS}
    for field in (
        "grammar_targets", "vocabulary_targets", "chunk_targets", "pattern_targets", "pragmatic_targets",
        "information_given", "information_missing", "information_requested", "information_confirmed",
        "information_corrected", "accessibility_support", "transfer_dimensions_changed", "source_refs", "authority_refs",
    ):
        contract[field] = []
    contract.update({
        "deployment_id": deployment_id, "capability_id": capability_id, "life_task_id": life_task_id,
        "contract_version": CONTRACT_SCHEMA_VERSION,
        "field_states": {field: "NOT_POPULATED" for field in REQUIRED_CONTRACT_FIELDS},
        "field_justifications": {}, "legacy_source": None,
    })
    for field in ("deployment_id", "capability_id", "life_task_id", "contract_version"):
        contract["field_states"][field] = "POPULATED"
    return contract


def adapt_legacy_record(record: Mapping[str, Any], *, source_type: str, source_sha256: str) -> dict[str, Any]:
    if source_type not in build_ontology()["compatibility_contract"]["legacy_source_types"]:
        raise ValueError("legacy_source_type_invalid")
    source_id = str(record.get("node_id") or record.get("asset_key") or record.get("learning_opportunity_id") or "").strip()
    if not source_id:
        raise ValueError("legacy_source_id_missing")
    token = digest([source_type, source_id])[:20].upper()
    contract = empty_contract(
        deployment_id=f"EDGE_DEPLOYMENT_{token}",
        capability_id=f"CAP_LEGACY_{token}",
        life_task_id=f"LIFE_TASK_LEGACY_{token}",
    )
    level = str(record.get("level") or "").upper().replace("+", "_PLUS")
    if level in ENUMS["levels"]:
        contract["level"] = level
        contract["field_states"]["level"] = "POPULATED"
    skill = str(record.get("skill") or "").upper()
    if skill in ENUMS["skills"]:
        contract["skill"] = skill
        contract["field_states"]["skill"] = "POPULATED"
    contract["source_refs"] = [source_id]
    contract["field_states"]["source_refs"] = "POPULATED"
    contract["legacy_source"] = {"source_type": source_type, "source_id": source_id, "source_sha256": source_sha256}
    return contract


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology-output", type=Path, required=True)
    parser.add_argument("--schema-output", type=Path, required=True)
    args = parser.parse_args()
    ontology, schema = build_ontology(), build_contract_schema()
    _write(args.ontology_output, ontology)
    _write(args.schema_output, schema)
    print(json.dumps({
        "validation_status": STATUS,
        "ontology_output": str(args.ontology_output),
        "schema_output": str(args.schema_output),
        "required_contract_field_count": len(REQUIRED_CONTRACT_FIELDS),
        "enum_group_count": len(ENUMS),
        "next_short_step": NEXT_SHORT_STEP,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
