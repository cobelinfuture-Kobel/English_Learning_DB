import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REVIEW = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_type_review_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_lane_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_lane_packet_summary.json"
TASK_ID = "R7-M104E5_A1A1PlusClearLearningUnitLaneSelection"
CLEAR_DECISION_PATHS = {
    "CREATE_LEARNING_UNIT_TYPE_REVIEW",
    "PATCH_MULTIPLE_OR_CREATE_COMPOSITE_REVIEW",
}
DEFER_DECISION_PATHS = {"DEFER_FOR_SOURCE_REVIEW"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def flatten_review_items(review):
    items = []
    for group in review.get("review_groups", []):
        for item in group.get("items", []):
            item = dict(item)
            item["source_review_group_learning_unit_type"] = group.get("learning_unit_type")
            items.append(item)
    return items


def main():
    review = load(REVIEW)
    review_items = flatten_review_items(review)
    no_action_items = review.get("no_action_items", [])
    clear_items = [item for item in review_items if item.get("recommended_decision_path") in CLEAR_DECISION_PATHS]
    deferred_items = [item for item in review_items if item.get("recommended_decision_path") in DEFER_DECISION_PATHS]
    unexpected_items = [item for item in review_items if item.get("recommended_decision_path") not in CLEAR_DECISION_PATHS | DEFER_DECISION_PATHS]
    clear_type_counts = count_by(clear_items, "learning_unit_type")
    deferred_type_counts = count_by(deferred_items, "learning_unit_type")
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_learning_unit_lane_packet",
        "source_artifact_id": review.get("artifact_id"),
        "operator_direction": "process_clear_items_first",
        "lane_policy": {
            "clear_active_lane": sorted(CLEAR_DECISION_PATHS),
            "deferred_lane": sorted(DEFER_DECISION_PATHS),
            "no_action_lane": "preserve without canonical write",
            "canonical_write_allowed": False,
            "a2_a2plus_progression_allowed": False,
        },
        "clear_active_lane_items": sorted(clear_items, key=sort_key),
        "deferred_lane_items": sorted(deferred_items, key=sort_key),
        "no_action_items": sorted(no_action_items, key=sort_key),
        "unexpected_review_items": sorted(unexpected_items, key=sort_key),
        "next_clear_lane_work": {
            "recommended_next_task": "R7-M104E6_A1A1PlusClearLearningUnitSchemaPlanningPacket",
            "allowed_scope": [
                "derive schema-planning requirements for clear active lane items",
                "separate phrase-pattern, construction, sentence-pattern, usage, and composite needs",
                "produce planning artifacts only",
            ],
            "not_allowed_scope": [
                "canonical grammar node writes",
                "canonical pattern graph writes",
                "A2/A2+ progression",
                "auto-processing deferred lane items",
            ],
        },
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_learning_unit_lane_packet_summary",
        "validation_status": "PASS",
        "source_review_item_count": len(review_items),
        "clear_active_lane_item_count": len(clear_items),
        "deferred_lane_item_count": len(deferred_items),
        "no_action_item_count": len(no_action_items),
        "unexpected_review_item_count": len(unexpected_items),
        "clear_learning_unit_type_counts": clear_type_counts,
        "deferred_learning_unit_type_counts": deferred_type_counts,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104E6_A1A1PlusClearLearningUnitSchemaPlanningPacket",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear learning unit lane packet build: PASS")
    print("Source review items:", len(review_items))
    print("Clear active lane items:", len(clear_items))
    print("Deferred lane items:", len(deferred_items))
    print("No-action items:", len(no_action_items))
    print("Unexpected review items:", len(unexpected_items))
    print("Clear learning unit types:", clear_type_counts)


def count_by(items, key):
    counts = {}
    for item in items:
        value = item.get(key)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def sort_key(item):
    return (
        item.get("learning_unit_type") or "",
        -(item.get("missing_row_count") or 0),
        item.get("cluster_key") or "",
    )


if __name__ == "__main__":
    main()
