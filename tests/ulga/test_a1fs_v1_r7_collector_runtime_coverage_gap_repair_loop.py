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
from ulga.builders import build_a1fs_v1_r7_collector_runtime_coverage_gap_repair_loop as r7
from ulga.validators import validate_a1fs_v1_r7_collector_runtime_coverage_gap_repair_loop as validator


def _write(path: Path, value) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _cell(cell_id: str, status: str):
    return {
        "cell_id": cell_id,
        "capability_node_id": f"REF:SPEAKING:{cell_id}",
        "capability_id": f"CAP_{cell_id}",
        "obligation_id": None if status == "PROFILE_DEFINITION_REQUIRED" else f"OBLIGATION_{cell_id}",
        "life_task_id": None if status == "PROFILE_DEFINITION_REQUIRED" else f"LIFE_TASK_{cell_id}",
        "domain": None if status == "PROFILE_DEFINITION_REQUIRED" else "TRAVEL_TRANSPORT",
        "status": status,
        "dimension_coverage": {},
        "matching_deployment_ids": [],
        "next_actions": [f"ACTION_{status}"],
    }


def _sources(tmp_path: Path):
    cells = [
        _cell("PROFILE", "PROFILE_DEFINITION_REQUIRED"),
        _cell("EVIDENCE", "EVIDENCE_INSUFFICIENT"),
        _cell("SYSTEM", "BLOCKED_SYSTEM_ERROR"),
        _cell("CONTENT", "CONTENT_MISSING"),
        _cell("MEDIA", "DEFERRED_MEDIA"),
    ]
    r3_core = {
        "task_id": r3.TASK_ID, "schema_version": r3.SCHEMA_VERSION,
        "validation_status": r3.STATUS,
        "source_bindings": {
            "ontology_sha256": "1" * 64, "graph_sha256": "2" * 64,
            "profiles_sha256": "3" * 64, "deployments_sha256": "4" * 64,
            "m10_structural_coverage": None,
        },
        "counts": {
            "required_mastery_node_count": 6, "required_capability_node_count": 5,
            "profile_defined_count": 4, "profile_missing_count": 1,
            "denominator_cell_count": 5, "deployment_contract_count": 2,
            "gap_count": 5,
            "status_counts": {status: sum(row["status"] == status for row in cells) for status in r3.CELL_STATUSES},
        },
        "coverage_metrics": {
            "structural_ready_count": 2, "structural_ready_percent": 40.0,
            "retention_complete_count": 0, "retention_complete_percent": 0.0,
            "false_100_percent_blocked": True,
            "completion_denominator_source": "EXPLICIT_BREADTH_REQUIREMENT_CELLS_PLUS_PROFILE_PLACEHOLDERS",
        },
        "profile_missing_capability_node_ids": ["REF:SPEAKING:PROFILE"],
        "cells": cells,
        "ranked_gaps": [],
        "claim_boundaries": {
            "m1_graph_modified": False, "m10_structural_coverage_replaced": False,
            "cartesian_product_generated": False, "a2_unlocked": False,
            "mastery_claimed": False, "retention_claimed_from_structure": False,
            "audio_completion_required": False,
        },
        "next_short_step": r3.NEXT_SHORT_STEP,
    }
    r3_value = {**r3_core, "report_sha256": r7.digest(r3_core)}

    supply = [
        {
            "breadth_cell_id": "CONTENT", "capability_id": "CAP_CONTENT",
            "life_task_id": "LIFE_TASK_CONTENT", "domain": "TRAVEL_TRANSPORT",
            "supply_status": "CAPACITY_INSUFFICIENT", "capacity_policy_present": True,
            "approved_item_count": 1, "approved_item_ids": ["ITEM_1"],
            "skill_projection": {"required": ["SPEAKING"], "approved": ["SPEAKING"], "missing": []},
            "purpose_capacity": {"CORE_PRACTICE": {"capacity_pass": False}},
            "decision_counts": {"APPROVED": 1}, "max_recent_reuse": 0,
        },
        {
            "breadth_cell_id": "VALIDATOR", "capability_id": "CAP_VALIDATOR",
            "life_task_id": "LIFE_TASK_VALIDATOR", "domain": "SCHOOL",
            "supply_status": "VALIDATOR_FAILED", "capacity_policy_present": True,
            "approved_item_count": 0, "approved_item_ids": [],
            "skill_projection": {"required": ["READING"], "approved": [], "missing": ["READING"]},
            "purpose_capacity": {}, "decision_counts": {"VALIDATOR_NOT_PASS": 1}, "max_recent_reuse": 0,
        },
        {
            "breadth_cell_id": "REVIEW", "capability_id": "CAP_REVIEW",
            "life_task_id": "LIFE_TASK_REVIEW", "domain": "SCHOOL",
            "supply_status": "HUMAN_REVIEW_REQUIRED", "capacity_policy_present": True,
            "approved_item_count": 0, "approved_item_ids": [],
            "skill_projection": {"required": ["WRITING"], "approved": [], "missing": ["WRITING"]},
            "purpose_capacity": {}, "decision_counts": {"AUTHORITY_REVIEW_REQUIRED": 1}, "max_recent_reuse": 0,
        },
        {
            "breadth_cell_id": "MEDIA", "capability_id": "CAP_MEDIA",
            "life_task_id": "LIFE_TASK_MEDIA", "domain": "TRAVEL_TRANSPORT",
            "supply_status": "MEDIA_DEFERRED", "capacity_policy_present": True,
            "approved_item_count": 1, "approved_item_ids": ["ITEM_MEDIA"],
            "skill_projection": {"required": ["LISTENING"], "approved": ["LISTENING"], "missing": []},
            "purpose_capacity": {"CORE_PRACTICE": {"capacity_pass": True}},
            "decision_counts": {"APPROVED": 1}, "max_recent_reuse": 0,
        },
    ]
    r4_core = {
        "task_id": r4.TASK_ID, "schema_version": r4.SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "source_bindings": {
            "ontology_sha256": "1" * 64, "coverage_sha256": r3_value["report_sha256"],
            "candidate_registry_sha256": "5" * 64, "capacity_policy_registry_sha256": "6" * 64,
        },
        "counts": {
            "candidate_count": 4, "approved_item_count": 2, "rejected_or_pending_count": 2,
            "breadth_cell_count": 4, "capacity_policy_count": 4,
            "supply_status_counts": {
                "CAPACITY_INSUFFICIENT": 1, "HUMAN_REVIEW_REQUIRED": 1,
                "MEDIA_DEFERRED": 1, "VALIDATOR_FAILED": 1,
            },
            "admission_status_counts": {"APPROVED": 2, "AUTHORITY_REVIEW_REQUIRED": 1, "VALIDATOR_NOT_PASS": 1},
        },
        "cell_supply": supply,
        "admission_decisions": [],
        "claim_boundaries": {
            "canonical_authority_modified": False, "m1_graph_modified": False,
            "r3_denominator_modified": False, "local_free_generation_enabled": False,
            "gpt_direct_admission_enabled": False, "qwen_required": False,
            "a2_content_admitted": False, "audio_files_required": False,
            "mastery_claimed": False,
        },
        "next_short_step": r4.NEXT_SHORT_STEP,
    }
    r4_value = {**r4_core, "report_sha256": r7.digest(r4_core)}

    r5_core = {
        "task_id": r5.TASK_ID, "schema_version": r5.SAFE_SCHEMA_VERSION,
        "validation_status": r5.STATUS, "learner_ref_sha256": "7" * 64,
        "exported_at": "2026-07-19T00:00:00Z", "attempt_count": 5,
        "valid_attempt_count": 3, "resolved_valid_attempt_count": 2,
        "outcome_counts": {"AUTO_PASS": 2, "HUMAN_DEFER": 1, "HUMAN_REJECT": 2},
        "validity_counts": {"VALID": 3, "INVALIDATED_SYSTEM_ERROR": 1, "PENDING_VALIDITY_REVIEW": 1},
        "objective_summary": {"EVIDENCE": {"attempts": 3, "passes": 2, "failures": 0, "unresolved": 1}},
        "entries": [], "entries_sha256": r7.digest([]),
        "claim_boundaries": {
            "mastery_written": False, "retention_confirmed": False,
            "gpt_analysis_performed": False, "qwen_used": False,
            "a2_unlocked": False, "public_delivery": False,
        },
        "next_short_step": r5.NEXT_SHORT_STEP,
    }
    r5_value = {**r5_core, "summary_sha256": r7.digest(r5_core)}

    queue_bindings = {
        "request_sha256": "8" * 64, "response_sha256": "9" * 64,
        "decisions_sha256": "a" * 64, "coverage_sha256": r3_value["report_sha256"],
    }
    r6_candidates = [
        {
            "recommendation_id": "REC_COLLECTOR", "type": "COLLECTOR_GAP_CANDIDATE",
            "diagnosis_ids": ["DIAG_COLLECTOR"], "target_breadth_cell_id": "EVIDENCE",
            "evidence_refs": ["EVIDENCE_1"],
            "action_payload": {"missing_field": "hint_count"},
            "activation_state": "CANDIDATE_ONLY_NOT_ACTIVE",
            "gate": {"decision": "APPROVE_AS_CANDIDATE"},
        },
        {
            "recommendation_id": "REC_CONTENT", "type": "CONTENT_GAP_CANDIDATE",
            "diagnosis_ids": ["DIAG_CONTENT"], "target_breadth_cell_id": "CONTENT",
            "evidence_refs": ["EVIDENCE_2"],
            "action_payload": {"needed_items": 3},
            "activation_state": "CANDIDATE_ONLY_NOT_ACTIVE",
            "gate": {"decision": "APPROVE_AS_CANDIDATE"},
        },
        {
            "recommendation_id": "REC_REMED", "type": "REMEDIATION_CANDIDATE",
            "diagnosis_ids": ["DIAG_REMED"], "target_breadth_cell_id": "EVIDENCE",
            "evidence_refs": ["EVIDENCE_3"],
            "action_payload": {"strategy": "GUIDED_REBUILD"},
            "activation_state": "CANDIDATE_ONLY_NOT_ACTIVE",
            "gate": {"decision": "APPROVE_AS_CANDIDATE"},
        },
    ]
    r6_queue_core = {
        "task_id": r6.TASK_ID, "schema_version": r6.QUEUE_SCHEMA_VERSION,
        "validation_status": r6.STATUS, "private_local_only": True,
        "source_bindings": queue_bindings,
        "candidate_count": len(r6_candidates), "candidates": r6_candidates,
        "activation_contract": {
            "active_policy_written": False, "planner_mutated": False,
            "mastery_written": False, "canonical_authority_written": False,
            "practice_bank_written": False, "separate_downstream_promotion_required": True,
        },
        "next_short_step": r6.NEXT_SHORT_STEP,
    }
    r6_queue = {**r6_queue_core, "queue_sha256": r7.digest(r6_queue_core)}
    r6_report_core = {
        "task_id": r6.TASK_ID, "schema_version": r6.REPORT_SCHEMA_VERSION,
        "validation_status": r6.STATUS, "source_bindings": queue_bindings,
        "counts": {
            "diagnosis_count": 3, "recommendation_count": 3, "candidate_count": 3,
            "decision_counts": {"APPROVE_AS_CANDIDATE": 3},
            "recommendation_type_counts": {
                "COLLECTOR_GAP_CANDIDATE": 1, "CONTENT_GAP_CANDIDATE": 1,
                "REMEDIATION_CANDIDATE": 1,
            },
        },
        "decisions": [], "candidate_ids": [row["recommendation_id"] for row in r6_candidates],
        "claim_boundaries": {
            "raw_response_included": False, "diagnostic_explanation_included": False,
            "action_payload_included": False, "reviewer_identity_included": False,
            "mastery_written": False, "canonical_written": False,
            "practice_bank_written": False, "active_policy_written": False,
            "a2_unlocked": False,
        },
        "next_short_step": r6.NEXT_SHORT_STEP,
    }
    r6_report = {**r6_report_core, "report_sha256": r7.digest(r6_report_core)}

    explicit_rows = [{
        "finding_id": "EXPLICIT_UI_BUG",
        "finding_type": "UI_SERIALIZATION_BUG", "severity": "P0",
        "source_refs": ["R5_LOCAL_UI"], "evidence_refs": ["ATTEMPT_HASH"],
        "breadth_cell_id": "EVIDENCE", "summary_code": "TOKEN_ARRAY_SERIALIZED_AS_TEXT",
        "detail": {"response_mode": "ordered_tokens"}, "reproducible": True,
        "source_sha256": "b" * 64,
    }]
    explicit = r7.explicit_finding_registry(explicit_rows)

    return {
        "r3": _write(tmp_path / "r3.json", r3_value),
        "r4": _write(tmp_path / "r4.json", r4_value),
        "r5": _write(tmp_path / "r5.json", r5_value),
        "r6_queue": _write(tmp_path / "r6_queue.json", r6_queue),
        "r6_report": _write(tmp_path / "r6_report.json", r6_report),
        "explicit": _write(tmp_path / "explicit.json", explicit),
    }


