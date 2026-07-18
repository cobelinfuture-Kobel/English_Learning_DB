from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1
from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r6_gpt_diagnostic_package_controlled_recommendation_gate as r6
from ulga.validators import validate_a1fs_v1_r6_gpt_diagnostic_package_controlled_recommendation_gate as validator

CELL_ID = "BREADTH_CELL_ASK_LOCATION_TRAVEL"


def _write(path: Path, value) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _item(item_id: str):
    learner = {
        "prompt": "You are in a new town. Ask where the bus stop is.",
        "response_mode": "short_text",
        "context": {"speaker_role": "SELF", "listener_role": "TRANSPORT_STAFF"},
    }
    scoring = {
        "scoring_mode": "FEATURE_RUBRIC",
        "response_type": "string",
        "rubric": {"grammar": "where question", "meaning": "requests location", "politeness": "neutral polite"},
        "human_review_fallback": True,
    }
    candidate_sha = r6.digest([item_id, "candidate"])
    return {
        "item_id": item_id,
        "breadth_cell_id": CELL_ID,
        "capability_id": "CAP_ASK_LOCATION",
        "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
        "domain": "TRAVEL_TRANSPORT",
        "level": "A1",
        "skill": "SPEAKING",
        "purpose": "CORE_PRACTICE",
        "task_type": "GUIDED_RESPONSE",
        "support_level": "S1_KEYWORD_OR_VISUAL",
        "initiative_level": "GUIDED_INITIATION",
        "interaction_variation": "EXPECTED_SCRIPT",
        "transfer_distance": "NONE",
        "template_family": "TEMPLATE_LOCATION_GUIDED_RESPONSE",
        "stimulus_fingerprint": r6.digest(learner),
        "media_payload_state": "AVAILABLE",
        "source_refs": ["SOURCE_ASK_LOCATION_A1"],
        "authority_refs": ["AUTHORITY_ASK_LOCATION_A1"],
        "provenance": "EXISTING_AUTHORITY_REVIEWED",
        "learner_contract": learner,
        "private_scoring_contract": scoring,
        "validator_status": "PASS",
        "candidate_sha256": candidate_sha,
        "authority_review": {
            "status": "APPROVED", "reviewer_id": "authority-reviewer",
            "reviewed_at": "2026-07-19T08:00:00+08:00", "criteria": {},
            "candidate_sha256": candidate_sha,
        },
        "admission": {
            "status": "APPROVED", "learner_fingerprint": r6.digest(learner),
            "candidate_sha256": candidate_sha,
        },
    }


