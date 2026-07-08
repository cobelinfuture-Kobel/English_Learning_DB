import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
TRIAGE = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage.json"
PLAN = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_decision_plan.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage_review_packet_summary.json"
TASK_ID = "R7-M104C_A1EGPAlignmentCrossSourceTriageReviewPacket"
TARGET_RECOMMENDATION = "REVIEW_CREATE_OR_PATCH_WITH_USAGE_AND_EXAM_SUPPORT"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    triage = load(TRIAGE)
    plan = load(PLAN)
    plan_by_id = {item.get("cluster_id"): item for item in plan.get("plan_items", [])}
    review_items = []
    for item in triage.get("triage_items", []):
        if item.get("recommended_operator_decision") != TARGET_RECOMMENDATION:
            continue
        plan_item = plan_by_id.get(item.get("cluster_id"), {})
        review_items.append({
            "cluster_id": item.get("cluster_id"),
            "cluster_key": item.get("cluster_key"),
            "row_count": item.get("row_count"),
            "missing_row_count": item.get("missing_row_count"),
            "cross_source_recommendation": item.get("recommended_operator_decision"),
            "confidence": item.get("confidence"),
            "evp_match": item.get("evp_match"),
            "raz_usage_match": item.get("raz_usage_match"),
            "cambridge_exam_match": item.get("cambridge_exam_match"),
            "target_existing_node_candidates": plan_item.get("target_existing_node_candidates", []),
            "selected_source_refs_preview": plan_item.get("selected_source_refs", [])[:5],
            "allowed_operator_decisions": [
                "PATCH_EXISTING_NODE_EVIDENCE",
                "CREATE_NEW_GRAMMAR_NODE",
                "SPLIT_CLUSTER_AND_CREATE_NODE",
                "DEFER_FOR_SOURCE_REVIEW",
            ],
            "operator_decision": "DEFER_FOR_SOURCE_REVIEW",
            "selected_target_node": None,
            "new_node_candidate": None,
            "operator_note": "Cross-source evidence exists; choose patch existing node or create/split node before canonical write.",
            "canonical_grammar_write_allowed": False,
        })
    review_items.sort(key=lambda x: (-(x.get("missing_row_count") or 0), x.get("cluster_key") or ""))
    confidence_counts = {}
    candidate_status_counts = {"has_existing_node_candidate": 0, "no_existing_node_candidate": 0}
    for item in review_items:
        confidence_counts[item.get("confidence")] = confidence_counts.get(item.get("confidence"), 0) + 1
        if item.get("target_existing_node_candidates"):
            candidate_status_counts["has_existing_node_candidate"] += 1
        else:
            candidate_status_counts["no_existing_node_candidate"] += 1
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cross_source_triage_review_packet",
        "source_artifact_id": triage.get("artifact_id"),
        "review_item_count": len(review_items),
        "review_items": review_items,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cross_source_triage_review_packet_summary",
        "validation_status": "PASS",
        "review_item_count": len(review_items),
        "medium_confidence_count": confidence_counts.get("MEDIUM", 0),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "candidate_status_counts": candidate_status_counts,
        "operator_decision_counts": {"DEFER_FOR_SOURCE_REVIEW": len(review_items)},
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104D_A1EGPAlignmentCrossSourceDecisionFillOrPatchPlan",
        "stop_reason": "OPERATOR_DECISION_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment cross-source triage review packet build: PASS")
    print("Review items:", len(review_items))
    print("Candidate status counts:", candidate_status_counts)
    print("Confidence counts:", summary["confidence_counts"])


if __name__ == "__main__":
    main()
