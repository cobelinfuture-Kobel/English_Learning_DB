import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_bulk_authority_mapping.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_a1_a1plus_bulk_authority_mapping.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_bulk_authority_mapping.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_bulk_authority_mapping_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_a1_a1plus_bulk_builder_can_run():
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_a1_a1plus_bulk_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_a1_a1plus_bulk_mapping_is_level_band_report_only():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert report["level_band"] == ["A1", "A1_PLUS"]
    assert summary["level_band"] == ["A1", "A1_PLUS"]
    assert report["mapping_scope"] == "REPORT_ONLY_NO_CANONICAL_WRITE"
    for value in report["scope_constraints"].values():
        assert value is False
    assert summary["canonical_grammar_write_allowed"] is False
    assert summary["coverage_increase_allowed"] is False


def test_a1_a1plus_bulk_mapping_covers_more_than_batch01():
    report = load_json(REPORT_PATH)
    grammar_ids = {record["grammar_id"] for record in report["records"]}
    assert len(grammar_ids) >= 10
    assert "GRAMMAR_ARTICLES_BASIC" in grammar_ids
    assert "GRAMMAR_BASIC_PREPOSITIONS_PLACE" in grammar_ids
    assert "GRAMMAR_BE_VERB_BASIC" in grammar_ids
    assert "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS" in grammar_ids
    assert "GRAMMAR_WH_QUESTIONS_BE_DO_BASIC" in grammar_ids


def test_a1_a1plus_bulk_classification_counts_match_records():
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    counts = {}
    for record in report["records"]:
        assert record["canonical_write_allowed"] is False
        counts[record["classification"]] = counts.get(record["classification"], 0) + 1
    assert summary["target_count"] == len(report["records"])
    assert summary["classification_counts"] == dict(sorted(counts.items()))
    assert summary["already_patched_count"] == counts.get("ALREADY_PATCHED", 0)
    assert summary["needs_refined_candidate_count"] == counts.get("NEEDS_REFINED_CANDIDATE", 0)
    assert summary["next_short_step"] == "R7-M96A_A1A1PLUSBulkRefinedEGPCandidateSearch"
    assert summary["stop_reason"] == "NONE"
