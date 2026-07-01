from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "ulga" / "schemas" / "raz_reading_authority_intake_query_index.schema.json"
SAMPLE_PATH = BASE_DIR / "ulga" / "schemas" / "sample_raz_reading_authority_intake_query_index.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_contract_summary.json"
VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_contract_validation.json"

TASK_NAME = "RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation"
SCHEMA_VERSION = "raz_reading_authority_intake_query_index.v1"
LEVELS_AW = [chr(code) for code in range(ord("A"), ord("W") + 1)]
APPROVED_LEVELS = set(["A", "B", "C", "D", "E", "F"])
STAGED_LEVELS = set(level for level in LEVELS_AW if level not in APPROVED_LEVELS)
UNIT_TYPES = ["sentence", "page_unit", "reuse_unit"]
QUERY_STATUSES = [
    "approved_candidate",
    "staged_candidate_not_query_approved",
    "blocked_from_query_policy",
    "metadata_review_candidate",
]
WARNING_FAMILIES = {
    "MISSING_CEFR_ESTIMATE",
    "SPARSE_PEDAGOGICAL_TAGS",
    "QUERY_LAYER_NOT_READY_G_TO_W",
    "MISSING_BOOK_TITLE",
    "LEGACY_TAG_COMPATIBILITY_MAPPED",
    "UNSUPPORTED_LEGACY_REUSABILITY_TAG",
    "S6B_PARITY_NOTE_INHERITED",
    "SENTENCE_COUNT_HEURISTIC_MISMATCH",
    "SOURCE_UNKNOWN_THEME",
    "SOURCE_UNKNOWN_PATTERN",
    "SOURCE_UNKNOWN_GRAMMAR",
    "SOURCE_SECTION_HEADING_DETECTED",
    "MISSING_WORD_COUNT_OR_DERIVED_WORD_COUNT",
}
SOURCE_ARTIFACT_PATH = "ulga/graph/raz_reading_authority_intake_candidates.json"
SOURCE_HASH = "96040b787816dd1ef193c680cefb4c350a08d6e78f8619759f8716a71a4e0fc6"


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
    require(schema.get("title") == "RAZ Reading Authority Intake Query Index Record", "schema title mismatch")
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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                require(isinstance(value, dict), "jsonl row must be an object")
                records.append(value)
    return records


def load_payload_path(payload_path: Path) -> Any:
    resolved_path = payload_path if payload_path.is_absolute() else BASE_DIR / payload_path
    if resolved_path.suffix == ".jsonl":
        return load_jsonl(resolved_path)
    return load_json(resolved_path)


