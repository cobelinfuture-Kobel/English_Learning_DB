#!/usr/bin/env python3
"""Build a private Approved PracticeBank from breadth-bound, validated candidates.

Task: A1FS-V1-R4_CentralQuestionSupplySkillProjectionAndCapacityGovernance

This module does not generate learner items. It admits existing or project-authored
candidates only after exact R3 breadth-cell binding, learner-contract validation,
hash-bound Authority review, stimulus/template deduplication, and explicit capacity
policy checks. The private bank contains prompts and scoring contracts; the safe
report never does.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment
from ulga.validators import validate_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2_validator

TASK_ID = "A1FS-V1-R4_CentralQuestionSupplySkillProjectionAndCapacityGovernance"
SCHEMA_VERSION = "a1fs.v1.r4.central_question_supply.v1"
CANDIDATE_SCHEMA_VERSION = "a1fs.v1.r4.question_candidate_registry.v1"
POLICY_SCHEMA_VERSION = "a1fs.v1.r4.capacity_policy_registry.v1"
BANK_SCHEMA_VERSION = "a1fs.v1.r4.approved_practice_bank.v1"
STATUS = "PASS_A1FS_V1_R4_CENTRAL_QUESTION_SUPPLY_CAPACITY_GOVERNANCE"
NEXT_SHORT_STEP = "A1FS-V1-R5_LocalEdgeRuntimeAndCompleteEvidenceCollector"

PURPOSES = (
    "CORE_PRACTICE", "REMEDIATION", "REASSESSMENT", "TRANSFER", "RETENTION",
)
PROVENANCE = {"EXISTING_AUTHORITY_REVIEWED", "PROJECT_AUTHORED_CANDIDATE"}
AUTHORITY_REVIEW_STATUS = {"APPROVED", "PENDING", "REJECTED"}
ADMISSION_STATUS = {
    "APPROVED", "AUTHORITY_REVIEW_REQUIRED", "AUTHORITY_REJECTED",
    "BREADTH_BINDING_INVALID", "LEARNER_CONTRACT_INVALID", "SCORING_CONTRACT_INVALID",
    "DUPLICATE_LEARNER_STIMULUS", "DUPLICATE_STIMULUS_FINGERPRINT",
    "DUPLICATE_ITEM_ID", "A2_OUT_OF_SCOPE", "VALIDATOR_NOT_PASS",
    "STIMULUS_DEPENDENCY_UNDECLARED", "REQUIRED_STIMULUS_MISSING",
    "STIMULUS_PAYLOAD_INVALID", "PROMPT_DEPENDENCY_CONTRACT_MISMATCH",
    "RENDERER_CAPABILITY_MISSING", "LEARNER_SERIALIZATION_LOSS",
    "ANSWERABILITY_FAILED", "MEDIA_PAYLOAD_DEFERRED",
}
CELL_SUPPLY_STATUS = (
    "CAPACITY_POLICY_MISSING", "CONTENT_MISSING", "VALIDATOR_FAILED",
    "HUMAN_REVIEW_REQUIRED", "CAPACITY_INSUFFICIENT", "READY_FOR_LOCAL_SELECTION",
    "MEDIA_DEFERRED", "BREADTH_PROFILE_REQUIRED",
)
ALLOWED_SCORING_MODES = {"EXACT_OPTION", "EXACT_SEQUENCE", "NORMALIZED_TEXT", "FEATURE_RUBRIC"}
PRIVATE_KEYS = {
    "prompt", "context", "options", "supplied_tokens", "supplied_morphemes",
    "gap_display_tokens", "word_bank", "accepted_texts", "accepted_sequence",
    "model_text", "model_texts", "rubric", "private_scoring_contract", "learner_contract",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class QuestionSupplyError(ValueError):
    """Fail-closed central question supply error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuestionSupplyError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise QuestionSupplyError(f"{code}_not_object")
    return value


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _timezone_timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuestionSupplyError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QuestionSupplyError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise QuestionSupplyError(code)
    return value


