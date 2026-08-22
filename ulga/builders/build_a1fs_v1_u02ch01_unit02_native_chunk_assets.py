#!/usr/bin/env python3
"""Build the governed Unit02-native chunk and instructional phrase asset set.

U02CH01 uses Unit01 only as a lexical/semantic baseline.  It materializes
Unit02-native plural phrase assets from the exact U02QB01 plain-s vocabulary
authority, the governed U02QB02 approved item pool, and A1 global chunk
authority.  It never promotes generated phrases into global canonical chunks.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as u02qb02,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02CH01_Unit02NativeChunkAndInstructionalPhraseAdmission"
SCHEMA_VERSION = "a1fs.v1.u02ch01.unit02_native_chunk_assets.v1"
PASS_STATUS = "PASS_A1FS_V1_U02CH01_UNIT02_NATIVE_CHUNK_ASSETS"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-22:U02CH01"
UNIT_ID = u02qb02.UNIT_ID
LEVEL_SCOPE = ["A1"]

REPO_ROOT = Path(__file__).resolve().parents[2]
SAFE_CHUNKS_PATH = REPO_ROOT / "chunk_profile/json/chunks_generator_safe.json"

FAMILY_NUM_PLURAL = "U02-CH-F01-NUMBER-PLURAL-NOUN"
FAMILY_ADJ_PLURAL = "U02-CH-F02-ADJECTIVE-PLURAL-NOUN"
FAMILY_NUM_ADJ_PLURAL = "U02-CH-F03-NUMBER-ADJECTIVE-PLURAL-NOUN"
FAMILY_CANONICAL_DERIVED = "U02-CH-F04-CANONICAL-MULTIWORD-PLURAL-DERIVATIVE"

EXPECTED_UNIT01_PLAIN_S_NOUNS = (
    "apple", "bag", "bed", "book", "cat", "desk", "dog",
    "door", "egg", "park", "room", "tree", "window",
)
EXPECTED_ADJECTIVE_PAIRS = (
    ("blue", "bag"),
    ("new", "book"),
    ("old", "book"),
    ("red", "book"),
    ("small", "bag"),
)
DERIVED_CANONICAL_BASES = (
    ("CD player", "EVP_CHUNK_000003"),
    ("dining room", "EVP_CHUNK_000030"),
    ("living room", "EVP_CHUNK_000075"),
)

EXPECTED_ASSET_COUNT = 26
EXPECTED_UNIT_ADMITTED_PHRASE_COUNT = 23
EXPECTED_DERIVED_UNIT_FORM_COUNT = 3

NEXT_SHORT_STEP = (
    "A1FS-V1-U02CH02_"
    "Unit01Unit02CumulativeChunkCoverageRecheck"
)


class Unit02ChunkBuildError(ValueError):
    """Fail-closed U02CH01 construction error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")


def load_safe_chunks(path: Path = SAFE_CHUNKS_PATH) -> list[dict[str, Any]]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise Unit02ChunkBuildError("SAFE_CHUNK_AUTHORITY_NOT_LIST")
    return [dict(row) for row in value]


def safe_chunks_by_surface() -> dict[str, dict[str, Any]]:
    rows = load_safe_chunks()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        surface = str(row.get("chunk") or "")
        if surface:
            result[surface] = row
    return result


def inventory_by_singular() -> dict[str, dict[str, Any]]:
    return u02qb02.inventory_by_singular()


def governed_qb02_approved_items() -> list[dict[str, Any]]:
    approved = u02qb02.admit_candidate(u02qb02.build_candidate())
    rows = approved["payload"]["approved_items"]
    if len(rows) != u02qb02.EXPECTED_APPROVED:
        raise Unit02ChunkBuildError("U02QB02_APPROVED_COUNT_DRIFT")
    return [dict(row) for row in rows]


