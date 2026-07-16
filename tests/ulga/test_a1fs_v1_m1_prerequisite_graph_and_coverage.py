from __future__ import annotations

import copy
import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

import pytest
from openpyxl import Workbook

from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as builder
from ulga.validators import validate_a1fs_v1_m1_prerequisite_graph_and_coverage as validator


def _zip(path: Path, members: dict[str, bytes | str]) -> Path:
    with ZipFile(path, "w", ZIP_STORED) as archive:
        for name, value in members.items():
            archive.writestr(name, value)
    return path


def _writing_book(targets: tuple[str, str, str] = ("A1W-01", "A1PW-01", "KW-001")) -> bytes:
    workbook = Workbook(); sheet = workbook.active; sheet.title = "AssetBodies"
    sheet.append(["fixture"]); sheet.append([]); sheet.append([])
    sheet.append(["asset_id", "lesson_id", "unit", "stage", "sequence", "role", "capability_targets"])
    rows = (
        ("W-A1", "KLSN-WF00-L01", "WF00", "A1 WF", 1, targets[0]),
        ("W-A1P", "KLSN-WB01-L01", "WB01", "A1+ WB", 1, targets[1]),
        ("W-A2", "KLSN-KP00-L01", "KP00", "A2 KP", 1, targets[2]),
    )
    for asset, lesson, unit, stage, sequence, target in rows:
        sheet.append([asset, lesson, unit, stage, sequence, "EVD", target])
    stream = BytesIO(); workbook.save(stream); return stream.getvalue()


def _rows(skill: str) -> list[dict]:
    if skill == "LISTENING":
        return [
            {"asset_body_id": "L-A1", "lesson_id": "KETL-LF-L001", "role": "EVD", "target_refs": ["KETL-A1-TASK-001"], "candidate_resource_refs": ["POP-EVP-0001"]},
            {"asset_body_id": "L-A1P", "lesson_id": "KETL-LB-L001", "role": "EVD", "target_refs": ["KETL-A1P-TASK-001"], "candidate_resource_refs": []},
            {"asset_body_id": "L-A2", "lesson_id": "KETL-KL-L001", "role": "EVD", "target_refs": ["KL-P1-001"], "candidate_resource_refs": []},
        ]
    if skill == "READING":
        return [
            {"asset_body_id": "R-A1", "lesson_id": "KETR-RF-00-L01", "role": "EVD", "target_refs": ["KETR-A1R-001"], "supporting_target_refs": ["KRR-SH-001"]},
            {"asset_body_id": "R-A1P", "lesson_id": "KETR-RB-00-L01", "role": "EVD", "target_refs": ["KETR-A1PR-001"], "supporting_target_refs": []},
            {"asset_body_id": "R-A2", "lesson_id": "KETR-KR-00-L01", "role": "EVD", "target_refs": ["KRR-P1-001"], "supporting_target_refs": []},
        ]
    return [
        {"asset_body_id": "S-A1", "lesson_id": "SF-00-L01", "role": "EVD", "level": "A1", "resource_refs": ["EGP-SPK-001", "SIT-01"]},
        {"asset_body_id": "S-A1P", "lesson_id": "SB-00-L01", "role": "EVD", "level": "A1+", "resource_refs": ["EVP-SPK-001"]},
        {"asset_body_id": "S-A2", "lesson_id": "KP-00-L01", "role": "EVD", "level": "A2", "resource_refs": ["PRON-01"]},
    ]


def _fixture(tmp_path: Path, writing_targets: tuple[str, str, str] = ("A1W-01", "A1PW-01", "KW-001")) -> tuple[dict[str, Path], Path]:
    paths = {
        "WRITING": _zip(tmp_path / "writing.zip", {builder.WRITING_LEDGER if hasattr(builder, "WRITING_LEDGER") else "outputs/ketw_asset_body/KETW_AB_Asset_Body_Per_Asset_Admission_Ledger_v1.0.0.xlsx": _writing_book(writing_targets)}),
        "READING": _zip(tmp_path / "reading.zip", {"ketr_asset_body_production/data/asset_body_registry.json": json.dumps({"asset_bodies": _rows("READING")})}),
        "SPEAKING": _zip(tmp_path / "speaking.zip", {"07_KETS_AB/data/asset_body_registry.json": json.dumps({"asset_bodies": _rows("SPEAKING")})}),
        "LISTENING": _zip(tmp_path / "listening.zip", {"ketl_asset_body_production/data/asset_body_registry.json": json.dumps({"rows": _rows("LISTENING")})}),
    }
    packages = []
    for skill, path in paths.items():
        packages.append({
            "skill": skill, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "counts": {"lessons": 3, "asset_bodies": 3, "teacher_guides": 3},
        })
    baseline = {
        "validation_status": builder.BASELINE_STATUS, "packages": packages,
        "totals": {"lessons": 12, "asset_bodies": 12, "teacher_guides": 12},
    }
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    return paths, baseline_path


