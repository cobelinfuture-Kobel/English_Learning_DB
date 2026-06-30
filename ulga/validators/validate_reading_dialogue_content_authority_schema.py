import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_DIR = BASE_DIR / "ulga" / "schemas"

READING_SCHEMA_PATH = SCHEMA_DIR / "reading_content_authority_schema.json"
DIALOGUE_SCHEMA_PATH = SCHEMA_DIR / "dialogue_content_authority_schema.json"
READING_SAMPLE_PATH = SCHEMA_DIR / "sample_reading_content_authority.json"
DIALOGUE_SAMPLE_PATH = SCHEMA_DIR / "sample_dialogue_content_authority.json"

AUTHORITY_FAMILIES = ("grammar", "vocabulary", "theme", "pattern", "chunk")
AUTHORITY_LINKAGE_STATUSES = {"not_linked", "partial_linked", "linked_with_warnings", "fully_linked", "blocked", "needs_human_review"}
AUTHORITY_STATUSES = {"candidate_only", "reviewed_candidate", "promoted", "rejected"}
PROMOTION_STATUSES = {"not_promoted", "promotion_candidate", "promoted", "blocked", "rejected"}
REVIEW_STATUSES = {"pending", "auto_reviewed", "human_review_required", "human_reviewed", "rejected"}


class ValidationError(Exception):
    pass


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require(condition, message: str):
    if not condition:
        raise ValidationError(message)


def validate_schema_file(schema: dict, schema_name: str, title: str):
    require(isinstance(schema, dict), f"{schema_name} must be a JSON object")
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"{schema_name} must declare Draft 2020-12")
    require(schema.get("title") == title, f"{schema_name} title mismatch")
    require(schema.get("type") == "object", f"{schema_name} type must be object")
    require(schema.get("additionalProperties") is False, f"{schema_name} must set additionalProperties false")
    Draft202012Validator.check_schema(schema)


def validate_with_schema(schema: dict, payload: dict, label: str):
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValidationError(f"{label} schema validation failed at {path}: {first.message}")


def simple_word_count(text: str) -> int:
    return len(text.split())


def simple_sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    return len(parts)


def validate_source_seed_ref_shape(schema: dict):
    sample_ref = {
        "seed_id": "RAZ_G_1001_REUSE_000001",
        "seed_type": "reuse_unit",
        "source": "RAZ",
        "source_level": "G",
        "source_book_id": "1001",
        "source_page_number": 3,
    }
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors({"source_seed_refs": [sample_ref]}), key=lambda error: list(error.absolute_path))
    blocking_errors = [
        error
        for error in errors
        if list(error.absolute_path)[:1] == ["source_seed_refs"]
    ]
    require(not blocking_errors, "source_seed_refs must accept source_level G for future RAZ levels")


def validate_linkage_fields(payload: dict, label: str):
    require(isinstance(payload.get("source_seed_refs"), list), f"{label} source_seed_refs must be a list")
    authority_refs = payload.get("authority_refs")
    require(isinstance(authority_refs, dict), f"{label} authority_refs must be an object")
    for family in ("grammar_refs", "vocabulary_refs", "theme_refs", "pattern_refs", "chunk_refs"):
        require(family in authority_refs, f"{label} authority_refs.{family} must exist")
        require(isinstance(authority_refs[family], list), f"{label} authority_refs.{family} must be a list")

    unresolved = payload.get("unresolved_authority_refs")
    require(isinstance(unresolved, dict), f"{label} unresolved_authority_refs must be an object")
    for family in AUTHORITY_FAMILIES:
        require(family in unresolved, f"{label} unresolved_authority_refs.{family} must exist")
        require(isinstance(unresolved[family], list), f"{label} unresolved_authority_refs.{family} must be a list")

    require(payload.get("authority_linkage_status") in AUTHORITY_LINKAGE_STATUSES, f"{label} authority_linkage_status is invalid")
    require(bool(payload.get("authority_linkage_policy_version", "").strip()), f"{label} authority_linkage_policy_version must be non-empty")
    require(isinstance(payload.get("authority_linkage_warnings"), list), f"{label} authority_linkage_warnings must be a list")
    require(payload.get("authority_status") in AUTHORITY_STATUSES, f"{label} authority_status is invalid")
    require(payload.get("promotion_status") in PROMOTION_STATUSES, f"{label} promotion_status is invalid")
    require(payload.get("review_status") in REVIEW_STATUSES, f"{label} review_status is invalid")
    require(isinstance(payload.get("final_eligible"), bool), f"{label} final_eligible must be a boolean")

    if payload.get("validation_status") == "candidate":
        require(payload.get("authority_status") == "candidate_only", f"{label} candidate payload must keep authority_status candidate_only")
        require(payload.get("promotion_status") == "not_promoted", f"{label} candidate payload must keep promotion_status not_promoted")
        require(payload.get("final_eligible") is False, f"{label} candidate payload must keep final_eligible false")

    if payload.get("authority_linkage_status") == "fully_linked":
        for family in AUTHORITY_FAMILIES:
            require(not unresolved[family], f"{label} fully_linked payload cannot keep unresolved_authority_refs.{family}")

    expected_vocabulary = set(payload.get("focus_vocabulary_refs", [])) | set(payload.get("reinforcement_vocabulary_refs", []))
    require(set(authority_refs.get("theme_refs", [])) == set(payload.get("theme_refs", [])), f"{label} authority_refs.theme_refs must match theme_refs")
    require(set(authority_refs.get("grammar_refs", [])) == set(payload.get("grammar_refs", [])), f"{label} authority_refs.grammar_refs must match grammar_refs")
    require(set(authority_refs.get("pattern_refs", [])) == set(payload.get("pattern_refs", [])), f"{label} authority_refs.pattern_refs must match pattern_refs")
    require(set(authority_refs.get("chunk_refs", [])) == set(payload.get("chunk_refs", [])), f"{label} authority_refs.chunk_refs must match chunk_refs")
    require(set(authority_refs.get("vocabulary_refs", [])) == expected_vocabulary, f"{label} authority_refs.vocabulary_refs must match focus + reinforcement vocabulary refs")


