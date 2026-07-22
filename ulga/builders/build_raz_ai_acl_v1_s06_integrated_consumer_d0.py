#!/usr/bin/env python3
"""Build the metadata-only RAZ/mainline consumer overlay and close ACL V1 at D0.

The index joins the existing A1FS M2 Asset Body consumer metadata with the S05
RAZ material registry, restores Sentence/Core Sentence/Passage/four-skill roles
from S02, proves bounded queries, and keeps all source text, learner-facing
payloads, canonical Authority writes, and A2/A2+ content outside the output.
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
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S06_IntegratedMainlineConsumerAndD0Closeout"
SCHEMA_VERSION = "raz.ai.acl.v1.s06.integrated_mainline_consumer_d0.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S06_INTEGRATED_MAINLINE_CONSUMER_D0"
PROGRAM_ID = "RAZ-AI-ACL-V1"

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
DEFAULT_RESOLUTION = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s04_admission_resolution/"
    / "rewrite_admission_resolution.safe.json"
)
DEFAULT_REGISTRY = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s05_material_registry/"
    / "a1_a1plus_material_registry.safe.json"
)
DEFAULT_MAINLINE = (
    REPO_ROOT / ".local/a1fs_v1/m2/"
    / "four_skill_asset_body_consumer.private.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s06_d0/"
    / "integrated_mainline_material_consumer.safe.json"
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
    "mainline_payload_traversal_performed": False,
    "mainline_payload_included_in_output": False,
    "metadata_only_integrated_consumer": True,
    "canonical_authority_write_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_payload_query_performed": False,
    "a2_a2plus_rows_remain_deferred": True,
    "mastery_or_retention_claimed": False,
}


class IntegratedConsumerError(ValueError):
    """Fail-closed lineage, query, scope, or reconciliation error."""


def _verify_hash(package: Mapping[str, Any], label: str) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise IntegratedConsumerError(f"{label}_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise IntegratedConsumerError(f"{label}_package_sha256_mismatch")


def _summary_contract(
    package: Mapping[str, Any],
    label: str,
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> Mapping[str, Any]:
    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise IntegratedConsumerError(f"{label}_aggregate_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise IntegratedConsumerError(
                f"{label}_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )
    return summary


def _verify_chain(
    dedup_package: Mapping[str, Any],
    linkage_package: Mapping[str, Any],
    resolution_package: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    stages = (
        (
            "dedup",
            dedup_package,
            dedup.TASK_ID,
            dedup.PASS_STATUS,
            "dedup_gate",
            "SEMANTIC_DEDUP_REPRESENTATIVES_READY",
        ),
        (
            "linkage",
            linkage_package,
            linkage.TASK_ID,
            linkage.PASS_STATUS,
            "authority_linkage_gate",
            "AUTHORITY_LINKAGE_READY",
        ),
        (
            "resolution",
            resolution_package,
            resolution.TASK_ID,
            resolution.PASS_STATUS,
            "admission_resolution_gate",
            "ADMISSION_RESOLUTION_READY",
        ),
        (
            "registry",
            registry_package,
            registry.TASK_ID,
            registry.PASS_STATUS,
            "material_registry_gate",
            "A1_A1PLUS_MATERIAL_REGISTRY_READY",
        ),
    )
    for label, package, task_id, status, gate_name, decision in stages:
        if package.get("task_id") != task_id:
            raise IntegratedConsumerError(f"{label}_task_id_mismatch")
        if package.get("validation_status") != status:
            raise IntegratedConsumerError(f"{label}_validation_status_not_pass")
        if package.get("errors") != []:
            raise IntegratedConsumerError(f"{label}_errors_not_empty")
        _verify_hash(package, label)
        gate = package.get(gate_name)
        if not isinstance(gate, Mapping) or gate.get("decision") != decision:
            raise IntegratedConsumerError(f"{label}_gate_not_ready")
        _summary_contract(
            package,
            label,
            expected_total_page_unit_count=expected_total_page_unit_count,
            expected_scope_page_unit_count=expected_scope_page_unit_count,
            expected_semantic_identity_count=expected_semantic_identity_count,
            expected_duplicate_binding_count=expected_duplicate_binding_count,
            expected_deferred_page_unit_count=expected_deferred_page_unit_count,
        )

    if linkage_package.get("input_identity", {}).get(
        "dedup_package_sha256"
    ) != dedup_package.get("package_sha256"):
        raise IntegratedConsumerError("linkage_dedup_lineage_mismatch")
    if resolution_package.get("input_identity", {}).get(
        "authority_linkage_package_sha256"
    ) != linkage_package.get("package_sha256"):
        raise IntegratedConsumerError("resolution_linkage_lineage_mismatch")
    if registry_package.get("input_identity", {}).get(
        "admission_resolution_package_sha256"
    ) != resolution_package.get("package_sha256"):
        raise IntegratedConsumerError("registry_resolution_lineage_mismatch")

    representatives = dedup_package.get("semantic_representatives")
    promoted = registry_package.get("promoted_material_registry")
    if not isinstance(representatives, list) or not all(
        isinstance(row, Mapping) for row in representatives
    ):
        raise IntegratedConsumerError("semantic_representatives_invalid")
    if not isinstance(promoted, list) or not all(
        isinstance(row, Mapping) for row in promoted
    ):
        raise IntegratedConsumerError("promoted_material_registry_invalid")
    if len(representatives) != expected_semantic_identity_count:
        raise IntegratedConsumerError("semantic_representative_count_mismatch")
    if len(promoted) != registry_package["aggregate_summary"].get(
        "final_promoted_material_count"
    ):
        raise IntegratedConsumerError("promoted_material_count_mismatch")
    if not promoted:
        raise IntegratedConsumerError("promoted_material_registry_empty")
    return representatives, promoted


def _verify_mainline(index: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int]:
    if index.get("task_id") != m2.TASK_ID:
        raise IntegratedConsumerError("mainline_consumer_task_id_mismatch")
    if index.get("schema_version") != m2.SCHEMA_VERSION:
        raise IntegratedConsumerError("mainline_consumer_schema_version_mismatch")
    if index.get("validation_status") != m2.STATUS:
        raise IntegratedConsumerError("mainline_consumer_status_not_pass")
    access = index.get("access_contract")
    if not isinstance(access, Mapping) or access.get("a2_payload_query_allowed") is not False:
        raise IntegratedConsumerError("mainline_a2_lock_invalid")
    records = index.get("asset_records")
    catalog = index.get("lesson_catalog")
    if not isinstance(records, list) or not all(isinstance(row, Mapping) for row in records):
        raise IntegratedConsumerError("mainline_asset_records_invalid")
    if not isinstance(catalog, list) or not all(isinstance(row, Mapping) for row in catalog):
        raise IntegratedConsumerError("mainline_lesson_catalog_invalid")
    requirement_by_lesson = {
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
            raise IntegratedConsumerError(f"mainline_level_invalid:{level}")
        asset_key = str(row.get("asset_key") or row.get("asset_id") or "")
        lesson_id = str(row.get("lesson_id") or "")
        skill = str(row.get("skill") or "")
        role = str(row.get("role") or "")
        if not asset_key or not lesson_id or not skill or not role:
            raise IntegratedConsumerError("mainline_asset_metadata_incomplete")
        # Deliberately do not read row['payload'].
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
                    {
                        "authority_type": "REQUIREMENT_NODE",
                        "authority_ref": ref,
                    }
                    for ref in requirement_by_lesson.get(lesson_id, [])
                ],
                "payload_access": "EXISTING_PRIVATE_M2_CONSUMER",
                "learner_facing": False,
            }
        )
    if not safe_rows:
        raise IntegratedConsumerError("mainline_a1_a1plus_assets_empty")
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
        raise IntegratedConsumerError("four_skill_affordances_invalid")
    skills = sorted({SKILL_MAP[value] for value in affordances if value in SKILL_MAP})
    if not skills:
        raise IntegratedConsumerError("raz_material_skill_projection_empty")
    return sorted(roles), skills


def _raz_rows(
    representatives: Sequence[Mapping[str, Any]],
    promoted: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    representative_by_group = {
        str(row.get("semantic_duplicate_group_id") or ""): row
        for row in representatives
    }
    if "" in representative_by_group or len(representative_by_group) != len(
        representatives
    ):
        raise IntegratedConsumerError("representative_group_missing_or_duplicate")
    rows: list[dict[str, Any]] = []
    seen_material_ids: set[str] = set()
    for material in promoted:
        group = str(material.get("semantic_duplicate_group_id") or "")
        source_ref = str(material.get("selected_source_unit_ref") or "")
        material_id = str(material.get("material_id") or "")
        representative = representative_by_group.get(group)
        if representative is None:
            raise IntegratedConsumerError(f"promoted_group_not_in_dedup:{group}")
        if source_ref != representative.get("selected_source_unit_ref"):
            raise IntegratedConsumerError(f"promoted_source_ref_mismatch:{group}")
        if not material_id or material_id in seen_material_ids:
            raise IntegratedConsumerError("promoted_material_id_missing_or_duplicate")
        seen_material_ids.add(material_id)
        scope = str(material.get("candidate_cefr_scope") or "")
        if scope not in {"A1", "A1_PLUS"}:
            raise IntegratedConsumerError(f"promoted_scope_invalid:{material_id}:{scope}")
        links = material.get("authority_links")
        if not isinstance(links, list) or not all(isinstance(link, Mapping) for link in links):
            raise IntegratedConsumerError(f"promoted_authority_links_invalid:{material_id}")
        types = {str(link.get("authority_type") or "") for link in links}
        if not {"VOCABULARY", "GRAMMAR"} <= types:
            raise IntegratedConsumerError(f"promoted_required_authority_missing:{material_id}")
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
        raise IntegratedConsumerError("index_status_invalid")
    if level in {"A2", "A2+", "A2_PLUS"}:
        raise IntegratedConsumerError("A2_QUERY_LOCKED")
    if level is not None and level not in {"A1", "A1+"}:
        raise IntegratedConsumerError("query_level_invalid")
    if source_type is not None and source_type not in {
        "MAINLINE_ASSET_BODY",
        "RAZ_DERIVED_MATERIAL",
    }:
        raise IntegratedConsumerError("query_source_type_invalid")
    if skill is not None and skill not in {"READING", "LISTENING", "SPEAKING", "WRITING"}:
        raise IntegratedConsumerError("query_skill_invalid")
    if offset < 0 or limit < 1 or limit > 100:
        raise IntegratedConsumerError("query_page_invalid")
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


def build_index(
    dedup_package: Mapping[str, Any],
    linkage_package: Mapping[str, Any],
    resolution_package: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    mainline_index: Mapping[str, Any],
    *,
    mainline_index_sha256: str,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    representatives, promoted = _verify_chain(
        dedup_package,
        linkage_package,
        resolution_package,
        registry_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    if not isinstance(mainline_index_sha256, str) or len(mainline_index_sha256) != 64:
        raise IntegratedConsumerError("mainline_index_sha256_invalid")
    mainline_rows, a2_mainline_skipped = _verify_mainline(mainline_index)
    raz_rows = _raz_rows(representatives, promoted)
    integrated_rows = sorted(
        mainline_rows + raz_rows,
        key=lambda row: (row["source_type"], row["level"], row["integrated_ref"]),
    )
    integrated_refs = [row["integrated_ref"] for row in integrated_rows]
    authority_type_refs: dict[str, set[str]] = {}
    role_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    for row in raz_rows:
        role_counts.update(row["material_roles"])
        skill_counts.update(row["skills"])
        for link in row["authority_links"]:
            authority_type_refs.setdefault(str(link["authority_type"]), set()).add(
                str(link["authority_ref"])
            )

    core: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "program_id": PROGRAM_ID,
        "input_identity": {
            "dedup_package_sha256": dedup_package["package_sha256"],
            "linkage_package_sha256": linkage_package["package_sha256"],
            "resolution_package_sha256": resolution_package["package_sha256"],
            "registry_package_sha256": registry_package["package_sha256"],
            "mainline_consumer_task_id": mainline_index["task_id"],
            "mainline_consumer_sha256": mainline_index_sha256,
        },
        "scope_contract": {
            "levels": ["A1", "A1+"],
            "a2_a2plus_status": "LOCKED_AND_DEFERRED",
            "consumer_mode": "METADATA_ONLY_PRIVATE_SOURCE_ROUTING",
            "max_query_limit": 100,
        },
        "integrated_materials": integrated_rows,
        "aggregate_summary": {
            "mainline_material_count": len(mainline_rows),
            "raz_promoted_material_count": len(raz_rows),
            "integrated_material_count": len(integrated_rows),
            "mainline_a2_asset_count_skipped": a2_mainline_skipped,
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "linked_theme_ref_count": len(authority_type_refs.get("THEME", set())),
            "linked_vocabulary_ref_count": len(authority_type_refs.get("VOCABULARY", set())),
            "linked_chunk_ref_count": len(authority_type_refs.get("CHUNK", set())),
            "linked_pattern_ref_count": len(authority_type_refs.get("PATTERN", set())),
            "linked_grammar_ref_count": len(authority_type_refs.get("GRAMMAR", set())),
            "linked_sentence_candidate_count": role_counts["SENTENCE_CANDIDATE"],
            "linked_core_sentence_candidate_count": (
                role_counts["STRICT_CORE_SENTENCE_CANDIDATE"]
                + role_counts["BROAD_CORE_SENTENCE_CANDIDATE"]
            ),
            "linked_passage_candidate_count": role_counts["PASSAGE_CANDIDATE"],
            "four_skill_candidate_counts": dict(sorted(skill_counts.items())),
            "remediation_queue_count": registry_package["aggregate_summary"][
                "remediation_queue_count"
            ],
            "support_registry_count": registry_package["aggregate_summary"][
                "support_registry_count"
            ],
            "rejected_registry_count": registry_package["aggregate_summary"][
                "rejected_registry_count"
            ],
        },
        "acceptance_gate": {},
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    if len(integrated_refs) != len(set(integrated_refs)):
        raise IntegratedConsumerError("integrated_ref_collision")
    if not raz_rows or not mainline_rows:
        raise IntegratedConsumerError("integrated_source_partition_empty")

    raz_probe = raz_rows[0]
    probe_link = raz_probe["authority_links"][0]
    mainline_probe = mainline_rows[0]
    raz_result = query_index(
        core,
        source_type="RAZ_DERIVED_MATERIAL",
        level=raz_probe["level"],
        authority_ref=probe_link["authority_ref"],
    )
    mainline_result = query_index(
        core,
        source_type="MAINLINE_ASSET_BODY",
        skill=mainline_probe["skills"][0],
    )
    a2_locked = False
    try:
        query_index(core, level="A2")
    except IntegratedConsumerError as exc:
        a2_locked = str(exc) == "A2_QUERY_LOCKED"

    checks = {
        "mainline_and_raz_sources_present": bool(mainline_rows and raz_rows),
        "integrated_refs_unique": len(integrated_refs) == len(set(integrated_refs)),
        "all_integrated_rows_a1_or_a1plus": all(
            row["level"] in {"A1", "A1+"} for row in integrated_rows
        ),
        "raz_query_proof_pass": any(
            row["integrated_ref"] == raz_probe["integrated_ref"]
            for row in raz_result["integrated_materials"]
        ),
        "mainline_query_proof_pass": any(
            row["integrated_ref"] == mainline_probe["integrated_ref"]
            for row in mainline_result["integrated_materials"]
        ),
        "a2_query_fail_closed": a2_locked,
        "no_learner_facing_rows": all(
            row["learner_facing"] is False for row in integrated_rows
        ),
        "raz_promoted_count_reconciles": len(raz_rows)
        == registry_package["aggregate_summary"]["final_promoted_material_count"],
        "sentence_role_covers_all_raz_materials": role_counts[
            "SENTENCE_CANDIDATE"
        ] == len(raz_rows),
    }
    ready = all(checks.values())
    core["validation_status"] = PASS_STATUS if ready else "FAIL"
    core["acceptance_gate"] = {
        "source_checks": checks,
        "decision": "RAZ_AI_ACL_V1_D0_ACCEPTED" if ready else "BLOCKED_D0_ACCEPTANCE",
        "distance_before": "D1",
        "distance_after": "D0" if ready else "D1",
        "program_status": "PASS_ACCEPTED_AND_CLOSED" if ready else "BLOCKED",
        "mainline_consumer_proof": ready,
        "a2_lock_status": "PASS_LOCKED" if a2_locked else "FAIL",
        "learner_facing_release_claimed": False,
    }
    leakage = matching.scan_forbidden_safe_keys(core)
    if leakage:
        raise IntegratedConsumerError(
            "safe_output_leakage:" + ";".join(leakage[:20])
        )
    core["package_sha256"] = deep.sha256_value(core)
    return core


def _read_json(path: Path, code: str) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IntegratedConsumerError(f"{code}_json_invalid") from exc
    if not isinstance(value, dict):
        raise IntegratedConsumerError(f"{code}_not_object")
    return value, deep.sha256_file(path)


def _readback(index: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": index["acceptance_gate"]["decision"],
        "program_status": index["acceptance_gate"]["program_status"],
        "distance_after": index["acceptance_gate"]["distance_after"],
        **index["aggregate_summary"],
        "package_sha256": index["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dedup-package", type=Path, default=DEFAULT_DEDUP)
    parser.add_argument("--authority-linkage-package", type=Path, default=DEFAULT_LINKAGE)
    parser.add_argument("--admission-resolution-package", type=Path, default=DEFAULT_RESOLUTION)
    parser.add_argument("--material-registry-package", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--mainline-consumer", type=Path, default=DEFAULT_MAINLINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        dedup_package, _ = _read_json(args.dedup_package, "dedup")
        linkage_package, _ = _read_json(args.authority_linkage_package, "linkage")
        resolution_package, _ = _read_json(args.admission_resolution_package, "resolution")
        registry_package, _ = _read_json(args.material_registry_package, "registry")
        mainline_index, mainline_sha = _read_json(args.mainline_consumer, "mainline")
        index = build_index(
            dedup_package,
            linkage_package,
            resolution_package,
            registry_package,
            mainline_index,
            mainline_index_sha256=mainline_sha,
        )
        deep.write_json_atomic(args.output, index)
        print(json.dumps(_readback(index), sort_keys=True))
        return 0
    except (
        IntegratedConsumerError,
        dedup.SemanticDedupError,
        linkage.AuthorityLinkageError,
        resolution.AdmissionResolutionError,
        registry.MaterialRegistryError,
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
