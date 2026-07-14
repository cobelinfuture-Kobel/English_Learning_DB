#!/usr/bin/env python3
"""Export a metadata-only A1/A1+ Reading source manifest from local RAZ data.

This tool is intentionally run on the operator's local machine. It scans JSON and
JSONL records, but never writes source text, passage text, sentence strings, or
other copyrighted payloads to the output manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

TASK_ID = "E4S-A1V1-M04B_SafeReadingSourceManifestExporter"
SCHEMA_VERSION = "e4s.a1v1.safe_reading_source_manifest.v1"

IDENTITY_KEYS = (
    "reading_intake_id",
    "reuse_unit_id",
    "page_unit_id",
    "sentence_candidate_id",
    "source_record_id",
    "candidate_id",
    "reading_id",
    "unit_id",
    "id",
)
TEXT_KEYS = {
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
}
EXCLUDED_PATH_FRAGMENTS = {
    "audio_timeline_extract",
    "failed_items",
    "warning_report",
    "drive_manifest",
    "count_reconciliation",
    "discovery_drift_validation",
    "downstream_discovery_drift_validation",
}
TAG_GROUPS = {
    "theme_tags": ("theme_tags", "themes", "theme_hint", "theme"),
    "grammar_tags": ("grammar_tags", "grammar_tag", "grammar_focus"),
    "pattern_tags": ("pattern_tags", "pattern_tag", "patterns"),
    "vocabulary_tags": ("vocabulary_tags", "vocabulary_tag", "vocabulary_refs"),
    "reusability_tags": (
        "reusability_tags",
        "reuse_tags",
        "future_reuse_candidates",
    ),
}
NESTED_METADATA_KEYS = (
    "tags",
    "pedagogical_tags",
    "linguistic_tags",
    "source_tags",
    "source_traceability",
    "artifact_pointer",
    "text_meta",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_scalar(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text or None


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    output: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            item = (
                item.get("id")
                or item.get("tag")
                or item.get("name")
                or item.get("value")
                or item.get("word")
                or item.get("pattern")
            )
        normalized = _normalize_scalar(item)
        if normalized and normalized not in output:
            output.append(normalized)
    return output


def _nested_mappings(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result = [record]
    for key in NESTED_METADATA_KEYS:
        value = record.get(key)
        if isinstance(value, Mapping):
            result.append(value)
    return result


def _first_value(record: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for mapping in _nested_mappings(record):
        for key in keys:
            value = mapping.get(key)
            if value not in (None, "", [], {}):
                return value
    return None


def _contains_text_payload(record: Mapping[str, Any]) -> bool:
    for mapping in _nested_mappings(record):
        for key in TEXT_KEYS:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return True
            if isinstance(value, list) and value:
                return True
    return False


def _iter_text_fragments(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        if value.strip():
            yield value.strip()
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_text_fragments(item)
        return
    if isinstance(value, Mapping):
        for key in TEXT_KEYS:
            if key in value:
                yield from _iter_text_fragments(value[key])


def _text_statistics(record: Mapping[str, Any]) -> dict[str, int]:
    fragments: list[str] = []
    for mapping in _nested_mappings(record):
        for key in TEXT_KEYS:
            if key in mapping:
                fragments.extend(_iter_text_fragments(mapping[key]))
    joined = "\n".join(dict.fromkeys(fragments))
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", joined)
    explicit_sentence_count = _first_value(
        record,
        ("sentence_count", "sentences_count", "unit_sentence_count"),
    )
    try:
        sentence_count = max(0, int(explicit_sentence_count))
    except (TypeError, ValueError):
        sentence_count = 0
    if not sentence_count and joined:
        sentence_count = max(
            1,
            len([line for line in joined.splitlines() if line.strip()]),
            len(re.findall(r"[.!?]+(?:\s|$)", joined)),
        )
    return {
        "character_count": len(joined),
        "word_count": len(words),
        "sentence_count": sentence_count,
    }


def _level_from_path(path: Path) -> str | None:
    text = path.as_posix()
    for pattern in (
        r"Level[_\-/ ]([A-Z]{1,3})(?:[/_.-]|$)",
        r"raz[_\-/]([A-Z]{1,3})(?:[/_.-]|$)",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def _extract_level(record: Mapping[str, Any], path: Path) -> str:
    value = _first_value(
        record,
        ("normalized_level", "source_level", "level", "raz_level", "reading_level"),
    )
    normalized = _normalize_scalar(value)
    return normalized.upper() if normalized else (_level_from_path(path) or "UNKNOWN")


def _extract_source_type(record: Mapping[str, Any], path: Path) -> str:
    explicit = _normalize_scalar(_first_value(record, ("source_type", "unit_type")))
    if explicit:
        return explicit.lower()
    lowered = path.as_posix().lower()
    if "reuse" in lowered:
        return "reuse_unit_candidate"
    if "page_unit" in lowered or "page-units" in lowered:
        return "page_unit"
    if "sentence" in lowered:
        return "sentence_candidate"
    if "enriched" in lowered:
        return "enriched_reading_unit"
    if "normalized" in lowered:
        return "normalized_reading_unit"
    return "derived_reading_unit"


def _extract_tags(record: Mapping[str, Any], keys: Iterable[str]) -> list[str]:
    values: list[str] = []
    for mapping in _nested_mappings(record):
        for key in keys:
            for value in _normalize_list(mapping.get(key)):
                if value not in values:
                    values.append(value)
    return sorted(values)


def _candidate_record(record: Mapping[str, Any]) -> bool:
    has_identity = any(_normalize_scalar(record.get(key)) for key in IDENTITY_KEYS)
    has_source_metadata = any(
        _first_value(record, keys)
        for keys in (
            ("source_level", "normalized_level", "level"),
            ("source_type", "unit_type"),
            ("source_book_id", "book_id"),
        )
    )
    return (has_identity or has_source_metadata) and _contains_text_payload(record)


def _iter_candidate_records(value: Any, pointer: str = "$") -> Iterator[tuple[str, Mapping[str, Any]]]:
    if isinstance(value, Mapping):
        if _candidate_record(value):
            yield pointer, value
            return
        for key, child in value.items():
            if isinstance(child, (Mapping, list)):
                yield from _iter_candidate_records(child, f"{pointer}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (Mapping, list)):
                yield from _iter_candidate_records(child, f"{pointer}[{index}]")


def _read_json_records(path: Path) -> Any:
    if path.suffix.lower() == ".jsonl":
        rows = []
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    rows.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}:{exc}") from exc
        return rows
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _safe_source_ref(record: Mapping[str, Any], relative_path: str, pointer: str) -> str:
    value = _first_value(record, IDENTITY_KEYS)
    normalized = _normalize_scalar(value)
    if normalized:
        return normalized
    return f"AUTO:{_sha256_text(relative_path + '#' + pointer)[:20]}"


def _record_to_manifest_entry(
    record: Mapping[str, Any],
    *,
    source_root: Path,
    path: Path,
    pointer: str,
) -> dict[str, Any]:
    relative_path = path.relative_to(source_root).as_posix()
    stats = _text_statistics(record)
    source_ref = _safe_source_ref(record, relative_path, pointer)
    tags = {
        name: _extract_tags(record, keys)
        for name, keys in TAG_GROUPS.items()
    }
    return {
        "source_unit_ref": source_ref,
        "source_locator": f"{relative_path}#{pointer}",
        "source_level": _extract_level(record, path),
        "normalized_level": _extract_level(record, path),
        "source_type": _extract_source_type(record, path),
        "book_id": _normalize_scalar(
            _first_value(record, ("book_id", "source_book_id", "book_key", "title_id"))
        ),
        "page_number": _first_value(
            record, ("page_number", "source_page_number", "page_index", "page")
        ),
        "sentence_count": stats["sentence_count"],
        "word_count": stats["word_count"],
        "character_count": stats["character_count"],
        **tags,
        "allowed_use": "PRIVATE_LOCAL_DERIVED_READING_PIPELINE_ONLY",
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "content_access": "LOCAL_SOURCE_REQUIRED_NOT_EMBEDDED",
        "evidence_refs": [
            f"path:{relative_path}",
            f"pointer:{pointer}",
            f"record_sha256:{_sha256_text(_canonical_json(record))}",
        ],
        "source_policy": {
            "raw_source_text_included": False,
            "full_passage_text_included": False,
            "sentence_text_included": False,
            "source_payload_copied": False,
            "metadata_and_hashes_only": True,
        },
    }


def discover_source_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    for suffix in ("*.json", "*.jsonl"):
        for path in source_root.rglob(suffix):
            lowered = path.as_posix().lower()
            if any(fragment in lowered for fragment in EXCLUDED_PATH_FRAGMENTS):
                continue
            files.append(path)
    return sorted(set(files))


def build_manifest(
    source_root: Path,
    *,
    levels: Iterable[str] = (),
    max_records: int = 0,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"source_root_not_found:{source_root}")
    allowed_levels = {str(level).upper() for level in levels if str(level).strip()}
    entries: list[dict[str, Any]] = []
    parse_warnings: list[str] = []
    scanned_files = discover_source_files(source_root)
    for path in scanned_files:
        try:
            payload = _read_json_records(path)
        except Exception as exc:  # pragma: no cover - warning path is integration-dependent
            parse_warnings.append(f"parse_skipped:{path.relative_to(source_root).as_posix()}:{exc}")
            continue
        for pointer, record in _iter_candidate_records(payload):
            entry = _record_to_manifest_entry(
                record,
                source_root=source_root,
                path=path,
                pointer=pointer,
            )
            if allowed_levels and entry["source_level"] not in allowed_levels:
                continue
            entries.append(entry)
            if max_records > 0 and len(entries) >= max_records:
                break
        if max_records > 0 and len(entries) >= max_records:
            break

    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        key = (entry["source_unit_ref"], entry["source_locator"])
        deduped[key] = entry
    entries = sorted(
        deduped.values(),
        key=lambda row: (
            row["source_level"],
            row["book_id"] or "",
            row["page_number"] if isinstance(row["page_number"], int) else 10**9,
            row["source_unit_ref"],
            row["source_locator"],
        ),
    )
    by_level = Counter(entry["source_level"] for entry in entries)
    by_source_type = Counter(entry["source_type"] for entry in entries)
    return {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "a1_a1plus_reading_source_metadata_manifest",
        "scope": {
            "target_program": "E4S_A1V1",
            "requested_levels": sorted(allowed_levels),
            "cefr_mapping_claimed": False,
            "operator_review_required_before_content_binding": True,
        },
        "source_root_name": source_root.name,
        "summary": {
            "scanned_file_count": len(scanned_files),
            "manifest_record_count": len(entries),
            "levels": dict(sorted(by_level.items())),
            "source_types": dict(sorted(by_source_type.items())),
            "parse_warning_count": len(parse_warnings),
        },
        "records": entries,
        "parse_warnings": parse_warnings,
        "claim_boundaries": {
            "raw_source_text_included": False,
            "full_passage_text_included": False,
            "sentence_text_included": False,
            "source_payload_copied": False,
            "metadata_only_manifest": True,
            "reading_v1_content_complete": False,
            "learner_evidence_created": False,
            "mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "next_resume_task": "E4S-A1V1-M04B_SourceGroundedReadingPracticeBankCompletion",
    }


def _assert_no_text_payload(manifest: Mapping[str, Any]) -> None:
    forbidden_keys = TEXT_KEYS | {
        "display_text",
        "transcript_text",
        "answer_text",
        "evidence_quote",
    }

    def visit(value: Any, path: str = "$") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in forbidden_keys:
                    raise ValueError(f"forbidden_text_key_in_manifest:{path}.{key}")
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(manifest)


def validate_manifest(manifest: Mapping[str, Any], *, require_records: bool = True) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    records = manifest.get("records")
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if require_records and not records:
        errors.append("manifest_has_no_records")
    for index, record in enumerate(records):
        prefix = f"record:{index}"
        for field in (
            "source_unit_ref",
            "source_locator",
            "source_level",
            "source_type",
            "evidence_refs",
            "source_policy",
        ):
            if record.get(field) in (None, "", [], {}):
                errors.append(f"{prefix}:missing:{field}")
        policy = record.get("source_policy", {})
        if not isinstance(policy, Mapping) or policy.get("metadata_and_hashes_only") is not True:
            errors.append(f"{prefix}:unsafe_source_policy")
        if any(
            policy.get(field) is not False
            for field in (
                "raw_source_text_included",
                "full_passage_text_included",
                "sentence_text_included",
                "source_payload_copied",
            )
        ):
            errors.append(f"{prefix}:text_or_payload_inclusion_claim")
    try:
        _assert_no_text_payload(manifest)
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export metadata-only Reading source manifest; no source text is written."
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--levels", nargs="*", default=[])
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Write an empty diagnostic manifest instead of failing when no records are found.",
    )
    args = parser.parse_args(argv)
    manifest = build_manifest(
        args.source_root,
        levels=args.levels,
        max_records=max(0, args.max_records),
    )
    errors = validate_manifest(manifest, require_records=not args.allow_empty)
    write_manifest(args.output, manifest)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "record_count": manifest["summary"]["manifest_record_count"],
                "levels": manifest["summary"]["levels"],
                "validation_status": "PASS" if not errors else "FAIL",
                "errors": errors,
            },
            ensure_ascii=False,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
