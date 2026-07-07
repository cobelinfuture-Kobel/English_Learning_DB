import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PACKET_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_operator_review_batches.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_operator_review_batches_summary.json"
EXPECTED_TASK = "R7-M58R_RefinedOperatorReviewBatchRefresh"


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def fail(message):
    print("FAIL: " + message)
    return False


def validate():
    print("Validating R7-M58R refined review packet...")
    if not PACKET_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("missing required JSON output")
    packet = load(PACKET_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(packet, dict) or not isinstance(summary, dict):
        return fail("top-level output must be JSON objects")
    if packet.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    scope = packet.get("scope_constraints", {})
    for key in scope:
        if scope[key] is not True:
            return fail(f"scope flag is not true: {key}")
    batches = packet.get("batches")
    if not isinstance(batches, list):
        return fail("batches must be a list")
    if summary.get("batch_count") != len(batches):
        return fail("batch_count mismatch")
    item_count = 0
    refined_count = 0
    empty_count = 0
    batch_size = packet.get("batch_size")
    for batch in batches:
        items = batch.get("items", [])
        if batch.get("item_count") != len(items):
            return fail("batch item_count mismatch")
        if batch_size is not None and len(items) > batch_size:
            return fail("batch too large")
        for item in items:
            options = item.get("refined_candidate_suggestions", [])
            if not isinstance(options, list):
                return fail("refined options must be a list")
            if item.get("operator_decision_required") is not True:
                return fail("review flag missing")
            if item.get("learner_state_write") is not False:
                return fail("learner state flag must be false")
            if item.get("practicebank_generation") is not False:
                return fail("practice flag must be false")
            refined_count += len(options)
            empty_count += 1 if not options else 0
            item_count += 1
    if summary.get("item_count") != item_count:
        return fail("summary item_count mismatch")
    if summary.get("total_refined_candidate_count") != refined_count:
        return fail("summary refined candidate count mismatch")
    if summary.get("items_without_refined_candidates") != empty_count:
        return fail("summary empty refined item count mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("R7-M58R refined review packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
