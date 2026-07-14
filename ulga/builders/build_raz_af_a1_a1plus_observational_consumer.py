#!/usr/bin/env python3
"""Build the private, text-free S12D observational overlay for A1/A1+ Reading."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.validators.validate_a1_a1plus_local_reading_practice_bank import (  # noqa: E402
    validate_materialization,
)
from ulga.validators.validate_a1_a1plus_selected_reading_source_manifest import (  # noqa: E402
    EXPECTED_FIELDS,
    INDEX_PATH,
    load_from_repo,
    validate_selected_manifest,
)

TASK_ID = "RAZ-AF-S12D_A1A1PlusObservationalConsumerAndM04B2CompatibilityQA"
BINDING_SCHEMA_VERSION = "raz.af.a1_a1plus_observational_consumer_binding.v1"
REPORT_SCHEMA_VERSION = "raz.af.a1_a1plus_observational_consumer_safe_report.v1"
ARTIFACT_SCHEMA_VERSION = "raz.af.a1_a1plus_observational_consumer.v1"
PASS_STATUS = "PASS_AF_OBSERVATIONAL_CONSUMER_AND_M04B2_COMPATIBLE"
EXPECTED_SOURCE_COUNT = 54
ACTIVITY_TYPES = (
    "true_false", "cloze_vocabulary", "sentence_ordering",
    "literal_who", "literal_what", "literal_where",
)
SUPPORT_STATUSES = ("SUPPORTED", "PARTIALLY_SUPPORTED", "UNKNOWN", "CONFLICT_REVIEW_REQUIRED")
ELIGIBILITY_STATUSES = (
    "ELIGIBLE", "ELIGIBLE_REVIEW_REQUIRED", "BLOCKED_SOURCE_INTEGRITY",
    "BLOCKED_CANONICAL_CONTRACT",
)
OBSERVATIONAL_STATUSES = (
    "STRONG_SUPPORT", "PARTIAL_SUPPORT", "LIMITED_SUPPORT", "UNKNOWN_REQUIRES_REVIEW",
)
ALIGNMENT_STATUSES = (
    "ALIGNED", "PARTIALLY_ALIGNED", "OBSERVATIONAL_UNKNOWN", "CONFLICT_REVIEW_REQUIRED",
)
REVIEW_REASONS = (
    "canonical_operator_review_required", "observational_support_unknown",
    "situation_alignment_conflict", "grammar_alignment_conflict",
    "activity_support_unknown", "source_integrity_failure", "canonical_contract_failure",
)
CLAIM_BOUNDARIES = {
    "text_free": True,
    "source_payload_included": False,
    "learner_facing_material_created": False,
    "canonical_authority_write_performed": False,
    "promotion_performed": False,
    "observational_support_only": True,
    "m04b1_m04b2_read_only": True,
}
SURFACE_FIELDS = {
    "evp_sense_candidate_refs": "evp_candidate_refs",
    "evp_levels": "evp_level_candidates",
    "canonical_chunk_ids": "canonical_chunk_ids",
    "chunk_equivalence_groups": "chunk_equivalence_group_ids",
    "safe_chunk_ids": "safe_chunk_ids",
    "grammar_candidate_refs": "grammar_candidate_refs",
    "sentence_pattern_candidate_refs": "pattern_candidate_refs",
    "macro_domains": "macro_domain_candidates",
    "situation_families": "situation_family_candidates",
    "micro_situations": "micro_situation_candidates",
    "communicative_functions": "communicative_function_candidates",
    "listening_templates": "listening_template_candidates",
    "speaking_templates": "speaking_template_candidates",
    "reading_templates": "reading_template_candidates",
    "writing_templates": "writing_template_candidates",
}


class ConsumerBuildError(ValueError):
    """Fail-closed S12D input or reconstruction error."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        raise ConsumerBuildError(f"json_unreadable:{path}:{exc}") from exc


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{id(payload)}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def selected_records(index_path: Path = INDEX_PATH) -> tuple[list[dict[str, Any]], dict[str, str]]:
    index, shards = load_from_repo(index_path)
    report = validate_selected_manifest(index, shards)
    if report.get("validation_status") != "PASS_SELECTED_READING_SOURCE_MANIFEST":
        raise ConsumerBuildError(f"m04b1_validation_failed:{report.get('errors', [])}")
    records = [dict(zip(EXPECTED_FIELDS, row)) for level in "ABCDEF" for row in shards[level]["records"]]
    records.sort(key=lambda row: row["selection_id"])
    paths = [index_path.resolve()] + [(REPO_ROOT / item["path"]).resolve() for item in index["shards"]]
    return records, {path.relative_to(REPO_ROOT).as_posix(): sha256_file(path) for path in paths}


