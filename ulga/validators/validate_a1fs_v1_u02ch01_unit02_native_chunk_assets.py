#!/usr/bin/env python3
"""Validate the governed Unit02-native chunk and phrase asset admission."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u02ch01_unit02_native_chunk_assets as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02CH01_UNIT02_NATIVE_CHUNK_ASSETS_VALIDATOR"

EXPECTED_FAMILY_COUNTS = {
    builder.FAMILY_NUM_PLURAL: 13,
    builder.FAMILY_ADJ_PLURAL: 5,
    builder.FAMILY_NUM_ADJ_PLURAL: 5,
    builder.FAMILY_CANONICAL_DERIVED: 3,
}
EXPECTED_DERIVED = {
    "CD players": "EVP_CHUNK_000003",
    "dining rooms": "EVP_CHUNK_000030",
    "living rooms": "EVP_CHUNK_000075",
}
FORBIDDEN_SURFACES = {
    "ice creams",
    "big boxes",
    "two big boxes",
}


class Unit02ChunkValidationError(ValueError):
    """Fail-closed U02CH01 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit02ChunkValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def expected_number_surfaces() -> set[str]:
    inv = builder.inventory_by_singular()
    return {
        f"{builder.u02qb02.DETERMINER} {inv[noun]['plural']}"
        for noun in builder.EXPECTED_UNIT01_PLAIN_S_NOUNS
    }


def expected_adjective_surfaces() -> set[str]:
    inv = builder.inventory_by_singular()
    return {
        f"{adjective} {inv[noun]['plural']}"
        for adjective, noun in builder.EXPECTED_ADJECTIVE_PAIRS
    }


def expected_number_adjective_surfaces() -> set[str]:
    inv = builder.inventory_by_singular()
    return {
        f"{builder.u02qb02.DETERMINER} {adjective} {inv[noun]['plural']}"
        for adjective, noun in builder.EXPECTED_ADJECTIVE_PAIRS
    }


def approved_qb_item_ids() -> set[str]:
    return {
        str(row["item_id"])
        for row in builder.governed_qb02_approved_items()
    }


