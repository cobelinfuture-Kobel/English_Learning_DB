import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_egp_alignment_matrix.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_matrix_summary.json"
RESET = BASE / "ulga" / "reports" / "a1_a1plus_alignment_reset_status.json"
TASK_ID = "R7-M101_RESET_A1_EGPAlignmentMatrixOneShot"
REQUIRED_DECISIONS = {
    "COVERED_BY_EXISTING_NODE_REFS",
    "REVIEW_EXTEND_EXISTING_NODE_EVIDENCE",
    "REVIEW_PATCH_EXISTING_NODE_OR_SPLIT_CLUSTER",
    "REVIEW_CREATE_NODE_OR_MARK_OUT_OF_SCOPE",
}


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
    print("Validating A1 EGP alignment matrix one-shot audit...")
    report = load(REPORT)
    summary = load(SUMMARY)
    reset = load(RESET)
    if not isinstance(report, dict) or not isinstance(summary, dict) or not isinstance(reset, dict):
        return fail("required audit files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    if reset.get("prior_closeout_status") != "PREMATURE_CLOSEOUT_INVALIDATED":
        return fail("reset status not invalidated")
    if report.get("egp_a1_row_count") != 109 or summary.get("egp_a1_row_count") != 109:
        return fail("EGP A1 row count mismatch")
    if report.get("a1_a1plus_node_count") != 15 or summary.get("a1_a1plus_node_count") != 15:
        return fail("A1/A1_PLUS node count mismatch")
    clusters = report.get("clusters", [])
    if not clusters:
        return fail("clusters missing")
    row_total = 0
    decision_counts = {}
    for cluster in clusters:
        decision = cluster.get("decision")
        if decision not in REQUIRED_DECISIONS:
            return fail("invalid cluster decision")
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        row_count = cluster.get("row_count")
        covered = cluster.get("covered_row_count")
        missing = cluster.get("missing_row_count")
        if row_count != covered + missing:
            return fail("cluster row counts do not add up")
        rows = cluster.get("rows", [])
        if row_count != len(rows):
            return fail("cluster rows length mismatch")
        row_total += row_count
    if row_total != 109:
        return fail("cluster row total must equal EGP A1 row count")
    if summary.get("cluster_count") != len(clusters):
        return fail("cluster_count mismatch")
    if summary.get("decision_counts") != dict(sorted(decision_counts.items())):
        return fail("decision_counts mismatch")
    if report.get("final_closeout_allowed") is not False or summary.get("final_closeout_allowed") is not False:
        return fail("final closeout must remain false")
    if report.get("a2_a2plus_progression_allowed") is not False or summary.get("a2_a2plus_progression_allowed") is not False:
        return fail("A2/A2_PLUS progression must remain false")
    if report.get("local_validation_required") is not True:
        return fail("local validation must be required")
    if report.get("ci_gate_required") is not False:
        return fail("CI gate must be disabled")
    if summary.get("next_short_step") != "R7-M102_A1EGPAlignmentMatrixOperatorReview":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1 EGP alignment matrix one-shot audit validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
