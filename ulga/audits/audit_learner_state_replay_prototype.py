import argparse
import json
import subprocess
import sys
from pathlib import Path


AUDIT_NAME = "ULGA-S9Z7_LearnerStateReplay_QA_Audit"
AUDIT_VERSION = "S9Z7"
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_replay_prototype_qa_audit.json"


def load_json(path: Path) -> dict | list:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def make_check(status: str, details: dict) -> dict:
    payload = {"status": status}
    payload.update(details)
    return payload


def audit_artifact_presence(root: Path) -> dict:
    required_paths = {
        "s9z6_builder": root / "ulga" / "builders" / "build_learner_state_replay_prototype.py",
        "s9z6_test_file": root / "tests" / "ulga" / "test_learner_state_replay_prototype.py",
        "s9z6_fixture": root / "tests" / "fixtures" / "ulga" / "learner_event_replay_prototype_events.json",
        "s9z6_documentation": root / "docs" / "ulga" / "ULGA_S9Z6_LEARNER_STATE_REPLAY_PROTOTYPE.md",
        "prototype_learner_state_projection": root / "ulga" / "learner_state" / "prototype" / "learner_state_projection_prototype.json",
        "prototype_mastery_graph_projection": root / "ulga" / "learner_state" / "prototype" / "mastery_graph_projection_prototype.json",
        "prototype_summary_report": root / "ulga" / "reports" / "learner_state_replay_prototype_summary.json",
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


def audit_prototype_isolation(root: Path) -> dict:
    builder_path = root / "ulga" / "builders" / "build_learner_state_replay_prototype.py"
    summary_path = root / "ulga" / "reports" / "learner_state_replay_prototype_summary.json"
    learner_state_projection_path = root / "ulga" / "learner_state" / "prototype" / "learner_state_projection_prototype.json"
    mastery_graph_projection_path = root / "ulga" / "learner_state" / "prototype" / "mastery_graph_projection_prototype.json"
    canonical_path = root / "ulga" / "learner_state" / "learner_state.json"

    builder_text = builder_path.read_text(encoding="utf-8")
    summary = load_json(summary_path)

    prototype_paths_only = (
        learner_state_projection_path.exists()
        and mastery_graph_projection_path.exists()
        and learner_state_projection_path.parent == root / "ulga" / "learner_state" / "prototype"
        and mastery_graph_projection_path.parent == root / "ulga" / "learner_state" / "prototype"
        and summary_path.parent == root / "ulga" / "reports"
        and "learner_state_projection_prototype.json" in builder_text
        and "mastery_graph_projection_prototype.json" in builder_text
    )
    canonical_modified = bool(summary.get("policy_summary", {}).get("canonical_learner_state_modified", True))
    canonical_exists = canonical_path.exists()

    status = "PASS" if prototype_paths_only and not canonical_modified else "FAIL"
    return make_check(
        status,
        {
            "canonical_learner_state_exists": canonical_exists,
            "canonical_learner_state_modified": canonical_modified,
            "prototype_paths_only": prototype_paths_only,
            "prototype_learner_state_path": str(learner_state_projection_path.relative_to(root)),
            "prototype_mastery_graph_path": str(mastery_graph_projection_path.relative_to(root)),
            "summary_report_path": str(summary_path.relative_to(root)),
        },
    )


def audit_s9z5_errata(root: Path) -> dict:
    path = root / "docs" / "ulga" / "ULGA_S9Z5_LEARNER_EVENT_REDUCER_DESIGN_SCAN.md"
    text = path.read_text(encoding="utf-8")

    required_phrase = (
        "This ordering policy guarantees deterministic replay order. "
        "Process-restart-safe idempotency additionally depends on duplicate event_id protection, "
        "stable event indexing, and append safety."
    )
    deterministic_phrase = "Because derived states must be deterministic projections"
    old_phrase = "Because derived states are non-deterministic projections"

    status = "PASS"
    missing = []
    if required_phrase not in text:
        status = "FAIL"
        missing.append("errata_ordering_phrase")
    if deterministic_phrase not in text:
        status = "FAIL"
        missing.append("deterministic_projection_phrase")
    if old_phrase in text:
        status = "FAIL"
        missing.append("old_incorrect_phrase_still_present")

    return make_check(
        status,
        {
            "required_ordering_phrase_present": required_phrase in text,
            "deterministic_projection_phrase_present": deterministic_phrase in text,
            "old_incorrect_phrase_present": old_phrase in text,
            "missing_or_invalid": missing,
        },
    )


def audit_deterministic_replay_policy(root: Path) -> dict:
    builder_text = (root / "ulga" / "builders" / "build_learner_state_replay_prototype.py").read_text(encoding="utf-8")
    doc_text = (root / "docs" / "ulga" / "ULGA_S9Z6_LEARNER_STATE_REPLAY_PROTOTYPE.md").read_text(encoding="utf-8")
    summary = load_json(root / "ulga" / "reports" / "learner_state_replay_prototype_summary.json")

    order_terms_present = all(term in builder_text or term in doc_text for term in ["occurred_at_utc", "event_id", "input_index"])
    no_complete_idempotency_claim = (
        "complete process-restart-safe idempotency" in doc_text
        and summary.get("policy_summary", {}).get("complete_idempotency_claimed") is False
    )
    deterministic_reported = summary.get("policy_summary", {}).get("deterministic_replay_order") is True

    status = "PASS" if order_terms_present and no_complete_idempotency_claim and deterministic_reported else "FAIL"
    return make_check(
        status,
        {
            "sort_fields_present": {
                "occurred_at_utc": "occurred_at_utc" in builder_text or "occurred_at_utc" in doc_text,
                "event_id": "event_id" in builder_text or "event_id" in doc_text,
                "input_index": "input_index" in builder_text or "input_index" in doc_text,
            },
            "deterministic_replay_order": deterministic_reported,
            "complete_idempotency_claimed": summary.get("policy_summary", {}).get("complete_idempotency_claimed"),
            "complete_idempotency_disclaimed": "Complete idempotency requires duplicate event_id protection" in doc_text,
        },
    )


def audit_fixture_coverage(root: Path) -> dict:
    fixture = load_json(root / "tests" / "fixtures" / "ulga" / "learner_event_replay_prototype_events.json")
    events = fixture["events"] if isinstance(fixture, dict) else fixture

    has_exposure_only = any(
        event.get("event_type") == "exposure_seen"
        and not event.get("attempt", {}).get("is_correct")
        and event.get("quality_flags", {}).get("requires_review") is False
        for event in events
    )
    has_correct_first_try = any(
        event.get("event_type") == "answer_submitted"
        and event.get("attempt", {}).get("is_correct") is True
        and event.get("attempt", {}).get("attempt_number") == 1
        and event.get("attempt", {}).get("used_hint") is False
        for event in events
    )
    has_retry = any(event.get("event_type") == "retry_attempt" for event in events)
    has_hint = any(event.get("event_type") == "hint_used" for event in events)
    has_assessment_attempt = any(event.get("event_type") == "assessment_attempt" for event in events)
    has_mastery_pass = any(
        event.get("event_type") == "mastery_check"
        and isinstance(event.get("attempt", {}).get("score"), (int, float))
        and isinstance(event.get("attempt", {}).get("max_score"), (int, float))
        and event["attempt"]["max_score"] > 0
        and (event["attempt"]["score"] / event["attempt"]["max_score"]) >= 0.7
        for event in events
    )
    has_mastery_fail = any(
        event.get("event_type") == "mastery_check"
        and isinstance(event.get("attempt", {}).get("score"), (int, float))
        and isinstance(event.get("attempt", {}).get("max_score"), (int, float))
        and event["attempt"]["max_score"] > 0
        and (event["attempt"]["score"] / event["attempt"]["max_score"]) < 0.7
        for event in events
    )
    has_content_completed = any(event.get("event_type") == "content_completed" for event in events)
    has_requires_review = any(event.get("quality_flags", {}).get("requires_review") is True for event in events)
    has_producer_invalid = any(event.get("quality_flags", {}).get("valid_event") is False for event in events)
    has_timezone_offset = any(isinstance(event.get("occurred_at"), str) and "+" in event["occurred_at"] for event in events)

    timestamps = [event.get("occurred_at") for event in events if isinstance(event.get("occurred_at"), str)]
    has_out_of_order = any(timestamps[idx] < timestamps[idx - 1] for idx in range(1, len(timestamps)))

    coverage = {
        "exposure_only_event": has_exposure_only,
        "correct_first_try_answer": has_correct_first_try,
        "retry_event": has_retry,
        "hint_used_event": has_hint,
        "assessment_attempt": has_assessment_attempt,
        "mastery_check_pass": has_mastery_pass,
        "mastery_check_fail": has_mastery_fail,
        "content_completed_event": has_content_completed,
        "requires_review_event": has_requires_review,
        "producer_marked_invalid_event": has_producer_invalid,
        "out_of_order_timestamp_sequence": has_out_of_order,
        "timezone_offset_timestamp": has_timezone_offset,
    }

    failures = []
    warnings = []
    if not has_requires_review:
        failures.append("requires_review_event")
    if not has_producer_invalid:
        failures.append("producer_marked_invalid_event")
    if not has_timezone_offset:
        failures.append("timezone_offset_timestamp")
    if not has_out_of_order:
        failures.append("out_of_order_timestamp_sequence")
    if not has_content_completed:
        warnings.append("content_completed_event")
    if not has_hint:
        warnings.append("hint_used_event")

    status = "FAIL" if failures else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    return make_check(status, {"coverage": coverage, "failures": failures, "warnings": warnings})


def audit_exclusion_policy(root: Path) -> dict:
    projection = load_json(root / "ulga" / "learner_state" / "prototype" / "learner_state_projection_prototype.json")
    summary = load_json(root / "ulga" / "reports" / "learner_state_replay_prototype_summary.json")

    node_ids = {node["node_id"] for node in projection.get("nodes", [])}
    orange_absent = "vocab:orange" not in node_ids
    grape_absent = "vocab:grape" not in node_ids
    quarantine_count = summary.get("input_summary", {}).get("events_excluded_quarantine") == 1
    invalid_count = summary.get("input_summary", {}).get("events_excluded_invalid") == 1

    status = "PASS" if orange_absent and grape_absent and quarantine_count and invalid_count else "FAIL"
    return make_check(
        status,
        {
            "events_excluded_quarantine": summary.get("input_summary", {}).get("events_excluded_quarantine"),
            "events_excluded_invalid": summary.get("input_summary", {}).get("events_excluded_invalid"),
            "excluded_only_nodes_absent": {
                "vocab:orange": orange_absent,
                "vocab:grape": grape_absent,
            },
        },
    )


def audit_exposure_ceiling(root: Path) -> dict:
    projection = load_json(root / "ulga" / "learner_state" / "prototype" / "learner_state_projection_prototype.json")
    node = next((node for node in projection.get("nodes", []) if node.get("node_id") == "vocab:apple"), None)
    if not node:
        return make_check("FAIL", {"reason": "vocab:apple not found in prototype projection"})

    band = node.get("mastery_projection", {}).get("band")
    status = "PASS" if band == "seen" else "FAIL"
    return make_check(status, {"node_id": "vocab:apple", "band": band})


def audit_theme_mastery_block(root: Path) -> dict:
    projection = load_json(root / "ulga" / "learner_state" / "prototype" / "learner_state_projection_prototype.json")
    node = next((node for node in projection.get("nodes", []) if node.get("node_id") == "theme:a1_food_and_drink"), None)
    if not node:
        return make_check("FAIL", {"reason": "theme:a1_food_and_drink not found in prototype projection"})

    raw_score = node.get("mastery_projection", {}).get("raw_score")
    band = node.get("mastery_projection", {}).get("band")
    status = "PASS" if raw_score == 0.0 and band not in {"functional", "mastered", "automatic"} else "FAIL"
    return make_check(status, {"node_id": node["node_id"], "raw_score": raw_score, "band": band})


def audit_failed_mastery_check(root: Path) -> dict:
    projection = load_json(root / "ulga" / "learner_state" / "prototype" / "learner_state_projection_prototype.json")
    node = next((node for node in projection.get("nodes", []) if node.get("node_id") == "vocab:banana"), None)
    if not node:
        return make_check("FAIL", {"reason": "vocab:banana not found in prototype projection"})

    band = node.get("mastery_projection", {}).get("band")
    status = "PASS" if band == "review_needed" else "FAIL"
    return make_check(status, {"node_id": "vocab:banana", "band": band})


def audit_summary_contract(root: Path) -> dict:
    summary = load_json(root / "ulga" / "reports" / "learner_state_replay_prototype_summary.json")
    required_top = ["status", "reducer_version", "input_summary", "node_projection_summary", "policy_summary"]
    required_policy = [
        "deterministic_replay_order",
        "complete_idempotency_claimed",
        "quarantine_excluded",
        "theme_only_mastery_blocked",
        "exposure_only_mastery_blocked",
        "canonical_learner_state_modified",
    ]

    missing_top = [key for key in required_top if key not in summary]
    policy = summary.get("policy_summary", {})
    missing_policy = [key for key in required_policy if key not in policy]
    expected_policy = {
        "deterministic_replay_order": True,
        "complete_idempotency_claimed": False,
        "quarantine_excluded": True,
        "theme_only_mastery_blocked": True,
        "exposure_only_mastery_blocked": True,
        "canonical_learner_state_modified": False,
    }
    mismatched_policy = {key: policy.get(key) for key, value in expected_policy.items() if policy.get(key) != value}

    status = "PASS" if not missing_top and not missing_policy and not mismatched_policy else "FAIL"
    return make_check(
        status,
        {
            "missing_top_level_fields": missing_top,
            "missing_policy_fields": missing_policy,
            "mismatched_policy_values": mismatched_policy,
        },
    )


def audit_output_shape(root: Path) -> dict:
    learner_state = load_json(root / "ulga" / "learner_state" / "prototype" / "learner_state_projection_prototype.json")
    mastery_graph = load_json(root / "ulga" / "learner_state" / "prototype" / "mastery_graph_projection_prototype.json")

    learner_state_required = ["status", "prototype_warning", "reducer_version", "learner_ids", "node_count", "nodes"]
    node_required = ["learner_id", "node_id", "node_type", "exposure", "practice", "assessment", "reinforcement", "engagement", "mastery_projection"]
    mastery_graph_required = ["status", "prototype_warning", "reducer_version", "nodes", "edges"]

    missing_learner_state = [key for key in learner_state_required if key not in learner_state]
    missing_mastery_graph = [key for key in mastery_graph_required if key not in mastery_graph]
    invalid_nodes = []
    for idx, node in enumerate(learner_state.get("nodes", [])):
        missing_fields = [key for key in node_required if key not in node]
        if missing_fields:
            invalid_nodes.append({"index": idx, "missing_fields": missing_fields})

    status = "PASS" if not missing_learner_state and not missing_mastery_graph and not invalid_nodes else "FAIL"
    return make_check(
        status,
        {
            "missing_learner_state_fields": missing_learner_state,
            "missing_mastery_graph_fields": missing_mastery_graph,
            "invalid_node_records": invalid_nodes,
        },
    )


def run_command(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "status": "PASS" if result.returncode == 0 else "FAIL",
    }


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
    checks = {
        "artifact_presence": audit_artifact_presence(root),
        "prototype_isolation": audit_prototype_isolation(root),
        "s9z5_errata_alignment": audit_s9z5_errata(root),
        "deterministic_replay_policy": audit_deterministic_replay_policy(root),
        "fixture_coverage": audit_fixture_coverage(root),
        "quarantine_invalid_exclusion": audit_exclusion_policy(root),
        "exposure_only_ceiling": audit_exposure_ceiling(root),
        "theme_direct_mastery_block": audit_theme_mastery_block(root),
        "failed_mastery_check_review_signal": audit_failed_mastery_check(root),
        "summary_report_contract": audit_summary_contract(root),
        "prototype_output_shape": audit_output_shape(root),
    }
    commands = run_regression_commands(root)
    status, summary = summarize_status(checks, commands)
    next_task = (
        "ULGA-S9Z8_LearnerStateReplay_Closeout_And_PromotionCriteria"
        if status == "PASS"
        else "ULGA-S9Z8_LearnerStateReplay_Prototype_Fix"
    )
    return {
        "status": status,
        "audit_name": AUDIT_NAME,
        "audit_version": AUDIT_VERSION,
        "scope": "read_only_prototype_qa",
        "summary": summary,
        "checks": checks,
        "commands": commands,
        "recommendation": {
            "next_task": next_task,
            "promotion_allowed": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ULGA learner state replay prototype outputs.")
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
        print(f"Learner state replay prototype QA audit: FAIL - {exc}")
        return 1

    print(f"Learner state replay prototype QA audit: {report['status']}")
    print(f"Report written to {report_path}")
    print(f"Promotion allowed: {report['recommendation']['promotion_allowed']}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    sys.exit(main())
