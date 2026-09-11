from __future__ import annotations

import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as base_contract
from product.a1fs_v1_2_1 import u04formv3c_diversified_assessment_blueprint_validator as guided_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical validation only over four static GPT-5.6-designed REDUCED_SUPPORT blueprints. "
    "This module does not choose response modes, quota families, task families, capabilities, "
    "Current360 episodes, learner wording, answers, distractors, or picture content."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FORMV3C_GPT56DiversifiedAssessmentBlueprint_Form05To08"
BLUEPRINT_STATUS = "GPT5_6_DIRECT_DESIGNED_STATIC_BLUEPRINT"
STATUS = "PASS_A1FS_V1_U04FORMV3C_REDUCED_SUPPORT_BLUEPRINT_FORM05_TO08_VALIDATION"
REVISION = "FORMV3C_REDUCED_SUPPORT_DIVERSIFIED_RESPONSE_BLUEPRINT_VALIDATOR_V1"
NEXT_SHORT_STEP = "A1FS-V1-U04FORMV3C_GPT56Current360BindingAndDirectAuthoring_Form05To08"
EXPECTED_FORMS = (5, 6, 7, 8)
BLUEPRINT_NAMES = {
    number: f"u04formv3c_reduced_support_blueprint_form{number:02d}.json"
    for number in EXPECTED_FORMS
}
EXPECTED_RESPONSE_MODES = set(guided_validator.EXPECTED_RESPONSE_MODES)
PICTURE_MODES = set(guided_validator.PICTURE_MODES)
LEARNER_CONTENT_KEYS_FORBIDDEN_IN_BLUEPRINT = {
    "prompt", "options", "reference_answer", "reference_answers", "correct_option_index",
    "passage", "episode_id", "visual_spec", "answer_map", "response_fields",
}
MIN_DISTINCT_MODES_PER_FORM = 20
MIN_DISTINCT_TASK_FAMILIES_PER_FORM = 21
MIN_DISTINCT_CAPABILITIES_PER_FORM = 20
MAX_PAIRWISE_SAME_SLOT_MODE_RATIO = 0.25


class Unit04FormV3CReducedSupportBlueprintError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_form(repo_root: Path | str | None, form_number: int) -> dict[str, Any]:
    path = _root(repo_root) / "product" / "a1fs_v1_2_1" / BLUEPRINT_NAMES[form_number]
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
    raise Unit04FormV3CReducedSupportBlueprintError(f"QUESTION_NUMBER_OUT_OF_RANGE:{number}")


def _validate_provenance(payload: dict[str, Any], form_number: int) -> None:
    provenance = payload.get("authoring_provenance") or {}
    required = {
        "assessment_blueprint_author": "GPT-5.6_SOL_DIRECT_DESIGN",
        "response_mode_selection_author": "GPT-5.6_SOL_DIRECT_DESIGN",
        "task_family_selection_author": "GPT-5.6_SOL_DIRECT_DESIGN",
        "quota_family_selection_author": "GPT-5.6_SOL_DIRECT_DESIGN",
        "learner_content_authoring_stage": "NOT_STARTED_BLUEPRINT_ONLY",
    }
    for key, value in required.items():
        if provenance.get(key) != value:
            raise Unit04FormV3CReducedSupportBlueprintError(
                f"AUTHORING_PROVENANCE_DRIFT:F{form_number:02d}:{key}"
            )
    for key in (
        "python_blueprint_generation_used", "python_response_mode_assignment_used",
        "python_task_family_assignment_used", "python_learner_content_authoring_used",
        "legacy_python_task_builder_used",
    ):
        if provenance.get(key) is not False:
            raise Unit04FormV3CReducedSupportBlueprintError(
                f"FORBIDDEN_PYTHON_AUTHORING_ROLE:F{form_number:02d}:{key}"
            )


