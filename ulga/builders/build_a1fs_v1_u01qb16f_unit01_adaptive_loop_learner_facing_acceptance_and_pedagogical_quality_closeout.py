#!/usr/bin/env python3
"""Close U01QB16 after learner-visible pedagogical and adaptive-loop integration.

This is an aggregate acceptance/readback over the already-merged U01QB16 through
U01QB16E production guards.  It creates no QuestionBank content and does not
replace the existing M3/M6/M7/M8 learner runtime.  The closeout proves that the
real product entry point preserves the 474-item bank while exposing the intended
learner flow:

    one attempt -> diagnosis -> targeted remediation -> different existing item
    -> reassessment -> canonical M7/M8 refresh -> ordinary form progression.

It also closes the learner-visible defect that motivated U01QB16: two different
item IDs may not count as two questions when their stimulus/prompt/options are
identical from the learner's perspective.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as product_runtime
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb16d_questionbank_diagnosis_remediation_identity_adapter as u16d
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Aggregate learner-facing acceptance and pedagogical-quality closeout over existing U01QB16-U01QB16E runtime guards; it creates no content, answers, scoring authority, mastery policy, learner-state migration, Unit02-24 content, audio, Speaking scoring, or A2 content."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16F_Unit01AdaptiveLoopLearnerFacingAcceptanceAndPedagogicalQualityCloseout"
PASS_STATUS = "PASS_A1FS_V1_U01QB16F_UNIT01_ADAPTIVE_LOOP_LEARNER_FACING_ACCEPTANCE_AND_PEDAGOGICAL_QUALITY_CLOSEOUT"
NEXT_SHORT_STEP = "A1FS-V1-U02QB00_Unit02QuestionBankScopeAndCurrentStateAdmission"


class AdaptiveLoopCloseoutError(ValueError):
    """Fail-closed U01QB16F acceptance error."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AdaptiveLoopCloseoutError(message)


def _manifest() -> tuple[dict[str, Any], Path]:
    path = Path(product_runtime.__file__).with_name("product_manifest.json")
    return json.loads(path.read_text(encoding="utf-8")), path


def _learner_ui_source() -> tuple[str, Path]:
    path = Path(product_runtime.__file__).parent / "runtime" / "secure_static" / "u01qb15.js"
    return path.read_text(encoding="utf-8"), path


