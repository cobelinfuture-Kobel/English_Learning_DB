from __future__ import annotations

import json

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import _u01qb18f_r4r3r3d_formal_donor_rejection_funnel_diagnostic as diagnostic


def test_formal_diagnostic_is_read_only_non_content_producer() -> None:
    assert diagnostic.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "Read-only" in diagnostic.A1FS_CONTENT_POLICY_EXEMPTION
    assert "474-item" in diagnostic.A1FS_CONTENT_POLICY_EXEMPTION
    assert "authors no content" in diagnostic.A1FS_CONTENT_POLICY_EXEMPTION


def test_candidate_summary_reports_learner_visible_unsat_with_per_activity_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activities = [
        {
            "activity_id": "A1",
            "pattern_family_ids_json": json.dumps(["PF"]),
            "scene_anchors_json": json.dumps(["robot"]),
            "situation_family": "SHOPPING",
            "assessment_candidate": 0,
        },
        {
            "activity_id": "A2",
            "pattern_family_ids_json": json.dumps(["PF"]),
            "scene_anchors_json": json.dumps(["robot"]),
            "situation_family": "SHOPPING",
            "assessment_candidate": 0,
        },
    ]
    visible_payload = json.dumps(
        {"stimulus": "I see a robot.", "prompt": "Choose the article.", "options": ["a", "the"]}
    )
    rows = {
        "A1": {"item_id": "I1", "skill": "READING", "private_item_json": visible_payload},
        "A2": {"item_id": "I2", "skill": "READING", "private_item_json": visible_payload},
    }

    def fake_pairs(activity, **_kwargs):
        row = rows[str(activity["activity_id"])]
        return [((0,), row)]

    monkeypatch.setattr(diagnostic.r4r2, "_candidate_pairs", fake_pairs)
    ok, error, detail = diagnostic._candidate_summary(
        activities,
        catalog=[],
        scoring={},
        form_ordinal=8,
        skill="READING",
    )
    assert ok is False
    assert "FORM_COMPONENT_LEARNER_VISIBLE_DISTINCTNESS_UNSAT" in error
    assert "A1:items=1,visible=1" in detail
    assert "A2:items=1,visible=1" in detail


def test_owner_prints_task_and_formal_funnels_then_reraises_original(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = r4r3r1.SupportStageSceneSwapError(
        "SUPPORT_STAGE_SCENE_SWAP_NOT_FOUND:U01-MA-SHOP-04:F08"
    )

    def fail_migration(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(
        owner.r4r3r1,
        "migrate_unbound_support_stage_scene_assignment",
        fail_migration,
    )
    monkeypatch.setattr(
        owner.r4r3r1_diagnostic,
        "diagnose",
        lambda *_args, **_kwargs: ["R4R3R1_DIAGNOSTIC_STATUS=PASS_TASK_FUNNEL"],
    )
    monkeypatch.setattr(
        owner.r4r3r3d_diagnostic,
        "diagnose",
        lambda *_args, **_kwargs: [
            "R4R3R3D_DIAGNOSTIC_STATUS=PASS_FORMAL_FUNNEL",
            "R4R3R3D_ENDPOINT=F11|U01-C4-TOY-SHOP|CURRENT_READING|status=FAIL",
        ],
    )

    with pytest.raises(r4r3r1.SupportStageSceneSwapError) as raised:
        owner.assemble_form_component_with_writing_parity(
            "ignored.sqlite3",
            learner_id="L",
            session_id="S",
            form_ordinal=8,
        )
    assert raised.value is error
    output = capsys.readouterr().out
    assert "PASS_TASK_FUNNEL" in output
    assert "PASS_FORMAL_FUNNEL" in output
    assert "CURRENT_READING|status=FAIL" in output


def test_formal_diagnostic_failure_never_masks_original_swap_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = r4r3r1.SupportStageSceneSwapError(
        "SUPPORT_STAGE_SCENE_SWAP_NOT_FOUND:U01-MA-SHOP-04:F08"
    )

    def fail_migration(*_args, **_kwargs):
        raise error

    def broken_diagnostic(*_args, **_kwargs):
        raise ValueError("DIAGNOSTIC_ONLY_FAILURE")

    monkeypatch.setattr(
        owner.r4r3r1,
        "migrate_unbound_support_stage_scene_assignment",
        fail_migration,
    )
    monkeypatch.setattr(owner.r4r3r1_diagnostic, "diagnose", lambda *_a, **_k: [])
    monkeypatch.setattr(owner.r4r3r3d_diagnostic, "diagnose", broken_diagnostic)

    with pytest.raises(r4r3r1.SupportStageSceneSwapError) as raised:
        owner.assemble_form_component_with_writing_parity(
            "ignored.sqlite3",
            learner_id="L",
            session_id="S",
            form_ordinal=8,
        )
    assert raised.value is error
    assert "R4R3R3D_DIAGNOSTIC_ERROR=ValueError:DIAGNOSTIC_ONLY_FAILURE" in capsys.readouterr().out
