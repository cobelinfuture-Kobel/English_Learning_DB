#!/usr/bin/env python3
"""Populate evidence-bound grammar spiral roles and recheck A1/A1+ content capacity.

CP06 consumes the approved private CP05 bank, CP04 scene candidates, the S05
promoted material registry, and the existing 24-unit learning-unit contract.
It emits metadata only. No source text, prompt, scoring contract, learner
response, runtime event, mastery, retention result, or A2/A2+ content is created.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as m02  # noqa: E402
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04  # noqa: E402
from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05  # noqa: E402
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy  # noqa: E402
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep  # noqa: E402
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Metadata-only role and capacity derivation from an already approved private "
    "content bank, committed unit relations, CP04 scene refs, and verified S05 "
    "Authority links; no learner content or runtime publication is produced."
)

TASK_ID = "A1FS-V1-CP06_GrammarSpiralRolePopulationAndContentCapacityRecheck"
PROGRAM_ID = cp05.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.cp06.grammar_spiral_role_capacity.v1"
PASS_STATUS = "PASS_CP06_GRAMMAR_SPIRAL_ROLES_AND_CONTENT_CAPACITY_RECONCILED"
NEXT_SHORT_STEP = "A1FS-V1-CP07_M4ToM8RuntimeConsumerIntegrationAndRealAttemptProof"

DEFAULT_CP05_APPROVED = cp05.DEFAULT_APPROVED_OUTPUT
DEFAULT_CP04 = cp04.OUTPUT_PATH
DEFAULT_REGISTRY = registry.DEFAULT_OUTPUT
DEFAULT_UNIT_CONTRACT = m02.OUTPUT_PATH
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp06/grammar_spiral_role_population.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp06/grammar_spiral_role_population.validation.json"

CONTENT_ROLES = ("FOCUS", "RECYCLE", "CONTRAST", "TRANSFER")
LIFECYCLE_ROLES = ("REMEDIATION", "REASSESSMENT", "RETENTION")
ALL_ROLES = CONTENT_ROLES + LIFECYCLE_ROLES
ALLOWED_STAGES = {"A1", "A1_PLUS"}
SKILLS = ("READING", "LISTENING", "SPEAKING", "WRITING")


class CP06BuildError(ValueError):
    """Fail-closed CP05 lineage, role evidence, or capacity accounting error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CP06BuildError(f"json_object_required:{path}")
    return value


def _write_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
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
    return content_policy.digest(value)


