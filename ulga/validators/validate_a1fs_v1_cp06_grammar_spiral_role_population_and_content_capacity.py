#!/usr/bin/env python3
"""Validate CP06 grammar spiral roles and content-capacity reconciliation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as builder  # noqa: E402

TASK_ID = builder.TASK_ID
PASS_STATUS = builder.PASS_STATUS
FORBIDDEN_KEYS = {
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


def _safe_leakage(value: Any) -> list[str]:
    errors: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                child_path = f"{path}.{key}" if path else str(key)
                if str(key).casefold() in FORBIDDEN_KEYS:
                    errors.append(f"private_or_runtime_key_detected:{child_path}")
                walk(child, child_path)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")

    walk(value, "")
    return errors


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    cp05_approved: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    unit_contract_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        expected = builder.build_artifact(
            cp05_approved,
            cp04_artifact,
            registry_package,
            unit_contract_artifact,
        )
    except (builder.CP06BuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")
        expected = {}

    if artifact != expected:
        errors.append("artifact_does_not_match_deterministic_rebuild")
    if artifact.get("task_id") != TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_invalid")
    if artifact.get("stop_reason") != "NONE":
        errors.append("stop_reason_invalid")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")

    summary = artifact.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("coverage_summary_required")
        summary = {}
    if summary.get("existing_learning_unit_count") != 24:
        errors.append("existing_learning_unit_count_not_24")
    if summary.get("new_learning_unit_count") != 0:
        errors.append("new_learning_unit_detected")

    raz_rows = artifact.get("raz_activity_role_bindings")
    m11b_rows = artifact.get("m11b_activity_role_bindings")
    unit_rows = artifact.get("unit_content_capacity")
    if not isinstance(raz_rows, list):
        errors.append("raz_role_bindings_list_required")
        raz_rows = []
    if not isinstance(m11b_rows, list):
        errors.append("m11b_role_bindings_list_required")
        m11b_rows = []
    if not isinstance(unit_rows, list) or len(unit_rows) != 24:
        errors.append("unit_content_capacity_count_not_24")
        unit_rows = []

    if summary.get("raz_activity_binding_count") != len(raz_rows):
        errors.append("raz_activity_binding_count_mismatch")
    if summary.get("m11b_activity_count") != len(m11b_rows):
        errors.append("m11b_activity_count_mismatch")

    allowed_content_roles = set(builder.CONTENT_ROLES)
    for row in raz_rows:
        if not isinstance(row, Mapping):
            errors.append("raz_role_binding_row_invalid")
            continue
        roles = row.get("content_roles")
        evidence = row.get("role_evidence")
        lifecycle = row.get("lifecycle_role_contracts")
        if not isinstance(roles, list) or not roles or roles[0] != "FOCUS":
            errors.append("raz_focus_role_missing_or_not_first")
        elif not set(roles) <= allowed_content_roles or len(roles) != len(set(roles)):
            errors.append("raz_content_roles_invalid")
        if not isinstance(evidence, list) or {item.get("role") for item in evidence if isinstance(item, Mapping)} != set(roles or []):
            errors.append("raz_role_evidence_not_reconciled")
        if not isinstance(lifecycle, Mapping) or set(lifecycle) != set(builder.LIFECYCLE_ROLES):
            errors.append("raz_lifecycle_contract_invalid")
        elif any(
            lifecycle[role].get("runtime_activation_performed") is not False
            for role in ("REMEDIATION", "REASSESSMENT")
        ) or lifecycle["RETENTION"].get("runtime_schedule_created") is not False:
            errors.append("runtime_lifecycle_activation_fabricated")

    for row in m11b_rows:
        if not isinstance(row, Mapping):
            errors.append("m11b_role_binding_row_invalid")
            continue
        if row.get("content_roles") != ["FOCUS"]:
            errors.append("m11b_role_must_be_focus_only")

    unit_ids = [str(row.get("learning_unit_id") or "") for row in unit_rows if isinstance(row, Mapping)]
    if len(unit_ids) != 24 or len(set(unit_ids)) != 24 or "" in unit_ids:
        errors.append("unit_capacity_identity_invalid")
    if [row.get("sequence_index") for row in unit_rows if isinstance(row, Mapping)] != list(range(1, 25)):
        errors.append("unit_capacity_sequence_invalid")

    scene_count = sum(
        bool(row.get("scene_capacity", {}).get("effective_theme_situation_refs"))
        for row in unit_rows
        if isinstance(row, Mapping)
    )
    cp04_scene_count = sum(
        bool(row.get("scene_capacity", {}).get("cp04_theme_situation_refs"))
        for row in unit_rows
        if isinstance(row, Mapping)
    )
    text_count = sum(
        row.get("activity_capacity", {}).get("text_runtime_candidate_available") is True
        for row in unit_rows
        if isinstance(row, Mapping)
    )
    if summary.get("effective_scene_capacity_unit_count") != scene_count:
        errors.append("effective_scene_capacity_count_mismatch")
    if summary.get("cp04_scene_capacity_unit_count") != cp04_scene_count:
        errors.append("cp04_scene_capacity_count_mismatch")
    if summary.get("effective_scene_gap_unit_count") != 24 - scene_count:
        errors.append("effective_scene_gap_count_mismatch")
    if summary.get("text_runtime_candidate_unit_count") != text_count:
        errors.append("text_runtime_candidate_unit_count_mismatch")

    gate = artifact.get("capacity_gate", {})
    if gate.get("decision") != "GRAMMAR_SPIRAL_ROLES_AND_CONTENT_CAPACITY_READY":
        errors.append("capacity_gate_decision_invalid")
    if gate.get("runtime_publication_allowed") is not False:
        errors.append("runtime_publication_must_be_false")
    if gate.get("a2_a2plus_status") != "LOCKED":
        errors.append("a2_lock_invalid")

    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("private_source_text_included") is not False:
        errors.append("private_source_claim_invalid")
    if boundaries.get("runtime_role_activation_performed") is not False:
        errors.append("runtime_role_activation_claim_invalid")
    if boundaries.get("retention_result_claimed") is not False:
        errors.append("retention_claim_invalid")
    if boundaries.get("a2_a2plus_in_scope") is not False:
        errors.append("a2_scope_claim_invalid")

    errors.extend(_safe_leakage(artifact))
    return {
        "schema_version": "a1fs.v1.cp06.grammar_spiral_role_capacity_validation.v1",
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "coverage_summary": dict(summary),
        "private_or_runtime_content_absent": not _safe_leakage(artifact),
        "deterministic_rebuild_matches": artifact == expected,
        "error_count": len(errors),
        "errors": errors,
        "stop_reason": "NONE" if not errors else "CP06_VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else TASK_ID,
    }


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--cp05-approved", type=Path, default=builder.DEFAULT_CP05_APPROVED)
    parser.add_argument("--cp04", type=Path, default=builder.DEFAULT_CP04)
    parser.add_argument("--raz-registry", type=Path, default=builder.DEFAULT_REGISTRY)
    parser.add_argument("--unit-contract", type=Path, default=builder.DEFAULT_UNIT_CONTRACT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        cp05_approved=_read(args.cp05_approved),
        cp04_artifact=_read(args.cp04),
        registry_package=_read(args.raz_registry),
        unit_contract_artifact=_read(args.unit_contract),
    )
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