def _build(tmp_path: Path):
    sources = _sources(tmp_path)
    queue, report = r7.build_queue(
        r3_path=sources["r3"], r4_path=sources["r4"], r5_path=sources["r5"],
        r6_queue_path=sources["r6_queue"], r6_report_path=sources["r6_report"],
        explicit_findings_path=sources["explicit"],
    )
    return sources, queue, report


def _result(work, *, result_state="PASS", changed_paths=None, ci_conclusion="success", gate_value=True):
    changed_paths = changed_paths if changed_paths is not None else (
        ["ulga/builders/build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector.py",
         "tests/ulga/test_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector.py"]
        if work["route"] == "CODE_FULLFIX" else []
    )
    gates = {key: gate_value for key in work["required_gates"]}
    replay_status = "PASS" if work["replay_contract"]["required"] else "NOT_REQUIRED"
    return {
        "work_item_id": work["work_item_id"], "result_state": result_state,
        "completed_at": "2026-07-19T12:00:00+08:00", "actor_id": "codex-or-operator",
        "commit_sha": "c" * 40 if work["route"] == "CODE_FULLFIX" else None,
        "changed_paths": changed_paths, "gate_results": gates,
        "ci": {"run_id": 12345, "conclusion": ci_conclusion, "test_commands": ["pytest focused", "pytest regression"]},
        "replay": {
            "status": replay_status, "source_hashes": list(work["source_hashes"]),
            "preserved_raw_evidence": True, "rebuilt_outputs": list(work["replay_contract"]["rebuild_required"]),
        },
        "output_hashes": {"result": "d" * 64}, "notes": "Scoped closure result.",
    }


