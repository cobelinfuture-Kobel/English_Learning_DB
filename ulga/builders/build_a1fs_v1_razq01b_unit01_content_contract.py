#!/usr/bin/env python3
"""Build the executable Unit01 vocabulary/chunk/frame/material contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Produces a machine-readable calibration input only; no learner-facing content, scoring, state, audio, A2, or canonical question bank is written."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01B_Unit01ActiveVocabularyChunksSentenceFramesAndMaterialContract"
SCHEMA_VERSION = "a1fs.v1.razq01b.unit01_content_contract.v1"
STATUS = "PROPOSED_UNIT01_CONTENT_CONTRACT_REQUIRES_OPERATOR_REVIEW"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01B_Unit01ContentContractOperatorReviewAndContractAwareReplay"
DEFAULT_OUTPUT = Path("ulga/graph/a1fs_v1_razq01b_unit01_content_contract.json")
WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
ARTICLE_RE = re.compile(r"\b(?:a|an|the)\s+[a-z][a-z'’-]*\b", re.I)

ACTIVE_VOCABULARY = (
    ("apple", "vocabulary:apple:v_418", "蘋果", "an apple", "the apple", "FOOD"),
    ("bag", "vocabulary:bag:v_639", "袋子；書包", "a bag", "the bag", "CLASSROOM_OBJECT"),
    ("bed", "vocabulary:bed:v_470", "床", "a bed", "the bed", "HOME_OBJECT"),
    ("book", "vocabulary:book:v_233", "書", "a book", "the book", "CLASSROOM_OBJECT"),
    ("box", "vocabulary:box:v_646", "盒子", "a box", "the box", "CONTAINER"),
    ("cat", "vocabulary:cat:v_221", "貓", "a cat", "the cat", "ANIMAL"),
    ("classroom", "vocabulary:classroom:v_989", "教室", "a classroom", "the classroom", "PLACE"),
    ("desk", "vocabulary:desk:v_2046", "書桌；課桌", "a desk", "the desk", "CLASSROOM_OBJECT"),
    ("dog", "vocabulary:dog:v_1866", "狗", "a dog", "the dog", "ANIMAL"),
    ("door", "vocabulary:door:v_2048", "門", "a door", "the door", "PLACE_OBJECT"),
    ("egg", "vocabulary:egg:v_2038", "蛋", "an egg", "the egg", "FOOD"),
    ("park", "vocabulary:park:v_6791", "公園", "a park", "the park", "PLACE"),
    ("room", "vocabulary:room:v_6776", "房間", "a room", "the room", "PLACE"),
    ("shop", "vocabulary:shop:v_8823", "商店", "a shop", "the shop", "PLACE"),
    ("tree", "vocabulary:tree:v_9885", "樹", "a tree", "the tree", "NATURE"),
    ("window", "vocabulary:window:v_9874", "窗戶", "a window", "the window", "PLACE_OBJECT"),
)

RECEPTIVE_VOCABULARY = (
    ("animal", "vocabulary:animal:v_206", "動物", "A1", "CONTEXT_SUPPORT"),
    ("birthday", "vocabulary:birthday:v_626", "生日", "A1", "CONTEXT_SUPPORT"),
    ("cake", "vocabulary:cake:v_423", "蛋糕", "A1", "CONTEXT_SUPPORT"),
    ("food", "vocabulary:food:v_3679", "食物", "A1", "CONTEXT_SUPPORT"),
    ("friend", "vocabulary:friend:v_3871", "朋友", "A1", "CONTEXT_SUPPORT"),
    ("home", "vocabulary:home:v_3704", "家", "A1", "CONTEXT_SUPPORT"),
    ("picnic", "vocabulary:picnic:v_6746", "野餐", "A1", "CONTEXT_SUPPORT"),
    ("school", "vocabulary:school:v_8983", "學校", "A1", "CONTEXT_SUPPORT"),
    ("toy", "vocabulary:toy:v_9994", "玩具", "A2", "PICTURE_SUPPORTED_RECEPTIVE_BRIDGE"),
)

CANONICAL_CHUNKS = (
    ("EVP_CHUNK_000003", "CD player", "A1", "noun_phrase"),
    ("EVP_CHUNK_000054", "ice cream", "A1", "noun_phrase"),
    ("EVP_CHUNK_000075", "living room", "A1", "noun_phrase"),
)

INSTRUCTIONAL_PHRASES = (
    "a bag", "a book", "an apple", "a cat", "the bag", "the book",
    "the door", "in the bag", "near the door", "on the desk",
    "at the park", "in the classroom",
)

CORE_SENTENCE_FRAMES = (
    ("U01-F01", "This is {ARTICLE} {THING}.", "IDENTIFY_ONE_ITEM", "CONTROLLED"),
    ("U01-F02", "I have {ARTICLE} {THING}.", "NAME_PERSONAL_OBJECT", "CONTROLLED"),
    ("U01-F03", "{ARTICLE_CAP} {THING} is in the {PLACE}.", "DESCRIBE_CONTENTS", "GUIDED"),
    ("U01-F04", "{ARTICLE_CAP} {THING} is near the {PLACE}.", "DESCRIBE_LOCATION", "GUIDED"),
    ("U01-F05", "The {THING} is {PLACE_PHRASE}.", "REFER_TO_KNOWN_ITEM", "GUIDED"),
    ("U01-F06", "I can see {ARTICLE} {THING}.", "IDENTIFY_VISIBLE_ITEM", "GUIDED"),
)

SCAFFOLD_FRAMES = (
    ("U01-SF01", "There is {ARTICLE} {THING} in the {PLACE}.", "GRAMMAR_THERE_IS", "SCAFFOLD_ONLY_NOT_UNIT01_TARGET"),
    ("U01-SF02", "{PERSON} has {ARTICLE} {THING} and {ARTICLE} {THING}.", "GRAMMAR_COORDINATION_A1", "SCAFFOLD_ONLY_NOT_UNIT01_TARGET"),
)

CORE_EGP_ROWS = (
    "1741163708789x105964971324936210",
    "1741163708789x344483096716751800",
)
GUIDED_EGP_ROWS = (
    "1741163708789x174288205596050180",
)
DEFERRED_EGP_ROWS = (
    "1741163708789x819248395543273500",
    "1741163708792x578027203654075000",
    "1741163708793x394528376329640770",
    "1741163708998x446294161060833700",
    "1741163708998x669595367530949600",
    "1741163709012x117638123076284200",
    "1741163709012x230041547102954000",
)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def build_contract() -> dict[str, Any]:
    active = [
        {
            "lemma": lemma,
            "evp_sense_id": sense,
            "cefr_level": "A1",
            "part_of_speech": "noun",
            "zh_tw_gloss": gloss,
            "memory_form_indefinite": indefinite,
            "memory_form_definite": definite,
            "semantic_group": group,
            "production_required": True,
            "spelling_required": True,
            "imageable": True,
        }
        for lemma, sense, gloss, indefinite, definite, group in ACTIVE_VOCABULARY
    ]
    receptive = [
        {
            "lemma": lemma,
            "evp_sense_id": sense,
            "zh_tw_gloss": gloss,
            "cefr_level": level,
            "role": role,
            "production_required": False,
            "spelling_required": False,
        }
        for lemma, sense, gloss, level, role in RECEPTIVE_VOCABULARY
    ]
    frame_scaffolds = {
        "U01-F01": ["GRAMMAR_DEMONSTRATIVES_CONTRAST", "GRAMMAR_BE_VERB_BASIC"],
        "U01-F02": ["GRAMMAR_SUBJECT_PRONOUNS", "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
        "U01-F03": ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_BASIC_PREPOSITIONS_PLACE"],
        "U01-F04": ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_BASIC_PREPOSITIONS_PLACE"],
        "U01-F05": ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_BASIC_PREPOSITIONS_PLACE"],
        "U01-F06": ["GRAMMAR_SUBJECT_PRONOUNS", "GRAMMAR_CAN_STATEMENT"],
    }
    core_frames = [
        {
            "frame_id": fid,
            "template": template,
            "communicative_goal": goal,
            "support_level": support,
            "scaffold_grammar_refs": frame_scaffolds[fid],
            "assessment_scope": "ARTICLE_SELECTION_AND_NOUN_PHRASE_ONLY",
        }
        for fid, template, goal, support in CORE_SENTENCE_FRAMES
    ]
    scaffold_frames = [
        {"frame_id": fid, "template": template, "external_grammar_ref": grammar, "role": role}
        for fid, template, grammar, role in SCAFFOLD_FRAMES
    ]
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": STATUS,
        "unit_id": UNIT_ID,
        "level_scope": ["A1"],
        "operator_review": {
            "required": True,
            "decision_status": "PENDING",
            "review_dimensions": [
                "ACTIVE_VOCABULARY",
                "RECEPTIVE_VOCABULARY",
                "CANONICAL_CHUNKS",
                "INSTRUCTIONAL_PHRASES",
                "SENTENCE_FRAMES",
                "MATERIAL_SELECTION_POLICY",
            ],
        },
        "grammar_contract": {
            "core_focus_egp_row_ids": list(CORE_EGP_ROWS),
            "guided_extension_egp_row_ids": list(GUIDED_EGP_ROWS),
            "deferred_not_assessed_egp_row_ids": list(DEFERRED_EGP_ROWS),
            "core_functions": [
                "a/an/the before nouns",
                "a/an before adjective plus singular countable noun",
                "indefinite introduction versus definite reference",
            ],
            "allowed_incidental_scaffolds": [
                "formulaic This is frame; demonstrative and be grammar are not assessed",
                "formulaic I have frame; pronoun and present-simple grammar are not assessed",
                "formulaic I can see frame; pronoun and can grammar are not assessed",
                "basic be forms in supplied location frames",
                "in/on/near place phrases",
                "there is in scaffolded model only",
                "and in scaffolded model only",
            ],
            "blocked_direct_use_features": [
                "past_simple",
                "continuous",
                "present_perfect",
                "passive",
                "future",
                "relative_clause",
                "conditional",
                "complex_comparative_or_superlative",
            ],
            "claim_boundary": "UNIT01_CONTENT_PACKAGE_V1_DOES_NOT_CLAIM_ACTIVE_TEACHING_OF_ALL_LINKED_EGP_ROWS",
        },
        "vocabulary_contract": {
            "active_memorization_count": len(active),
            "active_vocabulary": active,
            "memory_sets": [
                {"set_id": "U01-VSET-01", "label_zh_tw": "教室用品", "lemmas": ["bag", "book", "classroom", "desk"]},
                {"set_id": "U01-VSET-02", "label_zh_tw": "家中物品", "lemmas": ["bed", "box", "door", "room"]},
                {"set_id": "U01-VSET-03", "label_zh_tw": "動物與戶外", "lemmas": ["cat", "dog", "park", "tree"]},
                {"set_id": "U01-VSET-04", "label_zh_tw": "食物與地點", "lemmas": ["apple", "egg", "shop", "window"]},
            ],
            "memorization_evidence_required": {
                "recognition": True,
                "article_phrase_recall": True,
                "controlled_sentence_production": True,
                "minimum_distinct_context_exposures": 4,
                "minimum_controlled_productions": 2,
            },
            "receptive_vocabulary": receptive,
            "a2_bridge_policy": "A2 items may appear only as picture-supported receptive bridges and may not be scored or required for production.",
        },
        "chunk_contract": {
            "canonical_chunks": [
                {"chunk_id": cid, "surface_form": form, "cefr_level": level, "usage_class": usage}
                for cid, form, level, usage in CANONICAL_CHUNKS
            ],
            "instructional_phrases": [
                {"surface_form": phrase, "authority_role": "PROJECT_AUTHORED_INSTRUCTIONAL_PHRASE", "canonical_chunk_claimed": False}
                for phrase in INSTRUCTIONAL_PHRASES
            ],
        },
        "sentence_frame_contract": {
            "core_frames": core_frames,
            "scaffold_only_frames": scaffold_frames,
            "frame_slot_rules": {
                "ARTICLE": ["a", "an", "the"],
                "THING": "active_vocabulary noun",
                "PLACE": "active or receptive place noun",
                "PLACE_PHRASE": ["in the {PLACE}", "on the {THING}", "near the {PLACE}"],
            },
        },
        "material_contract": {
            "context_families": [
                {"context_id": "U01-C1-CLASSROOM-BAG", "active_lemmas": ["classroom", "bag", "book", "apple", "desk", "door"], "receptive_lemmas": ["school"]},
                {"context_id": "U01-C2-HOME-ROOM", "active_lemmas": ["room", "bed", "box", "door", "window"], "receptive_lemmas": ["home"]},
                {"context_id": "U01-C3-SHOP-BOX", "active_lemmas": ["shop", "box", "book", "bag", "window"], "receptive_lemmas": []},
                {"context_id": "U01-C4-PARK-PICNIC", "active_lemmas": ["park", "tree", "dog", "cat", "apple", "egg"], "receptive_lemmas": ["picnic", "food", "friend"]},
            ],
            "source_policy": {
                "direct_use_raz_levels": list("ABCDEFGHI"),
                "rewrite_only_raz_levels": list("JKLMNOPQRSTUVW"),
                "raw_raz_text_learner_facing_copy_allowed": False,
                "raz_role": "SOURCE_GROUNDING_CONTEXT_AND_LANGUAGE_EVIDENCE_ONLY",
            },
            "window_gate": {
                "sentence_count_min": 1,
                "sentence_count_max": 3,
                "word_count_min": 3,
                "word_count_max": 45,
                "target_article_hit_min": 1,
                "active_vocabulary_hit_min": 1,
                "known_content_word_ratio_min": 0.85,
                "unknown_content_word_unique_max": 2,
                "blocked_grammar_feature_max": 0,
                "semantic_group_lineage_required": True,
                "theme_only_match_is_pass": False,
            },
            "eligible_material_roles": [
                "VOCABULARY_MEMORY_CARD",
                "PICTURE_PROMPT",
                "MICRO_SCENE",
                "SHORT_READING_SOURCE",
                "LISTENING_SCRIPT_CANDIDATE_NO_AUDIO",
                "SPEAKING_PROMPT_CANDIDATE",
                "WRITING_FRAME_CANDIDATE",
            ],
        },
        "boundaries": {
            "unit02_to_unit24_modified": False,
            "canonical_question_bank_written": False,
            "learner_facing_content_written": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "parallel_curriculum_created": False,
        },
        "consumers": {
            "filter_consumer": "A1FS-V1-RAZQ01A_Unit01Unit02AuthorityAwareWindowedFilterFullFixAndReplay",
            "consumer_mode": "CALIBRATION_INPUT_PENDING_OPERATOR_APPROVAL",
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    return {**core, "contract_sha256": digest(core)}


def verify_contract_digest(contract: Mapping[str, Any]) -> None:
    expected = str(contract.get("contract_sha256") or "")
    core = {key: deepcopy(value) for key, value in contract.items() if key != "contract_sha256"}
    if expected != digest(core):
        raise ValueError("contract_digest_invalid")


def active_lemmas(contract: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(
        str(row.get("lemma") or "").lower()
        for row in contract.get("vocabulary_contract", {}).get("active_vocabulary", [])
        if isinstance(row, Mapping) and str(row.get("lemma") or "").strip()
    )


def receptive_lemmas(contract: Mapping[str, Any], *, include_a2_bridge: bool = False) -> frozenset[str]:
    rows = contract.get("vocabulary_contract", {}).get("receptive_vocabulary", [])
    return frozenset(
        str(row.get("lemma") or "").lower()
        for row in rows
        if isinstance(row, Mapping)
        and str(row.get("lemma") or "").strip()
        and (include_a2_bridge or row.get("cefr_level") == "A1")
    )


def evaluate_material_window(
    text: str,
    *,
    contract: Mapping[str, Any],
    known_lexicon: Sequence[str] = (),
    blocked_features: Sequence[str] = (),
    source_level: str = "A",
    lineage_complete: bool = True,
) -> dict[str, Any]:
    """Apply the executable Unit01 material gate to one candidate window."""
    verify_contract_digest(contract)
    gate = contract["material_contract"]["window_gate"]
    words = [token.lower().replace("’", "'") for token in WORD_RE.findall(text)]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    active = active_lemmas(contract)
    receptive = receptive_lemmas(contract)
    known = set(str(item).lower() for item in known_lexicon) | active | receptive
    function_words = set("a an the and or but i you he she it we they this that these those am is are have has can in on at near of to from with there here my your his her our their one two three four five six seven eight nine ten".split())
    content = [word for word in words if word not in function_words]
    unknown = sorted({word for word in content if word not in known})
    known_count = len(content) - sum(1 for word in content if word in unknown)
    known_ratio = known_count / len(content) if content else 1.0
    active_hits = sorted(active & set(words))
    article_hits = len(ARTICLE_RE.findall(text))
    reasons: list[str] = []
    if len(sentences) < int(gate["sentence_count_min"]) or len(sentences) > int(gate["sentence_count_max"]):
        reasons.append("SENTENCE_COUNT_OUT_OF_RANGE")
    if len(words) < int(gate["word_count_min"]) or len(words) > int(gate["word_count_max"]):
        reasons.append("WORD_COUNT_OUT_OF_RANGE")
    if article_hits < int(gate["target_article_hit_min"]):
        reasons.append("TARGET_ARTICLE_HIT_MISSING")
    if len(active_hits) < int(gate["active_vocabulary_hit_min"]):
        reasons.append("ACTIVE_VOCABULARY_HIT_MISSING")
    if known_ratio < float(gate["known_content_word_ratio_min"]) or len(unknown) > int(gate["unknown_content_word_unique_max"]):
        reasons.append("VOCABULARY_GATE_FAILED")
    if len(blocked_features) > int(gate["blocked_grammar_feature_max"]):
        reasons.append("BLOCKED_GRAMMAR_PRESENT")
    if bool(gate["semantic_group_lineage_required"]) and not lineage_complete:
        reasons.append("LINEAGE_GROUP_INCOMPLETE")
    direct = source_level.upper() in set(contract["material_contract"]["source_policy"]["direct_use_raz_levels"])
    rewrite = source_level.upper() in set(contract["material_contract"]["source_policy"]["rewrite_only_raz_levels"])
    if not direct and not rewrite:
        reasons.append("SOURCE_LEVEL_INVALID")
    classification = "PASS" if direct and not reasons else "BORDERLINE" if rewrite and not set(reasons) - {"SOURCE_LEVEL_INVALID"} else "REJECT"
    if rewrite:
        classification = "BORDERLINE"
        if "REWRITE_ONLY_SOURCE_LEVEL" not in reasons:
            reasons.append("REWRITE_ONLY_SOURCE_LEVEL")
    return {
        "classification": classification,
        "reasons": reasons or ["UNIT01_CONTENT_CONTRACT_MATCH"],
        "word_count": len(words),
        "sentence_count": len(sentences),
        "article_hit_count": article_hits,
        "active_vocabulary_hits": active_hits,
        "known_content_word_ratio": round(known_ratio, 4),
        "unknown_content_words": unknown,
        "blocked_grammar_features": list(blocked_features),
        "lineage_complete": lineage_complete,
        "source_level": source_level.upper(),
        "contract_sha256": contract["contract_sha256"],
    }


def write_contract(path: Path) -> dict[str, Any]:
    contract = build_contract()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return contract


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    contract = write_contract(args.output)
    print(f"STATUS={contract['status']}")
    print(f"UNIT={contract['unit_id']}")
    print(f"ACTIVE_VOCABULARY={contract['vocabulary_contract']['active_memorization_count']}")
    print(f"OUTPUT={args.output}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