def validate_blueprint_form05_08(repo_root: Path | str | None = None) -> dict[str, Any]:
    expected_context_slots = {
        slot: dict(spec["question_load"]) for slot, spec in base_contract.CONTEXT_SLOT_CONTRACT.items()
    }
    expected_quotas = base_contract.STAGE_FAMILY_QUOTAS["REDUCED_SUPPORT"]
    mode_sequences: dict[int, tuple[str, ...]] = {}
    family_sequences: set[tuple[str, ...]] = set()
    capability_sequences: set[tuple[str, ...]] = set()
    all_modes: Counter[str] = Counter()
    form_reports: list[dict[str, Any]] = []

    for form_number in EXPECTED_FORMS:
        payload = _load_form(repo_root, form_number)
        if payload.get("schema_version") != "a1fs.v1.u04.formv3c.reduced_support_blueprint.v1":
            raise Unit04FormV3CReducedSupportBlueprintError(f"SCHEMA_VERSION_DRIFT:F{form_number:02d}")
        if payload.get("program_id") != PROGRAM_ID or payload.get("unit_id") != UNIT_ID:
            raise Unit04FormV3CReducedSupportBlueprintError(f"PROGRAM_OR_UNIT_DRIFT:F{form_number:02d}")
        if payload.get("task_id") != TASK_ID or payload.get("status") != BLUEPRINT_STATUS:
            raise Unit04FormV3CReducedSupportBlueprintError(f"TASK_OR_STATUS_DRIFT:F{form_number:02d}")
        _validate_provenance(payload, form_number)

        stage = payload.get("stage_contract") or {}
        if stage.get("stage") != "REDUCED_SUPPORT" or stage.get("support_level") != "MEDIUM":
            raise Unit04FormV3CReducedSupportBlueprintError(f"STAGE_SUPPORT_DRIFT:F{form_number:02d}")
        if stage.get("tasks_per_form") != 40 or stage.get("section_counts") != base_contract.SECTION_COUNTS:
            raise Unit04FormV3CReducedSupportBlueprintError(f"STAGE_COUNT_DRIFT:F{form_number:02d}")
        if stage.get("context_slots") != expected_context_slots:
            raise Unit04FormV3CReducedSupportBlueprintError(f"CONTEXT_SLOT_CONTRACT_DRIFT:F{form_number:02d}")
        if stage.get("current360_passage_selection_stage") != "AFTER_BLUEPRINT_ACCEPTANCE":
            raise Unit04FormV3CReducedSupportBlueprintError(f"CURRENT360_SELECTION_STAGE_DRIFT:F{form_number:02d}")
        if stage.get("answer_option_authoring_stage") != "AFTER_CURRENT360_BINDING_BY_GPT5_6":
            raise Unit04FormV3CReducedSupportBlueprintError(f"ANSWER_AUTHORING_STAGE_DRIFT:F{form_number:02d}")
        if stage.get("output_policy") != "ONE_TO_TWO_CONNECTED_A1_SENTENCES":
            raise Unit04FormV3CReducedSupportBlueprintError(f"REDUCED_SUPPORT_OUTPUT_DRIFT:F{form_number:02d}")

        form = payload.get("form") or {}
        if form.get("form_number") != form_number or form.get("form_id") != f"U04-FORMV3C-F{form_number:02d}":
            raise Unit04FormV3CReducedSupportBlueprintError(f"FORM_IDENTITY_DRIFT:F{form_number:02d}")
        if form.get("stage") != "REDUCED_SUPPORT" or form.get("support_level") != "MEDIUM":
            raise Unit04FormV3CReducedSupportBlueprintError(f"FORM_STAGE_SUPPORT_DRIFT:F{form_number:02d}")
        tasks = list(form.get("tasks") or [])
        if len(tasks) != 40:
            raise Unit04FormV3CReducedSupportBlueprintError(f"TASK_COUNT_DRIFT:F{form_number:02d}:{len(tasks)}")

        section_counts: Counter[str] = Counter()
        context_load = {slot: Counter() for slot in base_contract.CONTEXT_SLOT_CONTRACT}
        quota_counts = {section: Counter() for section in base_contract.SECTION_ORDER}
        modes: list[str] = []
        families: list[str] = []
        capabilities: list[str] = []
        response_fields = 0
        picture_tasks = 0

        for expected_number, task in enumerate(tasks, start=1):
            qid = f"F{form_number:02d}:Q{expected_number:02d}"
            if task.get("question_number") != expected_number:
                raise Unit04FormV3CReducedSupportBlueprintError(f"QUESTION_NUMBER_DRIFT:{qid}")
            expected_section, expected_context = _expected_section_context(expected_number)
            if task.get("section") != expected_section or task.get("context_role") != expected_context:
                raise Unit04FormV3CReducedSupportBlueprintError(f"SECTION_CONTEXT_DRIFT:{qid}")
            if any(key in task for key in LEARNER_CONTENT_KEYS_FORBIDDEN_IN_BLUEPRINT):
                raise Unit04FormV3CReducedSupportBlueprintError(f"LEARNER_CONTENT_PRESENT_IN_BLUEPRINT:{qid}")
            if task.get("source_evidence_required") is not True:
                raise Unit04FormV3CReducedSupportBlueprintError(f"SOURCE_EVIDENCE_NOT_REQUIRED:{qid}")

            mode = str(task.get("response_mode") or "")
            quota_family = str(task.get("quota_family") or "")
            family = str(task.get("task_family") or "")
            capability = str(task.get("assessment_capability") or "")
            if mode not in EXPECTED_RESPONSE_MODES or not quota_family or not family or not capability:
                raise Unit04FormV3CReducedSupportBlueprintError(f"TASK_DIMENSION_INVALID:{qid}")
            fields = task.get("response_field_count")
            if not isinstance(fields, int) or fields < 1:
                raise Unit04FormV3CReducedSupportBlueprintError(f"RESPONSE_FIELD_COUNT_INVALID:{qid}")
            picture_required = task.get("picture_required")
            if (mode in PICTURE_MODES) != (picture_required is True):
                raise Unit04FormV3CReducedSupportBlueprintError(f"PICTURE_MODE_BINDING_INVALID:{qid}")

            section_counts[expected_section] += 1
            context_load[expected_context][expected_section] += 1
            quota_counts[expected_section][quota_family] += 1
            modes.append(mode)
            families.append(family)
            capabilities.append(capability)
            response_fields += fields
            picture_tasks += int(picture_required is True)
            all_modes[mode] += 1

        if dict(section_counts) != base_contract.SECTION_COUNTS:
            raise Unit04FormV3CReducedSupportBlueprintError(f"SECTION_COUNTS_DRIFT:F{form_number:02d}")
        actual_context = {slot: dict(counts) for slot, counts in context_load.items()}
        if actual_context != expected_context_slots:
            raise Unit04FormV3CReducedSupportBlueprintError(f"CONTEXT_LOAD_DRIFT:F{form_number:02d}:{actual_context}")
        for section in base_contract.SECTION_ORDER:
            if dict(quota_counts[section]) != expected_quotas[section]:
                raise Unit04FormV3CReducedSupportBlueprintError(
                    f"REDUCED_SUPPORT_QUOTA_DRIFT:F{form_number:02d}:{section}:{dict(quota_counts[section])}"
                )
        if len(set(modes)) < MIN_DISTINCT_MODES_PER_FORM:
            raise Unit04FormV3CReducedSupportBlueprintError(f"RESPONSE_MODE_BREADTH_TOO_LOW:F{form_number:02d}")
        if len(set(families)) < MIN_DISTINCT_TASK_FAMILIES_PER_FORM:
            raise Unit04FormV3CReducedSupportBlueprintError(f"TASK_FAMILY_BREADTH_TOO_LOW:F{form_number:02d}")
        if len(set(capabilities)) < MIN_DISTINCT_CAPABILITIES_PER_FORM:
            raise Unit04FormV3CReducedSupportBlueprintError(f"CAPABILITY_BREADTH_TOO_LOW:F{form_number:02d}")
        if response_fields <= 40:
            raise Unit04FormV3CReducedSupportBlueprintError(f"MULTI_FIELD_MODEL_NOT_MATERIALIZED:F{form_number:02d}")
        if picture_tasks < 2:
            raise Unit04FormV3CReducedSupportBlueprintError(f"PICTURE_TASK_BREADTH_TOO_LOW:F{form_number:02d}")

        mode_sequences[form_number] = tuple(modes)
        family_sequences.add(tuple(families))
        capability_sequences.add(tuple(capabilities))
        form_reports.append({
            "form_number": form_number,
            "distinct_response_mode_count": len(set(modes)),
            "distinct_task_family_count": len(set(families)),
            "distinct_capability_count": len(set(capabilities)),
            "response_field_count": response_fields,
            "picture_task_count": picture_tasks,
            "response_mode_counts": dict(sorted(Counter(modes).items())),
        })

    if set(all_modes) != EXPECTED_RESPONSE_MODES:
        raise Unit04FormV3CReducedSupportBlueprintError(
            f"FORM05_08_RESPONSE_MODE_COVERAGE_DRIFT:{sorted(set(all_modes))}"
        )
    if len(set(mode_sequences.values())) != 4 or len(family_sequences) != 4 or len(capability_sequences) != 4:
        raise Unit04FormV3CReducedSupportBlueprintError("FORM_SIGNATURE_DUPLICATE")

    fixed_slots = [
        index + 1 for index in range(40)
        if len({mode_sequences[number][index] for number in EXPECTED_FORMS}) == 1
    ]
    if fixed_slots:
        raise Unit04FormV3CReducedSupportBlueprintError(f"FIXED_RESPONSE_MODE_SLOTS:{fixed_slots}")

    pairwise: list[dict[str, Any]] = []
    for left, right in combinations(EXPECTED_FORMS, 2):
        same = sum(a == b for a, b in zip(mode_sequences[left], mode_sequences[right]))
        ratio = same / 40
        if ratio > MAX_PAIRWISE_SAME_SLOT_MODE_RATIO:
            raise Unit04FormV3CReducedSupportBlueprintError(
                f"FORM_RESPONSE_SIGNATURE_TOO_SIMILAR:F{left:02d}:F{right:02d}:{ratio:.3f}"
            )
        pairwise.append({"left": left, "right": right, "same_slot_count": same, "same_slot_ratio": ratio})

    guided_payload = guided_validator._load(_root(repo_root))
    guided_mode_sequences = {
        int(form["form_number"]): tuple(task["response_mode"] for task in form["tasks"])
        for form in guided_payload["forms"]
    }
    for reduced_number, reduced_sequence in mode_sequences.items():
        if reduced_sequence in guided_mode_sequences.values():
            raise Unit04FormV3CReducedSupportBlueprintError(
                f"CROSS_STAGE_RESPONSE_MODE_SEQUENCE_DUPLICATE:F{reduced_number:02d}"
            )

    if base_contract.CAMBRIDGE_BOUNDARY.get("grammar_ceiling") != "A1":
        raise Unit04FormV3CReducedSupportBlueprintError("A1_CEILING_DRIFT")
    if base_contract.CAMBRIDGE_BOUNDARY.get("a2_a2plus_unlocked") is not False:
        raise Unit04FormV3CReducedSupportBlueprintError("A2_A2PLUS_UNLOCKED")
    if base_contract.CAMBRIDGE_BOUNDARY.get("listening_modified") is not False:
        raise Unit04FormV3CReducedSupportBlueprintError("LISTENING_CHANGED")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "stage": "REDUCED_SUPPORT",
        "support_level": "MEDIUM",
        "form_count": 4,
        "task_count": 160,
        "response_mode_coverage_count": len(all_modes),
        "response_mode_coverage": sorted(all_modes),
        "fixed_response_mode_slot_count": len(fixed_slots),
        "max_pairwise_same_slot_mode_ratio": max(row["same_slot_ratio"] for row in pairwise),
        "pairwise_response_signature": pairwise,
        "forms": form_reports,
        "python_blueprint_generation_used": False,
        "python_response_mode_assignment_used": False,
        "python_task_family_assignment_used": False,
        "python_learner_content_authoring_used": False,
        "legacy_python_task_builder_used": False,
        "a2_a2plus_unlocked": False,
        "listening_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(validate_blueprint_form05_08(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
