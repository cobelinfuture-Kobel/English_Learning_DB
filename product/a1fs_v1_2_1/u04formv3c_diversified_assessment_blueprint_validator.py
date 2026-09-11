from __future__ import annotations

import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as base_contract

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical validation only over a static GPT-5.6-designed assessment blueprint. "
    "This module does not assign response modes, task families, capabilities, learner wording, "
    "answers, distractors, Current360 passages, or picture content."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FORMV3C_GPT56DiversifiedAssessmentBlueprint_Form01To04"
BLUEPRINT_STATUS = "GPT5_6_DIRECT_DESIGNED_STATIC_BLUEPRINT"
STATUS = "PASS_A1FS_V1_U04FORMV3C_DIVERSIFIED_BLUEPRINT_FORM01_TO04_VALIDATION"
REVISION = "FORMV3C_GUIDED_DIVERSIFIED_RESPONSE_BLUEPRINT_VALIDATOR_V1"
NEXT_SHORT_STEP = "A1FS-V1-U04FORMV3C_A1_GPT56Current360BindingAndDirectAuthoring_Form01To04"
BLUEPRINT_NAME = "u04formv3c_diversified_assessment_blueprint_form01_04.json"
EXPECTED_FORMS = (1, 2, 3, 4)
EXPECTED_RESPONSE_MODES = {
    "ASK_A_QUESTION", "DIALOGUE_RESPONSE", "FACT_CORRECTION", "GIST_BEST_TITLE",
    "MATCHING", "MULTIPLE_MATCHING", "NOTE_COMPLETION", "ONE_TO_THREE_WORDS",
    "ONE_WORD_GAP", "ORDER_SEQUENCE", "PICTURE_DIFFERENCE", "PICTURE_LABEL",
    "PICTURE_POSITION", "RECONSTRUCTION", "REFERENCE_MATCHING", "SELECT_ONE",
    "SENTENCE_COMPLETION", "SHORT_ANSWER", "SHORT_RETELL", "SPEAK_SHORT_RESPONSE",
    "TABLE_COMPLETION", "WRITE_SENTENCE",
}
PICTURE_MODES = {"PICTURE_POSITION", "PICTURE_DIFFERENCE", "PICTURE_LABEL"}
LEARNER_CONTENT_KEYS_FORBIDDEN_IN_BLUEPRINT = {
    "prompt", "options", "reference_answer", "correct_option_index", "passage", "episode_id"
}


class Unit04FormV3CBlueprintError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load(repo_root: Path | str | None = None) -> dict[str, Any]:
    path = _root(repo_root) / "product" / "a1fs_v1_2_1" / BLUEPRINT_NAME
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _expected_section_context(number: int) -> tuple[str, str]:
    if 1 <= number <= 3:
        return "A", "A1"
    if 4 <= number <= 6:
        return "A", "A2"
    if 7 <= number <= 11:
        return "B", "BC1"
    if 12 <= number <= 16:
        return "B", "BC2"
    if 17 <= number <= 21:
        return "C", "BC1"
    if 22 <= number <= 26:
        return "C", "BC2"
    if 27 <= number <= 30:
        return "D", "DE1"
    if 31 <= number <= 34:
        return "D", "DE2"
    if 35 <= number <= 37:
        return "E", "DE1"
    if 38 <= number <= 40:
        return "E", "DE2"
    raise Unit04FormV3CBlueprintError(f"QUESTION_NUMBER_OUT_OF_RANGE:{number}")


