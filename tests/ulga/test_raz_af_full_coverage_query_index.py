from __future__ import annotations

import copy
import json

import pytest

from ulga.builders import build_raz_af_full_coverage_query_index as s12c_builder
from ulga.builders import build_raz_af_full_language_pedagogy_observations as s12b_builder
from ulga.validators import validate_raz_af_full_coverage_query_index as s12c_validator


def _source(text: str = "There is a bank in front of the bank. Then, we can go.") -> dict:
    return {
        "page_unit_id": "RAZ_A_1_P001", "book_id": "1", "level": "A", "page_number": 1,
        "text": text, "sentence_count": len(s12b_builder.sentence_spans(text)),
        "authority_status": "candidate_only", "promotion_status": "not_promoted",
        "reuse_tags": {"reusability_tags": ["picture_prompt_seed"]},
    }


def _identity(row: dict) -> dict:
    content_hash, record_hash = s12b_builder.source_hashes(row)
    return {
        "observational_record_id": "RAZ_AF_OBS_V1__RAZ_A_1_P001", "source_unit_ref": row["page_unit_id"],
        "source_level": "A", "source_book_id": "1", "source_page_number": 1,
        "source_record_sha256": record_hash, "source_content_sha256": content_hash,
        "source_role": "observational_reference", "authority_import_allowed": False,
        "learner_facing_original_text_allowed": False, "promotion_status": "not_promoted",
    }


def _authorities() -> dict:
    vocab = {}
    for word in ("there", "is", "a", "in", "front", "of", "the", "then", "we", "can", "go"):
        vocab[word] = [{"id": f"vocabulary:{word}:v_1", "cefr_level": "A1", "metadata": {"part_of_speech": "word"}}]
    vocab["bank"] = [
        {"id": "vocabulary:bank:v_1", "cefr_level": "A1", "metadata": {"part_of_speech": "noun"}},
        {"id": "vocabulary:bank:v_2", "cefr_level": "B1", "metadata": {"part_of_speech": "noun"}},
    ]
    return {
        "snapshots": ["fixture/authority.json#" + "1" * 64],
        "availability": {
            "evp_vocabulary": "AVAILABLE", "evp_chunks": "AVAILABLE", "chunk_equivalence": "AVAILABLE",
            "chunk_usage_class": "AVAILABLE", "generator_safe_chunks": "AVAILABLE", "grammar_query": "AVAILABLE",
            "pattern_query": "AVAILABLE", "theme_situation": "UNAVAILABLE",
        },
        "vocab_index": vocab,
        "chunk_index": {("in", "front", "of"): [{"id": "EVP_CHUNK_000001", "level": "A1"}]},
        "group_by_chunk": {}, "safe_by_chunk": {"EVP_CHUNK_000001": {"safe_id": "SAFE_CHUNK_000001"}},
        "usage": {"EVP_CHUNK_000001": {"usage_class": "prepositional_phrase"}},
        "pattern_skeletons": [({"there", "is"}, {"id": "pattern:PATTERN_NODE_000001"})],
        "grammar_ids": {"GRAMMAR_THERE_IS", "GRAMMAR_CAN_STATEMENT", "GRAMMAR_BE_VERB_BASIC"},
    }


def _bundle():
    row = _source()
    identity = _identity(row)
    identity_inventory = {"records": [identity]}
    records, _inventory, s12b_safe = s12b_builder.build_extraction(
        identity_inventory, {identity["source_unit_ref"]: row}, _authorities(), enforce_expected_counts=False
    )
    query, coverage = s12c_builder.build_artifacts(
        records, s12b_safe["records_sha256"], s12b_safe["authority_snapshot_refs"]
    )
    return records, s12b_safe, query, coverage


def test_query_index_has_all_surfaces_once_and_hashes_observed_vocabulary():
    records, _safe, query, _coverage = _bundle()
    assert set(query["indexes"]) == set(s12c_builder.INDEX_SURFACES)
    assert query["record_count"] == 1
    assert query["record_index"] == [{
        "source_unit_ref": "RAZ_A_1_P001",
        "enrichment_payload_sha256": records[0]["identity"]["enrichment_payload_sha256"],
    }]
    normalized_buckets = query["indexes"]["vocabulary_normalized_forms"]
    assert normalized_buckets
    assert all(bucket["key"].startswith("sha256:") and len(bucket["key"]) == 71 for bucket in normalized_buckets)
    serialized = json.dumps(query)
    assert '"bank"' not in serialized
    assert "There is a bank" not in serialized


