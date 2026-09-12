from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import a1fs_v1_core_response_mode_contract as core_contract
from product.a1fs_v1_2_1 import u04formv3c_reduced_support_current360_binding_validator as binding_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical validation only over GPT-5.6-direct-authored Unit04 Form05-08 learner overlays. "
    "Python does not compose prompts, answers, distractors, matching sets, or semantic repairs."
)

TASK_ID = "A1FS-V1-U04FORMV3C_GPT56DirectAuthoring_NoPicture_Form05To08"
STATUS = "PASS_A1FS_V1_U04FORMV3C_REDUCED_SUPPORT_DIRECT_AUTHORED_NO_PICTURE_FORM05_TO08"
REVISION = "FORMV3C_REDUCED_SUPPORT_DIRECT_AUTHORING_OVERLAY_VALIDATOR_V1"
EXPECTED_FORMS = (5, 6, 7, 8)
EXPECTED_ACTIVE_COUNTS = {5: 38, 6: 38, 7: 37, 8: 37}
EXPECTED_DEFERRED_COUNTS = {5: 2, 6: 2, 7: 3, 8: 3}
EXPECTED_ACTIVE_TOTAL = 150
EXPECTED_DEFERRED_TOTAL = 10
BLUEPRINT_TEMPLATE = "product/a1fs_v1_2_1/u04formv3c_reduced_support_blueprint_form{number:02d}.json"
OVERLAY_TEMPLATE = "product/a1fs_v1_2_1/u04formv3c_reduced_support_direct_authored_overlay_form{number:02d}.json"
PICTURE_MODES = frozenset({"PICTURE_POSITION", "PICTURE_LABEL", "PICTURE_DIFFERENCE"})
SUPPORT_RELATIONS = ("next to", "in front of")
FORBIDDEN_LEARNER_PHRASES = (
    "response mode", "task family", "assessment capability", "target relation",
    "core response", "learner surface", "source evidence", "grammar level",
)


