import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_query_index.json"
OUTPUT_PATH = BASE_DIR / "ulga" / "graph" / "reading_practice_items.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_practice_items_summary.json"

ITEM_SCHEMA_VERSION = "READING_PRACTICE_ITEM_V1"
OUTPUT_SCHEMA_VERSION = "READING_PRACTICE_ITEMS_CANDIDATE_OUTPUT_V1"
SUMMARY_SCHEMA_VERSION = "READING_PRACTICE_ITEMS_CANDIDATE_SUMMARY_V1"
BUILDER_TASK = "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation"

QUESTION_TYPES = [
    "literal_who",
    "literal_what",
    "literal_where",
    "true_false",
    "sentence_ordering",
    "cloze_vocabulary",
]

SOURCE_TYPES = {
    "sentence_candidate",
    "page_unit",
    "reuse_unit_candidate",
    "normalized_reading_unit",
    "enriched_reading_unit",
}

QUESTION_SOURCE_TYPES = {
    "literal_who": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
    "literal_what": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
    "literal_where": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
    "true_false": {"sentence_candidate", "page_unit", "reuse_unit_candidate", "normalized_reading_unit", "enriched_reading_unit"},
    "sentence_ordering": {"page_unit", "reuse_unit_candidate", "normalized_reading_unit", "enriched_reading_unit"},
    "cloze_vocabulary": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
}

INSTRUCTIONS = {
    "literal_who": "Choose the correct answer.",
    "literal_what": "Choose the correct answer.",
    "literal_where": "Choose the correct answer.",
    "true_false": "Choose True or False.",
    "sentence_ordering": "Put the sentences in the correct order.",
    "cloze_vocabulary": "Choose the word that completes the sentence.",
}

SAFE = {
    "who": ["the boy", "the girl", "the teacher", "the mother", "the father", "the dog", "the cat"],
    "what": ["a book", "a ball", "a kite", "a bag", "a toy", "a pencil"],
    "where": ["in the room", "on the bed", "at school", "in the park", "under the table"],
    "word": ["book", "ball", "kite", "rice", "water", "school", "house", "room"],
}

