import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_egp_feature_learning_unit_reclassification.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_egp_feature_learning_unit_reclassification_summary.json"
TASK_ID = "R7-M104E3_A1A1PlusEGPFeatureLearningUnitReclassification"
VALID_TYPES = {
    "ATOMIC_GRAMMAR_NODE",
    "MULTI_NODE_COMPOSITE",
    "PHRASE_PATTERN_NODE",
    "SENTENCE_PATTERN_NODE",
    "CONSTRUCTION_NODE",
    "USAGE_CONSTRAINT",
    "SPLIT_REQUIRED",
    "DEFER_FOR_SOURCE_REVIEW",
}
VALID_DECISION_PATHS = {
    "NO_ACTION_REQUIRED",
    "PATCH_ATOMIC_NODE_REVIEW",
    "PATCH_MULTIPLE_OR_CREATE_COMPOSITE_REVIEW",
    "CREATE_LEARNING_UNIT_TYPE_REVIEW",
    "SPLIT_CLUSTER_REVIEW",
    "DEFER_FOR_SOURCE_REVIEW",
}


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def validate():
    print("Validating A1/A1+ EGP feature learning unit reclassification...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required reclassification files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = report.get("reclassification_items", [])
    if not items:
        return fail("reclassification_items missing")
    if summary.get("reclassification_item_count") != len(items):
        return fail("reclassification_item_count mismatch")
    if summary.get("source_cluster_count") != len(items):
        return fail("source_cluster_count must equal item count")
    ids = set()
    type_counts = {}
    decision_counts = {}
    operator_required = 0
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        lut = item.get("learning_unit_type")
        if lut not in VALID_TYPES:
            return fail("invalid learning_unit_type")
        path = item.get("recommended_decision_path")
        if path not in VALID_DECISION_PATHS:
            return fail("invalid recommended_decision_path")
        if not set(VALID_DECISION_PATHS).issubset(set(item.get("allowed_decision_paths", []))):
            return fail("allowed_decision_paths incomplete")
        if not item.get("classification_rationale"):
            return fail("classification_rationale missing")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("item canonical write must be false")
        type_counts[lut] = type_counts.get(lut, 0) + 1
        decision_counts[path] = decision_counts.get(path, 0) + 1
        if item.get("operator_decision_required") is True:
            operator_required += 1
        if path == "NO_ACTION_REQUIRED" and item.get("operator_decision_required") is not False:
            return fail("NO_ACTION_REQUIRED must not require operator decision")
        if path != "NO_ACTION_REQUIRED" and item.get("operator_decision_required") is not True:
            return fail("non no-action path must require operator decision")
    if summary.get("learning_unit_type_counts") != dict(sorted(type_counts.items())):
        return fail("learning_unit_type_counts mismatch")
    if summary.get("recommended_decision_path_counts") != dict(sorted(decision_counts.items())):
        return fail("recommended_decision_path_counts mismatch")
    if summary.get("operator_decision_required_count") != operator_required:
        return fail("operator_decision_required_count mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E4_A1A1PlusLearningUnitTypeReviewPacket":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason mismatch")
    print("A1/A1+ EGP feature learning unit reclassification validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
