#!/usr/bin/env python3
"""Attach a validated optional PKU overlay to an existing R3F composition."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only consumer adapter over an existing R3F lesson composition and M4 optional PKU overlay; no content, selection, production mapping, learner evidence, mastery, media, or A2 payload."
TASK_ID = "KET99-PK-M5_OptionalInstructionalOverlayConsumerIntegrationAndRuntimeCanary"
SCHEMA_VERSION = "ket99.pku.optional_overlay_consumer_canary.v1"
PASS_STATUS = "PASS_KET99_PK_M5_OPTIONAL_OVERLAY_CONSUMER_CANARY_READY"
NEXT_SHORT_STEP = "KET99-PK-M6_RealPrivateLessonCanaryAndPilotCloseout"
R3F_TASK = "A1FS-V1-CP07F-R3F_ReferenceAwareOptionalContextLessonComposition"
R3F_SCHEMA = "a1fs.v1.cp07f.r3f.reference_aware_optional_context_lesson_composition.v1"
R3F_STATUS = "PASS_CP07F_R3F_REFERENCE_AWARE_OPTIONAL_CONTEXT_LESSON_COMPOSITION_READY"
M4_TASK = "KET99-PK-M4_ControlledPilotOverlayAdmissionAndCoverageReadback"
M4_SCHEMA = "ket99.pku.controlled_pilot_overlay_admission.v1"
M4_STATUS = "PASS_KET99_PK_M4_CONTROLLED_PILOT_OVERLAY_ADMISSION_READY"
R3F = ROOT / ".local/a1fs_v1/cp07r3f/reference_aware_optional_context_lesson_composition.safe.json"
M4 = ROOT / ".local/a1fs_v1/ket99_pku_m4/controlled_pilot_overlay_admission.safe.json"
OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m5/optional_overlay_consumer_canary.safe.json"
FORBIDDEN_KEYS = {
    "payload", "source_content", "text", "prompt", "correct_answer",
    "answer_key", "learner_response", "transcript_text", "audio_bytes", "recording",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise ValueError(f"private_content_key_forbidden:{path}.{key}")
            walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_forbidden(child, f"{path}[{index}]")


def verify(
    composition: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if (
        composition.get("cp07r3f_task_id") != R3F_TASK
        or composition.get("cp07r3f_schema_version") != R3F_SCHEMA
        or composition.get("cp07r3f_validation_status") != R3F_STATUS
    ):
        raise ValueError("r3f_contract_invalid")
    if composition.get("errors") != [] or composition.get("stop_reason") != "NONE":
        raise ValueError("r3f_not_passed")
    unified = composition.get("unified_lesson_composition")
    if not isinstance(unified, Mapping):
        raise ValueError("r3f_composition_missing")
    gate = unified.get("consumer_gate", {})
    if (
        gate.get("m4_selected_lesson_unchanged") is not True
        or gate.get("m1_hard_prerequisite_graph_unchanged") is not True
        or gate.get("ket_asset_body_required") is not True
        or gate.get("a2_payload_included") is not False
    ):
        raise ValueError("r3f_consumer_gate_invalid")
    items = unified.get("composition_items")
    if (
        not isinstance(items, list)
        or not any(
            isinstance(row, Mapping) and row.get("source_kind") == "KET_ASSET_BODY"
            for row in items
        )
    ):
        raise ValueError("r3f_ket_asset_required")
    if composition.get("claim_boundaries", {}).get("hard_lesson_selection_changed") is not False:
        raise ValueError("r3f_selection_boundary_invalid")

    if (
        overlay.get("task_id") != M4_TASK
        or overlay.get("schema_version") != M4_SCHEMA
        or overlay.get("validation_status") != M4_STATUS
    ):
        raise ValueError("m4_overlay_contract_invalid")
    if overlay.get("errors") != [] or overlay.get("stop_reason") != "NONE":
        raise ValueError("m4_overlay_not_passed")
    unsigned = dict(overlay)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != digest(unsigned):
        raise ValueError("m4_overlay_sha256_invalid")
    policy = overlay.get("admission_policy", {})
    for key in (
        "hard_lesson_selection_allowed",
        "production_mapping_allowed",
        "a2_mapping_allowed",
    ):
        if policy.get(key) is not False:
            raise ValueError(f"m4_overlay_boundary_invalid:{key}")
    if policy.get("missing_reference_blocks_delivery") is not False:
        raise ValueError("m4_overlay_delivery_boundary_invalid")
    if (
        composition.get("source_identity", {}).get("m2_consumer_sha256")
        != overlay.get("source_identity", {}).get("m2_consumer_sha256")
    ):
        raise ValueError("r3f_m4_m2_binding_invalid")

    lesson_id = str(unified.get("selected_lesson_id") or "")
    matches = [
        row for row in overlay.get("lesson_pilot_overlays", [])
        if isinstance(row, Mapping) and row.get("lesson_id") == lesson_id
    ]
    if len(matches) != 1:
        raise ValueError("m4_selected_lesson_overlay_not_unique")
    row = matches[0]
    if (
        row.get("skill") != unified.get("selected_skill")
        or row.get("level") != unified.get("selected_level")
    ):
        raise ValueError("m4_selected_lesson_partition_drift")
    references = row.get("optional_pilot_references")
    if not isinstance(references, list):
        raise ValueError("m4_optional_reference_list_required")
    expected_status = "PILOT_REFERENCED" if references else "NO_PILOT_REFERENCE"
    if (
        row.get("pilot_reference_status") != expected_status
        or row.get("delivery_blocked_by_missing_reference") is not False
        or row.get("hard_lesson_selection_changed") is not False
    ):
        raise ValueError("m4_lesson_overlay_boundary_invalid")
    for reference in references:
        if (
            not isinstance(reference, Mapping)
            or reference.get("runtime_effect")
            != "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY"
            or reference.get("hard_lesson_selection_allowed") is not False
            or reference.get("production_mapping_allowed") is not False
        ):
            raise ValueError("m4_optional_reference_boundary_invalid")
    return unified, row


def build_artifact(
    composition: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    unified, row = verify(composition, overlay)
    before_items = copy.deepcopy(list(unified["composition_items"]))
    before_coverage = copy.deepcopy(dict(unified.get("coverage_summary", {})))
    references = copy.deepcopy(list(row.get("optional_pilot_references", [])))

    enriched = copy.deepcopy(dict(composition))
    enriched["ket99_pku_m5_task_id"] = TASK_ID
    enriched["ket99_pku_m5_schema_version"] = SCHEMA_VERSION
    enriched["ket99_pku_m5_validation_status"] = PASS_STATUS
    enriched["source_identity"] = copy.deepcopy(dict(composition.get("source_identity", {})))
    enriched["source_identity"]["ket99_pku_m4_overlay_sha256"] = digest(overlay)

    enriched_unified = enriched["unified_lesson_composition"]
    enriched_unified["ket99_pku_optional_overlay"] = {
        "overlay_status": row["pilot_reference_status"],
        "runtime_canary_status": (
            "OPTIONAL_METADATA_AVAILABLE" if references else "NO_OPTIONAL_METADATA"
        ),
        "optional_pilot_references": references,
        "optional_reference_count": len(references),
        "composition_item_count_delta": 0,
        "delivery_allowed_count_delta": 0,
        "missing_reference_blocks_delivery": False,
        "hard_lesson_selection_changed": False,
        "production_mapping_allowed": False,
    }
    if enriched_unified["composition_items"] != before_items:
        raise ValueError("composition_items_mutated")

    coverage = enriched_unified.setdefault("coverage_summary", {})
    coverage["ket99_pku_optional_reference_count"] = len(references)
    coverage["composition_item_count_before_pku_overlay"] = before_coverage.get(
        "composition_item_count", len(before_items)
    )
    coverage["composition_item_count_after_pku_overlay"] = len(
        enriched_unified["composition_items"]
    )
    coverage["delivery_allowed_count_before_pku_overlay"] = before_coverage.get(
        "delivery_allowed_now_count", 0
    )
    coverage["delivery_allowed_count_after_pku_overlay"] = coverage[
        "delivery_allowed_count_before_pku_overlay"
    ]

    consumer_gate = enriched_unified.setdefault("consumer_gate", {})
    consumer_gate["ket99_pku_optional_overlay_connected"] = True
    consumer_gate["ket99_pku_metadata_canary_passed"] = True
    consumer_gate["ket99_pku_reference_optional"] = True
    consumer_gate["missing_pku_reference_blocks_delivery"] = False

    enriched["claim_boundaries"] = copy.deepcopy(dict(composition.get("claim_boundaries", {})))
    enriched["claim_boundaries"].update({
        "ket99_pku_metadata_connected": True,
        "production_mapping_claimed": False,
        "hard_lesson_selection_changed": False,
        "learner_delivery_completed": False,
        "mastery_or_retention_claimed": False,
        "a2_a2plus_in_scope": False,
    })
    enriched["errors"] = []
    enriched["stop_reason"] = "NONE"
    enriched["next_short_step"] = NEXT_SHORT_STEP
    walk_forbidden(enriched)
    return enriched


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r3f", type=Path, default=R3F)
    parser.add_argument("--m4-overlay", type=Path, default=M4)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.r3f), read_json(args.m4_overlay))
    write(args.output, artifact)
    print(json.dumps(
        artifact["unified_lesson_composition"]["ket99_pku_optional_overlay"],
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
