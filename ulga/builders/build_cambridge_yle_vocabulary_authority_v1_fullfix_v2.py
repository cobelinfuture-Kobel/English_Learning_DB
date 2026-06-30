#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_cambridge_yle_vocabulary_authority_v1.py

Purpose:
    Merge Cambridge YLE Starters / Movers / Flyers normalized vocabulary JSON
    into one canonical YLE vocabulary authority layer.

Scope:
    - Reads normalized JSON artifacts only.
    - Does not read PDFs.
    - Does not perform OCR.
    - Does not modify ULGA graph files.
    - Does not generate learner-facing content.

Expected inputs:
    cambridge_starters_vocabulary_normalized.json
    cambridge_movers_vocabulary_normalized.json
    cambridge_flyers_vocabulary_normalized.json

Outputs:
    cambridge_yle_vocabulary_authority_v1.json
    cambridge_yle_vocabulary_authority_evidence_v1.json
    cambridge_yle_vocabulary_authority_summary_v1.json
    cambridge_yle_vocabulary_authority_blockers_v1.json
    cambridge_yle_vocabulary_authority_duplicates_v1.json

Example:
    python build_cambridge_yle_vocabulary_authority_v1.py ^
      --input-dir "G:/HomeWork/English_Learning_DB/output/cambridge_vocab_sample" ^
      --out-dir "G:/HomeWork/English_Learning_DB/output/cambridge_yle_authority_v1"

Or explicit paths:
    python build_cambridge_yle_vocabulary_authority_v1.py ^
      --starters ".../cambridge_starters_vocabulary_normalized.json" ^
      --movers ".../cambridge_movers_vocabulary_normalized.json" ^
      --flyers ".../cambridge_flyers_vocabulary_normalized.json" ^
      --out-dir ".../cambridge_yle_authority_v1"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SPACE_RE = re.compile(r"\s+")

SOURCE_LEVEL_PRIORITY = {
    "Starters": 1,
    "Movers": 2,
    "Flyers": 3,
}

SOURCE_LEVEL_TO_CANONICAL = {
    "Starters": "PreA1",
    "Movers": "A1",
    "Flyers": "A2_low",
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
    "raw_entry",
    "raw_section",
    "is_multiword",
    "variant_uk",
    "variant_us",
    "alt_forms",
    "guide_note",
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

HARD_RISK_FLAGS = {
    "pos_only_entry_excluded",
    "starts_with_pos_entry_excluded",
    "unmatched_parentheses_entry_excluded",
    "semantic_merge_error_detected",
    "duplicate_canonical_key_unmerged_needs_review",
}

ACCEPTED_REVIEW_RISK_FLAGS = {
    "proper_name_or_capitalized_entry_needs_review",
    "pattern_or_placeholder_entry_needs_review",
    "slash_variant_needs_review",
    "slash_phrase_variant_normalized",
    "wrapped_entry_auto_merged",
    "pos_inferred_for_no_pos_time_entry",
    "duplicate_canonical_key_merged",
}

ALT_FORM_CLEANUP_POLICY_VERSION = "clean_alt_forms_v2"

# Raw slash forms are allowed in evidence/surface_forms because they preserve
# the Cambridge source presentation, but they are not allowed in authority
# alt_forms because query/generator layers need expanded clean alternatives.
# Examples:
#   child/children          -> children
#   foot/feet               -> feet
#   take a photo/ picture   -> take a picture
#   city/town centre        -> town centre
#   businessman/ woman      -> businesswoman


def normalize_spaces(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\u00a0", " ")
    text = text.replace("’", "'")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    return SPACE_RE.sub(" ", text).strip()


def stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length].upper()


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def uniq_preserve_order(values: Iterable[Any]) -> List[Any]:
    seen = set()
    result = []
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
        normalize_spaces(value).lower()
        for value in values
        if normalize_spaces(value)
    )


def normalize_alt_form(value: Any) -> str:
    return normalize_spaces(value).lower()


def raw_slash_string_present(value: Any) -> bool:
    text = normalize_alt_form(value)
    return "/" in text


