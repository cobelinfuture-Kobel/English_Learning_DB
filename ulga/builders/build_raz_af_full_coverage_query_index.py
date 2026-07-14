#!/usr/bin/env python3
"""Build the deterministic, text-free S12C query index from validated S12B records."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_raz_af_full_language_pedagogy_observations import (  # noqa: E402
    SOURCE_LEVELS,
    STATUS_DISTRIBUTION_KEYS,
    canonical_json,
    load_source_rows,
    read_json,
    sha256_file,
    sha256_text,
    write_json_atomic,
)
from ulga.validators.validate_raz_af_full_language_pedagogy_observations import (  # noqa: E402
    load_private_records,
    validate_extraction,
)

TASK_ID = "RAZ-AF-S12C_FullCoverageQueryIndexAndExtractionValidation"
SOURCE_TASK_ID = "RAZ-AF-S12B_FullLanguagePedagogyObservationalExtraction"
QUERY_SCHEMA_VERSION = "raz.af.full_coverage_query_index.v1"
COVERAGE_SCHEMA_VERSION = "raz.af.full_coverage_safe_report.v1"
PASS_STATUS = "PASS_LOCAL_RAZ_AF_FULL_COVERAGE_QUERY_INDEX_AND_EXTRACTION_VALIDATION"
INDEX_SURFACES = (
    "vocabulary_normalized_forms", "vocabulary_lemma_candidates", "evp_sense_candidate_refs", "evp_levels",
    "canonical_chunk_ids", "chunk_equivalence_groups", "safe_chunk_ids", "sentence_pattern_candidate_refs",
    "grammar_candidate_refs", "macro_domains", "situation_families", "micro_situations",
    "communicative_functions", "discourse_shapes", "pedagogical_signals", "listening_templates",
    "speaking_templates", "reading_templates", "writing_templates", "raz_source_levels", "book_ids",
    "source_unit_refs",
)
CLAIM_BOUNDARIES = {
    "text_free": True, "source_payload_included": False, "learner_facing_material_created": False,
    "canonical_authority_write_performed": False, "promotion_performed": False,
    "observational_candidate_only": True,
}


class QueryIndexError(ValueError):
    """Fail-closed S12C build or validation error."""


def schema_validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    schema_dir = REPO_ROOT / "ulga/schemas"
    query = read_json(schema_dir / "raz_af_full_coverage_query_index.schema.json")
    coverage = read_json(schema_dir / "raz_af_full_coverage_safe_report.schema.json")
    registry = Registry().with_resource(query["$id"], Resource.from_contents(query))
    return Draft202012Validator(query), Draft202012Validator(coverage, registry=registry)


def _schema_errors(validator: Draft202012Validator, payload: Any, owner: str) -> list[str]:
    return [
        f"{owner}:{'.'.join(str(part) for part in error.absolute_path) or '$'}:{error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]


def _hash_key(value: str) -> str:
    return f"sha256:{sha256_text(value)}"


def _add(
    accumulators: Mapping[str, dict[str, dict[str, Any]]],
    surface: str,
    key_type: str,
    key: str | None,
    ref: str,
    occurrence_count: int = 1,
) -> None:
    if key is None or key == "":
        return
    bucket = accumulators[surface].setdefault(
        str(key), {"key_type": key_type, "source_unit_refs": set(), "occurrence_count": 0}
    )
    if bucket["key_type"] != key_type:
        raise QueryIndexError(f"index_key_type_conflict:{surface}:{key}")
    bucket["source_unit_refs"].add(ref)
    bucket["occurrence_count"] += int(occurrence_count)


def _finalize_indexes(accumulators: Mapping[str, dict[str, dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    indexes: dict[str, list[dict[str, Any]]] = {}
    for surface in INDEX_SURFACES:
        buckets = []
        for key in sorted(accumulators[surface]):
            item = accumulators[surface][key]
            refs = sorted(item["source_unit_refs"])
            buckets.append({
                "key_type": item["key_type"], "key": key, "record_count": len(refs),
                "occurrence_count": item["occurrence_count"], "source_unit_refs": refs,
            })
        indexes[surface] = buckets
    return indexes


def derive_status_distributions(records: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
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


def derive_coverage(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    vocabulary_items = [item for record in records for item in record["observations"]["vocabulary_exposure"]["items"]]
    chunk_items = [item for record in records for item in record["observations"]["chunk_exposure"]["items"]]
    pattern_items = [item for record in records for item in record["observations"]["sentence_pattern_observations"]["items"]]
    skill_coverage = {}
    for skill in ("listening", "speaking", "reading", "writing"):
        per_record = [record["observations"]["four_skill_affordances"]["skill_activity_templates"][skill] for record in records]
        skill_coverage[skill] = {
            "records_with_templates": sum(bool(items) for items in per_record),
            "template_count": sum(len(items) for items in per_record),
        }
    return {
        "vocabulary_item_count": len(vocabulary_items),
        "records_with_vocabulary_items": sum(bool(record["observations"]["vocabulary_exposure"]["items"]) for record in records),
        "vocabulary_items_with_evp_candidates": sum(bool(item["evp_candidate_refs"]) for item in vocabulary_items),
        "records_with_evp_candidates": sum(any(item["evp_candidate_refs"] for item in record["observations"]["vocabulary_exposure"]["items"]) for record in records),
        "chunk_item_count": len(chunk_items),
        "records_with_chunks": sum(bool(record["observations"]["chunk_exposure"]["items"]) for record in records),
        "chunk_items_with_authority_refs": sum(item["canonical_chunk_id"] is not None for item in chunk_items),
        "pattern_item_count": len(pattern_items),
        "pattern_items_with_pattern_refs": sum(bool(item["pattern_authority_candidate_refs"]) for item in pattern_items),
        "pattern_items_with_grammar_refs": sum(bool(item["grammar_candidate_refs"]) for item in pattern_items),
        "records_with_mapped_patterns": sum(any(item["pattern_authority_candidate_refs"] or item["grammar_candidate_refs"] for item in record["observations"]["sentence_pattern_observations"]["items"]) for record in records),
        "records_with_macro_domains": sum(bool(record["observations"]["situation_function_observations"]["macro_domain_candidates"]) for record in records),
        "records_with_situation_families": sum(bool(record["observations"]["situation_function_observations"]["situation_family_candidates"]) for record in records),
        "records_with_micro_situations": sum(bool(record["observations"]["situation_function_observations"]["micro_situation_candidates"]) for record in records),
        "records_with_communicative_functions": sum(bool(record["observations"]["situation_function_observations"]["communicative_function_candidates"]) for record in records),
        "records_with_known_discourse_shape": sum(record["observations"]["discourse_observation"]["discourse_shape"] != "unknown" for record in records),
        "supported_pedagogical_signal_count": sum(signal["status"] == "SUPPORTED" for record in records for signal in record["observations"]["pedagogical_signals"].values()),
        "records_with_supported_pedagogical_signals": sum(any(signal["status"] == "SUPPORTED" for signal in record["observations"]["pedagogical_signals"].values()) for record in records),
        "skill_templates": skill_coverage,
        "records_with_semantic_import": sum(record["observations"]["quality_and_review"]["semantic_pass_status"] == "APPLIED" for record in records),
        "records_requiring_review": sum(
            record["observations"]["quality_and_review"]["semantic_review_required"]
            or record["observations"]["situation_function_observations"]["review_status"] == "REVIEW_REQUIRED"
            or any(item["review_status"] == "REVIEW_REQUIRED" for item in record["observations"]["sentence_pattern_observations"]["items"])
            for record in records
        ),
    }


def build_artifacts(
    records: list[Mapping[str, Any]],
    source_records_sha256: str,
    authority_snapshot_refs: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    records = sorted(records, key=lambda record: record["identity"]["source_unit_ref"])
    accumulators: dict[str, dict[str, dict[str, Any]]] = {surface: {} for surface in INDEX_SURFACES}
    record_index = []
    for record in records:
        identity, observations = record["identity"], record["observations"]
        ref = identity["source_unit_ref"]
        record_index.append({"source_unit_ref": ref, "enrichment_payload_sha256": identity["enrichment_payload_sha256"]})
        _add(accumulators, "raz_source_levels", "raz_level", identity["source_level"], ref)
        _add(accumulators, "book_ids", "book_id", identity["source_book_id"], ref)
        _add(accumulators, "source_unit_refs", "source_unit_ref", ref, ref)
        for item in observations["vocabulary_exposure"]["items"]:
            occurrences = item["occurrence_count"]
            _add(accumulators, "vocabulary_normalized_forms", "sha256", _hash_key(item["normalized_form"]), ref, occurrences)
            if item["lemma_candidate"] is not None:
                _add(accumulators, "vocabulary_lemma_candidates", "sha256", _hash_key(item["lemma_candidate"]), ref, occurrences)
            for candidate_ref in item["evp_candidate_refs"]:
                _add(accumulators, "evp_sense_candidate_refs", "authority_id", candidate_ref, ref, occurrences)
            for level in item["evp_level_candidates"]:
                _add(accumulators, "evp_levels", "cefr_level", level, ref, occurrences)
        for item in observations["chunk_exposure"]["items"]:
            occurrences = item["occurrence_count"]
            _add(accumulators, "canonical_chunk_ids", "authority_id", item["canonical_chunk_id"], ref, occurrences)
            _add(accumulators, "chunk_equivalence_groups", "authority_id", item["equivalence_group_id"], ref, occurrences)
            _add(accumulators, "safe_chunk_ids", "authority_id", item["safe_chunk_id"], ref, occurrences)
        for item in observations["sentence_pattern_observations"]["items"]:
            occurrences = item["occurrence_count"]
            for candidate_ref in item["pattern_authority_candidate_refs"]:
                _add(accumulators, "sentence_pattern_candidate_refs", "authority_id", candidate_ref, ref, occurrences)
            for grammar_ref in item["grammar_candidate_refs"]:
                _add(accumulators, "grammar_candidate_refs", "authority_id", grammar_ref, ref, occurrences)
        situation = observations["situation_function_observations"]
        for surface, field in (
            ("macro_domains", "macro_domain_candidates"), ("situation_families", "situation_family_candidates"),
            ("micro_situations", "micro_situation_candidates"), ("communicative_functions", "communicative_function_candidates"),
        ):
            for value in situation[field]:
                _add(accumulators, surface, "machine_id", value, ref)
        _add(accumulators, "discourse_shapes", "machine_id", observations["discourse_observation"]["discourse_shape"], ref)
        for name, signal in observations["pedagogical_signals"].items():
            _add(accumulators, "pedagogical_signals", "signal_status", f"{name}:{signal['status']}", ref)
        skills = observations["four_skill_affordances"]["skill_activity_templates"]
        for skill in ("listening", "speaking", "reading", "writing"):
            for template in skills[skill]:
                _add(accumulators, f"{skill}_templates", "machine_id", template["template_id"], ref)
    indexes = _finalize_indexes(accumulators)
    index_sha256 = sha256_text(canonical_json({"record_index": record_index, "indexes": indexes}))
    query_index = {
        "task_id": TASK_ID, "schema_version": QUERY_SCHEMA_VERSION, "source_task_id": SOURCE_TASK_ID,
        "source_records_sha256": source_records_sha256, "authority_snapshot_refs": sorted(authority_snapshot_refs),
        "record_count": len(records), "index_surface_count": len(INDEX_SURFACES), "record_index": record_index,
        "indexes": indexes, "index_sha256": index_sha256, "claim_boundaries": dict(CLAIM_BOUNDARIES),
    }
    level_counts = Counter(record["identity"]["source_level"] for record in records)
    coverage = {
        "task_id": TASK_ID, "schema_version": COVERAGE_SCHEMA_VERSION, "source_task_id": SOURCE_TASK_ID,
        "source_records_sha256": source_records_sha256, "query_index_sha256": index_sha256,
        "summary": {
            "s12b_records_read": len(records), "s12c_records_indexed": len(record_index),
            "represented_book_count": len({record["identity"]["source_book_id"] for record in records}),
            "missing_ref_count": 0, "extra_ref_count": 0, "duplicate_ref_count": 0,
            "invalid_authority_ref_count": 0, "coverage_accounting_drift_count": 0,
            "source_text_leakage_count": 0, "source_payload_leakage_count": 0, "canonical_write_count": 0,
        },
        "level_counts": {level: level_counts[level] for level in SOURCE_LEVELS},
        "status_distributions": derive_status_distributions(records), "coverage": derive_coverage(records),
        "claim_boundaries": dict(CLAIM_BOUNDARIES), "validation_status": PASS_STATUS, "errors": [],
    }
    return query_index, coverage


def _private_file_hashes(output_root: Path, inventory: Mapping[str, Any]) -> dict[str, str]:
    result = {}
    for entry in inventory.get("records", []):
        path = (output_root / entry["path"]).resolve()
        result[str(path)] = sha256_file(path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT / "raz_output_jsons")
    parser.add_argument("--identity-inventory", type=Path, default=REPO_ROOT / ".local/raz_af/observational_companion_identity_inventory.json")
    parser.add_argument("--s12b-root", type=Path, default=REPO_ROOT / ".local/raz_af/observational_enrichment")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / ".local/raz_af/full_coverage_query_index")
    args = parser.parse_args(argv)
    try:
        identity_inventory = read_json(args.identity_inventory)
        source_rows, _source_hashes = load_source_rows(args.source_root)
        inventory = read_json(args.s12b_root / "inventory.json")
        safe = read_json(args.s12b_root / "validation.json")
        before_hashes = _private_file_hashes(args.s12b_root, inventory)
        records, load_errors = load_private_records(args.s12b_root, inventory)
        if load_errors:
            raise QueryIndexError("s12b_private_record_load_failed:" + ";".join(load_errors[:20]))
        s12b_validation = validate_extraction(identity_inventory, source_rows, records, inventory, safe)
        if s12b_validation["validation_status"] == "FAIL":
            raise QueryIndexError("s12b_validation_failed:" + ";".join(s12b_validation["errors"][:20]))
        query_index, coverage = build_artifacts(records, safe["records_sha256"], safe["authority_snapshot_refs"])
        query_validator, coverage_validator = schema_validators()
        errors = _schema_errors(query_validator, query_index, "query_index") + _schema_errors(coverage_validator, coverage, "coverage")
        if errors:
            raise QueryIndexError("schema_validation_failed:" + ";".join(errors[:20]))
        if before_hashes != _private_file_hashes(args.s12b_root, inventory):
            raise QueryIndexError("s12b_private_record_mutation_during_build")
        write_json_atomic(args.output_root / "query_index.json", query_index)
        write_json_atomic(args.output_root / "coverage.json", coverage)
        if before_hashes != _private_file_hashes(args.s12b_root, inventory):
            raise QueryIndexError("s12b_private_record_mutation_during_output_write")
        print(json.dumps(coverage["summary"], sort_keys=True))
        print(f"validation_status={coverage['validation_status']}")
        return 0
    except (QueryIndexError, ValueError, OSError, KeyError, TypeError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