def test_build_routes_all_gap_classes_and_ignores_deferred_media(tmp_path: Path) -> None:
    _, queue, report = _build(tmp_path)
    routes = {row["route"] for row in queue["work_items"]}
    types = {row["finding_type"] for row in queue["work_items"]}
    assert routes == {"CODE_FULLFIX", "CONTENT_EXPANSION", "PLANNER_REDEPLOY", "AUTHORITY_REVIEW"}
    assert "UI_SERIALIZATION_BUG" in types
    assert "EVIDENCE_FIELD_MISSING" in types
    assert "CONTENT_CAPACITY_INSUFFICIENT" in types
    assert "PEDAGOGICAL_EVIDENCE_INSUFFICIENT" in types
    assert "COVERAGE_REQUIREMENT_GAP" in types
    assert "AUTHORITY_DECISION_REQUIRED" in types
    assert all(row["breadth_cell_id"] != "MEDIA" for row in queue["work_items"])
    assert queue["claim_boundaries"]["gpt_candidate_executed_directly"] is False
    assert queue["claim_boundaries"]["code_modified"] is False
    assert all(row["work_state"] == "OPEN" for row in queue["work_items"])
    r7.safe_scan(report)


def test_build_exact_rebuild_validator_and_source_tamper_detection(tmp_path: Path) -> None:
    sources, queue, report = _build(tmp_path)
    queue_path = _write(tmp_path / "queue.json", queue)
    report_path = _write(tmp_path / "report.json", report)
    valid = validator.validate_build(
        r3_path=sources["r3"], r4_path=sources["r4"], r5_path=sources["r5"],
        r6_queue_path=sources["r6_queue"], r6_report_path=sources["r6_report"],
        explicit_findings_path=sources["explicit"], queue_path=queue_path, report_path=report_path,
    )
    assert valid["error_count"] == 0, valid["errors"]
    tampered = json.loads(sources["r4"].read_text())
    tampered["counts"]["approved_item_count"] = 999
    sources["r4"].write_text(json.dumps(tampered), encoding="utf-8")
    invalid = validator.validate_build(
        r3_path=sources["r3"], r4_path=sources["r4"], r5_path=sources["r5"],
        r6_queue_path=sources["r6_queue"], r6_report_path=sources["r6_report"],
        explicit_findings_path=sources["explicit"], queue_path=queue_path, report_path=report_path,
    )
    assert invalid["error_count"] > 0


