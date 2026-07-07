import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

ALIGNMENT_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_alignment.py"
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_coverage_matrix.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_grammar_coverage_matrix.py"
COVERAGE_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_coverage_matrix.json"
COVERAGE_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_cefr_egp_coverage_summary.json"
GAP_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_coverage_gap_report.json"

LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
ROLE_VALUES = ["focus", "recycle", "preview", "blocked", "maintenance", "not_applicable"]
TARGET_LEVELS = ["A1", "A2", "B1", "B2"]
ALLOWED_TASK_IDS = {
    "R7-M37_GrammarCoverageMatrixBuilderImplementation",
    "R7-M44A_SourcePathAndEvidenceRefNormalizationPatch",
}
ALLOWED_NEXT_STEPS = {
    "R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation",
    "R7-M45_GeneratedGrammarPipelineArtifactsRefresh",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run_after_alignment_builder():
    alignment_result = run_command([sys.executable, str(ALIGNMENT_BUILDER_PATH)])
    assert alignment_result.returncode == 0, alignment_result.stdout + alignment_result.stderr
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert COVERAGE_MATRIX_PATH.exists()
    assert COVERAGE_SUMMARY_PATH.exists()
    assert GAP_REPORT_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_matrix_contract_fields():
    matrix = load_json(COVERAGE_MATRIX_PATH)
    assert matrix["task_id"] in ALLOWED_TASK_IDS
    assert matrix["artifact_id"] == "grammar_coverage_matrix"
    assert matrix["level_stages"] == LEVEL_STAGES
    assert matrix["official_egp_levels"] == OFFICIAL_EGP_LEVELS
    assert matrix["role_values"] == ROLE_VALUES


def test_bridge_stages_are_internal_not_official_egp_levels():
    matrix = load_json(COVERAGE_MATRIX_PATH)
    for bridge_stage in ["A1+", "A2+", "B1+"]:
        assert matrix["bridge_stage_policy"][bridge_stage] == "internal_bridge_stage_not_official_egp_level"
        assert bridge_stage not in matrix["official_egp_levels"]


def test_scope_constraints_prevent_runtime_or_completion_claims():
    matrix = load_json(COVERAGE_MATRIX_PATH)
    scope = matrix["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_coverage_claim"] is True


def test_counts_are_internally_consistent():
    summary = load_json(COVERAGE_SUMMARY_PATH)
    gap_report = load_json(GAP_REPORT_PATH)
    for level in OFFICIAL_EGP_LEVELS:
        total = summary["egp_counts_by_level"][level]
        mapped = summary["mapped_counts_by_level"][level]
        uncovered = summary["uncovered_counts_by_level"][level]
        assert mapped + uncovered == total
        assert gap_report["uncovered_counts_by_level"][level] == uncovered
        expected_coverage = mapped / total if total else 0.0
        assert summary["coverage_by_level"][level] == expected_coverage

    target_total = sum(summary["egp_counts_by_level"][level] for level in TARGET_LEVELS)
    target_mapped = sum(summary["mapped_counts_by_level"][level] for level in TARGET_LEVELS)
    assert summary["target_a1_b2_total"] == target_total
    assert summary["target_a1_b2_mapped"] == target_mapped
    assert gap_report["target_a1_b2_uncovered_total"] == target_total - target_mapped


def test_next_short_step_is_allowed_refresh_or_downstream_step():
    summary = load_json(COVERAGE_SUMMARY_PATH)
    gap_report = load_json(GAP_REPORT_PATH)
    assert summary["next_short_step"] in ALLOWED_NEXT_STEPS
    assert gap_report["next_short_step"] in ALLOWED_NEXT_STEPS
    assert summary["stop_reason"] == "NONE"
    assert gap_report["stop_reason"] == "NONE"
