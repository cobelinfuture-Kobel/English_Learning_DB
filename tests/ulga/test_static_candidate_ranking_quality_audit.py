import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_PATH = BASE_DIR / "ulga" / "audits" / "audit_static_candidate_ranking_quality.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_quality_audit.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def ensure_report():
    result = run_command([sys.executable, str(AUDIT_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()


def load_report():
    ensure_report()
    with REPORT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_quality_audit_report_exists():
    ensure_report()


def test_quality_audit_schema_contract():
    report = load_report()
    assert report["schema_version"] == "ULGA_S10D_STATIC_CANDIDATE_RANKING_QA_AUDIT_V1"
    assert report["source_ranking_file"] == "ulga/graph/static_candidate_ranking.json"
    assert report["source_summary_file"] == "ulga/reports/static_candidate_ranking_summary.json"


def test_quality_audit_is_read_only_mode():
    report = load_report()
    assert report["audit_mode"] == "read_only_quality_audit"


def test_quality_audit_adaptive_leakage_false():
    report = load_report()
    assert report["adaptive_leakage_detected"] is False


def test_quality_audit_contains_top_n_windows():
    report = load_report()
    assert set(report["top_n_quality"]) == {"top_10", "top_20", "top_50", "top_100", "top_500"}


def test_quality_audit_contains_a1_quality_section():
    report = load_report()
    assert "a1_quality" in report
    assert "a1_candidate_count" in report["a1_quality"]
    assert "a1_top_20" in report["a1_quality"]


def test_quality_audit_contains_score_component_diagnostics():
    report = load_report()
    expected = {
        "dependency_readiness_score",
        "frequency_score",
        "theme_spiral_score",
        "reinforcement_score",
        "authority_confidence_score",
    }
    assert expected.issubset(report["score_component_diagnostics"])


def test_quality_audit_contains_blocked_candidate_diagnostics():
    report = load_report()
    blocked = report["blocked_candidate_diagnostics"]
    assert "blocked_candidate_count" in blocked
    assert "block_reason_distribution" in blocked


def test_quality_audit_contains_recommendations():
    report = load_report()
    assert report["recommendations"]
    assert report["next_recommended_task"] == "ULGA-S10E_StaticCandidateRanking_BalancingContract_DesignScan"


def test_quality_audit_status_is_valid():
    report = load_report()
    assert report["status"] in {"PASS", "PASS_WITH_WARNINGS", "FAIL"}