WHO_WORDS = {"boy", "girl", "teacher", "mother", "father", "child", "cat", "dog", "bird", "fish", "rabbit"}
STOPWORDS = {"a", "an", "the", "and", "or", "but", "i", "you", "he", "she", "it", "we", "they", "is", "are", "am", "was", "were", "do", "does", "did", "to", "of", "in", "on", "at", "for", "with", "my", "your", "his", "her", "our", "their"}


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def split_sentences(text):
    text = str(text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    lines = [clean(line) for line in text.splitlines() if clean(line)]
    if len(lines) > 1:
        return lines
    parts = re.findall(r"[^.!?]+[.!?]", text)
    return [clean(part) for part in parts] if parts else [clean(text)]


def is_noisy(text):
    text = str(text or "")
    if not text:
        return True
    if "\ufffd" in text or "�" in text:
        return True
    symbols = len(re.findall(r"[^A-Za-z0-9\s.,!?'-]", text))
    return len(text) >= 20 and symbols / max(1, len(text)) > 0.25


def source_trace(item):
    return item.get("source_traceability") if isinstance(item.get("source_traceability"), dict) else {}


def source_record_id(item):
    return source_trace(item).get("source_record_id") or item.get("source_record_id") or item.get("intake_id")


def source_path(item):
    return source_trace(item).get("source_path") or item.get("source_path")


def source_ok(item):
    if not isinstance(item, dict):
        return False, "not_object"
    if item.get("source_type") not in SOURCE_TYPES:
        return False, "bad_source_type"
    if not item.get("intake_id"):
        return False, "missing_intake_id"
    if not source_record_id(item):
        return False, "missing_source_record_id"
    if not clean(item.get("clean_text")):
        return False, "missing_text"
    if not isinstance(item.get("sentence_count"), int) or item["sentence_count"] < 1:
        return False, "bad_sentence_count"
    if item.get("generated_content") is True:
        return False, "generated_source_text"
    if item.get("authority_status") != "candidate_only":
        return False, "not_candidate_only"
    if item.get("promotion_status") != "not_promoted":
        return False, "promoted_source"
    if is_noisy(item.get("clean_text")):
        return False, "noisy_text"
    return True, "eligible"


def compatible(item, question_type):
    if item.get("source_type") not in QUESTION_SOURCE_TYPES[question_type]:
        return False
    count = int(item.get("sentence_count") or 0)
    if question_type == "sentence_ordering":
        return 2 <= count <= 5
    return 1 <= count <= 5


def choice_id(index):
    return chr(ord("A") + index)


def choices(correct, pool, count=3):
    correct = clean(correct)
    seen = {correct.lower()}
    values = [correct]
    for option in pool:
        option = clean(option)
        if option and option.lower() not in seen:
            values.append(option)
            seen.add(option.lower())
        if len(values) >= count:
            break
    if len(values) < count:
        return []
    return [{"choice_id": choice_id(i), "text": value} for i, value in enumerate(values)]


def detect_subject(sentence):
    sentence = clean(sentence)
    match = re.match(r"^(The|A|An|My|His|Her|Our|Their)\s+([A-Za-z][A-Za-z'-]*)\b", sentence)
    if match and match.group(2).lower() in WHO_WORDS:
        return clean(match.group(0))
    match = re.match(r"^([A-Z][a-z]+)\s+", sentence)
    return match.group(1) if match else None


def base_verb(verb):
    return {"has": "have", "does": "do", "goes": "go", "is": "be"}.get(verb.lower(), re.sub(r"s$", "", verb.lower()))


def detect_object(sentence):
    pattern = re.compile(
        r"^(?P<subject>(?:The|A|An|My|His|Her|Our|Their)\s+[A-Za-z][A-Za-z'-]*|[A-Z][a-z]+)\s+"
        r"(?P<verb>has|have|sees|see|eats|eat|likes|like|gets|get|wants|want|holds|hold|reads|read)\s+"
        r"(?P<object>(?:a|an|the|my|his|her|our|their)?\s*[A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,3})[.!?]?$",
        re.IGNORECASE,
    )
    match = pattern.match(clean(sentence))
    if not match:
        return None
    return clean(match.group("subject")), base_verb(match.group("verb")), clean(match.group("object"))


def detect_location(sentence):
    pattern = re.compile(
        r"^(?P<subject>(?:The|A|An|My|His|Her|Our|Their)\s+[A-Za-z][A-Za-z'-]*|[A-Z][a-z]+)\s+"
        r"(?:is|are|sits|sit|stands|stand|plays|play|lives|live)\s+"
        r"(?P<location>(?:in|on|at|under|near|next to)\s+(?:the|a|an|my|his|her|our|their)?\s*[A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,4})[.!?]?$",
        re.IGNORECASE,
    )
    match = pattern.match(clean(sentence))
    if not match:
        return None
    return clean(match.group("subject")), clean(match.group("location"))


def cloze_token(sentence):
    for word in reversed(re.findall(r"[A-Za-z][A-Za-z'-]*", sentence or "")):
        lower = word.lower()
        if len(lower) >= 3 and lower not in STOPWORDS and not word[0].isupper():
            return word
    return None


def level_object(item):
    level = str(item.get("level") or "UNKNOWN").upper()
    return {
        "source_level": f"RAZ_{level}" if level != "UNKNOWN" and not level.startswith("RAZ_") else level,
        "cefr_estimate": "unknown",
        "level_confidence": "source_declared" if level != "UNKNOWN" else "unknown",
    }


def source_object(item):
    return {
        "source_system": source_trace(item).get("source_system") or item.get("source_system") or "RAZ",
        "source_intake_id": item.get("intake_id"),
        "source_record_id": source_record_id(item),
        "source_type": item.get("source_type"),
        "source_level": str(item.get("level") or "UNKNOWN").upper(),
        "book_id": item.get("book_id"),
        "page_number": item.get("page_number"),
        "source_path": source_path(item),
        "generated_content": False,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }


def evidence(text, sentences, item):
    text = clean(text)
    kept = [clean(sentence) for sentence in sentences if clean(sentence)]
    return {
        "evidence_text": text,
        "evidence_sentences": kept,
        "sentence_count": len(kept),
        "evidence_span": {"start_char": 0, "end_char": len(text)},
        "supports_answer": True,
        "evidence_source": "source_sentence" if item.get("source_type") == "sentence_candidate" else "source_page_unit",
    }


def tags(item, reading_skill):
    query_tags = item.get("query_tags") if isinstance(item.get("query_tags"), dict) else {}
    return {
        "reading_skill": [reading_skill],
        "grammar": list(query_tags.get("grammar_tags") or []),
        "vocabulary": list(query_tags.get("vocabulary_tags") or []),
        "theme": list(query_tags.get("theme_hints") or []),
        "reusability": list(query_tags.get("reusability_tags") or []),
        "source_tags": [],
    }


def validation():
    return {
        "source_traceability_required": True,
        "source_traceability_passed": False,
        "answer_must_be_supported_by_evidence": True,
        "answer_support_passed": False,
        "no_unsourced_generation": True,
        "no_unsourced_generation_passed": False,
        "candidate_only_required": True,
        "candidate_only_passed": False,
        "validator_status": "not_run",
        "validator_errors": [],
        "validator_warnings": [],
    }


def lifecycle():
    return {
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "learner_facing": False,
        "generated_item": True,
        "generated_content": False,
        "requires_review": True,
    }


def make_item(seq, source, qtype, prompt, answer, ev, reading_skill):
    return {
        "item_id": f"READING_ITEM_S17_{seq:06d}",
        "schema_version": ITEM_SCHEMA_VERSION,
        "generation_task": BUILDER_TASK,
        "status": "candidate_generated",
        "skill": "reading",
        "question_type": qtype,
        "level": level_object(source),
        "source": source_object(source),
        "evidence": ev,
        "prompt": prompt,
        "answer_model": answer,
        "tags": tags(source, reading_skill),
        "validation": validation(),
        "lifecycle": lifecycle(),
    }


def single_choice_answer(correct, correct_choice="A"):
    return {
        "answer_type": "single_choice",
        "correct_answer": correct,
        "correct_choice_id": correct_choice,
        "acceptable_answers": [correct],
        "distractor_policy": "fixed_question_type_safe_pool",
        "scoring": {"mode": "choice_id_match", "points": 1, "case_sensitive": False, "trim_whitespace": True},
    }


def gen_literal_who(source):
    sentences = split_sentences(source.get("clean_text"))
    if not sentences:
        return None
    sentence = sentences[0]
    subject = detect_subject(sentence)
    if not subject:
        return None
    opts = choices(subject, SAFE["who"])
    if not opts:
        return None
    prompt = {"stem": "Who is in the text?", "instructions": INSTRUCTIONS["literal_who"], "choices": opts, "display_text": sentence}
    return prompt, single_choice_answer(subject, opts[0]["choice_id"]), evidence(sentence, [sentence], source), "literal_comprehension"


def gen_literal_what(source):
    sentences = split_sentences(source.get("clean_text"))
    if not sentences:
        return None
    detected = detect_object(sentences[0])
    if not detected:
        return None
    subject, verb, obj = detected
    opts = choices(obj, SAFE["what"])
    if not opts:
        return None
    prompt = {"stem": f"What does {subject} {verb}?", "instructions": INSTRUCTIONS["literal_what"], "choices": opts, "display_text": sentences[0]}
    return prompt, single_choice_answer(obj, opts[0]["choice_id"]), evidence(sentences[0], [sentences[0]], source), "literal_comprehension"


def gen_literal_where(source):
    sentences = split_sentences(source.get("clean_text"))
    if not sentences:
        return None
    detected = detect_location(sentences[0])
    if not detected:
        return None
    subject, location = detected
    opts = choices(location, SAFE["where"])
    if not opts:
        return None
    prompt = {"stem": f"Where is {subject}?", "instructions": INSTRUCTIONS["literal_where"], "choices": opts, "display_text": sentences[0]}
    return prompt, single_choice_answer(location, opts[0]["choice_id"]), evidence(sentences[0], [sentences[0]], source), "literal_comprehension"


def gen_true_false(source):
    sentences = split_sentences(source.get("clean_text"))
    if not sentences or len(sentences[0]) > 160:
        return None
    choices_tf = [{"choice_id": "A", "text": "True"}, {"choice_id": "B", "text": "False"}]
    prompt = {"stem": "Read the sentence. Choose True or False.", "instructions": INSTRUCTIONS["true_false"], "choices": choices_tf, "display_text": sentences[0], "statement": sentences[0]}
    answer = {
        "answer_type": "true_false",
        "correct_answer": True,
        "correct_choice_id": "A",
        "acceptable_answers": [True, "true", "True"],
        "distractor_policy": "fixed_true_false_choices",
        "scoring": {"mode": "boolean_match", "points": 1, "case_sensitive": False, "trim_whitespace": True},
    }
    return prompt, answer, evidence(sentences[0], [sentences[0]], source), "literal_comprehension"


def gen_sentence_ordering(source):
    sentences = split_sentences(source.get("clean_text"))
    if not 2 <= len(sentences) <= 5:
        return None
    seed = f"{source_record_id(source)}::{source.get('intake_id')}::sentence_ordering"
    shuffled = list(enumerate(sentences))
    shuffled.sort(key=lambda pair: f"{seed}::{pair[1]}")
    if [index for index, _ in shuffled] == list(range(len(sentences))):
        shuffled.reverse()
    opts = [{"choice_id": choice_id(i), "text": sentence} for i, (_, sentence) in enumerate(shuffled)]
    original_to_choice = {original_index: choice_id(display_index) for display_index, (original_index, _) in enumerate(shuffled)}
    correct = [original_to_choice[index] for index in range(len(sentences))]
    prompt = {"stem": "Put the sentences in the correct order.", "instructions": INSTRUCTIONS["sentence_ordering"], "choices": opts, "display_text": "\n".join(opt["text"] for opt in opts)}
    answer = {
        "answer_type": "ordered_sequence",
        "correct_answer": correct,
        "acceptable_answers": [correct],
        "distractor_policy": "deterministic_sentence_shuffle",
        "scoring": {"mode": "sequence_exact_match", "points": 1, "case_sensitive": False, "trim_whitespace": True},
    }
    return prompt, answer, evidence("\n".join(sentences), sentences, source), "sentence_sequence"


def gen_cloze(source):
    sentences = split_sentences(source.get("clean_text"))
    if not sentences:
        return None
    sentence = sentences[0]
    token = cloze_token(sentence)
    if not token:
        return None
    display = re.sub(rf"\b{re.escape(token)}\b", "____", sentence, count=1)
    if display.count("____") != 1:
        return None
    opts = choices(token, SAFE["word"])
    if not opts:
        return None
    prompt = {"stem": "Choose the word that completes the sentence.", "instructions": INSTRUCTIONS["cloze_vocabulary"], "choices": opts, "display_text": display}
    answer = {
        "answer_type": "cloze_text",
        "correct_answer": token,
        "correct_choice_id": opts[0]["choice_id"],
        "acceptable_answers": [token],
        "distractor_policy": "fixed_question_type_safe_pool",
        "scoring": {"mode": "choice_id_match", "points": 1, "case_sensitive": False, "trim_whitespace": True},
    }
    return prompt, answer, evidence(sentence, [sentence], source), "vocabulary_in_context"


GENERATOR = {
    "literal_who": gen_literal_who,
    "literal_what": gen_literal_what,
    "literal_where": gen_literal_where,
    "true_false": gen_true_false,
    "sentence_ordering": gen_sentence_ordering,
    "cloze_vocabulary": gen_cloze,
}


def build_items(index_payload, limit_per_question_type=25):
    generated = []
    counts = Counter()
    rejected = Counter()
    seq = 1
    for source in index_payload.get("items", []) if isinstance(index_payload, dict) else []:
        ok, reason = source_ok(source)
        if not ok:
            rejected[reason] += 1
            continue
        for qtype in QUESTION_TYPES:
            if counts[qtype] >= limit_per_question_type:
                continue
            if not compatible(source, qtype):
                rejected[f"{qtype}:incompatible_source"] += 1
                continue
            result = GENERATOR[qtype](source)
            if result is None:
                rejected[f"{qtype}:feature_not_found"] += 1
                continue
            prompt, answer, ev, skill = result
            generated.append(make_item(seq, source, qtype, prompt, answer, ev, skill))
            counts[qtype] += 1
            seq += 1
        if all(counts[qtype] >= limit_per_question_type for qtype in QUESTION_TYPES):
            break
    warnings = [f"no_items_generated_for_question_type:{qtype}" for qtype in QUESTION_TYPES if counts[qtype] == 0]
    if not generated:
        warnings.append("no_candidate_items_generated")
    return generated, warnings, rejected


def summarize(items, warnings, rejected, limit_per_question_type):
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": "PASS_WITH_WARNINGS" if warnings else "PASS",
        "builder_task": BUILDER_TASK,
        "total_items": len(items),
        "limit_per_question_type": limit_per_question_type,
        "by_question_type": dict(sorted(Counter(item["question_type"] for item in items).items())),
        "by_source_type": dict(sorted(Counter(item["source"]["source_type"] for item in items).items())),
        "by_source_level": dict(sorted(Counter(item["source"].get("source_level") for item in items).items())),
        "candidate_only_count": sum(1 for item in items if item["lifecycle"]["authority_status"] == "candidate_only"),
        "promoted_count": sum(1 for item in items if item["lifecycle"]["promotion_status"] == "promoted"),
        "learner_facing_count": sum(1 for item in items if item["lifecycle"].get("learner_facing") is True),
        "validator_status_counts": dict(sorted(Counter(item["validation"]["validator_status"] for item in items).items())),
        "warnings": sorted(dict.fromkeys(warnings)),
        "rejection_counts": dict(sorted(rejected.items())),
    }


