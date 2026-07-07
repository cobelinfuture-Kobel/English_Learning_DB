import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_refined_candidate_search.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_refined_candidate_search_summary.json"
EXPECTED_TASK = "R7-M96A_A1A1PLUSBulkRefinedEGPCandidateSearch"
MIN_REFINED_TARGETS = 5


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
    print("Validating A1/A1_PLUS refined candidate search...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required reports missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if report.get("search_scope") != "BULK_REFINED_QUERY_PREPARATION_ONLY":
        return fail("search_scope mismatch")
    records = report.get("records", [])
    if len(records) < MIN_REFINED_TARGETS:
        return fail("too few refined search targets")
    ids = set()
    for record in records:
        grammar_id = record.get("grammar_id")
        if not grammar_id or grammar_id in ids:
            return fail("missing or duplicate grammar_id")
        ids.add(grammar_id)
        if record.get("search_status") != "REFINED_SEARCH_QUERY_READY":
            return fail("search status mismatch")
        if not record.get("query_seeds"):
            return fail("query seeds missing")
        if record.get("candidate_row_ids") != []:
            return fail("candidate_row_ids must remain empty in query preparation step")
        if record.get("canonical_write_allowed") is not False:
            return fail("canonical_write_allowed must be false")
        if record.get("operator_review_required") is not True:
            return fail("operator_review_required must be true")
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
    if summary.get("refined_search_target_count") != len(records):
        return fail("refined target count mismatch")
    if summary.get("query_ready_count") != len(records):
        return fail("query ready count mismatch")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("canonical write must be false")
    if summary.get("next_short_step") != "R7-M97A_A1A1PLUSBulkEGPRowCandidateResolver":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1/A1_PLUS refined candidate search validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
