#!/usr/bin/env python3
"""Bind each S02 semantic representative to its verified Authority references.

S03 consumes only the text-free S02 package.  It preserves the selected source
identity, material classification, and A2/A2+ deferral while turning the
matched reference lists into an explicit, deterministic linkage registry.
It does not read source text, mutate canonical Authority, or promote material.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S03_AuthorityLinkageAndConflictGate"
SCHEMA_VERSION = "raz.ai.acl.v1.s03.authority_linkage_conflict_gate.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S03_AUTHORITY_LINKAGE_CONFLICT_GATE"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_DEDUP = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s02_semantic_dedup/"
    "semantic_dedup_representative_selection.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s03_authority_linkage/"
    "authority_linkage_conflict_gate.safe.json"
)

REFERENCE_FIELDS = (
    ("THEME", "candidate_theme_refs"),
    ("VOCABULARY", "matched_vocabulary_refs"),
    ("CHUNK", "matched_chunk_refs"),
    ("PATTERN", "matched_pattern_refs"),
    ("GRAMMAR", "matched_grammar_unit_refs"),
)
READY_STATUSES = {"A1_READY_CANDIDATE", "A1PLUS_READY_CANDIDATE"}
LINKAGE_STATUS_BY_ADMISSION = {
    "A1_READY_CANDIDATE": "AUTHORITY_LINKED_A1_READY",
    "A1PLUS_READY_CANDIDATE": "AUTHORITY_LINKED_A1PLUS_READY",
    "REWRITE_REQUIRED": "AUTHORITY_LINKED_REWRITE_REQUIRED",
    "SUPPORT_ONLY": "AUTHORITY_LINKED_SUPPORT_ONLY",
    "REJECTED_UNUSABLE": "REJECTED_NOT_PROMOTABLE",
}

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "raz_level_used_as_cefr_equivalence": False,
    "existing_authority_refs_linked": True,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "material_promotion_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class AuthorityLinkageError(ValueError):
    """Fail-closed S02 lineage, accounting, or Authority linkage error."""


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise AuthorityLinkageError("dedup_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise AuthorityLinkageError("dedup_package_sha256_mismatch")


def _list_of_strings(row: Mapping[str, Any], key: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise AuthorityLinkageError(f"representative_reference_list_invalid:{key}")
    if len(value) != len(set(value)):
        raise AuthorityLinkageError(f"representative_reference_list_duplicate:{key}")
    return sorted(value)


def _verify_dedup(
    package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if package.get("task_id") != dedup.TASK_ID:
        raise AuthorityLinkageError("dedup_task_id_mismatch")
    if package.get("validation_status") != dedup.PASS_STATUS:
        raise AuthorityLinkageError("dedup_validation_status_not_pass")
    if package.get("errors") != []:
        raise AuthorityLinkageError("dedup_errors_not_empty")
    _verify_hash(package)
    gate = package.get("dedup_gate")
    if (
        not isinstance(gate, Mapping)
        or gate.get("decision") != "SEMANTIC_DEDUP_REPRESENTATIVES_READY"
        or gate.get("ready_for_authority_linkage") is not True
    ):
        raise AuthorityLinkageError("dedup_gate_not_ready_for_authority_linkage")
    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise AuthorityLinkageError("dedup_aggregate_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "representative_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "final_promoted_material_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise AuthorityLinkageError(
                f"dedup_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )
    representatives = package.get("semantic_representatives")
    bindings = package.get("duplicate_bindings")
    if not isinstance(representatives, list) or not all(
        isinstance(row, Mapping) for row in representatives
    ):
        raise AuthorityLinkageError("semantic_representatives_invalid")
    if not isinstance(bindings, list) or not all(
        isinstance(row, Mapping) for row in bindings
    ):
        raise AuthorityLinkageError("duplicate_bindings_invalid")
    if len(representatives) != expected_semantic_identity_count:
        raise AuthorityLinkageError("semantic_representative_count_mismatch")
    if len(bindings) != expected_duplicate_binding_count:
        raise AuthorityLinkageError("duplicate_binding_count_mismatch")
    return representatives, bindings


def build_package(
    dedup_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    representatives, bindings = _verify_dedup(
        dedup_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    linkage_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    authority_type_counts: Counter[str] = Counter()
    seen_groups: set[str] = set()
    seen_refs: set[str] = set()
    conflicts: list[dict[str, str]] = []

    for row in sorted(
        representatives, key=lambda item: str(item.get("semantic_duplicate_group_id"))
    ):
        group = str(row.get("semantic_duplicate_group_id") or "")
        source_ref = str(row.get("selected_source_unit_ref") or "")
        admission_status = str(row.get("representative_admission_status") or "")
        scope = str(row.get("candidate_cefr_scope") or "")
        if not group or group in seen_groups:
            raise AuthorityLinkageError("semantic_group_missing_or_duplicate")
        if not source_ref or source_ref in seen_refs:
            raise AuthorityLinkageError("representative_source_ref_missing_or_duplicate")
        if admission_status not in LINKAGE_STATUS_BY_ADMISSION:
            raise AuthorityLinkageError(
                f"representative_admission_status_invalid:{source_ref}:{admission_status}"
            )
        if scope not in {"A1", "A1_PLUS", "NONE"}:
            raise AuthorityLinkageError(
                f"candidate_cefr_scope_invalid:{source_ref}:{scope}"
            )
        seen_groups.add(group)
        seen_refs.add(source_ref)

        links: list[dict[str, str]] = []
        refs_by_type: dict[str, list[str]] = {}
        ownership: dict[str, str] = {}
        for authority_type, field in REFERENCE_FIELDS:
            refs = _list_of_strings(row, field)
            refs_by_type[authority_type] = refs
            authority_type_counts[authority_type] += len(refs)
            for authority_ref in refs:
                prior = ownership.get(authority_ref)
                if prior and prior != authority_type:
                    conflicts.append(
                        {
                            "selected_source_unit_ref": source_ref,
                            "authority_ref": authority_ref,
                            "first_authority_type": prior,
                            "second_authority_type": authority_type,
                        }
                    )
                ownership[authority_ref] = authority_type
                links.append(
                    {
                        "authority_type": authority_type,
                        "authority_ref": authority_ref,
                        "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
                    }
                )

        if admission_status in READY_STATUSES and (
            not refs_by_type["VOCABULARY"] or not refs_by_type["GRAMMAR"]
        ):
            raise AuthorityLinkageError(
                f"ready_representative_missing_required_authority:{source_ref}"
            )
        linkage_status = LINKAGE_STATUS_BY_ADMISSION[admission_status]
        status_counts[linkage_status] += 1
        linkage_rows.append(
            {
                "semantic_duplicate_group_id": group,
                "selected_source_unit_ref": source_ref,
                "source_level": str(row.get("source_level") or ""),
                "source_book_id": str(row.get("source_book_id") or ""),
                "representative_admission_status": admission_status,
                "candidate_cefr_scope": scope,
                "authority_links": sorted(
                    links, key=lambda item: (item["authority_type"], item["authority_ref"])
                ),
                "authority_link_count": len(links),
                "authority_linkage_status": linkage_status,
                "promotion_status": "NOT_PROMOTED",
            }
        )

    binding_representatives = {
        str(row.get("representative_source_unit_ref") or "") for row in bindings
    }
    checks = {
        "one_linkage_row_per_semantic_identity": (
            len(linkage_rows) == expected_semantic_identity_count
            and len(seen_groups) == expected_semantic_identity_count
            and len(seen_refs) == expected_semantic_identity_count
        ),
        "duplicate_bindings_target_selected_representatives": (
            binding_representatives <= seen_refs
            and len(bindings) == expected_duplicate_binding_count
        ),
        "ready_rows_have_vocabulary_and_grammar_links": all(
            {link["authority_type"] for link in row["authority_links"]}
            >= {"VOCABULARY", "GRAMMAR"}
            for row in linkage_rows
            if row["representative_admission_status"] in READY_STATUSES
        ),
        "authority_reference_type_conflicts_absent": not conflicts,
        "a2_a2plus_not_opened": all(
            row["candidate_cefr_scope"] not in {"A2", "A2_PLUS"}
            for row in linkage_rows
        ),
        "no_material_promoted": all(
            row["promotion_status"] == "NOT_PROMOTED" for row in linkage_rows
        ),
        "linkage_status_counts_reconcile": (
            sum(status_counts.values()) == expected_semantic_identity_count
        ),
    }
    ready = all(checks.values())
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "dedup_task_id": dedup_package["task_id"],
            "dedup_package_sha256": dedup_package["package_sha256"],
        },
        "scope_contract": {
            "a1_a1plus_observational_levels": list(
                dedup_package["scope_contract"]["a1_a1plus_observational_levels"]
            ),
            "deferred_levels": list(dedup_package["scope_contract"]["deferred_levels"]),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "authority_linkage_rows": linkage_rows,
        "duplicate_bindings": [dict(row) for row in bindings],
        "authority_reference_type_conflicts": conflicts,
        "aggregate_summary": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": len(linkage_rows),
            "representative_count": len(linkage_rows),
            "duplicate_binding_count": len(bindings),
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "authority_link_count": sum(
                row["authority_link_count"] for row in linkage_rows
            ),
            "authority_type_link_counts": dict(sorted(authority_type_counts.items())),
            "authority_linkage_status_counts": dict(sorted(status_counts.items())),
            "authority_reference_type_conflict_count": len(conflicts),
            "final_promoted_material_count": 0,
        },
        "authority_linkage_gate": {
            "source_checks": checks,
            "decision": "AUTHORITY_LINKAGE_READY" if ready else "BLOCKED_AUTHORITY_LINKAGE",
            "distance_before": "D4",
            "distance_after": "D3" if ready else "D4",
            "ready_for_rewrite_and_admission_resolution": ready,
            "ready_for_material_promotion": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise AuthorityLinkageError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["authority_linkage_gate"]["decision"],
        "distance_after": package["authority_linkage_gate"]["distance_after"],
        **package["aggregate_summary"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dedup-package", type=Path, default=DEFAULT_DEDUP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.dedup_package)
        if not isinstance(package, Mapping):
            raise AuthorityLinkageError("dedup_package_not_object")
        output = build_package(package)
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (AuthorityLinkageError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
