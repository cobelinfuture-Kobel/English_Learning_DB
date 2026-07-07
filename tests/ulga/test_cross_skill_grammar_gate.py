import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

ALIGNMENT_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_alignment.py"
COVERAGE_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_coverage_matrix.py"
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_cross_skill_grammar_gate_matrix.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_cross_skill_grammar_gate.py"
CROSS_SKILL_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "cross_skill_grammar_gate_matrix.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "cross_skill_grammar_gate_summary.json"

SKILLS = ["reading", "listening", "speaking", "writing"]
LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
GLOBAL_ROLES = ["focus", "recycle", "preview", "blocked", "maintenance", "not_applicable"]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run_after_coverage_builder():
    alignment_result = run_command([sys.executable, str(ALIGNMENT_BUILDER_PATH)])
    assert alignment_result.returncode == 0, alignment_result.stdout + alignment_result.stderr
    coverage_result = run_command([sys.executable, str(COVERAGE_BUILDER_PATH)])
    assert coverage_result.returncode == 0, coverage_result.stdout + coverage_result.stderr
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert CROSS_SKILL_MATRIX_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_matrix_contract_fields():
    matrix = load_json(CROSS_SKILL_MATRIX_PATH)
    assert matrix["task_id"] == "R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation"
    assert matrix["artifact_id"] == "cross_skill_grammar_gate_matrix"
    assert matrix["skills"] == SKILLS
    assert matrix["level_stages"] == LEVEL_STAGES
    assert matrix["global_roles"] == GLOBAL_ROLES


def test_scope_constraints_block_runtime_and_productive_preview_misuse():
    matrix = load_json(CROSS_SKILL_MATRIX_PATH)
    scope = matrix["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_productive_use_for_receptive_preview"] is True


def test_records_have_all_skill_scopes():
    matrix = load_json(CROSS_SKILL_MATRIX_PATH)
    for record in matrix["records"]:
        assert set(record["skill_scope"]) == set(SKILLS)
        if record["receptive_preview_only"]:
            assert record["skill_scope"]["speaking"]["role"] == "blocked"
            assert record["skill_scope"]["writing"]["role"] == "blocked"


def test_summary_counts_match_records():
    matrix = load_json(CROSS_SKILL_MATRIX_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["grammar_rule_count"] == len(matrix["records"])
    assert summary["cross_skill_gate_ready"] == bool(matrix["records"])
    assert summary["next_short_step"] == "R7-M39_GrammarQueryIndexAndLookupContractImplementation"
    assert summary["stop_reason"] == "NONE"
