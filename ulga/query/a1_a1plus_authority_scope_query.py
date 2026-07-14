#!/usr/bin/env python3
"""Unified read-only A1/A1+ authority scope query.

The query resolves existing Grammar, Vocabulary, Chunk, Pattern, Theme,
Situation, Skill, Question-Type, and source-evidence layers without mutating
canonical graph data or joining learner state.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_text_mode_package,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR_QUERY_PATH = REPO_ROOT / "ulga/graph/grammar_query_index.json"
VOCABULARY_PATH = REPO_ROOT / "ulga/graph/vocabulary_nodes.json"
CHUNK_PATH = REPO_ROOT / "ulga/graph/chunk_nodes.json"
PATTERN_PATH = REPO_ROOT / "ulga/graph/sentence_patterns.json"
PATTERN_CONSTRAINT_PATH = REPO_ROOT / "ulga/graph/pattern_vocabulary_constraints.json"
THEME_PATH = REPO_ROOT / "ulga/graph/theme_nodes.json"
TEXT_MODE_PACKAGE_PATH = REPO_ROOT / "ulga/graph/a1_grammar_text_mode_private_pilot_package.json"
TEXT_MODE_PACKAGE_BUILDER_REF = (
    "ulga/builders/build_a1_grammar_text_mode_private_pilot_package.py"
)

TASK_ID = "E4S-A1V1-M01_AuthorityScopeAndQueryCompleteness"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
VALID_STAGES = ("A1", "A1_PLUS")
AUTHORITIES = (
    "grammar",
    "vocabulary",
    "chunk",
    "pattern",
    "theme",
    "situation",
    "skill",
    "question_type",
    "source_evidence",
)
MAX_LIMIT = 200


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"required authority artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_stage(value: str | None) -> str:
    stage = str(value or "A1").strip().upper().replace("+", "_PLUS")
    if stage not in VALID_STAGES:
        raise ValueError(f"OUT_OF_SCOPE_LEVEL_STAGE:{value}")
    return stage


def _source_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    source = row.get("authority_source", {})
    if not isinstance(source, Mapping):
        return {}
    return {
        "source_name": source.get("source_name"),
        "source_file": source.get("source_file"),
        "source_record_id": source.get("source_record_id"),
        "derivation": source.get("derivation"),
    }


def _is_a1(row: Mapping[str, Any]) -> bool:
    return str(row.get("cefr_level", "")).upper() == "A1"


def _load_package() -> tuple[dict[str, Any], str]:
    if TEXT_MODE_PACKAGE_PATH.exists():
        return _read_json(TEXT_MODE_PACKAGE_PATH), str(
            TEXT_MODE_PACKAGE_PATH.relative_to(REPO_ROOT)
        )
    artifact, report = build_text_mode_package()
    if report.get("validation_status") != "PASS":
        raise RuntimeError("text_mode_package_rebuild_validation_failed")
    return artifact, TEXT_MODE_PACKAGE_BUILDER_REF


def _grammar_rows(payload: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    canonical = payload.get("canonical_a1", {})
    by_row = payload.get("by_egp_row_id", {})
    rows = []
    for row_id in canonical.get("canonical_egp_row_ids", []):
        raw = by_row.get(row_id)
        if isinstance(raw, list):
            grammar_ids = [str(value) for value in raw]
        elif isinstance(raw, Mapping):
            grammar_ids = [
                str(value)
                for value in raw.get("grammar_ids", raw.get("grammar_unit_ids", []))
            ]
        else:
            grammar_ids = []
        rows.append(
            {
                "id": row_id,
                "authority": "grammar",
                "official_cefr_level": "A1",
                "internal_stage": stage,
                "grammar_ids": grammar_ids,
                "coverage_status": canonical.get("coverage_status"),
                "source_ref": {
                    "source_file": "ulga/graph/grammar_query_index.json",
                    "source_record_id": row_id,
                    "derivation": "canonical_a1_query_index",
                },
            }
        )
    return rows


def _vocabulary_rows(payload: Iterable[Mapping[str, Any]], stage: str) -> list[dict[str, Any]]:
    rows = []
    for row in payload:
        if not _is_a1(row):
            continue
        metadata = row.get("metadata", {})
        rows.append(
            {
                "id": row.get("id"),
                "authority": "vocabulary",
                "label": row.get("label"),
                "official_cefr_level": "A1",
                "internal_stage": stage,
                "part_of_speech": metadata.get("part_of_speech"),
                "frequency_rank": metadata.get("frequency_rank"),
                "frequency_score": metadata.get("frequency_score"),
                "source_ref": _source_ref(row),
            }
        )
    return rows


def _chunk_rows(payload: Iterable[Mapping[str, Any]], stage: str) -> list[dict[str, Any]]:
    rows = []
    for row in payload:
        metadata = row.get("metadata", {})
        if not _is_a1(row) or metadata.get("generator_allowed") is not True:
            continue
        rows.append(
            {
                "id": row.get("id"),
                "authority": "chunk",
                "label": row.get("label"),
                "official_cefr_level": "A1",
                "internal_stage": stage,
                "usage_class": metadata.get("usage_class"),
                "theme_hints": list(metadata.get("theme_hint", [])),
                "priority_band": metadata.get("priority_band"),
                "frequency_proxy_score": metadata.get("frequency_proxy_score"),
                "generator_allowed": True,
                "source_ref": _source_ref(row),
            }
        )
    return rows


def _pattern_rows(
    patterns: Iterable[Mapping[str, Any]],
    constraints: Iterable[Mapping[str, Any]],
    stage: str,
) -> list[dict[str, Any]]:
    by_id = {str(row.get("id")): row for row in patterns}
    rows = []
    for constraint in constraints:
        if not (
            str(constraint.get("cefr_level", "")).upper() == "A1"
            and constraint.get("active") is True
            and constraint.get("generator_allowed") is True
        ):
            continue
        node_id = str(constraint.get("pattern_node_id") or "")
        node = by_id.get(node_id, {})
        slot_constraints = constraint.get("slot_constraints", [])
        rows.append(
            {
                "id": constraint.get("pattern_id") or node_id,
                "pattern_node_id": node_id,
                "authority": "pattern",
                "label": constraint.get("canonical_pattern") or node.get("label"),
                "official_cefr_level": "A1",
                "internal_stage": stage,
                "review_status": constraint.get("review_status"),
                "slot_constraints": slot_constraints,
                "generator_allowed": True,
                "source_ref": {
                    "source_file": "ulga/graph/pattern_vocabulary_constraints.json",
                    "source_record_id": constraint.get("pattern_id"),
                    "authority_source": constraint.get("authority_source"),
                    "derivation": constraint.get("source"),
                },
            }
        )
    return rows


def _theme_rows(payload: Iterable[Mapping[str, Any]], stage: str) -> list[dict[str, Any]]:
    rows = []
    for row in payload:
        source_level = str(row.get("cefr_level", "")).upper()
        is_base = source_level == "A1"
        is_bridge = source_level in {"A1_PLUS", "A1+"}
        if stage == "A1" and not is_base:
            continue
        if stage == "A1_PLUS" and not (is_base or is_bridge):
            continue
        metadata = row.get("metadata", {})
        rows.append(
            {
                "id": row.get("id"),
                "theme_id": metadata.get("theme_id"),
                "authority": "theme",
                "label": row.get("label"),
                "official_cefr_level": "A1",
                "source_level": row.get("cefr_level"),
                "internal_stage": stage,
                "role": "bridge" if is_bridge else "base_situation",
                "parent_theme": metadata.get("parent_theme"),
                "description": metadata.get("description"),
                "source_ref": _source_ref(row),
            }
        )
    return rows


def _skill_rows(payload: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"skill:{skill}",
            "authority": "skill",
            "skill": skill,
            "official_cefr_level": "A1",
            "internal_stage": stage,
            "source_ref": {
                "source_file": "ulga/graph/grammar_query_index.json",
                "source_record_id": skill,
                "derivation": "canonical_cross_skill_gate",
            },
        }
        for skill in payload.get("skills", [])
    ]


def _question_type_rows(
    package: Mapping[str, Any], stage: str, package_source_ref: str
) -> list[dict[str, Any]]:
    discovered: dict[str, dict[str, Any]] = {}
    fields = (
        "question_type",
        "task_type",
        "activity_type",
        "item_type",
        "response_type",
        "response_mode",
    )
    for item in package.get("item_bank", []):
        skill = str(item.get("skill") or "unknown")
        role = str(item.get("item_role") or "unknown")
        values = [(field, str(item[field])) for field in fields if item.get(field)]
        if not values:
            values = [("skill_role", f"{skill}:{role}")]
        for field, value in values:
            item_id = f"question_type:{field}:{value}"
            discovered.setdefault(
                item_id,
                {
                    "id": item_id,
                    "authority": "question_type",
                    "question_type": value,
                    "source_field": field,
                    "skill": skill,
                    "item_role": role,
                    "official_cefr_level": "A1",
                    "internal_stage": stage,
                    "source_ref": {
                        "source_file": package_source_ref,
                        "source_record_id": item.get("item_id"),
                        "derivation": "approved_text_mode_item_inventory",
                    },
                },
            )
    return sorted(discovered.values(), key=lambda row: row["id"])


@lru_cache(maxsize=1)
def _load_sources() -> dict[str, Any]:
    package, package_source_ref = _load_package()
    return {
        "grammar": _read_json(GRAMMAR_QUERY_PATH),
        "vocabulary": _read_json(VOCABULARY_PATH),
        "chunk": _read_json(CHUNK_PATH),
        "pattern": _read_json(PATTERN_PATH),
        "pattern_constraint": _read_json(PATTERN_CONSTRAINT_PATH),
        "theme": _read_json(THEME_PATH),
        "package": package,
        "package_source_ref": package_source_ref,
    }


@lru_cache(maxsize=2)
def build_scope(stage: str = "A1") -> dict[str, Any]:
    stage = _normalize_stage(stage)
    sources = _load_sources()
    grammar = _grammar_rows(sources["grammar"], stage)
    vocabulary = _vocabulary_rows(sources["vocabulary"], stage)
    chunks = _chunk_rows(sources["chunk"], stage)
    patterns = _pattern_rows(sources["pattern"], sources["pattern_constraint"], stage)
    themes = _theme_rows(sources["theme"], stage)
    skills = _skill_rows(sources["grammar"], stage)
    question_types = _question_type_rows(
        sources["package"], stage, sources["package_source_ref"]
    )
    counts = {
        "grammar": len(grammar),
        "vocabulary": len(vocabulary),
        "chunk": len(chunks),
        "pattern": len(patterns),
        "theme": len(themes),
        "skill": len(skills),
        "question_type": len(question_types),
    }
    expected = {
        "grammar": 109,
        "vocabulary": 784,
        "chunk": 76,
        "pattern": 27,
        "theme": 9 if stage == "A1" else 10,
        "skill": 4,
    }
    failed = [name for name, count in expected.items() if counts[name] != count]
    if counts["question_type"] < 1:
        failed.append("question_type")
    if failed:
        raise RuntimeError("AUTHORITY_SCOPE_IDENTITY_FAILURE:" + ",".join(sorted(failed)))

    source_paths = {
        "grammar": str(GRAMMAR_QUERY_PATH.relative_to(REPO_ROOT)),
        "vocabulary": str(VOCABULARY_PATH.relative_to(REPO_ROOT)),
        "chunk": str(CHUNK_PATH.relative_to(REPO_ROOT)),
        "pattern": str(PATTERN_CONSTRAINT_PATH.relative_to(REPO_ROOT)),
        "theme": str(THEME_PATH.relative_to(REPO_ROOT)),
        "question_type": sources["package_source_ref"],
    }
    return {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "validation_status": "PASS_AUTHORITY_SCOPE_QUERY_COMPLETE",
        "scope": {
            "official_cefr_level": "A1",
            "internal_stage": stage,
            "source_cefr_policy": (
                "A1_PLUS_INHERITS_A1_AUTHORITY_WITH_APPROVED_BRIDGE_THEME"
                if stage == "A1_PLUS"
                else "DIRECT_A1_AUTHORITY"
            ),
            "a2_a2plus_in_scope": False,
            "static_only": True,
        },
        "counts": counts,
        "authorities": {
            "grammar": grammar,
            "vocabulary": vocabulary,
            "chunk": chunks,
            "pattern": patterns,
            "theme": themes,
            "situation": [dict(row, authority="situation") for row in themes],
            "skill": skills,
            "question_type": question_types,
        },
        "source_paths": source_paths,
        "claim_boundaries": {
            "authority_scope_query_complete": True,
            "learning_unit_contract_complete": False,
            "learner_state_joined": False,
            "mastery_claimed": False,
            "retention_confirmed": False,
            "canonical_graph_written": False,
            "production_runtime_event": False,
        },
        "stop_reason": "NONE",
        "next_short_step": "E4S-A1V1-M02_CrossSkillLearningUnitContractAndBuilder",
    }


def get_scope_summary(stage: str = "A1") -> dict[str, Any]:
    scope = build_scope(stage)
    return {
        key: scope[key]
        for key in (
            "task_id",
            "validation_status",
            "scope",
            "counts",
            "source_paths",
            "claim_boundaries",
            "stop_reason",
            "next_short_step",
        )
    }


def _matches(row: Mapping[str, Any], query: str | None) -> bool:
    if not query or not query.strip():
        return True
    needle = query.casefold().strip()
    fields = (
        "id",
        "label",
        "theme_id",
        "question_type",
        "skill",
        "part_of_speech",
        "usage_class",
    )
    return any(needle in str(row.get(field) or "").casefold() for field in fields)


def query_authority(
    authority: str,
    *,
    stage: str = "A1",
    query: str | None = None,
    limit: int | None = 50,
    offset: int = 0,
    static_only: bool = True,
) -> dict[str, Any]:
    if static_only is not True:
        return {"error": {"code": "STATIC_ONLY_REQUIRED"}, "results": []}
    authority = str(authority or "").strip().lower()
    if authority not in AUTHORITIES:
        return {
            "error": {
                "code": "UNKNOWN_AUTHORITY",
                "details": {"authority": authority, "allowed": list(AUTHORITIES)},
            },
            "results": [],
        }
    try:
        stage = _normalize_stage(stage)
    except ValueError as exc:
        return {"error": {"code": str(exc)}, "results": []}
    if not isinstance(limit, int) or limit < 0:
        return {"error": {"code": "INVALID_LIMIT"}, "results": []}
    if not isinstance(offset, int) or offset < 0:
        return {"error": {"code": "INVALID_OFFSET"}, "results": []}
    warnings = []
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
        warnings.append("LIMIT_CLAMPED_TO_MAXIMUM")

    scope = build_scope(stage)
    if authority == "source_evidence":
        rows = [
            {
                "id": f"source_evidence:{name}",
                "authority": "source_evidence",
                "source_authority": name,
                "source_file": source_file,
                "official_cefr_level": "A1",
                "internal_stage": stage,
            }
            for name, source_file in scope["source_paths"].items()
        ]
    else:
        rows = scope["authorities"][authority]
    filtered = [row for row in rows if _matches(row, query)]
    results = filtered[offset : offset + limit]
    return {
        "query_metadata": {
            "authority": authority,
            "official_cefr_level": "A1",
            "internal_stage": stage,
            "static_only": True,
            "query": query,
            "limit": limit,
            "offset": offset,
            "total_match_count": len(filtered),
            "result_count": len(results),
            "warnings": warnings,
        },
        "results": results,
    }
