from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import a1fs_v1_core_response_mode_contract as core
from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as form_contract
from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as current360

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical validation only over GPT-5.6-direct-authored Form05-08 assets. "
    "No learner-facing language is generated or repaired here."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FORMV3C_GPT56Current360BindingAndDirectAuthoring_Form05To08"
FORM_STATUS = "GPT5_6_DIRECT_AUTHORED_REDUCED_SUPPORT_WITH_CORE_SIX_RESPONSE_MODES"
STATUS = "PASS_A1FS_V1_U04FORMV3C_FORM05_TO08_CURRENT360_DIRECT_AUTHORING_CORE6_PICTURE_DEFERRED"
REVISION = "FORMV3C_REDUCED_SUPPORT_DIRECT_AUTHORING_CORE6_VALIDATOR_V1"
EXPECTED_FORMS = (5, 6, 7, 8)
DIRECT = "u04formv3c_direct_authored_form{number:02d}.json"
BLUEPRINT = "u04formv3c_reduced_support_blueprint_form{number:02d}.json"
PRIOR = "u04formv3c_direct_authored_form{number:02d}.json"
PICTURE = {"PICTURE_POSITION", "PICTURE_LABEL", "PICTURE_DIFFERENCE"}
CHOICE = {"SELECT_ONE", "GIST_BEST_TITLE"}
MATCH = {"MATCHING", "MULTIPLE_MATCHING", "REFERENCE_MATCHING"}
STRUCTURED = {"NOTE_COMPLETION", "TABLE_COMPLETION"}

class Unit04FormV3CForm05To08DirectAuthoringError(ValueError):
    pass

def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]

def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Unit04FormV3CForm05To08DirectAuthoringError(f"ASSET_MISSING:{path.name}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()

def _has(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))

def _project(task: dict[str, Any]) -> str | None:
    try:
        return core.project_core_response_mode(task)
    except core.CoreResponseModeContractError as exc:
        raise Unit04FormV3CForm05To08DirectAuthoringError(str(exc)) from exc

def _check_answer(task: dict[str, Any], legacy: str, qid: str) -> int | None:
    fields = int(task.get("response_field_count") or 0)
    if fields < 1:
        raise Unit04FormV3CForm05To08DirectAuthoringError(f"FIELD_COUNT:{qid}")
    dialogue_choice = legacy == "DIALOGUE_RESPONSE" and task.get("dialogue_mode") == "select_one"
    if legacy in CHOICE or dialogue_choice:
        options = task.get("options")
        correct = task.get("correct_option_index")
        if not isinstance(options, list) or len(options) != 4 or len({_norm(v) for v in options}) != 4:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"CHOICE_OPTIONS:{qid}")
        if not isinstance(correct, int) or correct not in range(4):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"CHOICE_INDEX:{qid}")
        if str(options[correct]).strip() != str(task.get("reference_answer") or "").strip():
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"CHOICE_ANSWER:{qid}")
        return correct
    if legacy in MATCH:
        left, right, answer_map = task.get("left_items"), task.get("right_options"), task.get("answer_map")
        if not isinstance(left, list) or len(left) != fields or not isinstance(right, list):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"MATCH_SHAPE:{qid}")
        if len({_norm(v) for v in right}) != len(right):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"MATCH_DUPLICATE:{qid}")
        if not isinstance(answer_map, list) or len(answer_map) != fields or any(
            not isinstance(i, int) or i not in range(len(right)) for i in answer_map
        ):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"MATCH_MAP:{qid}")
        return None
    if legacy in STRUCTURED:
        rows = task.get("response_fields")
        if not isinstance(rows, list) or len(rows) != fields or any(
            not str(r.get("label") or "").strip() or not str(r.get("answer") or "").strip()
            for r in rows
        ):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"STRUCTURED:{qid}")
        return None
    if legacy == "ORDER_SEQUENCE":
        seq, order = task.get("sequence_items"), task.get("correct_order")
        if not isinstance(seq, list) or len(seq) != fields or not isinstance(order, list) or sorted(order) != list(range(fields)):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"ORDER:{qid}")
        return None
    if legacy in PICTURE:
        if task.get("response_mode") is not None or task.get("picture_interaction_status") != "DEFERRED":
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"PICTURE_NOT_DEFERRED:{qid}")
        if (task.get("visual_spec") or {}).get("status") != "DEFERRED_PICTURE_ASSET":
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"PICTURE_SPEC:{qid}")
        answers = task.get("expected_actions") if legacy == "PICTURE_POSITION" else task.get("reference_answers")
        if not isinstance(answers, list) or len(answers) != fields:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"PICTURE_ANSWERS:{qid}")
        return None
    answer = str(task.get("reference_answer") or "").strip()
    if not answer:
        raise Unit04FormV3CForm05To08DirectAuthoringError(f"ANSWER_EMPTY:{qid}")
    if legacy == "DIALOGUE_RESPONSE" and task.get("dialogue_mode") != "short_text":
        raise Unit04FormV3CForm05To08DirectAuthoringError(f"DIALOGUE_FORMAT:{qid}")
    if legacy == "ONE_WORD_GAP" and len(answer.split()) != 1:
        raise Unit04FormV3CForm05To08DirectAuthoringError(f"ONE_WORD:{qid}")
    if legacy == "ONE_TO_THREE_WORDS":
        n = len(re.findall(r"\b[\w']+\b", answer))
        if not 1 <= n <= 3:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"ONE_TO_THREE:{qid}:{n}")
    return None

