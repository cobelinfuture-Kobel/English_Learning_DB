import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_raz_usage_evidence_candidates.py"
FILTER_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered_summary.json"
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


def test_filter_builder_can_run_after_raw_builder():
    raw = run_command([sys.executable, str(RAW_BUILDER)])
    assert raw.returncode == 0, raw.stdout + raw.stderr
    result = run_command([sys.executable, str(FILTER_BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert DATA_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_filter_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_filtered_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M75A_Batch01RAZUsageEvidenceQualityFilterImplementation"
    assert summary["task_id"] == "R7-M75A_Batch01RAZUsageEvidenceQualityFilterImplementation"
    scope = data["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True
    assert scope["no_egp_evidence_refs_write"] is True
    assert scope["no_coverage_increase"] is True
    assert summary["operator_review_required"] is True
    assert summary["authority_write_allowed"] is False
    assert summary["evidence_refs_write_allowed"] is False
    assert summary["coverage_increase_allowed"] is False


def test_filtered_records_cover_batch01_targets():
    data = load_json(DATA_PATH)
    records = data["records"]
    assert {record["grammar_id"] for record in records} == EXPECTED_IDS
    for record in records:
        assert record["raw_candidate_count"] >= record["filtered_candidate_count"]
        assert record["filtered_candidate_count"] == len(record["candidates"])
        for candidate in record["candidates"]:
            assert candidate["source_type"] == "RAZ"
            assert candidate["quality_filter_status"] == "KEPT"
            assert candidate["operator_review_required"] is True
            assert candidate["sentence_text"]


def test_filtered_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    raw_total = sum(record["raw_candidate_count"] for record in records)
    filtered_total = sum(record["filtered_candidate_count"] for record in records)
    missing = sum(1 for record in records if not record["candidates"])
    assert summary["raw_candidate_count"] == raw_total
    assert summary["filtered_candidate_count"] == filtered_total
    assert summary["removed_candidate_count"] == raw_total - filtered_total
    assert summary["targets_without_candidates"] == missing
    assert summary["next_short_step"] == "R7-M76A_Batch01RAZUsageEvidenceQualityFilterReadback"
    assert summary["stop_reason"] == "NONE"


def test_known_noisy_patterns_are_filtered():
    data = load_json(DATA_PATH)
    all_sentences = [candidate["sentence_text"].lower() for record in data["records"] for candidate in record["candidates"]]
    assert "i put on my shirt." not in all_sentences
    assert "how many bears in all?" not in all_sentences
    assert "you can go on a plane." not in all_sentences
