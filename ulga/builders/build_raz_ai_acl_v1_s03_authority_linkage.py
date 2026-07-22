#!/usr/bin/env python3
"""Bind S02 semantic representatives to verified canonical Authority records.

S03 consumes the text-free S02 package and validates every Theme, Vocabulary,
Chunk, Pattern, and Grammar reference against its authoritative registry.  The
three operator-approved Theme candidates are resolved only after their source
catalog records exist.  No source text is read and no material is promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_a1_a1plus_coverage_recheck as coverage
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S03_CanonicalAuthorityAndAssetRoleLinkage"
SCHEMA_VERSION = "raz.ai.acl.v1.s03.canonical_authority_asset_role_linkage.v2"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S03_CANONICAL_AUTHORITY_ASSET_ROLE_LINKAGE"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_DEDUP = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s02_semantic_dedup/"
    "semantic_dedup_representative_selection.safe.json"
)
DEFAULT_THEME_CATALOG = REPO_ROOT / "themes/theme_catalog.json"
DEFAULT_GRAMMAR_COVERAGE = (
    REPO_ROOT / "ulga/graph/a1_grammar_full_teachable_candidate_coverage.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s03_authority_linkage/"
    "canonical_authority_asset_role_linkage.safe.json"
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
    "A1_READY_CANDIDATE": "CANONICAL_LINKED_A1_READY",
    "A1PLUS_READY_CANDIDATE": "CANONICAL_LINKED_A1PLUS_READY",
    "REWRITE_REQUIRED": "CANONICAL_LINKED_REWRITE_REQUIRED",
    "SUPPORT_ONLY": "CANONICAL_LINKED_SUPPORT_ONLY",
    "REJECTED_UNUSABLE": "REJECTED_NOT_PROMOTABLE",
}
SKILL_ROLE_MAP = {
    "READING_SOURCE": "READING_SOURCE_ASSET",
    "LISTENING_ADAPTATION": "LISTENING_ADAPTATION_SEED",
    "SPEAKING_PROMPT": "SPEAKING_PROMPT_SEED",
    "WRITING_MODEL": "WRITING_MODEL_SEED",
}

APPROVED_THEME_CANONICAL_MAP = {
    candidate: "theme:" + candidate.split(":", 1)[1]
    for action in coverage.APPROVED_THEME_ACTIONS
    if action["decision"] == "APPROVE" and action["action"] == "ADD_A1_THEME"
    for candidate in action["candidate_target_refs"]
    if candidate.startswith("theme_candidate:")
}
EXPECTED_APPROVED_THEME_MAP = {
    "theme_candidate:a1_animals_and_habitats": "theme:a1_animals_and_habitats",
    "theme_candidate:a1_nature_and_environment": "theme:a1_nature_and_environment",
    "theme_candidate:a1_holidays_and_culture": "theme:a1_holidays_and_culture",
}
if APPROVED_THEME_CANONICAL_MAP != EXPECTED_APPROVED_THEME_MAP:
    raise RuntimeError("approved_theme_mapping_contract_drift")

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "raz_level_used_as_cefr_equivalence": False,
    "authority_registry_existence_validated": True,
    "operator_approved_theme_mount_consumed": True,
    "canonical_authority_write_performed_by_this_builder": False,
    "authority_promotion_performed_by_this_builder": False,
    "material_promotion_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class AuthorityLinkageError(ValueError):
    """Fail-closed S02 lineage, Authority registry, or linkage error."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _theme_catalog(path: Path) -> tuple[set[str], dict[str, Any]]:
    payload = deep.read_json(path)
    rows = payload.get("themes") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise AuthorityLinkageError("theme_catalog_invalid")
    ids = {
        "theme:" + str(row.get("theme_id"))
        for row in rows
        if row.get("level") in {"A1", "A1_plus"}
        and isinstance(row.get("theme_id"), str)
        and row.get("theme_id")
    }
    if len(ids) != 13:
        raise AuthorityLinkageError(f"a1_a1plus_theme_count_invalid:{len(ids)}")
    required = set(EXPECTED_APPROVED_THEME_MAP.values()) | {
        "theme:a1_personal_information_and_greetings"
    }
    if not required <= ids:
        raise AuthorityLinkageError(
            "approved_theme_mount_missing:" + ",".join(sorted(required - ids))
        )
    return ids, {
        "source_path": path.relative_to(REPO_ROOT).as_posix()
        if path.is_relative_to(REPO_ROOT) else str(path),
        "source_sha256": _sha256_file(path),
        "a1_a1plus_id_count": len(ids),
    }


