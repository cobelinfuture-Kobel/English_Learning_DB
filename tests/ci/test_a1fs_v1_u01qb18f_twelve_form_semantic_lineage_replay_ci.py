from __future__ import annotations

import inspect
import json

import pytest

from product.a1fs_v1_2_1 import u01qb18a_form01_fresh_learner_materialization_export as u18a
from product.a1fs_v1_2_1 import u01qb18f_twelve_form_semantic_lineage_replay as replay
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as semantic


def _exposure(
    *,
    form_ordinal: int,
    ref: str,
    token: str,
    task_angle: str,
    support: str,
) -> dict:
    return {
        "form_ordinal": form_ordinal,
        "scene_ref_id": ref,
        "selected_item_ids": [f"ITEM-{token}-{index}" for index in range(1, 6)],
        "task_angles": [task_angle, task_angle, "WORD_ORDER", "COMPLETE_SENTENCE_PRODUCTION", "SCENE_DESCRIPTION"],
        "support_levels": [support],
        "richer_language_asset_activity_count": 1,
        "semantic_compatible_activity_count": 1,
        "semantic_signal_hit_count": 1,
        "learner_visible_stimulus_duplicate_count": 0,
        "target_noun_counts": {"cat": 2, "tree": 2, "dog": 1},
        "vocabulary_ref_count": 2,
        "chunk_ref_count": 1,
        "sentence_ref_count": 1,
        "content_asset_count": 1,
    }


def _form_record(form_ordinal: int, exposures: list[dict]) -> dict:
    return {
        "form_ordinal": form_ordinal,
        "form_id": f"U01-FORM-{form_ordinal:02d}",
        "validation_status": replay.PASS_STATUS,
        "error_count": 0,
        "errors": [],
        "semantic_e2e": {"validation_status": semantic.PASS_STATUS, "error_count": 0},
        "scene_exposures": exposures,
        "student_form": {
            "form_id": f"U01-FORM-{form_ordinal:02d}",
            "form_ordinal": form_ordinal,
            "learner_visible_activity_count": 20,
            "activities": [],
        },
    }


def _twelve_form_records() -> list[dict]:
    records: list[dict] = []
    first_exposure: dict[str, int] = {}
    # Forms 01-08 introduce 32 distinct micro-scenes.
    for form_ordinal in range(1, 9):
        exposures = []
        for slot in range(1, 5):
            ref = f"SCENE-{(form_ordinal - 1) * 4 + slot:02d}"
            first_exposure[ref] = form_ordinal
            exposures.append(
                _exposure(
                    form_ordinal=form_ordinal,
                    ref=ref,
                    token=f"F{form_ordinal:02d}S{slot}",
                    task_angle="ARTICLE_CONTROL",
                    support="GUIDED" if form_ordinal <= 3 else "REDUCED_SUPPORT",
                )
            )
        records.append(_form_record(form_ordinal, exposures))
    # Forms 09-12 reuse exactly 16 scenes with changed task/support and no item replay.
    for form_ordinal in range(9, 13):
        exposures = []
        start = (form_ordinal - 9) * 4 + 1
        for offset in range(4):
            ref = f"SCENE-{start + offset:02d}"
            exposures.append(
                _exposure(
                    form_ordinal=form_ordinal,
                    ref=ref,
                    token=f"REPLAY-F{form_ordinal:02d}S{offset + 1}",
                    task_angle="KNOWN_REFERENCE_CONTEXT",
                    support="TRANSFER",
                )
            )
        records.append(_form_record(form_ordinal, exposures))
    return records


def test_scaffold_progression_is_frozen_across_forms_01_to_12() -> None:
    assert replay._expected_scaffold_stage(1) == quality.FORM01_SCAFFOLD_STAGE
    assert replay._expected_scaffold_stage(2) == quality.FORM02_SCAFFOLD_STAGE
    assert replay._expected_scaffold_stage(3) == quality.FORM03_SCAFFOLD_STAGE
    assert all(
        replay._expected_scaffold_stage(form) == quality.FORM04_PLUS_SCAFFOLD_STAGE
        for form in range(4, 13)
    )


