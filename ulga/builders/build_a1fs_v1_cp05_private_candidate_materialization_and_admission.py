#!/usr/bin/env python3
"""Materialize and admit private RAZ/M11B candidates for the existing 24 A1/A1+ units.

CP05 consumes the real CP04 candidate envelope, the promoted S05 registry, the
S02 semantic representatives, and the private RAZ derived source rows. It
creates one normalized private source record per distinct promoted RAZ material,
one activity binding per CP04 material/unit binding, and references existing
M11B reviewed exercises without copying their private payloads.

The canonical policy transition is enforced as:

    private candidate JSON -> independent validation -> approved canonical JSON

No artifact from this builder is published to runtime. CP06 must assign spiral
roles and CP07 must build four-skill runtime projections before learner use.
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

from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04  # noqa: E402
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy  # noqa: E402
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep  # noqa: E402
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup  # noqa: E402
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry  # noqa: E402
from ulga.builders import build_raz_aw_derived_schema_compatibility as compatibility  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
TASK_ID = "A1FS-V1-CP05_PrivateCandidateMaterializationAndAdmission"
PROGRAM_ID = cp04.PROGRAM_ID
PRODUCER_ID = "build_a1fs_v1_cp05_private_candidate_materialization_and_admission"
SCHEMA_VERSION = "a1fs.v1.cp05.private_candidate_materialization_admission.v1"
PASS_STATUS = "PASS_CP05_PRIVATE_CANDIDATES_MATERIALIZED_AND_ADMITTED"
NEXT_SHORT_STEP = "A1FS-V1-CP06_GrammarSpiralRolePopulationAndContentCapacityRecheck"
SOURCE_LEVELS = tuple("ABCDEFGHI")
SKILL_AFFORDANCE_MAP = {
    "READING_SOURCE": "READING",
    "LISTENING_ADAPTATION": "LISTENING",
    "SPEAKING_PROMPT": "SPEAKING",
    "WRITING_MODEL": "WRITING",
}
ALLOWED_SKILLS = tuple(SKILL_AFFORDANCE_MAP.values())

DEFAULT_CP04 = cp04.OUTPUT_PATH
DEFAULT_REGISTRY = registry.DEFAULT_OUTPUT
DEFAULT_DEDUP = dedup.DEFAULT_OUTPUT
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_CANDIDATE_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp05/private_candidate_materialization.candidate.private.json"
DEFAULT_APPROVED_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp05/private_candidate_materialization.approved.private.json"
DEFAULT_SAFE_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp05/private_candidate_materialization_admission.safe.json"
DEFAULT_REPORT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp05/private_candidate_materialization_admission.validation.json"


class CP05BuildError(ValueError):
    """Fail-closed lineage, source-resolution, policy, or accounting error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CP05BuildError(f"json_object_required:{path}")
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


def _stable_id(prefix: str, *parts: str) -> str:
    if not parts or any(not str(part) for part in parts):
        raise CP05BuildError("stable_identity_component_missing")
    digest = hashlib.sha256("\0".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:24]
    return f"A1FS_CP05_{prefix}_{digest}"


