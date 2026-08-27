from functools import lru_cache
from collections import Counter

from ulga.builders import (
    build_a1fs_v1_u03q9q10r1_unit03_form_pedagogical_contract_20x40_6_10_10_8_6
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u03q9q10r1_unit03_form_pedagogical_contract_20x40
    as validator,
)


@lru_cache(maxsize=1)
def _payload():
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["validation_status"] == "PASS"
    return approved["payload"]


def test_preserves_historical_authorities_and_creates_new_successor_identity():
    history = _payload()["historical_provenance"]
    assert history["unit03_q10_historical_runtime_count"] == 640
    assert history["unit03_q10_historical_identity_mutated"] is False
    assert history["u03scfv2_historical_runtime_count"] == 800
    assert history["u03scfv2_historical_identity_mutated"] is False
    assert history["successor_runtime_identity_is_new"] is True


def test_q9_keeps_exact_ten_families_and_adds_only_section_and_passage_mappings():
    q9 = _payload()["q9_amendment"]
    assert q9["task_family_count"] == 10
    assert tuple(q9["task_families"]) == builder.Q9_FAMILIES
    assert q9["family_11_created"] is False
    assert q9["section_mapping"] == builder.FAMILY_SECTION_MAPPING
    assert len(q9["connected_passage_question_types"]) == 6
    assert all(row["task_family"] in builder.Q9_FAMILIES for row in q9["connected_passage_question_types"])


def test_materializes_exact_twenty_by_forty_and_6_10_10_8_6_per_form():
    payload = _payload()
    contract = payload["q10_successor_form_contract"]
    assert contract["form_count"] == 20
    assert contract["activities_per_form"] == 40
    assert contract["runtime_occurrence_count"] == 800
    assert contract["section_counts_per_form"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
    items, runtime = payload["successor_questionbank_items"], payload["runtime_bindings"]
    assert len(items) == 800 and len(runtime) == 800
    assert len({row["item_id"] for row in items}) == 800
    assert len({row["selected_item_id"] for row in runtime}) == 800
    for form_number in range(1, 21):
        rows = [row for row in items if row["form_number"] == form_number]
        assert len(rows) == 40
        assert Counter(row["section"] for row in rows) == Counter({"A": 6, "B": 10, "C": 10, "D": 8, "E": 6})


def test_section_b_has_real_manipulation_correction_and_production_in_every_form():
    items = _payload()["successor_questionbank_items"]
    for form_number in range(1, 21):
        rows = [row for row in items if row["form_number"] == form_number and row["section"] == "B"]
        evidence = {value for row in rows for value in row["pedagogical_evidence"]}
        assert builder.B_REQUIRED_EVIDENCE.issubset(evidence)
        qtypes = {row["question_type"] for row in rows}
        assert any("rewrite" in qtype or "structured_morphology_build" in qtype for qtype in qtypes)
        assert any("correction" in qtype for qtype in qtypes)
        assert any("production" in qtype for qtype in qtypes)


def test_section_c_integrates_u01_u02_u03_inside_each_question_not_by_alternation():
    rows = [row for row in _payload()["successor_questionbank_items"] if row["section"] == "C"]
    assert len(rows) == 200
    assert all(row["task_family"] == "U01_U02_INTEGRATION" for row in rows)
    assert all(set(row["grammar_targets"]) == {"ARTICLE", "PLURALITY", "SUBJECT_PRONOUN"} for row in rows)
    assert all(row["primary_target"] == "SUBJECT_PRONOUN" for row in rows)
    assert all(set(row["secondary_targets"]) == {"ARTICLE", "PLURALITY"} for row in rows)
    assert all(row["integration_proof"] == {
        "same_question_contains_u01_article": True,
        "same_question_contains_u02_number_plural": True,
        "same_question_contains_u03_subject_pronoun": True,
        "alternating_separate_questions_only": False,
    } for row in rows)


def test_section_e_is_exactly_six_connected_passage_questions_per_form_and_120_total():
    payload = _payload()
    rows = [row for row in payload["successor_questionbank_items"] if row["section"] == "E"]
    assert len(rows) == 120
    expected_types = {qtype for qtype, _ in builder.CONNECTED_PASSAGE_TYPES}
    for form_number in range(1, 21):
        form_rows = [row for row in rows if row["form_number"] == form_number]
        assert len(form_rows) == 6
        assert all(row["connected_passage"] is True for row in form_rows)
        assert len({row["passage_id"] for row in form_rows}) == 1
        assert {row["question_type"] for row in form_rows} == expected_types
        stage = builder._stage(form_number)
        expected_sentence_count = builder.PASSAGE_SENTENCE_COUNT_BY_STAGE[stage]
        assert all(row["passage_sentence_count"] == expected_sentence_count for row in form_rows)
    assert payload["pedagogical_proofs"]["section_e_connected_passage_question_count"] == 120


def test_progression_is_guided_reduced_independent_transfer_retention():
    progression = _payload()["progression_contract"]
    assert progression["forms_by_stage"] == {
        "GUIDED": [1, 2, 3, 4],
        "REDUCED_SUPPORT": [5, 6, 7, 8],
        "INDEPENDENT": [9, 10, 11, 12],
        "TRANSFER": [13, 14, 15, 16],
        "RETENTION": [17, 18, 19, 20],
    }
    assert progression["passage_sentence_count_by_stage"] == {
        "GUIDED": 2, "REDUCED_SUPPORT": 3, "INDEPENDENT": 4,
        "TRANSFER": 5, "RETENTION": 5,
    }


def test_q6_is_read_only_and_out_of_scope_items_stay_locked():
    payload = _payload()
    q6 = payload["q6_preservation"]
    assert q6["historical_unit03_admitted_sentence_asset_count"] == 18983
    assert q6["successor_sentence_assets_created"] == 0
    assert q6["q6_regenerated"] is False
    assert q6["q6_mutated"] is False
    boundaries = payload["claim_boundaries"]
    assert all(boundaries[key] is False for key in (
        "q1_q4_mutated", "q5_mutated", "q6_regenerated", "q6_mutated",
        "q7_mutated", "q8_mutated", "historical_q10_runtime_mutated",
        "historical_u03scfv2_runtime_mutated", "family_11_created",
        "pdf_pagination_modified", "pdf_renderer_modified", "q11_opened",
        "unit04_opened", "a2_unlocked",
    ))
    assert payload["next_short_step"] == builder.NEXT_SHORT_STEP