def _load_ontology(path: Path) -> dict[str, Any]:
    value = read_json(path, "ontology")
    errors = r2_validator.validate_ontology(value)
    if errors:
        raise QuestionSupplyError("ontology_invalid:" + "|".join(errors))
    return value


def _load_coverage(path: Path, ontology_sha256: str) -> dict[str, Any]:
    value = read_json(path, "coverage")
    if value.get("task_id") != r3.TASK_ID or value.get("schema_version") != r3.SCHEMA_VERSION:
        raise QuestionSupplyError("coverage_identity_invalid")
    if value.get("validation_status") != r3.STATUS:
        raise QuestionSupplyError("coverage_status_invalid")
    if value.get("source_bindings", {}).get("ontology_sha256") != ontology_sha256:
        raise QuestionSupplyError("coverage_ontology_binding_mismatch")
    core = {key: child for key, child in value.items() if key != "report_sha256"}
    if value.get("report_sha256") != r3.digest(core):
        raise QuestionSupplyError("coverage_digest_invalid")
    return value


def candidate_core(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in candidate.items()
        if key not in {"authority_review", "candidate_sha256", "admission"}
    }


def candidate_digest(candidate: Mapping[str, Any]) -> str:
    return digest(candidate_core(candidate))


def candidate_registry(ontology_sha256: str, coverage_sha256: str, candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in candidates]
    return {
        "task_id": TASK_ID,
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "ontology_sha256": ontology_sha256,
        "coverage_sha256": coverage_sha256,
        "candidates": rows,
        "candidates_sha256": digest(rows),
    }


def capacity_policy_registry(coverage_sha256: str, policies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in policies]
    return {
        "task_id": TASK_ID,
        "schema_version": POLICY_SCHEMA_VERSION,
        "coverage_sha256": coverage_sha256,
        "policies": rows,
        "policies_sha256": digest(rows),
    }


def _load_candidates(path: Path, *, ontology_sha256: str, coverage_sha256: str) -> list[dict[str, Any]]:
    registry = read_json(path, "candidate_registry")
    if registry.get("task_id") != TASK_ID or registry.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        raise QuestionSupplyError("candidate_registry_identity_invalid")
    if registry.get("ontology_sha256") != ontology_sha256:
        raise QuestionSupplyError("candidate_registry_ontology_binding_mismatch")
    if registry.get("coverage_sha256") != coverage_sha256:
        raise QuestionSupplyError("candidate_registry_coverage_binding_mismatch")
    rows = registry.get("candidates")
    if not isinstance(rows, list) or registry.get("candidates_sha256") != digest(rows):
        raise QuestionSupplyError("candidate_registry_digest_invalid")
    return [deepcopy(dict(row)) for row in rows if isinstance(row, Mapping)]


def _validate_policy(row: Mapping[str, Any], cell_ids: set[str]) -> dict[str, Any]:
    required = {"breadth_cell_id", "purposes", "max_recent_reuse", "required_skill_projection", "policy_source_refs"}
    if set(row) != required:
        raise QuestionSupplyError("capacity_policy_shape_invalid")
    cell_id = str(row["breadth_cell_id"])
    if cell_id not in cell_ids:
        raise QuestionSupplyError(f"capacity_policy_unknown_cell:{cell_id}")
    purposes = row["purposes"]
    if not isinstance(purposes, Mapping) or not purposes:
        raise QuestionSupplyError(f"capacity_policy_purposes_invalid:{cell_id}")
    normalized: dict[str, Any] = {}
    for purpose, contract in purposes.items():
        if purpose not in PURPOSES or not isinstance(contract, Mapping):
            raise QuestionSupplyError(f"capacity_policy_purpose_invalid:{cell_id}:{purpose}")
        expected = {"min_approved_items", "min_unique_stimuli", "min_template_families"}
        if set(contract) != expected:
            raise QuestionSupplyError(f"capacity_policy_contract_shape_invalid:{cell_id}:{purpose}")
        values = {key: int(contract[key]) for key in expected}
        if any(value < 1 for value in values.values()):
            raise QuestionSupplyError(f"capacity_policy_threshold_invalid:{cell_id}:{purpose}")
        if values["min_unique_stimuli"] > values["min_approved_items"]:
            raise QuestionSupplyError(f"capacity_policy_stimulus_threshold_invalid:{cell_id}:{purpose}")
        if values["min_template_families"] > values["min_approved_items"]:
            raise QuestionSupplyError(f"capacity_policy_template_threshold_invalid:{cell_id}:{purpose}")
        normalized[purpose] = values
    max_recent_reuse = int(row["max_recent_reuse"])
    if max_recent_reuse < 0:
        raise QuestionSupplyError(f"capacity_policy_recent_reuse_invalid:{cell_id}")
    skills = row["required_skill_projection"]
    if not isinstance(skills, list) or not skills or len(skills) != len(set(skills)):
        raise QuestionSupplyError(f"capacity_policy_skill_projection_invalid:{cell_id}")
    if set(skills) - set(r2.ENUMS["skills"]):
        raise QuestionSupplyError(f"capacity_policy_skill_out_of_scope:{cell_id}")
    refs = row["policy_source_refs"]
    if not isinstance(refs, list) or not refs:
        raise QuestionSupplyError(f"capacity_policy_source_refs_missing:{cell_id}")
    return {
        "breadth_cell_id": cell_id,
        "purposes": normalized,
        "max_recent_reuse": max_recent_reuse,
        "required_skill_projection": list(skills),
        "policy_source_refs": list(refs),
    }