def validate_form05_08(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    if core.validate_contract().get("status") != core.STATUS:
        raise Unit04FormV3CForm05To08DirectAuthoringError("CORE_CONTRACT_NOT_PASS")
    current_report = current360.build_unit04_neb02_natural_episode_bank_360()
    rows = {str(r["episode_id"]): r for r in current_report.get("effective_episodes") or []}
    if current_report.get("status") != current360.STATUS or len(rows) != 360:
        raise Unit04FormV3CForm05To08DirectAuthoringError("CURRENT360_NOT_PASS")

    product = root / "product" / "a1fs_v1_2_1"
    prior = {
        str(c["episode_id"])
        for n in range(1, 5)
        for c in (_load(product / PRIOR.format(number=n)).get("form") or {}).get("contexts") or []
    }
    if len(prior) != 24:
        raise Unit04FormV3CForm05To08DirectAuthoringError(f"PRIOR_EPISODES:{len(prior)}")

    all_episodes: list[str] = []
    prompts: set[str] = set()
    global_core: Counter[str] = Counter()
    deferred_total = 0
    reports: list[dict[str, Any]] = []

    for n in EXPECTED_FORMS:
        bp = _load(product / BLUEPRINT.format(number=n))["form"]
        payload = _load(product / DIRECT.format(number=n))
        if payload.get("schema_version") != "a1fs.v1.u04.formv3c.direct_authored_reduced_support.v1":
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"SCHEMA:F{n:02d}")
        if payload.get("program_id") != PROGRAM_ID or payload.get("unit_id") != UNIT_ID:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"IDENTITY:F{n:02d}")
        if payload.get("task_id") != TASK_ID or payload.get("status") != FORM_STATUS:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"STATUS:F{n:02d}")
        prov = payload.get("authoring_provenance") or {}
        for key in (
            "python_blueprint_generation_used", "python_response_mode_assignment_used",
            "python_task_family_assignment_used", "python_learner_content_authoring_used",
            "python_answer_option_authoring_used", "legacy_python_task_builder_used",
        ):
            if prov.get(key) is not False:
                raise Unit04FormV3CForm05To08DirectAuthoringError(f"FORBIDDEN_PYTHON_AUTHORING:F{n:02d}:{key}")
        if prov.get("python_serialization_only") is not True:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"SERIALIZATION_PROVENANCE:F{n:02d}")
        tax = payload.get("taxonomy_contract") or {}
        if tax.get("response_mode_authority") != "A1FS_V1_CORE_SIX_RESPONSE_MODES":
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"TAXONOMY:F{n:02d}")

        form = payload["form"]
        if form.get("form_number") != n or form.get("stage") != "REDUCED_SUPPORT" or form.get("support_level") != "MEDIUM":
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"FORM_CONTRACT:F{n:02d}")
        contexts = form.get("contexts") or []
        if len(contexts) != 6 or {str(c.get("slot")) for c in contexts} != set(form_contract.CONTEXT_SLOT_CONTRACT):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"CONTEXT_SLOTS:F{n:02d}")
        ids, rels = [], set()
        for c in contexts:
            eid = str(c.get("episode_id") or "")
            source = rows.get(eid)
            if source is None or str(c.get("passage") or "") != str(source.get("passage") or ""):
                raise Unit04FormV3CForm05To08DirectAuthoringError(f"CURRENT360_BINDING:F{n:02d}:{eid}")
            ids.append(eid)
            rels.update(r for r in form_contract.TARGET_RELATIONS if _has(str(c["passage"]), r))
        if len(set(ids)) != 6 or set(ids) & prior:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"EPISODE_REUSE:F{n:02d}")
        if rels != set(form_contract.TARGET_RELATIONS):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"RELATION_COVERAGE:F{n:02d}:{sorted(rels)}")
        all_episodes.extend(ids)

        bp_tasks = {int(t["question_number"]): t for t in bp.get("tasks") or []}
        tasks = form.get("tasks") or []
        if len(tasks) != 40 or [int(t.get("question_number") or 0) for t in tasks] != list(range(1, 41)):
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"TASK_SEQUENCE:F{n:02d}")
        core_counts: Counter[str] = Counter()
        choices: list[int] = []
        deferred = 0
        for task in tasks:
            qn = int(task["question_number"])
            qid = f"U04-FORMV3C-F{n:02d}-Q{qn:02d}"
            if task.get("question_id") != qid:
                raise Unit04FormV3CForm05To08DirectAuthoringError(f"QID:{qid}")
            bpt = bp_tasks[qn]
            legacy = str(task.get("legacy_response_mode") or "")
            if legacy != str(bpt.get("response_mode") or "") or int(task.get("response_field_count") or 0) != int(bpt.get("response_field_count") or 0):
                raise Unit04FormV3CForm05To08DirectAuthoringError(f"BLUEPRINT_DRIFT:{qid}")
            expected_core = _project(dict(bpt))
            if task.get("response_mode") != expected_core:
                raise Unit04FormV3CForm05To08DirectAuthoringError(f"CORE_MODE_DRIFT:{qid}")
            if not str(task.get("response_format") or "").strip() or not str(task.get("prompt") or "").strip():
                raise Unit04FormV3CForm05To08DirectAuthoringError(f"VISIBLE_SCHEMA:{qid}")
            pkey = _norm(task["prompt"])
            if pkey in prompts:
                raise Unit04FormV3CForm05To08DirectAuthoringError(f"PROMPT_DUPLICATE:{qid}")
            prompts.add(pkey)
            if expected_core is None:
                deferred += 1
                deferred_total += 1
            else:
                core_counts[expected_core] += 1
                global_core[expected_core] += 1
            choice = _check_answer(task, legacy, qid)
            if choice is not None:
                choices.append(choice)
        if len(core_counts) < 5:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"CORE_BREADTH:F{n:02d}")
        pc = Counter(choices)
        choice_counts = [pc[i] for i in range(4)]
        if choices and max(choice_counts) - min(choice_counts) > 1:
            raise Unit04FormV3CForm05To08DirectAuthoringError(f"CHOICE_BALANCE:F{n:02d}:{choice_counts}")
        reports.append({
            "form_number": n,
            "episode_ids": ids,
            "target_relation_coverage": sorted(rels),
            "core_response_mode_counts": dict(sorted(core_counts.items())),
            "core_response_mode_coverage_count": len(core_counts),
            "deferred_picture_task_count": deferred,
            "choice_position_counts": choice_counts,
            "task_count": 40,
        })

    if len(all_episodes) != 24 or len(set(all_episodes)) != 24 or prior & set(all_episodes):
        raise Unit04FormV3CForm05To08DirectAuthoringError("CROSS_FORM_EPISODE_REUSE")
    if set(global_core) != set(core.CORE_RESPONSE_MODES):
        raise Unit04FormV3CForm05To08DirectAuthoringError(f"GLOBAL_CORE_COVERAGE:{sorted(global_core)}")

    return {
        "task_id": TASK_ID, "status": STATUS, "revision": REVISION,
        "form_count": 4, "task_count": 160,
        "current360_context_count": 24, "current360_exact_passage_count": 24,
        "form01_04_episode_reuse_count": 0, "form05_08_cross_form_episode_reuse_count": 0,
        "normalized_prompt_duplicate_count": 0,
        "core_response_modes": list(core.CORE_RESPONSE_MODES),
        "core_response_mode_counts": dict(sorted(global_core.items())),
        "deferred_picture_task_count": deferred_total,
        "picture_interaction_active": False,
        "blueprint_task_family_preserved": True,
        "blueprint_assessment_capability_preserved": True,
        "blueprint_quota_family_preserved": True,
        "learner_content_direct_authored": True,
        "forms": reports,
        "scope_safety": {
            "form01_04_learner_content_modified": False,
            "q10_800_activity_authority_modified": False,
            "current360_authority_modified": False,
            "canonical_grammar_modified": False,
            "canonical_vocabulary_modified": False,
            "canonical_chunk_modified": False,
            "picture_interaction_activated": False,
            "form09_plus_opened": False,
            "unit05_plus_opened": False,
            "a2_a2plus_unlocked": False,
        },
    }