def test_repeat_scene_report_requires_new_items_task_angle_and_support() -> None:
    records = [
        _form_record(
            1,
            [_exposure(form_ordinal=1, ref="SCENE-X", token="SAME", task_angle="ARTICLE_CONTROL", support="GUIDED")],
        ),
        _form_record(
            7,
            [_exposure(form_ordinal=7, ref="SCENE-X", token="SAME", task_angle="ARTICLE_CONTROL", support="GUIDED")],
        ),
    ]
    reports, errors = replay._repeat_scene_report(records)
    assert reports[0]["selected_item_overlap_count"] == 5
    assert reports[0]["task_angle_changed"] is False
    assert reports[0]["support_level_changed"] is False
    assert any(error.startswith("REUSED_SCENE_ITEM_REPLAY:SCENE-X:") for error in errors)
    assert "REUSED_SCENE_TASK_ANGLE_NOT_CHANGED:SCENE-X" in errors
    assert "REUSED_SCENE_SUPPORT_NOT_CHANGED:SCENE-X" in errors


def test_aggregate_accepts_12_forms_48_exposures_240_activities_and_16_spiral_reuses() -> None:
    records = _twelve_form_records()
    value = replay._aggregate(
        learner_id="FRESH",
        cutover={
            "questionbank_revision": "U01QB15-R1",
            "runtime_item_count": 474,
            "extension_item_count": 186,
            "real62_artifact_sha256": "a" * 64,
        },
        source_snapshot_sha256="b" * 64,
        form_records=records,
    )
    assert value["validation_status"] == replay.PASS_STATUS
    assert value["form_count"] == 12
    assert value["scene_exposure_count"] == 48
    assert value["learner_visible_activity_count"] == 240
    assert value["semantic_e2e_pass_form_count"] == 12
    assert value["reused_scene_count"] == 16
    assert all(row["selected_item_overlap_count"] == 0 for row in value["reused_scene_reports"])
    assert all(row["task_angle_changed"] is True for row in value["reused_scene_reports"])
    assert all(row["support_level_changed"] is True for row in value["reused_scene_reports"])
    assert value["runtime_proof"]["runtime_item_count"] == 474
    assert value["runtime_proof"]["real62_extension_item_count"] == 186
    assert value["runtime_proof"]["questionbank_modified"] is False
    assert value["runtime_proof"]["new_question_items_authored"] == 0


def test_aggregate_fails_if_one_form_semantic_e2e_fails() -> None:
    records = _twelve_form_records()
    records[4]["validation_status"] = replay.FAIL_STATUS
    records[4]["errors"] = ["SCENE_LANGUAGE_ASSET_CONSUMPTION_MISSING:F05:SCENE-17"]
    value = replay._aggregate(
        learner_id="FRESH",
        cutover={
            "questionbank_revision": "U01QB15-R1",
            "runtime_item_count": 474,
            "extension_item_count": 186,
            "real62_artifact_sha256": "a" * 64,
        },
        source_snapshot_sha256="b" * 64,
        form_records=records,
    )
    assert value["validation_status"] == replay.FAIL_STATUS
    assert value["semantic_e2e_failed_form_ordinals"] == [5]
    assert "FORM_SEMANTIC_E2E_FAILURES:5" in value["errors"]


def test_aggregate_never_allows_answer_side_fields_into_review_artifact() -> None:
    records = _twelve_form_records()
    records[0]["student_form"]["correct_answer"] = "SECRET"
    with pytest.raises(u18a.Form01MaterializationError, match="ANSWER_OR_PRIVATE_KEY_EXPORTED"):
        replay._aggregate(
            learner_id="FRESH",
            cutover={
                "questionbank_revision": "U01QB15-R1",
                "runtime_item_count": 474,
                "extension_item_count": 186,
                "real62_artifact_sha256": "a" * 64,
            },
            source_snapshot_sha256="b" * 64,
            form_records=records,
        )


def test_replay_uses_snapshot_formal_product_path_and_never_authors_items() -> None:
    source = inspect.getsource(replay.materialize_twelve_form_replay)
    skill_source = inspect.getsource(replay._materialize_skill)
    assert "u18a._sqlite_snapshot" in source
    assert "product_runtime.impl.require_cutover" in source
    assert "impl.matching.install()" in skill_source
    assert "u13.assemble_form_component(" in skill_source
    assert "impl.learner_form_payload" in skill_source
    assert replay.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert replay.A1FS_CONTENT_POLICY_EXEMPTION
    assert replay.FORM_COUNT == 12
    assert replay.EXPECTED_TOTAL_SCENE_EXPOSURES == 48
    assert replay.EXPECTED_TOTAL_ACTIVITIES == 240
    assert replay.NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB18G_")


