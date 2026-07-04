"""Deterministic metadata-only source query helper for E4S Reading V1.

This helper reads the E4S source manifest and emits metadata-only query
summaries for Reading V1 source routing. It must not read source payloads,
generate Reading candidates, create learner-facing output, mutate learner state,
or upgrade any source authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "READING_V1_SOURCE_QUERY_REPORT_V1"
PHASE_ID = "E4S-P1_ReadingV1SourceGroundedPractice"
TASK_ID = "E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation"
QUERY_HELPER_ID = "query_e4s_reading_v1_sources"
QUERY_HELPER_VERSION = "1.0.1"
NEXT_SHORTEST_STEP = "E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA"

PASS = "PASS"
PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

QUERY_MODES = {
    "eligible_reading_sources",
    "primary_reading_candidates",
    "supporting_evidence_sources",
    "reference_constraint_sources",
    "blocked_sources",
    "source_policy_snapshot",
    "candidate_trace_seed",
}

QUERY_CLASS_PRIORITY = {
    "PRIMARY_READING_CANDIDATE_INPUT": 10,
    "SUPPORTING_READING_EXPOSURE_EVIDENCE": 20,
    "SCHEMA_REFERENCE_ONLY_GRAMMAR": 30,
    "SCHEMA_REFERENCE_ONLY_VOCABULARY": 31,
    "SCHEMA_REFERENCE_ONLY_FREQUENCY": 32,
    "SCHEMA_REFERENCE_ONLY_CHUNK": 33,
    "STATUS_AUDIT_ONLY": 80,
    "GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT": 90,
    "OUT_OF_SCOPE_SKILL_CANDIDATE": 91,
    "GOVERNANCE_ONLY": 99,
    "UNKNOWN_OR_INVALID": 100,
}

ELIGIBLE_QUERY_CLASSES = {
    "PRIMARY_READING_CANDIDATE_INPUT",
    "SUPPORTING_READING_EXPOSURE_EVIDENCE",
    "SCHEMA_REFERENCE_ONLY_GRAMMAR",
    "SCHEMA_REFERENCE_ONLY_VOCABULARY",
    "SCHEMA_REFERENCE_ONLY_FREQUENCY",
    "SCHEMA_REFERENCE_ONLY_CHUNK",
}

REFERENCE_QUERY_CLASSES = {
    "SCHEMA_REFERENCE_ONLY_GRAMMAR",
    "SCHEMA_REFERENCE_ONLY_VOCABULARY",
    "SCHEMA_REFERENCE_ONLY_FREQUENCY",
    "SCHEMA_REFERENCE_ONLY_CHUNK",
}

BLOCKED_QUERY_CLASSES = {
    "STATUS_AUDIT_ONLY",
    "GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT",
    "OUT_OF_SCOPE_SKILL_CANDIDATE",
    "GOVERNANCE_ONLY",
    "UNKNOWN_OR_INVALID",
}

OUT_OF_SCOPE_SKILL_FAMILIES = {
    "assessment_pattern_corpus",
    "writing_template_corpus",
    "parent_functional_sentence_corpus",
    "story_dialogue_corpus",
}

CONTROL_PLANE_FAMILIES = {"governance", "roadmap"}


@dataclass(frozen=True)
class QueryIssue:
    code: str
    severity: str
    source_id: str | None
    message: str
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "source_id": self.source_id,
            "message": self.message,
            "blocking": self.blocking,
        }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return loaded


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ValueError("Manifest must contain a records list")
    return manifest


def classify_record(record: dict[str, Any]) -> str:
    source_id = str(record.get("source_id", ""))
    source_family = str(record.get("source_family", ""))
    authority_role = str(record.get("authority_role", ""))

    if source_id == "RAZ_READING_CORPUS_A_T_CANDIDATE" and authority_role == "reading_corpus_candidate":
        return "PRIMARY_READING_CANDIDATE_INPUT"
    if source_id == "RAZ_WORDLIST_A_T_EVIDENCE" and authority_role == "evidence_only":
        return "SUPPORTING_READING_EXPOSURE_EVIDENCE"
    if source_id == "EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE" and authority_role == "reference_only":
        return "SCHEMA_REFERENCE_ONLY_GRAMMAR"
    if source_id == "EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE" and authority_role == "reference_only":
        return "SCHEMA_REFERENCE_ONLY_VOCABULARY"
    if source_id == "NGSL_SOURCE_FREQUENCY_PROFILE" and authority_role == "reference_only":
        return "SCHEMA_REFERENCE_ONLY_FREQUENCY"
    if source_id == "CHUNK_SAFE_LAYER_REFERENCE" and authority_role == "reference_only":
        return "SCHEMA_REFERENCE_ONLY_CHUNK"
    if source_family == "status_artifact":
        return "STATUS_AUDIT_ONLY"
    if source_family == "generated_content_candidate":
        return "GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT"
    if source_family in OUT_OF_SCOPE_SKILL_FAMILIES:
        return "OUT_OF_SCOPE_SKILL_CANDIDATE"
    if source_family in CONTROL_PLANE_FAMILIES:
        return "GOVERNANCE_ONLY"
    return "UNKNOWN_OR_INVALID"


def deterministic_sort_key(record: dict[str, Any]) -> tuple[int, str, str, str]:
    query_class = record.get("query_class", "UNKNOWN_OR_INVALID")
    return (
        QUERY_CLASS_PRIORITY.get(str(query_class), QUERY_CLASS_PRIORITY["UNKNOWN_OR_INVALID"]),
        str(record.get("source_family", "")),
        str(record.get("source_id", "")),
        str(record.get("path", "")),
    )


def build_query_record(record: dict[str, Any], query_class: str) -> dict[str, Any]:
    risk_flags = list(record.get("risk_flags") or [])
    allowed_use = list(record.get("allowed_use") or [])
    blocked_use = list(record.get("blocked_use") or [])

    return {
        "source_id": record.get("source_id"),
        "source_family": record.get("source_family"),
        "authority_role": record.get("authority_role"),
        "query_class": query_class,
        "path": record.get("path"),
        "format": record.get("format"),
        "exists": bool(record.get("exists")),
        "license_status": record.get("license_status"),
        "review_status": record.get("review_status"),
        "allowed_use_snapshot": allowed_use,
        "blocked_use_snapshot": blocked_use,
        "promotion_rule": record.get("promotion_rule"),
        "risk_flags": risk_flags,
        "source_trace_required": "source_trace_required" in risk_flags,
        "payload_access_allowed": False,
        "learner_facing_allowed": False,
        "authority_upgrade_allowed": False,
        "query_notes": list(record.get("notes") or []),
    }


def with_candidate_trace_seed(record: dict[str, Any]) -> dict[str, Any]:
    seeded = dict(record)
    seeded.update(
        {
            "candidate_trace_seed_id": f"trace_seed:{record['source_id']}",
            "source_path_ref": record.get("path"),
            "source_unit_ref_policy": "locator_only_until_payload_policy",
            "source_payload_copied": False,
            "source_policy_snapshot": {
                "allowed_use_snapshot": record.get("allowed_use_snapshot", []),
                "blocked_use_snapshot": record.get("blocked_use_snapshot", []),
                "promotion_rule": record.get("promotion_rule"),
                "risk_flags": record.get("risk_flags", []),
                "payload_access_allowed": False,
                "learner_facing_allowed": False,
                "authority_upgrade_allowed": False,
            },
            "constraint_ref_policy": "reference_only_no_authority_upgrade",
        }
    )
    return seeded


def build_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_record in manifest.get("records", []):
        if not isinstance(raw_record, dict):
            continue
        query_class = classify_record(raw_record)
        records.append(build_query_record(raw_record, query_class))
    return sorted(records, key=deterministic_sort_key)


def select_records(records: list[dict[str, Any]], query_mode: str) -> list[dict[str, Any]]:
    if query_mode == "eligible_reading_sources":
        return [record for record in records if record["query_class"] in ELIGIBLE_QUERY_CLASSES]
    if query_mode == "primary_reading_candidates":
        return [record for record in records if record["query_class"] == "PRIMARY_READING_CANDIDATE_INPUT"]
    if query_mode == "supporting_evidence_sources":
        return [record for record in records if record["query_class"] == "SUPPORTING_READING_EXPOSURE_EVIDENCE"]
    if query_mode == "reference_constraint_sources":
        return [record for record in records if record["query_class"] in REFERENCE_QUERY_CLASSES]
    if query_mode == "blocked_sources":
        return [record for record in records if record["query_class"] in BLOCKED_QUERY_CLASSES]
    if query_mode == "source_policy_snapshot":
        return [record for record in records if record["query_class"] in ELIGIBLE_QUERY_CLASSES]
    if query_mode == "candidate_trace_seed":
        return [with_candidate_trace_seed(record) for record in records if record["query_class"] in ELIGIBLE_QUERY_CLASSES]
    return []


def build_warnings(records: list[dict[str, Any]]) -> list[QueryIssue]:
    warnings: list[QueryIssue] = []
    reference_classes_present = {record["query_class"] for record in records if record["query_class"] in REFERENCE_QUERY_CLASSES}
    for query_class in sorted(REFERENCE_QUERY_CLASSES - reference_classes_present):
        warnings.append(
            QueryIssue(
                code="READING_V1_QUERY_REFERENCE_SOURCE_MISSING",
                severity="medium",
                source_id=None,
                message=f"Optional reference class missing: {query_class}",
                blocking=False,
            )
        )

    for record in records:
        source_id = str(record.get("source_id"))
        if not record.get("exists", False):
            warnings.append(
                QueryIssue(
                    code="READING_V1_QUERY_SOURCE_EXISTS_FALSE",
                    severity="medium",
                    source_id=source_id,
                    message="Source is registered but not locally available.",
                    blocking=False,
                )
            )
        if record.get("license_status") in {"restricted_reference_only", "not_redistributable", "license_unknown"}:
            warnings.append(
                QueryIssue(
                    code="READING_V1_QUERY_LICENSE_REVIEW_NEEDED",
                    severity="medium",
                    source_id=source_id,
                    message="Source license status requires continued review.",
                    blocking=False,
                )
            )
        if record.get("review_status") not in {"final_reviewed", "schema_reviewed"}:
            warnings.append(
                QueryIssue(
                    code="READING_V1_QUERY_REVIEW_STATUS_NOT_FINAL",
                    severity="medium",
                    source_id=source_id,
                    message="Source review status is not final.",
                    blocking=False,
                )
            )
    return warnings


def build_issues(records: list[dict[str, Any]], selected: list[dict[str, Any]], query_mode: str) -> list[QueryIssue]:
    issues: list[QueryIssue] = []
    if query_mode not in QUERY_MODES:
        return [
            QueryIssue(
                code="READING_V1_QUERY_UNKNOWN_MODE",
                severity="high",
                source_id=None,
                message=f"Unknown query mode: {query_mode}",
                blocking=True,
            )
        ]

    primary = [record for record in records if record["query_class"] == "PRIMARY_READING_CANDIDATE_INPUT"]
    if not primary:
        issues.append(
            QueryIssue(
                code="READING_V1_QUERY_NO_PRIMARY_SOURCE",
                severity="high",
                source_id=None,
                message="No primary Reading candidate source was found.",
                blocking=True,
            )
        )

    for record in selected:
        source_id = str(record.get("source_id"))
        if record.get("payload_access_allowed") is not False:
            issues.append(QueryIssue("READING_V1_QUERY_PAYLOAD_ACCESS_ALLOWED", "high", source_id, "Payload access is not allowed.", True))
        if record.get("learner_facing_allowed") is not False:
            issues.append(QueryIssue("READING_V1_QUERY_LEARNER_FACING_ALLOWED", "high", source_id, "Learner-facing output is not allowed.", True))
        if record.get("authority_upgrade_allowed") is not False:
            issues.append(QueryIssue("READING_V1_QUERY_AUTHORITY_UPGRADE_ALLOWED", "high", source_id, "Authority upgrade is not allowed.", True))

        allowed_use = set(record.get("allowed_use_snapshot") or [])
        blocked_use = set(record.get("blocked_use_snapshot") or [])
        if not allowed_use or allowed_use & blocked_use:
            issues.append(QueryIssue("READING_V1_QUERY_SCHEMA_DRIFT", "high", source_id, "Allowed/blocked use snapshot is invalid.", True))

        if query_mode != "blocked_sources" and record.get("query_class") in BLOCKED_QUERY_CLASSES:
            issues.append(QueryIssue("READING_V1_QUERY_INELIGIBLE_SOURCE_INCLUDED", "high", source_id, "Ineligible source appeared in eligible query output.", True))

        if record.get("query_class") == "STATUS_AUDIT_ONLY" and query_mode != "blocked_sources":
            issues.append(QueryIssue("READING_V1_QUERY_STATUS_AS_READING_SOURCE", "high", source_id, "Status artifact cannot be a Reading source.", True))
        if record.get("query_class") == "GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT" and query_mode != "blocked_sources":
            issues.append(QueryIssue("READING_V1_QUERY_GENERATED_AS_AUTHORITY", "high", source_id, "Generated candidates cannot be source authority.", True))
        if record.get("source_id") == "RAZ_WORDLIST_A_T_EVIDENCE" and record.get("authority_role") != "evidence_only":
            issues.append(QueryIssue("READING_V1_QUERY_RAZ_WORDLIST_AS_AUTHORITY", "high", source_id, "RAZ wordlist must remain evidence-only.", True))
    return issues


def build_summary(records: list[dict[str, Any]], selected: list[dict[str, Any]], blocked_records: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts: dict[str, int] = {}
    for record in records:
        query_class = str(record.get("query_class", "UNKNOWN_OR_INVALID"))
        class_counts[query_class] = class_counts.get(query_class, 0) + 1
    return {
        "manifest_record_count": len(records),
        "selected_record_count": len(selected),
        "blocked_record_count": len(blocked_records),
        "query_class_counts": dict(sorted(class_counts.items())),
        "metadata_only": True,
        "payload_access_allowed": False,
        "learner_facing_allowed": False,
        "authority_upgrade_allowed": False,
    }


def build_report(manifest: dict[str, Any], manifest_path: Path, query_mode: str) -> dict[str, Any]:
    records = build_records(manifest)
    selected = select_records(records, query_mode)
    blocked_records = [record for record in records if record["query_class"] in BLOCKED_QUERY_CLASSES]
    issues = build_issues(records, selected, query_mode)
    warnings = [] if issues else build_warnings(selected)

    blocking_count = sum(1 for issue in issues if issue.blocking)
    if blocking_count:
        status = FAIL
    elif warnings:
        status = PASS_WITH_WARNINGS
    else:
        status = PASS

    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "query_helper_id": QUERY_HELPER_ID,
        "query_helper_version": QUERY_HELPER_VERSION,
        "query_id": f"{QUERY_HELPER_ID}:{query_mode}",
        "query_mode": query_mode,
        "input_manifest_path": str(manifest_path),
        "status": status,
        "records": selected,
        "summary": build_summary(records, selected, blocked_records),
        "issues": [issue.to_dict() for issue in issues],
        "warnings": [warning.to_dict() for warning in warnings],
        "blocked_records": blocked_records,
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def build_error_report(manifest_path: Path, query_mode: str, code: str, message: str) -> dict[str, Any]:
    issue = QueryIssue(code=code, severity="high", source_id=None, message=message, blocking=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "query_helper_id": QUERY_HELPER_ID,
        "query_helper_version": QUERY_HELPER_VERSION,
        "query_id": f"{QUERY_HELPER_ID}:{query_mode}",
        "query_mode": query_mode,
        "input_manifest_path": str(manifest_path),
        "status": FAIL,
        "records": [],
        "summary": {
            "manifest_record_count": 0,
            "selected_record_count": 0,
            "blocked_record_count": 0,
            "metadata_only": True,
            "payload_access_allowed": False,
            "learner_facing_allowed": False,
            "authority_upgrade_allowed": False,
        },
        "issues": [issue.to_dict()],
        "warnings": [],
        "blocked_records": [],
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def write_report(report: dict[str, Any], output_path: Path | None) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if output_path is None:
        print(text)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query E4S Reading V1 metadata sources.")
    parser.add_argument("--manifest-path", default="ulga/graph/e4s_source_manifest.json")
    parser.add_argument("--query-mode", required=True)
    parser.add_argument("--output-report", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest_path)
    output_path = Path(args.output_report) if args.output_report else None

    if args.query_mode not in QUERY_MODES:
        report = build_error_report(
            manifest_path,
            args.query_mode,
            "READING_V1_QUERY_UNKNOWN_MODE",
            f"Unknown query mode: {args.query_mode}",
        )
        write_report(report, output_path)
        return 1

    try:
        manifest = load_manifest(manifest_path)
        report = build_report(manifest, manifest_path, args.query_mode)
    except FileNotFoundError:
        report = build_error_report(
            manifest_path,
            args.query_mode,
            "READING_V1_QUERY_MANIFEST_MISSING",
            "Manifest path is missing.",
        )
    except (json.JSONDecodeError, ValueError) as exc:
        report = build_error_report(
            manifest_path,
            args.query_mode,
            "READING_V1_QUERY_MANIFEST_INVALID",
            str(exc),
        )

    write_report(report, output_path)
    return 0 if report["status"] in {PASS, PASS_WITH_WARNINGS} else 1


if __name__ == "__main__":
    sys.exit(main())
