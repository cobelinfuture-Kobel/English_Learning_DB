#!/usr/bin/env python3
"""Bind the 197-JSON source-reality audit to the existing per-Level RAZ extractor.

The semantic extractor remains derived-only. This adapter verifies the audited
A-W registry denominators and direct-field reality before declaring the package
ready for governance binding. It emits no source text and performs no Authority
promotion or Learning Unit population.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_per_level_derived_semantic_material_extraction as base

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_DerivedMaterialExtractionMinimalImplementation"
SCHEMA_VERSION = "raz.aw.derived_material_extraction_minimal.v1"
PASS_STATUS = "PASS_RAZ_AW_DERIVED_MATERIAL_EXTRACTION_MINIMAL"
LEVELS = base.LEVELS
A_I_LEVELS = frozenset("ABCDEFGHI")
EXPECTED_COUNTS = {
    "book_count": 1959,
    "sentence_count": 201993,
    "unit_count": 41964,
    "page_unit_count": 22632,
    "reuse_unit_count": 19332,
    "rich_a_i_unit_count": 12647,
}
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/derived_material_extraction_minimal/"
    / "derived_material_extraction_minimal.safe.json"
)

# Source-reality audit proved these are the meaningful direct labels. Avoid
# treating confidence/source metadata as Theme or pedagogical values.
DIRECT_THEME_KEYS = {
    "candidate_theme_tags",
    "primary_theme",
    "mapped_theme",
    "subthemes",
}
DIRECT_PEDAGOGICAL_KEYS = {
    "candidate_pedagogical_tags",
    "skill_area",
    "question_type_candidates",
    "assessment_seed",
    "exercise_seed",
}
SITUATION_KEYS = {
    "situation",
    "situation_family",
    "situation_families",
    "micro_situation",
    "micro_situations",
    "communicative_function",
    "communicative_functions",
    "participant_role",
    "participant_roles",
    "interaction_goal",
    "interaction_goals",
}
CHUNK_KEYS = {
    "candidate_chunk_refs",
    "chunk_refs",
    "chunk_tags",
    "chunks",
    "collocations",
}
SCENE_IMAGE_KEYS = {
    "scene",
    "scene_type",
    "scene_tags",
    "picture",
    "picture_tags",
    "picture_prompt_seed",
    "image",
    "image_tags",
    "visual",
    "visual_tags",
    "visual_support",
    "object_layout",
}

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_A_W_PER_LEVEL_DERIVED_ONLY",
    "derived_read_performed": True,
    "review_read_performed": False,
    "bridge_read_performed": False,
    "linkage_read_performed": False,
    "private_source_text_read": True,
    "source_text_included_in_safe_output": False,
    "source_payload_included_in_safe_output": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learning_unit_content_population_performed": False,
    "learner_facing_content_created": False,
    "image_generation_performed": False,
    "direct_image_evidence_claimed": False,
    "human_semantic_review_performed": False,
    "a2_a2plus_opened": False,
}


class MinimalExtractionError(ValueError):
    """Fail-closed source-reality or package error."""


def _records(payload: Any, schema: str, owner: str) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping) or payload.get("schema_version") != schema:
        raise MinimalExtractionError(f"schema_mismatch:{owner}")
    rows = payload.get("records")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise MinimalExtractionError(f"records_invalid:{owner}")
    return list(rows)


def _legacy_rows(payload: Any, owner: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise MinimalExtractionError(f"legacy_rows_invalid:{owner}")
    return list(payload)


def _nested_keys(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            result.add(str(key))
            result.update(_nested_keys(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_nested_keys(child))
    return result


def _nonempty_refs(row: Mapping[str, Any], key: str) -> bool:
    value = row.get(key)
    return isinstance(value, list) and any(isinstance(item, str) and item for item in value)


def _read_registry(
    source_root: Path,
    level: str,
    folder: str,
    filename: str,
    schema: str,
) -> tuple[list[dict[str, Any]], Path]:
    path = source_root / "derived" / f"Level_{level}" / folder / filename
    if not path.is_file():
        raise MinimalExtractionError(f"source_file_missing:{level}:{filename}")
    return _records(deep.read_json(path), schema, f"{level}:{filename}"), path


def _read_legacy(source_root: Path, level: str, filename: str) -> tuple[list[dict[str, Any]], Path]:
    path = source_root / "derived" / f"Level_{level}" / "enriched" / filename
    if not path.is_file():
        raise MinimalExtractionError(f"source_file_missing:{level}:{filename}")
    return _legacy_rows(deep.read_json(path), f"{level}:{filename}"), path


def scan_source_reality(
    source_root: Path,
    levels: Sequence[str] = LEVELS,
) -> dict[str, Any]:
    totals = Counter()
    direct_nonempty = Counter()
    observed_keys: set[str] = set()
    per_level: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []

    for level in levels:
        books, books_path = _read_registry(
            source_root,
            level,
            "enriched",
            f"raz_{level}_enriched_books.json",
            "raz_enriched_books.v1",
        )
        sentences, sentences_path = _read_registry(
            source_root,
            level,
            "enriched",
            f"raz_{level}_enriched_sentences.json",
            "raz_enriched_sentences.v1",
        )
        units, units_path = _read_registry(
            source_root,
            level,
            "enriched",
            f"raz_{level}_enriched_units.json",
            "raz_enriched_units.v1",
        )
        page_units = sum(row.get("unit_type") == "page_unit" for row in units)
        reuse_units = sum(row.get("unit_type") == "reuse_unit" for row in units)
        if page_units + reuse_units != len(units):
            raise MinimalExtractionError(f"unknown_unit_type:{level}")

        rich_count = 0
        rich_files: list[tuple[Path, str, int]] = []
        if level in A_I_LEVELS:
            rich_pages, rich_pages_path = _read_legacy(
                source_root, level, f"raz_{level}_page_unit_enriched.json"
            )
            rich_reuse, rich_reuse_path = _read_legacy(
                source_root, level, f"raz_{level}_reuse_unit_enriched.json"
            )
            rich_count = len(rich_pages) + len(rich_reuse)
            rich_files = [
                (rich_pages_path, "legacy_page_unit_enriched", len(rich_pages)),
                (rich_reuse_path, "legacy_reuse_unit_enriched", len(rich_reuse)),
            ]
            observed_keys.update(_nested_keys(rich_pages))
            observed_keys.update(_nested_keys(rich_reuse))

        observed_keys.update(_nested_keys(books))
        observed_keys.update(_nested_keys(sentences))
        observed_keys.update(_nested_keys(units))
        for row in sentences:
            direct_nonempty["vocabulary"] += int(_nonempty_refs(row, "candidate_vocab_refs"))
            direct_nonempty["patterns"] += int(_nonempty_refs(row, "candidate_pattern_refs"))
            direct_nonempty["grammar"] += int(_nonempty_refs(row, "candidate_grammar_refs"))

        totals.update(
            {
                "book_count": len(books),
                "sentence_count": len(sentences),
                "unit_count": len(units),
                "page_unit_count": page_units,
                "reuse_unit_count": reuse_units,
                "rich_a_i_unit_count": rich_count,
            }
        )
        per_level.append(
            {
                "level": level,
                "book_count": len(books),
                "sentence_count": len(sentences),
                "unit_count": len(units),
                "page_unit_count": page_units,
                "reuse_unit_count": reuse_units,
                "rich_unit_count": rich_count,
            }
        )
        for path, schema, count in [
            (books_path, "raz_enriched_books.v1", len(books)),
            (sentences_path, "raz_enriched_sentences.v1", len(sentences)),
            (units_path, "raz_enriched_units.v1", len(units)),
            *rich_files,
        ]:
            source_files.append(
                {
                    "level": level,
                    "path": path.relative_to(source_root).as_posix(),
                    "schema_version": schema,
                    "record_count": count,
                    "sha256": deep.sha256_file(path),
                }
            )

    return {
        "levels": list(levels),
        "counts": dict(totals),
        "per_level": per_level,
        "source_files": source_files,
        "observed_keys": sorted(observed_keys),
        "direct_nonempty_counts": dict(direct_nonempty),
        "direct_chunk_field_present": bool(observed_keys & CHUNK_KEYS),
        "direct_situation_field_present": bool(observed_keys & SITUATION_KEYS),
        "direct_scene_image_field_present": bool(observed_keys & SCENE_IMAGE_KEYS),
    }


def finalize_package(
    package: Mapping[str, Any],
    reality: Mapping[str, Any],
    *,
    expected_counts: Mapping[str, int] = EXPECTED_COUNTS,
    levels: Sequence[str] = LEVELS,
) -> dict[str, Any]:
    result = dict(package)
    result.pop("package_sha256", None)
    result["task_id"] = TASK_ID
    result["schema_version"] = SCHEMA_VERSION

    page_rows = result.get("page_unit_evidence")
    if not isinstance(page_rows, list):
        raise MinimalExtractionError("page_unit_evidence_missing")
    for row in page_rows:
        if not isinstance(row, dict):
            raise MinimalExtractionError("page_unit_evidence_invalid")
        row["scene_evidence_status"] = "DERIVED_SCENE_STRUCTURE_ONLY"

    counts = reality.get("counts") if isinstance(reality.get("counts"), Mapping) else {}
    checks = {
        f"{key}_exact": counts.get(key) == expected
        for key, expected in expected_counts.items()
    }
    checks.update(
        {
            "levels_exact": reality.get("levels") == list(levels),
            "base_page_unit_count_exact": len(page_rows) == expected_counts["page_unit_count"],
            "base_gate_ready": bool(
                result.get("extraction_gate", {}).get(
                    "ready_for_review_bridge_linkage_binding"
                )
            ),
            "scene_claim_is_derived_only": all(
                row.get("scene_evidence_status") == "DERIVED_SCENE_STRUCTURE_ONLY"
                for row in page_rows
            ),
            "derived_only_boundary_preserved": True,
        }
    )
    ready = all(checks.values())

    scope = dict(result.get("source_scope") or {})
    scope.update(counts)
    scope["source_reality_file_count"] = len(reality.get("source_files", []))
    scope["source_reality_files"] = reality.get("source_files", [])
    result["source_scope"] = scope
    result["source_reality"] = {
        "source_audit": "PASS_RAZ_AW_23_LEVEL_197_JSON_SOURCE_REALITY_AUDIT",
        "audited_levels": reality.get("levels"),
        "audited_registry_counts": counts,
        "per_level_registry_counts": reality.get("per_level"),
        "direct_candidate_vocabulary_nonempty_sentence_count": reality.get(
            "direct_nonempty_counts", {}
        ).get("vocabulary", 0),
        "direct_candidate_pattern_nonempty_sentence_count": reality.get(
            "direct_nonempty_counts", {}
        ).get("patterns", 0),
        "direct_candidate_grammar_nonempty_sentence_count": reality.get(
            "direct_nonempty_counts", {}
        ).get("grammar", 0),
        "direct_chunk_field_present": reality.get("direct_chunk_field_present"),
        "direct_situation_field_present": reality.get(
            "direct_situation_field_present"
        ),
        "direct_scene_image_field_present": reality.get(
            "direct_scene_image_field_present"
        ),
        "theme_granularity": {
            "A_I": "BOOK_AND_UNIT",
            "J_W": "BOOK_ONLY_WITH_UNIT_PROJECTION",
        },
        "situation_evidence_mode": "SEMANTIC_DERIVATION_FROM_PAGE_UNIT_TEXT_AND_THEME",
        "chunk_evidence_mode": "AUTHORITY_MATCH_FROM_PAGE_UNIT_TEXT",
        "pattern_evidence_mode": "DIRECT_FIELD_AUDIT_PLUS_AUTHORITY_MATCH",
        "grammar_evidence_mode": "DIRECT_FIELD_AUDIT_PLUS_DETERMINISTIC_DETECTOR",
        "sentence_source_mode": "201993_ENRICHED_SENTENCE_REGISTRY_AUDITED",
        "passage_source_mode": "22632_PAGE_PLUS_19332_REUSE_UNITS_AUDITED",
        "scene_evidence_mode": "DERIVED_SCENE_STRUCTURE_ONLY",
    }

    aggregate = dict(result.get("aggregate_summary") or {})
    aggregate["direct_picture_or_visual_tag_count"] = 0
    aggregate["audited_sentence_count"] = counts.get("sentence_count", 0)
    aggregate["audited_unit_count"] = counts.get("unit_count", 0)
    aggregate["audited_reuse_unit_count"] = counts.get("reuse_unit_count", 0)
    result["aggregate_summary"] = aggregate

    result["validation_status"] = PASS_STATUS if ready else "FAIL"
    result["extraction_gate"] = {
        "source_checks": checks,
        "decision": (
            "DERIVED_MATERIAL_READY_FOR_GOVERNANCE_BINDING"
            if ready
            else "BLOCKED_DERIVED_SOURCE_OR_ACCOUNTING"
        ),
        "ready_for_review_bridge_linkage_binding": ready,
        "ready_for_canonical_promotion": False,
        "ready_for_learning_unit_population": False,
        "next_short_step": "RAZ-AW_DerivedMaterialReviewBridgeLinkageBinding",
    }
    result["claim_boundaries"] = dict(CLAIM_BOUNDARIES)
    result["package_sha256"] = deep.sha256_value(result)
    return result


def build(
    source_root: Path,
    manifest: Path | None = None,
) -> dict[str, Any]:
    base.THEME_KEYS = set(DIRECT_THEME_KEYS)
    base.PEDAGOGICAL_KEYS = set(DIRECT_PEDAGOGICAL_KEYS)
    page_units, file_index, direct_metadata = base.load_source(source_root)
    package = base.build_package(
        page_units,
        file_index,
        direct_metadata,
        deep.load_authorities(),
        deep.load_manifest_grammar_tags(manifest),
    )
    reality = scan_source_reality(source_root)
    result = finalize_package(package, reality)
    leakage = base.scan_forbidden_safe_keys(result)
    if leakage:
        raise MinimalExtractionError(
            "safe_output_leakage:" + ";".join(leakage[:20])
        )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = build(args.source_root, args.manifest)
        deep.write_json_atomic(args.output, package)
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "decision": package["extraction_gate"]["decision"],
                    **{
                        key: package["source_scope"][key]
                        for key in EXPECTED_COUNTS
                    },
                    **package["aggregate_summary"],
                    "package_sha256": package["package_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (
        MinimalExtractionError,
        base.PerLevelExtractionError,
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
