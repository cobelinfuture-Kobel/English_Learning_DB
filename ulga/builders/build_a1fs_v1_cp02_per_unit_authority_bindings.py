#!/usr/bin/env python3
"""Select only source-proven content authority refs for the 24 A1/A1+ units.

CP02 is a metadata-only derivation.  It never fills a lane merely to make the
matrix look complete: refs require a deterministic lineage from an approved
unit example or from the canonical EGP-row -> grammar-node -> pattern chain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as m02  # noqa: E402
from ulga.query.a1_a1plus_authority_scope_query import build_scope  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only selection of existing authority IDs with evidence lineage; no learner content is produced."

TASK_ID = "A1FS-V1-CP02_PerUnitAuthorityBackedContentBinding"
PROGRAM_ID = "A1FS-V1_A1A1PlusFourSkillUnitCurriculumPlanningAndPopulation"
SCHEMA_VERSION = "a1fs.v1.cp02.per_unit_authority_binding.v1"
PASS_STATUS = "PASS_CP02_SOURCE_PROVEN_AUTHORITY_BINDINGS_SELECTED"
NEXT_SHORT_STEP = "A1FS-V1-CP03_AuthorityGapContentPopulationAndAdmission"
OUTPUT_PATH = REPO_ROOT / "ulga/reports/a1fs_v1_cp02_per_unit_authority_bindings.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1fs_v1_cp02_per_unit_authority_bindings_validation.json"

GRAMMAR_NODES_PATH = REPO_ROOT / "ulga/graph/grammar_nodes.json"
VOCABULARY_PATH = REPO_ROOT / "ulga/graph/vocabulary_nodes.json"
CHUNK_PATH = REPO_ROOT / "ulga/graph/chunk_nodes.json"
PATTERN_PATH = REPO_ROOT / "ulga/graph/sentence_patterns.json"
PATTERN_CONSTRAINT_PATH = REPO_ROOT / "ulga/graph/pattern_vocabulary_constraints.json"
THEME_PATH = REPO_ROOT / "ulga/graph/theme_nodes.json"
VOCABULARY_THEME_PATH = REPO_ROOT / "ulga/graph/vocabulary_theme_edges.refined.json"

AUTHORITIES = ("vocabulary", "chunk", "pattern", "theme_situation")
ROWLESS_STRUCTURAL_UNIT_ID = "GRAMMAR_DEMONSTRATIVES_CONTRAST"
MAX_VOCABULARY_REFS = 12
MAX_THEME_REFS = 3


class AuthorityBindingError(ValueError):
    """Fail-closed CP02 composition error."""


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_words(value: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", value.casefold())


def _normalized_phrase(value: str) -> str:
    return " ".join(_normalized_words(value))


def _positive_examples(unit: Mapping[str, Any]) -> list[str]:
    examples = unit.get("learning_content", {}).get("positive_examples", [])
    result = [str(row.get("text") or "") for row in examples if isinstance(row, Mapping)]
    if not result or any(not text for text in result):
        raise AuthorityBindingError(f"positive_examples_invalid:{unit.get('grammar_unit_id')}")
    return result


def _unique_a1_vocabulary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    grouped: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row.get("cefr_level", "")).upper() != "A1":
            continue
        key = _normalized_phrase(str(row.get("label") or ""))
        if key:
            grouped[key].append(row)
    return {key: values[0] for key, values in grouped.items() if len(values) == 1}


def _plural_lemma_candidates(word: str) -> list[str]:
    candidates: list[str] = []
    if word.endswith("ies") and len(word) > 3:
        candidates.append(word[:-3] + "y")
    if re.search(r"(?:s|x|z|ch|sh)es$", word):
        candidates.append(word[:-2])
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        candidates.append(word[:-1])
    return list(dict.fromkeys(candidates))


def _vocabulary_binding(
    unit: Mapping[str, Any], unique_vocabulary: Mapping[str, Mapping[str, Any]], pool_count: int
) -> dict[str, Any]:
    matches: dict[str, dict[str, Any]] = {}
    grammar_id = str(unit["grammar_unit_id"])
    for example_index, text in enumerate(_positive_examples(unit)):
        for word in set(_normalized_words(text)):
            candidates = [(word, "EXACT_UNIQUE_A1_SENSE_IN_POSITIVE_EXAMPLE")]
            if grammar_id == "GRAMMAR_REGULAR_PLURAL_NOUNS":
                candidates.extend(
                    (lemma, "REGULAR_PLURAL_POSITIVE_EXAMPLE_LEMMA")
                    for lemma in _plural_lemma_candidates(word)
                )
            for lemma, method in candidates:
                row = unique_vocabulary.get(lemma)
                if not row:
                    continue
                ref = str(row["id"])
                evidence = matches.setdefault(
                    ref,
                    {
                        "ref": ref,
                        "method": method,
                        "positive_example_indices": [],
                        "source_refs": [
                            "ulga/graph/vocabulary_nodes.json",
                            f"E4S_A1V1_UNIT:{grammar_id}",
                        ],
                    },
                )
                evidence["positive_example_indices"].append(example_index)
    vocabulary_by_ref = {str(row["id"]): row for row in unique_vocabulary.values()}
    ranked = sorted(
        matches,
        key=lambda ref: (
            vocabulary_by_ref[ref].get("metadata", {}).get("frequency_rank") or 10**9,
            ref,
        ),
    )[:MAX_VOCABULARY_REFS]
    evidence = []
    for ref in ranked:
        row = matches[ref]
        row["positive_example_indices"] = sorted(set(row["positive_example_indices"]))
        evidence.append(row)
    return _binding("vocabulary", ranked, evidence, pool_count, VOCABULARY_PATH)


def _pattern_binding(
    unit: Mapping[str, Any],
    row_to_node: Mapping[str, str],
    allowed_patterns: Mapping[str, Mapping[str, Any]],
    pool_count: int,
) -> dict[str, Any]:
    grammar_nodes = {
        row_to_node[row_id]
        for row_id in unit.get("canonical_egp_row_ids", [])
        if row_id in row_to_node
    }
    evidence: list[dict[str, Any]] = []
    for pattern_id, row in allowed_patterns.items():
        metadata = row.get("metadata", {})
        matched = sorted(grammar_nodes & set(metadata.get("grammar_refs", [])))
        if matched:
            evidence.append(
                {
                    "ref": pattern_id,
                    "pattern_node_id": row["id"],
                    "method": "CANONICAL_EGP_ROW_TO_GRAMMAR_NODE_TO_PATTERN",
                    "matched_grammar_node_refs": matched,
                    "source_refs": [
                        "ulga/graph/grammar_nodes.json",
                        "ulga/graph/sentence_patterns.json",
                        "ulga/graph/pattern_vocabulary_constraints.json",
                    ],
                }
            )
    if unit["grammar_unit_id"] == ROWLESS_STRUCTURAL_UNIT_ID:
        tokens = {
            word
            for text in _positive_examples(unit)
            for word in _normalized_words(text)
        }
        if not ({"this", "that", "these", "those"} & tokens):
            raise AuthorityBindingError("rowless_demonstrative_examples_missing")
        for pattern_id, row in allowed_patterns.items():
            metadata = row.get("metadata", {})
            if metadata.get("pattern_family_id") == "family:description_demonstrative":
                evidence.append(
                    {
                        "ref": pattern_id,
                        "pattern_node_id": row["id"],
                        "method": "ROWLESS_STRUCTURAL_EXAMPLE_TO_APPROVED_PATTERN_FAMILY",
                        "matched_pattern_family_ref": "family:description_demonstrative",
                        "source_refs": [
                            f"E4S_A1V1_UNIT:{ROWLESS_STRUCTURAL_UNIT_ID}",
                            "ulga/graph/sentence_patterns.json",
                            "ulga/graph/pattern_vocabulary_constraints.json",
                        ],
                    }
                )
    by_ref = {row["ref"]: row for row in evidence}
    refs = sorted(by_ref)
    return _binding("pattern", refs, [by_ref[ref] for ref in refs], pool_count, PATTERN_CONSTRAINT_PATH)


def _chunk_binding(
    unit: Mapping[str, Any], chunks: Iterable[Mapping[str, Any]], pool_count: int
) -> dict[str, Any]:
    examples = [_normalized_phrase(text) for text in _positive_examples(unit)]
    evidence = []
    for row in chunks:
        if str(row.get("cefr_level", "")).upper() != "A1":
            continue
        if row.get("metadata", {}).get("generator_allowed") is not True:
            continue
        phrase = _normalized_phrase(str(row.get("label") or ""))
        if len(phrase.split()) < 2:
            continue
        matched_indices = [
            index
            for index, text in enumerate(examples)
            if f" {phrase} " in f" {text} "
        ]
        if matched_indices:
            evidence.append(
                {
                    "ref": row["id"],
                    "method": "EXACT_A1_GENERATOR_SAFE_CHUNK_IN_POSITIVE_EXAMPLE",
                    "positive_example_indices": matched_indices,
                    "source_refs": [
                        "ulga/graph/chunk_nodes.json",
                        f"E4S_A1V1_UNIT:{unit['grammar_unit_id']}",
                    ],
                }
            )
    evidence.sort(key=lambda row: row["ref"])
    return _binding("chunk", [row["ref"] for row in evidence], evidence, pool_count, CHUNK_PATH)


def _theme_binding(
    pattern_binding: Mapping[str, Any],
    vocabulary_binding: Mapping[str, Any],
    patterns_by_authority_id: Mapping[str, Mapping[str, Any]],
    vocabulary_theme_edges: Iterable[Mapping[str, Any]],
    allowed_theme_refs: set[str],
    pool_count: int,
) -> dict[str, Any]:
    score: Counter[str] = Counter()
    lineage: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for pattern_ref in pattern_binding.get("selected_refs", []):
        pattern = patterns_by_authority_id[pattern_ref]
        for theme_ref in pattern.get("metadata", {}).get("theme_refs", []):
            if theme_ref in allowed_theme_refs:
                score[theme_ref] += 10
                lineage[theme_ref].append({"via": "pattern", "ref": pattern_ref})
    selected_vocabulary = set(vocabulary_binding.get("selected_refs", []))
    for edge in vocabulary_theme_edges:
        theme_ref = str(edge.get("target_node_id") or "")
        vocabulary_ref = str(edge.get("source_node_id") or "")
        if vocabulary_ref not in selected_vocabulary or theme_ref not in allowed_theme_refs:
            continue
        if float(edge.get("confidence", {}).get("value") or 0.0) < 0.9:
            continue
        score[theme_ref] += 1
        lineage[theme_ref].append({"via": "vocabulary", "ref": vocabulary_ref})
    refs = [ref for ref, _ in sorted(score.items(), key=lambda item: (-item[1], item[0]))[:MAX_THEME_REFS]]
    evidence = [
        {
            "ref": ref,
            "method": "PATTERN_THEME_OR_HIGH_CONFIDENCE_VOCABULARY_THEME_EDGE",
            "upstream_refs": sorted(lineage[ref], key=lambda row: (row["via"], row["ref"])),
            "source_refs": [
                "ulga/graph/sentence_patterns.json",
                "ulga/graph/vocabulary_theme_edges.refined.json",
                "ulga/graph/theme_nodes.json",
            ],
        }
        for ref in refs
    ]
    return _binding("theme_situation", refs, evidence, pool_count, THEME_PATH)


def _binding(
    authority: str,
    refs: list[str],
    evidence: list[Mapping[str, Any]],
    pool_count: int,
    source_path: Path,
) -> dict[str, Any]:
    if refs:
        return {
            "selection_status": "SELECTED_AUTHORITY_BACKED",
            "selected_refs": refs,
            "selection_count": len(refs),
            "evidence": evidence,
            "allowed_pool_count": pool_count,
            "source_query_ref": str(source_path.relative_to(REPO_ROOT)),
            "reason": None,
        }
    return {
        "selection_status": "PENDING_SOURCE_EVIDENCE",
        "selected_refs": [],
        "selection_count": 0,
        "evidence": [],
        "allowed_pool_count": pool_count,
        "source_query_ref": str(source_path.relative_to(REPO_ROOT)),
        "reason": f"NO_SOURCE_PROVEN_PER_UNIT_{authority.upper()}_REF_DO_NOT_INVENT_MAPPING",
    }


def build_artifact() -> dict[str, Any]:
    units = m02.build_artifact()
    grammar_nodes = _read(GRAMMAR_NODES_PATH)
    vocabulary = _read(VOCABULARY_PATH)
    chunks = _read(CHUNK_PATH)
    patterns = _read(PATTERN_PATH)
    constraints = _read(PATTERN_CONSTRAINT_PATH)
    vocabulary_theme_edges = _read(VOCABULARY_THEME_PATH)

    row_to_node = {
        str(row.get("authority_source", {}).get("source_record_id")): str(row["id"])
        for row in grammar_nodes
        if row.get("authority_source", {}).get("source_record_id")
    }
    allowed_pattern_nodes = {
        str(row["pattern_node_id"]): str(row["pattern_id"])
        for row in constraints
        if row.get("active") is True
        and row.get("generator_allowed") is True
        and str(row.get("cefr_level", "")).upper() == "A1"
    }
    patterns_by_authority_id = {
        allowed_pattern_nodes[str(row["id"])]: row
        for row in patterns
        if str(row.get("id")) in allowed_pattern_nodes
    }
    if len(patterns_by_authority_id) != 27:
        raise AuthorityBindingError("allowed_pattern_identity_not_27")
    unique_vocabulary = _unique_a1_vocabulary(vocabulary)

    rows = []
    selected_binding_counts: Counter[str] = Counter()
    selected_ref_counts: Counter[str] = Counter()
    for unit in units["learning_units"]:
        scope = build_scope(str(unit["internal_stage"]))
        counts = scope["counts"]
        pattern_binding = _pattern_binding(
            unit, row_to_node, patterns_by_authority_id, counts["pattern"]
        )
        vocabulary_binding = _vocabulary_binding(unit, unique_vocabulary, counts["vocabulary"])
        chunk_binding = _chunk_binding(unit, chunks, counts["chunk"])
        allowed_theme_refs = {row["id"] for row in scope["authorities"]["theme"]}
        theme_binding = _theme_binding(
            pattern_binding,
            vocabulary_binding,
            patterns_by_authority_id,
            vocabulary_theme_edges,
            allowed_theme_refs,
            counts["theme"],
        )
        bindings = {
            "vocabulary": vocabulary_binding,
            "chunk": chunk_binding,
            "pattern": pattern_binding,
            "theme_situation": theme_binding,
        }
        for authority, binding in bindings.items():
            if binding["selection_status"] == "SELECTED_AUTHORITY_BACKED":
                selected_binding_counts[authority] += 1
                selected_ref_counts[authority] += binding["selection_count"]
        rows.append(
            {
                "learning_unit_id": unit["learning_unit_id"],
                "grammar_unit_id": unit["grammar_unit_id"],
                "sequence_index": unit["sequence_index"],
                "internal_stage": unit["internal_stage"],
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "authority_bindings": bindings,
                "all_four_content_authorities_selected": all(
                    binding["selection_status"] == "SELECTED_AUTHORITY_BACKED"
                    for binding in bindings.values()
                ),
            }
        )

    selected_total = sum(selected_binding_counts.values())
    summary = {
        "learning_unit_count": len(rows),
        "canonical_egp_row_count": len(
            {row_id for row in rows for row_id in row["canonical_egp_row_ids"]}
        ),
        "content_authority_lane_count": len(rows) * len(AUTHORITIES),
        "selected_authority_lane_count": selected_total,
        "pending_authority_lane_count": len(rows) * len(AUTHORITIES) - selected_total,
        "all_four_content_authorities_selected_unit_count": sum(
            row["all_four_content_authorities_selected"] for row in rows
        ),
        "selected_unit_counts_by_authority": {
            authority: selected_binding_counts[authority] for authority in AUTHORITIES
        },
        "selected_ref_counts_by_authority": {
            authority: selected_ref_counts[authority] for authority in AUTHORITIES
        },
    }
    source_paths = (
        GRAMMAR_NODES_PATH,
        VOCABULARY_PATH,
        CHUNK_PATH,
        PATTERN_PATH,
        PATTERN_CONSTRAINT_PATH,
        THEME_PATH,
        VOCABULARY_THEME_PATH,
    )
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "metadata_only_per_unit_authority_backed_content_bindings",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "unit_contract_task_id": units["task_id"],
            "source_files": [
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "sha256": _sha256(path),
                }
                for path in source_paths
            ],
        },
        "coverage_summary": summary,
        "learning_units": rows,
        "claim_boundaries": {
            "canonical_unit_identity_changed": False,
            "canonical_egp_mapping_changed": False,
            "authority_registry_changed": False,
            "pending_bindings_filled_without_evidence": False,
            "content_admission_changed": False,
            "four_skill_population_claimed_complete": False,
            "runtime_publication_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact = build_artifact()
    from ulga.validators.validate_a1fs_v1_cp02_per_unit_authority_bindings import validate_artifact

    report = validate_artifact(artifact)
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
