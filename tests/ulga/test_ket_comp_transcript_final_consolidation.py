from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_ket_comp_transcript_final_consolidation as builder
from ulga.validators import validate_ket_comp_transcript_final_consolidation as validator

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ulga/reports/ket_comp_transcript_final_consolidation/transcript_source_manifest.json"
SRT_SCHEMA = ROOT / "ulga/schemas/ket99_srt_source_manifest.schema.json"


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


def _write_srt_corpus(root: Path) -> None:
    root.mkdir(parents=True)
    for number in range(4, 103):
        if number == 58:
            name = (
                "[P058]058.KET综合练-U7-62 复习-B站 "
                "咸咸的闲人MinYeah.ai-zh.srt"
            )
        elif number == 102:
            name = (
                "[P102]102.KET 系统梳理课 总复习-B站 "
                "咸咸的闲人MinYeah.ai-zh.srt"
            )
        else:
            name = (
                f"[P{number:03d}]{number:03d}.KET综-U1-P{number}-B站 "
                "咸咸的闲人MinYeah.ai-zh.srt"
            )
        text = f"transcript {number}"
        if number == 8:
            text = "阅读 关键词"
        elif number == 26:
            text = "dirty clean expensive cheap light"
        srt = (
            "\ufeff1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            f"{text}\n"
        )
        (root / name).write_text(srt, encoding="utf-8")


def _build_srt_publication(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    raw = tmp_path / "raw"
    legacy = tmp_path / "legacy"
    public = tmp_path / "public"
    private = tmp_path / "private"
    _write_srt_corpus(raw)
    builder.build(MANIFEST, legacy)
    builder.build_from_srt(
        raw,
        private,
        public,
        legacy / builder.FILE_NAMES["content"],
    )
    return raw, private, public, legacy / builder.FILE_NAMES["content"]


def test_srt_one_shot_build_and_validation(tmp_path: Path) -> None:
    raw, private, public, semantic_seed = _build_srt_publication(tmp_path)
    report = validator.validate_srt_publication(
        raw,
        private,
        public,
        semantic_seed,
        schema_path=SRT_SCHEMA,
    )
    assert report["validation_status"] == validator.SRT_PASS_STATUS
    assert report["source_count"] == 99
    assert report["valid_source_count"] == 99
    assert report["duplicate_content_count"] == 0
    assert report["p008_resolution_status"] == "RESOLVED"
    assert report["p026_resolution_status"] == "RESOLVED"
    assert report["deterministic_rebuild_status"] == "PASS"
    manifest = json.loads(
        (public / builder.SRT_PUBLIC_FILE_NAMES["manifest"]).read_text(
            encoding="utf-8"
        )
    )
    review = next(
        row for row in manifest["sources"] if row["transcript_id"] == "P058"
    )
    assert review["textbook_page"] == 62
    assert review["lesson_type"] == "review"
    assert manifest["raw_source_root_persisted"] is False
    assert not (public / builder.SRT_PRIVATE_BODY_NAME).exists()


def test_srt_missing_source_fails_closed(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    _write_srt_corpus(raw)
    next(raw.glob("[[]P004]*.srt")).unlink()
    try:
        builder.intake_srt_corpus(raw)
    except ValueError as exc:
        assert "source_identity_range_invalid" in str(exc)
    else:
        raise AssertionError("missing source was not rejected")


def test_srt_duplicate_content_fails_closed(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    _write_srt_corpus(raw)
    p004 = next(raw.glob("[[]P004]*.srt"))
    p005 = next(raw.glob("[[]P005]*.srt"))
    p005.write_bytes(p004.read_bytes())
    try:
        builder.intake_srt_corpus(raw)
    except ValueError as exc:
        assert "duplicate_content_sha256" in str(exc)
    else:
        raise AssertionError("duplicate content was not rejected")


def test_srt_repository_export_governance(tmp_path: Path) -> None:
    _, _, public, _ = _build_srt_publication(tmp_path)
    public_files = list(public.iterdir())
    assert not any(path.suffix == ".srt" for path in public_files)
    assert not any(path.name.endswith(".private.jsonl") for path in public_files)
    for path in public_files:
        text = path.read_text(encoding="utf-8")
        assert "G:\\HomeWork\\KET99_RAW_SRT" not in text
        if path.suffix == ".json":
            value = json.loads(text)
            assert validator._scan_forbidden_public_keys(value) == []
        elif path.suffix == ".jsonl":
            for line in text.splitlines():
                if line.strip():
                    assert validator._scan_forbidden_public_keys(
                        json.loads(line)
                    ) == []
