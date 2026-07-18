from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment
from ulga.validators import validate_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as validator


CELL_ID = "BREADTH_CELL_ASK_LOCATION_TRAVEL"


def _write(path: Path, value) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _sources(tmp_path: Path, *, cell_status: str = "CONTENT_MISSING"):
    ontology = r2.build_ontology()
    ontology_path = _write(tmp_path / "ontology.json", ontology)
    cell = {
        "cell_id": CELL_ID,
        "capability_node_id": "REF:SPEAKING:ASK_LOCATION",
        "capability_id": "CAP_ASK_LOCATION",
        "obligation_id": "BREADTH_OBLIGATION_ASK_LOCATION_TRAVEL",
        "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
        "domain": "TRAVEL_TRANSPORT",
        "status": cell_status,
        "dimension_coverage": {
            "skills": {"required": ["SPEAKING"], "observed": [], "missing": ["SPEAKING"]},
            "support_levels": {"required": ["S1_KEYWORD_OR_VISUAL"], "observed": [], "missing": ["S1_KEYWORD_OR_VISUAL"]},
            "initiative_levels": {"required": ["GUIDED_INITIATION"], "observed": [], "missing": ["GUIDED_INITIATION"]},
            "variation_types": {"required": ["EXPECTED_SCRIPT"], "observed": [], "missing": ["EXPECTED_SCRIPT"]},
            "transfer_distances": {"required": ["NONE"], "observed": [], "missing": ["NONE"]},
            "evidence_levels": {"required": ["E2_CONTROLLED_PRODUCTION"], "observed": [], "missing": ["E2_CONTROLLED_PRODUCTION"]},
            "retention_stages": {"required": ["NOT_SCHEDULED"], "observed": [], "missing": ["NOT_SCHEDULED"]},
        },
        "matching_deployment_ids": [],
        "source_refs": ["CONTEXT_TRAVEL_TRANSPORT"],
        "next_actions": ["POPULATE_CONTEXT_AND_LIFE_TASK_CONTENT"],
    }
    coverage_core = {
        "task_id": r3.TASK_ID,
        "schema_version": r3.SCHEMA_VERSION,
        "validation_status": r3.STATUS,
        "source_bindings": {
            "ontology_sha256": ontology["ontology_sha256"],
            "graph_sha256": "a" * 64,
            "profiles_sha256": "b" * 64,
            "deployments_sha256": "c" * 64,
            "m10_structural_coverage": None,
        },
        "counts": {
            "required_mastery_node_count": 2,
            "required_capability_node_count": 1,
            "profile_defined_count": 1,
            "profile_missing_count": 0,
            "denominator_cell_count": 1,
            "deployment_contract_count": 0,
            "gap_count": 1,
            "status_counts": {status: int(status == cell_status) for status in r3.CELL_STATUSES},
        },
        "coverage_metrics": {
            "structural_ready_count": 0,
            "structural_ready_percent": 0.0,
            "retention_complete_count": 0,
            "retention_complete_percent": 0.0,
            "false_100_percent_blocked": True,
            "completion_denominator_source": "EXPLICIT_BREADTH_REQUIREMENT_CELLS_PLUS_PROFILE_PLACEHOLDERS",
        },
        "profile_missing_capability_node_ids": [],
        "cells": [cell],
        "ranked_gaps": [{
            "rank": 1,
            "cell_id": CELL_ID,
            "capability_node_id": "REF:SPEAKING:ASK_LOCATION",
            "capability_id": "CAP_ASK_LOCATION",
            "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
            "domain": "TRAVEL_TRANSPORT",
            "status": cell_status,
            "next_actions": cell["next_actions"],
        }],
        "claim_boundaries": {
            "m1_graph_modified": False,
            "m10_structural_coverage_replaced": False,
            "cartesian_product_generated": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
            "retention_claimed_from_structure": False,
            "audio_completion_required": False,
        },
        "next_short_step": r3.NEXT_SHORT_STEP,
    }
    coverage = {**coverage_core, "report_sha256": r3.digest(coverage_core)}
    coverage_path = _write(tmp_path / "coverage.json", coverage)
    return ontology, ontology_path, coverage, coverage_path


