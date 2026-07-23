#!/usr/bin/env python3
"""Build a non-authoritative KET99 instructional reference overlay for 249 lessons.

The 99 teacher transcripts are KET course teaching references. They may add
soft instructional roles, sequence hints, and evidence references to an A1/A1+
lesson, but they never select a lesson, mutate the M1 graph, create a mastery
requirement, or block KET delivery when no exact transcript reference exists.
"""
from __future__ import annotations

import argparse
import hashlib
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

from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b  # noqa: E402
from ulga.builders import build_a1fs_v1_cp07r3c_ket_authority_semantic_bridge as r3c  # noqa: E402
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only optional teaching-reference index over existing KET99, M1, M2, and R3C identities; no transcript text, private payload, prompt, score, learner response, hard prerequisite mutation, mastery, retention, or A2 payload."

TASK_ID = "A1FS-V1-CP07F-R3E_KET99LessonInstructionalReferenceOverlayFullFix"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3e.ket99_lesson_instructional_reference_overlay.v1"
PASS_STATUS = "PASS_CP07F_R3E_KET99_LESSON_INSTRUCTIONAL_REFERENCE_OVERLAY_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R3F_ReferenceAwareOptionalContextLessonComposition"

DEFAULT_M1 = r3c.DEFAULT_M1
DEFAULT_M2 = r3c.DEFAULT_M2
DEFAULT_CP07B = r3c.DEFAULT_CP07B
DEFAULT_R3C = r3c.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r3e/ket99_lesson_instructional_reference_overlay.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r3e/ket99_lesson_instructional_reference_overlay.validation.json"

SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
LEVELS = {"A1", "A1+"}
FORBIDDEN_KEYS = {
    "payload", "source_content", "text", "prompt", "scoring_contract",
    "correct_answer", "answer_key", "learner_response", "transcript_text",
    "speaker_turns", "audio_bytes", "recording",
}


