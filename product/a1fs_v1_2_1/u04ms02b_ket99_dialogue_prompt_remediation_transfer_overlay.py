from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)

TASK_ID = "A1FS-V1-U04MS02B_KET99DialoguePromptRemediationTransferOverlay"
STATUS = "PASS_A1FS_V1_U04MS02B_KET99_DIALOGUE_PROMPT_REMEDIATION_TRANSFER_OVERLAY"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Deterministic structural teacher-delivery overlay over already-admitted Unit04 Q07/M2-A "
    "language authority using repository-exportable, text-free KET99 derived evidence only; "
    "does not copy transcript wording or promote KET99 into canonical authority."
)

KET99_DIR = "ulga/reports/ket_comp_transcript_final_consolidation"
ARTIFACT_INDEX = f"{KET99_DIR}/artifact_index.json"
CONTENT_UNITS = f"{KET99_DIR}/transcript_content_units.jsonl"
SEMANTIC = f"{KET99_DIR}/normalized_transcript_semantic_artifact.jsonl"
ADMISSION = f"{KET99_DIR}/transcript_admission_decisions.json"
EXPECTED_IDS = tuple(f"P{n:03d}" for n in range(4, 103))
STAGE_ROLES = ("GUIDED_DIALOGUE", "FOLLOW_UP_PROMPT", "ERROR_REPAIR", "TRANSFER_PROMPT")
FORBIDDEN_OUTPUT_KEYS = {
    "source_text", "transcript_text", "body_text", "raw_text", "clean_text", "title",
    "evidence_items", "correct_answer", "answer_key", "learner_response", "prompt",
}


