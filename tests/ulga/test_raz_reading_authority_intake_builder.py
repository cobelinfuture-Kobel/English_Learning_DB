import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ulga.builders import build_raz_reading_authority_intake as builder
from ulga.validators.validate_raz_reading_authority_intake_schema import validate_payload


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def inventory_row(level: str, *, query_layer_ready: bool, query_layer_approved: bool) -> dict:
    return {
        "level": level,
        "normalized_level": level,
        "status": "READY_FOR_REUSE_UNIT_PIPELINE",
        "query_layer_ready": query_layer_ready,
        "query_layer_approved": query_layer_approved,
    }


def test_builder_maps_canonical_and_legacy_records_and_preserves_query_layer_state():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        inventory_path = base / "inventory.json"
        derived_root = base / "derived"
        output_path = base / "out.json"
        summary_path = base / "summary.json"
        validation_path = base / "validation.json"

        write_json(inventory_path, [
            inventory_row("A", query_layer_ready=True, query_layer_approved=True),
            inventory_row("W", query_layer_ready=False, query_layer_approved=False),
        ])

        write_jsonl(
            derived_root / "Level_A" / "enriched" / "raz_A_sentence_enriched.jsonl",
            [{
                "candidate_id": "RAZ_A_1001_CAND_000001",
                "text": "I see a cat.",
                "source_tags": {
                    "book_id": "1001",
                    "book_title": "Cats",
                    "page_number": 1,
                    "page_unit_id": "RAZ_A_1001_P001",
                },
                "linguistic_tags": {
                    "cefr_estimate": "Pre-A1",
                    "grammar_tags": ["simple_present"],
                    "sentence_pattern_tags": ["i_see_noun"],
                    "vocabulary_tags": [{"normalized_word": "cat"}],
                },
                "theme_tags": {"mapped_theme": "Animals"},
                "reuse_tags": {"reusability_tags": ["sentence_only"]},
                "qa_tags": {"warnings": []},
            }]
        )
        write_json(
            derived_root / "Level_A" / "enriched" / "raz_A_page_unit_enriched.json",
            [{
                "page_unit_id": "RAZ_A_1001_P001",
                "book_id": "1001",
                "page_number": 1,
                "sentence_candidate_ids": ["RAZ_A_1001_CAND_000001"],
                "text": "I see a cat.",
                "title": "Cats",
                "reuse_tags": {"reusability_tags": ["short_reading_seed"]},
                "qa_tags": {"warnings": []},
            }]
        )
        write_json(
            derived_root / "Level_A" / "enriched" / "raz_A_reuse_unit_enriched.json",
            [{
                "reuse_unit_id": "RAZ_A_1001_REUSE_000001",
                "source_page_unit_id": "RAZ_A_1001_P001",
                "book_id": "1001",
                "page_number": 1,
                "source_sentence_candidate_ids": ["RAZ_A_1001_CAND_000001"],
                "clean_text": "I see a cat.",
                "sentence_count": 1,
                "title": "Cats",
                "reuse_tags": {"reusability_tags": ["short_reading_seed"]},
                "qa_tags": {"warnings": []},
            }]
        )

        write_json(
            derived_root / "Level_W" / "normalized" / "raz_W_normalized_sentences.json",
            {"records": [{
                "sentence_uid": "raz_W_4301_s0001",
                "book_id": "4301",
                "page_number": 7,
                "text": "Storm winds push inland."
            }]}
        )
        write_json(
            derived_root / "Level_W" / "normalized" / "raz_W_normalized_page_units.json",
            {"records": [{
                "page_unit_uid": "raz_W_4301_p0001",
                "book_id": "4301",
                "page_number": 7,
                "sentence_uids": ["raz_W_4301_s0001"]
            }]}
        )
        write_json(
            derived_root / "Level_W" / "normalized" / "raz_W_normalized_reuse_units.json",
            {"records": [{
                "reuse_unit_uid": "raz_W_4301_r0001",
                "book_id": "4301",
                "page_range": [7, 7],
                "sentence_uids": ["raz_W_4301_s0001"]
            }]}
        )
        write_json(
            derived_root / "Level_W" / "enriched" / "raz_W_enriched_sentences.json",
            {"records": [{
                "sentence_uid": "raz_W_4301_s0001",
                "book_uid": "raz_W_4301",
                "level": "W",
                "text": "Storm winds push inland.",
                "candidate_vocab_refs": [],
                "candidate_grammar_refs": [],
                "candidate_pattern_refs": [],
                "review_status": "pending"
            }]}
        )
        write_json(
            derived_root / "Level_W" / "enriched" / "raz_W_enriched_units.json",
            {"records": [
                {
                    "unit_uid": "raz_W_4301_p0001",
                    "unit_type": "page_unit",
                    "book_uid": "raz_W_4301",
                    "level": "W",
                    "sentence_uids": ["raz_W_4301_s0001"],
                    "unit_sentence_count": 1,
                    "candidate_use_cases": ["reading"],
                    "candidate_reuse_tags": ["page_unit"],
                    "review_status": "pending"
                },
                {
                    "unit_uid": "raz_W_4301_r0001",
                    "unit_type": "reuse_unit",
                    "book_uid": "raz_W_4301",
                    "level": "W",
                    "sentence_uids": ["raz_W_4301_s0001"],
                    "unit_sentence_count": 1,
                    "candidate_use_cases": ["reading"],
                    "candidate_reuse_tags": ["multi_sentence_unit"],
                    "review_status": "pending"
                }
            ]}
        )

        payload, summary, validation = builder.build_and_write_artifacts(
            inventory_path=inventory_path,
            derived_root=derived_root,
            output_path=output_path,
            summary_path=summary_path,
            validation_path=validation_path,
        )

        assert validation["status"] == "PASS"
        assert summary["records_by_unit_type"] == {"sentence": 2, "page_unit": 2, "reuse_unit": 2}
        assert summary["query_layer_ready_levels"] == ["A"]
        records = payload["records"]
        assert any(record["source_level"] == "W" and record["query_layer_ready"] is False for record in records)
        assert validate_payload(payload)["status"] == "PASS"


