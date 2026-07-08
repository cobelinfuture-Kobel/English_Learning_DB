import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SELECTION_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet.json"
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_design_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_design_packet_summary.json"
TASK_ID = "R7-M104E15_A1A1PlusClearLaneDraftFieldCompletionDesignPacket"
POLICY_NAME = "BALANCED_SOURCE_GROUNDED"
EXPECTED_COUNT = 19
EXPECTED_FIELD_DESIGN_COUNT = 48
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
CAMBRIDGE_USAGE = "EXAM_CONTEXT_ONLY_NOT_ROW_LEVEL_EVIDENCE"


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


def iter_selection_items(packet):
    for group in packet.get("selection_groups", []):
        for item in group.get("items", []):
            yield item


def flatten_designs(design_items):
    return [design for item in design_items for design in item.get("field_completion_designs", [])]


def validate():
    print("Validating A1/A1+ clear lane draft field completion design packet...")
    selection_packet = load(SELECTION_PACKET)
    report = load(REPORT)
    summary = load(SUMMARY)
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    selection_items = list(iter_selection_items(selection_packet))
    if len(selection_items) != EXPECTED_COUNT:
        return fail("source selection item count mismatch")
    selection_ids = {item.get("selection_item_id") for item in selection_items}
    expected_field_count = sum(len(item.get("field_evidence_selections", [])) for item in selection_items)
    if expected_field_count != EXPECTED_FIELD_DESIGN_COUNT:
        return fail("source field evidence selection count mismatch")
    if report.get("source_evidence_selection_policy") != POLICY_NAME:
        return fail("source_evidence_selection_policy mismatch")
    groups = report.get("design_groups", [])
    if not groups:
        return fail("design_groups missing")
    design_items = []
    for group in groups:
        group_items = group.get("items", [])
        if group.get("design_item_count") != len(group_items):
            return fail("group design_item_count mismatch")
        if group.get("field_completion_design_count") != sum(item.get("field_completion_design_count", 0) for item in group_items):
            return fail("group field_completion_design_count mismatch")
        for item in group_items:
            if item.get("learning_unit_type") != group.get("learning_unit_type"):
                return fail("item learning_unit_type mismatch with group")
            design_items.append(item)
    if len(design_items) != EXPECTED_COUNT:
        return fail("design_item_count mismatch")
    seen_selection_ids = set()
    for item in design_items:
        sid = item.get("selection_item_id")
        if sid not in selection_ids or sid in seen_selection_ids:
            return fail("missing, duplicate, or unknown selection_item_id")
        seen_selection_ids.add(sid)
        if item.get("field_completion_design_status") != "DESIGN_ONLY_NOT_IMPLEMENTED":
            return fail("field_completion_design_status mismatch")
        if item.get("source_evidence_selection_policy") != POLICY_NAME:
            return fail("item source_evidence_selection_policy mismatch")
        for key in ["field_completion_implementation_allowed_now", "draft_artifact_update_allowed_now", "promotion_planning_allowed_now", "promotion_allowed_now", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
            if item.get(key) is not False:
                return fail(f"item {key} must be false")
        if item.get("field_completion_design_count") != len(item.get("field_completion_designs", [])):
            return fail("item field_completion_design_count mismatch")
    all_designs = flatten_designs(design_items)
    if len(all_designs) != EXPECTED_FIELD_DESIGN_COUNT:
        return fail("field completion design count mismatch")
    for design in all_designs:
        if design.get("field_completion_design_status") != "DESIGN_ONLY_NOT_IMPLEMENTED":
            return fail("design status mismatch")
        if design.get("source_evidence_selection_policy") != POLICY_NAME:
            return fail("design policy mismatch")
        if design.get("selected_primary_evidence") != ["EGP_ROW"]:
            return fail("selected_primary_evidence must be EGP_ROW")
        if design.get("cambridge_usage") != CAMBRIDGE_USAGE:
            return fail("cambridge_usage mismatch")
        if not design.get("design_method"):
            return fail("design_method missing")
        if not design.get("completion_value_shape"):
            return fail("completion_value_shape missing")
        if design.get("operator_review_required") is not True:
            return fail("operator_review_required must be true")
        for key in ["field_completion_implementation_allowed_now", "draft_artifact_update_allowed_now", "canonical_write_allowed"]:
            if design.get(key) is not False:
                return fail(f"design {key} must be false")
    type_counts = count_by(design_items, lambda item: item.get("learning_unit_type"))
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    policy = report.get("design_policy", {})
    expected_policy = {
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
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            return fail(f"design_policy {key} mismatch")
    expected_summary = {
        "validation_status": "PASS",
        "source_selection_item_count": EXPECTED_COUNT,
        "design_group_count": len(groups),
        "design_item_count": EXPECTED_COUNT,
        "field_completion_design_count": EXPECTED_FIELD_DESIGN_COUNT,
        "learning_unit_type_counts": EXPECTED_TYPE_COUNTS,
        "field_completion_design_status_counts": {"DESIGN_ONLY_NOT_IMPLEMENTED": EXPECTED_FIELD_DESIGN_COUNT},
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
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            return fail(f"summary {key} mismatch")
    if summary.get("completion_kind_counts") != count_by(all_designs, lambda item: item.get("completion_kind")):
        return fail("completion_kind_counts mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False:
            return fail(f"report {key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    print("A1/A1+ clear lane draft field completion design packet validation: PASS")
    print("Design items:", len(design_items))
    print("Field completion designs:", len(all_designs))
    print("Policy:", POLICY_NAME)
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
