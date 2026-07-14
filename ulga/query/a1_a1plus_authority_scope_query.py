#!/usr/bin/env python3
"""Unified read-only A1/A1+ authority scope query.

This module closes the M01 query surface without mutating canonical graph data,
joining learner state, claiming mastery/retention, or expanding A2/A2+.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]

GRAMMAR_QUERY_PATH = REPO_ROOT / "ulga/graph/grammar_query_index.json"
VOCABULARY_PATH = REPO_ROOT / "ulga/graph/vocabulary_nodes.json"
CHUNK_PATH = REPO_ROOT / "ulga/graph/chunk_nodes.json"
PATTERN_PATH = REPO_ROOT / "ulga/graph/sentence_patterns.json"
PATTERN_CONSTRAINT_PATH = REPO_ROOT / "ulga/graph/pattern_vocabulary_constraints.json"
THEME_PATH = REPO_ROOT / "ulga/graph/theme_nodes.json"
TEXT_MODE_PACKAGE_PATH = (
    REPO_ROOT / "ulga/graph/a1_grammar_text_mode_private_pilot_package.json"
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
    normalized = str(value or "A1").strip().upper().replace("+", "_PLUS")
    if normalized not in VALID_STAGES:
        raise ValueError(f"OUT_OF_SCOPE_LEVEL_STAGE:{value}")
    return normalized


def _authority_source_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    authority = row.get("authority_source", {})
    if not isinstance(authority, Mapping):
        return {}
    return {
        "source_name": authority.get("source_name"),
        "source_file": authority.get("source_file"),
        "source_record_id": authority.get("source_record_id"),
        "derivation": authority.get("derivation"),
    }


def _is_a1_source(row: Mapping[str, Any]) -> bool:
    return str(row.get("cefr_level", "")).upper() == "A1"


def _text_matches(row: Mapping[str, Any], query: str | None) -> bool:
    if not query:
        return True
    needle = query.casefold().strip()
    if not needle:
        return True
    values = [
        row.get("id"),
        row.get("label"),
        row.get("canonical_pattern"),
        row.get("pattern_id"),
        row.get("theme_id"),
        row.get("theme_name"),
        row.get("question_type"),
        row.get("skill"),
    ]
    return any(needle in str(value or "").casefold() for value in values)


def _paginate(rows: list[dict[str, Any]], *, limit: int, offset: int) -> list[dict[str, Any]]:
    return rows[offset : offset + limit]


def _normalize_limit(limit: int | None) -> tuple[int, list[str]]:
    if limit is None:
        return 50, []
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("INVALID_LIMIT")
    if limit > MAX_LIMIT:
        return MAX_LIMIT, ["LIMIT_CLAMPED_TO_MAXIMUM"]
    return limit, []


def _grammar_rows(payload: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    canonical = payload.get("canonical_a1", {})
    row_ids = canonical.get("canonical_egp_row_ids", [])
    by_row = payload.get("by_egp_row_id", {})
    rows: list[dict[str, Any]] = []
    for row_id in row_ids:
        raw = by_row.get(row_id)
        grammar_ids: list[str] = []
        if isinstance(raw, list):
            grammar_ids = [str(value) for value in raw]
        elif isinstance(raw, Mapping):
            grammar_ids = [
                str(value)
                for value in raw.get("grammar_ids", raw.get("grammar_unit_ids", []))
            ]
        rows.append(
            {
                "id": row_id,
                "authority": "grammar",
                "official_cefr_level": canonical.get("official_level", "A1"),
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
        if not _is_a1_source(row):
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
                "source_ref": _authority_source_ref(row),
            }
        )
    return rows


def _chunk_rows(payload: Iterable[Mapping[str, Any]], stage: str) -> list[dict[str, Any]]:
    rows = []
    for row in payload:
        metadata = row.get("metadata", {})
        if not _is_a1_source(row) or metadata.get("generator_allowed") is not True:
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
                "source_ref": _authority_source_ref(row),
            }
        )
    return rows


def _pattern_rows(
    patterns: Iterable[Mapping[str, Any]],
    constraints: Iterable[Mapping[str, Any]],
    stage: str,
) -> list[dict[str, Any]]:
    pattern_by_id = {str(row.get("id")): row for row in patterns}
    rows = []
    for constraint in constraints:
        if (
            str(constraint.get("cefr_level", "")).upper() != "A1"
            or constraint.get("active") is not True
            or constraint.get("generator_allowed") is not True
        ):
            continue
        node_id = str(constraint.get("pattern_node_id") or "")
        node = pattern_by_id.get(node_id, {})
        rows.append(
            {
                "id": constraint.get("pattern_id") or node_id,
                "pattern_node_id": node_id,
                "authority": "pattern",
                "label": constraint.get("canonical_pattern") or node.get("label"),
                "official_cefr_level": "A1",
                "internal_stage": stage,
                "review_status": constraint.get("review_status"),
                "slot_constraints": list(constraint.get("slot_constraints", [])),
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
        level = str(row.get("cefr_level", "")).upper()
        is_base = level == "A1"
        is_bridge = level in {"A1_PLUS", "A1+"}
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
                "source_ref": _authority_source_ref(row),
            }
        )
    return rows


def _skill_rows(grammar_payload: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
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
        for skill in grammar_payload.get("skills", [])
    ]


def _question_type_rows(package: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    discovered: dict[str, dict[str, Any]] = {}
    for item in package.get("item_bank", []):
        skill = str(item.get("skill") or "unknown")
        role = str(item.get("item_role") or "unknown")
        values = []
        for key in (
            "question_type",
            "task_type",
            "activity_type",
            "item_type",
            "response_type",
            "response_mode",
        ):
            value = item.get(key)
            if value:
                values.append((key, str(value)))
        if not values:
            values.append(("skill_role", f"{skill}:{role}"))
        for field, value in values:
            identifier = f"question_type:{field}:{value}"
            discovered.setdefault(
                identifier,
                {
                    "id": identifier,
                    "authority": "question_type",
                    "question_type": value,
                    "source_field": field,
                    "skill": skill,
                    "item_role": role,
                    "official_cefr_level": "A1",
                    "internal_stage": stage,
                    "source_ref": {
                        "source_file": "ulga/graph/a1_grammar_text_mode_private_pilot_package.json",
                        "source_record_id": item.get("item_id"),
                        "derivation": "approved_text_mode_item_inventory",
                    },
                },
            )
    return sorted(discovered.values(), key=lambda row: row["id"])


@lru_cache(maxsize=1)
def _load_sources() -> dict[str, Any]:
    return {
        "grammar": _read_json(GRAMMAR_QUERY_PATH),
        "vocabulary": _read_json(VOCABULARY_PATH),
        "chunk": _read_json(CHUNK_PATH),
        "pattern": _read_json(PATTERN_PATH),
        "pattern_constraint": _read_json(PATTERN_CONSTRAINT_PATH),
        "theme": _read_json(THEME_PATH),
        "package": _read_json(TEXT_MODE_PACKAGE_PATH),
    }


@lru_cache(maxsize=2)
def build_scope(stage: str = "A1") -> dict[str, Any]:
    normalized_stage = _normalize_stage(stage)
    sources = _load_sources()
    grammar = _grammar_rows(sources["grammar"], normalized_stage)
    vocabulary = _vocabulary_rows(sources["vocabulary"], normalized_stage)
    chunks = _chunk_rows(sources["chunk"], normalized_stage)
    patterns = _pattern_rows(
        sources["pattern"], sources["pattern_constraint"], normalized_stage
    )
    themes = _theme_rows(sources["theme"], normalized_stage)
    skills = _skill_rows(sources["grammar"], normalized_stage)
    question_types = _question_type_rows(sources["package"], normalized_stage)

    required_counts = {
        "grammar": 109,
        "vocabulary": 784,
        "chunk": 76,
        "pattern": 27,
        "theme": 9 if normalized_stage == "A1" else 10,
        "skill": 4,
    }
    actual_counts = {
        "grammar": len(grammar),
        "vocabulary": len(vocabulary),
        "chunk": len(chunks),
        "pattern": len(patterns),
        "theme": len(themes),
        "skill": len(skills),
        "question_type": len(question_types),
    }
    failed = [
        authority
        for authority, expected in required_counts.items()
        if actual_counts[authority] != expected
    ]
    if not question_types:
        failed.append("question_type")
    if failed:
        raise RuntimeError("AUTHORITY_SCOPE_IDENTITY_FAILURE:" + ",".join(sorted(failed)))

    return {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "validation_status": "PASS_AUTHORITY_SCOPE_QUERY_COMPLETE",
        "scope": {
            "official_cefr_level": "A1",
            "internal_stage": normalized_stage,
            "source_cefr_policy": (
                "A1_PLUS_INHERITS_A1_AUTHORITY_WITH_APPROVED_BRIDGE_THEME"
                if normalized_stage == "A1_PLUS"
                else "DIRECT_A1_AUTHORITY"
            ),
            "a2_a2plus_in_scope": False,
            "static_only": True,
        },
        "counts": actual_counts,
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
        "source_paths": {
            "grammar": str(GRAMMAR_QUERY_PATH.relative_to(REPO_ROOT)),
            "vocabulary": str(VOCABULARY_PATH.relative_to(REPO_ROOT)),
            "chunk": str(CHUNK_PATH.relative_to(REPO_ROOT)),
            "pattern": str(PATTERN_CONSTRAINT_PATH.relative_to(REPO_ROOT)),
            "theme": str(THEME_PATH.relative_to(REPO_ROOT)),
            "question_type": str(TEXT_MODE_PACKAGE_PATH.relative_to(REPO_ROOT)),
        },
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
        "task_id": scope["task_id"],
        "validation_status": scope["validation_status"],
        "scope": scope["scope"],
        "counts": scope["counts"],
        "source_paths": scope["source_paths"],
        "claim_boundaries": scope["claim_boundaries"],
        "stop_reason": scope["stop_reason"],
        "next_short_step": scope["next_short_step"],
    }


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
        return {
            "error": {"code": "STATIC_ONLY_REQUIRED"},
            "results": [],
        }
    normalized_authority = str(authority or "").strip().lower()
    if normalized_authority not in AUTHORITIES:
        return {
            "error": {
                "code": "UNKNOWN_AUTHORITY",
                "details": {"authority": authority, "allowed": list(AUTHORITIES)},
            },
            "results": [],
        }
    try:
        normalized_stage = _normalize_stage(stage)
        normalized_limit, warnings = _normalize_limit(limit)
    except ValueError as exc:
        return {"error": {"code": str(exc)}, "results": []}
    if not isinstance(offset, int) or offset < 0:
        return {"error": {"code": "INVALID_OFFSET"}, "results": []}

    scope = build_scope(normalized_stage)
    if normalized_authority == "source_evidence":
        rows = []
        for source_authority, source_path in scope["source_paths"].items():
            rows.append(
                {
                    "id": f"source_evidence:{source_authority}",
                    "authority": "source_evidence",
                    "source_authority": source_authority,
                    "source_file": source_path,
                    "official_cefr_level": "A1",
                    "internal_stage": normalized_stage,
                }
            )
    else:
        rows = scope["authorities"][normalized_authority]
    filtered = [row for row in rows if _text_matches(row, query)]
    results = _paginate(filtered, limit=normalized_limit, offset=offset)
    return {
        "query_metadata": {
            "authority": normalized_authority,
            "official_cefr_level": "A1",
            "internal_stage": normalized_stage,
            "static_only": True,
            "query": query,
            "limit": normalized_limit,
            "offset": offset,
            "total_match_count": len(filtered),
            "result_count": len(results),
            "warnings": warnings,
        },
        "results": results,
    }
