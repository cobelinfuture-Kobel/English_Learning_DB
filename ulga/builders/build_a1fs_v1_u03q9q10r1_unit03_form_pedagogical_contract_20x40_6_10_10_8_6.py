#!/usr/bin/env python3
"""Unit03 Q9/Q10 successor: 20 Forms x 40 with A/B/C/D/E pedagogy.

Historical Unit03 Q10 16x40=640 and U03SCFV2 20x40=800 remain immutable
provenance. This builder creates a new successor runtime identity.
Q1-Q4/Q7/Q8 stay read-only, Q5 is verify-only, and Q6 is not regenerated.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u03scfv2_unit03_sentence_competence_forms_v2_800_materialization
    as historical_u03scfv2,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U03Q9Q10R1_Unit03FormPedagogicalContract20x40_6_10_10_8_6"
SCHEMA_VERSION = "a1fs.v1.u03q9q10r1.form_pedagogical_contract_20x40.v1"
PASS_STATUS = "PASS_A1FS_V1_U03Q9Q10R1_FORM_PEDAGOGICAL_CONTRACT_20X40"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-27:U03_Q9_Q10_SUCCESSOR_20X40_6_10_10_8_6"
NEXT_SHORT_STEP = "A1FS-V1-U03Q9Q10R1R1_Unit03SuccessorTwentyFormLearnerFacingAcceptance"
UNIT_ID = "GRAMMAR_SUBJECT_PRONOUNS"
FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_RUNTIME = 800
CANDIDATES_PER_SLOT = 3
Q6_ADMITTED_SENTENCE_ASSET_COUNT = 18983
HISTORICAL_Q9_SHA256 = "cef451a660982542c7d60d3c48b11a12f26ecdf9034662b221280b0caf6d9838"
HISTORICAL_Q10_SHA256 = "2ec55d6eec1933396e1c732fb43c0c83647ddb2ccb7a01bcab03733d8d3c5109"
HISTORICAL_Q10_RUNTIME = 640
HISTORICAL_SCFV2_RUNTIME = 800
Q9_FAMILIES = (
    "RECOGNITION", "MEANING_DISCRIMINATION", "FORM_SELECTION",
    "MORPHOLOGY_CONSTRUCTION", "ERROR_DETECTION", "ERROR_CORRECTION",
    "CONTEXT_GAP", "U01_U02_INTEGRATION", "PRODUCTIVE_RESPONSE", "TRANSFER",
)
SECTION_SPECS = (
    ("A", "PRONOUN_FOUNDATION", 6),
    ("B", "COMPLETE_SENTENCE_OPERATION", 10),
    ("C", "U01_U02_U03_INTEGRATION", 10),
    ("D", "INTERSENTENTIAL_REFERENCE", 8),
    ("E", "CONNECTED_PASSAGE_READING", 6),
)
SECTION_COUNTS = {key: count for key, _, count in SECTION_SPECS}
FAMILY_SECTION_MAPPING = {
    "RECOGNITION": ["A"],
    "MEANING_DISCRIMINATION": ["A", "D", "E"],
    "FORM_SELECTION": ["A", "B", "E"],
    "MORPHOLOGY_CONSTRUCTION": ["B"],
    "ERROR_DETECTION": ["B", "D", "E"],
    "ERROR_CORRECTION": ["B", "D"],
    "CONTEXT_GAP": ["B", "D", "E"],
    "U01_U02_INTEGRATION": ["C", "E"],
    "PRODUCTIVE_RESPONSE": ["B", "D"],
    "TRANSFER": ["D", "E"],
}
CONNECTED_PASSAGE_TYPES = (
    ("connected_passage_pronoun_reference", "MEANING_DISCRIMINATION"),
    ("connected_passage_fact_retrieval", "TRANSFER"),
    ("connected_passage_sentence_meaning", "MEANING_DISCRIMINATION"),
    ("connected_passage_article_reference", "U01_U02_INTEGRATION"),
    ("connected_passage_true_false", "ERROR_DETECTION"),
    ("connected_passage_sentence_completion", "CONTEXT_GAP"),
)
STAGE_BY_FORMS = {
    "GUIDED": [1, 2, 3, 4],
    "REDUCED_SUPPORT": [5, 6, 7, 8],
    "INDEPENDENT": [9, 10, 11, 12],
    "TRANSFER": [13, 14, 15, 16],
    "RETENTION": [17, 18, 19, 20],
}
PASSAGE_SENTENCE_COUNT_BY_STAGE = {
    "GUIDED": 2, "REDUCED_SUPPORT": 3, "INDEPENDENT": 4,
    "TRANSFER": 5, "RETENTION": 5,
}
PRONOUNS = ("I", "You", "He", "She", "It", "We", "They")
PASSAGE_PRONOUNS = ("He", "She", "It")
B_REQUIRED_EVIDENCE = {"sentence_manipulation", "sentence_correction", "sentence_production"}
C_TARGETS = {"ARTICLE", "PLURALITY", "SUBJECT_PRONOUN"}


class U03Q9Q10R1BuildError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _article(noun: str) -> str:
    return "an" if noun[:1].casefold() in {"a", "e", "i", "o", "u"} else "a"


def _stage(form_number: int) -> str:
    for stage, forms in STAGE_BY_FORMS.items():
        if form_number in forms:
            return stage
    raise U03Q9Q10R1BuildError(f"FORM_STAGE_MISSING:{form_number}")


def _have(pronoun: str) -> str:
    return "has" if pronoun in {"He", "She", "It"} else "have"


def _like(pronoun: str) -> str:
    return "likes" if pronoun in {"He", "She", "It"} else "like"


def _pronoun_context(pronoun: str, singular: str, plural: str) -> tuple[str, str]:
    art = _article(singular)
    if pronoun == "I":
        return f'Mia says, "I have {art} {singular}."', "Mia (the speaker)"
    if pronoun == "You":
        return f'Mia says to Ben, "You have {art} {singular}."', "Ben (the listener)"
    if pronoun == "He":
        return f"Ben has {art} {singular}.", "Ben"
    if pronoun == "She":
        return f"Mia has {art} {singular}.", "Mia"
    if pronoun == "It":
        return f"This is {art} {singular}.", f"the {singular}"
    if pronoun == "We":
        return f'Mia says, "Ben and I have two {plural}."', "Mia and Ben (including the speaker)"
    if pronoun == "They":
        return f"Ben and Mia have two {plural}.", "Ben and Mia"
    raise U03Q9Q10R1BuildError(f"UNKNOWN_PRONOUN:{pronoun}")


@lru_cache(maxsize=1)
def _historical_source() -> dict[str, Any]:
    payload = historical_u03scfv2.build_export_payload()
    if payload.get("status") != historical_u03scfv2.PASS_STATUS:
        raise U03Q9Q10R1BuildError("HISTORICAL_SCFV2_STATUS_DRIFT")
    contract = payload.get("runtime_form_contract") or {}
    if int(contract.get("form_count", -1)) != 20 or int(contract.get("runtime_occurrence_count", -1)) != 800:
        raise U03Q9Q10R1BuildError("HISTORICAL_SCFV2_RUNTIME_DRIFT")
    return payload


def _lexical_witnesses() -> list[dict[str, str]]:
    assets = list((_historical_source().get("sentence_asset_delta") or {}).get("assets") or [])
    found: dict[tuple[str, str], dict[str, str]] = {}
    for row in assets:
        singular = str(row.get("singular") or "").strip().casefold()
        plural = str(row.get("plural") or "").strip().casefold()
        sentence_id = str(row.get("sentence_id") or "").strip()
        if singular and plural and sentence_id:
            found.setdefault((singular, plural), {
                "singular": singular, "plural": plural,
                "source_sentence_asset_id": sentence_id,
            })
    rows = [found[key] for key in sorted(found)]
    if len(rows) < 8:
        raise U03Q9Q10R1BuildError(f"LEXICAL_WITNESS_POOL_TOO_SHALLOW:{len(rows)}")
    return rows


def _response_contract(correct: str, *, response_type: str = "string") -> dict[str, Any]:
    return {
        "scoring_mode": "NORMALIZED_TEXT" if response_type == "string" else "EXACT_OPTION",
        "response_type": response_type, "accepted_texts": [correct],
        "capture_enabled": True, "human_review_fallback": False,
    }


def _item(*, form_number: int, section: str, section_name: str, local_ordinal: int,
          task_family: str, question_type: str, skill: str, stimulus: str,
          prompt: str, correct_answer: str, options: Sequence[str] = (),
          evidence: Sequence[str] = (), grammar_targets: Sequence[str] = ("SUBJECT_PRONOUN",),
          primary_target: str = "SUBJECT_PRONOUN", secondary_targets: Sequence[str] = (),
          source_sentence_asset_ids: Sequence[str] = (), connected_passage: bool = False,
          passage_id: str | None = None, passage_sentences: Sequence[str] = (),
          passage_unseen: bool = False) -> dict[str, Any]:
    if task_family not in Q9_FAMILIES:
        raise U03Q9Q10R1BuildError(f"UNKNOWN_TASK_FAMILY:{task_family}")
    core = {
        "form_number": form_number, "section": section, "local_ordinal": local_ordinal,
        "task_family": task_family, "question_type": question_type,
        "stimulus": stimulus, "prompt": prompt, "correct_answer": correct_answer,
    }
    signature = _digest(core)
    item_id = f"U03Q10R1-F{form_number:02d}-{section}{local_ordinal:02d}-{task_family[:6]}-{signature[:10].upper()}"
    return {
        "item_id": item_id, "unit_id": UNIT_ID, "form_number": form_number,
        "progression_stage": _stage(form_number), "section": section,
        "section_name": section_name, "section_activity_ordinal": local_ordinal,
        "task_family": task_family, "question_type": question_type, "skill": skill,
        "stimulus": stimulus, "prompt": prompt, "options": list(options),
        "correct_answer": correct_answer, "accepted_answers": [correct_answer],
        "response_contract": _response_contract(correct_answer, response_type="option" if options else "string"),
        "pedagogical_evidence": sorted(set(evidence)),
        "grammar_targets": sorted(set(grammar_targets)), "primary_target": primary_target,
        "secondary_targets": sorted(set(secondary_targets)),
        "source_sentence_asset_ids": list(source_sentence_asset_ids),
        "q6_binding_status": "READ_ONLY_SOURCE_WITNESS" if source_sentence_asset_ids else "NOT_REQUIRED",
        "q6_sentence_asset_created": False, "connected_passage": connected_passage,
        "passage_id": passage_id, "passage_sentences": list(passage_sentences),
        "passage_sentence_count": len(passage_sentences), "passage_unseen": passage_unseen,
        "semantic_signature": signature, "learner_visible_capable": True,
        "assessment_eligible": True,
    }


def _build_section_a(form_number: int, lex: Mapping[str, str]) -> list[dict[str, Any]]:
    singular, plural, sid = str(lex["singular"]), str(lex["plural"]), str(lex["source_sentence_asset_id"])
    pronoun = PRONOUNS[(form_number - 1) % len(PRONOUNS)]
    antecedent, referent = _pronoun_context(pronoun, singular, plural)
    specs = [
        ("RECOGNITION", "pronoun_recognition_choice", f"{pronoun} {_have(pronoun)} two {plural}.", "Which word is the subject pronoun?", pronoun, [pronoun, singular, "two", _have(pronoun)]),
        ("MEANING_DISCRIMINATION", "referent_choice", f"{antecedent} {pronoun} {_have(pronoun)} two {plural}.", f"Who or what does {pronoun} refer to?", referent, [referent, "Ben", "Mia", f"the {singular}"]),
        ("FORM_SELECTION", "pronoun_form_choice", antecedent, "Choose the subject pronoun that continues the reference.", pronoun, list(PRONOUNS)),
        ("RECOGNITION", "pronoun_recognition_choice", f"Today, {pronoun} {_like(pronoun)} the {singular}.", "Choose the subject pronoun.", pronoun, [pronoun, "the", singular, "Today"]),
        ("MEANING_DISCRIMINATION", "pronoun_context_choice", antecedent, "Which subject pronoun matches this context?", pronoun, list(PRONOUNS)),
        ("FORM_SELECTION", "pronoun_form_choice", f"___ {_have(pronoun)} two {plural}.", "Choose the correct subject pronoun.", pronoun, list(PRONOUNS)),
    ]
    return [_item(form_number=form_number, section="A", section_name="PRONOUN_FOUNDATION",
                  local_ordinal=i, task_family=f, question_type=q, skill="READING",
                  stimulus=s, prompt=p, correct_answer=a, options=o,
                  evidence=["pronoun_foundation"], source_sentence_asset_ids=[sid])
            for i, (f, q, s, p, a, o) in enumerate(specs, start=1)]


def _build_section_b(form_number: int, lex: Mapping[str, str]) -> list[dict[str, Any]]:
    singular, plural, sid = str(lex["singular"]), str(lex["plural"]), str(lex["source_sentence_asset_id"])
    pronoun = PRONOUNS[(form_number + 1) % len(PRONOUNS)]
    have, article = _have(pronoun), _article(singular)
    cp, cs = f"{pronoun} {have} two {plural}.", f"{pronoun} {have} {article} {singular}."
    specs = [
        ("FORM_SELECTION", "complete_sentence_selection", f"Target meaning: {pronoun} owns two {plural}.", "Choose the complete sentence.", cp, [cp, f"{pronoun} {have} two {singular}.", f"They has two {plural}."], ["sentence_manipulation"]),
        ("MORPHOLOGY_CONSTRUCTION", "structured_morphology_build", f"base noun: {singular} | plural marker: s | sentence subject: {pronoun}", "Build the plural noun, then write the complete sentence.", cp, [], ["sentence_manipulation"]),
        ("ERROR_DETECTION", "sentence_error_detection", f"{pronoun} {have} two {singular}.", "Find the number/plural error in the sentence.", singular, [], ["sentence_manipulation"]),
        ("ERROR_CORRECTION", "sentence_error_correction", f"{pronoun} {have} {article} {plural}.", "Correct the sentence.", cs, [], ["sentence_correction"]),
        ("PRODUCTIVE_RESPONSE", "guided_sentence_production", f"Context: {pronoun} + two {plural}", "Write the complete sentence.", cp, [], ["sentence_production"]),
        ("CONTEXT_GAP", "sentence_gap_fill", f"{pronoun} {have} two ___.", "Complete the sentence with the plural noun.", plural, [], ["sentence_manipulation"]),
        ("FORM_SELECTION", "article_number_sentence_selection", f"Target: one {singular}", "Choose the complete sentence.", cs, [cs, f"{pronoun} {have} two {singular}.", f"{pronoun} {have} {article} {plural}."], ["sentence_manipulation"]),
        ("ERROR_CORRECTION", "article_plural_sentence_correction", f"{pronoun} {have} a {plural}.", "Rewrite the sentence correctly.", cs, [], ["sentence_correction"]),
        ("PRODUCTIVE_RESPONSE", "sentence_rewrite_production", cs, "Rewrite the sentence so the subject has two of the noun.", cp, [], ["sentence_production", "sentence_manipulation"]),
        ("MORPHOLOGY_CONSTRUCTION", "structured_morphology_build", f"{singular} + s → {plural} | {pronoun} | two", "Use the built plural form in a complete sentence.", cp, [], ["sentence_manipulation"]),
    ]
    return [_item(form_number=form_number, section="B", section_name="COMPLETE_SENTENCE_OPERATION",
                  local_ordinal=i, task_family=f, question_type=q,
                  skill="READING" if o else "WRITING", stimulus=s, prompt=p,
                  correct_answer=a, options=o, evidence=e,
                  grammar_targets=["SUBJECT_PRONOUN", "PLURALITY", "ARTICLE"],
                  secondary_targets=["PLURALITY", "ARTICLE"], source_sentence_asset_ids=[sid])
            for i, (f, q, s, p, a, o, e) in enumerate(specs, start=1)]


def _build_section_c(form_number: int, lex: Mapping[str, str], lex2: Mapping[str, str]) -> list[dict[str, Any]]:
    plural, singular, singular2 = str(lex["plural"]), str(lex["singular"]), str(lex2["singular"])
    sid1, sid2 = str(lex["source_sentence_asset_id"]), str(lex2["source_sentence_asset_id"])
    pronoun = PRONOUNS[(form_number + 3) % len(PRONOUNS)]
    have, article2 = _have(pronoun), _article(singular2)
    correct = f"{pronoun} {have} two {plural} and {article2} {singular2}."
    wrong_plural = f"{pronoun} {have} two {singular} and {article2} {singular2}."
    wrong_article = f"{pronoun} {have} two {plural} and {'a' if article2 == 'an' else 'an'} {singular2}."
    wrong_agreement = f"{pronoun} {'has' if have == 'have' else 'have'} two {plural} and {article2} {singular2}."
    qtypes = ("cumulative_complete_sentence_choice", "cumulative_error_detection",
              "cumulative_error_correction", "cumulative_gap_fill", "cumulative_sentence_rewrite")
    rows = []
    for i in range(1, 11):
        qtype = qtypes[(i - 1) % len(qtypes)]
        if qtype == "cumulative_complete_sentence_choice":
            s, p, a, o = "Choose one complete cumulative sentence.", "Which sentence is correct?", correct, [correct, wrong_plural, wrong_article, wrong_agreement]
        elif qtype == "cumulative_error_detection":
            s, p, a, o = wrong_plural, "Which part breaks number/plural agreement?", singular, []
        elif qtype == "cumulative_error_correction":
            s, p, a, o = wrong_article, "Correct the whole sentence.", correct, []
        elif qtype == "cumulative_gap_fill":
            s, p, a, o = f"{pronoun} {have} two {plural} and ___ {singular2}.", "Complete the article so the sentence is correct.", article2, []
        else:
            s, p, a, o = f"Target meaning: {pronoun} owns two {plural} plus one {singular2}.", "Write one complete sentence using the subject pronoun, plural noun, and article.", correct, []
        row = _item(form_number=form_number, section="C", section_name="U01_U02_U03_INTEGRATION",
                    local_ordinal=i, task_family="U01_U02_INTEGRATION", question_type=qtype,
                    skill="READING" if o else "WRITING", stimulus=s, prompt=p, correct_answer=a,
                    options=o, evidence=["same_item_u01_u02_u03_integration"],
                    grammar_targets=sorted(C_TARGETS), primary_target="SUBJECT_PRONOUN",
                    secondary_targets=["ARTICLE", "PLURALITY"], source_sentence_asset_ids=[sid1, sid2])
        row["integration_proof"] = {
            "same_question_contains_u01_article": True,
            "same_question_contains_u02_number_plural": True,
            "same_question_contains_u03_subject_pronoun": True,
            "alternating_separate_questions_only": False,
        }
        rows.append(row)
    return rows


def _build_section_d(form_number: int, lex: Mapping[str, str]) -> list[dict[str, Any]]:
    singular, plural, sid = str(lex["singular"]), str(lex["plural"]), str(lex["source_sentence_asset_id"])
    subject = "Mia" if form_number % 2 == 0 else "Ben"
    pronoun = "She" if subject == "Mia" else "He"
    wrong = "He" if pronoun == "She" else "She"
    context = f"There is {_article(singular)} {singular} near {subject}. {pronoun} has two {plural}."
    specs = [
        ("MEANING_DISCRIMINATION", "two_sentence_pronoun_reference", f"{subject} has {_article(singular)} {singular}. {pronoun} likes it.", f"Who does {pronoun} refer to?", subject, [subject, f"the {singular}", "Ben", "Mia"]),
        ("MEANING_DISCRIMINATION", "two_sentence_object_reference", f"{subject} has {_article(singular)} {singular}. It is new.", "What does It refer to?", f"the {singular}", [f"the {singular}", subject, "the room"]),
        ("CONTEXT_GAP", "reference_chain_gap_fill", f"{subject} is here. ___ has two {plural}.", "Complete the second sentence with the correct subject pronoun.", pronoun, list(PRONOUNS)),
        ("CONTEXT_GAP", "reference_chain_gap_fill", f"There is {_article(singular)} {singular}. ___ is new.", "Complete the reference chain.", "It", list(PRONOUNS)),
        ("ERROR_DETECTION", "reference_chain_error_detection", f"{subject} is here. {wrong} has two {plural}.", "Find the wrong subject pronoun.", wrong, []),
        ("ERROR_CORRECTION", "reference_chain_correction", f"{subject} is here. {wrong} has two {plural}.", "Correct the second sentence.", f"{pronoun} has two {plural}.", []),
        ("PRODUCTIVE_RESPONSE", "connected_reference_writing", f"{subject} is here. / two {plural}", "Write the next sentence with the correct subject pronoun.", f"{pronoun} has two {plural}.", []),
        ("TRANSFER", "unseen_reference_transfer", context, "In this new two-sentence context, choose the pronoun that keeps the reference coherent.", pronoun, list(PRONOUNS)),
    ]
    return [_item(form_number=form_number, section="D", section_name="INTERSENTENTIAL_REFERENCE",
                  local_ordinal=i, task_family=f, question_type=q,
                  skill="READING" if o else "WRITING", stimulus=s, prompt=p,
                  correct_answer=a, options=o, evidence=["noun_to_pronoun_reference_chain"],
                  grammar_targets=["SUBJECT_PRONOUN", "REFERENCE_TRACKING"],
                  source_sentence_asset_ids=[sid],
                  passage_unseen=_stage(form_number) in {"TRANSFER", "RETENTION"})
            for i, (f, q, s, p, a, o) in enumerate(specs, start=1)]


def _passage(form_number: int, lex: Mapping[str, str]) -> dict[str, Any]:
    singular, plural = str(lex["singular"]), str(lex["plural"])
    pronoun = PASSAGE_PRONOUNS[(form_number - 1) % len(PASSAGE_PRONOUNS)]
    if pronoun == "He":
        intro, referent = "Ben is a boy.", "Ben"
    elif pronoun == "She":
        intro, referent = "Mia is a girl.", "Mia"
    else:
        intro, referent = "A robot is in the room.", "the robot"
    sentences = [
        intro, f"{pronoun} {_have(pronoun)} two {plural}.",
        f"The {plural} are on a desk.", f"{pronoun} {_like(pronoun)} the red {singular}.",
        "They are new.",
    ]
    stage = _stage(form_number)
    count = PASSAGE_SENTENCE_COUNT_BY_STAGE[stage]
    selected = sentences[:count]
    return {
        "passage_id": f"U03Q10R1-PASSAGE-F{form_number:02d}", "sentences": selected,
        "text": " ".join(selected), "sentence_count": count, "pronoun": pronoun,
        "referent": referent, "singular": singular, "plural": plural,
        "unseen": stage in {"TRANSFER", "RETENTION"}, "mixed_cumulative": stage == "RETENTION",
    }


def _build_section_e(form_number: int, lex: Mapping[str, str]) -> list[dict[str, Any]]:
    sid = str(lex["source_sentence_asset_id"])
    passage = _passage(form_number, lex)
    ptext, pronoun, referent = str(passage["text"]), str(passage["pronoun"]), str(passage["referent"])
    singular, plural = str(passage["singular"]), str(passage["plural"])
    if int(passage["sentence_count"]) >= 3:
        article_prompt, article_answer = f'What does "the {plural}" refer to?', f"the two {plural}"
    else:
        article_prompt, article_answer = "Which article introduces the person or thing in the first sentence?", "a"
    specs = [
        (CONNECTED_PASSAGE_TYPES[0], f"Who or what does {pronoun} refer to?", referent, [referent, f"the {singular}", "the desk"]),
        (CONNECTED_PASSAGE_TYPES[1], f"How many {plural} does the main referent have?", "two", ["one", "two", "three"]),
        (CONNECTED_PASSAGE_TYPES[2], "Which statement matches the passage?", f"{pronoun} {_have(pronoun)} two {plural}.", [f"{pronoun} {_have(pronoun)} two {plural}.", f"{pronoun} {_have(pronoun)} one {singular}."]),
        (CONNECTED_PASSAGE_TYPES[3], article_prompt, article_answer, []),
        (CONNECTED_PASSAGE_TYPES[4], f"True or false: the main referent has one {singular}.", "false", ["true", "false"]),
        (CONNECTED_PASSAGE_TYPES[5], f"Complete from the passage: {pronoun} {_have(pronoun)} ___ {plural}.", "two", []),
    ]
    rows = []
    for i, ((qtype, family), prompt, answer, options) in enumerate(specs, start=1):
        rows.append(_item(
            form_number=form_number, section="E", section_name="CONNECTED_PASSAGE_READING",
            local_ordinal=i, task_family=family, question_type=qtype, skill="READING",
            stimulus=ptext, prompt=prompt, correct_answer=answer, options=options,
            evidence=["connected_passage_comprehension"],
            grammar_targets=["ARTICLE", "PLURALITY", "SUBJECT_PRONOUN", "REFERENCE_TRACKING"],
            primary_target="REFERENCE_TRACKING", secondary_targets=["ARTICLE", "PLURALITY", "SUBJECT_PRONOUN"],
            source_sentence_asset_ids=[sid], connected_passage=True,
            passage_id=str(passage["passage_id"]), passage_sentences=list(passage["sentences"]),
            passage_unseen=bool(passage["unseen"])))
    return rows


def _questionbank_items() -> list[dict[str, Any]]:
    lex = _lexical_witnesses()
    rows: list[dict[str, Any]] = []
    for form_number in range(1, FORM_COUNT + 1):
        lex1 = lex[(form_number - 1) % len(lex)]
        lex2 = lex[(form_number + 2) % len(lex)]
        rows.extend(_build_section_a(form_number, lex1))
        rows.extend(_build_section_b(form_number, lex1))
        rows.extend(_build_section_c(form_number, lex1, lex2))
        rows.extend(_build_section_d(form_number, lex1))
        rows.extend(_build_section_e(form_number, lex1))
    if len(rows) != TOTAL_RUNTIME:
        raise U03Q9Q10R1BuildError(f"QUESTIONBANK_ITEM_COUNT_INVALID:{len(rows)}")
    if len({row["item_id"] for row in rows}) != TOTAL_RUNTIME:
        raise U03Q9Q10R1BuildError("QUESTIONBANK_ITEM_ID_COLLISION")
    return rows


def _runtime_bindings(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[str]] = defaultdict(list)
    for row in items:
        by_family[str(row["task_family"])].append(str(row["item_id"]))
    missing = [family for family in Q9_FAMILIES if not by_family[family]]
    if missing:
        raise U03Q9Q10R1BuildError(f"Q9_FAMILY_RUNTIME_GAP:{missing}")
    runtime = []
    for row in items:
        family = str(row["task_family"])
        pool = by_family[family]
        selected_id = str(row["item_id"])
        pos = pool.index(selected_id)
        candidates = [pool[(pos + offset) % len(pool)] for offset in range(CANDIDATES_PER_SLOT)]
        if len(set(candidates)) != CANDIDATES_PER_SLOT:
            raise U03Q9Q10R1BuildError(f"CANDIDATE_POOL_TOO_SHALLOW:{family}")
        runtime.append({
            "runtime_occurrence_id": f"U03Q10R1-R{len(runtime)+1:03d}::{selected_id}",
            "slot_id": f"U03Q10R1-F{int(row['form_number']):02d}-{row['section']}{int(row['section_activity_ordinal']):02d}",
            "form_number": int(row["form_number"]), "progression_stage": str(row["progression_stage"]),
            "section": str(row["section"]), "task_family": family,
            "question_type": str(row["question_type"]), "selected_item_id": selected_id,
            "candidate_ids": candidates,
            "runtime_selection_rule": "SUCCESSOR_POLICY_BOUND_FIRST_OF_THREE_SAME_FAMILY",
            "source_identity": "U03Q9Q10R1_SUCCESSOR",
        })
    if len(runtime) != TOTAL_RUNTIME or len({row["selected_item_id"] for row in runtime}) != TOTAL_RUNTIME:
        raise U03Q9Q10R1BuildError("SUCCESSOR_RUNTIME_DISTINCTNESS_INVALID")
    return runtime


def build_export_payload() -> dict[str, Any]:
    source = _historical_source()
    items = _questionbank_items()
    runtime = _runtime_bindings(items)
    family_counts = Counter(str(row["task_family"]) for row in items)
    section_counts = Counter(str(row["section"]) for row in items)
    stage_counts = Counter(str(row["progression_stage"]) for row in items)
    passage_rows = [row for row in items if bool(row.get("connected_passage"))]
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "program_id": PROGRAM_ID, "task_id": TASK_ID,
        "status": PASS_STATUS, "unit_id": UNIT_ID,
        "scope_lock": {
            "q1_q4": "KEEP", "q5": "VERIFY_ONLY", "q6": "KEEP_NO_REGENERATION",
            "q7": "KEEP", "q8": "KEEP", "q9": "AMEND",
            "q10": "SUCCESSOR_REVISION_REMATERIALIZE", "pdf_pagination": "OUT_OF_SCOPE",
            "pdf_renderer": "OUT_OF_SCOPE", "q11": "OUT_OF_SCOPE",
            "unit04": "OUT_OF_SCOPE", "a2": "LOCKED",
        },
        "historical_provenance": {
            "unit03_q9_sha256": HISTORICAL_Q9_SHA256,
            "unit03_q10_16x40_sha256": HISTORICAL_Q10_SHA256,
            "unit03_q10_historical_runtime_count": HISTORICAL_Q10_RUNTIME,
            "unit03_q10_historical_identity_mutated": False,
            "u03scfv2_task_id": historical_u03scfv2.TASK_ID,
            "u03scfv2_status": source["status"],
            "u03scfv2_historical_runtime_count": HISTORICAL_SCFV2_RUNTIME,
            "u03scfv2_historical_identity_mutated": False,
            "successor_runtime_identity_is_new": True,
        },
        "q9_amendment": {
            "task_family_count": len(Q9_FAMILIES), "task_families": list(Q9_FAMILIES),
            "family_11_created": False, "section_mapping": FAMILY_SECTION_MAPPING,
            "connected_passage_question_types": [
                {"question_type": qtype, "task_family": family}
                for qtype, family in CONNECTED_PASSAGE_TYPES
            ],
        },
        "q10_successor_form_contract": {
            "materialization_identity": "U03Q10R1_SUCCESSOR_20X40_6_10_10_8_6",
            "form_count": FORM_COUNT, "activities_per_form": ACTIVITIES_PER_FORM,
            "runtime_occurrence_count": TOTAL_RUNTIME, "candidate_count_per_slot": CANDIDATES_PER_SLOT,
            "section_counts_per_form": SECTION_COUNTS, "global_section_counts": dict(section_counts),
            "global_family_counts": dict(family_counts), "global_stage_counts": dict(stage_counts),
            "selected_item_identity_count": len({row["selected_item_id"] for row in runtime}),
            "global_800_distinct_selected_item_proof": True,
        },
        "progression_contract": {
            "forms_by_stage": STAGE_BY_FORMS,
            "passage_sentence_count_by_stage": PASSAGE_SENTENCE_COUNT_BY_STAGE,
            "guided_forms_01_04": "2_SENTENCE_MINI_CONTEXT",
            "reduced_support_forms_05_08": "3_SENTENCE_PASSAGE",
            "independent_forms_09_12": "4_SENTENCE_PASSAGE",
            "transfer_forms_13_16": "5_SENTENCE_UNSEEN_PASSAGE",
            "retention_forms_17_20": "5_SENTENCE_MIXED_UNSEEN_CUMULATIVE_PASSAGE",
        },
        "pedagogical_proofs": {
            "section_b_required_evidence": sorted(B_REQUIRED_EVIDENCE),
            "section_c_same_item_targets": sorted(C_TARGETS),
            "section_c_not_alternating_separate_question_claim": True,
            "section_e_connected_passage_questions_per_form": 6,
            "section_e_connected_passage_question_count": len(passage_rows),
            "section_e_question_types": [qtype for qtype, _ in CONNECTED_PASSAGE_TYPES],
        },
        "q6_preservation": {
            "historical_unit03_admitted_sentence_asset_count": Q6_ADMITTED_SENTENCE_ASSET_COUNT,
            "successor_sentence_assets_created": 0, "q6_regenerated": False,
            "q6_mutated": False, "read_only_sentence_witness_source": historical_u03scfv2.TASK_ID,
        },
        "successor_questionbank_items": items, "runtime_bindings": runtime,
        "claim_boundaries": {
            "q1_q4_mutated": False, "q5_mutated": False, "q6_regenerated": False,
            "q6_mutated": False, "q7_mutated": False, "q8_mutated": False,
            "historical_q10_runtime_mutated": False,
            "historical_u03scfv2_runtime_mutated": False, "family_11_created": False,
            "pdf_pagination_modified": False, "pdf_renderer_modified": False,
            "q11_opened": False, "unit04_opened": False, "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["package_sha256"] = _digest(payload)
    return payload


def build_candidate() -> dict[str, Any]:
    payload = build_export_payload()
    return policy_artifact.build_candidate(
        payload=payload, producer_id=TASK_ID, level_scope=["A1"],
        source_bindings={
            "historical_unit03_q9_sha256": HISTORICAL_Q9_SHA256,
            "historical_unit03_q10_sha256": HISTORICAL_Q10_SHA256,
            "historical_u03scfv2_task_id": historical_u03scfv2.TASK_ID,
            "successor_runtime_target": TOTAL_RUNTIME,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u03q9q10r1_unit03_form_pedagogical_contract_20x40 as validator,
    )
    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate, validation_receipts=[receipt], decision_ref=DECISION_REF, producer_id=TASK_ID,
    )


def main() -> int:
    payload = admit_candidate(build_candidate())["payload"]
    contract = payload["q10_successor_form_contract"]
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={contract['form_count']}")
    print(f"ACTIVITIES_PER_FORM={contract['activities_per_form']}")
    print(f"RUNTIME={contract['runtime_occurrence_count']}")
    print("SECTION_COUNTS=A:6,B:10,C:10,D:8,E:6")
    print(f"CONNECTED_PASSAGE_QUESTIONS={payload['pedagogical_proofs']['section_e_connected_passage_question_count']}")
    print(f"Q6_REGENERATED={payload['q6_preservation']['q6_regenerated']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
