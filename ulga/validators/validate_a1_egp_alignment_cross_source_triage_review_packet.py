import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PACKET = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage_review_packet_summary.json"
TASK_ID = "R7-M104C_A1EGPAlignmentCrossSourceTriageReviewPacket"
VALID_OPERATOR_DECISIONS = {
    "PATCH_EXISTING_NODE_EVIDENCE",
    "CREATE_NEW_GRAMMAR_NODE",
    "SPLIT_CLUSTER_AND_CREATE_NODE",
    "DEFER_FOR_SOURCE_REVIEW",
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
    print("Validating A1 EGP alignment cross-source triage review packet...")
    packet = load(PACKET)
    summary = load(SUMMARY)
    if not isinstance(packet, dict) or not isinstance(summary, dict):
        return fail("required review packet files missing")
    if packet.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = packet.get("review_items", [])
    if packet.get("review_item_count") != len(items) or summary.get("review_item_count") != len(items):
        return fail("review_item_count mismatch")
    if not items:
        return fail("review_items missing")
    ids = set()
    confidence_counts = {}
    candidate_counts = {"has_existing_node_candidate": 0, "no_existing_node_candidate": 0}
    operator_counts = {}
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        if item.get("cross_source_recommendation") != "REVIEW_CREATE_OR_PATCH_WITH_USAGE_AND_EXAM_SUPPORT":
            return fail("unexpected cross-source recommendation")
        if item.get("evp_match", {}).get("status") != "MATCH":
            return fail("EVP must match for every review item")
        if item.get("raz_usage_match", {}).get("status") != "MATCH":
            return fail("RAZ must match for every review item")
        if item.get("cambridge_exam_match", {}).get("status") != "MATCH":
            return fail("Cambridge must match for every review item")
        if item.get("operator_decision") not in VALID_OPERATOR_DECISIONS:
            return fail("invalid operator_decision")
        if not set(VALID_OPERATOR_DECISIONS).issubset(set(item.get("allowed_operator_decisions", []))):
            return fail("allowed_operator_decisions incomplete")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("item canonical write must be false")
        confidence_counts[item.get("confidence")] = confidence_counts.get(item.get("confidence"), 0) + 1
        operator_counts[item.get("operator_decision")] = operator_counts.get(item.get("operator_decision"), 0) + 1
        if item.get("target_existing_node_candidates"):
            candidate_counts["has_existing_node_candidate"] += 1
        else:
            candidate_counts["no_existing_node_candidate"] += 1
    if summary.get("confidence_counts") != dict(sorted(confidence_counts.items())):
        return fail("confidence_counts mismatch")
    if summary.get("candidate_status_counts") != candidate_counts:
        return fail("candidate_status_counts mismatch")
    if summary.get("operator_decision_counts") != operator_counts:
        return fail("operator_decision_counts mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if packet.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if packet.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if packet.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104D_A1EGPAlignmentCrossSourceDecisionFillOrPatchPlan":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_DECISION_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment cross-source triage review packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
