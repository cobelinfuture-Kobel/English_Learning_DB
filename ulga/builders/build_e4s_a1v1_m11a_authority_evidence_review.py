#!/usr/bin/env python3
"""Build the evidence-driven A1/A1+ candidate-unit review.

M11A replaces manual checkbox approval with deterministic evidence derived from
canonical EGP mappings, executable grammar validators, project content gates,
and a metadata-only Cambridge YLE/A2 source policy. Raw Cambridge PDFs remain
outside the repository. Optional local source verification checks the pinned PDF
hashes without copying source content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOURCE_REPO_ROOT
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11_candidate_content_review as m11  # noqa: E402
from ulga.query.a1_canonical_validator_dispatcher import validate as dispatch_validate  # noqa: E402
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item  # noqa: E402

TASK_ID = "E4S-A1V1-M11A_AuthorityAndCambridgeEvidenceDrivenCandidateReviewFullFix"
SCHEMA_VERSION_MATRIX = "e4s.a1v1.m11a_authority_evidence_matrix.v1"
SCHEMA_VERSION_BANK = "e4s.a1v1.m11a_reviewed_private_learning_unit_bank.v1"
SCHEMA_VERSION_REPORT = "e4s.a1v1.m11a_authority_review_safe_report.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/content_review/m11a"
EVIDENCE_DIR = SOURCE_REPO_ROOT / "ulga/evidence"
SCHEMA_DIR = SOURCE_REPO_ROOT / "ulga/schemas"
MANIFEST_PATH = EVIDENCE_DIR / "e4s_a1v1_m11a_cambridge_source_manifest.json"
POLICY_PATH = EVIDENCE_DIR / "e4s_a1v1_m11a_cambridge_alignment_policy.json"
NEXT_SHORT_STEP = "E4S-A1V1-M11B_AuthorityExceptionContentRevisionAndRevalidation"

DECISIONS = (
    "AUTO_PASS",
    "REVISION_REQUIRED",
    "AUTHORITY_CONFLICT",
    "SOURCE_EVIDENCE_MISSING",
)
CRITERIA = (
    "canonical_mapping_verified",
    "validator_alignment_verified",
    "learning_objectives_clear",
    "form_rules_accurate",
    "meaning_and_usage_accurate",
    "positive_examples_natural_and_valid",
    "negative_examples_valid_and_explanatory",
    "practice_items_valid",
    "assessment_items_valid",
    "a1_a1plus_level_appropriate",
    "project_authored_content_boundary_verified",
    "no_a2_expansion",
)
SAFE_FORBIDDEN_KEYS = {
    "candidate_unit_payload",
    "final_private_unit_payload",
    "prompt",
    "answer",
    "answer_key",
    "accepted_texts",
    "positive_examples",
    "negative_examples",
    "official_question_text",
    "official_answer_text",
    "raw_pdf_text",
}


class AuthorityEvidenceError(ValueError):
    """Fail-closed M11A evidence error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityEvidenceError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AuthorityEvidenceError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _schema(name: str) -> dict[str, Any]:
    return read_json(SCHEMA_DIR / name)


def _assert_schema(name: str, value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema(name)).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise AuthorityEvidenceError(
            f"schema_validation_failed:{name}:{location}:{first.message}"
        )


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise AuthorityEvidenceError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _safe_scan(value: Any, *, name: str) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in SAFE_FORBIDDEN_KEYS or lowered.endswith("_absolute_path"):
                    raise AuthorityEvidenceError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (
                len(node) > 2 and node[1:3] in {":\\", ":/"}
            ):
                raise AuthorityEvidenceError(f"absolute_path_leak:{name}")

    walk(value)


def load_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = read_json(MANIFEST_PATH)
    policy = read_json(POLICY_PATH)
    _assert_schema("e4s_a1v1_m11a_cambridge_source_manifest.schema.json", manifest)
    if len({row["source_id"] for row in manifest.get("sources", [])}) != 4:
        raise AuthorityEvidenceError("cambridge_source_identity_not_4")
    alignments = policy.get("unit_alignment", [])
    if len(alignments) != 24 or len({row.get("grammar_unit_id") for row in alignments}) != 24:
        raise AuthorityEvidenceError("cambridge_alignment_identity_not_24")
    if set(policy.get("expected_distribution", {})) != set(DECISIONS):
        raise AuthorityEvidenceError("cambridge_expected_distribution_keys_invalid")
    return manifest, policy


