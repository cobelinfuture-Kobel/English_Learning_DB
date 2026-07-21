#!/usr/bin/env python3
"""Validate RAZ A-W linkage and emit text-free page-unit lineage.

The source linkage contract contains multiple artifact layers. This builder
selects only `page_unit` rows and requires exactly two linkage records per
source page unit: one normalized and one enriched. The output is safe metadata
for later Theme/Sentence/Scene classification and does not promote authority,
populate Learning Units, or expose source text.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_LinkageIntegrityAndPageUnitLineageGate"
SCHEMA_VERSION = "raz.aw.linkage_integrity_page_unit_lineage.v1"
PASS_STATUS = "PASS_RAZ_AW_LINKAGE_INTEGRITY_AND_PAGE_UNIT_LINEAGE"
LEVELS = tuple(chr(code) for code in range(ord("A"), ord("W") + 1))
EXPECTED_PAGE_UNIT_COUNT = 22632
EXPECTED_PAGE_UNIT_LINKAGE_RECORD_COUNT = EXPECTED_PAGE_UNIT_COUNT * 2
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/linkage_integrity/"
    / "page_unit_lineage.safe.json"
)

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_A_W_LINKAGE",
    "source_text_read": False,
    "source_text_included": False,
    "generated_content_included": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learning_unit_content_population_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_opened": False,
}

EXPECTED_ALLOWED_TARGETS = {"ReadingAuthority", "ContentQueryLayer"}
EXPECTED_BLOCKED_TARGETS = {
    "DialogueAuthority",
    "WritingAuthority",
    "AssessmentAuthority",
    "LearningOpportunityBinding",
}
EXPECTED_PAGE_VARIANTS = {"normalized_page_units", "enriched_units"}
FORBIDDEN_KEYS = {
    "text",
    "clean_text",
    "raw_text",
    "source_text",
    "original_text",
    "sentence_text",
}


class LinkageIntegrityError(ValueError):
    """Fail-closed linkage tree, contract, identity, or policy error."""


def discover_linkage_file(root: Path, level: str) -> Path:
    filename = f"raz_{level}_authority_linkage_view.json"
    candidates = [
        root / "linkage" / f"Level_{level}" / filename,
        root / f"Level_{level}" / filename,
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        found = [
            item
            for item in root.rglob(filename)
            if "linkage" in item.parts or item.parent.name == f"Level_{level}"
        ]
        if len(found) == 1:
            path = found[0]
    if path is None:
        raise LinkageIntegrityError(f"missing_linkage_file:{level}:{filename}")
    return path


def source_page_ref(record: Mapping[str, Any]) -> str:
    trace = record.get("source_traceability")
    if not isinstance(trace, Mapping):
        return ""
    return str(trace.get("source_page_unit_id") or "")


def linkage_variant(record: Mapping[str, Any]) -> str:
    uid = str(record.get("record_uid") or "")
    return uid.rsplit("::", 1)[-1] if "::" in uid else ""


def scan_forbidden_keys(value: Any, pointer: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                errors.append(f"forbidden_key:{pointer}.{key}")
            errors.extend(scan_forbidden_keys(child, f"{pointer}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_forbidden_keys(child, f"{pointer}[{index}]"))
    return errors


def validate_page_record(record: Mapping[str, Any], level: str) -> list[str]:
    errors: list[str] = []
    ref = source_page_ref(record)
    uid = str(record.get("record_uid") or "")
    variant = linkage_variant(record)
    if not ref:
        errors.append(f"missing_source_page_ref:{level}:{uid}")
    if not uid or not uid.startswith(f"{ref}::authority_linkage_v1::"):
        errors.append(f"record_uid_source_mismatch:{level}:{uid}:{ref}")
    if variant not in EXPECTED_PAGE_VARIANTS:
        errors.append(f"unexpected_page_variant:{level}:{ref}:{variant}")
    if record.get("artifact_layer") != "page_unit":
        errors.append(f"artifact_layer_mismatch:{level}:{ref}")
    if record.get("authority_status") != "candidate_only":
        errors.append(f"authority_status_mismatch:{level}:{ref}:{variant}")
    if record.get("promotion_status") != "promotion_blocked":
        errors.append(f"promotion_status_mismatch:{level}:{ref}:{variant}")
    if record.get("review_status") != "pending":
        errors.append(f"review_status_mismatch:{level}:{ref}:{variant}")
    if record.get("required_review_before_promotion") != "page_unit_review":
        errors.append(f"review_requirement_mismatch:{level}:{ref}:{variant}")
    if record.get("generated_content") is not False:
        errors.append(f"generated_content_mismatch:{level}:{ref}:{variant}")
    if record.get("derived_from_original_text") is not True:
        errors.append(f"derived_flag_mismatch:{level}:{ref}:{variant}")
    allowed = set(record.get("allowed_authority_targets") or [])
    blocked = set(record.get("blocked_authority_targets") or [])
    if not EXPECTED_ALLOWED_TARGETS.issubset(allowed):
        errors.append(f"allowed_targets_missing:{level}:{ref}:{variant}")
    if not EXPECTED_BLOCKED_TARGETS.issubset(blocked):
        errors.append(f"blocked_targets_missing:{level}:{ref}:{variant}")
    expected_confidence = "high" if variant == "normalized_page_units" else "medium"
    if record.get("trace_confidence") != expected_confidence:
        errors.append(f"trace_confidence_mismatch:{level}:{ref}:{variant}")
    return errors


def load_and_build(
    source_root: Path,
    *,
    levels: Sequence[str] = LEVELS,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    source_files: list[dict[str, Any]] = []
    lineage_rows: list[dict[str, Any]] = []
    all_errors: list[str] = []
    level_page_counts = Counter()
    total_linkage_records = 0
    artifact_layer_counts = Counter()

    for level in levels:
        path = discover_linkage_file(source_root, level)
        payload = deep.read_json(path)
        if not isinstance(payload, Mapping):
            raise LinkageIntegrityError(f"linkage_payload_not_object:{level}")
        if payload.get("schema_version") != "raz_authority_linkage_contract.v1":
            raise LinkageIntegrityError(
                f"linkage_schema_mismatch:{level}:{payload.get('schema_version')}"
            )
        records = payload.get("records")
        if not isinstance(records, list):
            raise LinkageIntegrityError(f"linkage_records_missing:{level}")
        if not all(isinstance(record, Mapping) for record in records):
            raise LinkageIntegrityError(f"invalid_linkage_record:{level}")
        total_linkage_records += len(records)
        artifact_layer_counts.update(str(record.get("artifact_layer")) for record in records)

        by_ref: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
        page_record_count = 0
        for record in records:
            if record.get("artifact_layer") != "page_unit":
                continue
            page_record_count += 1
            all_errors.extend(validate_page_record(record, level))
            ref = source_page_ref(record)
            variant = linkage_variant(record)
            if ref and variant:
                if variant in by_ref[ref]:
                    all_errors.append(
                        f"duplicate_page_variant:{level}:{ref}:{variant}"
                    )
                by_ref[ref][variant] = record

        for ref, variants in by_ref.items():
            if set(variants) != EXPECTED_PAGE_VARIANTS:
                all_errors.append(
                    f"page_variant_set_mismatch:{level}:{ref}:{sorted(variants)}"
                )
                continue
            normalized = variants["normalized_page_units"]
            enriched = variants["enriched_units"]
            normalized_allowed = sorted(set(normalized.get("allowed_authority_targets") or []))
            enriched_allowed = sorted(set(enriched.get("allowed_authority_targets") or []))
            normalized_blocked = sorted(set(normalized.get("blocked_authority_targets") or []))
            enriched_blocked = sorted(set(enriched.get("blocked_authority_targets") or []))
            if normalized_allowed != enriched_allowed:
                all_errors.append(f"allowed_target_drift:{level}:{ref}")
            if normalized_blocked != enriched_blocked:
                all_errors.append(f"blocked_target_drift:{level}:{ref}")
            lineage_rows.append(
                {
                    "source_unit_ref": ref,
                    "source_level": level,
                    "normalized_linkage_uid": normalized["record_uid"],
                    "enriched_linkage_uid": enriched["record_uid"],
                    "normalized_trace_confidence": normalized["trace_confidence"],
                    "enriched_trace_confidence": enriched["trace_confidence"],
                    "authority_status": "candidate_only",
                    "promotion_status": "promotion_blocked",
                    "review_status": "pending",
                    "required_review_before_promotion": "page_unit_review",
                    "allowed_authority_targets": normalized_allowed,
                    "blocked_authority_targets": normalized_blocked,
                }
            )
        level_page_counts[level] = len(by_ref)
        if page_record_count != len(by_ref) * 2:
            all_errors.append(
                f"page_record_accounting_mismatch:{level}:{page_record_count}:{len(by_ref)}"
            )
        source_files.append(
            {
                "level": level,
                "path": path.relative_to(source_root).as_posix(),
                "sha256": deep.sha256_file(path),
                "linkage_record_count": len(records),
                "page_unit_linkage_record_count": page_record_count,
                "page_unit_count": len(by_ref),
            }
        )

    duplicate_refs = [
        ref
        for ref, count in Counter(row["source_unit_ref"] for row in lineage_rows).items()
        if count != 1
    ]
    if duplicate_refs:
        all_errors.extend(f"duplicate_cross_level_page_ref:{ref}" for ref in duplicate_refs)

    source_checks = {
        "levels_exact": tuple(levels) == LEVELS,
        "source_file_count_exact": len(source_files) == len(LEVELS),
        "page_unit_count_exact": len(lineage_rows) == expected_page_unit_count,
        "page_unit_linkage_record_count_exact": sum(
            row["page_unit_linkage_record_count"] for row in source_files
        ) == expected_page_unit_count * 2,
        "all_page_refs_unique": not duplicate_refs,
        "all_page_records_policy_valid": not all_errors,
    }
    ready = all(source_checks.values()) and not all_errors

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "source_scope": {
            "levels": list(levels),
            "source_file_count": len(source_files),
            "total_linkage_record_count": total_linkage_records,
            "page_unit_linkage_record_count": sum(
                row["page_unit_linkage_record_count"] for row in source_files
            ),
            "page_unit_count": len(lineage_rows),
            "level_page_unit_counts": {
                level: level_page_counts[level] for level in levels
            },
            "artifact_layer_counts": dict(sorted(artifact_layer_counts.items())),
            "source_files": source_files,
        },
        "page_unit_lineage": sorted(
            lineage_rows, key=lambda row: row["source_unit_ref"]
        ),
        "integrity_gate": {
            "source_checks": source_checks,
            "decision": (
                "LINKAGE_READY_FOR_CLASSIFICATION_LINEAGE"
                if ready
                else "BLOCKED_LINKAGE_INTEGRITY"
            ),
            "ready_for_classification_lineage": ready,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": "RAZ-AW_FourLayerThemeSentenceSceneClassificationExecution",
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": sorted(set(all_errors)),
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = load_and_build(args.source_root)
        leakage = scan_forbidden_keys(package)
        if leakage:
            raise LinkageIntegrityError(
                "safe_output_leakage:" + ";".join(leakage[:20])
            )
        deep.write_json_atomic(args.output, package)
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "decision": package["integrity_gate"]["decision"],
                    "page_unit_count": package["source_scope"]["page_unit_count"],
                    "error_count": len(package["errors"]),
                    "package_sha256": package["package_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0 if package["validation_status"] == PASS_STATUS else 1
    except (
        LinkageIntegrityError,
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
