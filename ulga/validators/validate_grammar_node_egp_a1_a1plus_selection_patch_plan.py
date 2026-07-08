import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_selection_patch_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_selection_patch_plan_summary.json"
EXPECTED_TASK = "R7-M99C_A1A1PLUSSelectionPatchPlanBuilder"
VALID_ACTIONS = {
    "PLAN_EGP_AUTHORITY_REFS_PATCH",
    "PLAN_EGP_FORM_ONLY_REFS_PATCH",
    "PLAN_DEFER_NO_CANONICAL_PATCH",
}


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
    print("Validating A1/A1_PLUS selection patch plan...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required patch plan reports missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if report.get("patch_plan_scope") != "A1_A1PLUS_PATCH_PLAN_NO_CANONICAL_WRITE":
        return fail("patch_plan_scope mismatch")
    records = report.get("records", [])
    if not records:
        return fail("records missing")
    counts = {}
    ids = set()
    for record in records:
        grammar_id = record.get("grammar_id")
        if not grammar_id or grammar_id in ids:
            return fail("missing or duplicate grammar_id")
        ids.add(grammar_id)
        action = record.get("planned_action")
        if action not in VALID_ACTIONS:
            return fail("invalid planned action")
        counts[action] = counts.get(action, 0) + 1
        refs = record.get("selected_egp_refs", [])
        if record.get("selected_ref_count") != len(refs):
            return fail("selected_ref_count mismatch")
        if action == "PLAN_EGP_AUTHORITY_REFS_PATCH":
            if record.get("target_field") != "egp_evidence_refs" or not refs:
                return fail("authority patch plan invalid")
        if action == "PLAN_EGP_FORM_ONLY_REFS_PATCH":
            if record.get("target_field") != "egp_form_evidence_refs" or not refs:
                return fail("form-only patch plan invalid")
        if action == "PLAN_DEFER_NO_CANONICAL_PATCH":
            if record.get("target_field") is not None or refs or record.get("write_target_path") is not None:
                return fail("defer patch plan invalid")
        if record.get("canonical_write_allowed") is not False:
            return fail("canonical write must be false")
    constraints = report.get("scope_constraints", {})
    for key in [
        "canonical_grammar_write_allowed",
        "egp_evidence_refs_write_allowed",
        "coverage_increase_allowed",
        "practicebank_generation_allowed",
        "learner_state_write_allowed",
        "runtime_change_allowed",
    ]:
        if constraints.get(key) is not False:
            return fail(f"constraint must be false: {key}")
    if summary.get("source_target_count") != len(records):
        return fail("source target count mismatch")
    if summary.get("planned_action_counts") != dict(sorted(counts.items())):
        return fail("planned action counts mismatch")
    if summary.get("planned_patch_target_count") != counts.get("PLAN_EGP_AUTHORITY_REFS_PATCH", 0) + counts.get("PLAN_EGP_FORM_ONLY_REFS_PATCH", 0):
        return fail("planned patch target count mismatch")
    if summary.get("planned_defer_target_count") != counts.get("PLAN_DEFER_NO_CANONICAL_PATCH", 0):
        return fail("planned defer target count mismatch")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("summary canonical write must be false")
    if summary.get("next_short_step") != "R7-M99D_A1A1PLUSCanonicalPatchApplierBuilder":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1/A1_PLUS selection patch plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
