import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_egp_level_inventory.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_grammar_egp_level_inventory.py"
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


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def level_counts_from_source():
    rows = load_json(GRAMMAR_PROFILE_PATH)
    counts = Counter(str(row.get("level", "UNKNOWN")).strip().upper() or "UNKNOWN" for row in rows)
    return rows, counts


def test_builder_can_run():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert INVENTORY_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_inventory_and_summary_parse():
    inventory = load_json(INVENTORY_PATH)
    summary = load_json(SUMMARY_PATH)
    assert isinstance(inventory, dict)
    assert isinstance(summary, dict)


def test_inventory_contains_required_fields():
    inventory = load_json(INVENTORY_PATH)
    assert REQUIRED_INVENTORY_FIELDS <= set(inventory)


def test_summary_contains_required_fields():
    summary = load_json(SUMMARY_PATH)
    assert REQUIRED_SUMMARY_FIELDS <= set(summary)


def test_source_derived_counts_match_inventory_and_summary():
    rows, counts = level_counts_from_source()
    inventory = load_json(INVENTORY_PATH)
    summary = load_json(SUMMARY_PATH)

    expected_official = {level: counts.get(level, 0) for level in OFFICIAL_EGP_LEVELS}
    expected_target = {level: counts.get(level, 0) for level in TARGET_LEVELS}
    expected_target_total = sum(expected_target.values())

    assert inventory["total_egp_rows"] == len(rows)
    assert summary["total_egp_rows"] == len(rows)
    assert inventory["official_level_counts"] == expected_official
    assert summary["official_level_counts"] == expected_official
    assert inventory["r7_m35_target_level_counts"] == expected_target
    assert summary["a1_b2_counts"] == expected_target
    assert inventory["r7_m35_target_total_a1_b2"] == expected_target_total
    assert summary["r7_m35_target_total_a1_b2"] == expected_target_total


def test_internal_bridge_stages_are_not_counted_as_official_egp_levels():
    inventory = load_json(INVENTORY_PATH)
    assert inventory["official_egp_levels"] == OFFICIAL_EGP_LEVELS
    for bridge_stage in ["A1+", "A2+", "B1+"]:
        assert bridge_stage in inventory["internal_bridge_stages_not_counted_as_egp_levels"]
        assert bridge_stage not in inventory["official_level_counts"]


def test_scope_constraints_prevent_runtime_or_mapping_claims():
    inventory = load_json(INVENTORY_PATH)
    scope = inventory["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_grammar_node_mapping"] is True
    assert scope["no_coverage_claim"] is True


def test_rows_by_level_counts_match_level_counts():
    inventory = load_json(INVENTORY_PATH)
    rows_by_level = inventory["rows_by_level"]
    for level, expected_count in inventory["level_counts_including_unknown"].items():
        assert level in rows_by_level
        assert len(rows_by_level[level]) == expected_count


def test_next_short_step_points_to_r7_m36():
    summary = load_json(SUMMARY_PATH)
    assert summary["next_short_step"] == "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation"
    assert summary["stop_reason"] == "NONE"
