from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1.u04ms01_cross_source_reference_bank_and_unit04_projection import (
    STATUS as M1_STATUS,
    build_unit04_reference_projection,
)
from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    STATUS as M2A_STATUS,
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)
from product.a1fs_v1_2_1.u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay import (
    STATUS as M2B_STATUS,
    build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay,
)

TASK_ID = "A1FS-V1-U04MS02C_KETFourSkillTaskAssessmentProjection"
STATUS = "PASS_A1FS_V1_U04MS02C_KET_FOUR_SKILL_TASK_ASSESSMENT_PROJECTION"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Deterministic four-skill task/assessment projection over already-admitted Unit04 Q07/M2-A "
    "language and M2-B teacher-delivery structure, using the existing formal KET prerequisite/resource "
    "anchor only as non-authoritative task/resource evidence; no KET wording or canonical content is authored."
)

CP07B_ANCHOR = "ulga/builders/cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay_impl.py"
FORMAL_KET_SOURCE_ID = "KET_FOUR_SKILL_PREREQUISITE"
FORMAL_KET_AUTHORITY_ROLE = "FORMAL_PREREQUISITE_AND_RESOURCE_EVIDENCE"
SKILLS = ("READING", "LISTENING", "SPEAKING", "WRITING")

TASK_SHAPES: dict[str, dict[str, Any]] = {
    "READING": {
        "task_family": "SHORT_READING_LOCATION_EXTRACTION",
        "assessment_operation": "EXTRACT_LOCATION_RELATION_FROM_EXISTING_UNIT04_MICRO_SCENE",
        "formal_prerequisite_signals": ["READING_STRATEGY"],
        "teacher_delivery_stage_roles": ["FOLLOW_UP_PROMPT"],
        "resource_mode": "FORMAL_FOUR_SKILL_DOMAIN_REFERENCE_PLUS_UNIT04_EXISTING_TEXT_SCENE",
        "response_authority": "UNIT04_Q07_VIA_M2A",
    },
    "LISTENING": {
        "task_family": "LISTENING_LOCATION_EXTRACTION",
        "assessment_operation": "IDENTIFY_LOCATION_RELATION_FROM_FORMAL_LISTENING_RESOURCE_SLOT",
        "formal_prerequisite_signals": ["LISTENING_STRATEGY"],
        "teacher_delivery_stage_roles": ["GUIDED_DIALOGUE"],
        "resource_mode": "FORMAL_LISTENING_DOMAIN_REFERENCE_ONLY_NO_AUDIO_BODY",
        "response_authority": "UNIT04_Q07_VIA_M2A",
    },
    "SPEAKING": {
        "task_family": "SPEAKING_LOCATION_QA_AND_TRANSFER",
        "assessment_operation": "LOCATION_QA_SCENE_DESCRIPTION_AND_ALTERNATE_SCENE_TRANSFER",
        "formal_prerequisite_signals": ["SPEAKING_FUNCTION"],
        "teacher_delivery_stage_roles": ["GUIDED_DIALOGUE", "FOLLOW_UP_PROMPT", "TRANSFER_PROMPT"],
        "resource_mode": "FORMAL_SPEAKING_DOMAIN_REFERENCE_ONLY_NO_KET_WORDING",
        "response_authority": "UNIT04_Q07_VIA_M2A",
    },
    "WRITING": {
        "task_family": "SHORT_WRITING_LOCATION_DESCRIPTION",
        "assessment_operation": "WRITE_SHORT_LOCATION_DESCRIPTION_FROM_EXISTING_UNIT04_SCENE",
        "formal_prerequisite_signals": ["WRITING_STRATEGY"],
        "teacher_delivery_stage_roles": ["FOLLOW_UP_PROMPT"],
        "resource_mode": "FORMAL_WRITING_DOMAIN_REFERENCE_ONLY_NO_KET_WORDING",
        "response_authority": "UNIT04_Q07_VIA_M2A",
    },
}

FORBIDDEN_OUTPUT_KEYS = {
    "source_text", "transcript_text", "body_text", "raw_text", "clean_text", "prompt",
    "correct_answer", "answer_key", "learner_response", "audio_bytes", "recording",
}


class ProjectionError(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _assert_no_forbidden_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in FORBIDDEN_OUTPUT_KEYS:
                raise ProjectionError(f"forbidden_output_key:{path}.{key}")
            _assert_no_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, f"{path}[{index}]")