def _build(paths: dict[str, Path], baseline: Path) -> dict:
    return builder.build_graph(
        baseline_path=baseline, ketw=paths["WRITING"], ketr=paths["READING"],
        kets=paths["SPEAKING"], ketl=paths["LISTENING"],
    )


def test_builds_four_skill_a1_a1plus_graph_with_locked_a2(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path); graph = _build(paths, baseline)
    assert graph["validation_status"] == builder.STATUS
    assert graph["counts"]["lesson_count_by_level"] == {"A1": 4, "A1+": 4, "A2": 4}
    assert graph["counts"]["required_mastery_node_count"] == 16
    assert graph["a2_lock_contract"]["state"] == "LOCKED_BY_DESIGN"
    assert graph["a2_lock_contract"]["runtime_unlock_implemented"] is False
    assert graph["claim_boundaries"]["mastery_claimed"] is False


def test_every_required_node_is_an_exact_global_gate_dependency(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path); graph = _build(paths, baseline)
    required = set(graph["a2_lock_contract"]["required_mastery_node_ids"])
    incoming = {edge["from_node_id"] for edge in graph["edges"] if edge["edge_type"] == "UNLOCK_REQUIRES"}
    assert incoming == required
    assert len(required) == graph["counts"]["required_mastery_node_count"]


def test_support_references_are_covered_without_becoming_hidden_requirements(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path); graph = _build(paths, baseline)
    support = next(node for node in graph["nodes"] if node["source_ref"] == "SIT-01")
    assert support["node_type"] == "SUPPORT_RESOURCE"
    assert support["mastery_required_before_a2"] is False
    row = next(row for row in graph["coverage"] if row["node_id"] == support["node_id"])
    assert row["coverage_status"] == "COVERED"


def test_writing_ranges_expand_to_atomic_mastery_nodes(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path, ("A1W-01–03", "A1PW-01/03", "KW-001"))
    graph = _build(paths, baseline)
    refs = {node["source_ref"] for node in graph["nodes"] if node["skill"] == "WRITING"}
    assert {"A1W-01", "A1W-02", "A1W-03", "A1PW-01", "A1PW-03"} <= refs


def test_package_hash_drift_fails_closed(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path)
    with ZipFile(paths["READING"], "a") as archive:
        archive.writestr("drift.txt", "drift")
    with pytest.raises(builder.GraphError, match="baseline_package_hash_mismatch:READING"):
        _build(paths, baseline)


def test_unparseable_writing_target_fails_closed(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path, ("not a target", "A1PW-01", "KW-001"))
    with pytest.raises(builder.GraphError, match="writing_target_unparseable"):
        _build(paths, baseline)


def test_independent_validator_passes_and_rechecks_private_packages(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path); graph = _build(paths, baseline)
    graph_path = tmp_path / "graph.json"; graph_path.write_text(json.dumps(graph), encoding="utf-8")
    report = validator.validate(graph_path, baseline, paths)
    assert report["error_count"] == 0, report["errors"]
    assert report["checked_package_count"] == 4


def test_validator_rejects_missing_required_coverage(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path); graph = _build(paths, baseline)
    tampered = copy.deepcopy(graph)
    required_ref = next(node for node in tampered["nodes"] if node["node_type"] == "CAPABILITY" and node["mastery_required_before_a2"])
    tampered["coverage"] = [row for row in tampered["coverage"] if row["node_id"] != required_ref["node_id"]]
    tampered["counts"]["coverage_record_count"] -= 1
    graph_path = tmp_path / "tampered.json"; graph_path.write_text(json.dumps(tampered), encoding="utf-8")
    report = validator.validate(graph_path, baseline, paths)
    assert report["error_count"] > 0
    assert any(error.startswith("required_node_uncovered:") for error in report["errors"])


def test_validator_rejects_a2_bypass_edge(tmp_path: Path) -> None:
    paths, baseline = _fixture(tmp_path); graph = _build(paths, baseline)
    tampered = copy.deepcopy(graph)
    source = next(node["node_id"] for node in tampered["nodes"] if node["node_type"] == "LESSON" and node["level"] == "A1+")
    target = next(node["node_id"] for node in tampered["nodes"] if node["node_type"] == "LESSON" and node["level"] == "A2")
    tampered["edges"].append({"from_node_id": source, "to_node_id": target, "edge_type": "PRECEDES"})
    tampered["counts"]["edge_count"] += 1
    graph_path = tmp_path / "bypass.json"; graph_path.write_text(json.dumps(tampered), encoding="utf-8")
    report = validator.validate(graph_path, baseline, paths)
    assert "a2_direct_sequence_bypasses_global_lock" in report["errors"]
