#!/usr/bin/env python3
"""Prepare and apply fail-closed local Reading review decisions for M04B3."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.validators.validate_a1_a1plus_local_reading_practice_bank import (  # noqa: E402
    validate_materialization,
)

TASK_ID = "E4S-A1V1-M04B3_SourceGroundedReadingCandidateReviewAndPromotion"
QUEUE_SCHEMA = "e4s.a1v1.reading_review_queue.v1"
DECISIONS_SCHEMA = "e4s.a1v1.reading_operator_decisions.v1"
BANK_SCHEMA = "e4s.a1v1.reviewed_reading_practice_bank.v1"
REPORT_SCHEMA = "e4s.a1v1.reading_review_promotion_safe_report.v1"
EXPECTED_SOURCE_COUNT = 54
EXPECTED_DETERMINISTIC = {"true_false": 54, "cloze_vocabulary": 54, "sentence_ordering": 36}
EXPECTED_LITERAL = {"literal_who": 49, "literal_what": 54, "literal_where": 34}
QUESTION_TYPES = tuple((*EXPECTED_DETERMINISTIC, *EXPECTED_LITERAL))
LITERAL_TYPES = frozenset(EXPECTED_LITERAL)
DECISION_VALUES = ("PENDING", "APPROVE_AS_IS", "APPROVE_WITH_REVISION", "REJECT", "DEFER")
CRITERIA = {
    "true_false": (
        "source_grounding_verified", "statement_is_unambiguous", "answer_key_verified",
        "age_and_level_appropriate", "language_is_natural", "all_true_bias_reviewed",
        "copyright_boundary_accepted",
    ),
    "cloze_vocabulary": (
        "source_grounding_verified", "blank_target_verified", "answer_key_verified",
        "single_answer_or_accepted_variants_defined", "a1_a1plus_appropriate",
        "not_trivial_or_misleading", "language_is_natural", "copyright_boundary_accepted",
    ),
    "sentence_ordering": (
        "source_grounding_verified", "original_order_verified", "display_order_is_non_identity",
        "sequence_is_meaningful", "answer_key_verified", "a1_a1plus_appropriate",
        "copyright_boundary_accepted",
    ),
    "literal": (
        "source_grounding_verified", "question_type_verified", "prompt_is_natural",
        "answer_is_explicit_in_source", "accepted_answers_complete", "a1_a1plus_appropriate",
        "no_unsupported_inference", "copyright_boundary_accepted",
    ),
}
FORBIDDEN_SAFE_KEYS = {
    "text", "source_text", "sentence", "sentences", "source_sentences", "prompt", "answer",
    "answer_key", "answer_model", "accepted_answers", "cloze_target", "display_order",
    "review_notes", "source_payload", "candidate_content", "revision",
}
CLAIM_BOUNDARIES = {
    "private_local_only": True,
    "canonical_authority_promotion": False,
    "public_learner_delivery": False,
    "source_text_public_export": False,
    "m04b1_m04b2_mutated": False,
}


class PromotionBuildError(ValueError):
    """Fail-closed M04B3 contract error."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionBuildError(f"json_unreadable:{path}:{exc}") from exc


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _schema(name: str) -> Draft202012Validator:
    schema = read_json(REPO_ROOT / "ulga" / "schemas" / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _assert_schema(name: str, payload: Mapping[str, Any]) -> None:
    errors = sorted(_schema(name).iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(map(str, first.absolute_path)) or "$"
        raise PromotionBuildError(f"schema_validation_failed:{name}:{path}:{first.message}")


def _safe_scan(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if is_forbidden_safe_key(key):
                raise PromotionBuildError(f"safe_text_or_answer_leakage:{path}.{key}")
            _safe_scan(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _safe_scan(child, f"{path}[{index}]")


def is_forbidden_safe_key(key: Any) -> bool:
    lowered = str(key).lower()
    return (
        lowered in FORBIDDEN_SAFE_KEYS
        or "prompt" in lowered
        or "answer" in lowered
        or "display_order" in lowered
        or lowered.endswith("_text")
        or lowered.endswith("_sentence")
        or lowered.endswith("_sentences")
    )


def _counts_match(summary: Mapping[str, Any]) -> bool:
    return (
        summary.get("selected_source_count") == EXPECTED_SOURCE_COUNT
        and summary.get("deterministic_item_counts") == EXPECTED_DETERMINISTIC
        and summary.get("literal_review_candidate_counts") == EXPECTED_LITERAL
    )


def validate_m04b2(private: Mapping[str, Any], safe: Mapping[str, Any]) -> None:
    result = validate_materialization(private, safe)
    if result.get("validation_status") != "PASS_LOCAL_READING_PRACTICE_BANK":
        raise PromotionBuildError(f"m04b2_validation_failed:{result.get('errors', [])}")
    if private.get("summary") != safe.get("summary") or not _counts_match(safe.get("summary", {})):
        raise PromotionBuildError("m04b2_safe_baseline_drift")


def validate_s12d(private: Mapping[str, Any], safe: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    bindings = private.get("bindings")
    if not isinstance(bindings, list) or len(bindings) != EXPECTED_SOURCE_COUNT:
        raise PromotionBuildError("s12d_binding_count_not_54")
    if private.get("binding_count") != len(bindings):
        raise PromotionBuildError("s12d_binding_accounting_drift")
    if private.get("bindings_sha256") != sha256_value(bindings):
        raise PromotionBuildError("s12d_bindings_hash_drift")
    if safe.get("validation_status") != "PASS_AF_OBSERVATIONAL_CONSUMER_AND_M04B2_COMPATIBLE":
        raise PromotionBuildError("s12d_safe_not_validated")
    if safe.get("selected_source_count") != EXPECTED_SOURCE_COUNT:
        raise PromotionBuildError("s12d_safe_source_count_drift")
    if safe.get("bindings_sha256") != private.get("bindings_sha256"):
        raise PromotionBuildError("s12d_private_safe_hash_mismatch")
    binding_validator = _schema("raz_af_a1_a1plus_observational_consumer_binding.schema.json")
    for index, binding in enumerate(bindings):
        errors = list(binding_validator.iter_errors(binding))
        if errors:
            raise PromotionBuildError(f"s12d_binding_schema_invalid:{index}:{errors[0].message}")
    safe_errors = list(_schema("raz_af_a1_a1plus_observational_consumer_safe_report.schema.json").iter_errors(safe))
    if safe_errors:
        raise PromotionBuildError(f"s12d_safe_schema_invalid:{safe_errors[0].message}")
    by_ref: dict[str, Mapping[str, Any]] = {}
    for binding in bindings:
        ref = binding.get("selection_identity", {}).get("source_unit_ref")
        if not isinstance(ref, str) or ref in by_ref:
            raise PromotionBuildError(f"s12d_duplicate_or_invalid_join:{ref}")
        by_ref[ref] = binding
    return by_ref


def _precheck(name: str, status: str, code: str) -> dict[str, str]:
    return {"name": name, "status": status, "code": code}


def _candidate_signature(candidate: Mapping[str, Any]) -> str:
    return sha256_value({"prompt": candidate.get("prompt"), "answer_model": candidate.get("answer_model")})


def _ordering_is_identity(candidate: Mapping[str, Any]) -> bool:
    display = candidate.get("display_order")
    if not isinstance(display, list):
        return False
    display_ids = [row.get("sentence_id") if isinstance(row, Mapping) else row for row in display]
    answer_model = candidate.get("answer_model", {})
    correct = answer_model.get("answer_key", answer_model.get("correct_order")) if isinstance(answer_model, Mapping) else None
    return isinstance(correct, list) and display_ids == correct


def _candidate_local_block_reason(candidate: Mapping[str, Any]) -> str | None:
    qtype = candidate.get("question_type")
    if qtype == "sentence_ordering" and _ordering_is_identity(candidate):
        return "identity_ordering"
    if qtype == "cloze_vocabulary":
        answer = candidate.get("answer_model")
        if "____" not in str(candidate.get("prompt", "")) or not isinstance(answer, Mapping) or not str(answer.get("answer_key", "")).strip():
            return "empty_or_trivial_cloze"
    if qtype in LITERAL_TYPES and candidate.get("auto_answer_generated") is not False:
        return "unsupported_literal_auto_answer"
    return None


def _build_prechecks(
    record: Mapping[str, Any], candidate: Mapping[str, Any], binding: Mapping[str, Any],
    known_sentence_ids: set[str], duplicate_signature: bool,
) -> dict[str, Any]:
    qtype = str(candidate.get("question_type"))
    decision = binding.get("consumer_decision", {})
    canonical = binding.get("canonical_consumer_state", {})
    activity = next((row for row in decision.get("activity_support", []) if row.get("activity_type") == qtype), {})
    refs = candidate.get("source_sentence_ids", [])
    answer_model = candidate.get("answer_model")
    checks = [
        _precheck("source_integrity", "PASS", "SOURCE_HASHES_MATCH"),
        _precheck("m04b2_candidate_hash", "PASS", "CANDIDATE_HASH_CAPTURED"),
        _precheck("s12d_selected_source_join", "PASS", "S12D_JOIN_MATCH"),
        _precheck(
            "canonical_eligibility",
            "BLOCK" if str(decision.get("canonical_eligibility_status", "")).startswith("BLOCKED") else "PASS",
            str(decision.get("canonical_eligibility_status")),
        ),
        _precheck("question_type_contract", "PASS" if qtype in QUESTION_TYPES else "BLOCK", "QUESTION_TYPE_RECOGNIZED"),
        _precheck(
            "deterministic_scoring_readiness",
            "PASS" if qtype in LITERAL_TYPES or candidate.get("deterministic_scoring_ready") is True else "BLOCK",
            "READY_OR_LITERAL_REVIEW",
        ),
        _precheck(
            "answer_model_presence",
            "WARNING" if qtype in LITERAL_TYPES else ("PASS" if isinstance(answer_model, Mapping) else "BLOCK"),
            "LITERAL_REVISION_REQUIRED" if qtype in LITERAL_TYPES else "DETERMINISTIC_ANSWER_PRESENT",
        ),
        _precheck(
            "source_sentence_reference_existence", "PASS" if isinstance(refs, list) and bool(refs) and set(refs) <= known_sentence_ids else "BLOCK",
            "SOURCE_SENTENCE_IDS_RESOLVE",
        ),
        _precheck("duplicate_prompt_answer_signature", "WARNING" if duplicate_signature else "PASS", "DUPLICATE_SIGNATURE_REVIEWED" if duplicate_signature else "UNIQUE_SIGNATURE"),
        _precheck(
            "empty_or_trivial_cloze",
            "BLOCK" if _candidate_local_block_reason(candidate) == "empty_or_trivial_cloze" else "PASS",
            "CLOZE_CONTRACT_CHECKED",
        ),
        _precheck(
            "identity_ordering",
            "BLOCK" if _candidate_local_block_reason(candidate) == "identity_ordering" else "PASS",
            "ORDERING_NON_IDENTITY_CHECKED",
        ),
        _precheck(
            "unsupported_literal_auto_answer",
            "BLOCK" if _candidate_local_block_reason(candidate) == "unsupported_literal_auto_answer" else "PASS",
            "NO_LITERAL_AUTO_ANSWER",
        ),
        _precheck("source_or_candidate_hash_drift", "PASS", "HASHES_CURRENT"),
        _precheck("promotion_authority_boundary", "PASS", "PRIVATE_LOCAL_ONLY"),
    ]
    if activity.get("support_status") in {"UNKNOWN", "CONFLICT_REVIEW_REQUIRED"}:
        checks.append(_precheck("observational_activity_support", "WARNING", "OPERATOR_ACKNOWLEDGEMENT_REQUIRED"))
    statuses = {item["status"] for item in checks}
    overall = "BLOCK" if "BLOCK" in statuses else ("WARNING" if "WARNING" in statuses else "PASS")
    return {"overall_status": overall, "checks": checks}


def prepare_artifacts(
    m04b2_private: Mapping[str, Any], m04b2_safe: Mapping[str, Any],
    s12d_private: Mapping[str, Any], s12d_safe: Mapping[str, Any],
    upstream_hashes: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validate_m04b2(m04b2_private, m04b2_safe)
    s12d_by_ref = validate_s12d(s12d_private, s12d_safe)
    raw: list[tuple[Mapping[str, Any], Mapping[str, Any], str]] = []
    signatures = Counter()
    for record in m04b2_private.get("records", []):
        for candidate in (*record.get("deterministic_items", []), *record.get("literal_review_candidates", [])):
            origin = "M04B2_LITERAL_REVIEW" if candidate.get("question_type") in LITERAL_TYPES else "M04B2_DETERMINISTIC"
            raw.append((record, candidate, origin))
            signatures[_candidate_signature(candidate)] += 1
    if len(raw) != sum(EXPECTED_DETERMINISTIC.values()) + sum(EXPECTED_LITERAL.values()):
        raise PromotionBuildError(f"review_candidate_count_not_281:{len(raw)}")
    entries = []
    for record, candidate, origin in raw:
        selection = record["selection"]
        ref = selection["source_unit_ref"]
        binding = s12d_by_ref.get(ref)
        if binding is None:
            raise PromotionBuildError(f"missing_s12d_binding:{ref}")
        identity = binding.get("selection_identity", {})
        for field in ("selection_id", "source_unit_ref", "content_sha256", "record_sha256"):
            if identity.get(field) != selection.get(field):
                raise PromotionBuildError(f"s12d_source_join_drift:{ref}:{field}")
        candidate_id = candidate.get("item_id") or candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise PromotionBuildError(f"candidate_id_missing:{ref}")
        payload_hash = sha256_value(candidate)
        sentence_ids = {row["sentence_id"] for row in record.get("source_sentences", [])}
        entry_id = f"M04B3_REVIEW_{hashlib.sha256(candidate_id.encode()).hexdigest()[:20].upper()}"
        prechecks = _build_prechecks(record, candidate, binding, sentence_ids, signatures[_candidate_signature(candidate)] > 1)
        requirements = list(CRITERIA["literal" if candidate["question_type"] in LITERAL_TYPES else candidate["question_type"]])
        requirements.extend(
            f"warning_acknowledged__{check['name']}"
            for check in prechecks["checks"] if check["status"] == "WARNING"
        )
        entries.append({
            "review_entry_id": entry_id,
            "selection_id": selection["selection_id"],
            "source_unit_ref": ref,
            "candidate_id": candidate_id,
            "question_type": candidate["question_type"],
            "candidate_origin": origin,
            "source_integrity": {
                "content_sha256": selection["content_sha256"], "record_sha256": selection["record_sha256"], "status": "PASS",
            },
            "candidate_payload_sha256": payload_hash,
            "candidate_content": copy.deepcopy(candidate),
            "source_evidence": {"source_sentence_ids": list(candidate.get("source_sentence_ids", []))},
            "canonical_context": copy.deepcopy(binding.get("canonical_consumer_state", {})),
            "observational_support": {
                "binding_sha256": sha256_value(binding),
                "consumer_decision": copy.deepcopy(binding.get("consumer_decision", {})),
                "observations": copy.deepcopy(binding.get("observational_support", {})),
            },
            "automated_prechecks": prechecks,
            "review_requirements": requirements,
            "review_status": "PENDING_OPERATOR_REVIEW",
            "promotion_status": "not_promoted",
        })
    entries.sort(key=lambda row: (row["selection_id"], QUESTION_TYPES.index(row["question_type"]), row["candidate_id"]))
    if len({row["candidate_id"] for row in entries}) != len(entries) or len({row["review_entry_id"] for row in entries}) != len(entries):
        raise PromotionBuildError("duplicate_candidate_or_review_entry")
    queue = {
        "task_id": TASK_ID, "schema_version": QUEUE_SCHEMA, "artifact_type": "private_reading_review_queue",
        "policy": {"private_local_only": True, "must_not_be_committed": True, "automatic_approval": False},
        "upstream_hashes": dict(upstream_hashes), "review_entry_count": len(entries), "review_entries": entries,
        "review_entries_sha256": sha256_value(entries), "claim_boundaries": dict(CLAIM_BOUNDARIES),
    }
    decisions = {
        "task_id": TASK_ID, "schema_version": DECISIONS_SCHEMA, "artifact_type": "local_operator_decision_registry",
        "policy": {"private_local_only": True, "must_not_be_committed": True, "template_is_approval": False},
        "review_queue_sha256": sha256_value(queue),
        "decisions": [{
            "review_entry_id": row["review_entry_id"], "candidate_id": row["candidate_id"],
            "source_content_sha256": row["source_integrity"]["content_sha256"],
            "candidate_payload_sha256": row["candidate_payload_sha256"], "decision": "PENDING",
            "reviewer_id": None, "reviewed_at": None, "criteria": {}, "revision": None,
            "rejection_reasons": [], "review_notes": None,
        } for row in entries],
    }
    qdist = {key: sum(row["question_type"] == key for row in entries) for key in QUESTION_TYPES}
    prechecks = Counter(row["automated_prechecks"]["overall_status"] for row in entries)
    report = {
        "task_id": TASK_ID, "schema_version": REPORT_SCHEMA, "report_mode": "PREPARE_REVIEW",
        "upstream_hashes": dict(upstream_hashes), "candidate_counts": {
            "selected_sources": EXPECTED_SOURCE_COUNT, "deterministic": sum(EXPECTED_DETERMINISTIC.values()),
            "literal": sum(EXPECTED_LITERAL.values()), "total": len(entries),
        },
        "decision_counts": {key: len(entries) if key == "PENDING" else 0 for key in DECISION_VALUES},
        "question_type_distribution": qdist,
        "precheck_distribution": {key: prechecks[key] for key in ("PASS", "WARNING", "BLOCK")},
        "promotion_eligibility_distribution": {"eligible_after_operator_approval": sum(row["automated_prechecks"]["overall_status"] != "BLOCK" for row in entries), "blocked": prechecks["BLOCK"]},
        "reviewed_item_count": 0, "promotion_claim_count": 0, "rejection_reason_counts": {},
        "review_entries_sha256": queue["review_entries_sha256"], "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "validation_status": "PASS_PENDING_OPERATOR_REVIEW", "errors": [],
    }
    _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", decisions)
    _assert_schema("e4s_a1v1_reading_review_promotion_safe_report.schema.json", report)
    _safe_scan(report)
    return queue, decisions, report


def _decision_map(registry: Mapping[str, Any], queue: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if registry.get("review_queue_sha256") != sha256_value(queue):
        raise PromotionBuildError("decision_registry_queue_hash_mismatch")
    known = {row["review_entry_id"] for row in queue.get("review_entries", [])}
    result: dict[str, Mapping[str, Any]] = {}
    for decision in registry.get("decisions", []):
        entry_id = decision.get("review_entry_id")
        if entry_id not in known:
            raise PromotionBuildError(f"unknown_decision:{entry_id}")
        if entry_id in result:
            raise PromotionBuildError(f"duplicate_decision:{entry_id}")
        result[entry_id] = decision
    return result


def _validate_nonpending(entry: Mapping[str, Any], decision: Mapping[str, Any]) -> None:
    value = decision.get("decision")
    if value not in DECISION_VALUES:
        raise PromotionBuildError(f"invalid_decision:{value}")
    if value == "PENDING":
        return
    if not isinstance(decision.get("reviewer_id"), str) or not decision["reviewer_id"].strip():
        raise PromotionBuildError(f"reviewer_id_required:{entry['review_entry_id']}")
    if not isinstance(decision.get("reviewed_at"), str) or not decision["reviewed_at"].strip():
        raise PromotionBuildError(f"reviewed_at_required:{entry['review_entry_id']}")
    try:
        reviewed_at = datetime.fromisoformat(decision["reviewed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise PromotionBuildError(f"reviewed_at_invalid:{entry['review_entry_id']}") from exc
    if reviewed_at.tzinfo is None:
        raise PromotionBuildError(f"reviewed_at_timezone_required:{entry['review_entry_id']}")
    if decision.get("source_content_sha256") != entry["source_integrity"]["content_sha256"]:
        raise PromotionBuildError(f"stale_source_hash:{entry['review_entry_id']}")
    if decision.get("candidate_payload_sha256") != entry["candidate_payload_sha256"]:
        raise PromotionBuildError(f"stale_candidate_hash:{entry['review_entry_id']}")
    required = set(entry["review_requirements"])
    criteria = decision.get("criteria")
    if not isinstance(criteria, Mapping) or set(criteria) != required or any(criteria[key] is not True for key in required):
        raise PromotionBuildError(f"required_criteria_incomplete_or_false:{entry['review_entry_id']}")
    if value == "APPROVE_AS_IS" and entry["question_type"] in LITERAL_TYPES:
        raise PromotionBuildError(f"literal_approve_as_is_forbidden:{entry['review_entry_id']}")
    if value == "APPROVE_WITH_REVISION":
        revision = decision.get("revision")
        if not isinstance(revision, Mapping):
            raise PromotionBuildError(f"revision_required:{entry['review_entry_id']}")
        for key in ("prompt", "answer_model", "source_sentence_ids"):
            if not revision.get(key):
                raise PromotionBuildError(f"revision_missing_{key}:{entry['review_entry_id']}")
        if not isinstance(revision.get("accepted_answers"), list) or not revision["accepted_answers"]:
            raise PromotionBuildError(f"revision_missing_accepted_answers:{entry['review_entry_id']}")
        if not set(revision["source_sentence_ids"]) <= set(entry["source_evidence"]["source_sentence_ids"]):
            raise PromotionBuildError(f"revision_source_sentence_drift:{entry['review_entry_id']}")


def apply_artifacts(queue: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", registry)
    entries = queue.get("review_entries", [])
    if queue.get("review_entry_count") != len(entries) or queue.get("review_entries_sha256") != sha256_value(entries):
        raise PromotionBuildError("review_queue_accounting_or_hash_drift")
    decisions = _decision_map(registry, queue)
    reviewed = []
    decision_counts = Counter()
    rejection_reasons = Counter()
    for entry in entries:
        if entry.get("candidate_payload_sha256") != sha256_value(entry.get("candidate_content")):
            raise PromotionBuildError(f"stale_candidate_hash:{entry.get('review_entry_id')}")
        if entry.get("source_integrity", {}).get("status") != "PASS":
            raise PromotionBuildError(f"source_integrity_not_pass:{entry.get('review_entry_id')}")
        local_block = _candidate_local_block_reason(entry.get("candidate_content", {}))
        if local_block:
            raise PromotionBuildError(f"candidate_contract_block:{local_block}:{entry.get('review_entry_id')}")
        decision = decisions.get(entry["review_entry_id"])
        if decision is None:
            decision = {
                "decision": "PENDING", "source_content_sha256": entry["source_integrity"]["content_sha256"],
                "candidate_payload_sha256": entry["candidate_payload_sha256"],
            }
        if decision.get("candidate_id") not in (None, entry["candidate_id"]):
            raise PromotionBuildError(f"decision_candidate_join_mismatch:{entry['review_entry_id']}")
        _validate_nonpending(entry, decision)
        value = decision.get("decision", "PENDING")
        decision_counts[value] += 1
        rejection_reasons.update(decision.get("rejection_reasons", []))
        if value not in {"APPROVE_AS_IS", "APPROVE_WITH_REVISION"}:
            continue
        if entry["automated_prechecks"]["overall_status"] == "BLOCK":
            raise PromotionBuildError(f"block_precheck_cannot_be_overridden:{entry['review_entry_id']}")
        revision = decision.get("revision") if value == "APPROVE_WITH_REVISION" else None
        content = revision or entry["candidate_content"]
        prompt = content.get("prompt")
        answer_model = content.get("answer_model")
        accepted = content.get("accepted_answers")
        if entry["question_type"] == "cloze_vocabulary" and value == "APPROVE_WITH_REVISION" and not accepted:
            raise PromotionBuildError(f"cloze_revision_accepted_answers_missing:{entry['review_entry_id']}")
        if not isinstance(prompt, str) or not prompt.strip() or not isinstance(answer_model, Mapping):
            raise PromotionBuildError(f"final_prompt_or_answer_missing:{entry['review_entry_id']}")
        reviewed.append({
            "reviewed_item_id": f"M04B3_ITEM_{hashlib.sha256(entry['review_entry_id'].encode()).hexdigest()[:20].upper()}",
            "status": "REVIEWED_LOCAL_PRACTICE_ITEM", "selection_id": entry["selection_id"],
            "source_unit_ref": entry["source_unit_ref"],
            "source_integrity": copy.deepcopy(entry["source_integrity"]), "original_candidate_id": entry["candidate_id"],
            "question_type": entry["question_type"], "final_private_prompt": prompt,
            "final_private_answer_model": copy.deepcopy(answer_model),
            "accepted_answers": copy.deepcopy(accepted) if accepted is not None else [],
            "source_sentence_ids": copy.deepcopy(content.get("source_sentence_ids", entry["source_evidence"]["source_sentence_ids"])),
            "reviewer_id": decision["reviewer_id"], "decision_timestamp": decision["reviewed_at"],
            "decision_record_sha256": sha256_value(decision), "m04b2_candidate_sha256": entry["candidate_payload_sha256"],
            "s12d_observational_binding_sha256": entry["observational_support"]["binding_sha256"],
            "local_only_policy": True, "canonical_authority_promotion": False,
        })
    reviewed.sort(key=lambda row: row["reviewed_item_id"])
    if len({row["reviewed_item_id"] for row in reviewed}) != len(reviewed):
        raise PromotionBuildError("duplicate_reviewed_item")
    bank = {
        "task_id": TASK_ID, "schema_version": BANK_SCHEMA, "artifact_type": "reviewed_local_reading_practice_bank",
        "policy": {"private_local_only": True, "must_not_be_committed": True, "canonical_authority_promotion": False},
        "source_review_queue_sha256": sha256_value(queue), "source_decisions_sha256": sha256_value(registry),
        "reviewed_item_count": len(reviewed), "reviewed_items": reviewed,
        "reviewed_items_sha256": sha256_value(reviewed), "claim_boundaries": dict(CLAIM_BOUNDARIES),
    }
    qdist = {key: sum(row["question_type"] == key for row in entries) for key in QUESTION_TYPES}
    prechecks = Counter(row["automated_prechecks"]["overall_status"] for row in entries)
    report = {
        "task_id": TASK_ID, "schema_version": REPORT_SCHEMA, "report_mode": "APPLY_DECISIONS",
        "upstream_hashes": dict(queue.get("upstream_hashes", {})),
        "candidate_counts": {"selected_sources": EXPECTED_SOURCE_COUNT, "deterministic": sum(EXPECTED_DETERMINISTIC.values()), "literal": sum(EXPECTED_LITERAL.values()), "total": len(entries)},
        "decision_counts": {key: decision_counts[key] for key in DECISION_VALUES},
        "question_type_distribution": qdist,
        "precheck_distribution": {key: prechecks[key] for key in ("PASS", "WARNING", "BLOCK")},
        "promotion_eligibility_distribution": {"eligible_after_operator_approval": sum(row["automated_prechecks"]["overall_status"] != "BLOCK" for row in entries), "blocked": prechecks["BLOCK"]},
        "reviewed_item_count": len(reviewed), "promotion_claim_count": 0,
        "rejection_reason_counts": dict(sorted(rejection_reasons.items())),
        "review_entries_sha256": queue["review_entries_sha256"], "reviewed_items_sha256": bank["reviewed_items_sha256"],
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "validation_status": "PASS_PENDING_OPERATOR_REVIEW" if decision_counts["PENDING"] else "PASS",
        "errors": [],
    }
    _assert_schema("e4s_a1v1_reviewed_reading_practice_bank.schema.json", bank)
    _assert_schema("e4s_a1v1_reading_review_promotion_safe_report.schema.json", report)
    _safe_scan(report)
    return bank, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    prepare = sub.add_parser("prepare-review")
    prepare.add_argument("--m04b2-private", type=Path, required=True)
    prepare.add_argument("--m04b2-safe", type=Path, required=True)
    prepare.add_argument("--s12d-private", type=Path, required=True)
    prepare.add_argument("--s12d-safe", type=Path, required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    apply = sub.add_parser("apply-decisions")
    apply.add_argument("--review-queue", type=Path, required=True)
    apply.add_argument("--decisions", type=Path, required=True)
    apply.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "prepare-review":
            paths = (args.m04b2_private, args.m04b2_safe, args.s12d_private, args.s12d_safe)
            before = {path: sha256_file(path) for path in paths}
            upstream = {
                "m04b2_private_sha256": before[args.m04b2_private], "m04b2_safe_sha256": before[args.m04b2_safe],
                "s12d_private_sha256": before[args.s12d_private], "s12d_safe_sha256": before[args.s12d_safe],
            }
            queue, decisions, report = prepare_artifacts(
                read_json(args.m04b2_private), read_json(args.m04b2_safe),
                read_json(args.s12d_private), read_json(args.s12d_safe), upstream,
            )
            if any(sha256_file(path) != digest for path, digest in before.items()):
                raise PromotionBuildError("m04b1_m04b2_or_s12d_mutated")
            write_json_atomic(args.output_root / "review_queue.json", queue)
            write_json_atomic(args.output_root / "operator_decisions.template.json", decisions)
            write_json_atomic(args.output_root / "prepare_review_safe_report.json", report)
            print(json.dumps({"review_entries": len(queue["review_entries"]), "validation_status": report["validation_status"]}, sort_keys=True))
        else:
            queue, decisions = read_json(args.review_queue), read_json(args.decisions)
            bank, report = apply_artifacts(queue, decisions)
            write_json_atomic(args.output_root / "reviewed_private_reading_practice_bank.json", bank)
            write_json_atomic(args.output_root / "promotion_safe_report.json", report)
            print(json.dumps({"reviewed_items": len(bank["reviewed_items"]), "validation_status": report["validation_status"]}, sort_keys=True))
        return 0
    except (PromotionBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
