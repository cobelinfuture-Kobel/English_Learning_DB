#!/usr/bin/env python3
"""Independently validate the RAZ ACL V1 integrated metadata consumer at D0."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s06_integrated_consumer_d0 as builder

PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S06_INTEGRATED_CONSUMER_D0_VALIDATION"


def validate_index(index: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if index.get("task_id") != builder.TASK_ID:
        errors.append("task_id_mismatch")
    if index.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if index.get("validation_status") != builder.PASS_STATUS:
        errors.append("validation_status_not_pass")
    if index.get("program_id") != builder.PROGRAM_ID:
        errors.append("program_id_mismatch")
    claimed = index.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        errors.append("package_sha256_invalid")
    else:
        core = dict(index)
        core.pop("package_sha256", None)
        if deep.sha256_value(core) != claimed:
            errors.append("package_sha256_mismatch")

    scope = index.get("scope_contract")
    if not isinstance(scope, Mapping):
        errors.append("scope_contract_missing")
        scope = {}
    if scope.get("levels") != ["A1", "A1+"]:
        errors.append("scope_levels_invalid")
    if scope.get("a2_a2plus_status") != "LOCKED_AND_DEFERRED":
        errors.append("a2_scope_lock_invalid")
    if scope.get("consumer_mode") != "METADATA_ONLY_PRIVATE_SOURCE_ROUTING":
        errors.append("consumer_mode_invalid")

    rows = index.get("integrated_materials")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        errors.append("integrated_materials_invalid")
        rows = []
    refs = [str(row.get("integrated_ref") or "") for row in rows]
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        errors.append("integrated_ref_missing_or_duplicate")

    source_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    authority_refs: dict[str, set[str]] = {}
    for position, row in enumerate(rows):
        source_type = str(row.get("source_type") or "")
        if source_type not in {"MAINLINE_ASSET_BODY", "RAZ_DERIVED_MATERIAL"}:
            errors.append(f"source_type_invalid:{position}")
        source_counts[source_type] += 1
        if row.get("level") not in {"A1", "A1+"}:
            errors.append(f"level_invalid:{position}")
        if row.get("learner_facing") is not False:
            errors.append(f"learner_facing_row_detected:{position}")
        skills = row.get("skills")
        roles = row.get("material_roles")
        links = row.get("authority_links")
        if not isinstance(skills, list) or not skills or len(skills) != len(set(skills)):
            errors.append(f"skills_invalid:{position}")
            skills = []
        if not isinstance(roles, list) or not roles or len(roles) != len(set(roles)):
            errors.append(f"material_roles_invalid:{position}")
            roles = []
        if not isinstance(links, list) or not all(isinstance(link, Mapping) for link in links):
            errors.append(f"authority_links_invalid:{position}")
            links = []
        if source_type == "RAZ_DERIVED_MATERIAL":
            role_counts.update(str(role) for role in roles)
            skill_counts.update(str(skill) for skill in skills)
            types = {str(link.get("authority_type") or "") for link in links}
            if not {"VOCABULARY", "GRAMMAR"} <= types:
                errors.append(f"raz_required_authority_missing:{position}")
            if "SENTENCE_CANDIDATE" not in roles:
                errors.append(f"raz_sentence_role_missing:{position}")
            if row.get("payload_access") != "PRIVATE_SOURCE_REF_REQUIRED":
                errors.append(f"raz_payload_access_invalid:{position}")
            if not row.get("source_unit_ref") or not row.get("semantic_identity_id"):
                errors.append(f"raz_lineage_missing:{position}")
            for link in links:
                authority_refs.setdefault(str(link.get("authority_type") or ""), set()).add(
                    str(link.get("authority_ref") or "")
                )
        elif source_type == "MAINLINE_ASSET_BODY":
            if row.get("payload_access") != "EXISTING_PRIVATE_M2_CONSUMER":
                errors.append(f"mainline_payload_access_invalid:{position}")
            if not row.get("lesson_id"):
                errors.append(f"mainline_lesson_id_missing:{position}")

    summary = index.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        errors.append("aggregate_summary_missing")
        summary = {}
    expected_counts = {
        "mainline_material_count": source_counts["MAINLINE_ASSET_BODY"],
        "raz_promoted_material_count": source_counts["RAZ_DERIVED_MATERIAL"],
        "integrated_material_count": len(rows),
        "linked_theme_ref_count": len(authority_refs.get("THEME", set())),
        "linked_vocabulary_ref_count": len(authority_refs.get("VOCABULARY", set())),
        "linked_chunk_ref_count": len(authority_refs.get("CHUNK", set())),
        "linked_pattern_ref_count": len(authority_refs.get("PATTERN", set())),
        "linked_grammar_ref_count": len(authority_refs.get("GRAMMAR", set())),
        "linked_sentence_candidate_count": role_counts["SENTENCE_CANDIDATE"],
        "linked_core_sentence_candidate_count": (
            role_counts["STRICT_CORE_SENTENCE_CANDIDATE"]
            + role_counts["BROAD_CORE_SENTENCE_CANDIDATE"]
        ),
        "linked_passage_candidate_count": role_counts["PASSAGE_CANDIDATE"],
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            errors.append(f"summary_count_mismatch:{key}:{summary.get(key)}:{expected}")
    if summary.get("four_skill_candidate_counts") != dict(sorted(skill_counts.items())):
        errors.append("four_skill_candidate_counts_mismatch")
    if not isinstance(summary.get("deferred_a2_a2plus_count"), int) or summary.get(
        "deferred_a2_a2plus_count"
    ) < 0:
        errors.append("deferred_a2_a2plus_count_invalid")

    gate = index.get("acceptance_gate")
    if not isinstance(gate, Mapping):
        errors.append("acceptance_gate_missing")
        gate = {}
    if gate.get("decision") != "RAZ_AI_ACL_V1_D0_ACCEPTED":
        errors.append("d0_decision_not_accepted")
    if gate.get("distance_after") != "D0":
        errors.append("distance_after_not_d0")
    if gate.get("program_status") != "PASS_ACCEPTED_AND_CLOSED":
        errors.append("program_status_not_closed")
    if gate.get("mainline_consumer_proof") is not True:
        errors.append("mainline_consumer_proof_missing")
    if gate.get("a2_lock_status") != "PASS_LOCKED":
        errors.append("a2_lock_status_not_pass")
    if gate.get("learner_facing_release_claimed") is not False:
        errors.append("learner_facing_release_claimed")

    if rows:
        raz = next((row for row in rows if row.get("source_type") == "RAZ_DERIVED_MATERIAL"), None)
        mainline = next((row for row in rows if row.get("source_type") == "MAINLINE_ASSET_BODY"), None)
        if raz is None or mainline is None:
            errors.append("integrated_source_partition_missing")
        else:
            raz_query = builder.query_index(
                index,
                source_type="RAZ_DERIVED_MATERIAL",
                level=str(raz["level"]),
                material_role="SENTENCE_CANDIDATE",
            )
            if raz_query["total_match_count"] < 1:
                errors.append("raz_query_proof_failed")
            mainline_query = builder.query_index(
                index,
                source_type="MAINLINE_ASSET_BODY",
                skill=str(mainline["skills"][0]),
            )
            if mainline_query["total_match_count"] < 1:
                errors.append("mainline_query_proof_failed")
    try:
        builder.query_index(index, level="A2")
        errors.append("a2_query_did_not_fail_closed")
    except builder.IntegratedConsumerError as exc:
        if str(exc) != "A2_QUERY_LOCKED":
            errors.append(f"a2_query_wrong_failure:{exc}")

    leakage = matching.scan_forbidden_safe_keys(index)
    errors.extend(f"safe_output:{row}" for row in leakage)
    return {
        "task_id": builder.TASK_ID,
        "schema_version": "raz.ai.acl.v1.s06.integrated_consumer_d0_validation.v1",
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "package_sha256": claimed,
        "integrated_material_count": len(rows),
        "mainline_material_count": source_counts["MAINLINE_ASSET_BODY"],
        "raz_promoted_material_count": source_counts["RAZ_DERIVED_MATERIAL"],
        "distance_after": "D0" if not errors else "D1",
        "program_status": "PASS_ACCEPTED_AND_CLOSED" if not errors else "BLOCKED",
        "a2_unlocked": False,
        "learner_facing_release_claimed": False,
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    value = json.loads(args.index.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("index_object_required")
    report = validate_index(value)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
