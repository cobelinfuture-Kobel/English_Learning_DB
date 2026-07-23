#!/usr/bin/env python3
"""Map KET Complete transcript evidence to existing A1FS nodes and derive a soft sequence overlay.

The 99 transcript bundles are non-authoritative teacher-delivery references.
This implementation never creates or changes hard prerequisite edges.  Every
transcript evidence item is exhaustively disposed as a conservative canonical
match, instructional support, or review-required candidate.
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

from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as cp06  # noqa: E402
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1  # noqa: E402
from ulga.builders import build_ket_comp_transcript_final_consolidation as consolidation  # noqa: E402

TASK_ID = "A1FS-V1-CP07B_KET99CanonicalMappingAndInstructionalSequenceOverlay"
PROGRAM_ID = cp06.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.cp07b.ket99_instructional_sequence_overlay.v1"
PASS_STATUS = "PASS_CP07B_KET99_INSTRUCTIONAL_SEQUENCE_OVERLAY_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07C_UnifiedM4PlannerSelectionAndLessonComposition"

DEFAULT_CONTENT_UNITS = REPO_ROOT / "ulga/reports/ket_comp_transcript_final_consolidation/transcript_content_units.jsonl"
DEFAULT_ADMISSION = REPO_ROOT / "ulga/reports/ket_comp_transcript_final_consolidation/transcript_admission_decisions.json"
DEFAULT_M1_GRAPH = REPO_ROOT / ".local/a1fs_v1/m1/a1a1plus_prerequisite_graph_and_coverage.private.json"
DEFAULT_CP06 = cp06.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07b/ket99_instructional_sequence_overlay.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07b/ket99_instructional_sequence_overlay.validation.json"

EXPECTED_TRANSCRIPT_IDS = tuple(f"P{number:03d}" for number in range(4, 103))
ALLOWED_STAGES = {"A1", "A1_PLUS"}
ALLOWED_M1_NODE_TYPES = {"CAPABILITY", "SUPPORT_RESOURCE"}
DISPOSITIONS = ("CANONICAL_MATCH", "INSTRUCTIONAL_SUPPORT_ONLY", "REVIEW_REQUIRED")
OVERLAY_ROLES = ("FOCUS", "RECYCLE", "REVIEW", "ERROR_REPAIR", "SUPPORT")
MAX_QUERY_LIMIT = 100
FORBIDDEN_KEYS = {
    "source_text", "transcript_text", "body_text", "prompt", "scoring_contract",
    "correct_answer", "answer_key", "learner_response", "audio_bytes", "recording",
}

# Conservative semantic rules.  Targets must already exist in the 24-unit CP06 contract.
GRAMMAR_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"^(be_present_yes_no_question|be_present_short_answer)$"), "GRAMMAR_BE_INTERROGATIVES_A1", "EXACT_BE_INTERROGATIVE_LABEL"),
    (re.compile(r"^(be_present_affirmative|be_present_negative|subject_be_agreement)$"), "GRAMMAR_BE_VERB_BASIC", "EXACT_BE_FORM_LABEL"),
    (re.compile(r"^(present_simple_yes_no_question|present_simple_question|do_does_yes_no_question|do_does_question)$"), "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS", "EXACT_PRESENT_SIMPLE_QUESTION_LABEL"),
    (re.compile(r"^(present_simple_negative|present_simple_negatives|do_does_negative|do_not_does_not)$"), "GRAMMAR_PRESENT_SIMPLE_NEGATIVES", "EXACT_PRESENT_SIMPLE_NEGATIVE_LABEL"),
    (re.compile(r"^(present_simple|present_simple_affirmative|third_person_s|third_person_singular|subject_verb_agreement)$"), "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "EXACT_PRESENT_SIMPLE_LABEL"),
    (re.compile(r"^(frequency_adverbs|adverbs_of_frequency|adverb_phrase|adverb_phrases)$"), "GRAMMAR_ADVERB_PHRASES_A1", "EXACT_ADVERB_LABEL"),
    (re.compile(r"^(past_simple|past_simple_affirmative|past_simple_negative|past_simple_question|regular_past|irregular_past)$"), "GRAMMAR_PAST_SIMPLE_A1", "EXACT_PAST_SIMPLE_LABEL"),
    (re.compile(r"^(will_future|future_will|will_affirmative|will_negative|will_question)$"), "GRAMMAR_WILL_FUTURE_A1", "EXACT_WILL_FUTURE_LABEL"),
    (re.compile(r"^(because|because_clause|because_reason_clause|add_reason_with_because|give_reason_with_because)$"), "GRAMMAR_BECAUSE_REASON_CLAUSES_A1", "EXACT_BECAUSE_LABEL"),
    (re.compile(r"^(can_negative|cannot|cant|express_inability|inability_with_can)$"), "GRAMMAR_CAN_NEGATIVE_A1", "EXACT_CAN_NEGATIVE_LABEL"),
    (re.compile(r"^(can_statement|can_affirmative|can_ability|express_ability|ability_with_can)$"), "GRAMMAR_CAN_STATEMENT", "EXACT_CAN_STATEMENT_LABEL"),
    (re.compile(r"^(there_is|there_are|there_is_there_are)$"), "GRAMMAR_THERE_IS", "EXACT_THERE_IS_LABEL"),
    (re.compile(r"^(articles|article|a_an|a_an_the|definite_article|indefinite_article)$"), "GRAMMAR_ARTICLES_BASIC", "EXACT_ARTICLE_LABEL"),
    (re.compile(r"^(regular_plural|regular_plural_nouns|plural_nouns|singular_plural_nouns)$"), "GRAMMAR_REGULAR_PLURAL_NOUNS", "EXACT_PLURAL_LABEL"),
    (re.compile(r"^(subject_pronoun|subject_pronouns)$"), "GRAMMAR_SUBJECT_PRONOUNS", "EXACT_SUBJECT_PRONOUN_LABEL"),
    (re.compile(r"^(object_pronoun|object_pronouns)$"), "GRAMMAR_OBJECT_PRONOUNS_BASIC", "EXACT_OBJECT_PRONOUN_LABEL"),
    (re.compile(r"^(possessive_adjective|possessive_adjectives)$"), "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC", "EXACT_POSSESSIVE_ADJECTIVE_LABEL"),
    (re.compile(r"^(preposition_of_place|prepositions_of_place|basic_prepositions_place|in_on_under)$"), "GRAMMAR_BASIC_PREPOSITIONS_PLACE", "EXACT_PLACE_PREPOSITION_LABEL"),
    (re.compile(r"^(demonstrative|demonstratives|this_that_these_those|demonstratives_contrast)$"), "GRAMMAR_DEMONSTRATIVES_CONTRAST", "EXACT_DEMONSTRATIVE_LABEL"),
    (re.compile(r"^(adjective_phrase|adjective_phrases|adjective_order)$"), "GRAMMAR_ADJECTIVE_PHRASES_A1", "EXACT_ADJECTIVE_PHRASE_LABEL"),
    (re.compile(r"^(coordination|coordinating_conjunctions|and_or_but|add_alternative_with_or)$"), "GRAMMAR_COORDINATION_A1", "EXACT_COORDINATION_LABEL"),
    (re.compile(r"^(declarative_clause|declarative_clause_forms|statement_form)$"), "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1", "EXACT_DECLARATIVE_LABEL"),
    (re.compile(r"^(verb_complement|verb_complement_pattern|verb_complement_patterns)$"), "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1", "EXACT_VERB_COMPLEMENT_LABEL"),
    (re.compile(r"^(noun_phrase|noun_phrases)$"), "GRAMMAR_NOUN_PHRASES_A1", "EXACT_NOUN_PHRASE_LABEL"),
)

GRAMMAR_HINT_PATTERN = re.compile(
    r"(^|_)(affirmative|negative|question|short_answer|agreement|present|past|future|"
    r"article|pronoun|adjective|adverb|preposition|plural|singular|clause|conjunction|"
    r"demonstrative|complement|there_is|there_are|have_got|can|cannot|will|because)(_|$)"
)
COMMUNICATIVE_PREFIXES = (
    "ask_", "give_", "say_", "answer_", "describe_", "request_", "introduce_",
    "express_", "tell_", "talk_", "write_", "read_", "listen_", "identify_",
    "choose_", "compare_", "correct_", "complete_", "add_", "explain_",
)


class CP07BBuildError(ValueError):
    """Fail-closed transcript, admission, canonical mapping, or graph integrity error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _write_atomic(path: Path, value: Mapping[str, Any]) -> None:
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


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CP07BBuildError(f"json_object_required:{path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise CP07BBuildError(f"jsonl_object_required:{path}:{line_number}")
        rows.append(value)
    return rows


def _normalize_key(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = text.replace("’", "'").replace("can't", "cant")
    text = re.sub(r"[↔→←–—/\\+&]+", "_", text)
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _transcript_number(transcript_id: str) -> int:
    if not re.fullmatch(r"P\d{3}", transcript_id):
        raise CP07BBuildError(f"transcript_id_invalid:{transcript_id}")
    return int(transcript_id[1:])


def _assert_no_forbidden_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise CP07BBuildError(f"forbidden_content_key:{path}.{key}")
            _assert_no_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, f"{path}[{index}]")


def _verify_content_units(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CP07BBuildError("content_unit_row_invalid")
        transcript_id = str(row.get("transcript_id") or "")
        if transcript_id in by_id:
            raise CP07BBuildError(f"transcript_id_duplicate:{transcript_id}")
        _transcript_number(transcript_id)
        if row.get("authority_status") != consolidation.AUTHORITY:
            raise CP07BBuildError(f"transcript_authority_status_invalid:{transcript_id}")
        if row.get("canonical_promotion_allowed") is not False:
            raise CP07BBuildError(f"transcript_canonical_promotion_not_locked:{transcript_id}")
        if not isinstance(row.get("evidence_items"), list):
            raise CP07BBuildError(f"transcript_evidence_items_invalid:{transcript_id}")
        if not isinstance(row.get("content_roles"), list):
            raise CP07BBuildError(f"transcript_content_roles_invalid:{transcript_id}")
        source_span = row.get("source_span")
        if not isinstance(source_span, Mapping) or len(str(source_span.get("evidence_sha256") or "")) != 64:
            raise CP07BBuildError(f"transcript_source_lineage_invalid:{transcript_id}")
        by_id[transcript_id] = row
    if tuple(sorted(by_id, key=_transcript_number)) != EXPECTED_TRANSCRIPT_IDS:
        raise CP07BBuildError("transcript_identity_range_not_p004_p102")
    return [by_id[transcript_id] for transcript_id in EXPECTED_TRANSCRIPT_IDS]


def _verify_admission(artifact: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    if artifact.get("task_id") != consolidation.TASK_ID:
        raise CP07BBuildError("transcript_admission_task_id_invalid")
    if artifact.get("schema_version") != "ket.comp.transcript_admission_decisions.v1":
        raise CP07BBuildError("transcript_admission_schema_invalid")
    policy = artifact.get("global_policy")
    if not isinstance(policy, Mapping) or policy.get("canonical_promotion_allowed") is not False:
        raise CP07BBuildError("transcript_admission_global_policy_invalid")
    decisions = artifact.get("decisions")
    if not isinstance(decisions, list):
        raise CP07BBuildError("transcript_admission_decision_list_required")
    by_transcript: dict[str, Mapping[str, Any]] = {}
    denied_claims: list[str] = []
    for row in decisions:
        if not isinstance(row, Mapping):
            raise CP07BBuildError("transcript_admission_decision_row_invalid")
        if row.get("subject_type") == "content_unit":
            transcript_id = str(row.get("transcript_id") or "")
            if transcript_id in by_transcript:
                raise CP07BBuildError(f"transcript_admission_duplicate:{transcript_id}")
            decisions_map = row.get("decisions")
            requirements = row.get("requirements")
            if not isinstance(decisions_map, Mapping) or decisions_map.get("lesson_planner") != "approved_with_constraints":
                raise CP07BBuildError(f"transcript_planner_admission_invalid:{transcript_id}")
            if decisions_map.get("canonical_grammar_authority") != "denied" or decisions_map.get("canonical_vocabulary_authority") != "denied":
                raise CP07BBuildError(f"transcript_authority_denial_missing:{transcript_id}")
            if not isinstance(requirements, list) or "map_language_items_to_canonical_authorities" not in requirements:
                raise CP07BBuildError(f"transcript_mapping_requirement_missing:{transcript_id}")
            by_transcript[transcript_id] = row
        elif row.get("subject_type") == "source_claim":
            identifier = str(row.get("subject_id") or "")
            if not identifier:
                raise CP07BBuildError("denied_source_claim_identity_missing")
            denied_claims.append(identifier)
    if tuple(sorted(by_transcript, key=_transcript_number)) != EXPECTED_TRANSCRIPT_IDS:
        raise CP07BBuildError("transcript_admission_identity_range_not_p004_p102")
    required_denied = {"P093_FALSE_HOPE_WILL_CORRECTION", "P102_KET_ZHONGKAO_EQUIVALENCE"}
    if not required_denied.issubset(set(denied_claims)):
        raise CP07BBuildError("required_denied_source_claims_missing")
    return by_transcript, sorted(denied_claims)


def _verify_m1_graph(graph: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, list[str]]]:
    if graph.get("task_id") != m1.TASK_ID or graph.get("schema_version") != m1.SCHEMA_VERSION:
        raise CP07BBuildError("m1_graph_contract_invalid")
    if graph.get("validation_status") != m1.STATUS or graph.get("errors") != []:
        raise CP07BBuildError("m1_graph_not_passed")
    lock = graph.get("a2_lock_contract")
    if not isinstance(lock, Mapping) or lock.get("state") != "LOCKED_BY_DESIGN":
        raise CP07BBuildError("m1_a2_lock_invalid")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise CP07BBuildError("m1_nodes_or_edges_invalid")
    node_index: dict[str, Mapping[str, Any]] = {}
    exact_refs: defaultdict[str, list[str]] = defaultdict(list)
    for row in nodes:
        if not isinstance(row, Mapping):
            raise CP07BBuildError("m1_node_row_invalid")
        node_id = str(row.get("node_id") or "")
        if not node_id or node_id in node_index:
            raise CP07BBuildError("m1_node_identity_missing_or_duplicate")
        node_index[node_id] = row
        if row.get("node_type") in ALLOWED_M1_NODE_TYPES and row.get("level") in {"A1", "A1+"}:
            normalized = _normalize_key(row.get("source_ref"))
            if normalized:
                exact_refs[normalized].append(node_id)
    if len(node_index) != graph.get("counts", {}).get("node_count"):
        raise CP07BBuildError("m1_node_count_mismatch")
    if len(edges) != graph.get("counts", {}).get("edge_count"):
        raise CP07BBuildError("m1_edge_count_mismatch")
    return node_index, {key: sorted(value) for key, value in exact_refs.items()}


def _verify_cp06(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if artifact.get("task_id") != cp06.TASK_ID or artifact.get("schema_version") != cp06.SCHEMA_VERSION:
        raise CP07BBuildError("cp06_contract_invalid")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY" or artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        raise CP07BBuildError("cp06_scope_or_status_invalid")
    if artifact.get("coverage_summary", {}).get("existing_learning_unit_count") != 24:
        raise CP07BBuildError("cp06_existing_unit_count_not_24")
    rows = artifact.get("unit_content_capacity")
    if not isinstance(rows, list) or len(rows) != 24:
        raise CP07BBuildError("cp06_unit_capacity_count_not_24")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CP07BBuildError("cp06_unit_capacity_row_invalid")
        grammar_id = str(row.get("grammar_unit_id") or "")
        if not grammar_id or grammar_id in result or row.get("internal_stage") not in ALLOWED_STAGES:
            raise CP07BBuildError("cp06_grammar_unit_identity_or_stage_invalid")
        result[grammar_id] = row
    return result


def _grammar_match(normalized_item: str, units: Mapping[str, Mapping[str, Any]]) -> tuple[str, str] | None:
    matches = [(target, basis) for pattern, target, basis in GRAMMAR_RULES if pattern.fullmatch(normalized_item)]
    if len(matches) > 1:
        raise CP07BBuildError(f"ambiguous_grammar_rule:{normalized_item}")
    if not matches:
        return None
    target, basis = matches[0]
    if target not in units:
        raise CP07BBuildError(f"grammar_rule_target_not_in_cp06:{target}")
    return target, basis


def _support_domains(normalized_item: str, content_roles: Sequence[str]) -> list[str]:
    role_map = {
        "vocabulary": "VOCABULARY",
        "pronunciation": "PRONUNCIATION",
        "error_diagnosis": "ERROR_DIAGNOSIS",
        "remediation": "REMEDIATION",
        "teacher_delivery": "TEACHER_DELIVERY",
        "review": "REVIEW",
        "reading": "READING_STRATEGY",
        "listening": "LISTENING_STRATEGY",
        "speaking": "SPEAKING_FUNCTION",
        "writing": "WRITING_STRATEGY",
    }
    domains = {role_map[role] for role in content_roles if role in role_map}
    if normalized_item.startswith(COMMUNICATIVE_PREFIXES):
        domains.add("COMMUNICATIVE_FUNCTION")
    if "↔" in normalized_item or "pronunciation" in content_roles:
        domains.add("PRONUNCIATION")
    return sorted(domains)


def _instructional_additions(lesson_role: str, content_roles: Sequence[str], disposition: str) -> list[str]:
    roles: list[str] = []
    if disposition == "INSTRUCTIONAL_SUPPORT_ONLY":
        roles.append("SUPPORT")
    if lesson_role == "review" or "review" in content_roles:
        roles.append("REVIEW")
    if "error_diagnosis" in content_roles or "remediation" in content_roles:
        roles.append("ERROR_REPAIR")
    return roles


def build_artifact(
    content_units: Sequence[Mapping[str, Any]],
    admission_artifact: Mapping[str, Any],
    m1_graph: Mapping[str, Any],
    cp06_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    rows = _verify_content_units(content_units)
    admissions, denied_claims = _verify_admission(admission_artifact)
    m1_nodes, exact_m1_refs = _verify_m1_graph(m1_graph)
    grammar_units = _verify_cp06(cp06_artifact)

    target_seen: Counter[str] = Counter()
    target_occurrences: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    disposition_counts: Counter[str] = Counter()
    overlay_role_counts: Counter[str] = Counter()
    transcript_rows: list[dict[str, Any]] = []
    total_evidence = 0

    for row in rows:
        transcript_id = str(row["transcript_id"])
        content_roles = sorted({str(value) for value in row.get("content_roles", []) if str(value)})
        lesson_role = str(row.get("lesson_role") or "")
        evidence_occurrences: list[dict[str, Any]] = []
        for evidence_index, raw_item in enumerate(row.get("evidence_items", []), start=1):
            item = str(raw_item).strip()
            if not item:
                raise CP07BBuildError(f"empty_evidence_item:{transcript_id}:{evidence_index}")
            total_evidence += 1
            normalized = _normalize_key(item)
            if not normalized:
                raise CP07BBuildError(f"evidence_item_normalizes_empty:{transcript_id}:{evidence_index}")
            canonical_targets: list[dict[str, Any]] = []
            grammar = _grammar_match(normalized, grammar_units)
            if grammar is not None:
                grammar_id, basis = grammar
                unit = grammar_units[grammar_id]
                canonical_targets.append({
                    "target_type": "GRAMMAR_UNIT",
                    "target_id": grammar_id,
                    "learning_unit_id": str(unit["learning_unit_id"]),
                    "internal_stage": str(unit["internal_stage"]),
                    "mapping_basis": basis,
                    "mapping_confidence": "HIGH_RULE_EXACT",
                })
            for node_id in exact_m1_refs.get(normalized, []):
                node = m1_nodes[node_id]
                canonical_targets.append({
                    "target_type": "M1_NODE",
                    "target_id": node_id,
                    "skill": str(node["skill"]),
                    "level": str(node["level"]),
                    "node_type": str(node["node_type"]),
                    "mapping_basis": "EXACT_NORMALIZED_SOURCE_REF_MATCH",
                    "mapping_confidence": "HIGH_EXACT",
                })

            support_domains = _support_domains(normalized, content_roles)
            looks_grammar = bool(GRAMMAR_HINT_PATTERN.search(normalized)) or "grammar" in content_roles
            if canonical_targets:
                disposition = "CANONICAL_MATCH"
            elif support_domains and not looks_grammar:
                disposition = "INSTRUCTIONAL_SUPPORT_ONLY"
            else:
                disposition = "REVIEW_REQUIRED"
            disposition_counts[disposition] += 1

            target_role_assignments: list[dict[str, str]] = []
            roles = _instructional_additions(lesson_role, content_roles, disposition)
            for target in canonical_targets:
                key = f"{target['target_type']}:{target['target_id']}"
                role = "FOCUS" if target_seen[key] == 0 else "RECYCLE"
                target_seen[key] += 1
                roles.append(role)
                assignment = {
                    "target_type": str(target["target_type"]),
                    "target_id": str(target["target_id"]),
                    "sequence_role": role,
                }
                target_role_assignments.append(assignment)
                target_occurrences[key].append({
                    "transcript_id": transcript_id,
                    "textbook_page": row.get("textbook_page"),
                    "unit_id": str(row.get("unit_id") or ""),
                    "evidence_index": evidence_index,
                    "evidence_item": item,
                    "sequence_role": role,
                    "lesson_role": lesson_role,
                    "content_roles": content_roles,
                    "source_evidence_sha256": str(row["source_span"]["evidence_sha256"]),
                })
            roles = [role for role in OVERLAY_ROLES if role in set(roles)]
            overlay_role_counts.update(roles)
            evidence_occurrences.append({
                "evidence_occurrence_id": f"KET99:{transcript_id}:{evidence_index:02d}",
                "evidence_index": evidence_index,
                "evidence_item": item,
                "normalized_evidence_item": normalized,
                "disposition": disposition,
                "canonical_targets": canonical_targets,
                "support_domains": support_domains,
                "instructional_roles": roles,
                "target_role_assignments": target_role_assignments,
                "review_reason": (
                    "NO_HIGH_CONFIDENCE_CANONICAL_RULE_DO_NOT_INVENT_MAPPING"
                    if disposition == "REVIEW_REQUIRED"
                    else None
                ),
            })

        admission = admissions[transcript_id]
        transcript_rows.append({
            "transcript_id": transcript_id,
            "source_transcript_number": _transcript_number(transcript_id),
            "content_unit_id": str(row.get("content_unit_id") or ""),
            "textbook_page": row.get("textbook_page"),
            "unit_id": str(row.get("unit_id") or ""),
            "lesson_role": lesson_role,
            "content_roles": content_roles,
            "risk_flags": sorted({str(value) for value in row.get("risk_flags", []) if str(value)}),
            "source_lineage": {
                "source_evidence_sha256": str(row["source_span"]["evidence_sha256"]),
                "coverage_mode": str(row["source_span"].get("coverage_mode") or ""),
                "admission_id": str(admission.get("admission_id") or ""),
            },
            "planner_admission": "APPROVED_WITH_CONSTRAINTS",
            "canonical_promotion_allowed": False,
            "evidence_occurrences": evidence_occurrences,
            "evidence_disposition_counts": dict(Counter(item["disposition"] for item in evidence_occurrences)),
        })

    sequence_rollups: list[dict[str, Any]] = []
    for soft_order_rank, key in enumerate(sorted(target_occurrences, key=lambda value: (
        min(_transcript_number(row["transcript_id"]) for row in target_occurrences[value]), value
    )), start=1):
        target_type, target_id = key.split(":", 1)
        occurrences = target_occurrences[key]
        rollup: dict[str, Any] = {
            "target_type": target_type,
            "target_id": target_id,
            "soft_order_rank": soft_order_rank,
            "first_transcript_id": occurrences[0]["transcript_id"],
            "occurrence_count": len(occurrences),
            "focus_occurrence_count": sum(row["sequence_role"] == "FOCUS" for row in occurrences),
            "recycle_occurrence_count": sum(row["sequence_role"] == "RECYCLE" for row in occurrences),
            "review_occurrence_count": sum(row["lesson_role"] == "review" or "review" in row["content_roles"] for row in occurrences),
            "error_repair_occurrence_count": sum("error_diagnosis" in row["content_roles"] or "remediation" in row["content_roles"] for row in occurrences),
            "occurrences": occurrences,
        }
        if target_type == "GRAMMAR_UNIT":
            unit = grammar_units[target_id]
            rollup.update({
                "learning_unit_id": str(unit["learning_unit_id"]),
                "internal_stage": str(unit["internal_stage"]),
            })
        else:
            node = m1_nodes[target_id]
            rollup.update({
                "skill": str(node["skill"]), "level": str(node["level"]), "node_type": str(node["node_type"]),
            })
        sequence_rollups.append(rollup)

    summary = {
        "transcript_count": len(transcript_rows),
        "evidence_occurrence_count": total_evidence,
        "evidence_disposition_counts": {value: disposition_counts[value] for value in DISPOSITIONS},
        "overlay_role_assignment_counts": {value: overlay_role_counts[value] for value in OVERLAY_ROLES},
        "canonical_target_count": len(sequence_rollups),
        "grammar_unit_target_count": sum(row["target_type"] == "GRAMMAR_UNIT" for row in sequence_rollups),
        "m1_node_target_count": sum(row["target_type"] == "M1_NODE" for row in sequence_rollups),
        "transcript_identity_reconciled_count": len(transcript_rows),
        "denied_source_claim_count": len(denied_claims),
        "hard_graph_edge_count_before": int(m1_graph["counts"]["edge_count"]),
        "hard_graph_edge_count_after": int(m1_graph["counts"]["edge_count"]),
        "new_hard_prerequisite_edge_count": 0,
    }
    if sum(summary["evidence_disposition_counts"].values()) != total_evidence:
        raise CP07BBuildError("evidence_disposition_not_exhaustive")

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "metadata_only_ket99_instructional_sequence_overlay",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "transcript_content_units_sha256": _digest(list(rows)),
            "transcript_admission_decisions_sha256": _digest(admission_artifact),
            "m1_hard_graph_sha256": _digest(m1_graph),
            "cp06_unit_contract_sha256": _digest(cp06_artifact),
        },
        "authority_contract": {
            "transcript_source_role": consolidation.SOURCE_ROLE,
            "transcript_authority_status": consolidation.AUTHORITY,
            "canonical_promotion_allowed": False,
            "hard_prerequisite_authority": m1.TASK_ID,
            "hard_graph_mutation_allowed": False,
            "overlay_mode": "SOFT_ORDER_AND_SPIRAL_EVIDENCE_ONLY",
            "unmapped_evidence_policy": "REVIEW_REQUIRED_DO_NOT_INVENT_MAPPING",
            "a2_a2plus_status": "LOCKED",
        },
        "transcript_overlays": transcript_rows,
        "canonical_target_sequences": sequence_rollups,
        "denied_source_claim_ids": denied_claims,
        "coverage_summary": summary,
        "planner_overlay_gate": {
            "decision": "KET99_SOFT_SEQUENCE_OVERLAY_READY_FOR_CP07C",
            "all_99_transcript_identities_reconciled": len(transcript_rows) == 99,
            "all_evidence_occurrences_disposed": sum(disposition_counts.values()) == total_evidence,
            "hard_graph_digest_preserved": True,
            "hard_graph_edge_count_preserved": True,
            "canonical_graph_mutation_performed": False,
            "m4_planner_integration_completed": False,
        },
        "claim_boundaries": {
            "transcript_source_text_included": False,
            "canonical_grammar_authority_created": False,
            "canonical_vocabulary_authority_created": False,
            "hard_prerequisite_edge_created": False,
            "m4_planner_modified": False,
            "learner_facing_content_created": False,
            "learner_response_recorded": False,
            "mastery_or_retention_claimed": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _assert_no_forbidden_keys(artifact)
    return artifact


def query_instructional_overlay(
    artifact: Mapping[str, Any],
    *,
    transcript_id: str | None = None,
    grammar_unit_id: str | None = None,
    m1_node_id: str | None = None,
    disposition: str | None = None,
    instructional_role: str | None = None,
    content_role: str | None = None,
    level: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    if artifact.get("task_id") != TASK_ID or artifact.get("schema_version") != SCHEMA_VERSION:
        raise CP07BBuildError("overlay_contract_invalid")
    if artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        raise CP07BBuildError("overlay_not_passed")
    if level in {"A2", "A2_PLUS", "A2+"}:
        raise CP07BBuildError("A2_OVERLAY_LOCKED")
    if level is not None and level not in ALLOWED_STAGES:
        raise CP07BBuildError("query_level_invalid")
    if disposition is not None and disposition not in DISPOSITIONS:
        raise CP07BBuildError("query_disposition_invalid")
    if instructional_role is not None and instructional_role not in OVERLAY_ROLES:
        raise CP07BBuildError("query_instructional_role_invalid")
    if offset < 0 or limit < 1 or limit > MAX_QUERY_LIMIT:
        raise CP07BBuildError("query_page_invalid")
    results: list[dict[str, Any]] = []
    for transcript in artifact.get("transcript_overlays", []):
        if transcript_id is not None and transcript["transcript_id"] != transcript_id:
            continue
        if content_role is not None and content_role not in transcript["content_roles"]:
            continue
        for occurrence in transcript["evidence_occurrences"]:
            if disposition is not None and occurrence["disposition"] != disposition:
                continue
            if instructional_role is not None and instructional_role not in occurrence["instructional_roles"]:
                continue
            targets = occurrence["canonical_targets"]
            if grammar_unit_id is not None and not any(target["target_type"] == "GRAMMAR_UNIT" and target["target_id"] == grammar_unit_id for target in targets):
                continue
            if m1_node_id is not None and not any(target["target_type"] == "M1_NODE" and target["target_id"] == m1_node_id for target in targets):
                continue
            if level is not None and not any(
                (target["target_type"] == "GRAMMAR_UNIT" and target.get("internal_stage") == level)
                or (target["target_type"] == "M1_NODE" and _normalize_key(target.get("level")) == _normalize_key(level))
                for target in targets
            ):
                continue
            results.append({
                "transcript_id": transcript["transcript_id"],
                "textbook_page": transcript["textbook_page"],
                "unit_id": transcript["unit_id"],
                "lesson_role": transcript["lesson_role"],
                "content_roles": transcript["content_roles"],
                **occurrence,
            })
    page = results[offset:offset + limit]
    return {
        "query_status": "PASS_CP07B_KET99_INSTRUCTIONAL_OVERLAY_QUERY",
        "total_match_count": len(results),
        "offset": offset,
        "limit": limit,
        "returned_count": len(page),
        "evidence_occurrences": page,
        "hard_prerequisite_graph_modified": False,
        "a2_overlay_included": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--content-units", type=Path, default=DEFAULT_CONTENT_UNITS)
    build.add_argument("--admission", type=Path, default=DEFAULT_ADMISSION)
    build.add_argument("--m1-graph", type=Path, default=DEFAULT_M1_GRAPH)
    build.add_argument("--cp06", type=Path, default=DEFAULT_CP06)
    build.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    build.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    query = commands.add_parser("query")
    query.add_argument("--overlay", type=Path, required=True)
    for name in ("transcript-id", "grammar-unit-id", "m1-node-id", "disposition", "instructional-role", "content-role", "level"):
        query.add_argument(f"--{name}")
    query.add_argument("--offset", type=int, default=0)
    query.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            content_units = _read_jsonl(args.content_units)
            admission = _read_json(args.admission)
            m1_graph = _read_json(args.m1_graph)
            cp06_artifact = _read_json(args.cp06)
            artifact = build_artifact(content_units, admission, m1_graph, cp06_artifact)
            from ulga.validators import validate_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as validator
            report = validator.validate_artifact(
                artifact,
                content_units=content_units,
                admission_artifact=admission,
                m1_graph=m1_graph,
                cp06_artifact=cp06_artifact,
            )
            _write_atomic(args.output, artifact)
            _write_atomic(args.report, report)
            shown = report
            exit_code = 0 if report["validation_status"] == PASS_STATUS else 1
        else:
            shown = query_instructional_overlay(
                _read_json(args.overlay),
                transcript_id=args.transcript_id,
                grammar_unit_id=args.grammar_unit_id,
                m1_node_id=args.m1_node_id,
                disposition=args.disposition,
                instructional_role=args.instructional_role,
                content_role=args.content_role,
                level=args.level,
                offset=args.offset,
                limit=args.limit,
            )
            exit_code = 0
        print(json.dumps(shown, ensure_ascii=False, sort_keys=True))
        return exit_code
    except (CP07BBuildError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
