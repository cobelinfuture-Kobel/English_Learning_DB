import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
LANE = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_lane_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_planning_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_planning_packet_summary.json"
TASK_ID = "R7-M104E6_A1A1PlusClearLearningUnitSchemaPlanningPacket"

SCHEMA_REQUIREMENTS = {
    "PHRASE_PATTERN_NODE": {
        "schema_family": "phrase_pattern_schema",
        "required_fields": [
            "learning_unit_id",
            "cefr_level",
            "egp_cluster_refs",
            "phrase_head_type",
            "slot_model",
            "constraints",
            "positive_examples",
            "negative_examples",
            "source_refs",
        ],
        "planning_focus": "noun/adjective/preposition/determiner phrase pattern representation",
    },
    "SENTENCE_PATTERN_NODE": {
        "schema_family": "sentence_pattern_schema",
        "required_fields": [
            "learning_unit_id",
            "cefr_level",
            "egp_cluster_refs",
            "sentence_role_model",
            "slot_sequence",
            "transformations",
            "positive_examples",
            "negative_examples",
            "source_refs",
        ],
        "planning_focus": "sentence role, slot, order, and transform representation",
    },
    "CONSTRUCTION_NODE": {
        "schema_family": "construction_schema",
        "required_fields": [
            "learning_unit_id",
            "cefr_level",
            "egp_cluster_refs",
            "construction_type",
            "head_pattern",
            "complement_model",
            "constraints",
            "positive_examples",
            "negative_examples",
            "source_refs",
        ],
        "planning_focus": "verb/clause/complement construction representation",
    },
    "USAGE_CONSTRAINT": {
        "schema_family": "usage_constraint_schema",
        "required_fields": [
            "learning_unit_id",
            "cefr_level",
            "egp_cluster_refs",
            "constraint_type",
            "applies_to",
            "allowed_values",
            "blocked_values",
            "examples",
            "source_refs",
        ],
        "planning_focus": "countability/reference/quantity/distribution constraint representation",
    },
    "MULTI_NODE_COMPOSITE": {
        "schema_family": "composite_learning_unit_schema",
        "required_fields": [
            "learning_unit_id",
            "cefr_level",
            "egp_cluster_refs",
            "component_node_refs",
            "composition_rule",
            "role_mapping",
            "positive_examples",
            "negative_examples",
            "source_refs",
        ],
        "planning_focus": "multi-node composition and role mapping representation",
    },
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    lane = load(LANE)
    clear_items = lane.get("clear_active_lane_items", [])
    schema_groups = []
    schema_family_counts = {}
    item_count_by_type = {}
    for learning_unit_type, requirement in SCHEMA_REQUIREMENTS.items():
        items = [item for item in clear_items if item.get("learning_unit_type") == learning_unit_type]
        if not items:
            continue
        family = requirement["schema_family"]
        schema_family_counts[family] = len(items)
        item_count_by_type[learning_unit_type] = len(items)
        schema_groups.append({
            "learning_unit_type": learning_unit_type,
            "schema_family": family,
            "item_count": len(items),
            "planning_focus": requirement["planning_focus"],
            "required_fields": requirement["required_fields"],
            "items": [schema_plan_item(item, requirement) for item in sorted(items, key=sort_key)],
        })
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_learning_unit_schema_planning_packet",
        "source_artifact_id": lane.get("artifact_id"),
        "planning_scope": "schema planning only for A1/A1+ clear active learning-unit lane",
        "schema_groups": schema_groups,
        "deferred_lane_policy": {
            "deferred_lane_items_preserved": len(lane.get("deferred_lane_items", [])),
            "deferred_lane_processing_allowed": False,
        },
        "not_allowed_scope": [
            "canonical grammar node writes",
            "canonical pattern graph writes",
            "source evidence override",
            "A2/A2+ progression",
            "deferred lane processing",
        ],
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_learning_unit_schema_planning_packet_summary",
        "validation_status": "PASS",
        "source_clear_active_lane_item_count": len(clear_items),
        "schema_group_count": len(schema_groups),
        "schema_planning_item_count": sum(group["item_count"] for group in schema_groups),
        "schema_family_counts": dict(sorted(schema_family_counts.items())),
        "learning_unit_type_counts": dict(sorted(item_count_by_type.items())),
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E7_A1A1PlusClearLearningUnitSchemaPlanReview",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear learning unit schema planning packet build: PASS")
    print("Source clear active lane items:", len(clear_items))
    print("Schema groups:", len(schema_groups))
    print("Schema planning items:", summary["schema_planning_item_count"])
    print("Schema families:", summary["schema_family_counts"])


def schema_plan_item(item, requirement):
    return {
        "cluster_id": item.get("cluster_id"),
        "cluster_key": item.get("cluster_key"),
        "missing_row_count": item.get("missing_row_count"),
        "learning_unit_type": item.get("learning_unit_type"),
        "schema_family": requirement["schema_family"],
        "planning_focus": requirement["planning_focus"],
        "required_fields": requirement["required_fields"],
        "recommended_decision_path": item.get("recommended_decision_path"),
        "target_existing_node_candidates": item.get("target_existing_node_candidates", []),
        "classification_rationale": item.get("classification_rationale", []),
        "operator_schema_review_status": "PENDING_OPERATOR_REVIEW",
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
    }


def sort_key(item):
    return (-(item.get("missing_row_count") or 0), item.get("cluster_key") or "")


if __name__ == "__main__":
    main()
