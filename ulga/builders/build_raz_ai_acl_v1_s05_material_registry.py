#!/usr/bin/env python3
"""Integrate canonical-complete RAZ A1/A1+ materials with the mainline M2 consumer.

S05 consumes the S04 safe role package, verifies every promoted private source
reference, projects one extension record per four-skill affordance, links only
to existing M2 lessons/requirements, and exposes a combined metadata query.
Source text remains private and is represented in safe output only by digest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S05_MainlineM2ConsumerIntegration"
SCHEMA_VERSION = "raz.ai.acl.v1.s05.mainline_m2_consumer_integration.v2"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S05_MAINLINE_M2_CONSUMER_INTEGRATION"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_RESOLUTION = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s04_admission_resolution/"
    "safe_asset_role_materialization_admission.safe.json"
)
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_MAINLINE = (
    REPO_ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s05_material_registry/"
    "mainline_m2_consumer_extension.safe.json"
)

LANES = {
    "PROMOTION_ELIGIBLE",
    "REMEDIATION_REQUIRED",
    "SUPPORT_ADMITTED",
    "REJECTED_CLOSED",
}
SKILL_BY_ROLE = {
    "READING_SOURCE_ASSET": "READING",
    "LISTENING_ADAPTATION_SEED": "LISTENING",
    "SPEAKING_PROMPT_SEED": "SPEAKING",
    "WRITING_MODEL_SEED": "WRITING",
}
LEVEL_TO_M2 = {"A1": "A1", "A1_PLUS": "A1+"}
MAX_COMBINED_QUERY_LIMIT = 100

CLAIM_BOUNDARIES = {
    "private_source_text_read_for_digest_and_runtime_resolution": True,
    "source_text_included_in_safe_output": False,
    "source_title_included_in_safe_output": False,
    "canonical_authority_write_performed": False,
    "mainline_m2_source_index_mutated": False,
    "mainline_consumer_extension_created": True,
    "private_source_runtime_resolution_available": True,
    "rewrite_required_rows_promoted": False,
    "support_only_rows_promoted": False,
    "rejected_rows_promoted": False,
    "learner_facing_release_approved": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class MaterialRegistryError(ValueError):
    """Fail-closed S04 lineage, source, M2 integration, or query error."""


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise MaterialRegistryError("resolution_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise MaterialRegistryError("resolution_package_sha256_mismatch")


def _material_id(group: str, source_ref: str) -> str:
    digest = hashlib.sha256(f"{group}\0{source_ref}".encode("utf-8")).hexdigest()[:24]
    return f"RAZ_A1A1PLUS_MATERIAL_{digest}"


def _asset_key(material_id: str, skill: str) -> str:
    return f"RAZ_DERIVED:{skill}:{material_id}"


def _verify_resolution(
    package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if package.get("task_id") != resolution.TASK_ID:
        raise MaterialRegistryError("resolution_task_id_mismatch")
    if package.get("validation_status") != resolution.PASS_STATUS:
        raise MaterialRegistryError("resolution_validation_status_not_pass")
    if package.get("errors") != []:
        raise MaterialRegistryError("resolution_errors_not_empty")
    _verify_hash(package)
    gate = package.get("admission_resolution_gate")
    if (
        not isinstance(gate, Mapping)
        or gate.get("decision") != "SAFE_ASSET_ROLE_MATERIALIZATION_READY"
        or gate.get("ready_for_mainline_consumer_integration") is not True
        or gate.get("remediation_queue_is_nonpromotable") is not True
    ):
        raise MaterialRegistryError("resolution_gate_not_ready_for_consumer")
    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise MaterialRegistryError("resolution_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "final_promoted_material_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise MaterialRegistryError(
                f"resolution_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )
    rows = package.get("resolved_admission_rows")
    bindings = package.get("duplicate_bindings")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise MaterialRegistryError("resolved_admission_rows_invalid")
    if not isinstance(bindings, list) or not all(
        isinstance(row, Mapping) for row in bindings
    ):
        raise MaterialRegistryError("duplicate_bindings_invalid")
    if len(rows) != expected_semantic_identity_count:
        raise MaterialRegistryError("resolved_admission_row_count_mismatch")
    if len(bindings) != expected_duplicate_binding_count:
        raise MaterialRegistryError("duplicate_binding_count_mismatch")
    return rows, bindings


def _verify_mainline(index: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if index.get("task_id") != m2.TASK_ID or index.get("validation_status") != m2.STATUS:
        raise MaterialRegistryError("mainline_m2_identity_invalid")
    if index.get("errors") != []:
        raise MaterialRegistryError("mainline_m2_errors_not_empty")
    access = index.get("access_contract")
    if (
        not isinstance(access, Mapping)
        or access.get("a2_payload_query_allowed") is not False
        or set(access.get("learning_query_levels") or []) != {"A1", "A1+"}
    ):
        raise MaterialRegistryError("mainline_m2_a2_lock_or_scope_invalid")
    assets = index.get("asset_records")
    lessons = index.get("lesson_catalog")
    if not isinstance(assets, list) or not all(isinstance(row, Mapping) for row in assets):
        raise MaterialRegistryError("mainline_m2_asset_records_invalid")
    if not isinstance(lessons, list) or not all(isinstance(row, Mapping) for row in lessons):
        raise MaterialRegistryError("mainline_m2_lesson_catalog_invalid")
    if not assets or not lessons:
        raise MaterialRegistryError("mainline_m2_index_empty")
    return assets, lessons


def load_private_sources(
    source_root: Path,
    *,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    texts, source_index = dedup.load_raz_texts(
        source_root,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
    )
    digests = {
        ref: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for ref, text in texts.items()
    }
    return digests, source_index


def _roles(row: Mapping[str, Any]) -> set[str]:
    bindings = row.get("asset_role_bindings")
    if not isinstance(bindings, list) or not all(isinstance(item, Mapping) for item in bindings):
        raise MaterialRegistryError(
            f"asset_role_bindings_invalid:{row.get('selected_source_unit_ref')}"
        )
    roles = {
        str(item.get("asset_role") or "")
        for item in bindings
        if item.get("binding_status") == "SAFE_PRIVATE_SOURCE_ROLE_BOUND"
    }
    if "" in roles:
        raise MaterialRegistryError("asset_role_empty")
    return roles


def _authority_refs(row: Mapping[str, Any]) -> dict[str, list[str]]:
    value = row.get("authority_refs_by_type")
    if not isinstance(value, Mapping):
        raise MaterialRegistryError(
            f"authority_refs_by_type_invalid:{row.get('selected_source_unit_ref')}"
        )
    result: dict[str, list[str]] = {}
    for key in ("THEME", "VOCABULARY", "CHUNK", "PATTERN", "GRAMMAR"):
        refs = value.get(key, [])
        if not isinstance(refs, list) or not all(isinstance(ref, str) and ref for ref in refs):
            raise MaterialRegistryError(f"authority_ref_list_invalid:{key}")
        result[key] = sorted(set(refs))
    return result


def _lesson_links(
    lessons: Sequence[Mapping[str, Any]],
    *,
    level: str,
    skill: str,
    requirement_refs: set[str],
) -> tuple[list[str], list[str]]:
    lesson_ids: list[str] = []
    matched_requirements: set[str] = set()
    for lesson in lessons:
        if lesson.get("level") != level or lesson.get("skill") != skill:
            continue
        requirements = {
            str(value) for value in lesson.get("requirement_node_ids", [])
            if isinstance(value, str) and value
        }
        overlap = requirements & requirement_refs
        if overlap:
            lesson_id = str(lesson.get("lesson_id") or "")
            if not lesson_id:
                raise MaterialRegistryError("mainline_lesson_id_missing")
            lesson_ids.append(lesson_id)
            matched_requirements.update(overlap)
    return sorted(set(lesson_ids)), sorted(matched_requirements)


def _safe_mainline_record(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "origin": "MAINLINE_M2",
        "asset_key": str(row.get("asset_key") or ""),
        "lesson_id": str(row.get("lesson_id") or ""),
        "skill": str(row.get("skill") or ""),
        "level": str(row.get("level") or ""),
        "role": str(row.get("role") or ""),
        "content_digest": str(row.get("content_digest") or ""),
    }


def query_combined_index(
    mainline_index: Mapping[str, Any],
    extension_package: Mapping[str, Any],
    *,
    skill: str | None = None,
    level: str | None = None,
    lesson_id: str | None = None,
    role: str | None = None,
    requirement_node_id: str | None = None,
    authority_ref: str | None = None,
    asset_role: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    if extension_package.get("validation_status") != PASS_STATUS:
        raise MaterialRegistryError("extension_status_invalid")
    gate = extension_package.get("mainline_consumer_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != "MAINLINE_M2_CONSUMER_EXTENSION_READY":
        raise MaterialRegistryError("extension_gate_invalid")
    if skill is not None and skill not in SKILL_BY_ROLE.values():
        raise MaterialRegistryError("query_skill_invalid")
    if level == "A2":
        raise MaterialRegistryError("A2_PAYLOAD_LOCKED")
    if level is not None and level not in {"A1", "A1+"}:
        raise MaterialRegistryError("query_level_invalid")
    if offset < 0 or limit < 1 or limit > MAX_COMBINED_QUERY_LIMIT:
        raise MaterialRegistryError("query_page_invalid")

    mainline_rows: list[dict[str, Any]] = []
    if authority_ref is None and asset_role is None:
        try:
            result = m2.query_index(
                dict(mainline_index),
                skill=skill,
                level=level,
                lesson_id=lesson_id,
                role=role,
                requirement_node_id=requirement_node_id,
                offset=0,
                limit=m2.MAX_QUERY_LIMIT,
            )
        except m2.ConsumerError as exc:
            if lesson_id is not None or requirement_node_id is not None:
                result = {"asset_records": []}
            else:
                raise MaterialRegistryError(f"mainline_query_failed:{exc}") from exc
        mainline_rows = [_safe_mainline_record(row) for row in result.get("asset_records", [])]

    extension_rows: list[dict[str, Any]] = []
    for row in extension_package.get("mainline_extension_records", []):
        if skill is not None and row.get("skill") != skill:
            continue
        if level is not None and row.get("level") != level:
            continue
        if lesson_id is not None and lesson_id not in row.get("mainline_lesson_ids", []):
            continue
        if role is not None and row.get("role") != role:
            continue
        if requirement_node_id is not None and requirement_node_id not in row.get(
            "matched_mainline_requirement_node_ids", []
        ):
            continue
        if authority_ref is not None and authority_ref not in row.get(
            "all_canonical_authority_refs", []
        ):
            continue
        if asset_role is not None and asset_role not in row.get("material_asset_roles", []):
            continue
        extension_rows.append(dict(row))

    rows = sorted(
        mainline_rows + extension_rows,
        key=lambda row: (str(row.get("origin")), str(row.get("skill")), str(row.get("asset_key"))),
    )
    page = rows[offset : offset + limit]
    return {
        "query_status": "PASS_MAINLINE_M2_COMBINED_QUERY",
        "total_match_count": len(rows),
        "mainline_match_count": len(mainline_rows),
        "raz_extension_match_count": len(extension_rows),
        "offset": offset,
        "limit": limit,
        "returned_count": len(page),
        "records": page,
        "a2_payload_included": False,
        "learner_release_claimed": False,
    }


def build_package(
    resolution_package: Mapping[str, Any],
    mainline_index: Mapping[str, Any],
    private_source_digests: Mapping[str, str],
    private_source_index: Sequence[Mapping[str, Any]],
    *,
    mainline_index_sha256: str,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    rows, bindings = _verify_resolution(
        resolution_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    mainline_assets, mainline_lessons = _verify_mainline(mainline_index)
    promoted: list[dict[str, Any]] = []
    remediation: list[dict[str, Any]] = []
    support: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    extension: list[dict[str, Any]] = []
    lane_counts: Counter[str] = Counter()
    cefr_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    seen_groups: set[str] = set()
    seen_sources: set[str] = set()
    material_ids: set[str] = set()
    extension_keys: set[str] = set()

    for row in sorted(rows, key=lambda item: str(item.get("semantic_duplicate_group_id"))):
        group = str(row.get("semantic_duplicate_group_id") or "")
        source_ref = str(row.get("selected_source_unit_ref") or "")
        lane = str(row.get("admission_resolution") or "")
        scope = str(row.get("candidate_cefr_scope") or "")
        if not group or group in seen_groups:
            raise MaterialRegistryError("semantic_group_missing_or_duplicate")
        if not source_ref or source_ref in seen_sources:
            raise MaterialRegistryError("source_ref_missing_or_duplicate")
        if lane not in LANES:
            raise MaterialRegistryError(f"admission_resolution_invalid:{source_ref}:{lane}")
        if source_ref not in private_source_digests:
            raise MaterialRegistryError(f"private_source_ref_missing:{source_ref}")
        digest = private_source_digests[source_ref]
        if not isinstance(digest, str) or len(digest) != 64:
            raise MaterialRegistryError(f"private_source_digest_invalid:{source_ref}")
        seen_groups.add(group)
        seen_sources.add(source_ref)
        lane_counts[lane] += 1
        authorities = _authority_refs(row)
        roles = _roles(row)
        base = {
            "semantic_duplicate_group_id": group,
            "selected_source_unit_ref": source_ref,
            "source_level": str(row.get("source_level") or ""),
            "source_book_id": str(row.get("source_book_id") or ""),
            "authority_refs_by_type": authorities,
            "canonical_egp_row_refs": list(row.get("canonical_egp_row_refs") or []),
            "asset_role_bindings": [dict(value) for value in row.get("asset_role_bindings") or []],
            "private_source_content_sha256": digest,
        }
        if lane == "PROMOTION_ELIGIBLE":
            if scope not in LEVEL_TO_M2:
                raise MaterialRegistryError(f"promoted_scope_invalid:{source_ref}:{scope}")
            material_id = _material_id(group, source_ref)
            if material_id in material_ids:
                raise MaterialRegistryError("material_id_collision")
            material_ids.add(material_id)
            level = LEVEL_TO_M2[scope]
            skill_roles = sorted(roles & set(SKILL_BY_ROLE))
            material_roles = sorted(roles - set(SKILL_BY_ROLE))
            if not skill_roles or "SENTENCE_ASSET_CANDIDATE" not in material_roles:
                raise MaterialRegistryError(f"promoted_asset_roles_incomplete:{source_ref}")
            all_authority_refs = sorted(
                {ref for values in authorities.values() for ref in values}
            )
            requirement_refs = set(all_authority_refs) | set(base["canonical_egp_row_refs"])
            material_extension_keys: list[str] = []
            for skill_role in skill_roles:
                skill = SKILL_BY_ROLE[skill_role]
                asset_key = _asset_key(material_id, skill)
                if asset_key in extension_keys:
                    raise MaterialRegistryError("extension_asset_key_collision")
                extension_keys.add(asset_key)
                lesson_ids, matched_requirements = _lesson_links(
                    mainline_lessons,
                    level=level,
                    skill=skill,
                    requirement_refs=requirement_refs,
                )
                extension.append({
                    "origin": "RAZ_DERIVED_EXTENSION",
                    "asset_key": asset_key,
                    "asset_id": material_id,
                    "material_id": material_id,
                    "semantic_duplicate_group_id": group,
                    "selected_source_unit_ref": source_ref,
                    "skill": skill,
                    "level": level,
                    "role": skill_role,
                    "material_asset_roles": material_roles,
                    "authority_refs_by_type": authorities,
                    "all_canonical_authority_refs": all_authority_refs,
                    "canonical_egp_row_refs": list(base["canonical_egp_row_refs"]),
                    "mainline_lesson_ids": lesson_ids,
                    "matched_mainline_requirement_node_ids": matched_requirements,
                    "private_source_content_sha256": digest,
                    "private_source_resolution": "RAZ_PAGE_UNIT_BY_SOURCE_REF",
                    "release_scope": "PRIVATE_INTERNAL_DERIVED_EXTENSION",
                })
                material_extension_keys.append(asset_key)
                skill_counts[skill] += 1
                role_counts[skill_role] += 1
            role_counts.update(material_roles)
            cefr_counts[scope] += 1
            promoted.append({
                "material_id": material_id,
                **base,
                "candidate_cefr_scope": scope,
                "mainline_level": level,
                "extension_asset_keys": material_extension_keys,
                "material_asset_roles": material_roles,
                "skill_asset_roles": skill_roles,
                "registry_status": "INTEGRATED_WITH_MAINLINE_M2_CONSUMER",
                "source_payload_access": "PRIVATE_SOURCE_RESOLVER_REQUIRED",
            })
        elif lane == "REMEDIATION_REQUIRED":
            remediation.append({
                **base,
                "remediation_status": "PENDING_CONTROLLED_REWRITE_EVIDENCE",
                "promotion_status": "NOT_PROMOTED",
            })
        elif lane == "SUPPORT_ADMITTED":
            support.append({**base, "support_status": "ADMITTED_SUPPORT_ONLY"})
        else:
            rejected.append({**base, "rejection_status": "CLOSED_UNUSABLE"})

    provisional: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "input_identity": {},
        "mainline_extension_records": extension,
        "mainline_consumer_gate": {
            "decision": "MAINLINE_M2_CONSUMER_EXTENSION_READY"
        },
    }
    common_proof: dict[str, Any] | None = None
    for skill in sorted(SKILL_BY_ROLE.values()):
        for level in ("A1", "A1+"):
            result = query_combined_index(
                mainline_index, provisional, skill=skill, level=level, limit=100
            )
            if result["mainline_match_count"] and result["raz_extension_match_count"]:
                common_proof = {
                    "skill": skill,
                    "level": level,
                    "mainline_match_count": result["mainline_match_count"],
                    "raz_extension_match_count": result["raz_extension_match_count"],
                }
                break
        if common_proof:
            break
    authority_proof = None
    role_proof = None
    if extension:
        first = extension[0]
        authority = first["all_canonical_authority_refs"][0]
        authority_result = query_combined_index(
            mainline_index, provisional, authority_ref=authority, limit=100
        )
        authority_proof = {
            "authority_ref": authority,
            "raz_extension_match_count": authority_result[
                "raz_extension_match_count"
            ],
        }
        role = first["material_asset_roles"][0]
        role_result = query_combined_index(
            mainline_index, provisional, asset_role=role, limit=100
        )
        role_proof = {
            "asset_role": role,
            "raz_extension_match_count": role_result["raz_extension_match_count"],
        }
    a2_locked = False
    try:
        query_combined_index(mainline_index, provisional, level="A2")
    except MaterialRegistryError as exc:
        a2_locked = str(exc) == "A2_PAYLOAD_LOCKED"

    checks = {
        "all_semantic_identities_reconciled_once": (
            len(promoted) + len(remediation) + len(support) + len(rejected)
            == expected_semantic_identity_count
            and len(seen_groups) == expected_semantic_identity_count
            and len(seen_sources) == expected_semantic_identity_count
        ),
        "promotion_count_matches_eligible_count": (
            len(promoted) == lane_counts["PROMOTION_ELIGIBLE"]
        ),
        "promoted_material_ids_unique": len(material_ids) == len(promoted),
        "every_promoted_material_has_extension_asset": all(
            row["extension_asset_keys"] for row in promoted
        ),
        "extension_asset_keys_unique": len(extension_keys) == len(extension),
        "private_source_digest_complete": len(private_source_digests) == expected_scope_page_unit_count
        and all(row["private_source_content_sha256"] for row in promoted),
        "canonical_authority_complete": all(
            row["authority_refs_by_type"]["VOCABULARY"]
            and row["authority_refs_by_type"]["GRAMMAR"]
            for row in promoted
        ),
        "combined_mainline_and_extension_query_proven": common_proof is not None,
        "authority_query_proven": bool(
            authority_proof and authority_proof["raz_extension_match_count"]
        ),
        "asset_role_query_proven": bool(role_proof and role_proof["raz_extension_match_count"]),
        "at_least_one_real_mainline_lesson_link": any(
            row["mainline_lesson_ids"] for row in extension
        ),
        "noneligible_lanes_not_promoted": all(
            "material_id" not in row for row in remediation + support + rejected
        ),
        "a2_a2plus_locked": a2_locked,
        "duplicate_bindings_preserved": len(bindings) == expected_duplicate_binding_count,
    }
    ready = all(checks.values()) and bool(promoted) and bool(extension)
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "admission_resolution_task_id": resolution_package["task_id"],
            "admission_resolution_package_sha256": resolution_package["package_sha256"],
            "mainline_m2_task_id": mainline_index["task_id"],
            "mainline_m2_index_sha256": mainline_index_sha256,
        },
        "scope_contract": dict(resolution_package["scope_contract"]),
        "private_source_index": [dict(row) for row in private_source_index],
        "mainline_m2_summary": {
            "asset_record_count": len(mainline_assets),
            "lesson_count": len(mainline_lessons),
            "a2_payload_query_allowed": False,
        },
        "promoted_material_registry": promoted,
        "mainline_extension_records": extension,
        "remediation_queue": remediation,
        "support_registry": support,
        "rejected_registry": rejected,
        "duplicate_bindings": [dict(row) for row in bindings],
        "consumer_query_proof": {
            "combined_origin_query": common_proof,
            "authority_query": authority_proof,
            "asset_role_query": role_proof,
            "a2_lock_verified": a2_locked,
        },
        "aggregate_summary": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": expected_semantic_identity_count,
            "duplicate_binding_count": len(bindings),
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "lane_counts": dict(sorted(lane_counts.items())),
            "promoted_cefr_scope_counts": dict(sorted(cefr_counts.items())),
            "mainline_extension_skill_counts": dict(sorted(skill_counts.items())),
            "asset_role_binding_counts": dict(sorted(role_counts.items())),
            "final_promoted_material_count": len(promoted),
            "mainline_extension_asset_count": len(extension),
            "mainline_lesson_linked_extension_asset_count": sum(
                bool(row["mainline_lesson_ids"]) for row in extension
            ),
            "remediation_queue_count": len(remediation),
            "support_registry_count": len(support),
            "rejected_registry_count": len(rejected),
        },
        "mainline_consumer_gate": {
            "source_checks": checks,
            "decision": (
                "MAINLINE_M2_CONSUMER_EXTENSION_READY"
                if ready else "BLOCKED_MAINLINE_M2_CONSUMER_EXTENSION"
            ),
            "distance_before": "D2",
            "distance_after": "D1" if ready else "D2",
            "ready_for_end_to_end_d0_recloseout": ready,
            "ready_for_learner_facing_release": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise MaterialRegistryError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _read_json_object(path: Path, code: str) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MaterialRegistryError(f"{code}_json_invalid") from exc
    if not isinstance(value, dict):
        raise MaterialRegistryError(f"{code}_not_object")
    return value, hashlib.sha256(raw).hexdigest()


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["mainline_consumer_gate"]["decision"],
        "distance_after": package["mainline_consumer_gate"]["distance_after"],
        **package["aggregate_summary"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission-resolution-package", type=Path, default=DEFAULT_RESOLUTION)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--mainline-consumer", type=Path, default=DEFAULT_MAINLINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        resolution_package, _ = _read_json_object(
            args.admission_resolution_package, "resolution"
        )
        mainline_index, mainline_sha = _read_json_object(
            args.mainline_consumer, "mainline"
        )
        source_digests, source_index = load_private_sources(args.source_root)
        output = build_package(
            resolution_package,
            mainline_index,
            source_digests,
            source_index,
            mainline_index_sha256=mainline_sha,
        )
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (
        MaterialRegistryError,
        resolution.AdmissionResolutionError,
        m2.ConsumerError,
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
