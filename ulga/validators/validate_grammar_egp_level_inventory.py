import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

GRAMMAR_PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
INVENTORY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_egp_level_inventory.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_egp_level_inventory_summary.json"

OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
TARGET_LEVELS = ["A1", "A2", "B1", "B2"]
REQUIRED_INVENTORY_FIELDS = {
    "task_id",
    "artifact_id",
    "source_path",
    "official_egp_levels",
    "internal_bridge_stages_not_counted_as_egp_levels",
    "total_egp_rows",
    "official_level_counts",
    "r7_m35_target_level_counts",
    "r7_m35_target_total_a1_b2",
    "level_counts_including_unknown",
    "super_category_counts",
    "sub_category_counts",
    "level_super_category_counts",
    "rows_by_level",
    "quality",
    "scope_constraints",
}
REQUIRED_SUMMARY_FIELDS = {
    "task_id",
    "artifact_id",
    "source_path",
    "validation_status",
    "total_egp_rows",
    "official_level_counts",
    "r7_m35_target_total_a1_b2",
    "a1_b2_counts",
    "unknown_level_count",
    "warning_row_count",
    "duplicate_id_count",
    "next_short_step",
    "stop_reason",
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def normalize_level(value):
    if value is None:
        return "UNKNOWN"
    return str(value).strip().upper() or "UNKNOWN"


def compute_level_counts(rows):
    return Counter(normalize_level(row.get("level")) for row in rows if isinstance(row, dict))


def validate_inventory_shape(inventory):
    if not isinstance(inventory, dict):
        return fail("inventory must be an object")
    missing = REQUIRED_INVENTORY_FIELDS - set(inventory)
    if missing:
        return fail(f"inventory missing fields: {sorted(missing)}")
    if inventory["task_id"] != "R7-M35_GrammarEGPLevelInventoryBuilderImplementation":
        return fail("inventory task_id mismatch")
    if inventory["artifact_id"] != "grammar_egp_level_inventory":
        return fail("inventory artifact_id mismatch")
    if inventory["official_egp_levels"] != OFFICIAL_EGP_LEVELS:
        return fail("official EGP levels mismatch")
    for bridge_stage in ["A1+", "A2+", "B1+"]:
        if bridge_stage not in inventory["internal_bridge_stages_not_counted_as_egp_levels"]:
            return fail(f"missing bridge stage policy for {bridge_stage}")
    scope = inventory["scope_constraints"]
    for key in [
        "no_runtime_implementation",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_grammar_node_mapping",
        "no_coverage_claim",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    return True


def validate_summary_shape(summary):
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    missing = REQUIRED_SUMMARY_FIELDS - set(summary)
    if missing:
        return fail(f"summary missing fields: {sorted(missing)}")
    if summary["task_id"] != "R7-M35_GrammarEGPLevelInventoryBuilderImplementation":
        return fail("summary task_id mismatch")
    if summary["artifact_id"] != "grammar_egp_level_inventory_summary":
        return fail("summary artifact_id mismatch")
    if summary["validation_status"] not in {"PASS", "PASS_WITH_WARNINGS"}:
        return fail("summary validation_status must be PASS or PASS_WITH_WARNINGS")
    if summary["next_short_step"] != "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation":
        return fail("summary next_short_step mismatch")
    if summary["stop_reason"] != "NONE":
        return fail("summary stop_reason must be NONE")
    return True


def validate_counts(rows, inventory, summary):
    if not isinstance(rows, list):
        return fail("grammar profile source must be a list")
    counts = compute_level_counts(rows)
    official_counts = {level: counts.get(level, 0) for level in OFFICIAL_EGP_LEVELS}
    target_counts = {level: counts.get(level, 0) for level in TARGET_LEVELS}
    target_total = sum(target_counts.values())

    if inventory["total_egp_rows"] != len(rows):
        return fail("inventory total_egp_rows does not match source")
    if summary["total_egp_rows"] != len(rows):
        return fail("summary total_egp_rows does not match source")
    if inventory["official_level_counts"] != official_counts:
        return fail("inventory official_level_counts do not match source")
    if summary["official_level_counts"] != official_counts:
        return fail("summary official_level_counts do not match source")
    if inventory["r7_m35_target_level_counts"] != target_counts:
        return fail("inventory target level counts do not match source")
    if summary["a1_b2_counts"] != target_counts:
        return fail("summary target level counts do not match source")
    if inventory["r7_m35_target_total_a1_b2"] != target_total:
        return fail("inventory target total does not match source")
    if summary["r7_m35_target_total_a1_b2"] != target_total:
        return fail("summary target total does not match source")
    if target_total <= 0:
        return fail("target total A1-B2 must be positive")
    return True


def validate_rows_by_level(inventory):
    rows_by_level = inventory["rows_by_level"]
    if not isinstance(rows_by_level, dict):
        return fail("rows_by_level must be an object")
    for level, expected_count in inventory["level_counts_including_unknown"].items():
        if level not in rows_by_level:
            return fail(f"rows_by_level missing level {level}")
        if len(rows_by_level[level]) != expected_count:
            return fail(f"rows_by_level count mismatch for {level}")
        for item in rows_by_level[level]:
            for key in ["egp_row_id", "level", "super_category", "sub_category", "guideword", "source_sheet", "source_row"]:
                if key not in item:
                    return fail(f"rows_by_level item missing {key} for level {level}")
    return True


def validate():
    print("Validating Grammar EGP Level Inventory...")
    for path in [GRAMMAR_PROFILE_PATH, INVENTORY_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    rows = read_json(GRAMMAR_PROFILE_PATH)
    inventory = read_json(INVENTORY_PATH)
    summary = read_json(SUMMARY_PATH)
    if rows is None or inventory is None or summary is None:
        return False
    if not validate_inventory_shape(inventory):
        return False
    if not validate_summary_shape(summary):
        return False
    if not validate_counts(rows, inventory, summary):
        return False
    if not validate_rows_by_level(inventory):
        return False

    print("Grammar EGP Level Inventory validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
