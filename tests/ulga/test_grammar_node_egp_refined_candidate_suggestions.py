import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SUGGESTION_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_candidate_suggestions.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_refined_candidate_suggestions.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_refined_candidate_suggestions.py"
REFINED_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_candidate_suggestions_summary.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run_after_suggestion_builder():
    suggestion_result = run_command([sys.executable, str(SUGGESTION_BUILDER)])
    assert suggestion_result.returncode == 0, suggestion_result.stdout + suggestion_result.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REFINED_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_refined_contract_and_safety_fields():
    refined = load_json(REFINED_PATH)
    summary = load_json(SUMMARY_PATH)
    assert refined["task_id"] == "R7-M56R_GrammarNodeEGPRefinedCandidateBuilderImplementation"
    assert summary["task_id"] == "R7-M56R_GrammarNodeEGPRefinedCandidateBuilderImplementation"
    scope = refined["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True


def test_refined_records_are_review_only_and_limited():
    refined = load_json(REFINED_PATH)
    for record in refined["records"]:
        assert record["review_required"] is True
        assert record["learner_state_write"] is False
        assert record["practicebank_generation"] is False
        assert len(record["refined_candidate_suggestions"]) <= refined["max_refined_candidates_per_node"]
        for option in record["refined_candidate_suggestions"]:
            assert option["review_required"] is True
            assert option["candidate_score"] >= refined["minimum_candidate_score"]
            assert option["confidence_band"] in {"HIGH", "MEDIUM", "LOW"}


def test_summary_counts_match_records():
    refined = load_json(REFINED_PATH)
    summary = load_json(SUMMARY_PATH)
    records = refined["records"]
    assert summary["refined_record_count"] == len(records)
    total = sum(len(record["refined_candidate_suggestions"]) for record in records)
    assert summary["total_refined_candidate_count"] == total
    no_safe = sum(1 for record in records if not record["refined_candidate_suggestions"])
    assert summary["records_without_refined_candidates"] == no_safe
    assert summary["next_short_step"] == "R7-M57R_GrammarNodeEGPRefinedCandidateReadback"
    assert summary["stop_reason"] == "NONE"
