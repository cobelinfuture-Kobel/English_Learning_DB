import json
import tempfile
from pathlib import Path

from ulga.validators import validate_raz_reading_authority_intake_artifact_policy as policy


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_record(*, record_id: str, level: str, unit_type: str, source_type: str, page_number: int, page_unit_id: str, sentence_ids: list[str], clean_text: str, query_layer_ready: bool, qa_warnings: list[str]) -> dict:
    return {
        "reading_intake_id": record_id,
        "schema_version": "raz_reading_authority_intake.v1",
        "source": "RAZ",
        "source_level": level,
        "normalized_level": level,
        "unit_type": unit_type,
        "source_traceability": {
            "source_type": source_type,
            "source_artifact_path": f"raz_output_jsons/derived/Level_{level}/enriched/example.json",
            "source_record_id": record_id.replace("_SENT_", "_CAND_").replace("_PAGE_", "_P").replace("_REUSE_", "_REUSE_"),
            "book_id": "1001",
            "book_title": "Sample Book",
            "page_number": page_number,
            "page_unit_id": page_unit_id,
            "source_sentence_candidate_ids": sentence_ids,
            "derived_from_original_text": True,
            "generated_content": False,
        },
        "text": {
            "clean_text": clean_text,
            "sentence_count": 1,
            "word_count": len(clean_text.rstrip(".").split()),
            "text_language": "en",
            "text_role": "reading_source_text",
        },
        "pedagogical_tags": {
            "raz_level": level,
            "cefr_estimate": None,
            "theme_tags": [],
            "vocabulary_tags": [],
            "grammar_tags": [],
            "pattern_tags": [],
            "skill_area": ["reading"],
            "reusability_tags": ["short_reading_seed"],
        },
        "authority": {
            "authority_status": "candidate_only",
            "promotion_status": "not_promoted",
            "promotion_allowed": False,
            "requires_review": True,
            "review_status": "pending",
            "final_eligible": False,
        },
        "qa": {
            "blocked": False,
            "block_reasons": [],
            "warnings": qa_warnings,
            "source_integrity_status": "pass",
            "generated_content_block_status": "pass",
        },
        "query_layer_ready": query_layer_ready,
        "query_layer_approved": query_layer_ready,
    }


