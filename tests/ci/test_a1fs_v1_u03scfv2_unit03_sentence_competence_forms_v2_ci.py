from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u03scfv2_unit03_sentence_competence_forms_v2_800_materialization
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u03scfv2_unit03_sentence_competence_forms_v2
    as validator,
)


@lru_cache(maxsize=1)
def _payload():
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["validation_status"] == "PASS"
    return approved["payload"]


def test_u03scfv2_preserves_current_unit02_authority_and_reuses_existing_contracts():
    payload = _payload()
    assert payload["unit02_preservation"] == {
        "form_count": 16,
        "runtime_occurrence_count": 640,
        "approved_item_count": 1730,
        "cumulative_catalog_item_count": 2204,
        "unit02_16x40_mutated": False,
    }
    source = payload["source_authority"]
    assert source["unit03_q5_task_id"] == builder.u03q5.TASK_ID
    assert source["unit02_current_runtime_task_id"] == builder.u02r4.TASK_ID
    assert source["unit02_form01_task_id"] == builder.u02form01.TASK_ID
    assert source["sentence_asset_semantics_reused_from"] == "ulga/builders/a1fs_v1_u02sa01r1"
    assert "_student_activity" in source["existing_learner_projection_reused"]


def test_u03scfv2_materializes_context_bound_sentenceasset_and_questionbank_deltas():
    payload = _payload()
    sentence = payload["sentence_asset_delta"]
    assert sentence["asset_count"] == 80
    assert len(sentence["assets"]) == 80
    assert len({row["sentence_id"] for row in sentence["assets"]}) == 80
    assert len({row["normalized_text"] for row in sentence["assets"]}) == 80
    assert all(row["context_bound"] is True for row in sentence["assets"])
    assert all(row["pattern_binding_status"] == "NO_NEW_UNIT03_PATTERN_FAMILY_ADMITTED" for row in sentence["assets"])

    qb = payload["questionbank_delta"]
    assert qb["unit03_new_item_count"] == 400
    assert len(qb["unit03_new_items"]) == 400
    assert qb["inherited_cumulative_catalog_count"] == 2204
    assert qb["cumulative_catalog_count_after_unit03"] == 2604
    assert qb["parallel_questionbank_created"] is False


def test_u03scfv2_materializes_twenty_by_forty_eight_hundred_distinct_runtime_bindings():
    payload = _payload()
    contract = payload["runtime_form_contract"]
    assert contract["form_count"] == 20
    assert contract["activities_per_form"] == 40
    assert contract["runtime_occurrence_count"] == 800
    assert contract["inherited_runtime_binding_count"] == 400
    assert contract["unit03_delta_runtime_binding_count"] == 400
    assert contract["sections_per_form"] == 5
    assert contract["activities_per_section"] == 8
    assert contract["candidate_count_per_slot"] == 3
    assert contract["global_800_distinct_selected_item_proof"] is True

    runtime = payload["runtime_bindings"]
    assert len(runtime) == 800
    assert len({row["runtime_occurrence_id"] for row in runtime}) == 800
    assert len({row["selected_item_id"] for row in runtime}) == 800
    assert all(len(row["candidate_ids"]) == 3 for row in runtime)
    assert all(len(set(row["candidate_ids"])) == 3 for row in runtime)
    assert all(row["selected_item_id"] == row["candidate_ids"][0] for row in runtime)


def test_u03scfv2_stage_section_allocation_and_learner_forms_are_exact():
    payload = _payload()
    allocation = payload["stage_allocation"]
    assert allocation["forms_by_stage"] == {
        "GUIDED": [1, 2, 3, 4],
        "REDUCED_SUPPORT": [5, 6, 7, 8],
        "INDEPENDENT": [9, 10, 11, 12],
        "TRANSFER": [13, 14, 15, 16],
        "RETENTION": [17, 18, 19, 20],
    }
    assert allocation["runtime_occurrences_by_stage"] == {
        "GUIDED": 160,
        "REDUCED_SUPPORT": 160,
        "INDEPENDENT": 160,
        "TRANSFER": 160,
        "RETENTION": 160,
    }
    forms = payload["student_forms"]
    assert len(forms) == 20
    assert all(form["learner_visible_activity_count"] == 40 for form in forms)
    assert all(form["section_count"] == 5 for form in forms)
    assert sum(len(form["activities"]) for form in forms) == 800
    for form in forms:
        builder.u01_learner._assert_no_answer_leak(form)


def test_u03scfv2_does_not_create_parallel_authorities_or_unlock_a2():
    boundaries = _payload()["claim_boundaries"]
    assert boundaries == {
        "unit02_forms01_16_mutated": False,
        "unit01_unit02_questionbank_items_mutated": False,
        "second_questionbank_authority_created": False,
        "second_selector_created": False,
        "second_renderer_created": False,
        "parallel_sentence_asset_schema_created": False,
        "canonical_sentence_pattern_authority_mutated": False,
        "learner_state_mutated": False,
        "a2_unlocked": False,
    }
    assert _payload()["next_short_step"] == builder.NEXT_SHORT_STEP
