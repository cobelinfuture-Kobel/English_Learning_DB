import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SELECTION_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_source_evidence_selection_packet.json"
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_field_completion_design_implementation_bundle.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_field_completion_design_implementation_bundle_summary.json"
TASK_ID = "R7-M104E15B_A1A1PlusClearLaneFieldCompletionDesignImplementationBundle"
POLICY_NAME = "BALANCED_SOURCE_GROUNDED"
EXPECTED_ITEM_COUNT = 19
EXPECTED_FIELD_TASK_COUNT = 48
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
EXPECTED_DRAFT_PATH = "ulga/learning_units/draft/a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
EXPECTED_STATUS = "DESIGN_IMPLEMENTATION_PLAN_AND_PATCH_PREVIEW_ONLY"


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


def flatten_tasks(bundle_items):
    return [task for item in bundle_items for task in item.get("field_bundle_tasks", [])]


def validate():
    print("Validating A1/A1+ clear lane field completion design implementation bundle...")
    selection_packet = load(SELECTION_PACKET)
    report = load(REPORT)
    summary = load(SUMMARY)
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    selection_items = list(iter_selection_items(selection_packet))
    if len(selection_items) != EXPECTED_ITEM_COUNT:
        return fail("source selection item count mismatch")
    selection_ids = {item.get("selection_item_id") for item in selection_items}
    expected_task_count = sum(len(item.get("field_evidence_selections", [])) for item in selection_items)
    if expected_task_count != EXPECTED_FIELD_TASK_COUNT:
        return fail("source field evidence selection count mismatch")
    if report.get("source_evidence_selection_policy") != POLICY_NAME:
        return fail("source_evidence_selection_policy mismatch")
    groups = report.get("bundle_groups", [])
    if not groups:
        return fail("bundle_groups missing")
    bundle_items = []
    for group in groups:
        group_items = group.get("items", [])
        if group.get("bundle_item_count") != len(group_items):
            return fail("group bundle_item_count mismatch")
        if group.get("field_bundle_task_count") != sum(item.get("field_bundle_task_count", 0) for item in group_items):
            return fail("group field_bundle_task_count mismatch")
        for item in group_items:
            if item.get("learning_unit_type") != group.get("learning_unit_type"):
                return fail("item learning_unit_type mismatch with group")
            bundle_items.append(item)
    if len(bundle_items) != EXPECTED_ITEM_COUNT:
        return fail("bundle_item_count mismatch")
    seen_selection_ids = set()
    for item in bundle_items:
        sid = item.get("selection_item_id")
        if sid not in selection_ids or sid in seen_selection_ids:
            return fail("missing, duplicate, or unknown selection_item_id")
        seen_selection_ids.add(sid)
        if item.get("bundle_item_status") != EXPECTED_STATUS:
            return fail("bundle_item_status mismatch")
        if item.get("source_evidence_selection_policy") != POLICY_NAME:
            return fail("item source_evidence_selection_policy mismatch")
        for key in ["field_completion_implementation_allowed_now", "draft_artifact_update_allowed_now", "promotion_planning_allowed_now", "promotion_allowed_now", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
            if item.get(key) is not False:
                return fail(f"item {key} must be false")
        if item.get("field_bundle_task_count") != len(item.get("field_bundle_tasks", [])):
            return fail("item field_bundle_task_count mismatch")
    all_tasks = flatten_tasks(bundle_items)
    if len(all_tasks) != EXPECTED_FIELD_TASK_COUNT:
        return fail("field bundle task count mismatch")
    for task in all_tasks:
        if task.get("field_completion_design_status") != "DESIGN_ONLY_NOT_IMPLEMENTED":
            return fail("design status mismatch")
        if task.get("source_evidence_selection_policy") != POLICY_NAME:
            return fail("task policy mismatch")
        if task.get("selected_primary_evidence") != ["EGP_ROW"]:
            return fail("selected_primary_evidence must be EGP_ROW")
        if not task.get("design_method"):
            return fail("design_method missing")
        if not task.get("completion_value_shape"):
            return fail("completion_value_shape missing")
        plan = task.get("implementation_plan", {})
        if plan.get("implementation_status") != "PLANNED_NOT_IMPLEMENTED":
            return fail("implementation status mismatch")
        if plan.get("source_refs_required") is not True:
            return fail("source_refs_required must be true")
        if plan.get("operator_review_required") is not True:
            return fail("operator_review_required must be true")
        if plan.get("draft_artifact_update_allowed_now") is not False:
            return fail("plan draft_artifact_update_allowed_now must be false")
        if plan.get("canonical_write_allowed") is not False:
            return fail("plan canonical_write_allowed must be false")
        preview = task.get("patch_preview", {})
        if preview.get("patch_preview_status") != "PREVIEW_ONLY_NOT_APPLIED":
            return fail("patch preview status mismatch")
        if preview.get("target_path") != EXPECTED_DRAFT_PATH:
            return fail("patch preview target path mismatch")
        if preview.get("proposed_value_status") != "NOT_MATERIALIZED_IN_THIS_BUNDLE":
            return fail("proposed_value_status mismatch")
        if preview.get("apply_allowed_now") is not False:
            return fail("patch preview apply_allowed_now must be false")
        for key in ["field_completion_implementation_allowed_now", "draft_artifact_update_allowed_now", "canonical_write_allowed"]:
            if task.get(key) is not False:
                return fail(f"task {key} must be false")
    type_counts = count_by(bundle_items, lambda item: item.get("learning_unit_type"))
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    policy = report.get("bundle_policy", {})
    expected_policy = {
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
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            return fail(f"bundle_policy {key} mismatch")
    expected_summary = {
        "validation_status": "PASS",
        "source_selection_item_count": EXPECTED_ITEM_COUNT,
        "bundle_group_count": len(groups),
        "bundle_item_count": EXPECTED_ITEM_COUNT,
        "field_bundle_task_count": EXPECTED_FIELD_TASK_COUNT,
        "learning_unit_type_counts": EXPECTED_TYPE_COUNTS,
        "field_completion_design_status_counts": {"DESIGN_ONLY_NOT_IMPLEMENTED": EXPECTED_FIELD_TASK_COUNT},
        "implementation_status_counts": {"PLANNED_NOT_IMPLEMENTED": EXPECTED_FIELD_TASK_COUNT},
        "patch_preview_status_counts": {"PREVIEW_ONLY_NOT_APPLIED": EXPECTED_FIELD_TASK_COUNT},
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
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            return fail(f"summary {key} mismatch")
    if summary.get("completion_kind_counts") != count_by(all_tasks, lambda item: item.get("completion_kind")):
        return fail("completion_kind_counts mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False:
            return fail(f"report {key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    print("A1/A1+ clear lane field completion design implementation bundle validation: PASS")
    print("Bundle items:", len(bundle_items))
    print("Field bundle tasks:", len(all_tasks))
    print("Policy:", POLICY_NAME)
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