def validate_with_schema(schema: dict[str, Any], record: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValidationError(f"{label} schema validation failed at {path}: {first.message}")


def validate_record_semantics(record: dict[str, Any], seen_ids: set[str] | None = None) -> None:
    reading_intake_id = record.get("reading_intake_id")
    source_level = record.get("source_level")
    normalized_level = record.get("normalized_level")
    unit_type = record.get("unit_type")
    query_status = record.get("query_status")
    query_layer_ready = record.get("query_layer_ready")
    query_layer_approved = record.get("query_layer_approved")

    require(bool(str(reading_intake_id or "").strip()), "missing reading_intake_id")
    if seen_ids is not None:
        require(reading_intake_id not in seen_ids, f"duplicate reading_intake_id: {reading_intake_id}")
        seen_ids.add(reading_intake_id)

    require(source_level in LEVELS_AW, "invalid source_level outside A-W")
    require(normalized_level == source_level, "normalized_level must match source_level")
    require(unit_type in UNIT_TYPES, "invalid unit_type")
    require(query_status in QUERY_STATUSES, "invalid query_status")

    authority = record.get("authority") or {}
    require(authority.get("authority_status") == "candidate_only", "authority_status != candidate_only")
    require(authority.get("candidate_only") is True, "candidate_only != true")
    require(authority.get("promotion_allowed") is False, "promotion_allowed != false")
    require(authority.get("promotion_status") == "not_promoted", "promotion_status != not_promoted")
    require(authority.get("final_eligible") is False, "final_eligible = true")

    artifact_pointer = record.get("artifact_pointer") or {}
    require(artifact_pointer.get("source_artifact") == SOURCE_ARTIFACT_PATH, "source_artifact path mismatch")
    require(artifact_pointer.get("source_artifact_status") == "LOCAL_ONLY", "source_artifact_status must be LOCAL_ONLY")
    require(artifact_pointer.get("source_hash_sha256") == SOURCE_HASH, "source_hash_sha256 mismatch")
    require(artifact_pointer.get("source_record_id") == reading_intake_id, "source_record_id must match reading_intake_id")

    warnings = record.get("warnings") or {}
    families = warnings.get("families") or []
    require(isinstance(families, list), "warnings.families must be a list")
    require(warnings.get("count") == len(families), "warnings.count must equal number of warning families")
    require(warnings.get("blocking") is False, "warnings.blocking must remain false")
    for family in families:
        require(family in WARNING_FAMILIES, f"unknown warning family: {family}")

    if query_status == "approved_candidate":
        require(source_level in APPROVED_LEVELS, "approved_candidate must be restricted to A-F")
        require(query_layer_ready is True, "approved_candidate requires query_layer_ready=true")
        require(query_layer_approved is True, "approved_candidate requires query_layer_approved=true")
    elif source_level in APPROVED_LEVELS:
        require(query_layer_approved is False or query_status == "approved_candidate", "A-F query_layer_approved=true requires approved_candidate")

    if source_level in STAGED_LEVELS:
        require(query_status != "approved_candidate", "G-W must not use approved_candidate")
        require(query_layer_approved is False, "G-W must not set query_layer_approved=true")
        require(query_layer_ready is False, "G-W must remain query_layer_ready=false in S10A contract")
        require(
            query_status in {"staged_candidate_not_query_approved", "metadata_review_candidate", "blocked_from_query_policy"},
            "G-W query_status must remain staged or policy-blocked",
        )
        if query_status in {"staged_candidate_not_query_approved", "metadata_review_candidate"}:
            require("QUERY_LAYER_NOT_READY_G_TO_W" in families, "staged G-W records must include QUERY_LAYER_NOT_READY_G_TO_W")


def validate_payload(payload: Any) -> dict[str, Any]:
    schema = load_json(SCHEMA_PATH)
    validate_schema_file(schema)
    records = normalize_payload(payload)
    seen_ids: set[str] = set()
    blocking_errors: list[str] = []
    promotion_violation_count = 0
    query_policy_violation_count = 0
    unknown_warning_family_count = 0

    for index, record in enumerate(records):
        label = f"record[{index}]"
        try:
            validate_with_schema(schema, record, label)
            validate_record_semantics(record, seen_ids=seen_ids)
        except ValidationError as exc:
            message = str(exc)
            blocking_errors.append(f"{label}: {message}")
            if "promotion_allowed" in message or "final_eligible" in message or "authority_status" in message or "candidate_only" in message:
                promotion_violation_count += 1
            if "approved_candidate" in message or "query_layer_approved" in message or "query_layer_ready" in message or "QUERY_LAYER_NOT_READY_G_TO_W" in message:
                query_policy_violation_count += 1
            if "unknown warning family" in message:
                unknown_warning_family_count += 1

    return {
        "task": TASK_NAME,
        "status": "PASS" if not blocking_errors else "FAIL",
        "records_checked": len(records),
        "blocking_errors": blocking_errors,
        "promotion_violation_count": promotion_violation_count,
        "query_policy_violation_count": query_policy_violation_count,
        "unknown_warning_family_count": unknown_warning_family_count,
        "schema_path": stable_path(SCHEMA_PATH),
    }


def build_summary_report() -> dict[str, Any]:
    sample_payload = load_json(SAMPLE_PATH)
    records = normalize_payload(sample_payload)
    return {
        "task": TASK_NAME,
        "status": "PASS",
        "schema_path": stable_path(SCHEMA_PATH),
        "sample_fixture_path": stable_path(SAMPLE_PATH),
        "validator_path": stable_path(Path(__file__)),
        "records_in_fixture": len(records),
        "full_index_built": False,
        "large_artifact_required": False,
        "promotion_allowed": False,
        "query_layer_expansion": False,
        "recommended_next_task": "RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation",
    }


def build_validation_report(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "status": result["status"],
        "schema_validation_status": "PASS" if result["status"] == "PASS" else "FAIL",
        "policy_validation_status": "PASS" if result["status"] == "PASS" else "FAIL",
        "blocking_error_count": len(result["blocking_errors"]),
        "promotion_violation_count": result["promotion_violation_count"],
        "query_policy_violation_count": result["query_policy_violation_count"],
        "unknown_warning_family_count": result["unknown_warning_family_count"],
        "full_artifact_touched": False,
    }


def validate_paths() -> None:
    schema = load_json(SCHEMA_PATH)
    sample_payload = load_json(SAMPLE_PATH)
    validate_schema_file(schema)
    require(isinstance(sample_payload, dict), "sample payload must be an object")
    require(isinstance(sample_payload.get("records"), list) and len(sample_payload["records"]) == 5, "sample payload must provide five records")
    for payload in [sample_payload["records"][0], sample_payload["records"], sample_payload]:
        result = validate_payload(payload)
        require(result["status"] == "PASS", f"fixture validation failed: {result['blocking_errors']}")


def validate_payload_path(payload_path: Path) -> dict[str, Any]:
    resolved_path = payload_path if payload_path.is_absolute() else (BASE_DIR / payload_path)
    payload = load_payload_path(resolved_path)
    result = validate_payload(payload)
    result["payload_path"] = stable_path(resolved_path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    target_path = Path(args[0]) if args else SAMPLE_PATH
    try:
        result = validate_payload_path(target_path)
        summary = build_summary_report()
        validation = build_validation_report(result)
        write_json(SUMMARY_PATH, summary)
        write_json(VALIDATION_PATH, validation)
    except Exception as exc:
        failure_report = {
            "task": TASK_NAME,
            "status": "FAIL",
            "schema_validation_status": "FAIL",
            "policy_validation_status": "FAIL",
            "blocking_error_count": 1,
            "promotion_violation_count": 0,
            "query_policy_violation_count": 0,
            "unknown_warning_family_count": 0,
            "full_artifact_touched": False,
            "failure_reason": str(exc),
        }
        write_json(VALIDATION_PATH, failure_report)
        print(f"RAZ reading authority intake query index validation: FAIL - {exc}")
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
