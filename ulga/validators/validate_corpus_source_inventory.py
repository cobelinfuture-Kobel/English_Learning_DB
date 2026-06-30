import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

INVENTORY_PATH = BASE_DIR / "ulga" / "graph" / "corpus_source_inventory.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "corpus_source_inventory_summary.json"

ALLOWED_SOURCE_ROLES = {
    "authority_source",
    "normalized_authority_artifact",
    "external_reference_corpus",
    "experimental_pilot_output",
    "future_candidate_corpus",
    "blocked_or_missing_source",
}
ALLOWED_STATUSES = {
    "present",
    "present_with_warnings",
    "missing",
    "blocked",
    "deprecated",
    "future_candidate",
}
REQUIRED_FIELDS = {
    "source_id",
    "source_family",
    "source_role",
    "status",
    "path",
    "format",
    "exists",
    "direct_use_allowed",
    "authority_import_allowed",
    "content_extraction_allowed",
    "learner_facing_allowed",
    "license_status",
    "review_status",
    "notes",
    "risk_flags",
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_record(record, seen_ids):
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        return fail(f"{record.get('source_id', 'unknown')} missing required fields: {sorted(missing)}")
    source_id = record["source_id"]
    if source_id in seen_ids:
        return fail(f"duplicate source_id: {source_id}")
    seen_ids.add(source_id)

    if record["source_role"] not in ALLOWED_SOURCE_ROLES:
        return fail(f"{source_id} has invalid source_role: {record['source_role']}")
    if record["status"] not in ALLOWED_STATUSES:
        return fail(f"{source_id} has invalid status: {record['status']}")
    if not isinstance(record["exists"], bool):
        return fail(f"{source_id} exists must be boolean")
    for key in [
        "direct_use_allowed",
        "authority_import_allowed",
        "content_extraction_allowed",
        "learner_facing_allowed",
    ]:
        if not isinstance(record[key], bool):
            return fail(f"{source_id} {key} must be boolean")
    if not isinstance(record["notes"], list) or not all(isinstance(item, str) for item in record["notes"]):
        return fail(f"{source_id} notes must be a list of strings")
    if not isinstance(record["risk_flags"], list) or not all(isinstance(item, str) for item in record["risk_flags"]):
        return fail(f"{source_id} risk_flags must be a list of strings")

    path_text = record["path"]
    path = BASE_DIR / path_text if path_text and not path_text.startswith("future_candidate/") else None

    if record["status"] == "missing" and record["exists"] is not False:
        return fail(f"{source_id} missing status must have exists=false")
    if record["status"] in {"present", "present_with_warnings"} and record["exists"] is not True:
        return fail(f"{source_id} present status must have exists=true")
    if path is not None and path.exists() != record["exists"]:
        return fail(f"{source_id} exists flag does not match filesystem")

    if record["source_role"] == "external_reference_corpus" and record["authority_import_allowed"] is True:
        return fail(f"{source_id} external_reference_corpus cannot allow authority import")
    if record["source_role"] == "experimental_pilot_output" and record["authority_import_allowed"] is True:
        return fail(f"{source_id} experimental_pilot_output cannot allow authority import")
    if record["source_role"] == "blocked_or_missing_source" and record["direct_use_allowed"] is True:
        return fail(f"{source_id} blocked_or_missing_source cannot allow direct use")
    if source_id.startswith("RAZ_") and "PDF_REFERENCE_CORPUS" in source_id and record["learner_facing_allowed"] is True:
        return fail(f"{source_id} RAZ PDF corpus cannot be learner-facing")
    if record["source_role"] == "future_candidate_corpus" and record["authority_import_allowed"] is True:
        return fail(f"{source_id} future_candidate_corpus cannot allow authority import")
    if source_id == "RAZ_A_BOOKS_MANIFEST_XLSX" and record["authority_import_allowed"] is True:
        return fail("manifest-only authority must not be marked as content authority")
    if source_id.startswith("generated_") and record["learner_facing_allowed"] is True:
        return fail(f"{source_id} generated candidate corpus cannot be learner-facing")

    if source_id in {
        "RAZ_B_PDF_REFERENCE_CORPUS",
        "RAZ_C_PDF_REFERENCE_CORPUS",
        "RAZ_D_PDF_REFERENCE_CORPUS",
        "RAZ_E_PDF_REFERENCE_CORPUS",
        "RAZ_F_PDF_REFERENCE_CORPUS",
    }:
        pdf_count = len(list(path.glob("*.pdf"))) if path is not None and path.exists() else 0
        if pdf_count == 0 and record["status"] == "present":
            return fail(f"{source_id} cannot be present without PDF files")
    return True


def validate_summary(records, summary):
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    if summary.get("total_sources") != len(records):
        return fail("summary total_sources does not match inventory length")

    counts_by_source_role = Counter(record["source_role"] for record in records)
    counts_by_status = Counter(record["status"] for record in records)
    if summary.get("counts_by_source_role") != dict(sorted(counts_by_source_role.items())):
        return fail("summary counts_by_source_role does not match inventory")
    if summary.get("counts_by_status") != dict(sorted(counts_by_status.items())):
        return fail("summary counts_by_status does not match inventory")

    expected_present = [record["source_id"] for record in records if record["status"] in {"present", "present_with_warnings"}]
    expected_missing = [record["source_id"] for record in records if record["status"] == "missing"]
    expected_blocked = [record["source_id"] for record in records if record["status"] == "blocked"]
    expected_future = [record["source_id"] for record in records if record["status"] == "future_candidate"]
    if summary.get("present_sources") != expected_present:
        return fail("summary present_sources does not match inventory")
    if summary.get("missing_sources") != expected_missing:
        return fail("summary missing_sources does not match inventory")
    if summary.get("blocked_sources") != expected_blocked:
        return fail("summary blocked_sources does not match inventory")
    if summary.get("future_candidate_sources") != expected_future:
        return fail("summary future_candidate_sources does not match inventory")

    expected_risks = {
        record["source_id"]: record["risk_flags"]
        for record in records
        if record["risk_flags"]
    }
    if summary.get("risk_flags_by_source") != expected_risks:
        return fail("summary risk_flags_by_source does not match inventory")

    expected_raz_status = {
        record["source_id"]: {
            "status": record["status"],
            "exists": record["exists"],
            "notes": record["notes"],
        }
        for record in records
        if record["source_family"] == "raz_pdf_reference_corpus"
    }
    if summary.get("raz_pdf_folder_status") != expected_raz_status:
        return fail("summary raz_pdf_folder_status does not match inventory")

    expected_authority_sources = [
        record["source_id"]
        for record in records
        if record["source_role"] == "authority_source" and record["status"] in {"present", "present_with_warnings"}
    ]
    expected_external_reference = [
        record["source_id"]
        for record in records
        if record["source_role"] == "external_reference_corpus" and record["status"] in {"present", "present_with_warnings"}
    ]
    if summary.get("authority_sources_present") != expected_authority_sources:
        return fail("summary authority_sources_present does not match inventory")
    if summary.get("external_reference_corpora_present") != expected_external_reference:
        return fail("summary external_reference_corpora_present does not match inventory")
    if summary.get("validation_status") not in {"PASS", "PASS_WITH_WARNINGS"}:
        return fail("summary validation_status must be PASS or PASS_WITH_WARNINGS")
    return True


def validate():
    print("Validating Corpus Source Inventory...")
    if not INVENTORY_PATH.exists():
        return fail(f"required file does not exist: {INVENTORY_PATH}")
    if not SUMMARY_PATH.exists():
        return fail(f"required file does not exist: {SUMMARY_PATH}")

    records = read_json(INVENTORY_PATH)
    summary = read_json(SUMMARY_PATH)
    if records is None or summary is None:
        return False
    if not isinstance(records, list):
        return fail("inventory must contain a list")

    seen_ids = set()
    for record in records:
        if not isinstance(record, dict):
            return fail("inventory records must be objects")
        if not validate_record(record, seen_ids):
            return False
    if not validate_summary(records, summary):
        return False

    print("Corpus Source Inventory validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
