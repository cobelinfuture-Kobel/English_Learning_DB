import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SELECTION_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_deterministic_selection.py"
SELECTION_REPORT = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_deterministic_selection.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_selection_patch_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_selection_patch_plan_summary.json"
TASK_ID = "R7-M99C_A1A1PLUSSelectionPatchPlanBuilder"
PATCH_FILE = "ulga/grammar/grammar_nodes.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_selection_report():
    if SELECTION_REPORT.exists():
        return
    result = subprocess.run([sys.executable, str(SELECTION_BUILDER)], cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)


def plan_record(record):
    decision = record["selection_decision"]
    if decision == "SELECT_AUTHORITY_EVIDENCE":
        action = "PLAN_EGP_AUTHORITY_REFS_PATCH"
        target_field = "egp_evidence_refs"
        write_target = PATCH_FILE
    elif decision == "SELECT_FORM_ONLY_EVIDENCE":
        action = "PLAN_EGP_FORM_ONLY_REFS_PATCH"
        target_field = "egp_form_evidence_refs"
        write_target = PATCH_FILE
    else:
        action = "PLAN_DEFER_NO_CANONICAL_PATCH"
        target_field = None
        write_target = None
    return {
        "grammar_id": record["grammar_id"],
        "planned_action": action,
        "target_field": target_field,
        "selected_egp_refs": record.get("selected_egp_refs", []),
        "selected_ref_count": record.get("selected_ref_count", 0),
        "write_target_path": write_target,
        "canonical_write_allowed": False,
        "deferred": action == "PLAN_DEFER_NO_CANONICAL_PATCH",
    }


def main():
    ensure_selection_report()
    source = load_json(SELECTION_REPORT)
    records = [plan_record(record) for record in source.get("records", [])]
    counts = {}
    for record in records:
        counts[record["planned_action"]] = counts.get(record["planned_action"], 0) + 1
    report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_selection_patch_plan",
        "source_artifact_id": source.get("artifact_id"),
        "patch_plan_scope": "A1_A1PLUS_PATCH_PLAN_NO_CANONICAL_WRITE",
        "records": records,
        "scope_constraints": {
            "canonical_grammar_write_allowed": False,
            "egp_evidence_refs_write_allowed": False,
            "coverage_increase_allowed": False,
            "practicebank_generation_allowed": False,
            "learner_state_write_allowed": False,
            "runtime_change_allowed": False
        }
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_selection_patch_plan_summary",
        "validation_status": "PASS",
        "source_target_count": len(source.get("records", [])),
        "planned_patch_target_count": sum(1 for r in records if not r["deferred"]),
        "planned_defer_target_count": sum(1 for r in records if r["deferred"]),
        "planned_action_counts": dict(sorted(counts.items())),
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M99D_A1A1PLUSCanonicalPatchApplierBuilder",
        "stop_reason": "NONE"
    }
    write_json(OUT_PATH, report)
    write_json(SUMMARY_PATH, summary)
    print("A1/A1_PLUS selection patch plan build: PASS")
    print("Action counts:", summary["planned_action_counts"])


if __name__ == "__main__":
    main()
