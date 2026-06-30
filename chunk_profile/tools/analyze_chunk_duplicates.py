import json
import os
import sys
from collections import Counter, defaultdict


LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
CLASSIFICATION_ORDER = [
    "type_variant",
    "level_variant",
    "guideword_variant",
    "pos_variant",
    "topic_variant",
    "exact_duplicate_candidate",
]
POLICY_BY_CLASSIFICATION = {
    "level_variant": "surface_form_multi_level",
    "guideword_variant": "surface_form_multi_sense",
    "type_variant": "surface_form_multi_type",
    "pos_variant": "surface_form_multi_pos",
    "topic_variant": "surface_form_multi_topic",
    "exact_duplicate_candidate": "review_exact_duplicate",
}


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def ordered_unique(values):
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def sorted_values(values):
    non_null = sorted(v for v in values if v is not None)
    return non_null + ([None] if None in values else [])


def original_pos(record):
    if "original_part_of_speech" in record:
        return record.get("original_part_of_speech")
    return record.get("chunk_type")


def level_sort_key(level):
    try:
        return LEVEL_ORDER.index(level)
    except ValueError:
        return len(LEVEL_ORDER)


def group_flags(records):
    levels = {r.get("level") for r in records}
    chunk_types = {r.get("chunk_type") for r in records}
    guidewords = {r.get("guideword") for r in records}
    topics = {r.get("topic") for r in records}
    original_positions = {original_pos(r) for r in records}
    return {
        "has_level_variant": len(levels) > 1,
        "has_guideword_variant": len(guidewords) > 1,
        "has_type_variant": len(chunk_types) > 1,
        "has_pos_variant": len(original_positions) > 1,
        "has_topic_variant": len(topics) > 1,
    }


def classify(flags):
    if flags["has_type_variant"]:
        return "type_variant"
    if flags["has_level_variant"]:
        return "level_variant"
    if flags["has_guideword_variant"]:
        return "guideword_variant"
    if flags["has_pos_variant"]:
        return "pos_variant"
    if flags["has_topic_variant"]:
        return "topic_variant"
    return "exact_duplicate_candidate"


def canonical_notes(classification):
    notes = []
    if classification == "level_variant":
        notes.append("Multiple CEFR levels found; keep all senses.")
        notes.append("Generator must disambiguate by guideword/level.")
    elif classification == "guideword_variant":
        notes.append("Multiple guidewords found; keep all senses.")
        notes.append("Generator must disambiguate by guideword when available.")
    elif classification == "type_variant":
        notes.append("Multiple chunk types found; keep all entries.")
        notes.append("Generator must disambiguate by type and level.")
    elif classification == "pos_variant":
        notes.append("Multiple original parts of speech found; keep all entries.")
    elif classification == "topic_variant":
        notes.append("Multiple topics found; keep all entries.")
    elif classification == "exact_duplicate_candidate":
        notes.append("Exact duplicate candidate; requires manual review.")
    else:
        notes.append("Single surface entry.")
    return notes


