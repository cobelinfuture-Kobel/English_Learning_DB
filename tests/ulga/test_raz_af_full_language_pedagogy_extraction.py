from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ulga.builders import build_raz_af_full_language_pedagogy_observations as builder
from ulga.validators import validate_raz_af_full_language_pedagogy_observations as validator


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source(text: str = "There is a bank in front of the bank. Then, we can go.") -> dict:
    return {
        "page_unit_id": "RAZ_A_1_P001", "book_id": "1", "level": "A", "page_number": 1,
        "text": text, "sentence_count": len(builder.sentence_spans(text)),
        "authority_status": "candidate_only", "promotion_status": "not_promoted",
        "reuse_tags": {"reusability_tags": ["picture_prompt_seed"]},
    }


def _identity(row: dict) -> dict:
    content_hash, record_hash = builder.source_hashes(row)
    return {
        "observational_record_id": "RAZ_AF_OBS_V1__RAZ_A_1_P001", "source_unit_ref": "RAZ_A_1_P001",
        "source_level": "A", "source_book_id": "1", "source_page_number": 1,
        "source_record_sha256": record_hash, "source_content_sha256": content_hash,
        "enrichment_schema_version": "raz.af.observational_companion.v1",
        "extractor_version": "raz-af-observational-source-integrity-adapter.v1", "authority_snapshot_refs": [],
        "enrichment_payload_sha256": _sha("{}"), "source_role": "observational_reference",
        "authority_import_allowed": False, "learner_facing_original_text_allowed": False, "promotion_status": "not_promoted",
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
        "snapshots": ["fixture/authority.json#" + "1" * 64], "vocab_index": vocab,
        "chunk_index": {
            ("in", "front"): [{"id": "EVP_CHUNK_SHORT", "level": "A1"}],
            ("in", "front", "of"): [{"id": "EVP_CHUNK_EQ", "level": "A2"}],
        },
        "group_by_chunk": {"EVP_CHUNK_EQ": {"group_id": "CHUNK_EQ_1", "canonical_id": "EVP_CHUNK_LONG"}},
        "safe_by_chunk": {"EVP_CHUNK_LONG": {"safe_id": "SAFE_CHUNK_1"}},
        "usage": {"EVP_CHUNK_LONG": {"usage_class": "prepositional_phrase"}},
        "pattern_skeletons": [({"there", "is"}, {"id": "pattern:PATTERN_NODE_000001"})],
        "grammar_ids": {"GRAMMAR_THERE_IS", "GRAMMAR_CAN_STATEMENT", "GRAMMAR_BE_VERB_BASIC"},
    }


def _build(text: str | None = None):
    row = _source(text or "There is a bank in front of the bank. Then, we can go.")
    identity = _identity(row)
    record = builder.build_record(identity, row, _authorities())
    return row, identity, record


def _bundle(text: str | None = None):
    row = _source(text or "There is a bank in front of the bank. Then, we can go.")
    identity = _identity(row)
    identities = {"task_id": "fixture", "records": [identity]}
    records, inventory, safe = builder.build_extraction(identities, {identity["source_unit_ref"]: row}, _authorities(), enforce_expected_counts=False)
    inventory["records"] = [dict(inventory["records"][0], path="records/Level_A/RAZ_A_1_P001.json")]
    return identities, {identity["source_unit_ref"]: row}, records, inventory, safe


def test_exact_s12a_join_source_hash_preservation_and_closed_record_schema():
    row, identity, record = _build()
    assert record["identity"]["source_unit_ref"] == identity["source_unit_ref"]
    assert record["identity"]["source_content_sha256"] == builder.source_hashes(row)[0]
    record_validator, _safe, _semantic = builder.schema_validators()
    assert list(record_validator.iter_errors(record)) == []
    invalid = copy.deepcopy(record)
    invalid["unexpected"] = True
    assert list(record_validator.iter_errors(invalid))


def test_vocabulary_normalization_and_ambiguous_evp_senses_remain_ambiguous():
    exposure = builder.observe_vocabulary("Bank bank BANK.", _authorities())
    item = exposure["items"][0]
    assert item["normalized_form"] == "bank"
    assert item["occurrence_count"] == 3
    assert item["match_status"] == "EXACT_FORM_MULTIPLE_SENSES"
    assert item["evp_level_candidates"] == ["A1", "B1"]
    assert item["sense_ambiguity_status"] == "MULTIPLE_SENSES"


