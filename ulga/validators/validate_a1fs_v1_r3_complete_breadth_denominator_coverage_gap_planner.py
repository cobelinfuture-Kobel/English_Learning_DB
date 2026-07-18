#!/usr/bin/env python3
"""Independent validator for A1FS V1 breadth denominator, coverage and gaps."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3

FORBIDDEN_KEYS = {
    "prompt", "answer", "answer_key", "accepted_texts", "model_text", "learner_response",
    "transcript_text", "audio_bytes", "recording_bytes",
}


def _walk_safe(value: Any, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                errors.append(f"private_payload_key_present:{key}")
            _walk_safe(child, errors)
    elif isinstance(value, list):
        for child in value:
            _walk_safe(child, errors)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            errors.append("absolute_path_present")


def validate(
    *, ontology_path: Path, graph_path: Path, profiles_path: Path,
    deployments_path: Path, report_path: Path, m10_report_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        report = r3.read_json(report_path, "report")
        expected = r3.build(
            ontology_path=ontology_path,
            graph_path=graph_path,
            profiles_path=profiles_path,
            deployments_path=deployments_path,
            m10_report_path=m10_report_path,
        )
    except (OSError, json.JSONDecodeError, r3.BreadthCoverageError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"rebuild_failed:{exc}"]}
    if report != expected:
        errors.append("report_rebuild_drift")
    core = {key: value for key, value in report.items() if key != "report_sha256"}
    if report.get("report_sha256") != r3.digest(core):
        errors.append("report_digest_invalid")
    if report.get("task_id") != r3.TASK_ID or report.get("schema_version") != r3.SCHEMA_VERSION:
        errors.append("report_identity_invalid")
    if report.get("validation_status") != r3.STATUS:
        errors.append("report_status_invalid")
    cells = report.get("cells", [])
    cell_ids = [row.get("cell_id") for row in cells]
    if len(cell_ids) != len(set(cell_ids)) or None in cell_ids:
        errors.append("cell_identity_invalid")
    counts = report.get("counts", {})
    if counts.get("denominator_cell_count") != len(cells):
        errors.append("denominator_cell_count_invalid")
    status_counts = Counter(row.get("status") for row in cells)
    for status in r3.CELL_STATUSES:
        status_counts.setdefault(status, 0)
    if counts.get("status_counts") != dict(sorted(status_counts.items())):
        errors.append("status_counts_invalid")
    if set(status_counts) - set(r3.CELL_STATUSES):
        errors.append("unknown_cell_status")
    missing_nodes = set(report.get("profile_missing_capability_node_ids", []))
    profile_cells = {
        row.get("capability_node_id")
        for row in cells
        if row.get("status") == "PROFILE_DEFINITION_REQUIRED"
    }
    if profile_cells != missing_nodes:
        errors.append("profile_missing_partition_invalid")
    gaps = report.get("ranked_gaps", [])
    if [row.get("rank") for row in gaps] != list(range(1, len(gaps) + 1)):
        errors.append("gap_rank_sequence_invalid")
    priorities = [r3.GAP_PRIORITY.get(str(row.get("status")), 1000) for row in gaps]
    if priorities != sorted(priorities):
        errors.append("gap_priority_order_invalid")
    if any(row.get("status") == "RETENTION_PASS" for row in gaps):
        errors.append("completed_cell_present_in_gaps")
    metrics = report.get("coverage_metrics", {})
    denominator = len(cells)
    retained = status_counts["RETENTION_PASS"]
    expected_percent = round(retained * 100.0 / denominator, 2) if denominator else 0.0
    if metrics.get("retention_complete_percent") != expected_percent:
        errors.append("retention_percent_invalid")
    if metrics.get("false_100_percent_blocked") != (retained != denominator):
        errors.append("false_100_percent_guard_invalid")
    boundaries = report.get("claim_boundaries", {})
    for key in (
        "m1_graph_modified", "m10_structural_coverage_replaced", "cartesian_product_generated",
        "a2_unlocked", "mastery_claimed", "retention_claimed_from_structure", "audio_completion_required",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_broken:{key}")
    if report.get("next_short_step") != r3.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")
    _walk_safe(report, errors)
    return {
        "validation_status": r3.STATUS if not errors else "FAIL_A1FS_V1_R3_BREADTH_DENOMINATOR_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "denominator_cell_count": len(cells),
        "gap_count": len(gaps),
        "next_short_step": r3.NEXT_SHORT_STEP if not errors else r3.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--deployments", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--m10-report", type=Path)
    args = parser.parse_args()
    result = validate(
        ontology_path=args.ontology,
        graph_path=args.graph,
        profiles_path=args.profiles,
        deployments_path=args.deployments,
        report_path=args.report,
        m10_report_path=args.m10_report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
