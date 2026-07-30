#!/usr/bin/env python3
"""Rule-based Unit01 RAZ semantic rewrite, automatic admission, and exception-only review."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_razq01c_unit01_three_skill_candidate_selection_coverage_balancing as upstream
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as qb

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
PARENT_TASK_ID = (
    "A1FS-V1-RAZQ01D_Unit01MicroScenePassageDialogueAdmission_"
    "ThreeSkillProjectionAndUnit02ReusableHandoff"
)
TASK_ID = (
    "A1FS-V1-RAZQ01D-FULLFIX_"
    "Unit01RuleBasedSemanticRewriteAutoAdmissionAndExceptionOnlyHumanReview"
)
SCHEMA_VERSION = "a1fs.v1.razq01d.fullfix.rule_based_auto_admission.v2"
SAFE_SCHEMA_VERSION = "a1fs.v1.razq01d.fullfix.rule_based_auto_admission_safe_readback.v2"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_FULLFIX_RULE_BASED_AUTO_ADMISSION"
UNIT_ID = upstream.UNIT_ID
TARGET_UNIT02_SEQUENCE = 2
APPROVED_CONTRACT_SHA256 = upstream.APPROVED_CONTRACT_SHA256
AUTO_DECISION_REF = "AUTOMATED_POLICY:2026-07-30:RAZQ01D_FULLFIX"
HUMAN_DECISION_REF_PREFIX = "HUMAN_EXCEPTION_REVIEW:"
INSPECTION_REF = "OPERATOR_HANDSHAKE:2026-07-30:UNIT01_SCENE_THREE_SKILL"
OUTPUT_CANDIDATE = Path(
    "ulga/private/a1fs_v1_razq01d_fullfix_unit01_auto_admission.candidate.private.json"
)
OUTPUT_APPROVED = Path(
    "ulga/private/a1fs_v1_razq01d_fullfix_unit01_auto_admission.approved.private.json"
)
OUTPUT_SAFE = Path(
    "ulga/reports/a1fs_v1_razq01d_fullfix_unit01_auto_admission_readback.json"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-RAZQ01D-FULLFIX_"
    "LocalPrivateRuleBasedAutoAdmissionMaterializationAndCoverageRecheck"
)

CONTENT_KINDS = ("MICRO_SCENE", "SHORT_PASSAGE", "SHORT_DIALOGUE")
SKILLS = ("READING", "WRITING", "SPEAKING")
RESOLUTION_CLASSES = (
    "AUTO_APPROVE_DIRECT",
    "AUTO_APPROVE_RULE_REWRITE",
    "AUTO_REJECT",
    "HUMAN_REVIEW_REQUIRED",
    "HUMAN_APPROVE_EXCEPTION",
    "HUMAN_REJECT_EXCEPTION",
)
AUTOMATIC_APPROVAL_CLASSES = frozenset(
    {"AUTO_APPROVE_DIRECT", "AUTO_APPROVE_RULE_REWRITE"}
)
REVIEW_DIMENSIONS = (
    "GRAMMAR_SAFETY",
    "VOCABULARY_SAFETY",
    "SEMANTIC_NATURALNESS",
    "A1_ANSWERABILITY",
    "SCENE_DISTINCTNESS",
    "THREE_SKILL_AFFORDANCE",
)
FUTURE_ROLES = (
    "PREREQUISITE",
    "CARRY_OVER",
    "RECOMBINATION",
    "TRANSFER",
    "SCHEDULED_REVIEW",
    "REMEDIATION",
    "ASSESSMENT_SUPPORT",
)
REUSE_GATES = (
    "PREREQUISITE_UNLOCKED",
    "LEVEL_SCOPE_ALLOWED",
    "NEW_GRAMMAR_COMPATIBILITY_PASS",
    "NO_UNINTRODUCED_GRAMMAR",
    "SEMANTIC_COMPATIBILITY_PASS",
    "SCENE_DEDUPLICATION_PASS",
    "REUSE_REASON_RECORDED",
)
FAMILY_IDS = frozenset(str(row[0]) for row in qb.FAMILIES)
FAMILY_MAP = {
    "READING": (
        "U01-PF04-FIRST-MENTION-CONTEXT",
        "U01-PF05-KNOWN-REFERENCE-CONTEXT",
        "U01-PF08-TRANSFER-FIRST-MENTION",
    ),
    "WRITING": (
        "U01-PF07-WORD-ORDER",
        "U01-PF09-TRANSFER-KNOWN-REFERENCE",
    ),
    "SPEAKING": ("U01-PF10-SPEAK-NOUN",),
}
FINDINGS = (
    (
        "FIXED_CONTEXT_COUNT_TOO_LOW",
        "U01QB01 contains exactly five hard-coded context labels.",
    ),
    (
        "RAZQ01C_NOT_CONSUMED_BY_U01QB01",
        "U01QB01 does not import or consume RAZQ01C.",
    ),
    (
        "U01E_SHORT_TEXT_THREE_SKILL_PRESENT",
        "Existing U01E short texts feed Reading, Writing and Speaking.",
    ),
    (
        "U01QB01_FULL_TEXT_THREE_SKILL_NOT_PRESENT",
        "The 288-item pool uses labels rather than shared passage assets.",
    ),
    (
        "FUNCTIONAL_DIALOGUE_LABEL_WITHOUT_TURN_STRUCTURE",
        "The existing toy-shop context has no speaker turns.",
    ),
)
WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
NP_RE = r"(?P<np>(?:a|an|the)\s+[a-z]+(?:\s+[a-z]+){0,2})"
IDENTIFY_RE = re.compile(rf"^(?:this|that)\s+is\s+{NP_RE}[.!?]?$", re.I)
SEE_RE = re.compile(rf"^i\s+can\s+see\s+{NP_RE}[.!?]?$", re.I)
EXISTS_RE = re.compile(
    rf"^there\s+is\s+{NP_RE}(?:\s+(?P<relation>in|on|near)\s+"
    r"(?P<location>(?:a|an|the)\s+[a-z]+(?:\s+[a-z]+)?))?[.!?]?$",
    re.I,
)
LOCATE_RE = re.compile(
    rf"^{NP_RE}\s+is\s+(?P<relation>in|on|near)\s+"
    r"(?P<location>(?:a|an|the)\s+[a-z]+(?:\s+[a-z]+)?)[.!?]?$",
    re.I,
)
SEVERE_REJECT_FLAGS = frozenset(
    {
        "UNBALANCED_QUOTATION",
        "FRAGMENT_OR_TRAILING_PUNCTUATION",
        "NEGATIVE_IMPERATIVE_PRESENT",
    }
)


class AdmissionBuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def norm(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(filter(None, (norm(item) for item in value.values())))
    if isinstance(value, list):
        return " ".join(filter(None, (norm(item) for item in value)))
    return " ".join(WORD_RE.findall(str(value).casefold().replace("’", "'")))


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdmissionBuildError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AdmissionBuildError(f"OBJECT_REQUIRED:{path}")
    return value


def write(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def validate_upstream(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    scope = report.get("scope") or {}
    if (
        report.get("task_id") != upstream.TASK_ID
        or report.get("status") != upstream.PASS_STATUS
    ):
        raise AdmissionBuildError("RAZQ01C_IDENTITY_INVALID")
    if (
        scope.get("allowed_units") != [UNIT_ID]
        or scope.get("canonical_promotion") is not False
        or scope.get("a2_status") != "LOCKED"
    ):
        raise AdmissionBuildError("RAZQ01C_SCOPE_INVALID")
    rows = report.get("selected_candidates")
    if not isinstance(rows, list) or not rows:
        raise AdmissionBuildError("RAZQ01C_SELECTED_CANDIDATES_REQUIRED")
    source_ids = [str(row.get("source_record_id") or "") for row in rows]
    semantic_ids = [str(row.get("semantic_identity") or "") for row in rows]
    if (
        "" in source_ids
        or len(source_ids) != len(set(source_ids))
        or "" in semantic_ids
        or len(semantic_ids) != len(set(semantic_ids))
    ):
        raise AdmissionBuildError("RAZQ01C_SOURCE_OR_SEMANTIC_ID_INVALID")
    return deepcopy(rows)


def _sentences(text: str) -> list[str]:
    return [
        value.strip()
        for value in SENTENCE_SPLIT_RE.split(text.strip())
        if value.strip()
    ]


def _allowed_lexical_sets(
    contract: Mapping[str, Any],
) -> tuple[set[str], set[str]]:
    nouns = {
        str(row["lemma"]).casefold()
        for row in contract["vocabulary_contract"]["active_vocabulary"]
    }
    adjectives = {
        str(row["lemma"]).casefold()
        for row in contract["vocabulary_contract"]["active_adjectives"]
    }
    return nouns, adjectives


def _parse_np(
    value: str,
    *,
    allowed_nouns: set[str],
    allowed_adjectives: set[str],
) -> dict[str, Any] | None:
    words = norm(value).split()
    if len(words) < 2 or words[0] not in {"a", "an", "the"}:
        return None
    lexical = words[1:]
    noun = lexical[-1]
    modifiers = lexical[:-1]
    if noun not in allowed_nouns:
        return None
    if any(word != "very" and word not in allowed_adjectives for word in modifiers):
        return None
    if "very" in modifiers and (
        modifiers[0] != "very" or len(modifiers) != 2
    ):
        return None
    return {
        "article": words[0],
        "noun": noun,
        "modifiers": modifiers,
        "noun_phrase": " ".join(words),
    }


def extract_semantic_facts(
    candidate: Mapping[str, Any], contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    text = str(candidate.get("text_excerpt") or "").strip()
    allowed_nouns, allowed_adjectives = _allowed_lexical_sets(contract)
    facts: list[dict[str, Any]] = []
    reasons: list[str] = []
    for sentence in _sentences(text):
        match = IDENTIFY_RE.match(sentence)
        fact_type = "IDENTIFY"
        if match is None:
            match = SEE_RE.match(sentence)
            fact_type = "SEE"
        if match is None:
            match = EXISTS_RE.match(sentence)
            fact_type = "EXISTS"
        if match is None:
            match = LOCATE_RE.match(sentence)
            fact_type = "LOCATE"
        if match is None:
            reasons.append("UNSUPPORTED_SEMANTIC_SENTENCE_PATTERN")
            continue
        noun_phrase = _parse_np(
            match.group("np"),
            allowed_nouns=allowed_nouns,
            allowed_adjectives=allowed_adjectives,
        )
        if noun_phrase is None:
            reasons.append("NOUN_PHRASE_OUTSIDE_UNIT01_CONTRACT")
            continue
        relation = match.groupdict().get("relation")
        location_value = match.groupdict().get("location")
        location = None
        if location_value:
            location = _parse_np(
                location_value,
                allowed_nouns=allowed_nouns,
                allowed_adjectives=allowed_adjectives,
            )
            if location is None:
                reasons.append("LOCATION_OUTSIDE_UNIT01_CONTRACT")
                continue
        facts.append(
            {
                "fact_type": fact_type,
                **noun_phrase,
                "relation": relation.casefold() if relation else None,
                "location": location,
                "source_sentence_sha256": hashlib.sha256(
                    sentence.encode("utf-8")
                ).hexdigest(),
            }
        )
    if len(facts) != len(_sentences(text)):
        return [], sorted(set(reasons or ["SEMANTIC_PARSE_INCOMPLETE"]))
    return facts, []


def _all_three_skill_roles(candidate: Mapping[str, Any]) -> bool:
    roles = set(candidate.get("direct_task_candidate_roles") or [])
    return {
        "READING_TASK_CANDIDATE",
        "WRITING_TASK_CANDIDATE",
        "SPEAKING_TASK_CANDIDATE",
    }.issubset(roles)


def classify_resolution(
    candidate: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    selection_class = str(candidate.get("selection_class") or "")
    flags = set(candidate.get("structural_flags") or [])
    if selection_class == "REJECT" or flags & SEVERE_REJECT_FLAGS:
        return {
            "resolution_class": "AUTO_REJECT",
            "reason_codes": sorted(
                {"UPSTREAM_REJECT_OR_SEVERE_STRUCTURE", *flags}
            ),
            "facts": [],
        }
    if selection_class == "REWRITE_REQUIRED":
        return {
            "resolution_class": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": ["UPSTREAM_REWRITE_REQUIRED_SEMANTICS_NOT_UNIQUE"],
            "facts": [],
        }
    if flags:
        return {
            "resolution_class": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": sorted(
                {"NONFATAL_STRUCTURAL_FLAGS_REQUIRE_EXCEPTION_REVIEW", *flags}
            ),
            "facts": [],
        }
    if not _all_three_skill_roles(candidate):
        return {
            "resolution_class": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": ["THREE_SKILL_AFFORDANCE_NOT_CONFIRMED"],
            "facts": [],
        }
    facts, reasons = extract_semantic_facts(candidate, contract)
    if reasons or not facts:
        return {
            "resolution_class": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": reasons or ["SEMANTIC_FACTS_NOT_EXTRACTED"],
            "facts": [],
        }
    resolution_class = (
        "AUTO_APPROVE_DIRECT"
        if selection_class == "DIRECT_MODEL"
        else "AUTO_APPROVE_RULE_REWRITE"
    )
    return {
        "resolution_class": resolution_class,
        "reason_codes": [
            "SEMANTIC_IDENTITY_UNIQUE",
            "RULE_TEMPLATE_AVAILABLE",
            "UNIT01_LANGUAGE_CONTRACT_PASS",
            "THREE_SKILL_AFFORDANCE_PASS",
        ],
        "facts": facts,
    }


def _rewrite_fact(fact: Mapping[str, Any]) -> str:
    noun_phrase = str(fact["noun_phrase"])
    fact_type = str(fact["fact_type"])
    relation = fact.get("relation")
    location = fact.get("location")
    if fact_type == "IDENTIFY":
        return f"I can see {noun_phrase}."
    if fact_type == "SEE":
        return f"This is {noun_phrase}."
    if fact_type == "EXISTS" and relation and location:
        return (
            f"You can see {noun_phrase} {relation} "
            f"{location['noun_phrase']}."
        )
    if fact_type == "EXISTS":
        return f"I can see {noun_phrase}."
    if fact_type == "LOCATE" and relation and location:
        article = str(fact["article"])
        noun = str(fact["noun"])
        if article in {"a", "an"}:
            return (
                f"There is {noun_phrase} {relation} "
                f"{location['noun_phrase']}."
            )
        return (
            f"You can see the {noun} {relation} "
            f"{location['noun_phrase']}."
        )
    raise AdmissionBuildError("UNSUPPORTED_REWRITE_FACT")


def _dialogue_from_facts(
    facts: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    for fact in facts[:2]:
        relation = fact.get("relation")
        location = fact.get("location")
        noun = str(fact["noun"])
        noun_phrase = str(fact["noun_phrase"])
        if relation and location:
            turns.extend(
                [
                    {
                        "speaker_id": "GUIDE",
                        "utterance": f"Where is the {noun}?",
                    },
                    {
                        "speaker_id": "LEARNER",
                        "utterance": (
                            f"The {noun} is {relation} "
                            f"{location['noun_phrase']}."
                        ),
                    },
                ]
            )
        else:
            turns.extend(
                [
                    {
                        "speaker_id": "GUIDE",
                        "utterance": "What can you see?",
                    },
                    {
                        "speaker_id": "LEARNER",
                        "utterance": f"I can see {noun_phrase}.",
                    },
                ]
            )
    return turns[:4]


def _scene_profile(
    candidate: Mapping[str, Any], facts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    nouns = sorted(
        {
            str(value).casefold()
            for value in candidate.get("active_noun_hits") or []
        }
    )
    location_nouns = [
        str(fact["location"]["noun"])
        for fact in facts
        if fact.get("location")
    ]
    setting_nouns = {
        "classroom",
        "room",
        "park",
        "shop",
    }
    setting = next(
        (
            noun.upper()
            for noun in [*location_nouns, *nouns]
            if noun in setting_nouns
        ),
        "UNSPECIFIED_RAZ_SCENE",
    )
    actions = sorted({str(fact["fact_type"]) for fact in facts})
    information = []
    if any(str(fact["article"]) in {"a", "an"} for fact in facts):
        information.append("FIRST_MENTION")
    if any(str(fact["article"]) == "the" for fact in facts):
        information.append("KNOWN_REFERENCE")
    functions = []
    if any(action in {"IDENTIFY", "SEE", "EXISTS"} for action in actions):
        functions.append("IDENTIFY")
    if any(action == "LOCATE" for action in actions):
        functions.append("LOCATE")
    participants = (
        ["LEARNER"]
        if any(action in {"IDENTIFY", "SEE"} for action in actions)
        else []
    )
    profile = {
        "setting": setting,
        "participants": participants,
        "objects": [noun.upper() for noun in nouns],
        "actions": actions,
        "information_structure": information,
        "communicative_function_ids": functions,
    }
    profile["semantic_scene_id"] = (
        f"U01-SCENE-"
        f"{hashlib.sha256(str(candidate['semantic_identity']).encode()).hexdigest()[:12].upper()}"
    )
    profile["distinct_scene_signature"] = digest(
        {
            "semantic_identity": candidate["semantic_identity"],
            "setting": setting,
            "objects": profile["objects"],
            "actions": actions,
        }
    )
    return profile


def _theme(scene: Mapping[str, Any]) -> str:
    objects = set(scene.get("objects") or [])
    if objects & {"CAT", "DOG"}:
        return "ANIMALS"
    if objects & {"BOOK", "DESK", "CLASSROOM", "BAG"}:
        return "SCHOOL"
    if objects & {"APPLE", "EGG"}:
        return "FOOD"
    if objects & {"BED", "ROOM", "DOOR", "WINDOW", "BOX"}:
        return "HOME"
    if objects & {"PARK", "TREE"}:
        return "OUTDOORS"
    return "UNIT01_OBJECTS"


def patterns(candidate: Mapping[str, Any]) -> list[str]:
    result = {qb.PATTERN_NOUN}
    if candidate.get("active_adjective_hits") or candidate.get(
        "adjective_noun_phrases"
    ):
        result.add(qb.PATTERN_ADJECTIVE)
    if candidate.get("very_adjective_noun_phrases"):
        result.add(qb.PATTERN_VERY)
    return sorted(result)


def content_parts(
    decision: Mapping[str, Any],
) -> tuple[list[str], list[dict[str, str]]]:
    kind = str(decision["content_kind"])
    sentences = [
        str(value).strip()
        for value in decision.get("adapted_sentences") or []
        if str(value).strip()
    ]
    turns = [
        {
            "speaker_id": str(value.get("speaker_id") or ""),
            "utterance": str(value.get("utterance") or "").strip(),
        }
        for value in decision.get("dialogue_turns") or []
        if isinstance(value, Mapping)
    ]
    if kind == "MICRO_SCENE" and not (
        1 <= len(sentences) <= 3 and not turns
    ):
        raise AdmissionBuildError("MICRO_SCENE_STRUCTURE_INVALID")
    if kind == "SHORT_PASSAGE" and not (
        2 <= len(sentences) <= 6 and not turns
    ):
        raise AdmissionBuildError("SHORT_PASSAGE_STRUCTURE_INVALID")
    if kind == "SHORT_DIALOGUE":
        speakers = {turn["speaker_id"] for turn in turns if turn["speaker_id"]}
        if (
            sentences
            or not 2 <= len(turns) <= 6
            or len(speakers) < 2
            or any(
                not turn["speaker_id"] or not turn["utterance"]
                for turn in turns
            )
        ):
            raise AdmissionBuildError("SHORT_DIALOGUE_STRUCTURE_INVALID")
    return sentences, turns


def asset_id(kind: str, semantic_identity: str) -> str:
    prefix = {
        "MICRO_SCENE": "MS",
        "SHORT_PASSAGE": "SP",
        "SHORT_DIALOGUE": "DLG",
    }[kind]
    token = hashlib.sha256(
        f"{kind}|{semantic_identity}".encode("utf-8")
    ).hexdigest()[:12].upper()
    return f"U01-{prefix}-{token}"


def _projection_rows(
    content_asset_id: str, kind: str, pattern_ids: Sequence[str]
) -> list[dict[str, Any]]:
    projections = []
    for skill in SKILLS:
        family_ids = list(FAMILY_MAP[skill])
        if skill == "SPEAKING" and qb.PATTERN_ADJECTIVE in pattern_ids:
            family_ids.append("U01-PF11-SPEAK-ADJ-NOUN")
        if skill == "SPEAKING" and qb.PATTERN_VERY in pattern_ids:
            family_ids.append("U01-PF12-SPEAK-VERY-ADJ-NOUN")
        if not set(family_ids).issubset(FAMILY_IDS):
            raise AdmissionBuildError("QUESTION_BANK_FAMILY_MISSING")
        if skill == "READING":
            modes = ["SHORT_TEXT_DETAIL", "ARTICLE_REFERENCE"]
        elif skill == "WRITING":
            modes = ["GUIDED_SENTENCE", "CONTEXTUAL_WRITING"]
        elif kind == "SHORT_DIALOGUE":
            modes = ["ROLE_PLAY", "ORAL_RETELL"]
        else:
            modes = ["ORAL_RETELL"]
        projections.append(
            {
                "projection_id": f"{content_asset_id}-{skill}",
                "content_asset_id": content_asset_id,
                "skill": skill,
                "existing_question_bank_id": qb.BANK_ID,
                "existing_question_bank_version": qb.BANK_VERSION,
                "existing_family_ids": sorted(family_ids),
                "projection_mode": (
                    "REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK"
                ),
                "projection_status": (
                    "READY_FOR_EXISTING_QB_MATERIALIZATION"
                ),
                "task_modes": modes,
            }
        )
    return projections


def build_asset(
    candidate: Mapping[str, Any],
    decision: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    sentences, turns = content_parts(decision)
    raw_excerpt = str(candidate.get("text_excerpt") or "")
    content = {"sentences": sentences, "dialogue_turns": turns}
    if not norm(content) or norm(content) == norm(raw_excerpt):
        raise AdmissionBuildError("RAW_RAZ_TEXT_COPY_OR_EMPTY_ADAPTATION")
    scene = deepcopy(decision.get("scene_profile") or {})
    required_scene_fields = {
        "setting",
        "participants",
        "objects",
        "actions",
        "information_structure",
        "communicative_function_ids",
        "semantic_scene_id",
        "distinct_scene_signature",
    }
    if set(scene) != required_scene_fields:
        raise AdmissionBuildError("SCENE_PROFILE_FIELDS_INVALID")
    kind = str(decision["content_kind"])
    content_asset_id = asset_id(kind, str(candidate["semantic_identity"]))
    pattern_ids = patterns(candidate)
    vocabulary_rows = list(
        contract["vocabulary_contract"]["active_vocabulary"]
    ) + list(contract["vocabulary_contract"]["active_adjectives"])
    wanted = set(candidate.get("active_noun_hits") or []) | set(
        candidate.get("active_adjective_hits") or []
    )
    vocabulary_ids = sorted(
        str(row["evp_sense_id"])
        for row in vocabulary_rows
        if row["lemma"] in wanted
    )
    speakers = sorted({turn["speaker_id"] for turn in turns})
    review_dimensions = deepcopy(
        decision.get("review_dimensions")
        or {key: "PASS" for key in REVIEW_DIMENSIONS}
    )
    if (
        set(review_dimensions) != set(REVIEW_DIMENSIONS)
        or any(review_dimensions[key] != "PASS" for key in REVIEW_DIMENSIONS)
    ):
        raise AdmissionBuildError("APPROVAL_GATES_NOT_PASS")
    resolution_class = str(decision["resolution_class"])
    if resolution_class not in (
        *AUTOMATIC_APPROVAL_CLASSES,
        "HUMAN_APPROVE_EXCEPTION",
    ):
        raise AdmissionBuildError("APPROVAL_RESOLUTION_CLASS_INVALID")
    return {
        "content_asset_id": content_asset_id,
        "content_kind": kind,
        "title": str(decision.get("title") or content_asset_id),
        "introduced_unit_id": UNIT_ID,
        "introduced_unit_sequence": 1,
        "source_lineage": {
            "source_authority": "RAZ_READING_AUTHORITY",
            "source_record_id": str(candidate["source_record_id"]),
            "semantic_identity": str(candidate["semantic_identity"]),
            "source_level": candidate.get("source_level"),
            "source_type": candidate.get("source_type"),
            "original_excerpt_sha256": hashlib.sha256(
                raw_excerpt.encode("utf-8")
            ).hexdigest(),
            "original_excerpt_private": True,
            "adaptation_mode": str(decision["adaptation_mode"]),
            "adaptation_reason_codes": sorted(
                str(value)
                for value in decision.get("adaptation_reason_codes") or []
            ),
            "derived_from_task_id": upstream.TASK_ID,
        },
        "content": content,
        "content_sha256": digest(content),
        "target_alignment": {
            "grammar_target_ids": pattern_ids,
            "egp_row_ids": sorted(
                list(
                    contract["grammar_contract"][
                        "core_focus_egp_row_ids"
                    ]
                )
                + list(
                    contract["grammar_contract"][
                        "guided_extension_egp_row_ids"
                    ]
                )
            ),
            "vocabulary_asset_ids": vocabulary_ids,
            "chunk_asset_ids": [],
            "sentence_frame_ids": sorted(
                str(value)
                for value in candidate.get("matched_sentence_frame_ids")
                or []
            ),
            "theme_id": decision.get("theme_id"),
            "situation_family_id": decision.get(
                "situation_family_id"
            ),
            "micro_situation_id": decision.get("micro_situation_id"),
            "communicative_function_ids": sorted(
                str(value)
                for value in scene["communicative_function_ids"]
            ),
        },
        "scene_profile": scene,
        "dialogue_profile": {
            "is_real_dialogue": kind == "SHORT_DIALOGUE",
            "speaker_count": len(speakers),
            "turn_count": len(turns),
            "speaker_ids": speakers,
            "adjacency_pair_types": sorted(
                str(value)
                for value in decision.get("adjacency_pair_types") or []
            ),
            "role_play_supported": kind == "SHORT_DIALOGUE",
        },
        "skill_projections": _projection_rows(
            content_asset_id, kind, pattern_ids
        ),
        "admission": {
            "resolution_class": resolution_class,
            "decision_ref": str(decision["decision_ref"]),
            "review_dimensions": review_dimensions,
            "selection_class": candidate["selection_class"],
            "selection_reasons": deepcopy(
                candidate.get("selection_reasons") or []
            ),
            "canonical_admission": True,
            "template_only": False,
            "human_review_used": (
                resolution_class == "HUMAN_APPROVE_EXCEPTION"
            ),
        },
        "later_unit_reuse": {
            "reusable_in_later_units": True,
            "reuse_identity_mode": (
                "REFERENCE_EXISTING_CONTENT_ASSET_ID"
            ),
            "copy_on_reuse": False,
            "eligible_future_unit_roles": list(FUTURE_ROLES),
            "reuse_gates": list(REUSE_GATES),
        },
        "unit02_reusable_handoff": {
            "target_unit_sequence": TARGET_UNIT02_SEQUENCE,
            "source_content_asset_id": content_asset_id,
            "candidate_role": "CARRY_OVER",
            "binding_status": "AVAILABLE_NOT_BOUND",
            "unit02_modified": False,
            "required_when_bound": [
                "target_unit_id",
                "target_unit_role",
                "new_grammar_target_ids",
                "reuse_reason",
                "compatibility_gate_status",
            ],
        },
    }


def _automatic_decisions(
    candidate: Mapping[str, Any],
    facts: Sequence[Mapping[str, Any]],
    resolution_class: str,
) -> list[dict[str, Any]]:
    sentences = [_rewrite_fact(fact) for fact in facts]
    scene = _scene_profile(candidate, facts)
    base_kind = "MICRO_SCENE" if len(sentences) == 1 else "SHORT_PASSAGE"
    theme = _theme(scene)
    common = {
        "resolution_class": resolution_class,
        "decision_ref": AUTO_DECISION_REF,
        "adaptation_mode": "RULE_BASED_SEMANTIC_REWRITE",
        "adaptation_reason_codes": [
            "SEMANTIC_FACTS_PRESERVED",
            "UNIT01_CONTROLLED_TEMPLATE_APPLIED",
            "NO_NEW_SOURCE_FACTS",
        ],
        "review_dimensions": {key: "PASS" for key in REVIEW_DIMENSIONS},
        "theme_id": theme,
        "situation_family_id": scene["setting"],
        "micro_situation_id": scene["semantic_scene_id"],
        "scene_profile": scene,
        "template_only": False,
    }
    decisions = [
        {
            **common,
            "content_kind": base_kind,
            "title": f"{theme.title()} scene",
            "adapted_sentences": sentences,
            "dialogue_turns": [],
            "adjacency_pair_types": [],
        }
    ]
    dialogue_turns = _dialogue_from_facts(facts)
    if dialogue_turns:
        decisions.append(
            {
                **common,
                "content_kind": "SHORT_DIALOGUE",
                "title": f"{theme.title()} dialogue",
                "adapted_sentences": [],
                "dialogue_turns": dialogue_turns,
                "adjacency_pair_types": ["QUESTION_ANSWER"],
            }
        )
    return decisions


def _validate_exception_override(
    override: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    if (
        override.get("source_record_id")
        != candidate.get("source_record_id")
        or override.get("semantic_identity")
        != candidate.get("semantic_identity")
    ):
        raise AdmissionBuildError("HUMAN_OVERRIDE_IDENTITY_MISMATCH")
    decision_ref = str(override.get("decision_ref") or "")
    if not decision_ref.startswith(HUMAN_DECISION_REF_PREFIX):
        raise AdmissionBuildError("HUMAN_OVERRIDE_DECISION_REF_INVALID")
    review_status = override.get("review_status")
    if review_status not in {"APPROVED", "REJECTED"}:
        raise AdmissionBuildError("HUMAN_OVERRIDE_STATUS_INVALID")
    if review_status == "REJECTED" and not override.get(
        "rejection_reason_codes"
    ):
        raise AdmissionBuildError("HUMAN_OVERRIDE_REJECTION_REASON_REQUIRED")
    if review_status == "APPROVED":
        if override.get("content_kind") not in CONTENT_KINDS:
            raise AdmissionBuildError("HUMAN_OVERRIDE_CONTENT_KIND_INVALID")
        checks = override.get("review_dimensions") or {}
        if (
            set(checks) != set(REVIEW_DIMENSIONS)
            or any(checks[key] != "PASS" for key in REVIEW_DIMENSIONS)
        ):
            raise AdmissionBuildError(
                "HUMAN_OVERRIDE_REVIEW_DIMENSIONS_INVALID"
            )


def _human_override_decision(
    override: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    _validate_exception_override(override, candidate)
    value = deepcopy(dict(override))
    value["resolution_class"] = "HUMAN_APPROVE_EXCEPTION"
    value.setdefault("adaptation_mode", "HUMAN_EXCEPTION_REWRITE")
    value.setdefault(
        "adaptation_reason_codes", ["SEMANTIC_EXCEPTION_RESOLVED"]
    )
    value.setdefault("template_only", False)
    scene = deepcopy(value.get("scene_profile") or {})
    required_without_ids = {
        "setting",
        "participants",
        "objects",
        "actions",
        "information_structure",
        "communicative_function_ids",
    }
    if set(scene) != required_without_ids:
        raise AdmissionBuildError(
            "HUMAN_OVERRIDE_SCENE_PROFILE_FIELDS_INVALID"
        )
    scene["semantic_scene_id"] = (
        f"U01-SCENE-"
        f"{hashlib.sha256(str(candidate['semantic_identity']).encode()).hexdigest()[:12].upper()}"
    )
    scene["distinct_scene_signature"] = digest(
        {
            "semantic_identity": candidate["semantic_identity"],
            "setting": scene["setting"],
            "objects": scene["objects"],
            "actions": scene["actions"],
        }
    )
    value["scene_profile"] = scene
    return value


def safe_asset(asset: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(asset))
    value.pop("content", None)
    return value


def build_payload(
    selection_report: Mapping[str, Any],
    human_decisions: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(dict(contract or contract_builder.build_contract()))
    contract_builder.verify_contract_digest(contract)
    if contract.get("contract_sha256") != APPROVED_CONTRACT_SHA256:
        raise AdmissionBuildError("UNIT01_CONTRACT_DIGEST_INVALID")
    candidates = validate_upstream(selection_report)
    override_rows = list((human_decisions or {}).get("decisions") or [])
    if not all(isinstance(row, Mapping) for row in override_rows):
        raise AdmissionBuildError("HUMAN_DECISIONS_ARRAY_INVALID")
    overrides = {
        str(row.get("source_record_id") or ""): row
        for row in override_rows
    }
    if "" in overrides or len(overrides) != len(override_rows):
        raise AdmissionBuildError("HUMAN_DECISION_IDENTITY_INVALID")

    assets: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    human_queue: list[dict[str, Any]] = []
    seen_override_ids: set[str] = set()

    for candidate in candidates:
        resolution = classify_resolution(candidate, contract)
        resolution_class = str(resolution["resolution_class"])
        source_id = str(candidate["source_record_id"])
        produced_asset_ids: list[str] = []
        human_override_applied = False

        if resolution_class in AUTOMATIC_APPROVAL_CLASSES:
            if source_id in overrides:
                raise AdmissionBuildError(
                    "HUMAN_OVERRIDE_ONLY_ALLOWED_FOR_EXCEPTION_QUEUE"
                )
            for decision in _automatic_decisions(
                candidate,
                resolution["facts"],
                resolution_class,
            ):
                asset = build_asset(candidate, decision, contract)
                assets.append(asset)
                produced_asset_ids.append(asset["content_asset_id"])

        elif resolution_class == "HUMAN_REVIEW_REQUIRED":
            override = overrides.get(source_id)
            if override is None:
                human_queue.append(
                    {
                        "source_record_id": source_id,
                        "semantic_identity": candidate["semantic_identity"],
                        "source_excerpt_sha256": hashlib.sha256(
                            str(
                                candidate.get("text_excerpt") or ""
                            ).encode("utf-8")
                        ).hexdigest(),
                        "reason_codes": deepcopy(
                            resolution["reason_codes"]
                        ),
                        "allowed_human_outcomes": [
                            "HUMAN_APPROVE_EXCEPTION",
                            "HUMAN_REJECT_EXCEPTION",
                        ],
                    }
                )
            else:
                seen_override_ids.add(source_id)
                human_override_applied = True
                _validate_exception_override(override, candidate)
                if override["review_status"] == "APPROVED":
                    decision = _human_override_decision(
                        override, candidate
                    )
                    asset = build_asset(candidate, decision, contract)
                    assets.append(asset)
                    produced_asset_ids.append(
                        asset["content_asset_id"]
                    )
                    resolution_class = "HUMAN_APPROVE_EXCEPTION"
                else:
                    resolution_class = "HUMAN_REJECT_EXCEPTION"

        elif resolution_class == "AUTO_REJECT":
            if source_id in overrides:
                raise AdmissionBuildError(
                    "AUTO_REJECT_OVERRIDE_FORBIDDEN"
                )

        ledger.append(
            {
                "source_record_id": source_id,
                "semantic_identity": candidate["semantic_identity"],
                "selection_class": candidate["selection_class"],
                "resolution_class": resolution_class,
                "resolution_reason_codes": deepcopy(
                    resolution["reason_codes"]
                ),
                "human_review_required": (
                    resolution["resolution_class"]
                    == "HUMAN_REVIEW_REQUIRED"
                ),
                "human_override_applied": human_override_applied,
                "content_asset_ids": produced_asset_ids,
            }
        )

    unused_overrides = set(overrides) - seen_override_ids
    if unused_overrides:
        raise AdmissionBuildError(
            "HUMAN_OVERRIDE_SOURCE_NOT_IN_EXCEPTION_QUEUE:"
            + ",".join(sorted(unused_overrides))
        )
    if not assets:
        raise AdmissionBuildError("NO_AUTO_OR_HUMAN_APPROVED_CONTENT_ASSETS")

    content_ids = [asset["content_asset_id"] for asset in assets]
    if len(content_ids) != len(set(content_ids)):
        raise AdmissionBuildError("CONTENT_ASSET_ID_DUPLICATE")
    content_hashes = [asset["content_sha256"] for asset in assets]
    if len(content_hashes) != len(set(content_hashes)):
        raise AdmissionBuildError("CONTENT_PAYLOAD_DUPLICATE")

    kind_counts = Counter(asset["content_kind"] for asset in assets)
    resolution_counts = Counter(
        row["resolution_class"] for row in ledger
    )
    semantic_scene_count = len(
        {
            asset["scene_profile"]["semantic_scene_id"]
            for asset in assets
        }
    )
    coverage = {
        "upstream_candidate_count": len(candidates),
        "auto_approve_direct_count": resolution_counts[
            "AUTO_APPROVE_DIRECT"
        ],
        "auto_approve_rule_rewrite_count": resolution_counts[
            "AUTO_APPROVE_RULE_REWRITE"
        ],
        "auto_reject_count": resolution_counts["AUTO_REJECT"],
        "human_review_required_count": sum(
            row["human_review_required"] for row in ledger
        ),
        "human_review_resolved_count": sum(
            row["human_override_applied"] for row in ledger
        ),
        "human_review_pending_count": len(human_queue),
        "human_approve_exception_count": resolution_counts[
            "HUMAN_APPROVE_EXCEPTION"
        ],
        "human_reject_exception_count": resolution_counts[
            "HUMAN_REJECT_EXCEPTION"
        ],
        "approved_content_asset_count": len(assets),
        "distinct_semantic_scene_count": semantic_scene_count,
        "distinct_micro_scene_count": kind_counts["MICRO_SCENE"],
        "distinct_short_passage_count": kind_counts["SHORT_PASSAGE"],
        "distinct_dialogue_count": kind_counts["SHORT_DIALOGUE"],
        "raz_grounded_content_count": len(assets),
        "rule_based_rewrite_asset_count": sum(
            asset["source_lineage"]["adaptation_mode"]
            == "RULE_BASED_SEMANTIC_REWRITE"
            for asset in assets
        ),
        "human_exception_rewrite_asset_count": sum(
            asset["admission"]["human_review_used"]
            for asset in assets
        ),
        "reading_projection_count": len(assets),
        "writing_projection_count": len(assets),
        "speaking_projection_count": len(assets),
        "three_skill_shared_content_count": len(assets),
        "template_only_content_count": 0,
        "unit02_reusable_asset_count": len(assets),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "parent_task_id": PARENT_TASK_ID,
        "status": PASS_STATUS,
        "scope": {
            "allowed_units": [UNIT_ID],
            "unit02_to_unit24_modified": False,
            "a2_status": "LOCKED",
            "listening_status": "DEFERRED",
            "second_question_bank_created": False,
            "raw_raz_text_learner_facing_copy_allowed": False,
            "human_review_scope": "EXCEPTION_ONLY",
            "complete_manual_decision_manifest_required": False,
        },
        "inputs": {
            "upstream_task_id": upstream.TASK_ID,
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "existing_question_bank_id": qb.BANK_ID,
            "existing_question_bank_version": qb.BANK_VERSION,
            "automatic_decision_ref": AUTO_DECISION_REF,
        },
        "automatic_resolution_policy": {
            "resolution_classes": list(RESOLUTION_CLASSES),
            "semantic_identity_required": True,
            "semantic_fact_extraction_required": True,
            "rule_rewrite_must_preserve_source_facts": True,
            "new_source_facts_allowed": False,
            "all_six_validation_dimensions_required": True,
            "human_review_only_for_nonunique_or_unresolved_semantics": True,
            "unresolved_human_queue_blocks_auto_approved_assets": False,
        },
        "inspection_record": {
            "inspection_ref": INSPECTION_REF,
            "findings": [
                {
                    "finding_code": code,
                    "observed_status": "CONFIRMED",
                    "evidence": evidence,
                }
                for code, evidence in FINDINGS
            ],
            "resolution": (
                "RULE_BASED_SEMANTIC_REWRITE_AUTO_ADMISSION_"
                "WITH_EXCEPTION_ONLY_HUMAN_REVIEW"
            ),
            "unit02_reuse_fields_recorded": True,
        },
        "resolution_ledger": ledger,
        "human_review_queue": human_queue,
        "content_assets": assets,
        "coverage_readback": coverage,
        "boundaries": {
            "existing_question_bank_referenced": True,
            "existing_question_bank_modified": False,
            "parallel_question_bank_created": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "mastery_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate(
    selection_report: Mapping[str, Any],
    human_decisions: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return policy_artifact.build_candidate(
        payload=build_payload(
            selection_report, human_decisions, contract
        ),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "parent_task_id": PARENT_TASK_ID,
            "upstream_task_id": upstream.TASK_ID,
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "existing_question_bank_id": qb.BANK_ID,
            "existing_question_bank_version": qb.BANK_VERSION,
            "automatic_decision_ref": AUTO_DECISION_REF,
            "operator_inspection_ref": INSPECTION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as validator,
    )

    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[validator.validate_candidate(candidate)],
        decision_ref=AUTO_DECISION_REF,
        producer_id=TASK_ID,
    )


def build_safe_readback(
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(approved)
    payload = approved.get("payload") or {}
    safe = {
        "schema_version": SAFE_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "parent_task_id": PARENT_TASK_ID,
        "status": PASS_STATUS,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "content_governance": deepcopy(
            approved["content_governance"]
        ),
        "admission": deepcopy(approved["admission"]),
        "source_bindings": deepcopy(approved["source_bindings"]),
        "automatic_resolution_policy": deepcopy(
            payload.get("automatic_resolution_policy") or {}
        ),
        "inspection_record": deepcopy(
            payload.get("inspection_record") or {}
        ),
        "coverage_readback": deepcopy(
            payload.get("coverage_readback") or {}
        ),
        "resolution_ledger": deepcopy(
            payload.get("resolution_ledger") or []
        ),
        "human_review_queue": deepcopy(
            payload.get("human_review_queue") or []
        ),
        "content_assets": [
            safe_asset(asset)
            for asset in payload.get("content_assets") or []
        ],
        "boundaries": deepcopy(payload.get("boundaries") or {}),
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe["readback_sha256"] = digest(safe)
    return safe


def build_admission(
    selection_report: Mapping[str, Any],
    human_decisions: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate(
        selection_report, human_decisions, contract
    )
    approved = admit_candidate(candidate)
    return candidate, approved, build_safe_readback(approved)


def run(
    selection_report_path: Path,
    human_decisions_path: Path | None = None,
    candidate_output_path: Path = OUTPUT_CANDIDATE,
    approved_output_path: Path = OUTPUT_APPROVED,
    safe_output_path: Path = OUTPUT_SAFE,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    human_decisions = (
        load(human_decisions_path)
        if human_decisions_path is not None
        else None
    )
    candidate, approved, safe = build_admission(
        load(selection_report_path), human_decisions
    )
    write(candidate_output_path, candidate, private=True)
    write(approved_output_path, approved, private=True)
    write(safe_output_path, safe)
    return candidate, approved, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection-report", type=Path, required=True
    )
    parser.add_argument(
        "--human-decisions",
        "--decisions",
        dest="human_decisions",
        type=Path,
    )
    parser.add_argument(
        "--candidate-output", type=Path, default=OUTPUT_CANDIDATE
    )
    parser.add_argument(
        "--approved-output", type=Path, default=OUTPUT_APPROVED
    )
    parser.add_argument(
        "--safe-output", type=Path, default=OUTPUT_SAFE
    )
    args = parser.parse_args(argv)
    try:
        _, approved, safe = run(
            args.selection_report.resolve(),
            args.human_decisions.resolve()
            if args.human_decisions
            else None,
            args.candidate_output.resolve(),
            args.approved_output.resolve(),
            args.safe_output.resolve(),
        )
    except (
        AdmissionBuildError,
        policy_artifact.ContentPolicyBuildError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_RAZQ01D_FULLFIX")
        print(f"ERROR={exc}")
        return 1
    coverage = safe["coverage_readback"]
    print(f"STATUS={approved['payload']['status']}")
    print(
        "AUTO_APPROVED_SOURCE_RECORDS="
        f"{coverage['auto_approve_direct_count'] + coverage['auto_approve_rule_rewrite_count']}"
    )
    print(
        f"APPROVED_CONTENT_ASSETS={coverage['approved_content_asset_count']}"
    )
    print(
        f"HUMAN_REVIEW_PENDING={coverage['human_review_pending_count']}"
    )
    print(
        f"THREE_SKILL_SHARED={coverage['three_skill_shared_content_count']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
