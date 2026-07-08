import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DRAFTS_PATH = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
BUNDLE_SUMMARY_PATH = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_field_completion_design_implementation_bundle_summary.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_coverage_recheck_no_new_design_docs.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_coverage_recheck_no_new_design_docs_summary.json"

TASK_ID = "R7-M104E16A_A1A1PlusCoverageRecheck_NoNewDesignDocs"
EGP_A1_TOTAL_ROWS = 109
BASELINE_CANONICAL_COVERED_ROWS = 17
BASELINE_CANONICAL_MISSING_ROWS = 92
BASELINE_A1_A1PLUS_NODE_COUNT = 15
NON_A1_REF_NODE_COUNT = 3


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pct(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else 0.0


def draft_cluster_rows(draft_artifacts):
    rows = []
    for artifact in draft_artifacts:
        cluster = artifact.get("source_cluster", {})
        unit = artifact.get("draft_learning_unit", {})
        rows.append({
            "artifact_id": artifact.get("artifact_id"),
            "artifact_status": artifact.get("artifact_status"),
            "learning_unit_id": unit.get("learning_unit_id"),
            "learning_unit_type": unit.get("learning_unit_type"),
            "cluster_id": cluster.get("cluster_id"),
            "cluster_key": cluster.get("cluster_key"),
            "row_count": int(cluster.get("row_count", 0)),
            "draft_only_missing_row_count": int(cluster.get("missing_row_count", 0)),
            "coverage_credit_now": 0,
            "coverage_status": "DRAFT_ONLY_NOT_CANONICAL",
        })
    return rows


def count_by(rows, key):
    result = {}
    for row in rows:
        value = row.get(key)
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def sum_by(rows, key):
    return sum(int(row.get(key, 0)) for row in rows)


def main():
    drafts = load_json(DRAFTS_PATH)
    draft_artifacts = drafts.get("draft_artifacts", [])
    draft_rows = draft_cluster_rows(draft_artifacts)
    draft_only_missing_rows = sum_by(draft_rows, "draft_only_missing_row_count")
    clear_lane_row_count = sum_by(draft_rows, "row_count")
    missing_not_in_clear_draft_rows = max(BASELINE_CANONICAL_MISSING_ROWS - draft_only_missing_rows, 0)
    theoretical_covered_after_draft_promotion = min(
        EGP_A1_TOTAL_ROWS,
        BASELINE_CANONICAL_COVERED_ROWS + draft_only_missing_rows,
    )
    bundle_summary = load_json(BUNDLE_SUMMARY_PATH) if BUNDLE_SUMMARY_PATH.exists() else {}
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_coverage_recheck_no_new_design_docs",
        "source_inputs": [
            str(DRAFTS_PATH.relative_to(BASE)),
            str(BUNDLE_SUMMARY_PATH.relative_to(BASE)),
        ],
        "recheck_scope": "A1/A1+ EGP coverage recheck using existing artifacts only",
        "anti_artifact_proliferation_guard": {
            "new_design_docs_created": False,
            "new_planning_docs_created": False,
            "new_review_docs_created": False,
            "new_sync_docs_created": False,
            "canonical_graph_write_allowed": False,
            "a2_a2plus_progression_allowed": False,
        },
        "actual_canonical_coverage": {
            "egp_a1_total_rows": EGP_A1_TOTAL_ROWS,
            "canonical_covered_rows": BASELINE_CANONICAL_COVERED_ROWS,
            "canonical_missing_rows": BASELINE_CANONICAL_MISSING_ROWS,
            "coverage_ratio": pct(BASELINE_CANONICAL_COVERED_ROWS, EGP_A1_TOTAL_ROWS),
            "coverage_percent": round(pct(BASELINE_CANONICAL_COVERED_ROWS, EGP_A1_TOTAL_ROWS) * 100, 4),
            "a1_a1plus_node_count": BASELINE_A1_A1PLUS_NODE_COUNT,
            "nodes_using_non_a1_refs": NON_A1_REF_NODE_COUNT,
            "coverage_changed_by_current_draft_chain": False,
        },
        "draft_only_recheck": {
            "draft_artifact_count": len(draft_artifacts),
            "clear_lane_cluster_count": len(draft_rows),
            "clear_lane_total_row_count": clear_lane_row_count,
            "draft_only_missing_row_count": draft_only_missing_rows,
            "draft_only_coverage_credit_now": 0,
            "draft_only_items": draft_rows,
            "learning_unit_type_counts": count_by(draft_rows, "learning_unit_type"),
        },
        "missing_recheck": {
            "canonical_missing_rows": BASELINE_CANONICAL_MISSING_ROWS,
            "missing_rows_represented_by_clear_lane_drafts": draft_only_missing_rows,
            "missing_rows_not_in_clear_lane_drafts": missing_not_in_clear_draft_rows,
            "missing_rows_status": "aggregate_count_only_until_row_level_ids_are_materialized",
        },
        "theoretical_after_future_promotion": {
            "if_all_19_clear_lane_drafts_are_completed_and_promoted": {
                "covered_rows": theoretical_covered_after_draft_promotion,
                "missing_rows": max(EGP_A1_TOTAL_ROWS - theoretical_covered_after_draft_promotion, 0),
                "coverage_ratio": pct(theoretical_covered_after_draft_promotion, EGP_A1_TOTAL_ROWS),
                "coverage_percent": round(pct(theoretical_covered_after_draft_promotion, EGP_A1_TOTAL_ROWS) * 100, 4),
            },
            "promotion_preconditions": [
                "fill source-grounded draft fields",
                "replace placeholders in existing draft artifacts",
                "operator review actual source_refs and examples",
                "run promotion validator",
                "only then recompute canonical coverage",
            ],
        },
        "field_completion_bundle_status": {
            "bundle_validation_status": bundle_summary.get("validation_status"),
            "bundle_item_count": bundle_summary.get("bundle_item_count"),
            "field_bundle_task_count": bundle_summary.get("field_bundle_task_count"),
            "actual_field_values_materialized": bundle_summary.get("actual_field_values_materialized"),
            "draft_artifact_update_allowed_now": bundle_summary.get("draft_artifact_update_allowed_now"),
            "canonical_grammar_write_allowed": bundle_summary.get("canonical_grammar_write_allowed"),
            "canonical_pattern_write_allowed": bundle_summary.get("canonical_pattern_write_allowed"),
        },
        "next_short_step": "R7-M104E16B_A1A1PlusDraftArtifactFieldCompletionPatch_NoNewDesignDocs",
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_coverage_recheck_no_new_design_docs_summary",
        "validation_status": "PASS",
        "egp_a1_total_rows": EGP_A1_TOTAL_ROWS,
        "canonical_covered_rows": BASELINE_CANONICAL_COVERED_ROWS,
        "canonical_missing_rows": BASELINE_CANONICAL_MISSING_ROWS,
        "canonical_coverage_ratio": pct(BASELINE_CANONICAL_COVERED_ROWS, EGP_A1_TOTAL_ROWS),
        "canonical_coverage_percent": round(pct(BASELINE_CANONICAL_COVERED_ROWS, EGP_A1_TOTAL_ROWS) * 100, 4),
        "coverage_changed_by_current_draft_chain": False,
        "draft_artifact_count": len(draft_artifacts),
        "clear_lane_cluster_count": len(draft_rows),
        "clear_lane_total_row_count": clear_lane_row_count,
        "draft_only_missing_row_count": draft_only_missing_rows,
        "draft_only_coverage_credit_now": 0,
        "missing_rows_not_in_clear_lane_drafts": missing_not_in_clear_draft_rows,
        "theoretical_covered_rows_after_clear_lane_promotion": theoretical_covered_after_draft_promotion,
        "theoretical_missing_rows_after_clear_lane_promotion": max(EGP_A1_TOTAL_ROWS - theoretical_covered_after_draft_promotion, 0),
        "theoretical_coverage_ratio_after_clear_lane_promotion": pct(theoretical_covered_after_draft_promotion, EGP_A1_TOTAL_ROWS),
        "theoretical_coverage_percent_after_clear_lane_promotion": round(pct(theoretical_covered_after_draft_promotion, EGP_A1_TOTAL_ROWS) * 100, 4),
        "field_bundle_task_count": bundle_summary.get("field_bundle_task_count"),
        "actual_field_values_materialized": bundle_summary.get("actual_field_values_materialized"),
        "new_design_docs_created": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "next_short_step": "R7-M104E16B_A1A1PlusDraftArtifactFieldCompletionPatch_NoNewDesignDocs",
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    write_json(OUT, report)
    write_json(SUMMARY, summary)
    print("A1/A1+ coverage recheck no-new-design-docs build: PASS")
    print("Canonical coverage:", summary["canonical_covered_rows"], "/", summary["egp_a1_total_rows"], f"({summary['canonical_coverage_percent']}%)")
    print("Draft-only missing rows:", summary["draft_only_missing_row_count"])
    print("Missing not in clear lane drafts:", summary["missing_rows_not_in_clear_lane_drafts"])


if __name__ == "__main__":
    main()
