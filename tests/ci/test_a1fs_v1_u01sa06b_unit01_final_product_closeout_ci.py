from __future__ import annotations

import json
from pathlib import Path


EVIDENCE = (
    Path(__file__).resolve().parents[2]
    / "product"
    / "a1fs_v1_2_1"
    / "release_evidence"
    / "u01sa06b_unit01_final_product_closeout.safe.json"
)


def _load() -> dict:
    value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_u01sa06b_final_unit01_product_closeout_is_complete_and_fail_closed() -> None:
    value = _load()
    assert value["task_id"] == "A1FS-V1-U01SA06B_Unit01FinalLearnerProductBindingCloseout"
    assert value["validation_status"] == (
        "PASS_A1FS_V1_U01SA06B_UNIT01_FINAL_LEARNER_PRODUCT_BINDING_CLOSEOUT"
    )
    assert value["required_main_merge_sha"] == "c435f6354feea16ccb346810d07029f7338c1fa6"

    learner = value["learner_product_acceptance"]
    assert learner["r4_forms"] == 12
    assert learner["r4_activities"] == 240
    assert learner["semantic_e2e_pass_forms"] == 12
    assert learner["cross_layer_pass_forms"] == 12
    assert learner["pdf_files"] == 12
    assert learner["pdf_machine_preflight_pass"] == 12
    assert learner["pdf_human_visual_pass"] == 12
    assert learner["pdf_human_pedagogical_pass"] == 12
    for key in ("acceptance_zip_sha256", "pdf_manifest_sha256", "r4_report_sha256"):
        assert len(learner[key]) == 64

    binding = value["final_binding_acceptance"]
    assert binding["status"] == (
        "PASS_A1FS_V1_U01SA06A_UNIT01_FINAL240_ACTIVITY_QB_SENTENCE_ASSET_BINDING"
    )
    assert binding["form_count"] == 12
    assert binding["scene_exposure_count"] == 48
    assert binding["activity_binding_count"] == 240
    assert binding["selected_item_distinct_count"] == 185
    assert binding["runtime_item_count"] == 474
    assert binding["sentence_pool_total"] == 3805
    assert sum(binding["binding_source_occurrence_counts"].values()) == 240
    assert binding["binding_source_occurrence_counts"] == {
        "SA05R2_EXACT_ITEM_ID": 168,
        "R2R2_INLINE_SENTENCE_LINEAGE": 57,
        "POST_SA05R2_IDENTITY_BRIDGE": 15,
    }
    assert binding["unresolved_count"] == 0
    assert binding["r2r2_runtime_item_count"] == 474
    assert binding["r2r2_source_database_mutated"] is False
    assert binding["production_requirement_count"] == 43
    assert binding["production_materialized_item_count"] == 43
    assert binding["contextual_reference_requirement_count"] == 16
    assert binding["contextual_reference_materialized_item_count"] == 16

    closeout = value["closeout_assertions"]
    for key in (
        "unit01_product_d0",
        "unit01_closeout_complete",
        "questionbank_runtime_closed",
        "sentence_asset_binding_closed",
        "learner_product_acceptance_closed",
        "unit02_planning_allowed",
    ):
        assert closeout[key] is True
    for key in (
        "source_database_modified",
        "second_questionbank_created",
        "second_runtime_created",
        "second_planner_created",
        "second_scoring_authority_created",
        "unit02_to_unit24_modified",
        "unit02_implementation_allowed",
        "speaking_scoring_enabled",
        "a2_unlocked",
    ):
        assert closeout[key] is False
    assert closeout["new_sentence_candidate_count"] == 0
    assert closeout["new_question_item_count"] == 0
    assert value["next_short_step"] == (
        "A1FS-V1-U02QB00_Unit02QuestionBankScopeAndCurrentStateAdmission"
    )
    assert value["next_short_step_scope"] == "UNIT02_PLANNING_ONLY"
