#!/usr/bin/env python3
"""Bind S02 representatives to authority records that actually exist.

The public S03 contract remains compatible with S04-S06. Every Theme,
Vocabulary, Chunk, Pattern, and Grammar ref is checked against a real registry.
The three operator-approved Theme candidates become canonical refs only after
those Theme records exist. Grammar coverage is loaded from the generated
artifact when present, otherwise rebuilt deterministically from committed
canonical sources; both paths must yield 24 units and 109 EGP rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1_grammar_full_teachable_candidate_coverage as grammar_builder
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_a1_a1plus_coverage_recheck as coverage
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S03_AuthorityLinkageAndConflictGate"
SCHEMA_VERSION = "raz.ai.acl.v1.s03.authority_linkage_conflict_gate.v3"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S03_AUTHORITY_LINKAGE_CONFLICT_GATE"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675
EXPECTED_GRAMMAR_UNIT_COUNT = 24
EXPECTED_EGP_ROW_COUNT = 109
EXPECTED_A1_A1PLUS_THEME_COUNT = 13

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
EXPECTED_SCOPE_BY_ADMISSION = {
    "A1_READY_CANDIDATE": "A1",
    "A1PLUS_READY_CANDIDATE": "A1_PLUS",
    "REWRITE_REQUIRED": "A1_A1PLUS_UNRESOLVED",
    "SUPPORT_ONLY": "NONE",
    "REJECTED_UNUSABLE": "NONE",
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
    "existing_authority_refs_linked": True,
    "authority_registry_existence_validated": True,
    "operator_approved_theme_mount_consumed": True,
    "grammar_24_unit_109_row_traceability_validated": True,
    "canonical_authority_write_performed_by_builder": False,
    "authority_promotion_performed_by_builder": False,
    "material_promotion_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class AuthorityLinkageError(ValueError):
    """Fail-closed S02 lineage, authority registry, or linkage error."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    core = {key: value for key, value in package.items() if key != "package_sha256"}
    if not isinstance(claimed, str) or claimed != deep.sha256_value(core):
        raise AuthorityLinkageError("dedup_package_sha256_mismatch")


def _string_list(row: Mapping[str, Any], key: str) -> list[str]:
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
    if package.get("validation_status") != dedup.PASS_STATUS or package.get("errors") != []:
        raise AuthorityLinkageError("dedup_not_pass")
    _verify_hash(package)
    gate = package.get("dedup_gate")
    if not isinstance(gate, Mapping) or (
        gate.get("decision") != "SEMANTIC_DEDUP_REPRESENTATIVES_READY"
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


def _theme_registry(path: Path) -> tuple[set[str], dict[str, Any]]:
    payload = deep.read_json(path)
    rows = payload.get("themes") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise AuthorityLinkageError("theme_catalog_invalid")
    ids = {
        "theme:" + str(row["theme_id"])
        for row in rows
        if row.get("level") in {"A1", "A1_plus"}
        and isinstance(row.get("theme_id"), str)
        and row.get("theme_id")
    }
    if len(ids) != EXPECTED_A1_A1PLUS_THEME_COUNT:
        raise AuthorityLinkageError(f"a1_a1plus_theme_count_invalid:{len(ids)}")
    required = set(EXPECTED_APPROVED_THEME_MAP.values()) | {
        "theme:a1_personal_information_and_greetings"
    }
    if not required <= ids:
        raise AuthorityLinkageError(
            "approved_theme_mount_missing:" + ",".join(sorted(required - ids))
        )
    return ids, {
        "source_mode": "TRACKED_THEME_CATALOG",
        "source_path": path.relative_to(REPO_ROOT).as_posix(),
        "source_sha256": _sha256_file(path),
        "id_count": len(ids),
    }


def _build_grammar_coverage() -> tuple[dict[str, Any], dict[str, Any]]:
    paths = (
        grammar_builder.QUERY_PATH,
        grammar_builder.RULE_INDEX_PATH,
        grammar_builder.AUTHORITY_PATH,
        grammar_builder.CAN_RULE_PATH,
        grammar_builder.BATCH_01_PATH,
        grammar_builder.BATCH_02_PATH,
    )
    payloads = tuple(grammar_builder.load_json(path) for path in paths)
    artifact = grammar_builder.build_artifact(*payloads)
    report = grammar_builder.validate_artifact(artifact, *payloads)
    if report.get("validation_status") != "PASS":
        raise AuthorityLinkageError(
            "grammar_coverage_rebuild_failed:"
            + ";".join(str(error) for error in report.get("errors", [])[:10])
        )
    identity = {
        "source_mode": "DETERMINISTIC_REBUILD_FROM_COMMITTED_CANONICAL_SOURCES",
        "builder_task_id": grammar_builder.TASK_ID,
        "source_files": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "sha256": _sha256_file(path),
            }
            for path in paths
        ],
        "rebuilt_artifact_sha256": deep.sha256_value(artifact),
    }
    return artifact, identity


