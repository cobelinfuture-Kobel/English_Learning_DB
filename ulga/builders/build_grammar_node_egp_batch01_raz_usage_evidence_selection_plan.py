import json
import re
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_selection_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_selection_plan_summary.json"
TASK_ID = "R7-M78A_Batch01RAZUsageEvidenceSelectionPlanArtifactBuilder"

MAX_SELECTIONS = {
    "GRAMMAR_ARTICLES_BASIC": 5,
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": 5,
    "GRAMMAR_BE_VERB_BASIC": 6,
    "GRAMMAR_CAN_STATEMENT": 7,
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": 6,
}

PRIORITY_PATTERNS = {
    "GRAMMAR_ARTICLES_BASIC": [
        r"^this is a ",
        r"^the (dogs|cats|cows|pigs) ",
        r"^the bird goes over the ",
    ],
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": [
        r" on the water\.$",
        r" in the water\.$",
    ],
    "GRAMMAR_BE_VERB_BASIC": [
        r"^this is ",
        r"^here is ",
        r"^here are ",
        r"^my hair is ",
        r"^this is my ",
    ],
    "GRAMMAR_CAN_STATEMENT": [
        r"^i can run\.$",
        r"^i can jump\.$",
        r"^i can hop\.$",
        r"^i can ride\.$",
        r"^i can climb\.$",
        r"^i can play\.$",
        r"^we can make sounds\.$",
    ],
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": [
        r"^my dog can ",
        r"^here is my ",
        r"^here are my ",
        r"^my hair is ",
    ],
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text):
    return re.sub(r"\s+", " ", str(text).strip().lower())


def pattern_rank(grammar_id, sentence):
    normalized = normalize(sentence)
    for index, pattern in enumerate(PRIORITY_PATTERNS.get(grammar_id, [])):
        if re.search(pattern, normalized):
            return index
    return len(PRIORITY_PATTERNS.get(grammar_id, [])) + 1


def source_rank(candidate):
    source_path = str(candidate.get("source_path", ""))
    sentence = str(candidate.get("sentence_text", "")).strip()
    if "enriched_sentences" in source_path:
        return 0
    if sentence.endswith((".", "!", "?")):
        return 1
    if "page_unit" in source_path:
        return 2
    return 3


def candidate_sort_key(grammar_id, candidate):
    sentence = candidate.get("sentence_text", "")
    return (
        pattern_rank(grammar_id, sentence),
        source_rank(candidate),
        len(sentence),
        normalize(sentence),
    )


def build_records(raw):
    records = []
    selected_counts = Counter()
    source_filtered_count = 0
    for record in raw.get("records", []):
        grammar_id = record.get("grammar_id")
        candidates = list(record.get("candidates", []))
        source_filtered_count += len(candidates)
        max_count = MAX_SELECTIONS.get(grammar_id, 5)
        sorted_candidates = sorted(candidates, key=lambda c: candidate_sort_key(grammar_id, c))
        selected = []
        seen_sentence = set()
        for candidate in sorted_candidates:
            sentence_key = normalize(candidate.get("sentence_text", ""))
            if sentence_key in seen_sentence:
                continue
            seen_sentence.add(sentence_key)
            selected_candidate = dict(candidate)
            selected_candidate["selection_status"] = "PROPOSED_RAZ_USAGE_EVIDENCE"
            selected_candidate["selection_role"] = record.get("evidence_role")
            selected_candidate["operator_review_required"] = True
            selected.append(selected_candidate)
            if len(selected) >= max_count:
                break
        selected_counts[grammar_id] = len(selected)
        records.append({
            "item_id": record.get("item_id"),
            "grammar_id": grammar_id,
            "evidence_role": record.get("evidence_role"),
            "source_filtered_candidate_count": len(candidates),
            "selected_candidate_count": len(selected),
            "selection_status": "PROPOSED_SELECTION_REQUIRES_OPERATOR_REVIEW",
            "selected_candidates": selected,
        })
    return records, source_filtered_count, selected_counts


def main():
    raw = load_json(INPUT_PATH)
    records, source_filtered_count, selected_counts = build_records(raw)
    selected_total = sum(selected_counts.values())
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_raz_usage_evidence_selection_plan",
        "source_artifact_id": raw.get("artifact_id"),
        "selection_model": "deterministic_representative_subset_for_operator_review",
        "records": records,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_auto_egp_row_selection": True,
            "no_authority_write": True,
            "no_egp_evidence_refs_write": True,
            "no_coverage_increase": True,
            "no_final_usage_evidence_acceptance": True,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_raz_usage_evidence_selection_plan_summary",
        "validation_status": "PASS_WITH_WARNINGS" if any(v == 0 for v in selected_counts.values()) else "PASS",
        "source_filtered_candidate_count": source_filtered_count,
        "selected_candidate_count": selected_total,
        "unselected_candidate_count": source_filtered_count - selected_total,
        "selection_count_by_grammar_id": dict(sorted(selected_counts.items())),
        "target_count": len(records),
        "targets_without_selected_candidates": sum(1 for v in selected_counts.values() if v == 0),
        "operator_review_required": True,
        "authority_write_allowed": False,
        "evidence_refs_write_allowed": False,
        "coverage_increase_allowed": False,
        "final_acceptance_allowed": False,
        "next_short_step": "R7-M79A_Batch01RAZUsageEvidenceSelectionPlanReadback",
        "stop_reason": "NONE",
    }
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print(f"Batch 01 RAZ usage evidence selection plan build: {summary['validation_status']}")
    print(f"Source filtered candidates: {source_filtered_count}")
    print(f"Selected candidates: {selected_total}")


if __name__ == "__main__":
    main()
