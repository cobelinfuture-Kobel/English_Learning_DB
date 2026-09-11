from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as contract
from product.a1fs_v1_2_1 import u04formv3c_diversified_assessment_blueprint_validator as blueprint
from product.a1fs_v1_2_1 import u04neb01r1_strict_a1_boundary_audit_108 as boundary
from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as current360

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical validation only over GPT-5.6-direct-authored diversified FormV3C assets. "
    "This module does not select Current360 episodes, assign response modes or task families, "
    "compose learner wording, author answers or distractors, shuffle options, or repair content."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FORMV3C_A1_GPT56Current360BindingAndDirectAuthoring_Form01To04"
FORM_STATUS = "GPT5_6_DIRECT_AUTHORED_DIVERSIFIED_STATIC_FORM"
STATUS = "PASS_A1FS_V1_U04FORMV3C_DIRECT_AUTHORED_FORM01_TO04_MECHANICAL_VALIDATION"
REVISION = "FORMV3C_GUIDED_DIVERSIFIED_DIRECT_AUTHORING_VALIDATOR_V1"
NEXT_SHORT_STEP = "A1FS-V1-U04FORMV3C_A2_PictureAssetMaterializationAndDiversifiedRendererIntegration"
EXPECTED_FORMS = (1, 2, 3, 4)
FORM_ASSET_NAMES = {
    1: "u04formv3c_direct_authored_form01.json",
    2: "u04formv3c_direct_authored_form02.json",
    3: "u04formv3c_direct_authored_form03.json",
    4: "u04formv3c_direct_authored_form04.json",
}
CHOICE_MODES = {"SELECT_ONE", "GIST_BEST_TITLE"}
MATCHING_MODES = {"MATCHING", "MULTIPLE_MATCHING", "REFERENCE_MATCHING"}
FIELD_MODES = {"NOTE_COMPLETION", "TABLE_COMPLETION"}
PICTURE_MODES = {"PICTURE_POSITION", "PICTURE_LABEL", "PICTURE_DIFFERENCE"}
SCALAR_MODES = {
    "ASK_A_QUESTION", "DIALOGUE_RESPONSE", "FACT_CORRECTION", "ONE_TO_THREE_WORDS",
    "ONE_WORD_GAP", "RECONSTRUCTION", "SENTENCE_COMPLETION", "SHORT_ANSWER",
    "SHORT_RETELL", "SPEAK_SHORT_RESPONSE", "WRITE_SENTENCE",
}


class Unit04FormV3CDirectAuthoringError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", str(text), flags=re.I))


