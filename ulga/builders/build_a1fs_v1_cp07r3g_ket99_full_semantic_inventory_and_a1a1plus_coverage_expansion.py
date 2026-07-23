#!/usr/bin/env python3
"""Inventory all KET99 transcripts and expand optional A1/A1+ lesson references.

The builder consumes existing CP07B evidence metadata and private M1/M2 identities.
It uses closed semantic-taxonomy rules and exact identities only. It never copies
transcript prose or private payloads into the output, mutates M1, selects lessons,
or unlocks A2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b  # noqa: E402
from ulga.builders import build_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as r3e  # noqa: E402
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only full KET99 semantic inventory and optional lesson-reference expansion over existing CP07B, M1, M2, and R3E identities; no transcript text, private payload, prompt, answer, score, learner response, media, hard edge, lesson selection, mastery, retention, or A2 payload is produced."

TASK_ID = "A1FS-V1-CP07F-R3G_KET99FullSemanticInventoryAndA1A1PlusCoverageExpansion"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3g.ket99_full_semantic_inventory_a1a1plus_coverage_expansion.v1"
PASS_STATUS = "PASS_CP07F_R3G_KET99_FULL_SEMANTIC_INVENTORY_AND_A1A1PLUS_COVERAGE_EXPANSION_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R3H_KET99CoverageConsumerRefresh"

DEFAULT_M1 = r3e.DEFAULT_M1
DEFAULT_M2 = r3e.DEFAULT_M2
DEFAULT_CP07B = r3e.DEFAULT_CP07B
DEFAULT_R3E = r3e.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r3g/ket99_full_semantic_inventory_and_coverage_expansion.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r3g/ket99_full_semantic_inventory_and_coverage_expansion.validation.json"

SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
LEVELS = {"A1", "A1+"}
DISPOSITIONS = (
    "USED_FOR_A1_A1PLUS",
    "A2_ONLY",
    "NO_RELEVANT_PEDAGOGICAL_CONTENT",
    "HUMAN_EVIDENCE_REQUIRED",
)
FORBIDDEN_KEYS = {
    "payload", "source_content", "text", "prompt", "scoring_contract",
    "correct_answer", "answer_key", "learner_response", "transcript_text",
    "speaker_turns", "audio_bytes", "recording", "evidence_item",
}

DOMAIN_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PERSONAL_INFORMATION", re.compile(r"(^|_)(name|age|origin|personal_information|nice_to_meet_you|introduce)(_|$)")),
    ("FAMILY_RELATIONSHIPS", re.compile(r"(^|_)(family|aunt|brother|cousin|daughter|son|mother|father|parent|grand)(_|$)")),
    ("NUMBERS_TIME_DATE", re.compile(r"(^|_)(number|date|time|clock|quarter|half|thirteen|thirty|fourteen|forty|fifteen|fifty|sixteen|sixty|seventeen|seventy)(_|$)")),
    ("HOME_AND_PLACES", re.compile(r"(^|_)(home|house|villa|flat|apartment|room|place|location)(_|$)")),
    ("FOOD_AND_DRINK", re.compile(r"(^|_)(food|drink|cereal|sausage|egg|cheese|cake|restaurant)(_|$)")),
    ("SHOPPING_AND_CLOTHES", re.compile(r"(^|_)(shop|shopping|clothing|clothes|fashion|changing_room|fitting_room|expensive|cheap)(_|$)")),
    ("DAILY_ROUTINE_AND_FREQUENCY", re.compile(r"(^|_)(daily|routine|frequency|always|usually|often|sometimes|never)(_|$)")),
    ("MESSAGES_AND_NOTICES", re.compile(r"(^|_)(email|message|text_message|notice|note|invitation|party_message)(_|$)")),
    ("READING_DETAIL_LOCATION", re.compile(r"(^|_)(keyword|paragraph|detail|location|cloze|gap|article|multiple_choice|single_best_answer|sequential_question)(_|$)")),
    ("LISTENING_DETAIL_EXTRACTION", re.compile(r"(^|_)(listen|audio|sound|speaker|monologue|gap_completion|information_form|matching_people)(_|$)")),
    ("SPEAKING_INTERACTION", re.compile(r"(^|_)(paired|interaction|discussion|opinion|examiner|full_sentence|answer_expansion|shared_question)(_|$)")),
    ("WRITING_PRODUCTION", re.compile(r"(^|_)(write|writing|email_register|full_sentence|give_three|answer_topic)(_|$)")),
    ("ERROR_REPAIR", re.compile(r"(^|_)(error|incorrect|correction|correct|negative_then_positive|discrimination)(_|$)")),
    ("PRONUNCIATION", re.compile(r"(^|_)(pronunciation|sound|stress|syllable)(_|$)")),
    ("QUESTION_AND_ANSWER", re.compile(r"(^|_)(ask|answer|question|short_answer|yes_no)(_|$)")),
)

A2_ONLY_RULES = (
    re.compile(r"(^|_)(present_perfect|past_continuous|first_conditional|relative_clause|passive_voice)(_|$)"),
)

ROLE_DOMAINS = {
    "listening": "LISTENING_SKILL",
    "speaking": "SPEAKING_SKILL",
    "reading": "READING_SKILL",
    "writing": "WRITING_SKILL",
    "grammar": "GRAMMAR_SYSTEM",
    "vocabulary": "VOCABULARY_SYSTEM",
    "pronunciation": "PRONUNCIATION",
    "error_diagnosis": "ERROR_REPAIR",
    "remediation": "ERROR_REPAIR",
    "review": "REVIEW_SUPPORT",
}

SKILL_ROLE_DOMAIN = {
    "LISTENING": "LISTENING_SKILL",
    "SPEAKING": "SPEAKING_SKILL",
    "READING": "READING_SKILL",
    "WRITING": "WRITING_SKILL",
}

TOPIC_DOMAINS = {
    "PERSONAL_INFORMATION", "FAMILY_RELATIONSHIPS", "NUMBERS_TIME_DATE",
    "HOME_AND_PLACES", "FOOD_AND_DRINK", "SHOPPING_AND_CLOTHES",
    "DAILY_ROUTINE_AND_FREQUENCY", "MESSAGES_AND_NOTICES",
}

STRATEGY_DOMAIN = {
    "LISTENING": "LISTENING_DETAIL_EXTRACTION",
    "SPEAKING": "SPEAKING_INTERACTION",
    "READING": "READING_DETAIL_LOCATION",
    "WRITING": "WRITING_PRODUCTION",
}


class R3GError(ValueError):
    """Fail-closed source identity or semantic inventory error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise R3GError(f"json_object_required:{path}")
    return value


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def normalize(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("’", "'").replace("can't", "cant")
    text = re.sub(r"[↔→←–—/\\+&]+", "_", text)
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def tokens(value: str) -> set[str]:
    return {token for token in value.split("_") if len(token) >= 3}


def domains(normalized: str, roles: Sequence[str], support: Sequence[str]) -> set[str]:
    result = {str(value) for value in support if str(value)}
    result.update(ROLE_DOMAINS[role] for role in roles if role in ROLE_DOMAINS)
    for domain, pattern in DOMAIN_RULES:
        if pattern.search(normalized):
            result.add(domain)
    return result


def walk_scalars(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, Mapping):
        for child in value.values():
            result.extend(walk_scalars(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(walk_scalars(child))
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value).strip()
        if text:
            result.append(text)
    return result


def verify_sources(
    graph: Mapping[str, Any],
    consumer: Mapping[str, Any],
    overlay: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if graph.get("task_id") != m1.TASK_ID or graph.get("schema_version") != m1.SCHEMA_VERSION:
        raise R3GError("m1_contract_invalid")
    if graph.get("validation_status") != m1.STATUS or graph.get("errors") != []:
        raise R3GError("m1_not_passed")
    if graph.get("a2_lock_contract", {}).get("state") != "LOCKED_BY_DESIGN":
        raise R3GError("m1_a2_lock_invalid")

    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise R3GError("m2_contract_invalid")
    if consumer.get("validation_status") != m2.STATUS or consumer.get("errors") != []:
        raise R3GError("m2_not_passed")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise R3GError("m2_a2_lock_invalid")

    if overlay.get("task_id") != cp07b.TASK_ID or overlay.get("schema_version") != cp07b.SCHEMA_VERSION:
        raise R3GError("cp07b_contract_invalid")
    if overlay.get("stop_reason") != "NONE" or overlay.get("errors") != []:
        raise R3GError("cp07b_not_passed")
    if overlay.get("coverage_summary", {}).get("transcript_count") != 99:
        raise R3GError("cp07b_transcript_count_not_99")
    if overlay.get("source_identity", {}).get("m1_hard_graph_sha256") != digest(graph):
        raise R3GError("cp07b_m1_binding_invalid")

    if baseline.get("task_id") != r3e.TASK_ID or baseline.get("schema_version") != r3e.SCHEMA_VERSION:
        raise R3GError("r3e_contract_invalid")
    if baseline.get("validation_status") != r3e.PASS_STATUS or baseline.get("stop_reason") != "NONE" or baseline.get("errors") != []:
        raise R3GError("r3e_not_passed")
    expected = {
        "m1_hard_graph_sha256": digest(graph),
        "m2_consumer_sha256": digest(consumer),
        "cp07b_instructional_overlay_sha256": digest(overlay),
    }
    for key, value in expected.items():
        if baseline.get("source_identity", {}).get(key) != value:
            raise R3GError(f"r3e_source_identity_mismatch:{key}")

    lessons = [row for row in consumer.get("lesson_catalog", []) if isinstance(row, Mapping) and row.get("level") in LEVELS]
    if len(lessons) != consumer.get("counts", {}).get("learning_lesson_count"):
        raise R3GError("learning_lesson_count_mismatch")
    lesson_ids = [str(row.get("lesson_id") or "") for row in lessons]
    if any(not value for value in lesson_ids) or len(set(lesson_ids)) != len(lesson_ids):
        raise R3GError("lesson_identity_invalid")

    nodes = {str(row.get("node_id") or ""): row for row in graph.get("nodes", []) if isinstance(row, Mapping) and str(row.get("node_id") or "")}
    assets = {str(row.get("asset_key") or ""): row for row in consumer.get("asset_records", []) if isinstance(row, Mapping) and str(row.get("asset_key") or "")}
    if len(assets) != len(consumer.get("asset_records", [])):
        raise R3GError("m2_asset_identity_invalid")
    return lessons, nodes, assets


def lesson_profiles(
    lessons: Sequence[Mapping[str, Any]],
    nodes: Mapping[str, Mapping[str, Any]],
    assets: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for lesson in lessons:
        lesson_id = str(lesson["lesson_id"])
        atoms: set[str] = set()
        semantic_domains = {SKILL_ROLE_DOMAIN[str(lesson["skill"])]}
        requirement_ids = sorted({str(value) for value in lesson.get("requirement_node_ids", []) if str(value)})
        for requirement_id in requirement_ids:
            node = nodes.get(requirement_id)
            if node is None:
                raise R3GError(f"lesson_requirement_node_missing:{lesson_id}:{requirement_id}")
            normalized = normalize(node.get("source_ref"))
            if normalized:
                atoms.add(normalized)
                atoms.update(tokens(normalized))
                semantic_domains.update(domains(normalized, [], []))
        for asset_key in lesson.get("asset_keys", []):
            asset = assets.get(str(asset_key))
            if asset is None:
                raise R3GError(f"lesson_asset_missing:{lesson_id}:{asset_key}")
            for scalar in walk_scalars(asset.get("payload")):
                normalized = normalize(scalar)
                if normalized:
                    atoms.add(normalized)
                    atoms.update(tokens(normalized))
                    semantic_domains.update(domains(normalized, [], []))
        result[lesson_id] = {
            "skill": str(lesson["skill"]),
            "semantic_atoms": atoms,
            "semantic_domains": semantic_domains,
            "requirement_node_ids": requirement_ids,
        }
    return result


def baseline_references(baseline: Mapping[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    result: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for lesson in baseline.get("lesson_instructional_references", []):
        if not isinstance(lesson, Mapping):
            continue
        lesson_id = str(lesson.get("lesson_id") or "")
        for reference in lesson.get("instructional_references", []):
            if not isinstance(reference, Mapping):
                continue
            occurrence_id = str(reference.get("evidence_occurrence_id") or "")
            result[lesson_id][occurrence_id] = {
                "evidence_occurrence_id": occurrence_id,
                "transcript_id": str(reference.get("transcript_id") or ""),
                "source_evidence_sha256": str(reference.get("source_evidence_sha256") or ""),
                "instructional_roles": sorted({str(value) for value in reference.get("instructional_roles", []) if str(value)}),
                "canonical_target_refs": sorted(
                    [
                        {"target_type": str(target.get("target_type") or ""), "target_id": str(target.get("target_id") or "")}
                        for target in reference.get("canonical_target_refs", [])
                        if isinstance(target, Mapping) and str(target.get("target_type") or "") and str(target.get("target_id") or "")
                    ], key=lambda target: (target["target_type"], target["target_id"]),
                ),
                "semantic_domains": [],
                "mapping_basis": ["BASELINE_R3E_REFERENCE"],
                "runtime_effect": "OPTIONAL_TEACHING_REFERENCE_ONLY",
            }
    return dict(result)


def build_artifact(
    graph: Mapping[str, Any],
    consumer: Mapping[str, Any],
    overlay: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    lessons, nodes, assets = verify_sources(graph, consumer, overlay, baseline)
    profiles = lesson_profiles(lessons, nodes, assets)
    references: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    transcript_lessons: defaultdict[str, set[str]] = defaultdict(set)

    for lesson_id, rows in baseline_references(baseline).items():
        for occurrence_id, reference in rows.items():
            references[lesson_id][occurrence_id] = reference
            transcript_lessons[reference["transcript_id"]].add(lesson_id)

    inventory: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    transcript_rows = overlay.get("transcript_overlays")
    if not isinstance(transcript_rows, list) or len(transcript_rows) != 99:
        raise R3GError("cp07b_transcript_rows_not_99")

    for transcript in sorted(transcript_rows, key=lambda row: str(row.get("transcript_id") or "")):
        if not isinstance(transcript, Mapping):
            raise R3GError("cp07b_transcript_row_invalid")
        transcript_id = str(transcript.get("transcript_id") or "")
        roles = sorted({str(value) for value in transcript.get("content_roles", []) if str(value)})
        risk_flags = sorted({str(value) for value in transcript.get("risk_flags", []) if str(value)})
        source_sha = str(transcript.get("source_lineage", {}).get("source_evidence_sha256") or "")
        transcript_domains: set[str] = set()
        transcript_atoms: set[str] = set()
        review_count = 0
        support_count = 0
        a2_only_count = 0
        occurrence_count = 0

        for occurrence in transcript.get("evidence_occurrences", []):
            if not isinstance(occurrence, Mapping):
                raise R3GError(f"cp07b_occurrence_invalid:{transcript_id}")
            occurrence_id = str(occurrence.get("evidence_occurrence_id") or "")
            normalized = normalize(occurrence.get("normalized_evidence_item"))
            if not occurrence_id or not normalized:
                raise R3GError(f"cp07b_occurrence_identity_invalid:{transcript_id}")
            occurrence_count += 1
            atom_set = {normalized} | tokens(normalized)
            domain_set = domains(normalized, roles, occurrence.get("support_domains", []))
            target_refs = sorted(
                [
                    {"target_type": str(target.get("target_type") or ""), "target_id": str(target.get("target_id") or "")}
                    for target in occurrence.get("canonical_targets", [])
                    if isinstance(target, Mapping) and str(target.get("target_type") or "") and str(target.get("target_id") or "")
                ], key=lambda target: (target["target_type"], target["target_id"]),
            )
            disposition = str(occurrence.get("disposition") or "")
            review_count += int(disposition == "REVIEW_REQUIRED")
            support_count += int(disposition == "INSTRUCTIONAL_SUPPORT_ONLY")
            a2_only_count += int(any(pattern.search(normalized) for pattern in A2_ONLY_RULES))
            transcript_atoms.update(atom_set)
            transcript_domains.update(domain_set)
            occurrences.append({
                "evidence_occurrence_id": occurrence_id,
                "transcript_id": transcript_id,
                "source_evidence_sha256": source_sha,
                "normalized_semantic_atom_sha256": digest(normalized),
                "semantic_atoms": sorted(atom_set),
                "semantic_domains": sorted(domain_set),
                "canonical_target_refs": target_refs,
                "instructional_roles": sorted({str(value) for value in occurrence.get("instructional_roles", []) if str(value)}),
            })

        inventory.append({
            "transcript_id": transcript_id,
            "content_unit_id": str(transcript.get("content_unit_id") or ""),
            "unit_id": str(transcript.get("unit_id") or ""),
            "lesson_role": str(transcript.get("lesson_role") or ""),
            "content_roles": roles,
            "risk_flags": risk_flags,
            "source_evidence_sha256": source_sha,
            "semantic_domains": sorted(transcript_domains),
            "semantic_atom_count": len(transcript_atoms),
            "evidence_occurrence_count": occurrence_count,
            "review_required_evidence_count": review_count,
            "instructional_support_evidence_count": support_count,
            "a2_only_evidence_count": a2_only_count,
        })

    for occurrence in occurrences:
        atom_set = set(occurrence["semantic_atoms"])
        domain_set = set(occurrence["semantic_domains"])
        m1_targets = {target["target_id"] for target in occurrence["canonical_target_refs"] if target["target_type"] == "M1_NODE"}
        grammar_targets = {target["target_id"] for target in occurrence["canonical_target_refs"] if target["target_type"] == "GRAMMAR_UNIT"}
        grammar_tokens = set().union(*(tokens(normalize(target)) - {"grammar", "basic"} for target in grammar_targets)) if grammar_targets else set()

        for lesson_id, profile in profiles.items():
            bases: set[str] = set()
            profile_atoms = set(profile["semantic_atoms"])
            profile_domains = set(profile["semantic_domains"])
            skill = profile["skill"]
            if m1_targets & set(profile["requirement_node_ids"]):
                bases.add("EXACT_CP07B_M1_NODE_TARGET")
            if grammar_tokens and len(grammar_tokens & profile_atoms) >= 2:
                bases.add("CONTROLLED_CANONICAL_GRAMMAR_TOKEN_MATCH")
            if atom_set & profile_atoms:
                bases.add("EXACT_NORMALIZED_SEMANTIC_ATOM")
            compatible = domain_set & profile_domains
            if compatible & TOPIC_DOMAINS and SKILL_ROLE_DOMAIN[skill] in domain_set:
                bases.add("CONTROLLED_TOPIC_DOMAIN_AND_SKILL")
            if STRATEGY_DOMAIN[skill] in domain_set:
                bases.add("CONTROLLED_STRATEGY_DOMAIN_AND_SKILL")
            if not bases:
                continue
            occurrence_id = occurrence["evidence_occurrence_id"]
            reference = {
                "evidence_occurrence_id": occurrence_id,
                "transcript_id": occurrence["transcript_id"],
                "source_evidence_sha256": occurrence["source_evidence_sha256"],
                "instructional_roles": occurrence["instructional_roles"],
                "canonical_target_refs": occurrence["canonical_target_refs"],
                "semantic_domains": sorted(compatible),
                "mapping_basis": sorted(bases),
                "runtime_effect": "OPTIONAL_TEACHING_REFERENCE_ONLY",
            }
            current = references[lesson_id].get(occurrence_id)
            if current is None:
                references[lesson_id][occurrence_id] = reference
            else:
                current["mapping_basis"] = sorted(set(current["mapping_basis"]) | bases)
                current["semantic_domains"] = sorted(set(current.get("semantic_domains", [])) | compatible)
            transcript_lessons[occurrence["transcript_id"]].add(lesson_id)

    skill_summary = {
        skill: {"lesson_count": 0, "referenced_lesson_count": 0, "unreferenced_lesson_count": 0, "instructional_reference_count": 0}
        for skill in SKILLS
    }
    lesson_rows: list[dict[str, Any]] = []
    for lesson in sorted(lessons, key=lambda row: (str(row.get("skill") or ""), str(row.get("level") or ""), str(row.get("lesson_id") or ""))):
        lesson_id = str(lesson["lesson_id"])
        skill = str(lesson["skill"])
        lesson_refs = sorted(references[lesson_id].values(), key=lambda row: (row["transcript_id"], row["evidence_occurrence_id"]))
        skill_summary[skill]["lesson_count"] += 1
        skill_summary[skill]["referenced_lesson_count"] += int(bool(lesson_refs))
        skill_summary[skill]["unreferenced_lesson_count"] += int(not lesson_refs)
        skill_summary[skill]["instructional_reference_count"] += len(lesson_refs)
        lesson_rows.append({
            "lesson_id": lesson_id,
            "lesson_node_id": str(lesson.get("lesson_node_id") or ""),
            "skill": skill,
            "level": str(lesson.get("level") or ""),
            "requirement_node_ids": sorted({str(value) for value in lesson.get("requirement_node_ids", []) if str(value)}),
            "reference_status": "REFERENCED" if lesson_refs else "NO_EXACT_OR_CONTROLLED_KET99_REFERENCE",
            "instructional_references": lesson_refs,
            "delivery_blocked_by_missing_reference": False,
            "hard_lesson_selection_changed": False,
        })

    disposition_counts: Counter[str] = Counter()
    for row in inventory:
        lesson_ids = sorted(transcript_lessons.get(row["transcript_id"], set()))
        if lesson_ids:
            disposition = "USED_FOR_A1_A1PLUS"
        elif row["semantic_atom_count"] == 0:
            disposition = "NO_RELEVANT_PEDAGOGICAL_CONTENT"
        elif row["evidence_occurrence_count"] > 0 and row["a2_only_evidence_count"] == row["evidence_occurrence_count"]:
            disposition = "A2_ONLY"
        else:
            disposition = "HUMAN_EVIDENCE_REQUIRED"
        row["disposition"] = disposition
        row["referenced_lesson_count"] = len(lesson_ids)
        row["referenced_skills"] = sorted({profiles[lesson_id]["skill"] for lesson_id in lesson_ids})
        disposition_counts[disposition] += 1

    referenced_lessons = sum(bool(row["instructional_references"]) for row in lesson_rows)
    referenced_transcripts = sum(row["disposition"] == "USED_FOR_A1_A1PLUS" for row in inventory)
    baseline_summary = baseline.get("coverage_summary", {})
    coverage_summary = {
        "learning_lesson_count": len(lesson_rows),
        "referenced_lesson_count": referenced_lessons,
        "unreferenced_lesson_count": len(lesson_rows) - referenced_lessons,
        "instructional_reference_count": sum(len(row["instructional_references"]) for row in lesson_rows),
        "transcript_count": len(inventory),
        "referenced_transcript_count": referenced_transcripts,
        "unused_transcript_count": len(inventory) - referenced_transcripts,
        "transcript_disposition_counts": {value: disposition_counts[value] for value in DISPOSITIONS},
        "baseline_referenced_lesson_count": int(baseline_summary.get("referenced_lesson_count", 0)),
        "baseline_referenced_transcript_count": int(baseline_summary.get("referenced_transcript_count", 0)),
        "referenced_lesson_delta": referenced_lessons - int(baseline_summary.get("referenced_lesson_count", 0)),
        "referenced_transcript_delta": referenced_transcripts - int(baseline_summary.get("referenced_transcript_count", 0)),
        "hard_graph_edge_delta": 0,
        "blocked_lesson_count": 0,
    }

    artifact = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_ket99_full_semantic_inventory_and_a1a1plus_coverage_expansion",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m1_hard_graph_sha256": digest(graph),
            "m2_consumer_sha256": digest(consumer),
            "cp07b_instructional_overlay_sha256": digest(overlay),
            "r3e_baseline_sha256": digest(baseline),
        },
        "authority_contract": {
            "source_role": "NON_AUTHORITATIVE_KET_TEACHER_DELIVERY_REFERENCE",
            "mapping_model": "CONTROLLED_MULTI_DOMAIN_EXACT_TAXONOMY",
            "free_form_fuzzy_matching_allowed": False,
            "generic_teacher_delivery_role_sufficient_for_mapping": False,
            "hard_graph_mutation_allowed": False,
            "hard_lesson_selection_allowed": False,
            "mastery_gate_creation_allowed": False,
            "delivery_block_on_missing_reference_allowed": False,
            "a2_a2plus_status": "LOCKED",
        },
        "transcript_semantic_inventory": inventory,
        "lesson_instructional_references": lesson_rows,
        "skill_coverage_summary": skill_summary,
        "coverage_summary": coverage_summary,
        "claim_boundaries": {
            "transcript_text_included": False,
            "private_payload_included": False,
            "new_canonical_authority_created": False,
            "hard_prerequisite_changed": False,
            "lesson_selection_changed": False,
            "mastery_or_retention_claimed": False,
            "learner_delivery_completed": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    walk_forbidden(artifact)
    return artifact


def walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise R3GError(f"private_or_text_key_forbidden:{path}.{key}")
            walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_forbidden(child, f"{path}[{index}]")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1-graph", type=Path, default=DEFAULT_M1)
    parser.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    parser.add_argument("--cp07b-overlay", type=Path, default=DEFAULT_CP07B)
    parser.add_argument("--r3e-baseline", type=Path, default=DEFAULT_R3E)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        graph, consumer = read(args.m1_graph), read(args.m2_consumer)
        overlay, baseline = read(args.cp07b_overlay), read(args.r3e_baseline)
        artifact = build_artifact(graph, consumer, overlay, baseline)
        from ulga.validators import validate_a1fs_v1_cp07r3g_ket99_full_semantic_inventory_and_a1a1plus_coverage_expansion as validator
        report = validator.validate_artifact(
            artifact,
            m1_graph=graph,
            m2_consumer=consumer,
            cp07b_overlay=overlay,
            r3e_baseline=baseline,
        )
        write(args.output, artifact)
        write(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (R3GError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