def validate_asset(asset: Mapping[str, Any], qb_item_ids: set[str]) -> None:
    asset_id = str(asset.get("asset_id") or "")
    require(asset.get("unit_id") == builder.UNIT_ID, f"UNIT_INVALID:{asset_id}")
    require(asset.get("level") == "A1", f"LEVEL_INVALID:{asset_id}")
    require(asset.get("coverage_state") == "DIRECT_TARGET", f"COVERAGE_STATE_INVALID:{asset_id}")
    require(asset.get("grammar_target_ids") == ["REGULAR_PLURAL_NOUNS"], f"GRAMMAR_INVALID:{asset_id}")
    require(asset.get("unit_pattern_ids") == [builder.u02qb02.DIRECT_PATTERN_ID], f"PATTERN_INVALID:{asset_id}")
    require(asset.get("production_allowed") is True, f"PRODUCTION_INVALID:{asset_id}")
    require(asset.get("direct_assessment_allowed") is True, f"ASSESSMENT_INVALID:{asset_id}")
    require(asset.get("reusable_in_later_units") is True, f"REUSE_INVALID:{asset_id}")
    require(asset.get("learner_visible_capable") is True, f"LEARNER_FLAG_INVALID:{asset_id}")
    require(asset.get("global_canonical_created") is False, f"GLOBAL_PROMOTION_INVALID:{asset_id}")
    require(asset.get("admission", {}).get("status") == "AUTO_APPROVED", f"ADMISSION_INVALID:{asset_id}")
    require(asset.get("semantic_signature") == builder.semantic_signature(asset), f"SIGNATURE_INVALID:{asset_id}")

    surface = str(asset.get("surface") or "")
    require(surface not in FORBIDDEN_SURFACES, f"FORBIDDEN_SURFACE:{surface}")
    slots = asset.get("lexical_slots", {})
    singular = str(slots.get("singular_noun") or "")
    plural = str(slots.get("plural_noun") or "")
    inv = builder.inventory_by_singular()
    require(singular in inv, f"NOUN_NOT_IN_U02_INVENTORY:{asset_id}")
    require(plural == inv[singular]["plural"], f"PLURAL_DRIFT:{asset_id}")
    require(plural == singular + "s", f"NON_PLAIN_S:{asset_id}")
    require(
        set(inv[singular]["vocabulary_ids"]).issubset(set(asset.get("target_evp_sense_ids", []))),
        f"VOCABULARY_AUTHORITY_MISSING:{asset_id}",
    )

    source_refs = asset.get("source_refs")
    require(isinstance(source_refs, list) and source_refs, f"SOURCE_REFS_INVALID:{asset_id}")
    qb_refs = [
        ref for ref in source_refs
        if ref.get("source_type") == "U02QB02_GOVERNED_APPROVED_ITEM"
    ]
    require(len(qb_refs) == 1, f"QB02_SOURCE_CARDINALITY:{asset_id}")
    require(str(qb_refs[0].get("item_id")) in qb_item_ids, f"QB02_SOURCE_NOT_APPROVED:{asset_id}")

    scope = asset.get("authority_scope")
    if scope == "UNIT_ADMITTED_PHRASE":
        require(asset.get("asset_kind") == "PROJECT_INSTRUCTIONAL_PHRASE", f"ASSET_KIND_INVALID:{asset_id}")
        require(asset.get("linguistic_family") == "NP_COMPOSITION", f"LINGUISTIC_FAMILY_INVALID:{asset_id}")
        require(asset.get("target_chunk_ids") == [], f"CANONICAL_TARGET_LEAK:{asset_id}")
        require("parent_canonical_chunk_id" not in asset, f"PARENT_CANONICAL_LEAK:{asset_id}")
    elif scope == "DERIVED_UNIT_FORM":
        require(asset.get("asset_kind") == "DERIVED_CANONICAL_CHUNK_FORM", f"DERIVED_KIND_INVALID:{asset_id}")
        parent = asset.get("parent_canonical_chunk_id")
        require(EXPECTED_DERIVED.get(surface) == parent, f"DERIVED_PARENT_INVALID:{asset_id}")
        require(asset.get("target_chunk_ids") == [parent], f"DERIVED_TARGET_INVALID:{asset_id}")
        require(asset.get("family_id") == builder.FAMILY_CANONICAL_DERIVED, f"DERIVED_FAMILY_INVALID:{asset_id}")
    else:
        raise Unit02ChunkValidationError(f"AUTHORITY_SCOPE_INVALID:{asset_id}")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    require(payload.get("level_scope") == ["A1"], "LEVEL_SCOPE_INVALID")

    assets = payload.get("unit02_native_assets")
    require(isinstance(assets, list), "ASSETS_NOT_LIST")
    require(len(assets) == builder.EXPECTED_ASSET_COUNT, "ASSET_COUNT_INVALID")
    require(len({row["asset_id"] for row in assets}) == len(assets), "DUPLICATE_ASSET_ID")
    require(len({row["surface"] for row in assets}) == len(assets), "DUPLICATE_SURFACE")
    require(len({row["semantic_signature"] for row in assets}) == len(assets), "DUPLICATE_SIGNATURE")

    family_counts = Counter(str(row["family_id"]) for row in assets)
    require(dict(family_counts) == EXPECTED_FAMILY_COUNTS, "FAMILY_COUNTS_INVALID")
    authority_counts = Counter(str(row["authority_scope"]) for row in assets)
    require(
        authority_counts == Counter({
            "UNIT_ADMITTED_PHRASE": builder.EXPECTED_UNIT_ADMITTED_PHRASE_COUNT,
            "DERIVED_UNIT_FORM": builder.EXPECTED_DERIVED_UNIT_FORM_COUNT,
        }),
        "AUTHORITY_COUNTS_INVALID",
    )

    qb_item_ids = approved_qb_item_ids()
    for asset in assets:
        validate_asset(asset, qb_item_ids)

    per_family = {
        family: {str(row["surface"]) for row in assets if row["family_id"] == family}
        for family in EXPECTED_FAMILY_COUNTS
    }
    require(per_family[builder.FAMILY_NUM_PLURAL] == expected_number_surfaces(), "NUMBER_SURFACES_INVALID")
    require(per_family[builder.FAMILY_ADJ_PLURAL] == expected_adjective_surfaces(), "ADJECTIVE_SURFACES_INVALID")
    require(
        per_family[builder.FAMILY_NUM_ADJ_PLURAL] == expected_number_adjective_surfaces(),
        "NUMBER_ADJECTIVE_SURFACES_INVALID",
    )
    require(
        {
            str(row["surface"]): str(row["parent_canonical_chunk_id"])
            for row in assets
            if row["family_id"] == builder.FAMILY_CANONICAL_DERIVED
        } == EXPECTED_DERIVED,
        "DERIVED_SURFACES_INVALID",
    )
    require(not (FORBIDDEN_SURFACES & {str(row["surface"]) for row in assets}), "FORBIDDEN_SURFACE_ADMITTED")

    coverage = payload.get("coverage_denominators", {})
    require(coverage.get("unit02_native_chunk_asset_count") == 26, "COVERAGE_ASSET_COUNT_INVALID")
    require(coverage.get("unit_admitted_phrase_count") == 23, "COVERAGE_UNIT_PHRASE_INVALID")
    require(coverage.get("derived_unit_form_count") == 3, "COVERAGE_DERIVED_INVALID")
    require(coverage.get("family_counts") == EXPECTED_FAMILY_COUNTS, "COVERAGE_FAMILY_COUNTS_INVALID")
    require(
        coverage.get("u02qb01_plain_s_noun_surface_count_not_chunk_denominator") == 162,
        "SOURCE_NOUN_DENOMINATOR_INVALID",
    )
    require(
        coverage.get("u02qb02_approved_question_count_not_chunk_denominator") == 658,
        "SOURCE_QUESTION_DENOMINATOR_INVALID",
    )

    inheritance = payload.get("inheritance_contract", {})
    require(inheritance.get("unit01_used_as_lexical_semantic_baseline") is True, "UNIT01_BASELINE_INVALID")
    require(inheritance.get("unit01_assets_auto_admitted_to_unit02") is False, "UNIT01_AUTO_ADMISSION_INVALID")
    require(inheritance.get("unit02_requires_native_assets") is True, "UNIT02_NATIVE_REQUIREMENT_INVALID")

    policy = payload.get("admission_policy", {})
    for key in (
        "u02qb01_plain_s_authority_required",
        "u02qb02_governed_approved_item_required",
        "unit01_active_noun_reuse_requires_u02_plain_s_membership",
        "unit01_adjective_pair_reuse_requires_u02_plain_s_membership",
        "canonical_multiword_derivative_requires_a1_safe_parent",
        "generated_questionbank_items_are_not_chunk_assets",
    ):
        require(policy.get(key) is True, f"POLICY_INVALID:{key}")
    require(policy.get("global_canonical_promotion_allowed") is False, "GLOBAL_PROMOTION_ALLOWED")
    require(policy.get("receptive_only_ice_cream_derivative_admitted") is False, "ICE_CREAM_DERIVATIVE_ADMITTED")

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "global_chunk_authority_mutated",
        "unit01_assets_mutated",
        "questionbank_mutated",
        "runtime_connected",
        "new_scene_created",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return {
        "status": builder.PASS_STATUS,
        "unit02_native_chunk_asset_count": len(assets),
        "unit_admitted_phrase_count": authority_counts["UNIT_ADMITTED_PHRASE"],
        "derived_unit_form_count": authority_counts["DERIVED_UNIT_FORM"],
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("producer_id") == builder.TASK_ID, "CANDIDATE_PRODUCER_INVALID")
    require(candidate.get("level_scope") == ["A1"], "CANDIDATE_LEVEL_INVALID")
    validate_payload(candidate["payload"])
    return validation_receipt(candidate["payload"])


def validate_approved(
    candidate: Mapping[str, Any], approved: Mapping[str, Any]
) -> dict[str, Any]:
    validate_candidate(candidate)
    policy_artifact.verify_artifact_digest(approved)
    require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
    require(approved.get("producer_id") == builder.TASK_ID, "APPROVED_PRODUCER_INVALID")
    require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
    require(approved.get("admission", {}).get("status") == "APPROVED", "APPROVED_STATUS_INVALID")
    require(approved.get("admission", {}).get("decision_ref") == builder.DECISION_REF, "DECISION_REF_INVALID")
    require(len(approved.get("validation_receipts", [])) == 1, "RECEIPT_COUNT_INVALID")
    require(approved["validation_receipts"][0]["validator_id"] == VALIDATOR_ID, "RECEIPT_VALIDATOR_INVALID")
    summary = validate_payload(approved["payload"])
    return {
        **summary,
        "error_count": 0,
        "errors": [],
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "approved_artifact_sha256": approved["artifact_sha256"],
    }