def _verify_package_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise CP06BuildError("registry_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise CP06BuildError("registry_package_sha256_mismatch")


def _verify_cp05_approved(approved: Mapping[str, Any]) -> Mapping[str, Any]:
    if approved.get("artifact_role") != "APPROVED_CANONICAL_JSON":
        raise CP06BuildError("cp05_approved_artifact_role_invalid")
    if approved.get("admission", {}).get("status") != "APPROVED":
        raise CP06BuildError("cp05_approved_admission_status_invalid")
    if approved.get("learner_facing") is not False:
        raise CP06BuildError("cp05_approved_must_not_be_learner_facing")
    try:
        content_policy.verify_artifact_digest(approved)
    except content_policy.ContentPolicyBuildError as exc:
        raise CP06BuildError(f"cp05_approved_digest_invalid:{exc}") from exc
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise CP06BuildError("cp05_payload_required")
    if payload.get("task_id") != cp05.TASK_ID:
        raise CP06BuildError("cp05_task_id_mismatch")
    if payload.get("schema_version") != cp05.SCHEMA_VERSION:
        raise CP06BuildError("cp05_schema_version_mismatch")
    if payload.get("scope") != "A1_A1_PLUS_ONLY":
        raise CP06BuildError("cp05_scope_invalid")
    if payload.get("stop_reason") != "NONE":
        raise CP06BuildError("cp05_not_passed")
    if payload.get("next_short_step") != TASK_ID:
        raise CP06BuildError("cp05_next_short_step_mismatch")
    summary = payload.get("coverage_summary", {})
    if (
        summary.get("existing_learning_unit_count") != 24
        or summary.get("new_learning_unit_count") != 0
    ):
        raise CP06BuildError("cp05_unit_coverage_invalid")
    return payload


def _verify_cp04(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if artifact.get("task_id") != cp04.TASK_ID:
        raise CP06BuildError("cp04_task_id_mismatch")
    if artifact.get("schema_version") != cp04.SCHEMA_VERSION:
        raise CP06BuildError("cp04_schema_version_mismatch")
    if artifact.get("stop_reason") != "NONE":
        raise CP06BuildError("cp04_not_passed")
    units = artifact.get("learning_units")
    if not isinstance(units, list) or len(units) != 24:
        raise CP06BuildError("cp04_learning_unit_count_not_24")
    result = {
        str(row.get("learning_unit_id") or ""): row
        for row in units
        if isinstance(row, Mapping)
    }
    if len(result) != 24 or "" in result:
        raise CP06BuildError("cp04_learning_unit_identity_invalid")
    return result


def _resolve_unit_ref(
    raw: Any,
    *,
    by_learning: Mapping[str, Mapping[str, Any]],
    by_grammar: Mapping[str, str],
) -> str:
    value = str(raw or "")
    if not value:
        raise CP06BuildError("unit_relation_ref_empty")
    if value in by_learning:
        return value
    if value in by_grammar:
        return by_grammar[value]
    raise CP06BuildError(f"unit_relation_ref_unknown:{value}")


def _unit_contract_index(
    artifact: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if artifact.get("task_id") != m02.TASK_ID:
        raise CP06BuildError("unit_contract_task_id_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        raise CP06BuildError("unit_contract_scope_invalid")
    rows = artifact.get("learning_units")
    if not isinstance(rows, list) or len(rows) != 24:
        raise CP06BuildError("unit_contract_count_not_24")
    by_learning: dict[str, Mapping[str, Any]] = {}
    by_grammar: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CP06BuildError("unit_contract_row_invalid")
        learning_id = str(row.get("learning_unit_id") or "")
        grammar_id = str(row.get("grammar_unit_id") or "")
        stage = str(row.get("internal_stage") or "")
        if (
            not learning_id
            or not grammar_id
            or learning_id in by_learning
            or grammar_id in by_grammar
            or stage not in ALLOWED_STAGES
        ):
            raise CP06BuildError("unit_contract_identity_or_stage_invalid")
        by_learning[learning_id] = row
        by_grammar[grammar_id] = learning_id
    if sorted(int(row.get("sequence_index") or 0) for row in rows) != list(range(1, 25)):
        raise CP06BuildError("unit_contract_sequence_invalid")

    result: dict[str, dict[str, Any]] = {}
    for learning_id, row in by_learning.items():
        contrast_refs = row.get("learning_content", {}).get("contrast_unit_ids", [])
        prerequisite_refs = row.get("prerequisite_unit_ids", [])
        error_tags = row.get("error_remediation_binding", {}).get("error_tags", [])
        if not isinstance(contrast_refs, list) or not isinstance(prerequisite_refs, list):
            raise CP06BuildError(f"unit_relation_lists_invalid:{learning_id}")
        if not isinstance(error_tags, list):
            raise CP06BuildError(f"unit_error_tags_invalid:{learning_id}")
        result[learning_id] = {
            "learning_unit_id": learning_id,
            "grammar_unit_id": str(row["grammar_unit_id"]),
            "sequence_index": int(row["sequence_index"]),
            "internal_stage": str(row["internal_stage"]),
            "canonical_egp_row_ids": list(row.get("canonical_egp_row_ids", [])),
            "prerequisite_unit_ids": sorted(
                {
                    _resolve_unit_ref(
                        ref, by_learning=by_learning, by_grammar=by_grammar
                    )
                    for ref in prerequisite_refs
                }
            ),
            "contrast_unit_ids": sorted(
                {
                    _resolve_unit_ref(
                        ref, by_learning=by_learning, by_grammar=by_grammar
                    )
                    for ref in contrast_refs
                }
            ),
            "error_tags": sorted({str(tag) for tag in error_tags if str(tag)}),
        }
    return result


def _registry_index(
    package: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, list[str]]]:
    if package.get("task_id") != registry.TASK_ID:
        raise CP06BuildError("registry_task_id_mismatch")
    if package.get("validation_status") != registry.PASS_STATUS or package.get("errors") != []:
        raise CP06BuildError("registry_not_passed")
    _verify_package_hash(package)
    rows = package.get("promoted_material_registry")
    if not isinstance(rows, list) or not rows:
        raise CP06BuildError("promoted_registry_empty_or_invalid")
    materials: dict[str, Mapping[str, Any]] = {}
    themes: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CP06BuildError("promoted_registry_row_invalid")
        material_id = str(row.get("material_id") or "")
        if not material_id or material_id in materials:
            raise CP06BuildError("promoted_material_id_missing_or_duplicate")
        if row.get("registry_status") != "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY":
            raise CP06BuildError(f"material_not_promoted:{material_id}")
        if row.get("candidate_cefr_scope") not in {"A1", "A1_PLUS"}:
            raise CP06BuildError(f"material_scope_invalid:{material_id}")
        links = row.get("authority_links")
        if not isinstance(links, list):
            raise CP06BuildError(f"material_authority_links_invalid:{material_id}")
        themes[material_id] = sorted(
            {
                str(link.get("authority_ref") or "")
                for link in links
                if isinstance(link, Mapping)
                and link.get("authority_type") == "THEME"
                and link.get("link_status") == "VERIFIED_EXISTING_AUTHORITY_MATCH"
                and str(link.get("authority_ref") or "")
            }
        )
        materials[material_id] = row
    expected = package.get("aggregate_summary", {}).get("final_promoted_material_count")
    if expected != len(materials):
        raise CP06BuildError("registry_promoted_count_mismatch")
    return materials, themes


def _lifecycle_contract(error_tags: Sequence[str]) -> dict[str, Any]:
    tags = sorted({str(tag) for tag in error_tags if str(tag)})
    return {
        "REMEDIATION": {
            "eligibility_status": (
                "ELIGIBLE_NOT_ACTIVATED" if tags else "PENDING_ERROR_TAG_EVIDENCE"
            ),
            "activation_requirement": "RUNTIME_DIAGNOSED_ERROR_EVIDENCE",
            "error_tags": tags,
            "runtime_activation_performed": False,
        },
        "REASSESSMENT": {
            "eligibility_status": "ELIGIBLE_AFTER_REMEDIATION_EVIDENCE",
            "activation_requirement": "COMPLETED_REMEDIATION_RESULT",
            "runtime_activation_performed": False,
        },
        "RETENTION": {
            "eligibility_status": "ELIGIBLE_AFTER_SUCCESSFUL_ATTEMPT",
            "checkpoint_days": [1, 3, 7],
            "runtime_schedule_created": False,
        },
    }


def _content_roles(
    binding: Mapping[str, Any],
    *,
    ordered_material_bindings: Sequence[Mapping[str, Any]],
    unit_contracts: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    learning_id = str(binding["learning_unit_id"])
    current = unit_contracts[learning_id]
    first = ordered_material_bindings[0]
    first_learning_id = str(first["learning_unit_id"])
    first_unit = unit_contracts[first_learning_id]
    material_unit_ids = {
        str(row["learning_unit_id"]) for row in ordered_material_bindings
    }
    roles = ["FOCUS"]
    evidence = [
        {
            "role": "FOCUS",
            "basis": "DIRECT_CP05_ACTIVITY_BINDING_TO_TARGET_GRAMMAR_UNIT",
            "evidence_refs": [
                str(binding["activity_binding_id"]),
                str(current["grammar_unit_id"]),
            ],
        }
    ]
    if int(current["sequence_index"]) > int(first_unit["sequence_index"]):
        roles.append("RECYCLE")
        evidence.append(
            {
                "role": "RECYCLE",
                "basis": "SAME_PROMOTED_MATERIAL_REAPPEARS_IN_LATER_UNIT",
                "evidence_refs": [
                    str(binding["material_id"]),
                    first_learning_id,
                    learning_id,
                ],
            }
        )
    contrast_peers = set(current["contrast_unit_ids"]) & (
        material_unit_ids - {learning_id}
    )
    reverse_contrast_peers = {
        peer_id
        for peer_id in material_unit_ids - {learning_id}
        if learning_id in set(unit_contracts[peer_id]["contrast_unit_ids"])
    }
    contrast_peers |= reverse_contrast_peers
    if contrast_peers:
        roles.append("CONTRAST")
        evidence.append(
            {
                "role": "CONTRAST",
                "basis": "SAME_MATERIAL_BOUND_TO_EXISTING_CONTRAST_UNIT_RELATION",
                "evidence_refs": sorted(contrast_peers),
            }
        )
    if (
        first_unit["internal_stage"] == "A1"
        and current["internal_stage"] == "A1_PLUS"
    ):
        roles.append("TRANSFER")
        transfer_refs = sorted(
            set(current["prerequisite_unit_ids"]) & material_unit_ids
        )
        evidence.append(
            {
                "role": "TRANSFER",
                "basis": "SAME_MATERIAL_TRANSFERS_FROM_A1_TO_A1_PLUS",
                "evidence_refs": transfer_refs or [first_learning_id, learning_id],
            }
        )
    return roles, evidence


def build_artifact(
    cp05_approved: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    unit_contract_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _verify_cp05_approved(cp05_approved)
    cp04_units = _verify_cp04(cp04_artifact)
    unit_contracts = _unit_contract_index(unit_contract_artifact)
    materials, material_theme_refs = _registry_index(registry_package)

    cp05_units = payload.get("learning_units")
    if not isinstance(cp05_units, list) or len(cp05_units) != 24:
        raise CP06BuildError("cp05_learning_units_invalid")
    cp05_unit_ids = {str(row.get("learning_unit_id") or "") for row in cp05_units}
    if cp05_unit_ids != set(unit_contracts) or cp05_unit_ids != set(cp04_units):
        raise CP06BuildError("cp04_cp05_unit_contract_identity_mismatch")

    raz_bindings = payload.get("raz_unit_activity_bindings")
    m11b_activities = payload.get("m11b_reuse_activities")
    if not isinstance(raz_bindings, list) or not isinstance(m11b_activities, list):
        raise CP06BuildError("cp05_activity_lists_invalid")

    raz_by_material: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    seen_binding_ids: set[str] = set()
    for row in raz_bindings:
        if not isinstance(row, Mapping):
            raise CP06BuildError("cp05_raz_binding_row_invalid")
        binding_id = str(row.get("activity_binding_id") or "")
        learning_id = str(row.get("learning_unit_id") or "")
        material_id = str(row.get("material_id") or "")
        if (
            not binding_id
            or binding_id in seen_binding_ids
            or learning_id not in unit_contracts
            or material_id not in materials
        ):
            raise CP06BuildError("cp05_raz_binding_identity_invalid")
        skills = row.get("target_skill_lanes")
        if (
            not isinstance(skills, list)
            or not skills
            or any(str(skill) not in SKILLS for skill in skills)
        ):
            raise CP06BuildError(f"cp05_raz_binding_skills_invalid:{binding_id}")
        seen_binding_ids.add(binding_id)
        raz_by_material[material_id].append(row)

    role_counts: Counter[str] = Counter()
    raz_role_bindings: list[dict[str, Any]] = []
    unit_raz_rows: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for material_id, rows in sorted(raz_by_material.items()):
        ordered = sorted(
            rows,
            key=lambda row: (
                unit_contracts[str(row["learning_unit_id"])]["sequence_index"],
                str(row["activity_binding_id"]),
            ),
        )
        for row in ordered:
            learning_id = str(row["learning_unit_id"])
            roles, evidence = _content_roles(
                row,
                ordered_material_bindings=ordered,
                unit_contracts=unit_contracts,
            )
            role_counts.update(roles)
            result = {
                "activity_binding_id": str(row["activity_binding_id"]),
                "learning_unit_id": learning_id,
                "grammar_unit_id": str(row["grammar_unit_id"]),
                "material_id": material_id,
                "target_skill_lanes": sorted({str(value) for value in row["target_skill_lanes"]}),
                "content_roles": roles,
                "role_evidence": evidence,
                "lifecycle_role_contracts": _lifecycle_contract(
                    unit_contracts[learning_id]["error_tags"]
                ),
                "runtime_status": "CP07_RUNTIME_PROJECTION_REQUIRED",
            }
            raz_role_bindings.append(result)
            unit_raz_rows[learning_id].append(result)

    m11b_role_bindings: list[dict[str, Any]] = []
    unit_m11b_rows: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_m11b_ids: set[str] = set()
    for row in sorted(m11b_activities, key=lambda item: str(item.get("activity_id") or "")):
        if not isinstance(row, Mapping):
            raise CP06BuildError("cp05_m11b_row_invalid")
        activity_id = str(row.get("activity_id") or "")
        learning_id = str(row.get("learning_unit_id") or "")
        skill = str(row.get("target_skill") or "")
        if (
            not activity_id
            or activity_id in seen_m11b_ids
            or learning_id not in unit_contracts
            or skill not in SKILLS
        ):
            raise CP06BuildError("cp05_m11b_identity_or_skill_invalid")
        seen_m11b_ids.add(activity_id)
        role_counts["FOCUS"] += 1
        result = {
            "activity_id": activity_id,
            "learning_unit_id": learning_id,
            "grammar_unit_id": str(row["grammar_unit_id"]),
            "target_skill": skill,
            "content_roles": ["FOCUS"],
            "role_evidence": [
                {
                    "role": "FOCUS",
                    "basis": "EXISTING_REVIEWED_M11B_ACTIVITY_BOUND_TO_TARGET_UNIT",
                    "evidence_refs": [activity_id, str(row["grammar_unit_id"])],
                }
            ],
            "lifecycle_role_contracts": _lifecycle_contract(
                unit_contracts[learning_id]["error_tags"]
            ),
            "runtime_status": "CP07_RUNTIME_PROJECTION_REQUIRED",
        }
        m11b_role_bindings.append(result)
        unit_m11b_rows[learning_id].append(result)

    cp05_summary = payload.get("coverage_summary", {})
    if len(raz_role_bindings) != cp05_summary.get("raz_admitted_activity_binding_count"):
        raise CP06BuildError("raz_role_binding_count_not_reconciled")
    if len(m11b_role_bindings) != cp05_summary.get("m11b_reused_activity_count"):
        raise CP06BuildError("m11b_role_binding_count_not_reconciled")

    unit_capacity_rows: list[dict[str, Any]] = []
    scene_capacity_count = text_capacity_count = 0
    cp04_scene_capacity_count = 0
    lifecycle_eligible_counts: Counter[str] = Counter()
    for learning_id, contract in sorted(
        unit_contracts.items(), key=lambda item: item[1]["sequence_index"]
    ):
        raz_rows = unit_raz_rows.get(learning_id, [])
        m11b_rows = unit_m11b_rows.get(learning_id, [])
        skill_counts: Counter[str] = Counter()
        for row in raz_rows:
            skill_counts.update(row["target_skill_lanes"])
        for row in m11b_rows:
            skill_counts[row["target_skill"]] += 1
        cp04_scene_refs = sorted(
            {
                str(row.get("theme_situation_ref") or "")
                for row in cp04_units[learning_id].get("scene_candidates", [])
                if isinstance(row, Mapping) and str(row.get("theme_situation_ref") or "")
            }
        )
        raz_theme_refs = sorted(
            {
                theme_ref
                for row in raz_rows
                for theme_ref in material_theme_refs.get(row["material_id"], [])
            }
        )
        effective_scene_refs = sorted(set(cp04_scene_refs) | set(raz_theme_refs))
        cp04_scene_capacity_count += bool(cp04_scene_refs)
        scene_capacity_count += bool(effective_scene_refs)
        text_ready = bool(skill_counts["READING"] or skill_counts["WRITING"])
        text_capacity_count += text_ready
        role_count = Counter(
            role
            for row in raz_rows + m11b_rows
            for role in row["content_roles"]
        )
        for lifecycle_role in LIFECYCLE_ROLES:
            lifecycle_eligible_counts[lifecycle_role] += sum(
                row["lifecycle_role_contracts"][lifecycle_role]["eligibility_status"]
                != "PENDING_ERROR_TAG_EVIDENCE"
                for row in raz_rows + m11b_rows
            )
        unit_capacity_rows.append(
            {
                "learning_unit_id": learning_id,
                "grammar_unit_id": contract["grammar_unit_id"],
                "sequence_index": contract["sequence_index"],
                "internal_stage": contract["internal_stage"],
                "canonical_egp_row_ids": list(contract["canonical_egp_row_ids"]),
                "prerequisite_unit_ids": list(contract["prerequisite_unit_ids"]),
                "contrast_unit_ids": list(contract["contrast_unit_ids"]),
                "error_tags": list(contract["error_tags"]),
                "activity_capacity": {
                    "raz_activity_binding_count": len(raz_rows),
                    "m11b_activity_count": len(m11b_rows),
                    "skill_binding_counts": {
                        skill: skill_counts[skill] for skill in SKILLS
                    },
                    "content_role_counts": {
                        role: role_count[role] for role in CONTENT_ROLES
                    },
                    "text_runtime_candidate_available": text_ready,
                    "listening_audio_generation_pending_binding_count": sum(
                        "LISTENING" in row["target_skill_lanes"] for row in raz_rows
                    ),
                    "speaking_recording_pending_binding_count": sum(
                        "SPEAKING" in row["target_skill_lanes"] for row in raz_rows
                    ),
                },
                "scene_capacity": {
                    "cp04_theme_situation_refs": cp04_scene_refs,
                    "raz_verified_theme_refs": raz_theme_refs,
                    "effective_theme_situation_refs": effective_scene_refs,
                    "capacity_status": (
                        "CP04_AND_RAZ_VERIFIED_THEME"
                        if cp04_scene_refs and raz_theme_refs
                        else "CP04_THEME_ONLY"
                        if cp04_scene_refs
                        else "RAZ_VERIFIED_THEME_ONLY"
                        if raz_theme_refs
                        else "PENDING_SOURCE_EVIDENCE"
                    ),
                },
                "content_capacity_status": (
                    "TEXT_AND_SCENE_CAPACITY_AVAILABLE"
                    if text_ready and effective_scene_refs
                    else "TEXT_CAPACITY_AVAILABLE_SCENE_PENDING"
                    if text_ready
                    else "SCENE_CAPACITY_AVAILABLE_TEXT_PENDING"
                    if effective_scene_refs
                    else "CONTENT_CAPACITY_PENDING"
                ),
            }
        )

    summary = {
        "existing_learning_unit_count": len(unit_capacity_rows),
        "new_learning_unit_count": 0,
        "raz_distinct_material_count": len(raz_by_material),
        "raz_activity_binding_count": len(raz_role_bindings),
        "m11b_activity_count": len(m11b_role_bindings),
        "content_role_assignment_counts": {
            role: role_counts[role] for role in CONTENT_ROLES
        },
        "lifecycle_role_eligible_activity_counts": {
            role: lifecycle_eligible_counts[role] for role in LIFECYCLE_ROLES
        },
        "text_runtime_candidate_unit_count": text_capacity_count,
        "cp04_scene_capacity_unit_count": cp04_scene_capacity_count,
        "effective_scene_capacity_unit_count": scene_capacity_count,
        "effective_scene_gap_unit_count": 24 - scene_capacity_count,
        "listening_audio_generation_pending_binding_count": cp05_summary.get(
            "listening_audio_generation_pending_binding_count"
        ),
        "speaking_recording_pending_binding_count": sum(
            "SPEAKING" in row["target_skill_lanes"] for row in raz_role_bindings
        ),
        "skill_binding_counts": dict(cp05_summary.get("skill_binding_counts", {})),
    }
    if summary["existing_learning_unit_count"] != 24:
        raise CP06BuildError("cp06_learning_unit_count_not_24")
    if summary["raz_distinct_material_count"] != cp05_summary.get(
        "raz_distinct_candidate_material_count"
    ):
        raise CP06BuildError("cp06_distinct_material_count_not_reconciled")
    if summary["raz_activity_binding_count"] != cp05_summary.get(
        "raz_admitted_activity_binding_count"
    ):
        raise CP06BuildError("cp06_raz_activity_count_not_reconciled")
    if summary["listening_audio_generation_pending_binding_count"] != sum(
        "LISTENING" in row["target_skill_lanes"] for row in raz_role_bindings
    ):
        raise CP06BuildError("cp06_listening_pending_count_not_reconciled")

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "metadata_only_grammar_spiral_role_and_content_capacity",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "cp05_approved_artifact_sha256": str(cp05_approved["artifact_sha256"]),
            "cp04_artifact_sha256": _digest(cp04_artifact),
            "raz_registry_package_sha256": str(registry_package["package_sha256"]),
            "unit_contract_sha256": _digest(unit_contract_artifact),
        },
        "role_contract": {
            "content_roles": list(CONTENT_ROLES),
            "lifecycle_roles": list(LIFECYCLE_ROLES),
            "focus_basis": "DIRECT_TARGET_GRAMMAR_BINDING",
            "recycle_basis": "SAME_MATERIAL_LATER_UNIT_REAPPEARANCE",
            "contrast_basis": "EXISTING_CONTRAST_RELATION_AND_SHARED_MATERIAL",
            "transfer_basis": "SAME_MATERIAL_A1_TO_A1_PLUS_REUSE",
            "remediation_activation": "RUNTIME_DIAGNOSED_ERROR_EVIDENCE_REQUIRED",
            "reassessment_activation": "COMPLETED_REMEDIATION_RESULT_REQUIRED",
            "retention_activation": "SUCCESSFUL_ATTEMPT_REQUIRED_WITH_1_3_7_DAY_CHECKPOINTS",
        },
        "raz_activity_role_bindings": raz_role_bindings,
        "m11b_activity_role_bindings": m11b_role_bindings,
        "unit_content_capacity": unit_capacity_rows,
        "coverage_summary": summary,
        "capacity_gate": {
            "decision": "GRAMMAR_SPIRAL_ROLES_AND_CONTENT_CAPACITY_READY",
            "all_existing_units_have_admitted_activity_capacity": all(
                row["activity_capacity"]["raz_activity_binding_count"]
                + row["activity_capacity"]["m11b_activity_count"]
                > 0
                for row in unit_capacity_rows
            ),
            "scene_gap_requires_source_evidence_not_invention": True,
            "runtime_publication_allowed": False,
            "cp07_runtime_integration_required": True,
            "a2_a2plus_status": "LOCKED",
        },
        "claim_boundaries": {
            "private_source_text_included": False,
            "prompt_or_scoring_contract_included": False,
            "learner_response_included": False,
            "runtime_role_activation_performed": False,
            "learner_mastery_claimed": False,
            "retention_result_claimed": False,
            "scene_gap_filled_without_verified_authority": False,
            "canonical_unit_identity_changed": False,
            "canonical_egp_mapping_changed": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    return artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp05-approved", type=Path, default=DEFAULT_CP05_APPROVED)
    parser.add_argument("--cp04", type=Path, default=DEFAULT_CP04)
    parser.add_argument("--raz-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--unit-contract", type=Path, default=DEFAULT_UNIT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        cp05_approved = _read(args.cp05_approved)
        cp04_artifact = _read(args.cp04)
        registry_package = _read(args.raz_registry)
        unit_contract = _read(args.unit_contract)
        artifact = build_artifact(
            cp05_approved, cp04_artifact, registry_package, unit_contract
        )
        from ulga.validators import validate_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as validator

        report = validator.validate_artifact(
            artifact,
            cp05_approved=cp05_approved,
            cp04_artifact=cp04_artifact,
            registry_package=registry_package,
            unit_contract_artifact=unit_contract,
        )
        _write_atomic(args.output, artifact)
        _write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (CP06BuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
