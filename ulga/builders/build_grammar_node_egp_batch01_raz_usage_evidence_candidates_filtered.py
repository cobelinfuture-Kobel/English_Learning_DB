import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered_summary.json"
TASK_ID = "R7-M75A_Batch01RAZUsageEvidenceQualityFilterImplementation"

CLOTHING_TERMS = {
    "shirt", "pants", "belt", "socks", "shoes", "glasses", "jacket", "backpack",
    "hat", "coat", "dress", "skirt", "boots", "clothes",
}
TRANSPORT_TERMS = {"plane", "train", "boat", "car", "bus", "bike", "skateboard", "horse"}
GOOD_PLACE_TERMS = {
    "water", "box", "table", "bed", "chair", "room", "house", "school", "park", "farm",
    "city", "street", "tree", "garden", "yard", "zoo", "pool", "lake", "river", "sea",
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text).strip().lower())


def is_sentence_like(text):
    stripped = str(text).strip()
    return stripped.endswith((".", "!", "?"))


def is_book_title_source(candidate):
    return "enriched_books" in str(candidate.get("source_path", ""))


def words(text):
    return re.findall(r"[a-z]+", normalize_text(text))


def reject_reason(grammar_id, candidate):
    sentence = normalize_text(candidate.get("sentence_text", ""))
    matched = normalize_text(candidate.get("matched_text", ""))
    source_path = str(candidate.get("source_path", ""))

    if not sentence or not matched:
        return "missing_sentence_or_match"

    if is_book_title_source(candidate) and not is_sentence_like(candidate.get("sentence_text", "")):
        return "title_only_candidate"

    if grammar_id == "GRAMMAR_ARTICLES_BASIC":
        if matched in {"the big", "the number", "my little", "my easter"}:
            return "partial_title_or_adjective_match"
        return None

    if grammar_id == "GRAMMAR_BASIC_PREPOSITIONS_PLACE":
        ws = words(sentence)
        if "in all" in sentence:
            return "counting_phrase_in_all"
        if sentence.startswith("i put on "):
            return "clothing_phrasal_put_on"
        if any(term in ws for term in CLOTHING_TERMS) and matched.startswith("on "):
            return "clothing_on_not_place"
        if any(term in ws for term in TRANSPORT_TERMS):
            return "transport_medium_not_place_location"
        if not any(term in ws for term in GOOD_PLACE_TERMS):
            return "no_clear_place_noun"
        return None

    if grammar_id == "GRAMMAR_BE_VERB_BASIC":
        if sentence.endswith("?"):
            return "question_not_affirmative_declarative"
        return None

    if grammar_id == "GRAMMAR_CAN_STATEMENT":
        if " can go " in f" {sentence} ":
            return "can_go_ambiguous_not_ability"
        return None

    if grammar_id == "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC":
        if sentence.endswith("?"):
            return "question_not_primary_usage_candidate"
        if matched in {"my little", "my easter"}:
            return "partial_title_or_adjective_match"
        return None

    return None


def preferred_rank(candidate):
    source_path = str(candidate.get("source_path", ""))
    sentence = str(candidate.get("sentence_text", ""))
    if "enriched_sentences" in source_path:
        return 0
    if "page_unit" in source_path and is_sentence_like(sentence):
        return 1
    if "page_unit" in source_path:
        return 2
    if "enriched_books" in source_path:
        return 3
    return 4


def filter_records(raw):
    filtered_records = []
    removed_by_reason = Counter()
    raw_count_by_grammar_id = Counter()
    filtered_count_by_grammar_id = Counter()
    seen = set()

    for record in raw.get("records", []):
        grammar_id = record.get("grammar_id")
        raw_candidates = list(record.get("candidates", []))
        raw_count_by_grammar_id[grammar_id] += len(raw_candidates)
        sorted_candidates = sorted(raw_candidates, key=preferred_rank)
        filtered = []
        for candidate in sorted_candidates:
            key = (
                grammar_id,
                normalize_text(candidate.get("sentence_text", "")),
                normalize_text(candidate.get("matched_text", "")),
            )
            if key in seen:
                removed_by_reason["duplicate_sentence_match"] += 1
                continue
            reason = reject_reason(grammar_id, candidate)
            if reason:
                removed_by_reason[reason] += 1
                continue
            seen.add(key)
            cleaned = dict(candidate)
            cleaned["quality_filter_status"] = "KEPT"
            cleaned["operator_review_required"] = True
            filtered.append(cleaned)
        filtered_count_by_grammar_id[grammar_id] = len(filtered)
        filtered_records.append({
            "item_id": record.get("item_id"),
            "grammar_id": grammar_id,
            "evidence_role": record.get("evidence_role"),
            "raw_candidate_count": len(raw_candidates),
            "filtered_candidate_count": len(filtered),
            "candidates": filtered,
        })
    return filtered_records, raw_count_by_grammar_id, filtered_count_by_grammar_id, removed_by_reason


def main():
    raw = load_json(INPUT_PATH)
    records, raw_counts, filtered_counts, removed = filter_records(raw)
    raw_total = sum(raw_counts.values())
    filtered_total = sum(filtered_counts.values())
    targets_without_candidates = sum(1 for record in records if not record["candidates"])
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered",
        "source_artifact_id": raw.get("artifact_id"),
        "records": records,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_auto_egp_row_selection": True,
            "no_authority_write": True,
            "no_egp_evidence_refs_write": True,
            "no_coverage_increase": True,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered_summary",
        "validation_status": "PASS_WITH_WARNINGS" if targets_without_candidates else "PASS",
        "raw_candidate_count": raw_total,
        "filtered_candidate_count": filtered_total,
        "removed_candidate_count": raw_total - filtered_total,
        "removed_by_reason": dict(sorted(removed.items())),
        "raw_candidate_count_by_grammar_id": dict(sorted(raw_counts.items())),
        "filtered_candidate_count_by_grammar_id": dict(sorted(filtered_counts.items())),
        "target_count": len(records),
        "targets_without_candidates": targets_without_candidates,
        "operator_review_required": True,
        "authority_write_allowed": False,
        "evidence_refs_write_allowed": False,
        "coverage_increase_allowed": False,
        "next_short_step": "R7-M76A_Batch01RAZUsageEvidenceQualityFilterReadback",
        "stop_reason": "NONE",
    }
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print(f"Batch 01 filtered RAZ usage evidence build: {summary['validation_status']}")
    print(f"Raw candidates: {raw_total}")
    print(f"Filtered candidates: {filtered_total}")
    print(f"Removed candidates: {raw_total - filtered_total}")


if __name__ == "__main__":
    main()
