import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_cluster_bridge_plan.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_cluster_bridge_plan_summary.json"
TASK_ID = "R7-M104E2_CambridgeOfficialClusterBridgePlan"
REQUIRED_SOURCE_IDS = {
    "CAMBRIDGE_OFFICIAL_A1_MOVERS_PAGE",
    "CAMBRIDGE_OFFICIAL_PRE_A1_STARTERS_PAGE",
    "CAMBRIDGE_OFFICIAL_A2_FLYERS_PAGE",
    "CAMBRIDGE_OFFICIAL_A2_KEY_PAGE",
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
    print("Validating A1 EGP alignment Cambridge official cluster bridge plan...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required bridge plan files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = report.get("bridge_items", [])
    if summary.get("bridge_item_count") != len(items):
        return fail("bridge_item_count mismatch")
    if not items:
        return fail("bridge_items missing")
    source_validation = report.get("official_source_validation", {})
    if source_validation.get("official_cambridge_source_verified") is not True:
        return fail("official Cambridge source must be verified")
    if source_validation.get("required_official_sources_present") is not True:
        return fail("required official sources must be present")
    used_sources = set()
    ids = set()
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        used_sources.add(item.get("primary_cambridge_exam_context_source"))
        used_sources.add(item.get("lower_bound_context_source"))
        used_sources.update(item.get("upper_bound_context_sources", []))
        if item.get("egp_authority_role") != "primary_grammar_row_authority":
            return fail("EGP must remain primary grammar-row authority")
        if item.get("cambridge_official_role") != "exam_level_context_support_only":
            return fail("Cambridge official role must be exam-level context only")
        if item.get("per_cluster_official_cambridge_grammar_authority") is not False:
            return fail("per-cluster Cambridge grammar authority must be false")
        if item.get("operator_patch_decision_allowed") is not True:
            return fail("operator patch decision must be allowed after bridge policy")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("canonical write must remain false")
    if not REQUIRED_SOURCE_IDS.issubset(used_sources):
        return fail("required official source IDs not used in bridge items")
    if report.get("per_cluster_official_cambridge_bridge_ready") is not False or summary.get("per_cluster_official_cambridge_bridge_ready") is not False:
        return fail("per-cluster official bridge must not be ready")
    if report.get("operator_patch_decision_allowed") is not True or summary.get("operator_patch_decision_allowed") is not True:
        return fail("operator patch decision allowed mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104F_A1EGPAlignmentPatchLaneTop10OperatorDecisionFill":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_DECISION_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment Cambridge official cluster bridge plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