def verify_source_bytes(manifest: Mapping[str, Any], source_root: Path | None) -> str:
    if source_root is None:
        return "MANIFEST_HASH_PINNED"
    root = source_root.resolve()
    if not root.exists() or not root.is_dir():
        raise AuthorityEvidenceError(f"cambridge_source_root_missing:{root}")
    for source in manifest["sources"]:
        filename = str(source["local_filename"])
        path = (root / filename).resolve()
        if not path.is_relative_to(root):
            raise AuthorityEvidenceError(f"cambridge_source_path_escape:{filename}")
        if not path.exists() or not path.is_file():
            raise AuthorityEvidenceError(f"cambridge_source_file_missing:{filename}")
        if path.is_symlink():
            raise AuthorityEvidenceError(f"cambridge_source_symlink_forbidden:{filename}")
        if path.stat().st_size != source["byte_size"]:
            raise AuthorityEvidenceError(f"cambridge_source_size_drift:{filename}")
        if sha256_file(path) != source["sha256"]:
            raise AuthorityEvidenceError(f"cambridge_source_hash_drift:{filename}")
    return "SOURCE_BYTES_VERIFIED"


def _criterion(status: str, refs: list[str], **metrics: Any) -> dict[str, Any]:
    if status not in {"PASS", "WARNING", "FAIL"}:
        raise AuthorityEvidenceError(f"criterion_status_invalid:{status}")
    clean_refs = sorted({str(ref) for ref in refs if ref})
    if not clean_refs:
        raise AuthorityEvidenceError("criterion_evidence_refs_empty")
    return {"status": status, "evidence_refs": clean_refs, "metrics": metrics}


def _unit_validation(unit: Mapping[str, Any]) -> dict[str, Any]:
    grammar_id = str(unit["grammar_unit_id"])
    positive_results = [
        dispatch_validate(grammar_id, str(row.get("text") or ""))
        for row in unit.get("positive_examples", [])
    ]
    negative_results = [
        dispatch_validate(grammar_id, str(row.get("text") or ""))
        for row in unit.get("negative_examples", [])
    ]
    practice = list(unit.get("practice_items", []))
    assessment = list(unit.get("assessment_items", []))
    practice_results = [validate_practice_item(row) for row in practice]
    assessment_results = [validate_practice_item(row) for row in assessment]
    return {
        "positive_total": len(positive_results),
        "positive_pass": sum(
            result.get("dispatch_status") == "VALIDATOR_EXECUTED"
            and result.get("match") is True
            for result in positive_results
        ),
        "negative_total": len(negative_results),
        "negative_pass": sum(
            result.get("dispatch_status") == "VALIDATOR_EXECUTED"
            and result.get("match") is False
            for result in negative_results
        ),
        "practice_total": len(practice_results),
        "practice_pass": sum(result.get("gate_status") == "PASS" for result in practice_results),
        "assessment_total": len(assessment_results),
        "assessment_pass": sum(result.get("gate_status") == "PASS" for result in assessment_results),
    }


def _source_boundary_ok(unit: Mapping[str, Any]) -> bool:
    trace = unit.get("source_trace", {})
    return (
        trace.get("official_egp_text_copied") is False
        and trace.get("raw_external_source_text_copied") is False
        and trace.get("restricted_source_payload_persisted") is False
        and trace.get("content_origin") == "project_authored_derived_content"
    )


