#!/usr/bin/env python3
"""Fail-closed validation for private S12B records and the text-free safe report."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_raz_af_full_language_pedagogy_observations import (  # noqa: E402
    EXPECTED_BOOK_COUNT,
    EXPECTED_PAGE_UNIT_COUNT,
    PASS_STATUS,
    SOURCE_LEVELS,
    STATUS_DISTRIBUTION_KEYS,
    TASK_ID,
    authority_reference_maps,
    canonical_json,
    format_schema_errors,
    load_authorities,
    load_source_rows,
    read_json,
    safe_field_scan,
    schema_validators,
    sha256_text,
    source_hashes,
)


def _authority_reference_errors(ref: str, observations: Mapping[str, Any], authorities: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    maps = authority_reference_maps(authorities)
    vocabulary = maps["vocabulary"]
    for item in observations.get("vocabulary_exposure", {}).get("items", []):
        candidate_refs = item.get("evp_candidate_refs", [])
        status = item.get("match_status")
        for candidate_ref in candidate_refs:
            if candidate_ref not in vocabulary:
                errors.append(f"invalid_evp_candidate_ref:{ref}:{candidate_ref}")
        expected_levels = sorted({
            str(vocabulary[candidate_ref].get("cefr_level"))
            for candidate_ref in candidate_refs if candidate_ref in vocabulary
            if vocabulary[candidate_ref].get("cefr_level") in {"A1", "A2", "B1", "B2", "C1", "C2"}
        })
        if item.get("evp_level_candidates") != expected_levels:
            errors.append(f"inconsistent_evp_levels:{ref}:{item.get('normalized_form')}")
        authority_match_statuses = {
            "EXACT_FORM_POS_SENSE_CANDIDATE", "EXACT_FORM_MULTIPLE_SENSES", "LEMMA_POS_SENSE_AMBIGUOUS",
            "LEMMA_ONLY_MATCH", "MORPHOLOGICAL_MATCH",
        }
        if status in authority_match_statuses and not candidate_refs:
            errors.append(f"missing_required_evp_ref:{ref}:{status}")
        if status not in authority_match_statuses and candidate_refs:
            errors.append(f"unexpected_evp_ref_for_status:{ref}:{status}")

    chunks = maps["chunks"]
    groups = maps["groups"]
    safe_chunks = maps["safe_chunks"]
    usage = authorities.get("usage", {})
    matched_chunk_statuses = {"EXACT_CANONICAL_CHUNK_MATCH", "EQUIVALENT_CHUNK_MATCH", "GENERATOR_SAFE_CHUNK_MATCH"}
    for item in observations.get("chunk_exposure", {}).get("items", []):
        status = item.get("match_status")
        canonical_id = item.get("canonical_chunk_id")
        group_id = item.get("equivalence_group_id")
        safe_id = item.get("safe_chunk_id")
        usage_class = item.get("usage_class")
        if status in matched_chunk_statuses and canonical_id not in chunks:
            errors.append(f"invalid_canonical_chunk_id:{ref}:{canonical_id}")
        if status not in matched_chunk_statuses and any(value is not None for value in (canonical_id, group_id, safe_id, usage_class, item.get("evp_level_candidate"))):
            errors.append(f"unexpected_chunk_authority_ref_for_status:{ref}:{status}")
        group = groups.get(group_id) if group_id is not None else None
        if group_id is not None and group is None:
            errors.append(f"invalid_chunk_equivalence_group_id:{ref}:{group_id}")
        if group is not None and group.get("canonical_id") != canonical_id:
            errors.append(f"incorrect_chunk_equivalence_mapping:{ref}:{group_id}:{canonical_id}")
        if status == "EQUIVALENT_CHUNK_MATCH" and group is None:
            errors.append(f"missing_chunk_equivalence_group:{ref}:{canonical_id}")
        safe_row = safe_chunks.get(safe_id) if safe_id is not None else None
        if safe_id is not None and safe_row is None:
            errors.append(f"invalid_generator_safe_chunk_id:{ref}:{safe_id}")
        if safe_row is not None and safe_row.get("canonical_chunk_id") != canonical_id:
            errors.append(f"incorrect_generator_safe_chunk_mapping:{ref}:{safe_id}:{canonical_id}")
        if status == "GENERATOR_SAFE_CHUNK_MATCH" and safe_row is None:
            errors.append(f"missing_generator_safe_chunk_mapping:{ref}:{canonical_id}")
        expected_usage = (usage.get(canonical_id) or {}).get("usage_class") if canonical_id is not None else None
        if usage_class != expected_usage:
            errors.append(f"incorrect_chunk_usage_mapping:{ref}:{canonical_id}:{usage_class}")
        valid_levels = set()
        candidate_chunk_ids = group.get("equivalent_ids", []) if group is not None else [canonical_id]
        for candidate_chunk_id in candidate_chunk_ids:
            row = chunks.get(candidate_chunk_id, {})
            if row.get("level"):
                valid_levels.add(row["level"])
        if item.get("evp_level_candidate") is not None and item.get("evp_level_candidate") not in valid_levels:
            errors.append(f"incorrect_chunk_level_mapping:{ref}:{canonical_id}:{item.get('evp_level_candidate')}")

    for item in observations.get("sentence_pattern_observations", {}).get("items", []):
        for grammar_ref in item.get("grammar_candidate_refs", []):
            if grammar_ref not in maps["grammar"]:
                errors.append(f"invalid_grammar_candidate_ref:{ref}:{grammar_ref}")
        for pattern_ref in item.get("pattern_authority_candidate_refs", []):
            if pattern_ref not in maps["patterns"]:
                errors.append(f"invalid_pattern_candidate_ref:{ref}:{pattern_ref}")
    return errors


def _identity_index(identity_inventory: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    errors: list[str] = []
    rows = identity_inventory.get("records")
    if not isinstance(rows, list):
        return {}, ["s12a_identity_records_missing"]
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("source_unit_ref"), str):
            errors.append("invalid_s12a_identity")
            continue
        ref = row["source_unit_ref"]
        if ref in result:
            errors.append(f"duplicate_s12a_identity:{ref}")
        result[ref] = row
    return result, errors


def load_private_records(output_root: Path, inventory: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    entries = inventory.get("records")
    if not isinstance(entries, list):
        return records, ["private_inventory_records_missing"]
    listed_paths: set[Path] = set()
    for entry in entries:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
            errors.append("private_inventory_entry_invalid")
            continue
        path = (output_root / entry["path"]).resolve()
        try:
            path.relative_to(output_root.resolve())
        except ValueError:
            errors.append(f"private_record_path_escape:{entry['path']}")
            continue
        listed_paths.add(path)
        try:
            payload = read_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not isinstance(payload, dict):
            errors.append(f"private_record_not_object:{entry['path']}")
            continue
        records.append(payload)
    records_root = output_root / "records"
    actual_paths = {path.resolve() for path in records_root.rglob("*.json")} if records_root.is_dir() else set()
    for path in sorted(actual_paths - listed_paths):
        errors.append(f"extra_unlisted_enrichment_record:{path.relative_to(output_root.resolve()).as_posix()}")
    for path in sorted(listed_paths - actual_paths):
        errors.append(f"listed_enrichment_record_missing:{path.relative_to(output_root.resolve()).as_posix()}")
    return records, errors


def validate_extraction(
    identity_inventory: Mapping[str, Any],
    source_rows: Mapping[str, Mapping[str, Any]],
    records: list[Mapping[str, Any]],
    inventory: Mapping[str, Any],
    safe: Mapping[str, Any],
    *,
    enforce_expected_counts: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    record_validator, safe_validator, _semantic_validator = schema_validators()
    errors.extend(format_schema_errors(safe_validator, safe, "safe_schema"))
    identities, identity_errors = _identity_index(identity_inventory)
    errors.extend(identity_errors)
    by_ref: dict[str, Mapping[str, Any]] = {}
    duplicates = 0
    payload_mismatches = 0
    schema_error_count = 0
    content_hash_drifts = 0
    record_hash_drifts = 0
    authorities = load_authorities()
    for record in records:
        record_schema_errors = format_schema_errors(record_validator, record, "record_schema")
        schema_error_count += len(record_schema_errors)
        errors.extend(record_schema_errors)
        identity = record.get("identity", {}) if isinstance(record, Mapping) else {}
        ref = identity.get("source_unit_ref") if isinstance(identity, Mapping) else None
        if not isinstance(ref, str):
            errors.append("enrichment_source_ref_missing")
            continue
        if ref in by_ref:
            duplicates += 1
            errors.append(f"duplicate_enrichment_record:{ref}")
        by_ref[ref] = record
        observations = record.get("observations")
        if identity.get("enrichment_payload_sha256") != sha256_text(canonical_json(observations)):
            payload_mismatches += 1
            errors.append(f"enrichment_payload_hash_mismatch:{ref}")
        s12a = identities.get(ref)
        if s12a is None:
            errors.append(f"missing_s12a_identity:{ref}")
        else:
            for field in ("observational_record_id", "source_unit_ref", "source_level", "source_book_id", "source_page_number", "source_record_sha256", "source_content_sha256", "source_role", "authority_import_allowed", "learner_facing_original_text_allowed", "promotion_status"):
                if identity.get(field) != s12a.get(field):
                    errors.append(f"s12a_identity_mismatch:{ref}:{field}")
        source = source_rows.get(ref)
        if source is None:
            errors.append(f"source_record_missing:{ref}")
        else:
            content_hash, record_hash = source_hashes(source)
            if identity.get("source_content_sha256") != content_hash:
                content_hash_drifts += 1
                errors.append(f"source_content_hash_drift:{ref}")
            if identity.get("source_record_sha256") != record_hash:
                record_hash_drifts += 1
                errors.append(f"source_record_hash_drift:{ref}")
        if identity.get("authority_import_allowed") is not False or identity.get("promotion_status") != "not_promoted":
            errors.append(f"canonical_promotion_claim:{ref}")
        if identity.get("learner_facing_original_text_allowed") is not False:
            errors.append(f"learner_facing_original_text_claim:{ref}")
        if isinstance(observations, Mapping):
            quality = observations.get("quality_and_review", {})
            if quality.get("authority_write_performed") is not False:
                errors.append(f"canonical_authority_write_claim:{ref}")
            errors.extend(_authority_reference_errors(ref, observations, authorities))
            for key in ("vocabulary_exposure", "chunk_exposure", "sentence_pattern_observations", "situation_function_observations", "discourse_observation", "pedagogical_signals", "four_skill_affordances"):
                if key not in observations:
                    errors.append(f"missing_observation_surface:{ref}:{key}")
    expected_refs, actual_refs = set(identities), set(by_ref)
    missing, extra = expected_refs - actual_refs, actual_refs - expected_refs
    errors.extend(f"missing_enrichment_record:{ref}" for ref in sorted(missing))
    errors.extend(f"extra_enrichment_record:{ref}" for ref in sorted(extra))
    source_only = set(source_rows) - expected_refs
    if source_only:
        errors.append(f"extra_source_record_count:{len(source_only)}")
    if enforce_expected_counts:
        if len(identities) != EXPECTED_PAGE_UNIT_COUNT:
            errors.append(f"s12a_identity_count:expected={EXPECTED_PAGE_UNIT_COUNT}:actual={len(identities)}")
        if len(by_ref) != EXPECTED_PAGE_UNIT_COUNT:
            errors.append(f"s12b_record_count:expected={EXPECTED_PAGE_UNIT_COUNT}:actual={len(by_ref)}")
        book_count = len({record.get("identity", {}).get("source_book_id") for record in records})
        if book_count != EXPECTED_BOOK_COUNT:
            errors.append(f"represented_book_count:expected={EXPECTED_BOOK_COUNT}:actual={book_count}")
    record_index = [{"source_unit_ref": ref, "enrichment_payload_sha256": by_ref[ref]["identity"]["enrichment_payload_sha256"]} for ref in sorted(by_ref) if isinstance(by_ref[ref].get("identity"), Mapping)]
    expected_records_hash = sha256_text(canonical_json(record_index))
    if inventory.get("records_sha256") != expected_records_hash or safe.get("records_sha256") != expected_records_hash:
        errors.append("records_sha256_mismatch")
    authority_refs = set(authorities["snapshots"])
    if set(safe.get("authority_snapshot_refs", [])) != authority_refs:
        errors.append("safe_authority_snapshot_refs_invalid")
    for ref, record in by_ref.items():
        if set(record.get("identity", {}).get("authority_snapshot_refs", [])) != authority_refs:
            errors.append(f"record_authority_snapshot_refs_invalid:{ref}")
    text_count, payload_count, safe_errors = safe_field_scan(safe)
    errors.extend(safe_errors)
    summary = safe.get("summary", {}) if isinstance(safe.get("summary"), Mapping) else {}
    authority_write_count = sum(
        record.get("observations", {}).get("quality_and_review", {}).get("authority_write_performed") is not False
        for record in records
    )
    promotion_claim_count = sum(record.get("identity", {}).get("promotion_status") != "not_promoted" for record in records)
    learner_facing_claim_count = sum(
        record.get("identity", {}).get("learner_facing_original_text_allowed") is not False for record in records
    )
    template_copy_count = sum(
        record.get("observations", {}).get("quality_and_review", {}).get("source_text_template_copy_detected") is not False
        for record in records
    )
    derived_summary = {
        "s12a_identities_read": len(identities), "s12b_records_built": len(by_ref), "identity_join_count": len(expected_refs & actual_refs),
        "represented_book_count": len({record.get("identity", {}).get("source_book_id") for record in records}),
        "source_mutation_count": 0, "content_hash_drift_count": content_hash_drifts,
        "record_hash_drift_count": record_hash_drifts,
        "duplicate_source_ref_count": duplicates, "missing_enrichment_record_count": len(missing), "extra_enrichment_record_count": len(extra),
        "payload_hash_mismatch_count": payload_mismatches, "schema_error_count": schema_error_count,
        "records_with_vocabulary_scan": sum(record.get("observations", {}).get("vocabulary_exposure", {}).get("scan_status") == "COMPLETE" for record in records),
        "records_with_chunk_scan": sum(record.get("observations", {}).get("chunk_exposure", {}).get("scan_status") == "COMPLETE" for record in records),
        "records_with_pattern_scan": sum(record.get("observations", {}).get("sentence_pattern_observations", {}).get("scan_status") == "COMPLETE" for record in records),
        "records_with_situation_function_status": sum(bool(record.get("observations", {}).get("situation_function_observations", {}).get("classification_status")) for record in records),
        "records_with_discourse_status": sum(bool(record.get("observations", {}).get("discourse_observation", {}).get("classification_status")) for record in records),
        "records_with_pedagogical_signals": sum(bool(record.get("observations", {}).get("pedagogical_signals")) for record in records),
        "records_with_four_skill_affordance_object": sum(bool(record.get("observations", {}).get("four_skill_affordances")) for record in records),
        "canonical_authority_write_count": authority_write_count,
        "promotion_claim_count": promotion_claim_count,
        "learner_facing_original_text_claim_count": learner_facing_claim_count,
        "source_text_template_copy_claim_count": template_copy_count,
        "safe_source_text_field_count": text_count, "safe_source_payload_field_count": payload_count,
    }
    for key, derived in derived_summary.items():
        if summary.get(key) != derived:
            errors.append(f"safe_summary_accounting_drift:{key}:declared={summary.get(key)}:derived={derived}")
    derived_distributions = {
        name: Counter({key: 0 for key in keys}) for name, keys in STATUS_DISTRIBUTION_KEYS.items()
    }
    for record in records:
        observations = record.get("observations", {})
        derived_distributions["vocabulary_match"].update(
            item.get("match_status") for item in observations.get("vocabulary_exposure", {}).get("items", [])
        )
        derived_distributions["chunk_match"].update(
            item.get("match_status") for item in observations.get("chunk_exposure", {}).get("items", [])
        )
        derived_distributions["pattern_mapping"].update(
            item.get("mapping_status") for item in observations.get("sentence_pattern_observations", {}).get("items", [])
        )
        derived_distributions["situation_classification"].update([
            observations.get("situation_function_observations", {}).get("classification_status")
        ])
        derived_distributions["discourse_shape"].update([
            observations.get("discourse_observation", {}).get("discourse_shape")
        ])
        derived_distributions["semantic_pass"].update([
            observations.get("quality_and_review", {}).get("semantic_pass_status")
        ])
    declared_distributions = safe.get("status_distributions", {})
    for name, counter in derived_distributions.items():
        derived = {key: counter[key] for key in STATUS_DISTRIBUTION_KEYS[name]}
        if declared_distributions.get(name) != derived:
            errors.append(f"status_distribution_accounting_drift:{name}")

    level_counts = Counter(record.get("identity", {}).get("source_level") for record in records)
    semantic_import_count = derived_distributions["semantic_pass"]["APPLIED"]
    derived_coverage = {
        "level_counts": {level: level_counts[level] for level in SOURCE_LEVELS},
        "represented_level_count": sum(level_counts[level] > 0 for level in SOURCE_LEVELS),
        "records_with_semantic_import": semantic_import_count,
    }
    if safe.get("coverage_distributions") != derived_coverage:
        errors.append("coverage_distribution_accounting_drift")
    if safe.get("authority_availability") != authorities["availability"]:
        errors.append("authority_availability_drift")
    derived_claims = {
        "observational_candidate_only": promotion_claim_count == 0,
        "raw_source_text_included": template_copy_count > 0,
        "source_payload_copied": payload_count > 0,
        "canonical_authority_write_performed": authority_write_count > 0,
        "learner_facing_material_created": learner_facing_claim_count > 0,
        "source_files_rewritten": False,
    }
    if safe.get("claim_boundaries") != derived_claims:
        errors.append("claim_boundary_accounting_drift")
    if safe.get("task_id") != TASK_ID:
        errors.append("safe_task_id_mismatch")
    if safe.get("validation_status") != PASS_STATUS:
        errors.append("safe_execution_not_pass")
    if safe.get("errors"):
        errors.append("safe_execution_errors_not_empty")
    compatibility = safe.get("consumer_compatibility", {})
    if enforce_expected_counts and compatibility != {"m04b1_source_count": 54, "m04b1_resolvable_count": 54, "m04b1_unresolved_count": 0, "m04b2_source_integrity_status": "PASS"}:
        errors.append("m04b1_m04b2_compatibility_mismatch")
    return {"task_id": TASK_ID, "validation_status": PASS_STATUS if not errors else "FAIL", "error_count": len(errors), "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT / "raz_output_jsons")
    parser.add_argument("--identity-inventory", type=Path, default=REPO_ROOT / ".local/raz_af/observational_companion_identity_inventory.json")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / ".local/raz_af/observational_enrichment")
    args = parser.parse_args(argv)
    try:
        identity_inventory = read_json(args.identity_inventory)
        source_rows, _hashes = load_source_rows(args.source_root)
        inventory = read_json(args.output_root / "inventory.json")
        safe = read_json(args.output_root / "validation.json")
        records, load_errors = load_private_records(args.output_root, inventory)
        report = validate_extraction(identity_inventory, source_rows, records, inventory, safe)
        if load_errors:
            report["errors"] = load_errors + report["errors"]
            report["error_count"] = len(report["errors"])
            report["validation_status"] = "FAIL"
    except (ValueError, OSError) as exc:
        report = {"task_id": TASK_ID, "validation_status": "FAIL", "error_count": 1, "errors": [str(exc)]}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
