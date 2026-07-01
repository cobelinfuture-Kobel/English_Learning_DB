from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "ulga" / "schemas" / "raz_reading_authority_intake.schema.json"
SAMPLE_PATH = BASE_DIR / "ulga" / "schemas" / "sample_raz_reading_authority_intake_candidates.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_schema_summary.json"
VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_schema_validation.json"

TASK_NAME = "RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation"
SCHEMA_VERSION = "raz_reading_authority_intake.v1"
LEVELS_AW = [chr(code) for code in range(ord("A"), ord("W") + 1)]
UNIT_TYPES = ["sentence", "page_unit", "reuse_unit"]


class ValidationError(Exception):
    pass


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def stable_path(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def validate_schema_file(schema: dict[str, Any]) -> None:
    require(isinstance(schema, dict), "schema must be a JSON object")
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "schema must declare Draft 2020-12")
    require(schema.get("title") == "RAZ Reading Authority Intake Candidate", "schema title mismatch")
    require(schema.get("type") == "object", "schema type must be object")
    require(schema.get("additionalProperties") is False, "schema must set additionalProperties false")
    Draft202012Validator.check_schema(schema)


def normalize_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        records = payload["records"]
    elif isinstance(payload, dict):
        records = [payload]
    else:
        raise ValidationError("payload must be an object, a list of objects, or an object with records array")

    for index, record in enumerate(records):
        require(isinstance(record, dict), f"record[{index}] must be an object")
    return records


def validate_with_schema(schema: dict[str, Any], record: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValidationError(f"{label} schema validation failed at {path}: {first.message}")


def simple_word_count(text: str) -> int:
    return len(text.split())


def simple_sentence_count(text: str) -> int:
    chunks = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    return len(chunks) if chunks else 0


def _expected_source_type(unit_type: str) -> str:
    mapping = {
        "sentence": "raz_enriched_sentence",
        "page_unit": "raz_enriched_page_unit",
        "reuse_unit": "raz_enriched_reuse_unit",
    }
    return mapping[unit_type]


def validate_record_semantics(record: dict[str, Any], seen_ids: set[str] | None = None) -> list[str]:
    warnings: list[str] = []
    intake_id = record.get("reading_intake_id", "<missing>")
    source_level = record.get("source_level")
    normalized_level = record.get("normalized_level")
    unit_type = record.get("unit_type")

    require(bool(str(intake_id).strip()), "missing reading_intake_id")
    if seen_ids is not None:
        require(intake_id not in seen_ids, f"duplicate intake id: {intake_id}")
        seen_ids.add(intake_id)

    require(source_level in LEVELS_AW, "invalid source_level outside A-W")
    require(normalized_level in LEVELS_AW, "invalid normalized_level outside A-W")
    require(source_level == normalized_level, "normalized_level must match source_level for intake staging")
    require(unit_type in UNIT_TYPES, "invalid unit_type")

    source_traceability = record.get("source_traceability")
    require(isinstance(source_traceability, dict), "source_traceability missing")
    require(bool(str(source_traceability.get("source_artifact_path", "")).strip()), "source_artifact_path missing")
    require(bool(str(source_traceability.get("source_record_id", "")).strip()), "source_record_id missing")
    require(bool(str(source_traceability.get("book_id", "")).strip()), "book_id missing where source provides it")
    sentence_ids = source_traceability.get("source_sentence_candidate_ids")
    require(isinstance(sentence_ids, list) and bool(sentence_ids), "source_sentence_candidate_ids empty for sentence/page/reuse units")
    require(source_traceability.get("derived_from_original_text") is True, "derived_from_original_text must be true")
    require(source_traceability.get("generated_content") is False, "generated_content=true is blocked")
    require(source_traceability.get("source_type") == _expected_source_type(unit_type), "unit_type conflicts with source_type")

    if unit_type in {"page_unit", "reuse_unit"}:
        require(source_traceability.get("page_number") is not None, "page_number missing for page/reuse units where source provides it")
        require(bool(str(source_traceability.get("page_unit_id", "")).strip()), "page_unit_id missing for page/reuse units where source provides it")

    text = record.get("text")
    require(isinstance(text, dict), "text payload missing")
    clean_text = str(text.get("clean_text", ""))
    require(bool(clean_text), "missing clean_text")
    require(bool(clean_text.strip()), "empty clean_text")
    require(isinstance(text.get("sentence_count"), int) and text["sentence_count"] > 0, "sentence_count <= 0")
    require(text.get("text_language") == "en", "text_language must be en")
    require(text.get("text_role") == "reading_source_text", "text_role must be reading_source_text")

    if "word_count" in text:
        require(isinstance(text["word_count"], int) and text["word_count"] > 0, "word_count must be > 0 when present")
        if text["word_count"] != simple_word_count(clean_text):
            warnings.append("word_count differs from simple whitespace token count")
    else:
        warnings.append("word_count missing or computed downstream")

    if text["sentence_count"] != simple_sentence_count(clean_text):
        warnings.append("sentence_count differs from simple punctuation sentence count")

    pedagogical_tags = record.get("pedagogical_tags")
    require(isinstance(pedagogical_tags, dict), "pedagogical_tags missing")
    require(pedagogical_tags.get("raz_level") == source_level, "pedagogical_tags.raz_level must match source_level")
    for field_name in ["theme_tags", "vocabulary_tags", "grammar_tags", "pattern_tags"]:
        if not pedagogical_tags.get(field_name):
            warnings.append(f"{field_name} empty")
    if pedagogical_tags.get("cefr_estimate") in {None, ""}:
        warnings.append("cefr_estimate missing")
    require("reading" in pedagogical_tags.get("skill_area", []), "skill_area must include reading")
    require(bool(pedagogical_tags.get("reusability_tags")), "reusability_tags must be non-empty")

    authority = record.get("authority")
    require(isinstance(authority, dict), "authority payload missing")
    require(authority.get("authority_status") == "candidate_only", "authority_status != candidate_only")
    require(authority.get("promotion_allowed") is False, "promotion_allowed != false")
    require(authority.get("promotion_status") == "not_promoted", "promotion_status != not_promoted")
    require(bool(str(authority.get("review_status", "")).strip()), "review_status missing")
    require(authority.get("final_eligible") is False, "final_eligible = true")

    qa = record.get("qa")
    require(isinstance(qa, dict), "qa payload missing")
    require(isinstance(qa.get("block_reasons"), list), "qa.block_reasons must be a list")
    require(isinstance(qa.get("warnings"), list), "qa.warnings must be a list")
    require(qa.get("generated_content_block_status") != "fail" or source_traceability.get("generated_content") is True, "generated_content_block_status inconsistent")

    if not source_traceability.get("book_title"):
        warnings.append("book_title missing")
    if record.get("query_layer_ready") is False:
        warnings.append("query_layer_ready false for G-W is not a schema blocker")
    if source_level in {"K", "M"} and unit_type == "sentence":
        warnings.append("non-blocking K/M sentence count parity note inherited from S6B")

    return warnings


def validate_payload(payload: Any) -> dict[str, Any]:
    schema = load_json(SCHEMA_PATH)
    validate_schema_file(schema)
    records = normalize_payload(payload)
    seen_ids: set[str] = set()
    blocking_errors: list[str] = []
    warnings: list[str] = []

    for index, record in enumerate(records):
        label = f"record[{index}]"
        try:
            validate_with_schema(schema, record, label)
            warnings.extend(validate_record_semantics(record, seen_ids=seen_ids))
        except ValidationError as exc:
            blocking_errors.append(f"{label}: {exc}")

    return {
        "task": TASK_NAME,
        "status": "PASS" if not blocking_errors else "FAIL",
        "records_checked": len(records),
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "schema_path": stable_path(SCHEMA_PATH),
    }


def _sample_record(record_index: int = 0) -> dict[str, Any]:
    sample_payload = load_json(SAMPLE_PATH)
    return json.loads(json.dumps(sample_payload["records"][record_index]))


def build_summary_report() -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "status": "IMPLEMENTED",
        "scope_levels": LEVELS_AW,
        "schema_version": SCHEMA_VERSION,
        "supported_unit_types": UNIT_TYPES,
        "authority_status": "candidate_only",
        "promotion_allowed": False,
        "generated_content_allowed": False,
        "builder_implemented": False,
        "authority_promotion_implemented": False,
        "recommended_next_task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
    }