def _candidate(
    item_id: str,
    *,
    prompt: str,
    template_family: str,
    review_status: str = "APPROVED",
    level: str = "A1",
    media_state: str = "AVAILABLE",
    validator_status: str = "PASS",
):
    learner = {
        "prompt": prompt,
        "response_mode": "select_one",
        "options": ["It is next to the bank.", "It is eight o'clock.", "It is blue."],
    }
    scoring = {
        "scoring_mode": "EXACT_OPTION",
        "response_type": "string",
        "accepted_texts": ["It is next to the bank."],
        "human_review_fallback": False,
    }
    candidate = {
        "item_id": item_id,
        "breadth_cell_id": CELL_ID,
        "capability_id": "CAP_ASK_LOCATION",
        "life_task_id": "LIFE_TASK_FIND_BUS_STOP",
        "domain": "TRAVEL_TRANSPORT",
        "level": level,
        "skill": "SPEAKING",
        "purpose": "CORE_PRACTICE",
        "task_type": "SELECT_ONE",
        "support_level": "S1_KEYWORD_OR_VISUAL",
        "initiative_level": "GUIDED_INITIATION",
        "interaction_variation": "EXPECTED_SCRIPT",
        "transfer_distance": "NONE",
        "template_family": template_family,
        "stimulus_fingerprint": assessment._contract_fingerprint(learner),
        "media_payload_state": media_state,
        "source_refs": [f"SOURCE_{item_id}"],
        "authority_refs": ["AUTHORITY_ASK_LOCATION_A1"],
        "provenance": "PROJECT_AUTHORED_CANDIDATE",
        "learner_contract": learner,
        "private_scoring_contract": scoring,
        "validator_status": validator_status,
    }
    candidate_sha = r4.candidate_digest(candidate)
    candidate["candidate_sha256"] = candidate_sha
    candidate["authority_review"] = {
        "status": review_status,
        "reviewer_id": "authority-reviewer" if review_status == "APPROVED" else None,
        "reviewed_at": "2026-07-19T00:00:00+08:00" if review_status == "APPROVED" else None,
        "criteria": {
            "a1_a1plus_level_fit": review_status == "APPROVED",
            "breadth_cell_fit": review_status == "APPROVED",
            "learner_stimulus_complete": review_status == "APPROVED",
            "answer_or_rubric_valid": review_status == "APPROVED",
            "semantic_unambiguous": review_status == "APPROVED",
            "source_trace_complete": review_status == "APPROVED",
        },
        "candidate_sha256": candidate_sha,
    }
    return candidate


def _policy(min_items: int = 2, min_stimuli: int = 2, min_templates: int = 2):
    return {
        "breadth_cell_id": CELL_ID,
        "purposes": {
            "CORE_PRACTICE": {
                "min_approved_items": min_items,
                "min_unique_stimuli": min_stimuli,
                "min_template_families": min_templates,
            }
        },
        "max_recent_reuse": 0,
        "required_skill_projection": ["SPEAKING"],
        "policy_source_refs": ["BREADTH_OBLIGATION_ASK_LOCATION_TRAVEL"],
    }


def _registries(tmp_path: Path, ontology, coverage, candidates, policies):
    candidate_registry = r4.candidate_registry(
        ontology["ontology_sha256"], coverage["report_sha256"], candidates
    )
    policy_registry = r4.capacity_policy_registry(coverage["report_sha256"], policies)
    return (
        _write(tmp_path / "candidates.json", candidate_registry),
        _write(tmp_path / "policies.json", policy_registry),
    )


def test_two_unique_reviewed_items_form_ready_private_bank(tmp_path: Path) -> None:
    ontology, ontology_path, coverage, coverage_path = _sources(tmp_path)
    candidates = [
        _candidate("ITEM_1", prompt="Where is the bus stop?", template_family="TEMPLATE_LOCATION_CHOICE_A"),
        _candidate("ITEM_2", prompt="Where can I find the bus stop?", template_family="TEMPLATE_LOCATION_CHOICE_B"),
    ]
    candidate_path, policy_path = _registries(tmp_path, ontology, coverage, candidates, [_policy()])
    bank, report = r4.build(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
    )
    assert bank["item_count"] == 2
    assert all(row["admission"]["status"] == "APPROVED" for row in bank["items"])
    cell = report["cell_supply"][0]
    assert cell["supply_status"] == "READY_FOR_LOCAL_SELECTION"
    assert cell["purpose_capacity"]["CORE_PRACTICE"]["capacity_pass"] is True
    assert cell["skill_projection"]["missing"] == []
    assert bank["selection_contract"]["local_free_generation_enabled"] is False
    assert report["claim_boundaries"]["gpt_direct_admission_enabled"] is False
    r4.safe_scan(report)


