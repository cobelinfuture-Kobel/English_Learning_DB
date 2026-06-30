import json
import subprocess
import sys
from pathlib import Path

from ulga.audits.audit_learner_state_builder import AUDIT_REPORT_PATH, audit_review_due, load_json, run_audit


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT_PATH = BASE_DIR / "ulga" / "audits" / "audit_learner_state_builder.py"


def test_audit_script_creates_qa_audit_json(tmp_path):
    report_path = tmp_path / "qa_audit.json"
    report = run_audit(report_path=report_path)
    assert report_path.exists()
    assert report["contract_version"] == "ULGA-S9F"


def test_audit_status_is_pass_with_warnings_for_current_output(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    assert report["status"] == "PASS_WITH_WARNINGS"


def test_no_blockers_reported(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    assert report["blockers"] == []


def test_role_risk_warnings_are_detected(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    assert report["role_risk_records"]
    assert any(item["warning_code"] == "WARN_ROLE_HIGH_BAND_LOW_AUTHORITY_ROLE" for item in report["role_risk_records"])


def test_ratio_risk_warnings_are_detected(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    codes = {item["warning_code"] for item in report["ratio_risk_records"]}
    assert "WARN_RATIO_OVERSTATEMENT_RISK" in codes
    assert "WARN_SINGLE_EVENT_DERIVED_NODE_MASTERY" in codes


def test_decay_warning_is_detected(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    assert any("WARN_DECAY_NOT_MODELED" in warning for warning in report["warnings"])


def test_boundary_audit_confirms_no_planner_or_ranking_fields(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    assert all(item["status"] == "PASS" for item in report["boundary_findings"])


def test_summary_metrics_match_actual_output(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    metrics = report["metrics"]
    assert metrics["total_events"] == 3
    assert metrics["total_flattened_entries"] == 9
    assert metrics["total_learner_state_records"] == 9
    assert metrics["learner_count"] == 2


def test_duplicate_learner_node_pairs_are_not_present(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    assert report["metrics"]["duplicate_learner_node_pair_count"] == 0


def test_duplicate_output_idempotency_keys_are_not_present(tmp_path):
    report = run_audit(report_path=tmp_path / "qa_audit.json")
    assert report["metrics"]["duplicate_output_processing_idempotency_key_count"] == 0


def review_record(**overrides):
    record = {
        "learner_id": "learner:test",
        "node_id": "grammar:TEST_NODE",
        "mastery_band": "practicing",
        "last_seen_at": "2026-06-17T09:00:00Z",
        "last_success_at": None,
        "review_due_at": "2026-06-20T09:00:00Z",
    }
    record.update(overrides)
    return record


def test_practicing_with_last_seen_anchor_allows_review_due():
    _, blockers, findings = audit_review_due([review_record()])
    assert blockers == []
    assert findings[0]["status"] == "PASS"


def test_practicing_without_any_anchor_blocks_review_due():
    _, blockers, _ = audit_review_due([
        review_record(last_seen_at=None, last_success_at=None)
    ])
    assert blockers


def test_mastered_without_last_success_blocks_review_due():
    _, blockers, _ = audit_review_due([
        review_record(
            mastery_band="mastered",
            last_seen_at="2026-06-17T09:00:00Z",
            last_success_at=None,
            review_due_at="2026-07-01T09:00:00Z",
        )
    ])
    assert blockers


def test_seen_with_last_seen_anchor_allows_review_due():
    _, blockers, findings = audit_review_due([
        review_record(
            mastery_band="seen",
            last_seen_at="2026-06-17T09:00:00Z",
            last_success_at=None,
            review_due_at="2026-06-19T09:00:00Z",
        )
    ])
    assert blockers == []
    assert findings[0]["status"] == "PASS"


def test_audit_script_cli_passes_and_writes_default_report():
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS_WITH_WARNINGS" in result.stdout
    report = load_json(AUDIT_REPORT_PATH)
    assert report["status"] == "PASS_WITH_WARNINGS"
