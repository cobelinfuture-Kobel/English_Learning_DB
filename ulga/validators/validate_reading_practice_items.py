import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ITEMS_PATH = BASE_DIR / "ulga" / "graph" / "reading_practice_items.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_practice_items_summary.json"

OUTPUT_SCHEMA_VERSION = "READING_PRACTICE_ITEMS_CANDIDATE_OUTPUT_V1"
ITEM_SCHEMA_VERSION = "READING_PRACTICE_ITEM_V1"
SUMMARY_SCHEMA_VERSION = "READING_PRACTICE_ITEMS_CANDIDATE_SUMMARY_V1"
VALIDATOR_TASK = "RAZ-AW-S18_ReadingItemValidator_Implementation"

QUESTION_TYPES = {
    "literal_who",
    "literal_what",
    "literal_where",
    "true_false",
    "sentence_ordering",
    "cloze_vocabulary",
}

QUESTION_ANSWER_TYPES = {
    "literal_who": "single_choice",
    "literal_what": "single_choice",
    "literal_where": "single_choice",
    "true_false": "true_false",
    "sentence_ordering": "ordered_sequence",
    "cloze_vocabulary": "cloze_text",
}

QUESTION_SOURCE_TYPES = {
    "literal_who": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
    "literal_what": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
    "literal_where": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
    "true_false": {"sentence_candidate", "page_unit", "reuse_unit_candidate", "normalized_reading_unit", "enriched_reading_unit"},
    "sentence_ordering": {"page_unit", "reuse_unit_candidate", "normalized_reading_unit", "enriched_reading_unit"},
    "cloze_vocabulary": {"sentence_candidate", "page_unit", "enriched_reading_unit"},
}

QUESTION_SCORING_MODES = {
    "literal_who": "choice_id_match",
    "literal_what": "choice_id_match",
    "literal_where": "choice_id_match",
    "true_false": "boolean_match",
    "sentence_ordering": "sequence_exact_match",
    "cloze_vocabulary": "choice_id_match",
}

REQUIRED_ITEM_KEYS = {
    "item_id",
    "schema_version",
    "generation_task",
    "status",
    "skill",
    "question_type",
    "level",
    "source",
    "evidence",
    "prompt",
    "answer_model",
    "tags",
    "validation",
    "lifecycle",
}

REQUIRED_SOURCE_KEYS = {
    "source_system",
    "source_intake_id",
    "source_record_id",
    "source_type",
    "source_level",
    "book_id",
    "page_number",
    "source_path",
    "generated_content",
    "authority_status",
    "promotion_status",
}

REQUIRED_EVIDENCE_KEYS = {
    "evidence_text",
    "evidence_sentences",
    "sentence_count",
    "evidence_source",
    "supports_answer",
}

REQUIRED_PROMPT_KEYS = {"stem", "instructions"}
REQUIRED_LIFECYCLE_KEYS = {"authority_status", "promotion_status", "learner_facing", "generated_item", "generated_content", "requires_review"}


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize(value):
    return " ".join(str(value or "").split()).strip().lower()


def add(errors, code, detail):
    errors.append(f"{code}: {detail}")


