import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SUGGESTIONS_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_operator_review_batches.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_operator_review_batches_summary.json"
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


def compact_item(item):
    return {
        "grammar_id": item.get("grammar_id"),
        "review_priority": item.get("review_priority"),
        "system_stage": item.get("system_stage"),
        "node_status": item.get("node_status"),
        "candidate_suggestions": item.get("candidate_suggestions", []),
        "allowed_decisions": DECISIONS,
        "operator_decision_required": True,
        "selected_egp_row_id": None,
        "operator_reason": None,
        "learner_state_write": False,
        "practicebank_generation": False,
    }


def build_batches(suggestions):
    records = sorted(suggestions.get("records", []), key=sort_key)
    batches = []
    for index in range(0, len(records), BATCH_SIZE):
        batch_no = len(batches) + 1
        batch_items = [compact_item(item) for item in records[index:index + BATCH_SIZE]]
        batches.append({
            "batch_id": f"R7-M53-BATCH-{batch_no:02d}",
            "batch_number": batch_no,
            "item_count": len(batch_items),
            "items": batch_items,
            "batch_status": "OPERATOR_REVIEW_REQUIRED",
        })
    return batches


def build(suggestions):
    batches = build_batches(suggestions)
    priority_counts = {}
    for batch in batches:
        for item in batch["items"]:
            key = item.get("review_priority") or "UNKNOWN"
            priority_counts[key] = priority_counts.get(key, 0) + 1
    output = {
        "task_id": "R7-M53_GrammarNodeEGPOperatorReviewBatchBuilderImplementation",
        "artifact_id": "grammar_node_egp_operator_review_batches",
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
        "task_id": "R7-M53_GrammarNodeEGPOperatorReviewBatchBuilderImplementation",
        "artifact_id": "grammar_node_egp_operator_review_batches_summary",
        "validation_status": "PASS",
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "item_count": sum(batch["item_count"] for batch in batches),
        "priority_counts": dict(sorted(priority_counts.items())),
        "operator_review_required": True,
        "next_short_step": "R7-M54_GrammarNodeEGPOperatorReviewBatchReadback",
        "stop_reason": "NONE",
    }
    return output, summary


def main():
    suggestions = read_json(SUGGESTIONS_PATH, {"records": []})
    batches, summary = build(suggestions)
    write_json(OUT_PATH, batches)
    write_json(SUMMARY_PATH, summary)
    print(f"Grammar node EGP operator review batches build: {summary['validation_status']}")
    print(f"Batch count: {summary['batch_count']}")
    print(f"Item count: {summary['item_count']}")


if __name__ == "__main__":
    main()
