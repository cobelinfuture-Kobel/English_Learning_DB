#!/usr/bin/env python3
"""Independently validate R4 authority-lineage repair and re-admission outputs."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r4_authority_reference_lineage_repair_and_readmission as repair
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4

TASK_ID = repair.TASK_ID
PASS_STATUS = repair.PASS_STATUS


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{code}_not_object")
    return value


def _prefixed(values: Any, prefix: str) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value)[len(prefix):] for value in values if isinstance(value, str) and value.startswith(prefix)]


def validate(
    *,
    ontology_path: Path,
    coverage_path: Path,
    source_candidates_path: Path,
    policies_path: Path,
    graph_path: Path,
    consumer_path: Path,
    output_root: Path,
    expected_item_count: int | None = None,
    expected_project_resolution_count: int | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(output_root)
    try:
        source = read_json(source_candidates_path, "source_candidates")
        repaired = read_json(root / repair.CANDIDATE_OUTPUT, "repaired_candidates")
        bank = read_json(root / repair.BANK_OUTPUT, "repaired_bank")
        supply = read_json(root / repair.SUPPLY_OUTPUT, "repaired_supply")
        report = read_json(root / repair.REPORT_OUTPUT, "repair_report")
        graph = read_json(graph_path, "graph")
        consumer = read_json(consumer_path, "consumer")
    except ValueError as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [str(exc)]}

    graph_sha = repair.file_digest(graph_path)
    consumer_sha = repair.file_digest(consumer_path)
    if consumer.get("source_graph_sha256") != graph_sha:
        errors.append("consumer_graph_binding_mismatch")
    if graph.get("claim_boundaries", {}).get("a2_unlocked") is True:
        errors.append("graph_a2_unlocked")
    if consumer.get("claim_boundaries", {}).get("a2_unlocked") is True:
        errors.append("consumer_a2_unlocked")

    source_rows = source.get("candidates")
    repaired_rows = repaired.get("candidates")
    if not isinstance(source_rows, list) or not isinstance(repaired_rows, list):
        errors.append("candidate_rows_missing")
        source_rows = []
        repaired_rows = []
    if expected_item_count is not None and len(repaired_rows) != expected_item_count:
        errors.append(f"candidate_count_mismatch:{len(repaired_rows)}:{expected_item_count}")
    if len(source_rows) != len(repaired_rows):
        errors.append(f"candidate_denominator_changed:{len(source_rows)}:{len(repaired_rows)}")
    if repaired.get("candidates_sha256") != r4.digest(repaired_rows):
        errors.append("candidate_registry_digest_invalid")
    if repaired.get("semantic_sha256") != r4.candidate_registry_semantic_digest(repaired_rows):
        errors.append("candidate_registry_semantic_digest_invalid")

    source_by_id = {
        str(row.get("item_id")): row
        for row in source_rows
        if isinstance(row, Mapping) and row.get("item_id")
    }
    project_resolution_count = 0
    repaired_count = 0
    for row in repaired_rows:
        if not isinstance(row, Mapping):
            errors.append("repaired_candidate_not_object")
            continue
        item_id = str(row.get("item_id") or "")
        before = source_by_id.get(item_id)
        if not before:
            errors.append(f"candidate_identity_added:{item_id}")
            continue
        for field in (
            "item_id", "breadth_cell_id", "capability_id", "life_task_id", "domain",
            "level", "skill", "purpose", "task_type", "support_level",
            "initiative_level", "interaction_variation", "transfer_distance",
            "template_family", "stimulus_fingerprint", "media_payload_state",
            "provenance", "learner_contract", "private_scoring_contract",
            "validator_status",
        ):
            if row.get(field) != before.get(field):
                errors.append(f"learner_or_candidate_content_changed:{item_id}:{field}")
        if row.get("candidate_sha256") != r4.candidate_digest(row):
            errors.append(f"candidate_digest_invalid:{item_id}")
        review = row.get("authority_review")
        if not isinstance(review, Mapping):
            errors.append(f"authority_review_missing:{item_id}")
            continue
        if review.get("status") != "APPROVED":
            errors.append(f"authority_review_not_approved:{item_id}")
        if review.get("candidate_sha256") != row.get("candidate_sha256"):
            errors.append(f"authority_review_hash_mismatch:{item_id}")
        lineage = review.get("lineage_repair")
        if not isinstance(lineage, Mapping) or lineage.get("task_id") != TASK_ID:
            errors.append(f"lineage_repair_receipt_missing:{item_id}")
            continue
        if lineage.get("learner_visible_content_changed") is not False:
            errors.append(f"learner_visible_change_claim_invalid:{item_id}")
        if lineage.get("previous_candidate_sha256") != before.get("candidate_sha256"):
            errors.append(f"previous_candidate_binding_mismatch:{item_id}")

        authority_refs = row.get("authority_refs")
        if _prefixed(authority_refs, repair.M1_PREFIX) != [graph_sha]:
            errors.append(f"m1_graph_ref_invalid:{item_id}")
        if _prefixed(authority_refs, repair.M2_PREFIX) != [consumer_sha]:
            errors.append(f"m2_consumer_ref_invalid:{item_id}")
        m2_content = _prefixed(authority_refs, repair.M2_CONTENT_PREFIX)
        project_content = _prefixed(authority_refs, repair.PROJECT_CONTENT_PREFIX)
        previous_refs = _prefixed(authority_refs, repair.PROJECT_PREVIOUS_PREFIX)
        resolution = lineage.get("resolution")
        if resolution == "PROJECT_AUTHORED_CONTENT_IDENTITY_REBOUND":
            project_resolution_count += 1
            expected_project_digest = repair.digest(repair._project_content_core(row))
            if project_content != [expected_project_digest]:
                errors.append(f"project_content_digest_invalid:{item_id}")
            if previous_refs != [str(before.get("candidate_sha256") or "")]:
                errors.append(f"project_previous_candidate_ref_invalid:{item_id}")
            source_refs = row.get("source_refs")
            if not isinstance(source_refs, list) or f"{repair.PROJECT_SOURCE_PREFIX}{before.get('candidate_sha256')}" not in source_refs:
                errors.append(f"project_source_ref_invalid:{item_id}")
            if any(isinstance(value, str) and value.startswith(("M2_ASSET:", "M2_LESSON:")) for value in source_refs or []):
                errors.append(f"project_m2_source_ref_not_removed:{item_id}")
            if m2_content:
                errors.append(f"project_m2_content_ref_not_removed:{item_id}")
        else:
            if len(m2_content) != 1:
                errors.append(f"m2_content_ref_invalid:{item_id}")
            if project_content or previous_refs:
                errors.append(f"unexpected_project_content_ref:{item_id}")
        repaired_count += 1

    if expected_project_resolution_count is not None and project_resolution_count != expected_project_resolution_count:
        errors.append(
            f"project_resolution_count_mismatch:{project_resolution_count}:{expected_project_resolution_count}"
        )

    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".a1fs-r4-repaired-candidates.", suffix=".json", dir=root
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        temporary_path.write_text(
            json.dumps(repaired, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        expected_bank, expected_supply = r4.build(
            ontology_path=ontology_path,
            coverage_path=coverage_path,
            candidates_path=temporary_path,
            policies_path=policies_path,
        )
        if bank != expected_bank:
            errors.append("practice_bank_rebuild_drift")
        if supply != expected_supply:
            errors.append("supply_report_rebuild_drift")
    except Exception as exc:
        errors.append(f"readmission_rebuild_failed:{exc}")
    finally:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)

    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    if bank.get("bank_sha256") != r4.digest(bank_core):
        errors.append("practice_bank_digest_invalid")
    if bank.get("item_count") != len(repaired_rows):
        errors.append("practice_bank_item_count_invalid")
    admission_counts = supply.get("counts", {}).get("admission_status_counts")
    if admission_counts != {"APPROVED": len(repaired_rows)}:
        errors.append(f"readmission_not_all_approved:{admission_counts}")

    report_core = {key: value for key, value in report.items() if key != "report_sha256"}
    if report.get("report_sha256") != repair.digest(report_core):
        errors.append("repair_report_digest_invalid")
    if report.get("validation_status") != PASS_STATUS:
        errors.append("repair_report_status_invalid")
    if report.get("source_bindings", {}).get("source_graph_sha256") != graph_sha:
        errors.append("repair_report_graph_binding_invalid")
    if report.get("source_bindings", {}).get("source_consumer_sha256") != consumer_sha:
        errors.append("repair_report_consumer_binding_invalid")
    if report.get("counts", {}).get("authority_ref_repaired_count") != repaired_count:
        errors.append("repair_report_repaired_count_invalid")
    if report.get("counts", {}).get("project_authored_source_resolved_count") != project_resolution_count:
        errors.append("repair_report_project_count_invalid")
    if report.get("claim_boundaries", {}).get("a2_unlocked") is not False:
        errors.append("repair_report_a2_lock_invalid")
    try:
        repair.safe_scan(supply)
        repair.safe_scan(report)
    except repair.AuthorityLineageRepairError as exc:
        errors.append(f"safe_scan_failed:{exc}")

    return {
        "validation_status": PASS_STATUS if not errors else "FAIL_A1FS_V1_R4_AUTHORITY_REFERENCE_LINEAGE_REPAIR",
        "error_count": len(errors),
        "errors": errors,
        "candidate_count": len(repaired_rows),
        "authority_ref_repaired_count": repaired_count,
        "project_authored_source_resolved_count": project_resolution_count,
        "readmission_pass_count": bank.get("item_count", 0),
        "a2_unlocked": False,
        "next_short_step": repair.NEXT_SHORT_STEP if not errors else TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--source-candidates", type=Path, required=True)
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-item-count", type=int, default=289)
    parser.add_argument("--expected-project-resolution-count", type=int, default=5)
    args = parser.parse_args(argv)
    result = validate(
        ontology_path=args.ontology,
        coverage_path=args.coverage,
        source_candidates_path=args.source_candidates,
        policies_path=args.policies,
        graph_path=args.graph,
        consumer_path=args.consumer,
        output_root=args.output_root,
        expected_item_count=args.expected_item_count,
        expected_project_resolution_count=args.expected_project_resolution_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
