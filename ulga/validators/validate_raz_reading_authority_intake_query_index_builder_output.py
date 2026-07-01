import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

INDEX_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_query_index.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_summary.json"

SCHEMA_VERSION = "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_V1"
SUMMARY_SCHEMA_VERSION = "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_SUMMARY_V1"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "builder_task",
    "generated_at",
    "source_policy",
    "levels",
    "items",
    "query_indexes",
    "summary",
}

REQUIRED_ITEM_KEYS = {
    "intake_id",
    "source_type",
    "level",
    "book_id",
    "page_number",
    "sentence_count",
    "clean_text",
    "sentence_candidate_ids",
    "source_page_unit_id",
    "source_reuse_unit_id",
    "authority_status",
    "promotion_status",
    "generated_content",
    "source_traceability",
    "query_tags",
    "quality_flags",
    "notes",
}

REQUIRED_QUERY_TAG_KEYS = {
    "level",
    "book_id",
    "theme_hints",
    "grammar_tags",
    "pattern_tags",
    "vocabulary_tags",
    "reusability_tags",
    "derivation_potential",
    "has_multi_sentence_unit",
    "is_short_reading_seed",
    "is_writing_model_seed",
    "is_dialogue_rewrite_seed",
    "is_exercise_seed",
}

REQUIRED_INDEX_KEYS = {
    "by_level",
    "by_book_id",
    "by_level_and_book",
    "by_source_type",
    "by_reusability_tag",
    "by_authority_status",
    "by_promotion_status",
    "by_sentence_count_bucket",
    "by_multi_sentence_status",
    "by_theme_hint",
    "by_grammar_tag",
    "by_pattern_tag",
    "by_vocabulary_tag",
}

FINAL_AUTHORITY_STATUSES = {
    "authority",
    "final",
    "final_authority",
    "promoted",
    "published",
    "approved_for_authority",
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:
        return None, f"could not load {path}: {exc}"


def sentence_count_bucket(sentence_count):
    if not isinstance(sentence_count, int) or sentence_count <= 0:
        return "unknown"
    if sentence_count == 1:
        return "single_sentence"
    if sentence_count == 2:
        return "two_sentences"
    if 3 <= sentence_count <= 5:
        return "three_to_five_sentences"
    return "six_plus_sentences"


def add_error(errors, message):
    errors.append(f"FAIL: {message}")


def add_warning(warnings, message):
    warnings.append(f"WARN: {message}")


def ensure_list_of_strings(value, label, errors):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        add_error(errors, f"{label} must be a list of strings")


def validate_item(item, seen_ids, errors, warnings):
    if not isinstance(item, dict):
        add_error(errors, "every item must be an object")
        return

    missing = REQUIRED_ITEM_KEYS - set(item)
    if missing:
        add_error(errors, f"{item.get('intake_id', 'unknown')} missing item keys: {sorted(missing)}")
        return

    intake_id = item["intake_id"]
    if not isinstance(intake_id, str) or not intake_id.startswith("RAZ_AW_S11_INTAKE_"):
        add_error(errors, f"invalid intake_id: {intake_id}")
    if intake_id in seen_ids:
        add_error(errors, f"duplicate intake_id: {intake_id}")
    seen_ids.add(intake_id)

    if not isinstance(item["clean_text"], str):
        add_error(errors, f"{intake_id} clean_text must be a string")
    if not isinstance(item["sentence_count"], int) or item["sentence_count"] < 0:
        add_error(errors, f"{intake_id} sentence_count must be a non-negative integer")

    if item["authority_status"] in FINAL_AUTHORITY_STATUSES:
        add_error(errors, f"{intake_id} was promoted to final authority")
    if item["authority_status"] != "candidate_only":
        add_warning(warnings, f"{intake_id} authority_status is not candidate_only: {item['authority_status']}")
    if item["promotion_status"] in FINAL_AUTHORITY_STATUSES or item["promotion_status"] == "promoted":
        add_error(errors, f"{intake_id} promotion_status indicates promotion")

    if not isinstance(item["generated_content"], bool):
        add_error(errors, f"{intake_id} generated_content must be boolean")
    if item["generated_content"] is True:
        add_error(errors, f"{intake_id} generated_content must remain false for RAZ intake index")

    ensure_list_of_strings(item["sentence_candidate_ids"], f"{intake_id}.sentence_candidate_ids", errors)
    ensure_list_of_strings(item["quality_flags"], f"{intake_id}.quality_flags", errors)
    ensure_list_of_strings(item["notes"], f"{intake_id}.notes", errors)

    source_traceability = item["source_traceability"]
    if not isinstance(source_traceability, dict):
        add_error(errors, f"{intake_id} source_traceability must be an object")
    else:
        if not source_traceability.get("source_path"):
            add_error(errors, f"{intake_id} source_traceability.source_path is required")
        if source_traceability.get("generated_content") is True:
            add_error(errors, f"{intake_id} source_traceability.generated_content must be false")

    query_tags = item["query_tags"]
    if not isinstance(query_tags, dict):
        add_error(errors, f"{intake_id} query_tags must be an object")
    else:
        missing_tags = REQUIRED_QUERY_TAG_KEYS - set(query_tags)
        if missing_tags:
            add_error(errors, f"{intake_id} missing query_tags: {sorted(missing_tags)}")
        for key in ["theme_hints", "grammar_tags", "pattern_tags", "vocabulary_tags", "reusability_tags"]:
            ensure_list_of_strings(query_tags.get(key), f"{intake_id}.query_tags.{key}", errors)
        for key in [
            "has_multi_sentence_unit",
            "is_short_reading_seed",
            "is_writing_model_seed",
            "is_dialogue_rewrite_seed",
            "is_exercise_seed",
        ]:
            if not isinstance(query_tags.get(key), bool):
                add_error(errors, f"{intake_id}.query_tags.{key} must be boolean")
        expected_multi_sentence = item["sentence_count"] > 1
        if query_tags.get("has_multi_sentence_unit") != expected_multi_sentence:
            add_error(errors, f"{intake_id} multi-sentence flag does not match sentence_count")


def validate_indexes(indexes, item_ids, errors):
    if not isinstance(indexes, dict):
        add_error(errors, "query_indexes must be an object")
        return

    missing = REQUIRED_INDEX_KEYS - set(indexes)
    if missing:
        add_error(errors, f"query_indexes missing required keys: {sorted(missing)}")

    for index_name in REQUIRED_INDEX_KEYS:
        index = indexes.get(index_name, {})
        if not isinstance(index, dict):
            add_error(errors, f"{index_name} must be an object")
            continue
        for key, values in index.items():
            if not isinstance(key, str):
                add_error(errors, f"{index_name} contains a non-string key")
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                add_error(errors, f"{index_name}.{key} must be a list of intake IDs")
                continue
            for value in values:
                if value not in item_ids:
                    add_error(errors, f"{index_name}.{key} references unknown intake_id {value}")


def validate_summary(payload, summary_file_payload, errors):
    items = payload["items"]
    summary = payload["summary"]

    if summary != summary_file_payload:
        add_error(errors, "embedded summary does not match summary file")
        return

    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        add_error(errors, "summary schema_version mismatch")
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "FAIL"}:
        add_error(errors, "summary status must be PASS, PASS_WITH_WARNINGS, or FAIL")
    if summary.get("total_items") != len(items):
        add_error(errors, "summary total_items does not match items length")

    by_source_type = dict(sorted(Counter(item["source_type"] for item in items).items()))
    by_level = dict(sorted(Counter(item["level"] for item in items).items()))
    by_sentence_count_bucket = dict(
        sorted(Counter(sentence_count_bucket(item["sentence_count"]) for item in items).items())
    )
    reusability_counter = Counter()
    for item in items:
        reusability_counter.update(item["query_tags"]["reusability_tags"])

    if summary.get("by_source_type") != by_source_type:
        add_error(errors, "summary by_source_type does not match items")
    if summary.get("by_level") != by_level:
        add_error(errors, "summary by_level does not match items")
    if summary.get("by_sentence_count_bucket") != by_sentence_count_bucket:
        add_error(errors, "summary by_sentence_count_bucket does not match items")
    if summary.get("by_reusability_tag") != dict(sorted(reusability_counter.items())):
        add_error(errors, "summary by_reusability_tag does not match items")

    expected_multi_sentence_count = sum(1 for item in items if item["sentence_count"] > 1)
    if summary.get("multi_sentence_item_count") != expected_multi_sentence_count:
        add_error(errors, "summary multi_sentence_item_count does not match items")
    if summary.get("promoted_count") != 0:
        add_error(errors, "summary promoted_count must be 0")
    if summary.get("candidate_only_count") != sum(1 for item in items if item["authority_status"] == "candidate_only"):
        add_error(errors, "summary candidate_only_count does not match items")


