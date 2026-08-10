"""Canonical Unit01 micro-scene resolver and Unit01 language projection.

U01QB18F-R2 fixes the authority-loss boundary exposed by learner-facing Form01.
The approved Unit01 scene world is not re-authored here.  Instead, the existing
five canonical Unit01 contexts and the already-approved 27 U01QB07 model-authored
scene specifications are dereferenced into one read-only 32-scene authority.

Rotation/allocation/runtime layers may continue to store only ``scene_ref_id``.
Any consumer that needs scene meaning must dereference this module rather than
reconstructing a partial scene from downstream rows.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as u01qb01
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as u06
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u07

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only canonical resolver over the existing approved Unit01 five-context "
    "authority and U01QB07 model-authored scene specification.  It authors no learner "
    "content, changes no scene identity, QuestionBank item, selector, planner, learner "
    "database or scoring authority, modifies no Unit02-24 content, enables no audio/"
    "Speaking score, and unlocks no A2.  Unit01 language projection references only "
    "existing Vocabulary/Chunk/Sentence/Pattern/EGP authorities."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R2_Unit01CanonicalMicroSceneAuthorityPreservationAndLanguageProjectionFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R2_CANONICAL_MICRO_SCENE_AUTHORITY_FULLFIX"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18F_R2_CANONICAL_MICRO_SCENE_AUTHORITY_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F-R3_Unit01MicroSceneCrossLayerFailClosedConsumerCutover"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
EXPECTED_SCENE_COUNT = 32
EXPECTED_CANONICAL_CONTEXT_COUNT = 5
EXPECTED_MODEL_SCENE_COUNT = 27
EXPECTED_UNIT01_BINDABLE_COUNT = 31
EXPECTED_DEFERRED_REFS = ("U01-MA-FOOD-04",)
_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)


class CanonicalMicroSceneAuthorityError(ValueError):
    """Fail-closed canonical scene authority error."""


def _words(value: Any) -> set[str]:
    return {token.casefold() for token in _WORD_RE.findall(str(value or "").replace("_", " "))}


def _spec() -> dict[str, Any]:
    path = Path(u07.DEFAULT_SPEC)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalMicroSceneAuthorityError(f"SCENE_SUPPLEMENT_UNREADABLE:{exc}") from exc
    if not isinstance(value, dict):
        raise CanonicalMicroSceneAuthorityError("SCENE_SUPPLEMENT_OBJECT_REQUIRED")
    rows = u07.candidates(value)
    if len(rows) != EXPECTED_MODEL_SCENE_COUNT:
        raise CanonicalMicroSceneAuthorityError(
            f"MODEL_SCENE_COUNT_INVALID:{len(rows)}:{EXPECTED_MODEL_SCENE_COUNT}"
        )
    return value


def _active_unit01_nouns() -> set[str]:
    return {str(row["lemma"]).strip().casefold() for row in u01qb01.nouns() if str(row.get("lemma") or "").strip()}


def _canonical_context_rows() -> list[dict[str, Any]]:
    rows = [u06.canonical_context_scene_row(context) for context in s01.CONTEXTS]
    if len(rows) != EXPECTED_CANONICAL_CONTEXT_COUNT:
        raise CanonicalMicroSceneAuthorityError(
            f"CANONICAL_CONTEXT_COUNT_INVALID:{len(rows)}:{EXPECTED_CANONICAL_CONTEXT_COUNT}"
        )
    return rows


def _model_scene_rows() -> list[dict[str, Any]]:
    anchors = _canonical_context_rows()
    rows: list[dict[str, Any]] = []
    for candidate in u07.candidates(_spec()):
        # U01QB07 already admitted these candidates.  Re-running its deterministic
        # row materializer here preserves the full semantic core instead of the
        # later cumulative_unique_scenes summary projection.
        rows.append(u07.model_scene_row(candidate, anchors))
    return rows


def _unit01_bindability(package: Mapping[str, Any]) -> tuple[bool, list[str], str]:
    active = _active_unit01_nouns()
    core = package["scene_core"]
    object_words = {str(row).casefold() for row in core.get("objects") or []}
    setting_words = _words(core.get("setting"))
    anchors = sorted((object_words | setting_words) & active)
    if anchors:
        return True, anchors, "UNIT_ACTIVE_NOUN_ANCHOR_PRESENT"
    return False, [], "UNIT_ACTIVE_NOUN_ANCHOR_MISSING_DEFER_FOR_LATER_UNIT"


@lru_cache(maxsize=1)
def _language_authority() -> dict[str, Any]:
    scope, _unit, authority = s01.unit_authority_context()
    vocabulary, _unselected = s01.selected_vocabulary(scope)
    chunks = s01.selected_chunks(scope)
    phrases = s01.context_phrase_rows(chunks)
    sentences = s01.sentence_rows()
    return {
        "vocabulary": vocabulary,
        "chunks": chunks,
        "context_phrases": phrases,
        "sentences": sentences,
        "egp_refs": sorted(str(row) for row in authority["egp_row_ids"]),
        "pattern_refs": sorted(str(row["authority_id"]) for row in authority["patterns"]),
    }


def _label_words(row: Mapping[str, Any], key: str = "label") -> set[str]:
    return _words(row.get(key))


def _scene_language_projection(package: Mapping[str, Any]) -> dict[str, Any]:
    authority = _language_authority()
    core = package["scene_core"]
    lexical_words = set()
    for field in ("setting", "objects", "descriptors", "actions", "relations"):
        raw = core.get(field)
        if isinstance(raw, list):
            for value in raw:
                lexical_words.update(_words(value))
        else:
            lexical_words.update(_words(raw))
    lexical_words.update(_words(package.get("event")))
    lexical_words.update(_words(package.get("communicative_goal")))

    vocabulary_refs = sorted(
        str(row["authority_id"])
        for row in authority["vocabulary"]
        if _label_words(row) & lexical_words
    )
    chunk_refs = sorted(
        str(row["authority_id"])
        for row in authority["chunks"]
        if _label_words(row) and _label_words(row) <= lexical_words
    )
    context_phrase_refs = sorted(
        str(row["phrase_id"])
        for row in authority["context_phrases"]
        if _label_words(row) and _label_words(row) <= lexical_words
    )

    sentence_refs: list[str] = []
    ref = str(package["scene_ref_id"])
    object_words = set()
    for value in core.get("objects") or []:
        object_words.update(_words(value))
    semantic_signal_words = set()
    for value in (core.get("actions") or []) + (core.get("relations") or []):
        semantic_signal_words.update(_words(value))
    semantic_signal_words.update(_words(core.get("setting")))
    for sentence in authority["sentences"]:
        sentence_words = _words(sentence.get("text"))
        exact_context = str(sentence.get("context_id") or "") == ref
        object_hit = bool(sentence_words & object_words)
        semantic_hit = bool(sentence_words & semantic_signal_words)
        if exact_context or (object_hit and semantic_hit):
            sentence_refs.append(str(sentence["sentence_id"]))
    sentence_refs = sorted(set(sentence_refs))

    gaps: list[str] = []
    if not vocabulary_refs and package.get("unit_runtime_bindable") is True:
        gaps.append("ELIGIBLE_VOCABULARY_REF_MISSING")
    if not chunk_refs and not context_phrase_refs and not sentence_refs:
        gaps.append("RICHER_LANGUAGE_ASSET_REF_MISSING")

    return {
        "unit_id": UNIT_ID,
        "eligible_vocabulary_refs": vocabulary_refs,
        "eligible_chunk_refs": chunk_refs,
        "eligible_context_phrase_refs": context_phrase_refs,
        "eligible_sentence_refs": sentence_refs,
        "eligible_content_asset_refs": [],
        "eligible_egp_refs": list(authority["egp_refs"]),
        "eligible_pattern_refs": list(authority["pattern_refs"]),
        "content_asset_projection_status": "RUNTIME_SELECTED_ITEM_LINEAGE_ONLY",
        "projection_gap_codes": gaps,
        "projection_source": "EXISTING_UNIT01_LANGUAGE_AUTHORITIES_ONLY",
    }


def _canonical_package(context: Mapping[str, Any], scene_row: Mapping[str, Any]) -> dict[str, Any]:
    core = deepcopy(dict(scene_row["semantic_scene_core"]))
    package = {
        "scene_ref_id": str(scene_row["scene_ref_id"]),
        "scene_origin": "CANONICAL_UNIT01_CONTEXT",
        "situation_family": str(scene_row["situation_family"]),
        "setting": str(core["setting"]),
        "event": str(context.get("title") or ""),
        "scene_core": core,
        "communicative_goal": "IDENTIFY_AND_DESCRIBE_REFERENTS",
        "semantic_scene_signature_v2": str(scene_row["semantic_scene_signature_v2"]),
        "source_lineage": {
            "lineage_mode": "EXISTING_UNIT01_CONTEXT_AUTHORITY",
            "source_authority": str(context.get("source_role") or ""),
            "source_context_id": str(context["context_id"]),
            "source_role": str(context.get("role") or ""),
            "source_equivalence_claimed": True,
        },
    }
    bindable, anchors, reason = _unit01_bindability(package)
    package["unit_runtime_bindable"] = bindable
    package["anchors"] = anchors
    package["runtime_bindability_gate_reason"] = reason
    package["unit_language_projection"] = _scene_language_projection(package)
    return package


def _model_package(row: Mapping[str, Any]) -> dict[str, Any]:
    core = deepcopy(dict(row["semantic_scene_core"]))
    provenance = deepcopy(dict(row.get("provenance") or {}))
    package = {
        "scene_ref_id": str(row["scene_ref_id"]),
        "scene_origin": str(row["scene_origin"]),
        "situation_family": str(row["situation_family"]),
        "setting": str(core["setting"]),
        "event": str(row.get("small_micro_scene_event") or ""),
        "scene_core": core,
        "communicative_goal": str(row.get("communicative_goal") or ""),
        "semantic_scene_signature_v2": str(row["semantic_scene_signature_v2"]),
        "source_lineage": {
            "lineage_mode": str(row.get("lineage_mode") or ""),
            "source_authority": str(row.get("source_authority") or ""),
            "resolved_seed_scene_ref_ids": list(provenance.get("resolved_seed_scene_ref_ids") or []),
            "source_claim": str(provenance.get("source_claim") or ""),
            "source_equivalence_claimed": bool(provenance.get("source_equivalence_claimed")),
        },
    }
    bindable, anchors, reason = _unit01_bindability(package)
    package["unit_runtime_bindable"] = bindable
    package["anchors"] = anchors
    package["runtime_bindability_gate_reason"] = reason
    package["unit_language_projection"] = _scene_language_projection(package)
    return package


@lru_cache(maxsize=1)
def _authority_cached() -> dict[str, dict[str, Any]]:
    context_rows = _canonical_context_rows()
    values: dict[str, dict[str, Any]] = {}
    for context, row in zip(s01.CONTEXTS, context_rows, strict=True):
        package = _canonical_package(context, row)
        values[package["scene_ref_id"]] = package
    for row in _model_scene_rows():
        package = _model_package(row)
        ref = package["scene_ref_id"]
        if ref in values:
            raise CanonicalMicroSceneAuthorityError(f"SCENE_REF_DUPLICATE:{ref}")
        values[ref] = package
    if len(values) != EXPECTED_SCENE_COUNT:
        raise CanonicalMicroSceneAuthorityError(
            f"CANONICAL_SCENE_COUNT_INVALID:{len(values)}:{EXPECTED_SCENE_COUNT}"
        )
    return values


def canonical_micro_scene_authority() -> dict[str, dict[str, Any]]:
    return deepcopy(_authority_cached())


def canonical_scene_package(scene_ref_id: str) -> dict[str, Any]:
    package = _authority_cached().get(str(scene_ref_id))
    if package is None:
        raise CanonicalMicroSceneAuthorityError(f"CANONICAL_SCENE_REF_UNKNOWN:{scene_ref_id}")
    return deepcopy(package)


def tolerant_scene_semantic_index() -> dict[str, dict[str, Any]]:
    """Compatibility shape for U01QB13/U14R1/U18E; full package remains dereferenceable."""
    result: dict[str, dict[str, Any]] = {}
    for ref, package in _authority_cached().items():
        core = package["scene_core"]
        result[ref] = {
            "scene_ref_id": ref,
            "objects": list(core.get("objects") or []),
            "anchors": list(package.get("anchors") or []),
            "setting": str(package.get("setting") or ""),
            "source": str(package.get("scene_origin") or ""),
            "event": str(package.get("event") or ""),
            "action": list(core.get("actions") or []),
            "relations": list(core.get("relations") or []),
            "participants": list(core.get("participants") or []),
            "descriptors": list(core.get("descriptors") or []),
            "information_structure": list(core.get("information_structure") or []),
            "communicative_function_ids": list(core.get("communicative_function_ids") or []),
            "communicative_goal": str(package.get("communicative_goal") or ""),
            "semantic_scene_signature_v2": str(package.get("semantic_scene_signature_v2") or ""),
            "source_lineage": deepcopy(package.get("source_lineage") or {}),
            "unit_language_projection": deepcopy(package.get("unit_language_projection") or {}),
            "unit_runtime_bindable": bool(package.get("unit_runtime_bindable")),
        }
    return result


def validate_authority() -> dict[str, Any]:
    authority = _authority_cached()
    errors: list[str] = []
    required_core = (
        "setting", "participants", "objects", "actions", "relations",
        "information_structure", "communicative_function_ids",
    )
    bindable_refs: list[str] = []
    deferred_refs: list[str] = []
    richer_gap_refs: list[str] = []
    for ref, package in sorted(authority.items()):
        core = package.get("scene_core")
        if not isinstance(core, Mapping):
            errors.append(f"SCENE_CORE_MISSING:{ref}")
            continue
        for field in required_core:
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
            if "RICHER_LANGUAGE_ASSET_REF_MISSING" in (projection.get("projection_gap_codes") or []):
                richer_gap_refs.append(ref)
        if package.get("unit_runtime_bindable") is True:
            bindable_refs.append(ref)
            if not package.get("anchors"):
                errors.append(f"BINDABLE_SCENE_ANCHORS_MISSING:{ref}")
            if isinstance(projection, Mapping) and not projection.get("eligible_vocabulary_refs"):
                errors.append(f"BINDABLE_SCENE_VOCABULARY_PROJECTION_MISSING:{ref}")
        else:
            deferred_refs.append(ref)

    if len(authority) != EXPECTED_SCENE_COUNT:
        errors.append(f"SCENE_COUNT_INVALID:{len(authority)}:{EXPECTED_SCENE_COUNT}")
    if len(bindable_refs) != EXPECTED_UNIT01_BINDABLE_COUNT:
        errors.append(
            f"BINDABLE_SCENE_COUNT_INVALID:{len(bindable_refs)}:{EXPECTED_UNIT01_BINDABLE_COUNT}"
        )
    if tuple(sorted(deferred_refs)) != EXPECTED_DEFERRED_REFS:
        errors.append("DEFERRED_SCENE_SET_DRIFT:" + ",".join(sorted(deferred_refs)))

    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "canonical_scene_count": len(authority),
        "unit01_runtime_bindable_scene_count": len(bindable_refs),
        "deferred_scene_refs": sorted(deferred_refs),
        "all_32_scenes_dereferenceable": len(authority) == EXPECTED_SCENE_COUNT,
        "required_scene_core_fields_missing": sum(
            error.startswith("SCENE_CORE_FIELD_MISSING") for error in errors
        ),
        "source_lineage_missing_count": sum(
            error.startswith("SOURCE_LINEAGE_MISSING") for error in errors
        ),
        "richer_language_projection_gap_scene_count": len(richer_gap_refs),
        "richer_language_projection_gap_scene_refs": sorted(richer_gap_refs),
        "questionbank_modified": False,
        "new_scene_authored": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def require_authority_pass() -> dict[str, Any]:
    report = validate_authority()
    if report["error_count"]:
        raise CanonicalMicroSceneAuthorityError(
            "CANONICAL_MICRO_SCENE_AUTHORITY_FAIL:" + "|".join(report["errors"])
        )
    return report