def build_authority(chunks):
    id_counts = Counter(record.get("id") for record in chunks)
    duplicate_ids = sorted(chunk_id for chunk_id, count in id_counts.items() if count > 1)
    missing_normalized = [record.get("id") for record in chunks if not record.get("normalized_chunk")]

    surface_index = defaultdict(list)
    records_by_surface = defaultdict(list)
    for record in chunks:
        surface = record.get("normalized_chunk")
        if not surface:
            continue
        surface_index[surface].append(record["id"])
        records_by_surface[surface].append(record)

    surface_index = dict(sorted(surface_index.items()))

    duplicate_groups = []
    classification_counts = {name: 0 for name in CLASSIFICATION_ORDER}
    risk_counts = {"keep_all": 0, "review": 0}
    canonical_candidates = {}
    missing_original_pos_total = 0

    for surface, records in sorted(records_by_surface.items()):
        ids = [record["id"] for record in records]
        levels = sorted_values({record.get("level") for record in records})
        chunk_types = sorted_values({record.get("chunk_type") for record in records})
        original_positions = sorted_values({original_pos(record) for record in records})
        guidewords = sorted_values({record.get("guideword") for record in records})
        topics = sorted_values({record.get("topic") for record in records})
        lowest_level = min(
            [level for level in levels if level is not None],
            key=level_sort_key,
            default=None,
        )

        missing_original_pos_total += sum(1 for record in records if original_pos(record) is None)

        if len(records) == 1:
            canonical_candidates[surface] = {
                "canonical_policy": "single_entry",
                "recommended_ids": ids,
                "lowest_level": lowest_level,
                "levels": levels,
                "sense_count": 1,
                "notes": canonical_notes("single_entry"),
            }
            continue

        flags = group_flags(records)
        classification = classify(flags)
        risk = "review" if classification == "exact_duplicate_candidate" else "keep_all"
        classification_counts[classification] += 1
        risk_counts[risk] += 1

        duplicate_groups.append(
            {
                "normalized_chunk": surface,
                "count": len(records),
                "ids": ids,
                "levels": levels,
                "chunk_types": chunk_types,
                "original_pos": original_positions,
                "guidewords": guidewords,
                "topics": topics,
                "classification": classification,
                "risk": risk,
                "flags": flags,
            }
        )

        canonical_candidates[surface] = {
            "canonical_policy": POLICY_BY_CLASSIFICATION[classification],
            "recommended_ids": ids,
            "lowest_level": lowest_level,
            "levels": levels,
            "sense_count": len(records),
            "notes": canonical_notes(classification),
        }

    duplicate_groups.sort(key=lambda group: (-group["count"], group["normalized_chunk"]))
    duplicate_entry_total = sum(group["count"] - 1 for group in duplicate_groups)
    a1_a2_duplicate_groups = [
        group for group in duplicate_groups if "A1" in group["levels"] or "A2" in group["levels"]
    ]

    warnings = []
    if classification_counts["exact_duplicate_candidate"] > 0:
        warnings.append("exact duplicate candidates require manual review")
    if missing_original_pos_total > 0:
        warnings.append("missing original_part_of_speech found")

    verdict = "PASS"
    if (
        not chunks
        or duplicate_ids
        or missing_normalized
        or sum(len(ids) for ids in surface_index.values()) != len(chunks)
        or len(canonical_candidates) != len(surface_index)
        or not duplicate_groups
        or duplicate_entry_total <= 0
    ):
        verdict = "FAIL"
    elif warnings:
        verdict = "WARNING"

    report = {
        "input_chunks_total": len(chunks),
        "surface_total": len(surface_index),
        "duplicate_surface_total": len(duplicate_groups),
        "duplicate_entry_total": duplicate_entry_total,
        "classification_counts": classification_counts,
        "risk_counts": risk_counts,
        "top_duplicate_groups": duplicate_groups[:20],
        "a1_a2_duplicate_groups": a1_a2_duplicate_groups,
        "a1_a2_duplicate_group_count": len(a1_a2_duplicate_groups),
        "missing_original_part_of_speech_total": missing_original_pos_total,
        "warnings": warnings,
        "verdict": verdict,
    }
    if duplicate_ids:
        report["duplicate_ids"] = duplicate_ids[:50]
    if missing_normalized:
        report["missing_normalized_chunk_ids"] = missing_normalized[:50]

    policy = {
        "policy_name": "EVP Chunk Dedup Authority Policy",
        "version": "S1",
        "source": "CHUNK_DB_S1_DedupAuthority_DesignScan",
        "rules": {
            "do_not_delete_duplicates": True,
            "surface_form_is_not_unique": True,
            "canonical_lookup_uses_normalized_chunk": True,
            "generator_must_filter_by_level": True,
            "generator_must_filter_by_guideword_when_available": True,
            "validator_must_accept_all_senses": True,
            "exact_duplicate_requires_manual_review": True,
        },
        "level_order": LEVEL_ORDER,
    }

    return surface_index, duplicate_groups, canonical_candidates, policy, report


def main():
    base_dir = repo_root()
    json_dir = os.path.join(base_dir, "chunk_profile", "json")
    report_dir = os.path.join(base_dir, "chunk_profile", "reports")
    chunks_path = os.path.join(json_dir, "chunks.json")

    if not os.path.exists(chunks_path):
        print(f"chunks.json not found: {chunks_path}")
        return 1

    try:
        chunks = read_json(chunks_path)
    except Exception as exc:
        print(f"Failed to read chunks.json: {exc}")
        return 1

    surface_index, duplicate_groups, canonical_candidates, policy, report = build_authority(chunks)

    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)

    outputs = {
        os.path.join(json_dir, "chunk_surface_index.json"): surface_index,
        os.path.join(json_dir, "chunk_duplicate_groups.json"): duplicate_groups,
        os.path.join(json_dir, "chunk_canonical_candidates.json"): canonical_candidates,
        os.path.join(json_dir, "chunk_dedup_policy.json"): policy,
        os.path.join(report_dir, "chunk_dedup_authority_report.json"): report,
    }
    for path, payload in outputs.items():
        write_json(path, payload)
        read_json(path)

    print(f"Input chunks: {report['input_chunks_total']}")
    print(f"Surfaces: {report['surface_total']}")
    print(f"Duplicate surfaces: {report['duplicate_surface_total']}")
    print(f"Report verdict: {report['verdict']}")
    return 0 if report["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
