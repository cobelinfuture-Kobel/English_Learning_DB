import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
RECLASS = BASE / "ulga" / "reports" / "a1_a1plus_egp_feature_learning_unit_reclassification.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_type_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_type_review_packet_summary.json"
TASK_ID = "R7-M104E4_A1A1PlusLearningUnitTypeReviewPacket"

TYPE_ORDER = [
    "PHRASE_PATTERN_NODE",
    "CONSTRUCTION_NODE",
    "SENTENCE_PATTERN_NODE",
    "MULTI_NODE_COMPOSITE",
    "USAGE_CONSTRAINT",
    "ATOMIC_GRAMMAR_NODE",
    "DEFER_FOR_SOURCE_REVIEW",
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    reclass = load(RECLASS)
    items = reclass.get("reclassification_items", [])
    groups = []
    type_counts = {}
    decision_counts = {}
    operator_required = 0
    by_type = {}
    for item in items:
        lut = item.get("learning_unit_type")
        by_type.setdefault(lut, []).append(item)
        type_counts[lut] = type_counts.get(lut, 0) + 1
        path = item.get("recommended_decision_path")
        decision_counts[path] = decision_counts.get(path, 0) + 1
        if item.get("operator_decision_required"):
            operator_required += 1
    for lut in TYPE_ORDER:
        bucket = by_type.get(lut, [])
        if not bucket:
            continue
        sorted_bucket = sorted(bucket, key=lambda x: (-(x.get("missing_row_count") or 0), x.get("cluster_key") or ""))
        groups.append({
            "learning_unit_type": lut,
            "item_count": len(sorted_bucket),
            "missing_row_count": sum(item.get("missing_row_count") or 0 for item in sorted_bucket),
            "review_priority": "HIGH" if lut != "DEFER_FOR_SOURCE_REVIEW" else "SOURCE_REVIEW_REQUIRED",
            "recommended_operator_question": question_for_type(lut),
            "items": [review_item(item) for item in sorted_bucket],
        })
    no_action_items = [item for item in items if item.get("recommended_decision_path") == "NO_ACTION_REQUIRED"]
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_learning_unit_type_review_packet",
        "source_artifact_id": reclass.get("artifact_id"),
        "review_scope": "A1/A1+ EGP feature learning-unit type classification review",
        "operator_instruction": "Review learning_unit_type and recommended_decision_path before any canonical grammar or pattern writes.",
        "review_groups": groups,
        "no_action_items": [review_item(item) for item in sorted(no_action_items, key=lambda x: x.get("cluster_key") or "")],
        "allowed_next_actions": [
            "APPROVE_LEARNING_UNIT_TYPE_POLICY",
            "ADJUST_LEARNING_UNIT_TYPE_FOR_SELECTED_ITEMS",
            "DEFER_SELECTED_ITEMS_FOR_SOURCE_REVIEW",
        ],
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_learning_unit_type_review_packet_summary",
        "validation_status": "PASS",
        "source_reclassification_item_count": len(items),
        "review_group_count": len(groups),
        "review_item_count": sum(group["item_count"] for group in groups),
        "no_action_item_count": len(no_action_items),
        "learning_unit_type_counts": dict(sorted(type_counts.items())),
        "recommended_decision_path_counts": dict(sorted(decision_counts.items())),
        "operator_decision_required_count": operator_required,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104E5_A1A1PlusLearningUnitTypeOperatorReview",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ learning unit type review packet build: PASS")
    print("Review groups:", len(groups))
    print("Review items:", summary["review_item_count"])
    print("No-action items:", len(no_action_items))
    print("Learning unit types:", summary["learning_unit_type_counts"])


def question_for_type(lut):
    return {
        "ATOMIC_GRAMMAR_NODE": "Confirm whether the feature can safely patch an atomic grammar node.",
        "MULTI_NODE_COMPOSITE": "Confirm whether the feature should patch multiple nodes or create a composite node.",
        "PHRASE_PATTERN_NODE": "Confirm phrase-pattern node type and whether a new phrase-pattern node is needed.",
        "SENTENCE_PATTERN_NODE": "Confirm sentence-pattern node type and required role/slot mapping.",
        "CONSTRUCTION_NODE": "Confirm construction node type and whether examples require verb/clause complement modeling.",
        "USAGE_CONSTRAINT": "Confirm whether this belongs as a usage/countability/reference constraint.",
        "DEFER_FOR_SOURCE_REVIEW": "Review manually; current automatic classification is not safe.",
        "SPLIT_REQUIRED": "Confirm how to split the cluster before mapping.",
    }.get(lut, "Review manually.")


def review_item(item):
    return {
        "cluster_id": item.get("cluster_id"),
        "cluster_key": item.get("cluster_key"),
        "row_count": item.get("row_count"),
        "missing_row_count": item.get("missing_row_count"),
        "learning_unit_type": item.get("learning_unit_type"),
        "recommended_decision_path": item.get("recommended_decision_path"),
        "target_existing_node_candidates": item.get("target_existing_node_candidates", []),
        "classification_rationale": item.get("classification_rationale", []),
        "operator_decision_required": item.get("operator_decision_required"),
        "operator_review_status": "PENDING_OPERATOR_REVIEW" if item.get("operator_decision_required") else "NO_ACTION_REQUIRED",
        "canonical_grammar_write_allowed": False,
    }


if __name__ == "__main__":
    main()
