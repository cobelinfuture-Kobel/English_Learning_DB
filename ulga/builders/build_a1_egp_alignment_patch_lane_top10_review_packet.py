import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
LANE = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_decision_lane_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_patch_lane_top10_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_patch_lane_top10_review_packet_summary.json"
TASK_ID = "R7-M104E_A1EGPAlignmentPatchLaneTop10ReviewPacket"
TOP_N = 10
PATCH_LANE = "PATCH_EXISTING_NODE_REVIEW_LANE"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    lane = load(LANE)
    patch_items = [item for item in lane.get("lane_items", []) if item.get("lane") == PATCH_LANE]
    selected = sorted(patch_items, key=lambda item: (-(item.get("missing_row_count") or 0), item.get("cluster_key") or ""))[:TOP_N]
    review_items = []
    for rank, item in enumerate(selected, start=1):
        review_items.append({
            "priority_rank": rank,
            "cluster_id": item.get("cluster_id"),
            "cluster_key": item.get("cluster_key"),
            "missing_row_count": item.get("missing_row_count"),
            "row_count": item.get("row_count"),
            "confidence": item.get("confidence"),
            "target_existing_node_candidates": item.get("target_existing_node_candidates", []),
            "selected_source_refs_preview": item.get("selected_source_refs_preview", []),
            "allowed_operator_decisions": [
                "PATCH_EXISTING_NODE_EVIDENCE",
                "SPLIT_CLUSTER_AND_CREATE_NODE",
                "DEFER_FOR_SOURCE_REVIEW",
            ],
            "default_operator_decision": "PATCH_EXISTING_NODE_EVIDENCE",
            "operator_decision": "DEFER_FOR_SOURCE_REVIEW",
            "selected_target_node": None,
            "operator_note": "Choose target node to patch, or split/create if existing candidates are semantically wrong.",
            "canonical_grammar_write_allowed": False,
        })
    candidate_total = sum(len(item.get("target_existing_node_candidates", [])) for item in review_items)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_patch_lane_top10_review_packet",
        "source_artifact_id": lane.get("artifact_id"),
        "top_n": TOP_N,
        "selection_policy": "patch lane only, highest missing_row_count first",
        "review_items": review_items,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_patch_lane_top10_review_packet_summary",
        "validation_status": "PASS",
        "source_patch_lane_count": len(patch_items),
        "top_priority_item_count": len(review_items),
        "top_priority_missing_row_count": sum(item.get("missing_row_count", 0) for item in review_items),
        "existing_node_candidate_total": candidate_total,
        "operator_decision_counts": {"DEFER_FOR_SOURCE_REVIEW": len(review_items)},
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104F_A1EGPAlignmentPatchLaneTop10OperatorDecisionFill",
        "stop_reason": "OPERATOR_DECISION_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment patch lane top10 review packet build: PASS")
    print("Source patch lane items:", len(patch_items))
    print("Top priority items:", len(review_items))
    print("Top priority missing rows:", summary["top_priority_missing_row_count"])
    print("Existing node candidate total:", candidate_total)


if __name__ == "__main__":
    main()
