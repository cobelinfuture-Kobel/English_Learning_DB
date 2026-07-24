from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

TASK_ID = "KET_COMP_TRANSCRIPT_FINAL_CONSOLIDATION_V1"
SOURCE_ROLE = "third_party_teacher_delivery_reference"
AUTHORITY = "non_authoritative"
PARSER_VERSION = "ket_comp_transcript_parser_v1.1.0"
FILE_NAMES = {
    "registry": "transcript_source_registry.json",
    "content": "transcript_content_units.jsonl",
    "reuse": "transcript_reuse_candidates.json",
    "admission": "transcript_admission_decisions.json",
}

SRT_TASK_ID = "KET99-SRC-V1_FullP004P102OneShotNormalizationValidationAndPublication"
SRT_SCHEMA_VERSION = "ket99.srt.source_manifest.v1"
SRT_EXPECTED_NUMBERS = tuple(range(4, 103))
SRT_PUBLIC_FILE_NAMES = {
    "manifest": "final_source_manifest.json",
    "digest_mapping": "source_digest_mapping.json",
    "semantic": "normalized_transcript_semantic_artifact.jsonl",
    "evidence_resolution": "evidence_resolution_result.json",
    "shard_index": "deterministic_shard_index.json",
    "consumer_locator": "consumer_input_locator.json",
    "artifact_index": "artifact_index.json",
    "content": FILE_NAMES["content"],
}
SRT_PRIVATE_BODY_NAME = "normalized_transcripts.private.jsonl"
SRT_PRIVATE_LOGICAL_LOCATOR = "private://ket99/p004-p102/normalized-transcripts-v1"
SRT_TIMESTAMP_RE = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> "
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})$"
)
SRT_FILENAME_RE = re.compile(r"^\[P(\d{3})\](\d{3})\.")
SRT_REGULAR_RE = re.compile(r"-U(\d+)-P(\d+)")
SRT_REVIEW_RE = re.compile(r"-U(\d+)-(\d+)")
MAX_UNSHARDED_ARTIFACT_BYTES = 20 * 1024 * 1024


def _json_dump(value: Any, *, compact: bool = False) -> str:
    if compact:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _timestamp_ms(groups: tuple[str, ...] | list[str]) -> int:
    hours, minutes, seconds, milliseconds = (int(value) for value in groups)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def _format_timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _decode_srt(value: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5"):
        try:
            text = value.decode(encoding)
        except UnicodeDecodeError:
            continue
        if encoding == "utf-8-sig" and not value.startswith(b"\xef\xbb\xbf"):
            continue
        return text, encoding
    raise ValueError("encoding_unrecognized")


def _parse_filename(filename: str, transcript_number: int) -> tuple[str, int | None, str]:
    regular = SRT_REGULAR_RE.search(filename)
    if regular:
        return f"U{int(regular.group(1)):02d}", int(regular.group(2)), "regular"
    review = SRT_REVIEW_RE.search(filename)
    if review:
        return f"U{int(review.group(1)):02d}", int(review.group(2)), "review"
    if transcript_number == 102:
        return "COURSE", None, "grand_review"
    raise ValueError("filename_metadata_unparseable")


def _parse_srt(path: Path, transcript_number: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_bytes = path.read_bytes()
    text, encoding = _decode_srt(raw_bytes)
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip()) if text.strip() else []
    cues: list[dict[str, Any]] = []
    for block_number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].strip().isdigit():
            raise ValueError(f"cue_structure_invalid:{block_number}")
        cue_index = int(lines[0].strip())
        timestamp_match = SRT_TIMESTAMP_RE.fullmatch(lines[1].strip())
        if not timestamp_match:
            raise ValueError(f"timestamp_unparseable:{cue_index}")
        start_ms = _timestamp_ms(timestamp_match.groups()[:4])
        end_ms = _timestamp_ms(timestamp_match.groups()[4:])
        if start_ms >= end_ms:
            raise ValueError(f"timestamp_start_not_before_end:{cue_index}")
        normalized_text = re.sub(r"\s+", " ", "\n".join(lines[2:])).strip()
        cues.append(
            {
                "cue_index": cue_index,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": normalized_text,
            }
        )
    cue_indexes = [cue["cue_index"] for cue in cues]
    if cue_indexes != list(range(1, len(cues) + 1)):
        raise ValueError("cue_index_not_contiguous_from_one")
    if len(cue_indexes) != len(set(cue_indexes)):
        raise ValueError("duplicate_cue_index")
    if any(
        cues[index]["start_ms"] < cues[index - 1]["start_ms"]
        or cues[index]["end_ms"] < cues[index - 1]["end_ms"]
        for index in range(1, len(cues))
    ):
        raise ValueError("timeline_reverse")
    if not any(cue["text"] for cue in cues):
        raise ValueError("no_nonblank_cue")

    unit_id, textbook_page, lesson_type = _parse_filename(path.name, transcript_number)
    normalized_body = "\n".join(cue["text"] for cue in cues)
    first_ms = cues[0]["start_ms"]
    last_ms = cues[-1]["end_ms"]
    metadata = {
        "transcript_id": f"P{transcript_number:03d}",
        "original_filename": path.name,
        "unit_id": unit_id,
        "textbook_page": textbook_page,
        "lesson_type": lesson_type,
        "source_format": "srt",
        "encoding": encoding,
        "cue_count": len(cues),
        "first_timestamp": _format_timestamp(first_ms),
        "last_timestamp": _format_timestamp(last_ms),
        "duration": _format_timestamp(last_ms - first_ms),
        "duration_ms": last_ms - first_ms,
        "file_size": len(raw_bytes),
        "sha256": _sha256_bytes(raw_bytes),
        "normalized_text_sha256": _sha256_text(normalized_body),
        "raw_text_persistence": "private_only",
        "repository_export_allowed": False,
        "authority_status": AUTHORITY,
        "intake_status": "accepted",
        "derived_artifact_ids": [
            f"KET99_NORMALIZED_{transcript_number:03d}",
            f"KET99_SEMANTIC_{transcript_number:03d}",
        ],
    }
    return metadata, cues


