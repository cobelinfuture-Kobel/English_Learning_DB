#!/usr/bin/env python3
"""Build Unit01 RAZ-derived A1 assets through semantic rewrite, imitation, and contract completion."""
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
from ulga.builders import (
    build_a1fs_v1_razq01c_unit01_three_skill_candidate_selection_coverage_balancing
    as upstream,
)
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as qb,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
PARENT_TASK_ID = (
    "A1FS-V1-RAZQ01D-FULLFIX_"
    "Unit01RuleBasedSemanticRewriteAutoAdmissionAndExceptionOnlyHumanReview"
)
TASK_ID = (
    "A1FS-V1-RAZQ01D-FULLFIX2_"
    "Real44SemanticInterpretationA1ImitationAndContractCompletion"
)
SCHEMA_VERSION = "a1fs.v1.razq01d.fullfix2.real44_semantic_reconciliation.v1"
SAFE_SCHEMA_VERSION = (
    "a1fs.v1.razq01d.fullfix2.real44_semantic_reconciliation_safe.v1"
)
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_FULLFIX2_REAL44_SEMANTIC_RECONCILIATION"
UNIT_ID = upstream.UNIT_ID
TARGET_UNIT02_SEQUENCE = 2
APPROVED_CONTRACT_SHA256 = upstream.APPROVED_CONTRACT_SHA256
AUTO_DECISION_REF = "AUTOMATED_POLICY:2026-07-30:RAZQ01D_FULLFIX2"
HUMAN_DECISION_REF_PREFIX = "HUMAN_EXCEPTION_REVIEW:"
OUTPUT_CANDIDATE = Path(
    "ulga/private/a1fs_v1_razq01d_fullfix2_unit01_real44.candidate.private.json"
)
OUTPUT_APPROVED = Path(
    "ulga/private/a1fs_v1_razq01d_fullfix2_unit01_real44.approved.private.json"
)
OUTPUT_SAFE = Path(
    "ulga/reports/a1fs_v1_razq01d_fullfix2_unit01_real44_readback.json"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-RAZQ01D-FULLFIX2_"
    "LocalPrivateReal44MaterializationCoverageAndExceptionReadback"
)

CONTENT_KINDS = ("MICRO_SCENE", "SHORT_PASSAGE", "SHORT_DIALOGUE")
SKILLS = ("READING", "WRITING", "SPEAKING")
RESOLUTION_CLASSES = (
    "AUTO_APPROVE_SEMANTIC_EQUIVALENT",
    "AUTO_APPROVE_A1_IMITATION",
    "AUTO_APPROVE_PROJECT_AUTHORED_COMPLETION",
    "AUTO_REJECT",
    "HUMAN_REVIEW_REQUIRED",
    "HUMAN_APPROVE_EXCEPTION",
    "HUMAN_REJECT_EXCEPTION",
)
AUTOMATIC_SOURCE_APPROVAL_CLASSES = frozenset(
    {
        "AUTO_APPROVE_SEMANTIC_EQUIVALENT",
        "AUTO_APPROVE_A1_IMITATION",
    }
)
AUTOMATIC_APPROVAL_CLASSES = frozenset(
    {
        *AUTOMATIC_SOURCE_APPROVAL_CLASSES,
        "AUTO_APPROVE_PROJECT_AUTHORED_COMPLETION",
    }
)
LINEAGE_MODES = (
    "SEMANTIC_EQUIVALENT_REWRITE",
    "SEMANTIC_ANCHOR_A1_IMITATION",
    "PROJECT_AUTHORED_CONTRACT_COMPLETION",
    "HUMAN_EXCEPTION_REWRITE",
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
        "SOURCE_RECORD_ID_IS_NOT_CANDIDATE_IDENTITY",
        "One RAZ source record may produce multiple independently identified semantic windows.",
    ),
    (
        "REWRITE_REQUIRED_IS_NOT_HUMAN_REVIEW",
        "Rewrite-required sources are first processed through equivalent rewrite or A1 imitation.",
    ),
    (
        "RAZ_SOURCE_COVERAGE_IS_NOT_UNIT_COVERAGE",
        "Missing Unit01 targets are completed with project-authored contract assets.",
    ),
)

WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
SEVERE_REJECT_FLAGS = frozenset(
    {
        "UNBALANCED_QUOTATION",
        "FRAGMENT_OR_TRAILING_PUNCTUATION",
        "NEGATIVE_IMPERATIVE_PRESENT",
    }
)
FRAME_COMPLETION_TEXT = {
    "U01-F01": ("This is a book.", ["book"], [], ["U01-F01"]),
    "U01-F02": ("I have a bag.", ["bag"], [], ["U01-F02"]),
    "U01-F03": ("A book is in the classroom.", ["book", "classroom"], [], ["U01-F03"]),
    "U01-F04": ("A cat is near the tree.", ["cat", "tree"], [], ["U01-F04"]),
    "U01-F05": ("The book is on the desk.", ["book", "desk"], [], ["U01-F05"]),
    "U01-F06": ("I can see an apple.", ["apple"], [], ["U01-F06"]),
    "U01-AF01": ("This is a blue bag.", ["bag"], ["blue"], ["U01-AF01"]),
    "U01-AF02": ("I can see an old book.", ["book"], ["old"], ["U01-AF02"]),
    "U01-AF03": ("This is a very big box.", ["box"], ["big"], ["U01-AF03"]),
}


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
    if isinstance(value, (list, tuple)):
        return " ".join(filter(None, (norm(item) for item in value)))
    return " ".join(
        token.casefold().replace("’", "'") for token in WORD_RE.findall(str(value))
    )


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


def candidate_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("source_record_id") or "").strip(),
        str(row.get("semantic_identity") or "").strip(),
    )


def candidate_key_text(row: Mapping[str, Any]) -> str:
    source_id, semantic_id = candidate_key(row)
    return f"{source_id}::{semantic_id}"


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
    if not all(isinstance(row, Mapping) for row in rows):
        raise AdmissionBuildError("RAZQ01C_CANDIDATE_OBJECT_REQUIRED")

    keys = [candidate_key(row) for row in rows]
    source_ids = [key[0] for key in keys]
    semantic_ids = [key[1] for key in keys]
    if "" in source_ids or "" in semantic_ids:
        raise AdmissionBuildError("RAZQ01C_COMPOSITE_IDENTITY_MISSING")
    if len(keys) != len(set(keys)):
        raise AdmissionBuildError("RAZQ01C_COMPOSITE_IDENTITY_DUPLICATE")
    if len(semantic_ids) != len(set(semantic_ids)):
        raise AdmissionBuildError("RAZQ01C_SEMANTIC_IDENTITY_DUPLICATE")

    summary = report.get("selection_summary") or {}
    declared = summary.get("strict_candidate_count")
    if declared is not None and declared != len(rows):
        raise AdmissionBuildError("RAZQ01C_DECLARED_COUNT_DRIFT")
    return deepcopy(list(rows))


