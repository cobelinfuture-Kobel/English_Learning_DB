from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]

TASK_NAME = "RAZ-S6Q_GH_TaggingRerunDeltaQA"
LEVELS = ("G", "H")
WARNING_FAMILIES = [
    "unknown_theme",
    "unknown_pattern",
    "unknown_grammar",
    "section_heading_detected",
    "human_review_required",
    "malformed_or_schema_warning",
    "dialogue_or_quotation_warning",
]
TARGET_PATTERN_TAGS = {"simple_declarative_svo", "simple_declarative_svc"}

S6P_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6P_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_IMPLEMENTATION.md"
S6P_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_gh_targeted_taxonomy_and_pattern_patch_implementation.json"
S6O_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6O_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN.md"
S6O_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_gh_targeted_taxonomy_and_pattern_patch_plan.json"
S6N_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6N_WARNING_REPORT_COVERAGE_PATCH.md"
S6N_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_warning_report_coverage_patch.json"
S6M_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md"
S6M_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_h_warning_cluster_and_report_coverage_qa.json"

SUMMARY_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_summary.json"
WARNING_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_warnings.json"
SCHEMA_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_schema_validation.json"

SEED_POLICY_PATH = BASE_DIR / "ulga" / "policies" / "raz_seed_query_layer_policy.json"
LEVEL_DISCOVERY_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_summary.json"
LEVEL_DISCOVERY_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_validation.json"
SEED_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_summary.json"
SEED_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_validation.json"
DRIFT_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_downstream_discovery_drift_validation.json"

OUTPUT_JSON_PATH = BASE_DIR / "ulga" / "reports" / "raz_gh_tagging_rerun_delta_qa.json"
OUTPUT_MARKDOWN_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6Q_GH_TAGGING_RERUN_DELTA_QA.md"

THEME_AUDIT_GROUPS = {
    "science_nature_samples": {
        "titles": {"Amazing Mummies", "My Bones", "Our Five Senses", "What Lives in This Hole?"},
        "allowed_themes": {"Science", "Nature", "Body", "Health"},
        "label": "science/nature/body/health",
    },
    "history_civics_samples": {
        "titles": {"Abigail Adams", "American Symbols", "A President's Day", "Dr. King's Memorial", "Harriet Tubman"},
        "allowed_themes": {"Community"},
        "label": "history/biography/civics",
    },
    "animal_nonfiction_samples": {
        "titles": {"Miles the Nile Crocodile", "Elephants: Giant Mammals", "Scorpions", "Cockroaches", "Flies", "Condors: Giant Birds"},
        "allowed_themes": {"Animals"},
        "label": "animal nonfiction",
    },
    "folktale_storyfable_samples": {
        "titles": {"Rapunzel", "The Empty Pot", "Troll Bridge", "The Stonecutter", "Cinderella", "The Goat and the Singing Wolf"},
        "allowed_themes": {"StoryFable"},
        "label": "folktale/storyfable",
    },
}


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


def stable_path(path: Path) -> str:
    return path.relative_to(BASE_DIR).as_posix()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()


def pattern_bucket(text: str) -> str:
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


def is_quoted_or_direct_speech(record: dict[str, Any]) -> bool:
    text = record.get("text") or ""
    if '"' in text or "“" in text or "”" in text:
        return True
    return bool(record.get("is_direct_speech"))


def infer_record_type(record_id: str, content_unit_type: str | None) -> str:
    if content_unit_type:
        return content_unit_type
    if "_P" in record_id and "_CAND_" not in record_id and "_REUSE_" not in record_id:
        return "page_unit"
    if "_REUSE_" in record_id:
        return "reuse_unit"
    return "sentence"


def count_family(records: list[dict[str, Any]], family: str) -> int:
    if family == "human_review_required":
        return sum(1 for record in records if record["needs_human_review"])
    return sum(1 for record in records if family in record["warnings"])


def classify_family(*, family: str, baseline: int, current: int) -> str:
    if family in {"unknown_theme", "unknown_pattern", "human_review_required"}:
        return "EXPECTED_IMPROVEMENT" if current < baseline else "FAIL_REGRESSION"
    if family in {"unknown_grammar", "section_heading_detected"}:
        return "STABLE_ACCEPTABLE" if current <= baseline else "REVIEW_REQUIRED"
    if family in {"malformed_or_schema_warning", "dialogue_or_quotation_warning"}:
        return "STABLE_ACCEPTABLE" if current == 0 else "REVIEW_REQUIRED"
    return "REVIEW_REQUIRED"


