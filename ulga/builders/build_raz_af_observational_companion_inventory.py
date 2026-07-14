#!/usr/bin/env python3
"""Build a deterministic, text-free companion identity inventory for RAZ A-F.

The enriched source records are read-only. Generated artifacts default to `.local/`.
No semantic observation extraction is performed by this S12A adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_ID = "RAZ-AF-S12A_ObservationalCompanionContractAndSourceIntegrityAdapter"
INVENTORY_SCHEMA = "raz.af.observational_companion.inventory.v1"
SAFE_INDEX_SCHEMA = "raz.af.observational_companion.safe_index.v1"
ENRICHMENT_SCHEMA_VERSION = "raz.af.observational_companion.v1"
EXTRACTOR_VERSION = "raz-af-observational-source-integrity-adapter.v1"
PASS_STATUS = "PASS_LOCAL_RAZ_AF_OBSERVATIONAL_COMPANION_CONTRACT"
EXPECTED_LEVELS = tuple("ABCDEF")
EXPECTED_LEVEL_COUNT = 6
EXPECTED_PAGE_UNIT_COUNT = 4925
EXPECTED_BOOK_COUNT = 566
EXPECTED_SELECTED_SOURCE_COUNT = 54
CURRENT_CONSUMER_ID = "E4S-A1V1-M04B1_SELECTED_READING_SOURCES"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SOURCE_REF_RE = re.compile(r"^RAZ_([A-F])_([A-Za-z0-9_-]+)_P([0-9]+)$")
EMPTY_ENRICHMENT_PAYLOAD_SHA256 = hashlib.sha256(b"{}").hexdigest()
SCHEMA_DIR = REPO_ROOT / "ulga/schemas"
IDENTITY_SCHEMA_PATH = SCHEMA_DIR / "raz_af_observational_companion_identity_record.schema.json"
SAFE_INDEX_SCHEMA_PATH = SCHEMA_DIR / "raz_af_observational_companion_safe_index.schema.json"

SOURCE_TEXT_KEYS = {
    "clean_text", "reading_text", "page_text", "passage_text", "normalized_text",
    "raw_text", "text", "content", "sentence", "sentences", "source_sentences",
    "display_text", "transcript_text", "answer_text", "evidence_quote",
}
FORBIDDEN_PAYLOAD_KEYS = {
    "source_payload", "source_record", "source_records", "page_unit", "page_units",
    "sentence_candidates", "deterministic_items", "literal_review_candidates",
    "vocabulary_exposure", "evp_alignment", "chunk_mappings", "sentence_patterns",
    "situation_function_tags", "discourse_structures", "pedagogical_signals",
    "four_skill_template_candidates", "enrichment_payload",
}


class InventoryBuildError(ValueError):
    """Fail-closed source discovery or integrity error."""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryBuildError(f"source_json_unreadable:{path}:{exc}") from exc


def _schema_validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    identity_schema = _read_json(IDENTITY_SCHEMA_PATH)
    safe_index_schema = _read_json(SAFE_INDEX_SCHEMA_PATH)
    registry = Registry().with_resource(
        identity_schema["$id"],
        Resource.from_contents(identity_schema),
    )
    return (
        Draft202012Validator(identity_schema),
        Draft202012Validator(safe_index_schema, registry=registry),
    )


def _format_schema_errors(validator: Draft202012Validator, payload: Any, owner: str) -> list[str]:
    return [
        f"{owner}:{'.'.join(str(part) for part in error.absolute_path) or '$'}:{error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def discover_level_source_files(source_root: Path) -> dict[str, Path]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise InventoryBuildError(f"source_root_not_found:{source_root}")
    discovered: dict[str, list[Path]] = {level: [] for level in EXPECTED_LEVELS}
    pattern = re.compile(r"^raz_([A-F])_page_unit_enriched\.json$", re.IGNORECASE)
    for path in sorted(source_root.rglob("*.json")):
        match = pattern.fullmatch(path.name)
        if not match or path.parent.name.casefold() != "enriched":
            continue
        level = match.group(1).upper()
        if f"Level_{level}" not in path.parts:
            continue
        discovered[level].append(path)
    errors = []
    for level, matches in discovered.items():
        if not matches:
            errors.append(f"level_source_file_missing:{level}")
        elif len(matches) > 1:
            errors.append(f"level_source_file_ambiguous:{level}:{len(matches)}")
    if errors:
        raise InventoryBuildError(";".join(errors))
    return {level: matches[0] for level, matches in discovered.items()}


def _source_hashes(row: Mapping[str, Any], *, level: str, index: int) -> tuple[str, str]:
    text = row.get("text")
    if not isinstance(text, str) or not text.strip():
        raise InventoryBuildError(f"source_content_missing:{level}:{index}")
    content_hash = _sha256_text(text.strip())
    record_hash = _sha256_text(_canonical_json(row))
    if not HEX64.fullmatch(content_hash) or not HEX64.fullmatch(record_hash):
        raise InventoryBuildError(f"source_hash_malformed:{level}:{index}")
    return content_hash, record_hash


def _snapshot_sources(paths: Mapping[str, Path]) -> tuple[list[dict[str, Any]], dict[str, tuple[str, str]]]:
    normalized: list[dict[str, Any]] = []
    hashes: dict[str, tuple[str, str]] = {}
    seen: dict[str, tuple[str, str, int, str, str]] = {}
    duplicate_count = 0
    conflicting_count = 0
    for level in EXPECTED_LEVELS:
        payload = _read_json(paths[level])
        if not isinstance(payload, list):
            raise InventoryBuildError(f"level_source_not_list:{level}")
        for index, row in enumerate(payload):
            if not isinstance(row, Mapping):
                raise InventoryBuildError(f"source_record_not_object:{level}:{index}")
            source_ref = row.get("page_unit_id")
            book_id = row.get("book_id")
            page_number = row.get("page_number")
            if not isinstance(source_ref, str) or not source_ref:
                raise InventoryBuildError(f"source_unit_ref_missing:{level}:{index}")
            ref_match = SOURCE_REF_RE.fullmatch(source_ref)
            if ref_match is None:
                raise InventoryBuildError(f"source_unit_ref_malformed:{level}:{index}:{source_ref}")
            normalized_book_id = str(book_id) if book_id is not None else ""
            if row.get("level") != level or ref_match.group(1) != level:
                raise InventoryBuildError(f"source_identity_level_mismatch:{level}:{index}:{source_ref}")
            if book_id is None or isinstance(book_id, (dict, list, bool)) or not str(book_id).strip():
                raise InventoryBuildError(f"source_book_id_missing:{level}:{index}:{source_ref}")
            if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
                raise InventoryBuildError(f"source_page_number_invalid:{level}:{index}:{source_ref}")
            if ref_match.group(2) != normalized_book_id:
                raise InventoryBuildError(
                    f"source_identity_book_mismatch:{level}:{index}:{source_ref}:book_id={normalized_book_id}"
                )
            if int(ref_match.group(3)) != page_number:
                raise InventoryBuildError(
                    f"source_identity_page_mismatch:{level}:{index}:{source_ref}:page_number={page_number}"
                )
            content_hash, record_hash = _source_hashes(row, level=level, index=index)
            identity = (level, normalized_book_id, page_number, content_hash, record_hash)
            if source_ref in seen:
                duplicate_count += 1
                if seen[source_ref] != identity:
                    conflicting_count += 1
                continue
            seen[source_ref] = identity
            hashes[source_ref] = (content_hash, record_hash)
            normalized.append(
                {
                    "source_unit_ref": source_ref,
                    "source_level": level,
                    "source_book_id": normalized_book_id,
                    "source_page_number": page_number,
                    "source_content_sha256": content_hash,
                    "source_record_sha256": record_hash,
                }
            )
    if duplicate_count or conflicting_count:
        raise InventoryBuildError(
            f"duplicate_or_conflicting_source_unit_refs:duplicates={duplicate_count}:conflicts={conflicting_count}"
        )
    normalized.sort(key=lambda row: row["source_unit_ref"])
    return normalized, hashes


def _build_identity_record(source: Mapping[str, Any]) -> dict[str, Any]:
    source_ref = str(source["source_unit_ref"])
    return {
        "observational_record_id": f"RAZ_AF_OBS_V1__{source_ref}",
        "source_unit_ref": source_ref,
        "source_level": source["source_level"],
        "source_book_id": source["source_book_id"],
        "source_page_number": source["source_page_number"],
        "source_record_sha256": source["source_record_sha256"],
        "source_content_sha256": source["source_content_sha256"],
        "enrichment_schema_version": ENRICHMENT_SCHEMA_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "authority_snapshot_refs": [],
        "enrichment_payload_sha256": EMPTY_ENRICHMENT_PAYLOAD_SHA256,
        "source_role": "observational_reference",
        "authority_import_allowed": False,
        "learner_facing_original_text_allowed": False,
        "promotion_status": "not_promoted",
    }


def scan_forbidden_safe_fields(value: Any) -> tuple[int, int, list[str]]:
    text_count = 0
    payload_count = 0
    errors: list[str] = []

    def visit(child: Any, pointer: str = "$") -> None:
        nonlocal text_count, payload_count
        if isinstance(child, Mapping):
            for key, nested in child.items():
                next_pointer = f"{pointer}.{key}"
                if key in SOURCE_TEXT_KEYS:
                    text_count += 1
                    errors.append(f"safe_output_forbidden_text_key:{next_pointer}")
                if key in FORBIDDEN_PAYLOAD_KEYS:
                    payload_count += 1
                    errors.append(f"safe_output_forbidden_payload_key:{next_pointer}")
                visit(nested, next_pointer)
        elif isinstance(child, list):
            for index, nested in enumerate(child):
                visit(nested, f"{pointer}[{index}]")

    visit(value)
    return text_count, payload_count, errors


def _drift_counts(
    before: Mapping[str, tuple[str, str]],
    after: Mapping[str, tuple[str, str]],
) -> tuple[int, int, int]:
    refs = set(before) | set(after)
    content_drift = sum(before.get(ref, (None, None))[0] != after.get(ref, (None, None))[0] for ref in refs)
    record_drift = sum(before.get(ref, (None, None))[1] != after.get(ref, (None, None))[1] for ref in refs)
    mutation = sum(before.get(ref) != after.get(ref) for ref in refs)
    return mutation, content_drift, record_drift


def _default_consumer_source_refs() -> dict[str, list[str]]:
    # The current A1/A1+ selection is a consumer compatibility gate, not part of
    # the stage-neutral companion identity contract.
    from ulga.builders.build_a1_a1plus_local_reading_practice_bank import _selected_records

    return {
        CURRENT_CONSUMER_ID: [str(row["source_unit_ref"]) for row in _selected_records()]
    }


def _consumer_compatibility(
    consumer_source_refs: Mapping[str, Iterable[str]],
    available_source_refs: set[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for consumer_id in sorted(consumer_source_refs):
        refs = [str(ref) for ref in consumer_source_refs[consumer_id]]
        if len(refs) != len(set(refs)):
            raise InventoryBuildError(f"consumer_duplicate_source_ref:{consumer_id}")
        resolvable = sum(ref in available_source_refs for ref in refs)
        result.append(
            {
                "consumer_id": consumer_id,
                "source_ref_count": len(refs),
                "resolvable_source_ref_count": resolvable,
                "unresolved_source_ref_count": len(refs) - resolvable,
            }
        )
    return result


def build_inventory(
    source_root: Path,
    *,
    consumer_source_refs: Mapping[str, Iterable[str]] | None = None,
    enforce_expected_counts: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = discover_level_source_files(source_root)
    sources, before_hashes = _snapshot_sources(paths)
    records = [_build_identity_record(source) for source in sources]
    if consumer_source_refs is None:
        consumer_source_refs = _default_consumer_source_refs()
    source_refs = set(before_hashes)
    consumer_compatibility = _consumer_compatibility(consumer_source_refs, source_refs)

    # Re-read after construction to detect concurrent source changes or accidental writes.
    _, after_hashes = _snapshot_sources(paths)
    mutation_count, content_drift_count, record_drift_count = _drift_counts(before_hashes, after_hashes)
    level_counts = Counter(str(row["source_level"]) for row in records)
    represented_books = {(str(row["source_level"]), str(row["source_book_id"])) for row in records}
    errors: list[str] = []
    if enforce_expected_counts:
        if len(paths) != EXPECTED_LEVEL_COUNT:
            errors.append(f"discovered_level_count_not_{EXPECTED_LEVEL_COUNT}:actual={len(paths)}")
        if len(records) != EXPECTED_PAGE_UNIT_COUNT:
            errors.append(f"discovered_page_unit_count_not_{EXPECTED_PAGE_UNIT_COUNT}:actual={len(records)}")
        if len(represented_books) != EXPECTED_BOOK_COUNT:
            errors.append(f"represented_book_count_not_{EXPECTED_BOOK_COUNT}:actual={len(represented_books)}")
        current_consumer = next(
            (row for row in consumer_compatibility if row["consumer_id"] == CURRENT_CONSUMER_ID),
            None,
        )
        if current_consumer is None:
            errors.append("current_a1_a1plus_consumer_compatibility_missing")
        elif (
            current_consumer["source_ref_count"] != EXPECTED_SELECTED_SOURCE_COUNT
            or current_consumer["resolvable_source_ref_count"] != EXPECTED_SELECTED_SOURCE_COUNT
            or current_consumer["unresolved_source_ref_count"] != 0
        ):
            errors.append(
                "current_a1_a1plus_consumer_not_fully_resolvable:"
                f"actual={current_consumer}"
            )
    if mutation_count:
        errors.append(f"source_record_mutation_detected:actual={mutation_count}")
    if content_drift_count:
        errors.append(f"source_content_hash_drift_detected:actual={content_drift_count}")
    if record_drift_count:
        errors.append(f"source_record_hash_drift_detected:actual={record_drift_count}")

    records_hash = _sha256_text(_canonical_json(records))
    summary = {
        "discovered_level_count": len(paths),
        "discovered_levels": sorted(paths),
        "discovered_page_unit_count": len(records),
        "represented_book_count": len(represented_books),
        "page_unit_counts_by_level": {level: level_counts[level] for level in EXPECTED_LEVELS},
        "source_record_mutation_count": mutation_count,
        "source_content_hash_drift_count": content_drift_count,
        "source_record_hash_drift_count": record_drift_count,
        "duplicate_source_unit_ref_count": 0,
        "conflicting_source_unit_ref_count": 0,
        "source_text_field_count": 0,
        "forbidden_payload_field_count": 0,
    }
    boundaries = {
        "metadata_and_hashes_only": True,
        "raw_source_text_included": False,
        "source_payload_copied": False,
        "semantic_extraction_performed": False,
        "authority_import_allowed": False,
        "learner_facing_original_text_allowed": False,
        "canonical_graph_write_performed": False,
        "source_files_rewritten": False,
    }
    safe_index: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SAFE_INDEX_SCHEMA,
        "artifact_type": "raz_af_observational_companion_metadata_hash_index",
        "summary": summary,
        "consumer_compatibility": consumer_compatibility,
        "records_sha256": records_hash,
        "records": records,
        "claim_boundaries": boundaries,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "errors": errors,
    }
    text_count, payload_count, forbidden_errors = scan_forbidden_safe_fields(safe_index)
    summary["source_text_field_count"] = text_count
    summary["forbidden_payload_field_count"] = payload_count
    if forbidden_errors:
        safe_index["errors"].extend(forbidden_errors)
        safe_index["validation_status"] = "FAIL"
        raise InventoryBuildError(";".join(forbidden_errors))
    identity_validator, safe_index_validator = _schema_validators()
    schema_errors: list[str] = []
    for index, record in enumerate(records):
        schema_errors.extend(_format_schema_errors(identity_validator, record, f"identity_schema:{index}"))
    schema_errors.extend(_format_schema_errors(safe_index_validator, safe_index, "safe_index_schema"))
    if schema_errors:
        raise InventoryBuildError("schema_validation_failed:" + ";".join(schema_errors))
    inventory = {
        "task_id": TASK_ID,
        "schema_version": INVENTORY_SCHEMA,
        "artifact_type": "private_local_raz_af_observational_companion_identity_inventory",
        "private_local_only": True,
        "records_sha256": records_hash,
        "records": records,
    }
    return inventory, safe_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the local RAZ A-F observational companion identity inventory.")
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT / "raz_output_jsons")
    parser.add_argument(
        "--inventory-output",
        type=Path,
        default=REPO_ROOT / ".local/raz_af/observational_companion_identity_inventory.json",
    )
    parser.add_argument(
        "--safe-report",
        type=Path,
        default=REPO_ROOT / ".local/raz_af/observational_companion_safe_index.json",
    )
    args = parser.parse_args(argv)
    try:
        inventory, safe_index = build_inventory(args.source_root)
    except (InventoryBuildError, FileNotFoundError, ValueError) as exc:
        print(f"validation_status=FAIL\nerror={exc}", file=sys.stderr)
        return 1
    _write_json_atomic(args.inventory_output, inventory)
    _write_json_atomic(args.safe_report, safe_index)
    print(json.dumps(safe_index["summary"], sort_keys=True))
    print(f"validation_status={safe_index['validation_status']}")
    return 0 if safe_index["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
