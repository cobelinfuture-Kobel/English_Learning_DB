"""Canonical Unit01 micro-scene resolver and Unit01 language projection.

The five existing canonical Unit01 contexts and the 27 already-approved U01QB07
model-authored scene specifications remain the only scene sources. Downstream
layers keep lightweight ``scene_ref_id`` references and dereference this module
whenever full scene semantics are required.

U01QB07 production admission used a private Real62 approved artifact to resolve
exact seed scene refs. That artifact was never committed. This resolver therefore
preserves the committed approved seed-backed claim and complete scene semantics,
but never invents unavailable ``resolved_seed_scene_ref_ids``.
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
    "Read-only dereference view over existing approved Unit01 scene and language "
    "authorities; no learner content, scene identity, QuestionBank, selector, planner, "
    "database, scoring, Unit02-24, audio/Speaking-score, or A2 authority is created."
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
PRIVATE_SEED_DETAIL_STATUS = "U07_PRIVATE_PRODUCTION_SEED_REFS_NOT_COMMITTED"
_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)


class CanonicalMicroSceneAuthorityError(ValueError):
    pass


def _words(value: Any) -> set[str]:
    return {token.casefold() for token in _WORD_RE.findall(str(value or "").replace("_", " "))}


def _spec() -> dict[str, Any]:
    try:
        value = json.loads(Path(u07.DEFAULT_SPEC).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalMicroSceneAuthorityError(f"SCENE_SUPPLEMENT_UNREADABLE:{exc}") from exc
    if not isinstance(value, dict):
        raise CanonicalMicroSceneAuthorityError("SCENE_SUPPLEMENT_OBJECT_REQUIRED")
    rows = u07.candidates(value)
    if len(rows) != EXPECTED_MODEL_SCENE_COUNT:
        raise CanonicalMicroSceneAuthorityError(f"MODEL_SCENE_COUNT_INVALID:{len(rows)}")
    return value


def _active_unit01_nouns() -> set[str]:
    return {
        str(row["lemma"]).strip().casefold()
        for row in u01qb01.nouns()
        if str(row.get("lemma") or "").strip()
    }


def _canonical_context_rows() -> list[dict[str, Any]]:
    rows = [u06.canonical_context_scene_row(context) for context in s01.CONTEXTS]
    if len(rows) != EXPECTED_CANONICAL_CONTEXT_COUNT:
        raise CanonicalMicroSceneAuthorityError("CANONICAL_CONTEXT_COUNT_INVALID")
    return rows


def _model_scene_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in u07.candidates(_spec()):
        core = u06.semantic_scene_core(
            setting=str(candidate["medium_setting"]),
            participants=candidate["participants"],
            objects=candidate["objects"],
            descriptors=candidate.get("descriptors") or [],
            actions=candidate["actions"],
            relations=candidate["relations"],
            information_structure=candidate["information_structure"],
            communicative_functions=candidate["communicative_function_ids"],
        )
        reasons = u06.genuine_scene_reason_codes(core)
        if reasons:
            raise CanonicalMicroSceneAuthorityError(
                f"COMMITTED_MODEL_SCENE_GATE_FAIL:{candidate['candidate_id']}:" + ",".join(reasons)
            )
        taxonomy = u06.scene_taxonomy(core)
        if taxonomy["large_situation_family"] != candidate["large_situation_family"]:
            raise CanonicalMicroSceneAuthorityError(
                f"COMMITTED_MODEL_SCENE_FAMILY_DRIFT:{candidate['candidate_id']}"
            )
        if (
            candidate["source_class"] != "MODEL_AUTHORED_FROM_APPROVED_SEEDS"
            or candidate["source_claim"] != "SEED_ANCHORED_MODEL_AUTHORED_NOT_SOURCE_EQUIVALENT"
        ):
            raise CanonicalMicroSceneAuthorityError(
                f"COMMITTED_MODEL_PROVENANCE_INVALID:{candidate['candidate_id']}"
            )
        rows.append(
            {
                "scene_ref_id": str(candidate["candidate_id"]),
                "scene_origin": "MODEL_AUTHORED_SCENE_ENRICHMENT",
                "situation_family": str(candidate["large_situation_family"]),
                "small_micro_scene_event": str(candidate["small_micro_scene_event"]),
                "semantic_scene_core": core,
                "semantic_scene_signature_v2": u06.digest(core),
                "communicative_goal": str(candidate["communicative_goal"]),
                "lineage_mode": "MODEL_AUTHORED_FROM_APPROVED_SEEDS",
                "source_authority": "PROJECT_MODEL_AUTHORED_SCENE_ENRICHMENT",
                "provenance": {
                    "source_claim": str(candidate["source_claim"]),
                    "source_equivalence_claimed": False,
                    "resolved_seed_scene_ref_ids": [],
                    "resolved_seed_scene_ref_detail_status": PRIVATE_SEED_DETAIL_STATUS,
                    "upstream_admission_task_id": u07.TASK_ID,
                },
            }
        )
    return rows


def _unit01_bindability(core: Mapping[str, Any]) -> tuple[bool, list[str], str]:
    active = _active_unit01_nouns()
    object_words = {str(row).casefold() for row in core.get("objects") or []}
    anchors = sorted((object_words | _words(core.get("setting"))) & active)
    return (
        (True, anchors, "UNIT_ACTIVE_NOUN_ANCHOR_PRESENT")
        if anchors
        else (False, [], "UNIT_ACTIVE_NOUN_ANCHOR_MISSING_DEFER_FOR_LATER_UNIT")
    )


@lru_cache(maxsize=1)
def _language_authority() -> dict[str, Any]:
    scope, _unit, unit_authority = s01.unit_authority_context()
    vocabulary, _unselected = s01.selected_vocabulary(scope)
    chunks = s01.selected_chunks(scope)
    return {
        "vocabulary": vocabulary,
        "chunks": chunks,
        "context_phrases": s01.context_phrase_rows(chunks),
        "sentences": s01.sentence_rows(),
        "egp_refs": sorted(str(row) for row in unit_authority["egp_row_ids"]),
        "pattern_refs": sorted(str(row["authority_id"]) for row in unit_authority["patterns"]),
    }


def _label_words(row: Mapping[str, Any]) -> set[str]:
    return _words(row.get("label"))


def _scene_language_projection(package: Mapping[str, Any]) -> dict[str, Any]:
    language = _language_authority()
    core = package["scene_core"]
    lexical_words: set[str] = set()
    for field in ("setting", "objects", "descriptors", "actions", "relations"):
        raw = core.get(field)
        for value in raw if isinstance(raw, list) else [raw]:
            lexical_words.update(_words(value))
    lexical_words.update(_words(package.get("event")))
    lexical_words.update(_words(package.get("communicative_goal")))

    vocabulary_refs = sorted(
        str(row["authority_id"])
        for row in language["vocabulary"]
        if _label_words(row) & lexical_words
    )
    chunk_refs = sorted(
        str(row["authority_id"])
        for row in language["chunks"]
        if _label_words(row) and _label_words(row) <= lexical_words
    )
    context_phrase_refs = sorted(
        str(row["phrase_id"])
        for row in language["context_phrases"]
        if _label_words(row) and _label_words(row) <= lexical_words
    )
    ref = str(package["scene_ref_id"])
    object_words: set[str] = set()
    for value in core.get("objects") or []:
        object_words.update(_words(value))
    semantic_words = _words(core.get("setting"))
    for value in (core.get("actions") or []) + (core.get("relations") or []):
        semantic_words.update(_words(value))
    sentence_refs = sorted(
        {
            str(row["sentence_id"])
            for row in language["sentences"]
            if str(row.get("context_id") or "") == ref
            or (
                bool(_words(row.get("text")) & object_words)
                and bool(_words(row.get("text")) & semantic_words)
            )
        }
    )
    gaps: list[str] = []
    if package.get("unit_runtime_bindable") is True and not vocabulary_refs:
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
        "eligible_egp_refs": list(language["egp_refs"]),
        "eligible_pattern_refs": list(language["pattern_refs"]),
        "content_asset_projection_status": "RUNTIME_SELECTED_ITEM_LINEAGE_ONLY",
        "projection_gap_codes": gaps,
        "projection_source": "EXISTING_UNIT01_LANGUAGE_AUTHORITIES_ONLY",
    }


def _finish_package(package: dict[str, Any]) -> dict[str, Any]:
    bindable, anchors, reason = _unit01_bindability(package["scene_core"])
    package["unit_runtime_bindable"] = bindable
    package["anchors"] = anchors
    package["runtime_bindability_gate_reason"] = reason
    package["unit_language_projection"] = _scene_language_projection(package)
    return package


def _canonical_package(context: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    core = deepcopy(dict(row["semantic_scene_core"]))
    return _finish_package(
        {
            "scene_ref_id": str(row["scene_ref_id"]),
            "scene_origin": "CANONICAL_UNIT01_CONTEXT",
            "situation_family": str(row["situation_family"]),
            "setting": str(core["setting"]),
            "event": str(context.get("title") or ""),
            "scene_core": core,
            "communicative_goal": "IDENTIFY_AND_DESCRIBE_REFERENTS",
            "semantic_scene_signature_v2": str(row["semantic_scene_signature_v2"]),
            "source_lineage": {
                "lineage_mode": "EXISTING_UNIT01_CONTEXT_AUTHORITY",
                "source_authority": str(context.get("source_role") or ""),
                "source_context_id": str(context["context_id"]),
                "source_role": str(context.get("role") or ""),
                "source_equivalence_claimed": True,
            },
        }
    )


def _model_package(row: Mapping[str, Any]) -> dict[str, Any]:
    core = deepcopy(dict(row["semantic_scene_core"]))
    provenance = deepcopy(dict(row.get("provenance") or {}))
    return _finish_package(
        {
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
                "resolved_seed_scene_ref_detail_status": str(
                    provenance.get("resolved_seed_scene_ref_detail_status") or ""
                ),
                "source_claim": str(provenance.get("source_claim") or ""),
                "source_equivalence_claimed": bool(provenance.get("source_equivalence_claimed")),
                "upstream_admission_task_id": str(provenance.get("upstream_admission_task_id") or ""),
            },
        }
    )


@lru_cache(maxsize=1)
def _authority_cached() -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for context, row in zip(s01.CONTEXTS, _canonical_context_rows(), strict=True):
        package = _canonical_package(context, row)
        values[package["scene_ref_id"]] = package
    for row in _model_scene_rows():
        package = _model_package(row)
        ref = package["scene_ref_id"]
        if ref in values:
            raise CanonicalMicroSceneAuthorityError(f"SCENE_REF_DUPLICATE:{ref}")
        values[ref] = package
    if len(values) != EXPECTED_SCENE_COUNT:
        raise CanonicalMicroSceneAuthorityError(f"CANONICAL_SCENE_COUNT_INVALID:{len(values)}")
    return values


def canonical_micro_scene_authority() -> dict[str, dict[str, Any]]:
    return deepcopy(_authority_cached())


def canonical_scene_package(scene_ref_id: str) -> dict[str, Any]:
    package = _authority_cached().get(str(scene_ref_id))
    if package is None:
        raise CanonicalMicroSceneAuthorityError(f"CANONICAL_SCENE_REF_UNKNOWN:{scene_ref_id}")
    return deepcopy(package)


def tolerant_scene_semantic_index() -> dict[str, dict[str, Any]]:
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


def _core_errors(ref: str, core: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(core.get("setting") or ""):
        errors.append(f"SCENE_CORE_FIELD_MISSING:{ref}:setting")
    for field in ("participants", "objects", "information_structure", "communicative_function_ids"):
        value = core.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"SCENE_CORE_FIELD_MISSING:{ref}:{field}")
    for field in ("actions", "relations", "descriptors"):
        if not isinstance(core.get(field), list):
            errors.append(f"SCENE_CORE_FIELD_TYPE_INVALID:{ref}:{field}")
    if not (core.get("actions") or core.get("relations") or len(core.get("objects") or []) >= 2):
        errors.append(f"SCENE_EVENT_UNDER_SPECIFIED:{ref}")
    return errors


def validate_authority() -> dict[str, Any]:
    values = _authority_cached()
    errors: list[str] = []
    bindable: list[str] = []
    deferred: list[str] = []
    richer_gaps: list[str] = []
    private_seed_detail_refs: list[str] = []
    for ref, package in sorted(values.items()):
        core = package.get("scene_core")
        if not isinstance(core, Mapping):
            errors.append(f"SCENE_CORE_MISSING:{ref}")
            continue
        errors.extend(_core_errors(ref, core))
        if not str(package.get("communicative_goal") or ""):
            errors.append(f"COMMUNICATIVE_GOAL_MISSING:{ref}")
        lineage = package.get("source_lineage")
        if not isinstance(lineage, Mapping) or not str(lineage.get("lineage_mode") or ""):
            errors.append(f"SOURCE_LINEAGE_MISSING:{ref}")
        elif lineage.get("lineage_mode") == "MODEL_AUTHORED_FROM_APPROVED_SEEDS":
            if (
                lineage.get("source_claim") != "SEED_ANCHORED_MODEL_AUTHORED_NOT_SOURCE_EQUIVALENT"
                or lineage.get("source_equivalence_claimed") is not False
            ):
                errors.append(f"MODEL_SOURCE_CLAIM_INVALID:{ref}")
            if not lineage.get("resolved_seed_scene_ref_ids"):
                if lineage.get("resolved_seed_scene_ref_detail_status") != PRIVATE_SEED_DETAIL_STATUS:
                    errors.append(f"MODEL_PRIVATE_SEED_DETAIL_STATUS_MISSING:{ref}")
                private_seed_detail_refs.append(ref)
        projection = package.get("unit_language_projection")
        if not isinstance(projection, Mapping):
            errors.append(f"UNIT_LANGUAGE_PROJECTION_MISSING:{ref}")
        else:
            if not projection.get("eligible_egp_refs"):
                errors.append(f"ELIGIBLE_EGP_REFS_MISSING:{ref}")
            if not projection.get("eligible_pattern_refs"):
                errors.append(f"ELIGIBLE_PATTERN_REFS_MISSING:{ref}")
            if "RICHER_LANGUAGE_ASSET_REF_MISSING" in (projection.get("projection_gap_codes") or []):
                richer_gaps.append(ref)
        if package.get("unit_runtime_bindable") is True:
            bindable.append(ref)
            if not package.get("anchors"):
                errors.append(f"BINDABLE_SCENE_ANCHORS_MISSING:{ref}")
            if isinstance(projection, Mapping) and not projection.get("eligible_vocabulary_refs"):
                errors.append(f"BINDABLE_SCENE_VOCABULARY_PROJECTION_MISSING:{ref}")
        else:
            deferred.append(ref)

    if len(values) != EXPECTED_SCENE_COUNT:
        errors.append(f"SCENE_COUNT_INVALID:{len(values)}:{EXPECTED_SCENE_COUNT}")
    if len(bindable) != EXPECTED_UNIT01_BINDABLE_COUNT:
        errors.append(f"BINDABLE_SCENE_COUNT_INVALID:{len(bindable)}:{EXPECTED_UNIT01_BINDABLE_COUNT}")
    if tuple(sorted(deferred)) != EXPECTED_DEFERRED_REFS:
        errors.append("DEFERRED_SCENE_SET_DRIFT:" + ",".join(sorted(deferred)))
    if len(private_seed_detail_refs) != EXPECTED_MODEL_SCENE_COUNT:
        errors.append(
            f"PRIVATE_SEED_DETAIL_DENOMINATOR_DRIFT:{len(private_seed_detail_refs)}:{EXPECTED_MODEL_SCENE_COUNT}"
        )
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "canonical_scene_count": len(values),
        "unit01_runtime_bindable_scene_count": len(bindable),
        "deferred_scene_refs": sorted(deferred),
        "all_32_scenes_dereferenceable": len(values) == EXPECTED_SCENE_COUNT,
        "required_scene_core_fields_missing": sum(
            error.startswith("SCENE_CORE_FIELD_MISSING") for error in errors
        ),
        "source_lineage_missing_count": sum(
            error.startswith("SOURCE_LINEAGE_MISSING") for error in errors
        ),
        "private_seed_ref_detail_unavailable_scene_count": len(private_seed_detail_refs),
        "private_seed_ref_detail_status": PRIVATE_SEED_DETAIL_STATUS,
        "richer_language_projection_gap_scene_count": len(richer_gaps),
        "richer_language_projection_gap_scene_refs": sorted(richer_gaps),
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
