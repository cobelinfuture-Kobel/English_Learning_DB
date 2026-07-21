#!/usr/bin/env python3
"""Extract text-free RAZ A-W material evidence from verified derived sources.

The source contract follows the completed local 197-JSON reality audit:

* A-W book, sentence, unit, normalized page-unit, and normalized reuse registries;
* A-I legacy enriched page/reuse units as richer metadata only;
* no review, bridge, or linkage read;
* no canonical promotion, learner-facing content, image-evidence claim, or Unit fill.

Source macro-theme labels and source subtheme labels are deliberately separated.
Grammar detection returns the 24 learning-unit identifiers defined by the existing
A1/A1+ detector; it does not claim coverage of the 109 canonical EGP rows.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_schema_compatibility as compatibility

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_DerivedMaterialExtractionMinimal"
SCHEMA_VERSION = "raz.aw.derived_material_extraction_minimal.v2"
PASS_STATUS = "PASS_RAZ_AW_DERIVED_MATERIAL_EXTRACTION_MINIMAL"
LEVELS = tuple(chr(code) for code in range(ord("A"), ord("W") + 1))
EXPECTED_PAGE_UNIT_COUNT = 22632
EXPECTED_BOOK_COUNT = 1959
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/derived_material_extraction_minimal/"
    / "derived_material_extraction_minimal.safe.json"
)

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

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_A_W_DERIVED_ONLY",
    "review_read_performed": False,
    "bridge_read_performed": False,
    "linkage_read_performed": False,
    "private_source_text_read": True,
    "source_text_included_in_safe_output": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learning_unit_population_performed": False,
    "learner_facing_content_created": False,
    "direct_image_evidence_available": False,
    "scene_structure_is_text_derived": True,
    "source_theme_labels_are_not_canonical_theme_authority": True,
    "grammar_refs_are_learning_unit_ids_not_egp_row_ids": True,
    "a2_a2plus_opened": False,
}


class MinimalExtractionError(ValueError):
    """Fail-closed source, identity, accounting, or leakage error."""


def _strings(value: Any) -> set[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return {cleaned} if cleaned else set()
    if isinstance(value, list):
        result: set[str] = set()
        for child in value:
            result.update(_strings(child))
        return result
    return set()


def _clean_labels(values: set[str]) -> set[str]:
    return {
        value
        for value in values
        if value.casefold() not in {"unknown", "none", "null"}
    }


def _theme_components_from_record(record: Mapping[str, Any]) -> dict[str, set[str]]:
    """Separate source macro-theme labels from source subtheme/topic labels."""
    macro = _strings(record.get("candidate_theme_tags"))
    subthemes: set[str] = set()
    tags = record.get("theme_tags")
    if isinstance(tags, Mapping):
        macro.update(_strings(tags.get("primary_theme")))
        macro.update(_strings(tags.get("mapped_theme")))
        subthemes.update(_strings(tags.get("subthemes")))
    return {
        "source_macro_theme_labels": _clean_labels(macro),
        "source_subtheme_labels": _clean_labels(subthemes),
    }


def _pedagogy_labels(record: Mapping[str, Any]) -> set[str]:
    result = _strings(record.get("candidate_pedagogical_tags"))
    tags = record.get("pedagogical_tags")
    if not isinstance(tags, Mapping):
        return result
    result.update(_strings(tags.get("skill_area")))
    for key in ("question_type_candidates", "assessment_seed", "exercise_seed"):
        for value in _strings(tags.get(key)):
            result.add(f"{key}:{value}")
    derivation = tags.get("derivation_potential")
    if isinstance(derivation, Mapping):
        for key, value in derivation.items():
            if value is True:
                result.add(f"derivation:{key}")
            elif isinstance(value, str) and value.strip() and value.casefold() != "none":
                result.add(f"derivation:{key}:{value.strip()}")
    return result


def _candidate_refs(record: Mapping[str, Any]) -> dict[str, set[str]]:
    return {
        "vocabulary": _strings(record.get("candidate_vocab_refs")),
        "chunks": _strings(record.get("candidate_chunk_refs")),
        "patterns": _strings(record.get("candidate_pattern_refs")),
        "grammar_units": _strings(record.get("candidate_grammar_refs")),
    }


def _records(path: Path) -> list[Mapping[str, Any]]:
    payload = deep.read_json(path)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("records"), list):
        rows = payload["records"]
    else:
        raise MinimalExtractionError(f"record_payload_unavailable:{path}")
    if not all(isinstance(row, Mapping) for row in rows):
        raise MinimalExtractionError(f"invalid_record_payload:{path}")
    return list(rows)


def _exact_derived_file(root: Path, level: str, filename: str) -> Path:
    return compatibility.discover_named(root, level, "derived", filename)


def load_direct_metadata(
    source_root: Path,
    level: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    macro_themes: set[str] = set()
    subthemes: set[str] = set()
    pedagogy: set[str] = set()
    direct_refs = {
        name: set()
        for name in ("vocabulary", "chunks", "patterns", "grammar_units")
    }
    source_index: list[dict[str, Any]] = []

    filenames = [
        f"raz_{level}_enriched_books.json",
        f"raz_{level}_enriched_sentences.json",
    ]
    if level <= "I":
        filenames.extend(
            [
                f"raz_{level}_page_unit_enriched.json",
                f"raz_{level}_reuse_unit_enriched.json",
            ]
        )

    for filename in filenames:
        path = _exact_derived_file(source_root, level, filename)
        rows = _records(path)
        for row in rows:
            themes = _theme_components_from_record(row)
            macro_themes.update(themes["source_macro_theme_labels"])
            subthemes.update(themes["source_subtheme_labels"])
            pedagogy.update(_pedagogy_labels(row))
            refs = _candidate_refs(row)
            for name, values in refs.items():
                direct_refs[name].update(values)
        source_index.append(
            {
                "level": level,
                "path": path.relative_to(source_root).as_posix(),
                "record_count": len(rows),
                "sha256": deep.sha256_file(path),
            }
        )

    return (
        {
            "source_macro_theme_labels": sorted(macro_themes),
            "source_subtheme_labels": sorted(subthemes),
            "pedagogy_labels": sorted(pedagogy),
            "direct_candidate_vocabulary_refs": sorted(direct_refs["vocabulary"]),
            "direct_candidate_chunk_refs": sorted(direct_refs["chunks"]),
            "direct_candidate_pattern_refs": sorted(direct_refs["patterns"]),
            "direct_candidate_grammar_unit_refs": sorted(direct_refs["grammar_units"]),
        },
        source_index,
    )


def load_source(
    source_root: Path,
    levels: Sequence[str] = LEVELS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    page_units: list[dict[str, Any]] = []
    source_index: list[dict[str, Any]] = []
    metadata: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()

    for level in levels:
        rows, semantic_paths, derived_schema = compatibility.load_derived_level(
            source_root, level
        )
        for row in rows:
            ref = str(row.get("page_unit_id") or "")
            if not ref or ref in seen:
                raise MinimalExtractionError(
                    f"invalid_or_duplicate_page_unit_ref:{level}:{ref}"
                )
            if row.get("level") != level:
                raise MinimalExtractionError(f"page_unit_level_mismatch:{ref}")
            if not isinstance(row.get("text"), str) or not row["text"].strip():
                raise MinimalExtractionError(f"page_unit_text_missing:{ref}")
            page_units.append(dict(row))
            seen.add(ref)

        direct, files = load_direct_metadata(source_root, level)
        metadata[level] = direct
        source_index.extend(files)
        source_index.append(
            {
                "level": level,
                "path": "|".join(
                    path.relative_to(source_root).as_posix()
                    for path in semantic_paths
                ),
                "record_count": len(rows),
                "derived_schema": derived_schema,
                "sha256": deep.sha256_value(
                    [deep.sha256_file(path) for path in semantic_paths]
                ),
            }
        )

    return page_units, source_index, metadata


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
    sentence_count = int(row.get("sentence_count") or 0)
    if sentence_count <= 1 and len(deep.tokens(str(row["text"]))) <= 12:
        return "OBJECT_OR_ENTITY_SCENE"
    return "GENERAL_CONTEXT_SCENE"


def _four_skill_affordances(
    row: Mapping[str, Any],
    discourse: str,
    scene: str,
) -> set[str]:
    values = {"READING_SOURCE"}
    content = row.get("content_unit_tags")
    if not isinstance(content, Mapping):
        content = {}
    if content.get("has_direct_speech") is True or discourse == "dialogue_or_question_answer":
        values.add("LISTENING_ADAPTATION")
    if discourse == "dialogue_or_question_answer" or scene != "GENERAL_CONTEXT_SCENE":
        values.add("SPEAKING_PROMPT")
    if discourse in {
        "sequence",
        "cause_effect",
        "comparison_or_contrast",
        "simple_narrative_or_description",
    }:
        values.add("WRITING_MODEL")
    return values


def _seed_maturity(
    grammar_unit_refs: set[str],
    vocabulary_refs: set[str],
    chunk_refs: set[str],
    pattern_refs: set[str],
    discourse: str,
    sentence_count: int,
) -> str:
    if grammar_unit_refs and vocabulary_refs and (chunk_refs or pattern_refs):
        return "STRICT_CORE_SENTENCE_SEED"
    if grammar_unit_refs and vocabulary_refs:
        return "BROAD_CORE_SENTENCE_SEED"
    if discourse == "dialogue_or_question_answer":
        return "DIALOGUE_TURN_SEED"
    if sentence_count >= 2:
        return "PASSAGE_SUPPORT_SEED"
    return "SUPPORT_SENTENCE_SEED"


def build_package(
    page_units: Sequence[Mapping[str, Any]],
    source_index: Sequence[Mapping[str, Any]],
    direct_metadata: Mapping[str, Mapping[str, Any]],
    authorities: Mapping[str, Any],
    manifest_tags: Mapping[str, set[str]],
    *,
    levels: Sequence[str] = LEVELS,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
) -> dict[str, Any]:
    level_state = {
        level: {
            "refs": set(),
            "books": set(),
            "macro_themes": set(
                direct_metadata[level]["source_macro_theme_labels"]
            ),
            "subthemes": set(direct_metadata[level]["source_subtheme_labels"]),
            "pedagogy": set(direct_metadata[level]["pedagogy_labels"]),
            "families": set(),
            "micro": set(),
            "functions": set(),
            "roles": set(),
            "goals": set(),
            "vocabulary": set(),
            "chunks": set(),
            "patterns": set(),
            "grammar_units": set(),
            "seed_counts": Counter(),
            "discourse_counts": Counter(),
            "scene_counts": Counter(),
            "skill_counts": Counter(),
            "duplicate_groups": set(),
        }
        for level in levels
    }
    evidence: list[dict[str, Any]] = []
    books: set[tuple[str, str]] = set()
    seen: set[str] = set()

    for row in page_units:
        ref = str(row.get("page_unit_id") or "")
        level = str(row.get("level") or "")
        book_id = str(row.get("book_id") or "")
        if level not in level_state or not ref or ref in seen or not book_id:
            raise MinimalExtractionError(f"invalid_page_unit_identity:{level}:{ref}")
        text = str(row["text"])
        semantic = deep.semantic_alignment(row)
        vocabulary = deep.match_vocabulary(text, authorities["vocabulary"])
        chunks = deep.match_template_authority(text, authorities["chunks"])
        patterns = deep.match_template_authority(text, authorities["patterns"])
        grammar_units = deep.grammar_units(text, manifest_tags.get(ref, set()))
        discourse = deep.discourse_shape(row)
        scene = _scene_structure(row, semantic, discourse)
        skills = _four_skill_affordances(row, discourse, scene)
        sentence_count = int(
            row.get("sentence_count") or len(deep.sentence_spans(text))
        )
        maturity = _seed_maturity(
            grammar_units,
            vocabulary,
            chunks,
            patterns,
            discourse,
            sentence_count,
        )
        duplicate_group = (
            f"SDUP_{deep.sha256_value(deep.normalize(text))[:16].upper()}"
        )
        themes = _theme_components_from_record(row)

        state = level_state[level]
        state["refs"].add(ref)
        state["books"].add(book_id)
        state["macro_themes"].update(themes["source_macro_theme_labels"])
        state["subthemes"].update(themes["source_subtheme_labels"])
        state["families"].update(semantic["situation_families"])
        state["micro"].update(semantic["micro_situations"])
        state["functions"].update(semantic["communicative_functions"])
        state["roles"].update(semantic["participant_roles"])
        state["goals"].update(semantic["interaction_goals"])
        state["vocabulary"].update(vocabulary)
        state["chunks"].update(chunks)
        state["patterns"].update(patterns)
        state["grammar_units"].update(grammar_units)
        state["seed_counts"][maturity] += 1
        state["discourse_counts"][discourse] += 1
        state["scene_counts"][scene] += 1
        state["skill_counts"].update(skills)
        state["duplicate_groups"].add(duplicate_group)
        books.add((level, book_id))
        seen.add(ref)

        evidence.append(
            {
                "source_unit_ref": ref,
                "source_level": level,
                "source_book_id": book_id,
                "source_macro_theme_labels": sorted(
                    themes["source_macro_theme_labels"]
                ),
                "source_subtheme_labels": sorted(
                    themes["source_subtheme_labels"]
                ),
                "situation_families": sorted(semantic["situation_families"]),
                "micro_situations": sorted(semantic["micro_situations"]),
                "communicative_functions": sorted(
                    semantic["communicative_functions"]
                ),
                "participant_roles": sorted(semantic["participant_roles"]),
                "interaction_goals": sorted(semantic["interaction_goals"]),
                "matched_vocabulary_refs": sorted(vocabulary),
                "matched_chunk_refs": sorted(chunks),
                "matched_pattern_refs": sorted(patterns),
                "matched_grammar_unit_refs": sorted(grammar_units),
                "sentence_seed_maturity": maturity,
                "semantic_duplicate_group_id": duplicate_group,
                "discourse_shape": discourse,
                "passage_seed_status": (
                    "SUPPORTED" if sentence_count >= 2 else "NOT_A_PASSAGE"
                ),
                "scene_structure": scene,
                "scene_evidence_status": "DERIVED_SCENE_STRUCTURE",
                "four_skill_affordances": sorted(skills),
                "a1_a1plus_use_status": (
                    "A1_A1PLUS_REVIEW_REQUIRED"
                    if level <= "I"
                    else "SOURCE_EVIDENCE_ONLY_REWRITE_REQUIRED"
                ),
                "promotion_status": "NOT_PROMOTED",
            }
        )

    per_level: list[dict[str, Any]] = []
    for level in levels:
        state = level_state[level]
        direct = direct_metadata[level]
        per_level.append(
            {
                "level": level,
                "page_unit_count": len(state["refs"]),
                "book_count": len(state["books"]),
                "source_macro_theme_labels": sorted(state["macro_themes"]),
                "source_subtheme_labels": sorted(state["subthemes"]),
                "situation_families": sorted(state["families"]),
                "micro_situations": sorted(state["micro"]),
                "communicative_functions": sorted(state["functions"]),
                "participant_roles": sorted(state["roles"]),
                "interaction_goals": sorted(state["goals"]),
                "direct_candidate_vocabulary_refs": direct[
                    "direct_candidate_vocabulary_refs"
                ],
                "direct_candidate_chunk_refs": direct[
                    "direct_candidate_chunk_refs"
                ],
                "direct_candidate_pattern_refs": direct[
                    "direct_candidate_pattern_refs"
                ],
                "direct_candidate_grammar_unit_refs": direct[
                    "direct_candidate_grammar_unit_refs"
                ],
                "matched_vocabulary_refs": sorted(state["vocabulary"]),
                "matched_chunk_refs": sorted(state["chunks"]),
                "matched_pattern_refs": sorted(state["patterns"]),
                "matched_grammar_unit_refs": sorted(state["grammar_units"]),
                "direct_pedagogy_labels": sorted(state["pedagogy"]),
                "sentence_seed_counts": dict(sorted(state["seed_counts"].items())),
                "semantic_duplicate_group_count": len(
                    state["duplicate_groups"]
                ),
                "discourse_shape_counts": dict(
                    sorted(state["discourse_counts"].items())
                ),
                "scene_structure_counts": dict(
                    sorted(state["scene_counts"].items())
                ),
                "four_skill_affordance_counts": dict(
                    sorted(state["skill_counts"].items())
                ),
            }
        )

    def aggregate(key: str) -> set[str]:
        return {value for row in per_level for value in row[key]}

    checks = {
        "levels_exact": {row["level"] for row in per_level} == set(levels),
        "page_unit_count_exact": len(evidence) == expected_page_unit_count,
        "book_count_exact": len(books) == expected_book_count,
        "all_page_units_unique": len(seen) == len(evidence),
        "all_page_units_have_situation": all(
            row["situation_families"] and row["micro_situations"]
            for row in evidence
        ),
        "all_page_units_have_sentence_seed": all(
            row["sentence_seed_maturity"] for row in evidence
        ),
        "all_page_units_have_scene_structure": all(
            row["scene_structure"] for row in evidence
        ),
        "all_page_units_have_skill_affordance": all(
            row["four_skill_affordances"] for row in evidence
        ),
        "all_scene_evidence_text_derived": all(
            row["scene_evidence_status"] == "DERIVED_SCENE_STRUCTURE"
            for row in evidence
        ),
        "theme_taxonomy_boundary_separated": all(
            "theme_labels" not in row for row in evidence
        ),
        "grammar_unit_boundary_explicit": all(
            "matched_grammar_refs" not in row for row in evidence
        ),
    }
    ready = all(checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "source_scope": {
            "levels": list(levels),
            "page_unit_count": len(evidence),
            "book_count": len(books),
            "source_files": sorted(
                [dict(row) for row in source_index],
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
            evidence, key=lambda row: row["source_unit_ref"]
        ),
        "aggregate_summary": {
            "source_macro_theme_label_count": len(
                aggregate("source_macro_theme_labels")
            ),
            "source_macro_theme_labels": sorted(
                aggregate("source_macro_theme_labels")
            ),
            "source_subtheme_label_count": len(
                aggregate("source_subtheme_labels")
            ),
            "source_subtheme_labels": sorted(
                aggregate("source_subtheme_labels")
            ),
            "situation_family_count": len(aggregate("situation_families")),
            "micro_situation_count": len(aggregate("micro_situations")),
            "communicative_function_count": len(
                aggregate("communicative_functions")
            ),
            "participant_role_count": len(aggregate("participant_roles")),
            "interaction_goal_count": len(aggregate("interaction_goals")),
            "matched_vocabulary_ref_count": len(
                aggregate("matched_vocabulary_refs")
            ),
            "matched_chunk_ref_count": len(aggregate("matched_chunk_refs")),
            "matched_pattern_ref_count": len(aggregate("matched_pattern_refs")),
            "matched_grammar_unit_ref_count": len(
                aggregate("matched_grammar_unit_refs")
            ),
            "semantic_duplicate_group_count": len(
                {row["semantic_duplicate_group_id"] for row in evidence}
            ),
            "passage_seed_count": sum(
                row["passage_seed_status"] == "SUPPORTED" for row in evidence
            ),
            "direct_image_evidence_count": 0,
        },
        "extraction_gate": {
            "source_checks": checks,
            "decision": (
                "DERIVED_MATERIAL_READY_FOR_LOCAL_VALIDATION"
                if ready
                else "BLOCKED_DERIVED_SOURCE_OR_ACCOUNTING"
            ),
            "ready_for_governance_binding": False,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": "RAZ-AW_DerivedMaterialExtractionLocalReplayValidation",
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
            errors.extend(
                scan_forbidden_safe_keys(child, f"{pointer}[{index}]")
            )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        page_units, source_index, metadata = load_source(args.source_root)
        package = build_package(
            page_units,
            source_index,
            metadata,
            deep.load_authorities(),
            deep.load_manifest_grammar_tags(args.manifest),
        )
        leakage = scan_forbidden_safe_keys(package)
        if leakage:
            raise MinimalExtractionError(
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
        MinimalExtractionError,
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
