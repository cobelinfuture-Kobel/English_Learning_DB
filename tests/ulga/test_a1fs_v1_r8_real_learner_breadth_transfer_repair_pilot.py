from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders import build_a1fs_v1_r8_real_learner_breadth_transfer_repair_pilot as r8
from ulga.validators.validate_a1fs_v1_r8_real_learner_breadth_transfer_repair_pilot import validate


def _write(path: Path, value) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _with_digest(core, key):
    return {**core, key: r8.digest(core)}


def _source_fixture(tmp_path: Path, *, blocked: bool = False):
    dimensions = {
        "skills": {"required": ["READING", "WRITING"], "observed": [], "missing": ["READING", "WRITING"]},
        "support_levels": {"required": ["S3_FULL_MODEL", "S2_FRAME", "S1_KEYWORD_OR_VISUAL", "S0_INDEPENDENT"], "observed": [], "missing": []},
        "initiative_levels": {"required": ["RESPOND_ONLY", "CHOOSE_FROM_OPTIONS", "GUIDED_INITIATION", "INDEPENDENT_INITIATION", "SUSTAIN_INTERACTION", "REPAIR_AND_CLOSE_TASK"], "observed": [], "missing": []},
        "variation_types": {"required": ["EXPECTED_SCRIPT", "LEXICAL_VARIATION", "UNEXPECTED_EVENT", "REPAIR_REQUIRED"], "observed": [], "missing": []},
        "transfer_distances": {"required": ["NONE", "NEAR", "MEDIUM", "FAR"], "observed": [], "missing": []},
        "evidence_levels": {"required": ["E1_RECOGNITION", "E2_CONTROLLED_PRODUCTION", "E3_INDEPENDENT_PRODUCTION", "E4_CROSS_CONTEXT_TRANSFER", "E5_DELAYED_RETENTION", "E6_AUTHENTIC_TASK_PERFORMANCE"], "observed": [], "missing": []},
        "retention_stages": {"required": ["DAY_1", "DAY_3", "DAY_7", "RETAINED"], "observed": [], "missing": []},
    }
    cells = [
        {
            "cell_id": "CELL_CORE", "capability_node_id": "REF:READING:C1", "capability_id": "CAP_COMPLETE_LIFE_TASK",
            "obligation_id": "BREADTH_OBLIGATION_CORE", "life_task_id": "LIFE_TASK_CORE", "domain": "SCHOOL_CLASSROOM",
            "status": "CONTENT_MISSING" if blocked else "READY_TO_DEPLOY", "dimension_coverage": dimensions,
            "matching_deployment_ids": [], "source_refs": ["SOURCE_CORE"], "next_actions": [],
        },
        {
            "cell_id": "CELL_MEDIA", "capability_node_id": "REF:LISTENING:C2", "capability_id": "CAP_LISTEN_MEDIA",
            "obligation_id": "BREADTH_OBLIGATION_MEDIA", "life_task_id": "LIFE_TASK_MEDIA", "domain": "TRAVEL_TRANSPORT",
            "status": "DEFERRED_MEDIA", "dimension_coverage": dimensions,
            "matching_deployment_ids": [], "source_refs": ["SOURCE_MEDIA"], "next_actions": [],
        },
    ]
    status_counts = {name: 0 for name in (
        "PROFILE_DEFINITION_REQUIRED", "CONTENT_MISSING", "ITEMS_MISSING", "READY_TO_DEPLOY", "DEPLOYED",
        "EVIDENCE_INSUFFICIENT", "SUPPORTED_PASS", "INDEPENDENT_PASS", "TRANSFER_PASS", "RETENTION_PASS",
        "BLOCKED_SYSTEM_ERROR", "DEFERRED_MEDIA",
    )}
    for cell in cells:
        status_counts[cell["status"]] += 1
    r3_core = {
        "task_id": r8.R3_TASK_ID, "schema_version": r8.R3_SCHEMA_VERSION, "validation_status": r8.R3_STATUS,
        "source_bindings": {"ontology_sha256": "1" * 64, "graph_sha256": "2" * 64, "profiles_sha256": "3" * 64, "deployments_sha256": "4" * 64, "m10_structural_coverage": None},
        "counts": {"required_mastery_node_count": 2, "required_capability_node_count": 2, "profile_defined_count": 2, "profile_missing_count": 0, "denominator_cell_count": 2, "deployment_contract_count": 0, "gap_count": 2, "status_counts": status_counts},
        "coverage_metrics": {"structural_ready_count": 2, "structural_ready_percent": 100.0, "retention_complete_count": 0, "retention_complete_percent": 0.0, "false_100_percent_blocked": True, "completion_denominator_source": "EXPLICIT_BREADTH_REQUIREMENT_CELLS_PLUS_PROFILE_PLACEHOLDERS"},
        "profile_missing_capability_node_ids": [], "cells": cells, "ranked_gaps": [],
        "claim_boundaries": {"m1_graph_modified": False, "m10_structural_coverage_replaced": False, "cartesian_product_generated": False, "a2_unlocked": False, "mastery_claimed": False, "retention_claimed_from_structure": False, "audio_completion_required": False},
        "next_short_step": "A1FS-V1-R4_CentralQuestionSupplySkillProjectionAndCapacityGovernance",
    }
    r3 = _with_digest(r3_core, "report_sha256")
    r3_path = _write(tmp_path / "r3.json", r3)
    supply = [
        {"breadth_cell_id": "CELL_CORE", "capability_id": "CAP_COMPLETE_LIFE_TASK", "life_task_id": "LIFE_TASK_CORE", "domain": "SCHOOL_CLASSROOM", "supply_status": "CONTENT_MISSING" if blocked else "READY_FOR_LOCAL_SELECTION", "capacity_policy_present": True, "approved_item_count": 6, "approved_item_ids": [f"ITEM_{i}" for i in range(1, 7)], "skill_projection": {"required": ["READING", "WRITING"], "approved": ["READING", "WRITING"], "missing": []}, "purpose_capacity": {}, "decision_counts": {}, "max_recent_reuse": 0},
        {"breadth_cell_id": "CELL_MEDIA", "capability_id": "CAP_LISTEN_MEDIA", "life_task_id": "LIFE_TASK_MEDIA", "domain": "TRAVEL_TRANSPORT", "supply_status": "MEDIA_DEFERRED", "capacity_policy_present": True, "approved_item_count": 1, "approved_item_ids": ["ITEM_MEDIA"], "skill_projection": {"required": ["LISTENING"], "approved": ["LISTENING"], "missing": []}, "purpose_capacity": {}, "decision_counts": {}, "max_recent_reuse": 0},
    ]
    r4_core = {
        "task_id": r8.R4_TASK_ID, "schema_version": r8.R4_SCHEMA_VERSION, "validation_status": r8.R4_STATUS,
        "source_bindings": {"ontology_sha256": "1" * 64, "coverage_sha256": r3["report_sha256"], "candidate_registry_sha256": "5" * 64, "capacity_policy_registry_sha256": "6" * 64},
        "counts": {"candidate_count": 7, "approved_item_count": 7, "rejected_or_pending_count": 0, "breadth_cell_count": 2, "capacity_policy_count": 2, "supply_status_counts": {}, "admission_status_counts": {"APPROVED": 7}},
        "cell_supply": supply, "admission_decisions": [],
        "claim_boundaries": {"canonical_authority_modified": False, "m1_graph_modified": False, "r3_denominator_modified": False, "local_free_generation_enabled": False, "gpt_direct_admission_enabled": False, "qwen_required": False, "a2_content_admitted": False, "audio_files_required": False, "mastery_claimed": False},
        "next_short_step": "A1FS-V1-R5_LocalEdgeRuntimeAndCompleteEvidenceCollector",
    }
    r4 = _with_digest(r4_core, "report_sha256")
    return r3, r3_path, r4, _write(tmp_path / "r4.json", r4)


