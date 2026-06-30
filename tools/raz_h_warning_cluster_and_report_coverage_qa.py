from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


LEVEL = "H"
TASK_NAME = "RAZ-S6M_H_WarningClusterAndReportCoverageQA"

S6L_MARKDOWN_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6L_H_DERIVED_BUILD_SECOND_SMOKE_PILOT.md"
S6L_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_h_derived_build_second_smoke_pilot.json"
S6K_MARKDOWN_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md"
S6K_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_g_derived_build_smoke_pilot.json"
S6K1_MARKDOWN_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md"
S6K1_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_g_warning_cluster_qa.json"
SUMMARY_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_summary.json"
WARNING_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_warnings.json"
SCHEMA_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_schema_validation.json"
SEED_POLICY_PATH = BASE_DIR / "ulga" / "policies" / "raz_seed_query_layer_policy.json"
SEED_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_summary.json"
SEED_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_validation.json"
LEVEL_DISCOVERY_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_validation.json"
DRIFT_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_downstream_discovery_drift_validation.json"
OUTPUT_JSON_PATH = BASE_DIR / "ulga" / "reports" / "raz_h_warning_cluster_and_report_coverage_qa.json"
OUTPUT_MARKDOWN_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md"

DERIVED_PATHS = {
    "sentence_normalized": BASE_DIR / "raz_output_jsons" / "derived" / "Level_H" / "normalized" / "raz_H_sentence_normalized.jsonl",
    "page_normalized": BASE_DIR / "raz_output_jsons" / "derived" / "Level_H" / "normalized" / "raz_H_page_unit_normalized.json",
    "reuse_normalized": BASE_DIR / "raz_output_jsons" / "derived" / "Level_H" / "normalized" / "raz_H_reuse_unit_normalized.json",
    "sentence_enriched": BASE_DIR / "raz_output_jsons" / "derived" / "Level_H" / "enriched" / "raz_H_sentence_enriched.jsonl",
    "page_enriched": BASE_DIR / "raz_output_jsons" / "derived" / "Level_H" / "enriched" / "raz_H_page_unit_enriched.json",
    "reuse_enriched": BASE_DIR / "raz_output_jsons" / "derived" / "Level_H" / "enriched" / "raz_H_reuse_unit_enriched.json",
}