def test_longest_chunk_match_preserves_equivalent_canonical_safe_and_usage_mapping():
    chunks = builder.observe_chunks("We stand in front of it.", _authorities())["items"]
    assert len(chunks) == 1
    assert chunks[0]["normalized_form"] == "in front of"
    assert chunks[0]["match_status"] == "EQUIVALENT_CHUNK_MATCH"
    assert chunks[0]["canonical_chunk_id"] == "EVP_CHUNK_LONG"
    assert chunks[0]["equivalence_group_id"] == "CHUNK_EQ_1"
    assert chunks[0]["safe_chunk_id"] == "SAFE_CHUNK_1"
    assert chunks[0]["usage_class"] == "prepositional_phrase"


def test_unmatched_recurring_chunk_stays_candidate_only():
    chunks = builder.observe_chunks("Blue moon, blue moon.", _authorities())["items"]
    recurring = next(item for item in chunks if item["normalized_form"] == "blue moon")
    assert recurring["match_status"] == "RECURRING_OBSERVED_CHUNK_CANDIDATE"
    assert recurring["canonical_chunk_id"] is None
    assert recurring["safe_chunk_id"] is None


def test_pattern_abstraction_never_copies_sentence_and_maps_grammar_candidate():
    source = "There is a cat in the house."
    patterns = builder.observe_patterns(source, _authorities())["items"]
    assert patterns[0]["abstract_pattern"] != source
    assert "{THING}" in patterns[0]["abstract_pattern"]
    assert "GRAMMAR_THERE_IS" in patterns[0]["grammar_candidate_refs"]
    assert patterns[0]["mapping_status"] == "EXACT_CANONICAL_PATTERN_CANDIDATE"


@pytest.mark.parametrize(
    "text,shape",
    [
        ("First we mix. Then we bake.", "sequence"),
        ("Where is it? It is here.", "question_answer"),
        ("I see a cat. I see a dog.", "repeated_description"),
    ],
)
def test_discourse_structural_detection(text, shape):
    assert builder.observe_discourse(text)["discourse_shape"] == shape


def test_unknown_semantic_classification_and_four_skill_layers_are_explicit():
    _row, _identity, record = _build("Quartz glimmers softly.")
    observations = record["observations"]
    assert observations["situation_function_observations"]["classification_status"] == "UNKNOWN_REQUIRES_REVIEW"
    affordances = observations["four_skill_affordances"]
    assert set(affordances) == {"language_templates", "discourse_templates", "skill_activity_templates", "scaffolding_templates"}
    assert set(affordances["skill_activity_templates"]) == {"listening", "speaking", "reading", "writing"}
    assert all(candidate["authority_status"] == "observational_candidate" for candidates in affordances["skill_activity_templates"].values() for candidate in candidates)


def test_semantic_import_closed_schema_identity_hash_and_reasoning_rejection(tmp_path):
    row = _source()
    identity = _identity(row)
    semantic_validator = builder.schema_validators()[2]
    valid = {
        "source_unit_ref": identity["source_unit_ref"], "source_record_sha256": identity["source_record_sha256"],
        "source_content_sha256": identity["source_content_sha256"], "annotation_version": "raz.af.observational_semantic_annotation.v1",
        "confidence": 0.8, "review_status": "HUMAN_REVIEWED", "annotations": {"micro_situation_candidates": ["at_home"]},
    }
    path = tmp_path / "valid.json"
    path.write_text(json.dumps(valid), encoding="utf-8")
    loaded = builder.load_semantic_imports(tmp_path, {identity["source_unit_ref"]: identity}, semantic_validator)
    assert loaded[identity["source_unit_ref"]] == valid
    invalid = copy.deepcopy(valid)
    invalid["source_record_sha256"] = "0" * 64
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(builder.ExtractionError, match="identity_or_hash_mismatch"):
        builder.load_semantic_imports(tmp_path, {identity["source_unit_ref"]: identity}, semantic_validator)
    invalid = copy.deepcopy(valid)
    invalid["chain_of_thought"] = "forbidden"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(builder.ExtractionError, match="semantic_import"):
        builder.load_semantic_imports(tmp_path, {identity["source_unit_ref"]: identity}, semantic_validator)


def test_semantic_import_applies_without_changing_identity_or_hashes():
    row = _source()
    identity = _identity(row)
    annotation = {
        "source_unit_ref": identity["source_unit_ref"], "source_record_sha256": identity["source_record_sha256"],
        "source_content_sha256": identity["source_content_sha256"], "annotation_version": "raz.af.observational_semantic_annotation.v1",
        "confidence": 0.9, "review_status": "HUMAN_REVIEWED", "annotations": {"micro_situation_candidates": ["near_a_bank"], "communicative_function_candidates": ["describing_location"]},
    }
    record = builder.build_record(identity, row, _authorities(), annotation)
    assert record["identity"]["source_record_sha256"] == identity["source_record_sha256"]
    assert record["observations"]["quality_and_review"]["semantic_pass_status"] == "APPLIED"
    assert record["observations"]["situation_function_observations"]["classification_status"] == "MODEL_ASSISTED_CANDIDATE"