def build_candidate_items(index_payload=None, limit_per_question_type=25, write_outputs=True, output_path=OUTPUT_PATH, summary_path=SUMMARY_PATH):
    if index_payload is None:
        index_payload = read_json(INPUT_PATH) if INPUT_PATH.exists() else {"items": []}
    items, warnings, rejected = build_items(index_payload, limit_per_question_type=limit_per_question_type)
    summary = summarize(items, warnings, rejected, limit_per_question_type)
    payload = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "item_schema_version": ITEM_SCHEMA_VERSION,
        "builder_task": BUILDER_TASK,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_policy": {
            "input_index_schema_version": index_payload.get("schema_version") if isinstance(index_payload, dict) else None,
            "offline_static_only": True,
            "generated_source_content_allowed": False,
            "authority_promotion": False,
            "candidate_only_preserved": True,
            "learner_facing": False,
        },
        "generation_policy": {
            "approved_question_types": QUESTION_TYPES,
            "validator_status_emitted": "not_run",
            "max_items_per_question_type": limit_per_question_type,
        },
        "items": items,
        "summary": summary,
    }
    if write_outputs:
        write_json(output_path, payload)
        write_json(summary_path, summary)
    return payload


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(INPUT_PATH))
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument("--summary", default=str(SUMMARY_PATH))
    parser.add_argument("--limit-per-question-type", type=int, default=25)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input)
    index_payload = read_json(input_path) if input_path.exists() else {"items": []}
    payload = build_candidate_items(
        index_payload=index_payload,
        limit_per_question_type=max(0, args.limit_per_question_type),
        write_outputs=not args.no_write,
        output_path=Path(args.output),
        summary_path=Path(args.summary),
    )
    print(f"Status: {payload['summary']['status']}")
    print(f"Generated items: {payload['summary']['total_items']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
