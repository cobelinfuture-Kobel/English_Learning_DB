import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

INVENTORY_PATH = BASE_DIR / "ulga" / "graph" / "corpus_source_inventory.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "corpus_source_inventory_summary.json"

ALLOWED_SOURCE_ROLES = {
    "authority_source",
    "normalized_authority_artifact",
    "external_reference_corpus",
    "experimental_pilot_output",
    "future_candidate_corpus",
    "blocked_or_missing_source",
}
ALLOWED_STATUSES = {
    "present",
    "present_with_warnings",
    "missing",
    "blocked",
    "deprecated",
    "future_candidate",
}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def relative_path(path):
    return path.relative_to(BASE_DIR).as_posix()


def detect_format(path):
    if not path:
        return "unknown"
    if path.suffix == ".xlsx":
        return "xlsx"
    if path.suffix == ".json":
        return "json"
    if path.suffix == ".md":
        return "md"
    if path.is_dir():
        if path.parts[-2:] and len(path.parts) >= 2 and path.parts[-2] == "pdf":
            return "pdf_folder"
        return "unknown"
    return "unknown"


def normalize_strings(values):
    return [str(value) for value in values]


def make_record(
    *,
    source_id,
    source_family,
    source_role,
    status,
    path,
    exists,
    direct_use_allowed,
    authority_import_allowed,
    content_extraction_allowed,
    learner_facing_allowed,
    license_status,
    review_status,
    notes=None,
    risk_flags=None,
):
    notes = normalize_strings(notes or [])
    risk_flags = normalize_strings(risk_flags or [])
    return {
        "source_id": source_id,
        "source_family": source_family,
        "source_role": source_role,
        "status": status,
        "path": path,
        "format": detect_format(BASE_DIR / path) if path and not path.startswith("future_candidate/") else "unknown",
        "exists": exists,
        "direct_use_allowed": direct_use_allowed,
        "authority_import_allowed": authority_import_allowed,
        "content_extraction_allowed": content_extraction_allowed,
        "learner_facing_allowed": learner_facing_allowed,
        "license_status": license_status,
        "review_status": review_status,
        "notes": notes,
        "risk_flags": risk_flags,
    }


def path_record(
    *,
    source_id,
    source_family,
    source_role,
    rel_path,
    direct_use_allowed,
    authority_import_allowed,
    content_extraction_allowed,
    learner_facing_allowed,
    license_status,
    review_status,
    missing_status="missing",
    notes=None,
    risk_flags=None,
):
    path = BASE_DIR / rel_path
    exists = path.exists()
    status = "present" if exists else missing_status
    path_notes = list(notes or [])
    path_risks = list(risk_flags or [])
    if not exists and missing_status == "missing":
        path_risks.append("path_not_found")
    return make_record(
        source_id=source_id,
        source_family=source_family,
        source_role=source_role,
        status=status,
        path=rel_path,
        exists=exists,
        direct_use_allowed=direct_use_allowed,
        authority_import_allowed=authority_import_allowed,
        content_extraction_allowed=content_extraction_allowed,
        learner_facing_allowed=learner_facing_allowed,
        license_status=license_status,
        review_status=review_status,
        notes=path_notes,
        risk_flags=path_risks,
    )


def raz_pdf_folder_record(level):
    rel_path = f"input/pdf/{level.lower()}"
    path = BASE_DIR / rel_path
    exists = path.exists()
    pdf_count = len(list(path.glob("*.pdf"))) if exists and path.is_dir() else 0
    notes = [f"raz_level={level}", f"pdf_file_count={pdf_count}"]
    risk_flags = []
    if exists and pdf_count > 0:
        status = "present" if level == "A" else "present_with_warnings"
        if level != "A":
            risk_flags.append("cross_level_reference_corpus_present_requires_policy_review")
            notes.append("folder has PDFs but remains external_reference_corpus only")
    elif exists:
        status = "blocked"
        risk_flags.extend(["empty_pdf_folder", "folder_exists_without_pdf_assets"])
        notes.append("folder exists but contains no PDF files")
    else:
        status = "missing"
        risk_flags.append("path_not_found")
        notes.append("folder not found in current workspace")
    return make_record(
        source_id=f"RAZ_{level}_PDF_REFERENCE_CORPUS",
        source_family="raz_pdf_reference_corpus",
        source_role="external_reference_corpus",
        status=status,
        path=rel_path,
        exists=exists,
        direct_use_allowed=False,
        authority_import_allowed=False,
        content_extraction_allowed=False,
        learner_facing_allowed=False,
        license_status="external_reference_only",
        review_status="required_before_use" if exists and pdf_count > 0 else "blocked",
        notes=notes,
        risk_flags=risk_flags,
    )


