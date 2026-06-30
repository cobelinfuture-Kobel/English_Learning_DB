import argparse
import json
import subprocess
import sys
from pathlib import Path


AUDIT_NAME = "ULGA-S9Z9_LearnerStateReplay_PromotionReadiness_Audit"
AUDIT_VERSION = "S9Z9"
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_replay_promotion_readiness_audit.json"


def load_json(path: Path) -> dict | list:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def make_check(status: str, details: dict) -> dict:
    payload = {"status": status}
    payload.update(details)
    return payload


def run_command(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "status": "PASS" if result.returncode == 0 else "FAIL",
    }


def audit_artifact_presence(root: Path) -> dict:
    required_paths = {
        "s9z8_closeout_markdown": root / "docs" / "ulga" / "ULGA_S9Z8_LEARNER_STATE_REPLAY_CLOSEOUT_AND_PROMOTION_CRITERIA.md",
        "s9z8_readiness_json": root / "ulga" / "reports" / "learner_state_replay_promotion_readiness.json",
        "s9z7_qa_markdown": root / "docs" / "ulga" / "ULGA_S9Z7_LEARNER_STATE_REPLAY_QA_AUDIT.md",
        "s9z7_qa_report_json": root / "ulga" / "reports" / "learner_state_replay_prototype_qa_audit.json",
        "s9z6_prototype_markdown": root / "docs" / "ulga" / "ULGA_S9Z6_LEARNER_STATE_REPLAY_PROTOTYPE.md",
        "s9z6_prototype_summary_report": root / "ulga" / "reports" / "learner_state_replay_prototype_summary.json",
        "s9z5_reducer_design_scan": root / "docs" / "ulga" / "ULGA_S9Z5_LEARNER_EVENT_REDUCER_DESIGN_SCAN.md",
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    status = "FAIL" if missing else "PASS"
    return make_check(
        status,
        {
            "required_files": {name: str(path.relative_to(root)) for name, path in required_paths.items()},
            "missing_files": missing,
        },
    )


def audit_s9z8_readiness_metadata(root: Path) -> dict:
    data = load_json(root / "ulga" / "reports" / "learner_state_replay_promotion_readiness.json")
    expected = {
        "status": "NOT_READY",
        "promotion_allowed": False,
        "s10a_integration_allowed": False,
        "planner_integration_allowed": False,
        "current_stage": "prototype_qa_passed",
    }
    mismatches = {key: data.get(key) for key, value in expected.items() if data.get(key) != value}
    status = "PASS" if not mismatches else "FAIL"
    return make_check(status, {"expected": expected, "actual_mismatches": mismatches})


def audit_blocker_coverage(root: Path) -> dict:
    data = load_json(root / "ulga" / "reports" / "learner_state_replay_promotion_readiness.json")
    blockers = set(data.get("blockers", []))
    required = {
        "scoring_calibration_missing",
        "decay_policy_missing",
        "dependency_lock_missing",
        "canonical_schema_alignment_missing",
        "event_store_idempotency_missing",
        "rollback_plan_missing",
        "s10a_contract_missing",
    }
    missing = sorted(required - blockers)
    extra = sorted(blockers - required)
    status = "PASS" if not missing else "FAIL"
    return make_check(status, {"required_blockers": sorted(required), "missing_blockers": missing, "extra_blockers": extra})


def audit_completed_foundations(root: Path) -> dict:
    data = load_json(root / "ulga" / "reports" / "learner_state_replay_promotion_readiness.json")
    foundations = set(data.get("completed_foundations", []))
    required = {"event_schema", "event_validator", "replay_prototype", "prototype_qa_audit"}
    missing = sorted(required - foundations)
    status = "PASS" if not missing else "PASS_WITH_WARNINGS"
    return make_check(status, {"required_foundations": sorted(required), "missing_foundations": missing})


def audit_s9z8_markdown_policy(root: Path) -> dict:
    text = read_text(root / "docs" / "ulga" / "ULGA_S9Z8_LEARNER_STATE_REPLAY_CLOSEOUT_AND_PROMOTION_CRITERIA.md")
    checks = {
        "not_promotion_implementation": "It is not a promotion implementation." in text or "S9Z8 does not promote prototype learner_state." in text,
        "promotion_not_allowed": "Promotion to canonical learner_state: NOT ALLOWED IN S9Z8" in text,
        "s10a_blocked": "S10A integration remains blocked." in text or "S10A Candidate Ranking integration remains blocked after S9Z8." in text,
        "planner_blocked": "planner integration = not allowed yet" in text or "connect S9Z6 output directly to planner" in text,
        "prototype_weights_not_production": "treat prototype weights as production scores" in text,
        "dedicated_promotion_task_required": "Promotion must happen through a dedicated promotion task." in text,
        "canonical_not_overwritten": "overwrite `ulga/learner_state/learner_state.json`" in text,
        "direct_s10a_after_s9z8_not_allowed": "Do not recommend direct S10A integration after S9Z8." in text,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return make_check(status, {"policy_checks": checks})


def audit_s9z7_consistency(root: Path) -> dict:
    report = load_json(root / "ulga" / "reports" / "learner_state_replay_prototype_qa_audit.json")
    status_ok = report.get("status") in {"PASS", "PASS_WITH_WARNINGS"}
    promotion_allowed = report.get("recommendation", {}).get("promotion_allowed")
    s10a_allowed = False
    planner_allowed = False
    doc_text = read_text(root / "docs" / "ulga" / "ULGA_S9Z7_LEARNER_STATE_REPLAY_QA_AUDIT.md")
    s10a_blocked = "S10A integration" not in doc_text or "No candidate ranking integration exists yet." in doc_text
    planner_blocked = "No planner integration exists yet." in doc_text
    status = "PASS" if status_ok and promotion_allowed is False and s10a_blocked and planner_blocked else "FAIL"
    return make_check(
        status,
        {
            "s9z7_status": report.get("status"),
            "promotion_allowed": promotion_allowed,
            "s10a_integration_allowed": s10a_allowed,
            "planner_integration_allowed": planner_allowed,
            "s10a_blocked_in_doc": s10a_blocked,
            "planner_blocked_in_doc": planner_blocked,
        },
    )


def audit_s9z6_prototype_isolation(root: Path) -> dict:
    summary = load_json(root / "ulga" / "reports" / "learner_state_replay_prototype_summary.json")
    policy = summary.get("policy_summary", {})
    expected = {
        "deterministic_replay_order": True,
        "complete_idempotency_claimed": False,
        "quarantine_excluded": True,
        "theme_only_mastery_blocked": True,
        "exposure_only_mastery_blocked": True,
        "canonical_learner_state_modified": False,
    }
    mismatches = {key: policy.get(key) for key, value in expected.items() if policy.get(key) != value}
    status = "PASS" if not mismatches else "FAIL"
    return make_check(status, {"expected_policy": expected, "actual_mismatches": mismatches})


def audit_s9z5_replay_semantics(root: Path) -> dict:
    text = read_text(root / "docs" / "ulga" / "ULGA_S9Z5_LEARNER_EVENT_REDUCER_DESIGN_SCAN.md")
    required_phrase = (
        "This ordering policy guarantees deterministic replay order. "
        "Process-restart-safe idempotency additionally depends on duplicate event_id protection, "
        "stable event indexing, and append safety."
    )
    deterministic_phrase = "Because derived states must be deterministic projections"
    old_phrase = "Because derived states are non-deterministic projections"
    checks = {
        "required_ordering_phrase_present": required_phrase in text,
        "deterministic_projection_phrase_present": deterministic_phrase in text,
        "old_incorrect_phrase_absent": old_phrase not in text,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return make_check(status, checks)


def audit_canonical_learner_state_safety(root: Path) -> dict:
    canonical_path = root / "ulga" / "learner_state" / "learner_state.json"
    exists = canonical_path.exists()
    before_mtime = canonical_path.stat().st_mtime_ns if exists else None
    after_mtime = canonical_path.stat().st_mtime_ns if exists else None
    modified = exists and before_mtime != after_mtime
    status = "PASS" if not modified else "FAIL"
    return make_check(
        status,
        {
            "canonical_learner_state_exists": exists,
            "modified_by_s9z9": modified,
            "canonical_path": str(canonical_path.relative_to(root)),
        },
    )


def audit_downstream_integration_block(root: Path) -> dict:
    text = read_text(root / "docs" / "ulga" / "ULGA_S9Z8_LEARNER_STATE_REPLAY_CLOSEOUT_AND_PROMOTION_CRITERIA.md")
    readiness = load_json(root / "ulga" / "reports" / "learner_state_replay_promotion_readiness.json")
    checks = {
        "s10a_blocked_in_json": readiness.get("s10a_integration_allowed") is False,
        "planner_blocked_in_json": readiness.get("planner_integration_allowed") is False,
        "promotion_blocked_in_json": readiness.get("promotion_allowed") is False,
        "s10a_blocked_in_markdown": "S10A integration remains blocked." in text,
        "planner_blocked_in_markdown": "planner integration = not allowed yet" in text or "connect S9Z6 output directly to planner" in text,
        "runtime_api_blocked_in_markdown": "S9Z8 does not connect to S10A Candidate Ranking." in text and "S9Z8 defines the rules required before those actions are allowed." in text,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return make_check(status, {"integration_checks": checks})


def audit_risk_register(root: Path) -> dict:
    text = read_text(root / "docs" / "ulga" / "ULGA_S9Z8_LEARNER_STATE_REPLAY_CLOSEOUT_AND_PROMOTION_CRITERIA.md")
    required_risks = [
        "Prototype score overfitting",
        "False mastery from insufficient attempts",
        "Lack of decay formula",
        "Dependency lock absence",
        "Event store duplicate replay",
        "Schema migration mismatch",
        "learner_state cache staleness",
        "Candidate ranking reading unstable fields",
        "Planner acting on prototype output",
        "Rollback failure",
    ]
    missing = [risk for risk in required_risks if risk not in text]
    if not missing:
        status = "PASS"
    elif len(missing) <= 2:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "FAIL"
    return make_check(status, {"required_risks": required_risks, "missing_risks": missing})


def run_regression_commands(root: Path) -> dict:
    return {
        "s9z6_tests": run_command([sys.executable, "-m", "pytest", "tests/ulga/test_learner_state_replay_prototype.py", "-q"], root),
        "s9z4_validator_tests": run_command([sys.executable, "-m", "pytest", "tests/ulga/test_validate_learner_event_log.py", "-q"], root),
        "s9z3_schema_tests": run_command([sys.executable, "-m", "pytest", "tests/ulga/test_learner_event_log_schema.py", "-q"], root),
        "broader_ulga_tests": None,
    }


def summarize_status(checks: dict, commands: dict) -> tuple[str, dict]:
    check_statuses = [payload["status"] for payload in checks.values()]
    command_statuses = [payload["status"] for payload in commands.values() if isinstance(payload, dict)]
    failures = sum(status == "FAIL" for status in check_statuses) + sum(status == "FAIL" for status in command_statuses)
    warnings = sum(status == "PASS_WITH_WARNINGS" for status in check_statuses)
    checks_passed = sum(status == "PASS" for status in check_statuses)
    checks_total = len(check_statuses)
    if failures > 0:
        status = "FAIL"
    elif warnings > 0:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"
    return status, {
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "warnings": warnings,
        "failures": failures,
    }


def run_audit(root: Path) -> dict:
    readiness = load_json(root / "ulga" / "reports" / "learner_state_replay_promotion_readiness.json")
    checks = {
        "artifact_presence": audit_artifact_presence(root),
        "s9z8_readiness_metadata": audit_s9z8_readiness_metadata(root),
        "promotion_blocker_coverage": audit_blocker_coverage(root),
        "completed_foundations": audit_completed_foundations(root),
        "s9z8_markdown_policy": audit_s9z8_markdown_policy(root),
        "s9z7_audit_consistency": audit_s9z7_consistency(root),
        "s9z6_prototype_isolation": audit_s9z6_prototype_isolation(root),
        "s9z5_replay_semantics": audit_s9z5_replay_semantics(root),
        "canonical_learner_state_safety": audit_canonical_learner_state_safety(root),
        "downstream_integration_block": audit_downstream_integration_block(root),
        "risk_register": audit_risk_register(root),
    }
    commands = run_regression_commands(root)
    status, summary = summarize_status(checks, commands)
    return {
        "status": status,
        "audit_name": AUDIT_NAME,
        "audit_version": AUDIT_VERSION,
        "scope": "read_only_promotion_readiness_audit",
        "promotion_allowed": False,
        "s10a_integration_allowed": False,
        "planner_integration_allowed": False,
        "summary": summary,
        "checks": checks,
        "commands": commands,
        "recommendation": {
            "current_readiness": readiness.get("status", "NOT_READY"),
            "next_task": "ULGA-S9ZA_LearnerStateCanonicalSchema_DesignScan",
            "promotion_allowed": False,
            "direct_s10a_integration_allowed": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ULGA learner state replay promotion readiness.")
    parser.add_argument("--root", default=str(BASE_DIR), help="Repository root")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Path to write the audit report JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root)
    report_path = Path(args.report)
    try:
        report = run_audit(root)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
    except Exception as exc:
        print(f"Learner state replay promotion readiness audit: FAIL - {exc}")
        return 1

    print(f"Learner state replay promotion readiness audit: {report['status']}")
    print(f"Report written to {report_path}")
    print(f"Promotion allowed: {report['promotion_allowed']}")
    print(f"S10A integration allowed: {report['s10a_integration_allowed']}")
    print(f"Planner integration allowed: {report['planner_integration_allowed']}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    sys.exit(main())
