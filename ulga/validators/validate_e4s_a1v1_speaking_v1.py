#!/usr/bin/env python3
"""Independently validate private/local E4S A1V1 Speaking V1 artifacts."""
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

from ulga.builders import build_e4s_a1v1_speaking_v1 as builder  # noqa: E402

TASK_ID = builder.TASK_ID
PASS_STATUS = builder.PASS_STATUS
ARTIFACT_FILES = {
    "queue": "speaking_capture_queue.private.json",
    "payload": "speaking_learner_safe_payload.json",
    "evidence": "speaking_evidence_input.private.json",
    "bank": "speaking_private_review_bank.json",
    "query": "speaking_query_index.private.json",
    "safe_report": "speaking_safe_report.json",
}


def _schema_check(filename: str, value: Mapping[str, Any], errors: list[str]) -> None:
    try:
        import jsonschema
        schema = builder.read_json(REPO_ROOT / "ulga/schemas" / filename)
        jsonschema.Draft202012Validator(schema).validate(value)
    except ImportError:
        errors.append("jsonschema_dependency_missing")
    except Exception as exc:
        errors.append(f"schema_validation_failed:{filename}:{exc}")


def _report(errors: list[str], safe_status: str | None = None) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL_M06_SPEAKING_V1_VALIDATION",
        "safe_artifact_status": safe_status,
        "error_count": len(errors),
        "errors": errors,
        "expected_counts": dict(builder.EXPECTED_COUNTS),
        "claim_boundaries": {
            "canonical_authority_writes": 0,
            "public_delivery_count": 0,
            "learner_mastery_claims": 0,
            "persistent_learner_state_writes": 0,
            "asr_enabled": False,
        },
        "next_resume_task": builder.NEXT_RESUME_TASK if not errors else None,
    }


