#!/usr/bin/env python3
"""Unit05 Q10: deterministic 20x40 QuestionBank and Form materialization."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u05_q06_sentence_assets as q06_builder
from ulga.builders import build_a1fs_v1_u05_q07_life_skill_micro_scenes as q07_builder

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BE_VERB_BASIC"
TASK_ID = "A1FS-V1-U05Q10_Unit05QuestionBankAndFormMaterialization"
SCHEMA_VERSION = "a1fs.v1.u05.q10.questionbank_form_materialization.v1"
PASS_STATUS = "PASS_A1FS_V1_U05Q10_QUESTIONBANK_AND_FORM_MATERIALIZATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-09-21:U05_Q10_20X40_800"
NEXT_SHORT_STEP = "A1FS-V1-U05Q10R1_Unit05LearnerFacingPedagogicalAcceptance"

Q08 = ROOT / "ulga/contracts/a1fs_v1_u05_q08_communicative_function_authority.json"
Q09 = ROOT / "ulga/contracts/a1fs_v1_u05_q09_task_pedagogical_contract.json"

FORM_COUNT = 20
QUESTIONS_PER_FORM = 40
TOTAL_ITEMS = 800
CANDIDATES_PER_SLOT = 3

SECTION_SPECS = (
    ("A", "FORM_AND_AGREEMENT_RECOGNITION", 6),
    ("B", "MEANING_POLARITY_AND_SCENE_TRUTH", 10),
    ("C", "CONSTRUCTION_AND_REPAIR", 10),
    ("D", "CONNECTED_CONTEXT_AND_CUMULATIVE_INTEGRATION", 8),
    ("E", "PRODUCTIVE_RESPONSE_AND_TRANSFER", 6),
)
SECTION_COUNTS = {section: count for section, _, count in SECTION_SPECS}

STAGE_BY_FORMS = {
    "GUIDED": range(1, 5),
    "REDUCED_SUPPORT": range(5, 9),
    "INDEPENDENT": range(9, 13),
    "TRANSFER": range(13, 17),
    "RETENTION": range(17, 21),
}

PATTERNS = {
    "A": (
        "U05-TF01_BE_FORM_RECOGNITION",
        "U05-TF02_SUBJECT_BE_AGREEMENT_SELECTION",
    ) * 3,
    "B": (
        "U05-TF03_COMPLEMENT_MEANING_DISCRIMINATION",
        "U05-TF04_AFFIRMATIVE_NEGATIVE_INTERPRETATION",
    ) * 5,
    "C": (
        "U05-TF05_SENTENCE_CONSTRUCTION",
        "U05-TF06_ERROR_DETECTION_AND_CORRECTION",
        "U05-TF07_CONTEXT_GAP",
        "U05-TF05_SENTENCE_CONSTRUCTION",
        "U05-TF06_ERROR_DETECTION_AND_CORRECTION",
        "U05-TF07_CONTEXT_GAP",
        "U05-TF05_SENTENCE_CONSTRUCTION",
        "U05-TF06_ERROR_DETECTION_AND_CORRECTION",
        "U05-TF07_CONTEXT_GAP",
        "U05-TF05_SENTENCE_CONSTRUCTION",
    ),
    "D": (
        "U05-TF07_CONTEXT_GAP",
        "U05-TF08_U01_U04_CUMULATIVE_INTEGRATION",
    ) * 4,
    "E": (
        "U05-TF09_PRODUCTIVE_RESPONSE",
        "U05-TF10_TRANSFER",
    ) * 3,
}

QUESTION_TYPES = {
    "U05-TF01_BE_FORM_RECOGNITION": "be_form_recognition",
    "U05-TF02_SUBJECT_BE_AGREEMENT_SELECTION": "subject_be_agreement",
    "U05-TF03_COMPLEMENT_MEANING_DISCRIMINATION": "complement_meaning",
    "U05-TF04_AFFIRMATIVE_NEGATIVE_INTERPRETATION": "affirmative_negative_truth",
    "U05-TF05_SENTENCE_CONSTRUCTION": "sentence_construction",
    "U05-TF06_ERROR_DETECTION_AND_CORRECTION": "error_detection_or_correction",
    "U05-TF07_CONTEXT_GAP": "context_completion",
    "U05-TF08_U01_U04_CUMULATIVE_INTEGRATION": "cumulative_integration",
    "U05-TF09_PRODUCTIVE_RESPONSE": "short_productive_response",
    "U05-TF10_TRANSFER": "unseen_transfer",
}

SUBJECT_ORDER = (
    "I",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "ADMITTED_SINGULAR_NOUN_PHRASE",
    "ADMITTED_PLURAL_NOUN_PHRASE",
)
FRAME_ORDER = (
    "U05-BF-NP-AFF",
    "U05-BF-ADJ-AFF",
    "U05-BF-PLACE-AFF",
    "U05-BF-NP-NEG",
    "U05-BF-ADJ-NEG",
    "U05-BF-PLACE-NEG",
)
FULL_REQUIRED_FAMILIES = {
    "U05-TF01_BE_FORM_RECOGNITION",
    "U05-TF02_SUBJECT_BE_AGREEMENT_SELECTION",
    "U05-TF06_ERROR_DETECTION_AND_CORRECTION",
    "U05-TF08_U01_U04_CUMULATIVE_INTEGRATION",
}
CONTEXT_REQUIRED_FAMILIES = {"U05-TF07_CONTEXT_GAP"}

class U05Q10BuildError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _stage(form_number: int) -> str:
    for stage, forms in STAGE_BY_FORMS.items():
        if form_number in forms:
            return stage
    raise U05Q10BuildError(f"FORM_STAGE_MISSING:{form_number}")


def _q06_identity(row: Mapping[str, Any]) -> str:
    return str(row.get("sentence_id") or row.get("binding_id") or "")


def _sources() -> dict[str, Any]:
    q06 = q06_builder.build_report()
    q07 = q07_builder.build_report()
    q08 = _load(Q08)
    q09 = _load(Q09)
    expected = (
        (q06, "PASS_A1FS_V1_U05Q06_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"),
        (q07, "PASS_A1FS_V1_U05Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"),
        (q08, "PASS_A1FS_V1_U05Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"),
        (q09, "PASS_A1FS_V1_U05Q09_TASK_AND_PEDAGOGICAL_CONTRACT"),
    )
    for payload, status in expected:
        if payload.get("status") != status:
            raise U05Q10BuildError(f"SOURCE_STATUS_DRIFT:{payload.get('task_id')}")
    return {"q06": q06, "q07": q07, "q08": q08, "q09": q09}


def _families(src: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {str(row["task_family_id"]): dict(row) for row in src["q09"]["task_families"]}
    expected = {family for pattern in PATTERNS.values() for family in pattern}
    if len(rows) != 10 or set(rows) != expected:
        raise U05Q10BuildError("Q09_TASK_FAMILY_DRIFT")
    return rows


def _q06_rows(src: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [*src["q06"]["reuse_bindings"], *src["q06"]["new_sentence_assets"]]
    if len(rows) != 855:
        raise U05Q10BuildError(f"Q06_USABLE_COUNT_DRIFT:{len(rows)}")
    if len({_q06_identity(row) for row in rows}) != 855:
        raise U05Q10BuildError("Q06_IDENTITY_COLLISION")
    return [dict(row) for row in rows]


def _binding_map(src: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    bindings = {str(row["q06_identity"]): dict(row) for row in src["q07"]["sentence_scene_bindings"]}
    if len(bindings) != 478:
        raise U05Q10BuildError("Q07_BINDING_COUNT_DRIFT")
    return bindings


def _scene_map(src: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    scenes = {str(row["scene_ref_id"]): dict(row) for row in src["q07"]["micro_scenes"]}
    if not scenes:
        raise U05Q10BuildError("Q07_SCENE_POOL_EMPTY")
    return scenes


def _function_for(
    row: Mapping[str, Any],
    family: Mapping[str, Any],
    src: Mapping[str, Any],
    occurrence: int,
) -> str:
    frame = str(row["frame_id"])
    allowed_by_frame = set(src["q08"]["frame_function_compatibility"][frame])
    allowed_by_family = set(family["allowed_function_ids"])
    compatible = sorted(allowed_by_frame & allowed_by_family)
    if not compatible:
        raise U05Q10BuildError(f"FUNCTION_COMPATIBILITY_EMPTY:{family['task_family_id']}:{frame}")
    return compatible[occurrence % len(compatible)]


def _desired_variant(family_id: str, occurrence: int) -> str:
    if family_id in FULL_REQUIRED_FAMILIES:
        return "FULL"
    return ("CONTRACTED", "FULL", "CONTRACTED_ALT")[occurrence % 3]


def _eligible(row: Mapping[str, Any], family_id: str) -> bool:
    if family_id in FULL_REQUIRED_FAMILIES and row["surface_variant"] != "FULL":
        return False
    if family_id in CONTEXT_REQUIRED_FAMILIES and row["requires_context_binding"] is not True:
        return False
    return True


def _choose_source(
    rows: Sequence[Mapping[str, Any]],
    used: set[str],
    family_id: str,
    occurrence: int,
) -> dict[str, Any]:
    desired_subject = SUBJECT_ORDER[occurrence % len(SUBJECT_ORDER)]
    desired_frame = FRAME_ORDER[occurrence % len(FRAME_ORDER)]
    desired_variant = _desired_variant(family_id, occurrence)
    candidates = [
        dict(row)
        for row in rows
        if _q06_identity(row) not in used and _eligible(row, family_id)
    ]
    if not candidates:
        raise U05Q10BuildError(f"SOURCE_POOL_EXHAUSTED:{family_id}")
    candidates.sort(
        key=lambda row: (
            0 if row["subject_class"] == desired_subject else 1,
            0 if row["frame_id"] == desired_frame else 1,
            0 if row["surface_variant"] == desired_variant else 1,
            0 if row["requires_context_binding"] else 1,
            str(row["normalized_text"]),
        )
    )
    selected = candidates[0]
    used.add(_q06_identity(selected))
    return selected


def _frame_base(frame_id: str) -> str:
    if "-NP-" in frame_id:
        return "NP"
    if "-ADJ-" in frame_id:
        return "ADJ"
    if "-PLACE-" in frame_id:
        return "PLACE"
    raise U05Q10BuildError(f"UNKNOWN_FRAME:{frame_id}")


def _complement_label(frame_id: str) -> str:
    return {
        "NP": "IDENTITY_OR_CATEGORY",
        "ADJ": "DESCRIPTION_OR_STATE",
        "PLACE": "STATIC_LOCATION",
    }[_frame_base(frame_id)]


def _full_be_realization(row: Mapping[str, Any]) -> str:
    be_form = str(row["be_form"])
    return be_form if row["polarity"] == "AFFIRMATIVE" else f"{be_form} not"


def _agreement_options(row: Mapping[str, Any]) -> list[str]:
    if row["polarity"] == "AFFIRMATIVE":
        return ["am", "is", "are"]
    return ["am not", "is not", "are not"]


def _context_gap_options(row: Mapping[str, Any]) -> list[str]:
    be_form = str(row["be_form"])
    if be_form == "am":
        return ["am", "am not", "is"]
    if be_form == "is":
        return ["is", "is not", "are"]
    return ["are", "are not", "is"]


def _wrong_be(row: Mapping[str, Any]) -> str:
    be_form = str(row["be_form"])
    wrong = {"am": "is", "is": "are", "are": "is"}[be_form]
    return wrong if row["polarity"] == "AFFIRMATIVE" else f"{wrong} not"


def _full_sentence_with_be(row: Mapping[str, Any], be_realization: str) -> str:
    subject = str(row["subject_surface"])
    complement = str(row["complement_surface"])
    return f"{subject[:1].upper() + subject[1:]} {be_realization} {complement}."


def _semantic_proposition_key(row: Mapping[str, Any]) -> str:
    core = {
        "frame_id": row["frame_id"],
        "polarity": row["polarity"],
        "subject_surface": str(row["subject_surface"]).casefold(),
        "complement_surface": str(row["complement_surface"]).casefold(),
        "relation_surface": row.get("relation_surface"),
    }
    return _digest(core)


def _response_contract(mode: str, single: bool, nonexclusive: bool = False) -> dict[str, Any]:
    return {
        "scoring_mode": mode,
        "single_answer_required": single,
        "reference_response_nonexclusive": nonexclusive,
    }


def _item(
    form_number: int,
    section: str,
    section_name: str,
    local: int,
    family_id: str,
    family: Mapping[str, Any],
    row: Mapping[str, Any],
    function_id: str,
    binding: Mapping[str, Any] | None,
    scene: Mapping[str, Any] | None,
    occurrence: int,
) -> dict[str, Any]:
    stage = _stage(form_number)
    qid = _q06_identity(row)
    frame_id = str(row["frame_id"])
    source_text = str(row["text"])
    scene_ref = str(binding["scene_ref_id"]) if binding else None
    stimulus: dict[str, Any]
    prompt: str
    options: list[str] = []
    correct: Any = None
    answerability_basis = "Q06_APPROVED_SENTENCE"
    response_class = str(family["response_class"])
    question_type = QUESTION_TYPES[family_id]

    if row["requires_context_binding"]:
        if binding is None or scene is None:
            raise U05Q10BuildError(f"CONTEXT_BINDING_MISSING:{qid}")
        answerability_basis = "Q06_APPROVED_SENTENCE_PLUS_Q07_BOUND_SCENE"

    if family_id == "U05-TF01_BE_FORM_RECOGNITION":
        correct = _full_be_realization(row)
        options = _agreement_options(row)
        stimulus = {
            "mode": "ADMITTED_SENTENCE_WITH_BE_GAP",
            "subject_surface": row["subject_surface"],
            "complement_surface": row["complement_surface"],
            "polarity": row["polarity"],
            "scene_ref_id": scene_ref,
        }
        prompt = "Choose the admitted present-be form that completes the sentence."
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U05-TF02_SUBJECT_BE_AGREEMENT_SELECTION":
        correct = _full_be_realization(row)
        options = _agreement_options(row)
        stimulus = {
            "mode": "SUBJECT_AGREEMENT_SELECTION",
            "subject_surface": row["subject_surface"],
            "complement_surface": row["complement_surface"],
            "polarity": row["polarity"],
            "scene_ref_id": scene_ref,
        }
        prompt = "Choose the present-be form that agrees with the subject and the licensed polarity."
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U05-TF03_COMPLEMENT_MEANING_DISCRIMINATION":
        correct = _complement_label(frame_id)
        options = ["IDENTITY_OR_CATEGORY", "DESCRIPTION_OR_STATE", "STATIC_LOCATION"]
        stimulus = {
            "mode": "ADMITTED_SENTENCE_MEANING_CLASSIFICATION",
            "sentence_text": source_text,
            "scene_ref_id": scene_ref,
        }
        prompt = "What kind of meaning does the admitted be-complement express?"
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U05-TF04_AFFIRMATIVE_NEGATIVE_INTERPRETATION":
        correct = str(row["polarity"])
        options = ["AFFIRMATIVE", "NEGATIVE"]
        stimulus = {
            "mode": "ADMITTED_SENTENCE_POLARITY_INTERPRETATION",
            "sentence_text": source_text,
            "scene_ref_id": scene_ref,
            "explicit_positive_contrast_evidence": (
                scene["truth_evidence_spec"]["explicit_positive_alternative_required_for_negative"]
                if scene is not None and row["polarity"] == "NEGATIVE"
                else False
            ),
        }
        prompt = "Does the admitted sentence affirm the proposition or deny/correct it?"
        response_class = "SELECTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U05-TF05_SENTENCE_CONSTRUCTION":
        stimulus = {
            "mode": "BOUNDED_SENTENCE_PARTS",
            "subject_surface": row["subject_surface"],
            "required_be_family": row["be_form"],
            "polarity": row["polarity"],
            "complement_surface": row["complement_surface"],
            "scene_ref_id": scene_ref,
        }
        prompt = "Build one complete present-be sentence from the admitted parts. Equivalent admitted full or contracted realization may be accepted."
        correct = source_text
        response_class = "CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)

    elif family_id == "U05-TF06_ERROR_DETECTION_AND_CORRECTION":
        wrong_sentence = _full_sentence_with_be(row, _wrong_be(row))
        stimulus = {
            "mode": "ONE_BE_AGREEMENT_ERROR",
            "incorrect_sentence": wrong_sentence,
            "scene_ref_id": scene_ref,
        }
        prompt = "Correct only the present-be agreement error."
        correct = source_text
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("NORMALIZED_TEXT", True)

    elif family_id == "U05-TF07_CONTEXT_GAP":
        stimulus = {
            "mode": "Q07_SCENE_BOUND_BE_GAP",
            "scene_ref_id": scene_ref,
            "subject_surface": row["subject_surface"],
            "complement_surface": row["complement_surface"],
            "referent_binding_spec": scene["referent_binding_spec"] if scene else None,
            "truth_evidence_spec": scene["truth_evidence_spec"] if scene else None,
        }
        prompt = "Use the bound scene evidence to complete the present-be meaning. Give one admitted sentence."
        correct = source_text
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)

    elif family_id == "U05-TF08_U01_U04_CUMULATIVE_INTEGRATION":
        correct = _full_be_realization(row)
        options = _agreement_options(row)
        stimulus = {
            "mode": "CUMULATIVE_CARRIER_WITH_UNIT05_BE_TARGET",
            "sentence_without_be": f"{row['subject_surface']} ___ {row['complement_surface']}.",
            "unit01_article_carrier_possible": True,
            "unit02_plural_carrier_possible": True,
            "unit03_reference_carrier_possible": True,
            "unit04_static_place_carrier_possible": _frame_base(frame_id) == "PLACE",
            "scene_ref_id": scene_ref,
        }
        prompt = "Keep the earlier-unit carriers unchanged and choose the Unit05 present-be target."
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("EXACT_OPTION", True)

    elif family_id == "U05-TF09_PRODUCTIVE_RESPONSE":
        if function_id == "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
            stimulus = {
                "mode": "INFORMATION_REQUEST_USING_EXISTING_CUMULATIVE_QUESTION_FORM",
                "known_proposition_reference": qid,
                "scene_ref_id": scene_ref,
                "exact_question_form_materialized_by_unit05": False,
            }
            prompt = "Ask for the missing information using an already-admitted cumulative question form. Do not create a new Unit05 interrogative target."
            correct = None
        else:
            stimulus = {
                "mode": "PRODUCTIVE_BE_RESPONSE",
                "communicative_function_id": function_id,
                "scene_ref_id": scene_ref,
                "subject_or_entity_cue": row["subject_surface"],
                "meaning_cue": _complement_label(frame_id),
            }
            prompt = "Produce one complete Unit05 present-be response that matches the licensed meaning."
            correct = source_text
        response_class = "OPEN_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)

    elif family_id == "U05-TF10_TRANSFER":
        if function_id == "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
            stimulus = {
                "mode": "TRANSFER_INFORMATION_REQUEST",
                "authority_compatible_new_context": True,
                "scene_ref_id": scene_ref,
                "exact_question_form_materialized_by_unit05": False,
            }
            prompt = "In this new context, request the needed information using prior admitted question grammar; do not introduce a new Unit05 question pattern."
            correct = None
        else:
            stimulus = {
                "mode": "TRANSFER_PRESENT_BE_APPLICATION",
                "authority_compatible_new_context": True,
                "scene_ref_id": scene_ref,
                "subject_class": row["subject_class"],
                "meaning_cue": _complement_label(frame_id),
                "polarity": row["polarity"],
            }
            prompt = "Apply the same Unit05 present-be system to the new authority-compatible context."
            correct = source_text
        response_class = "SELECTED_OR_CONSTRUCTED_RESPONSE"
        scoring = _response_contract("HUMAN_REVIEW", False, True)

    else:
        raise U05Q10BuildError(f"UNSUPPORTED_FAMILY:{family_id}")

    if options:
        if len(options) != len(set(options)) or correct not in options:
            raise U05Q10BuildError(f"OPTION_CONTRACT_INVALID:{family_id}:{qid}")

    core = {
        "form_number": form_number,
        "stage": stage,
        "section": section,
        "local": local,
        "family_id": family_id,
        "function_id": function_id,
        "q06_identity": qid,
        "question_type": question_type,
        "stimulus": stimulus,
        "prompt": prompt,
        "options": options,
        "correct_answer": correct,
    }
    signature = _digest(core)
    item_id = f"U05Q10-F{form_number:02d}-{section}{local:02d}-{signature[:12].upper()}"

    return {
        "item_id": item_id,
        "unit_id": UNIT_ID,
        "form_number": form_number,
        "progression_role": stage,
        "section": section,
        "section_name": section_name,
        "section_activity_ordinal": local,
        "task_family_id": family_id,
        "task_family_name": family["family_name"],
        "question_type": question_type,
        "communicative_function_id": function_id,
        "frame_id": frame_id,
        "polarity": row["polarity"],
        "subject_class": row["subject_class"],
        "subject_surface": row["subject_surface"],
        "complement_surface": row["complement_surface"],
        "relation_surface": row.get("relation_surface"),
        "surface_variant": row["surface_variant"],
        "q06_identity": qid,
        "q06_generation_role": row["generation_role"],
        "q06_semantic_admission_class": row["semantic_admission_class"],
        "requires_context_binding": row["requires_context_binding"],
        "scene_ref_id": scene_ref,
        "stimulus": stimulus,
        "prompt": prompt,
        "options": options,
        "correct_answer": correct,
        "response_class": response_class,
        "response_contract": scoring,
        "answerability_basis": answerability_basis,
        "single_answer_unique_cue_required": bool(options),
        "semantic_proposition_key": _semantic_proposition_key(row),
        "item_semantic_signature": signature,
        "surface_variant_is_new_semantics": False,
        "creates_new_grammar_authority": False,
        "creates_new_vocabulary_identity": False,
        "creates_new_sentence_identity": False,
        "creates_new_scene_identity": False,
        "creates_new_communicative_function_identity": False,
        "be_interrogative_mastery_activated": False,
        "past_be_activated": False,
        "existential_there_be_activated": False,
        "present_continuous_mastery_activated": False,
        "a2_a2plus_unlocked": False,
    }


def _runtime(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[str]] = defaultdict(list)
    for row in items:
        by_family[str(row["task_family_id"])].append(str(row["item_id"]))
    runtime: list[dict[str, Any]] = []
    for row in items:
        family = str(row["task_family_id"])
        pool = by_family[family]
        selected = str(row["item_id"])
        pos = pool.index(selected)
        candidates = [pool[(pos + offset) % len(pool)] for offset in range(CANDIDATES_PER_SLOT)]
        runtime.append({
            "slot_id": f"U05Q10-SLOT-{int(row['form_number']):02d}-{row['section']}{int(row['section_activity_ordinal']):02d}",
            "form_number": row["form_number"],
            "section": row["section"],
            "task_family_id": family,
            "candidate_ids": candidates,
            "selected_item_id": selected,
            "selection_policy": "DETERMINISTIC_SAME_TASK_FAMILY_THREE_CANDIDATES",
        })
    return runtime


def build_export_payload() -> dict[str, Any]:
    src = _sources()
    families = _families(src)
    rows = _q06_rows(src)
    bindings = _binding_map(src)
    scenes = _scene_map(src)

    used: set[str] = set()
    items: list[dict[str, Any]] = []
    family_occurrence: Counter[str] = Counter()

    for form_number in range(1, FORM_COUNT + 1):
        for section, section_name, count in SECTION_SPECS:
            pattern = PATTERNS[section]
            if len(pattern) != count:
                raise U05Q10BuildError(f"SECTION_PATTERN_DRIFT:{section}")
            for local, family_id in enumerate(pattern, start=1):
                occurrence = family_occurrence[family_id]
                source = _choose_source(rows, used, family_id, occurrence)
                family = families[family_id]
                function_id = _function_for(source, family, src, occurrence)
                qid = _q06_identity(source)
                binding = bindings.get(qid)
                scene = scenes.get(str(binding["scene_ref_id"])) if binding else None
                item = _item(
                    form_number,
                    section,
                    section_name,
                    local,
                    family_id,
                    family,
                    source,
                    function_id,
                    binding,
                    scene,
                    occurrence,
                )
                items.append(item)
                family_occurrence[family_id] += 1

    if len(items) != TOTAL_ITEMS or len(used) != TOTAL_ITEMS:
        raise U05Q10BuildError(f"ITEM_COUNT_DRIFT:{len(items)}:{len(used)}")

    forms: list[dict[str, Any]] = []
    for form_number in range(1, FORM_COUNT + 1):
        form_items = [row for row in items if row["form_number"] == form_number]
        forms.append({
            "form_id": f"U05-FORM-{form_number:02d}",
            "form_number": form_number,
            "progression_role": _stage(form_number),
            "question_count": len(form_items),
            "section_counts": dict(Counter(row["section"] for row in form_items)),
            "item_ids": [row["item_id"] for row in form_items],
        })

    runtime = _runtime(items)
    family_counts = Counter(row["task_family_id"] for row in items)
    function_counts = Counter(row["communicative_function_id"] for row in items)
    frame_counts = Counter(row["frame_id"] for row in items)
    subject_counts = Counter(row["subject_class"] for row in items)
    polarity_counts = Counter(row["polarity"] for row in items)
    variant_counts = Counter(row["surface_variant"] for row in items)
    complement_counts = Counter(_frame_base(str(row["frame_id"])) for row in items)
    context_count = sum(1 for row in items if row["requires_context_binding"])
    scene_bound_count = sum(1 for row in items if row["scene_ref_id"] is not None)

    all_functions = {row["function_id"] for row in src["q08"]["communicative_functions"]}
    all_frames = set(src["q08"]["frame_function_compatibility"])
    all_subjects = set(src["q06"]["coverage"]["subject_class_counts"])

    coverage = {
        "questionbank_item_count": len(items),
        "form_count": len(forms),
        "task_family_coverage": f"{len(family_counts)}/10",
        "communicative_function_coverage": f"{len(function_counts)}/7",
        "frame_coverage": f"{len(frame_counts)}/6",
        "subject_class_coverage": f"{len(subject_counts)}/9",
        "polarity_coverage": f"{len(polarity_counts)}/2",
        "complement_class_coverage": f"{len(complement_counts)}/3",
        "surface_variant_coverage": {
            "full_count": variant_counts.get("FULL", 0),
            "contracted_count": variant_counts.get("CONTRACTED", 0),
            "contracted_alt_count": variant_counts.get("CONTRACTED_ALT", 0),
            "surface_variant_is_new_semantics": False,
        },
        "task_family_counts": dict(sorted(family_counts.items())),
        "communicative_function_counts": dict(sorted(function_counts.items())),
        "frame_counts": dict(sorted(frame_counts.items())),
        "subject_class_counts": dict(sorted(subject_counts.items())),
        "polarity_counts": dict(sorted(polarity_counts.items())),
        "complement_class_counts": dict(sorted(complement_counts.items())),
        "context_required_item_count": context_count,
        "scene_bound_item_count": scene_bound_count,
        "context_required_unbound_item_count": sum(
            1 for row in items if row["requires_context_binding"] and row["scene_ref_id"] is None
        ),
        "standalone_item_forced_scene_count": sum(
            1 for row in items if not row["requires_context_binding"] and row["scene_ref_id"] is not None
        ),
        "unique_item_id_count": len({row["item_id"] for row in items}),
        "unique_item_semantic_signature_count": len({row["item_semantic_signature"] for row in items}),
        "unique_q06_source_identity_count": len({row["q06_identity"] for row in items}),
        "unique_semantic_proposition_count": len({row["semantic_proposition_key"] for row in items}),
        "expected_function_ids": sorted(all_functions),
        "expected_frame_ids": sorted(all_frames),
        "expected_subject_classes": sorted(all_subjects),
    }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "artifact_id": "A1FS-V1-U05Q10_QuestionBankAndFormMaterialization",
        "status": PASS_STATUS,
        "unit_number": 5,
        "unit_id": UNIT_ID,
        "authority_role": "Q10_MATERIALIZED_QUESTIONBANK_AND_FORM_AUTHORITY",
        "authority_refs": {
            "q06": "ulga/contracts/a1fs_v1_u05_q06_sentence_assets.json",
            "q07": "ulga/contracts/a1fs_v1_u05_q07_life_skill_micro_scenes.json",
            "q08": "ulga/contracts/a1fs_v1_u05_q08_communicative_function_authority.json",
            "q09": "ulga/contracts/a1fs_v1_u05_q09_task_pedagogical_contract.json",
            "source_main_sha": "779db81f560471ca31e3c2dc01e404ab927838a9",
        },
        "materialization_contract": {
            "form_count": FORM_COUNT,
            "questions_per_form": QUESTIONS_PER_FORM,
            "questionbank_item_count": TOTAL_ITEMS,
            "runtime_occurrence_count": TOTAL_ITEMS,
            "candidate_count_per_slot": CANDIDATES_PER_SLOT,
            "section_counts_per_form": SECTION_COUNTS,
            "task_family_count": 10,
            "communicative_function_count": 7,
            "frame_count": 6,
            "subject_class_count": 9,
            "polarity_count": 2,
            "complement_class_count": 3,
            "progression_roles": list(STAGE_BY_FORMS),
            "full_and_contracted_are_surface_variants_not_new_semantics": True,
        },
        "questionbank_items": items,
        "forms": forms,
        "runtime_bindings": runtime,
        "coverage": coverage,
        "boundaries": {
            "q06_sentence_semantics_modified": False,
            "q07_scene_semantics_modified": False,
            "q08_communicative_function_semantics_modified": False,
            "q09_task_family_inventory_modified": False,
            "new_grammar_authority_created": False,
            "new_vocabulary_identity_created": False,
            "new_sentence_identity_created": False,
            "new_scene_identity_created": False,
            "new_communicative_function_identity_created": False,
            "unit05_current360_materialized": False,
            "unit05_spoken360_materialized": False,
            "unit05_pattern360_materialized": False,
            "be_interrogative_mastery_activated": False,
            "past_be_activated": False,
            "existential_there_be_activated": False,
            "present_continuous_mastery_activated": False,
            "a2_a2plus_unlocked": False,
        },
        "integrity": {
            "questionbank_digest": _digest(items),
            "forms_digest": _digest(forms),
            "runtime_digest": _digest(runtime),
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
            "q06_task_id": q06_builder.TASK_ID,
            "q07_task_id": q07_builder.TASK_ID,
            "q08_path": str(Q08.relative_to(ROOT)).replace("\\", "/"),
            "q09_path": str(Q09.relative_to(ROOT)).replace("\\", "/"),
            "questionbank_item_count": TOTAL_ITEMS,
            "form_count": FORM_COUNT,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u05q10_questionbank_form_materialization as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def main() -> int:
    from ulga.validators import validate_a1fs_v1_u05q10_questionbank_form_materialization as validator

    candidate = build_candidate()
    approved = admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    payload = approved["payload"]
    print(f"STATUS={payload['status']}")
    print(f"QUESTIONBANK_ITEMS={payload['coverage']['questionbank_item_count']}")
    print(f"FORMS={payload['coverage']['form_count']}")
    print(f"TASK_FAMILIES={payload['coverage']['task_family_coverage']}")
    print(f"FUNCTIONS={payload['coverage']['communicative_function_coverage']}")
    print(f"FRAMES={payload['coverage']['frame_coverage']}")
    print(f"SUBJECT_CLASSES={payload['coverage']['subject_class_coverage']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEXT_SHORT_STEP={payload['next_short_step']}")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