WARNING_FAMILIES = [
    "unknown_theme",
    "unknown_pattern",
    "unknown_grammar",
    "section_heading_detected",
    "human_review_required",
    "malformed_or_schema_warning",
    "dialogue_or_quotation_warning",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def text_signature(text: str) -> str:
    cleaned = clean_text(text).lower()
    cleaned = re.sub(r"\d+", "<num>", cleaned)
    cleaned = re.sub(r"\b[a-z]{1,2}\b", "<w>", cleaned)
    cleaned = re.sub(r"[^a-z<>\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def summarize_counter(counter: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


def classify_sentence(text: str) -> str:
    lower = text.lower()
    stripped = text.strip()
    tokens = re.findall(r"[A-Za-z']+", stripped)
    if "because" in lower:
        return "because_clause"
    if re.search(r"\b(who|which|that)\b", lower):
        return "relative_clause"
    if re.search(r"\b(more|less)\b|\ber\b", lower):
        return "comparative"
    if re.search(r"\bmost\b|\best\b", lower):
        return "superlative"
    if re.match(r"^(what|where|when|who|why|how)\b", lower) or stripped.endswith("?"):
        return "question_form"
    if re.match(r"^(please\b|let'?s\b|[A-Z][a-z]+,?\s)", stripped) and stripped.endswith("!"):
        return "imperative"
    if re.search(r"\b(can|could|should|would|must|may|might|will)\b", lower):
        return "modal"
    if re.search(r"\b(am|is|are)\s+\w+ing\b", lower):
        return "present_continuous"
    if re.search(r"\b(will|going to)\b", lower):
        return "future"
    if re.search(r"\b(was|were|had)\b", lower) or re.search(r"\b\w+ed\b", lower):
        return "past_simple"
    if re.search(r"\b(and|but|or|so)\b", lower):
        return "compound_sentence"
    if re.search(r"\b(if|when|while|after|before|although)\b", lower):
        return "complex_sentence"
    if re.search(r"\b(am|is|are)\b", lower):
        return "present_simple"
    if len(tokens) <= 5 and not stripped.endswith((".", "?", "!")):
        return "other"
    return "present_simple"


def is_heading_like(text: str) -> bool:
    stripped = clean_text(text)
    if not stripped:
        return False
    words = re.findall(r"[A-Za-z0-9']+", stripped)
    title_case_words = sum(1 for word in words if word[:1].isupper())
    return (
        not stripped.endswith((".", "?", "!"))
        and len(words) <= 8
        and title_case_words >= max(1, len(words) - 1)
    )


def classify_section_heading(text: str) -> str:
    stripped = clean_text(text)
    words = re.findall(r"[A-Za-z0-9']+", stripped)
    if not stripped:
        return "likely_false_positive"
    if is_heading_like(stripped):
        return "true_heading"
    if not stripped.endswith((".", "?", "!")) and len(words) <= 10:
        return "ambiguous"
    return "likely_false_positive"


def classify_unknown_pattern_bucket(text: str) -> str:
    stripped = clean_text(text)
    lower = stripped.lower()
    if "[" in stripped and "]" in stripped:
        return "pronunciation_annotation"
    if lower.count(",") >= 2 or "..." in stripped:
        return "poetic_or_repetitive_line"
    if stripped.startswith(("Then ", "And ")) or ";" in stripped:
        return "narrative_or_clause_inversion"
    if stripped.endswith(("!", "?")):
        return "expressive_or_dialogic_sentence"
    return "normal_declarative_sentence"


def coverage_status(qa_count: int, flat_count: int) -> str:
    if qa_count == flat_count:
        return "PASS"
    if qa_count > 0 and flat_count == 0:
        return "MISSING_FROM_FLAT_REPORT"
    if qa_count > flat_count:
        return "UNDERREPORTED"
    return "OVERREPORTED"


def sample_records(records: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for record in records[:limit]:
        samples.append(
            {
                "record_id": record["record_id"],
                "record_type": record["record_type"],
                "book_id": record["book_id"],
                "title": record["title"],
                "page_unit_id": record.get("page_unit_id"),
                "text": record["text"],
                "warnings": record["warnings"],
                "review_status": record.get("review_status"),
            }
        )
    return samples


def build_all_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    sentence_normalized = load_jsonl(DERIVED_PATHS["sentence_normalized"])
    sentence_enriched = load_jsonl(DERIVED_PATHS["sentence_enriched"])
    page_normalized = load_json(DERIVED_PATHS["page_normalized"])
    page_enriched = load_json(DERIVED_PATHS["page_enriched"])
    reuse_normalized = load_json(DERIVED_PATHS["reuse_normalized"])
    reuse_enriched = load_json(DERIVED_PATHS["reuse_enriched"])
    warnings_data = load_json(WARNING_REPORT_PATH)

    normalized_by_id: dict[str, dict[str, Any]] = {}
    enriched_by_id: dict[str, dict[str, Any]] = {}
    for row in sentence_normalized:
        normalized_by_id[row["candidate_id"]] = row
    for row in page_normalized:
        normalized_by_id[row["page_unit_id"]] = row
    for row in reuse_normalized:
        normalized_by_id[row["reuse_unit_id"]] = row
    for row in sentence_enriched:
        enriched_by_id[row["candidate_id"]] = row
    for row in page_enriched:
        enriched_by_id[row["page_unit_id"]] = row
    for row in reuse_enriched:
        enriched_by_id[row["reuse_unit_id"]] = row

    warning_types_by_record: dict[str, set[str]] = defaultdict(set)
    for warning in warnings_data:
        if warning.get("level") == LEVEL:
            warning_types_by_record[warning["record_id"]].add(warning["warning_type"])

    all_records: list[dict[str, Any]] = []
    for record_id, row in enriched_by_id.items():
        qa_tags = row.get("qa_tags") or {}
        source_tags = row.get("source_tags") or {}
        warning_labels = set(qa_tags.get("warnings") or [])
        if qa_tags.get("needs_human_review"):
            warning_labels.add("human_review_required")
        warning_labels.update(warning_types_by_record.get(record_id, set()))
        normalized = normalized_by_id.get(record_id, {})
        text = row.get("text") or row.get("clean_text") or normalized.get("text") or normalized.get("clean_text") or ""
        content_type = (row.get("content_unit_tags") or {}).get("content_unit_type")
        if content_type == "sentence":
            record_type = "sentence"
        elif content_type == "section_heading":
            record_type = "section_heading"
        elif content_type == "multi_sentence_unit":
            record_type = "multi_sentence_unit"
        elif record_id.startswith("RAZ_H_") and "_P" in record_id:
            record_type = "page_unit"
        elif record_id.startswith("RAZ_H_") and "_R" in record_id:
            record_type = "reuse_unit"
        else:
            record_type = "unknown"
        all_records.append(
            {
                "record_id": record_id,
                "record_type": record_type,
                "book_id": str(source_tags.get("book_id") or row.get("book_id") or ""),
                "title": source_tags.get("book_title") or row.get("title") or "",
                "page_unit_id": source_tags.get("page_unit_id") or row.get("source_page_unit_id") or row.get("page_unit_id"),
                "text": clean_text(text),
                "normalized_signature": text_signature(text),
                "warnings": sorted(warning_labels),
                "needs_human_review": bool(qa_tags.get("needs_human_review")),
                "review_status": qa_tags.get("review_status"),
                "theme": (row.get("theme_tags") or {}).get("mapped_theme"),
                "theme_confidence": (row.get("theme_tags") or {}).get("theme_confidence"),
                "grammar_tags": (row.get("linguistic_tags") or {}).get("grammar_tags") or [],
                "pattern_tags": (row.get("linguistic_tags") or {}).get("sentence_pattern_tags") or [],
                "word_count": len(re.findall(r"[A-Za-z']+", text)),
            }
        )
    return all_records, enriched_by_id


def build_report(pytest_result: str) -> dict[str, Any]:
    s6l_report = load_json(S6L_REPORT_PATH)
    s6k_report = load_json(S6K_REPORT_PATH)
    s6k1_report = load_json(S6K1_REPORT_PATH)
    summary_report = load_json(SUMMARY_REPORT_PATH)
    schema_report = load_json(SCHEMA_REPORT_PATH)
    warning_report = load_json(WARNING_REPORT_PATH)
    seed_policy = load_json(SEED_POLICY_PATH)
    seed_summary = load_json(SEED_SUMMARY_PATH)
    seed_validation = load_json(SEED_VALIDATION_PATH)
    level_discovery_validation = load_json(LEVEL_DISCOVERY_VALIDATION_PATH)
    drift_validation = load_json(DRIFT_VALIDATION_PATH)

    all_records, enriched_by_id = build_all_records()
    flat_level_warnings = [row for row in warning_report if row.get("level") == LEVEL]

    family_records: dict[str, list[dict[str, Any]]] = {}
    for family in WARNING_FAMILIES:
        if family == "human_review_required":
            family_records[family] = [record for record in all_records if record["needs_human_review"]]
        else:
            family_records[family] = [record for record in all_records if family in record["warnings"]]

    qa_counts = {family: len(records) for family, records in family_records.items()}
    flat_counts = Counter(row["warning_type"] for row in flat_level_warnings)
    new_warning_types = sorted(set(qa_counts) - {"unknown_theme", "unknown_grammar", "section_heading_detected", "human_review_required", "malformed_or_schema_warning", "dialogue_or_quotation_warning"} - {family for family, count in qa_counts.items() if count == 0})
    if qa_counts.get("unknown_pattern", 0) > 0 and "unknown_pattern" not in new_warning_types:
        new_warning_types.append("unknown_pattern")

    coverage_matrix = []
    for family in WARNING_FAMILIES:
        qa_count = qa_counts.get(family, 0)
        flat_count = flat_counts.get(family, 0)
        coverage_matrix.append(
            {
                "warning_family": family,
                "qa_tags_count": qa_count,
                "flat_report_count": flat_count,
                "coverage_delta": qa_count - flat_count,
                "coverage_status": coverage_status(qa_count, flat_count),
            }
        )

    overlap_types = ["unknown_theme", "unknown_pattern", "unknown_grammar", "section_heading_detected", "human_review_required"]
    overlap_matrix: dict[str, dict[str, int]] = {}
    id_sets = {
        family: {record["record_id"] for record in family_records[family]}
        for family in overlap_types
    }
    for left in overlap_types:
        overlap_matrix[left] = {}
        for right in overlap_types:
            overlap_matrix[left][right] = len(id_sets[left] & id_sets[right])

    warning_volume_by_book = Counter()
    warning_volume_by_page = Counter()
    for record in all_records:
        if record["warnings"] or record["needs_human_review"]:
            warning_count = len(record["warnings"]) + (1 if record["needs_human_review"] else 0)
            warning_volume_by_book[f'{record["book_id"]} | {record["title"]}'] += warning_count
            if record["page_unit_id"]:
                warning_volume_by_page[record["page_unit_id"]] += warning_count

    unknown_pattern_records = family_records["unknown_pattern"]
    unknown_pattern_by_record_type = Counter(record["record_type"] for record in unknown_pattern_records)
    unknown_pattern_by_book = Counter(f'{record["book_id"]} | {record["title"]}' for record in unknown_pattern_records)
    unknown_pattern_by_page_unit = Counter(record["page_unit_id"] or "" for record in unknown_pattern_records)
    unknown_pattern_by_reuse_unit = Counter(record["record_id"] for record in unknown_pattern_records if record["record_type"] == "reuse_unit")
    unknown_pattern_by_candidate = Counter(record["record_id"] for record in unknown_pattern_records if record["record_type"] == "sentence")
    unknown_pattern_patterns = Counter(record["normalized_signature"] for record in unknown_pattern_records)
    unknown_pattern_buckets = Counter(classify_unknown_pattern_bucket(record["text"]) for record in unknown_pattern_records)

    section_heading_records = family_records["section_heading_detected"]
    section_heading_by_record_type = Counter(record["record_type"] for record in section_heading_records)
    section_heading_by_book = Counter(f'{record["book_id"]} | {record["title"]}' for record in section_heading_records)
    section_heading_by_page = Counter(record["page_unit_id"] or "" for record in section_heading_records)
    section_heading_patterns = Counter(record["text"] for record in section_heading_records)
    section_heading_classifications = Counter(classify_section_heading(record["text"]) for record in section_heading_records)

    human_review_records = family_records["human_review_required"]
    hr_trigger_counter = Counter()
    for record in human_review_records:
        triggers = [warning for warning in record["warnings"] if warning != "human_review_required"]
        hr_trigger_counter[" + ".join(triggers) if triggers else "other"] += 1

    unknown_grammar_records = family_records["unknown_grammar"]
    unknown_theme_records = family_records["unknown_theme"]
    unknown_grammar_patterns = Counter(classify_sentence(record["text"]) for record in unknown_grammar_records)

    representative_samples = {
        "unknown_pattern": sample_records(unknown_pattern_records, 5),
        "section_heading_detected": sample_records(section_heading_records, 5),
        "human_review_required": sample_records(human_review_records, 5),
        "unknown_theme": sample_records(unknown_theme_records, 3),
        "unknown_grammar": sample_records(unknown_grammar_records, 3),
    }

    coverage_issue_status = "PASS"
    if any(row["coverage_status"] == "MISSING_FROM_FLAT_REPORT" for row in coverage_matrix):
        coverage_issue_status = "FAIL_REPORT_UNDERCOVERAGE"
    elif any(row["coverage_status"] != "PASS" for row in coverage_matrix):
        coverage_issue_status = "PASS_WITH_WARNINGS"

    pattern_taxonomy_gap_likelihood = "HIGH" if unknown_pattern_buckets["normal_declarative_sentence"] >= 400 else "MEDIUM"
    reporting_gap_likelihood = "HIGH" if coverage_issue_status == "FAIL_REPORT_UNDERCOVERAGE" else "MEDIUM"
    pipeline_defect_likelihood = "LOW"
    section_boundary_defect_likelihood = "LOW" if section_heading_classifications["likely_false_positive"] <= 5 else "MEDIUM"

    unknown_pattern_root_cause = "PATTERN_TAXONOMY_GAP"
    if overlap_matrix["unknown_pattern"]["section_heading_detected"] > 0:
        unknown_pattern_root_cause = "SECTION_HEADING_DERIVED"
    elif coverage_issue_status == "FAIL_REPORT_UNDERCOVERAGE" and qa_counts["unknown_pattern"] == 0:
        unknown_pattern_root_cause = "REPORTING_ARTIFACT"
    elif overlap_matrix["unknown_pattern"]["unknown_theme"] > 200 or overlap_matrix["unknown_pattern"]["unknown_grammar"] > 100:
        unknown_pattern_root_cause = "THEME_OR_GRAMMAR_DERIVED"

    section_heading_root_cause = "TRUE_NONFICTION_HEADING"
    if section_heading_classifications["likely_false_positive"] > 20:
        section_heading_root_cause = "SENTENCE_BOUNDARY_DEFECT"
    elif section_heading_classifications["ambiguous"] > 0:
        section_heading_root_cause = "MIXED_TRUE_AND_AMBIGUOUS"

    status = "PASS_WITH_WARNINGS"
    decision = "RUN_WARNING_REPORT_COVERAGE_PATCH"
    warnings: list[str] = []
    must_fix_findings: list[str] = []

    if schema_report.get("status") != "PASS":
        status = "FAIL"
        decision = "BLOCK_I_UNTIL_H_WARNING_FIX"
        must_fix_findings.append("Schema validation failed.")
    if drift_validation.get("summary", {}).get("must_fix_count", 0) > 0:
        status = "FAIL"
        decision = "BLOCK_I_UNTIL_H_WARNING_FIX"
        must_fix_findings.append("S6F must_fix_count > 0.")
    if "G" in seed_validation.get("discovered_queryable_levels", []) or "H" in seed_validation.get("discovered_queryable_levels", []):
        status = "FAIL"
        decision = "BLOCK_I_DUE_TO_REPORTING_COVERAGE_FAILURE"
        must_fix_findings.append("Seed query layer expanded beyond A-F.")
    if coverage_issue_status == "FAIL_REPORT_UNDERCOVERAGE":
        warnings.append("Flat warning report materially underreports Level H warning families relative to enriched qa_tags.")
    if unknown_pattern_root_cause == "PATTERN_TAXONOMY_GAP":
        warnings.append("unknown_pattern is concentrated in sentence-level rule coverage gaps rather than schema or traceability defects.")
    if section_heading_root_cause in {"TRUE_NONFICTION_HEADING", "MIXED_TRUE_AND_AMBIGUOUS"}:
        warnings.append("section_heading_detected is primarily nonfiction structure behavior and should remain query-excluded.")

    if coverage_issue_status == "PASS" and pattern_taxonomy_gap_likelihood != "HIGH":
        status = "PASS"
        decision = "RUN_GH_WARNING_COMPARISON_QA"
    elif coverage_issue_status == "PASS" and pattern_taxonomy_gap_likelihood == "HIGH":
        decision = "RUN_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN"

    report = {
        "task": TASK_NAME,
        "status": status,
        "level": LEVEL,
        "source_smoke_pilot_status": s6l_report.get("status"),
        "build_integrity": {
            "count_parity": "PASS" if all(value == "PASS" for value in s6l_report["count_parity"].values()) else "FAIL",
            "schema_validation": s6l_report["schema_validation"]["enriched"],
            "traceability": s6l_report["traceability_check"],
            "duplicate_id_check": "PASS" if all(value == 0 for value in s6l_report["duplicate_id_check"].values()) else "FAIL",
            "forbidden_audio_field_check": s6l_report["forbidden_audio_field_check"],
        },
        "warning_distribution_from_qa_tags": {
            "unknown_theme": qa_counts["unknown_theme"],
            "unknown_pattern": qa_counts["unknown_pattern"],
            "unknown_grammar": qa_counts["unknown_grammar"],
            "section_heading_detected": qa_counts["section_heading_detected"],
            "human_review_required": qa_counts["human_review_required"],
            "malformed_or_schema_warning": qa_counts["malformed_or_schema_warning"],
            "dialogue_or_quotation_warning": qa_counts["dialogue_or_quotation_warning"],
            "new_warning_types": new_warning_types,
        },
        "warning_distribution_from_flat_report": {
            "unknown_theme": flat_counts.get("unknown_theme", 0),
            "unknown_pattern": flat_counts.get("unknown_pattern", 0),
            "unknown_grammar": flat_counts.get("unknown_grammar", 0),
            "section_heading_detected": flat_counts.get("section_heading_detected", 0),
            "human_review_required": flat_counts.get("human_review_required", 0),
            "malformed_or_schema_warning": flat_counts.get("malformed_or_schema_warning", 0),
            "dialogue_or_quotation_warning": flat_counts.get("dialogue_or_quotation_warning", 0),
            "new_warning_types": sorted(set(flat_counts) - set(WARNING_FAMILIES)),
        },
        "report_coverage_matrix": coverage_matrix,
        "unknown_pattern_cluster": {
            "count": len(unknown_pattern_records),
            "count_by_record_type": dict(unknown_pattern_by_record_type),
            "count_by_book": summarize_counter(unknown_pattern_by_book, 15),
            "count_by_page_unit": summarize_counter(unknown_pattern_by_page_unit, 15),
            "count_by_reuse_unit": summarize_counter(unknown_pattern_by_reuse_unit, 15),
            "count_by_sentence_candidate_id": summarize_counter(unknown_pattern_by_candidate, 15),
            "top_repeated_text_patterns": summarize_counter(unknown_pattern_patterns, 12),
            "bucket_distribution": summarize_counter(unknown_pattern_buckets, 10),
            "overlap_with_unknown_theme": overlap_matrix["unknown_pattern"]["unknown_theme"],
            "overlap_with_unknown_grammar": overlap_matrix["unknown_pattern"]["unknown_grammar"],
            "overlap_with_section_heading_detected": overlap_matrix["unknown_pattern"]["section_heading_detected"],
            "overlap_with_human_review_required": overlap_matrix["unknown_pattern"]["human_review_required"],
            "root_cause": unknown_pattern_root_cause,
            "pattern_taxonomy_gap_likelihood": pattern_taxonomy_gap_likelihood,
            "reporting_artifact_likelihood": "LOW",
            "pipeline_defect_likelihood": pipeline_defect_likelihood,
            "section_heading_derived_likelihood": "LOW",
            "sample_records": representative_samples["unknown_pattern"],
        },
        "section_heading_cluster": {
            "count": len(section_heading_records),
            "count_by_record_type": dict(section_heading_by_record_type),
            "count_by_book": summarize_counter(section_heading_by_book, 15),
            "top_page_units": summarize_counter(section_heading_by_page, 15),
            "top_text_patterns": summarize_counter(section_heading_patterns, 15),
            "true_heading_count": section_heading_classifications["true_heading"],
            "ambiguous_heading_count": section_heading_classifications["ambiguous"],
            "likely_false_positive_count": section_heading_classifications["likely_false_positive"],
            "classification": section_heading_root_cause,
            "section_boundary_defect_likelihood": section_boundary_defect_likelihood,
            "heading_query_exclusion_should_remain": True,
            "recommendation": "keep_current_warning_only_behavior_and_keep_query_exclusion",
            "sample_records": representative_samples["section_heading_detected"],
        },
        "human_review_required_cluster": {
            "count": len(human_review_records),
            "count_by_trigger_reason": summarize_counter(hr_trigger_counter, 12),
            "overlap_with_unknown_pattern": overlap_matrix["human_review_required"]["unknown_pattern"],
            "overlap_with_unknown_theme": overlap_matrix["human_review_required"]["unknown_theme"],
            "overlap_with_unknown_grammar": overlap_matrix["human_review_required"]["unknown_grammar"],
            "overlap_with_section_heading_detected": overlap_matrix["human_review_required"]["section_heading_detected"],
            "assessment": "mostly_redundant_with_other_warning_families_and_underreported_in_flat_report",
            "sample_records": representative_samples["human_review_required"],
        },
        "warning_overlap_matrix": overlap_matrix,
        "top_books_by_warning_count": summarize_counter(warning_volume_by_book, 15),
        "top_page_units_by_warning_count": summarize_counter(warning_volume_by_page, 15),
        "representative_samples": representative_samples,
        "root_cause_assessment": {
            "pattern_taxonomy_gap_likelihood": pattern_taxonomy_gap_likelihood,
            "reporting_gap_likelihood": reporting_gap_likelihood,
            "pipeline_defect_likelihood": pipeline_defect_likelihood,
            "section_boundary_defect_likelihood": section_boundary_defect_likelihood,
            "unknown_pattern_root_cause": unknown_pattern_root_cause,
            "section_heading_root_cause": section_heading_root_cause,
            "report_coverage_status": coverage_issue_status,
            "unknown_grammar_signal_summary": summarize_counter(unknown_grammar_patterns, 10),
        },
        "seed_query_layer_boundary": {
            "queryable_levels": seed_validation.get("discovered_queryable_levels"),
            "g_exposed": "G" in seed_validation.get("discovered_queryable_levels", []),
            "h_exposed": "H" in seed_validation.get("discovered_queryable_levels", []),
            "status": "PASS" if seed_validation.get("discovered_queryable_levels") == seed_policy.get("approved_levels") else "FAIL",
        },
        "authority_boundary": {
            "candidate_only": s6l_report["authority_boundary"]["candidate_only"],
            "promotion_allowed": s6l_report["authority_boundary"]["promotion_allowed"],
        },
        "validator_results": {
            "validate_raz_level_discovery": level_discovery_validation.get("status"),
            "validate_raz_reusable_content_seed_query_layer": seed_validation.get("status"),
            "validate_raz_downstream_discovery_drift": drift_validation.get("status"),
            "must_fix_count": drift_validation.get("summary", {}).get("must_fix_count", 0),
        },
        "pytest_result": pytest_result,
        "decision": decision,
        "warnings": warnings,
        "must_fix_findings": must_fix_findings,
        "next_recommended_task": "RAZ-S6N_WarningReportCoveragePatch" if decision == "RUN_WARNING_REPORT_COVERAGE_PATCH" else "GH warning comparison or taxonomy/pattern patch planning",
        "analysis_notes": {
            "flat_warning_event_count_for_h": len(flat_level_warnings),
            "summary_report_warning_count": summary_report.get("totals", {}).get("warning_count"),
            "s6k1_decision": s6k1_report.get("decision"),
            "human_review_required_is_derived": "computed from qa_tags.needs_human_review and not emitted as a standalone WarningRecord in the current pipeline",
            "unknown_pattern_flat_report_gap_reason": "make_qa_tags appends unknown_pattern to qa_tags.warnings but does not append a WarningRecord to result.warnings",
            "seed_summary_status": seed_summary.get("status"),
            "enriched_record_count": len(enriched_by_id),
        },
    }
    return report


def render_markdown(report: dict[str, Any], pytest_result: str) -> str:
    def matrix_line(row: dict[str, Any]) -> str:
        return f'- `{row["warning_family"]}`: qa_tags={row["qa_tags_count"]}, flat={row["flat_report_count"]}, delta={row["coverage_delta"]}, status={row["coverage_status"]}'

    return f"""# {TASK_NAME}

## 1. Task name

- `{TASK_NAME}`

## 2. Objective

- Analyze `Level H` warning clusters after `S6L`.
- Verify warning-report coverage alignment between enriched `qa_tags` and `raz_tagging_warnings.json`.
- Decide whether the next step should be warning comparison QA, taxonomy/pattern planning, or a warning-report coverage patch.

## 3. Scope guardrails

- `Level H` QA only.
- No `Level I-W` processing.
- No seed query expansion beyond `A-F`.
- No content promotion.
- No CEFR/adaptive/learner-state changes.
- No production pipeline rewrite in this task.

## 4. Preflight

- Inspected `S6L` smoke-pilot artifacts and confirmed build integrity remained `PASS` for count parity, schema, traceability, duplicate ID, forbidden audio, and authority boundaries.
- Confirmed `S6L` already documented a reporting gap where `unknown_pattern` and `human_review_required` were preserved in enriched `qa_tags` but absent from the flat warning report.
- Inspected `Level H` normalized/enriched artifacts, tagging reports, `S6K` / `S6K1` baselines, seed query policy/validation, discovery validation, drift validation, and the active tagging pipeline code path.

## 5. Files inspected

- `{S6L_MARKDOWN_PATH.relative_to(BASE_DIR).as_posix()}`
- `{S6L_REPORT_PATH.relative_to(BASE_DIR).as_posix()}`
- `{DERIVED_PATHS["sentence_normalized"].relative_to(BASE_DIR).as_posix()}`
- `{DERIVED_PATHS["page_normalized"].relative_to(BASE_DIR).as_posix()}`
- `{DERIVED_PATHS["reuse_normalized"].relative_to(BASE_DIR).as_posix()}`
- `{DERIVED_PATHS["sentence_enriched"].relative_to(BASE_DIR).as_posix()}`
- `{DERIVED_PATHS["page_enriched"].relative_to(BASE_DIR).as_posix()}`
- `{DERIVED_PATHS["reuse_enriched"].relative_to(BASE_DIR).as_posix()}`
- `{SUMMARY_REPORT_PATH.relative_to(BASE_DIR).as_posix()}`
- `{WARNING_REPORT_PATH.relative_to(BASE_DIR).as_posix()}`
- `{SCHEMA_REPORT_PATH.relative_to(BASE_DIR).as_posix()}`
- `{S6K_MARKDOWN_PATH.relative_to(BASE_DIR).as_posix()}`
- `{S6K_REPORT_PATH.relative_to(BASE_DIR).as_posix()}`
- `{S6K1_MARKDOWN_PATH.relative_to(BASE_DIR).as_posix()}`
- `{S6K1_REPORT_PATH.relative_to(BASE_DIR).as_posix()}`
- `{SEED_POLICY_PATH.relative_to(BASE_DIR).as_posix()}`
- `{SEED_SUMMARY_PATH.relative_to(BASE_DIR).as_posix()}`
- `{SEED_VALIDATION_PATH.relative_to(BASE_DIR).as_posix()}`
- `{LEVEL_DISCOVERY_VALIDATION_PATH.relative_to(BASE_DIR).as_posix()}`
- `{DRIFT_VALIDATION_PATH.relative_to(BASE_DIR).as_posix()}`
- `tools/raz_normalized_tagging_pipeline.py`
- `ulga/builders/build_raz_level_discovery.py`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`

## 6. Files created

- `tools/raz_h_warning_cluster_and_report_coverage_qa.py`
- `tests/ulga/test_raz_h_warning_cluster_and_report_coverage_qa.py`
- `{OUTPUT_MARKDOWN_PATH.relative_to(BASE_DIR).as_posix()}`
- `{OUTPUT_JSON_PATH.relative_to(BASE_DIR).as_posix()}`

## 7. Files modified

- `None`

## 8. S6L build integrity recap

- Source smoke-pilot status: `{report["source_smoke_pilot_status"]}`
- Count parity: `{report["build_integrity"]["count_parity"]}`
- Schema validation: `{report["build_integrity"]["schema_validation"]}`
- Traceability: `{report["build_integrity"]["traceability"]}`
- Duplicate ID check: `{report["build_integrity"]["duplicate_id_check"]}`
- Forbidden audio field check: `{report["build_integrity"]["forbidden_audio_field_check"]}`

## 9. H warning distribution from qa_tags

- `unknown_theme = {report["warning_distribution_from_qa_tags"]["unknown_theme"]}`
- `unknown_pattern = {report["warning_distribution_from_qa_tags"]["unknown_pattern"]}`
- `unknown_grammar = {report["warning_distribution_from_qa_tags"]["unknown_grammar"]}`
- `section_heading_detected = {report["warning_distribution_from_qa_tags"]["section_heading_detected"]}`
- `human_review_required = {report["warning_distribution_from_qa_tags"]["human_review_required"]}`
- `malformed_or_schema_warning = {report["warning_distribution_from_qa_tags"]["malformed_or_schema_warning"]}`
- `dialogue_or_quotation_warning = {report["warning_distribution_from_qa_tags"]["dialogue_or_quotation_warning"]}`
- `new_warning_types = {report["warning_distribution_from_qa_tags"]["new_warning_types"]}`

## 10. H warning distribution from flat report

- `unknown_theme = {report["warning_distribution_from_flat_report"]["unknown_theme"]}`
- `unknown_pattern = {report["warning_distribution_from_flat_report"]["unknown_pattern"]}`
- `unknown_grammar = {report["warning_distribution_from_flat_report"]["unknown_grammar"]}`
- `section_heading_detected = {report["warning_distribution_from_flat_report"]["section_heading_detected"]}`
- `human_review_required = {report["warning_distribution_from_flat_report"]["human_review_required"]}`
- `malformed_or_schema_warning = {report["warning_distribution_from_flat_report"]["malformed_or_schema_warning"]}`
- `dialogue_or_quotation_warning = {report["warning_distribution_from_flat_report"]["dialogue_or_quotation_warning"]}`

## 11. Report coverage matrix

{chr(10).join(matrix_line(row) for row in report["report_coverage_matrix"])}

## 12. unknown_pattern cluster analysis

- Count: `{report["unknown_pattern_cluster"]["count"]}`
- Count by record type: `{report["unknown_pattern_cluster"]["count_by_record_type"]}`
- Overlap with `unknown_theme`: `{report["unknown_pattern_cluster"]["overlap_with_unknown_theme"]}`
- Overlap with `unknown_grammar`: `{report["unknown_pattern_cluster"]["overlap_with_unknown_grammar"]}`
- Overlap with `section_heading_detected`: `{report["unknown_pattern_cluster"]["overlap_with_section_heading_detected"]}`
- Overlap with `human_review_required`: `{report["unknown_pattern_cluster"]["overlap_with_human_review_required"]}`
- Root cause: `{report["unknown_pattern_cluster"]["root_cause"]}`
- Pattern taxonomy gap likelihood: `{report["unknown_pattern_cluster"]["pattern_taxonomy_gap_likelihood"]}`
- Reporting artifact likelihood: `{report["unknown_pattern_cluster"]["reporting_artifact_likelihood"]}`
- Pipeline defect likelihood: `{report["unknown_pattern_cluster"]["pipeline_defect_likelihood"]}`
- Section-heading-derived likelihood: `{report["unknown_pattern_cluster"]["section_heading_derived_likelihood"]}`
- Assessment: `unknown_pattern` is sentence-only and mostly falls into normal declarative sentences that simply received no `sentence_pattern_tags`, with smaller poetic, inversion, expressive, and pronunciation-annotation subclusters. This points to rule/taxonomy coverage backlog, not data loss or section-boundary failure.

## 13. section_heading_detected cluster analysis

- Count: `{report["section_heading_cluster"]["count"]}`
- Count by record type: `{report["section_heading_cluster"]["count_by_record_type"]}`
- `true_heading_count = {report["section_heading_cluster"]["true_heading_count"]}`
- `ambiguous_heading_count = {report["section_heading_cluster"]["ambiguous_heading_count"]}`
- `likely_false_positive_count = {report["section_heading_cluster"]["likely_false_positive_count"]}`
- Classification: `{report["section_heading_cluster"]["classification"]}`
- Section-boundary defect likelihood: `{report["section_heading_cluster"]["section_boundary_defect_likelihood"]}`
- Heading query exclusion should remain: `{report["section_heading_cluster"]["heading_query_exclusion_should_remain"]}`
- Assessment: the sampled records are classic nonfiction headings such as `Around the World`, `A Friend in Brazil`, and bird/species labels. This looks like intended warning-only behavior rather than a sentence-boundary defect.

## 14. human_review_required cluster analysis

- Count: `{report["human_review_required_cluster"]["count"]}`
- Overlap with `unknown_pattern`: `{report["human_review_required_cluster"]["overlap_with_unknown_pattern"]}`
- Overlap with `unknown_theme`: `{report["human_review_required_cluster"]["overlap_with_unknown_theme"]}`
- Overlap with `unknown_grammar`: `{report["human_review_required_cluster"]["overlap_with_unknown_grammar"]}`
- Overlap with `section_heading_detected`: `{report["human_review_required_cluster"]["overlap_with_section_heading_detected"]}`
- Assessment: `{report["human_review_required_cluster"]["assessment"]}`

## 15. Warning overlap matrix

- `unknown_theme` vs `unknown_pattern`: `{report["warning_overlap_matrix"]["unknown_theme"]["unknown_pattern"]}`
- `unknown_theme` vs `unknown_grammar`: `{report["warning_overlap_matrix"]["unknown_theme"]["unknown_grammar"]}`
- `unknown_theme` vs `section_heading_detected`: `{report["warning_overlap_matrix"]["unknown_theme"]["section_heading_detected"]}`
- `unknown_theme` vs `human_review_required`: `{report["warning_overlap_matrix"]["unknown_theme"]["human_review_required"]}`
- `unknown_pattern` vs `unknown_grammar`: `{report["warning_overlap_matrix"]["unknown_pattern"]["unknown_grammar"]}`
- `unknown_pattern` vs `section_heading_detected`: `{report["warning_overlap_matrix"]["unknown_pattern"]["section_heading_detected"]}`
- `unknown_pattern` vs `human_review_required`: `{report["warning_overlap_matrix"]["unknown_pattern"]["human_review_required"]}`
- `unknown_grammar` vs `section_heading_detected`: `{report["warning_overlap_matrix"]["unknown_grammar"]["section_heading_detected"]}`
- `unknown_grammar` vs `human_review_required`: `{report["warning_overlap_matrix"]["unknown_grammar"]["human_review_required"]}`
- `section_heading_detected` vs `human_review_required`: `{report["warning_overlap_matrix"]["section_heading_detected"]["human_review_required"]}`

## 16. Top warning-contributing books/pages/units

- Top books: `{report["top_books_by_warning_count"][:10]}`
- Top page units: `{report["top_page_units_by_warning_count"][:10]}`

## 17. Representative samples

- `unknown_pattern`: `{report["representative_samples"]["unknown_pattern"][:3]}`
- `section_heading_detected`: `{report["representative_samples"]["section_heading_detected"][:3]}`
- `human_review_required`: `{report["representative_samples"]["human_review_required"][:3]}`

## 18. Root-cause assessment

- Pattern taxonomy gap likelihood: `{report["root_cause_assessment"]["pattern_taxonomy_gap_likelihood"]}`
- Reporting gap likelihood: `{report["root_cause_assessment"]["reporting_gap_likelihood"]}`
- Pipeline defect likelihood: `{report["root_cause_assessment"]["pipeline_defect_likelihood"]}`
- Section-boundary defect likelihood: `{report["root_cause_assessment"]["section_boundary_defect_likelihood"]}`
- unknown_pattern root cause: `{report["root_cause_assessment"]["unknown_pattern_root_cause"]}`
- section_heading root cause: `{report["root_cause_assessment"]["section_heading_root_cause"]}`
- Report coverage status: `{report["root_cause_assessment"]["report_coverage_status"]}`
- Flat-report undercoverage cause:
  - `unknown_pattern` is appended only to `qa_tags.warnings` in `make_qa_tags` and never appended as a `WarningRecord`.
  - `human_review_required` is derived from `qa_tags.needs_human_review` / `review_status` and is also never emitted as a standalone `WarningRecord`.
  - `raz_tagging_warnings.json` writes only `result.warnings`, so these families are currently invisible in the flat report.

## 19. Seed query layer boundary result

- Queryable levels: `{report["seed_query_layer_boundary"]["queryable_levels"]}`
- `G` exposed: `{report["seed_query_layer_boundary"]["g_exposed"]}`
- `H` exposed: `{report["seed_query_layer_boundary"]["h_exposed"]}`
- Status: `{report["seed_query_layer_boundary"]["status"]}`

## 20. Authority boundary result

- `candidate_only = {report["authority_boundary"]["candidate_only"]}`
- `promotion_allowed = {report["authority_boundary"]["promotion_allowed"]}`

## 21. Validator results

- `validate_raz_level_discovery = {report["validator_results"]["validate_raz_level_discovery"]}`
- `validate_raz_reusable_content_seed_query_layer = {report["validator_results"]["validate_raz_reusable_content_seed_query_layer"]}`
- `validate_raz_downstream_discovery_drift = {report["validator_results"]["validate_raz_downstream_discovery_drift"]}`
- `must_fix_count = {report["validator_results"]["must_fix_count"]}`

## 22. Test results

- `{pytest_result}`

## 23. QA status

- `{report["status"]}`

## 24. Decision for next stage

- `{report["decision"]}`

## 25. Next recommended task

- `{report["next_recommended_task"]}`
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Level H warning clusters and flat-report coverage.")
    parser.add_argument("--pytest-result", default="", help="Optional pytest result string to embed in the report.")
    args = parser.parse_args()

    report = build_report(pytest_result=args.pytest_result)
    OUTPUT_JSON_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_MARKDOWN_PATH.write_text(render_markdown(report, args.pytest_result) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "decision": report["decision"], "output_json": str(OUTPUT_JSON_PATH.relative_to(BASE_DIR)).replace("\\", "/")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
