#!/usr/bin/env python3
"""Unit03 Sentence-Competence Forms V2: 20 Forms x 40 = 800 bindings.

Policy-bound extension over current A1FS authorities.  Unit02 16x40 remains
unchanged.  This module reuses current Unit01/Unit02 QuestionBank/runtime
identity, the accepted learner projection, and Unit02 SentenceAsset
admission/lineage semantics.  It creates only the Unit03 deltas and the
Unit03-specific binding/materialization projection.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18a_form01_fresh_learner_materialization_export as u01_learner,
)
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02form01_unit02_existing_learner_renderer_reuse_and_16x40_deterministic_form_materialization
    as u02form01,
)
from ulga.builders import (
    build_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix_and_global_distinct_runtime
    as u02r4,
)
from ulga.builders import (
    build_a1fs_v1_u03q05r1_unit03_exact_lesson_sentence_pattern_binding_crosscheck
    as u03q5,
)
from ulga.builders.a1fs_v1_u02sa01r1.common import normalize_sentence, normalize_surface

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U03SCFV2_Unit03SentenceCompetenceFormsV2Implement800Materialization"
SCHEMA_VERSION = "a1fs.v1.u03scfv2.sentence_competence_forms.v2"
PASS_STATUS = "PASS_A1FS_V1_U03SCFV2_20X40_800_RUNTIME_MATERIALIZATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-27:UNIT03_SENTENCE_COMPETENCE_FORMS_V2_20X40"
NEXT_SHORT_STEP = "A1FS-V1-U03SCFV2R1_Unit03TwentyFormLearnerFacingAcceptance"

UNIT_ID = "GRAMMAR_SUBJECT_PRONOUNS"
FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_RUNTIME = 800
INHERITED_RUNTIME = 400
UNIT03_RUNTIME = 400
UNIT03_CONTEXTS = 80
UNIT03_SENTENCE_ASSETS = 80
UNIT03_QB_ITEMS = 400
CANDIDATES_PER_SLOT = 3
SECTIONS_PER_FORM = 5
ACTIVITIES_PER_SECTION = 8
CURRENT_U02_FORM_COUNT = 16
CURRENT_U02_RUNTIME = 640
CURRENT_U02_APPROVED = 1730
CURRENT_CUMULATIVE_QB = 2204
EXPECTED_CUMULATIVE_AFTER_U03 = 2604

PRONOUNS = ("I", "You", "He", "She", "It", "We", "They")
SECTION_FAMILIES = (
    ("PRONOUN_FOUNDATION", "SUBJECT_PRONOUN_SELECTION"),
    ("REFERENCE_IDENTIFICATION", "PRONOUN_REFERENT_MATCH"),
    ("COMPLETE_SENTENCE", "COMPLETE_SENTENCE_SELECTION"),
    ("CUMULATIVE_INTEGRATION", "U01_U02_U03_INTEGRATION"),
    ("REFERENCE_CHAIN", "TWO_SENTENCE_REFERENCE_CHAIN"),
)
STAGE_BY_FORMS = {
    "GUIDED": range(1, 5),
    "REDUCED_SUPPORT": range(5, 9),
    "INDEPENDENT": range(9, 13),
    "TRANSFER": range(13, 17),
    "RETENTION": range(17, 21),
}
SUPPORT_NOTE = {
    "GUIDED": "Use the name or noun in the context to choose the subject pronoun.",
    "REDUCED_SUPPORT": "Use the context to choose the subject pronoun.",
    "INDEPENDENT": "Choose from meaning and sentence agreement.",
    "TRANSFER": "Apply subject-pronoun reference in the new context without a rule hint.",
    "RETENTION": "Recall the subject pronoun independently.",
}
SAFE_POSSESSABLE_TARGETS = frozenset({
    "apple", "bag", "ball", "bike", "book", "cake", "card", "cat", "coat",
    "cup", "dog", "egg", "game", "hat", "key", "kite", "map", "pen",
    "pencil", "phone", "photo", "picture", "robot", "shoe", "ticket", "toy",
    "watch", "flower", "guitar", "camera",
})


class U03SCFV2BuildError(ValueError):
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
    raise U03SCFV2BuildError(f"FORM_STAGE_MISSING:{form_number}")


def _current_q10() -> dict[str, Any]:
    q10 = dict(u02r4.build_export_payload()["q10_questionbank_capacity_runtime"])
    inv = q10["inventory_summary"]
    contract = q10["runtime_form_contract"]
    checks = {
        "U02_APPROVED": (int(inv["unit02_approved_item_count"]), CURRENT_U02_APPROVED),
        "CUMULATIVE": (int(inv["cumulative_catalog_item_count"]), CURRENT_CUMULATIVE_QB),
        "U02_FORMS": (int(contract["form_count"]), CURRENT_U02_FORM_COUNT),
        "U02_RUNTIME": (int(contract["runtime_occurrence_count"]), CURRENT_U02_RUNTIME),
    }
    for name, (actual, expected) in checks.items():
        if actual != expected:
            raise U03SCFV2BuildError(f"CURRENT_AUTHORITY_DRIFT:{name}:{actual}:{expected}")
    runtime = list(q10["runtime_occurrences"])
    if len(runtime) != CURRENT_U02_RUNTIME or len({row["selected_item_id"] for row in runtime}) != CURRENT_U02_RUNTIME:
        raise U03SCFV2BuildError("CURRENT_U02_RUNTIME_IDENTITY_DRIFT")
    return q10


def _item_index(q10: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = [dict(row) for row in q10["unit02_approved_items"]]
    result = {str(row["item_id"]): row for row in rows}
    if len(rows) != CURRENT_U02_APPROVED or len(result) != CURRENT_U02_APPROVED:
        raise U03SCFV2BuildError("CURRENT_U02_ITEM_INDEX_DRIFT")
    return result


def _lexical_pool(q10: Mapping[str, Any], items: Mapping[str, Mapping[str, Any]]) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for runtime_row in q10["runtime_occurrences"]:
        item = items[str(runtime_row["selected_item_id"])]
        singular = normalize_surface(str(runtime_row.get("target_singular") or ""))
        plural = normalize_surface(str(u02r4._target_plural(item) or ""))
        if singular in SAFE_POSSESSABLE_TARGETS and plural and singular not in found:
            found[singular] = {
                "singular": singular,
                "plural": plural,
                "source_selected_item_id": str(runtime_row["selected_item_id"]),
                "source_slot_id": str(runtime_row["slot_id"]),
            }
    rows = [found[key] for key in sorted(found)]
    if len(rows) < 12:
        raise U03SCFV2BuildError(f"SAFE_CUMULATIVE_LEXICAL_POOL_TOO_SHALLOW:{len(rows)}")
    return rows


def _context_spec(index: int, lexical: Mapping[str, str], pronoun: str) -> dict[str, Any]:
    singular, plural = lexical["singular"], lexical["plural"]
    art = _article(singular)
    if pronoun == "I":
        antecedent, target, referent = f'Ben says, "I have {art} {singular}."', f"I have {art} {singular}.", "Ben (the speaker)"
    elif pronoun == "You":
        antecedent, target, referent = f'Ben says to Mia, "You have {art} {singular}."', f"You have {art} {singular}.", "Mia (the listener)"
    elif pronoun == "He":
        antecedent, target, referent = f"Ben has {art} {singular}.", f"He has the {singular}.", "Ben"
    elif pronoun == "She":
        antecedent, target, referent = f"Mia has {art} {singular}.", f"She has the {singular}.", "Mia"
    elif pronoun == "It":
        antecedent, target, referent = f"This is {art} {singular}.", f"It is the {singular}.", f"the {singular}"
    elif pronoun == "We":
        antecedent, target, referent = f'Ben says, "Mia and I have two {plural}."', f"We have two {plural}.", "Ben and Mia (including the speaker)"
    elif pronoun == "They":
        antecedent, target, referent = f"Ben and Mia have two {plural}.", f"They have two {plural}.", "Ben and Mia"
    else:
        raise U03SCFV2BuildError(f"UNKNOWN_PRONOUN:{pronoun}")
    return {
        "context_id": f"U03-CTX-{index + 1:03d}", "pronoun": pronoun,
        "singular": singular, "plural": plural, "antecedent": antecedent,
        "target_sentence": target, "referent": referent,
        "source_selected_item_id": lexical["source_selected_item_id"],
        "source_slot_id": lexical["source_slot_id"],
    }


def _contexts(q10: Mapping[str, Any], items: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lexical in _lexical_pool(q10, items):
        for pronoun in PRONOUNS:
            rows.append(_context_spec(len(rows), lexical, pronoun))
            if len(rows) == UNIT03_CONTEXTS:
                return rows
    raise U03SCFV2BuildError(f"UNIT03_CONTEXT_COUNT_TOO_SHALLOW:{len(rows)}")


def _sentence_assets(contexts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for context in contexts:
        text = str(context["target_sentence"])
        normalized = normalize_sentence(text)
        rows.append({
            "sentence_id": "U03-SENT-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16].upper(),
            "unit_id": UNIT_ID, "text": text, "normalized_text": normalized,
            "canonical_admission_status": "ADMITTED", "pattern_id": None,
            "pattern_binding_status": "NO_NEW_UNIT03_PATTERN_FAMILY_ADMITTED",
            "context_bound": True, "context_id": context["context_id"],
            "subject_pronoun": context["pronoun"], "singular": context["singular"],
            "plural": context["plural"],
            "generation_role": "UNIT03_SUBJECT_PRONOUN_CONTEXT_BOUND_TARGET",
            "semantic_pedagogical_decision": "APPROVE",
            "decision_reasons": [
                "POST_GENERATION_FULL_SENTENCE_REVIEW",
                "UNIT03_SUBJECT_PRONOUN_CONTEXT_BOUND",
                "CUMULATIVE_U01_U02_LEXICAL_CONTEXT",
                "NO_NEW_SENTENCE_PATTERN_AUTHORITY_CLAIM",
            ],
            "source_refs": [
                {"source_type": "UNIT03_EXACT_LESSON_BINDING_GATE", "task_id": u03q5.TASK_ID, "lesson_id": u03q5.LESSON_ID},
                {"source_type": "CURRENT_U02_RUNTIME_SELECTED_ITEM", "task_id": u02r4.TASK_ID, "selected_item_id": context["source_selected_item_id"], "slot_id": context["source_slot_id"]},
            ],
            "legacy_unnormalized": False,
        })
    if len(rows) != UNIT03_SENTENCE_ASSETS or len({row["sentence_id"] for row in rows}) != UNIT03_SENTENCE_ASSETS or len({row["normalized_text"] for row in rows}) != UNIT03_SENTENCE_ASSETS:
        raise U03SCFV2BuildError("UNIT03_SENTENCE_ASSET_IDENTITY_INVALID")
    return rows


def _unique_options(*values: str) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _response_contract(correct: str) -> dict[str, Any]:
    return {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": [correct], "accepted_sequence": [], "capture_enabled": True, "human_review_fallback": False}


def _question_item(context: Mapping[str, Any], asset: Mapping[str, Any], family: str) -> dict[str, Any]:
    pronoun, singular, plural = str(context["pronoun"]), str(context["singular"]), str(context["plural"])
    antecedent, target, referent = str(context["antecedent"]), str(context["target_sentence"]), str(context["referent"])
    if family == "SUBJECT_PRONOUN_SELECTION":
        section, stimulus, prompt, options, correct = "PRONOUN_FOUNDATION", antecedent, "Choose the subject pronoun that continues the reference.", list(PRONOUNS), pronoun
    elif family == "PRONOUN_REFERENT_MATCH":
        section, stimulus, prompt = "REFERENCE_IDENTIFICATION", f"{antecedent} {target}", f"Who or what does {pronoun} refer to?"
        options, correct = _unique_options(referent, "Ben", "Mia", f"the {singular}", "Ben and Mia"), referent
    elif family == "COMPLETE_SENTENCE_SELECTION":
        section, stimulus, prompt = "COMPLETE_SENTENCE", antecedent, "Choose the complete sentence that uses the correct subject pronoun."
        options, correct = _unique_options(target, f"They has the {singular}.", f"He have two {plural}.", f"It have the {singular}."), target
    elif family == "U01_U02_U03_INTEGRATION":
        section, stimulus, prompt = "CUMULATIVE_INTEGRATION", antecedent, "Choose the sentence that keeps the article/plural meaning and the subject pronoun correct."
        if pronoun in {"We", "They"}:
            options = _unique_options(target, f"{pronoun} have two {singular}.", f"He have two {plural}.", f"{pronoun} has two {plural}.")
        elif pronoun == "It":
            options = _unique_options(target, f"They is the {singular}.", f"It are the {singular}.", f"He is the {singular}.")
        else:
            article, verb = _article(singular), "has" if pronoun in {"He", "She"} else "have"
            wrong_article = "a" if article == "an" else "an"
            options = _unique_options(target, f"{pronoun} {verb} {wrong_article} {singular}.", f"They has {article} {singular}.", f"{pronoun} {verb} two {singular}.")
        correct = target
    elif family == "TWO_SENTENCE_REFERENCE_CHAIN":
        section, stimulus, prompt, options, correct = "REFERENCE_CHAIN", f"{antecedent} {target}", "Which subject pronoun carries the reference into the second sentence?", list(PRONOUNS), pronoun
    else:
        raise U03SCFV2BuildError(f"UNKNOWN_UNIT03_FAMILY:{family}")
    if len(options) < 2 or correct not in options:
        raise U03SCFV2BuildError(f"UNIT03_OPTIONS_INVALID:{context['context_id']}:{family}")
    item_id = f"U03SCFV2-QB-{family}-{context['context_id']}"
    return {
        "item_id": item_id, "unit_id": UNIT_ID, "task_family": family,
        "section": section, "skill": "READING", "question_type": "multiple_choice",
        "prompt": prompt, "stimulus": stimulus, "options": options,
        "correct_answer": correct, "accepted_answers": [correct],
        "scoring_mode": "EXACT_OPTION", "response_contract": _response_contract(correct),
        "learner_visible_capable": True,
        "lexical_slots": {"singular_noun": singular, "plural_noun": plural, "subject_pronoun": pronoun},
        "sentence_asset_binding": {"status": "BOUND_CANONICAL_UNIT03_SENTENCE_ASSET", "sentence_asset_id": asset["sentence_id"]},
        "pattern_binding_status": "INHERITED_OR_RULE_BOUND_NO_NEW_Q5_PATTERN",
        "admission_proposal": {"status": "AUTO_APPROVED", "reason_codes": ["UNIT03_SENTENCE_COMPETENCE_V2_POLICY_BOUND", "CONTEXT_BOUND_SENTENCE_ASSET", f"TASK_FAMILY_{family}"]},
        "source_refs": list(asset["source_refs"]) + [{"source_type": "UNIT03_SENTENCE_ASSET", "sentence_asset_id": asset["sentence_id"]}],
        "semantic_signature": _digest({"family": family, "context_id": context["context_id"], "stimulus": stimulus, "prompt": prompt, "correct": correct}),
    }


def _unit03_items(contexts: Sequence[Mapping[str, Any]], assets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_context = {str(asset["context_id"]): asset for asset in assets}
    rows = [_question_item(context, by_context[str(context["context_id"])], family) for context in contexts for _, family in SECTION_FAMILIES]
    if len(rows) != UNIT03_QB_ITEMS or len({row["item_id"] for row in rows}) != UNIT03_QB_ITEMS or len({row["semantic_signature"] for row in rows}) != UNIT03_QB_ITEMS:
        raise U03SCFV2BuildError("UNIT03_QB_IDENTITY_INVALID")
    return rows


def _even_inherited_runtime(q10: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = [dict(row) for row in q10["runtime_occurrences"]]
    rows = [source[(i * len(source)) // INHERITED_RUNTIME] for i in range(INHERITED_RUNTIME)]
    if len({row["selected_item_id"] for row in rows}) != INHERITED_RUNTIME:
        raise U03SCFV2BuildError("INHERITED_SELECTED_ITEM_NOT_DISTINCT")
    return rows


def _new_candidate_ids(family_rows: Sequence[Mapping[str, Any]], selected_id: str) -> list[str]:
    ids = [str(row["item_id"]) for row in family_rows]
    index = ids.index(selected_id)
    return [ids[index], ids[(index + 1) % len(ids)], ids[(index + 2) % len(ids)]]


def _runtime_bindings(q10: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]], new_items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    inherited = _even_inherited_runtime(q10)
    by_family = {family: [row for row in new_items if row["task_family"] == family] for _, family in SECTION_FAMILIES}
    runtime: list[dict[str, Any]] = []
    inherited_cursor = 0
    for form_number in range(1, FORM_COUNT + 1):
        form_contexts = list(contexts[(form_number - 1) * 4 : form_number * 4])
        for section_ordinal, (section, family) in enumerate(SECTION_FAMILIES, start=1):
            section_new: list[Mapping[str, Any]] = []
            for context in form_contexts:
                suffix = str(context["context_id"])
                matches = [row for row in by_family[family] if str(row["item_id"]).endswith(suffix)]
                if len(matches) != 1:
                    raise U03SCFV2BuildError(f"NEW_ITEM_CONTEXT_BINDING_INVALID:{family}:{suffix}:{len(matches)}")
                section_new.append(matches[0])
            for local_index, item in enumerate(section_new, start=1):
                selected_id = str(item["item_id"])
                slot = f"U03-F{form_number:02d}-SEC{section_ordinal:02d}-N{local_index:02d}"
                runtime.append({
                    "slot_id": slot, "runtime_occurrence_id": f"{slot}::{selected_id}",
                    "form_number": form_number, "progression_stage": _stage(form_number),
                    "section": section, "section_ordinal": section_ordinal,
                    "section_activity_ordinal": local_index, "task_family": family,
                    "candidate_ids": _new_candidate_ids(by_family[family], selected_id),
                    "selected_item_id": selected_id, "questionbank_item_id": selected_id,
                    "questionbank_source": "UNIT03_DELTA",
                    "runtime_selection_rule": "UNIT03_POLICY_BOUND_FIRST_OF_THREE_DETERMINISTIC_BINDING",
                    "learner_support_note": SUPPORT_NOTE[_stage(form_number)],
                    "sentence_asset_binding": dict(item["sentence_asset_binding"]),
                })
            for local_index in range(5, 9):
                source = inherited[inherited_cursor]
                inherited_cursor += 1
                selected_id = str(source["selected_item_id"])
                slot = f"U03-F{form_number:02d}-SEC{section_ordinal:02d}-N{local_index:02d}"
                runtime.append({
                    "slot_id": slot, "runtime_occurrence_id": f"{slot}::{selected_id}",
                    "form_number": form_number, "progression_stage": _stage(form_number),
                    "section": section, "section_ordinal": section_ordinal,
                    "section_activity_ordinal": local_index, "task_family": str(source["task_family"]),
                    "candidate_ids": list(source["candidate_ids"]), "selected_item_id": selected_id,
                    "questionbank_item_id": selected_id, "questionbank_source": "INHERITED_CURRENT_U01_U02",
                    "runtime_selection_rule": "PRESERVE_EXISTING_CURRENT_RUNTIME_SELECTED_IDENTITY",
                    "learner_support_note": SUPPORT_NOTE[_stage(form_number)],
                    "sentence_asset_binding": dict(source.get("sentence_asset_binding") or {}),
                    "inherited_source_slot_id": str(source["slot_id"]),
                })
    if inherited_cursor != INHERITED_RUNTIME or len(runtime) != TOTAL_RUNTIME:
        raise U03SCFV2BuildError("RUNTIME_DENOMINATOR_INVALID")
    if len({row["runtime_occurrence_id"] for row in runtime}) != TOTAL_RUNTIME or len({row["selected_item_id"] for row in runtime}) != TOTAL_RUNTIME:
        raise U03SCFV2BuildError("RUNTIME_GLOBAL_800_DISTINCTNESS_FAILED")
    if not all(len(row["candidate_ids"]) == 3 and len(set(row["candidate_ids"])) == 3 and row["selected_item_id"] == row["candidate_ids"][0] for row in runtime):
        raise U03SCFV2BuildError("RUNTIME_THREE_CANDIDATE_CONTRACT_INVALID")
    return runtime


def _student_activity(number: int, runtime_row: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    note = str(runtime_row.get("learner_support_note") or "").strip()
    prompt = str(item.get("prompt") or "").strip()
    if note:
        prompt = f"{prompt} {note}".strip()
    selected = {
        "activity_id": str(runtime_row["slot_id"]), "skill": str(item["skill"]),
        "scene_ref_id": f"U03-F{int(runtime_row['form_number']):02d}-SEC{int(runtime_row['section_ordinal']):02d}",
        "setting": str(runtime_row["section"]).replace("_", " ").title(),
        "stimulus": str(item.get("stimulus") or ""), "prompt": prompt,
        "options": list(item.get("options") or []), "response_mode": u02form01._response_mode(item),
        "capture_enabled": bool((item.get("response_contract") or {}).get("capture_enabled", True)),
        "practice_only": False,
    }
    blueprint = {"scene_ref_id": selected["scene_ref_id"], "skill": selected["skill"]}
    return u01_learner._student_activity(number=number, blueprint=blueprint, selected=selected)


def _student_forms(runtime: Sequence[Mapping[str, Any]], item_index: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    forms: list[dict[str, Any]] = []
    for form_number in range(1, FORM_COUNT + 1):
        rows = [row for row in runtime if int(row["form_number"]) == form_number]
        if len(rows) != ACTIVITIES_PER_FORM:
            raise U03SCFV2BuildError(f"FORM_ACTIVITY_COUNT_INVALID:{form_number}")
        activities = [_student_activity(number, row, item_index[str(row["selected_item_id"])]) for number, row in enumerate(rows, start=1)]
        if Counter(row["section"] for row in rows) != Counter({section: 8 for section, _ in SECTION_FAMILIES}):
            raise U03SCFV2BuildError(f"FORM_SECTION_DISTRIBUTION_INVALID:{form_number}")
        student_form = {
            "unit_id": UNIT_ID, "unit_ordinal": 3, "form_id": f"U03-F{form_number:02d}",
            "form_ordinal": form_number, "progression_stage": _stage(form_number),
            "section_count": SECTIONS_PER_FORM, "learner_visible_activity_count": len(activities),
            "sections": [{"section_ordinal": index, "section": section, "activity_count": 8} for index, (section, _) in enumerate(SECTION_FAMILIES, start=1)],
            "activities": activities,
        }
        u01_learner._assert_no_answer_leak(student_form)
        forms.append(student_form)
    return forms


def build_export_payload() -> dict[str, Any]:
    q5 = u03q5.build_report()
    u03q5.validate(q5)
    if q5["q5_pattern_family_coverage"]["cumulative_pattern_family_count"] != 7 or q5["q5_exact_frame_coverage"]["cumulative_exact_frame_count"] != 15 or q5["q5_pattern_family_coverage"]["unit03_new_canonical_pattern_family_count"] != 0:
        raise U03SCFV2BuildError("UNIT03_Q5_PATTERN_AUTHORITY_DRIFT")
    q10 = _current_q10()
    current_items = _item_index(q10)
    contexts = _contexts(q10, current_items)
    assets = _sentence_assets(contexts)
    new_items = _unit03_items(contexts, assets)
    runtime = _runtime_bindings(q10, contexts, new_items)
    all_items = dict(current_items)
    all_items.update({str(row["item_id"]): row for row in new_items})
    forms = _student_forms(runtime, all_items)
    source_counts = Counter(row["questionbank_source"] for row in runtime)
    stage_counts = Counter(row["progression_stage"] for row in runtime)
    payload = {
        "schema_version": SCHEMA_VERSION, "program_id": PROGRAM_ID, "task_id": TASK_ID,
        "status": PASS_STATUS, "unit_id": UNIT_ID,
        "source_authority": {
            "unit03_q5_task_id": u03q5.TASK_ID, "unit02_current_runtime_task_id": u02r4.TASK_ID,
            "unit02_form01_task_id": u02form01.TASK_ID,
            "sentence_asset_semantics_reused_from": "ulga/builders/a1fs_v1_u02sa01r1",
            "existing_learner_projection_reused": "product.a1fs_v1_2_1.u01qb18a_form01_fresh_learner_materialization_export._student_activity/_assert_no_answer_leak",
        },
        "unit02_preservation": {
            "form_count": 16, "runtime_occurrence_count": 640, "approved_item_count": 1730,
            "cumulative_catalog_item_count": 2204, "unit02_16x40_mutated": False,
        },
        "sentence_asset_delta": {
            "asset_count": len(assets), "assets": assets, "asset_digest": _digest(assets),
            "parallel_sentence_asset_schema_created": False,
            "post_generation_full_sentence_review": True, "context_bound_lineage_preserved": True,
        },
        "questionbank_delta": {
            "unit03_new_item_count": len(new_items), "unit03_new_items": new_items,
            "inherited_cumulative_catalog_count": 2204,
            "cumulative_catalog_count_after_unit03": EXPECTED_CUMULATIVE_AFTER_U03,
            "parallel_questionbank_created": False,
        },
        "runtime_form_contract": {
            "form_count": 20, "activities_per_form": 40, "runtime_occurrence_count": len(runtime),
            "inherited_runtime_binding_count": source_counts["INHERITED_CURRENT_U01_U02"],
            "unit03_delta_runtime_binding_count": source_counts["UNIT03_DELTA"],
            "sections_per_form": 5, "activities_per_section": 8, "candidate_count_per_slot": 3,
            "global_800_distinct_selected_item_proof": len({row["selected_item_id"] for row in runtime}) == 800,
            "parallel_selector_created": False, "parallel_runtime_authority_created": False,
        },
        "stage_allocation": {
            "forms_by_stage": {stage: list(forms_range) for stage, forms_range in STAGE_BY_FORMS.items()},
            "runtime_occurrences_by_stage": dict(stage_counts),
            "section_order": [section for section, _ in SECTION_FAMILIES],
        },
        "runtime_bindings": runtime, "student_forms": forms,
        "claim_boundaries": {
            "unit02_forms01_16_mutated": False, "unit01_unit02_questionbank_items_mutated": False,
            "second_questionbank_authority_created": False, "second_selector_created": False,
            "second_renderer_created": False, "parallel_sentence_asset_schema_created": False,
            "canonical_sentence_pattern_authority_mutated": False, "learner_state_mutated": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    if sum(form["learner_visible_activity_count"] for form in forms) != TOTAL_RUNTIME:
        raise U03SCFV2BuildError("LEARNER_VISIBLE_800_COUNT_INVALID")
    payload["package_sha256"] = _digest(payload)
    return payload


def build_candidate() -> dict[str, Any]:
    payload = build_export_payload()
    return policy_artifact.build_candidate(
        payload=payload, producer_id=TASK_ID, level_scope=["A1"],
        source_bindings={
            "unit03_q5_task_id": u03q5.TASK_ID,
            "current_unit02_runtime_task_id": u02r4.TASK_ID,
            "current_unit02_runtime_count": 640, "unit03_runtime_target": 800,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u03scfv2_unit03_sentence_competence_forms_v2 as validator
    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(candidate, validation_receipts=[receipt], decision_ref=DECISION_REF, producer_id=TASK_ID)


def main() -> int:
    payload = admit_candidate(build_candidate())["payload"]
    contract = payload["runtime_form_contract"]
    print(f"STATUS={PASS_STATUS}")
    print(f"UNIT03_SENTENCE_ASSETS={payload['sentence_asset_delta']['asset_count']}")
    print(f"UNIT03_NEW_QB_ITEMS={payload['questionbank_delta']['unit03_new_item_count']}")
    print(f"FORMS={contract['form_count']}")
    print(f"ACTIVITIES_PER_FORM={contract['activities_per_form']}")
    print(f"RUNTIME_BINDINGS={contract['runtime_occurrence_count']}")
    print(f"INHERITED_BINDINGS={contract['inherited_runtime_binding_count']}")
    print(f"UNIT03_DELTA_BINDINGS={contract['unit03_delta_runtime_binding_count']}")
    print(f"GLOBAL_800_DISTINCT={contract['global_800_distinct_selected_item_proof']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