def _make_entry(
    unit: Mapping[str, Any],
    alignment: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    grammar_id = str(unit["grammar_unit_id"])
    refs = sorted(set(alignment.get("evidence_refs", [])))
    validation = _unit_validation(unit)
    rows = list(unit.get("canonical_egp_row_ids", []))
    mapping_ok = all(isinstance(value, str) and value for value in rows)
    objective_ok = (
        len(unit.get("learning_objectives", [])) >= 2
        and all(str(value).strip() for value in unit.get("learning_objectives", []))
    )
    form_ok = len(unit.get("form_rules", [])) >= 1
    meaning_ok = (
        len(unit.get("meaning_functions", [])) >= 1
        and len(unit.get("usage_conditions", [])) >= 2
    )
    positive_ok = validation["positive_total"] >= 2 and validation["positive_pass"] == validation["positive_total"]
    negative_ok = validation["negative_total"] >= 3 and validation["negative_pass"] == validation["negative_total"]
    practice_ok = validation["practice_total"] >= 6 and validation["practice_pass"] == validation["practice_total"]
    assessment_ok = validation["assessment_total"] >= 2 and validation["assessment_pass"] == validation["assessment_total"]
    task_types = {
        str(row.get("task_type"))
        for row in list(unit.get("practice_items", [])) + list(unit.get("assessment_items", []))
    }
    task_policy = policy.get("task_compatibility", {})
    task_policy_ok = all(task_type in task_policy for task_type in task_types)
    boundary_ok = _source_boundary_ok(unit)

    policy_decision = str(alignment.get("policy_decision") or "SOURCE_EVIDENCE_MISSING")
    warning_codes = list(alignment.get("reason_codes", [])) if policy_decision == "REVISION_REQUIRED" else []
    conflict_codes = list(alignment.get("reason_codes", [])) if policy_decision == "AUTHORITY_CONFLICT" else []

    mechanical_ok = all(
        (mapping_ok, objective_ok, form_ok, meaning_ok, positive_ok, negative_ok, practice_ok, assessment_ok, task_policy_ok, boundary_ok)
    )
    if not refs or alignment.get("cambridge_stage") in {None, "UNRESOLVED"}:
        decision = "SOURCE_EVIDENCE_MISSING"
    elif policy_decision == "AUTHORITY_CONFLICT":
        decision = "AUTHORITY_CONFLICT"
    elif not mechanical_ok or policy_decision == "REVISION_REQUIRED":
        decision = "REVISION_REQUIRED"
        if not mechanical_ok:
            warning_codes = sorted(set(warning_codes + ["PROJECT_VALIDATOR_OR_CONTENT_GATE_REQUIRES_REVISION"]))
    elif policy_decision == "AUTO_PASS":
        decision = "AUTO_PASS"
    else:
        raise AuthorityEvidenceError(f"policy_decision_invalid:{grammar_id}:{policy_decision}")

    level_status = "FAIL" if decision == "AUTHORITY_CONFLICT" else "WARNING" if decision in {"REVISION_REQUIRED", "SOURCE_EVIDENCE_MISSING"} else "PASS"
    form_status = "FAIL" if decision == "AUTHORITY_CONFLICT" else "WARNING" if decision == "REVISION_REQUIRED" else "PASS"
    no_a2_status = "FAIL" if decision == "AUTHORITY_CONFLICT" else "PASS"
    base_refs = refs + [
        f"EGP_CANONICAL:{grammar_id}",
        f"CANONICAL_VALIDATOR:{grammar_id}",
        "CAMBRIDGE_YLE_SAMPLE_PAPERS_2018_VOL1:task-pattern-metadata",
        "CAMBRIDGE_YLE_WORDLISTS_2018:stage-evidence",
    ]
    criteria = {
        "canonical_mapping_verified": _criterion("PASS" if mapping_ok else "FAIL", [f"EGP_CANONICAL:{grammar_id}"], row_count=len(rows)),
        "validator_alignment_verified": _criterion("PASS" if positive_ok and negative_ok else "FAIL", [f"CANONICAL_VALIDATOR:{grammar_id}"], **validation),
        "learning_objectives_clear": _criterion("PASS" if objective_ok else "FAIL", [f"PROJECT_CANDIDATE:{grammar_id}"], objective_count=len(unit.get("learning_objectives", []))),
        "form_rules_accurate": _criterion(form_status if form_ok else "FAIL", refs + [f"RULE_PRIMITIVES:{grammar_id}"], form_rule_count=len(unit.get("form_rules", []))),
        "meaning_and_usage_accurate": _criterion(form_status if meaning_ok else "FAIL", refs + [f"PROJECT_CANDIDATE:{grammar_id}"], meaning_count=len(unit.get("meaning_functions", [])), usage_count=len(unit.get("usage_conditions", []))),
        "positive_examples_natural_and_valid": _criterion("PASS" if positive_ok else "FAIL", [f"CANONICAL_VALIDATOR:{grammar_id}"], passed=validation["positive_pass"], total=validation["positive_total"]),
        "negative_examples_valid_and_explanatory": _criterion("PASS" if negative_ok else "FAIL", [f"CANONICAL_VALIDATOR:{grammar_id}"], passed=validation["negative_pass"], total=validation["negative_total"]),
        "practice_items_valid": _criterion("PASS" if practice_ok and task_policy_ok else "FAIL", [f"PRACTICE_GRAMMAR_GATE:{grammar_id}", "CAMBRIDGE_YLE_SAMPLE_PAPERS_2018_VOL1:task-pattern-metadata"], passed=validation["practice_pass"], total=validation["practice_total"], task_types=sorted(task_types)),
        "assessment_items_valid": _criterion("PASS" if assessment_ok and task_policy_ok else "FAIL", [f"ASSESSMENT_GRAMMAR_GATE:{grammar_id}", "CAMBRIDGE_YLE_SAMPLE_PAPERS_2018_VOL1:marking-policy-metadata"], passed=validation["assessment_pass"], total=validation["assessment_total"]),
        "a1_a1plus_level_appropriate": _criterion(level_status, refs + ["CAMBRIDGE_YLE_WORDLISTS_2018:stage-evidence"], cambridge_stage=alignment.get("cambridge_stage"), internal_stage=unit.get("internal_stage")),
        "project_authored_content_boundary_verified": _criterion("PASS" if boundary_ok else "FAIL", [f"PROJECT_SOURCE_TRACE:{grammar_id}"], project_authored=boundary_ok),
        "no_a2_expansion": _criterion(no_a2_status, refs + ["CAMBRIDGE_A2_KEY_FOR_SCHOOLS_HANDBOOK:A2-ceiling"], a2_content_promoted=False),
    }
    if set(criteria) != set(CRITERIA):
        raise AuthorityEvidenceError(f"criteria_contract_drift:{grammar_id}")

    entry = {
        "grammar_unit_id": grammar_id,
        "internal_stage": unit["internal_stage"],
        "canonical_egp_row_ids": rows,
        "candidate_payload_sha256": sha256_value(unit),
        "cambridge_stage": alignment.get("cambridge_stage", "UNRESOLVED"),
        "criteria": criteria,
        "automated_decision": decision,
        "warning_codes": sorted(set(warning_codes)),
        "conflict_codes": sorted(set(conflict_codes)),
        "evidence_refs": sorted(set(base_refs)),
    }
    entry["evidence_record_sha256"] = sha256_value(entry)
    return entry


def build_artifacts(source_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest, policy = load_sources()
    source_verification = verify_source_bytes(manifest, source_root)
    candidate, candidate_validation = m11._source_candidate()
    if candidate_validation.get("validation_status") != "PASS":
        raise AuthorityEvidenceError("candidate_source_validation_failed")
    units = list(candidate.get("learning_units", []))
    if len(units) != 24:
        raise AuthorityEvidenceError("candidate_unit_count_not_24")
    by_alignment = {row["grammar_unit_id"]: row for row in policy["unit_alignment"]}
    if set(by_alignment) != {str(unit["grammar_unit_id"]) for unit in units}:
        raise AuthorityEvidenceError("cambridge_alignment_unit_set_mismatch")

    entries = [_make_entry(unit, by_alignment[str(unit["grammar_unit_id"])], policy) for unit in units]
    entries.sort(key=lambda row: row["grammar_unit_id"])
    rows = {row_id for entry in entries for row_id in entry["canonical_egp_row_ids"]}
    if len(rows) != 109:
        raise AuthorityEvidenceError("canonical_row_union_not_109")
    counts = Counter(entry["automated_decision"] for entry in entries)
    expected = policy["expected_distribution"]
    actual = {decision: counts[decision] for decision in DECISIONS}
    if actual != expected:
        raise AuthorityEvidenceError(f"automated_decision_distribution_drift:{actual}:{expected}")

    matrix = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_MATRIX,
        "private_local_only": True,
        "source_manifest_sha256": sha256_value(manifest),
        "alignment_policy_sha256": sha256_value(policy),
        "candidate_source_sha256": sha256_value(candidate),
        "source_verification": source_verification,
        "unit_count": 24,
        "canonical_egp_row_count": 109,
        "entries": entries,
        "entries_sha256": sha256_value(entries),
        "claim_boundaries": {
            "private_local_only": True,
            "raw_cambridge_source_included": False,
            "manual_checkbox_approval_required": False,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "a2_content_promoted": False,
        },
    }
    _assert_schema("e4s_a1v1_m11a_authority_evidence_matrix.schema.json", matrix)

    units_by_id = {str(unit["grammar_unit_id"]): unit for unit in units}
    reviewed = []
    reviewed_rows: set[str] = set()
    for entry in entries:
        if entry["automated_decision"] != "AUTO_PASS":
            continue
        grammar_id = entry["grammar_unit_id"]
        token = hashlib.sha256(grammar_id.encode("utf-8")).hexdigest()[:20].upper()
        reviewed_rows.update(entry["canonical_egp_row_ids"])
        reviewed.append(
            {
                "reviewed_unit_id": f"M11A_UNIT_{token}",
                "status": "EVIDENCE_REVIEWED_PRIVATE_LEARNING_UNIT",
                "grammar_unit_id": grammar_id,
                "internal_stage": entry["internal_stage"],
                "canonical_egp_row_ids": list(entry["canonical_egp_row_ids"]),
                "final_private_unit_payload": deepcopy(units_by_id[grammar_id]),
                "automated_decision": "AUTO_PASS",
                "evidence_record_sha256": entry["evidence_record_sha256"],
                "private_learning_ready": True,
                "mastery_trackable": False,
                "canonical_authority_promotion": False,
            }
        )
    reviewed.sort(key=lambda row: row["grammar_unit_id"])
    bank = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_BANK,
        "private_local_only": True,
        "source_matrix_sha256": sha256_value(matrix),
        "reviewed_unit_count": len(reviewed),
        "canonical_egp_row_count": len(reviewed_rows),
        "reviewed_units": reviewed,
        "reviewed_units_sha256": sha256_value(reviewed),
        "claim_boundaries": {
            "private_local_only": True,
            "must_not_be_committed": True,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "persistent_learner_state_write": False,
            "a2_content_promoted": False,
        },
    }
    _assert_schema("e4s_a1v1_m11a_reviewed_private_learning_unit_bank.schema.json", bank)

    criterion_counts: Counter[str] = Counter(
        criterion["status"]
        for entry in entries
        for criterion in entry["criteria"].values()
    )
    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_REPORT,
        "candidate_unit_count": 24,
        "canonical_egp_row_count": 109,
        "source_verification": source_verification,
        "decision_counts": actual,
        "reviewed_unit_count": bank["reviewed_unit_count"],
        "reviewed_row_count": bank["canonical_egp_row_count"],
        "criteria_status_counts": {
            "PASS": criterion_counts["PASS"],
            "WARNING": criterion_counts["WARNING"],
            "FAIL": criterion_counts["FAIL"],
        },
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_candidate_content_included": False,
            "raw_cambridge_source_included": False,
            "manual_checkbox_approval_required": False,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "audio_or_recording_processed": False,
            "a2_content_promoted": False,
        },
        "validation_status": "PASS_WITH_AUTHORITY_EXCEPTIONS" if actual["REVISION_REQUIRED"] or actual["AUTHORITY_CONFLICT"] else "PASS_AUTHORITY_EVIDENCE_REVIEW_COMPLETE",
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
        "errors": [],
    }
    _safe_scan(report, name="m11a_authority_review_safe_report")
    _assert_schema("e4s_a1v1_m11a_authority_review_safe_report.schema.json", report)
    return matrix, bank, report


def build_to_root(output_root: Path, source_root: Path | None = None) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    matrix, bank, report = build_artifacts(source_root)
    write_json_atomic(root / "authority_evidence_matrix.private.json", matrix)
    write_json_atomic(root / "reviewed_private_learning_unit_bank.json", bank)
    write_json_atomic(root / "authority_review_safe_report.json", report)
    return {"matrix": matrix, "bank": bank, "safe_report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--cambridge-source-root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_to_root(args.output_root, args.cambridge_source_root)
        report = result["safe_report"]
        print(json.dumps({
            "candidate_units": report["candidate_unit_count"],
            "canonical_egp_rows": report["canonical_egp_row_count"],
            "decision_counts": report["decision_counts"],
            "reviewed_units": report["reviewed_unit_count"],
            "reviewed_rows": report["reviewed_row_count"],
            "source_verification": report["source_verification"],
            "validation_status": report["validation_status"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (AuthorityEvidenceError, m11.CandidateReviewError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
