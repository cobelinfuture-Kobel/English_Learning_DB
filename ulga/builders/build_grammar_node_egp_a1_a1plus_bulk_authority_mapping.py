import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
GRAMMAR_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_bulk_authority_mapping.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_bulk_authority_mapping_summary.json"
TASK_ID = "R7-M95A_A1A1PLUSGrammarEGPAuthorityMappingBulkBuilder"
LEVEL_BAND = {"A1", "A1_PLUS"}

REFINEMENT_HINTS = {
    "GRAMMAR_BE_VERB_BASIC": ["be verb", "am is are", "basic forms", "clauses"],
    "GRAMMAR_SUBJECT_PRONOUNS": ["subject pronouns", "personal pronouns", "I you he she it we they"],
    "GRAMMAR_THIS_IS": ["this is", "these are", "identification", "demonstrative pronoun"],
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": ["prepositions of place", "in on under behind between next to", "location"],
    "GRAMMAR_REGULAR_PLURAL_NOUNS": ["regular plural nouns", "plural -s", "noun phrases"],
    "GRAMMAR_THERE_IS": ["there is", "there are", "existential there", "clauses"],
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": ["this that these those", "demonstratives", "determiners"],
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": ["object pronouns", "me you him her it us them", "personal pronouns"],
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS": ["present simple", "affirmative declarative", "verb phrases"],
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES": ["present simple negative", "do not does not", "negative declarative"],
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS": ["present simple yes/no questions", "do does questions", "interrogatives"],
    "GRAMMAR_WH_QUESTIONS_BE_DO_BASIC": ["WH questions", "be do", "what where when who", "interrogatives"],
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evidence_status(node):
    if node.get("egp_evidence_refs"):
        return "ALREADY_PATCHED", "egp_evidence_refs"
    if node.get("egp_form_evidence_refs"):
        return "ALREADY_PATCHED", "egp_form_evidence_refs"
    return "NEEDS_REFINED_CANDIDATE", None


def main():
    nodes = load_json(GRAMMAR_PATH)
    if not isinstance(nodes, list):
        raise RuntimeError("grammar_nodes.json must be a JSON array")
    target_nodes = [node for node in nodes if node.get("introduced_stage") in LEVEL_BAND]
    records = []
    counts = {}
    for node in target_nodes:
        status, evidence_field = evidence_status(node)
        grammar_id = node["grammar_id"]
        record = {
            "grammar_id": grammar_id,
            "label": node.get("label"),
            "category": node.get("category"),
            "introduced_stage": node.get("introduced_stage"),
            "authority_status": node.get("authority_status"),
            "classification": status,
            "evidence_field": evidence_field,
            "egp_evidence_ref_count": len(node.get("egp_evidence_refs", [])),
            "egp_form_evidence_ref_count": len(node.get("egp_form_evidence_refs", [])),
            "refinement_search_hints": REFINEMENT_HINTS.get(grammar_id, []),
            "canonical_write_allowed": False,
            "recommended_next_action": "NO_ACTION_ALREADY_PATCHED" if status == "ALREADY_PATCHED" else "BULK_REFINED_EGP_CANDIDATE_SEARCH",
        }
        records.append(record)
        counts[status] = counts.get(status, 0) + 1
    records.sort(key=lambda item: (item["introduced_stage"], item["grammar_id"]))
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_bulk_authority_mapping",
        "level_band": sorted(LEVEL_BAND),
        "mapping_scope": "REPORT_ONLY_NO_CANONICAL_WRITE",
        "records": records,
        "scope_constraints": {
            "canonical_grammar_write_allowed": False,
            "egp_evidence_refs_write_allowed": False,
            "egp_form_evidence_refs_write_allowed": False,
            "coverage_increase_allowed": False,
            "practicebank_generation_allowed": False,
            "learner_state_write_allowed": False,
            "runtime_change_allowed": False,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_bulk_authority_mapping_summary",
        "validation_status": "PASS",
        "level_band": sorted(LEVEL_BAND),
        "target_count": len(records),
        "classification_counts": dict(sorted(counts.items())),
        "already_patched_count": counts.get("ALREADY_PATCHED", 0),
        "needs_refined_candidate_count": counts.get("NEEDS_REFINED_CANDIDATE", 0),
        "canonical_grammar_write_allowed": False,
        "coverage_increase_allowed": False,
        "next_short_step": "R7-M96A_A1A1PLUSBulkRefinedEGPCandidateSearch",
        "stop_reason": "NONE",
    }
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print("A1/A1_PLUS bulk authority mapping build: PASS")
    print("Targets:", len(records))
    print("Classification counts:", summary["classification_counts"])


if __name__ == "__main__":
    main()