def _coverage():
    cell = {
        "cell_id": CELL_ID,
        "capability_node_id": "REF:SPEAKING:ASK_LOCATION",
        "capability_id": "CAP_ASK_LOCATION",
        "obligation_id": "BREADTH_OBLIGATION_ASK_LOCATION_TRAVEL",
        "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
        "domain": "TRAVEL_TRANSPORT",
        "status": "EVIDENCE_INSUFFICIENT",
        "dimension_coverage": {
            "skills": {"required": ["SPEAKING"], "observed": ["SPEAKING"], "missing": []},
            "support_levels": {"required": ["S1_KEYWORD_OR_VISUAL", "S0_INDEPENDENT"], "observed": ["S1_KEYWORD_OR_VISUAL"], "missing": ["S0_INDEPENDENT"]},
            "initiative_levels": {"required": ["GUIDED_INITIATION", "INDEPENDENT_INITIATION"], "observed": ["GUIDED_INITIATION"], "missing": ["INDEPENDENT_INITIATION"]},
            "variation_types": {"required": ["EXPECTED_SCRIPT", "REPAIR_REQUIRED"], "observed": ["EXPECTED_SCRIPT"], "missing": ["REPAIR_REQUIRED"]},
            "transfer_distances": {"required": ["MEDIUM"], "observed": ["NONE"], "missing": ["MEDIUM"]},
            "evidence_levels": {"required": ["E3_INDEPENDENT_PRODUCTION", "E4_CROSS_CONTEXT_TRANSFER"], "observed": ["E2_CONTROLLED_PRODUCTION"], "missing": ["E3_INDEPENDENT_PRODUCTION", "E4_CROSS_CONTEXT_TRANSFER"]},
            "retention_stages": {"required": ["DAY_1", "DAY_3", "DAY_7", "RETAINED"], "observed": ["NOT_SCHEDULED"], "missing": ["DAY_1", "DAY_3", "DAY_7", "RETAINED"]},
        },
        "matching_deployment_ids": [],
        "source_refs": ["CONTEXT_TRAVEL_TRANSPORT"],
        "next_actions": ["COLLECT_MISSING_DIMENSION_EVIDENCE"],
    }
    core = {
        "task_id": r3.TASK_ID,
        "schema_version": r3.SCHEMA_VERSION,
        "validation_status": r3.STATUS,
        "source_bindings": {
            "ontology_sha256": "a" * 64, "graph_sha256": "b" * 64,
            "profiles_sha256": "c" * 64, "deployments_sha256": "d" * 64,
            "m10_structural_coverage": None,
        },
        "counts": {
            "required_mastery_node_count": 2, "required_capability_node_count": 1,
            "profile_defined_count": 1, "profile_missing_count": 0,
            "denominator_cell_count": 1, "deployment_contract_count": 1, "gap_count": 1,
            "status_counts": {status: int(status == "EVIDENCE_INSUFFICIENT") for status in r3.CELL_STATUSES},
        },
        "coverage_metrics": {
            "structural_ready_count": 1, "structural_ready_percent": 100.0,
            "retention_complete_count": 0, "retention_complete_percent": 0.0,
            "false_100_percent_blocked": True,
            "completion_denominator_source": "EXPLICIT_BREADTH_REQUIREMENT_CELLS_PLUS_PROFILE_PLACEHOLDERS",
        },
        "profile_missing_capability_node_ids": [],
        "cells": [cell],
        "ranked_gaps": [{
            "rank": 1, "cell_id": CELL_ID,
            "capability_node_id": "REF:SPEAKING:ASK_LOCATION",
            "capability_id": "CAP_ASK_LOCATION",
            "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
            "domain": "TRAVEL_TRANSPORT", "status": "EVIDENCE_INSUFFICIENT",
            "next_actions": ["COLLECT_MISSING_DIMENSION_EVIDENCE"],
        }],
        "claim_boundaries": {
            "m1_graph_modified": False, "m10_structural_coverage_replaced": False,
            "cartesian_product_generated": False, "a2_unlocked": False,
            "mastery_claimed": False, "retention_claimed_from_structure": False,
            "audio_completion_required": False,
        },
        "next_short_step": r3.NEXT_SHORT_STEP,
    }
    return {**core, "report_sha256": r6.digest(core)}


