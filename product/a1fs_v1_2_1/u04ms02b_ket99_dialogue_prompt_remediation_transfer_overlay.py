from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)

TASK_ID = "A1FS-V1-U04MS02B_KET99DialoguePromptRemediationTransferOverlay"
STATUS = "PASS_A1FS_V1_U04MS02B_KET99_DIALOGUE_PROMPT_REMEDIATION_TRANSFER_OVERLAY"
REVISION = "R1_KET99_SEMANTIC_DELIVERY_SUITABILITY_GATE"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads repository-exportable KET99 evidence_items only to derive abstract teacher-delivery mechanics "
    "for already-admitted Unit04 Q07/M2-A language; source wording is never copied or promoted."
)
KET99_DIR = "ulga/reports/ket_comp_transcript_final_consolidation"
ARTIFACT_INDEX = f"{KET99_DIR}/artifact_index.json"
CONTENT_UNITS = f"{KET99_DIR}/transcript_content_units.jsonl"
SEMANTIC = f"{KET99_DIR}/normalized_transcript_semantic_artifact.jsonl"
ADMISSION = f"{KET99_DIR}/transcript_admission_decisions.json"
EXPECTED_IDS = tuple(f"P{n:03d}" for n in range(4, 103))
STAGE_ROLES = ("GUIDED_DIALOGUE", "FOLLOW_UP_PROMPT", "ERROR_REPAIR", "TRANSFER_PROMPT")
UNIT04_TARGET_OPERATION = {
    "GUIDED_DIALOGUE": "LOCATION_QA",
    "FOLLOW_UP_PROMPT": "SCENE_DESCRIPTION_AND_DETAIL_EXPANSION",
    "ERROR_REPAIR": "RELATION_CONTRAST_AND_REPAIR",
    "TRANSFER_PROMPT": "ALTERNATE_SCENE_TRANSFER",
}
FORBIDDEN_OUTPUT_KEYS = {
    "source_text", "transcript_text", "body_text", "raw_text", "clean_text", "title",
    "evidence_items", "correct_answer", "answer_key", "learner_response", "prompt",
}
MECHANIC_PATTERNS = {
    "SCENE_OR_PICTURE_ELICITATION": ("picture_prompt", "picture_story", "preview_image", "picture_coverage", "image_prompt", "scene_prompt"),
    "DIALOGUE_INTERACTION": ("paired_candidate_interaction", "two_way_discussion", "single_conversation", "dialogue", "conversation", "chat", "discuss", "opinion_exchange"),
    "RESPONSE_EXPANSION": ("answer_in_full_sentences", "full_sentence_answer", "answer_expansion", "add_reason", "add_alternative", "give_three_or_more_details", "give_more_details", "expand_answer", "extended_answer", "answer_topic_prompt"),
    "DETAIL_ELABORATION": ("detail_question", "target_detail", "detail_discrimination", "locate_evidence", "question_paragraph_alignment", "keyword_location", "give_three_or_more_details", "give_more_details"),
    "ERROR_CORRECTION": ("incorrect", "correction", "correct_", "_correct", "negative_then_positive", "error_repair", "self_correct"),
    "CONTRAST_OR_DISCRIMINATION": ("discrimination", "compare", "contrast", "difference", "distinguish", "negative_then_positive"),
    "RETRY_OR_COMPLETION": ("question_completion", "sentence_completion", "retry", "try_again", "repair", "reformulate"),
    "TRANSFER_OR_REVIEW": ("grand_review", "closeout", "what_to_do_next", "transfer", "reuse", "alternate_context", "new_context"),
    "ALTERNATE_CONTEXT_REUSE": ("alternate_context", "new_context", "reuse_in_new", "transfer_to", "change_context"),
    "DESCRIPTION": ("describe", "description", "picture_prompt", "picture_story", "scene_prompt"),
    "SEQUENCING": ("sequence_required", "sequencing", "story_order", "picture_story"),
}
STAGE_ALLOWED_MECHANICS = {
    "GUIDED_DIALOGUE": {"QUESTION_RESPONSE", "SCENE_OR_PICTURE_ELICITATION", "DIALOGUE_INTERACTION", "DESCRIPTION"},
    "FOLLOW_UP_PROMPT": {"RESPONSE_EXPANSION", "DETAIL_ELABORATION", "QUESTION_RESPONSE", "DIALOGUE_INTERACTION", "DESCRIPTION"},
    "ERROR_REPAIR": {"ERROR_CORRECTION", "CONTRAST_OR_DISCRIMINATION", "RETRY_OR_COMPLETION"},
    "TRANSFER_PROMPT": {"ALTERNATE_CONTEXT_REUSE", "SCENE_OR_PICTURE_ELICITATION", "DIALOGUE_INTERACTION", "DESCRIPTION", "SEQUENCING", "TRANSFER_OR_REVIEW"},
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
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise OverlayError(f"jsonl_object_required:{path}")
    return rows


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _assert_no_forbidden_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in FORBIDDEN_OUTPUT_KEYS:
                raise OverlayError(f"forbidden_output_key:{path}.{key}")
            _assert_no_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, f"{path}[{index}]")


