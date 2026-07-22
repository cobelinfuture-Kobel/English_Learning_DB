#!/usr/bin/env python3
"""Deduplicate RAZ A1/A1+ candidates and compare them with the mainline M2 Asset Body.

The builder reads private RAZ A-I page text and the private A1FS-V1-M2 consumer
index.  It emits only text-free hashes, representative identities, similarity
scores, and dispositions.  A2 payload rows are never traversed or compared.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s01_material_admission as admission

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S02_MainlineSemanticDedupAndConflictResolution"
SCHEMA_VERSION = "raz.ai.acl.v1.s02.mainline_semantic_dedup.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S02_MAINLINE_SEMANTIC_DEDUP"

M2_TASK_ID = "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery"
M2_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
SCOPE_LEVELS = admission.A1_A1PLUS_LEVELS
EXPECTED_SCOPE_ROW_COUNT = 7957
EXPECTED_GROUP_COUNT = 7849
EXPECTED_DUPLICATE_EXCESS = 108

DEFAULT_ADMISSION = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s01_material_admission/"
    / "material_admission_classification.safe.json"
)
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_MAINLINE = (
    REPO_ROOT / ".local/a1fs_v1/m2/"
    / "four_skill_asset_body_consumer.private.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s02_mainline_semantic_dedup/"
    / "mainline_semantic_dedup.safe.json"
)

TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
FORBIDDEN_SAFE_KEYS = {
    "text", "title", "source_text", "body_text", "payload", "prompt",
    "passage", "sentence", "sentences", "teacher_delivery",
}

STATUS_PRIORITY = {
    "A1_READY_CANDIDATE": 6,
    "A1PLUS_READY_CANDIDATE": 6,
    "REWRITE_REQUIRED": 4,
    "SUPPORT_ONLY": 3,
    "REJECTED_UNUSABLE": 1,
    "DUPLICATE_CANDIDATE": 0,
}
MATURITY_PRIORITY = {
    "STRICT_CORE_SENTENCE_SEED": 4,
    "BROAD_CORE_SENTENCE_SEED": 3,
    "PASSAGE_SUPPORT_SEED": 2,
    "SUPPORT_SENTENCE_SEED": 1,
}
READY_STATUSES = admission.READY_STATUSES
LINKABLE_DISPOSITIONS = {
    "NEW_COMPLEMENTARY_MATERIAL",
    "VARIANT_WORTH_KEEPING",
}

CLAIM_BOUNDARIES = {
    "private_raz_text_read_performed": True,
    "private_mainline_payload_read_performed": True,
    "source_text_included_in_output": False,
    "mainline_payload_included_in_output": False,
    "a2_payload_semantic_comparison_performed": False,
    "a2_a2plus_admission_performed": False,
    "canonical_authority_write_performed": False,
    "learner_facing_content_created": False,
    "human_approval_fabricated": False,
}


class SemanticDedupError(ValueError):
    """Fail-closed identity, source, accounting, or privacy error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _verify_owned_package(package: Mapping[str, Any], *, task_id: str, status: str, label: str) -> None:
    if package.get("task_id") != task_id:
        raise SemanticDedupError(f"{label}_task_id_invalid")
    if package.get("validation_status") != status:
        raise SemanticDedupError(f"{label}_status_invalid")
    claimed = package.get("package_sha256")
    core = {key: value for key, value in package.items() if key != "package_sha256"}
    if not isinstance(claimed, str) or claimed != deep.sha256_value(core):
        raise SemanticDedupError(f"{label}_package_sha256_mismatch")