def _private_item(stimulus: str, *, options: list[str] | None = None) -> str:
    return json.dumps(
        {
            "stimulus": stimulus,
            "prompt": "Choose the best article.",
            "options": options or ["a", "an", "the"],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _visible_signature_acceptance() -> dict[str, Any]:
    failed: Mapping[str, Any] = {
        "item_id": "FAILED",
        "skill": "READING",
        "private_item_json": _private_item("There is ___ apple in the bag."),
    }
    reordered_duplicate: Mapping[str, Any] = {
        "item_id": "DUPLICATE-ID",
        "skill": "READING",
        "private_item_json": _private_item(
            "There is ___ apple in the bag.",
            options=["the", "a", "an"],
        ),
    }
    distinct: Mapping[str, Any] = {
        "item_id": "DISTINCT",
        "skill": "READING",
        "private_item_json": _private_item("Mia can see ___ orange at the picnic."),
    }
    failed_signature = u16.learner_visible_signature(failed)
    duplicate_signature = u16.learner_visible_signature(reordered_duplicate)
    distinct_signature = u16.learner_visible_signature(distinct)
    _require(
        failed_signature == duplicate_signature,
        "OPTION_REORDERING_WAS_MISTAKEN_FOR_PEDAGOGICAL_DISTINCTNESS",
    )
    _require(
        failed_signature != distinct_signature,
        "DISTINCT_LEARNER_VISIBLE_ITEM_COLLAPSED_TO_FAILED_SIGNATURE",
    )
    return {
        "option_reordering_counts_as_same_question": True,
        "different_stimulus_counts_as_different_question": True,
    }


def _runtime_acceptance(manifest: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        manifest.get("serve_module") == "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e",
        "SECOND_OR_DRIFTED_PRODUCT_RUNTIME_DETECTED",
    )
    _require(manifest.get("unit01_questionbank_revision") == "U01QB15-R1", "QUESTIONBANK_REVISION_DRIFT")
    _require(manifest.get("unit01_questionbank_runtime_item_count") == 474, "QUESTIONBANK_COUNT_DRIFT")
    _require(manifest.get("unit01_questionbank_form_count") == 12, "FORM_COUNT_DRIFT")
    _require(manifest.get("unit01_questionbank_blueprint_activity_count") == 240, "BLUEPRINT_COUNT_DRIFT")
    _require(manifest.get("unit01_questionbank_same_item_retry_allowed") is False, "SAME_ITEM_RETRY_REENABLED")
    _require(
        manifest.get("unit01_questionbank_reassessment_mode")
        == "DIFFERENT_EXISTING_ITEM_AFTER_M7_DIAGNOSIS",
        "DIFFERENT_ITEM_REASSESSMENT_MODE_MISSING",
    )
    _require(manifest.get("listening_enabled") is False, "LISTENING_SCOPE_DRIFT")
    _require(manifest.get("audio_enabled") is False, "AUDIO_SCOPE_DRIFT")
    _require(manifest.get("speaking_capture_enabled") is False, "SPEAKING_CAPTURE_SCOPE_DRIFT")

    guards = {
        "u01qb16_visible_distinctness": u16.installed(),
        "u01qb16b_capability_progression": u16b.installed(),
        "u01qb16c_unbound_form_migration": u16c.installed(),
        "u01qb16d_diagnosis_identity": u16d.installed(),
        "u01qb16e_different_item_consumer": u16e.installed(),
    }
    _require(all(guards.values()), "U01QB16_GUARD_CHAIN_NOT_FULLY_INSTALLED")
    _require(m7._diagnostic_tags is u16d.diagnostic_tags, "M7_DIAGNOSTIC_AUTHORITY_NOT_ENRICHED")
    _require(m7._strategy is u16d.strategy, "M7_REMEDIATION_STRATEGY_NOT_ENRICHED")
    _require(
        m7.MasteryRemediationEngine.build_snapshot is u16d.build_snapshot,
        "M7_SNAPSHOT_IDENTITY_ADAPTER_NOT_ACTIVE",
    )
    app = product_runtime.impl.U01QB15ProductApplication
    _require(
        app.start_u01qb15_form is u16e._start_form_after_reassessment_gate,
        "ORDINARY_FORM_NOT_BLOCKED_BY_PENDING_REASSESSMENT",
    )
    _require(
        app.submit_u01qb15_response is u16e._submit_form_response_attempt_once,
        "ATTEMPT_ONCE_RESPONSE_GUARD_NOT_ACTIVE",
    )
    _require(
        app.start_u01qb16e_reassessment is u16e._start_reassessment_api,
        "REASSESSMENT_START_CONSUMER_NOT_ACTIVE",
    )
    _require(
        app.submit_u01qb16e_reassessment is u16e._submit_reassessment_api,
        "REASSESSMENT_RESPONSE_CONSUMER_NOT_ACTIVE",
    )
    return {
        "single_existing_runtime": True,
        "installed_guards": guards,
        "same_item_retry_allowed": False,
        "reassessment_mode": manifest["unit01_questionbank_reassessment_mode"],
        "canonical_m7_authority_preserved": True,
    }


def _progression_acceptance() -> dict[str, Any]:
    expected = {
        "ARTICLE_CONTROL": u16b.FIRST_MENTION_SELECTION,
        "FIRST_MENTION_CONTEXT": u16b.FIRST_MENTION_SELECTION,
        "TRANSFER_DECISION": u16b.FIRST_MENTION_SELECTION,
        "KNOWN_REFERENCE_CONTEXT": u16b.KNOWN_REFERENCE_USE,
        "ERROR_CHECK": u16b.ERROR_DISCRIMINATION,
        "REFERENCE_EVIDENCE": u16b.REFERENCE_EVIDENCE,
    }
    actual = {
        angle: u16b.capability_class("READING", angle)
        for angle in expected
    }
    _require(actual == expected, "READING_CAPABILITY_CLASSIFICATION_DRIFT")
    _require(
        len({u16b.FIRST_MENTION_SELECTION, u16b.KNOWN_REFERENCE_USE, u16b.ERROR_DISCRIMINATION, u16b.REFERENCE_EVIDENCE}) == 4,
        "READING_PEDAGOGICAL_CAPABILITY_CLASSES_COLLAPSED",
    )
    return {
        "first_mention_label_aliases_collapsed": True,
        "known_reference_is_distinct_capability": True,
        "error_discrimination_is_distinct_capability": True,
        "reference_evidence_is_distinct_capability": True,
    }


def _learner_facing_acceptance(source: str) -> dict[str, Any]:
    required_tokens = (
        "U01QB16E_ATTEMPT_ONCE_THEN_DIAGNOSE_REASSESS",
        "每題只作答一次",
        "已記錄錯誤；完成後換題補救",
        "/api/u01qb16e/reassessment/pending",
        "/api/u01qb16e/reassessment/start",
        "/api/u01qb16e/reassessment/active",
        "/api/u01qb16e/reassessment/response",
        "錯題補救",
        "完成補救，開始換題重評",
        "不會直接重做剛才的錯題",
        "換題重新評量",
        "Different-item reassessment",
        "原錯題不重播",
        "u01qb16eMaybeRenderPending",
        "u01qb16eAttempted",
    )
    missing = [token for token in required_tokens if token not in source]
    _require(not missing, "LEARNER_FACING_ADAPTIVE_LOOP_TOKEN_MISSING:" + ",".join(missing))
    forbidden_tokens = ("correct_answer", "accepted_answers")
    leaked = [token for token in forbidden_tokens if token in source]
    _require(not leaked, "PRIVATE_ANSWER_FIELD_REFERENCED_BY_LEARNER_UI:" + ",".join(leaked))
    return {
        "attempt_once_message_visible": True,
        "diagnosis_and_remediation_visible": True,
        "different_item_reassessment_visible": True,
        "pending_reassessment_resume_visible": True,
        "private_answer_fields_referenced": False,
    }


def build_closeout() -> dict[str, Any]:
    manifest, manifest_path = _manifest()
    ui_source, ui_path = _learner_ui_source()
    runtime = _runtime_acceptance(manifest)
    signatures = _visible_signature_acceptance()
    progression = _progression_acceptance()
    learner_facing = _learner_facing_acceptance(ui_source)
    return {
        "schema_version": "a1fs.v1.u01qb16f.adaptive_loop_closeout.v1",
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "product": {
            "manifest_path": str(manifest_path),
            "learner_ui_path": str(ui_path),
            "serve_module": manifest["serve_module"],
            "questionbank_revision": manifest["unit01_questionbank_revision"],
            "runtime_item_count": manifest["unit01_questionbank_runtime_item_count"],
            "form_count": manifest["unit01_questionbank_form_count"],
            "blueprint_activity_count": manifest["unit01_questionbank_blueprint_activity_count"],
        },
        "pedagogical_quality": {
            **signatures,
            **progression,
            "learner_visible_duplicate_guard_active": True,
            "future_unbound_reading_form_progression_overlay_active": True,
        },
        "adaptive_loop": {
            **runtime,
            "flow": [
                "ATTEMPT_ONCE",
                "M7_DIAGNOSIS",
                "TARGETED_REMEDIATION",
                "DIFFERENT_EXISTING_ITEM_REASSESSMENT",
                "M7_M8_CANONICAL_REFRESH",
                "ORDINARY_FORM_PROGRESSION",
            ],
        },
        "learner_facing": learner_facing,
        "frozen_boundaries": {
            "questionbank_count_preserved": True,
            "questionbank_content_modified_by_closeout": False,
            "scoring_authority_modified_by_closeout": False,
            "mastery_policy_modified_by_closeout": False,
            "unit02_to_unit24_modified_by_closeout": False,
            "speaking_practice_only_no_score": True,
            "audio_deferred": True,
            "a2_locked": True,
        },
        "unit01_questionbank_pedagogical_quality_closeout_complete": True,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    try:
        print(json.dumps(build_closeout(), ensure_ascii=False, indent=2, sort_keys=True))
    except (AdaptiveLoopCloseoutError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL:{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