def test_duplicate_learner_stimulus_is_rejected_and_capacity_shortage_remains_visible(tmp_path: Path) -> None:
    ontology, ontology_path, coverage, coverage_path = _sources(tmp_path)
    first = _candidate("ITEM_1", prompt="Where is the bus stop?", template_family="TEMPLATE_LOCATION_CHOICE_A")
    duplicate = _candidate("ITEM_2", prompt="Where is the bus stop?", template_family="TEMPLATE_LOCATION_CHOICE_B")
    candidate_path, policy_path = _registries(tmp_path, ontology, coverage, [first, duplicate], [_policy()])
    bank, report = r4.build(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
    )
    assert bank["item_count"] == 1
    assert {row["status"] for row in report["admission_decisions"]} == {
        "APPROVED", "DUPLICATE_LEARNER_STIMULUS"
    }
    assert report["cell_supply"][0]["supply_status"] == "CAPACITY_INSUFFICIENT"


def test_pending_authority_review_never_enters_formal_bank(tmp_path: Path) -> None:
    ontology, ontology_path, coverage, coverage_path = _sources(tmp_path)
    pending = _candidate(
        "ITEM_PENDING",
        prompt="Where is the station?",
        template_family="TEMPLATE_LOCATION_PENDING",
        review_status="PENDING",
    )
    candidate_path, policy_path = _registries(
        tmp_path, ontology, coverage, [pending], [_policy(1, 1, 1)]
    )
    bank, report = r4.build(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
    )
    assert bank["item_count"] == 0
    assert report["admission_decisions"][0]["status"] == "AUTHORITY_REVIEW_REQUIRED"
    assert report["cell_supply"][0]["supply_status"] == "HUMAN_REVIEW_REQUIRED"


def test_a2_and_validator_failed_candidates_are_fail_closed(tmp_path: Path) -> None:
    ontology, ontology_path, coverage, coverage_path = _sources(tmp_path)
    a2 = _candidate(
        "ITEM_A2", prompt="Where is the station?", template_family="TEMPLATE_A2", level="A2"
    )
    invalid = _candidate(
        "ITEM_INVALID", prompt="Where is the station?", template_family="TEMPLATE_INVALID",
        validator_status="FAIL",
    )
    candidate_path, policy_path = _registries(
        tmp_path, ontology, coverage, [a2, invalid], [_policy(1, 1, 1)]
    )
    bank, report = r4.build(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
    )
    assert bank["item_count"] == 0
    assert {row["status"] for row in report["admission_decisions"]} == {
        "A2_OUT_OF_SCOPE", "VALIDATOR_NOT_PASS"
    }
    assert report["claim_boundaries"]["a2_content_admitted"] is False


def test_media_defer_preserves_supply_contract_without_audio_completion_claim(tmp_path: Path) -> None:
    ontology, ontology_path, coverage, coverage_path = _sources(
        tmp_path, cell_status="DEFERRED_MEDIA"
    )
    deferred = _candidate(
        "ITEM_MEDIA",
        prompt="Where is the bus stop?",
        template_family="TEMPLATE_LOCATION_MEDIA",
        media_state="DEFERRED_MEDIA_PAYLOAD",
    )
    candidate_path, policy_path = _registries(
        tmp_path, ontology, coverage, [deferred], [_policy(1, 1, 1)]
    )
    bank, report = r4.build(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
    )
    assert bank["item_count"] == 1
    assert report["cell_supply"][0]["supply_status"] == "MEDIA_DEFERRED"
    assert report["claim_boundaries"]["audio_files_required"] is False


def test_missing_policy_is_explicit_and_validator_detects_bank_tampering(tmp_path: Path) -> None:
    ontology, ontology_path, coverage, coverage_path = _sources(tmp_path)
    candidate_path, policy_path = _registries(tmp_path, ontology, coverage, [], [])
    bank, report = r4.build(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
    )
    assert report["cell_supply"][0]["supply_status"] == "CAPACITY_POLICY_MISSING"
    bank_path = _write(tmp_path / "bank.json", bank)
    report_path = _write(tmp_path / "report.json", report)
    valid = validator.validate(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
        bank_path=bank_path,
        report_path=report_path,
    )
    assert valid["error_count"] == 0, valid["errors"]
    tampered = deepcopy(report)
    tampered["claim_boundaries"]["local_free_generation_enabled"] = True
    report_path.write_text(json.dumps(tampered), encoding="utf-8")
    invalid = validator.validate(
        ontology_path=ontology_path,
        coverage_path=coverage_path,
        candidates_path=candidate_path,
        policies_path=policy_path,
        bank_path=bank_path,
        report_path=report_path,
    )
    assert invalid["error_count"] > 0
