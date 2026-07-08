import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver_summary.json"
EXPECTED_TASK = "R7-M97C_A1A1PLUSBulkEGPRowCandidateResolverWithCompactIndex"


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
    print("Validating A1/A1_PLUS candidate resolver...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required resolver reports missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if report.get("source_index_status") not in {"READY", "MISSING"}:
        return fail("source_index_status invalid")
    records = report.get("records", [])
    if not records:
        return fail("records missing")
    ids = set()
    candidate_total = 0
    resolved_count = 0
    for record in records:
        grammar_id = record.get("grammar_id")
        if not grammar_id or grammar_id in ids:
            return fail("missing or duplicate grammar_id")
        ids.add(grammar_id)
        if record.get("canonical_write_allowed") is not False:
            return fail("canonical write must be false")
        if record.get("operator_review_required") is not True:
            return fail("operator review must be true")
        candidates = record.get("candidates", [])
        if len(candidates) != record.get("candidate_count"):
            return fail("candidate count mismatch")
        for candidate in candidates:
            if not candidate.get("egp_source_ref") or "score" not in candidate:
                return fail("candidate missing source ref or score")
        if candidates:
            resolved_count += 1
        candidate_total += len(candidates)
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
    if summary.get("source_refined_target_count") != len(records):
        return fail("source target count mismatch")
    if summary.get("resolved_target_count") != resolved_count:
        return fail("resolved target count mismatch")
    if summary.get("total_candidate_count") != candidate_total:
        return fail("total candidate count mismatch")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("summary canonical write must be false")
    if summary.get("operator_review_required") is not True:
        return fail("summary operator review must be true")
    if summary.get("next_short_step") != "R7-M98A_A1A1PLUSBulkCandidateResolverReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1/A1_PLUS candidate resolver validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