def test_code_fullfix_closes_only_with_allowed_paths_ci_and_replay(tmp_path: Path) -> None:
    _, queue, _ = _build(tmp_path)
    work = next(row for row in queue["work_items"] if row["finding_type"] == "UI_SERIALIZATION_BUG")
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=[_result(work)])
    closed, report = r7.apply_results(queue=queue, registry=registry)
    closed_work = next(row for row in closed["work_items"] if row["work_item_id"] == work["work_item_id"])
    assert closed_work["work_state"] == "CLOSED"
    assert closed_work["closure"]["result_state"] == "PASS"
    assert closed["counts"]["closed_count"] == 1
    assert closed["claim_boundaries"]["code_modified"] is False
    r7.safe_scan(report)


def test_forbidden_or_out_of_scope_code_path_fails_closed(tmp_path: Path) -> None:
    _, queue, _ = _build(tmp_path)
    work = next(row for row in queue["work_items"] if row["finding_type"] == "UI_SERIALIZATION_BUG")
    result = _result(work, changed_paths=["ulga/graph/canonical_graph.json"])
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=[result])
    with pytest.raises(r7.RepairLoopError, match="forbidden_path_changed"):
        r7.apply_results(queue=queue, registry=registry)
    result = _result(work, changed_paths=["ulga/builders/unrelated_system.py"])
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=[result])
    with pytest.raises(r7.RepairLoopError, match="path_outside_allowed_scope"):
        r7.apply_results(queue=queue, registry=registry)


