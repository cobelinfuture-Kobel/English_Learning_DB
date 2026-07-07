import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_candidates.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_candidates_summary.json"
EXPECTED_TASK = "R7-M69_Batch01SecondRefinementCandidateAuditBuilderImplementation"


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
    print("Validating Batch 01 second refinement candidate/audit report...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    scope = data.get("scope_constraints", {})
    for key in ["no_runtime_implementation", "no_practicebank_generation", "no_learner_state_write", "no_auto_egp_row_selection", "no_authority_write", "no_egp_evidence_refs_write", "no_coverage_increase"]:
        if scope.get(key) is not True:
            return fail(f"scope flag not true: {key}")
    records = data.get("records", [])
    if summary.get("record_count") != len(records):
        return fail("record_count mismatch")
    action_counts = {}
    total_candidates = 0
    audit_count = 0
    missing_candidate_targets = 0
    for record in records:
        if record.get("review_required") is not True:
            return fail("record review_required must be true")
        if record.get("learner_state_write") is not False or record.get("practicebank_generation") is not False:
            return fail("record safety flags invalid")
        action = record.get("refinement_action")
        action_counts[action] = action_counts.get(action, 0) + 1
        if action == "SECOND_PASS_REFINE":
            candidates = record.get("second_refinement_candidates", [])
            if not candidates:
                missing_candidate_targets += 1
            last_score = None
            for candidate in candidates:
                if candidate.get("review_required") is not True:
                    return fail("candidate review_required must be true")
                if candidate.get("confidence_band") not in {"HIGH", "MEDIUM", "LOW"}:
                    return fail("invalid confidence band")
                score = candidate.get("candidate_score")
                if not isinstance(score, (int, float)):
                    return fail("candidate_score must be numeric")
                if last_score is not None and score > last_score:
                    return fail("candidates must be sorted descending")
                last_score = score
                total_candidates += 1
        elif action == "SOURCE_ROW_AUDIT":
            audit = record.get("source_row_audit", {})
            if audit.get("review_required") is not True:
                return fail("audit review_required must be true")
            if not audit.get("candidate_to_audit"):
                return fail("audit candidate missing")
            audit_count += 1
        else:
            return fail("invalid refinement_action")
    if summary.get("action_counts") != action_counts:
        return fail("action_counts mismatch")
    if summary.get("total_second_refinement_candidate_count") != total_candidates:
        return fail("candidate total mismatch")
    if summary.get("source_row_audit_count") != audit_count:
        return fail("audit count mismatch")
    if summary.get("second_refine_targets_without_candidates") != missing_candidate_targets:
        return fail("missing candidate target count mismatch")
    if summary.get("operator_review_required") is not True:
        return fail("operator_review_required must be true")
    if summary.get("next_short_step") != "R7-M70_Batch01SecondRefinementCandidateAuditReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 second refinement candidate/audit report validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
