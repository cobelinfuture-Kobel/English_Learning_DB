import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SELECTION_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_design_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_design_packet_summary.json"
TASK_ID = "R7-M104E15_A1A1PlusClearLaneDraftFieldCompletionDesignPacket"
POLICY_NAME = "BALANCED_SOURCE_GROUNDED"

DESIGN_RULES = {
    "source_grounded_positive_example": {
        "design_method": "select_or_write_source_grounded_positive_example",
        "completion_value_shape": "array_of_short_a1_examples_with_source_refs",
        "operator_review_required": True,
    },
    "source_grounded_usage_example": {
        "design_method": "select_or_write_source_grounded_usage_example",
        "completion_value_shape": "array_of_short_a1_usage_examples_with_source_refs",
        "operator_review_required": True,
    },
    "phrase_slot_model": {
        "design_method": "derive_phrase_slot_model_from_egp_and_operator_reviewed_pattern",
        "completion_value_shape": "object_with_slots_constraints_and_source_refs",
        "operator_review_required": True,
    },
    "sentence_role_model": {
        "design_method": "derive_sentence_role_model_from_egp_and_operator_reviewed_pattern",
        "completion_value_shape": "object_with_sentence_roles_constraints_and_source_refs",
        "operator_review_required": True,
    },
    "sentence_slot_sequence": {
        "design_method": "derive_sentence_slot_sequence_from_egp_and_operator_reviewed_pattern",
        "completion_value_shape": "ordered_array_of_sentence_slots_with_source_refs",
        "operator_review_required": True,
    },
    "construction_head_pattern": {
        "design_method": "derive_construction_head_pattern_from_egp_and_operator_reviewed_pattern",
        "completion_value_shape": "object_with_head_pattern_slots_and_source_refs",
        "operator_review_required": True,
    },
    "construction_complement_model": {
        "design_method": "derive_construction_complement_model_from_egp_and_operator_reviewed_pattern",
        "completion_value_shape": "object_with_complement_slots_constraints_and_source_refs",
        "operator_review_required": True,
    },
    "component_node_reference_selection": {
        "design_method": "select_component_node_refs_from_existing_or_operator_reviewed_refs",
        "completion_value_shape": "array_of_existing_or_operator_reviewed_component_node_refs",
        "operator_review_required": True,
    },
    "composite_rule_definition": {
        "design_method": "define_composite_rule_from_egp_and_operator_reviewed_composition_rule",
        "completion_value_shape": "object_with_composition_rule_and_source_refs",
        "operator_review_required": True,
    },
    "composite_role_mapping": {
        "design_method": "define_composite_role_mapping_from_egp_and_operator_reviewed_role_map",
        "completion_value_shape": "object_with_role_mapping_and_source_refs",
        "operator_review_required": True,
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


def iter_selection_items(packet):
    for group in packet.get("selection_groups", []):
        for item in group.get("items", []):
            yield item


def design_task(selection):
    kind = selection.get("completion_kind")
    rule = DESIGN_RULES.get(kind, {
        "design_method": "operator_reviewed_field_completion_design",
        "completion_value_shape": "operator_reviewed_value_with_source_refs",
        "operator_review_required": True,
    })
    return {
        "field_name": selection.get("field_name"),
        "completion_kind": kind,
        "field_completion_design_status": "DESIGN_ONLY_NOT_IMPLEMENTED",
        "design_method": rule["design_method"],
        "completion_value_shape": rule["completion_value_shape"],
        "selected_primary_evidence": selection.get("selected_primary_evidence", []),
        "selected_support_evidence": selection.get("selected_support_evidence", []),
        "selected_structural_evidence": selection.get("selected_structural_evidence", []),
        "selected_context_evidence": selection.get("selected_context_evidence", []),
        "cambridge_usage": selection.get("cambridge_usage"),
        "source_evidence_selection_policy": selection.get("source_evidence_selection_policy"),
        "operator_review_required": rule["operator_review_required"],
        "field_completion_implementation_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "canonical_write_allowed": False,
    }


def design_item(item):
    selections = item.get("field_evidence_selections", [])
    designs = [design_task(selection) for selection in selections]
    return {
        "design_item_id": "design_" + item.get("selection_item_id", "unknown"),
        "selection_item_id": item.get("selection_item_id"),
        "planning_item_id": item.get("planning_item_id"),
        "artifact_id": item.get("artifact_id"),
        "learning_unit_id": item.get("learning_unit_id"),
        "learning_unit_type": item.get("learning_unit_type"),
        "source_cluster": item.get("source_cluster", {}),
        "schema_contract_path": item.get("schema_contract_path"),
        "field_completion_design_status": "DESIGN_ONLY_NOT_IMPLEMENTED",
        "field_completion_design_count": len(designs),
        "field_completion_designs": designs,
        "source_evidence_selection_policy": POLICY_NAME,
        "field_completion_implementation_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
    }


def flatten_designs(items):
    return [design for item in items for design in item.get("field_completion_designs", [])]


def main():
    selection_packet = load(SELECTION_PACKET)
    selection_items = list(iter_selection_items(selection_packet))
    if len(selection_items) != 19:
        raise ValueError(f"Expected 19 selection items, got {len(selection_items)}")
    design_items = [design_item(item) for item in sorted(selection_items, key=lambda item: (item.get("learning_unit_type") or "", item.get("artifact_id") or ""))]
    groups = []
    for lut in sorted(set(item["learning_unit_type"] for item in design_items)):
        group_items = [item for item in design_items if item["learning_unit_type"] == lut]
        groups.append({
            "learning_unit_type": lut,
            "design_item_count": len(group_items),
            "field_completion_design_count": sum(item["field_completion_design_count"] for item in group_items),
            "items": group_items,
        })
    all_designs = flatten_designs(design_items)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_field_completion_design_packet",
        "source_artifact_id": selection_packet.get("artifact_id"),
        "design_scope": "design-only field completion for 48 A1/A1+ clear-lane draft placeholder fields",
        "source_evidence_selection_policy": POLICY_NAME,
        "design_groups": groups,
        "design_policy": {
            "design_only_not_implemented": True,
            "source_grounded_values_required": True,
            "operator_review_required": True,
            "field_completion_implementation_allowed_now": False,
            "draft_artifact_update_allowed_now": False,
            "promotion_planning_allowed_now": False,
            "promotion_allowed_now": False,
            "generated_examples_allowed": False,
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
        "artifact_id": "a1_a1plus_clear_lane_draft_field_completion_design_packet_summary",
        "validation_status": "PASS",
        "source_selection_item_count": len(selection_items),
        "design_group_count": len(groups),
        "design_item_count": len(design_items),
        "field_completion_design_count": len(all_designs),
        "learning_unit_type_counts": count_by(design_items, lambda item: item["learning_unit_type"]),
        "field_completion_design_status_counts": count_by(all_designs, lambda item: item["field_completion_design_status"]),
        "completion_kind_counts": count_by(all_designs, lambda item: item["completion_kind"]),
        "source_evidence_selection_policy": POLICY_NAME,
        "design_only_not_implemented": True,
        "source_grounded_values_required": True,
        "operator_review_required": True,
        "field_completion_implementation_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "generated_examples_allowed": False,
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E16_A1A1PlusClearLaneDraftFieldCompletionImplementationPlan",
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear lane draft field completion design packet build: PASS")
    print("Design items:", len(design_items))
    print("Field completion designs:", len(all_designs))
    print("Policy:", POLICY_NAME)


if __name__ == "__main__":
    main()
