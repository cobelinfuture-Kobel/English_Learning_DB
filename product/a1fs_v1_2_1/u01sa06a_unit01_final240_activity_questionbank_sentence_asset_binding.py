#!/usr/bin/env python3
"""Validate final Unit01 240 activity -> QuestionBank -> sentence-asset bindings.

This is a private read-only closeout consumer. It reuses the accepted U01QB18F-R4
selection path, the approved U01SA05R2 3805-sentence/474-QB binding evidence, and
U01QB18H-R2R2 inline sentence lineage. It never reruns the global SA05R2 matcher.
Only post-SA05R2 selected item identities may use a bounded bridge over already-
approved SA05R2 bindings; every reused sentence is revalidated in the unchanged
3805 admitted pool, including sentence source-scene affinity.
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
    "Private read-only Unit01 closeout validator over accepted U01QB18F-R4 selection, "
    "U01SA05R2 3805-sentence/474-QB evidence and U01QB18H-R2R2 sentence lineage. "
    "It authors or mutates no content, QuestionBank, runtime, planner, learner state, "
    "scoring authority, Unit02-24 content, Speaking score, or A2 state."
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
FIRST_FAMILIES = frozenset(
    {"U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"}
)
KNOWN_FAMILIES = frozenset({"U01-PF05-KNOWN-REFERENCE-CONTEXT"})
REFERENCE_FAMILIES = frozenset({"U01-PF16-READING-REFERENCE-EVIDENCE"})


class Final240BindingError(ValueError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).resolve(strict=True).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Final240BindingError(f"JSON_UNREADABLE:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise Final240BindingError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _pool_index(value: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if value.get("task_id") != SA05R2_TASK_ID:
        raise Final240BindingError("SENTENCE_POOL_TASK_ID_INVALID")
    profiles = list(value.get("profiles") or [])
    if int(value.get("sentence_pool_total", -1)) != EXPECTED_POOL_TOTAL or len(profiles) != EXPECTED_POOL_TOTAL:
        raise Final240BindingError("SENTENCE_POOL_3805_REQUIRED")
    result: dict[str, Mapping[str, Any]] = {}
    for row in profiles:
        if not isinstance(row, Mapping):
            raise Final240BindingError("SENTENCE_PROFILE_OBJECT_REQUIRED")
        sid = str(row.get("sentence_id") or "")
        if not sid or sid in result:
            raise Final240BindingError(f"SENTENCE_ID_DUPLICATE_OR_MISSING:{sid}")
        if row.get("canonical_admission_status") != "ADMITTED":
            raise Final240BindingError(f"SENTENCE_NOT_ADMITTED:{sid}")
        result[sid] = row
    return result


def _sa05r2_bindings(value: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if value.get("task_id") != SA05R2_TASK_ID:
        raise Final240BindingError("SA05R2_REBIND_TASK_ID_INVALID")
    rows = list(value.get("bindings") or [])
    if int(value.get("questionbank_total", -1)) != EXPECTED_RUNTIME_ITEMS or len(rows) != EXPECTED_RUNTIME_ITEMS:
        raise Final240BindingError("SA05R2_REBIND_474_REQUIRED")
    if value.get("unresolved"):
        raise Final240BindingError("SA05R2_REBIND_NOT_CLEAN")
    result = {}
    for row in rows:
        iid = str(row.get("item_id") or "")
        if not iid or iid in result or row.get("disposition") != "BOUND":
            raise Final240BindingError(f"SA05R2_BINDING_INVALID:{iid}")
        result[iid] = row
    return result


def _catalog(database: Path) -> dict[str, dict[str, Any]]:
    db = Path(database).resolve(strict=True)
    con = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT item_id,skill,pattern_family_id,private_item_json,item_digest "
            "FROM u01qb02_item_catalog ORDER BY item_id"
        ).fetchall()
    finally:
        con.close()
    if len(rows) != EXPECTED_RUNTIME_ITEMS:
        raise Final240BindingError(f"FINAL_RUNTIME_ITEM_COUNT_INVALID:{len(rows)}")
    result = {}
    for source in rows:
        row = dict(source)
        try:
            private = json.loads(str(row["private_item_json"]))
        except json.JSONDecodeError as exc:
            raise Final240BindingError(f"PRIVATE_ITEM_JSON_INVALID:{row['item_id']}") from exc
        if not isinstance(private, dict):
            raise Final240BindingError(f"PRIVATE_ITEM_OBJECT_REQUIRED:{row['item_id']}")
        row["private_item"] = private
        result[str(row["item_id"])] = row
    return result


def _capture_exact_activity_bindings(database: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    captured: list[dict[str, Any]] = []
    original = r4._ORIGINAL_FORM_RECORD

    def capture(*, learner_id: str, form_ordinal: int, skill_payloads: Mapping[str, Mapping[str, Any]], blueprint_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        selected = r4.base._selected_by_activity(skill_payloads)
        blueprint = {str(row.get("activity_id") or ""): row for row in blueprint_rows}
        if len(selected) != r4.base.EXPECTED_ACTIVITIES_PER_FORM:
            raise Final240BindingError(f"CAPTURED_FORM_ACTIVITY_COUNT_INVALID:{form_ordinal}:{len(selected)}")
        for aid, item in selected.items():
            bp = blueprint.get(str(aid))
            if bp is None:
                raise Final240BindingError(f"CAPTURED_ACTIVITY_BLUEPRINT_MISSING:{aid}")
            captured.append(
                {
                    "activity_id": str(aid),
                    "form_id": str(bp.get("form_id") or f"U01-FORM-{form_ordinal:02d}"),
                    "form_ordinal": int(form_ordinal),
                    "scene_ref_id": str(bp.get("scene_ref_id") or ""),
                    "skill": str(bp.get("skill") or ""),
                    "task_angle": str(bp.get("task_angle") or ""),
                    "support_level": str(bp.get("support_level") or ""),
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
        with tempfile.TemporaryDirectory(prefix="a1fs_u01sa06a_") as tmp:
            replay = r4.materialize_full_replay(
                database=Path(database),
                output=Path(tmp) / "r4.json",
                learner_id=REPLAY_LEARNER_ID,
            )
    finally:
        r4._ORIGINAL_FORM_RECORD = original

    expected = (
        replay.get("validation_status") == r4.PASS_STATUS
        and int(replay.get("form_count", -1)) == EXPECTED_FORMS
        and int(replay.get("scene_exposure_count", -1)) == EXPECTED_SCENE_EXPOSURES
        and int(replay.get("learner_visible_activity_count", -1)) == EXPECTED_ACTIVITY_BINDINGS
        and len(captured) == EXPECTED_ACTIVITY_BINDINGS
    )
    if not expected:
        raise Final240BindingError("FINAL_R4_CAPTURE_DENOMINATOR_INVALID")
    aids = [row["activity_id"] for row in captured]
    if len(aids) != len(set(aids)):
        raise Final240BindingError("CAPTURED_ACTIVITY_DUPLICATE")
    return replay, sorted(captured, key=lambda row: row["activity_id"])


def _target_noun(private: Mapping[str, Any]) -> str:
    slots = private.get("lexical_slots") or {}
    if isinstance(slots, Mapping):
        for key in ("noun", "target_noun", "item", "target"):
            value = str(slots.get(key) or "").strip().casefold()
            if value:
                return value
    return ""


def _determiner(private: Mapping[str, Any], family: str) -> str:
    if family in FIRST_FAMILIES:
        answer = str(private.get("correct_answer") or "").strip().casefold()
        return answer if answer in {"a", "an"} else ""
    if family in KNOWN_FAMILIES or family in REFERENCE_FAMILIES:
        return "the"
    return ""


def _task_rank(family: str, angle: str) -> int | None:
    if family == "U01-PF04-FIRST-MENTION-CONTEXT":
        return {"FIRST_MENTION": 0, "FIRST_MENTION_TRANSFER": 1}.get(angle)
    if family == "U01-PF08-TRANSFER-FIRST-MENTION":
        return {"FIRST_MENTION_TRANSFER": 0, "FIRST_MENTION": 1}.get(angle)
    if family == "U01-PF05-KNOWN-REFERENCE-CONTEXT":
        return {"KNOWN_REFERENCE": 0, "KNOWN_REFERENCE_TRANSFER": 1}.get(angle)
    if family == "U01-PF16-READING-REFERENCE-EVIDENCE":
        return {"REFERENCE_EVIDENCE": 0, "KNOWN_REFERENCE": 1, "KNOWN_REFERENCE_TRANSFER": 2}.get(angle)
    return None


def _profile_matches(profile: Mapping[str, Any], noun: str, entity: str = "") -> bool:
    noun = noun.casefold()
    entity = entity.upper()
    for slot in profile.get("np_slots") or []:
        if not isinstance(slot, Mapping):
            continue
        if entity and str(slot.get("entity_id") or "").upper() == entity:
            return True
        if noun and str(slot.get("canonical_surface") or "").casefold() == noun:
            return True
    return False


def _validate_refs(item_id: str, refs: Sequence[str], pool: Mapping[str, Mapping[str, Any]], noun: str, entity: str = "") -> None:
    if not refs:
        raise Final240BindingError(f"SENTENCE_EVIDENCE_EMPTY:{item_id}")
    for sid in refs:
        profile = pool.get(str(sid))
        if profile is None:
            raise Final240BindingError(f"SENTENCE_REF_NOT_IN_3805_POOL:{item_id}:{sid}")
        if not _profile_matches(profile, noun, entity):
            raise Final240BindingError(f"SENTENCE_TARGET_REFERENT_MISMATCH:{item_id}:{sid}:{noun}:{entity}")


def _bridge_binding(*, item_id: str, family: str, private: Mapping[str, Any], sa05r2_rows: Sequence[Mapping[str, Any]], pool: Mapping[str, Mapping[str, Any]] | None = None) -> Mapping[str, Any]:
    """Choose already-approved evidence using referent/discourse + sentence scene affinity."""
    noun = _target_noun(private)
    determiner = _determiner(private, family)
    context = str(private.get("context_id") or "")
    if not noun or not determiner:
        raise Final240BindingError(f"POST_SA05R2_BRIDGE_DEMAND_UNSUPPORTED:{item_id}:{family}")
    pool = dict(pool or {})
    candidates: list[tuple[tuple[Any, ...], Mapping[str, Any]]] = []
    for row in sa05r2_rows:
        rank = _task_rank(family, str(row.get("task_angle") or ""))
        if rank is None:
            continue
        target = row.get("target_np") or {}
        compat = row.get("compatibility") or {}
        if not isinstance(target, Mapping) or not isinstance(compat, Mapping):
            continue
        if str(target.get("canonical_surface") or "").casefold() != noun:
            continue
        if str(target.get("determiner") or "").casefold() != determiner:
            continue
        if str(target.get("structure") or "NOUN").upper() != "NOUN" or compat.get("candidate_compatible") is not True:
            continue
        primary = str(row.get("primary_sentence_ref") or "")
        antecedent = str(row.get("antecedent_sentence_ref") or "")
        if not primary or ((family in KNOWN_FAMILIES or family in REFERENCE_FAMILIES) and not antecedent):
            continue
        refs = [primary] + ([antecedent] if antecedent else []) + [str(v) for v in row.get("support_sentence_refs") or [] if str(v)]
        if pool and any(ref not in pool for ref in refs):
            continue
        exact_source_scene = sum(
            bool(context) and str((pool.get(ref) or {}).get("source_scene_ref") or "") == context
            for ref in refs
        )
        generic_source = sum(
            "GENERIC_SCENE_NEUTRAL" in ((pool.get(ref) or {}).get("scene_capability") or [])
            for ref in refs
        )
        legacy_id = str(row.get("item_id") or "")
        score = (
            0 if str(compat.get("scene_ref") or "") == context else 1,
            0 if context and context in legacy_id else 1,
            -exact_source_scene,
            -generic_source,
            rank,
            legacy_id,
        )
        candidates.append((score, row))
    if not candidates:
        raise Final240BindingError(f"POST_SA05R2_BRIDGE_EVIDENCE_MISSING:{item_id}")
    candidates.sort(key=lambda pair: pair[0])
    best = candidates[0][0][:-1]
    tied = [row for score, row in candidates if score[:-1] == best]
    evidence = {
        (
            str(row.get("primary_sentence_ref") or ""),
            str(row.get("antecedent_sentence_ref") or ""),
            tuple(str(v) for v in row.get("support_sentence_refs") or []),
        )
        for row in tied
    }
    if len(evidence) != 1:
        raise Final240BindingError(f"POST_SA05R2_BRIDGE_AMBIGUOUS:{item_id}:{len(tied)}:{len(evidence)}")
    return candidates[0][1]


def _resolve_sentence_binding(*, item_id: str, catalog_row: Mapping[str, Any], sa05r2_by_id: Mapping[str, Mapping[str, Any]], pool: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    private = catalog_row.get("private_item") or {}
    family = str(catalog_row.get("pattern_family_id") or "")
    noun = _target_noun(private)
    if item_id in sa05r2_by_id:
        row = sa05r2_by_id[item_id]
        target = row.get("target_np") or {}
        entity = str(target.get("entity_id") or "") if isinstance(target, Mapping) else ""
        noun = noun or (str(target.get("canonical_surface") or "").casefold() if isinstance(target, Mapping) else "")
        primary = str(row.get("primary_sentence_ref") or "")
        antecedent = str(row.get("antecedent_sentence_ref") or "") or None
        support = [str(v) for v in row.get("support_sentence_refs") or [] if str(v)]
        _validate_refs(item_id, [primary] + ([antecedent] if antecedent else []) + support, pool, noun, entity)
        return {"binding_source": "SA05R2_EXACT_ITEM_ID", "primary_sentence_ref": primary, "antecedent_sentence_ref": antecedent, "support_sentence_refs": support, "legacy_evidence_item_id": item_id}

    sources = [str(v) for v in private.get("source_sentence_ids") or [] if str(v)]
    if sources and private.get("sentence_pool_source_task_id") == SA05R2_TASK_ID:
        entity = str(private.get("sentence_pool_target_entity_id") or "")
        _validate_refs(item_id, sources, pool, noun, entity)
        antecedent = None
        if family == "U01-PF09-TRANSFER-KNOWN-REFERENCE":
            antecedent = str(private.get("contextual_reference_source_sentence_id") or "") or sources[0]
            if antecedent not in sources:
                raise Final240BindingError(f"R2R2_CONTEXTUAL_REFERENCE_ANTECEDENT_NOT_SOURCE_BOUND:{item_id}")
        return {"binding_source": "R2R2_INLINE_SENTENCE_LINEAGE", "primary_sentence_ref": sources[0], "antecedent_sentence_ref": antecedent, "support_sentence_refs": sources[1:], "legacy_evidence_item_id": None}

    bridge = _bridge_binding(item_id=item_id, family=family, private=private, sa05r2_rows=list(sa05r2_by_id.values()), pool=pool)
    target = bridge.get("target_np") or {}
    entity = str(target.get("entity_id") or "") if isinstance(target, Mapping) else ""
    primary = str(bridge.get("primary_sentence_ref") or "")
    antecedent = str(bridge.get("antecedent_sentence_ref") or "") or None
    support = [str(v) for v in bridge.get("support_sentence_refs") or [] if str(v)]
    _validate_refs(item_id, [primary] + ([antecedent] if antecedent else []) + support, pool, noun, entity)
    return {"binding_source": "POST_SA05R2_IDENTITY_BRIDGE", "primary_sentence_ref": primary, "antecedent_sentence_ref": antecedent, "support_sentence_refs": support, "legacy_evidence_item_id": str(bridge.get("item_id") or "")}


def materialize_final_binding(*, database: Path, sentence_pool_capability_index: Path, sa05r2_final474_rebind: Path, output: Path) -> dict[str, Any]:
    database = Path(database).resolve(strict=True)
    output = Path(output).resolve()
    if output == database:
        raise Final240BindingError("OUTPUT_MUST_NOT_OVERWRITE_DATABASE")
    before = _sha256(database)
    pool_path = Path(sentence_pool_capability_index).resolve(strict=True)
    rebind_path = Path(sa05r2_final474_rebind).resolve(strict=True)
    pool = _pool_index(_load(pool_path))
    sa05r2 = _sa05r2_bindings(_load(rebind_path))
    catalog = _catalog(database)
    replay, selected = _capture_exact_activity_bindings(database)

    bindings: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    unresolved: list[dict[str, Any]] = []
    for row in selected:
        iid = str(row["item_id"])
        current = catalog.get(iid)
        if current is None:
            unresolved.append({"activity_id": row["activity_id"], "item_id": iid, "reason": "ITEM_NOT_IN_FINAL474"})
            continue
        try:
            sentence = _resolve_sentence_binding(item_id=iid, catalog_row=current, sa05r2_by_id=sa05r2, pool=pool)
        except Final240BindingError as exc:
            unresolved.append({"activity_id": row["activity_id"], "item_id": iid, "reason": str(exc)})
            continue
        source = str(sentence["binding_source"])
        source_counts[source] = source_counts.get(source, 0) + 1
        bindings.append({**row, "pattern_family_id": str(current.get("pattern_family_id") or ""), **sentence})

    if unresolved:
        first = unresolved[0]
        raise Final240BindingError(f"FINAL240_UNRESOLVED:{len(unresolved)}:{first['activity_id']}:{first['item_id']}:{first['reason']}")
    if len(bindings) != EXPECTED_ACTIVITY_BINDINGS or any(not row.get("primary_sentence_ref") for row in bindings):
        raise Final240BindingError(f"FINAL240_BINDING_COUNT_OR_PRIMARY_REF_INVALID:{len(bindings)}")
    if _sha256(database) != before:
        raise Final240BindingError("SOURCE_DATABASE_MODIFIED")

    result = {
        "schema_version": "a1fs.v1.u01sa06a.final240_activity_qb_sentence_binding.v1",
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "form_count": int(replay["form_count"]),
        "scene_exposure_count": int(replay["scene_exposure_count"]),
        "activity_binding_count": len(bindings),
        "selected_item_occurrence_count": len(bindings),
        "selected_item_distinct_count": len({row["item_id"] for row in bindings}),
        "runtime_item_count": len(catalog),
        "sentence_pool_total": len(pool),
        "binding_source_occurrence_counts": dict(sorted(source_counts.items())),
        "unresolved_count": 0,
        "unresolved": [],
        "activity_bindings": bindings,
        "source_bindings": {
            "database_sha256": before,
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
    _write(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", type=Path, required=True)
    p.add_argument("--sentence-pool-capability-index", type=Path, required=True)
    p.add_argument("--sa05r2-final474-rebind", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
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
