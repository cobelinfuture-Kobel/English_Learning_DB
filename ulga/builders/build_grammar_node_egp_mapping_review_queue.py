import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
ALIGNMENT_TABLE_PATH = BASE_DIR / "ulga" / "graph" / "cefr_egp_alignment_table.json"
REVIEW_QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue_summary.json"

REVIEWABLE_NODE_STATUSES = {
    "UNMAPPED",
    "EGP_PARTIAL_MATCH",
    "UNRESOLVED_EGP_REFS",
    "CONFLICT_REVIEW_REQUIRED",
    "NOT_IN_EGP_BUT_SYSTEM_REQUIRED",
}
HIGH_PRIORITY_STAGES = {"A1", "A1+", "A2", "A2+"}


def read_json(path, default=None):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def normalize_stage(value):
    text = str(value or "").strip()
    return {"A1_PLUS": "A1+", "A2_PLUS": "A2+", "B1_PLUS": "B1+"}.get(text, text)


def index_nodes(nodes):
    result = {}
    for node in nodes:
        if isinstance(node, dict) and node.get("grammar_id"):
            result[node["grammar_id"]] = node
    return result


def priority_for(node, alignment_record):
    stage = normalize_stage(alignment_record.get("system_stage") or node.get("introduced_stage"))
    authority_status = node.get("authority_status", "")
    node_status = alignment_record.get("node_status", "")
    if node_status in {"UNRESOLVED_EGP_REFS", "EGP_PARTIAL_MATCH", "CONFLICT_REVIEW_REQUIRED"}:
        return "HIGH"
    if stage in HIGH_PRIORITY_STAGES:
        return "HIGH"
    if authority_status == "accepted":
        return "HIGH"
    if stage in {"B1", "B1+", "B2"}:
        return "MEDIUM"
    return "LOW"


def review_reason_for(node, alignment_record):
    node_status = alignment_record.get("node_status", "")
    if node_status == "UNMAPPED":
        return "grammar node has no resolving egp_refs or egp_evidence_refs"
    if node_status == "EGP_PARTIAL_MATCH":
        return "some evidence references resolve and some do not"
    if node_status == "UNRESOLVED_EGP_REFS":
        return "evidence references exist but do not resolve to normalized EGP rows"
    if node_status == "NOT_IN_EGP_BUT_SYSTEM_REQUIRED":
        return "node is marked as system-required outside EGP and requires reason review"
    return "mapping conflict or review-required status"


def allowed_next_action_for(alignment_record):
    node_status = alignment_record.get("node_status", "")
    if node_status == "NOT_IN_EGP_BUT_SYSTEM_REQUIRED":
        return "confirm_system_required_reason_or_defer"
    if node_status in {"EGP_PARTIAL_MATCH", "UNRESOLVED_EGP_REFS", "CONFLICT_REVIEW_REQUIRED"}:
        return "operator_resolve_existing_ref_conflict"
    return "operator_select_egp_ref_or_mark_not_in_egp"


def build_review_queue(nodes, alignment_table):
    node_index = index_nodes(nodes)
    queue = []
    alignment_records = alignment_table.get("records", [])

    for record in alignment_records:
        grammar_id = record.get("grammar_id")
        node_status = record.get("node_status")
        if node_status not in REVIEWABLE_NODE_STATUSES:
            continue
        node = node_index.get(grammar_id, {})
        queue.append({
            "grammar_id": grammar_id,
            "label": record.get("label") or node.get("label", ""),
            "category": node.get("category", ""),
            "system_stage": normalize_stage(record.get("system_stage") or node.get("introduced_stage")),
            "authority_status": node.get("authority_status", "review_required"),
            "node_status": node_status,
            "alignment_status": record.get("alignment_status"),
            "review_priority": priority_for(node, record),
            "review_reason": review_reason_for(node, record),
            "allowed_next_action": allowed_next_action_for(record),
            "candidate_generation_allowed": True,
            "candidate_promotion_allowed": False,
            "learner_state_write": False,
            "practicebank_generation": False,
            "missing_egp_refs": record.get("missing_egp_refs", []),
            "source_ref_fields": record.get("source_ref_fields", []),
        })

    queue.sort(key=lambda item: (
        {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(item["review_priority"], 3),
        item["system_stage"],
        item["grammar_id"] or "",
    ))

    priority_counts = {}
    status_counts = {}
    stage_counts = {}
    for item in queue:
        priority_counts[item["review_priority"]] = priority_counts.get(item["review_priority"], 0) + 1
        status_counts[item["node_status"]] = status_counts.get(item["node_status"], 0) + 1
        stage_counts[item["system_stage"]] = stage_counts.get(item["system_stage"], 0) + 1

    review_queue = {
        "task_id": "R7-M48_GrammarNodeEGPMappingReviewQueueBuilderImplementation",
        "artifact_id": "grammar_node_egp_mapping_review_queue",
        "source_paths": {
            "grammar_nodes": "ulga/grammar/grammar_nodes.json",
            "alignment_table": "ulga/graph/cefr_egp_alignment_table.json",
        },
        "records": queue,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_ai_mapping_promotion": True,
            "no_new_evidence_selection": True,
        },
    }
    summary = {
        "task_id": "R7-M48_GrammarNodeEGPMappingReviewQueueBuilderImplementation",
        "artifact_id": "grammar_node_egp_mapping_review_queue_summary",
        "validation_status": "PASS_WITH_WARNINGS" if queue else "PASS",
        "review_queue_count": len(queue),
        "priority_counts": dict(sorted(priority_counts.items())),
        "node_status_counts": dict(sorted(status_counts.items())),
        "stage_counts": dict(sorted(stage_counts.items())),
        "candidate_generation_allowed": True,
        "candidate_promotion_allowed": False,
        "next_short_step": "R7-M49_GrammarNodeEGPCandidateSuggestionPolicyScan",
        "stop_reason": "NONE",
    }
    return review_queue, summary


def main():
    nodes = read_json(GRAMMAR_NODES_PATH, default=[])
    alignment_table = read_json(ALIGNMENT_TABLE_PATH, default={"records": []})
    review_queue, summary = build_review_queue(nodes, alignment_table)
    write_json(REVIEW_QUEUE_PATH, review_queue)
    write_json(SUMMARY_PATH, summary)
    print(f"Grammar node EGP mapping review queue build: {summary['validation_status']}")
    print(f"Review queue count: {summary['review_queue_count']}")
    print(f"Priority counts: {summary['priority_counts']}")


if __name__ == "__main__":
    main()
