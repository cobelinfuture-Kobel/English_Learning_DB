import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_decision_buckets.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_decision_buckets_summary.json"
EXPECTED_TASK = "R7-M99A_A1A1PLUSBulkCandidateDecisionBucketBuilder"
VALID_BUCKETS = {"OPERATOR_REVIEW_REQUIRED", "REJECT_BROAD_ONLY", "NO_SAFE_CANDIDATE"}


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
    print("Validating A1/A1_PLUS candidate decision buckets...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required decision bucket reports missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if report.get("decision_scope") != "BULK_CANDIDATE_BUCKETS_NO_CANONICAL_WRITE":
        return fail("decision_scope mismatch")
    records = report.get("records", [])
    if not records:
        return fail("records missing")
    bucket_counts = {}
    ids = set()
    for record in records:
        grammar_id = record.get("grammar_id")
        if not grammar_id or grammar_id in ids:
            return fail("missing or duplicate grammar_id")
        ids.add(grammar_id)
        bucket = record.get("decision_bucket")
        if bucket not in VALID_BUCKETS:
            return fail("unexpected decision bucket")
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if record.get("auto_accept_allowed") is not False:
            return fail("auto_accept_allowed must be false")
        if record.get("canonical_write_allowed") is not False:
            return fail("canonical write must be false")
        if record.get("operator_review_required") != (bucket == "OPERATOR_REVIEW_REQUIRED"):
            return fail("operator review flag mismatch")
        if record.get("review_candidate_count", 0) != len(record.get("review_candidates", [])) and len(record.get("review_candidates", [])) > 3:
            return fail("review candidate count invalid")
    constraints = report.get("scope_constraints", {})
    for key in [
        "auto_accept_allowed",
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
    if summary.get("bucketed_target_count") != len(records):
        return fail("bucketed target count mismatch")
    if summary.get("bucket_counts") != dict(sorted(bucket_counts.items())):
        return fail("bucket counts mismatch")
    if summary.get("auto_accept_count") != 0:
        return fail("auto_accept_count must be zero")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("summary canonical write must be false")
    if summary.get("next_short_step") != "R7-M100A_A1A1PLUSOperatorReviewPacketBuilder":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1/A1_PLUS candidate decision bucket validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
