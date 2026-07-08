import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PACKET = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_decision_lane_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_decision_lane_packet_summary.json"
TASK_ID = "R7-M104D_A1EGPAlignmentCrossSourceDecisionFillOrPatchPlan"
VALID_LANES = {"PATCH_EXISTING_NODE_REVIEW_LANE", "CREATE_OR_SPLIT_NODE_REVIEW_LANE"}


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
    print("Validating A1 EGP alignment cross-source decision lane packet...")
    packet = load(PACKET)
    summary = load(SUMMARY)
    if not isinstance(packet, dict) or not isinstance(summary, dict):
        return fail("required lane packet files missing")
    if packet.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = packet.get("lane_items", [])
    if not items:
        return fail("lane_items missing")
    ids = set()
    lane_counts = {}
    lane_missing_rows = {}
    operator_counts = {}
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        lane = item.get("lane")
        if lane not in VALID_LANES:
            return fail("invalid lane")
        has_candidate = bool(item.get("target_existing_node_candidates"))
        if lane == "PATCH_EXISTING_NODE_REVIEW_LANE" and not has_candidate:
            return fail("patch lane item must have existing node candidates")
        if lane == "CREATE_OR_SPLIT_NODE_REVIEW_LANE" and has_candidate:
            return fail("create/split lane item must not have existing node candidates")
        if item.get("operator_decision") != "DEFER_FOR_SOURCE_REVIEW":
            return fail("operator_decision must remain deferred")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("item canonical write must be false")
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        lane_missing_rows[lane] = lane_missing_rows.get(lane, 0) + (item.get("missing_row_count") or 0)
        operator_counts[item.get("operator_decision")] = operator_counts.get(item.get("operator_decision"), 0) + 1
    if summary.get("lane_item_count") != len(items):
        return fail("lane_item_count mismatch")
    if summary.get("lane_counts") != dict(sorted(lane_counts.items())):
        return fail("lane_counts mismatch")
    if summary.get("lane_missing_row_counts") != dict(sorted(lane_missing_rows.items())):
        return fail("lane_missing_row_counts mismatch")
    if summary.get("operator_decision_counts") != operator_counts:
        return fail("operator_decision_counts mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if packet.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if packet.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if packet.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E_A1EGPAlignmentPatchLaneTop10ReviewPacket":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment cross-source decision lane packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
