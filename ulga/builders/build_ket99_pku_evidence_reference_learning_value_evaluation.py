#!/usr/bin/env python3
"""Evaluate KET99 PKU and lesson bindings against current A1/A1+ materials."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "KET99-PK-M4B_EvidenceReferenceLearningValueEvaluation"
SCHEMA_VERSION = "ket99.pku.evidence_reference_learning_value_evaluation.v1"
PASS_STATUS = "PASS_KET99_PK_M4B_EVIDENCE_REFERENCE_LEARNING_VALUE_EVALUATION_READY"
NEXT_SHORT_STEP = "KET99-PK-M4C_SelectedTeacherDeliveryAndRemediationAssetAuthoring"
M4A_TASK = "KET99-PK-M4A_TeacherDeliveryAndRemediationAssetMainlineIntake"
M4A_SCHEMA = "ket99.pku.teacher_delivery_remediation_asset_intake.v1"
M4A_STATUS = "PASS_KET99_PK_M4A_TEACHER_DELIVERY_REMEDIATION_ASSET_MAINLINE_INTAKE_READY"
M2_TASK = "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery"
M2_SCHEMA = "a1fs.v1.m2.four_skill_asset_body_consumer.v1"
M2_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
BRIDGE_TASK = "KET99-PK-M2_OperatorConfirmationAndTeachingNeedIdentityBridge"
BRIDGE_STATUS = "PASS_KET99_PK_M2_OPERATOR_CONFIRMATION_AND_TEACHING_NEED_IDENTITY_BRIDGE_READY"

DEFAULT_INTAKE = ROOT / ".local/a1fs_v1/ket99_pku_m4a/teacher_delivery_remediation_asset_intake.safe.json"
DEFAULT_M2 = ROOT / ".local/a1fs_v1/runtime/m2/four_skill_asset_body_consumer.private.json"
DEFAULT_BRIDGE = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_operator_confirmation_teaching_need_bridge.v1.json"
DEFAULT_OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4b/evidence_reference_learning_value_evaluation.safe.json"

GENERIC_TOKENS = {
    "grammar", "teaching", "need", "reading", "listening", "speaking", "writing",
    "learner", "language", "skill", "function", "vocab", "teacher", "method",
    "support", "with", "and", "then", "before", "after", "simple", "basic",
    "statement", "form", "pattern", "practice", "focus", "remediation",
}
TEACHER_MARKERS = {
    "teacher_delivery", "teacher_guide", "teacher_instruction", "launch", "model",
    "guided", "elicitation", "wait", "feedback", "scaffold", "notice", "explain",
    "instruction", "support", "context", "transfer",
}
REMEDIATION_MARKERS = {
    "remediation", "diagnostic", "error_route", "error", "repair", "misconception",
    "critical_failure", "correction", "retry", "reassessment", "contrast",
}
EVIDENCE_MARKERS = {
    "evidence", "acceptance", "rubric", "check", "score", "criterion", "outcome",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _verify_signed(value: Mapping[str, Any], code: str) -> None:
    unsigned = dict(value)
    stored = unsigned.pop("artifact_sha256", None)
    if stored != digest(unsigned):
        raise ValueError(f"{code}_artifact_sha256_invalid")


def _decode_rows(bundle: Mapping[str, Any], fields_key: str, rows_key: str) -> list[dict[str, Any]]:
    fields = bundle.get(fields_key)
    rows = bundle.get(rows_key)
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise ValueError(f"bridge_row_bundle_missing:{rows_key}")
    decoded = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(fields):
            raise ValueError(f"bridge_row_bundle_invalid:{rows_key}")
        decoded.append(dict(zip(fields, row)))
    return decoded


def verify_inputs(intake: Mapping[str, Any], consumer: Mapping[str, Any], bridge: Mapping[str, Any]) -> None:
    if (
        intake.get("task_id") != M4A_TASK
        or intake.get("schema_version") != M4A_SCHEMA
        or intake.get("validation_status") != M4A_STATUS
        or intake.get("errors") != []
        or intake.get("stop_reason") != "NONE"
    ):
        raise ValueError("m4a_intake_contract_invalid")
    _verify_signed(intake, "m4a_intake")
    if intake.get("claim_boundaries", {}).get("learning_value_evaluated") is not False:
        raise ValueError("m4a_prior_evaluation_claim_invalid")
    if (
        consumer.get("task_id") != M2_TASK
        or consumer.get("schema_version") != M2_SCHEMA
        or consumer.get("validation_status") != M2_STATUS
        or consumer.get("errors") != []
    ):
        raise ValueError("m2_consumer_contract_invalid")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise ValueError("m2_a2_lock_invalid")
    if (
        bridge.get("task_id") != BRIDGE_TASK
        or bridge.get("validation_status") != BRIDGE_STATUS
        or bridge.get("errors") != []
        or bridge.get("stop_reason") != "NONE"
    ):
        raise ValueError("pku_bridge_contract_invalid")
    candidates = intake.get("asset_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("m4a_asset_candidates_required")
    if intake.get("counts", {}).get("asset_candidate_count") != len(candidates):
        raise ValueError("m4a_candidate_count_mismatch")
    m2_sha = digest(consumer)
    for row in candidates:
        if not isinstance(row, Mapping):
            raise ValueError("m4a_candidate_row_invalid")
        if row.get("source_lineage", {}).get("m2_artifact_sha256") != m2_sha:
            raise ValueError("m4a_m2_binding_invalid")
        if row.get("learning_value_evaluation_status") != "NOT_EVALUATED":
            raise ValueError("m4a_candidate_already_evaluated")
        if any(row.get(key) is not False for key in (
            "composition_item", "required_for_delivery", "learner_facing_allowed",
            "mastery_evidence_allowed", "production_activation_allowed",
        )):
            raise ValueError("m4a_candidate_boundary_invalid")


def _flatten(value: Any, *, texts: list[str], keys: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            token = str(key).casefold()
            keys.add(token)
            _flatten(child, texts=texts, keys=keys)
    elif isinstance(value, list):
        for child in value:
            _flatten(child, texts=texts, keys=keys)
    elif isinstance(value, (str, int, float, bool)):
        texts.append(str(value).casefold())


def _marker_count(keys: set[str], markers: set[str]) -> int:
    return sum(any(marker in key for marker in markers) for key in keys)


def _concept_tokens(concept_id: str) -> list[str]:
    return sorted({
        token.casefold()
        for token in re.split(r"[^A-Za-z0-9]+", concept_id)
        if len(token) >= 3 and token.casefold() not in GENERIC_TOKENS
    })


def _material_profiles(consumer: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    assets_by_lesson: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in consumer.get("asset_records", []):
        if isinstance(row, Mapping) and row.get("level") in {"A1", "A1+"}:
            assets_by_lesson[str(row.get("lesson_id") or "")].append(row)
    catalog = {
        str(row.get("lesson_id") or ""): row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and row.get("level") in {"A1", "A1+"}
    }
    profiles: dict[str, dict[str, Any]] = {}
    for lesson_id, lesson in catalog.items():
        texts: list[str] = []
        keys: set[str] = set()
        assets = assets_by_lesson.get(lesson_id, [])
        for asset in assets:
            _flatten(asset.get("payload", {}), texts=texts, keys=keys)
        roles = sorted({str(row.get("role") or "") for row in assets if str(row.get("role") or "")})
        profiles[lesson_id] = {
            "lesson_id": lesson_id,
            "skill": str(lesson.get("skill") or ""),
            "level": str(lesson.get("level") or ""),
            "asset_count": len(assets),
            "roles": roles,
            "requirement_node_ids": sorted(str(v) for v in lesson.get("requirement_node_ids", []) if str(v)),
            "teacher_surface_count": _marker_count(keys, TEACHER_MARKERS) + sum(role in {"MOD", "NTC", "GDT", "CTX"} for role in roles),
            "remediation_surface_count": _marker_count(keys, REMEDIATION_MARKERS) + sum(role in {"CHK", "ERR"} for role in roles),
            "evidence_surface_count": _marker_count(keys, EVIDENCE_MARKERS) + sum(role in {"CHK", "EVD"} for role in roles),
            "material_search_text": "\n".join(texts + sorted(keys)),
            "material_digest": digest({
                "asset_digests": sorted(str(row.get("content_digest") or "") for row in assets),
                "roles": roles,
            }),
        }
    return profiles


def _registry(bridge: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _decode_rows(bridge, "teaching_need_field_order", "teaching_need_registry"):
        pku_id = str(row.get("source_pku_id") or "")
        if pku_id:
            result[pku_id] = row
    return result


def _metadata(candidate: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    pku_id = str(candidate.get("pku_id") or "")
    row = registry.get(pku_id, {})
    authority_ids = sorted(str(v) for v in candidate.get("authority_ids", []) if str(v))
    teaching_need_id = str(candidate.get("teaching_need_id") or "")
    concept_id = str(row.get("pedagogical_concept_id") or "")
    if not concept_id:
        concept_id = teaching_need_id.split(":", 1)[-1] if teaching_need_id else (authority_ids[0] if authority_ids else pku_id)
    knowledge_mode = str(row.get("knowledge_mode") or ("LEARNER_LANGUAGE" if authority_ids else "UNCLASSIFIED"))
    knowledge_type = str(row.get("knowledge_type") or ("GRAMMAR_FORM" if authority_ids else "UNCLASSIFIED"))
    roles = row.get("teaching_roles") or (["FOCUS", "PRACTICE", "REMEDIATION"] if authority_ids else [])
    if not isinstance(roles, list):
        raise ValueError(f"teaching_roles_invalid:{pku_id}")
    return {
        "pku_id": pku_id,
        "concept_id": concept_id,
        "knowledge_mode": knowledge_mode,
        "knowledge_type": knowledge_type,
        "teaching_roles": sorted(str(v) for v in roles if str(v)),
        "authority_ids": authority_ids,
        "teaching_need_id": teaching_need_id or None,
    }


def _binding_score(meta: Mapping[str, Any], candidate: Mapping[str, Any], profile: Mapping[str, Any]) -> tuple[int, list[str], dict[str, Any]]:
    mode = str(meta["knowledge_mode"])
    kind = str(meta["knowledge_type"])
    roles = set(meta["teaching_roles"])
    score = 0
    reasons: list[str] = []
    if mode == "ERROR_REPAIR":
        score += 6; reasons.append("SPECIFIC_ERROR_REPAIR")
    elif mode == "PRONUNCIATION_SUPPORT":
        score += 5; reasons.append("PRONUNCIATION_SUPPORT")
    elif mode == "LEARNER_SKILL":
        score += 4; reasons.append("SKILL_STRATEGY_SUPPORT")
    elif mode == "TEACHER_METHOD":
        score += 3; reasons.append("ALTERNATIVE_TEACHING_METHOD")
    elif mode == "LEARNER_LANGUAGE":
        score += 2; reasons.append("LANGUAGE_EXPLANATION_SUPPORT")
    if kind in {"READING_STRATEGY", "LISTENING_SKILL", "SPEAKING_SKILL", "WRITING_SKILL", "ERROR_PATTERN"}:
        score += 2; reasons.append("NON_GRAMMAR_SKILL_VALUE")
    exact_nodes = {f"REF:{candidate.get('skill')}:{authority_id}" for authority_id in meta["authority_ids"]}
    exact_existing = bool(exact_nodes & set(profile["requirement_node_ids"]))
    if exact_existing:
        score -= 2; reasons.append("CANONICAL_TARGET_ALREADY_EXPLICIT")
    tokens = _concept_tokens(str(meta["concept_id"]))
    search = str(profile["material_search_text"])
    hits = sorted(token for token in tokens if token in search)
    if len(hits) >= 2:
        score -= 2; reasons.append("CURRENT_MATERIAL_CONCEPT_SIGNAL_PRESENT")
    elif hits:
        score -= 1; reasons.append("CURRENT_MATERIAL_PARTIAL_CONCEPT_SIGNAL")
    teacher_relevant = mode in {"TEACHER_METHOD", "PRONUNCIATION_SUPPORT", "LEARNER_SKILL", "ERROR_REPAIR"} or bool(roles & {"INTRO", "SUPPORT", "FOCUS", "PRACTICE", "TRANSFER"})
    remediation_relevant = mode == "ERROR_REPAIR" or kind == "ERROR_PATTERN" or bool(roles & {"REMEDIATION", "ERROR_REPAIR"})
    if teacher_relevant:
        if int(profile["teacher_surface_count"]) == 0:
            score += 2; reasons.append("CURRENT_TEACHER_DELIVERY_SURFACE_THIN")
        else:
            score -= 1; reasons.append("CURRENT_TEACHER_DELIVERY_ALREADY_STRUCTURED")
    if remediation_relevant:
        if int(profile["remediation_surface_count"]) == 0:
            score += 3; reasons.append("CURRENT_REMEDIATION_SURFACE_MISSING")
        else:
            score += 1; reasons.append("SPECIFIC_REMEDIATION_MAY_COMPLEMENT_EXISTING_ROUTE")
    media_required = mode == "PRONUNCIATION_SUPPORT" or (kind == "LISTENING_SKILL" and candidate.get("skill") == "LISTENING")
    if media_required:
        reasons.append("MEDIA_OR_AUDIO_EVIDENCE_REQUIRED")
    return score, sorted(set(reasons)), {
        "exact_authority_already_explicit": exact_existing,
        "concept_token_count": len(tokens),
        "current_material_concept_token_hit_count": len(hits),
        "current_teacher_surface_count": int(profile["teacher_surface_count"]),
        "current_remediation_surface_count": int(profile["remediation_surface_count"]),
        "current_evidence_surface_count": int(profile["evidence_surface_count"]),
        "media_evidence_required": media_required,
    }


def _retention_cap(meta: Mapping[str, Any]) -> int:
    mode = str(meta["knowledge_mode"])
    if mode in {"ERROR_REPAIR", "PRONUNCIATION_SUPPORT", "TEACHER_METHOD"}:
        return 2
    if mode == "LEARNER_SKILL":
        return 3
    if meta["authority_ids"]:
        return 1
    return 2


def build_artifact(intake: Mapping[str, Any], consumer: Mapping[str, Any], bridge: Mapping[str, Any]) -> dict[str, Any]:
    verify_inputs(intake, consumer, bridge)
    profiles = _material_profiles(consumer)
    registry = _registry(bridge)
    provisional: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in intake["asset_candidates"]:
        lesson_id = str(candidate.get("lesson_id") or "")
        profile = profiles.get(lesson_id)
        if profile is None:
            raise ValueError(f"m2_lesson_material_missing:{lesson_id}")
        if profile["skill"] != candidate.get("skill") or profile["level"] != candidate.get("level"):
            raise ValueError(f"m2_lesson_partition_drift:{lesson_id}")
        meta = _metadata(candidate, registry)
        score, reasons, signals = _binding_score(meta, candidate, profile)
        provisional[meta["pku_id"]].append({
            "asset_candidate_id": candidate["asset_candidate_id"],
            "pku_id": meta["pku_id"],
            "concept_id": meta["concept_id"],
            "knowledge_mode": meta["knowledge_mode"],
            "knowledge_type": meta["knowledge_type"],
            "teaching_roles": meta["teaching_roles"],
            "lesson_id": lesson_id,
            "skill": candidate["skill"],
            "level": candidate["level"],
            "mapping_class": candidate.get("mapping_class"),
            "authority_ids": meta["authority_ids"],
            "teaching_need_id": meta["teaching_need_id"],
            "material_profile": {
                "asset_count": profile["asset_count"],
                "roles": profile["roles"],
                "material_digest": profile["material_digest"],
                **signals,
            },
            "raw_incremental_value_score": score,
            "evaluation_reasons": reasons,
            "source_lineage": candidate.get("source_lineage", {}),
        })
    bindings: list[dict[str, Any]] = []
    pku_rows: list[dict[str, Any]] = []
    for pku_id, rows in sorted(provisional.items()):
        rows = sorted(rows, key=lambda row: (-int(row["raw_incremental_value_score"]), row["lesson_id"], row["asset_candidate_id"]))
        cap = _retention_cap(rows[0])
        retained = 0
        decision_counts: Counter[str] = Counter()
        for rank, row in enumerate(rows, 1):
            score = int(row["raw_incremental_value_score"])
            media = bool(row["material_profile"]["media_evidence_required"])
            if score >= 4 and retained < cap:
                decision = "RETAIN_CONDITIONAL_MEDIA_EVIDENCE" if media else "RETAIN_FOR_ASSET_AUTHORING_EVALUATION"
                retained += 1
            elif score >= 2 and retained < cap:
                decision = "DEFER_SUPPORT_ONLY"
                retained += 1
            elif score <= 0:
                decision = "REJECT_NO_INCREMENTAL_VALUE"
            else:
                decision = "DEFER_REDUNDANT_BINDING"
            if decision.startswith("RETAIN"):
                priority = "HIGH" if score >= 7 else "MEDIUM"
            elif decision == "DEFER_SUPPORT_ONLY":
                priority = "LOW"
            else:
                priority = "NONE"
            evaluated = dict(row)
            evaluated.update({
                "within_pku_rank": rank,
                "pku_binding_retention_cap": cap,
                "learning_value_priority": priority,
                "binding_decision": decision,
                "teacher_delivery_activation_status": "NOT_ACTIVATED",
                "remediation_activation_status": "NOT_ACTIVATED",
                "human_content_review_required": decision.startswith("RETAIN") or decision == "DEFER_SUPPORT_ONLY",
            })
            decision_counts[decision] += 1
            bindings.append(evaluated)
        retained_count = sum(count for decision, count in decision_counts.items() if decision.startswith("RETAIN"))
        recommended_lanes = []
        mode = str(rows[0]["knowledge_mode"])
        roles = set(rows[0]["teaching_roles"])
        if mode in {"TEACHER_METHOD", "PRONUNCIATION_SUPPORT", "LEARNER_SKILL"} or roles & {"INTRO", "SUPPORT", "FOCUS", "PRACTICE", "TRANSFER"}:
            recommended_lanes.append("TEACHER_DELIVERY")
        if mode == "ERROR_REPAIR" or rows[0]["knowledge_type"] == "ERROR_PATTERN" or roles & {"REMEDIATION", "ERROR_REPAIR"}:
            recommended_lanes.append("REMEDIATION")
        pku_rows.append({
            "pku_id": pku_id,
            "concept_id": rows[0]["concept_id"],
            "knowledge_mode": mode,
            "knowledge_type": rows[0]["knowledge_type"],
            "teaching_roles": rows[0]["teaching_roles"],
            "binding_count": len(rows),
            "retention_cap": cap,
            "maximum_incremental_value_score": max(int(row["raw_incremental_value_score"]) for row in rows),
            "recommended_lanes": sorted(recommended_lanes),
            "retained_binding_count": retained_count,
            "decision_counts": dict(sorted(decision_counts.items())),
            "pku_decision": "RETAIN_FOR_SELECTIVE_AUTHORING" if retained_count else "NO_INCREMENTAL_VALUE_IN_CURRENT_MATERIALS",
        })
    decision_counts = Counter(row["binding_decision"] for row in bindings)
    priority_counts = Counter(row["learning_value_priority"] for row in bindings)
    result = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_current_material_comparative_learning_value_evaluation",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m4a_intake_sha256": digest(intake),
            "m2_consumer_sha256": digest(consumer),
            "pku_bridge_sha256": digest(bridge),
        },
        "evaluation_policy": {
            "evaluation_mode": "DETERMINISTIC_MACHINE_ASSISTED_CURRENT_MATERIAL_COMPARISON",
            "comparison_surfaces": ["M2_ASSET_PAYLOAD", "M2_ASSET_ROLES", "M2_REQUIREMENT_NODES", "PKU_KNOWLEDGE_MODE", "PKU_TEACHING_ROLES"],
            "binding_is_not_independent_content_unit": True,
            "pku_level_deduplication_required": True,
            "current_material_presence_does_not_prove_pedagogical_equivalence": True,
            "human_content_review_required_before_authoring_or_activation": True,
            "activation_allowed": False,
        },
        "pku_evaluations": pku_rows,
        "binding_evaluations": sorted(bindings, key=lambda row: row["asset_candidate_id"]),
        "counts": {
            "source_pku_count": len(pku_rows),
            "source_binding_count": len(bindings),
            "referenced_lesson_count": len({row["lesson_id"] for row in bindings}),
            "retained_pku_count": sum(row["pku_decision"] == "RETAIN_FOR_SELECTIVE_AUTHORING" for row in pku_rows),
            "no_incremental_value_pku_count": sum(row["pku_decision"] != "RETAIN_FOR_SELECTIVE_AUTHORING" for row in pku_rows),
            "binding_decision_counts": dict(sorted(decision_counts.items())),
            "binding_priority_counts": dict(sorted(priority_counts.items())),
            "teacher_delivery_activated_count": 0,
            "remediation_activated_count": 0,
            "learner_facing_asset_count": 0,
            "mastery_evidence_delta": 0,
            "canonical_coverage_delta": 0,
            "private_text_exposure_count": 0,
        },
        "claim_boundaries": {
            "learning_value_evaluation_completed": True,
            "pedagogical_effectiveness_proven": False,
            "teacher_delivery_assets_authored": False,
            "remediation_assets_authored": False,
            "runtime_activation_completed": False,
            "composition_items_modified": False,
            "lesson_selection_modified": False,
            "canonical_graph_modified": False,
            "mastery_denominator_modified": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    result["artifact_sha256"] = digest(result)
    return result


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4a-intake", type=Path, default=DEFAULT_INTAKE)
    parser.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    parser.add_argument("--pku-bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.m4a_intake), read_json(args.m2_consumer), read_json(args.pku_bridge))
    write(args.output, artifact)
    print(json.dumps(artifact["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
