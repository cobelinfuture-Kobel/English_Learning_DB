import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
QUEUE_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_mapping_review_queue.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_candidate_suggestions.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_candidate_suggestions.py"
SUGGESTIONS_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions_summary.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run_after_review_queue_builder():
    queue_result = run_command([sys.executable, str(QUEUE_BUILDER)])
    assert queue_result.returncode == 0, queue_result.stdout + queue_result.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert SUGGESTIONS_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_suggestion_contract_and_safety_fields():
    suggestions = load_json(SUGGESTIONS_PATH)
    summary = load_json(SUMMARY_PATH)
    assert suggestions["task_id"] == "R7-M50_GrammarNodeEGPCandidateSuggestionBuilderImplementation"
    assert summary["task_id"] == "R7-M50_GrammarNodeEGPCandidateSuggestionBuilderImplementation"
    assert suggestions["scope_constraints"]["no_runtime_implementation"] is True
    assert suggestions["scope_constraints"]["no_practicebank_generation"] is True
    assert suggestions["scope_constraints"]["no_learner_state_write"] is True
    assert summary["next_short_step"] == "R7-M51_GrammarNodeEGPCandidateSuggestionReviewReadback"
    assert summary["stop_reason"] == "NONE"


def test_records_require_review_and_do_not_write_state():
    suggestions = load_json(SUGGESTIONS_PATH)
    for record in suggestions["records"]:
        assert record["review_required"] is True
        assert record["learner_state_write"] is False
        assert record["practicebank_generation"] is False
        for option in record["candidate_suggestions"]:
            assert option["review_required"] is True
            assert option["candidate_score"] >= 0


def test_summary_counts_match_records():
    suggestions = load_json(SUGGESTIONS_PATH)
    summary = load_json(SUMMARY_PATH)
    records = suggestions["records"]
    assert summary["suggestion_record_count"] == len(records)
    assert summary["review_queue_count"] == len(records)
    total = sum(len(record["candidate_suggestions"]) for record in records)
    assert summary["total_candidate_count"] == total
