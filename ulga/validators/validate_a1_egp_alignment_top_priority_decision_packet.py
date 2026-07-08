import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PACKET = BASE / "ulga" / "reports" / "a1_egp_alignment_top_priority_decision_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_top_priority_decision_packet_summary.json"
TASK_ID = "R7-M104A_A1EGPAlignmentTopPriorityDecisionPacket"


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
    print("Validating A1 EGP alignment top priority decision packet...")
    packet = load(PACKET)
    summary = load(SUMMARY)
    if not isinstance(packet, dict) or not isinstance(summary, dict):
        return fail("required top priority packet files missing")
    if packet.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = packet.get("packet_items", [])
    if len(items) != packet.get("top_n"):
        return fail("packet_items count must equal top_n")
    if summary.get("top_priority_item_count") != len(items):
        return fail("top_priority_item_count mismatch")
    ranks = [item.get("priority_rank") for item in items]
    if ranks != list(range(1, len(items) + 1)):
        return fail("priority ranks must be sequential")
    ids = set()
    action_counts = {}
    missing_total = 0
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        if item.get("operator_decision") == "NO_ACTION_REQUIRED":
            return fail("top priority packet must require operator decisions")
        missing = item.get("missing_row_count", 0)
        if missing <= 0:
            return fail("top priority item must have missing rows")
        missing_total += missing
        if not item.get("required_fill_fields"):
            return fail("required_fill_fields missing")
        action = item.get("proposed_action")
        action_counts[action] = action_counts.get(action, 0) + 1
    if summary.get("top_priority_missing_row_count") != missing_total:
        return fail("top priority missing row count mismatch")
    if summary.get("proposed_action_counts") != dict(sorted(action_counts.items())):
        return fail("proposed action counts mismatch")
    if summary.get("source_operator_fill_required_count", 0) < len(items):
        return fail("source operator fill count too small")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if packet.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if packet.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if packet.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104B_A1EGPAlignmentTopPriorityOperatorDecisionFill":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_DECISION_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment top priority decision packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
