#!/usr/bin/env python3
"""Build the metadata-only CP07A unified runtime activity index.

The adapter joins the existing KET M2 consumer, the approved CP05 private
RAZ/M11B bank, and CP06 spiral-role metadata.  It emits identities, lineage,
readiness, and query contracts only.  It never copies KET payloads, RAZ source
text, prompts, scoring contracts, learner responses, or media.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05  # noqa: E402
from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as cp06  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only source-lineage and runtime-query adapter over governed KET, CP05, and CP06 artifacts; no learner-facing content, prompt, scoring contract, source text, media, response, mastery, or canonical Authority mutation is produced."

TASK_ID = "A1FS-V1-CP07A_UnifiedRuntimeActivityContractAndSourceLineageAdapter"
PROGRAM_ID = cp06.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.cp07a.unified_runtime_activity_index.v1"
PASS_STATUS = "PASS_CP07A_UNIFIED_RUNTIME_ACTIVITY_INDEX_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07B_KET99CanonicalMappingAndInstructionalSequenceOverlay"

DEFAULT_M2 = REPO_ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
DEFAULT_CP05_APPROVED = cp05.DEFAULT_APPROVED_OUTPUT
DEFAULT_CP06 = cp06.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07a/unified_runtime_activity_index.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07a/unified_runtime_activity_index.validation.json"

SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
LEVELS = ("A1", "A1_PLUS")
SOURCE_KINDS = ("KET_ASSET_BODY", "RAZ_ACTIVITY_BINDING", "M11B_REVIEWED_ACTIVITY")
CONTENT_ROLES = ("FOCUS", "RECYCLE", "CONTRAST", "TRANSFER")
MAX_QUERY_LIMIT = 100
FORBIDDEN_CONTENT_KEYS = {
    "payload", "source_content", "text", "prompt", "scoring_contract",
    "correct_answer", "answer_key", "learner_response", "recording", "audio_bytes",
}


class CP07ABuildError(ValueError):
    """Fail-closed source-lineage, identity, readiness, or query error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CP07ABuildError(f"json_object_required:{path}")
    return value


def _write_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    if not parts or any(not str(part) for part in parts):
        raise CP07ABuildError("stable_identity_component_missing")
    value = hashlib.sha256("\0".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:24]
    return f"A1FS_CP07A_{prefix}_{value}"


def _normalize_level(value: Any) -> str:
    normalized = str(value or "").upper().replace("+", "_PLUS")
    if normalized not in LEVELS:
        raise CP07ABuildError(f"level_outside_a1_a1plus:{value}")
    return normalized


