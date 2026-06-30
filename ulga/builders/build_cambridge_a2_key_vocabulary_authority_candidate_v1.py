#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_cambridge_a2_key_vocabulary_authority_candidate_v1.py

Purpose:
    Build a Cambridge A2 Key vocabulary authority candidate layer from the
    A2 Key normalized/raw/summary/error JSON artifacts.

Scope:
    - Static/offline JSON builder only.
    - Does not read PDF.
    - Does not run OCR.
    - Does not mutate ULGA graph/runtime/dashboard/learner state.
    - Does not generate learner-facing content.
    - Builds an authority *candidate* layer, not a final learner-facing authority.

Expected input files:
    cambridge_a2_key_vocabulary_normalized.json
    cambridge_a2_key_vocabulary_raw.json
    cambridge_a2_key_vocabulary_summary.json
    cambridge_a2_key_vocabulary_errors.json

Outputs:
    cambridge_a2_key_vocabulary_authority_candidate_v1.json
    cambridge_a2_key_vocabulary_authority_evidence_v1.json
    cambridge_a2_key_vocabulary_authority_summary_v1.json
    cambridge_a2_key_vocabulary_authority_blockers_v1.json
    cambridge_a2_key_vocabulary_authority_duplicates_v1.json

Example:
    python build_cambridge_a2_key_vocabulary_authority_candidate_v1.py ^
      --input-dir "G:/HomeWork/English_Learning_DB/output/a2_key_v2" ^
      --out-dir "G:/HomeWork/English_Learning_DB/output/a2_key_authority_candidate"

Or explicit paths:
    python build_cambridge_a2_key_vocabulary_authority_candidate_v1.py ^
      --normalized ".../cambridge_a2_key_vocabulary_normalized.json" ^
      --raw ".../cambridge_a2_key_vocabulary_raw.json" ^
      --summary ".../cambridge_a2_key_vocabulary_summary.json" ^
      --errors ".../cambridge_a2_key_vocabulary_errors.json" ^
      --out-dir ".../a2_key_authority_candidate"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SOURCE_ID_DEFAULT = "cambridge_a2_key_2025"
SOURCE_LEVEL = "A2_Key"
CANONICAL_LEVEL = "A2"
CEFR_ESTIMATE = "A2"
BUILDER_NAME = "build_cambridge_a2_key_vocabulary_authority_candidate_v1.py"
BUILDER_POLICY_VERSION = "a2_key_authority_candidate_builder_v1"
ALT_FORM_POLICY_VERSION = "a2_key_clean_alt_forms_v2"
SOURCE_POS_REVIEW_POLICY_VERSION = "a2_key_source_pos_review_v1"

DEFAULT_NORMALIZED_FILENAME = "cambridge_a2_key_vocabulary_normalized.json"
DEFAULT_RAW_FILENAME = "cambridge_a2_key_vocabulary_raw.json"
DEFAULT_SUMMARY_FILENAME = "cambridge_a2_key_vocabulary_summary.json"
DEFAULT_ERRORS_FILENAME = "cambridge_a2_key_vocabulary_errors.json"

AUTHORITY_OUT_FILENAME = "cambridge_a2_key_vocabulary_authority_candidate_v1.json"
EVIDENCE_OUT_FILENAME = "cambridge_a2_key_vocabulary_authority_evidence_v1.json"
SUMMARY_OUT_FILENAME = "cambridge_a2_key_vocabulary_authority_summary_v1.json"
BLOCKERS_OUT_FILENAME = "cambridge_a2_key_vocabulary_authority_blockers_v1.json"
DUPLICATES_OUT_FILENAME = "cambridge_a2_key_vocabulary_authority_duplicates_v1.json"

PASS_STATUSES = {"PASS", "PASS_WITH_WARNINGS"}
ACCEPTED_INPUT_WARNINGS = {
    "same_lemma_pos_duplicate_review_count",
    "source_pos_semantic_review_count",
}

HARD_RISK_FLAGS = {
    "pos_parse_failed",
    "empty_word_part",
    "unmatched_parentheses_entry_excluded",
    "starts_with_pos_entry_excluded",
    "semantic_fragment_alt_form_residual",
    "slash_residual_in_alt_forms",
    "unflagged_known_source_pos_semantic_review",
}

ACCEPTED_REVIEW_RISK_FLAGS = {
    "capitalized_or_acronym_entry_needs_review",
    "dialect_variant_normalized",
    "example_lines_present",
    "guide_note_present",
    "inline_parenthetical_variant_normalized",
    "same_lemma_pos_duplicate_needs_review",
    "slash_variant_normalized",
    "source_pos_semantic_review",
}

# These single-token alternatives are acceptable even when the canonical lemma is
# multiword. They are dialect/orthographic equivalents, not semantic fragments.
ALLOWED_SINGLE_TOKEN_MULTIWORD_ALTS = {
    ("all right", "alright"),
    ("french fries", "chips"),
    ("movie theater", "cinema"),
}

# Source-PDF semantic POS anomalies already flagged by the A2 extraction v2 parser.
KNOWN_SOURCE_POS_SEMANTIC_REVIEW = {
    "unfortunately": {
        "expected_pos_hint": ["adverb"],
        "reason": "source_pdf_lists_unfortunately_as_adj",
    },
    "unhappy": {
        "expected_pos_hint": ["adjective"],
        "reason": "source_pdf_lists_unhappy_as_n",
    },
}