def _verify_package_hash(package: Mapping[str, Any], label: str) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise CP05BuildError(f"{label}_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise CP05BuildError(f"{label}_package_sha256_mismatch")


def _verify_cp04(artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if artifact.get("task_id") != cp04.TASK_ID:
        raise CP05BuildError("cp04_task_id_mismatch")
    if artifact.get("schema_version") != cp04.SCHEMA_VERSION:
        raise CP05BuildError("cp04_schema_version_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        raise CP05BuildError("cp04_scope_mismatch")
    if artifact.get("stop_reason") != "NONE":
        raise CP05BuildError("cp04_not_passed")
    if artifact.get("next_short_step") != TASK_ID:
        raise CP05BuildError("cp04_next_short_step_mismatch")
    units = artifact.get("learning_units")
    if not isinstance(units, list) or len(units) != 24:
        raise CP05BuildError("cp04_learning_unit_count_not_24")
    if [row.get("sequence_index") for row in units] != list(range(1, 25)):
        raise CP05BuildError("cp04_unit_sequence_invalid")
    if artifact.get("coverage_summary", {}).get("new_learning_unit_count") != 0:
        raise CP05BuildError("cp04_new_unit_detected")
    return units


def _registry_index(package: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if package.get("task_id") != registry.TASK_ID:
        raise CP05BuildError("registry_task_id_mismatch")
    if package.get("validation_status") != registry.PASS_STATUS or package.get("errors") != []:
        raise CP05BuildError("registry_not_passed")
    _verify_package_hash(package, "registry")
    rows = package.get("promoted_material_registry")
    if not isinstance(rows, list) or not rows:
        raise CP05BuildError("promoted_registry_empty_or_invalid")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CP05BuildError("promoted_registry_row_invalid")
        material_id = str(row.get("material_id") or "")
        if not material_id or material_id in result:
            raise CP05BuildError("promoted_material_id_missing_or_duplicate")
        if row.get("registry_status") != "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY":
            raise CP05BuildError(f"material_not_promoted:{material_id}")
        if row.get("candidate_cefr_scope") not in {"A1", "A1_PLUS"}:
            raise CP05BuildError(f"material_scope_invalid:{material_id}")
        result[material_id] = row
    if package.get("aggregate_summary", {}).get("final_promoted_material_count") != len(result):
        raise CP05BuildError("registry_promoted_count_mismatch")
    return result


def _representative_index(package: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if package.get("task_id") != dedup.TASK_ID:
        raise CP05BuildError("dedup_task_id_mismatch")
    if package.get("validation_status") != dedup.PASS_STATUS or package.get("errors") != []:
        raise CP05BuildError("dedup_not_passed")
    _verify_package_hash(package, "dedup")
    rows = package.get("semantic_representatives")
    if not isinstance(rows, list) or not rows:
        raise CP05BuildError("semantic_representatives_empty_or_invalid")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CP05BuildError("semantic_representative_row_invalid")
        group = str(row.get("semantic_duplicate_group_id") or "")
        if not group or group in result:
            raise CP05BuildError("semantic_group_missing_or_duplicate")
        result[group] = row
    return result


def load_private_source_rows(
    source_root: Path,
    levels: Sequence[str] = SOURCE_LEVELS,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    rows_by_ref: dict[str, dict[str, Any]] = {}
    source_index: list[dict[str, Any]] = []
    for level in levels:
        rows, semantic_paths, derived_schema = compatibility.load_derived_level(source_root, level)
        level_count = 0
        for row in rows:
            if not isinstance(row, Mapping):
                raise CP05BuildError(f"private_source_row_invalid:{level}")
            ref = str(row.get("page_unit_id") or "")
            text = row.get("text")
            if not ref or ref in rows_by_ref:
                raise CP05BuildError(f"private_source_ref_missing_or_duplicate:{level}:{ref}")
            if not isinstance(text, str) or not text.strip():
                raise CP05BuildError(f"private_source_text_missing:{ref}")
            if str(row.get("level") or level) != level:
                raise CP05BuildError(f"private_source_level_mismatch:{ref}")
            rows_by_ref[ref] = {"page_unit_id": ref, "level": level, "text": text.strip()}
            level_count += 1
        source_index.append(
            {
                "level": level,
                "record_count": level_count,
                "derived_schema": derived_schema,
                "source_file_sha256s": [deep.sha256_file(path) for path in semantic_paths],
            }
        )
    return rows_by_ref, source_index


def _skill_contract(skill: str) -> dict[str, Any]:
    contracts: dict[str, dict[str, Any]] = {
        "READING": {
            "skill": "READING",
            "activity_kind": "SOURCE_READING_RESPONSE",
            "prompt": "Read the source and write one sentence about its main idea.",
            "response_mode": "OPEN_TEXT",
            "support_level": "SOURCE_TEXT_VISIBLE",
            "initiative_level": "GUIDED",
            "scoring_contract": {
                "mode": "RUBRIC",
                "automatic_exact_answer": False,
                "criteria": ["SOURCE_RELEVANCE", "A1_A1PLUS_LANGUAGE_CONTROL"],
            },
            "evidence_level": "LEARNER_RESPONSE_REQUIRED",
            "runtime_dependency_status": "READY_FOR_TEXT_RUNTIME_INTEGRATION",
        },
        "LISTENING": {
            "skill": "LISTENING",
            "activity_kind": "SOURCE_LISTENING_RETELL",
            "prompt": "Listen to the source and say or write one detail you heard.",
            "response_mode": "OPEN_TEXT_OR_AUDIO",
            "support_level": "AUDIO_WITH_OPTIONAL_REPLAY",
            "initiative_level": "GUIDED",
            "scoring_contract": {
                "mode": "RUBRIC",
                "automatic_exact_answer": False,
                "criteria": ["SOURCE_RELEVANCE", "COMPREHENSIBLE_RESPONSE"],
            },
            "evidence_level": "LEARNER_RESPONSE_REQUIRED",
            "runtime_dependency_status": "AUDIO_GENERATION_REQUIRED",
        },
        "SPEAKING": {
            "skill": "SPEAKING",
            "activity_kind": "SOURCE_SPEAKING_RETELL",
            "prompt": "Record yourself retelling one idea from the source.",
            "response_mode": "AUDIO_RECORDING",
            "support_level": "SOURCE_TEXT_VISIBLE_BEFORE_RECORDING",
            "initiative_level": "GUIDED",
            "scoring_contract": {
                "mode": "RUBRIC",
                "automatic_exact_answer": False,
                "criteria": ["SOURCE_RELEVANCE", "COMPREHENSIBILITY", "TARGET_LANGUAGE_USE"],
            },
            "evidence_level": "RECORDED_LEARNER_RESPONSE_REQUIRED",
            "runtime_dependency_status": "RECORDING_CAPTURE_REQUIRED",
        },
        "WRITING": {
            "skill": "WRITING",
            "activity_kind": "SOURCE_WRITING_TRANSFER",
            "prompt": "Write one sentence about the source using the target grammar.",
            "response_mode": "OPEN_TEXT",
            "support_level": "SOURCE_TEXT_AND_GRAMMAR_TARGET_VISIBLE",
            "initiative_level": "GUIDED",
            "scoring_contract": {
                "mode": "RUBRIC",
                "automatic_exact_answer": False,
                "criteria": ["SOURCE_RELEVANCE", "TARGET_GRAMMAR_USE", "A1_A1PLUS_CLARITY"],
            },
            "evidence_level": "LEARNER_RESPONSE_REQUIRED",
            "runtime_dependency_status": "READY_FOR_TEXT_RUNTIME_INTEGRATION",
        },
    }
    if skill not in contracts:
        raise CP05BuildError(f"skill_contract_invalid:{skill}")
    return contracts[skill]


def build_private_payload(
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    dedup_package: Mapping[str, Any],
    private_source_rows: Mapping[str, Mapping[str, Any]],
    *,
    source_index: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    units = _verify_cp04(cp04_artifact)
    materials = _registry_index(registry_package)
    representatives = _representative_index(dedup_package)

    cp04_raz_candidates: dict[tuple[str, str], tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    m11b_reuse: list[dict[str, Any]] = []
    unit_identity: list[dict[str, Any]] = []
    for unit in units:
        learning_id = str(unit.get("learning_unit_id") or "")
        grammar_id = str(unit.get("grammar_unit_id") or "")
        if not learning_id or not grammar_id:
            raise CP05BuildError("cp04_unit_identity_missing")
        unit_identity.append(
            {
                "learning_unit_id": learning_id,
                "grammar_unit_id": grammar_id,
                "sequence_index": unit.get("sequence_index"),
                "internal_stage": unit.get("internal_stage"),
                "canonical_egp_row_ids": list(unit.get("canonical_egp_row_ids", [])),
            }
        )
        content_by_id = {
            str(row.get("content_candidate_id") or ""): row
            for row in unit.get("content_candidates", [])
            if isinstance(row, Mapping)
        }
        for exercise in unit.get("exercise_candidates", []):
            if not isinstance(exercise, Mapping):
                raise CP05BuildError(f"cp04_exercise_candidate_invalid:{learning_id}")
            source_kind = exercise.get("source_kind")
            content_id = str(exercise.get("content_candidate_id") or "")
            content = content_by_id.get(content_id)
            if content is None:
                raise CP05BuildError(f"cp04_exercise_content_pair_missing:{learning_id}:{content_id}")
            if source_kind == "M11B_REVIEWED_SHARED_ITEM":
                skills = exercise.get("target_skill_lanes")
                if not isinstance(skills, list) or len(skills) != 1 or str(skills[0]).upper() not in ALLOWED_SKILLS:
                    raise CP05BuildError(f"m11b_target_skill_invalid:{learning_id}")
                m11b_reuse.append(
                    {
                        "activity_id": _stable_id("M11B_ACTIVITY", learning_id, str(exercise.get("exercise_candidate_id"))),
                        "learning_unit_id": learning_id,
                        "grammar_unit_id": grammar_id,
                        "exercise_candidate_id": str(exercise.get("exercise_candidate_id")),
                        "content_candidate_id": content_id,
                        "source_item_ref": str(exercise.get("source_ref") or ""),
                        "target_skill": str(skills[0]).upper(),
                        "admission_status": "REUSED_EXISTING_REVIEWED_ADMISSION",
                        "runtime_status": "CP06_ROLE_ASSIGNMENT_REQUIRED",
                    }
                )
            elif source_kind == "RAZ_PROMOTED_MATERIAL":
                material_id = str(exercise.get("source_ref") or "")
                key = (learning_id, material_id)
                if not material_id or key in cp04_raz_candidates:
                    raise CP05BuildError(f"raz_binding_identity_missing_or_duplicate:{learning_id}:{material_id}")
                if content.get("source_ref") != material_id or content.get("grammar_authority_ref") != grammar_id:
                    raise CP05BuildError(f"raz_content_binding_drift:{learning_id}:{material_id}")
                cp04_raz_candidates[key] = (content, exercise)
            else:
                raise CP05BuildError(f"cp04_source_kind_invalid:{learning_id}:{source_kind}")

    materialized_sources: list[dict[str, Any]] = []
    source_remediation: dict[str, dict[str, Any]] = {}
    material_skill_map: dict[str, list[str]] = {}
    source_digest_rows: list[dict[str, str]] = []
    referenced_material_ids = sorted({material_id for _, material_id in cp04_raz_candidates})
    for material_id in referenced_material_ids:
        material = materials.get(material_id)
        if material is None:
            raise CP05BuildError(f"cp04_material_not_in_promoted_registry:{material_id}")
        group = str(material.get("semantic_duplicate_group_id") or "")
        source_ref = str(material.get("selected_source_unit_ref") or "")
        representative = representatives.get(group)
        if representative is None:
            raise CP05BuildError(f"promoted_group_missing_from_dedup:{material_id}:{group}")
        if representative.get("selected_source_unit_ref") != source_ref:
            raise CP05BuildError(f"promoted_source_ref_dedup_mismatch:{material_id}")
        affordances = representative.get("four_skill_affordances")
        if not isinstance(affordances, list):
            raise CP05BuildError(f"representative_affordances_invalid:{material_id}")
        skills = sorted({SKILL_AFFORDANCE_MAP[value] for value in affordances if value in SKILL_AFFORDANCE_MAP})
        source = private_source_rows.get(source_ref)
        if source is None:
            source_remediation[material_id] = {
                "material_id": material_id,
                "source_unit_ref": source_ref,
                "reason_codes": ["PRIVATE_SOURCE_UNIT_NOT_RESOLVED"],
                "remediation_status": "PENDING_PRIVATE_SOURCE_RECOVERY",
            }
            continue
        text = source.get("text")
        if not isinstance(text, str) or not text.strip():
            source_remediation[material_id] = {
                "material_id": material_id,
                "source_unit_ref": source_ref,
                "reason_codes": ["PRIVATE_SOURCE_TEXT_EMPTY"],
                "remediation_status": "PENDING_PRIVATE_SOURCE_RECOVERY",
            }
            continue
        if not skills:
            source_remediation[material_id] = {
                "material_id": material_id,
                "source_unit_ref": source_ref,
                "reason_codes": ["NO_VERIFIED_FOUR_SKILL_AFFORDANCE"],
                "remediation_status": "PENDING_AFFORDANCE_REVIEW",
            }
            continue
        source_sha = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        source_digest_rows.append({"source_unit_ref": source_ref, "source_content_sha256": source_sha})
        material_skill_map[material_id] = skills
        materialized_sources.append(
            {
                "material_id": material_id,
                "semantic_identity_id": group,
                "source_unit_ref": source_ref,
                "source_level": str(material.get("source_level") or source.get("level") or ""),
                "candidate_cefr_scope": str(material.get("candidate_cefr_scope") or ""),
                "source_content": {"text": text.strip()},
                "source_content_sha256": source_sha,
                "verified_skill_affordances": list(affordances),
                "skill_contracts": [_skill_contract(skill) for skill in skills],
                "materialization_status": "MATERIALIZED_PRIVATE_SOURCE_BOUND",
                "admission_status": "ADMISSION_READY",
                "runtime_status": "CP06_ROLE_ASSIGNMENT_REQUIRED",
            }
        )

    admitted_bindings: list[dict[str, Any]] = []
    binding_remediation: list[dict[str, Any]] = []
    skill_binding_counts: Counter[str] = Counter()
    listening_audio_pending_count = 0
    for (learning_id, material_id), (content, exercise) in sorted(cp04_raz_candidates.items()):
        unit = next(row for row in unit_identity if row["learning_unit_id"] == learning_id)
        if material_id in source_remediation:
            binding_remediation.append(
                {
                    "learning_unit_id": learning_id,
                    "grammar_unit_id": unit["grammar_unit_id"],
                    "material_id": material_id,
                    "exercise_candidate_id": str(exercise.get("exercise_candidate_id")),
                    "reason_codes": list(source_remediation[material_id]["reason_codes"]),
                    "remediation_status": source_remediation[material_id]["remediation_status"],
                }
            )
            continue
        skills = material_skill_map[material_id]
        skill_binding_counts.update(skills)
        listening_audio_pending_count += int("LISTENING" in skills)
        admitted_bindings.append(
            {
                "activity_binding_id": _stable_id(
                    "RAZ_ACTIVITY_BINDING",
                    learning_id,
                    material_id,
                    str(exercise.get("exercise_candidate_id")),
                ),
                "learning_unit_id": learning_id,
                "grammar_unit_id": unit["grammar_unit_id"],
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "content_candidate_id": str(content.get("content_candidate_id")),
                "exercise_candidate_id": str(exercise.get("exercise_candidate_id")),
                "material_id": material_id,
                "target_skill_lanes": skills,
                "admission_status": "ADMITTED_PRIVATE_SOURCE_BOUND_ACTIVITY",
                "runtime_status": "CP06_ROLE_ASSIGNMENT_REQUIRED",
            }
        )

    cp04_summary = cp04_artifact.get("coverage_summary", {})
    if len(m11b_reuse) != cp04_summary.get("ready_reuse_exercise_candidate_count"):
        raise CP05BuildError("m11b_reuse_count_not_reconciled")
    if len(cp04_raz_candidates) != cp04_summary.get("pending_raz_exercise_derivation_candidate_count"):
        raise CP05BuildError("raz_binding_candidate_count_not_reconciled")
    if len(admitted_bindings) + len(binding_remediation) != len(cp04_raz_candidates):
        raise CP05BuildError("raz_binding_disposition_not_exhaustive")

    source_digest_rows.sort(key=lambda row: row["source_unit_ref"])
    private_source_set_sha = _digest(source_digest_rows)
    payload = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
        "learning_units": unit_identity,
        "materialized_raz_sources": sorted(materialized_sources, key=lambda row: row["material_id"]),
        "raz_unit_activity_bindings": admitted_bindings,
        "m11b_reuse_activities": sorted(m11b_reuse, key=lambda row: row["activity_id"]),
        "remediation_queue": sorted(
            list(source_remediation.values()) + binding_remediation,
            key=lambda row: (str(row.get("material_id")), str(row.get("learning_unit_id", ""))),
        ),
        "coverage_summary": {
            "existing_learning_unit_count": 24,
            "new_learning_unit_count": 0,
            "cp04_content_candidate_count": cp04_summary.get("content_candidate_count"),
            "cp04_exercise_candidate_count": cp04_summary.get("exercise_candidate_count"),
            "m11b_reused_activity_count": len(m11b_reuse),
            "raz_distinct_candidate_material_count": len(referenced_material_ids),
            "raz_materialized_source_count": len(materialized_sources),
            "raz_source_remediation_material_count": len(source_remediation),
            "raz_candidate_binding_count": len(cp04_raz_candidates),
            "raz_admitted_activity_binding_count": len(admitted_bindings),
            "raz_remediation_binding_count": len(binding_remediation),
            "skill_binding_counts": dict(sorted(skill_binding_counts.items())),
            "listening_audio_generation_pending_binding_count": listening_audio_pending_count,
        },
        "private_source_identity": {
            "private_source_set_sha256": private_source_set_sha,
            "private_source_record_count": len(private_source_rows),
            "resolved_source_count": len(source_digest_rows),
            "source_index_sha256": _digest(list(source_index or [])),
        },
        "claim_boundaries": {
            "private_source_text_read": True,
            "private_source_text_in_private_candidate": True,
            "private_source_text_in_safe_readback": False,
            "objective_answer_fabricated": False,
            "canonical_unit_identity_changed": False,
            "canonical_egp_mapping_changed": False,
            "learner_runtime_publication_performed": False,
            "four_skill_runtime_projection_performed": False,
            "mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    source_bindings = {
        "cp04_task_id": cp04_artifact["task_id"],
        "cp04_artifact_sha256": _digest(cp04_artifact),
        "raz_registry_task_id": registry_package["task_id"],
        "raz_registry_package_sha256": registry_package["package_sha256"],
        "semantic_dedup_task_id": dedup_package["task_id"],
        "semantic_dedup_package_sha256": dedup_package["package_sha256"],
        "private_source_set_sha256": private_source_set_sha,
        "existing_learning_unit_count": 24,
    }
    return payload, source_bindings


def build_policy_candidate(
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    dedup_package: Mapping[str, Any],
    private_source_rows: Mapping[str, Mapping[str, Any]],
    *,
    source_index: Sequence[Mapping[str, Any]] | None = None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload, source_bindings = build_private_payload(
        cp04_artifact,
        registry_package,
        dedup_package,
        private_source_rows,
        source_index=source_index,
    )
    return content_policy.build_candidate(
        payload=payload,
        producer_id=PRODUCER_ID,
        level_scope=["A1", "A1+"],
        source_bindings=source_bindings,
        policy=policy,
    )


def build_safe_readback(
    candidate: Mapping[str, Any],
    approved: Mapping[str, Any],
    candidate_report: Mapping[str, Any],
) -> dict[str, Any]:
    payload = approved["payload"]
    summary = dict(payload["coverage_summary"])
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": "a1fs.v1.cp05.private_candidate_materialization_admission.safe_readback.v1",
        "scope": "A1_A1_PLUS_ONLY",
        "validation_status": PASS_STATUS,
        "source_identity": {
            **dict(candidate["source_bindings"]),
            "candidate_artifact_sha256": candidate["artifact_sha256"],
            "approved_artifact_sha256": approved["artifact_sha256"],
            "candidate_validation_sha256": _digest(candidate_report),
        },
        "coverage_summary": summary,
        "admission_gate": {
            "decision": "PRIVATE_CANDIDATE_MATERIALIZATION_AND_ADMISSION_READY",
            "approved_canonical_private_content_created": True,
            "runtime_publication_allowed": False,
            "cp06_role_population_required": True,
            "cp07_runtime_projection_required": True,
            "a2_a2plus_status": "LOCKED",
        },
        "claim_boundaries": {
            "private_source_text_included": False,
            "prompt_or_scoring_content_included": False,
            "learner_response_included": False,
            "runtime_publication_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }


def run_pipeline(
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
    dedup_package: Mapping[str, Any],
    private_source_rows: Mapping[str, Mapping[str, Any]],
    *,
    source_index: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_policy_candidate(
        cp04_artifact,
        registry_package,
        dedup_package,
        private_source_rows,
        source_index=source_index,
    )
    from ulga.validators import validate_a1fs_v1_cp05_private_candidate_materialization_and_admission as validator

    candidate_report = validator.validate_candidate(
        candidate,
        cp04_artifact=cp04_artifact,
        registry_package=registry_package,
        dedup_package=dedup_package,
    )
    if candidate_report.get("validation_status") != validator.CANDIDATE_PASS_STATUS:
        raise CP05BuildError(f"candidate_validation_failed:{candidate_report.get('errors')}")
    receipt_sha = _digest(candidate_report)
    approved = content_policy.admit_candidate(
        candidate,
        validation_receipts=[
            {
                "validator_id": "validate_a1fs_v1_cp05_private_candidate_materialization_and_admission",
                "status": "PASS",
                "receipt_sha256": receipt_sha,
            }
        ],
        decision_ref=f"{TASK_ID}:{receipt_sha}",
        producer_id=PRODUCER_ID,
    )
    safe = build_safe_readback(candidate, approved, candidate_report)
    release_report = validator.validate_release(
        candidate,
        approved,
        safe,
        cp04_artifact=cp04_artifact,
        registry_package=registry_package,
        dedup_package=dedup_package,
    )
    if release_report.get("validation_status") != PASS_STATUS:
        raise CP05BuildError(f"release_validation_failed:{release_report.get('errors')}")
    return candidate, approved, safe, release_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp04", type=Path, default=DEFAULT_CP04)
    parser.add_argument("--raz-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--semantic-dedup", type=Path, default=DEFAULT_DEDUP)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--candidate-output", type=Path, default=DEFAULT_CANDIDATE_OUTPUT)
    parser.add_argument("--approved-output", type=Path, default=DEFAULT_APPROVED_OUTPUT)
    parser.add_argument("--safe-output", type=Path, default=DEFAULT_SAFE_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        cp04_artifact = _read(args.cp04)
        registry_package = _read(args.raz_registry)
        dedup_package = _read(args.semantic_dedup)
        private_rows, source_index = load_private_source_rows(args.source_root)
        candidate, approved, safe, report = run_pipeline(
            cp04_artifact,
            registry_package,
            dedup_package,
            private_rows,
            source_index=source_index,
        )
        _write_atomic(args.candidate_output, candidate)
        _write_atomic(args.approved_output, approved)
        _write_atomic(args.safe_output, safe)
        _write_atomic(args.report_output, report)
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "validation_status": report["validation_status"],
                    "coverage_summary": safe["coverage_summary"],
                    "candidate_artifact_sha256": candidate["artifact_sha256"],
                    "approved_artifact_sha256": approved["artifact_sha256"],
                    "stop_reason": safe["stop_reason"],
                    "next_short_step": safe["next_short_step"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (CP05BuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