def build_validation_report() -> dict[str, Any]:
    sample_payload = load_json(SAMPLE_PATH)
    single_result = validate_payload(sample_payload["records"][0])
    list_result = validate_payload(sample_payload["records"])
    records_result = validate_payload(sample_payload)
    blocking_errors = single_result["blocking_errors"] + list_result["blocking_errors"] + records_result["blocking_errors"]
    warning_count = len(single_result["warnings"]) + len(list_result["warnings"]) + len(records_result["warnings"])
    return {
        "task": TASK_NAME,
        "status": "PASS" if not blocking_errors else "FAIL",
        "blocking_error_count": len(blocking_errors),
        "warning_count": warning_count,
        "schema_path": stable_path(SCHEMA_PATH),
        "test_fixture_status": "PASS" if not blocking_errors else "FAIL",
        "validated_payload_shapes": [
            "single_object",
            "list",
            "object_with_records_array",
        ],
    }


def validate_paths() -> None:
    schema = load_json(SCHEMA_PATH)
    sample_payload = load_json(SAMPLE_PATH)
    validate_schema_file(schema)
    require(isinstance(sample_payload, dict), "sample payload must be an object")
    require(isinstance(sample_payload.get("records"), list) and len(sample_payload["records"]) == 3, "sample payload must provide three records")
    for payload in [sample_payload["records"][0], sample_payload["records"], sample_payload]:
        result = validate_payload(payload)
        require(result["status"] == "PASS", f"fixture validation failed: {result['blocking_errors']}")


def main() -> int:
    try:
        validate_paths()
        summary = build_summary_report()
        validation = build_validation_report()
        write_json(SUMMARY_PATH, summary)
        write_json(VALIDATION_PATH, validation)
    except Exception as exc:
        failure_report = {
            "task": TASK_NAME,
            "status": "FAIL",
            "blocking_error_count": 1,
            "warning_count": 0,
            "schema_path": stable_path(SCHEMA_PATH),
            "test_fixture_status": "FAIL",
            "failure_reason": str(exc),
        }
        write_json(VALIDATION_PATH, failure_report)
        print(f"RAZ reading authority intake schema validation: FAIL - {exc}")
        return 1

    print("RAZ reading authority intake schema validation: PASS")
    print(f"Validated {stable_path(SCHEMA_PATH)}")
    print(f"Validated {stable_path(SAMPLE_PATH)}")
    print(f"Wrote {stable_path(SUMMARY_PATH)}")
    print(f"Wrote {stable_path(VALIDATION_PATH)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