def qb_item(
    rows: Sequence[Mapping[str, Any]],
    *,
    family_id: str,
    singular: str,
    adjective: str | None = None,
) -> Mapping[str, Any]:
    matches = []
    for row in rows:
        if row.get("pattern_family_id") != family_id:
            continue
        slots = row.get("lexical_slots", {})
        if slots.get("singular_noun") != singular:
            continue
        if adjective is not None and slots.get("adjective") != adjective:
            continue
        matches.append(row)
    if len(matches) != 1:
        raise Unit02ChunkBuildError(
            f"U02QB02_SOURCE_ITEM_CARDINALITY:{family_id}:{singular}:{adjective}:{len(matches)}"
        )
    return matches[0]


def source_unit01_plain_s_nouns() -> tuple[str, ...]:
    inv = inventory_by_singular()
    active = {
        str(lemma)
        for lemma, _sense, _gloss, _indefinite, _definite, _group
        in u02qb02.u01_contract.ACTIVE_NOUNS
    }
    actual = tuple(sorted(active & set(inv)))
    if actual != EXPECTED_UNIT01_PLAIN_S_NOUNS:
        raise Unit02ChunkBuildError(f"UNIT01_PLAIN_S_BASELINE_DRIFT:{actual}")
    return actual


def source_adjective_pairs() -> tuple[tuple[str, str], ...]:
    inv = inventory_by_singular()
    actual = tuple(
        sorted(
            (str(row["adjective"]), str(row["noun"]))
            for row in u02qb02.direct_adjective_pairs()
            if str(row["noun"]) in inv
        )
    )
    if actual != EXPECTED_ADJECTIVE_PAIRS:
        raise Unit02ChunkBuildError(f"ADJECTIVE_PAIR_BASELINE_DRIFT:{actual}")
    return actual


def semantic_signature(asset: Mapping[str, Any]) -> str:
    return digest(
        {
            "asset_id": asset["asset_id"],
            "surface": asset["surface"],
            "family_id": asset["family_id"],
            "authority_scope": asset["authority_scope"],
            "coverage_state": asset["coverage_state"],
            "lexical_slots": asset["lexical_slots"],
            "target_egp_row_ids": asset["target_egp_row_ids"],
            "target_chunk_ids": asset["target_chunk_ids"],
        }
    )


def finalize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    asset["semantic_signature"] = semantic_signature(asset)
    return asset


def unit_phrase_asset(
    *,
    family_id: str,
    surface: str,
    lexical_slots: Mapping[str, Any],
    target_egp_row_id: str,
    target_evp_sense_ids: Sequence[str],
    source_item_id: str,
    source_reason: str,
) -> dict[str, Any]:
    return finalize_asset(
        {
            "asset_id": f"U02-PHRASE-{slug(family_id)}-{slug(surface)}",
            "unit_id": UNIT_ID,
            "level": "A1",
            "surface": surface,
            "normalized_surface": surface.casefold(),
            "asset_kind": "PROJECT_INSTRUCTIONAL_PHRASE",
            "linguistic_family": "NP_COMPOSITION",
            "family_id": family_id,
            "authority_scope": "UNIT_ADMITTED_PHRASE",
            "coverage_state": "DIRECT_TARGET",
            "grammar_target_ids": ["REGULAR_PLURAL_NOUNS"],
            "unit_pattern_ids": [u02qb02.DIRECT_PATTERN_ID],
            "target_egp_row_ids": [target_egp_row_id],
            "prerequisite_egp_row_ids": (
                [u02qb02.PREREQUISITE_KP009]
                if lexical_slots.get("determiner") == u02qb02.DETERMINER
                else []
            ),
            "target_evp_sense_ids": sorted(set(str(x) for x in target_evp_sense_ids)),
            "target_chunk_ids": [],
            "lexical_slots": dict(lexical_slots),
            "production_allowed": True,
            "direct_assessment_allowed": True,
            "reusable_in_later_units": True,
            "learner_visible_capable": True,
            "global_canonical_created": False,
            "source_refs": [
                {
                    "source_type": "U02QB02_GOVERNED_APPROVED_ITEM",
                    "task_id": u02qb02.TASK_ID,
                    "item_id": source_item_id,
                },
                {
                    "source_type": source_reason,
                    "task_id": u02qb02.u01_contract.TASK_ID,
                },
            ],
            "admission": {
                "status": "AUTO_APPROVED",
                "reason_codes": [
                    "U02_NATIVE_PHRASE_WITH_GOVERNED_LEXICAL_AND_GRAMMAR_AUTHORITY"
                ],
            },
        }
    )


