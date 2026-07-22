#!/usr/bin/env python3
"""Select one deterministic high-quality representative per RAZ A-I semantic identity.

S02 consumes the verified S01 text-free admission package. It recomputes every
A-I duplicate member as a hypothetical representative, selects the strongest
candidate using Authority completeness and pedagogical utility, binds all
remaining duplicate rows, and keeps J-W deferred.

The builder does not read source text, infer CEFR from RAZ level, promote
content, or write canonical Authority.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s01_material_admission as admission

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S02_SemanticDedupAndRepresentativeSelection"
SCHEMA_VERSION = "raz.ai.acl.v1.s02.semantic_dedup_representative_selection.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S02_SEMANTIC_DEDUP_REPRESENTATIVE_SELECTION"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_ADMISSION = (
    REPO_ROOT
    / ".local/raz_ai/acl_v1_s01_material_admission/"
    / "material_admission_classification.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_ai/acl_v1_s02_semantic_dedup/"
    / "semantic_dedup_representative_selection.safe.json"
)

REPRESENTATIVE_STATUSES = {
    "A1_READY_CANDIDATE",
    "A1PLUS_READY_CANDIDATE",
    "REWRITE_REQUIRED",
    "SUPPORT_ONLY",
    "REJECTED_UNUSABLE",
}
READY_STATUSES = {"A1_READY_CANDIDATE", "A1PLUS_READY_CANDIDATE"}
STATUS_TIER = {
    "A1_READY_CANDIDATE": 4,
    "A1PLUS_READY_CANDIDATE": 4,
    "REWRITE_REQUIRED": 3,
    "SUPPORT_ONLY": 2,
    "REJECTED_UNUSABLE": 1,
}
MATURITY_TIER = {
    "STRICT_CORE_SENTENCE_SEED": 4,
    "BROAD_CORE_SENTENCE_SEED": 3,
    "PASSAGE_SUPPORT_SEED": 2,
    "SUPPORT_SENTENCE_SEED": 1,
}

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "raz_level_used_as_cefr_equivalence": False,
    "semantic_identity_dedup_performed": True,
    "representative_selection_uses_authority_and_pedagogical_signals": True,
    "human_content_approval_fabricated": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class SemanticDedupError(ValueError):
    """Fail-closed S01 package, identity, accounting, or leakage error."""


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise SemanticDedupError("admission_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise SemanticDedupError("admission_package_sha256_mismatch")


def _verify_admission(
    package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> list[Mapping[str, Any]]:
    if package.get("task_id") != admission.TASK_ID:
        raise SemanticDedupError("admission_task_id_mismatch")
    if package.get("validation_status") != admission.PASS_STATUS:
        raise SemanticDedupError("admission_validation_status_not_pass")
    if package.get("errors") != []:
        raise SemanticDedupError("admission_errors_not_empty")
    _verify_hash(package)

    gate = package.get("admission_gate")
    if (
        not isinstance(gate, Mapping)
        or gate.get("decision") != "MATERIAL_ADMISSION_CLASSIFICATION_READY"
        or gate.get("ready_for_semantic_dedup") is not True
    ):
        raise SemanticDedupError("admission_gate_not_ready_for_semantic_dedup")

    rows = package.get("admission_rows")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise SemanticDedupError("admission_rows_invalid")
    if len(rows) != expected_total_page_unit_count:
        raise SemanticDedupError(
            f"source_candidate_count_mismatch:{len(rows)}:{expected_total_page_unit_count}"
        )
    refs = [str(row.get("source_unit_ref") or "") for row in rows]
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        raise SemanticDedupError("source_unit_ref_missing_or_duplicate")

    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise SemanticDedupError("admission_aggregate_summary_missing")
    expected_summary = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_duplicate_group_count": expected_semantic_identity_count,
        "duplicate_candidate_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "final_promoted_material_count": 0,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise SemanticDedupError(
                f"admission_summary_mismatch:{key}:{summary.get(key)}:{expected}"
            )
    observed_status_counts = Counter(str(row.get("admission_status") or "") for row in rows)
    if dict(sorted(observed_status_counts.items())) != summary.get("admission_status_counts"):
        raise SemanticDedupError("admission_status_counts_mismatch")
    return rows


def _strings(row: Mapping[str, Any], key: str) -> set[str]:
    values = row.get(key, [])
    if not isinstance(values, list):
        raise SemanticDedupError(f"row_list_field_invalid:{key}")
    return {str(value) for value in values if isinstance(value, str) and value}


def _hypothetical_classification(
    row: Mapping[str, Any],
) -> tuple[str, str, list[str]]:
    ref = str(row.get("source_unit_ref") or "")
    status, scope, reasons = admission._classify_scope_row(
        row, duplicate_representative=ref
    )
    if status not in REPRESENTATIVE_STATUSES:
        raise SemanticDedupError(
            f"hypothetical_representative_status_invalid:{ref}:{status}"
        )
    return status, scope, reasons


def _quality(row: Mapping[str, Any]) -> tuple[dict[str, int], str, str, list[str]]:
    status, scope, reasons = _hypothetical_classification(row)
    vocabulary = _strings(row, "matched_vocabulary_refs")
    grammar = _strings(row, "matched_grammar_unit_refs")
    chunks = _strings(row, "matched_chunk_refs")
    patterns = _strings(row, "matched_pattern_refs")
    themes = _strings(row, "candidate_theme_refs")
    skills = _strings(row, "four_skill_affordances")
    maturity = str(row.get("sentence_seed_maturity") or "")
    vector = {
        "admission_tier": STATUS_TIER[status],
        "authority_dimension_count": sum(
            bool(values)
            for values in (vocabulary, grammar, chunks, patterns, themes)
        ),
        "matched_authority_ref_count": sum(
            len(values)
            for values in (vocabulary, grammar, chunks, patterns, themes)
        ),
        "four_skill_affordance_count": len(skills),
        "sentence_seed_maturity_tier": MATURITY_TIER.get(maturity, 0),
        "passage_support": int(row.get("passage_seed_status") == "SUPPORTED"),
        "a1plus_signal_count": sum(code.startswith("A1PLUS_") for code in reasons),
    }
    return vector, status, scope, reasons


def _rank_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    vector = candidate["quality_vector"]
    return (
        -int(vector["admission_tier"]),
        -int(vector["authority_dimension_count"]),
        -int(vector["matched_authority_ref_count"]),
        -int(vector["four_skill_affordance_count"]),
        -int(vector["sentence_seed_maturity_tier"]),
        -int(vector["passage_support"]),
        -int(vector["a1plus_signal_count"]),
        str(candidate["source_unit_ref"]),
    )


def _candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    vector, status, scope, reasons = _quality(row)
    return {
        "source_unit_ref": str(row["source_unit_ref"]),
        "row": row,
        "quality_vector": vector,
        "representative_admission_status": status,
        "candidate_cefr_scope": scope,
        "representative_reason_codes": reasons,
    }


def build_package(
    admission_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    rows = _verify_admission(
        admission_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )

    scope_rows = [
        row
        for row in rows
        if str(row.get("source_level") or "") in admission.A1_A1PLUS_LEVELS
    ]
    deferred_rows = [
        row
        for row in rows
        if str(row.get("source_level") or "") in admission.DEFERRED_LEVELS
    ]
    if len(scope_rows) != expected_scope_page_unit_count:
        raise SemanticDedupError("scope_page_unit_count_mismatch")
    if len(deferred_rows) != expected_deferred_page_unit_count:
        raise SemanticDedupError("deferred_page_unit_count_mismatch")
    if any(row.get("admission_status") != "DEFERRED_A2_A2PLUS" for row in deferred_rows):
        raise SemanticDedupError("deferred_row_status_invalid")

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in scope_rows:
        group = str(row.get("semantic_duplicate_group_id") or "")
        if not group:
            raise SemanticDedupError(
                f"semantic_duplicate_group_missing:{row.get('source_unit_ref')}"
            )
        grouped[group].append(row)
    if len(grouped) != expected_semantic_identity_count:
        raise SemanticDedupError(
            f"semantic_identity_count_mismatch:{len(grouped)}:"
            f"{expected_semantic_identity_count}"
        )

    representative_rows: list[dict[str, Any]] = []
    duplicate_bindings: list[dict[str, Any]] = []
    representative_status_counts: Counter[str] = Counter()
    changed_count = 0
    conflict_count = 0

    for group, members in sorted(grouped.items()):
        provisional_refs = {
            str(row.get("duplicate_representative_source_unit_ref") or "")
            for row in members
        }
        if len(provisional_refs) != 1 or "" in provisional_refs:
            raise SemanticDedupError(
                f"s01_provisional_representative_inconsistent:{group}"
            )
        provisional = next(iter(provisional_refs))
        member_refs = {str(row["source_unit_ref"]) for row in members}
        if provisional not in member_refs:
            raise SemanticDedupError(
                f"s01_provisional_representative_not_member:{group}:{provisional}"
            )
        s01_duplicate_count = sum(
            row.get("admission_status") == "DUPLICATE_CANDIDATE" for row in members
        )
        if s01_duplicate_count != len(members) - 1:
            raise SemanticDedupError(
                f"s01_duplicate_member_count_mismatch:{group}:"
                f"{s01_duplicate_count}:{len(members) - 1}"
            )

        candidates = [_candidate(row) for row in members]
        winner = min(candidates, key=_rank_key)
        winner_ref = str(winner["source_unit_ref"])
        winner_row = winner["row"]
        status_set = {
            str(candidate["representative_admission_status"])
            for candidate in candidates
        }
        scope_set = {
            str(candidate["candidate_cefr_scope"]) for candidate in candidates
        }
        if len(status_set) > 1 or len(scope_set) > 1:
            conflict_count += 1
        changed = winner_ref != provisional
        changed_count += int(changed)
        representative_status_counts[
            str(winner["representative_admission_status"])
        ] += 1

        same_vector_count = sum(
            candidate["quality_vector"] == winner["quality_vector"]
            for candidate in candidates
        )
        selection_reasons = ["HIGHEST_DEDUP_QUALITY_VECTOR"]
        if same_vector_count > 1:
            selection_reasons.append("SOURCE_UNIT_REF_STABLE_TIEBREAKER")

        representative_rows.append(
            {
                "semantic_duplicate_group_id": group,
                "selected_source_unit_ref": winner_ref,
                "source_level": str(winner_row.get("source_level") or ""),
                "source_book_id": str(winner_row.get("source_book_id") or ""),
                "member_count": len(members),
                "duplicate_member_count": len(members) - 1,
                "s01_provisional_representative_source_unit_ref": provisional,
                "representative_changed_from_s01": changed,
                "representative_admission_status": winner[
                    "representative_admission_status"
                ],
                "candidate_cefr_scope": winner["candidate_cefr_scope"],
                "representative_reason_codes": list(
                    winner["representative_reason_codes"]
                ),
                "selection_reason_codes": selection_reasons,
                "quality_vector": dict(winner["quality_vector"]),
                "member_hypothetical_statuses": sorted(status_set),
                "member_candidate_cefr_scopes": sorted(scope_set),
                "classification_conflict_observed": (
                    len(status_set) > 1 or len(scope_set) > 1
                ),
                "candidate_theme_refs": sorted(
                    _strings(winner_row, "candidate_theme_refs")
                ),
                "matched_vocabulary_refs": sorted(
                    _strings(winner_row, "matched_vocabulary_refs")
                ),
                "matched_chunk_refs": sorted(
                    _strings(winner_row, "matched_chunk_refs")
                ),
                "matched_pattern_refs": sorted(
                    _strings(winner_row, "matched_pattern_refs")
                ),
                "matched_grammar_unit_refs": sorted(
                    _strings(winner_row, "matched_grammar_unit_refs")
                ),
                "sentence_seed_maturity": str(
                    winner_row.get("sentence_seed_maturity") or ""
                ),
                "passage_seed_status": str(
                    winner_row.get("passage_seed_status") or ""
                ),
                "discourse_shape": str(winner_row.get("discourse_shape") or ""),
                "scene_structure": str(winner_row.get("scene_structure") or ""),
                "four_skill_affordances": sorted(
                    _strings(winner_row, "four_skill_affordances")
                ),
                "promotion_status": "NOT_PROMOTED",
            }
        )
        for member in sorted(members, key=lambda row: str(row["source_unit_ref"])):
            member_ref = str(member["source_unit_ref"])
            if member_ref == winner_ref:
                continue
            duplicate_bindings.append(
                {
                    "semantic_duplicate_group_id": group,
                    "duplicate_source_unit_ref": member_ref,
                    "representative_source_unit_ref": winner_ref,
                    "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE",
                }
            )

    representative_refs = {
        row["selected_source_unit_ref"] for row in representative_rows
    }
    duplicate_refs = {
        row["duplicate_source_unit_ref"] for row in duplicate_bindings
    }
    scope_refs = {str(row["source_unit_ref"]) for row in scope_rows}
    ready_count = sum(
        representative_status_counts[status] for status in READY_STATUSES
    )
    checks = {
        "one_representative_per_semantic_identity": (
            len(representative_rows) == expected_semantic_identity_count
            and len(representative_refs) == expected_semantic_identity_count
        ),
        "duplicate_binding_count_exact": (
            len(duplicate_bindings) == expected_duplicate_binding_count
            and len(duplicate_refs) == expected_duplicate_binding_count
        ),
        "scope_rows_reconciled": (
            representative_refs.isdisjoint(duplicate_refs)
            and representative_refs | duplicate_refs == scope_refs
        ),
        "representative_statuses_closed": all(
            row["representative_admission_status"] in REPRESENTATIVE_STATUSES
            for row in representative_rows
        ),
        "representative_status_counts_reconcile": (
            sum(representative_status_counts.values())
            == expected_semantic_identity_count
        ),
        "deferred_rows_preserved": len(deferred_rows)
        == expected_deferred_page_unit_count,
        "a2_a2plus_not_opened": all(
            row["candidate_cefr_scope"] not in {"A2", "A2_PLUS"}
            for row in representative_rows
        ),
        "no_promoted_rows": all(
            row["promotion_status"] == "NOT_PROMOTED"
            for row in representative_rows
        ),
        "ready_representatives_authority_complete": all(
            row["matched_vocabulary_refs"] and row["matched_grammar_unit_refs"]
            for row in representative_rows
            if row["representative_admission_status"] in READY_STATUSES
        ),
    }
    ready = all(checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "admission_task_id": admission_package["task_id"],
            "admission_package_sha256": admission_package["package_sha256"],
        },
        "scope_contract": {
            "a1_a1plus_observational_levels": list(admission.A1_A1PLUS_LEVELS),
            "deferred_levels": list(admission.DEFERRED_LEVELS),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "semantic_representatives": representative_rows,
        "duplicate_bindings": duplicate_bindings,
        "aggregate_summary": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": len(representative_rows),
            "representative_count": len(representative_rows),
            "duplicate_binding_count": len(duplicate_bindings),
            "deferred_a2_a2plus_count": len(deferred_rows),
            "representative_status_counts": dict(
                sorted(representative_status_counts.items())
            ),
            "a1_ready_representative_count": representative_status_counts[
                "A1_READY_CANDIDATE"
            ],
            "a1plus_ready_representative_count": representative_status_counts[
                "A1PLUS_READY_CANDIDATE"
            ],
            "rewrite_required_representative_count": representative_status_counts[
                "REWRITE_REQUIRED"
            ],
            "support_only_representative_count": representative_status_counts[
                "SUPPORT_ONLY"
            ],
            "rejected_unusable_representative_count": representative_status_counts[
                "REJECTED_UNUSABLE"
            ],
            "ready_representative_count": ready_count,
            "classification_conflict_group_count": conflict_count,
            "representative_changed_from_s01_count": changed_count,
            "final_promoted_material_count": 0,
        },
        "dedup_gate": {
            "source_checks": checks,
            "decision": (
                "SEMANTIC_DEDUP_REPRESENTATIVES_READY"
                if ready
                else "BLOCKED_SEMANTIC_DEDUP_REPRESENTATIVE_SELECTION"
            ),
            "distance_before": "D5",
            "distance_after": "D4" if ready else "D5",
            "ready_for_authority_linkage": ready,
            "ready_for_material_promotion": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise SemanticDedupError(
            "safe_output_leakage:" + ";".join(leakage[:20])
        )
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["dedup_gate"]["decision"],
        "distance_after": package["dedup_gate"]["distance_after"],
        **package["aggregate_summary"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--admission-package", type=Path, default=DEFAULT_ADMISSION
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.admission_package)
        if not isinstance(package, Mapping):
            raise SemanticDedupError("admission_package_not_object")
        output = build_package(package)
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (
        SemanticDedupError,
        admission.MaterialAdmissionError,
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
