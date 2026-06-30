import subprocess
import sys
from pathlib import Path

from ulga.audits.audit_learner_state_guardrails import REPORT_PATH, load_json, run_audit


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT_PATH = BASE_DIR / "ulga" / "audits" / "audit_learner_state_guardrails.py"


def test_audit_json_created(tmp_path):
    report_path = tmp_path / "guardrail_qa_audit.json"
    report = run_audit(report_path=report_path)
    assert report_path.exists()
    assert report["contract_version"] == "ULGA-S9I"


def test_audit_status_valid(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert report["status"] in {"PASS", "PASS_WITH_WARNINGS", "BLOCKER"}


def test_role_ceiling_findings_populated(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert report["role_ceiling_audit"]


def test_node_type_findings_populated(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert report["node_type_audit"]


def test_dialogue_review_present(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert report["dialogue_exception_review"]["recommendation"] in {"keep_exception", "tighten_exception", "remove_exception"}


def test_ranking_readiness_score_exists(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert isinstance(report["ranking_readiness"]["ranking_readiness_score"], int)
    assert isinstance(report["ranking_readiness"]["planner_readiness_score"], int)


def test_remaining_risks_populated(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert report["remaining_risks"]


def test_recommendation_present(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert report["recommendations"]
    assert report["recommendations"][0]["label"] == "Do S9J Stability Audit first"


def test_no_blockers_reported(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
    assert report["blockers"] == []


def test_status_pass_with_warnings(tmp_path):
    report = run_audit(report_path=tmp_path / "guardrail_qa_audit.json")
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
