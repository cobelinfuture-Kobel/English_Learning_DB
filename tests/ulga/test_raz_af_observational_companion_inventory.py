from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders import build_raz_af_observational_companion_inventory as adapter
from ulga.builders.build_a1_a1plus_local_reading_practice_bank import _canonical_json
from ulga.builders.build_raz_af_observational_companion_inventory import (
    CURRENT_CONSUMER_ID,
    EMPTY_ENRICHMENT_PAYLOAD_SHA256,
    InventoryBuildError,
    PASS_STATUS,
    build_inventory,
)
from ulga.validators.validate_raz_af_observational_companion_safe_report import validate_safe_index

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source(ref: str, level: str, book: str, page: int, text: str) -> dict:
    return {
        "page_unit_id": ref,
        "book_id": book,
        "level": level,
        "page_number": page,
        "text": text,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }


def _write_corpus(root: Path, rows_by_level: dict[str, list[dict]]) -> None:
    for level in "ABCDEF":
        path = root / "derived" / f"Level_{level}" / "enriched" / f"raz_{level}_page_unit_enriched.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows_by_level.get(level, [])), encoding="utf-8")


def _fixture_corpus(tmp_path: Path) -> tuple[Path, list[dict]]:
    root = tmp_path / "raz_output_jsons"
    rows = {
        level: [_source(f"RAZ_{level}_{index}_P001", level, str(index), 1, f"Fixture {level} {index}.")]
        for index, level in enumerate("ABCDEF", start=1)
    }
    _write_corpus(root, rows)
    selected = [{"source_unit_ref": rows[level][0]["page_unit_id"]} for level in "ABCDEF"]
    return root, selected


def _consumer_refs(selected: list[dict]) -> dict[str, list[str]]:
    return {CURRENT_CONSUMER_ID: [row["source_unit_ref"] for row in selected]}


def _fixture_safe(tmp_path: Path) -> tuple[Path, dict]:
    root, selected = _fixture_corpus(tmp_path)
    _, safe = build_inventory(
        root,
        consumer_source_refs=_consumer_refs(selected),
        enforce_expected_counts=False,
    )
    return root, safe


def _validate_fixture(safe: dict) -> dict:
    return validate_safe_index(
        safe,
        expected_page_unit_count=6,
        expected_book_count=6,
        expected_levels=tuple("ABCDEF"),
        expected_current_consumer_counts=(6, 6, 0),
    )


def _refresh_records_hash(safe: dict) -> None:
    safe["records_sha256"] = _sha(_canonical_json(safe["records"]))


def test_closed_identity_schema_accepts_builder_record_and_rejects_extra_field(tmp_path):
    root, selected = _fixture_corpus(tmp_path)
    inventory, _ = build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)
    schema = json.loads(
        (REPO_ROOT / "ulga/schemas/raz_af_observational_companion_identity_record.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    record = inventory["records"][0]
    assert list(validator.iter_errors(record)) == []
    mutated = dict(record, unexpected=True)
    assert list(validator.iter_errors(mutated))


def test_builder_preserves_m04b2_hashes_and_is_deterministic(tmp_path):
    root, selected = _fixture_corpus(tmp_path)
    first_inventory, first_safe = build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)
    second_inventory, second_safe = build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)
    assert first_inventory == second_inventory
    assert first_safe == second_safe
    source = json.loads(
        (root / "derived/Level_A/enriched/raz_A_page_unit_enriched.json").read_text()
    )[0]
    record = first_inventory["records"][0]
    assert record["source_content_sha256"] == _sha(source["text"].strip())
    assert record["source_record_sha256"] == _sha(_canonical_json(source))
    assert record["enrichment_payload_sha256"] == EMPTY_ENRICHMENT_PAYLOAD_SHA256
    assert record["authority_snapshot_refs"] == []


def test_contract_and_index_are_cefr_stage_neutral_for_future_consumers(tmp_path):
    for name in (
        "raz_af_observational_companion_identity_record.schema.json",
        "raz_af_observational_companion_safe_index.schema.json",
    ):
        schema_text = (REPO_ROOT / "ulga/schemas" / name).read_text(encoding="utf-8").casefold()
        assert "cefr" not in schema_text
        assert "a1/a1+" not in schema_text
    root, _ = _fixture_corpus(tmp_path)
    inventory, safe = build_inventory(
        root,
        consumer_source_refs={
            "FUTURE_A2_A2PLUS_CONSUMER": ["RAZ_A_1_P001"],
            "FUTURE_B1_B1PLUS_CONSUMER": ["RAZ_F_6_P001"],
        },
        enforce_expected_counts=False,
    )
    assert len(inventory["records"]) == 6
    assert safe["consumer_compatibility"] == [
        {
            "consumer_id": "FUTURE_A2_A2PLUS_CONSUMER",
            "source_ref_count": 1,
            "resolvable_source_ref_count": 1,
            "unresolved_source_ref_count": 0,
        },
        {
            "consumer_id": "FUTURE_B1_B1PLUS_CONSUMER",
            "source_ref_count": 1,
            "resolvable_source_ref_count": 1,
            "unresolved_source_ref_count": 0,
        },
    ]


