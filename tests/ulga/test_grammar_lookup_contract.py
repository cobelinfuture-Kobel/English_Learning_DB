import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

ALIGNMENT_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_alignment.py"
COVERAGE_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_coverage_matrix.py"
CROSS_SKILL_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_cross_skill_grammar_gate_matrix.py"
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_query_index.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_grammar_lookup_contract.py"
QUERY_INDEX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_query_index.json"
LOOKUP_CONTRACT_PATH = BASE_DIR / "ulga" / "contracts" / "grammar_lookup_contract.json"
VALIDATION_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_lookup_contract_validation_report.json"

LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
SKILLS = ["reading", "listening", "speaking", "writing"]
REQUIRED_CAPABILITIES = {
    "lookup_by_level",
    "lookup_by_skill",
    "lookup_by_grammar_id",
    "lookup_by_egp_row_id",
    "lookup_uncovered_egp_rules",
    "lookup_blocked_grammar_by_stage_skill",
    "lookup_cross_skill_roles",
    "lookup_receptive_preview_vs_productive_mastery",
    "no_learner_state_write",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run_after_upstream_builders():
    for builder in [ALIGNMENT_BUILDER_PATH, COVERAGE_BUILDER_PATH, CROSS_SKILL_BUILDER_PATH]:
        result = run_command([sys.executable, str(builder)])
        assert result.returncode == 0, result.stdout + result.stderr
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert QUERY_INDEX_PATH.exists()
    assert LOOKUP_CONTRACT_PATH.exists()
    assert VALIDATION_REPORT_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_lookup_contract_capabilities():
    contract = load_json(LOOKUP_CONTRACT_PATH)
    assert contract["artifact_id"] == "grammar_lookup_contract"
    assert set(contract["capabilities"]) == REQUIRED_CAPABILITIES
    for capability in REQUIRED_CAPABILITIES:
        assert contract["capabilities"][capability] is True


def test_query_index_contains_level_and_skill_indexes():
    query_index = load_json(QUERY_INDEX_PATH)
    assert query_index["level_stages"] == LEVEL_STAGES
    assert query_index["skills"] == SKILLS
    for key in ["allowed_by_level_stage", "blocked_by_level_stage", "role_by_level_stage"]:
        assert set(query_index[key]) == set(LEVEL_STAGES)
    for key in ["allowed_by_level_stage_skill", "blocked_by_level_stage_skill", "role_by_level_stage_skill"]:
        assert set(query_index[key]) == set(LEVEL_STAGES)
        for stage in LEVEL_STAGES:
            assert set(query_index[key][stage]) == set(SKILLS)


def test_scope_constraints_make_contract_read_only_and_state_safe():
    query_index = load_json(QUERY_INDEX_PATH)
    contract = load_json(LOOKUP_CONTRACT_PATH)
    for payload in [query_index, contract]:
        scope = payload["scope_constraints"]
        assert scope["no_runtime_implementation"] is True
        assert scope["no_practicebank_generation"] is True
        assert scope["no_learner_state_write"] is True
        assert scope["read_only_contract_for_downstream_systems"] is True


def test_validation_report_counts_match_query_index():
    query_index = load_json(QUERY_INDEX_PATH)
    report = load_json(VALIDATION_REPORT_PATH)
    assert report["grammar_id_count"] == len(query_index["by_grammar_id"])
    assert report["egp_row_index_count"] == len(query_index["by_egp_row_id"])
    uncovered_count = sum(len(rows) for rows in query_index["uncovered_by_egp_level"].values())
    assert report["uncovered_egp_row_count"] == uncovered_count
    assert report["next_short_step"] == "R7-M40_GrammarEGPCoverageValidatorImplementation"
    assert report["stop_reason"] == "NONE"