def expand_slash_alt_form(value: Any, canonical_lemma: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Expand one raw slash form into clean authority alt forms.

    This function intentionally does not return the raw slash text itself.
    The raw slash text remains available in surface_forms/raw_entries/evidence.
    """
    text = normalize_alt_form(value)
    lemma = normalize_alt_form(canonical_lemma)
    notes: List[Dict[str, Any]] = []

    if not text or "/" not in text:
        return ([text] if text else []), notes

    before, after = text.split("/", 1)
    left = normalize_alt_form(before)
    right = normalize_alt_form(after)
    if not left or not right:
        notes.append({
            "type": "slash_alt_form_dropped_unexpandable",
            "raw_alt_form": text,
            "reason": "missing_left_or_right_side",
        })
        return [], notes

    expanded: List[str] = []

    # Case: take a photo/ picture -> take a picture
    if " " in left and " " not in right:
        prefix = left.rsplit(" ", 1)[0]
        expanded.append(normalize_alt_form(f"{prefix} {right}"))
    # Case: businessman/ woman -> businesswoman
    elif left.endswith("man") and right == "woman":
        expanded.append(normalize_alt_form(f"{left[:-3]}woman"))
    elif left.endswith("men") and right == "women":
        expanded.append(normalize_alt_form(f"{left[:-3]}women"))
    else:
        # Cases: child/children -> children; city/town centre -> town centre
        expanded.append(right)

    cleaned = []
    for candidate in expanded:
        candidate = normalize_alt_form(candidate)
        if not candidate:
            continue
        if candidate == lemma:
            notes.append({
                "type": "slash_alt_form_candidate_equal_lemma_dropped",
                "raw_alt_form": text,
                "candidate": candidate,
            })
            continue
        if "/" in candidate:
            notes.append({
                "type": "slash_alt_form_candidate_still_contains_slash_dropped",
                "raw_alt_form": text,
                "candidate": candidate,
            })
            continue
        cleaned.append(candidate)

    if cleaned:
        notes.append({
            "type": "slash_alt_form_expanded",
            "raw_alt_form": text,
            "expanded_alt_forms": cleaned,
        })
    else:
        notes.append({
            "type": "slash_alt_form_dropped_no_clean_candidate",
            "raw_alt_form": text,
        })

    return uniq_preserve_order(cleaned), notes


def clean_alt_form_candidates(
    candidates: Iterable[Any],
    canonical_lemma: str,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    lemma = normalize_alt_form(canonical_lemma)
    clean_forms: List[str] = []
    notes: List[Dict[str, Any]] = []

    for value in candidates:
        text = normalize_alt_form(value)
        if not text:
            continue
        if raw_slash_string_present(text):
            expanded, expansion_notes = expand_slash_alt_form(text, lemma)
            clean_forms.extend(expanded)
            notes.extend(expansion_notes)
            continue
        if text == lemma:
            notes.append({
                "type": "alt_form_equal_lemma_dropped",
                "alt_form": text,
            })
            continue
        clean_forms.append(text)

    # Final guard: authority alt_forms must be clean generator/query variants.
    final_forms: List[str] = []
    for form in uniq_preserve_order(clean_forms):
        if not form or form == lemma:
            continue
        if raw_slash_string_present(form):
            notes.append({
                "type": "alt_form_with_slash_dropped_by_final_guard",
                "alt_form": form,
            })
            continue
        final_forms.append(form)

    return final_forms, notes


def is_multiword_text(text: Any) -> bool:
    clean = normalize_alt_form(text)
    return bool(clean) and (" " in clean or "-" in clean)


def is_single_token_alt_form(text: Any) -> bool:
    clean = normalize_alt_form(text)
    return bool(clean) and (" " not in clean and "-" not in clean)


def last_token(text: Any) -> str:
    clean = normalize_alt_form(text)
    if not clean:
        return ""
    return clean.split()[-1].split("-")[-1]


def remove_semantic_fragment_alt_forms(
    typed_forms: Iterable[Tuple[str, str]],
    canonical_lemma: str,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Remove broad one-token fragments from multiword authority variants.

    Example: take a photo/ picture can generate both:
      - picture
      - take a picture
    For query/generator authority use, only the anchored phrase is safe.
    The one-token fragment remains traceable in evidence.alt_forms/raw_entry,
    but is not allowed in authority.alt_forms or evidence.clean_alt_forms.
    """
    lemma = normalize_alt_form(canonical_lemma)
    normalized_typed: List[Tuple[str, str]] = []
    for form, source in typed_forms:
        clean = normalize_alt_form(form)
        if not clean or clean == lemma or raw_slash_string_present(clean):
            continue
        normalized_typed.append((clean, source))

    all_forms = [form for form, _source in normalized_typed]
    phrase_last_tokens = {last_token(form) for form in all_forms if is_multiword_text(form)}

    final_forms: List[str] = []
    notes: List[Dict[str, Any]] = []
    for form, source in normalized_typed:
        if (
            source in {"raw_alt_form", "primary_raw_alt_form"}
            and is_multiword_text(lemma)
            and is_single_token_alt_form(form)
            and form in phrase_last_tokens
        ):
            notes.append({
                "type": "semantic_fragment_alt_form_dropped",
                "alt_form": form,
                "canonical_lemma": lemma,
                "reason": "single_token_fragment_of_multiword_variant",
            })
            continue
        final_forms.append(form)

    return uniq_preserve_order(final_forms), notes


def semantic_fragment_alt_form_residuals_for_entry(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    lemma = normalize_alt_form(entry.get("canonical_lemma"))
    if not is_multiword_text(lemma):
        return []

    alt_forms = [normalize_alt_form(alt) for alt in entry.get("alt_forms", []) if normalize_alt_form(alt)]
    phrase_last_tokens = {last_token(alt) for alt in alt_forms if is_multiword_text(alt)}
    residuals = []
    for alt in alt_forms:
        if is_single_token_alt_form(alt) and alt in phrase_last_tokens:
            residuals.append({
                "authority_id": entry.get("authority_id"),
                "canonical_lemma": lemma,
                "alt_form": alt,
                "matched_phrase_last_token": alt,
            })
    return residuals


def clean_entry_alt_forms(entry: Dict[str, Any]) -> List[str]:
    lemma = normalize_spaces(entry.get("lemma")).lower()

    raw_clean, _ = clean_alt_form_candidates(as_list(entry.get("alt_forms")), lemma)
    uk_clean, _ = clean_alt_form_candidates([entry.get("variant_uk")] if entry.get("variant_uk") else [], lemma)
    us_clean, _ = clean_alt_form_candidates([entry.get("variant_us")] if entry.get("variant_us") else [], lemma)
    surface_clean, _ = clean_alt_form_candidates(
        [entry.get("surface_form")]
        if normalize_spaces(entry.get("surface_form")).lower() != lemma
        else [],
        lemma,
    )

    typed_forms = (
        [(form, "raw_alt_form") for form in raw_clean]
        + [(form, "variant_uk") for form in uk_clean]
        + [(form, "variant_us") for form in us_clean]
        + [(form, "surface_form") for form in surface_clean]
    )
    clean, _ = remove_semantic_fragment_alt_forms(typed_forms, lemma)
    return clean


def has_unmatched_parentheses(text: str) -> bool:
    bal = 0
    for ch in normalize_spaces(text):
        if ch == "(":
            bal += 1
        elif ch == ")":
            bal -= 1
        if bal < 0:
            return True
    return bal != 0


def canonical_pos_tuple(pos: Any) -> Tuple[str, ...]:
    return tuple(sorted(normalize_spaces(p).lower() for p in as_list(pos) if normalize_spaces(p)))


def source_sort_key(entry: Dict[str, Any]) -> Tuple[int, int, str, str]:
    source_level = normalize_spaces(entry.get("source_level"))
    return (
        SOURCE_LEVEL_PRIORITY.get(source_level, 999),
        int(entry.get("source_page") or 9999),
        normalize_spaces(entry.get("raw_section")),
        normalize_spaces(entry.get("raw_id")),
    )


def authority_id_for(lemma: str, pos: Tuple[str, ...]) -> str:
    digest = stable_hash(f"cambridge_yle_v1|{lemma}|{'|'.join(pos)}", 12)
    return f"VOCAB_AUTH_CAMBRIDGE_YLE_V1_{digest}"


def validate_input_entry(entry: Dict[str, Any], path_label: str, index: int) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []

    missing = sorted(field for field in REQUIRED_NORMALIZED_FIELDS if field not in entry)
    if missing:
        blockers.append({
            "type": "missing_required_fields",
            "path_label": path_label,
            "index": index,
            "raw_id": entry.get("raw_id"),
            "entry_id": entry.get("entry_id"),
            "missing_fields": missing,
        })

    lemma = normalize_spaces(entry.get("lemma")).lower()
    if not lemma:
        blockers.append({
            "type": "empty_lemma",
            "path_label": path_label,
            "index": index,
            "raw_id": entry.get("raw_id"),
            "entry_id": entry.get("entry_id"),
        })

    pos = canonical_pos_tuple(entry.get("pos"))
    if not pos:
        blockers.append({
            "type": "empty_pos",
            "path_label": path_label,
            "index": index,
            "raw_id": entry.get("raw_id"),
            "entry_id": entry.get("entry_id"),
            "lemma": lemma,
        })

    source_level = normalize_spaces(entry.get("source_level"))
    if source_level not in SOURCE_LEVEL_PRIORITY:
        blockers.append({
            "type": "unknown_source_level",
            "path_label": path_label,
            "index": index,
            "raw_id": entry.get("raw_id"),
            "entry_id": entry.get("entry_id"),
            "source_level": source_level,
        })

    for field_name in ("variant_uk", "variant_us"):
        value = normalize_spaces(entry.get(field_name))
        if value and has_unmatched_parentheses(value):
            blockers.append({
                "type": "unbalanced_variant_form",
                "path_label": path_label,
                "index": index,
                "raw_id": entry.get("raw_id"),
                "entry_id": entry.get("entry_id"),
                "field": field_name,
                "value": value,
            })

    for alt in as_list(entry.get("alt_forms")):
        alt_clean = normalize_spaces(alt)
        if alt_clean and has_unmatched_parentheses(alt_clean):
            blockers.append({
                "type": "unbalanced_alt_form",
                "path_label": path_label,
                "index": index,
                "raw_id": entry.get("raw_id"),
                "entry_id": entry.get("entry_id"),
                "alt_form": alt_clean,
            })

    hard_flags = sorted(set(as_list(entry.get("risk_flags"))) & HARD_RISK_FLAGS)
    if hard_flags:
        blockers.append({
            "type": "hard_risk_flag_present",
            "path_label": path_label,
            "index": index,
            "raw_id": entry.get("raw_id"),
            "entry_id": entry.get("entry_id"),
            "lemma": lemma,
            "risk_flags": hard_flags,
        })

    return blockers


def load_entries(starters: Path, movers: Path, flyers: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    loaded: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []

    for label, path in (("Starters", starters), ("Movers", movers), ("Flyers", flyers)):
        data = load_json(path)
        if not isinstance(data, list):
            blockers.append({
                "type": "input_not_list",
                "path_label": label,
                "path": str(path),
                "actual_type": type(data).__name__,
            })
            continue
        for idx, entry in enumerate(data, start=1):
            if not isinstance(entry, dict):
                blockers.append({
                    "type": "input_item_not_object",
                    "path_label": label,
                    "path": str(path),
                    "index": idx,
                    "actual_type": type(entry).__name__,
                })
                continue
            entry_copy = dict(entry)
            entry_copy["_input_path_label"] = label
            entry_copy["_input_path"] = str(path)
            entry_copy["_input_index"] = idx
            blockers.extend(validate_input_entry(entry_copy, label, idx))
            loaded.append(entry_copy)

    return loaded, blockers


def build_evidence_record(entry: Dict[str, Any], authority_id: str) -> Dict[str, Any]:
    source_level = normalize_spaces(entry.get("source_level"))
    return {
        "authority_id": authority_id,
        "entry_id": entry.get("entry_id"),
        "raw_id": entry.get("raw_id"),
        "source_id": entry.get("source_id"),
        "source_file": entry.get("source_file"),
        "source_page": entry.get("source_page"),
        "source_level": source_level,
        "canonical_level": entry.get("canonical_level"),
        "source_priority_rank": SOURCE_LEVEL_PRIORITY.get(source_level, 999),
        "raw_section": entry.get("raw_section"),
        "raw_entry": entry.get("raw_entry"),
        "surface_form": entry.get("surface_form"),
        "lemma": normalize_spaces(entry.get("lemma")).lower(),
        "pos": list(canonical_pos_tuple(entry.get("pos"))),
        "variant_uk": entry.get("variant_uk"),
        "variant_us": entry.get("variant_us"),
        "alt_forms": as_list(entry.get("alt_forms")),
        "clean_alt_forms": clean_entry_alt_forms(entry),
        "alt_form_cleanup_policy_version": ALT_FORM_CLEANUP_POLICY_VERSION,
        "guide_note": entry.get("guide_note"),
        "parser_rule": entry.get("parser_rule"),
        "risk_flags": as_list(entry.get("risk_flags")),
        "review_status": entry.get("review_status"),
        "extraction_confidence": entry.get("extraction_confidence"),
    }


def choose_primary_entry(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    def score(entry: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
        # Lower source priority is earlier/core. Then prefer cleaner entries.
        source_level = normalize_spaces(entry.get("source_level"))
        risks = set(as_list(entry.get("risk_flags")))
        return (
            -SOURCE_LEVEL_PRIORITY.get(source_level, 999),
            -len(risks),
            int(entry.get("child_priority") or 0),
            -int(entry.get("source_page") or 9999),
            -int(entry.get("_input_index") or 999999),
        )

    return sorted(group, key=score, reverse=True)[0]


def build_authority_entry(lemma: str, pos: Tuple[str, ...], group: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    group_sorted = sorted(group, key=source_sort_key)
    primary = choose_primary_entry(group_sorted)

    source_levels = uniq_preserve_order(normalize_spaces(e.get("source_level")) for e in group_sorted)
    earliest_source_level = sorted(source_levels, key=lambda level: SOURCE_LEVEL_PRIORITY.get(level, 999))[0]
    earliest_canonical_level = SOURCE_LEVEL_TO_CANONICAL.get(earliest_source_level, earliest_source_level)
    authority_id = authority_id_for(lemma, pos)

    primary_raw_alt_candidates: List[Any] = list(as_list(primary.get("alt_forms")))
    raw_alt_candidates: List[Any] = []
    variant_uk_candidates: List[Any] = []
    variant_us_candidates: List[Any] = []
    surface_alt_candidates: List[Any] = []

    for e in group_sorted:
        raw_alt_candidates.extend(as_list(e.get("alt_forms")))
        if e.get("variant_uk"):
            variant_uk_candidates.append(e.get("variant_uk"))
        if e.get("variant_us"):
            variant_us_candidates.append(e.get("variant_us"))
        surface = normalize_spaces(e.get("surface_form"))
        if surface and surface.lower() != lemma:
            surface_alt_candidates.append(surface)

    primary_raw_alt_forms, primary_raw_notes = clean_alt_form_candidates(primary_raw_alt_candidates, lemma)
    raw_alt_forms, raw_alt_notes = clean_alt_form_candidates(raw_alt_candidates, lemma)
    surface_alt_forms, surface_alt_notes = clean_alt_form_candidates(surface_alt_candidates, lemma)
    variant_uk_forms, variant_uk_cleanup_notes = clean_alt_form_candidates(variant_uk_candidates, lemma)
    variant_us_forms, variant_us_cleanup_notes = clean_alt_form_candidates(variant_us_candidates, lemma)

    typed_alt_forms = (
        [(form, "primary_raw_alt_form") for form in primary_raw_alt_forms]
        + [(form, "raw_alt_form") for form in raw_alt_forms]
        + [(form, "surface_form") for form in surface_alt_forms]
        + [(form, "variant_uk") for form in variant_uk_forms]
        + [(form, "variant_us") for form in variant_us_forms]
    )
    alt_forms, semantic_fragment_notes = remove_semantic_fragment_alt_forms(typed_alt_forms, lemma)

    alt_form_cleanup_notes: List[Dict[str, Any]] = []
    alt_form_cleanup_notes.extend(primary_raw_notes)
    alt_form_cleanup_notes.extend(raw_alt_notes)
    alt_form_cleanup_notes.extend({**note, "scope": "surface_forms"} for note in surface_alt_notes)
    alt_form_cleanup_notes.extend({**note, "scope": "variant_uk_forms"} for note in variant_uk_cleanup_notes)
    alt_form_cleanup_notes.extend({**note, "scope": "variant_us_forms"} for note in variant_us_cleanup_notes)
    alt_form_cleanup_notes.extend(semantic_fragment_notes)

    surface_forms = uniq_preserve_order(normalize_spaces(e.get("surface_form")) for e in group_sorted if normalize_spaces(e.get("surface_form")))
    raw_entries = uniq_preserve_order(normalize_spaces(e.get("raw_entry")) for e in group_sorted if normalize_spaces(e.get("raw_entry")))
    raw_sections = uniq_preserve_order(e.get("raw_section") for e in group_sorted if e.get("raw_section"))
    source_ids = uniq_preserve_order(e.get("source_id") for e in group_sorted if e.get("source_id"))
    source_files = uniq_preserve_order(e.get("source_file") for e in group_sorted if e.get("source_file"))
    parser_rules = uniq_preserve_order(e.get("parser_rule") for e in group_sorted if e.get("parser_rule"))
    risk_flags = uniq_preserve_order(flag for e in group_sorted for flag in as_list(e.get("risk_flags")))

    accepted_warning_flags = sorted(set(risk_flags) & ACCEPTED_REVIEW_RISK_FLAGS)
    hard_flags = sorted(set(risk_flags) & HARD_RISK_FLAGS)

    if hard_flags:
        review_status = "blocked_by_hard_risk_flag"
        validator_accepts = False
        generator_allowed = False
    elif accepted_warning_flags:
        review_status = "auto_merged_pending_review"
        validator_accepts = True
        generator_allowed = True
    else:
        review_status = "auto_merged_clean"
        validator_accepts = True
        generator_allowed = True

    evidence_refs = [e.get("raw_id") for e in group_sorted if e.get("raw_id")]
    source_entry_refs = [e.get("entry_id") for e in group_sorted if e.get("entry_id")]

    authority_entry = {
        "authority_id": authority_id,
        "authority_version": "cambridge_yle_vocabulary_authority_v1",
        "authority_role": "vocabulary_authority_source",
        "source_role": "merged_authority_source",
        "canonical_lemma": lemma,
        "normalized_entry": lemma,
        "pos": list(pos),
        "is_multiword": any(bool(e.get("is_multiword")) for e in group_sorted) or len(lemma.split()) > 1 or "-" in lemma,
        "earliest_source_level": earliest_source_level,
        "canonical_level": earliest_canonical_level,
        "cefr_estimate": earliest_canonical_level,
        "source_priority_rank": SOURCE_LEVEL_PRIORITY.get(earliest_source_level, 999),
        "source_levels": source_levels,
        "source_level_count": len(source_levels),
        "source_ids": source_ids,
        "source_files": source_files,
        "surface_forms": surface_forms,
        "alt_forms": alt_forms,
        "alt_form_cleanup_policy_version": ALT_FORM_CLEANUP_POLICY_VERSION,
        "alt_form_cleanup_notes": alt_form_cleanup_notes,
        "variant_uk_forms": variant_uk_forms,
        "variant_us_forms": variant_us_forms,
        "guide_notes": uniq_preserve_order(e.get("guide_note") for e in group_sorted if e.get("guide_note")),
        "raw_sections": raw_sections,
        "raw_entries": raw_entries,
        "evidence_refs": evidence_refs,
        "source_entry_refs": source_entry_refs,
        "evidence_count": len(evidence_refs),
        "parser_rules": parser_rules,
        "risk_flags": risk_flags,
        "accepted_warning_flags": accepted_warning_flags,
        "hard_risk_flags": hard_flags,
        "level_policy": "earliest_source_level_wins",
        "cross_level_duplicate_policy": "merge_same_lemma_same_pos_preserve_earliest_level",
        "authority_import_allowed": True,
        "direct_use_allowed": False,
        "content_extraction_allowed": False,
        "learner_facing_allowed": False,
        "usable_for_reading": all(bool(e.get("usable_for_reading")) for e in group_sorted),
        "usable_for_dialogue": all(bool(e.get("usable_for_dialogue")) for e in group_sorted),
        "usable_for_writing": all(bool(e.get("usable_for_writing")) for e in group_sorted),
        "usable_for_assessment": all(bool(e.get("usable_for_assessment")) for e in group_sorted),
        "generator_allowed": generator_allowed,
        "validator_accepts": validator_accepts,
        "review_status": review_status,
        "child_priority": max(int(e.get("child_priority") or 0) for e in group_sorted),
        "primary_source_entry_id": primary.get("entry_id"),
        "primary_raw_id": primary.get("raw_id"),
    }

    evidence_records = [build_evidence_record(e, authority_id) for e in group_sorted]

    duplicate_note = {
        "authority_id": authority_id,
        "canonical_lemma": lemma,
        "pos": list(pos),
        "evidence_count": len(group_sorted),
        "source_levels": source_levels,
        "earliest_source_level": earliest_source_level,
        "merged": len(group_sorted) > 1,
        "evidence_raw_ids": evidence_refs,
        "surface_forms": surface_forms,
        "alt_forms": alt_forms,
        "alt_form_cleanup_policy_version": ALT_FORM_CLEANUP_POLICY_VERSION,
        "raw_entries": raw_entries,
    }

    return authority_entry, evidence_records, duplicate_note


def build_authority(entries: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    groups: Dict[Tuple[str, Tuple[str, ...]], List[Dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        lemma = normalize_spaces(entry.get("lemma")).lower()
        pos = canonical_pos_tuple(entry.get("pos"))
        groups[(lemma, pos)].append(entry)

    authority_entries: List[Dict[str, Any]] = []
    evidence_records: List[Dict[str, Any]] = []
    duplicate_notes: List[Dict[str, Any]] = []

    for (lemma, pos), group in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        authority_entry, evidence, duplicate_note = build_authority_entry(lemma, pos, group)
        authority_entries.append(authority_entry)
        evidence_records.extend(evidence)
        if duplicate_note["merged"]:
            duplicate_notes.append(duplicate_note)

    blockers = detect_authority_blockers(authority_entries, entries)
    authority_entries.sort(key=lambda e: (e["source_priority_rank"], e["canonical_lemma"], tuple(e["pos"]), e["authority_id"]))
    evidence_records.sort(key=lambda e: (e["authority_id"], e["source_priority_rank"], e.get("source_page") or 9999, e.get("raw_id") or ""))
    duplicate_notes.sort(key=lambda e: (e["canonical_lemma"], e["pos"]))

    return authority_entries, evidence_records, duplicate_notes, blockers


def detect_authority_blockers(authority_entries: List[Dict[str, Any]], input_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []

    authority_id_counter = Counter(e["authority_id"] for e in authority_entries)
    for authority_id, count in authority_id_counter.items():
        if count > 1:
            blockers.append({"type": "duplicate_authority_id", "authority_id": authority_id, "count": count})

    canonical_key_counter = Counter((e["canonical_lemma"], tuple(e["pos"])) for e in authority_entries)
    for key, count in canonical_key_counter.items():
        if count > 1:
            blockers.append({"type": "duplicate_authority_canonical_key", "canonical_lemma": key[0], "pos": list(key[1]), "count": count})

    for entry in authority_entries:
        if not entry.get("canonical_lemma"):
            blockers.append({"type": "empty_authority_lemma", "authority_id": entry.get("authority_id")})
        if not entry.get("pos"):
            blockers.append({"type": "empty_authority_pos", "authority_id": entry.get("authority_id")})
        if entry.get("hard_risk_flags"):
            blockers.append({
                "type": "authority_has_hard_risk_flags",
                "authority_id": entry.get("authority_id"),
                "canonical_lemma": entry.get("canonical_lemma"),
                "pos": entry.get("pos"),
                "hard_risk_flags": entry.get("hard_risk_flags"),
            })
        for alt in entry.get("alt_forms", []):
            if has_unmatched_parentheses(alt):
                blockers.append({
                    "type": "authority_unbalanced_alt_form",
                    "authority_id": entry.get("authority_id"),
                    "canonical_lemma": entry.get("canonical_lemma"),
                    "alt_form": alt,
                })
            if raw_slash_string_present(alt):
                blockers.append({
                    "type": "authority_alt_form_contains_slash_raw_string",
                    "authority_id": entry.get("authority_id"),
                    "canonical_lemma": entry.get("canonical_lemma"),
                    "alt_form": alt,
                })
        for field_name in ("variant_uk_forms", "variant_us_forms"):
            for value in entry.get(field_name, []):
                if raw_slash_string_present(value):
                    blockers.append({
                        "type": "authority_variant_form_contains_slash_raw_string",
                        "authority_id": entry.get("authority_id"),
                        "canonical_lemma": entry.get("canonical_lemma"),
                        "field": field_name,
                        "value": value,
                    })
        for residual in semantic_fragment_alt_form_residuals_for_entry(entry):
            blockers.append({
                "type": "authority_semantic_fragment_alt_form_residual",
                **residual,
            })

    input_raw_ids = {e.get("raw_id") for e in input_entries if e.get("raw_id")}
    authority_evidence_raw_ids = {raw_id for e in authority_entries for raw_id in e.get("evidence_refs", []) if raw_id}
    missing_raw_ids = sorted(input_raw_ids - authority_evidence_raw_ids)
    if missing_raw_ids:
        blockers.append({
            "type": "input_raw_ids_missing_from_authority_evidence",
            "count": len(missing_raw_ids),
            "sample_raw_ids": missing_raw_ids[:20],
        })

    # Same lemma but different POS sets is not a blocker, but it needs review in summary.
    lemma_to_pos_sets: Dict[str, set[Tuple[str, ...]]] = defaultdict(set)
    for e in authority_entries:
        lemma_to_pos_sets[e["canonical_lemma"]].add(tuple(e["pos"]))
    for lemma, pos_sets in sorted(lemma_to_pos_sets.items()):
        if len(pos_sets) > 1:
            # Keep as warning-style blocker with severity=review, not hard fail.
            blockers.append({
                "type": "same_lemma_multiple_pos_sets_review",
                "severity": "review",
                "canonical_lemma": lemma,
                "pos_sets": [list(pos_set) for pos_set in sorted(pos_sets)],
            })

    return blockers


def build_summary(
    authority_entries: List[Dict[str, Any]],
    evidence_records: List[Dict[str, Any]],
    duplicate_notes: List[Dict[str, Any]],
    input_entries: List[Dict[str, Any]],
    input_blockers: List[Dict[str, Any]],
    authority_blockers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    hard_authority_blockers = [b for b in authority_blockers if b.get("severity") != "review"]
    review_items = [b for b in authority_blockers if b.get("severity") == "review"]

    source_level_counts = Counter(e.get("source_level") for e in input_entries)
    authority_level_counts = Counter(e.get("earliest_source_level") for e in authority_entries)
    pos_counter = Counter(pos for entry in authority_entries for pos in entry.get("pos", []))
    risk_counter = Counter(flag for entry in authority_entries for flag in entry.get("risk_flags", []))
    accepted_warning_counter = Counter(flag for entry in authority_entries for flag in entry.get("accepted_warning_flags", []))
    input_raw_slash_alt_form_count = sum(
        1
        for entry in input_entries
        for alt in as_list(entry.get("alt_forms"))
        if raw_slash_string_present(alt)
    )
    authority_slash_alt_form_residuals = [
        {
            "authority_id": entry.get("authority_id"),
            "canonical_lemma": entry.get("canonical_lemma"),
            "alt_form": alt,
        }
        for entry in authority_entries
        for alt in entry.get("alt_forms", [])
        if raw_slash_string_present(alt)
    ]
    authority_slash_variant_form_residuals = [
        {
            "authority_id": entry.get("authority_id"),
            "canonical_lemma": entry.get("canonical_lemma"),
            "field": field_name,
            "value": value,
        }
        for entry in authority_entries
        for field_name in ("variant_uk_forms", "variant_us_forms")
        for value in entry.get(field_name, [])
        if raw_slash_string_present(value)
    ]
    authority_semantic_fragment_alt_form_residuals = [
        residual
        for entry in authority_entries
        for residual in semantic_fragment_alt_form_residuals_for_entry(entry)
    ]
    alt_form_cleanup_note_counter = Counter(
        note.get("type")
        for entry in authority_entries
        for note in entry.get("alt_form_cleanup_notes", [])
        if note.get("type")
    )

    validation_status = "PASS"
    if input_blockers or hard_authority_blockers:
        validation_status = "FAIL"
    elif review_items:
        validation_status = "PASS_WITH_REVIEW_WARNINGS"

    return {
        "validation_status": validation_status,
        "authority_version": "cambridge_yle_vocabulary_authority_v1",
        "input_entry_count": len(input_entries),
        "authority_entry_count": len(authority_entries),
        "evidence_record_count": len(evidence_records),
        "merged_duplicate_group_count": len(duplicate_notes),
        "input_blocker_count": len(input_blockers),
        "authority_hard_blocker_count": len(hard_authority_blockers),
        "authority_review_warning_count": len(review_items),
        "source_level_input_counts": dict(sorted(source_level_counts.items(), key=lambda kv: SOURCE_LEVEL_PRIORITY.get(kv[0], 999))),
        "earliest_source_level_authority_counts": dict(sorted(authority_level_counts.items(), key=lambda kv: SOURCE_LEVEL_PRIORITY.get(kv[0], 999))),
        "counts_by_pos": dict(sorted(pos_counter.items())),
        "risk_flags": dict(sorted(risk_counter.items())),
        "accepted_warning_flags": dict(sorted(accepted_warning_counter.items())),
        "alt_form_cleanup": {
            "policy_version": ALT_FORM_CLEANUP_POLICY_VERSION,
            "input_raw_slash_alt_form_count": input_raw_slash_alt_form_count,
            "authority_slash_alt_form_residual_count": len(authority_slash_alt_form_residuals),
            "authority_slash_variant_form_residual_count": len(authority_slash_variant_form_residuals),
            "authority_semantic_fragment_alt_form_residual_count": len(authority_semantic_fragment_alt_form_residuals),
            "authority_entries_with_cleanup_notes_count": sum(1 for entry in authority_entries if entry.get("alt_form_cleanup_notes")),
            "cleanup_note_counts": dict(sorted(alt_form_cleanup_note_counter.items())),
            "sample_authority_slash_alt_form_residuals": authority_slash_alt_form_residuals[:20],
            "sample_authority_slash_variant_form_residuals": authority_slash_variant_form_residuals[:20],
            "sample_authority_semantic_fragment_alt_form_residuals": authority_semantic_fragment_alt_form_residuals[:20],
        },
        "quality_gates": {
            "no_input_schema_blockers": not input_blockers,
            "no_duplicate_authority_ids": not any(b.get("type") == "duplicate_authority_id" for b in hard_authority_blockers),
            "no_duplicate_authority_canonical_keys": not any(b.get("type") == "duplicate_authority_canonical_key" for b in hard_authority_blockers),
            "no_empty_authority_lemma": not any(b.get("type") == "empty_authority_lemma" for b in hard_authority_blockers),
            "no_empty_authority_pos": not any(b.get("type") == "empty_authority_pos" for b in hard_authority_blockers),
            "all_input_raw_ids_preserved_in_evidence": not any(b.get("type") == "input_raw_ids_missing_from_authority_evidence" for b in hard_authority_blockers),
            "no_hard_risk_flags_in_authority": not any(b.get("type") == "authority_has_hard_risk_flags" for b in hard_authority_blockers),
            "no_unbalanced_authority_alt_forms": not any(b.get("type") == "authority_unbalanced_alt_form" for b in hard_authority_blockers),
            "no_raw_slash_strings_in_authority_alt_forms": not any(b.get("type") == "authority_alt_form_contains_slash_raw_string" for b in hard_authority_blockers),
            "no_raw_slash_strings_in_authority_variant_forms": not any(b.get("type") == "authority_variant_form_contains_slash_raw_string" for b in hard_authority_blockers),
            "no_semantic_fragment_authority_alt_forms": not any(b.get("type") == "authority_semantic_fragment_alt_form_residual" for b in hard_authority_blockers),
            "alt_form_cleanup_policy_applied": True,
            "earliest_source_level_policy_applied": True,
            "ulga_graph_modified": False,
            "learner_facing_content_generated": False,
        },
        "boundary_confirmation": {
            "ocr_used": False,
            "pdf_reading_used": False,
            "normalized_json_only": True,
            "authority_graph_modified": False,
            "learner_facing_content_generated": False,
            "content_extraction_allowed": False,
        },
    }


def resolve_inputs(args: argparse.Namespace) -> Tuple[Path, Path, Path]:
    input_dir = Path(args.input_dir).resolve() if args.input_dir else None

    starters = Path(args.starters).resolve() if args.starters else None
    movers = Path(args.movers).resolve() if args.movers else None
    flyers = Path(args.flyers).resolve() if args.flyers else None

    if input_dir:
        starters = starters or input_dir / "cambridge_starters_vocabulary_normalized.json"
        movers = movers or input_dir / "cambridge_movers_vocabulary_normalized.json"
        flyers = flyers or input_dir / "cambridge_flyers_vocabulary_normalized.json"

    if not starters or not movers or not flyers:
        raise ValueError("Provide either --input-dir or all of --starters --movers --flyers.")

    return starters, movers, flyers


def run(args: argparse.Namespace) -> int:
    starters, movers, flyers = resolve_inputs(args)
    out_dir = Path(args.out_dir).resolve()

    print(f"[INFO] Starters: {starters}")
    print(f"[INFO] Movers:   {movers}")
    print(f"[INFO] Flyers:   {flyers}")
    print(f"[INFO] Out dir:  {out_dir}")

    input_entries, input_blockers = load_entries(starters, movers, flyers)
    print(f"[INFO] Input normalized entries: {len(input_entries)}")
    print(f"[INFO] Input blockers: {len(input_blockers)}")

    authority_entries, evidence_records, duplicate_notes, authority_blockers = build_authority(input_entries)
    print(f"[INFO] Authority entries: {len(authority_entries)}")
    print(f"[INFO] Evidence records: {len(evidence_records)}")
    print(f"[INFO] Merged duplicate groups: {len(duplicate_notes)}")
    print(f"[INFO] Authority blockers/review items: {len(authority_blockers)}")

    summary = build_summary(
        authority_entries=authority_entries,
        evidence_records=evidence_records,
        duplicate_notes=duplicate_notes,
        input_entries=input_entries,
        input_blockers=input_blockers,
        authority_blockers=authority_blockers,
    )

    authority_out = out_dir / "cambridge_yle_vocabulary_authority_v1.json"
    evidence_out = out_dir / "cambridge_yle_vocabulary_authority_evidence_v1.json"
    summary_out = out_dir / "cambridge_yle_vocabulary_authority_summary_v1.json"
    blockers_out = out_dir / "cambridge_yle_vocabulary_authority_blockers_v1.json"
    duplicates_out = out_dir / "cambridge_yle_vocabulary_authority_duplicates_v1.json"

    write_json(authority_out, authority_entries)
    write_json(evidence_out, evidence_records)
    write_json(summary_out, summary)
    write_json(blockers_out, {
        "input_blockers": input_blockers,
        "authority_blockers_and_review_items": authority_blockers,
    })
    write_json(duplicates_out, duplicate_notes)

    print(f"[WRITE] {authority_out}")
    print(f"[WRITE] {evidence_out}")
    print(f"[WRITE] {summary_out}")
    print(f"[WRITE] {blockers_out}")
    print(f"[WRITE] {duplicates_out}")
    print(f"[RESULT] {summary['validation_status']}")

    if summary["validation_status"] == "FAIL":
        return 1
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Cambridge YLE vocabulary authority v1 from Starters/Movers/Flyers normalized JSON.")
    parser.add_argument("--input-dir", default=None, help="Directory containing all three normalized JSON files.")
    parser.add_argument("--starters", default=None, help="Path to cambridge_starters_vocabulary_normalized.json.")
    parser.add_argument("--movers", default=None, help="Path to cambridge_movers_vocabulary_normalized.json.")
    parser.add_argument("--flyers", default=None, help="Path to cambridge_flyers_vocabulary_normalized.json.")
    parser.add_argument("--out-dir", required=True, help="Output directory for merged authority artifacts.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
