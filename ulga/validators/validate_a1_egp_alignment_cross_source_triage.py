import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage_summary.json"
TASK_ID = "R7-M104B_A1EGPAlignmentCrossSourceEvidenceTriage"
VALID_RECOMMENDATIONS = {
    "NO_ACTION_REQUIRED",
    "DEFER_NEEDS_SOURCE_INDEXING",
    "REVIEW_CREATE_OR_PATCH_WITH_USAGE_AND_EXAM_SUPPORT",
    "REVIEW_EXAM_ALIGNED_GRAMMAR_NODE",
    "REVIEW_LEXICAL_OR_LEXICAL_GRAMMAR_BRIDGE",
    "REVIEW_USAGE_ONLY_SUPPORT",
    "DEFER_SOURCE_AMBIGUOUS",
}
VALID_MATCH_STATUS = {"MATCH", "NO_MATCH", "READY", "SOURCE_NOT_INDEXED", "SOURCE_PRESENT_BUT_OPENPYXL_UNAVAILABLE"}


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
    print("Validating A1 EGP alignment cross-source triage...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required triage files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = report.get("triage_items", [])
    if not items:
        return fail("triage_items missing")
    rec_counts = {}
    confidence_counts = {}
    source_status_counts = {"evp": {}, "raz": {}, "cambridge": {}}
    ids = set()
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        rec = item.get("recommended_operator_decision")
        if rec not in VALID_RECOMMENDATIONS:
            return fail("invalid recommended_operator_decision")
        if item.get("confidence") not in {"HIGH", "MEDIUM", "LOW"}:
            return fail("invalid confidence")
        for key, source_field in [("evp", "evp_match"), ("raz", "raz_usage_match"), ("cambridge", "cambridge_exam_match")]:
            status = item.get(source_field, {}).get("status")
            if status not in VALID_MATCH_STATUS:
                return fail(f"invalid source match status: {key}")
            source_status_counts[key][status] = source_status_counts[key].get(status, 0) + 1
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("item canonical write must be false")
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
        confidence_counts[item.get("confidence")] = confidence_counts.get(item.get("confidence"), 0) + 1
    if summary.get("cluster_count") != len(items):
        return fail("cluster_count mismatch")
    if summary.get("recommendation_counts") != dict(sorted(rec_counts.items())):
        return fail("recommendation_counts mismatch")
    if summary.get("confidence_counts") != dict(sorted(confidence_counts.items())):
        return fail("confidence_counts mismatch")
    if summary.get("source_status_counts") != source_status_counts:
        return fail("source_status_counts mismatch")
    source_indexes = report.get("source_indexes", {})
    computed_source_indexing_required = any((source_indexes.get(key, {}).get("status") != "READY") for key in ["evp", "raz", "cambridge"])
    if summary.get("source_indexing_required") is not computed_source_indexing_required:
        return fail("source_indexing_required mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104C_A1EGPAlignmentCrossSourceTriageReviewPacket":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment cross-source triage validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
