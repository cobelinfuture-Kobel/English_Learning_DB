"""Build a metadata-only tiny pilot for E4S Reading V1 candidates.

This builder is intentionally bounded by the P1-S9 pilot policy. It consumes
only the metadata query helper and the source manifest. It must not read source
text payloads, generate learner-facing output, create learner state, create
adaptive recommendations, or upgrade any source authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import query_e4s_reading_v1_sources as source_query


SCHEMA_VERSION = "READING_V1_PILOT_SUMMARY_V1"
CANDIDATE_SCHEMA_VERSION = "READING_V1_CANDIDATE_SCHEMA_V1"
PHASE_ID = "E4S-P1_ReadingV1SourceGroundedPractice"
TASK_ID = "E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation"
PILOT_POLICY_REF = "docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md"
NEXT_SHORTEST_STEP = "E4S-P1-S11_ReadingV1_PilotCandidateReadbackQA"
DEFAULT_MAX_CANDIDATE_COUNT = 3
HARD_MAX_CANDIDATE_COUNT = 5

PASS = "PASS"
PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

RECOMMENDED_QUESTION_TYPES = ["literal_what", "literal_where", "literal_yes_no"]


class PilotPolicyError(ValueError):
    """Raised when a requested pilot violates P1-S9 policy."""


BLOCKED_OUTPUT_STATE_FALSE = {
    "learner_facing_output_created": False,
    "student_html_created": False,
    "worksheet_created": False,
    "learner_event_created": False,
    "learner_state_updated": False,
    "adaptive_recommendation_created": False,
    "authority_promotion_performed": False,
    "large_scale_generation_performed": False,
}


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    return source_query.load_manifest(manifest_path)


def ensure_policy_count(candidate_count: int) -> None:
    if candidate_count < 1:
        raise PilotPolicyError("candidate_count must be >= 1")
    if candidate_count > HARD_MAX_CANDIDATE_COUNT:
        raise PilotPolicyError(
            f"candidate_count {candidate_count} exceeds hard_max_candidate_count {HARD_MAX_CANDIDATE_COUNT}"
        )


def query_candidate_trace_seeds(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    report = source_query.build_report(manifest, manifest_path, "candidate_trace_seed")
    if report["status"] in {FAIL, BLOCKED}:
        raise PilotPolicyError("source query report status is FAIL or BLOCKED")
    primary = [
        record
        for record in report["records"]
        if record.get("query_class") == "PRIMARY_READING_CANDIDATE_INPUT"
    ]
    if not primary:
        raise PilotPolicyError("no primary Reading source is available")
    return report


def pick_seed_records(query_report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    records = list(query_report.get("records") or [])
    primary = next(record for record in records if record["query_class"] == "PRIMARY_READING_CANDIDATE_INPUT")
    evidence = next(
        (record for record in records if record["query_class"] == "SUPPORTING_READING_EXPOSURE_EVIDENCE"),
        None,
    )
    references = [record for record in records if str(record.get("query_class", "")).startswith("SCHEMA_REFERENCE_ONLY_")]
    return primary, evidence, references


def make_source_trace(primary_seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": primary_seed["source_id"],
        "source_family": primary_seed["source_family"],
        "authority_role": primary_seed["authority_role"],
        "source_path_ref": primary_seed["source_path_ref"],
        "source_unit_ref": primary_seed["source_unit_ref_policy"],
        "source_license_status": primary_seed["license_status"],
        "source_review_status": primary_seed["review_status"],
        "source_trace_required": True,
        "source_payload_copied": False,
    }


def make_source_policy(primary_seed: dict[str, Any]) -> dict[str, Any]:
    policy = primary_seed["source_policy_snapshot"]
    return {
        "allowed_use_snapshot": list(policy.get("allowed_use_snapshot") or []),
        "blocked_use_snapshot": list(policy.get("blocked_use_snapshot") or []),
        "promotion_rule": policy.get("promotion_rule") or "manual_review_required_no_auto_promotion",
        "risk_flags": list(policy.get("risk_flags") or []),
        "public_distribution_allowed": False,
        "learner_facing_allowed": False,
        "authority_promotion_allowed": False,
    }


def make_constraint_refs(evidence_seed: dict[str, Any] | None, references: list[dict[str, Any]]) -> dict[str, str]:
    refs: dict[str, str] = {}
    if evidence_seed is not None:
        refs["wordlist_evidence_ref"] = f"source:{evidence_seed['source_id']}"
    for record in references:
        source_id = record["source_id"]
        if source_id == "EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE":
            refs["grammar_reference_ref"] = f"source:{source_id}"
        elif source_id == "EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE":
            refs["vocabulary_reference_ref"] = f"source:{source_id}"
        elif source_id == "NGSL_SOURCE_FREQUENCY_PROFILE":
            refs["frequency_reference_ref"] = f"source:{source_id}"
        elif source_id == "CHUNK_SAFE_LAYER_REFERENCE":
            refs["chunk_reference_ref"] = f"source:{source_id}"
    return refs


def build_candidate(index: int, primary_seed: dict[str, Any], evidence_seed: dict[str, Any] | None, references: list[dict[str, Any]]) -> dict[str, Any]:
    question_type = RECOMMENDED_QUESTION_TYPES[(index - 1) % len(RECOMMENDED_QUESTION_TYPES)]
    candidate_id = f"reading_v1_pilot_{index:03d}"
    evidence_id = f"{candidate_id}:evidence:locator_only"
    passage_ref = f"metadata_locator:{primary_seed['source_id']}:pilot:{index:03d}"

    return {
        "reading_candidate_id": candidate_id,
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "candidate_status": "candidate_generated",
        "source_trace": make_source_trace(primary_seed),
        "source_policy": make_source_policy(primary_seed),
        "reading_payload_ref": {
            "passage_ref": passage_ref,
            "passage_level_ref": "metadata_only_unverified",
            "passage_title_ref": "metadata_only_title_not_copied",
            "passage_excerpt_allowed": False,
        },
        "question_model": {
            "question_id": f"{candidate_id}:question:001",
            "question_type": question_type,
            "question_text": f"Metadata-only pilot question for {passage_ref}.",
            "question_language": "en",
            "question_level_band": "metadata_only_unverified",
            "requires_evidence": True,
        },
        "answer_model": {
            "answer_type": "short_text",
            "expected_answer": "manual review required from source locator",
            "acceptable_answers": ["manual review required"],
            "answer_source": "manual_review_required",
            "answer_evidence_ref": evidence_id,
        },
        "evidence_model": {
            "evidence_id": evidence_id,
            "evidence_type": "source_locator_only",
            "source_trace_ref": primary_seed["candidate_trace_seed_id"],
            "evidence_locator": passage_ref,
            "evidence_text_allowed": False,
            "manual_review_required": True,
        },
        "level_metadata": {
            "level_system": "RAZ",
            "raw_level_code": "metadata_only_unverified",
            "normalized_level_band": "UNKNOWN",
            "level_claim_status": "metadata_only_unverified",
            "level_evidence_role": "source_metadata_reference_only",
            "learner_placement_allowed": False,
        },
        "situation_metadata": {
            "situation_domain": "metadata_only_reading_pilot",
            "situation_context": "source_trace_smoke_test",
            "communicative_function": "reading_candidate_schema_smoke_test",
            "interaction_mode": "solo_reading",
            "situation_claim_status": "metadata_only_unverified",
        },
        "skill_metadata": {
            "skill_fit": "reading_candidate",
            "target_phase": PHASE_ID,
            "multi_skill_expansion_allowed": False,
        },
        "constraint_refs": make_constraint_refs(evidence_seed, references),
        "validation_state": {
            "schema_validation_status": "not_run",
            "source_trace_validation_status": "not_run",
            "evidence_validation_status": "not_run",
            "blocked_output_validation_status": "not_run",
            "validator_version": "pending_P1_S12",
        },
        "manual_review_state": {
            "manual_review_required": True,
            "manual_review_status": "pending",
            "review_notes": ["Metadata-only tiny pilot; source payload not inspected."],
        },
        "blocked_output_state": dict(BLOCKED_OUTPUT_STATE_FALSE),
        "audit_trail": {
            "created_by_task": TASK_ID,
            "created_from_contracts": [
                "docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md",
                "docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md",
                "docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md",
                "docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md",
                PILOT_POLICY_REF,
            ],
            "source_manifest_version_ref": "ulga/graph/e4s_source_manifest.json",
            "warnings": ["manual_review_required", "payload_policy_locator_only"],
            "deferred_issues": ["actual_source_payload_validation_deferred_until_policy"],
        },
    }


def build_candidates(manifest: dict[str, Any], manifest_path: Path, candidate_count: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ensure_policy_count(candidate_count)
    query_report = query_candidate_trace_seeds(manifest, manifest_path)
    primary_seed, evidence_seed, references = pick_seed_records(query_report)
    candidates = [build_candidate(index, primary_seed, evidence_seed, references) for index in range(1, candidate_count + 1)]
    return candidates, query_report


def validate_candidates_against_policy(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if len(candidates) > HARD_MAX_CANDIDATE_COUNT:
        issues.append({"code": "READING_V1_PILOT_COUNT_EXCEEDS_HARD_CAP", "blocking": True})

    for candidate in candidates:
        candidate_id = candidate.get("reading_candidate_id")
        source_trace = candidate.get("source_trace", {})
        source_policy = candidate.get("source_policy", {})
        reading_payload_ref = candidate.get("reading_payload_ref", {})
        evidence_model = candidate.get("evidence_model", {})
        question_model = candidate.get("question_model", {})

        checks = {
            "source_payload_copied": source_trace.get("source_payload_copied") is False,
            "passage_excerpt_allowed": reading_payload_ref.get("passage_excerpt_allowed") is False,
            "evidence_text_allowed": evidence_model.get("evidence_text_allowed") is False,
            "learner_facing_allowed": source_policy.get("learner_facing_allowed") is False,
            "authority_promotion_allowed": source_policy.get("authority_promotion_allowed") is False,
            "requires_evidence": question_model.get("requires_evidence") is True,
        }
        for check_name, passed in checks.items():
            if not passed:
                issues.append({"code": f"READING_V1_PILOT_{check_name.upper()}_FAILED", "candidate_id": candidate_id, "blocking": True})

        for field, value in candidate.get("blocked_output_state", {}).items():
            if value is not False:
                issues.append({"code": "READING_V1_PILOT_BLOCKED_OUTPUT_TRUE", "candidate_id": candidate_id, "field": field, "blocking": True})
    return issues


def build_summary(
    candidates: list[dict[str, Any]],
    query_report: dict[str, Any],
    candidate_output_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    issues = validate_candidates_against_policy(candidates)
    warnings = [
        {
            "code": "READING_V1_PILOT_METADATA_ONLY",
            "severity": "medium",
            "message": "Tiny pilot is metadata-only and requires manual review before content use.",
            "blocking": False,
        }
    ]
    status = FAIL if issues else PASS_WITH_WARNINGS
    source_ids_used = sorted({candidate["source_trace"]["source_id"] for candidate in candidates})
    question_types_used = sorted({candidate["question_model"]["question_type"] for candidate in candidates})

    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "pilot_policy_ref": PILOT_POLICY_REF,
        "candidate_artifact_path": str(candidate_output_path),
        "candidate_count": len(candidates),
        "max_candidate_count": DEFAULT_MAX_CANDIDATE_COUNT,
        "hard_max_candidate_count": HARD_MAX_CANDIDATE_COUNT,
        "source_query_report_ref": "in_memory:query_e4s_reading_v1_sources:candidate_trace_seed",
        "source_manifest_ref": str(manifest_path),
        "source_ids_used": source_ids_used,
        "question_types_used": question_types_used,
        "metadata_only": True,
        "payload_access_allowed": False,
        "learner_facing_allowed": False,
        "authority_upgrade_allowed": False,
        "blocked_output_state_summary": {
            "all_false": all(
                value is False
                for candidate in candidates
                for value in candidate.get("blocked_output_state", {}).values()
            ),
            "fields": sorted(BLOCKED_OUTPUT_STATE_FALSE),
        },
        "validation_readiness": {
            "schema_shape_present": True,
            "source_trace_present": True,
            "evidence_locator_present": all(bool(candidate["evidence_model"].get("evidence_locator")) for candidate in candidates),
            "manual_review_required": True,
            "validator_task": "E4S-P1-S12_ReadingV1_CandidateValidator_Implementation",
        },
        "query_report_status": query_report.get("status"),
        "warnings": warnings,
        "issues": issues,
        "status": status,
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Reading V1 metadata-only tiny pilot candidates.")
    parser.add_argument("--manifest-path", default="ulga/graph/e4s_source_manifest.json")
    parser.add_argument("--candidate-output", default="ulga/reports/reading_v1_pilot_candidates.json")
    parser.add_argument("--summary-output", default="ulga/reports/reading_v1_pilot_summary.json")
    parser.add_argument("--candidate-count", type=int, default=DEFAULT_MAX_CANDIDATE_COUNT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest_path)
    candidate_output_path = Path(args.candidate_output)
    summary_output_path = Path(args.summary_output)

    try:
        manifest = load_manifest(manifest_path)
        candidates, query_report = build_candidates(manifest, manifest_path, args.candidate_count)
        summary = build_summary(candidates, query_report, candidate_output_path, manifest_path)
    except (FileNotFoundError, PilotPolicyError, json.JSONDecodeError, ValueError) as exc:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "task_id": TASK_ID,
            "pilot_policy_ref": PILOT_POLICY_REF,
            "candidate_artifact_path": str(candidate_output_path),
            "candidate_count": 0,
            "max_candidate_count": DEFAULT_MAX_CANDIDATE_COUNT,
            "hard_max_candidate_count": HARD_MAX_CANDIDATE_COUNT,
            "source_query_report_ref": None,
            "source_manifest_ref": str(manifest_path),
            "source_ids_used": [],
            "question_types_used": [],
            "metadata_only": True,
            "payload_access_allowed": False,
            "learner_facing_allowed": False,
            "authority_upgrade_allowed": False,
            "blocked_output_state_summary": {"all_false": True, "fields": sorted(BLOCKED_OUTPUT_STATE_FALSE)},
            "validation_readiness": {"schema_shape_present": False, "source_trace_present": False, "evidence_locator_present": False},
            "warnings": [],
            "issues": [{"code": "READING_V1_PILOT_BUILD_FAILED", "message": str(exc), "blocking": True}],
            "status": FAIL,
            "next_shortest_step": NEXT_SHORTEST_STEP,
        }
        write_json(summary_output_path, summary)
        return 1

    write_json(candidate_output_path, candidates)
    write_json(summary_output_path, summary)
    return 0 if summary["status"] in {PASS, PASS_WITH_WARNINGS} else 1


if __name__ == "__main__":
    sys.exit(main())