def future_candidate_record(source_id):
    return make_record(
        source_id=source_id,
        source_family="future_candidate_corpora",
        source_role="future_candidate_corpus",
        status="future_candidate",
        path=f"future_candidate/{source_id}",
        exists=False,
        direct_use_allowed=False,
        authority_import_allowed=False,
        content_extraction_allowed=False,
        learner_facing_allowed=False,
        license_status="future_candidate_unknown",
        review_status="pending",
        notes=["placeholder record created by AUX-S1 inventory builder"],
        risk_flags=["source_not_present_in_workspace"],
    )


def build_inventory():
    records = [
        path_record(
            source_id="EGP_SOURCE_XLSX",
            source_family="grammar_authority",
            source_role="authority_source",
            rel_path="grammar_profile/source/English Grammar Profile Online.xlsx",
            direct_use_allowed=False,
            authority_import_allowed=True,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="known_authority_source",
            review_status="not_required",
        ),
        path_record(
            source_id="GRAMMAR_PROFILE_JSON",
            source_family="grammar_authority",
            source_role="normalized_authority_artifact",
            rel_path="grammar_profile/json/grammar_profile.json",
            direct_use_allowed=False,
            authority_import_allowed=False,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="normalized_internal_artifact",
            review_status="not_required",
        ),
        path_record(
            source_id="EVP_SOURCE_XLSX",
            source_family="vocabulary_authority",
            source_role="authority_source",
            rel_path="vocabulary/source/English Vocabulary Profile Online.xlsx",
            direct_use_allowed=False,
            authority_import_allowed=True,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="known_authority_source",
            review_status="not_required",
        ),
        path_record(
            source_id="NGSL_SOURCE_XLSX",
            source_family="vocabulary_authority",
            source_role="authority_source",
            rel_path="vocabulary/source/NGSL+with+SFI+(31K).xlsx",
            direct_use_allowed=False,
            authority_import_allowed=True,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="known_authority_source",
            review_status="not_required",
        ),
        path_record(
            source_id="VOCABULARY_JSON",
            source_family="vocabulary_authority",
            source_role="normalized_authority_artifact",
            rel_path="vocabulary/json/vocabulary.json",
            direct_use_allowed=False,
            authority_import_allowed=False,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="normalized_internal_artifact",
            review_status="not_required",
        ),
        path_record(
            source_id="THEME_CATALOG_JSON",
            source_family="theme_authority",
            source_role="normalized_authority_artifact",
            rel_path="themes/theme_catalog.json",
            direct_use_allowed=False,
            authority_import_allowed=False,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="normalized_internal_artifact",
            review_status="not_required",
        ),
        path_record(
            source_id="THEME_MAPPING_JSON",
            source_family="theme_authority",
            source_role="normalized_authority_artifact",
            rel_path="themes/theme_mapping.json",
            direct_use_allowed=False,
            authority_import_allowed=False,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="normalized_internal_artifact",
            review_status="not_required",
        ),
        path_record(
            source_id="THEME_VOCAB_MAPPING_JSON",
            source_family="theme_authority",
            source_role="normalized_authority_artifact",
            rel_path="themes/theme_vocab_mapping.json",
            direct_use_allowed=False,
            authority_import_allowed=False,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="normalized_internal_artifact",
            review_status="not_required",
        ),
        path_record(
            source_id="RAZ_A_BOOKS_MANIFEST_XLSX",
            source_family="raz_manifest",
            source_role="authority_source",
            rel_path="input/manifest/raz_a_books_manifest.xlsx",
            direct_use_allowed=False,
            authority_import_allowed=False,
            content_extraction_allowed=False,
            learner_facing_allowed=False,
            license_status="known_authority_source",
            review_status="required_before_use",
            notes=["manifest_only_not_content_authority"],
            risk_flags=["manifest_only_source"],
        ),
    ]

    for level in ["A", "B", "C", "D", "E", "F"]:
        records.append(raz_pdf_folder_record(level))

    pilot_output_specs = [
        ("RAZ_REFERENCE_SENTENCES_XLSX", "output/excel/raz_a_reference_sentences.xlsx"),
        ("RAZ_REFERENCE_SENTENCES_COPY_XLSX", "output/excel/raz_a_reference_sentences - 複製.xlsx"),
        ("RAZ_REFERENCE_SENTENCES_S25_XLSX", "output/excel/raz_reference_sentences_S2_5_RUN_20260620_022807.xlsx"),
        ("RAZ_PAGES_RAW_JSON", "output/json/pages_raw.json"),
        ("RAZ_SENTENCES_V01_JSON", "output/json/sentences_v01.json"),
        ("RAZ_REFERENCE_DUPLICATE_GROUPS_JSON", "output/json/reference_duplicate_groups.json"),
        ("RAZ_EXTRACTION_REPORT_JSON", "output/json/extraction_report.json"),
        ("RAZ_EXTRACTION_LOG_TXT", "output/logs/extraction_log.txt"),
        ("RAZ_ARCHIVE_S25_RUN", "output/archive/S2_5_RUN_20260620_022807"),
        ("RAZ_S23_MULTIPDF_MANIFEST_PILOT_MD", "docs/raz/RAZ_A_S2_3_MULTIPDF_MANIFEST_PILOT.md"),
        ("RAZ_S24_LARGER_A_SET_PILOT_MD", "docs/raz/RAZ_A_S2_4_LARGER_A_SET_PILOT.md"),
        ("RAZ_S25_CROSS_LEVEL_SMOKE_PILOT_MD", "docs/raz/RAZ_A_S2_5_CROSS_LEVEL_SMOKE_PILOT.md"),
    ]
    for source_id, rel_path in pilot_output_specs:
        records.append(
            path_record(
                source_id=source_id,
                source_family="raz_pilot_output",
                source_role="experimental_pilot_output",
                rel_path=rel_path,
                direct_use_allowed=False,
                authority_import_allowed=False,
                content_extraction_allowed=False,
                learner_facing_allowed=False,
                license_status="unknown_internal_reference_only",
                review_status="required_before_use",
            )
        )

    records.extend(
        [
            future_candidate_record("parent_functional_sentence_corpus"),
            future_candidate_record("story_dialogue_corpus"),
            future_candidate_record("writing_sentence_template_corpus"),
            future_candidate_record("generated_dialogue_candidates"),
            future_candidate_record("generated_writing_candidates"),
            future_candidate_record("assessment_pattern_corpus"),
        ]
    )

    records.sort(key=lambda item: (item["source_family"], item["source_id"]))
    return records


