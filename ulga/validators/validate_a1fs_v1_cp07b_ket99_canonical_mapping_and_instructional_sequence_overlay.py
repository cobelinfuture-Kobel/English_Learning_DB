#!/usr/bin/env python3
"""Validate the CP07B KET99 canonical mapping and soft sequence overlay."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as builder  # noqa: E402

VALIDATOR_ID = "validate_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay"
SCHEMA_VERSION = "a1fs.v1.cp07b.ket99_instructional_sequence_overlay_validation.v1"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"jsonl_object_required:{path}")
    return rows


def _walk_forbidden(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in builder.FORBIDDEN_KEYS:
                errors.append(f"forbidden_content_key:{path}.{key}")
            _walk_forbidden(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]", errors)


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    content_units: Sequence[Mapping[str, Any]],
    admission_artifact: Mapping[str, Any],
    m1_graph: Mapping[str, Any],
    cp06_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_invalid")
    if artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        errors.append("artifact_not_passed")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")

    expected_source_identity = {
        "transcript_content_units_sha256": builder._digest(list(content_units)),
        "transcript_admission_decisions_sha256": builder._digest(admission_artifact),
        "m1_hard_graph_sha256": builder._digest(m1_graph),
        "cp06_unit_contract_sha256": builder._digest(cp06_artifact),
    }
    if artifact.get("source_identity") != expected_source_identity:
        errors.append("source_identity_mismatch")

    authority = artifact.get("authority_contract")
    if not isinstance(authority, Mapping):
        errors.append("authority_contract_required")
    else:
        if authority.get("canonical_promotion_allowed") is not False:
            errors.append("canonical_promotion_not_locked")
        if authority.get("hard_graph_mutation_allowed") is not False:
            errors.append("hard_graph_mutation_not_locked")
        if authority.get("overlay_mode") != "SOFT_ORDER_AND_SPIRAL_EVIDENCE_ONLY":
            errors.append("overlay_mode_invalid")
        if authority.get("a2_a2plus_status") != "LOCKED":
            errors.append("a2_lock_invalid")

    graph_node_ids = {str(row.get("node_id") or "") for row in m1_graph.get("nodes", []) if isinstance(row, Mapping)}
    grammar_units = {
        str(row.get("grammar_unit_id") or ""): row
        for row in cp06_artifact.get("unit_content_capacity", [])
        if isinstance(row, Mapping)
    }
    transcripts = artifact.get("transcript_overlays")
    if not isinstance(transcripts, list):
        errors.append("transcript_overlay_list_required")
        transcripts = []
    transcript_ids = [str(row.get("transcript_id") or "") for row in transcripts if isinstance(row, Mapping)]
    if tuple(transcript_ids) != builder.EXPECTED_TRANSCRIPT_IDS:
        errors.append("transcript_identity_order_or_range_invalid")

    occurrence_ids: set[str] = set()
    disposition_counts: Counter[str] = Counter()
    overlay_role_counts: Counter[str] = Counter()
    target_occurrence_counts: Counter[str] = Counter()
    target_focus_counts: Counter[str] = Counter()
    evidence_total = 0
    for transcript in transcripts:
        if not isinstance(transcript, Mapping):
            errors.append("transcript_overlay_row_invalid")
            continue
        transcript_id = str(transcript.get("transcript_id") or "")
        if transcript.get("canonical_promotion_allowed") is not False:
            errors.append(f"transcript_canonical_promotion_not_locked:{transcript_id}")
        if transcript.get("planner_admission") != "APPROVED_WITH_CONSTRAINTS":
            errors.append(f"transcript_planner_admission_invalid:{transcript_id}")
        occurrences = transcript.get("evidence_occurrences")
        if not isinstance(occurrences, list):
            errors.append(f"transcript_evidence_occurrence_list_invalid:{transcript_id}")
            continue
        local_counts: Counter[str] = Counter()
        for occurrence in occurrences:
            evidence_total += 1
            if not isinstance(occurrence, Mapping):
                errors.append(f"evidence_occurrence_invalid:{transcript_id}")
                continue
            occurrence_id = str(occurrence.get("evidence_occurrence_id") or "")
            if not occurrence_id or occurrence_id in occurrence_ids:
                errors.append(f"evidence_occurrence_identity_missing_or_duplicate:{occurrence_id}")
            occurrence_ids.add(occurrence_id)
            disposition = str(occurrence.get("disposition") or "")
            if disposition not in builder.DISPOSITIONS:
                errors.append(f"evidence_disposition_invalid:{occurrence_id}")
            disposition_counts[disposition] += 1
            local_counts[disposition] += 1
            roles = occurrence.get("instructional_roles")
            targets = occurrence.get("canonical_targets")
            if not isinstance(roles, list) or any(role not in builder.OVERLAY_ROLES for role in roles):
                errors.append(f"overlay_roles_invalid:{occurrence_id}")
                roles = []
            overlay_role_counts.update(roles)
            if not isinstance(targets, list):
                errors.append(f"canonical_targets_invalid:{occurrence_id}")
                targets = []
            if disposition == "CANONICAL_MATCH" and not targets:
                errors.append(f"canonical_match_without_target:{occurrence_id}")
            if disposition != "CANONICAL_MATCH" and targets:
                errors.append(f"noncanonical_disposition_with_target:{occurrence_id}")
            if disposition == "REVIEW_REQUIRED" and occurrence.get("review_reason") != "NO_HIGH_CONFIDENCE_CANONICAL_RULE_DO_NOT_INVENT_MAPPING":
                errors.append(f"review_reason_invalid:{occurrence_id}")
            for target in targets:
                if not isinstance(target, Mapping):
                    errors.append(f"canonical_target_invalid:{occurrence_id}")
                    continue
                target_type = str(target.get("target_type") or "")
                target_id = str(target.get("target_id") or "")
                key = f"{target_type}:{target_id}"
                if target_type == "GRAMMAR_UNIT":
                    if target_id not in grammar_units:
                        errors.append(f"grammar_target_unknown:{occurrence_id}:{target_id}")
                    elif target.get("internal_stage") not in builder.ALLOWED_STAGES:
                        errors.append(f"grammar_target_stage_invalid:{occurrence_id}:{target_id}")
                elif target_type == "M1_NODE":
                    if target_id not in graph_node_ids:
                        errors.append(f"m1_target_unknown:{occurrence_id}:{target_id}")
                    if target.get("level") not in {"A1", "A1+"}:
                        errors.append(f"m1_target_level_invalid:{occurrence_id}:{target_id}")
                else:
                    errors.append(f"canonical_target_type_invalid:{occurrence_id}:{target_type}")
                target_occurrence_counts[key] += 1
            assignments = occurrence.get("target_role_assignments")
            if not isinstance(assignments, list) or len(assignments) != len(targets):
                errors.append(f"target_role_assignment_count_invalid:{occurrence_id}")
                assignments = []
            for assignment in assignments:
                if not isinstance(assignment, Mapping):
                    errors.append(f"target_role_assignment_invalid:{occurrence_id}")
                    continue
                role = str(assignment.get("sequence_role") or "")
                if role not in {"FOCUS", "RECYCLE"}:
                    errors.append(f"target_sequence_role_invalid:{occurrence_id}")
                key = f"{assignment.get('target_type')}:{assignment.get('target_id')}"
                if role == "FOCUS":
                    target_focus_counts[key] += 1
        if dict(local_counts) != transcript.get("evidence_disposition_counts"):
            errors.append(f"transcript_disposition_summary_mismatch:{transcript_id}")

    rollups = artifact.get("canonical_target_sequences")
    if not isinstance(rollups, list):
        errors.append("canonical_target_sequence_list_required")
        rollups = []
    rollup_keys: set[str] = set()
    ranks: list[int] = []
    for row in rollups:
        if not isinstance(row, Mapping):
            errors.append("canonical_target_sequence_row_invalid")
            continue
        key = f"{row.get('target_type')}:{row.get('target_id')}"
        if key in rollup_keys:
            errors.append(f"canonical_target_sequence_duplicate:{key}")
        rollup_keys.add(key)
        ranks.append(int(row.get("soft_order_rank") or 0))
        if row.get("occurrence_count") != target_occurrence_counts[key]:
            errors.append(f"canonical_target_occurrence_count_mismatch:{key}")
        if row.get("focus_occurrence_count") != target_focus_counts[key]:
            errors.append(f"canonical_target_focus_count_mismatch:{key}")
        if target_focus_counts[key] != 1:
            errors.append(f"canonical_target_must_have_exactly_one_focus:{key}")
    if ranks != list(range(1, len(ranks) + 1)):
        errors.append("soft_order_rank_not_contiguous")
    if rollup_keys != set(target_occurrence_counts):
        errors.append("canonical_target_rollup_set_mismatch")

    summary = artifact.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("coverage_summary_required")
        summary = {}
    if summary.get("transcript_count") != 99 or summary.get("transcript_identity_reconciled_count") != 99:
        errors.append("transcript_count_not_99")
    if summary.get("evidence_occurrence_count") != evidence_total:
        errors.append("evidence_occurrence_count_mismatch")
    if summary.get("evidence_disposition_counts") != {value: disposition_counts[value] for value in builder.DISPOSITIONS}:
        errors.append("evidence_disposition_summary_mismatch")
    if summary.get("overlay_role_assignment_counts") != {value: overlay_role_counts[value] for value in builder.OVERLAY_ROLES}:
        errors.append("overlay_role_summary_mismatch")
    if summary.get("canonical_target_count") != len(rollups):
        errors.append("canonical_target_count_mismatch")
    if summary.get("hard_graph_edge_count_before") != len(m1_graph.get("edges", [])) or summary.get("hard_graph_edge_count_after") != len(m1_graph.get("edges", [])):
        errors.append("hard_graph_edge_count_not_preserved")
    if summary.get("new_hard_prerequisite_edge_count") != 0:
        errors.append("new_hard_prerequisite_edge_detected")

    denied = set(artifact.get("denied_source_claim_ids", []))
    required_denied = {"P093_FALSE_HOPE_WILL_CORRECTION", "P102_KET_ZHONGKAO_EQUIVALENCE"}
    if not required_denied.issubset(denied):
        errors.append("required_denied_source_claims_not_preserved")

    gate = artifact.get("planner_overlay_gate")
    if not isinstance(gate, Mapping):
        errors.append("planner_overlay_gate_required")
    else:
        if gate.get("canonical_graph_mutation_performed") is not False:
            errors.append("canonical_graph_mutation_claim_invalid")
        if gate.get("m4_planner_integration_completed") is not False:
            errors.append("premature_m4_integration_claim")
        if gate.get("hard_graph_digest_preserved") is not True or gate.get("hard_graph_edge_count_preserved") is not True:
            errors.append("hard_graph_preservation_gate_invalid")

    boundaries = artifact.get("claim_boundaries")
    if not isinstance(boundaries, Mapping) or any(value is not False for value in boundaries.values()):
        errors.append("claim_boundaries_invalid")
    if "edges" in artifact:
        errors.append("hard_graph_edges_must_not_be_copied_to_overlay")
    _walk_forbidden(artifact, "$", errors)

    deterministic_rebuild_matches = False
    try:
        rebuilt = builder.build_artifact(content_units, admission_artifact, m1_graph, cp06_artifact)
        deterministic_rebuild_matches = builder._digest(rebuilt) == builder._digest(artifact)
        if not deterministic_rebuild_matches:
            errors.append("deterministic_rebuild_mismatch")
    except (builder.CP07BBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")

    mapped_queryable = review_queryable = a2_fail_closed = False
    try:
        mapped = builder.query_instructional_overlay(artifact, disposition="CANONICAL_MATCH", limit=1)
        mapped_queryable = mapped["returned_count"] == 1
        if not mapped_queryable:
            errors.append("canonical_mapping_query_smoke_failed")
        review = builder.query_instructional_overlay(artifact, disposition="REVIEW_REQUIRED", limit=1)
        review_queryable = review["returned_count"] == 1 or disposition_counts["REVIEW_REQUIRED"] == 0
        if not review_queryable:
            errors.append("review_queue_query_smoke_failed")
    except (builder.CP07BBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"overlay_query_smoke_failed:{exc}")
    try:
        builder.query_instructional_overlay(artifact, level="A2")
        errors.append("a2_overlay_query_not_rejected")
    except builder.CP07BBuildError as exc:
        a2_fail_closed = str(exc) == "A2_OVERLAY_LOCKED"
        if not a2_fail_closed:
            errors.append(f"a2_overlay_wrong_failure:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07B_KET99_INSTRUCTIONAL_SEQUENCE_OVERLAY",
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic_rebuild_matches,
        "mapped_queryable": mapped_queryable,
        "review_queue_queryable": review_queryable,
        "a2_fail_closed": a2_fail_closed,
        "coverage_summary": dict(summary),
        "hard_graph_digest_preserved": artifact.get("source_identity", {}).get("m1_hard_graph_sha256") == builder._digest(m1_graph),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--content-units", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--m1-graph", type=Path, required=True)
    parser.add_argument("--cp06", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read_json(args.artifact),
        content_units=_read_jsonl(args.content_units),
        admission_artifact=_read_json(args.admission),
        m1_graph=_read_json(args.m1_graph),
        cp06_artifact=_read_json(args.cp06),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
