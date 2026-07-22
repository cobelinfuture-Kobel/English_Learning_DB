#!/usr/bin/env python3
"""Reconcile S05 coverage, prove mainline consumption, and close at D0.

D0 is not granted by registry counts alone.  The builder joins promoted RAZ
material metadata with the existing A1FS M2 Asset Body consumer metadata,
restores Sentence/Core Sentence/Passage/four-skill roles from S02, executes
bounded queries against both source partitions, and verifies A2 fail-closed.
No RAZ text or mainline payload is copied into the safe output.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S06_FinalCoverageReconciliationAndD0Closeout"
SCHEMA_VERSION = "raz.ai.acl.v1.s06.final_coverage_reconciliation_closeout.v2"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S06_FINAL_COVERAGE_RECONCILIATION_D0_CLOSEOUT"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_DEDUP = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s02_semantic_dedup/"
    "semantic_dedup_representative_selection.safe.json"
)
DEFAULT_REGISTRY = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s05_material_registry/"
    "a1_a1plus_material_registry.safe.json"
)
DEFAULT_MAINLINE = (
    REPO_ROOT / ".local/a1fs_v1/m2/"
    "four_skill_asset_body_consumer.private.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s06_final_closeout/"
    "final_coverage_reconciliation_d0.safe.json"
)

SKILL_MAP = {
    "READING_SOURCE": "READING",
    "LISTENING_ADAPTATION": "LISTENING",
    "SPEAKING_PROMPT": "SPEAKING",
    "WRITING_MODEL": "WRITING",
}
CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "mainline_payload_traversal_performed": False,
    "mainline_payload_included_in_output": False,
    "metadata_only_mainline_consumer_proof_performed": True,
    "canonical_authority_write_performed": False,
    "learner_facing_content_created": False,
    "mastery_claimed": False,
    "retention_claimed": False,
    "a2_a2plus_payload_query_performed": False,
    "a2_a2plus_rows_remain_deferred": True,
    "program_closeout_is_registry_capability_closeout": False,
    "program_closeout_requires_runtime_query_proof": True,
}


class FinalCloseoutError(ValueError):
    """Fail-closed lineage, coverage, query, or D0 invariant error."""


def _verify_hash(package: Mapping[str, Any], label: str) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise FinalCloseoutError(f"{label}_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise FinalCloseoutError(f"{label}_package_sha256_mismatch")


def _rows(package: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = package.get(key)
    if not isinstance(value, list) or not all(isinstance(row, Mapping) for row in value):
        raise FinalCloseoutError(f"package_lane_invalid:{key}")
    return value


def _verify_registry(
    package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]], Mapping[str, Any]]:
    if package.get("task_id") != registry.TASK_ID:
        raise FinalCloseoutError("registry_task_id_mismatch")
    if package.get("validation_status") != registry.PASS_STATUS:
        raise FinalCloseoutError("registry_validation_status_not_pass")
    if package.get("errors") != []:
        raise FinalCloseoutError("registry_errors_not_empty")
    _verify_hash(package, "registry")
    gate = package.get("material_registry_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != (
        "A1_A1PLUS_MATERIAL_REGISTRY_READY"
    ) or gate.get("ready_for_final_coverage_reconciliation") is not True:
        raise FinalCloseoutError("registry_gate_not_ready_for_closeout")
    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise FinalCloseoutError("registry_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise FinalCloseoutError(
                f"registry_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )
    promoted = _rows(package, "promoted_material_registry")
    remediation = _rows(package, "remediation_queue")
    support = _rows(package, "support_registry")
    rejected = _rows(package, "rejected_registry")
    bindings = _rows(package, "duplicate_bindings")
    if len(bindings) != expected_duplicate_binding_count:
        raise FinalCloseoutError("duplicate_binding_count_mismatch")
    return promoted, remediation, support, rejected, bindings, summary


def _verify_dedup(
    package: Mapping[str, Any],
    *,
    expected_semantic_identity_count: int,
) -> list[Mapping[str, Any]]:
    if package.get("task_id") != dedup.TASK_ID:
        raise FinalCloseoutError("dedup_task_id_mismatch")
    if package.get("validation_status") != dedup.PASS_STATUS:
        raise FinalCloseoutError("dedup_validation_status_not_pass")
    if package.get("errors") != []:
        raise FinalCloseoutError("dedup_errors_not_empty")
    _verify_hash(package, "dedup")
    gate = package.get("dedup_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != (
        "SEMANTIC_DEDUP_REPRESENTATIVES_READY"
    ) or gate.get("ready_for_authority_linkage") is not True:
        raise FinalCloseoutError("dedup_gate_not_ready")
    representatives = _rows(package, "semantic_representatives")
    if len(representatives) != expected_semantic_identity_count:
        raise FinalCloseoutError("semantic_representative_count_mismatch")
    return representatives


def _verify_mainline(index: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int]:
    if index.get("task_id") != m2.TASK_ID:
        raise FinalCloseoutError("mainline_consumer_task_id_mismatch")
    if index.get("schema_version") != m2.SCHEMA_VERSION:
        raise FinalCloseoutError("mainline_consumer_schema_version_mismatch")
    if index.get("validation_status") != m2.STATUS:
        raise FinalCloseoutError("mainline_consumer_status_not_pass")
    access = index.get("access_contract")
    if not isinstance(access, Mapping) or access.get("a2_payload_query_allowed") is not False:
        raise FinalCloseoutError("mainline_a2_lock_invalid")
    records = index.get("asset_records")
    catalog = index.get("lesson_catalog")
    if not isinstance(records, list) or not all(isinstance(row, Mapping) for row in records):
        raise FinalCloseoutError("mainline_asset_records_invalid")
    if not isinstance(catalog, list) or not all(isinstance(row, Mapping) for row in catalog):
        raise FinalCloseoutError("mainline_lesson_catalog_invalid")
    requirements = {
        str(row.get("lesson_id") or ""): sorted(
            str(value) for value in row.get("requirement_node_ids", [])
        )
        for row in catalog
        if isinstance(row.get("requirement_node_ids", []), list)
    }
    safe_rows: list[dict[str, Any]] = []
    a2_skipped = 0
    for row in records:
        level = str(row.get("level") or "")
        if level == "A2":
            a2_skipped += 1
            continue
        if level not in {"A1", "A1+"}:
            raise FinalCloseoutError(f"mainline_level_invalid:{level}")
        asset_key = str(row.get("asset_key") or row.get("asset_id") or "")
        lesson_id = str(row.get("lesson_id") or "")
        skill = str(row.get("skill") or "")
        role = str(row.get("role") or "")
        if not asset_key or not lesson_id or not skill or not role:
            raise FinalCloseoutError("mainline_asset_metadata_incomplete")
        # Payload is deliberately not read.
        safe_rows.append(
            {
                "integrated_ref": f"MAINLINE:{asset_key}",
                "source_type": "MAINLINE_ASSET_BODY",
                "material_ref": asset_key,
                "lesson_id": lesson_id,
                "level": level,
                "skills": [skill],
                "material_roles": [role],
                "authority_links": [
                    {"authority_type": "REQUIREMENT_NODE", "authority_ref": ref}
                    for ref in requirements.get(lesson_id, [])
                ],
                "payload_access": "EXISTING_PRIVATE_M2_CONSUMER",
                "learner_facing": False,
            }
        )
    if not safe_rows:
        raise FinalCloseoutError("mainline_a1_a1plus_assets_empty")
    return safe_rows, a2_skipped


def _roles(representative: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    roles = {"SENTENCE_CANDIDATE"}
    maturity = str(representative.get("sentence_seed_maturity") or "")
    if maturity == "STRICT_CORE_SENTENCE_SEED":
        roles.add("STRICT_CORE_SENTENCE_CANDIDATE")
    elif maturity == "BROAD_CORE_SENTENCE_SEED":
        roles.add("BROAD_CORE_SENTENCE_CANDIDATE")
    if representative.get("passage_seed_status") == "SUPPORTED":
        roles.add("PASSAGE_CANDIDATE")
    affordances = representative.get("four_skill_affordances")
    if not isinstance(affordances, list):
        raise FinalCloseoutError("four_skill_affordances_invalid")
    skills = sorted({SKILL_MAP[value] for value in affordances if value in SKILL_MAP})
    if not skills:
        raise FinalCloseoutError("raz_material_skill_projection_empty")
    return sorted(roles), skills


def _raz_rows(
    representatives: Sequence[Mapping[str, Any]],
    promoted: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_group = {
        str(row.get("semantic_duplicate_group_id") or ""): row
        for row in representatives
    }
    if "" in by_group or len(by_group) != len(representatives):
        raise FinalCloseoutError("representative_group_missing_or_duplicate")
    rows: list[dict[str, Any]] = []
    material_ids: set[str] = set()
    for material in promoted:
        group = str(material.get("semantic_duplicate_group_id") or "")
        source_ref = str(material.get("selected_source_unit_ref") or "")
        material_id = str(material.get("material_id") or "")
        representative = by_group.get(group)
        if representative is None:
            raise FinalCloseoutError(f"promoted_group_not_in_dedup:{group}")
        if source_ref != representative.get("selected_source_unit_ref"):
            raise FinalCloseoutError(f"promoted_source_ref_mismatch:{group}")
        if not material_id or material_id in material_ids:
            raise FinalCloseoutError("promoted_material_id_missing_or_duplicate")
        material_ids.add(material_id)
        scope = str(material.get("candidate_cefr_scope") or "")
        if scope not in {"A1", "A1_PLUS"}:
            raise FinalCloseoutError(f"promoted_scope_invalid:{material_id}:{scope}")
        links = material.get("authority_links")
        if not isinstance(links, list) or not all(isinstance(link, Mapping) for link in links):
            raise FinalCloseoutError(f"promoted_authority_links_invalid:{material_id}")
        authority_types = {str(link.get("authority_type") or "") for link in links}
        if not {"VOCABULARY", "GRAMMAR"} <= authority_types:
            raise FinalCloseoutError(f"promoted_required_authority_missing:{material_id}")
        roles, skills = _roles(representative)
        rows.append(
            {
                "integrated_ref": f"RAZ:{material_id}",
                "source_type": "RAZ_DERIVED_MATERIAL",
                "material_ref": material_id,
                "source_unit_ref": source_ref,
                "semantic_identity_id": group,
                "level": "A1+" if scope == "A1_PLUS" else "A1",
                "skills": skills,
                "material_roles": roles,
                "authority_links": [dict(link) for link in links],
                "payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
                "learner_facing": False,
            }
        )
    return rows


def query_index(
    index: Mapping[str, Any],
    *,
    source_type: str | None = None,
    level: str | None = None,
    skill: str | None = None,
    authority_ref: str | None = None,
    material_role: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    if index.get("validation_status") != PASS_STATUS:
        raise FinalCloseoutError("index_status_invalid")
    if level in {"A2", "A2+", "A2_PLUS"}:
        raise FinalCloseoutError("A2_QUERY_LOCKED")
    if level is not None and level not in {"A1", "A1+"}:
        raise FinalCloseoutError("query_level_invalid")
    if source_type is not None and source_type not in {
        "MAINLINE_ASSET_BODY", "RAZ_DERIVED_MATERIAL"
    }:
        raise FinalCloseoutError("query_source_type_invalid")
    if skill is not None and skill not in {"READING", "LISTENING", "SPEAKING", "WRITING"}:
        raise FinalCloseoutError("query_skill_invalid")
    if offset < 0 or limit < 1 or limit > 100:
        raise FinalCloseoutError("query_page_invalid")
    rows = []
    for row in index.get("integrated_materials", []):
        if source_type is not None and row["source_type"] != source_type:
            continue
        if level is not None and row["level"] != level:
            continue
        if skill is not None and skill not in row["skills"]:
            continue
        if material_role is not None and material_role not in row["material_roles"]:
            continue
        if authority_ref is not None and authority_ref not in {
            link["authority_ref"] for link in row["authority_links"]
        }:
            continue
        rows.append(row)
    page = rows[offset : offset + limit]
    return {
        "query_status": "PASS_METADATA_ONLY_INTEGRATED_QUERY",
        "total_match_count": len(rows),
        "offset": offset,
        "limit": limit,
        "returned_count": len(page),
        "integrated_materials": page,
        "a2_payload_included": False,
        "learner_facing_payload_included": False,
    }


def build_package(
    registry_package: Mapping[str, Any],
    dedup_package: Mapping[str, Any],
    mainline_index: Mapping[str, Any],
    *,
    mainline_index_sha256: str,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    promoted, remediation, support, rejected, bindings, summary = _verify_registry(
        registry_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    representatives = _verify_dedup(
        dedup_package,
        expected_semantic_identity_count=expected_semantic_identity_count,
    )
    if not isinstance(mainline_index_sha256, str) or len(mainline_index_sha256) != 64:
        raise FinalCloseoutError("mainline_index_sha256_invalid")
    mainline_rows, a2_skipped = _verify_mainline(mainline_index)
    raz_rows = _raz_rows(representatives, promoted)

    lanes = promoted + remediation + support + rejected
    group_counts = Counter(str(row.get("semantic_duplicate_group_id") or "") for row in lanes)
    source_counts = Counter(str(row.get("selected_source_unit_ref") or "") for row in lanes)
    material_ids = [str(row.get("material_id") or "") for row in promoted]
    promoted_scope_counts = Counter(str(row.get("candidate_cefr_scope") or "") for row in promoted)
    integrated_rows = sorted(
        mainline_rows + raz_rows,
        key=lambda row: (row["source_type"], row["level"], row["integrated_ref"]),
    )
    integrated_refs = [row["integrated_ref"] for row in integrated_rows]
    authority_refs: dict[str, set[str]] = {}
    role_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    for row in raz_rows:
        role_counts.update(row["material_roles"])
        skill_counts.update(row["skills"])
        for link in row["authority_links"]:
            authority_refs.setdefault(str(link["authority_type"]), set()).add(
                str(link["authority_ref"])
            )

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "input_identity": {
            "material_registry_task_id": registry_package["task_id"],
            "material_registry_package_sha256": registry_package["package_sha256"],
            "semantic_dedup_task_id": dedup_package["task_id"],
            "semantic_dedup_package_sha256": dedup_package["package_sha256"],
            "mainline_consumer_task_id": mainline_index["task_id"],
            "mainline_consumer_sha256": mainline_index_sha256,
        },
        "scope_contract": {
            **dict(registry_package["scope_contract"]),
            "consumer_levels": ["A1", "A1+"],
            "a2_query_status": "LOCKED",
            "max_query_limit": 100,
        },
        "integrated_materials": integrated_rows,
        "coverage_reconciliation": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": expected_semantic_identity_count,
            "duplicate_binding_count": expected_duplicate_binding_count,
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "promoted_material_count": len(promoted),
            "remediation_queue_count": len(remediation),
            "support_registry_count": len(support),
            "rejected_registry_count": len(rejected),
            "promoted_cefr_scope_counts": dict(sorted(promoted_scope_counts.items())),
            "mainline_material_count": len(mainline_rows),
            "mainline_a2_asset_count_skipped": a2_skipped,
            "integrated_material_count": len(integrated_rows),
            "linked_theme_ref_count": len(authority_refs.get("THEME", set())),
            "linked_vocabulary_ref_count": len(authority_refs.get("VOCABULARY", set())),
            "linked_chunk_ref_count": len(authority_refs.get("CHUNK", set())),
            "linked_pattern_ref_count": len(authority_refs.get("PATTERN", set())),
            "linked_grammar_ref_count": len(authority_refs.get("GRAMMAR", set())),
            "linked_sentence_candidate_count": role_counts["SENTENCE_CANDIDATE"],
            "linked_core_sentence_candidate_count": (
                role_counts["STRICT_CORE_SENTENCE_CANDIDATE"]
                + role_counts["BROAD_CORE_SENTENCE_CANDIDATE"]
            ),
            "linked_passage_candidate_count": role_counts["PASSAGE_CANDIDATE"],
            "four_skill_candidate_counts": dict(sorted(skill_counts.items())),
        },
        "consumer_contract": {
            "source_partitions": ["MAINLINE_ASSET_BODY", "RAZ_DERIVED_MATERIAL"],
            "source_payload_resolution": "PRIVATE_SOURCE_REF_REQUIRED",
            "query_filters": ["source_type", "level", "skill", "authority_ref", "material_role"],
            "learner_facing_content_status": "NOT_CREATED_BY_THIS_PROGRAM",
        },
        "final_closeout_gate": {},
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    if not mainline_rows or not raz_rows:
        raise FinalCloseoutError("integrated_source_partition_empty")
    if len(integrated_refs) != len(set(integrated_refs)):
        raise FinalCloseoutError("integrated_ref_collision")

    raz_probe = raz_rows[0]
    mainline_probe = mainline_rows[0]
    probe_authority = str(raz_probe["authority_links"][0]["authority_ref"])
    raz_query = query_index(
        package,
        source_type="RAZ_DERIVED_MATERIAL",
        level=raz_probe["level"],
        authority_ref=probe_authority,
    )
    mainline_query = query_index(
        package,
        source_type="MAINLINE_ASSET_BODY",
        skill=mainline_probe["skills"][0],
    )
    a2_locked = False
    try:
        query_index(package, level="A2")
    except FinalCloseoutError as exc:
        a2_locked = str(exc) == "A2_QUERY_LOCKED"

    checks = {
        "source_total_reconciles": (
            expected_scope_page_unit_count + expected_deferred_page_unit_count
            == expected_total_page_unit_count
        ),
        "scope_count_reconciles_from_identity_and_duplicates": (
            expected_semantic_identity_count + expected_duplicate_binding_count
            == expected_scope_page_unit_count
        ),
        "all_semantic_identities_in_exactly_one_lane": (
            len(lanes) == expected_semantic_identity_count
            and bool(group_counts)
            and all(group and count == 1 for group, count in group_counts.items())
            and all(source and count == 1 for source, count in source_counts.items())
        ),
        "duplicate_bindings_exact": len(bindings) == expected_duplicate_binding_count,
        "promoted_registry_nonempty": bool(promoted),
        "promoted_material_ids_complete_unique": (
            all(material_ids) and len(material_ids) == len(set(material_ids))
        ),
        "promoted_scope_closed_to_a1_a1plus": (
            set(promoted_scope_counts) <= {"A1", "A1_PLUS"}
            and sum(promoted_scope_counts.values()) == len(promoted)
        ),
        "nonpromoted_lanes_have_no_material_id": all(
            "material_id" not in row for row in remediation + support + rejected
        ),
        "registry_summary_counts_match_lanes": (
            summary.get("final_promoted_material_count") == len(promoted)
            and summary.get("remediation_queue_count") == len(remediation)
            and summary.get("support_registry_count") == len(support)
            and summary.get("rejected_registry_count") == len(rejected)
        ),
        "mainline_and_raz_consumer_partitions_present": bool(mainline_rows and raz_rows),
        "integrated_refs_unique": len(integrated_refs) == len(set(integrated_refs)),
        "raz_runtime_query_proof": any(
            row["integrated_ref"] == raz_probe["integrated_ref"]
            for row in raz_query["integrated_materials"]
        ),
        "mainline_runtime_query_proof": any(
            row["integrated_ref"] == mainline_probe["integrated_ref"]
            for row in mainline_query["integrated_materials"]
        ),
        "a2_query_fails_closed": a2_locked,
        "all_integrated_rows_nonlearner_facing": all(
            row["learner_facing"] is False for row in integrated_rows
        ),
        "sentence_role_covers_all_promoted_materials": (
            role_counts["SENTENCE_CANDIDATE"] == len(raz_rows)
        ),
    }
    ready = all(checks.values())
    package["validation_status"] = PASS_STATUS if ready else "FAIL"
    package["final_closeout_gate"] = {
        "source_checks": checks,
        "decision": "RAZ_AI_ACL_V1_D0_CLOSED" if ready else "BLOCKED_FINAL_CLOSEOUT",
        "program_status": "PASS_ACCEPTED_AND_CLOSED" if ready else "BLOCKED",
        "distance_before": "D1",
        "distance_after": "D0" if ready else "D1",
        "remaining_in_scope_blocker_count": 0 if ready else sum(
            1 for passed in checks.values() if not passed
        ),
        "mainline_consumer_proof": ready,
        "a2_a2plus_status": "DEFERRED_A2_A2PLUS",
        "a2_lock_status": "PASS_LOCKED" if a2_locked else "FAIL",
        "learner_facing_release_claimed": False,
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise FinalCloseoutError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _read_json_object(path: Path, code: str) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FinalCloseoutError(f"{code}_json_invalid") from exc
    if not isinstance(value, dict):
        raise FinalCloseoutError(f"{code}_not_object")
    return value, deep.sha256_file(path)


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["final_closeout_gate"]["decision"],
        "program_status": package["final_closeout_gate"]["program_status"],
        "distance_after": package["final_closeout_gate"]["distance_after"],
        **package["coverage_reconciliation"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-registry-package", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--semantic-dedup-package", type=Path, default=DEFAULT_DEDUP)
    parser.add_argument("--mainline-consumer", type=Path, default=DEFAULT_MAINLINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        registry_package, _ = _read_json_object(args.material_registry_package, "registry")
        dedup_package, _ = _read_json_object(args.semantic_dedup_package, "dedup")
        mainline_index, mainline_sha = _read_json_object(args.mainline_consumer, "mainline")
        output = build_package(
            registry_package,
            dedup_package,
            mainline_index,
            mainline_index_sha256=mainline_sha,
        )
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (
        FinalCloseoutError,
        registry.MaterialRegistryError,
        dedup.SemanticDedupError,
        m2.ConsumerError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
