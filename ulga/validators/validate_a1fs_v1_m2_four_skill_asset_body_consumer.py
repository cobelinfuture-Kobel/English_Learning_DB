#!/usr/bin/env python3
"""Independent integrity and boundary validator for the M2 private consumer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1

TASK_ID = "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery"
STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
NEXT_SHORT_STEP = "A1FS-V1-M3_LearnerProfileSessionAndStateStorage"


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes(); value = json.loads(raw)
    if not isinstance(value, dict): raise ValueError("json_not_object")
    return value, raw


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(tmp, path)


def validate(index_path: Path, graph_path: Path, baseline_path: Path, paths: dict[str, Path]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        index, _ = _load(index_path); graph, graph_raw = _load(graph_path)
        m1._baseline(baseline_path, paths)
    except Exception as exc:
        return {"validation_status": "FAIL_A1FS_V1_M2", "error_count": 1, "errors": [str(exc)]}
    if index.get("task_id") != TASK_ID: errors.append("task_id_invalid")
    if index.get("validation_status") != STATUS: errors.append("validation_status_invalid")
    if index.get("next_short_step") != NEXT_SHORT_STEP: errors.append("next_short_step_invalid")
    if index.get("source_graph_sha256") != hashlib.sha256(graph_raw).hexdigest(): errors.append("graph_hash_mismatch")
    if graph.get("validation_status") != m1.STATUS: errors.append("graph_status_invalid")
    assets = index.get("asset_records"); catalog = index.get("lesson_catalog")
    if not isinstance(assets, list) or not isinstance(catalog, list):
        errors.append("consumer_collections_invalid"); assets = []; catalog = []
    keys = [row.get("asset_key") for row in assets if isinstance(row, dict)]
    if len(keys) != len(assets) or len(set(keys)) != len(keys): errors.append("asset_key_invalid")
    graph_lessons = {row.get("source_ref"): row for row in graph.get("nodes", []) if row.get("node_type") == "LESSON"}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in assets:
        if not isinstance(row, dict): continue
        if row.get("release_scope") != "PRIVATE_INTERNAL_D0": errors.append(f'asset_release_scope_invalid:{row.get("asset_key")}')
        if not isinstance(row.get("payload"), dict) or row.get("content_digest") != _digest(row.get("payload")):
            errors.append(f'asset_digest_invalid:{row.get("asset_key")}')
        lesson = graph_lessons.get(row.get("lesson_id"))
        if not lesson or lesson.get("skill") != row.get("skill") or lesson.get("level") != row.get("level"):
            errors.append(f'asset_graph_partition_invalid:{row.get("asset_key")}')
        grouped[str(row.get("lesson_id"))].append(row)
    catalog_map = {row.get("lesson_id"): row for row in catalog if isinstance(row, dict)}
    if len(catalog_map) != len(catalog): errors.append("lesson_catalog_identity_invalid")
    if set(catalog_map) != set(grouped): errors.append("lesson_catalog_coverage_mismatch")
    for lesson_id, rows in grouped.items():
        item = catalog_map.get(lesson_id, {})
        if sorted(item.get("asset_keys") or []) != sorted(row.get("asset_key") for row in rows): errors.append(f"catalog_assets_mismatch:{lesson_id}")
        if sorted(item.get("roles") or []) != sorted({row.get("role") for row in rows}): errors.append(f"catalog_roles_mismatch:{lesson_id}")
        if item.get("release_scope") != "PRIVATE_INTERNAL_D0": errors.append(f"catalog_release_scope_invalid:{lesson_id}")
    counts = index.get("counts") or {}
    expected = {
        "asset_record_count": len(assets), "lesson_count": len(catalog),
        "learning_lesson_count": sum(row.get("level") in {"A1", "A1+"} for row in catalog),
        "a2_handoff_lesson_count": sum(row.get("level") == "A2" for row in catalog),
    }
    for key, value in expected.items():
        if counts.get(key) != value: errors.append(f"reported_count_mismatch:{key}")
    access = index.get("access_contract") or {}
    if access.get("visibility") != "PRIVATE_INTERNAL": errors.append("visibility_invalid")
    if access.get("learning_query_levels") != ["A1", "A1+"]: errors.append("learning_query_levels_invalid")
    if access.get("a2_payload_query_allowed") is not False or access.get("a2_handoff_metadata_allowed") is not True:
        errors.append("a2_access_boundary_invalid")
    if access.get("max_query_limit") != 100: errors.append("query_limit_contract_invalid")
    boundaries = index.get("claim_boundaries") or {}
    for key in ("learner_ui_implemented", "learner_state_implemented", "planner_implemented", "mastery_claimed", "learner_release_approved", "a2_unlocked"):
        if boundaries.get(key) is not False: errors.append(f"claim_boundary_invalid:{key}")
    return {
        "task_id": TASK_ID,
        "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER",
        "error_count": len(errors), "errors": errors,
        "checked_asset_record_count": len(assets), "checked_lesson_count": len(catalog),
        "checked_package_count": len(paths), "next_short_step": NEXT_SHORT_STEP if not errors else TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True); parser.add_argument("--graph", type=Path, required=True); parser.add_argument("--baseline", type=Path, required=True)
    for name in ("ketw", "ketr", "kets", "ketl"): parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True); args = parser.parse_args()
    report = validate(args.index, args.graph, args.baseline, {"WRITING": args.ketw, "READING": args.ketr, "SPEAKING": args.kets, "LISTENING": args.ketl})
    _atomic(args.validation_report, report); print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if not report["errors"] else 1


if __name__ == "__main__": raise SystemExit(main())
