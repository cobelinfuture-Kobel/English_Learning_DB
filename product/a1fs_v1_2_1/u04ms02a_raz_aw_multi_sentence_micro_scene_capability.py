from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

TASK_ID = "A1FS-V1-U04MS02A_RAZAWMultiSentenceMicroSceneCapabilityMaterialization"
STATUS = "PASS_A1FS_V1_U04MS02A_RAZ_AW_MULTI_SENTENCE_MICRO_SCENE_CAPABILITY_MATERIALIZATION"
REVISION = "R1_A_I_REVIEW_BRIDGE_LINKAGE_GATE_HYDRATION"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Deterministic Unit04 capability projection over already-admitted Q07 scene-bound "
    "sentences using a text-free RAZ-AW A-W inventory digest and hydrated A-I "
    "review/bridge/linkage gate digest; no RAZ text or candidate is promoted."
)

Q07 = "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
RAZ_SNAPSHOT = "ulga/contracts/a1fs_v1_u04_ms02a_raz_aw_structural_evidence_snapshot.json"
CAPABILITY_COUNT = 36
SENTENCE_COUNT_PATTERN = (2, 3, 4, 5)
EXPECTED = {
    "aw_total": 41964, "aw_page": 22632, "aw_reuse": 19332, "aw_max": 635,
    "ai_page": 7957, "ai_reuse": 4690, "direct": 4634, "extension": 4746,
    "review": 7957, "bridge": 7957, "linkage": 58590, "manifest": 50,
}
EXPECTED_BUCKETS = {
    "SINGLE_SENTENCE": 3300, "MICRO_CONTEXT": 4325, "SHORT_CONTEXT": 2121,
    "EXTENDED_CONTEXT": 2843, "SHORT_PASSAGE": 3560, "EXTENDED_PASSAGE": 25815,
}


