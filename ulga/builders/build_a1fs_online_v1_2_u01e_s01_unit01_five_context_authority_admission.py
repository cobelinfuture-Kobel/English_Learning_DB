#!/usr/bin/env python3
"""Admit the Unit 01 five-context material-first language target package.

The five context texts are project-authored and fixed. Canonical vocabulary,
chunk, pattern, and EGP identities are selected only from committed authorities.
The existing eleven Unit 01 response contracts are consumed read-only to build
an asset target index without exposing hidden answers or learner responses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01
from ulga.builders import build_a1fs_v1_cp02_per_unit_authority_bindings as cp02
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.query.a1_a1plus_authority_scope_query import build_scope

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S01_"
    "Unit01FiveContextMaterialFirstAuthorityAdmission"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s01.unit01_five_context_admission.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S01_FIVE_CONTEXT_AUTHORITY_ADMISSION"
DECISION_REF = "OPERATOR_APPROVAL:2026-07-28:U01E-S00-S05"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.2-U01E-S02_"
    "Unit01MultiStandardQuestionGenerationContextPack"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
CAMBRIDGE_POLICY_PATH = REPO_ROOT / "ulga/evidence/e4s_a1v1_m11a_cambridge_alignment_policy.json"

EXPECTED_CONTEXT_COUNT = 5
EXPECTED_EXISTING_ASSET_COUNT = 11
PRODUCTIVE_TARGET_RANGE = (6, 10)
RECEPTIVE_TARGET_RANGE = (5, 10)
CHUNK_TARGET_RANGE = (4, 8)
CORE_SENTENCE_RANGE = (3, 6)

CONTEXTS: tuple[dict[str, Any], ...] = (
    {
        "context_id": "U01-C1-CLASSROOM-BAG",
        "role": "ANCHOR_CONTEXT",
        "setting": "CLASSROOM",
        "title": "Mia's classroom bag",
        "sentences": [
            "Mia is in a classroom.",
            "She has a bag and a book.",
            "There is an apple in the bag.",
            "A cat is near the door.",
            "Mia puts the book on the desk.",
            "Later, she eats the apple.",
        ],
        "core_sentence_index": 2,
        "source_role": "EXISTING_APPROVED_UNIT01_ANCHOR",
    },
    {
        "context_id": "U01-C2-HOME-TOY-BOX",
        "role": "NEAR_TRANSFER",
        "setting": "HOME",
        "title": "A toy in the living room",
        "sentences": [
            "There is a CD player in the living room.",
            "A toy is in a box near the bed.",
            "The toy is a robot.",
        ],
        "core_sentence_index": 1,
        "source_role": "PROJECT_AUTHORED_RAZ_GROUNDED_CONTEXT",
    },
    {
        "context_id": "U01-C3-PICNIC-FOOD",
        "role": "EXTENDED_CONTEXT",
        "setting": "FOOD_AND_PICNIC",
        "title": "Food for a picnic",
        "sentences": [
            "Mia has an orange and an egg in a basket.",
            "There is an ice cream near the basket.",
            "The orange is for the picnic.",
        ],
        "core_sentence_index": 0,
        "source_role": "PROJECT_AUTHORED_RAZ_GROUNDED_CONTEXT",
    },
    {
        "context_id": "U01-C4-TOY-SHOP",
        "role": "FUNCTIONAL_DIALOGUE_CONTEXT",
        "setting": "SHOPPING",
        "title": "At a toy shop",
        "sentences": [
            "There is a toy shop near the bus stop.",
            "Mia sees a robot in the shop window.",
            "The robot is a toy for her friend.",
        ],
        "core_sentence_index": 0,
        "source_role": "PROJECT_AUTHORED_RAZ_GROUNDED_CONTEXT",
    },
    {
        "context_id": "U01-C5-PARK-BIRTHDAY",
        "role": "UNSEEN_TRANSFER",
        "setting": "PARK_AND_BIRTHDAY",
        "title": "A birthday party in the park",
        "sentences": [
            "There is a birthday party in the park.",
            "A dog is near a tree and a bench.",
            "The dog has a toy.",
        ],
        "core_sentence_index": 0,
        "source_role": "PROJECT_AUTHORED_UNSEEN_TRANSFER",
    },
)

PRODUCTIVE_PRIORITY = (
    "bag", "book", "apple", "cat", "box", "toy", "orange", "egg", "robot", "dog"
)
RECEPTIVE_PRIORITY = (
    "classroom", "door", "desk", "room", "bed", "shop", "park", "tree", "bench", "window"
)
CHUNK_PRIORITY = (
    "cd player", "living room", "ice cream", "toy shop", "bus stop", "birthday party",
    "in the bag", "near the door", "on the desk",
)
ASSESSMENT_PATTERN_BY_MODE = {
    "EXACT_OPTION": "multiple_choice",
    "EXACT_SEQUENCE": "word_order",
    "NORMALIZED_TEXT": "guided_sentence",
    "FEATURE_RUBRIC": "guided_sentence",
}


class S01AdmissionError(ValueError):
    """Fail-closed Unit 01 material or authority admission error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def words(value: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", str(value).casefold())


def phrase(value: str) -> str:
    return " ".join(words(value))


def all_context_text() -> str:
    return " ".join(sentence for context in CONTEXTS for sentence in context["sentences"])


def sentence_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for context in CONTEXTS:
        for index, text in enumerate(context["sentences"], start=1):
            rows.append(
                {
                    "sentence_id": f"sentence:u01e:{context['context_id'].casefold()}:{index:02d}",
                    "context_id": context["context_id"],
                    "text": text,
                    "learning_role": (
                        "CORE_NEW_SENTENCE"
                        if index - 1 == int(context["core_sentence_index"])
                        else "SUPPORT_SENTENCE"
                    ),
                    "source_role": context["source_role"],
                }
            )
    return rows


def unique_a1_vocabulary(scope: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, list[str]]]:
    grouped: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in scope.get("authorities", {}).get("vocabulary", []):
        if isinstance(row, Mapping) and row.get("id") and phrase(str(row.get("label") or "")):
            grouped[phrase(str(row["label"]))].append(row)
    unique = {label: rows[0] for label, rows in grouped.items() if len(rows) == 1}
    ambiguous = {label: sorted(str(row["id"]) for row in rows) for label, rows in grouped.items() if len(rows) > 1}
    return unique, ambiguous