def intake_srt_corpus(raw_source_dir: Path) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    if not raw_source_dir.is_dir():
        raise ValueError("raw_source_root_missing")
    candidates: list[tuple[int, Path]] = []
    for path in raw_source_dir.glob("*.srt"):
        match = SRT_FILENAME_RE.match(path.name)
        if not match:
            continue
        transcript_number = int(match.group(1))
        if transcript_number not in SRT_EXPECTED_NUMBERS:
            continue
        if int(match.group(2)) != transcript_number:
            raise ValueError(f"filename_prefix_mismatch:{path.name}")
        candidates.append((transcript_number, path))
    candidates.sort(key=lambda item: (item[0], item[1].name))
    numbers = [number for number, _ in candidates]
    if numbers != list(SRT_EXPECTED_NUMBERS):
        missing = sorted(set(SRT_EXPECTED_NUMBERS) - set(numbers))
        duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
        raise ValueError(f"source_identity_range_invalid:missing={missing}:duplicates={duplicates}")

    records = [_parse_srt(path, number) for number, path in candidates]
    digests: dict[str, list[str]] = {}
    filenames: dict[str, list[tuple[str, str]]] = {}
    for metadata, _ in records:
        digests.setdefault(metadata["sha256"], []).append(metadata["original_filename"])
        filenames.setdefault(metadata["original_filename"].casefold(), []).append(
            (metadata["original_filename"], metadata["sha256"])
        )
    duplicate_content = {digest: names for digest, names in digests.items() if len(names) > 1}
    if duplicate_content:
        raise ValueError(f"duplicate_content_sha256:{sorted(duplicate_content)}")
    same_name_different_content = {
        name: rows
        for name, rows in filenames.items()
        if len({digest for _, digest in rows}) > 1
    }
    if same_name_different_content:
        raise ValueError(f"same_filename_different_content:{sorted(same_name_different_content)}")
    return records