def _load_asset(root: Path, form_number: int) -> dict[str, Any]:
    path = root / "product" / "a1fs_v1_2_1" / FORM_ASSET_NAMES[form_number]
    if not path.is_file():
        raise Unit04FormV3CDirectAuthoringError(f"FORM_ASSET_MISSING:F{form_number:02d}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != "a1fs.v1.u04.formv3c.direct_authored_form.v1":
        raise Unit04FormV3CDirectAuthoringError(f"FORM_SCHEMA_DRIFT:F{form_number:02d}")
    if payload.get("program_id") != PROGRAM_ID or payload.get("unit_id") != UNIT_ID:
        raise Unit04FormV3CDirectAuthoringError(f"PROGRAM_OR_UNIT_DRIFT:F{form_number:02d}")
    if payload.get("task_id") != TASK_ID or payload.get("status") != FORM_STATUS:
        raise Unit04FormV3CDirectAuthoringError(f"TASK_OR_STATUS_DRIFT:F{form_number:02d}")
    provenance = payload.get("authoring_provenance") or {}
    expected = {
        "assessment_blueprint_author": "GPT-5.6_SOL_DIRECT_DESIGN",
        "current360_binding_author": "GPT-5.6_SOL_DIRECT_DESIGN",
        "learner_content_author": "GPT-5.6_SOL_DIRECT_AUTHORING",
        "answer_option_author": "GPT-5.6_SOL_DIRECT_AUTHORING",
        "semantic_review": "GPT-5.6_SOL_SECOND_PASS_COMPLETE",
    }
    for key, value in expected.items():
        if provenance.get(key) != value:
            raise Unit04FormV3CDirectAuthoringError(f"AUTHORING_PROVENANCE_DRIFT:F{form_number:02d}:{key}")
    for key in (
        "python_blueprint_generation_used", "python_response_mode_assignment_used",
        "python_task_family_assignment_used", "python_learner_content_authoring_used",
        "python_answer_option_authoring_used", "legacy_python_task_builder_used",
    ):
        if provenance.get(key) is not False:
            raise Unit04FormV3CDirectAuthoringError(f"FORBIDDEN_PYTHON_AUTHORING_ROLE:F{form_number:02d}:{key}")
    return payload


def _current360_by_id() -> dict[str, dict[str, Any]]:
    report = current360.build_unit04_neb02_natural_episode_bank_360()
    if report.get("status") != current360.STATUS:
        raise Unit04FormV3CDirectAuthoringError("CURRENT360_SOURCE_NOT_PASS")
    rows = {str(row["episode_id"]): dict(row) for row in report.get("effective_episodes") or []}
    if len(rows) != 360:
        raise Unit04FormV3CDirectAuthoringError(f"CURRENT360_COUNT_DRIFT:{len(rows)}")
    return rows


def _assessed_strings(task: dict[str, Any]) -> list[str]:
    values: list[str] = []
    reference = task.get("reference_answer")
    if reference is not None:
        values.append(str(reference))
    values.extend(str(v) for v in task.get("reference_answers") or [])
    values.extend(str(row.get("answer") or "") for row in task.get("response_fields") or [])
    values.extend(str(v) for v in task.get("expected_actions") or [])
    mode = str(task.get("response_mode") or "")
    if mode in MATCHING_MODES:
        right = list(task.get("right_options") or [])
        for index in task.get("answer_map") or []:
            if isinstance(index, int) and 0 <= index < len(right):
                values.append(str(right[index]))
    if mode == "ORDER_SEQUENCE":
        values.extend(str(v) for v in task.get("sequence_items") or [])
    return [value for value in values if value.strip()]


def _visible_strings(task: dict[str, Any]) -> list[str]:
    values = [str(task.get("prompt") or "")]
    for key in ("options", "left_items", "right_options", "sequence_items"):
        values.extend(str(v) for v in task.get(key) or [])
    values.extend(str(row.get("label") or "") for row in task.get("response_fields") or [])
    return [value for value in values if value.strip()]


def _validate_response_schema(task: dict[str, Any], qid: str) -> tuple[list[int], int]:
    mode = str(task["response_mode"])
    fields = int(task["response_field_count"])
    choice_positions: list[int] = []
    picture_pending = 0

    is_dialogue_choice = mode == "DIALOGUE_RESPONSE" and task.get("dialogue_mode") == "select_one"
    if mode in CHOICE_MODES or is_dialogue_choice:
        options = task.get("options")
        if not isinstance(options, list) or len(options) != 4:
            raise Unit04FormV3CDirectAuthoringError(f"CHOICE_OPTION_COUNT_INVALID:{qid}")
        if len({_normalized(value) for value in options}) != 4:
            raise Unit04FormV3CDirectAuthoringError(f"CHOICE_OPTION_DUPLICATE:{qid}")
        correct = task.get("correct_option_index")
        if not isinstance(correct, int) or correct not in range(4):
            raise Unit04FormV3CDirectAuthoringError(f"CHOICE_INDEX_INVALID:{qid}")
        if str(options[correct]).strip() != str(task.get("reference_answer") or "").strip():
            raise Unit04FormV3CDirectAuthoringError(f"CHOICE_REFERENCE_MISMATCH:{qid}")
        choice_positions.append(correct)
    elif mode in MATCHING_MODES:
        left = task.get("left_items")
        right = task.get("right_options")
        answer_map = task.get("answer_map")
        if not isinstance(left, list) or len(left) != fields:
            raise Unit04FormV3CDirectAuthoringError(f"MATCHING_LEFT_COUNT_INVALID:{qid}")
        if not isinstance(right, list) or not right or len({_normalized(v) for v in right}) != len(right):
            raise Unit04FormV3CDirectAuthoringError(f"MATCHING_RIGHT_INVALID:{qid}")
        if not isinstance(answer_map, list) or len(answer_map) != fields:
            raise Unit04FormV3CDirectAuthoringError(f"MATCHING_MAP_COUNT_INVALID:{qid}")
        if any(not isinstance(index, int) or index not in range(len(right)) for index in answer_map):
            raise Unit04FormV3CDirectAuthoringError(f"MATCHING_MAP_INDEX_INVALID:{qid}")
    elif mode in FIELD_MODES:
        rows = task.get("response_fields")
        if not isinstance(rows, list) or len(rows) != fields:
            raise Unit04FormV3CDirectAuthoringError(f"RESPONSE_FIELD_COUNT_INVALID:{qid}")
        if any(not str(row.get("label") or "").strip() or not str(row.get("answer") or "").strip() for row in rows):
            raise Unit04FormV3CDirectAuthoringError(f"RESPONSE_FIELD_EMPTY:{qid}")
    elif mode == "PICTURE_POSITION":
        spec = task.get("visual_spec") or {}
        actions = task.get("expected_actions")
        if spec.get("status") != "SPEC_AUTHORED_ASSET_PENDING" or not isinstance(actions, list) or len(actions) != fields:
            raise Unit04FormV3CDirectAuthoringError(f"PICTURE_POSITION_SPEC_INVALID:{qid}")
        picture_pending = 1
    elif mode in {"PICTURE_LABEL", "PICTURE_DIFFERENCE"}:
        spec = task.get("visual_spec") or {}
        answers = task.get("reference_answers")
        if spec.get("status") != "SPEC_AUTHORED_ASSET_PENDING" or not isinstance(answers, list) or len(answers) != fields:
            raise Unit04FormV3CDirectAuthoringError(f"PICTURE_SPEC_INVALID:{qid}")
        picture_pending = 1
    elif mode == "ORDER_SEQUENCE":
        sequence = task.get("sequence_items")
        order = task.get("correct_order")
        if not isinstance(sequence, list) or len(sequence) != fields:
            raise Unit04FormV3CDirectAuthoringError(f"SEQUENCE_ITEM_COUNT_INVALID:{qid}")
        if not isinstance(order, list) or sorted(order) != list(range(fields)):
            raise Unit04FormV3CDirectAuthoringError(f"SEQUENCE_ORDER_INVALID:{qid}")
    elif mode in SCALAR_MODES:
        reference = str(task.get("reference_answer") or "").strip()
        if not reference:
            raise Unit04FormV3CDirectAuthoringError(f"SCALAR_REFERENCE_EMPTY:{qid}")
        if mode == "DIALOGUE_RESPONSE" and task.get("dialogue_mode") not in {"short_text", "select_one"}:
            raise Unit04FormV3CDirectAuthoringError(f"DIALOGUE_MODE_INVALID:{qid}")
    else:
        raise Unit04FormV3CDirectAuthoringError(f"UNKNOWN_RESPONSE_MODE:{qid}:{mode}")

    if mode == "ONE_WORD_GAP" and len(str(task.get("reference_answer") or "").split()) != 1:
        raise Unit04FormV3CDirectAuthoringError(f"ONE_WORD_GAP_ANSWER_LENGTH:{qid}")
    if mode == "ONE_TO_THREE_WORDS":
        word_count = len(str(task.get("reference_answer") or "").replace(".", "").split())
        if not 1 <= word_count <= 3:
            raise Unit04FormV3CDirectAuthoringError(f"ONE_TO_THREE_WORD_ANSWER_LENGTH:{qid}:{word_count}")
    return choice_positions, picture_pending


def validate_form01_04(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    blueprint_report = blueprint.validate_blueprint(root)
    if blueprint_report.get("status") != blueprint.STATUS:
        raise Unit04FormV3CDirectAuthoringError("BLUEPRINT_NOT_PASS")
    blueprint_payload = blueprint._load(root)
    blueprint_forms = {int(row["form_number"]): row for row in blueprint_payload["forms"]}
    current_rows = _current360_by_id()

    form_reports: list[dict[str, Any]] = []
    all_episode_ids: list[str] = []
    all_prompts: list[tuple[str, str]] = []
    all_response_modes: Counter[str] = Counter()
    picture_pending_count = 0
    higher_exposure_lexemes = set(boundary.KNOWN_SCENE_REQUIRED_LEXICAL_EXPOSURE)

    for form_number in EXPECTED_FORMS:
        payload = _load_asset(root, form_number)
        form = payload.get("form") or {}
        if form.get("form_number") != form_number or form.get("form_id") != f"U04-FORMV3C-F{form_number:02d}":
            raise Unit04FormV3CDirectAuthoringError(f"FORM_IDENTITY_DRIFT:F{form_number:02d}")
        if form.get("stage") != "GUIDED" or form.get("support_level") != "HIGH":
            raise Unit04FormV3CDirectAuthoringError(f"FORM_STAGE_SUPPORT_DRIFT:F{form_number:02d}")

        contexts = list(form.get("contexts") or [])
        if len(contexts) != 6:
            raise Unit04FormV3CDirectAuthoringError(f"CONTEXT_COUNT_DRIFT:F{form_number:02d}:{len(contexts)}")
        context_by_slot = {str(row.get("slot")): dict(row) for row in contexts}
        if set(context_by_slot) != set(contract.CONTEXT_SLOT_CONTRACT) or len(context_by_slot) != 6:
            raise Unit04FormV3CDirectAuthoringError(f"CONTEXT_SLOT_DRIFT:F{form_number:02d}")
        episode_ids: list[str] = []
        target_relation_coverage: set[str] = set()
        for slot, row in context_by_slot.items():
            episode_id = str(row.get("episode_id") or "")
            source = current_rows.get(episode_id)
            if source is None:
                raise Unit04FormV3CDirectAuthoringError(f"CURRENT360_EPISODE_UNKNOWN:F{form_number:02d}:{slot}:{episode_id}")
            passage = str(row.get("passage") or "")
            if passage != str(source.get("passage") or ""):
                raise Unit04FormV3CDirectAuthoringError(f"CURRENT360_PASSAGE_NOT_EXACT:F{form_number:02d}:{slot}:{episode_id}")
            episode_ids.append(episode_id)
            target_relation_coverage.update(
                relation for relation in contract.TARGET_RELATIONS if _contains_surface(passage, relation)
            )
        if len(set(episode_ids)) != 6:
            raise Unit04FormV3CDirectAuthoringError(f"WITHIN_FORM_EPISODE_REUSE:F{form_number:02d}")
        if target_relation_coverage != set(contract.TARGET_RELATIONS):
            raise Unit04FormV3CDirectAuthoringError(
                f"TARGET_RELATION_COVERAGE_DRIFT:F{form_number:02d}:{sorted(target_relation_coverage)}"
            )
        all_episode_ids.extend(episode_ids)

        tasks = list(form.get("tasks") or [])
        blueprint_tasks = list(blueprint_forms[form_number].get("tasks") or [])
        if len(tasks) != 40 or len(blueprint_tasks) != 40:
            raise Unit04FormV3CDirectAuthoringError(f"TASK_COUNT_DRIFT:F{form_number:02d}")
        section_counts: Counter[str] = Counter()
        context_load = {slot: Counter() for slot in contract.CONTEXT_SLOT_CONTRACT}
        choice_positions: list[int] = []
        form_picture_pending = 0
        form_modes: Counter[str] = Counter()

        for expected_number, (task, planned) in enumerate(zip(tasks, blueprint_tasks), start=1):
            qid = f"U04-FORMV3C-F{form_number:02d}-Q{expected_number:02d}"
            if task.get("question_id") != qid or task.get("question_number") != expected_number:
                raise Unit04FormV3CDirectAuthoringError(f"QUESTION_IDENTITY_DRIFT:{qid}")
            for key in (
                "question_number", "section", "context_role", "skill", "assessment_capability",
                "task_family", "response_mode", "response_field_count", "picture_required",
            ):
                if task.get(key) != planned.get(key):
                    raise Unit04FormV3CDirectAuthoringError(f"BLUEPRINT_DIMENSION_DRIFT:{qid}:{key}")
            prompt = str(task.get("prompt") or "").strip()
            if not prompt:
                raise Unit04FormV3CDirectAuthoringError(f"PROMPT_EMPTY:{qid}")
            all_prompts.append((qid, prompt))
            visible = " ".join(_visible_strings(task)).casefold()
            for phrase in contract.LEARNER_LANGUAGE_FORBIDDEN_PHRASES:
                if phrase.casefold() in visible:
                    raise Unit04FormV3CDirectAuthoringError(f"FORBIDDEN_LEARNER_LANGUAGE:{qid}:{phrase}")

            positions, pending = _validate_response_schema(task, qid)
            choice_positions.extend(positions)
            form_picture_pending += pending
            mode = str(task["response_mode"])
            form_modes[mode] += 1
            all_response_modes[mode] += 1
            section = str(task["section"])
            slot = str(task["context_role"])
            section_counts[section] += 1
            context_load[slot][section] += 1

            passage = str(context_by_slot[slot]["passage"])
            if mode == "RECONSTRUCTION":
                reference = _normalized(str(task.get("reference_answer") or ""))
                if reference and reference in _normalized(passage):
                    raise Unit04FormV3CDirectAuthoringError(f"RECONSTRUCTION_REFERENCE_VERBATIM_LEAK:{qid}")

            assessed = _assessed_strings(task)
            for answer in assessed:
                for relation in contract.SUPPORT_RELATIONS:
                    if _contains_surface(answer, relation):
                        raise Unit04FormV3CDirectAuthoringError(f"SUPPORT_RELATION_ASSESSED:{qid}:{relation}:{answer}")
                for lexeme in higher_exposure_lexemes:
                    if _contains_surface(answer, lexeme):
                        raise Unit04FormV3CDirectAuthoringError(f"HIGHER_LEXICAL_EXPOSURE_ASSESSED:{qid}:{lexeme}:{answer}")

        if dict(section_counts) != contract.SECTION_COUNTS:
            raise Unit04FormV3CDirectAuthoringError(f"SECTION_COUNTS_DRIFT:F{form_number:02d}:{dict(section_counts)}")
        expected_context = {slot: dict(spec["question_load"]) for slot, spec in contract.CONTEXT_SLOT_CONTRACT.items()}
        actual_context = {slot: dict(counts) for slot, counts in context_load.items()}
        if actual_context != expected_context:
            raise Unit04FormV3CDirectAuthoringError(f"CONTEXT_LOAD_DRIFT:F{form_number:02d}:{actual_context}")
        position_counts = Counter({index: 0 for index in range(4)})
        position_counts.update(choice_positions)
        if len([count for count in position_counts.values() if count > 0]) < 3:
            raise Unit04FormV3CDirectAuthoringError(f"CHOICE_POSITION_BREADTH_TOO_LOW:F{form_number:02d}:{dict(position_counts)}")
        if max(position_counts.values()) - min(position_counts.values()) > 1:
            raise Unit04FormV3CDirectAuthoringError(f"CHOICE_POSITION_IMBALANCE:F{form_number:02d}:{dict(position_counts)}")
        if form_picture_pending != 2:
            raise Unit04FormV3CDirectAuthoringError(f"PICTURE_PENDING_COUNT_DRIFT:F{form_number:02d}:{form_picture_pending}")
        picture_pending_count += form_picture_pending
        form_reports.append({
            "form_number": form_number,
            "context_count": 6,
            "task_count": 40,
            "distinct_response_mode_count": len(form_modes),
            "response_mode_counts": dict(sorted(form_modes.items())),
            "choice_position_counts": dict(sorted(position_counts.items())),
            "choice_position_max_delta": max(position_counts.values()) - min(position_counts.values()),
            "picture_asset_pending_count": form_picture_pending,
            "target_relation_coverage": sorted(target_relation_coverage),
            "episode_ids": episode_ids,
        })

    if len(all_episode_ids) != 24 or len(set(all_episode_ids)) != 24:
        raise Unit04FormV3CDirectAuthoringError(f"CROSS_FORM_EPISODE_REUSE:{len(all_episode_ids)}:{len(set(all_episode_ids))}")
    if set(all_response_modes) != blueprint.EXPECTED_RESPONSE_MODES:
        raise Unit04FormV3CDirectAuthoringError(f"RESPONSE_MODE_COVERAGE_DRIFT:{sorted(all_response_modes)}")
    normalized_prompt_map: dict[str, list[str]] = {}
    for qid, prompt in all_prompts:
        normalized_prompt_map.setdefault(_normalized(prompt), []).append(qid)
    duplicate_groups = [qids for normalized, qids in normalized_prompt_map.items() if normalized and len(qids) > 1]
    if duplicate_groups:
        raise Unit04FormV3CDirectAuthoringError(f"EXACT_PROMPT_DUPLICATES:{duplicate_groups}")
    if picture_pending_count != 8:
        raise Unit04FormV3CDirectAuthoringError(f"PICTURE_PENDING_TOTAL_DRIFT:{picture_pending_count}")
    if contract.CAMBRIDGE_BOUNDARY.get("a2_a2plus_unlocked") is not False:
        raise Unit04FormV3CDirectAuthoringError("A2_A2PLUS_UNLOCKED")
    if contract.CAMBRIDGE_BOUNDARY.get("listening_modified") is not False:
        raise Unit04FormV3CDirectAuthoringError("LISTENING_CHANGED")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_authority": {
            "blueprint": blueprint.TASK_ID,
            "current360": current360.TASK_ID,
        },
        "form_count": 4,
        "task_count": 160,
        "response_mode_coverage_count": len(all_response_modes),
        "response_mode_coverage": sorted(all_response_modes),
        "distinct_current360_episode_count": len(set(all_episode_ids)),
        "cross_form_episode_reuse_count": 0,
        "exact_prompt_duplicate_count": 0,
        "picture_asset_pending_count": picture_pending_count,
        "picture_asset_materialization_status": "PENDING",
        "human_visual_acceptance": "PENDING",
        "python_blueprint_generation_used": False,
        "python_response_mode_assignment_used": False,
        "python_task_family_assignment_used": False,
        "python_learner_content_authoring_used": False,
        "python_answer_option_authoring_used": False,
        "legacy_python_task_builder_used": False,
        "current360_passage_mutation_used": False,
        "formv3c_runtime_cutover": False,
        "current_fsv2_runtime_remains_active": True,
        "a2_a2plus_unlocked": False,
        "listening_modified": False,
        "forms": form_reports,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(validate_form01_04(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
