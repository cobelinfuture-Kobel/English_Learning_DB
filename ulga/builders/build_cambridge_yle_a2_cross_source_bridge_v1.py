#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_cambridge_yle_a2_cross_source_bridge_v1.py

Purpose:
    Build a static/offline cross-source bridge between:
      1) Cambridge YLE vocabulary authority v1.2
      2) Cambridge A2 Key vocabulary authority candidate v1

Scope:
    - Reads existing JSON authority/evidence/summary/blocker/duplicate artifacts only.
    - Does not read PDFs.
    - Does not perform OCR.
    - Does not modify ULGA graph/runtime/dashboard/learner state.
    - Does not generate learner-facing content.
    - Does not overwrite YLE or A2 authority artifacts.
    - Produces a bridge/merge contract layer, not a final learner-facing vocabulary list.

Expected input directories:
    --yle-dir containing:
      cambridge_yle_vocabulary_authority_v1.json
      cambridge_yle_vocabulary_authority_evidence_v1.json
      cambridge_yle_vocabulary_authority_summary_v1.json
      cambridge_yle_vocabulary_authority_blockers_v1.json
      cambridge_yle_vocabulary_authority_duplicates_v1.json

    --a2-dir containing:
      cambridge_a2_key_vocabulary_authority_candidate_v1.json
      cambridge_a2_key_vocabulary_authority_evidence_v1.json
      cambridge_a2_key_vocabulary_authority_summary_v1.json
      cambridge_a2_key_vocabulary_authority_blockers_v1.json
      cambridge_a2_key_vocabulary_authority_duplicates_v1.json

Outputs:
    cambridge_yle_a2_cross_source_bridge_v1.json
    cambridge_yle_a2_cross_source_bridge_evidence_v1.json
    cambridge_yle_a2_cross_source_bridge_summary_v1.json
    cambridge_yle_a2_cross_source_bridge_conflicts_v1.json

Example:
    python build_cambridge_yle_a2_cross_source_bridge_v1.py ^
      --yle-dir "G:/HomeWork/English_Learning_DB/output/yle_authority_candidate" ^
      --a2-dir "G:/HomeWork/English_Learning_DB/output/a2_key_authority_candidate" ^
      --out-dir "G:/HomeWork/English_Learning_DB/output/yle_a2_bridge_v1"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BRIDGE_BUILDER_NAME = "build_cambridge_yle_a2_cross_source_bridge_v1.py"
BRIDGE_POLICY_VERSION = "cambridge_yle_a2_cross_source_bridge_v1"

YLE_AUTHORITY_VERSION_EXPECTED = "cambridge_yle_vocabulary_authority_v1"
A2_AUTHORITY_TYPE_EXPECTED = "cambridge_a2_key_vocabulary_authority_candidate"

YLE_FILES = {
    "authority": "cambridge_yle_vocabulary_authority_v1.json",
    "evidence": "cambridge_yle_vocabulary_authority_evidence_v1.json",
    "summary": "cambridge_yle_vocabulary_authority_summary_v1.json",
    "blockers": "cambridge_yle_vocabulary_authority_blockers_v1.json",
    "duplicates": "cambridge_yle_vocabulary_authority_duplicates_v1.json",
}

A2_FILES = {
    "authority": "cambridge_a2_key_vocabulary_authority_candidate_v1.json",
    "evidence": "cambridge_a2_key_vocabulary_authority_evidence_v1.json",
    "summary": "cambridge_a2_key_vocabulary_authority_summary_v1.json",
    "blockers": "cambridge_a2_key_vocabulary_authority_blockers_v1.json",
    "duplicates": "cambridge_a2_key_vocabulary_authority_duplicates_v1.json",
}

BRIDGE_OUT = "cambridge_yle_a2_cross_source_bridge_v1.json"
BRIDGE_EVIDENCE_OUT = "cambridge_yle_a2_cross_source_bridge_evidence_v1.json"
SUMMARY_OUT = "cambridge_yle_a2_cross_source_bridge_summary_v1.json"
CONFLICTS_OUT = "cambridge_yle_a2_cross_source_bridge_conflicts_v1.json"

PASS_STATUSES = {"PASS", "PASS_WITH_WARNINGS", "PASS_WITH_REVIEW_WARNINGS"}

SPACE_RE = re.compile(r"\s+")

