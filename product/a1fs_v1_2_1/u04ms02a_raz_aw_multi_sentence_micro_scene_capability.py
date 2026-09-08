from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

TASK_ID = "A1FS-V1-U04MS02A_RAZAWMultiSentenceMicroSceneCapabilityMaterialization"
STATUS = "PASS_A1FS_V1_U04MS02A_RAZ_AW_MULTI_SENTENCE_MICRO_SCENE_CAPABILITY_MATERIALIZATION"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Deterministic capability projection that composes already-admitted Unit04 Q07 "
    "scene-bound sentence assets using text-free RAZ-AW structural evidence; it does "
    "not author new sentence text or promote RAZ candidate content."
)

Q07 = "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
RAZ_SNAPSHOT = "ulga/contracts/a1fs_v1_u04_ms02a_raz_aw_structural_evidence_snapshot.json"
CAPABILITY_COUNT = 36
SENTENCE_COUNT_PATTERN = (2, 3, 4, 5)


class MaterializationError(ValueError):
    pass


def _repo_root(repo_root: Path | str | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MaterializationError(f"required_source_missing:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MaterializationError(f"required_source_not_object:{path}")
    return value


def _sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_raz_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    if snapshot.get("task_id") != TASK_ID:
        raise MaterializationError("raz_snapshot_task_id_mismatch")
    if snapshot.get("source_id") != "RAZ_AW":
        raise MaterializationError("raz_snapshot_source_id_mismatch")
    if snapshot.get("authority_role") != "NON_AUTHORITATIVE_READING_CONTEXT_EXPOSURE_EVIDENCE":
        raise MaterializationError("raz_snapshot_authority_role_mismatch")
    if snapshot.get("canonical_promotion_allowed") is not False:
        raise MaterializationError("raz_snapshot_canonical_promotion_must_be_false")
    if snapshot.get("learner_facing_authority") is not False:
        raise MaterializationError("raz_snapshot_learner_facing_authority_must_be_false")
    policy = snapshot.get("snapshot_policy")
    if not isinstance(policy, dict):
        raise MaterializationError("raz_snapshot_policy_missing")
    required_false = (
        "raw_raz_text_included",
        "clean_text_included",
        "source_titles_included",
        "candidate_rows_promoted",
    )
    if any(policy.get(key) is not False for key in required_false):
        raise MaterializationError("raz_snapshot_private_or_promotion_boundary_broken")
    if policy.get("structural_evidence_only") is not True:
        raise MaterializationError("raz_snapshot_not_structural_only")
    rows = snapshot.get("records")
    if not isinstance(rows, list) or not rows:
        raise MaterializationError("raz_snapshot_records_missing")
    forbidden_keys = {"clean_text", "text", "title", "book_title", "source_text"}
    for row in rows:
        if not isinstance(row, dict):
            raise MaterializationError("raz_snapshot_row_not_object")
        if forbidden_keys.intersection(row):
            raise MaterializationError("raz_snapshot_contains_forbidden_text_field")
        if row.get("has_multi_sentence_unit") is not True:
            raise MaterializationError("raz_snapshot_row_not_multi_sentence")
        if int(row.get("sentence_count") or 0) < 2:
            raise MaterializationError("raz_snapshot_sentence_count_below_two")
        if row.get("authority_status") != "candidate_only":
            raise MaterializationError("raz_snapshot_authority_status_drift")
        if row.get("promotion_status") != "not_promoted":
            raise MaterializationError("raz_snapshot_promotion_status_drift")
    return rows


def _validate_q07(q07: dict[str, Any]) -> list[dict[str, Any]]:
    expected = "PASS_Q07_UNIT04_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"
    if q07.get("status") != expected:
        raise MaterializationError(f"unit04_q07_not_pass:{q07.get('status')}")
    if q07.get("unit_number") != 4 or q07.get("unit_id") != "GRAMMAR_BASIC_PREPOSITIONS_PLACE":
        raise MaterializationError("unit04_q07_identity_mismatch")
    policy = q07.get("materialization_policy")
    if not isinstance(policy, dict) or policy.get("a2_unlocked") is not False:
        raise MaterializationError("unit04_q07_a2_boundary_invalid")
    scenes = q07.get("micro_scenes")
    if not isinstance(scenes, list) or len(scenes) < CAPABILITY_COUNT:
        raise MaterializationError("unit04_q07_scene_supply_insufficient")
    seen_scene_refs: set[str] = set()
    seen_sentence_ids: set[str] = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            raise MaterializationError("unit04_q07_scene_not_object")
        scene_ref = str(scene.get("scene_ref_id") or "")
        sentence_id = str(scene.get("bound_sentence_id") or "")
        sentence_text = str(scene.get("bound_sentence_text") or "")
        if not scene_ref or not sentence_id or not sentence_text:
            raise MaterializationError("unit04_q07_scene_binding_incomplete")
        if scene_ref in seen_scene_refs:
            raise MaterializationError("unit04_q07_scene_ref_duplicate")
        if sentence_id in seen_sentence_ids:
            raise MaterializationError("unit04_q07_sentence_id_duplicate")
        if scene.get("a2_unlocked") is not False:
            raise MaterializationError("unit04_q07_scene_a2_unlocked")
        seen_scene_refs.add(scene_ref)
        seen_sentence_ids.add(sentence_id)
    return scenes


def _group_scenes(scenes: Iterable[dict[str, Any]]) -> tuple[
    dict[tuple[str, str], list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    exact: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scene in scenes:
        scene_family = str(scene.get("scene_family") or "")
        medium_setting = str(scene.get("medium_setting") or "")
        if not scene_family:
            raise MaterializationError("unit04_q07_scene_family_missing")
        exact[(scene_family, medium_setting)].append(scene)
        family[scene_family].append(scene)
    key = lambda row: (
        str(row.get("relation_surface") or ""),
        str(row.get("small_micro_scene_event") or ""),
        str(row.get("scene_ref_id") or ""),
    )
    for rows in exact.values():
        rows.sort(key=key)
    for rows in family.values():
        rows.sort(key=key)
    return dict(exact), dict(family)


def _pick_group(
    size: int,
    capability_index: int,
    exact: dict[tuple[str, str], list[dict[str, Any]]],
    family: dict[str, list[dict[str, Any]]],
) -> tuple[str, str, list[dict[str, Any]], str]:
    exact_keys = sorted(key for key, rows in exact.items() if len(rows) >= size)
    if exact_keys:
        key = exact_keys[capability_index % len(exact_keys)]
        scene_family, medium_setting = key
        return scene_family, medium_setting, exact[key], "SCENE_FAMILY_AND_MEDIUM_SETTING"
    family_keys = sorted(key for key, rows in family.items() if len(rows) >= size)
    if not family_keys:
        raise MaterializationError(f"no_coherent_scene_group_for_sentence_count:{size}")
    scene_family = family_keys[capability_index % len(family_keys)]
    return scene_family, "", family[scene_family], "SCENE_FAMILY"


def _window(rows: list[dict[str, Any]], size: int, start: int) -> list[dict[str, Any]]:
    if len(rows) < size:
        raise MaterializationError("window_group_smaller_than_requested_size")
    start = start % len(rows)
    if start + size <= len(rows):
        selected = rows[start : start + size]
    else:
        selected = rows[start:] + rows[: (start + size) % len(rows)]
    if len({row["scene_ref_id"] for row in selected}) != size:
        raise MaterializationError("window_scene_ref_not_distinct")
    return selected


def _capability_row(
    capability_index: int,
    selected: list[dict[str, Any]],
    sentence_count: int,
    scene_family: str,
    medium_setting: str,
    coherence_basis: str,
    raz_row: dict[str, Any],
) -> dict[str, Any]:
    identity = "|".join(str(row["scene_ref_id"]) for row in selected)
    digest = hashlib.sha256(
        f"{capability_index:03d}\0{identity}\0{raz_row['reuse_unit_id']}".encode("utf-8")
    ).hexdigest()[:20].upper()
    relations = [str(row.get("relation_surface") or "") for row in selected]
    return {
        "capability_id": f"U04-MS02A-RAZ-MICRO-{digest}",
        "capability_type": "RAZ_STRUCTURAL_PATTERN_PROJECTED_ONTO_UNIT04_Q07_AUTHORITY",
        "sentence_count": sentence_count,
        "scene_family": scene_family,
        "medium_setting": medium_setting or None,
        "coherence_basis": coherence_basis,
        "unit04_scene_ref_ids": [str(row["scene_ref_id"]) for row in selected],
        "unit04_sentence_ids": [str(row["bound_sentence_id"]) for row in selected],
        "unit04_sentence_texts": [str(row["bound_sentence_text"]) for row in selected],
        "relation_surfaces": relations,
        "distinct_relation_count": len(set(relations)),
        "raz_structural_evidence": {
            "reuse_unit_id": raz_row["reuse_unit_id"],
            "source_page_unit_id": raz_row["source_page_unit_id"],
            "level": raz_row["level"],
            "book_id": raz_row["book_id"],
            "page_number": raz_row["page_number"],
            "source_sentence_candidate_ids": list(raz_row["source_sentence_candidate_ids"]),
            "source_sentence_count": raz_row["sentence_count"],
            "authority_status": raz_row["authority_status"],
            "promotion_status": raz_row["promotion_status"],
            "review_status": raz_row["review_status"],
            "evidence_role": "MULTI_SENTENCE_STRUCTURE_REFERENCE_ONLY",
        },
        "authority_boundary": {
            "unit04_language_authority": Q07,
            "raz_is_learner_facing_authority": False,
            "raz_canonical_promotion_allowed": False,
            "raz_raw_text_copied": False,
            "new_sentence_text_authored": False,
            "new_global_scene_identity_created": False,
            "a2_unlocked": False,
        },
    }


def build_unit04_raz_aw_multi_sentence_micro_scene_capability(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    q07 = _load_json(root / Q07)
    snapshot = _load_json(root / RAZ_SNAPSHOT)
    scenes = _validate_q07(q07)
    raz_rows = _validate_raz_snapshot(snapshot)
    exact, family = _group_scenes(scenes)

    capabilities: list[dict[str, Any]] = []
    for index in range(CAPABILITY_COUNT):
        sentence_count = SENTENCE_COUNT_PATTERN[index % len(SENTENCE_COUNT_PATTERN)]
        scene_family, medium_setting, rows, coherence_basis = _pick_group(
            sentence_count, index, exact, family
        )
        start = (index * 7 + sentence_count * 3) % len(rows)
        selected = _window(rows, sentence_count, start)
        raz_row = raz_rows[index % len(raz_rows)]
        capabilities.append(
            _capability_row(
                index,
                selected,
                sentence_count,
                scene_family,
                medium_setting,
                coherence_basis,
                raz_row,
            )
        )

    sentence_counts = Counter(row["sentence_count"] for row in capabilities)
    family_counts = Counter(row["scene_family"] for row in capabilities)
    relation_counts = Counter(
        relation
        for row in capabilities
        for relation in row["relation_surfaces"]
        if relation
    )
    used_sentence_ids = {
        sentence_id
        for row in capabilities
        for sentence_id in row["unit04_sentence_ids"]
    }
    result: dict[str, Any] = {
        "schema_version": "a1fs.v1.u04.ms02a.raz_aw.multi_sentence_micro_scene_capability.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "internal_stage": "A1",
        "source_refs": {
            "unit04_q07": Q07,
            "raz_structural_evidence_snapshot": RAZ_SNAPSHOT,
        },
        "scope": {
            "capability_materialization_only": True,
            "form01_20_modified": False,
            "canonical_grammar_modified": False,
            "canonical_vocabulary_modified": False,
            "canonical_chunk_modified": False,
            "new_sentence_text_authored": False,
            "raz_raw_text_included": False,
            "raz_candidate_promoted": False,
            "unit05_plus_grammar_opened": False,
            "a2_unlocked": False,
        },
        "raz_evidence_readback": {
            "source_id": snapshot["source_id"],
            "authority_role": snapshot["authority_role"],
            "structural_snapshot_record_count": len(raz_rows),
            "all_structural_rows_multi_sentence": all(
                row["has_multi_sentence_unit"] is True for row in raz_rows
            ),
            "all_structural_rows_nonpromoted": all(
                row["promotion_status"] == "not_promoted" for row in raz_rows
            ),
            "external_source_folder_id": snapshot["source_folder_id"],
        },
        "capability_summary": {
            "capability_count": len(capabilities),
            "sentence_count_distribution": {
                str(key): sentence_counts[key] for key in sorted(sentence_counts)
            },
            "scene_family_count": len(family_counts),
            "scene_family_distribution": dict(sorted(family_counts.items())),
            "relation_distribution": dict(sorted(relation_counts.items())),
            "distinct_unit04_sentence_ids_used": len(used_sentence_ids),
            "min_sentences_per_capability": min(sentence_counts),
            "max_sentences_per_capability": max(sentence_counts),
        },
        "capabilities": capabilities,
        "safety": {
            "raz_authority_role_preserved": True,
            "raz_canonical_promotion_allowed": False,
            "raw_raz_text_copied": False,
            "all_language_rows_resolve_to_q07_scene_bound_sentence_authority": True,
            "new_global_scene_identity_count": 0,
            "unit05_plus_grammar_leak_count": 0,
            "a2_plus_unlock_count": 0,
        },
    }
    result["projection_sha256"] = _sha256(result)
    return result


def compact_readback(projection: dict[str, Any]) -> dict[str, Any]:
    summary = projection["capability_summary"]
    return {
        "task_id": projection["task_id"],
        "status": projection["status"],
        "capability_count": summary["capability_count"],
        "sentence_count_distribution": summary["sentence_count_distribution"],
        "scene_family_count": summary["scene_family_count"],
        "distinct_unit04_sentence_ids_used": summary["distinct_unit04_sentence_ids_used"],
        "raz_structural_snapshot_record_count": projection["raz_evidence_readback"][
            "structural_snapshot_record_count"
        ],
        "raz_raw_text_copied": projection["safety"]["raw_raz_text_copied"],
        "a2_plus_unlock_count": projection["safety"]["a2_plus_unlock_count"],
        "projection_sha256": projection["projection_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    projection = build_unit04_raz_aw_multi_sentence_micro_scene_capability()
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(projection, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(compact_readback(projection), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
