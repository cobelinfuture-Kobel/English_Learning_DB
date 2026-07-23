#!/usr/bin/env python3
"""Build an exact KET Authority semantic bridge for CP07C lesson composition.

The bridge resolves opaque M1 requirement identifiers through their exact M1
coverage asset IDs, the corresponding private M2 Asset Body payloads, and
canonical grammar evidence already admitted by the non-authoritative CP07B
instructional overlay.  It never performs fuzzy matching, mutates M1, copies
private payload text, or creates learner-facing content.

Root lessons with no requirement nodes are resolved only from their own Asset
Body payloads.  If no exact semantic evidence is present they remain
UNRESOLVED and downstream composition must fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b  # noqa: E402
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only exact semantic bridge over existing M1 coverage, private M2 Asset Body identities, and CP07B canonical grammar evidence; no payload text, prompt, answer, learner response, canonical mutation, mastery, retention, or A2 payload is produced."

TASK_ID = "A1FS-V1-CP07F-R3C_KETAuthoritySemanticBridgeAndRootLessonTargetFullFix"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3c.ket_authority_semantic_bridge.v1"
PASS_STATUS = "PASS_CP07F_R3C_KET_AUTHORITY_SEMANTIC_BRIDGE_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R3C_FourSkillSemanticLessonCompositionReplay"

DEFAULT_M1 = REPO_ROOT / ".local/a1fs_v1/m1/a1a1plus_prerequisite_graph_and_coverage.private.json"
DEFAULT_M2 = REPO_ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
DEFAULT_CP07B = cp07b.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r3c/ket_authority_semantic_bridge.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r3c/ket_authority_semantic_bridge.validation.json"

SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
SEMANTIC_PATH_HINTS = (
    "target", "objective", "focus", "grammar", "capability", "evidence",
    "acceptance", "diagnostic", "teacher_delivery", "body_title", "body_text",
    "scaffold", "language", "function", "pronunciation", "vocabulary",
)
FORBIDDEN_KEYS = {
    "payload", "source_content", "text", "prompt", "scoring_contract",
    "correct_answer", "answer_key", "learner_response", "audio_bytes",
    "recording", "transcript_text", "speaker_turns",
}


class SemanticBridgeError(ValueError):
    """Fail-closed authority identity, semantic evidence, or lineage error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SemanticBridgeError(f"json_object_required:{path}")
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