class OverlayError(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise OverlayError(f"required_source_missing:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OverlayError(f"json_object_required:{path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise OverlayError(f"required_source_missing:{path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise OverlayError(f"jsonl_object_required:{path}:{line_number}")
        rows.append(value)
    return rows


def _sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _assert_no_forbidden_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in FORBIDDEN_OUTPUT_KEYS:
                raise OverlayError(f"forbidden_output_key:{path}.{key}")
            _assert_no_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, f"{path}[{index}]")


def _validate_artifact_index(index: dict[str, Any]) -> None:
    artifacts = index.get("artifacts")
    if not isinstance(artifacts, list):
        raise OverlayError("artifact_index_rows_missing")
    by_id = {str(row.get("artifact_id") or ""): row for row in artifacts if isinstance(row, dict)}
    required = {
        "KET99_PUBLIC_NORMALIZED_TRANSCRIPT_SEMANTIC_ARTIFACT",
        "KET99_PUBLIC_TRANSCRIPT_CONTENT_UNITS",
    }
    if not required.issubset(by_id):
        raise OverlayError("required_public_ket99_artifact_missing")
    if any(by_id[key].get("repository_export_allowed") is not True for key in required):
        raise OverlayError("required_ket99_artifact_not_exportable")
    private = by_id.get("KET99_PRIVATE_NORMALIZED_TRANSCRIPTS")
    if not isinstance(private, dict) or private.get("repository_export_allowed") is not False:
        raise OverlayError("private_ket99_boundary_missing")


def _admission_by_transcript(admission: dict[str, Any]) -> dict[str, dict[str, Any]]:
    decisions = admission.get("decisions")
    if not isinstance(decisions, list):
        raise OverlayError("admission_decisions_missing")
    by_id: dict[str, dict[str, Any]] = {}
    for row in decisions:
        if not isinstance(row, dict) or row.get("subject_type") != "content_unit":
            continue
        transcript_id = str(row.get("transcript_id") or "")
        if transcript_id in by_id:
            raise OverlayError(f"admission_duplicate:{transcript_id}")
        d = row.get("decisions")
        requirements = row.get("requirements")
        if not isinstance(d, dict):
            raise OverlayError(f"admission_map_missing:{transcript_id}")
        if d.get("teacher_delivery") != "approved":
            raise OverlayError(f"teacher_delivery_not_approved:{transcript_id}")
        if d.get("lesson_planner") != "approved_with_constraints":
            raise OverlayError(f"lesson_planner_not_constrained:{transcript_id}")
        if d.get("canonical_grammar_authority") != "denied" or d.get("canonical_vocabulary_authority") != "denied":
            raise OverlayError(f"canonical_authority_not_denied:{transcript_id}")
        if not isinstance(requirements, list) or "map_language_items_to_canonical_authorities" not in requirements:
            raise OverlayError(f"canonical_mapping_requirement_missing:{transcript_id}")
        by_id[transcript_id] = row
    if tuple(sorted(by_id)) != EXPECTED_IDS:
        raise OverlayError("admission_transcript_range_mismatch")
    return by_id


def _build_evidence_inventory(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    _validate_artifact_index(_json(root / ARTIFACT_INDEX))
    units = _jsonl(root / CONTENT_UNITS)
    semantic = _jsonl(root / SEMANTIC)
    admission = _admission_by_transcript(_json(root / ADMISSION))
    if len(units) != 99 or len(semantic) != 99:
        raise OverlayError("ket99_public_row_count_mismatch")
    units_by_id = {str(row.get("transcript_id") or ""): row for row in units}
    semantic_by_id = {str(row.get("transcript_id") or ""): row for row in semantic}
    if tuple(sorted(units_by_id)) != EXPECTED_IDS or tuple(sorted(semantic_by_id)) != EXPECTED_IDS:
        raise OverlayError("ket99_transcript_identity_range_mismatch")

    inventory: list[dict[str, Any]] = []
    pools: dict[str, list[str]] = {role: [] for role in STAGE_ROLES}
    for transcript_id in EXPECTED_IDS:
        unit = units_by_id[transcript_id]
        sem = semantic_by_id[transcript_id]
        adm = admission[transcript_id]
        if unit.get("authority_status") != "non_authoritative" or unit.get("canonical_promotion_allowed") is not False:
            raise OverlayError(f"content_unit_authority_boundary_broken:{transcript_id}")
        if sem.get("authority_status") != "non_authoritative" or sem.get("raw_text_included") is not False:
            raise OverlayError(f"semantic_authority_boundary_broken:{transcript_id}")
        source_span = unit.get("source_span")
        if not isinstance(source_span, dict):
            raise OverlayError(f"source_span_missing:{transcript_id}")
        evidence_sha = str(source_span.get("evidence_sha256") or "")
        if len(evidence_sha) != 64 or sem.get("source_sha256") != evidence_sha:
            raise OverlayError(f"source_lineage_mismatch:{transcript_id}")
        evidence_items = unit.get("evidence_items")
        roles = unit.get("content_roles")
        risk_flags = unit.get("risk_flags")
        if not isinstance(evidence_items, list) or not isinstance(roles, list) or not isinstance(risk_flags, list):
            raise OverlayError(f"content_unit_structure_invalid:{transcript_id}")
        role_set = {str(value) for value in roles}
        teacher_delivery = "teacher_delivery" in role_set
        eligibility = {
            "GUIDED_DIALOGUE": teacher_delivery and "speaking" in role_set,
            "FOLLOW_UP_PROMPT": teacher_delivery and bool(role_set.intersection({"speaking", "writing"})),
            "ERROR_REPAIR": teacher_delivery and "error_diagnosis" in role_set,
            "TRANSFER_PROMPT": teacher_delivery and (
                unit.get("lesson_role") == "review" or "review" in role_set or {"speaking", "writing"}.issubset(role_set)
            ),
        }
        evidence_ref_id = f"KET99-TEXTFREE-{transcript_id}"
        row = {
            "evidence_ref_id": evidence_ref_id,
            "transcript_id": transcript_id,
            "content_unit_id": unit.get("content_unit_id"),
            "source_unit_id": unit.get("unit_id"),
            "lesson_role": unit.get("lesson_role"),
            "content_roles": sorted(role_set),
            "risk_flags": sorted(str(value) for value in risk_flags),
            "source_evidence_sha256": evidence_sha,
            "normalized_text_sha256": sem.get("normalized_text_sha256"),
            "evidence_item_count": len(evidence_items),
            "evidence_item_digest_sha256": _sha(evidence_items),
            "stage_role_eligibility": eligibility,
            "authority_status": "non_authoritative",
            "canonical_promotion_allowed": False,
            "raw_text_included": False,
            "admission": {
                "admission_id": adm.get("admission_id"),
                "teacher_delivery": "approved",
                "lesson_planner": "approved_with_constraints",
                "canonical_grammar_authority": "denied",
                "canonical_vocabulary_authority": "denied",
            },
        }
        inventory.append(row)
        for role, allowed in eligibility.items():
            if allowed:
                pools[role].append(evidence_ref_id)
    if any(not refs for refs in pools.values()):
        raise OverlayError("ket99_stage_evidence_pool_empty")
    return inventory, pools


def _pick(pool: list[str], capability_index: int, salt: int) -> str:
    return pool[(capability_index * 7 + salt * 11) % len(pool)]


def build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    root = _root(repo_root)
    inventory, pools = _build_evidence_inventory(root)
    m2a = build_unit04_raz_aw_multi_sentence_micro_scene_capability(root)
    capabilities = m2a.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != 36:
        raise OverlayError("m2a_capability_supply_invalid")

    overlays: list[dict[str, Any]] = []
    for index, capability in enumerate(capabilities):
        transfer_target = capabilities[(index + 1) % len(capabilities)]
        selected_refs = {
            role: _pick(pools[role], index, stage_index)
            for stage_index, role in enumerate(STAGE_ROLES)
        }
        stages = [
            {
                "stage_role": "GUIDED_DIALOGUE",
                "delivery_operation": "ELICIT_FROM_EXISTING_UNIT04_SCENE",
                "ket99_evidence_ref_id": selected_refs["GUIDED_DIALOGUE"],
            },
            {
                "stage_role": "FOLLOW_UP_PROMPT",
                "delivery_operation": "FOLLOW_UP_ON_EXISTING_UNIT04_SCENE",
                "ket99_evidence_ref_id": selected_refs["FOLLOW_UP_PROMPT"],
            },
            {
                "stage_role": "ERROR_REPAIR",
                "delivery_operation": "REFOCUS_EXISTING_UNIT04_RELATION_AND_MODEL",
                "ket99_evidence_ref_id": selected_refs["ERROR_REPAIR"],
            },
            {
                "stage_role": "TRANSFER_PROMPT",
                "delivery_operation": "TRANSFER_TO_ALTERNATE_UNIT04_Q07_SCENE",
                "ket99_evidence_ref_id": selected_refs["TRANSFER_PROMPT"],
                "transfer_target_capability_id": transfer_target["capability_id"],
                "transfer_target_scene_ref_ids": list(transfer_target["unit04_scene_ref_ids"]),
            },
        ]
        overlay_id = hashlib.sha256(
            f"{capability['capability_id']}|{'|'.join(selected_refs[role] for role in STAGE_ROLES)}".encode("utf-8")
        ).hexdigest()[:20].upper()
        overlays.append({
            "overlay_id": f"U04-MS02B-KET99-{overlay_id}",
            "unit04_capability_id": capability["capability_id"],
            "unit04_scene_ref_ids": list(capability["unit04_scene_ref_ids"]),
            "unit04_sentence_ids": list(capability["unit04_sentence_ids"]),
            "interaction_stages": stages,
            "authority_boundary": {
                "learner_language_authority": "UNIT04_Q07_VIA_M2A",
                "ket99_is_learner_facing_authority": False,
                "ket99_canonical_promotion_allowed": False,
                "ket99_raw_transcript_text_copied": False,
                "new_learner_facing_wording_authored": False,
                "a2_unlocked": False,
            },
        })

    stage_counts = Counter(stage["stage_role"] for row in overlays for stage in row["interaction_stages"])
    used_refs = {stage["ket99_evidence_ref_id"] for row in overlays for stage in row["interaction_stages"]}
    result: dict[str, Any] = {
        "schema_version": "a1fs.v1.u04.ms02b.ket99.dialogue_prompt_remediation_transfer_overlay.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "source_refs": {
            "m2a": "product/a1fs_v1_2_1/u04ms02a_raz_aw_multi_sentence_micro_scene_capability.py",
            "ket99_artifact_index": ARTIFACT_INDEX,
            "ket99_content_units": CONTENT_UNITS,
            "ket99_semantic_artifact": SEMANTIC,
            "ket99_admission": ADMISSION,
        },
        "scope": {
            "structural_teacher_delivery_overlay_only": True,
            "form01_20_modified": False,
            "canonical_grammar_modified": False,
            "canonical_vocabulary_modified": False,
            "canonical_chunk_modified": False,
            "new_learner_facing_wording_authored": False,
            "raw_ket99_transcript_text_included": False,
            "unit05_plus_grammar_opened": False,
            "a2_unlocked": False,
        },
        "ket99_evidence_inventory": {
            "transcript_count": len(inventory),
            "expected_transcript_range": {"first": "P004", "last": "P102", "count": 99},
            "stage_pool_counts": {role: len(pools[role]) for role in STAGE_ROLES},
            "materialized_evidence_ref_count": len(used_refs),
            "records": inventory,
        },
        "overlay_summary": {
            "overlay_count": len(overlays),
            "interaction_stage_count": sum(stage_counts.values()),
            "stage_role_distribution": dict(sorted(stage_counts.items())),
            "unit04_capability_count": len(capabilities),
        },
        "overlays": overlays,
        "safety": {
            "ket99_authority_role_preserved": "NON_AUTHORITATIVE_TEACHER_DELIVERY_DIALOGUE_USAGE_EVIDENCE",
            "ket99_canonical_promotion_allowed": False,
            "private_normalized_transcripts_read": False,
            "raw_ket99_transcript_text_copied": False,
            "all_learner_language_resolves_to_existing_unit04_q07_via_m2a": True,
            "unit05_plus_grammar_leak_count": 0,
            "a2_plus_unlock_count": 0,
        },
    }
    _assert_no_forbidden_keys(result)
    result["projection_sha256"] = _sha(result)
    return result


def compact_readback(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": projection["task_id"],
        "status": projection["status"],
        "ket99_transcript_count": projection["ket99_evidence_inventory"]["transcript_count"],
        "stage_pool_counts": projection["ket99_evidence_inventory"]["stage_pool_counts"],
        "overlay_count": projection["overlay_summary"]["overlay_count"],
        "interaction_stage_count": projection["overlay_summary"]["interaction_stage_count"],
        "stage_role_distribution": projection["overlay_summary"]["stage_role_distribution"],
        "materialized_evidence_ref_count": projection["ket99_evidence_inventory"]["materialized_evidence_ref_count"],
        "raw_ket99_transcript_text_copied": projection["safety"]["raw_ket99_transcript_text_copied"],
        "a2_plus_unlock_count": projection["safety"]["a2_plus_unlock_count"],
        "projection_sha256": projection["projection_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    projection = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(args.repo_root)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("U04MS02B_KET99_READBACK=" + json.dumps(compact_readback(projection), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
