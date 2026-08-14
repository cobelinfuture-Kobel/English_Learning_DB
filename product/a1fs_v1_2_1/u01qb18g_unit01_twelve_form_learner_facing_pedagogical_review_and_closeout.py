#!/usr/bin/env python3
"""Close Unit01 after the actual R4 replay and private R5 provenance proof.

U01QB18G is a read-only operator closeout over the already-produced R4 and R5
reports. It does not replay, author, select, score, migrate, or modify learner
content. It verifies the frozen Unit01 micro-scene/runtime denominators and the
12-Form pedagogical support progression, then emits only a compact private
closeout summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import u01qb18f_r4_full_semantic_language_pedagogical_replay as r4
from product.a1fs_v1_2_1 import u01qb18f_r5_private_real62_seed_provenance_reconciliation as r5
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit01 closeout over already-produced R4 learner-safe replay and R5 "
    "private provenance reports. It authors no learner content or scene, changes no "
    "QuestionBank, selector, planner, runtime, database, scoring, Unit02-24, audio/"
    "Speaking score, or A2 authority."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18G_Unit01TwelveFormLearnerFacingPedagogicalReviewAndCloseout"
PASS_STATUS = "PASS_A1FS_V1_U01QB18G_UNIT01_TWELVE_FORM_LEARNER_FACING_PEDAGOGICAL_REVIEW_AND_CLOSEOUT"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18G_UNIT01_TWELVE_FORM_LEARNER_FACING_PEDAGOGICAL_REVIEW_AND_CLOSEOUT"
NEXT_SHORT_STEP = "A1FS-V1-U02QB00_Unit02QuestionBankScopeAndCurrentStateAdmission"
NEXT_SHORT_STEP_SCOPE = "OUTSIDE_CURRENT_UNIT01_SCOPE"
DEFAULT_R4_REPORT = Path(".local/a1fs_v1/review/unit01_forms01_12_full_semantic_language_replay.json")
DEFAULT_R5_REPORT = Path(".local/a1fs_v1/review/unit01_micro_scene_real62_seed_provenance.private.json")
DEFAULT_OUTPUT = Path(".local/a1fs_v1/review/unit01_twelve_form_learner_facing_pedagogical_closeout.private.json")

EXPECTED_FORM_COUNT = 12
EXPECTED_SCENE_EXPOSURES = 48
EXPECTED_LEARNER_ACTIVITIES = 240
EXPECTED_RUNTIME_ITEMS = 474
EXPECTED_BASE_ITEMS = 288
EXPECTED_REAL62_EXTENSION_ITEMS = 186
EXPECTED_CANONICAL_SCENES = 32
EXPECTED_BINDABLE_SCENES = 31
EXPECTED_DEFERRED_REFS = ("U01-MA-FOOD-04",)
EXPECTED_MODEL_SCENES = 27
EXPECTED_SKILL_COUNTS = {"READING": 8, "WRITING": 8, "SPEAKING": 4}


class LearnerFacingPedagogicalCloseoutError(ValueError):
    """Fail-closed U01QB18G closeout error."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LearnerFacingPedagogicalCloseoutError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise LearnerFacingPedagogicalCloseoutError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _write_private(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _expected_support(form_ordinal: int) -> str:
    return u09.support_for_form(int(form_ordinal))


