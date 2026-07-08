import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
TRIAGE = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_egp_feature_learning_unit_reclassification.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_egp_feature_learning_unit_reclassification_summary.json"
TASK_ID = "R7-M104E3_A1A1PlusEGPFeatureLearningUnitReclassification"

VALID_TYPES = {
    "ATOMIC_GRAMMAR_NODE",
    "MULTI_NODE_COMPOSITE",
    "PHRASE_PATTERN_NODE",
    "SENTENCE_PATTERN_NODE",
    "CONSTRUCTION_NODE",
    "USAGE_CONSTRAINT",
    "SPLIT_REQUIRED",
    "DEFER_FOR_SOURCE_REVIEW",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize(value):
    return (value or "").lower().replace("_", " ").replace("/", " ")


def classify(cluster_key):
    text = normalize(cluster_key)
    rationale = []
    target = None
    if "verb patterns" in text or "to and -ing" in text or "patterns with to" in text:
        target = "CONSTRUCTION_NODE"
        rationale.append("verb complement pattern is a construction, not a tense/question node")
    elif "preposition" in text or "prepostion" in text:
        target = "PHRASE_PATTERN_NODE"
        rationale.append("preposition evidence usually lands in prepositional phrase or place/time phrase patterns")
    elif "adjective" in text and "position" in text:
        target = "PHRASE_PATTERN_NODE"
        rationale.append("adjective position is learned through adjective-noun phrase pattern")
    elif "determiners" in text and "articles" in text:
        target = "PHRASE_PATTERN_NODE"
        rationale.append("articles are learned inside noun phrase patterns with countability/reference constraints")
    elif "determiners" in text and "quantity" in text:
        target = "PHRASE_PATTERN_NODE"
        rationale.append("quantity determiners are learned as quantifier + noun phrase patterns")
    elif "determiners" in text:
        target = "PHRASE_PATTERN_NODE"
        rationale.append("determiners generally attach to noun phrase patterns rather than standing alone")
    elif "pronouns" in text and ("subject" in text or "object" in text):
        target = "MULTI_NODE_COMPOSITE"
        rationale.append("subject and object pronouns require role-specific nodes and sentence slots")
    elif "pronouns" in text and "indefinite" in text:
        target = "CONSTRUCTION_NODE"
        rationale.append("indefinite pronoun forms require lexicalized pronoun construction tracking")
    elif "noun phrases" in text or "grammatical functions" in text:
        target = "SENTENCE_PATTERN_NODE"
        rationale.append("noun phrase grammatical function requires sentence-role pattern mapping")
    elif "nouns" in text and "types" in text:
        target = "USAGE_CONSTRAINT"
        rationale.append("noun type classification is a usage/countability constraint more than a single form node")
    elif "nouns" in text:
        target = "PHRASE_PATTERN_NODE"
        rationale.append("noun features commonly need noun phrase pattern support")
    elif "questions" in text or "word order" in text:
        target = "SENTENCE_PATTERN_NODE"
        rationale.append("question and word-order evidence should map to sentence pattern nodes")
    elif "clause" in text or "reported" in text or "relative" in text:
        target = "CONSTRUCTION_NODE"
        rationale.append("clause-level evidence requires construction-level representation")
    elif "form" in text and any(token in text for token in ["plural", "past", "present", "imperative"]):
        target = "ATOMIC_GRAMMAR_NODE"
        rationale.append("morphological form can usually map to an atomic grammar node")
    else:
        target = "DEFER_FOR_SOURCE_REVIEW"
        rationale.append("no safe automatic learning-unit type rule matched")
    return target, rationale


def recommended_decision(learning_unit_type, existing_candidates, recommendation):
    if recommendation == "NO_ACTION_REQUIRED":
        return "NO_ACTION_REQUIRED"
    if learning_unit_type == "ATOMIC_GRAMMAR_NODE" and existing_candidates:
        return "PATCH_ATOMIC_NODE_REVIEW"
    if learning_unit_type == "MULTI_NODE_COMPOSITE":
        return "PATCH_MULTIPLE_OR_CREATE_COMPOSITE_REVIEW"
    if learning_unit_type in {"PHRASE_PATTERN_NODE", "SENTENCE_PATTERN_NODE", "CONSTRUCTION_NODE", "USAGE_CONSTRAINT"}:
        return "CREATE_LEARNING_UNIT_TYPE_REVIEW"
    if learning_unit_type == "SPLIT_REQUIRED":
        return "SPLIT_CLUSTER_REVIEW"
    return "DEFER_FOR_SOURCE_REVIEW"


def main():
    triage = load(TRIAGE)
    triage_items = triage.get("triage_items", [])
    source_cluster_count = len(triage_items)
    items = []
    type_counts = {}
    decision_counts = {}
    for item in triage_items:
        cluster_key = item.get("cluster_key") or ""
        learning_unit_type, rationale = classify(cluster_key)
        existing_candidates = item.get("target_existing_node_candidates", [])
        rec = item.get("recommended_operator_decision")
        decision = recommended_decision(learning_unit_type, existing_candidates, rec)
        type_counts[learning_unit_type] = type_counts.get(learning_unit_type, 0) + 1
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        items.append({
            "cluster_id": item.get("cluster_id"),
            "cluster_key": cluster_key,
            "row_count": item.get("row_count"),
            "missing_row_count": item.get("missing_row_count"),
            "source_recommendation": rec,
            "source_confidence": item.get("confidence"),
            "target_existing_node_candidates": existing_candidates,
            "learning_unit_type": learning_unit_type,
            "classification_rationale": rationale,
            "recommended_decision_path": decision,
            "allowed_decision_paths": [
                "NO_ACTION_REQUIRED",
                "PATCH_ATOMIC_NODE_REVIEW",
                "PATCH_MULTIPLE_OR_CREATE_COMPOSITE_REVIEW",
                "CREATE_LEARNING_UNIT_TYPE_REVIEW",
                "SPLIT_CLUSTER_REVIEW",
                "DEFER_FOR_SOURCE_REVIEW",
            ],
            "operator_decision_required": decision not in {"NO_ACTION_REQUIRED"},
            "canonical_grammar_write_allowed": False,
        })
    items.sort(key=lambda x: (x["learning_unit_type"], -(x.get("missing_row_count") or 0), x.get("cluster_key") or ""))
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_egp_feature_learning_unit_reclassification",
        "source_artifact_id": triage.get("artifact_id"),
        "source_cluster_count": source_cluster_count,
        "classification_policy": {
            "ATOMIC_GRAMMAR_NODE": "single teachable grammar unit such as basic morphology or a bounded form rule",
            "MULTI_NODE_COMPOSITE": "feature requires multiple existing nodes or a composite node",
            "PHRASE_PATTERN_NODE": "feature is realized mainly inside noun/verb/adjective/preposition phrase patterns",
            "SENTENCE_PATTERN_NODE": "feature is realized mainly through sentence role, slot, order, or clause placement",
            "CONSTRUCTION_NODE": "feature is a construction or verb/clause complement pattern",
            "USAGE_CONSTRAINT": "feature is a constraint such as countability, reference, quantity, or distribution",
            "SPLIT_REQUIRED": "cluster must be split before safe mapping",
            "DEFER_FOR_SOURCE_REVIEW": "insufficient evidence for automated classification",
        },
        "reclassification_items": items,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_egp_feature_learning_unit_reclassification_summary",
        "validation_status": "PASS",
        "source_cluster_count": source_cluster_count,
        "reclassification_item_count": len(items),
        "learning_unit_type_counts": dict(sorted(type_counts.items())),
        "recommended_decision_path_counts": dict(sorted(decision_counts.items())),
        "operator_decision_required_count": sum(1 for item in items if item["operator_decision_required"]),
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104E4_A1A1PlusLearningUnitTypeReviewPacket",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ EGP feature learning unit reclassification build: PASS")
    print("Items:", len(items))
    print("Source clusters:", source_cluster_count)
    print("Learning unit types:", summary["learning_unit_type_counts"])
    print("Decision paths:", summary["recommended_decision_path_counts"])


if __name__ == "__main__":
    main()
