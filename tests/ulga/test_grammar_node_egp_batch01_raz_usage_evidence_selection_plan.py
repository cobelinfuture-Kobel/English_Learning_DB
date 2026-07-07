import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_raz_usage_evidence_candidates.py"
FILTER_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.py"
SELECTION_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_raz_usage_evidence_selection_plan.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_raz_usage_evidence_selection_plan.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_selection_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_selection_plan_summary.json"
EXPECTED_IDS = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
}


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_selection_builder_can_run_after_dependencies():
    raw = run_command([sys.executable, str(RAW_BUILDER)])
    assert raw.returncode == 0, raw.stdout + raw.stderr
    filtered = run_command([sys.executable, str(FILTER_BUILDER)])
    assert filtered.returncode == 0, filtered.stdout + filtered.stderr
    result = run_command([sys.executable, str(SELECTION_BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert DATA_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_selection_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_selection_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M78A_Batch01RAZUsageEvidenceSelectionPlanArtifactBuilder"
    assert summary["task_id"] == "R7-M78A_Batch01RAZUsageEvidenceSelectionPlanArtifactBuilder"
    scope = data["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True
    assert scope["no_egp_evidence_refs_write"] is True
    assert scope["no_coverage_increase"] is True
    assert scope["no_final_usage_evidence_acceptance"] is True
    assert summary["operator_review_required"] is True
    assert summary["authority_write_allowed"] is False
    assert summary["evidence_refs_write_allowed"] is False
    assert summary["coverage_increase_allowed"] is False
    assert summary["final_acceptance_allowed"] is False


def test_selection_records_cover_batch01_targets():
    data = load_json(DATA_PATH)
    records = data["records"]
    assert {record["grammar_id"] for record in records} == EXPECTED_IDS
    for record in records:
        assert record["source_filtered_candidate_count"] >= record["selected_candidate_count"]
        assert record["selected_candidate_count"] == len(record["selected_candidates"])
        assert record["selection_status"] == "PROPOSED_SELECTION_REQUIRES_OPERATOR_REVIEW"
        assert record["selected_candidates"]
        for candidate in record["selected_candidates"]:
            assert candidate["source_type"] == "RAZ"
            assert candidate["quality_filter_status"] == "KEPT"
            assert candidate["selection_status"] == "PROPOSED_RAZ_USAGE_EVIDENCE"
            assert candidate["operator_review_required"] is True
            assert candidate["sentence_text"]


def test_selection_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    source_total = sum(record["source_filtered_candidate_count"] for record in records)
    selected_total = sum(record["selected_candidate_count"] for record in records)
    missing = sum(1 for record in records if not record["selected_candidates"])
    assert summary["source_filtered_candidate_count"] == source_total
    assert summary["selected_candidate_count"] == selected_total
    assert summary["unselected_candidate_count"] == source_total - selected_total
    assert summary["targets_without_selected_candidates"] == missing
    assert summary["next_short_step"] == "R7-M79A_Batch01RAZUsageEvidenceSelectionPlanReadback"
    assert summary["stop_reason"] == "NONE"


def test_can_ability_examples_are_selected():
    data = load_json(DATA_PATH)
    can_record = next(record for record in data["records"] if record["grammar_id"] == "GRAMMAR_CAN_STATEMENT")
    sentences = {candidate["sentence_text"] for candidate in can_record["selected_candidates"]}
    assert "I can run." in sentences
    assert "I can jump." in sentences
    assert "I can play." in sentences
    assert "We can make sounds." in sentences