def validate():
    errors = []
    warnings = []

    if not INDEX_PATH.exists():
        add_error(errors, f"required file does not exist: {INDEX_PATH}")
    if not SUMMARY_PATH.exists():
        add_error(errors, f"required file does not exist: {SUMMARY_PATH}")
    if errors:
        for message in errors:
            print(message)
        return False

    payload, payload_error = read_json(INDEX_PATH)
    if payload_error:
        add_error(errors, payload_error)
        payload = None

    summary_payload, summary_error = read_json(SUMMARY_PATH)
    if summary_error:
        add_error(errors, summary_error)
        summary_payload = None

    if payload is None or summary_payload is None:
        for message in errors:
            print(message)
        return False

    if not isinstance(payload, dict):
        add_error(errors, "index payload must be an object")
    else:
        missing = REQUIRED_TOP_LEVEL_KEYS - set(payload)
        if missing:
            add_error(errors, f"index missing top-level keys: {sorted(missing)}")

    if errors:
        for message in errors:
            print(message)
        return False

    if payload["schema_version"] != SCHEMA_VERSION:
        add_error(errors, "schema_version mismatch")

    source_policy = payload["source_policy"]
    if not isinstance(source_policy, dict):
        add_error(errors, "source_policy must be an object")
    else:
        expected_policy = {
            "offline_static_only": True,
            "generated_content": False,
            "authority_promotion": False,
            "candidate_only_preserved": True,
        }
        for key, expected_value in expected_policy.items():
            if source_policy.get(key) is not expected_value:
                add_error(errors, f"source_policy.{key} must be {expected_value}")

    if not isinstance(payload["levels"], list) or not all(isinstance(level, str) for level in payload["levels"]):
        add_error(errors, "levels must be a list of strings")
    if not isinstance(payload["items"], list):
        add_error(errors, "items must be a list")

    seen_ids = set()
    if isinstance(payload["items"], list):
        for item in payload["items"]:
            validate_item(item, seen_ids, errors, warnings)

    validate_indexes(payload["query_indexes"], seen_ids, errors)
    validate_summary(payload, summary_payload, errors)

    for message in warnings:
        print(message)
    for message in errors:
        print(message)

    if errors:
        print("RAZ Reading Authority Intake Query Index builder output validation: FAIL")
        return False

    if warnings:
        print("RAZ Reading Authority Intake Query Index builder output validation: PASS_WITH_WARNINGS")
    else:
        print("RAZ Reading Authority Intake Query Index builder output validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
