#!/usr/bin/env python3
"""Independently validate private/local E4S A1V1 Listening V1 artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_listening_v1 as builder  # noqa: E402

TASK_ID = builder.TASK_ID
PASS_STATUS = "PASS_M05_LISTENING_V1_VALIDATED"
ARTIFACT_FILES = {
    "manifest": "audio_asset_manifest.private.json",
    "bank": "listening_private_delivery_bank.json",
    "payload": "listening_learner_safe_payload.json",
    "query": "listening_query_index.private.json",
    "safe_report": "listening_safe_report.json",
}


def _safe_check(value: Any, name: str, errors: list[str]) -> None:
    try:
        builder._scan_safe(value, name=name)
    except builder.ListeningBuildError as exc:
        errors.append(str(exc))


def _schema_check(filename: str, value: Mapping[str, Any], errors: list[str]) -> None:
    try:
        import jsonschema
        schema = builder.read_json(REPO_ROOT / "ulga/schemas" / filename)
        jsonschema.Draft202012Validator(schema).validate(value)
    except ImportError:
        errors.append("jsonschema_dependency_missing")
    except Exception as exc:  # jsonschema exposes multiple validation exception types
        errors.append(f"schema_validation_failed:{filename}:{exc}")


def validate(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    root = output_root.resolve()
    artifacts: dict[str, dict[str, Any]] = {}
    for key, filename in ARTIFACT_FILES.items():
        try:
            artifacts[key] = builder.read_json(root / filename)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"artifact_read_failed:{filename}:{exc}")
    if errors:
        return _report(errors)

    manifest, bank = artifacts["manifest"], artifacts["bank"]
    payload, query, safe_report = artifacts["payload"], artifacts["query"], artifacts["safe_report"]
    _schema_check("e4s_a1v1_listening_audio_asset_manifest.schema.json", manifest, errors)
    _schema_check("e4s_a1v1_listening_private_delivery_bank.schema.json", bank, errors)
    _schema_check("e4s_a1v1_listening_safe_report.schema.json", safe_report, errors)
    _safe_check(payload, "learner_payload", errors)
    _safe_check(safe_report, "safe_report", errors)

    try:
        source, shared, expected_items = builder._upstream()
        requests = builder.read_json(root / "render_requests.private.json")
        receipt = builder._require_m04_gate(root / "m04_closeout_receipt.private.json")
    except (builder.ListeningBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"upstream_gate_failed:{exc}")
        return _report(errors)

    expected_by_activity = {item["source_item_id"]: item for item in expected_items}
    request_by_activity = {row.get("activity_id"): row for row in requests.get("requests", [])}
    assets = manifest.get("assets", [])
    asset_ids = [asset.get("audio_asset_id") for asset in assets]
    activity_ids = [asset.get("activity_id") for asset in assets]
    if len(assets) != 96 or len(set(activity_ids)) != 96:
        errors.append("audio_binding_identity_count_not_96")
    if len(set(asset_ids)) != 96:
        errors.append("duplicate_audio_asset_id")
    if set(activity_ids) != set(expected_by_activity) or set(activity_ids) != set(request_by_activity):
        errors.append("activity_identity_drift")

    expected_files = {f"{activity_id}.wav" for activity_id in expected_by_activity}
    actual_files = {path.name for path in (root / "audio").glob("*.wav") if path.is_file()}
    if expected_files - actual_files:
        errors.append(f"missing_audio_count:{len(expected_files - actual_files)}")
    if actual_files - expected_files:
        errors.append(f"extra_audio_count:{len(actual_files - expected_files)}")

    roles: Counter[str] = Counter()
    units: set[str] = set()
    rows: set[str] = set()
    for asset in assets:
        activity_id = asset.get("activity_id")
        expected = expected_by_activity.get(activity_id)
        request = request_by_activity.get(activity_id)
        if not expected or not request:
            continue
        if asset.get("shared_item_id") != expected.get("shared_item_id"):
            errors.append(f"wrong_shared_item_join:{activity_id}")
        transcript = expected.get("answer_contract", {}).get("transcript_text", "")
        expected_transcript_hash = __import__("hashlib").sha256(transcript.encode("utf-8")).hexdigest()
        if asset.get("transcript_sha256") != expected_transcript_hash or request.get("transcript_sha256") != expected_transcript_hash:
            errors.append(f"transcript_hash_drift:{activity_id}")
        relative = asset.get("audio_relative_path")
        try:
            path = builder._resolved_audio_path(root, relative)
            wav = builder.inspect_wav(path)
            if asset.get("wav") != wav:
                errors.append(f"wav_metadata_drift:{activity_id}")
            if asset.get("audio_sha256") != builder.sha256_file(path):
                errors.append(f"audio_hash_drift:{activity_id}")
        except (builder.ListeningBuildError, OSError, TypeError) as exc:
            errors.append(str(exc))
        for false_key in ("public_delivery", "canonical_authority_write"):
            if asset.get(false_key) is not False:
                errors.append(f"false_claim:{activity_id}:{false_key}")
        if asset.get("private_local_only") is not True or asset.get("audio_status") != "RENDERED_LOCAL_VALIDATED":
            errors.append(f"asset_status_invalid:{activity_id}")
        roles[str(asset.get("item_role"))] += 1
        units.add(str(asset.get("grammar_unit_id")))
        rows.update(str(row) for row in asset.get("canonical_egp_row_ids", []))

    if roles != Counter({"practice": 72, "assessment": 24}):
        errors.append(f"item_role_distribution_invalid:{dict(roles)}")
    if len(units) != 24 or len(rows) != 109:
        errors.append(f"coverage_invalid:units={len(units)}:rows={len(rows)}")
    if bank.get("item_count") != 96 or len(bank.get("items", [])) != 96:
        errors.append("private_bank_count_not_96")
    bank_by_id = {item.get("shared_item_id"): item for item in bank.get("items", [])}
    if len(bank_by_id) != 96 or set(bank_by_id) != {item.get("shared_item_id") for item in expected_items}:
        errors.append("private_bank_identity_drift")
    for shared_id, item in bank_by_id.items():
        if item.get("readiness", {}).get("real_skill_delivery_complete") is not True:
            errors.append(f"private_bank_delivery_not_complete:{shared_id}")
        if item.get("readiness", {}).get("actual_learner_evidence_complete") is not False:
            errors.append(f"false_learner_evidence_claim:{shared_id}")
        claims = item.get("claim_boundaries", {})
        if claims.get("learner_mastery_claimed") is not False:
            errors.append(f"false_mastery_claim:{shared_id}")
        if claims.get("persistent_learner_state_write") is not False:
            errors.append(f"false_persistent_state_claim:{shared_id}")
    boundaries = bank.get("claim_boundaries", {})
    expected_boundaries = {
        "real_skill_delivery_complete": True, "actual_learner_evidence_complete": False,
        "learner_mastery_claimed": False, "canonical_authority_write": False,
        "public_delivery": False, "persistent_learner_state_write": False,
    }
    if boundaries != expected_boundaries:
        errors.append("private_bank_claim_boundary_invalid")
    if payload.get("item_count") != 96 or len(payload.get("items", [])) != 96:
        errors.append("learner_payload_count_not_96")
    safe_payload_text = json.dumps(payload, ensure_ascii=False).casefold()
    safe_report_text = json.dumps(safe_report, ensure_ascii=False).casefold()
    for expected in expected_items:
        transcript = expected.get("answer_contract", {}).get("transcript_text", "")
        if isinstance(transcript, str) and transcript.strip():
            if transcript.casefold() in safe_payload_text:
                errors.append(f"transcript_value_leak:learner_payload:{expected.get('shared_item_id')}")
            if transcript.casefold() in safe_report_text:
                errors.append(f"transcript_value_leak:safe_report:{expected.get('shared_item_id')}")
    for item in payload.get("items", []):
        uri = item.get("audio_uri", "")
        if not isinstance(uri, str) or not uri.startswith("audio/") or Path(uri).is_absolute():
            errors.append(f"unsafe_learner_audio_uri:{item.get('shared_item_id')}")
    if query.get("item_count") != 96 or len(query.get("items", [])) != 96:
        errors.append("query_index_count_not_96")
    query_ids = {item.get("shared_item_id") for item in query.get("items", [])}
    if query_ids != {item.get("shared_item_id") for item in expected_items}:
        errors.append("query_item_identity_drift")
    report_boundaries = safe_report.get("claim_boundaries", {})
    for key in ("canonical_authority_writes", "public_delivery_count", "learner_evidence_count", "mastery_claims", "persistent_learner_state_writes"):
        if report_boundaries.get(key) != 0:
            errors.append(f"safe_report_false_claim:{key}")
    if safe_report.get("counts", {}).get("validated_wav_files") != 96:
        errors.append("safe_report_audio_count_invalid")
    expected_hashes = {
        "m04_closeout_receipt_sha256": builder.sha256_value(receipt),
        "listening_source_sha256": builder.sha256_value(source),
        "shared_contract_sha256": builder.sha256_value(shared),
        "render_requests_sha256": builder.sha256_value(requests),
    }
    if safe_report.get("input_artifact_hashes") != expected_hashes:
        errors.append("safe_report_input_hash_drift")
    html_path = root / "local_player/index.html"
    try:
        html = html_path.read_text(encoding="utf-8").lower()
        if "audio.controls=true" not in html or "localstorage" in html or "answer_key" in html or "fetch('http" in html:
            errors.append("local_player_contract_invalid")
    except OSError as exc:
        errors.append(f"local_player_read_failed:{exc}")
    return _report(errors)


def _report(errors: list[str]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL_M05_LISTENING_V1_VALIDATION",
        "error_count": len(errors), "errors": errors,
        "counts": {"expected_items": 96, "expected_practice": 72, "expected_assessment": 24, "expected_units": 24, "expected_rows": 109},
        "claim_boundaries": {"canonical_authority_writes": 0, "public_delivery_count": 0, "learner_evidence_count": 0, "mastery_claims": 0},
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    report = validate(args.output_root)
    report_path = args.validation_report or args.output_root / "listening_validation.json"
    builder.write_json_atomic(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
