#!/usr/bin/env python3
"""Bind the final Unit01 240 learner activities to final QB items and sentence assets.

U01SA06A is a private read-only closeout consumer.  It reuses the already accepted
U01QB18F-R4 product replay to capture the exact activity -> selected-item mapping,
then reconciles those final selected items against the already-approved U01SA05R2
3805-sentence/474-QB binding authority plus the sentence lineage embedded by the
U01QB18H-R2R2 exact-slot materialization.

It does not rerun the global SA05R2 3805x474 matcher, author sentences/questions,
mutate the learner database, create another QuestionBank/runtime/planner/scoring
authority, modify Unit02-24, enable Speaking scoring, or unlock A2.  A bounded
semantic bridge is permitted only for a final selected item identity introduced
after SA05R2: it may reuse an already-approved SA05R2 binding row for the same
referent/article-NP/discourse role and must revalidate every referenced sentence
against the unchanged admitted 3805 pool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18f_r4_full_semantic_language_pedagogical_replay as r4,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private read-only Unit01 closeout validator over the accepted U01QB18F-R4 "
    "selection path, existing U01SA05R2 3805-sentence/474-QB binding evidence, "
    "and U01QB18H-R2R2 exact-slot sentence lineage. It authors and mutates no "
    "content, QuestionBank, runtime, planner, learner state, scoring authority, "
    "Unit02-24 content, audio/Speaking score, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01SA06A_Unit01Final240ActivityQuestionBankAndSentenceAssetBinding"
PASS_STATUS = "PASS_A1FS_V1_U01SA06A_UNIT01_FINAL240_ACTIVITY_QB_SENTENCE_ASSET_BINDING"
FAIL_STATUS = "FAIL_A1FS_V1_U01SA06A_UNIT01_FINAL240_ACTIVITY_QB_SENTENCE_ASSET_BINDING"
NEXT_SHORT_STEP = "A1FS-V1-U01SA06B_Unit01FinalLearnerProductBindingCloseout"
SA05R2_TASK_ID = (
    "A1FS-V1-U01SA05R2_"
    "Full3805SentencePoolCapabilityCoverageAndUnit01QuestionBankResidualBindingReconciliation"
)
EXPECTED_POOL_TOTAL = 3805
EXPECTED_RUNTIME_ITEMS = 474
EXPECTED_FORMS = 12
EXPECTED_SCENE_EXPOSURES = 48
EXPECTED_ACTIVITY_BINDINGS = 240
REPLAY_LEARNER_ID = "U01SA06A_FINAL240_BINDING_REPLAY"

_FIRST_FAMILIES = frozenset(
    {"U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"}
)
_KNOWN_FAMILIES = frozenset({"U01-PF05-KNOWN-REFERENCE-CONTEXT"})
_REFERENCE_FAMILIES = frozenset({"U01-PF16-READING-REFERENCE-EVIDENCE"})


class Final240BindingError(ValueError):
    """Fail-closed U01SA06A validation error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    path = Path(path).resolve(strict=True)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Final240BindingError(f"JSON_UNREADABLE:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise Final240BindingError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
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


def _pool_index(pool: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if str(pool.get("task_id") or "") != SA05R2_TASK_ID:
        raise Final240BindingError("SENTENCE_POOL_TASK_ID_INVALID")
    if int(pool.get("sentence_pool_total", -1)) != EXPECTED_POOL_TOTAL:
        raise Final240BindingError(
            f"SENTENCE_POOL_TOTAL_INVALID:{pool.get('sentence_pool_total')}:{EXPECTED_POOL_TOTAL}"
        )
    profiles = list(pool.get("profiles") or [])
    if len(profiles) != EXPECTED_POOL_TOTAL:
        raise Final240BindingError(
            f"SENTENCE_PROFILE_COUNT_INVALID:{len(profiles)}:{EXPECTED_POOL_TOTAL}"
        )
    result: dict[str, Mapping[str, Any]] = {}
    for row in profiles:
        if not isinstance(row, Mapping):
            raise Final240BindingError("SENTENCE_PROFILE_OBJECT_REQUIRED")
        sentence_id = str(row.get("sentence_id") or "")
        if not sentence_id or sentence_id in result:
            raise Final240BindingError(f"SENTENCE_ID_DUPLICATE_OR_MISSING:{sentence_id}")
        if str(row.get("canonical_admission_status") or "") != "ADMITTED":
            raise Final240BindingError(f"SENTENCE_NOT_ADMITTED:{sentence_id}")
        result[sentence_id] = row
    return result


def _sa05r2_bindings(rebind: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if str(rebind.get("task_id") or "") != SA05R2_TASK_ID:
        raise Final240BindingError("SA05R2_REBIND_TASK_ID_INVALID")
    if int(rebind.get("questionbank_total", -1)) != EXPECTED_RUNTIME_ITEMS:
        raise Final240BindingError("SA05R2_REBIND_DENOMINATOR_INVALID")
    if list(rebind.get("unresolved") or []):
        raise Final240BindingError("SA05R2_REBIND_NOT_CLEAN")
    values = list(rebind.get("bindings") or [])
    if len(values) != EXPECTED_RUNTIME_ITEMS:
        raise Final240BindingError(
            f"SA05R2_BINDING_COUNT_INVALID:{len(values)}:{EXPECTED_RUNTIME_ITEMS}"
        )
    result: dict[str, Mapping[str, Any]] = {}
    for row in values:
        if not isinstance(row, Mapping):
            raise Final240BindingError("SA05R2_BINDING_OBJECT_REQUIRED")
        item_id = str(row.get("item_id") or "")
        if not item_id or item_id in result:
            raise Final240BindingError(f"SA05R2_ITEM_ID_DUPLICATE_OR_MISSING:{item_id}")
        if str(row.get("disposition") or "") != "BOUND":
            raise Final240BindingError(f"SA05R2_ITEM_NOT_BOUND:{item_id}")
        result[item_id] = row
    return result


def _catalog(database: Path) -> dict[str, dict[str, Any]]:
    database = Path(database).resolve(strict=True)
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """SELECT item_id,skill,pattern_family_id,private_item_json,item_digest
               FROM u01qb02_item_catalog ORDER BY item_id"""
        ).fetchall()
    finally:
        connection.close()
    if len(rows) != EXPECTED_RUNTIME_ITEMS:
        raise Final240BindingError(
            f"FINAL_RUNTIME_ITEM_COUNT_INVALID:{len(rows)}:{EXPECTED_RUNTIME_ITEMS}"
        )
    result: dict[str, dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        try:
            private = json.loads(str(row["private_item_json"]))
        except json.JSONDecodeError as exc:
            raise Final240BindingError(
                f"PRIVATE_ITEM_JSON_INVALID:{row.get('item_id')}"
            ) from exc
        if not isinstance(private, dict):
            raise Final240BindingError(f"PRIVATE_ITEM_OBJECT_REQUIRED:{row.get('item_id')}")
        row["private_item"] = private
        result[str(row["item_id"])] = row
    return result


def _capture_exact_activity_bindings(database: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Reuse R4 and capture its private activity -> selected-item mapping in memory."""
    captured: list[dict[str, Any]] = []
    original = r4._ORIGINAL_FORM_RECORD

    def capture(
        *,
        learner_id: str,
        form_ordinal: int,
        skill_payloads: Mapping[str, Mapping[str, Any]],
        blueprint_rows: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        selected = r4.base._selected_by_activity(skill_payloads)
        blueprint_by_id = {
            str(row.get("activity_id") or ""): row for row in blueprint_rows
        }
        if len(selected) != r4.base.EXPECTED_ACTIVITIES_PER_FORM:
            raise Final240BindingError(
                f"CAPTURED_FORM_ACTIVITY_COUNT_INVALID:{form_ordinal}:{len(selected)}"
            )
        for activity_id, item in selected.items():
            blueprint = blueprint_by_id.get(str(activity_id))
            if blueprint is None:
                raise Final240BindingError(
                    f"CAPTURED_ACTIVITY_BLUEPRINT_MISSING:{form_ordinal}:{activity_id}"
                )
            captured.append(
                {
                    "activity_id": str(activity_id),
                    "form_id": str(blueprint.get("form_id") or f"U01-FORM-{form_ordinal:02d}"),
                    "form_ordinal": int(form_ordinal),
                    "scene_ref_id": str(blueprint.get("scene_ref_id") or ""),
                    "skill": str(blueprint.get("skill") or ""),
                    "task_angle": str(blueprint.get("task_angle") or ""),
                    "support_level": str(blueprint.get("support_level") or ""),
                    "item_id": str(item.get("item_id") or ""),
                }
            )
        return original(
            learner_id=learner_id,
            form_ordinal=form_ordinal,
            skill_payloads=skill_payloads,
            blueprint_rows=blueprint_rows,
        )

    r4._ORIGINAL_FORM_RECORD = capture
    try:
        with tempfile.TemporaryDirectory(prefix="a1fs_u01sa06a_r4_") as temporary:
            replay_path = Path(temporary) / "u01sa06a_r4.json"
            replay = r4.materialize_full_replay(
                database=Path(database),
                output=replay_path,
                learner_id=REPLAY_LEARNER_ID,
            )
    finally:
        r4._ORIGINAL_FORM_RECORD = original

    if str(replay.get("validation_status") or "") != r4.PASS_STATUS:
        raise Final240BindingError("U01SA06A_R4_REPLAY_NOT_PASS")
    if int(replay.get("form_count", -1)) != EXPECTED_FORMS:
        raise Final240BindingError("U01SA06A_R4_FORM_COUNT_INVALID")
    if int(replay.get("scene_exposure_count", -1)) != EXPECTED_SCENE_EXPOSURES:
        raise Final240BindingError("U01SA06A_R4_SCENE_EXPOSURE_COUNT_INVALID")
    if int(replay.get("learner_visible_activity_count", -1)) != EXPECTED_ACTIVITY_BINDINGS:
        raise Final240BindingError("U01SA06A_R4_ACTIVITY_COUNT_INVALID")
    if len(captured) != EXPECTED_ACTIVITY_BINDINGS:
        raise Final240BindingError(
            f"CAPTURED_ACTIVITY_BINDING_COUNT_INVALID:{len(captured)}:{EXPECTED_ACTIVITY_BINDINGS}"
        )
    activity_ids = [row["activity_id"] for row in captured]
    if len(activity_ids) != len(set(activity_ids)):
        raise Final240BindingError("CAPTURED_ACTIVITY_BINDING_DUPLICATE")
    return replay, sorted(captured, key=lambda row: row["activity_id"])


def _target_noun(private: Mapping[str, Any]) -> str:
    slots = private.get("lexical_slots") or {}
    if isinstance(slots, Mapping):
        for key in ("noun", "target_noun", "item", "target"):
            value = str(slots.get(key) or "").strip().casefold()
            if value:
                return value
    for key in ("noun", "target_noun", "item", "target"):
        value = str(private.get(key) or "").strip().casefold()
        if value:
            return value
    return ""


def _desired_determiner(private: Mapping[str, Any], family: str) -> str:
    if family in _FIRST_FAMILIES:
        answer = str(private.get("correct_answer") or "").strip().casefold()
        return answer if answer in {"a", "an"} else ""
    if family in _KNOWN_FAMILIES or family in _REFERENCE_FAMILIES:
        return "the"
    return ""


def _bridge_task_rank(family: str, legacy_task_angle: str) -> int | None:
    angle = str(legacy_task_angle or "")
    if family == "U01-PF04-FIRST-MENTION-CONTEXT":
        return {"FIRST_MENTION": 0, "FIRST_MENTION_TRANSFER": 1}.get(angle)
    if family == "U01-PF08-TRANSFER-FIRST-MENTION":
        return {"FIRST_MENTION_TRANSFER": 0, "FIRST_MENTION": 1}.get(angle)
    if family == "U01-PF05-KNOWN-REFERENCE-CONTEXT":
        return {"KNOWN_REFERENCE": 0, "KNOWN_REFERENCE_TRANSFER": 1}.get(angle)
    if family == "U01-PF16-READING-REFERENCE-EVIDENCE":
        return {
            "REFERENCE_EVIDENCE": 0,
            "KNOWN_REFERENCE": 1,
            "KNOWN_REFERENCE_TRANSFER": 2,
        }.get(angle)
    return None


def _bridge_binding(
    *,
    item_id: str,
    family: str,
    private: Mapping[str, Any],
    sa05r2_rows: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Reuse only already-approved SA05R2 evidence for a post-SA05R2 item identity."""
    noun = _target_noun(private)
    determiner = _desired_determiner(private, family)
    context_id = str(private.get("context_id") or "")
    if not noun or not determiner:
        raise Final240BindingError(f"POST_SA05R2_BRIDGE_DEMAND_UNSUPPORTED:{item_id}:{family}")

    candidates: list[tuple[tuple[Any, ...], Mapping[str, Any]]] = []
    for row in sa05r2_rows:
        task_rank = _bridge_task_rank(family, str(row.get("task_angle") or ""))
        if task_rank is None:
            continue
        target = row.get("target_np") or {}
        compatibility = row.get("compatibility") or {}
        if not isinstance(target, Mapping) or not isinstance(compatibility, Mapping):
            continue
        if str(target.get("canonical_surface") or "").strip().casefold() != noun:
            continue
        if str(target.get("determiner") or "").strip().casefold() != determiner:
            continue
        if str(target.get("structure") or "NOUN").upper() != "NOUN":
            continue
        if compatibility.get("candidate_compatible") is not True:
            continue
        if not str(row.get("primary_sentence_ref") or ""):
            continue
        if family in (_KNOWN_FAMILIES | _REFERENCE_FAMILIES) and not str(
            row.get("antecedent_sentence_ref") or ""
        ):
            continue
        legacy_item_id = str(row.get("item_id") or "")
        scene_exact = 0 if str(compatibility.get("scene_ref") or "") == context_id else 1
        context_identity = 0 if context_id and context_id in legacy_item_id else 1
        generic = 0 if str(compatibility.get("scene_binding_mode") or "") == "GENERIC_SCENE_NEUTRAL" else 1
        score = (scene_exact, context_identity, task_rank, generic, legacy_item_id)
        candidates.append((score, row))

    if not candidates:
        raise Final240BindingError(f"POST_SA05R2_BRIDGE_EVIDENCE_MISSING:{item_id}")
    candidates.sort(key=lambda pair: pair[0])
    best_score = candidates[0][0][:-1]
    tied = [row for score, row in candidates if score[:-1] == best_score]
    # Multiple legacy item identities may intentionally share the same exact sentence
    # evidence.  Fail only if the top semantic rank would produce different sentence
    # evidence, not merely a different historical item ID.
    evidence = {
        (
            str(row.get("primary_sentence_ref") or ""),
            str(row.get("antecedent_sentence_ref") or ""),
            tuple(str(value) for value in row.get("support_sentence_refs") or []),
        )
        for row in tied
    }
    if len(evidence) != 1:
        raise Final240BindingError(
            f"POST_SA05R2_BRIDGE_AMBIGUOUS:{item_id}:{len(tied)}:{len(evidence)}"
        )
    return candidates[0][1]


def _profile_has_target(profile: Mapping[str, Any], *, noun: str, entity_id: str = "") -> bool:
    noun = str(noun or "").strip().casefold()
    entity_id = str(entity_id or "").strip().upper()
    for slot in profile.get("np_slots") or []:
        if not isinstance(slot, Mapping):
            continue
        slot_noun = str(slot.get("canonical_surface") or "").strip().casefold()
        slot_entity = str(slot.get("entity_id") or "").strip().upper()
        if entity_id and slot_entity == entity_id:
            return True
        if noun and slot_noun == noun:
            return True
    return False


def _validate_sentence_evidence(
    *,
    item_id: str,
    sentence_ids: Sequence[str],
    pool: Mapping[str, Mapping[str, Any]],
    noun: str,
    entity_id: str = "",
) -> None:
    if not sentence_ids:
        raise Final240BindingError(f"SENTENCE_EVIDENCE_EMPTY:{item_id}")
    for sentence_id in sentence_ids:
        profile = pool.get(str(sentence_id))
        if profile is None:
            raise Final240BindingError(
                f"SENTENCE_REF_NOT_IN_3805_POOL:{item_id}:{sentence_id}"
            )
        if not _profile_has_target(profile, noun=noun, entity_id=entity_id):
            raise Final240BindingError(
                f"SENTENCE_TARGET_REFERENT_MISMATCH:{item_id}:{sentence_id}:{noun}:{entity_id}"
            )


def _resolve_sentence_binding(
    *,
    item_id: str,
    catalog_row: Mapping[str, Any],
    sa05r2_by_id: Mapping[str, Mapping[str, Any]],
    pool: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    private = catalog_row.get("private_item") or {}
    family = str(catalog_row.get("pattern_family_id") or "")
    noun = _target_noun(private)

    if item_id in sa05r2_by_id:
        source = sa05r2_by_id[item_id]
        target = source.get("target_np") or {}
        entity_id = str(target.get("entity_id") or "") if isinstance(target, Mapping) else ""
        noun = noun or (str(target.get("canonical_surface") or "").casefold() if isinstance(target, Mapping) else "")
        primary = str(source.get("primary_sentence_ref") or "")
        antecedent = str(source.get("antecedent_sentence_ref") or "") or None
        support = [str(value) for value in source.get("support_sentence_refs") or [] if str(value)]
        _validate_sentence_evidence(
            item_id=item_id,
            sentence_ids=[primary] + ([antecedent] if antecedent else []) + support,
            pool=pool,
            noun=noun,
            entity_id=entity_id,
        )
        return {
            "binding_source": "SA05R2_EXACT_ITEM_ID",
            "primary_sentence_ref": primary,
            "antecedent_sentence_ref": antecedent,
            "support_sentence_refs": support,
            "legacy_evidence_item_id": item_id,
        }

    source_sentence_ids = [
        str(value) for value in private.get("source_sentence_ids") or [] if str(value)
    ]
    source_task = str(private.get("sentence_pool_source_task_id") or "")
    if source_sentence_ids and source_task == SA05R2_TASK_ID:
        entity_id = str(private.get("sentence_pool_target_entity_id") or "")
        _validate_sentence_evidence(
            item_id=item_id,
            sentence_ids=source_sentence_ids,
            pool=pool,
            noun=noun,
            entity_id=entity_id,
        )
        antecedent = None
        if family == "U01-PF09-TRANSFER-KNOWN-REFERENCE":
            antecedent = str(private.get("contextual_reference_source_sentence_id") or "") or source_sentence_ids[0]
            if antecedent not in source_sentence_ids:
                raise Final240BindingError(
                    f"R2R2_CONTEXTUAL_REFERENCE_ANTECEDENT_NOT_SOURCE_BOUND:{item_id}:{antecedent}"
                )
        return {
            "binding_source": "R2R2_INLINE_SENTENCE_LINEAGE",
            "primary_sentence_ref": source_sentence_ids[0],
            "antecedent_sentence_ref": antecedent,
            "support_sentence_refs": source_sentence_ids[1:],
            "legacy_evidence_item_id": None,
        }

    bridge = _bridge_binding(
        item_id=item_id,
        family=family,
        private=private,
        sa05r2_rows=list(sa05r2_by_id.values()),
    )
    target = bridge.get("target_np") or {}
    entity_id = str(target.get("entity_id") or "") if isinstance(target, Mapping) else ""
    primary = str(bridge.get("primary_sentence_ref") or "")
    antecedent = str(bridge.get("antecedent_sentence_ref") or "") or None
    support = [str(value) for value in bridge.get("support_sentence_refs") or [] if str(value)]
    _validate_sentence_evidence(
        item_id=item_id,
        sentence_ids=[primary] + ([antecedent] if antecedent else []) + support,
        pool=pool,
        noun=noun,
        entity_id=entity_id,
    )
    return {
        "binding_source": "POST_SA05R2_IDENTITY_BRIDGE",
        "primary_sentence_ref": primary,
        "antecedent_sentence_ref": antecedent,
        "support_sentence_refs": support,
        "legacy_evidence_item_id": str(bridge.get("item_id") or ""),
    }


def materialize_final_binding(
    *,
    database: Path,
    sentence_pool_capability_index: Path,
    sa05r2_final474_rebind: Path,
    output: Path,
) -> dict[str, Any]:
    database = Path(database).resolve(strict=True)
    output = Path(output).resolve()
    if output == database:
        raise Final240BindingError("OUTPUT_MUST_NOT_OVERWRITE_DATABASE")
    database_before = _sha256(database)
    pool_path = Path(sentence_pool_capability_index).resolve(strict=True)
    rebind_path = Path(sa05r2_final474_rebind).resolve(strict=True)
    pool_json = _load_json(pool_path)
    rebind_json = _load_json(rebind_path)
    pool = _pool_index(pool_json)
    sa05r2_by_id = _sa05r2_bindings(rebind_json)
    catalog = _catalog(database)

    replay, selected = _capture_exact_activity_bindings(database)
    unresolved: list[dict[str, Any]] = []
    activity_bindings: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    for row in selected:
        item_id = str(row["item_id"])
        catalog_row = catalog.get(item_id)
        if catalog_row is None:
            unresolved.append(
                {"activity_id": row["activity_id"], "item_id": item_id, "reason": "ITEM_NOT_IN_FINAL474"}
            )
            continue
        try:
            sentence = _resolve_sentence_binding(
                item_id=item_id,
                catalog_row=catalog_row,
                sa05r2_by_id=sa05r2_by_id,
                pool=pool,
            )
        except Final240BindingError as exc:
            unresolved.append(
                {"activity_id": row["activity_id"], "item_id": item_id, "reason": str(exc)}
            )
            continue
        source = str(sentence["binding_source"])
        source_counts[source] = source_counts.get(source, 0) + 1
        activity_bindings.append(
            {
                **row,
                "pattern_family_id": str(catalog_row.get("pattern_family_id") or ""),
                **sentence,
            }
        )

    if unresolved:
        first = unresolved[0]
        raise Final240BindingError(
            f"FINAL240_UNRESOLVED:{len(unresolved)}:{first['activity_id']}:{first['item_id']}:{first['reason']}"
        )
    if len(activity_bindings) != EXPECTED_ACTIVITY_BINDINGS:
        raise Final240BindingError(
            f"FINAL240_BINDING_COUNT_INVALID:{len(activity_bindings)}:{EXPECTED_ACTIVITY_BINDINGS}"
        )
    if any(not row.get("primary_sentence_ref") for row in activity_bindings):
        raise Final240BindingError("FINAL240_PRIMARY_SENTENCE_REF_MISSING")

    database_after = _sha256(database)
    if database_after != database_before:
        raise Final240BindingError("SOURCE_DATABASE_MODIFIED")

    result = {
        "schema_version": "a1fs.v1.u01sa06a.final240_activity_qb_sentence_binding.v1",
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "form_count": int(replay["form_count"]),
        "scene_exposure_count": int(replay["scene_exposure_count"]),
        "activity_binding_count": len(activity_bindings),
        "selected_item_occurrence_count": len(activity_bindings),
        "selected_item_distinct_count": len({row["item_id"] for row in activity_bindings}),
        "runtime_item_count": len(catalog),
        "sentence_pool_total": len(pool),
        "binding_source_occurrence_counts": dict(sorted(source_counts.items())),
        "unresolved_count": 0,
        "unresolved": [],
        "activity_bindings": activity_bindings,
        "source_bindings": {
            "database_sha256": database_before,
            "sentence_pool_capability_index_sha256": _sha256(pool_path),
            "sa05r2_final474_rebind_sha256": _sha256(rebind_path),
            "r4_task_id": r4.TASK_ID,
            "sa05r2_task_id": SA05R2_TASK_ID,
        },
        "boundaries": {
            "sa05r2_global_matcher_rerun": False,
            "new_sentence_candidate_count": 0,
            "new_question_item_count": 0,
            "questionbank_modified": False,
            "source_database_modified": False,
            "scoring_contract_modified": False,
            "unit02_to_unit24_modified": False,
            "speaking_scoring_enabled": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    _atomic_json(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--sentence-pool-capability-index", type=Path, required=True)
    parser.add_argument("--sa05r2-final474-rebind", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = materialize_final_binding(
            database=args.database,
            sentence_pool_capability_index=args.sentence_pool_capability_index,
            sa05r2_final474_rebind=args.sa05r2_final474_rebind,
            output=args.output,
        )
    except (Final240BindingError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        print(f"STATUS={FAIL_STATUS}")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={value['validation_status']}")
    print(f"FORM_COUNT={value['form_count']}")
    print(f"SCENE_EXPOSURE_COUNT={value['scene_exposure_count']}")
    print(f"ACTIVITY_BINDING_COUNT={value['activity_binding_count']}")
    print(f"SELECTED_ITEM_DISTINCT_COUNT={value['selected_item_distinct_count']}")
    print(f"RUNTIME_ITEMS={value['runtime_item_count']}")
    print(f"SENTENCE_POOL_TOTAL={value['sentence_pool_total']}")
    print("BINDING_SOURCE_OCCURRENCE_COUNTS=" + json.dumps(value["binding_source_occurrence_counts"], sort_keys=True))
    print(f"UNRESOLVED={value['unresolved_count']}")
    print(f"OUTPUT={Path(args.output).resolve()}")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