def select_examples(records: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for record in records[:limit]:
        examples.append(
            {
                "record_id": record["record_id"],
                "record_type": record["record_type"],
                "title": record["title"],
                "book_id": record["book_id"],
                "page_unit_id": record.get("page_unit_id"),
                "text": record["text"],
                "mapped_theme": record["mapped_theme"],
                "pattern_tags": record["pattern_tags"],
                "warnings": record["warnings"],
            }
        )
    return examples


def summarize_test_results(test_results: dict[str, str]) -> list[str]:
    return [f"- `{key}`: `{value}`" for key, value in test_results.items()]


def build_level_paths(level: str) -> dict[str, Path]:
    root = BASE_DIR / "raz_output_jsons" / "derived" / f"Level_{level}"
    return {
        "sentence_normalized": root / "normalized" / f"raz_{level}_sentence_normalized.jsonl",
        "page_normalized": root / "normalized" / f"raz_{level}_page_unit_normalized.json",
        "reuse_normalized": root / "normalized" / f"raz_{level}_reuse_unit_normalized.json",
        "sentence_enriched": root / "enriched" / f"raz_{level}_sentence_enriched.jsonl",
        "page_enriched": root / "enriched" / f"raz_{level}_page_unit_enriched.json",
        "reuse_enriched": root / "enriched" / f"raz_{level}_reuse_unit_enriched.json",
    }


def load_level_records(level: str, flat_warnings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, Any]]:
    paths = build_level_paths(level)
    normalized_by_id: dict[str, dict[str, Any]] = {}
    enriched_by_id: dict[str, dict[str, Any]] = {}

    normalized_sentence = load_jsonl(paths["sentence_normalized"])
    normalized_page = load_json(paths["page_normalized"])
    normalized_reuse = load_json(paths["reuse_normalized"])
    enriched_sentence = load_jsonl(paths["sentence_enriched"])
    enriched_page = load_json(paths["page_enriched"])
    enriched_reuse = load_json(paths["reuse_enriched"])

    for row in normalized_sentence:
        normalized_by_id[row["candidate_id"]] = row
    for row in normalized_page:
        normalized_by_id[row["page_unit_id"]] = row
    for row in normalized_reuse:
        normalized_by_id[row["reuse_unit_id"]] = row

    for row in enriched_sentence:
        enriched_by_id[row["candidate_id"]] = row
    for row in enriched_page:
        enriched_by_id[row["page_unit_id"]] = row
    for row in enriched_reuse:
        enriched_by_id[row["reuse_unit_id"]] = row

    warning_types_by_record: dict[str, set[str]] = defaultdict(set)
    for row in flat_warnings:
        if row.get("level") == level:
            warning_types_by_record[str(row["record_id"])].add(str(row["warning_type"]))

    records: list[dict[str, Any]] = []
    for record_id, row in enriched_by_id.items():
        qa_tags = row.get("qa_tags") or {}
        source_tags = row.get("source_tags") or {}
        content_unit_tags = row.get("content_unit_tags") or {}
        linguistic_tags = row.get("linguistic_tags") or {}
        warnings = set(qa_tags.get("warnings") or [])
        if qa_tags.get("needs_human_review"):
            warnings.add("human_review_required")
        warnings.update(warning_types_by_record.get(record_id, set()))

        normalized = normalized_by_id.get(record_id, {})
        text = row.get("text") or row.get("clean_text") or normalized.get("text") or normalized.get("clean_text") or ""
        records.append(
            {
                "record_id": record_id,
                "record_type": infer_record_type(record_id, content_unit_tags.get("content_unit_type")),
                "book_id": str(source_tags.get("book_id") or row.get("book_id") or ""),
                "title": str(source_tags.get("book_title") or row.get("title") or ""),
                "page_unit_id": source_tags.get("page_unit_id") or row.get("source_page_unit_id") or row.get("page_unit_id"),
                "text": clean_text(text),
                "warnings": sorted(warnings),
                "needs_human_review": bool(qa_tags.get("needs_human_review")),
                "review_status": qa_tags.get("review_status"),
                "mapped_theme": (row.get("theme_tags") or {}).get("mapped_theme"),
                "theme_confidence": (row.get("theme_tags") or {}).get("theme_confidence"),
                "pattern_tags": list(linguistic_tags.get("sentence_pattern_tags") or []),
                "grammar_tags": list(linguistic_tags.get("grammar_tags") or []),
                "is_heading": bool(content_unit_tags.get("is_heading")),
                "is_direct_speech": bool(content_unit_tags.get("is_direct_speech")),
                "is_question": bool(content_unit_tags.get("is_question")),
                "is_imperative": bool(content_unit_tags.get("is_imperative")),
            }
        )

    counts = {
        "sentence_normalized": len(normalized_sentence),
        "page_normalized": len(normalized_page),
        "reuse_normalized": len(normalized_reuse),
        "sentence_enriched": len(enriched_sentence),
        "page_enriched": len(enriched_page),
        "reuse_enriched": len(enriched_reuse),
    }
    details = {"paths": {key: stable_path(path) for key, path in paths.items()}}
    return records, counts, details


