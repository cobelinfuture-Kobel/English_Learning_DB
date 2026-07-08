import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RESOLVER_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_candidate_resolver.py"
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_candidate_decision_buckets.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_a1_a1plus_candidate_decision_buckets.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_decision_buckets.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_decision_buckets_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_candidate_decision_bucket_builder_can_run():
    resolver = run_command([sys.executable, str(RESOLVER_BUILDER)])
    assert resolver.returncode == 0, resolver.stdout + resolver.stderr
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_candidate_decision_bucket_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_candidate_decision_bucket_contract():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert report["task_id"] == "R7-M99A_A1A1PLUSBulkCandidateDecisionBucketBuilder"
    assert summary["task_id"] == "R7-M99A_A1A1PLUSBulkCandidateDecisionBucketBuilder"
    assert report["decision_scope"] == "BULK_CANDIDATE_BUCKETS_NO_CANONICAL_WRITE"
    assert summary["auto_accept_count"] == 0
    assert summary["canonical_grammar_write_allowed"] is False
    assert summary["next_short_step"] == "R7-M100A_A1A1PLUSOperatorReviewPacketBuilder"
    assert summary["stop_reason"] == "NONE"


def test_candidate_decision_bucket_records_are_safe():
    report = load_json(REPORT_PATH)
    records = report["records"]
    assert records
    for record in records:
        assert record["auto_accept_allowed"] is False
        assert record["canonical_write_allowed"] is False
        assert record["decision_bucket"] in {"OPERATOR_REVIEW_REQUIRED", "REJECT_BROAD_ONLY", "NO_SAFE_CANDIDATE"}


def test_candidate_decision_bucket_summary_matches_records():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    counts = {}
    for record in report["records"]:
        counts[record["decision_bucket"]] = counts.get(record["decision_bucket"], 0) + 1
    assert summary["source_target_count"] == len(report["records"])
    assert summary["bucketed_target_count"] == len(report["records"])
    assert summary["bucket_counts"] == dict(sorted(counts.items()))
