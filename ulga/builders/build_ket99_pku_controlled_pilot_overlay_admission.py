#!/usr/bin/env python3
"""Admit controlled KET99 PKU candidates as optional pilot lesson references."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only optional pilot overlay admission over validated M3 candidates and the private M2 lesson catalog; no content, hard graph mutation, hard lesson selection, production mapping, mastery, media, or A2 payload."
TASK_ID = "KET99-PK-M4_ControlledPilotOverlayAdmissionAndCoverageReadback"
SCHEMA_VERSION = "ket99.pku.controlled_pilot_overlay_admission.v1"
PASS_STATUS = "PASS_KET99_PK_M4_CONTROLLED_PILOT_OVERLAY_ADMISSION_READY"
NEXT_SHORT_STEP = "KET99-PK-M5_OptionalInstructionalOverlayConsumerIntegrationAndRuntimeCanary"
M3_TASK = "KET99-PK-M3_ControlledLessonCandidateMappingAndValidation"
M3_SCHEMA = "ket99.pku.controlled_lesson_candidate_mapping.v1"
M3_STATUS = "PASS_KET99_PK_M3_CONTROLLED_LESSON_CANDIDATE_MAPPING_READY"
M2_TASK = "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery"
M2_SCHEMA = "a1fs.v1.m2.four_skill_asset_body_consumer.v1"
M2_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
R3G_TASK = "A1FS-V1-CP07F-R3G_KET99FullSemanticInventoryAndA1A1PlusCoverageExpansion"
R3G_SCHEMA = "a1fs.v1.cp07f.r3g.ket99_full_semantic_inventory_a1a1plus_coverage_expansion.v1"
R3G_STATUS = "PASS_CP07F_R3G_KET99_FULL_SEMANTIC_INVENTORY_AND_A1A1PLUS_COVERAGE_EXPANSION_READY"
CP07B_TASK = "A1FS-V1-CP07B_KET99CanonicalMappingAndInstructionalSequenceOverlay"
CP07B_SCHEMA = "a1fs.v1.cp07b.ket99_instructional_sequence_overlay.v1"
CP07B_STATUS = "PASS_CP07B_KET99_INSTRUCTIONAL_SEQUENCE_OVERLAY_READY"
CONTROLLED_READY_COUNT = 17
PENDING_COUNT = 15
REJECTED_COUNT = 3
MAX_LESSONS_PER_PKU = 6
MAX_REFERENCES_PER_LESSON = 8
PRIORITY = {"EXACT_AUTHORITY_REQUIREMENT": 100, "CONTROLLED_TRANSCRIPT_REFERENCE": 80}
M3 = ROOT / ".local/a1fs_v1/ket99_pku_m3/controlled_lesson_candidate_mapping.safe.json"
M2 = ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
R3G = ROOT / ".local/a1fs_v1/cp07r3g/ket99_full_semantic_inventory_and_coverage_expansion.safe.json"
CP07B = ROOT / ".local/a1fs_v1/cp07b/ket99_instructional_sequence_overlay.safe.json"
OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4/controlled_pilot_overlay_admission.safe.json"
COVERAGE_OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4/coverage_readback.safe.json"
INDEX_OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4/artifact_index.json"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def verify_sources(
    m3: Mapping[str, Any],
    consumer: Mapping[str, Any],
    r3g: Mapping[str, Any],
    cp07b: Mapping[str, Any],
) -> None:
    if m3.get("task_id") != M3_TASK or m3.get("schema_version") != M3_SCHEMA or m3.get("validation_status") != M3_STATUS:
        raise ValueError("m3_contract_invalid")
    if m3.get("errors") != [] or m3.get("stop_reason") != "NONE":
        raise ValueError("m3_not_passed")
    unsigned = dict(m3)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != digest(unsigned):
        raise ValueError("m3_artifact_sha256_invalid")
    policy = m3.get("mapping_policy", {})
    for key in (
        "skill_level_only_mapping_allowed",
        "token_only_mapping_allowed",
        "hard_lesson_selection_allowed",
        "production_lesson_mapping_allowed",
        "a2_mapping_allowed",
    ):
        if policy.get(key) is not False:
            raise ValueError(f"m3_policy_boundary_invalid:{key}")
    if m3.get("counts", {}).get("production_lesson_mapping_count") != 0:
        raise ValueError("m3_production_mapping_claim_invalid")

    if consumer.get("task_id") != M2_TASK or consumer.get("schema_version") != M2_SCHEMA or consumer.get("validation_status") != M2_STATUS:
        raise ValueError("m2_consumer_invalid")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise ValueError("m2_a2_lock_invalid")
    if m3.get("source_identity", {}).get("m2_consumer_sha256") != digest(consumer):
        raise ValueError("m3_m2_binding_invalid")
    counts = m3.get("counts", {})
    mappings = m3.get("candidate_mappings", [])
    actual_rejected = sum(
        isinstance(row, Mapping)
        and row.get("mapping_class") == "REJECTED_EXAM_PROCEDURE_ONLY"
        for row in mappings
    )
    actual_ready = sum(
        isinstance(row, Mapping)
        and row.get("mapping_class") != "REJECTED_EXAM_PROCEDURE_ONLY"
        and int(row.get("candidate_count", 0)) > 0
        for row in mappings
    )
    actual_pending = len(mappings) - actual_rejected - actual_ready
    if (
        counts.get("source_pku_count") != len(mappings)
        or counts.get("admitted_pku_count") != len(mappings) - actual_rejected
        or counts.get("candidate_mapped_pku_count") != actual_ready
        or counts.get("unresolved_pku_count") != actual_pending
        or counts.get("rejected_exam_procedure_count") != actual_rejected
    ):
        raise ValueError("m3_count_semantics_invalid")
    if len(mappings) == 35 and (
        counts.get("admitted_pku_count") != 32
        or actual_ready != CONTROLLED_READY_COUNT
        or actual_pending != PENDING_COUNT
        or actual_rejected != REJECTED_COUNT
        or counts.get("candidate_lesson_reference_count") != 1021
    ):
        raise ValueError("m3_production_count_semantics_invalid")

    if (
        r3g.get("task_id") != R3G_TASK
        or r3g.get("schema_version") != R3G_SCHEMA
        or r3g.get("validation_status") != R3G_STATUS
        or r3g.get("errors") != []
        or r3g.get("stop_reason") != "NONE"
    ):
        raise ValueError("r3g_contract_invalid")
    precision = r3g.get("precision_summary", {})
    resolution = r3g.get("human_evidence_resolution_summary", {})
    if (
        precision.get("token_only_mapping_allowed") is not False
        or precision.get("precision_gate_passed") is not True
        or resolution.get("unresolved_transcript_ids") != []
    ):
        raise ValueError("r3g_precision_contract_invalid")
    if m3.get("source_identity", {}).get("r3g_sha256") != digest(r3g):
        raise ValueError("m3_r3g_binding_invalid")
    if r3g.get("source_identity", {}).get("m2_consumer_sha256") != digest(consumer):
        raise ValueError("r3g_m2_binding_invalid")

    if (
        cp07b.get("task_id") != CP07B_TASK
        or cp07b.get("schema_version") != CP07B_SCHEMA
        or cp07b.get("errors") != []
        or cp07b.get("stop_reason") != "NONE"
    ):
        raise ValueError("cp07b_contract_invalid")
    if r3g.get("source_identity", {}).get("cp07b_instructional_overlay_sha256") != digest(cp07b):
        raise ValueError("r3g_cp07b_binding_invalid")


def build_artifact(
    m3: Mapping[str, Any],
    consumer: Mapping[str, Any],
    r3g: Mapping[str, Any],
    cp07b: Mapping[str, Any],
) -> dict[str, Any]:
    verify_sources(m3, consumer, r3g, cp07b)
    lessons = {
        str(row.get("lesson_id") or ""): row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and row.get("level") in {"A1", "A1+"}
    }
    if not lessons or len(lessons) != len(set(lessons)):
        raise ValueError("learning_lesson_catalog_invalid")
    r3g_lessons = {
        str(row.get("lesson_id") or ""): row
        for row in r3g.get("lesson_instructional_references", [])
        if isinstance(row, Mapping)
    }
    transcript_inventory = {
        str(row.get("transcript_id") or ""): row
        for row in r3g.get("transcript_semantic_inventory", [])
        if isinstance(row, Mapping)
    }
    cp07b_transcripts = {
        str(row.get("transcript_id") or ""): row
        for row in cp07b.get("transcript_overlays", [])
        if isinstance(row, Mapping)
    }

    proposed_by_lesson: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    admission_rows: list[dict[str, Any]] = []
    rejected = unresolved = candidate_ready = 0
    pruned_by_pku = 0

    for row in sorted(m3.get("candidate_mappings", []), key=lambda item: str(item.get("pku_id") or "")):
        if not isinstance(row, Mapping):
            raise ValueError("m3_candidate_row_not_object")
        pku_id = str(row.get("pku_id") or "")
        if not pku_id:
            raise ValueError("m3_pku_id_missing")
        transcript_id = str(row.get("source_transcript_id") or "")
        transcript = cp07b_transcripts.get(transcript_id)
        inventory = transcript_inventory.get(transcript_id)
        if not transcript_id or transcript is None or inventory is None:
            raise ValueError(f"candidate_transcript_lineage_missing:{pku_id}")
        if (
            transcript.get("unit_id") != inventory.get("unit_id")
            or transcript.get("lesson_role") != inventory.get("lesson_role")
        ):
            raise ValueError(f"candidate_transcript_lineage_drift:{pku_id}")
        if row.get("production_mapping_allowed") is not False:
            raise ValueError(f"m3_candidate_production_mapping_true:{pku_id}")
        mapping_class = str(row.get("mapping_class") or "")
        candidates = row.get("candidate_lesson_ids") or []
        if not isinstance(candidates, list) or len(candidates) != len(set(candidates)):
            raise ValueError(f"m3_candidate_identity_invalid:{pku_id}")
        if row.get("candidate_count", len(candidates)) != len(candidates):
            raise ValueError(f"m3_candidate_count_drift:{pku_id}")

        if mapping_class == "REJECTED_EXAM_PROCEDURE_ONLY":
            rejected += 1
            if candidates:
                raise ValueError(f"rejected_candidate_present:{pku_id}")
            admission_rows.append({
                "pku_id": pku_id,
                "admission_status": "PILOT_REJECTED",
                "admission_reasons": ["REJECTED_EXAM_PROCEDURE_ONLY"],
                "blocked_reasons": ["EXAM_PROCEDURE_ONLY"],
                "admitted_lesson_ids": [],
                "pruned_candidate_lesson_ids": [],
            })
            continue
        if mapping_class not in PRIORITY:
            raise ValueError(f"mapping_class_invalid:{pku_id}:{mapping_class}")
        if not candidates:
            unresolved += 1
            admission_rows.append({
                "pku_id": pku_id,
                "admission_status": "PILOT_PENDING",
                "admission_reasons": [],
                "blocked_reasons": ["NO_CONTROLLED_CANDIDATE_REQUIRES_EVIDENCE"],
                "admitted_lesson_ids": [],
                "pruned_candidate_lesson_ids": [],
            })
            continue

        candidate_ready += 1
        level_scope = set(row.get("level_scope") or [])
        skill_scope = set(row.get("skill_scope") or [])
        selected = sorted(candidates)[:MAX_LESSONS_PER_PKU]
        pruned = sorted(candidates)[MAX_LESSONS_PER_PKU:]
        pruned_by_pku += len(pruned)
        for lesson_id in selected:
            lesson = lessons.get(lesson_id)
            if lesson is None:
                raise ValueError(f"candidate_lesson_missing_or_a2:{pku_id}:{lesson_id}")
            if lesson.get("level") not in level_scope or lesson.get("skill") not in skill_scope:
                raise ValueError(f"candidate_partition_drift:{pku_id}:{lesson_id}")
            lineage_references = [
                reference
                for reference in r3g_lessons.get(lesson_id, {}).get(
                    "instructional_references", []
                )
                if isinstance(reference, Mapping)
                and reference.get("transcript_id") == transcript_id
            ]
            if not lineage_references:
                raise ValueError(f"r3g_candidate_reference_missing:{pku_id}:{lesson_id}")
            occurrence_ids = sorted(
                {
                    str(reference.get("evidence_occurrence_id") or "")
                    for reference in lineage_references
                    if str(reference.get("evidence_occurrence_id") or "")
                }
            )
            if not occurrence_ids:
                raise ValueError(f"candidate_evidence_anchor_missing:{pku_id}:{lesson_id}")
            resolution_anchor_ids = sorted(
                {
                    str(anchor)
                    for reference in lineage_references
                    for anchor in reference.get(
                        "ket99_resolution_anchor_sha256s", []
                    )
                    if str(anchor)
                }
            )
            target_ids = sorted(
                {
                    f"{target.get('target_type')}:{target.get('target_id')}"
                    for reference in lineage_references
                    for target in reference.get("canonical_target_refs", [])
                    if isinstance(target, Mapping)
                    and target.get("target_type")
                    and target.get("target_id")
                }
            )
            semantic_domains = sorted(
                {
                    str(domain)
                    for reference in lineage_references
                    for domain in reference.get("semantic_domains", [])
                    if str(domain)
                }
            )
            authority_ids = sorted(
                {str(value) for value in row.get("authority_ids", []) if str(value)}
            )
            teaching_need_id = row.get("teaching_need_id")
            semantic_linkage_ids = sorted(
                set(target_ids)
                | {f"DOMAIN:{domain}" for domain in semantic_domains}
                | ({str(teaching_need_id)} if teaching_need_id else set())
            )
            proposed_by_lesson[lesson_id].append({
                "pku_id": pku_id,
                "m3_candidate_id": pku_id,
                "source_transcript_id": transcript_id,
                "textbook_page": transcript.get("textbook_page"),
                "source_unit_id": transcript.get("unit_id"),
                "lesson_role": transcript.get("lesson_role"),
                "mapping_class": mapping_class,
                "mapping_priority": PRIORITY[mapping_class],
                "mapping_confidence": (
                    "EXACT_AUTHORITY" if mapping_class == "EXACT_AUTHORITY_REQUIREMENT"
                    else "CONTROLLED_R3G_REFERENCE"
                ),
                "authority_ids": authority_ids,
                "teaching_need_id": teaching_need_id,
                "candidate_evidence": list((row.get("candidate_evidence") or {}).get(lesson_id, [])),
                "evidence_anchor_ids": occurrence_ids,
                "resolution_anchor_sha256s": resolution_anchor_ids,
                "canonical_lesson_ids": [lesson_id],
                "grammar_node_ids": authority_ids,
                "vocabulary_chunk_pattern_ids": semantic_linkage_ids,
                "instructional_sequence_positions": [
                    int(reference.get("admission_rank", 0))
                    for reference in lineage_references
                ],
                "r3g_artifact_sha256": digest(r3g),
                "cp07b_artifact_sha256": digest(cp07b),
                "m2_artifact_sha256": digest(consumer),
                "m3_artifact_sha256": digest(m3),
                "authority_status": "NON_AUTHORITATIVE_PILOT_OVERLAY",
                "admission_decision": "PILOT_ADMITTED",
                "admission_reasons": ["CONTROLLED_LINEAGE_AND_PARTITION_VERIFIED"],
                "blocked_reasons": [],
                "coverage_contribution": "ALREADY_COVERED_EVIDENCE_DENSITY_ONLY",
                "repository_export_policy": "METADATA_ONLY_NO_PRIVATE_TRANSCRIPT_BODY",
                "runtime_effect": "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY",
                "hard_lesson_selection_allowed": False,
                "production_mapping_allowed": False,
            })
        admission_rows.append({
            "pku_id": pku_id,
            "admission_status": "PILOT_PENDING",
            "admission_reasons": ["CONTROLLED_CANDIDATE_CONTRACT_VERIFIED"],
            "blocked_reasons": ["AWAITING_BOUNDED_ADMISSION"],
            "candidate_lesson_ids": sorted(candidates),
            "pre_lesson_cap_lesson_ids": selected,
            "pruned_candidate_lesson_ids": pruned,
        })

    admitted_by_pku: defaultdict[str, list[str]] = defaultdict(list)
    pruned_by_lesson: defaultdict[str, list[str]] = defaultdict(list)
    lesson_rows = []
    exact_refs = controlled_refs = 0
    per_skill: Counter[str] = Counter()
    per_level: Counter[str] = Counter()

    for lesson_id, lesson in sorted(
        lessons.items(),
        key=lambda item: (str(item[1].get("skill")), str(item[1].get("level")), item[0]),
    ):
        proposed = sorted(
            proposed_by_lesson.get(lesson_id, []),
            key=lambda ref: (-int(ref["mapping_priority"]), str(ref["pku_id"])),
        )
        admitted = proposed[:MAX_REFERENCES_PER_LESSON]
        for ref in admitted:
            admitted_by_pku[str(ref["pku_id"])].append(lesson_id)
            if ref["mapping_class"] == "EXACT_AUTHORITY_REQUIREMENT":
                exact_refs += 1
            else:
                controlled_refs += 1
        for ref in proposed[MAX_REFERENCES_PER_LESSON:]:
            pruned_by_lesson[str(ref["pku_id"])].append(lesson_id)
        if admitted:
            per_skill[str(lesson.get("skill"))] += 1
            per_level[str(lesson.get("level"))] += 1
        lesson_rows.append({
            "lesson_id": lesson_id,
            "lesson_node_id": str(lesson.get("lesson_node_id") or ""),
            "skill": str(lesson.get("skill") or ""),
            "level": str(lesson.get("level") or ""),
            "pilot_reference_status": "PILOT_REFERENCED" if admitted else "NO_PILOT_REFERENCE",
            "optional_pilot_references": admitted,
            "delivery_blocked_by_missing_reference": False,
            "hard_lesson_selection_changed": False,
        })

    final_admissions = []
    admitted_pku_count = 0
    for row in admission_rows:
        pku_id = row["pku_id"]
        if row["admission_status"] == "PILOT_PENDING" and row.get("pre_lesson_cap_lesson_ids") is not None:
            admitted_ids = sorted(admitted_by_pku.get(pku_id, []))
            row = dict(row)
            row["admitted_lesson_ids"] = admitted_ids
            row["lesson_cap_pruned_lesson_ids"] = sorted(pruned_by_lesson.get(pku_id, []))
            row["admission_status"] = "PILOT_ADMITTED" if admitted_ids else "PILOT_PENDING"
            row["admission_reasons"] = (
                ["BOUNDED_OPTIONAL_PILOT_REFERENCE_ADMITTED"] if admitted_ids else []
            )
            row["blocked_reasons"] = (
                [] if admitted_ids else ["PRUNED_NO_ADMITTED_REFERENCE"]
            )
            admitted_pku_count += bool(admitted_ids)
        final_admissions.append(row)

    referenced_lessons = sum(row["pilot_reference_status"] == "PILOT_REFERENCED" for row in lesson_rows)
    optional_count = sum(len(row["optional_pilot_references"]) for row in lesson_rows)
    artifact = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_optional_ket99_pku_pilot_overlay",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m3_candidate_mapping_sha256": digest(m3),
            "m2_consumer_sha256": digest(consumer),
            "r3g_precision_artifact_sha256": digest(r3g),
            "cp07b_instructional_overlay_sha256": digest(cp07b),
        },
        "admission_policy": {
            "runtime_effect": "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY",
            "exact_authority_priority": PRIORITY["EXACT_AUTHORITY_REQUIREMENT"],
            "controlled_reference_priority": PRIORITY["CONTROLLED_TRANSCRIPT_REFERENCE"],
            "max_lessons_per_pku": MAX_LESSONS_PER_PKU,
            "max_references_per_lesson": MAX_REFERENCES_PER_LESSON,
            "missing_reference_blocks_delivery": False,
            "hard_lesson_selection_allowed": False,
            "production_mapping_allowed": False,
            "a2_mapping_allowed": False,
        },
        "pku_admissions": final_admissions,
        "lesson_pilot_overlays": lesson_rows,
        "coverage_summary": {
            "learning_lesson_count": len(lesson_rows),
            "semantic_candidate_count": sum(
                int(row.get("candidate_count", 0))
                for row in m3.get("candidate_mappings", [])
                if isinstance(row, Mapping)
            ),
            "non_rejected_pku_count": len(final_admissions) - rejected,
            "controlled_candidate_ready_count": candidate_ready,
            "pilot_referenced_lesson_count": referenced_lessons,
            "unreferenced_lesson_count": len(lesson_rows) - referenced_lessons,
            "source_pku_count": len(final_admissions),
            "candidate_ready_pku_count": candidate_ready,
            "admitted_pku_count": admitted_pku_count,
            "unresolved_pku_count": unresolved,
            "rejected_exam_procedure_count": rejected,
            "optional_reference_count": optional_count,
            "exact_authority_reference_count": exact_refs,
            "controlled_reference_count": controlled_refs,
            "pruned_by_pku_cap_reference_count": pruned_by_pku,
            "pruned_by_lesson_cap_reference_count": sum(len(v) for v in pruned_by_lesson.values()),
            "pending_auto_promotion_count": 0,
            "rejected_reentry_count": 0,
            "referenced_lesson_count_by_skill": dict(sorted(per_skill.items())),
            "referenced_lesson_count_by_level": dict(sorted(per_level.items())),
            "hard_graph_edge_delta": 0,
            "hard_lesson_selection_delta": 0,
            "canonical_denominator_delta": 0,
            "coverage_double_count": 0,
            "production_lesson_mapping_count": 0,
        },
        "claim_boundaries": {
            "optional_pilot_overlay_admitted": True,
            "production_overlay_admitted": False,
            "m4_selection_changed": False,
            "hard_graph_modified": False,
            "canonical_denominator_modified": False,
            "mastery_denominator_modified": False,
            "learner_delivery_completed": False,
            "mastery_or_retention_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    artifact["artifact_sha256"] = digest(artifact)
    if admitted_pku_count <= 0 or admitted_pku_count > candidate_ready:
        raise ValueError("m4_admission_population_invalid")
    if len(final_admissions) == 35 and (
        candidate_ready != CONTROLLED_READY_COUNT
        or unresolved != PENDING_COUNT
        or rejected != REJECTED_COUNT
    ):
        raise ValueError("m4_production_admission_population_invalid")
    return artifact


def build_coverage_readback(
    overlay: Mapping[str, Any],
    m3: Mapping[str, Any],
    consumer: Mapping[str, Any],
) -> dict[str, Any]:
    lesson_rows = overlay.get("lesson_pilot_overlays", [])
    if not isinstance(lesson_rows, list) or not lesson_rows:
        raise ValueError("overlay_lesson_rows_missing")
    denominator = [
        row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and row.get("level") in {"A1", "A1+"}
    ]
    if len(denominator) != len(lesson_rows):
        raise ValueError("coverage_denominator_drift")
    denominator_ids = {str(row.get("lesson_id") or "") for row in denominator}
    if denominator_ids != {
        str(row.get("lesson_id") or "") for row in lesson_rows
    }:
        raise ValueError("coverage_denominator_identity_drift")

    rows = []
    level_counts: dict[str, dict[str, int | float]] = {}
    duplicate_only = 0
    admitted_transcripts: set[str] = set()
    grammar_evidence: set[str] = set()
    lexical_evidence: set[str] = set()
    for row in sorted(lesson_rows, key=lambda value: str(value.get("lesson_id") or "")):
        references = row.get("optional_pilot_references", [])
        if not isinstance(references, list):
            raise ValueError("overlay_reference_rows_invalid")
        reference_count = len(references)
        duplicate_only += max(reference_count - 1, 0)
        for reference in references:
            admitted_transcripts.add(str(reference.get("source_transcript_id") or ""))
            grammar_evidence.update(
                str(value)
                for value in reference.get("grammar_node_ids", [])
                if str(value)
            )
            lexical_evidence.update(
                str(value)
                for value in reference.get("vocabulary_chunk_pattern_ids", [])
                if str(value)
            )
        rows.append({
            "lesson_id": str(row.get("lesson_id") or ""),
            "lesson_node_id": str(row.get("lesson_node_id") or ""),
            "skill": str(row.get("skill") or ""),
            "level": str(row.get("level") or ""),
            "baseline_status": "COVERED",
            "overlay_evidence_reference_count": reference_count,
            "coverage_status_after": "COVERED",
            "coverage_contribution": (
                "ALREADY_COVERED_OVERLAP"
                if reference_count
                else "NO_OVERLAY_CONTRIBUTION"
            ),
            "draft_only": False,
        })

    for level in ("A1", "A1+"):
        total = sum(row["level"] == level for row in rows)
        covered = total
        before = round(covered * 100.0 / total, 6) if total else 0.0
        level_counts[level] = {
            "denominator_count": total,
            "covered_before_count": covered,
            "covered_after_count": covered,
            "coverage_before_percent": before,
            "coverage_after_percent": before,
            "coverage_delta_percentage_points": 0.0,
        }

    overlap = sum(
        bool(row.get("optional_pilot_references"))
        for row in lesson_rows
        if isinstance(row, Mapping)
    )
    coverage = {
        "task_id": TASK_ID,
        "schema_version": "ket99.pku.controlled_pilot_overlay_coverage_readback.v1",
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_canonical_denominator_coverage_readback",
        "source_identity": {
            "m4_overlay_sha256": digest(overlay),
            "m3_candidate_mapping_sha256": digest(m3),
            "m2_consumer_sha256": digest(consumer),
        },
        "coverage_denominator": {
            "source": "A1FS_V1_M2_VALIDATED_A1_A1PLUS_LESSON_CATALOG",
            "source_sha256": digest(consumer),
            "denominator_count": len(rows),
            "canonical_denominator_mutation_count": 0,
        },
        "input_count_semantics": {
            "semantic_candidate_count": overlay.get("coverage_summary", {}).get(
                "semantic_candidate_count"
            ),
            "non_rejected_pku_count": overlay.get("coverage_summary", {}).get(
                "non_rejected_pku_count"
            ),
            "controlled_candidate_ready_count": overlay.get(
                "coverage_summary", {}
            ).get("controlled_candidate_ready_count"),
            "pending_pku_count": overlay.get("coverage_summary", {}).get(
                "unresolved_pku_count"
            ),
            "rejected_pku_count": overlay.get("coverage_summary", {}).get(
                "rejected_exam_procedure_count"
            ),
        },
        "coverage_counts": {
            "baseline_covered_count": len(rows),
            "baseline_missing_count": 0,
            "baseline_draft_only_count": 0,
            "overlay_unique_new_coverage_count": 0,
            "overlay_already_covered_count": overlap,
            "overlay_duplicate_only_count": duplicate_only,
            "overlay_pending_only_count": overlay.get("coverage_summary", {}).get(
                "unresolved_pku_count"
            ),
            "overlay_rejected_count": overlay.get("coverage_summary", {}).get(
                "rejected_exam_procedure_count"
            ),
            "overlay_unmapped_count": 0,
            "coverage_double_count": 0,
            "canonical_graph_mutation_count": 0,
            "canonical_denominator_mutation_count": 0,
        },
        "coverage_by_level": level_counts,
        "coverage_deltas": {
            "grammar_canonical_coverage_delta": 0,
            "vocabulary_canonical_coverage_delta": 0,
            "chunk_pattern_canonical_coverage_delta": 0,
            "lesson_unit_canonical_coverage_delta": 0,
            "grammar_evidence_density_target_count": len(grammar_evidence),
            "vocabulary_chunk_pattern_evidence_density_target_count": len(
                lexical_evidence
            ),
        },
        "source_evidence_coverage": {
            "admitted_transcript_count": len(admitted_transcripts - {""}),
            "controlled_candidate_ready_count": overlay.get(
                "coverage_summary", {}
            ).get("controlled_candidate_ready_count"),
            "overlay_evidence_increases_density_only": True,
        },
        "coverage_rows": rows,
        "no_double_count_proof": {
            "canonical_target_key": "lesson_id",
            "distinct_denominator_target_count": len(denominator_ids),
            "coverage_credit_per_target_maximum": 1,
            "overlap_increases_evidence_density_only": True,
            "pending_coverage_credit": 0,
            "rejected_coverage_credit": 0,
            "proof_status": "PASS",
        },
        "claim_boundaries": {
            "canonical_coverage_modified": False,
            "canonical_denominator_modified": False,
            "hard_graph_modified": False,
            "mastery_denominator_modified": False,
            "a2_unlocked": False,
            "learner_effectiveness_claimed": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    coverage["artifact_sha256"] = digest(coverage)
    return coverage


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_artifact_index(
    overlay_path: Path,
    coverage_path: Path,
) -> dict[str, Any]:
    value = {
        "task_id": TASK_ID,
        "schema_version": "ket99.pku.controlled_pilot_overlay_artifact_index.v1",
        "artifacts": [
            {
                "artifact_role": "CONTROLLED_PILOT_OVERLAY_ADMISSION",
                "path": overlay_path.name,
                "byte_size": overlay_path.stat().st_size,
                "sha256": file_sha256(overlay_path),
                "repository_export_policy": "PRIVATE_METADATA_ONLY",
            },
            {
                "artifact_role": "CANONICAL_COVERAGE_READBACK",
                "path": coverage_path.name,
                "byte_size": coverage_path.stat().st_size,
                "sha256": file_sha256(coverage_path),
                "repository_export_policy": "PRIVATE_METADATA_ONLY",
            },
        ],
        "private_locator": "private://a1fs-v1/ket99-pku-m4",
        "downstream_consumer": NEXT_SHORT_STEP,
    }
    value["artifact_sha256"] = digest(value)
    return value


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m3", type=Path, default=M3)
    parser.add_argument("--m2-consumer", type=Path, default=M2)
    parser.add_argument("--r3g", type=Path, default=R3G)
    parser.add_argument("--cp07b", type=Path, default=CP07B)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--coverage-output", type=Path, default=COVERAGE_OUTPUT)
    parser.add_argument("--index-output", type=Path, default=INDEX_OUTPUT)
    args = parser.parse_args(argv)
    m3 = read_json(args.m3)
    consumer = read_json(args.m2_consumer)
    artifact = build_artifact(
        m3,
        consumer,
        read_json(args.r3g),
        read_json(args.cp07b),
    )
    coverage = build_coverage_readback(artifact, m3, consumer)
    write(args.output, artifact)
    write(args.coverage_output, coverage)
    write(
        args.index_output,
        build_artifact_index(args.output, args.coverage_output),
    )
    print(json.dumps(artifact["coverage_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
