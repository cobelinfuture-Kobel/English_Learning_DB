#!/usr/bin/env python3
"""Measure targeted RAZ G-I gap yield after the completed A-F semantic audit.

The builder recomputes A-F and G-I observations against the same committed
Authority snapshot, reports only aggregate/hash metadata, and does not read J-W.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-GI_TargetedGapSourceExpansion"
SCHEMA_VERSION = "raz.gi.targeted_gap_source_expansion.v1"
PASS_STATUS = "PASS_RAZ_GI_TARGETED_GAP_SOURCE_EXPANSION"
AF_LEVELS = ("A", "B", "C", "D", "E", "F")
GI_LEVELS = ("G", "H", "I")
EXPECTED_AF_RECORDS = 4925
EXPECTED_AF_BOOKS = 566
EXPECTED_GI_RECORDS = 3032
EXPECTED_GI_BOOKS = 264
TARGET_UNIT_IDS = (
    "GRAMMAR_CAN_NEGATIVE_A1",
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1",
)
DEFAULT_AF_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_GI_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_MANIFEST = REPO_ROOT / ".local/raz_af/a1_a1plus_reading_source_manifest.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_gi/targeted_gap_expansion/targeted_gap_expansion.safe.json"

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_G_I_TARGETED_AFTER_AF",
    "a_f_recomputed_for_delta": True,
    "g_i_read_performed": True,
    "j_w_read_performed": False,
    "source_text_included_in_safe_output": False,
    "source_payload_included_in_safe_output": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learner_facing_material_created": False,
    "core_sentence_candidate_created": False,
    "core_sentence_seed_count_only": True,
    "learning_unit_content_population_performed": False,
    "a2_a2plus_in_scope": False,
}

THRESHOLDS = {
    "combined_vocabulary_coverage_rate": 0.85,
    "combined_chunk_coverage_rate": 0.75,
    "combined_pattern_coverage_rate": 0.80,
    "target_unit_record_count": 50,
    "target_unit_strict_core_seed_count": 8,
    "target_unit_passage_seed_count": 2,
}


class TargetedGapError(ValueError):
    """Fail-closed targeted G-I expansion error."""


def discover_level_file(root: Path, level: str) -> Path:
    candidates = [
        root / f"raz_{level}_page_unit_enriched.json",
        root / "derived" / f"Level_{level}" / "enriched"
        / f"raz_{level}_page_unit_enriched.json",
        root / f"Level_{level}" / "enriched"
        / f"raz_{level}_page_unit_enriched.json",
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        found = list(root.rglob(f"raz_{level}_page_unit_enriched.json"))
        if len(found) == 1:
            path = found[0]
    if path is None:
        raise TargetedGapError(f"missing_page_unit_file:{level}")
    return path


def load_levels(
    root: Path,
    levels: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    index = []
    seen: set[str] = set()
    for level in levels:
        path = discover_level_file(root, level)
        payload = deep.read_json(path)
        if not isinstance(payload, list):
            raise TargetedGapError(f"page_unit_not_list:{level}")
        books = set()
        for row in payload:
            if not isinstance(row, dict):
                raise TargetedGapError(f"invalid_page_unit:{level}")
            ref = row.get("page_unit_id")
            if not isinstance(ref, str) or not ref or ref in seen:
                raise TargetedGapError(f"invalid_or_duplicate_page_unit_id:{ref}")
            if row.get("level") != level:
                raise TargetedGapError(f"level_mismatch:{ref}")
            if not isinstance(row.get("text"), str) or not row["text"].strip():
                raise TargetedGapError(f"source_text_missing:{ref}")
            seen.add(ref)
            records.append(row)
            books.add(str(row.get("book_id")))
        index.append({
            "level": level,
            "path": path.name,
            "page_unit_count": len(payload),
            "book_count": len(books),
            "sha256": deep.sha256_file(path),
        })
    return records, index


def observe(
    records: Sequence[Mapping[str, Any]],
    authorities: Mapping[str, Any],
    manifest_tags: Mapping[str, set[str]],
) -> dict[str, Any]:
    asset_refs = {name: set() for name in ("vocabulary", "chunks", "patterns")}
    unit_refs = {unit_id: set() for unit_id in TARGET_UNIT_IDS}
    strict_refs = {unit_id: set() for unit_id in TARGET_UNIT_IDS}
    passage_refs = {unit_id: set() for unit_id in TARGET_UNIT_IDS}
    books = set()
    levels = Counter()
    semantic_complete = 0

    for row in records:
        ref = str(row["page_unit_id"])
        level = str(row["level"])
        book_id = str(row["book_id"])
        books.add((level, book_id))
        levels[level] += 1
        text = str(row["text"])
        vocabulary = deep.match_vocabulary(text, authorities["vocabulary"])
        chunks = deep.match_template_authority(text, authorities["chunks"])
        patterns = deep.match_template_authority(text, authorities["patterns"])
        units = deep.grammar_units(text, manifest_tags.get(ref, set()))
        semantic = deep.semantic_alignment(row)
        complete = all(semantic[name] for name in (
            "situation_families",
            "micro_situations",
            "communicative_functions",
            "participant_roles",
            "interaction_goals",
        ))
        semantic_complete += int(complete)
        known_semantic = (
            "general_child_friendly_context"
            not in semantic["situation_families"]
        )
        strict = bool(units and vocabulary and (chunks or patterns) and known_semantic)
        passage = int(row.get("sentence_count") or 0) >= 2

        asset_refs["vocabulary"].update(vocabulary)
        asset_refs["chunks"].update(chunks)
        asset_refs["patterns"].update(patterns)
        for unit_id in set(TARGET_UNIT_IDS) & units:
            unit_refs[unit_id].add(ref)
            if strict:
                strict_refs[unit_id].add(ref)
            if passage:
                passage_refs[unit_id].add(ref)

    return {
        "assets": asset_refs,
        "unit_refs": unit_refs,
        "strict_refs": strict_refs,
        "passage_refs": passage_refs,
        "record_count": len(records),
        "book_count": len(books),
        "level_counts": dict(levels),
        "semantic_complete_record_count": semantic_complete,
    }


def build_report(
    af_records: Sequence[Mapping[str, Any]],
    af_file_index: Sequence[Mapping[str, Any]],
    gi_records: Sequence[Mapping[str, Any]],
    gi_file_index: Sequence[Mapping[str, Any]],
    authorities: Mapping[str, Any],
    manifest_tags: Mapping[str, set[str]],
    *,
    expected_af_records: int = EXPECTED_AF_RECORDS,
    expected_af_books: int = EXPECTED_AF_BOOKS,
    expected_gi_records: int = EXPECTED_GI_RECORDS,
    expected_gi_books: int = EXPECTED_GI_BOOKS,
) -> dict[str, Any]:
    af = observe(af_records, authorities, manifest_tags)
    gi = observe(gi_records, authorities, manifest_tags)

    source_checks = {
        "af_record_count_exact": af["record_count"] == expected_af_records,
        "af_book_count_exact": af["book_count"] == expected_af_books,
        "gi_record_count_exact": gi["record_count"] == expected_gi_records,
        "gi_book_count_exact": gi["book_count"] == expected_gi_books,
        "af_levels_exact": set(af["level_counts"]) == set(AF_LEVELS),
        "gi_levels_exact": set(gi["level_counts"]) == set(GI_LEVELS),
        "gi_semantic_complete": gi["semantic_complete_record_count"]
        == gi["record_count"],
    }

    coverage = {}
    for name, threshold_key in (
        ("vocabulary", "combined_vocabulary_coverage_rate"),
        ("chunks", "combined_chunk_coverage_rate"),
        ("patterns", "combined_pattern_coverage_rate"),
    ):
        denominator = authorities[name]["ids"]
        af_refs = af["assets"][name] & denominator
        gi_refs = gi["assets"][name] & denominator
        combined = af_refs | gi_refs
        rate = round(len(combined) / len(denominator), 6) if denominator else 0.0
        coverage[name] = {
            "authority_count": len(denominator),
            "af_observed_count": len(af_refs),
            "gi_observed_count": len(gi_refs),
            "gi_new_authority_count": len(gi_refs - af_refs),
            "combined_observed_count": len(combined),
            "combined_coverage_rate": rate,
            "threshold": THRESHOLDS[threshold_key],
            "pass": rate >= THRESHOLDS[threshold_key],
        }

    target_units = []
    for unit_id in TARGET_UNIT_IDS:
        af_record_refs = af["unit_refs"][unit_id]
        gi_record_refs = gi["unit_refs"][unit_id]
        af_strict_refs = af["strict_refs"][unit_id]
        gi_strict_refs = gi["strict_refs"][unit_id]
        combined_records = af_record_refs | gi_record_refs
        combined_strict = af_strict_refs | gi_strict_refs
        combined_passage = (
            af["passage_refs"][unit_id] | gi["passage_refs"][unit_id]
        )
        checks = {
            "record_density": len(combined_records)
            >= THRESHOLDS["target_unit_record_count"],
            "strict_core_seed_density": len(combined_strict)
            >= THRESHOLDS["target_unit_strict_core_seed_count"],
            "passage_seed_density": len(combined_passage)
            >= THRESHOLDS["target_unit_passage_seed_count"],
        }
        target_units.append({
            "grammar_unit_id": unit_id,
            "af_record_count": len(af_record_refs),
            "gi_record_count": len(gi_record_refs),
            "gi_new_record_count": len(gi_record_refs - af_record_refs),
            "combined_record_count": len(combined_records),
            "af_strict_core_seed_count": len(af_strict_refs),
            "gi_strict_core_seed_count": len(gi_strict_refs),
            "combined_strict_core_seed_count": len(combined_strict),
            "combined_passage_seed_count": len(combined_passage),
            "checks": checks,
            "sufficient": all(checks.values()),
        })

    checks = {
        "source_integrity": all(source_checks.values()),
        "vocabulary_coverage": coverage["vocabulary"]["pass"],
        "chunk_coverage": coverage["chunks"]["pass"],
        "pattern_coverage": coverage["patterns"]["pass"],
        "all_target_units_sufficient": all(
            row["sufficient"] for row in target_units
        ),
    }
    if not checks["source_integrity"]:
        decision = "BLOCKED_SOURCE_INTEGRITY"
    elif all(checks.values()):
        decision = "AI_SUFFICIENT_FOR_CONTENT_POPULATION"
    else:
        decision = "TARGETED_JW_EXPANSION_REQUIRED"

    report: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "source_scope": {
            "af_levels": list(AF_LEVELS),
            "gi_levels": list(GI_LEVELS),
            "af_record_count": af["record_count"],
            "af_book_count": af["book_count"],
            "gi_record_count": gi["record_count"],
            "gi_book_count": gi["book_count"],
            "af_source_files": list(af_file_index),
            "gi_source_files": list(gi_file_index),
            "j_w_read_performed": False,
        },
        "authority_baselines": {
            name: {
                "count": value["count"],
                "source_path": value["source_path"],
                "source_sha256": value["source_sha256"],
            }
            for name, value in authorities.items()
        },
        "targeted_gap_yield": {
            "authority_coverage": coverage,
            "target_learning_units": target_units,
            "gi_semantic_complete_record_count": gi[
                "semantic_complete_record_count"
            ],
            "gi_semantic_completion_rate": round(
                gi["semantic_complete_record_count"] / gi["record_count"], 6
            ) if gi["record_count"] else 0.0,
        },
        "sufficiency_gate": {
            "source_checks": source_checks,
            "checks": checks,
            "decision": decision,
            "a_i_sufficient_for_content_population": (
                decision == "AI_SUFFICIENT_FOR_CONTENT_POPULATION"
            ),
            "targeted_j_w_expansion_allowed": (
                decision == "TARGETED_JW_EXPANSION_REQUIRED"
            ),
            "remaining_asset_gap_counts": {
                name: value["authority_count"] - value["combined_observed_count"]
                for name, value in coverage.items()
            },
            "remaining_weak_units": [
                row["grammar_unit_id"]
                for row in target_units
                if not row["sufficient"]
            ],
            "next_short_step": (
                "RAZ-AI_ContentPopulationBinding"
                if decision == "AI_SUFFICIENT_FOR_CONTENT_POPULATION"
                else "RAZ-JW_TargetedGapSourceExtraction"
                if decision == "TARGETED_JW_EXPANSION_REQUIRED"
                else TASK_ID
            ),
        },
        "thresholds": dict(THRESHOLDS),
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    report["report_sha256"] = deep.sha256_value(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--af-root", type=Path, default=DEFAULT_AF_ROOT)
    parser.add_argument("--gi-root", type=Path, default=DEFAULT_GI_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        af_records, af_index = load_levels(args.af_root, AF_LEVELS)
        gi_records, gi_index = load_levels(args.gi_root, GI_LEVELS)
        report = build_report(
            af_records,
            af_index,
            gi_records,
            gi_index,
            deep.load_authorities(),
            deep.load_manifest_grammar_tags(args.manifest),
        )
        leakage = deep.scan_forbidden_safe_keys(report)
        if leakage:
            raise TargetedGapError(
                "safe_output_leakage:" + ";".join(leakage[:10])
            )
        deep.write_json_atomic(args.output, report)
        print(json.dumps({
            "task_id": TASK_ID,
            "decision": report["sufficiency_gate"]["decision"],
            "remaining_asset_gap_counts": report["sufficiency_gate"][
                "remaining_asset_gap_counts"
            ],
            "remaining_weak_units": report["sufficiency_gate"][
                "remaining_weak_units"
            ],
            "report_sha256": report["report_sha256"],
        }, sort_keys=True))
        return 0
    except (
        TargetedGapError,
        deep.AlignmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
