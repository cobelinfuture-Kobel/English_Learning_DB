from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ulga.builders import (
    build_a1fs_v1_u01qb16f_unit01_adaptive_loop_learner_facing_acceptance_and_pedagogical_quality_closeout
    as u16f,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = (
    "ulga.builders."
    "build_a1fs_v1_u01qb16f_unit01_adaptive_loop_learner_facing_acceptance_and_pedagogical_quality_closeout"
)


def test_u01qb16f_closes_the_real_learner_visible_defect_without_expanding_the_bank() -> None:
    result = u16f.build_closeout()
    assert result["status"] == u16f.PASS_STATUS
    assert result["product"]["serve_module"] == "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
    assert result["product"]["runtime_item_count"] == 474
    assert result["product"]["form_count"] == 12
    assert result["product"]["blueprint_activity_count"] == 240
    quality = result["pedagogical_quality"]
    assert quality["option_reordering_counts_as_same_question"] is True
    assert quality["different_stimulus_counts_as_different_question"] is True
    assert quality["first_mention_label_aliases_collapsed"] is True
    assert quality["known_reference_is_distinct_capability"] is True
    assert quality["error_discrimination_is_distinct_capability"] is True
    assert quality["reference_evidence_is_distinct_capability"] is True
    assert quality["learner_visible_duplicate_guard_active"] is True


def test_u01qb16f_accepts_the_single_existing_adaptive_runtime_chain() -> None:
    result = u16f.build_closeout()
    adaptive = result["adaptive_loop"]
    assert adaptive["single_existing_runtime"] is True
    assert adaptive["same_item_retry_allowed"] is False
    assert adaptive["reassessment_mode"] == "DIFFERENT_EXISTING_ITEM_AFTER_M7_DIAGNOSIS"
    assert adaptive["canonical_m7_authority_preserved"] is True
    assert all(adaptive["installed_guards"].values())
    assert adaptive["flow"] == [
        "ATTEMPT_ONCE",
        "M7_DIAGNOSIS",
        "TARGETED_REMEDIATION",
        "DIFFERENT_EXISTING_ITEM_REASSESSMENT",
        "M7_M8_CANONICAL_REFRESH",
        "ORDINARY_FORM_PROGRESSION",
    ]


def test_u01qb16f_learner_ui_exposes_remediation_and_different_item_reassessment_without_answers() -> None:
    result = u16f.build_closeout()
    learner = result["learner_facing"]
    assert learner == {
        "attempt_once_message_visible": True,
        "diagnosis_and_remediation_visible": True,
        "different_item_reassessment_visible": True,
        "pending_reassessment_resume_visible": True,
        "private_answer_fields_referenced": False,
    }
    frozen = result["frozen_boundaries"]
    assert frozen["questionbank_count_preserved"] is True
    assert frozen["questionbank_content_modified_by_closeout"] is False
    assert frozen["scoring_authority_modified_by_closeout"] is False
    assert frozen["mastery_policy_modified_by_closeout"] is False
    assert frozen["unit02_to_unit24_modified_by_closeout"] is False
    assert frozen["speaking_practice_only_no_score"] is True
    assert frozen["audio_deferred"] is True
    assert frozen["a2_locked"] is True
    assert result["unit01_questionbank_pedagogical_quality_closeout_complete"] is True


def test_u01qb16f_cli_is_machine_readable_and_points_outside_the_completed_unit01_scope() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", MODULE],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    result = json.loads(completed.stdout)
    assert result["status"] == u16f.PASS_STATUS
    assert result["next_short_step"] == "A1FS-V1-U02QB00_Unit02QuestionBankScopeAndCurrentStateAdmission"
    assert u16f.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16f.A1FS_CONTENT_POLICY_EXEMPTION
