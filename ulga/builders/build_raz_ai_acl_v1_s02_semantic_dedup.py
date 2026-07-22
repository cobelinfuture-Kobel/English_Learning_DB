#!/usr/bin/env python3
"""Select RAZ semantic representatives and compare them with the mainline M2 Asset Body.

S02 consumes the verified S01 admission package, privately reads RAZ A-I page
text and the private A1FS-V1-M2 consumer index, and emits only text-free hashes,
representative identities, similarity evidence, and dispositions. A2 payload
rows are skipped before payload traversal and remain deferred.
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
TASK_ID = "RAZ-AI-ACL-V1-S02_SemanticDedupAndMainlineConflictResolution"
SCHEMA_VERSION = "raz.ai.acl.v1.s02.semantic_dedup_mainline_conflict.v2"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S02_SEMANTIC_DEDUP_MAINLINE_CONFLICT"

M2_TASK_ID = "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery"
M2_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

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
    REPO_ROOT / ".local/raz_ai/acl_v1_s02_semantic_dedup/"
    / "semantic_dedup_mainline_conflict_resolution.safe.json"
)

TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
FORBIDDEN_SAFE_KEYS = {
    "text", "title", "source_text", "body_text", "payload", "prompt",
    "passage", "sentence", "sentences", "teacher_delivery",
}
REPRESENTATIVE_STATUSES = {
    "A1_READY_CANDIDATE",
    "A1PLUS_READY_CANDIDATE",
    "REWRITE_REQUIRED",
    "SUPPORT_ONLY",
    "REJECTED_UNUSABLE",
}
READY_STATUSES = admission.READY_STATUSES
STATUS_TIER = {
    "A1_READY_CANDIDATE": 6,
    "A1PLUS_READY_CANDIDATE": 6,
    "REWRITE_REQUIRED": 4,
    "SUPPORT_ONLY": 3,
    "REJECTED_UNUSABLE": 1,
}
MATURITY_TIER = {
    "STRICT_CORE_SENTENCE_SEED": 4,
    "BROAD_CORE_SENTENCE_SEED": 3,
    "PASSAGE_SUPPORT_SEED": 2,
    "SUPPORT_SENTENCE_SEED": 1,
}
LINKABLE_DISPOSITIONS = {
    "NEW_COMPLEMENTARY_MATERIAL",
    "VARIANT_WORTH_KEEPING",
}

CLAIM_BOUNDARIES = {
    "private_raz_text_read_performed": True,
    "private_mainline_payload_read_performed": True,
    "source_text_included_in_output": False,
    "mainline_payload_included_in_output": False,
    "raz_level_used_as_cefr_equivalence": False,
    "semantic_identity_dedup_performed": True,
    "mainline_semantic_comparison_performed": True,
    "a2_payload_semantic_comparison_performed": False,
    "a2_a2plus_rows_remain_deferred": True,
    "human_content_approval_fabricated": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learner_facing_content_created": False,
}


class SemanticDedupError(ValueError):
    """Fail-closed package, source, identity, accounting, or privacy error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    core = {key: value for key, value in package.items() if key != "package_sha256"}
    if not isinstance(claimed, str) or claimed != deep.sha256_value(core):
        raise SemanticDedupError("admission_package_sha256_mismatch")


def _verify_admission(
    package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
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
        or gate.get("distance_after") != "D5"
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
    expected_summary = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_duplicate_group_count": expected_semantic_identity_count,
        "duplicate_candidate_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "final_promoted_material_count": 0,
    }
    if not isinstance(summary, Mapping):
        raise SemanticDedupError("admission_aggregate_summary_missing")
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise SemanticDedupError(
                f"admission_summary_mismatch:{key}:{summary.get(key)}:{expected}"
            )
    observed = Counter(str(row.get("admission_status") or "") for row in rows)
    if dict(sorted(observed.items())) != summary.get("admission_status_counts"):
        raise SemanticDedupError("admission_status_counts_mismatch")
    scope_rows = [
        row for row in rows
        if str(row.get("source_level") or "") in admission.A1_A1PLUS_LEVELS
    ]
    deferred_rows = [
        row for row in rows
        if str(row.get("source_level") or "") in admission.DEFERRED_LEVELS
    ]
    if len(scope_rows) != expected_scope_page_unit_count:
        raise SemanticDedupError("scope_page_unit_count_mismatch")
    if len(deferred_rows) != expected_deferred_page_unit_count:
        raise SemanticDedupError("deferred_page_unit_count_mismatch")
    if any(row.get("admission_status") != "DEFERRED_A2_A2PLUS" for row in deferred_rows):
        raise SemanticDedupError("deferred_row_status_invalid")
    return scope_rows, deferred_rows


