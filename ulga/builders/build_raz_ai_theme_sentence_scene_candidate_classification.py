#!/usr/bin/env python3
"""Classify RAZ A-I Theme/Situation, Sentence Seed, and Scene Seed candidates.

The builder reads the private enriched RAZ A-I page-unit corpus and emits one
text-free candidate package. It does not promote Authority, populate Learning
Units, create learner-facing language, generate images, or read RAZ J-W.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_gi_targeted_gap_source_expansion as gi

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI_ThemeSentenceSceneCandidateClassification"
SCHEMA_VERSION = "raz.ai.theme_sentence_scene_candidate_classification.v1"
PASS_STATUS = "PASS_RAZ_AI_THEME_SENTENCE_SCENE_CANDIDATE_CLASSIFICATION"
LEVELS = gi.AF_LEVELS + gi.GI_LEVELS
EXPECTED_RECORD_COUNT = gi.EXPECTED_AF_RECORDS + gi.EXPECTED_GI_RECORDS
EXPECTED_BOOK_COUNT = gi.EXPECTED_AF_BOOKS + gi.EXPECTED_GI_BOOKS
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_MANIFEST = REPO_ROOT / ".local/raz_af/a1_a1plus_reading_source_manifest.json"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_ai/theme_sentence_scene_classification/"
    / "theme_sentence_scene_candidate_classification.safe.json"
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Text-free candidate classification only; no canonical or learner-facing content."
)

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_A_I_ONLY",
    "j_w_read_performed": False,
    "source_text_read_privately": True,
    "source_text_included_in_safe_output": False,
    "source_payload_included_in_safe_output": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learning_unit_content_population_performed": False,
    "learner_facing_core_sentence_created": False,
    "image_generation_performed": False,
    "human_semantic_review_performed": False,
    "classification_status": "DETERMINISTIC_CANDIDATE_REQUIRES_REVIEW",
    "a2_a2plus_in_scope": False,
}

FORBIDDEN_SAFE_KEYS = deep.FORBIDDEN_SAFE_KEYS | {
    "clean_text",
    "raw_text",
    "source_sentence",
    "original_text",
}

FUNCTION_PRIORITY = (
    "asking_for_information",
    "requesting",
    "giving_reason",
    "sequencing",
    "expressing_inability",
    "expressing_ability",
    "expressing_preference",
    "describing_location",
    "expressing_possession",
    "narrating_past",
    "referring_to_future",
    "counting_or_listing",
    "describing_quality",
    "answering_or_stating_information",
    "stating_or_identifying",
)

SCENE_FORMAT = {
    "OBJECT_IDENTIFICATION": "OBJECT_GRID",
    "PERSON_OR_CHARACTER_DESCRIPTION": "SINGLE_FRAME",
    "ACTION_SCENE": "SINGLE_FRAME",
    "LOCATION_RELATION_SCENE": "SINGLE_FRAME",
    "SOCIAL_INTERACTION_SCENE": "DIALOGUE_FRAME",
    "ROUTINE_SCENE": "MULTI_PANEL_SEQUENCE",
    "SEQUENCE_SCENE": "MULTI_PANEL_SEQUENCE",
    "PROBLEM_ACTION_RESULT_SCENE": "MULTI_PANEL_SEQUENCE",
    "CAUSE_EFFECT_SCENE": "BEFORE_AFTER_PAIR",
    "COMPARISON_SCENE": "BEFORE_AFTER_PAIR",
    "MAP_OR_ROUTE_SCENE": "MAP_OR_DIAGRAM",
    "SCIENTIFIC_OR_INFORMATIONAL_SCENE": "MAP_OR_DIAGRAM",
    "GENERAL_CONTEXT_SCENE": "SINGLE_FRAME",
}

SCENE_USES = {
    "OBJECT_IDENTIFICATION": ["VOCABULARY_NAMING", "READ_AND_MATCH"],
    "PERSON_OR_CHARACTER_DESCRIPTION": ["SPEAK_FROM_PICTURE", "WRITE_A_SENTENCE"],
    "ACTION_SCENE": ["SPEAK_FROM_PICTURE", "WRITE_A_SENTENCE"],
    "LOCATION_RELATION_SCENE": ["LISTEN_AND_LOCATE", "GRAMMAR_CONTRAST"],
    "SOCIAL_INTERACTION_SCENE": ["DIALOGUE_ROLE_PLAY", "SPEAK_FROM_PICTURE"],
    "ROUTINE_SCENE": ["SEQUENCE_RETELLING", "WRITE_A_SENTENCE"],
    "SEQUENCE_SCENE": ["SEQUENCE_RETELLING", "READ_AND_MATCH"],
    "PROBLEM_ACTION_RESULT_SCENE": ["SEQUENCE_RETELLING", "TRANSFER_ASSESSMENT"],
    "CAUSE_EFFECT_SCENE": ["GRAMMAR_CONTRAST", "TRANSFER_ASSESSMENT"],
    "COMPARISON_SCENE": ["GRAMMAR_CONTRAST", "SPEAK_FROM_PICTURE"],
    "MAP_OR_ROUTE_SCENE": ["LISTEN_AND_LOCATE", "READ_AND_MATCH"],
    "SCIENTIFIC_OR_INFORMATIONAL_SCENE": ["READ_AND_MATCH", "SPEAK_FROM_PICTURE"],
    "GENERAL_CONTEXT_SCENE": ["READ_AND_MATCH"],
}


class ClassificationError(ValueError):
    """Fail-closed source, identity, or accounting error."""


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{deep.sha256_value(value)[:16].upper()}"


def canonical_theme_index(authorities: Mapping[str, Any]) -> dict[str, str]:
    return {
        row["normalized"]: row["id"]
        for row in authorities["themes"]["rows"]
        if row.get("normalized")
    }


def source_theme(row: Mapping[str, Any]) -> str:
    tags = row.get("theme_tags") if isinstance(row.get("theme_tags"), Mapping) else {}
    value = tags.get("mapped_theme") or tags.get("primary_theme") or "Unknown"
    return str(value)


def theme_disposition(
    macro: str,
    canonical_theme_id: str | None,
    families: set[str],
) -> str:
    if canonical_theme_id:
        return "CANONICAL_THEME_MATCH"
    if len(families) > 1:
        return "CROSS_THEME_BRIDGE"
    if families and "general_child_friendly_context" not in families:
        return "SITUATION_FAMILY_MATCH"
    if macro == "Unknown":
        return "HUMAN_REVIEW_REQUIRED"
    return "NEW_SITUATION_CANDIDATE"


def primary_function(functions: set[str]) -> str:
    for value in FUNCTION_PRIORITY:
        if value in functions:
            return value
    return sorted(functions)[0] if functions else "stating_or_identifying"


def sentence_maturity(
    grammar_refs: set[str],
    vocabulary_refs: set[str],
    chunk_refs: set[str],
    pattern_refs: set[str],
    known_semantic: bool,
    dialogue: bool,
    passage: bool,
) -> str:
    if grammar_refs and vocabulary_refs and (chunk_refs or pattern_refs) and known_semantic:
        return "STRICT_CORE_SENTENCE_SEED"
    if grammar_refs and vocabulary_refs and known_semantic:
        return "BROAD_CORE_SENTENCE_SEED"
    if dialogue:
        return "DIALOGUE_TURN_SEED"
    if passage:
        return "PASSAGE_ONLY_SEED"
    if vocabulary_refs or known_semantic:
        return "SUPPORT_SENTENCE_SEED"
    return "DEFERRED_OR_REJECTED"


def sentence_role(maturity: str) -> str:
    return {
        "STRICT_CORE_SENTENCE_SEED": "MODEL_SENTENCE",
        "BROAD_CORE_SENTENCE_SEED": "GUIDED_PRACTICE_SENTENCE",
        "DIALOGUE_TURN_SEED": "DIALOGUE_TURN",
        "PASSAGE_ONLY_SEED": "PASSAGE_SUPPORT_SENTENCE",
        "SUPPORT_SENTENCE_SEED": "PASSAGE_SUPPORT_SENTENCE",
        "DEFERRED_OR_REJECTED": "DEFERRED",
    }[maturity]


def scene_type(
    row: Mapping[str, Any],
    semantic: Mapping[str, set[str]],
    shape: str,
) -> str:
    words = set(deep.tokens(str(row["text"])))
    families = semantic["situation_families"]
    goals = semantic["interaction_goals"]
    functions = semantic["communicative_functions"]

    if "giving_reason" in functions or "explain_reason" in goals or shape == "cause_effect":
        return "CAUSE_EFFECT_SCENE"
    if shape == "comparison_or_contrast" or "count_or_compare" in goals:
        return "COMPARISON_SCENE"
    if shape == "sequence":
        return "SEQUENCE_SCENE"
    if "story_problem_and_result" in families:
        return "PROBLEM_ACTION_RESULT_SCENE"
    if "transport_and_mobility" in families or "travel_and_places" in families:
        if words & {"map", "road", "street", "station", "route", "left", "right"}:
            return "MAP_OR_ROUTE_SCENE"
    if shape == "dialogue_or_question_answer" or "speaker_listener" in semantic["participant_roles"]:
        return "SOCIAL_INTERACTION_SCENE"
    if "describing_location" in functions or "locate_or_identify" in goals:
        return "LOCATION_RELATION_SCENE"
    if "daily_routines_and_time" in families:
        return "ROUTINE_SCENE"
    if families & {"science_observation", "nature_observation", "animals_and_habitats"}:
        return "SCIENTIFIC_OR_INFORMATIONAL_SCENE"
    if functions & {"describing_quality", "expressing_possession"} and words & {
        "he", "she", "boy", "girl", "man", "woman", "child", "person"
    }:
        return "PERSON_OR_CHARACTER_DESCRIPTION"
    if words & {"run", "walk", "eat", "drink", "play", "read", "write", "jump", "swim", "dance", "sing"}:
        return "ACTION_SCENE"
    if int(row.get("sentence_count") or 0) <= 1 and len(words) <= 12:
        return "OBJECT_IDENTIFICATION"
    return "GENERAL_CONTEXT_SCENE"


def build_package(
    records: Sequence[Mapping[str, Any]],
    file_index: Sequence[Mapping[str, Any]],
    authorities: Mapping[str, Any],
    manifest_tags: Mapping[str, set[str]],
    *,
    expected_record_count: int = EXPECTED_RECORD_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
) -> dict[str, Any]:
    theme_index = canonical_theme_index(authorities)
    theme_acc: dict[tuple[str, str, str], dict[str, Any]] = {}
    sentence_rows = []
    scene_rows = []
    cross_links = []
    seen_refs: set[str] = set()
    books = set()
    level_counts = Counter()
    maturity_counts = Counter()
    scene_type_counts = Counter()
    theme_disposition_counts = Counter()

    for row in records:
        ref = str(row.get("page_unit_id") or "")
        level = str(row.get("level") or "")
        book_id = str(row.get("book_id") or "")
        if not ref or ref in seen_refs:
            raise ClassificationError(f"invalid_or_duplicate_source_ref:{ref}")
        if level not in LEVELS or not book_id:
            raise ClassificationError(f"invalid_source_identity:{ref}")
        if not isinstance(row.get("text"), str) or not row["text"].strip():
            raise ClassificationError(f"source_text_missing:{ref}")
        seen_refs.add(ref)
        books.add((level, book_id))
        level_counts[level] += 1

        text = str(row["text"])
        semantic = deep.semantic_alignment(row)
        macro = source_theme(row)
        canonical_id = theme_index.get(deep.normalize(macro))
        disposition = theme_disposition(
            macro, canonical_id, semantic["situation_families"]
        )
        shape = deep.discourse_shape(row)
        vocabulary_refs = deep.match_vocabulary(text, authorities["vocabulary"])
        chunk_refs = deep.match_template_authority(text, authorities["chunks"])
        pattern_refs = deep.match_template_authority(text, authorities["patterns"])
        grammar_refs = deep.grammar_units(text, manifest_tags.get(ref, set()))
        known_semantic = (
            "general_child_friendly_context"
            not in semantic["situation_families"]
        )
        content = row.get("content_unit_tags") if isinstance(row.get("content_unit_tags"), Mapping) else {}
        dialogue = bool(content.get("has_direct_speech") or shape == "dialogue_or_question_answer")
        passage = int(row.get("sentence_count") or 0) >= 2

        theme_ids = []
        for family in sorted(semantic["situation_families"]):
            micros = sorted(
                micro for micro in semantic["micro_situations"]
                if micro.startswith(f"{family}__")
            ) or [f"{family}__share_or_understand_information"]
            for micro in micros:
                key = (macro, family, micro)
                if key not in theme_acc:
                    candidate_id = stable_id("TSIT", key)
                    theme_acc[key] = {
                        "theme_situation_candidate_id": candidate_id,
                        "source_macro_domain": macro,
                        "canonical_theme_id": canonical_id,
                        "situation_family": family,
                        "micro_situation": micro,
                        "communicative_functions": set(),
                        "participant_roles": set(),
                        "interaction_goals": set(),
                        "source_refs": set(),
                        "source_books": set(),
                        "source_levels": set(),
                        "disposition": disposition,
                    }
                acc = theme_acc[key]
                acc["communicative_functions"].update(semantic["communicative_functions"])
                acc["participant_roles"].update(semantic["participant_roles"])
                acc["interaction_goals"].update(semantic["interaction_goals"])
                acc["source_refs"].add(ref)
                acc["source_books"].add((level, book_id))
                acc["source_levels"].add(level)
                theme_ids.append(acc["theme_situation_candidate_id"])

        function = primary_function(semantic["communicative_functions"])
        maturity = sentence_maturity(
            grammar_refs,
            vocabulary_refs,
            chunk_refs,
            pattern_refs,
            known_semantic,
            dialogue,
            passage,
        )
        duplicate_group_id = stable_id("SDUP", deep.normalize(text))
        sentence_id = stable_id("SSEED", ref)
        sentence_rows.append({
            "sentence_seed_id": sentence_id,
            "source_unit_ref": ref,
            "source_level": level,
            "source_band": "AF" if level in gi.AF_LEVELS else "GI",
            "grammar_unit_candidates": sorted(grammar_refs),
            "vocabulary_refs": sorted(vocabulary_refs),
            "chunk_refs": sorted(chunk_refs),
            "pattern_refs": sorted(pattern_refs),
            "theme_situation_candidate_ids": sorted(set(theme_ids)),
            "primary_communicative_function": function,
            "seed_maturity": maturity,
            "primary_material_role": sentence_role(maturity),
            "semantic_duplicate_group_id": duplicate_group_id,
            "level_suitability_status": "A1_A1PLUS_REVIEW_REQUIRED",
            "promotion_status": "NOT_PROMOTED",
        })
        maturity_counts[maturity] += 1

        scene_kind = scene_type(row, semantic, shape)
        reuse = row.get("reuse_tags") if isinstance(row.get("reuse_tags"), Mapping) else {}
        picture_seed = "picture_prompt_seed" in reuse.get("reusability_tags", [])
        visualizable = picture_seed or known_semantic
        scene_id = stable_id("SCENE", ref)
        scene_group_id = stable_id(
            "SCGRP",
            {
                "type": scene_kind,
                "format": SCENE_FORMAT[scene_kind],
                "families": sorted(semantic["situation_families"]),
                "goals": sorted(semantic["interaction_goals"]),
            },
        )
        scene_rows.append({
            "scene_seed_id": scene_id,
            "source_unit_ref": ref,
            "source_level": level,
            "source_band": "AF" if level in gi.AF_LEVELS else "GI",
            "theme_situation_candidate_ids": sorted(set(theme_ids)),
            "scene_type": scene_kind,
            "presentation_format": SCENE_FORMAT[scene_kind],
            "pedagogical_uses": SCENE_USES[scene_kind],
            "semantic_scene_group_id": scene_group_id,
            "visualizable_status": "SUPPORTED" if visualizable else "REVIEW_REQUIRED",
            "target_visible_status": "CANDIDATE_REVIEW_REQUIRED",
            "answerability_status": "CANDIDATE_REVIEW_REQUIRED",
            "language_leakage_status": "NOT_ASSESSED",
            "scene_consistency_status": "NOT_ASSESSED",
            "age_appropriateness_status": "SOURCE_LEVEL_CANDIDATE",
            "promotion_status": "NOT_PROMOTED",
        })
        scene_type_counts[scene_kind] += 1
        theme_disposition_counts[disposition] += 1

        cross_links.append({
            "source_unit_ref": ref,
            "theme_situation_candidate_ids": sorted(set(theme_ids)),
            "sentence_seed_id": sentence_id,
            "scene_seed_id": scene_id,
        })

    theme_rows = []
    for acc in theme_acc.values():
        theme_rows.append({
            "theme_situation_candidate_id": acc["theme_situation_candidate_id"],
            "source_macro_domain": acc["source_macro_domain"],
            "canonical_theme_id": acc["canonical_theme_id"],
            "situation_family": acc["situation_family"],
            "micro_situation": acc["micro_situation"],
            "communicative_functions": sorted(acc["communicative_functions"]),
            "participant_roles": sorted(acc["participant_roles"]),
            "interaction_goals": sorted(acc["interaction_goals"]),
            "source_ref_count": len(acc["source_refs"]),
            "source_book_count": len(acc["source_books"]),
            "source_levels": sorted(acc["source_levels"]),
            "disposition": acc["disposition"],
            "promotion_status": "NOT_PROMOTED",
        })

    source_checks = {
        "record_count_exact": len(records) == expected_record_count,
        "book_count_exact": len(books) == expected_book_count,
        "levels_exact": set(level_counts) == set(LEVELS),
        "all_records_have_sentence_classification": len(sentence_rows) == len(records),
        "all_records_have_scene_classification": len(scene_rows) == len(records),
        "all_records_have_cross_link": len(cross_links) == len(records),
        "all_records_have_theme_link": all(
            row["theme_situation_candidate_ids"] for row in cross_links
        ),
    }
    classification_ready = all(source_checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "source_scope": {
            "levels": list(LEVELS),
            "record_count": len(records),
            "book_count": len(books),
            "level_counts": {level: level_counts[level] for level in LEVELS},
            "source_files": list(file_index),
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
        "theme_situation_candidates": sorted(
            theme_rows, key=lambda row: row["theme_situation_candidate_id"]
        ),
        "sentence_seed_candidates": sorted(
            sentence_rows, key=lambda row: row["source_unit_ref"]
        ),
        "scene_seed_candidates": sorted(
            scene_rows, key=lambda row: row["source_unit_ref"]
        ),
        "cross_links": sorted(
            cross_links, key=lambda row: row["source_unit_ref"]
        ),
        "classification_summary": {
            "theme_situation_candidate_count": len(theme_rows),
            "sentence_seed_candidate_count": len(sentence_rows),
            "scene_seed_candidate_count": len(scene_rows),
            "cross_link_count": len(cross_links),
            "sentence_maturity_counts": dict(sorted(maturity_counts.items())),
            "scene_type_counts": dict(sorted(scene_type_counts.items())),
            "theme_disposition_counts": dict(sorted(theme_disposition_counts.items())),
            "sentence_duplicate_group_count": len({
                row["semantic_duplicate_group_id"] for row in sentence_rows
            }),
            "scene_semantic_group_count": len({
                row["semantic_scene_group_id"] for row in scene_rows
            }),
        },
        "classification_gate": {
            "source_checks": source_checks,
            "decision": (
                "CLASSIFICATION_READY_FOR_REVIEW"
                if classification_ready
                else "BLOCKED_SOURCE_OR_ACCOUNTING_INTEGRITY"
            ),
            "ready_for_human_review": classification_ready,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": "RAZ-AI_ThemeSentenceSceneCandidateReviewAndDedup",
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def scan_forbidden_safe_keys(value: Any, pointer: str = "$") -> list[str]:
    errors = []
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
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        af_records, af_index = gi.load_levels(args.source_root, gi.AF_LEVELS)
        gi_records, gi_index = gi.load_levels(args.source_root, gi.GI_LEVELS)
        package = build_package(
            [*af_records, *gi_records],
            [*af_index, *gi_index],
            deep.load_authorities(),
            deep.load_manifest_grammar_tags(args.manifest),
        )
        leakage = scan_forbidden_safe_keys(package)
        if leakage:
            raise ClassificationError(
                "safe_output_leakage:" + ";".join(leakage[:10])
            )
        deep.write_json_atomic(args.output, package)
        print(json.dumps({
            "task_id": TASK_ID,
            "decision": package["classification_gate"]["decision"],
            "theme_situation_candidate_count": package["classification_summary"][
                "theme_situation_candidate_count"
            ],
            "sentence_seed_candidate_count": package["classification_summary"][
                "sentence_seed_candidate_count"
            ],
            "scene_seed_candidate_count": package["classification_summary"][
                "scene_seed_candidate_count"
            ],
            "package_sha256": package["package_sha256"],
        }, sort_keys=True))
        return 0
    except (
        ClassificationError,
        gi.TargetedGapError,
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
