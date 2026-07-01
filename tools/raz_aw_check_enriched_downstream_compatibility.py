#!/usr/bin/env python3
"""RAZ A-W enriched downstream compatibility QA.

Reads local enriched artifacts and emits sanitized aggregate reports only.
No learner-facing approval or authority promotion is performed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
EXPECTED = {"book_count": 1959, "sentence_count": 201993, "unit_count": 41964}
FILES = {
    "books": "raz_{level}_enriched_books.json",
    "sentences": "raz_{level}_enriched_sentences.json",
    "units": "raz_{level}_enriched_units.json",
}
BOOK_FIELDS = ["book_uid", "level", "book_id", "title", "sentence_count", "page_unit_count", "reuse_unit_count", "estimated_text_complexity_bucket", "candidate_theme_tags", "candidate_content_unit_tags", "candidate_pedagogical_tags", "authority_linkage_status", "enrichment_status", "review_status", "validation_status"]
SENTENCE_FIELDS = ["sentence_uid", "book_uid", "level", "text", "normalized_token_count", "candidate_vocab_refs", "candidate_grammar_refs", "candidate_pattern_refs", "sentence_length_bucket", "punctuation_profile", "dialogue_candidate_flag", "reading_sentence_candidate_flag", "authority_linkage_status", "enrichment_status", "review_status", "validation_status"]
UNIT_FIELDS = ["unit_uid", "unit_type", "book_uid", "level", "sentence_uids", "unit_sentence_count", "unit_token_count", "candidate_use_cases", "candidate_reuse_tags", "reading_usefulness_score_candidate", "dialogue_usefulness_score_candidate", "exercise_usefulness_score_candidate", "authority_linkage_status", "enrichment_status", "review_status", "validation_status"]
BAD_STATUS = {"approved", "promoted", "final_authority", "learner_facing_approved"}


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("top_level_not_object")
    return data


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def records(path: Path) -> List[Dict[str, Any]]:
    data = read_json(path)
    value = data.get("records")
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def add_sample(samples: List[Dict[str, str]], issue: str, uid: Any, level: str) -> None:
    if len(samples) < 40:
        samples.append({"issue": issue, "uid": str(uid), "level": level})


def type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if value is None:
        return "null"
    return type(value).__name__


def scan_status(value: Any, counter: Counter) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, str) and v in BAD_STATUS:
                counter[f"{k}:{v}"] += 1
            scan_status(v, counter)
    elif isinstance(value, list):
        for item in value:
            scan_status(item, counter)


def check_status_boundary(kind: str, rec: Dict[str, Any], uid: str, level: str, issues: Counter, samples: List[Dict[str, str]]) -> None:
    if rec.get("enrichment_status") != "candidate_enriched":
        issues[f"{kind}_enrichment_status_invalid"] += 1
        add_sample(samples, f"{kind}_enrichment_status_invalid", uid, level)
    if rec.get("authority_linkage_status") not in {"candidate_only", "not_evaluated"}:
        issues[f"{kind}_authority_linkage_status_invalid"] += 1
        add_sample(samples, f"{kind}_authority_linkage_status_invalid", uid, level)


def require(kind: str, rec: Dict[str, Any], uid_field: str, fields: List[str], level: str, issues: Counter, samples: List[Dict[str, str]], presence: Dict[str, Counter], types: Dict[str, Counter]) -> None:
    uid = rec.get(uid_field, "MISSING_UID")
    for field in fields:
        if field not in rec:
            issues[f"missing_field:{kind}:{field}"] += 1
            add_sample(samples, f"missing_field:{kind}:{field}", uid, level)
        else:
            presence[kind][field] += 1
            types[kind][f"{field}:{type_name(rec.get(field))}"] += 1


def merge_counter(dst: Counter, src: Counter, prefix: str) -> None:
    for k, v in src.items():
        dst[f"{prefix}:{k}"] += v


def run(derived_root: Path, reports_dir: Path, build_summary: Optional[Path], validator_report: Optional[Path]) -> Dict[str, Any]:
    issues: Counter = Counter()
    bad_status: Counter = Counter()
    joins: Counter = Counter()
    facets: Counter = Counter()
    candidate_refs: Counter = Counter()
    totals: Counter = Counter()
    level_counts: Dict[str, Dict[str, int]] = {}
    field_presence: Dict[str, Counter] = {"books": Counter(), "sentences": Counter(), "units": Counter()}
    field_types: Dict[str, Counter] = {"books": Counter(), "sentences": Counter(), "units": Counter()}
    missing_files: List[str] = []
    parse_failures: List[Dict[str, str]] = []
    samples: List[Dict[str, str]] = []

    for level in LEVELS:
        root = derived_root / f"Level_{level}" / "enriched"
        expected_paths = {kind: root / pattern.format(level=level) for kind, pattern in FILES.items()}
        for kind, path in expected_paths.items():
            if not path.exists():
                missing_files.append(str(path))
                issues[f"missing_file:{kind}"] += 1
        if any(not path.exists() for path in expected_paths.values()):
            continue
        try:
            books = records(expected_paths["books"])
            sentences = records(expected_paths["sentences"])
            units = records(expected_paths["units"])
        except Exception as exc:
            parse_failures.append({"level": level, "error_type": type(exc).__name__})
            issues["parse_or_load_failure"] += 1
            continue

        book_ids: Set[str] = set()
        sentence_ids: Set[str] = set()
        sentences_by_book: Counter = Counter()
        page_units_by_book: Counter = Counter()
        reuse_units_by_book: Counter = Counter()

        for book in books:
            uid = str(book.get("book_uid", "MISSING_BOOK_UID"))
            book_ids.add(uid)
            require("books", book, "book_uid", BOOK_FIELDS, level, issues, samples, field_presence, field_types)
            scan_status(book, bad_status)
            check_status_boundary("book", book, uid, level, issues, samples)
            facets[f"book.level:{book.get('level')}"] += 1
            facets[f"book.complexity:{book.get('estimated_text_complexity_bucket')}"] += 1
            for tag in book.get("candidate_content_unit_tags", []) if isinstance(book.get("candidate_content_unit_tags"), list) else []:
                facets[f"book.content_tag:{tag}"] += 1
            for tag in book.get("candidate_pedagogical_tags", []) if isinstance(book.get("candidate_pedagogical_tags"), list) else []:
                facets[f"book.pedagogical_tag:{tag}"] += 1

        for sent in sentences:
            uid = str(sent.get("sentence_uid", "MISSING_SENTENCE_UID"))
            book_uid = str(sent.get("book_uid", "MISSING_BOOK_UID"))
            sentence_ids.add(uid)
            sentences_by_book[book_uid] += 1
            require("sentences", sent, "sentence_uid", SENTENCE_FIELDS, level, issues, samples, field_presence, field_types)
            scan_status(sent, bad_status)
            check_status_boundary("sentence", sent, uid, level, issues, samples)
            if book_uid in book_ids:
                joins["sentence_to_book_ok"] += 1
            else:
                issues["sentence_to_book_missing"] += 1
                add_sample(samples, "sentence_to_book_missing", uid, level)
            facets[f"sentence.level:{sent.get('level')}"] += 1
            facets[f"sentence.length_bucket:{sent.get('sentence_length_bucket')}"] += 1
            profile = sent.get("punctuation_profile") if isinstance(sent.get("punctuation_profile"), dict) else {}
            facets[f"sentence.terminal:{profile.get('terminal_punctuation')}"] += 1
            facets[f"sentence.dialogue:{sent.get('dialogue_candidate_flag')}"] += 1
            facets[f"sentence.reading:{sent.get('reading_sentence_candidate_flag')}"] += 1
            for ref_field in ("candidate_vocab_refs", "candidate_grammar_refs", "candidate_pattern_refs"):
                refs = sent.get(ref_field)
                if not isinstance(refs, list):
                    issues[f"{ref_field}_not_list"] += 1
                    add_sample(samples, f"{ref_field}_not_list", uid, level)
                else:
                    candidate_refs[f"{ref_field}_total_refs"] += len(refs)
                    if refs:
                        candidate_refs[f"{ref_field}_non_empty_records"] += 1

        for unit in units:
            uid = str(unit.get("unit_uid", "MISSING_UNIT_UID"))
            book_uid = str(unit.get("book_uid", "MISSING_BOOK_UID"))
            require("units", unit, "unit_uid", UNIT_FIELDS, level, issues, samples, field_presence, field_types)
            scan_status(unit, bad_status)
            check_status_boundary("unit", unit, uid, level, issues, samples)
            if book_uid in book_ids:
                joins["unit_to_book_ok"] += 1
            else:
                issues["unit_to_book_missing"] += 1
                add_sample(samples, "unit_to_book_missing", uid, level)
            if unit.get("unit_type") == "page_unit":
                page_units_by_book[book_uid] += 1
            elif unit.get("unit_type") == "reuse_unit":
                reuse_units_by_book[book_uid] += 1
            refs = unit.get("sentence_uids") if isinstance(unit.get("sentence_uids"), list) else []
            if unit.get("unit_sentence_count") != len(refs):
                issues["unit_sentence_count_mismatch"] += 1
                add_sample(samples, "unit_sentence_count_mismatch", uid, level)
            for ref in refs:
                if ref in sentence_ids:
                    joins["unit_to_sentence_ok"] += 1
                else:
                    issues["unit_to_sentence_missing"] += 1
                    add_sample(samples, "unit_to_sentence_missing", uid, level)
            facets[f"unit.level:{unit.get('level')}"] += 1
            facets[f"unit.type:{unit.get('unit_type')}"] += 1
            for use_case in unit.get("candidate_use_cases", []) if isinstance(unit.get("candidate_use_cases"), list) else []:
                facets[f"unit.use_case:{use_case}"] += 1
            for tag in unit.get("candidate_reuse_tags", []) if isinstance(unit.get("candidate_reuse_tags"), list) else []:
                facets[f"unit.reuse_tag:{tag}"] += 1

        for book in books:
            uid = str(book.get("book_uid", "MISSING_BOOK_UID"))
            if isinstance(book.get("sentence_count"), int) and book.get("sentence_count") != sentences_by_book[uid]:
                issues["book_sentence_count_join_mismatch"] += 1
                add_sample(samples, "book_sentence_count_join_mismatch", uid, level)
            if isinstance(book.get("page_unit_count"), int) and book.get("page_unit_count") != page_units_by_book[uid]:
                issues["book_page_unit_count_join_mismatch"] += 1
                add_sample(samples, "book_page_unit_count_join_mismatch", uid, level)
            if isinstance(book.get("reuse_unit_count"), int) and book.get("reuse_unit_count") != reuse_units_by_book[uid]:
                issues["book_reuse_unit_count_join_mismatch"] += 1
                add_sample(samples, "book_reuse_unit_count_join_mismatch", uid, level)

        counts = {"book_count": len(books), "sentence_count": len(sentences), "unit_count": len(units)}
        level_counts[level] = counts
        totals.update(counts)

    blockers: List[str] = []
    warnings: List[str] = []
    if missing_files:
        blockers.append("missing_enriched_files")
    if parse_failures:
        blockers.append("enriched_parse_or_load_failures")
    for key, expected in EXPECTED.items():
        if totals[key] != expected:
            blockers.append(f"{key}_mismatch")
    if issues:
        blockers.append("downstream_compatibility_violations")
    if bad_status:
        blockers.append("forbidden_status_values_present")

    upstream = {}
    for label, path in (("enriched_build_summary", build_summary), ("enriched_validator_report", validator_report)):
        if path and path.exists():
            try:
                upstream[label] = str(read_json(path).get("status", "UNKNOWN"))
            except Exception:
                upstream[label] = "PARSE_FAILURE"
                blockers.append(f"{label}_parse_failure")
        else:
            upstream[label] = "MISSING"
            warnings.append(f"{label}_missing")

    status = "PASS" if not blockers else "BLOCKED"
    readiness = {
        "consumer_can_read_books_sentences_units": status == "PASS",
        "book_sentence_unit_join_ready": not any(k.endswith("missing") or "join_mismatch" in k for k in issues),
        "query_facets_ready": status == "PASS",
        "authority_linkage_placeholders_ready": True,
        "authority_linkage_approved": False,
        "generation_approved": False,
    }
    report = {
        "task_id": "RAZ-AW-S3E0_EnrichedDownstreamCompatibilityQA",
        "report_type": "raz_aw_enriched_downstream_compatibility_qa_report",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "derived_root": str(derived_root),
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "text_bearing_enriched_artifacts_committed_to_github": False,
        "authority_promotion": False,
        "tag_authority_promotion": False,
        "approved_authority_linkage": False,
        "generation_approved": False,
        "runtime_api_integration": False,
        "actual_counts": dict(totals),
        "expected_counts": EXPECTED,
        "level_counts": level_counts,
        "upstream_report_statuses": upstream,
        "join_coverage_counts": dict(sorted(joins.items())),
        "candidate_ref_counts": dict(sorted(candidate_refs.items())),
        "query_facet_readiness": readiness,
        "issue_counts": dict(sorted(issues.items())),
        "forbidden_status_counts": dict(sorted(bad_status.items())),
        "missing_file_count": len(missing_files),
        "parse_failure_count": len(parse_failures),
        "sample_issues": samples,
        "warnings": warnings,
        "blockers": sorted(set(blockers)),
    }
    shape = {
        "task_id": "RAZ-AW-S3E0_EnrichedDownstreamCompatibilityQA",
        "report_type": "raz_aw_enriched_downstream_shape_manifest",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "record_counts": dict(totals),
        "required_consumer_fields": {"books": BOOK_FIELDS, "sentences": SENTENCE_FIELDS, "units": UNIT_FIELDS},
        "field_presence_counts": {k: dict(sorted(v.items())) for k, v in field_presence.items()},
        "field_type_counts": {k: dict(sorted(v.items())) for k, v in field_types.items()},
        "issue_counts": dict(sorted(issues.items())),
        "blockers": sorted(set(blockers)),
    }
    facet = {
        "task_id": "RAZ-AW-S3E0_EnrichedDownstreamCompatibilityQA",
        "report_type": "raz_aw_enriched_query_facet_readiness_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "query_facet_readiness": readiness,
        "facet_value_distribution_counts": dict(sorted(facets.items())),
        "candidate_ref_counts": dict(sorted(candidate_refs.items())),
        "issue_counts": dict(sorted(issues.items())),
        "blockers": sorted(set(blockers)),
    }
    safety = {
        "task_id": "RAZ-AW-S3E0_EnrichedDownstreamCompatibilityQA",
        "report_type": "raz_aw_enriched_downstream_compatibility_safety_report",
        "status": "PASS" if not bad_status else "BLOCKED",
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "text_bearing_enriched_artifacts_committed_to_github": False,
        "forbidden_status_counts": dict(sorted(bad_status.items())),
        "authority_promotion": False,
        "tag_authority_promotion": False,
        "approved_authority_linkage": False,
        "generation_approved": False,
    }
    for payload in (report, shape, facet, safety):
        if "text" in payload:
            raise ValueError("unsafe_report_key")
    write_json(reports_dir / "raz_aw_enriched_downstream_compatibility_qa_report.json", report)
    write_json(reports_dir / "raz_aw_enriched_downstream_shape_manifest.json", shape)
    write_json(reports_dir / "raz_aw_enriched_query_facet_readiness_summary.json", facet)
    write_json(reports_dir / "raz_aw_enriched_downstream_compatibility_safety_report.json", safety)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="RAZ enriched downstream compatibility QA.")
    parser.add_argument("--derived-root", default="raz_output_jsons/derived")
    parser.add_argument("--reports-dir", default="reports/raz")
    parser.add_argument("--enriched-build-summary", default="reports/raz/raz_aw_enriched_build_summary.json")
    parser.add_argument("--enriched-validator-report", default="reports/raz/raz_aw_enriched_validator_qa_report.json")
    args = parser.parse_args()
    derived_root = Path(args.derived_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    if not derived_root.exists() or not derived_root.is_dir():
        payload = {"task_id": "RAZ-AW-S3E0_EnrichedDownstreamCompatibilityQA", "status": "BLOCKED", "sanitized": True, "contains_text_values": False, "blockers": ["derived_root_missing_or_not_directory"]}
        write_json(reports_dir / "raz_aw_enriched_downstream_compatibility_qa_report.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    report = run(derived_root, reports_dir, Path(args.enriched_build_summary).resolve(), Path(args.enriched_validator_report).resolve())
    print(json.dumps({"status": report["status"], "actual_counts": report["actual_counts"], "query_facet_readiness": report["query_facet_readiness"], "issue_counts": report["issue_counts"], "warnings": report["warnings"], "blockers": report["blockers"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
