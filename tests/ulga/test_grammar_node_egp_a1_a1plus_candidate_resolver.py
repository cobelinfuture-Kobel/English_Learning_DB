import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SEARCH_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_refined_candidate_search.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_candidate_resolver.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_a1_a1plus_candidate_resolver.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_candidate_resolver_builder_can_run():
    search = run_command([sys.executable, str(SEARCH_BUILDER)])
    assert search.returncode == 0, search.stdout + search.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_candidate_resolver_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_candidate_resolver_contract_is_report_only():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert report["task_id"] == "R7-M97C_A1A1PLUSBulkEGPRowCandidateResolverWithCompactIndex"
    assert summary["task_id"] == "R7-M97C_A1A1PLUSBulkEGPRowCandidateResolverWithCompactIndex"
    assert report["source_index_status"] in {"READY", "MISSING"}
    assert summary["canonical_grammar_write_allowed"] is False
    assert summary["operator_review_required"] is True
    for value in report["scope_constraints"].values():
        assert value is False


def test_candidate_resolver_records_match_summary():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    records = report["records"]
    assert records
    assert summary["source_refined_target_count"] == len(records)
    assert summary["resolved_target_count"] == sum(1 for r in records if r["candidate_count"] > 0)
    assert summary["total_candidate_count"] == sum(r["candidate_count"] for r in records)
    assert summary["next_short_step"] == "R7-M98A_A1A1PLUSBulkCandidateResolverReadback"
    assert summary["stop_reason"] == "NONE"


def test_candidate_resolver_keeps_operator_review_required():
    report = load_json(REPORT_PATH)
    for record in report["records"]:
        assert record["canonical_write_allowed"] is False
        assert record["operator_review_required"] is True