def validate_blueprint(repo_root: Path | str | None = None) -> dict[str, Any]:
    payload = _load(repo_root)
    if payload.get("schema_version") != "a1fs.v1.u04.formv3c.diversified_assessment_blueprint.v1":
        raise Unit04FormV3CBlueprintError("SCHEMA_VERSION_DRIFT")
    if payload.get("program_id") != PROGRAM_ID or payload.get("unit_id") != UNIT_ID:
        raise Unit04FormV3CBlueprintError("PROGRAM_OR_UNIT_DRIFT")
    if payload.get("task_id") != TASK_ID or payload.get("status") != BLUEPRINT_STATUS:
        raise Unit04FormV3CBlueprintError("TASK_OR_STATUS_DRIFT")

    provenance = payload.get("authoring_provenance") or {}
    if provenance.get("assessment_blueprint_author") != "GPT-5.6_SOL_DIRECT_DESIGN":
        raise Unit04FormV3CBlueprintError("BLUEPRINT_AUTHOR_NOT_GPT56_DIRECT_DESIGN")
    if provenance.get("response_mode_selection_author") != "GPT-5.6_SOL_DIRECT_DESIGN":
        raise Unit04FormV3CBlueprintError("RESPONSE_MODE_SELECTOR_NOT_GPT56")
    if provenance.get("task_family_selection_author") != "GPT-5.6_SOL_DIRECT_DESIGN":
        raise Unit04FormV3CBlueprintError("TASK_FAMILY_SELECTOR_NOT_GPT56")
    for key in (
        "python_blueprint_generation_used", "python_response_mode_assignment_used",
        "python_task_family_assignment_used", "python_learner_content_authoring_used",
        "legacy_python_task_builder_used",
    ):
        if provenance.get(key) is not False:
            raise Unit04FormV3CBlueprintError(f"FORBIDDEN_PYTHON_AUTHORING_ROLE:{key}")
    if provenance.get("learner_content_authoring_stage") != "NOT_STARTED_BLUEPRINT_ONLY":
        raise Unit04FormV3CBlueprintError("LEARNER_CONTENT_PREMATURELY_AUTHORED")

    scope = payload.get("scope") or {}
    if scope.get("forms") != [1, 2, 3, 4]:
        raise Unit04FormV3CBlueprintError("FORM_SCOPE_DRIFT")
    if scope.get("stage") != "GUIDED" or scope.get("support_level") != "HIGH":
        raise Unit04FormV3CBlueprintError("GUIDED_SUPPORT_CONTRACT_DRIFT")
    if scope.get("tasks_per_form") != 40:
        raise Unit04FormV3CBlueprintError("TASKS_PER_FORM_DRIFT")
    if scope.get("section_counts") != base_contract.SECTION_COUNTS:
        raise Unit04FormV3CBlueprintError("SECTION_COUNT_CONTRACT_DRIFT")
    expected_context_slots = {
        slot: dict(spec["question_load"]) for slot, spec in base_contract.CONTEXT_SLOT_CONTRACT.items()
    }
    if scope.get("context_slots") != expected_context_slots:
        raise Unit04FormV3CBlueprintError("CONTEXT_SLOT_CONTRACT_DRIFT")
    if scope.get("current360_passage_selection_stage") != "AFTER_BLUEPRINT_ACCEPTANCE":
        raise Unit04FormV3CBlueprintError("CURRENT360_SELECTION_STAGE_DRIFT")
    if scope.get("answer_option_authoring_stage") != "AFTER_CURRENT360_BINDING_BY_GPT5_6":
        raise Unit04FormV3CBlueprintError("ANSWER_AUTHORING_STAGE_DRIFT")

    if base_contract.CAMBRIDGE_BOUNDARY.get("grammar_ceiling") != "A1":
        raise Unit04FormV3CBlueprintError("A1_CEILING_DRIFT")
    if base_contract.CAMBRIDGE_BOUNDARY.get("a2_a2plus_unlocked") is not False:
        raise Unit04FormV3CBlueprintError("A2_A2PLUS_UNLOCKED")
    if base_contract.CAMBRIDGE_BOUNDARY.get("listening_modified") is not False:
        raise Unit04FormV3CBlueprintError("LISTENING_CHANGED")

    mode_contract = payload.get("response_mode_contract") or {}
    allowed_modes = set(mode_contract.get("allowed_modes") or [])
    required_modes = set(mode_contract.get("required_form01_04_coverage") or [])
    if allowed_modes != EXPECTED_RESPONSE_MODES or required_modes != EXPECTED_RESPONSE_MODES:
        raise Unit04FormV3CBlueprintError("RESPONSE_MODE_REPERTOIRE_DRIFT")
    if mode_contract.get("python_post_design_shuffle_allowed") is not False:
        raise Unit04FormV3CBlueprintError("PYTHON_POST_DESIGN_SHUFFLE_ALLOWED")
    if mode_contract.get("task_count_and_response_field_count_are_distinct") is not True:
        raise Unit04FormV3CBlueprintError("TASK_RESPONSE_FIELD_MODEL_DRIFT")

    forms = payload.get("forms") or []
    if [form.get("form_number") for form in forms] != list(EXPECTED_FORMS):
        raise Unit04FormV3CBlueprintError("FORM_SEQUENCE_DRIFT")

    all_modes: Counter[str] = Counter()
    form_reports: list[dict[str, Any]] = []
    mode_sequences: dict[int, tuple[str, ...]] = {}
    family_sequences: set[tuple[str, ...]] = set()
    capability_sequences: set[tuple[str, ...]] = set()

    for form in forms:
        number = int(form["form_number"])
        if form.get("form_id") != f"U04-FORMV3C-F{number:02d}":
            raise Unit04FormV3CBlueprintError(f"FORM_ID_DRIFT:F{number:02d}")
        if form.get("stage") != "GUIDED" or form.get("support_level") != "HIGH":
            raise Unit04FormV3CBlueprintError(f"FORM_GUIDED_SUPPORT_DRIFT:F{number:02d}")
        tasks = form.get("tasks") or []
        if len(tasks) != 40:
            raise Unit04FormV3CBlueprintError(f"TASK_COUNT_DRIFT:F{number:02d}:{len(tasks)}")

        section_counts: Counter[str] = Counter()
        context_load = {slot: Counter() for slot in base_contract.CONTEXT_SLOT_CONTRACT}
        modes: list[str] = []
        families: list[str] = []
        capabilities: list[str] = []
        response_fields = 0
        picture_tasks = 0

        for expected_number, task in enumerate(tasks, start=1):
            if task.get("question_number") != expected_number:
                raise Unit04FormV3CBlueprintError(f"QUESTION_NUMBER_DRIFT:F{number:02d}:Q{expected_number:02d}")
            expected_section, expected_context = _expected_section_context(expected_number)
            if task.get("section") != expected_section or task.get("context_role") != expected_context:
                raise Unit04FormV3CBlueprintError(f"SECTION_CONTEXT_DRIFT:F{number:02d}:Q{expected_number:02d}")
            if any(key in task for key in LEARNER_CONTENT_KEYS_FORBIDDEN_IN_BLUEPRINT):
                raise Unit04FormV3CBlueprintError(f"LEARNER_CONTENT_PRESENT_IN_BLUEPRINT:F{number:02d}:Q{expected_number:02d}")
            if task.get("source_evidence_required") is not True:
                raise Unit04FormV3CBlueprintError(f"SOURCE_EVIDENCE_NOT_REQUIRED:F{number:02d}:Q{expected_number:02d}")

            mode = str(task.get("response_mode") or "")
            family = str(task.get("task_family") or "")
            capability = str(task.get("assessment_capability") or "")
            if mode not in EXPECTED_RESPONSE_MODES or not family or not capability:
                raise Unit04FormV3CBlueprintError(f"TASK_DIMENSION_INVALID:F{number:02d}:Q{expected_number:02d}")
            fields = task.get("response_field_count")
            if not isinstance(fields, int) or fields < 1:
                raise Unit04FormV3CBlueprintError(f"RESPONSE_FIELD_COUNT_INVALID:F{number:02d}:Q{expected_number:02d}")
            picture_required = task.get("picture_required")
            if (mode in PICTURE_MODES) != (picture_required is True):
                raise Unit04FormV3CBlueprintError(f"PICTURE_MODE_BINDING_INVALID:F{number:02d}:Q{expected_number:02d}")

            section_counts[expected_section] += 1
            context_load[expected_context][expected_section] += 1
            modes.append(mode)
            families.append(family)
            capabilities.append(capability)
            response_fields += fields
            picture_tasks += int(picture_required is True)
            all_modes[mode] += 1

        if dict(section_counts) != base_contract.SECTION_COUNTS:
            raise Unit04FormV3CBlueprintError(f"SECTION_COUNTS_DRIFT:F{number:02d}")
        actual_context = {slot: dict(counts) for slot, counts in context_load.items()}
        if actual_context != expected_context_slots:
            raise Unit04FormV3CBlueprintError(f"CONTEXT_LOAD_DRIFT:F{number:02d}:{actual_context}")
        if len(set(modes)) < int(mode_contract["minimum_distinct_modes_per_form"]):
            raise Unit04FormV3CBlueprintError(f"RESPONSE_MODE_BREADTH_TOO_LOW:F{number:02d}:{len(set(modes))}")
        if len(set(families)) < 28:
            raise Unit04FormV3CBlueprintError(f"TASK_FAMILY_BREADTH_TOO_LOW:F{number:02d}:{len(set(families))}")
        if len(set(capabilities)) < 22:
            raise Unit04FormV3CBlueprintError(f"CAPABILITY_BREADTH_TOO_LOW:F{number:02d}:{len(set(capabilities))}")
        if picture_tasks < 2:
            raise Unit04FormV3CBlueprintError(f"PICTURE_TASK_BREADTH_TOO_LOW:F{number:02d}:{picture_tasks}")
        if response_fields <= 40:
            raise Unit04FormV3CBlueprintError(f"MULTI_FIELD_TASK_MODEL_NOT_MATERIALIZED:F{number:02d}:{response_fields}")

        mode_sequences[number] = tuple(modes)
        family_sequences.add(tuple(families))
        capability_sequences.add(tuple(capabilities))
        form_reports.append({
            "form_number": number,
            "distinct_response_mode_count": len(set(modes)),
            "distinct_task_family_count": len(set(families)),
            "distinct_capability_count": len(set(capabilities)),
            "response_field_count": response_fields,
            "picture_task_count": picture_tasks,
            "response_mode_counts": dict(sorted(Counter(modes).items())),
        })

    if set(all_modes) != EXPECTED_RESPONSE_MODES:
        raise Unit04FormV3CBlueprintError(f"FORM01_04_RESPONSE_MODE_COVERAGE_DRIFT:{sorted(set(all_modes))}")
    if len(set(mode_sequences.values())) != 4 or len(family_sequences) != 4 or len(capability_sequences) != 4:
        raise Unit04FormV3CBlueprintError("FORM_SIGNATURE_DUPLICATE")

    fixed_slots: list[int] = []
    pairwise: list[dict[str, Any]] = []
    max_allowed = float(mode_contract["max_pairwise_same_slot_mode_ratio"])
    for q_index in range(40):
        values = {mode_sequences[number][q_index] for number in EXPECTED_FORMS}
        if len(values) == 1:
            fixed_slots.append(q_index + 1)
    if fixed_slots and mode_contract.get("fixed_same_slot_mode_across_all_four_forms_allowed") is False:
        raise Unit04FormV3CBlueprintError(f"FIXED_RESPONSE_MODE_SLOTS:{fixed_slots}")

    for left, right in combinations(EXPECTED_FORMS, 2):
        same = sum(a == b for a, b in zip(mode_sequences[left], mode_sequences[right]))
        ratio = same / 40
        if ratio > max_allowed:
            raise Unit04FormV3CBlueprintError(f"FORM_RESPONSE_SIGNATURE_TOO_SIMILAR:F{left:02d}:F{right:02d}:{ratio:.3f}")
        pairwise.append({"left": left, "right": right, "same_slot_count": same, "same_slot_ratio": ratio})

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "form_count": 4,
        "task_count": 160,
        "response_mode_coverage_count": len(all_modes),
        "response_mode_coverage": sorted(all_modes),
        "response_mode_counts": dict(sorted(all_modes.items())),
        "fixed_response_mode_slot_count": len(fixed_slots),
        "pairwise_response_signature": pairwise,
        "forms": form_reports,
        "python_blueprint_generation_used": False,
        "python_response_mode_assignment_used": False,
        "python_task_family_assignment_used": False,
        "python_learner_content_authoring_used": False,
        "legacy_python_task_builder_used": False,
        "learner_content_present": False,
        "current360_binding_status": "PENDING_GPT5_6_DIRECT_BINDING",
        "a2_a2plus_unlocked": False,
        "listening_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(validate_blueprint(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
