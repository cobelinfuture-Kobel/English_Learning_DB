#!/usr/bin/env python3
"""Build the E4S Source Manifest.

Scope:
- Deterministic, metadata-only manifest builder for E4S-P0-S2.
- No source payload extraction.
- No Reading question generation.
- No learner-facing output.
- No source promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

EPIC_ID = "E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem"
PHASE_ID = "E4S-P0_SourceAuthorityAndCorpusRoadmap"
TASK_ID = "E4S-P0-S2_SourceManifestBuilder_Implementation"
SCHEMA_VERSION = "E4S_SOURCE_MANIFEST_V1"
CONTRACT_PATH = "docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"
DEFAULT_SUMMARY_PATH = REPO_ROOT / "ulga" / "reports" / "e4s_source_manifest_summary.json"

REQUIRED_FIELDS = (
    "source_id",
    "source_family",
    "source_type",
    "authority_role",
    "path",
    "format",
    "exists",
    "license_status",
    "review_status",
    "allowed_use",
    "blocked_use",
    "promotion_rule",
    "target_phase",
    "target_ulga_stage",
    "risk_flags",
    "notes",
)

SOURCE_RECORDS: list[dict[str, Any]] = [
    {
        "source_id": "GOV_PROJECT_TASK_EXPANSION_CONTROL_POLICY",
        "display_name": "Project Task Expansion Control Policy",
        "source_family": "governance",
        "source_type": "policy_doc",
        "authority_role": "governance_only",
        "path": "docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md",
        "format": "markdown",
        "exists": True,
        "license_status": "owned",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "internal_reference", "schema_design"],
        "blocked_use": ["learner_facing_output", "final_authority_promotion", "automatic_promotion"],
        "promotion_rule": "already_governance_not_content",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "GOVERNANCE_ONLY",
        "risk_flags": [],
        "notes": ["Project-wide scope-control policy; not content authority."],
    },
    {
        "source_id": "ROADMAP_E4S_CORPUS_AND_FOUR_SKILL_SYSTEM",
        "display_name": "E4S Corpus and Four-Skill System Roadmap",
        "source_family": "roadmap",
        "source_type": "roadmap_doc",
        "authority_role": "governance_only",
        "path": "docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md",
        "format": "markdown",
        "exists": True,
        "license_status": "owned",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "internal_reference", "schema_design"],
        "blocked_use": ["learner_facing_output", "final_authority_promotion", "automatic_promotion"],
        "promotion_rule": "already_governance_not_content",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "ROADMAP_ONLY",
        "risk_flags": [],
        "notes": ["Master roadmap for P0-P8 and P0 task order."],
    },
    {
        "source_id": "CONTRACT_E4S_P0_SOURCE_INVENTORY",
        "display_name": "E4S P0 Source Inventory Contract",
        "source_family": "governance",
        "source_type": "design_scan",
        "authority_role": "governance_only",
        "path": "docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md",
        "format": "markdown",
        "exists": True,
        "license_status": "owned",
        "review_status": "schema_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "internal_reference", "schema_design", "validator_design"],
        "blocked_use": ["learner_facing_output", "final_authority_promotion", "automatic_promotion"],
        "promotion_rule": "already_governance_not_content",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "SOURCE_INVENTORY_CONTRACT",
        "risk_flags": [],
        "notes": ["Contract that controls source manifest record fields and safety rules."],
    },
    {
        "source_id": "EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE",
        "display_name": "English Grammar Profile Online",
        "source_family": "grammar_profile",
        "source_type": "source_excel",
        "authority_role": "reference_only",
        "path": "google_drive_reference:English Grammar Profile Online.xlsx",
        "format": "xlsx",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "internal_reference", "schema_design"],
        "blocked_use": ["learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "requires_promotion_task",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "GRAMMAR_PROFILE_REFERENCE",
        "risk_flags": ["source_trace_required", "not_for_public_distribution"],
        "notes": ["Registered as reference metadata only in P0-S2; no payload extraction."],
    },
    {
        "source_id": "EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE",
        "display_name": "English Vocabulary Profile Online",
        "source_family": "vocabulary_profile",
        "source_type": "source_excel",
        "authority_role": "reference_only",
        "path": "google_drive_reference:English Vocabulary Profile Online.xlsx",
        "format": "xlsx",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "internal_reference", "schema_design"],
        "blocked_use": ["learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "requires_promotion_task",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "VOCABULARY_PROFILE_REFERENCE",
        "risk_flags": ["source_trace_required", "not_for_public_distribution"],
        "notes": ["Registered as reference metadata only in P0-S2; no payload extraction."],
    },
    {
        "source_id": "NGSL_SOURCE_FREQUENCY_PROFILE",
        "display_name": "NGSL Frequency Profile",
        "source_family": "frequency_profile",
        "source_type": "source_excel",
        "authority_role": "reference_only",
        "path": "google_drive_reference:NGSL+with+SFI+(31K).xlsx",
        "format": "xlsx",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "internal_reference", "schema_design"],
        "blocked_use": ["learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "requires_promotion_task",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "FREQUENCY_PROFILE_REFERENCE",
        "risk_flags": ["source_trace_required", "not_for_public_distribution"],
        "notes": ["Registered as reference metadata only in P0-S2; no payload extraction."],
    },
    {
        "source_id": "CHUNK_SAFE_LAYER_REFERENCE",
        "display_name": "EVP Derived Safe Chunk Layer",
        "source_family": "chunk_authority",
        "source_type": "source_json",
        "authority_role": "reference_only",
        "path": "google_drive_reference:chunks_generator_safe.json",
        "format": "json",
        "exists": False,
        "license_status": "owned",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "internal_reference", "query_index_design"],
        "blocked_use": ["learner_facing_output", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "requires_promotion_task",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "CHUNK_AUTHORITY_REFERENCE",
        "risk_flags": ["source_trace_required", "candidate_not_authority"],
        "notes": ["Reference to existing chunk safe layer; no content payload copied by this builder."],
    },
    {
        "source_id": "CAMBRIDGE_VOCABULARY_COLLECTION",
        "display_name": "Cambridge Vocabulary Source Collection",
        "source_family": "cambridge_vocabulary",
        "source_type": "source_folder",
        "authority_role": "candidate_only",
        "path": "google_drive_reference:Cambridge vocabulary files",
        "format": "folder",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "schema_design", "manual_review"],
        "blocked_use": ["learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "requires_promotion_task",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "CAMBRIDGE_VOCABULARY_CANDIDATE",
        "risk_flags": ["source_trace_required", "not_for_public_distribution", "requires_manual_review"],
        "notes": ["Collection-level record only; detailed source split belongs to later manifest expansion."],
    },
    {
        "source_id": "RAZ_WORDLIST_A_T_EVIDENCE",
        "display_name": "RAZ A-T WordList Evidence",
        "source_family": "raz_wordlist",
        "source_type": "source_folder",
        "authority_role": "evidence_only",
        "path": "google_drive_reference:RAZ A-T word list",
        "format": "folder",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "source_trace_only", "reading_candidate_selection"],
        "blocked_use": ["direct_vocab_authority", "learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "evidence_only_never_authority",
        "target_phase": "E4S-P1_ReadingV1SourceGroundedPractice",
        "target_ulga_stage": "RAZ_WORDLIST_EVIDENCE",
        "risk_flags": ["source_trace_required", "candidate_not_authority", "not_for_public_distribution"],
        "notes": ["RAZ word list can support exposure evidence but cannot become direct vocabulary authority."],
    },
    {
        "source_id": "RAZ_READING_CORPUS_A_T_CANDIDATE",
        "display_name": "RAZ A-T Reading Corpus Candidate",
        "source_family": "raz_reading_corpus",
        "source_type": "source_folder",
        "authority_role": "reading_corpus_candidate",
        "path": "google_drive_reference:RAZ A-T reading corpus",
        "format": "folder",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "source_trace_only", "query_index_design", "reading_candidate_selection"],
        "blocked_use": ["learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion", "direct_reading_authority"],
        "promotion_rule": "candidate_only_until_review",
        "target_phase": "E4S-P1_ReadingV1SourceGroundedPractice",
        "target_ulga_stage": "RAZ_READING_CORPUS_CANDIDATE",
        "risk_flags": ["source_trace_required", "candidate_not_authority", "not_for_public_distribution"],
        "notes": ["Reading source candidate only; learner-facing packages require later validation."],
    },
    {
        "source_id": "WRITING_TEMPLATE_CORPUS_REFERENCE",
        "display_name": "Writing Template Corpus",
        "source_family": "writing_template_corpus",
        "source_type": "source_folder",
        "authority_role": "template_corpus",
        "path": "google_drive_reference:Writing Framework 1-3",
        "format": "folder",
        "exists": False,
        "license_status": "owned",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "schema_design", "writing_template_candidate"],
        "blocked_use": ["direct_reading_authority", "learner_facing_output", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "template_only_until_derivation_review",
        "target_phase": "E4S-P3_WritingPracticeSystem",
        "target_ulga_stage": "WRITING_TEMPLATE_CORPUS",
        "risk_flags": ["candidate_not_authority", "requires_manual_review"],
        "notes": ["Writing templates are registered but not converted into exercises during P0."],
    },
    {
        "source_id": "PARENT_FUNCTIONAL_SENTENCE_CORPUS_REFERENCE",
        "display_name": "Parent Functional Sentence Corpus",
        "source_family": "parent_functional_sentence_corpus",
        "source_type": "source_folder",
        "authority_role": "functional_sentence_corpus",
        "path": "google_drive_reference:parent functional sentences",
        "format": "folder",
        "exists": False,
        "license_status": "owned",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "schema_design", "dialogue_candidate", "speaking_prompt_candidate"],
        "blocked_use": ["direct_dialogue_authority", "learner_facing_output", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "candidate_only_until_review",
        "target_phase": "E4S-P4_DialogueSpeakingPromptSystem",
        "target_ulga_stage": "PARENT_FUNCTIONAL_SENTENCE_CORPUS",
        "risk_flags": ["candidate_not_authority", "requires_manual_review"],
        "notes": ["Functional sentence source candidate only; no direct dialogue authority."],
    },
    {
        "source_id": "STORY_DIALOGUE_CORPUS_REFERENCE",
        "display_name": "Story Dialogue Corpus",
        "source_family": "story_dialogue_corpus",
        "source_type": "source_folder",
        "authority_role": "dialogue_corpus_candidate",
        "path": "google_drive_reference:story dialogue corpus",
        "format": "folder",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "schema_design", "dialogue_candidate"],
        "blocked_use": ["direct_dialogue_authority", "learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "candidate_only_until_review",
        "target_phase": "E4S-P4_DialogueSpeakingPromptSystem",
        "target_ulga_stage": "STORY_DIALOGUE_CORPUS_CANDIDATE",
        "risk_flags": ["candidate_not_authority", "not_for_public_distribution", "requires_manual_review"],
        "notes": ["Dialogue-like source candidate; not promoted during P0."],
    },
    {
        "source_id": "ASSESSMENT_PATTERN_CORPUS_REFERENCE",
        "display_name": "Assessment Pattern Corpus",
        "source_family": "assessment_pattern_corpus",
        "source_type": "source_folder",
        "authority_role": "assessment_pattern_candidate",
        "path": "google_drive_reference:assessment pattern corpus",
        "format": "folder",
        "exists": False,
        "license_status": "restricted_reference_only",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "assessment_pattern_design", "manual_review"],
        "blocked_use": ["direct_assessment_authority", "learner_facing_output", "public_distribution", "automatic_promotion", "final_authority_promotion"],
        "promotion_rule": "candidate_only_until_review",
        "target_phase": "E4S-P2_AssessmentPatternExpansion",
        "target_ulga_stage": "ASSESSMENT_PATTERN_CANDIDATE",
        "risk_flags": ["candidate_not_authority", "not_for_public_distribution", "requires_manual_review"],
        "notes": ["Assessment pattern source candidate only."],
    },
    {
        "source_id": "GENERATED_CONTENT_CANDIDATE_POOL",
        "display_name": "Generated Content Candidate Pool",
        "source_family": "generated_content_candidate",
        "source_type": "generated_candidate_set",
        "authority_role": "generated_candidate",
        "path": "future_registry:generated_content_candidates",
        "format": "json",
        "exists": False,
        "license_status": "owned",
        "review_status": "not_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata", "manual_review"],
        "blocked_use": ["learner_facing_output", "automatic_promotion", "final_authority_promotion", "direct_reading_authority", "direct_dialogue_authority", "direct_writing_authority", "large_scale_generation"],
        "promotion_rule": "candidate_only_until_review",
        "target_phase": "DEFERRED",
        "target_ulga_stage": "GENERATED_CONTENT_CANDIDATE_REVIEW",
        "risk_flags": ["candidate_not_authority", "requires_manual_review", "promotion_risk"],
        "notes": ["Generated content remains candidate-only until review and validation."],
    },
    {
        "source_id": "STATUS_RAZ_AW_V1_SNAPSHOT",
        "display_name": "RAZ-AW-V1 Status Snapshot",
        "source_family": "status_artifact",
        "source_type": "status_snapshot",
        "authority_role": "status_only",
        "path": "google_drive_reference:RAZ-AW-V1 Status Snapshot.txt",
        "format": "txt",
        "exists": False,
        "license_status": "owned",
        "review_status": "metadata_reviewed",
        "allowed_use": ["register_in_manifest", "summarize_metadata"],
        "blocked_use": ["learner_facing_output", "direct_reading_authority", "automatic_promotion", "final_authority_promotion", "app_runtime_use"],
        "promotion_rule": "status_artifact_never_content",
        "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
        "target_ulga_stage": "STATUS_TRACKING_ONLY",
        "risk_flags": ["status_not_content", "learner_facing_blocked"],
        "notes": ["Status snapshot is progress evidence only, not Reading practice content."],
    },
]


def _assert_record_contract(record: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"{record.get('source_id', '<unknown>')} missing required fields: {missing}")

    allowed = set(record["allowed_use"])
    blocked = set(record["blocked_use"])
    conflict = sorted(allowed & blocked)
    if conflict:
        raise ValueError(f"{record['source_id']} has allowed_use/blocked_use conflict: {conflict}")
    if not record["allowed_use"]:
        raise ValueError(f"{record['source_id']} has empty allowed_use")


def normalized_records(records: Iterable[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Return manifest records in deterministic order after light contract checks."""
    selected = list(records if records is not None else SOURCE_RECORDS)
    seen: set[str] = set()

    for record in selected:
        _assert_record_contract(record)
        source_id = record["source_id"]
        if source_id in seen:
            raise ValueError(f"duplicate source_id: {source_id}")
        seen.add(source_id)

    return sorted(selected, key=lambda item: item["source_id"])


