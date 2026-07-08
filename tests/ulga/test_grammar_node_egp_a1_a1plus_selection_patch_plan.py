import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SELECTION_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_deterministic_selection.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_selection_patch_plan.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_a1_a1plus_selection_patch_plan.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_selection_patch_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_selection_patch_plan_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_selection_patch_plan_builder_can_run():
    selection = run_command([sys.executable, str(SELECTION_BUILDER)])
    assert selection.returncode == 0, selection.stdout + selection.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_selection_patch_plan_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_selection_patch_plan_summary_contract():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert report["task_id"] == "R7-M99C_A1A1PLUSSelectionPatchPlanBuilder"
    assert summary["task_id"] == "R7-M99C_A1A1PLUSSelectionPatchPlanBuilder"
    assert summary["source_target_count"] == len(report["records"])
    assert summary["planned_patch_target_count"] >= 1
    assert summary["planned_defer_target_count"] >= 1
    assert summary["canonical_grammar_write_allowed"] is False
    assert summary["next_short_step"] == "R7-M99D_A1A1PLUSCanonicalPatchApplierBuilder"
    assert summary["stop_reason"] == "NONE"


def test_selection_patch_plan_records_are_safe():
    report = load_json(REPORT_PATH)
    for record in report["records"]:
        assert record["canonical_write_allowed"] is False
        if record["planned_action"] == "PLAN_DEFER_NO_CANONICAL_PATCH":
            assert record["target_field"] is None
            assert record["selected_egp_refs"] == []
            assert record["write_target_path"] is None
        else:
            assert record["selected_egp_refs"]
            assert record["write_target_path"] == "ulga/grammar/grammar_nodes.json"
