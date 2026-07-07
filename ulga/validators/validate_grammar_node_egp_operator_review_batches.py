import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BATCHES_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_operator_review_batches.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_operator_review_batches_summary.json"
REQUIRED_TOP = {"task_id", "artifact_id", "batch_size", "allowed_decisions", "batches", "scope_constraints"}
REQUIRED_SUMMARY = {"task_id", "artifact_id", "validation_status", "batch_size", "batch_count", "item_count", "priority_counts", "operator_review_required", "next_short_step", "stop_reason"}
REQUIRED_ITEM = {"grammar_id", "review_priority", "system_stage", "node_status", "candidate_suggestions", "allowed_decisions", "operator_decision_required", "selected_egp_row_id", "operator_reason", "learner_state_write", "practicebank_generation"}
DECISIONS = ["ACCEPT_EGP_ROW", "REJECT_ALL_CANDIDATES", "MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED", "DEFER", "REQUEST_REFINED_CANDIDATES"]


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_shapes(batches, summary):
    if not isinstance(batches, dict):
        return fail("batches must be an object")
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    if REQUIRED_TOP - set(batches):
        return fail(f"batches missing fields: {sorted(REQUIRED_TOP - set(batches))}")
    if REQUIRED_SUMMARY - set(summary):
        return fail(f"summary missing fields: {sorted(REQUIRED_SUMMARY - set(summary))}")
    expected = "R7-M53_GrammarNodeEGPOperatorReviewBatchBuilderImplementation"
    if batches["task_id"] != expected or summary["task_id"] != expected:
        return fail("task_id mismatch")
    if batches["allowed_decisions"] != DECISIONS:
        return fail("allowed_decisions mismatch")
    if summary["next_short_step"] != "R7-M54_GrammarNodeEGPOperatorReviewBatchReadback":
        return fail("next_short_step mismatch")
    if summary["stop_reason"] != "NONE":
        return fail("stop_reason must be NONE")
    return True


def validate_scope(batches):
    scope = batches["scope_constraints"]
    for key in ["no_runtime_implementation", "no_practicebank_generation", "no_learner_state_write", "no_auto_egp_row_selection", "no_authority_write"]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    return True


def validate_batches(batches, summary):
    batch_list = batches["batches"]
    if not isinstance(batch_list, list):
        return fail("batches must be a list")
    if summary["batch_count"] != len(batch_list):
        return fail("batch_count mismatch")
    total = 0
    priority_counts = {}
    for batch in batch_list:
        if batch.get("batch_status") != "OPERATOR_REVIEW_REQUIRED":
            return fail("batch_status must require operator review")
        items = batch.get("items", [])
        if batch.get("item_count") != len(items):
            return fail("batch item_count mismatch")
        if len(items) > batches["batch_size"]:
            return fail("batch exceeds batch_size")
        for item in items:
            if REQUIRED_ITEM - set(item):
                return fail(f"item missing fields: {sorted(REQUIRED_ITEM - set(item))}")
            if item["allowed_decisions"] != DECISIONS:
                return fail("item allowed_decisions mismatch")
            if item["operator_decision_required"] is not True:
                return fail("operator_decision_required must be true")
            if item["selected_egp_row_id"] is not None:
                return fail("selected_egp_row_id must be null before review")
            if item["operator_reason"] is not None:
                return fail("operator_reason must be null before review")
            if item["learner_state_write"] is not False:
                return fail("learner_state_write must be false")
            if item["practicebank_generation"] is not False:
                return fail("practicebank_generation must be false")
            key = item.get("review_priority") or "UNKNOWN"
            priority_counts[key] = priority_counts.get(key, 0) + 1
            total += 1
    if summary["item_count"] != total:
        return fail("item_count mismatch")
    if summary["priority_counts"] != dict(sorted(priority_counts.items())):
        return fail("priority_counts mismatch")
    if summary["operator_review_required"] is not True:
        return fail("operator_review_required must be true")
    return True


def validate():
    print("Validating Grammar Node EGP Operator Review Batches...")
    for path in [BATCHES_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    batches = read_json(BATCHES_PATH)
    summary = read_json(SUMMARY_PATH)
    if batches is None or summary is None:
        return False
    if not validate_shapes(batches, summary):
        return False
    if not validate_scope(batches):
        return False
    if not validate_batches(batches, summary):
        return False
    print("Grammar Node EGP Operator Review Batches validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