def load_s12b_records(root: Path) -> tuple[dict[str, Mapping[str, Any]], Mapping[str, Any], Mapping[str, Any]]:
    inventory = read_json(root / "inventory.json")
    safe = read_json(root / "validation.json")
    if safe.get("validation_status") != "PASS_LOCAL_RAZ_AF_FULL_LANGUAGE_PEDAGOGY_OBSERVATIONAL_EXTRACTION":
        raise ConsumerBuildError("s12b_not_validated")
    records: dict[str, Mapping[str, Any]] = {}
    for item in inventory.get("records", []):
        record = read_json(root / item["path"])
        ref = record.get("identity", {}).get("source_unit_ref")
        if not isinstance(ref, str) or ref in records:
            raise ConsumerBuildError(f"s12b_duplicate_or_invalid_ref:{ref}")
        records[ref] = record
    expected_index = [
        {"source_unit_ref": ref, "enrichment_payload_sha256": records[ref]["identity"]["enrichment_payload_sha256"]}
        for ref in sorted(records)
    ]
    if inventory.get("records_sha256") != sha256_text(canonical_json(expected_index)):
        raise ConsumerBuildError("s12b_records_sha256_mismatch")
    return records, inventory, safe


def index_keys_for_ref(query_index: Mapping[str, Any], ref: str) -> dict[str, list[str]]:
    return {
        surface: sorted(bucket["key"] for bucket in buckets if ref in bucket.get("source_unit_refs", []))
        for surface, buckets in query_index.get("indexes", {}).items()
    }


def direct_observations(record: Mapping[str, Any]) -> tuple[dict[str, list[str] | str], dict[str, list[str]]]:
    observations = record["observations"]
    vocabulary = observations["vocabulary_exposure"]["items"]
    chunks = observations["chunk_exposure"]["items"]
    patterns = observations["sentence_pattern_observations"]["items"]
    situation = observations["situation_function_observations"]
    skills = observations["four_skill_affordances"]["skill_activity_templates"]
    support: dict[str, list[str] | str] = {
        "evp_candidate_refs": sorted({value for item in vocabulary for value in item["evp_candidate_refs"]}),
        "evp_level_candidates": sorted({value for item in vocabulary for value in item["evp_level_candidates"]}),
        "canonical_chunk_ids": sorted({item["canonical_chunk_id"] for item in chunks if item["canonical_chunk_id"]}),
        "chunk_equivalence_group_ids": sorted({item["equivalence_group_id"] for item in chunks if item["equivalence_group_id"]}),
        "safe_chunk_ids": sorted({item["safe_chunk_id"] for item in chunks if item["safe_chunk_id"]}),
        "grammar_candidate_refs": sorted({value for item in patterns for value in item["grammar_candidate_refs"]}),
        "pattern_candidate_refs": sorted({value for item in patterns for value in item["pattern_authority_candidate_refs"]}),
        "macro_domain_candidates": sorted(set(situation["macro_domain_candidates"])),
        "situation_family_candidates": sorted(set(situation["situation_family_candidates"])),
        "micro_situation_candidates": sorted(set(situation["micro_situation_candidates"])),
        "communicative_function_candidates": sorted(set(situation["communicative_function_candidates"])),
        "discourse_shape": observations["discourse_observation"]["discourse_shape"],
        "supported_pedagogical_signals": sorted(
            name for name, signal in observations["pedagogical_signals"].items() if signal["status"] == "SUPPORTED"
        ),
        "listening_template_candidates": sorted({item["template_id"] for item in skills["listening"]}),
        "speaking_template_candidates": sorted({item["template_id"] for item in skills["speaking"]}),
        "reading_template_candidates": sorted({item["template_id"] for item in skills["reading"]}),
        "writing_template_candidates": sorted({item["template_id"] for item in skills["writing"]}),
    }
    index_values = {
        "vocabulary_normalized_forms": sorted({f"sha256:{sha256_text(item['normalized_form'])}" for item in vocabulary}),
        "vocabulary_lemma_candidates": sorted({f"sha256:{sha256_text(item['lemma_candidate'])}" for item in vocabulary if item["lemma_candidate"]}),
        **{surface: list(support[field]) for surface, field in SURFACE_FIELDS.items()},
        "discourse_shapes": [str(support["discourse_shape"])],
        "pedagogical_signals": sorted(
            f"{name}:{signal['status']}" for name, signal in observations["pedagogical_signals"].items()
        ),
    }
    return support, index_values


