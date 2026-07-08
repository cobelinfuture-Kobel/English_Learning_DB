import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DRAFTS = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_review_packet_summary.json"
TASK_ID = "R7-M104E11_A1A1PlusClearLaneDraftArtifactReviewPacket"
EXPECTED_COUNT = 19
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
REQUIRED_REVIEW_CHECKS = {
    "schema_contract_fit",
    "learning_unit_type_fit",
    "source_cluster_traceability",
    "placeholder_fields_need_operator_completion",
    "example_quality_review",
    "promotion_block_confirmed",
}
DECISION_OPTIONS = {
    "APPROVE_DRAFT_FOR_PROMOTION_PLANNING",
    "ADJUST_DRAFT_FIELDS_BEFORE_PROMOTION_PLANNING",
    "DEFER_DRAFT_FOR_SOURCE_REVIEW",
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


def validate():
    print("Validating A1/A1+ clear lane draft artifact review packet...")
    drafts = load(DRAFTS)
    report = load(REPORT)
    summary = load(SUMMARY)
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    source_artifacts = drafts.get("draft_artifacts", [])
    if len(source_artifacts) != EXPECTED_COUNT:
        return fail("source draft artifact count mismatch")
    source_ids = {artifact.get("artifact_id") for artifact in source_artifacts}
    groups = report.get("review_groups", [])
    if not groups:
        return fail("review_groups missing")
    items = []
    for group in groups:
        group_items = group.get("items", [])
        if group.get("review_item_count") != len(group_items):
            return fail("group review_item_count mismatch")
        if group.get("placeholder_field_total") != sum(item.get("placeholder_field_count", 0) for item in group_items):
            return fail("group placeholder_field_total mismatch")
        for item in group_items:
            if item.get("learning_unit_type") != group.get("learning_unit_type"):
                return fail("item learning_unit_type mismatch with group")
            items.append(item)
    if len(items) != EXPECTED_COUNT:
        return fail("review item count mismatch")
    seen_artifacts = set()
    for item in items:
        artifact_id = item.get("artifact_id")
        if artifact_id not in source_ids or artifact_id in seen_artifacts:
            return fail("missing, duplicate, or unknown artifact_id")
        seen_artifacts.add(artifact_id)
        if item.get("artifact_status") != "DRAFT_NOT_CANONICAL":
            return fail("artifact_status must be DRAFT_NOT_CANONICAL")
        if item.get("operator_review_status") != "PENDING_OPERATOR_REVIEW":
            return fail("operator_review_status must be pending")
        if not REQUIRED_REVIEW_CHECKS.issubset(set(item.get("required_review_checks", []))):
            return fail("required review checks incomplete")
        if set(item.get("review_decision_options", [])) != DECISION_OPTIONS:
            return fail("review decision options mismatch")
        if item.get("recommended_default_decision") not in DECISION_OPTIONS:
            return fail("recommended default decision invalid")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("canonical_grammar_write_allowed must be false")
        if item.get("canonical_pattern_write_allowed") is not False:
            return fail("canonical_pattern_write_allowed must be false")
        if not item.get("schema_contract_path"):
            return fail("schema_contract_path missing")
    type_counts = count_by(items, lambda item: item.get("learning_unit_type"))
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    review_policy = report.get("review_policy", {})
    if review_policy.get("promotion_allowed_now") is not False:
        return fail("promotion_allowed_now must be false")
    if review_policy.get("promotion_planning_allowed_after_review") is not True:
        return fail("promotion_planning_allowed_after_review must be true")
    for key in ["canonical_grammar_write_allowed", "canonical_pattern_write_allowed", "deferred_lane_processing_allowed", "a2_a2plus_progression_allowed"]:
        if review_policy.get(key) is not False:
            return fail(f"review_policy {key} must be false")
    expected_summary = {
        "validation_status": "PASS",
        "source_draft_artifact_count": EXPECTED_COUNT,
        "review_group_count": len(groups),
        "review_item_count": EXPECTED_COUNT,
        "learning_unit_type_counts": EXPECTED_TYPE_COUNTS,
        "review_status_counts": {"PENDING_OPERATOR_REVIEW": EXPECTED_COUNT},
        "promotion_allowed_now": False,
        "promotion_planning_allowed_after_review": True,
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E12_A1A1PlusClearLaneDraftArtifactOperatorReviewDecisionPacket",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            return fail(f"summary {key} mismatch")
    if summary.get("recommended_default_decision_counts") != count_by(items, lambda item: item.get("recommended_default_decision")):
        return fail("recommended_default_decision_counts mismatch")
    if summary.get("total_placeholder_field_count") != sum(item.get("placeholder_field_count", 0) for item in items):
        return fail("total_placeholder_field_count mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False:
            return fail(f"report {key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    print("A1/A1+ clear lane draft artifact review packet validation: PASS")
    print("Review items:", len(items))
    print("Learning unit types:", type_counts)
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