def test_builder_does_not_mutate_source_files(tmp_path):
    root, selected = _fixture_corpus(tmp_path)
    paths = sorted(root.rglob("raz_*_page_unit_enriched.json"))
    before = {path: path.read_bytes() for path in paths}
    _, safe = build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)
    assert {path: path.read_bytes() for path in paths} == before
    assert safe["summary"]["source_record_mutation_count"] == 0
    assert safe["summary"]["source_content_hash_drift_count"] == 0
    assert safe["summary"]["source_record_hash_drift_count"] == 0


def test_duplicate_and_conflicting_source_refs_fail_closed(tmp_path):
    root, selected = _fixture_corpus(tmp_path)
    path = root / "derived/Level_A/enriched/raz_A_page_unit_enriched.json"
    rows = json.loads(path.read_text())
    rows.append(copy.deepcopy(rows[0]))
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(InventoryBuildError, match="duplicate_or_conflicting_source_unit_refs"):
        build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)
    rows[-1]["text"] = "Conflicting content."
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(InventoryBuildError, match="conflicts=1"):
        build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)


@pytest.mark.parametrize("field,value", [("text", ""), ("page_unit_id", ""), ("page_number", None)])
def test_missing_source_identity_or_hash_input_fails_closed(tmp_path, field, value):
    root, selected = _fixture_corpus(tmp_path)
    path = root / "derived/Level_A/enriched/raz_A_page_unit_enriched.json"
    rows = json.loads(path.read_text())
    rows[0][field] = value
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(InventoryBuildError):
        build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)


def test_validator_rejects_malformed_hash_duplicate_and_safe_text(tmp_path):
    root, selected = _fixture_corpus(tmp_path)
    _, safe = build_inventory(root, consumer_source_refs=_consumer_refs(selected), enforce_expected_counts=False)
    # Fixture mode is intentionally below production counts, so patch only count evidence
    # to isolate substantive fail-closed checks in this unit test.
    safe["summary"].update(
        discovered_page_unit_count=4925,
        represented_book_count=566,
    )
    safe["consumer_compatibility"] = [{
        "consumer_id": CURRENT_CONSUMER_ID,
        "source_ref_count": 54,
        "resolvable_source_ref_count": 54,
        "unresolved_source_ref_count": 0,
    }]
    safe["summary"]["page_unit_counts_by_level"] = {level: 0 for level in "ABCDEF"}
    safe["summary"]["page_unit_counts_by_level"]["A"] = len(safe["records"])
    malformed = copy.deepcopy(safe)
    malformed["records"][0]["source_record_sha256"] = "bad"
    malformed["records"].append(copy.deepcopy(malformed["records"][0]))
    malformed["records"][0]["clean_text"] = "must never enter safe output"
    report = validate_safe_index(malformed)
    assert report["validation_status"] == "FAIL"
    assert any("source_record_sha256" in error for error in report["errors"])
    assert any("duplicate_source_unit_ref" in error for error in report["errors"])
    assert any("forbidden_text_key" in error for error in report["errors"])


