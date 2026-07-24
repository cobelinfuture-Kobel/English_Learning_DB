#!/usr/bin/env python3
"""Attach selected KET99 Reading assets to the existing private CP07D consumer."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_selected_reading_teacher_delivery_remediation_assets as m4c
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "KET99-PK-M4D_SelectedReadingAssetConsumerActivationAndPrivateCanary"
SCHEMA_VERSION = "ket99.pku.selected_reading_asset_consumer_activation_canary.v1"
PASS_STATUS = "PASS_KET99_PK_M4D_SELECTED_READING_ASSET_CONSUMER_PRIVATE_CANARY_READY"
NEXT_SHORT_STEP = "KET99-PK-M4E_SelectedReadingRemediationTriggerBindingAndPrivateErrorCanary"
DEFAULT_M4C = m4c.DEFAULT_OUTPUT
DEFAULT_CP07D = cp07d.DEFAULT_OUTPUT
DEFAULT_OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4d/selected_reading_asset_consumer_canary.private.json"
DEFAULT_REPORT = ROOT / ".local/a1fs_v1/ket99_pku_m4d/selected_reading_asset_consumer_canary.validation.json"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _verify_m4c(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != digest(unsigned):
        raise ValueError("m4c_artifact_sha256_invalid")
    if (
        value.get("task_id") != m4c.TASK_ID
        or value.get("schema_version") != m4c.SCHEMA_VERSION
        or value.get("validation_status") != m4c.PASS_STATUS
        or value.get("errors") != []
        or value.get("stop_reason") != "NONE"
    ):
        raise ValueError("m4c_contract_invalid")
    counts = value.get("counts", {})
    if counts.get("authored_asset_bundle_count") != 4 or counts.get("authored_placement_count") != 11:
        raise ValueError("m4c_count_contract_invalid")
    if counts.get("teacher_delivery_activated_count") != 0 or counts.get("remediation_activated_count") != 0:
        raise ValueError("m4c_precanary_activation_invalid")


def _verify_cp07d(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if (
        value.get("cp07d_task_id") != cp07d.TASK_ID
        or value.get("cp07d_schema_version") != cp07d.SCHEMA_VERSION
        or value.get("cp07d_validation_status") != cp07d.PASS_STATUS
        or value.get("cp07d_errors") != []
        or value.get("cp07d_stop_reason") != "NONE"
    ):
        raise ValueError("cp07d_contract_invalid")
    contract = value.get("cp07d_delivery_contract")
    if not isinstance(contract, Mapping):
        raise ValueError("cp07d_delivery_contract_missing")
    lesson_id = str(contract.get("selected_lesson_id") or "")
    skill = str(contract.get("selected_skill") or "")
    level = str(contract.get("selected_level") or "")
    if not lesson_id or skill not in {"LISTENING", "SPEAKING", "READING", "WRITING"} or level not in {"A1", "A1+"}:
        raise ValueError("cp07d_selection_invalid")
    if contract.get("a2_payload_included") is not False:
        raise ValueError("cp07d_a2_boundary_invalid")
    return contract


def _teacher_projection(bundle: Mapping[str, Any]) -> dict[str, Any]:
    contract = bundle.get("teacher_delivery_contract")
    if not isinstance(contract, Mapping):
        raise ValueError(f"teacher_contract_missing:{bundle.get('asset_id')}")
    return {
        "asset_id": bundle["asset_id"],
        "pku_id": bundle["pku_id"],
        "concept_id": bundle["concept_id"],
        "title": bundle["title"],
        "skill": bundle["skill"],
        "level": bundle["level"],
        "teacher_delivery_contract": copy.deepcopy(dict(contract)),
        "content_sha256": bundle["content_sha256"],
        "required_for_delivery": False,
        "composition_item": False,
        "learner_facing_allowed": False,
        "activation_scope": "PRIVATE_CANARY_OPTIONAL_METADATA",
    }


def _remediation_projection(bundle: Mapping[str, Any]) -> dict[str, Any]:
    contract = bundle.get("remediation_contract")
    if not isinstance(contract, Mapping):
        raise ValueError(f"remediation_contract_missing:{bundle.get('asset_id')}")
    triggers = contract.get("trigger_signatures", [])
    if not isinstance(triggers, list) or not triggers:
        raise ValueError(f"remediation_trigger_missing:{bundle.get('asset_id')}")
    return {
        "support_asset_id": bundle["asset_id"],
        "pku_id": bundle["pku_id"],
        "concept_id": bundle["concept_id"],
        "trigger_signatures": sorted(str(v) for v in triggers if str(v)),
        "remediation_contract": copy.deepcopy(dict(contract)),
        "m7_consumer_task_id": m7.TASK_ID,
        "m7_consumer_schema_version": m7.SCHEMA_VERSION,
        "m7_consumer_validation_status": m7.STATUS,
        "assignment_attachment_surface": "remediation_assignments.support_asset_ids",
        "mastery_evidence_allowed": False,
        "activation_scope": "PRIVATE_CANARY_OPTIONAL_SUPPORT",
    }


def build_artifact(m4c_value: Mapping[str, Any], cp07d_value: Mapping[str, Any]) -> dict[str, Any]:
    _verify_m4c(m4c_value)
    contract = _verify_cp07d(cp07d_value)
    lesson_id = str(contract["selected_lesson_id"])
    skill = str(contract["selected_skill"])
    level = str(contract["selected_level"])
    bundles = m4c.assets_for_lesson(m4c_value, lesson_id) if skill == "READING" and level == "A1+" else []
    teacher_assets = [_teacher_projection(bundle) for bundle in bundles if "TEACHER_DELIVERY" in bundle.get("recommended_lanes", [])]
    remediation_assets = [_remediation_projection(bundle) for bundle in bundles if "REMEDIATION" in bundle.get("recommended_lanes", [])]

    result = copy.deepcopy(dict(cp07d_value))
    before_asset_digest = digest(cp07d_value.get("asset_records", []))
    before_counts_digest = digest(cp07d_value.get("counts", {}))
    delivery = result["cp07d_delivery_contract"]
    delivery["optional_teacher_delivery_assets"] = teacher_assets
    delivery["optional_teacher_delivery_asset_ids"] = [row["asset_id"] for row in teacher_assets]
    delivery["optional_teacher_delivery_activation_status"] = (
        "ACTIVATED_PRIVATE_CANARY" if teacher_assets else "NON_BLOCKING_NO_SELECTED_READING_ASSET"
    )
    result["m7_optional_remediation_asset_registry"] = remediation_assets
    result["m4d_task_id"] = TASK_ID
    result["m4d_schema_version"] = SCHEMA_VERSION
    result["m4d_validation_status"] = PASS_STATUS
    result["m4d_source_identity"] = {
        "m4c_artifact_sha256": digest(m4c_value),
        "cp07d_consumer_sha256": digest(cp07d_value),
    }
    result["m4d_private_canary"] = {
        "selected_lesson_id": lesson_id,
        "selected_skill": skill,
        "selected_level": level,
        "selected_lesson_has_authored_assets": bool(bundles),
        "teacher_delivery_asset_count": len(teacher_assets),
        "remediation_asset_count": len(remediation_assets),
        "canary_status": "PASS_REFERENCED_READING_ASSET_PRIVATE_CANARY" if bundles else "PASS_NON_BLOCKING_NO_SELECTED_READING_ASSET",
        "asset_records_digest_before": before_asset_digest,
        "asset_records_digest_after": digest(result.get("asset_records", [])),
        "counts_digest_before": before_counts_digest,
        "counts_digest_after": digest(result.get("counts", {})),
        "projected_asset_keys_before": list(contract.get("projected_asset_keys", [])),
        "projected_asset_keys_after": list(delivery.get("projected_asset_keys", [])),
        "response_capture_asset_keys_before": list(contract.get("response_capture_asset_keys", [])),
        "response_capture_asset_keys_after": list(delivery.get("response_capture_asset_keys", [])),
    }
    result["m4d_counts"] = {
        "available_m4c_bundle_count": len(m4c_value.get("asset_bundles", [])),
        "selected_lesson_bundle_count": len(bundles),
        "teacher_delivery_asset_attached_count": len(teacher_assets),
        "remediation_asset_registered_count": len(remediation_assets),
        "composition_item_delta": 0,
        "required_delivery_asset_delta": 0,
        "asset_record_delta": 0,
        "response_capture_contract_delta": 0,
        "mastery_evidence_delta": 0,
        "canonical_coverage_delta": 0,
        "a2_unlock_count": 0,
    }
    result["m4d_claim_boundaries"] = {
        "optional_metadata_connected": bool(bundles),
        "learner_facing_content_added": False,
        "composition_items_modified": False,
        "required_delivery_assets_modified": False,
        "response_capture_modified": False,
        "lesson_selection_modified": False,
        "mastery_or_retention_claimed": False,
        "pedagogical_effectiveness_proven": False,
        "a2_unlocked": False,
    }
    result["m4d_errors"] = []
    result["m4d_stop_reason"] = "NONE"
    result["m4d_next_short_step"] = NEXT_SHORT_STEP
    result["m4d_artifact_sha256"] = digest(result)
    return result


def remediation_assets_for_tags(artifact: Mapping[str, Any], tags: Sequence[str]) -> list[dict[str, Any]]:
    if artifact.get("m4d_validation_status") != PASS_STATUS:
        raise ValueError("m4d_artifact_status_invalid")
    requested = {str(value) for value in tags if str(value)}
    return [
        dict(row)
        for row in artifact.get("m7_optional_remediation_asset_registry", [])
        if requested & set(row.get("trigger_signatures", []))
    ]


def write(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        if private:
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4c-assets", type=Path, default=DEFAULT_M4C)
    parser.add_argument("--cp07d-consumer", type=Path, default=DEFAULT_CP07D)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.m4c_assets), read_json(args.cp07d_consumer))
    from ulga.validators import validate_ket99_pku_selected_reading_asset_consumer_activation_canary as validator
    report = validator.validate_paths(artifact=artifact, m4c_value=read_json(args.m4c_assets), cp07d_value=read_json(args.cp07d_consumer))
    write(args.output, artifact, private=True)
    write(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
