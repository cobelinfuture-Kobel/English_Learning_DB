import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REFINED_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_candidate_suggestions_summary.json"
BANDS = {"HIGH", "MEDIUM", "LOW"}
REQUIRED_TOP = {"task_id", "artifact_id", "source_path", "max_refined_candidates_per_node", "minimum_candidate_score", "records", "scope_constraints"}
REQUIRED_SUMMARY = {"task_id", "artifact_id", "validation_status", "source_record_count", "refined_record_count", "total_refined_candidate_count", "records_without_refined_candidates", "removed_candidate_count", "confidence_band_counts", "max_refined_candidates_per_node", "operator_review_required", "next_short_step", "stop_reason"}
REQUIRED_RECORD = {"grammar_id", "review_priority", "system_stage", "node_status", "refined_candidate_suggestions", "review_required", "learner_state_write", "practicebank_generation"}
REQUIRED_OPTION = {"egp_row_id", "egp_level", "super_category", "sub_category", "guideword", "candidate_score", "candidate_reason", "review_required", "confidence_band"}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_shapes(refined, summary):
    if not isinstance(refined, dict):
        return fail("refined suggestions must be an object")
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    if REQUIRED_TOP - set(refined):
        return fail(f"refined suggestions missing fields: {sorted(REQUIRED_TOP - set(refined))}")
    if REQUIRED_SUMMARY - set(summary):
        return fail(f"summary missing fields: {sorted(REQUIRED_SUMMARY - set(summary))}")
    expected = "R7-M56R_GrammarNodeEGPRefinedCandidateBuilderImplementation"
    if refined["task_id"] != expected or summary["task_id"] != expected:
        return fail("task_id mismatch")
    if summary["next_short_step"] != "R7-M57R_GrammarNodeEGPRefinedCandidateReadback":
        return fail("next_short_step mismatch")
    if summary["stop_reason"] != "NONE":
        return fail("stop_reason must be NONE")
    return True


def validate_scope(refined):
    scope = refined["scope_constraints"]
    for key in ["no_runtime_implementation", "no_practicebank_generation", "no_learner_state_write", "no_auto_egp_row_selection", "no_authority_write"]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    return True


def validate_records(refined, summary):
    records = refined["records"]
    if not isinstance(records, list):
        return fail("records must be a list")
    if summary["refined_record_count"] != len(records):
        return fail("refined_record_count mismatch")
    total = 0
    no_safe = 0
    bands = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for record in records:
        if REQUIRED_RECORD - set(record):
            return fail(f"record missing fields: {sorted(REQUIRED_RECORD - set(record))}")
        if record["review_required"] is not True:
            return fail("record review_required must be true")
        if record["learner_state_write"] is not False:
            return fail("learner_state_write must be false")
        if record["practicebank_generation"] is not False:
            return fail("practicebank_generation must be false")
        options = record["refined_candidate_suggestions"]
        if len(options) > refined["max_refined_candidates_per_node"]:
            return fail("too many refined options for one record")
        if not options:
            no_safe += 1
        last_score = None
        for option in options:
            if REQUIRED_OPTION - set(option):
                return fail(f"option missing fields: {sorted(REQUIRED_OPTION - set(option))}")
            if option["review_required"] is not True:
                return fail("option review_required must be true")
            score = option["candidate_score"]
            if score < refined["minimum_candidate_score"]:
                return fail("option below minimum score")
            if option["confidence_band"] not in BANDS:
                return fail("invalid confidence_band")
            if last_score is not None and score > last_score:
                return fail("options must be sorted by descending score")
            last_score = score
            bands[option["confidence_band"]] += 1
        total += len(options)
    if summary["total_refined_candidate_count"] != total:
        return fail("total_refined_candidate_count mismatch")
    if summary["records_without_refined_candidates"] != no_safe:
        return fail("records_without_refined_candidates mismatch")
    if summary["confidence_band_counts"] != bands:
        return fail("confidence_band_counts mismatch")
    if summary["operator_review_required"] is not True:
        return fail("operator_review_required must be true")
    return True


def validate():
    print("Validating Refined Grammar Node EGP Candidate Suggestions...")
    for path in [REFINED_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    refined = read_json(REFINED_PATH)
    summary = read_json(SUMMARY_PATH)
    if refined is None or summary is None:
        return False
    if not validate_shapes(refined, summary):
        return False
    if not validate_scope(refined):
        return False
    if not validate_records(refined, summary):
        return False
    print("Refined Grammar Node EGP Candidate Suggestions validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
