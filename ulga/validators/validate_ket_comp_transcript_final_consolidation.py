from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from ulga.builders import build_ket_comp_transcript_final_consolidation as builder

PASS_STATUS = "PASS_99_OF_99_SOURCES_READ_TRACED_VALIDATED"
REPORT_NAME = "transcript_consolidation_validation_report.json"
SRT_PASS_STATUS = "PASS_KET99_P004_P102_ONE_SHOT_CORPUS_VALIDATION"
SRT_REPORT_NAME = "final_validation_result.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _duplicates(values: list[str]) -> list[str]:
    seen, duplicates = set(), set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _scan_forbidden_public_keys(value: Any, path: str = "$") -> list[str]:
    forbidden = {"text", "cues", "transcript_text", "raw_source_dir", "private_body_path"}
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                findings.append(f"{path}.{key}")
            findings.extend(_scan_forbidden_public_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan_forbidden_public_keys(child, f"{path}[{index}]"))
    return findings


def _load_publication_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_srt_publication(
    raw_source_dir: Path,
    private_output_dir: Path,
    public_output_dir: Path,
    semantic_seed_path: Path,
    *,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    records = builder.intake_srt_corpus(raw_source_dir)
    manifest_path = public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["manifest"]
    manifest = _load_json(manifest_path)
    digest_mapping = _load_json(
        public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["digest_mapping"]
    )
    semantic_rows = _load_publication_jsonl(
        public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["semantic"]
    )
    content_rows = _load_publication_jsonl(
        public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["content"]
    )
    evidence_resolution = _load_json(
        public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["evidence_resolution"]
    )
    shard_index = _load_json(
        public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["shard_index"]
    )
    consumer_locator = _load_json(
        public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["consumer_locator"]
    )
    artifact_index = _load_json(
        public_output_dir / builder.SRT_PUBLIC_FILE_NAMES["artifact_index"]
    )
    private_body_path = private_output_dir / builder.SRT_PRIVATE_BODY_NAME

    sources = manifest.get("sources", [])
    source_ids = [row.get("transcript_id") for row in sources]
    expected_ids = [f"P{number:03d}" for number in builder.SRT_EXPECTED_NUMBERS]
    if source_ids != expected_ids:
        errors.append("manifest_transcript_range_invalid")
    if manifest.get("source_count") != 99 or len(sources) != 99:
        errors.append("manifest_source_count_invalid")
    if _duplicates([str(value) for value in source_ids]):
        errors.append("duplicate_transcript_ids")
    required_manifest_fields = {
        "transcript_id",
        "original_filename",
        "unit_id",
        "textbook_page",
        "lesson_type",
        "source_format",
        "encoding",
        "cue_count",
        "first_timestamp",
        "last_timestamp",
        "duration",
        "file_size",
        "sha256",
        "raw_text_persistence",
        "repository_export_allowed",
        "authority_status",
        "intake_status",
        "derived_artifact_ids",
    }
    for source in sources:
        missing_fields = sorted(required_manifest_fields - set(source))
        if missing_fields:
            errors.append(
                f"manifest_fields_missing:{source.get('transcript_id')}:{missing_fields}"
            )
        if source.get("repository_export_allowed") is not False:
            errors.append(f"raw_export_policy_invalid:{source.get('transcript_id')}")
        if source.get("authority_status") != builder.AUTHORITY:
            errors.append(f"authority_status_invalid:{source.get('transcript_id')}")
        if source.get("intake_status") != "accepted":
            errors.append(f"intake_status_invalid:{source.get('transcript_id')}")

    intake_by_id = {metadata["transcript_id"]: metadata for metadata, _ in records}
    for source in sources:
        actual = intake_by_id.get(source.get("transcript_id"))
        if not actual or source.get("sha256") != actual["sha256"]:
            errors.append(f"source_digest_mismatch:{source.get('transcript_id')}")
    mapping_rows = digest_mapping.get("mappings", [])
    if len(mapping_rows) != 99:
        errors.append("digest_mapping_count_invalid")
    mapping_by_id = {row.get("transcript_id"): row for row in mapping_rows}
    if set(mapping_by_id) != set(expected_ids):
        errors.append("digest_mapping_identity_range_invalid")
    if len(semantic_rows) != 99 or [row.get("transcript_id") for row in semantic_rows] != expected_ids:
        errors.append("semantic_artifact_identity_range_invalid")
    if len(content_rows) != 99 or [row.get("transcript_id") for row in content_rows] != expected_ids:
        errors.append("cp07b_content_identity_range_invalid")
    for row in content_rows:
        transcript_id = row.get("transcript_id")
        source_span = row.get("source_span", {})
        if source_span.get("evidence_sha256") != intake_by_id[transcript_id]["sha256"]:
            errors.append(f"cp07b_source_lineage_mismatch:{transcript_id}")
        if row.get("authority_status") != builder.AUTHORITY:
            errors.append(f"cp07b_authority_status_invalid:{transcript_id}")

    resolution_by_id = {
        row.get("transcript_id"): row
        for row in evidence_resolution.get("results", [])
    }
    if set(resolution_by_id) != {"P008", "P026"}:
        errors.append("evidence_resolution_identity_invalid")
    for transcript_id in ("P008", "P026"):
        row = resolution_by_id.get(transcript_id, {})
        if row.get("resolution_status") != "RESOLVED":
            errors.append(f"evidence_resolution_unresolved:{transcript_id}")
        if row.get("source_sha256") != intake_by_id[transcript_id]["sha256"]:
            errors.append(f"evidence_resolution_source_digest_mismatch:{transcript_id}")
        if not row.get("evidence_anchors"):
            errors.append(f"evidence_resolution_anchor_missing:{transcript_id}")

    if shard_index.get("sharding_triggered") is not False:
        errors.append("unexpected_sharding")
    if shard_index.get("shard_count") != 0 or shard_index.get("shards") != []:
        errors.append("unsharded_index_invalid")
    unsharded = shard_index.get("unsharded_private_body", {})
    if not private_body_path.is_file():
        errors.append("private_normalized_body_missing")
    else:
        if private_body_path.stat().st_size >= builder.MAX_UNSHARDED_ARTIFACT_BYTES:
            errors.append("private_normalized_body_requires_sharding")
        if unsharded.get("sha256") != _sha256(private_body_path):
            errors.append("private_normalized_body_digest_mismatch")
        private_rows = _load_publication_jsonl(private_body_path)
        if len(private_rows) != 99:
            errors.append("private_normalized_body_count_invalid")

    if consumer_locator.get("private_body") != builder.SRT_PRIVATE_LOGICAL_LOCATOR:
        errors.append("private_body_logical_locator_invalid")
    if ":\\" in json.dumps(consumer_locator, ensure_ascii=False):
        errors.append("private_absolute_locator_leaked")

    public_values: list[Any] = [
        manifest,
        digest_mapping,
        semantic_rows,
        content_rows,
        evidence_resolution,
        shard_index,
        consumer_locator,
        artifact_index,
    ]
    forbidden_findings = [
        finding
        for value in public_values
        for finding in _scan_forbidden_public_keys(value)
    ]
    if forbidden_findings:
        errors.append(f"private_text_key_leak:{forbidden_findings[:10]}")

    indexed_paths = {
        row["path"]: row
        for row in artifact_index.get("artifacts", [])
        if row.get("repository_export_allowed") is True
    }
    for filename in (
        value
        for key, value in builder.SRT_PUBLIC_FILE_NAMES.items()
        if key != "artifact_index"
    ):
        path = public_output_dir / filename
        index_row = indexed_paths.get(filename)
        if not path.is_file() or not index_row:
            errors.append(f"artifact_index_entry_missing:{filename}")
        elif index_row.get("sha256") != _sha256(path):
            errors.append(f"artifact_index_digest_mismatch:{filename}")

    schema_validation_status = "NOT_REQUESTED"
    if schema_path:
        try:
            import jsonschema

            jsonschema.validate(manifest, _load_json(schema_path))
            schema_validation_status = "PASS"
        except Exception as exc:  # pragma: no cover - exact dependency errors vary
            schema_validation_status = "FAIL"
            errors.append(f"manifest_schema_validation_failed:{exc}")

    deterministic_files = sorted(builder.SRT_PUBLIC_FILE_NAMES.values())
    with tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as second_temp:
        first_root = Path(first_temp)
        second_root = Path(second_temp)
        first_public, first_private = first_root / "public", first_root / "private"
        second_public, second_private = second_root / "public", second_root / "private"
        builder.build_from_srt(
            raw_source_dir, first_private, first_public, semantic_seed_path
        )
        builder.build_from_srt(
            raw_source_dir, second_private, second_public, semantic_seed_path
        )
        for filename in deterministic_files:
            first_bytes = (first_public / filename).read_bytes()
            second_bytes = (second_public / filename).read_bytes()
            if first_bytes != second_bytes:
                errors.append(f"deterministic_double_build_drift:{filename}")
            if first_bytes != (public_output_dir / filename).read_bytes():
                errors.append(f"published_artifact_rebuild_drift:{filename}")
        first_body = (first_private / builder.SRT_PRIVATE_BODY_NAME).read_bytes()
        second_body = (second_private / builder.SRT_PRIVATE_BODY_NAME).read_bytes()
        if first_body != second_body:
            errors.append("deterministic_double_build_drift:private_body")
        if first_body != private_body_path.read_bytes():
            errors.append("published_artifact_rebuild_drift:private_body")

    duplicate_content_count = len(
        {
            metadata["sha256"]
            for metadata, _ in records
            if sum(
                other["sha256"] == metadata["sha256"]
                for other, _ in records
            )
            > 1
        }
    )
    report = {
        "task_id": builder.SRT_TASK_ID,
        "schema_version": "ket99.srt.validation_result.v1",
        "validation_status": SRT_PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "source_count": len(records),
        "valid_source_count": len(records) if not errors else 0,
        "invalid_source_count": 0 if not errors else len(records),
        "source_range": ["P004", "P102"],
        "missing_transcripts": sorted(set(expected_ids) - set(source_ids)),
        "duplicate_transcript_ids": _duplicates([str(value) for value in source_ids]),
        "duplicate_content_count": duplicate_content_count,
        "total_cue_count": sum(metadata["cue_count"] for metadata, _ in records),
        "total_duration_ms": sum(metadata["duration_ms"] for metadata, _ in records),
        "regular_lesson_count": sum(
            metadata["lesson_type"] == "regular" for metadata, _ in records
        ),
        "review_lesson_count": sum(
            metadata["lesson_type"] == "review" for metadata, _ in records
        ),
        "grand_review_lesson_count": sum(
            metadata["lesson_type"] == "grand_review" for metadata, _ in records
        ),
        "p008_source_sha256": intake_by_id["P008"]["sha256"],
        "p008_resolution_status": resolution_by_id.get("P008", {}).get(
            "resolution_status"
        ),
        "p026_source_sha256": intake_by_id["P026"]["sha256"],
        "p026_resolution_status": resolution_by_id.get("P026", {}).get(
            "resolution_status"
        ),
        "repository_export_policy": manifest.get("repository_export_policy"),
        "raw_srt_committed": False,
        "normalized_text_committed": False,
        "derived_metadata_committed": True,
        "schema_validation_status": schema_validation_status,
        "deterministic_rebuild_status": "PASS" if not any(
            "drift" in error for error in errors
        ) else "FAIL",
        "private_body_locator": builder.SRT_PRIVATE_LOGICAL_LOCATOR,
        "shard_count": shard_index.get("shard_count"),
        "shard_ranges": [],
        "max_shard_size": 0,
    }
    return report


def validate(
    manifest_path: Path,
    output_dir: Path,
    *,
    raw_source_dir: Path | None = None,
    batch_markdown_dir: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = builder.load_manifest(manifest_path)
    registry = _load_json(output_dir / builder.FILE_NAMES["registry"])
    content_units = _load_jsonl(output_dir / builder.FILE_NAMES["content"])
    reuse = _load_json(output_dir / builder.FILE_NAMES["reuse"])
    admission = _load_json(output_dir / builder.FILE_NAMES["admission"])
    sources = registry.get("sources", [])
    candidates = reuse.get("candidates", [])
    decisions = admission.get("decisions", [])

    expected_numbers = list(range(manifest["expected"][0], manifest["expected"][1] + 1))
    actual_numbers = [row.get("source_transcript_number") for row in sources]
    if actual_numbers != expected_numbers:
        errors.append("source transcript range is not exactly P004-P102")
    if len(sources) != 99:
        errors.append(f"registry source count must be 99, got {len(sources)}")
    if _duplicates([row.get("transcript_id", "") for row in sources]):
        errors.append("duplicate transcript_id")
    if any(row.get("read_status") != "complete" for row in sources):
        errors.append("all registry rows must be read_status=complete")
    if any(not row.get("source_sha256") or row.get("source_line_count", 0) <= 0 for row in sources):
        errors.append("all registry rows require source hash and positive line count")
    if any(row.get("canonical_promotion_allowed") is not False for row in sources):
        errors.append("non-authoritative source was marked canonical-promotable")

    source_ids = {row["transcript_id"] for row in sources}
    content_ids = {row["content_unit_id"] for row in content_units}
    if len(content_units) != 99 or {row.get("transcript_id") for row in content_units} != source_ids:
        errors.append("content units must cover all 99 sources exactly once")
    if _duplicates([row.get("content_unit_id", "") for row in content_units]):
        errors.append("duplicate content_unit_id")
    for row in content_units:
        span = row.get("source_span", {})
        source = next((item for item in sources if item["transcript_id"] == row.get("transcript_id")), None)
        if not source:
            errors.append(f"orphan content unit {row.get('content_unit_id')}")
            continue
        if span.get("start_line") != 1 or span.get("end_line") != source["source_line_count"]:
            errors.append(f"incomplete source span for {row['content_unit_id']}")
        if span.get("evidence_sha256") != source["source_sha256"]:
            errors.append(f"source evidence hash mismatch for {row['content_unit_id']}")
        batch = row.get("batch_evidence", {})
        if batch.get("section_sha256") != source["processing_batch_section_sha256"]:
            errors.append(f"batch evidence hash mismatch for {row['content_unit_id']}")

    if len(candidates) != 99:
        errors.append("reuse candidate count must be 99")
    if _duplicates([row.get("reuse_candidate_id", "") for row in candidates]):
        errors.append("duplicate reuse_candidate_id")
    for row in candidates:
        refs = row.get("source_content_unit_ids", [])
        if not refs or any(ref not in content_ids for ref in refs):
            errors.append(f"orphan reuse reference in {row.get('reuse_candidate_id')}")

    if _duplicates([row.get("admission_id", "") for row in decisions]):
        errors.append("duplicate admission_id")
    for row in decisions:
        if row.get("subject_type") == "content_unit" and row.get("subject_id") not in content_ids:
            errors.append(f"orphan admission subject {row.get('admission_id')}")
        if any(value in {"approved", "canonical_approved"} for key, value in row.get("decisions", {}).items() if "canonical" in key):
            errors.append(f"canonical approval found in {row.get('admission_id')}")
    if not any(row.get("subject_id") == "P093_FALSE_HOPE_WILL_CORRECTION" for row in decisions):
        errors.append("missing false hope+will correction decision")
    if not any(row.get("subject_id") == "P102_KET_ZHONGKAO_EQUIVALENCE" for row in decisions):
        errors.append("missing KET/zhongkao equivalence denial")

    raw_verified = 0
    if raw_source_dir:
        for source in sources:
            path = raw_source_dir / source["source_filename"]
            if not path.exists():
                errors.append(f"missing raw source: {source['source_filename']}")
                continue
            if _sha256(path) != source["source_sha256"]:
                errors.append(f"raw source hash mismatch: {source['transcript_id']}")
                continue
            raw_verified += 1
    else:
        warnings.append("raw source directory not supplied; using committed strict-validation evidence")

    batch_verified = 0
    if batch_markdown_dir:
        for source in sources:
            path = batch_markdown_dir / source["processing_batch_filename"]
            if not path.exists():
                errors.append(f"missing batch markdown: {source['processing_batch_filename']}")
                continue
            if _sha256(path) != source["processing_batch_sha256"]:
                errors.append(f"batch markdown hash mismatch: {source['processing_batch_id']}")
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            section = "\n".join(lines[source["batch_section_start_line"] - 1:source["batch_section_end_line"]])
            if hashlib.sha256(section.encode("utf-8")).hexdigest() != source["processing_batch_section_sha256"]:
                errors.append(f"batch section hash mismatch: {source['transcript_id']}")
                continue
            batch_verified += 1
    else:
        warnings.append("batch markdown directory not supplied; using committed strict-validation evidence")

    with tempfile.TemporaryDirectory() as temp:
        rebuilt = Path(temp)
        builder.build(manifest_path, rebuilt)
        for filename in builder.FILE_NAMES.values():
            if _sha256(rebuilt / filename) != _sha256(output_dir / filename):
                errors.append(f"deterministic rebuild drift: {filename}")

    report = {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
        "expected_source_count": 99,
        "registry_source_count": len(sources),
        "unique_source_count": len(source_ids),
        "content_unit_count": len(content_units),
        "reuse_candidate_count": len(candidates),
        "admission_decision_count": len(decisions),
        "raw_hash_verified_count": raw_verified,
        "raw_hash_evidence_count": len(sources),
        "raw_hash_verification_mode": "direct" if raw_source_dir else "committed_evidence",
        "batch_hash_verified_count": batch_verified,
        "batch_hash_evidence_count": len(sources),
        "batch_hash_verification_mode": "direct" if batch_markdown_dir else "committed_evidence",
        "orphan_content_units": sum(1 for row in content_units if row.get("transcript_id") not in source_ids),
        "orphan_reuse_references": sum(1 for row in candidates for ref in row.get("source_content_unit_ids", []) if ref not in content_ids),
        "all_99_sources_accounted_for": len(sources) == 99 and len(source_ids) == 99,
        "all_references_resolvable": not any("orphan" in error for error in errors),
        "canonical_promotion_from_non_authoritative_source": 0 if not any("canonical approval" in error for error in errors) else 1,
        "output_hashes": {filename: _sha256(output_dir / filename) for filename in builder.FILE_NAMES.values()},
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--raw-source-dir", type=Path)
    parser.add_argument("--batch-markdown-dir", type=Path)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--raw-srt-source-root", type=Path)
    parser.add_argument("--private-output-dir", type=Path)
    parser.add_argument("--public-output-dir", type=Path)
    parser.add_argument("--semantic-seed", type=Path)
    parser.add_argument("--schema", type=Path)
    args = parser.parse_args()
    if args.raw_srt_source_root:
        required = (args.private_output_dir, args.public_output_dir, args.semantic_seed)
        if not all(required):
            parser.error(
                "--private-output-dir, --public-output-dir, and --semantic-seed "
                "are required with --raw-srt-source-root"
            )
        report = validate_srt_publication(
            args.raw_srt_source_root,
            args.private_output_dir,
            args.public_output_dir,
            args.semantic_seed,
            schema_path=args.schema,
        )
        report_path = (
            args.validation_report
            or args.public_output_dir / SRT_REPORT_NAME
        )
    else:
        if not args.manifest or not args.output_dir:
            parser.error("--manifest and --output-dir are required for legacy validation")
        report = validate(
            args.manifest,
            args.output_dir,
            raw_source_dir=args.raw_source_dir,
            batch_markdown_dir=args.batch_markdown_dir,
        )
        report_path = args.validation_report or args.output_dir / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    builder._atomic_write_text(
        report_path,
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
