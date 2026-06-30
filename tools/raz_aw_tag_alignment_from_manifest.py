#!/usr/bin/env python3
"""Manifest-driven RAZ A-W tag alignment.

This tool consumes the sanitized RAZ A-W manifest produced by S1C and aligns only
safe, manifest-level observations to the bootstrap tag registry. It does not read
raw RAZ JSON files and must not emit raw sentence/page text.

Default usage from repository root:
    python tools/raz_aw_tag_alignment_from_manifest.py
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_ALIGNMENT_CATEGORIES = {
    "matched_existing_tag",
    "matched_existing_tag_by_alias",
    "candidate_new_tag",
    "no_tag_needed_context_only",
}

RAW_CONTEXT_FIELDS = {
    "filename",
    "relative_path",
    "relative_path_hash",
    "size_bytes",
    "size_mb",
    "mime_type",
    "source_bucket",
    "source_type",
    "extraction_method",
    "extractor_version",
    "book_id",
    "book_title",
    "level",
    "level_from_json",
    "folder_title",
    "json_parse_status",
    "json_parse_error",
    "generated_content",
    "raw_audio_fields_preserved",
    "final_should_remove_audio_fields",
}

TOP_LEVEL_KEY_TO_CONTENT_TYPE = {
    "sentence_candidates": "sentence",
    "page_units": "page_unit",
    "reuse_unit_candidates": "reuse_unit",
}

COUNT_FIELD_TO_CONTENT_TYPE = {
    "sentence_candidate_count": "sentence",
    "page_unit_count": "page_unit",
    "reuse_candidate_count": "reuse_unit",
}

# These keys would be unsafe if emitted as object keys with raw payload values.
# It is valid for these strings to appear as metadata values, for example inside
# a manifest top_level_keys list. The validator below checks keys, not string
# values, to avoid false positives.
FORBIDDEN_RAW_PAYLOAD_KEYS = {
    "text",
    "sentences",
    "cleaned_candidate",
    "candidate_text",
    "legacy_story_sentences",
    "legacy_story_sentences_text",
    "page_text",
    "raw_text",
    "word_trace",
    "audio_trace",
    "audio_timeline",
    "page_units",
    "sentence_candidates",
    "reuse_unit_candidates",
}

SAFE_VALUE_COUNT_FIELDS = {
    "level",
    "level_from_json",
    "source_type",
    "extraction_method",
    "extractor_version",
    "json_parse_status",
    "authority_status",
    "source_bucket",
    "mime_type",
    "generated_content",
    "raw_audio_fields_preserved",
    "final_should_remove_audio_fields",
}


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} top-level JSON is not an object")
    return data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def registry_by_label(content_registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for record in content_registry.get("records", []):
        if isinstance(record, dict) and isinstance(record.get("canonical_label"), str):
            out[record["canonical_label"]] = record
    return out


def load_alias_map(alias_path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    if not alias_path.exists():
        return {}
    data = read_json(alias_path)
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for record in data.get("records", []):
        if not isinstance(record, dict):
            continue
        alias = record.get("alias")
        domain = record.get("domain")
        if isinstance(alias, str) and isinstance(domain, str):
            out[(domain, alias)] = record
    return out


def safe_ref(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in {
            "level": record.get("level"),
            "filename": record.get("filename"),
            "relative_path_hash": record.get("relative_path_hash"),
            "book_id": record.get("book_id"),
            "book_title": record.get("book_title"),
        }.items()
        if value is not None
    }


def add_alignment(
    rows: List[Dict[str, Any]],
    *,
    observed_value: Optional[Any] = None,
    observed_field: Optional[str] = None,
    domain: str,
    category: str,
    reason: str,
    example_record: Optional[Dict[str, Any]] = None,
    matched_registry_record: Optional[Dict[str, Any]] = None,
    alias_record: Optional[Dict[str, Any]] = None,
    count: int = 1,
) -> None:
    if category not in ALLOWED_ALIGNMENT_CATEGORIES:
        raise ValueError(f"Invalid alignment category: {category}")
    row: Dict[str, Any] = {
        "alignment_category": category,
        "domain": domain,
        "count": count,
        "reason": reason,
    }
    if observed_value is not None:
        row["observed_value"] = observed_value
    if observed_field is not None:
        row["observed_field"] = observed_field
    if example_record is not None:
        row["example_ref"] = safe_ref(example_record)
    if matched_registry_record is not None:
        row.update({
            "matched_tag_id": matched_registry_record.get("tag_id"),
            "matched_label": matched_registry_record.get("canonical_label"),
            "authority_status": matched_registry_record.get("authority_status", "candidate_only"),
            "review_status": matched_registry_record.get("review_status", "pending"),
        })
    if alias_record is not None:
        row.update({
            "alias_matched": alias_record.get("alias"),
            "canonical_candidate": alias_record.get("canonical_candidate"),
            "auto_merge_allowed": alias_record.get("auto_merge_allowed", False),
            "review_status": alias_record.get("review_status", "pending"),
            "authority_status": "candidate_only",
        })
    rows.append({key: value for key, value in row.items() if value is not None})


def summarize_observations(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    field_counts: Counter[str] = Counter()
    value_counts: Dict[str, Counter[str]] = defaultdict(Counter)
    level_counts: Counter[str] = Counter()
    parse_counts: Counter[str] = Counter()

    for record in records:
        level = str(record.get("level", "UNKNOWN"))
        level_counts[level] += 1
        parse_counts[str(record.get("json_parse_status", "UNKNOWN"))] += 1
        for key, value in record.items():
            field_counts[key] += 1
            if key not in SAFE_VALUE_COUNT_FIELDS:
                continue
            if isinstance(value, (str, int, float, bool)):
                value_counts[key][str(value)] += 1
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (str, int, float, bool)):
                        value_counts[key][str(item)] += 1

    return {
        "record_count": len(records),
        "field_counts": dict(sorted(field_counts.items())),
        "level_counts": dict(sorted(level_counts.items())),
        "json_parse_status_counts": dict(sorted(parse_counts.items())),
        "safe_value_counts": {key: dict(counter.most_common()) for key, counter in sorted(value_counts.items())},
    }


def build_alignment(
    records: List[Dict[str, Any]],
    content_registry_by_label: Dict[str, Dict[str, Any]],
    alias_map: Dict[Tuple[str, str], Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    alignment_rows: List[Dict[str, Any]] = []
    candidate_new: Dict[Tuple[str, str], Dict[str, Any]] = {}
    content_type_seen: Counter[str] = Counter()
    content_type_examples: Dict[str, Dict[str, Any]] = {}
    context_field_counts: Counter[str] = Counter()
    context_field_examples: Dict[str, Dict[str, Any]] = {}
    skipped_parse_failures: List[Dict[str, Any]] = []

    for record in records:
        if record.get("json_parse_status") != "PASS":
            skipped_parse_failures.append(safe_ref(record) | {"json_parse_status": record.get("json_parse_status")})
            continue

        for field in RAW_CONTEXT_FIELDS:
            if field in record:
                context_field_counts[field] += 1
                context_field_examples.setdefault(field, record)

        for count_field, content_type in COUNT_FIELD_TO_CONTENT_TYPE.items():
            value = record.get(count_field)
            if isinstance(value, int) and value > 0:
                content_type_seen[content_type] += 1
                content_type_examples.setdefault(content_type, record)

        top_keys = record.get("top_level_keys")
        if isinstance(top_keys, list):
            for top_key, content_type in TOP_LEVEL_KEY_TO_CONTENT_TYPE.items():
                if top_key in top_keys:
                    content_type_seen[content_type] += 1
                    content_type_examples.setdefault(content_type, record)

    for content_type, count in sorted(content_type_seen.items()):
        registry_record = content_registry_by_label.get(content_type)
        alias_record = alias_map.get(("content_unit_type", content_type))
        if registry_record:
            add_alignment(
                alignment_rows,
                observed_value=content_type,
                domain="content_unit_type",
                category="matched_existing_tag",
                reason="manifest_count_or_top_level_key_infers_existing_content_unit_type",
                example_record=content_type_examples.get(content_type),
                matched_registry_record=registry_record,
                count=count,
            )
        elif alias_record:
            add_alignment(
                alignment_rows,
                observed_value=content_type,
                domain="content_unit_type",
                category="matched_existing_tag_by_alias",
                reason="manifest_inferred_content_type_matches_alias_candidate",
                example_record=content_type_examples.get(content_type),
                alias_record=alias_record,
                count=count,
            )
        else:
            key = ("content_unit_type", content_type)
            candidate_new[key] = {
                "observed_value": content_type,
                "domain": "content_unit_type",
                "alignment_category": "candidate_new_tag",
                "authority_status": "candidate_only",
                "review_status": "pending",
                "count": count,
                "example_ref": safe_ref(content_type_examples[content_type]),
            }

    for field, count in sorted(context_field_counts.items()):
        add_alignment(
            alignment_rows,
            observed_field=field,
            domain="raw_manifest_context",
            category="no_tag_needed_context_only",
            reason="manifest_metadata_or_source_trace_not_formal_tag",
            example_record=context_field_examples.get(field),
            count=count,
        )

    diagnostics = {
        "records_seen": len(records),
        "records_skipped_parse_failure_count": len(skipped_parse_failures),
        "records_skipped_parse_failure_examples": skipped_parse_failures[:20],
        "content_type_inference_counts": dict(sorted(content_type_seen.items())),
        "context_field_counts": dict(sorted(context_field_counts.items())),
    }
    return alignment_rows, list(candidate_new.values()), diagnostics


def build_authority_gap_report(records: List[Dict[str, Any]], diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    parse_fail_count = diagnostics.get("records_skipped_parse_failure_count", 0)
    return {
        "task_id": "RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation",
        "report_type": "authority_linkage_gap_report",
        "status": "PASS_WITH_WARNINGS" if parse_fail_count else "PASS",
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "authority_promotion": False,
        "manifest_record_count": len(records),
        "parse_fail_records_skipped": parse_fail_count,
        "gap_categories": {
            "missing_egp_grammar_ref": "not_evaluated_manifest_only",
            "missing_evp_vocabulary_ref": "not_evaluated_manifest_only",
            "missing_pattern_authority_ref": "not_evaluated_manifest_only",
            "missing_theme_authority_ref": "not_evaluated_manifest_only",
            "missing_chunk_authority_ref": "not_evaluated_manifest_only",
            "not_applicable": "raw_manifest_context_fields",
        },
        "reason": "S2 uses sanitized manifest metadata only. It does not inspect raw grammar, vocabulary, theme, pattern, or chunk tags.",
    }


def validate_no_forbidden_raw_payload_keys(payload: Any, path: str = "$") -> None:
    """Reject raw-payload-bearing keys while allowing safe metadata values.

    The manifest may safely contain string values such as "reuse_unit_candidates"
    inside top_level_keys. That is schema metadata, not raw text. The unsafe case is
    emitting an object key named reuse_unit_candidates, page_units, sentence_candidates,
    etc., because those keys conventionally contain raw corpus payloads.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_RAW_PAYLOAD_KEYS:
                raise ValueError(f"Forbidden raw-payload-bearing key emitted at {path}.{key}: {key}")
            validate_no_forbidden_raw_payload_keys(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            validate_no_forbidden_raw_payload_keys(item, f"{path}[{index}]")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run manifest-driven RAZ A-W tag alignment.")
    parser.add_argument("--manifest", default="reports/raz/raw_aw_drive_file_manifest.json")
    parser.add_argument("--content-unit-registry", default="tag_registry/content_unit_type_registry.bootstrap_draft.json")
    parser.add_argument("--alias-registry", default="tag_registry/tag_alias_candidates.bootstrap_draft.json")
    parser.add_argument("--reports-dir", default="reports/raz")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    content_registry_path = Path(args.content_unit_registry)
    alias_registry_path = Path(args.alias_registry)
    reports_dir = Path(args.reports_dir)

    manifest = read_json(manifest_path)
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ValueError("Manifest missing records array")
    safe_records = [record for record in records if isinstance(record, dict)]

    content_registry = read_json(content_registry_path)
    content_by_label = registry_by_label(content_registry)
    alias_map = load_alias_map(alias_registry_path)

    observed_inventory = summarize_observations(safe_records)
    alignment_rows, candidate_new, diagnostics = build_alignment(safe_records, content_by_label, alias_map)
    category_counts = Counter(row["alignment_category"] for row in alignment_rows)
    domain_counts = Counter(row["domain"] for row in alignment_rows)

    status = "PASS_WITH_WARNINGS" if diagnostics["records_skipped_parse_failure_count"] else "PASS"
    tag_alignment_report = {
        "task_id": "RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation",
        "report_type": "tag_alignment_report",
        "alignment_status": status,
        "registry_status_used": "bootstrap_draft",
        "source_manifest": str(manifest_path),
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "authority_promotion": False,
        "tag_registry_promotion": False,
        "counts_by_alignment_category": dict(sorted(category_counts.items())),
        "counts_by_domain": dict(sorted(domain_counts.items())),
        "diagnostics": diagnostics,
        "records": alignment_rows,
    }

    candidate_new_report = {
        "task_id": "RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation",
        "report_type": "candidate_new_tags",
        "status": "PASS",
        "sanitized": True,
        "contains_raw_text": False,
        "authority_status_default": "candidate_only",
        "review_status_default": "pending",
        "records": candidate_new,
    }

    alias_report = {
        "task_id": "RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation",
        "report_type": "tag_alias_mapping_candidates",
        "status": "PASS",
        "sanitized": True,
        "contains_raw_text": False,
        "records": [row for row in alignment_rows if row["alignment_category"] == "matched_existing_tag_by_alias"],
    }

    authority_gap_report = build_authority_gap_report(safe_records, diagnostics)

    safety_report = {
        "task_id": "RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation",
        "report_type": "tag_alignment_manifest_driven_safety_report",
        "status": status,
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "authority_promotion": False,
        "tag_registry_promotion": False,
        "manifest_records_seen": len(safe_records),
        "parse_fail_records_skipped": diagnostics["records_skipped_parse_failure_count"],
        "allowed_alignment_categories": sorted(ALLOWED_ALIGNMENT_CATEGORIES),
        "blockers": [],
        "warnings": ["one_or_more_manifest_records_skipped_due_to_parse_failure"] if diagnostics["records_skipped_parse_failure_count"] else [],
        "validator_note": "Forbidden raw payload keys are checked as object keys only; schema key names may appear as metadata values.",
    }

    outputs = {
        "observed_raw_tag_inventory.json": {
            "task_id": "RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation",
            "report_type": "observed_raw_tag_inventory",
            "status": status,
            "sanitized": True,
            "contains_raw_text": False,
            "raw_mutation": False,
            "inventory_source": "sanitized_manifest_only",
            **observed_inventory,
        },
        "tag_alignment_report.json": tag_alignment_report,
        "candidate_new_tags.json": candidate_new_report,
        "tag_alias_mapping_candidates.json": alias_report,
        "authority_linkage_gap_report.json": authority_gap_report,
        "tag_alignment_manifest_driven_safety_report.json": safety_report,
    }

    for filename, payload in outputs.items():
        validate_no_forbidden_raw_payload_keys(payload)
        write_json(reports_dir / filename, payload)

    print(json.dumps({
        "status": status,
        "manifest_records_seen": len(safe_records),
        "parse_fail_records_skipped": diagnostics["records_skipped_parse_failure_count"],
        "counts_by_alignment_category": dict(sorted(category_counts.items())),
        "candidate_new_tag_count": len(candidate_new),
        "reports_written": sorted(outputs),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
