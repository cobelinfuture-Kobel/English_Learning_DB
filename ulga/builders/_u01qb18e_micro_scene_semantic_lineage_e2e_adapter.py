"""Preserve Unit01 micro-scene semantics through learner-facing Form projection.

U01QB18E closes a cross-layer acceptance gap exposed by the exact fresh Form01
review: approved micro-scenes retained objects/actions/relations/goals upstream,
while U01QB13 runtime matching consumed mostly noun anchors and U01QB18C learner
scaffolds could replace the selected item's learner-visible scene context.

This product-scoped adapter keeps the existing 474-item QuestionBank and every
existing selector/projection authority identity. It extends only internal
already-owned delegates:

* U01QB16C keeps owning ``matching.assemble_form_component``; its preserved base
  assembler delegate receives a temporary semantic-fidelity rank overlay.
* U01QB18C keeps owning ``target.form_component_payload``; its preserved base
  payload and repair delegates receive scene lineage and non-destructive context
  composition.

No second selector, runtime, planner, learner database, scoring authority or
content authority is created.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as target,
)
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix
    as scene_authority,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Product-scoped semantic-lineage extension over already-approved Unit01 micro-scenes "
    "and the existing U01QB13/U01QB16C/U01QB18C path. It changes only internal delegates "
    "already owned by U16C/U18C: already-eligible candidates are re-ranked by approved "
    "scene semantic fidelity and prior same-form usage, and approved scene metadata is "
    "composed with existing scaffolds. It authors no assessed item, changes no 474-item "
    "denominator, creates no second selector/runtime/planner/database/scoring authority, "
    "modifies no Unit02-24 content, enables no audio/Speaking score, and unlocks no A2."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18E_Unit01MicroSceneToLearnerFormSemanticLineageE2EFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18E_UNIT01_MICRO_SCENE_TO_LEARNER_FORM_SEMANTIC_LINEAGE_E2E_FULLFIX"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18E_UNIT01_MICRO_SCENE_TO_LEARNER_FORM_SEMANTIC_LINEAGE_E2E_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F_Unit01TwelveFormSemanticLineageReplayAndPedagogicalReacceptance"

_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)
_CONTEXT_CUE_FORMS = frozenset({1, 2, 3})

# Preserve exact prior owners. U01QB18E intentionally does not replace
# matching.assemble_form_component or target.form_component_payload.
_ORIGINAL_U16C_DELEGATE_ASSEMBLER = u16c._ORIGINAL_ASSEMBLE
_ORIGINAL_18C_BASE_PAYLOAD = quality._ORIGINAL_FORM_COMPONENT_PAYLOAD
_ORIGINAL_18C_REPAIR = quality.repair_learner_item

_ACTIVE_CANDIDATE_RANK = None
_ACTIVE_ACTIVITY_SEMANTICS: dict[str, dict[str, Any]] = {}
_ACTIVE_PRIOR_NOUN_COUNTS: dict[str, Counter[str]] = {}
_ACTIVE_PRIOR_STIMULI: dict[str, set[str]] = {}
_ACTIVE_PRIOR_ITEM_IDS: dict[str, set[str]] = {}
_INSTALLED = False


class MicroSceneSemanticLineageError(ValueError):
    """Fail-closed cross-layer scene semantic lineage error."""


def _words(value: Any) -> set[str]:
    return {token.casefold() for token in _WORD_RE.findall(str(value or ""))}


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _private_item(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(str(row.get("private_item_json")))
    except (TypeError, json.JSONDecodeError) as exc:
        raise MicroSceneSemanticLineageError(
            f"PRIVATE_ITEM_JSON_INVALID:{row.get('item_id')}"
        ) from exc
    if not isinstance(value, Mapping):
        raise MicroSceneSemanticLineageError(
            f"PRIVATE_ITEM_OBJECT_REQUIRED:{row.get('item_id')}"
        )
    return dict(value)


def _lexical_noun(item: Mapping[str, Any]) -> str:
    lexical = item.get("lexical_slots")
    if not isinstance(lexical, Mapping):
        return ""
    return str(lexical.get("noun") or "").strip().casefold()


def _visible_text(item: Mapping[str, Any]) -> str:
    return " ".join(
        part
        for part in (
            str(item.get("stimulus") or ""),
            str(item.get("prompt") or ""),
        )
        if part.strip()
    )


def _approved_semantic_asset_evidence(item: Mapping[str, Any]) -> bool:
    """Recognize only the existing admitted RAZQ asset lineage as a signal."""
    if str(item.get("content_lineage_mode") or "") not in {
        "SEMANTIC_ANCHOR_A1_IMITATION",
        "PROJECT_AUTHORED_CONTRACT_COMPLETION",
        "SEMANTIC_EQUIVALENT",
    }:
        return False
    if not str(item.get("content_asset_id") or ""):
        return False
    return any(
        isinstance(source, Mapping)
        and str(source.get("source_type") or "") == "RAZQ01D_APPROVED_CONTENT_ASSET"
        for source in item.get("source_refs") or []
    )


def _action_hit(action: str, words: set[str]) -> bool:
    base = str(action).strip().casefold()
    if not base:
        return False
    variants = {base, f"{base}s", f"{base}es"}
    variants.add(f"{base[:-1]}ing" if base.endswith("e") else f"{base}ing")
    return bool(variants & words)


def _ids(item: Mapping[str, Any], *names: str) -> list[str]:
    values: set[str] = set()
    for name in names:
        raw = item.get(name)
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            values.update(str(value) for value in raw if str(value))
    return sorted(values)


def language_asset_lineage(item: Mapping[str, Any]) -> dict[str, Any]:
    """Read only language lineage already present on the selected catalog item."""
    content_asset_id = str(item.get("content_asset_id") or "")
    return {
        "vocabulary_refs": _ids(item, "target_evp_sense_ids"),
        "chunk_refs": _ids(item, "target_chunk_ids", "target_canonical_chunk_ids"),
        "sentence_refs": _ids(item, "target_sentence_ids"),
        "pattern_refs": _ids(item, "unit_pattern_ids", "target_pattern_ids"),
        "content_asset_ids": [content_asset_id] if content_asset_id else [],
    }


def semantic_fidelity(
    *,
    scene_ref_id: str,
    semantics: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one already-eligible item against one approved micro-scene."""
    words = _words(_visible_text(item))
    noun = _lexical_noun(item)
    objects = {
        str(value).strip().casefold()
        for value in semantics.get("objects") or []
        if str(value).strip()
    }
    anchors = {
        str(value).strip().casefold()
        for value in semantics.get("anchors") or []
        if str(value).strip()
    }
    relations = {
        str(value).strip().casefold()
        for value in semantics.get("relations") or []
        if str(value).strip()
    }
    actions = {
        str(value).strip().casefold()
        for value in semantics.get("action") or []
        if str(value).strip()
    }
    setting_words = _words(str(semantics.get("setting") or ""))
    item_context = str(
        item.get("context_id")
        or (item.get("lexical_slots") or {}).get("context_id")
        or ""
    )
    content_asset_id = str(item.get("content_asset_id") or "")
    exact_scene_identity = bool(scene_ref_id) and scene_ref_id in {
        item_context,
        content_asset_id,
    }
    object_hits = sorted((objects | anchors) & words)
    relation_hits = sorted(relations & words)
    action_hits = sorted(action for action in actions if _action_hit(action, words))
    setting_hits = sorted(setting_words & words)
    # A context-bound item with the exact approved scene identity is already
    # semantically bound even when its lexical noun is a valid introduced object
    # rather than one of the scene's headline anchors. The R2R1 consumer guard
    # separately rejects tautological item/container pairs.
    # The formal Writing selector may use an already-approved context-bound
    # item from the same situation family when a model scene has no exact
    # scene-specific row.  Its persisted context_id is the compatibility
    # evidence for that bounded fallback; richer linked assets still require
    # the stricter projection overlap gate below.
    context_bound_fallback = bool(noun) and bool(item_context)
    noun_bound = bool(noun) and (
        noun in (objects | anchors) or exact_scene_identity or context_bound_fallback
    )
    approved_asset_signal = int(noun_bound and _approved_semantic_asset_evidence(item))
    semantic_signal_hits = (
        len(relation_hits) + len(action_hits) + len(setting_hits) + approved_asset_signal
    )
    assets = language_asset_lineage(item)
    richer_asset = bool(
        assets["content_asset_ids"] or assets["chunk_refs"] or assets["sentence_refs"]
    )

    if exact_scene_identity:
        tier, mode = 0, "EXACT_SCENE_LINEAGE"
    elif noun_bound and semantic_signal_hits and richer_asset:
        tier, mode = 1, "SCENE_SEMANTIC_AND_LANGUAGE_ASSET_COMPATIBLE"
    elif noun_bound and semantic_signal_hits:
        tier, mode = 2, "SCENE_SEMANTIC_COMPATIBLE"
    elif noun_bound and richer_asset:
        tier, mode = 3, "LANGUAGE_ASSET_LEXICAL_COMPATIBLE"
    elif noun_bound:
        tier, mode = 4, "LEXICAL_ANCHOR_ONLY"
    else:
        tier, mode = 5, "SCENE_SEMANTIC_UNBOUND"

    return {
        "mode": mode,
        "tier": tier,
        "scene_ref_id": scene_ref_id,
        "noun": noun,
        "noun_bound": noun_bound,
        "exact_scene_identity": exact_scene_identity,
        "object_hits": object_hits,
        "relation_hits": relation_hits,
        "action_hits": action_hits,
        "setting_hits": setting_hits,
        "approved_asset_signal": bool(approved_asset_signal),
        "semantic_signal_hit_count": semantic_signal_hits,
        "language_asset_lineage": assets,
        "richer_language_asset_present": richer_asset,
        "content_asset_id": content_asset_id,
        "item_context_id": item_context,
    }