def _entry(index, *, support, initiative, variation, transfer, skill, purpose="CORE_PRACTICE", fingerprint=None, validity="VALID"):
    response = f"response-{index}"
    return {
        "attempt_id": f"ATTEMPT_{index}", "session_id": f"SESSION_{index}", "item_id": f"ITEM_{index}", "breadth_cell_id": "CELL_CORE",
        "capability_id": "CAP_COMPLETE_LIFE_TASK", "life_task_id": "LIFE_TASK_CORE", "domain": "SCHOOL_CLASSROOM",
        "level": "A1", "skill": skill, "purpose": purpose, "task_type": "MULTI_STEP_LIFE_TASK",
        "support_level": support, "initiative_level": initiative, "interaction_variation": variation,
        "transfer_distance": transfer, "template_family": f"TEMPLATE_{index}", "stimulus_fingerprint": fingerprint or f"FP_{index}",
        "response": response, "response_sha256": r8.digest(response), "response_time_ms": 1000 + index,
        "hint_count": 0, "revision_count": 0, "submitted_at": f"2026-07-19T00:{index:02d}:00Z", "session_state": "COMPLETED",
        "scoring_mode": "NORMALIZED_TEXT", "outcome": "AUTO_PASS", "score": 1.0, "human_review_required": False,
        "operator_review": {"decision": "PENDING", "reviewer_id": None, "reviewed_at": None, "criteria": {}, "notes": None},
        "validity_status": validity, "attempt_hash": f"{index:x}".rjust(64, "0"),
    }


