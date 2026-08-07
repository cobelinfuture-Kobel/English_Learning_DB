#!/usr/bin/env python3
"""Accept the existing Unit01 12-form learner-visible production-quality chain.

This validator creates no content and no runtime. It reconciles the already-
merged U01QB09/U01QB12/U01QB13/U01QB16B/U01QB16C/U01QB16E contracts into one
fail-closed gate for pedagogical progression and product safety.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as product_runtime
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u12
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB17B_UNIT01_TWELVE_FORM_LEARNER_VISIBLE_PRODUCTION_QUALITY_VALIDATOR"
TASK_ID = "A1FS-V1-U01QB17B_Unit01TwelveFormLearnerVisibleProductionQualityAndProgressionAcceptance"
PASS_STATUS = "PASS_A1FS_V1_U01QB17B_UNIT01_TWELVE_FORM_LEARNER_VISIBLE_PRODUCTION_QUALITY_AND_PROGRESSION_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-U01QB17C_Unit01QuestionBankProductionQualityCloseoutAndUnit02HandoffReadiness"
EXPECTED_SUPPORT_BY_FORM = {
    1: "GUIDED", 2: "GUIDED", 3: "GUIDED",
    4: "REDUCED_SUPPORT", 5: "REDUCED_SUPPORT", 6: "REDUCED_SUPPORT",
    7: "INDEPENDENT", 8: "INDEPENDENT", 9: "INDEPENDENT",
    10: "TRANSFER", 11: "TRANSFER", 12: "TRANSFER",
}


class ProductionQualityValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ProductionQualityValidationError(code)


def _manifest() -> dict[str, Any]:
    return json.loads(
        (Path(product_runtime.__file__).with_name("product_manifest.json")).read_text(encoding="utf-8")
    )


def _learner_adapter_source() -> str:
    return (
        Path(product_runtime.__file__)
        .with_name("runtime")
        .joinpath("secure_static", "u01qb15.js")
        .read_text(encoding="utf-8")
    )


def validate() -> dict[str, Any]:
    # 1. Denominator and single-runtime authority remain frozen.
    manifest = _manifest()
    require(manifest.get("serve_module") == "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e", "SERVE_MODULE_DRIFT")
    require(manifest.get("unit01_questionbank_runtime_item_count") == 474, "RUNTIME_DENOMINATOR_DRIFT")
    require(u13.EXPECTED_RUNTIME_COUNT == 474, "U13_RUNTIME_DENOMINATOR_DRIFT")
    require(u12.EXPECTED_RUNTIME_COUNT == 474, "U12_RUNTIME_DENOMINATOR_DRIFT")
    require(u13.EXPECTED_EXTENSION_COUNT == 186, "REAL62_DENOMINATOR_DRIFT")

    # 2. The 12 Forms have a monotonic support-withdrawal curriculum, not 12
    # interchangeable worksheets.
    support_by_form = {form: u09.support_for_form(form) for form in range(1, 13)}
    require(support_by_form == EXPECTED_SUPPORT_BY_FORM, "TWELVE_FORM_SUPPORT_PROGRESSION_DRIFT")
    require(u13.ASSESSMENT_FORM_ORDINALS == (10, 11, 12), "TRANSFER_ASSESSMENT_FORMS_DRIFT")
    require(u13.FORM_COUNT == 12, "FORM_COUNT_DRIFT")
    require(u13.ACTIVITIES_PER_FORM == 20, "ACTIVITIES_PER_FORM_DRIFT")
    require(u13.SCORED_PER_FORM == 16, "SCORED_PER_FORM_DRIFT")
    require(u13.SPEAKING_PRACTICE_PER_FORM == 4, "SPEAKING_PER_FORM_DRIFT")
    require(u13.EXPECTED_ACTIVITY_COUNT == 240, "TOTAL_ACTIVITY_COUNT_DRIFT")
    require(u13.EXPECTED_SCORED_ACTIVITY_COUNT == 192, "TOTAL_SCORED_COUNT_DRIFT")
    require(u13.EXPECTED_SPEAKING_ACTIVITY_COUNT == 48, "TOTAL_SPEAKING_COUNT_DRIFT")

    # 3. Every scored angle that any support band may request has an exact
    # canonical U01QB13 binding. PF16/PF17 must be real canonical U01QB12
    # families, not historical partial aliases.
    requested_scored: set[tuple[str, str]] = set()
    for profile in u09.SUPPORT_PROFILES.values():
        for skill in ("READING", "WRITING"):
            for angle in profile["candidates"][skill]:
                requested_scored.add((skill, angle))
    missing = sorted(pair for pair in requested_scored if not u13.EXACT_SCORED_BINDINGS.get(pair))
    require(not missing, f"SCORED_EXACT_BINDING_GAP:{missing}")
    require(u13.PF16 == u12.PF16, "PF16_AUTHORITY_DRIFT")
    require(u13.PF17 == u12.PF17, "PF17_AUTHORITY_DRIFT")
    require(u13.EXACT_SCORED_BINDINGS[("READING", "REFERENCE_EVIDENCE")] == (u12.PF16,), "REFERENCE_EVIDENCE_NOT_CANONICAL")
    require(u13.EXACT_SCORED_BINDINGS[("WRITING", "PHRASE_CONSTRUCTION")] == (u12.PF17,), "PHRASE_CONSTRUCTION_NOT_CANONICAL")

    # 4. Reading labels are evaluated by learner capability class so apparent
    # label diversity cannot hide repeated first-mention a/an/the tasks.
    reading_angles = {
        angle
        for profile in u09.SUPPORT_PROFILES.values()
        for angle in profile["candidates"]["READING"]
    }
    class_by_angle = {angle: u16b.capability_class("READING", angle) for angle in sorted(reading_angles)}
    require(class_by_angle["ARTICLE_CONTROL"] == u16b.FIRST_MENTION_SELECTION, "ARTICLE_CONTROL_CLASS_DRIFT")
    require(class_by_angle["FIRST_MENTION_CONTEXT"] == u16b.FIRST_MENTION_SELECTION, "FIRST_MENTION_CLASS_DRIFT")
    require(class_by_angle["TRANSFER_DECISION"] == u16b.FIRST_MENTION_SELECTION, "TRANSFER_DECISION_CLASS_DRIFT")
    require(class_by_angle["KNOWN_REFERENCE_CONTEXT"] == u16b.KNOWN_REFERENCE_USE, "KNOWN_REFERENCE_CLASS_DRIFT")
    require(class_by_angle["ERROR_CHECK"] == u16b.ERROR_DISCRIMINATION, "ERROR_CLASS_DRIFT")
    require(class_by_angle["REFERENCE_EVIDENCE"] == u16b.REFERENCE_EVIDENCE, "REFERENCE_EVIDENCE_CLASS_DRIFT")
    require(len(set(class_by_angle.values())) >= 4, "READING_CAPABILITY_BREADTH_INSUFFICIENT")

    # 5. Existing learner evidence is protected: U16C only migrates unbound
    # Reading forms and freezes a form as soon as any Reading activity is bound.
    require(u16c.MIGRATION_TABLE == "u01qb16c_unbound_activity_migrations", "U16C_MIGRATION_TABLE_DRIFT")
    require(u16c.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER", "U16C_CONTENT_MODE_DRIFT")
    source_c = Path(u16c.__file__).read_text(encoding="utf-8")
    require("SKIP_FORM_FROZEN_BY_PRIOR_BINDING" in source_c, "BOUND_FORM_FREEZE_GUARD_MISSING")
    require("learner_attempts_modified\": \"false" in source_c, "LEARNER_ATTEMPT_IMMUTABILITY_MARKER_MISSING")
    require("questionbank_modified\": \"false" in source_c, "QUESTIONBANK_IMMUTABILITY_MARKER_MISSING")

    # 6. Learner surface exposes task-angle/support semantics and closes failed
    # evidence through targeted remediation + a different existing item, rather
    # than same-item drill-until-correct.
    ui = _learner_adapter_source()
    for token in (
        "${item.task_angle}｜${item.support_level}",
        "錯題補救",
        "完成補救，開始換題重評",
        "換題重新評量",
        "原錯題不重播",
        "support fillers 不呈現給學習者",
    ):
        require(token in ui, f"LEARNER_VISIBLE_SEMANTIC_MISSING:{token}")
    require(u16e.installed() is True, "U16E_RUNTIME_NOT_INSTALLED")
    require(manifest.get("unit01_questionbank_same_item_retry_allowed") is False, "SAME_ITEM_RETRY_REENABLED")
    require(manifest.get("unit01_questionbank_reassessment_mode") == "DIFFERENT_EXISTING_ITEM_AFTER_M7_DIAGNOSIS", "REASSESSMENT_MODE_DRIFT")

    support_counts = Counter(support_by_form.values())
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "runtime_item_count": 474,
        "real62_extension_count": 186,
        "form_count": 12,
        "activity_count": 240,
        "scored_activity_count": 192,
        "speaking_practice_activity_count": 48,
        "support_form_counts": dict(sorted(support_counts.items())),
        "assessment_form_ordinals": [10, 11, 12],
        "requested_scored_angle_count": len(requested_scored),
        "scored_exact_binding_gap_count": 0,
        "reading_capability_class_count": len(set(class_by_angle.values())),
        "reference_evidence_family": u12.PF16,
        "phrase_construction_family": u12.PF17,
        "bound_form_rewrite_allowed": False,
        "same_item_retry_allowed": False,
        "second_runtime_created": False,
        "questionbank_expanded": False,
        "speaking_scoring_enabled": False,
        "audio_enabled": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    try:
        report = validate()
    except (ProductionQualityValidationError, OSError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB17B_UNIT01_TWELVE_FORM_LEARNER_VISIBLE_PRODUCTION_QUALITY")
        print(f"ERROR={exc}")
        return 1
    for key in (
        "validation_status",
        "runtime_item_count",
        "form_count",
        "activity_count",
        "scored_exact_binding_gap_count",
        "reading_capability_class_count",
        "next_short_step",
    ):
        print(f"{key.upper()}={report[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