def _sources(tmp_path: Path):
    item = _item("ITEM_ASK_LOCATION_1")
    bindings = {
        "ontology_sha256": "a" * 64, "coverage_sha256": "b" * 64,
        "candidate_registry_sha256": "c" * 64, "capacity_policy_registry_sha256": "d" * 64,
    }
    bank_core = {
        "task_id": r4.TASK_ID, "schema_version": r4.BANK_SCHEMA_VERSION,
        "validation_status": r4.STATUS, "private_local_only": True,
        "source_bindings": bindings,
        "selection_contract": {
            "local_free_generation_enabled": False,
            "gpt_direct_item_admission_enabled": False,
            "qwen_direct_item_admission_enabled": False,
            "formal_item_requires_admission_approved": True,
            "recent_reuse_policy_source": "CELL_CAPACITY_POLICY",
        },
        "item_count": 1, "items": [item],
    }
    bank = {**bank_core, "bank_sha256": r6.digest(bank_core)}
    entries = [
        {
            "attempt_id": "ATTEMPT_FAIL", "session_id": "SESSION_1",
            "item_id": item["item_id"], "breadth_cell_id": CELL_ID,
            "capability_id": "CAP_ASK_LOCATION", "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
            "domain": "TRAVEL_TRANSPORT", "level": "A1", "skill": "SPEAKING",
            "purpose": "CORE_PRACTICE", "task_type": "GUIDED_RESPONSE",
            "support_level": "S1_KEYWORD_OR_VISUAL", "initiative_level": "GUIDED_INITIATION",
            "interaction_variation": "EXPECTED_SCRIPT", "transfer_distance": "NONE",
            "template_family": item["template_family"], "stimulus_fingerprint": item["stimulus_fingerprint"],
            "response": "Where bus stop?", "response_sha256": r6.digest("Where bus stop?"),
            "response_time_ms": 3500, "hint_count": 1, "revision_count": 0,
            "submitted_at": "2026-07-19T00:10:00Z", "session_state": "COMPLETED",
            "scoring_mode": "FEATURE_RUBRIC", "outcome": "HUMAN_REJECT", "score": 0.0,
            "human_review_required": False,
            "operator_review": {
                "decision": "REJECT", "reviewer_id": "teacher",
                "reviewed_at": "2026-07-19T00:11:00Z",
                "criteria": {"grammar_target_match": False, "meaning_matches_context": True, "complete_response": False},
                "notes": "Missing auxiliary and article.",
            },
            "validity_status": r1.VALID, "attempt_hash": "e" * 64,
        },
        {
            "attempt_id": "ATTEMPT_INVALID", "session_id": "SESSION_2",
            "item_id": item["item_id"], "breadth_cell_id": CELL_ID,
            "capability_id": "CAP_ASK_LOCATION", "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
            "domain": "TRAVEL_TRANSPORT", "level": "A1", "skill": "SPEAKING",
            "purpose": "CORE_PRACTICE", "task_type": "GUIDED_RESPONSE",
            "support_level": "S1_KEYWORD_OR_VISUAL", "initiative_level": "GUIDED_INITIATION",
            "interaction_variation": "EXPECTED_SCRIPT", "transfer_distance": "NONE",
            "template_family": item["template_family"], "stimulus_fingerprint": item["stimulus_fingerprint"],
            "response": "garbled", "response_sha256": r6.digest("garbled"),
            "response_time_ms": 5, "hint_count": 0, "revision_count": 0,
            "submitted_at": "2026-07-19T00:20:00Z", "session_state": "COMPLETED",
            "scoring_mode": "FEATURE_RUBRIC", "outcome": "HUMAN_REJECT", "score": 0.0,
            "human_review_required": False,
            "operator_review": {
                "decision": "REJECT", "reviewer_id": "teacher",
                "reviewed_at": "2026-07-19T00:21:00Z",
                "criteria": {"grammar_target_match": False, "meaning_matches_context": False, "complete_response": False},
                "notes": "UI serialization failure.",
            },
            "validity_status": "INVALIDATED_SYSTEM_ERROR", "attempt_hash": "f" * 64,
        },
    ]
    package_core = {
        "task_id": r5.TASK_ID, "schema_version": r5.PACKAGE_SCHEMA_VERSION,
        "validation_status": r5.STATUS, "private_local_only": True,
        "learner_id": "learner-private-id", "exported_at": "2026-07-19T00:30:00Z",
        "database_binding_sha256": "1" * 64,
        "attempt_count": 2, "valid_attempt_count": 1, "resolved_valid_attempt_count": 1,
        "entries": entries, "entries_sha256": r6.digest(entries),
        "objective_summary": {CELL_ID: {"attempts": 1, "failures": 1, "passes": 0, "unresolved": 0}},
        "claim_boundaries": {
            "mastery_written": False, "retention_confirmed": False,
            "gpt_analysis_performed": False, "qwen_used": False,
            "a2_unlocked": False, "public_delivery": False,
        },
        "next_short_step": r5.NEXT_SHORT_STEP,
    }
    package = {**package_core, "package_sha256": r6.digest(package_core)}
    safe_entries = [{key: value for key, value in row.items() if key not in {"response", "operator_review"}} for row in entries]
    safe_core = {
        "task_id": r5.TASK_ID, "schema_version": r5.SAFE_SCHEMA_VERSION,
        "validation_status": r5.STATUS, "learner_ref_sha256": r6.digest("learner-private-id"),
        "exported_at": "2026-07-19T00:30:00Z", "attempt_count": 2,
        "valid_attempt_count": 1, "resolved_valid_attempt_count": 1,
        "outcome_counts": {"HUMAN_REJECT": 2},
        "validity_counts": {"INVALIDATED_SYSTEM_ERROR": 1, "VALID": 1},
        "objective_summary": package_core["objective_summary"], "entries": safe_entries,
        "entries_sha256": r6.digest(safe_entries),
        "claim_boundaries": package_core["claim_boundaries"],
        "next_short_step": r5.NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "summary_sha256": r6.digest(safe_core)}
    coverage = _coverage()
    return {
        "package": _write(tmp_path / "evidence.private.json", package),
        "safe": _write(tmp_path / "evidence.safe.json", safe),
        "bank": _write(tmp_path / "bank.json", bank),
        "coverage": _write(tmp_path / "coverage.json", coverage),
    }