def _private_stimulus_signature(item: Mapping[str, Any]) -> str:
    value = _normalized(item.get("stimulus"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""


_PRESENTATION_ONLY_PREFIXES = (
    "scene:",
    "scene words:",
    "relationship:",
    "action:",
    "event:",
    "task focus:",
    "example:",
)


def _core_stimulus(value: Any) -> str:
    parts = []
    for raw in str(value or "").split("|"):
        part = _normalized(raw)
        if not part or any(part.startswith(prefix) for prefix in _PRESENTATION_ONLY_PREFIXES):
            continue
        parts.append(part)
    return " | ".join(parts)


def _speaking_operation(task_angle: str) -> str:
    return {
        "SCENE_DESCRIPTION": "SHORT_SENTENCE_PRODUCTION",
        "COMPLETE_SENTENCE_PRODUCTION": "COMPLETE_SENTENCE_PRODUCTION",
        "CONNECTED_SENTENCE_PRODUCTION": "CONNECTED_SENTENCE_PRODUCTION",
    }.get(str(task_angle), "SPEAKING_PRODUCTION")


def _canonical_core_task(
    *,
    private_item: Mapping[str, Any],
    skill: str,
    task_angle: str,
    form_ordinal: int,
    scene_anchors: Sequence[str],
    setting: str,
    semantics: Mapping[str, Any],
) -> dict[str, Any]:
    skill = str(skill).upper()
    contract = private_item.get("response_contract") or {}
    if not isinstance(contract, Mapping):
        contract = {}
    options = [str(value).casefold() for value in private_item.get("options") or []]
    accepted_sequence = [
        str(value).casefold() for value in contract.get("accepted_sequence") or []
    ]
    lexical_slots = {
        str(key): _normalized(value)
        for key, value in (private_item.get("lexical_slots") or {}).items()
        if str(key) != "context_id" and str(value).strip()
    }
    core: dict[str, Any] = {
        "skill": skill,
        "stimulus": _core_stimulus(private_item.get("stimulus")),
        "question_type": _normalized(private_item.get("question_type")),
        "response_type": _normalized(contract.get("response_type")),
        "scoring_mode": _normalized(contract.get("scoring_mode") or private_item.get("scoring_mode")),
        "options": options,
        "accepted_sequence": accepted_sequence,
        "target_answer": private_item.get("correct_answer")
        or private_item.get("accepted_answers")
        or accepted_sequence,
        "lexical_slots": lexical_slots,
        "grammar_target_ids": sorted(
            _normalized(value) for value in private_item.get("grammar_target_ids") or []
        ),
        "candidate_structure": _normalized(private_item.get("candidate_structure")),
    }
    if str(task_angle) == "WORD_ORDER":
        core["stimulus"] = "words: " + " | ".join(options)
        core["ordered_tokens"] = options
        core["operation"] = "WORD_ORDER"
    elif skill == "SPEAKING":
        noun = quality.lexical_noun(private_item)
        scaffold = quality.speaking_scaffold(
            form_ordinal=int(form_ordinal),
            task_angle=str(task_angle),
            target_noun=noun,
            scene_anchors=scene_anchors,
            setting=setting,
        )
        core.update(
            {
                "stimulus": _core_stimulus(scaffold["stimulus"]),
                "operation": _speaking_operation(str(task_angle)),
                "target_word": _normalized(scaffold["target_word"]),
                "sentence_frame": _normalized(scaffold["sentence_frame"]),
                "scaffold_stage": _normalized(scaffold["stage"]),
            }
        )
    else:
        core["operation"] = _normalized(
            private_item.get("question_type")
            or contract.get("response_type")
            or ""
        )
    return core


def _projected_stimulus(
    *,
    private_item: Mapping[str, Any],
    skill: str,
    task_angle: str,
    form_ordinal: int,
    scene_anchors: Sequence[str],
    setting: str,
    semantics: Mapping[str, Any],
) -> str:
    """Mirror the installed learner-facing projection for collision ranking."""
    skill = str(skill).upper()
    task_angle = str(task_angle)
    if skill == "SPEAKING":
        noun = quality.lexical_noun(private_item)
        value = quality.speaking_scaffold(
            form_ordinal=int(form_ordinal),
            task_angle=task_angle,
            target_noun=noun,
            scene_anchors=scene_anchors,
            setting=setting,
        )["stimulus"]
    elif task_angle == "WORD_ORDER":
        tokens = [str(token) for token in private_item.get("options") or []]
        value = (
            f"Example: {quality._word_order_example(tokens)} | Words: "
            + " | ".join(tokens)
        )
    else:
        value = str(private_item.get("stimulus") or "")
    had_stimulus = bool(str(value).strip())
    value = _prepend_context_card(
        value,
        _scene_context_card(semantics=semantics, form_ordinal=int(form_ordinal)),
    )
    label = task_angle.replace("_", " ").strip().casefold()
    if str(skill).upper() != "READING" or not had_stimulus:
        value = f"{value} | Task focus: {label}" if value else f"Task focus: {label}"
    return value


def _projected_stimulus_signature(
    *,
    private_item: Mapping[str, Any],
    skill: str,
    task_angle: str,
    form_ordinal: int,
    scene_anchors: Sequence[str],
    setting: str,
    semantics: Mapping[str, Any],
) -> str:
    value = json.dumps(
        _canonical_core_task(
            private_item=private_item,
            skill=skill,
            task_angle=task_angle,
            form_ordinal=form_ordinal,
            scene_anchors=scene_anchors,
            setting=setting,
            semantics=semantics,
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""


def _candidate_rank_with_scene_semantics(
    *,
    row: Mapping[str, Any],
    anchors: set[str],
    situation_family: str,
    learner_id: str,
    session_id: str,
    activity_id: str,
    exposed: set[str],
    recent: set[str],
    assessment: bool,
    scene_ref_id: str | None = None,
    task_angle: str | None = None,
):
    delegate = _ACTIVE_CANDIDATE_RANK
    if delegate is None:
        raise MicroSceneSemanticLineageError("SEMANTIC_RANK_DELEGATE_NOT_ACTIVE")
    base = delegate(
        row=row,
        anchors=anchors,
        situation_family=situation_family,
        learner_id=learner_id,
        session_id=session_id,
        activity_id=activity_id,
        exposed=exposed,
        recent=recent,
        assessment=assessment,
        scene_ref_id=scene_ref_id,
        task_angle=task_angle,
    )
    if base is None:
        return None
    context = _ACTIVE_ACTIVITY_SEMANTICS.get(str(activity_id))
    if context is None or row.get("private_item_json") in (None, ""):
        return base
    item = _private_item(row)
    ref = str(context["scene_ref_id"])
    fidelity = semantic_fidelity(
        scene_ref_id=ref,
        semantics=context["semantics"],
        item=item,
    )
    noun = str(fidelity["noun"])
    prior_noun_count = int(_ACTIVE_PRIOR_NOUN_COUNTS.get(ref, Counter()).get(noun, 0))
    stimulus_signature = _projected_stimulus_signature(
        private_item=item,
        skill=str(context["skill"]),
        task_angle=str(context["task_angle"]),
        form_ordinal=int(context["form_ordinal"]),
        scene_anchors=sorted(anchors),
        setting=str(context["semantics"].get("setting") or ""),
        semantics=context["semantics"],
    )
    prior_stimulus_duplicate = int(
        bool(stimulus_signature)
        and stimulus_signature in _ACTIVE_PRIOR_STIMULI.get(ref, set())
    )
    scene_item_replay = int(
        str(row["item_id"]) in _ACTIVE_PRIOR_ITEM_IDS.get(ref, set())
    )
    if scene_item_replay:
        return None
    # This prefix changes preference only among candidates already accepted by
    # the canonical rank. It cannot turn a previously-illegal candidate legal.
    return (
        int(fidelity["tier"]),
        scene_item_replay,
        prior_stimulus_duplicate,
        prior_noun_count,
        -int(fidelity["semantic_signal_hit_count"]),
        -len(fidelity["object_hits"]),
    ) + tuple(base)


def _activity_semantics(database: Path, form_ordinal: int) -> dict[str, dict[str, Any]]:
    semantic_index = scene_authority.tolerant_scene_semantic_index()
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT activity_id,scene_ref_id,form_ordinal,skill,task_angle,support_level
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=? ORDER BY activity_id""",
            (int(form_ordinal),),
        ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        ref = str(row["scene_ref_id"])
        semantics = semantic_index.get(ref)
        if not isinstance(semantics, Mapping):
            raise MicroSceneSemanticLineageError(
                f"SCENE_SEMANTICS_MISSING:{ref}:{row['activity_id']}"
            )
        result[str(row["activity_id"])] = {
            "scene_ref_id": ref,
            "form_ordinal": int(row["form_ordinal"]),
            "skill": str(row["skill"]),
            "task_angle": str(row["task_angle"]),
            "support_level": str(row["support_level"]),
            "semantics": deepcopy(dict(semantics)),
        }
    return result


def _prior_form_usage(
    database: Path,
    form_ordinal: int,
    *,
    skill: str,
) -> tuple[
    dict[str, Counter[str]],
    dict[str, set[str]],
    dict[str, set[str]],
]:
    noun_counts: dict[str, Counter[str]] = defaultdict(Counter)
    stimuli: dict[str, set[str]] = defaultdict(set)
    item_ids: dict[str, set[str]] = defaultdict(set)
    semantic_index = scene_authority.tolerant_scene_semantic_index()
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT a.scene_ref_id,a.form_ordinal,a.skill,a.task_angle,
                      a.scene_anchors_json,a.setting,c.item_id,c.private_item_json
               FROM u01qb13_session_bindings b
               JOIN u01qb13_blueprint_activities a USING(activity_id)
               JOIN u01qb02_item_catalog c USING(item_id)
               WHERE a.form_ordinal<=? ORDER BY b.session_id,b.item_position""",
            (int(form_ordinal),),
        ).fetchall()
    for row in rows:
        ref = str(row["scene_ref_id"])
        if str(row["skill"]).upper() == str(skill).upper():
            item_ids[ref].add(str(row["item_id"]))
        item = _private_item(row)
        noun = _lexical_noun(item)
        if noun:
            noun_counts[ref][noun] += 1
        signature = _projected_stimulus_signature(
            private_item=item,
            skill=str(row["skill"]),
            task_angle=str(row["task_angle"]),
            form_ordinal=int(row["form_ordinal"]),
            scene_anchors=json.loads(str(row["scene_anchors_json"])),
            setting=str(row["setting"]),
            semantics=semantic_index[str(row["scene_ref_id"])],
        )
        if signature:
            stimuli[ref].add(signature)
    return dict(noun_counts), dict(stimuli), dict(item_ids)


def assemble_form_component_with_semantic_rank(
    database,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
):
    """Internal U16C delegate that preserves U16C's public assembler identity."""
    global _ACTIVE_CANDIDATE_RANK, _ACTIVE_ACTIVITY_SEMANTICS
    global _ACTIVE_PRIOR_NOUN_COUNTS, _ACTIVE_PRIOR_STIMULI, _ACTIVE_PRIOR_ITEM_IDS
    previous_rank = target._candidate_rank
    previous_context = _ACTIVE_ACTIVITY_SEMANTICS
    previous_nouns = _ACTIVE_PRIOR_NOUN_COUNTS
    previous_stimuli = _ACTIVE_PRIOR_STIMULI
    previous_item_ids = _ACTIVE_PRIOR_ITEM_IDS
    _ACTIVE_CANDIDATE_RANK = previous_rank
    _ACTIVE_ACTIVITY_SEMANTICS = _activity_semantics(Path(database), int(form_ordinal))
    with closing(sqlite3.connect(Path(database))) as connection:
        session_row = connection.execute(
            "SELECT skill FROM learning_sessions WHERE session_id=?",
            (str(session_id),),
        ).fetchone()
    active_skill = str(session_row[0]) if session_row else ""
    (
        _ACTIVE_PRIOR_NOUN_COUNTS,
        _ACTIVE_PRIOR_STIMULI,
        _ACTIVE_PRIOR_ITEM_IDS,
    ) = _prior_form_usage(
        Path(database),
        int(form_ordinal),
        skill=active_skill,
    )
    target._candidate_rank = _candidate_rank_with_scene_semantics
    try:
        return _ORIGINAL_U16C_DELEGATE_ASSEMBLER(
            database,
            learner_id=learner_id,
            session_id=session_id,
            form_ordinal=form_ordinal,
            selected_at=selected_at,
        )
    finally:
        target._candidate_rank = previous_rank
        _ACTIVE_CANDIDATE_RANK = None
        _ACTIVE_ACTIVITY_SEMANTICS = previous_context
        _ACTIVE_PRIOR_NOUN_COUNTS = previous_nouns
        _ACTIVE_PRIOR_STIMULI = previous_stimuli
        _ACTIVE_PRIOR_ITEM_IDS = previous_item_ids


def _scene_context_card(*, semantics: Mapping[str, Any], form_ordinal: int) -> str:
    """Project only already-approved scene metadata; never synthesize an answer."""
    setting = str(semantics.get("setting") or "").replace("_", " ").strip().title()
    objects = [
        str(value).strip().casefold()
        for value in semantics.get("objects") or []
        if str(value).strip()
    ]
    relations = [
        str(value).strip().casefold()
        for value in semantics.get("relations") or []
        if str(value).strip()
    ]
    actions = [
        str(value).strip().casefold()
        for value in semantics.get("action") or []
        if str(value).strip()
    ]
    event = str(semantics.get("event") or "").replace("_", " ").strip().casefold()
    parts: list[str] = []
    if setting:
        parts.append(f"Scene: {setting}")
    if int(form_ordinal) in _CONTEXT_CUE_FORMS:
        if objects:
            parts.append("Scene words: " + ", ".join(objects))
        if relations:
            parts.append("Relationship: " + ", ".join(relations))
        elif actions:
            parts.append("Action: " + ", ".join(actions))
        elif event:
            parts.append("Event: " + event)
    return " | ".join(parts)


def _prepend_context_card(stimulus: str, card: str) -> str:
    stimulus = str(stimulus or "").strip()
    card = str(card or "").strip()
    if not card:
        return stimulus
    if stimulus.casefold().startswith(card.casefold()):
        return stimulus
    return f"{card} | {stimulus}" if stimulus else card


def _binding_metadata(connection, session_id: str) -> dict[str, dict[str, Any]]:
    semantic_index = scene_authority.tolerant_scene_semantic_index()
    rows = connection.execute(
        """SELECT b.activity_id,a.form_ordinal,a.scene_ref_id,a.skill,a.task_angle,
                  c.item_id,c.private_item_json
           FROM u01qb13_session_bindings b
           JOIN u01qb13_blueprint_activities a USING(activity_id)
           JOIN u01qb02_item_catalog c USING(item_id)
           WHERE b.session_id=? ORDER BY b.item_position""",
        (session_id,),
    ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        ref = str(row["scene_ref_id"])
        semantics = semantic_index.get(ref)
        if not isinstance(semantics, Mapping):
            raise MicroSceneSemanticLineageError(f"SCENE_SEMANTICS_MISSING:{ref}")
        item = _private_item(row)
        result[str(row["activity_id"])] = {
            "form_ordinal": int(row["form_ordinal"]),
            "scene_ref_id": ref,
            "skill": str(row["skill"]),
            "task_angle": str(row["task_angle"]),
            "item_id": str(row["item_id"]),
            "private_item": item,
            "semantics": deepcopy(dict(semantics)),
            "fidelity": semantic_fidelity(
                scene_ref_id=ref,
                semantics=semantics,
                item=item,
            ),
        }
    return result


def base_form_component_payload_with_semantic_lineage(
    connection,
    *,
    session_id: str,
) -> dict[str, Any]:
    """Internal base payload delegate called by the unchanged U01QB18C owner."""
    value = _ORIGINAL_18C_BASE_PAYLOAD(connection, session_id=session_id)
    metadata = _binding_metadata(connection, session_id)
    enriched = []
    for source in value.get("items") or []:
        row = dict(source)
        activity_id = str(row.get("activity_id") or "")
        meta = metadata.get(activity_id)
        if meta is None:
            raise MicroSceneSemanticLineageError(
                f"FORM_COMPONENT_ACTIVITY_LINEAGE_MISSING:{activity_id}"
            )
        card = _scene_context_card(
            semantics=meta["semantics"],
            form_ordinal=int(meta["form_ordinal"]),
        )
        row["semantic_lineage"] = {
            "scene_ref_id": meta["scene_ref_id"],
            "scene_source": str(meta["semantics"].get("source") or ""),
            "scene_event": str(meta["semantics"].get("event") or ""),
            "scene_objects": list(meta["semantics"].get("objects") or []),
            "scene_actions": list(meta["semantics"].get("action") or []),
            "scene_relations": list(meta["semantics"].get("relations") or []),
            "communicative_goal": str(meta["semantics"].get("communicative_goal") or ""),
            "selection_fidelity": deepcopy(meta["fidelity"]),
            "language_asset_lineage": deepcopy(
                meta["fidelity"]["language_asset_lineage"]
            ),
            "learner_scene_context_card": card,
            "scene_context_preserved": False,
        }
        enriched.append(row)
    value["items"] = enriched
    value["semantic_lineage_preprojection"] = PASS_STATUS
    return value


def repair_learner_item_with_semantic_lineage(
    item: Mapping[str, Any],
    *,
    private_item: Mapping[str, Any],
    form_ordinal: int,
    scene_anchors: Sequence[str],
    setting: str,
) -> dict[str, Any]:
    """Run U18C repair first, then compose the scene card instead of replacing it."""
    value = _ORIGINAL_18C_REPAIR(
        item,
        private_item=private_item,
        form_ordinal=form_ordinal,
        scene_anchors=scene_anchors,
        setting=setting,
    )
    lineage = item.get("semantic_lineage")
    if not isinstance(lineage, Mapping):
        raise MicroSceneSemanticLineageError(
            f"SEMANTIC_LINEAGE_MISSING_BEFORE_REPAIR:{item.get('activity_id')}"
        )
    preserved = deepcopy(dict(lineage))
    card = str(preserved.get("learner_scene_context_card") or "")
    had_stimulus = bool(str(value.get("stimulus") or "").strip())
    value["stimulus"] = _prepend_context_card(str(value.get("stimulus") or ""), card)
    task_angle = str(item.get("task_angle") or "").replace("_", " ").strip().casefold()
    if str(item.get("skill") or "").upper() != "READING" or not had_stimulus:
        value["stimulus"] = (
            f"{value['stimulus']} | Task focus: {task_angle}"
            if value["stimulus"]
            else f"Task focus: {task_angle}"
        )
    preserved["scene_context_preserved"] = bool(
        card and card.casefold() in str(value["stimulus"]).casefold()
    )
    value["semantic_lineage"] = preserved
    # Internal-only operation evidence for the U18E distinctness gate. The
    # learner export projects a fixed public field set and strips this key.
    response_contract = private_item.get("response_contract") or {}
    value["_semantic_operation"] = _normalized(
        private_item.get("question_type")
        or (response_contract.get("response_type") if isinstance(response_contract, Mapping) else "")
        or ""
    )
    return value


def _learner_core_task(item: Mapping[str, Any]) -> dict[str, Any]:
    skill = str(item.get("skill") or "").upper()
    task_angle = _normalized(item.get("task_angle"))
    semantic_operation = _normalized(item.get("_semantic_operation"))
    options = [str(value).casefold() for value in item.get("options") or []]
    ordered_tokens = [
        str(value).casefold() for value in item.get("ordered_tokens") or []
    ]
    core: dict[str, Any] = {
        "skill": skill,
        "stimulus": _core_stimulus(item.get("stimulus")),
        "response_mode": _normalized(item.get("response_mode")),
        "options": options,
        "ordered_tokens": ordered_tokens,
        "target_word": _normalized(item.get("target_word")),
        "sentence_frame": _normalized(item.get("sentence_frame")),
        "scaffold_stage": _normalized(item.get("speaking_scaffold_stage")),
        "word_order_interaction": _normalized(item.get("word_order_interaction")),
    }
    if core["word_order_interaction"] or core["ordered_tokens"]:
        core["operation"] = "WORD_ORDER"
    elif skill == "SPEAKING":
        frame = core["sentence_frame"]
        core["operation"] = (
            "CONNECTED_SENTENCE_PRODUCTION"
            if "the ______ is here" in frame
            else "SENTENCE_PRODUCTION"
        )
    elif skill == "WRITING" and semantic_operation:
        # The approved item's response contract is the operation authority;
        # blueprint task_angle is only a fallback for synthetic payloads.
        core["operation"] = semantic_operation
    elif skill == "WRITING" and task_angle in {
        "ERROR_CHECK",
        "COMPLETE_SENTENCE_PRODUCTION",
        "CONNECTED_SENTENCE_PRODUCTION",
        "PHRASE_CONSTRUCTION",
        "WORD_ORDER",
    }:
        # Blueprint task_angle is the existing operation authority for the
        # learner's response contract. It distinguishes one-sentence and
        # connected-sentence production without using wrapper wording.
        core["operation"] = task_angle
    else:
        core["operation"] = core["response_mode"]
    return core


def _safe_stimulus_signature(item: Mapping[str, Any]) -> str:
    value = json.dumps(
        _learner_core_task(item),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""


def validate_form_components(skill_payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Validate one logical 20-activity form after all three skills materialize."""
    items = [
        item
        for skill in ("READING", "WRITING", "SPEAKING")
        for item in skill_payloads.get(skill, {}).get("items") or []
    ]
    errors: list[str] = []
    if len(items) != target.ACTIVITIES_PER_FORM:
        errors.append(f"FORM_ACTIVITY_COUNT_INVALID:{len(items)}")

    by_scene: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        lineage = item.get("semantic_lineage")
        if not isinstance(lineage, Mapping):
            errors.append(f"SEMANTIC_LINEAGE_MISSING:{item.get('activity_id')}")
            continue
        ref = str(lineage.get("scene_ref_id") or "")
        by_scene[ref].append(item)
        if lineage.get("scene_context_preserved") is not True:
            errors.append(f"SCENE_CONTEXT_NOT_PRESERVED:{item.get('activity_id')}")
        fidelity = lineage.get("selection_fidelity") or {}
        if fidelity.get("noun_bound") is not True:
            errors.append(f"SCENE_NOUN_UNBOUND:{item.get('activity_id')}")
        if str(fidelity.get("mode") or "") == "SCENE_SEMANTIC_UNBOUND":
            errors.append(f"SCENE_SEMANTIC_UNBOUND:{item.get('activity_id')}")

    if len(by_scene) != target.SCENES_PER_FORM:
        errors.append(f"FORM_SCENE_COUNT_INVALID:{len(by_scene)}")

    form_ordinals = {
        int(payload.get("form_ordinal", 0) or 0)
        for payload in skill_payloads.values()
        if payload
    }
    form_ordinal = next(iter(form_ordinals)) if len(form_ordinals) == 1 else 0
    scene_reports = []
    for ref, rows in sorted(by_scene.items()):
        if len(rows) != target.ACTIVITIES_PER_SCENE:
            errors.append(f"SCENE_ACTIVITY_COUNT_INVALID:{ref}:{len(rows)}")
        semantic_signal_hits = sum(
            int(
                ((row.get("semantic_lineage") or {}).get("selection_fidelity") or {}).get(
                    "semantic_signal_hit_count", 0
                )
            )
            for row in rows
        )
        richer_asset_count = sum(
            bool(
                ((row.get("semantic_lineage") or {}).get("selection_fidelity") or {}).get(
                    "richer_language_asset_present"
                )
            )
            for row in rows
        )
        exact_or_semantic = sum(
            str(
                ((row.get("semantic_lineage") or {}).get("selection_fidelity") or {}).get(
                    "mode"
                )
                or ""
            )
            in {
                "EXACT_SCENE_LINEAGE",
                "SCENE_SEMANTIC_AND_LANGUAGE_ASSET_COMPATIBLE",
                "SCENE_SEMANTIC_COMPATIBLE",
            }
            for row in rows
        )
        if (
            form_ordinal in _CONTEXT_CUE_FORMS
            and exact_or_semantic == 0
            and semantic_signal_hits == 0
        ):
            errors.append(f"GUIDED_SCENE_SEMANTIC_SIGNAL_MISSING:{ref}")
        if form_ordinal in _CONTEXT_CUE_FORMS and richer_asset_count == 0:
            errors.append(f"GUIDED_SCENE_LANGUAGE_ASSET_CONSUMPTION_MISSING:{ref}")

        stimulus_signatures = [
            signature
            for signature in (_safe_stimulus_signature(row) for row in rows)
            if signature
        ]
        duplicate_stimuli = len(stimulus_signatures) - len(set(stimulus_signatures))
        if duplicate_stimuli:
            errors.append(
                f"LEARNER_VISIBLE_STIMULUS_DUPLICATE_WITHIN_SCENE:{ref}:{duplicate_stimuli}"
            )

        noun_counts = Counter(
            str(
                ((row.get("semantic_lineage") or {}).get("selection_fidelity") or {}).get(
                    "noun"
                )
                or ""
            )
            for row in rows
        )
        vocabulary_refs: set[str] = set()
        chunk_refs: set[str] = set()
        sentence_refs: set[str] = set()
        content_asset_ids: set[str] = set()
        for row in rows:
            assets = (row.get("semantic_lineage") or {}).get("language_asset_lineage") or {}
            vocabulary_refs.update(str(value) for value in assets.get("vocabulary_refs") or [])
            chunk_refs.update(str(value) for value in assets.get("chunk_refs") or [])
            sentence_refs.update(str(value) for value in assets.get("sentence_refs") or [])
            content_asset_ids.update(str(value) for value in assets.get("content_asset_ids") or [])
        scene_reports.append(
            {
                "scene_ref_id": ref,
                "activity_count": len(rows),
                "semantic_signal_hit_count": semantic_signal_hits,
                "exact_or_semantic_compatible_activity_count": exact_or_semantic,
                "richer_language_asset_activity_count": richer_asset_count,
                "target_noun_counts": dict(
                    sorted((key, value) for key, value in noun_counts.items() if key)
                ),
                "vocabulary_ref_count": len(vocabulary_refs),
                "chunk_ref_count": len(chunk_refs),
                "sentence_ref_count": len(sentence_refs),
                "content_asset_count": len(content_asset_ids),
                "learner_visible_stimulus_duplicate_count": duplicate_stimuli,
            }
        )

    form_ids = {
        str(payload.get("form_id") or "")
        for payload in skill_payloads.values()
        if payload
    }
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "form_id": next(iter(form_ids)) if len(form_ids) == 1 else "",
        "form_ordinal": form_ordinal,
        "activity_count": len(items),
        "scene_count": len(by_scene),
        "scene_reports": scene_reports,
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "next_short_step": NEXT_SHORT_STEP,
    }


def require_form_components_pass(
    skill_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    report = validate_form_components(skill_payloads)
    if report["error_count"]:
        raise MicroSceneSemanticLineageError(
            "SEMANTIC_E2E_FAIL:" + "|".join(str(row) for row in report["errors"])
        )
    return report


def install() -> None:
    """Install only internal delegates; preserve U16C/U18C public ownership."""
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if not u16c.installed():
        raise MicroSceneSemanticLineageError("U01QB16C_REQUIRED_BEFORE_U01QB18E")
    if not quality.installed():
        raise MicroSceneSemanticLineageError("U01QB18C_REQUIRED_BEFORE_U01QB18E")
    if u16c._ORIGINAL_ASSEMBLE is not _ORIGINAL_U16C_DELEGATE_ASSEMBLER:
        raise MicroSceneSemanticLineageError("U01QB16C_INTERNAL_DELEGATE_ALREADY_PATCHED")
    if quality._ORIGINAL_FORM_COMPONENT_PAYLOAD is not _ORIGINAL_18C_BASE_PAYLOAD:
        raise MicroSceneSemanticLineageError("U01QB18C_BASE_PAYLOAD_DELEGATE_ALREADY_PATCHED")
    if quality.repair_learner_item is not _ORIGINAL_18C_REPAIR:
        raise MicroSceneSemanticLineageError("U01QB18C_REPAIR_DELEGATE_ALREADY_PATCHED")

    u16c._ORIGINAL_ASSEMBLE = assemble_form_component_with_semantic_rank
    quality._ORIGINAL_FORM_COMPONENT_PAYLOAD = (
        base_form_component_payload_with_semantic_lineage
    )
    quality.repair_learner_item = repair_learner_item_with_semantic_lineage
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and u16c._ORIGINAL_ASSEMBLE is assemble_form_component_with_semantic_rank
        and quality._ORIGINAL_FORM_COMPONENT_PAYLOAD
        is base_form_component_payload_with_semantic_lineage
        and quality.repair_learner_item is repair_learner_item_with_semantic_lineage
        and u16c.installed()
        and quality.installed()
    )