def _grammar_registry(path: Path) -> tuple[set[str], dict[str, Any], dict[str, list[str]]]:
    payload = deep.read_json(path)
    rows = payload.get("learning_units") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise AuthorityLinkageError("grammar_learning_units_invalid")
    mapping: dict[str, list[str]] = {}
    for row in rows:
        unit_id = row.get("grammar_unit_id") or row.get("learning_unit_id") or row.get("id")
        egp = row.get("canonical_egp_row_ids")
        if not isinstance(unit_id, str) or not unit_id:
            raise AuthorityLinkageError("grammar_unit_id_invalid")
        if not isinstance(egp, list) or not all(isinstance(value, str) and value for value in egp):
            raise AuthorityLinkageError(f"grammar_egp_rows_invalid:{unit_id}")
        mapping[unit_id] = sorted(set(egp))
    ids = set(mapping)
    expected = set(deep.UNIT_IDS)
    if ids != expected:
        raise AuthorityLinkageError(
            "grammar_unit_registry_mismatch:" + ",".join(sorted(ids ^ expected))
        )
    return ids, {
        "source_path": path.relative_to(REPO_ROOT).as_posix()
        if path.is_relative_to(REPO_ROOT) else str(path),
        "source_sha256": _sha256_file(path),
        "unit_count": len(ids),
        "canonical_egp_row_count": len({value for values in mapping.values() for value in values}),
    }, mapping


def load_authority_registry(
    *, theme_catalog_path: Path = DEFAULT_THEME_CATALOG,
    grammar_coverage_path: Path = DEFAULT_GRAMMAR_COVERAGE,
) -> tuple[dict[str, set[str]], dict[str, Any], dict[str, list[str]]]:
    matched = deep.load_authorities()
    themes, theme_identity = _theme_catalog(theme_catalog_path)
    grammar, grammar_identity, grammar_to_egp = _grammar_registry(grammar_coverage_path)
    registry = {
        "THEME": themes,
        "VOCABULARY": set(matched["vocabulary"]["ids"]),
        "CHUNK": set(matched["chunks"]["ids"]),
        "PATTERN": set(matched["patterns"]["ids"]),
        "GRAMMAR": grammar,
    }
    identity = {
        "THEME": theme_identity,
        "VOCABULARY": {
            "source_path": matched["vocabulary"]["source_path"],
            "source_sha256": matched["vocabulary"]["source_sha256"],
            "id_count": len(registry["VOCABULARY"]),
        },
        "CHUNK": {
            "source_path": matched["chunks"]["source_path"],
            "source_sha256": matched["chunks"]["source_sha256"],
            "id_count": len(registry["CHUNK"]),
        },
        "PATTERN": {
            "source_path": matched["patterns"]["source_path"],
            "source_sha256": matched["patterns"]["source_sha256"],
            "id_count": len(registry["PATTERN"]),
        },
        "GRAMMAR": grammar_identity,
    }
    return registry, identity, grammar_to_egp


