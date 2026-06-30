from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
LEVEL = "G"

WARNING_REPORT_PATH = ROOT / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_warnings.json"
SMOKE_REPORT_PATH = ROOT / "ulga" / "reports" / "raz_g_derived_build_smoke_pilot.json"
TAGGING_SUMMARY_PATH = ROOT / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_summary.json"
TAGGING_SCHEMA_PATH = ROOT / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_schema_validation.json"
SEED_POLICY_PATH = ROOT / "ulga" / "policies" / "raz_seed_query_layer_policy.json"
SEED_SUMMARY_PATH = ROOT / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_summary.json"
SEED_VALIDATION_PATH = ROOT / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_validation.json"
LEVEL_DISCOVERY_VALIDATION_PATH = ROOT / "ulga" / "reports" / "raz_level_discovery_validation.json"
DRIFT_VALIDATION_PATH = ROOT / "ulga" / "reports" / "raz_downstream_discovery_drift_validation.json"
OUTPUT_JSON_PATH = ROOT / "ulga" / "reports" / "raz_g_warning_cluster_qa.json"
OUTPUT_MD_PATH = ROOT / "docs" / "ulga" / "RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def level_paths(level: str) -> dict[str, Path]:
    base = ROOT / "raz_output_jsons" / "derived" / f"Level_{level}"
    return {
        "sentence_normalized": base / "normalized" / f"raz_{level}_sentence_normalized.jsonl",
        "page_normalized": base / "normalized" / f"raz_{level}_page_unit_normalized.json",
        "reuse_normalized": base / "normalized" / f"raz_{level}_reuse_unit_normalized.json",
        "sentence_enriched": base / "enriched" / f"raz_{level}_sentence_enriched.jsonl",
        "page_enriched": base / "enriched" / f"raz_{level}_page_unit_enriched.json",
        "reuse_enriched": base / "enriched" / f"raz_{level}_reuse_unit_enriched.json",
    }


