import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_authority_patch_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_authority_patch_plan_summary.json"
EXPECTED_TASK = "R7-M87A_Batch01AuthorityPatchPlanArtifactBuilder"
EXPECTED_IDS = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
}
VALID_ACTIONS = {
    "PLAN_AUTHORITY_EGP_EVIDENCE_PATCH",
    "PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH",
    "PLAN_REFINED_EGP_CANDIDATE_REQUEST",
}


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
    print("Validating Batch 01 authority patch plan...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if data.get("plan_scope") != "PATCH_PLAN_ONLY_NO_AUTHORITY_WRITE":
        return fail("plan_scope mismatch")
    scope = data.get("scope_constraints", {})
    for key in [
        "no_canonical_grammar_write",
        "no_egp_evidence_refs_write",
        "no_raz_usage_attachment_write",
        "no_coverage_increase",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_runtime_change",
        "operator_review_required",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope flag must be true: {key}")
    records = data.get("records", [])
    if {record.get("grammar_id") for record in records} != EXPECTED_IDS:
        return fail("unexpected grammar ids")
    action_counts = {}
    for record in records:
        action = record.get("planned_action")
        if action not in VALID_ACTIONS:
            return fail("unexpected planned_action")
        action_counts[action] = action_counts.get(action, 0) + 1
        if record.get("write_allowed") is not False:
            return fail("record write_allowed must be false")
        if record.get("operator_review_required") is not True:
            return fail("record operator_review_required must be true")
        if action == "PLAN_REFINED_EGP_CANDIDATE_REQUEST":
            if record.get("selected_egp_row_id") is not None or record.get("selected_egp_evidence_role") is not None:
                return fail("refined request must not include selected EGP evidence")
            if record.get("write_target_path") is not None:
                return fail("refined request must not include write target")
        else:
            if not record.get("selected_egp_row_id") or not record.get("selected_egp_evidence_role"):
                return fail("patch action must include selected EGP evidence")
            if record.get("write_target_path") != "ulga/grammar/grammar_nodes.json":
                return fail("patch action write target mismatch")
    if summary.get("target_count") != len(records):
        return fail("target_count mismatch")
    if summary.get("action_counts") != dict(sorted(action_counts.items())):
        return fail("action_counts mismatch")
    if summary.get("planned_authority_patch_count") != action_counts.get("PLAN_AUTHORITY_EGP_EVIDENCE_PATCH", 0):
        return fail("authority patch count mismatch")
    if summary.get("planned_form_only_patch_count") != action_counts.get("PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH", 0):
        return fail("form-only patch count mismatch")
    if summary.get("planned_refined_candidate_request_count") != action_counts.get("PLAN_REFINED_EGP_CANDIDATE_REQUEST", 0):
        return fail("refined request count mismatch")
    for key in [
        "write_allowed",
        "canonical_grammar_write_allowed",
        "egp_evidence_refs_write_allowed",
        "raz_usage_attachment_write_allowed",
        "coverage_increase_allowed",
    ]:
        if summary.get(key) is not False:
            return fail(f"summary flag must be false: {key}")
    if summary.get("operator_review_required") is not True:
        return fail("summary operator_review_required must be true")
    if summary.get("next_short_step") != "R7-M88A_Batch01AuthorityPatchPlanReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 authority patch plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
