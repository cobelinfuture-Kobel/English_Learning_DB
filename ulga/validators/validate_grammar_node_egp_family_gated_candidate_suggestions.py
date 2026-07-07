import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_family_gated_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_family_gated_candidate_suggestions_summary.json"
EXPECTED_TASK = "R7-M62_GrammarNodeEGPFamilyGatedCandidateBuilderImplementation"


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
    print("Validating grammar-family gated candidate suggestions...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be JSON objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    scope = data.get("scope_constraints", {})
    for key in ["no_runtime_implementation", "no_practicebank_generation", "no_learner_state_write", "no_auto_egp_row_selection", "no_authority_write"]:
        if scope.get(key) is not True:
            return fail(f"scope flag not true: {key}")
    records = data.get("records", [])
    if summary.get("gated_record_count") != len(records):
        return fail("gated_record_count mismatch")
    total = 0
    missing = 0
    for record in records:
        if record.get("review_required") is not True:
            return fail("record review flag missing")
        if record.get("learner_state_write") is not False or record.get("practicebank_generation") is not False:
            return fail("record safety flags invalid")
        options = record.get("family_gated_candidate_suggestions", [])
        if len(options) > data.get("max_candidates_per_node"):
            return fail("too many options")
        if record.get("gate_configured") is True and not options:
            missing += 1
        last_score = None
        for option in options:
            if option.get("review_required") is not True:
                return fail("option review flag missing")
            if option.get("confidence_band") not in {"HIGH", "MEDIUM", "LOW"}:
                return fail("bad confidence band")
            score = option.get("candidate_score")
            if not isinstance(score, (int, float)):
                return fail("score must be numeric")
            if last_score is not None and score > last_score:
                return fail("options must be sorted descending")
            last_score = score
            total += 1
    if summary.get("total_family_gated_candidate_count") != total:
        return fail("candidate total mismatch")
    if summary.get("configured_gate_records_without_candidates") != missing:
        return fail("missing candidate count mismatch")
    if summary.get("operator_review_required") is not True:
        return fail("operator_review_required must be true")
    if summary.get("next_short_step") != "R7-M63_GrammarNodeEGPFamilyGatedCandidateReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Grammar-family gated candidate suggestions validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
