#!/usr/bin/env python3
"""Reconcile the real S00-S05 lineage and reclose RAZ-AI-ACL-V1 at D0.

S06 requires canonical Authority linkage, safe Sentence/Core-Sentence/Passage
roles, four-skill M2 extension records, private-source digest completeness,
combined mainline-plus-RAZ query proof, and the A2 payload lock.  It does not
claim learner release, mastery, or retention.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S06_EndToEndMainlineConsumerAcceptanceAndD0Recloseout"
SCHEMA_VERSION = "raz.ai.acl.v1.s06.end_to_end_mainline_consumer_d0_recloseout.v2"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S06_END_TO_END_MAINLINE_CONSUMER_D0_RECLOSEOUT"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_REGISTRY = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s05_material_registry/"
    "mainline_m2_consumer_extension.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s06_final_closeout/"
    "end_to_end_mainline_consumer_d0_recloseout.safe.json"
)

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "canonical_authority_write_performed_by_closeout": False,
    "mainline_private_consumer_integration_proven": True,
    "program_closeout_is_registry_capability_closeout": False,
    "learner_facing_release_approved": False,
    "learner_facing_content_created_by_closeout": False,
    "mastery_claimed": False,
    "retention_claimed": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class FinalCloseoutError(ValueError):
    """Fail-closed S05 lineage, coverage, consumer, or D0 invariant error."""


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise FinalCloseoutError("registry_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise FinalCloseoutError("registry_package_sha256_mismatch")


def _rows(package: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = package.get(key)
    if not isinstance(value, list) or not all(isinstance(row, Mapping) for row in value):
        raise FinalCloseoutError(f"registry_lane_invalid:{key}")
    return value


def _authority_sets(promoted: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    result = {
        key: set() for key in ("THEME", "VOCABULARY", "CHUNK", "PATTERN", "GRAMMAR")
    }
    for row in promoted:
        refs = row.get("authority_refs_by_type")
        if not isinstance(refs, Mapping):
            raise FinalCloseoutError("promoted_authority_refs_by_type_invalid")
        for key in result:
            values = refs.get(key, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise FinalCloseoutError(f"promoted_authority_ref_list_invalid:{key}")
            result[key].update(values)
    return result


def build_package(
    registry_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    if registry_package.get("task_id") != registry.TASK_ID:
        raise FinalCloseoutError("registry_task_id_mismatch")
    if registry_package.get("validation_status") != registry.PASS_STATUS:
        raise FinalCloseoutError("registry_validation_status_not_pass")
    if registry_package.get("errors") != []:
        raise FinalCloseoutError("registry_errors_not_empty")
    _verify_hash(registry_package)
    gate = registry_package.get("mainline_consumer_gate")
    if (
        not isinstance(gate, Mapping)
        or gate.get("decision") != "MAINLINE_M2_CONSUMER_EXTENSION_READY"
        or gate.get("ready_for_end_to_end_d0_recloseout") is not True
    ):
        raise FinalCloseoutError("mainline_consumer_gate_not_ready_for_closeout")
    summary = registry_package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise FinalCloseoutError("registry_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise FinalCloseoutError(
                f"registry_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )

    promoted = _rows(registry_package, "promoted_material_registry")
    extension = _rows(registry_package, "mainline_extension_records")
    remediation = _rows(registry_package, "remediation_queue")
    support = _rows(registry_package, "support_registry")
    rejected = _rows(registry_package, "rejected_registry")
    bindings = _rows(registry_package, "duplicate_bindings")
    lanes = promoted + remediation + support + rejected
    group_counts = Counter(
        str(row.get("semantic_duplicate_group_id") or "") for row in lanes
    )
    source_counts = Counter(str(row.get("selected_source_unit_ref") or "") for row in lanes)
    material_ids = [str(row.get("material_id") or "") for row in promoted]
    extension_keys = [str(row.get("asset_key") or "") for row in extension]
    promoted_scope_counts = Counter(
        str(row.get("candidate_cefr_scope") or "") for row in promoted
    )
    skill_counts = Counter(str(row.get("skill") or "") for row in extension)
    role_counts: Counter[str] = Counter()
    for row in promoted:
        roles = row.get("material_asset_roles")
        if not isinstance(roles, list) or not all(isinstance(value, str) for value in roles):
            raise FinalCloseoutError("promoted_material_asset_roles_invalid")
        role_counts.update(roles)
    authority_sets = _authority_sets(promoted)
    lesson_ids = {
        str(lesson_id)
        for row in extension
        for lesson_id in row.get("mainline_lesson_ids", [])
        if isinstance(lesson_id, str) and lesson_id
    }
    query_proof = registry_package.get("consumer_query_proof")
    if not isinstance(query_proof, Mapping):
        raise FinalCloseoutError("consumer_query_proof_invalid")
    combined_proof = query_proof.get("combined_origin_query")
    authority_proof = query_proof.get("authority_query")
    role_proof = query_proof.get("asset_role_query")

    promoted_authority_complete = all(
        isinstance(row.get("authority_refs_by_type"), Mapping)
        and bool(row["authority_refs_by_type"].get("THEME"))
        and bool(row["authority_refs_by_type"].get("VOCABULARY"))
        and bool(row["authority_refs_by_type"].get("GRAMMAR"))
        for row in promoted
    )
    promoted_private_source_complete = all(
        isinstance(row.get("private_source_content_sha256"), str)
        and len(row["private_source_content_sha256"]) == 64
        for row in promoted
    )
    checks = {
        "source_total_reconciles": (
            expected_scope_page_unit_count + expected_deferred_page_unit_count
            == expected_total_page_unit_count
        ),
        "scope_count_reconciles_from_identity_and_duplicates": (
            expected_semantic_identity_count + expected_duplicate_binding_count
            == expected_scope_page_unit_count
        ),
        "all_semantic_identities_in_exactly_one_lane": (
            len(lanes) == expected_semantic_identity_count
            and bool(group_counts)
            and all(group and count == 1 for group, count in group_counts.items())
            and all(source and count == 1 for source, count in source_counts.items())
        ),
        "duplicate_bindings_exact": len(bindings) == expected_duplicate_binding_count,
        "promoted_registry_nonempty": bool(promoted),
        "promoted_material_ids_complete_unique": (
            all(material_ids) and len(material_ids) == len(set(material_ids))
        ),
        "extension_asset_keys_complete_unique": (
            bool(extension_keys)
            and all(extension_keys)
            and len(extension_keys) == len(set(extension_keys))
        ),
        "promoted_scope_closed_to_a1_a1plus": (
            set(promoted_scope_counts) <= {"A1", "A1_PLUS"}
            and sum(promoted_scope_counts.values()) == len(promoted)
        ),
        "promoted_canonical_theme_vocabulary_grammar_complete": (
            promoted_authority_complete
        ),
        "promoted_private_source_digest_complete": promoted_private_source_complete,
        "sentence_role_coverage_nonzero": role_counts["SENTENCE_ASSET_CANDIDATE"] > 0,
        "core_sentence_role_coverage_nonzero": (
            role_counts["CORE_SENTENCE_ASSET_CANDIDATE"] > 0
        ),
        "passage_role_coverage_nonzero": role_counts["PASSAGE_ASSET_CANDIDATE"] > 0,
        "four_skill_extension_coverage_complete": set(skill_counts) == {
            "LISTENING", "SPEAKING", "READING", "WRITING"
        }
        and all(skill_counts[skill] > 0 for skill in skill_counts),
        "mainline_lesson_linkage_nonzero": bool(lesson_ids),
        "combined_mainline_and_raz_query_proven": (
            isinstance(combined_proof, Mapping)
            and int(combined_proof.get("mainline_match_count") or 0) > 0
            and int(combined_proof.get("raz_extension_match_count") or 0) > 0
        ),
        "authority_query_proven": (
            isinstance(authority_proof, Mapping)
            and int(authority_proof.get("raz_extension_match_count") or 0) > 0
        ),
        "asset_role_query_proven": (
            isinstance(role_proof, Mapping)
            and int(role_proof.get("raz_extension_match_count") or 0) > 0
        ),
        "a2_payload_lock_proven": query_proof.get("a2_lock_verified") is True,
        "nonpromoted_lanes_have_no_material_id": all(
            "material_id" not in row for row in remediation + support + rejected
        ),
        "registry_summary_counts_match_lanes": (
            summary.get("final_promoted_material_count") == len(promoted)
            and summary.get("mainline_extension_asset_count") == len(extension)
            and summary.get("remediation_queue_count") == len(remediation)
            and summary.get("support_registry_count") == len(support)
            and summary.get("rejected_registry_count") == len(rejected)
        ),
        "a2_a2plus_not_opened": all(
            row.get("candidate_cefr_scope") not in {"A2", "A2_PLUS"}
            for row in promoted
        ),
    }
    ready = all(checks.values())
    coverage = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "promoted_material_count": len(promoted),
        "mainline_extension_asset_count": len(extension),
        "remediation_queue_count": len(remediation),
        "support_registry_count": len(support),
        "rejected_registry_count": len(rejected),
        "promoted_cefr_scope_counts": dict(sorted(promoted_scope_counts.items())),
        "linked_theme_count": len(authority_sets["THEME"]),
        "linked_vocabulary_count": len(authority_sets["VOCABULARY"]),
        "linked_chunk_count": len(authority_sets["CHUNK"]),
        "linked_pattern_count": len(authority_sets["PATTERN"]),
        "linked_grammar_unit_count": len(authority_sets["GRAMMAR"]),
        "linked_sentence_material_count": role_counts["SENTENCE_ASSET_CANDIDATE"],
        "linked_core_sentence_material_count": role_counts[
            "CORE_SENTENCE_ASSET_CANDIDATE"
        ],
        "linked_passage_material_count": role_counts["PASSAGE_ASSET_CANDIDATE"],
        "linked_four_skill_asset_count": len(extension),
        "linked_mainline_lesson_count": len(lesson_ids),
        "mainline_extension_skill_counts": dict(sorted(skill_counts.items())),
    }
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "mainline_consumer_extension_task_id": registry_package["task_id"],
            "mainline_consumer_extension_package_sha256": registry_package[
                "package_sha256"
            ],
            "mainline_m2_index_sha256": registry_package["input_identity"][
                "mainline_m2_index_sha256"
            ],
        },
        "scope_contract": dict(registry_package["scope_contract"]),
        "coverage_reconciliation": coverage,
        "producer_to_consumer_lineage": {
            "producer": "RAZ-AI-ACL-V1-S04 safe asset role materialization",
            "authoritative_state": "S05 canonical-complete mainline extension records",
            "runtime_consumer": "A1FS-V1-M2 combined private consumer query",
            "readback": "S06 end-to-end coverage and query proof",
        },
        "consumer_contract": {
            "mainline_consumer": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
            "extension_input": "mainline_extension_records",
            "private_source_resolution": "RAZ_PAGE_UNIT_BY_SOURCE_REF_AND_SHA256",
            "canonical_authority_types": [
                "THEME", "VOCABULARY", "CHUNK", "PATTERN", "GRAMMAR"
            ],
            "material_roles": [
                "SENTENCE_ASSET_CANDIDATE",
                "CORE_SENTENCE_ASSET_CANDIDATE",
                "PASSAGE_ASSET_CANDIDATE",
            ],
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
            "learner_facing_release_status": "NOT_APPROVED_BY_THIS_PROGRAM",
        },
        "final_closeout_gate": {
            "source_checks": checks,
            "decision": (
                "RAZ_AI_ACL_V1_D0_RECLOSED_AFTER_MAINLINE_CONSUMER_FULLFIX"
                if ready else "BLOCKED_END_TO_END_MAINLINE_CONSUMER_CLOSEOUT"
            ),
            "program_status": "PASS_ACCEPTED_AND_CLOSED" if ready else "BLOCKED",
            "distance_before": "D1",
            "distance_after": "D0" if ready else "D1",
            "remaining_in_scope_blocker_count": 0 if ready else sum(
                1 for passed in checks.values() if not passed
            ),
            "a2_a2plus_status": "DEFERRED_A2_A2PLUS",
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise FinalCloseoutError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["final_closeout_gate"]["decision"],
        "program_status": package["final_closeout_gate"]["program_status"],
        "distance_after": package["final_closeout_gate"]["distance_after"],
        **package["coverage_reconciliation"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mainline-consumer-extension-package", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.mainline_consumer_extension_package)
        if not isinstance(package, Mapping):
            raise FinalCloseoutError("mainline_consumer_extension_package_not_object")
        output = build_package(package)
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (FinalCloseoutError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
