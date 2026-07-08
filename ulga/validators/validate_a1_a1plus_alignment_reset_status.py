import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
STATUS = BASE / "ulga" / "reports" / "a1_a1plus_alignment_reset_status.json"
EXPECTED_TASK = "R7-M101_RESET_A1_EGPAlignmentMatrixOneShot"


def fail(message):
    print("FAIL: " + message)
    return False


def validate():
    print("Validating A1/A1_PLUS alignment reset status...")
    try:
        data = json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"reset status missing or unreadable: {exc}")
    if data.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if data.get("prior_closeout_status") != "PREMATURE_CLOSEOUT_INVALIDATED":
        return fail("prior closeout must be invalidated")
    if data.get("final_closeout_allowed") is not False:
        return fail("final closeout must remain false")
    if data.get("a2_a2plus_progression_allowed") is not False:
        return fail("A2/A2_PLUS progression must remain false")
    if data.get("egp_a1_row_count") != 109:
        return fail("EGP A1 row count mismatch")
    if data.get("covered_egp_a1_row_count") != 17:
        return fail("covered EGP A1 row count mismatch")
    if data.get("missing_egp_a1_row_count") != 92:
        return fail("missing EGP A1 row count mismatch")
    if data.get("required_next_task") != EXPECTED_TASK:
        return fail("required_next_task mismatch")
    outputs = data.get("required_one_shot_outputs", [])
    if len(outputs) < 5:
        return fail("required one-shot outputs incomplete")
    if data.get("local_validation_required") is not True:
        return fail("local validation must be required")
    if data.get("ci_gate_required") is not False:
        return fail("CI gate must be disabled for this line")
    print("A1/A1_PLUS alignment reset status validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
