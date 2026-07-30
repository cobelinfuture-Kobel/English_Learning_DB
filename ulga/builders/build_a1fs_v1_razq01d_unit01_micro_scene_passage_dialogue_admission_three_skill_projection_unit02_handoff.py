#!/usr/bin/env python3
"""Admit Unit01 RAZ-grounded scene assets and project them to the existing three-skill bank."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_razq01c_unit01_three_skill_candidate_selection_coverage_balancing as upstream
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as qb

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01D_Unit01MicroScenePassageDialogueAdmission_ThreeSkillProjectionAndUnit02ReusableHandoff"
SCHEMA_VERSION = "a1fs.v1.razq01d.unit01_content_admission_handoff.v1"
SAFE_SCHEMA_VERSION = "a1fs.v1.razq01d.unit01_content_admission_handoff_safe_readback.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_UNIT01_CONTENT_ADMISSION_HANDOFF"
UNIT_ID = upstream.UNIT_ID
UNIT_SEQUENCE = 1
TARGET_UNIT02_SEQUENCE = 2
APPROVED_CONTRACT_SHA256 = upstream.APPROVED_CONTRACT_SHA256
DECISION_REF = "OPERATOR_APPROVAL:2026-07-30:RAZQ01D"
INSPECTION_REF = "OPERATOR_HANDSHAKE:2026-07-30:UNIT01_SCENE_THREE_SKILL"
OUTPUT_CANDIDATE = Path("ulga/private/a1fs_v1_razq01d_unit01_admitted_content.candidate.private.json")
OUTPUT_APPROVED = Path("ulga/private/a1fs_v1_razq01d_unit01_admitted_content.approved.private.json")
OUTPUT_SAFE = Path("ulga/reports/a1fs_v1_razq01d_unit01_admission_handoff_readback.json")
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01D_LocalPrivateAdmissionMaterializationAndCoverageRecheck"
CONTENT_KINDS = ("MICRO_SCENE", "SHORT_PASSAGE", "SHORT_DIALOGUE")
SKILLS = ("READING", "WRITING", "SPEAKING")
REVIEW_DIMENSIONS = (
    "GRAMMAR_SAFETY",
    "VOCABULARY_SAFETY",
    "SEMANTIC_NATURALNESS",
    "A1_ANSWERABILITY",
    "SCENE_DISTINCTNESS",
    "THREE_SKILL_AFFORDANCE",
)
FUTURE_ROLES = (
    "PREREQUISITE",
    "CARRY_OVER",
    "RECOMBINATION",
    "TRANSFER",
    "SCHEDULED_REVIEW",
    "REMEDIATION",
    "ASSESSMENT_SUPPORT",
)
REUSE_GATES = (
    "PREREQUISITE_UNLOCKED",
    "LEVEL_SCOPE_ALLOWED",
    "NEW_GRAMMAR_COMPATIBILITY_PASS",
    "NO_UNINTRODUCED_GRAMMAR",
    "SEMANTIC_COMPATIBILITY_PASS",
    "SCENE_DEDUPLICATION_PASS",
    "REUSE_REASON_RECORDED",
)
FAMILY_IDS = frozenset(str(row[0]) for row in qb.FAMILIES)
FAMILY_MAP = {
    "READING": (
        "U01-PF04-FIRST-MENTION-CONTEXT",
        "U01-PF05-KNOWN-REFERENCE-CONTEXT",
        "U01-PF08-TRANSFER-FIRST-MENTION",
    ),
    "WRITING": (
        "U01-PF07-WORD-ORDER",
        "U01-PF09-TRANSFER-KNOWN-REFERENCE",
    ),
    "SPEAKING": ("U01-PF10-SPEAK-NOUN",),
}
FINDINGS = (
    ("FIXED_CONTEXT_COUNT_TOO_LOW", "U01QB01 contains exactly five hard-coded context labels."),
    ("RAZQ01C_NOT_CONSUMED_BY_U01QB01", "U01QB01 does not import or consume RAZQ01C."),
    ("U01E_SHORT_TEXT_THREE_SKILL_PRESENT", "Existing U01E short texts feed Reading, Writing and Speaking."),
    ("U01QB01_FULL_TEXT_THREE_SKILL_NOT_PRESENT", "The 288-item pool uses labels rather than shared passage assets."),
    ("FUNCTIONAL_DIALOGUE_LABEL_WITHOUT_TURN_STRUCTURE", "The existing toy-shop context has no speaker turns."),
)
WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)


class AdmissionBuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def norm(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(norm(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(norm(item) for item in value)
    return " ".join(WORD_RE.findall(str(value).casefold().replace("’", "'")))


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdmissionBuildError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AdmissionBuildError(f"OBJECT_REQUIRED:{path}")
    return value


def write(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def validate_upstream(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    scope = report.get("scope") or {}
    if report.get("task_id") != upstream.TASK_ID or report.get("status") != upstream.PASS_STATUS:
        raise AdmissionBuildError("RAZQ01C_IDENTITY_INVALID")
    if (
        scope.get("allowed_units") != [UNIT_ID]
        or scope.get("canonical_promotion") is not False
        or scope.get("a2_status") != "LOCKED"
    ):
        raise AdmissionBuildError("RAZQ01C_SCOPE_INVALID")
    rows = report.get("selected_candidates")
    if not isinstance(rows, list) or not rows:
        raise AdmissionBuildError("RAZQ01C_SELECTED_CANDIDATES_REQUIRED")
    identities = [str(row.get("source_record_id") or "") for row in rows]
    if "" in identities or len(identities) != len(set(identities)):
        raise AdmissionBuildError("RAZQ01C_SOURCE_ID_INVALID")
    return deepcopy(rows)


def validate_decision(decision: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    if (
        decision.get("source_record_id") != candidate.get("source_record_id")
        or decision.get("semantic_identity") != candidate.get("semantic_identity")
    ):
        raise AdmissionBuildError("DECISION_IDENTITY_MISMATCH")
    if decision.get("decision_ref") != DECISION_REF or decision.get("review_status") not in {
        "APPROVED",
        "REJECTED",
    }:
        raise AdmissionBuildError("DECISION_STATUS_OR_REF_INVALID")
    checks = decision.get("review_dimensions") or {}
    if set(checks) != set(REVIEW_DIMENSIONS):
        raise AdmissionBuildError("REVIEW_DIMENSIONS_INCOMPLETE")
    if decision["review_status"] == "APPROVED":
        if candidate.get("selection_class") == "REJECT" or decision.get("content_kind") not in CONTENT_KINDS:
            raise AdmissionBuildError("APPROVAL_KIND_INVALID")
        if any(checks[key] != "PASS" for key in REVIEW_DIMENSIONS) or decision.get("template_only") is not False:
            raise AdmissionBuildError("APPROVAL_GATES_NOT_PASS")
    elif not decision.get("rejection_reason_codes"):
        raise AdmissionBuildError("REJECTION_REASON_REQUIRED")


def content_parts(decision: Mapping[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    kind = str(decision["content_kind"])
    sentences = [
        str(value).strip()
        for value in decision.get("adapted_sentences") or []
        if str(value).strip()
    ]
    turns = [
        {
            "speaker_id": str(value.get("speaker_id") or ""),
            "utterance": str(value.get("utterance") or "").strip(),
        }
        for value in decision.get("dialogue_turns") or []
        if isinstance(value, Mapping)
    ]
    if kind == "MICRO_SCENE" and not (1 <= len(sentences) <= 3 and not turns):
        raise AdmissionBuildError("MICRO_SCENE_STRUCTURE_INVALID")
    if kind == "SHORT_PASSAGE" and not (2 <= len(sentences) <= 6 and not turns):
        raise AdmissionBuildError("SHORT_PASSAGE_STRUCTURE_INVALID")
    if kind == "SHORT_DIALOGUE":
        speakers = {turn["speaker_id"] for turn in turns if turn["speaker_id"]}
        if (
            sentences
            or not 2 <= len(turns) <= 6
            or len(speakers) < 2
            or any(not turn["speaker_id"] or not turn["utterance"] for turn in turns)
        ):
            raise AdmissionBuildError("SHORT_DIALOGUE_STRUCTURE_INVALID")
    return sentences, turns


def asset_id(kind: str, semantic_identity: str) -> str:
    prefix = {"MICRO_SCENE": "MS", "SHORT_PASSAGE": "SP", "SHORT_DIALOGUE": "DLG"}[kind]
    token = hashlib.sha256(f"{kind}|{semantic_identity}".encode("utf-8")).hexdigest()[:12].upper()
    return f"U01-{prefix}-{token}"


def patterns(candidate: Mapping[str, Any]) -> list[str]:
    result = {qb.PATTERN_NOUN}
    if candidate.get("active_adjective_hits") or candidate.get("adjective_noun_phrases"):
        result.add(qb.PATTERN_ADJECTIVE)
    if candidate.get("very_adjective_noun_phrases"):
        result.add(qb.PATTERN_VERY)
    return sorted(result)


def build_asset(
    candidate: Mapping[str, Any],
    decision: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    sentences, turns = content_parts(decision)
    raw_excerpt = str(candidate.get("text_excerpt") or "")
    adapted_payload = {"sentences": sentences, "dialogue_turns": turns}
    if not norm(adapted_payload) or norm(adapted_payload) == norm(raw_excerpt):
        raise AdmissionBuildError("RAW_RAZ_TEXT_COPY_OR_EMPTY_ADAPTATION")

    scene = deepcopy(decision.get("scene_profile") or {})
    required_scene_fields = {
        "setting",
        "participants",
        "objects",
        "actions",
        "information_structure",
        "communicative_function_ids",
    }
    if set(scene) != required_scene_fields:
        raise AdmissionBuildError("SCENE_PROFILE_FIELDS_INVALID")
    scene["distinct_scene_signature"] = digest(scene)

    kind = str(decision["content_kind"])
    content_asset_id = asset_id(kind, str(candidate["semantic_identity"]))
    pattern_ids = patterns(candidate)
    vocabulary_rows = list(contract["vocabulary_contract"]["active_vocabulary"]) + list(
        contract["vocabulary_contract"]["active_adjectives"]
    )
    wanted_lemmas = set(candidate.get("active_noun_hits") or []) | set(
        candidate.get("active_adjective_hits") or []
    )
    vocabulary_ids = sorted(
        str(row["evp_sense_id"])
        for row in vocabulary_rows
        if row["lemma"] in wanted_lemmas
    )

    projections: list[dict[str, Any]] = []
    for skill in SKILLS:
        family_ids = list(FAMILY_MAP[skill])
        if skill == "SPEAKING" and qb.PATTERN_ADJECTIVE in pattern_ids:
            family_ids.append("U01-PF11-SPEAK-ADJ-NOUN")
        if skill == "SPEAKING" and qb.PATTERN_VERY in pattern_ids:
            family_ids.append("U01-PF12-SPEAK-VERY-ADJ-NOUN")
        if not set(family_ids).issubset(FAMILY_IDS):
            raise AdmissionBuildError("QUESTION_BANK_FAMILY_MISSING")
        if skill == "READING":
            task_modes = ["SHORT_TEXT_DETAIL", "ARTICLE_REFERENCE"]
        elif skill == "WRITING":
            task_modes = ["GUIDED_SENTENCE", "CONTEXTUAL_WRITING"]
        elif kind == "SHORT_DIALOGUE":
            task_modes = ["ROLE_PLAY", "ORAL_RETELL"]
        else:
            task_modes = ["ORAL_RETELL"]
        projections.append(
            {
                "projection_id": f"{content_asset_id}-{skill}",
                "content_asset_id": content_asset_id,
                "skill": skill,
                "existing_question_bank_id": qb.BANK_ID,
                "existing_question_bank_version": qb.BANK_VERSION,
                "existing_family_ids": sorted(family_ids),
                "projection_mode": "REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK",
                "projection_status": "READY_FOR_EXISTING_QB_MATERIALIZATION",
                "task_modes": task_modes,
            }
        )

    speakers = sorted({turn["speaker_id"] for turn in turns})
    return {
        "content_asset_id": content_asset_id,
        "content_kind": kind,
        "title": str(decision.get("title") or content_asset_id),
        "introduced_unit_id": UNIT_ID,
        "introduced_unit_sequence": UNIT_SEQUENCE,
        "source_lineage": {
            "source_authority": "RAZ_READING_AUTHORITY",
            "source_record_id": str(candidate["source_record_id"]),
            "semantic_identity": str(candidate["semantic_identity"]),
            "source_level": candidate.get("source_level"),
            "source_type": candidate.get("source_type"),
            "original_excerpt_sha256": hashlib.sha256(raw_excerpt.encode("utf-8")).hexdigest(),
            "original_excerpt_private": True,
            "adaptation_mode": str(decision.get("adaptation_mode") or ""),
            "adaptation_reason_codes": sorted(
                str(value) for value in decision.get("adaptation_reason_codes") or []
            ),
            "derived_from_task_id": upstream.TASK_ID,
        },
        "content": adapted_payload,
        "content_sha256": digest(adapted_payload),
        "target_alignment": {
            "grammar_target_ids": pattern_ids,
            "egp_row_ids": sorted(
                list(contract["grammar_contract"]["core_focus_egp_row_ids"])
                + list(contract["grammar_contract"]["guided_extension_egp_row_ids"])
            ),
            "vocabulary_asset_ids": vocabulary_ids,
            "chunk_asset_ids": [],
            "sentence_frame_ids": sorted(
                str(value) for value in candidate.get("matched_sentence_frame_ids") or []
            ),
            "theme_id": decision.get("theme_id"),
            "situation_family_id": decision.get("situation_family_id"),
            "micro_situation_id": decision.get("micro_situation_id"),
            "communicative_function_ids": sorted(
                str(value) for value in scene["communicative_function_ids"]
            ),
        },
        "scene_profile": scene,
        "dialogue_profile": {
            "is_real_dialogue": kind == "SHORT_DIALOGUE",
            "speaker_count": len(speakers),
            "turn_count": len(turns),
            "speaker_ids": speakers,
            "adjacency_pair_types": sorted(
                str(value) for value in decision.get("adjacency_pair_types") or []
            ),
            "role_play_supported": kind == "SHORT_DIALOGUE",
        },
        "skill_projections": projections,
        "admission": {
            "review_status": "APPROVED",
            "decision_ref": DECISION_REF,
            "review_dimensions": deepcopy(decision["review_dimensions"]),
            "selection_class": candidate["selection_class"],
            "selection_reasons": deepcopy(candidate.get("selection_reasons") or []),
            "canonical_admission": True,
            "template_only": False,
        },
        "later_unit_reuse": {
            "reusable_in_later_units": True,
            "reuse_identity_mode": "REFERENCE_EXISTING_CONTENT_ASSET_ID",
            "copy_on_reuse": False,
            "eligible_future_unit_roles": list(FUTURE_ROLES),
            "reuse_gates": list(REUSE_GATES),
        },
        "unit02_reusable_handoff": {
            "target_unit_sequence": TARGET_UNIT02_SEQUENCE,
            "source_content_asset_id": content_asset_id,
            "candidate_role": "CARRY_OVER",
            "binding_status": "AVAILABLE_NOT_BOUND",
            "unit02_modified": False,
            "required_when_bound": [
                "target_unit_id",
                "target_unit_role",
                "new_grammar_target_ids",
                "reuse_reason",
                "compatibility_gate_status",
            ],
        },
    }


def safe_asset(asset: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(asset))
    value.pop("content", None)
    return value


def build_payload(
    selection_report: Mapping[str, Any],
    decisions: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(dict(contract or contract_builder.build_contract()))
    contract_builder.verify_contract_digest(contract)
    if contract.get("contract_sha256") != APPROVED_CONTRACT_SHA256:
        raise AdmissionBuildError("UNIT01_CONTRACT_DIGEST_INVALID")

    candidates = validate_upstream(selection_report)
    reviewable = [row for row in candidates if row.get("selection_class") != "REJECT"]
    decision_rows = decisions.get("decisions")
    if not isinstance(decision_rows, list):
        raise AdmissionBuildError("DECISIONS_ARRAY_REQUIRED")
    by_source_id = {
        str(row.get("source_record_id") or ""): row
        for row in decision_rows
        if isinstance(row, Mapping)
    }
    expected_ids = {str(row["source_record_id"]) for row in reviewable}
    if (
        "" in by_source_id
        or len(by_source_id) != len(decision_rows)
        or set(by_source_id) != expected_ids
    ):
        raise AdmissionBuildError("COMPLETE_REVIEWABLE_CANDIDATE_DECISIONS_REQUIRED")

    assets: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    for candidate in reviewable:
        decision = by_source_id[str(candidate["source_record_id"])]
        validate_decision(decision, candidate)
        ledger.append(
            {
                "source_record_id": candidate["source_record_id"],
                "semantic_identity": candidate["semantic_identity"],
                "review_status": decision["review_status"],
                "decision_ref": decision["decision_ref"],
                "content_kind": decision.get("content_kind"),
                "rejection_reason_codes": sorted(
                    str(value) for value in decision.get("rejection_reason_codes") or []
                ),
            }
        )
        if decision["review_status"] == "APPROVED":
            assets.append(build_asset(candidate, decision, contract))

    kind_counts = Counter(asset["content_kind"] for asset in assets)
    if not assets or any(kind_counts[kind] < 1 for kind in CONTENT_KINDS):
        raise AdmissionBuildError("ALL_CONTENT_KINDS_REQUIRED_FOR_ACCEPTANCE")
    signatures = [asset["scene_profile"]["distinct_scene_signature"] for asset in assets]
    if len(signatures) != len(set(signatures)):
        raise AdmissionBuildError("SCENE_SIGNATURE_DUPLICATE")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "scope": {
            "allowed_units": [UNIT_ID],
            "unit02_to_unit24_modified": False,
            "a2_status": "LOCKED",
            "listening_status": "DEFERRED",
            "second_question_bank_created": False,
            "raw_raz_text_learner_facing_copy_allowed": False,
        },
        "inputs": {
            "upstream_task_id": upstream.TASK_ID,
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "existing_question_bank_id": qb.BANK_ID,
            "existing_question_bank_version": qb.BANK_VERSION,
            "decision_ref": DECISION_REF,
        },
        "inspection_record": {
            "inspection_ref": INSPECTION_REF,
            "findings": [
                {
                    "finding_code": code,
                    "observed_status": "CONFIRMED",
                    "evidence": evidence,
                }
                for code, evidence in FINDINGS
            ],
            "resolution": "ADMIT_RAZ_GROUNDED_CONTENT_AND_REFERENCE_EXISTING_THREE_SKILL_QB",
            "unit02_reuse_fields_recorded": True,
        },
        "review_ledger": ledger,
        "content_assets": assets,
        "coverage_readback": {
            "reviewable_candidate_count": len(reviewable),
            "approved_content_asset_count": len(assets),
            "rejected_candidate_count": sum(
                row["review_status"] == "REJECTED" for row in ledger
            ),
            "distinct_micro_scene_count": kind_counts["MICRO_SCENE"],
            "distinct_short_passage_count": kind_counts["SHORT_PASSAGE"],
            "distinct_dialogue_count": kind_counts["SHORT_DIALOGUE"],
            "raz_grounded_content_count": len(assets),
            "project_authored_rewrite_count": sum(
                asset["source_lineage"]["adaptation_mode"] == "PROJECT_AUTHORED_REWRITE"
                for asset in assets
            ),
            "reading_projection_count": len(assets),
            "writing_projection_count": len(assets),
            "speaking_projection_count": len(assets),
            "three_skill_shared_content_count": len(assets),
            "template_only_content_count": 0,
            "unit02_reusable_asset_count": len(assets),
        },
        "boundaries": {
            "existing_question_bank_referenced": True,
            "existing_question_bank_modified": False,
            "parallel_question_bank_created": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "mastery_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate(
    selection_report: Mapping[str, Any],
    decisions: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_payload(selection_report, decisions, contract)
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "upstream_task_id": upstream.TASK_ID,
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "existing_question_bank_id": qb.BANK_ID,
            "existing_question_bank_version": qb.BANK_VERSION,
            "operator_decision_ref": DECISION_REF,
            "operator_inspection_ref": INSPECTION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as validator,
    )

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def build_safe_readback(approved: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(approved)
    payload = approved.get("payload") or {}
    assets = payload.get("content_assets") or []
    safe = {
        "schema_version": SAFE_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "content_governance": deepcopy(approved["content_governance"]),
        "admission": deepcopy(approved["admission"]),
        "source_bindings": deepcopy(approved["source_bindings"]),
        "inspection_record": deepcopy(payload.get("inspection_record") or {}),
        "coverage_readback": deepcopy(payload.get("coverage_readback") or {}),
        "content_assets": [safe_asset(asset) for asset in assets],
        "boundaries": deepcopy(payload.get("boundaries") or {}),
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe["readback_sha256"] = digest(safe)
    return safe


def build_admission(
    selection_report: Mapping[str, Any],
    decisions: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate(selection_report, decisions, contract)
    approved = admit_candidate(candidate)
    safe = build_safe_readback(approved)
    return candidate, approved, safe


def run(
    selection_report_path: Path,
    decisions_path: Path,
    candidate_output_path: Path = OUTPUT_CANDIDATE,
    approved_output_path: Path = OUTPUT_APPROVED,
    safe_output_path: Path = OUTPUT_SAFE,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate, approved, safe = build_admission(
        load(selection_report_path),
        load(decisions_path),
    )
    write(candidate_output_path, candidate, private=True)
    write(approved_output_path, approved, private=True)
    write(safe_output_path, safe)
    return candidate, approved, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-report", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--candidate-output", type=Path, default=OUTPUT_CANDIDATE)
    parser.add_argument("--approved-output", type=Path, default=OUTPUT_APPROVED)
    parser.add_argument("--safe-output", type=Path, default=OUTPUT_SAFE)
    args = parser.parse_args(argv)
    try:
        _, approved, safe = run(
            args.selection_report.resolve(),
            args.decisions.resolve(),
            args.candidate_output.resolve(),
            args.approved_output.resolve(),
            args.safe_output.resolve(),
        )
    except (
        AdmissionBuildError,
        policy_artifact.ContentPolicyBuildError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_RAZQ01D")
        print(f"ERROR={exc}")
        return 1
    coverage = safe["coverage_readback"]
    print(f"STATUS={approved['payload']['status']}")
    print(f"APPROVED_CONTENT_ASSETS={coverage['approved_content_asset_count']}")
    print(f"THREE_SKILL_SHARED={coverage['three_skill_shared_content_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