REQUIRED_NORMALIZED_FIELDS = {
    "entry_id",
    "raw_id",
    "source_id",
    "source_file",
    "source_page",
    "source_level",
    "canonical_level",
    "cefr_estimate",
    "lemma",
    "surface_form",
    "normalized_entry",
    "pos",
    "grammar_features",
    "raw_entry",
    "raw_section",
    "example_lines",
    "is_multiword",
    "variant_uk",
    "variant_us",
    "dialect_labels",
    "alt_forms",
    "guide_note",
    "grammar_note",
    "authority_role",
    "source_role",
    "authority_import_allowed",
    "direct_use_allowed",
    "content_extraction_allowed",
    "learner_facing_allowed",
    "child_priority",
    "usable_for_reading",
    "usable_for_dialogue",
    "usable_for_writing",
    "usable_for_assessment",
    "generator_allowed",
    "validator_accepts",
    "review_status",
    "extraction_confidence",
    "parser_rule",
    "risk_flags",
}

REQUIRED_RAW_FIELDS = {
    "raw_id",
    "source_id",
    "source_file",
    "source_page",
    "raw_section",
    "raw_entry",
    "example_lines",
    "raw_text_span",
    "extraction_method",
    "extraction_confidence",
    "parser_rule",
    "page_line_index",
}

SPACE_RE = re.compile(r"\s+")


def normalize_spaces(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\u00a0", " ")
    text = text.replace("’", "'")
    text = text.replace("‘", "'")
    text = text.replace("“", '"')
    text = text.replace("”", '"')
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    return SPACE_RE.sub(" ", text).strip()


def normalize_key(value: Any) -> str:
    return normalize_spaces(value).lower()


def stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length].upper()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def uniq_preserve_order(values: Iterable[Any]) -> List[Any]:
    seen = set()
    result: List[Any] = []
    for value in values:
        if value is None:
            continue
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalized_string_list(values: Iterable[Any]) -> List[str]:
    return uniq_preserve_order(
        normalize_key(value)
        for value in values
        if normalize_key(value)
    )


def safe_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def pos_key(pos: Sequence[Any]) -> Tuple[str, ...]:
    return tuple(normalized_string_list(pos))


def optional_text_key(value: Any) -> str:
    text = normalize_key(value)
    return text if text else ""


def authority_group_key(entry: Dict[str, Any]) -> Tuple[str, Tuple[str, ...], str]:
    """A2 candidate merge key.

    A2 Key contains sense-specific guide notes, for example:
      design (PLANNING), design (PROCESS), smart (stylish), smart (clever)

    So same lemma + same POS is not enough. We merge only when guide_note is
    identical as well.
    """
    return (
        normalize_key(entry.get("lemma")),
        pos_key(entry.get("pos", [])),
        optional_text_key(entry.get("guide_note")),
    )


def loose_duplicate_key(entry: Dict[str, Any]) -> Tuple[str, Tuple[str, ...]]:
    return (normalize_key(entry.get("lemma")), pos_key(entry.get("pos", [])))


def make_authority_id(source_id: str, group_key: Tuple[str, Tuple[str, ...], str]) -> str:
    lemma, pos_tuple, guide = group_key
    digest = stable_hash(f"{source_id}|{lemma}|{'|'.join(pos_tuple)}|{guide}", 12)
    return f"AUTH_A2_KEY_{digest}"


def make_evidence_id(authority_id: str, raw_id: str, entry_id: str) -> str:
    digest = stable_hash(f"{authority_id}|{raw_id}|{entry_id}", 12)
    return f"EVID_A2_KEY_{digest}"


def has_slash_residual(values: Iterable[Any]) -> bool:
    return any("/" in normalize_spaces(value) for value in values if normalize_spaces(value))


def is_semantic_fragment_alt_form(lemma: str, alt_form: str, risk_flags: Iterable[str]) -> bool:
    lemma_key = normalize_key(lemma)
    alt_key = normalize_key(alt_form)
    if not lemma_key or not alt_key:
        return False
    if (lemma_key, alt_key) in ALLOWED_SINGLE_TOKEN_MULTIWORD_ALTS:
        return False
    if len(lemma_key.split()) <= 1:
        return False
    if len(alt_key.split()) > 1:
        return False
    # Dialect variants such as chips/cinema are explicitly allowed above. Other
    # single-token variants of multiword lemmas are treated as unsafe fragments.
    return True


def raw_id_alignment(raw_entries: List[Dict[str, Any]], normalized_entries: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str]]:
    raw_ids = {normalize_spaces(item.get("raw_id")) for item in raw_entries}
    norm_ids = {normalize_spaces(item.get("raw_id")) for item in normalized_entries}
    return raw_ids == norm_ids, sorted(raw_ids - norm_ids), sorted(norm_ids - raw_ids)


