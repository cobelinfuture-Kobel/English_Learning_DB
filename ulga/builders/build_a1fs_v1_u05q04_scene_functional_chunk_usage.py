#!/usr/bin/env python3
"""Extract scene-attested Unit05 present-be functional-language candidates.

This builder does not author learner-facing English. It extracts already
approved Current360 passage language and Spoken360 dialogue language, records
scene/episode usage, and preserves the Q04 exact-chunk denominator separately.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
READER = ROOT / "product" / "a1fs_v1_2_1" / "u04reader360_spoken_dialogue_reader_partial.json"
Q04 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q04_be_chunk_authority.json"

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only extraction of already-authored Current360/Spoken360 language; "
    "creates no new learner-facing English or canonical chunk identity."
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
COORD_SPLIT_RE = re.compile(r",\s+(?:and|but|so|while)\s+", re.I)
DISCOURSE_PREFIX_RE = re.compile(r"^(?:yes|no|okay|ok|good|great)\s*,?\s*", re.I)
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
BE_RE = re.compile(
    r"\b(?:am|is|are)\b|\b(?:i'm|you're|he's|she's|it's|we're|they're)\b|"
    r"\b(?:isn't|aren't)\b",
    re.I,
)
NEG_RE = re.compile(
    r"\b(?:am not|is not|are not|isn't|aren't)\b|"
    r"\b(?:i'm|you're|he's|she's|it's|we're|they're)\s+not\b",
    re.I,
)
AUX_RE = re.compile(
    r"\b(?:am|is|are)\s+[a-z]+ing\b|"
    r"\b(?:i'm|you're|he's|she's|it's|we're|they're)\s+[a-z]+ing\b",
    re.I,
)
THERE_RE = re.compile(r"\bthere\s+(?:is|are|'s)\b", re.I)
FROM_RE = re.compile(
    r"\b(?:am|is|are)\s+from\b|"
    r"\b(?:i'm|you're|he's|she's|it's|we're|they're)\s+from\b",
    re.I,
)
QUESTION_START_RE = re.compile(r"^(?:where|what|who|when|why|how|is|are|am)\b", re.I)
PLACE_RE = re.compile(
    r"\b(?:am|is|are)\s+(?:in|inside|on|near|at|under|behind|between)\b|"
    r"\b(?:i'm|you're|he's|she's|it's|we're|they're)\s+"
    r"(?:in|inside|on|near|at|under|behind|between)\b",
    re.I,
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: str) -> str:
    value = str(value).replace("’", "'").lower()
    value = re.sub(r"[.!]+$", "", value)
    return " ".join(value.split())


def clauses(text: str) -> list[str]:
    output: list[str] = []
    for sentence in SENTENCE_SPLIT_RE.split(str(text or "")):
        for clause in COORD_SPLIT_RE.split(sentence):
            clause = DISCOURSE_PREFIX_RE.sub("", clause).strip()
            if clause:
                output.append(clause)
    return output


def classify(clause: str) -> str:
    value = normalize(clause)
    if NEG_RE.search(value):
        return "NEGATIVE_BE_FUNCTIONAL"
    if PLACE_RE.search(value):
        return "STATIC_PLACE_FUNCTIONAL"
    return "COPULAR_COMPLEMENT_FUNCTIONAL"


def eligible(clause: str) -> bool:
    value = clause.strip()
    words = WORD_RE.findall(value)
    if value.endswith("?") or QUESTION_START_RE.search(value):
        return False
    if len(words) < 2 or len(words) > 12:
        return False
    if not BE_RE.search(value):
        return False
    if AUX_RE.search(value) or THERE_RE.search(value) or FROM_RE.search(value):
        return False
    return True


def extract_occurrences(reader: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in reader["entries"]:
        sources = [
            ("CURRENT360_PASSAGE", [entry.get("passage", "")]),
            (
                "SPOKEN360_DIALOGUE",
                [turn.get("text", "") for turn in entry.get("dialogue_turns", [])],
            ),
        ]
        for layer, texts in sources:
            for text in texts:
                for clause in clauses(text):
                    if not eligible(clause):
                        continue
                    rows.append(
                        {
                            "layer": layer,
                            "episode": entry["source_episode_id"],
                            "scene": entry["micro_scene_id"],
                            "domain": entry["life_domain"],
                            "family": entry.get("governed_scene_family"),
                            "text": re.sub(r"[.!]+$", "", clause),
                            "class": classify(clause),
                        }
                    )
    return rows


def _contains_surface(text: str, surface: str) -> bool:
    return f" {normalize(surface)} " in f" {normalize(text)} "


def build_usage_ledger() -> dict[str, Any]:
    reader = _load(READER)
    q04 = _load(Q04)
    occurrences = extract_occurrences(reader)

    grouped: dict[str, dict[str, Any]] = {}
    for row in occurrences:
        key = normalize(row["text"])
        item = grouped.setdefault(
            key,
            {
                "surface": row["text"],
                "class": row["class"],
                "occ": 0,
                "current": 0,
                "spoken": 0,
                "scenes": set(),
                "episodes": set(),
                "domains": set(),
                "families": set(),
            },
        )
        item["occ"] += 1
        if row["layer"] == "CURRENT360_PASSAGE":
            item["current"] += 1
        else:
            item["spoken"] += 1
        item["scenes"].add(row["scene"])
        item["episodes"].add(row["episode"])
        item["domains"].add(row["domain"])
        if row["family"]:
            item["families"].add(row["family"])

    candidates: list[dict[str, Any]] = []
    for index, key in enumerate(sorted(grouped), start=1):
        item = grouped[key]
        both_layers = item["current"] > 0 and item["spoken"] > 0
        if item["occ"] >= 5 and (len(item["scenes"]) >= 2 or both_layers):
            utility = "HIGH_UTILITY"
        elif item["occ"] >= 2:
            utility = "REPEATED"
        else:
            utility = "SINGLE_ATTESTATION"
        candidates.append(
            {
                "functional_chunk_id": f"U05-FC-{index:04d}",
                "normalized_surface": key,
                "exemplar_surface": item["surface"],
                "functional_class": item["class"],
                "occurrence_count": item["occ"],
                "current360_occurrence_count": item["current"],
                "spoken360_occurrence_count": item["spoken"],
                "episode_count": len(item["episodes"]),
                "scene_count": len(item["scenes"]),
                "domain_count": len(item["domains"]),
                "scene_ids": sorted(item["scenes"]),
                "episode_ids": sorted(item["episodes"]),
                "utility_tier": utility,
                "admission_state": "SCENE_DERIVED_FUNCTIONAL_CANDIDATE_NOT_CANONICAL_CHUNK",
                "q02_lexical_gate_status": "REQUIRED_BEFORE_Q05_Q06_PROMOTION",
                "q03_grammar_gate_status": "PASS_Q03_SURFACE_SHAPE_FILTER",
                "canonical_chunk_claimed": False,
            }
        )

    seed_surfaces = [
        surface
        for group in q04["chunk_groups"]
        for surface in group["surfaces"]
    ]
    seed_usage: list[dict[str, Any]] = []
    for surface in seed_surfaces:
        matches = [row for row in occurrences if _contains_surface(row["text"], surface)]
        seed_usage.append(
            {
                "seed_surface": surface,
                "occurrence_count": len(matches),
                "current360_occurrence_count": sum(
                    row["layer"] == "CURRENT360_PASSAGE" for row in matches
                ),
                "spoken360_occurrence_count": sum(
                    row["layer"] == "SPOKEN360_DIALOGUE" for row in matches
                ),
                "scene_ids": sorted({row["scene"] for row in matches}),
                "episode_ids": sorted({row["episode"] for row in matches}),
                "observed": bool(matches),
            }
        )

    scene_ids = sorted({entry["micro_scene_id"] for entry in reader["entries"]})
    scene_ids_with_candidates = {row["scene"] for row in occurrences}
    unique_by_class = {
        label: sum(row["functional_class"] == label for row in candidates)
        for label in (
            "STATIC_PLACE_FUNCTIONAL",
            "NEGATIVE_BE_FUNCTIONAL",
            "COPULAR_COMPLEMENT_FUNCTIONAL",
        )
    }
    occurrence_by_class = {
        label: sum(row["class"] == label for row in occurrences)
        for label in (
            "STATIC_PLACE_FUNCTIONAL",
            "NEGATIVE_BE_FUNCTIONAL",
            "COPULAR_COMPLEMENT_FUNCTIONAL",
        )
    }

    return {
        "schema_version": "a1fs.v1.u05.q04.scene_functional_chunk_usage.v1",
        "program_id": "A1FS-V1",
        "task_id": "A1FS-V1-U05Q04_Unit05BeChunkAuthorityAndCumulativeDedup",
        "artifact_id": "A1FS-V1-U05Q04_SceneFunctionalChunkUsage",
        "status": "PASS_U05_Q04_SCENE_DERIVED_FUNCTIONAL_CHUNK_EXTRACTION",
        "unit_id": "GRAMMAR_BE_VERB_BASIC",
        "source_reader": {
            "path": str(READER.relative_to(ROOT)).replace("\\", "/"),
            "materialized_entries": len(reader["entries"]),
            "current360_source_role": (
                "The passage field is the preserved Current360 passage carried by "
                "Spoken360 staging."
            ),
            "spoken360_source_role": "dialogue_turns are the Spoken360 dialogue layer.",
            "micro_scene_count": len(scene_ids),
        },
        "extraction_contract": {
            "purpose": (
                "Extract scene-attested, high-retrievability present-be functional-"
                "language candidates without changing the exact Q04 chunk denominator."
            ),
            "source_layers": ["CURRENT360_PASSAGE", "SPOKEN360_DIALOGUE"],
            "max_clause_words": 12,
            "clause_split": "sentence boundary plus comma+and/but/so/while",
            "included_shapes": [
                "present am/is/are copular declaratives",
                "pronoun be contractions",
                "negative be contractions",
                "Q03 static-place relations",
            ],
            "excluded_shapes": [
                "questions",
                "auxiliary be + -ing",
                "there is/are",
                "be + from origin",
                "clauses over 12 words",
            ],
            "candidate_is_not_canonical_chunk": True,
            "frequency_does_not_auto_admit": True,
            "q02_lexical_gate_required_before_q05_q06_promotion": True,
            "q03_grammar_gate_required": True,
        },
        "summary": {
            "reader_episode_count": len(reader["entries"]),
            "micro_scene_count": len(scene_ids),
            "micro_scenes_with_extracted_candidate_count": len(scene_ids_with_candidates),
            "extracted_occurrence_count": len(occurrences),
            "unique_functional_candidate_count": len(candidates),
            "current360_occurrence_count": sum(
                row["layer"] == "CURRENT360_PASSAGE" for row in occurrences
            ),
            "spoken360_occurrence_count": sum(
                row["layer"] == "SPOKEN360_DIALOGUE" for row in occurrences
            ),
            "unique_by_class": unique_by_class,
            "occurrence_by_class": occurrence_by_class,
            "high_utility_candidate_count": sum(
                row["utility_tier"] == "HIGH_UTILITY" for row in candidates
            ),
            "repeated_candidate_count": sum(
                row["utility_tier"] == "REPEATED" for row in candidates
            ),
            "single_attestation_candidate_count": sum(
                row["utility_tier"] == "SINGLE_ATTESTATION" for row in candidates
            ),
            "exact_q04_seed_surface_count": len(seed_surfaces),
            "exact_q04_seed_observed_count": sum(row["observed"] for row in seed_usage),
            "exact_q04_seed_unobserved_count": sum(not row["observed"] for row in seed_usage),
            "candidates_observed_in_both_layers": sum(
                row["current360_occurrence_count"] > 0
                and row["spoken360_occurrence_count"] > 0
                for row in candidates
            ),
        },
        "exact_q04_seed_usage": seed_usage,
        "functional_candidates": candidates,
        "downstream_usage_recording_contract": {
            "required": True,
            "actual_q05_q06_usage_not_yet_materialized": True,
            "required_fields_when_consumed": [
                "functional_chunk_id",
                "target_asset_id",
                "source_episode_id",
                "source_micro_scene_id",
                "source_layer",
                "usage_role",
            ],
            "rule": (
                "Q05/Q06 must record every promoted or consumed scene-derived functional "
                "candidate. Extraction frequency alone is not proof of downstream use."
            ),
        },
        "claim_boundaries": {
            "exact_q04_chunk_surface_denominator_unchanged": True,
            "exact_q04_new_surface_count": 66,
            "cumulative_exact_chunk_surface_count": 156,
            "scene_candidates_added_to_exact_chunk_denominator": 0,
            "learner_facing_sentence_assets_created": 0,
            "present_continuous_mastery_unlocked": False,
            "a2_a2plus_unlocked": False,
        },
    }


def main() -> int:
    report = build_usage_ledger()
    print(f"STATUS={report['status']}")
    for key, value in report["summary"].items():
        if not isinstance(value, dict):
            print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