def _evidence_fixture(tmp_path: Path, r3, r4, *, invalidate_far=False):
    entries = [
        _entry(1, support="S3_FULL_MODEL", initiative="RESPOND_ONLY", variation="EXPECTED_SCRIPT", transfer="NONE", skill="READING"),
        _entry(2, support="S2_FRAME", initiative="CHOOSE_FROM_OPTIONS", variation="LEXICAL_VARIATION", transfer="NEAR", skill="WRITING"),
        _entry(3, support="S1_KEYWORD_OR_VISUAL", initiative="GUIDED_INITIATION", variation="UNEXPECTED_EVENT", transfer="MEDIUM", skill="READING"),
        _entry(4, support="S0_INDEPENDENT", initiative="INDEPENDENT_INITIATION", variation="REPAIR_REQUIRED", transfer="FAR", skill="WRITING", validity="INVALIDATED_SYSTEM_ERROR" if invalidate_far else "VALID"),
        _entry(5, support="S0_INDEPENDENT", initiative="SUSTAIN_INTERACTION", variation="EXPECTED_SCRIPT", transfer="FAR", skill="READING", purpose="TRANSFER"),
        _entry(6, support="S0_INDEPENDENT", initiative="REPAIR_AND_CLOSE_TASK", variation="REPAIR_REQUIRED", transfer="FAR", skill="WRITING", purpose="REASSESSMENT", fingerprint="FP_REASSESS_NEW"),
    ]
    package_core = {
        "task_id": r8.R5_TASK_ID, "schema_version": r8.R5_PACKAGE_SCHEMA_VERSION, "validation_status": r8.R5_STATUS,
        "private_local_only": True, "learner_id": "learner-real-01", "exported_at": "2026-07-19T01:00:00Z",
        "database_binding_sha256": "7" * 64, "attempt_count": len(entries),
        "valid_attempt_count": sum(row["validity_status"] == "VALID" for row in entries),
        "resolved_valid_attempt_count": sum(row["validity_status"] == "VALID" for row in entries),
        "entries": entries, "entries_sha256": r8.digest(entries), "objective_summary": {"CELL_CORE": {"attempts": len(entries), "passes": len(entries), "failures": 0, "unresolved": 0}},
        "claim_boundaries": {"mastery_written": False, "retention_confirmed": False, "gpt_analysis_performed": False, "qwen_used": False, "a2_unlocked": False, "public_delivery": False},
        "next_short_step": "A1FS-V1-R6_GPTDiagnosticPackageAndControlledRecommendationGate",
    }
    package = _with_digest(package_core, "package_sha256")
    safe_entries = [{key: value for key, value in row.items() if key not in {"response", "operator_review"}} for row in entries]
    safe_core = {
        "task_id": r8.R5_TASK_ID, "schema_version": r8.R5_SAFE_SCHEMA_VERSION, "validation_status": r8.R5_STATUS,
        "learner_ref_sha256": r8.digest(package["learner_id"]), "exported_at": package["exported_at"],
        "attempt_count": len(entries), "valid_attempt_count": package["valid_attempt_count"], "resolved_valid_attempt_count": package["resolved_valid_attempt_count"],
        "outcome_counts": {"AUTO_PASS": len(entries)}, "validity_counts": dict(Counter(row["validity_status"] for row in entries)),
        "objective_summary": package["objective_summary"], "entries": safe_entries, "entries_sha256": r8.digest(safe_entries),
        "claim_boundaries": package["claim_boundaries"], "next_short_step": package["next_short_step"],
    }
    safe = _with_digest(safe_core, "summary_sha256")
    package_path = _write(tmp_path / "r5.private.json", package)
    safe_path = _write(tmp_path / "r5.safe.json", safe)
    work_items = [{"work_item_id": "WORK_REDEPLOY", "finding_type": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT", "route": "PLANNER_REDEPLOY", "severity": "P2", "breadth_cell_id": "CELL_CORE", "summary_code": "BREADTH_EVIDENCE_INSUFFICIENT", "work_state": "OPEN", "required_gates": []}]
    r7_core = {
        "task_id": r8.R7_TASK_ID, "schema_version": r8.R7_REPORT_SCHEMA_VERSION, "validation_status": r8.R7_STATUS,
        "source_bindings": {"r3_report_sha256": r3["report_sha256"], "r4_report_sha256": r4["report_sha256"], "r5_summary_sha256": safe["summary_sha256"], "r6_queue_sha256": "8" * 64, "r6_report_sha256": "9" * 64, "explicit_findings_sha256": None},
        "counts": {"finding_count": 1, "work_item_count": 1, "finding_type_counts": {}, "route_counts": {"PLANNER_REDEPLOY": 1}, "state_counts": {"OPEN": 1, "CLOSED": 0, "BLOCKED": 0}},
        "work_items": work_items,
        "claim_boundaries": {"code_modified": False, "github_issue_created": False, "canonical_authority_modified": False, "practice_bank_modified": False, "planner_policy_modified": False, "mastery_modified": False, "a2_unlocked": False, "gpt_candidate_executed_directly": False},
        "next_short_step": "A1FS-V1-R8_RealLearnerBreadthTransferAndRepairPilot",
    }
    r7 = _with_digest(r7_core, "report_sha256")
    return entries, package, package_path, safe, safe_path, _write(tmp_path / "r7.json", r7)


def _observation(row, evidence_level):
    repair_required = row["interaction_variation"] in {"UNEXPECTED_EVENT", "REPAIR_REQUIRED"}
    transfer_required = row["transfer_distance"] != "NONE"
    return {
        "attempt_id": row["attempt_id"], "session_id": row["session_id"], "breadth_cell_id": row["breadth_cell_id"],
        "observed_at": row["submitted_at"], "operator_ref": "OPERATOR_PARENT_01", "delivery_mode": "AUTHENTIC_LIFE_TASK" if evidence_level == "E6_AUTHENTIC_TASK_PERFORMANCE" else "LOCAL_RUNTIME",
        "language_accuracy": "PASS", "meaning_success": "PASS", "life_task_completion": "PASS", "pragmatic_appropriacy": "PASS",
        "independence": "PASS", "initiative": "PASS", "repair": "PASS" if repair_required else "NOT_APPLICABLE",
        "transfer": "PASS" if transfer_required else "NOT_APPLICABLE", "evidence_level": evidence_level,
        "evidence_refs": [row["attempt_hash"], row["item_id"]],
    }


def _attestation(tmp_path, package, safe, entries, *, synthetic=False):
    levels = ["E1_RECOGNITION", "E2_CONTROLLED_PRODUCTION", "E2_CONTROLLED_PRODUCTION", "E3_INDEPENDENT_PRODUCTION", "E4_CROSS_CONTEXT_TRANSFER", "E6_AUTHENTIC_TASK_PERFORMANCE"]
    selected = [(row, level) for row, level in zip(entries, levels) if row["validity_status"] == "VALID"]
    value = r8.attestation_registry(
        learner_ref_sha256=safe["learner_ref_sha256"], r5_package_sha256=package["package_sha256"], r5_summary_sha256=safe["summary_sha256"],
        operator_ref="OPERATOR_PARENT_01", attested_at="2026-07-19T02:00:00Z",
        session_ids=[row["session_id"] for row, _ in selected], observations=[_observation(row, level) for row, level in selected],
        session_recovery_event_refs=["R5_EVENT:PAUSED", "R5_EVENT:RESUMED"],
    )
    if synthetic:
        value["synthetic_fixture"] = True
        value["attestation_sha256"] = r8.digest({key: child for key, child in value.items() if key != "attestation_sha256"})
    return _write(tmp_path / "attestation.json", value)


def test_contract_preserves_complete_denominator_and_defers_media(tmp_path: Path) -> None:
    r3, r3_path, r4, r4_path = _source_fixture(tmp_path)
    _, _, _, _, _, r7_path = _evidence_fixture(tmp_path, r3, r4)
    contract = r8.build_pilot_contract(r3_path=r3_path, r4_path=r4_path, r7_report_path=r7_path)
    assert contract["counts"]["complete_breadth_denominator_count"] == 2
    assert contract["counts"]["real_learner_required_cell_count"] == 1
    assert contract["counts"]["media_deferred_cell_count"] == 1
    assert contract["counts"]["r9_deferred_requirement_count"] == 2
    assert contract["contract_ready_for_real_evidence"] is True
    assert contract["claim_boundaries"]["complete_denominator_reduced"] is False


def test_precondition_gap_blocks_pilot_contract(tmp_path: Path) -> None:
    r3, r3_path, r4, r4_path = _source_fixture(tmp_path, blocked=True)
    _, _, _, _, _, r7_path = _evidence_fixture(tmp_path, r3, r4)
    contract = r8.build_pilot_contract(r3_path=r3_path, r4_path=r4_path, r7_report_path=r7_path)
    assert contract["contract_ready_for_real_evidence"] is False
    assert contract["counts"]["precondition_blocked_cell_count"] == 1


def test_synthetic_attestation_is_rejected(tmp_path: Path) -> None:
    r3, r3_path, r4, r4_path = _source_fixture(tmp_path)
    entries, package, package_path, safe, safe_path, r7_path = _evidence_fixture(tmp_path, r3, r4)
    contract_path = _write(tmp_path / "contract.json", r8.build_pilot_contract(r3_path=r3_path, r4_path=r4_path, r7_report_path=r7_path))
    with pytest.raises(r8.RealLearnerPilotError, match="synthetic_or_non_real_learner_evidence_forbidden"):
        r8.evaluate_pilot(contract_path=contract_path, r5_package_path=package_path, r5_safe_path=safe_path, r7_report_path=r7_path, attestation_path=_attestation(tmp_path, package, safe, entries, synthetic=True))


def test_real_learner_full_breadth_pilot_passes_without_false_release_claim(tmp_path: Path) -> None:
    r3, r3_path, r4, r4_path = _source_fixture(tmp_path)
    entries, package, package_path, safe, safe_path, r7_path = _evidence_fixture(tmp_path, r3, r4)
    contract_path = _write(tmp_path / "contract.json", r8.build_pilot_contract(r3_path=r3_path, r4_path=r4_path, r7_report_path=r7_path))
    attestation_path = _attestation(tmp_path, package, safe, entries)
    report = r8.evaluate_pilot(contract_path=contract_path, r5_package_path=package_path, r5_safe_path=safe_path, r7_report_path=r7_path, attestation_path=attestation_path)
    assert report["pilot_state"] == "PASS" and all(report["gates"].values())
    assert report["claim_boundaries"]["real_learner_pilot_claimed"] is True
    assert report["claim_boundaries"]["true_four_skill_release_claimed"] is False
    assert report["claim_boundaries"]["retention_confirmed"] is False
    assert report["next_short_step"] == r8.NEXT_SHORT_STEP
    schema = json.loads(Path("ulga/schemas/a1fs_v1_r8_real_learner_pilot_report.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(report))
    result = validate(_write(tmp_path / "report.json", report), contract_path=contract_path, r5_package_path=package_path, r5_safe_path=safe_path, r7_report_path=r7_path, attestation_path=attestation_path)
    assert result["error_count"] == 0, result["errors"]


def test_invalid_system_error_evidence_is_excluded_and_gap_remains_visible(tmp_path: Path) -> None:
    r3, r3_path, r4, r4_path = _source_fixture(tmp_path)
    entries, package, package_path, safe, safe_path, r7_path = _evidence_fixture(tmp_path, r3, r4, invalidate_far=True)
    contract_path = _write(tmp_path / "contract.json", r8.build_pilot_contract(r3_path=r3_path, r4_path=r4_path, r7_report_path=r7_path))
    report = r8.evaluate_pilot(contract_path=contract_path, r5_package_path=package_path, r5_safe_path=safe_path, r7_report_path=r7_path, attestation_path=_attestation(tmp_path, package, safe, entries))
    assert report["pilot_state"] == "IN_PROGRESS"
    assert report["counts"]["excluded_attempt_count"] == 1
    assert report["counts"]["dimension_gap_count"] > 0
    assert report["claim_boundaries"]["real_learner_pilot_claimed"] is False


def test_report_tampering_fails_reconstruction_validation(tmp_path: Path) -> None:
    r3, r3_path, r4, r4_path = _source_fixture(tmp_path)
    entries, package, package_path, safe, safe_path, r7_path = _evidence_fixture(tmp_path, r3, r4)
    contract_path = _write(tmp_path / "contract.json", r8.build_pilot_contract(r3_path=r3_path, r4_path=r4_path, r7_report_path=r7_path))
    attestation_path = _attestation(tmp_path, package, safe, entries)
    report = r8.evaluate_pilot(contract_path=contract_path, r5_package_path=package_path, r5_safe_path=safe_path, r7_report_path=r7_path, attestation_path=attestation_path)
    report["counts"]["passed_required_cell_count"] = 0
    result = validate(_write(tmp_path / "tampered.json", report), contract_path=contract_path, r5_package_path=package_path, r5_safe_path=safe_path, r7_report_path=r7_path, attestation_path=attestation_path)
    assert result["error_count"] > 0
    assert "report_digest_invalid" in result["errors"] or "report_reconstruction_mismatch" in result["errors"]
