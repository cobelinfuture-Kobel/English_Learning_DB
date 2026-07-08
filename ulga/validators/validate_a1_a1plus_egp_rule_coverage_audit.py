import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_egp_rule_coverage_audit.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_egp_rule_coverage_audit_summary.json"
TASK_ID = "R7-M100B_A1A1PLUS_EGPRuleCoverageAudit"


def fail(msg):
    print("FAIL: " + msg)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def validate():
    print("Validating A1/A1_PLUS EGP rule coverage audit...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required audit files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    if summary.get("source_index_status") != "READY":
        return fail("source index must be READY")
    if summary.get("a1_a1plus_node_count", 0) <= 0:
        return fail("node count must be positive")
    if summary.get("egp_a1_row_count", 0) <= 0:
        return fail("EGP A1 row count must be positive")
    total = summary.get("egp_a1_row_count")
    covered = summary.get("covered_egp_a1_row_count")
    missing = summary.get("missing_egp_a1_row_count")
    if covered + missing != total:
        return fail("row coverage counts do not add up")
    ratio = summary.get("egp_a1_row_coverage_ratio")
    if not isinstance(ratio, (int, float)) or ratio < 0 or ratio > 1:
        return fail("coverage ratio out of range")
    if summary.get("final_closeout_allowed") is not False:
        return fail("final_closeout_allowed must remain false until threshold policy exists")
    if not summary.get("final_closeout_blocker"):
        return fail("final_closeout_blocker missing")
    if summary.get("next_short_step") != "R7-M100C_LevelBandCloseoutGateValidator":
        return fail("next short step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    if report.get("canonical_grammar_write_allowed") is not False:
        return fail("canonical grammar write must be false")
    print("A1/A1_PLUS EGP rule coverage audit validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