def validate_reading_semantics(payload: dict):
    require(payload.get("content_type") == "reading", "reading sample content_type must equal reading")
    require(payload.get("reading_id"), "reading sample reading_id must be non-empty")
    require(payload.get("linked_opportunity"), "reading sample linked_opportunity must be non-empty")
    text = payload.get("text", "")
    require(text.strip(), "reading sample text must be non-empty after trimming")
    require(payload.get("word_count", 0) >= 1, "reading sample word_count must be >= 1")
    require(payload.get("sentence_count", 0) >= 1, "reading sample sentence_count must be >= 1")
    require(payload.get("word_count") == simple_word_count(text), "reading sample word_count must match simple whitespace token count")
    require(payload.get("sentence_count") == simple_sentence_count(text), "reading sample sentence_count must match simple sentence split count")
    validate_linkage_fields(payload, "reading sample")


def validate_dialogue_semantics(payload: dict):
    require(payload.get("content_type") == "dialogue", "dialogue sample content_type must equal dialogue")
    require(payload.get("dialogue_id"), "dialogue sample dialogue_id must be non-empty")
    turns = payload.get("turns", [])
    require(isinstance(turns, list) and turns, "dialogue sample turns must be a non-empty list")
    require(payload.get("turn_count") == len(turns), "dialogue sample turn_count must match turns length")
    require(payload.get("turn_count", 0) >= 2, "dialogue sample turn_count must be >= 2")
    for index, turn in enumerate(turns):
        require(turn.get("speaker", "").strip(), f"dialogue sample turns[{index}].speaker must be non-empty")
        require(turn.get("text", "").strip(), f"dialogue sample turns[{index}].text must be non-empty")
    validate_linkage_fields(payload, "dialogue sample")


def validate_paths():
    reading_schema = load_json(READING_SCHEMA_PATH)
    dialogue_schema = load_json(DIALOGUE_SCHEMA_PATH)
    reading_sample = load_json(READING_SAMPLE_PATH)
    dialogue_sample = load_json(DIALOGUE_SAMPLE_PATH)

    validate_schema_file(reading_schema, "reading_content_authority_schema.json", "ULGA Reading Content Authority Record")
    validate_schema_file(dialogue_schema, "dialogue_content_authority_schema.json", "ULGA Dialogue Content Authority Record")
    validate_with_schema(reading_schema, reading_sample, "sample_reading_content_authority.json")
    validate_with_schema(dialogue_schema, dialogue_sample, "sample_dialogue_content_authority.json")
    validate_source_seed_ref_shape(reading_schema)
    validate_source_seed_ref_shape(dialogue_schema)
    validate_reading_semantics(reading_sample)
    validate_dialogue_semantics(dialogue_sample)


def main():
    try:
        validate_paths()
    except Exception as exc:
        print(f"Reading/dialogue content authority schema validation: FAIL - {exc}")
        return 1
    print("Reading/dialogue content authority schema validation: PASS")
    print(f"Validated {READING_SCHEMA_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {DIALOGUE_SCHEMA_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {READING_SAMPLE_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {DIALOGUE_SAMPLE_PATH.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
