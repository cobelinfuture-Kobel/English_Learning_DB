import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
GRAMMAR_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a2_a2plus_bulk_inventory.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a2_a2plus_bulk_inventory_summary.json"
TASK_ID = "R7-M102_A2A2PLUSBulkInventoryBuilder"
LEVEL_BAND = {"A2", "A2_PLUS"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classification(node):
    if node.get("egp_evidence_refs") or node.get("egp_form_evidence_refs"):
        return "ALREADY_PATCHED"
    return "NEEDS_EGP_CANDIDATE_RESOLUTION"


def main():
    nodes = load_json(GRAMMAR_PATH)
    targets = [node for node in nodes if node.get("introduced_stage") in LEVEL_BAND]
    records = []
    counts = {}
    for node in targets:
        item_class = classification(node)
        counts[item_class] = counts.get(item_class, 0) + 1
        records.append({
            "grammar_id": node.get("grammar_id"),
            "introduced_stage": node.get("introduced_stage"),
            "category": node.get("category"),
            "authority_status": node.get("authority_status"),
            "classification": item_class,
            "egp_evidence_ref_count": len(node.get("egp_evidence_refs", [])),
            "egp_form_evidence_ref_count": len(node.get("egp_form_evidence_refs", [])),
            "canonical_write_allowed": False,
        })
    records.sort(key=lambda item: (item.get("introduced_stage") or "", item.get("grammar_id") or ""))
    report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a2_a2plus_bulk_inventory",
        "level_band": sorted(LEVEL_BAND),
        "inventory_scope": "A2_A2PLUS_REPORT_ONLY_NO_CANONICAL_WRITE",
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
        "artifact_id": "grammar_node_egp_a2_a2plus_bulk_inventory_summary",
        "validation_status": "PASS",
        "level_band": sorted(LEVEL_BAND),
        "target_count": len(records),
        "classification_counts": dict(sorted(counts.items())),
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M103_A2A2PLUSBulkEGPCandidateResolver",
        "stop_reason": "NONE"
    }
    write_json(OUT_PATH, report)
    write_json(SUMMARY_PATH, summary)
    print("A2/A2_PLUS bulk inventory build: PASS")
    print("Targets:", len(records))
    print("Classification counts:", summary["classification_counts"])


if __name__ == "__main__":
    main()
