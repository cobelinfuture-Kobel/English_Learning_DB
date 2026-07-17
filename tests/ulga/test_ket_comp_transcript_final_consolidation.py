from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_ket_comp_transcript_final_consolidation as builder
from ulga.validators import validate_ket_comp_transcript_final_consolidation as validator

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ulga/reports/ket_comp_transcript_final_consolidation/transcript_source_manifest.json"


def build_output(tmp_path: Path) -> Path:
    out = tmp_path / "output"
    result = builder.build(MANIFEST, out)
    assert result["source_count"] == 99
    return out


def test_build_and_validate_all_99(tmp_path: Path) -> None:
    out = build_output(tmp_path)
    report = validator.validate(MANIFEST, out)
    assert report["validation_status"] == validator.PASS_STATUS
    assert report["registry_source_count"] == 99
    assert report["content_unit_count"] == 99
    assert report["reuse_candidate_count"] == 99
    assert report["admission_decision_count"] == 101
    assert report["raw_hash_verified_count"] == 0
    assert report["raw_hash_evidence_count"] == 99
    assert report["raw_hash_verification_mode"] == "committed_evidence"
    assert report["batch_hash_verified_count"] == 0
    assert report["batch_hash_evidence_count"] == 99
    assert report["batch_hash_verification_mode"] == "committed_evidence"


def test_manifest_range_is_exact() -> None:
    manifest = builder.load_manifest(MANIFEST)
    numbers = [row[0] for row in manifest["sources"]]
    assert numbers == list(range(4, 103))


def test_orphan_reuse_reference_fails(tmp_path: Path) -> None:
    out = build_output(tmp_path)
    path = out / builder.FILE_NAMES["reuse"]
    value = json.loads(path.read_text(encoding="utf-8"))
    value["candidates"][0]["source_content_unit_ids"] = ["MISSING"]
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    report = validator.validate(MANIFEST, out)
    assert report["error_count"] > 0
    assert any("orphan reuse" in error for error in report["errors"])


def test_canonical_approval_fails(tmp_path: Path) -> None:
    out = build_output(tmp_path)
    path = out / builder.FILE_NAMES["admission"]
    value = json.loads(path.read_text(encoding="utf-8"))
    value["decisions"][0]["decisions"]["canonical_grammar_authority"] = "approved"
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    report = validator.validate(MANIFEST, out)
    assert any("canonical approval" in error for error in report["errors"])


def test_deterministic_rebuild(tmp_path: Path) -> None:
    first = build_output(tmp_path / "first")
    second = build_output(tmp_path / "second")
    for filename in builder.FILE_NAMES.values():
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_strict_raw_tamper_is_detected(tmp_path: Path) -> None:
    out = build_output(tmp_path)
    registry = json.loads((out / builder.FILE_NAMES["registry"]).read_text(encoding="utf-8"))
    raw = tmp_path / "raw"
    raw.mkdir()
    for row in registry["sources"]:
        (raw / row["source_filename"]).write_text("placeholder", encoding="utf-8")
    report = validator.validate(MANIFEST, out, raw_source_dir=raw)
    assert report["error_count"] > 0
    assert any("raw source hash mismatch" in error for error in report["errors"])