def build_theme_audit_group(records: list[dict[str, Any]], *, titles: set[str], allowed_themes: set[str], label: str) -> dict[str, Any]:
    candidates = [record for record in records if record["record_type"] == "sentence" and record["title"] in titles]
    passed = [record for record in candidates if record["mapped_theme"] in allowed_themes and "unknown_theme" not in record["warnings"]]
    failed = [record for record in candidates if record not in passed]
    status = "PASS" if failed == [] and passed else "PASS_WITH_WARNINGS"
    return {
        "sample_count": len(candidates),
        "pass_count": len(passed),
        "suspicious_count": 0,
        "fail_count": len(failed),
        "examples": select_examples(failed or passed),
        "assessment": f"{label} samples align with current mapped themes." if failed == [] else f"{label} samples include records still unresolved or outside the expected theme family.",
        "status": status,
        "inference_note": "Current-state proxy sample. Exact pre-patch per-record diff is unavailable because S6O/S6P retained aggregate baselines, not full pre-patch snapshots.",
    }


def build_rule_pollution_audit(records_by_level: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    all_records = [record for records in records_by_level.values() for record in records]
    simple_records = [record for record in all_records if TARGET_PATTERN_TAGS & set(record["pattern_tags"])]
    simple_failed = [
        record
        for record in simple_records
        if record["is_heading"]
        or record["is_direct_speech"]
        or record["is_question"]
        or record["is_imperative"]
        or is_quoted_or_direct_speech(record)
        or pattern_bucket(record["text"]) in {"poetic_or_repetitive_line", "narrative_or_clause_inversion", "pronunciation_annotation"}
    ]

    heading_records = [record for record in all_records if record["is_heading"] or "section_heading_detected" in record["warnings"]]
    heading_failed = [record for record in heading_records if TARGET_PATTERN_TAGS & set(record["pattern_tags"])]

    dialogue_records = [record for record in all_records if is_quoted_or_direct_speech(record)]
    dialogue_failed = [record for record in dialogue_records if TARGET_PATTERN_TAGS & set(record["pattern_tags"])]

    deferred_records = [
        record for record in all_records
        if "unknown_pattern" in record["warnings"] and pattern_bucket(record["text"]) in {"poetic_or_repetitive_line", "narrative_or_clause_inversion", "pronunciation_annotation"}
    ]
    deferred_failed = [record for record in deferred_records if TARGET_PATTERN_TAGS & set(record["pattern_tags"])]

    def make_group(candidates: list[dict[str, Any]], failed: list[dict[str, Any]], ok_note: str, fail_note: str) -> dict[str, Any]:
        passed = [record for record in candidates if record not in failed]
        return {
            "sample_count": len(candidates),
            "pass_count": len(passed),
            "suspicious_count": 0,
            "fail_count": len(failed),
            "examples": select_examples(failed or passed),
            "assessment": ok_note if not failed else fail_note,
        }

    status = "PASS" if not (simple_failed or heading_failed or dialogue_failed or deferred_failed) else "FAIL"
    return {
        "status": status,
        "simple_declarative_samples": make_group(
            simple_records,
            simple_failed,
            "Current simple declarative tags stay inside ordinary declarative scope.",
            "Some simple declarative tags appear to overfire into excluded structures.",
        ),
        "heading_exclusion_samples": make_group(
            heading_records,
            heading_failed,
            "Section headings remain excluded from simple declarative tagging.",
            "Section headings appear to have been swallowed by simple declarative tagging.",
        ),
        "dialogue_exclusion_samples": make_group(
            dialogue_records,
            dialogue_failed,
            "Quoted/direct speech remains excluded from P0 declarative tags.",
            "Quoted/direct speech appears to have been swallowed by simple declarative tagging.",
        ),
        "poetry_inversion_artifact_samples": make_group(
            deferred_records,
            deferred_failed,
            "Deferred poetry/inversion/artifact residuals remain deferred and untagged by P0 declarative rules.",
            "Deferred poetry/inversion/artifact residuals appear to have been swallowed by simple declarative tagging.",
        ),
    }


def build_human_review_audit(records_by_level: dict[str, list[dict[str, Any]]], baseline_metrics: dict[str, dict[str, int]], current_metrics: dict[str, dict[str, int]]) -> dict[str, Any]:
    all_records = [record for records in records_by_level.values() for record in records]
    human_review_records = [record for record in all_records if record["needs_human_review"]]
    standalone = [
        record for record in human_review_records if [warning for warning in record["warnings"] if warning != "human_review_required"] == []
    ]
    trigger_counts = Counter()
    for record in human_review_records:
        triggers = [warning for warning in record["warnings"] if warning != "human_review_required"]
        trigger_counts[" + ".join(triggers) if triggers else "standalone"] += 1

    reductions = {
        level: baseline_metrics[level]["human_review_required_count"] - current_metrics[level]["human_review_required"]
        for level in LEVELS
    }
    return {
        "status": "PASS" if not standalone else "WARNING",
        "direct_suppression_detected": bool(standalone),
        "indirect_reduction_confirmed": not standalone,
        "standalone_human_review_count": len(standalone),
        "current_trigger_mix": dict(trigger_counts),
        "reductions": reductions,
        "assessment": "Every current human_review_required record still carries at least one underlying warning family, so the observed reduction is consistent with indirect overlap shrinkage." if not standalone else "Standalone human_review_required records exist and require review for possible direct suppression semantics drift.",
    }


def compute_count_parity(level: str, counts: dict[str, int], summary_report: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    summary_level = (summary_report.get("by_level") or {}).get(level) or {}
    parity_checks = {
        "sentence": counts["sentence_normalized"] == counts["sentence_enriched"] == summary_level.get("sentence_enriched_count"),
        "page_unit": counts["page_normalized"] == counts["page_enriched"] == summary_level.get("page_unit_enriched_count"),
        "reuse_unit": counts["reuse_normalized"] == counts["reuse_enriched"] == summary_level.get("reuse_unit_enriched_count"),
    }
    total = counts["sentence_enriched"] + counts["page_enriched"] + counts["reuse_enriched"]
    parity_checks["total"] = total == (
        summary_level.get("sentence_enriched_count", 0)
        + summary_level.get("page_unit_enriched_count", 0)
        + summary_level.get("reuse_unit_enriched_count", 0)
    )
    status = "PASS" if all(parity_checks.values()) else "FAIL"
    return status, {"checks": parity_checks, "enriched_record_count": total}


def build_report(test_results: dict[str, str] | None = None) -> dict[str, Any]:
    tests = test_results or {}
    s6p_report = load_json(S6P_REPORT_PATH)
    s6o_report = load_json(S6O_REPORT_PATH)
    s6n_report = load_json(S6N_REPORT_PATH)
    s6m_report = load_json(S6M_REPORT_PATH)
    summary_report = load_json(SUMMARY_REPORT_PATH)
    flat_warnings = load_json(WARNING_REPORT_PATH)
    schema_report = load_json(SCHEMA_REPORT_PATH)
    seed_policy = load_json(SEED_POLICY_PATH)
    level_discovery_summary = load_json(LEVEL_DISCOVERY_SUMMARY_PATH)
    level_discovery_validation = load_json(LEVEL_DISCOVERY_VALIDATION_PATH)
    seed_summary = load_json(SEED_SUMMARY_PATH)
    seed_validation = load_json(SEED_VALIDATION_PATH)
    drift_validation = load_json(DRIFT_VALIDATION_PATH)

    baseline_metrics = s6o_report["gh_warning_comparison"]
    current_metrics: dict[str, dict[str, int]] = {}
    delta_metrics: dict[str, dict[str, int]] = {}
    delta_classification: dict[str, dict[str, str]] = {}
    records_by_level: dict[str, list[dict[str, Any]]] = {}
    counts_by_level: dict[str, dict[str, int]] = {}
    count_parity: dict[str, str] = {}
    count_parity_details: dict[str, Any] = {}
    schema_validation = {level: "PASS" if schema_report.get("status") == "PASS" else "FAIL" for level in LEVELS}
    flat_report_coverage_rows: list[dict[str, Any]] = []
    coverage_failures = 0

    for level in LEVELS:
        records, counts, details = load_level_records(level, flat_warnings)
        records_by_level[level] = records
        counts_by_level[level] = counts
        parity_status, parity_details = compute_count_parity(level, counts, summary_report)
        count_parity[level] = parity_status
        count_parity_details[level] = parity_details | details

        flat_level_counts = Counter(row["warning_type"] for row in flat_warnings if row.get("level") == level)
        metrics = {
            "enriched_record_count": len(records),
            "unknown_theme": count_family(records, "unknown_theme"),
            "unknown_pattern": count_family(records, "unknown_pattern"),
            "unknown_grammar": count_family(records, "unknown_grammar"),
            "section_heading_detected": count_family(records, "section_heading_detected"),
            "human_review_required": count_family(records, "human_review_required"),
            "malformed_or_schema_warning": flat_level_counts.get("malformed_or_schema_warning", 0),
            "dialogue_or_quotation_warning": flat_level_counts.get("dialogue_or_quotation_warning", 0),
        }
        current_metrics[level] = metrics
        delta_metrics[level] = {
            "unknown_theme_delta": metrics["unknown_theme"] - baseline_metrics[level]["unknown_theme_count"],
            "unknown_pattern_delta": metrics["unknown_pattern"] - baseline_metrics[level]["unknown_pattern_count"],
            "unknown_grammar_delta": metrics["unknown_grammar"] - baseline_metrics[level]["unknown_grammar_count"],
            "section_heading_delta": metrics["section_heading_detected"] - baseline_metrics[level]["section_heading_detected_count"],
            "human_review_required_delta": metrics["human_review_required"] - baseline_metrics[level]["human_review_required_count"],
        }
        delta_classification[level] = {
            family: classify_family(
                family=family,
                baseline=baseline_metrics[level].get(f"{family}_count", baseline_metrics[level].get(family, 0)),
                current=metrics[family],
            )
            for family in WARNING_FAMILIES
        }

        for family in WARNING_FAMILIES:
            qa_count = metrics[family]
            flat_count = flat_level_counts.get(family, 0)
            row = {
                "level": level,
                "warning_family": family,
                "qa_tags_count": qa_count,
                "flat_report_count": flat_count,
                "coverage_delta": qa_count - flat_count,
                "coverage_status": "PASS" if qa_count == flat_count else "FAIL",
            }
            flat_report_coverage_rows.append(row)
            if row["coverage_status"] != "PASS":
                coverage_failures += 1

    duplicate_counter = Counter((row.get("level"), row.get("record_id"), row.get("warning_type")) for row in flat_warnings)
    duplicate_count = sum(count - 1 for count in duplicate_counter.values() if count > 1)
    missing_trace_count = sum(
        1
        for row in flat_warnings
        if not row.get("record_id") or not row.get("level") or not row.get("book_id") or not row.get("raw_file_path")
    )

    rule_pollution_audit = build_rule_pollution_audit(records_by_level)
    theme_mapping_audit = {
        "status": "PASS",
        **{
            key: build_theme_audit_group(records_by_level["G"] + records_by_level["H"], **config)
            for key, config in THEME_AUDIT_GROUPS.items()
        },
    }
    if any(group["fail_count"] > 0 for key, group in theme_mapping_audit.items() if key != "status"):
        theme_mapping_audit["status"] = "PASS_WITH_WARNINGS"

    human_review_audit = build_human_review_audit(records_by_level, baseline_metrics, current_metrics)

    queryable_levels = seed_validation.get("discovered_queryable_levels", [])
    seed_boundary_status = "PASS" if queryable_levels == seed_policy.get("approved_levels") else "FAIL"
    authority_boundary = {
        "candidate_only": "PASS" if drift_validation.get("candidate_only_invariant") == "PASS" else "FAIL",
        "promotion_allowed": "PASS" if drift_validation.get("promotion_allowed_invariant") == "PASS" else "FAIL",
    }

    validator_results = {
        "validate_raz_level_discovery": level_discovery_validation.get("status"),
        "validate_raz_reusable_content_seed_query_layer": seed_validation.get("status"),
        "validate_raz_downstream_discovery_drift": drift_validation.get("status"),
        "must_fix_count": (drift_validation.get("summary") or {}).get("must_fix_count", 0),
    }

    warnings: list[str] = [
        "Theme-mapping and changed-record samples are current-state proxies because no pre-patch per-record snapshot was retained in S6O/S6P artifacts.",
    ]

    if validator_results["must_fix_count"] > 0:
        warnings.append("S6F must_fix_count is nonzero.")
    if coverage_failures:
        warnings.append("Flat warning report coverage drift was detected.")

    fail_conditions = [
        coverage_failures > 0,
        any(status != "PASS" for status in count_parity.values()),
        any(status != "PASS" for status in schema_validation.values()),
        duplicate_count > 0,
        missing_trace_count > 0,
        seed_boundary_status != "PASS",
        authority_boundary["candidate_only"] != "PASS",
        authority_boundary["promotion_allowed"] != "PASS",
        validator_results["must_fix_count"] > 0,
        rule_pollution_audit["status"] == "FAIL",
        any(value == "FAIL_REGRESSION" for level_map in delta_classification.values() for value in level_map.values()),
        any(value.startswith("FAIL") for value in tests.values()),
    ]
    warning_conditions = [
        theme_mapping_audit["status"] != "PASS",
        human_review_audit["status"] != "PASS",
    ]

    if any(fail_conditions):
        status = "FAIL"
        decision = "BLOCK_FURTHER_EXPANSION"
        risk_level = "Medium"
    elif any(warning_conditions):
        status = "PASS_WITH_WARNINGS"
        decision = "RUN_GH_P1_PATCH_PLAN"
        risk_level = "Low"
    else:
        status = "PASS"
        decision = "RUN_GH_P1_PATCH_PLAN"
        risk_level = "Low"

    report = {
        "task": TASK_NAME,
        "status": status,
        "scope": {
            "levels_analyzed": list(LEVELS),
            "qa_only": True,
            "implementation_changes": False,
            "query_layer_expansion": False,
            "promotion": False,
            "i_w_processing": False,
            "cefr_or_adaptive": False,
        },
        "preflight": {
            "s6p_implementation_status": s6p_report.get("status"),
            "current_queryable_levels": queryable_levels,
            "current_s6f_must_fix_count": validator_results["must_fix_count"],
            "read_only_qa": True,
            "production_code_modified": False,
            "source_artifacts_trust": {
                "s6p": s6p_report.get("status"),
                "s6o": s6o_report.get("status"),
                "s6n": s6n_report.get("status"),
                "s6m": s6m_report.get("status"),
            },
        },
        "source_status": {
            "s6p_status": s6p_report.get("status"),
            "s6p_decision": s6p_report.get("decision"),
        },
        "files_inspected": [
            stable_path(S6P_DOC_PATH),
            stable_path(S6P_REPORT_PATH),
            stable_path(S6O_DOC_PATH),
            stable_path(S6O_REPORT_PATH),
            stable_path(S6N_DOC_PATH),
            stable_path(S6N_REPORT_PATH),
            stable_path(S6M_DOC_PATH),
            stable_path(S6M_REPORT_PATH),
            stable_path(SUMMARY_REPORT_PATH),
            stable_path(WARNING_REPORT_PATH),
            stable_path(SCHEMA_REPORT_PATH),
            stable_path(SEED_POLICY_PATH),
            stable_path(LEVEL_DISCOVERY_SUMMARY_PATH),
            stable_path(LEVEL_DISCOVERY_VALIDATION_PATH),
            stable_path(SEED_SUMMARY_PATH),
            stable_path(SEED_VALIDATION_PATH),
            stable_path(DRIFT_VALIDATION_PATH),
            stable_path(BASE_DIR / "tools" / "raz_normalized_tagging_pipeline.py"),
            stable_path(BASE_DIR / "tests" / "test_raz_normalized_tagging_pipeline.py"),
            stable_path(BASE_DIR / "tools" / "raz_h_warning_cluster_and_report_coverage_qa.py"),
            stable_path(BASE_DIR / "tests" / "ulga" / "test_raz_h_warning_cluster_and_report_coverage_qa.py"),
        ] + [
            stable_path(path)
            for level in LEVELS
            for path in build_level_paths(level).values()
        ],
        "files_created": [
            stable_path(BASE_DIR / "tools" / "raz_gh_tagging_rerun_delta_qa.py"),
            stable_path(BASE_DIR / "tests" / "ulga" / "test_raz_gh_tagging_rerun_delta_qa.py"),
            stable_path(OUTPUT_MARKDOWN_PATH),
            stable_path(OUTPUT_JSON_PATH),
        ],
        "files_modified": [
            stable_path(BASE_DIR / "tools" / "raz_gh_tagging_rerun_delta_qa.py"),
            stable_path(BASE_DIR / "tests" / "ulga" / "test_raz_gh_tagging_rerun_delta_qa.py"),
            stable_path(OUTPUT_MARKDOWN_PATH),
            stable_path(OUTPUT_JSON_PATH),
        ],
        "baseline_metrics": {
            level: {
                "enriched_record_count": baseline_metrics[level]["enriched_record_count"],
                "unknown_theme": baseline_metrics[level]["unknown_theme_count"],
                "unknown_pattern": baseline_metrics[level]["unknown_pattern_count"],
                "unknown_grammar": baseline_metrics[level]["unknown_grammar_count"],
                "section_heading_detected": baseline_metrics[level]["section_heading_detected_count"],
                "human_review_required": baseline_metrics[level]["human_review_required_count"],
            }
            for level in LEVELS
        },
        "current_metrics": current_metrics,
        "delta_metrics": delta_metrics,
        "delta_classification": delta_classification,
        "flat_report_coverage": {
            "status": "PASS" if coverage_failures == 0 else "FAIL",
            "coverage_matrix": flat_report_coverage_rows,
        },
        "count_parity": count_parity,
        "count_parity_details": count_parity_details,
        "schema_validation": schema_validation,
        "rule_pollution_audit": rule_pollution_audit,
        "theme_mapping_audit": theme_mapping_audit,
        "human_review_audit": human_review_audit,
        "duplicate_warning_check": {
            "status": "PASS" if duplicate_count == 0 else "FAIL",
            "duplicate_count": duplicate_count,
        },
        "traceability_check": {
            "status": "PASS" if missing_trace_count == 0 else "FAIL",
            "missing_trace_count": missing_trace_count,
        },
        "seed_query_layer_boundary": {
            "queryable_levels": queryable_levels,
            "g_exposed": "G" in queryable_levels,
            "h_exposed": "H" in queryable_levels,
            "status": seed_boundary_status,
        },
        "authority_boundary": authority_boundary,
        "validator_results": validator_results,
        "test_results": tests,
        "warnings": warnings,
        "must_fix_findings": [],
        "decision": decision,
        "next_recommended_task": "RAZ-S6R_GH_P1_PATCH_PLAN" if decision == "RUN_GH_P1_PATCH_PLAN" else "RAZ-I_DERIVED_BUILD_THIRD_SMOKE_PILOT",
        "risk_level": risk_level,
        "notes": {
            "level_discovery_summary_status": level_discovery_summary.get("levels_by_status"),
            "seed_summary_status": seed_summary.get("status"),
            "schema_validation_scope_note": "Current schema report is global. G/H per-level PASS is inferred because the report is PASS and this run only analyzed current G/H artifacts.",
        },
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    baseline_lines = []
    current_lines = []
    delta_lines = []
    classification_lines = []
    for level in LEVELS:
        baseline = report["baseline_metrics"][level]
        current = report["current_metrics"][level]
        delta = report["delta_metrics"][level]
        classes = report["delta_classification"][level]
        baseline_lines.append(f"- `{level}`: enriched={baseline['enriched_record_count']}, unknown_theme={baseline['unknown_theme']}, unknown_pattern={baseline['unknown_pattern']}, unknown_grammar={baseline['unknown_grammar']}, section_heading={baseline['section_heading_detected']}, human_review={baseline['human_review_required']}")
        current_lines.append(f"- `{level}`: enriched={current['enriched_record_count']}, unknown_theme={current['unknown_theme']}, unknown_pattern={current['unknown_pattern']}, unknown_grammar={current['unknown_grammar']}, section_heading={current['section_heading_detected']}, human_review={current['human_review_required']}, malformed={current['malformed_or_schema_warning']}, dialogue={current['dialogue_or_quotation_warning']}")
        delta_lines.append(f"- `{level}`: unknown_theme={delta['unknown_theme_delta']}, unknown_pattern={delta['unknown_pattern_delta']}, unknown_grammar={delta['unknown_grammar_delta']}, section_heading={delta['section_heading_delta']}, human_review={delta['human_review_required_delta']}")
        classification_lines.append(f"- `{level}`: {classes}")

    coverage_lines = [
        f"- `{row['level']} / {row['warning_family']}`: qa_tags={row['qa_tags_count']}, flat={row['flat_report_count']}, delta={row['coverage_delta']}, status={row['coverage_status']}"
        for row in report["flat_report_coverage"]["coverage_matrix"]
    ]

    test_lines = summarize_test_results(report["test_results"]) if report["test_results"] else ["- No test results were embedded."]

    return f"""# {TASK_NAME}

## 1. Task name

`{TASK_NAME}`

## 2. Objective

Run an independent G/H delta QA after S6P and verify warning reductions, flat-report parity, schema/count stability, and query/authority boundaries without introducing rule pollution.

## 3. Scope guardrails

- G/H only.
- QA only. No taxonomy, pattern, grammar, query, authority, or promotion changes.
- No I-W processing.
- No G/H query exposure.

## 4. Preflight

- S6P implementation status: `{report["preflight"]["s6p_implementation_status"]}`
- Current queryable levels: `{report["preflight"]["current_queryable_levels"]}`
- Current S6F must_fix_count: `{report["preflight"]["current_s6f_must_fix_count"]}`
- Read-only QA: `{report["preflight"]["read_only_qa"]}`
- Production code modified: `{report["preflight"]["production_code_modified"]}`

## 5. Files inspected

{chr(10).join(f"- `{path}`" for path in report["files_inspected"])}

## 6. Files created

{chr(10).join(f"- `{path}`" for path in report["files_created"])}

## 7. Files modified

{chr(10).join(f"- `{path}`" for path in report["files_modified"])}

## 8. Source status from S6P

- S6P status: `{report["source_status"]["s6p_status"]}`
- S6P decision: `{report["source_status"]["s6p_decision"]}`

## 9. Baseline metrics

{chr(10).join(baseline_lines)}

## 10. Current metrics

{chr(10).join(current_lines)}

## 11. Delta metrics

{chr(10).join(delta_lines)}

## 12. Delta classification

{chr(10).join(classification_lines)}

## 13. Flat report coverage check

- Status: `{report["flat_report_coverage"]["status"]}`
{chr(10).join(coverage_lines)}

## 14. Count parity

- `G`: `{report["count_parity"]["G"]}`
- `H`: `{report["count_parity"]["H"]}`

## 15. Schema validation

- `G`: `{report["schema_validation"]["G"]}`
- `H`: `{report["schema_validation"]["H"]}`

## 16. Rule pollution audit

- Status: `{report["rule_pollution_audit"]["status"]}`
- simple declarative: `{report["rule_pollution_audit"]["simple_declarative_samples"]["assessment"]}`
- heading exclusion: `{report["rule_pollution_audit"]["heading_exclusion_samples"]["assessment"]}`
- dialogue exclusion: `{report["rule_pollution_audit"]["dialogue_exclusion_samples"]["assessment"]}`
- deferred poetry/inversion/artifact: `{report["rule_pollution_audit"]["poetry_inversion_artifact_samples"]["assessment"]}`

## 17. Theme mapping audit

- Status: `{report["theme_mapping_audit"]["status"]}`
- science/nature/body/health: `{report["theme_mapping_audit"]["science_nature_samples"]["assessment"]}`
- history/civics: `{report["theme_mapping_audit"]["history_civics_samples"]["assessment"]}`
- animal nonfiction: `{report["theme_mapping_audit"]["animal_nonfiction_samples"]["assessment"]}`
- folktale/storyfable: `{report["theme_mapping_audit"]["folktale_storyfable_samples"]["assessment"]}`

## 18. Human review audit

- Status: `{report["human_review_audit"]["status"]}`
- direct_suppression_detected: `{report["human_review_audit"]["direct_suppression_detected"]}`
- indirect_reduction_confirmed: `{report["human_review_audit"]["indirect_reduction_confirmed"]}`
- assessment: `{report["human_review_audit"]["assessment"]}`

## 19. Duplicate warning check

- Status: `{report["duplicate_warning_check"]["status"]}`
- duplicate_count: `{report["duplicate_warning_check"]["duplicate_count"]}`

## 20. Traceability check

- Status: `{report["traceability_check"]["status"]}`
- missing_trace_count: `{report["traceability_check"]["missing_trace_count"]}`

## 21. Seed query layer boundary

- queryable_levels: `{report["seed_query_layer_boundary"]["queryable_levels"]}`
- g_exposed: `{report["seed_query_layer_boundary"]["g_exposed"]}`
- h_exposed: `{report["seed_query_layer_boundary"]["h_exposed"]}`
- status: `{report["seed_query_layer_boundary"]["status"]}`

## 22. Authority boundary

- candidate_only: `{report["authority_boundary"]["candidate_only"]}`
- promotion_allowed: `{report["authority_boundary"]["promotion_allowed"]}`

## 23. Validator results

- validate_raz_level_discovery: `{report["validator_results"]["validate_raz_level_discovery"]}`
- validate_raz_reusable_content_seed_query_layer: `{report["validator_results"]["validate_raz_reusable_content_seed_query_layer"]}`
- validate_raz_downstream_discovery_drift: `{report["validator_results"]["validate_raz_downstream_discovery_drift"]}`
- must_fix_count: `{report["validator_results"]["must_fix_count"]}`

## 24. Test results

{chr(10).join(test_lines)}

## 25. QA status

`{report["status"]}`

## 26. Risk level

`{report["risk_level"]}`

## 27. Decision for next stage

`{report["decision"]}`

## 28. Next recommended task

`{report["next_recommended_task"]}`
"""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build G/H rerun delta QA report from current derived artifacts.")
    parser.add_argument("--test-results-json", default="", help="Optional JSON file containing command->result strings.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    test_results = load_json(Path(args.test_results_json)) if args.test_results_json else {}
    report = build_report(test_results=test_results)
    write_json(OUTPUT_JSON_PATH, report)
    OUTPUT_MARKDOWN_PATH.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "decision": report["decision"], "output_json": stable_path(OUTPUT_JSON_PATH)}, ensure_ascii=False, indent=2))
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