def test_production_validator_rejects_six_records_forged_as_4925_and_six_books_forged_as_566(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["summary"]["discovered_page_unit_count"] = 4925
    safe["summary"]["represented_book_count"] = 566
    report = validate_safe_index(safe)
    assert report["validation_status"] == "FAIL"
    assert any("actual_record_count:expected=4925:actual=6" in error for error in report["errors"])
    assert any("actual_represented_book_count:expected=566:actual=6" in error for error in report["errors"])
    assert any("summary:discovered_page_unit_count:derived=6:declared=4925" in error for error in report["errors"])
    assert any("summary:represented_book_count:derived=6:declared=566" in error for error in report["errors"])


def test_validator_rejects_forged_per_level_counts(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["summary"]["page_unit_counts_by_level"] = {
        "A": 2, "B": 0, "C": 1, "D": 1, "E": 1, "F": 1,
    }
    report = _validate_fixture(safe)
    assert any("summary:page_unit_counts_by_level" in error for error in report["errors"])


def test_validator_rejects_forged_discovered_levels(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["summary"]["discovered_levels"] = list("ABCDE")
    safe["summary"]["discovered_level_count"] = 5
    report = _validate_fixture(safe)
    assert any("summary:discovered_levels" in error for error in report["errors"])
    assert any("summary:discovered_level_count" in error for error in report["errors"])


def test_validator_requires_current_m04b1_consumer_entry(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["consumer_compatibility"] = []
    report = _validate_fixture(safe)
    assert "current_consumer_entry_count:expected=1:actual=0" in report["errors"]


@pytest.mark.parametrize(
    "counts",
    [
        (53, 53, 0),
        (54, 53, 1),
    ],
)
def test_validator_rejects_wrong_current_consumer_counts(tmp_path, counts):
    _, safe = _fixture_safe(tmp_path)
    current = safe["consumer_compatibility"][0]
    current["source_ref_count"], current["resolvable_source_ref_count"], current["unresolved_source_ref_count"] = counts
    report = validate_safe_index(
        safe,
        expected_page_unit_count=6,
        expected_book_count=6,
        expected_levels=tuple("ABCDEF"),
    )
    assert any("current_consumer_counts:expected=(54, 54, 0)" in error for error in report["errors"])
    if counts[-1]:
        assert any("pass_with_unresolved_sources" in error for error in report["errors"])


def test_validator_rejects_duplicate_current_consumer_entries(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["consumer_compatibility"].append(copy.deepcopy(safe["consumer_compatibility"][0]))
    report = _validate_fixture(safe)
    assert any("duplicate_consumer_id" in error for error in report["errors"])
    assert "current_consumer_entry_count:expected=1:actual=2" in report["errors"]


@pytest.mark.parametrize(
    "target,value,error_fragment",
    [
        ("source_book_id", "This is unrestricted natural language.", "source_book_id"),
        ("authority_snapshot_refs", ["This is unrestricted natural language."], "authority_snapshot_refs"),
    ],
)
def test_validator_rejects_prose_in_identity_metadata(tmp_path, target, value, error_fragment):
    _, safe = _fixture_safe(tmp_path)
    safe["records"][0][target] = value
    _refresh_records_hash(safe)
    report = _validate_fixture(safe)
    assert report["validation_status"] == "FAIL"
    assert any(error_fragment in error for error in report["errors"])


def test_validator_rejects_prose_in_consumer_id(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["consumer_compatibility"][0]["consumer_id"] = "This is unrestricted natural language."
    report = _validate_fixture(safe)
    assert any("consumer_id" in error for error in report["errors"])


@pytest.mark.parametrize(
    "field,value,error_fragment",
    [
        ("source_book_id", "999", "source_unit_ref_book_mismatch"),
        ("source_page_number", 99, "source_unit_ref_page_mismatch"),
    ],
)
def test_validator_rejects_cross_field_source_identity_mismatch(tmp_path, field, value, error_fragment):
    _, safe = _fixture_safe(tmp_path)
    safe["records"][0][field] = value
    _refresh_records_hash(safe)
    report = _validate_fixture(safe)
    assert any(error_fragment in error for error in report["errors"])


@pytest.mark.parametrize(
    "field,value,error_fragment",
    [
        ("book_id", "999", "source_identity_book_mismatch"),
        ("page_number", 99, "source_identity_page_mismatch"),
    ],
)
def test_builder_rejects_cross_field_source_identity_mismatch(tmp_path, field, value, error_fragment):
    root, selected = _fixture_corpus(tmp_path)
    path = root / "derived/Level_A/enriched/raz_A_page_unit_enriched.json"
    rows = json.loads(path.read_text())
    rows[0][field] = value
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(InventoryBuildError, match=error_fragment):
        build_inventory(
            root,
            consumer_source_refs=_consumer_refs(selected),
            enforce_expected_counts=False,
        )


def test_builder_never_returns_schema_invalid_pass_artifact(tmp_path, monkeypatch):
    root, selected = _fixture_corpus(tmp_path)
    original = adapter._build_identity_record

    def invalid_record(source):
        record = original(source)
        record["source_book_id"] = "Natural language is forbidden here."
        return record

    monkeypatch.setattr(adapter, "_build_identity_record", invalid_record)
    with pytest.raises(InventoryBuildError, match="schema_validation_failed"):
        adapter.build_inventory(
            root,
            consumer_source_refs=_consumer_refs(selected),
            enforce_expected_counts=False,
        )


def test_builder_validates_full_safe_index_schema_before_return(tmp_path, monkeypatch):
    root, selected = _fixture_corpus(tmp_path)

    def invalid_compatibility(*_args, **_kwargs):
        return [{
            "consumer_id": "Natural language is forbidden here.",
            "source_ref_count": 6,
            "resolvable_source_ref_count": 6,
            "unresolved_source_ref_count": 0,
        }]

    monkeypatch.setattr(adapter, "_consumer_compatibility", invalid_compatibility)
    with pytest.raises(InventoryBuildError, match="safe_index_schema"):
        adapter.build_inventory(
            root,
            consumer_source_refs=_consumer_refs(selected),
            enforce_expected_counts=False,
        )


def test_validator_rejects_tampered_represented_book_accounting(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["summary"]["represented_book_count"] = 5
    report = _validate_fixture(safe)
    assert any("summary:represented_book_count:derived=6:declared=5" in error for error in report["errors"])


def test_validator_rejects_tampered_records_sha256(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    safe["records_sha256"] = "0" * 64
    report = _validate_fixture(safe)
    assert "records_sha256_mismatch" in report["errors"]


@pytest.mark.parametrize(
    "counter",
    [
        "source_record_mutation_count",
        "source_content_hash_drift_count",
        "source_record_hash_drift_count",
    ],
)
def test_validator_rejects_nonzero_source_drift_counters(tmp_path, counter):
    _, safe = _fixture_safe(tmp_path)
    safe["summary"][counter] = 1
    report = _validate_fixture(safe)
    assert any(f"summary:{counter}:expected=0:actual=1" in error for error in report["errors"])


def test_validator_recomputes_duplicate_and_conflicting_source_ref_counters(tmp_path):
    _, safe = _fixture_safe(tmp_path)
    conflict = copy.deepcopy(safe["records"][0])
    conflict["source_record_sha256"] = "0" * 64
    safe["records"].append(conflict)
    _refresh_records_hash(safe)
    report = validate_safe_index(
        safe,
        expected_page_unit_count=7,
        expected_book_count=6,
        expected_levels=tuple("ABCDEF"),
        expected_current_consumer_counts=(6, 6, 0),
    )
    assert "actual_duplicate_source_unit_ref_count:1" in report["errors"]
    assert "actual_conflicting_source_unit_ref_count:1" in report["errors"]
    assert any("summary:duplicate_source_unit_ref_count:derived=1:declared=0" in error for error in report["errors"])
    assert any("summary:conflicting_source_unit_ref_count:derived=1:declared=0" in error for error in report["errors"])


@pytest.mark.parametrize(
    "field,error_fragment,counter",
    [
        ("clean_text", "safe_output_forbidden_text_key", "source_text_field_count"),
        ("source_payload", "safe_output_forbidden_payload_key", "forbidden_payload_field_count"),
    ],
)
def test_validator_rejects_forbidden_text_and_payload_keys(tmp_path, field, error_fragment, counter):
    _, safe = _fixture_safe(tmp_path)
    safe["records"][0][field] = "forbidden"
    _refresh_records_hash(safe)
    report = _validate_fixture(safe)
    assert any(error_fragment in error for error in report["errors"])
    assert any(f"summary:{counter}:derived=1:declared=0" in error for error in report["errors"])


def test_real_local_corpus_acceptance_counts_and_safe_validator():
    source_root = REPO_ROOT / "raz_output_jsons"
    if not source_root.is_dir():
        pytest.skip("private local RAZ corpus unavailable")
    first_inventory, first_safe = build_inventory(source_root)
    second_inventory, second_safe = build_inventory(source_root)
    assert first_inventory == second_inventory
    assert first_safe == second_safe
    assert first_safe["validation_status"] == PASS_STATUS
    assert first_safe["summary"] == {
        "discovered_level_count": 6,
        "discovered_levels": list("ABCDEF"),
        "discovered_page_unit_count": 4925,
        "represented_book_count": 566,
        "page_unit_counts_by_level": {"A": 804, "B": 802, "C": 808, "D": 735, "E": 904, "F": 872},
        "source_record_mutation_count": 0,
        "source_content_hash_drift_count": 0,
        "source_record_hash_drift_count": 0,
        "duplicate_source_unit_ref_count": 0,
        "conflicting_source_unit_ref_count": 0,
        "source_text_field_count": 0,
        "forbidden_payload_field_count": 0,
    }
    assert first_safe["consumer_compatibility"] == [{
        "consumer_id": CURRENT_CONSUMER_ID,
        "source_ref_count": 54,
        "resolvable_source_ref_count": 54,
        "unresolved_source_ref_count": 0,
    }]
    report = validate_safe_index(first_safe)
    assert report["validation_status"] == PASS_STATUS
    assert report["error_count"] == 0
