import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "egp_row_index_compact_v2.json"
SUMMARY = BASE / "ulga" / "reports" / "egp_row_index_compact_v2_summary.json"
TASK_ID = "R7-M100D_EGPCompactRowIndexV2Builder"
REQUIRED_FIELDS = ["lexical_range", "can_do", "example"]


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
    print("Validating EGP compact row index v2...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required v2 index files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    if report.get("source_workbook_status") != "READY" or summary.get("source_workbook_status") != "READY":
        return fail("source workbook must be READY")
    rows = report.get("rows", [])
    if not rows:
        return fail("rows missing")
    if summary.get("row_count") != len(rows):
        return fail("row_count mismatch")
    for field in REQUIRED_FIELDS:
        if field not in summary.get("required_fields", []):
            return fail(f"summary missing required field: {field}")
    sample = rows[:20]
    for row in sample:
        for field in ["source_ref", "row_id", "level", "super_category", "sub_category", "guideword", *REQUIRED_FIELDS]:
            if field not in row:
                return fail(f"row missing field: {field}")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("canonical grammar write must be false")
    if summary.get("next_short_step") != "R7-M100E_A1A1PLUSSemanticCoverageAuditV2":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("EGP compact row index v2 validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
