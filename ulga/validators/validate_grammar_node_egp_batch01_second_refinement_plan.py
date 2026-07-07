import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PLAN_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_plan_summary.json"
EXPECTED_TASK = "R7-M67_Batch01SecondRefinementPlanArtifactBuilder"
VALID_ACTIONS = {"SECOND_PASS_REFINE", "SOURCE_ROW_AUDIT"}
VALID_DECISIONS = {"REQUEST_REFINED_CANDIDATES", "DEFER"}


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
    print("Validating Batch 01 second refinement plan...")
    if not PLAN_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    plan = load(PLAN_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(plan, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if plan.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    scope = plan.get("scope_constraints", {})
    for key in ["no_runtime_implementation", "no_practicebank_generation", "no_learner_state_write", "no_auto_egp_row_selection", "no_authority_write", "no_egp_evidence_refs_write", "no_coverage_increase"]:
        if scope.get(key) is not True:
            return fail(f"scope flag not true: {key}")
    targets = plan.get("targets", [])
    if summary.get("target_count") != len(targets):
        return fail("target_count mismatch")
    action_counts = {}
    decision_counts = {}
    for target in targets:
        action = target.get("refinement_action")
        decision = target.get("operator_decision")
        if action not in VALID_ACTIONS:
            return fail("invalid refinement_action")
        if decision not in VALID_DECISIONS:
            return fail("invalid operator_decision")
        if target.get("operator_review_required") is not True:
            return fail("operator_review_required must be true on each target")
        if action == "SOURCE_ROW_AUDIT" and not target.get("candidate_to_audit"):
            return fail("audit target missing candidate_to_audit")
        if action == "SECOND_PASS_REFINE":
            if not target.get("guideword_include"):
                return fail("second pass target missing guideword_include")
            if not target.get("guideword_exclude"):
                return fail("second pass target missing guideword_exclude")
        action_counts[action] = action_counts.get(action, 0) + 1
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    if summary.get("action_counts") != action_counts:
        return fail("action_counts mismatch")
    if summary.get("decision_counts") != decision_counts:
        return fail("decision_counts mismatch")
    if summary.get("operator_review_required") is not True:
        return fail("summary operator_review_required must be true")
    if summary.get("next_short_step") != "R7-M68_Batch01SecondRefinementPlanReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 second refinement plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
