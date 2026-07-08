import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
A1_CLOSEOUT = BASE / "docs" / "ulga" / "R7_M100_A1A1PLUS_LEVEL_BAND_CLOSEOUT.md"
A1_AUDIT_SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_egp_rule_coverage_audit_summary.json"
GATE_REPORT = BASE / "ulga" / "reports" / "level_band_closeout_gate_status.json"
TASK_ID = "R7-M100C_LevelBandCloseoutGateValidator"


def write(data):
    GATE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    GATE_REPORT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def validate():
    print("Validating level-band closeout gates...")
    closeout_exists = A1_CLOSEOUT.exists()
    audit = load(A1_AUDIT_SUMMARY)
    audit_exists = isinstance(audit, dict)
    audit_pass = audit_exists and audit.get("validation_status") == "PASS"
    final_allowed = audit_exists and audit.get("final_closeout_allowed") is True
    status = {
        "task_id": TASK_ID,
        "artifact_id": "level_band_closeout_gate_status",
        "level_band": "A1+A1_PLUS",
        "closeout_doc_exists": closeout_exists,
        "egp_rule_coverage_audit_exists": audit_exists,
        "egp_rule_coverage_audit_pass": audit_pass,
        "final_closeout_allowed": final_allowed,
        "gate_status": "BLOCKED" if closeout_exists and not final_allowed else "PASS",
        "blocker": None if final_allowed else "EGP_RULE_COVERAGE_AUDIT_AND_THRESHOLD_POLICY_REQUIRED",
        "next_short_step": "R7-M100D_EGPCompactIndexV2DesignPatch",
        "stop_reason": "NONE",
    }
    write(status)
    if closeout_exists and not audit_exists:
        print("FAIL: closeout exists without EGP rule coverage audit")
        return False
    print("Level-band closeout gate validation: PASS_WITH_BLOCKED_FINAL_CLOSEOUT" if not final_allowed else "PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