def test_validator_rejects_payload_hash_tampering_duplicate_missing_and_promotion(monkeypatch):
    identities, sources, records, inventory, safe = _bundle()
    monkeypatch.setattr(validator, "load_authorities", lambda: _authorities())
    assert validator.validate_extraction(identities, sources, records, inventory, safe, enforce_expected_counts=False)["validation_status"] == builder.PASS_STATUS
    tampered = copy.deepcopy(records)
    tampered[0]["observations"]["quality_and_review"]["semantic_review_required"] = False
    report = validator.validate_extraction(identities, sources, tampered, inventory, safe, enforce_expected_counts=False)
    assert any("payload_hash_mismatch" in error for error in report["errors"])
    duplicated = records + [copy.deepcopy(records[0])]
    report = validator.validate_extraction(identities, sources, duplicated, inventory, safe, enforce_expected_counts=False)
    assert any("duplicate_enrichment_record" in error for error in report["errors"])
    promoted = copy.deepcopy(records)
    promoted[0]["identity"]["promotion_status"] = "promoted"
    report = validator.validate_extraction(identities, sources, promoted, inventory, safe, enforce_expected_counts=False)
    assert any("canonical_promotion_claim" in error or "promotion_status" in error for error in report["errors"])
    report = validator.validate_extraction(identities, sources, [], {**inventory, "records": []}, safe, enforce_expected_counts=False)
    assert any("missing_enrichment_record" in error for error in report["errors"])


def test_safe_report_rejects_source_text_token_chunk_and_payload_fields(monkeypatch):
    identities, sources, records, inventory, safe = _bundle()
    monkeypatch.setattr(validator, "load_authorities", lambda: _authorities())
    for field in ("source_text", "source_tokens", "observed_chunks", "source_payload"):
        unsafe = copy.deepcopy(safe)
        unsafe[field] = "forbidden"
        report = validator.validate_extraction(identities, sources, records, inventory, unsafe, enforce_expected_counts=False)
        assert report["validation_status"] == "FAIL"
        assert any("safe_output_forbidden" in error or "Additional properties" in error for error in report["errors"])


def test_private_record_loader_rejects_unlisted_extra_record(tmp_path):
    output_root = tmp_path / "output"
    listed = output_root / "records/Level_A/RAZ_A_1_P001.json"
    extra = output_root / "records/Level_A/RAZ_A_2_P001.json"
    listed.parent.mkdir(parents=True)
    listed.write_text("{}", encoding="utf-8")
    extra.write_text("{}", encoding="utf-8")
    records, errors = validator.load_private_records(output_root, {"records": [{"path": "records/Level_A/RAZ_A_1_P001.json"}]})
    assert records == [{}]
    assert any("extra_unlisted_enrichment_record" in error for error in errors)


def test_deterministic_rebuild():
    first = _bundle()
    second = _bundle()
    assert first == second


def test_source_mutation_file_hash_detection(tmp_path):
    root = tmp_path / "raz"
    for level in "ABCDEF":
        path = root / "derived" / f"Level_{level}" / "enriched" / f"raz_{level}_page_unit_enriched.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        row = _source(f"Fixture {level}.")
        row.update(page_unit_id=f"RAZ_{level}_{ord(level)}_P001", book_id=str(ord(level)), level=level)
        path.write_text(json.dumps([row]), encoding="utf-8")
    _rows, before = builder.load_source_rows(root)
    target = root / "derived/Level_A/enriched/raz_A_page_unit_enriched.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload[0]["text"] = "Mutated."
    target.write_text(json.dumps(payload), encoding="utf-8")
    _rows, after = builder.load_source_rows(root)
    assert before != after


def test_real_4925_record_local_smoke_and_m04_compatibility():
    root = builder.REPO_ROOT
    identity_path = root / ".local/raz_af/observational_companion_identity_inventory.json"
    source_root = root / "raz_output_jsons"
    if not identity_path.is_file() or not source_root.is_dir():
        pytest.skip("private local RAZ corpus unavailable")
    identities = builder.read_json(identity_path)
    sources, _hashes = builder.load_source_rows(source_root)
    assert len(identities["records"]) == 4925
    assert len(sources) == 4925
    assert len({row["book_id"] for row in sources.values()}) == 566
    safe_index = builder.read_json(root / ".local/raz_af/observational_companion_safe_index.json")
    assert safe_index["consumer_compatibility"] == [{
        "consumer_id": builder.CURRENT_CONSUMER_ID, "source_ref_count": 54,
        "resolvable_source_ref_count": 54, "unresolved_source_ref_count": 0,
    }]
