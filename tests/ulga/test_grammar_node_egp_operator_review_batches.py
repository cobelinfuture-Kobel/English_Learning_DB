import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SUGGESTION_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_candidate_suggestions.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_operator_review_batches.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_operator_review_batches.py"
BATCHES_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_operator_review_batches.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_operator_review_batches_summary.json"
DECISIONS = ["ACCEPT_EGP_ROW", "REJECT_ALL_CANDIDATES", "MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED", "DEFER", "REQUEST_REFINED_CANDIDATES"]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run_after_suggestion_builder():
    suggestion_result = run_command([sys.executable, str(SUGGESTION_BUILDER)])
    assert suggestion_result.returncode == 0, suggestion_result.stdout + suggestion_result.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert BATCHES_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_batch_contract_and_safety_fields():
    batches = load_json(BATCHES_PATH)
    summary = load_json(SUMMARY_PATH)
    assert batches["task_id"] == "R7-M53_GrammarNodeEGPOperatorReviewBatchBuilderImplementation"
    assert summary["task_id"] == "R7-M53_GrammarNodeEGPOperatorReviewBatchBuilderImplementation"
    assert batches["allowed_decisions"] == DECISIONS
    scope = batches["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True


def test_items_require_operator_decision_and_have_no_selection_yet():
    batches = load_json(BATCHES_PATH)
    for batch in batches["batches"]:
        assert batch["batch_status"] == "OPERATOR_REVIEW_REQUIRED"
        assert batch["item_count"] == len(batch["items"])
        assert batch["item_count"] <= batches["batch_size"]
        for item in batch["items"]:
            assert item["allowed_decisions"] == DECISIONS
            assert item["operator_decision_required"] is True
            assert item["selected_egp_row_id"] is None
            assert item["operator_reason"] is None
            assert item["learner_state_write"] is False
            assert item["practicebank_generation"] is False


def test_summary_counts_match_batches():
    batches = load_json(BATCHES_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["batch_count"] == len(batches["batches"])
    total = sum(batch["item_count"] for batch in batches["batches"])
    assert summary["item_count"] == total
    assert summary["operator_review_required"] is True
    assert summary["next_short_step"] == "R7-M54_GrammarNodeEGPOperatorReviewBatchReadback"
    assert summary["stop_reason"] == "NONE"