def build_summary(records):
    counts_by_source_role = Counter(record["source_role"] for record in records)
    counts_by_status = Counter(record["status"] for record in records)
    present_sources = [record["source_id"] for record in records if record["status"] in {"present", "present_with_warnings"}]
    missing_sources = [record["source_id"] for record in records if record["status"] == "missing"]
    blocked_sources = [record["source_id"] for record in records if record["status"] == "blocked"]
    future_candidate_sources = [record["source_id"] for record in records if record["status"] == "future_candidate"]
    risk_flags_by_source = {
        record["source_id"]: record["risk_flags"]
        for record in records
        if record["risk_flags"]
    }
    raz_pdf_folder_status = {
        record["source_id"]: {
            "status": record["status"],
            "exists": record["exists"],
            "notes": record["notes"],
        }
        for record in records
        if record["source_family"] == "raz_pdf_reference_corpus"
    }
    authority_sources_present = [
        record["source_id"]
        for record in records
        if record["source_role"] == "authority_source" and record["status"] in {"present", "present_with_warnings"}
    ]
    external_reference_corpora_present = [
        record["source_id"]
        for record in records
        if record["source_role"] == "external_reference_corpus" and record["status"] in {"present", "present_with_warnings"}
    ]
    validation_status = "PASS_WITH_WARNINGS" if blocked_sources or missing_sources else "PASS"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_sources": len(records),
        "counts_by_source_role": dict(sorted(counts_by_source_role.items())),
        "counts_by_status": dict(sorted(counts_by_status.items())),
        "present_sources": present_sources,
        "missing_sources": missing_sources,
        "blocked_sources": blocked_sources,
        "future_candidate_sources": future_candidate_sources,
        "risk_flags_by_source": risk_flags_by_source,
        "raz_pdf_folder_status": raz_pdf_folder_status,
        "authority_sources_present": authority_sources_present,
        "external_reference_corpora_present": external_reference_corpora_present,
        "validation_status": validation_status,
    }


def main():
    records = build_inventory()
    summary = build_summary(records)
    write_json(INVENTORY_PATH, records)
    write_json(SUMMARY_PATH, summary)
    print(f"Corpus Source Inventory build: {summary['validation_status']}")
    print(f"Total sources: {summary['total_sources']}")
    print(f"Present: {len(summary['present_sources'])}")
    print(f"Missing: {len(summary['missing_sources'])}")
    print(f"Blocked: {len(summary['blocked_sources'])}")
    print(f"Future candidate: {len(summary['future_candidate_sources'])}")


if __name__ == "__main__":
    main()