def _grammar_registry(
    path: Path,
) -> tuple[set[str], dict[str, Any], dict[str, list[str]]]:
    if path.is_file():
        payload = deep.read_json(path)
        identity: dict[str, Any] = {
            "source_mode": "TRACKED_OR_LOCAL_GENERATED_ARTIFACT",
            "source_path": path.relative_to(REPO_ROOT).as_posix(),
            "source_sha256": _sha256_file(path),
        }
    else:
        payload, identity = _build_grammar_coverage()
    rows = payload.get("learning_units") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise AuthorityLinkageError("grammar_learning_units_invalid")
    mapping: dict[str, list[str]] = {}
    for row in rows:
        unit_id = row.get("grammar_unit_id") or row.get("learning_unit_id") or row.get("id")
        egp_refs = row.get("canonical_egp_row_ids")
        if not isinstance(unit_id, str) or not unit_id:
            raise AuthorityLinkageError("grammar_unit_id_invalid")
        if not isinstance(egp_refs, list) or not all(
            isinstance(ref, str) and ref for ref in egp_refs
        ):
            raise AuthorityLinkageError(f"grammar_egp_rows_invalid:{unit_id}")
        mapping[unit_id] = sorted(set(egp_refs))
    ids = set(mapping)
    egp_ids = {ref for refs in mapping.values() for ref in refs}
    if ids != set(deep.UNIT_IDS):
        raise AuthorityLinkageError(
            "grammar_unit_registry_mismatch:" + ",".join(sorted(ids ^ set(deep.UNIT_IDS)))
        )
    if len(ids) != EXPECTED_GRAMMAR_UNIT_COUNT or len(egp_ids) != EXPECTED_EGP_ROW_COUNT:
        raise AuthorityLinkageError(
            f"grammar_coverage_count_invalid:{len(ids)}:{len(egp_ids)}"
        )
    identity.update(
        {
            "id_count": len(ids),
            "canonical_egp_row_count": len(egp_ids),
        }
    )
    return ids, identity, mapping


def load_authority_registry(
    *,
    theme_catalog_path: Path = DEFAULT_THEME_CATALOG,
    grammar_coverage_path: Path = DEFAULT_GRAMMAR_COVERAGE,
) -> tuple[dict[str, set[str]], dict[str, Any], dict[str, list[str]]]:
    base = deep.load_authorities()
    themes, theme_identity = _theme_registry(theme_catalog_path)
    grammar, grammar_identity, grammar_to_egp = _grammar_registry(
        grammar_coverage_path
    )
    registry = {
        "THEME": themes,
        "VOCABULARY": set(base["vocabulary"]["ids"]),
        "CHUNK": set(base["chunks"]["ids"]),
        "PATTERN": set(base["patterns"]["ids"]),
        "GRAMMAR": grammar,
    }
    identity = {
        "THEME": theme_identity,
        "VOCABULARY": {
            "source_path": base["vocabulary"]["source_path"],
            "source_sha256": base["vocabulary"]["source_sha256"],
            "id_count": len(registry["VOCABULARY"]),
        },
        "CHUNK": {
            "source_path": base["chunks"]["source_path"],
            "source_sha256": base["chunks"]["source_sha256"],
            "id_count": len(registry["CHUNK"]),
        },
        "PATTERN": {
            "source_path": base["patterns"]["source_path"],
            "source_sha256": base["patterns"]["source_sha256"],
            "id_count": len(registry["PATTERN"]),
        },
        "GRAMMAR": grammar_identity,
    }
    return registry, identity, grammar_to_egp