# These one-token alternatives are intentionally allowed because the source
# artifact already classified them as dialect/orthographic equivalents rather
# than unsafe fragments.
ALLOWED_SINGLE_TOKEN_MULTIWORD_ALTS = {
    ("all right", "alright"),
    ("french fries", "chips"),
    ("movie theater", "cinema"),
    ("city centre", "center"),
    ("town centre", "center"),
    ("shopping centre", "center"),
    ("sports centre", "center"),
}


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


def read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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


def pos_tuple(entry: Dict[str, Any]) -> Tuple[str, ...]:
    return tuple(normalize_key(pos) for pos in safe_list(entry.get("pos")) if normalize_key(pos))


def pos_set(entry: Dict[str, Any]) -> set[str]:
    return set(pos_tuple(entry))


def canonical_key_for_authority(source_tag: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    key = {
        "source_tag": source_tag,
        "authority_id": entry.get("authority_id"),
        "canonical_lemma": entry.get("canonical_lemma"),
        "pos": list(pos_tuple(entry)),
    }
    if source_tag == "A2_KEY":
        key["guide_note_key"] = entry.get("guide_note_key", "")
    return key


def bridge_id(kind: str, payload: Dict[str, Any]) -> str:
    digest = stable_hash(json.dumps({"kind": kind, "payload": payload}, ensure_ascii=False, sort_keys=True), 14)
    return f"BRIDGE_YLE_A2_{digest}"


def evidence_id_for(bridge_record_id: str, source_authority_id: str, raw_id: str) -> str:
    digest = stable_hash(f"{bridge_record_id}|{source_authority_id}|{raw_id}", 14)
    return f"BRIDGE_EVID_YLE_A2_{digest}"


def load_side(side_name: str, directory: Path, filenames: Dict[str, str]) -> Dict[str, Any]:
    paths = {key: directory / filename for key, filename in filenames.items()}
    return {
        "side_name": side_name,
        "paths": {key: str(path) for key, path in paths.items()},
        "authority": read_json(paths["authority"]),
        "evidence": read_json(paths["evidence"]),
        "summary": read_json(paths["summary"]),
        "blockers": read_json(paths["blockers"]),
        "duplicates": read_json(paths["duplicates"]),
    }


def validate_side(side_name: str, side: Dict[str, Any]) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    authority = side.get("authority")
    evidence = side.get("evidence")
    summary = side.get("summary")

    if not isinstance(authority, list) or not authority:
        blockers.append({"type": "side_authority_not_nonempty_list", "severity": "hard", "side": side_name})
        return blockers
    if not isinstance(evidence, list) or not evidence:
        blockers.append({"type": "side_evidence_not_nonempty_list", "severity": "hard", "side": side_name})
    if not isinstance(summary, dict):
        blockers.append({"type": "side_summary_not_object", "severity": "hard", "side": side_name})
        return blockers

    status = summary.get("validation_status")
    if status not in PASS_STATUSES:
        blockers.append({"type": "side_summary_status_not_pass", "severity": "hard", "side": side_name, "status": status})

    hard_count = int(summary.get("authority_hard_blocker_count") or 0)
    input_blocker_count = int(summary.get("input_blocker_count") or 0)
    if hard_count != 0:
        blockers.append({"type": "side_authority_hard_blocker_count_nonzero", "severity": "hard", "side": side_name, "count": hard_count})
    if input_blocker_count != 0:
        blockers.append({"type": "side_input_blocker_count_nonzero", "severity": "hard", "side": side_name, "count": input_blocker_count})

    quality_gates = summary.get("quality_gates", {}) if isinstance(summary.get("quality_gates"), dict) else {}
    required_true_gates = [
        "no_duplicate_authority_ids",
        "no_duplicate_authority_canonical_keys",
        "all_input_raw_ids_preserved_in_evidence",
        "no_hard_risk_flags_in_authority",
        "all_direct_use_disallowed",
        "all_learner_facing_disallowed",
    ]
    # YLE names two slash gates differently from A2.
    slash_gates = [
        "no_raw_slash_strings_in_authority_alt_forms",
        "no_slash_residual_in_authority_alt_forms",
    ]
    semantic_gates = [
        "no_semantic_fragment_authority_alt_forms",
    ]
    for gate in required_true_gates:
        if gate in quality_gates and quality_gates.get(gate) is not True:
            blockers.append({"type": "side_quality_gate_failed", "severity": "hard", "side": side_name, "gate": gate, "value": quality_gates.get(gate)})
    if not any(quality_gates.get(gate) is True for gate in slash_gates if gate in quality_gates):
        blockers.append({"type": "side_slash_quality_gate_missing_or_failed", "severity": "hard", "side": side_name})
    if not any(quality_gates.get(gate) is True for gate in semantic_gates if gate in quality_gates):
        blockers.append({"type": "side_semantic_fragment_quality_gate_missing_or_failed", "severity": "hard", "side": side_name})

    authority_ids = [entry.get("authority_id") for entry in authority]
    if len(authority_ids) != len(set(authority_ids)):
        blockers.append({"type": "side_duplicate_authority_ids", "severity": "hard", "side": side_name})

    evidence_by_authority: Dict[str, set[str]] = defaultdict(set)
    for ev in evidence:
        evidence_by_authority[ev.get("authority_id")].add(ev.get("raw_id"))

    authority_id_set = set(authority_ids)
    evidence_missing_authority = [ev for ev in evidence if ev.get("authority_id") not in authority_id_set]
    if evidence_missing_authority:
        blockers.append({"type": "side_evidence_authority_id_missing", "severity": "hard", "side": side_name, "count": len(evidence_missing_authority), "sample": evidence_missing_authority[:5]})

    mismatches = []
    for entry in authority:
        authority_id = entry.get("authority_id")
        refs = set(entry.get("evidence_refs", []))
        if refs != evidence_by_authority.get(authority_id, set()):
            mismatches.append({"authority_id": authority_id, "expected_refs": len(refs), "actual_evidence_refs": len(evidence_by_authority.get(authority_id, set()))})
    if mismatches:
        blockers.append({"type": "side_authority_evidence_refs_mismatch", "severity": "hard", "side": side_name, "count": len(mismatches), "sample": mismatches[:5]})

    slash_alt_residuals = [
        {"authority_id": entry.get("authority_id"), "canonical_lemma": entry.get("canonical_lemma"), "alt_form": alt}
        for entry in authority
        for alt in entry.get("alt_forms", [])
        if "/" in normalize_spaces(alt)
    ]
    if slash_alt_residuals:
        blockers.append({"type": "side_slash_alt_form_residual", "severity": "hard", "side": side_name, "count": len(slash_alt_residuals), "sample": slash_alt_residuals[:10]})

    return blockers


def index_authority(authority: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_lemma: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_authority_id: Dict[str, Dict[str, Any]] = {}
    by_canonical_key: Dict[Tuple[str, Tuple[str, ...]], List[Dict[str, Any]]] = defaultdict(list)
    for entry in authority:
        lemma = normalize_key(entry.get("canonical_lemma"))
        by_lemma[lemma].append(entry)
        by_authority_id[entry.get("authority_id")] = entry
        by_canonical_key[(lemma, pos_tuple(entry))].append(entry)
    return {
        "by_lemma": by_lemma,
        "by_authority_id": by_authority_id,
        "by_canonical_key": by_canonical_key,
    }


def classify_pos_relation(yle_entry: Dict[str, Any], a2_entry: Dict[str, Any]) -> str:
    y_pos = pos_set(yle_entry)
    a_pos = pos_set(a2_entry)
    if y_pos == a_pos:
        return "exact_pos_match"
    if y_pos and a_pos and y_pos <= a_pos:
        return "yle_pos_subset_of_a2"
    if y_pos and a_pos and a_pos <= y_pos:
        return "a2_pos_subset_of_yle"
    if y_pos & a_pos:
        return "pos_overlap_review"
    return "pos_disjoint_review"


def classify_relation_type(yle_entry: Dict[str, Any], a2_entry: Dict[str, Any]) -> Tuple[str, str]:
    pos_relation = classify_pos_relation(yle_entry, a2_entry)
    guide_present = bool(a2_entry.get("guide_note_key") or a2_entry.get("guide_notes"))

    if pos_relation == "exact_pos_match" and not guide_present:
        return "same_lemma_exact_pos_equivalent", "info"
    if pos_relation == "exact_pos_match" and guide_present:
        return "same_lemma_exact_pos_a2_guide_note_preserved", "review"
    if pos_relation in {"yle_pos_subset_of_a2", "a2_pos_subset_of_yle", "pos_overlap_review"}:
        return "same_lemma_pos_overlap_review", "review"
    return "same_lemma_pos_disjoint_review", "review"


def classify_level_relation(yle_entry: Dict[str, Any], a2_entry: Dict[str, Any]) -> str:
    yle_level = normalize_spaces(yle_entry.get("canonical_level"))
    a2_level = normalize_spaces(a2_entry.get("canonical_level"))
    if yle_level in {"A2", "A2_low"} and a2_level == "A2":
        return "a2_level_alignment"
    if yle_level in {"PreA1", "A1"} and a2_level == "A2":
        return "a2_key_reconfirms_lower_level_item"
    if not yle_level or not a2_level:
        return "level_missing_review"
    return "level_progression_review"


def source_summary_for_entry(source_tag: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_tag": source_tag,
        "authority_id": entry.get("authority_id"),
        "canonical_lemma": entry.get("canonical_lemma"),
        "pos": list(pos_tuple(entry)),
        "canonical_level": entry.get("canonical_level"),
        "cefr_estimate": entry.get("cefr_estimate"),
        "source_level": entry.get("source_level") or entry.get("earliest_source_level"),
        "guide_note_key": entry.get("guide_note_key", "") if source_tag == "A2_KEY" else "",
        "guide_notes": entry.get("guide_notes", []),
        "alt_forms": entry.get("alt_forms", []),
        "risk_flags": entry.get("risk_flags", []),
        "review_status": entry.get("review_status"),
        "evidence_refs": entry.get("evidence_refs", []),
    }


def build_same_lemma_bridge_records(
    yle_authority: List[Dict[str, Any]],
    a2_authority: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    yle_index = index_authority(yle_authority)
    a2_index = index_authority(a2_authority)
    overlap_lemmas = sorted(set(yle_index["by_lemma"]) & set(a2_index["by_lemma"]))

    records: List[Dict[str, Any]] = []
    for lemma in overlap_lemmas:
        for yle_entry in sorted(yle_index["by_lemma"][lemma], key=lambda e: (pos_tuple(e), e.get("authority_id"))):
            for a2_entry in sorted(a2_index["by_lemma"][lemma], key=lambda e: (pos_tuple(e), e.get("guide_note_key", ""), e.get("authority_id"))):
                relation_type, severity = classify_relation_type(yle_entry, a2_entry)
                pos_relation = classify_pos_relation(yle_entry, a2_entry)
                level_relation = classify_level_relation(yle_entry, a2_entry)
                payload = {
                    "relation_type": relation_type,
                    "yle_authority_id": yle_entry.get("authority_id"),
                    "a2_authority_id": a2_entry.get("authority_id"),
                    "canonical_lemma": lemma,
                    "yle_pos": list(pos_tuple(yle_entry)),
                    "a2_pos": list(pos_tuple(a2_entry)),
                    "a2_guide_note_key": a2_entry.get("guide_note_key", ""),
                }
                record_id = bridge_id("same_lemma", payload)
                records.append({
                    "bridge_id": record_id,
                    "bridge_type": "cross_source_same_lemma_alignment",
                    "relation_type": relation_type,
                    "severity": severity,
                    "canonical_lemma": lemma,
                    "normalized_bridge_key": {
                        "canonical_lemma": lemma,
                        "yle_pos": list(pos_tuple(yle_entry)),
                        "a2_pos": list(pos_tuple(a2_entry)),
                        "a2_guide_note_key": a2_entry.get("guide_note_key", ""),
                    },
                    "pos_relation": pos_relation,
                    "level_relation": level_relation,
                    "guide_note_policy": "preserve_a2_guide_note_do_not_overwrite_yle" if a2_entry.get("guide_note_key") or a2_entry.get("guide_notes") else "no_a2_guide_note",
                    "source_pair": {
                        "yle": source_summary_for_entry("YLE", yle_entry),
                        "a2_key": source_summary_for_entry("A2_KEY", a2_entry),
                    },
                    "authority_merge_allowed": relation_type == "same_lemma_exact_pos_equivalent",
                    "manual_review_required": severity == "review",
                    "bridge_import_allowed": True,
                    "direct_use_allowed": False,
                    "learner_facing_allowed": False,
                })
    return records


def build_alt_collision_records(
    src_tag: str,
    dst_tag: str,
    src_authority: List[Dict[str, Any]],
    dst_authority: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    dst_index = index_authority(dst_authority)
    records: List[Dict[str, Any]] = []

    for src_entry in sorted(src_authority, key=lambda e: (normalize_key(e.get("canonical_lemma")), e.get("authority_id"))):
        src_lemma = normalize_key(src_entry.get("canonical_lemma"))
        for alt in sorted(set(normalize_key(alt) for alt in src_entry.get("alt_forms", []) if normalize_key(alt))):
            if alt == src_lemma:
                continue
            for dst_entry in dst_index["by_lemma"].get(alt, []):
                dst_lemma = normalize_key(dst_entry.get("canonical_lemma"))
                if dst_lemma == src_lemma:
                    continue
                pos_relation = classify_pos_relation(src_entry, dst_entry)
                payload = {
                    "src_tag": src_tag,
                    "dst_tag": dst_tag,
                    "src_authority_id": src_entry.get("authority_id"),
                    "dst_authority_id": dst_entry.get("authority_id"),
                    "src_canonical_lemma": src_lemma,
                    "alt_form": alt,
                    "dst_canonical_lemma": dst_lemma,
                    "src_pos": list(pos_tuple(src_entry)),
                    "dst_pos": list(pos_tuple(dst_entry)),
                }
                record_id = bridge_id("alt_collision", payload)
                records.append({
                    "bridge_id": record_id,
                    "bridge_type": "cross_source_alt_form_collision",
                    "relation_type": "alt_form_maps_to_other_source_canonical_review",
                    "severity": "review",
                    "source_direction": f"{src_tag}_ALT_TO_{dst_tag}_CANONICAL",
                    "alt_form": alt,
                    "pos_relation": pos_relation,
                    "source_pair": {
                        "source_alt_holder": source_summary_for_entry(src_tag, src_entry),
                        "target_canonical_holder": source_summary_for_entry(dst_tag, dst_entry),
                    },
                    "collision_policy": "do_not_merge_by_alt_form_without_review",
                    "manual_review_required": True,
                    "bridge_import_allowed": True,
                    "direct_use_allowed": False,
                    "learner_facing_allowed": False,
                })
    return records


def build_bridge_records(yle_authority: List[Dict[str, Any]], a2_authority: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    records.extend(build_same_lemma_bridge_records(yle_authority, a2_authority))
    records.extend(build_alt_collision_records("YLE", "A2_KEY", yle_authority, a2_authority))
    records.extend(build_alt_collision_records("A2_KEY", "YLE", a2_authority, yle_authority))

    records.sort(key=lambda r: (r.get("bridge_type"), r.get("relation_type"), r.get("canonical_lemma", r.get("alt_form", "")), r.get("bridge_id")))
    return records


def build_bridge_evidence(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for record in records:
        bridge_id_value = record.get("bridge_id")
        # Same-lemma records use source_pair. Alt-collision records use source_alt_holder/target_canonical_holder.
        source_pair = record.get("source_pair", {})
        sources = []
        if "yle" in source_pair:
            sources.append(source_pair["yle"])
        if "a2_key" in source_pair:
            sources.append(source_pair["a2_key"])
        if "source_alt_holder" in source_pair:
            sources.append(source_pair["source_alt_holder"])
        if "target_canonical_holder" in source_pair:
            sources.append(source_pair["target_canonical_holder"])

        for source in sources:
            authority_id = source.get("authority_id")
            for raw_id in source.get("evidence_refs", []):
                evidence.append({
                    "bridge_evidence_id": evidence_id_for(bridge_id_value, authority_id, raw_id),
                    "bridge_id": bridge_id_value,
                    "bridge_type": record.get("bridge_type"),
                    "relation_type": record.get("relation_type"),
                    "source_tag": source.get("source_tag"),
                    "source_authority_id": authority_id,
                    "source_canonical_lemma": source.get("canonical_lemma"),
                    "source_pos": source.get("pos"),
                    "source_canonical_level": source.get("canonical_level"),
                    "source_raw_id": raw_id,
                    "bridge_import_allowed": True,
                    "direct_use_allowed": False,
                    "learner_facing_allowed": False,
                })
    evidence.sort(key=lambda e: (e.get("bridge_id"), e.get("source_tag"), e.get("source_raw_id")))
    return evidence


def hard_bridge_blockers(records: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    bridge_ids = [record.get("bridge_id") for record in records]
    duplicate_bridge_ids = [bid for bid, count in Counter(bridge_ids).items() if bid and count > 1]
    if duplicate_bridge_ids:
        blockers.append({"type": "duplicate_bridge_ids", "severity": "hard", "count": len(duplicate_bridge_ids), "sample": duplicate_bridge_ids[:20]})

    evidence_bridge_ids = {e.get("bridge_id") for e in evidence}
    missing_evidence = [record.get("bridge_id") for record in records if record.get("bridge_id") not in evidence_bridge_ids]
    if missing_evidence:
        # Not all records necessarily need evidence? In this project, every bridge record must trace to raw evidence.
        blockers.append({"type": "bridge_records_missing_evidence", "severity": "hard", "count": len(missing_evidence), "sample": missing_evidence[:20]})

    if any(record.get("direct_use_allowed") is not False for record in records):
        blockers.append({"type": "bridge_direct_use_allowed_not_false", "severity": "hard"})
    if any(record.get("learner_facing_allowed") is not False for record in records):
        blockers.append({"type": "bridge_learner_facing_allowed_not_false", "severity": "hard"})

    return blockers


def build_conflicts(input_blockers: List[Dict[str, Any]], bridge_hard_blockers: List[Dict[str, Any]], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    review_items = [
        {
            "bridge_id": record.get("bridge_id"),
            "bridge_type": record.get("bridge_type"),
            "relation_type": record.get("relation_type"),
            "severity": record.get("severity"),
            "canonical_lemma": record.get("canonical_lemma"),
            "alt_form": record.get("alt_form"),
            "pos_relation": record.get("pos_relation"),
            "level_relation": record.get("level_relation"),
            "source_direction": record.get("source_direction"),
        }
        for record in records
        if record.get("severity") == "review"
    ]
    return {
        "builder_name": BRIDGE_BUILDER_NAME,
        "bridge_policy_version": BRIDGE_POLICY_VERSION,
        "input_blocker_count": len(input_blockers),
        "bridge_hard_blocker_count": len(bridge_hard_blockers),
        "bridge_review_warning_count": len(review_items),
        "input_blockers": input_blockers,
        "bridge_hard_blockers": bridge_hard_blockers,
        "bridge_review_items": review_items,
    }


def build_summary(
    yle_side: Dict[str, Any],
    a2_side: Dict[str, Any],
    records: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
    input_blockers: List[Dict[str, Any]],
    bridge_hard_blockers: List[Dict[str, Any]],
    conflicts: Dict[str, Any],
) -> Dict[str, Any]:
    relation_counter = Counter(record.get("relation_type") for record in records)
    bridge_type_counter = Counter(record.get("bridge_type") for record in records)
    severity_counter = Counter(record.get("severity") for record in records)
    pos_relation_counter = Counter(record.get("pos_relation") for record in records if record.get("pos_relation"))
    level_relation_counter = Counter(record.get("level_relation") for record in records if record.get("level_relation"))

    yle_auth = yle_side["authority"]
    a2_auth = a2_side["authority"]
    ylemmas = {normalize_key(entry.get("canonical_lemma")) for entry in yle_auth}
    a2lemmas = {normalize_key(entry.get("canonical_lemma")) for entry in a2_auth}
    overlap = ylemmas & a2lemmas

    validation_status = "PASS"
    if input_blockers or bridge_hard_blockers:
        validation_status = "FAIL"
    elif conflicts.get("bridge_review_warning_count", 0) > 0:
        validation_status = "PASS_WITH_REVIEW_WARNINGS"

    return {
        "validation_status": validation_status,
        "builder_name": BRIDGE_BUILDER_NAME,
        "bridge_policy_version": BRIDGE_POLICY_VERSION,
        "source_paths": {
            "yle": yle_side.get("paths"),
            "a2_key": a2_side.get("paths"),
        },
        "input_status": {
            "yle_validation_status": yle_side.get("summary", {}).get("validation_status"),
            "yle_authority_count": len(yle_auth),
            "yle_evidence_count": len(yle_side.get("evidence", [])),
            "yle_hard_blocker_count": yle_side.get("summary", {}).get("authority_hard_blocker_count"),
            "a2_validation_status": a2_side.get("summary", {}).get("validation_status"),
            "a2_authority_count": len(a2_auth),
            "a2_evidence_count": len(a2_side.get("evidence", [])),
            "a2_hard_blocker_count": a2_side.get("summary", {}).get("authority_hard_blocker_count"),
        },
        "bridge_counts": {
            "bridge_record_count": len(records),
            "bridge_evidence_record_count": len(evidence),
            "input_blocker_count": len(input_blockers),
            "bridge_hard_blocker_count": len(bridge_hard_blockers),
            "bridge_review_warning_count": conflicts.get("bridge_review_warning_count", 0),
            "yle_unique_lemma_count": len(ylemmas),
            "a2_unique_lemma_count": len(a2lemmas),
            "overlap_lemma_count": len(overlap),
            "yle_only_lemma_count": len(ylemmas - a2lemmas),
            "a2_only_lemma_count": len(a2lemmas - ylemmas),
        },
        "counts_by_bridge_type": dict(sorted(bridge_type_counter.items())),
        "counts_by_relation_type": dict(sorted(relation_counter.items())),
        "counts_by_severity": dict(sorted(severity_counter.items())),
        "counts_by_pos_relation": dict(sorted(pos_relation_counter.items())),
        "counts_by_level_relation": dict(sorted(level_relation_counter.items())),
        "quality_gates": {
            "no_input_blockers": not input_blockers,
            "no_bridge_hard_blockers": not bridge_hard_blockers,
            "no_duplicate_bridge_ids": len(records) == len({record.get("bridge_id") for record in records}),
            "all_bridge_records_have_evidence": {record.get("bridge_id") for record in records} <= {ev.get("bridge_id") for ev in evidence},
            "all_bridge_records_direct_use_disallowed": all(record.get("direct_use_allowed") is False for record in records),
            "all_bridge_records_learner_facing_disallowed": all(record.get("learner_facing_allowed") is False for record in records),
            "source_authorities_not_modified": True,
            "ulga_graph_modified": False,
            "learner_facing_content_generated": False,
        },
        "boundary_confirmation": {
            "pdf_read": False,
            "ocr_used": False,
            "input_json_only": True,
            "source_authority_files_modified": False,
            "authority_graph_modified": False,
            "learner_facing_content_generated": False,
            "content_extraction_allowed": False,
        },
    }


def run(args: argparse.Namespace) -> int:
    yle_dir = Path(args.yle_dir).resolve()
    a2_dir = Path(args.a2_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    print(f"[INFO] YLE dir: {yle_dir}")
    print(f"[INFO] A2 dir:  {a2_dir}")
    print(f"[INFO] Out dir: {out_dir}")

    yle_side = load_side("YLE", yle_dir, YLE_FILES)
    a2_side = load_side("A2_KEY", a2_dir, A2_FILES)

    input_blockers = []
    input_blockers.extend(validate_side("YLE", yle_side))
    input_blockers.extend(validate_side("A2_KEY", a2_side))

    records = build_bridge_records(yle_side["authority"], a2_side["authority"])
    evidence = build_bridge_evidence(records)
    bridge_hard_blockers = hard_bridge_blockers(records, evidence)
    conflicts = build_conflicts(input_blockers, bridge_hard_blockers, records)
    summary = build_summary(yle_side, a2_side, records, evidence, input_blockers, bridge_hard_blockers, conflicts)

    write_json(out_dir / BRIDGE_OUT, records)
    write_json(out_dir / BRIDGE_EVIDENCE_OUT, evidence)
    write_json(out_dir / SUMMARY_OUT, summary)
    write_json(out_dir / CONFLICTS_OUT, conflicts)

    print(f"[INFO] Bridge records: {len(records)}")
    print(f"[INFO] Bridge evidence records: {len(evidence)}")
    print(f"[INFO] Input blockers: {len(input_blockers)}")
    print(f"[INFO] Bridge hard blockers: {len(bridge_hard_blockers)}")
    print(f"[INFO] Bridge review warnings: {conflicts.get('bridge_review_warning_count', 0)}")
    print(f"[WRITE] {out_dir / BRIDGE_OUT}")
    print(f"[WRITE] {out_dir / BRIDGE_EVIDENCE_OUT}")
    print(f"[WRITE] {out_dir / SUMMARY_OUT}")
    print(f"[WRITE] {out_dir / CONFLICTS_OUT}")
    print(f"[RESULT] {summary['validation_status']}")

    return 0 if summary["validation_status"] in {"PASS", "PASS_WITH_REVIEW_WARNINGS"} else 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Cambridge YLE + A2 Key cross-source bridge artifacts.")
    parser.add_argument("--yle-dir", required=True, help="Directory containing the five YLE authority JSON artifacts.")
    parser.add_argument("--a2-dir", required=True, help="Directory containing the five A2 Key authority candidate JSON artifacts.")
    parser.add_argument("--out-dir", required=True, help="Output directory for YLE+A2 bridge artifacts.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
