import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_deterministic_selection.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_deterministic_selection_summary.json"
EXPECTED_TASK = "R7-M99B_A1A1PLUSDeterministicEGPSelection"
VALID_DECISIONS = {
    "SELECT_AUTHORITY_EVIDENCE",
    "SELECT_FORM_ONLY_EVIDENCE",
    "DEFER_REFINED_SOURCE_REQUIRED",
    "DEFER_COMPOSITIONAL_SOURCE_REQUIRED",
    "DEFER_NO_DETERMINISTIC_SELECTION",
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
    print("Validating A1/A1_PLUS deterministic EGP selection...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required selection reports missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if report.get("selection_scope") != "A1_A1PLUS_DETERMINISTIC_SELECTION_NO_CANONICAL_WRITE":
        return fail("selection_scope mismatch")
    records = report.get("records", [])
    if not records:
        return fail("records missing")
    ids = set()
    counts = {}
    for record in records:
        grammar_id = record.get("grammar_id")
        if not grammar_id or grammar_id in ids:
            return fail("missing or duplicate grammar_id")
        ids.add(grammar_id)
        decision = record.get("selection_decision")
        if decision not in VALID_DECISIONS:
            return fail("invalid selection decision")
        counts[decision] = counts.get(decision, 0) + 1
        refs = record.get("selected_egp_refs", [])
        if record.get("selected_ref_count") != len(refs):
            return fail("selected_ref_count mismatch")
        if decision.startswith("SELECT") and not refs:
            return fail("selected decision must include refs")
        if decision.startswith("DEFER") and refs:
            return fail("deferred decision must not include refs")
        if record.get("canonical_write_allowed") is not False:
            return fail("canonical write must be false")
        if record.get("operator_review_required") != decision.startswith("DEFER"):
            return fail("operator_review_required mismatch")
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
    if summary.get("selection_counts") != dict(sorted(counts.items())):
        return fail("selection counts mismatch")
    if summary.get("selected_authority_target_count") != counts.get("SELECT_AUTHORITY_EVIDENCE", 0):
        return fail("authority target count mismatch")
    if summary.get("selected_form_only_target_count") != counts.get("SELECT_FORM_ONLY_EVIDENCE", 0):
        return fail("form-only target count mismatch")
    if summary.get("deferred_target_count") != sum(v for k, v in counts.items() if k.startswith("DEFER")):
        return fail("deferred target count mismatch")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("summary canonical write must be false")
    if summary.get("next_short_step") != "R7-M99C_A1A1PLUSSelectionPatchPlanBuilder":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1/A1_PLUS deterministic EGP selection validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
