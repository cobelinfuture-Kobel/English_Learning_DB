import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDERS = [
    BASE_DIR / "ulga" / "builders" / "build_grammar_egp_level_inventory.py",
    BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_alignment.py",
    BASE_DIR / "ulga" / "builders" / "build_grammar_coverage_matrix.py",
    BASE_DIR / "ulga" / "builders" / "build_cross_skill_grammar_gate_matrix.py",
    BASE_DIR / "ulga" / "builders" / "build_grammar_query_index.py",
]
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_grammar_skill_tree_pipeline.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_skill_tree_validator_report.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_pipeline_validator_can_run_after_builders():
    for builder in BUILDERS:
        result = run_command([sys.executable, str(builder)])
        assert result.returncode == 0, result.stdout + result.stderr
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()


def test_pipeline_report_contract():
    report = load_json(REPORT_PATH)
    assert report["task_id"] == "R7-M40_GrammarEGPCoverageValidatorImplementation"
    assert report["artifact_id"] == "grammar_skill_tree_validator_report"
    assert report["overall_status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert isinstance(report["validator_results"], list)
    assert report["validator_results"]
    assert report["next_short_step"] == "R7-M41_GrammarGraphCoverageCloseoutQA"
    assert report["stop_reason"] == "NONE"


def test_all_child_validators_pass():
    report = load_json(REPORT_PATH)
    for result in report["validator_results"]:
        assert result["status"] == "PASS", result
        assert result["returncode"] == 0


def test_pipeline_scope_constraints():
    report = load_json(REPORT_PATH)
    scope = report["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_completion_claim"] is True
