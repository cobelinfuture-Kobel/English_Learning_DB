import json
import os
import re
import sys
from collections import Counter, defaultdict

import pandas as pd


SOURCE_FILE = "English Vocabulary Profile Online.xlsx"
SOURCE_SHEET = "total(15696)"
REQUIRED_COLUMNS = [
    "Base Word",
    "Guideword",
    "Level",
    "Part of Speech",
    "Topic",
    "Details",
]
VALID_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
TYPE_KEYS = ["phrase", "phrasal verb", "multi_word_entry"]


def clean_value(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def normalize_chunk(value):
    text = clean_value(value) or ""
    return re.sub(r"\s+", " ", text).strip().lower()


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def source_path(base_dir):
    candidates = [
        os.path.join(base_dir, "chunk_profile", "source", SOURCE_FILE),
        os.path.join(base_dir, "vocabulary", "source", SOURCE_FILE),
        os.path.join(base_dir, SOURCE_FILE),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def fail_report(base_dir, reason, warnings=None, sheet_names=None):
    report_dir = os.path.join(base_dir, "chunk_profile", "reports")
    os.makedirs(report_dir, exist_ok=True)
    report = {
        "source_file": SOURCE_FILE,
        "source_sheet": SOURCE_SHEET,
        "total_rows": 0,
        "candidate_total": 0,
        "by_level": {},
        "by_type": {},
        "multi_word_non_phrase_total": 0,
        "duplicate_normalized_chunk_total": 0,
        "duplicate_examples": [],
        "missing_level_total": 0,
        "missing_type_total": 0,
        "missing_topic_total": 0,
        "warnings": warnings or [reason],
        "verdict": "FAIL",
    }
    if sheet_names is not None:
        report["available_sheets"] = sheet_names
    write_json(os.path.join(report_dir, "chunk_extract_report.json"), report)
    print(reason)
    if sheet_names is not None:
        print("Available sheets:")
        for name in sheet_names:
            print(f"- {name}")
    return 1


def build_outputs(df):
    records = []
    by_level = {level: [] for level in VALID_LEVELS}
    by_type = {type_key: [] for type_key in TYPE_KEYS}
    level_counts = Counter()
    type_counts = Counter()
    missing_level_total = 0
    missing_type_total = 0
    missing_topic_total = 0
    multi_word_non_phrase_total = 0

    for _, row in df.iterrows():
        chunk = clean_value(row.get("Base Word"))
        if not chunk:
            continue

        pos = clean_value(row.get("Part of Speech"))
        pos_norm = pos.lower() if pos else ""
        normalized = normalize_chunk(chunk)
        is_phrase_type = pos_norm in {"phrase", "phrasal verb"}
        is_multi_word_non_phrase = " " in normalized and not is_phrase_type

        if not is_phrase_type and not is_multi_word_non_phrase:
            continue

        level = clean_value(row.get("Level"))
        guideword = clean_value(row.get("Guideword"))
        topic = clean_value(row.get("Topic"))
        details = clean_value(row.get("Details"))
        chunk_type = pos_norm if is_phrase_type else "multi_word_entry"

        if not level:
            missing_level_total += 1
        if not pos:
            missing_type_total += 1
        if not topic:
            missing_topic_total += 1
        if is_multi_word_non_phrase:
            multi_word_non_phrase_total += 1

        record_id = f"EVP_CHUNK_{len(records) + 1:06d}"
        record = {
            "id": record_id,
            "chunk": chunk,
            "normalized_chunk": normalized,
            "level": level,
            "chunk_type": chunk_type,
            "guideword": guideword,
            "topic": topic,
            "details": details,
            "source": "EVP",
            "source_file": SOURCE_FILE,
            "source_sheet": SOURCE_SHEET,
        }
        if is_multi_word_non_phrase:
            record["original_part_of_speech"] = pos
        records.append(record)

        if level in by_level:
            by_level[level].append(record_id)
        else:
            by_level.setdefault(level or "", []).append(record_id)
        by_type.setdefault(chunk_type, []).append(record_id)
        level_counts[level or ""] += 1
        type_counts[chunk_type or ""] += 1

    normalized_counts = Counter(r["normalized_chunk"] for r in records)
    duplicate_names = sorted(name for name, count in normalized_counts.items() if count > 1)
    duplicate_examples = []
    records_by_normalized = defaultdict(list)
    for record in records:
        records_by_normalized[record["normalized_chunk"]].append(record)

    for name in duplicate_names[:20]:
        duplicate_examples.append(
            {
                "normalized_chunk": name,
                "count": normalized_counts[name],
                "ids": [r["id"] for r in records_by_normalized[name][:10]],
                "levels": sorted({r["level"] for r in records_by_normalized[name] if r["level"]}),
                "chunk_types": sorted({r["chunk_type"] for r in records_by_normalized[name] if r["chunk_type"]}),
            }
        )

    warnings = []
    if duplicate_names:
        warnings.append("duplicate normalized_chunk found")
    if missing_topic_total:
        warnings.append("missing topic found")
    if multi_word_non_phrase_total:
        warnings.append("multi_word_entry found from non phrase/phrasal verb POS")
    if missing_type_total:
        warnings.append("missing original Part of Speech found")
    if missing_level_total:
        warnings.append("missing level found")

    required_output_fields = {"id", "chunk", "level", "chunk_type", "source"}
    output_missing_required = [
        r["id"] for r in records if any(not r.get(field) for field in required_output_fields)
    ]
    invalid_levels = sorted({r["level"] for r in records if r.get("level") not in VALID_LEVELS})

    verdict = "PASS"
    if not records or output_missing_required or invalid_levels:
        verdict = "FAIL"
    elif warnings:
        verdict = "WARNING"

    report = {
        "source_file": SOURCE_FILE,
        "source_sheet": SOURCE_SHEET,
        "total_rows": int(len(df)),
        "candidate_total": len(records),
        "by_level": dict(sorted(level_counts.items())),
        "by_type": dict(sorted(type_counts.items())),
        "multi_word_non_phrase_total": multi_word_non_phrase_total,
        "duplicate_normalized_chunk_total": len(duplicate_names),
        "duplicate_examples": duplicate_examples,
        "missing_level_total": missing_level_total,
        "missing_type_total": missing_type_total,
        "missing_topic_total": missing_topic_total,
        "warnings": warnings,
        "verdict": verdict,
    }
    if output_missing_required:
        report["output_missing_required_ids"] = output_missing_required[:50]
    if invalid_levels:
        report["invalid_levels"] = invalid_levels

    return records, by_level, by_type, report


def main():
    base_dir = repo_root()
    chunk_dir = os.path.join(base_dir, "chunk_profile")
    source_dir = os.path.join(chunk_dir, "source")
    json_dir = os.path.join(chunk_dir, "json")
    report_dir = os.path.join(chunk_dir, "reports")

    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)

    excel_path = source_path(base_dir)
    if not os.path.exists(excel_path):
        return fail_report(base_dir, f"Source xlsx not found: {SOURCE_FILE}")

    try:
        xls = pd.ExcelFile(excel_path)
    except Exception as exc:
        return fail_report(base_dir, f"Failed to read source xlsx: {exc}")

    if SOURCE_SHEET not in xls.sheet_names:
        return fail_report(
            base_dir,
            f"Source sheet not found: {SOURCE_SHEET}",
            sheet_names=xls.sheet_names,
        )

    try:
        df = pd.read_excel(excel_path, sheet_name=SOURCE_SHEET)
    except Exception as exc:
        return fail_report(base_dir, f"Failed to read source sheet: {exc}")

    df.columns = [str(column).strip() for column in df.columns]
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        return fail_report(base_dir, f"Missing required columns: {missing_columns}")

    records, by_level, by_type, report = build_outputs(df)

    chunks_path = os.path.join(json_dir, "chunks.json")
    level_mapping_path = os.path.join(json_dir, "chunk_level_mapping.json")
    type_mapping_path = os.path.join(json_dir, "chunk_type_mapping.json")
    report_path = os.path.join(report_dir, "chunk_extract_report.json")

    write_json(chunks_path, records)
    write_json(level_mapping_path, by_level)
    write_json(type_mapping_path, by_type)
    write_json(report_path, report)

    for path in [chunks_path, level_mapping_path, type_mapping_path, report_path]:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)

    print(f"Extracted {len(records)} chunk candidates")
    print(f"Report verdict: {report['verdict']}")
    return 0 if report["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