class MaterializationError(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MaterializationError(f"required_source_missing:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MaterializationError(f"required_source_not_object:{path}")
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _count(row: dict[str, Any], key: str, expected: int) -> None:
    if int(row.get(key, -1)) != expected:
        raise MaterializationError(f"count_mismatch:{key}:{row.get(key)}:{expected}")


def _validate_snapshot(s: dict[str, Any]) -> dict[str, Any]:
    if s.get("schema_version") != "a1fs.v1.u04.ms02a.raz_aw.structural_evidence_snapshot.v2":
        raise MaterializationError("snapshot_schema_mismatch")
    if s.get("task_id") != TASK_ID or s.get("source_id") != "RAZ_AW":
        raise MaterializationError("snapshot_identity_mismatch")
    if s.get("authority_role") != "NON_AUTHORITATIVE_READING_CONTEXT_EXPOSURE_EVIDENCE":
        raise MaterializationError("snapshot_authority_role_mismatch")
    if s.get("canonical_promotion_allowed") is not False or s.get("learner_facing_authority") is not False:
        raise MaterializationError("snapshot_authority_boundary_broken")

    p = s.get("snapshot_policy", {})
    false_keys = (
        "raw_raz_text_included", "clean_text_included", "source_titles_included",
        "candidate_rows_promoted", "raz_level_used_as_cefr_equivalence", "a2_a2plus_opened",
        "reuse_unit_treated_as_admission_gated_page_unit",
    )
    if not isinstance(p, dict) or any(p.get(k) is not False for k in false_keys):
        raise MaterializationError("snapshot_policy_boundary_broken")
    if p.get("structural_evidence_only") is not True or p.get("source_sentence_count_not_prelimited") is not True:
        raise MaterializationError("snapshot_policy_incomplete")

    c = s.get("sentence_count_classification", {})
    if c.get("unit04_direct_projection_eligible") != {"min": 2, "max": 5, "label": "UNIT04_DIRECT_PROJECTION_ELIGIBLE"}:
        raise MaterializationError("direct_lane_drift")
    if c.get("unit04_extension_reference") != {"min": 6, "max": None, "label": "UNIT04_EXTENSION_REFERENCE"}:
        raise MaterializationError("extension_lane_drift")

    aw = s.get("a_w_complete_inventory", {})
    _count(aw, "total_unit_count", EXPECTED["aw_total"]); _count(aw, "page_unit_count", EXPECTED["aw_page"])
    _count(aw, "reuse_unit_count", EXPECTED["aw_reuse"]); _count(aw, "max_sentence_count", EXPECTED["aw_max"])
    if aw.get("bucket_counts") != EXPECTED_BUCKETS:
        raise MaterializationError("aw_bucket_counts_mismatch")
    levels = aw.get("per_level")
    if not isinstance(levels, dict) or set(levels) != set("ABCDEFGHIJKLMNOPQRSTUVW"):
        raise MaterializationError("aw_level_inventory_incomplete")
    if sum(int(r["total_unit_count"]) for r in levels.values()) != EXPECTED["aw_total"]:
        raise MaterializationError("aw_level_inventory_not_reconciled")
    for key in ("exact_sentence_count_distribution_sha256", "full_inventory_digest_sha256"):
        if len(str(aw.get(key, ""))) != 64:
            raise MaterializationError(f"aw_digest_missing:{key}")

    gate = s.get("a1_a1plus_observational_gate_scope", {})
    if gate.get("levels") != "A-I" or gate.get("raz_level_is_not_cefr_equivalence") is not True:
        raise MaterializationError("ai_gate_identity_invalid")
    _count(gate, "page_unit_count", EXPECTED["ai_page"]); _count(gate, "reuse_unit_count_structural_reference_only", EXPECTED["ai_reuse"])
    _count(gate, "unit04_direct_projection_eligible_page_count_2_to_5", EXPECTED["direct"])
    _count(gate, "unit04_extension_reference_total_gt_5", EXPECTED["extension"])
    if gate.get("unit04_direct_projection_exact_sentence_count_distribution") != {"2": 2643, "3": 1240, "4": 575, "5": 176}:
        raise MaterializationError("direct_exact_counts_mismatch")
    gl = gate.get("per_level")
    if not isinstance(gl, dict) or set(gl) != set("ABCDEFGHI"):
        raise MaterializationError("ai_gate_levels_incomplete")
    if not all(all(bool(v) for v in r.get("cross_layer_checks", {}).values()) for r in gl.values()):
        raise MaterializationError("ai_cross_layer_check_failed")

    h = s.get("review_bridge_linkage_hydration", {})
    review, bridge, linkage, cross = h.get("review", {}), h.get("reading_authority_bridge", {}), h.get("linkage", {}), h.get("cross_layer_checks", {})
    _count(review, "record_count", EXPECTED["review"]); _count(bridge, "record_count", EXPECTED["bridge"]); _count(linkage, "record_count", EXPECTED["linkage"])
    for row, n in ((review, EXPECTED["review"]), (bridge, EXPECTED["bridge"]), (linkage, EXPECTED["linkage"])):
        if row.get("authority_status_counts") != {"candidate_only": n} or row.get("promotion_status_counts") != {"promotion_blocked": n}:
            raise MaterializationError("hydration_authority_status_drift")
    if linkage.get("generated_content_counts") != {"False": EXPECTED["linkage"]}:
        raise MaterializationError("linkage_generated_content_detected")
    if not isinstance(cross, dict) or not cross or not all(bool(v) for v in cross.values()):
        raise MaterializationError("aggregate_cross_layer_gate_failed")

    m = s.get("source_file_manifest_digest", {})
    _count(m, "file_count", EXPECTED["manifest"]); _count(m, "derived_enriched_units_file_count", 23); _count(m, "a_i_gate_file_count", 27)
    if len(str(m.get("manifest_sha256", ""))) != 64:
        raise MaterializationError("source_manifest_digest_missing")
    serialized = json.dumps(s, ensure_ascii=False, sort_keys=True)
    if any(token in serialized for token in ('"clean_text":', '"source_text":', '"book_title":', '"title":')):
        raise MaterializationError("forbidden_source_text_field_present")
    return s


def _validate_q07(q: dict[str, Any]) -> list[dict[str, Any]]:
    if q.get("status") != "PASS_Q07_UNIT04_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING":
        raise MaterializationError("q07_not_pass")
    if q.get("unit_number") != 4 or q.get("unit_id") != "GRAMMAR_BASIC_PREPOSITIONS_PLACE":
        raise MaterializationError("q07_identity_mismatch")
    if q.get("materialization_policy", {}).get("a2_unlocked") is not False:
        raise MaterializationError("q07_a2_boundary_invalid")
    scenes = q.get("micro_scenes")
    if not isinstance(scenes, list) or len(scenes) < CAPABILITY_COUNT:
        raise MaterializationError("q07_scene_supply_insufficient")
    refs, ids = set(), set()
    for scene in scenes:
        ref, sid, text = str(scene.get("scene_ref_id") or ""), str(scene.get("bound_sentence_id") or ""), str(scene.get("bound_sentence_text") or "")
        if not ref or not sid or not text or ref in refs or sid in ids or scene.get("a2_unlocked") is not False:
            raise MaterializationError("q07_scene_binding_invalid")
        refs.add(ref); ids.add(sid)
    return scenes


def _groups(scenes: Iterable[dict[str, Any]]) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    exact: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list); family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    key = lambda r: (str(r.get("relation_surface") or ""), str(r.get("small_micro_scene_event") or ""), str(r.get("scene_ref_id") or ""))
    for s in scenes:
        fam, setting = str(s.get("scene_family") or ""), str(s.get("medium_setting") or "")
        if not fam: raise MaterializationError("q07_scene_family_missing")
        exact[(fam, setting)].append(s); family[fam].append(s)
    for rows in list(exact.values()) + list(family.values()): rows.sort(key=key)
    return dict(exact), dict(family)


def _select(size: int, index: int, exact: dict[tuple[str, str], list[dict[str, Any]]], family: dict[str, list[dict[str, Any]]]) -> tuple[str, str, list[dict[str, Any]], str]:
    keys = sorted(k for k, rows in exact.items() if len(rows) >= size)
    if keys:
        fam, setting = keys[index % len(keys)]; rows = exact[(fam, setting)]; basis = "SCENE_FAMILY_AND_MEDIUM_SETTING"
    else:
        fkeys = sorted(k for k, rows in family.items() if len(rows) >= size)
        if not fkeys: raise MaterializationError(f"no_coherent_scene_group:{size}")
        fam, setting, rows, basis = fkeys[index % len(fkeys)], "", family[fkeys[index % len(fkeys)]], "SCENE_FAMILY"
    start = (index * 7 + size * 3) % len(rows)
    chosen = (rows[start:] + rows[:start])[:size]
    if len({r["scene_ref_id"] for r in chosen}) != size: raise MaterializationError("selected_scene_not_distinct")
    return fam, setting, chosen, basis


def build_unit04_raz_aw_multi_sentence_micro_scene_capability(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root); snapshot = _validate_snapshot(_load(root / RAZ_SNAPSHOT)); scenes = _validate_q07(_load(root / Q07)); exact, family = _groups(scenes)
    gate_levels = snapshot["a1_a1plus_observational_gate_scope"]["per_level"]
    eligible_levels = sorted(k for k, r in gate_levels.items() if int(r["direct_projection_page_count_2_to_5"]) > 0)
    caps = []
    for i in range(CAPABILITY_COUNT):
        size = SENTENCE_COUNT_PATTERN[i % 4]; fam, setting, chosen, basis = _select(size, i, exact, family); level = eligible_levels[i % len(eligible_levels)]; lg = gate_levels[level]
        identity = "|".join(r["scene_ref_id"] for r in chosen)
        cid = hashlib.sha256(f"{i:03d}\0{identity}\0{level}\0R1".encode()).hexdigest()[:20].upper()
        relations = [str(r.get("relation_surface") or "") for r in chosen]
        caps.append({
            "capability_id": f"U04-MS02A-RAZ-MICRO-{cid}", "capability_type": "RAZ_STRUCTURAL_PATTERN_PROJECTED_ONTO_UNIT04_Q07_AUTHORITY",
            "projection_lane": "UNIT04_DIRECT_PROJECTION_ELIGIBLE", "sentence_count": size, "scene_family": fam, "medium_setting": setting or None, "coherence_basis": basis,
            "unit04_scene_ref_ids": [r["scene_ref_id"] for r in chosen], "unit04_sentence_ids": [r["bound_sentence_id"] for r in chosen],
            "unit04_sentence_texts": [r["bound_sentence_text"] for r in chosen], "relation_surfaces": relations, "distinct_relation_count": len(set(relations)),
            "raz_structural_evidence": {"source_level": level, "source_sentence_count_band": "2-5", "level_direct_projection_page_count": lg["direct_projection_page_count_2_to_5"],
                "review_record_count": lg["review_record_count"], "bridge_record_count": lg["bridge_record_count"], "linkage_record_count": lg["linkage_record_count"],
                "cross_layer_gate_hydrated": all(bool(v) for v in lg["cross_layer_checks"].values()), "authority_status": "candidate_only", "promotion_status": "promotion_blocked",
                "evidence_role": "MULTI_SENTENCE_STRUCTURE_REFERENCE_ONLY"},
            "authority_boundary": {"unit04_language_authority": Q07, "raz_is_learner_facing_authority": False, "raz_canonical_promotion_allowed": False,
                "raz_raw_text_copied": False, "new_sentence_text_authored": False, "new_global_scene_identity_created": False, "a2_unlocked": False},
        })
    counts = Counter(r["sentence_count"] for r in caps); used = {sid for r in caps for sid in r["unit04_sentence_ids"]}; gate = snapshot["a1_a1plus_observational_gate_scope"]; h = snapshot["review_bridge_linkage_hydration"]
    result = {
        "schema_version": "a1fs.v1.u04.ms02a.raz_aw.multi_sentence_micro_scene_capability.v2", "task_id": TASK_ID, "status": STATUS, "revision": REVISION,
        "unit_number": 4, "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE", "internal_stage": "A1_R1", "source_refs": {"unit04_q07": Q07, "raz_structural_evidence_snapshot": RAZ_SNAPSHOT},
        "scope": {"complete_multi_sentence_evidence_inventory": True, "source_sentence_count_prelimited": False, "direct_projection_sentence_count_min": 2, "direct_projection_sentence_count_max": 5,
            "extension_reference_sentence_count_min": 6, "capability_materialization_only": True, "form01_20_modified": False, "canonical_grammar_modified": False,
            "canonical_vocabulary_modified": False, "canonical_chunk_modified": False, "new_sentence_text_authored": False, "raz_raw_text_included": False,
            "raz_candidate_promoted": False, "unit05_plus_grammar_opened": False, "a2_unlocked": False},
        "raz_evidence_readback": {"complete_inventory_unit_count": EXPECTED["aw_total"], "complete_inventory_max_sentence_count": EXPECTED["aw_max"], "a_i_page_unit_count": EXPECTED["ai_page"],
            "unit04_direct_projection_eligible_page_count_2_to_5": EXPECTED["direct"], "unit04_extension_reference_total_gt_5": EXPECTED["extension"],
            "review_record_count": h["review"]["record_count"], "reading_authority_bridge_record_count": h["reading_authority_bridge"]["record_count"],
            "linkage_record_count": h["linkage"]["record_count"], "source_manifest_file_count": snapshot["source_file_manifest_digest"]["file_count"]},
        "capability_summary": {"capability_count": len(caps), "projection_lane": "UNIT04_DIRECT_PROJECTION_ELIGIBLE", "sentence_count_distribution": {str(k): counts[k] for k in sorted(counts)},
            "distinct_unit04_sentence_ids_used": len(used), "min_sentences_per_capability": min(counts), "max_sentences_per_capability": max(counts)},
        "extension_reference_summary": {"projection_lane": "UNIT04_EXTENSION_REFERENCE", "page_unit_reference_count_gt_5": gate["unit04_extension_reference_page_count_gt_5"],
            "reuse_unit_structural_reference_count_gt_5": gate["unit04_extension_reference_reuse_count_gt_5_structural_only"], "total_reference_count_gt_5": gate["unit04_extension_reference_total_gt_5"],
            "max_a_i_page_sentence_count": gate["max_page_sentence_count"], "max_a_i_reuse_sentence_count": gate["max_reuse_sentence_count"], "direct_learner_language_materialized_in_this_revision": False},
        "capabilities": caps,
        "safety": {"raz_authority_role_preserved": True, "raz_canonical_promotion_allowed": False, "raw_raz_text_copied": False, "source_inventory_sentence_cap_applied": False,
            "raz_level_used_as_cefr_equivalence": False, "reuse_unit_promoted_as_admission_gated_page_unit": False, "all_language_rows_resolve_to_q07_scene_bound_sentence_authority": True,
            "new_global_scene_identity_count": 0, "unit05_plus_grammar_leak_count": 0, "a2_plus_unlock_count": 0},
    }
    result["projection_sha256"] = _digest(result); return result


def compact_readback(p: dict[str, Any]) -> dict[str, Any]:
    e, s, x = p["raz_evidence_readback"], p["capability_summary"], p["extension_reference_summary"]
    return {"task_id": p["task_id"], "status": p["status"], "revision": p["revision"], "capability_count": s["capability_count"], "sentence_count_distribution": s["sentence_count_distribution"],
        "complete_inventory_unit_count": e["complete_inventory_unit_count"], "complete_inventory_max_sentence_count": e["complete_inventory_max_sentence_count"],
        "unit04_direct_projection_eligible_page_count_2_to_5": e["unit04_direct_projection_eligible_page_count_2_to_5"], "unit04_extension_reference_total_gt_5": x["total_reference_count_gt_5"],
        "review_record_count": e["review_record_count"], "reading_authority_bridge_record_count": e["reading_authority_bridge_record_count"], "linkage_record_count": e["linkage_record_count"],
        "source_manifest_file_count": e["source_manifest_file_count"], "raz_raw_text_copied": p["safety"]["raw_raz_text_copied"],
        "source_inventory_sentence_cap_applied": p["safety"]["source_inventory_sentence_cap_applied"], "a2_plus_unlock_count": p["safety"]["a2_plus_unlock_count"], "projection_sha256": p["projection_sha256"]}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--repo-root", type=Path, default=None); ap.add_argument("--output", type=Path, default=None); args = ap.parse_args()
    p = build_unit04_raz_aw_multi_sentence_micro_scene_capability(args.repo_root)
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(compact_readback(p), sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