def is_list_of_strings(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_top_level(payload, summary_payload, errors, warnings):
    if not isinstance(payload, dict):
        add(errors, "top_level_not_object", "payload must be an object")
        return
    for key in ["schema_version", "item_schema_version", "builder_task", "source_policy", "generation_policy", "items", "summary"]:
        if key not in payload:
            add(errors, "missing_top_level_key", key)
    if errors:
        return
    if payload["schema_version"] != OUTPUT_SCHEMA_VERSION:
        add(errors, "schema_version_mismatch", payload["schema_version"])
    if payload["item_schema_version"] != ITEM_SCHEMA_VERSION:
        add(errors, "item_schema_version_mismatch", payload["item_schema_version"])
    if not isinstance(payload["items"], list):
        add(errors, "items_not_list", "items must be a list")
    if summary_payload is not None and payload.get("summary") != summary_payload:
        add(errors, "summary_file_mismatch", "embedded summary differs from summary file")
    if isinstance(payload.get("summary"), dict):
        if payload["summary"].get("schema_version") != SUMMARY_SCHEMA_VERSION:
            add(errors, "summary_schema_mismatch", str(payload["summary"].get("schema_version")))
        if payload["summary"].get("total_items") != len(payload.get("items", [])):
            add(errors, "summary_total_items_mismatch", "summary total does not match item count")
        if len(payload.get("items", [])) == 0:
            warnings.append("no_items_to_validate")


def validate_choices(item_id, prompt, answer_model, errors):
    choices = prompt.get("choices")
    if not isinstance(choices, list) or not choices:
        add(errors, "missing_choices", item_id)
        return
    ids = set()
    for choice in choices:
        if not isinstance(choice, dict):
            add(errors, "choice_not_object", item_id)
            continue
        choice_id = choice.get("choice_id")
        text = choice.get("text")
        if not isinstance(choice_id, str) or not choice_id:
            add(errors, "choice_missing_id", item_id)
        if not isinstance(text, str) or not text.strip():
            add(errors, "choice_missing_text", item_id)
        if choice_id in ids:
            add(errors, "duplicate_choice_id", f"{item_id}:{choice_id}")
        ids.add(choice_id)
    correct_choice_id = answer_model.get("correct_choice_id")
    if correct_choice_id is not None and correct_choice_id not in ids:
        add(errors, "correct_choice_id_not_in_choices", f"{item_id}:{correct_choice_id}")


def answer_supported(item):
    question_type = item["question_type"]
    answer_model = item["answer_model"]
    evidence = item["evidence"]
    prompt = item["prompt"]
    evidence_text = normalize(evidence.get("evidence_text"))
    correct = answer_model.get("correct_answer")

    if question_type in {"literal_who", "literal_what", "literal_where", "cloze_vocabulary"}:
        return normalize(correct) in evidence_text
    if question_type == "true_false":
        return correct is True and normalize(prompt.get("statement")) in evidence_text
    if question_type == "sentence_ordering":
        sentences = [normalize(sentence) for sentence in evidence.get("evidence_sentences", [])]
        choices = {choice.get("choice_id"): normalize(choice.get("text")) for choice in prompt.get("choices", []) if isinstance(choice, dict)}
        ordered = [choices.get(choice_id) for choice_id in correct if choice_id in choices] if isinstance(correct, list) else []
        return ordered == sentences
    return False


def validate_item(item, seen_ids, errors, warnings):
    if not isinstance(item, dict):
        add(errors, "item_not_object", "item must be an object")
        return
    missing = REQUIRED_ITEM_KEYS - set(item)
    if missing:
        add(errors, "missing_item_keys", f"{item.get('item_id', 'unknown')}:{sorted(missing)}")
        return

    item_id = item["item_id"]
    if not isinstance(item_id, str) or not item_id:
        add(errors, "invalid_item_id", str(item_id))
    if item_id in seen_ids:
        add(errors, "duplicate_item_id", item_id)
    seen_ids.add(item_id)

    if item["schema_version"] != ITEM_SCHEMA_VERSION:
        add(errors, "item_schema_mismatch", item_id)
    if item["skill"] != "reading":
        add(errors, "skill_not_reading", item_id)
    if item["question_type"] not in QUESTION_TYPES:
        add(errors, "unknown_question_type", f"{item_id}:{item['question_type']}")
        return

    question_type = item["question_type"]
    source = item["source"]
    evidence = item["evidence"]
    prompt = item["prompt"]
    answer_model = item["answer_model"]
    lifecycle = item["lifecycle"]
    validation = item["validation"]

    if not isinstance(source, dict):
        add(errors, "source_not_object", item_id)
    else:
        missing_source = REQUIRED_SOURCE_KEYS - set(source)
        if missing_source:
            add(errors, "missing_source_keys", f"{item_id}:{sorted(missing_source)}")
        if source.get("source_type") not in QUESTION_SOURCE_TYPES[question_type]:
            add(errors, "source_type_incompatible", f"{item_id}:{source.get('source_type')}:{question_type}")
        if not source.get("source_intake_id") or not source.get("source_record_id") or not source.get("source_path"):
            add(errors, "source_traceability_incomplete", item_id)
        if source.get("generated_content") is not False:
            add(errors, "source_generated_content_not_false", item_id)
        if source.get("authority_status") != "candidate_only":
            add(errors, "source_not_candidate_only", item_id)
        if source.get("promotion_status") != "not_promoted":
            add(errors, "source_promoted", item_id)

    if not isinstance(evidence, dict):
        add(errors, "evidence_not_object", item_id)
    else:
        missing_evidence = REQUIRED_EVIDENCE_KEYS - set(evidence)
        if missing_evidence:
            add(errors, "missing_evidence_keys", f"{item_id}:{sorted(missing_evidence)}")
        if not isinstance(evidence.get("evidence_text"), str) or not evidence.get("evidence_text").strip():
            add(errors, "evidence_text_empty", item_id)
        if not is_list_of_strings(evidence.get("evidence_sentences")) or not evidence.get("evidence_sentences"):
            add(errors, "evidence_sentences_invalid", item_id)
        if evidence.get("sentence_count") != len(evidence.get("evidence_sentences", [])):
            add(errors, "evidence_sentence_count_mismatch", item_id)
        if evidence.get("supports_answer") is not True:
            add(errors, "evidence_supports_answer_not_true", item_id)

    if not isinstance(prompt, dict):
        add(errors, "prompt_not_object", item_id)
    else:
        missing_prompt = REQUIRED_PROMPT_KEYS - set(prompt)
        if missing_prompt:
            add(errors, "missing_prompt_keys", f"{item_id}:{sorted(missing_prompt)}")
        if question_type in {"literal_who", "literal_what", "literal_where", "true_false", "sentence_ordering", "cloze_vocabulary"}:
            validate_choices(item_id, prompt, answer_model if isinstance(answer_model, dict) else {}, errors)

    if not isinstance(answer_model, dict):
        add(errors, "answer_model_not_object", item_id)
    else:
        expected_answer_type = QUESTION_ANSWER_TYPES[question_type]
        if answer_model.get("answer_type") != expected_answer_type:
            add(errors, "answer_type_mismatch", f"{item_id}:{answer_model.get('answer_type')}:{expected_answer_type}")
        scoring = answer_model.get("scoring")
        if not isinstance(scoring, dict):
            add(errors, "scoring_not_object", item_id)
        elif scoring.get("mode") != QUESTION_SCORING_MODES[question_type]:
            add(errors, "scoring_mode_mismatch", f"{item_id}:{scoring.get('mode')}:{QUESTION_SCORING_MODES[question_type]}")
        if not answer_supported(item):
            add(errors, "answer_not_supported_by_evidence", item_id)

    if not isinstance(lifecycle, dict):
        add(errors, "lifecycle_not_object", item_id)
    else:
        missing_lifecycle = REQUIRED_LIFECYCLE_KEYS - set(lifecycle)
        if missing_lifecycle:
            add(errors, "missing_lifecycle_keys", f"{item_id}:{sorted(missing_lifecycle)}")
        if lifecycle.get("authority_status") != "candidate_only":
            add(errors, "lifecycle_not_candidate_only", item_id)
        if lifecycle.get("promotion_status") != "not_promoted":
            add(errors, "lifecycle_promoted", item_id)
        if lifecycle.get("learner_facing") is not False:
            add(errors, "lifecycle_learner_facing", item_id)
        if lifecycle.get("generated_item") is not True:
            add(errors, "lifecycle_generated_item_not_true", item_id)
        if lifecycle.get("generated_content") is not False:
            add(errors, "lifecycle_generated_content_not_false", item_id)

    if not isinstance(validation, dict):
        add(errors, "validation_not_object", item_id)
    else:
        if validation.get("validator_status") not in {"not_run", "pass", "fail", "PASS", "FAIL"}:
            add(errors, "invalid_validator_status", f"{item_id}:{validation.get('validator_status')}")


def summarize(payload, errors, warnings):
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return {
        "validator_task": VALIDATOR_TASK,
        "status": "FAIL" if errors else "PASS_WITH_WARNINGS" if warnings else "PASS",
        "total_items_checked": len(items) if isinstance(items, list) else 0,
        "by_question_type": dict(sorted(Counter(item.get("question_type") for item in items if isinstance(item, dict)).items())),
        "errors": errors,
        "warnings": warnings,
    }


def validate_payload(payload, summary_payload=None):
    errors = []
    warnings = []
    validate_top_level(payload, summary_payload, errors, warnings)
    seen_ids = set()
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        for item in payload["items"]:
            validate_item(item, seen_ids, errors, warnings)
    return summarize(payload if isinstance(payload, dict) else {}, errors, warnings)


def validate_files(items_path=ITEMS_PATH, summary_path=SUMMARY_PATH):
    if not Path(items_path).exists():
        return {"validator_task": VALIDATOR_TASK, "status": "FAIL", "total_items_checked": 0, "by_question_type": {}, "errors": [f"missing_items_file:{items_path}"], "warnings": []}
    payload = read_json(items_path)
    summary_payload = read_json(summary_path) if Path(summary_path).exists() else None
    return validate_payload(payload, summary_payload)


def parse_args():
    parser = argparse.ArgumentParser(description="Validate S17 Reading practice candidate items.")
    parser.add_argument("--items", default=str(ITEMS_PATH))
    parser.add_argument("--summary", default=str(SUMMARY_PATH))
    return parser.parse_args()


def main():
    args = parse_args()
    result = validate_files(args.items, args.summary)
    for warning in result["warnings"]:
        print(f"WARN: {warning}")
    for error in result["errors"]:
        print(f"FAIL: {error}")
    print(f"Reading practice item validation: {result['status']}")
    print(f"Items checked: {result['total_items_checked']}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