def test_query_and_coverage_schemas_are_draft_2020_12_valid():
    _records, _safe, query, coverage = _bundle()
    query_validator, coverage_validator = s12c_builder.schema_validators()
    assert list(query_validator.iter_errors(query)) == []
    assert list(coverage_validator.iter_errors(coverage)) == []


def test_coverage_is_derived_from_records_and_reports_all_four_skills():
    records, _safe, _query, coverage = _bundle()
    expected = s12c_builder.derive_coverage(records)
    assert coverage["coverage"] == expected
    assert set(coverage["coverage"]["skill_templates"]) == {"listening", "speaking", "reading", "writing"}
    assert coverage["level_counts"] == {"A": 1, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    assert coverage["coverage"]["records_with_semantic_import"] == 0


def test_independent_validator_accepts_fixture_and_deterministic_rebuild():
    first = _bundle()
    second = _bundle()
    assert first == second
    records, safe, query, coverage = first
    report = s12c_validator.validate_artifacts(
        records, safe, query, coverage, enforce_expected_counts=False, authorities=_authorities()
    )
    assert report == {"task_id": s12c_builder.TASK_ID, "validation_status": s12c_builder.PASS_STATUS, "error_count": 0, "errors": []}


@pytest.mark.parametrize(
    "mutate,marker",
    [
        (lambda query, coverage: query["record_index"].clear(), "record_index_mismatch"),
        (lambda query, coverage: query["record_index"].append(copy.deepcopy(query["record_index"][0])), "record_index_mismatch"),
        (lambda query, coverage: query["indexes"]["source_unit_refs"][0]["source_unit_refs"].append("RAZ_A_999_P001"), "index_ref_not_in_s12b"),
        (lambda query, coverage: coverage["coverage"].update(records_with_semantic_import=1), "coverage_accounting_drift"),
        (lambda query, coverage: query.update(index_sha256="0" * 64), "query_index_sha256_mismatch"),
    ],
)
def test_validator_rejects_missing_duplicate_extra_refs_counter_and_hash_tampering(mutate, marker):
    records, safe, query, coverage = _bundle()
    mutate(query, coverage)
    report = s12c_validator.validate_artifacts(
        records, safe, query, coverage, enforce_expected_counts=False, authorities=_authorities()
    )
    assert report["validation_status"] == "FAIL"
    assert any(marker in error for error in report["errors"])


def test_validator_rejects_source_text_payload_and_learner_facing_fields():
    records, safe, query, coverage = _bundle()
    for target, field in ((query, "source_text"), (coverage, "source_payload"), (query, "learner_facing_text")):
        tampered_query, tampered_coverage = copy.deepcopy(query), copy.deepcopy(coverage)
        tampered_target = tampered_query if target is query else tampered_coverage
        tampered_target[field] = "forbidden prose"
        report = s12c_validator.validate_artifacts(
            records, safe, tampered_query, tampered_coverage,
            enforce_expected_counts=False, authorities=_authorities(),
        )
        assert any("safe_output_forbidden_key" in error or "Additional properties" in error for error in report["errors"])


def test_validator_rejects_raw_vocabulary_key_and_invalid_authority_ref():
    records, safe, query, coverage = _bundle()
    query["indexes"]["vocabulary_normalized_forms"][0]["key"] = "observed word"
    report = s12c_validator.validate_artifacts(
        records, safe, query, coverage, enforce_expected_counts=False, authorities=_authorities()
    )
    assert any("unsafe_or_invalid_index_key" in error for error in report["errors"])
    records, safe, query, coverage = _bundle()
    records[0]["observations"]["vocabulary_exposure"]["items"][0]["evp_candidate_refs"][0] = "vocabulary:missing:v_999"
    report = s12c_validator.validate_artifacts(
        records, safe, query, coverage, enforce_expected_counts=False, authorities=_authorities()
    )
    assert any("invalid_evp_candidate_ref" in error for error in report["errors"])


def test_private_s12b_hash_snapshot_detects_mutation(tmp_path):
    root = tmp_path / "s12b"
    path = root / "records/Level_A/RAZ_A_1_P001.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    inventory = {"records": [{"path": "records/Level_A/RAZ_A_1_P001.json"}]}
    before = s12c_builder._private_file_hashes(root, inventory)
    path.write_text('{"changed":true}', encoding="utf-8")
    after = s12c_builder._private_file_hashes(root, inventory)
    assert before != after
