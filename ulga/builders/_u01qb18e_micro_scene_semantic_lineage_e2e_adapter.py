"""Preserve Unit01 micro-scene semantics through learner-facing Form projection.

U01QB18E closes a cross-layer acceptance gap exposed by the exact fresh Form01
review: approved micro-scenes retained objects/actions/relations/goals upstream,
while U01QB13 runtime matching consumed mostly noun anchors and U01QB18C learner
scaffolds could replace the selected item's learner-visible scene context.

This adapter does not author assessed content or create a second selector. It:

* reconstructs the already-approved U01QB14R1 scene semantic authority;
* prepends semantic-fidelity signals to the existing U01QB13 candidate rank only
  while the existing matcher is assembling a form component;
* composes a learner-safe scene context card with the U01QB18C scaffold instead
  of replacing all scene context;
* attaches private/internal semantic lineage evidence to the component payload;
* emits a fail-closed semantic E2E report that can be aggregated across the
  Reading/Writing/Speaking components of one logical form.

The current 474-item QuestionBank, U01QB13 blueprint, U01QB16 distinctness,
U01QB18C content gate, M3/M6 state/scoring and learner database remain the only
authorities. No Unit02-24 content, audio, Speaking scoring or A2 content is added.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as visible
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
    "Product-scoped semantic-lineage and learner-projection adapter over already-approved "
    "Unit01 micro-scenes and the existing U01QB13/U01QB16/U01QB18C path. It only "
    "re-ranks existing eligible catalog candidates by approved scene semantic fidelity, "
    "composes learner-safe scene metadata with existing scaffolds, and validates lineage; "
    "it authors no assessed item, changes no 474-item denominator, creates no second "
    "selector/runtime/planner/database/scoring authority, modifies no Unit02-24 content, "
    "enables no audio/Speaking score, and unlocks no A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18E_Unit01MicroSceneToLearnerFormSemanticLineageE2EFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18E_UNIT01_MICRO_SCENE_TO_LEARNER_FORM_SEMANTIC_LINEAGE_E2E_FULLFIX"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18E_UNIT01_MICRO_SCENE_TO_LEARNER_FORM_SEMANTIC_LINEAGE_E2E_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F_Unit01TwelveFormSemanticLineageReplayAndPedagogicalReacceptance"

_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)
_CONTEXT_CUE_FORMS = frozenset({1, 2, 3})
_REQUIRED_SCENE_SEMANTIC_SIGNAL_FOR_GUIDED = True

_BASE_MATCHING_ASSEMBLER = matching.assemble_form_component
_DELEGATE_MATCHING_ASSEMBLER = None
_DELEGATE_FORM_COMPONENT_PAYLOAD = None
_ACTIVE_CANDIDATE_RANK = None
_ACTIVE_ACTIVITY_SEMANTICS: dict[str, dict[str, Any]] = {}
_INSTALLED = False


class MicroSceneSemanticLineageError(ValueError):
    """Fail-closed cross-layer scene semantic lineage error."""


def _words(value: Any) -> set[str]:
    return {token.casefold() for token in _WORD_RE.findall(str(value or ""))}


def _private_item(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("private_item_json")
    try:
        value = json.loads(str(raw))
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
    parts = [str(item.get("stimulus") or ""), str(item.get("prompt") or "")]
    content = item.get("content")
    if isinstance(content, Mapping):
        parts.extend(str(row) for row in content.get("sentences") or [])
        parts.extend(
            str(row.get("utterance") or "")
            for row in content.get("dialogue_turns") or []
            if isinstance(row, Mapping)
        )
    return " ".join(part for part in parts if part.strip())


def _action_hit(action: str, words: set[str]) -> bool:
    base = str(action).strip().casefold()
    if not base:
        return False
    variants = {base, f"{base}s", f"{base}es"}
    if base.endswith("e"):
        variants.add(f"{base[:-1]}ing")
    else:
        variants.add(f"{base}ing")
    return bool(variants & words)


def semantic_fidelity(
    *,
    scene_ref_id: str,
    semantics: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one already-eligible item against one approved micro-scene."""
    text = _visible_text(item)
    words = _words(text)
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
    noun_bound = bool(noun) and noun in (objects | anchors)
    semantic_signal_hits = len(relation_hits) + len(action_hits) + len(setting_hits)

    if exact_scene_identity:
        tier = 0
        mode = "EXACT_SCENE_LINEAGE"
    elif noun_bound and semantic_signal_hits:
        tier = 1
        mode = "SCENE_SEMANTIC_COMPATIBLE"
    elif content_asset_id and noun_bound:
        tier = 2
        mode = "CONTENT_ASSET_LEXICAL_COMPATIBLE"
    elif noun_bound:
        tier = 3
        mode = "LEXICAL_ANCHOR_ONLY"
    else:
        tier = 4
        mode = "SCENE_SEMANTIC_UNBOUND"

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
        "semantic_signal_hit_count": semantic_signal_hits,
        "content_asset_id": content_asset_id,
        "item_context_id": item_context,
    }


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
    )
    if base is None:
        return None
    context = _ACTIVE_ACTIVITY_SEMANTICS.get(str(activity_id))
    if context is None or row.get("private_item_json") in (None, ""):
        return base
    item = _private_item(row)
    fidelity = semantic_fidelity(
        scene_ref_id=str(context["scene_ref_id"]),
        semantics=context["semantics"],
        item=item,
    )
    # Prepend only quality signals. Existing exposure/assessment/tie-breaking rank
    # remains authoritative inside each semantic-fidelity tier.
    return (
        int(fidelity["tier"]),
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


def assemble_form_component_with_semantic_lineage(
    database,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
):
    """Delegate to the existing matcher while adding semantic rank context only."""
    global _ACTIVE_CANDIDATE_RANK, _ACTIVE_ACTIVITY_SEMANTICS
    delegate = _DELEGATE_MATCHING_ASSEMBLER
    if delegate is None:
        raise MicroSceneSemanticLineageError("MATCHING_ASSEMBLER_DELEGATE_NOT_INSTALLED")
    previous_rank = target._candidate_rank
    previous_context = _ACTIVE_ACTIVITY_SEMANTICS
    _ACTIVE_CANDIDATE_RANK = previous_rank
    _ACTIVE_ACTIVITY_SEMANTICS = _activity_semantics(Path(database), int(form_ordinal))
    target._candidate_rank = _candidate_rank_with_scene_semantics
    try:
        return delegate(
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


def _scene_context_card(
    *,
    semantics: Mapping[str, Any],
    form_ordinal: int,
) -> str:
    """Project existing approved scene metadata without inventing answer content."""
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
    parts = []
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
        private_item = _private_item(row)
        result[str(row["activity_id"])] = {
            "form_ordinal": int(row["form_ordinal"]),
            "scene_ref_id": ref,
            "skill": str(row["skill"]),
            "task_angle": str(row["task_angle"]),
            "item_id": str(row["item_id"]),
            "private_item": private_item,
            "semantics": deepcopy(dict(semantics)),
            "fidelity": semantic_fidelity(
                scene_ref_id=ref,
                semantics=semantics,
                item=private_item,
            ),
        }
    return result


def form_component_payload_with_semantic_lineage(
    connection,
    *,
    session_id: str,
) -> dict[str, Any]:
    delegate = _DELEGATE_FORM_COMPONENT_PAYLOAD
    if delegate is None:
        raise MicroSceneSemanticLineageError("FORM_PAYLOAD_DELEGATE_NOT_INSTALLED")
    value = delegate(connection, session_id=session_id)
    metadata = _binding_metadata(connection, session_id)
    repaired = []
    lineage_rows = []
    for source in value.get("items") or []:
        activity_id = str(source.get("activity_id") or "")
        meta = metadata.get(activity_id)
        if meta is None:
            raise MicroSceneSemanticLineageError(
                f"FORM_COMPONENT_ACTIVITY_LINEAGE_MISSING:{activity_id}"
            )
        row = dict(source)
        card = _scene_context_card(
            semantics=meta["semantics"],
            form_ordinal=int(meta["form_ordinal"]),
        )
        row["stimulus"] = _prepend_context_card(str(row.get("stimulus") or ""), card)
        fidelity = deepcopy(meta["fidelity"])
        lineage = {
            "scene_ref_id": meta["scene_ref_id"],
            "scene_source": str(meta["semantics"].get("source") or ""),
            "scene_event": str(meta["semantics"].get("event") or ""),
            "scene_objects": list(meta["semantics"].get("objects") or []),
            "scene_actions": list(meta["semantics"].get("action") or []),
            "scene_relations": list(meta["semantics"].get("relations") or []),
            "communicative_goal": str(meta["semantics"].get("communicative_goal") or ""),
            "selection_fidelity": fidelity,
            "learner_scene_context_card": card,
            "scene_context_preserved": bool(card and card.casefold() in str(row["stimulus"]).casefold()),
        }
        row["semantic_lineage"] = lineage
        lineage_rows.append({"activity_id": activity_id, **deepcopy(lineage)})
        repaired.append(row)
    value["items"] = repaired
    value["semantic_lineage_rows"] = lineage_rows
    value["semantic_lineage_fullfix"] = PASS_STATUS
    return value


def validate_form_components(
    skill_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate one logical form after all three skill components are materialized."""
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

    scene_reports = []
    for ref, rows in sorted(by_scene.items()):
        if len(rows) != target.ACTIVITIES_PER_SCENE:
            errors.append(f"SCENE_ACTIVITY_COUNT_INVALID:{ref}:{len(rows)}")
        semantic_signal_hits = sum(
            int(((row.get("semantic_lineage") or {}).get("selection_fidelity") or {}).get("semantic_signal_hit_count", 0))
            for row in rows
        )
        exact_or_semantic = sum(
            str(((row.get("semantic_lineage") or {}).get("selection_fidelity") or {}).get("mode") or "")
            in {"EXACT_SCENE_LINEAGE", "SCENE_SEMANTIC_COMPATIBLE"}
            for row in rows
        )
        form_ordinal = int(next(iter(skill_payloads.values())).get("form_ordinal", 0) or 0)
        if (
            _REQUIRED_SCENE_SEMANTIC_SIGNAL_FOR_GUIDED
            and form_ordinal in _CONTEXT_CUE_FORMS
            and semantic_signal_hits == 0
            and exact_or_semantic == 0
        ):
            errors.append(f"GUIDED_SCENE_SEMANTIC_SIGNAL_MISSING:{ref}")
        signatures = [
            visible.learner_visible_signature(
                {
                    "item_id": str(row.get("item_id") or ""),
                    "skill": str(row.get("skill") or ""),
                    "private_item_json": json.dumps(
                        {
                            "stimulus": row.get("stimulus") or "",
                            "prompt": row.get("prompt") or "",
                            "options": row.get("options") or [],
                        }
                    ),
                }
            )
            for row in rows
        ]
        if len(signatures) != len(set(signatures)):
            errors.append(f"LEARNER_VISIBLE_DUPLICATE_WITHIN_SCENE:{ref}")
        noun_counts = Counter(
            str(((row.get("semantic_lineage") or {}).get("selection_fidelity") or {}).get("noun") or "")
            for row in rows
        )
        scene_reports.append(
            {
                "scene_ref_id": ref,
                "activity_count": len(rows),
                "semantic_signal_hit_count": semantic_signal_hits,
                "exact_or_semantic_compatible_activity_count": exact_or_semantic,
                "target_noun_counts": dict(sorted((key, value) for key, value in noun_counts.items() if key)),
                "learner_visible_duplicate_count": len(signatures) - len(set(signatures)),
            }
        )

    form_ids = {
        str(payload.get("form_id") or "")
        for payload in skill_payloads.values()
        if payload
    }
    form_ordinals = {
        int(payload.get("form_ordinal", 0) or 0)
        for payload in skill_payloads.values()
        if payload
    }
    report = {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "form_id": next(iter(form_ids)) if len(form_ids) == 1 else "",
        "form_ordinal": next(iter(form_ordinals)) if len(form_ordinals) == 1 else 0,
        "activity_count": len(items),
        "scene_count": len(by_scene),
        "scene_reports": scene_reports,
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "next_short_step": NEXT_SHORT_STEP,
    }
    return report


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
    """Install after U01QB18C; keep all selector/scoring authorities singular."""
    global _INSTALLED, _DELEGATE_MATCHING_ASSEMBLER, _DELEGATE_FORM_COMPONENT_PAYLOAD
    if _INSTALLED:
        return
    if not quality.installed():
        raise MicroSceneSemanticLineageError("U01QB18C_REQUIRED_BEFORE_U01QB18E")

    _DELEGATE_MATCHING_ASSEMBLER = matching.assemble_form_component
    _DELEGATE_FORM_COMPONENT_PAYLOAD = target.form_component_payload
    if _DELEGATE_FORM_COMPONENT_PAYLOAD is not quality.form_component_payload_with_learner_quality:
        raise MicroSceneSemanticLineageError(
            "U01QB18C_FORM_COMPONENT_PAYLOAD_NOT_ACTIVE"
        )

    # Patch the modern matcher module object before matching.install() binds it
    # into U01QB13. If matching was already installed, update that exact pointer
    # only; do not replace a different/legacy selector authority.
    matching.assemble_form_component = assemble_form_component_with_semantic_lineage
    if target.assemble_form_component is _DELEGATE_MATCHING_ASSEMBLER:
        target.assemble_form_component = assemble_form_component_with_semantic_lineage
    elif target.assemble_form_component not in {
        target.assemble_form_component,
        assemble_form_component_with_semantic_lineage,
    }:
        raise MicroSceneSemanticLineageError("U01QB13_SELECTOR_AUTHORITY_CONFLICT")

    target.form_component_payload = form_component_payload_with_semantic_lineage
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and matching.assemble_form_component is assemble_form_component_with_semantic_lineage
        and target.form_component_payload is form_component_payload_with_semantic_lineage
    )
