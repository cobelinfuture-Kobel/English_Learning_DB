import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PLANNING_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_planning_packet.json"
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet_summary.json"
TASK_ID = "R7-M104E14_A1A1PlusClearLaneDraftFieldCompletionSourceEvidenceSelection"
POLICY_NAME = "BALANCED_SOURCE_GROUNDED"
EXPECTED_COUNT = 19
EXPECTED_FIELD_SELECTION_COUNT = 48
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
CAMBRIDGE_USAGE = "EXAM_CONTEXT_ONLY_NOT_ROW_LEVEL_EVIDENCE"
PROHIBITED_EVIDENCE = {
    "CAMBRIDGE_ROW_LEVEL_EVIDENCE",
    "GENERATED_EXAMPLE_WITHOUT_SEPARATE_APPROVAL",
    "CANONICAL_GRAPH_AS_UNVERIFIED_SOURCE",
}


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: {exc}")


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


def flatten_selections(selection_items):
    return [selection for item in selection_items for selection in item.get("field_evidence_selections", [])]


def validate():
    print("Validating A1/A1+ clear lane draft field completion source evidence selection...")
    planning_packet = load(PLANNING_PACKET)
    report = load(REPORT)
    summary = load(SUMMARY)
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    planning_items = list(iter_planning_items(planning_packet))
    if len(planning_items) != EXPECTED_COUNT:
        return fail("source planning item count mismatch")
    planning_ids = {item.get("planning_item_id") for item in planning_items}
    expected_field_count = sum(len(item.get("field_completion_tasks", [])) for item in planning_items)
    if expected_field_count != EXPECTED_FIELD_SELECTION_COUNT:
        return fail("source field completion task count mismatch")
    if report.get("source_evidence_selection_policy") != POLICY_NAME:
        return fail("source_evidence_selection_policy mismatch")
    policy = report.get("policy_definition", {})
    expected_policy = {
        "primary_evidence": "EGP_ROW",
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
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            return fail(f"policy_definition {key} mismatch")
    groups = report.get("selection_groups", [])
    if not groups:
        return fail("selection_groups missing")
    selection_items = []
    for group in groups:
        group_items = group.get("items", [])
        if group.get("selection_item_count") != len(group_items):
            return fail("group selection_item_count mismatch")
        if group.get("field_evidence_selection_count") != sum(item.get("field_evidence_selection_count", 0) for item in group_items):
            return fail("group field_evidence_selection_count mismatch")
        for item in group_items:
            if item.get("learning_unit_type") != group.get("learning_unit_type"):
                return fail("item learning_unit_type mismatch with group")
            selection_items.append(item)
    if len(selection_items) != EXPECTED_COUNT:
        return fail("selection_item_count mismatch")
    seen_planning_ids = set()
    for item in selection_items:
        pid = item.get("planning_item_id")
        if pid not in planning_ids or pid in seen_planning_ids:
            return fail("missing, duplicate, or unknown planning_item_id")
        seen_planning_ids.add(pid)
        if item.get("field_evidence_selection_status") != "SELECTED_NOT_IMPLEMENTED":
            return fail("field_evidence_selection_status mismatch")
        if item.get("source_evidence_selection_policy") != POLICY_NAME:
            return fail("item source_evidence_selection_policy mismatch")
        for key in ["field_completion_allowed_now", "draft_artifact_update_allowed_now", "promotion_planning_allowed_now", "promotion_allowed_now", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
            if item.get(key) is not False:
                return fail(f"item {key} must be false")
        if item.get("field_evidence_selection_count") != len(item.get("field_evidence_selections", [])):
            return fail("item field_evidence_selection_count mismatch")
    all_selections = flatten_selections(selection_items)
    if len(all_selections) != EXPECTED_FIELD_SELECTION_COUNT:
        return fail("field evidence selection count mismatch")
    for selection in all_selections:
        if selection.get("evidence_selection_status") != "SELECTED_NOT_IMPLEMENTED":
            return fail("evidence_selection_status mismatch")
        if selection.get("source_evidence_selection_policy") != POLICY_NAME:
            return fail("selection policy mismatch")
        if selection.get("selected_primary_evidence") != ["EGP_ROW"]:
            return fail("selected_primary_evidence must be EGP_ROW")
        if selection.get("cambridge_usage") != CAMBRIDGE_USAGE:
            return fail("cambridge_usage mismatch")
        if "CAMBRIDGE_EXAM_CONTEXT" not in selection.get("selected_context_evidence", []):
            return fail("Cambridge exam context missing")
        if not PROHIBITED_EVIDENCE.issubset(set(selection.get("prohibited_evidence", []))):
            return fail("prohibited evidence incomplete")
        if selection.get("evidence_required") is not True:
            return fail("evidence_required must be true")
        for key in ["field_completion_allowed_now", "draft_artifact_update_allowed_now", "canonical_write_allowed"]:
            if selection.get(key) is not False:
                return fail(f"selection {key} must be false")
    type_counts = count_by(selection_items, lambda item: item.get("learning_unit_type"))
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    expected_summary = {
        "validation_status": "PASS",
        "source_planning_item_count": EXPECTED_COUNT,
        "selection_group_count": len(groups),
        "selection_item_count": EXPECTED_COUNT,
        "field_evidence_selection_count": EXPECTED_FIELD_SELECTION_COUNT,
        "learning_unit_type_counts": EXPECTED_TYPE_COUNTS,
        "evidence_selection_status_counts": {"SELECTED_NOT_IMPLEMENTED": EXPECTED_FIELD_SELECTION_COUNT},
        "primary_evidence_counts": {"EGP_ROW": EXPECTED_FIELD_SELECTION_COUNT},
        "cambridge_usage_counts": {CAMBRIDGE_USAGE: EXPECTED_FIELD_SELECTION_COUNT},
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
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            return fail(f"summary {key} mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False:
            return fail(f"report {key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    print("A1/A1+ clear lane draft field completion source evidence selection validation: PASS")
    print("Selection items:", len(selection_items))
    print("Field evidence selections:", len(all_selections))
    print("Policy:", POLICY_NAME)
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
