#!/usr/bin/env python3
"""Materialize deterministic private M12F evidence-bridge assets.

The builder is allowed only after the fail-closed candidate report proves that
none of the frozen A1/A1+ Asset Body records is content-equivalent to the nine
resolved M12 items. It writes private-local graph and consumer overlays. The
records are evidence adapters, not learner-renderable curriculum.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12f_explicit_mapping_overlay as overlay  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge  # noqa: E402

TASK_ID = "E4S-A1V1-M12F_DedicatedPrivateBridgeAssetMaterialization"
SCHEMA_VERSION = "e4s.a1v1.m12f.dedicated_private_bridge_assets.v1"
STATUS = "PASS_M12F_DEDICATED_PRIVATE_BRIDGE_ASSETS_READY"
NEXT_SHORT_STEP = bridge.TASK_ID
EXPECTED_COUNT = bridge.EXPECTED_ATTEMPTS
EVIDENCE_BASIS = "SOURCE_BANK_IDENTITY_PRESERVING_DEDICATED_BRIDGE"
GRAPH_FILENAME = "a1a1plus_prerequisite_graph_and_coverage.m12f_bridge.private.json"
CONSUMER_FILENAME = "four_skill_asset_body_consumer.m12f_bridge.private.json"
REPORT_FILENAME = "m12f_dedicated_private_bridge_assets.safe.json"
VALID_SKILLS = {"LISTENING", "SPEAKING", "READING", "WRITING"}


class DedicatedBridgeError(ValueError):
    """Fail-closed dedicated bridge materialization error."""


def require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise DedicatedBridgeError(f"{code}:expected={expected!r}:actual={actual!r}")


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
    os.chmod(path, 0o600)


def load_candidate_report(path: Path, source: Mapping[str, Any], item_ids: list[str]) -> dict[str, Any]:
    report = overlay.read_json(overlay.safe_local_file(path, "candidate_report"), "candidate_report")
    require(report.get("validation_status"), overlay.CANDIDATE_BLOCKED_STATUS, "candidate_status")
    require(report.get("stop_reason"), overlay.CANDIDATE_EVIDENCE_STOP, "candidate_stop_reason")
    require(report.get("source_session_bank_sha256"), source["bank_hash"], "candidate_bank_hash")
    require(report.get("source_consumer_sha256"), source["consumer_hash"], "candidate_consumer_hash")
    require(report.get("source_graph_sha256"), source["graph_hash"], "candidate_graph_hash")
    require(set(report.get("blocked_item_ids", [])), set(item_ids), "candidate_blocked_partition")
    rows = report.get("items")
    if not isinstance(rows, list) or len(rows) != len(item_ids):
        raise DedicatedBridgeError("candidate_item_count_invalid")
    by_item = {str(row.get("item_id")): row for row in rows if isinstance(row, Mapping)}
    require(set(by_item), set(item_ids), "candidate_item_partition")
    for item_id in item_ids:
        require(by_item[item_id].get("candidate_count"), 0, f"candidate_not_exhausted:{item_id}")
        if by_item[item_id].get("top_candidates") not in ([], None):
            raise DedicatedBridgeError(f"candidate_top_rows_present:{item_id}")
    return report


def role_for(item: Mapping[str, Any], skill: str) -> str:
    contract = item.get("private_scoring_contract")
    if not isinstance(contract, Mapping):
        raise DedicatedBridgeError(f"source_scoring_contract_missing:{item.get('item_id')}")
    mode = str(contract.get("scoring_mode") or "")
    if mode == "FEATURE_RUBRIC":
        return "PRD" if skill in {"WRITING", "SPEAKING"} else "EVD"
    if mode in {"EXACT_OPTION", "EXACT_SEQUENCE", "NORMALIZED_TEXT"}:
        return "CHK"
    raise DedicatedBridgeError(f"source_scoring_mode_unsupported:{item.get('item_id')}:{mode}")


def identity_for(item_id: str, skill: str) -> dict[str, str]:
    token = overlay.canonical_sha(item_id)[:16]
    lesson_id = f"M12F-{skill[:3]}-{token}"
    return {
        "asset_id": f"M12F-BRIDGE-{token}",
        "asset_key": f"{skill}:M12F:{token}",
        "lesson_id": lesson_id,
        "lesson_node_id": f"LESSON:{skill}:{lesson_id}",
        "capability_node_id": f"REF:{skill}:M12F:{token}",
    }


def dedicated_asset(item: Mapping[str, Any], bank_hash: str) -> tuple[dict[str, Any], dict[str, str]]:
    item_id = str(item.get("item_id") or "")
    grammar_unit_id = str(item.get("grammar_unit_id") or "")
    skill = str(item.get("skill") or "").upper()
    level = str(item.get("level") or "A1")
    if not item_id or not grammar_unit_id or skill not in VALID_SKILLS:
        raise DedicatedBridgeError(f"source_item_identity_invalid:{item_id}")
    if level not in {"A1", "A1+"}:
        raise DedicatedBridgeError(f"source_item_level_out_of_scope:{item_id}:{level}")
    role = role_for(item, skill)
    identity = identity_for(item_id, skill)
    payload = {
        "body_title": f"M12F private evidence bridge — {grammar_unit_id}",
        "instruction": "Private evidence adapter bound to the original M12 source item; not learner-renderable.",
        "bridge_only": True,
        "rendering_allowed": False,
        "source_grammar_unit_id": grammar_unit_id,
        "source_task_type": str(item.get("task_type") or ""),
        "source_item_sha256": overlay.canonical_sha(item),
        "m12_item_id": item_id,
        "m12_session_bank_sha256": bank_hash,
        "m12_mapping_evidence_basis": EVIDENCE_BASIS,
        "private_scoring_contract": deepcopy(dict(item["private_scoring_contract"])),
        "response_capture_enabled": True,
    }
    asset = {
        "asset_id": identity["asset_id"],
        "asset_key": identity["asset_key"],
        "lesson_id": identity["lesson_id"],
        "skill": skill,
        "level": level,
        "role": role,
        "payload": payload,
        "content_digest": overlay.canonical_sha(payload),
        "release_scope": "PRIVATE_INTERNAL_D0",
    }
    drift = bridge._contract_drift(asset, item)
    if drift:
        raise DedicatedBridgeError(f"dedicated_asset_contract_drift:{item_id}:{','.join(drift)}")
    if not m6.derive_contract(asset).get("capture_enabled"):
        raise DedicatedBridgeError(f"dedicated_asset_capture_disabled:{item_id}")
    return asset, identity


def build_overlays(source: Mapping[str, Any], candidate_report: Mapping[str, Any], item_ids: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    graph = deepcopy(source["graph"])
    consumer = deepcopy(source["consumer"])
    bank_hash = str(source["bank_hash"])
    gate = str(graph.get("a2_lock_contract", {}).get("gate_node_id") or "")
    node_ids = {str(row.get("node_id")) for row in graph.get("nodes", [])}
    if not gate or gate not in node_ids:
        raise DedicatedBridgeError("a2_gate_node_missing")

    asset_ids = {str(row.get("asset_id")) for row in consumer.get("asset_records", [])}
    asset_keys = {str(row.get("asset_key")) for row in consumer.get("asset_records", [])}
    lesson_ids = {str(row.get("lesson_id")) for row in consumer.get("lesson_catalog", [])}
    coverage_ids = {str(row.get("node_id")) for row in graph.get("coverage", [])}
    required = list(graph["a2_lock_contract"]["required_mastery_node_ids"])
    edge_keys = {(row["from_node_id"], row["to_node_id"], row["edge_type"]) for row in graph.get("edges", [])}
    materialized: list[dict[str, Any]] = []

    for item_id in sorted(item_ids):
        item = source["items_by_id"].get(item_id)
        if not isinstance(item, Mapping):
            raise DedicatedBridgeError(f"source_item_missing:{item_id}")
        asset, ident = dedicated_asset(item, bank_hash)
        collisions = [
            ident["asset_id"] in asset_ids,
            ident["asset_key"] in asset_keys,
            ident["lesson_id"] in lesson_ids,
            ident["lesson_node_id"] in node_ids,
            ident["capability_node_id"] in node_ids,
            ident["capability_node_id"] in coverage_ids,
        ]
        if any(collisions):
            raise DedicatedBridgeError(f"dedicated_identity_collision:{item_id}")
        skill, level, role = asset["skill"], asset["level"], asset["role"]
        consumer["asset_records"].append(asset)
        consumer["lesson_catalog"].append({
            "lesson_id": ident["lesson_id"],
            "lesson_node_id": ident["lesson_node_id"],
            "skill": skill,
            "level": level,
            "asset_keys": [ident["asset_key"]],
            "roles": [role],
            "requirement_node_ids": [ident["capability_node_id"]],
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
        graph["nodes"].extend([
            {
                "node_id": ident["lesson_node_id"], "node_type": "LESSON", "skill": skill,
                "level": level, "source_ref": ident["lesson_id"], "mastery_required_before_a2": False,
                "asset_body_count": 1, "roles": [role], "private_bridge_only": True,
            },
            {
                "node_id": ident["capability_node_id"], "node_type": "CAPABILITY", "skill": skill,
                "level": level, "source_ref": item_id, "mastery_required_before_a2": True,
                "private_bridge_only": True,
            },
        ])
        graph["coverage"].append({
            "node_id": ident["capability_node_id"], "skill": skill, "source_ref": item_id,
            "coverage_class": "MASTERY", "levels": [level], "lesson_ids": [ident["lesson_id"]],
            "asset_body_ids": [ident["asset_id"]], "roles": [role], "coverage_status": "COVERED",
            "private_bridge_only": True,
        })
        for edge in (
            {"from_node_id": ident["capability_node_id"], "to_node_id": ident["lesson_node_id"], "edge_type": "TAUGHT_BY"},
            {"from_node_id": ident["capability_node_id"], "to_node_id": gate, "edge_type": "UNLOCK_REQUIRES"},
        ):
            key = (edge["from_node_id"], edge["to_node_id"], edge["edge_type"])
            if key in edge_keys:
                raise DedicatedBridgeError(f"dedicated_edge_collision:{item_id}")
            graph["edges"].append(edge)
            edge_keys.add(key)
        required.append(ident["capability_node_id"])
        materialized.append({
            "item_id": item_id, "asset_key": ident["asset_key"], "asset_id": ident["asset_id"],
            "lesson_id": ident["lesson_id"], "capability_node_id": ident["capability_node_id"],
            "skill": skill, "level": level, "role": role,
        })
        node_ids.update({ident["lesson_node_id"], ident["capability_node_id"]})
        coverage_ids.add(ident["capability_node_id"])
        asset_ids.add(ident["asset_id"])
        asset_keys.add(ident["asset_key"])
        lesson_ids.add(ident["lesson_id"])

    graph["nodes"] = sorted(graph["nodes"], key=lambda row: row["node_id"])
    graph["edges"] = sorted(graph["edges"], key=lambda row: (row["from_node_id"], row["to_node_id"], row["edge_type"]))
    graph["coverage"] = sorted(graph["coverage"], key=lambda row: row["node_id"])
    required = sorted(set(required))
    graph["a2_lock_contract"]["required_mastery_node_ids"] = required
    require(graph["a2_lock_contract"].get("state"), "LOCKED_BY_DESIGN", "a2_lock_state")
    counts = graph["counts"]
    counts["node_count"] = len(graph["nodes"])
    counts["edge_count"] = len(graph["edges"])
    counts["coverage_record_count"] = len(graph["coverage"])
    counts["lesson_count"] = int(counts["lesson_count"]) + len(materialized)
    by_level = dict(counts.get("lesson_count_by_level", {}))
    for row in materialized:
        by_level[row["level"]] = int(by_level.get(row["level"], 0)) + 1
    counts["lesson_count_by_level"] = by_level
    counts["required_mastery_node_count"] = len(required)
    counts["uncovered_required_node_count"] = 0
    graph["m12f_dedicated_private_bridge_overlay"] = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "source_graph_sha256": source["graph_hash"],
        "source_session_bank_sha256": bank_hash, "candidate_report_sha256": overlay.canonical_sha(candidate_report),
        "dedicated_asset_count": len(materialized), "private_local_only": True,
    }

    consumer["asset_records"] = sorted(consumer["asset_records"], key=lambda row: row["asset_key"])
    consumer["lesson_catalog"] = sorted(consumer["lesson_catalog"], key=lambda row: row["lesson_id"])
    ccounts = consumer["counts"]
    ccounts["asset_record_count"] = len(consumer["asset_records"])
    ccounts["lesson_count"] = len(consumer["lesson_catalog"])
    ccounts["learning_lesson_count"] = sum(row.get("level") in {"A1", "A1+"} for row in consumer["lesson_catalog"])
    ccounts["a2_handoff_lesson_count"] = sum(row.get("level") == "A2" for row in consumer["lesson_catalog"])
    consumer["m12f_dedicated_private_bridge_overlay"] = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "source_consumer_sha256": source["consumer_hash"],
        "source_session_bank_sha256": bank_hash, "candidate_report_sha256": overlay.canonical_sha(candidate_report),
        "dedicated_asset_count": len(materialized), "private_local_only": True,
    }

    report = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
        "source_session_bank_sha256": bank_hash, "source_consumer_sha256": source["consumer_hash"],
        "source_graph_sha256": source["graph_hash"], "candidate_report_sha256": overlay.canonical_sha(candidate_report),
        "item_count": len(item_ids), "dedicated_asset_count": len(materialized),
        "dedicated_lesson_count": len(materialized), "required_mastery_added_count": len(materialized),
        "materialized": materialized, "mapping_ready": False,
        "a2_lock_state": graph["a2_lock_contract"]["state"],
        "claim_boundaries": {
            "frozen_package_modified": False, "canonical_graph_modified": False,
            "canonical_coverage_modified": False, "canonical_authority_write": False,
            "new_curriculum_authored": False, "learner_rendering_enabled": False,
            "a2_content_promoted": False, "a2_payload_access_granted": False,
            "private_local_only": True,
        },
        "stop_reason": "NONE", "next_short_step": NEXT_SHORT_STEP,
    }
    require(len(materialized), EXPECTED_COUNT, "materialized_count")
    return graph, consumer, report


def materialize(*, source_bank_path: Path, consumer_path: Path, graph_path: Path, candidate_report_path: Path, item_ids: list[str], output_root: Path) -> dict[str, Any]:
    output_root = overlay.safe_local_root(output_root)
    source = overlay.load_sources(source_bank_path, consumer_path, graph_path)
    item_ids = list(dict.fromkeys(item_ids))
    require(len(item_ids), EXPECTED_COUNT, "item_id_count")
    candidate_report = load_candidate_report(candidate_report_path, source, item_ids)
    graph, consumer, report = build_overlays(source, candidate_report, item_ids)
    graph_output = output_root / GRAPH_FILENAME
    consumer_output = output_root / CONSUMER_FILENAME
    report_output = output_root / REPORT_FILENAME
    write_private(graph_output, graph)
    consumer["source_graph_sha256"] = overlay.file_sha(graph_output)
    consumer["m12f_dedicated_private_bridge_overlay"]["output_graph_sha256"] = consumer["source_graph_sha256"]
    write_private(consumer_output, consumer)
    mapping = bridge._mapping({
        "entries_by_id": {item_id: {} for item_id in item_ids},
        "consumer": consumer,
        "graph": graph,
        "bank_hash": source["bank_hash"],
        "bank_by_id": {item_id: source["items_by_id"][item_id] for item_id in item_ids},
    })
    if not mapping["ready"]:
        raise DedicatedBridgeError(f"dedicated_mapping_not_ready:{mapping['issues']}")
    report["mapping_ready"] = True
    report["mapped_count"] = len(mapping["mapped"])
    report["output_graph_sha256"] = overlay.file_sha(graph_output)
    report["output_consumer_sha256"] = overlay.file_sha(consumer_output)
    write_private(report_output, report)
    return {
        "graph": graph, "consumer": consumer, "report": report, "mapping": mapping,
        "graph_output": graph_output, "consumer_output": consumer_output, "report_output": report_output,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-bank", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--candidate-report", type=Path, required=True)
    parser.add_argument("--item-id", action="append", dest="item_ids", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = materialize(
            source_bank_path=args.source_bank, consumer_path=args.consumer, graph_path=args.graph,
            candidate_report_path=args.candidate_report, item_ids=args.item_ids, output_root=args.output_root,
        )
        report = result["report"]
        print(json.dumps({
            "validation_status": report["validation_status"],
            "dedicated_asset_count": report["dedicated_asset_count"],
            "required_mastery_added_count": report["required_mastery_added_count"],
            "mapped_count": report["mapped_count"], "a2_lock_state": report["a2_lock_state"],
            "stop_reason": report["stop_reason"], "graph_output": str(result["graph_output"]),
            "consumer_output": str(result["consumer_output"]), "report_output": str(result["report_output"]),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (DedicatedBridgeError, overlay.OverlayError, bridge.BridgeError, m6.ResponseEvidenceError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
