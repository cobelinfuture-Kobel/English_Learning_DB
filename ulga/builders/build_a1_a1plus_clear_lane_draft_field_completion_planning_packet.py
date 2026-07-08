import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DECISION_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_planning_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_planning_packet_summary.json"
TASK_ID = "R7-M104E13_A1A1PlusClearLaneDraftFieldCompletionPlanningPacket"

FIELD_COMPLETION_GUIDANCE = {
    "positive_examples": {
        "completion_kind": "source_grounded_positive_example",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "EVP_SUPPORT", "RAZ_SUPPORT", "CAMBRIDGE_EXAM_CONTEXT"],
    },
    "negative_examples": {
        "completion_kind": "contrast_or_boundary_example",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "EVP_SUPPORT", "OPERATOR_REVIEWED_CONTRAST"],
    },
    "examples": {
        "completion_kind": "source_grounded_usage_example",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "EVP_SUPPORT", "RAZ_SUPPORT"],
    },
    "slot_model": {
        "completion_kind": "phrase_slot_model",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "EVP_SUPPORT", "OPERATOR_REVIEWED_PATTERN"],
    },
    "sentence_role_model": {
        "completion_kind": "sentence_role_model",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "OPERATOR_REVIEWED_PATTERN"],
    },
    "slot_sequence": {
        "completion_kind": "sentence_slot_sequence",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "OPERATOR_REVIEWED_PATTERN"],
    },
    "head_pattern": {
        "completion_kind": "construction_head_pattern",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "EVP_SUPPORT", "OPERATOR_REVIEWED_PATTERN"],
    },
    "complement_model": {
        "completion_kind": "construction_complement_model",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "EVP_SUPPORT", "OPERATOR_REVIEWED_PATTERN"],
    },
    "component_node_refs": {
        "completion_kind": "component_node_reference_selection",
        "evidence_required": True,
        "source_priority": ["EXISTING_NODE_CANDIDATES", "OPERATOR_REVIEWED_NODE_REF"],
    },
    "composition_rule": {
        "completion_kind": "composite_rule_definition",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "OPERATOR_REVIEWED_COMPOSITION_RULE"],
    },
    "role_mapping": {
        "completion_kind": "composite_role_mapping",
        "evidence_required": True,
        "source_priority": ["EGP_ROW", "OPERATOR_REVIEWED_ROLE_MAP"],
    },
}


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


def iter_decision_items(packet):
    for group in packet.get("decision_groups", []):
        for item in group.get("items", []):
            yield item


def field_task(item, field_name):
    guidance = FIELD_COMPLETION_GUIDANCE.get(field_name, {
        "completion_kind": "operator_reviewed_field_completion",
        "evidence_required": True,
        "source_priority": ["OPERATOR_REVIEWED_SOURCE"],
    })
    return {
        "field_name": field_name,
        "completion_kind": guidance["completion_kind"],
        "evidence_required": guidance["evidence_required"],
        "source_priority": guidance["source_priority"],
        "field_completion_status": "SOURCE_EVIDENCE_REQUIRED",
        "implementation_allowed_now": False,
        "canonical_write_allowed": False,
    }


def planning_item(item):
    fields = item.get("placeholder_fields_to_complete", [])
    return {
        "planning_item_id": "plan_" + item.get("decision_item_id", "unknown"),
        "decision_item_id": item.get("decision_item_id"),
        "artifact_id": item.get("artifact_id"),
        "learning_unit_id": item.get("learning_unit_id"),
        "learning_unit_type": item.get("learning_unit_type"),
        "source_cluster": item.get("source_cluster", {}),
        "schema_contract_path": item.get("schema_contract_path"),
        "operator_decision": item.get("operator_decision"),
        "allowed_next_action": item.get("allowed_next_action"),
        "field_completion_status": "PLANNED_NOT_IMPLEMENTED",
        "placeholder_fields_to_complete": fields,
        "placeholder_field_count": len(fields),
        "field_completion_tasks": [field_task(item, field) for field in fields],
        "source_evidence_selection_required": True,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
    }


def main():
    decision_packet = load(DECISION_PACKET)
    decision_items = list(iter_decision_items(decision_packet))
    if len(decision_items) != 19:
        raise ValueError(f"Expected 19 decision items, got {len(decision_items)}")
    planning_items = [planning_item(item) for item in sorted(decision_items, key=lambda item: (item.get("learning_unit_type") or "", item.get("artifact_id") or ""))]
    groups = []
    for lut in sorted(set(item["learning_unit_type"] for item in planning_items)):
        group_items = [item for item in planning_items if item["learning_unit_type"] == lut]
        groups.append({
            "learning_unit_type": lut,
            "planning_item_count": len(group_items),
            "field_completion_task_count": sum(len(item["field_completion_tasks"]) for item in group_items),
            "placeholder_field_total": sum(item["placeholder_field_count"] for item in group_items),
            "items": group_items,
        })
    all_tasks = [task for item in planning_items for task in item["field_completion_tasks"]]
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_field_completion_planning_packet",
        "source_artifact_id": decision_packet.get("artifact_id"),
        "planning_scope": "field completion planning for 19 A1/A1+ clear-lane draft learning-unit artifacts",
        "planning_groups": groups,
        "planning_policy": {
            "field_completion_implementation_allowed_now": False,
            "source_evidence_selection_required": True,
            "draft_artifact_update_allowed_now": False,
            "promotion_planning_allowed_now": False,
            "promotion_allowed_now": False,
            "canonical_grammar_write_allowed": False,
            "canonical_pattern_write_allowed": False,
            "deferred_lane_processing_allowed": False,
            "a2_a2plus_progression_allowed": False,
        },
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_field_completion_planning_packet_summary",
        "validation_status": "PASS",
        "source_decision_item_count": len(decision_items),
        "planning_group_count": len(groups),
        "planning_item_count": len(planning_items),
        "learning_unit_type_counts": count_by(planning_items, lambda item: item["learning_unit_type"]),
        "field_completion_status_counts": count_by(planning_items, lambda item: item["field_completion_status"]),
        "field_completion_task_count": len(all_tasks),
        "field_completion_task_kind_counts": count_by(all_tasks, lambda task: task["completion_kind"]),
        "total_placeholder_field_count": sum(item["placeholder_field_count"] for item in planning_items),
        "source_evidence_selection_required": True,
        "field_completion_implementation_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E14_A1A1PlusClearLaneDraftFieldCompletionSourceEvidenceSelection",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear lane draft field completion planning packet build: PASS")
    print("Planning items:", len(planning_items))
    print("Field completion tasks:", len(all_tasks))
    print("Source evidence selection required:", summary["source_evidence_selection_required"])


if __name__ == "__main__":
    main()