def test_builder_blocks_generated_content_and_duplicate_ids():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        inventory_path = base / "inventory.json"
        derived_root = base / "derived"
        output_path = base / "out.json"
        summary_path = base / "summary.json"
        validation_path = base / "validation.json"

        write_json(inventory_path, [inventory_row("A", query_layer_ready=True, query_layer_approved=True)])
        duplicate_record = {
            "candidate_id": "RAZ_A_1001_CAND_000001",
            "text": "I see a cat.",
            "source_tags": {
                "book_id": "1001",
                "book_title": "Cats",
                "page_number": 1,
                "page_unit_id": "RAZ_A_1001_P001",
            },
            "linguistic_tags": {
                "cefr_estimate": "Pre-A1",
                "grammar_tags": ["simple_present"],
                "sentence_pattern_tags": ["i_see_noun"],
                "vocabulary_tags": [{"normalized_word": "cat"}],
            },
            "theme_tags": {"mapped_theme": "Animals"},
            "reuse_tags": {"reusability_tags": ["sentence_only"]},
            "qa_tags": {"warnings": []},
        }
        write_jsonl(
            derived_root / "Level_A" / "enriched" / "raz_A_sentence_enriched.jsonl",
            [
                duplicate_record,
                dict(duplicate_record),
                {
                    "candidate_id": "RAZ_A_1001_CAND_000002",
                    "text": "Generated sentence.",
                    "generated_content": True,
                    "source_tags": {
                        "book_id": "1001",
                        "book_title": "Cats",
                        "page_number": 1,
                        "page_unit_id": "RAZ_A_1001_P001",
                    },
                    "linguistic_tags": {},
                    "theme_tags": {},
                    "reuse_tags": {"reusability_tags": ["sentence_only"]},
                    "qa_tags": {"warnings": []},
                }
            ]
        )
        write_json(derived_root / "Level_A" / "enriched" / "raz_A_page_unit_enriched.json", [])
        write_json(derived_root / "Level_A" / "enriched" / "raz_A_reuse_unit_enriched.json", [])

        payload, summary, validation = builder.build_and_write_artifacts(
            inventory_path=inventory_path,
            derived_root=derived_root,
            output_path=output_path,
            summary_path=summary_path,
            validation_path=validation_path,
        )

        assert len(payload["records"]) == 1
        assert summary["blocked_record_count"] == 2
        assert validation["duplicate_id_count"] == 1
        assert any("generated_content_flagged" in row["reasons"] for row in validation["blocked_records"])


def test_builder_script_and_schema_validator_cli_pass():
    result = subprocess.run(
        [sys.executable, str(builder.BASE_DIR / "ulga" / "builders" / "build_raz_reading_authority_intake.py")],
        cwd=builder.BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    validator = subprocess.run(
        [
            sys.executable,
            str(builder.BASE_DIR / "ulga" / "validators" / "validate_raz_reading_authority_intake_schema.py"),
            "ulga/graph/raz_reading_authority_intake_candidates.json",
        ],
        cwd=builder.BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert validator.returncode == 0, validator.stdout + validator.stderr
