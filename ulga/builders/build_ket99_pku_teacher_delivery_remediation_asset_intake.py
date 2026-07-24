#!/usr/bin/env python3
"""Register M4 KET99 references for teacher-delivery and remediation evaluation.

This is a metadata-only mainline intake contract. It binds every admitted M4
optional reference to the existing CP07D teacher-delivery surface and M7
remediation surface, but it does not decide learning value, create content,
activate delivery, alter composition, write learner evidence, change mastery,
or unlock A2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_controlled_pilot_overlay_admission as m4
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7

ROOT = Path(__file__).resolve().parents[2]
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Metadata-only intake over validated M4 optional references. No transcript "
    "text, teacher script, remediation content, learner-facing payload, lesson "
    "selection, composition item, mastery evidence, media, or A2 payload is created."
)
TASK_ID = "KET99-PK-M4A_TeacherDeliveryAndRemediationAssetMainlineIntake"
SCHEMA_VERSION = "ket99.pku.teacher_delivery_remediation_asset_intake.v1"
PASS_STATUS = "PASS_KET99_PK_M4A_TEACHER_DELIVERY_REMEDIATION_ASSET_MAINLINE_INTAKE_READY"
NEXT_SHORT_STEP = "KET99-PK-M4B_EvidenceReferenceLearningValueEvaluation"
COVERAGE_SCHEMA = "ket99.pku.controlled_pilot_overlay_coverage_readback.v1"

M4_OVERLAY = ROOT / ".local/a1fs_v1/ket99_pku_m4/controlled_pilot_overlay_admission.safe.json"
M4_COVERAGE = ROOT / ".local/a1fs_v1/ket99_pku_m4/coverage_readback.safe.json"
OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4a/teacher_delivery_remediation_asset_intake.safe.json"

FORBIDDEN_KEYS = {
    "payload",
    "source_content",
    "source_text",
    "text",
    "prompt",
    "correct_answer",
    "answer_key",
    "learner_response",
    "transcript_text",
    "audio_bytes",
    "recording",
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


def walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise ValueError(f"private_content_key_forbidden:{path}.{key}")
            walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_forbidden(child, f"{path}[{index}]")


def _verify_signed(value: Mapping[str, Any], code: str) -> None:
    unsigned = dict(value)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != digest(unsigned):
        raise ValueError(f"{code}_artifact_sha256_invalid")


def verify_inputs(overlay: Mapping[str, Any], coverage: Mapping[str, Any]) -> None:
    if (
        overlay.get("task_id") != m4.TASK_ID
        or overlay.get("schema_version") != m4.SCHEMA_VERSION
        or overlay.get("validation_status") != m4.PASS_STATUS
        or overlay.get("errors") != []
        or overlay.get("stop_reason") != "NONE"
    ):
        raise ValueError("m4_overlay_contract_invalid")
    _verify_signed(overlay, "m4_overlay")
    policy = overlay.get("admission_policy", {})
    for key in (
        "hard_lesson_selection_allowed",
        "production_mapping_allowed",
        "a2_mapping_allowed",
    ):
        if policy.get(key) is not False:
            raise ValueError(f"m4_overlay_boundary_invalid:{key}")
    boundaries = overlay.get("claim_boundaries", {})
    if (
        boundaries.get("hard_graph_modified") is not False
        or boundaries.get("canonical_denominator_modified") is not False
        or boundaries.get("mastery_denominator_modified") is not False
        or boundaries.get("a2_unlocked") is not False
    ):
        raise ValueError("m4_overlay_claim_boundary_invalid")

    if (
        coverage.get("task_id") != m4.TASK_ID
        or coverage.get("schema_version") != COVERAGE_SCHEMA
        or coverage.get("validation_status") != m4.PASS_STATUS
        or coverage.get("errors") != []
        or coverage.get("stop_reason") != "NONE"
    ):
        raise ValueError("m4_coverage_contract_invalid")
    _verify_signed(coverage, "m4_coverage")
    if coverage.get("source_identity", {}).get("m4_overlay_sha256") != digest(overlay):
        raise ValueError("m4_coverage_overlay_binding_invalid")
    counts = coverage.get("coverage_counts", {})
    if (
        counts.get("overlay_unique_new_coverage_count") != 0
        or counts.get("coverage_double_count") != 0
        or counts.get("canonical_graph_mutation_count") != 0
        or counts.get("canonical_denominator_mutation_count") != 0
    ):
        raise ValueError("m4_coverage_boundary_invalid")
    if coverage.get("claim_boundaries", {}).get("learner_effectiveness_claimed") is not False:
        raise ValueError("m4_learning_effectiveness_claim_invalid")

    lesson_rows = overlay.get("lesson_pilot_overlays")
    if not isinstance(lesson_rows, list) or not lesson_rows:
        raise ValueError("m4_lesson_overlay_rows_required")
    actual_reference_count = 0
    actual_referenced_lesson_count = 0
    for row in lesson_rows:
        if not isinstance(row, Mapping):
            raise ValueError("m4_lesson_overlay_row_invalid")
        references = row.get("optional_pilot_references")
        if not isinstance(references, list):
            raise ValueError("m4_optional_reference_list_required")
        if references:
            actual_referenced_lesson_count += 1
        actual_reference_count += len(references)
        for reference in references:
            if (
                not isinstance(reference, Mapping)
                or reference.get("admission_decision") != "PILOT_ADMITTED"
                or reference.get("runtime_effect")
                != "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY"
                or reference.get("hard_lesson_selection_allowed") is not False
                or reference.get("production_mapping_allowed") is not False
                or reference.get("repository_export_policy")
                != "METADATA_ONLY_NO_PRIVATE_TRANSCRIPT_BODY"
            ):
                raise ValueError("m4_optional_reference_boundary_invalid")
    summary = overlay.get("coverage_summary", {})
    if (
        summary.get("optional_reference_count") != actual_reference_count
        or summary.get("pilot_referenced_lesson_count") != actual_referenced_lesson_count
        or actual_reference_count <= 0
        or actual_referenced_lesson_count <= 0
    ):
        raise ValueError("m4_reference_count_semantics_invalid")
    if (
        counts.get("overlay_already_covered_count") != actual_referenced_lesson_count
        or counts.get("overlay_duplicate_only_count")
        != actual_reference_count - actual_referenced_lesson_count
    ):
        raise ValueError("m4_coverage_reference_count_semantics_invalid")
    walk_forbidden(overlay)
    walk_forbidden(coverage)


def _candidate_id(lesson_id: str, reference: Mapping[str, Any]) -> str:
    identity = {
        "lesson_id": lesson_id,
        "pku_id": str(reference.get("pku_id") or ""),
        "source_transcript_id": str(reference.get("source_transcript_id") or ""),
        "evidence_anchor_ids": sorted(
            str(value) for value in reference.get("evidence_anchor_ids", []) if str(value)
        ),
    }
    if not all((identity["lesson_id"], identity["pku_id"], identity["source_transcript_id"])):
        raise ValueError("asset_candidate_identity_incomplete")
    if not identity["evidence_anchor_ids"]:
        raise ValueError("asset_candidate_evidence_anchor_missing")
    return f"KET99_TDR:{digest(identity)[:24]}"


def build_artifact(
    overlay: Mapping[str, Any], coverage: Mapping[str, Any]
) -> dict[str, Any]:
    verify_inputs(overlay, coverage)
    candidates: list[dict[str, Any]] = []
    lesson_intake: list[dict[str, Any]] = []
    for lesson in sorted(
        overlay["lesson_pilot_overlays"],
        key=lambda row: (str(row.get("skill") or ""), str(row.get("level") or ""), str(row.get("lesson_id") or "")),
    ):
        references = lesson.get("optional_pilot_references", [])
        if not references:
            continue
        lesson_id = str(lesson.get("lesson_id") or "")
        skill = str(lesson.get("skill") or "")
        level = str(lesson.get("level") or "")
        if not lesson_id or skill not in {"LISTENING", "SPEAKING", "READING", "WRITING"} or level not in {"A1", "A1+"}:
            raise ValueError("asset_intake_lesson_partition_invalid")
        candidate_ids: list[str] = []
        for reference in references:
            candidate_id = _candidate_id(lesson_id, reference)
            candidate_ids.append(candidate_id)
            candidates.append(
                {
                    "asset_candidate_id": candidate_id,
                    "lesson_id": lesson_id,
                    "lesson_node_id": str(lesson.get("lesson_node_id") or ""),
                    "skill": skill,
                    "level": level,
                    "pku_id": str(reference.get("pku_id") or ""),
                    "source_transcript_id": str(reference.get("source_transcript_id") or ""),
                    "source_unit_id": reference.get("source_unit_id"),
                    "textbook_page": reference.get("textbook_page"),
                    "lesson_role": reference.get("lesson_role"),
                    "mapping_class": reference.get("mapping_class"),
                    "authority_ids": sorted(
                        str(value) for value in reference.get("authority_ids", []) if str(value)
                    ),
                    "teaching_need_id": reference.get("teaching_need_id"),
                    "evidence_anchor_ids": sorted(
                        str(value) for value in reference.get("evidence_anchor_ids", []) if str(value)
                    ),
                    "resolution_anchor_sha256s": sorted(
                        str(value) for value in reference.get("resolution_anchor_sha256s", []) if str(value)
                    ),
                    "canonical_lesson_ids": [lesson_id],
                    "grammar_node_ids": sorted(
                        str(value) for value in reference.get("grammar_node_ids", []) if str(value)
                    ),
                    "vocabulary_chunk_pattern_ids": sorted(
                        str(value)
                        for value in reference.get("vocabulary_chunk_pattern_ids", [])
                        if str(value)
                    ),
                    "source_lineage": {
                        "m4_overlay_sha256": digest(overlay),
                        "m3_artifact_sha256": reference.get("m3_artifact_sha256"),
                        "r3g_artifact_sha256": reference.get("r3g_artifact_sha256"),
                        "cp07b_artifact_sha256": reference.get("cp07b_artifact_sha256"),
                        "m2_artifact_sha256": reference.get("m2_artifact_sha256"),
                    },
                    "candidate_lanes": {
                        "teacher_delivery": {
                            "consumer_task_id": cp07d.TASK_ID,
                            "consumer_schema_version": cp07d.SCHEMA_VERSION,
                            "intake_status": "EVALUATION_REQUIRED",
                            "activation_status": "NOT_ACTIVATED",
                            "intended_role": "OPTIONAL_TEACHER_DELIVERY_SUPPORT",
                        },
                        "remediation": {
                            "consumer_task_id": m7.TASK_ID,
                            "consumer_schema_version": m7.SCHEMA_VERSION,
                            "intake_status": "EVALUATION_REQUIRED",
                            "activation_status": "NOT_ACTIVATED",
                            "strategy_binding_status": "UNBOUND_PENDING_LEARNING_VALUE_EVALUATION",
                        },
                    },
                    "learning_value_evaluation_status": "NOT_EVALUATED",
                    "composition_item": False,
                    "required_for_delivery": False,
                    "learner_facing_allowed": False,
                    "mastery_evidence_allowed": False,
                    "production_activation_allowed": False,
                    "repository_export_policy": "METADATA_ONLY_NO_PRIVATE_TRANSCRIPT_BODY",
                }
            )
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"asset_candidate_id_duplicate_within_lesson:{lesson_id}")
        lesson_intake.append(
            {
                "lesson_id": lesson_id,
                "lesson_node_id": str(lesson.get("lesson_node_id") or ""),
                "skill": skill,
                "level": level,
                "asset_candidate_ids": sorted(candidate_ids),
                "asset_candidate_count": len(candidate_ids),
                "teacher_delivery_candidate_count": len(candidate_ids),
                "remediation_candidate_count": len(candidate_ids),
                "learning_value_evaluation_status": "NOT_EVALUATED",
                "runtime_activation_status": "NOT_ACTIVATED",
            }
        )
    if len(candidates) != len({row["asset_candidate_id"] for row in candidates}):
        raise ValueError("asset_candidate_id_duplicate")
    expected_reference_count = int(
        overlay.get("coverage_summary", {}).get("optional_reference_count") or 0
    )
    if len(candidates) != expected_reference_count:
        raise ValueError("asset_candidate_reference_count_mismatch")
    pku_ids = {str(row["pku_id"]) for row in candidates}
    result = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_teacher_delivery_remediation_asset_intake",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m4_overlay_sha256": digest(overlay),
            "m4_coverage_readback_sha256": digest(coverage),
        },
        "mainline_consumer_contracts": {
            "teacher_delivery": {
                "consumer_task_id": cp07d.TASK_ID,
                "consumer_schema_version": cp07d.SCHEMA_VERSION,
                "consumer_validation_status": cp07d.PASS_STATUS,
                "attachment_surface": "cp07d_delivery_contract.optional_teacher_delivery_assets",
                "activation_requires_learning_value_evaluation": True,
            },
            "remediation": {
                "consumer_task_id": m7.TASK_ID,
                "consumer_schema_version": m7.SCHEMA_VERSION,
                "consumer_validation_status": m7.STATUS,
                "attachment_surface": "remediation_assignments.support_asset_ids",
                "activation_requires_learning_value_evaluation": True,
            },
        },
        "intake_policy": {
            "learning_value_evaluation_required": True,
            "teacher_delivery_asset_activation_allowed": False,
            "remediation_asset_activation_allowed": False,
            "learner_facing_allowed": False,
            "required_delivery_asset_allowed": False,
            "mastery_evidence_allowed": False,
            "production_mapping_allowed": False,
            "a2_mapping_allowed": False,
        },
        "lesson_asset_intake": lesson_intake,
        "asset_candidates": sorted(candidates, key=lambda row: row["asset_candidate_id"]),
        "counts": {
            "source_optional_reference_count": len(candidates),
            "asset_candidate_count": len(candidates),
            "referenced_lesson_count": len(lesson_intake),
            "admitted_pku_count": len(pku_ids),
            "teacher_delivery_candidate_count": len(candidates),
            "remediation_candidate_count": len(candidates),
            "learning_value_evaluated_count": 0,
            "teacher_delivery_activated_count": 0,
            "remediation_activated_count": 0,
            "composition_item_delta": 0,
            "delivery_allowed_delta": 0,
            "mastery_evidence_delta": 0,
            "canonical_coverage_delta": 0,
            "private_text_exposure_count": 0,
        },
        "claim_boundaries": {
            "teacher_delivery_assets_created": False,
            "remediation_assets_created": False,
            "learning_value_evaluated": False,
            "runtime_activation_completed": False,
            "composition_items_modified": False,
            "lesson_selection_modified": False,
            "canonical_graph_modified": False,
            "mastery_denominator_modified": False,
            "learner_effectiveness_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    result["artifact_sha256"] = digest(result)
    walk_forbidden(result)
    return result


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4-overlay", type=Path, default=M4_OVERLAY)
    parser.add_argument("--m4-coverage", type=Path, default=M4_COVERAGE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.m4_overlay), read_json(args.m4_coverage))
    write(args.output, artifact)
    print(json.dumps(artifact["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
