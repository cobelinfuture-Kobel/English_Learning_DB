#!/usr/bin/env python3
"""Extract RAZ A-W semantic/material evidence from per-level derived records.

This builder deliberately performs semantic discovery from
`derived/Level_A..W` only. Review, bridge, and linkage are governance layers
and are not read here. The safe output contains text-free Theme, Situation,
Authority-match, Sentence/Passage/Scene seed, and four-skill affordance
metadata. It does not promote Authority or populate Learning Units.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_schema_compatibility as compatibility

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_PerLevelDerivedSemanticMaterialExtraction"
SCHEMA_VERSION = "raz.aw.per_level_derived_semantic_material.v1"
PASS_STATUS = "PASS_RAZ_AW_PER_LEVEL_DERIVED_SEMANTIC_MATERIAL_EXTRACTION"
LEVELS = tuple(chr(code) for code in range(ord("A"), ord("W") + 1))
EXPECTED_PAGE_UNIT_COUNT = 22632
EXPECTED_BOOK_COUNT = 1959
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/per_level_derived_semantic_material/"
    / "per_level_derived_semantic_material.safe.json"
)

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_A_W_DERIVED_LEVEL_RECORDS_ONLY",
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
    "human_semantic_review_performed": False,
    "a2_a2plus_opened": False,
}

FORBIDDEN_SAFE_KEYS = {
    "text",
    "clean_text",
    "raw_text",
    "source_text",
    "original_text",
    "title",
    "sentence",
    "sentences",
    "passage",
    "transcript",
    "source_payload",
    "raw_payload",
}

EXCLUDED_FILE_TOKENS = {
    "summary",
    "validation",
    "reconciliation",
    "report",
    "inventory",
    "manifest",
    "count",
}

THEME_KEYS = {
    "candidate_theme_tags",
    "theme_tags",
    "primary_theme",
    "mapped_theme",
    "subthemes",
}
PEDAGOGICAL_KEYS = {
    "candidate_pedagogical_tags",
    "pedagogical_tags",
    "question_type_candidates",
    "skill_area",
    "assessment_seed",
    "exercise_seed",
}
DIRECT_REF_KEYS = {
    "candidate_grammar_refs": "grammar",
    "candidate_chunk_refs": "chunks",
    "candidate_pattern_refs": "patterns",
}


class PerLevelExtractionError(ValueError):
    """Fail-closed derived source, identity, or accounting error."""


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{deep.sha256_value(value)[:16].upper()}"


def _string_values(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            result.add(cleaned)
    elif isinstance(value, Mapping):
        for child in value.values():
            result.update(_string_values(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_string_values(child))
    return result


def _walk_selected(
    value: Any,
    selected_keys: set[str],
) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in selected_keys:
                result.update(_string_values(child))
            result.update(_walk_selected(child, selected_keys))
    elif isinstance(value, list):
        for child in value:
            result.update(_walk_selected(child, selected_keys))
    return result


def _walk_direct_refs(value: Any) -> dict[str, set[str]]:
    result = {name: set() for name in DIRECT_REF_KEYS.values()}
    if isinstance(value, Mapping):
        for key, child in value.items():
            target = DIRECT_REF_KEYS.get(str(key))
            if target:
                result[target].update(_string_values(child))
            nested = _walk_direct_refs(child)
            for name, refs in nested.items():
                result[name].update(refs)
    elif isinstance(value, list):
        for child in value:
            nested = _walk_direct_refs(child)
            for name, refs in nested.items():
                result[name].update(refs)
    return result


def _payload_records(payload: Any, owner: str) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("records"), list):
        rows = payload["records"]
    else:
        raise PerLevelExtractionError(f"record_payload_unavailable:{owner}")
    if not all(isinstance(row, Mapping) for row in rows):
        raise PerLevelExtractionError(f"invalid_record_payload:{owner}")
    return list(rows)


def discover_record_bearing_files(source_root: Path, level: str) -> list[Path]:
    level_root = source_root / "derived" / f"Level_{level}"
    if not level_root.is_dir():
        raise PerLevelExtractionError(f"derived_level_directory_missing:{level}")
    files: list[Path] = []
    for path in sorted(level_root.rglob("*.json")):
        name = path.name.casefold()
        if not name.startswith(f"raz_{level.casefold()}_"):
            continue
        if any(token in name for token in EXCLUDED_FILE_TOKENS):
            continue
        try:
            payload = deep.read_json(path)
            _payload_records(payload, f"{level}:{path.name}")
        except (deep.AlignmentError, PerLevelExtractionError):
            continue
        files.append(path)
    if not files:
        raise PerLevelExtractionError(f"no_record_bearing_files:{level}")
    return files


def load_level_direct_metadata(
    source_root: Path,
    level: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    themes: set[str] = set()
    pedagogical: set[str] = set()
    direct_refs = {name: set() for name in DIRECT_REF_KEYS.values()}
    record_count = 0
    file_index: list[dict[str, Any]] = []
    for path in discover_record_bearing_files(source_root, level):
        payload = deep.read_json(path)
        rows = _payload_records(payload, f"{level}:{path.name}")
        record_count += len(rows)
        for row in rows:
            themes.update(_walk_selected(row, THEME_KEYS))
            pedagogical.update(_walk_selected(row, PEDAGOGICAL_KEYS))
            nested_refs = _walk_direct_refs(row)
            for name, refs in nested_refs.items():
                direct_refs[name].update(refs)
        schema_version = payload.get("schema_version") if isinstance(payload, Mapping) else None
        file_index.append(
            {
                "level": level,
                "path": path.relative_to(source_root).as_posix(),
                "schema_version": str(schema_version or "list_payload"),
                "record_count": len(rows),
                "sha256": deep.sha256_file(path),
            }
        )
    return (
        {
            "direct_theme_labels": sorted(themes),
            "direct_pedagogical_tags": sorted(pedagogical),
            "direct_candidate_grammar_refs": sorted(direct_refs["grammar"]),
            "direct_candidate_chunk_refs": sorted(direct_refs["chunks"]),
            "direct_candidate_pattern_refs": sorted(direct_refs["patterns"]),
            "record_bearing_record_count": record_count,
        },
        file_index,
    )


def load_source(
    source_root: Path,
    levels: Sequence[str] = LEVELS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    page_units: list[dict[str, Any]] = []
    file_index: list[dict[str, Any]] = []
    direct_metadata: dict[str, dict[str, Any]] = {}
    seen_refs: set[str] = set()
    for level in levels:
        rows, semantic_paths, derived_schema = compatibility.load_derived_level(
            source_root, level
        )
        for row in rows:
            ref = str(row.get("page_unit_id") or "")
            if not ref or ref in seen_refs:
                raise PerLevelExtractionError(
                    f"invalid_or_duplicate_page_unit_ref:{level}:{ref}"
                )
            if row.get("level") != level:
                raise PerLevelExtractionError(f"page_unit_level_mismatch:{ref}")
            if not isinstance(row.get("text"), str) or not row["text"].strip():
                raise PerLevelExtractionError(f"page_unit_text_missing:{ref}")
            page_units.append(row)
            seen_refs.add(ref)
        metadata, record_files = load_level_direct_metadata(source_root, level)
        direct_metadata[level] = metadata
        file_index.extend(record_files)
        file_index.append(
            {
                "level": level,
                "path": "|".join(
                    path.relative_to(source_root).as_posix() for path in semantic_paths
                ),
                "schema_version": derived_schema,
                "record_count": len(rows),
                "sha256": deep.sha256_value(
                    [deep.sha256_file(path) for path in semantic_paths]
                ),
            }
        )
    return page_units, file_index, direct_metadata


def _theme_values(row: Mapping[str, Any]) -> set[str]:
    tags = row.get("theme_tags") if isinstance(row.get("theme_tags"), Mapping) else {}
    values: set[str] = set()
    for key in ("primary_theme", "mapped_theme", "subthemes"):
        values.update(_string_values(tags.get(key)))
    return values


def _reuse_values(row: Mapping[str, Any]) -> set[str]:
    reuse = row.get("reuse_tags") if isinstance(row.get("reuse_tags"), Mapping) else {}
    return {value.casefold() for value in _string_values(reuse)}


def _scene_structure(
    row: Mapping[str, Any],
    semantic: Mapping[str, set[str]],
    discourse: str,
) -> str:
    if discourse == "dialogue_or_question_answer":
        return "SOCIAL_INTERACTION_SCENE"
    if discourse == "sequence":
        return "SEQUENCE_SCENE"
    if discourse == "cause_effect":
        return "CAUSE_EFFECT_SCENE"
    if discourse == "comparison_or_contrast":
        return "COMPARISON_SCENE"
    if "describing_location" in semantic["communicative_functions"]:
        return "LOCATION_RELATION_SCENE"
    if semantic["situation_families"] & {
        "science_observation",
        "nature_observation",
        "animals_and_habitats",
    }:
        return "INFORMATIONAL_SCENE"
    if int(row.get("sentence_count") or 0) <= 1 and len(deep.tokens(str(row["text"]))) <= 12:
        return "OBJECT_OR_ENTITY_SCENE"
    return "GENERAL_CONTEXT_SCENE"


def _four_skill_affordances(
    row: Mapping[str, Any],
    discourse: str,
    scene_structure: str,
) -> set[str]:
    reuse_values = _reuse_values(row)
    content = row.get("content_unit_tags") if isinstance(row.get("content_unit_tags"), Mapping) else {}
    values = {"READING_SOURCE"}
    if (
        "listening_audio" in reuse_values
        or content.get("has_direct_speech") is True
        or discourse == "dialogue_or_question_answer"
    ):
        values.add("LISTENING_ADAPTATION")
    if (
        discourse == "dialogue_or_question_answer"
        or scene_structure != "GENERAL_CONTEXT_SCENE"
    ):
        values.add("SPEAKING_PROMPT")
    if (
        "writing_model" in reuse_values
        or discourse in {
            "sequence",
            "cause_effect",
            "comparison_or_contrast",
            "simple_narrative_or_description",
        }
    ):
        values.add("WRITING_MODEL")
    return values


def _seed_maturity(
    grammar_refs: set[str],
    vocabulary_refs: set[str],
    chunk_refs: set[str],
    pattern_refs: set[str],
    discourse: str,
    sentence_count: int,
) -> str:
    if grammar_refs and vocabulary_refs and (chunk_refs or pattern_refs):
        return "STRICT_CORE_SENTENCE_SEED"
    if grammar_refs and vocabulary_refs:
        return "BROAD_CORE_SENTENCE_SEED"
    if discourse == "dialogue_or_question_answer":
        return "DIALOGUE_TURN_SEED"
    if sentence_count >= 2:
        return "PASSAGE_SUPPORT_SEED"
    return "SUPPORT_SENTENCE_SEED"


def _level_template(level: str, direct: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "level": level,
        "page_unit_refs": set(),
        "book_ids": set(),
        "direct_theme_labels": set(direct["direct_theme_labels"]),
        "direct_pedagogical_tags": set(direct["direct_pedagogical_tags"]),
        "direct_candidate_grammar_refs": set(direct["direct_candidate_grammar_refs"]),
        "direct_candidate_chunk_refs": set(direct["direct_candidate_chunk_refs"]),
        "direct_candidate_pattern_refs": set(direct["direct_candidate_pattern_refs"]),
        "observed_theme_labels": set(),
        "situation_families": set(),
        "micro_situations": set(),
        "communicative_functions": set(),
        "participant_roles": set(),
        "interaction_goals": set(),
        "matched_vocabulary_refs": set(),
        "matched_chunk_refs": set(),
        "matched_pattern_refs": set(),
        "matched_grammar_refs": set(),
        "sentence_seed_counts": Counter(),
        "discourse_shape_counts": Counter(),
        "scene_structure_counts": Counter(),
        "four_skill_affordance_counts": Counter(),
        "semantic_duplicate_groups": set(),
        "record_bearing_record_count": int(direct["record_bearing_record_count"]),
    }


def build_package(
    page_units: Sequence[Mapping[str, Any]],
    file_index: Sequence[Mapping[str, Any]],
    direct_metadata: Mapping[str, Mapping[str, Any]],
    authorities: Mapping[str, Any],
    manifest_tags: Mapping[str, set[str]],
    *,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
) -> dict[str, Any]:
    levels = {
        level: _level_template(level, direct_metadata[level]) for level in LEVELS
    }
    evidence_rows: list[dict[str, Any]] = []
    all_books: set[tuple[str, str]] = set()
    seen_refs: set[str] = set()

    for row in page_units:
        ref = str(row.get("page_unit_id") or "")
        level = str(row.get("level") or "")
        book_id = str(row.get("book_id") or "")
        if level not in levels or not ref or ref in seen_refs or not book_id:
            raise PerLevelExtractionError(f"invalid_page_unit_identity:{ref}:{level}")
        text = str(row["text"])
        themes = _theme_values(row)
        semantic = deep.semantic_alignment(row)
        vocabulary_refs = deep.match_vocabulary(text, authorities["vocabulary"])
        chunk_refs = deep.match_template_authority(text, authorities["chunks"])
        pattern_refs = deep.match_template_authority(text, authorities["patterns"])
        grammar_refs = deep.grammar_units(text, manifest_tags.get(ref, set()))
        discourse = deep.discourse_shape(row)
        scene = _scene_structure(row, semantic, discourse)
        affordances = _four_skill_affordances(row, discourse, scene)
        sentence_count = int(row.get("sentence_count") or len(deep.sentence_spans(text)))
        maturity = _seed_maturity(
            grammar_refs,
            vocabulary_refs,
            chunk_refs,
            pattern_refs,
            discourse,
            sentence_count,
        )
        duplicate_group = stable_id("SDUP", deep.normalize(text))
        reuse_values = _reuse_values(row)
        scene_evidence_status = (
            "DIRECT_PICTURE_OR_VISUAL_TAG"
            if reuse_values & {"picture_prompt_seed", "picture", "visual", "scene"}
            else "DERIVED_SCENE_STRUCTURE"
        )

        acc = levels[level]
        acc["page_unit_refs"].add(ref)
        acc["book_ids"].add(book_id)
        acc["observed_theme_labels"].update(themes)
        for key in (
            "situation_families",
            "micro_situations",
            "communicative_functions",
            "participant_roles",
            "interaction_goals",
        ):
            acc[key].update(semantic[key])
        acc["matched_vocabulary_refs"].update(vocabulary_refs)
        acc["matched_chunk_refs"].update(chunk_refs)
        acc["matched_pattern_refs"].update(pattern_refs)
        acc["matched_grammar_refs"].update(grammar_refs)
        acc["sentence_seed_counts"][maturity] += 1
        acc["discourse_shape_counts"][discourse] += 1
        acc["scene_structure_counts"][scene] += 1
        acc["four_skill_affordance_counts"].update(affordances)
        acc["semantic_duplicate_groups"].add(duplicate_group)
        seen_refs.add(ref)
        all_books.add((level, book_id))

        evidence_rows.append(
            {
                "source_unit_ref": ref,
                "source_level": level,
                "source_book_id": book_id,
                "direct_theme_labels": sorted(themes),
                "situation_families": sorted(semantic["situation_families"]),
                "micro_situations": sorted(semantic["micro_situations"]),
                "communicative_functions": sorted(semantic["communicative_functions"]),
                "participant_roles": sorted(semantic["participant_roles"]),
                "interaction_goals": sorted(semantic["interaction_goals"]),
                "matched_vocabulary_refs": sorted(vocabulary_refs),
                "matched_chunk_refs": sorted(chunk_refs),
                "matched_pattern_refs": sorted(pattern_refs),
                "matched_grammar_refs": sorted(grammar_refs),
                "sentence_seed_maturity": maturity,
                "semantic_duplicate_group_id": duplicate_group,
                "discourse_shape": discourse,
                "passage_seed_status": "SUPPORTED" if sentence_count >= 2 else "NOT_A_PASSAGE",
                "scene_structure": scene,
                "scene_evidence_status": scene_evidence_status,
                "four_skill_affordances": sorted(affordances),
                "a1_a1plus_use_status": (
                    "A1_A1PLUS_REVIEW_REQUIRED"
                    if level <= "I"
                    else "SOURCE_EVIDENCE_ONLY_REWRITE_REQUIRED"
                ),
                "promotion_status": "NOT_PROMOTED",
            }
        )

    per_level = []
    for level in LEVELS:
        acc = levels[level]
        direct_and_observed_themes = (
            acc["direct_theme_labels"] | acc["observed_theme_labels"]
        )
        per_level.append(
            {
                "level": level,
                "page_unit_count": len(acc["page_unit_refs"]),
                "book_count": len(acc["book_ids"]),
                "record_bearing_record_count": acc["record_bearing_record_count"],
                "direct_theme_labels": sorted(acc["direct_theme_labels"]),
                "observed_theme_labels": sorted(acc["observed_theme_labels"]),
                "combined_theme_labels": sorted(direct_and_observed_themes),
                "situation_families": sorted(acc["situation_families"]),
                "micro_situations": sorted(acc["micro_situations"]),
                "communicative_functions": sorted(acc["communicative_functions"]),
                "participant_roles": sorted(acc["participant_roles"]),
                "interaction_goals": sorted(acc["interaction_goals"]),
                "direct_candidate_grammar_refs": sorted(acc["direct_candidate_grammar_refs"]),
                "direct_candidate_chunk_refs": sorted(acc["direct_candidate_chunk_refs"]),
                "direct_candidate_pattern_refs": sorted(acc["direct_candidate_pattern_refs"]),
                "matched_vocabulary_refs": sorted(acc["matched_vocabulary_refs"]),
                "matched_chunk_refs": sorted(acc["matched_chunk_refs"]),
                "matched_pattern_refs": sorted(acc["matched_pattern_refs"]),
                "matched_grammar_refs": sorted(acc["matched_grammar_refs"]),
                "direct_pedagogical_tags": sorted(acc["direct_pedagogical_tags"]),
                "sentence_seed_counts": dict(sorted(acc["sentence_seed_counts"].items())),
                "semantic_duplicate_group_count": len(acc["semantic_duplicate_groups"]),
                "discourse_shape_counts": dict(sorted(acc["discourse_shape_counts"].items())),
                "scene_structure_counts": dict(sorted(acc["scene_structure_counts"].items())),
                "four_skill_affordance_counts": dict(
                    sorted(acc["four_skill_affordance_counts"].items())
                ),
            }
        )

    aggregate_sets = {
        key: set()
        for key in (
            "combined_theme_labels",
            "situation_families",
            "micro_situations",
            "communicative_functions",
            "participant_roles",
            "interaction_goals",
            "matched_vocabulary_refs",
            "matched_chunk_refs",
            "matched_pattern_refs",
            "matched_grammar_refs",
        )
    }
    for row in per_level:
        for key in aggregate_sets:
            aggregate_sets[key].update(row[key])

    source_checks = {
        "levels_exact": {row["level"] for row in per_level} == set(LEVELS),
        "page_unit_count_exact": len(evidence_rows) == expected_page_unit_count,
        "book_count_exact": len(all_books) == expected_book_count,
        "all_page_units_unique": len(seen_refs) == len(evidence_rows),
        "all_page_units_have_situation": all(
            row["situation_families"] and row["micro_situations"]
            for row in evidence_rows
        ),
        "all_page_units_have_sentence_seed": all(
            row["sentence_seed_maturity"] for row in evidence_rows
        ),
        "all_page_units_have_scene_structure": all(
            row["scene_structure"] for row in evidence_rows
        ),
        "all_page_units_have_four_skill_affordance": all(
            row["four_skill_affordances"] for row in evidence_rows
        ),
        "derived_only_boundary_preserved": True,
    }
    ready = all(source_checks.values())
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "source_scope": {
            "levels": list(LEVELS),
            "page_unit_count": len(evidence_rows),
            "book_count": len(all_books),
            "record_bearing_file_count": len(file_index),
            "source_files": sorted(
                [dict(row) for row in file_index],
                key=lambda row: (row["level"], row["path"]),
            ),
        },
        "authority_baselines": {
            name: {
                "count": authority["count"],
                "source_path": authority["source_path"],
                "source_sha256": authority["source_sha256"],
            }
            for name, authority in authorities.items()
        },
        "per_level_summary": per_level,
        "page_unit_evidence": sorted(
            evidence_rows, key=lambda row: row["source_unit_ref"]
        ),
        "aggregate_summary": {
            "combined_theme_label_count": len(aggregate_sets["combined_theme_labels"]),
            "combined_theme_labels": sorted(aggregate_sets["combined_theme_labels"]),
            "situation_family_count": len(aggregate_sets["situation_families"]),
            "micro_situation_count": len(aggregate_sets["micro_situations"]),
            "communicative_function_count": len(aggregate_sets["communicative_functions"]),
            "participant_role_count": len(aggregate_sets["participant_roles"]),
            "interaction_goal_count": len(aggregate_sets["interaction_goals"]),
            "matched_vocabulary_ref_count": len(aggregate_sets["matched_vocabulary_refs"]),
            "matched_chunk_ref_count": len(aggregate_sets["matched_chunk_refs"]),
            "matched_pattern_ref_count": len(aggregate_sets["matched_pattern_refs"]),
            "matched_grammar_ref_count": len(aggregate_sets["matched_grammar_refs"]),
            "semantic_duplicate_group_count": len(
                {row["semantic_duplicate_group_id"] for row in evidence_rows}
            ),
            "passage_seed_count": sum(
                row["passage_seed_status"] == "SUPPORTED" for row in evidence_rows
            ),
            "direct_picture_or_visual_tag_count": sum(
                row["scene_evidence_status"] == "DIRECT_PICTURE_OR_VISUAL_TAG"
                for row in evidence_rows
            ),
        },
        "extraction_gate": {
            "source_checks": source_checks,
            "decision": (
                "PER_LEVEL_DERIVED_MATERIAL_READY_FOR_GOVERNANCE_BINDING"
                if ready
                else "BLOCKED_DERIVED_SOURCE_OR_ACCOUNTING"
            ),
            "ready_for_review_bridge_linkage_binding": ready,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": "RAZ-AW_DerivedMaterialReviewBridgeLinkageBinding",
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def scan_forbidden_safe_keys(value: Any, pointer: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                errors.append(f"forbidden_safe_key:{pointer}.{key}")
            errors.extend(scan_forbidden_safe_keys(child, f"{pointer}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_forbidden_safe_keys(child, f"{pointer}[{index}]"))
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        page_units, file_index, direct_metadata = load_source(args.source_root)
        package = build_package(
            page_units,
            file_index,
            direct_metadata,
            deep.load_authorities(),
            deep.load_manifest_grammar_tags(args.manifest),
        )
        leakage = scan_forbidden_safe_keys(package)
        if leakage:
            raise PerLevelExtractionError(
                "safe_output_leakage:" + ";".join(leakage[:20])
            )
        deep.write_json_atomic(args.output, package)
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "decision": package["extraction_gate"]["decision"],
                    "page_unit_count": package["source_scope"]["page_unit_count"],
                    "book_count": package["source_scope"]["book_count"],
                    **package["aggregate_summary"],
                    "package_sha256": package["package_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (
        PerLevelExtractionError,
        compatibility.DerivedSchemaCompatibilityError,
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