def validate(output_root: Path) -> dict[str, Any]:
    root = output_root.resolve()
    errors: list[str] = []
    artifacts: dict[str, dict[str, Any]] = {}
    for key, filename in ARTIFACT_FILES.items():
        path = root / filename
        if key == "evidence" and not path.exists():
            path = root / "speaking_evidence_input.template.json"
        try:
            artifacts[key] = builder.read_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"artifact_read_failed:{filename}:{exc}")
    if errors:
        return _report(errors)

    queue = artifacts["queue"]
    payload = artifacts["payload"]
    evidence = artifacts["evidence"]
    bank = artifacts["bank"]
    query = artifacts["query"]
    safe_report = artifacts["safe_report"]
    _schema_check("e4s_a1v1_speaking_capture_queue.schema.json", queue, errors)
    _schema_check("e4s_a1v1_speaking_private_review_bank.schema.json", bank, errors)
    _schema_check("e4s_a1v1_speaking_safe_report.schema.json", safe_report, errors)
    try:
        builder._scan_safe(payload, name="learner_payload")
        builder._scan_safe(safe_report, name="safe_report")
    except builder.SpeakingBuildError as exc:
        errors.append(str(exc))

    try:
        receipt = builder._require_m05_gate(root / "m05_closeout_receipt.private.json")
        source, shared, expected_items = builder._upstream()
    except (builder.SpeakingBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"upstream_gate_failed:{exc}")
        return _report(errors)

    queue_items = queue.get("items", [])
    queue_by_shared = {item.get("shared_item_id"): item for item in queue_items}
    expected_by_shared = {item.get("shared_item_id"): item for item in expected_items}
    if queue.get("item_count") != 96 or len(queue_items) != 96 or len(queue_by_shared) != 96:
        errors.append("capture_queue_count_not_96")
    if set(queue_by_shared) != set(expected_by_shared):
        errors.append("capture_queue_identity_drift")
    roles = Counter(str(item.get("item_role")) for item in queue_items)
    units = {str(item.get("grammar_unit_id")) for item in queue_items}
    rows = {str(row) for item in queue_items for row in item.get("canonical_egp_row_ids", [])}
    if roles != Counter({"practice": 72, "assessment": 24}):
        errors.append(f"role_distribution_invalid:{dict(roles)}")
    if len(units) != 24 or len(rows) != 109:
        errors.append(f"coverage_invalid:units={len(units)}:rows={len(rows)}")
    upstream_hashes = queue.get("upstream_hashes", {})
    expected_hashes = {
        "m05_closeout_receipt_sha256": builder.sha256_value(receipt),
        "speaking_source_sha256": builder.sha256_value(source),
        "shared_contract_sha256": builder.sha256_value(shared),
    }
    if upstream_hashes != expected_hashes:
        errors.append("capture_queue_upstream_hash_drift")

    if payload.get("item_count") != 96 or len(payload.get("items", [])) != 96:
        errors.append("learner_payload_count_not_96")
    payload_ids = {item.get("shared_item_id") for item in payload.get("items", [])}
    if payload_ids != set(expected_by_shared):
        errors.append("learner_payload_identity_drift")
    encoded_payload = json.dumps(payload, ensure_ascii=False).casefold()
    for expected in expected_items:
        answer = expected.get("answer_contract", {})
        for key in ("model_texts", "accepted_texts"):
            for value in answer.get(key, []) if isinstance(answer.get(key), list) else []:
                if isinstance(value, str) and value.strip() and value.casefold() in encoded_payload:
                    errors.append(f"private_value_leak:learner_payload:{expected.get('shared_item_id')}")
    if ":\\" in encoded_payload or "source_payload" in encoded_payload:
        errors.append("learner_payload_path_or_source_leak")

    if evidence.get("capture_queue_sha256") != builder.sha256_value(queue):
        errors.append("evidence_queue_hash_drift")
    try:
        rebuilt_bank, rebuilt_report, rebuilt_query = builder.build_evidence_artifacts(root, evidence)
        if bank != rebuilt_bank:
            errors.append("private_review_bank_not_reproducible")
        if safe_report != rebuilt_report:
            errors.append("safe_report_not_reproducible")
        if query != rebuilt_query:
            errors.append("query_index_not_reproducible")
    except (builder.SpeakingBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"evidence_rebuild_failed:{exc}")
        return _report(errors, str(safe_report.get("validation_status")))

    if bank.get("item_count") != 96 or len(bank.get("items", [])) != 96:
        errors.append("private_review_bank_count_not_96")
    bank_ids = {item.get("shared_item_id") for item in bank.get("items", [])}
    if bank_ids != set(expected_by_shared):
        errors.append("private_review_bank_identity_drift")
    for item in bank.get("items", []):
        claims = item.get("claim_boundaries", {})
        for key in ("learner_mastery_claimed", "persistent_learner_state_write", "canonical_authority_write", "public_delivery"):
            if claims.get(key) is not False:
                errors.append(f"false_item_claim:{item.get('shared_item_id')}:{key}")
    bank_claims = bank.get("claim_boundaries", {})
    if bank_claims.get("capture_and_review_engine_complete") is not True:
        errors.append("capture_review_engine_not_complete")
    for key in ("learner_mastery_claimed", "persistent_learner_state_write", "canonical_authority_write", "public_delivery", "asr_enabled"):
        if bank_claims.get(key) is not False:
            errors.append(f"false_bank_claim:{key}")

    report_counts = safe_report.get("counts", {})
    expected_report_counts = {
        "capture_items": 96,
        "practice_items": 72,
        "assessment_items": 24,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
    }
    for key, expected in expected_report_counts.items():
        if report_counts.get(key) != expected:
            errors.append(f"safe_report_count_drift:{key}")
    for key in ("canonical_authority_writes", "public_delivery_count", "learner_mastery_claims", "persistent_learner_state_writes"):
        if safe_report.get("claim_boundaries", {}).get(key) != 0:
            errors.append(f"safe_report_false_claim:{key}")
    if safe_report.get("claim_boundaries", {}).get("asr_enabled") is not False:
        errors.append("safe_report_false_asr_claim")
    if query.get("item_count") != 96 or len(query.get("items", [])) != 96:
        errors.append("query_index_count_not_96")
    query_ids = {item.get("shared_item_id") for item in query.get("items", [])}
    if query_ids != set(expected_by_shared):
        errors.append("query_index_identity_drift")

    try:
        html = (root / "local_recorder/index.html").read_text(encoding="utf-8").casefold()
        for required in ("getusermedia", "mediarecorder", "localstorage", "download evidence json"):
            if required not in html:
                errors.append(f"local_recorder_missing:{required}")
        for forbidden in ("answer_key", "model_text", "invoke-webrequest", "fetch('http", 'fetch("http'):
            if forbidden in html:
                errors.append(f"local_recorder_forbidden:{forbidden}")
    except OSError as exc:
        errors.append(f"local_recorder_read_failed:{exc}")

    return _report(errors, str(safe_report.get("validation_status")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    report = validate(args.output_root)
    path = args.validation_report or args.output_root / "speaking_validation.json"
    builder.write_json_atomic(path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
