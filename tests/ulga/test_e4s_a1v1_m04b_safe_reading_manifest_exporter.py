from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import export_a1_a1plus_safe_reading_source_manifest as exporter


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_exporter_emits_metadata_without_source_text(tmp_path):
    source_root = tmp_path / "raz_output_jsons"
    _write_json(
        source_root / "derived" / "Level_A" / "normalized" / "units.json",
        {
            "items": [
                {
                    "reading_intake_id": "RAZ_A_BOOK1_UNIT1",
                    "source_level": "A",
                    "book_id": "BOOK1",
                    "page_number": 3,
                    "clean_text": "I see a red cat. The cat can run.",
                    "tags": {
                        "theme_tags": ["animals"],
                        "grammar_tags": ["present_simple"],
                        "pattern_tags": ["I see ..."],
                        "vocabulary_tags": ["cat", "run"],
                        "reusability_tags": ["short_reading_seed"],
                    },
                }
            ]
        },
    )

    manifest = exporter.build_manifest(source_root, levels=["A", "B"])
    errors = exporter.validate_manifest(manifest)

    assert errors == []
    assert manifest["summary"]["manifest_record_count"] == 1
    record = manifest["records"][0]
    assert record["source_unit_ref"] == "RAZ_A_BOOK1_UNIT1"
    assert record["source_level"] == "A"
    assert record["sentence_count"] == 2
    assert record["word_count"] == 9
    assert record["theme_tags"] == ["animals"]
    assert record["grammar_tags"] == ["present_simple"]
    assert record["source_policy"]["metadata_and_hashes_only"] is True

    serialized = json.dumps(manifest, ensure_ascii=False)
    assert "I see a red cat" not in serialized
    assert "The cat can run" not in serialized
    assert '"clean_text"' not in serialized
    assert '"passage_text"' not in serialized


def test_exporter_filters_levels_and_skips_audio_timeline(tmp_path):
    source_root = tmp_path / "raz_output_jsons"
    _write_json(
        source_root / "Level_A" / "a.json",
        {"id": "A1", "level": "A", "text": "A short sentence."},
    )
    _write_json(
        source_root / "Level_G" / "g.json",
        {"id": "G1", "level": "G", "text": "A later sentence."},
    )
    _write_json(
        source_root / "Level_A" / "audio_timeline_extract.json",
        {"id": "AUDIO1", "level": "A", "text": "Do not include this."},
    )

    manifest = exporter.build_manifest(source_root, levels=["A"])

    assert manifest["summary"]["manifest_record_count"] == 1
    assert [row["source_unit_ref"] for row in manifest["records"]] == ["A1"]
    assert manifest["summary"]["levels"] == {"A": 1}


def test_exporter_supports_jsonl_and_stable_evidence_hash(tmp_path):
    source_root = tmp_path / "raz_output_jsons"
    path = source_root / "derived" / "Level_B" / "enriched" / "units.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "source_record_id": "B-001",
        "normalized_level": "B",
        "source_type": "enriched_reading_unit",
        "reading_text": "We play in the park.",
        "pedagogical_tags": {"theme_tags": ["park"]},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    first = exporter.build_manifest(source_root)
    second = exporter.build_manifest(source_root)

    assert exporter.validate_manifest(first) == []
    assert first["records"] == second["records"]
    evidence = first["records"][0]["evidence_refs"]
    assert any(value.startswith("record_sha256:") for value in evidence)


def test_validator_fails_closed_on_text_key_in_manifest(tmp_path):
    source_root = tmp_path / "raz_output_jsons"
    _write_json(
        source_root / "Level_C" / "c.json",
        {"id": "C1", "level": "C", "text": "This stays local."},
    )
    manifest = exporter.build_manifest(source_root)
    manifest["records"][0]["display_text"] = "Leaked text"

    errors = exporter.validate_manifest(manifest)

    assert any("forbidden_text_key_in_manifest" in error for error in errors)


def test_validator_requires_at_least_one_record_by_default(tmp_path):
    source_root = tmp_path / "raz_output_jsons"
    source_root.mkdir()

    manifest = exporter.build_manifest(source_root)

    assert exporter.validate_manifest(manifest) == ["manifest_has_no_records"]
    assert exporter.validate_manifest(manifest, require_records=False) == []