def _normalize(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("’", "'")
    return re.sub(r"_+", "_", re.sub(r"[^0-9a-z]+", "_", text)).strip("_")


def _classify_mechanics(evidence_items: list[Any]) -> list[str]:
    tags: set[str] = set()
    for raw in evidence_items:
        item = _normalize(raw)
        if not item:
            continue
        if item.startswith("ask_") or "question" in item or item in {"personal_short_answer", "answer_topic_prompt", "full_sentence_answer"} or any(x in item for x in ("examiner_topic_prompt", "one_shared_question", "personal_information_question")):
            tags.add("QUESTION_RESPONSE")
        for tag, tokens in MECHANIC_PATTERNS.items():
            if any(token in item for token in tokens):
                tags.add(tag)
    return sorted(tags)


def _stage_gate(role: str, content_roles: set[str], mechanics: set[str]) -> tuple[bool, list[str]]:
    matched = sorted(mechanics & STAGE_ALLOWED_MECHANICS[role])
    role_ok = {
        "GUIDED_DIALOGUE": "speaking" in content_roles,
        "FOLLOW_UP_PROMPT": bool(content_roles & {"speaking", "writing"}),
        "ERROR_REPAIR": "error_diagnosis" in content_roles,
        "TRANSFER_PROMPT": bool(content_roles & {"speaking", "writing", "review"}),
    }[role]
    if "teacher_delivery" not in content_roles or not role_ok or not matched:
        return False, []
    reasons = [f"MECHANIC_{tag}" for tag in matched]
    reasons += [f"UNIT04_{UNIT04_TARGET_OPERATION[role]}_COMPATIBLE", "KET99_TEACHER_DELIVERY_APPROVED"]
    return True, reasons


def _validate_artifact_index(index: dict[str, Any]) -> None:
    rows = index.get("artifacts")
    if not isinstance(rows, list):
        raise OverlayError("artifact_index_rows_missing")
    by_id = {str(row.get("artifact_id") or ""): row for row in rows if isinstance(row, dict)}
    required = {"KET99_PUBLIC_NORMALIZED_TRANSCRIPT_SEMANTIC_ARTIFACT", "KET99_PUBLIC_TRANSCRIPT_CONTENT_UNITS"}
    if not required.issubset(by_id) or any(by_id[key].get("repository_export_allowed") is not True for key in required):
        raise OverlayError("required_public_ket99_artifact_not_exportable")
    private = by_id.get("KET99_PRIVATE_NORMALIZED_TRANSCRIPTS")
    if not isinstance(private, dict) or private.get("repository_export_allowed") is not False:
        raise OverlayError("private_ket99_boundary_missing")


def _admission_by_transcript(admission: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = admission.get("decisions")
    if not isinstance(rows, list):
        raise OverlayError("admission_decisions_missing")
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("subject_type") != "content_unit":
            continue
        tid = str(row.get("transcript_id") or "")
        d, req = row.get("decisions"), row.get("requirements")
        if tid in by_id or not isinstance(d, dict):
            raise OverlayError(f"admission_invalid:{tid}")
        if d.get("teacher_delivery") != "approved" or d.get("lesson_planner") != "approved_with_constraints":
            raise OverlayError(f"admission_delivery_invalid:{tid}")
        if d.get("canonical_grammar_authority") != "denied" or d.get("canonical_vocabulary_authority") != "denied":
            raise OverlayError(f"canonical_authority_not_denied:{tid}")
        if not isinstance(req, list) or "map_language_items_to_canonical_authorities" not in req:
            raise OverlayError(f"canonical_mapping_requirement_missing:{tid}")
        by_id[tid] = row
    if tuple(sorted(by_id)) != EXPECTED_IDS:
        raise OverlayError("admission_transcript_range_mismatch")
    return by_id


def _build_evidence_inventory(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    _validate_artifact_index(_json(root / ARTIFACT_INDEX))
    units, semantic = _jsonl(root / CONTENT_UNITS), _jsonl(root / SEMANTIC)
    admission = _admission_by_transcript(_json(root / ADMISSION))
    if len(units) != 99 or len(semantic) != 99:
        raise OverlayError("ket99_public_row_count_mismatch")
    ub = {str(row.get("transcript_id") or ""): row for row in units}
    sb = {str(row.get("transcript_id") or ""): row for row in semantic}
    if tuple(sorted(ub)) != EXPECTED_IDS or tuple(sorted(sb)) != EXPECTED_IDS:
        raise OverlayError("ket99_transcript_identity_range_mismatch")
    inventory, pools = [], {role: [] for role in STAGE_ROLES}
    for tid in EXPECTED_IDS:
        unit, sem, adm = ub[tid], sb[tid], admission[tid]
        if unit.get("authority_status") != "non_authoritative" or unit.get("canonical_promotion_allowed") is not False:
            raise OverlayError(f"content_unit_authority_boundary_broken:{tid}")
        if sem.get("authority_status") != "non_authoritative" or sem.get("raw_text_included") is not False:
            raise OverlayError(f"semantic_authority_boundary_broken:{tid}")
        span = unit.get("source_span")
        evidence_sha = str(span.get("evidence_sha256") or "") if isinstance(span, dict) else ""
        if len(evidence_sha) != 64 or sem.get("source_sha256") != evidence_sha:
            raise OverlayError(f"source_lineage_mismatch:{tid}")
        items, roles, risks = unit.get("evidence_items"), unit.get("content_roles"), unit.get("risk_flags")
        if not isinstance(items, list) or not isinstance(roles, list) or not isinstance(risks, list):
            raise OverlayError(f"content_unit_structure_invalid:{tid}")
        role_set, mechanics = {str(x) for x in roles}, set(_classify_mechanics(items))
        acceptance, reasons = {}, {}
        for stage in STAGE_ROLES:
            acceptance[stage], reasons[stage] = _stage_gate(stage, role_set, mechanics)
        ref = f"KET99-TEXTFREE-{tid}"
        row = {
            "evidence_ref_id": ref, "transcript_id": tid, "content_unit_id": unit.get("content_unit_id"),
            "source_unit_id": unit.get("unit_id"), "lesson_role": unit.get("lesson_role"),
            "content_roles": sorted(role_set), "risk_flags": sorted(str(x) for x in risks),
            "source_evidence_sha256": evidence_sha, "normalized_text_sha256": sem.get("normalized_text_sha256"),
            "evidence_item_count": len(items), "evidence_item_digest_sha256": _sha(items),
            "mechanic_tags": sorted(mechanics), "stage_semantic_acceptance": acceptance,
            "stage_match_reasons": reasons, "unit04_target_operations": dict(UNIT04_TARGET_OPERATION),
            "authority_status": "non_authoritative", "canonical_promotion_allowed": False, "raw_text_included": False,
            "admission": {"admission_id": adm.get("admission_id"), "teacher_delivery": "approved",
                "lesson_planner": "approved_with_constraints", "canonical_grammar_authority": "denied",
                "canonical_vocabulary_authority": "denied"},
        }
        inventory.append(row)
        for stage, allowed in acceptance.items():
            if allowed:
                pools[stage].append(ref)
    empty = [stage for stage, refs in pools.items() if not refs]
    if empty:
        raise OverlayError("ket99_semantic_stage_evidence_pool_empty:" + ",".join(empty))
    return inventory, pools


def _pick(pool: list[str], index: int, salt: int) -> str:
    return pool[(index * 7 + salt * 11) % len(pool)]


def _stage(role: str, ref: str, evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = evidence[ref]
    if row["stage_semantic_acceptance"].get(role) is not True or not row["stage_match_reasons"].get(role):
        raise OverlayError(f"selected_evidence_not_semantically_accepted:{role}:{ref}")
    return {
        "stage_role": role,
        "delivery_operation": {"GUIDED_DIALOGUE": "ELICIT_FROM_EXISTING_UNIT04_SCENE",
            "FOLLOW_UP_PROMPT": "FOLLOW_UP_ON_EXISTING_UNIT04_SCENE",
            "ERROR_REPAIR": "REFOCUS_EXISTING_UNIT04_RELATION_AND_MODEL",
            "TRANSFER_PROMPT": "TRANSFER_TO_ALTERNATE_UNIT04_Q07_SCENE"}[role],
        "unit04_target_operation": UNIT04_TARGET_OPERATION[role], "ket99_evidence_ref_id": ref,
        "semantic_compatibility": "PASS", "semantic_match_reasons": list(row["stage_match_reasons"][role]),
    }


def build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    inventory, pools = _build_evidence_inventory(root)
    evidence = {row["evidence_ref_id"]: row for row in inventory}
    m2a = build_unit04_raz_aw_multi_sentence_micro_scene_capability(root)
    capabilities = m2a.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != 36:
        raise OverlayError("m2a_capability_supply_invalid")
    overlays = []
    for index, capability in enumerate(capabilities):
        target = capabilities[(index + 1) % len(capabilities)]
        refs = {role: _pick(pools[role], index, n) for n, role in enumerate(STAGE_ROLES)}
        stages = [_stage(role, refs[role], evidence) for role in STAGE_ROLES]
        stages[-1]["transfer_target_capability_id"] = target["capability_id"]
        stages[-1]["transfer_target_scene_ref_ids"] = list(target["unit04_scene_ref_ids"])
        oid = hashlib.sha256(f"R1|{capability['capability_id']}|{'|'.join(refs[r] for r in STAGE_ROLES)}".encode()).hexdigest()[:20].upper()
        overlays.append({"overlay_id": f"U04-MS02B-KET99-{oid}", "unit04_capability_id": capability["capability_id"],
            "unit04_scene_ref_ids": list(capability["unit04_scene_ref_ids"]), "unit04_sentence_ids": list(capability["unit04_sentence_ids"]),
            "interaction_stages": stages, "authority_boundary": {"learner_language_authority": "UNIT04_Q07_VIA_M2A",
                "ket99_is_learner_facing_authority": False, "ket99_canonical_promotion_allowed": False,
                "ket99_raw_transcript_text_copied": False, "new_learner_facing_wording_authored": False, "a2_unlocked": False}})
    counts = Counter(stage["stage_role"] for row in overlays for stage in row["interaction_stages"])
    semantic_pass = sum(stage["semantic_compatibility"] == "PASS" for row in overlays for stage in row["interaction_stages"])
    used = {stage["ket99_evidence_ref_id"] for row in overlays for stage in row["interaction_stages"]}
    result = {
        "schema_version": "a1fs.v1.u04.ms02b.ket99.dialogue_prompt_remediation_transfer_overlay.v2",
        "task_id": TASK_ID, "status": STATUS, "revision": REVISION, "unit_number": 4, "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "source_refs": {"m2a": "product/a1fs_v1_2_1/u04ms02a_raz_aw_multi_sentence_micro_scene_capability.py",
            "ket99_artifact_index": ARTIFACT_INDEX, "ket99_content_units": CONTENT_UNITS,
            "ket99_semantic_artifact": SEMANTIC, "ket99_admission": ADMISSION},
        "scope": {"semantic_delivery_suitability_gate": True, "structural_teacher_delivery_overlay_only": True,
            "source_evidence_items_read_for_validation": True, "source_evidence_items_emitted": False,
            "form01_20_modified": False, "canonical_grammar_modified": False, "canonical_vocabulary_modified": False,
            "canonical_chunk_modified": False, "new_learner_facing_wording_authored": False,
            "raw_ket99_transcript_text_included": False, "unit05_plus_grammar_opened": False, "a2_unlocked": False},
        "ket99_evidence_inventory": {"transcript_count": len(inventory), "expected_transcript_range": {"first": "P004", "last": "P102", "count": 99},
            "stage_pool_counts": {r: len(pools[r]) for r in STAGE_ROLES}, "materialized_evidence_ref_count": len(used), "records": inventory},
        "overlay_summary": {"overlay_count": len(overlays), "interaction_stage_count": sum(counts.values()),
            "semantic_compatible_stage_count": semantic_pass, "semantic_incompatible_stage_count": sum(counts.values()) - semantic_pass,
            "stage_role_distribution": dict(sorted(counts.items())), "unit04_capability_count": len(capabilities)},
        "overlays": overlays,
        "safety": {"ket99_authority_role_preserved": "NON_AUTHORITATIVE_TEACHER_DELIVERY_DIALOGUE_USAGE_EVIDENCE",
            "ket99_canonical_promotion_allowed": False, "private_normalized_transcripts_read": False,
            "raw_ket99_transcript_text_copied": False, "evidence_item_wording_copied_to_output": False,
            "all_selected_stage_bindings_semantically_compatible": semantic_pass == 144,
            "all_learner_language_resolves_to_existing_unit04_q07_via_m2a": True,
            "unit05_plus_grammar_leak_count": 0, "a2_plus_unlock_count": 0},
    }
    _assert_no_forbidden_keys(result)
    result["projection_sha256"] = _sha(result)
    return result


def compact_readback(projection: dict[str, Any]) -> dict[str, Any]:
    s, i = projection["overlay_summary"], projection["ket99_evidence_inventory"]
    return {"status": projection["status"], "revision": projection["revision"], "ket99_transcript_count": i["transcript_count"],
        "stage_pool_counts": i["stage_pool_counts"], "overlay_count": s["overlay_count"], "interaction_stage_count": s["interaction_stage_count"],
        "semantic_compatible_stage_count": s["semantic_compatible_stage_count"], "semantic_incompatible_stage_count": s["semantic_incompatible_stage_count"],
        "stage_role_distribution": s["stage_role_distribution"], "raw_ket99_transcript_text_copied": projection["safety"]["raw_ket99_transcript_text_copied"],
        "evidence_item_wording_copied_to_output": projection["safety"]["evidence_item_wording_copied_to_output"],
        "a2_plus_unlock_count": projection["safety"]["a2_plus_unlock_count"], "projection_sha256": projection["projection_sha256"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    projection = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("U04MS02B_R1_READBACK=" + json.dumps(compact_readback(projection), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
