import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SELECTION_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_field_completion_design_implementation_bundle.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_field_completion_design_implementation_bundle_summary.json"
TASK_ID = "R7-M104E15B_A1A1PlusClearLaneFieldCompletionDesignImplementationBundle"
POLICY_NAME = "BALANCED_SOURCE_GROUNDED"
DRAFT_ARTIFACT_PATH = "ulga/learning_units/draft/a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"

DESIGN_METHOD_BY_KIND = {
    "component_node_reference_selection": "select_component_node_refs_from_existing_or_operator_reviewed_refs",
    "composite_role_mapping": "define_composite_role_mapping_from_egp_and_operator_reviewed_role_map",
    "composite_rule_definition": "define_composite_rule_from_egp_and_operator_reviewed_composition_rule",
    "construction_complement_model": "derive_construction_complement_model_from_egp_and_operator_reviewed_pattern",
    "construction_head_pattern": "derive_construction_head_pattern_from_egp_and_operator_reviewed_pattern",
    "phrase_slot_model": "derive_phrase_slot_model_from_egp_evp_and_operator_reviewed_pattern",
    "sentence_role_model": "derive_sentence_role_model_from_egp_and_operator_reviewed_pattern",
    "sentence_slot_sequence": "derive_sentence_slot_sequence_from_egp_and_operator_reviewed_pattern",
    "source_grounded_positive_example": "select_or_write_source_grounded_positive_example_from_egp_evp_raz",
    "source_grounded_usage_example": "select_or_write_source_grounded_usage_example_from_egp_evp_raz",
}

