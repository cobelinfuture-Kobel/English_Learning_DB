"""Cut Unit01 product consumers over to the canonical micro-scene resolver.

R3 does not replace U01QB13/U16C/U18C/U18E ownership.  It replaces only the
scene semantic lookup dependency they consume in the product path, and adds a
fail-closed cross-layer preservation gate for the 240-activity Unit01 blueprint
and learner-facing Form payloads.
"""
from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as semantic
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as authority
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as u14r1

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Product-scoped reference cutover to the R2 read-only canonical Unit01 micro-scene "
    "resolver. It preserves U01QB13/U16C/U18C/U18E public ownership, authors no learner "
    "content, changes no QuestionBank denominator, creates no second selector/runtime/"
    "planner/database/scoring authority, modifies no Unit02-24 content, enables no audio/"
    "Speaking score, and unlocks no A2."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R3_Unit01MicroSceneCrossLayerFailClosedConsumerCutover"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R3_MICRO_SCENE_CROSS_LAYER_CONSUMER_CUTOVER"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18F_R3_MICRO_SCENE_CROSS_LAYER_CONSUMER_CUTOVER"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F-R4_ActualTwelveFormFullSemanticLanguagePedagogicalReplay"
EXPECTED_BLUEPRINT_ACTIVITIES = 240
EXPECTED_SCENE_EXPOSURES = 48
EXPECTED_DISTINCT_RUNTIME_SCENES = 31
EXPECTED_SKILL_COUNTS = {"READING": 96, "WRITING": 96, "SPEAKING": 48}

_ORIGINAL_U13_SCENE_INDEX = u13._scene_semantic_index
_ORIGINAL_U14R1_TOLERANT_SCENE_INDEX = u14r1.tolerant_scene_semantic_index
_ORIGINAL_SEMANTIC_SCENE_AUTHORITY = semantic.scene_authority
_ORIGINAL_SEMANTIC_FIDELITY = semantic.semantic_fidelity
_INSTALLED = False


class MicroSceneCrossLayerCutoverError(ValueError):
    """Fail-closed consumer cutover or preservation error."""


