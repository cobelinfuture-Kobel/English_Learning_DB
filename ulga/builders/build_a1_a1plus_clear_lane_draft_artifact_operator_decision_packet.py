import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REVIEW_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_review_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet_summary.json"
TASK_ID = "R7-M104E12_A1A1PlusClearLaneDraftArtifactOperatorReviewDecisionPacket"
DECISION = "ADJUST_DRAFT_FIELDS_BEFORE_PROMOTION_PLANNING"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_by(items, key_fn):
    counts = {}
    for item in items:
        key = key_fn(item)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def iter_review_items(review_packet):
    for group in review_packet.get("review_groups", []):
        for item in group.get("items", []):
            yield item


def decision_item(item):
    placeholder_fields = item.get("placeholder_fields", [])
    return {
        "decision_item_id": "decision_" + item.get("review_item_id", "unknown"),
        "review_item_id": item.get("review_item_id"),
        "artifact_id": item.get("artifact_id"),
        "learning_unit_id": item.get("learning_unit_id"),
        "learning_unit_type": item.get("learning_unit_type"),
        "source_cluster": item.get("source_cluster", {}),
        "schema_contract_path": item.get("schema_contract_path"),
        "operator_decision": DECISION,
        "decision_reason": "draft artifact contains placeholder fields or draft-only examples; complete fields before promotion planning",
        "placeholder_fields_to_complete": placeholder_fields,
        "placeholder_field_count": len(placeholder_fields),
        "allowed_next_action": "FIELD_COMPLETION_PLANNING_ONLY",
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "deferred_lane_processing_allowed": False,
    }


def main():
    review_packet = load(REVIEW_PACKET)
    review_items = list(iter_review_items(review_packet))
    if len(review_items) != 19:
        raise ValueError(f"Expected 19 review items, got {len(review_items)}")
    decisions = [decision_item(item) for item in sorted(review_items, key=lambda item: (item.get("learning_unit_type") or "", item.get("artifact_id") or ""))]
    groups = []
    for lut in sorted(set(item["learning_unit_type"] for item in decisions)):
        group_items = [item for item in decisions if item["learning_unit_type"] == lut]
        groups.append({
            "learning_unit_type": lut,
            "decision_item_count": len(group_items),
            "placeholder_field_total": sum(item["placeholder_field_count"] for item in group_items),
            "items": group_items,
        })
    total_placeholder_fields = sum(item["placeholder_field_count"] for item in decisions)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet",
        "source_artifact_id": review_packet.get("artifact_id"),
        "operator_decision_scope": "19 A1/A1+ clear-lane draft artifacts",
        "operator_decision_policy": {
            "decision": DECISION,
            "promotion_planning_allowed_now": False,
            "promotion_allowed_now": False,
            "field_completion_planning_allowed": True,
            "canonical_grammar_write_allowed": False,
            "canonical_pattern_write_allowed": False,
            "deferred_lane_processing_allowed": False,
            "a2_a2plus_progression_allowed": False,
        },
        "decision_groups": groups,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet_summary",
        "validation_status": "PASS",
        "source_review_item_count": len(review_items),
        "decision_group_count": len(groups),
        "decision_item_count": len(decisions),
        "learning_unit_type_counts": count_by(decisions, lambda item: item["learning_unit_type"]),
        "operator_decision_counts": count_by(decisions, lambda item: item["operator_decision"]),
        "allowed_next_action_counts": count_by(decisions, lambda item: item["allowed_next_action"]),
        "total_placeholder_field_count": total_placeholder_fields,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "field_completion_planning_allowed": True,
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E13_A1A1PlusClearLaneDraftFieldCompletionPlanningPacket",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear lane draft artifact operator decision packet build: PASS")
    print("Decision items:", len(decisions))
    print("Operator decisions:", summary["operator_decision_counts"])
    print("Total placeholder fields:", total_placeholder_fields)


if __name__ == "__main__":
    main()
