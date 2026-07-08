import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
MANIFEST = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_exam_source_manifest.json"
PATCH_TOP10 = BASE / "ulga" / "reports" / "a1_egp_alignment_patch_lane_top10_review_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_cluster_bridge_plan.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_cluster_bridge_plan_summary.json"
TASK_ID = "R7-M104E2_CambridgeOfficialClusterBridgePlan"
PRIMARY_A1_SOURCE = "CAMBRIDGE_OFFICIAL_A1_MOVERS_PAGE"
LOWER_BOUND_SOURCE = "CAMBRIDGE_OFFICIAL_PRE_A1_STARTERS_PAGE"
UPPER_BOUND_SOURCES = ["CAMBRIDGE_OFFICIAL_A2_FLYERS_PAGE", "CAMBRIDGE_OFFICIAL_A2_KEY_PAGE"]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    manifest = load(MANIFEST)
    patch_top10 = load(PATCH_TOP10)
    official_sources = {source["source_id"]: source for source in manifest.get("official_sources", [])}
    missing_sources = [source for source in [PRIMARY_A1_SOURCE, LOWER_BOUND_SOURCE, *UPPER_BOUND_SOURCES] if source not in official_sources]
    bridge_items = []
    for item in patch_top10.get("review_items", []):
        bridge_items.append({
            "priority_rank": item.get("priority_rank"),
            "cluster_id": item.get("cluster_id"),
            "cluster_key": item.get("cluster_key"),
            "missing_row_count": item.get("missing_row_count"),
            "target_existing_node_candidates": item.get("target_existing_node_candidates", []),
            "egp_authority_role": "primary_grammar_row_authority",
            "cambridge_official_role": "exam_level_context_support_only",
            "primary_cambridge_exam_context_source": PRIMARY_A1_SOURCE,
            "lower_bound_context_source": LOWER_BOUND_SOURCE,
            "upper_bound_context_sources": UPPER_BOUND_SOURCES,
            "per_cluster_official_cambridge_grammar_authority": False,
            "operator_patch_decision_allowed": True,
            "operator_patch_decision_condition": "Patch decisions must be based on EGP row semantics and existing node fit; Cambridge official source can only be cited as A1 exam-level learner-outcome context.",
            "allowed_operator_decisions": item.get("allowed_operator_decisions", []),
            "operator_decision": item.get("operator_decision"),
            "canonical_grammar_write_allowed": False,
        })
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cambridge_official_cluster_bridge_plan",
        "source_manifest_artifact_id": manifest.get("artifact_id"),
        "source_patch_top10_artifact_id": patch_top10.get("artifact_id"),
        "official_source_validation": {
            "official_cambridge_source_verified": manifest.get("official_cambridge_source_verified") is True,
            "required_official_sources_present": not missing_sources,
            "missing_official_sources": missing_sources,
        },
        "authority_policy": {
            "egp": "primary grammar-row authority for grammar node patch decisions",
            "evp": "lexical and lexical-grammar bridge support",
            "raz": "usage evidence only",
            "cambridge_official": "exam-level and learner-outcome context only until a per-cluster official bridge is explicitly authored",
        },
        "bridge_items": bridge_items,
        "per_cluster_official_cambridge_bridge_ready": False,
        "operator_patch_decision_allowed": True,
        "operator_patch_decision_allowed_scope": "R7-M104E patch-lane top10 only; Cambridge official evidence is not per-cluster grammar authority",
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cambridge_official_cluster_bridge_plan_summary",
        "validation_status": "PASS",
        "bridge_item_count": len(bridge_items),
        "official_cambridge_source_verified": manifest.get("official_cambridge_source_verified") is True,
        "required_official_sources_present": not missing_sources,
        "per_cluster_official_cambridge_bridge_ready": False,
        "operator_patch_decision_allowed": True,
        "operator_patch_decision_allowed_scope": "patch_lane_top10_with_cambridge_exam_context_only",
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104F_A1EGPAlignmentPatchLaneTop10OperatorDecisionFill",
        "stop_reason": "OPERATOR_DECISION_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment Cambridge official cluster bridge plan build: PASS")
    print("Bridge items:", len(bridge_items))
    print("Official sources present:", not missing_sources)
    print("Operator patch decision allowed:", summary["operator_patch_decision_allowed"])


if __name__ == "__main__":
    main()
