from __future__ import annotations

from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07
from ulga.builders import build_a1fs_online_v1_s08_private_multiunit_learner_journey_qa as s08


def test_bootstrap_rebinds_s07_runtime_to_s08_surface_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        s07.MultiUnitWorkbenchApplication,
        "bootstrap",
        lambda self: {
            "task_id": s07.TASK_ID,
            "validation_status": s07.PASS_STATUS,
            "product_status": s07.PRODUCT_STATUS,
            "units": [],
        },
    )
    app = object.__new__(s08.JourneyWorkbenchApplication)
    value = app.bootstrap()
    assert value["task_id"] == s08.TASK_ID
    assert value["validation_status"] == s08.PASS_STATUS
    assert value["product_status"] == s08.PRODUCT_STATUS
    assert value["release_profile"] == s08.RELEASE_PROFILE
    assert value["source_runtime"]["task_id"] == s07.TASK_ID
    assert value["journey_controls"]["navigation_locked_while_active"] is True


def test_static_surface_locks_pending_resume_and_marks_selected_navigation(tmp_path) -> None:
    s08._write_static(tmp_path)
    script = (tmp_path / "app.js").read_text(encoding="utf-8")
    assert "const navigationLocked = () => Boolean(active || pendingResume);" in script
    assert "button.disabled = navigationLocked();" in script
    assert "button.classList.toggle(" in script
    assert "pendingResume.grammar_unit_id + ' / ' + pendingResume.session.skill" in script
    assert "if (navigationLocked()) throw new Error('請先繼續或放棄目前技能');" in script
    assert "chooseUnit(match.unit)" not in script
