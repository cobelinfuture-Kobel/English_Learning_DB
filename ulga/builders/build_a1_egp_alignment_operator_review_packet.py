import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
MATRIX = BASE / "ulga" / "reports" / "a1_egp_alignment_matrix.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_review_packet_summary.json"
TASK_ID = "R7-M102_A1EGPAlignmentMatrixOperatorReview"
DECISION_ORDER = [
    "REVIEW_CREATE_NODE_OR_MARK_OUT_OF_SCOPE",
    "REVIEW_PATCH_EXISTING_NODE_OR_SPLIT_CLUSTER",
    "REVIEW_EXTEND_EXISTING_NODE_EVIDENCE",
    "COVERED_BY_EXISTING_NODE_REFS",
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact_cluster(cluster):
    rows = cluster.get("rows", [])
    missing_rows = [row for row in rows if not row.get("exact_covering_nodes")]
    sample_rows = missing_rows[:3] if missing_rows else rows[:3]
    return {
        "cluster_id": cluster.get("cluster_id"),
        "cluster_key": cluster.get("cluster_key"),
        "super_category": cluster.get("super_category"),
        "sub_category": cluster.get("sub_category"),
        "decision": cluster.get("decision"),
        "row_count": cluster.get("row_count"),
        "covered_row_count": cluster.get("covered_row_count"),
        "missing_row_count": cluster.get("missing_row_count"),
        "suggested_existing_nodes": cluster.get("suggested_existing_nodes", [])[:5],
        "sample_rows_for_review": [
            {
                "source_ref": row.get("source_ref"),
                "row_number": row.get("row_number"),
                "guideword": row.get("guideword"),
                "can_do": row.get("can_do"),
                "example": row.get("example"),
                "semantic_candidate_nodes": row.get("semantic_candidate_nodes", [])[:3],
            }
            for row in sample_rows
        ],
        "operator_action_required": cluster.get("decision") != "COVERED_BY_EXISTING_NODE_REFS",
    }


def main():
    matrix = load(MATRIX)
    clusters = matrix.get("clusters", [])
    review_items = [compact_cluster(cluster) for cluster in clusters]
    review_items.sort(key=lambda item: (DECISION_ORDER.index(item["decision"]), -(item.get("missing_row_count") or 0), item.get("cluster_key") or ""))
    decision_counts = {}
    row_counts = {}
    for item in review_items:
        decision = item["decision"]
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        row_counts[decision] = row_counts.get(decision, 0) + item.get("row_count", 0)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_operator_review_packet",
        "source_artifact_id": matrix.get("artifact_id"),
        "review_mode": "LOCAL_OPERATOR_REVIEW_REQUIRED",
        "review_items": review_items,
        "wrong_level_or_bridge_refs": matrix.get("wrong_level_or_bridge_refs", []),
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_operator_review_packet_summary",
        "validation_status": "PASS",
        "source_cluster_count": len(clusters),
        "review_item_count": len(review_items),
        "operator_action_required_count": sum(1 for item in review_items if item["operator_action_required"]),
        "decision_counts": decision_counts,
        "row_counts_by_decision": row_counts,
        "wrong_level_or_bridge_node_count": len(matrix.get("wrong_level_or_bridge_refs", [])),
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "next_short_step": "R7-M103_A1EGPAlignmentOperatorDecisionPlan",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment operator review packet build: PASS")
    print("Review items:", len(review_items))
    print("Operator action required:", summary["operator_action_required_count"])
    print("Decision counts:", decision_counts)


if __name__ == "__main__":
    main()