def _verify_mainline(
    index: Mapping[str, Any], *, expected_asset_count: int | None = None
) -> list[Mapping[str, Any]]:
    if index.get("task_id") != M2_TASK_ID or index.get("validation_status") != M2_STATUS:
        raise SemanticDedupError("mainline_m2_identity_invalid")
    if index.get("errors") != []:
        raise SemanticDedupError("mainline_m2_errors_not_empty")
    records = index.get("asset_records")
    if not isinstance(records, list) or not all(isinstance(row, Mapping) for row in records):
        raise SemanticDedupError("mainline_asset_records_invalid")
    if expected_asset_count is not None and len(records) != expected_asset_count:
        raise SemanticDedupError(
            f"mainline_asset_count_mismatch:{len(records)}:{expected_asset_count}"
        )
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
        raise SemanticDedupError(
            f"source_file_resolution_not_unique:{level}:{len(unique)}"
        )
    return unique[0]


def load_raz_texts(
    source_root: Path,
    *,
    levels: Sequence[str] = admission.A1_A1PLUS_LEVELS,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    texts: dict[str, str] = {}
    source_index: list[dict[str, Any]] = []
    for level in levels:
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
                raise SemanticDedupError(
                    f"source_identity_or_text_invalid:{level}:{ref}"
                )
            texts[ref] = text
        source_index.append({
            "level": level,
            "source_path": path.relative_to(source_root).as_posix()
            if path.is_relative_to(source_root) else str(path),
            "record_count": len(payload),
            "sha256": deep.sha256_file(path),
        })
    if len(texts) != expected_scope_page_unit_count:
        raise SemanticDedupError(
            f"source_text_count_mismatch:{len(texts)}:{expected_scope_page_unit_count}"
        )
    return texts, source_index


def _normalize(value: str) -> str:
    return " ".join(
        token.casefold().replace("’", "'") for token in TOKEN_RE.findall(value)
    )


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


def _mainline_text_units(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
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
        payload = asset.get("payload")
        if not asset_key or not isinstance(payload, Mapping):
            raise SemanticDedupError(f"mainline_asset_invalid:{asset_key}")
        for path, text in _strings(payload):
            normalized = _normalize(text)
            token_set = frozenset(normalized.split())
            if len(token_set) < 2:
                continue
            text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            identity = (asset_key, path, text_hash)
            if identity in seen:
                continue
            seen.add(identity)
            units.append({
                "asset_key": asset_key,
                "lesson_id": str(asset.get("lesson_id") or ""),
                "skill": str(asset.get("skill") or ""),
                "level": "A1_PLUS" if level == "A1+" else "A1",
                "role": str(asset.get("role") or ""),
                "payload_path_sha256": hashlib.sha256(path.encode("utf-8")).hexdigest(),
                "normalized_sha256": text_hash,
                "normalized": normalized,
                "tokens": token_set,
            })
    if not units:
        raise SemanticDedupError("mainline_learning_text_units_empty")
    units.sort(
        key=lambda row: (
            row["asset_key"], row["payload_path_sha256"], row["normalized_sha256"]
        )
    )
    return units, a2_skipped


def _row_strings(row: Mapping[str, Any], key: str) -> set[str]:
    values = row.get(key, [])
    if not isinstance(values, list):
        raise SemanticDedupError(f"row_list_field_invalid:{key}")
    return {str(value) for value in values if isinstance(value, str) and value}


def _hypothetical(row: Mapping[str, Any]) -> tuple[str, str, list[str]]:
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
    status, scope, reasons = _hypothetical(row)
    vocabulary = _row_strings(row, "matched_vocabulary_refs")
    grammar = _row_strings(row, "matched_grammar_unit_refs")
    chunks = _row_strings(row, "matched_chunk_refs")
    patterns = _row_strings(row, "matched_pattern_refs")
    themes = _row_strings(row, "candidate_theme_refs")
    skills = _row_strings(row, "four_skill_affordances")
    vector = {
        "admission_tier": STATUS_TIER[status],
        "authority_dimension_count": sum(
            bool(values) for values in (vocabulary, grammar, chunks, patterns, themes)
        ),
        "matched_authority_ref_count": sum(
            len(values) for values in (vocabulary, grammar, chunks, patterns, themes)
        ),
        "four_skill_affordance_count": len(skills),
        "sentence_seed_maturity_tier": MATURITY_TIER.get(
            str(row.get("sentence_seed_maturity") or ""), 0
        ),
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


def _representatives(
    scope_rows: Sequence[Mapping[str, Any]],
    *,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
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
            f"semantic_identity_count_mismatch:{len(grouped)}:{expected_semantic_identity_count}"
        )
    representative_rows: list[dict[str, Any]] = []
    duplicate_bindings: list[dict[str, Any]] = []
    changed_count = 0
    classification_conflict_count = 0
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
        candidates = [_candidate(row) for row in members]
        winner = min(candidates, key=_rank_key)
        winner_ref = str(winner["source_unit_ref"])
        winner_row = winner["row"]
        status_set = {
            str(candidate["representative_admission_status"]) for candidate in candidates
        }
        scope_set = {str(candidate["candidate_cefr_scope"]) for candidate in candidates}
        classification_conflict_count += int(len(status_set) > 1 or len(scope_set) > 1)
        changed = winner_ref != provisional
        changed_count += int(changed)
        same_vector_count = sum(
            candidate["quality_vector"] == winner["quality_vector"]
            for candidate in candidates
        )
        selection_reasons = ["HIGHEST_DEDUP_QUALITY_VECTOR"]
        if same_vector_count > 1:
            selection_reasons.append("SOURCE_UNIT_REF_STABLE_TIEBREAKER")
        representative_rows.append({
            "semantic_duplicate_group_id": group,
            "selected_source_unit_ref": winner_ref,
            "source_level": str(winner_row.get("source_level") or ""),
            "source_book_id": str(winner_row.get("source_book_id") or ""),
            "member_count": len(members),
            "member_source_unit_refs": sorted(member_refs),
            "duplicate_member_count": len(members) - 1,
            "s01_provisional_representative_source_unit_ref": provisional,
            "representative_changed_from_s01": changed,
            "representative_admission_status": winner[
                "representative_admission_status"
            ],
            "candidate_cefr_scope": winner["candidate_cefr_scope"],
            "representative_reason_codes": list(winner["representative_reason_codes"]),
            "selection_reason_codes": selection_reasons,
            "quality_vector": dict(winner["quality_vector"]),
            "member_hypothetical_statuses": sorted(status_set),
            "member_candidate_cefr_scopes": sorted(scope_set),
            "classification_conflict_observed": len(status_set) > 1 or len(scope_set) > 1,
            "candidate_theme_refs": sorted(_row_strings(winner_row, "candidate_theme_refs")),
            "matched_vocabulary_refs": sorted(
                _row_strings(winner_row, "matched_vocabulary_refs")
            ),
            "matched_chunk_refs": sorted(_row_strings(winner_row, "matched_chunk_refs")),
            "matched_pattern_refs": sorted(
                _row_strings(winner_row, "matched_pattern_refs")
            ),
            "matched_grammar_unit_refs": sorted(
                _row_strings(winner_row, "matched_grammar_unit_refs")
            ),
            "sentence_seed_maturity": str(
                winner_row.get("sentence_seed_maturity") or ""
            ),
            "passage_seed_status": str(winner_row.get("passage_seed_status") or ""),
            "discourse_shape": str(winner_row.get("discourse_shape") or ""),
            "scene_structure": str(winner_row.get("scene_structure") or ""),
            "four_skill_affordances": sorted(
                _row_strings(winner_row, "four_skill_affordances")
            ),
        })
        for member in sorted(members, key=lambda row: str(row["source_unit_ref"])):
            member_ref = str(member["source_unit_ref"])
            if member_ref == winner_ref:
                continue
            duplicate_bindings.append({
                "semantic_duplicate_group_id": group,
                "duplicate_source_unit_ref": member_ref,
                "representative_source_unit_ref": winner_ref,
                "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE",
            })
    if len(duplicate_bindings) != expected_duplicate_binding_count:
        raise SemanticDedupError(
            f"duplicate_binding_count_mismatch:{len(duplicate_bindings)}:{expected_duplicate_binding_count}"
        )
    return (
        representative_rows,
        duplicate_bindings,
        changed_count,
        classification_conflict_count,
    )


def _indexes(
    units: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
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
    overlaps: Counter[int] = Counter()
    for token in source_tokens:
        overlaps.update(postings.get(token, []))
    ranked: list[tuple[float, float, float, str, int]] = []
    for index, overlap in overlaps.most_common(250):
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
        ranked.append(
            (jaccard, containment, length_ratio, str(units[index]["asset_key"]), index)
        )
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


def _skill_names(affordances: Sequence[str]) -> set[str]:
    mapping = {
        "READING_SOURCE": "READING",
        "LISTENING_ADAPTATION": "LISTENING",
        "SPEAKING_PROMPT": "SPEAKING",
        "WRITING_MODEL": "WRITING",
    }
    return {mapping[value] for value in affordances if value in mapping}


def _disposition(
    representative: Mapping[str, Any], match: Mapping[str, Any] | None
) -> tuple[str, str, bool]:
    status = str(representative["representative_admission_status"])
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
    if match["match_kind"] in {"EXACT", "NEAR"} and candidate_scope not in matched_levels:
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
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
    expected_mainline_asset_count: int | None = None,
) -> dict[str, Any]:
    scope_rows, deferred_rows = _verify_admission(
        admission_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    mainline_records = _verify_mainline(
        mainline_index, expected_asset_count=expected_mainline_asset_count
    )
    scope_refs = {str(row["source_unit_ref"]) for row in scope_rows}
    if scope_refs != set(raz_texts):
        raise SemanticDedupError("admission_source_text_identity_mismatch")
    (
        representatives,
        duplicate_bindings,
        changed_count,
        classification_conflict_count,
    ) = _representatives(
        scope_rows,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
    )
    mainline_units, a2_skipped = _mainline_text_units(mainline_records)
    exact_index, postings = _indexes(mainline_units)
    output_rows: list[dict[str, Any]] = []
    disposition_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    unresolved_conflicts = 0
    for representative in representatives:
        ref = str(representative["selected_source_unit_ref"])
        status = str(representative["representative_admission_status"])
        match = (
            _match(raz_texts[ref], mainline_units, exact_index, postings)
            if status in READY_STATUSES else None
        )
        disposition, resolution, linkable = _disposition(representative, match)
        if (
            disposition == "CONFLICTING_AUTHORITY_MAPPING"
            and resolution != "RESOLVED_BY_EXCLUSION_FROM_LINKAGE"
        ):
            unresolved_conflicts += 1
        disposition_counts[disposition] += 1
        status_counts[status] += 1
        output_rows.append({
            **representative,
            "mainline_match": _safe_match(match),
            "dedup_disposition": disposition,
            "conflict_resolution": resolution,
            "ready_for_canonical_linkage": linkable,
            "promotion_status": "NOT_PROMOTED",
        })
    deferred_registry = [
        {
            "source_unit_ref": str(row["source_unit_ref"]),
            "source_level": str(row.get("source_level") or ""),
            "source_book_id": str(row.get("source_book_id") or ""),
            "semantic_duplicate_group_id": str(
                row.get("semantic_duplicate_group_id") or ""
            ),
            "candidate_theme_refs": sorted(
                _row_strings(row, "candidate_theme_refs")
            ),
            "matched_vocabulary_refs": sorted(
                _row_strings(row, "matched_vocabulary_refs")
            ),
            "matched_chunk_refs": sorted(_row_strings(row, "matched_chunk_refs")),
            "matched_pattern_refs": sorted(
                _row_strings(row, "matched_pattern_refs")
            ),
            "matched_grammar_unit_refs": sorted(
                _row_strings(row, "matched_grammar_unit_refs")
            ),
            "defer_reason": "OUTSIDE_APPROVED_A1_A1PLUS_PROGRAM_SCOPE",
            "admission_status": "DEFERRED_A2_A2PLUS",
        }
        for row in sorted(deferred_rows, key=lambda item: str(item["source_unit_ref"]))
    ]
    representative_refs = {row["selected_source_unit_ref"] for row in output_rows}
    duplicate_refs = {row["duplicate_source_unit_ref"] for row in duplicate_bindings}
    checks = {
        "one_representative_per_semantic_identity": (
            len(output_rows) == expected_semantic_identity_count
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
        "all_representatives_dispositioned": (
            sum(disposition_counts.values()) == expected_semantic_identity_count
        ),
        "unresolved_conflict_count_zero": unresolved_conflicts == 0,
        "deferred_registry_reconciled": (
            len(deferred_registry) == expected_deferred_page_unit_count
        ),
        "a2_payload_comparison_not_performed": all(
            row.get("level") != "A2" for row in mainline_units
        ),
        "ready_representatives_authority_complete": all(
            row["matched_vocabulary_refs"] and row["matched_grammar_unit_refs"]
            for row in output_rows
            if row["representative_admission_status"] in READY_STATUSES
        ),
        "no_promoted_rows": all(
            row["promotion_status"] == "NOT_PROMOTED" for row in output_rows
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
            "mainline_task_id": mainline_index["task_id"],
            "mainline_index_sha256": mainline_index_sha256,
        },
        "scope_contract": {
            "a1_a1plus_observational_levels": list(admission.A1_A1PLUS_LEVELS),
            "deferred_levels": list(admission.DEFERRED_LEVELS),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "private_source_index": [dict(row) for row in source_index],
        "mainline_index_summary": {
            "asset_record_count": len(mainline_records),
            "learning_text_unit_count": len(mainline_units),
            "a2_asset_record_count_skipped_without_payload_traversal": a2_skipped,
        },
        "semantic_representatives": output_rows,
        "duplicate_bindings": duplicate_bindings,
        "deferred_a2_a2plus_registry": deferred_registry,
        "aggregate_summary": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": len(output_rows),
            "representative_count": len(output_rows),
            "duplicate_binding_count": len(duplicate_bindings),
            "deferred_a2_a2plus_count": len(deferred_registry),
            "representative_status_counts": dict(sorted(status_counts.items())),
            "dedup_disposition_counts": dict(sorted(disposition_counts.items())),
            "ready_representative_count": sum(
                status_counts[status] for status in READY_STATUSES
            ),
            "linkage_candidate_count": sum(
                row["ready_for_canonical_linkage"] for row in output_rows
            ),
            "classification_conflict_group_count": classification_conflict_count,
            "representative_changed_from_s01_count": changed_count,
            "unresolved_conflict_count": unresolved_conflicts,
            "final_promoted_material_count": 0,
        },
        "dedup_gate": {
            "source_checks": checks,
            "decision": (
                "MAINLINE_SEMANTIC_DEDUP_READY"
                if ready else "BLOCKED_MAINLINE_SEMANTIC_DEDUP"
            ),
            "distance_before": "D5",
            "distance_after": "D4" if ready else "D5",
            "ready_for_authority_linkage": ready,
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
        mainline_index, mainline_sha = _read_json_object(
            args.mainline_consumer, "mainline"
        )
        raz_texts, source_index = load_raz_texts(args.source_root)
        output = build_package(
            admission_package,
            mainline_index,
            raz_texts,
            source_index,
            mainline_index_sha256=mainline_sha,
        )
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