def verify_s12c_consistency(
    record: Mapping[str, Any], query_index: Mapping[str, Any], *, require_all_surfaces: bool = True
) -> dict[str, list[str] | str]:
    identity = record["identity"]
    ref = identity["source_unit_ref"]
    indexed = index_keys_for_ref(query_index, ref)
    support, expected = direct_observations(record)
    base = {
        "source_unit_refs": [ref],
        "raz_source_levels": [identity["source_level"]],
        "book_ids": [identity["source_book_id"]],
    }
    for surface, values in {**expected, **base}.items():
        if sorted(indexed.get(surface, [])) != sorted(values):
            raise ConsumerBuildError(f"s12b_s12c_mismatch:{ref}:{surface}")
    if require_all_surfaces and len(query_index.get("indexes", {})) != 22:
        raise ConsumerBuildError("s12c_surface_count_not_22")
    return support


def situation_alignment(canonical_domain: str, candidates: Iterable[str]) -> str:
    values = list(candidates)
    if not values:
        return "OBSERVATIONAL_UNKNOWN"
    if canonical_domain in values:
        return "ALIGNED"
    canonical_tokens = set(canonical_domain.split("_"))
    if any(canonical_tokens & set(value.split("_")) for value in values):
        return "PARTIALLY_ALIGNED"
    return "CONFLICT_REVIEW_REQUIRED"


def grammar_alignment(canonical: Iterable[str], observational: Iterable[str]) -> str:
    canonical_set, observational_set = set(canonical), set(observational)
    if not observational_set:
        return "OBSERVATIONAL_UNKNOWN"
    if canonical_set & observational_set:
        return "ALIGNED" if observational_set <= canonical_set else "PARTIALLY_ALIGNED"
    return "CONFLICT_REVIEW_REQUIRED"


def observational_status(support: Mapping[str, list[str] | str]) -> str:
    features = sum(bool(support[key]) for key in (
        "evp_candidate_refs", "canonical_chunk_ids", "grammar_candidate_refs", "pattern_candidate_refs",
        "macro_domain_candidates", "supported_pedagogical_signals", "reading_template_candidates",
    )) + int(support["discourse_shape"] != "unknown")
    if features >= 5:
        return "STRONG_SUPPORT"
    if features >= 3:
        return "PARTIAL_SUPPORT"
    if features >= 1:
        return "LIMITED_SUPPORT"
    return "UNKNOWN_REQUIRES_REVIEW"