VALUE_SHAPE_BY_KIND = {
    "component_node_reference_selection": "array_of_existing_or_operator_reviewed_component_node_refs",
    "composite_role_mapping": "object_with_role_mapping_and_source_refs",
    "composite_rule_definition": "object_with_composition_rule_and_source_refs",
    "construction_complement_model": "object_with_complement_slots_constraints_and_source_refs",
    "construction_head_pattern": "object_with_head_pattern_slots_and_source_refs",
    "phrase_slot_model": "object_with_slots_constraints_and_source_refs",
    "sentence_role_model": "object_with_sentence_roles_constraints_and_source_refs",
    "sentence_slot_sequence": "ordered_array_of_sentence_slots_with_source_refs",
    "source_grounded_positive_example": "array_of_short_a1_examples_with_source_refs",
    "source_grounded_usage_example": "array_of_short_a1_usage_examples_with_source_refs",
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


def design_and_plan(selection):
    kind = selection.get("completion_kind")
    field = selection.get("field_name")
    return {
        "field_name": field,
        "completion_kind": kind,
        "field_completion_design_status": "DESIGN_ONLY_NOT_IMPLEMENTED",
        "design_method": DESIGN_METHOD_BY_KIND.get(kind, "operator_reviewed_field_completion_design"),
        "completion_value_shape": VALUE_SHAPE_BY_KIND.get(kind, "operator_reviewed_value_with_source_refs"),
        "selected_primary_evidence": selection.get("selected_primary_evidence", []),
        "selected_support_evidence": selection.get("selected_support_evidence", []),
        "selected_structural_evidence": selection.get("selected_structural_evidence", []),
        "selected_context_evidence": selection.get("selected_context_evidence", []),
        "cambridge_usage": selection.get("cambridge_usage"),
        "source_evidence_selection_policy": selection.get("source_evidence_selection_policy"),
        "implementation_plan": {
            "implementation_status": "PLANNED_NOT_IMPLEMENTED",
            "implementation_method": "fill_draft_field_from_selected_evidence_after_operator_approval",
            "source_refs_required": True,
            "operator_review_required": True,
            "draft_artifact_update_allowed_now": False,
            "canonical_write_allowed": False,
        },
        "patch_preview": {
            "patch_preview_status": "PREVIEW_ONLY_NOT_APPLIED",
            "target_path": DRAFT_ARTIFACT_PATH,
            "target_artifact_id": None,
            "operation": "replace_placeholder_field_with_source_grounded_value_after_future_approval",
            "field_path": field,
            "proposed_value_status": "NOT_MATERIALIZED_IN_THIS_BUNDLE",
            "proposed_value_shape": VALUE_SHAPE_BY_KIND.get(kind, "operator_reviewed_value_with_source_refs"),
            "apply_allowed_now": False,
        },
        "field_completion_implementation_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "canonical_write_allowed": False,
    }


def bundle_item(item):
    tasks = [design_and_plan(selection) for selection in item.get("field_evidence_selections", [])]
    for task in tasks:
        task["patch_preview"]["target_artifact_id"] = item.get("artifact_id")
    return {
        "bundle_item_id": "bundle_" + item.get("selection_item_id", "unknown"),
        "selection_item_id": item.get("selection_item_id"),
        "planning_item_id": item.get("planning_item_id"),
        "artifact_id": item.get("artifact_id"),
        "learning_unit_id": item.get("learning_unit_id"),
        "learning_unit_type": item.get("learning_unit_type"),
        "source_cluster": item.get("source_cluster", {}),
        "schema_contract_path": item.get("schema_contract_path"),
        "bundle_item_status": "DESIGN_IMPLEMENTATION_PLAN_AND_PATCH_PREVIEW_ONLY",
        "field_bundle_task_count": len(tasks),
        "field_bundle_tasks": tasks,
        "source_evidence_selection_policy": POLICY_NAME,
        "field_completion_implementation_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
    }


def flatten_tasks(items):
    return [task for item in items for task in item.get("field_bundle_tasks", [])]


def main():
    selection_packet = load(SELECTION_PACKET)
    selection_items = list(iter_selection_items(selection_packet))
    if len(selection_items) != 19:
        raise ValueError(f"Expected 19 selection items, got {len(selection_items)}")
    bundle_items = [bundle_item(item) for item in sorted(selection_items, key=lambda item: (item.get("learning_unit_type") or "", item.get("artifact_id") or ""))]
    groups = []
    for lut in sorted(set(item["learning_unit_type"] for item in bundle_items)):
        group_items = [item for item in bundle_items if item["learning_unit_type"] == lut]
        groups.append({
            "learning_unit_type": lut,
            "bundle_item_count": len(group_items),
            "field_bundle_task_count": sum(item["field_bundle_task_count"] for item in group_items),
            "items": group_items,
        })
    all_tasks = flatten_tasks(bundle_items)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_field_completion_design_implementation_bundle",
        "source_artifact_id": selection_packet.get("artifact_id"),
        "bundle_scope": "design plus implementation-plan rules plus patch preview for 48 clear-lane draft fields",
        "source_evidence_selection_policy": POLICY_NAME,
        "bundle_groups": groups,
        "bundle_policy": {
            "design_included": True,
            "implementation_plan_included": True,
            "patch_preview_included": True,
            "actual_field_values_materialized": False,
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
        "artifact_id": "a1_a1plus_clear_lane_field_completion_design_implementation_bundle_summary",
        "validation_status": "PASS",
        "source_selection_item_count": len(selection_items),
        "bundle_group_count": len(groups),
        "bundle_item_count": len(bundle_items),
        "field_bundle_task_count": len(all_tasks),
        "learning_unit_type_counts": count_by(bundle_items, lambda item: item["learning_unit_type"]),
        "completion_kind_counts": count_by(all_tasks, lambda task: task["completion_kind"]),
        "field_completion_design_status_counts": count_by(all_tasks, lambda task: task["field_completion_design_status"]),
        "implementation_status_counts": count_by(all_tasks, lambda task: task["implementation_plan"]["implementation_status"]),
        "patch_preview_status_counts": count_by(all_tasks, lambda task: task["patch_preview"]["patch_preview_status"]),
        "source_evidence_selection_policy": POLICY_NAME,
        "design_included": True,
        "implementation_plan_included": True,
        "patch_preview_included": True,
        "actual_field_values_materialized": False,
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
        "next_short_step": "R7-M104E16_A1A1PlusClearLaneDraftFieldCompletionPatchApprovalGate",
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear lane field completion design implementation bundle build: PASS")
    print("Bundle items:", len(bundle_items))
    print("Field bundle tasks:", len(all_tasks))
    print("Policy:", POLICY_NAME)


if __name__ == "__main__":
    main()