def test_projected_task_focus_keeps_existing_approved_surfaces_distinct() -> None:
    semantics = {
        "setting": "TOY_SHOP",
        "objects": ["shop", "window"],
        "anchors": ["shop", "window"],
        "relations": ["IN"],
        "action": [],
    }
    private = {
        "stimulus": "",
        "options": ["a", "shop"],
        "lexical_slots": {"noun": "shop"},
    }

    reading = semantic._projected_stimulus(
        private_item=private,
        skill="READING",
        task_angle="ERROR_CHECK",
        form_ordinal=4,
        scene_anchors=["shop", "window"],
        setting="TOY_SHOP",
        semantics=semantics,
    )
    speaking = semantic._projected_stimulus(
        private_item=private,
        skill="SPEAKING",
        task_angle="SCENE_DESCRIPTION",
        form_ordinal=4,
        scene_anchors=["shop", "window"],
        setting="TOY_SHOP",
        semantics=semantics,
    )
    writing = semantic._projected_stimulus(
        private_item={**private, "stimulus": "item: shop | place: in the shop"},
        skill="WRITING",
        task_angle="CONNECTED_SENTENCE_PRODUCTION",
        form_ordinal=10,
        scene_anchors=["shop", "window"],
        setting="TOY_SHOP",
        semantics=semantics,
    )

    assert reading != speaking
    assert speaking != writing
    assert "task focus:" in speaking.casefold()


def test_core_task_identity_ignores_presentation_wrappers_and_instruction_wording() -> None:
    base = {
        "skill": "WRITING",
        "stimulus": "There is a shop.",
        "response_mode": "short_text",
        "options": [],
        "prompt": "Write the sentence.",
    }
    scene_wrapped = {
        **base,
        "stimulus": "Scene: Toy Shop | There is a shop. | Task focus: complete sentence production",
    }
    scene_card_only = {**base, "stimulus": "Scene: Toy Shop | There is a shop."}
    task_focus_only = {
        **base,
        "stimulus": "There is a shop. | Task focus: complete sentence production",
    }
    instruction_rephrased = {**base, "prompt": "Produce one sentence."}

    assert semantic._safe_stimulus_signature(base) == semantic._safe_stimulus_signature(
        scene_wrapped
    )
    assert semantic._safe_stimulus_signature(base) == semantic._safe_stimulus_signature(
        scene_card_only
    )
    assert semantic._safe_stimulus_signature(base) == semantic._safe_stimulus_signature(
        task_focus_only
    )
    assert semantic._safe_stimulus_signature(base) == semantic._safe_stimulus_signature(
        instruction_rephrased
    )


def test_core_task_identity_uses_material_response_contract_difference() -> None:
    select_one = {
        "skill": "READING",
        "stimulus": "There is a shop.",
        "response_mode": "select_one",
        "options": ["a", "the"],
    }
    short_text = {
        **select_one,
        "response_mode": "short_text",
        "options": [],
    }
    assert semantic._safe_stimulus_signature(select_one) != semantic._safe_stimulus_signature(
        short_text
    )


def test_same_scene_same_skill_same_item_is_rejected_by_semantic_rank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantics = {
        "setting": "TOY_SHOP",
        "objects": ["shop", "window"],
        "anchors": ["shop", "window"],
        "relations": ["IN"],
        "action": [],
    }
    monkeypatch.setattr(semantic, "_ACTIVE_CANDIDATE_RANK", lambda **_kwargs: (0,))
    monkeypatch.setattr(
        semantic,
        "_ACTIVE_ACTIVITY_SEMANTICS",
        {
            "ACTIVITY": {
                "scene_ref_id": "SCENE",
                "form_ordinal": 4,
                "skill": "READING",
                "task_angle": "ERROR_CHECK",
                "semantics": semantics,
            }
        },
    )
    monkeypatch.setattr(semantic, "_ACTIVE_PRIOR_NOUN_COUNTS", {"SCENE": {}})
    monkeypatch.setattr(semantic, "_ACTIVE_PRIOR_STIMULI", {"SCENE": set()})
    monkeypatch.setattr(semantic, "_ACTIVE_PRIOR_ITEM_IDS", {"SCENE": {"USED"}})
    item = {"stimulus": "There is a shop.", "lexical_slots": {"noun": "shop"}}
    row = {"item_id": "USED", "private_item_json": json.dumps(item)}

    assert (
        semantic._candidate_rank_with_scene_semantics(
            row=row,
            anchors={"shop"},
            situation_family="SHOPPING",
            learner_id="L",
            session_id="S",
            activity_id="ACTIVITY",
            exposed=set(),
            recent=set(),
            assessment=False,
            scene_ref_id="SCENE",
        )
        is None
    )
