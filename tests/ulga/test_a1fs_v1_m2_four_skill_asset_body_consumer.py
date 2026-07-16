from __future__ import annotations

import copy
import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

import pytest
from openpyxl import Workbook

from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.validators import validate_a1fs_v1_m2_four_skill_asset_body_consumer as validator


def _zip(path: Path, member: str, value: bytes | str) -> Path:
    with ZipFile(path, "w", ZIP_STORED) as archive: archive.writestr(member, value)
    return path


def _writing() -> bytes:
    workbook = Workbook(); sheet = workbook.active; sheet.title = "AssetBodies"
    sheet.append(["fixture"]); sheet.append([]); sheet.append([])
    sheet.append(["asset_id", "lesson_id", "unit", "stage", "sequence", "role", "capability_targets", "body_title", "body_text", "expected_evidence"])
    for row in (
        ("W-A1", "KLSN-WF00-L01", "WF00", "A1 WF", "A1W-01"),
        ("W-A1P", "KLSN-WB01-L01", "WB01", "A1+ WB", "A1PW-01"),
        ("W-A2", "KLSN-KP00-L01", "KP00", "A2 KP", "KW-001"),
    ):
        asset, lesson, unit, stage, target = row
        sheet.append([asset, lesson, unit, stage, 1, "EVD", target, f"{asset} title", f"{asset} private body", "observable evidence"])
    stream = BytesIO(); workbook.save(stream); return stream.getvalue()


def _rows(skill: str) -> list[dict]:
    specs = {
        "LISTENING": (("L-A1", "KETL-LF-L001", None, "KETL-A1-TASK-001"), ("L-A1P", "KETL-LB-L001", None, "KETL-A1P-TASK-001"), ("L-A2", "KETL-KL-L001", None, "KL-P1-001")),
        "READING": (("R-A1", "KETR-RF-00-L01", None, "KETR-A1R-001"), ("R-A1P", "KETR-RB-00-L01", None, "KETR-A1PR-001"), ("R-A2", "KETR-KR-00-L01", None, "KRR-P1-001")),
        "SPEAKING": (("S-A1", "SF-00-L01", "A1", "EGP-SPK-001"), ("S-A1P", "SB-00-L01", "A1+", "EVP-SPK-001"), ("S-A2", "KP-00-L01", "A2", "PRON-01")),
    }
    rows = []
    for asset, lesson, level, ref in specs[skill]:
        row = {"asset_body_id": asset, "lesson_id": lesson, "role": "EVD", "body": {"prompt": f"private {asset}"}}
        if skill == "LISTENING": row.update(target_refs=[ref], candidate_resource_refs=[])
        elif skill == "READING": row.update(target_refs=[ref], supporting_target_refs=[])
        else: row.update(level=level, resource_refs=[ref])
        rows.append(row)
    return rows


def _fixture(tmp_path: Path) -> tuple[dict[str, Path], Path, Path]:
    paths = {
        "WRITING": _zip(tmp_path / "w.zip", "outputs/ketw_asset_body/KETW_AB_Asset_Body_Per_Asset_Admission_Ledger_v1.0.0.xlsx", _writing()),
        "READING": _zip(tmp_path / "r.zip", "ketr_asset_body_production/data/asset_body_registry.json", json.dumps({"asset_bodies": _rows("READING")})),
        "SPEAKING": _zip(tmp_path / "s.zip", "07_KETS_AB/data/asset_body_registry.json", json.dumps({"asset_bodies": _rows("SPEAKING")})),
        "LISTENING": _zip(tmp_path / "l.zip", "ketl_asset_body_production/data/asset_body_registry.json", json.dumps({"rows": _rows("LISTENING")})),
    }
    baseline = {"validation_status": m1.BASELINE_STATUS, "packages": [{"skill": skill, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "counts": {"lessons": 3, "asset_bodies": 3, "teacher_guides": 3}} for skill, path in paths.items()]}
    baseline_path = tmp_path / "baseline.json"; baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    graph = m1.build_graph(baseline_path=baseline_path, ketw=paths["WRITING"], ketr=paths["READING"], kets=paths["SPEAKING"], ketl=paths["LISTENING"])
    graph_path = tmp_path / "graph.json"; graph_path.write_text(json.dumps(graph), encoding="utf-8")
    return paths, baseline_path, graph_path


