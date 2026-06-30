import subprocess
import sys
from pathlib import Path

from ulga.audits.audit_post_tightening_readiness import REPORT_PATH, load_json, run_audit


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT_PATH = BASE_DIR / "ulga" / "audits" / "audit_post_tightening_readiness.py"


def test_audit_json_created(tmp_path):
    report_path = tmp_path / "post_tightening_readiness.json"
    report = run_audit(report_path=report_path)
    assert report_path.exists()
    assert report["contract_version"] == "ULGA-S9L"


def test_status_is_valid(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert report["status"] in {"PASS", "PASS_WITH_WARNINGS", "BLOCKER"}


def test_no_blockers_are_reported(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert report["blockers"] == []


def test_s9k_effect_confirmation_exists(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert report["s9k_effect_confirmation"]["status"] == "PASS"


def test_dialogue_record_is_practicing(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    target = report["s9k_effect_confirmation"]["target_record"]
    assert target["mastery_score"] == 0.49
    assert target["mastery_band"] == "practicing"


def test_readiness_scores_exist(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert isinstance(report["readiness_scores"]["ranking_readiness_score"], int)
    assert isinstance(report["readiness_scores"]["planner_readiness_score"], int)


def test_ranking_readiness_at_least_s9j(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert report["readiness_scores"]["ranking_readiness_score"] >= 74


def test_planner_readiness_at_least_s9j(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert report["readiness_scores"]["planner_readiness_score"] >= 57


def test_s10a_decision_exists(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert report["s10a_entry_decision"]["decision"] == "Yes with warnings"


def test_recommendation_includes_s10a(tmp_path):
    report = run_audit(report_path=tmp_path / "post_tightening_readiness.json")
    assert report["s10a_entry_decision"]["recommended_next_task"] == "S10A_CandidateRanking_DesignScan"


def test_audit_cli_passes():
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS_WITH_WARNINGS" in result.stdout
    report = load_json(REPORT_PATH)
    assert report["status"] == "PASS_WITH_WARNINGS"
