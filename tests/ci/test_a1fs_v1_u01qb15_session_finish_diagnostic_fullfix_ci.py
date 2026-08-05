from __future__ import annotations

import json

from ulga.builders import (
    build_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback as runner,
)


def test_private_runner_installs_diagnostic_finish_path_without_changing_runtime_authority() -> None:
    assert runner._impl._finish_active is runner._finish_active_with_diagnostics
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION


class _FakeCDP:
    def __init__(self) -> None:
        self.clicked = False

    def evaluate(self, expression: str, *, await_promise: bool = False):
        if expression == "abandon.click();true":
            self.clicked = True
            return True
        if expression.startswith("(async()=>"):
            return {
                "ui_status": "SESSION_VERSION_CONFLICT:7:8",
                "lane_note": "U01QB15-R1｜Form 2／12",
                "form_ordinal": 2,
                "complete_disabled": True,
                "u01qb15_card_count": 8,
                "active": {
                    "session_id": "U01QB15:READING:diagnostic",
                    "session_version": 7,
                    "lesson_id": "UNIT01:READING",
                    "skill": "READING",
                    "session_state": "ACTIVE",
                },
                "pending_resume": None,
                "backend_active_session": {
                    "ok": True,
                    "value": {
                        "active": True,
                        "session": {
                            "session_id": "U01QB15:READING:diagnostic",
                            "session_version": 8,
                        },
                    },
                },
                "backend_u01qb15_form": {
                    "ok": True,
                    "value": {"active": True},
                },
            }
        if expression.startswith("({done:"):
            return {
                "done": False,
                "active_session_id": "U01QB15:READING:diagnostic",
                "active_session_version": 7,
                "pending_session_id": None,
                "ui_status": "SESSION_VERSION_CONFLICT:7:8",
            }
        raise AssertionError(expression)


def test_stalled_finish_reports_ui_and_backend_state_instead_of_generic_timeout() -> None:
    fake = _FakeCDP()
    original_monotonic = runner.time.monotonic
    ticks = iter((100.0, 121.0))
    runner.time.monotonic = lambda: next(ticks)
    try:
        try:
            runner._finish_active_with_diagnostics(fake, complete_session=False)
        except runner._impl.PrivateBrowserReadbackError as exc:
            message = str(exc)
        else:
            raise AssertionError("expected diagnostic failure")
    finally:
        runner.time.monotonic = original_monotonic

    assert fake.clicked is True
    assert message.startswith("SESSION_FINISH_STATE_NOT_CLEARED:")
    payload = json.loads(message.split(":", 1)[1])
    assert payload["action"] == "ABANDON"
    assert payload["after"]["ui_status"] == "SESSION_VERSION_CONFLICT:7:8"
    assert payload["after"]["active"]["session_id"] == "U01QB15:READING:diagnostic"
    assert payload["after"]["backend_active_session"]["value"]["session"]["session_version"] == 8
    assert payload["after"]["backend_u01qb15_form"]["value"]["active"] is True
