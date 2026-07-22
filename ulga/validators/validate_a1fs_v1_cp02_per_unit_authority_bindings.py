#!/usr/bin/env python3
"""Independently validate CP02 per-unit authority selections and evidence."""
from __future__ import annotations

import json
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as m02  # noqa: E402
from ulga.builders.build_a1fs_v1_cp02_per_unit_authority_bindings import (  # noqa: E402
    AUTHORITIES,
    CHUNK_PATH,
    GRAMMAR_NODES_PATH,
    NEXT_SHORT_STEP,
    PASS_STATUS,
    PATTERN_CONSTRAINT_PATH,
    PATTERN_PATH,
    ROWLESS_STRUCTURAL_UNIT_ID,
    SCHEMA_VERSION,
    TASK_ID,
    THEME_PATH,
    VOCABULARY_PATH,
    VOCABULARY_THEME_PATH,
    _normalized_phrase,
    _normalized_words,
    _plural_lemma_candidates,
)
from ulga.query.a1_a1plus_authority_scope_query import build_scope  # noqa: E402

EXPECTED_SUMMARY = {
    "learning_unit_count": 24,
    "canonical_egp_row_count": 109,
    "content_authority_lane_count": 96,
    "selected_authority_lane_count": 57,
    "pending_authority_lane_count": 39,
    "all_four_content_authorities_selected_unit_count": 0,
    "selected_unit_counts_by_authority": {
        "vocabulary": 24,
        "chunk": 1,
        "pattern": 9,
        "theme_situation": 23,
    },
    "selected_ref_counts_by_authority": {
        "vocabulary": 118,
        "chunk": 2,
        "pattern": 22,
        "theme_situation": 46,
    },
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_units() -> dict[str, Mapping[str, Any]]:
    return {row["grammar_unit_id"]: row for row in m02.build_artifact()["learning_units"]}


def _positive_examples(unit: Mapping[str, Any]) -> list[str]:
    return [str(row["text"]) for row in unit["learning_content"]["positive_examples"]]


def _evidence_by_ref(binding: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    evidence = binding.get("evidence", [])
    return {
        str(row.get("ref")): row
        for row in evidence
        if isinstance(row, Mapping) and row.get("ref")
    }


def validate_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != TASK_ID:
        errors.append("task_id_mismatch")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_mismatch")

    source_units = _source_units()
    grammar_nodes = _read(GRAMMAR_NODES_PATH)
    vocabulary = _read(VOCABULARY_PATH)
    chunks = _read(CHUNK_PATH)
    patterns = _read(PATTERN_PATH)
    constraints = _read(PATTERN_CONSTRAINT_PATH)
    themes = _read(THEME_PATH)
    vocabulary_theme_edges = _read(VOCABULARY_THEME_PATH)

    vocabulary_by_ref = {str(row["id"]): row for row in vocabulary}
    a1_vocabulary_by_label: defaultdict[str, list[str]] = defaultdict(list)
    for vocabulary_row in vocabulary:
        if str(vocabulary_row.get("cefr_level", "")).upper() == "A1":
            a1_vocabulary_by_label[
                _normalized_phrase(str(vocabulary_row.get("label") or ""))
            ].append(str(vocabulary_row["id"]))
    chunk_by_ref = {str(row["id"]): row for row in chunks}
    pattern_by_node_ref = {str(row["id"]): row for row in patterns}
    constraint_by_ref = {
        str(row["pattern_id"]): row
        for row in constraints
        if row.get("active") is True
        and row.get("generator_allowed") is True
        and str(row.get("cefr_level", "")).upper() == "A1"
    }
    theme_refs = {str(row["id"]) for row in themes}
    row_to_node = {
        str(row.get("authority_source", {}).get("source_record_id")): str(row["id"])
        for row in grammar_nodes
        if row.get("authority_source", {}).get("source_record_id")
    }
    theme_edge_keys = {
        (str(row.get("source_node_id")), str(row.get("target_node_id")))
        for row in vocabulary_theme_edges
        if float(row.get("confidence", {}).get("value") or 0.0) >= 0.9
    }

    rows = artifact.get("learning_units", [])
    if not isinstance(rows, list) or len(rows) != 24:
        errors.append("learning_unit_count_not_24")
        rows = []
    grammar_ids = [row.get("grammar_unit_id") for row in rows]
    if set(grammar_ids) != set(source_units) or len(set(grammar_ids)) != 24:
        errors.append("learning_unit_identity_mismatch")
    if [row.get("sequence_index") for row in rows] != list(range(1, 25)):
        errors.append("learning_unit_sequence_mismatch")

    selected_unit_counts: Counter[str] = Counter()
    selected_ref_counts: Counter[str] = Counter()
    selected_lane_count = 0
    all_selected_count = 0
    row_union: set[str] = set()

    expected_source_paths = {
        str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            GRAMMAR_NODES_PATH,
            VOCABULARY_PATH,
            CHUNK_PATH,
            PATTERN_PATH,
            PATTERN_CONSTRAINT_PATH,
            THEME_PATH,
            VOCABULARY_THEME_PATH,
        )
    }
    actual_source_files = artifact.get("source_identity", {}).get("source_files", [])
    actual_source_paths = {
        str(row.get("path")): str(row.get("sha256"))
        for row in actual_source_files
        if isinstance(row, Mapping)
    }
    if actual_source_paths != expected_source_paths:
        errors.append("source_identity_hash_mismatch")

    for row in rows:
        grammar_id = str(row.get("grammar_unit_id") or "")
        source = source_units.get(grammar_id)
        if source is None:
            continue
        prefix = f"unit:{grammar_id}:"
        if row.get("learning_unit_id") != source.get("learning_unit_id"):
            errors.append(prefix + "learning_unit_id_mismatch")
        if row.get("canonical_egp_row_ids") != source.get("canonical_egp_row_ids"):
            errors.append(prefix + "canonical_rows_mismatch")
        row_union.update(row.get("canonical_egp_row_ids", []))
        stage = str(source["internal_stage"])
        scope = build_scope(stage)
        allowed_refs = {
            "vocabulary": {item["id"] for item in scope["authorities"]["vocabulary"]},
            "chunk": {item["id"] for item in scope["authorities"]["chunk"]},
            "pattern": {item["id"] for item in scope["authorities"]["pattern"]},
            "theme_situation": {item["id"] for item in scope["authorities"]["theme"]},
        }
        bindings = row.get("authority_bindings", {})
        if set(bindings) != set(AUTHORITIES):
            errors.append(prefix + "authority_set_mismatch")
            continue
        selected_for_unit = 0
        for authority in AUTHORITIES:
            binding = bindings[authority]
            refs = binding.get("selected_refs", [])
            evidence_by_ref = _evidence_by_ref(binding)
            if len(refs) != len(set(refs)):
                errors.append(prefix + authority + ":duplicate_refs")
            if not set(refs) <= allowed_refs[authority]:
                errors.append(prefix + authority + ":ref_outside_scope")
            if binding.get("selection_count") != len(refs):
                errors.append(prefix + authority + ":selection_count_mismatch")
            if binding.get("allowed_pool_count") != len(allowed_refs[authority]):
                errors.append(prefix + authority + ":allowed_pool_count_mismatch")
            if refs:
                if binding.get("selection_status") != "SELECTED_AUTHORITY_BACKED":
                    errors.append(prefix + authority + ":selected_status_mismatch")
                if set(evidence_by_ref) != set(refs):
                    errors.append(prefix + authority + ":evidence_ref_mismatch")
                if binding.get("reason") is not None:
                    errors.append(prefix + authority + ":selected_reason_not_null")
                selected_for_unit += 1
                selected_lane_count += 1
                selected_unit_counts[authority] += 1
                selected_ref_counts[authority] += len(refs)
            else:
                if binding.get("selection_status") != "PENDING_SOURCE_EVIDENCE":
                    errors.append(prefix + authority + ":pending_status_mismatch")
                if binding.get("evidence") != [] or not binding.get("reason"):
                    errors.append(prefix + authority + ":pending_evidence_or_reason_invalid")

        positive_examples = _positive_examples(source)
        positive_words = [set(_normalized_words(text)) for text in positive_examples]

        vocabulary_binding = bindings["vocabulary"]
        for ref, evidence in _evidence_by_ref(vocabulary_binding).items():
            node = vocabulary_by_ref.get(ref)
            if node is None or str(node.get("cefr_level", "")).upper() != "A1":
                errors.append(prefix + f"vocabulary:invalid_node:{ref}")
                continue
            lemma = _normalized_phrase(str(node.get("label") or ""))
            indices = evidence.get("positive_example_indices", [])
            method = evidence.get("method")
            if not indices:
                errors.append(prefix + f"vocabulary:example_indices_empty:{ref}")
            for index in indices:
                if not isinstance(index, int) or not 0 <= index < len(positive_words):
                    errors.append(prefix + f"vocabulary:example_index_invalid:{ref}")
                    continue
                if method == "EXACT_UNIQUE_A1_SENSE_IN_POSITIVE_EXAMPLE":
                    if a1_vocabulary_by_label.get(lemma) != [ref]:
                        errors.append(prefix + f"vocabulary:sense_not_unique:{ref}")
                    if lemma not in positive_words[index]:
                        errors.append(prefix + f"vocabulary:exact_evidence_invalid:{ref}")
                elif method == "REGULAR_PLURAL_POSITIVE_EXAMPLE_LEMMA":
                    if a1_vocabulary_by_label.get(lemma) != [ref]:
                        errors.append(prefix + f"vocabulary:plural_sense_not_unique:{ref}")
                    if grammar_id != "GRAMMAR_REGULAR_PLURAL_NOUNS" or not any(
                        lemma in _plural_lemma_candidates(word) for word in positive_words[index]
                    ):
                        errors.append(prefix + f"vocabulary:plural_evidence_invalid:{ref}")
                else:
                    errors.append(prefix + f"vocabulary:method_invalid:{ref}")

        chunk_binding = bindings["chunk"]
        normalized_examples = [_normalized_phrase(text) for text in positive_examples]
        for ref, evidence in _evidence_by_ref(chunk_binding).items():
            node = chunk_by_ref.get(ref)
            if (
                node is None
                or str(node.get("cefr_level", "")).upper() != "A1"
                or node.get("metadata", {}).get("generator_allowed") is not True
                or evidence.get("method") != "EXACT_A1_GENERATOR_SAFE_CHUNK_IN_POSITIVE_EXAMPLE"
            ):
                errors.append(prefix + f"chunk:evidence_invalid:{ref}")
                continue
            phrase = _normalized_phrase(str(node.get("label") or ""))
            indices = evidence.get("positive_example_indices", [])
            if not indices:
                errors.append(prefix + f"chunk:example_indices_empty:{ref}")
            for index in indices:
                if not isinstance(index, int) or not 0 <= index < len(normalized_examples) or (
                    f" {phrase} " not in f" {normalized_examples[index]} "
                ):
                    errors.append(prefix + f"chunk:example_evidence_invalid:{ref}")

        grammar_node_refs = {
            row_to_node[row_id]
            for row_id in source.get("canonical_egp_row_ids", [])
            if row_id in row_to_node
        }
        pattern_binding = bindings["pattern"]
        for ref, evidence in _evidence_by_ref(pattern_binding).items():
            constraint = constraint_by_ref.get(ref)
            node = pattern_by_node_ref.get(str(evidence.get("pattern_node_id")))
            if constraint is None or node is None or constraint.get("pattern_node_id") != node.get("id"):
                errors.append(prefix + f"pattern:registry_lineage_invalid:{ref}")
                continue
            method = evidence.get("method")
            if method == "CANONICAL_EGP_ROW_TO_GRAMMAR_NODE_TO_PATTERN":
                matched = set(evidence.get("matched_grammar_node_refs", []))
                if not matched or not matched <= grammar_node_refs or not matched <= set(node.get("metadata", {}).get("grammar_refs", [])):
                    errors.append(prefix + f"pattern:grammar_lineage_invalid:{ref}")
            elif method == "ROWLESS_STRUCTURAL_EXAMPLE_TO_APPROVED_PATTERN_FAMILY":
                if (
                    grammar_id != ROWLESS_STRUCTURAL_UNIT_ID
                    or node.get("metadata", {}).get("pattern_family_id") != "family:description_demonstrative"
                ):
                    errors.append(prefix + f"pattern:rowless_lineage_invalid:{ref}")
            else:
                errors.append(prefix + f"pattern:method_invalid:{ref}")

        theme_binding = bindings["theme_situation"]
        selected_vocabulary = set(vocabulary_binding.get("selected_refs", []))
        selected_patterns = set(pattern_binding.get("selected_refs", []))
        for ref, evidence in _evidence_by_ref(theme_binding).items():
            if ref not in theme_refs or evidence.get("method") != "PATTERN_THEME_OR_HIGH_CONFIDENCE_VOCABULARY_THEME_EDGE":
                errors.append(prefix + f"theme:registry_or_method_invalid:{ref}")
                continue
            upstream = evidence.get("upstream_refs", [])
            if not upstream:
                errors.append(prefix + f"theme:upstream_empty:{ref}")
            for link in upstream:
                via = link.get("via")
                upstream_ref = link.get("ref")
                if via == "vocabulary":
                    if upstream_ref not in selected_vocabulary or (upstream_ref, ref) not in theme_edge_keys:
                        errors.append(prefix + f"theme:vocabulary_lineage_invalid:{ref}")
                elif via == "pattern":
                    pattern = pattern_by_node_ref.get(str(constraint_by_ref.get(upstream_ref, {}).get("pattern_node_id")), {})
                    if upstream_ref not in selected_patterns or ref not in pattern.get("metadata", {}).get("theme_refs", []):
                        errors.append(prefix + f"theme:pattern_lineage_invalid:{ref}")
                else:
                    errors.append(prefix + f"theme:upstream_type_invalid:{ref}")

        expected_complete = selected_for_unit == len(AUTHORITIES)
        if row.get("all_four_content_authorities_selected") is not expected_complete:
            errors.append(prefix + "all_four_selection_flag_mismatch")
        all_selected_count += expected_complete

    if len(row_union) != 109:
        errors.append("canonical_row_union_not_109")
    calculated_summary = {
        "learning_unit_count": len(rows),
        "canonical_egp_row_count": len(row_union),
        "content_authority_lane_count": len(rows) * len(AUTHORITIES),
        "selected_authority_lane_count": selected_lane_count,
        "pending_authority_lane_count": len(rows) * len(AUTHORITIES) - selected_lane_count,
        "all_four_content_authorities_selected_unit_count": all_selected_count,
        "selected_unit_counts_by_authority": {
            authority: selected_unit_counts[authority] for authority in AUTHORITIES
        },
        "selected_ref_counts_by_authority": {
            authority: selected_ref_counts[authority] for authority in AUTHORITIES
        },
    }
    if artifact.get("coverage_summary") != calculated_summary:
        errors.append("coverage_summary_not_reconciled")
    if calculated_summary != EXPECTED_SUMMARY:
        errors.append("expected_source_proven_coverage_drift")

    boundaries = artifact.get("claim_boundaries", {})
    for key in (
        "canonical_unit_identity_changed",
        "canonical_egp_mapping_changed",
        "authority_registry_changed",
        "pending_bindings_filled_without_evidence",
        "content_admission_changed",
        "four_skill_population_claimed_complete",
        "runtime_publication_claimed",
        "learner_mastery_claimed",
        "retention_confirmed",
        "a2_a2plus_in_scope",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"false_claim_boundary:{key}")

    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "errors": errors,
        "validation_counts": calculated_summary,
        "claim_boundaries": {
            "source_proven_authority_bindings_validated": not errors,
            "all_pending_authority_bindings_resolved": False,
            "content_admission_changed": False,
            "runtime_publication_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if not errors else None,
    }


def validate() -> dict[str, Any]:
    from ulga.builders.build_a1fs_v1_cp02_per_unit_authority_bindings import build_artifact

    return validate_artifact(build_artifact())


def main() -> int:
    report = validate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
