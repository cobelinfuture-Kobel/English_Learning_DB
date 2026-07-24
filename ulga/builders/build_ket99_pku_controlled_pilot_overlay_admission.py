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
MAX_LESSONS_PER_PKU = 6
MAX_REFERENCES_PER_LESSON = 8
PRIORITY = {"EXACT_AUTHORITY_REQUIREMENT": 100, "CONTROLLED_TRANSCRIPT_REFERENCE": 80}
M3 = ROOT / ".local/a1fs_v1/ket99_pku_m3/controlled_lesson_candidate_mapping.safe.json"
M2 = ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4/controlled_pilot_overlay_admission.safe.json"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def verify_sources(m3: Mapping[str, Any], consumer: Mapping[str, Any]) -> None:
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


def build_artifact(m3: Mapping[str, Any], consumer: Mapping[str, Any]) -> dict[str, Any]:
    verify_sources(m3, consumer)
    lessons = {
        str(row.get("lesson_id") or ""): row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and row.get("level") in {"A1", "A1+"}
    }
    if not lessons or len(lessons) != len(set(lessons)):
        raise ValueError("learning_lesson_catalog_invalid")

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
                "admission_status": "REJECTED_EXAM_PROCEDURE_ONLY",
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
                "admission_status": "UNRESOLVED_NO_CONTROLLED_CANDIDATE",
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
            proposed_by_lesson[lesson_id].append({
                "pku_id": pku_id,
                "source_transcript_id": str(row.get("source_transcript_id") or ""),
                "mapping_class": mapping_class,
                "mapping_priority": PRIORITY[mapping_class],
                "authority_ids": list(row.get("authority_ids") or []),
                "teaching_need_id": row.get("teaching_need_id"),
                "candidate_evidence": list((row.get("candidate_evidence") or {}).get(lesson_id, [])),
                "runtime_effect": "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY",
                "hard_lesson_selection_allowed": False,
                "production_mapping_allowed": False,
            })
        admission_rows.append({
            "pku_id": pku_id,
            "admission_status": "PENDING_LESSON_CAP_ADMISSION",
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
        if row["admission_status"] == "PENDING_LESSON_CAP_ADMISSION":
            admitted_ids = sorted(admitted_by_pku.get(pku_id, []))
            row = dict(row)
            row["admitted_lesson_ids"] = admitted_ids
            row["lesson_cap_pruned_lesson_ids"] = sorted(pruned_by_lesson.get(pku_id, []))
            row["admission_status"] = (
                "ADMITTED_OPTIONAL_PILOT_REFERENCE" if admitted_ids else "PRUNED_NO_ADMITTED_REFERENCE"
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
            "referenced_lesson_count_by_skill": dict(sorted(per_skill.items())),
            "referenced_lesson_count_by_level": dict(sorted(per_level.items())),
            "hard_graph_edge_delta": 0,
            "hard_lesson_selection_delta": 0,
            "production_lesson_mapping_count": 0,
        },
        "claim_boundaries": {
            "optional_pilot_overlay_admitted": True,
            "production_overlay_admitted": False,
            "m4_selection_changed": False,
            "hard_graph_modified": False,
            "learner_delivery_completed": False,
            "mastery_or_retention_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    artifact["artifact_sha256"] = digest(artifact)
    return artifact


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
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.m3), read_json(args.m2_consumer))
    write(args.output, artifact)
    print(json.dumps(artifact["coverage_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