def _normalize(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = text.replace("’", "'").replace("can't", "cant")
    text = re.sub(r"[↔→←–—/\\+&]+", "_", text)
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise SemanticBridgeError(f"private_content_key_forbidden:{path}.{key}")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")


def _iter_scalars(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            yield from _iter_scalars(value[key], f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_scalars(child, f"{path}[{index}]")
    elif isinstance(value, (str, int, float, bool)) and not isinstance(value, bool):
        text = str(value).strip()
        if text:
            yield path, text


def _semantic_path(path: str) -> bool:
    normalized = _normalize(path)
    return any(hint in normalized for hint in SEMANTIC_PATH_HINTS)


def _exact_semantic_match(*, semantic_key: str, scalar: str, path: str) -> bool:
    if not semantic_key or semantic_key == "nonlexical_marker":
        return False
    scalar_key = _normalize(scalar)
    if not scalar_key:
        return False
    if scalar_key == semantic_key:
        return True
    bounded = f"_{scalar_key}_"
    needle = f"_{semantic_key}_"
    if needle not in bounded:
        return False
    # Short single-token labels (for example "can") are only authoritative in
    # explicitly semantic fields; longer labels remain exact token sequences.
    if "_" not in semantic_key and len(semantic_key) < 6:
        return _semantic_path(path)
    return True


def _verify_m1(graph: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if graph.get("task_id") != m1.TASK_ID or graph.get("schema_version") != m1.SCHEMA_VERSION:
        raise SemanticBridgeError("m1_contract_invalid")
    if graph.get("validation_status") != m1.STATUS or graph.get("errors") != []:
        raise SemanticBridgeError("m1_not_passed")
    if graph.get("a2_lock_contract", {}).get("state") != "LOCKED_BY_DESIGN":
        raise SemanticBridgeError("m1_a2_lock_invalid")
    nodes = {
        str(row.get("node_id") or ""): row
        for row in graph.get("nodes", [])
        if isinstance(row, Mapping) and str(row.get("node_id") or "")
    }
    coverage = {
        str(row.get("node_id") or ""): row
        for row in graph.get("coverage", [])
        if isinstance(row, Mapping) and str(row.get("node_id") or "")
    }
    if len(nodes) != len(graph.get("nodes", [])) or len(coverage) != len(graph.get("coverage", [])):
        raise SemanticBridgeError("m1_identity_missing_or_duplicate")
    return nodes, coverage


def _verify_m2(consumer: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise SemanticBridgeError("m2_contract_invalid")
    if consumer.get("validation_status") != m2.STATUS or consumer.get("errors") != []:
        raise SemanticBridgeError("m2_not_passed")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise SemanticBridgeError("m2_a2_lock_invalid")
    lessons = {
        str(row.get("lesson_id") or ""): row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and str(row.get("lesson_id") or "")
    }
    assets = {
        str(row.get("asset_key") or ""): row
        for row in consumer.get("asset_records", [])
        if isinstance(row, Mapping) and str(row.get("asset_key") or "")
    }
    if len(lessons) != len(consumer.get("lesson_catalog", [])) or len(assets) != len(consumer.get("asset_records", [])):
        raise SemanticBridgeError("m2_identity_missing_or_duplicate")
    return lessons, assets


def _verify_cp07b(overlay: Mapping[str, Any], graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    if overlay.get("task_id") != cp07b.TASK_ID or overlay.get("schema_version") != cp07b.SCHEMA_VERSION:
        raise SemanticBridgeError("cp07b_contract_invalid")
    if overlay.get("stop_reason") != "NONE" or overlay.get("errors") != []:
        raise SemanticBridgeError("cp07b_not_passed")
    authority = overlay.get("authority_contract")
    if not isinstance(authority, Mapping) or authority.get("hard_graph_mutation_allowed") is not False:
        raise SemanticBridgeError("cp07b_hard_graph_boundary_invalid")
    if authority.get("a2_a2plus_status") != "LOCKED":
        raise SemanticBridgeError("cp07b_a2_lock_invalid")
    if overlay.get("source_identity", {}).get("m1_hard_graph_sha256") != _digest(graph):
        raise SemanticBridgeError("cp07b_m1_binding_invalid")

    candidates: list[dict[str, Any]] = []
    for transcript in overlay.get("transcript_overlays", []):
        if not isinstance(transcript, Mapping):
            continue
        transcript_id = str(transcript.get("transcript_id") or "")
        source_sha = str(transcript.get("source_lineage", {}).get("source_evidence_sha256") or "")
        for occurrence in transcript.get("evidence_occurrences", []):
            if not isinstance(occurrence, Mapping) or occurrence.get("disposition") != "CANONICAL_MATCH":
                continue
            grammar_targets = sorted({
                str(target.get("target_id") or "")
                for target in occurrence.get("canonical_targets", [])
                if isinstance(target, Mapping)
                and target.get("target_type") == "GRAMMAR_UNIT"
                and str(target.get("target_id") or "")
            })
            semantic_key = _normalize(occurrence.get("normalized_evidence_item") or occurrence.get("evidence_item"))
            if grammar_targets and semantic_key and semantic_key != "nonlexical_marker":
                candidates.append({
                    "semantic_key": semantic_key,
                    "grammar_unit_ids": grammar_targets,
                    "evidence_occurrence_id": str(occurrence.get("evidence_occurrence_id") or ""),
                    "transcript_id": transcript_id,
                    "source_evidence_sha256": source_sha,
                })
    if not candidates:
        raise SemanticBridgeError("cp07b_no_canonical_grammar_evidence")
    candidates.sort(key=lambda row: (row["semantic_key"], row["evidence_occurrence_id"]))
    return candidates


def _asset_id(row: Mapping[str, Any]) -> str:
    return str(row.get("asset_id") or "")


def _match_assets(
    *, assets: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]]
) -> tuple[list[str], list[dict[str, Any]]]:
    grammar_ids: set[str] = set()
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for asset in sorted(assets, key=lambda row: str(row.get("asset_key") or "")):
        payload = asset.get("payload")
        if not isinstance(payload, Mapping):
            raise SemanticBridgeError(f"m2_asset_payload_invalid:{asset.get('asset_key')}")
        for payload_path, scalar in _iter_scalars(payload):
            for candidate in candidates:
                semantic_key = str(candidate["semantic_key"])
                if not _exact_semantic_match(semantic_key=semantic_key, scalar=scalar, path=payload_path):
                    continue
                key = (
                    str(asset.get("asset_key") or ""), payload_path,
                    semantic_key, str(candidate["evidence_occurrence_id"]),
                )
                if key in seen:
                    continue
                seen.add(key)
                grammar_ids.update(candidate["grammar_unit_ids"])
                evidence.append({
                    "authority_asset_key": str(asset.get("asset_key") or ""),
                    "authority_asset_id": _asset_id(asset),
                    "authority_payload_path": payload_path,
                    "authority_scalar_sha256": _sha_text(scalar),
                    "normalized_semantic_key": semantic_key,
                    "match_mode": "EXACT_NORMALIZED_AUTHORITY_TEXT",
                    "cp07b_evidence_occurrence_id": str(candidate["evidence_occurrence_id"]),
                    "cp07b_transcript_id": str(candidate["transcript_id"]),
                    "cp07b_source_evidence_sha256": str(candidate["source_evidence_sha256"]),
                    "grammar_unit_ids": list(candidate["grammar_unit_ids"]),
                })
    evidence.sort(key=lambda row: (
        row["authority_asset_key"], row["authority_payload_path"],
        row["normalized_semantic_key"], row["cp07b_evidence_occurrence_id"],
    ))
    return sorted(grammar_ids), evidence


def build_artifact(
    m1_graph: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    nodes, coverage = _verify_m1(m1_graph)
    lessons, asset_index = _verify_m2(m2_consumer)
    semantic_candidates = _verify_cp07b(cp07b_overlay, m1_graph)

    assets_by_lesson: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    asset_by_skill_and_id: dict[tuple[str, str], Mapping[str, Any]] = {}
    for asset in asset_index.values():
        lesson_id = str(asset.get("lesson_id") or "")
        skill = str(asset.get("skill") or "")
        asset_id = _asset_id(asset)
        if lesson_id not in lessons or skill not in SKILLS or not asset_id:
            raise SemanticBridgeError("m2_asset_partition_invalid")
        assets_by_lesson[lesson_id].append(asset)
        key = (skill, asset_id)
        if key in asset_by_skill_and_id:
            raise SemanticBridgeError(f"m2_skill_asset_id_duplicate:{skill}:{asset_id}")
        asset_by_skill_and_id[key] = asset

    bridge_rows: list[dict[str, Any]] = []
    resolution_counts: Counter[str] = Counter()
    root_count = 0
    requirement_count = 0

    for lesson_id, lesson in sorted(lessons.items(), key=lambda item: (
        str(item[1].get("skill") or ""), str(item[1].get("level") or ""), item[0]
    )):
        skill = str(lesson.get("skill") or "")
        level = str(lesson.get("level") or "")
        if level not in {"A1", "A1+"}:
            continue
        requirement_ids = [str(value) for value in lesson.get("requirement_node_ids", [])]
        if any(value not in nodes for value in requirement_ids):
            raise SemanticBridgeError(f"m1_requirement_node_missing:{lesson_id}")

        requirement_rows: list[dict[str, Any]] = []
        all_grammar_ids: set[str] = set()
        all_evidence: list[dict[str, Any]] = []
        matched_requirement_ids: list[str] = []

        if requirement_ids:
            anchor_mode = "REQUIREMENT_ASSET_AUTHORITY"
            requirement_count += 1
            for requirement_id in requirement_ids:
                coverage_row = coverage.get(requirement_id)
                if coverage_row is None:
                    raise SemanticBridgeError(f"m1_requirement_coverage_missing:{requirement_id}")
                authority_assets: list[Mapping[str, Any]] = []
                for asset_id in coverage_row.get("asset_body_ids", []):
                    asset = asset_by_skill_and_id.get((skill, str(asset_id)))
                    if asset is not None and str(asset.get("lesson_id") or "") == lesson_id:
                        authority_assets.append(asset)
                grammar_ids, evidence = _match_assets(assets=authority_assets, candidates=semantic_candidates)
                if grammar_ids:
                    matched_requirement_ids.append(requirement_id)
                    all_grammar_ids.update(grammar_ids)
                    all_evidence.extend(evidence)
                requirement_rows.append({
                    "requirement_node_id": requirement_id,
                    "source_ref": str(nodes[requirement_id].get("source_ref") or ""),
                    "authority_asset_keys": sorted(str(row.get("asset_key") or "") for row in authority_assets),
                    "grammar_unit_ids": grammar_ids,
                    "authority_evidence": evidence,
                    "resolution_status": "RESOLVED" if grammar_ids else "UNRESOLVED",
                })
        else:
            anchor_mode = "ROOT_LESSON_ASSET_AUTHORITY"
            root_count += 1
            grammar_ids, evidence = _match_assets(
                assets=assets_by_lesson.get(lesson_id, []), candidates=semantic_candidates
            )
            all_grammar_ids.update(grammar_ids)
            all_evidence.extend(evidence)

        resolution_status = "RESOLVED" if all_grammar_ids else "UNRESOLVED"
        resolution_counts[resolution_status] += 1
        bridge_rows.append({
            "lesson_id": lesson_id,
            "lesson_node_id": str(lesson.get("lesson_node_id") or ""),
            "skill": skill,
            "level": level,
            "anchor_mode": anchor_mode,
            "requirement_node_ids": requirement_ids,
            "matched_requirement_node_ids": sorted(matched_requirement_ids),
            "grammar_unit_ids": sorted(all_grammar_ids),
            "authority_evidence": sorted(all_evidence, key=lambda row: (
                row["authority_asset_key"], row["authority_payload_path"],
                row["normalized_semantic_key"], row["cp07b_evidence_occurrence_id"],
            )),
            "requirement_resolutions": requirement_rows,
            "resolution_status": resolution_status,
            "unresolved_reason": None if resolution_status == "RESOLVED" else (
                "ROOT_LESSON_AUTHORITY_SEMANTIC_TARGET_NOT_FOUND"
                if not requirement_ids else "REQUIREMENT_AUTHORITY_SEMANTIC_TARGET_NOT_FOUND"
            ),
        })

    summary = {
        "learning_lesson_count": len(bridge_rows),
        "resolved_lesson_count": resolution_counts["RESOLVED"],
        "unresolved_lesson_count": resolution_counts["UNRESOLVED"],
        "root_lesson_count": root_count,
        "requirement_bound_lesson_count": requirement_count,
        "semantic_candidate_count": len(semantic_candidates),
        "hard_graph_edge_count_before": int(m1_graph.get("counts", {}).get("edge_count", 0)),
        "hard_graph_edge_count_after": int(m1_graph.get("counts", {}).get("edge_count", 0)),
        "new_hard_prerequisite_edge_count": 0,
    }
    artifact = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_ket_authority_semantic_bridge",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m1_hard_graph_sha256": _digest(m1_graph),
            "m2_consumer_sha256": _digest(m2_consumer),
            "cp07b_instructional_overlay_sha256": _digest(cp07b_overlay),
        },
        "authority_contract": {
            "identity_join": "M1_COVERAGE_ASSET_ID_TO_M2_ASSET_PAYLOAD",
            "semantic_match_mode": "EXACT_NORMALIZED_AUTHORITY_TEXT_ONLY",
            "fuzzy_matching_allowed": False,
            "manual_opaque_id_mapping_embedded": False,
            "root_lesson_policy": "OWN_ASSET_BODY_AUTHORITY_TARGET_REQUIRED",
            "hard_graph_mutation_allowed": False,
            "a2_a2plus_status": "LOCKED",
        },
        "lesson_semantic_bridges": bridge_rows,
        "coverage_summary": summary,
        "claim_boundaries": {
            "private_payload_text_included": False,
            "manual_semantic_guess_included": False,
            "hard_prerequisite_edge_created": False,
            "canonical_authority_created": False,
            "learner_facing_content_created": False,
            "learner_response_recorded": False,
            "mastery_or_retention_claimed": False,
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        inputs = (_read(args.m1_graph), _read(args.m2_consumer), _read(args.cp07b_overlay))
        artifact = build_artifact(*inputs)
        from ulga.validators import validate_a1fs_v1_cp07r3c_ket_authority_semantic_bridge as validator
        report = validator.validate_artifact(
            artifact, m1_graph=inputs[0], m2_consumer=inputs[1], cp07b_overlay=inputs[2]
        )
        _write_atomic(args.output, artifact)
        _write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (SemanticBridgeError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
