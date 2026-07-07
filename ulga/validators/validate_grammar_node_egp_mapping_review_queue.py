import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

REVIEW_QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue_summary.json"

REQUIRED_QUEUE_FIELDS = {
    "task_id",
    "artifact_id",
    "source_paths",
    "records",
    "scope_constraints",
}
REQUIRED_SUMMARY_FIELDS = {
    "task_id",
    "artifact_id",
    "validation_status",
    "review_queue_count",
    "priority_counts",
    "node_status_counts",
    "stage_counts",
    "candidate_generation_allowed",
    "candidate_promotion_allowed",
    "next_short_step",
    "stop_reason",
}
REQUIRED_RECORD_FIELDS = {
    "grammar_id",
    "label",
    "category",
    "system_stage",
    "authority_status",
    "node_status",
    "alignment_status",
    "review_priority",
    "review_reason",
    "allowed_next_action",
    "candidate_generation_allowed",
    "candidate_promotion_allowed",
    "learner_state_write",
    "practicebank_generation",
    "missing_egp_refs",
    "source_ref_fields",
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_shapes(queue, summary):
    if not isinstance(queue, dict):
        return fail("review queue must be an object")
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    missing_queue = REQUIRED_QUEUE_FIELDS - set(queue)
    if missing_queue:
        return fail(f"review queue missing fields: {sorted(missing_queue)}")
    missing_summary = REQUIRED_SUMMARY_FIELDS - set(summary)
    if missing_summary:
        return fail(f"summary missing fields: {sorted(missing_summary)}")
    expected_task = "R7-M48_GrammarNodeEGPMappingReviewQueueBuilderImplementation"
    if queue["task_id"] != expected_task:
        return fail("review queue task_id mismatch")
    if summary["task_id"] != expected_task:
        return fail("summary task_id mismatch")
    if summary["next_short_step"] != "R7-M49_GrammarNodeEGPCandidateSuggestionPolicyScan":
        return fail("summary next_short_step mismatch")
    if summary["stop_reason"] != "NONE":
        return fail("summary stop_reason must be NONE")
    return True


def validate_scope(queue, summary):
    scope = queue["scope_constraints"]
    for key in [
        "no_runtime_implementation",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_ai_mapping_promotion",
        "no_new_evidence_selection",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    if summary["candidate_generation_allowed"] is not True:
        return fail("candidate_generation_allowed must be true")
    if summary["candidate_promotion_allowed"] is not False:
        return fail("candidate_promotion_allowed must be false")
    return True


def validate_records(queue, summary):
    records = queue["records"]
    if not isinstance(records, list):
        return fail("records must be a list")
    if summary["review_queue_count"] != len(records):
        return fail("review_queue_count mismatch")
    priority_counts = {}
    node_status_counts = {}
    stage_counts = {}
    for record in records:
        if not isinstance(record, dict):
            return fail("record must be an object")
        missing = REQUIRED_RECORD_FIELDS - set(record)
        if missing:
            return fail(f"record missing fields: {sorted(missing)}")
        if record["candidate_generation_allowed"] is not True:
            return fail("record candidate_generation_allowed must be true")
        if record["candidate_promotion_allowed"] is not False:
            return fail("record candidate_promotion_allowed must be false")
        if record["learner_state_write"] is not False:
            return fail("record learner_state_write must be false")
        if record["practicebank_generation"] is not False:
            return fail("record practicebank_generation must be false")
        priority_counts[record["review_priority"]] = priority_counts.get(record["review_priority"], 0) + 1
        node_status_counts[record["node_status"]] = node_status_counts.get(record["node_status"], 0) + 1
        stage_counts[record["system_stage"]] = stage_counts.get(record["system_stage"], 0) + 1
    if summary["priority_counts"] != dict(sorted(priority_counts.items())):
        return fail("priority_counts mismatch")
    if summary["node_status_counts"] != dict(sorted(node_status_counts.items())):
        return fail("node_status_counts mismatch")
    if summary["stage_counts"] != dict(sorted(stage_counts.items())):
        return fail("stage_counts mismatch")
    return True


def validate():
    print("Validating Grammar Node EGP Mapping Review Queue...")
    for path in [REVIEW_QUEUE_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    queue = read_json(REVIEW_QUEUE_PATH)
    summary = read_json(SUMMARY_PATH)
    if queue is None or summary is None:
        return False
    if not validate_shapes(queue, summary):
        return False
    if not validate_scope(queue, summary):
        return False
    if not validate_records(queue, summary):
        return False
    print("Grammar Node EGP Mapping Review Queue validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
