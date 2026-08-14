from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import (
    u01qb18g_unit01_twelve_form_learner_facing_pedagogical_review_and_closeout as closeout,
)


def _write(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _r4_report() -> dict[str, object]:
    forms = []
    for ordinal in range(1, 13):
        support = closeout._expected_support(ordinal)
        exposures = [
            {
                "form_ordinal": ordinal,
                "scene_ref_id": f"SCENE-{ordinal:02d}-{index}",
                "support_levels": [support],
                "richer_language_asset_activity_count": 1,
                "learner_visible_stimulus_duplicate_count": 0,
            }
            for index in range(1, 5)
        ]
        forms.append(
            {
                "form_ordinal": ordinal,
                "form_id": f"U01-FORM-{ordinal:02d}",
                "error_count": 0,
                "scene_exposures": exposures,
                "student_form": {
                    "scene_count": 4,
                    "learner_visible_activity_count": 20,
                    "skill_counts": {"READING": 8, "WRITING": 8, "SPEAKING": 4},
                },
                "semantic_e2e": {"error_count": 0},
                "cross_layer_preservation": {"error_count": 0},
            }
        )
    return {
        "task_id": closeout.r4.TASK_ID,
        "validation_status": closeout.r4.PASS_STATUS,
        "form_count": 12,
        "scene_exposure_count": 48,
        "learner_visible_activity_count": 240,
        "semantic_e2e_pass_form_count": 12,
        "cross_layer_pass_form_count": 12,
        "canonical_scene_authority": {
            "canonical_scene_count": 32,
            "unit01_runtime_bindable_scene_count": 31,
            "deferred_scene_refs": ["U01-MA-FOOD-04"],
        },
        "runtime_proof": {
            "runtime_item_count": 474,
            "real62_extension_item_count": 186,
            "real62_artifact_sha256": "real62-sha",
            "source_production_database_modified": False,
            "questionbank_modified": False,
            "new_question_items_authored": 0,
        },
        "claim_boundaries": {
            "scoring_recorded": False,
            "mastery_recorded": False,
            "audio_enabled": False,
            "speaking_scored": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "forms": forms,
        "reused_scene_count": 1,
        "reused_scene_reports": [
            {
                "scene_ref_id": "REUSED",
                "selected_item_overlap_count": 0,
                "task_angle_changed": True,
                "support_level_changed": True,
            }
        ],
    }


def _r5_report(r4_sha: str) -> dict[str, object]:
    return {
        "task_id": closeout.r5.TASK_ID,
        "validation_status": closeout.r5.PASS_STATUS,
        "r4_report_sha256": r4_sha,
        "real62_artifact_sha256": "real62-sha",
        "canonical_scene_count": 32,
        "unit01_runtime_bindable_scene_count": 31,
        "deferred_scene_refs": ["U01-MA-FOOD-04"],
        "model_scene_count": 27,
        "reconciled_model_scene_count": 27,
        "unresolved_model_scene_count": 0,
        "source_text_exported": False,
        "questionbank_modified": False,
        "scene_semantics_modified": False,
        "new_scene_authored": False,
    }


def _materialize(tmp_path: Path, r4_report: dict[str, object], r5_mutator=None):
    r4_path = tmp_path / "r4.json"
    r5_path = tmp_path / "r5.json"
    output = tmp_path / "closeout.json"
    _write(r4_path, r4_report)
    r5_report = _r5_report(_sha(r4_path))
    if r5_mutator is not None:
        r5_mutator(r5_report)
    _write(r5_path, r5_report)
    return closeout.materialize_closeout(
        r4_report_path=r4_path,
        r5_report_path=r5_path,
        output=output,
    ), output


def test_u18g_closes_only_after_r4_r5_and_all_four_support_bands_pass(tmp_path: Path) -> None:
    result, output = _materialize(tmp_path, _r4_report())

    assert result["validation_status"] == closeout.PASS_STATUS
    assert result["unit01_closeout_complete"] is True
    assert result["form_count"] == 12
    assert result["scene_exposure_count"] == 48
    assert result["learner_visible_activity_count"] == 240
    assert result["runtime_item_count"] == 474
    assert result["base_item_count"] == 288
    assert result["real62_extension_item_count"] == 186
    assert result["canonical_scene_count"] == 32
    assert result["unit01_runtime_bindable_scene_count"] == 31
    assert result["deferred_scene_refs"] == ["U01-MA-FOOD-04"]
    assert result["reconciled_model_scene_count"] == 27
    assert result["unresolved_model_scene_count"] == 0
    assert result["support_band_form_counts"] == {
        "GUIDED": 3,
        "REDUCED_SUPPORT": 3,
        "INDEPENDENT": 3,
        "TRANSFER": 3,
    }
    assert result["questionbank_modified"] is False
    assert result["new_question_items_authored"] == 0
    assert result["new_scene_authored"] is False
    assert result["production_database_modified"] is False
    assert result["a2_unlocked"] is False
    assert result["next_short_step_scope"] == "OUTSIDE_CURRENT_UNIT01_SCOPE"
    assert output.is_file()


def test_u18g_fails_closed_on_support_progression_drift(tmp_path: Path) -> None:
    report = _r4_report()
    report["forms"][3]["scene_exposures"][0]["support_levels"] = ["GUIDED"]

    with pytest.raises(
        closeout.LearnerFacingPedagogicalCloseoutError,
        match="FORM_SUPPORT_PROGRESS_DRIFT:F04",
    ):
        _materialize(tmp_path, report)


def test_u18g_fails_closed_when_r5_does_not_prove_the_exact_r4_report(tmp_path: Path) -> None:
    with pytest.raises(
        closeout.LearnerFacingPedagogicalCloseoutError,
        match="R5_R4_REPORT_IDENTITY_MISMATCH",
    ):
        _materialize(
            tmp_path,
            _r4_report(),
            lambda report: report.__setitem__("r4_report_sha256", "wrong"),
        )


def test_u18g_fails_closed_on_reused_scene_item_or_progression_regression(tmp_path: Path) -> None:
    report = _r4_report()
    report["reused_scene_reports"][0]["selected_item_overlap_count"] = 1

    with pytest.raises(
        closeout.LearnerFacingPedagogicalCloseoutError,
        match="REUSED_SCENE_ITEM_OVERLAP",
    ):
        _materialize(tmp_path, report)


def test_u18g_is_non_content_producer_and_does_not_enter_unit02() -> None:
    assert closeout.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert closeout.EXPECTED_RUNTIME_ITEMS == 474
    assert closeout.EXPECTED_REAL62_EXTENSION_ITEMS == 186
    assert closeout.EXPECTED_CANONICAL_SCENES == 32
    assert closeout.EXPECTED_BINDABLE_SCENES == 31
    assert closeout.EXPECTED_DEFERRED_REFS == ("U01-MA-FOOD-04",)
    assert closeout.NEXT_SHORT_STEP.startswith("A1FS-V1-U02QB00_")
    assert closeout.NEXT_SHORT_STEP_SCOPE == "OUTSIDE_CURRENT_UNIT01_SCOPE"