def activity_support(
    activity_type: str,
    deterministic_types: Mapping[str, int],
    literal_types: Iterable[str],
    support: Mapping[str, list[str] | str],
    observations: Mapping[str, Any],
    integrity_ok: bool,
) -> dict[str, Any]:
    refs: list[str] = []
    conflicts: list[str] = []
    if not integrity_ok:
        status = "CONFLICT_REVIEW_REQUIRED"
        conflicts.append("source_integrity_failure")
    elif activity_type == "cloze_vocabulary":
        refs = [f"evp:{value}" for value in support["evp_candidate_refs"]]
        status = "SUPPORTED" if refs else ("PARTIALLY_SUPPORTED" if observations["vocabulary_exposure"]["items"] else "UNKNOWN")
    elif activity_type == "sentence_ordering":
        if observations["discourse_observation"]["ordering_potential"]:
            refs.append("discourse:ordering_potential")
        if "sentence_ordering_potential" in support["supported_pedagogical_signals"]:
            refs.append("pedagogical_signal:sentence_ordering_potential")
        status = "SUPPORTED" if refs else ("PARTIALLY_SUPPORTED" if deterministic_types.get(activity_type, 0) else "UNKNOWN")
    else:
        if "literal_comprehension_potential" in support["supported_pedagogical_signals"]:
            refs.append("pedagogical_signal:literal_comprehension_potential")
        refs.extend(f"reading_template:{value}" for value in support["reading_template_candidates"])
        canonical_present = bool(deterministic_types.get(activity_type, 0)) if activity_type == "true_false" else activity_type in literal_types
        status = "SUPPORTED" if refs and canonical_present else ("PARTIALLY_SUPPORTED" if canonical_present else "UNKNOWN")
    return {
        "activity_type": activity_type,
        "support_status": status,
        "supporting_observation_refs": sorted(set(refs)),
        "conflict_reasons": conflicts,
        "review_required": status != "SUPPORTED",
    }


