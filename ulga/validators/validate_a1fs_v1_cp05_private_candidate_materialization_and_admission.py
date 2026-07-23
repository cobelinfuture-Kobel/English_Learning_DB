#!/usr/bin/env python3
"""Independently validate CP05 private materialization, admission, and safe readback."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04  # noqa: E402
from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as builder  # noqa: E402
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy  # noqa: E402
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep  # noqa: E402
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup  # noqa: E402
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry  # noqa: E402
from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as envelope_validator  # noqa: E402

TASK_ID = builder.TASK_ID
CANDIDATE_PASS_STATUS = "PASS_CP05_PRIVATE_CANDIDATE_VALIDATED"
PASS_STATUS = builder.PASS_STATUS
FORBIDDEN_SAFE_KEYS = {
    "text",
    "title",
    "payload",
    "prompt",
    "answer",
    "answer_key",
    "accepted_texts",
    "scoring_contract",
    "learner_response",
    "transcript",
}


def _digest(value: Any) -> str:
    return content_policy.digest(value)


def _package_hash_valid(package: Mapping[str, Any]) -> bool:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        return False
    core = dict(package)
    core.pop("package_sha256", None)
    return deep.sha256_value(core) == claimed


def _safe_leakage(value: Any) -> list[str]:
    errors: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                child_path = f"{path}.{key}" if path else str(key)
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    errors.append(f"safe_private_key_detected:{child_path}")
                walk(child, child_path)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")

    walk(value, "")
    return errors


def validate_candidate(
    candidate: Mapping[str, Any],
    *,
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    dedup_package: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    envelope = envelope_validator.validate_artifact(candidate, expected_role="CANDIDATE_JSON")
    errors.extend(f"envelope:{error}" for error in envelope.get("errors", []))

    payload = candidate.get("payload")
    bindings = candidate.get("source_bindings")
    if not isinstance(payload, Mapping):
        errors.append("payload_object_required")
        payload = {}
    if not isinstance(bindings, Mapping):
        errors.append("source_bindings_object_required")
        bindings = {}

    if payload.get("task_id") != TASK_ID:
        errors.append("task_id_invalid")
    if payload.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_invalid")
    if payload.get("course_container") != "EXISTING_24_CANONICAL_UNITS_ONLY":
        errors.append("course_container_invalid")
    if payload.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")
    if payload.get("stop_reason") != "NONE":
        errors.append("stop_reason_invalid")

    if cp04_artifact.get("task_id") != cp04.TASK_ID:
        errors.append("cp04_task_id_invalid")
    if registry_package.get("task_id") != registry.TASK_ID or not _package_hash_valid(registry_package):
        errors.append("registry_identity_or_hash_invalid")
    if dedup_package.get("task_id") != dedup.TASK_ID or not _package_hash_valid(dedup_package):
        errors.append("dedup_identity_or_hash_invalid")
    if bindings.get("cp04_artifact_sha256") != _digest(cp04_artifact):
        errors.append("cp04_source_sha256_mismatch")
    if bindings.get("raz_registry_package_sha256") != registry_package.get("package_sha256"):
        errors.append("registry_source_sha256_mismatch")
    if bindings.get("semantic_dedup_package_sha256") != dedup_package.get("package_sha256"):
        errors.append("dedup_source_sha256_mismatch")

    units = payload.get("learning_units")
    if not isinstance(units, list) or len(units) != 24:
        errors.append("learning_unit_count_not_24")
        units = []
    unit_ids = [str(row.get("learning_unit_id") or "") for row in units if isinstance(row, Mapping)]
    grammar_ids = [str(row.get("grammar_unit_id") or "") for row in units if isinstance(row, Mapping)]
    if len(set(unit_ids)) != 24 or "" in unit_ids:
        errors.append("learning_unit_identity_invalid")
    if len(set(grammar_ids)) != 24 or "" in grammar_ids:
        errors.append("grammar_unit_identity_invalid")
    if [row.get("sequence_index") for row in units if isinstance(row, Mapping)] != list(range(1, 25)):
        errors.append("unit_sequence_invalid")

    sources = payload.get("materialized_raz_sources")
    raz_bindings = payload.get("raz_unit_activity_bindings")
    m11b = payload.get("m11b_reuse_activities")
    remediation = payload.get("remediation_queue")
    for value, code in (
        (sources, "materialized_sources_list_required"),
        (raz_bindings, "raz_bindings_list_required"),
        (m11b, "m11b_reuse_list_required"),
        (remediation, "remediation_queue_list_required"),
    ):
        if not isinstance(value, list):
            errors.append(code)
    sources = sources if isinstance(sources, list) else []
    raz_bindings = raz_bindings if isinstance(raz_bindings, list) else []
    m11b = m11b if isinstance(m11b, list) else []
    remediation = remediation if isinstance(remediation, list) else []

    material_ids: set[str] = set()
    source_refs: set[str] = set()
    source_digest_rows: list[dict[str, str]] = []
    material_skills: dict[str, set[str]] = {}
    for row in sources:
        if not isinstance(row, Mapping):
            errors.append("materialized_source_row_invalid")
            continue
        material_id = str(row.get("material_id") or "")
        source_ref = str(row.get("source_unit_ref") or "")
        if not material_id or material_id in material_ids:
            errors.append("material_id_missing_or_duplicate")
        if not source_ref or source_ref in source_refs:
            errors.append("source_ref_missing_or_duplicate")
        material_ids.add(material_id)
        source_refs.add(source_ref)
        source_content = row.get("source_content")
        text = source_content.get("text") if isinstance(source_content, Mapping) else None
        if not isinstance(text, str) or not text.strip():
            errors.append(f"source_text_missing:{material_id}")
            continue
        source_sha = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        if row.get("source_content_sha256") != source_sha:
            errors.append(f"source_content_sha256_mismatch:{material_id}")
        source_digest_rows.append({"source_unit_ref": source_ref, "source_content_sha256": source_sha})
        if row.get("candidate_cefr_scope") not in {"A1", "A1_PLUS"}:
            errors.append(f"material_scope_invalid:{material_id}")
        contracts = row.get("skill_contracts")
        if not isinstance(contracts, list) or not contracts:
            errors.append(f"skill_contracts_missing:{material_id}")
            continue
        skills: set[str] = set()
        for contract in contracts:
            if not isinstance(contract, Mapping):
                errors.append(f"skill_contract_invalid:{material_id}")
                continue
            skill = str(contract.get("skill") or "")
            if skill not in builder.ALLOWED_SKILLS or skill in skills:
                errors.append(f"skill_contract_skill_invalid:{material_id}:{skill}")
            skills.add(skill)
            if not isinstance(contract.get("prompt"), str) or not contract.get("prompt", "").strip():
                errors.append(f"skill_prompt_missing:{material_id}:{skill}")
            scoring = contract.get("scoring_contract")
            if not isinstance(scoring, Mapping) or scoring.get("mode") != "RUBRIC":
                errors.append(f"skill_scoring_contract_invalid:{material_id}:{skill}")
            elif scoring.get("automatic_exact_answer") is not False:
                errors.append(f"objective_answer_fabrication_detected:{material_id}:{skill}")
            if any(key in contract for key in ("answer", "answer_key", "accepted_texts")):
                errors.append(f"answer_field_forbidden:{material_id}:{skill}")
        material_skills[material_id] = skills

    source_digest_rows.sort(key=lambda row: row["source_unit_ref"])
    private_source_sha = _digest(source_digest_rows)
    if payload.get("private_source_identity", {}).get("private_source_set_sha256") != private_source_sha:
        errors.append("private_source_set_sha256_mismatch")
    if bindings.get("private_source_set_sha256") != private_source_sha:
        errors.append("private_source_binding_sha256_mismatch")

    binding_ids: set[str] = set()
    raz_candidate_pairs: set[tuple[str, str]] = set()
    skill_counts: Counter[str] = Counter()
    for row in raz_bindings:
        if not isinstance(row, Mapping):
            errors.append("raz_binding_row_invalid")
            continue
        binding_id = str(row.get("activity_binding_id") or "")
        learning_id = str(row.get("learning_unit_id") or "")
        material_id = str(row.get("material_id") or "")
        pair = (learning_id, str(row.get("exercise_candidate_id") or ""))
        if not binding_id or binding_id in binding_ids:
            errors.append("raz_activity_binding_id_missing_or_duplicate")
        binding_ids.add(binding_id)
        if pair in raz_candidate_pairs or not all(pair):
            errors.append("raz_candidate_binding_missing_or_duplicate")
        raz_candidate_pairs.add(pair)
        if learning_id not in unit_ids:
            errors.append(f"raz_binding_unknown_unit:{learning_id}")
        if material_id not in material_ids:
            errors.append(f"raz_binding_unmaterialized_source:{material_id}")
        skills = row.get("target_skill_lanes")
        if not isinstance(skills, list) or set(skills) != material_skills.get(material_id, set()):
            errors.append(f"raz_binding_skill_drift:{binding_id}")
        else:
            skill_counts.update(skills)
        if row.get("admission_status") != "ADMITTED_PRIVATE_SOURCE_BOUND_ACTIVITY":
            errors.append(f"raz_binding_admission_invalid:{binding_id}")

    m11b_ids = [str(row.get("activity_id") or "") for row in m11b if isinstance(row, Mapping)]
    if len(m11b_ids) != len(set(m11b_ids)) or "" in m11b_ids:
        errors.append("m11b_activity_identity_invalid")
    if any(
        row.get("admission_status") != "REUSED_EXISTING_REVIEWED_ADMISSION"
        for row in m11b
        if isinstance(row, Mapping)
    ):
        errors.append("m11b_admission_status_invalid")

    summary = payload.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("coverage_summary_required")
        summary = {}
    if summary.get("existing_learning_unit_count") != 24 or summary.get("new_learning_unit_count") != 0:
        errors.append("unit_summary_invalid")
    if summary.get("m11b_reused_activity_count") != len(m11b):
        errors.append("m11b_summary_count_mismatch")
    if summary.get("raz_materialized_source_count") != len(sources):
        errors.append("materialized_source_summary_count_mismatch")
    if summary.get("raz_admitted_activity_binding_count") != len(raz_bindings):
        errors.append("raz_admitted_binding_summary_count_mismatch")
    if summary.get("raz_candidate_binding_count") != (
        len(raz_bindings)
        + sum(
            1
            for row in remediation
            if isinstance(row, Mapping) and row.get("learning_unit_id")
        )
    ):
        errors.append("raz_binding_disposition_summary_mismatch")
    if summary.get("skill_binding_counts") != dict(sorted(skill_counts.items())):
        errors.append("skill_binding_counts_mismatch")
    cp04_summary = cp04_artifact.get("coverage_summary", {})
    if summary.get("cp04_content_candidate_count") != cp04_summary.get("content_candidate_count"):
        errors.append("cp04_content_count_not_reconciled")
    if summary.get("cp04_exercise_candidate_count") != cp04_summary.get("exercise_candidate_count"):
        errors.append("cp04_exercise_count_not_reconciled")

    boundaries = payload.get("claim_boundaries", {})
    if boundaries.get("objective_answer_fabricated") is not False:
        errors.append("objective_answer_claim_invalid")
    if boundaries.get("learner_runtime_publication_performed") is not False:
        errors.append("runtime_publication_claim_invalid")
    if boundaries.get("a2_a2plus_in_scope") is not False:
        errors.append("a2_scope_claim_invalid")
    if candidate.get("learner_facing") is not False:
        errors.append("candidate_learner_facing_forbidden")
    if candidate.get("admission", {}).get("status") != "PENDING_VALIDATION":
        errors.append("candidate_admission_status_invalid")

    return {
        "schema_version": "a1fs.v1.cp05.private_candidate_validation.v1",
        "task_id": TASK_ID,
        "validation_status": CANDIDATE_PASS_STATUS if not errors else "FAIL",
        "artifact_sha256": candidate.get("artifact_sha256"),
        "materialized_source_count": len(sources),
        "raz_admitted_activity_binding_count": len(raz_bindings),
        "m11b_reused_activity_count": len(m11b),
        "remediation_row_count": len(remediation),
        "skill_binding_counts": dict(sorted(skill_counts.items())),
        "error_count": len(errors),
        "errors": errors,
    }


def validate_release(
    candidate: Mapping[str, Any],
    approved: Mapping[str, Any],
    safe: Mapping[str, Any],
    *,
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    dedup_package: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    candidate_report = validate_candidate(
        candidate,
        cp04_artifact=cp04_artifact,
        registry_package=registry_package,
        dedup_package=dedup_package,
    )
    if candidate_report.get("validation_status") != CANDIDATE_PASS_STATUS:
        errors.extend(f"candidate:{error}" for error in candidate_report.get("errors", []))
    approved_report = envelope_validator.validate_artifact(
        approved, expected_role="APPROVED_CANONICAL_JSON"
    )
    errors.extend(f"approved:{error}" for error in approved_report.get("errors", []))
    if approved.get("payload") != candidate.get("payload"):
        errors.append("approved_payload_drift")
    if approved.get("source_bindings", {}).get("candidate_artifact_sha256") != candidate.get("artifact_sha256"):
        errors.append("approved_candidate_binding_mismatch")
    if approved.get("admission", {}).get("status") != "APPROVED":
        errors.append("approved_admission_status_invalid")
    if approved.get("learner_facing") is not False:
        errors.append("approved_canonical_must_not_be_runtime_facing")

    if safe.get("task_id") != TASK_ID:
        errors.append("safe_task_id_invalid")
    if safe.get("validation_status") != PASS_STATUS:
        errors.append("safe_validation_status_invalid")
    if safe.get("source_identity", {}).get("candidate_artifact_sha256") != candidate.get("artifact_sha256"):
        errors.append("safe_candidate_sha_mismatch")
    if safe.get("source_identity", {}).get("approved_artifact_sha256") != approved.get("artifact_sha256"):
        errors.append("safe_approved_sha_mismatch")
    if safe.get("coverage_summary") != approved.get("payload", {}).get("coverage_summary"):
        errors.append("safe_coverage_summary_drift")
    gate = safe.get("admission_gate", {})
    if gate.get("decision") != "PRIVATE_CANDIDATE_MATERIALIZATION_AND_ADMISSION_READY":
        errors.append("safe_admission_gate_invalid")
    if gate.get("runtime_publication_allowed") is not False:
        errors.append("safe_runtime_publication_must_be_false")
    if gate.get("a2_a2plus_status") != "LOCKED":
        errors.append("safe_a2_lock_invalid")
    errors.extend(_safe_leakage(safe))

    return {
        "schema_version": "a1fs.v1.cp05.private_candidate_materialization_admission_validation.v1",
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "candidate_validation_status": candidate_report.get("validation_status"),
        "approved_policy_envelope_error_count": approved_report.get("error_count"),
        "private_or_learner_content_absent_from_safe_readback": not _safe_leakage(safe),
        "coverage_summary": safe.get("coverage_summary", {}),
        "stop_reason": "NONE" if not errors else "CP05_VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else TASK_ID,
        "error_count": len(errors),
        "errors": errors,
    }


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--safe", type=Path, required=True)
    parser.add_argument("--cp04", type=Path, default=builder.DEFAULT_CP04)
    parser.add_argument("--raz-registry", type=Path, default=builder.DEFAULT_REGISTRY)
    parser.add_argument("--semantic-dedup", type=Path, default=builder.DEFAULT_DEDUP)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = validate_release(
        _read(args.candidate),
        _read(args.approved),
        _read(args.safe),
        cp04_artifact=_read(args.cp04),
        registry_package=_read(args.raz_registry),
        dedup_package=_read(args.semantic_dedup),
    )
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