def _asset_roles(row: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    status = str(row.get("representative_admission_status") or "")
    if status not in READY_STATUSES:
        return [], []
    roles = {"SENTENCE_ASSET_CANDIDATE"}
    maturity = str(row.get("sentence_seed_maturity") or "")
    if maturity in {"STRICT_CORE_SENTENCE_SEED", "BROAD_CORE_SENTENCE_SEED"}:
        roles.add("CORE_SENTENCE_ASSET_CANDIDATE")
    if row.get("passage_seed_status") == "SUPPORTED":
        roles.add("PASSAGE_ASSET_CANDIDATE")
    affordances = _list_of_strings(row, "four_skill_affordances")
    skill_roles = {SKILL_ROLE_MAP[value] for value in affordances if value in SKILL_ROLE_MAP}
    return sorted(roles), sorted(skill_roles)


def build_package(
    dedup_package: Mapping[str, Any],
    authority_registry: Mapping[str, set[str]],
    authority_identity: Mapping[str, Any],
    grammar_to_egp: Mapping[str, Sequence[str]],
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
    expected_types = {item[0] for item in REFERENCE_FIELDS}
    if set(authority_registry) != expected_types:
        raise AuthorityLinkageError("authority_registry_types_invalid")
    if any(not isinstance(authority_registry[key], set) or not authority_registry[key] for key in expected_types):
        raise AuthorityLinkageError("authority_registry_empty_or_invalid")
    if set(grammar_to_egp) != authority_registry["GRAMMAR"]:
        raise AuthorityLinkageError("grammar_to_egp_registry_mismatch")

    linkage_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    authority_type_counts: Counter[str] = Counter()
    canonical_target_sets: dict[str, set[str]] = {key: set() for key in expected_types}
    seen_groups: set[str] = set()
    seen_refs: set[str] = set()
    conflicts: list[dict[str, str]] = []
    resolved_theme_candidate_count = 0

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

        links: list[dict[str, Any]] = []
        refs_by_type: dict[str, list[str]] = {}
        ownership: dict[str, str] = {}
        grammar_egp_refs: set[str] = set()
        for authority_type, field in REFERENCE_FIELDS:
            source_refs = _list_of_strings(row, field)
            canonical_refs: list[str] = []
            for authority_ref in source_refs:
                source_authority_ref = authority_ref
                resolution = "DIRECT_EXISTING_AUTHORITY_REF"
                if authority_type == "THEME" and authority_ref.startswith("theme_candidate:"):
                    canonical = APPROVED_THEME_CANONICAL_MAP.get(authority_ref)
                    if canonical is None:
                        raise AuthorityLinkageError(
                            f"unapproved_theme_candidate_ref:{source_ref}:{authority_ref}"
                        )
                    authority_ref = canonical
                    resolution = "OPERATOR_APPROVED_THEME_CANDIDATE_TO_CANONICAL"
                    resolved_theme_candidate_count += 1
                if authority_ref not in authority_registry[authority_type]:
                    raise AuthorityLinkageError(
                        f"authority_ref_not_found:{authority_type}:{source_ref}:{authority_ref}"
                    )
                prior = ownership.get(authority_ref)
                if prior and prior != authority_type:
                    conflicts.append({
                        "selected_source_unit_ref": source_ref,
                        "authority_ref": authority_ref,
                        "first_authority_type": prior,
                        "second_authority_type": authority_type,
                    })
                ownership[authority_ref] = authority_type
                canonical_refs.append(authority_ref)
                canonical_target_sets[authority_type].add(authority_ref)
                links.append({
                    "authority_type": authority_type,
                    "source_authority_ref": source_authority_ref,
                    "canonical_authority_ref": authority_ref,
                    "resolution": resolution,
                    "link_status": "VERIFIED_CANONICAL_AUTHORITY_LINK",
                })
                if authority_type == "GRAMMAR":
                    grammar_egp_refs.update(grammar_to_egp[authority_ref])
            refs_by_type[authority_type] = sorted(set(canonical_refs))
            authority_type_counts[authority_type] += len(canonical_refs)

        if admission_status in READY_STATUSES and (
            not refs_by_type["VOCABULARY"] or not refs_by_type["GRAMMAR"]
        ):
            raise AuthorityLinkageError(
                f"ready_representative_missing_required_authority:{source_ref}"
            )
        asset_roles, skill_roles = _asset_roles(row)
        linkage_status = LINKAGE_STATUS_BY_ADMISSION[admission_status]
        status_counts[linkage_status] += 1
        linkage_rows.append({
            "semantic_duplicate_group_id": group,
            "selected_source_unit_ref": source_ref,
            "source_level": str(row.get("source_level") or ""),
            "source_book_id": str(row.get("source_book_id") or ""),
            "representative_admission_status": admission_status,
            "candidate_cefr_scope": scope,
            "authority_links": sorted(
                links,
                key=lambda item: (
                    item["authority_type"], item["canonical_authority_ref"],
                    item["source_authority_ref"],
                ),
            ),
            "authority_refs_by_type": refs_by_type,
            "canonical_egp_row_refs": sorted(grammar_egp_refs),
            "authority_link_count": len(links),
            "authority_linkage_status": linkage_status,
            "sentence_seed_maturity": str(row.get("sentence_seed_maturity") or ""),
            "passage_seed_status": str(row.get("passage_seed_status") or ""),
            "discourse_shape": str(row.get("discourse_shape") or ""),
            "scene_structure": str(row.get("scene_structure") or ""),
            "four_skill_affordances": _list_of_strings(row, "four_skill_affordances"),
            "candidate_asset_roles": asset_roles,
            "candidate_skill_asset_roles": skill_roles,
            "canonical_linkage_complete": True,
            "promotion_status": "NOT_PROMOTED",
        })

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
            row["authority_refs_by_type"]["VOCABULARY"]
            and row["authority_refs_by_type"]["GRAMMAR"]
            for row in linkage_rows
            if row["representative_admission_status"] in READY_STATUSES
        ),
        "all_output_authority_refs_verified": all(
            link["canonical_authority_ref"] in authority_registry[link["authority_type"]]
            and link["link_status"] == "VERIFIED_CANONICAL_AUTHORITY_LINK"
            for row in linkage_rows for link in row["authority_links"]
        ),
        "approved_theme_candidates_resolved_to_canonical": all(
            not link["canonical_authority_ref"].startswith("theme_candidate:")
            for row in linkage_rows for link in row["authority_links"]
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
            "authority_registry_identity": dict(authority_identity),
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
            "unique_canonical_authority_ref_counts": {
                key: len(values) for key, values in sorted(canonical_target_sets.items())
            },
            "authority_linkage_status_counts": dict(sorted(status_counts.items())),
            "resolved_operator_approved_theme_candidate_link_count": (
                resolved_theme_candidate_count
            ),
            "sentence_asset_candidate_count": sum(
                "SENTENCE_ASSET_CANDIDATE" in row["candidate_asset_roles"]
                for row in linkage_rows
            ),
            "core_sentence_asset_candidate_count": sum(
                "CORE_SENTENCE_ASSET_CANDIDATE" in row["candidate_asset_roles"]
                for row in linkage_rows
            ),
            "passage_asset_candidate_count": sum(
                "PASSAGE_ASSET_CANDIDATE" in row["candidate_asset_roles"]
                for row in linkage_rows
            ),
            "four_skill_asset_role_link_count": sum(
                len(row["candidate_skill_asset_roles"]) for row in linkage_rows
            ),
            "authority_reference_type_conflict_count": len(conflicts),
            "unresolved_authority_ref_count": 0,
            "final_promoted_material_count": 0,
        },
        "authority_linkage_gate": {
            "source_checks": checks,
            "decision": (
                "CANONICAL_AUTHORITY_ASSET_ROLE_LINKAGE_READY"
                if ready else "BLOCKED_CANONICAL_AUTHORITY_ASSET_ROLE_LINKAGE"
            ),
            "distance_before": "D4",
            "distance_after": "D3" if ready else "D4",
            "ready_for_safe_asset_materialization": ready,
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
    parser.add_argument("--theme-catalog", type=Path, default=DEFAULT_THEME_CATALOG)
    parser.add_argument(
        "--grammar-coverage", type=Path, default=DEFAULT_GRAMMAR_COVERAGE
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.dedup_package)
        if not isinstance(package, Mapping):
            raise AuthorityLinkageError("dedup_package_not_object")
        registry, identity, grammar_to_egp = load_authority_registry(
            theme_catalog_path=args.theme_catalog,
            grammar_coverage_path=args.grammar_coverage,
        )
        output = build_package(package, registry, identity, grammar_to_egp)
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (
        AuthorityLinkageError,
        deep.AlignmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
