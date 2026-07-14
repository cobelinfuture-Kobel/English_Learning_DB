#!/usr/bin/env python3
"""Independently validate S12C indexes and coverage against private S12B records."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_raz_af_full_coverage_query_index import (  # noqa: E402
    CLAIM_BOUNDARIES,
    INDEX_SURFACES,
    PASS_STATUS,
    TASK_ID,
    _private_file_hashes,
    schema_validators,
)
from ulga.builders.build_raz_af_full_language_pedagogy_observations import (  # noqa: E402
    EXPECTED_BOOK_COUNT,
    EXPECTED_PAGE_UNIT_COUNT,
    SOURCE_LEVELS,
    STATUS_DISTRIBUTION_KEYS,
    canonical_json,
    load_authorities,
    load_source_rows,
    read_json,
    sha256_text,
)
from ulga.validators.validate_raz_af_full_language_pedagogy_observations import (  # noqa: E402
    _authority_reference_errors,
    load_private_records,
    validate_extraction,
)

SOURCE_REF_RE = re.compile(r"^RAZ_[A-F]_[A-Za-z0-9_-]+_P[0-9]+$")
MACHINE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SIGNAL_RE = re.compile(r"^[a-z][a-z0-9_]*:(?:SUPPORTED|NOT_SUPPORTED|UNKNOWN)$")
HASH_KEY_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
AUTHORITY_KEY_RES = {
    "evp_sense_candidate_refs": re.compile(r"^vocabulary:[A-Za-z0-9_:'-]+$"),
    "canonical_chunk_ids": re.compile(r"^EVP_CHUNK_[0-9]+$"),
    "chunk_equivalence_groups": re.compile(r"^CHUNK_EQ_[0-9]+$"),
    "safe_chunk_ids": re.compile(r"^SAFE_CHUNK_[0-9]+$"),
    "sentence_pattern_candidate_refs": re.compile(r"^pattern:PATTERN_NODE_[0-9]+$"),
    "grammar_candidate_refs": re.compile(r"^GRAMMAR_[A-Z0-9_]+$"),
}
FORBIDDEN_SAFE_KEYS = {
    "text", "source_text", "sentence", "sentences", "passage", "transcript", "observed_form",
    "surface_form", "normalized_form", "lemma_candidate", "observed_chunk", "answer", "answers",
    "source_payload", "record_payload", "learner_facing_text", "canonical_write", "promotion",
}


def _schema_errors(validator: Any, payload: Any, owner: str) -> list[str]:
    return [
        f"{owner}:{'.'.join(str(part) for part in error.absolute_path) or '$'}:{error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]


def _safe_scan(value: Any, pointer: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            next_pointer = f"{pointer}.{key}"
            if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                errors.append(f"safe_output_forbidden_key:{next_pointer}")
            errors.extend(_safe_scan(child, next_pointer))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_safe_scan(child, f"{pointer}[{index}]"))
    return errors


def _key_valid(surface: str, key_type: str, key: str) -> bool:
    if surface in {"vocabulary_normalized_forms", "vocabulary_lemma_candidates"}:
        return key_type == "sha256" and bool(HASH_KEY_RE.fullmatch(key))
    if surface in AUTHORITY_KEY_RES:
        return key_type == "authority_id" and bool(AUTHORITY_KEY_RES[surface].fullmatch(key))
    if surface == "evp_levels":
        return key_type == "cefr_level" and key in {"A1", "A2", "B1", "B2", "C1", "C2"}
    if surface == "raz_source_levels":
        return key_type == "raz_level" and key in SOURCE_LEVELS
    if surface == "book_ids":
        return key_type == "book_id" and key.isdigit()
    if surface == "source_unit_refs":
        return key_type == "source_unit_ref" and bool(SOURCE_REF_RE.fullmatch(key))
    if surface == "pedagogical_signals":
        return key_type == "signal_status" and bool(SIGNAL_RE.fullmatch(key))
    return key_type == "machine_id" and bool(MACHINE_ID_RE.fullmatch(key))


def _add_expected(
    expected: dict[str, dict[str, dict[str, Any]]], surface: str, key_type: str,
    key: str | None, ref: str, occurrences: int = 1,
) -> None:
    if key is None or key == "":
        return
    bucket = expected[surface].setdefault(str(key), {"key_type": key_type, "refs": set(), "occurrences": 0})
    bucket["refs"].add(ref)
    bucket["occurrences"] += int(occurrences)


def _expected_indexes(records: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    expected: dict[str, dict[str, dict[str, Any]]] = {surface: {} for surface in INDEX_SURFACES}
    for record in records:
        identity, observations = record["identity"], record["observations"]
        ref = identity["source_unit_ref"]
        _add_expected(expected, "raz_source_levels", "raz_level", identity["source_level"], ref)
        _add_expected(expected, "book_ids", "book_id", identity["source_book_id"], ref)
        _add_expected(expected, "source_unit_refs", "source_unit_ref", ref, ref)
        for item in observations["vocabulary_exposure"]["items"]:
            occurrences = item["occurrence_count"]
            _add_expected(expected, "vocabulary_normalized_forms", "sha256", f"sha256:{sha256_text(item['normalized_form'])}", ref, occurrences)
            if item["lemma_candidate"] is not None:
                _add_expected(expected, "vocabulary_lemma_candidates", "sha256", f"sha256:{sha256_text(item['lemma_candidate'])}", ref, occurrences)
            for candidate_ref in item["evp_candidate_refs"]:
                _add_expected(expected, "evp_sense_candidate_refs", "authority_id", candidate_ref, ref, occurrences)
            for level in item["evp_level_candidates"]:
                _add_expected(expected, "evp_levels", "cefr_level", level, ref, occurrences)
        for item in observations["chunk_exposure"]["items"]:
            occurrences = item["occurrence_count"]
            _add_expected(expected, "canonical_chunk_ids", "authority_id", item["canonical_chunk_id"], ref, occurrences)
            _add_expected(expected, "chunk_equivalence_groups", "authority_id", item["equivalence_group_id"], ref, occurrences)
            _add_expected(expected, "safe_chunk_ids", "authority_id", item["safe_chunk_id"], ref, occurrences)
        for item in observations["sentence_pattern_observations"]["items"]:
            for candidate_ref in item["pattern_authority_candidate_refs"]:
                _add_expected(expected, "sentence_pattern_candidate_refs", "authority_id", candidate_ref, ref, item["occurrence_count"])
            for grammar_ref in item["grammar_candidate_refs"]:
                _add_expected(expected, "grammar_candidate_refs", "authority_id", grammar_ref, ref, item["occurrence_count"])
        situation = observations["situation_function_observations"]
        for surface, field in (
            ("macro_domains", "macro_domain_candidates"), ("situation_families", "situation_family_candidates"),
            ("micro_situations", "micro_situation_candidates"), ("communicative_functions", "communicative_function_candidates"),
        ):
            for value in situation[field]:
                _add_expected(expected, surface, "machine_id", value, ref)
        _add_expected(expected, "discourse_shapes", "machine_id", observations["discourse_observation"]["discourse_shape"], ref)
        for name, signal in observations["pedagogical_signals"].items():
            _add_expected(expected, "pedagogical_signals", "signal_status", f"{name}:{signal['status']}", ref)
        for skill, templates in observations["four_skill_affordances"]["skill_activity_templates"].items():
            for template in templates:
                _add_expected(expected, f"{skill}_templates", "machine_id", template["template_id"], ref)
    return {
        surface: [{
            "key_type": data["key_type"], "key": key, "record_count": len(data["refs"]),
            "occurrence_count": data["occurrences"], "source_unit_refs": sorted(data["refs"]),
        } for key, data in sorted(expected[surface].items())]
        for surface in INDEX_SURFACES
    }


def _expected_statuses(records: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    counters = {name: Counter({key: 0 for key in keys}) for name, keys in STATUS_DISTRIBUTION_KEYS.items()}
    for record in records:
        observations = record["observations"]
        counters["vocabulary_match"].update(item["match_status"] for item in observations["vocabulary_exposure"]["items"])
        counters["chunk_match"].update(item["match_status"] for item in observations["chunk_exposure"]["items"])
        counters["pattern_mapping"].update(item["mapping_status"] for item in observations["sentence_pattern_observations"]["items"])
        counters["situation_classification"].update([observations["situation_function_observations"]["classification_status"]])
        counters["discourse_shape"].update([observations["discourse_observation"]["discourse_shape"]])
        counters["semantic_pass"].update([observations["quality_and_review"]["semantic_pass_status"]])
    return {name: {key: counters[name][key] for key in keys} for name, keys in STATUS_DISTRIBUTION_KEYS.items()}


def _expected_coverage(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    vocabulary = [item for record in records for item in record["observations"]["vocabulary_exposure"]["items"]]
    chunks = [item for record in records for item in record["observations"]["chunk_exposure"]["items"]]
    patterns = [item for record in records for item in record["observations"]["sentence_pattern_observations"]["items"]]
    skills = {}
    for skill in ("listening", "speaking", "reading", "writing"):
        groups = [record["observations"]["four_skill_affordances"]["skill_activity_templates"][skill] for record in records]
        skills[skill] = {"records_with_templates": sum(bool(group) for group in groups), "template_count": sum(len(group) for group in groups)}
    return {
        "vocabulary_item_count": len(vocabulary), "records_with_vocabulary_items": sum(bool(record["observations"]["vocabulary_exposure"]["items"]) for record in records),
        "vocabulary_items_with_evp_candidates": sum(bool(item["evp_candidate_refs"]) for item in vocabulary), "records_with_evp_candidates": sum(any(item["evp_candidate_refs"] for item in record["observations"]["vocabulary_exposure"]["items"]) for record in records),
        "chunk_item_count": len(chunks), "records_with_chunks": sum(bool(record["observations"]["chunk_exposure"]["items"]) for record in records), "chunk_items_with_authority_refs": sum(item["canonical_chunk_id"] is not None for item in chunks),
        "pattern_item_count": len(patterns), "pattern_items_with_pattern_refs": sum(bool(item["pattern_authority_candidate_refs"]) for item in patterns), "pattern_items_with_grammar_refs": sum(bool(item["grammar_candidate_refs"]) for item in patterns),
        "records_with_mapped_patterns": sum(any(item["pattern_authority_candidate_refs"] or item["grammar_candidate_refs"] for item in record["observations"]["sentence_pattern_observations"]["items"]) for record in records),
        "records_with_macro_domains": sum(bool(record["observations"]["situation_function_observations"]["macro_domain_candidates"]) for record in records),
        "records_with_situation_families": sum(bool(record["observations"]["situation_function_observations"]["situation_family_candidates"]) for record in records),
        "records_with_micro_situations": sum(bool(record["observations"]["situation_function_observations"]["micro_situation_candidates"]) for record in records),
        "records_with_communicative_functions": sum(bool(record["observations"]["situation_function_observations"]["communicative_function_candidates"]) for record in records),
        "records_with_known_discourse_shape": sum(record["observations"]["discourse_observation"]["discourse_shape"] != "unknown" for record in records),
        "supported_pedagogical_signal_count": sum(signal["status"] == "SUPPORTED" for record in records for signal in record["observations"]["pedagogical_signals"].values()),
        "records_with_supported_pedagogical_signals": sum(any(signal["status"] == "SUPPORTED" for signal in record["observations"]["pedagogical_signals"].values()) for record in records),
        "skill_templates": skills,
        "records_with_semantic_import": sum(record["observations"]["quality_and_review"]["semantic_pass_status"] == "APPLIED" for record in records),
        "records_requiring_review": sum(record["observations"]["quality_and_review"]["semantic_review_required"] or record["observations"]["situation_function_observations"]["review_status"] == "REVIEW_REQUIRED" or any(item["review_status"] == "REVIEW_REQUIRED" for item in record["observations"]["sentence_pattern_observations"]["items"]) for record in records),
    }


def validate_artifacts(
    records: list[Mapping[str, Any]], s12b_safe: Mapping[str, Any],
    query_index: Mapping[str, Any], coverage: Mapping[str, Any],
    *, enforce_expected_counts: bool = True, authorities: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    query_validator, coverage_validator = schema_validators()
    errors.extend(_schema_errors(query_validator, query_index, "query_schema"))
    errors.extend(_schema_errors(coverage_validator, coverage, "coverage_schema"))
    errors.extend(_safe_scan(query_index, "$.query_index"))
    errors.extend(_safe_scan(coverage, "$.coverage"))
    records = sorted(records, key=lambda record: record["identity"]["source_unit_ref"])
    expected_record_index = [{"source_unit_ref": record["identity"]["source_unit_ref"], "enrichment_payload_sha256": record["identity"]["enrichment_payload_sha256"]} for record in records]
    declared_record_index = query_index.get("record_index", [])
    expected_refs = {item["source_unit_ref"] for item in expected_record_index}
    declared_refs = [item.get("source_unit_ref") for item in declared_record_index if isinstance(item, Mapping)]
    missing = expected_refs - set(declared_refs)
    extra = set(declared_refs) - expected_refs
    duplicates = len(declared_refs) - len(set(declared_refs))
    if declared_record_index != expected_record_index:
        errors.append("record_index_mismatch")
    indexes = query_index.get("indexes", {})
    for surface in INDEX_SURFACES:
        seen_keys = set()
        for bucket in indexes.get(surface, []) if isinstance(indexes, Mapping) else []:
            key = bucket.get("key")
            if key in seen_keys:
                errors.append(f"duplicate_index_key:{surface}:{key}")
            seen_keys.add(key)
            if not isinstance(key, str) or not _key_valid(surface, bucket.get("key_type"), key):
                errors.append(f"unsafe_or_invalid_index_key:{surface}:{key}")
            refs = bucket.get("source_unit_refs", [])
            if bucket.get("record_count") != len(set(refs)):
                errors.append(f"bucket_record_count_drift:{surface}:{key}")
            for ref in refs:
                if ref not in expected_refs:
                    errors.append(f"index_ref_not_in_s12b:{surface}:{key}:{ref}")
    expected_indexes = _expected_indexes(records)
    if indexes != expected_indexes:
        errors.append("query_index_accounting_drift")
    expected_index_hash = sha256_text(canonical_json({"record_index": expected_record_index, "indexes": expected_indexes}))
    if query_index.get("index_sha256") != expected_index_hash or coverage.get("query_index_sha256") != expected_index_hash:
        errors.append("query_index_sha256_mismatch")
    source_records_sha256 = sha256_text(canonical_json(expected_record_index))
    if query_index.get("source_records_sha256") != source_records_sha256 or coverage.get("source_records_sha256") != source_records_sha256 or s12b_safe.get("records_sha256") != source_records_sha256:
        errors.append("s12b_source_records_sha256_mismatch")
    authority_errors = []
    authority_data = authorities or load_authorities()
    for record in records:
        authority_errors.extend(_authority_reference_errors(record["identity"]["source_unit_ref"], record["observations"], authority_data))
    errors.extend(authority_errors)
    if set(query_index.get("authority_snapshot_refs", [])) != set(authority_data["snapshots"]):
        errors.append("authority_snapshot_refs_mismatch")
    level_counts = Counter(record["identity"]["source_level"] for record in records)
    expected_levels = {level: level_counts[level] for level in SOURCE_LEVELS}
    expected_statuses = _expected_statuses(records)
    expected_coverage = _expected_coverage(records)
    coverage_drift = int(coverage.get("level_counts") != expected_levels) + int(coverage.get("status_distributions") != expected_statuses) + int(coverage.get("coverage") != expected_coverage)
    if coverage_drift:
        errors.append("coverage_accounting_drift")
    expected_summary = {
        "s12b_records_read": len(records), "s12c_records_indexed": len(expected_record_index),
        "represented_book_count": len({record["identity"]["source_book_id"] for record in records}),
        "missing_ref_count": len(missing), "extra_ref_count": len(extra), "duplicate_ref_count": duplicates,
        "invalid_authority_ref_count": len(authority_errors), "coverage_accounting_drift_count": coverage_drift,
        "source_text_leakage_count": 0, "source_payload_leakage_count": 0, "canonical_write_count": 0,
    }
    if coverage.get("summary") != expected_summary:
        errors.append("coverage_summary_accounting_drift")
    if query_index.get("claim_boundaries") != CLAIM_BOUNDARIES or coverage.get("claim_boundaries") != CLAIM_BOUNDARIES:
        errors.append("claim_boundary_mismatch")
    if query_index.get("record_count") != len(records) or query_index.get("index_surface_count") != len(INDEX_SURFACES):
        errors.append("query_index_summary_count_mismatch")
    if coverage.get("validation_status") != PASS_STATUS or coverage.get("errors"):
        errors.append("coverage_execution_not_pass")
    if enforce_expected_counts:
        if len(records) != EXPECTED_PAGE_UNIT_COUNT:
            errors.append(f"s12b_record_count:expected={EXPECTED_PAGE_UNIT_COUNT}:actual={len(records)}")
        book_count = len({record["identity"]["source_book_id"] for record in records})
        if book_count != EXPECTED_BOOK_COUNT:
            errors.append(f"book_count:expected={EXPECTED_BOOK_COUNT}:actual={book_count}")
    return {"task_id": TASK_ID, "validation_status": PASS_STATUS if not errors else "FAIL", "error_count": len(errors), "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT / "raz_output_jsons")
    parser.add_argument("--identity-inventory", type=Path, default=REPO_ROOT / ".local/raz_af/observational_companion_identity_inventory.json")
    parser.add_argument("--s12b-root", type=Path, default=REPO_ROOT / ".local/raz_af/observational_enrichment")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / ".local/raz_af/full_coverage_query_index")
    args = parser.parse_args(argv)
    try:
        identity_inventory = read_json(args.identity_inventory)
        source_rows, _hashes = load_source_rows(args.source_root)
        inventory = read_json(args.s12b_root / "inventory.json")
        s12b_safe = read_json(args.s12b_root / "validation.json")
        before_hashes = _private_file_hashes(args.s12b_root, inventory)
        records, load_errors = load_private_records(args.s12b_root, inventory)
        if load_errors:
            raise ValueError(";".join(load_errors[:20]))
        s12b_report = validate_extraction(identity_inventory, source_rows, records, inventory, s12b_safe)
        if s12b_report["validation_status"] == "FAIL":
            raise ValueError("s12b_validation_failed:" + ";".join(s12b_report["errors"][:20]))
        query_index = read_json(args.output_root / "query_index.json")
        coverage = read_json(args.output_root / "coverage.json")
        report = validate_artifacts(records, s12b_safe, query_index, coverage)
        if before_hashes != _private_file_hashes(args.s12b_root, inventory):
            report["errors"].insert(0, "s12b_private_record_mutation_during_validation")
            report["error_count"] = len(report["errors"])
            report["validation_status"] = "FAIL"
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report = {"task_id": TASK_ID, "validation_status": "FAIL", "error_count": 1, "errors": [str(exc)]}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
