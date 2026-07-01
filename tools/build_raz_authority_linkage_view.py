#!/usr/bin/env python3
"""Build a local RAZ authority-linkage view.

S3J contract:
- Read legacy normalized/enriched artifacts under raz_output_jsons/derived.
- Do not mutate raw or derived corpus files.
- Do not promote authority records.
- Emit local linkage-view artifacts under raz_output_jsons/linkage.
- Emit a sanitized aggregate summary under reports/raz.
- Do not write sentence/page text into the sanitized summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
SCHEMA_VERSION = "raz_authority_linkage_contract.v1"
OUTPUT_SUFFIX = "authority_linkage_view"
TEXT_KEYS = {"text", "title", "clean_text"}
REAL_AUTHORITY_TARGETS = [
    "SentenceAuthority",
    "ReadingAuthority",
    "DialogueAuthority",
    "WritingAuthority",
    "ExerciseAuthority",
    "AssessmentAuthority",
    "ContentQueryLayer",
    "LearningOpportunityBinding",
]
SENTENCE_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_s[0-9]{4}$")
PAGE_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_p[0-9]{4}$")
REUSE_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_r[0-9]{4}$")
BOOK_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)$")


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top_level_json_is_not_object")
    return value


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    value = payload.get("records")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def sha256_text(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def uid_parts(uid: str) -> Tuple[Optional[str], Optional[str]]:
    for pattern in (SENTENCE_UID_RE, PAGE_UID_RE, REUSE_UID_RE, BOOK_UID_RE):
        match = pattern.match(uid)
        if match:
            level, book_id = match.group(1), match.group(2)
            return level, book_id
    return None, None


def source_ref_value(source_ref: Any, key: str) -> Optional[str]:
    if isinstance(source_ref, dict):
        value = source_ref.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def input_file(level_dir: Path, level: str, artifact_type: str) -> Path:
    return level_dir / f"raz_{level}_{artifact_type}.json"


def load_level_payloads(derived_root: Path, level: str) -> Dict[str, Dict[str, Any]]:
    level_root = derived_root / f"Level_{level}"
    paths = {
        "normalized_books": input_file(level_root / "normalized", level, "normalized_books"),
        "normalized_sentences": input_file(level_root / "normalized", level, "normalized_sentences"),
        "normalized_page_units": input_file(level_root / "normalized", level, "normalized_page_units"),
        "normalized_reuse_units": input_file(level_root / "normalized", level, "normalized_reuse_units"),
        "enriched_books": input_file(level_root / "enriched", level, "enriched_books"),
        "enriched_sentences": input_file(level_root / "enriched", level, "enriched_sentences"),
        "enriched_units": input_file(level_root / "enriched", level, "enriched_units"),
    }
    payloads: Dict[str, Dict[str, Any]] = {}
    for key, path in paths.items():
        if path.exists():
            payloads[key] = read_json(path)
    return payloads


def index_by(records_value: Iterable[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for record in records_value:
        value = record.get(key)
        if isinstance(value, str) and value:
            result[value] = record
    return result


def artifact_layer(kind: str, record: Dict[str, Any]) -> str:
    if kind == "normalized_books" or kind == "enriched_books":
        return "raw_source_reference"
    if kind == "normalized_sentences":
        return "sentence_normalized"
    if kind == "enriched_sentences":
        return "sentence_enriched"
    if kind == "normalized_page_units":
        return "page_unit"
    if kind == "normalized_reuse_units":
        return "reuse_unit_candidate"
    if kind == "enriched_units":
        return "reuse_unit_candidate" if record.get("unit_type") == "reuse_unit" else "page_unit"
    return "bridge_candidate"


def record_uid(kind: str, record: Dict[str, Any]) -> Optional[str]:
    for key in ("sentence_uid", "page_unit_uid", "reuse_unit_uid", "unit_uid", "book_uid"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def review_status(record: Dict[str, Any]) -> str:
    value = record.get("review_status")
    if value in {"pending", "needs_review", "rejected", "passed", "failed", "needs_revision", "in_review", "not_required"}:
        return str(value)
    return "pending"


def authority_status(record: Dict[str, Any]) -> str:
    value = record.get("authority_status")
    if value in {"candidate_only", "raw_reference", "validated_candidate", "reviewed_candidate", "promoted_authority", "rejected", "deprecated"}:
        return str(value)
    if record.get("authority_linkage_status") in {"candidate_only", "not_evaluated"}:
        return "candidate_only"
    return "candidate_only"


def required_review(layer: str) -> str:
    if layer == "raw_source_reference":
        return "none"
    if layer in {"sentence_normalized", "sentence_enriched"}:
        return "sentence_validation"
    if layer == "page_unit":
        return "page_unit_review"
    if layer == "reuse_unit_candidate":
        return "human_review_required"
    if layer == "derived_dialogue_candidate":
        return "dialogue_rewrite_review"
    if layer == "writing_model_seed":
        return "writing_template_review"
    if layer == "exercise_seed":
        return "exercise_schema_review"
    if layer == "assessment_seed":
        return "assessment_contract_review"
    return "human_review_required"


def target_policy(layer: str) -> Tuple[List[str], List[str]]:
    if layer == "raw_source_reference":
        return ["None"], REAL_AUTHORITY_TARGETS
    if layer in {"sentence_normalized", "sentence_enriched"}:
        allowed = ["SentenceAuthority", "ContentQueryLayer"]
        blocked = [item for item in REAL_AUTHORITY_TARGETS if item not in allowed]
        return allowed, blocked
    if layer == "page_unit":
        allowed = ["ReadingAuthority", "ContentQueryLayer"]
        blocked = ["DialogueAuthority", "WritingAuthority", "AssessmentAuthority", "LearningOpportunityBinding"]
        return allowed, blocked
    if layer == "reuse_unit_candidate":
        allowed = ["ContentQueryLayer"]
        blocked = [item for item in REAL_AUTHORITY_TARGETS if item not in allowed]
        return allowed, blocked
    return ["ContentQueryLayer"], [item for item in REAL_AUTHORITY_TARGETS if item != "ContentQueryLayer"]


def trace_confidence(record: Dict[str, Any], layer: str) -> str:
    source_ref = record.get("source_ref")
    has_source_ref = isinstance(source_ref, dict)
    if layer == "raw_source_reference":
        return "high" if has_source_ref else "medium"
    if layer in {"sentence_normalized", "page_unit", "reuse_unit_candidate"}:
        return "high" if has_source_ref else "medium"
    return "medium"


def sentence_ids(record: Dict[str, Any], uid: str, layer: str) -> List[str]:
    if layer in {"sentence_normalized", "sentence_enriched"} and SENTENCE_UID_RE.match(uid):
        return [uid]
    value = record.get("sentence_uids")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def source_trace(record: Dict[str, Any], uid: str, layer: str, norm_by_uid: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    level, book_id = uid_parts(uid)
    source_ref = record.get("source_ref")
    page_number = record.get("page_number") if isinstance(record.get("page_number"), int) else None
    if layer == "sentence_enriched":
        norm = norm_by_uid.get(uid)
        if norm:
            source_ref = norm.get("source_ref")
            page_number = norm.get("page_number") if isinstance(norm.get("page_number"), int) else page_number
            if level is None:
                level = norm.get("level") if isinstance(norm.get("level"), str) else None
            if book_id is None:
                book_id = str(norm.get("book_id")) if norm.get("book_id") is not None else None
    if level is None:
        value = record.get("level")
        level = value if isinstance(value, str) else "A"
    if book_id is None:
        value = record.get("book_id")
        book_id = str(value) if value is not None else "0"
    book_uid = record.get("book_uid") if isinstance(record.get("book_uid"), str) else f"raz_{level}_{book_id}"
    page_unit_id = uid if layer == "page_unit" and PAGE_UID_RE.match(uid) else None
    reuse_unit_id = uid if layer == "reuse_unit_candidate" and REUSE_UID_RE.match(uid) else None
    return {
        "source_type": "raz",
        "source_level": level,
        "source_book_id": book_id,
        "source_book_uid": book_uid,
        "source_page_number": page_number,
        "source_page_unit_id": page_unit_id,
        "source_passage_unit_id": None,
        "source_sentence_candidate_ids": sentence_ids(record, uid, layer),
        "source_sentence_final_ids": [],
        "source_reuse_unit_id": reuse_unit_id,
        "raw_file_relative_path": source_ref_value(source_ref, "raw_file_relative_path"),
        "raw_candidate_ref": source_ref_value(source_ref, "raw_candidate_ref"),
        "raw_page_ref": source_ref_value(source_ref, "raw_page_ref"),
        "deterministic_index_ref": source_ref_value(source_ref, "deterministic_index_ref"),
        "derived_from_original_text": True,
        "generated_content": False,
        "generation_method": "none",
        "generation_prompt_id": None,
        "generation_task_id": None,
        "trace_confidence": trace_confidence(record, layer),
    }


def linkage_record(kind: str, record: Dict[str, Any], norm_by_uid: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    uid = record_uid(kind, record)
    if not uid:
        return None
    layer = artifact_layer(kind, record)
    allowed, blocked = target_policy(layer)
    content_hash = sha256_text(record.get("text"))
    clean_hash = content_hash
    if kind == "enriched_sentences" and not content_hash:
        norm = norm_by_uid.get(uid)
        if norm:
            content_hash = sha256_text(norm.get("text"))
            clean_hash = content_hash
    return {
        "record_uid": f"{uid}::authority_linkage_v1::{kind}",
        "artifact_layer": layer,
        "source_traceability": source_trace(record, uid, layer, norm_by_uid),
        "authority_status": authority_status(record),
        "promotion_status": "promotion_blocked",
        "review_status": review_status(record),
        "required_review_before_promotion": required_review(layer),
        "allowed_authority_targets": allowed,
        "blocked_authority_targets": blocked,
        "generated_content": False,
        "derived_from_original_text": True,
        "trace_confidence": trace_confidence(record, layer),
        "content_hash": content_hash,
        "clean_text_hash": clean_hash,
        "contract_patch_notes": ["s3j_backfill_emitter", "legacy_artifact_read_only", "promotion_blocked_default"],
    }


def safe_summary_check(payload: Dict[str, Any]) -> None:
    def walk(value: Any, path: str = "$") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in TEXT_KEYS:
                    raise ValueError(f"unsafe_summary_key:{path}.{key}")
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")
    walk(payload)


def build(derived_root: Path, linkage_root: Path, reports_dir: Path) -> Dict[str, Any]:
    artifact_counts: Counter = Counter()
    level_counts: Dict[str, Dict[str, int]] = {}
    promotion_counts: Counter = Counter()
    authority_counts: Counter = Counter()
    review_counts: Counter = Counter()
    required_review_counts: Counter = Counter()
    allowed_counts: Counter = Counter()
    blocked_counts: Counter = Counter()
    trace_counts: Counter = Counter()
    warnings: List[str] = []
    blockers: List[str] = []
    files_read_count = 0
    records_emitted_count = 0

    if not derived_root.exists():
        blockers.append("derived_root_missing")
    for level in EXPECTED_LEVELS:
        level_payloads = load_level_payloads(derived_root, level) if not blockers else {}
        files_read_count += len(level_payloads)
        norm_sentence_index = index_by(records(level_payloads.get("normalized_sentences", {})), "sentence_uid")
        level_records: List[Dict[str, Any]] = []
        for kind, payload in level_payloads.items():
            for source_record in records(payload):
                result = linkage_record(kind, source_record, norm_sentence_index)
                if result is None:
                    continue
                level_records.append(result)
                artifact_counts[result["artifact_layer"]] += 1
                promotion_counts[result["promotion_status"]] += 1
                authority_counts[result["authority_status"]] += 1
                review_counts[result["review_status"]] += 1
                required_review_counts[result["required_review_before_promotion"]] += 1
                trace_counts[result["trace_confidence"]] += 1
                for target in result["allowed_authority_targets"]:
                    allowed_counts[target] += 1
                for target in result["blocked_authority_targets"]:
                    blocked_counts[target] += 1
        if level_records:
            output = {"schema_version": SCHEMA_VERSION, "records": level_records}
            write_json(linkage_root / f"Level_{level}" / f"raz_{level}_{OUTPUT_SUFFIX}.json", output)
            records_emitted_count += len(level_records)
            level_counts[level] = {"records_emitted": len(level_records)}
        else:
            warnings.append(f"no_records_emitted_for_level:{level}")

    status = "PASS" if not blockers else "BLOCKED"
    summary = {
        "task_id": "RAZ-AW-S3J_SourceTraceabilityBackfillEmitter_Implementation",
        "report_type": "raz_authority_linkage_backfill_emitter_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "derived_mutation": False,
        "authority_promotion": False,
        "input_derived_root": str(derived_root),
        "output_linkage_root": str(linkage_root),
        "levels_processed": [level for level in EXPECTED_LEVELS if level in level_counts],
        "files_read_count": files_read_count,
        "records_emitted_count": records_emitted_count,
        "artifact_layer_counts": dict(sorted(artifact_counts.items())),
        "promotion_status_counts": dict(sorted(promotion_counts.items())),
        "authority_status_counts": dict(sorted(authority_counts.items())),
        "review_status_counts": dict(sorted(review_counts.items())),
        "required_review_counts": dict(sorted(required_review_counts.items())),
        "allowed_target_counts": dict(sorted(allowed_counts.items())),
        "blocked_target_counts": dict(sorted(blocked_counts.items())),
        "trace_confidence_counts": dict(sorted(trace_counts.items())),
        "level_counts": level_counts,
        "warnings": warnings,
        "blockers": blockers,
    }
    safe_summary_check(summary)
    write_json(reports_dir / "raz_authority_linkage_backfill_emitter_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RAZ authority-linkage view files.")
    parser.add_argument("--derived-root", default="raz_output_jsons/derived")
    parser.add_argument("--linkage-root", default="raz_output_jsons/linkage")
    parser.add_argument("--reports-dir", default="reports/raz")
    args = parser.parse_args()
    summary = build(Path(args.derived_root).resolve(), Path(args.linkage_root).resolve(), Path(args.reports_dir).resolve())
    print(json.dumps({
        "status": summary["status"],
        "files_read_count": summary["files_read_count"],
        "records_emitted_count": summary["records_emitted_count"],
        "warnings": summary["warnings"],
        "blockers": summary["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
