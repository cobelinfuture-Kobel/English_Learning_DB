from collections import Counter
from functools import lru_cache

from product.a1fs_v1_2_1 import (
    u01qb18a_form01_fresh_learner_materialization_export as u01_learner,
)
from ulga.builders import (
    build_a1fs_v1_u02form01_unit02_existing_learner_renderer_reuse_and_16x40_deterministic_form_materialization
    as builder,
)
from ulga.builders import (
    build_a1fs_v1_u02fp01_unit02_final_package_q1_q10_export as u02fp01,
)
from ulga.builders import (
    build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as qbc02,
)


@lru_cache(maxsize=1)
def _payload():
    return builder.build_materialization()


@lru_cache(maxsize=1)
def _q10():
    return u02fp01.build_export_payload()["q10_questionbank_capacity_runtime"]


def test_u02form01_materializes_exact_16x40_student_forms():
    payload = _payload()
    assert payload["status"] == builder.PASS_STATUS
    contract = payload["form_contract"]
    assert contract == {
        "form_count": 16,
        "scene_slots_per_form": 4,
        "task_family_count": 10,
        "activities_per_scene": 10,
        "activities_per_form": 40,
        "materialized_activity_count": 640,
        "q10_selection_recomputed": False,
        "q10_candidate_order_mutated": False,
        "q10_selected_item_identity_mutated": False,
        "within_form_same_task_family_selected_item_reuse": False,
    }
    forms = payload["student_forms"]
    assert len(forms) == 16
    assert [form["form_ordinal"] for form in forms] == list(range(1, 17))
    assert all(form["scene_count"] == 4 for form in forms)
    assert all(form["learner_visible_activity_count"] == 40 for form in forms)
    assert all(form["skill_counts"] == {"READING": 16, "WRITING": 24} for form in forms)


def test_u02form01_preserves_q10_slot_task_and_selected_identity():
    q10 = _q10()
    runtime = q10["runtime_occurrences"]
    assert len(runtime) == 640
    assert all(len(row["candidate_ids"]) == 3 for row in runtime)
    assert all(row["selected_item_id"] == row["candidate_ids"][0] for row in runtime)

    expected = builder._digest(builder._selection_identity(runtime))
    assert _payload()["runtime_proof"]["source_selection_identity_sha256"] == expected

    for form_number in range(1, 17):
        rows = [row for row in runtime if row["form_number"] == form_number]
        assert len(rows) == 40
        for scene_slot in range(1, 5):
            scene_rows = [row for row in rows if row["scene_slot_ordinal"] == scene_slot]
            assert [row["task_family"] for row in scene_rows] == list(qbc02.TASK_FAMILIES)
            assert len({row["selected_item_id"] for row in scene_rows}) >= 1
        for family in qbc02.TASK_FAMILIES:
            selected = [row["selected_item_id"] for row in rows if row["task_family"] == family]
            assert len(selected) == 4
            assert len(set(selected)) == 4


def test_u02form01_student_payload_is_answer_private_and_candidate_safe():
    payload = _payload()
    for form in payload["student_forms"]:
        u01_learner._assert_no_answer_leak(form)
        text = builder._canonical(form).casefold()
        assert "candidate_ids" not in text
        assert "selected_item_id" not in text
        assert "runtime_occurrence_id" not in text
        assert "sentence_asset_id" not in text
        assert "correct_answer" not in text
        assert "accepted_answers" not in text
        assert "scoring_mode" not in text

    proof = payload["runtime_proof"]
    assert proof["candidate_ids_exported_to_learner"] is False
    assert proof["selected_item_ids_exported_to_learner"] is False
    assert proof["q6_binding_text_exported_to_learner"] is False


def test_u02form01_q6_lineage_is_validated_but_never_used_as_learner_stimulus():
    q10 = _q10()
    runtime = q10["runtime_occurrences"]
    bound = [
        row for row in runtime
        if row["sentence_asset_binding"]["status"] == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"
    ]
    assert len(bound) == 128
    assert Counter(row["task_family"] for row in bound) == {
        "PRODUCTIVE_RESPONSE": 64,
        "TRANSFER": 64,
    }
    assert all(row["sentence_asset_binding"]["sentence_asset_id"] for row in bound)
    assert all(row["sentence_asset_binding"]["binding_text"] for row in bound)
    assert _payload()["runtime_proof"]["q6_bound_occurrence_count"] == 128
    assert _payload()["runtime_proof"]["q6_binding_used_as_hidden_lineage_only"] is True


def test_u02form01_reuses_existing_unit01_learner_and_print_renderer_contracts():
    payload = _payload()
    authority = payload["source_authority"]
    assert "_student_activity/_assert_no_answer_leak" in authority["unit01_learner_projection_reuse"]
    assert "_activity_html" in authority["unit01_printable_activity_renderer_reuse"]

    html = builder.render_form_html(payload["student_forms"][0])
    assert "<title>Unit02 Form 01</title>" in html
    assert html.count('class="activity"') == 40
    assert "Practice set 1" in html
    lowered = html.casefold()
    for marker in builder.FORBIDDEN_HTML_MARKERS:
        assert marker not in lowered


def test_u02form01_runtime_restricted_surface_and_authority_boundaries():
    q10 = _q10()
    assert "beer" in q10["runtime_eligibility"]["restricted_target_surfaces"]
    assert all(
        str(row["target_singular"]).casefold() != "beer"
        for row in q10["runtime_occurrences"]
    )
    payload = _payload()
    assert payload["claim_boundaries"] == {
        "learner_facing_materialization_created": True,
        "canonical_content_created": False,
        "questionbank_items_created": False,
        "sentence_assets_created": False,
        "canonical_scene_authority_created": False,
        "runtime_authority_created": False,
        "learner_state_mutated": False,
        "scoring_authority_created": False,
        "a2_unlocked": False,
    }
    assert payload["runtime_proof"]["questionbank_modified"] is False
    assert payload["runtime_proof"]["new_question_items_authored"] == 0
    assert payload["runtime_proof"]["parallel_selector_created"] is False
    assert payload["runtime_proof"]["parallel_runtime_created"] is False
