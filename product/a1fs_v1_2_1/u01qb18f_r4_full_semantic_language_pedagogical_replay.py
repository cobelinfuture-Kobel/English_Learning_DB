#!/usr/bin/env python3
"""Replay Forms01..12 with canonical scene + language preservation gates.

R4 delegates the existing U01QB18F replay rather than creating another runtime.
It adds R2/R3 authority and cross-layer checks around the same disposable SQLite
snapshot and the same U01QB13/U16C/U18C/U18E product path.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from product import a1fs_v1_2_1 as _product_package  # noqa: F401
from product.a1fs_v1_2_1 import u01qb18a_form01_fresh_learner_materialization_export as u18a
from product.a1fs_v1_2_1 import u01qb18f_twelve_form_semantic_lineage_replay as base
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as authority
from ulga.builders import _u01qb18f_r3_micro_scene_cross_layer_consumer_cutover_adapter as cross_layer

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private operator replay wrapper around the existing U01QB18F disposable-snapshot "
    "runner. It adds read-only canonical scene/language and cross-layer gates, authors "
    "no content, changes no QuestionBank, selector, runtime, planner, learner database "
    "or scoring authority, modifies no Unit02-24 content, enables no audio/Speaking "
    "score, and unlocks no A2."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4_ActualTwelveFormFullSemanticLanguagePedagogicalReplay"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4_FULL_SEMANTIC_LANGUAGE_PEDAGOGICAL_REPLAY"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18F_R4_FULL_SEMANTIC_LANGUAGE_PEDAGOGICAL_REPLAY"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F-R5_Unit01PrivateReal62SeedProvenanceReconciliationFullFix"
DEFAULT_LEARNER_ID = "U01_FORMS01_12_FULL_SEMANTIC_LANGUAGE_REPLAY"
DEFAULT_OUTPUT = Path(".local/a1fs_v1/review/unit01_forms01_12_full_semantic_language_replay.json")


class FullSemanticLanguageReplayError(ValueError):
    pass


_ORIGINAL_FORM_RECORD = base._form_record


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
