#!/usr/bin/env python3
"""Build the RAZ A-W four-layer Theme/Sentence/Scene classification package.

The builder joins:

1. derived page-unit observations,
2. review candidates,
3. Reading Authority bridge candidates, and
4. normalized/enriched page-unit linkage.

It emits only text-free candidate metadata. It does not promote Authority,
populate Learning Units, create learner-facing content, or generate images.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_theme_sentence_scene_candidate_classification as three_layer
from ulga.builders import build_raz_aw_derived_schema_compatibility as compatibility
from ulga.builders import build_raz_aw_linkage_integrity_and_page_unit_lineage as linkage

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_FourLayerThemeSentenceSceneClassification"
SCHEMA_VERSION = "raz.aw.four_layer_theme_sentence_scene_classification.v1"
PASS_STATUS = "PASS_RAZ_AW_FOUR_LAYER_THEME_SENTENCE_SCENE_CLASSIFICATION"
EXPECTED_RECORD_COUNT = 22632
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_MANIFEST = REPO_ROOT / ".local/raz_af/a1_a1plus_reading_source_manifest.json"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/four_layer_classification/"
    / "theme_sentence_scene_four_layer.safe.json"
)

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_A_W",
    "derived_read_performed": True,
    "review_read_performed": True,
    "reading_bridge_read_performed": True,
    "linkage_read_performed": True,
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
    "a2_a2plus_opened": False,
}

FORBIDDEN_SAFE_KEYS = three_layer.FORBIDDEN_SAFE_KEYS | {
    "source_payload",
    "raw_payload",
}


class FourLayerClassificationError(ValueError):
    """Fail-closed four-layer identity, lineage, or accounting error."""


def bind_packages(
    classification: Mapping[str, Any],
    linkage_package: Mapping[str, Any],
    *,
    expected_record_count: int = EXPECTED_RECORD_COUNT,
) -> dict[str, Any]:
    classification_gate = classification.get("classification_gate", {})
    linkage_gate = linkage_package.get("integrity_gate", {})
    if classification_gate.get("decision") != "THREE_LAYER_CLASSIFICATION_READY_FOR_REVIEW":
        raise FourLayerClassificationError("three_layer_classification_not_ready")
    if linkage_gate.get("decision") != "LINKAGE_READY_FOR_CLASSIFICATION_LINEAGE":
        raise FourLayerClassificationError("linkage_not_ready")

    classification_links = classification.get("cross_links")
    linkage_rows = linkage_package.get("page_unit_lineage")
    if not isinstance(classification_links, list) or not isinstance(linkage_rows, list):
        raise FourLayerClassificationError("cross_link_or_lineage_rows_missing")

    linkage_by_ref: dict[str, Mapping[str, Any]] = {}
    for row in linkage_rows:
        if not isinstance(row, Mapping):
            raise FourLayerClassificationError("invalid_linkage_lineage_row")
        ref = row.get("source_unit_ref")
        if not isinstance(ref, str) or not ref or ref in linkage_by_ref:
            raise FourLayerClassificationError(
                f"invalid_or_duplicate_linkage_ref:{ref}"
            )
        linkage_by_ref[ref] = row

    classification_by_ref: dict[str, Mapping[str, Any]] = {}
    for row in classification_links:
        if not isinstance(row, Mapping):
            raise FourLayerClassificationError("invalid_classification_cross_link")
        ref = row.get("source_unit_ref")
        if not isinstance(ref, str) or not ref or ref in classification_by_ref:
            raise FourLayerClassificationError(
                f"invalid_or_duplicate_classification_ref:{ref}"
            )
        classification_by_ref[ref] = row

    classification_refs = set(classification_by_ref)
    linkage_refs = set(linkage_by_ref)
    if classification_refs != linkage_refs:
        missing_linkage = sorted(classification_refs - linkage_refs)
        missing_classification = sorted(linkage_refs - classification_refs)
        raise FourLayerClassificationError(
            "four_layer_ref_set_mismatch:"
            f"missing_linkage={missing_linkage[:5]}:"
            f"missing_classification={missing_classification[:5]}"
        )

    four_layer_links = []
    for ref in sorted(classification_refs):
        base = classification_by_ref[ref]
        line = linkage_by_ref[ref]
        if line.get("authority_status") != "candidate_only":
            raise FourLayerClassificationError(
                f"linkage_authority_status_mismatch:{ref}"
            )
        if line.get("promotion_status") != "promotion_blocked":
            raise FourLayerClassificationError(
                f"linkage_promotion_status_mismatch:{ref}"
            )
        if line.get("review_status") != "pending":
            raise FourLayerClassificationError(
                f"linkage_review_status_mismatch:{ref}"
            )
        four_layer_links.append(
            {
                "source_unit_ref": ref,
                "theme_situation_candidate_ids": list(
                    base.get("theme_situation_candidate_ids") or []
                ),
                "sentence_seed_id": base.get("sentence_seed_id"),
                "scene_seed_id": base.get("scene_seed_id"),
                "review_candidate_uid": base.get("review_candidate_uid"),
                "bridge_candidate_uid": base.get("bridge_candidate_uid"),
                "normalized_linkage_uid": line.get("normalized_linkage_uid"),
                "enriched_linkage_uid": line.get("enriched_linkage_uid"),
                "normalized_trace_confidence": line.get(
                    "normalized_trace_confidence"
                ),
                "enriched_trace_confidence": line.get(
                    "enriched_trace_confidence"
                ),
                "authority_status": line.get("authority_status"),
                "promotion_status": line.get("promotion_status"),
                "review_status": line.get("review_status"),
                "required_review_before_promotion": line.get(
                    "required_review_before_promotion"
                ),
                "allowed_authority_targets": list(
                    line.get("allowed_authority_targets") or []
                ),
                "blocked_authority_targets": list(
                    line.get("blocked_authority_targets") or []
                ),
            }
        )

    classification_scope = classification.get("source_scope", {})
    linkage_scope = linkage_package.get("source_scope", {})
    record_count = classification_scope.get("record_count")
    source_checks = {
        "classification_record_count_exact": record_count
        == expected_record_count,
        "linkage_page_unit_count_exact": linkage_scope.get("page_unit_count")
        == expected_record_count,
        "four_layer_cross_link_count_exact": len(four_layer_links)
        == expected_record_count,
        "classification_linkage_ref_sets_equal": classification_refs
        == linkage_refs,
        "classification_levels_exact": classification_scope.get("levels")
        == list(three_layer.LEVELS),
        "linkage_levels_exact": linkage_scope.get("levels")
        == list(linkage.LEVELS),
        "classification_ready_for_review": classification_gate.get(
            "ready_for_human_review"
        )
        is True,
        "linkage_ready_for_classification": linkage_gate.get(
            "ready_for_classification_lineage"
        )
        is True,
    }
    ready = all(source_checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "source_scope": {
            "levels": list(three_layer.LEVELS),
            "record_count": record_count,
            "book_count": classification_scope.get("book_count"),
            "derived_record_count": classification_scope.get(
                "derived_record_count"
            ),
            "review_candidate_count": classification_scope.get(
                "review_candidate_count"
            ),
            "bridge_candidate_count": classification_scope.get(
                "bridge_candidate_count"
            ),
            "linkage_page_unit_count": linkage_scope.get("page_unit_count"),
            "linkage_record_count": linkage_scope.get(
                "page_unit_linkage_record_count"
            ),
            "classification_source_files": classification_scope.get(
                "source_files"
            ),
            "linkage_source_files": linkage_scope.get("source_files"),
        },
        "authority_baselines": classification.get("authority_baselines"),
        "theme_situation_candidates": classification.get(
            "theme_situation_candidates"
        ),
        "sentence_seed_candidates": classification.get(
            "sentence_seed_candidates"
        ),
        "scene_seed_candidates": classification.get("scene_seed_candidates"),
        "four_layer_cross_links": four_layer_links,
        "classification_summary": {
            **dict(classification.get("classification_summary", {})),
            "four_layer_cross_link_count": len(four_layer_links),
            "normalized_linkage_count": len(four_layer_links),
            "enriched_linkage_count": len(four_layer_links),
        },
        "classification_gate": {
            "source_checks": source_checks,
            "decision": (
                "FOUR_LAYER_CLASSIFICATION_READY_FOR_REVIEW"
                if ready
                else "BLOCKED_FOUR_LAYER_IDENTITY_OR_ACCOUNTING"
            ),
            "ready_for_human_review": ready,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": (
                "RAZ-AW_ThemeSentenceSceneReviewDedupAndSourceBandFiltering"
            ),
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def build_from_source(
    source_root: Path,
    manifest_path: Path,
    *,
    expected_record_count: int = EXPECTED_RECORD_COUNT,
) -> dict[str, Any]:
    records, file_index = compatibility.load_three_layers(source_root)
    classification = three_layer.build_package(
        records,
        file_index,
        deep.load_authorities(),
        deep.load_manifest_grammar_tags(manifest_path),
        expected_record_count=expected_record_count,
        expected_book_count=three_layer.EXPECTED_BOOK_COUNT,
    )
    linkage_package = linkage.load_and_build(
        source_root,
        expected_page_unit_count=expected_record_count,
    )
    return bind_packages(
        classification,
        linkage_package,
        expected_record_count=expected_record_count,
    )


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
        package = build_from_source(args.source_root, args.manifest)
        leakage = scan_forbidden_safe_keys(package)
        if leakage:
            raise FourLayerClassificationError(
                "safe_output_leakage:" + ";".join(leakage[:20])
            )
        deep.write_json_atomic(args.output, package)
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "decision": package["classification_gate"]["decision"],
                    "record_count": package["source_scope"]["record_count"],
                    "theme_situation_candidate_count": package[
                        "classification_summary"
                    ]["theme_situation_candidate_count"],
                    "sentence_seed_candidate_count": package[
                        "classification_summary"
                    ]["sentence_seed_candidate_count"],
                    "scene_seed_candidate_count": package[
                        "classification_summary"
                    ]["scene_seed_candidate_count"],
                    "four_layer_cross_link_count": package[
                        "classification_summary"
                    ]["four_layer_cross_link_count"],
                    "package_sha256": package["package_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (
        FourLayerClassificationError,
        compatibility.DerivedSchemaCompatibilityError,
        three_layer.ClassificationError,
        linkage.LinkageIntegrityError,
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
