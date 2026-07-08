import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RESOLVER_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_candidate_resolver.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_deterministic_selection.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_a1_a1plus_deterministic_selection.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_deterministic_selection.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_deterministic_selection_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_deterministic_selection_builder_can_run():
    resolver = run_command([sys.executable, str(RESOLVER_BUILDER)])
    assert resolver.returncode == 0, resolver.stdout + resolver.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_deterministic_selection_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_deterministic_selection_summary_contract():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert report["task_id"] == "R7-M99B_A1A1PLUSDeterministicEGPSelection"
    assert summary["task_id"] == "R7-M99B_A1A1PLUSDeterministicEGPSelection"
    assert summary["source_target_count"] == len(report["records"])
    assert summary["selected_authority_target_count"] >= 1
    assert summary["selected_form_only_target_count"] >= 1
    assert summary["deferred_target_count"] >= 1
    assert summary["canonical_grammar_write_allowed"] is False
    assert summary["next_short_step"] == "R7-M99C_A1A1PLUSSelectionPatchPlanBuilder"
    assert summary["stop_reason"] == "NONE"


def test_deterministic_selection_records_are_safe():
    report = load_json(REPORT_PATH)
    decisions = {record["grammar_id"]: record["selection_decision"] for record in report["records"]}
    assert decisions["GRAMMAR_BASIC_PREPOSITIONS_PLACE"].startswith("DEFER")
    assert decisions["GRAMMAR_REGULAR_PLURAL_NOUNS"].startswith("DEFER")
    assert decisions["GRAMMAR_THIS_IS"].startswith("DEFER")
    assert decisions["GRAMMAR_BE_VERB_BASIC"] == "SELECT_FORM_ONLY_EVIDENCE"
    for record in report["records"]:
        assert record["canonical_write_allowed"] is False
        if record["selection_decision"].startswith("SELECT"):
            assert record["selected_egp_refs"]
        else:
            assert record["selected_egp_refs"] == []
