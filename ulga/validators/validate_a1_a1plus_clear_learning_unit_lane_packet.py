import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_lane_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_lane_packet_summary.json"
TASK_ID = "R7-M104E5_A1A1PlusClearLearningUnitLaneSelection"
CLEAR_DECISION_PATHS = {
    "CREATE_LEARNING_UNIT_TYPE_REVIEW",
    "PATCH_MULTIPLE_OR_CREATE_COMPOSITE_REVIEW",
}
DEFER_DECISION_PATHS = {"DEFER_FOR_SOURCE_REVIEW"}
EXPECTED_CLEAR_COUNT = 19
EXPECTED_DEFER_COUNT = 27
EXPECTED_NO_ACTION_COUNT = 3
EXPECTED_REVIEW_COUNT = 46


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
    print("Validating A1/A1+ clear learning unit lane packet...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required clear lane files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    clear = report.get("clear_active_lane_items", [])
    deferred = report.get("deferred_lane_items", [])
    no_action = report.get("no_action_items", [])
    unexpected = report.get("unexpected_review_items", [])
    if len(clear) != EXPECTED_CLEAR_COUNT:
        return fail("clear active lane item count mismatch")
    if len(deferred) != EXPECTED_DEFER_COUNT:
        return fail("deferred lane item count mismatch")
    if len(no_action) != EXPECTED_NO_ACTION_COUNT:
        return fail("no-action item count mismatch")
    if unexpected:
        return fail("unexpected review items must be empty")
    all_ids = set()
    for item in clear:
        if item.get("recommended_decision_path") not in CLEAR_DECISION_PATHS:
            return fail("clear item has invalid decision path")
        if item.get("operator_decision_required") is not True:
            return fail("clear item must require operator decision")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("clear item canonical write must be false")
        all_ids.add(required_cluster_id(item))
    for item in deferred:
        if item.get("recommended_decision_path") not in DEFER_DECISION_PATHS:
            return fail("deferred item has invalid decision path")
        if item.get("operator_decision_required") is not True:
            return fail("deferred item must require operator decision")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("deferred item canonical write must be false")
        all_ids.add(required_cluster_id(item))
    for item in no_action:
        if item.get("recommended_decision_path") != "NO_ACTION_REQUIRED":
            return fail("no-action item has invalid decision path")
        if item.get("operator_decision_required") is not False:
            return fail("no-action item must not require operator decision")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("no-action item canonical write must be false")
        all_ids.add(required_cluster_id(item))
    if len(all_ids) != EXPECTED_CLEAR_COUNT + EXPECTED_DEFER_COUNT + EXPECTED_NO_ACTION_COUNT:
        return fail("duplicate or missing cluster IDs across lanes")
    clear_counts = count_by(clear, "learning_unit_type")
    deferred_counts = count_by(deferred, "learning_unit_type")
    if summary.get("clear_learning_unit_type_counts") != clear_counts:
        return fail("clear learning unit type counts mismatch")
    if summary.get("deferred_learning_unit_type_counts") != deferred_counts:
        return fail("deferred learning unit type counts mismatch")
    expected_summary = {
        "source_review_item_count": EXPECTED_REVIEW_COUNT,
        "clear_active_lane_item_count": EXPECTED_CLEAR_COUNT,
        "deferred_lane_item_count": EXPECTED_DEFER_COUNT,
        "no_action_item_count": EXPECTED_NO_ACTION_COUNT,
        "unexpected_review_item_count": 0,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            return fail(f"{key} mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E6_A1A1PlusClearLearningUnitSchemaPlanningPacket":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason mismatch")
    print("A1/A1+ clear learning unit lane packet validation: PASS")
    return True


def required_cluster_id(item):
    cid = item.get("cluster_id")
    if not cid:
        raise ValueError("cluster_id missing")
    return cid


def count_by(items, key):
    counts = {}
    for item in items:
        value = item.get(key)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        print("FAIL: " + str(exc))
        ok = False
    if not ok:
        sys.exit(1)