def validate_input_files(
    raw_entries: List[Dict[str, Any]],
    normalized_entries: List[Dict[str, Any]],
    summary: Dict[str, Any],
    errors: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []

    if not isinstance(raw_entries, list) or not raw_entries:
        blockers.append({"type": "input_raw_empty_or_not_list", "severity": "hard"})
    if not isinstance(normalized_entries, list) or not normalized_entries:
        blockers.append({"type": "input_normalized_empty_or_not_list", "severity": "hard"})
    if not isinstance(summary, dict):
        blockers.append({"type": "input_summary_not_object", "severity": "hard"})
    if not isinstance(errors, list):
        blockers.append({"type": "input_errors_not_list", "severity": "hard"})

    if isinstance(summary, dict):
        status = summary.get("validation_status")
        if status not in PASS_STATUSES:
            blockers.append({"type": "input_summary_status_not_pass", "severity": "hard", "validation_status": status})
        if summary.get("error_count") not in {0, "0", None}:
            blockers.append({"type": "input_summary_error_count_nonzero", "severity": "hard", "error_count": summary.get("error_count")})
        quality_gates = summary.get("quality_gates", {}) if isinstance(summary.get("quality_gates"), dict) else {}
        for gate in [
            "no_hard_normalization_errors",
            "no_suspicious_normalized_entries",
            "no_slash_residual_in_alt_forms",
            "no_semantic_fragment_alt_forms",
            "known_source_pos_semantic_items_flagged",
            "appendices_excluded",
        ]:
            if quality_gates.get(gate) is not True:
                blockers.append({"type": "input_quality_gate_failed", "severity": "hard", "gate": gate, "value": quality_gates.get(gate)})

    if errors:
        blockers.append({"type": "input_errors_file_nonempty", "severity": "hard", "count": len(errors), "sample": errors[:5]})

    for name, entries, required in [
        ("raw", raw_entries, REQUIRED_RAW_FIELDS),
        ("normalized", normalized_entries, REQUIRED_NORMALIZED_FIELDS),
    ]:
        missing_samples = []
        for idx, entry in enumerate(entries[:50]):
            missing = sorted(required - set(entry.keys()))
            if missing:
                missing_samples.append({"index": idx, "missing": missing, "entry_id": entry.get("entry_id"), "raw_id": entry.get("raw_id")})
        if missing_samples:
            blockers.append({"type": f"input_{name}_missing_required_fields", "severity": "hard", "samples": missing_samples[:10]})

    alignment_ok, raw_missing_from_norm, norm_missing_from_raw = raw_id_alignment(raw_entries, normalized_entries)
    if not alignment_ok:
        blockers.append({
            "type": "input_raw_id_alignment_failed",
            "severity": "hard",
            "raw_missing_from_normalized_count": len(raw_missing_from_norm),
            "normalized_missing_from_raw_count": len(norm_missing_from_raw),
            "raw_missing_from_normalized_sample": raw_missing_from_norm[:10],
            "normalized_missing_from_raw_sample": norm_missing_from_raw[:10],
        })

    raw_id_counter = Counter(normalize_spaces(item.get("raw_id")) for item in raw_entries)
    duplicated_raw_ids = sorted(raw_id for raw_id, count in raw_id_counter.items() if raw_id and count > 1)
    if duplicated_raw_ids:
        blockers.append({"type": "duplicate_raw_ids_in_raw_input", "severity": "hard", "count": len(duplicated_raw_ids), "sample": duplicated_raw_ids[:10]})

    norm_raw_id_counter = Counter(normalize_spaces(item.get("raw_id")) for item in normalized_entries)
    duplicated_norm_raw_ids = sorted(raw_id for raw_id, count in norm_raw_id_counter.items() if raw_id and count > 1)
    if duplicated_norm_raw_ids:
        blockers.append({"type": "duplicate_raw_ids_in_normalized_input", "severity": "hard", "count": len(duplicated_norm_raw_ids), "sample": duplicated_norm_raw_ids[:10]})

    entry_id_counter = Counter(normalize_spaces(item.get("entry_id")) for item in normalized_entries)
    duplicated_entry_ids = sorted(entry_id for entry_id, count in entry_id_counter.items() if entry_id and count > 1)
    if duplicated_entry_ids:
        blockers.append({"type": "duplicate_entry_ids_in_normalized_input", "severity": "hard", "count": len(duplicated_entry_ids), "sample": duplicated_entry_ids[:10]})

    return blockers


def source_pos_semantic_review_payload(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lemma = normalize_key(entry.get("lemma"))
    if lemma in KNOWN_SOURCE_POS_SEMANTIC_REVIEW:
        return KNOWN_SOURCE_POS_SEMANTIC_REVIEW[lemma]
    return None


def clean_authority_alt_forms(entries: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Aggregate authority-level alt_forms and remove unsafe fragments.

    The extractor v2 should already have done this, but this builder keeps a
    second authority-level gate so unsafe variants cannot enter candidate nodes.
    """
    notes: List[Dict[str, Any]] = []
    canonical_lemma = normalize_key(entries[0].get("lemma")) if entries else ""
    risk_flags = set(flag for entry in entries for flag in safe_list(entry.get("risk_flags")))

    candidates: List[str] = []
    for entry in entries:
        candidates.extend(safe_list(entry.get("alt_forms")))
        if entry.get("variant_uk"):
            candidates.append(entry.get("variant_uk"))
        if entry.get("variant_us"):
            candidates.append(entry.get("variant_us"))

    cleaned: List[str] = []
    for alt in normalized_string_list(candidates):
        if alt == canonical_lemma:
            continue
        if "/" in alt:
            notes.append({
                "type": "slash_alt_form_dropped",
                "alt_form": alt,
                "reason": "raw_slash_string_not_allowed_in_authority_alt_forms",
            })
            continue
        if is_semantic_fragment_alt_form(canonical_lemma, alt, risk_flags):
            notes.append({
                "type": "semantic_fragment_alt_form_dropped",
                "alt_form": alt,
                "reason": "single_token_fragment_of_multiword_variant",
            })
            continue
        cleaned.append(alt)
    return uniq_preserve_order(cleaned), notes


def merge_lists(entries: List[Dict[str, Any]], field: str, lower: bool = True) -> List[str]:
    values: List[str] = []
    for entry in entries:
        raw_value = entry.get(field)
        for item in safe_list(raw_value):
            text = normalize_spaces(item)
            if not text:
                continue
            values.append(text.lower() if lower else text)
    return uniq_preserve_order(values)


def merge_optional_texts(entries: List[Dict[str, Any]], field: str, lower: bool = False) -> List[str]:
    values: List[str] = []
    for entry in entries:
        text = normalize_spaces(entry.get(field))
        if text:
            values.append(text.lower() if lower else text)
    return uniq_preserve_order(values)


def determine_review_status(entries: List[Dict[str, Any]], cleanup_notes: List[Dict[str, Any]], duplicate_group_review: bool) -> str:
    risk_flags = set(flag for entry in entries for flag in safe_list(entry.get("risk_flags")))
    if cleanup_notes or duplicate_group_review or (risk_flags & ACCEPTED_REVIEW_RISK_FLAGS):
        return "auto_merged_pending_review"
    return "auto_merged_clean"


def build_authority_entries(normalized_entries: List[Dict[str, Any]], source_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    groups: Dict[Tuple[str, Tuple[str, ...], str], List[Dict[str, Any]]] = defaultdict(list)
    for entry in normalized_entries:
        groups[authority_group_key(entry)].append(entry)

    loose_groups: Dict[Tuple[str, Tuple[str, ...]], List[Tuple[str, Tuple[str, Tuple[str, ...], str]]]] = defaultdict(list)
    for key in groups:
        lemma, pos_tuple, guide_key = key
        loose_groups[(lemma, pos_tuple)].append((guide_key, key))

    authorities: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []

    for group_key, entries in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        lemma, pos_tuple, guide_key = group_key
        authority_id = make_authority_id(source_id, group_key)
        alt_forms, cleanup_notes = clean_authority_alt_forms(entries)
        loose_key = (lemma, pos_tuple)
        duplicate_group_review = len(loose_groups.get(loose_key, [])) > 1

        evidence_refs = [normalize_spaces(entry.get("raw_id")) for entry in entries]
        source_entry_ids = [normalize_spaces(entry.get("entry_id")) for entry in entries]
        source_raw_ids = evidence_refs[:]
        risk_flags = sorted(set(flag for entry in entries for flag in safe_list(entry.get("risk_flags"))))
        if duplicate_group_review and "same_lemma_pos_duplicate_sense_review" not in risk_flags:
            risk_flags.append("same_lemma_pos_duplicate_sense_review")
        if cleanup_notes and "authority_alt_form_cleanup_applied" not in risk_flags:
            risk_flags.append("authority_alt_form_cleanup_applied")

        source_pos_reviews = [
            {
                "entry_id": entry.get("entry_id"),
                "raw_id": entry.get("raw_id"),
                "lemma": entry.get("lemma"),
                "pos": entry.get("pos"),
                "review": source_pos_semantic_review_payload(entry),
            }
            for entry in entries
            if source_pos_semantic_review_payload(entry)
        ]

        authority = {
            "authority_id": authority_id,
            "authority_type": "cambridge_a2_key_vocabulary_authority_candidate",
            "builder_name": BUILDER_NAME,
            "builder_policy_version": BUILDER_POLICY_VERSION,
            "alt_form_cleanup_policy_version": ALT_FORM_POLICY_VERSION,
            "source_pos_review_policy_version": SOURCE_POS_REVIEW_POLICY_VERSION,

            "source_id": source_id,
            "source_level": SOURCE_LEVEL,
            "canonical_level": CANONICAL_LEVEL,
            "cefr_estimate": CEFR_ESTIMATE,

            "canonical_lemma": lemma,
            "normalized_entry": lemma,
            "pos": list(pos_tuple),
            "canonical_key": {
                "canonical_lemma": lemma,
                "pos": list(pos_tuple),
                "guide_note_key": guide_key,
            },
            "guide_note_key": guide_key,

            "surface_forms": merge_lists(entries, "surface_form"),
            "alt_forms": alt_forms,
            "guide_notes": merge_optional_texts(entries, "guide_note"),
            "grammar_notes": merge_optional_texts(entries, "grammar_note"),
            "grammar_features": merge_lists(entries, "grammar_features"),
            "variant_uk_forms": merge_optional_texts(entries, "variant_uk", lower=True),
            "variant_us_forms": merge_optional_texts(entries, "variant_us", lower=True),
            "dialect_labels": merge_lists(entries, "dialect_labels", lower=False),

            "source_pages": sorted(set(int(entry.get("source_page")) for entry in entries if entry.get("source_page") is not None)),
            "raw_sections": uniq_preserve_order(normalize_spaces(entry.get("raw_section")) for entry in entries if normalize_spaces(entry.get("raw_section"))),
            "source_entry_ids": source_entry_ids,
            "source_raw_ids": source_raw_ids,
            "evidence_refs": evidence_refs,
            "evidence_count": len(evidence_refs),

            "source_pos_semantic_reviews": source_pos_reviews,
            "authority_alt_form_cleanup_notes": cleanup_notes,
            "risk_flags": sorted(set(risk_flags)),
            "review_status": determine_review_status(entries, cleanup_notes, duplicate_group_review),

            "authority_role": "vocabulary_authority_candidate",
            "source_role": "authority_source",
            "authority_import_allowed": True,
            "candidate_layer_allowed": True,
            "query_candidate_allowed": True,
            "validator_accepts": True,
            "generator_allowed": False,
            "direct_use_allowed": False,
            "content_extraction_allowed": False,
            "learner_facing_allowed": False,
        }
        authorities.append(authority)

    # Build duplicate/sense review groups by lemma+POS, not by authority grouping.
    normalized_by_loose: Dict[Tuple[str, Tuple[str, ...]], List[Dict[str, Any]]] = defaultdict(list)
    for entry in normalized_entries:
        normalized_by_loose[loose_duplicate_key(entry)].append(entry)

    for loose_key, entries in sorted(normalized_by_loose.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if len(entries) <= 1:
            continue
        lemma, pos_tuple = loose_key
        guide_values = sorted(set(optional_text_key(entry.get("guide_note")) for entry in entries))
        duplicate_type = "same_lemma_same_pos_same_guide_merged" if len(guide_values) == 1 else "same_lemma_same_pos_different_guide_sense_review"
        same_guide = len(guide_values) == 1
        authority_ids = sorted(set(make_authority_id(source_id, authority_group_key(entry)) for entry in entries))
        duplicates.append({
            "duplicate_group_id": f"DUP_A2_KEY_{stable_hash(f'{source_id}|{lemma}|{pos_tuple}', 12)}",
            "duplicate_type": duplicate_type,
            "severity": "review" if not same_guide else "info",
            "merge_policy": "merged" if same_guide else "not_merged_preserve_sense_notes",
            "canonical_lemma": lemma,
            "pos": list(pos_tuple),
            "guide_note_values": guide_values,
            "authority_ids": authority_ids,
            "entry_count": len(entries),
            "entries": [
                {
                    "entry_id": entry.get("entry_id"),
                    "raw_id": entry.get("raw_id"),
                    "raw_entry": entry.get("raw_entry"),
                    "surface_form": entry.get("surface_form"),
                    "lemma": entry.get("lemma"),
                    "pos": entry.get("pos"),
                    "guide_note": entry.get("guide_note"),
                    "grammar_note": entry.get("grammar_note"),
                    "risk_flags": entry.get("risk_flags", []),
                }
                for entry in entries
            ],
        })

    return authorities, duplicates


def build_evidence_records(authorities: List[Dict[str, Any]], normalized_entries: List[Dict[str, Any]], raw_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    raw_by_id = {normalize_spaces(raw.get("raw_id")): raw for raw in raw_entries}
    authority_by_raw_id: Dict[str, Dict[str, Any]] = {}
    for authority in authorities:
        for raw_id in authority.get("evidence_refs", []):
            authority_by_raw_id[normalize_spaces(raw_id)] = authority

    evidence_records: List[Dict[str, Any]] = []
    for entry in normalized_entries:
        raw_id = normalize_spaces(entry.get("raw_id"))
        authority = authority_by_raw_id.get(raw_id)
        raw = raw_by_id.get(raw_id, {})
        authority_id = authority.get("authority_id") if authority else None
        evidence_id = make_evidence_id(authority_id or "MISSING_AUTHORITY", raw_id, normalize_spaces(entry.get("entry_id")))
        source_pos_review = source_pos_semantic_review_payload(entry)
        evidence_records.append({
            "evidence_id": evidence_id,
            "authority_id": authority_id,
            "raw_id": raw_id,
            "entry_id": entry.get("entry_id"),
            "source_id": entry.get("source_id"),
            "source_file": entry.get("source_file"),
            "source_page": entry.get("source_page"),
            "source_level": entry.get("source_level"),
            "canonical_level": entry.get("canonical_level"),
            "cefr_estimate": entry.get("cefr_estimate"),
            "raw_section": entry.get("raw_section"),
            "raw_entry": entry.get("raw_entry"),
            "raw_text_span": raw.get("raw_text_span"),
            "surface_form": entry.get("surface_form"),
            "lemma": entry.get("lemma"),
            "normalized_entry": entry.get("normalized_entry"),
            "pos": entry.get("pos", []),
            "grammar_features": entry.get("grammar_features", []),
            "guide_note": entry.get("guide_note"),
            "grammar_note": entry.get("grammar_note"),
            "example_lines": entry.get("example_lines", []),
            "alt_forms": entry.get("alt_forms", []),
            "variant_uk": entry.get("variant_uk"),
            "variant_us": entry.get("variant_us"),
            "dialect_labels": entry.get("dialect_labels", []),
            "source_pos_semantic_review": source_pos_review,
            "risk_flags": entry.get("risk_flags", []),
            "review_status": entry.get("review_status"),
            "extraction_confidence": entry.get("extraction_confidence"),
            "parser_rule": entry.get("parser_rule"),
            "extraction_method": raw.get("extraction_method"),
            "page_line_index": raw.get("page_line_index"),
            "authority_import_allowed": entry.get("authority_import_allowed"),
            "direct_use_allowed": entry.get("direct_use_allowed"),
            "content_extraction_allowed": entry.get("content_extraction_allowed"),
            "learner_facing_allowed": entry.get("learner_facing_allowed"),
        })
    return evidence_records


def find_authority_hard_blockers(authorities: List[Dict[str, Any]], evidence: List[Dict[str, Any]], normalized_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []

    authority_id_counter = Counter(a.get("authority_id") for a in authorities)
    duplicate_authority_ids = sorted(key for key, count in authority_id_counter.items() if key and count > 1)
    if duplicate_authority_ids:
        blockers.append({"type": "duplicate_authority_ids", "severity": "hard", "count": len(duplicate_authority_ids), "sample": duplicate_authority_ids[:10]})

    canonical_key_counter = Counter(json.dumps(a.get("canonical_key"), ensure_ascii=False, sort_keys=True) for a in authorities)
    duplicate_canonical_keys = sorted(key for key, count in canonical_key_counter.items() if key and count > 1)
    if duplicate_canonical_keys:
        blockers.append({"type": "duplicate_authority_canonical_keys", "severity": "hard", "count": len(duplicate_canonical_keys), "sample": duplicate_canonical_keys[:10]})

    authority_ids = {a.get("authority_id") for a in authorities}
    evidence_authority_missing = [e for e in evidence if e.get("authority_id") not in authority_ids]
    if evidence_authority_missing:
        blockers.append({
            "type": "evidence_authority_id_missing_in_authority",
            "severity": "hard",
            "count": len(evidence_authority_missing),
            "sample": [e.get("evidence_id") for e in evidence_authority_missing[:10]],
        })

    normalized_raw_ids = {normalize_spaces(e.get("raw_id")) for e in normalized_entries}
    evidence_raw_ids = {normalize_spaces(e.get("raw_id")) for e in evidence}
    if normalized_raw_ids != evidence_raw_ids:
        blockers.append({
            "type": "evidence_raw_id_preservation_failed",
            "severity": "hard",
            "normalized_minus_evidence_count": len(normalized_raw_ids - evidence_raw_ids),
            "evidence_minus_normalized_count": len(evidence_raw_ids - normalized_raw_ids),
            "normalized_minus_evidence_sample": sorted(normalized_raw_ids - evidence_raw_ids)[:10],
            "evidence_minus_normalized_sample": sorted(evidence_raw_ids - normalized_raw_ids)[:10],
        })

    slash_residuals = [
        {"authority_id": a.get("authority_id"), "canonical_lemma": a.get("canonical_lemma"), "alt_form": alt}
        for a in authorities
        for alt in a.get("alt_forms", [])
        if "/" in normalize_spaces(alt)
    ]
    if slash_residuals:
        blockers.append({"type": "slash_residual_in_authority_alt_forms", "severity": "hard", "count": len(slash_residuals), "sample": slash_residuals[:10]})

    semantic_fragment_residuals = [
        {"authority_id": a.get("authority_id"), "canonical_lemma": a.get("canonical_lemma"), "alt_form": alt}
        for a in authorities
        for alt in a.get("alt_forms", [])
        if is_semantic_fragment_alt_form(a.get("canonical_lemma"), alt, a.get("risk_flags", []))
    ]
    if semantic_fragment_residuals:
        blockers.append({"type": "semantic_fragment_alt_form_residual", "severity": "hard", "count": len(semantic_fragment_residuals), "sample": semantic_fragment_residuals[:10]})

    hard_risk_hits = [
        {"authority_id": a.get("authority_id"), "canonical_lemma": a.get("canonical_lemma"), "risk_flags": sorted(set(a.get("risk_flags", [])) & HARD_RISK_FLAGS)}
        for a in authorities
        if set(a.get("risk_flags", [])) & HARD_RISK_FLAGS
    ]
    if hard_risk_hits:
        blockers.append({"type": "hard_risk_flags_in_authority", "severity": "hard", "count": len(hard_risk_hits), "sample": hard_risk_hits[:10]})

    unflagged_pos_reviews = []
    for item in normalized_entries:
        payload = source_pos_semantic_review_payload(item)
        if payload and "source_pos_semantic_review" not in item.get("risk_flags", []):
            unflagged_pos_reviews.append({"entry_id": item.get("entry_id"), "raw_id": item.get("raw_id"), "lemma": item.get("lemma"), "pos": item.get("pos"), "review": payload})
    if unflagged_pos_reviews:
        blockers.append({"type": "unflagged_known_source_pos_semantic_review", "severity": "hard", "count": len(unflagged_pos_reviews), "sample": unflagged_pos_reviews[:10]})

    empty_lemma = [a for a in authorities if not normalize_spaces(a.get("canonical_lemma"))]
    empty_pos = [a for a in authorities if not a.get("pos")]
    if empty_lemma:
        blockers.append({"type": "empty_authority_canonical_lemma", "severity": "hard", "count": len(empty_lemma), "sample": [a.get("authority_id") for a in empty_lemma[:10]]})
    if empty_pos:
        blockers.append({"type": "empty_authority_pos", "severity": "hard", "count": len(empty_pos), "sample": [a.get("authority_id") for a in empty_pos[:10]]})

    return blockers


def build_review_items(authorities: List[Dict[str, Any]], duplicates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    review_items: List[Dict[str, Any]] = []

    for dup in duplicates:
        if dup.get("severity") == "review":
            review_items.append({
                "type": "same_lemma_pos_duplicate_sense_review",
                "severity": "review",
                "duplicate_group_id": dup.get("duplicate_group_id"),
                "canonical_lemma": dup.get("canonical_lemma"),
                "pos": dup.get("pos"),
                "guide_note_values": dup.get("guide_note_values"),
                "entry_count": dup.get("entry_count"),
            })

    lemma_to_pos_sets: Dict[str, set] = defaultdict(set)
    for authority in authorities:
        lemma_to_pos_sets[authority.get("canonical_lemma")].add(tuple(authority.get("pos", [])))
    for lemma, pos_sets in sorted(lemma_to_pos_sets.items()):
        if len(pos_sets) > 1:
            review_items.append({
                "type": "same_lemma_multiple_pos_sets_review",
                "severity": "review",
                "canonical_lemma": lemma,
                "pos_sets": [list(pos_tuple) for pos_tuple in sorted(pos_sets)],
            })

    for authority in authorities:
        if authority.get("source_pos_semantic_reviews"):
            review_items.append({
                "type": "source_pos_semantic_review",
                "severity": "review",
                "authority_id": authority.get("authority_id"),
                "canonical_lemma": authority.get("canonical_lemma"),
                "pos": authority.get("pos"),
                "reviews": authority.get("source_pos_semantic_reviews"),
            })

    return review_items


def build_blockers_report(input_blockers: List[Dict[str, Any]], authority_hard_blockers: List[Dict[str, Any]], review_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "builder_name": BUILDER_NAME,
        "builder_policy_version": BUILDER_POLICY_VERSION,
        "input_blocker_count": len(input_blockers),
        "authority_hard_blocker_count": len(authority_hard_blockers),
        "authority_review_warning_count": len(review_items),
        "input_blockers": input_blockers,
        "authority_hard_blockers": authority_hard_blockers,
        "authority_review_items": review_items,
    }


def build_summary(
    source_paths: Dict[str, str],
    source_summary: Dict[str, Any],
    raw_entries: List[Dict[str, Any]],
    normalized_entries: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
    authorities: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
    duplicates: List[Dict[str, Any]],
    input_blockers: List[Dict[str, Any]],
    authority_hard_blockers: List[Dict[str, Any]],
    review_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    validation_status = "PASS"
    if input_blockers or authority_hard_blockers:
        validation_status = "FAIL"
    elif review_items or source_summary.get("validation_status") == "PASS_WITH_WARNINGS":
        validation_status = "PASS_WITH_REVIEW_WARNINGS"

    risk_counter = Counter(flag for authority in authorities for flag in authority.get("risk_flags", []))
    review_counter = Counter(item.get("type") for item in review_items)
    duplicate_counter = Counter(dup.get("duplicate_type") for dup in duplicates)
    pos_counter = Counter(pos for authority in authorities for pos in authority.get("pos", []))
    section_counter = Counter(section for authority in authorities for section in authority.get("raw_sections", []))
    page_counter = Counter(str(page) for authority in authorities for page in authority.get("source_pages", []))
    review_status_counter = Counter(authority.get("review_status") for authority in authorities)

    authority_ids = [a.get("authority_id") for a in authorities]
    canonical_keys = [json.dumps(a.get("canonical_key"), ensure_ascii=False, sort_keys=True) for a in authorities]
    normalized_raw_ids = {normalize_spaces(e.get("raw_id")) for e in normalized_entries}
    evidence_raw_ids = {normalize_spaces(e.get("raw_id")) for e in evidence}
    evidence_authority_ids = {e.get("authority_id") for e in evidence}
    authority_id_set = set(authority_ids)

    slash_residuals = [
        {"authority_id": a.get("authority_id"), "canonical_lemma": a.get("canonical_lemma"), "alt_form": alt}
        for a in authorities
        for alt in a.get("alt_forms", [])
        if "/" in normalize_spaces(alt)
    ]
    semantic_fragment_residuals = [
        {"authority_id": a.get("authority_id"), "canonical_lemma": a.get("canonical_lemma"), "alt_form": alt}
        for a in authorities
        for alt in a.get("alt_forms", [])
        if is_semantic_fragment_alt_form(a.get("canonical_lemma"), alt, a.get("risk_flags", []))
    ]
    source_pos_reviews = [review for a in authorities for review in a.get("source_pos_semantic_reviews", [])]
    unflagged_known_source_pos = [
        item for item in normalized_entries
        if source_pos_semantic_review_payload(item) and "source_pos_semantic_review" not in item.get("risk_flags", [])
    ]

    return {
        "validation_status": validation_status,
        "builder_name": BUILDER_NAME,
        "builder_policy_version": BUILDER_POLICY_VERSION,
        "alt_form_cleanup_policy_version": ALT_FORM_POLICY_VERSION,
        "source_pos_review_policy_version": SOURCE_POS_REVIEW_POLICY_VERSION,
        "source_paths": source_paths,
        "source_id": source_summary.get("source_id") or SOURCE_ID_DEFAULT,
        "source_level": SOURCE_LEVEL,
        "canonical_level": CANONICAL_LEVEL,
        "cefr_estimate": CEFR_ESTIMATE,
        "source_validation_status": source_summary.get("validation_status"),
        "source_parser_policy_version": source_summary.get("parser_policy_version"),

        "input_raw_entry_count": len(raw_entries),
        "input_normalized_entry_count": len(normalized_entries),
        "input_error_count": len(errors),
        "authority_entry_count": len(authorities),
        "evidence_record_count": len(evidence),
        "duplicate_group_count": len(duplicates),
        "input_blocker_count": len(input_blockers),
        "authority_hard_blocker_count": len(authority_hard_blockers),
        "authority_review_warning_count": len(review_items),

        "counts_by_pos": dict(sorted(pos_counter.items())),
        "counts_by_raw_section": dict(sorted(section_counter.items())),
        "counts_by_source_page": dict(sorted(page_counter.items(), key=lambda kv: int(kv[0]))),
        "counts_by_review_status": dict(sorted(review_status_counter.items())),
        "risk_flags": dict(sorted(risk_counter.items())),
        "review_item_types": dict(sorted(review_counter.items())),
        "duplicate_types": dict(sorted(duplicate_counter.items())),

        "alt_form_cleanup": {
            "policy_version": ALT_FORM_POLICY_VERSION,
            "slash_alt_form_residual_count": len(slash_residuals),
            "semantic_fragment_alt_form_residual_count": len(semantic_fragment_residuals),
            "sample_slash_alt_form_residuals": slash_residuals[:10],
            "sample_semantic_fragment_alt_form_residuals": semantic_fragment_residuals[:10],
        },
        "source_pos_semantic_review": {
            "known_review_policy_version": SOURCE_POS_REVIEW_POLICY_VERSION,
            "source_pos_semantic_review_count": len(source_pos_reviews),
            "unflagged_known_source_pos_semantic_review_count": len(unflagged_known_source_pos),
            "samples": source_pos_reviews[:10],
        },
        "quality_gates": {
            "no_input_blockers": not input_blockers,
            "no_authority_hard_blockers": not authority_hard_blockers,
            "no_duplicate_authority_ids": len(authority_ids) == len(set(authority_ids)),
            "no_duplicate_authority_canonical_keys": len(canonical_keys) == len(set(canonical_keys)),
            "all_input_raw_ids_preserved_in_evidence": normalized_raw_ids == evidence_raw_ids,
            "all_evidence_authority_ids_exist": evidence_authority_ids <= authority_id_set,
            "no_hard_risk_flags_in_authority": not any(set(a.get("risk_flags", [])) & HARD_RISK_FLAGS for a in authorities),
            "no_slash_residual_in_authority_alt_forms": not slash_residuals,
            "no_semantic_fragment_authority_alt_forms": not semantic_fragment_residuals,
            "known_source_pos_semantic_items_flagged": not unflagged_known_source_pos,
            "source_pos_semantic_review_is_non_blocking": True,
            "all_authority_import_allowed": all(a.get("authority_import_allowed") is True for a in authorities),
            "all_direct_use_disallowed": all(a.get("direct_use_allowed") is False for a in authorities),
            "all_learner_facing_disallowed": all(a.get("learner_facing_allowed") is False for a in authorities),
            "ulga_graph_modified": False,
            "learner_facing_content_generated": False,
        },
        "boundary_confirmation": {
            "pdf_read": False,
            "ocr_used": False,
            "pdf_text_layer_only": False,
            "input_json_only": True,
            "authority_graph_modified": False,
            "learner_facing_content_generated": False,
            "content_extraction_allowed": False,
        },
    }


def resolve_input_paths(args: argparse.Namespace) -> Dict[str, Path]:
    if args.input_dir:
        input_dir = Path(args.input_dir).resolve()
        paths = {
            "normalized": input_dir / DEFAULT_NORMALIZED_FILENAME,
            "raw": input_dir / DEFAULT_RAW_FILENAME,
            "summary": input_dir / DEFAULT_SUMMARY_FILENAME,
            "errors": input_dir / DEFAULT_ERRORS_FILENAME,
        }
    else:
        required = [args.normalized, args.raw, args.summary, args.errors]
        if not all(required):
            raise ValueError("Either --input-dir or all of --normalized --raw --summary --errors must be provided.")
        paths = {
            "normalized": Path(args.normalized).resolve(),
            "raw": Path(args.raw).resolve(),
            "summary": Path(args.summary).resolve(),
            "errors": Path(args.errors).resolve(),
        }

    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input files: {missing}")
    return paths


def run(args: argparse.Namespace) -> int:
    input_paths = resolve_input_paths(args)
    out_dir = Path(args.out_dir).resolve()

    print(f"[INFO] Normalized: {input_paths['normalized']}")
    print(f"[INFO] Raw:        {input_paths['raw']}")
    print(f"[INFO] Summary:    {input_paths['summary']}")
    print(f"[INFO] Errors:     {input_paths['errors']}")
    print(f"[INFO] Output dir: {out_dir}")

    normalized_entries = load_json(input_paths["normalized"])
    raw_entries = load_json(input_paths["raw"])
    source_summary = load_json(input_paths["summary"])
    errors = load_json(input_paths["errors"])

    if not isinstance(normalized_entries, list):
        raise TypeError("normalized JSON must be a list")
    if not isinstance(raw_entries, list):
        raise TypeError("raw JSON must be a list")
    if not isinstance(source_summary, dict):
        raise TypeError("summary JSON must be an object")
    if not isinstance(errors, list):
        raise TypeError("errors JSON must be a list")

    source_id = source_summary.get("source_id") or SOURCE_ID_DEFAULT

    input_blockers = validate_input_files(raw_entries, normalized_entries, source_summary, errors)
    authorities, duplicates = build_authority_entries(normalized_entries, source_id=source_id)
    evidence = build_evidence_records(authorities, normalized_entries, raw_entries)
    authority_hard_blockers = find_authority_hard_blockers(authorities, evidence, normalized_entries)
    review_items = build_review_items(authorities, duplicates)
    blockers_report = build_blockers_report(input_blockers, authority_hard_blockers, review_items)
    summary = build_summary(
        source_paths={key: str(path) for key, path in input_paths.items()},
        source_summary=source_summary,
        raw_entries=raw_entries,
        normalized_entries=normalized_entries,
        errors=errors,
        authorities=authorities,
        evidence=evidence,
        duplicates=duplicates,
        input_blockers=input_blockers,
        authority_hard_blockers=authority_hard_blockers,
        review_items=review_items,
    )

    authority_out = out_dir / AUTHORITY_OUT_FILENAME
    evidence_out = out_dir / EVIDENCE_OUT_FILENAME
    summary_out = out_dir / SUMMARY_OUT_FILENAME
    blockers_out = out_dir / BLOCKERS_OUT_FILENAME
    duplicates_out = out_dir / DUPLICATES_OUT_FILENAME

    write_json(authority_out, authorities)
    write_json(evidence_out, evidence)
    write_json(summary_out, summary)
    write_json(blockers_out, blockers_report)
    write_json(duplicates_out, duplicates)

    print(f"[INFO] Input normalized entries: {len(normalized_entries)}")
    print(f"[INFO] Input raw entries: {len(raw_entries)}")
    print(f"[INFO] Authority entries: {len(authorities)}")
    print(f"[INFO] Evidence records: {len(evidence)}")
    print(f"[INFO] Duplicate groups: {len(duplicates)}")
    print(f"[INFO] Input blockers: {len(input_blockers)}")
    print(f"[INFO] Authority hard blockers: {len(authority_hard_blockers)}")
    print(f"[INFO] Authority review warnings: {len(review_items)}")
    print(f"[WRITE] {authority_out}")
    print(f"[WRITE] {evidence_out}")
    print(f"[WRITE] {summary_out}")
    print(f"[WRITE] {blockers_out}")
    print(f"[WRITE] {duplicates_out}")
    print(f"[RESULT] {summary['validation_status']}")

    return 0 if summary["validation_status"] in {"PASS", "PASS_WITH_REVIEW_WARNINGS"} else 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Cambridge A2 Key vocabulary authority candidate JSON artifacts."
    )
    parser.add_argument("--input-dir", default=None, help="Directory containing the four A2 extraction JSON files.")
    parser.add_argument("--normalized", default=None, help="Path to cambridge_a2_key_vocabulary_normalized.json.")
    parser.add_argument("--raw", default=None, help="Path to cambridge_a2_key_vocabulary_raw.json.")
    parser.add_argument("--summary", default=None, help="Path to cambridge_a2_key_vocabulary_summary.json.")
    parser.add_argument("--errors", default=None, help="Path to cambridge_a2_key_vocabulary_errors.json.")
    parser.add_argument("--out-dir", required=True, help="Output directory for authority candidate artifacts.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
