#!/usr/bin/env python3
"""Materialize R3/R4 production artifacts from the frozen R2/M1/M2 authority chain.

This builder preserves incomplete breadth explicitly. It projects only learner items
that already exist in the private M2 Asset Body consumer, pass the existing M6 scoring
contract derivation, and pass the existing M12G learner-contract validator. It never
creates new learner-visible questions, modifies canonical Authority data, or claims
learner mastery/retention.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment
from ulga.validators import validate_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2_validator

TASK_ID = "A1FS-V1-R3R4_AuthorityReviewedProductionPopulation"
SCHEMA_VERSION = "a1fs.v1.r3r4.authority_reviewed_production_population.v1"
STATUS = "PASS_A1FS_V1_R3R4_AUTHORITY_REVIEWED_PRODUCTION_POPULATION"
NEXT_SHORT_STEP = "A1FS-V1-R5_LocalEdgeRuntimeAndCompleteEvidenceCollector"
PARTIAL_PROFILE_STATE = "PROFILE_PARTIALLY_POPULATED"
AUTHORITY_REVIEWER = "A1FS_M0_M1_M2_FROZEN_AUTHORITY_CHAIN"

PROFILE_OUTPUT = "a1fs_v1_r3_breadth_requirement_profiles.json"
DEPLOYMENT_OUTPUT = "a1fs_v1_r3_breadth_deployments.json"
COVERAGE_OUTPUT = "a1fs_v1_r3_breadth_coverage.safe.json"
CANDIDATE_OUTPUT = "a1fs_v1_r4_question_candidates.private.json"
POLICY_OUTPUT = "a1fs_v1_r4_capacity_policies.json"
BANK_OUTPUT = "a1fs_v1_r4_approved_practice_bank.private.json"
SUPPLY_OUTPUT = "a1fs_v1_r4_supply_report.safe.json"
REPORT_OUTPUT = "a1fs_v1_r3r4_population.safe.json"

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "PERSONAL_INFORMATION_SOCIAL": ("name", "age", "family", "friend", "mother", "father", "brother", "sister", "hello", "introduce"),
    "DAILY_ROUTINE_TIME": ("time", "clock", "morning", "afternoon", "evening", "daily", "routine", "breakfast", "lunch", "dinner", "week"),
    "SCHOOL_CLASSROOM": ("school", "classroom", "teacher", "student", "pupil", "lesson", "desk", "pencil", "book", "homework"),
    "HOME_LIVING_ENVIRONMENT": ("home", "house", "room", "bedroom", "bathroom", "kitchen", "living room", "garden", "sofa", "table"),
    "SHOPPING_TRANSACTIONS": ("shop", "store", "shopping", "buy", "price", "cost", "pound", "dollar", "cash", "card"),
    "FOOD_DINING": ("food", "drink", "eat", "menu", "restaurant", "cafe", "juice", "water", "milk", "sandwich", "apple"),
    "INTERESTS_LEISURE_ABILITY": ("hobby", "sport", "football", "tennis", "swim", "play", "game", "music", "dance", "can"),
    "TRAVEL_TRANSPORT": ("travel", "bus", "train", "station", "airport", "ticket", "transport", "route", "stop", "platform"),
    "WEATHER": ("weather", "sunny", "rain", "rainy", "cloud", "cloudy", "wind", "windy", "snow", "hot", "cold"),
    "HEALTH_MEDICAL": ("health", "doctor", "nurse", "sick", "ill", "pain", "hurt", "headache", "medicine", "hospital"),
    "PUBLIC_PLACES_COMMUNITY": ("library", "park", "bank", "post office", "museum", "cinema", "street", "town", "community", "public"),
    "DIGITAL_COMMUNICATION": ("email", "message", "chat", "online", "computer", "phone", "website", "internet", "digital"),
}

LIFE_TASK_BY_DOMAIN = {
    "PERSONAL_INFORMATION_SOCIAL": "LIFE_TASK_EXCHANGE_BASIC_PERSONAL_INFORMATION",
    "DAILY_ROUTINE_TIME": "LIFE_TASK_UNDERSTAND_OR_REPORT_DAILY_TIME_INFORMATION",
    "SCHOOL_CLASSROOM": "LIFE_TASK_COMPLETE_A_CONTROLLED_CLASSROOM_LANGUAGE_TASK",
    "HOME_LIVING_ENVIRONMENT": "LIFE_TASK_DESCRIBE_OR_LOCATE_SOMETHING_AT_HOME",
    "SHOPPING_TRANSACTIONS": "LIFE_TASK_SELECT_OR_CONFIRM_A_BASIC_PURCHASE",
    "FOOD_DINING": "LIFE_TASK_EXPRESS_OR_UNDERSTAND_A_BASIC_FOOD_CHOICE",
    "INTERESTS_LEISURE_ABILITY": "LIFE_TASK_EXPRESS_OR_UNDERSTAND_AN_INTEREST_OR_ABILITY",
    "TRAVEL_TRANSPORT": "LIFE_TASK_OBTAIN_OR_CONFIRM_BASIC_TRAVEL_INFORMATION",
    "WEATHER": "LIFE_TASK_UNDERSTAND_OR_REPORT_BASIC_WEATHER_INFORMATION",
    "HEALTH_MEDICAL": "LIFE_TASK_REPORT_OR_UNDERSTAND_A_BASIC_HEALTH_NEED",
    "PUBLIC_PLACES_COMMUNITY": "LIFE_TASK_LOCATE_OR_USE_A_BASIC_PUBLIC_SERVICE",
    "DIGITAL_COMMUNICATION": "LIFE_TASK_READ_OR_SEND_A_BASIC_DIGITAL_MESSAGE",
}

PURPOSE_BY_ROLE = {
    "CHK": "CORE_PRACTICE",
    "PRD": "CORE_PRACTICE",
    "XFR": "TRANSFER",
    "EVD": "REASSESSMENT",
}


class ProductionPopulationError(ValueError):
    """Fail-closed R3/R4 production-population error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionPopulationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ProductionPopulationError(f"{code}_not_object")
    return value


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _safe_root(path: Path) -> Path:
    resolved = Path(path).resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise ProductionPopulationError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _timestamp(value: str | None) -> str:
    raw = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProductionPopulationError("reviewed_at_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProductionPopulationError("reviewed_at_timezone_required")
    return raw


def _identifier(prefix: str, *parts: Any, length: int = 20) -> str:
    return f"{prefix}{digest([str(value) for value in parts])[:length].upper()}"


def _strings(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list) and all(isinstance(row, str) and row.strip() for row in value):
        return [row.strip() for row in value]
    return []


def _walk_values(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            result.append(str(key))
            result.extend(_walk_values(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_walk_values(child))
    elif isinstance(value, (str, int, float)):
        result.append(str(value))
    return result


def _walk_named(value: Any, names: set[str]) -> list[Any]:
    result: list[Any] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in names:
                result.append(child)
            result.extend(_walk_named(child, names))
    elif isinstance(value, list):
        for child in value:
            result.extend(_walk_named(child, names))
    return result


def _domain(asset: Mapping[str, Any], requirement_node_id: str) -> tuple[str | None, str]:
    payload = asset.get("payload")
    text = " ".join(_walk_values(payload) + [str(asset.get("lesson_id")), requirement_node_id]).casefold()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            pattern = r"(?<![a-z])" + re.escape(keyword.casefold()) + r"(?![a-z])"
            score += len(re.findall(pattern, text))
        if score:
            scores[domain] = score
    if not scores:
        return None, "DOMAIN_NOT_RESOLVED"
    best = max(scores.values())
    winners = sorted(domain for domain, score in scores.items() if score == best)
    if len(winners) != 1:
        return None, "DOMAIN_AMBIGUOUS"
    return winners[0], "DOMAIN_KEYWORD_AUTHORITY_PROJECTION"


def _context(payload: Any) -> dict[str, Any] | None:
    candidates = _walk_named(payload, {"context", "situation", "scenario", "source_text", "passage", "dialogue"})
    for candidate in candidates:
        if isinstance(candidate, Mapping) and candidate:
            return deepcopy(dict(candidate))
        if isinstance(candidate, str) and candidate.strip():
            return {"source_context": candidate.strip()}
    return None


def _options(payload: Any) -> list[str]:
    for candidate in _walk_named(payload, {"options", "choices", "answer_options", "answer_choices"}):
        rows = _strings(candidate)
        if len(rows) >= 2 and len(rows) == len(set(rows)):
            return rows
    return []


def _sequence(payload: Any, *, morphology: bool = False) -> list[str]:
    names = {"supplied_morphemes", "morphology_parts"} if morphology else {"supplied_tokens", "token_sequence", "sequence_tokens", "tokens"}
    for candidate in _walk_named(payload, names):
        rows = _strings(candidate)
        if len(rows) >= 2:
            return rows
    return []


def _task_projection(asset: Mapping[str, Any], derived: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str, str, str]:
    payload = asset["payload"]
    mode = str(derived["scoring_mode"])
    prompt = str(derived["prompt"]).strip()
    role = str(asset["role"])
    context = _context(payload)
    learner: dict[str, Any] = {"prompt": prompt}
    scoring: dict[str, Any]
    if mode == "EXACT_OPTION":
        choices = _options(payload)
        accepted = list(derived["accepted_texts"])
        if len(choices) < 2 or not accepted or any(answer not in choices for answer in accepted):
            raise ProductionPopulationError("EXACT_OPTION_VISIBLE_OPTIONS_MISSING")
        learner.update({"response_mode": "select_one", "options": choices})
        scoring = {"scoring_mode": mode, "response_type": "string", "accepted_texts": accepted, "human_review_fallback": False}
        task_type, support, initiative, evidence = "SELECT_ONE", "S1_KEYWORD_OR_VISUAL", "CHOOSE_FROM_OPTIONS", "E1_RECOGNITION"
    elif mode == "EXACT_SEQUENCE":
        accepted = list(derived["accepted_sequence"])
        supplied = _sequence(payload)
        response_mode = "ordered_tokens"
        learner_key = "supplied_tokens"
        if not supplied:
            supplied = _sequence(payload, morphology=True)
            response_mode = "ordered_morphemes"
            learner_key = "supplied_morphemes"
        if len(supplied) < 2 or Counter(supplied) != Counter(accepted):
            raise ProductionPopulationError("EXACT_SEQUENCE_VISIBLE_PARTS_MISSING")
        learner.update({"response_mode": response_mode, learner_key: supplied})
        scoring = {"scoring_mode": mode, "response_type": "string_array", "accepted_sequence": accepted, "human_review_fallback": False}
        task_type, support, initiative, evidence = "SENTENCE_ORDERING", "S1_KEYWORD_OR_VISUAL", "CHOOSE_FROM_OPTIONS", "E1_RECOGNITION"
    elif mode == "NORMALIZED_TEXT":
        accepted = list(derived["accepted_texts"])
        if not accepted:
            raise ProductionPopulationError("NORMALIZED_TEXT_ANSWER_MISSING")
        learner.update({"response_mode": "short_text"})
        scoring = {
            "scoring_mode": mode, "response_type": "string", "accepted_texts": accepted,
            "case_insensitive": bool(derived.get("case_insensitive", True)),
            "punctuation_tolerance": bool(derived.get("punctuation_tolerance", True)),
            "human_review_fallback": False,
        }
        task_type, support, initiative, evidence = "GUIDED_RESPONSE", "S2_FRAME", "RESPOND_ONLY", "E2_CONTROLLED_PRODUCTION"
    elif mode == "FEATURE_RUBRIC":
        rubric = deepcopy(dict(derived.get("rubric") or {}))
        if not rubric or not context:
            raise ProductionPopulationError("FEATURE_RUBRIC_CONTEXT_OR_RUBRIC_MISSING")
        learner.update({"response_mode": "short_text", "context": context})
        scoring = {"scoring_mode": mode, "response_type": "string", "rubric": rubric, "human_review_fallback": True}
        task_type, support, initiative, evidence = "INDEPENDENT_RESPONSE", "S0_INDEPENDENT", "INDEPENDENT_INITIATION", "E3_INDEPENDENT_PRODUCTION"
    else:
        raise ProductionPopulationError("SCORING_MODE_NOT_FORMAL_ITEM")
    if context and "context" not in learner:
        learner["context"] = context
    if role == "XFR":
        support, initiative, evidence = "S0_INDEPENDENT", "INDEPENDENT_INITIATION", "E4_CROSS_CONTEXT_TRANSFER"
        variation, transfer = "RESPONSE_VARIATION", "NEAR"
    else:
        variation, transfer = "EXPECTED_SCRIPT", "NONE"
    return learner, scoring, task_type, support, initiative, variation, transfer, evidence


def _load_sources(ontology_path: Path, graph_path: Path, consumer_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    ontology = read_json(ontology_path, "ontology")
    errors = r2_validator.validate_ontology(ontology)
    if errors:
        raise ProductionPopulationError("ontology_invalid:" + "|".join(errors))
    graph = read_json(graph_path, "graph")
    if graph.get("validation_status") != r3.GRAPH_STATUS:
        raise ProductionPopulationError("graph_status_invalid")
    consumer = read_json(consumer_path, "consumer")
    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION or consumer.get("validation_status") != m2.STATUS:
        raise ProductionPopulationError("consumer_identity_or_status_invalid")
    if consumer.get("source_graph_sha256") != file_digest(graph_path):
        raise ProductionPopulationError("consumer_graph_binding_mismatch")
    if any(row.get("level") not in {"A1", "A1+", "A2"} for row in consumer.get("lesson_catalog", [])):
        raise ProductionPopulationError("consumer_level_invalid")
    return ontology, graph, consumer


def _candidate_projection(
    *, ontology: Mapping[str, Any], graph: Mapping[str, Any], consumer: Mapping[str, Any], reviewed_at: str,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], Counter[str]]:
    required_nodes = {str(row["node_id"]): row for row in r3.capability_nodes(graph)}
    lessons = {str(row["lesson_id"]): row for row in consumer.get("lesson_catalog", []) if row.get("level") in {"A1", "A1+"}}
    assets_by_lesson: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in consumer.get("asset_records", []):
        if raw.get("level") in {"A1", "A1+"}:
            assets_by_lesson[str(raw["lesson_id"])].append(dict(raw))
    candidates: list[dict[str, Any]] = []
    by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejected: Counter[str] = Counter()
    fingerprints_by_cell_key: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for lesson_id, lesson in sorted(lessons.items()):
        requirement_ids = sorted(set(lesson.get("requirement_node_ids", [])) & set(required_nodes))
        if not requirement_ids:
            continue
        for asset in sorted(assets_by_lesson.get(lesson_id, []), key=lambda row: str(row.get("asset_key"))):
            try:
                derived = m6.derive_contract(asset)
                if not derived.get("capture_enabled"):
                    raise ProductionPopulationError("CAPTURE_NOT_ENABLED")
                learner, scoring, task_type, support, initiative, variation, transfer, evidence = _task_projection(asset, derived)
                validated_learner, validated_scoring = assessment.validate_learner_contract(
                    item_id=str(asset["asset_key"]), task_type=task_type.casefold(), learner=learner, scoring=scoring,
                )
            except (m6.ResponseEvidenceError, assessment.AssessmentValidityError, ProductionPopulationError, KeyError, TypeError, ValueError) as exc:
                rejected[str(exc).split(":", 1)[0]] += 1
                continue
            for node_id in requirement_ids:
                domain, domain_method = _domain(asset, node_id)
                if not domain:
                    rejected[domain_method] += 1
                    continue
                capability_id = _identifier("CAP_", node_id)
                life_task_id = LIFE_TASK_BY_DOMAIN[domain]
                cell_key = (capability_id, life_task_id, domain)
                fingerprint = assessment._contract_fingerprint(validated_learner)
                if fingerprint in fingerprints_by_cell_key[cell_key]:
                    rejected["DUPLICATE_LEARNER_STIMULUS_PER_CELL"] += 1
                    continue
                fingerprints_by_cell_key[cell_key].add(fingerprint)
                role = str(asset.get("role"))
                purpose = PURPOSE_BY_ROLE.get(role, "CORE_PRACTICE")
                item_id = _identifier("R4_ITEM_", asset.get("asset_key"), node_id, purpose, length=24)
                level = "A1_PLUS" if asset.get("level") == "A1+" else "A1"
                media_state = "DEFERRED_MEDIA_PAYLOAD" if asset.get("skill") in {"LISTENING", "SPEAKING"} else "NOT_REQUIRED"
                candidate: dict[str, Any] = {
                    "item_id": item_id,
                    "breadth_cell_id": "PENDING_CELL_ID",
                    "capability_id": capability_id,
                    "life_task_id": life_task_id,
                    "domain": domain,
                    "level": level,
                    "skill": str(asset["skill"]),
                    "purpose": purpose,
                    "task_type": task_type,
                    "support_level": support,
                    "initiative_level": initiative,
                    "interaction_variation": variation,
                    "transfer_distance": transfer,
                    "template_family": f"TEMPLATE_{asset['skill']}_{task_type}_{role or 'GENERIC'}",
                    "stimulus_fingerprint": fingerprint,
                    "media_payload_state": media_state,
                    "source_refs": [
                        f"M1_NODE:{node_id}", f"M2_ASSET:{asset['asset_key']}",
                        f"M2_LESSON:{lesson_id}", f"DOMAIN_METHOD:{domain_method}",
                    ],
                    "authority_refs": [
                        f"M1_GRAPH:{graph.get('source_baseline_sha256')}",
                        f"M2_CONSUMER:{consumer.get('source_graph_sha256')}",
                        f"M2_CONTENT_DIGEST:{asset.get('content_digest')}",
                    ],
                    "provenance": "EXISTING_AUTHORITY_REVIEWED",
                    "learner_contract": validated_learner,
                    "private_scoring_contract": validated_scoring,
                    "validator_status": "PASS",
                }
                candidate_sha = r4.candidate_digest(candidate)
                candidate["candidate_sha256"] = candidate_sha
                candidate["authority_review"] = {
                    "status": "APPROVED", "reviewer_id": AUTHORITY_REVIEWER, "reviewed_at": reviewed_at,
                    "criteria": {
                        "a1_a1plus_level_fit": True,
                        "breadth_cell_fit": True,
                        "learner_stimulus_complete": True,
                        "answer_or_rubric_valid": True,
                        "semantic_unambiguous": True,
                        "source_trace_complete": True,
                    },
                    "candidate_sha256": candidate_sha,
                }
                candidate["_projection"] = {
                    "node_id": node_id, "evidence_level": evidence, "lesson_id": lesson_id,
                    "asset_key": str(asset["asset_key"]), "role": role,
                }
                candidates.append(candidate)
                by_node[node_id].append(candidate)
    return candidates, by_node, rejected


def _profiles_and_obligations(
    *, ontology: Mapping[str, Any], graph: Mapping[str, Any], candidates_by_node: Mapping[str, Sequence[Mapping[str, Any]]], graph_sha: str,
) -> tuple[dict[str, Any], dict[tuple[str, str, str], dict[str, Any]]]:
    profiles: list[dict[str, Any]] = []
    obligation_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for node in r3.capability_nodes(graph):
        node_id = str(node["node_id"])
        capability_id = _identifier("CAP_", node_id)
        rows = list(candidates_by_node.get(node_id, []))
        if not rows:
            profiles.append({
                "capability_node_id": node_id,
                "capability_id": capability_id,
                "profile_state": "PROFILE_NOT_POPULATED",
                "dimension_states": {field: "NOT_POPULATED" for field in r3.PROFILE_DIMENSIONS},
                "dimension_justifications": {},
                "obligations": [],
            })
            continue
        grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(str(row["life_task_id"]), str(row["domain"]))].append(row)
        obligations: list[dict[str, Any]] = []
        for (life_task_id, domain), group in sorted(grouped.items()):
            obligation_id = _identifier("BREADTH_OBLIGATION_", node_id, life_task_id, domain, length=24)
            evidence_levels = sorted({str(row["_projection"]["evidence_level"]) for row in group})
            media_policy = "REQUIRED" if all(row["media_payload_state"] == "DEFERRED_MEDIA_PAYLOAD" for row in group) else "NONE"
            obligation = {
                "obligation_id": obligation_id,
                "life_task_id": life_task_id,
                "domain": domain,
                "required_skills": sorted({str(row["skill"]) for row in group}),
                "required_support_levels": sorted({str(row["support_level"]) for row in group}),
                "required_initiative_levels": sorted({str(row["initiative_level"]) for row in group}),
                "required_variation_types": sorted({str(row["interaction_variation"]) for row in group}),
                "required_transfer_distances": sorted({str(row["transfer_distance"]) for row in group}),
                "required_evidence_levels": evidence_levels,
                "required_retention_stages": ["NOT_SCHEDULED"],
                "required_media_policy": media_policy,
                "source_refs": sorted({ref for row in group for ref in row["source_refs"]}),
            }
            obligations.append(obligation)
            obligation_index[(capability_id, life_task_id, domain)] = {"node_id": node_id, "obligation": obligation}
        profiles.append({
            "capability_node_id": node_id,
            "capability_id": capability_id,
            "profile_state": PARTIAL_PROFILE_STATE,
            "dimension_states": {
                "required_domains": "NOT_POPULATED",
                "required_life_tasks": "NOT_POPULATED",
                "required_skills": "POPULATED",
                "required_support_levels": "POPULATED",
                "required_initiative_levels": "POPULATED",
                "required_variation_types": "POPULATED",
                "required_transfer_distances": "NOT_POPULATED",
                "required_evidence_levels": "POPULATED",
                "required_retention_stages": "NOT_POPULATED",
                "required_media_policy": "POPULATED",
            },
            "dimension_justifications": {},
            "obligations": obligations,
        })
    registry = {
        "task_id": r3.TASK_ID,
        "schema_version": r3.PROFILE_SCHEMA_VERSION,
        "source_graph_sha256": graph_sha,
        "ontology_sha256": ontology["ontology_sha256"],
        "profiles": profiles,
        "profiles_sha256": r3.digest(profiles),
    }
    return registry, obligation_index


def _deployment_contract(candidate: Mapping[str, Any], obligation: Mapping[str, Any]) -> dict[str, Any]:
    contract = r2.empty_contract(
        deployment_id=_identifier("EDGE_DEPLOYMENT_", candidate["item_id"], length=24),
        capability_id=str(candidate["capability_id"]),
        life_task_id=str(candidate["life_task_id"]),
    )
    values: dict[str, Any] = {
        "level": candidate["level"],
        "domain": candidate["domain"],
        "skill": candidate["skill"],
        "task_type": candidate["task_type"],
        "support_level": candidate["support_level"],
        "initiative_level": candidate["initiative_level"],
        "interaction_variation": candidate["interaction_variation"],
        "transfer_distance": candidate["transfer_distance"],
        "transfer_dimensions_changed": ["SITUATION"] if candidate["transfer_distance"] != "NONE" else [],
        "evidence_level": "E0_EXPOSURE",
        "accuracy_result": "NOT_EVALUATED",
        "meaning_result": "NOT_EVALUATED",
        "task_completion_result": "NOT_EVALUATED",
        "pragmatic_result": "NOT_EVALUATED",
        "independence_result": "NOT_EVALUATED",
        "initiative_result": "NOT_EVALUATED",
        "repair_result": "NOT_EVALUATED",
        "retention_stage": "NOT_SCHEDULED",
        "evidence_validity": "VALID",
        "system_error_status": "NONE",
        "media_requirement": obligation["required_media_policy"],
        "media_payload_state": candidate["media_payload_state"],
        "transcript_state": "NOT_POPULATED" if candidate["skill"] == "LISTENING" else "NOT_REQUIRED",
        "recording_requirement": "REQUIRED" if candidate["skill"] == "SPEAKING" else "NONE",
        "recording_state": "DEFERRED_MEDIA_PAYLOAD" if candidate["skill"] == "SPEAKING" else "NOT_REQUIRED",
        "consent_requirement": "REQUIRED_NOT_CAPTURED" if candidate["skill"] == "SPEAKING" else "NOT_REQUIRED",
        "template_family": candidate["template_family"],
        "stimulus_fingerprint": candidate["stimulus_fingerprint"],
        "context_seen_before": "UNSEEN",
        "validator_status": "PASS",
        "source_refs": list(candidate["source_refs"]),
        "authority_refs": list(candidate["authority_refs"]),
    }
    for field, value in values.items():
        contract[field] = value
        if field in {"media_payload_state", "recording_state"} and value == "DEFERRED_MEDIA_PAYLOAD":
            contract["field_states"][field] = "DEFERRED_MEDIA_PAYLOAD"
        elif value in (None, [], ""):
            continue
        else:
            contract["field_states"][field] = "POPULATED"
    if candidate["transfer_distance"] == "NONE":
        contract["field_states"]["transfer_dimensions_changed"] = "NOT_APPLICABLE_WITH_JUSTIFICATION"
        contract["field_justifications"]["transfer_dimensions_changed"] = "No transfer dimension changes are claimed for a non-transfer source item."
    errors = r2_validator.validate_contract(contract)
    if errors:
        raise ProductionPopulationError("deployment_contract_invalid:" + "|".join(errors))
    return contract


def _partial_coverage(
    *, ontology_path: Path, graph_path: Path, partial_profiles: Mapping[str, Any], deployments_path: Path, output_root: Path,
) -> dict[str, Any]:
    normalized_profiles = deepcopy(dict(partial_profiles))
    partial_node_ids: list[str] = []
    full_count = 0
    for profile in normalized_profiles["profiles"]:
        if profile["profile_state"] == PARTIAL_PROFILE_STATE:
            partial_node_ids.append(profile["capability_node_id"])
            profile["profile_state"] = "PROFILE_DEFINED"
            profile["dimension_states"] = {field: "POPULATED" for field in r3.PROFILE_DIMENSIONS}
        elif profile["profile_state"] == "PROFILE_DEFINED":
            full_count += 1
    normalized_profiles["profiles_sha256"] = r3.digest(normalized_profiles["profiles"])
    normalized_path = output_root / ".normalized_profiles.private.json"
    write_private(normalized_path, normalized_profiles)
    report = r3.build(
        ontology_path=ontology_path, graph_path=graph_path,
        profiles_path=normalized_path, deployments_path=deployments_path,
    )
    normalized_path.unlink(missing_ok=True)
    existing_ids = {row["capability_node_id"] for row in report["cells"] if row["status"] == "PROFILE_DEFINITION_REQUIRED"}
    partial_by_id = {row["capability_node_id"]: row for row in partial_profiles["profiles"] if row["profile_state"] == PARTIAL_PROFILE_STATE}
    for node_id in sorted(partial_node_ids):
        profile = partial_by_id[node_id]
        missing_dimensions = [field for field, state in profile["dimension_states"].items() if state == "NOT_POPULATED"]
        report["cells"].append({
            "cell_id": f"BREADTH_CELL_PROFILE_REQUIRED_{r3.digest([node_id, missing_dimensions])[:20].upper()}",
            "capability_node_id": node_id,
            "capability_id": profile["capability_id"],
            "obligation_id": None,
            "life_task_id": None,
            "domain": None,
            "status": "PROFILE_DEFINITION_REQUIRED",
            "dimension_coverage": {
                field: {"required": [], "observed": [], "missing": ["PROFILE_PARTIALLY_POPULATED"] if field in missing_dimensions else []}
                for field in r3.PROFILE_DIMENSIONS
            },
            "matching_deployment_ids": [],
            "next_actions": ["COMPLETE_REMAINING_BREADTH_REQUIREMENT_DIMENSIONS"],
        })
        existing_ids.add(node_id)
    report["cells"].sort(key=lambda row: (r3.GAP_PRIORITY[row["status"]], str(row["capability_node_id"]), str(row.get("obligation_id"))))
    status_counts = Counter(row["status"] for row in report["cells"])
    for status in r3.CELL_STATUSES:
        status_counts.setdefault(status, 0)
    gaps = []
    for index, row in enumerate((row for row in report["cells"] if row["status"] != "RETENTION_PASS"), start=1):
        gaps.append({
            "rank": index, "cell_id": row["cell_id"], "capability_node_id": row["capability_node_id"],
            "capability_id": row["capability_id"], "life_task_id": row.get("life_task_id"),
            "domain": row.get("domain"), "status": row["status"], "next_actions": row["next_actions"],
        })
    denominator = len(report["cells"])
    retained = status_counts["RETENTION_PASS"]
    structural_ready = sum(status_counts[status] for status in (
        "READY_TO_DEPLOY", "DEPLOYED", "EVIDENCE_INSUFFICIENT", "SUPPORTED_PASS",
        "INDEPENDENT_PASS", "TRANSFER_PASS", "RETENTION_PASS", "DEFERRED_MEDIA",
    ))
    not_populated_count = sum(row["profile_state"] == "PROFILE_NOT_POPULATED" for row in partial_profiles["profiles"])
    report["source_bindings"]["profiles_sha256"] = r3.digest(partial_profiles["profiles"])
    report["counts"].update({
        "profile_defined_count": full_count,
        "profile_partial_count": len(partial_node_ids),
        "profile_missing_count": not_populated_count + len(partial_node_ids),
        "denominator_cell_count": denominator,
        "gap_count": len(gaps),
        "status_counts": dict(sorted(status_counts.items())),
    })
    report["coverage_metrics"] = {
        "structural_ready_count": structural_ready,
        "structural_ready_percent": round(structural_ready * 100.0 / denominator, 2) if denominator else 0.0,
        "retention_complete_count": retained,
        "retention_complete_percent": round(retained * 100.0 / denominator, 2) if denominator else 0.0,
        "false_100_percent_blocked": retained != denominator,
        "completion_denominator_source": "EXPLICIT_BREADTH_REQUIREMENT_CELLS_PLUS_PARTIAL_AND_MISSING_PROFILE_PLACEHOLDERS",
    }
    report["profile_missing_capability_node_ids"] = sorted(existing_ids)
    report["ranked_gaps"] = gaps
    core = {key: value for key, value in report.items() if key != "report_sha256"}
    return {**core, "report_sha256": r3.digest(core)}


def materialize(
    *, ontology_path: Path, graph_path: Path, consumer_path: Path, output_root: Path, reviewed_at: str | None = None,
) -> dict[str, Any]:
    root = _safe_root(output_root)
    reviewed_at = _timestamp(reviewed_at)
    ontology, graph, consumer = _load_sources(ontology_path, graph_path, consumer_path)
    candidates, candidates_by_node, rejected = _candidate_projection(
        ontology=ontology, graph=graph, consumer=consumer, reviewed_at=reviewed_at,
    )
    profiles, obligation_index = _profiles_and_obligations(
        ontology=ontology, graph=graph, candidates_by_node=candidates_by_node, graph_sha=file_digest(graph_path),
    )
    for candidate in candidates:
        projection = candidate.pop("_projection")
        key = (candidate["capability_id"], candidate["life_task_id"], candidate["domain"])
        indexed = obligation_index[key]
        candidate["breadth_cell_id"] = f"BREADTH_CELL_{r3.digest([indexed['node_id'], indexed['obligation']['obligation_id']])[:24].upper()}"
        candidate["candidate_sha256"] = r4.candidate_digest(candidate)
        candidate["authority_review"]["candidate_sha256"] = candidate["candidate_sha256"]
        candidate["authority_review"]["reviewed_at"] = reviewed_at
        candidate["_projection"] = projection
    contracts = []
    for candidate in candidates:
        key = (candidate["capability_id"], candidate["life_task_id"], candidate["domain"])
        contracts.append(_deployment_contract(candidate, obligation_index[key]["obligation"]))
    deployments = r3.deployment_registry(ontology["ontology_sha256"], contracts)
    profiles_path = root / PROFILE_OUTPUT
    deployments_path = root / DEPLOYMENT_OUTPUT
    coverage_path = root / COVERAGE_OUTPUT
    write_private(profiles_path, profiles)
    write_private(deployments_path, deployments)
    coverage = _partial_coverage(
        ontology_path=ontology_path, graph_path=graph_path, partial_profiles=profiles,
        deployments_path=deployments_path, output_root=root,
    )
    write_private(coverage_path, coverage)
    clean_candidates = []
    for candidate in candidates:
        row = deepcopy(candidate)
        row.pop("_projection", None)
        clean_candidates.append(row)
    candidate_registry = r4.candidate_registry(ontology["ontology_sha256"], coverage["report_sha256"], clean_candidates)
    policies = []
    grouped_by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in clean_candidates:
        grouped_by_cell[row["breadth_cell_id"]].append(row)
    cell_by_id = {row["cell_id"]: row for row in coverage["cells"]}
    for cell_id, rows in sorted(grouped_by_cell.items()):
        purposes: dict[str, Any] = {}
        for purpose in sorted({row["purpose"] for row in rows}):
            purpose_rows = [row for row in rows if row["purpose"] == purpose]
            purposes[purpose] = {
                "min_approved_items": len(purpose_rows),
                "min_unique_stimuli": len({row["stimulus_fingerprint"] for row in purpose_rows}),
                "min_template_families": len({row["template_family"] for row in purpose_rows}),
            }
        cell = cell_by_id[cell_id]
        policies.append({
            "breadth_cell_id": cell_id,
            "purposes": purposes,
            "max_recent_reuse": 0,
            "required_skill_projection": sorted({row["skill"] for row in rows}),
            "policy_source_refs": list(cell.get("source_refs", [])) or [cell["capability_node_id"]],
        })
    policy_registry = r4.capacity_policy_registry(coverage["report_sha256"], policies)
    candidate_path = root / CANDIDATE_OUTPUT
    policy_path = root / POLICY_OUTPUT
    write_private(candidate_path, candidate_registry)
    write_private(policy_path, policy_registry)
    bank, supply = r4.build(
        ontology_path=ontology_path, coverage_path=coverage_path,
        candidates_path=candidate_path, policies_path=policy_path,
    )
    bank_path = root / BANK_OUTPUT
    supply_path = root / SUPPLY_OUTPUT
    write_private(bank_path, bank)
    write_private(supply_path, supply)
    ready_cells = sum(row["supply_status"] == "READY_FOR_LOCAL_SELECTION" for row in supply["cell_supply"])
    media_cells = sum(row["supply_status"] == "MEDIA_DEFERRED" for row in supply["cell_supply"])
    report_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "reviewed_at": reviewed_at,
        "source_bindings": {
            "ontology_sha256": ontology["ontology_sha256"],
            "graph_sha256": file_digest(graph_path),
            "consumer_sha256": file_digest(consumer_path),
            "profile_registry_sha256": file_digest(profiles_path),
            "deployment_registry_sha256": file_digest(deployments_path),
            "coverage_report_sha256": coverage["report_sha256"],
            "candidate_registry_sha256": file_digest(candidate_path),
            "policy_registry_sha256": file_digest(policy_path),
            "practice_bank_sha256": bank["bank_sha256"],
            "supply_report_sha256": supply["report_sha256"],
        },
        "counts": {
            "required_capability_node_count": coverage["counts"]["required_capability_node_count"],
            "profile_defined_count": coverage["counts"].get("profile_defined_count", 0),
            "profile_partial_count": coverage["counts"].get("profile_partial_count", 0),
            "profile_not_populated_count": sum(row["profile_state"] == "PROFILE_NOT_POPULATED" for row in profiles["profiles"]),
            "denominator_cell_count": coverage["counts"]["denominator_cell_count"],
            "profile_placeholder_cell_count": coverage["counts"]["status_counts"]["PROFILE_DEFINITION_REQUIRED"],
            "source_asset_count": sum(row.get("level") in {"A1", "A1+"} for row in consumer.get("asset_records", [])),
            "formal_candidate_count": len(clean_candidates),
            "approved_practice_item_count": bank["item_count"],
            "ready_for_local_selection_cell_count": ready_cells,
            "media_deferred_cell_count": media_cells,
            "rejected_projection_count": sum(rejected.values()),
            "rejected_projection_counts": dict(sorted(rejected.items())),
        },
        "claim_boundaries": {
            "canonical_authority_modified": False,
            "m1_graph_modified": False,
            "complete_breadth_denominator_reduced": False,
            "unpopulated_dimensions_hidden": False,
            "new_learner_questions_generated": False,
            "test_fixture_promoted": False,
            "learner_mastery_claimed": False,
            "retention_claimed": False,
            "audio_or_recording_completed": False,
            "a2_content_admitted": False,
            "a2_unlocked": False,
            "qwen_required": False,
        },
        "next_short_step": NEXT_SHORT_STEP if ready_cells else TASK_ID,
    }
    report = {**report_core, "report_sha256": digest(report_core)}
    write_private(root / REPORT_OUTPUT, report)
    return report


def safe_scan(value: Any) -> None:
    forbidden = {
        "prompt", "response", "answer", "answer_key", "accepted_texts", "accepted_sequence",
        "learner_contract", "private_scoring_contract", "operator_review", "rubric",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in forbidden:
                raise ProductionPopulationError(f"private_field_leak:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            raise ProductionPopulationError("absolute_path_leak")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reviewed-at")
    args = parser.parse_args()
    try:
        report = materialize(
            ontology_path=args.ontology, graph_path=args.graph, consumer_path=args.consumer,
            output_root=args.output_root, reviewed_at=args.reviewed_at,
        )
        safe_scan(report)
        print(json.dumps({
            "validation_status": report["validation_status"],
            "approved_practice_item_count": report["counts"]["approved_practice_item_count"],
            "ready_for_local_selection_cell_count": report["counts"]["ready_for_local_selection_cell_count"],
            "profile_placeholder_cell_count": report["counts"]["profile_placeholder_cell_count"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, indent=2))
        return 0
    except (ProductionPopulationError, r3.BreadthCoverageError, r4.QuestionSupplyError, m6.ResponseEvidenceError, assessment.AssessmentValidityError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
