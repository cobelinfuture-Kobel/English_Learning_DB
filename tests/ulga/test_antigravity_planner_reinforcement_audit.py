import json
import subprocess
import sys
from pathlib import Path

from ulga.audits.audit_antigravity_planner_with_reinforcement import AUDIT_OUT_PATH, run_audit


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT_PATH = BASE_DIR / "ulga" / "audits" / "audit_antigravity_planner_with_reinforcement.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_audit_runs(tmp_path):
    report = run_audit(report_path=tmp_path / "audit.json")
    assert report["contract_version"] == "ULGA-S10H"


def test_audit_report_exists():
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert AUDIT_OUT_PATH.exists()


def test_status_is_pass_or_pass_with_warnings(tmp_path):
    report = run_audit(report_path=tmp_path / "audit.json")
    assert report["status"] in {"PASS", "PASS_WITH_WARNINGS"}


def test_does_not_report_planner_failure_when_no_eligible_signal(tmp_path):
    report = run_audit(report_path=tmp_path / "audit.json")
    assert report["signal_presence"]["eligible_with_score_gt_zero"] == 0
    assert report["diagnosis"]["planner_failure"] is False


def test_detects_dependency_unknown_as_upstream_cause(tmp_path):
    report = run_audit(report_path=tmp_path / "audit.json")
    assert report["diagnosis"]["primary_cause"] == "UPSTREAM_DEPENDENCY_READINESS_GAP"
    assert report["signal_presence"]["dependency_unknown_blocked_count"] >= report["signal_presence"]["signals_with_score_gt_zero"]


def test_no_selected_ineligible_reinforcement(tmp_path):
    report = run_audit(report_path=tmp_path / "audit.json")
    assert report["planner_behavior"]["selected_ineligible_reinforcement_claims"] == []
    assert report["planner_behavior"]["missing_reinforcement_signal_claims"] == []
    assert "planner_claimed_ineligible_reinforcement" not in report["blockers"]


def test_structural_fallback_detected(tmp_path):
    report = run_audit(report_path=tmp_path / "audit.json")
    assert report["planner_behavior"]["reinforcement_block_exists"] is True
    assert report["planner_behavior"]["structural_fallback_detected"] is True
