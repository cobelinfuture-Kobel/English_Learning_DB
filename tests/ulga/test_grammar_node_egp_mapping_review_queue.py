import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

ALIGNMENT_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_alignment.py"
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_mapping_review_queue.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_mapping_review_queue.py"
REVIEW_QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue_summary.json"


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
    assert REVIEW_QUEUE_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_review_queue_contract_and_safety_fields():
    queue = load_json(REVIEW_QUEUE_PATH)
    summary = load_json(SUMMARY_PATH)
    assert queue["task_id"] == "R7-M48_GrammarNodeEGPMappingReviewQueueBuilderImplementation"
    assert summary["task_id"] == "R7-M48_GrammarNodeEGPMappingReviewQueueBuilderImplementation"
    scope = queue["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_ai_mapping_promotion"] is True
    assert scope["no_new_evidence_selection"] is True


def test_review_queue_records_never_promote_candidates():
    queue = load_json(REVIEW_QUEUE_PATH)
    for record in queue["records"]:
        assert record["candidate_generation_allowed"] is True
        assert record["candidate_promotion_allowed"] is False
        assert record["learner_state_write"] is False
        assert record["practicebank_generation"] is False
        assert record["allowed_next_action"] in {
            "operator_select_egp_ref_or_mark_not_in_egp",
            "operator_resolve_existing_ref_conflict",
            "confirm_system_required_reason_or_defer",
        }


def test_summary_counts_match_records():
    queue = load_json(REVIEW_QUEUE_PATH)
    summary = load_json(SUMMARY_PATH)
    records = queue["records"]
    assert summary["review_queue_count"] == len(records)
    assert summary["candidate_generation_allowed"] is True
    assert summary["candidate_promotion_allowed"] is False
    assert summary["next_short_step"] == "R7-M49_GrammarNodeEGPCandidateSuggestionPolicyScan"
    assert summary["stop_reason"] == "NONE"