def _load_semantic_seed(path: Path) -> dict[str, dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {str(row["transcript_id"]): row for row in rows}
    expected = {f"P{number:03d}" for number in SRT_EXPECTED_NUMBERS}
    if set(by_id) != expected or len(rows) != len(expected):
        raise ValueError("semantic_seed_identity_range_invalid")
    return by_id


def _evidence_resolution(
    records: list[tuple[dict[str, Any], list[dict[str, Any]]]]
) -> dict[str, Any]:
    rules = {
        "P008": {
            "resolution_basis": "CONTROLLED_READING_STRATEGY_LEXICON",
            "semantic_atoms": ["reading_strategy", "keyword_location", "detail_location"],
            "required_terms": ["阅读", "关键词"],
        },
        "P026": {
            "resolution_basis": "CONTROLLED_DESCRIPTIVE_ADJECTIVE_AND_SHOPPING_LEXICON",
            "semantic_atoms": ["dirty", "clean", "expensive", "cheap", "light"],
            "required_terms": ["dirty", "clean", "expensive", "cheap", "light"],
        },
    }
    by_id = {metadata["transcript_id"]: (metadata, cues) for metadata, cues in records}
    results = []
    for transcript_id in ("P008", "P026"):
        metadata, cues = by_id[transcript_id]
        rule = rules[transcript_id]
        term_matches = {
            term: [cue for cue in cues if term.casefold() in cue["text"].casefold()]
            for term in rule["required_terms"]
        }
        matched_cues = {
            cue["cue_index"]: cue
            for matches in term_matches.values()
            for cue in matches
        }
        anchors = [
            {
                "cue_index": cue_index,
                "start_timestamp": _format_timestamp(cue["start_ms"]),
                "end_timestamp": _format_timestamp(cue["end_ms"]),
                "normalized_cue_sha256": _sha256_text(cue["text"]),
            }
            for cue_index, cue in sorted(matched_cues.items())
        ]
        resolved = all(term_matches.values())
        results.append(
            {
                "transcript_id": transcript_id,
                "source_sha256": metadata["sha256"],
                "resolution_status": "RESOLVED" if resolved else "UNRESOLVED",
                "resolution_basis": rule["resolution_basis"],
                "semantic_atoms": rule["semantic_atoms"],
                "required_term_match_counts": {
                    term: len(term_matches[term]) for term in rule["required_terms"]
                },
                "evidence_anchors": anchors,
                "raw_text_included": False,
            }
        )
    return {
        "task_id": SRT_TASK_ID,
        "schema_version": "ket99.srt.evidence_resolution.v1",
        "resolution_count": len(results),
        "resolved_count": sum(row["resolution_status"] == "RESOLVED" for row in results),
        "results": results,
    }


def build_from_srt(
    raw_source_dir: Path,
    private_output_dir: Path,
    public_output_dir: Path,
    semantic_seed_path: Path,
) -> dict[str, Any]:
    records = intake_srt_corpus(raw_source_dir)
    semantic_seed = _load_semantic_seed(semantic_seed_path)
    private_output_dir.mkdir(parents=True, exist_ok=True)
    public_output_dir.mkdir(parents=True, exist_ok=True)

    private_lines: list[str] = []
    semantic_lines: list[str] = []
    content_lines: list[str] = []
    manifest_sources: list[dict[str, Any]] = []
    digest_rows: list[dict[str, Any]] = []
    for metadata, cues in records:
        transcript_id = metadata["transcript_id"]
        private_lines.append(
            _json_dump(
                {
                    "artifact_id": f"KET99_NORMALIZED_{transcript_id[1:]}",
                    "transcript_id": transcript_id,
                    "source_sha256": metadata["sha256"],
                    "cues": cues,
                },
                compact=True,
            )
        )
        semantic_lines.append(
            _json_dump(
                {
                    "artifact_id": f"KET99_SEMANTIC_{transcript_id[1:]}",
                    "transcript_id": transcript_id,
                    "unit_id": metadata["unit_id"],
                    "textbook_page": metadata["textbook_page"],
                    "lesson_type": metadata["lesson_type"],
                    "cue_count": metadata["cue_count"],
                    "duration_ms": metadata["duration_ms"],
                    "source_sha256": metadata["sha256"],
                    "normalized_text_sha256": metadata["normalized_text_sha256"],
                    "nonblank_cue_count": sum(bool(cue["text"]) for cue in cues),
                    "unique_normalized_cue_count": len({cue["text"] for cue in cues if cue["text"]}),
                    "raw_text_included": False,
                    "authority_status": AUTHORITY,
                },
                compact=True,
            )
        )
        content = dict(semantic_seed[transcript_id])
        content["textbook_page"] = metadata["textbook_page"]
        content["unit_id"] = metadata["unit_id"]
        content["lesson_role"] = metadata["lesson_type"]
        content["source_span"] = {
            "start_cue_index": 1,
            "end_cue_index": metadata["cue_count"],
            "evidence_sha256": metadata["sha256"],
            "normalized_text_sha256": metadata["normalized_text_sha256"],
            "coverage_mode": "full_srt_read",
        }
        content.pop("batch_evidence", None)
        content_lines.append(_json_dump(content, compact=True))
        manifest_sources.append(
            {key: value for key, value in metadata.items() if key != "normalized_text_sha256"}
        )
        digest_rows.append(
            {
                "transcript_id": transcript_id,
                "source_sha256": metadata["sha256"],
                "normalized_text_sha256": metadata["normalized_text_sha256"],
                "semantic_artifact_id": f"KET99_SEMANTIC_{transcript_id[1:]}",
                "private_body_artifact_id": f"KET99_NORMALIZED_{transcript_id[1:]}",
            }
        )

    private_body_path = private_output_dir / SRT_PRIVATE_BODY_NAME
    _atomic_write_text(private_body_path, "".join(private_lines))
    if private_body_path.stat().st_size > MAX_UNSHARDED_ARTIFACT_BYTES:
        raise ValueError("private_body_exceeds_20_mib_sharding_required")

    manifest = {
        "task_id": SRT_TASK_ID,
        "schema_version": SRT_SCHEMA_VERSION,
        "source_range": ["P004", "P102"],
        "expected_source_count": 99,
        "source_count": len(manifest_sources),
        "raw_source_root_persisted": False,
        "raw_srt_committed": False,
        "repository_export_policy": "METADATA_DIGEST_SEMANTIC_EXTRACTION_ONLY",
        "private_body_locator": SRT_PRIVATE_LOGICAL_LOCATOR,
        "sources": manifest_sources,
    }
    digest_mapping = {
        "task_id": SRT_TASK_ID,
        "schema_version": "ket99.srt.source_digest_mapping.v1",
        "mapping_count": len(digest_rows),
        "mappings": digest_rows,
    }
    shard_index = {
        "task_id": SRT_TASK_ID,
        "schema_version": "ket99.srt.deterministic_shard_index.v1",
        "sharding_threshold_bytes": MAX_UNSHARDED_ARTIFACT_BYTES,
        "sharding_triggered": False,
        "shard_count": 0,
        "shards": [],
        "unsharded_private_body": {
            "transcript_start": "P004",
            "transcript_end": "P102",
            "transcript_count": 99,
            "byte_size": private_body_path.stat().st_size,
            "sha256": _sha256_bytes(private_body_path.read_bytes()),
            "schema_version": "ket99.srt.normalized_transcript.private.v1",
            "deterministic_order": "transcript_id_ascending_then_cue_index_ascending",
        },
    }
    consumer_locator = {
        "task_id": SRT_TASK_ID,
        "schema_version": "ket99.srt.consumer_input_locator.v1",
        "cp07b": {
            "content_units": "ulga/reports/ket_comp_transcript_final_consolidation/transcript_content_units.jsonl",
            "admission_decisions": "ulga/reports/ket_comp_transcript_final_consolidation/transcript_admission_decisions.json",
        },
        "r3g": {
            "upstream_consumer": "CP07B",
            "source_manifest": "ulga/reports/ket_comp_transcript_final_consolidation/final_source_manifest.json",
            "evidence_resolution": "ulga/reports/ket_comp_transcript_final_consolidation/evidence_resolution_result.json",
        },
        "private_body": SRT_PRIVATE_LOGICAL_LOCATOR,
    }
    public_texts = {
        SRT_PUBLIC_FILE_NAMES["manifest"]: _json_dump(manifest),
        SRT_PUBLIC_FILE_NAMES["digest_mapping"]: _json_dump(digest_mapping),
        SRT_PUBLIC_FILE_NAMES["semantic"]: "".join(semantic_lines),
        SRT_PUBLIC_FILE_NAMES["evidence_resolution"]: _json_dump(_evidence_resolution(records)),
        SRT_PUBLIC_FILE_NAMES["shard_index"]: _json_dump(shard_index),
        SRT_PUBLIC_FILE_NAMES["consumer_locator"]: _json_dump(consumer_locator),
        SRT_PUBLIC_FILE_NAMES["content"]: "".join(content_lines),
    }
    for filename, text in public_texts.items():
        _atomic_write_text(public_output_dir / filename, text)
    artifacts = [
        {
            "artifact_id": f"KET99_PUBLIC_{Path(filename).stem.upper()}",
            "path": filename,
            "byte_size": (public_output_dir / filename).stat().st_size,
            "sha256": _sha256_bytes((public_output_dir / filename).read_bytes()),
            "repository_export_allowed": True,
        }
        for filename in sorted(public_texts)
    ]
    artifact_index = {
        "task_id": SRT_TASK_ID,
        "schema_version": "ket99.srt.artifact_index.v1",
        "artifact_count": len(artifacts) + 1,
        "validation_result_locator": "final_validation_result.json",
        "artifacts": artifacts
        + [
            {
                "artifact_id": "KET99_PRIVATE_NORMALIZED_TRANSCRIPTS",
                "path": SRT_PRIVATE_LOGICAL_LOCATOR,
                "byte_size": private_body_path.stat().st_size,
                "sha256": _sha256_bytes(private_body_path.read_bytes()),
                "repository_export_allowed": False,
            }
        ],
    }
    _atomic_write_text(
        public_output_dir / SRT_PUBLIC_FILE_NAMES["artifact_index"],
        _json_dump(artifact_index),
    )
    return {
        "task_id": SRT_TASK_ID,
        "source_count": len(records),
        "total_cue_count": sum(metadata["cue_count"] for metadata, _ in records),
        "total_duration_ms": sum(metadata["duration_ms"] for metadata, _ in records),
        "regular_lesson_count": sum(metadata["lesson_type"] == "regular" for metadata, _ in records),
        "review_lesson_count": sum(metadata["lesson_type"] == "review" for metadata, _ in records),
        "grand_review_lesson_count": sum(metadata["lesson_type"] == "grand_review" for metadata, _ in records),
        "private_body_locator": SRT_PRIVATE_LOGICAL_LOCATOR,
        "private_body_path": str(private_body_path),
        "private_body_sha256": _sha256_bytes(private_body_path.read_bytes()),
        "public_output_hashes": {
            filename: _sha256_bytes((public_output_dir / filename).read_bytes())
            for filename in sorted(SRT_PUBLIC_FILE_NAMES.values())
        },
    }


def load_manifest(path: Path) -> dict[str, Any]:
    index = json.loads(path.read_text(encoding="utf-8"))
    if index.get("schema") != "ket.comp.source_manifest.index.v1":
        raise ValueError("unsupported source manifest index schema")
    base = path.parent
    batch_value = json.loads((base / index["batch_file"]).read_text(encoding="utf-8"))
    if batch_value.get("schema") != "ket.comp.batch_manifest.v1":
        raise ValueError("unsupported batch manifest schema")
    sources: list[list[Any]] = []
    for name in index["source_parts"]:
        part = json.loads((base / name).read_text(encoding="utf-8"))
        if part.get("schema") != "ket.comp.source_manifest.part.v1":
            raise ValueError(f"unsupported source manifest part: {name}")
        sources.extend(part["sources"])
    return {"schema": "ket.comp.source_manifest.v1", "expected": index["expected"], "batches": batch_value["batches"], "sources": sources}


def _source_record(row: list[Any]) -> dict[str, Any]:
    (
        number, filename, textbook_page, unit_id, lesson_role,
        size_bytes, character_count, line_count, source_sha256,
        batch_id, batch_filename, batch_sha256, section_sha256,
        section_start, section_end, title, content_roles, evidence_items, risk_flags,
    ) = row
    transcript_id = f"P{number:03d}"
    return {
        "transcript_id": transcript_id,
        "source_filename": filename,
        "source_transcript_number": number,
        "textbook_page": textbook_page,
        "unit_id": unit_id,
        "lesson_role": lesson_role,
        "source_role": SOURCE_ROLE,
        "authority_status": AUTHORITY,
        "canonical_promotion_allowed": False,
        "instructional_pattern_reuse_allowed": True,
        "read_status": "complete",
        "extraction_status": "content_extracted",
        "source_size_bytes": size_bytes,
        "source_character_count": character_count,
        "source_line_count": line_count,
        "source_sha256": source_sha256,
        "parser_version": PARSER_VERSION,
        "processing_batch_id": batch_id,
        "processing_batch_filename": batch_filename,
        "processing_batch_sha256": batch_sha256,
        "processing_batch_section_sha256": section_sha256,
        "batch_section_start_line": section_start,
        "batch_section_end_line": section_end,
        "content_unit_id": f"KET_COMP_CU_{transcript_id}_LESSON_BUNDLE",
        "reuse_candidate_id": f"KET_COMP_REUSE_{transcript_id}_DELIVERY_PATTERN",
        "admission_decision_id": f"KET_COMP_ADMISSION_{transcript_id}",
        "title": title,
        "content_roles": content_roles,
        "evidence_items": evidence_items,
        "risk_flags": risk_flags,
    }


def _target_systems(roles: list[str]) -> list[str]:
    mapping = {
        "grammar": "grammar_candidate_layer",
        "vocabulary": "vocabulary_candidate_layer",
        "reading": "ket_reading",
        "listening": "ket_listening",
        "speaking": "ket_speaking",
        "writing": "ket_writing",
        "pronunciation": "pronunciation_candidate_layer",
        "teacher_delivery": "teacher_delivery",
        "review": "review_mastery_layer",
        "error_taxonomy": "error_diagnosis",
        "remediation": "remediation",
    }
    targets = [mapping[x] for x in roles if x in mapping]
    return sorted(set(targets + ["lesson_planner", "teacher_delivery"]))


def build(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    sources = [_source_record(row) for row in manifest["sources"]]
    sources.sort(key=lambda row: row["source_transcript_number"])
    expected_start, expected_end = manifest["expected"]

    registry_sources = []
    content_units = []
    reuse_candidates = []
    admission_decisions = []
    for source in sources:
        registry_sources.append({key: value for key, value in source.items() if key not in {
            "title", "content_roles", "evidence_items", "risk_flags"
        }})
        transcript_id = source["transcript_id"]
        content_unit_id = source["content_unit_id"]
        content_units.append({
            "content_unit_id": content_unit_id,
            "transcript_id": transcript_id,
            "textbook_page": source["textbook_page"],
            "unit_id": source["unit_id"],
            "lesson_role": source["lesson_role"],
            "content_type": "lesson_content_bundle",
            "title": source["title"],
            "content_roles": source["content_roles"],
            "evidence_items": source["evidence_items"],
            "risk_flags": source["risk_flags"],
            "source_span": {
                "start_line": 1,
                "end_line": source["source_line_count"],
                "evidence_sha256": source["source_sha256"],
                "coverage_mode": "full_transcript_read",
            },
            "batch_evidence": {
                "batch_id": source["processing_batch_id"],
                "batch_filename": source["processing_batch_filename"],
                "start_line": source["batch_section_start_line"],
                "end_line": source["batch_section_end_line"],
                "section_sha256": source["processing_batch_section_sha256"],
            },
            "authority_status": AUTHORITY,
            "canonical_promotion_allowed": False,
        })
        target_systems = _target_systems(source["content_roles"])
        reuse_candidates.append({
            "reuse_candidate_id": source["reuse_candidate_id"],
            "source_content_unit_ids": [content_unit_id],
            "transcript_id": transcript_id,
            "candidate_type": "instructional_pattern_bundle",
            "content_roles": source["content_roles"],
            "target_systems": target_systems,
            "reuse_status": "approved_with_constraints",
            "constraints": [
                "non_authoritative_source",
                "canonical_promotion_forbidden",
                "audio_image_and_exam_claims_require_independent_verification",
            ] + (["risk_flags_present"] if source["risk_flags"] else []),
        })
        admission_decisions.append({
            "admission_id": source["admission_decision_id"],
            "subject_type": "content_unit",
            "subject_id": content_unit_id,
            "transcript_id": transcript_id,
            "decisions": {
                "teacher_delivery": "approved",
                "lesson_planner": "approved_with_constraints",
                "reuse_candidate_layer": "approved_with_constraints",
                "canonical_grammar_authority": "denied",
                "canonical_vocabulary_authority": "denied",
                "external_fact_layer": "denied_until_verified",
                "assessment_contract": "denied_until_verified",
                "human_pilot": "not_ready",
            },
            "requirements": [
                "retain_source_lineage",
                "map_language_items_to_canonical_authorities",
                "validate_audio_image_answer_keys_and_current_exam_format",
            ],
        })

    admission_decisions.extend([
        {
            "admission_id": "KET_COMP_ADMISSION_FALSE_CORRECTION_HOPE_WILL",
            "subject_type": "source_claim",
            "subject_id": "P093_FALSE_HOPE_WILL_CORRECTION",
            "transcript_id": "P093",
            "decisions": {"teacher_delivery": "rejected", "error_taxonomy": "approved", "canonical_grammar_authority": "denied"},
            "reason": "The source incorrectly labels 'I hope we will have...' as ungrammatical.",
        },
        {
            "admission_id": "KET_COMP_ADMISSION_KET_ZHONGKAO_EQUIVALENCE",
            "subject_type": "source_claim",
            "subject_id": "P102_KET_ZHONGKAO_EQUIVALENCE",
            "transcript_id": "P102",
            "decisions": {"reference_only": "approved", "exam_equivalence_layer": "denied", "canonical_knowledge": "denied"},
            "reason": "Different constructs, curricula, age groups and regional scoring prevent direct equivalence.",
        },
    ])

    registry = {
        "task_id": TASK_ID,
        "schema_version": "ket.comp.transcript_source_registry.v1",
        "expected_source_range": [expected_start, expected_end],
        "expected_source_count": expected_end - expected_start + 1,
        "source_count": len(registry_sources),
        "batch_count": len(manifest["batches"]),
        "batch_inventory": manifest["batches"],
        "sources": registry_sources,
        "claim_boundaries": {"source_role": SOURCE_ROLE, "authority_status": AUTHORITY, "canonical_promotion_allowed": False},
    }
    reuse = {
        "task_id": TASK_ID,
        "schema_version": "ket.comp.transcript_reuse_candidates.v1",
        "candidate_count": len(reuse_candidates),
        "candidates": reuse_candidates,
    }
    admission = {
        "task_id": TASK_ID,
        "schema_version": "ket.comp.transcript_admission_decisions.v1",
        "global_policy": {"source_role": SOURCE_ROLE, "canonical_promotion_allowed": False},
        "decision_count": len(admission_decisions),
        "decisions": admission_decisions,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        FILE_NAMES["registry"]: _json_dump(registry),
        FILE_NAMES["content"]: "".join(_json_dump(row, compact=True) for row in content_units),
        FILE_NAMES["reuse"]: _json_dump(reuse),
        FILE_NAMES["admission"]: _json_dump(admission),
    }
    hashes = {}
    for filename, text in outputs.items():
        (output_dir / filename).write_text(text, encoding="utf-8")
        hashes[filename] = _sha256_text(text)
    return {
        "task_id": TASK_ID,
        "source_count": len(sources),
        "content_unit_count": len(content_units),
        "reuse_candidate_count": len(reuse_candidates),
        "admission_decision_count": len(admission_decisions),
        "output_hashes": hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--raw-srt-source-root", type=Path)
    parser.add_argument("--private-output-dir", type=Path)
    parser.add_argument("--public-output-dir", type=Path)
    parser.add_argument("--semantic-seed", type=Path)
    args = parser.parse_args()
    if args.raw_srt_source_root:
        required = (args.private_output_dir, args.public_output_dir, args.semantic_seed)
        if not all(required):
            parser.error(
                "--private-output-dir, --public-output-dir, and --semantic-seed "
                "are required with --raw-srt-source-root"
            )
        result = build_from_srt(
            args.raw_srt_source_root,
            args.private_output_dir,
            args.public_output_dir,
            args.semantic_seed,
        )
    else:
        if not args.manifest or not args.output_dir:
            parser.error("--manifest and --output-dir are required for legacy manifest builds")
        result = build(args.manifest, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
