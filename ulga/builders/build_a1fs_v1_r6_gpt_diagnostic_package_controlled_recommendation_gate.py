#!/usr/bin/env python3
"""Build de-identified GPT diagnostic requests and gate recommendations.

Task: A1FS-V1-R6_GPTDiagnosticPackageAndControlledRecommendationGate

No model API is invoked. The module prepares a private, de-identified request from
R5 objective evidence plus R4 item context, validates an externally produced
structured diagnostic response, and admits only hash-bound human-reviewed
recommendations into a candidate-only queue. It cannot write mastery, Authority,
PracticeBank, active planner policy, or A2 state.
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

from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1

TASK_ID = "A1FS-V1-R6_GPTDiagnosticPackageAndControlledRecommendationGate"
REQUEST_SCHEMA_VERSION = "a1fs.v1.r6.gpt_diagnostic_request.v1"
SAFE_SCHEMA_VERSION = "a1fs.v1.r6.gpt_diagnostic_request_safe.v1"
RESPONSE_SCHEMA_VERSION = "a1fs.v1.r6.gpt_diagnostic_response.v1"
DECISION_SCHEMA_VERSION = "a1fs.v1.r6.recommendation_decisions.v1"
QUEUE_SCHEMA_VERSION = "a1fs.v1.r6.controlled_recommendation_queue.v1"
REPORT_SCHEMA_VERSION = "a1fs.v1.r6.controlled_recommendation_report.v1"
STATUS = "PASS_A1FS_V1_R6_GPT_DIAGNOSTIC_CONTROLLED_RECOMMENDATION_GATE"
NEXT_SHORT_STEP = "A1FS-V1-R7_CollectorRuntimeAndCoverageGapRepairLoop"

SUFFICIENCY_STATUSES = {"SUFFICIENT", "INSUFFICIENT", "CONFLICTING_EVIDENCE"}
DIAGNOSIS_CATEGORIES = {
    "LANGUAGE_KNOWLEDGE", "VOCABULARY_GAP", "PATTERN_CONTROL_GAP",
    "PRAGMATIC_APPROPRIACY", "CONTEXT_TRANSFER_GAP", "SKILL_ASYMMETRY",
    "SUPPORT_DEPENDENCY", "INITIATIVE_GAP", "COMMUNICATION_REPAIR_GAP",
    "RETENTION_GAP", "CONTENT_CAPACITY_GAP", "DATA_QUALITY_GAP",
    "SYSTEM_ERROR_SUSPECTED", "EVIDENCE_INSUFFICIENT",
}
RECOMMENDATION_TYPES = {
    "REMEDIATION_CANDIDATE", "NEXT_DEPLOYMENT_CELL_CANDIDATE",
    "SKILL_TRANSFER_CANDIDATE", "SUPPORT_CHANGE_CANDIDATE",
    "REPAIR_TASK_CANDIDATE", "RETENTION_REVIEW_CANDIDATE",
    "COLLECTOR_GAP_CANDIDATE", "CONTENT_GAP_CANDIDATE",
    "HUMAN_REVIEW_CANDIDATE",
}
DECISIONS = {"APPROVE_AS_CANDIDATE", "REJECT", "DEFER"}
GATE_CRITERIA = {
    "evidence_grounded", "a1_a1plus_scope_confirmed", "authority_boundary_preserved",
    "deterministic_validation_passed", "no_direct_write", "actionable_and_specific",
    "regression_risk_checked",
}
DIRECT_WRITE_KEYS = {
    "mastery_state", "mastered", "mastery_score", "score_override", "outcome_override",
    "canonical_write", "authority_write", "authority_mutation", "practice_bank_write",
    "active_policy", "activate", "planner_policy_write", "a2_unlocked", "a2_unlock",
    "accepted_answer", "accepted_texts", "accepted_sequence", "private_scoring_contract",
}
PRIVATE_SAFE_KEYS = {
    "response", "prompt", "context", "options", "word_bank", "supplied_tokens",
    "supplied_morphemes", "gap_display_tokens", "expected_contract", "rubric",
    "accepted_texts", "accepted_sequence", "explanation", "action_payload",
    "model_output", "learner_id", "reviewer_id", "notes",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class DiagnosticGateError(ValueError):
    """Fail-closed R6 diagnostic or recommendation gate error."""


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
        raise DiagnosticGateError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise DiagnosticGateError(f"{code}_not_object")
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


def timezone_timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DiagnosticGateError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DiagnosticGateError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DiagnosticGateError(code)
    return value


def _validate_digest_object(value: Mapping[str, Any], digest_key: str, code: str) -> None:
    core = {key: child for key, child in value.items() if key != digest_key}
    if value.get(digest_key) != digest(core):
        raise DiagnosticGateError(code)


def _load_r5(package_path: Path, safe_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    package = read_json(package_path, "r5_package")
    safe = read_json(safe_path, "r5_safe")
    if package.get("task_id") != r5.TASK_ID or package.get("schema_version") != r5.PACKAGE_SCHEMA_VERSION:
        raise DiagnosticGateError("r5_package_identity_invalid")
    if safe.get("task_id") != r5.TASK_ID or safe.get("schema_version") != r5.SAFE_SCHEMA_VERSION:
        raise DiagnosticGateError("r5_safe_identity_invalid")
    if package.get("validation_status") != r5.STATUS or safe.get("validation_status") != r5.STATUS:
        raise DiagnosticGateError("r5_status_invalid")
    if package.get("private_local_only") is not True:
        raise DiagnosticGateError("r5_package_privacy_invalid")
    _validate_digest_object(package, "package_sha256", "r5_package_digest_invalid")
    _validate_digest_object(safe, "summary_sha256", "r5_safe_digest_invalid")
    entries = package.get("entries")
    safe_entries = safe.get("entries")
    if not isinstance(entries, list) or not isinstance(safe_entries, list):
        raise DiagnosticGateError("r5_entries_invalid")
    if package.get("entries_sha256") != digest(entries) or safe.get("entries_sha256") != digest(safe_entries):
        raise DiagnosticGateError("r5_entries_digest_invalid")
    if package.get("attempt_count") != len(entries) or safe.get("attempt_count") != len(safe_entries):
        raise DiagnosticGateError("r5_attempt_count_invalid")
    if package.get("attempt_count") != safe.get("attempt_count"):
        raise DiagnosticGateError("r5_package_safe_count_mismatch")
    if safe.get("learner_ref_sha256") != digest(str(package.get("learner_id"))):
        raise DiagnosticGateError("r5_learner_hash_mismatch")
    safe_by_attempt = {str(row.get("attempt_id")): row for row in safe_entries if isinstance(row, Mapping)}
    if len(safe_by_attempt) != len(safe_entries):
        raise DiagnosticGateError("r5_safe_attempt_identity_invalid")
    for row in entries:
        attempt_id = str(row.get("attempt_id") or "")
        if attempt_id not in safe_by_attempt:
            raise DiagnosticGateError(f"r5_safe_attempt_missing:{attempt_id}")
        expected_safe = {key: child for key, child in row.items() if key not in {"response", "operator_review"}}
        if safe_by_attempt[attempt_id] != expected_safe:
            raise DiagnosticGateError(f"r5_safe_attempt_drift:{attempt_id}")
    return package, safe


def _load_bank(path: Path) -> dict[str, Any]:
    bank = read_json(path, "r4_bank")
    if bank.get("task_id") != r4.TASK_ID or bank.get("schema_version") != r4.BANK_SCHEMA_VERSION:
        raise DiagnosticGateError("r4_bank_identity_invalid")
    if bank.get("validation_status") != r4.STATUS or bank.get("private_local_only") is not True:
        raise DiagnosticGateError("r4_bank_status_invalid")
    _validate_digest_object(bank, "bank_sha256", "r4_bank_digest_invalid")
    items = bank.get("items")
    if not isinstance(items, list) or bank.get("item_count") != len(items):
        raise DiagnosticGateError("r4_bank_item_count_invalid")
    ids = [str(row.get("item_id") or "") for row in items if isinstance(row, Mapping)]
    if len(ids) != len(items) or len(ids) != len(set(ids)):
        raise DiagnosticGateError("r4_bank_item_identity_invalid")
    return bank


def _load_coverage(path: Path) -> dict[str, Any]:
    coverage = read_json(path, "r3_coverage")
    if coverage.get("task_id") != r3.TASK_ID or coverage.get("schema_version") != r3.SCHEMA_VERSION:
        raise DiagnosticGateError("r3_coverage_identity_invalid")
    if coverage.get("validation_status") != r3.STATUS:
        raise DiagnosticGateError("r3_coverage_status_invalid")
    _validate_digest_object(coverage, "report_sha256", "r3_coverage_digest_invalid")
    cells = coverage.get("cells")
    if not isinstance(cells, list):
        raise DiagnosticGateError("r3_cells_invalid")
    cell_ids = [str(row.get("cell_id") or "") for row in cells if isinstance(row, Mapping)]
    if len(cell_ids) != len(cells) or len(cell_ids) != len(set(cell_ids)):
        raise DiagnosticGateError("r3_cell_identity_invalid")
    return coverage


def _expected_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    scoring = item.get("private_scoring_contract")
    if not isinstance(scoring, Mapping):
        raise DiagnosticGateError(f"scoring_contract_missing:{item.get('item_id')}")
    mode = scoring.get("scoring_mode")
    core: dict[str, Any] = {
        "scoring_mode": mode,
        "response_type": scoring.get("response_type"),
        "human_review_fallback": bool(scoring.get("human_review_fallback")),
    }
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        core["accepted_texts"] = list(scoring.get("accepted_texts", []))
    elif mode == "EXACT_SEQUENCE":
        core["accepted_sequence"] = list(scoring.get("accepted_sequence", []))
    elif mode == "FEATURE_RUBRIC":
        core["rubric"] = deepcopy(dict(scoring.get("rubric", {})))
    else:
        raise DiagnosticGateError(f"unsupported_scoring_mode:{item.get('item_id')}")
    return core


def _severity(row: Mapping[str, Any]) -> tuple[int, str]:
    if row.get("validity_status") != r1.VALID:
        return (99, str(row.get("attempt_id")))
    outcome = row.get("outcome")
    if outcome in {"HUMAN_REJECT", "AUTO_FAIL"}:
        return (0, str(row.get("attempt_id")))
    if outcome in {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}:
        return (1, str(row.get("attempt_id")))
    if outcome in {"HUMAN_APPROVE", "AUTO_PASS"}:
        return (2, str(row.get("attempt_id")))
    return (3, str(row.get("attempt_id")))


def build_request(
    *, evidence_package_path: Path, evidence_safe_path: Path, bank_path: Path,
    coverage_path: Path, max_representatives_per_cell: int = 6,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if max_representatives_per_cell < 1 or max_representatives_per_cell > 20:
        raise DiagnosticGateError("representative_limit_invalid")
    package, safe = _load_r5(evidence_package_path, evidence_safe_path)
    bank = _load_bank(bank_path)
    coverage = _load_coverage(coverage_path)
    bank_items = {str(row["item_id"]): row for row in bank["items"]}
    cells = {str(row["cell_id"]): row for row in coverage["cells"]}
    valid_entries = [row for row in package["entries"] if row.get("validity_status") == r1.VALID]
    for row in valid_entries:
        item_id = str(row.get("item_id") or "")
        if item_id not in bank_items:
            raise DiagnosticGateError(f"evidence_item_not_in_bank:{item_id}")
        if row.get("breadth_cell_id") not in cells:
            raise DiagnosticGateError(f"evidence_cell_not_in_coverage:{row.get('breadth_cell_id')}")
        item = bank_items[item_id]
        for key in ("breadth_cell_id", "capability_id", "life_task_id", "domain", "skill", "purpose"):
            if row.get(key) != item.get(key):
                raise DiagnosticGateError(f"evidence_bank_binding_mismatch:{item_id}:{key}")
        if row.get("level") not in {"A1", "A1_PLUS"}:
            raise DiagnosticGateError(f"evidence_level_out_of_scope:{item_id}")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in valid_entries:
        grouped[str(row["breadth_cell_id"])].append(row)
    representatives: list[dict[str, Any]] = []
    for cell_id in sorted(grouped):
        rows = sorted(grouped[cell_id], key=_severity)[:max_representatives_per_cell]
        for row in rows:
            item = bank_items[str(row["item_id"])]
            learner = item.get("learner_contract")
            if not isinstance(learner, Mapping):
                raise DiagnosticGateError(f"learner_contract_missing:{row.get('item_id')}")
            evidence_ref = f"R6_EVIDENCE:{digest([package['package_sha256'], row['attempt_id']])[:24]}"
            representatives.append({
                "evidence_ref": evidence_ref,
                "attempt_ref_sha256": digest(str(row["attempt_id"])),
                "session_ref_sha256": digest(str(row["session_id"])),
                "item_id": row["item_id"],
                "breadth_cell_id": row["breadth_cell_id"],
                "capability_id": row["capability_id"],
                "life_task_id": row["life_task_id"],
                "domain": row["domain"],
                "level": row["level"],
                "skill": row["skill"],
                "purpose": row["purpose"],
                "task_type": row["task_type"],
                "support_level": row["support_level"],
                "initiative_level": row["initiative_level"],
                "interaction_variation": row["interaction_variation"],
                "transfer_distance": row["transfer_distance"],
                "template_family": row["template_family"],
                "stimulus_fingerprint": row["stimulus_fingerprint"],
                "prompt": learner.get("prompt"),
                "context": deepcopy(learner.get("context", {})),
                "options": deepcopy(learner.get("options", [])),
                "supplied_tokens": deepcopy(learner.get("supplied_tokens", [])),
                "supplied_morphemes": deepcopy(learner.get("supplied_morphemes", [])),
                "word_bank": deepcopy(learner.get("word_bank", [])),
                "response": deepcopy(row["response"]),
                "expected_contract": _expected_contract(item),
                "outcome": row["outcome"],
                "score": row["score"],
                "response_time_ms": row["response_time_ms"],
                "hint_count": row["hint_count"],
                "revision_count": row["revision_count"],
                "submitted_at": row["submitted_at"],
                "session_state": row["session_state"],
                "validity_status": row["validity_status"],
            })
    referenced_cells = sorted({row["breadth_cell_id"] for row in representatives})
    gap_context = [{
        "breadth_cell_id": cell_id,
        "capability_id": cells[cell_id].get("capability_id"),
        "life_task_id": cells[cell_id].get("life_task_id"),
        "domain": cells[cell_id].get("domain"),
        "coverage_status": cells[cell_id].get("status"),
        "dimension_coverage": deepcopy(cells[cell_id].get("dimension_coverage", {})),
        "next_actions": deepcopy(cells[cell_id].get("next_actions", [])),
    } for cell_id in referenced_cells]
    request_core = {
        "task_id": TASK_ID,
        "schema_version": REQUEST_SCHEMA_VERSION,
        "private_local_only": True,
        "analysis_role": "DIAGNOSTIC_CANDIDATE_ONLY",
        "source_bindings": {
            "r5_package_sha256": package["package_sha256"],
            "r5_safe_summary_sha256": safe["summary_sha256"],
            "r4_bank_sha256": bank["bank_sha256"],
            "r3_coverage_sha256": coverage["report_sha256"],
        },
        "learner_ref_sha256": safe["learner_ref_sha256"],
        "analysis_window": {
            "exported_at": package["exported_at"],
            "attempt_count": package["attempt_count"],
            "valid_attempt_count": package["valid_attempt_count"],
            "resolved_valid_attempt_count": package["resolved_valid_attempt_count"],
            "representative_evidence_count": len(representatives),
        },
        "objective_summary": deepcopy(package["objective_summary"]),
        "coverage_gap_context": gap_context,
        "representative_evidence": representatives,
        "required_output_contract": {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "sufficiency_statuses": sorted(SUFFICIENCY_STATUSES),
            "diagnosis_categories": sorted(DIAGNOSIS_CATEGORIES),
            "recommendation_types": sorted(RECOMMENDATION_TYPES),
            "every_claim_requires_evidence_refs": True,
            "candidate_only_required": True,
        },
        "prohibited_actions": {
            "mastery_write": True,
            "score_override": True,
            "canonical_authority_write": True,
            "practice_bank_write": True,
            "active_planner_policy_write": True,
            "a2_unlock": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    request = {**request_core, "request_sha256": digest(request_core)}
    safe_core = {
        "task_id": TASK_ID,
        "schema_version": SAFE_SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": request_core["source_bindings"],
        "learner_ref_sha256": safe["learner_ref_sha256"],
        "analysis_window": request_core["analysis_window"],
        "objective_summary": request_core["objective_summary"],
        "coverage_cell_ids": referenced_cells,
        "representative_evidence_refs": [row["evidence_ref"] for row in representatives],
        "representative_evidence_hashes": [digest(row) for row in representatives],
        "request_sha256": request["request_sha256"],
        "claim_boundaries": {
            "raw_response_included": False,
            "prompt_included": False,
            "expected_answer_included": False,
            "learner_identity_included": False,
            "model_invoked": False,
            "mastery_written": False,
            "canonical_written": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe_request = {**safe_core, "summary_sha256": digest(safe_core)}
    return request, safe_request


def _recursive_forbidden(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).casefold() in DIRECT_WRITE_KEYS:
                errors.append(f"direct_write_key:{child_path}")
            errors.extend(_recursive_forbidden(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_recursive_forbidden(child, f"{path}[{index}]"))
    return errors


def response_core(response: Mapping[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in response.items() if key != "response_sha256"}


def validate_response(
    *, request: Mapping[str, Any], response: Mapping[str, Any], coverage: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    required_top = {
        "task_id", "schema_version", "request_sha256", "candidate_only", "model_metadata",
        "evidence_sufficiency", "diagnoses", "recommendations", "prohibited_write_confirmation",
        "response_sha256",
    }
    if set(response) != required_top:
        errors.append("response_shape_invalid")
    if response.get("task_id") != TASK_ID or response.get("schema_version") != RESPONSE_SCHEMA_VERSION:
        errors.append("response_identity_invalid")
    if response.get("request_sha256") != request.get("request_sha256"):
        errors.append("response_request_binding_invalid")
    if response.get("candidate_only") is not True:
        errors.append("response_candidate_only_required")
    if response.get("response_sha256") != digest(response_core(response)):
        errors.append("response_digest_invalid")
    model = response.get("model_metadata")
    if not isinstance(model, Mapping) or set(model) != {"provider", "model_id", "generated_at"}:
        errors.append("model_metadata_invalid")
    else:
        if not str(model.get("provider") or "").strip() or not str(model.get("model_id") or "").strip():
            errors.append("model_identity_missing")
        try:
            timezone_timestamp(model.get("generated_at"), "model_generated_at_invalid")
        except DiagnosticGateError as exc:
            errors.append(str(exc))
    sufficiency = response.get("evidence_sufficiency")
    if not isinstance(sufficiency, Mapping) or set(sufficiency) != {"status", "reason_codes", "missing_evidence_requests"}:
        errors.append("evidence_sufficiency_invalid")
        sufficiency_status = None
    else:
        sufficiency_status = sufficiency.get("status")
        if sufficiency_status not in SUFFICIENCY_STATUSES:
            errors.append("evidence_sufficiency_status_invalid")
        for key in ("reason_codes", "missing_evidence_requests"):
            values = sufficiency.get(key)
            if not isinstance(values, list) or not all(isinstance(row, str) and row.strip() for row in values):
                errors.append(f"evidence_sufficiency_{key}_invalid")
    evidence_refs = {
        str(row.get("evidence_ref")) for row in request.get("representative_evidence", [])
        if isinstance(row, Mapping)
    }
    cell_ids = {
        str(row.get("cell_id")) for row in coverage.get("cells", [])
        if isinstance(row, Mapping)
    }
    diagnoses = response.get("diagnoses")
    if not isinstance(diagnoses, list):
        errors.append("diagnoses_not_list"); diagnoses = []
    diagnosis_ids: set[str] = set()
    for row in diagnoses:
        if not isinstance(row, Mapping):
            errors.append("diagnosis_not_object"); continue
        required = {"diagnosis_id", "category", "scope", "evidence_refs", "confidence", "explanation", "candidate_only"}
        if set(row) != required:
            errors.append(f"diagnosis_shape_invalid:{row.get('diagnosis_id')}"); continue
        diagnosis_id = str(row.get("diagnosis_id") or "")
        if not diagnosis_id or diagnosis_id in diagnosis_ids:
            errors.append(f"diagnosis_identity_invalid:{diagnosis_id}")
        diagnosis_ids.add(diagnosis_id)
        if row.get("category") not in DIAGNOSIS_CATEGORIES:
            errors.append(f"diagnosis_category_invalid:{diagnosis_id}")
        scope = row.get("scope")
        if not isinstance(scope, Mapping) or set(scope) != {"breadth_cell_ids", "capability_ids", "skills"}:
            errors.append(f"diagnosis_scope_invalid:{diagnosis_id}")
        else:
            scoped_cells = scope.get("breadth_cell_ids")
            if not isinstance(scoped_cells, list) or set(scoped_cells) - cell_ids:
                errors.append(f"diagnosis_scope_cell_invalid:{diagnosis_id}")
            for key in ("capability_ids", "skills"):
                if not isinstance(scope.get(key), list):
                    errors.append(f"diagnosis_scope_{key}_invalid:{diagnosis_id}")
        refs = row.get("evidence_refs")
        if not isinstance(refs, list) or not refs or set(refs) - evidence_refs:
            errors.append(f"diagnosis_evidence_refs_invalid:{diagnosis_id}")
        confidence = row.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            errors.append(f"diagnosis_confidence_invalid:{diagnosis_id}")
        if not str(row.get("explanation") or "").strip():
            errors.append(f"diagnosis_explanation_missing:{diagnosis_id}")
        if row.get("candidate_only") is not True:
            errors.append(f"diagnosis_candidate_only_required:{diagnosis_id}")
    recommendations = response.get("recommendations")
    if not isinstance(recommendations, list):
        errors.append("recommendations_not_list"); recommendations = []
    recommendation_ids: set[str] = set()
    for row in recommendations:
        if not isinstance(row, Mapping):
            errors.append("recommendation_not_object"); continue
        required = {
            "recommendation_id", "type", "diagnosis_ids", "target_breadth_cell_id",
            "evidence_refs", "action_payload", "candidate_only",
        }
        if set(row) != required:
            errors.append(f"recommendation_shape_invalid:{row.get('recommendation_id')}"); continue
        recommendation_id = str(row.get("recommendation_id") or "")
        if not recommendation_id or recommendation_id in recommendation_ids:
            errors.append(f"recommendation_identity_invalid:{recommendation_id}")
        recommendation_ids.add(recommendation_id)
        if row.get("type") not in RECOMMENDATION_TYPES:
            errors.append(f"recommendation_type_invalid:{recommendation_id}")
        linked = row.get("diagnosis_ids")
        if not isinstance(linked, list) or not linked or set(linked) - diagnosis_ids:
            errors.append(f"recommendation_diagnosis_refs_invalid:{recommendation_id}")
        refs = row.get("evidence_refs")
        if not isinstance(refs, list) or not refs or set(refs) - evidence_refs:
            errors.append(f"recommendation_evidence_refs_invalid:{recommendation_id}")
        target = row.get("target_breadth_cell_id")
        target_optional = row.get("type") in {
            "COLLECTOR_GAP_CANDIDATE", "CONTENT_GAP_CANDIDATE", "HUMAN_REVIEW_CANDIDATE",
        }
        if target is None and not target_optional:
            errors.append(f"recommendation_target_required:{recommendation_id}")
        if target is not None and target not in cell_ids:
            errors.append(f"recommendation_target_invalid:{recommendation_id}")
        payload = row.get("action_payload")
        if not isinstance(payload, Mapping):
            errors.append(f"recommendation_payload_invalid:{recommendation_id}")
        else:
            errors.extend(f"{recommendation_id}:{error}" for error in _recursive_forbidden(payload))
            if str(payload.get("level") or "").upper() in {"A2", "A2_PLUS", "B1", "B2", "C1", "C2"}:
                errors.append(f"recommendation_level_out_of_scope:{recommendation_id}")
        if row.get("candidate_only") is not True:
            errors.append(f"recommendation_candidate_only_required:{recommendation_id}")
    confirmation = response.get("prohibited_write_confirmation")
    required_confirmation = {
        "mastery_written", "score_overridden", "canonical_authority_written",
        "practice_bank_written", "active_planner_policy_written", "a2_unlocked",
    }
    if not isinstance(confirmation, Mapping) or set(confirmation) != required_confirmation:
        errors.append("prohibited_write_confirmation_invalid")
    elif any(confirmation.get(key) is not False for key in required_confirmation):
        errors.append("prohibited_write_confirmation_broken")
    if sufficiency_status != "SUFFICIENT" and recommendations:
        errors.append("recommendations_for_insufficient_evidence_forbidden")
    return {
        "validation_status": STATUS if not errors else "FAIL_A1FS_V1_R6_DIAGNOSTIC_RESPONSE",
        "error_count": len(errors),
        "errors": errors,
        "diagnosis_count": len(diagnoses),
        "recommendation_count": len(recommendations),
        "next_short_step": NEXT_SHORT_STEP if not errors else TASK_ID,
    }


def decision_registry(
    *, request_sha256: str, response_sha256: str, decisions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in decisions]
    core = {
        "task_id": TASK_ID,
        "schema_version": DECISION_SCHEMA_VERSION,
        "request_sha256": request_sha256,
        "response_sha256": response_sha256,
        "decisions": rows,
    }
    return {**core, "decisions_sha256": digest(rows)}


def _validate_decisions(
    *, registry: Mapping[str, Any], request: Mapping[str, Any], response: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if registry.get("task_id") != TASK_ID or registry.get("schema_version") != DECISION_SCHEMA_VERSION:
        raise DiagnosticGateError("decision_registry_identity_invalid")
    if registry.get("request_sha256") != request.get("request_sha256"):
        raise DiagnosticGateError("decision_request_binding_invalid")
    if registry.get("response_sha256") != response.get("response_sha256"):
        raise DiagnosticGateError("decision_response_binding_invalid")
    rows = registry.get("decisions")
    if not isinstance(rows, list) or registry.get("decisions_sha256") != digest(rows):
        raise DiagnosticGateError("decision_registry_digest_invalid")
    recommendation_ids = {str(row["recommendation_id"]) for row in response.get("recommendations", [])}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise DiagnosticGateError("decision_not_object")
        required = {"recommendation_id", "decision", "reviewer_id", "reviewed_at", "criteria", "notes"}
        if set(row) != required:
            raise DiagnosticGateError("decision_shape_invalid")
        recommendation_id = str(row.get("recommendation_id") or "")
        if recommendation_id not in recommendation_ids or recommendation_id in result:
            raise DiagnosticGateError(f"decision_recommendation_invalid:{recommendation_id}")
        if row.get("decision") not in DECISIONS:
            raise DiagnosticGateError(f"decision_value_invalid:{recommendation_id}")
        if not str(row.get("reviewer_id") or "").strip():
            raise DiagnosticGateError(f"decision_reviewer_missing:{recommendation_id}")
        timezone_timestamp(row.get("reviewed_at"), f"decision_timestamp_invalid:{recommendation_id}")
        criteria = row.get("criteria")
        if not isinstance(criteria, Mapping) or set(criteria) != GATE_CRITERIA:
            raise DiagnosticGateError(f"decision_criteria_invalid:{recommendation_id}")
        if any(criteria[key] not in {True, False} for key in GATE_CRITERIA):
            raise DiagnosticGateError(f"decision_criteria_value_invalid:{recommendation_id}")
        if row.get("decision") == "APPROVE_AS_CANDIDATE" and not all(criteria.values()):
            raise DiagnosticGateError(f"approved_decision_criteria_not_all_true:{recommendation_id}")
        result[recommendation_id] = deepcopy(dict(row))
    return result


def apply_gate(
    *, request: Mapping[str, Any], response: Mapping[str, Any], decisions: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    validation = validate_response(request=request, response=response, coverage=coverage)
    if validation["error_count"]:
        raise DiagnosticGateError("diagnostic_response_invalid:" + "|".join(validation["errors"]))
    decision_by_id = _validate_decisions(registry=decisions, request=request, response=response)
    approved: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    recommendations = {str(row["recommendation_id"]): row for row in response["recommendations"]}
    for recommendation_id in sorted(recommendations):
        recommendation = recommendations[recommendation_id]
        decision = decision_by_id.get(recommendation_id)
        state = decision["decision"] if decision else "UNREVIEWED"
        if state == "APPROVE_AS_CANDIDATE":
            approved.append({
                "recommendation_id": recommendation_id,
                "type": recommendation["type"],
                "diagnosis_ids": list(recommendation["diagnosis_ids"]),
                "target_breadth_cell_id": recommendation["target_breadth_cell_id"],
                "evidence_refs": list(recommendation["evidence_refs"]),
                "action_payload": deepcopy(dict(recommendation["action_payload"])),
                "activation_state": "CANDIDATE_ONLY_NOT_ACTIVE",
                "gate": {
                    "decision": state,
                    "reviewer_id": decision["reviewer_id"],
                    "reviewed_at": decision["reviewed_at"],
                    "criteria": deepcopy(dict(decision["criteria"])),
                    "request_sha256": request["request_sha256"],
                    "response_sha256": response["response_sha256"],
                },
            })
        decision_rows.append({
            "recommendation_id": recommendation_id,
            "type": recommendation["type"],
            "target_breadth_cell_id": recommendation["target_breadth_cell_id"],
            "decision": state,
        })
    queue_core = {
        "task_id": TASK_ID,
        "schema_version": QUEUE_SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "source_bindings": {
            "request_sha256": request["request_sha256"],
            "response_sha256": response["response_sha256"],
            "decisions_sha256": decisions["decisions_sha256"],
            "coverage_sha256": coverage["report_sha256"],
        },
        "candidate_count": len(approved),
        "candidates": approved,
        "activation_contract": {
            "active_policy_written": False,
            "planner_mutated": False,
            "mastery_written": False,
            "canonical_authority_written": False,
            "practice_bank_written": False,
            "separate_downstream_promotion_required": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    queue = {**queue_core, "queue_sha256": digest(queue_core)}
    report_core = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": queue_core["source_bindings"],
        "counts": {
            "diagnosis_count": len(response["diagnoses"]),
            "recommendation_count": len(response["recommendations"]),
            "candidate_count": len(approved),
            "decision_counts": dict(sorted(Counter(row["decision"] for row in decision_rows).items())),
            "recommendation_type_counts": dict(sorted(Counter(row["type"] for row in decision_rows).items())),
        },
        "decisions": decision_rows,
        "candidate_ids": [row["recommendation_id"] for row in approved],
        "claim_boundaries": {
            "raw_response_included": False,
            "diagnostic_explanation_included": False,
            "action_payload_included": False,
            "reviewer_identity_included": False,
            "mastery_written": False,
            "canonical_written": False,
            "practice_bank_written": False,
            "active_policy_written": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**report_core, "report_sha256": digest(report_core)}
    return queue, report


def safe_scan(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in PRIVATE_SAFE_KEYS:
                raise DiagnosticGateError(f"safe_private_field:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            raise DiagnosticGateError("safe_absolute_path")


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    request_cmd = commands.add_parser("build-request")
    request_cmd.add_argument("--evidence-package", type=Path, required=True)
    request_cmd.add_argument("--evidence-safe", type=Path, required=True)
    request_cmd.add_argument("--bank", type=Path, required=True)
    request_cmd.add_argument("--coverage", type=Path, required=True)
    request_cmd.add_argument("--request-output", type=Path, required=True)
    request_cmd.add_argument("--safe-output", type=Path, required=True)
    request_cmd.add_argument("--max-per-cell", type=int, default=6)
    validate_cmd = commands.add_parser("validate-response")
    validate_cmd.add_argument("--request", type=Path, required=True)
    validate_cmd.add_argument("--response", type=Path, required=True)
    validate_cmd.add_argument("--coverage", type=Path, required=True)
    gate_cmd = commands.add_parser("apply-gate")
    gate_cmd.add_argument("--request", type=Path, required=True)
    gate_cmd.add_argument("--response", type=Path, required=True)
    gate_cmd.add_argument("--decisions", type=Path, required=True)
    gate_cmd.add_argument("--coverage", type=Path, required=True)
    gate_cmd.add_argument("--queue-output", type=Path, required=True)
    gate_cmd.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build-request":
        request, safe = build_request(
            evidence_package_path=args.evidence_package,
            evidence_safe_path=args.evidence_safe,
            bank_path=args.bank,
            coverage_path=args.coverage,
            max_representatives_per_cell=args.max_per_cell,
        )
        safe_scan(safe)
        write_private(args.request_output, request)
        write_private(args.safe_output, safe)
        result = {
            "validation_status": STATUS,
            "request_output": str(args.request_output),
            "safe_output": str(args.safe_output),
            "representative_evidence_count": request["analysis_window"]["representative_evidence_count"],
            "next_short_step": NEXT_SHORT_STEP,
        }
    elif args.command == "validate-response":
        request = read_json(args.request, "request")
        response = read_json(args.response, "response")
        coverage = _load_coverage(args.coverage)
        result = validate_response(request=request, response=response, coverage=coverage)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["error_count"] == 0 else 1
    else:
        request = read_json(args.request, "request")
        response = read_json(args.response, "response")
        decisions = read_json(args.decisions, "decisions")
        coverage = _load_coverage(args.coverage)
        queue, report = apply_gate(request=request, response=response, decisions=decisions, coverage=coverage)
        safe_scan(report)
        write_private(args.queue_output, queue)
        write_private(args.report_output, report)
        result = {
            "validation_status": STATUS,
            "queue_output": str(args.queue_output),
            "report_output": str(args.report_output),
            "candidate_count": queue["candidate_count"],
            "next_short_step": NEXT_SHORT_STEP,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