def build_package(
    dedup_package: Mapping[str, Any],
    authority_registry: Mapping[str, set[str]] | None = None,
    authority_identity: Mapping[str, Any] | None = None,
    grammar_to_egp: Mapping[str, Sequence[str]] | None = None,
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
    if authority_registry is None or authority_identity is None or grammar_to_egp is None:
        authority_registry, authority_identity, grammar_to_egp = load_authority_registry()
    expected_types = {authority_type for authority_type, _ in REFERENCE_FIELDS}
    if set(authority_registry) != expected_types:
        raise AuthorityLinkageError("authority_registry_types_invalid")
    if any(
        not isinstance(authority_registry[key], set) or not authority_registry[key]
        for key in expected_types
    ):
        raise AuthorityLinkageError("authority_registry_empty_or_invalid")
    if set(grammar_to_egp) != authority_registry["GRAMMAR"]:
        raise AuthorityLinkageError("grammar_to_egp_registry_mismatch")

    output_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    unique_refs = {key: set() for key in expected_types}
    seen_groups: set[str] = set()
    seen_sources: set[str] = set()
    conflicts: list[dict[str, str]] = []
    resolved_theme_count = 0

    for row in sorted(
        representatives, key=lambda item: str(item.get("semantic_duplicate_group_id"))
    ):
        group = str(row.get("semantic_duplicate_group_id") or "")
        source_ref = str(row.get("selected_source_unit_ref") or "")
        admission = str(row.get("representative_admission_status") or "")
        scope = str(row.get("candidate_cefr_scope") or "")
        if not group or group in seen_groups:
            raise AuthorityLinkageError("semantic_group_missing_or_duplicate")
        if not source_ref or source_ref in seen_sources:
            raise AuthorityLinkageError("representative_source_ref_missing_or_duplicate")
        if admission not in LINKAGE_STATUS_BY_ADMISSION:
            raise AuthorityLinkageError(f"representative_admission_status_invalid:{source_ref}")
        expected_scope = EXPECTED_SCOPE_BY_ADMISSION[admission]
        if scope != expected_scope:
            raise AuthorityLinkageError(
                "candidate_cefr_scope_mismatch:"
                f"{source_ref}:{admission}:{scope}:{expected_scope}"
            )
        seen_groups.add(group)
        seen_sources.add(source_ref)
        links: list[dict[str, str]] = []
        refs_by_type: dict[str, list[str]] = {}
        ownership: dict[str, str] = {}
        egp_refs: set[str] = set()
        for authority_type, field in REFERENCE_FIELDS:
            canonical_refs: list[str] = []
            for source_authority_ref in _string_list(row, field):
                canonical_ref = source_authority_ref
                resolution = "DIRECT_EXISTING_AUTHORITY_REF"
                if authority_type == "THEME" and source_authority_ref.startswith(
                    "theme_candidate:"
                ):
                    canonical_ref = APPROVED_THEME_CANONICAL_MAP.get(source_authority_ref, "")
                    if not canonical_ref:
                        raise AuthorityLinkageError(
                            f"unapproved_theme_candidate_ref:{source_ref}:{source_authority_ref}"
                        )
                    resolution = "OPERATOR_APPROVED_THEME_CANDIDATE_TO_CANONICAL"
                    resolved_theme_count += 1
                if canonical_ref not in authority_registry[authority_type]:
                    raise AuthorityLinkageError(
                        f"authority_ref_not_found:{authority_type}:{source_ref}:{canonical_ref}"
                    )
                prior = ownership.get(canonical_ref)
                if prior and prior != authority_type:
                    conflicts.append(
                        {
                            "selected_source_unit_ref": source_ref,
                            "authority_ref": canonical_ref,
                            "first_authority_type": prior,
                            "second_authority_type": authority_type,
                        }
                    )
                ownership[canonical_ref] = authority_type
                canonical_refs.append(canonical_ref)
                unique_refs[authority_type].add(canonical_ref)
                links.append(
                    {
                        "authority_type": authority_type,
                        "authority_ref": canonical_ref,
                        "source_authority_ref": source_authority_ref,
                        "resolution": resolution,
                        "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
                    }
                )
                if authority_type == "GRAMMAR":
                    egp_refs.update(grammar_to_egp[canonical_ref])
            refs_by_type[authority_type] = sorted(set(canonical_refs))
            type_counts[authority_type] += len(canonical_refs)
        if admission in READY_STATUSES and (
            not refs_by_type["VOCABULARY"] or not refs_by_type["GRAMMAR"]
        ):
            raise AuthorityLinkageError(
                f"ready_representative_missing_required_authority:{source_ref}"
            )
        linkage_status = LINKAGE_STATUS_BY_ADMISSION[admission]
        status_counts[linkage_status] += 1
        output_rows.append(
            {
                "semantic_duplicate_group_id": group,
                "selected_source_unit_ref": source_ref,
                "source_level": str(row.get("source_level") or ""),
                "source_book_id": str(row.get("source_book_id") or ""),
                "representative_admission_status": admission,
                "candidate_cefr_scope": scope,
                "authority_links": sorted(
                    links,
                    key=lambda item: (
                        item["authority_type"], item["authority_ref"],
                        item["source_authority_ref"],
                    ),
                ),
                "authority_refs_by_type": refs_by_type,
                "canonical_egp_row_refs": sorted(egp_refs),
                "authority_link_count": len(links),
                "authority_linkage_status": linkage_status,
                "promotion_status": "NOT_PROMOTED",
            }
        )

    binding_targets = {
        str(row.get("representative_source_unit_ref") or "") for row in bindings
    }
    checks = {
        "one_linkage_row_per_semantic_identity": (
            len(output_rows) == expected_semantic_identity_count
            and len(seen_groups) == expected_semantic_identity_count
            and len(seen_sources) == expected_semantic_identity_count
        ),
        "duplicate_bindings_target_selected_representatives": (
            binding_targets <= seen_sources
            and len(bindings) == expected_duplicate_binding_count
        ),
        "ready_rows_have_vocabulary_and_grammar_links": all(
            row["authority_refs_by_type"]["VOCABULARY"]
            and row["authority_refs_by_type"]["GRAMMAR"]
            for row in output_rows
            if row["representative_admission_status"] in READY_STATUSES
        ),
        "all_output_refs_exist_in_authority_registries": all(
            link["authority_ref"] in authority_registry[link["authority_type"]]
            for row in output_rows for link in row["authority_links"]
        ),
        "approved_theme_candidates_resolved_to_canonical": all(
            not link["authority_ref"].startswith("theme_candidate:")
            for row in output_rows for link in row["authority_links"]
        ),
        "authority_reference_type_conflicts_absent": not conflicts,
        "a2_a2plus_not_opened": all(
            row["candidate_cefr_scope"] not in {"A2", "A2_PLUS"}
            for row in output_rows
        ),
        "no_material_promoted": all(
            row["promotion_status"] == "NOT_PROMOTED" for row in output_rows
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
        "authority_linkage_rows": output_rows,
        "duplicate_bindings": [dict(row) for row in bindings],
        "authority_reference_type_conflicts": conflicts,
        "aggregate_summary": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": len(output_rows),
            "representative_count": len(output_rows),
            "duplicate_binding_count": len(bindings),
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "authority_link_count": sum(row["authority_link_count"] for row in output_rows),
            "authority_type_link_counts": dict(sorted(type_counts.items())),
            "unique_canonical_authority_ref_counts": {
                key: len(values) for key, values in sorted(unique_refs.items())
            },
            "authority_linkage_status_counts": dict(sorted(status_counts.items())),
            "resolved_operator_approved_theme_candidate_link_count": resolved_theme_count,
            "authority_reference_type_conflict_count": len(conflicts),
            "unresolved_authority_ref_count": 0,
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
    parser.add_argument("--theme-catalog", type=Path, default=DEFAULT_THEME_CATALOG)
    parser.add_argument("--grammar-coverage", type=Path, default=DEFAULT_GRAMMAR_COVERAGE)
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
