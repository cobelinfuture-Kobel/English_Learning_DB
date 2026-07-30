#!/usr/bin/env python3
"""Build stable Unit01 language-asset bindings for cumulative later-unit reuse."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Materializes reference bindings from the approved Unit01 contract only; no new learner text, question bank, answer key, scoring, state, audio, A2 production target, or parallel curriculum is created."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01DATA01_Unit01CumulativeReusableLanguageAssetRegistryMaterialization"
SCHEMA_VERSION = "a1fs.v1.u01data01.unit01_cumulative_reusable_language_asset_registry.v1"
PASS_STATUS = "PASS_A1FS_V1_U01DATA01_UNIT01_CUMULATIVE_REUSABLE_LANGUAGE_ASSET_REGISTRY"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
APPROVED_CONTRACT_SHA256 = "114376e997275a5ac387d69a16d9d3304096605392c6928e49863d4214efbc29"
DEFAULT_CONTRACT = contract_builder.DEFAULT_OUTPUT
DEFAULT_APPROVAL = Path("ulga/graph/a1fs_v1_razq01b2_unit01_content_contract_approval_v2.json")
DEFAULT_OUTPUT = Path("ulga/graph/a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry.json")
NEXT_SHORT_STEP = "A1FS-V1-U01DATA02_Unit01SentenceAssetAndThreeSkillQuestionProjectionBuild"
FUTURE_ROLES = ("PREREQUISITE", "CARRY_OVER", "RECOMBINATION", "SCHEDULED_REVIEW", "WEAK_REMEDIATION", "TRANSFER", "ASSESSMENT_SUPPORT")
SELECTION_GATES = ("PREREQUISITE_UNLOCKED", "LEVEL_SCOPE_ALLOWED", "SEMANTIC_COMPATIBILITY_PASS", "NEW_GRAMMAR_COMPATIBILITY_PASS", "NO_UNINTRODUCED_GRAMMAR", "DEDUPLICATION_PASS", "REUSE_REASON_RECORDED")
FORBIDDEN_CONTENT_KEYS = frozenset({"question_id", "prompt", "answer", "answer_key", "learner_id", "score"})
SLUG_RE = re.compile(r"[^A-Z0-9]+")


class RegistryBuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _slug(value: str) -> str:
    return SLUG_RE.sub("-", value.upper()).strip("-") or "ITEM"


def _norm(value: str) -> str:
    return " ".join(value.lower().replace("’", "'").split())


def _base(binding_id: str, asset_id: str, kind: str) -> dict[str, Any]:
    return {"binding_id": binding_id, "asset_id": asset_id, "asset_kind": kind, "introduced_unit_id": UNIT_ID, "introduced_unit_sequence": 1, "available_from_unit_sequence": 1, "unit01_role": "NEW_TARGET", "reuse_identity_mode": "REFERENCE_EXISTING_ASSET_ID", "copy_on_reuse": False, "reusable_in_later_units": True, "eligible_future_unit_roles": list(FUTURE_ROLES)}


def _approve(contract: Mapping[str, Any], approval: Mapping[str, Any]) -> None:
    contract_builder.verify_contract_digest(contract)
    if contract.get("contract_sha256") != APPROVED_CONTRACT_SHA256:
        raise RegistryBuildError("UNIT01_APPROVED_CONTRACT_DIGEST_INVALID")
    if approval.get("unit_id") != UNIT_ID or approval.get("decision_status") != "APPROVED_AS_RECONCILED" or approval.get("approved_contract_sha256") != APPROVED_CONTRACT_SHA256:
        raise RegistryBuildError("UNIT01_APPROVAL_INVALID")
    keys = ("unit02_to_unit24_modified", "canonical_question_bank_written", "learner_facing_content_written", "audio_enabled", "speaking_capture_enabled", "a2_unlocked", "parallel_curriculum_created")
    if any((approval.get("boundaries") or {}).get(key) is not False for key in keys):
        raise RegistryBuildError("UNIT01_APPROVAL_BOUNDARY_INVALID")


def _vocabulary(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    vocab = contract["vocabulary_contract"]
    for pos, rows in (("noun", vocab["active_vocabulary"]), ("adjective", vocab["active_adjectives"])):
        for row in rows:
            lemma = row["lemma"]
            item = _base(f"U01-BIND-VOC-{pos.upper()}-{_slug(lemma)}", row["evp_sense_id"], "VOCABULARY_SENSE")
            forms = [row["memory_phrase"]] if pos == "adjective" else [row["memory_form_indefinite"], row["memory_form_definite"]]
            item.update(surface_form=lemma, part_of_speech=pos, cefr_level=row["cefr_level"], zh_tw_gloss=row["zh_tw_gloss"], semantic_group=row["semantic_group"], unit01_learning_role="ACTIVE_MEMORIZATION", memory_forms=forms, production_allowed=True, spelling_required=True, direct_assessment_allowed=True, skill_affordances=["READING", "WRITING", "SPEAKING"], source_authority="EVP_VOCABULARY_AUTHORITY")
            result.append(item)
    for row in vocab["receptive_vocabulary"]:
        lemma = row["lemma"]
        item = _base(f"U01-BIND-VOC-RECEPTIVE-{_slug(lemma)}", row["evp_sense_id"], "VOCABULARY_SENSE")
        item.update(unit01_role="CONTEXT_SUPPORT", surface_form=lemma, part_of_speech=row.get("part_of_speech"), cefr_level=row["cefr_level"], zh_tw_gloss=row["zh_tw_gloss"], unit01_learning_role=row["role"], memory_forms=[], production_allowed=False, spelling_required=False, direct_assessment_allowed=False, skill_affordances=["READING_CONTEXT", "WRITING_INPUT_ONLY", "SPEAKING_INPUT_ONLY"], source_authority="EVP_VOCABULARY_AUTHORITY", a2_bridge=row["cefr_level"] == "A2")
        result.append(item)
    return result


def _phrases(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: OrderedDict[str, dict[str, Any]] = OrderedDict()
    def add(surface: str, provenance: Mapping[str, Any]) -> None:
        normalized = _norm(surface)
        if normalized not in items:
            token = hashlib.sha256(normalized.encode()).hexdigest()[:12].upper()
            item = _base(f"U01-BIND-PHRASE-{token}", f"U01-PHRASE-{token}", "PROJECT_INSTRUCTIONAL_PHRASE")
            item.update(surface_form=surface, normalized_surface=normalized, canonical_chunk_claimed=False, production_allowed=True, direct_assessment_allowed=True, skill_affordances=["READING", "WRITING", "SPEAKING"], source_authority="UNIT01_APPROVED_CONTENT_CONTRACT", provenance=[])
            items[normalized] = item
        if dict(provenance) not in items[normalized]["provenance"]:
            items[normalized]["provenance"].append(dict(provenance))
    vocab = contract["vocabulary_contract"]
    for row in vocab["active_vocabulary"]:
        add(row["memory_form_indefinite"], {"source_type": "NOUN_MEMORY_INDEFINITE", "source_asset_id": row["evp_sense_id"], "lemma": row["lemma"]})
        add(row["memory_form_definite"], {"source_type": "NOUN_MEMORY_DEFINITE", "source_asset_id": row["evp_sense_id"], "lemma": row["lemma"]})
    for row in vocab["active_adjectives"]:
        add(row["memory_phrase"], {"source_type": "ADJECTIVE_MEMORY_PHRASE", "source_asset_id": row["evp_sense_id"], "lemma": row["lemma"]})
    chunks = contract["chunk_contract"]
    for row in chunks["instructional_phrases"]:
        add(row["surface_form"], {"source_type": "INSTRUCTIONAL_PHRASE", "authority_role": row["authority_role"]})
    for row in chunks["adjective_instructional_phrases"]:
        add(row["surface_form"], {"source_type": "ADJECTIVE_INSTRUCTIONAL_PHRASE", "adjective": row["adjective"], "noun": row["noun"], "article": row["article"], "egp_role": row["egp_role"], "authority_role": row["authority_role"]})
    return list(items.values())


def _chunks(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for row in contract["chunk_contract"]["canonical_chunks"]:
        direct = bool(row["direct_unit01_use_allowed"])
        item = _base(f"U01-BIND-CHUNK-{_slug(row['chunk_id'])}", row["chunk_id"], "CANONICAL_CHUNK")
        item.update(unit01_role="NEW_TARGET" if direct else "RECEPTIVE_CONTEXT_SUPPORT", surface_form=row["surface_form"], cefr_level=row["cefr_level"], usage_class=row["usage_class"], unit01_learning_role=row["unit01_role"], production_allowed=direct, direct_assessment_allowed=direct, skill_affordances=["READING", "WRITING", "SPEAKING"] if direct else ["READING_CONTEXT"], source_authority="EVP_CHUNK_AUTHORITY")
        result.append(item)
    return result


def _frames(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    sections = (("core_frames", "CORE_TARGET", True), ("adjective_expansion_frames", "ADJECTIVE_TARGET", True), ("scaffold_only_frames", "SCAFFOLD_ONLY", False))
    for section, role, assessed in sections:
        for row in contract["sentence_frame_contract"][section]:
            item = _base(f"U01-BIND-FRAME-{_slug(row['frame_id'])}", row["frame_id"], "SENTENCE_FRAME")
            item.update(unit01_role="NEW_TARGET" if assessed else "PREREQUISITE", template=row["template"], frame_role=role, production_allowed=True, direct_assessment_allowed=assessed, skill_affordances=["READING", "WRITING", "SPEAKING"], source_authority="UNIT01_APPROVED_CONTENT_CONTRACT", communicative_goal=row.get("communicative_goal"), support_level=row.get("support_level"), assessment_scope=row.get("assessment_scope"), external_grammar_ref=row.get("external_grammar_ref"), scaffold_grammar_refs=row.get("scaffold_grammar_refs", []))
            result.append(item)
    return result


def build_registry(contract: Mapping[str, Any], approval: Mapping[str, Any]) -> dict[str, Any]:
    _approve(contract, approval)
    vocabulary, chunks, phrases, frames = _vocabulary(contract), _chunks(contract), _phrases(contract), _frames(contract)
    active = [row for row in vocabulary if row["unit01_learning_role"] == "ACTIVE_MEMORIZATION"]
    core = {
        "schema_version": SCHEMA_VERSION, "program_id": PROGRAM_ID, "task_id": TASK_ID, "status": PASS_STATUS,
        "unit": {"unit_id": UNIT_ID, "unit_sequence": 1, "level_scope": list(contract["level_scope"]), "introduced_assets_are_reusable": True},
        "source_authority": {"contract_task_id": contract["task_id"], "approved_contract_sha256": APPROVED_CONTRACT_SHA256, "approval_task_id": approval["task_id"], "approval_status": approval["decision_status"], "authority_mode": "DERIVED_REFERENCE_BINDINGS_ONLY"},
        "cumulative_reuse_policy": {"later_units_may_reference_unit01_assets": True, "copy_records_into_later_units": False, "identity_mode": "REFERENCE_BY_STABLE_ASSET_ID", "introduced_unit_is_immutable": True, "future_unit_roles": list(FUTURE_ROLES), "selection_gates": list(SELECTION_GATES), "learner_payload_rule": "NEW_TARGETS_PLUS_SELECTED_PRIOR_ASSETS; NEVER_ASSIGN_THE_FULL_CUMULATIVE_POOL_AS_ONE_LESSON"},
        "grammar_references": {key: list(contract["grammar_contract"][key]) for key in ("core_focus_egp_row_ids", "guided_extension_egp_row_ids", "deferred_not_assessed_egp_row_ids")},
        "asset_bindings": {"vocabulary": vocabulary, "canonical_chunks": chunks, "instructional_phrases": phrases, "sentence_frames": frames},
        "denominators": {"active_vocabulary": len(active), "active_nouns": sum(row["part_of_speech"] == "noun" for row in active), "active_adjectives": sum(row["part_of_speech"] == "adjective" for row in active), "receptive_vocabulary": len(vocabulary) - len(active), "canonical_chunks": len(chunks), "instructional_phrases_distinct": len(phrases), "target_sentence_frames": sum(row["frame_role"] != "SCAFFOLD_ONLY" for row in frames), "scaffold_sentence_frames": sum(row["frame_role"] == "SCAFFOLD_ONLY" for row in frames), "total_language_asset_bindings": len(vocabulary) + len(chunks) + len(phrases) + len(frames)},
        "boundaries": {"unit02_to_unit24_modified": False, "canonical_question_bank_written": False, "learner_facing_content_written": False, "new_sentence_instances_generated": False, "audio_enabled": False, "speaking_capture_enabled": False, "a2_unlocked": False, "parallel_curriculum_created": False},
        "next_short_step": NEXT_SHORT_STEP,
    }
    core["registry_sha256"] = digest(core)
    return core


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryBuildError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(data, dict):
        raise RegistryBuildError(f"OBJECT_REQUIRED:{path}")
    return data


def run(contract_path: Path, approval_path: Path, output_path: Path) -> dict[str, Any]:
    report = build_registry(_load(contract_path), _load(approval_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--approval", type=Path, default=DEFAULT_APPROVAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = run(args.contract.resolve(), args.approval.resolve(), args.output.resolve())
    except (RegistryBuildError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA01_UNIT01_CUMULATIVE_REUSABLE_LANGUAGE_ASSET_REGISTRY")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    for key, value in report["denominators"].items():
        print(f"{key.upper()}={value}")
    print(f"REGISTRY_SHA256={report['registry_sha256']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
