import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PLAN_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_selection_patch_plan.py"
PLAN_REPORT = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_selection_patch_plan.json"
GRAMMAR_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
PATCH_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_canonical_patch_report.json"
PATCH_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_canonical_patch_summary.json"
TASK_ID = "R7-M99D_A1A1PLUSCanonicalPatchApplier"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) if compact else json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def ensure_patch_plan():
    if PLAN_REPORT.exists():
        return
    result = subprocess.run([sys.executable, str(PLAN_BUILDER)], cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)


def append_unique(existing, values):
    output = list(existing or [])
    for value in values:
        if value not in output:
            output.append(value)
    return output


def main():
    ensure_patch_plan()
    plan = load_json(PLAN_REPORT)
    nodes = load_json(GRAMMAR_PATH)
    by_id = {node.get("grammar_id"): node for node in nodes}
    changes = []
    deferred = []
    for record in plan.get("records", []):
        grammar_id = record["grammar_id"]
        action = record["planned_action"]
        if action == "PLAN_DEFER_NO_CANONICAL_PATCH":
            deferred.append(grammar_id)
            continue
        if grammar_id not in by_id:
            raise RuntimeError(f"Missing grammar node: {grammar_id}")
        target_field = record["target_field"]
        refs = record.get("selected_egp_refs", [])
        before = list(by_id[grammar_id].get(target_field, []))
        by_id[grammar_id][target_field] = append_unique(before, refs)
        notes = by_id[grammar_id].setdefault("traceability", {}).setdefault("notes", [])
        note = f"R7-M99D added A1/A1_PLUS EGP refs to {target_field}."
        if note not in notes:
            notes.append(note)
        after = by_id[grammar_id][target_field]
        changes.append({
            "grammar_id": grammar_id,
            "target_field": target_field,
            "added_ref_count": len(after) - len(before),
            "selected_ref_count": len(refs),
        })
    write_json(GRAMMAR_PATH, nodes, compact=True)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_canonical_patch_report",
        "patched_file": "ulga/grammar/grammar_nodes.json",
        "patch_status": "PASS",
        "changed_grammar_ids": sorted(change["grammar_id"] for change in changes),
        "deferred_grammar_ids": sorted(deferred),
        "changes": sorted(changes, key=lambda item: item["grammar_id"]),
        "scope_constraints": {
            "practicebank_generation": False,
            "learner_state_write": False,
            "runtime_change": False,
        }
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_canonical_patch_summary",
        "patch_status": "PASS",
        "patched_file": "ulga/grammar/grammar_nodes.json",
        "changed_grammar_id_count": len(changes),
        "changed_grammar_ids": sorted(change["grammar_id"] for change in changes),
        "deferred_grammar_id_count": len(deferred),
        "deferred_grammar_ids": sorted(deferred),
        "practicebank_generation": False,
        "learner_state_write": False,
        "runtime_change": False,
        "next_short_step": "R7-M99E_A1A1PLUSCanonicalPatchReadback",
        "stop_reason": "NONE"
    }
    write_json(PATCH_REPORT_PATH, report)
    write_json(PATCH_SUMMARY_PATH, summary)
    print("A1/A1_PLUS canonical patch apply: PASS")
    print("Changed grammar IDs:", ", ".join(summary["changed_grammar_ids"]))
    print("Deferred grammar IDs:", ", ".join(summary["deferred_grammar_ids"]))


if __name__ == "__main__":
    main()
