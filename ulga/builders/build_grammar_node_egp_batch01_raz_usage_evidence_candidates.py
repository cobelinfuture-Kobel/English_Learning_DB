import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates_summary.json"
TASK_ID = "R7-M72A_Batch01RAZUsageEvidenceCandidateBuilderImplementation"
MAX_PER_NODE = 30
SOURCE_ROOTS = [
    "raz_output_jsons",
    "raz",
    "data/raz",
    "ulga/raz",
    "ulga/raz_output_jsons",
]
TEXT_KEYS = {"text", "sentence", "sentences", "source_text", "normalized_text", "cleaned_text", "passage", "page_text", "line"}
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")

TARGETS = [
    {"item_id": "B01-01", "grammar_id": "GRAMMAR_ARTICLES_BASIC", "evidence_role": "RAZ_USAGE_EVIDENCE"},
    {"item_id": "B01-02", "grammar_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE", "evidence_role": "RAZ_USAGE_EVIDENCE"},
    {"item_id": "B01-03", "grammar_id": "GRAMMAR_BE_VERB_BASIC", "evidence_role": "RAZ_USAGE_EVIDENCE"},
    {"item_id": "B01-04", "grammar_id": "GRAMMAR_CAN_STATEMENT", "evidence_role": "RAZ_SEMANTIC_USAGE_EVIDENCE"},
    {"item_id": "B01-05", "grammar_id": "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC", "evidence_role": "RAZ_USAGE_EVIDENCE"},
]

PATTERNS = {
    "GRAMMAR_ARTICLES_BASIC": [
        ("article_a_an_the_noun", re.compile(r"\b(a|an|the)\s+[A-Za-z][A-Za-z'\-]*\b", re.I)),
    ],
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": [
        ("place_preposition_phrase", re.compile(r"\b(in|on|under|behind|between|next to|in front of|beside|near)\s+(the|a|an|my|your|his|her|its|our|their)?\s*[A-Za-z][A-Za-z'\-]*\b", re.I)),
    ],
    "GRAMMAR_BE_VERB_BASIC": [
        ("basic_be_verb", re.compile(r"\b(I am|I'm|you are|you're|he is|he's|she is|she's|it is|it's|we are|we're|they are|they're|is|are|am)\b", re.I)),
    ],
    "GRAMMAR_CAN_STATEMENT": [
        ("can_ability_base_verb", re.compile(r"\b(I|We|You|He|She|They|It|A\s+[A-Za-z]+|The\s+[A-Za-z]+)\s+can\s+(jump|run|swim|fly|read|play|draw|sing|hop|walk|climb|write|ride|make|see|hear|help)\b", re.I)),
    ],
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": [
        ("possessive_determiner_noun", re.compile(r"\b(my|your|his|her|its|our|their)\s+[A-Za-z][A-Za-z'\-]*\b", re.I)),
    ],
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_paths():
    paths = []
    roots_found = []
    for rel in SOURCE_ROOTS:
        root = BASE_DIR / rel
        if root.exists():
            roots_found.append(rel)
            paths.extend(sorted(path for path in root.rglob("*") if path.suffix.lower() in {".json", ".jsonl", ".txt", ".md"}))
    return paths, roots_found


def iter_text_from_json(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in TEXT_KEYS and isinstance(child, str):
                yield child
            else:
                yield from iter_text_from_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_text_from_json(child)
    elif isinstance(value, str):
        if len(value.split()) >= 3:
            yield value


def iter_texts(path):
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            yield from iter_text_from_json(data)
        elif path.suffix.lower() == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    yield from iter_text_from_json(json.loads(line))
                except json.JSONDecodeError:
                    yield line
        else:
            yield path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return


def split_sentences(text):
    for part in SENTENCE_SPLIT_RE.split(str(text)):
        sentence = " ".join(part.strip().split())
        if 2 <= len(WORD_RE.findall(sentence)) <= 20:
            yield sentence


def classify(sentence):
    matches = []
    for grammar_id, patterns in PATTERNS.items():
        for pattern_id, pattern in patterns:
            match = pattern.search(sentence)
            if match:
                matches.append({
                    "grammar_id": grammar_id,
                    "pattern_id": pattern_id,
                    "matched_text": match.group(0),
                })
    return matches


def collect_candidates():
    paths, roots_found = source_paths()
    target_map = {target["grammar_id"]: {**target, "candidates": []} for target in TARGETS}
    scanned_text_units = 0
    scanned_sentences = 0
    for path in paths:
        rel_path = str(path.relative_to(BASE_DIR))
        for text in iter_texts(path):
            scanned_text_units += 1
            for sentence in split_sentences(text):
                scanned_sentences += 1
                for match in classify(sentence):
                    row = target_map.get(match["grammar_id"])
                    if not row or len(row["candidates"]) >= MAX_PER_NODE:
                        continue
                    row["candidates"].append({
                        "source_type": "RAZ",
                        "source_path": rel_path,
                        "sentence_text": sentence,
                        "matched_text": match["matched_text"],
                        "pattern_id": match["pattern_id"],
                        "evidence_role": row["evidence_role"],
                        "operator_review_required": True,
                    })
    return list(target_map.values()), paths, roots_found, scanned_text_units, scanned_sentences


def main():
    records, paths, roots_found, scanned_text_units, scanned_sentences = collect_candidates()
    total = sum(len(record["candidates"]) for record in records)
    missing = sum(1 for record in records if not record["candidates"])
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_raz_usage_evidence_candidates",
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
        "artifact_id": "grammar_node_egp_batch01_raz_usage_evidence_candidates_summary",
        "validation_status": "PASS_WITH_WARNINGS" if missing or not paths else "PASS",
        "source_roots_checked": SOURCE_ROOTS,
        "source_roots_found": roots_found,
        "source_file_count": len(paths),
        "scanned_text_unit_count": scanned_text_units,
        "scanned_sentence_count": scanned_sentences,
        "target_count": len(records),
        "total_raz_usage_candidate_count": total,
        "targets_without_candidates": missing,
        "operator_review_required": True,
        "next_short_step": "R7-M73A_Batch01RAZUsageEvidenceCandidateReadback",
        "stop_reason": "NONE",
    }
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print(f"Batch 01 RAZ usage evidence candidates build: {summary['validation_status']}")
    print(f"Source files: {summary['source_file_count']}")
    print(f"RAZ usage candidates: {summary['total_raz_usage_candidate_count']}")


if __name__ == "__main__":
    main()
