#!/usr/bin/env python3
"""Validate RAZ ACL V1 S04 policy-bound metadata-only material candidates."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s04_policy_bound_asset_materialization as builder
from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as envelope

PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S04_POLICY_BOUND_ASSET_MATERIALIZATION_VALIDATION"


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    envelope_report = envelope.validate_artifact(
        candidate, expected_role=envelope.CANDIDATE_ROLE
    )
    errors.extend(f"envelope:{row}" for row in envelope_report["errors"])

    if candidate.get("producer_id") != builder.PRODUCER_ID:
        errors.append("producer_id_mismatch")
    if candidate.get("level_scope") != ["A1", "A1+"]:
        errors.append("level_scope_mismatch")
    if candidate.get("learner_facing") is not False:
        errors.append("candidate_must_not_be_learner_facing")

    source = candidate.get("source_bindings")
    if not isinstance(source, Mapping):
        errors.append("source_bindings_missing")
        source = {}
    for key in ("dedup_package_sha256", "linkage_package_sha256"):
        value = source.get(key)
        if not isinstance(value, str) or len(value) != 64:
            errors.append(f"source_binding_digest_invalid:{key}")
    if source.get("dedup_task_id") != builder.dedup.TASK_ID:
        errors.append("dedup_task_id_binding_invalid")
    if source.get("linkage_task_id") != builder.linkage.TASK_ID:
        errors.append("linkage_task_id_binding_invalid")

    payload = candidate.get("payload")
    if not isinstance(payload, Mapping):
        errors.append("payload_missing")
        payload = {}
    if payload.get("task_id") != builder.TASK_ID:
        errors.append("payload_task_id_mismatch")
    if payload.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("payload_schema_version_mismatch")
    if payload.get("validation_status") != builder.PASS_STATUS:
        errors.append("payload_validation_status_not_pass")
    gate = payload.get("materialization_gate")
    if not isinstance(gate, Mapping):
        errors.append("materialization_gate_missing")
        gate = {}
    if gate.get("decision") != "POLICY_BOUND_ASSET_CANDIDATES_READY":
        errors.append("materialization_gate_not_ready")
    if gate.get("distance_after") != "D2":
        errors.append("materialization_distance_not_d2")
    if gate.get("ready_for_candidate_consumer_integration") is not True:
        errors.append("candidate_consumer_integration_not_ready")
    if gate.get("ready_for_canonical_promotion") is not False:
        errors.append("canonical_promotion_must_remain_blocked")

    rows = payload.get("material_candidates")
    routed = payload.get("non_materialized_registry")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        errors.append("material_candidates_invalid")
        rows = []
    if not isinstance(routed, list) or not all(
        isinstance(row, Mapping) for row in routed
    ):
        errors.append("non_materialized_registry_invalid")
        routed = []

    candidate_ids = [str(row.get("material_candidate_id") or "") for row in rows]
    semantic_ids = [str(row.get("semantic_identity_id") or "") for row in rows]
    routed_ids = [str(row.get("semantic_identity_id") or "") for row in routed]
    if any(not value for value in candidate_ids) or len(candidate_ids) != len(
        set(candidate_ids)
    ):
        errors.append("material_candidate_id_missing_or_duplicate")
    if any(not value for value in semantic_ids + routed_ids):
        errors.append("semantic_identity_missing")
    if len(semantic_ids + routed_ids) != len(set(semantic_ids + routed_ids)):
        errors.append("semantic_identity_materialization_overlap")

    role_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        level = row.get("level")
        if level not in {"A1", "A1+"}:
            errors.append(f"candidate_level_invalid:{index}")
        else:
            level_counts[str(level)] += 1
        roles = row.get("material_roles")
        if not isinstance(roles, list) or not roles or len(roles) != len(set(roles)):
            errors.append(f"material_roles_invalid:{index}")
        else:
            role_counts.update(str(role) for role in roles)
            if "SENTENCE_CANDIDATE" not in roles:
                errors.append(f"sentence_candidate_role_missing:{index}")
        links = row.get("authority_links")
        if not isinstance(links, list) or not all(isinstance(link, Mapping) for link in links):
            errors.append(f"authority_links_invalid:{index}")
            links = []
        authority_types = {str(link.get("authority_type") or "") for link in links}
        if not {"VOCABULARY", "GRAMMAR"} <= authority_types:
            errors.append(f"required_authority_links_missing:{index}")
        if row.get("authority_link_count") != len(links):
            errors.append(f"authority_link_count_mismatch:{index}")
        if row.get("content_payload_state") != (
            "TEXT_NOT_EMBEDDED_CONTROLLED_REWRITE_REQUIRED"
        ):
            errors.append(f"content_payload_state_invalid:{index}")
        if row.get("candidate_validation_status") != "PENDING_VALIDATION":
            errors.append(f"candidate_validation_status_invalid:{index}")
        if row.get("canonical_admission_status") != "NOT_ADMITTED":
            errors.append(f"canonical_admission_fabricated:{index}")
        if row.get("learner_facing") is not False:
            errors.append(f"learner_facing_candidate_detected:{index}")
        lineage = row.get("source_lineage")
        if not isinstance(lineage, Mapping):
            errors.append(f"source_lineage_missing:{index}")
        else:
            if lineage.get("dedup_package_sha256") != source.get(
                "dedup_package_sha256"
            ):
                errors.append(f"dedup_lineage_mismatch:{index}")
            if lineage.get("linkage_package_sha256") != source.get(
                "linkage_package_sha256"
            ):
                errors.append(f"linkage_lineage_mismatch:{index}")

    allowed_routes = set(builder.NON_MATERIALIZED_ROUTES.values())
    for index, row in enumerate(routed):
        if row.get("resolution_route") not in allowed_routes:
            errors.append(f"resolution_route_invalid:{index}")
        if row.get("representative_admission_status") in builder.READY_STATUSES:
            errors.append(f"ready_candidate_routed_out:{index}")

    summary = payload.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        errors.append("aggregate_summary_missing")
        summary = {}
    if summary.get("materialized_candidate_count") != len(rows):
        errors.append("materialized_candidate_count_mismatch")
    if summary.get("non_materialized_count") != len(routed):
        errors.append("non_materialized_count_mismatch")
    if summary.get("semantic_identity_count") != len(rows) + len(routed):
        errors.append("semantic_identity_count_mismatch")
    if summary.get("level_candidate_counts") != dict(sorted(level_counts.items())):
        errors.append("level_candidate_counts_mismatch")
    if summary.get("material_role_counts") != dict(sorted(role_counts.items())):
        errors.append("material_role_counts_mismatch")
    if summary.get("canonical_admitted_material_count") != 0:
        errors.append("canonical_admitted_material_count_not_zero")
    if summary.get("learner_facing_material_count") != 0:
        errors.append("learner_facing_material_count_not_zero")
    if summary.get("deferred_a2_a2plus_count") != source.get(
        "deferred_a2_a2plus_count"
    ):
        errors.append("deferred_a2_a2plus_count_binding_mismatch")
    if source.get("semantic_identity_count") != summary.get("semantic_identity_count"):
        errors.append("semantic_identity_source_binding_mismatch")
    if source.get("materialized_candidate_count") != len(rows):
        errors.append("materialized_candidate_source_binding_mismatch")

    leakage = matching.scan_forbidden_safe_keys(candidate)
    errors.extend(f"safe_output:{row}" for row in leakage)
    return {
        "task_id": builder.TASK_ID,
        "schema_version": (
            "raz.ai.acl.v1.s04.policy_bound_asset_materialization_validation.v1"
        ),
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "artifact_sha256": candidate.get("artifact_sha256"),
        "materialized_candidate_count": len(rows),
        "non_materialized_count": len(routed),
        "level_candidate_counts": dict(sorted(level_counts.items())),
        "material_role_counts": dict(sorted(role_counts.items())),
        "a2_unlocked": False,
        "canonical_promotion_performed": False,
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if not isinstance(candidate, Mapping):
        raise ValueError("candidate_object_required")
    report = validate_candidate(candidate)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