def derived_chunk_asset(
    *,
    base_surface: str,
    parent_chunk_id: str,
    plural_surface: str,
    inventory_row: Mapping[str, Any],
    safe_row: Mapping[str, Any],
    source_item_id: str,
) -> dict[str, Any]:
    usage_class = str(safe_row.get("usage_class") or "")
    linguistic_family = "COMPOUND_NOUN" if usage_class == "compound_noun" else "LEXICAL_MULTIWORD"
    return finalize_asset(
        {
            "asset_id": f"U02-DERIVED-{parent_chunk_id}",
            "unit_id": UNIT_ID,
            "level": "A1",
            "surface": plural_surface,
            "normalized_surface": plural_surface.casefold(),
            "asset_kind": "DERIVED_CANONICAL_CHUNK_FORM",
            "linguistic_family": linguistic_family,
            "family_id": FAMILY_CANONICAL_DERIVED,
            "authority_scope": "DERIVED_UNIT_FORM",
            "coverage_state": "DIRECT_TARGET",
            "grammar_target_ids": ["REGULAR_PLURAL_NOUNS"],
            "unit_pattern_ids": [u02qb02.DIRECT_PATTERN_ID],
            "target_egp_row_ids": [u02qb02.KP014],
            "prerequisite_egp_row_ids": [],
            "target_evp_sense_ids": sorted(
                set(str(x) for x in inventory_row["vocabulary_ids"])
            ),
            "target_chunk_ids": [parent_chunk_id],
            "parent_canonical_chunk_id": parent_chunk_id,
            "parent_canonical_surface": base_surface,
            "lexical_slots": {
                "singular_noun": base_surface,
                "plural_noun": plural_surface,
            },
            "production_allowed": True,
            "direct_assessment_allowed": True,
            "reusable_in_later_units": True,
            "learner_visible_capable": True,
            "global_canonical_created": False,
            "source_refs": [
                {
                    "source_type": "EVP_DERIVED_SAFE_LAYER",
                    "path": str(SAFE_CHUNKS_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "safe_id": safe_row["safe_id"],
                    "canonical_chunk_id": parent_chunk_id,
                },
                {
                    "source_type": "U02QB01_PLAIN_S_ACTIVE_VOCABULARY_INVENTORY",
                    "task_id": "A1FS-V1-U02QB01_ExactPlainSActiveVocabularyInventory",
                    "vocabulary_ids": list(inventory_row["vocabulary_ids"]),
                },
                {
                    "source_type": "U02QB02_GOVERNED_APPROVED_ITEM",
                    "task_id": u02qb02.TASK_ID,
                    "item_id": source_item_id,
                },
            ],
            "admission": {
                "status": "AUTO_APPROVED",
                "reason_codes": [
                    "A1_CANONICAL_MULTIWORD_CHUNK_PLUS_U02_PLAIN_S_MORPHOLOGY"
                ],
            },
        }
    )


def build_assets() -> list[dict[str, Any]]:
    inv = inventory_by_singular()
    approved_items = governed_qb02_approved_items()
    assets: list[dict[str, Any]] = []

    for noun in source_unit01_plain_s_nouns():
        row = inv[noun]
        plural = str(row["plural"])
        source = qb_item(
            approved_items,
            family_id="U02-PF05-NUMBER-PLURAL-NOUN",
            singular=noun,
        )
        assets.append(
            unit_phrase_asset(
                family_id=FAMILY_NUM_PLURAL,
                surface=f"{u02qb02.DETERMINER} {plural}",
                lexical_slots={
                    "determiner": u02qb02.DETERMINER,
                    "singular_noun": noun,
                    "plural_noun": plural,
                },
                target_egp_row_id=u02qb02.KP013,
                target_evp_sense_ids=row["vocabulary_ids"],
                source_item_id=str(source["item_id"]),
                source_reason="UNIT01_ACTIVE_NOUN_BASELINE",
            )
        )

    for adjective, noun in source_adjective_pairs():
        row = inv[noun]
        plural = str(row["plural"])
        adjective_id = u02qb02.active_adjective_id(adjective)
        source = qb_item(
            approved_items,
            family_id="U02-PF03-ADJECTIVE-PLURAL-NOUN",
            singular=noun,
            adjective=adjective,
        )
        assets.append(
            unit_phrase_asset(
                family_id=FAMILY_ADJ_PLURAL,
                surface=f"{adjective} {plural}",
                lexical_slots={
                    "adjective": adjective,
                    "singular_noun": noun,
                    "plural_noun": plural,
                },
                target_egp_row_id=u02qb02.KP011,
                target_evp_sense_ids=[*row["vocabulary_ids"], adjective_id],
                source_item_id=str(source["item_id"]),
                source_reason="UNIT01_APPROVED_ADJECTIVE_NOUN_PAIR_REUSE",
            )
        )

    for adjective, noun in source_adjective_pairs():
        row = inv[noun]
        plural = str(row["plural"])
        adjective_id = u02qb02.active_adjective_id(adjective)
        source = qb_item(
            approved_items,
            family_id="U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN",
            singular=noun,
            adjective=adjective,
        )
        assets.append(
            unit_phrase_asset(
                family_id=FAMILY_NUM_ADJ_PLURAL,
                surface=f"{u02qb02.DETERMINER} {adjective} {plural}",
                lexical_slots={
                    "determiner": u02qb02.DETERMINER,
                    "adjective": adjective,
                    "singular_noun": noun,
                    "plural_noun": plural,
                },
                target_egp_row_id=u02qb02.KP012,
                target_evp_sense_ids=[*row["vocabulary_ids"], adjective_id],
                source_item_id=str(source["item_id"]),
                source_reason="UNIT01_APPROVED_ADJECTIVE_NOUN_PAIR_REUSE",
            )
        )

    safe_by_surface = safe_chunks_by_surface()
    for base_surface, expected_chunk_id in DERIVED_CANONICAL_BASES:
        if base_surface not in inv:
            raise Unit02ChunkBuildError(f"DERIVED_BASE_NOT_IN_U02_INVENTORY:{base_surface}")
        safe_row = safe_by_surface.get(base_surface)
        if not safe_row:
            raise Unit02ChunkBuildError(f"DERIVED_BASE_NOT_IN_SAFE_CHUNKS:{base_surface}")
        if safe_row.get("canonical_chunk_id") != expected_chunk_id:
            raise Unit02ChunkBuildError(f"DERIVED_PARENT_ID_DRIFT:{base_surface}")
        if safe_row.get("level") != "A1":
            raise Unit02ChunkBuildError(f"DERIVED_PARENT_NOT_A1:{base_surface}")
        if safe_row.get("is_canonical") is not True:
            raise Unit02ChunkBuildError(f"DERIVED_PARENT_NOT_CANONICAL:{base_surface}")
        if safe_row.get("generator_allowed") is not True:
            raise Unit02ChunkBuildError(f"DERIVED_PARENT_NOT_GENERATOR_SAFE:{base_surface}")
        row = inv[base_surface]
        plural = str(row["plural"])
        source = qb_item(
            approved_items,
            family_id="U02-PF01-PLURAL-FORM-PRODUCTION",
            singular=base_surface,
        )
        assets.append(
            derived_chunk_asset(
                base_surface=base_surface,
                parent_chunk_id=expected_chunk_id,
                plural_surface=plural,
                inventory_row=row,
                safe_row=safe_row,
                source_item_id=str(source["item_id"]),
            )
        )

    assets.sort(key=lambda row: str(row["asset_id"]))
    if len(assets) != EXPECTED_ASSET_COUNT:
        raise Unit02ChunkBuildError(f"ASSET_COUNT_INVALID:{len(assets)}")
    if len({row["asset_id"] for row in assets}) != len(assets):
        raise Unit02ChunkBuildError("DUPLICATE_ASSET_ID")
    if len({row["surface"] for row in assets}) != len(assets):
        raise Unit02ChunkBuildError("DUPLICATE_SURFACE")
    return assets


def payload() -> dict[str, Any]:
    assets = build_assets()
    authority_counts = Counter(str(row["authority_scope"]) for row in assets)
    family_counts = Counter(str(row["family_id"]) for row in assets)
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "unit02_native_assets": assets,
        "coverage_denominators": {
            "unit02_native_chunk_asset_count": len(assets),
            "unit_admitted_phrase_count": authority_counts["UNIT_ADMITTED_PHRASE"],
            "derived_unit_form_count": authority_counts["DERIVED_UNIT_FORM"],
            "family_counts": dict(sorted(family_counts.items())),
            "u02qb01_plain_s_noun_surface_count_not_chunk_denominator": u02qb02.EXPECTED_NOUN_SURFACES,
            "u02qb02_approved_question_count_not_chunk_denominator": u02qb02.EXPECTED_APPROVED,
        },
        "inheritance_contract": {
            "unit01_used_as_lexical_semantic_baseline": True,
            "unit01_assets_auto_admitted_to_unit02": False,
            "unit02_requires_native_assets": True,
        },
        "admission_policy": {
            "u02qb01_plain_s_authority_required": True,
            "u02qb02_governed_approved_item_required": True,
            "unit01_active_noun_reuse_requires_u02_plain_s_membership": True,
            "unit01_adjective_pair_reuse_requires_u02_plain_s_membership": True,
            "canonical_multiword_derivative_requires_a1_safe_parent": True,
            "generated_questionbank_items_are_not_chunk_assets": True,
            "global_canonical_promotion_allowed": False,
            "receptive_only_ice_cream_derivative_admitted": False,
        },
        "claim_boundaries": {
            "global_chunk_authority_mutated": False,
            "unit01_assets_mutated": False,
            "questionbank_mutated": False,
            "runtime_connected": False,
            "new_scene_created": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate() -> dict[str, Any]:
    value = payload()
    return policy_artifact.build_candidate(
        payload=value,
        producer_id=TASK_ID,
        level_scope=LEVEL_SCOPE,
        source_bindings={
            "u02qb01_task_id": "A1FS-V1-U02QB01_ExactPlainSActiveVocabularyInventory",
            "u02qb02_task_id": u02qb02.TASK_ID,
            "unit01_contract_task_id": u02qb02.u01_contract.TASK_ID,
            "safe_chunk_authority_path": str(SAFE_CHUNKS_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "parent_canonical_chunk_ids": [row[1] for row in DERIVED_CANONICAL_BASES],
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u02ch01_unit02_native_chunk_assets as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def main() -> int:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u02ch01_unit02_native_chunk_assets as validator

    report = validator.validate_approved(candidate, approved)
    counts = approved["payload"]["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(f"UNIT02_NATIVE_CHUNK_ASSETS={counts['unit02_native_chunk_asset_count']}")
    print(f"UNIT_ADMITTED_PHRASES={counts['unit_admitted_phrase_count']}")
    print(f"DERIVED_UNIT_FORMS={counts['derived_unit_form_count']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