def _valid_response(request):
    evidence_ref = request["representative_evidence"][0]["evidence_ref"]
    core = {
        "task_id": r6.TASK_ID,
        "schema_version": r6.RESPONSE_SCHEMA_VERSION,
        "request_sha256": request["request_sha256"],
        "candidate_only": True,
        "model_metadata": {
            "provider": "OpenAI", "model_id": "diagnostic-model",
            "generated_at": "2026-07-19T09:00:00+08:00",
        },
        "evidence_sufficiency": {"status": "SUFFICIENT", "reason_codes": [], "missing_evidence_requests": []},
        "diagnoses": [{
            "diagnosis_id": "DIAG_WHERE_AUXILIARY",
            "category": "LANGUAGE_KNOWLEDGE",
            "scope": {"breadth_cell_ids": [CELL_ID], "capability_ids": ["CAP_ASK_LOCATION"], "skills": ["SPEAKING"]},
            "evidence_refs": [evidence_ref], "confidence": 0.88,
            "explanation": "The response preserves the location intent but omits the auxiliary verb and article.",
            "candidate_only": True,
        }],
        "recommendations": [{
            "recommendation_id": "REC_WHERE_GUIDED_REMEDIATION",
            "type": "REMEDIATION_CANDIDATE",
            "diagnosis_ids": ["DIAG_WHERE_AUXILIARY"],
            "target_breadth_cell_id": CELL_ID,
            "evidence_refs": [evidence_ref],
            "action_payload": {
                "strategy": "GUIDED_WHERE_QUESTION_REBUILD",
                "support_level": "S2_FRAME",
                "required_variation": "EXPECTED_SCRIPT",
                "level": "A1",
            },
            "candidate_only": True,
        }],
        "prohibited_write_confirmation": {
            "mastery_written": False, "score_overridden": False,
            "canonical_authority_written": False, "practice_bank_written": False,
            "active_planner_policy_written": False, "a2_unlocked": False,
        },
    }
    return {**core, "response_sha256": r6.digest(core)}


def _decisions(request, response, decision="APPROVE_AS_CANDIDATE", all_true=True):
    criteria = {key: all_true for key in r6.GATE_CRITERIA}
    rows = [{
        "recommendation_id": "REC_WHERE_GUIDED_REMEDIATION",
        "decision": decision,
        "reviewer_id": "authority-reviewer",
        "reviewed_at": "2026-07-19T10:00:00+08:00",
        "criteria": criteria,
        "notes": "Hash-bound candidate review.",
    }]
    return r6.decision_registry(
        request_sha256=request["request_sha256"],
        response_sha256=response["response_sha256"],
        decisions=rows,
    )


def test_request_is_deidentified_and_excludes_invalid_system_evidence(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    request, safe = r6.build_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
    )
    assert request["learner_ref_sha256"] == r6.digest("learner-private-id")
    assert "learner_id" not in request
    assert request["analysis_window"]["attempt_count"] == 2
    assert request["analysis_window"]["representative_evidence_count"] == 1
    assert request["representative_evidence"][0]["response"] == "Where bus stop?"
    assert all(row["validity_status"] == "VALID" for row in request["representative_evidence"])
    assert safe["claim_boundaries"]["raw_response_included"] is False
    assert "response" not in json.dumps(safe)
    r6.safe_scan(safe)


def test_request_exact_rebuild_validator_passes_and_detects_tampering(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    request, safe = r6.build_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
    )
    request_path = _write(tmp_path / "request.json", request)
    safe_path = _write(tmp_path / "request.safe.json", safe)
    valid = validator.validate_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
        request_path=request_path, safe_request_path=safe_path,
    )
    assert valid["error_count"] == 0, valid["errors"]
    tampered = deepcopy(safe)
    tampered["analysis_window"]["attempt_count"] = 999
    safe_path.write_text(json.dumps(tampered), encoding="utf-8")
    invalid = validator.validate_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
        request_path=request_path, safe_request_path=safe_path,
    )
    assert invalid["error_count"] > 0


