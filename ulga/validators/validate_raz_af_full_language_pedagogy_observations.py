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
    TASK_ID,
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
                errors.append(f"source_content_hash_drift:{ref}")
            if identity.get("source_record_sha256") != record_hash:
                errors.append(f"source_record_hash_drift:{ref}")
        if identity.get("authority_import_allowed") is not False or identity.get("promotion_status") != "not_promoted":
            errors.append(f"canonical_promotion_claim:{ref}")
        if identity.get("learner_facing_original_text_allowed") is not False:
            errors.append(f"learner_facing_original_text_claim:{ref}")
        if isinstance(observations, Mapping):
            quality = observations.get("quality_and_review", {})
            if quality.get("authority_write_performed") is not False:
                errors.append(f"canonical_authority_write_claim:{ref}")
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
    authority_refs = set(load_authorities()["snapshots"])
    if set(safe.get("authority_snapshot_refs", [])) != authority_refs:
        errors.append("safe_authority_snapshot_refs_invalid")
    for ref, record in by_ref.items():
        if set(record.get("identity", {}).get("authority_snapshot_refs", [])) != authority_refs:
            errors.append(f"record_authority_snapshot_refs_invalid:{ref}")
    text_count, payload_count, safe_errors = safe_field_scan(safe)
    errors.extend(safe_errors)
    summary = safe.get("summary", {}) if isinstance(safe.get("summary"), Mapping) else {}
    derived_summary = {
        "s12a_identities_read": len(identities), "s12b_records_built": len(by_ref), "identity_join_count": len(expected_refs & actual_refs),
        "represented_book_count": len({record.get("identity", {}).get("source_book_id") for record in records}),
        "duplicate_source_ref_count": duplicates, "missing_enrichment_record_count": len(missing), "extra_enrichment_record_count": len(extra),
        "payload_hash_mismatch_count": payload_mismatches, "schema_error_count": schema_error_count,
        "records_with_vocabulary_scan": sum(record.get("observations", {}).get("vocabulary_exposure", {}).get("scan_status") == "COMPLETE" for record in records),
        "records_with_chunk_scan": sum(record.get("observations", {}).get("chunk_exposure", {}).get("scan_status") == "COMPLETE" for record in records),
        "records_with_pattern_scan": sum(record.get("observations", {}).get("sentence_pattern_observations", {}).get("scan_status") == "COMPLETE" for record in records),
        "records_with_situation_function_status": sum(bool(record.get("observations", {}).get("situation_function_observations", {}).get("classification_status")) for record in records),
        "records_with_discourse_status": sum(bool(record.get("observations", {}).get("discourse_observation", {}).get("classification_status")) for record in records),
        "records_with_pedagogical_signals": sum(bool(record.get("observations", {}).get("pedagogical_signals")) for record in records),
        "records_with_four_skill_affordance_object": sum(bool(record.get("observations", {}).get("four_skill_affordances")) for record in records),
        "safe_source_text_field_count": text_count, "safe_source_payload_field_count": payload_count,
    }
    for key, derived in derived_summary.items():
        if summary.get(key) != derived:
            errors.append(f"safe_summary_accounting_drift:{key}:declared={summary.get(key)}:derived={derived}")
    for zero_key in ("source_mutation_count", "content_hash_drift_count", "record_hash_drift_count", "canonical_authority_write_count", "promotion_claim_count", "learner_facing_original_text_claim_count"):
        if summary.get(zero_key) != 0:
            errors.append(f"safe_summary_nonzero:{zero_key}:{summary.get(zero_key)}")
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