def test_build_all_reports_handles_present_artifact_and_required_taxonomy_categories():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        artifact_path = base / "ulga" / "graph" / "raz_reading_authority_intake_candidates.json"
        gitignore_path = base / ".gitignore"
        builder_summary_path = base / "builder_summary.json"
        builder_validation_path = base / "builder_validation.json"
        manifest_path = base / "manifest.json"
        taxonomy_path = base / "taxonomy.json"
        qa_summary_path = base / "qa_summary.json"
        qa_validation_path = base / "qa_validation.json"

        records = [
            sample_record(
                record_id="RAZ_A_1001_SENT_000001",
                level="A",
                unit_type="sentence",
                source_type="raz_enriched_sentence",
                page_number=1,
                page_unit_id="RAZ_A_1001_P001",
                sentence_ids=["RAZ_A_1001_CAND_000001"],
                clean_text="I see a cat.",
                query_layer_ready=True,
                qa_warnings=[],
            ),
            sample_record(
                record_id="RAZ_W_1001_PAGE_000001",
                level="W",
                unit_type="page_unit",
                source_type="raz_enriched_page_unit",
                page_number=7,
                page_unit_id="RAZ_W_1001_P007",
                sentence_ids=["RAZ_W_1001_CAND_000041"],
                clean_text="Storm winds push inland.",
                query_layer_ready=False,
                qa_warnings=[
                    "mapped_legacy_reusability_tag:page_unit->short_reading_seed",
                    "unknown_theme",
                ],
            ),
            sample_record(
                record_id="RAZ_K_1001_SENT_000001",
                level="K",
                unit_type="sentence",
                source_type="raz_enriched_sentence",
                page_number=4,
                page_unit_id="RAZ_K_1001_P004",
                sentence_ids=["RAZ_K_1001_CAND_000010"],
                clean_text="Plants need water.",
                query_layer_ready=True,
                qa_warnings=[
                    "unsupported_reusability_tag:single_sentence",
                    "unknown_pattern",
                    "unknown_grammar",
                    "section_heading_detected",
                ],
            ),
        ]

        write_json(artifact_path, {
            "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
            "schema_version": "raz_reading_authority_intake.v1",
            "records": records,
        })
        gitignore_path.write_text(policy.REQUIRED_GITIGNORE_ENTRY + "\n", encoding="utf-8")
        write_json(builder_summary_path, {
            "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
            "status": "IMPLEMENTED",
            "total_records": 3,
            "warning_count": 23,
        })
        write_json(builder_validation_path, {
            "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
            "status": "PASS",
            "warnings": [
                "cefr_estimate missing",
                "mapped_legacy_reusability_tag:page_unit->short_reading_seed",
                "query_layer_ready false for G-W is not a schema blocker",
                "section_heading_detected",
                "unknown_grammar",
                "unknown_pattern",
                "unknown_theme",
                "unsupported_reusability_tag:single_sentence",
            ],
        })

        manifest, taxonomy, qa_summary, qa_validation = policy.build_all_reports(
            artifact_path=artifact_path,
            gitignore_path=gitignore_path,
            builder_summary_path=builder_summary_path,
            builder_validation_path=builder_validation_path,
            manifest_path=manifest_path,
            taxonomy_path=taxonomy_path,
            qa_summary_path=qa_summary_path,
            qa_validation_path=qa_validation_path,
        )

        assert manifest["artifact_status"] == "LOCAL_ONLY"
        assert manifest["git_policy"] == "do_not_commit"
        assert manifest["gitignore_status"] == "PASS"
        assert manifest["content_hash_sha256"]

        categories = {item["category"]: item for item in taxonomy["warning_categories"]}
        for required in [
            "MISSING_CEFR_ESTIMATE",
            "SPARSE_PEDAGOGICAL_TAGS",
            "LEGACY_TAG_COMPATIBILITY_MAPPED",
            "UNSUPPORTED_LEGACY_REUSABILITY_TAG",
            "MISSING_WORD_COUNT_OR_DERIVED_WORD_COUNT",
            "QUERY_LAYER_NOT_READY_G_TO_W",
            "S6B_PARITY_NOTE_INHERITED",
        ]:
            assert required in categories
        assert categories["SPARSE_PEDAGOGICAL_TAGS"]["blocking"] is False
        assert categories["MISSING_CEFR_ESTIMATE"]["count"] == 3
        assert categories["QUERY_LAYER_NOT_READY_G_TO_W"]["count"] == 1
        assert categories["S6B_PARITY_NOTE_INHERITED"]["count"] == 1
        assert taxonomy["warning_count_reconciliation_status"] == "PASS"
        assert taxonomy["recomputed_source_warning_count"] == 23

        assert qa_summary["promotion_allowed"] is False
        assert qa_summary["authority_status"] == "candidate_only"
        assert qa_validation["status"] == "PASS"


def test_build_artifact_manifest_handles_absent_artifact():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        artifact_path = base / "missing.json"
        gitignore_path = base / ".gitignore"
        gitignore_path.write_text(policy.REQUIRED_GITIGNORE_ENTRY + "\n", encoding="utf-8")

        manifest = policy.build_artifact_manifest(
            artifact_path=artifact_path,
            gitignore_path=gitignore_path,
            builder_summary={"total_records": 3, "status": "PASS"},
        )

        assert manifest["artifact_status"] == "LOCAL_ARTIFACT_NOT_PRESENT"
        assert manifest["hash_status"] == "NOT_COMPUTED"
        assert manifest["size_bytes"] is None
        assert manifest["size_mb"] is None
