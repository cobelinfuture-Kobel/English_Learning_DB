from __future__ import annotations
from collections import defaultdict
from typing import Any, Mapping, Sequence
from ulga.builders import build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as u02qb02
from .constants import *
from .common import *
from .common import _is_noun, _active_level

def _canonical_index(vocabulary: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in vocabulary:
        if row.get("active") is not True:
            continue
        word = normalize_surface(row.get("word") or "")
        if word:
            result[word].append(dict(row))
    return result


def _q2_authority() -> tuple[list[dict[str, Any]], set[str], dict[str, int]]:
    value = u02qb02.load_inventory()
    rows = [dict(row) for row in value.get("inventory", [])]
    if len(rows) != EXPECTED_U02_PLAIN_S_TARGETS:
        raise U02SA01R1BuildError(f"Q2_TARGET_COUNT_DRIFT:{len(rows)}")
    excluded = value.get("excluded_non_plain_s", {})
    excluded_surfaces = {normalize_surface(x) for values in excluded.values() for x in values}
    return rows, excluded_surfaces, {str(k): len(v) for k, v in excluded.items()}


def build_generation_universe(manifest: Mapping[str, Any], vocabulary: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    index = _canonical_index(vocabulary)
    q2_rows, q2_excluded, q2_excluded_family_counts = _q2_authority()
    target_by_surface: dict[str, dict[str, Any]] = {}
    for row in q2_rows:
        key = normalize_surface(row["singular"])
        target_by_surface[key] = {
            "surface": str(row["singular"]), "plural": str(row["plural"]),
            "vocabulary_ids": sorted(str(x) for x in row.get("vocabulary_ids", [])),
            "role": "MORPHOLOGY_TARGET", "yle_bands": [], "review_required": False,
            "canonical_levels": ["A1"], "source_roles": ["U02QB01_MORPHOLOGY_TARGET"],
        }

    mapped_relationships = []
    a2_locked_ids: set[str] = set()
    unmapped_evidence = 0
    a1_by_surface: dict[str, dict[str, Any]] = {}
    for evidence in manifest.get("yle_noun_evidence", []):
        matched_any = False
        for candidate_surface in evidence.get("surface_candidates", []):
            key = normalize_surface(candidate_surface)
            for row in index.get(key, []):
                if not _is_noun(row):
                    continue
                matched_any = True
                level = str(row.get("level") or "").upper()
                vocab_id = str(row["vocab_id"])
                mapped_relationships.append({"source_surface": evidence.get("source_surface"), "canonical_surface": row.get("word"), "vocab_id": vocab_id, "level": level, "bands": list(evidence.get("bands", []))})
                if level == "A2":
                    a2_locked_ids.add(vocab_id)
                    continue
                if level != "A1":
                    continue
                canonical_surface = str(row.get("word") or "").strip()
                ckey = normalize_surface(canonical_surface)
                rec = a1_by_surface.setdefault(ckey, {"surface": canonical_surface, "vocabulary_ids": set(), "yle_bands": set(), "review_required": False, "canonical_levels": {"A1"}})
                rec["vocabulary_ids"].add(vocab_id)
                rec["yle_bands"].update(evidence.get("bands", []))
                rec["review_required"] = rec["review_required"] or bool(row.get("review_required"))
        if not matched_any:
            unmapped_evidence += 1

    expansion_valid = []
    structural_rejects = []
    for key, rec in sorted(a1_by_surface.items()):
        if key in target_by_surface:
            target_by_surface[key]["yle_bands"] = sorted(rec["yle_bands"])
            continue
        if key in q2_excluded:
            structural_rejects.append({"surface": rec["surface"], "structural_reason": "Q2_NON_PLAIN_S_AUTHORITY_EXCLUSION", "vocabulary_ids": sorted(rec["vocabulary_ids"])})
            continue
        plural, reason = plain_s_plural(rec["surface"])
        if plural is None:
            structural_rejects.append({"surface": rec["surface"], "structural_reason": reason, "vocabulary_ids": sorted(rec["vocabulary_ids"])})
            continue
        expansion_valid.append({"surface": rec["surface"], "plural": plural, "vocabulary_ids": sorted(rec["vocabulary_ids"]), "role": "YLE_LEXICAL_EXPANSION", "yle_bands": sorted(rec["yle_bands"]), "review_required": rec["review_required"], "canonical_levels": ["A1"], "source_roles": ["CAMBRIDGE_YLE_CANONICAL_MAPPING"]})

    # Unit01 cumulative lexical reuse can broaden sentence generation even when a noun is not a YLE item.
    u01_by_surface: dict[str, dict[str, Any]] = {}
    for seed in manifest.get("unit01_i_can_see_structural_seeds", []):
        surface = str(seed.get("canonical_surface") or "").strip()
        key = normalize_surface(surface)
        if key in target_by_surface or any(normalize_surface(x["surface"]) == key for x in expansion_valid):
            continue
        matches = [row for row in index.get(key, []) if _is_noun(row) and _active_level(row, "A1")]
        if not matches or key in q2_excluded:
            continue
        plural, reason = plain_s_plural(surface)
        if plural is None:
            continue
        rec = u01_by_surface.setdefault(key, {"surface": surface, "plural": plural, "vocabulary_ids": set(), "review_required": False})
        for row in matches:
            rec["vocabulary_ids"].add(str(row["vocab_id"]))
            rec["review_required"] = rec["review_required"] or bool(row.get("review_required"))
    u01_valid = [{"surface": rec["surface"], "plural": rec["plural"], "vocabulary_ids": sorted(rec["vocabulary_ids"]), "role": "UNIT01_CUMULATIVE_REUSE", "yle_bands": [], "review_required": rec["review_required"], "canonical_levels": ["A1"], "source_roles": ["UNIT01_I_CAN_SEE_STRUCTURAL_REUSE"]} for _, rec in sorted(u01_by_surface.items())]

    all_valid = list(target_by_surface.values()) + expansion_valid + u01_valid
    by_surface = {normalize_surface(row["surface"]): row for row in all_valid}
    if len(by_surface) != len(all_valid):
        raise U02SA01R1BuildError("GENERATION_UNIVERSE_SURFACE_DUPLICATE")
    return {
        "targets": list(target_by_surface.values()), "expansion_valid": expansion_valid, "u01_reuse_valid": u01_valid,
        "all_valid": all_valid, "by_surface": by_surface, "expansion_structural_rejects": structural_rejects,
        "yle_mapping_relationship_count": len(mapped_relationships), "yle_unmapped_evidence_count": unmapped_evidence,
        "yle_a2_locked_mapped_vocab_ids": sorted(a2_locked_ids), "q2_non_plain_s_exclusion_surface_count": len(q2_excluded),
        "q2_non_plain_s_exclusion_family_counts": q2_excluded_family_counts,
    }


