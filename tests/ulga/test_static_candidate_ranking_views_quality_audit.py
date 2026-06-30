import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_PATH = BASE_DIR / "ulga" / "audits" / "audit_static_candidate_ranking_views_quality.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_views_quality_audit.json"


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


def test_views_quality_audit_report_exists():
    ensure_report()


def test_views_quality_audit_schema_contract():
    report = load_report()
    assert report["schema_version"] == "ULGA_S10G_STATIC_CANDIDATE_RANKING_VIEWS_QA_AUDIT_V1"
    assert report["source_views_file"] == "ulga/graph/static_candidate_ranking_views.json"
    assert report["source_summary_file"] == "ulga/reports/static_candidate_ranking_views_summary.json"


def test_views_quality_audit_is_read_only_mode():
    report = load_report()
    assert report["audit_mode"] == "read_only_view_quality_audit"


def test_views_quality_audit_adaptive_leakage_false():
    report = load_report()
    assert report["adaptive_leakage_detected"] is False


def test_views_quality_audit_required_views_present():
    report = load_report()
    assert report["overall"]["required_views_present"] is True


def test_views_quality_audit_traceability_pass():
    report = load_report()
    assert report["overall"]["raw_traceability_pass"] is True
    assert report["traceability_diagnostics"]["traceability_pass"] is True


def test_views_quality_audit_contains_view_quality_sections():
    report = load_report()
    expected = {
        "balanced_global_view",
        "a1_safe_view",
        "reading_bridge_view",
        "dialogue_bridge_view",
        "theme_scoped_view",
        "pattern_first_view",
        "vocabulary_first_view",
        "chunk_safe_view",
        "deduplicated_view",
    }
    assert expected.issubset(report["view_quality"])


def test_views_quality_audit_contains_score_diagnostics():
    report = load_report()
    assert "balanced_global_view" in report["score_diagnostics"]
    assert "reading_bridge_view" in report["score_diagnostics"]


def test_views_quality_audit_contains_deduplication_diagnostics():
    report = load_report()
    assert "balanced_global_view" in report["deduplication_diagnostics"]
    assert "deduplicated_view" in report["deduplication_diagnostics"]


def test_views_quality_audit_contains_downstream_readiness():
    report = load_report()
    readiness = report["downstream_readiness"]
    assert readiness["balanced_global_view"] in {"READY", "READY_WITH_WARNINGS", "NEEDS_TUNING", "NOT_READY"}
    assert readiness["reading_bridge_view"] in {"READY", "READY_WITH_WARNINGS", "NEEDS_TUNING", "NOT_READY"}


def test_views_quality_audit_status_is_valid():
    report = load_report()
    assert report["status"] in {"PASS", "PASS_WITH_WARNINGS", "FAIL"}