def _counter(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(record[field]) for record in records).items()))


def _risk_flag_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.get("risk_flags", []))
    return dict(sorted(counter.items()))


def build_manifest(records: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    normalized = normalized_records(records)
    return {
        "schema_version": SCHEMA_VERSION,
        "epic_id": EPIC_ID,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "contract_path": CONTRACT_PATH,
        "artifact_policy": {
            "source_payload_extraction": "forbidden",
            "learner_facing_output": "forbidden",
            "authority_promotion": "forbidden",
            "deterministic_order": "source_id",
        },
        "records": normalized,
    }


def build_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    records = manifest["records"]
    total = len(records)
    exists_true = sum(1 for record in records if record["exists"])
    exists_false = total - exists_true

    return {
        "schema_version": "E4S_SOURCE_MANIFEST_SUMMARY_V1",
        "source_manifest_schema_version": manifest["schema_version"],
        "epic_id": manifest["epic_id"],
        "phase_id": manifest["phase_id"],
        "task_id": manifest["task_id"],
        "contract_path": manifest["contract_path"],
        "record_count": total,
        "exists": {"true": exists_true, "false": exists_false},
        "by_source_family": _counter(records, "source_family"),
        "by_authority_role": _counter(records, "authority_role"),
        "by_target_phase": _counter(records, "target_phase"),
        "by_review_status": _counter(records, "review_status"),
        "risk_flag_counts": _risk_flag_counts(records),
        "gate_metrics": {
            "manifest_created": "PASS",
            "summary_created": "PASS",
            "deterministic_order_by_source_id": "PASS",
            "required_fields_present": "PASS",
            "source_payload_extraction": "NOT_PERFORMED",
            "learner_facing_output": "NOT_PERFORMED",
            "authority_promotion": "NOT_PERFORMED",
        },
        "next_shortest_step": "E4S-P0-S3_SourceManifestValidator_Implementation",
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_and_write(manifest_path: Path = DEFAULT_MANIFEST_PATH, summary_path: Path = DEFAULT_SUMMARY_PATH) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = build_manifest()
    summary = build_summary(manifest)
    write_json(manifest_path, manifest)
    write_json(summary_path, summary)
    return manifest, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the E4S source manifest and summary.")
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_and_write(args.manifest_output, args.summary_output)


if __name__ == "__main__":
    main()
