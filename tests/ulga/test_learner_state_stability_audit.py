import subprocess
import sys
from pathlib import Path

from ulga.audits.audit_learner_state_stability import REPORT_PATH, load_json, run_audit


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT_PATH = BASE_DIR / "ulga" / "audits" / "audit_learner_state_stability.py"


def test_audit_json_created(tmp_path):
    report_path = tmp_path / "stability_audit.json"
    report = run_audit(report_path=report_path)
    assert report_path.exists()
    assert report["contract_version"] == "ULGA-S9J"


def test_status_valid(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    assert report["status"] in {"PASS", "PASS_WITH_WARNINGS", "BLOCKER"}


def test_readiness_scores_present(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    assert isinstance(report["ranking_authority_readiness"]["score"], int)
    assert isinstance(report["planner_authority_readiness"]["score"], int)


def test_dialogue_assessment_present(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    assert report["dialogue_exception"]["recommendation"] in {"keep", "tighten", "remove"}


def test_direct_node_scores_present(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    for node_type in ["grammar", "vocabulary", "chunk", "sentence_pattern"]:
        assert node_type in report["direct_node_stability"]
        assert isinstance(report["direct_node_stability"][node_type]["score"], int)


def test_derived_node_scores_present(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    for node_type in ["theme", "morphology", "skill", "assessment", "dialogue", "reading", "exercise_type"]:
        assert node_type in report["derived_node_stability"]
        assert isinstance(report["derived_node_stability"][node_type]["score"], int)


def test_future_failure_modes_present(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    assert report["future_failure_modes"]


def test_recommendation_present(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    assert report["recommendations"]
    assert report["recommendations"][0]["recommended_next_task"] == "S10A_CandidateRanking_DesignScan"


def test_ranking_readiness_exceeds_planner_readiness(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    assert report["ranking_authority_readiness"]["score"] > report["planner_authority_readiness"]["score"]


def test_status_pass_with_warnings(tmp_path):
    report = run_audit(report_path=tmp_path / "stability_audit.json")
    assert report["status"] == "PASS_WITH_WARNINGS"


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
