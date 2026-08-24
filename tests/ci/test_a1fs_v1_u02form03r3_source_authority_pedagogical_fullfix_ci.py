from collections import Counter
from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix_and_global_distinct_runtime
    as builder,
)
from ulga.builders import (
    build_a1fs_v1_u02fp01_unit02_final_package_q1_q10_export as fp01,
)
from ulga.validators import (
    validate_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix
    as validator,
)


@lru_cache(maxsize=1)
def _payload():
    return builder.build_export_payload()


def test_r3_preserves_q01_q08_and_updates_only_q09_q10_authority():
    baseline = fp01.build_export_payload()
    payload = _payload()
    for key in builder._Q1_Q8_KEYS:
        assert payload[key] == baseline[key]
    assert payload["q01_q08_preservation"]["preserved"] is True
    assert (
        payload["q01_q08_preservation"]["baseline_sha256"]
        == payload["q01_q08_preservation"]["r3_sha256"]
    )
    assert payload["q9_task_angle_question_type"] != baseline["q9_task_angle_question_type"]
    assert payload["q10_questionbank_capacity_runtime"] != baseline["q10_questionbank_capacity_runtime"]


def test_r3_materializes_capacity_for_64_distinct_questions_per_family():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    assert q10["inventory_summary"]["unit02_approved_item_count"] == builder.EXPECTED_UNIT02_APPROVED_ITEMS
    assert q10["inventory_summary"]["r3_new_policy_bound_items"] == builder.R3_NEW_ITEMS
    assert q10["runtime_eligibility"]["minimum_runtime_family_pool_depth"] >= 64
    assert all(depth >= 64 for depth in q10["runtime_eligibility"]["runtime_family_pool_counts"].values())
    r3_items = [row for row in q10["unit02_approved_items"] if row["item_id"].startswith("U02FORM03R3-")]
    assert len(r3_items) == builder.R3_NEW_ITEMS
    assert Counter(row["task_family"] for row in r3_items) == Counter(
        {family: builder.R3_CONTEXTS_PER_MATERIALIZED_FAMILY for family in builder.R3_MATERIALIZED_FAMILIES}
    )


def test_r3_proves_global_640_runtime_question_distinctness():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    rows = q10["runtime_occurrences"]
    proof = q10["global_distinctness_proof"]
    assert len(rows) == 640
    assert len({row["runtime_occurrence_id"] for row in rows}) == 640
    assert len({row["selected_item_id"] for row in rows}) == 640
    assert len({row["visible_signature"] for row in rows}) == 640
    assert len({row["effective_signature"] for row in rows}) == 640
    assert len({row["runtime_semantic_signature"] for row in rows}) == 640
    assert proof["distinct_runtime_occurrence_ids"] == 640
    assert proof["distinct_selected_item_ids"] == 640
    assert proof["distinct_visible_signatures"] == 640
    assert proof["distinct_effective_signatures"] == 640
    assert proof["distinct_semantic_signatures"] == 640
    assert proof["exact_duplicate_groups"] == 0
    assert proof["normalized_duplicate_groups"] == 0
    assert proof["semantic_duplicate_groups"] == 0
    assert proof["same_visible_different_answer_groups"] == 0
    assert proof["within_form_duplicates"] == 0
    assert proof["cross_form_duplicates"] == 0
    assert proof["prior_activity_direct_answer_leaks"] == 0
    assert proof["global_640_distinct_runtime_question_proof"] is True
    for family in builder.TASK_FAMILIES:
        assert proof["per_family"][family] == {
            "runtime_occurrences": 64,
            "distinct_selected_item_ids": 64,
            "distinct_visible_signatures": 64,
            "distinct_effective_signatures": 64,
            "distinct_semantic_signatures": 64,
        }


def test_r3_runtime_removes_legacy_qbc02_delivery_and_restricted_surface():
    rows = _payload()["q10_questionbank_capacity_runtime"]["runtime_occurrences"]
    assert not any(row["selected_item_id"].startswith("U02QBC02-") for row in rows)
    assert all(row["target_singular"].casefold() != "beer" for row in rows)
    assert Counter(row["task_family"] for row in rows) == Counter({family: 64 for family in builder.TASK_FAMILIES})
    for form_number in range(1, 17):
        form_rows = [row for row in rows if row["form_number"] == form_number]
        assert len(form_rows) == 40
        for scene_slot in range(1, 5):
            scene_rows = [row for row in form_rows if row["scene_slot_ordinal"] == scene_slot]
            assert len(scene_rows) == 10
            assert len({row["target_singular"] for row in scene_rows}) == 10


def test_r3_q6_binding_and_progression_support_contract():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    rows = q10["runtime_occurrences"]
    bound = [row for row in rows if row["sentence_asset_binding"]["status"] == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"]
    assert len(bound) == 128
    assert Counter(row["task_family"] for row in bound) == Counter({"PRODUCTIVE_RESPONSE": 64, "TRANSFER": 64})
    assert q10["progression_support_contract"] == {
        "learner_support_notes_by_stage": builder.SUPPORT_NOTE_BY_STAGE,
        "support_reduction_proven": True,
    }
    assert {row["progression_stage"]: row["learner_support_note"] for row in rows} == builder.SUPPORT_NOTE_BY_STAGE


def test_r3_selected_learner_text_has_no_legacy_at_the_template():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    items = {row["item_id"]: row for row in q10["unit02_approved_items"]}
    for runtime in q10["runtime_occurrences"]:
        item = items[runtime["selected_item_id"]]
        visible = " ".join([
            str(item.get("prompt") or ""),
            str(item.get("stimulus") or ""),
            *[str(value) for value in item.get("options") or []],
        ])
        assert "At the " not in visible


def test_r3_policy_bound_candidate_and_validator_pass():
    candidate = builder.build_candidate()
    receipt = validator.validate_candidate(candidate)
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert receipt["status"] == "PASS"
    assert report["validation_status"] == "PASS"
    assert report["global_640_distinct_runtime_question_proof"] is True
