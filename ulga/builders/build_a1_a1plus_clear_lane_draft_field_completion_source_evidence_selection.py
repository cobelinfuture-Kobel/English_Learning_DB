import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PLANNING_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_planning_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet_summary.json"
TASK_ID = "R7-M104E14_A1A1PlusClearLaneDraftFieldCompletionSourceEvidenceSelection"
POLICY_NAME = "BALANCED_SOURCE_GROUNDED"
PRIMARY_EVIDENCE = "EGP_ROW"
CAMBRIDGE_CONTEXT = "CAMBRIDGE_EXAM_CONTEXT"
CAMBRIDGE_USAGE = "EXAM_CONTEXT_ONLY_NOT_ROW_LEVEL_EVIDENCE"

STRUCTURAL_EVIDENCE_BY_KIND = {
    "component_node_reference_selection": ["OPERATOR_REVIEWED_NODE_REF"],
    "composite_role_mapping": ["OPERATOR_REVIEWED_ROLE_MAP"],
    "composite_rule_definition": ["OPERATOR_REVIEWED_COMPOSITION_RULE"],
    "construction_complement_model": ["OPERATOR_REVIEWED_PATTERN"],
    "construction_head_pattern": ["OPERATOR_REVIEWED_PATTERN"],
    "phrase_slot_model": ["OPERATOR_REVIEWED_PATTERN"],
    "sentence_role_model": ["OPERATOR_REVIEWED_PATTERN"],
    "sentence_slot_sequence": ["OPERATOR_REVIEWED_PATTERN"],
}

SUPPORT_EVIDENCE_BY_KIND = {
    "construction_complement_model": ["EVP_SUPPORT"],
    "construction_head_pattern": ["EVP_SUPPORT"],
    "phrase_slot_model": ["EVP_SUPPORT"],
    "source_grounded_positive_example": ["EVP_SUPPORT", "RAZ_SUPPORT"],
    "source_grounded_usage_example": ["EVP_SUPPORT", "RAZ_SUPPORT"],
}

PROHIBITED_EVIDENCE = [
    "CAMBRIDGE_ROW_LEVEL_EVIDENCE",
    "GENERATED_EXAMPLE_WITHOUT_SEPARATE_APPROVAL",
    "CANONICAL_GRAPH_AS_UNVERIFIED_SOURCE",
]


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


def iter_planning_items(packet):
    for group in packet.get("planning_groups", []):
        for item in group.get("items", []):
            yield item


def select_evidence_for_task(task):
    kind = task.get("completion_kind")
    return {
        "field_name": task.get("field_name"),
        "completion_kind": kind,
        "evidence_selection_status": "SELECTED_NOT_IMPLEMENTED",
        "selected_primary_evidence": [PRIMARY_EVIDENCE],
        "selected_support_evidence": SUPPORT_EVIDENCE_BY_KIND.get(kind, []),
        "selected_structural_evidence": STRUCTURAL_EVIDENCE_BY_KIND.get(kind, []),
        "selected_context_evidence": [CAMBRIDGE_CONTEXT],
        "cambridge_usage": CAMBRIDGE_USAGE,
        "prohibited_evidence": PROHIBITED_EVIDENCE,
        "source_evidence_selection_policy": POLICY_NAME,
        "evidence_required": True,
        "field_completion_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "canonical_write_allowed": False,
    }


def selection_item(item):
    tasks = item.get("field_completion_tasks", [])
    selections = [select_evidence_for_task(task) for task in tasks]
    return {
        "selection_item_id": "selection_" + item.get("planning_item_id", "unknown"),
        "planning_item_id": item.get("planning_item_id"),
        "decision_item_id": item.get("decision_item_id"),
        "artifact_id": item.get("artifact_id"),
        "learning_unit_id": item.get("learning_unit_id"),
        "learning_unit_type": item.get("learning_unit_type"),
        "source_cluster": item.get("source_cluster", {}),
        "schema_contract_path": item.get("schema_contract_path"),
        "field_evidence_selection_status": "SELECTED_NOT_IMPLEMENTED",
        "field_evidence_selection_count": len(selections),
        "field_evidence_selections": selections,
        "source_evidence_selection_policy": POLICY_NAME,
        "field_completion_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
    }


def flatten_selection_tasks(items):
    return [selection for item in items for selection in item.get("field_evidence_selections", [])]


def main():
    planning_packet = load(PLANNING_PACKET)
    planning_items = list(iter_planning_items(planning_packet))
    if len(planning_items) != 19:
        raise ValueError(f"Expected 19 planning items, got {len(planning_items)}")
    selection_items = [selection_item(item) for item in sorted(planning_items, key=lambda item: (item.get("learning_unit_type") or "", item.get("artifact_id") or ""))]
    groups = []
    for lut in sorted(set(item["learning_unit_type"] for item in selection_items)):
        group_items = [item for item in selection_items if item["learning_unit_type"] == lut]
        groups.append({
            "learning_unit_type": lut,
            "selection_item_count": len(group_items),
            "field_evidence_selection_count": sum(item["field_evidence_selection_count"] for item in group_items),
            "items": group_items,
        })
    all_selections = flatten_selection_tasks(selection_items)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet",
        "source_artifact_id": planning_packet.get("artifact_id"),
        "source_evidence_selection_policy": POLICY_NAME,
        "policy_definition": {
            "primary_evidence": PRIMARY_EVIDENCE,
            "support_evidence_allowed": ["EVP_SUPPORT", "RAZ_SUPPORT"],
            "cambridge_usage": CAMBRIDGE_USAGE,
            "operator_reviewed_structural_evidence_allowed": True,
            "generated_examples_allowed": False,
            "field_completion_allowed_now": False,
            "draft_artifact_update_allowed_now": False,
            "canonical_grammar_write_allowed": False,
            "canonical_pattern_write_allowed": False,
            "deferred_lane_processing_allowed": False,
            "a2_a2plus_progression_allowed": False,
        },
        "selection_groups": groups,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet_summary",
        "validation_status": "PASS",
        "source_planning_item_count": len(planning_items),
        "selection_group_count": len(groups),
        "selection_item_count": len(selection_items),
        "field_evidence_selection_count": len(all_selections),
        "learning_unit_type_counts": count_by(selection_items, lambda item: item["learning_unit_type"]),
        "evidence_selection_status_counts": count_by(all_selections, lambda item: item["evidence_selection_status"]),
        "primary_evidence_counts": count_by(all_selections, lambda item: "+".join(item["selected_primary_evidence"])),
        "cambridge_usage_counts": count_by(all_selections, lambda item: item["cambridge_usage"]),
        "source_evidence_selection_policy": POLICY_NAME,
        "field_completion_allowed_now": False,
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
        "next_short_step": "R7-M104E15_A1A1PlusClearLaneDraftFieldCompletionDesignPacket",
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear lane draft field completion source evidence selection build: PASS")
    print("Selection items:", len(selection_items))
    print("Field evidence selections:", len(all_selections))
    print("Policy:", POLICY_NAME)


if __name__ == "__main__":
    main()
