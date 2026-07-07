import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BULK_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_bulk_authority_mapping.py"
BULK_REPORT = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_bulk_authority_mapping.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_refined_candidate_search.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_refined_candidate_search_summary.json"
TASK_ID = "R7-M96A_A1A1PLUSBulkRefinedEGPCandidateSearch"

QUERY_SEEDS = {
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": ["prepositions place", "in on under next to", "location"],
    "GRAMMAR_BE_VERB_BASIC": ["be verb", "am is are", "basic be forms"],
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": ["this that these those", "demonstratives", "determiners"],
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": ["object pronouns", "me him her us them", "personal pronouns"],
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS": ["present simple", "affirmative declarative", "verb phrases"],
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES": ["present simple negative", "do not does not", "negative declarative"],
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS": ["present simple questions", "do does", "yes no questions"],
    "GRAMMAR_REGULAR_PLURAL_NOUNS": ["plural nouns", "regular plural", "noun phrase"],
    "GRAMMAR_SUBJECT_PRONOUNS": ["subject pronouns", "I you he she", "personal pronouns"],
    "GRAMMAR_THERE_IS": ["there is there are", "existential there", "clauses"],
    "GRAMMAR_THIS_IS": ["this is these are", "identification", "demonstratives"],
    "GRAMMAR_WH_QUESTIONS_BE_DO_BASIC": ["wh questions", "be do questions", "what where when who"],
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_bulk_report():
    if BULK_REPORT.exists():
        return
    result = subprocess.run([sys.executable, str(BULK_BUILDER)], cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)


def main():
    ensure_bulk_report()
    bulk = load_json(BULK_REPORT)
    targets = [r for r in bulk["records"] if r["classification"] == "NEEDS_REFINED_CANDIDATE"]
    records = []
    for item in targets:
        grammar_id = item["grammar_id"]
        seeds = QUERY_SEEDS.get(grammar_id, item.get("refinement_search_hints", []))
        records.append({
            "grammar_id": grammar_id,
            "introduced_stage": item.get("introduced_stage"),
            "category": item.get("category"),
            "search_status": "REFINED_SEARCH_QUERY_READY",
            "query_seeds": seeds,
            "candidate_row_ids": [],
            "canonical_write_allowed": False,
            "operator_review_required": True,
        })
    records.sort(key=lambda r: (r.get("introduced_stage") or "", r["grammar_id"]))
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_refined_candidate_search",
        "source_artifact_id": bulk.get("artifact_id"),
        "search_scope": "BULK_REFINED_QUERY_PREPARATION_ONLY",
        "records": records,
        "scope_constraints": {
            "canonical_grammar_write_allowed": False,
            "egp_evidence_refs_write_allowed": False,
            "coverage_increase_allowed": False,
            "practicebank_generation_allowed": False,
            "learner_state_write_allowed": False,
            "runtime_change_allowed": False,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_refined_candidate_search_summary",
        "validation_status": "PASS",
        "source_target_count": len(bulk["records"]),
        "refined_search_target_count": len(records),
        "query_ready_count": len(records),
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M97A_A1A1PLUSBulkEGPRowCandidateResolver",
        "stop_reason": "NONE",
    }
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print("A1/A1_PLUS refined candidate search build: PASS")
    print("Refined search targets:", len(records))


if __name__ == "__main__":
    main()
