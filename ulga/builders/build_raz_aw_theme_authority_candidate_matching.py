#!/usr/bin/env python3
"""Match verified RAZ A-W source themes to A1/A1+ Theme Authority candidates.

Consumes the text-free output of ``build_raz_aw_derived_material_extraction_minimal``.
It does not reread RAZ source text, write canonical Authority, promote candidates,
or populate Learning Units.

This version keeps three boundaries explicit:

* raw source macro labels are normalized into source-only macro families;
* Authority mappings remain candidate-only and unmapped families remain coverage gaps;
* the source ``subthemes`` field is treated as a mixed source topic-label inventory,
  not as a pedagogical subtheme taxonomy.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_ThemeAuthorityCandidateMatching"
SCHEMA_VERSION = "raz.aw.theme_authority_candidate_matching.v2"
PASS_STATUS = "PASS_RAZ_AW_THEME_AUTHORITY_CANDIDATE_MATCHING"
EXPECTED_PAGE_UNIT_COUNT = 22632
EXPECTED_BOOK_COUNT = 1959
DEFAULT_INPUT = (
    REPO_ROOT
    / ".local/raz_aw/derived_material_extraction_minimal/"
    / "derived_material_extraction_minimal.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/theme_authority_candidate_matching/"
    / "theme_authority_candidate_matching.safe.json"
)

SOURCE_MACRO_THEME_ALIASES = {
    "personal": "theme:a1_personal_information_and_greetings",
    "daily routine": "theme:a1_daily_life_and_routines",
    "dailyroutine": "theme:a1_daily_life_and_routines",
    "actions": "theme:a1_daily_life_and_routines",
    "actions and movement": "theme:a1_daily_life_and_routines",
    "school": "theme:a1_school_and_classroom",
    "home": "theme:a1_homes_and_neighborhoods",
    "community": "theme:a1_homes_and_neighborhoods",
    "shopping": "theme:a1_shopping_and_basic_transactions",
    "money": "theme:a1_shopping_and_basic_transactions",
    "money and finance": "theme:a1_shopping_and_basic_transactions",
    "clothing": "theme:a1_shopping_and_basic_transactions",
    "food": "theme:a1_food_and_dining",
    "hobbies": "theme:a1_interests_and_abilities",
    "sports": "theme:a1_interests_and_abilities",
    "transportation": "theme:a1_travel_and_weather",
    "travel": "theme:a1_travel_and_weather",
    "weather": "theme:a1_travel_and_weather",
    "weather and seasons": "theme:a1_travel_and_weather",
    "health": "theme:a1_health_and_medical",
    "body": "theme:a1_health_and_medical",
    "body and senses": "theme:a1_health_and_medical",
}

# Closed normalization for the 44 source macro labels proven by the corrected
# local replay. A future unseen label fails closed instead of silently creating
# a new pseudo-taxonomy.
SOURCE_MACRO_THEME_FAMILIES = {
    "actions": "actions_and_movement",
    "actions and movement": "actions_and_movement",
    "animal nonfiction": "animals_and_habitats",
    "animals": "animals_and_habitats",
    "body": "body_and_senses",
    "body and senses": "body_and_senses",
    "clothing": "clothing",
    "community": "community",
    "culture and holiday traditions": "holidays_and_culture",
    "daily routine": "daily_routines",
    "dailyroutine": "daily_routines",
    "fairy tale": "fairy_tales_and_folktales",
    "fantasy and monster story": "fantasy_fable_and_moral_stories",
    "feelings": "feelings_character_and_social_emotional",
    "feelings and character": "feelings_character_and_social_emotional",
    "folktale and fairy tale": "fairy_tales_and_folktales",
    "food": "food",
    "health": "health",
    "history and civics": "history_and_civics",
    "hobbies": "hobbies",
    "holidays": "holidays_and_culture",
    "holidays and events": "holidays_and_culture",
    "home": "home",
    "math": "math_and_concepts",
    "math and concepts": "math_and_concepts",
    "math and geometry": "math_and_concepts",
    "math and numbers": "math_and_concepts",
    "money": "money_and_finance",
    "money and finance": "money_and_finance",
    "nature": "nature_and_environment",
    "personal": "personal_information",
    "pets": "pets_and_animal_care",
    "pets and animal care": "pets_and_animal_care",
    "school": "school_and_classroom",
    "science": "science_and_nature_nonfiction",
    "science and nature nonfiction": "science_and_nature_nonfiction",
    "shopping": "shopping",
    "social and emotional learning": "feelings_character_and_social_emotional",
    "sports": "sports",
    "storyfable": "fantasy_fable_and_moral_stories",
    "transportation": "transportation",
    "travel": "travel",
    "weather": "weather_and_seasons",
    "weather and seasons": "weather_and_seasons",
}

FORBIDDEN_SAFE_KEYS = set(material.FORBIDDEN_SAFE_KEYS)
CLAIM_BOUNDARIES = {
    "material_package_read_performed": True,
    "raz_source_text_read_performed": False,
    "review_read_performed": False,
    "bridge_read_performed": False,
    "linkage_read_performed": False,
    "theme_authority_read_performed": True,
    "vocabulary_authority_read_performed": True,
    "theme_aliases_are_candidate_only": True,
    "source_macro_families_are_normalized_source_evidence_not_authority": True,
    "source_subthemes_are_mixed_topic_labels_not_pedagogical_taxonomy": True,
    "unverified_source_topic_labels_are_not_rejected": True,
    "human_semantic_review_performed": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learning_unit_population_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_opened": False,
}


class ThemeAuthorityCandidateMatchingError(ValueError):
    """Fail-closed input, Authority, identity, or accounting error."""


def _normal_label(value: str) -> str:
    return deep.normalize(value.replace("_", " ").replace("-", " "))


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


def verify_material_package(
    package: Mapping[str, Any],
    *,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
) -> list[Mapping[str, Any]]:
    if package.get("task_id") != material.TASK_ID:
        raise ThemeAuthorityCandidateMatchingError("material_task_id_mismatch")
    if package.get("validation_status") != material.PASS_STATUS:
        raise ThemeAuthorityCandidateMatchingError("material_validation_status_not_pass")
    if package.get("errors") != []:
        raise ThemeAuthorityCandidateMatchingError("material_errors_not_empty")

    claimed_hash = package.get("package_sha256")
    if not isinstance(claimed_hash, str) or len(claimed_hash) != 64:
        raise ThemeAuthorityCandidateMatchingError("material_package_sha256_invalid")
    reconstructed = dict(package)
    reconstructed.pop("package_sha256", None)
    if deep.sha256_value(reconstructed) != claimed_hash:
        raise ThemeAuthorityCandidateMatchingError("material_package_sha256_mismatch")

    source_scope = package.get("source_scope")
    if not isinstance(source_scope, Mapping):
        raise ThemeAuthorityCandidateMatchingError("material_source_scope_missing")
    if source_scope.get("page_unit_count") != expected_page_unit_count:
        raise ThemeAuthorityCandidateMatchingError("material_page_unit_count_mismatch")
    if source_scope.get("book_count") != expected_book_count:
        raise ThemeAuthorityCandidateMatchingError("material_book_count_mismatch")

    rows = package.get("page_unit_evidence")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ThemeAuthorityCandidateMatchingError("material_page_unit_evidence_invalid")
    if len(rows) != expected_page_unit_count:
        raise ThemeAuthorityCandidateMatchingError(
            "material_page_unit_evidence_count_mismatch"
        )

    refs = [str(row.get("source_unit_ref") or "") for row in rows]
    if any(not ref for ref in refs) or len(set(refs)) != len(refs):
        raise ThemeAuthorityCandidateMatchingError(
            "material_source_unit_ref_invalid_or_duplicate"
        )
    leakage = scan_forbidden_safe_keys(package)
    if leakage:
        raise ThemeAuthorityCandidateMatchingError(
            "material_safe_output_leakage:" + ";".join(leakage[:20])
        )
    return rows


def _candidate_theme_refs(
    labels: set[str],
    authority_ids: set[str],
) -> tuple[set[str], set[str]]:
    refs: set[str] = set()
    unmapped: set[str] = set()
    for label in labels:
        target = SOURCE_MACRO_THEME_ALIASES.get(_normal_label(label))
        if target is None:
            unmapped.add(label)
            continue
        if target not in authority_ids:
            raise ThemeAuthorityCandidateMatchingError(
                f"theme_alias_target_missing_from_authority:{label}:{target}"
            )
        refs.add(target)
    return refs, unmapped


def _source_macro_family(label: str) -> str:
    normalized = _normal_label(label)
    family = SOURCE_MACRO_THEME_FAMILIES.get(normalized)
    if family is None:
        raise ThemeAuthorityCandidateMatchingError(
            f"source_macro_family_missing:{label}:{normalized}"
        )
    return family


def _vocabulary_index(
    authority: Mapping[str, Any],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    singles: dict[str, set[str]] = defaultdict(set)
    phrases: dict[str, set[str]] = defaultdict(set)
    rows = authority.get("rows")
    if not isinstance(rows, list):
        raise ThemeAuthorityCandidateMatchingError("vocabulary_authority_rows_missing")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        identifier = row.get("id")
        normalized = row.get("normalized")
        if not isinstance(identifier, str) or not identifier:
            continue
        if not isinstance(normalized, str) or not normalized:
            continue
        if " " in normalized:
            phrases[normalized].add(identifier)
        else:
            singles[normalized].add(identifier)
    return singles, phrases


def _source_topic_vocabulary_refs(
    label: str,
    singles: Mapping[str, set[str]],
    phrases: Mapping[str, set[str]],
) -> set[str]:
    normalized = _normal_label(label)
    if not normalized:
        return set()
    if " " in normalized:
        return set(phrases.get(normalized, set()))
    refs: set[str] = set()
    for candidate in deep.morphology_candidates(normalized):
        refs.update(singles.get(candidate, set()))
    return refs


def _source_topic_label_type(label: str, vocabulary_refs: set[str]) -> str:
    normalized = _normal_label(label)
    if "_" in label or "-" in label or len(normalized.split()) > 1:
        return "COMPOUND_OR_MULTIWORD_TOPIC_TAG"
    if vocabulary_refs:
        return "A1_VOCABULARY_BACKED_SINGLE_TOKEN"
    if normalized.endswith(("ing", "ed")) and len(normalized) > 4:
        return "UNVERIFIED_INFLECTED_SINGLE_TOKEN"
    if normalized.endswith("s") and len(normalized) > 3:
        return "UNVERIFIED_PLURAL_OR_THIRD_PERSON_SINGLE_TOKEN"
    return "UNVERIFIED_SINGLE_TOKEN"


def build_package(
    material_package: Mapping[str, Any],
    authorities: Mapping[str, Any],
    *,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
) -> dict[str, Any]:
    rows = verify_material_package(
        material_package,
        expected_page_unit_count=expected_page_unit_count,
        expected_book_count=expected_book_count,
    )
    themes = authorities.get("themes")
    vocabulary = authorities.get("vocabulary")
    if not isinstance(themes, Mapping) or not isinstance(vocabulary, Mapping):
        raise ThemeAuthorityCandidateMatchingError("required_authority_missing")
    authority_ids = themes.get("ids")
    if not isinstance(authority_ids, set):
        authority_ids = {
            str(row.get("id"))
            for row in themes.get("rows", [])
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        }
    singles, phrases = _vocabulary_index(vocabulary)

    candidate_rows: list[dict[str, Any]] = []
    per_level_state: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "macro": set(),
            "macro_families": set(),
            "mapped_macro": set(),
            "unmapped_macro": set(),
            "theme_refs": set(),
            "subthemes": set(),
            "backed_topic_labels": set(),
            "unverified_topic_labels": set(),
            "topic_vocab_refs": set(),
            "topic_label_types": {},
        }
    )
    family_source_labels: dict[str, set[str]] = defaultdict(set)
    family_theme_refs: dict[str, set[str]] = defaultdict(set)
    global_topic_label_types: dict[str, str] = {}

    all_books: set[tuple[str, str]] = set()
    for row in rows:
        ref = str(row.get("source_unit_ref") or "")
        level = str(row.get("source_level") or "")
        book_id = str(row.get("source_book_id") or "")
        if not level or not book_id:
            raise ThemeAuthorityCandidateMatchingError(
                f"material_identity_incomplete:{ref}"
            )
        macro_labels = {
            str(value)
            for value in row.get("source_macro_theme_labels", [])
            if isinstance(value, str) and value
        }
        subtheme_labels = {
            str(value)
            for value in row.get("source_subtheme_labels", [])
            if isinstance(value, str) and value
        }
        theme_refs, unmapped_macro = _candidate_theme_refs(
            macro_labels, authority_ids
        )
        mapped_macro = macro_labels - unmapped_macro
        macro_families = {_source_macro_family(label) for label in macro_labels}

        for label in macro_labels:
            family = _source_macro_family(label)
            family_source_labels[family].add(label)
            target = SOURCE_MACRO_THEME_ALIASES.get(_normal_label(label))
            if target is not None:
                family_theme_refs[family].add(target)

        topic_classifications: list[dict[str, Any]] = []
        backed_topic_labels: set[str] = set()
        unverified_topic_labels: set[str] = set()
        topic_vocab_refs: set[str] = set()
        local_topic_types: dict[str, str] = {}
        for label in sorted(subtheme_labels):
            refs = _source_topic_vocabulary_refs(label, singles, phrases)
            label_type = _source_topic_label_type(label, refs)
            quality_status = (
                "A1_VOCABULARY_BACKED"
                if refs
                else "UNVERIFIED_SOURCE_TOPIC_LABEL"
            )
            if refs:
                backed_topic_labels.add(label)
                topic_vocab_refs.update(refs)
            else:
                unverified_topic_labels.add(label)
            previous = global_topic_label_types.get(label)
            if previous is not None and previous != label_type:
                raise ThemeAuthorityCandidateMatchingError(
                    f"source_topic_label_type_conflict:{label}:{previous}:{label_type}"
                )
            global_topic_label_types[label] = label_type
            local_topic_types[label] = label_type
            topic_classifications.append(
                {
                    "source_subtheme_label": label,
                    "source_topic_label_type": label_type,
                    "matched_vocabulary_refs": sorted(refs),
                    "quality_status": quality_status,
                }
            )

        state = per_level_state[level]
        state["macro"].update(macro_labels)
        state["macro_families"].update(macro_families)
        state["mapped_macro"].update(mapped_macro)
        state["unmapped_macro"].update(unmapped_macro)
        state["theme_refs"].update(theme_refs)
        state["subthemes"].update(subtheme_labels)
        state["backed_topic_labels"].update(backed_topic_labels)
        state["unverified_topic_labels"].update(unverified_topic_labels)
        state["topic_vocab_refs"].update(topic_vocab_refs)
        state["topic_label_types"].update(local_topic_types)
        all_books.add((level, book_id))

        candidate_rows.append(
            {
                "source_unit_ref": ref,
                "source_level": level,
                "source_book_id": book_id,
                "source_macro_theme_labels": sorted(macro_labels),
                "source_macro_theme_family_ids": sorted(macro_families),
                "candidate_theme_authority_refs": sorted(theme_refs),
                "unmapped_source_macro_theme_labels": sorted(unmapped_macro),
                "source_subtheme_labels": sorted(subtheme_labels),
                "source_topic_label_classifications": topic_classifications,
                "authority_status": "candidate_only",
                "review_status": "pending",
                "promotion_status": "promotion_blocked",
            }
        )

    per_level_summary: list[dict[str, Any]] = []
    for level in sorted(per_level_state):
        state = per_level_state[level]
        type_counts = Counter(state["topic_label_types"].values())
        per_level_summary.append(
            {
                "level": level,
                "source_macro_theme_labels": sorted(state["macro"]),
                "source_macro_theme_family_ids": sorted(state["macro_families"]),
                "mapped_source_macro_theme_labels": sorted(
                    state["mapped_macro"]
                ),
                "unmapped_source_macro_theme_labels": sorted(
                    state["unmapped_macro"]
                ),
                "candidate_theme_authority_refs": sorted(state["theme_refs"]),
                "source_subtheme_labels": sorted(state["subthemes"]),
                "a1_vocabulary_backed_source_topic_labels": sorted(
                    state["backed_topic_labels"]
                ),
                "unverified_source_topic_labels": sorted(
                    state["unverified_topic_labels"]
                ),
                "matched_source_topic_vocabulary_refs": sorted(
                    state["topic_vocab_refs"]
                ),
                "source_topic_label_type_counts": dict(sorted(type_counts.items())),
            }
        )

    def aggregate(key: str) -> set[str]:
        return {value for row in per_level_summary for value in row[key]}

    input_summary = material_package.get("aggregate_summary")
    if not isinstance(input_summary, Mapping):
        raise ThemeAuthorityCandidateMatchingError(
            "material_aggregate_summary_missing"
        )
    input_macro = set(input_summary.get("source_macro_theme_labels", []))
    input_subthemes = set(input_summary.get("source_subtheme_labels", []))
    observed_macro = aggregate("source_macro_theme_labels")
    observed_subthemes = aggregate("source_subtheme_labels")
    observed_families = aggregate("source_macro_theme_family_ids")
    mapped_macro = aggregate("mapped_source_macro_theme_labels")
    unmapped_macro = aggregate("unmapped_source_macro_theme_labels")
    theme_refs = aggregate("candidate_theme_authority_refs")
    backed_topic_labels = aggregate(
        "a1_vocabulary_backed_source_topic_labels"
    )
    unverified_topic_labels = aggregate("unverified_source_topic_labels")
    topic_vocab_refs = aggregate("matched_source_topic_vocabulary_refs")

    family_rows: list[dict[str, Any]] = []
    for family in sorted(observed_families):
        refs = family_theme_refs.get(family, set())
        family_rows.append(
            {
                "source_macro_theme_family_id": family,
                "source_macro_theme_labels": sorted(
                    family_source_labels.get(family, set())
                ),
                "candidate_theme_authority_refs": sorted(refs),
                "coverage_status": (
                    "AUTHORITY_CANDIDATE_MAPPED"
                    if refs
                    else "AUTHORITY_GAP_CANDIDATE"
                ),
                "authority_status": "candidate_only",
                "review_status": "pending",
                "promotion_status": "promotion_blocked",
            }
        )

    mapped_family_ids = {
        row["source_macro_theme_family_id"]
        for row in family_rows
        if row["coverage_status"] == "AUTHORITY_CANDIDATE_MAPPED"
    }
    gap_family_ids = {
        row["source_macro_theme_family_id"]
        for row in family_rows
        if row["coverage_status"] == "AUTHORITY_GAP_CANDIDATE"
    }
    source_topic_labels_by_type: dict[str, list[str]] = defaultdict(list)
    for label, label_type in sorted(global_topic_label_types.items()):
        source_topic_labels_by_type[label_type].append(label)
    topic_type_counts = Counter(global_topic_label_types.values())

    checks = {
        "page_unit_count_exact": len(candidate_rows) == expected_page_unit_count,
        "book_count_exact": len(all_books) == expected_book_count,
        "source_macro_theme_reconciled": observed_macro == input_macro,
        "source_subtheme_reconciled": observed_subthemes == input_subthemes,
        "all_macro_labels_classified": mapped_macro | unmapped_macro
        == observed_macro,
        "macro_classifications_disjoint": mapped_macro.isdisjoint(
            unmapped_macro
        ),
        "all_macro_labels_assigned_to_source_family": (
            set().union(*family_source_labels.values())
            if family_source_labels
            else set()
        )
        == observed_macro,
        "source_macro_family_classifications_disjoint": (
            mapped_family_ids.isdisjoint(gap_family_ids)
        ),
        "all_source_macro_families_classified": (
            mapped_family_ids | gap_family_ids
        )
        == observed_families,
        "all_source_topic_labels_quality_classified": (
            backed_topic_labels | unverified_topic_labels
        )
        == observed_subthemes,
        "source_topic_quality_classifications_disjoint": (
            backed_topic_labels.isdisjoint(unverified_topic_labels)
        ),
        "all_source_topic_labels_type_classified": set(
            global_topic_label_types
        )
        == observed_subthemes,
        "candidate_theme_refs_exist_in_authority": theme_refs <= authority_ids,
        "family_candidate_theme_refs_exist_in_authority": all(
            set(row["candidate_theme_authority_refs"]) <= authority_ids
            for row in family_rows
        ),
        "candidate_boundaries_preserved": all(
            row["authority_status"] == "candidate_only"
            and row["review_status"] == "pending"
            and row["promotion_status"] == "promotion_blocked"
            for row in candidate_rows + family_rows
        ),
    }
    ready = all(checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_material_identity": {
            "task_id": material_package["task_id"],
            "package_sha256": material_package["package_sha256"],
            "page_unit_count": expected_page_unit_count,
            "book_count": expected_book_count,
        },
        "authority_baselines": {
            "themes": {
                "count": themes.get("count"),
                "source_path": themes.get("source_path"),
                "source_sha256": themes.get("source_sha256"),
            },
            "vocabulary": {
                "count": vocabulary.get("count"),
                "source_path": vocabulary.get("source_path"),
                "source_sha256": vocabulary.get("source_sha256"),
            },
        },
        "source_macro_theme_family_candidates": family_rows,
        "source_topic_label_classification": {
            "source_topic_label_count": len(observed_subthemes),
            "source_topic_label_type_counts": dict(
                sorted(topic_type_counts.items())
            ),
            "source_topic_labels_by_type": {
                key: values
                for key, values in sorted(source_topic_labels_by_type.items())
            },
            "a1_vocabulary_backed_source_topic_labels": sorted(
                backed_topic_labels
            ),
            "unverified_source_topic_labels": sorted(
                unverified_topic_labels
            ),
        },
        "per_level_summary": per_level_summary,
        "theme_subtheme_candidates": sorted(
            candidate_rows, key=lambda row: row["source_unit_ref"]
        ),
        "aggregate_summary": {
            "source_macro_theme_label_count": len(observed_macro),
            "source_macro_theme_family_count": len(observed_families),
            "mapped_source_macro_theme_label_count": len(mapped_macro),
            "unmapped_source_macro_theme_label_count": len(unmapped_macro),
            "authority_mapped_source_macro_theme_family_count": len(
                mapped_family_ids
            ),
            "authority_gap_source_macro_theme_family_count": len(
                gap_family_ids
            ),
            "authority_gap_source_macro_theme_family_ids": sorted(
                gap_family_ids
            ),
            "candidate_theme_authority_ref_count": len(theme_refs),
            "candidate_theme_authority_refs": sorted(theme_refs),
            "source_subtheme_label_count": len(observed_subthemes),
            "a1_vocabulary_backed_source_topic_label_count": len(
                backed_topic_labels
            ),
            "unverified_source_topic_label_count": len(
                unverified_topic_labels
            ),
            "matched_source_topic_vocabulary_ref_count": len(
                topic_vocab_refs
            ),
            "source_topic_label_type_counts": dict(
                sorted(topic_type_counts.items())
            ),
        },
        "matching_gate": {
            "source_checks": checks,
            "decision": (
                "THEME_AUTHORITY_CANDIDATES_READY_FOR_LOCAL_VALIDATION"
                if ready
                else "BLOCKED_THEME_AUTHORITY_CANDIDATE_MATCHING"
            ),
            "ready_for_governance_binding": False,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": (
                "RAZ-AW_ThemeAuthorityCoverageGapAndSourceTopicReview"
            ),
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback_summary(package: Mapping[str, Any]) -> dict[str, Any]:
    aggregate = package["aggregate_summary"]
    return {
        "task_id": TASK_ID,
        "decision": package["matching_gate"]["decision"],
        "source_macro_theme_label_count": aggregate[
            "source_macro_theme_label_count"
        ],
        "source_macro_theme_family_count": aggregate[
            "source_macro_theme_family_count"
        ],
        "mapped_source_macro_theme_label_count": aggregate[
            "mapped_source_macro_theme_label_count"
        ],
        "unmapped_source_macro_theme_label_count": aggregate[
            "unmapped_source_macro_theme_label_count"
        ],
        "authority_mapped_source_macro_theme_family_count": aggregate[
            "authority_mapped_source_macro_theme_family_count"
        ],
        "authority_gap_source_macro_theme_family_count": aggregate[
            "authority_gap_source_macro_theme_family_count"
        ],
        "authority_gap_source_macro_theme_family_ids": aggregate[
            "authority_gap_source_macro_theme_family_ids"
        ],
        "candidate_theme_authority_ref_count": aggregate[
            "candidate_theme_authority_ref_count"
        ],
        "source_subtheme_label_count": aggregate["source_subtheme_label_count"],
        "a1_vocabulary_backed_source_topic_label_count": aggregate[
            "a1_vocabulary_backed_source_topic_label_count"
        ],
        "unverified_source_topic_label_count": aggregate[
            "unverified_source_topic_label_count"
        ],
        "matched_source_topic_vocabulary_ref_count": aggregate[
            "matched_source_topic_vocabulary_ref_count"
        ],
        "source_topic_label_type_counts": aggregate[
            "source_topic_label_type_counts"
        ],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-package", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        material_package = deep.read_json(args.material_package)
        if not isinstance(material_package, Mapping):
            raise ThemeAuthorityCandidateMatchingError(
                "material_package_not_object"
            )
        package = build_package(material_package, deep.load_authorities())
        leakage = scan_forbidden_safe_keys(package)
        if leakage:
            raise ThemeAuthorityCandidateMatchingError(
                "safe_output_leakage:" + ";".join(leakage[:20])
            )
        deep.write_json_atomic(args.output, package)
        print(json.dumps(_readback_summary(package), sort_keys=True))
        return 0
    except (
        ThemeAuthorityCandidateMatchingError,
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