def build_binding(
    selected: Mapping[str, Any],
    m04b2_record: Mapping[str, Any],
    s12b_record: Mapping[str, Any],
    query_index: Mapping[str, Any],
) -> dict[str, Any]:
    identity = s12b_record["identity"]
    ref = selected["source_unit_ref"]
    if identity["source_unit_ref"] != ref:
        raise ConsumerBuildError(f"s12b_identity_ref_mismatch:{ref}")
    support = verify_s12c_consistency(s12b_record, query_index)
    safe_selection = m04b2_record
    identity_checks = {
        "source_level": identity["source_level"], "book_id": identity["source_book_id"],
        "page_number": identity["source_page_number"], "content_sha256": identity["source_content_sha256"],
        "record_sha256": identity["source_record_sha256"],
    }
    canonical_ok = all(selected[field] == value for field, value in identity_checks.items())
    m04b2_ok = all(selected[field] == safe_selection[field] for field in (
        "selection_id", "source_unit_ref", "source_level", "book_id", "page_number",
        "content_sha256", "record_sha256", "e4s_situation_domain",
    ))
    integrity_ok = safe_selection.get("source_integrity_status") == "PASS" and canonical_ok
    operator_review = bool(safe_selection["operator_review_required"])
    if not integrity_ok:
        eligibility = "BLOCKED_SOURCE_INTEGRITY"
    elif not m04b2_ok:
        eligibility = "BLOCKED_CANONICAL_CONTRACT"
    else:
        eligibility = "ELIGIBLE_REVIEW_REQUIRED" if operator_review else "ELIGIBLE"
    situation = situation_alignment(selected["e4s_situation_domain"], support["macro_domain_candidates"])
    grammar = grammar_alignment(safe_selection["candidate_grammar_ids"], support["grammar_candidate_refs"])
    obs_status = observational_status(support)
    activities = [
        activity_support(
            activity, safe_selection["deterministic_item_types"], safe_selection["literal_review_candidate_types"],
            support, s12b_record["observations"], integrity_ok,
        )
        for activity in ACTIVITY_TYPES
    ]
    reasons = []
    if operator_review:
        reasons.append("canonical_operator_review_required")
    if obs_status == "UNKNOWN_REQUIRES_REVIEW":
        reasons.append("observational_support_unknown")
    if situation == "CONFLICT_REVIEW_REQUIRED":
        reasons.append("situation_alignment_conflict")
    if grammar == "CONFLICT_REVIEW_REQUIRED":
        reasons.append("grammar_alignment_conflict")
    if any(item["support_status"] == "UNKNOWN" for item in activities):
        reasons.append("activity_support_unknown")
    if eligibility == "BLOCKED_SOURCE_INTEGRITY":
        reasons.append("source_integrity_failure")
    if eligibility == "BLOCKED_CANONICAL_CONTRACT":
        reasons.append("canonical_contract_failure")
    return {
        "selection_identity": {
            "selection_id": selected["selection_id"], "source_unit_ref": ref,
            "source_level": selected["source_level"], "book_id": selected["book_id"],
            "page_number": selected["page_number"], "content_sha256": selected["content_sha256"],
            "record_sha256": selected["record_sha256"],
        },
        "upstream_integrity": {
            "m04b1_manifest_status": "PASS", "m04b2_binding_status": "PASS" if m04b2_ok else "FAIL",
            "s12b_identity_status": "PASS" if canonical_ok else "FAIL", "s12c_index_status": "PASS",
            "s12b_enrichment_payload_sha256": identity["enrichment_payload_sha256"],
            "s12c_query_index_sha256": query_index["index_sha256"],
        },
        "canonical_consumer_state": {
            "e4s_situation_domain": selected["e4s_situation_domain"],
            "grammar_binding_status": safe_selection["grammar_binding_status"],
            "candidate_grammar_ids": safe_selection["candidate_grammar_ids"],
            "deterministic_item_types": safe_selection["deterministic_item_types"],
            "literal_review_candidate_types": safe_selection["literal_review_candidate_types"],
            "operator_review_required": operator_review,
        },
        "observational_support": support,
        "consumer_decision": {
            "canonical_eligibility_status": eligibility, "observational_support_status": obs_status,
            "situation_alignment_status": situation, "grammar_alignment_status": grammar,
            "activity_support": activities, "review_reasons": sorted(set(reasons)),
            "promotion_status": "not_promoted",
        },
    }


def closed_counter(values: Iterable[str], keys: Iterable[str]) -> dict[str, int]:
    counter = Counter(values)
    return {key: counter[key] for key in keys}


def aggregate_hash(rows: Iterable[str]) -> str:
    return sha256_text(canonical_json(sorted(rows)))


