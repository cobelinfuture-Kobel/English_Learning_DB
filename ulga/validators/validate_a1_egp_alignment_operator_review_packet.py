import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PACKET = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_review_packet_summary.json"
TASK_ID = "R7-M102_A1EGPAlignmentMatrixOperatorReview"
VALID_DECISIONS = {
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
    print("Validating A1 EGP alignment operator review packet...")
    packet = load(PACKET)
    summary = load(SUMMARY)
    if not isinstance(packet, dict) or not isinstance(summary, dict):
        return fail("required packet files missing")
    if packet.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = packet.get("review_items", [])
    if not items:
        return fail("review_items missing")
    decision_counts = {}
    row_counts = {}
    action_required = 0
    ids = set()
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        decision = item.get("decision")
        if decision not in VALID_DECISIONS:
            return fail("invalid decision")
        row_count = item.get("row_count", 0)
        covered = item.get("covered_row_count", 0)
        missing = item.get("missing_row_count", 0)
        if row_count != covered + missing:
            return fail("row counts do not add up")
        if item.get("operator_action_required") != (decision != "COVERED_BY_EXISTING_NODE_REFS"):
            return fail("operator_action_required mismatch")
        if item.get("operator_action_required"):
            action_required += 1
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        row_counts[decision] = row_counts.get(decision, 0) + row_count
        if not item.get("sample_rows_for_review"):
            return fail("sample_rows_for_review missing")
    if summary.get("source_cluster_count") != len(items):
        return fail("source_cluster_count mismatch")
    if summary.get("review_item_count") != len(items):
        return fail("review_item_count mismatch")
    if summary.get("operator_action_required_count") != action_required:
        return fail("operator_action_required_count mismatch")
    if summary.get("decision_counts") != decision_counts:
        return fail("decision_counts mismatch")
    if summary.get("row_counts_by_decision") != row_counts:
        return fail("row_counts_by_decision mismatch")
    if packet.get("final_closeout_allowed") is not False or summary.get("final_closeout_allowed") is not False:
        return fail("final closeout must remain false")
    if packet.get("a2_a2plus_progression_allowed") is not False or summary.get("a2_a2plus_progression_allowed") is not False:
        return fail("A2/A2_PLUS progression must remain false")
    if packet.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if packet.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M103_A1EGPAlignmentOperatorDecisionPlan":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_REVIEW_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment operator review packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
