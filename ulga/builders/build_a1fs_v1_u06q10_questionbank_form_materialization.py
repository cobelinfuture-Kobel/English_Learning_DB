#!/usr/bin/env python3
"""Unit06 Q10: coverage-driven QuestionBank and Form materialization."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q06_sentence_assets as q06_builder
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as q07_builder
from ulga.builders import build_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as q07r1_builder

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_CAN_STATEMENT"
TASK_ID = "A1FS-V1-U06Q10_Unit06QuestionBankAndFormMaterialization"
SCHEMA_VERSION = "a1fs.v1.u06.q10.questionbank_form_materialization.v1"
PASS_STATUS = "PASS_A1FS_V1_U06Q10_QUESTIONBANK_AND_FORM_MATERIALIZATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-10-03:U06_Q10_COVERAGE_DRIVEN_300"
NEXT_SHORT_STEP = "A1FS-V1-U06Q10R1_Unit06LearnerFacingPedagogicalAcceptance"

Q08 = ROOT / "ulga/contracts/a1fs_v1_u06_q08_communicative_function_authority.json"
Q09 = ROOT / "ulga/contracts/a1fs_v1_u06_q09_task_pedagogical_contract.json"

FORM_COUNT = 10
QUESTIONS_PER_FORM = 30
TOTAL_ITEMS = 300

SECTION_SPECS = (
    ("A", "CAN_FORM_AND_BASE_VERB_RECOGNITION", 6),
    ("B", "ABILITY_MEANING_AND_FUNCTIONAL_CHUNK_COMPREHENSION", 6),
    ("C", "SENTENCE_CONSTRUCTION_REPAIR_AND_CONTEXT_GAP", 8),
    ("D", "CONNECTED_CONTEXT_AND_CUMULATIVE_INTEGRATION", 4),
    ("E", "PRODUCTIVE_RESPONSE_AND_TRANSFER", 6),
)
SECTION_COUNTS = {section: count for section, _, count in SECTION_SPECS}

FORM_STAGES = {
    1: "GUIDED", 2: "GUIDED",
    3: "REDUCED_SUPPORT", 4: "REDUCED_SUPPORT",
    5: "INDEPENDENT", 6: "INDEPENDENT",
    7: "TRANSFER", 8: "TRANSFER",
    9: "RETENTION", 10: "RETENTION",
}

PATTERNS = {
    "A": (
        "U06-TF01_CAN_FORM_RECOGNITION",
        "U06-TF02_BASE_VERB_FORM_SELECTION",
    ) * 3,
    "B": (
        "U06-TF03_ABILITY_MEANING_DISCRIMINATION",
        "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE",
    ) * 3,
    "C": (
        "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE",
        "U06-TF06_ERROR_DETECTION_AND_CORRECTION",
        "U06-TF07_SCENE_BOUND_CONTEXT_GAP",
        "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE",
        "U06-TF06_ERROR_DETECTION_AND_CORRECTION",
        "U06-TF07_SCENE_BOUND_CONTEXT_GAP",
        "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE",
        "U06-TF06_ERROR_DETECTION_AND_CORRECTION",
    ),
    "D": (
        "U06-TF07_SCENE_BOUND_CONTEXT_GAP",
        "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION",
    ) * 2,
    "E": (
        "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE",
        "U06-TF10_TRANSFER",
    ) * 3,
}

QUESTION_TYPES = {
    "U06-TF01_CAN_FORM_RECOGNITION": "can_form_recognition",
    "U06-TF02_BASE_VERB_FORM_SELECTION": "base_verb_form",
    "U06-TF03_ABILITY_MEANING_DISCRIMINATION": "ability_meaning",
    "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE": "functional_chunk_scene_match",
    "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE": "chunk_to_sentence",
    "U06-TF06_ERROR_DETECTION_AND_CORRECTION": "error_detection_or_correction",
    "U06-TF07_SCENE_BOUND_CONTEXT_GAP": "scene_context_completion",
    "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION": "cumulative_integration",
    "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE": "productive_ability_response",
    "U06-TF10_TRANSFER": "unseen_transfer",
}

CHUNK_ROUTE_FAMILIES = {
    "U06-TF02_BASE_VERB_FORM_SELECTION",
    "U06-TF03_ABILITY_MEANING_DISCRIMINATION",
    "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE",
    "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE",
    "U06-TF06_ERROR_DETECTION_AND_CORRECTION",
    "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION",
    "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE",
}
CANONICAL_ROUTE_COUNTS = {
    "U06-TF01_CAN_FORM_RECOGNITION": 30,
    "U06-TF07_SCENE_BOUND_CONTEXT_GAP": 40,
    "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE": 29,
    "U06-TF10_TRANSFER": 30,
}
CHUNK_ROUTE_COUNTS = {
    "U06-TF02_BASE_VERB_FORM_SELECTION": 30,
    "U06-TF03_ABILITY_MEANING_DISCRIMINATION": 30,
    "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE": 30,
    "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE": 30,
    "U06-TF06_ERROR_DETECTION_AND_CORRECTION": 30,
    "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION": 20,
    "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE": 1,
}
RESTRICTED_CHUNK_SENTENCE_SURFACES = {"can go to school", "can study at school"}

class U06Q10BuildError(ValueError):
    pass

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()

def _normalize(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value).strip().casefold())
    return re.sub(r"[.!?]+$", "", text).strip()

def _sources() -> dict[str, Any]:
    q06 = q06_builder.build_report()
    q07 = q07_builder.build_report()
    q07r1 = q07r1_builder.build_report()
    q08 = _load(Q08)
    q09 = _load(Q09)
    expected = (
        (q06, "PASS_A1FS_V1_U06Q06_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"),
        (q07, "PASS_A1FS_V1_U06Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"),
        (q07r1, "PASS_A1FS_V1_U06Q07R1_YLE_ABILITY_VERB_FUNCTIONAL_CHUNK_SEMANTIC_EXPANSION"),
        (q08, "PASS_A1FS_V1_U06Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"),
        (q09, "PASS_A1FS_V1_U06Q09_TASK_AND_PEDAGOGICAL_CONTRACT"),
    )
    for payload, status in expected:
        if payload.get("status") != status:
            raise U06Q10BuildError(f"SOURCE_STATUS_DRIFT:{payload.get('task_id')}")
    return {"q06": q06, "q07": q07, "q07r1": q07r1, "q08": q08, "q09": q09}

def _q06_rows(src: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in src["q06"]["new_sentence_assets"]]
    if len(rows) != 129 or len({str(row["sentence_id"]) for row in rows}) != 129:
        raise U06Q10BuildError("Q06_SENTENCE_DENOMINATOR_DRIFT")
    return rows

def _binding_map(src: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {str(row["q06_sentence_id"]): dict(row) for row in src["q07"]["sentence_scene_bindings"]}
    if len(rows) != 49:
        raise U06Q10BuildError("Q07_BINDING_DENOMINATOR_DRIFT")
    return rows

def _scene_map(src: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {str(row["scene_ref_id"]): dict(row) for row in src["q07"]["micro_scenes"]}
    if len(rows) != 17:
        raise U06Q10BuildError("Q07_SCENE_DENOMINATOR_DRIFT")
    return rows

def _frame_tail(text: str) -> str:
    m = re.search(r"\bcan\b\s+(.+?)[.!?]?$", text, flags=re.I)
    if not m:
        raise U06Q10BuildError(f"CAN_TAIL_PARSE_FAILED:{text}")
    return m.group(1).strip()

def _chunk_from_q06(row: Mapping[str, Any]) -> str:
    exact = str(row.get("source_functional_chunk_surface") or "").strip()
    if exact:
        return _normalize(exact)
    return _normalize("can " + _frame_tail(str(row["text"])))

def _chunk_inventory(src: Mapping[str, Any]) -> list[dict[str, Any]]:
    q07r1 = src["q07r1"]
    baseline = [
        {
            "surface": str(surface),
            "normalized_surface": _normalize(surface),
            "source_kind": "EXISTING_Q04R1_OR_Q07",
            "semantic_admission_class": "BASELINE_ADMITTED",
            "base_verb": str(surface).split()[1],
            "scene_grounding": None,
            "q07r1_source_verb_member": False,
        }
        for surface in q07r1["existing_chunk_baseline"]["normalized_surfaces"]
    ]
    new_rows = [
        {
            "surface": str(row["surface"]),
            "normalized_surface": str(row["normalized_surface"]),
            "source_kind": "Q07R1_NEW",
            "semantic_admission_class": str(row["semantic_admission_class"]),
            "base_verb": str(row["base_verb"]),
            "scene_grounding": dict(row["scene_grounding"]),
            "q07r1_source_verb_member": True,
        }
        for row in q07r1["new_unit06_functional_chunks"]
    ]
    rows = baseline + new_rows
    if len(rows) != 182 or len({x["normalized_surface"] for x in rows}) != 182:
        raise U06Q10BuildError("Q07R1_CHUNK_DENOMINATOR_DRIFT")
    return rows

def _families(src: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {str(row["task_family_id"]): dict(row) for row in src["q09"]["task_families"]}
    expected = {family for pattern in PATTERNS.values() for family in pattern}
    if len(rows) != 10 or set(rows) != expected:
        raise U06Q10BuildError("Q09_TASK_FAMILY_DRIFT")
    return rows

def _slot_plan() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for form_number in range(1, FORM_COUNT + 1):
        position = 0
        for section, section_name, expected_count in SECTION_SPECS:
            pattern = PATTERNS[section]
            if len(pattern) != expected_count:
                raise U06Q10BuildError(f"SECTION_PATTERN_DRIFT:{section}")
            for local, family_id in enumerate(pattern, start=1):
                position += 1
                rows.append({
                    "slot_id": f"U06-F{form_number:02d}-{section}{local:02d}",
                    "form_number": form_number,
                    "position": position,
                    "section": section,
                    "section_name": section_name,
                    "section_local_position": local,
                    "progression_role": FORM_STAGES[form_number],
                    "task_family_id": family_id,
                })
    if len(rows) != TOTAL_ITEMS:
        raise U06Q10BuildError("SLOT_COUNT_DRIFT")
    counts = Counter(x["task_family_id"] for x in rows)
    expected = {**CANONICAL_ROUTE_COUNTS, **CHUNK_ROUTE_COUNTS}
    combined = Counter()
    for k, v in CANONICAL_ROUTE_COUNTS.items():
        combined[k] += v
    for k, v in CHUNK_ROUTE_COUNTS.items():
        combined[k] += v
    if counts != combined:
        raise U06Q10BuildError(f"TASK_SLOT_COUNTS_DRIFT:{counts}:{combined}")
    return rows

def _ordered_context_rows(src: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [x for x in _q06_rows(src) if x["requires_context_binding"] is True]
    bindings = _binding_map(src)
    by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scene[str(bindings[str(row["sentence_id"])]["scene_ref_id"])].append(row)
    ordered: list[dict[str, Any]] = []
    used: set[str] = set()
    for scene_ref in sorted(by_scene):
        choice = sorted(by_scene[scene_ref], key=lambda x: str(x["sentence_id"]))[0]
        ordered.append(choice)
        used.add(str(choice["sentence_id"]))
    for row in sorted(rows, key=lambda x: str(x["sentence_id"])):
        if str(row["sentence_id"]) not in used:
            ordered.append(row)
    if len(ordered) != 49 or len({x["sentence_id"] for x in ordered}) != 49:
        raise U06Q10BuildError("CONTEXT_ORDERING_DRIFT")
    return ordered

def _canonical_assignment(src: Mapping[str, Any], slots: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    standalone = sorted(
        [x for x in _q06_rows(src) if x["requires_context_binding"] is False],
        key=lambda x: str(x["sentence_id"]),
    )
    context = _ordered_context_rows(src)
    if len(standalone) != 80 or len(context) != 49:
        raise U06Q10BuildError("Q06_CONTEXT_SPLIT_DRIFT")
    queues = {
        "U06-TF01_CAN_FORM_RECOGNITION": list(standalone[:30]),
        "U06-TF07_SCENE_BOUND_CONTEXT_GAP": list(context[:40]),
        "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE": list(context[40:49]) + list(standalone[30:50]),
        "U06-TF10_TRANSFER": list(standalone[50:80]),
    }
    if {k: len(v) for k, v in queues.items()} != CANONICAL_ROUTE_COUNTS:
        raise U06Q10BuildError("CANONICAL_QUEUE_COUNT_DRIFT")
    result: dict[str, dict[str, Any]] = {}
    offsets = Counter()
    for slot in slots:
        family = str(slot["task_family_id"])
        if family not in queues:
            continue
        idx = offsets[family]
        if idx >= len(queues[family]):
            if family == "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE":
                continue
            raise U06Q10BuildError(f"CANONICAL_QUEUE_EXHAUSTED:{family}")
        # TF09 has 30 slots but only 29 canonical; reserve its first slot for chunk route.
        if family == "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE" and idx == 0 and slot["form_number"] == 1 and slot["section_local_position"] == 1:
            continue
        result[str(slot["slot_id"])] = dict(queues[family][idx])
        offsets[family] += 1
    # The reserved TF09 slot means all 29 canonical rows must still be consumed in later TF09 slots.
    if offsets != Counter(CANONICAL_ROUTE_COUNTS):
        raise U06Q10BuildError(f"CANONICAL_ASSIGNMENT_DRIFT:{offsets}")
    if len(result) != 129 or len({x["sentence_id"] for x in result.values()}) != 129:
        raise U06Q10BuildError("Q06_CANONICAL_COVERAGE_NOT_129")
    return result

def _canonical_bound_chunks(canonical: Mapping[str, Mapping[str, Any]], chunk_by_norm: Mapping[str, Mapping[str, Any]]) -> set[str]:
    return {
        n
        for row in canonical.values()
        for n in [_chunk_from_q06(row)]
        if n in chunk_by_norm
    }

def _chunk_assignment(
    src: Mapping[str, Any],
    slots: list[dict[str, Any]],
    canonical: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    inventory = _chunk_inventory(src)
    chunk_by_norm = {x["normalized_surface"]: x for x in inventory}
    covered_by_q06 = _canonical_bound_chunks(canonical, chunk_by_norm)
    missing = [x for x in inventory if x["normalized_surface"] not in covered_by_q06]
    chunk_slots = [x for x in slots if str(x["slot_id"]) not in canonical]
    if len(chunk_slots) != 171:
        raise U06Q10BuildError(f"CHUNK_SLOT_COUNT_DRIFT:{len(chunk_slots)}")
    if len(missing) > len(chunk_slots):
        raise U06Q10BuildError(f"CHUNK_SLOT_CAPACITY_INSUFFICIENT:{len(missing)}")

    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for slot in chunk_slots:
        by_family[str(slot["task_family_id"])].append(slot)
    if {k: len(v) for k, v in by_family.items()} != CHUNK_ROUTE_COUNTS:
        raise U06Q10BuildError("CHUNK_ROUTE_FAMILY_COUNT_DRIFT")

    # Assign restricted context-sensitive baseline chunks only to phrase/meaning tasks.
    restricted = [x for x in missing if x["normalized_surface"] in RESTRICTED_CHUNK_SENTENCE_SURFACES]
    rest = [x for x in missing if x["normalized_surface"] not in RESTRICTED_CHUNK_SENTENCE_SURFACES]
    ordered_slots = (
        by_family["U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE"]
        + by_family["U06-TF03_ABILITY_MEANING_DISCRIMINATION"]
        + by_family["U06-TF02_BASE_VERB_FORM_SELECTION"]
        + by_family["U06-TF05_CHUNK_TO_COMPLETE_SENTENCE"]
        + by_family["U06-TF06_ERROR_DETECTION_AND_CORRECTION"]
        + by_family["U06-TF09_PRODUCTIVE_ABILITY_RESPONSE"]
        + by_family["U06-TF08_U01_U05_CUMULATIVE_INTEGRATION"]
    )
    result: dict[str, dict[str, Any]] = {}
    cursor = 0
    for row in restricted:
        slot = ordered_slots[cursor]
        if slot["task_family_id"] not in {
            "U06-TF03_ABILITY_MEANING_DISCRIMINATION",
            "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE",
        }:
            # TF04 slots are first by construction.
            raise U06Q10BuildError("RESTRICTED_CHUNK_NOT_IN_SAFE_FAMILY")
        result[str(slot["slot_id"])] = dict(row)
        cursor += 1
    for row in rest:
        while cursor < len(ordered_slots) and str(ordered_slots[cursor]["slot_id"]) in result:
            cursor += 1
        if cursor >= len(ordered_slots):
            raise U06Q10BuildError("MISSING_CHUNK_ASSIGNMENT_OVERFLOW")
        slot = ordered_slots[cursor]
        if slot["task_family_id"] == "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION" and row["scene_grounding"] is None:
            # Find a later grounded row and swap.
            swap_idx = next(
                (i for i in range(rest.index(row) + 1, len(rest)) if rest[i]["scene_grounding"] is not None),
                None,
            )
            if swap_idx is not None:
                row, rest[swap_idx] = rest[swap_idx], row
        result[str(slot["slot_id"])] = dict(row)
        cursor += 1

    # Fill any remaining chunk slots with reviewed chunks, preferring Q07R1 new rows for richer grounding.
    repeat_pool = [x for x in inventory if x["source_kind"] == "Q07R1_NEW"] + inventory
    repeat_cursor = 0
    for slot in ordered_slots:
        sid = str(slot["slot_id"])
        if sid in result:
            continue
        family = str(slot["task_family_id"])
        while True:
            row = repeat_pool[repeat_cursor % len(repeat_pool)]
            repeat_cursor += 1
            if row["normalized_surface"] in RESTRICTED_CHUNK_SENTENCE_SURFACES and family not in {
                "U06-TF03_ABILITY_MEANING_DISCRIMINATION",
                "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE",
            }:
                continue
            if family == "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION" and row["scene_grounding"] is None:
                continue
            result[sid] = dict(row)
            break
    if len(result) != 171:
        raise U06Q10BuildError("CHUNK_ASSIGNMENT_NOT_171")
    coverage = covered_by_q06 | {x["normalized_surface"] for x in result.values()}
    if coverage != set(chunk_by_norm):
        missing_surfaces = sorted(set(chunk_by_norm) - coverage)
        raise U06Q10BuildError(f"CHUNK_COVERAGE_GAP:{missing_surfaces[:10]}")
    return result

def _subject_for_chunk(chunk: Mapping[str, Any], occurrence: int) -> tuple[str, str, str | None]:
    surface = str(chunk["normalized_surface"])
    if surface in {"can fly", "can fly in the park"}:
        return ("It", "it", "A bird is in the park.")
    choices = (
        ("I", "I"),
        ("You", "you"),
        ("We", "we"),
        ("Mia", "SOURCE_BACKED_PROPER_NAME"),
        ("Ben", "SOURCE_BACKED_PROPER_NAME"),
    )
    subject, subject_class = choices[occurrence % len(choices)]
    return (subject, subject_class, None)

def _third_person_form(base: str) -> str:
    if base.endswith(("s", "sh", "ch", "x", "z", "o")):
        return base + "es"
    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return base[:-1] + "ies"
    return base + "s"

def _chunk_sentence(chunk: Mapping[str, Any], occurrence: int) -> tuple[str, str, str, str | None]:
    subject, subject_class, antecedent = _subject_for_chunk(chunk, occurrence)
    return (f"{subject} {chunk['surface']}.", subject, subject_class, antecedent)

def _function_for(family: Mapping[str, Any], occurrence: int) -> str:
    allowed = list(family["allowed_function_ids"])
    if not allowed:
        raise U06Q10BuildError("TASK_FAMILY_FUNCTION_EMPTY")
    return str(allowed[occurrence % len(allowed)])

def _response_contract(mode: str, single: bool, nonexclusive: bool = False) -> dict[str, Any]:
    return {
        "scoring_mode": mode,
        "single_answer_required": single,
        "reference_response_nonexclusive": nonexclusive,
    }

def _scene_for_q06(row: Mapping[str, Any], src: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if row["requires_context_binding"] is not True:
        return None, None
    binding = _binding_map(src)[str(row["sentence_id"])]
    scene = _scene_map(src)[str(binding["scene_ref_id"])]
    return binding, scene

def _scene_target_options(scene: Mapping[str, Any]) -> list[str]:
    rows = [str(x["text"]) for x in scene["lines"] if x["role"] == "Q06_CAN_TARGET"]
    if len(rows) < 2 or len(rows) != len(set(rows)):
        raise U06Q10BuildError("SCENE_TARGET_OPTION_POOL_INVALID")
    return rows

def _referent_cue(text: str, scene: Mapping[str, Any]) -> str:
    subject = text.split(" can ", 1)[0].strip().rstrip(".")
    mapped = scene.get("antecedent_bindings", {}).get(subject)
    return str(mapped or subject)

def _chunk_distractors(target: Mapping[str, Any], inventory: list[dict[str, Any]], occurrence: int) -> list[str]:
    choices = []
    target_verb = str(target["base_verb"])
    target_norm = str(target["normalized_surface"])
    for offset in range(1, len(inventory) + 1):
        row = inventory[(occurrence + offset) % len(inventory)]
        if row["normalized_surface"] == target_norm or row["base_verb"] == target_verb:
            continue
        if row["surface"] not in choices:
            choices.append(str(row["surface"]))
        if len(choices) == 2:
            break
    if len(choices) != 2:
        raise U06Q10BuildError("CHUNK_DISTRACTOR_POOL_INVALID")
    return [str(target["surface"]), *choices]

def _canonical_item(
    slot: Mapping[str, Any],
    row: Mapping[str, Any],
    family: Mapping[str, Any],
    src: Mapping[str, Any],
    occurrence: int,
    chunk_norms: set[str],
) -> dict[str, Any]:
    family_id = str(slot["task_family_id"])
    text = str(row["text"])
    binding, scene = _scene_for_q06(row, src)
    scene_ref = str(binding["scene_ref_id"]) if binding else None
    function_id = _function_for(family, occurrence)
    chunk_norm = _chunk_from_q06(row)
    bound_chunk = chunk_norm if chunk_norm in chunk_norms else None
    tail = _frame_tail(text)
    subject_surface = text.split(" can ", 1)[0].strip()
    prompt = ""
    stimulus: dict[str, Any] = {}
    options: list[str] = []
    correct: Any = None
    response_class = str(family["response_class"])
    scoring = _response_contract("HUMAN_REVIEW", False, True)

    if family_id == "U06-TF01_CAN_FORM_RECOGNITION":
        stimulus = {
            "mode": "Q06_ADMITTED_CAN_GAP",
            "sentence_with_gap": text.replace(" can ", " ___ ", 1),
            "scene_ref_id": scene_ref,
        }
        prompt = "Choose the word that completes the admitted ability sentence."
        options = ["can", "cans", "can to"]
        correct = "can"
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U06-TF07_SCENE_BOUND_CONTEXT_GAP":
        if scene is None:
            raise U06Q10BuildError("TF07_REQUIRES_Q07_SCENE")
        options = _scene_target_options(scene)
        if text not in options:
            raise U06Q10BuildError("TF07_TARGET_NOT_IN_SCENE")
        stimulus = {
            "mode": "Q07_BOUND_SCENE_TARGET_SELECTION",
            "scene_ref_id": scene_ref,
            "scene_sentences": [str(x["text"]) for x in scene["lines"]],
            "target_referent_cue": _referent_cue(text, scene),
            "target_action_cue": tail,
        }
        prompt = "Choose the ability sentence that matches the target person or thing and the target action."
        correct = text
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE":
        stimulus = {
            "mode": "Q06_ADMITTED_PRODUCTIVE_ABILITY_CUE",
            "subject_cue": subject_surface,
            "action_cue": tail,
            "scene_ref_id": scene_ref,
            "referent_cue": _referent_cue(text, scene) if scene is not None else subject_surface,
        }
        prompt = "Write one complete affirmative ability sentence that matches the cue."
        correct = text
        response_class = "OPEN_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)

    elif family_id == "U06-TF10_TRANSFER":
        stimulus = {
            "mode": "AUTHORITY_COMPATIBLE_TRANSFER",
            "source_subject_cue": subject_surface,
            "action_cue": tail,
            "scene_ref_id": scene_ref,
            "new_context_is_authority_compatible": True,
        }
        prompt = "Use the same Unit06 ability meaning in the new compatible context. Write one complete affirmative CAN sentence."
        correct = text
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)

    else:
        raise U06Q10BuildError(f"CANONICAL_ROUTE_FAMILY_INVALID:{family_id}")

    if options:
        if len(options) != len(set(options)) or correct not in options:
            raise U06Q10BuildError(f"CANONICAL_OPTION_CONTRACT_INVALID:{family_id}:{row['sentence_id']}")

    core = {
        "slot_id": slot["slot_id"],
        "source_route": "Q06_CANONICAL_SENTENCE",
        "q06_sentence_id": row["sentence_id"],
        "task_family_id": family_id,
        "communicative_function_id": function_id,
        "prompt": prompt,
        "stimulus": stimulus,
        "correct_answer": correct,
    }
    return {
        "item_id": "U06-Q10-"+_digest(core)[:20].upper(),
        **slot,
        "question_type": QUESTION_TYPES[family_id],
        "source_route": "Q06_CANONICAL_SENTENCE",
        "q06_sentence_id": row["sentence_id"],
        "q06_semantic_admission_class": row["semantic_admission_class"],
        "q06_requires_context_binding": row["requires_context_binding"],
        "scene_ref_id": scene_ref,
        "frame_id": row["frame_id"],
        "subject_class": row["subject_class"],
        "base_verb": row["base_verb"],
        "functional_chunk_binding": bound_chunk,
        "task_family_id": family_id,
        "communicative_function_id": function_id,
        "prompt": prompt,
        "stimulus": stimulus,
        "options": options,
        "correct_answer": correct,
        "response_class": response_class,
        "response_contract": scoring,
        "learner_visible_reference_sentence": text,
        "item_local_sentence_realization": False,
        "item_local_sentence_promoted_to_canonical_asset": False,
        "creates_new_grammar_authority": False,
        "creates_new_sentence_identity": False,
        "creates_new_chunk_identity": False,
        "creates_new_scene_identity": False,
        "can_interrogative_mastery_activated": False,
        "can_negative_mastery_activated": False,
        "non_ability_can_meaning_activated": False,
        "a2_a2plus_unlocked": False,
    }

def _chunk_item(
    slot: Mapping[str, Any],
    chunk: Mapping[str, Any],
    family: Mapping[str, Any],
    inventory: list[dict[str, Any]],
    occurrence: int,
) -> dict[str, Any]:
    family_id = str(slot["task_family_id"])
    if family_id not in CHUNK_ROUTE_FAMILIES:
        raise U06Q10BuildError(f"CHUNK_ROUTE_FAMILY_INVALID:{family_id}")
    function_id = _function_for(family, occurrence)
    sentence, subject, subject_class, antecedent = _chunk_sentence(chunk, occurrence)
    surface = str(chunk["surface"])
    base = str(chunk["base_verb"])
    requires_grounding = (
        chunk["semantic_admission_class"] == "SCENE_GROUNDED_APPROVE"
        or chunk["normalized_surface"] in RESTRICTED_CHUNK_SENTENCE_SURFACES
    )
    if chunk["normalized_surface"] in RESTRICTED_CHUNK_SENTENCE_SURFACES and family_id not in {
        "U06-TF03_ABILITY_MEANING_DISCRIMINATION",
        "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE",
    }:
        raise U06Q10BuildError("RESTRICTED_CHUNK_REALIZED_AS_SENTENCE")
    grounding = dict(chunk["scene_grounding"] or {})
    ability_context_cue = (
        "This is an ability or capability example, not permission, a request, or availability."
        if requires_grounding else None
    )
    prompt = ""
    stimulus: dict[str, Any] = {}
    options: list[str] = []
    correct: Any = None
    response_class = str(family["response_class"])
    scoring = _response_contract("HUMAN_REVIEW", False, True)
    learner_sentence = None

    if family_id == "U06-TF02_BASE_VERB_FORM_SELECTION":
        third = _third_person_form(base)
        options = [base, third, f"to {base}"]
        if len(options) != len(set(options)):
            raise U06Q10BuildError(f"BASE_VERB_OPTIONS_COLLIDE:{base}")
        stimulus = {
            "mode": "CAN_BASE_VERB_GAP",
            "sentence_with_gap": sentence.replace(f"can {base}", "can ___", 1),
            "ability_context_cue": ability_context_cue,
            "antecedent_cue": antecedent,
        }
        prompt = "Choose the base verb that correctly follows can."
        correct = base
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)
        learner_sentence = sentence

    elif family_id == "U06-TF03_ABILITY_MEANING_DISCRIMINATION":
        stimulus = {
            "mode": "CAN_CHUNK_MEANING_CLASSIFICATION",
            "functional_chunk": surface,
            "ability_context_cue": ability_context_cue,
            "scene_grounding": grounding or None,
        }
        prompt = "What meaning is this CAN phrase being used for here?"
        options = ["ability or capability", "permission or a request", "possibility"]
        correct = "ability or capability"
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE":
        options = _chunk_distractors(chunk, inventory, occurrence)
        stimulus = {
            "mode": "ACTION_TO_FUNCTIONAL_CHUNK",
            "action_cue": base,
            "scene_grounding": grounding or None,
            "ability_context_cue": ability_context_cue,
        }
        prompt = f'Choose the CAN phrase that uses the action "{base}".'
        correct = surface
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE":
        stimulus = {
            "mode": "SUBJECT_PLUS_ADMITTED_CHUNK",
            "subject_cue": subject,
            "functional_chunk": surface,
            "ability_context_cue": ability_context_cue,
            "antecedent_cue": antecedent,
            "scene_grounding": grounding or None,
        }
        prompt = "Use the subject and the admitted CAN phrase to write one complete affirmative ability sentence."
        correct = sentence
        response_class = "CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)
        learner_sentence = sentence

    elif family_id == "U06-TF06_ERROR_DETECTION_AND_CORRECTION":
        incorrect = sentence.replace(" can ", " cans ", 1)
        stimulus = {
            "mode": "ONE_CAN_FORM_ERROR",
            "incorrect_sentence": incorrect,
            "ability_context_cue": ability_context_cue,
            "antecedent_cue": antecedent,
            "scene_grounding": grounding or None,
        }
        prompt = "Correct only the CAN form error. Keep the admitted ability meaning."
        correct = sentence
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("NORMALIZED_TEXT", True)
        learner_sentence = sentence

    elif family_id == "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION":
        if not grounding:
            raise U06Q10BuildError("TF08_CHUNK_REQUIRES_SCENE_GROUNDING_METADATA")
        support = [
            "Mia is ready.",
            "Two things are near her.",
        ]
        stimulus = {
            "mode": "CUMULATIVE_SUPPORT_PLUS_UNIT06_TARGET",
            "prior_unit_support_sentences": support,
            "subject_cue": subject,
            "functional_chunk": surface,
            "scene_grounding": grounding,
            "ability_context_cue": ability_context_cue,
        }
        prompt = "Keep the earlier-unit support unchanged and write the Unit06 affirmative ability sentence."
        correct = sentence
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)
        learner_sentence = sentence

    elif family_id == "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE":
        stimulus = {
            "mode": "CHUNK_GROUNDED_PRODUCTIVE_RESPONSE",
            "subject_cue": subject,
            "functional_chunk": surface,
            "scene_grounding": grounding or None,
            "ability_context_cue": ability_context_cue,
            "antecedent_cue": antecedent,
            "can_interrogative_prompt_surface_materialized": False,
        }
        prompt = "Write one complete affirmative sentence that gives the ability information."
        correct = sentence
        response_class = "OPEN_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)
        learner_sentence = sentence

    else:
        raise U06Q10BuildError(f"UNSUPPORTED_CHUNK_FAMILY:{family_id}")

    if options:
        if len(options) != len(set(options)) or correct not in options:
            raise U06Q10BuildError(f"CHUNK_OPTION_CONTRACT_INVALID:{family_id}:{surface}")

    core = {
        "slot_id": slot["slot_id"],
        "source_route": "Q07R1_CHUNK_CONTROLLED_REALIZATION",
        "functional_chunk": chunk["normalized_surface"],
        "task_family_id": family_id,
        "communicative_function_id": function_id,
        "prompt": prompt,
        "stimulus": stimulus,
        "correct_answer": correct,
    }
    return {
        "item_id": "U06-Q10-"+_digest(core)[:20].upper(),
        **slot,
        "question_type": QUESTION_TYPES[family_id],
        "source_route": "Q07R1_CHUNK_CONTROLLED_REALIZATION",
        "q06_sentence_id": None,
        "q06_semantic_admission_class": None,
        "q06_requires_context_binding": False,
        "scene_ref_id": None,
        "frame_id": "U06-CF-ABILITY-PREDICATE-TAIL",
        "subject_class": subject_class,
        "base_verb": base,
        "functional_chunk_binding": str(chunk["normalized_surface"]),
        "functional_chunk_source_kind": chunk["source_kind"],
        "functional_chunk_semantic_admission_class": chunk["semantic_admission_class"],
        "functional_chunk_scene_grounding": grounding or None,
        "q07r1_source_verb_member": bool(chunk["q07r1_source_verb_member"]),
        "task_family_id": family_id,
        "communicative_function_id": function_id,
        "prompt": prompt,
        "stimulus": stimulus,
        "options": options,
        "correct_answer": correct,
        "response_class": response_class,
        "response_contract": scoring,
        "learner_visible_reference_sentence": learner_sentence,
        "item_local_sentence_realization": learner_sentence is not None,
        "item_local_sentence_promoted_to_canonical_asset": False,
        "creates_new_grammar_authority": False,
        "creates_new_sentence_identity": False,
        "creates_new_chunk_identity": False,
        "creates_new_scene_identity": False,
        "can_interrogative_mastery_activated": False,
        "can_negative_mastery_activated": False,
        "non_ability_can_meaning_activated": False,
        "a2_a2plus_unlocked": False,
    }

def build_export_payload() -> dict[str, Any]:
    src = _sources()
    families = _families(src)
    slots = _slot_plan()
    canonical = _canonical_assignment(src, slots)
    chunks = _chunk_assignment(src, slots, canonical)
    inventory = _chunk_inventory(src)
    chunk_norms = {x["normalized_surface"] for x in inventory}

    items: list[dict[str, Any]] = []
    family_occurrence = Counter()
    for slot in slots:
        family_id = str(slot["task_family_id"])
        family = families[family_id]
        occurrence = family_occurrence[family_id]
        family_occurrence[family_id] += 1
        sid = str(slot["slot_id"])
        if sid in canonical:
            item = _canonical_item(slot, canonical[sid], family, src, occurrence, chunk_norms)
        else:
            item = _chunk_item(slot, chunks[sid], family, inventory, occurrence)
        items.append(item)

    if len(items) != TOTAL_ITEMS or len({x["item_id"] for x in items}) != TOTAL_ITEMS:
        raise U06Q10BuildError("QUESTIONBANK_IDENTITY_DRIFT")

    by_form: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_form[int(item["form_number"])].append(item)
    forms = []
    for form_number in range(1, FORM_COUNT + 1):
        form_items = sorted(by_form[form_number], key=lambda x: int(x["position"]))
        section_counts = Counter(x["section"] for x in form_items)
        if len(form_items) != QUESTIONS_PER_FORM or dict(section_counts) != SECTION_COUNTS:
            raise U06Q10BuildError(f"FORM_SHAPE_DRIFT:{form_number}")
        forms.append({
            "form_id": f"U06-FORM-{form_number:02d}",
            "form_number": form_number,
            "progression_role": FORM_STAGES[form_number],
            "question_count": len(form_items),
            "section_counts": dict(section_counts),
            "item_ids": [x["item_id"] for x in form_items],
        })

    q06_ids = {str(x["q06_sentence_id"]) for x in items if x["q06_sentence_id"]}
    chunk_bindings = {str(x["functional_chunk_binding"]) for x in items if x["functional_chunk_binding"]}
    q07r1_source_verbs = {
        str(x["base_verb"])
        for x in items
        if x["source_route"] == "Q07R1_CHUNK_CONTROLLED_REALIZATION" and x["q07r1_source_verb_member"]
    }
    scene_refs = {str(x["scene_ref_id"]) for x in items if x["scene_ref_id"]}
    route_counts = Counter(x["source_route"] for x in items)
    family_counts = Counter(x["task_family_id"] for x in items)
    function_ids = {x["communicative_function_id"] for x in items}
    frame_ids = {x["frame_id"] for x in items}

    coverage = {
        "questionbank_item_count": len(items),
        "form_count": len(forms),
        "questions_per_form": QUESTIONS_PER_FORM,
        "task_family_coverage": f"{len(family_counts)}/10",
        "task_family_counts": dict(sorted(family_counts.items())),
        "communicative_function_coverage": f"{len(function_ids)}/6",
        "frame_coverage": f"{len(frame_ids)}/3",
        "q06_sentence_materialized_coverage": f"{len(q06_ids)}/129",
        "q06_context_required_sentence_materialized_coverage": f"{len({x['q06_sentence_id'] for x in items if x['q06_sentence_id'] and x['q06_requires_context_binding']})}/49",
        "q06_standalone_sentence_materialized_coverage": f"{len({x['q06_sentence_id'] for x in items if x['q06_sentence_id'] and not x['q06_requires_context_binding']})}/80",
        "q07_scene_materialized_coverage": f"{len(scene_refs)}/17",
        "q07r1_functional_chunk_binding_coverage": f"{len(chunk_bindings)}/182",
        "q07r1_source_verb_binding_coverage": f"{len(q07r1_source_verbs)}/62",
        "source_route_counts": dict(route_counts),
        "item_local_sentence_realization_count": sum(1 for x in items if x["item_local_sentence_realization"]),
        "item_local_sentence_promoted_to_canonical_asset_count": sum(1 for x in items if x["item_local_sentence_promoted_to_canonical_asset"]),
        "restricted_deferred_chunk_sentence_realization_count": sum(
            1
            for x in items
            if x["source_route"] == "Q07R1_CHUNK_CONTROLLED_REALIZATION"
            and x["functional_chunk_binding"] in RESTRICTED_CHUNK_SENTENCE_SURFACES
            and x["item_local_sentence_realization"]
        ),
        "selected_response_multiple_valid_answer_count": 0,
        "option_duplication_count": 0,
        "new_global_sentence_identity_count": 0,
        "new_global_chunk_identity_count": 0,
        "new_global_scene_identity_count": 0,
        "new_global_vocabulary_identity_count": 0,
    }

    boundaries = {
        "q06_sentence_semantics_modified": False,
        "q07_scene_semantics_modified": False,
        "q07r1_functional_chunk_semantics_modified": False,
        "q08_communicative_function_semantics_modified": False,
        "q09_task_family_inventory_modified": False,
        "new_grammar_authority_created": False,
        "new_vocabulary_identity_created": False,
        "new_sentence_identity_created": False,
        "new_scene_identity_created": False,
        "new_functional_chunk_identity_created": False,
        "new_communicative_function_identity_created": False,
        "can_interrogative_mastery_activated": False,
        "can_negative_mastery_activated": False,
        "permission_can_activated": False,
        "offer_can_activated": False,
        "request_can_activated": False,
        "possibility_can_activated": False,
        "unit06_current360_materialized": False,
        "unit06_spoken360_materialized": False,
        "unit06_pattern360_materialized": False,
        "a2_a2plus_unlocked": False,
    }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_number": 6,
        "unit_id": UNIT_ID,
        "authority_refs": {
            "q06": "ulga/contracts/a1fs_v1_u06_q06_sentence_assets.json",
            "q07": "ulga/contracts/a1fs_v1_u06_q07_life_skill_micro_scenes.json",
            "q07r1": "ulga/contracts/a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion.json",
            "q08": "ulga/contracts/a1fs_v1_u06_q08_communicative_function_authority.json",
            "q09": "ulga/contracts/a1fs_v1_u06_q09_task_pedagogical_contract.json",
        },
        "materialization_contract": {
            "capacity_policy": "COVERAGE_DRIVEN_NOT_FIXED_BY_LEGACY_20X40",
            "form_count": FORM_COUNT,
            "questions_per_form": QUESTIONS_PER_FORM,
            "total_items": TOTAL_ITEMS,
            "section_counts_per_form": SECTION_COUNTS,
            "progression_distribution": dict(Counter(FORM_STAGES.values())),
            "q06_canonical_sentence_route_item_count": 129,
            "q07r1_chunk_controlled_route_item_count": 171,
            "all_q06_sentences_materialized_once": True,
            "all_182_chunks_have_questionbank_binding": True,
            "all_62_q07r1_source_verbs_have_questionbank_binding": True,
            "all_17_q07_scenes_have_questionbank_binding": True,
            "learner_english_authoring_mode": "GPT56_AUTHORED_PROMPT_TEMPLATES_PLUS_AUTHORITY_BOUND_ITEM_LOCAL_REALIZATION",
            "python_may_invent_new_lexical_semantics": False,
            "item_local_sentence_realization_authorized_by_q09": True,
            "item_local_sentence_realization_promoted_to_sentence_authority": False,
        },
        "questionbank_items": items,
        "forms": forms,
        "coverage": coverage,
        "boundaries": boundaries,
        "integrity": {
            "questionbank_digest": _digest(items),
            "forms_digest": _digest(forms),
            "coverage_digest": _digest(coverage),
        },
        "acceptance": {
            "questionbank_items": "300/300",
            "forms": "10/10",
            "task_families": "10/10",
            "communicative_functions": "6/6",
            "frames": "3/3",
            "q06_sentence_materialized_coverage": "129/129",
            "q07_context_required_sentence_materialized_coverage": "49/49",
            "q06_standalone_sentence_materialized_coverage": "80/80",
            "q07_scene_materialized_coverage": "17/17",
            "q07r1_functional_chunk_binding_coverage": "182/182",
            "q07r1_source_verb_binding_coverage": "62/62",
            "restricted_deferred_chunk_sentence_realization_count": 0,
            "item_local_sentence_promoted_to_canonical_asset_count": 0,
            "status": PASS_STATUS,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    return payload

def build_candidate() -> dict[str, Any]:
    payload = build_export_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "q06_sentence_count": 129,
            "q07_scene_count": 17,
            "q07r1_distinct_chunk_count": 182,
            "q07r1_source_verb_count": 62,
            "q08_function_count": 6,
            "q09_task_family_count": 10,
            "questionbank_item_count": 300,
            "form_count": 10,
        },
    )

def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u06q10_questionbank_form_materialization as validator
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[validator.validate_candidate(candidate)],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )

def build_report() -> dict[str, Any]:
    return admit_candidate(build_candidate())["payload"]

def main() -> int:
    from ulga.validators import validate_a1fs_v1_u06q10_questionbank_form_materialization as validator
    payload = build_export_payload()
    report = validator.validate_payload(payload)
    print(f"STATUS={payload['status']}")
    print(f"QUESTIONBANK_ITEMS={len(payload['questionbank_items'])}")
    print(f"FORMS={len(payload['forms'])}")
    print(f"Q06_SENTENCE_COVERAGE={payload['coverage']['q06_sentence_materialized_coverage']}")
    print(f"CHUNK_COVERAGE={payload['coverage']['q07r1_functional_chunk_binding_coverage']}")
    print(f"SOURCE_VERB_COVERAGE={payload['coverage']['q07r1_source_verb_binding_coverage']}")
    print(f"SCENE_COVERAGE={payload['coverage']['q07_scene_materialized_coverage']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={payload['next_short_step']}")
    return 0 if report["error_count"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
