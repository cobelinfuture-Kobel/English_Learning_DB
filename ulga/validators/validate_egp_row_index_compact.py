import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "egp_row_index_compact.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "egp_row_index_compact_summary.json"
EXPECTED_TASK = "R7-M97B_EGPCompactRowIndexBuilder"


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def validate():
    print("Validating EGP compact row index...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required compact index files missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    status = report.get("source_workbook_status")
    if status not in {"READY", "MISSING"}:
        return fail("invalid source_workbook_status")
    if summary.get("source_workbook_status") != status:
        return fail("summary source status mismatch")
    rows = report.get("rows", [])
    if status == "MISSING":
        if rows != [] or summary.get("row_count") != 0:
            return fail("missing-source report must have zero rows")
        if summary.get("stop_reason") != "SOURCE_WORKBOOK_REQUIRED":
            return fail("missing-source stop_reason mismatch")
    if status == "READY":
        if len(rows) < 100:
            return fail("ready compact index has too few rows")
        if summary.get("row_count") != len(rows):
            return fail("row_count mismatch")
        seen_refs = set()
        for row in rows:
            source_ref = row.get("source_ref")
            if not source_ref or source_ref in seen_refs:
                return fail("missing or duplicate source_ref")
            seen_refs.add(source_ref)
            for key in ["row_id", "level", "super_category", "sub_category", "guideword"]:
                if key not in row:
                    return fail(f"row missing key: {key}")
        if summary.get("stop_reason") != "NONE":
            return fail("ready stop_reason mismatch")
    constraints = report.get("scope_constraints", {})
    for key in ["canonical_grammar_write_allowed", "coverage_increase_allowed", "runtime_change_allowed"]:
        if constraints.get(key) is not False:
            return fail(f"constraint must be false: {key}")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("summary canonical write must be false")
    print("EGP compact row index validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
