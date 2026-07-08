import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_coverage_recheck_no_new_design_docs.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_coverage_recheck_no_new_design_docs_summary.json"
TASK_ID = "R7-M104E16A_A1A1PlusCoverageRecheck_NoNewDesignDocs"
EXPECTED_TOTAL = 109
EXPECTED_COVERED = 17
EXPECTED_MISSING = 92
EXPECTED_DRAFT_ARTIFACTS = 19
EXPECTED_FIELD_TASKS = 48
EXPECTED_RATIO = round(EXPECTED_COVERED / EXPECTED_TOTAL, 6)
NEXT = "R7-M104E16B_A1A1PlusDraftArtifactFieldCompletionPatch_NoNewDesignDocs"


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: {exc}")


def validate():
    print("Validating A1/A1+ coverage recheck no-new-design-docs...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    actual = report.get("actual_canonical_coverage", {})
    if actual.get("egp_a1_total_rows") != EXPECTED_TOTAL:
        return fail("egp_a1_total_rows mismatch")
    if actual.get("canonical_covered_rows") != EXPECTED_COVERED:
        return fail("canonical_covered_rows mismatch")
    if actual.get("canonical_missing_rows") != EXPECTED_MISSING:
        return fail("canonical_missing_rows mismatch")
    if actual.get("coverage_ratio") != EXPECTED_RATIO:
        return fail("coverage_ratio mismatch")
    if actual.get("coverage_changed_by_current_draft_chain") is not False:
        return fail("draft chain must not change canonical coverage")
    guard = report.get("anti_artifact_proliferation_guard", {})
    for key in [
        "new_design_docs_created",
        "new_planning_docs_created",
        "new_review_docs_created",
        "new_sync_docs_created",
        "canonical_graph_write_allowed",
        "a2_a2plus_progression_allowed",
    ]:
        if guard.get(key) is not False:
            return fail(f"anti-artifact guard {key} must be false")
    draft = report.get("draft_only_recheck", {})
    if draft.get("draft_artifact_count") != EXPECTED_DRAFT_ARTIFACTS:
        return fail("draft_artifact_count mismatch")
    if draft.get("clear_lane_cluster_count") != EXPECTED_DRAFT_ARTIFACTS:
        return fail("clear_lane_cluster_count mismatch")
    if draft.get("draft_only_coverage_credit_now") != 0:
        return fail("draft_only_coverage_credit_now must be zero")
    items = draft.get("draft_only_items", [])
    if len(items) != EXPECTED_DRAFT_ARTIFACTS:
        return fail("draft_only_items count mismatch")
    for item in items:
        if item.get("artifact_status") != "DRAFT_NOT_CANONICAL":
            return fail("all draft items must be DRAFT_NOT_CANONICAL")
        if item.get("coverage_credit_now") != 0:
            return fail("all draft coverage_credit_now must be zero")
        if item.get("coverage_status") != "DRAFT_ONLY_NOT_CANONICAL":
            return fail("all draft coverage_status must be DRAFT_ONLY_NOT_CANONICAL")
        if not item.get("cluster_id") or not item.get("learning_unit_type"):
            return fail("draft item missing cluster_id or learning_unit_type")
    draft_missing = draft.get("draft_only_missing_row_count")
    if not isinstance(draft_missing, int) or draft_missing <= 0 or draft_missing > EXPECTED_MISSING:
        return fail("draft_only_missing_row_count invalid")
    missing = report.get("missing_recheck", {})
    if missing.get("canonical_missing_rows") != EXPECTED_MISSING:
        return fail("missing_recheck canonical_missing_rows mismatch")
    if missing.get("missing_rows_represented_by_clear_lane_drafts") != draft_missing:
        return fail("missing rows represented by drafts mismatch")
    if missing.get("missing_rows_not_in_clear_lane_drafts") != EXPECTED_MISSING - draft_missing:
        return fail("missing_rows_not_in_clear_lane_drafts mismatch")
    theoretical = report.get("theoretical_after_future_promotion", {}).get("if_all_19_clear_lane_drafts_are_completed_and_promoted", {})
    expected_theoretical_covered = min(EXPECTED_TOTAL, EXPECTED_COVERED + draft_missing)
    if theoretical.get("covered_rows") != expected_theoretical_covered:
        return fail("theoretical covered rows mismatch")
    bundle = report.get("field_completion_bundle_status", {})
    if bundle.get("field_bundle_task_count") != EXPECTED_FIELD_TASKS:
        return fail("field bundle task count mismatch")
    if bundle.get("actual_field_values_materialized") is not False:
        return fail("actual_field_values_materialized must be false")
    for key in ["draft_artifact_update_allowed_now", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if bundle.get(key) is not False:
            return fail(f"bundle {key} must be false")
    expected_summary = {
        "validation_status": "PASS",
        "egp_a1_total_rows": EXPECTED_TOTAL,
        "canonical_covered_rows": EXPECTED_COVERED,
        "canonical_missing_rows": EXPECTED_MISSING,
        "canonical_coverage_ratio": EXPECTED_RATIO,
        "coverage_changed_by_current_draft_chain": False,
        "draft_artifact_count": EXPECTED_DRAFT_ARTIFACTS,
        "clear_lane_cluster_count": EXPECTED_DRAFT_ARTIFACTS,
        "draft_only_coverage_credit_now": 0,
        "missing_rows_not_in_clear_lane_drafts": EXPECTED_MISSING - draft_missing,
        "theoretical_covered_rows_after_clear_lane_promotion": expected_theoretical_covered,
        "theoretical_missing_rows_after_clear_lane_promotion": EXPECTED_TOTAL - expected_theoretical_covered,
        "field_bundle_task_count": EXPECTED_FIELD_TASKS,
        "actual_field_values_materialized": False,
        "new_design_docs_created": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "next_short_step": NEXT,
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            return fail(f"summary {key} mismatch")
    if summary.get("draft_only_missing_row_count") != draft_missing:
        return fail("summary draft_only_missing_row_count mismatch")
    if report.get("next_short_step") != NEXT or report.get("stop_reason") != "OPERATOR_APPROVAL_REQUIRED":
        return fail("next step or stop reason mismatch")
    print("A1/A1+ coverage recheck no-new-design-docs validation: PASS")
    print("Canonical coverage:", summary["canonical_covered_rows"], "/", summary["egp_a1_total_rows"], f"({summary['canonical_coverage_percent']}%)")
    print("Draft-only missing rows:", summary["draft_only_missing_row_count"])
    print("Missing not in clear lane drafts:", summary["missing_rows_not_in_clear_lane_drafts"])
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
