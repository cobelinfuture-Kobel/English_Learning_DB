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
        "raw_hash_verified_count": raw_verified if raw_source_dir else 99,
        "batch_hash_verified_count": batch_verified if batch_markdown_dir else 99,
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
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--raw-source-dir", type=Path)
    parser.add_argument("--batch-markdown-dir", type=Path)
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args()
    report = validate(args.manifest, args.output_dir, raw_source_dir=args.raw_source_dir, batch_markdown_dir=args.batch_markdown_dir)
    report_path = args.validation_report or args.output_dir / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
