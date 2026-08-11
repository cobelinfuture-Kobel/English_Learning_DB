#!/usr/bin/env python3
"""Replay Forms01..12 with canonical scene + language preservation gates.

R4 delegates the existing U01QB18F replay rather than creating another runtime.
It adds R2/R3 authority and cross-layer checks around the same disposable SQLite
snapshot and the same U01QB13/U16C/U18C/U18E product path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from product import a1fs_v1_2_1 as _product_package  # noqa: F401
from product.a1fs_v1_2_1 import u01qb18a_form01_fresh_learner_materialization_export as u18a
from product.a1fs_v1_2_1 import u01qb18f_twelve_form_semantic_lineage_replay as base
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as authority
from ulga.builders import _u01qb18f_r3_micro_scene_cross_layer_consumer_cutover_adapter as cross_layer
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private operator replay wrapper around the existing U01QB18F disposable-snapshot "
    "runner. It adds read-only canonical scene/language and cross-layer gates plus "
    "read-only candidate-funnel diagnostics on binding failure, authors no content, "
    "changes no QuestionBank, selector, runtime, planner, learner database or scoring "
    "authority, modifies no Unit02-24 content, enables no audio/Speaking score, and "
    "unlocks no A2."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4_ActualTwelveFormFullSemanticLanguagePedagogicalReplay"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4_FULL_SEMANTIC_LANGUAGE_PEDAGOGICAL_REPLAY"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18F_R4_FULL_SEMANTIC_LANGUAGE_PEDAGOGICAL_REPLAY"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F-R5_Unit01PrivateReal62SeedProvenanceReconciliationFullFix"
DEFAULT_LEARNER_ID = "U01_FORMS01_12_FULL_SEMANTIC_LANGUAGE_REPLAY"
DEFAULT_OUTPUT = Path(".local/a1fs_v1/review/unit01_forms01_12_full_semantic_language_replay.json")
_BINDING_GAP_PREFIX = "SCENE_TASK_RUNTIME_BINDING_GAP:"


class FullSemanticLanguageReplayError(ValueError):
    pass


_ORIGINAL_FORM_RECORD = base._form_record


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _binding_gap_activity_id(error: Any) -> str:
    text = str(error)
    if not text.startswith(_BINDING_GAP_PREFIX):
        return ""
    tail = text[len(_BINDING_GAP_PREFIX) :]
    activity_id = tail.split(":", 1)[0].strip()
    return activity_id if activity_id else ""


def binding_gap_diagnostic(database: Path, activity_id: str) -> dict[str, Any]:
    """Explain one formal selector zero-candidate failure without mutating SQLite.

    The funnel mirrors the active product matcher predicates while keeping each
    rejection dimension separate: family, canonical scoring class, learner-text
    quality, then scene lexical/context compatibility. U18E/R3 semantic logic is a
    rank-only overlay at this point and therefore cannot create a zero-candidate
    activity after these predicates pass.
    """
    database = Path(database).resolve(strict=True)
    before = _sha256_file(database)
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        activity_row = connection.execute(
            """SELECT activity_id,form_ordinal,scene_ref_id,situation_family,setting,
                      skill,task_angle,support_level,scored,assessment_candidate,
                      pattern_family_ids_json,scene_anchors_json
               FROM u01qb13_blueprint_activities WHERE activity_id=?""",
            (str(activity_id),),
        ).fetchone()
        if activity_row is None:
            raise FullSemanticLanguageReplayError(
                f"BINDING_GAP_ACTIVITY_NOT_FOUND:{activity_id}"
            )
        activity = dict(activity_row)
        skill = str(activity["skill"])
        allowed_families = {
            str(value)
            for value in json.loads(str(activity["pattern_family_ids_json"]))
        }
        anchors = {
            str(value).casefold()
            for value in json.loads(str(activity["scene_anchors_json"]))
        }
        catalog = [
            dict(row)
            for row in connection.execute(
                """SELECT c.item_id,c.asset_key,c.skill,c.pattern_family_id,
                          c.private_item_json,c.capture_enabled,r.contract_json
                   FROM u01qb02_item_catalog c
                   LEFT JOIN response_contracts r ON r.asset_key=c.asset_key
                   WHERE c.skill=? ORDER BY c.item_id""",
                (skill,),
            )
        ]
    finally:
        connection.close()

    required_class = matching.required_activity_scoring_class(activity)
    scoring_classes = {
        str(row["item_id"]): matching.scoring_class_from_contract_json(
            row.get("contract_json"),
            capture_enabled=bool(row.get("capture_enabled")),
        )
        for row in catalog
    }
    family_rows = [
        row for row in catalog if str(row["pattern_family_id"]) in allowed_families
    ]
    scoring_rows = [
        row
        for row in family_rows
        if quality._ORIGINAL_CANDIDATE_PRESERVES_SCORING_CLASS(
            activity,
            row,
            scoring_classes,
        )
    ]
    anchor_context_rows = [
        row
        for row in scoring_rows
        if u13._candidate_rank(
            row=row,
            anchors=anchors,
            situation_family=str(activity["situation_family"]),
            learner_id="R4_BINDING_DIAGNOSTIC",
            session_id="R4_BINDING_DIAGNOSTIC",
            activity_id=str(activity_id),
            exposed=set(),
            recent=set(),
            assessment=bool(activity["assessment_candidate"]),
        )
        is not None
    ]
    learner_quality_rows = [
        row
        for row in scoring_rows
        if quality.runtime_catalog_row_learner_quality_ok(row)
    ]
    final_rows = [
        row
        for row in learner_quality_rows
        if u13._candidate_rank(
            row=row,
            anchors=anchors,
            situation_family=str(activity["situation_family"]),
            learner_id="R4_BINDING_DIAGNOSTIC",
            session_id="R4_BINDING_DIAGNOSTIC",
            activity_id=str(activity_id),
            exposed=set(),
            recent=set(),
            assessment=bool(activity["assessment_candidate"]),
        )
        is not None
    ]

    if not family_rows:
        root_cause = "PATTERN_FAMILY_CAPACITY_ZERO"
    elif not scoring_rows:
        root_cause = "SCORING_CLASS_CAPACITY_ZERO"
    elif not anchor_context_rows:
        root_cause = "SCENE_ANCHOR_OR_CONTEXT_CAPACITY_ZERO"
    elif not learner_quality_rows:
        root_cause = "LEARNER_QUALITY_CAPACITY_ZERO"
    elif not final_rows:
        root_cause = "COMBINED_SCENE_CONTEXT_AND_LEARNER_QUALITY_CAPACITY_ZERO"
    else:
        root_cause = "PER_ACTIVITY_CAPACITY_PRESENT_CHECK_FORM_LEVEL_MATCHING"

    after = _sha256_file(database)
    return {
        "diagnostic_status": "PASS_R4_BINDING_GAP_DIAGNOSTIC",
        "activity_id": str(activity["activity_id"]),
        "form_ordinal": int(activity["form_ordinal"]),
        "scene_ref_id": str(activity["scene_ref_id"]),
        "situation_family": str(activity["situation_family"]),
        "setting": str(activity["setting"]),
        "skill": skill,
        "task_angle": str(activity["task_angle"]),
        "support_level": str(activity["support_level"]),
        "required_scoring_class": required_class,
        "allowed_pattern_family_ids": sorted(allowed_families),
        "scene_anchors": sorted(anchors),
        "skill_catalog_count": len(catalog),
        "family_candidate_count": len(family_rows),
        "scoring_class_candidate_count": len(scoring_rows),
        "scene_anchor_context_candidate_count": len(anchor_context_rows),
        "learner_quality_candidate_count": len(learner_quality_rows),
        "formal_candidate_count": len(final_rows),
        "family_runtime_scoring_class_counts": {
            value: sum(scoring_classes[str(row["item_id"])] == value for row in family_rows)
            for value in (
                matching.SCORING_CLASS_AUTO,
                matching.SCORING_CLASS_HUMAN_REVIEW,
                matching.SCORING_CLASS_PRACTICE_ONLY,
                matching.SCORING_CLASS_UNKNOWN,
            )
        },
        "root_cause": root_cause,
        "u18e_r3_selector_effect": "RANK_ONLY_NOT_ZERO_CANDIDATE_FILTER",
        "database_modified": before != after,
    }


def _print_binding_gap_diagnostic(report: Mapping[str, Any]) -> None:
    print(f"BINDING_GAP_DIAGNOSTIC_STATUS={report['diagnostic_status']}")
    print(f"BINDING_GAP_ACTIVITY_ID={report['activity_id']}")
    print(f"BINDING_GAP_FORM={report['form_ordinal']}")
    print(f"BINDING_GAP_SCENE_REF={report['scene_ref_id']}")
    print(f"BINDING_GAP_SITUATION_FAMILY={report['situation_family']}")
    print(f"BINDING_GAP_SETTING={report['setting']}")
    print(f"BINDING_GAP_SKILL={report['skill']}")
    print(f"BINDING_GAP_TASK_ANGLE={report['task_angle']}")
    print(f"BINDING_GAP_SUPPORT={report['support_level']}")
    print(f"BINDING_GAP_REQUIRED_SCORING_CLASS={report['required_scoring_class']}")
    print("BINDING_GAP_ALLOWED_FAMILIES=" + ",".join(report["allowed_pattern_family_ids"]))
    print("BINDING_GAP_SCENE_ANCHORS=" + ",".join(report["scene_anchors"]))
    print(f"BINDING_GAP_SKILL_CATALOG_COUNT={report['skill_catalog_count']}")
    print(f"BINDING_GAP_FAMILY_CANDIDATES={report['family_candidate_count']}")
    print(f"BINDING_GAP_SCORING_CLASS_CANDIDATES={report['scoring_class_candidate_count']}")
    print(f"BINDING_GAP_SCENE_ANCHOR_CONTEXT_CANDIDATES={report['scene_anchor_context_candidate_count']}")
    print(f"BINDING_GAP_LEARNER_QUALITY_CANDIDATES={report['learner_quality_candidate_count']}")
    print(f"BINDING_GAP_FORMAL_CANDIDATES={report['formal_candidate_count']}")
    print(f"BINDING_GAP_ROOT_CAUSE={report['root_cause']}")
    print(f"BINDING_GAP_DATABASE_MODIFIED={report['database_modified']}")


def _form_record_with_cross_layer(
    *,
    learner_id: str,
    form_ordinal: int,
    skill_payloads: Mapping[str, Mapping[str, Any]],
    blueprint_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    value = _ORIGINAL_FORM_RECORD(
        learner_id=learner_id,
        form_ordinal=form_ordinal,
        skill_payloads=skill_payloads,
        blueprint_rows=blueprint_rows,
    )
    report = cross_layer.validate_form_cross_layer(skill_payloads, blueprint_rows)
    errors = list(value.get("errors") or [])
    errors.extend(str(row) for row in report.get("errors") or [] if str(row) not in errors)
    value["cross_layer_preservation"] = report
    value["errors"] = errors
    value["error_count"] = len(errors)
    value["validation_status"] = base.PASS_STATUS if not errors else base.FAIL_STATUS
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def materialize_full_replay(
    *,
    database: Path,
    output: Path,
    learner_id: str = DEFAULT_LEARNER_ID,
) -> dict[str, Any]:
    database = Path(database).resolve(strict=True)
    output = Path(output).resolve()
    authority_report = authority.require_authority_pass()
    blueprint_report = cross_layer.validate_blueprint_database(database)

    previous = base._form_record
    base._form_record = _form_record_with_cross_layer
    try:
        value = base.materialize_twelve_form_replay(
            database=database,
            output=output,
            learner_id=learner_id,
        )
    finally:
        base._form_record = previous

    forms = value.get("forms") or []
    cross_pass_forms = sum(
        (row.get("cross_layer_preservation") or {}).get("validation_status")
        == cross_layer.PASS_STATUS
        for row in forms
    )
    errors = list(value.get("errors") or [])
    if authority_report.get("validation_status") != authority.PASS_STATUS:
        errors.append("CANONICAL_SCENE_AUTHORITY_NOT_PASS")
    if blueprint_report.get("validation_status") != cross_layer.PASS_STATUS:
        errors.append("BLUEPRINT_CROSS_LAYER_PRESERVATION_NOT_PASS")
    if cross_pass_forms != base.FORM_COUNT:
        errors.append(f"FORM_CROSS_LAYER_PASS_COUNT_INVALID:{cross_pass_forms}:{base.FORM_COUNT}")

    value["task_id"] = TASK_ID
    value["validation_status"] = PASS_STATUS if not errors else FAIL_STATUS
    value["error_count"] = len(errors)
    value["errors"] = errors
    value["canonical_scene_authority"] = authority_report
    value["blueprint_cross_layer_preservation"] = blueprint_report
    value["cross_layer_pass_form_count"] = cross_pass_forms
    value["next_short_step"] = NEXT_SHORT_STEP
    runtime_proof = value.get("runtime_proof") or {}
    runtime_proof["formal_selector"] = (
        "U01QB13/U01QB16C/U01QB18C/U01QB18E+U01QB18F-R2-R3_CANONICAL_SCENE_PRODUCT_PATH"
    )
    value["runtime_proof"] = runtime_proof
    u18a._assert_no_answer_leak(value)
    _write(output, value)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--learner-id", default=DEFAULT_LEARNER_ID)
    args = parser.parse_args(argv)
    try:
        value = materialize_full_replay(
            database=args.database,
            output=args.output,
            learner_id=str(args.learner_id),
        )
    except (
        FullSemanticLanguageReplayError,
        authority.CanonicalMicroSceneAuthorityError,
        cross_layer.MicroSceneCrossLayerCutoverError,
        base.TwelveFormReplayError,
        u18a.Form01MaterializationError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        print(f"STATUS={FAIL_STATUS}")
        print(f"ERROR={exc}")
        activity_id = _binding_gap_activity_id(exc)
        if activity_id:
            try:
                _print_binding_gap_diagnostic(
                    binding_gap_diagnostic(Path(args.database), activity_id)
                )
            except Exception as diagnostic_exc:
                print("BINDING_GAP_DIAGNOSTIC_STATUS=FAIL")
                print(f"BINDING_GAP_DIAGNOSTIC_ERROR={diagnostic_exc}")
        return 1

    scene = value["canonical_scene_authority"]
    blueprint = value["blueprint_cross_layer_preservation"]
    print(f"STATUS={value['validation_status']}")
    print(f"CANONICAL_SCENES={scene['canonical_scene_count']}")
    print(f"UNIT01_BINDABLE_SCENES={scene['unit01_runtime_bindable_scene_count']}")
    print("DEFERRED_SCENE_REFS=" + ",".join(scene["deferred_scene_refs"]))
    print(f"FORMS={value['form_count']}")
    print(f"SCENE_EXPOSURES={value['scene_exposure_count']}")
    print(f"BLUEPRINT_ACTIVITIES={blueprint['blueprint_activity_count']}")
    print(f"LEARNER_ACTIVITIES={value['learner_visible_activity_count']}")
    print(f"SEMANTIC_E2E_PASS_FORMS={value['semantic_e2e_pass_form_count']}")
    print(f"CROSS_LAYER_PASS_FORMS={value['cross_layer_pass_form_count']}")
    print(f"REUSED_SCENES={value['reused_scene_count']}")
    print(f"RUNTIME_ITEMS={value['runtime_proof']['runtime_item_count']}")
    print(f"REAL62_EXTENSION_ITEMS={value['runtime_proof']['real62_extension_item_count']}")
    print(f"SOURCE_PRODUCTION_DATABASE_MODIFIED={value['runtime_proof']['source_production_database_modified']}")
    print(f"OUTPUT={Path(args.output).resolve()}")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0 if value["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