def _load_policies(path: Path, *, coverage_sha256: str, cell_ids: set[str]) -> dict[str, dict[str, Any]]:
    registry = read_json(path, "capacity_policy_registry")
    if registry.get("task_id") != TASK_ID or registry.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise QuestionSupplyError("capacity_policy_registry_identity_invalid")
    if registry.get("coverage_sha256") != coverage_sha256:
        raise QuestionSupplyError("capacity_policy_registry_coverage_binding_mismatch")
    rows = registry.get("policies")
    if not isinstance(rows, list) or registry.get("policies_sha256") != digest(rows):
        raise QuestionSupplyError("capacity_policy_registry_digest_invalid")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise QuestionSupplyError("capacity_policy_not_object")
        normalized = _validate_policy(row, cell_ids)
        cell_id = normalized["breadth_cell_id"]
        if cell_id in result:
            raise QuestionSupplyError(f"capacity_policy_duplicate:{cell_id}")
        result[cell_id] = normalized
    return result


def _cell_index(coverage: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in coverage.get("cells", []):
        if not isinstance(row, Mapping):
            raise QuestionSupplyError("coverage_cell_not_object")
        cell_id = str(row.get("cell_id") or "")
        if not cell_id or cell_id in result:
            raise QuestionSupplyError("coverage_cell_identity_invalid")
        result[cell_id] = dict(row)
    return result


def _review_state(candidate: Mapping[str, Any]) -> tuple[str, str | None]:
    review = candidate.get("authority_review")
    if not isinstance(review, Mapping):
        return "AUTHORITY_REVIEW_REQUIRED", "authority_review_missing"
    status = review.get("status")
    if status not in AUTHORITY_REVIEW_STATUS:
        return "AUTHORITY_REVIEW_REQUIRED", "authority_review_status_invalid"
    if status == "PENDING":
        return "AUTHORITY_REVIEW_REQUIRED", "authority_review_pending"
    if status == "REJECTED":
        return "AUTHORITY_REJECTED", "authority_review_rejected"
    reviewer = str(review.get("reviewer_id") or "").strip()
    if not reviewer:
        return "AUTHORITY_REVIEW_REQUIRED", "authority_reviewer_missing"
    try:
        _timezone_timestamp(review.get("reviewed_at"), "authority_review_timestamp_invalid")
    except QuestionSupplyError as exc:
        return "AUTHORITY_REVIEW_REQUIRED", str(exc)
    criteria = review.get("criteria")
    required_criteria = {
        "a1_a1plus_level_fit", "breadth_cell_fit", "learner_stimulus_complete",
        "answer_or_rubric_valid", "semantic_unambiguous", "source_trace_complete",
    }
    if not isinstance(criteria, Mapping) or set(criteria) != required_criteria or not all(criteria.values()):
        return "AUTHORITY_REVIEW_REQUIRED", "authority_review_criteria_invalid"
    if review.get("candidate_sha256") != candidate_digest(candidate):
        return "AUTHORITY_REVIEW_REQUIRED", "authority_review_candidate_hash_mismatch"
    return "APPROVED", None


def _scoring_valid(scoring: Mapping[str, Any]) -> str | None:
    mode = scoring.get("scoring_mode")
    response_type = scoring.get("response_type")
    if mode not in ALLOWED_SCORING_MODES:
        return "scoring_mode_invalid"
    if response_type not in {"string", "string_array"}:
        return "scoring_response_type_invalid"
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        accepted = scoring.get("accepted_texts")
        if not isinstance(accepted, list) or not accepted or not all(isinstance(row, str) and row.strip() for row in accepted):
            return "scoring_accepted_texts_missing"
    elif mode == "EXACT_SEQUENCE":
        accepted = scoring.get("accepted_sequence")
        if not isinstance(accepted, list) or len(accepted) < 2 or not all(isinstance(row, str) and row.strip() for row in accepted):
            return "scoring_accepted_sequence_missing"
    else:
        rubric = scoring.get("rubric")
        if not isinstance(rubric, Mapping) or not rubric or scoring.get("human_review_fallback") is not True:
            return "feature_rubric_contract_invalid"
    return None


def _breadth_binding_error(candidate: Mapping[str, Any], cell: Mapping[str, Any], policy: Mapping[str, Any] | None) -> str | None:
    if cell.get("status") == "PROFILE_DEFINITION_REQUIRED":
        return "breadth_profile_required"
    if candidate.get("capability_id") != cell.get("capability_id"):
        return "capability_id_mismatch"
    if candidate.get("life_task_id") != cell.get("life_task_id"):
        return "life_task_id_mismatch"
    if candidate.get("domain") != cell.get("domain"):
        return "domain_mismatch"
    if candidate.get("level") not in {"A1", "A1_PLUS"}:
        return "level_out_of_scope"
    enum_fields = {
        "skill": "skills", "task_type": "task_types", "support_level": "support_levels",
        "initiative_level": "initiative_levels", "interaction_variation": "interaction_variations",
        "transfer_distance": "transfer_distances",
    }
    for field, enum_name in enum_fields.items():
        if candidate.get(field) not in r2.ENUMS[enum_name]:
            return f"{field}_invalid"
    dimensions = cell.get("dimension_coverage", {})
    field_dimension = {
        "skill": "skills", "support_level": "support_levels",
        "initiative_level": "initiative_levels", "interaction_variation": "variation_types",
        "transfer_distance": "transfer_distances",
    }
    for field, dimension in field_dimension.items():
        required = dimensions.get(dimension, {}).get("required", [])
        if required and candidate.get(field) not in required:
            return f"{field}_outside_cell_requirement"
    if policy and candidate.get("skill") not in policy["required_skill_projection"]:
        return "skill_outside_capacity_policy_projection"
    return None


def _validate_candidate_shape(candidate: Mapping[str, Any]) -> str | None:
    required = {
        "item_id", "breadth_cell_id", "capability_id", "life_task_id", "domain", "level",
        "skill", "purpose", "task_type", "support_level", "initiative_level",
        "interaction_variation", "transfer_distance", "template_family",
        "stimulus_fingerprint", "media_payload_state", "source_refs", "authority_refs",
        "provenance", "learner_contract", "private_scoring_contract", "validator_status",
        "authority_review", "candidate_sha256",
    }
    if set(candidate) != required:
        return "candidate_shape_invalid"
    if not str(candidate.get("item_id") or "").strip():
        return "item_id_missing"
    if candidate.get("purpose") not in PURPOSES:
        return "purpose_invalid"
    if candidate.get("provenance") not in PROVENANCE:
        return "provenance_invalid"
    if candidate.get("validator_status") != "PASS":
        return "validator_not_pass"
    if not str(candidate.get("template_family") or "").startswith("TEMPLATE_"):
        return "template_family_invalid"
    fingerprint = candidate.get("stimulus_fingerprint")
    if not isinstance(fingerprint, str) or not HEX64.fullmatch(fingerprint):
        return "stimulus_fingerprint_invalid"
    if candidate.get("candidate_sha256") != candidate_digest(candidate):
        return "candidate_digest_invalid"
    if not isinstance(candidate.get("source_refs"), list) or not candidate["source_refs"]:
        return "source_refs_missing"
    if not isinstance(candidate.get("authority_refs"), list) or not candidate["authority_refs"]:
        return "authority_refs_missing"
    return None


def admit_candidates(
    *, candidates: Sequence[Mapping[str, Any]], cells: Mapping[str, Mapping[str, Any]],
    policies: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    approved: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    seen_learner_fingerprints: dict[str, set[str]] = defaultdict(set)
    seen_stimulus_fingerprints: dict[str, set[str]] = defaultdict(set)
    for raw in candidates:
        candidate = deepcopy(dict(raw))
        item_id = str(candidate.get("item_id") or "")
        cell_id = str(candidate.get("breadth_cell_id") or "")
        status, reason = "APPROVED", None
        shape_error = _validate_candidate_shape(candidate)
        if shape_error == "validator_not_pass":
            status, reason = "VALIDATOR_NOT_PASS", shape_error
        elif shape_error:
            status, reason = "SCORING_CONTRACT_INVALID", shape_error
        elif item_id in seen_item_ids:
            status, reason = "DUPLICATE_ITEM_ID", "duplicate_item_id"
        elif cell_id not in cells:
            status, reason = "BREADTH_BINDING_INVALID", "unknown_breadth_cell"
        elif candidate.get("level") not in {"A1", "A1_PLUS"}:
            status, reason = "A2_OUT_OF_SCOPE", "level_out_of_scope"
        else:
            binding = _breadth_binding_error(candidate, cells[cell_id], policies.get(cell_id))
            if binding:
                status, reason = "BREADTH_BINDING_INVALID", binding
        learner = candidate.get("learner_contract")
        scoring = candidate.get("private_scoring_contract")
        validated_learner: dict[str, Any] | None = None
        validated_scoring: dict[str, Any] | None = None
        learner_fingerprint: str | None = None
        if status == "APPROVED":
            if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
                status, reason = "LEARNER_CONTRACT_INVALID", "learner_or_scoring_contract_missing"
            else:
                scoring_error = _scoring_valid(scoring)
                if scoring_error:
                    status, reason = "SCORING_CONTRACT_INVALID", scoring_error
        if status == "APPROVED":
            try:
                validated_learner, validated_scoring = assessment.validate_learner_contract(
                    item_id=item_id,
                    task_type=str(candidate["task_type"]).casefold(),
                    learner=learner,
                    scoring=scoring,
                )
            except assessment.AssessmentValidityError as exc:
                status, reason = "LEARNER_CONTRACT_INVALID", str(exc).split(":", 1)[0]
            else:
                learner_fingerprint = assessment._contract_fingerprint(validated_learner)
                if candidate["stimulus_fingerprint"] != learner_fingerprint:
                    status, reason = "SCORING_CONTRACT_INVALID", "stimulus_fingerprint_mismatch"
        if status == "APPROVED":
            review_status, review_reason = _review_state(candidate)
            if review_status != "APPROVED":
                status, reason = review_status, review_reason
        if status == "APPROVED":
            if learner_fingerprint in seen_learner_fingerprints[cell_id]:
                status, reason = "DUPLICATE_LEARNER_STIMULUS", "duplicate_learner_stimulus"
            elif candidate["stimulus_fingerprint"] in seen_stimulus_fingerprints[cell_id]:
                status, reason = "DUPLICATE_STIMULUS_FINGERPRINT", "duplicate_stimulus_fingerprint"
        seen_item_ids.add(item_id)
        if status == "APPROVED":
            seen_learner_fingerprints[cell_id].add(str(learner_fingerprint))
            seen_stimulus_fingerprints[cell_id].add(candidate["stimulus_fingerprint"])
            admitted = deepcopy(candidate)
            admitted["learner_contract"] = validated_learner
            admitted["private_scoring_contract"] = validated_scoring
            admitted["admission"] = {
                "status": "APPROVED",
                "learner_fingerprint": learner_fingerprint,
                "candidate_sha256": candidate["candidate_sha256"],
            }
            approved.append(admitted)
        decisions.append({
            "item_id": item_id,
            "breadth_cell_id": cell_id,
            "status": status,
            "reason_code": reason,
            "candidate_sha256": candidate.get("candidate_sha256"),
            "stimulus_fingerprint": candidate.get("stimulus_fingerprint"),
            "template_family": candidate.get("template_family"),
            "skill": candidate.get("skill"),
            "purpose": candidate.get("purpose"),
            "provenance": candidate.get("provenance"),
        })
    return approved, decisions


def _purpose_capacity(items: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]) -> dict[str, Any]:
    stimuli = {str(row["stimulus_fingerprint"]) for row in items}
    templates = {str(row["template_family"]) for row in items}
    counts = {
        "approved_items": len(items),
        "unique_stimuli": len(stimuli),
        "template_families": len(templates),
    }
    requirements = {
        "approved_items": int(contract["min_approved_items"]),
        "unique_stimuli": int(contract["min_unique_stimuli"]),
        "template_families": int(contract["min_template_families"]),
    }
    shortages = {
        key: max(requirements[key] - counts[key], 0)
        for key in requirements
    }
    return {
        "requirements": requirements,
        "counts": counts,
        "shortages": shortages,
        "capacity_pass": all(value == 0 for value in shortages.values()),
    }


def build(
    *, ontology_path: Path, coverage_path: Path, candidates_path: Path,
    policies_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ontology = _load_ontology(ontology_path)
    coverage = _load_coverage(coverage_path, ontology["ontology_sha256"])
    coverage_sha256 = coverage["report_sha256"]
    cells = _cell_index(coverage)
    candidates = _load_candidates(
        candidates_path,
        ontology_sha256=ontology["ontology_sha256"],
        coverage_sha256=coverage_sha256,
    )
    policies = _load_policies(policies_path, coverage_sha256=coverage_sha256, cell_ids=set(cells))
    approved, decisions = admit_candidates(candidates=candidates, cells=cells, policies=policies)
    approved_by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    decision_by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in approved:
        approved_by_cell[str(row["breadth_cell_id"])].append(row)
    for row in decisions:
        decision_by_cell[str(row["breadth_cell_id"])].append(row)
    cell_reports: list[dict[str, Any]] = []
    for cell_id, cell in sorted(cells.items()):
        cell_items = approved_by_cell.get(cell_id, [])
        cell_decisions = decision_by_cell.get(cell_id, [])
        policy = policies.get(cell_id)
        purpose_reports: dict[str, Any] = {}
        status = "READY_FOR_LOCAL_SELECTION"
        if cell.get("status") == "PROFILE_DEFINITION_REQUIRED":
            status = "BREADTH_PROFILE_REQUIRED"
        elif policy is None:
            status = "CAPACITY_POLICY_MISSING"
        else:
            for purpose, purpose_contract in policy["purposes"].items():
                purpose_items = [row for row in cell_items if row["purpose"] == purpose]
                purpose_reports[purpose] = _purpose_capacity(purpose_items, purpose_contract)
            if not cell_decisions:
                status = "CONTENT_MISSING"
            elif not cell_items and any(row["status"] == "AUTHORITY_REVIEW_REQUIRED" for row in cell_decisions):
                status = "HUMAN_REVIEW_REQUIRED"
            elif not cell_items and any(row["status"] in {"LEARNER_CONTRACT_INVALID", "SCORING_CONTRACT_INVALID", "VALIDATOR_NOT_PASS", "BREADTH_BINDING_INVALID"} for row in cell_decisions):
                status = "VALIDATOR_FAILED"
            elif any(not row["capacity_pass"] for row in purpose_reports.values()):
                status = "CAPACITY_INSUFFICIENT"
            else:
                required_skills = set(policy["required_skill_projection"])
                approved_skills = {str(row["skill"]) for row in cell_items}
                if required_skills - approved_skills:
                    status = "CAPACITY_INSUFFICIENT"
                elif cell.get("status") == "DEFERRED_MEDIA" or (
                    cell_items and all(row.get("media_payload_state") == "DEFERRED_MEDIA_PAYLOAD" for row in cell_items)
                ):
                    status = "MEDIA_DEFERRED"
        cell_reports.append({
            "breadth_cell_id": cell_id,
            "capability_id": cell.get("capability_id"),
            "life_task_id": cell.get("life_task_id"),
            "domain": cell.get("domain"),
            "supply_status": status,
            "capacity_policy_present": policy is not None,
            "approved_item_count": len(cell_items),
            "approved_item_ids": sorted(str(row["item_id"]) for row in cell_items),
            "skill_projection": {
                "required": sorted(policy["required_skill_projection"]) if policy else [],
                "approved": sorted({str(row["skill"]) for row in cell_items}),
                "missing": sorted(set(policy["required_skill_projection"]) - {str(row["skill"]) for row in cell_items}) if policy else [],
            },
            "purpose_capacity": purpose_reports,
            "decision_counts": dict(sorted(Counter(row["status"] for row in cell_decisions).items())),
            "max_recent_reuse": policy["max_recent_reuse"] if policy else None,
        })
    approved.sort(key=lambda row: (str(row["breadth_cell_id"]), str(row["purpose"]), str(row["item_id"])))
    bank_core = {
        "task_id": TASK_ID,
        "schema_version": BANK_SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "source_bindings": {
            "ontology_sha256": ontology["ontology_sha256"],
            "coverage_sha256": coverage_sha256,
            "candidate_registry_sha256": file_digest(candidates_path),
            "capacity_policy_registry_sha256": file_digest(policies_path),
        },
        "selection_contract": {
            "local_free_generation_enabled": False,
            "gpt_direct_item_admission_enabled": False,
            "qwen_direct_item_admission_enabled": False,
            "formal_item_requires_admission_approved": True,
            "recent_reuse_policy_source": "CELL_CAPACITY_POLICY",
        },
        "item_count": len(approved),
        "items": approved,
    }
    bank = {**bank_core, "bank_sha256": digest(bank_core)}
    safe_decisions = decisions
    report_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": bank_core["source_bindings"],
        "counts": {
            "candidate_count": len(candidates),
            "approved_item_count": len(approved),
            "rejected_or_pending_count": len(candidates) - len(approved),
            "breadth_cell_count": len(cells),
            "capacity_policy_count": len(policies),
            "supply_status_counts": dict(sorted(Counter(row["supply_status"] for row in cell_reports).items())),
            "admission_status_counts": dict(sorted(Counter(row["status"] for row in decisions).items())),
        },
        "cell_supply": cell_reports,
        "admission_decisions": safe_decisions,
        "claim_boundaries": {
            "canonical_authority_modified": False,
            "m1_graph_modified": False,
            "r3_denominator_modified": False,
            "local_free_generation_enabled": False,
            "gpt_direct_admission_enabled": False,
            "qwen_required": False,
            "a2_content_admitted": False,
            "audio_files_required": False,
            "mastery_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe_report = {**report_core, "report_sha256": digest(report_core)}
    return bank, safe_report


def safe_scan(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in PRIVATE_KEYS:
                raise QuestionSupplyError(f"private_field_leak:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            raise QuestionSupplyError("absolute_path_leak")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--bank-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args()
    bank, report = build(
        ontology_path=args.ontology,
        coverage_path=args.coverage,
        candidates_path=args.candidates,
        policies_path=args.policies,
    )
    safe_scan(report)
    write_private(args.bank_output, bank)
    write_private(args.report_output, report)
    print(json.dumps({
        "validation_status": STATUS,
        "bank_output": str(args.bank_output),
        "report_output": str(args.report_output),
        "approved_item_count": bank["item_count"],
        "next_short_step": NEXT_SHORT_STEP,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
