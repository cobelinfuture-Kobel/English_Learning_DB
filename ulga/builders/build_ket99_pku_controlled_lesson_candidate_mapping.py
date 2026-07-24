#!/usr/bin/env python3
"""Build controlled KET99 PKU lesson candidates without selecting lessons."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only candidate mapping over confirmed KET99 PKUs, the private M2 lesson catalog, and precision-guarded R3G references; no content, graph mutation, hard selection, production mapping, mastery, media, or A2 payload."
TASK_ID = "KET99-PK-M3_ControlledLessonCandidateMappingAndValidation"
SCHEMA_VERSION = "ket99.pku.controlled_lesson_candidate_mapping.v1"
PASS_STATUS = "PASS_KET99_PK_M3_CONTROLLED_LESSON_CANDIDATE_MAPPING_READY"
NEXT_SHORT_STEP = "KET99-PK-M4_ControlledPilotOverlayAdmissionAndCoverageReadback"
M2_TASK = "KET99-PK-M2_OperatorConfirmationAndTeachingNeedIdentityBridge"
M2_STATUS = "PASS_KET99_PK_M2_OPERATOR_CONFIRMATION_AND_TEACHING_NEED_IDENTITY_BRIDGE_READY"
M2_CONSUMER_TASK = "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery"
M2_CONSUMER_SCHEMA = "a1fs.v1.m2.four_skill_asset_body_consumer.v1"
M2_CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
R3G_TASK = "A1FS-V1-CP07F-R3G_KET99FullSemanticInventoryAndA1A1PlusCoverageExpansion"
R3G_SCHEMA = "a1fs.v1.cp07f.r3g.ket99_full_semantic_inventory_a1a1plus_coverage_expansion.v1"
R3G_STATUS = "PASS_CP07F_R3G_KET99_FULL_SEMANTIC_INVENTORY_AND_A1A1PLUS_COVERAGE_EXPANSION_READY"
ALLOWED_BASES = {
    "BASELINE_R3E_REFERENCE", "EXACT_CP07B_M1_NODE_TARGET",
    "EXACT_NORMALIZED_SEMANTIC_ATOM", "CONTROLLED_CANONICAL_GRAMMAR_IDENTITY",
    "CONTROLLED_HUMAN_EVIDENCE_RESOLUTION", "CONTROLLED_TOPIC_DOMAIN_AND_SKILL",
    "CONTROLLED_STRATEGY_DOMAIN_INTERSECTION",
}
LEVEL_MAP = {
    "ADMITTED_A1": {"A1"}, "ADMITTED_A1_PLUS": {"A1+"},
    "ADMITTED_A1_AND_A1_PLUS": {"A1", "A1+"},
}
SKILLS = {"LISTENING", "SPEAKING", "READING", "WRITING"}
M1_CSV = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_pilot_review.csv"
M2_BRIDGE = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_operator_confirmation_teaching_need_bridge.v1.json"
M2_CONSUMER = ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
R3G = ROOT / ".local/a1fs_v1/cp07r3g/ket99_full_semantic_inventory_and_coverage_expansion.safe.json"
OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m3/controlled_lesson_candidate_mapping.safe.json"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if not rows:
        raise ValueError(f"csv_rows_required:{path}")
    return rows


def decode(bundle: Mapping[str, Any], field_key: str, row_key: str) -> list[dict[str, Any]]:
    fields, raw_rows = bundle.get(field_key), bundle.get(row_key)
    if not isinstance(fields, list) or not isinstance(raw_rows, list):
        raise ValueError(f"row_bundle_missing:{row_key}")
    result = []
    for raw in raw_rows:
        if not isinstance(raw, list) or len(raw) != len(fields):
            raise ValueError(f"row_bundle_invalid:{row_key}")
        result.append(dict(zip(fields, raw)))
    return result


def split_pipe(value: Any) -> set[str]:
    return {part for part in str(value or "").split("|") if part}


def bases(reference: Mapping[str, Any]) -> set[str]:
    raw = reference.get("mapping_basis") or []
    if isinstance(raw, str):
        raw = [raw]
    return {str(item) for item in raw if str(item)}


def verify_sources(bridge: Mapping[str, Any], consumer: Mapping[str, Any], r3g: Mapping[str, Any]) -> None:
    if bridge.get("task_id") != M2_TASK or bridge.get("validation_status") != M2_STATUS or bridge.get("stop_reason") != "NONE":
        raise ValueError("m2_bridge_invalid")
    authority = bridge.get("authority_contract", {})
    if authority.get("production_lesson_mapping_allowed") is not False or authority.get("hard_lesson_selection_allowed") is not False or authority.get("a2_mapping_allowed") is not False:
        raise ValueError("m2_bridge_boundaries_invalid")
    if consumer.get("task_id") != M2_CONSUMER_TASK or consumer.get("schema_version") != M2_CONSUMER_SCHEMA or consumer.get("validation_status") != M2_CONSUMER_STATUS:
        raise ValueError("m2_consumer_invalid")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise ValueError("m2_consumer_a2_lock_invalid")
    if r3g.get("task_id") != R3G_TASK or r3g.get("schema_version") != R3G_SCHEMA or r3g.get("validation_status") != R3G_STATUS or r3g.get("stop_reason") != "NONE":
        raise ValueError("r3g_invalid")
    if r3g.get("source_identity", {}).get("m2_consumer_sha256") != digest(consumer):
        raise ValueError("r3g_m2_binding_invalid")
    precision = r3g.get("precision_summary", {})
    if precision.get("token_only_mapping_allowed") is not False:
        raise ValueError("r3g_token_only_mapping_not_locked")


def build_artifact(
    bridge: Mapping[str, Any], m1_rows: Sequence[Mapping[str, str]],
    consumer: Mapping[str, Any], r3g: Mapping[str, Any],
) -> dict[str, Any]:
    verify_sources(bridge, consumer, r3g)
    decisions = {row["pku_id"]: row for row in decode(bridge, "operator_decision_field_order", "operator_decisions")}
    csv_rows = {str(row.get("pku_id") or ""): row for row in m1_rows if str(row.get("pku_id") or "")}
    if set(decisions) != set(csv_rows):
        raise ValueError("m1_csv_m2_decision_coverage_mismatch")

    lessons = {
        str(row.get("lesson_id") or ""): row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and row.get("level") in {"A1", "A1+"}
    }
    if not lessons:
        raise ValueError("learning_lesson_catalog_empty")
    r3g_lessons = {
        str(row.get("lesson_id") or ""): row
        for row in r3g.get("lesson_instructional_references", [])
        if isinstance(row, Mapping)
    }

    mappings = []
    unresolved = []
    rejected = 0
    exact_ready = controlled_ready = 0
    for pku_id in sorted(decisions):
        decision, source = decisions[pku_id], csv_rows[pku_id]
        transcript_id = str(source.get("source_transcript_id") or "")
        if decision.get("confirmed_disposition") == "REJECTED_EXAM_PROCEDURE_ONLY":
            rejected += 1
            mappings.append({
                "pku_id": pku_id, "source_transcript_id": transcript_id,
                "mapping_class": "REJECTED_EXAM_PROCEDURE_ONLY", "candidate_lesson_ids": [],
                "candidate_status": "NOT_ELIGIBLE", "production_mapping_allowed": False,
            })
            continue

        levels = LEVEL_MAP.get(str(source.get("cefr_decision") or ""))
        skills = split_pipe(source.get("skill_scope"))
        if not levels or not skills or not skills <= SKILLS:
            raise ValueError(f"pku_partition_invalid:{pku_id}")
        authority_ids = [str(item) for item in decision.get("authority_ids") or []]
        teaching_need_id = decision.get("teaching_need_id")
        candidates = []
        evidence: dict[str, list[str]] = {}

        if decision.get("operator_decision") == "CONFIRM_EXACT_AUTHORITY_JOIN":
            mapping_class = "EXACT_AUTHORITY_REQUIREMENT"
            for lesson_id, lesson in lessons.items():
                skill, level = str(lesson.get("skill") or ""), str(lesson.get("level") or "")
                required = set(lesson.get("requirement_node_ids") or [])
                expected = {f"REF:{skill}:{authority_id}" for authority_id in authority_ids}
                if skill in skills and level in levels and required & expected:
                    candidates.append(lesson_id)
                    evidence[lesson_id] = sorted(required & expected)
            status = "EXACT_AUTHORITY_CANDIDATES_READY" if candidates else "NO_EXACT_REQUIREMENT_CANDIDATE"
            exact_ready += bool(candidates)
        elif decision.get("operator_decision") == "CONFIRM_TEACHING_NEED_BRIDGE":
            mapping_class = "CONTROLLED_TRANSCRIPT_REFERENCE"
            for lesson_id, lesson in lessons.items():
                skill, level = str(lesson.get("skill") or ""), str(lesson.get("level") or "")
                if skill not in skills or level not in levels:
                    continue
                reference_bases: set[str] = set()
                for reference in r3g_lessons.get(lesson_id, {}).get("instructional_references", []):
                    if isinstance(reference, Mapping) and reference.get("transcript_id") == transcript_id:
                        reference_bases.update(bases(reference) & ALLOWED_BASES)
                if reference_bases:
                    candidates.append(lesson_id)
                    evidence[lesson_id] = sorted(reference_bases)
            status = "CONTROLLED_REFERENCE_CANDIDATES_READY" if candidates else "NO_CONTROLLED_CANDIDATE_REQUIRES_EVIDENCE"
            controlled_ready += bool(candidates)
        else:
            raise ValueError(f"operator_decision_unsupported:{pku_id}")

        candidates.sort()
        if not candidates:
            unresolved.append(pku_id)
        mappings.append({
            "pku_id": pku_id, "source_transcript_id": transcript_id,
            "mapping_class": mapping_class, "authority_ids": authority_ids,
            "teaching_need_id": teaching_need_id, "level_scope": sorted(levels),
            "skill_scope": sorted(skills), "candidate_lesson_ids": candidates,
            "candidate_count": len(candidates), "candidate_evidence": evidence,
            "candidate_status": status, "production_mapping_allowed": False,
        })

    admitted = len(mappings) - rejected
    mapped = admitted - len(unresolved)
    result = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": PASS_STATUS,
        "source_identity": {
            "m2_bridge_sha256": digest(bridge), "m2_consumer_sha256": digest(consumer),
            "r3g_sha256": digest(r3g), "m1_review_row_count": len(m1_rows),
        },
        "mapping_policy": {
            "exact_authority_requires_exact_requirement_node": True,
            "teaching_need_requires_controlled_r3g_transcript_reference": True,
            "skill_level_only_mapping_allowed": False, "token_only_mapping_allowed": False,
            "hard_lesson_selection_allowed": False, "production_lesson_mapping_allowed": False,
            "a2_mapping_allowed": False,
        },
        "candidate_mappings": mappings,
        "counts": {
            "source_pku_count": len(mappings), "admitted_pku_count": admitted,
            "rejected_exam_procedure_count": rejected, "candidate_mapped_pku_count": mapped,
            "unresolved_pku_count": len(unresolved), "exact_authority_ready_pku_count": exact_ready,
            "controlled_reference_ready_pku_count": controlled_ready,
            "candidate_lesson_reference_count": sum(row.get("candidate_count", 0) for row in mappings),
            "production_lesson_mapping_count": 0,
        },
        "unresolved_pku_ids": unresolved,
        "claim_boundaries": {
            "candidate_mapping_completed": True, "production_overlay_admitted": False,
            "m4_selection_changed": False, "hard_graph_modified": False,
            "learner_content_created": False, "mastery_claimed": False, "a2_unlocked": False,
        },
        "errors": [], "stop_reason": "NONE", "next_short_step": NEXT_SHORT_STEP,
    }
    result["artifact_sha256"] = digest(result)
    return result


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2); handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m1-csv", type=Path, default=M1_CSV)
    parser.add_argument("--m2-bridge", type=Path, default=M2_BRIDGE)
    parser.add_argument("--m2-consumer", type=Path, default=M2_CONSUMER)
    parser.add_argument("--r3g", type=Path, default=R3G)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.m2_bridge), read_csv(args.m1_csv), read_json(args.m2_consumer), read_json(args.r3g))
    write(args.output, artifact); print(json.dumps(artifact["counts"], indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
