import hashlib
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


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def clean_value(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def normalize(value):
    return re.sub(r"\s+", " ", clean_value(value) or "").strip().lower()


def hash_payload(payload):
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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


def fail_report(base_dir, reason, sheet_names=None):
    report_dir = os.path.join(base_dir, "chunk_profile", "reports")
    os.makedirs(report_dir, exist_ok=True)
    report = {
        "source_file": SOURCE_FILE,
        "source_sheet": SOURCE_SHEET,
        "input_chunks_total": 0,
        "matched_total": 0,
        "ambiguous_match_total": 0,
        "unmatched_total": 0,
        "exact_duplicate_groups_input": 0,
        "reclassification_counts": {},
        "warnings": [reason],
        "verdict": "FAIL",
    }
    if sheet_names is not None:
        report["available_sheets"] = sheet_names
    write_json(os.path.join(report_dir, "chunk_duplicate_evidence_recovery_report.json"), report)
    print(reason)
    if sheet_names is not None:
        print("Available sheets:")
        for name in sheet_names:
            print(f"- {name}")
    return 1


def read_source_rows(excel_path):
    xls = pd.ExcelFile(excel_path)
    if SOURCE_SHEET not in xls.sheet_names:
        return None, xls.sheet_names

    df = pd.read_excel(excel_path, sheet_name=SOURCE_SHEET)
    df.columns = [str(column).strip() for column in df.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    rows = []
    for df_index, row in df.iterrows():
        raw_fields = {column: clean_value(row.get(column)) for column in df.columns}
        source_row = {
            "source_row_index": int(df_index + 2),
            "raw_base_word": raw_fields.get("Base Word"),
            "raw_guideword": raw_fields.get("Guideword"),
            "raw_level": raw_fields.get("Level"),
            "raw_part_of_speech": raw_fields.get("Part of Speech"),
            "raw_topic": raw_fields.get("Topic"),
            "raw_details": raw_fields.get("Details"),
            "raw_row_fields": raw_fields,
        }
        source_row["normalized_base_word"] = normalize(source_row["raw_base_word"])
        source_row["row_signature"] = hash_payload(raw_fields)
        source_row["sense_signature"] = hash_payload(
            {
                "base_word": source_row["normalized_base_word"],
                "guideword": normalize(source_row["raw_guideword"]),
                "level": source_row["raw_level"],
                "part_of_speech": normalize(source_row["raw_part_of_speech"]),
                "topic": normalize(source_row["raw_topic"]),
                "details": normalize(source_row["raw_details"]),
            }
        )
        rows.append(source_row)
    return rows, None


def source_row_is_chunk_candidate(row):
    pos = normalize(row["raw_part_of_speech"])
    base = normalize(row["raw_base_word"])
    return pos in {"phrase", "phrasal verb"} or (" " in base and pos not in {"phrase", "phrasal verb"})


def chunk_original_pos(chunk):
    if "original_part_of_speech" in chunk:
        return chunk.get("original_part_of_speech")
    return chunk.get("chunk_type")


def same_or_null(left, right):
    return left == right or left is None or right is None


def primary_match(chunk, row):
    return (
        chunk.get("chunk") == row["raw_base_word"]
        and chunk.get("level") == row["raw_level"]
        and chunk_original_pos(chunk) == row["raw_part_of_speech"]
        and chunk.get("guideword") == row["raw_guideword"]
        and chunk.get("topic") == row["raw_topic"]
    )


def fallback_pos_match(chunk, row):
    chunk_type = chunk.get("chunk_type")
    row_pos = normalize(row["raw_part_of_speech"])
    if chunk_type in {"phrase", "phrasal verb"}:
        return row_pos == chunk_type
    if chunk_type == "multi_word_entry":
        return row_pos not in {"phrase", "phrasal verb"}
    return False


def fallback_match(chunk, row):
    return (
        chunk.get("normalized_chunk") == row["normalized_base_word"]
        and chunk.get("level") == row["raw_level"]
        and fallback_pos_match(chunk, row)
        and same_or_null(chunk.get("guideword"), row["raw_guideword"])
        and same_or_null(chunk.get("topic"), row["raw_topic"])
    )


def choose_row(candidates, used_rows, expected_row_index):
    unused = [row for row in candidates if row["source_row_index"] not in used_rows]
    pool = unused or candidates
    return min(pool, key=lambda row: abs(row["source_row_index"] - expected_row_index))


def evidence_from_row(row, candidates, status):
    return {
        "evidence_status": status,
        "source_row_index": row["source_row_index"] if row else None,
        "matched_row_candidates": [candidate["source_row_index"] for candidate in candidates],
        "raw_base_word": row["raw_base_word"] if row else None,
        "raw_guideword": row["raw_guideword"] if row else None,
        "raw_level": row["raw_level"] if row else None,
        "raw_part_of_speech": row["raw_part_of_speech"] if row else None,
        "raw_topic": row["raw_topic"] if row else None,
        "raw_details": row["raw_details"] if row else None,
        "raw_row_fields": row["raw_row_fields"] if row else {},
        "row_signature": row["row_signature"] if row else None,
        "sense_signature": row["sense_signature"] if row else None,
    }


def match_chunks_to_source(chunks, source_rows):
    candidate_rows = [row for row in source_rows if source_row_is_chunk_candidate(row)]
    used_rows = set()
    chunks_with_evidence = []
    status_counts = Counter()

    for index, chunk in enumerate(chunks):
        primary_candidates = [row for row in candidate_rows if primary_match(chunk, row)]
        candidates = primary_candidates or [row for row in candidate_rows if fallback_match(chunk, row)]
        expected_row_index = (
            candidate_rows[index]["source_row_index"] if index < len(candidate_rows) else source_rows[-1]["source_row_index"]
        )

        if not candidates:
            chosen = None
            status = "unmatched"
        else:
            chosen = choose_row(candidates, used_rows, expected_row_index)
            used_rows.add(chosen["source_row_index"])
            status = "ambiguous_match" if len(candidates) > 1 else "matched"

        enriched = dict(chunk)
        enriched["source_evidence"] = evidence_from_row(chosen, candidates, status)
        chunks_with_evidence.append(enriched)
        status_counts[status] += 1

    return chunks_with_evidence, status_counts


def reclassify_groups(duplicate_groups, chunks_with_evidence):
    chunk_by_id = {chunk["id"]: chunk for chunk in chunks_with_evidence}
    reclassified_groups = []
    review_candidates = []
    counts = {
        "confirmed_exact_duplicate": 0,
        "evidence_recovered_sense_variant": 0,
        "evidence_incomplete_review": 0,
        "unchanged_non_exact_variant": 0,
    }

    for group in duplicate_groups:
        enriched_group = dict(group)
        group_chunks = [chunk_by_id[chunk_id] for chunk_id in group["ids"] if chunk_id in chunk_by_id]
        evidence_statuses = [chunk["source_evidence"]["evidence_status"] for chunk in group_chunks]
        sense_signatures = sorted(
            {
                chunk["source_evidence"]["sense_signature"]
                for chunk in group_chunks
                if chunk["source_evidence"]["sense_signature"]
            }
        )
        row_signatures = sorted(
            {
                chunk["source_evidence"]["row_signature"]
                for chunk in group_chunks
                if chunk["source_evidence"]["row_signature"]
            }
        )
        source_rows = [chunk["source_evidence"]["source_row_index"] for chunk in group_chunks]

        if group["classification"] != "exact_duplicate_candidate":
            recovered_classification = group["classification"]
            evidence_risk = group["risk"]
            counts["unchanged_non_exact_variant"] += 1
        elif len(group_chunks) != group["count"] or "unmatched" in evidence_statuses:
            recovered_classification = "evidence_incomplete_review"
            evidence_risk = "review"
            counts[recovered_classification] += 1
        elif len(sense_signatures) > 1:
            recovered_classification = "evidence_recovered_sense_variant"
            evidence_risk = "keep_all"
            counts[recovered_classification] += 1
        else:
            recovered_classification = "confirmed_exact_duplicate"
            evidence_risk = "review"
            counts[recovered_classification] += 1

        enriched_group.update(
            {
                "source_row_indexes": source_rows,
                "evidence_statuses": sorted(set(evidence_statuses)),
                "sense_signature_count": len(sense_signatures),
                "row_signature_count": len(row_signatures),
                "sense_signatures": sense_signatures,
                "recovered_classification": recovered_classification,
                "evidence_risk": evidence_risk,
            }
        )
        reclassified_groups.append(enriched_group)

        if recovered_classification in {"confirmed_exact_duplicate", "evidence_incomplete_review"}:
            review_candidates.append(enriched_group)

    return reclassified_groups, review_candidates, counts


def build_sense_signature_index(chunks_with_evidence):
    index = defaultdict(list)
    for chunk in chunks_with_evidence:
        signature = chunk["source_evidence"]["sense_signature"]
        if signature:
            index[signature].append(chunk["id"])
    return dict(sorted(index.items()))


def build_policy():
    return {
        "policy_name": "EVP Chunk Duplicate Evidence Recovery Policy",
        "version": "S1B",
        "source": "CHUNK_DB_S1B_DuplicateEvidenceRecovery_DesignScan",
        "rules": {
            "do_not_delete_duplicates": True,
            "do_not_modify_cefr": True,
            "source_evidence_is_additive": True,
            "unmatched_chunks_remain_in_output": True,
            "ambiguous_matches_keep_all_candidates": True,
            "confirmed_exact_duplicate_requires_manual_review": True,
            "evidence_recovered_sense_variant_keeps_all_entries": True,
        },
        "level_order": VALID_LEVELS,
    }


def main():
    base_dir = repo_root()
    json_dir = os.path.join(base_dir, "chunk_profile", "json")
    report_dir = os.path.join(base_dir, "chunk_profile", "reports")
    chunks_path = os.path.join(json_dir, "chunks.json")
    duplicate_groups_path = os.path.join(json_dir, "chunk_duplicate_groups.json")
    surface_index_path = os.path.join(json_dir, "chunk_surface_index.json")
    canonical_path = os.path.join(json_dir, "chunk_canonical_candidates.json")
    dedup_report_path = os.path.join(report_dir, "chunk_dedup_authority_report.json")

    for path in [chunks_path, duplicate_groups_path, surface_index_path, canonical_path, dedup_report_path]:
        if not os.path.exists(path):
            return fail_report(base_dir, f"Required input not found: {path}")

    excel_path = source_path(base_dir)
    if not os.path.exists(excel_path):
        return fail_report(base_dir, f"Source xlsx not found: {SOURCE_FILE}")

    try:
        source_rows, missing_sheets = read_source_rows(excel_path)
    except Exception as exc:
        return fail_report(base_dir, f"Failed to read source workbook: {exc}")
    if missing_sheets is not None:
        return fail_report(base_dir, f"Source sheet not found: {SOURCE_SHEET}", sheet_names=missing_sheets)

    chunks = read_json(chunks_path)
    duplicate_groups = read_json(duplicate_groups_path)
    chunks_with_evidence, status_counts = match_chunks_to_source(chunks, source_rows)
    reclassified_groups, review_candidates, reclassification_counts = reclassify_groups(
        duplicate_groups,
        chunks_with_evidence,
    )
    sense_index = build_sense_signature_index(chunks_with_evidence)
    policy = build_policy()

    exact_input = sum(1 for group in duplicate_groups if group["classification"] == "exact_duplicate_candidate")
    warnings = []
    if status_counts["unmatched"]:
        warnings.append("some chunks could not be matched to source rows")
    if status_counts["ambiguous_match"]:
        warnings.append("some chunks had multiple source row candidates")
    if reclassification_counts["confirmed_exact_duplicate"]:
        warnings.append("confirmed exact duplicate candidates require manual review")

    verdict = "PASS"
    if not chunks or len(chunks_with_evidence) != len(chunks) or status_counts["unmatched"] or not sense_index:
        verdict = "FAIL"
    elif warnings:
        verdict = "WARNING"

    report = {
        "source_file": SOURCE_FILE,
        "source_sheet": SOURCE_SHEET,
        "input_chunks_total": len(chunks),
        "source_rows_total": len(source_rows),
        "matched_total": status_counts["matched"],
        "ambiguous_match_total": status_counts["ambiguous_match"],
        "unmatched_total": status_counts["unmatched"],
        "exact_duplicate_groups_input": exact_input,
        "reclassification_counts": reclassification_counts,
        "confirmed_exact_duplicate_review_total": len(review_candidates),
        "sense_signature_total": len(sense_index),
        "top_reclassified_exact_candidates": review_candidates[:20],
        "warnings": warnings,
        "verdict": verdict,
    }

    outputs = {
        os.path.join(json_dir, "chunks_with_evidence.json"): chunks_with_evidence,
        os.path.join(json_dir, "chunk_duplicate_groups_reclassified.json"): reclassified_groups,
        os.path.join(json_dir, "chunk_exact_duplicate_review_candidates.json"): review_candidates,
        os.path.join(json_dir, "chunk_sense_signature_index.json"): sense_index,
        os.path.join(json_dir, "chunk_evidence_policy.json"): policy,
        os.path.join(report_dir, "chunk_duplicate_evidence_recovery_report.json"): report,
    }
    for path, payload in outputs.items():
        write_json(path, payload)
        read_json(path)

    print(f"Input chunks: {report['input_chunks_total']}")
    print(f"Matched: {report['matched_total']}")
    print(f"Ambiguous: {report['ambiguous_match_total']}")
    print(f"Unmatched: {report['unmatched_total']}")
    print(f"Report verdict: {report['verdict']}")
    return 0 if report["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
