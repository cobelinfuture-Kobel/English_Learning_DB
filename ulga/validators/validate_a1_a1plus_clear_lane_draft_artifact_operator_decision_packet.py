import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REVIEW_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_review_packet.json"
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet_summary.json"
TASK_ID = "R7-M104E12_A1A1PlusClearLaneDraftArtifactOperatorReviewDecisionPacket"
EXPECTED_COUNT = 19
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
DECISION = "ADJUST_DRAFT_FIELDS_BEFORE_PROMOTION_PLANNING"
ALLOWED_NEXT_ACTION = "FIELD_COMPLETION_PLANNING_ONLY"


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


def iter_review_items(review_packet):
    for group in review_packet.get("review_groups", []):
        for item in group.get("items", []):
            yield item


def validate():
    print("Validating A1/A1+ clear lane draft artifact operator decision packet...")
    review_packet = load(REVIEW_PACKET)
    report = load(REPORT)
    summary = load(SUMMARY)
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    review_items = list(iter_review_items(review_packet))
    if len(review_items) != EXPECTED_COUNT:
        return fail("source review item count mismatch")
    review_ids = {item.get("review_item_id") for item in review_items}
    review_placeholder_total = sum(item.get("placeholder_field_count", 0) for item in review_items)
    groups = report.get("decision_groups", [])
    if not groups:
        return fail("decision_groups missing")
    decisions = []
    for group in groups:
        group_items = group.get("items", [])
        if group.get("decision_item_count") != len(group_items):
            return fail("group decision_item_count mismatch")
        if group.get("placeholder_field_total") != sum(item.get("placeholder_field_count", 0) for item in group_items):
            return fail("group placeholder_field_total mismatch")
        for item in group_items:
            if item.get("learning_unit_type") != group.get("learning_unit_type"):
                return fail("item learning_unit_type mismatch with group")
            decisions.append(item)
    if len(decisions) != EXPECTED_COUNT:
        return fail("decision_item_count mismatch")
    seen_review_ids = set()
    for item in decisions:
        rid = item.get("review_item_id")
        if rid not in review_ids or rid in seen_review_ids:
            return fail("missing, duplicate, or unknown review_item_id")
        seen_review_ids.add(rid)
        if item.get("operator_decision") != DECISION:
            return fail("operator_decision mismatch")
        if item.get("allowed_next_action") != ALLOWED_NEXT_ACTION:
            return fail("allowed_next_action mismatch")
        if item.get("promotion_planning_allowed_now") is not False:
            return fail("promotion_planning_allowed_now must be false")
        if item.get("promotion_allowed_now") is not False:
            return fail("promotion_allowed_now must be false")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("canonical_grammar_write_allowed must be false")
        if item.get("canonical_pattern_write_allowed") is not False:
            return fail("canonical_pattern_write_allowed must be false")
        if item.get("deferred_lane_processing_allowed") is not False:
            return fail("deferred_lane_processing_allowed must be false")
    type_counts = count_by(decisions, lambda item: item.get("learning_unit_type"))
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    decision_policy = report.get("operator_decision_policy", {})
    expected_policy = {
        "decision": DECISION,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "field_completion_planning_allowed": True,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "deferred_lane_processing_allowed": False,
        "a2_a2plus_progression_allowed": False,
    }
    for key, expected in expected_policy.items():
        if decision_policy.get(key) != expected:
            return fail(f"operator_decision_policy {key} mismatch")
    expected_summary = {
        "validation_status": "PASS",
        "source_review_item_count": EXPECTED_COUNT,
        "decision_group_count": len(groups),
        "decision_item_count": EXPECTED_COUNT,
        "learning_unit_type_counts": EXPECTED_TYPE_COUNTS,
        "operator_decision_counts": {DECISION: EXPECTED_COUNT},
        "allowed_next_action_counts": {ALLOWED_NEXT_ACTION: EXPECTED_COUNT},
        "total_placeholder_field_count": review_placeholder_total,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "field_completion_planning_allowed": True,
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E13_A1A1PlusClearLaneDraftFieldCompletionPlanningPacket",
        "stop_reason": "NONE",
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
    print("A1/A1+ clear lane draft artifact operator decision packet validation: PASS")
    print("Decision items:", len(decisions))
    print("Operator decisions:", {DECISION: len(decisions)})
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