def _projection_refs(projection: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for name in (
        "eligible_vocabulary_refs",
        "eligible_chunk_refs",
        "eligible_context_phrase_refs",
        "eligible_sentence_refs",
        "eligible_egp_refs",
        "eligible_pattern_refs",
    ):
        refs.update(str(row) for row in projection.get(name) or [] if str(row))
    return refs


def _item_lineage_refs(lineage: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for name in ("vocabulary_refs", "chunk_refs", "sentence_refs", "pattern_refs"):
        refs.update(str(row) for row in lineage.get(name) or [] if str(row))
    return refs


def semantic_fidelity_with_unit_language_projection(
    *,
    scene_ref_id: str,
    semantics: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    """Extend existing U18E fidelity without making any illegal candidate legal."""
    value = _ORIGINAL_SEMANTIC_FIDELITY(
        scene_ref_id=scene_ref_id,
        semantics=semantics,
        item=item,
    )
    projection = semantics.get("unit_language_projection")
    if not isinstance(projection, Mapping):
        raise MicroSceneCrossLayerCutoverError(
            f"UNIT_LANGUAGE_PROJECTION_MISSING:{scene_ref_id}"
        )
    allowed_refs = _projection_refs(projection)
    item_refs = _item_lineage_refs(value.get("language_asset_lineage") or {})
    overlap = sorted(allowed_refs & item_refs)
    # Legacy base-bank rows may have no explicit authority refs. They remain legal
    # only when the existing semantic noun binding already passes. Richly-linked
    # rows are expected to overlap the scene's Unit01 projection; a mismatch is
    # demoted, never promoted.
    compatible = bool(overlap) if item_refs else bool(value.get("noun_bound"))
    value["unit_language_projection_compatible"] = compatible
    value["unit_language_projection_overlap_refs"] = overlap
    value["unit_language_projection_ref_count"] = len(allowed_refs)
    value["selected_item_language_ref_count"] = len(item_refs)
    value["unit_language_projection_gap_codes"] = list(
        projection.get("projection_gap_codes") or []
    )
    if item_refs and not compatible:
        value["tier"] = max(int(value.get("tier", 5)), 4)
        value["mode"] = "LANGUAGE_PROJECTION_MISMATCH"
    return value


def _required_package_errors(ref: str, package: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    core = package.get("scene_core")
    if not isinstance(core, Mapping):
        return [f"SCENE_CORE_MISSING:{ref}"]
    for field in (
        "setting", "participants", "objects", "actions", "relations",
        "information_structure", "communicative_function_ids",
    ):
        value = core.get(field)
        if field == "setting":
            if not str(value or ""):
                errors.append(f"SCENE_CORE_FIELD_MISSING:{ref}:{field}")
        elif not isinstance(value, list) or not value:
            errors.append(f"SCENE_CORE_FIELD_MISSING:{ref}:{field}")
    if not str(package.get("communicative_goal") or ""):
        errors.append(f"COMMUNICATIVE_GOAL_MISSING:{ref}")
    lineage = package.get("source_lineage")
    if not isinstance(lineage, Mapping) or not str(lineage.get("lineage_mode") or ""):
        errors.append(f"SOURCE_LINEAGE_MISSING:{ref}")
    projection = package.get("unit_language_projection")
    if not isinstance(projection, Mapping):
        errors.append(f"UNIT_LANGUAGE_PROJECTION_MISSING:{ref}")
    else:
        if not projection.get("eligible_egp_refs"):
            errors.append(f"ELIGIBLE_EGP_REFS_MISSING:{ref}")
        if not projection.get("eligible_pattern_refs"):
            errors.append(f"ELIGIBLE_PATTERN_REFS_MISSING:{ref}")
        if package.get("unit_runtime_bindable") is True and not projection.get("eligible_vocabulary_refs"):
            errors.append(f"ELIGIBLE_VOCABULARY_REFS_MISSING:{ref}")
    return errors


def validate_blueprint_database(database: Path) -> dict[str, Any]:
    """Validate all 240 activities dereference the same 32-scene authority."""
    database = Path(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT activity_id,form_ordinal,scene_ref_id,skill,task_angle,support_level
               FROM u01qb13_blueprint_activities
               ORDER BY form_ordinal,activity_id"""
        ).fetchall()
    errors: list[str] = []
    skill_counts: Counter[str] = Counter()
    exposure_keys: set[tuple[int, str]] = set()
    scene_refs: set[str] = set()
    package_errors_seen: set[str] = set()
    richer_gap_refs: set[str] = set()
    for row in rows:
        activity_id = str(row["activity_id"])
        ref = str(row["scene_ref_id"])
        try:
            package = authority.canonical_scene_package(ref)
        except authority.CanonicalMicroSceneAuthorityError:
            errors.append(f"BLUEPRINT_SCENE_REF_NOT_DEREFERENCEABLE:{activity_id}:{ref}")
            continue
        if package.get("unit_runtime_bindable") is not True:
            errors.append(f"DEFERRED_SCENE_LEAKED_INTO_BLUEPRINT:{activity_id}:{ref}")
        for error in _required_package_errors(ref, package):
            if error not in package_errors_seen:
                package_errors_seen.add(error)
                errors.append(error)
        projection = package.get("unit_language_projection") or {}
        if "RICHER_LANGUAGE_ASSET_REF_MISSING" in (projection.get("projection_gap_codes") or []):
            richer_gap_refs.add(ref)
        if not str(row["task_angle"] or ""):
            errors.append(f"BLUEPRINT_TASK_ANGLE_MISSING:{activity_id}")
        if not str(row["support_level"] or ""):
            errors.append(f"BLUEPRINT_SUPPORT_LEVEL_MISSING:{activity_id}")
        skill_counts[str(row["skill"])] += 1
        exposure_keys.add((int(row["form_ordinal"]), ref))
        scene_refs.add(ref)

    if len(rows) != EXPECTED_BLUEPRINT_ACTIVITIES:
        errors.append(f"BLUEPRINT_ACTIVITY_COUNT_INVALID:{len(rows)}:{EXPECTED_BLUEPRINT_ACTIVITIES}")
    if len(exposure_keys) != EXPECTED_SCENE_EXPOSURES:
        errors.append(f"BLUEPRINT_SCENE_EXPOSURE_COUNT_INVALID:{len(exposure_keys)}:{EXPECTED_SCENE_EXPOSURES}")
    if len(scene_refs) != EXPECTED_DISTINCT_RUNTIME_SCENES:
        errors.append(f"BLUEPRINT_DISTINCT_SCENE_COUNT_INVALID:{len(scene_refs)}:{EXPECTED_DISTINCT_RUNTIME_SCENES}")
    if dict(skill_counts) != EXPECTED_SKILL_COUNTS:
        errors.append(f"BLUEPRINT_SKILL_COUNTS_INVALID:{dict(skill_counts)}:{EXPECTED_SKILL_COUNTS}")

    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "blueprint_activity_count": len(rows),
        "scene_exposure_count": len(exposure_keys),
        "distinct_runtime_scene_count": len(scene_refs),
        "skill_counts": dict(skill_counts),
        "all_blueprint_scene_refs_dereferenceable": not any(
            error.startswith("BLUEPRINT_SCENE_REF_NOT_DEREFERENCEABLE") for error in errors
        ),
        "richer_language_projection_gap_scene_count": len(richer_gap_refs),
        "richer_language_projection_gap_scene_refs": sorted(richer_gap_refs),
        "questionbank_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_form_cross_layer(
    skill_payloads: Mapping[str, Mapping[str, Any]],
    blueprint_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate final learner payloads can recover full scene authority by reference."""
    selected: dict[str, Mapping[str, Any]] = {}
    for payload in skill_payloads.values():
        for item in payload.get("items") or []:
            activity_id = str(item.get("activity_id") or "")
            if not activity_id or activity_id in selected:
                raise MicroSceneCrossLayerCutoverError(
                    f"FORM_ACTIVITY_DUPLICATE_OR_MISSING:{activity_id}"
                )
            selected[activity_id] = item

    errors: list[str] = []
    by_scene: dict[str, list[str]] = defaultdict(list)
    richer_gap_refs: set[str] = set()
    for blueprint in blueprint_rows:
        activity_id = str(blueprint.get("activity_id") or "")
        ref = str(blueprint.get("scene_ref_id") or "")
        item = selected.get(activity_id)
        if item is None:
            errors.append(f"LEARNER_ACTIVITY_MISSING:{activity_id}")
            continue
        try:
            package = authority.canonical_scene_package(ref)
        except authority.CanonicalMicroSceneAuthorityError:
            errors.append(f"LEARNER_SCENE_REF_NOT_DEREFERENCEABLE:{activity_id}:{ref}")
            continue
        errors.extend(_required_package_errors(ref, package))
        lineage = item.get("semantic_lineage")
        if not isinstance(lineage, Mapping):
            errors.append(f"LEARNER_SEMANTIC_LINEAGE_MISSING:{activity_id}")
            continue
        if str(lineage.get("scene_ref_id") or "") != ref:
            errors.append(f"LEARNER_SCENE_REF_DRIFT:{activity_id}:{lineage.get('scene_ref_id')}:{ref}")
        fidelity = lineage.get("selection_fidelity")
        if not isinstance(fidelity, Mapping):
            errors.append(f"LEARNER_SELECTION_FIDELITY_MISSING:{activity_id}")
        else:
            if fidelity.get("noun_bound") is not True:
                errors.append(f"LEARNER_SCENE_NOUN_UNBOUND:{activity_id}:{ref}")
            if fidelity.get("unit_language_projection_compatible") is not True:
                errors.append(f"LEARNER_LANGUAGE_PROJECTION_MISMATCH:{activity_id}:{ref}")
        if not str(blueprint.get("skill") or ""):
            errors.append(f"LEARNER_SKILL_BINDING_MISSING:{activity_id}")
        if not str(blueprint.get("task_angle") or ""):
            errors.append(f"LEARNER_TASK_ANGLE_BINDING_MISSING:{activity_id}")
        if not str(blueprint.get("support_level") or ""):
            errors.append(f"LEARNER_SUPPORT_BINDING_MISSING:{activity_id}")
        projection = package.get("unit_language_projection") or {}
        if "RICHER_LANGUAGE_ASSET_REF_MISSING" in (projection.get("projection_gap_codes") or []):
            richer_gap_refs.add(ref)
        by_scene[ref].append(activity_id)

    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "activity_count": len(selected),
        "scene_count": len(by_scene),
        "full_scene_authority_dereference_count": len(by_scene),
        "richer_language_projection_gap_scene_count": len(richer_gap_refs),
        "richer_language_projection_gap_scene_refs": sorted(richer_gap_refs),
        "questionbank_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def install() -> None:
    """Install only semantic lookup/reference dependencies in the product path."""
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if u13._scene_semantic_index is not _ORIGINAL_U13_SCENE_INDEX:
        raise MicroSceneCrossLayerCutoverError("U01QB13_SCENE_INDEX_ALREADY_PATCHED")
    if u14r1.tolerant_scene_semantic_index is not _ORIGINAL_U14R1_TOLERANT_SCENE_INDEX:
        raise MicroSceneCrossLayerCutoverError("U01QB14R1_SCENE_INDEX_ALREADY_PATCHED")
    if semantic.scene_authority is not _ORIGINAL_SEMANTIC_SCENE_AUTHORITY:
        raise MicroSceneCrossLayerCutoverError("U01QB18E_SCENE_AUTHORITY_ALREADY_PATCHED")
    if semantic.semantic_fidelity is not _ORIGINAL_SEMANTIC_FIDELITY:
        raise MicroSceneCrossLayerCutoverError("U01QB18E_SEMANTIC_FIDELITY_ALREADY_PATCHED")

    authority.require_authority_pass()
    u13._scene_semantic_index = authority.tolerant_scene_semantic_index
    u14r1.tolerant_scene_semantic_index = authority.tolerant_scene_semantic_index
    semantic.scene_authority = authority
    semantic.semantic_fidelity = semantic_fidelity_with_unit_language_projection
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and u13._scene_semantic_index is authority.tolerant_scene_semantic_index
        and u14r1.tolerant_scene_semantic_index is authority.tolerant_scene_semantic_index
        and semantic.scene_authority is authority
        and semantic.semantic_fidelity is semantic_fidelity_with_unit_language_projection
    )