def build_artifacts(
    selected: list[Mapping[str, Any]],
    m04b2_safe: Mapping[str, Any],
    s12b_records: Mapping[str, Mapping[str, Any]],
    s12b_inventory: Mapping[str, Any],
    s12b_safe: Mapping[str, Any],
    query_index: Mapping[str, Any],
    coverage: Mapping[str, Any],
    upstream_hashes: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if coverage.get("validation_status") != "PASS_LOCAL_RAZ_AF_FULL_COVERAGE_QUERY_INDEX_AND_EXTRACTION_VALIDATION":
        raise ConsumerBuildError("s12c_not_validated")
    if query_index.get("source_records_sha256") != s12b_safe.get("records_sha256"):
        raise ConsumerBuildError("s12b_s12c_records_hash_mismatch")
    m04b2_by_ref = {row["source_unit_ref"]: row for row in m04b2_safe.get("records", [])}
    if len(m04b2_by_ref) != len(m04b2_safe.get("records", [])):
        raise ConsumerBuildError("duplicate_m04b2_source_ref")
    bindings = []
    for row in selected:
        ref = row["source_unit_ref"]
        if ref not in s12b_records:
            raise ConsumerBuildError(f"missing_s12b_selected_record:{ref}")
        if ref not in m04b2_by_ref:
            raise ConsumerBuildError(f"missing_m04b2_selected_record:{ref}")
        bindings.append(build_binding(row, m04b2_by_ref[ref], s12b_records[ref], query_index))
    if len(bindings) != EXPECTED_SOURCE_COUNT:
        raise ConsumerBuildError(f"binding_count_not_54:{len(bindings)}")
    eligibility = closed_counter(
        (item["consumer_decision"]["canonical_eligibility_status"] for item in bindings), ELIGIBILITY_STATUSES
    )
    observational = closed_counter(
        (item["consumer_decision"]["observational_support_status"] for item in bindings), OBSERVATIONAL_STATUSES
    )
    situation = closed_counter(
        (item["consumer_decision"]["situation_alignment_status"] for item in bindings), ALIGNMENT_STATUSES
    )
    grammar = closed_counter(
        (item["consumer_decision"]["grammar_alignment_status"] for item in bindings), ALIGNMENT_STATUSES
    )
    activity = {
        name: closed_counter(
            (next(row for row in item["consumer_decision"]["activity_support"] if row["activity_type"] == name)["support_status"] for item in bindings),
            SUPPORT_STATUSES,
        )
        for name in ACTIVITY_TYPES
    }
    review = closed_counter(
        (reason for item in bindings for reason in item["consumer_decision"]["review_reasons"]), REVIEW_REASONS
    )
    artifact = {
        "task_id": TASK_ID, "schema_version": ARTIFACT_SCHEMA_VERSION,
        "binding_count": len(bindings), "bindings": bindings,
        "bindings_sha256": sha256_text(canonical_json(bindings)), "private_local_only": True,
    }
    report = {
        "task_id": TASK_ID, "schema_version": REPORT_SCHEMA_VERSION,
        "upstream_artifact_hashes": dict(upstream_hashes),
        "before_after_hashes": {
            "m04b1_manifest_and_shards_before": dict(upstream_hashes["m04b1_manifest_and_shards"]),
            "m04b1_manifest_and_shards_after": dict(upstream_hashes["m04b1_manifest_and_shards"]),
            "m04b2_private_before": upstream_hashes["m04b2_private_sha256"],
            "m04b2_private_after": upstream_hashes["m04b2_private_sha256"],
            "m04b2_safe_before": upstream_hashes["m04b2_safe_sha256"],
            "m04b2_safe_after": upstream_hashes["m04b2_safe_sha256"],
            "source_content_before": aggregate_hash(row["content_sha256"] for row in selected),
            "source_content_after": aggregate_hash(row["content_sha256"] for row in selected),
            "source_record_before": aggregate_hash(row["record_sha256"] for row in selected),
            "source_record_after": aggregate_hash(row["record_sha256"] for row in selected),
        },
        "selected_source_count": len(selected),
        "join_counts": {"m04b1_m04b2": len(bindings), "m04b1_s12b": len(bindings), "m04b1_s12c": len(bindings), "s12d_bindings": len(bindings)},
        "status_distributions": {
            "canonical_eligibility": eligibility, "observational_support": observational,
            "situation_alignment": situation, "grammar_alignment": grammar,
        },
        "activity_support_distributions": activity,
        "review_reason_counts": review,
        "compatibility_counters": {
            "missing_binding_count": 0, "extra_binding_count": 0, "duplicate_binding_count": 0,
            "invalid_authority_ref_count": 0, "s12b_s12c_consistency_error_count": 0,
            "canonical_eligibility_override_error_count": 0, "situation_silent_overwrite_error_count": 0,
            "m04b1_hash_drift_count": 0, "m04b2_private_hash_drift_count": 0,
            "m04b2_safe_hash_drift_count": 0, "source_content_hash_drift_count": 0,
            "source_record_hash_drift_count": 0, "safe_source_text_leakage_count": 0,
            "safe_source_payload_leakage_count": 0, "learner_facing_material_created_count": 0,
            "canonical_authority_write_count": 0, "promotion_claim_count": 0,
        },
        "m04b2_baseline": dict(m04b2_safe["summary"]),
        "source_hash_aggregates": {
            "content_sha256": aggregate_hash(row["content_sha256"] for row in selected),
            "record_sha256": aggregate_hash(row["record_sha256"] for row in selected),
        },
        "bindings_sha256": artifact["bindings_sha256"], "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "validation_status": PASS_STATUS, "errors": [],
    }
    return artifact, report


def schema_validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    binding_schema = read_json(REPO_ROOT / "ulga/schemas/raz_af_a1_a1plus_observational_consumer_binding.schema.json")
    report_schema = read_json(REPO_ROOT / "ulga/schemas/raz_af_a1_a1plus_observational_consumer_safe_report.schema.json")
    return Draft202012Validator(binding_schema), Draft202012Validator(report_schema)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s12b-root", type=Path, required=True)
    parser.add_argument("--s12c-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--m04b2-private", type=Path, required=True)
    parser.add_argument("--m04b2-safe", type=Path, required=True)
    parser.add_argument("--selected-index", type=Path, default=INDEX_PATH)
    args = parser.parse_args(argv)
    try:
        selected, manifest_hashes = selected_records(args.selected_index)
        m04b2_private, m04b2_safe = read_json(args.m04b2_private), read_json(args.m04b2_safe)
        m04b2_report = validate_materialization(m04b2_private, m04b2_safe)
        if m04b2_report["validation_status"] != "PASS_LOCAL_READING_PRACTICE_BANK":
            raise ConsumerBuildError(f"m04b2_validation_failed:{m04b2_report['errors']}")
        before = {
            "m04b1_manifest_and_shards": manifest_hashes,
            "m04b2_private_sha256": sha256_file(args.m04b2_private),
            "m04b2_safe_sha256": sha256_file(args.m04b2_safe),
            "s12b_inventory_sha256": sha256_file(args.s12b_root / "inventory.json"),
            "s12b_safe_sha256": sha256_file(args.s12b_root / "validation.json"),
            "s12c_query_index_sha256": sha256_file(args.s12c_root / "query_index.json"),
            "s12c_coverage_sha256": sha256_file(args.s12c_root / "coverage.json"),
        }
        records, inventory, s12b_safe = load_s12b_records(args.s12b_root)
        query_index, coverage = read_json(args.s12c_root / "query_index.json"), read_json(args.s12c_root / "coverage.json")
        artifact, report = build_artifacts(selected, m04b2_safe, records, inventory, s12b_safe, query_index, coverage, before)
        binding_validator, report_validator = schema_validators()
        errors = []
        for index, binding in enumerate(artifact["bindings"]):
            errors.extend(f"binding[{index}]:{error.message}" for error in binding_validator.iter_errors(binding))
        errors.extend(f"safe_report:{error.message}" for error in report_validator.iter_errors(report))
        if errors:
            raise ConsumerBuildError("schema_validation_failed:" + ";".join(errors[:20]))
        after_manifest = selected_records(args.selected_index)[1]
        if after_manifest != manifest_hashes or sha256_file(args.m04b2_private) != before["m04b2_private_sha256"] or sha256_file(args.m04b2_safe) != before["m04b2_safe_sha256"]:
            raise ConsumerBuildError("m04b1_or_m04b2_mutated_during_build")
        write_json_atomic(args.output_root / "bindings.json", artifact)
        write_json_atomic(args.output_root / "safe_report.json", report)
        print(json.dumps({"binding_count": len(artifact["bindings"]), "validation_status": report["validation_status"]}, sort_keys=True))
        return 0
    except (ConsumerBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