def _formal_ket_registry_row(m1: dict[str, Any]) -> dict[str, Any]:
    if m1.get("status") != M1_STATUS:
        raise ProjectionError("m1_cross_source_projection_not_pass")
    rows = m1.get("source_registry")
    if not isinstance(rows, list):
        raise ProjectionError("m1_source_registry_missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("source_id") == FORMAL_KET_SOURCE_ID]
    if len(matches) != 1:
        raise ProjectionError("formal_ket_source_registry_identity_invalid")
    row = matches[0]
    if row.get("authority_role") != FORMAL_KET_AUTHORITY_ROLE:
        raise ProjectionError("formal_ket_authority_role_drift")
    if row.get("learner_facing_authority") is not False or row.get("canonical_promotion_allowed") is not False:
        raise ProjectionError("formal_ket_authority_boundary_broken")
    if row.get("integration_anchor_resolved") is not True:
        raise ProjectionError("formal_ket_integration_anchor_unresolved")
    return row


def _validate_cp07b_anchor(root: Path) -> dict[str, Any]:
    path = root / CP07B_ANCHOR
    if not path.is_file():
        raise ProjectionError("cp07b_formal_prerequisite_anchor_missing")
    text = path.read_text(encoding="utf-8")
    required_signals = sorted({signal for shape in TASK_SHAPES.values() for signal in shape["formal_prerequisite_signals"]})
    missing = [signal for signal in required_signals if signal not in text]
    if missing:
        raise ProjectionError("cp07b_formal_prerequisite_signal_missing:" + ",".join(missing))
    return {
        "source": CP07B_ANCHOR,
        "required_signal_count": len(required_signals),
        "required_signals": required_signals,
        "anchor_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "source_body_emitted": False,
    }


def _validate_m2a(m2a: dict[str, Any]) -> list[dict[str, Any]]:
    if m2a.get("status") != M2A_STATUS:
        raise ProjectionError("m2a_not_pass")
    capabilities = m2a.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != 36:
        raise ProjectionError("m2a_capability_count_invalid")
    seen: set[str] = set()
    for row in capabilities:
        if not isinstance(row, dict):
            raise ProjectionError("m2a_capability_row_invalid")
        cid = str(row.get("capability_id") or "")
        scene_refs = row.get("unit04_scene_ref_ids")
        sentence_ids = row.get("unit04_sentence_ids")
        if not cid or cid in seen or not isinstance(scene_refs, list) or not scene_refs or not isinstance(sentence_ids, list):
            raise ProjectionError("m2a_capability_identity_invalid")
        if len(scene_refs) != len(sentence_ids) or row.get("authority_boundary", {}).get("a2_unlocked") is not False:
            raise ProjectionError(f"m2a_capability_binding_invalid:{cid}")
        seen.add(cid)
    return capabilities


def _validate_m2b(m2b: dict[str, Any], capability_ids: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    if m2b.get("status") != M2B_STATUS:
        raise ProjectionError("m2b_not_pass")
    summary = m2b.get("overlay_summary")
    inventory = m2b.get("ket99_evidence_inventory")
    overlays = m2b.get("overlays")
    if not isinstance(summary, dict) or not isinstance(inventory, dict) or not isinstance(overlays, list):
        raise ProjectionError("m2b_structure_invalid")
    if summary.get("interaction_stage_count") != 144:
        raise ProjectionError("m2b_stage_count_invalid")
    if summary.get("semantic_compatible_stage_count") != 144 or summary.get("semantic_incompatible_stage_count") != 0:
        raise ProjectionError("m2b_semantic_gate_not_144_of_144")
    stage_pool_counts = inventory.get("stage_pool_counts")
    expected_roles = {"GUIDED_DIALOGUE", "FOLLOW_UP_PROMPT", "ERROR_REPAIR", "TRANSFER_PROMPT"}
    if not isinstance(stage_pool_counts, dict) or set(stage_pool_counts) != expected_roles:
        raise ProjectionError("m2b_stage_pool_counts_invalid")
    if any(int(value) <= 0 for value in stage_pool_counts.values()):
        raise ProjectionError("m2b_stage_pool_empty")

    by_capability: dict[str, dict[str, Any]] = {}
    for row in overlays:
        if not isinstance(row, dict):
            raise ProjectionError("m2b_overlay_row_invalid")
        cid = str(row.get("unit04_capability_id") or "")
        if cid not in capability_ids or cid in by_capability:
            raise ProjectionError(f"m2b_overlay_capability_binding_invalid:{cid}")
        stages = row.get("interaction_stages")
        if not isinstance(stages, list) or len(stages) != 4:
            raise ProjectionError(f"m2b_overlay_stage_structure_invalid:{cid}")
        stage_by_role = {str(stage.get("stage_role") or ""): stage for stage in stages if isinstance(stage, dict)}
        if set(stage_by_role) != expected_roles:
            raise ProjectionError(f"m2b_overlay_stage_roles_invalid:{cid}")
        if any(stage.get("semantic_compatibility") != "PASS" for stage in stage_by_role.values()):
            raise ProjectionError(f"m2b_overlay_semantic_compatibility_invalid:{cid}")
        by_capability[cid] = row
    if set(by_capability) != capability_ids:
        raise ProjectionError("m2b_overlay_capability_coverage_incomplete")
    return by_capability, {str(key): int(value) for key, value in stage_pool_counts.items()}


def _task_row(capability: dict[str, Any], overlay: dict[str, Any], skill: str, shape: dict[str, Any]) -> dict[str, Any]:
    stages = {str(stage["stage_role"]): stage for stage in overlay["interaction_stages"] if isinstance(stage, dict)}
    selected_roles = list(shape["teacher_delivery_stage_roles"])
    selected_stages = [stages[role] for role in selected_roles]
    if any(stage.get("semantic_compatibility") != "PASS" for stage in selected_stages):
        raise ProjectionError(f"selected_teacher_delivery_stage_not_semantic_pass:{skill}")

    identity = f"{capability['capability_id']}|{skill}|{shape['task_family']}|{FORMAL_KET_SOURCE_ID}"
    projection_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20].upper()
    return {
        "task_projection_id": f"U04-MS02C-KET-{projection_id}",
        "skill": skill,
        "task_family": shape["task_family"],
        "assessment_operation": shape["assessment_operation"],
        "formal_ket_source_id": FORMAL_KET_SOURCE_ID,
        "formal_ket_authority_role": FORMAL_KET_AUTHORITY_ROLE,
        "formal_prerequisite_signals": list(shape["formal_prerequisite_signals"]),
        "task_shape_authority": "UNIT04_PROJECTED_SHAPE_NOT_OFFICIAL_KET_ITEM_FORMAT",
        "resource_mode": shape["resource_mode"],
        "unit04_capability_id": capability["capability_id"],
        "unit04_scene_ref_ids": list(capability["unit04_scene_ref_ids"]),
        "unit04_sentence_ids": list(capability["unit04_sentence_ids"]),
        "unit04_relation_surfaces": list(capability.get("relation_surfaces", [])),
        "m2b_overlay_id": overlay["overlay_id"],
        "teacher_delivery_stage_roles": selected_roles,
        "teacher_delivery_evidence_refs": [stage["ket99_evidence_ref_id"] for stage in selected_stages],
        "teacher_delivery_semantic_compatibility": ["PASS" for _ in selected_stages],
        "response_authority": shape["response_authority"],
        "authority_boundary": {
            "learner_language_authority": "UNIT04_Q07_VIA_M2A",
            "formal_ket_is_learner_facing_authority": False,
            "formal_ket_canonical_promotion_allowed": False,
            "ket99_teacher_delivery_is_learner_facing_authority": False,
            "new_learner_facing_wording_authored": False,
            "formal_ket_source_text_copied": False,
            "a2_unlocked": False,
        },
    }


def build_unit04_ket_four_skill_task_assessment_projection(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    m1 = build_unit04_reference_projection(root)
    formal_row = _formal_ket_registry_row(m1)
    cp07b_anchor = _validate_cp07b_anchor(root)
    m2a = build_unit04_raz_aw_multi_sentence_micro_scene_capability(root)
    capabilities = _validate_m2a(m2a)
    capability_ids = {str(row["capability_id"]) for row in capabilities}
    m2b = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(root)
    overlay_by_capability, stage_pool_counts = _validate_m2b(m2b, capability_ids)

    tasks: list[dict[str, Any]] = []
    for capability in capabilities:
        overlay = overlay_by_capability[str(capability["capability_id"])]
        if list(overlay.get("unit04_scene_ref_ids", [])) != list(capability["unit04_scene_ref_ids"]):
            raise ProjectionError("m2b_scene_lineage_drift")
        if list(overlay.get("unit04_sentence_ids", [])) != list(capability["unit04_sentence_ids"]):
            raise ProjectionError("m2b_sentence_lineage_drift")
        for skill in SKILLS:
            tasks.append(_task_row(capability, overlay, skill, TASK_SHAPES[skill]))

    skill_counts = Counter(row["skill"] for row in tasks)
    if len(tasks) != 144 or skill_counts != Counter({skill: 36 for skill in SKILLS}):
        raise ProjectionError("four_skill_projection_count_invalid")
    if len({row["task_projection_id"] for row in tasks}) != len(tasks):
        raise ProjectionError("task_projection_identity_not_unique")

    result: dict[str, Any] = {
        "schema_version": "a1fs.v1.u04.ms02c.ket_four_skill_task_assessment_projection.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "source_refs": {
            "m1_cross_source_reference_projection": "product/a1fs_v1_2_1/u04ms01_cross_source_reference_bank_and_unit04_projection.py",
            "m2a_multi_sentence_capability": "product/a1fs_v1_2_1/u04ms02a_raz_aw_multi_sentence_micro_scene_capability.py",
            "m2b_teacher_delivery_overlay": "product/a1fs_v1_2_1/u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay.py",
            "formal_ket_prerequisite_anchor": CP07B_ANCHOR,
        },
        "formal_ket_reference": {
            "source_id": formal_row["source_id"],
            "authority_role": formal_row["authority_role"],
            "learner_facing_authority": formal_row["learner_facing_authority"],
            "canonical_promotion_allowed": formal_row["canonical_promotion_allowed"],
            "integration_anchor_resolved": formal_row["integration_anchor_resolved"],
            "resolved_locators": list(formal_row.get("resolved_locators", [])),
            "anchor_validation": cp07b_anchor,
        },
        "scope": {
            "four_skill_task_assessment_projection_only": True,
            "form01_20_modified": False,
            "canonical_grammar_modified": False,
            "canonical_vocabulary_modified": False,
            "canonical_chunk_modified": False,
            "new_learner_facing_wording_authored": False,
            "formal_ket_source_text_included": False,
            "private_ket_body_read": False,
            "unit05_plus_grammar_opened": False,
            "a2_unlocked": False,
        },
        "projection_summary": {
            "unit04_capability_count": len(capabilities),
            "task_projection_count": len(tasks),
            "skill_count": len(SKILLS),
            "skill_distribution": {skill: skill_counts[skill] for skill in SKILLS},
            "m2b_interaction_stage_count": m2b["overlay_summary"]["interaction_stage_count"],
            "m2b_semantic_compatible_stage_count": m2b["overlay_summary"]["semantic_compatible_stage_count"],
            "m2b_semantic_incompatible_stage_count": m2b["overlay_summary"]["semantic_incompatible_stage_count"],
            "m2b_stage_pool_counts": stage_pool_counts,
        },
        "task_projections": tasks,
        "safety": {
            "formal_ket_authority_role_preserved": FORMAL_KET_AUTHORITY_ROLE,
            "formal_ket_learner_facing_authority": False,
            "formal_ket_canonical_promotion_allowed": False,
            "formal_ket_source_text_copied": False,
            "private_ket_body_read": False,
            "all_tasks_resolve_to_existing_unit04_q07_via_m2a": True,
            "m2b_teacher_delivery_semantic_gate_144_of_144": True,
            "forms_modified": False,
            "canonical_authority_mutated": False,
            "unit05_plus_grammar_leak_count": 0,
            "a2_plus_unlock_count": 0,
        },
    }
    result["projection_sha256"] = _digest({
        "formal_ket_reference": result["formal_ket_reference"],
        "scope": result["scope"],
        "projection_summary": result["projection_summary"],
        "task_projections": result["task_projections"],
        "safety": result["safety"],
    })
    _assert_no_forbidden_keys(result)
    return result


def compact_readback(projection: dict[str, Any]) -> dict[str, Any]:
    summary = projection["projection_summary"]
    return {
        "status": projection["status"],
        "task_projection_count": summary["task_projection_count"],
        "skill_distribution": summary["skill_distribution"],
        "unit04_capability_count": summary["unit04_capability_count"],
        "m2b_stage_pool_counts": summary["m2b_stage_pool_counts"],
        "m2b_semantic_compatible_stage_count": summary["m2b_semantic_compatible_stage_count"],
        "m2b_semantic_incompatible_stage_count": summary["m2b_semantic_incompatible_stage_count"],
        "formal_ket_authority_role": projection["formal_ket_reference"]["authority_role"],
        "formal_ket_source_text_copied": projection["safety"]["formal_ket_source_text_copied"],
        "forms_modified": projection["safety"]["forms_modified"],
        "canonical_authority_mutated": projection["safety"]["canonical_authority_mutated"],
        "a2_plus_unlock_count": projection["safety"]["a2_plus_unlock_count"],
        "projection_sha256": projection["projection_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    projection = build_unit04_ket_four_skill_task_assessment_projection(args.repo_root)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("U04MS02C_ACCEPTANCE_READBACK=" + json.dumps(compact_readback(projection), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