def _verify_admission(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    _verify_owned_package(
        package,
        task_id=admission.TASK_ID,
        status=admission.PASS_STATUS,
        label="admission",
    )
    gate = package.get("admission_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != "MATERIAL_ADMISSION_CLASSIFICATION_READY":
        raise SemanticDedupError("admission_gate_not_ready")
    if gate.get("distance_after") != "D5":
        raise SemanticDedupError("admission_distance_not_d5")
    rows = package.get("admission_rows")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise SemanticDedupError("admission_rows_invalid")
    scope = [row for row in rows if str(row.get("source_level") or "") in SCOPE_LEVELS]
    if len(scope) != EXPECTED_SCOPE_ROW_COUNT:
        raise SemanticDedupError(f"scope_row_count_mismatch:{len(scope)}")
    return scope


def _verify_mainline(index: Mapping[str, Any], *, expected_asset_count: int | None = None) -> list[Mapping[str, Any]]:
    if index.get("task_id") != M2_TASK_ID or index.get("validation_status") != M2_STATUS:
        raise SemanticDedupError("mainline_m2_identity_invalid")
    if index.get("errors") != []:
        raise SemanticDedupError("mainline_m2_errors_not_empty")
    records = index.get("asset_records")
    if not isinstance(records, list) or not all(isinstance(row, Mapping) for row in records):
        raise SemanticDedupError("mainline_asset_records_invalid")
    if expected_asset_count is not None and len(records) != expected_asset_count:
        raise SemanticDedupError(f"mainline_asset_count_mismatch:{len(records)}:{expected_asset_count}")
    access = index.get("access_contract")
    if not isinstance(access, Mapping) or access.get("a2_payload_query_allowed") is not False:
        raise SemanticDedupError("mainline_a2_lock_invalid")
    return records


def _discover_page_file(source_root: Path, level: str) -> Path:
    filename = f"raz_{level}_page_unit_enriched.json"
    candidates = [
        source_root / "derived" / f"Level_{level}" / "enriched" / filename,
        source_root / f"Level_{level}" / "enriched" / filename,
        source_root / filename,
    ]
    present = [path.resolve() for path in candidates if path.is_file()]
    if not present:
        present = [path.resolve() for path in source_root.rglob(filename)]
    unique = sorted(set(present))
    if len(unique) != 1:
        raise SemanticDedupError(f"source_file_resolution_not_unique:{level}:{len(unique)}")
    return unique[0]


def _load_raz_texts(source_root: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    texts: dict[str, str] = {}
    source_index: list[dict[str, Any]] = []
    for level in SCOPE_LEVELS:
        path = _discover_page_file(source_root, level)
        payload = deep.read_json(path)
        if not isinstance(payload, list):
            raise SemanticDedupError(f"source_payload_not_list:{level}")
        for row in payload:
            if not isinstance(row, Mapping):
                raise SemanticDedupError(f"source_row_not_object:{level}")
            ref = str(row.get("page_unit_id") or "")
            text = row.get("text")
            if not ref or ref in texts or not isinstance(text, str) or not text.strip():
                raise SemanticDedupError(f"source_identity_or_text_invalid:{level}:{ref}")
            texts[ref] = text
        source_index.append({
            "level": level,
            "source_path": path.relative_to(source_root).as_posix()
            if path.is_relative_to(source_root) else str(path),
            "record_count": len(payload),
            "sha256": deep.sha256_file(path),
        })
    if len(texts) != EXPECTED_SCOPE_ROW_COUNT:
        raise SemanticDedupError(f"source_text_count_mismatch:{len(texts)}")
    return texts, source_index


def _normalize(value: str) -> str:
    return " ".join(token.casefold().replace("’", "'") for token in TOKEN_RE.findall(value))


def _tokens(value: str) -> frozenset[str]:
    return frozenset(_normalize(value).split())


def _strings(value: Any, path: str = "$ROOT") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        if value.strip():
            yield path, value
    elif isinstance(value, Mapping):
        for key in sorted(value, key=str):
            yield from _strings(value[key], f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _strings(child, f"{path}[{index}]")


def _mainline_text_units(records: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    units: list[dict[str, Any]] = []
    a2_skipped = 0
    seen: set[tuple[str, str, str]] = set()
    for asset in records:
        level = str(asset.get("level") or "")
        if level == "A2":
            a2_skipped += 1
            continue
        if level not in {"A1", "A1+"}:
            raise SemanticDedupError(f"mainline_level_invalid:{level}")
        asset_key = str(asset.get("asset_key") or asset.get("asset_id") or "")
        skill = str(asset.get("skill") or "")
        role = str(asset.get("role") or "")
        payload = asset.get("payload")
        if not asset_key or not isinstance(payload, Mapping):
            raise SemanticDedupError(f"mainline_asset_invalid:{asset_key}")
        for path, text in _strings(payload):
            normalized = _normalize(text)
            token_set = frozenset(normalized.split())
            if len(token_set) < 2:
                continue
            identity = (asset_key, path, hashlib.sha256(normalized.encode("utf-8")).hexdigest())
            if identity in seen:
                continue
            seen.add(identity)
            units.append({
                "asset_key": asset_key,
                "lesson_id": str(asset.get("lesson_id") or ""),
                "skill": skill,
                "level": "A1_PLUS" if level == "A1+" else "A1",
                "role": role,
                "payload_path_sha256": hashlib.sha256(path.encode("utf-8")).hexdigest(),
                "normalized_sha256": identity[2],
                "normalized": normalized,
                "tokens": token_set,
            })
    if not units:
        raise SemanticDedupError("mainline_learning_text_units_empty")
    units.sort(key=lambda row: (row["asset_key"], row["payload_path_sha256"], row["normalized_sha256"]))
    return units, a2_skipped


def _provisional(row: Mapping[str, Any]) -> tuple[str, str, list[str]]:
    status = str(row.get("admission_status") or "")
    if status != "DUPLICATE_CANDIDATE":
        return status, str(row.get("candidate_cefr_scope") or "NONE"), list(row.get("admission_reason_codes") or [])
    ref = str(row.get("source_unit_ref") or "")
    return admission._classify_scope_row(row, duplicate_representative=ref)


def _rank(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int]:
    status, _, _ = _provisional(row)
    vocabulary = len(row.get("matched_vocabulary_refs") or [])
    grammar = len(row.get("matched_grammar_unit_refs") or [])
    chunks = len(row.get("matched_chunk_refs") or [])
    patterns = len(row.get("matched_pattern_refs") or [])
    skills = len(row.get("four_skill_affordances") or [])
    maturity = MATURITY_PRIORITY.get(str(row.get("sentence_seed_maturity") or ""), 0)
    passage = int(row.get("passage_seed_status") == "SUPPORTED")
    return (
        STATUS_PRIORITY.get(status, -1),
        int(bool(vocabulary and grammar)),
        vocabulary + grammar + chunks + patterns,
        skills,
        maturity,
        passage,
    )


def _representatives(scope_rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in scope_rows:
        group = str(row.get("semantic_duplicate_group_id") or "")
        ref = str(row.get("source_unit_ref") or "")
        if not group or not ref:
            raise SemanticDedupError(f"group_or_ref_missing:{ref}")
        groups[group].append(row)
    if len(groups) != EXPECTED_GROUP_COUNT:
        raise SemanticDedupError(f"semantic_group_count_mismatch:{len(groups)}")
    duplicate_excess = sum(len(rows) - 1 for rows in groups.values())
    if duplicate_excess != EXPECTED_DUPLICATE_EXCESS:
        raise SemanticDedupError(f"duplicate_excess_mismatch:{duplicate_excess}")

    selected: list[dict[str, Any]] = []
    for group, members in sorted(groups.items()):
        ordered = sorted(
            members,
            key=lambda row: tuple(-value for value in _rank(row))
            + (str(row.get("source_unit_ref") or ""),),
        )
        winner = ordered[0]
        status, scope, reasons = _provisional(winner)
        selected.append({
            "semantic_duplicate_group_id": group,
            "member_source_unit_refs": sorted(str(row["source_unit_ref"]) for row in members),
            "member_count": len(members),
            "representative_source_unit_ref": str(winner["source_unit_ref"]),
            "representative_status": status,
            "candidate_cefr_scope": scope,
            "representative_reason_codes": reasons,
            "representative_rank_vector": list(_rank(winner)),
            "candidate_theme_refs": list(winner.get("candidate_theme_refs") or []),
            "matched_vocabulary_refs": list(winner.get("matched_vocabulary_refs") or []),
            "matched_chunk_refs": list(winner.get("matched_chunk_refs") or []),
            "matched_pattern_refs": list(winner.get("matched_pattern_refs") or []),
            "matched_grammar_unit_refs": list(winner.get("matched_grammar_unit_refs") or []),
            "sentence_seed_maturity": str(winner.get("sentence_seed_maturity") or ""),
            "passage_seed_status": str(winner.get("passage_seed_status") or ""),
            "four_skill_affordances": list(winner.get("four_skill_affordances") or []),
        })
    return selected, duplicate_excess


def _skill_names(affordances: Sequence[str]) -> set[str]:
    mapping = {
        "READING_SOURCE": "READING",
        "LISTENING_ADAPTATION": "LISTENING",
        "SPEAKING_PROMPT": "SPEAKING",
        "WRITING_MODEL": "WRITING",
    }
    return {mapping[value] for value in affordances if value in mapping}


def _indexes(units: Sequence[Mapping[str, Any]]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    exact: dict[str, list[int]] = defaultdict(list)
    postings: dict[str, list[int]] = defaultdict(list)
    for index, unit in enumerate(units):
        exact[str(unit["normalized_sha256"])].append(index)
        for token in unit["tokens"]:
            postings[str(token)].append(index)
    return exact, postings


def _match(
    text: str,
    units: Sequence[Mapping[str, Any]],
    exact_index: Mapping[str, Sequence[int]],
    postings: Mapping[str, Sequence[int]],
) -> dict[str, Any] | None:
    normalized = _normalize(text)
    source_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    exact_ids = list(exact_index.get(source_hash, []))
    if exact_ids:
        rows = [units[index] for index in exact_ids]
        return {
            "match_kind": "EXACT",
            "similarity": 1.0,
            "containment": 1.0,
            "source_normalized_sha256": source_hash,
            "matches": rows[:20],
            "match_count": len(rows),
        }

    source_tokens = frozenset(normalized.split())
    if len(source_tokens) < 3:
        return None
    overlap_counts: Counter[int] = Counter()
    for token in source_tokens:
        overlap_counts.update(postings.get(token, []))
    ranked: list[tuple[float, float, float, str, int]] = []
    for index, overlap in overlap_counts.most_common(250):
        target_tokens = units[index]["tokens"]
        minimum = min(len(source_tokens), len(target_tokens))
        if minimum < 3 or overlap < max(2, math.ceil(minimum * 0.70)):
            continue
        union = len(source_tokens | target_tokens)
        jaccard = overlap / union if union else 0.0
        containment = overlap / minimum if minimum else 0.0
        length_ratio = minimum / max(len(source_tokens), len(target_tokens))
        if not (jaccard >= 0.75 and containment >= 0.85 and length_ratio >= 0.60):
            continue
        ranked.append((jaccard, containment, length_ratio, str(units[index]["asset_key"]), index))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3], row[4]))
    best = ranked[0]
    near = best[0] >= 0.90 or (best[1] >= 0.95 and best[2] >= 0.75)
    return {
        "match_kind": "NEAR" if near else "VARIANT",
        "similarity": round(best[0], 4),
        "containment": round(best[1], 4),
        "source_normalized_sha256": source_hash,
        "matches": [units[best[4]]],
        "match_count": 1,
    }


def _safe_match(match: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if match is None:
        return None
    return {
        "match_kind": match["match_kind"],
        "similarity": match["similarity"],
        "containment": match["containment"],
        "source_normalized_sha256": match["source_normalized_sha256"],
        "match_count": match["match_count"],
        "mainline_matches": [
            {
                "asset_key": row["asset_key"],
                "lesson_id": row["lesson_id"],
                "skill": row["skill"],
                "level": row["level"],
                "role": row["role"],
                "payload_path_sha256": row["payload_path_sha256"],
                "normalized_sha256": row["normalized_sha256"],
            }
            for row in match["matches"]
        ],
    }


def _disposition(representative: Mapping[str, Any], match: Mapping[str, Any] | None) -> tuple[str, str, bool]:
    status = str(representative["representative_status"])
    if status == "REWRITE_REQUIRED":
        return "REWRITE_REQUIRED_NOT_LINKABLE", "CONTROLLED_REWRITE_REQUIRED", False
    if status == "SUPPORT_ONLY":
        return "SUPPORT_ONLY_NOT_LINKABLE", "RETAIN_AS_TEACHER_SUPPORT", False
    if status == "REJECTED_UNUSABLE":
        return "REJECTED_UNUSABLE", "EXCLUDE_FROM_LINKAGE", False
    if status not in READY_STATUSES:
        raise SemanticDedupError(f"representative_status_unhandled:{status}")
    if match is None:
        return "NEW_COMPLEMENTARY_MATERIAL", "KEEP_FOR_CANONICAL_LINKAGE", True

    candidate_scope = str(representative["candidate_cefr_scope"])
    matched_levels = {str(row["level"]) for row in match["matches"]}
    same_level = candidate_scope in matched_levels
    if match["match_kind"] in {"EXACT", "NEAR"} and not same_level:
        return (
            "CONFLICTING_AUTHORITY_MAPPING",
            "RESOLVED_BY_EXCLUSION_FROM_LINKAGE",
            False,
        )
    if match["match_kind"] == "EXACT":
        return "EXACT_DUPLICATE", "USE_EXISTING_MAINLINE_ASSET", False
    if match["match_kind"] == "NEAR":
        source_skills = _skill_names(representative.get("four_skill_affordances") or [])
        matched_skills = {str(row["skill"]) for row in match["matches"]}
        if source_skills - matched_skills:
            return "VARIANT_WORTH_KEEPING", "KEEP_AS_CROSS_SKILL_VARIANT", True
        return "NEAR_DUPLICATE", "USE_EXISTING_MAINLINE_ASSET", False
    return "VARIANT_WORTH_KEEPING", "KEEP_AS_SEMANTIC_VARIANT", True


def _scan_forbidden(value: Any, path: str = "$ROOT") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_SAFE_KEYS:
                errors.append(f"{path}.{key}")
            errors.extend(_scan_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_scan_forbidden(child, f"{path}[{index}]"))
    return errors


def build_package(
    admission_package: Mapping[str, Any],
    mainline_index: Mapping[str, Any],
    raz_texts: Mapping[str, str],
    source_index: Sequence[Mapping[str, Any]],
    *,
    mainline_index_sha256: str,
    expected_mainline_asset_count: int | None = None,
) -> dict[str, Any]:
    scope_rows = _verify_admission(admission_package)
    mainline_records = _verify_mainline(mainline_index, expected_asset_count=expected_mainline_asset_count)
    if set(str(row.get("source_unit_ref") or "") for row in scope_rows) != set(raz_texts):
        raise SemanticDedupError("admission_source_text_identity_mismatch")

    representatives, duplicate_excess = _representatives(scope_rows)
    text_units, a2_skipped = _mainline_text_units(mainline_records)
    exact_index, postings = _indexes(text_units)

    output_rows: list[dict[str, Any]] = []
    disposition_counts: Counter[str] = Counter()
    representative_status_counts: Counter[str] = Counter()
    unresolved_conflicts = 0
    for representative in representatives:
        ref = str(representative["representative_source_unit_ref"])
        status = str(representative["representative_status"])
        match = _match(raz_texts[ref], text_units, exact_index, postings) if status in READY_STATUSES else None
        disposition, resolution, linkable = _disposition(representative, match)
        if disposition == "CONFLICTING_AUTHORITY_MAPPING" and resolution != "RESOLVED_BY_EXCLUSION_FROM_LINKAGE":
            unresolved_conflicts += 1
        disposition_counts[disposition] += 1
        representative_status_counts[status] += 1
        output_rows.append({
            **representative,
            "mainline_match": _safe_match(match),
            "dedup_disposition": disposition,
            "conflict_resolution": resolution,
            "ready_for_canonical_linkage": linkable,
            "promotion_status": "NOT_PROMOTED",
        })

    checks = {
        "scope_rows_reconciled": len(scope_rows) == EXPECTED_SCOPE_ROW_COUNT,
        "semantic_groups_reconciled": len(output_rows) == EXPECTED_GROUP_COUNT,
        "duplicate_excess_reconciled": duplicate_excess == EXPECTED_DUPLICATE_EXCESS,
        "one_representative_per_group": len({row["semantic_duplicate_group_id"] for row in output_rows}) == len(output_rows),
        "all_representatives_dispositioned": sum(disposition_counts.values()) == len(output_rows),
        "unresolved_conflict_count_zero": unresolved_conflicts == 0,
        "a2_payload_comparison_not_performed": all(row.get("level") != "A2" for row in text_units),
        "no_promoted_rows": all(row["promotion_status"] == "NOT_PROMOTED" for row in output_rows),
    }
    ready = all(checks.values())
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "admission_task_id": admission_package["task_id"],
            "admission_package_sha256": admission_package["package_sha256"],
            "mainline_task_id": mainline_index["task_id"],
            "mainline_index_sha256": mainline_index_sha256,
        },
        "private_source_index": [dict(row) for row in source_index],
        "mainline_index_summary": {
            "asset_record_count": len(mainline_records),
            "learning_text_unit_count": len(text_units),
            "a2_asset_record_count_skipped_without_payload_traversal": a2_skipped,
        },
        "representative_rows": output_rows,
        "aggregate_summary": {
            "a1_a1plus_scope_candidate_count": len(scope_rows),
            "semantic_identity_count": len(output_rows),
            "duplicate_excess_count": duplicate_excess,
            "representative_status_counts": dict(sorted(representative_status_counts.items())),
            "dedup_disposition_counts": dict(sorted(disposition_counts.items())),
            "linkage_candidate_count": sum(row["ready_for_canonical_linkage"] for row in output_rows),
            "unresolved_conflict_count": unresolved_conflicts,
            "final_promoted_material_count": 0,
        },
        "dedup_gate": {
            "source_checks": checks,
            "decision": "MAINLINE_SEMANTIC_DEDUP_READY" if ready else "BLOCKED_MAINLINE_SEMANTIC_DEDUP",
            "distance_before": "D5",
            "distance_after": "D4" if ready else "D5",
            "ready_for_canonical_linkage": ready,
            "ready_for_material_promotion": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = _scan_forbidden(package)
    if leakage:
        raise SemanticDedupError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _read_json_object(path: Path, code: str) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SemanticDedupError(f"{code}_json_invalid") from exc
    if not isinstance(value, dict):
        raise SemanticDedupError(f"{code}_not_object")
    return value, hashlib.sha256(raw).hexdigest()


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
    parser.add_argument("--admission-package", type=Path, default=DEFAULT_ADMISSION)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--mainline-consumer", type=Path, default=DEFAULT_MAINLINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        admission_package, _ = _read_json_object(args.admission_package, "admission")
        mainline_index, mainline_sha = _read_json_object(args.mainline_consumer, "mainline")
        raz_texts, source_index = _load_raz_texts(args.source_root)
        package = build_package(
            admission_package,
            mainline_index,
            raz_texts,
            source_index,
            mainline_index_sha256=mainline_sha,
        )
        deep.write_json_atomic(args.output, package)
        print(json.dumps(_readback(package), sort_keys=True))
        return 0
    except (SemanticDedupError, admission.MaterialAdmissionError, deep.AlignmentError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