class ReferenceOverlayError(ValueError):
    """Fail-closed identity, source, or reference-overlay contract error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReferenceOverlayError(f"json_object_required:{path}")
    return value


def _write_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
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


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise ReferenceOverlayError(f"private_content_key_forbidden:{path}.{key}")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")


def _verify_sources(
    graph: Mapping[str, Any],
    consumer: Mapping[str, Any],
    overlay: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if graph.get("task_id") != m1.TASK_ID or graph.get("schema_version") != m1.SCHEMA_VERSION:
        raise ReferenceOverlayError("m1_contract_invalid")
    if graph.get("validation_status") != m1.STATUS or graph.get("errors") != []:
        raise ReferenceOverlayError("m1_not_passed")
    if graph.get("a2_lock_contract", {}).get("state") != "LOCKED_BY_DESIGN":
        raise ReferenceOverlayError("m1_a2_lock_invalid")

    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise ReferenceOverlayError("m2_contract_invalid")
    if consumer.get("validation_status") != m2.STATUS or consumer.get("errors") != []:
        raise ReferenceOverlayError("m2_not_passed")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise ReferenceOverlayError("m2_a2_lock_invalid")

    if overlay.get("task_id") != cp07b.TASK_ID or overlay.get("schema_version") != cp07b.SCHEMA_VERSION:
        raise ReferenceOverlayError("cp07b_contract_invalid")
    if overlay.get("stop_reason") != "NONE" or overlay.get("errors") != []:
        raise ReferenceOverlayError("cp07b_not_passed")
    authority = overlay.get("authority_contract")
    if not isinstance(authority, Mapping):
        raise ReferenceOverlayError("cp07b_authority_contract_missing")
    if authority.get("hard_graph_mutation_allowed") is not False or authority.get("a2_a2plus_status") != "LOCKED":
        raise ReferenceOverlayError("cp07b_authority_boundary_invalid")
    if overlay.get("source_identity", {}).get("m1_hard_graph_sha256") != _digest(graph):
        raise ReferenceOverlayError("cp07b_m1_binding_invalid")

    if bridge.get("task_id") != r3c.TASK_ID or bridge.get("schema_version") != r3c.SCHEMA_VERSION:
        raise ReferenceOverlayError("r3c_contract_invalid")
    if bridge.get("validation_status") != r3c.PASS_STATUS or bridge.get("stop_reason") != "NONE" or bridge.get("errors") != []:
        raise ReferenceOverlayError("r3c_not_passed")
    expected_identity = {
        "m1_hard_graph_sha256": _digest(graph),
        "m2_consumer_sha256": _digest(consumer),
        "cp07b_instructional_overlay_sha256": _digest(overlay),
    }
    if bridge.get("source_identity") != expected_identity:
        raise ReferenceOverlayError("r3c_source_identity_mismatch")

    lessons = [
        row for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and str(row.get("level") or "") in LEVELS
    ]
    if len(lessons) != consumer.get("counts", {}).get("learning_lesson_count"):
        raise ReferenceOverlayError("m2_learning_lesson_count_mismatch")
    lesson_ids = [str(row.get("lesson_id") or "") for row in lessons]
    if any(not value for value in lesson_ids) or len(set(lesson_ids)) != len(lesson_ids):
        raise ReferenceOverlayError("m2_learning_lesson_identity_invalid")

    bridge_index = {
        str(row.get("lesson_id") or ""): row
        for row in bridge.get("lesson_semantic_bridges", [])
        if isinstance(row, Mapping)
    }
    if set(bridge_index) != set(lesson_ids):
        raise ReferenceOverlayError("r3c_lesson_identity_set_mismatch")
    return lessons, bridge_index


def _occurrence_index(overlay: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    occurrences: dict[str, dict[str, Any]] = {}
    direct_m1: defaultdict[str, list[str]] = defaultdict(list)
    for transcript in overlay.get("transcript_overlays", []):
        if not isinstance(transcript, Mapping):
            continue
        transcript_id = str(transcript.get("transcript_id") or "")
        source_sha = str(transcript.get("source_lineage", {}).get("source_evidence_sha256") or "")
        for occurrence in transcript.get("evidence_occurrences", []):
            if not isinstance(occurrence, Mapping):
                continue
            occurrence_id = str(occurrence.get("evidence_occurrence_id") or "")
            if not occurrence_id or occurrence_id in occurrences:
                raise ReferenceOverlayError("cp07b_occurrence_identity_missing_or_duplicate")
            targets = sorted(
                {
                    (str(target.get("target_type") or ""), str(target.get("target_id") or ""))
                    for target in occurrence.get("canonical_targets", [])
                    if isinstance(target, Mapping)
                    and str(target.get("target_type") or "")
                    and str(target.get("target_id") or "")
                }
            )
            occurrences[occurrence_id] = {
                "evidence_occurrence_id": occurrence_id,
                "transcript_id": transcript_id,
                "source_evidence_sha256": source_sha,
                "instructional_roles": sorted({str(value) for value in occurrence.get("instructional_roles", []) if str(value)}),
                "canonical_target_refs": [
                    {"target_type": target_type, "target_id": target_id}
                    for target_type, target_id in targets
                ],
            }
            for target_type, target_id in targets:
                if target_type == "M1_NODE":
                    direct_m1[target_id].append(occurrence_id)
    for occurrence_ids in direct_m1.values():
        occurrence_ids.sort()
    return occurrences, dict(direct_m1)


def build_artifact(
    m1_graph: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
    r3c_bridge: Mapping[str, Any],
) -> dict[str, Any]:
    lessons, bridge_index = _verify_sources(m1_graph, m2_consumer, cp07b_overlay, r3c_bridge)
    occurrences, direct_m1 = _occurrence_index(cp07b_overlay)

    lesson_rows: list[dict[str, Any]] = []
    referenced_transcripts: set[str] = set()
    status_counts: Counter[str] = Counter()
    reference_count = 0

    for lesson in sorted(lessons, key=lambda row: (str(row.get("skill") or ""), str(row.get("level") or ""), str(row.get("lesson_id") or ""))):
        lesson_id = str(lesson["lesson_id"])
        requirement_ids = sorted({str(value) for value in lesson.get("requirement_node_ids", []) if str(value)})
        evidence_basis: defaultdict[str, set[str]] = defaultdict(set)
        for requirement_id in requirement_ids:
            for occurrence_id in direct_m1.get(requirement_id, []):
                evidence_basis[occurrence_id].add("EXACT_CP07B_M1_NODE_TARGET")

        bridge_row = bridge_index[lesson_id]
        for evidence in bridge_row.get("authority_evidence", []):
            if not isinstance(evidence, Mapping):
                continue
            occurrence_id = str(evidence.get("cp07b_evidence_occurrence_id") or "")
            if occurrence_id:
                evidence_basis[occurrence_id].add("EXACT_R3C_AUTHORITY_EVIDENCE")
        for resolution in bridge_row.get("requirement_resolutions", []):
            if not isinstance(resolution, Mapping):
                continue
            for evidence in resolution.get("authority_evidence", []):
                if not isinstance(evidence, Mapping):
                    continue
                occurrence_id = str(evidence.get("cp07b_evidence_occurrence_id") or "")
                if occurrence_id:
                    evidence_basis[occurrence_id].add("EXACT_R3C_REQUIREMENT_AUTHORITY_EVIDENCE")

        references: list[dict[str, Any]] = []
        for occurrence_id in sorted(evidence_basis):
            occurrence = occurrences.get(occurrence_id)
            if occurrence is None:
                raise ReferenceOverlayError(f"r3c_occurrence_missing_from_cp07b:{lesson_id}:{occurrence_id}")
            reference = dict(occurrence)
            reference["mapping_basis"] = sorted(evidence_basis[occurrence_id])
            reference["runtime_effect"] = "OPTIONAL_TEACHING_REFERENCE_ONLY"
            references.append(reference)
            referenced_transcripts.add(str(reference["transcript_id"]))

        status = "REFERENCED" if references else "NO_EXACT_KET99_REFERENCE"
        status_counts[status] += 1
        reference_count += len(references)
        lesson_rows.append({
            "lesson_id": lesson_id,
            "lesson_node_id": str(lesson.get("lesson_node_id") or ""),
            "skill": str(lesson.get("skill") or ""),
            "level": str(lesson.get("level") or ""),
            "requirement_node_ids": requirement_ids,
            "reference_status": status,
            "instructional_references": references,
            "delivery_blocked_by_missing_reference": False,
            "hard_lesson_selection_changed": False,
        })

    transcript_ids = {
        str(row.get("transcript_id") or "")
        for row in cp07b_overlay.get("transcript_overlays", [])
        if isinstance(row, Mapping) and str(row.get("transcript_id") or "")
    }
    artifact = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_ket99_lesson_instructional_reference_overlay",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m1_hard_graph_sha256": _digest(m1_graph),
            "m2_consumer_sha256": _digest(m2_consumer),
            "cp07b_instructional_overlay_sha256": _digest(cp07b_overlay),
            "r3c_semantic_bridge_sha256": _digest(r3c_bridge),
        },
        "authority_contract": {
            "source_role": "NON_AUTHORITATIVE_KET_TEACHER_DELIVERY_REFERENCE",
            "hard_graph_mutation_allowed": False,
            "hard_lesson_selection_allowed": False,
            "mastery_gate_creation_allowed": False,
            "delivery_block_on_missing_reference_allowed": False,
            "fuzzy_matching_allowed": False,
            "reference_use": ["TEACHER_DELIVERY", "SOFT_SEQUENCE", "RECYCLE", "REVIEW", "ERROR_REPAIR"],
            "a2_a2plus_status": "LOCKED",
        },
        "lesson_instructional_references": lesson_rows,
        "coverage_summary": {
            "learning_lesson_count": len(lesson_rows),
            "referenced_lesson_count": status_counts["REFERENCED"],
            "unreferenced_lesson_count": status_counts["NO_EXACT_KET99_REFERENCE"],
            "instructional_reference_count": reference_count,
            "transcript_count": len(transcript_ids),
            "referenced_transcript_count": len(referenced_transcripts),
            "unused_transcript_count": len(transcript_ids - referenced_transcripts),
            "hard_graph_edge_delta": 0,
            "blocked_lesson_count": 0,
        },
        "claim_boundaries": {
            "transcript_text_included": False,
            "private_payload_included": False,
            "hard_prerequisite_changed": False,
            "lesson_selection_changed": False,
            "mastery_or_retention_claimed": False,
            "learner_delivery_completed": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _walk_forbidden(artifact)
    return artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1-graph", type=Path, default=DEFAULT_M1)
    parser.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    parser.add_argument("--cp07b-overlay", type=Path, default=DEFAULT_CP07B)
    parser.add_argument("--r3c-bridge", type=Path, default=DEFAULT_R3C)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        inputs = (_read(args.m1_graph), _read(args.m2_consumer), _read(args.cp07b_overlay), _read(args.r3c_bridge))
        artifact = build_artifact(*inputs)
        from ulga.validators import validate_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as validator
        report = validator.validate_artifact(
            artifact,
            m1_graph=inputs[0],
            m2_consumer=inputs[1],
            cp07b_overlay=inputs[2],
            r3c_bridge=inputs[3],
        )
        _write_atomic(args.output, artifact)
        _write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (ReferenceOverlayError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