def selected_vocabulary(scope: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    unique, ambiguous = unique_a1_vocabulary(scope)
    material_words = set(words(all_context_text()))
    selected: list[dict[str, Any]] = []
    selected_labels: set[str] = set()

    def choose(priority: Iterable[str], role: str, limit: int) -> None:
        for raw_label in priority:
            label = phrase(raw_label)
            if len([row for row in selected if row["learning_role"] == role]) >= limit:
                break
            row = unique.get(label)
            if not row or label not in material_words or label in selected_labels:
                continue
            selected.append(
                {
                    "authority_id": str(row["id"]),
                    "label": str(row.get("label") or label),
                    "part_of_speech": row.get("part_of_speech"),
                    "learning_role": role,
                    "selection_method": "EXACT_UNIQUE_A1_AUTHORITY_LABEL_IN_FIXED_MATERIAL",
                    "source_ref": deepcopy(row.get("source_ref", {})),
                    "sense_binding_status": "UNIQUE_A1_SOURCE_RECORD_ID_BOUND",
                }
            )
            selected_labels.add(label)

    choose(PRODUCTIVE_PRIORITY, "NEW_PRODUCTIVE", PRODUCTIVE_TARGET_RANGE[1])
    choose(RECEPTIVE_PRIORITY, "NEW_RECEPTIVE", RECEPTIVE_TARGET_RANGE[1])
    productive_count = sum(row["learning_role"] == "NEW_PRODUCTIVE" for row in selected)
    receptive_count = sum(row["learning_role"] == "NEW_RECEPTIVE" for row in selected)
    if not PRODUCTIVE_TARGET_RANGE[0] <= productive_count <= PRODUCTIVE_TARGET_RANGE[1]:
        raise S01AdmissionError(f"productive_vocabulary_load_invalid:{productive_count}")
    if not RECEPTIVE_TARGET_RANGE[0] <= receptive_count <= RECEPTIVE_TARGET_RANGE[1]:
        raise S01AdmissionError(f"receptive_vocabulary_load_invalid:{receptive_count}")

    unselected: list[dict[str, Any]] = []
    for label in sorted(material_words):
        if label in selected_labels or len(label) < 2:
            continue
        if label in ambiguous:
            reason = "ELIGIBLE_NOT_SELECTED_AMBIGUOUS_A1_SOURCE_IDENTITY"
            candidates = ambiguous[label]
        elif label in unique:
            reason = "OBSERVED_IN_MATERIAL_ONLY"
            candidates = [str(unique[label]["id"])]
        else:
            reason = "NOT_SELECTED_NO_A1_AUTHORITY_MATCH"
            candidates = []
        unselected.append({"label": label, "status": reason, "candidate_authority_ids": candidates})
    return selected, unselected


def selected_chunks(scope: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_label = {
        phrase(str(row.get("label") or "")): row
        for row in scope.get("authorities", {}).get("chunk", [])
        if isinstance(row, Mapping) and row.get("id") and phrase(str(row.get("label") or ""))
    }
    material = f" {phrase(all_context_text())} "
    rows: list[dict[str, Any]] = []
    for raw_label in CHUNK_PRIORITY:
        label = phrase(raw_label)
        row = by_label.get(label)
        if not row or f" {label} " not in material:
            continue
        rows.append(
            {
                "authority_id": str(row["id"]),
                "label": str(row.get("label") or label),
                "learning_role": "NEW_CHUNK",
                "usage_class": row.get("usage_class"),
                "selection_method": "EXACT_A1_GENERATOR_SAFE_CHUNK_IN_FIXED_MATERIAL",
                "source_ref": deepcopy(row.get("source_ref", {})),
            }
        )
    if not CHUNK_TARGET_RANGE[0] <= len(rows) <= CHUNK_TARGET_RANGE[1]:
        raise S01AdmissionError(f"chunk_learning_load_invalid:{len(rows)}")
    return rows


def unit_authority_context() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scope = build_scope("A1")
    cp02_artifact = cp02.build_artifact()
    unit = next(
        (
            row for row in cp02_artifact.get("learning_units", [])
            if isinstance(row, Mapping) and row.get("grammar_unit_id") == m01.UNIT_ID
        ),
        None,
    )
    if not isinstance(unit, Mapping):
        raise S01AdmissionError("unit01_cp02_context_missing")
    grammar_ids = {str(row.get("id")) for row in scope["authorities"]["grammar"]}
    egp_rows = [str(row) for row in unit.get("canonical_egp_row_ids", [])]
    if not egp_rows or any(row not in grammar_ids for row in egp_rows):
        raise S01AdmissionError("unit01_egp_binding_invalid")
    pattern_binding = unit.get("authority_bindings", {}).get("pattern", {})
    pattern_refs = list(pattern_binding.get("selected_refs", []))
    allowed_patterns = {str(row.get("id")): row for row in scope["authorities"]["pattern"]}
    if not pattern_refs or any(ref not in allowed_patterns for ref in pattern_refs):
        raise S01AdmissionError("unit01_pattern_binding_missing_or_invalid")
    patterns = [
        {
            "authority_id": ref,
            "label": allowed_patterns[ref].get("label"),
            "learning_role": "CORE_SENTENCE_PATTERN",
            "selection_method": "CP02_CANONICAL_EGP_TO_PATTERN_LINEAGE",
            "source_ref": deepcopy(allowed_patterns[ref].get("source_ref", {})),
        }
        for ref in pattern_refs
    ]
    return scope, unit, {"egp_row_ids": egp_rows, "patterns": patterns}


def cambridge_context() -> dict[str, Any]:
    policy = json.loads(CAMBRIDGE_POLICY_PATH.read_text(encoding="utf-8"))
    alignment = next(
        row for row in policy["unit_alignment"] if row["grammar_unit_id"] == m01.UNIT_ID
    )
    if alignment["cambridge_stage"] != "STARTERS" or alignment["policy_decision"] != "AUTO_PASS":
        raise S01AdmissionError("unit01_cambridge_policy_invalid")
    return {
        "cambridge_stage": "STARTERS",
        "policy_decision": "AUTO_PASS",
        "evidence_refs": list(alignment["evidence_refs"]),
        "task_compatibility": deepcopy(policy["task_compatibility"]),
        "granular_capability_refs": [],
        "granular_capability_status": "UNRESOLVED_COMMITTED_DENOMINATOR_NOT_AVAILABLE",
        "flyers_or_a2_promoted": False,
    }


def load_contracts(database_path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    lesson_ids = list(m01.LESSON_IDS.values())
    placeholders = ",".join("?" for _ in lesson_ids)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT asset_key,lesson_id,skill,role,capture_enabled,contract_json "
            f"FROM response_contracts WHERE lesson_id IN ({placeholders}) ORDER BY lesson_id,asset_key",
            tuple(lesson_ids),
        ).fetchall()
    if len(rows) != EXPECTED_EXISTING_ASSET_COUNT:
        raise S01AdmissionError(f"unit01_response_contract_count_invalid:{len(rows)}")
    assets: list[dict[str, Any]] = []
    contracts: dict[str, dict[str, Any]] = {}
    for row in rows:
        asset_key = str(row["asset_key"])
        contract = json.loads(str(row["contract_json"]))
        if not isinstance(contract, dict):
            raise S01AdmissionError(f"response_contract_not_object:{asset_key}")
        contract.update(
            {
                "asset_key": asset_key,
                "lesson_id": str(row["lesson_id"]),
                "role": str(row["role"]),
                "capture_enabled": bool(row["capture_enabled"]),
            }
        )
        contracts[asset_key] = contract
        assets.append(
            {
                "asset_key": asset_key,
                "lesson_id": str(row["lesson_id"]),
                "skill": str(row["skill"]),
                "role": str(row["role"]),
            }
        )
    return assets, contracts


def accepted_phrase(contract: Mapping[str, Any]) -> str:
    texts = contract.get("accepted_texts")
    if isinstance(texts, list) and texts:
        return phrase(str(texts[0]))
    sequence = contract.get("accepted_sequence")
    if isinstance(sequence, list) and sequence:
        return phrase(" ".join(str(row) for row in sequence))
    return ""


def refs_in_text(text: str, vocabulary: Sequence[Mapping[str, Any]]) -> list[str]:
    tokens = set(words(text))
    return sorted(
        str(row["authority_id"])
        for row in vocabulary
        if phrase(str(row["label"])) in tokens
    )


def chunks_in_text(text: str, chunks: Sequence[Mapping[str, Any]]) -> list[str]:
    normalized = f" {phrase(text)} "
    return sorted(
        str(row["authority_id"])
        for row in chunks
        if f" {phrase(str(row['label']))} " in normalized
    )


def sentence_ids_by_context(sentences: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    result: defaultdict[str, list[str]] = defaultdict(list)
    for row in sentences:
        result[str(row["context_id"])].append(str(row["sentence_id"]))
    return dict(result)


def build_existing_asset_target_index(
    *, database_path: Path, vocabulary: Sequence[Mapping[str, Any]], chunks: Sequence[Mapping[str, Any]],
    egp_rows: Sequence[str], patterns: Sequence[Mapping[str, Any]], sentences: Sequence[Mapping[str, Any]],
    cambridge: Mapping[str, Any],
) -> list[dict[str, Any]]:
    assets, contracts = load_contracts(database_path)
    by_lesson: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for asset in assets:
        by_lesson[asset["lesson_id"]].append(asset)
    context_sentence_ids = sentence_ids_by_context(sentences)
    pattern_ids = sorted(str(row["authority_id"]) for row in patterns)
    rows: list[dict[str, Any]] = []

    reading_assets = by_lesson[m01.LESSON_IDS["READING"]]
    reading_assignments = m01.assign_reading_specs(reading_assets, contracts)
    for asset in reading_assets:
        key = asset["asset_key"]
        spec = reading_assignments[key]
        target_text = str(spec["accepted_text"])
        rows.append(
            {
                "asset_key": key,
                "lesson_id": asset["lesson_id"],
                "skill": "READING",
                "spec_id": spec["spec_id"],
                "question_type": "checkpoint_choice" if asset["role"] == "CHK" else "multiple_choice",
                "assessment_pattern_ref": "checkpoint_choice" if asset["role"] == "CHK" else "multiple_choice",
                "context_id": "U01-C1-CLASSROOM-BAG",
                "target_evp_sense_ids": refs_in_text(target_text, vocabulary),
                "target_egp_row_ids": sorted(egp_rows),
                "target_chunk_ids": chunks_in_text(target_text, chunks),
                "target_sentence_ids": context_sentence_ids["U01-C1-CLASSROOM-BAG"],
                "target_pattern_ids": pattern_ids,
                "target_ket_prerequisite_node_ids": [],
                "ket_binding_status": "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
                "cambridge_stage": cambridge["cambridge_stage"],
                "binding_status": "RESOLVED_LANGUAGE_TARGETS_KET_PENDING",
            }
        )

    writing_assets = sorted(by_lesson[m01.LESSON_IDS["WRITING"]], key=lambda row: row["asset_key"])
    for index, asset in enumerate(writing_assets, start=1):
        key = asset["asset_key"]
        contract = contracts[key]
        spec = m01.writing_spec_for_contract(asset=asset, contract=contract, index=index)
        target_text = accepted_phrase(contract)
        mode = str(contract.get("scoring_mode") or "")
        assessment = "checkpoint_write" if asset["role"] == "CHK" else ASSESSMENT_PATTERN_BY_MODE.get(mode, "guided_sentence")
        rows.append(
            {
                "asset_key": key,
                "lesson_id": asset["lesson_id"],
                "skill": "WRITING",
                "spec_id": spec["spec_id"],
                "question_type": assessment,
                "assessment_pattern_ref": assessment,
                "context_id": "U01-C1-CLASSROOM-BAG",
                "target_evp_sense_ids": refs_in_text(target_text, vocabulary),
                "target_egp_row_ids": sorted(egp_rows),
                "target_chunk_ids": chunks_in_text(target_text, chunks),
                "target_sentence_ids": context_sentence_ids["U01-C1-CLASSROOM-BAG"],
                "target_pattern_ids": pattern_ids,
                "target_ket_prerequisite_node_ids": [],
                "ket_binding_status": "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
                "cambridge_stage": cambridge["cambridge_stage"],
                "binding_status": "RESOLVED_LANGUAGE_TARGETS_KET_PENDING",
            }
        )

    speaking_assets = sorted(by_lesson[m01.LESSON_IDS["SPEAKING"]], key=lambda row: row["asset_key"])
    for asset, spec in zip(speaking_assets, m01.SPEAKING_SPECS, strict=True):
        model = str(spec["model"])
        rows.append(
            {
                "asset_key": asset["asset_key"],
                "lesson_id": asset["lesson_id"],
                "skill": "SPEAKING",
                "spec_id": spec["spec_id"],
                "question_type": "guided_sentence",
                "assessment_pattern_ref": "guided_sentence",
                "context_id": "U01-C1-CLASSROOM-BAG",
                "target_evp_sense_ids": refs_in_text(model, vocabulary),
                "target_egp_row_ids": sorted(egp_rows),
                "target_chunk_ids": chunks_in_text(model, chunks),
                "target_sentence_ids": context_sentence_ids["U01-C1-CLASSROOM-BAG"],
                "target_pattern_ids": pattern_ids,
                "target_ket_prerequisite_node_ids": [],
                "ket_binding_status": "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
                "cambridge_stage": cambridge["cambridge_stage"],
                "binding_status": "RESOLVED_LANGUAGE_TARGETS_KET_PENDING",
                "evidence_policy": "EXPOSURE_ONLY_NO_SCORING_NO_MASTERY",
            }
        )
    rows.sort(key=lambda row: (row["lesson_id"], row["asset_key"]))
    if len(rows) != EXPECTED_EXISTING_ASSET_COUNT or len({row["asset_key"] for row in rows}) != len(rows):
        raise S01AdmissionError("existing_asset_target_index_invalid")
    return rows


def candidate_payload(database_path: Path) -> dict[str, Any]:
    scope, unit, unit_authority = unit_authority_context()
    vocabulary, unselected = selected_vocabulary(scope)
    chunks = selected_chunks(scope)
    sentences = sentence_rows()
    core_sentences = [row for row in sentences if row["learning_role"] == "CORE_NEW_SENTENCE"]
    if not CORE_SENTENCE_RANGE[0] <= len(core_sentences) <= CORE_SENTENCE_RANGE[1]:
        raise S01AdmissionError(f"core_sentence_load_invalid:{len(core_sentences)}")
    cambridge = cambridge_context()
    asset_index = build_existing_asset_target_index(
        database_path=database_path,
        vocabulary=vocabulary,
        chunks=chunks,
        egp_rows=unit_authority["egp_row_ids"],
        patterns=unit_authority["patterns"],
        sentences=sentences,
        cambridge=cambridge,
    )
    return {
        "content_id": "A1FS_V1_2_UNIT01_FIVE_CONTEXT_LANGUAGE_ADMISSION",
        "unit_id": m01.UNIT_ID,
        "level_scope": ["A1"],
        "selection_model": "MATERIAL_FIRST_AUTHORITY_CONTROLLED",
        "contexts": [deepcopy(row) for row in CONTEXTS],
        "language_targets": {
            "vocabulary": vocabulary,
            "chunks": chunks,
            "sentences": sentences,
            "patterns": unit_authority["patterns"],
            "egp_row_ids": unit_authority["egp_row_ids"],
        },
        "unselected_material_vocabulary": unselected,
        "existing_asset_target_index": asset_index,
        "cambridge_alignment": cambridge,
        "ket_prerequisite_alignment": {
            "required_denominator_source": "A1FS_V1_M1_PRIVATE_GRAPH",
            "activity_level_bridge_status": "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
            "target_node_ids": [],
            "coverage_claim_allowed": False,
        },
        "source_policy": {
            "content_origin": "PROJECT_AUTHORED_FIXED_MATERIAL",
            "existing_anchor_task_id": m01.TASK_ID,
            "cp02_authority_task_id": cp02.TASK_ID,
            "raz_role": "CONTEXT_GROUNDING_ONLY_NO_RAW_TEXT_COPY",
            "raw_raz_text_copied": False,
            "raw_ket_text_copied": False,
            "canonical_authority_replaced": False,
        },
        "learning_load": {
            "new_productive_vocabulary_count": sum(row["learning_role"] == "NEW_PRODUCTIVE" for row in vocabulary),
            "new_receptive_vocabulary_count": sum(row["learning_role"] == "NEW_RECEPTIVE" for row in vocabulary),
            "new_chunk_count": len(chunks),
            "core_sentence_count": len(core_sentences),
            "pattern_count": len(unit_authority["patterns"]),
            "context_count": len(CONTEXTS),
        },
        "claim_boundaries": {
            "candidate_only_until_admitted": True,
            "learner_database_written": False,
            "response_contract_changed": False,
            "existing_asset_identity_changed": False,
            "ket_coverage_claimed": False,
            "cambridge_granular_capability_claimed": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
    }


def build_candidate(database_path: Path) -> dict[str, Any]:
    payload = candidate_payload(database_path)
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "unit01_content_task_id": m01.TASK_ID,
            "cp02_task_id": cp02.TASK_ID,
            "authority_scope_task_id": build_scope("A1")["task_id"],
            "cambridge_policy_sha256": file_digest(CAMBRIDGE_POLICY_PATH),
            "private_response_contract_database_sha256": file_digest(database_path),
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as validator,
    )

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def materialize(
    *, database_path: Path, candidate_path: Path, approved_path: Path, report_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate(database_path)
    approved = admit_candidate(candidate)
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as validator,
    )

    report = validator.validate_approved(candidate, approved)
    if report["error_count"]:
        raise S01AdmissionError("approved_validation_failed:" + "|".join(report["errors"]))
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _, _, report = materialize(
            database_path=args.database,
            candidate_path=args.candidate,
            approved_path=args.approved,
            report_path=args.report,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (
        S01AdmissionError,
        policy_artifact.ContentPolicyBuildError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