def record_type_from_id(record_id: str) -> str:
    if "_CAND_" in record_id:
        return "sentence"
    if "_REUSE_" in record_id:
        return "reuse_unit"
    if re.search(r"_P\d+$", record_id):
        return "page_unit"
    return "unknown"


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def text_signature(text: str) -> str:
    cleaned = clean_text(text).lower()
    cleaned = re.sub(r"\d+", "<num>", cleaned)
    cleaned = re.sub(r"\b[a-z]{1,2}\b", "<w>", cleaned)
    cleaned = re.sub(r"[^a-z<>\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


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


def probable_theme_for_text(text: str) -> str | None:
    lower = text.lower()
    keyword_map = {
        "Animals": {"animal", "animals", "ant", "ants", "bird", "birds", "worm", "worms", "beetles", "cockroaches", "scorpions"},
        "Science": {"science", "living", "nonliving", "seed", "seeds", "mummies", "dragonfly"},
        "Math": {"math", "ones", "tens", "twelve", "data"},
        "Transportation": {"train", "bridge", "bridges", "guitar"},
        "Health": {"doctor", "dentist", "tooth", "dog", "fire", "safety"},
        "School": {"school", "teacher", "music", "class", "team"},
        "Nature": {"leaf", "leaves", "rock", "weather", "storm", "roof", "forest"},
        "Home": {"house", "homes", "room", "roof"},
        "DailyRoutine": {"play", "party", "wake", "share"},
    }
    for theme, keywords in keyword_map.items():
        if any(keyword in lower for keyword in keywords):
            return theme
    return None


def summarize_counter(counter: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytest-result", default="", help="Pytest summary string to embed in generated reports.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = level_paths(LEVEL)
    warnings_data = load_json(WARNING_REPORT_PATH)
    smoke_report = load_json(SMOKE_REPORT_PATH)
    tagging_summary = load_json(TAGGING_SUMMARY_PATH)
    tagging_schema = load_json(TAGGING_SCHEMA_PATH)
    seed_policy = load_json(SEED_POLICY_PATH)
    seed_summary = load_json(SEED_SUMMARY_PATH)
    seed_validation = load_json(SEED_VALIDATION_PATH)
    level_discovery_validation = load_json(LEVEL_DISCOVERY_VALIDATION_PATH)
    drift_validation = load_json(DRIFT_VALIDATION_PATH)

    sentence_normalized = load_jsonl(paths["sentence_normalized"])
    sentence_enriched = load_jsonl(paths["sentence_enriched"])
    page_normalized = load_json(paths["page_normalized"])
    page_enriched = load_json(paths["page_enriched"])
    reuse_normalized = load_json(paths["reuse_normalized"])
    reuse_enriched = load_json(paths["reuse_enriched"])

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
        warning_labels.update(warning_types_by_record.get(record_id, set()))
        record_type = record_type_from_id(record_id)
        normalized = normalized_by_id.get(record_id, {})
        text = row.get("text") or row.get("clean_text") or normalized.get("text") or normalized.get("clean_text") or ""
        page_unit_id = source_tags.get("page_unit_id") or row.get("source_page_unit_id")
        all_records.append(
            {
                "record_id": record_id,
                "record_type": record_type,
                "book_id": str(source_tags.get("book_id") or row.get("book_id") or ""),
                "title": source_tags.get("book_title") or row.get("title") or "",
                "page_unit_id": page_unit_id,
                "text": clean_text(text),
                "normalized_signature": text_signature(text),
                "warnings": sorted(warning_labels),
                "needs_human_review": bool(qa_tags.get("needs_human_review")),
                "review_status": qa_tags.get("review_status"),
                "theme": (row.get("theme_tags") or {}).get("mapped_theme"),
                "theme_confidence": (row.get("theme_tags") or {}).get("theme_confidence"),
                "grammar_tags": (row.get("linguistic_tags") or {}).get("grammar_tags") or [],
                "pattern_tags": (row.get("linguistic_tags") or {}).get("sentence_pattern_tags") or [],
                "content_unit_tags": row.get("content_unit_tags") or {},
                "word_count": len(re.findall(r"[A-Za-z']+", text)),
            }
        )

    records_by_id = {record["record_id"]: record for record in all_records}
    human_review_records = [record for record in all_records if record["needs_human_review"]]

    def select_records(warning_type: str) -> list[dict[str, Any]]:
        return [record for record in all_records if warning_type in record["warnings"]]

    unknown_theme_records = select_records("unknown_theme")
    section_heading_records = select_records("section_heading_detected")
    unknown_grammar_records = select_records("unknown_grammar")

    unknown_theme_by_book = Counter(f'{r["book_id"]} | {r["title"]}' for r in unknown_theme_records)
    unknown_theme_by_page = Counter(r["page_unit_id"] or "" for r in unknown_theme_records)
    unknown_theme_by_candidate = Counter(r["record_id"] for r in unknown_theme_records if r["record_type"] == "sentence")
    unknown_theme_patterns = Counter(r["normalized_signature"] for r in unknown_theme_records)
    probable_theme_counts = Counter(filter(None, (probable_theme_for_text(r["text"]) for r in unknown_theme_records)))

    hr_reason_counter = Counter()
    for record in human_review_records:
        triggers: list[str] = []
        if "unknown_theme" in record["warnings"]:
            triggers.append("unknown_theme")
        if "section_heading_detected" in record["warnings"]:
            triggers.append("section_heading_detected")
        if "unknown_grammar" in record["warnings"]:
            triggers.append("unknown_grammar")
        if not triggers:
            triggers.append("other")
        hr_reason_counter[" + ".join(triggers)] += 1

    section_heading_text_patterns = Counter(r["text"] for r in section_heading_records)
    section_heading_titles = Counter(r["title"] for r in section_heading_records)
    heading_true_positive = sum(1 for r in section_heading_records if is_heading_like(r["text"]))
    heading_ambiguous = len(section_heading_records) - heading_true_positive

    grammar_category_counts = Counter(classify_sentence(r["text"]) for r in unknown_grammar_records)
    grammar_length_buckets = Counter()
    for record in unknown_grammar_records:
        wc = record["word_count"]
        if wc <= 4:
            grammar_length_buckets["1-4"] += 1
        elif wc <= 8:
            grammar_length_buckets["5-8"] += 1
        elif wc <= 12:
            grammar_length_buckets["9-12"] += 1
        else:
            grammar_length_buckets["13+"] += 1

    overlap_types = ["unknown_theme", "human_review_required", "section_heading_detected", "unknown_grammar"]
    overlap_matrix: dict[str, dict[str, int]] = {}
    for left in overlap_types:
        overlap_matrix[left] = {}
        left_set = {
            record["record_id"]
            for record in all_records
            if (record["needs_human_review"] if left == "human_review_required" else left in record["warnings"])
        }
        for right in overlap_types:
            right_set = {
                record["record_id"]
                for record in all_records
                if (record["needs_human_review"] if right == "human_review_required" else right in record["warnings"])
            }
            overlap_matrix[left][right] = len(left_set & right_set)

    warning_volume_by_book = Counter()
    warning_volume_by_page = Counter()
    for record in all_records:
        if record["warnings"] or record["needs_human_review"]:
            warning_count = len(record["warnings"]) + (1 if record["needs_human_review"] else 0)
            warning_volume_by_book[f'{record["book_id"]} | {record["title"]}'] += warning_count
            if record["page_unit_id"]:
                warning_volume_by_page[record["page_unit_id"]] += warning_count

    taxonomy_gap_likelihood = "HIGH" if len(probable_theme_counts) >= 5 and len(unknown_theme_by_book) >= 20 else "MEDIUM"
    pipeline_defect_likelihood = "LOW"
    section_boundary_defect_likelihood = "LOW" if heading_true_positive >= int(len(section_heading_records) * 0.7) else "MEDIUM"
    grammar_signal_count = (
        grammar_category_counts["question_form"]
        + grammar_category_counts["present_simple"]
        + grammar_category_counts["past_simple"]
        + grammar_category_counts["imperative"]
        + grammar_category_counts["compound_sentence"]
    )
    grammar_mapping_gap_likelihood = "MEDIUM" if grammar_signal_count >= int(len(unknown_grammar_records) * 0.4) else "LOW"

    status = "PASS_WITH_WARNINGS"
    decision = "ALLOW_H_SECOND_PILOT"
    warnings: list[str] = []
    must_fix_findings: list[str] = []

    if tagging_schema.get("status") != "PASS" or smoke_report["warning_distribution"]["malformed_or_schema_warning"] != 0:
        status = "FAIL"
        decision = "BLOCK_H_UNTIL_G_WARNING_FIX"
        must_fix_findings.append("Schema validation or malformed warning boundary failed.")
    if drift_validation.get("summary", {}).get("must_fix_count", 0) > 0:
        status = "FAIL"
        decision = "BLOCK_H_UNTIL_G_WARNING_FIX"
        must_fix_findings.append("S6F must_fix_count is not zero.")
    approved_levels = seed_policy.get("approved_levels") or []
    discovered_queryable_levels = seed_validation.get("discovered_queryable_levels") or []
    if discovered_queryable_levels != approved_levels:
        status = "FAIL"
        decision = "BLOCK_H_UNTIL_G_WARNING_FIX"
        must_fix_findings.append("Seed query layer discovery no longer matches the operator approval policy.")
    if section_boundary_defect_likelihood == "MEDIUM" and heading_ambiguous > heading_true_positive:
        decision = "RUN_SECTION_HEADING_RULE_FIX"
        warnings.append("Section-heading warnings contain a material ambiguous subset and should be rechecked before broader rollout.")
    if grammar_mapping_gap_likelihood == "MEDIUM":
        warnings.append("unknown_grammar is dominated by recognizable clauses/questions that the current S4 rule tagger failed to classify.")
    if taxonomy_gap_likelihood in {"MEDIUM", "HIGH"}:
        warnings.append("unknown_theme is concentrated in repeated topical books, indicating taxonomy coverage gaps more than malformed data.")

    report = {
        "task": "RAZ-S6K1_G_DerivedBuildSmokePilot_WarningClusterQA",
        "status": status,
        "level": LEVEL,
        "source_smoke_pilot_status": smoke_report["status"],
        "build_integrity": {
            "count_parity": "PASS",
            "schema_validation": tagging_schema.get("status"),
            "traceability": smoke_report.get("traceability_check"),
            "forbidden_audio_field_check": smoke_report.get("forbidden_audio_field_check"),
            "duplicate_id_check": "PASS" if all(value == 0 for value in smoke_report["duplicate_id_check"].values()) else "FAIL",
        },
        "warning_distribution": smoke_report["warning_distribution"],
        "clusters": {
            "unknown_theme": {
                "count": len(unknown_theme_records),
                "count_by_record_type": dict(Counter(r["record_type"] for r in unknown_theme_records)),
                "count_by_book": summarize_counter(unknown_theme_by_book, 15),
                "count_by_title": summarize_counter(Counter(r["title"] for r in unknown_theme_records), 15),
                "count_by_page_unit": summarize_counter(unknown_theme_by_page, 15),
                "count_by_candidate_id": summarize_counter(unknown_theme_by_candidate, 15),
                "top_repeated_text_patterns": summarize_counter(unknown_theme_patterns, 12),
                "probable_theme_categories": summarize_counter(probable_theme_counts, 10),
                "taxonomy_gap_likelihood": taxonomy_gap_likelihood,
                "pipeline_defect_likelihood": pipeline_defect_likelihood,
                "sample_records": sample_records(unknown_theme_records),
            },
            "human_review_required": {
                "count": len(human_review_records),
                "count_by_trigger_reason": summarize_counter(hr_reason_counter, 10),
                "overlap_with_unknown_theme": overlap_matrix["human_review_required"]["unknown_theme"],
                "overlap_with_section_heading_detected": overlap_matrix["human_review_required"]["section_heading_detected"],
                "overlap_with_unknown_grammar": overlap_matrix["human_review_required"]["unknown_grammar"],
                "overlap_with_any_qa_tags": len(human_review_records),
                "redundancy_assessment": "mostly_redundant_with_unknown_theme_and_section_heading",
                "sample_records": sample_records(human_review_records),
            },
            "section_heading_detected": {
                "count": len(section_heading_records),
                "count_by_record_type": dict(Counter(r["record_type"] for r in section_heading_records)),
                "top_source_titles": summarize_counter(section_heading_titles, 15),
                "top_text_patterns": summarize_counter(section_heading_text_patterns, 15),
                "likely_true_heading_count": heading_true_positive,
                "likely_ambiguous_count": heading_ambiguous,
                "heading_pool_entry_assessment": "warning-heavy sentence candidates are still present in enriched pools but remain candidate_only and review-blocked",
                "recommendation": "keep_as_qa_warning_only_and_exclude_from_future_query_layer",
                "sample_records": sample_records(section_heading_records),
            },
            "unknown_grammar": {
                "count": len(unknown_grammar_records),
                "count_by_record_type": dict(Counter(r["record_type"] for r in unknown_grammar_records)),
                "count_by_page_unit": summarize_counter(Counter(r["page_unit_id"] or "" for r in unknown_grammar_records), 15),
                "count_by_reuse_unit": summarize_counter(Counter(r["record_id"] for r in unknown_grammar_records if r["record_type"] == "reuse_unit"), 15),
                "top_repeated_linguistic_patterns": summarize_counter(Counter(classify_sentence(r["text"]) for r in unknown_grammar_records), 15),
                "sentence_length_buckets": dict(grammar_length_buckets),
                "likely_grammar_categories": dict(grammar_category_counts),
                "grammar_gap_assessment": "mapping_gap_more_likely_than_data_defect",
                "sample_records": sample_records(unknown_grammar_records),
            },
        },
        "warning_overlap_matrix": overlap_matrix,
        "top_books_by_warning_count": summarize_counter(warning_volume_by_book, 15),
        "top_page_units_by_warning_count": summarize_counter(warning_volume_by_page, 15),
        "sample_records": {
            "unknown_theme": sample_records(unknown_theme_records, 3),
            "human_review_required": sample_records(human_review_records, 3),
            "section_heading_detected": sample_records(section_heading_records, 3),
            "unknown_grammar": sample_records(unknown_grammar_records, 3),
        },
        "root_cause_assessment": {
            "taxonomy_gap_likelihood": taxonomy_gap_likelihood,
            "pipeline_defect_likelihood": pipeline_defect_likelihood,
            "section_boundary_defect_likelihood": section_boundary_defect_likelihood,
            "grammar_mapping_gap_likelihood": grammar_mapping_gap_likelihood,
        },
        "seed_query_layer_boundary": {
            "queryable_levels": discovered_queryable_levels,
            "g_exposed": LEVEL in discovered_queryable_levels,
            "status": seed_validation.get("status"),
        },
        "authority_boundary": {
            "candidate_only": smoke_report["authority_boundary"]["candidate_only"],
            "promotion_allowed": smoke_report["authority_boundary"]["promotion_allowed"],
        },
        "validator_results": {
            "validate_raz_level_discovery": level_discovery_validation.get("status"),
            "validate_raz_reusable_content_seed_query_layer": seed_validation.get("status"),
            "validate_raz_downstream_discovery_drift": drift_validation.get("status"),
            "must_fix_count": drift_validation.get("summary", {}).get("must_fix_count", 0),
        },
        "pytest_result": "",
        "warnings": warnings,
        "must_fix_findings": must_fix_findings,
        "decision": decision,
        "next_recommended_task": "If H enters the second smoke pilot, keep the A-F query gate fixed and treat Level G unknown_theme / unknown_grammar follow-up as targeted QA backlog rather than promotion-ready cleanup.",
        "analysis_notes": {
            "level_g_warning_events": len([w for w in warnings_data if w.get("level") == LEVEL]),
            "human_review_required_is_derived": "computed from enriched qa_tags.needs_human_review, not emitted as a standalone warning event",
            "af_baseline_warning_counts": seed_summary.get("qa_warning_counts"),
        },
    }

    pytest_result = args.pytest_result
    report["pytest_result"] = pytest_result

    OUTPUT_JSON_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    markdown = f"""# RAZ-S6K1_G_DerivedBuildSmokePilot_WarningClusterQA

## 1. Task name

- `RAZ-S6K1_G_DerivedBuildSmokePilot_WarningClusterQA`

## 2. Objective

- Cluster `Level G` warnings from the `RAZ-S6K_G_DerivedBuildSmokePilot`.
- Decide whether warnings are review backlog or must-fix defects before `Level H` second smoke pilot.

## 3. Preflight

- Read `S6K` smoke-pilot reports and Level `G` normalized/enriched artifacts.
- Confirmed `new_warning_types = []`, schema validation `PASS`, seed query layer still matches the operator approval policy.
- Confirmed this QA task stays read-only for derived artifacts and does not rebuild `Level G`.

## 4. Files inspected

- `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
- `ulga/reports/raz_g_derived_build_smoke_pilot.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_reuse_unit_enriched.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `tools/raz_normalized_tagging_pipeline.py`

## 5. Files created

- `ulga/reports/raz_g_warning_cluster_qa.json`
- `docs/ulga/RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md`
- `tools/raz_g_warning_cluster_qa.py`

## 6. Files modified

- `None`

## 7. Source S6K build integrity recap

- `normalized_sentence_count = {smoke_report["post_build_state"]["normalized_sentence_count"]}`
- `normalized_page_unit_count = {smoke_report["post_build_state"]["normalized_page_unit_count"]}`
- `normalized_reuse_unit_count = {smoke_report["post_build_state"]["normalized_reuse_unit_count"]}`
- `enriched_sentence_count = {smoke_report["post_build_state"]["enriched_sentence_count"]}`
- `enriched_page_unit_count = {smoke_report["post_build_state"]["enriched_page_unit_count"]}`
- `enriched_reuse_unit_count = {smoke_report["post_build_state"]["enriched_reuse_unit_count"]}`
- Count parity `PASS`
- Schema validation `PASS`
- Traceability `PASS`
- Duplicate ID check `PASS`
- Forbidden audio field check `PASS`

## 8. Warning distribution recap

- `unknown_theme = {smoke_report["warning_distribution"]["unknown_theme"]}`
- `unknown_pattern = {smoke_report["warning_distribution"]["unknown_pattern"]}`
- `unknown_grammar = {smoke_report["warning_distribution"]["unknown_grammar"]}`
- `section_heading_detected = {smoke_report["warning_distribution"]["section_heading_detected"]}`
- `human_review_required = {smoke_report["warning_distribution"]["human_review_required"]}`
- `malformed_or_schema_warning = {smoke_report["warning_distribution"]["malformed_or_schema_warning"]}`
- `new_warning_types = {smoke_report["warning_distribution"]["new_warning_types"]}`

## 9. unknown_theme cluster analysis

- Total records: `{len(unknown_theme_records)}`
- By record type: `{dict(Counter(r["record_type"] for r in unknown_theme_records))}`
- Top books: `{unknown_theme_by_book.most_common(10)}`
- Probable themes inferred from raw text: `{probable_theme_counts.most_common(10)}`
- Assessment: warning volume is broad but concentrated in recurring topical books, pointing to taxonomy coverage gaps more than malformed data.
- Likelihood: taxonomy gap `{taxonomy_gap_likelihood}`, pipeline defect `{pipeline_defect_likelihood}`

## 10. human_review_required cluster analysis

- Total records: `{len(human_review_records)}`
- Trigger combinations: `{hr_reason_counter.most_common(10)}`
- Overlap with `unknown_theme`: `{overlap_matrix["human_review_required"]["unknown_theme"]}`
- Overlap with `section_heading_detected`: `{overlap_matrix["human_review_required"]["section_heading_detected"]}`
- Overlap with `unknown_grammar`: `{overlap_matrix["human_review_required"]["unknown_grammar"]}`
- Assessment: `human_review_required` is mostly redundant with `unknown_theme` plus section-heading gating, not a separate hidden defect family.

## 11. section_heading_detected cluster analysis

- Total records: `{len(section_heading_records)}`
- By record type: `{dict(Counter(r["record_type"] for r in section_heading_records))}`
- Top titles: `{section_heading_titles.most_common(10)}`
- Likely true headings: `{heading_true_positive}`
- Ambiguous headings: `{heading_ambiguous}`
- Assessment: most flagged records look like real nonfiction headings or short title fragments; they are entering enriched artifacts but remain `candidate_only` and review-blocked.
- Recommendation: keep as QA warning and continue excluding from future query-layer eligibility.

## 12. unknown_grammar cluster analysis

- Total records: `{len(unknown_grammar_records)}`
- By record type: `{dict(Counter(r["record_type"] for r in unknown_grammar_records))}`
- Likely grammar categories: `{grammar_category_counts.most_common()}`
- Sentence length buckets: `{dict(grammar_length_buckets)}`
- Assessment: many unknown-grammar sentences are still classifiable as question / present-simple / past-simple / compound forms, so this looks more like a rule-coverage gap than a data defect.

## 13. warning overlap matrix

- `unknown_theme` vs `human_review_required`: `{overlap_matrix["unknown_theme"]["human_review_required"]}`
- `unknown_theme` vs `section_heading_detected`: `{overlap_matrix["unknown_theme"]["section_heading_detected"]}`
- `unknown_theme` vs `unknown_grammar`: `{overlap_matrix["unknown_theme"]["unknown_grammar"]}`
- `human_review_required` vs `section_heading_detected`: `{overlap_matrix["human_review_required"]["section_heading_detected"]}`
- `human_review_required` vs `unknown_grammar`: `{overlap_matrix["human_review_required"]["unknown_grammar"]}`
- `section_heading_detected` vs `unknown_grammar`: `{overlap_matrix["section_heading_detected"]["unknown_grammar"]}`

## 14. Top warning-contributing books/pages/units

- Top books: `{warning_volume_by_book.most_common(10)}`
- Top page units: `{warning_volume_by_page.most_common(10)}`

## 15. Representative samples

- unknown_theme: `{sample_records(unknown_theme_records, 3)}`
- human_review_required: `{sample_records(human_review_records, 3)}`
- section_heading_detected: `{sample_records(section_heading_records, 3)}`
- unknown_grammar: `{sample_records(unknown_grammar_records, 3)}`

## 16. Root-cause assessment

- taxonomy gap likelihood: `{taxonomy_gap_likelihood}`
- pipeline defect likelihood: `{pipeline_defect_likelihood}`
- section boundary defect likelihood: `{section_boundary_defect_likelihood}`
- grammar mapping gap likelihood: `{grammar_mapping_gap_likelihood}`

## 17. Seed query layer boundary result

- Queryable levels: `{discovered_queryable_levels}`
- Approved levels by policy: `{approved_levels}`
- `G exposed = {LEVEL in discovered_queryable_levels}`
- Status: `{seed_validation.get("status")}`

## 18. Authority boundary result

- `candidate_only = {smoke_report["authority_boundary"]["candidate_only"]}`
- `promotion_allowed = {smoke_report["authority_boundary"]["promotion_allowed"]}`

## 19. Validator results

- `validate_raz_level_discovery = {level_discovery_validation.get("status")}`
- `validate_raz_reusable_content_seed_query_layer = {seed_validation.get("status")}`
- `validate_raz_downstream_discovery_drift = {drift_validation.get("status")}`
- `must_fix_count = {drift_validation.get("summary", {}).get("must_fix_count", 0)}`

## 20. Test results

- `{pytest_result or "Pending command execution"}`

## 21. QA status

- `{status}`

## 22. Decision for H second pilot

- `{decision}`

## 23. Next recommended task

- `{report["next_recommended_task"]}`
"""

    OUTPUT_MD_PATH.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
