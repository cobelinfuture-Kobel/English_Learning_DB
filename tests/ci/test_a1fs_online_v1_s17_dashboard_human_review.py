from __future__ import annotations

from pathlib import Path

from ulga.builders import build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime as s17


def test_dashboard_projection_separates_three_roles_and_privacy() -> None:
    projection = s17.build_dashboard_projection(
        skill_progress=[
            {
                "skill": "LISTENING",
                "session_count": 0,
                "completed_session_count": 0,
                "attempt_count": 0,
                "pass_count": 0,
                "fail_count": 0,
                "pending_review_count": 0,
                "resolved_pass_rate": 0.0,
            },
            {
                "skill": "SPEAKING",
                "session_count": 1,
                "completed_session_count": 1,
                "attempt_count": 0,
                "pass_count": 0,
                "fail_count": 0,
                "pending_review_count": 0,
                "resolved_pass_rate": 0.0,
            },
            {
                "skill": "READING",
                "session_count": 2,
                "completed_session_count": 2,
                "attempt_count": 8,
                "pass_count": 7,
                "fail_count": 1,
                "pending_review_count": 0,
                "resolved_pass_rate": 0.875,
            },
            {
                "skill": "WRITING",
                "session_count": 1,
                "completed_session_count": 0,
                "attempt_count": 4,
                "pass_count": 3,
                "fail_count": 0,
                "pending_review_count": 1,
                "resolved_pass_rate": 1.0,
            },
        ],
        canonical_learning={
            "required_mastery_node_count": 72,
            "mastered_required_count": 3,
            "open_remediation_count": 2,
            "pending_reassessment_count": 2,
            "due_review_count": 3,
            "overdue_review_count": 1,
            "retained_required_count": 0,
        },
        pending_review_count=1,
    )

    assert projection["role_count"] == 3
    assert projection["learner"] == {
        "completed_session_count": 3,
        "mastered_required_count": 3,
        "required_mastery_node_count": 72,
        "open_remediation_count": 2,
        "due_review_count": 4,
        "a2_unlocked": False,
    }
    assert projection["parent"]["attempt_count"] == 12
    assert projection["parent"]["attention_codes"] == [
        "HUMAN_REVIEW_REQUIRED",
        "REMEDIATION_REQUIRED",
        "REASSESSMENT_PENDING",
        "SPACED_REVIEW_DUE",
    ]
    assert projection["teacher"]["pending_human_review_count"] == 1
    assert projection["teacher"]["writing"]["pending_review_count"] == 1
    assert projection["privacy_boundaries"]["raw_response_in_dashboard"] is False
    assert projection["privacy_boundaries"]["raw_response_available_only_in_authenticated_review_queue"] is True
    assert projection["product_boundaries"]["role_based_identity_authorization_claimed"] is False
    assert s17._contains_exact_key(projection, s17.DASHBOARD_PRIVATE_KEYS) is False


def test_s17_static_surface_and_launcher_preserve_security_boundaries(tmp_path: Path) -> None:
    static = tmp_path / "static"
    s17.s16._write_static(static)
    s17._write_static(static)
    index = (static / "index.html").read_text(encoding="utf-8")
    app = (static / "app.js").read_text(encoding="utf-8")

    assert "學習儀表板與人工審核" in index
    assert 'data-dashboard-role="learner"' in index
    assert 'data-dashboard-role="parent"' in index
    assert 'data-dashboard-role="teacher"' in index
    assert "/api/dashboard" in app
    assert "/api/human-review" in app
    assert "/api/human-review/decision" in app
    assert "renderRoleDashboard" in app
    assert "renderHumanReviews" in app
    assert "innerHTML" not in app

    outputs = s17._write_launch_bundle(
        target_root=tmp_path / "launch",
        receipt_path=tmp_path / "receipt.private.json",
        auth_state_db=tmp_path / "auth.sqlite3",
    )
    start = Path(outputs["start_script_path"]).read_text(encoding="utf-8")
    stop = Path(outputs["stop_script_path"]).read_text(encoding="utf-8")
    contract = s17.read_json(Path(outputs["launch_contract_path"]), "contract")
    assert "build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime" in start
    assert "PID_OWNERSHIP_MISMATCH" in stop
    assert contract["dashboard_role_count"] == 3
    assert contract["csrf_required_for_review_decision"] is True
    assert contract["role_based_identity_authorization_claimed"] is False
    assert contract["human_review_authority"] == "A1FS_V1_M6"
    assert contract["a2_session_enabled"] is False
    assert contract["audio_enabled"] is False
    assert contract["cloudflare_enabled"] is False