def _build(paths: dict[str, Path], baseline: Path, graph: Path) -> dict:
    return m2.build_index(graph_path=graph, baseline_path=baseline, ketw=paths["WRITING"], ketr=paths["READING"], kets=paths["SPEAKING"], ketl=paths["LISTENING"])


def test_builds_queryable_private_four_skill_index(tmp_path: Path) -> None:
    paths, baseline, graph = _fixture(tmp_path); index = _build(paths, baseline, graph)
    assert index["counts"] == {"asset_record_count": 12, "lesson_count": 12, "learning_lesson_count": 8, "a2_handoff_lesson_count": 4}
    result = m2.query_index(index, skill="READING", level="A1")
    assert result["total_match_count"] == 1
    assert result["asset_records"][0]["payload"]["prompt"] == "private R-A1"
    assert result["a2_payload_included"] is False


def test_requirement_node_query_resolves_covered_lessons(tmp_path: Path) -> None:
    paths, baseline, graph = _fixture(tmp_path); index = _build(paths, baseline, graph)
    result = m2.query_index(index, requirement_node_id="REF:LISTENING:KETL-A1-TASK-001")
    assert result["total_match_count"] == 1
    assert result["asset_records"][0]["lesson_id"] == "KETL-LF-L001"


def test_a2_payload_is_fail_closed_by_level_and_lesson(tmp_path: Path) -> None:
    paths, baseline, graph = _fixture(tmp_path); index = _build(paths, baseline, graph)
    with pytest.raises(m2.ConsumerError, match="A2_PAYLOAD_LOCKED"):
        m2.query_index(index, level="A2")
    with pytest.raises(m2.ConsumerError, match="A2_PAYLOAD_LOCKED"):
        m2.query_index(index, lesson_id="KETL-KL-L001")


def test_a2_handoff_is_metadata_only(tmp_path: Path) -> None:
    paths, baseline, graph = _fixture(tmp_path); index = _build(paths, baseline, graph)
    result = m2.a2_handoff_metadata(index, skill="WRITING")
    assert result["lesson_count"] == 1
    assert result["lessons"][0]["payload_exposed"] is False
    assert "asset_keys" not in result["lessons"][0]


def test_query_pagination_limit_is_bounded(tmp_path: Path) -> None:
    paths, baseline, graph = _fixture(tmp_path); index = _build(paths, baseline, graph)
    with pytest.raises(m2.ConsumerError, match="query_page_invalid"):
        m2.query_index(index, limit=101)


def test_independent_validator_rechecks_index_and_sources(tmp_path: Path) -> None:
    paths, baseline, graph = _fixture(tmp_path); index = _build(paths, baseline, graph)
    index_path = tmp_path / "index.json"; index_path.write_text(json.dumps(index), encoding="utf-8")
    report = validator.validate(index_path, graph, baseline, paths)
    assert report["error_count"] == 0, report["errors"]


def test_validator_rejects_payload_tampering(tmp_path: Path) -> None:
    paths, baseline, graph = _fixture(tmp_path); index = _build(paths, baseline, graph)
    tampered = copy.deepcopy(index); tampered["asset_records"][0]["payload"]["prompt"] = "changed"
    index_path = tmp_path / "tampered.json"; index_path.write_text(json.dumps(tampered), encoding="utf-8")
    report = validator.validate(index_path, graph, baseline, paths)
    assert any(error.startswith("asset_digest_invalid:") for error in report["errors"])
