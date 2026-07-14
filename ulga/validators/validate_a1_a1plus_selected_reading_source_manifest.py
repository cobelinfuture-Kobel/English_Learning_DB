#!/usr/bin/env python3
"""Validate the compact A1/A1+ selected Reading source manifest shards."""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = REPO_ROOT / "ulga/graph/reading_sources/a1_a1plus_selected/index.json"
TASK_ID = "E4S-A1V1-M04B1_ReadingSourceManifestSelectionAndCompaction"
INDEX_SCHEMA = "e4s.a1v1.selected_reading_source_manifest.index.v1"
SHARD_SCHEMA = "e4s.a1v1.selected_reading_source_manifest.shard.v1"
LEVELS = ("A", "B", "C", "D", "E", "F")
DOMAINS = {
    "personal_social",
    "daily_routine",
    "school",
    "home",
    "shopping",
    "food",
    "hobbies_abilities",
    "travel_transport_weather",
    "health_medical",
}
QUESTION_TYPES = {
    "literal_who",
    "literal_what",
    "literal_where",
    "true_false",
    "sentence_ordering",
    "cloze_vocabulary",
}
REQUIRED_GENERAL_TYPES = {"literal_what", "true_false", "cloze_vocabulary"}
EXPECTED_FIELDS = [
    "selection_id",
    "source_unit_ref",
    "drive_file_id",
    "source_level",
    "book_id",
    "page_number",
    "sentence_count",
    "word_count",
    "character_count",
    "e4s_situation_domain",
    "source_theme",
    "theme_confidence",
    "candidate_question_types",
    "content_sha256",
    "record_sha256",
]
EXPECTED_DRIVE_IDS = {
    "A": "1Mdp8xf_D3MSgrbjWalvCqYqbR5Lz470l",
    "B": "1sMp2p9MAaMP9RLzvd4iGmr20tdmo3Rts",
    "C": "1fUlgIf5xJqoEo_wSzrn-fjw-HIW26-xN",
    "D": "17EKKTDhpIWmELAsfK1-TRdc47L-KNp_g",
    "E": "17JxkXI-lqnT7uv1ElGHhn_7eE4iotN9g",
    "F": "1HRn9amcG9CNOfF5cTIgocytFLmRKLJEb",
}
FALSE_CLAIMS = {
    "raw_source_text_included",
    "full_passage_text_included",
    "sentence_text_included",
    "source_payload_copied",
    "reading_v1_content_complete",
    "learner_evidence_created",
    "mastery_claimed",
    "retention_confirmed",
    "persistent_learner_state_write",
    "production_runtime_event",
    "a2_a2plus_in_scope",
}
FORBIDDEN_KEYS = {
    "clean_text",
    "reading_text",
    "page_text",
    "passage_text",
    "normalized_text",
    "raw_text",
    "text",
    "content",
    "sentence",
    "sentences",
    "sentence_candidates",
    "source_sentences",
    "lines",
    "display_text",
    "transcript_text",
    "answer_text",
    "evidence_quote",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_from_repo(index_path: Path = INDEX_PATH) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    index = _load(index_path)
    shards: dict[str, dict[str, Any]] = {}
    for row in index.get("shards", []):
        level = row.get("level")
        rel = row.get("path")
        if isinstance(level, str) and isinstance(rel, str):
            shards[level] = _load(REPO_ROOT / rel)
    return index, shards


def _scan_forbidden(value: Any, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                errors.append(f"forbidden_text_key:{path}.{key}")
            _scan_forbidden(child, errors, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _scan_forbidden(child, errors, f"{path}[{idx}]")


def validate_selected_manifest(
    index: Mapping[str, Any], shards: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if index.get("task_id") != TASK_ID:
        errors.append("index_task_id_mismatch")
    if index.get("schema_version") != INDEX_SCHEMA:
        errors.append("index_schema_version_mismatch")
    source_ref = index.get("source_manifest_ref", {})
    if source_ref.get("drive_file_id") != "1reKRq6odwbMr8b98W5wXb5RC54uC5NjS":
        errors.append("source_manifest_drive_ref_mismatch")
    if source_ref.get("manifest_record_count") != 43818:
        errors.append("source_manifest_record_count_mismatch")
    if source_ref.get("equivalent_validation_status") != "PASS_SAFE_READING_SOURCE_MANIFEST":
        errors.append("source_manifest_not_validated")
    if source_ref.get("equivalent_validation_error_count") != 0:
        errors.append("source_manifest_validation_errors_nonzero")

    claim_boundaries = index.get("claim_boundaries", {})
    if claim_boundaries.get("metadata_only_manifest") is not True:
        errors.append("index_metadata_only_boundary_missing")
    for key in FALSE_CLAIMS:
        if claim_boundaries.get(key) is not False:
            errors.append(f"index_false_claim_boundary_invalid:{key}")

    shard_rows = index.get("shards")
    if not isinstance(shard_rows, list) or {row.get("level") for row in shard_rows} != set(LEVELS):
        errors.append("index_shard_levels_invalid")
    if set(shards) != set(LEVELS):
        errors.append("loaded_shard_levels_invalid")

    selection_ids: list[str] = []
    source_refs: list[str] = []
    book_keys: list[tuple[str, str]] = []
    level_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    sentence_counts: Counter[str] = Counter()
    question_counts: Counter[str] = Counter()

    for level in LEVELS:
        shard = shards.get(level, {})
        if shard.get("task_id") != TASK_ID:
            errors.append(f"{level}:task_id_mismatch")
        if shard.get("schema_version") != SHARD_SCHEMA:
            errors.append(f"{level}:schema_version_mismatch")
        if shard.get("level") != level:
            errors.append(f"{level}:declared_level_mismatch")
        if shard.get("record_fields") != EXPECTED_FIELDS:
            errors.append(f"{level}:record_fields_mismatch")
        policy = shard.get("record_policy", {})
        if policy.get("metadata_and_hashes_only") is not True:
            errors.append(f"{level}:metadata_only_policy_missing")
        if policy.get("authority_status") != "candidate_only":
            errors.append(f"{level}:authority_status_invalid")
        if policy.get("promotion_status") != "not_promoted":
            errors.append(f"{level}:promotion_status_invalid")
        if policy.get("content_access") != "LOCAL_SOURCE_REQUIRED_NOT_EMBEDDED":
            errors.append(f"{level}:content_access_invalid")
        for key in (
            "raw_source_text_included",
            "full_passage_text_included",
            "sentence_text_included",
            "source_payload_copied",
        ):
            if policy.get(key) is not False:
                errors.append(f"{level}:unsafe_policy:{key}")
        records = shard.get("records")
        if not isinstance(records, list) or len(records) != 9:
            errors.append(f"{level}:record_count_not_9")
            records = records if isinstance(records, list) else []
        domains_seen: set[str] = set()
        for idx, row in enumerate(records):
            prefix = f"{level}:{idx}"
            if not isinstance(row, list) or len(row) != len(EXPECTED_FIELDS):
                errors.append(f"{prefix}:record_shape_invalid")
                continue
            record = dict(zip(EXPECTED_FIELDS, row))
            if record["source_level"] != level:
                errors.append(f"{prefix}:source_level_mismatch")
            if record["drive_file_id"] != EXPECTED_DRIVE_IDS[level]:
                errors.append(f"{prefix}:drive_file_id_mismatch")
            if not str(record["source_unit_ref"]).startswith(f"RAZ_{level}_"):
                errors.append(f"{prefix}:source_unit_ref_level_mismatch")
            if record["e4s_situation_domain"] not in DOMAINS:
                errors.append(f"{prefix}:unknown_situation_domain")
            domains_seen.add(record["e4s_situation_domain"])
            if not isinstance(record["sentence_count"], int) or not 1 <= record["sentence_count"] <= 5:
                errors.append(f"{prefix}:sentence_count_out_of_range")
            if not isinstance(record["word_count"], int) or not 2 <= record["word_count"] <= 60:
                errors.append(f"{prefix}:word_count_out_of_range")
            if not isinstance(record["character_count"], int) or record["character_count"] <= 0:
                errors.append(f"{prefix}:character_count_invalid")
            if not isinstance(record["theme_confidence"], (int, float)) or not 0 <= record["theme_confidence"] <= 1:
                errors.append(f"{prefix}:theme_confidence_invalid")
            types = record["candidate_question_types"]
            if not isinstance(types, list) or not REQUIRED_GENERAL_TYPES <= set(types):
                errors.append(f"{prefix}:required_question_types_missing")
                types = types if isinstance(types, list) else []
            if not set(types) <= QUESTION_TYPES:
                errors.append(f"{prefix}:unknown_question_type")
            if "sentence_ordering" in types and record["sentence_count"] < 2:
                errors.append(f"{prefix}:sentence_ordering_without_multi_sentence_source")
            if not HEX64.fullmatch(str(record["content_sha256"])):
                errors.append(f"{prefix}:content_hash_invalid")
            if not HEX64.fullmatch(str(record["record_sha256"])):
                errors.append(f"{prefix}:record_hash_invalid")
            selection_ids.append(str(record["selection_id"]))
            source_refs.append(str(record["source_unit_ref"]))
            book_keys.append((level, str(record["book_id"])))
            level_counts[level] += 1
            domain_counts[str(record["e4s_situation_domain"])] += 1
            sentence_counts[str(record["sentence_count"])] += 1
            question_counts.update(types)
        if domains_seen != DOMAINS:
            errors.append(f"{level}:domain_set_incomplete")
        _scan_forbidden(shard, errors, f"$.shards.{level}")

    if len(selection_ids) != len(set(selection_ids)):
        errors.append("duplicate_selection_id")
    if len(source_refs) != len(set(source_refs)):
        errors.append("duplicate_source_unit_ref")
    if len(book_keys) != len(set(book_keys)):
        errors.append("duplicate_book_within_level")

    recomputed = {
        "selected_record_count": len(selection_ids),
        "source_level_count": len(level_counts),
        "situation_domain_count": len(domain_counts),
        "unique_book_count": len(set(book_keys)),
        "levels": dict(sorted(level_counts.items())),
        "situation_domains": dict(sorted(domain_counts.items())),
        "sentence_counts": dict(sorted(sentence_counts.items())),
        "candidate_question_types": dict(sorted(question_counts.items())),
        "local_content_binding_required_count": len(selection_ids),
    }
    if index.get("summary") != recomputed:
        errors.append("index_summary_drift")
    if recomputed["selected_record_count"] != 54:
        errors.append("selected_record_count_not_54")
    if recomputed["unique_book_count"] != 54:
        errors.append("unique_book_count_not_54")
    if recomputed["levels"] != {level: 9 for level in LEVELS}:
        errors.append("level_distribution_not_9_each")
    if recomputed["situation_domains"] != {domain: 6 for domain in sorted(DOMAINS)}:
        errors.append("domain_distribution_not_6_each")

    _scan_forbidden(index, errors, "$.index")
    return {
        "task_id": TASK_ID,
        "validation_status": "PASS_SELECTED_READING_SOURCE_MANIFEST" if not errors else "FAIL",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": recomputed,
        "m04b1_selection_complete": not errors,
        "m04b2_local_content_binding_complete": False,
        "reading_v1_complete": False,
        "next_resume_task": "E4S-A1V1-M04B2_LocalReadingContentBindingAndPracticeBankMaterialization",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    index, shards = load_from_repo(args.index)
    report = validate_selected_manifest(index, shards)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == "PASS_SELECTED_READING_SOURCE_MANIFEST" else 1


if __name__ == "__main__":
    raise SystemExit(main())