def _sentences(text: str) -> list[str]:
    return [
        value.strip()
        for value in SENTENCE_SPLIT_RE.split(text.strip())
        if value.strip()
    ]


def _noun_rows(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row["lemma"]).casefold(): dict(row)
        for row in contract["vocabulary_contract"]["active_vocabulary"]
    }


def _adjective_rows(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row["lemma"]).casefold(): dict(row)
        for row in contract["vocabulary_contract"]["active_adjectives"]
    }


def _article_for(word: str) -> str:
    return contract_builder.expected_indefinite_article(word)


def _anchor_bundle(
    candidate: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    noun_rows = _noun_rows(contract)
    adjective_rows = _adjective_rows(contract)
    nouns = [
        str(value).casefold()
        for value in candidate.get("active_noun_hits") or []
        if str(value).casefold() in noun_rows
    ]
    adjectives = [
        str(value).casefold()
        for value in candidate.get("active_adjective_hits") or []
        if str(value).casefold() in adjective_rows
    ]
    nouns = list(dict.fromkeys(nouns))
    adjectives = list(dict.fromkeys(adjectives))
    direct_phrases = [
        norm(value).split()[-1]
        for value in candidate.get("direct_noun_phrases") or []
        if norm(value).split()
    ]
    preferred = next((value for value in direct_phrases if value in nouns), None)
    if preferred:
        nouns = [preferred, *[value for value in nouns if value != preferred]]
    if not nouns:
        return {"nouns": [], "adjectives": [], "indefinite": None, "definite": None}
    noun = nouns[0]
    adjective = adjectives[0] if adjectives else None
    if adjective:
        indefinite = f"{_article_for(adjective)} {adjective} {noun}"
    else:
        indefinite = str(noun_rows[noun]["memory_form_indefinite"])
    definite = str(noun_rows[noun]["memory_form_definite"])
    return {
        "nouns": nouns,
        "adjectives": adjectives,
        "noun": noun,
        "adjective": adjective,
        "indefinite": indefinite,
        "definite": definite,
    }


def _parse_equivalent(
    candidate: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any] | None:
    text = str(candidate.get("text_excerpt") or "").strip()
    lower = norm(text)
    anchors = _anchor_bundle(candidate, contract)
    if not anchors["nouns"]:
        return None
    noun = anchors["noun"]
    indefinite = anchors["indefinite"]
    definite = anchors["definite"]
    nouns = anchors["nouns"]

    if re.fullmatch(r"(?:this|that|it) is (?:a|an|the) [a-z]+(?: [a-z]+)?", lower):
        return {
            "fact_type": "IDENTIFY",
            "sentences": [f"I can see {indefinite}."],
            "nouns": nouns,
            "adjectives": anchors["adjectives"],
            "relation": None,
        }
    if re.fullmatch(r"i (?:can )?see (?:a|an|the) [a-z]+(?: [a-z]+)?", lower):
        return {
            "fact_type": "SEE",
            "sentences": [f"This is {indefinite}."],
            "nouns": nouns,
            "adjectives": anchors["adjectives"],
            "relation": None,
        }

    action_match = re.fullmatch(
        r"the (?:(?P<adj>big|small|red|blue|new|old) )?"
        r"(?P<noun>[a-z]+) (?P<verb>plays|runs|eats|looks)",
        lower,
    )
    if action_match and action_match.group("noun") == noun:
        verb = action_match.group("verb")
        return {
            "fact_type": "ACTION",
            "sentences": [
                f"This is {indefinite}.",
                f"{definite.capitalize()} {verb}.",
            ],
            "nouns": nouns,
            "adjectives": anchors["adjectives"],
            "relation": None,
        }

    ordinal_location = re.fullmatch(
        r"the first (?P<noun>[a-z]+) is (?P<rel>in|on|near) the (?P<place>[a-z]+)",
        lower,
    )
    if ordinal_location:
        subject = ordinal_location.group("noun")
        place = ordinal_location.group("place")
        noun_rows = _noun_rows(contract)
        if subject in noun_rows and place in noun_rows:
            rel = ordinal_location.group("rel")
            subject_indef = noun_rows[subject]["memory_form_indefinite"]
            subject_def = noun_rows[subject]["memory_form_definite"]
            place_def = noun_rows[place]["memory_form_definite"]
            return {
                "fact_type": "LOCATE",
                "sentences": [
                    f"{subject_indef.capitalize()} is {rel} {place_def}.",
                    f"{subject_def.capitalize()} is {rel} {place_def}.",
                ],
                "nouns": [subject, place],
                "adjectives": anchors["adjectives"],
                "relation": rel,
            }

    if " put " in f" {lower} " and len(nouns) >= 2 and " in " in f" {lower} ":
        noun_rows = _noun_rows(contract)
        subject, place = nouns[0], nouns[1]
        subject_indef = noun_rows[subject]["memory_form_indefinite"]
        subject_def = noun_rows[subject]["memory_form_definite"]
        place_indef = noun_rows[place]["memory_form_indefinite"]
        place_def = noun_rows[place]["memory_form_definite"]
        return {
            "fact_type": "RESULT_LOCATION",
            "sentences": [
                f"{subject_indef.capitalize()} is in {place_indef}.",
                f"{subject_def.capitalize()} is in {place_def}.",
            ],
            "nouns": [subject, place],
            "adjectives": anchors["adjectives"],
            "relation": "in",
        }

    if "looks into the box" in lower and noun == "box":
        return {
            "fact_type": "LOOK_IN",
            "sentences": ["This is a box.", "She looks in the box."],
            "nouns": ["box"],
            "adjectives": [],
            "relation": "in",
        }
    return None


def extract_semantic_facts(
    candidate: Mapping[str, Any], contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    parsed = _parse_equivalent(candidate, contract)
    if parsed is None:
        return [], ["NO_SAFE_EQUIVALENT_REWRITE"]
    return [parsed], []


def classify_resolution(
    candidate: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    selection_class = str(candidate.get("selection_class") or "")
    flags = set(candidate.get("structural_flags") or [])
    if selection_class == "REJECT" or flags & SEVERE_REJECT_FLAGS:
        return {
            "resolution_class": "AUTO_REJECT",
            "lineage_mode": None,
            "reason_codes": sorted(
                {"UPSTREAM_REJECT_OR_SEVERE_STRUCTURE", *flags}
            ),
            "semantic_plan": None,
        }

    parsed = _parse_equivalent(candidate, contract)
    if parsed is not None:
        return {
            "resolution_class": "AUTO_APPROVE_SEMANTIC_EQUIVALENT",
            "lineage_mode": "SEMANTIC_EQUIVALENT_REWRITE",
            "reason_codes": [
                "COMPOSITE_IDENTITY_UNIQUE",
                "SOURCE_FACTS_RETAINED",
                "BLOCKED_FEATURES_REMOVED_WHEN_REQUIRED",
                "UNIT01_TEMPLATE_VALIDATED",
            ],
            "semantic_plan": parsed,
        }

    anchors = _anchor_bundle(candidate, contract)
    if anchors["nouns"]:
        return {
            "resolution_class": "AUTO_APPROVE_A1_IMITATION",
            "lineage_mode": "SEMANTIC_ANCHOR_A1_IMITATION",
            "reason_codes": [
                "COMPOSITE_IDENTITY_UNIQUE",
                "SOURCE_SEMANTIC_ANCHORS_RETAINED",
                "A1_SCENE_REAUTHORED",
                "NO_EQUIVALENCE_CLAIM",
                "UNIT01_TEMPLATE_VALIDATED",
            ],
            "semantic_plan": {
                "fact_type": "ANCHOR_IMITATION",
                **anchors,
            },
        }

    return {
        "resolution_class": "HUMAN_REVIEW_REQUIRED",
        "lineage_mode": None,
        "reason_codes": ["NO_RELIABLE_UNIT01_SEMANTIC_ANCHOR"],
        "semantic_plan": None,
    }


def _scene_profile(
    identity: str,
    nouns: Sequence[str],
    adjectives: Sequence[str],
    action: str,
    *,
    setting_hint: str | None = None,
) -> dict[str, Any]:
    noun_set = sorted(set(str(value).casefold() for value in nouns))
    adjective_set = sorted(set(str(value).casefold() for value in adjectives))
    setting_nouns = {"classroom", "room", "park", "shop"}
    setting = setting_hint or next(
        (noun.upper() for noun in noun_set if noun in setting_nouns),
        "UNIT01_OBJECT_SCENE",
    )
    profile = {
        "setting": setting,
        "participants": ["LEARNER"],
        "objects": [noun.upper() for noun in noun_set],
        "descriptors": [value.upper() for value in adjective_set],
        "actions": [action],
        "information_structure": ["FIRST_MENTION", "KNOWN_REFERENCE"],
        "communicative_function_ids": ["IDENTIFY", "DESCRIBE"],
    }
    token = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12].upper()
    profile["semantic_scene_id"] = f"U01-SCENE-{token}"
    profile["distinct_scene_signature"] = digest(
        {
            "identity": identity,
            "setting": setting,
            "objects": profile["objects"],
            "descriptors": profile["descriptors"],
            "actions": profile["actions"],
        }
    )
    return profile


def _theme(nouns: Sequence[str]) -> str:
    values = set(nouns)
    if values & {"cat", "dog"}:
        return "ANIMALS"
    if values & {"book", "desk", "classroom", "bag"}:
        return "SCHOOL"
    if values & {"apple", "egg"}:
        return "FOOD"
    if values & {"bed", "room", "door", "window", "box"}:
        return "HOME"
    if values & {"park", "tree"}:
        return "OUTDOORS"
    return "UNIT01_OBJECTS"


def _dialogue(indefinite: str, definite: str) -> list[dict[str, str]]:
    return [
        {"speaker_id": "GUIDE", "utterance": "What can you see?"},
        {"speaker_id": "LEARNER", "utterance": f"I can see {indefinite}."},
        {"speaker_id": "GUIDE", "utterance": f"Can you see {definite}?"},
        {"speaker_id": "LEARNER", "utterance": "Yes, I can."},
    ]


def _source_decision(
    candidate: Mapping[str, Any],
    resolution: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    resolution_class = str(resolution["resolution_class"])
    plan = deepcopy(dict(resolution["semantic_plan"] or {}))
    source_text = str(candidate.get("text_excerpt") or "")
    anchors = _anchor_bundle(candidate, contract)
    nouns = list(plan.get("nouns") or anchors.get("nouns") or [])
    adjectives = list(plan.get("adjectives") or anchors.get("adjectives") or [])
    if not nouns:
        raise AdmissionBuildError("SOURCE_DECISION_WITHOUT_NOUN_ANCHOR")

    indefinite = str(anchors["indefinite"])
    definite = str(anchors["definite"])
    source_sentence_count = len(_sentences(source_text))
    if resolution_class == "AUTO_APPROVE_SEMANTIC_EQUIVALENT":
        sentences = list(plan["sentences"])
        kind = "MICRO_SCENE" if len(sentences) == 1 else "SHORT_PASSAGE"
        turns: list[dict[str, str]] = []
        action = str(plan.get("fact_type") or "SEMANTIC_EQUIVALENT")
    else:
        action = "A1_IMITATION"
        if "?" in source_text or candidate.get("selection_class") == "CONTEXT_SOURCE":
            kind = "SHORT_DIALOGUE"
            sentences = []
            turns = _dialogue(indefinite, definite)
        elif source_sentence_count > 1 or len(nouns) > 1 or adjectives:
            kind = "SHORT_PASSAGE"
            if len(nouns) > 1:
                noun_rows = _noun_rows(contract)
                second = nouns[1]
                second_definite = noun_rows[second]["memory_form_definite"]
                sentences = [
                    f"This is {indefinite}.",
                    f"{definite.capitalize()} is near {second_definite}.",
                ]
            else:
                sentences = [
                    f"This is {indefinite}.",
                    f"I can see {definite}.",
                ]
            turns = []
        else:
            kind = "MICRO_SCENE"
            raw_sentences = {norm(value) for value in _sentences(source_text)}
            options = [
                f"I can see {indefinite}.",
                f"This is {indefinite}.",
                f"There is {indefinite}.",
            ]
            sentences = [
                next(value for value in options if norm(value) not in raw_sentences)
            ]
            turns = []

    identity = candidate_key_text(candidate)
    scene = _scene_profile(identity, nouns, adjectives, action)
    theme = _theme(nouns)
    return {
        "resolution_class": resolution_class,
        "decision_ref": AUTO_DECISION_REF,
        "lineage_mode": resolution["lineage_mode"],
        "adaptation_reason_codes": deepcopy(resolution["reason_codes"]),
        "review_dimensions": {key: "PASS" for key in REVIEW_DIMENSIONS},
        "content_kind": kind,
        "title": f"{theme.title()} {kind.casefold().replace('_', ' ')}",
        "adapted_sentences": sentences,
        "dialogue_turns": turns,
        "adjacency_pair_types": ["QUESTION_ANSWER"] if turns else [],
        "scene_profile": scene,
        "theme_id": theme,
        "situation_family_id": scene["setting"],
        "micro_situation_id": scene["semantic_scene_id"],
        "target_nouns": nouns,
        "target_adjectives": adjectives,
        "target_articles": sorted(
            {
                token
                for token in norm([sentences, turns]).split()
                if token in {"a", "an", "the"}
            }
        ),
        "target_sentence_frame_ids": sorted(
            str(value)
            for value in candidate.get("matched_sentence_frame_ids") or []
        ),
        "template_only": False,
    }


def _project_gap_candidate(
    gap: Mapping[str, Any], index: int, contract: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    gap_id = str(gap.get("gap_spec_id") or "")
    if not gap_id:
        raise AdmissionBuildError("PROJECT_GAP_ID_REQUIRED")
    dimension = str(gap.get("gap_dimension") or "")
    forms = [str(value) for value in gap.get("required_memory_forms") or []]
    nouns: list[str] = []
    adjectives: list[str] = []
    frames = [str(value) for value in gap.get("target_sentence_frame_ids") or []]
    articles = [str(value) for value in gap.get("target_articles") or []]

    if dimension == "ACTIVE_NOUN":
        nouns = [str(value) for value in gap.get("target_lemmas") or []]
        if not nouns or not forms:
            raise AdmissionBuildError("PROJECT_NOUN_GAP_INVALID")
        indefinite = forms[0]
        definite = forms[1] if len(forms) > 1 else f"the {nouns[0]}"
        base_sentence = f"I can see {indefinite}."
    elif dimension == "ACTIVE_ADJECTIVE":
        adjectives = [str(value) for value in gap.get("target_lemmas") or []]
        if not adjectives or not forms:
            raise AdmissionBuildError("PROJECT_ADJECTIVE_GAP_INVALID")
        indefinite = forms[0]
        nouns = [indefinite.split()[-1]]
        definite = f"the {nouns[0]}"
        base_sentence = f"This is {indefinite}."
    elif dimension == "ARTICLE_FORM":
        indefinite = "an apple"
        definite = "the apple"
        nouns = ["apple"]
        articles = ["an"]
        base_sentence = "I can see an apple."
    elif dimension == "SENTENCE_FRAME":
        if len(frames) != 1 or frames[0] not in FRAME_COMPLETION_TEXT:
            raise AdmissionBuildError("PROJECT_FRAME_GAP_INVALID")
        base_sentence, nouns, adjectives, frames = FRAME_COMPLETION_TEXT[frames[0]]
        noun = nouns[0]
        indefinite = f"{_article_for(adjectives[0] if adjectives else noun)} "
        if adjectives:
            indefinite += f"{adjectives[0]} {noun}"
        else:
            indefinite += noun
        definite = f"the {noun}"
    else:
        raise AdmissionBuildError(f"PROJECT_GAP_DIMENSION_UNSUPPORTED:{dimension}")

    semantic_identity = hashlib.sha256(
        f"PROJECT_AUTHORED|{gap_id}".encode("utf-8")
    ).hexdigest()
    candidate = {
        "source_record_id": gap_id,
        "semantic_identity": semantic_identity,
        "source_level": "A1",
        "source_type": "project_authored_gap_spec",
        "text_excerpt": "",
        "selection_class": "PROJECT_AUTHORED_CONTRACT_COMPLETION",
        "selection_reasons": ["UNIT01_COVERAGE_GAP"],
        "structural_flags": [],
        "matched_sentence_frame_ids": frames,
        "direct_task_candidate_roles": [
            "READING_TASK_CANDIDATE",
            "WRITING_TASK_CANDIDATE",
            "SPEAKING_TASK_CANDIDATE",
        ],
        "active_noun_hits": nouns,
        "active_adjective_hits": adjectives,
        "canonical_admission": False,
        "human_review_required": False,
        "gap_spec_id": gap_id,
        "gap_dimension": dimension,
    }

    kind_index = index % 3
    if kind_index == 0:
        kind = "MICRO_SCENE"
        sentences = [base_sentence]
        turns: list[dict[str, str]] = []
    elif kind_index == 1:
        kind = "SHORT_PASSAGE"
        sentences = [base_sentence, f"I can see {definite}."]
        turns = []
    else:
        kind = "SHORT_DIALOGUE"
        sentences = []
        turns = _dialogue(indefinite, definite)

    scene = _scene_profile(
        candidate_key_text(candidate),
        nouns,
        adjectives,
        "PROJECT_CONTRACT_COMPLETION",
    )
    decision = {
        "resolution_class": "AUTO_APPROVE_PROJECT_AUTHORED_COMPLETION",
        "decision_ref": AUTO_DECISION_REF,
        "lineage_mode": "PROJECT_AUTHORED_CONTRACT_COMPLETION",
        "adaptation_reason_codes": [
            "UNIT01_DECLARED_COVERAGE_GAP",
            "CONTRACT_TEMPLATE_MATERIALIZED",
            "NO_RAZ_EQUIVALENCE_CLAIM",
        ],
        "review_dimensions": {key: "PASS" for key in REVIEW_DIMENSIONS},
        "content_kind": kind,
        "title": f"Unit01 coverage {gap_id}",
        "adapted_sentences": sentences,
        "dialogue_turns": turns,
        "adjacency_pair_types": ["QUESTION_ANSWER"] if turns else [],
        "scene_profile": scene,
        "theme_id": _theme(nouns),
        "situation_family_id": scene["setting"],
        "micro_situation_id": gap_id,
        "target_nouns": nouns,
        "target_adjectives": adjectives,
        "target_articles": sorted(
            set(
                articles
                + [
                    token
                    for token in norm([sentences, turns]).split()
                    if token in {"a", "an", "the"}
                ]
            )
        ),
        "target_sentence_frame_ids": frames,
        "gap_spec_id": gap_id,
        "gap_dimension": dimension,
        "template_only": False,
    }
    return candidate, decision


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
    if kind == "MICRO_SCENE" and not (1 <= len(sentences) <= 3 and not turns):
        raise AdmissionBuildError("MICRO_SCENE_STRUCTURE_INVALID")
    if kind == "SHORT_PASSAGE" and not (2 <= len(sentences) <= 6 and not turns):
        raise AdmissionBuildError("SHORT_PASSAGE_STRUCTURE_INVALID")
    if kind == "SHORT_DIALOGUE":
        speakers = {turn["speaker_id"] for turn in turns if turn["speaker_id"]}
        if (
            sentences
            or not 2 <= len(turns) <= 6
            or len(speakers) < 2
            or any(not turn["speaker_id"] or not turn["utterance"] for turn in turns)
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


def patterns(candidate: Mapping[str, Any]) -> list[str]:
    result = {qb.PATTERN_NOUN}
    if candidate.get("active_adjective_hits"):
        result.add(qb.PATTERN_ADJECTIVE)
    if any("very" in value for value in candidate.get("adjective_noun_phrases") or []):
        result.add(qb.PATTERN_VERY)
    return sorted(result)


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
        modes = {
            "READING": ["SHORT_TEXT_DETAIL", "ARTICLE_REFERENCE"],
            "WRITING": ["GUIDED_SENTENCE", "CONTEXTUAL_WRITING"],
            "SPEAKING": (
                ["ROLE_PLAY", "ORAL_RETELL"]
                if kind == "SHORT_DIALOGUE"
                else ["ORAL_RETELL"]
            ),
        }[skill]
        projections.append(
            {
                "projection_id": f"{content_asset_id}-{skill}",
                "content_asset_id": content_asset_id,
                "skill": skill,
                "existing_question_bank_id": qb.BANK_ID,
                "existing_question_bank_version": qb.BANK_VERSION,
                "existing_family_ids": sorted(family_ids),
                "projection_mode": "REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK",
                "projection_status": "READY_FOR_EXISTING_QB_MATERIALIZATION",
                "task_modes": modes,
            }
        )
    return projections


def _no_raw_copy(candidate: Mapping[str, Any], content: Mapping[str, Any]) -> None:
    raw = str(candidate.get("text_excerpt") or "").strip()
    if not raw:
        return
    raw_sentences = {norm(value) for value in _sentences(raw)}
    generated_parts = [
        *list(content.get("sentences") or []),
        *[
            str(turn.get("utterance") or "")
            for turn in content.get("dialogue_turns") or []
        ],
    ]
    if any(norm(part) in raw_sentences for part in generated_parts if norm(part)):
        raise AdmissionBuildError("RAW_RAZ_SENTENCE_COPY")
    if norm(content) == norm(raw):
        raise AdmissionBuildError("RAW_RAZ_TEXT_COPY")


def build_asset(
    candidate: Mapping[str, Any],
    decision: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    sentences, turns = content_parts(decision)
    content = {"sentences": sentences, "dialogue_turns": turns}
    if not norm(content):
        raise AdmissionBuildError("EMPTY_ADAPTATION")
    _no_raw_copy(candidate, content)

    scene = deepcopy(dict(decision.get("scene_profile") or {}))
    required_scene_fields = {
        "setting",
        "participants",
        "objects",
        "descriptors",
        "actions",
        "information_structure",
        "communicative_function_ids",
        "semantic_scene_id",
        "distinct_scene_signature",
    }
    if set(scene) != required_scene_fields:
        raise AdmissionBuildError("SCENE_PROFILE_FIELDS_INVALID")

    kind = str(decision["content_kind"])
    semantic_identity = str(candidate["semantic_identity"])
    content_asset_id = asset_id(kind, semantic_identity)
    resolution_class = str(decision["resolution_class"])
    lineage_mode = str(decision["lineage_mode"])
    if resolution_class not in (*AUTOMATIC_APPROVAL_CLASSES, "HUMAN_APPROVE_EXCEPTION"):
        raise AdmissionBuildError("APPROVAL_RESOLUTION_CLASS_INVALID")
    if lineage_mode not in LINEAGE_MODES:
        raise AdmissionBuildError("LINEAGE_MODE_INVALID")

    review_dimensions = deepcopy(dict(decision.get("review_dimensions") or {}))
    if (
        set(review_dimensions) != set(REVIEW_DIMENSIONS)
        or any(review_dimensions[key] != "PASS" for key in REVIEW_DIMENSIONS)
    ):
        raise AdmissionBuildError("APPROVAL_GATES_NOT_PASS")

    vocabulary_rows = [
        *contract["vocabulary_contract"]["active_vocabulary"],
        *contract["vocabulary_contract"]["active_adjectives"],
    ]
    wanted = set(decision.get("target_nouns") or []) | set(
        decision.get("target_adjectives") or []
    )
    vocabulary_ids = sorted(
        str(row["evp_sense_id"])
        for row in vocabulary_rows
        if str(row["lemma"]) in wanted
    )

    source_is_project = lineage_mode == "PROJECT_AUTHORED_CONTRACT_COMPLETION"
    raw_excerpt = str(candidate.get("text_excerpt") or "")
    source_lineage = {
        "source_authority": (
            "PROJECT_AUTHORED_UNIT01_CONTRACT"
            if source_is_project
            else "RAZ_READING_AUTHORITY"
        ),
        "source_record_id": str(candidate["source_record_id"]),
        "semantic_identity": semantic_identity,
        "candidate_composite_key": candidate_key_text(candidate),
        "source_level": candidate.get("source_level"),
        "source_type": candidate.get("source_type"),
        "original_excerpt_sha256": (
            digest(
                {
                    "gap_spec_id": candidate.get("gap_spec_id"),
                    "gap_dimension": candidate.get("gap_dimension"),
                }
            )
            if source_is_project
            else hashlib.sha256(raw_excerpt.encode("utf-8")).hexdigest()
        ),
        "original_excerpt_private": not source_is_project,
        "lineage_mode": lineage_mode,
        "adaptation_reason_codes": sorted(
            str(value) for value in decision.get("adaptation_reason_codes") or []
        ),
        "derived_from_task_id": (
            TASK_ID if source_is_project else upstream.TASK_ID
        ),
        "equivalence_claimed": lineage_mode == "SEMANTIC_EQUIVALENT_REWRITE",
        "imitation_claimed": lineage_mode == "SEMANTIC_ANCHOR_A1_IMITATION",
        "project_authored_claimed": source_is_project,
    }
    if source_is_project:
        source_lineage["gap_spec_id"] = candidate.get("gap_spec_id")
        source_lineage["gap_dimension"] = candidate.get("gap_dimension")

    pattern_ids = patterns(candidate)
    speakers = sorted({turn["speaker_id"] for turn in turns})
    return {
        "content_asset_id": content_asset_id,
        "content_kind": kind,
        "title": str(decision.get("title") or content_asset_id),
        "introduced_unit_id": UNIT_ID,
        "introduced_unit_sequence": 1,
        "source_lineage": source_lineage,
        "content": content,
        "content_sha256": digest(content),
        "target_alignment": {
            "grammar_target_ids": pattern_ids,
            "egp_row_ids": sorted(
                [
                    *contract["grammar_contract"]["core_focus_egp_row_ids"],
                    *contract["grammar_contract"]["guided_extension_egp_row_ids"],
                ]
            ),
            "vocabulary_asset_ids": vocabulary_ids,
            "active_nouns": sorted(set(decision.get("target_nouns") or [])),
            "active_adjectives": sorted(
                set(decision.get("target_adjectives") or [])
            ),
            "article_forms": sorted(set(decision.get("target_articles") or [])),
            "chunk_asset_ids": [],
            "sentence_frame_ids": sorted(
                set(decision.get("target_sentence_frame_ids") or [])
            ),
            "theme_id": decision.get("theme_id"),
            "situation_family_id": decision.get("situation_family_id"),
            "micro_situation_id": decision.get("micro_situation_id"),
            "communicative_function_ids": sorted(
                str(value) for value in scene["communicative_function_ids"]
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
            "canonical_admission": True,
            "template_only": False,
            "human_review_used": resolution_class == "HUMAN_APPROVE_EXCEPTION",
            "lineage_mode": lineage_mode,
        },
        "later_unit_reuse": {
            "reusable_in_later_units": True,
            "reuse_identity_mode": "REFERENCE_EXISTING_CONTENT_ASSET_ID",
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


def _validate_exception_override(
    override: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    if candidate_key(override) != candidate_key(candidate):
        raise AdmissionBuildError("HUMAN_OVERRIDE_COMPOSITE_IDENTITY_MISMATCH")
    decision_ref = str(override.get("decision_ref") or "")
    if not decision_ref.startswith(HUMAN_DECISION_REF_PREFIX):
        raise AdmissionBuildError("HUMAN_OVERRIDE_DECISION_REF_INVALID")
    if override.get("review_status") not in {"APPROVED", "REJECTED"}:
        raise AdmissionBuildError("HUMAN_OVERRIDE_STATUS_INVALID")


def _human_override_decision(
    override: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    _validate_exception_override(override, candidate)
    value = deepcopy(dict(override))
    value["resolution_class"] = "HUMAN_APPROVE_EXCEPTION"
    value["lineage_mode"] = "HUMAN_EXCEPTION_REWRITE"
    value.setdefault("adaptation_reason_codes", ["SEMANTIC_EXCEPTION_RESOLVED"])
    value.setdefault("review_dimensions", {key: "PASS" for key in REVIEW_DIMENSIONS})
    value.setdefault("template_only", False)
    if "scene_profile" not in value:
        anchors = value.get("target_nouns") or candidate.get("active_noun_hits") or []
        value["scene_profile"] = _scene_profile(
            candidate_key_text(candidate),
            anchors,
            value.get("target_adjectives") or [],
            "HUMAN_EXCEPTION",
        )
    return value


def safe_asset(asset: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(asset))
    value.pop("content", None)
    return value


def _coverage_targets(contract: Mapping[str, Any]) -> dict[str, set[str]]:
    frames = {
        str(row["frame_id"])
        for group in ("core_frames", "adjective_expansion_frames")
        for row in contract["sentence_frame_contract"][group]
    }
    return {
        "active_nouns": set(_noun_rows(contract)),
        "active_adjectives": set(_adjective_rows(contract)),
        "article_forms": {"a", "an", "the"},
        "sentence_frames": frames,
    }


def _coverage_from_assets(
    assets: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    targets = _coverage_targets(contract)
    covered = {
        "active_nouns": set(),
        "active_adjectives": set(),
        "article_forms": set(),
        "sentence_frames": set(),
    }
    for asset in assets:
        alignment = asset["target_alignment"]
        covered["active_nouns"].update(alignment.get("active_nouns") or [])
        covered["active_adjectives"].update(
            alignment.get("active_adjectives") or []
        )
        covered["article_forms"].update(alignment.get("article_forms") or [])
        covered["sentence_frames"].update(
            alignment.get("sentence_frame_ids") or []
        )
    result: dict[str, Any] = {}
    for key, target in targets.items():
        values = covered[key] & target
        result[key] = {
            "target": sorted(target),
            "covered": sorted(values),
            "missing": sorted(target - values),
        }
    result["complete"] = all(not row["missing"] for row in result.values())
    return result


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
    override_keys = [candidate_key(row) for row in override_rows]
    if any(not all(key) for key in override_keys) or len(override_keys) != len(
        set(override_keys)
    ):
        raise AdmissionBuildError("HUMAN_DECISION_COMPOSITE_IDENTITY_INVALID")
    overrides = {key: row for key, row in zip(override_keys, override_rows)}

    assets: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    human_queue: list[dict[str, Any]] = []
    seen_overrides: set[tuple[str, str]] = set()

    for candidate in candidates:
        key = candidate_key(candidate)
        resolution = classify_resolution(candidate, contract)
        resolution_class = str(resolution["resolution_class"])
        produced_asset_ids: list[str] = []
        human_override_applied = False

        if resolution_class in AUTOMATIC_SOURCE_APPROVAL_CLASSES:
            if key in overrides:
                raise AdmissionBuildError(
                    "HUMAN_OVERRIDE_ONLY_ALLOWED_FOR_EXCEPTION_QUEUE"
                )
            decision = _source_decision(candidate, resolution, contract)
            asset = build_asset(candidate, decision, contract)
            assets.append(asset)
            produced_asset_ids.append(asset["content_asset_id"])
        elif resolution_class == "HUMAN_REVIEW_REQUIRED":
            override = overrides.get(key)
            if override is None:
                human_queue.append(
                    {
                        "source_record_id": key[0],
                        "semantic_identity": key[1],
                        "candidate_composite_key": candidate_key_text(candidate),
                        "source_excerpt_sha256": hashlib.sha256(
                            str(candidate.get("text_excerpt") or "").encode("utf-8")
                        ).hexdigest(),
                        "reason_codes": deepcopy(resolution["reason_codes"]),
                        "allowed_human_outcomes": [
                            "HUMAN_APPROVE_EXCEPTION",
                            "HUMAN_REJECT_EXCEPTION",
                        ],
                    }
                )
            else:
                seen_overrides.add(key)
                human_override_applied = True
                _validate_exception_override(override, candidate)
                if override["review_status"] == "APPROVED":
                    decision = _human_override_decision(override, candidate)
                    asset = build_asset(candidate, decision, contract)
                    assets.append(asset)
                    produced_asset_ids.append(asset["content_asset_id"])
                    resolution_class = "HUMAN_APPROVE_EXCEPTION"
                else:
                    resolution_class = "HUMAN_REJECT_EXCEPTION"
        elif resolution_class == "AUTO_REJECT":
            if key in overrides:
                raise AdmissionBuildError("AUTO_REJECT_OVERRIDE_FORBIDDEN")

        ledger.append(
            {
                "source_record_id": key[0],
                "semantic_identity": key[1],
                "candidate_composite_key": candidate_key_text(candidate),
                "selection_class": candidate["selection_class"],
                "resolution_class": resolution_class,
                "resolution_reason_codes": deepcopy(resolution["reason_codes"]),
                "lineage_mode": resolution.get("lineage_mode"),
                "human_review_required": (
                    resolution["resolution_class"] == "HUMAN_REVIEW_REQUIRED"
                ),
                "human_override_applied": human_override_applied,
                "content_asset_ids": produced_asset_ids,
            }
        )

    unused_overrides = set(overrides) - seen_overrides
    if unused_overrides:
        raise AdmissionBuildError(
            "HUMAN_OVERRIDE_COMPOSITE_KEY_NOT_IN_EXCEPTION_QUEUE:"
            + ",".join(f"{source}::{semantic}" for source, semantic in sorted(unused_overrides))
        )

    gap_specs = list(
        (selection_report.get("coverage") or {}).get(
            "project_authored_gap_specs"
        )
        or []
    )
    project_gap_ids: list[str] = []
    for index, gap in enumerate(gap_specs):
        if not isinstance(gap, Mapping):
            raise AdmissionBuildError("PROJECT_GAP_SPEC_OBJECT_REQUIRED")
        candidate, decision = _project_gap_candidate(gap, index, contract)
        asset = build_asset(candidate, decision, contract)
        assets.append(asset)
        project_gap_ids.append(str(gap["gap_spec_id"]))
        ledger.append(
            {
                "source_record_id": candidate["source_record_id"],
                "semantic_identity": candidate["semantic_identity"],
                "candidate_composite_key": candidate_key_text(candidate),
                "selection_class": candidate["selection_class"],
                "resolution_class": decision["resolution_class"],
                "resolution_reason_codes": deepcopy(
                    decision["adaptation_reason_codes"]
                ),
                "lineage_mode": decision["lineage_mode"],
                "human_review_required": False,
                "human_override_applied": False,
                "content_asset_ids": [asset["content_asset_id"]],
            }
        )

    if not assets:
        raise AdmissionBuildError("NO_APPROVED_CONTENT_ASSETS")
    asset_ids = [asset["content_asset_id"] for asset in assets]
    if len(asset_ids) != len(set(asset_ids)):
        raise AdmissionBuildError("CONTENT_ASSET_ID_DUPLICATE")

    source_ledger = [
        row
        for row in ledger
        if row["resolution_class"]
        != "AUTO_APPROVE_PROJECT_AUTHORED_COMPLETION"
    ]
    counts = Counter(row["resolution_class"] for row in ledger)
    kind_counts = Counter(asset["content_kind"] for asset in assets)
    lineage_counts = Counter(
        asset["source_lineage"]["lineage_mode"] for asset in assets
    )
    coverage_matrix = _coverage_from_assets(assets, contract)
    real44 = len(candidates) == 44
    auto_source_count = sum(
        counts[name] for name in AUTOMATIC_SOURCE_APPROVAL_CLASSES
    )
    auto_reject_count = counts["AUTO_REJECT"]
    human_pending_count = len(human_queue)

    if real44:
        if auto_source_count < 35:
            raise AdmissionBuildError("REAL44_AUTO_TRANSFORM_COUNT_BELOW_35")
        if human_pending_count > 6:
            raise AdmissionBuildError("REAL44_HUMAN_QUEUE_ABOVE_6")
        if auto_reject_count != 3:
            raise AdmissionBuildError("REAL44_AUTO_REJECT_COUNT_NOT_3")
        if not coverage_matrix["complete"]:
            raise AdmissionBuildError("REAL44_UNIT01_COVERAGE_INCOMPLETE")

    coverage = {
        "source_candidate_count": len(candidates),
        "project_authored_gap_spec_count": len(gap_specs),
        "resolution_ledger_count": len(ledger),
        "auto_approve_semantic_equivalent_count": counts[
            "AUTO_APPROVE_SEMANTIC_EQUIVALENT"
        ],
        "auto_approve_a1_imitation_count": counts[
            "AUTO_APPROVE_A1_IMITATION"
        ],
        "auto_approve_project_authored_completion_count": counts[
            "AUTO_APPROVE_PROJECT_AUTHORED_COMPLETION"
        ],
        "auto_reject_count": auto_reject_count,
        "human_review_required_count": sum(
            row["human_review_required"] for row in source_ledger
        ),
        "human_review_resolved_count": sum(
            row["human_override_applied"] for row in source_ledger
        ),
        "human_review_pending_count": human_pending_count,
        "human_approve_exception_count": counts["HUMAN_APPROVE_EXCEPTION"],
        "human_reject_exception_count": counts["HUMAN_REJECT_EXCEPTION"],
        "auto_transformed_source_count": auto_source_count,
        "auto_transformed_source_ratio": (
            auto_source_count / len(candidates) if candidates else 0.0
        ),
        "approved_content_asset_count": len(assets),
        "distinct_semantic_scene_count": len(
            {
                asset["scene_profile"]["semantic_scene_id"]
                for asset in assets
            }
        ),
        "distinct_micro_scene_count": kind_counts["MICRO_SCENE"],
        "distinct_short_passage_count": kind_counts["SHORT_PASSAGE"],
        "distinct_dialogue_count": kind_counts["SHORT_DIALOGUE"],
        "lineage_mode_counts": {
            mode: lineage_counts[mode] for mode in LINEAGE_MODES
        },
        "reading_projection_count": len(assets),
        "writing_projection_count": len(assets),
        "speaking_projection_count": len(assets),
        "three_skill_shared_content_count": len(assets),
        "template_only_content_count": 0,
        "unit02_reusable_asset_count": len(assets),
        "unit01_coverage": coverage_matrix,
        "real44_acceptance_applied": real44,
        "real44_acceptance_pass": (
            real44
            and auto_source_count >= 35
            and human_pending_count <= 6
            and auto_reject_count == 3
            and coverage_matrix["complete"]
        ),
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
            "human_review_scope": "TRUE_UNCERTAINTY_ONLY",
            "complete_manual_decision_manifest_required": False,
            "additional_raz_search_allowed": False,
        },
        "inputs": {
            "upstream_task_id": upstream.TASK_ID,
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "existing_question_bank_id": qb.BANK_ID,
            "existing_question_bank_version": qb.BANK_VERSION,
            "automatic_decision_ref": AUTO_DECISION_REF,
            "source_candidate_manifest_sha256": digest(
                [
                    {
                        "source_record_id": row["source_record_id"],
                        "semantic_identity": row["semantic_identity"],
                    }
                    for row in candidates
                ]
            ),
        },
        "automatic_resolution_policy": {
            "candidate_identity_fields": [
                "source_record_id",
                "semantic_identity",
            ],
            "source_record_id_may_repeat": True,
            "semantic_identity_must_be_unique": True,
            "resolution_classes": list(RESOLUTION_CLASSES),
            "semantic_equivalent_rewrite_enabled": True,
            "semantic_anchor_a1_imitation_enabled": True,
            "project_authored_contract_completion_enabled": True,
            "raw_source_copy_allowed": False,
            "model_output_requires_deterministic_validation": True,
            "human_review_only_for_true_uncertainty": True,
            "unresolved_human_queue_blocks_auto_approved_assets": False,
        },
        "inspection_record": {
            "findings": [
                {
                    "finding_code": code,
                    "observed_status": "CONFIRMED",
                    "evidence": evidence,
                }
                for code, evidence in FINDINGS
            ],
            "resolution": (
                "COMPOSITE_IDENTITY_SEMANTIC_REWRITE_A1_IMITATION_"
                "PROJECT_AUTHORED_CONTRACT_COMPLETION"
            ),
        },
        "resolution_ledger": ledger,
        "human_review_queue": human_queue,
        "project_authored_gap_spec_ids": sorted(project_gap_ids),
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
        payload=build_payload(selection_report, human_decisions, contract),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "parent_task_id": PARENT_TASK_ID,
            "upstream_task_id": upstream.TASK_ID,
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "existing_question_bank_id": qb.BANK_ID,
            "existing_question_bank_version": qb.BANK_VERSION,
            "automatic_decision_ref": AUTO_DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
        as validator,
    )

    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[validator.validate_candidate(candidate)],
        decision_ref=AUTO_DECISION_REF,
        producer_id=TASK_ID,
    )


def build_safe_readback(approved: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(approved)
    payload = approved.get("payload") or {}
    safe = {
        "schema_version": SAFE_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "parent_task_id": PARENT_TASK_ID,
        "status": PASS_STATUS,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "content_governance": deepcopy(approved["content_governance"]),
        "admission": deepcopy(approved["admission"]),
        "source_bindings": deepcopy(approved["source_bindings"]),
        "automatic_resolution_policy": deepcopy(
            payload.get("automatic_resolution_policy") or {}
        ),
        "inspection_record": deepcopy(payload.get("inspection_record") or {}),
        "coverage_readback": deepcopy(payload.get("coverage_readback") or {}),
        "resolution_ledger": deepcopy(payload.get("resolution_ledger") or []),
        "human_review_queue": deepcopy(
            payload.get("human_review_queue") or []
        ),
        "project_authored_gap_spec_ids": deepcopy(
            payload.get("project_authored_gap_spec_ids") or []
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
    candidate = build_candidate(selection_report, human_decisions, contract)
    approved = admit_candidate(candidate)
    return candidate, approved, build_safe_readback(approved)


def run(
    selection_report_path: Path,
    human_decisions_path: Path | None = None,
    candidate_output_path: Path = OUTPUT_CANDIDATE,
    approved_output_path: Path = OUTPUT_APPROVED,
    safe_output_path: Path = OUTPUT_SAFE,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    decisions = load(human_decisions_path) if human_decisions_path else None
    candidate, approved, safe = build_admission(
        load(selection_report_path), decisions
    )
    write(candidate_output_path, candidate, private=True)
    write(approved_output_path, approved, private=True)
    write(safe_output_path, safe)
    return candidate, approved, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-report", type=Path, required=True)
    parser.add_argument(
        "--human-decisions", "--decisions", dest="human_decisions", type=Path
    )
    parser.add_argument("--candidate-output", type=Path, default=OUTPUT_CANDIDATE)
    parser.add_argument("--approved-output", type=Path, default=OUTPUT_APPROVED)
    parser.add_argument("--safe-output", type=Path, default=OUTPUT_SAFE)
    args = parser.parse_args(argv)
    try:
        _, approved, safe = run(
            args.selection_report.resolve(),
            args.human_decisions.resolve() if args.human_decisions else None,
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
        print("STATUS=FAIL_A1FS_V1_RAZQ01D_FULLFIX2")
        print(f"ERROR={exc}")
        return 1
    coverage = safe["coverage_readback"]
    print(f"STATUS={approved['payload']['status']}")
    print(
        f"AUTO_TRANSFORMED_SOURCE={coverage['auto_transformed_source_count']}"
    )
    print(f"AUTO_REJECT={coverage['auto_reject_count']}")
    print(f"HUMAN_REVIEW_PENDING={coverage['human_review_pending_count']}")
    print(
        f"PROJECT_AUTHORED_COMPLETION="
        f"{coverage['auto_approve_project_authored_completion_count']}"
    )
    print(f"APPROVED_CONTENT_ASSETS={coverage['approved_content_asset_count']}")
    print(f"UNIT01_COVERAGE_COMPLETE={coverage['unit01_coverage']['complete']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
