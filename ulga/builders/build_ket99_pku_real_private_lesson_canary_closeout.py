#!/usr/bin/env python3
"""Close the KET99 PKU pilot only on a real referenced private lesson canary."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only closeout readback over an existing M5 private lesson canary; no content, selection, production mapping, learner evidence, mastery, media, or A2 payload."
TASK_ID = "KET99-PK-M6_RealPrivateLessonCanaryAndPilotCloseout"
SCHEMA_VERSION = "ket99.pku.real_private_lesson_canary_closeout.v1"
PASS_CLOSEOUT = "PASS_KET99_PK_M6_REAL_PRIVATE_LESSON_CANARY_AND_PILOT_CLOSEOUT"
PASS_PENDING = "PASS_KET99_PK_M6_NONBLOCKING_NO_METADATA_CANARY_PENDING_REFERENCED_CLOSEOUT"
NEXT_MAINLINE = "A1FS-V1_MainlineDistanceGateAndNextContentPopulationStep"
M5_TASK = "KET99-PK-M5_OptionalInstructionalOverlayConsumerIntegrationAndRuntimeCanary"
M5_SCHEMA = "ket99.pku.optional_overlay_consumer_canary.v1"
M5_STATUS = "PASS_KET99_PK_M5_OPTIONAL_OVERLAY_CONSUMER_CANARY_READY"
M5 = ROOT / ".local/a1fs_v1/ket99_pku_m5/optional_overlay_consumer_canary.safe.json"
OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m6/real_private_lesson_canary.closeout.json"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def build_artifact(m5: Mapping[str, Any]) -> dict[str, Any]:
    if (
        m5.get("ket99_pku_m5_task_id") != M5_TASK
        or m5.get("ket99_pku_m5_schema_version") != M5_SCHEMA
        or m5.get("ket99_pku_m5_validation_status") != M5_STATUS
    ):
        raise ValueError("m5_contract_invalid")
    if m5.get("errors") != [] or m5.get("stop_reason") != "NONE":
        raise ValueError("m5_not_passed")
    unified = m5.get("unified_lesson_composition")
    if not isinstance(unified, Mapping):
        raise ValueError("m5_composition_missing")
    gate = unified.get("consumer_gate", {})
    if (
        gate.get("ket99_pku_optional_overlay_connected") is not True
        or gate.get("ket99_pku_metadata_canary_passed") is not True
        or gate.get("ket_asset_body_required") is not True
        or gate.get("missing_pku_reference_blocks_delivery") is not False
        or gate.get("a2_payload_included") is not False
    ):
        raise ValueError("m5_consumer_gate_invalid")
    items = unified.get("composition_items")
    if not isinstance(items, list):
        raise ValueError("m5_composition_items_invalid")
    ket_count = sum(
        isinstance(row, Mapping) and row.get("source_kind") == "KET_ASSET_BODY"
        for row in items
    )
    if ket_count < 1:
        raise ValueError("real_private_ket_asset_missing")

    coverage = unified.get("coverage_summary", {})
    before = coverage.get("composition_item_count_before_pku_overlay")
    after = coverage.get("composition_item_count_after_pku_overlay")
    if before != after or after != len(items):
        raise ValueError("composition_item_count_delta_invalid")
    delivery_before = coverage.get("delivery_allowed_count_before_pku_overlay")
    delivery_after = coverage.get("delivery_allowed_count_after_pku_overlay")
    if delivery_before != delivery_after:
        raise ValueError("delivery_allowed_count_delta_invalid")

    overlay = unified.get("ket99_pku_optional_overlay")
    if not isinstance(overlay, Mapping):
        raise ValueError("m5_optional_overlay_missing")
    references = overlay.get("optional_pilot_references")
    if (
        not isinstance(references, list)
        or overlay.get("optional_reference_count") != len(references)
    ):
        raise ValueError("m5_optional_reference_count_invalid")
    if (
        overlay.get("composition_item_count_delta") != 0
        or overlay.get("delivery_allowed_count_delta") != 0
        or overlay.get("missing_reference_blocks_delivery") is not False
        or overlay.get("hard_lesson_selection_changed") is not False
        or overlay.get("production_mapping_allowed") is not False
    ):
        raise ValueError("m5_overlay_boundary_invalid")
    for reference in references:
        if (
            not isinstance(reference, Mapping)
            or reference.get("runtime_effect")
            != "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY"
            or reference.get("hard_lesson_selection_allowed") is not False
            or reference.get("production_mapping_allowed") is not False
        ):
            raise ValueError("m5_reference_boundary_invalid")

    boundaries = m5.get("claim_boundaries", {})
    if (
        boundaries.get("hard_lesson_selection_changed") is not False
        or boundaries.get("production_mapping_claimed") is not False
        or boundaries.get("a2_a2plus_in_scope") is not False
    ):
        raise ValueError("m5_claim_boundary_invalid")
    level = str(unified.get("selected_level") or "")
    if level not in {"A1", "A1+"}:
        raise ValueError("selected_level_out_of_scope")

    closeout = bool(references)
    status = PASS_CLOSEOUT if closeout else PASS_PENDING
    canary_class = (
        "REFERENCED_PRIVATE_LESSON_CANARY"
        if closeout
        else "NONBLOCKING_NO_METADATA_PRIVATE_LESSON_CANARY"
    )
    result = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": status,
        "source_identity": {"m5_private_canary_sha256": digest(m5)},
        "real_private_lesson_canary": {
            "selected_lesson_id": str(unified.get("selected_lesson_id") or ""),
            "selected_skill": str(unified.get("selected_skill") or ""),
            "selected_level": level,
            "canary_class": canary_class,
            "ket_asset_count": ket_count,
            "composition_item_count": len(items),
            "delivery_allowed_count": int(delivery_after or 0),
            "optional_pku_reference_count": len(references),
            "optional_pku_ids": sorted({
                str(reference.get("pku_id") or "")
                for reference in references
                if str(reference.get("pku_id") or "")
            }),
            "composition_item_count_delta": 0,
            "delivery_allowed_count_delta": 0,
            "missing_reference_blocks_delivery": False,
            "hard_lesson_selection_changed": False,
            "production_mapping_count": 0,
            "a2_payload_included": False,
        },
        "pilot_closeout": {
            "closeout_allowed": closeout,
            "closeout_status": (
                "CLOSED_REFERENCED_CANARY_PROVEN"
                if closeout
                else "PENDING_REFERENCED_CANARY"
            ),
            "synthetic_test_only": False,
            "real_private_input_required": True,
        },
        "claim_boundaries": {
            "learner_attempt_created": False,
            "learner_evidence_created": False,
            "mastery_or_retention_claimed": False,
            "production_mapping_claimed": False,
            "hard_graph_modified": False,
            "hard_lesson_selection_changed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": (
            "NONE" if closeout else "REAL_REFERENCED_PRIVATE_CANARY_REQUIRED"
        ),
        "next_short_step": NEXT_MAINLINE if closeout else TASK_ID,
    }
    result["artifact_sha256"] = digest(result)
    return result


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
    parser.add_argument("--m5", type=Path, default=M5)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.m5))
    write(args.output, artifact)
    print(json.dumps(artifact, indent=2))
    return 0 if artifact["pilot_closeout"]["closeout_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
