import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SUGGESTIONS_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions_summary.json"

REQUIRED_TOP = {"task_id", "artifact_id", "records", "scope_constraints"}
REQUIRED_SUMMARY = {"task_id", "artifact_id", "validation_status", "review_queue_count", "suggestion_record_count", "total_candidate_count", "max_candidates_per_node", "review_required", "next_short_step", "stop_reason"}
REQUIRED_RECORD = {"grammar_id", "review_priority", "system_stage", "node_status", "candidate_suggestions", "review_required", "learner_state_write", "practicebank_generation"}
REQUIRED_OPTION = {"egp_row_id", "egp_level", "super_category", "sub_category", "guideword", "candidate_score", "candidate_reason", "review_required"}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_shapes(suggestions, summary):
    if not isinstance(suggestions, dict):
        return fail("suggestions must be an object")
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    if REQUIRED_TOP - set(suggestions):
        return fail(f"suggestions missing fields: {sorted(REQUIRED_TOP - set(suggestions))}")
    if REQUIRED_SUMMARY - set(summary):
        return fail(f"summary missing fields: {sorted(REQUIRED_SUMMARY - set(summary))}")
    expected = "R7-M50_GrammarNodeEGPCandidateSuggestionBuilderImplementation"
    if suggestions["task_id"] != expected or summary["task_id"] != expected:
        return fail("task_id mismatch")
    if summary["next_short_step"] != "R7-M51_GrammarNodeEGPCandidateSuggestionReviewReadback":
        return fail("next_short_step mismatch")
    if summary["stop_reason"] != "NONE":
        return fail("stop_reason must be NONE")
    return True


def validate_scope(suggestions):
    scope = suggestions["scope_constraints"]
    for key in ["no_runtime_implementation", "no_practicebank_generation", "no_learner_state_write"]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    return True


def validate_records(suggestions, summary):
    records = suggestions["records"]
    if not isinstance(records, list):
        return fail("records must be a list")
    if summary["suggestion_record_count"] != len(records):
        return fail("suggestion_record_count mismatch")
    total = 0
    for record in records:
        if not isinstance(record, dict):
            return fail("record must be an object")
        if REQUIRED_RECORD - set(record):
            return fail(f"record missing fields: {sorted(REQUIRED_RECORD - set(record))}")
        if record["review_required"] is not True:
            return fail("record review_required must be true")
        if record["learner_state_write"] is not False:
            return fail("learner_state_write must be false")
        if record["practicebank_generation"] is not False:
            return fail("practicebank_generation must be false")
        options = record["candidate_suggestions"]
        if len(options) > summary["max_candidates_per_node"]:
            return fail("too many suggestions for one record")
        last_score = None
        for option in options:
            if REQUIRED_OPTION - set(option):
                return fail(f"option missing fields: {sorted(REQUIRED_OPTION - set(option))}")
            if option["review_required"] is not True:
                return fail("option review_required must be true")
            score = option["candidate_score"]
            if not isinstance(score, (int, float)) or score < 0:
                return fail("candidate_score must be non-negative number")
            if last_score is not None and score > last_score:
                return fail("suggestions must be sorted by descending score")
            last_score = score
        total += len(options)
    if summary["total_candidate_count"] != total:
        return fail("total_candidate_count mismatch")
    if summary["review_queue_count"] != len(records):
        return fail("review_queue_count mismatch")
    return True


def validate():
    print("Validating Grammar Node EGP Candidate Suggestions...")
    for path in [SUGGESTIONS_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    suggestions = read_json(SUGGESTIONS_PATH)
    summary = read_json(SUMMARY_PATH)
    if suggestions is None or summary is None:
        return False
    if not validate_shapes(suggestions, summary):
        return False
    if not validate_scope(suggestions):
        return False
    if not validate_records(suggestions, summary):
        return False
    print("Grammar Node EGP Candidate Suggestions validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
