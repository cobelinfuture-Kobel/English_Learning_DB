from __future__ import annotations

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r3r1_donor_rejection_diagnostic as diagnostic
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1


def test_diagnostic_is_read_only_non_content_producer() -> None:
    assert diagnostic.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "Read-only" in diagnostic.A1FS_CONTENT_POLICY_EXEMPTION
    assert "QuestionBank" in diagnostic.A1FS_CONTENT_POLICY_EXEMPTION


def test_post_swap_repeat_gap_keeps_reused_donor_visible_when_legal() -> None:
    ok, detail = diagnostic._post_swap_repeat_gap(
        donor_usage={"form_ordinals": [2, 10], "exposure_count": 2},
        donor_form=10,
        current_form=8,
    )
    assert ok is True
    assert detail == "FORMS=2,8;GAP=6;MIN=3"


def test_post_swap_repeat_gap_rejects_reused_donor_when_too_close() -> None:
    ok, detail = diagnostic._post_swap_repeat_gap(
        donor_usage={"form_ordinals": [6, 10], "exposure_count": 2},
        donor_form=10,
        current_form=8,
    )
    assert ok is False
    assert detail == "FORMS=6,8;GAP=2;MIN=3"


def test_skill_capacity_reports_exact_skill_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_choices(*, skill: str, **_kwargs):
        if skill == "WRITING":
            raise ValueError("WRITING_CAPACITY_ZERO")
        return {"SCENE": ("ANGLE",)}

    monkeypatch.setattr(r4r3r1, "_form_skill_choices", fake_choices)
    ok, detail = diagnostic._skill_capacity(
        all_rows=[],
        form_ordinal=8,
        catalog={},
    )
    assert ok is False
    assert detail == "WRITING=ValueError:WRITING_CAPACITY_ZERO"


def test_owner_prints_diagnostic_and_reraises_original_swap_failure(
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
        lambda *_args, **_kwargs: [
            "R4R3R1_DIAGNOSTIC_STATUS=PASS_DIAGNOSTIC",
            "R4R3R1_DONOR=F10|U01-MA-SHOP-01|exposures=2|broader_pair_pass=true",
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
    assert "R4R3R1_DIAGNOSTIC_STATUS=PASS_DIAGNOSTIC" in output
    assert "exposures=2" in output
    assert "broader_pair_pass=true" in output
