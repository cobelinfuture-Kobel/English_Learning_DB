import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_egp_alignment_evp_intake_diagnostics.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_evp_intake_diagnostics_summary.json"
TASK_ID = "R7-M104C_A1EGPAlignmentEVPIntakeDiagnostics"


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
    print("Validating A1 EGP alignment EVP intake diagnostics...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required diagnostics files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    inspected = report.get("inspected_paths", [])
    if not inspected:
        return fail("inspected_paths missing")
    existing = sum(1 for item in inspected if item.get("exists"))
    readable = sum(1 for item in inspected if item.get("readable"))
    if summary.get("inspected_path_count") != len(inspected):
        return fail("inspected_path_count mismatch")
    if summary.get("existing_path_count") != existing:
        return fail("existing_path_count mismatch")
    if summary.get("readable_path_count") != readable:
        return fail("readable_path_count mismatch")
    if summary.get("evp_ready") != (readable > 0):
        return fail("evp_ready mismatch")
    if report.get("evp_ready") != summary.get("evp_ready"):
        return fail("report/summary evp_ready mismatch")
    if summary.get("source_intake_required") != (readable == 0):
        return fail("source_intake_required mismatch")
    if summary.get("evp_ready") and not summary.get("recommended_evp_source_path"):
        return fail("recommended path required when EVP is ready")
    if not summary.get("evp_ready") and not report.get("required_operator_commands_if_not_ready"):
        return fail("operator commands required when EVP is not ready")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104D_A1EGPAlignmentEVPSourceIntakeOrRerunCrossSourceTriage":
        return fail("next_short_step mismatch")
    expected_stop = "NONE" if summary.get("evp_ready") else "SOURCE_INTAKE_REQUIRED"
    if summary.get("stop_reason") != expected_stop:
        return fail("stop_reason mismatch")
    print("A1 EGP alignment EVP intake diagnostics validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
