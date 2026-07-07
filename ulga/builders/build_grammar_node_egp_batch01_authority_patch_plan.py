import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_operator_decisions.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_authority_patch_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_authority_patch_plan_summary.json"
TASK_ID = "R7-M87A_Batch01AuthorityPatchPlanArtifactBuilder"
WRITE_TARGET_PATH = "ulga/grammar/grammar_nodes.json"

ACTION_BY_EGP_DECISION = {
    "ACCEPT_EGP_ROW_AS_AUTHORITY_EVIDENCE": "PLAN_AUTHORITY_EGP_EVIDENCE_PATCH",
    "ACCEPT_EGP_ROW_AS_FORM_EVIDENCE_ONLY": "PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH",
    "KEEP_EGP_UNRESOLVED_REQUEST_REFINED_CANDIDATES": "PLAN_REFINED_EGP_CANDIDATE_REQUEST",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_records(source):
    records = []
    for item in source["records"]:
        egp_decision = item["egp_decision"]
        planned_action = ACTION_BY_EGP_DECISION[egp_decision]
        records.append({
            "item_id": item["item_id"],
            "grammar_id": item["grammar_id"],
            "planned_action": planned_action,
            "source_egp_decision": egp_decision,
            "selected_egp_row_id": item.get("egp_row_id"),
            "selected_egp_evidence_role": item.get("egp_evidence_role"),
            "raz_usage_status": item["raz_decision"],
            "approved_raz_usage_example_count": item["approved_raz_usage_example_count"],
            "write_target_path": WRITE_TARGET_PATH if planned_action != "PLAN_REFINED_EGP_CANDIDATE_REQUEST" else None,
            "write_allowed": False,
            "operator_review_required": True,
        })
    return records


def main():
    source = load_json(INPUT_PATH)
    records = build_records(source)
    action_counts = {}
    for record in records:
        action_counts[record["planned_action"]] = action_counts.get(record["planned_action"], 0) + 1
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_authority_patch_plan",
        "source_artifact_id": source.get("artifact_id"),
        "plan_scope": "PATCH_PLAN_ONLY_NO_AUTHORITY_WRITE",
        "records": records,
        "scope_constraints": {
            "no_canonical_grammar_write": True,
            "no_egp_evidence_refs_write": True,
            "no_raz_usage_attachment_write": True,
            "no_coverage_increase": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_runtime_change": True,
            "operator_review_required": True,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_authority_patch_plan_summary",
        "validation_status": "PASS",
        "target_count": len(records),
        "action_counts": dict(sorted(action_counts.items())),
        "planned_authority_patch_count": action_counts.get("PLAN_AUTHORITY_EGP_EVIDENCE_PATCH", 0),
        "planned_form_only_patch_count": action_counts.get("PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH", 0),
        "planned_refined_candidate_request_count": action_counts.get("PLAN_REFINED_EGP_CANDIDATE_REQUEST", 0),
        "write_allowed": False,
        "canonical_grammar_write_allowed": False,
        "egp_evidence_refs_write_allowed": False,
        "raz_usage_attachment_write_allowed": False,
        "coverage_increase_allowed": False,
        "operator_review_required": True,
        "next_short_step": "R7-M88A_Batch01AuthorityPatchPlanReadback",
        "stop_reason": "NONE",
    }
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print(f"Batch 01 authority patch plan build: {summary['validation_status']}")
    print(f"Targets: {summary['target_count']}")
    print(f"Actions: {summary['action_counts']}")


if __name__ == "__main__":
    main()
