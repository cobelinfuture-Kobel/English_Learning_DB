import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REFINED_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_refined_candidate_suggestions.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_refined_operator_review_batches.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_refined_operator_review_batches.py"
PACKET_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_operator_review_batches.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_operator_review_batches_summary.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run_after_refined_candidate_builder():
    refined_result = run_command([sys.executable, str(REFINED_BUILDER)])
    assert refined_result.returncode == 0, refined_result.stdout + refined_result.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert PACKET_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_packet_contract_and_safety_flags():
    packet = load_json(PACKET_PATH)
    summary = load_json(SUMMARY_PATH)
    assert packet["task_id"] == "R7-M58R_RefinedOperatorReviewBatchRefresh"
    assert summary["task_id"] == "R7-M58R_RefinedOperatorReviewBatchRefresh"
    scope = packet["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True


def test_items_are_review_only_and_use_refined_candidates():
    packet = load_json(PACKET_PATH)
    for batch in packet["batches"]:
        assert batch["batch_status"] == "OPERATOR_REVIEW_REQUIRED"
        assert batch["item_count"] == len(batch["items"])
        assert batch["item_count"] <= packet["batch_size"]
        for item in batch["items"]:
            assert item["operator_decision_required"] is True
            assert item["selected_egp_row_id"] is None
            assert item["operator_reason"] is None
            assert item["learner_state_write"] is False
            assert item["practicebank_generation"] is False
            assert isinstance(item["refined_candidate_suggestions"], list)


def test_summary_counts_match_packet():
    packet = load_json(PACKET_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["batch_count"] == len(packet["batches"])
    item_count = sum(batch["item_count"] for batch in packet["batches"])
    refined_count = sum(len(item["refined_candidate_suggestions"]) for batch in packet["batches"] for item in batch["items"])
    empty_count = sum(1 for batch in packet["batches"] for item in batch["items"] if not item["refined_candidate_suggestions"])
    assert summary["item_count"] == item_count
    assert summary["total_refined_candidate_count"] == refined_count
    assert summary["items_without_refined_candidates"] == empty_count
    assert summary["next_short_step"] == "R7-M59R_RefinedOperatorReviewBatchCIReadbackAndStop"
    assert summary["stop_reason"] == "NONE"
