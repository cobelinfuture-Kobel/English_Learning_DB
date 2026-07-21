#!/usr/bin/env python3
"""Repair mislabeled R4 authority lineage and deterministically re-admit candidates.

This builder does not author or alter learner-visible content. It corrects legacy
M1/M2 authority reference labels, converts unsupported project-authored M2
content bindings into explicit project-content bindings, rebinds the hash-bound
Authority review to the repaired candidate core, and invokes the existing R4
admission gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Repairs source-lineage metadata and re-admits existing validated R4 candidate "
    "content without authoring or changing learner-visible content."
)

TASK_ID = "A1FS-V1-R4_AuthorityReferenceLineageRepairAndReadmission"
SCHEMA_VERSION = "a1fs.v1.r4.authority_reference_lineage_repair.v1"
PASS_STATUS = "PASS_A1FS_V1_R4_AUTHORITY_REFERENCE_LINEAGE_REPAIR_AND_READMISSION"
NEXT_SHORT_STEP = "A1FS-V1-R7_PlannerRedeploy198ReadingStimulusDependencyFullFix"

CANDIDATE_OUTPUT = "a1fs_v1_r4_question_candidates.authority_repaired.private.json"
BANK_OUTPUT = "a1fs_v1_r4_approved_practice_bank.authority_repaired.private.json"
SUPPLY_OUTPUT = "a1fs_v1_r4_supply_report.authority_repaired.safe.json"
REPORT_OUTPUT = "a1fs_v1_r4_authority_reference_lineage_repair.safe.json"

HEX64 = re.compile(r"^[0-9a-f]{64}$")
M1_PREFIX = "M1_GRAPH:"
M2_PREFIX = "M2_CONSUMER:"
M2_CONTENT_PREFIX = "M2_CONTENT_DIGEST:"
PROJECT_CONTENT_PREFIX = "PROJECT_CONTENT_DIGEST:"
PROJECT_PREVIOUS_PREFIX = "PROJECT_PREVIOUS_CANDIDATE_SHA256:"
PROJECT_SOURCE_PREFIX = "PROJECT_CANDIDATE:"
LINEAGE_PREFIXES = (
    M1_PREFIX,
    M2_PREFIX,
    M2_CONTENT_PREFIX,
    PROJECT_CONTENT_PREFIX,
    PROJECT_PREVIOUS_PREFIX,
)


class AuthorityLineageRepairError(ValueError):
    """Fail-closed authority-lineage repair error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityLineageRepairError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise AuthorityLineageRepairError(f"{code}_not_object")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any], *, private: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityLineageRepairError("reviewed_at_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorityLineageRepairError("reviewed_at_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AuthorityLineageRepairError("reviewed_at_timezone_required")
    return value


def _single_prefixed(values: Sequence[Any], prefix: str, code: str) -> str:
    matches = [str(value)[len(prefix):] for value in values if isinstance(value, str) and value.startswith(prefix)]
    if len(matches) != 1 or not matches[0]:
        raise AuthorityLineageRepairError(code)
    return matches[0]


def _replace_lineage_refs(
    authority_refs: Sequence[Any],
    *,
    graph_sha256: str,
    consumer_sha256: str,
    content_refs: Sequence[str],
) -> list[str]:
    retained = [
        str(value)
        for value in authority_refs
        if isinstance(value, str) and value and not value.startswith(LINEAGE_PREFIXES)
    ]
    return [
        f"{M1_PREFIX}{graph_sha256}",
        f"{M2_PREFIX}{consumer_sha256}",
        *content_refs,
        *retained,
    ]


def _asset_index(consumer: Mapping[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    result: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for raw in consumer.get("asset_records", []):
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        lesson_id = str(row.get("lesson_id") or "")
        for identity in {str(row.get("asset_key") or ""), str(row.get("asset_id") or "")} - {""}:
            result.setdefault((identity, lesson_id), []).append(row)
    return result


def _project_content_core(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "item_id": candidate.get("item_id"),
        "breadth_cell_id": candidate.get("breadth_cell_id"),
        "level": candidate.get("level"),
        "skill": candidate.get("skill"),
        "purpose": candidate.get("purpose"),
        "task_type": candidate.get("task_type"),
        "template_family": candidate.get("template_family"),
        "stimulus_fingerprint": candidate.get("stimulus_fingerprint"),
        "learner_contract": deepcopy(candidate.get("learner_contract")),
        "private_scoring_contract": deepcopy(candidate.get("private_scoring_contract")),
    }


def _old_review_is_hash_bound(candidate: Mapping[str, Any]) -> bool:
    review = candidate.get("authority_review")
    if not isinstance(review, Mapping) or review.get("status") != "APPROVED":
        return False
    expected = candidate.get("candidate_sha256")
    return isinstance(expected, str) and HEX64.fullmatch(expected) is not None and review.get("candidate_sha256") == expected and expected == r4.candidate_digest(candidate)


def _already_repaired(
    candidate: Mapping[str, Any],
    *,
    graph_sha256: str,
    consumer_sha256: str,
) -> bool:
    refs = candidate.get("authority_refs")
    review = candidate.get("authority_review")
    if not isinstance(refs, list) or not isinstance(review, Mapping):
        return False
    lineage = review.get("lineage_repair")
    return (
        f"{M1_PREFIX}{graph_sha256}" in refs
        and f"{M2_PREFIX}{consumer_sha256}" in refs
        and isinstance(lineage, Mapping)
        and lineage.get("task_id") == TASK_ID
        and review.get("candidate_sha256") == candidate.get("candidate_sha256")
        and candidate.get("candidate_sha256") == r4.candidate_digest(candidate)
    )


def repair_candidate(
    candidate: Mapping[str, Any],
    *,
    graph_sha256: str,
    consumer_sha256: str,
    assets: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    reviewer_id: str,
    reviewed_at: str,
) -> tuple[dict[str, Any], str]:
    row = deepcopy(dict(candidate))
    if _already_repaired(row, graph_sha256=graph_sha256, consumer_sha256=consumer_sha256):
        lineage = row["authority_review"]["lineage_repair"]
        return row, str(lineage.get("resolution") or "ALREADY_REPAIRED")
    if not _old_review_is_hash_bound(row):
        raise AuthorityLineageRepairError(f"previous_authority_review_not_hash_bound:{row.get('item_id')}")
    if row.get("level") not in {"A1", "A1_PLUS"}:
        raise AuthorityLineageRepairError(f"a2_or_out_of_scope_candidate:{row.get('item_id')}")

    old_sha = str(row["candidate_sha256"])
    old_review = deepcopy(dict(row["authority_review"]))
    source_refs = row.get("source_refs")
    authority_refs = row.get("authority_refs")
    if not isinstance(source_refs, list) or not isinstance(authority_refs, list):
        raise AuthorityLineageRepairError(f"source_or_authority_refs_missing:{row.get('item_id')}")

    provenance = str(row.get("provenance") or "")
    asset_ref = _single_prefixed(source_refs, "M2_ASSET:", f"m2_asset_ref_invalid:{row.get('item_id')}")
    lesson_ref = _single_prefixed(source_refs, "M2_LESSON:", f"m2_lesson_ref_invalid:{row.get('item_id')}")
    declared_digest = _single_prefixed(authority_refs, M2_CONTENT_PREFIX, f"m2_content_digest_ref_invalid:{row.get('item_id')}")
    matches = list(assets.get((asset_ref, lesson_ref), []))
    if len(matches) > 1:
        raise AuthorityLineageRepairError(f"duplicate_m2_asset_binding:{row.get('item_id')}")
    exact_content = len(matches) == 1 and str(matches[0].get("content_digest") or "") == declared_digest

    if provenance == "EXISTING_AUTHORITY_REVIEWED":
        if not exact_content:
            raise AuthorityLineageRepairError(f"existing_authority_m2_content_mismatch:{row.get('item_id')}")
        content_refs = [f"{M2_CONTENT_PREFIX}{declared_digest}"]
        resolution = "M2_AUTHORITY_LINEAGE_REBOUND"
    elif provenance == "PROJECT_AUTHORED_CANDIDATE":
        if exact_content:
            content_refs = [f"{M2_CONTENT_PREFIX}{declared_digest}"]
            resolution = "PROJECT_AUTHORED_EXACT_M2_LINEAGE_REBOUND"
        else:
            project_digest = digest(_project_content_core(row))
            content_refs = [
                f"{PROJECT_CONTENT_PREFIX}{project_digest}",
                f"{PROJECT_PREVIOUS_PREFIX}{old_sha}",
            ]
            row["source_refs"] = [
                str(value)
                for value in source_refs
                if isinstance(value, str)
                and value
                and not value.startswith(("M2_ASSET:", "M2_LESSON:"))
            ] + [f"{PROJECT_SOURCE_PREFIX}{old_sha}"]
            resolution = "PROJECT_AUTHORED_CONTENT_IDENTITY_REBOUND"
    else:
        raise AuthorityLineageRepairError(f"provenance_invalid:{row.get('item_id')}:{provenance}")

    row["authority_refs"] = _replace_lineage_refs(
        authority_refs,
        graph_sha256=graph_sha256,
        consumer_sha256=consumer_sha256,
        content_refs=content_refs,
    )
    new_sha = r4.candidate_digest(row)
    row["candidate_sha256"] = new_sha
    criteria = old_review.get("criteria")
    if not isinstance(criteria, Mapping) or not criteria or not all(criteria.values()):
        raise AuthorityLineageRepairError(f"previous_authority_criteria_not_pass:{row.get('item_id')}")
    row["authority_review"] = {
        "status": "APPROVED",
        "reviewer_id": reviewer_id,
        "reviewed_at": reviewed_at,
        "criteria": deepcopy(dict(criteria)),
        "candidate_sha256": new_sha,
        "lineage_repair": {
            "task_id": TASK_ID,
            "resolution": resolution,
            "previous_candidate_sha256": old_sha,
            "previous_reviewer_id": old_review.get("reviewer_id"),
            "operator_approved": True,
            "learner_visible_content_changed": False,
        },
    }
    return row, resolution


def repair_registry(
    *,
    candidate_registry: Mapping[str, Any],
    graph_sha256: str,
    consumer_sha256: str,
    consumer: Mapping[str, Any],
    reviewer_id: str,
    reviewed_at: str,
    expected_item_count: int | None = None,
    expected_project_resolution_count: int | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    rows = candidate_registry.get("candidates")
    if not isinstance(rows, list):
        raise AuthorityLineageRepairError("candidate_registry_candidates_missing")
    if expected_item_count is not None and len(rows) != expected_item_count:
        raise AuthorityLineageRepairError(f"candidate_count_mismatch:{len(rows)}:{expected_item_count}")
    if candidate_registry.get("candidates_sha256") != r4.digest(rows):
        raise AuthorityLineageRepairError("candidate_registry_digest_invalid")
    if candidate_registry.get("semantic_sha256") != r4.candidate_registry_semantic_digest(rows):
        raise AuthorityLineageRepairError("candidate_registry_semantic_digest_invalid")

    assets = _asset_index(consumer)
    repaired: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise AuthorityLineageRepairError("candidate_not_object")
        row, resolution = repair_candidate(
            raw,
            graph_sha256=graph_sha256,
            consumer_sha256=consumer_sha256,
            assets=assets,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
        )
        repaired.append(row)
        counts[resolution] = counts.get(resolution, 0) + 1

    project_count = counts.get("PROJECT_AUTHORED_CONTENT_IDENTITY_REBOUND", 0)
    if expected_project_resolution_count is not None and project_count != expected_project_resolution_count:
        raise AuthorityLineageRepairError(
            f"project_resolution_count_mismatch:{project_count}:{expected_project_resolution_count}"
        )

    registry = r4.candidate_registry(
        str(candidate_registry.get("ontology_sha256") or ""),
        str(candidate_registry.get("coverage_sha256") or ""),
        repaired,
    )
    return registry, dict(sorted(counts.items()))


def build_repair(
    *,
    ontology_path: Path,
    coverage_path: Path,
    candidates_path: Path,
    policies_path: Path,
    graph_path: Path,
    consumer_path: Path,
    reviewer_id: str,
    reviewed_at: str,
    expected_item_count: int | None = None,
    expected_project_resolution_count: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    reviewed_at = _timestamp(reviewed_at)
    if not reviewer_id.strip():
        raise AuthorityLineageRepairError("reviewer_id_required")
    graph_sha256 = file_digest(graph_path)
    consumer_sha256 = file_digest(consumer_path)
    graph = read_json(graph_path, "graph")
    consumer = read_json(consumer_path, "consumer")
    if consumer.get("source_graph_sha256") != graph_sha256:
        raise AuthorityLineageRepairError("consumer_graph_binding_mismatch")
    if graph.get("claim_boundaries", {}).get("a2_unlocked") is True:
        raise AuthorityLineageRepairError("graph_a2_unlocked")
    if consumer.get("claim_boundaries", {}).get("a2_unlocked") is True:
        raise AuthorityLineageRepairError("consumer_a2_unlocked")

    candidate_registry = read_json(candidates_path, "candidate_registry")
    repaired_registry, resolution_counts = repair_registry(
        candidate_registry=candidate_registry,
        graph_sha256=graph_sha256,
        consumer_sha256=consumer_sha256,
        consumer=consumer,
        reviewer_id=reviewer_id,
        reviewed_at=reviewed_at,
        expected_item_count=expected_item_count,
        expected_project_resolution_count=expected_project_resolution_count,
    )

    temporary_registry_path = Path(candidates_path).with_name(
        f".{Path(candidates_path).name}.authority_repair.tmp"
    )
    write_json_atomic(temporary_registry_path, repaired_registry, private=True)
    try:
        bank, supply = r4.build(
            ontology_path=ontology_path,
            coverage_path=coverage_path,
            candidates_path=temporary_registry_path,
            policies_path=policies_path,
        )
    finally:
        temporary_registry_path.unlink(missing_ok=True)

    candidate_count = len(repaired_registry["candidates"])
    if bank.get("item_count") != candidate_count:
        raise AuthorityLineageRepairError(
            f"readmission_not_complete:{bank.get('item_count')}:{candidate_count}"
        )
    admission_counts = supply.get("counts", {}).get("admission_status_counts", {})
    if admission_counts != {"APPROVED": candidate_count}:
        raise AuthorityLineageRepairError(f"readmission_status_invalid:{admission_counts}")

    project_resolution_count = resolution_counts.get("PROJECT_AUTHORED_CONTENT_IDENTITY_REBOUND", 0)
    report_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "source_bindings": {
            "source_candidate_registry_sha256": file_digest(candidates_path),
            "source_graph_sha256": graph_sha256,
            "source_consumer_sha256": consumer_sha256,
            "ontology_sha256": repaired_registry["ontology_sha256"],
            "coverage_sha256": repaired_registry["coverage_sha256"],
        },
        "counts": {
            "candidate_count": candidate_count,
            "authority_ref_repaired_count": candidate_count,
            "candidate_sha_recomputed_count": candidate_count,
            "readmission_pass_count": bank["item_count"],
            "readmission_fail_count": candidate_count - bank["item_count"],
            "project_authored_source_resolved_count": project_resolution_count,
            "resolution_counts": resolution_counts,
        },
        "claim_boundaries": {
            "learner_visible_content_changed": False,
            "m0_modified": False,
            "m1_modified": False,
            "m2_modified": False,
            "breadth_denominator_modified": False,
            "learner_evidence_generated": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**report_core, "report_sha256": digest(report_core)}
    return repaired_registry, bank, supply, report


def safe_scan(value: Any) -> None:
    forbidden = {
        "prompt",
        "context",
        "options",
        "accepted_texts",
        "accepted_sequence",
        "model_text",
        "model_texts",
        "rubric",
        "learner_contract",
        "private_scoring_contract",
        "response",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in forbidden:
                raise AuthorityLineageRepairError(f"private_field_leak:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            raise AuthorityLineageRepairError("absolute_path_leak")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reviewer-id", default="OPERATOR_APPROVED_A1FS_V1_R4_LINEAGE_REPAIR")
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--expected-item-count", type=int, default=289)
    parser.add_argument("--expected-project-resolution-count", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        registry, bank, supply, report = build_repair(
            ontology_path=args.ontology,
            coverage_path=args.coverage,
            candidates_path=args.candidates,
            policies_path=args.policies,
            graph_path=args.graph,
            consumer_path=args.consumer,
            reviewer_id=args.reviewer_id,
            reviewed_at=args.reviewed_at,
            expected_item_count=args.expected_item_count,
            expected_project_resolution_count=args.expected_project_resolution_count,
        )
        safe_scan(supply)
        safe_scan(report)
        root = args.output_root
        write_json_atomic(root / CANDIDATE_OUTPUT, registry, private=True)
        write_json_atomic(root / BANK_OUTPUT, bank, private=True)
        write_json_atomic(root / SUPPLY_OUTPUT, supply, private=False)
        write_json_atomic(root / REPORT_OUTPUT, report, private=False)
        print(json.dumps({
            "validation_status": report["validation_status"],
            "candidate_count": report["counts"]["candidate_count"],
            "readmission_pass_count": report["counts"]["readmission_pass_count"],
            "project_authored_source_resolved_count": report["counts"]["project_authored_source_resolved_count"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, indent=2))
        return 0
    except (AuthorityLineageRepairError, r4.QuestionSupplyError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
