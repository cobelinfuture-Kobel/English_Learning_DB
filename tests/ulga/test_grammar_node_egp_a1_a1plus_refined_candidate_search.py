import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BULK_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_bulk_authority_mapping.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_refined_candidate_search.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_a1_a1plus_refined_candidate_search.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_refined_candidate_search.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_refined_candidate_search_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_refined_candidate_search_builder_can_run():
    bulk = run_command([sys.executable, str(BULK_BUILDER)])
    assert bulk.returncode == 0, bulk.stdout + bulk.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_refined_candidate_search_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_refined_candidate_search_contract():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert report["task_id"] == "R7-M96A_A1A1PLUSBulkRefinedEGPCandidateSearch"
    assert summary["task_id"] == "R7-M96A_A1A1PLUSBulkRefinedEGPCandidateSearch"
    assert report["search_scope"] == "BULK_REFINED_QUERY_PREPARATION_ONLY"
    assert summary["canonical_grammar_write_allowed"] is False
    assert summary["next_short_step"] == "R7-M97A_A1A1PLUSBulkEGPRowCandidateResolver"
    assert summary["stop_reason"] == "NONE"


def test_refined_candidate_search_records_are_query_ready():
    report = load_json(REPORT_PATH)
    assert len(report["records"]) >= 5
    grammar_ids = {record["grammar_id"] for record in report["records"]}
    assert "GRAMMAR_BASIC_PREPOSITIONS_PLACE" in grammar_ids
    assert "GRAMMAR_BE_VERB_BASIC" in grammar_ids
    for record in report["records"]:
        assert record["search_status"] == "REFINED_SEARCH_QUERY_READY"
        assert record["query_seeds"]
        assert record["candidate_row_ids"] == []
        assert record["canonical_write_allowed"] is False
        assert record["operator_review_required"] is True


def test_refined_candidate_search_summary_matches_records():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["refined_search_target_count"] == len(report["records"])
    assert summary["query_ready_count"] == len(report["records"])
    assert summary["source_target_count"] >= summary["refined_search_target_count"]