def test_pass_result_requires_every_gate_ci_and_replay(tmp_path: Path) -> None:
    _, queue, _ = _build(tmp_path)
    work = next(row for row in queue["work_items"] if row["finding_type"] == "COLLECTOR_BUG") if any(row["finding_type"] == "COLLECTOR_BUG" for row in queue["work_items"]) else next(row for row in queue["work_items"] if row["route"] == "CODE_FULLFIX")
    result = _result(work, gate_value=False)
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=[result])
    with pytest.raises(r7.RepairLoopError, match="pass_result_gate_not_all_true"):
        r7.apply_results(queue=queue, registry=registry)
    result = _result(work, ci_conclusion="failure")
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=[result])
    with pytest.raises(r7.RepairLoopError, match="pass_code_fullfix_ci_not_success"):
        r7.apply_results(queue=queue, registry=registry)
    result = _result(work)
    result["replay"]["status"] = "FAIL"
    result["gate_results"]["MIGRATION_REPLAY_PASS"] = False
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=[result])
    with pytest.raises(r7.RepairLoopError, match="pass_result"):
        r7.apply_results(queue=queue, registry=registry)


def test_planner_redeploy_and_authority_review_can_close_without_code_commit(tmp_path: Path) -> None:
    _, queue, _ = _build(tmp_path)
    planner = next(row for row in queue["work_items"] if row["route"] == "PLANNER_REDEPLOY")
    authority = next(row for row in queue["work_items"] if row["route"] == "AUTHORITY_REVIEW")
    results = [_result(planner, ci_conclusion="skipped"), _result(authority, ci_conclusion="skipped")]
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=results)
    closed, _ = r7.apply_results(queue=queue, registry=registry)
    states = {row["work_item_id"]: row["work_state"] for row in closed["work_items"]}
    assert states[planner["work_item_id"]] == "CLOSED"
    assert states[authority["work_item_id"]] == "CLOSED"
    assert all(result["commit_sha"] is None for result in results)


def test_closure_exact_rebuild_validator_and_registry_hash_binding(tmp_path: Path) -> None:
    _, queue, _ = _build(tmp_path)
    work = next(row for row in queue["work_items"] if row["route"] == "CONTENT_EXPANSION")
    registry = r7.result_registry(queue_sha256=queue["queue_sha256"], results=[_result(work, ci_conclusion="success")])
    closed, report = r7.apply_results(queue=queue, registry=registry)
    queue_path = _write(tmp_path / "source.queue.json", queue)
    registry_path = _write(tmp_path / "results.json", registry)
    closed_path = _write(tmp_path / "closed.queue.json", closed)
    report_path = _write(tmp_path / "closed.report.json", report)
    valid = validator.validate_closure(
        queue_path=queue_path, results_path=registry_path,
        closed_queue_path=closed_path, report_path=report_path,
    )
    assert valid["error_count"] == 0, valid["errors"]
    registry["queue_sha256"] = "0" * 64
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    invalid = validator.validate_closure(
        queue_path=queue_path, results_path=registry_path,
        closed_queue_path=closed_path, report_path=report_path,
    )
    assert invalid["error_count"] > 0
