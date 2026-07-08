import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PACKET = BASE / "ulga" / "reports" / "a1_egp_alignment_patch_lane_top10_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_patch_lane_top10_review_packet_summary.json"
TASK_ID = "R7-M104E_A1EGPAlignmentPatchLaneTop10ReviewPacket"
VALID_DECISIONS = {"PATCH_EXISTING_NODE_EVIDENCE", "SPLIT_CLUSTER_AND_CREATE_NODE", "DEFER_FOR_SOURCE_REVIEW"}


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
    print("Validating A1 EGP alignment patch lane top10 review packet...")
    packet = load(PACKET)
    summary = load(SUMMARY)
    if not isinstance(packet, dict) or not isinstance(summary, dict):
        return fail("required patch lane top10 packet files missing")
    if packet.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = packet.get("review_items", [])
    if len(items) != packet.get("top_n"):
        return fail("review_items count must equal top_n")
    if summary.get("top_priority_item_count") != len(items):
        return fail("top_priority_item_count mismatch")
    ranks = [item.get("priority_rank") for item in items]
    if ranks != list(range(1, len(items) + 1)):
        return fail("priority_rank sequence mismatch")
    ids = set()
    missing_total = 0
    candidate_total = 0
    operator_counts = {}
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        if not item.get("target_existing_node_candidates"):
            return fail("patch lane item must have existing node candidates")
        if item.get("operator_decision") not in VALID_DECISIONS:
            return fail("invalid operator_decision")
        if item.get("operator_decision") != "DEFER_FOR_SOURCE_REVIEW":
            return fail("operator_decision must remain deferred")
        if not set(VALID_DECISIONS).issubset(set(item.get("allowed_operator_decisions", []))):
            return fail("allowed_operator_decisions incomplete")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("canonical write must be false")
        missing_total += item.get("missing_row_count") or 0
        candidate_total += len(item.get("target_existing_node_candidates", []))
        operator_counts[item.get("operator_decision")] = operator_counts.get(item.get("operator_decision"), 0) + 1
    if summary.get("top_priority_missing_row_count") != missing_total:
        return fail("top_priority_missing_row_count mismatch")
    if summary.get("existing_node_candidate_total") != candidate_total:
        return fail("existing_node_candidate_total mismatch")
    if summary.get("operator_decision_counts") != operator_counts:
        return fail("operator_decision_counts mismatch")
    if summary.get("source_patch_lane_count", 0) < len(items):
        return fail("source_patch_lane_count too small")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if packet.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if packet.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if packet.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104F_A1EGPAlignmentPatchLaneTop10OperatorDecisionFill":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_DECISION_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment patch lane top10 review packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
