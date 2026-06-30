import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_corpus_source_inventory.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_corpus_source_inventory.py"
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


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def get_record(records, source_id):
    return next(record for record in records if record["source_id"] == source_id)


def test_builder_can_run():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert INVENTORY_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_inventory_json_exists_and_parses():
    records = load_json(INVENTORY_PATH)
    assert isinstance(records, list)
    assert records


def test_all_records_contain_required_fields():
    records = load_json(INVENTORY_PATH)
    for record in records:
        assert REQUIRED_FIELDS <= set(record)


def test_source_role_enum_validity():
    records = load_json(INVENTORY_PATH)
    for record in records:
        assert record["source_role"] in ALLOWED_SOURCE_ROLES


def test_status_enum_validity():
    records = load_json(INVENTORY_PATH)
    for record in records:
        assert record["status"] in ALLOWED_STATUSES


def test_external_reference_corpus_cannot_import_authority():
    records = load_json(INVENTORY_PATH)
    for record in records:
        if record["source_role"] == "external_reference_corpus":
            assert record["authority_import_allowed"] is False


def test_experimental_pilot_output_cannot_import_authority():
    records = load_json(INVENTORY_PATH)
    for record in records:
        if record["source_role"] == "experimental_pilot_output":
            assert record["authority_import_allowed"] is False


def test_raz_b_to_f_cannot_be_present_without_pdfs():
    records = load_json(INVENTORY_PATH)
    for source_id in [
        "RAZ_B_PDF_REFERENCE_CORPUS",
        "RAZ_C_PDF_REFERENCE_CORPUS",
        "RAZ_D_PDF_REFERENCE_CORPUS",
        "RAZ_E_PDF_REFERENCE_CORPUS",
        "RAZ_F_PDF_REFERENCE_CORPUS",
    ]:
        record = get_record(records, source_id)
        path = BASE_DIR / record["path"]
        pdf_count = len(list(path.glob("*.pdf"))) if path.exists() else 0
        if pdf_count == 0:
            assert record["status"] != "present"


def test_raz_a_folder_handling_matches_filesystem():
    records = load_json(INVENTORY_PATH)
    record = get_record(records, "RAZ_A_PDF_REFERENCE_CORPUS")
    path = BASE_DIR / record["path"]
    pdf_count = len(list(path.glob("*.pdf"))) if path.exists() else 0
    assert record["exists"] == path.exists()
    if pdf_count > 0:
        assert record["status"] in {"present", "present_with_warnings"}
    else:
        assert record["status"] in {"blocked", "missing"}


def test_future_candidate_records_are_non_promotable():
    records = load_json(INVENTORY_PATH)
    future_records = [record for record in records if record["source_role"] == "future_candidate_corpus"]
    assert future_records
    for record in future_records:
        assert record["status"] == "future_candidate"
        assert record["authority_import_allowed"] is False
        assert record["learner_facing_allowed"] is False
        assert record["direct_use_allowed"] is False


def test_summary_counts_match_inventory_records():
    records = load_json(INVENTORY_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["total_sources"] == len(records)
    assert len(summary["present_sources"]) == sum(
        1 for record in records if record["status"] in {"present", "present_with_warnings"}
    )
    assert len(summary["missing_sources"]) == sum(1 for record in records if record["status"] == "missing")
    assert len(summary["blocked_sources"]) == sum(1 for record in records if record["status"] == "blocked")
    assert len(summary["future_candidate_sources"]) == sum(
        1 for record in records if record["status"] == "future_candidate"
    )