def test_structured_response_requires_grounded_refs_and_blocks_direct_writes_or_a2(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    request, _ = r6.build_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
    )
    coverage = json.loads(sources["coverage"].read_text())
    response = _valid_response(request)
    valid = r6.validate_response(request=request, response=response, coverage=coverage)
    assert valid["error_count"] == 0, valid["errors"]
    broken = deepcopy(response)
    broken["recommendations"][0]["evidence_refs"] = ["UNKNOWN_EVIDENCE"]
    broken["recommendations"][0]["action_payload"]["mastery_state"] = "MASTERED"
    broken["recommendations"][0]["action_payload"]["level"] = "A2"
    core = r6.response_core(broken)
    broken["response_sha256"] = r6.digest(core)
    invalid = r6.validate_response(request=request, response=broken, coverage=coverage)
    assert any("recommendation_evidence_refs_invalid" in error for error in invalid["errors"])
    assert any("direct_write_key" in error for error in invalid["errors"])
    assert any("level_out_of_scope" in error for error in invalid["errors"])


def test_insufficient_evidence_response_cannot_emit_recommendations(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    request, _ = r6.build_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
    )
    coverage = json.loads(sources["coverage"].read_text())
    response = _valid_response(request)
    response["evidence_sufficiency"] = {
        "status": "INSUFFICIENT", "reason_codes": ["NEEDS_S0_EVIDENCE"],
        "missing_evidence_requests": ["Collect independent S0 speaking evidence."],
    }
    response["response_sha256"] = r6.digest(r6.response_core(response))
    result = r6.validate_response(request=request, response=response, coverage=coverage)
    assert "recommendations_for_insufficient_evidence_forbidden" in result["errors"]


def test_hash_bound_gate_emits_candidate_only_queue_not_active_policy(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    request, _ = r6.build_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
    )
    coverage = json.loads(sources["coverage"].read_text())
    response = _valid_response(request)
    decisions = _decisions(request, response)
    queue, report = r6.apply_gate(request=request, response=response, decisions=decisions, coverage=coverage)
    assert queue["candidate_count"] == 1
    candidate = queue["candidates"][0]
    assert candidate["activation_state"] == "CANDIDATE_ONLY_NOT_ACTIVE"
    assert candidate["gate"]["request_sha256"] == request["request_sha256"]
    assert candidate["gate"]["response_sha256"] == response["response_sha256"]
    assert queue["activation_contract"]["separate_downstream_promotion_required"] is True
    assert queue["activation_contract"]["mastery_written"] is False
    assert report["claim_boundaries"]["active_policy_written"] is False
    assert "action_payload" not in json.dumps(report)
    r6.safe_scan(report)


def test_gate_rejects_incomplete_approval_criteria_and_decision_hash_drift(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    request, _ = r6.build_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
    )
    coverage = json.loads(sources["coverage"].read_text())
    response = _valid_response(request)
    decisions = _decisions(request, response, all_true=False)
    with pytest.raises(r6.DiagnosticGateError, match="approved_decision_criteria_not_all_true"):
        r6.apply_gate(request=request, response=response, decisions=decisions, coverage=coverage)
    decisions = _decisions(request, response)
    decisions["response_sha256"] = "0" * 64
    with pytest.raises(r6.DiagnosticGateError, match="decision_response_binding_invalid"):
        r6.apply_gate(request=request, response=response, decisions=decisions, coverage=coverage)


def test_gate_exact_rebuild_validator_detects_queue_tampering(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    request, _ = r6.build_request(
        evidence_package_path=sources["package"], evidence_safe_path=sources["safe"],
        bank_path=sources["bank"], coverage_path=sources["coverage"],
    )
    coverage = json.loads(sources["coverage"].read_text())
    response = _valid_response(request)
    decisions = _decisions(request, response)
    queue, report = r6.apply_gate(request=request, response=response, decisions=decisions, coverage=coverage)
    request_path = _write(tmp_path / "request.json", request)
    response_path = _write(tmp_path / "response.json", response)
    decisions_path = _write(tmp_path / "decisions.json", decisions)
    queue_path = _write(tmp_path / "queue.json", queue)
    report_path = _write(tmp_path / "report.json", report)
    valid = validator.validate_gate(
        request_path=request_path, response_path=response_path, decisions_path=decisions_path,
        coverage_path=sources["coverage"], queue_path=queue_path, report_path=report_path,
    )
    assert valid["error_count"] == 0, valid["errors"]
    queue["candidates"][0]["activation_state"] = "ACTIVE"
    queue_path.write_text(json.dumps(queue), encoding="utf-8")
    invalid = validator.validate_gate(
        request_path=request_path, response_path=response_path, decisions_path=decisions_path,
        coverage_path=sources["coverage"], queue_path=queue_path, report_path=report_path,
    )
    assert invalid["error_count"] > 0
