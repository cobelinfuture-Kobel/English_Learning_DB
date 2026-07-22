#!/usr/bin/env python3
"""Materialize S03-linked RAZ representatives as policy-bound A1/A1+ candidates.

The builder never copies RAZ source text.  It converts verified semantic
representatives and Authority links into deterministic metadata-only Candidate
JSON under the existing A1FS canonical-content governance policy.  Learner-
facing text, canonical admission, and A2/A2+ processing remain blocked.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S04_PolicyBoundAssetMaterialization"
SCHEMA_VERSION = "raz.ai.acl.v1.s04.policy_bound_asset_materialization.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S04_POLICY_BOUND_ASSET_MATERIALIZATION"
PRODUCER_ID = "build_raz_ai_acl_v1_s04_policy_bound_asset_materialization"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_DEDUP = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s02_semantic_dedup/"
    / "semantic_dedup_representative_selection.safe.json"
)
DEFAULT_LINKAGE = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s03_authority_linkage/"
    / "authority_linkage_conflict_gate.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s04_policy_bound_materialization/"
    / "raz_ai_acl_v1_material_candidates.private.json"
)

READY_STATUSES = {"A1_READY_CANDIDATE", "A1PLUS_READY_CANDIDATE"}
NON_MATERIALIZED_ROUTES = {
    "REWRITE_REQUIRED": "CONTROLLED_REWRITE_QUEUE",
    "SUPPORT_ONLY": "TEACHER_SUPPORT_REGISTRY",
    "REJECTED_UNUSABLE": "EXCLUDED_FROM_MATERIALIZATION",
}
SKILL_ROLE_MAP = {
    "READING_SOURCE": "READING_SOURCE_CANDIDATE",
    "LISTENING_ADAPTATION": "LISTENING_ADAPTATION_CANDIDATE",
    "SPEAKING_PROMPT": "SPEAKING_PROMPT_CANDIDATE",
    "WRITING_MODEL": "WRITING_MODEL_CANDIDATE",
}
CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "metadata_only_candidate_materialization": True,
    "controlled_rewrite_required_before_learner_facing_use": True,
    "canonical_authority_write_performed": False,
    "canonical_material_admission_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_processing_performed": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class AssetMaterializationError(ValueError):
    """Fail-closed S04 lineage, accounting, policy, or privacy error."""


def _verify_package_hash(package: Mapping[str, Any], label: str) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise AssetMaterializationError(f"{label}_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise AssetMaterializationError(f"{label}_package_sha256_mismatch")


def _verify_inputs(
    dedup_package: Mapping[str, Any],
    linkage_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if dedup_package.get("task_id") != dedup.TASK_ID:
        raise AssetMaterializationError("dedup_task_id_mismatch")
    if dedup_package.get("validation_status") != dedup.PASS_STATUS:
        raise AssetMaterializationError("dedup_validation_status_not_pass")
    if dedup_package.get("errors") != []:
        raise AssetMaterializationError("dedup_errors_not_empty")
    _verify_package_hash(dedup_package, "dedup")
    dedup_gate = dedup_package.get("dedup_gate")
    if not isinstance(dedup_gate, Mapping) or dedup_gate.get("decision") != (
        "SEMANTIC_DEDUP_REPRESENTATIVES_READY"
    ) or dedup_gate.get("ready_for_authority_linkage") is not True:
        raise AssetMaterializationError("dedup_gate_not_ready")

    if linkage_package.get("task_id") != linkage.TASK_ID:
        raise AssetMaterializationError("linkage_task_id_mismatch")
    if linkage_package.get("validation_status") != linkage.PASS_STATUS:
        raise AssetMaterializationError("linkage_validation_status_not_pass")
    if linkage_package.get("errors") != []:
        raise AssetMaterializationError("linkage_errors_not_empty")
    _verify_package_hash(linkage_package, "linkage")
    linkage_gate = linkage_package.get("authority_linkage_gate")
    if not isinstance(linkage_gate, Mapping) or linkage_gate.get("decision") != (
        "AUTHORITY_LINKAGE_READY"
    ) or linkage_gate.get("ready_for_rewrite_and_admission_resolution") is not True:
        raise AssetMaterializationError("linkage_gate_not_ready")
    identity = linkage_package.get("input_identity")
    if not isinstance(identity, Mapping) or identity.get("dedup_package_sha256") != (
        dedup_package.get("package_sha256")
    ):
        raise AssetMaterializationError("linkage_dedup_identity_mismatch")

    expected_summary = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "representative_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "final_promoted_material_count": 0,
    }
    for label, package in (("dedup", dedup_package), ("linkage", linkage_package)):
        summary = package.get("aggregate_summary")
        if not isinstance(summary, Mapping):
            raise AssetMaterializationError(f"{label}_summary_missing")
        for key, expected in expected_summary.items():
            if summary.get(key) != expected:
                raise AssetMaterializationError(
                    f"{label}_summary_mismatch:{key}:{summary.get(key)}:{expected}"
                )

    representatives = dedup_package.get("semantic_representatives")
    linkage_rows = linkage_package.get("authority_linkage_rows")
    if not isinstance(representatives, list) or not all(
        isinstance(row, Mapping) for row in representatives
    ):
        raise AssetMaterializationError("semantic_representatives_invalid")
    if not isinstance(linkage_rows, list) or not all(
        isinstance(row, Mapping) for row in linkage_rows
    ):
        raise AssetMaterializationError("authority_linkage_rows_invalid")
    if len(representatives) != expected_semantic_identity_count:
        raise AssetMaterializationError("semantic_representative_count_mismatch")
    if len(linkage_rows) != expected_semantic_identity_count:
        raise AssetMaterializationError("authority_linkage_row_count_mismatch")
    return representatives, linkage_rows


def _material_roles(row: Mapping[str, Any]) -> list[str]:
    roles = {"SENTENCE_CANDIDATE"}
    maturity = str(row.get("sentence_seed_maturity") or "")
    if maturity == "STRICT_CORE_SENTENCE_SEED":
        roles.add("STRICT_CORE_SENTENCE_CANDIDATE")
    elif maturity == "BROAD_CORE_SENTENCE_SEED":
        roles.add("BROAD_CORE_SENTENCE_CANDIDATE")
    if row.get("passage_seed_status") == "SUPPORTED":
        roles.add("PASSAGE_CANDIDATE")
    affordances = row.get("four_skill_affordances")
    if not isinstance(affordances, list):
        raise AssetMaterializationError("four_skill_affordances_invalid")
    for affordance in affordances:
        mapped = SKILL_ROLE_MAP.get(str(affordance))
        if mapped:
            roles.add(mapped)
    return sorted(roles)


def _asset_id(group: str) -> str:
    suffix = "".join(char for char in group if char.isalnum() or char == "_")
    if not suffix:
        raise AssetMaterializationError("semantic_identity_invalid_for_asset_id")
    return f"RAZ_AI_ACL_{suffix}"


def build_candidate(
    dedup_package: Mapping[str, Any],
    linkage_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    representatives, linkage_rows = _verify_inputs(
        dedup_package,
        linkage_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    rep_by_group = {
        str(row.get("semantic_duplicate_group_id") or ""): row
        for row in representatives
    }
    link_by_group = {
        str(row.get("semantic_duplicate_group_id") or ""): row
        for row in linkage_rows
    }
    if "" in rep_by_group or len(rep_by_group) != len(representatives):
        raise AssetMaterializationError("representative_group_missing_or_duplicate")
    if "" in link_by_group or len(link_by_group) != len(linkage_rows):
        raise AssetMaterializationError("linkage_group_missing_or_duplicate")
    if set(rep_by_group) != set(link_by_group):
        raise AssetMaterializationError("representative_linkage_group_mismatch")

    candidates: list[dict[str, Any]] = []
    routed_rows: list[dict[str, str]] = []
    role_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()

    for group in sorted(rep_by_group):
        representative = rep_by_group[group]
        linked = link_by_group[group]
        source_ref = str(representative.get("selected_source_unit_ref") or "")
        if source_ref != linked.get("selected_source_unit_ref"):
            raise AssetMaterializationError(
                f"representative_linkage_source_ref_mismatch:{group}"
            )
        status = str(representative.get("representative_admission_status") or "")
        scope = str(representative.get("candidate_cefr_scope") or "")
        if status in READY_STATUSES:
            if scope not in {"A1", "A1_PLUS"}:
                raise AssetMaterializationError(
                    f"ready_candidate_scope_invalid:{source_ref}:{scope}"
                )
            links = linked.get("authority_links")
            if not isinstance(links, list) or not all(
                isinstance(item, Mapping) for item in links
            ):
                raise AssetMaterializationError(
                    f"authority_links_invalid:{source_ref}"
                )
            authority_types = {str(item.get("authority_type") or "") for item in links}
            if not {"VOCABULARY", "GRAMMAR"} <= authority_types:
                raise AssetMaterializationError(
                    f"ready_candidate_required_authority_missing:{source_ref}"
                )
            roles = _material_roles(representative)
            role_counts.update(roles)
            normalized_level = "A1+" if scope == "A1_PLUS" else "A1"
            level_counts[normalized_level] += 1
            candidates.append(
                {
                    "material_candidate_id": _asset_id(group),
                    "semantic_identity_id": group,
                    "source_unit_ref": source_ref,
                    "source_level": str(representative.get("source_level") or ""),
                    "level": normalized_level,
                    "material_roles": roles,
                    "authority_links": [dict(item) for item in links],
                    "authority_link_count": len(links),
                    "content_payload_state": (
                        "TEXT_NOT_EMBEDDED_CONTROLLED_REWRITE_REQUIRED"
                    ),
                    "candidate_validation_status": "PENDING_VALIDATION",
                    "canonical_admission_status": "NOT_ADMITTED",
                    "learner_facing": False,
                    "source_lineage": {
                        "dedup_package_sha256": dedup_package["package_sha256"],
                        "linkage_package_sha256": linkage_package["package_sha256"],
                    },
                }
            )
        else:
            route = NON_MATERIALIZED_ROUTES.get(status)
            if route is None:
                raise AssetMaterializationError(
                    f"representative_status_unhandled:{source_ref}:{status}"
                )
            route_counts[route] += 1
            routed_rows.append(
                {
                    "semantic_identity_id": group,
                    "source_unit_ref": source_ref,
                    "representative_admission_status": status,
                    "resolution_route": route,
                }
            )

    candidate_ids = [row["material_candidate_id"] for row in candidates]
    ready_expected = sum(
        str(row.get("representative_admission_status") or "") in READY_STATUSES
        for row in representatives
    )
    checks = {
        "all_semantic_identities_resolved": (
            len(candidates) + len(routed_rows) == expected_semantic_identity_count
        ),
        "ready_representatives_materialized_once": (
            len(candidates) == ready_expected
            and len(candidate_ids) == len(set(candidate_ids))
        ),
        "non_ready_representatives_routed_once": (
            len(routed_rows) == expected_semantic_identity_count - ready_expected
        ),
        "all_candidates_have_vocabulary_and_grammar": all(
            {link["authority_type"] for link in row["authority_links"]}
            >= {"VOCABULARY", "GRAMMAR"}
            for row in candidates
        ),
        "all_candidates_have_material_roles": all(
            row["material_roles"] for row in candidates
        ),
        "all_candidates_text_free_and_not_learner_facing": all(
            row["content_payload_state"]
            == "TEXT_NOT_EMBEDDED_CONTROLLED_REWRITE_REQUIRED"
            and row["learner_facing"] is False
            for row in candidates
        ),
        "a2_a2plus_not_materialized": all(
            row["level"] in {"A1", "A1+"} for row in candidates
        ),
        "canonical_admission_not_fabricated": all(
            row["canonical_admission_status"] == "NOT_ADMITTED"
            for row in candidates
        ),
    }
    ready = all(checks.values())
    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "program_id": "RAZ-AI-ACL-V1",
        "material_candidates": candidates,
        "non_materialized_registry": routed_rows,
        "aggregate_summary": {
            "semantic_identity_count": expected_semantic_identity_count,
            "materialized_candidate_count": len(candidates),
            "non_materialized_count": len(routed_rows),
            "level_candidate_counts": dict(sorted(level_counts.items())),
            "material_role_counts": dict(sorted(role_counts.items())),
            "resolution_route_counts": dict(sorted(route_counts.items())),
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "canonical_admitted_material_count": 0,
            "learner_facing_material_count": 0,
        },
        "materialization_gate": {
            "source_checks": checks,
            "decision": (
                "POLICY_BOUND_ASSET_CANDIDATES_READY"
                if ready else "BLOCKED_POLICY_BOUND_ASSET_MATERIALIZATION"
            ),
            "distance_before": "D3",
            "distance_after": "D2" if ready else "D3",
            "ready_for_candidate_consumer_integration": ready,
            "ready_for_canonical_promotion": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(payload)
    if leakage:
        raise AssetMaterializationError(
            "safe_output_leakage:" + ";".join(leakage[:20])
        )
    return policy.build_candidate(
        payload=payload,
        producer_id=PRODUCER_ID,
        level_scope=["A1", "A1+"],
        source_bindings={
            "dedup_task_id": dedup_package["task_id"],
            "dedup_package_sha256": dedup_package["package_sha256"],
            "linkage_task_id": linkage_package["task_id"],
            "linkage_package_sha256": linkage_package["package_sha256"],
            "semantic_identity_count": expected_semantic_identity_count,
            "materialized_candidate_count": len(candidates),
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        },
    )


def _readback(candidate: Mapping[str, Any]) -> dict[str, Any]:
    payload = candidate["payload"]
    return {
        "task_id": TASK_ID,
        "artifact_role": candidate["artifact_role"],
        "artifact_sha256": candidate["artifact_sha256"],
        "decision": payload["materialization_gate"]["decision"],
        "distance_after": payload["materialization_gate"]["distance_after"],
        **payload["aggregate_summary"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dedup-package", type=Path, default=DEFAULT_DEDUP)
    parser.add_argument("--linkage-package", type=Path, default=DEFAULT_LINKAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        dedup_package = deep.read_json(args.dedup_package)
        linkage_package = deep.read_json(args.linkage_package)
        if not isinstance(dedup_package, Mapping):
            raise AssetMaterializationError("dedup_package_not_object")
        if not isinstance(linkage_package, Mapping):
            raise AssetMaterializationError("linkage_package_not_object")
        candidate = build_candidate(dedup_package, linkage_package)
        deep.write_json_atomic(args.output, candidate)
        print(json.dumps(_readback(candidate), sort_keys=True))
        return 0
    except (
        AssetMaterializationError,
        policy.ContentPolicyBuildError,
        dedup.SemanticDedupError,
        linkage.AuthorityLinkageError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