class Unit04ReducedSupportDirectAuthoringError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _visible_and_assessed_strings(task: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("prompt", "reference_answer"):
        value = task.get(key)
        if value:
            values.append(str(value))
    for key in ("options", "left_items", "right_options", "sequence_items"):
        values.extend(str(value) for value in task.get(key) or [])
    for row in task.get("response_fields") or []:
        values.append(str(row.get("label") or ""))
        values.append(str(row.get("answer") or ""))
    return [value for value in values if value.strip()]


def _expected_core_mode(blueprint_task: dict[str, Any], overlay_task: dict[str, Any]) -> str | None:
    legacy_mode = str(blueprint_task.get("response_mode") or "")
    if legacy_mode in PICTURE_MODES:
        return None
    if legacy_mode == "DIALOGUE_RESPONSE":
        dialogue_mode = str(overlay_task.get("dialogue_mode") or "short_text")
        if dialogue_mode == "select_one":
            return "SELECT"
        if dialogue_mode == "short_text":
            return "TEXT_ENTRY"
        raise Unit04ReducedSupportDirectAuthoringError(
            f"DIALOGUE_MODE_INVALID:{dialogue_mode}"
        )
    try:
        return core_contract.project_core_response_mode({"response_mode": legacy_mode})
    except core_contract.CoreResponseModeContractError as exc:
        raise Unit04ReducedSupportDirectAuthoringError(str(exc)) from exc


def _validate_active_schema(task: dict[str, Any], qid: str) -> int | None:
    mode = str(task.get("core_response_mode") or "")
    response_format = str(task.get("response_format") or "")
    if mode not in core_contract.CORE_RESPONSE_MODES:
        raise Unit04ReducedSupportDirectAuthoringError(f"CORE_MODE_INVALID:{qid}:{mode}")
    if not response_format or response_format == "DEFERRED":
        raise Unit04ReducedSupportDirectAuthoringError(f"RESPONSE_FORMAT_INVALID:{qid}")
    prompt = str(task.get("prompt") or "").strip()
    if not prompt:
        raise Unit04ReducedSupportDirectAuthoringError(f"PROMPT_EMPTY:{qid}")

    choice_position: int | None = None
    if mode == "SELECT":
        options = task.get("options")
        if not isinstance(options, list) or len(options) != 4:
            raise Unit04ReducedSupportDirectAuthoringError(f"SELECT_OPTION_COUNT:{qid}")
        if len({_normalized(value) for value in options}) != 4:
            raise Unit04ReducedSupportDirectAuthoringError(f"SELECT_OPTION_DUPLICATE:{qid}")
        correct = task.get("correct_option_index")
        if not isinstance(correct, int) or correct not in range(4):
            raise Unit04ReducedSupportDirectAuthoringError(f"SELECT_INDEX_INVALID:{qid}")
        if str(options[correct]).strip() != str(task.get("reference_answer") or "").strip():
            raise Unit04ReducedSupportDirectAuthoringError(f"SELECT_REFERENCE_MISMATCH:{qid}")
        choice_position = correct
    elif mode == "MATCH":
        left = task.get("left_items")
        right = task.get("right_options")
        answer_map = task.get("answer_map")
        if not isinstance(left, list) or len(left) != 3:
            raise Unit04ReducedSupportDirectAuthoringError(f"MATCH_LEFT_COUNT:{qid}")
        if not isinstance(right, list) or len(right) != 3 or len({_normalized(v) for v in right}) != 3:
            raise Unit04ReducedSupportDirectAuthoringError(f"MATCH_RIGHT_INVALID:{qid}")
        if not isinstance(answer_map, list) or len(answer_map) != 3:
            raise Unit04ReducedSupportDirectAuthoringError(f"MATCH_MAP_COUNT:{qid}")
        if any(not isinstance(index, int) or index not in range(3) for index in answer_map):
            raise Unit04ReducedSupportDirectAuthoringError(f"MATCH_MAP_INDEX:{qid}")
    elif mode == "STRUCTURED_ENTRY":
        rows = task.get("response_fields")
        if not isinstance(rows, list) or len(rows) != 3:
            raise Unit04ReducedSupportDirectAuthoringError(f"STRUCTURED_FIELD_COUNT:{qid}")
        if any(not str(row.get("label") or "").strip() or not str(row.get("answer") or "").strip() for row in rows):
            raise Unit04ReducedSupportDirectAuthoringError(f"STRUCTURED_FIELD_EMPTY:{qid}")
    elif mode == "ORDER":
        sequence = task.get("sequence_items")
        order = task.get("correct_order")
        if not isinstance(sequence, list) or len(sequence) != 3:
            raise Unit04ReducedSupportDirectAuthoringError(f"ORDER_ITEM_COUNT:{qid}")
        if not isinstance(order, list) or sorted(order) != [0, 1, 2]:
            raise Unit04ReducedSupportDirectAuthoringError(f"ORDER_MAPPING_INVALID:{qid}")
    elif mode in {"TEXT_ENTRY", "SPEAK"}:
        if not str(task.get("reference_answer") or "").strip():
            raise Unit04ReducedSupportDirectAuthoringError(f"REFERENCE_EMPTY:{qid}")
    return choice_position


def validate_form05_08(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    binding_report = binding_validator.validate_binding(root)
    if binding_report.get("status") != binding_validator.STATUS:
        raise Unit04ReducedSupportDirectAuthoringError("BINDING_NOT_PASS")
    core_report = core_contract.validate_contract()
    if core_report.get("status") != core_contract.STATUS:
        raise Unit04ReducedSupportDirectAuthoringError("CORE_CONTRACT_NOT_PASS")

    prompt_seen: dict[str, str] = {}
    global_core_counts: Counter[str] = Counter()
    active_total = 0
    deferred_total = 0
    form_reports: list[dict[str, Any]] = []

    for form_number in EXPECTED_FORMS:
        blueprint_payload = _load(root / BLUEPRINT_TEMPLATE.format(number=form_number))
        overlay = _load(root / OVERLAY_TEMPLATE.format(number=form_number))
        blueprint_form = blueprint_payload.get("form") or {}
        if overlay.get("schema_version") != "a1fs.v1.u04.formv3c.reduced_support_direct_authored_overlay.v1":
            raise Unit04ReducedSupportDirectAuthoringError(f"OVERLAY_SCHEMA_DRIFT:F{form_number:02d}")
        if overlay.get("task_id") != TASK_ID or overlay.get("form_number") != form_number:
            raise Unit04ReducedSupportDirectAuthoringError(f"OVERLAY_IDENTITY_DRIFT:F{form_number:02d}")
        provenance = overlay.get("authoring_provenance") or {}
        expected_provenance = {
            "learner_content_author": "GPT-5.6_SOL_DIRECT_AUTHORING",
            "answer_option_author": "GPT-5.6_SOL_DIRECT_AUTHORING",
            "semantic_review": "GPT-5.6_SOL_SECOND_PASS_COMPLETE",
            "python_learner_content_authoring_used": False,
            "python_answer_option_authoring_used": False,
        }
        for key, value in expected_provenance.items():
            if provenance.get(key) != value:
                raise Unit04ReducedSupportDirectAuthoringError(f"PROVENANCE_DRIFT:F{form_number:02d}:{key}")

        blueprint_tasks = list(blueprint_form.get("tasks") or [])
        overlay_tasks = list(overlay.get("tasks") or [])
        if len(blueprint_tasks) != 40 or len(overlay_tasks) != 40:
            raise Unit04ReducedSupportDirectAuthoringError(f"TASK_COUNT_DRIFT:F{form_number:02d}")
        if [row.get("question_number") for row in overlay_tasks] != list(range(1, 41)):
            raise Unit04ReducedSupportDirectAuthoringError(f"QUESTION_IDENTITY_DRIFT:F{form_number:02d}")

        active = 0
        deferred = 0
        core_counts: Counter[str] = Counter()
        choice_positions: list[int] = []
        for blueprint_task, task in zip(blueprint_tasks, overlay_tasks):
            q = int(task["question_number"])
            qid = f"F{form_number:02d}Q{q:02d}"
            if int(blueprint_task.get("question_number")) != q:
                raise Unit04ReducedSupportDirectAuthoringError(f"BLUEPRINT_OVERLAY_Q_MISMATCH:{qid}")
            expected_core = _expected_core_mode(blueprint_task, task)
            picture_required = bool(blueprint_task.get("picture_required"))
            active_flag = task.get("learner_surface_active")
            if picture_required:
                if expected_core is not None:
                    raise Unit04ReducedSupportDirectAuthoringError(f"PICTURE_CORE_EXPECTATION_DRIFT:{qid}")
                if active_flag is not False or task.get("core_response_mode") is not None:
                    raise Unit04ReducedSupportDirectAuthoringError(f"PICTURE_NOT_DEFERRED:{qid}")
                if task.get("response_format") != "DEFERRED" or task.get("deferred_reason") != "PICTURE_INTERACTION_DEFERRED":
                    raise Unit04ReducedSupportDirectAuthoringError(f"PICTURE_DEFERRED_METADATA_DRIFT:{qid}")
                if any(key in task for key in ("prompt", "reference_answer", "options", "left_items", "right_options")):
                    raise Unit04ReducedSupportDirectAuthoringError(f"PICTURE_LEARNER_CONTENT_PRESENT:{qid}")
                deferred += 1
                continue
            if active_flag is not True:
                raise Unit04ReducedSupportDirectAuthoringError(f"NON_PICTURE_TASK_INACTIVE:{qid}")
            if task.get("core_response_mode") != expected_core:
                raise Unit04ReducedSupportDirectAuthoringError(
                    f"CORE_PROJECTION_MISMATCH:{qid}:{task.get('core_response_mode')}:{expected_core}"
                )
            choice_position = _validate_active_schema(task, qid)
            if choice_position is not None:
                choice_positions.append(choice_position)
            prompt_key = _normalized(str(task.get("prompt") or ""))
            prior = prompt_seen.get(prompt_key)
            if prior is not None:
                raise Unit04ReducedSupportDirectAuthoringError(f"DUPLICATE_PROMPT:{prior}:{qid}")
            prompt_seen[prompt_key] = qid
            for value in _visible_and_assessed_strings(task):
                lowered = value.casefold()
                if any(phrase in lowered for phrase in SUPPORT_RELATIONS):
                    raise Unit04ReducedSupportDirectAuthoringError(f"SUPPORT_RELATION_ASSESSED:{qid}:{value}")
                if any(phrase in lowered for phrase in FORBIDDEN_LEARNER_PHRASES):
                    raise Unit04ReducedSupportDirectAuthoringError(f"ENGINEERING_LANGUAGE_VISIBLE:{qid}:{value}")
            mode = str(task["core_response_mode"])
            core_counts[mode] += 1
            global_core_counts[mode] += 1
            active += 1

        if active != EXPECTED_ACTIVE_COUNTS[form_number] or deferred != EXPECTED_DEFERRED_COUNTS[form_number]:
            raise Unit04ReducedSupportDirectAuthoringError(
                f"ACTIVE_DEFERRED_COUNT_DRIFT:F{form_number:02d}:{active}:{deferred}"
            )
        if set(core_counts) != set(core_contract.CORE_RESPONSE_MODES):
            raise Unit04ReducedSupportDirectAuthoringError(
                f"FORM_CORE_MODE_COVERAGE_DRIFT:F{form_number:02d}:{sorted(core_counts)}"
            )
        position_counts = Counter(choice_positions)
        if position_counts and max(position_counts.values()) - min(position_counts.values()) > 1:
            raise Unit04ReducedSupportDirectAuthoringError(
                f"CHOICE_POSITION_IMBALANCE:F{form_number:02d}:{dict(position_counts)}"
            )
        active_total += active
        deferred_total += deferred
        form_reports.append({
            "form_number": form_number,
            "active_task_count": active,
            "deferred_picture_task_count": deferred,
            "core_response_mode_counts": dict(sorted(core_counts.items())),
            "choice_position_counts": dict(sorted(position_counts.items())),
        })

    if active_total != EXPECTED_ACTIVE_TOTAL or deferred_total != EXPECTED_DEFERRED_TOTAL:
        raise Unit04ReducedSupportDirectAuthoringError(
            f"GLOBAL_ACTIVE_DEFERRED_DRIFT:{active_total}:{deferred_total}"
        )
    if set(global_core_counts) != set(core_contract.CORE_RESPONSE_MODES):
        raise Unit04ReducedSupportDirectAuthoringError("GLOBAL_CORE_MODE_COVERAGE_DRIFT")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "form_count": 4,
        "canonical_slot_count": 160,
        "active_no_picture_task_count": active_total,
        "deferred_picture_task_count": deferred_total,
        "core_response_modes": list(core_contract.CORE_RESPONSE_MODES),
        "core_response_mode_counts": dict(sorted(global_core_counts.items())),
        "unique_active_prompt_count": len(prompt_seen),
        "support_relations_assessed": False,
        "learner_content_author": "GPT-5.6_SOL_DIRECT_AUTHORING",
        "python_learner_authoring_used": False,
        "picture_interaction_active": False,
        "listening_modified": False,
        "a2_a2plus_unlocked": False,
        "forms": form_reports,
    }
