#!/usr/bin/env python3
"""Materialize Unit06 Q06 sentence assets from GPT-5.6-authored reviewed rows.

This builder does not author learner English. It only validates current authority,
normalizes explicit authored rows, assigns deterministic IDs, preserves lineage,
and applies policy-bound candidate -> validator -> admission governance.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u06_q06_sentence_assets.json"
SEED_PATH = REPO_ROOT / "ulga/reports/a1fs_v1_u06_q06_authored_sentence_seed.json"
Q02_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u06_q02_vocabulary_carrier_authority.json"
Q03_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u06_q03_can_form_meaning_boundary_authority.json"
Q04R1_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json"
Q05_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u06_q05_core_sentence_frame_authority.json"

TASK_ID = "A1FS-V1-U06Q06_Unit06SentenceAssetProductionAndSemanticAdmission"
DECISION_REF = "OPERATOR_APPROVAL:2026-10-03:U06Q06_SENTENCE_ASSET_SEMANTIC_ADMISSION"
A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

PASS_STATUS = "PASS_A1FS_V1_U06Q06_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"
ALLOWED_DECISIONS = {"APPROVE", "CONTEXT_BOUND_APPROVE", "DEFER"}

INHERITED_FUNCTIONAL = [
    "can drink from a cup",
    "can eat an apple",
    "can go to school",
    "can make a box",
    "can play with a ball",
    "can read a book",
    "can run fast",
    "can sit on a chair",
    "can study at school",
    "can swim fast",
    "can walk to school",
    "can work at home",
    "can write with a pen",
]


class U06Q06BuildError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def normalize_sentence(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip().casefold()
    value = re.sub(r"\s+([,.!?;:])", r"\1", value)
    return re.sub(r"[.!?]+$", "", value).strip()


def _functional_surfaces(q04r1: Mapping[str, Any]) -> list[str]:
    new = q04r1["q04r1_chunk_expansion"]["non_scene_functional_chunks"]["newly_admitted_surfaces"]
    rows = [*INHERITED_FUNCTIONAL, *new]
    if len(rows) != 41 or len(set(rows)) != 41:
        raise U06Q06BuildError("Q04R1_FUNCTIONAL_DENOMINATOR_DRIFT")
    return rows


def _base_surfaces(q04r1: Mapping[str, Any]) -> list[str]:
    group = q04r1["q04r1_chunk_expansion"]["can_base_verb"]
    rows = [*group["prior_surfaces"], *group["newly_admitted_surfaces"]]
    if len(rows) != 62 or len(set(rows)) != 62:
        raise U06Q06BuildError("Q04R1_CAN_BASE_DENOMINATOR_DRIFT")
    return rows


def _current_authority_guard(contract: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    q02 = _load(Q02_PATH)
    q03 = _load(Q03_PATH)
    q04r1 = _load(Q04R1_PATH)
    q05 = _load(Q05_PATH)

    if q02["summary"]["admitted_identity_count"] != 91:
        raise U06Q06BuildError("Q02_ADMITTED_IDENTITY_DRIFT")
    if q03["status"] != "PASS_A1FS_V1_U06Q03_CAN_FORM_MEANING_BOUNDARY_AUTHORITY":
        raise U06Q06BuildError("Q03_STATUS_DRIFT")
    if q04r1["acceptance"]["course_cumulative_distinct_chunk_surfaces_after_r1"] != 266:
        raise U06Q06BuildError("Q04R1_CUMULATIVE_CHUNK_DRIFT")
    if q05["status"] != "PASS_A1FS_V1_U06Q05_UNIT06_CORE_SENTENCE_FRAME_AUTHORITY":
        raise U06Q06BuildError("Q05_STATUS_DRIFT")
    if q05["q06_primary_generation_routing"]["predecessor_sentence_pool_for_dedup"] != 27371:
        raise U06Q06BuildError("Q05_PREDECESSOR_POOL_DRIFT")
    if q05["q06_primary_generation_routing"]["exact_and_normalized_sentence_dedup_required"] is not True:
        raise U06Q06BuildError("Q05_DEDUP_REQUIREMENT_DRIFT")
    if q05["q06_primary_generation_routing"]["semantic_pedagogical_admission_required"] is not True:
        raise U06Q06BuildError("Q05_SEMANTIC_GATE_DRIFT")

    frame_ids = [row["frame_id"] for row in q05["unit06_operational_frames"]]
    if frame_ids != contract["generation_authority"]["q05_frame_ids"]:
        raise U06Q06BuildError("Q05_FRAME_AUTHORITY_DRIFT")
    return set(_base_surfaces(q04r1)), set(_functional_surfaces(q04r1))


def _seed_rows(contract: Mapping[str, Any], base_surfaces: set[str], functional_surfaces: set[str]) -> list[dict[str, Any]]:
    seed = _load(SEED_PATH)
    if seed.get("authoring_model") != "GPT-5.6 Sol":
        raise U06Q06BuildError("AUTHORING_MODEL_DRIFT")
    if seed.get("authoring_mode") != "EXPLICIT_FULL_SENTENCE_AUTHORING_AND_SEMANTIC_REVIEW":
        raise U06Q06BuildError("AUTHORING_MODE_DRIFT")
    if seed.get("python_builder_may_author_learner_english") is not False:
        raise U06Q06BuildError("PYTHON_ENGLISH_AUTHORING_FORBIDDEN")

    rows = list(seed.get("candidates", []))
    if len(rows) != contract["coverage"]["candidate_count"]:
        raise U06Q06BuildError("AUTHORED_CANDIDATE_COUNT_DRIFT")
    normalized = [normalize_sentence(row["text"]) for row in rows]
    if len(normalized) != len(set(normalized)):
        raise U06Q06BuildError("AUTHORED_SENTENCE_DUPLICATE")

    allowed_frames = set(contract["generation_authority"]["q05_frame_ids"])
    for row, normalized_text in zip(rows, normalized):
        if row.get("decision") not in ALLOWED_DECISIONS:
            raise U06Q06BuildError("INVALID_SEMANTIC_DECISION")
        if row.get("frame_id") not in allowed_frames:
            raise U06Q06BuildError("INVALID_Q05_FRAME")
        if row.get("normalized_text") != normalized_text:
            raise U06Q06BuildError("NORMALIZED_TEXT_DRIFT")
        text = str(row["text"])
        if " can " not in f" {text.casefold()} ":
            raise U06Q06BuildError("CAN_SURFACE_MISSING")
        if "?" in text or re.search(r"\b(?:cannot|can't|can\s+not)\b", text, flags=re.I):
            raise U06Q06BuildError("QUESTION_OR_NEGATIVE_LEAK")
        if re.search(r"\bcan\s+to\b", text, flags=re.I):
            raise U06Q06BuildError("CAN_TO_VERB_LEAK")

        func = row.get("source_functional_chunk_surface")
        base = row.get("source_can_base_surface")
        if func:
            if func not in functional_surfaces:
                raise U06Q06BuildError("FUNCTIONAL_CHUNK_LINEAGE_DRIFT")
        elif base not in base_surfaces:
            raise U06Q06BuildError("CAN_BASE_LINEAGE_DRIFT")
        if row["decision"] == "CONTEXT_BOUND_APPROVE" and row.get("requires_context_binding") is not True:
            raise U06Q06BuildError("CONTEXT_BOUND_FLAG_MISSING")
        if row["decision"] == "DEFER" and row.get("q07_resolution_required") is not True:
            raise U06Q06BuildError("DEFER_Q07_RESOLUTION_MISSING")
    return rows


def _build_payload() -> dict[str, Any]:
    contract = _load(CONTRACT_PATH)
    if contract.get("status") != PASS_STATUS:
        raise U06Q06BuildError("CONTRACT_STATUS_DRIFT")
    base_surfaces, functional_surfaces = _current_authority_guard(contract)
    rows = _seed_rows(contract, base_surfaces, functional_surfaces)

    new_assets: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        common = {
            "text": row["text"],
            "normalized_text": row["normalized_text"],
            "frame_id": row["frame_id"],
            "base_verb": row["base_verb"],
            "subject_class": row["subject_class"],
            "subject_surface": row["subject_surface"],
            "source_can_base_surface": row["source_can_base_surface"],
            "source_functional_chunk_surface": row.get("source_functional_chunk_surface"),
            "composition_policy": row["composition_policy"],
            "semantic_admission_class": row["decision"],
            "semantic_admission_reason": row["semantic_admission_reason"],
            "requires_context_binding": bool(row.get("requires_context_binding")),
            "requires_antecedent_binding": bool(row.get("requires_antecedent_binding")),
            "q07_resolution_required": bool(row.get("q07_resolution_required")),
        }
        if row["decision"] == "DEFER":
            excluded.append({
                "candidate_id": "U06-CAND-" + hashlib.sha256(row["normalized_text"].encode("utf-8")).hexdigest()[:20].upper(),
                **common,
                "decision": "DEFER",
            })
            continue
        new_assets.append({
            "sentence_id": "U06-SENT-" + hashlib.sha256(row["normalized_text"].encode("utf-8")).hexdigest()[:20].upper(),
            "unit_id": "GRAMMAR_CAN_STATEMENT",
            "unit_number": 6,
            "level": "A1",
            **common,
            "canonical_admission_status": "ADMITTED",
            "generation_role": "UNIT06_NEW_ADMITTED",
            "direct_unit06_assessment_allowed": not bool(row.get("requires_context_binding")),
            "scene_binding_required_at_use_time": bool(row.get("requires_context_binding")),
            "counts_as_q03_target_evidence": True,
            "source_refs": [
                "ulga/contracts/a1fs_v1_u06_q02_vocabulary_carrier_authority.json",
                "ulga/contracts/a1fs_v1_u06_q03_can_form_meaning_boundary_authority.json",
                "ulga/contracts/a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json",
                "ulga/contracts/a1fs_v1_u06_q05_core_sentence_frame_authority.json",
            ],
            "reader360_generation_authority_used": False,
            "a2_unlocked": False,
        })

    expected = contract["acceptance"]
    if len(new_assets) != expected["unit06_new_admitted_sentence_asset_count"]:
        raise U06Q06BuildError("NEW_ASSET_COUNT_DRIFT")
    if len(excluded) != expected["deferred_count"]:
        raise U06Q06BuildError("DEFERRED_COUNT_DRIFT")
    if len({row["normalized_text"] for row in new_assets}) != len(new_assets):
        raise U06Q06BuildError("USABLE_NORMALIZED_TEXT_NOT_DISTINCT")

    frame_counts = dict(sorted(Counter(row["frame_id"] for row in new_assets).items()))
    if frame_counts != contract["coverage"]["frame_counts"]:
        raise U06Q06BuildError("FRAME_COVERAGE_DRIFT")
    subject_counts = dict(sorted(Counter(row["subject_class"] for row in new_assets).items()))
    if subject_counts != dict(sorted(contract["coverage"]["subject_class_counts"].items())):
        raise U06Q06BuildError("SUBJECT_COVERAGE_DRIFT")

    return {
        **contract,
        "reuse_bindings": [],
        "new_sentence_assets": new_assets,
        "excluded_candidates": excluded,
    }


def build_candidate() -> dict[str, Any]:
    payload = _build_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "q02_authority_path": str(Q02_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "q03_authority_path": str(Q03_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "q04r1_authority_path": str(Q04R1_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "q05_authority_path": str(Q05_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "q06_contract_path": str(CONTRACT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "q06_authored_seed_path": str(SEED_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "predecessor_dedup_denominator": payload["predecessor_dedup_receipt"]["predecessor_asset_row_count"],
            "usable_sentence_supply_count": payload["coverage"]["usable_sentence_supply_count"],
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u06_q06_sentence_assets as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def build_report() -> dict[str, Any]:
    return admit_candidate(build_candidate())["payload"]


def main() -> int:
    from ulga.validators import validate_a1fs_v1_u06_q06_sentence_assets as validator

    candidate = build_candidate()
    approved = admit_candidate(candidate)
    result = validator.validate_approved(candidate, approved)
    report = approved["payload"]
    a = report["acceptance"]
    print(f"STATUS={report['status']}")
    print(f"CANDIDATES={a['authored_candidate_count']}")
    print(f"USABLE={a['semantic_review_usable_count']}")
    print(f"NEW={a['unit06_new_admitted_sentence_asset_count']}")
    print(f"DEFERRED={a['deferred_count']}")
    print(f"ERROR_COUNT={result['error_count']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
