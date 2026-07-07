import json
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

GRAMMAR_PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
INVENTORY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_egp_level_inventory.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_egp_level_inventory_summary.json"

OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
R7_M35_TARGET_LEVELS = ["A1", "A2", "B1", "B2"]
REQUIRED_SOURCE_FIELDS = {
    "id",
    "super_category",
    "sub_category",
    "level",
    "guideword",
    "can_do_statement",
    "example",
    "source_sheet",
    "source_row",
}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_level(value):
    if value is None:
        return "UNKNOWN"
    return str(value).strip().upper() or "UNKNOWN"


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def as_source_ref(row):
    return {
        "egp_row_id": normalize_text(row.get("id")),
        "level": normalize_level(row.get("level")),
        "super_category": normalize_text(row.get("super_category")),
        "sub_category": normalize_text(row.get("sub_category")),
        "guideword": normalize_text(row.get("guideword")),
        "source_sheet": normalize_text(row.get("source_sheet")),
        "source_row": row.get("source_row"),
    }


def detect_row_warnings(row):
    warnings = []
    missing = sorted(field for field in REQUIRED_SOURCE_FIELDS if field not in row)
    if missing:
        warnings.append({"warning": "missing_required_source_fields", "fields": missing})
    if not normalize_text(row.get("id")):
        warnings.append({"warning": "missing_egp_row_id"})
    if normalize_level(row.get("level")) not in OFFICIAL_EGP_LEVELS:
        warnings.append({"warning": "unknown_or_unsupported_level", "level": normalize_level(row.get("level"))})
    if not normalize_text(row.get("guideword")):
        warnings.append({"warning": "missing_guideword"})
    if not normalize_text(row.get("can_do_statement")):
        warnings.append({"warning": "missing_can_do_statement"})
    return warnings


def build_inventory(rows):
    if not isinstance(rows, list):
        raise TypeError("grammar profile must be a list of EGP rows")

    level_counts = Counter()
    super_category_counts = Counter()
    sub_category_counts = Counter()
    level_super_category_counts = defaultdict(Counter)
    rows_by_level = defaultdict(list)
    warning_rows = []
    seen_ids = set()
    duplicate_ids = []

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            warning_rows.append({
                "source_index": index,
                "egp_row_id": None,
                "warnings": [{"warning": "row_not_object"}],
            })
            continue

        row_id = normalize_text(row.get("id"))
        level = normalize_level(row.get("level"))
        super_category = normalize_text(row.get("super_category")) or "UNKNOWN"
        sub_category = normalize_text(row.get("sub_category")) or "UNKNOWN"

        level_counts[level] += 1
        super_category_counts[super_category] += 1
        sub_category_counts[sub_category] += 1
        level_super_category_counts[level][super_category] += 1
        rows_by_level[level].append(as_source_ref(row))

        if row_id:
            if row_id in seen_ids:
                duplicate_ids.append(row_id)
            seen_ids.add(row_id)

        warnings = detect_row_warnings(row)
        if warnings:
            warning_rows.append({
                "source_index": index,
                "egp_row_id": row_id or None,
                "level": level,
                "warnings": warnings,
            })

    official_level_counts = {level: level_counts.get(level, 0) for level in OFFICIAL_EGP_LEVELS}
    r7_m35_target_level_counts = {level: level_counts.get(level, 0) for level in R7_M35_TARGET_LEVELS}
    total_rows = len(rows)
    unknown_level_count = sum(
        count for level, count in level_counts.items() if level not in OFFICIAL_EGP_LEVELS
    )
    warning_status = "PASS_WITH_WARNINGS" if warning_rows or duplicate_ids or unknown_level_count else "PASS"

    inventory = {
        "task_id": "R7-M35_GrammarEGPLevelInventoryBuilderImplementation",
        "artifact_id": "grammar_egp_level_inventory",
        "source_path": "grammar_profile/json/grammar_profile.json",
        "official_egp_levels": OFFICIAL_EGP_LEVELS,
        "internal_bridge_stages_not_counted_as_egp_levels": ["A1+", "A2+", "B1+"],
        "total_egp_rows": total_rows,
        "official_level_counts": official_level_counts,
        "r7_m35_target_level_counts": r7_m35_target_level_counts,
        "r7_m35_target_total_a1_b2": sum(r7_m35_target_level_counts.values()),
        "level_counts_including_unknown": dict(sorted(level_counts.items())),
        "super_category_counts": dict(sorted(super_category_counts.items())),
        "sub_category_counts": dict(sorted(sub_category_counts.items())),
        "level_super_category_counts": {
            level: dict(sorted(counts.items()))
            for level, counts in sorted(level_super_category_counts.items())
        },
        "rows_by_level": {
            level: sorted(items, key=lambda item: (str(item.get("source_row")), item["egp_row_id"]))
            for level, items in sorted(rows_by_level.items())
        },
        "quality": {
            "validation_status": warning_status,
            "unknown_level_count": unknown_level_count,
            "warning_row_count": len(warning_rows),
            "duplicate_id_count": len(duplicate_ids),
            "duplicate_ids": sorted(set(duplicate_ids)),
            "warning_rows": warning_rows,
        },
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_grammar_node_mapping": True,
            "no_coverage_claim": True,
        },
    }

    summary = {
        "task_id": "R7-M35_GrammarEGPLevelInventoryBuilderImplementation",
        "artifact_id": "grammar_egp_level_inventory_summary",
        "source_path": "grammar_profile/json/grammar_profile.json",
        "validation_status": warning_status,
        "total_egp_rows": total_rows,
        "official_level_counts": official_level_counts,
        "r7_m35_target_total_a1_b2": inventory["r7_m35_target_total_a1_b2"],
        "a1_b2_counts": r7_m35_target_level_counts,
        "unknown_level_count": unknown_level_count,
        "warning_row_count": len(warning_rows),
        "duplicate_id_count": len(duplicate_ids),
        "next_short_step": "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation",
        "stop_reason": "NONE",
    }
    return inventory, summary


def main():
    rows = read_json(GRAMMAR_PROFILE_PATH)
    inventory, summary = build_inventory(rows)
    write_json(INVENTORY_PATH, inventory)
    write_json(SUMMARY_PATH, summary)
    print(f"Grammar EGP level inventory build: {summary['validation_status']}")
    print(f"Total EGP rows: {summary['total_egp_rows']}")
    print(f"A1-B2 target rows: {summary['r7_m35_target_total_a1_b2']}")
    for level in OFFICIAL_EGP_LEVELS:
        print(f"{level}: {summary['official_level_counts'].get(level, 0)}")


if __name__ == "__main__":
    main()