def _validate_r4(report: Mapping[str, Any]) -> None:
    if str(report.get("task_id") or "") != r4.TASK_ID:
        raise LearnerFacingPedagogicalCloseoutError("R4_TASK_ID_INVALID")
    if str(report.get("validation_status") or "") != r4.PASS_STATUS:
        raise LearnerFacingPedagogicalCloseoutError("R4_NOT_PASS")
    expected_counts = {
        "form_count": EXPECTED_FORM_COUNT,
        "scene_exposure_count": EXPECTED_SCENE_EXPOSURES,
        "learner_visible_activity_count": EXPECTED_LEARNER_ACTIVITIES,
        "semantic_e2e_pass_form_count": EXPECTED_FORM_COUNT,
        "cross_layer_pass_form_count": EXPECTED_FORM_COUNT,
    }
    for key, expected in expected_counts.items():
        if int(report.get(key, -1)) != expected:
            raise LearnerFacingPedagogicalCloseoutError(
                f"R4_{key.upper()}_INVALID:{report.get(key)}:{expected}"
            )
    scene = report.get("canonical_scene_authority") or {}
    if int(scene.get("canonical_scene_count", -1)) != EXPECTED_CANONICAL_SCENES:
        raise LearnerFacingPedagogicalCloseoutError("R4_CANONICAL_SCENE_COUNT_INVALID")
    if int(scene.get("unit01_runtime_bindable_scene_count", -1)) != EXPECTED_BINDABLE_SCENES:
        raise LearnerFacingPedagogicalCloseoutError("R4_BINDABLE_SCENE_COUNT_INVALID")
    if tuple(scene.get("deferred_scene_refs") or ()) != EXPECTED_DEFERRED_REFS:
        raise LearnerFacingPedagogicalCloseoutError("R4_DEFERRED_SCENE_REFS_INVALID")
    runtime = report.get("runtime_proof") or {}
    if int(runtime.get("runtime_item_count", -1)) != EXPECTED_RUNTIME_ITEMS:
        raise LearnerFacingPedagogicalCloseoutError("R4_RUNTIME_ITEM_COUNT_INVALID")
    if int(runtime.get("real62_extension_item_count", -1)) != EXPECTED_REAL62_EXTENSION_ITEMS:
        raise LearnerFacingPedagogicalCloseoutError("R4_REAL62_EXTENSION_COUNT_INVALID")
    if runtime.get("source_production_database_modified") is not False:
        raise LearnerFacingPedagogicalCloseoutError("R4_SOURCE_DATABASE_MODIFIED")
    if runtime.get("questionbank_modified") is not False:
        raise LearnerFacingPedagogicalCloseoutError("R4_QUESTIONBANK_MODIFIED")
    if int(runtime.get("new_question_items_authored", -1)) != 0:
        raise LearnerFacingPedagogicalCloseoutError("R4_NEW_QUESTION_ITEMS_AUTHORED")
    boundaries = report.get("claim_boundaries") or {}
    for key in (
        "scoring_recorded",
        "mastery_recorded",
        "audio_enabled",
        "speaking_scored",
        "unit02_to_unit24_modified",
        "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            raise LearnerFacingPedagogicalCloseoutError(f"R4_BOUNDARY_INVALID:{key}")


def _validate_r5(report: Mapping[str, Any], *, r4_report_sha256: str, r4_report: Mapping[str, Any]) -> None:
    if str(report.get("task_id") or "") != r5.TASK_ID:
        raise LearnerFacingPedagogicalCloseoutError("R5_TASK_ID_INVALID")
    if str(report.get("validation_status") or "") != r5.PASS_STATUS:
        raise LearnerFacingPedagogicalCloseoutError("R5_NOT_PASS")
    if str(report.get("r4_report_sha256") or "") != r4_report_sha256:
        raise LearnerFacingPedagogicalCloseoutError("R5_R4_REPORT_IDENTITY_MISMATCH")
    runtime = r4_report.get("runtime_proof") or {}
    if str(report.get("real62_artifact_sha256") or "") != str(
        runtime.get("real62_artifact_sha256") or ""
    ):
        raise LearnerFacingPedagogicalCloseoutError("R4_R5_REAL62_IDENTITY_MISMATCH")
    if int(report.get("canonical_scene_count", -1)) != EXPECTED_CANONICAL_SCENES:
        raise LearnerFacingPedagogicalCloseoutError("R5_CANONICAL_SCENE_COUNT_INVALID")
    if int(report.get("unit01_runtime_bindable_scene_count", -1)) != EXPECTED_BINDABLE_SCENES:
        raise LearnerFacingPedagogicalCloseoutError("R5_BINDABLE_SCENE_COUNT_INVALID")
    if tuple(report.get("deferred_scene_refs") or ()) != EXPECTED_DEFERRED_REFS:
        raise LearnerFacingPedagogicalCloseoutError("R5_DEFERRED_SCENE_REFS_INVALID")
    if int(report.get("model_scene_count", -1)) != EXPECTED_MODEL_SCENES:
        raise LearnerFacingPedagogicalCloseoutError("R5_MODEL_SCENE_COUNT_INVALID")
    if int(report.get("reconciled_model_scene_count", -1)) != EXPECTED_MODEL_SCENES:
        raise LearnerFacingPedagogicalCloseoutError("R5_RECONCILED_MODEL_SCENE_COUNT_INVALID")
    if int(report.get("unresolved_model_scene_count", -1)) != 0:
        raise LearnerFacingPedagogicalCloseoutError("R5_UNRESOLVED_MODEL_SCENES")
    for key in ("source_text_exported", "questionbank_modified", "scene_semantics_modified", "new_scene_authored"):
        if report.get(key) is not False:
            raise LearnerFacingPedagogicalCloseoutError(f"R5_BOUNDARY_INVALID:{key}")


def _review_form(form: Mapping[str, Any]) -> dict[str, Any]:
    ordinal = int(form.get("form_ordinal", 0))
    if ordinal < 1 or ordinal > EXPECTED_FORM_COUNT:
        raise LearnerFacingPedagogicalCloseoutError(f"FORM_ORDINAL_INVALID:{ordinal}")
    if int(form.get("error_count", -1)) != 0:
        raise LearnerFacingPedagogicalCloseoutError(f"FORM_NOT_CLEAN:F{ordinal:02d}")
    expected_support = _expected_support(ordinal)
    exposures = list(form.get("scene_exposures") or [])
    if len(exposures) != 4:
        raise LearnerFacingPedagogicalCloseoutError(
            f"FORM_SCENE_EXPOSURE_COUNT_INVALID:F{ordinal:02d}:{len(exposures)}"
        )
    for exposure in exposures:
        supports = list(exposure.get("support_levels") or [])
        if supports != [expected_support]:
            raise LearnerFacingPedagogicalCloseoutError(
                f"FORM_SUPPORT_PROGRESS_DRIFT:F{ordinal:02d}:{supports}:{expected_support}"
            )
        if int(exposure.get("richer_language_asset_activity_count", 0)) < 1:
            raise LearnerFacingPedagogicalCloseoutError(
                f"FORM_RICH_LANGUAGE_ASSET_MISSING:F{ordinal:02d}:{exposure.get('scene_ref_id')}"
            )
        if int(exposure.get("learner_visible_stimulus_duplicate_count", -1)) != 0:
            raise LearnerFacingPedagogicalCloseoutError(
                f"FORM_LEARNER_VISIBLE_DUPLICATE:F{ordinal:02d}:{exposure.get('scene_ref_id')}"
            )
    student = form.get("student_form") or {}
    if int(student.get("scene_count", -1)) != 4:
        raise LearnerFacingPedagogicalCloseoutError(f"FORM_SCENE_COUNT_INVALID:F{ordinal:02d}")
    if int(student.get("learner_visible_activity_count", -1)) != 20:
        raise LearnerFacingPedagogicalCloseoutError(f"FORM_ACTIVITY_COUNT_INVALID:F{ordinal:02d}")
    if dict(student.get("skill_counts") or {}) != EXPECTED_SKILL_COUNTS:
        raise LearnerFacingPedagogicalCloseoutError(f"FORM_SKILL_COUNTS_INVALID:F{ordinal:02d}")
    semantic = form.get("semantic_e2e") or {}
    if int(semantic.get("error_count", -1)) != 0:
        raise LearnerFacingPedagogicalCloseoutError(f"FORM_SEMANTIC_E2E_NOT_CLEAN:F{ordinal:02d}")
    cross = form.get("cross_layer_preservation") or {}
    if int(cross.get("error_count", -1)) != 0:
        raise LearnerFacingPedagogicalCloseoutError(f"FORM_CROSS_LAYER_NOT_CLEAN:F{ordinal:02d}")
    return {
        "form_ordinal": ordinal,
        "form_id": str(form.get("form_id") or f"U01-FORM-{ordinal:02d}"),
        "support_level": expected_support,
        "scene_count": 4,
        "learner_visible_activity_count": 20,
        "skill_counts": dict(EXPECTED_SKILL_COUNTS),
        "pedagogical_review_status": "PASS",
    }


def materialize_closeout(*, r4_report_path: Path, r5_report_path: Path, output: Path) -> dict[str, Any]:
    r4_report_path = Path(r4_report_path).resolve(strict=True)
    r5_report_path = Path(r5_report_path).resolve(strict=True)
    r4_report = _load_json(r4_report_path)
    r5_report = _load_json(r5_report_path)
    r4_sha = _file_sha256(r4_report_path)
    r5_sha = _file_sha256(r5_report_path)
    _validate_r4(r4_report)
    _validate_r5(r5_report, r4_report_sha256=r4_sha, r4_report=r4_report)

    forms = list(r4_report.get("forms") or [])
    if len(forms) != EXPECTED_FORM_COUNT:
        raise LearnerFacingPedagogicalCloseoutError("R4_FORM_RECORD_COUNT_INVALID")
    form_reviews = [_review_form(form) for form in forms]
    if [row["form_ordinal"] for row in form_reviews] != list(range(1, EXPECTED_FORM_COUNT + 1)):
        raise LearnerFacingPedagogicalCloseoutError("FORM_SEQUENCE_INVALID")

    for row in r4_report.get("reused_scene_reports") or []:
        if int(row.get("selected_item_overlap_count", -1)) != 0:
            raise LearnerFacingPedagogicalCloseoutError(
                f"REUSED_SCENE_ITEM_OVERLAP:{row.get('scene_ref_id')}"
            )
        if row.get("task_angle_changed") is not True:
            raise LearnerFacingPedagogicalCloseoutError(
                f"REUSED_SCENE_TASK_ANGLE_NOT_CHANGED:{row.get('scene_ref_id')}"
            )
        if row.get("support_level_changed") is not True:
            raise LearnerFacingPedagogicalCloseoutError(
                f"REUSED_SCENE_SUPPORT_NOT_CHANGED:{row.get('scene_ref_id')}"
            )

    support_counts = {
        support: sum(row["support_level"] == support for row in form_reviews)
        for support in u09.SUPPORT_PROFILES
    }
    expected_support_counts = {support: 3 for support in u09.SUPPORT_PROFILES}
    if support_counts != expected_support_counts:
        raise LearnerFacingPedagogicalCloseoutError(
            f"SUPPORT_BAND_COUNTS_INVALID:{support_counts}:{expected_support_counts}"
        )

    result = {
        "schema_version": "a1fs.v1.u01qb18g.unit01_learner_facing_pedagogical_closeout.v1",
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "r4_report_sha256": r4_sha,
        "r5_report_sha256": r5_sha,
        "form_count": EXPECTED_FORM_COUNT,
        "scene_exposure_count": EXPECTED_SCENE_EXPOSURES,
        "learner_visible_activity_count": EXPECTED_LEARNER_ACTIVITIES,
        "runtime_item_count": EXPECTED_RUNTIME_ITEMS,
        "base_item_count": EXPECTED_BASE_ITEMS,
        "real62_extension_item_count": EXPECTED_REAL62_EXTENSION_ITEMS,
        "canonical_scene_count": EXPECTED_CANONICAL_SCENES,
        "unit01_runtime_bindable_scene_count": EXPECTED_BINDABLE_SCENES,
        "deferred_scene_refs": list(EXPECTED_DEFERRED_REFS),
        "reconciled_model_scene_count": EXPECTED_MODEL_SCENES,
        "unresolved_model_scene_count": 0,
        "support_band_form_counts": support_counts,
        "form_reviews": form_reviews,
        "reused_scene_count": int(r4_report.get("reused_scene_count", 0)),
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "new_scene_authored": False,
        "source_text_exported": False,
        "production_database_modified": False,
        "second_runtime_created": False,
        "second_planner_created": False,
        "second_matcher_created": False,
        "second_scoring_authority_created": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "unit01_closeout_complete": True,
        "next_short_step": NEXT_SHORT_STEP,
        "next_short_step_scope": NEXT_SHORT_STEP_SCOPE,
    }
    _write_private(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r4-report", type=Path, default=DEFAULT_R4_REPORT)
    parser.add_argument("--r5-report", type=Path, default=DEFAULT_R5_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        value = materialize_closeout(
            r4_report_path=args.r4_report,
            r5_report_path=args.r5_report,
            output=args.output,
        )
    except (LearnerFacingPedagogicalCloseoutError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"STATUS={FAIL_STATUS}")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={value['validation_status']}")
    print(f"FORMS={value['form_count']}")
    print(f"SCENE_EXPOSURES={value['scene_exposure_count']}")
    print(f"LEARNER_ACTIVITIES={value['learner_visible_activity_count']}")
    print(f"CANONICAL_SCENES={value['canonical_scene_count']}")
    print(f"UNIT01_BINDABLE_SCENES={value['unit01_runtime_bindable_scene_count']}")
    print(f"RECONCILED_MODEL_SCENES={value['reconciled_model_scene_count']}")
    print(f"UNIT01_CLOSEOUT_COMPLETE={value['unit01_closeout_complete']}")
    print(f"OUTPUT={Path(args.output).resolve()}")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    print(f"NEXT_SHORT_STEP_SCOPE={value['next_short_step_scope']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
