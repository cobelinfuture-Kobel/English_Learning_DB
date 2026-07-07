import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REFINED_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_candidate_suggestions.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_operator_review_batches.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_operator_review_batches_summary.json"
BATCH_SIZE = 5
PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
DECISIONS = [
    "ACCEPT_EGP_ROW",
    "REJECT_ALL_CANDIDATES",
    "MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED",
    "DEFER",
    "REQUEST_REFINED_CANDIDATES",
]


def read_json(path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sort_key(item):
    return (
        PRIORITY_ORDER.get(item.get("review_priority", "LOW"), 9),
        str(item.get("system_stage") or ""),
        str(item.get("grammar_id") or ""),
    )


def item_for_review(record):
    return {
        "grammar_id": record.get("grammar_id"),
        "review_priority": record.get("review_priority"),
        "system_stage": record.get("system_stage"),
        "node_status": record.get("node_status"),
        "refined_candidate_suggestions": record.get("refined_candidate_suggestions", []),
        "allowed_decisions": DECISIONS,
        "operator_decision_required": True,
        "selected_egp_row_id": None,
        "operator_reason": None,
        "learner_state_write": False,
        "practicebank_generation": False,
    }


def build_batches(refined):
    records = sorted(refined.get("records", []), key=sort_key)
    batches = []
    for offset in range(0, len(records), BATCH_SIZE):
        number = len(batches) + 1
        items = [item_for_review(item) for item in records[offset:offset + BATCH_SIZE]]
        batches.append({
            "batch_id": f"R7-M58R-BATCH-{number:02d}",
            "batch_number": number,
            "item_count": len(items),
            "items": items,
            "batch_status": "OPERATOR_REVIEW_REQUIRED",
        })
    return batches


def build(refined):
    batches = build_batches(refined)
    priority_counts = {}
    total_candidates = 0
    no_candidate_items = 0
    for batch in batches:
        for item in batch["items"]:
            priority = item.get("review_priority") or "UNKNOWN"
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            count = len(item.get("refined_candidate_suggestions", []))
            total_candidates += count
            if count == 0:
                no_candidate_items += 1
    output = {
        "task_id": "R7-M58R_RefinedOperatorReviewBatchRefresh",
        "artifact_id": "grammar_node_egp_refined_operator_review_batches",
        "source_path": "ulga/reports/grammar_node_egp_refined_candidate_suggestions.json",
        "batch_size": BATCH_SIZE,
        "allowed_decisions": DECISIONS,
        "batches": batches,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_auto_egp_row_selection": True,
            "no_authority_write": True,
        },
    }
    summary = {
        "task_id": "R7-M58R_RefinedOperatorReviewBatchRefresh",
        "artifact_id": "grammar_node_egp_refined_operator_review_batches_summary",
        "validation_status": "PASS_WITH_WARNINGS" if no_candidate_items else "PASS",
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "item_count": sum(batch["item_count"] for batch in batches),
        "total_refined_candidate_count": total_candidates,
        "items_without_refined_candidates": no_candidate_items,
        "priority_counts": dict(sorted(priority_counts.items())),
        "operator_review_required": True,
        "next_short_step": "R7-M59R_RefinedOperatorReviewBatchCIReadbackAndStop",
        "stop_reason": "NONE",
    }
    return output, summary


def main():
    refined = read_json(REFINED_PATH, {"records": []})
    batches, summary = build(refined)
    write_json(OUT_PATH, batches)
    write_json(SUMMARY_PATH, summary)
    print(f"Refined operator review batches build: {summary['validation_status']}")
    print(f"Batch count: {summary['batch_count']}")
    print(f"Item count: {summary['item_count']}")
    print(f"Total refined candidates: {summary['total_refined_candidate_count']}")


if __name__ == "__main__":
    main()