def _assert_safe(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_CONTENT_KEYS:
                raise CP07ABuildError(f"private_content_key_forbidden:{path}.{key}")
            _assert_safe(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_safe(child, f"{path}[{index}]")


def _verify_m2(index: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if index.get("task_id") != m2.TASK_ID or index.get("schema_version") != m2.SCHEMA_VERSION:
        raise CP07ABuildError("m2_contract_invalid")
    if index.get("validation_status") != m2.STATUS or index.get("errors") != []:
        raise CP07ABuildError("m2_not_passed")
    access = index.get("access_contract")
    if not isinstance(access, Mapping) or access.get("a2_payload_query_allowed") is not False:
        raise CP07ABuildError("m2_a2_payload_lock_not_enforced")
    assets, catalog = index.get("asset_records"), index.get("lesson_catalog")
    if not isinstance(assets, list) or not isinstance(catalog, list):
        raise CP07ABuildError("m2_asset_or_catalog_list_required")
    catalog_by_lesson: dict[str, Mapping[str, Any]] = {}
    for row in catalog:
        if not isinstance(row, Mapping):
            raise CP07ABuildError("m2_catalog_row_invalid")
        lesson_id = str(row.get("lesson_id") or "")
        if not lesson_id or lesson_id in catalog_by_lesson:
            raise CP07ABuildError("m2_lesson_id_missing_or_duplicate")
        catalog_by_lesson[lesson_id] = row
    learning_assets: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for row in assets:
        if not isinstance(row, Mapping):
            raise CP07ABuildError("m2_asset_row_invalid")
        key, lesson_id = str(row.get("asset_key") or ""), str(row.get("lesson_id") or "")
        if not key or key in seen or lesson_id not in catalog_by_lesson or row.get("skill") not in SKILLS:
            raise CP07ABuildError("m2_asset_identity_invalid")
        seen.add(key)
        if row.get("level") == "A2":
            continue
        _normalize_level(row.get("level"))
        learning_assets.append(row)
    actual_lessons = sum(str(row.get("level")) in {"A1", "A1+"} for row in catalog)
    if actual_lessons != index.get("counts", {}).get("learning_lesson_count"):
        raise CP07ABuildError("m2_learning_lesson_count_mismatch")
    return learning_assets, catalog_by_lesson


def _verify_cp05(approved: Mapping[str, Any]) -> Mapping[str, Any]:
    if approved.get("artifact_role") != content_policy.APPROVED_ROLE:
        raise CP07ABuildError("cp05_approved_artifact_role_invalid")
    if approved.get("admission", {}).get("status") != "APPROVED" or approved.get("learner_facing") is not False:
        raise CP07ABuildError("cp05_admission_contract_invalid")
    try:
        content_policy.verify_artifact_digest(approved)
    except content_policy.ContentPolicyBuildError as exc:
        raise CP07ABuildError(f"cp05_approved_digest_invalid:{exc}") from exc
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise CP07ABuildError("cp05_payload_required")
    if payload.get("task_id") != cp05.TASK_ID or payload.get("schema_version") != cp05.SCHEMA_VERSION:
        raise CP07ABuildError("cp05_payload_identity_invalid")
    if payload.get("scope") != "A1_A1_PLUS_ONLY" or payload.get("stop_reason") != "NONE":
        raise CP07ABuildError("cp05_payload_scope_or_status_invalid")
    if payload.get("coverage_summary", {}).get("existing_learning_unit_count") != 24:
        raise CP07ABuildError("cp05_existing_unit_count_not_24")
    return payload


def _verify_cp06(artifact: Mapping[str, Any]) -> None:
    if artifact.get("task_id") != cp06.TASK_ID or artifact.get("schema_version") != cp06.SCHEMA_VERSION:
        raise CP07ABuildError("cp06_contract_invalid")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY" or artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        raise CP07ABuildError("cp06_scope_or_status_invalid")
    summary = artifact.get("coverage_summary", {})
    if summary.get("existing_learning_unit_count") != 24 or summary.get("new_learning_unit_count") != 0:
        raise CP07ABuildError("cp06_unit_coverage_invalid")
    if summary.get("effective_scene_gap_unit_count") != 0:
        raise CP07ABuildError("cp06_scene_gap_remaining")
    if artifact.get("capacity_gate", {}).get("a2_a2plus_status") != "LOCKED":
        raise CP07ABuildError("cp06_a2_lock_invalid")


def _cp05_indexes(payload: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    sources: dict[str, Mapping[str, Any]] = {}
    for row in payload.get("materialized_raz_sources", []):
        if not isinstance(row, Mapping):
            raise CP07ABuildError("cp05_materialized_source_row_invalid")
        material_id = str(row.get("material_id") or "")
        if not material_id or material_id in sources or row.get("materialization_status") != "MATERIALIZED_PRIVATE_SOURCE_BOUND":
            raise CP07ABuildError("cp05_material_identity_or_status_invalid")
        sources[material_id] = row
    raz: dict[str, Mapping[str, Any]] = {}
    for row in payload.get("raz_unit_activity_bindings", []):
        if not isinstance(row, Mapping):
            raise CP07ABuildError("cp05_raz_binding_row_invalid")
        identity = str(row.get("activity_binding_id") or "")
        if not identity or identity in raz or row.get("admission_status") != "ADMITTED_PRIVATE_SOURCE_BOUND_ACTIVITY":
            raise CP07ABuildError("cp05_raz_binding_identity_or_status_invalid")
        raz[identity] = row
    m11b: dict[str, Mapping[str, Any]] = {}
    for row in payload.get("m11b_reuse_activities", []):
        if not isinstance(row, Mapping):
            raise CP07ABuildError("cp05_m11b_row_invalid")
        identity = str(row.get("activity_id") or "")
        if not identity or identity in m11b or row.get("admission_status") != "REUSED_EXISTING_REVIEWED_ADMISSION":
            raise CP07ABuildError("cp05_m11b_identity_or_status_invalid")
        m11b[identity] = row
    summary = payload.get("coverage_summary", {})
    if len(sources) != summary.get("raz_materialized_source_count"):
        raise CP07ABuildError("cp05_materialized_source_count_mismatch")
    if len(raz) != summary.get("raz_admitted_activity_binding_count"):
        raise CP07ABuildError("cp05_raz_binding_count_mismatch")
    if len(m11b) != summary.get("m11b_reused_activity_count"):
        raise CP07ABuildError("cp05_m11b_count_mismatch")
    return sources, raz, m11b


def _skill_contract(source: Mapping[str, Any], skill: str) -> Mapping[str, Any]:
    rows = source.get("skill_contracts")
    if not isinstance(rows, list):
        raise CP07ABuildError("cp05_skill_contract_list_required")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("skill") == skill]
    if len(matches) != 1:
        raise CP07ABuildError(f"cp05_exact_skill_contract_required:{source.get('material_id')}:{skill}")
    contract = matches[0]
    if not isinstance(contract.get("prompt"), str) or not isinstance(contract.get("scoring_contract"), Mapping):
        raise CP07ABuildError(f"cp05_skill_contract_incomplete:{source.get('material_id')}:{skill}")
    if not str(contract.get("runtime_dependency_status") or ""):
        raise CP07ABuildError(f"cp05_runtime_dependency_missing:{source.get('material_id')}:{skill}")
    return contract


def _raz_readiness(skill: str, dependency: str) -> str:
    expected = {
        "READING": "READY_FOR_TEXT_RUNTIME_INTEGRATION",
        "WRITING": "READY_FOR_TEXT_RUNTIME_INTEGRATION",
        "LISTENING": "AUDIO_GENERATION_REQUIRED",
        "SPEAKING": "RECORDING_CAPTURE_REQUIRED",
    }
    if dependency != expected[skill]:
        raise CP07ABuildError(f"raz_runtime_dependency_mismatch:{skill}:{dependency}")
    return {
        "READING": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
        "WRITING": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
        "LISTENING": "BLOCKED_AUDIO_GENERATION",
        "SPEAKING": "BLOCKED_RECORDING_CAPTURE",
    }[skill]


def build_artifact(m2_index: Mapping[str, Any], cp05_approved: Mapping[str, Any], cp06_artifact: Mapping[str, Any]) -> dict[str, Any]:
    ket_assets, catalog = _verify_m2(m2_index)
    cp05_payload = _verify_cp05(cp05_approved)
    _verify_cp06(cp06_artifact)
    sources, cp05_raz, cp05_m11b = _cp05_indexes(cp05_payload)
    unit_stage = {
        str(row.get("learning_unit_id") or ""): str(row.get("internal_stage") or "")
        for row in cp06_artifact.get("unit_content_capacity", [])
        if isinstance(row, Mapping)
    }
    records: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    readiness_counts: Counter[str] = Counter()
    seen_runtime_ids: set[str] = set()

    def append(record: dict[str, Any]) -> None:
        runtime_id = record["runtime_activity_id"]
        if runtime_id in seen_runtime_ids:
            raise CP07ABuildError("runtime_activity_id_collision")
        seen_runtime_ids.add(runtime_id)
        records.append(record)
        source_counts[record["source_kind"]] += 1
        skill_counts[record["skill"]] += 1
        readiness_counts[record["runtime_readiness"]] += 1

    for asset in sorted(ket_assets, key=lambda row: (str(row["skill"]), str(row["level"]), str(row["lesson_id"]), str(row["asset_key"]))):
        lesson = catalog[str(asset["lesson_id"])]
        append({
            "runtime_activity_id": _stable_id("KET", str(asset["asset_key"])),
            "source_kind": "KET_ASSET_BODY",
            "skill": str(asset["skill"]),
            "level": _normalize_level(asset["level"]),
            "curriculum_binding": {
                "ket_lesson_id": str(asset["lesson_id"]),
                "ket_lesson_node_id": str(lesson.get("lesson_node_id") or ""),
                "requirement_node_ids": sorted({str(value) for value in lesson.get("requirement_node_ids", []) if str(value)}),
                "learning_unit_id": None, "grammar_unit_id": None, "canonical_egp_row_ids": [],
            },
            "instructional_roles": sorted({"FOCUS", str(asset.get("role") or "").upper()} - {""}),
            "source_lineage": {
                "m2_asset_key": str(asset["asset_key"]),
                "m2_content_digest": str(asset["content_digest"]),
                "private_payload_locator": {"consumer_artifact": "M2_FOUR_SKILL_ASSET_BODY_CONSUMER", "asset_key": str(asset["asset_key"])},
            },
            "response_contract_ref": {"authority": "KET_ASSET_BODY_PRIVATE_PAYLOAD", "contract_resolution_status": "RESOLVE_AT_M5_DELIVERY"},
            "runtime_readiness": "QUERYABLE_PRIVATE_KET_ASSET",
            "learner_facing": False,
            "a2_payload_included": False,
        })

    cp06_raz = cp06_artifact.get("raz_activity_role_bindings")
    if not isinstance(cp06_raz, list):
        raise CP07ABuildError("cp06_raz_role_binding_list_required")
    seen_raz: set[str] = set()
    for role_row in sorted(cp06_raz, key=lambda row: str(row.get("activity_binding_id") or "")):
        if not isinstance(role_row, Mapping):
            raise CP07ABuildError("cp06_raz_role_row_invalid")
        binding_id = str(role_row.get("activity_binding_id") or "")
        if not binding_id or binding_id in seen_raz or binding_id not in cp05_raz:
            raise CP07ABuildError("cp06_raz_role_identity_invalid")
        seen_raz.add(binding_id)
        binding = cp05_raz[binding_id]
        if any(binding.get(key) != role_row.get(key) for key in ("material_id", "learning_unit_id", "grammar_unit_id")):
            raise CP07ABuildError(f"cp05_cp06_raz_binding_drift:{binding_id}")
        if sorted(binding.get("target_skill_lanes", [])) != sorted(role_row.get("target_skill_lanes", [])):
            raise CP07ABuildError(f"cp05_cp06_raz_skill_drift:{binding_id}")
        source = sources.get(str(binding["material_id"]))
        if source is None or len(str(source.get("source_content_sha256") or "")) != 64:
            raise CP07ABuildError(f"cp05_material_source_invalid:{binding.get('material_id')}")
        roles = list(role_row.get("content_roles", []))
        if "FOCUS" not in roles or any(role not in CONTENT_ROLES for role in roles):
            raise CP07ABuildError(f"cp06_content_roles_invalid:{binding_id}")
        for skill in sorted({str(value) for value in binding["target_skill_lanes"]}):
            if skill not in SKILLS:
                raise CP07ABuildError(f"cp05_skill_invalid:{binding_id}:{skill}")
            contract = _skill_contract(source, skill)
            append({
                "runtime_activity_id": _stable_id("RAZ", binding_id, skill),
                "source_kind": "RAZ_ACTIVITY_BINDING",
                "skill": skill,
                "level": _normalize_level(source.get("candidate_cefr_scope")),
                "curriculum_binding": {
                    "ket_lesson_id": None, "ket_lesson_node_id": None, "requirement_node_ids": [],
                    "learning_unit_id": str(binding["learning_unit_id"]),
                    "grammar_unit_id": str(binding["grammar_unit_id"]),
                    "canonical_egp_row_ids": sorted({str(value) for value in binding.get("canonical_egp_row_ids", []) if str(value)}),
                },
                "instructional_roles": roles,
                "source_lineage": {
                    "cp05_activity_binding_id": binding_id,
                    "cp05_material_id": str(binding["material_id"]),
                    "cp05_source_unit_ref": str(source["source_unit_ref"]),
                    "cp05_source_content_sha256": str(source["source_content_sha256"]),
                    "cp06_role_evidence_sha256": _digest(role_row.get("role_evidence", [])),
                    "private_payload_locator": {"approved_artifact_sha256": str(cp05_approved["artifact_sha256"]), "material_id": str(binding["material_id"])},
                },
                "response_contract_ref": {
                    "authority": "CP05_APPROVED_SKILL_CONTRACT",
                    "skill_contract_sha256": _digest(contract),
                    "prompt_sha256": _digest(contract["prompt"]),
                    "scoring_contract_sha256": _digest(contract["scoring_contract"]),
                    "contract_resolution_status": "RESOLVE_AT_M5_DELIVERY",
                },
                "runtime_readiness": _raz_readiness(skill, str(contract["runtime_dependency_status"])),
                "learner_facing": False,
                "a2_payload_included": False,
            })
    if set(cp05_raz) != seen_raz:
        raise CP07ABuildError("cp05_cp06_raz_binding_set_mismatch")

    cp06_m11b = cp06_artifact.get("m11b_activity_role_bindings")
    if not isinstance(cp06_m11b, list):
        raise CP07ABuildError("cp06_m11b_role_binding_list_required")
    seen_m11b: set[str] = set()
    for role_row in sorted(cp06_m11b, key=lambda row: str(row.get("activity_id") or "")):
        if not isinstance(role_row, Mapping):
            raise CP07ABuildError("cp06_m11b_role_row_invalid")
        activity_id = str(role_row.get("activity_id") or "")
        if not activity_id or activity_id in seen_m11b or activity_id not in cp05_m11b:
            raise CP07ABuildError("cp06_m11b_role_identity_invalid")
        seen_m11b.add(activity_id)
        source = cp05_m11b[activity_id]
        skill = str(source.get("target_skill") or "")
        learning_id = str(source.get("learning_unit_id") or "")
        if skill not in SKILLS or learning_id not in unit_stage:
            raise CP07ABuildError(f"cp05_m11b_skill_or_unit_invalid:{activity_id}")
        if source.get("learning_unit_id") != role_row.get("learning_unit_id") or source.get("grammar_unit_id") != role_row.get("grammar_unit_id"):
            raise CP07ABuildError(f"cp05_cp06_m11b_binding_drift:{activity_id}")
        roles = list(role_row.get("content_roles", []))
        if "FOCUS" not in roles or any(role not in CONTENT_ROLES for role in roles):
            raise CP07ABuildError(f"cp06_m11b_roles_invalid:{activity_id}")
        append({
            "runtime_activity_id": _stable_id("M11B", activity_id),
            "source_kind": "M11B_REVIEWED_ACTIVITY",
            "skill": skill,
            "level": _normalize_level(unit_stage[learning_id]),
            "curriculum_binding": {
                "ket_lesson_id": None, "ket_lesson_node_id": None, "requirement_node_ids": [],
                "learning_unit_id": learning_id, "grammar_unit_id": str(source["grammar_unit_id"]), "canonical_egp_row_ids": [],
            },
            "instructional_roles": roles,
            "source_lineage": {
                "cp05_m11b_activity_id": activity_id,
                "m11b_source_item_ref": str(source.get("source_item_ref") or ""),
                "private_payload_locator": {"source_item_ref": str(source.get("source_item_ref") or ""), "resolution_authority": "EXISTING_M11B_REVIEWED_CONTENT_STORE"},
            },
            "response_contract_ref": {"authority": "EXISTING_M11B_REVIEWED_CONTENT_STORE", "contract_resolution_status": "PENDING_CP07C_OR_CP07D_RESOLUTION"},
            "runtime_readiness": "PENDING_REVIEWED_PAYLOAD_RESOLUTION",
            "learner_facing": False,
            "a2_payload_included": False,
        })
    if set(cp05_m11b) != seen_m11b:
        raise CP07ABuildError("cp05_cp06_m11b_activity_set_mismatch")

    records.sort(key=lambda row: (row["level"], row["skill"], row["source_kind"], row["runtime_activity_id"]))
    expected_raz_projections = sum(len(row.get("target_skill_lanes", [])) for row in cp05_raz.values())
    summary = {
        "runtime_activity_count": len(records),
        "source_kind_counts": {kind: source_counts[kind] for kind in SOURCE_KINDS},
        "skill_counts": {skill: skill_counts[skill] for skill in SKILLS},
        "runtime_readiness_counts": dict(sorted(readiness_counts.items())),
        "ket_learning_asset_count": source_counts["KET_ASSET_BODY"],
        "raz_binding_count": len(cp05_raz),
        "raz_skill_projection_count": source_counts["RAZ_ACTIVITY_BINDING"],
        "m11b_activity_count": source_counts["M11B_REVIEWED_ACTIVITY"],
        "existing_learning_unit_count": 24,
        "new_learning_unit_count": 0,
        "a2_activity_count": 0,
    }
    if summary["raz_skill_projection_count"] != expected_raz_projections:
        raise CP07ABuildError("raz_skill_projection_count_not_reconciled")
    if summary["m11b_activity_count"] != cp05_payload.get("coverage_summary", {}).get("m11b_reused_activity_count"):
        raise CP07ABuildError("m11b_runtime_count_not_reconciled")
    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "metadata_only_unified_runtime_activity_index",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m2_consumer_sha256": _digest(m2_index),
            "cp05_approved_artifact_sha256": str(cp05_approved["artifact_sha256"]),
            "cp06_artifact_sha256": _digest(cp06_artifact),
        },
        "runtime_activity_contract": {
            "source_kinds": list(SOURCE_KINDS), "skills": list(SKILLS), "levels": list(LEVELS),
            "content_roles": list(CONTENT_ROLES),
            "selection_consumer": "A1FS_V1_CP07C_M4_SELECTION_ADAPTER",
            "delivery_consumer": "A1FS_V1_CP07D_M5_M6_DELIVERY_RESPONSE_ADAPTER",
            "learner_facing_content_included": False, "a2_payload_allowed": False,
            "max_query_limit": MAX_QUERY_LIMIT,
        },
        "runtime_activities": records,
        "coverage_summary": summary,
        "consumer_smoke": {
            "query_function": "query_runtime_activity_index",
            "ket_queryable": source_counts["KET_ASSET_BODY"] > 0,
            "raz_text_queryable": any(row["source_kind"] == "RAZ_ACTIVITY_BINDING" and row["runtime_readiness"] == "QUERYABLE_TEXT_RUNTIME_CONTRACT" for row in records),
            "a2_fail_closed": True,
            "m4_direct_selection_integration_completed": False,
        },
        "claim_boundaries": {
            "source_text_included": False, "ket_payload_included": False, "prompt_included": False,
            "scoring_contract_included": False, "learner_facing_projection_created": False,
            "m4_planner_modified": False, "m5_renderer_modified": False,
            "learner_response_recorded": False, "mastery_or_retention_claimed": False,
            "canonical_authority_changed": False, "a2_a2plus_in_scope": False,
        },
        "errors": [], "stop_reason": "NONE", "next_short_step": NEXT_SHORT_STEP,
    }
    _assert_safe(artifact)
    return artifact


def query_runtime_activity_index(index: Mapping[str, Any], *, skill: str | None = None, level: str | None = None, source_kind: str | None = None, instructional_role: str | None = None, runtime_readiness: str | None = None, lesson_id: str | None = None, requirement_node_id: str | None = None, learning_unit_id: str | None = None, grammar_unit_id: str | None = None, offset: int = 0, limit: int = 50) -> dict[str, Any]:
    if index.get("task_id") != TASK_ID or index.get("schema_version") != SCHEMA_VERSION:
        raise CP07ABuildError("runtime_index_contract_invalid")
    if index.get("stop_reason") != "NONE" or index.get("errors") != []:
        raise CP07ABuildError("runtime_index_not_passed")
    if skill is not None and skill not in SKILLS:
        raise CP07ABuildError("query_skill_invalid")
    if level in {"A2", "A2_PLUS", "A2+"}:
        raise CP07ABuildError("A2_PAYLOAD_LOCKED")
    normalized_level = _normalize_level(level) if level is not None else None
    if source_kind is not None and source_kind not in SOURCE_KINDS:
        raise CP07ABuildError("query_source_kind_invalid")
    if instructional_role is not None and instructional_role not in CONTENT_ROLES:
        raise CP07ABuildError("query_instructional_role_invalid")
    if offset < 0 or limit < 1 or limit > MAX_QUERY_LIMIT:
        raise CP07ABuildError("query_page_invalid")
    rows = []
    for row in index.get("runtime_activities", []):
        binding = row["curriculum_binding"]
        if skill is not None and row["skill"] != skill: continue
        if normalized_level is not None and row["level"] != normalized_level: continue
        if source_kind is not None and row["source_kind"] != source_kind: continue
        if instructional_role is not None and instructional_role not in row["instructional_roles"]: continue
        if runtime_readiness is not None and row["runtime_readiness"] != runtime_readiness: continue
        if lesson_id is not None and binding["ket_lesson_id"] != lesson_id: continue
        if requirement_node_id is not None and requirement_node_id not in binding["requirement_node_ids"]: continue
        if learning_unit_id is not None and binding["learning_unit_id"] != learning_unit_id: continue
        if grammar_unit_id is not None and binding["grammar_unit_id"] != grammar_unit_id: continue
        rows.append(row)
    page = rows[offset:offset + limit]
    return {
        "query_status": "PASS_CP07A_UNIFIED_RUNTIME_ACTIVITY_QUERY",
        "total_match_count": len(rows), "offset": offset, "limit": limit,
        "returned_count": len(page), "runtime_activities": page,
        "learner_facing_content_included": False, "a2_payload_included": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    build.add_argument("--cp05-approved", type=Path, default=DEFAULT_CP05_APPROVED)
    build.add_argument("--cp06", type=Path, default=DEFAULT_CP06)
    build.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    build.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    query = commands.add_parser("query")
    query.add_argument("--index", type=Path, required=True)
    for name in ("skill", "level", "source-kind", "instructional-role", "runtime-readiness", "lesson-id", "requirement-node-id", "learning-unit-id", "grammar-unit-id"):
        query.add_argument(f"--{name}")
    query.add_argument("--offset", type=int, default=0)
    query.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            m2_index, cp05_approved, cp06_artifact = _read(args.m2_consumer), _read(args.cp05_approved), _read(args.cp06)
            artifact = build_artifact(m2_index, cp05_approved, cp06_artifact)
            from ulga.validators import validate_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as validator
            report = validator.validate_artifact(artifact, m2_index=m2_index, cp05_approved=cp05_approved, cp06_artifact=cp06_artifact)
            _write_atomic(args.output, artifact)
            _write_atomic(args.report, report)
            shown, exit_code = report, 0 if report["validation_status"] == PASS_STATUS else 1
        else:
            shown = query_runtime_activity_index(
                _read(args.index), skill=args.skill, level=args.level, source_kind=args.source_kind,
                instructional_role=args.instructional_role, runtime_readiness=args.runtime_readiness,
                lesson_id=args.lesson_id, requirement_node_id=args.requirement_node_id,
                learning_unit_id=args.learning_unit_id, grammar_unit_id=args.grammar_unit_id,
                offset=args.offset, limit=args.limit,
            )
            exit_code = 0
        print(json.dumps(shown, ensure_ascii=False, sort_keys=True))
        return exit_code
    except (CP07ABuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
