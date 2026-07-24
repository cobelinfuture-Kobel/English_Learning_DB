#!/usr/bin/env python3
"""Author four selected KET99 Reading teacher-delivery/remediation bundles."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_evidence_reference_learning_value_evaluation as m4b
from ulga.builders import build_ket99_pku_teacher_delivery_remediation_asset_intake as m4a
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "KET99-PK-M4C_SelectedReadingTeacherDeliveryAndRemediationAssetAuthoring"
SCHEMA_VERSION = "ket99.pku.selected_reading_teacher_delivery_remediation_assets.v1"
PASS_STATUS = "PASS_KET99_PK_M4C_SELECTED_READING_TEACHER_DELIVERY_REMEDIATION_ASSETS_READY"
NEXT_SHORT_STEP = "A1FS-V1_MainlineResumeAfterKET99OptionalOverlayFreeze"
DEFAULT_M4A = ROOT / ".local/a1fs_v1/ket99_pku_m4a/teacher_delivery_remediation_asset_intake.safe.json"
DEFAULT_M4B = ROOT / ".local/a1fs_v1/ket99_pku_m4b/evidence_reference_learning_value_evaluation.safe.json"
DEFAULT_OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4c/selected_reading_teacher_delivery_remediation_assets.safe.json"
FORBIDDEN_KEYS = {"payload", "source_content", "source_text", "text", "prompt", "correct_answer", "answer_key", "learner_response", "transcript_text", "audio_bytes", "recording"}

PLACEMENT_POLICY: dict[str, dict[str, str]] = {
    "KET99-P008-PKU02": {"KETR-RB-00-L01": "INTRO_SCAFFOLD", "KETR-RB-00-L02": "GUIDED_PRACTICE", "KETR-RB-01-L01": "TRANSFER_FADE"},
    "KET99-P008-PKU03": {"KETR-RB-00-L01": "FOCUS_MODEL", "KETR-RB-00-L02": "GUIDED_EVIDENCE_PRACTICE", "KETR-RB-01-L01": "INDEPENDENT_TRANSFER"},
    "KET99-P008-PKU04": {"KETR-RB-00-L01": "FOCUS_CONTRAST", "KETR-RB-00-L02": "GUIDED_MEANING_MATCH", "KETR-RB-01-L01": "INDEPENDENT_TRANSFER"},
    "KET99-P008-PKU05": {"KETR-RB-00-L01": "DIAGNOSTIC_CONTRAST", "KETR-RB-00-L02": "ERROR_TRIGGERED_REMEDIATION"},
}

ASSET_DEFINITIONS: dict[str, dict[str, Any]] = {
    "KET99-P008-PKU02": {
        "asset_id": "KET99-RDG-TD-KEYWORD-CONTROL-V1",
        "concept_id": "READING.UNDERLINE_QUESTION_KEYWORDS",
        "title": "Decisive-question-feature scaffold",
        "lanes": ["TEACHER_DELIVERY"],
        "teacher_delivery": {
            "objective": "Identify the smallest question features that control the answer before reading.",
            "teacher_steps": [
                "Ask the learner to mark the actor, polarity, relationship and action-or-state requirement.",
                "Require the learner to restate the information target in plain meaning.",
                "Model the difference between a topic word and a decision-controlling feature.",
                "Require source evidence before accepting an answer selected from keyword overlap.",
            ],
            "learner_protocol": [
                "Mark who or what the question is about.",
                "Mark negative, relationship, possession, ability or preference features when present.",
                "State what evidence would count before searching the passage.",
                "Check the chosen answer against the complete question meaning.",
            ],
            "scaffold_and_fade": {"initial": "Mark all decisive features with teacher modelling.", "guided": "Mark only the actor and one decisive contrast.", "transfer": "State the target mentally and cite evidence without visible marking."},
            "success_observation": "The learner searches for the complete information target rather than isolated repeated words.",
        },
        "remediation": None,
    },
    "KET99-P008-PKU03": {
        "asset_id": "KET99-RDG-TD-EVIDENCE-ELIMINATION-V1",
        "concept_id": "READING.LOCATE_AND_ELIMINATE_WITH_EVIDENCE",
        "title": "Evidence-location and option-elimination routine",
        "lanes": ["TEACHER_DELIVERY", "REMEDIATION"],
        "teacher_delivery": {
            "objective": "Choose an answer only after locating supporting or excluding evidence.",
            "teacher_steps": ["Create a supports, contradicts, or not-stated evidence check.", "Require one source span for the selected answer.", "Require a short reason for excluding each plausible distractor.", "Delay final choice until the relevant candidates have been checked."],
            "learner_protocol": ["Locate the relevant sentence or phrase.", "Label each plausible candidate as supports, contradicts, or not stated.", "Select the answer with direct support.", "Recheck that the evidence belongs to the target person or thing."],
            "scaffold_and_fade": {"initial": "Use a visible evidence table for all candidates.", "guided": "Write evidence only for the answer and strongest distractor.", "transfer": "Cite the decisive evidence orally or in a short response."},
            "success_observation": "The learner can cite evidence and explain why a tempting distractor fails.",
        },
        "remediation": {
            "trigger_signatures": ["FIRST_MENTION_BIAS", "KEYWORD_OVERLAP_WITHOUT_EVIDENCE", "DISTRACTOR_NOT_EXPLICITLY_ELIMINATED", "EVIDENCE_FROM_WRONG_ENTITY"],
            "repair_steps": ["Return to the question target.", "Mark the evidence owner and the stated relation.", "Compare the best answer with the strongest distractor.", "Retry with a new short passage using the same evidence table."],
            "reassessment_observation": "The learner independently cites a decisive source span and rejects the strongest distractor.",
        },
    },
    "KET99-P008-PKU04": {
        "asset_id": "KET99-RDG-TD-PARAPHRASE-MATCH-V1",
        "concept_id": "READING.MATCH_PARAPHRASED_MEANING",
        "title": "Paraphrased-meaning matching routine",
        "lanes": ["TEACHER_DELIVERY", "REMEDIATION"],
        "teacher_delivery": {
            "objective": "Match equivalent meanings when the question and passage use different wording.",
            "teacher_steps": ["Separate actor, action-or-state, object, time, place and reference.", "Compare meaning components instead of requiring identical vocabulary.", "Model one equivalent pair and one near-match that changes a decisive component.", "Require the learner to name the preserved meaning components."],
            "learner_protocol": ["Identify the core meaning in the question.", "Find a sentence that preserves the same actor and event or state.", "Check that reference words point to the intended person, place or thing.", "Reject wording that shares vocabulary but changes meaning."],
            "scaffold_and_fade": {"initial": "Use a component grid for actor, action, object and reference.", "guided": "Compare only the changed wording and decisive component.", "transfer": "Explain the equivalence without a visible grid."},
            "success_observation": "The learner accepts genuine meaning equivalence and rejects lexical overlap with changed meaning.",
        },
        "remediation": {
            "trigger_signatures": ["EXACT_WORDING_REQUIRED", "LEXICAL_OVERLAP_FALSE_MATCH", "REFERENCE_RESOLUTION_FAILURE", "DECISIVE_MEANING_COMPONENT_CHANGED"],
            "repair_steps": ["Rewrite both statements as actor plus action-or-state plus object.", "Circle the component that differs.", "Decide whether the difference preserves or changes the answer.", "Retry with a new paraphrase pair."],
            "reassessment_observation": "The learner identifies equivalent meaning without relying on identical wording.",
        },
    },
    "KET99-P008-PKU05": {
        "asset_id": "KET99-RDG-RM-DETAIL-RELATIONSHIP-V1",
        "concept_id": "READING.ERROR_DETAIL_RELATIONSHIP_CONFUSION",
        "title": "Detail-owner and relationship-confusion repair",
        "lanes": ["REMEDIATION"],
        "teacher_delivery": None,
        "remediation": {
            "objective": "Repair answers caused by assigning a detail to the wrong person, owner or relation.",
            "trigger_signatures": ["SPEAKER_VS_FRIEND_CONFUSION", "OWNER_VS_WANTED_OBJECT_CONFUSION", "ABILITY_VS_PREFERENCE_CONFUSION", "EXACT_AGE_VS_APPROXIMATE_AGE_CONFUSION", "RELATIONSHIP_DIRECTION_CONFUSION"],
            "diagnostic_frame": ["Who owns or performs the detail?", "What action, state or relation is actually stated?", "Is the detail present, wanted, absent or attributed to another person?", "Does the evidence satisfy every part of the question?"],
            "repair_steps": ["Write the evidence as subject, relation-or-action, and object.", "Contrast the learner choice with the correct evidence owner.", "Name the changed relation that made the first answer wrong.", "Retry on a new item with a different relationship pattern."],
            "reassessment_observation": "The learner assigns each detail to the correct entity and relation before selecting an answer.",
        },
    },
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _verify_signed(value: Mapping[str, Any], code: str) -> None:
    unsigned = dict(value)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != digest(unsigned):
        raise ValueError(f"{code}_artifact_sha256_invalid")


def walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise ValueError(f"private_content_key_forbidden:{path}.{key}")
            walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_forbidden(child, f"{path}[{index}]")


def verify_inputs(m4a_value: Mapping[str, Any], m4b_value: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[tuple[str, str], Mapping[str, Any]]]:
    if (m4a_value.get("task_id"), m4a_value.get("schema_version"), m4a_value.get("validation_status"), m4a_value.get("errors"), m4a_value.get("stop_reason")) != (m4a.TASK_ID, m4a.SCHEMA_VERSION, m4a.PASS_STATUS, [], "NONE"):
        raise ValueError("m4a_contract_invalid")
    _verify_signed(m4a_value, "m4a")
    if (m4b_value.get("task_id"), m4b_value.get("schema_version"), m4b_value.get("validation_status"), m4b_value.get("errors"), m4b_value.get("stop_reason")) != (m4b.TASK_ID, m4b.SCHEMA_VERSION, m4b.PASS_STATUS, [], "NONE"):
        raise ValueError("m4b_contract_invalid")
    _verify_signed(m4b_value, "m4b")
    if m4b_value.get("source_identity", {}).get("m4a_intake_sha256") != digest(m4a_value):
        raise ValueError("m4b_m4a_binding_invalid")
    if m4b_value.get("evaluation_policy", {}).get("activation_allowed") is not False:
        raise ValueError("m4b_activation_policy_invalid")
    candidates = {str(row.get("asset_candidate_id") or ""): row for row in m4a_value.get("asset_candidates", []) if isinstance(row, Mapping) and str(row.get("asset_candidate_id") or "")}
    selected: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in m4b_value.get("binding_evaluations", []):
        if not isinstance(row, Mapping):
            raise ValueError("m4b_binding_row_invalid")
        pku_id, lesson_id = str(row.get("pku_id") or ""), str(row.get("lesson_id") or "")
        if pku_id not in PLACEMENT_POLICY or lesson_id not in PLACEMENT_POLICY[pku_id]:
            continue
        if row.get("binding_decision") != "RETAIN_FOR_ASSET_AUTHORING_EVALUATION":
            raise ValueError(f"selected_binding_not_authoring_eligible:{pku_id}:{lesson_id}")
        if row.get("learning_value_priority") not in {"MEDIUM", "HIGH"} or int(row.get("raw_incremental_value_score") or 0) < 4:
            raise ValueError(f"selected_binding_value_invalid:{pku_id}:{lesson_id}")
        candidate_id = str(row.get("asset_candidate_id") or "")
        candidate = candidates.get(candidate_id)
        if candidate is None:
            raise ValueError(f"selected_binding_candidate_missing:{candidate_id}")
        if (candidate.get("pku_id"), candidate.get("lesson_id"), candidate.get("skill"), candidate.get("level"), candidate.get("source_transcript_id"), int(candidate.get("textbook_page") or 0), candidate.get("lesson_role")) != (pku_id, lesson_id, "READING", "A1+", "P008", 12, "regular"):
            raise ValueError(f"selected_binding_source_boundary_invalid:{pku_id}:{lesson_id}")
        key = (pku_id, lesson_id)
        if key in selected:
            raise ValueError(f"selected_binding_duplicate:{pku_id}:{lesson_id}")
        selected[key] = row
    expected = {(pku_id, lesson_id) for pku_id, lessons in PLACEMENT_POLICY.items() for lesson_id in lessons}
    if set(selected) != expected:
        raise ValueError(f"selected_binding_set_mismatch:missing={sorted(expected-set(selected))}:extra={sorted(set(selected)-expected)}")
    walk_forbidden(m4a_value)
    walk_forbidden(m4b_value)
    return candidates, selected


def _bundle(pku_id: str, definition: Mapping[str, Any], candidates: Mapping[str, Mapping[str, Any]], bindings: Mapping[tuple[str, str], Mapping[str, Any]]) -> dict[str, Any]:
    placements, anchors, lineages = [], set(), []
    for lesson_id, role in sorted(PLACEMENT_POLICY[pku_id].items()):
        binding = bindings[(pku_id, lesson_id)]
        candidate = candidates[str(binding["asset_candidate_id"])]
        anchors.update(str(v) for v in candidate.get("evidence_anchor_ids", []) if str(v))
        lineages.append(candidate.get("source_lineage", {}))
        placements.append({
            "asset_candidate_id": binding["asset_candidate_id"], "lesson_id": lesson_id,
            "lesson_node_id": candidate.get("lesson_node_id"), "skill": "READING", "level": "A1+",
            "instructional_role": role, "binding_decision": binding.get("binding_decision"),
            "learning_value_priority": binding.get("learning_value_priority"),
            "raw_incremental_value_score": binding.get("raw_incremental_value_score"),
            "evaluation_reasons": binding.get("evaluation_reasons", []),
            "material_digest": binding.get("material_profile", {}).get("material_digest"),
            "placement_status": "AUTHORING_APPROVED_NOT_ACTIVATED",
        })
    result = {
        "asset_id": definition["asset_id"], "pku_id": pku_id, "concept_id": definition["concept_id"],
        "title": definition["title"], "skill": "READING", "level": "A1+",
        "authority_status": "NON_AUTHORITATIVE_OPTIONAL_INSTRUCTIONAL_ASSET",
        "source_role": "THIRD_PARTY_PATTERN_REUSE_WITH_ORIGINAL_ABSTRACTION",
        "content_origin": "ORIGINAL_ABSTRACTED_PROCEDURE_NOT_TRANSCRIPT_TEXT",
        "recommended_lanes": definition["lanes"],
        "teacher_delivery_contract": definition["teacher_delivery"],
        "remediation_contract": definition["remediation"],
        "placements": placements,
        "source_evidence": {"source_transcript_ids": ["P008"], "textbook_pages": [12], "evidence_anchor_ids": sorted(anchors), "source_lineage_digests": sorted({digest(v) for v in lineages}), "verbatim_source_content_included": False},
        "consumer_policy": {"teacher_delivery_attachment_surface": "cp07d_delivery_contract.optional_teacher_delivery_assets", "remediation_attachment_surface": "remediation_assignments.support_asset_ids", "required_for_delivery": False, "composition_item": False, "learner_facing_allowed": False, "mastery_evidence_allowed": False, "production_activation_allowed": False, "a2_mapping_allowed": False, "private_canary_required_before_activation": True},
    }
    result["content_sha256"] = digest(result)
    return result


def build_artifact(m4a_value: Mapping[str, Any], m4b_value: Mapping[str, Any]) -> dict[str, Any]:
    candidates, bindings = verify_inputs(m4a_value, m4b_value)
    bundles = [_bundle(pku_id, ASSET_DEFINITIONS[pku_id], candidates, bindings) for pku_id in sorted(ASSET_DEFINITIONS)]
    placements = [placement for bundle in bundles for placement in bundle["placements"]]
    lesson_index: dict[str, list[str]] = {}
    for bundle in bundles:
        for placement in bundle["placements"]:
            lesson_index.setdefault(str(placement["lesson_id"]), []).append(str(bundle["asset_id"]))
    result = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": PASS_STATUS,
        "artifact_type": "selected_reading_teacher_delivery_and_remediation_assets", "scope": "A1_PLUS_READING_ONLY",
        "source_identity": {"m4a_intake_sha256": digest(m4a_value), "m4b_evaluation_sha256": digest(m4b_value)},
        "selection_contract": {"selected_pku_ids": sorted(ASSET_DEFINITIONS), "selected_binding_count": len(placements), "excluded_media_dependent_pku_count": 4, "excluded_writing_pku_count": 1, "selection_basis": "M4B_RETAINED_NON_MEDIA_READING_BINDINGS_PLUS_SOURCE_CONTENT_REVIEW", "verbatim_transcript_reuse_allowed": False, "instructional_pattern_reuse_allowed": True},
        "mainline_consumer_contracts": {
            "teacher_delivery": {"consumer_task_id": cp07d.TASK_ID, "consumer_schema_version": cp07d.SCHEMA_VERSION, "consumer_validation_status": cp07d.PASS_STATUS, "attachment_surface": "cp07d_delivery_contract.optional_teacher_delivery_assets", "activation_status": "READY_FOR_PRIVATE_CANARY_NOT_ACTIVATED"},
            "remediation": {"consumer_task_id": m7.TASK_ID, "consumer_schema_version": m7.SCHEMA_VERSION, "consumer_validation_status": m7.STATUS, "attachment_surface": "remediation_assignments.support_asset_ids", "activation_status": "READY_FOR_PRIVATE_CANARY_NOT_ACTIVATED"},
        },
        "asset_bundles": bundles,
        "lesson_asset_index": [{"lesson_id": lesson_id, "asset_ids": sorted(asset_ids), "asset_count": len(asset_ids), "runtime_activation_status": "NOT_ACTIVATED"} for lesson_id, asset_ids in sorted(lesson_index.items())],
        "counts": {"authored_asset_bundle_count": len(bundles), "authored_placement_count": len(placements), "referenced_lesson_count": len(lesson_index), "teacher_delivery_bundle_count": sum("TEACHER_DELIVERY" in b["recommended_lanes"] for b in bundles), "remediation_bundle_count": sum("REMEDIATION" in b["recommended_lanes"] for b in bundles), "teacher_delivery_activated_count": 0, "remediation_activated_count": 0, "learner_facing_asset_count": 0, "composition_item_delta": 0, "lesson_selection_delta": 0, "mastery_evidence_delta": 0, "canonical_coverage_delta": 0, "private_text_exposure_count": 0},
        "claim_boundaries": {"source_content_review_completed": True, "pedagogical_effectiveness_proven": False, "runtime_activation_completed": False, "composition_items_modified": False, "lesson_selection_modified": False, "canonical_graph_modified": False, "mastery_denominator_modified": False, "learner_facing_content_created": False, "a2_unlocked": False},
        "errors": [], "stop_reason": "NONE", "next_short_step": NEXT_SHORT_STEP,
    }
    result["artifact_sha256"] = digest(result)
    walk_forbidden(result)
    return result


def assets_for_lesson(artifact: Mapping[str, Any], lesson_id: str) -> list[dict[str, Any]]:
    if artifact.get("validation_status") != PASS_STATUS:
        raise ValueError("m4c_artifact_status_invalid")
    selected_ids = {asset_id for row in artifact.get("lesson_asset_index", []) if row.get("lesson_id") == lesson_id for asset_id in row.get("asset_ids", [])}
    return [dict(bundle) for bundle in artifact.get("asset_bundles", []) if bundle.get("asset_id") in selected_ids]


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4a-intake", type=Path, default=DEFAULT_M4A)
    parser.add_argument("--m4b-evaluation", type=Path, default=DEFAULT_M4B)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.m4a_intake), read_json(args.m4b_evaluation))
    write(args.output, artifact)
    print(json.dumps(artifact["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
