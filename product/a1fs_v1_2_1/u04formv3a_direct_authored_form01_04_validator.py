from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as contract
from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as current360

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical validator over GPT-5.6-direct-authored static FormV3 learner assets. "
    "It does not compose, rewrite, shuffle, repair, or otherwise author learner-facing English."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FORMV3A_GPT56DirectForm01To04LearnerTaskRematerialization"
STATUS = "PASS_A1FS_V1_U04FORMV3A_DIRECT_AUTHORED_FORM01_TO04_MECHANICAL_VALIDATION"
REVISION = "FORMV3A_GUIDED_DIRECT_AUTHORED_STATIC_ASSET_V1"
NEXT_SHORT_STEP = "A1FS-V1-U04FORMV3B_ExistingRendererIntegrationAndActualForm01To04VisualReview"

FORM_ASSET_NAMES = {
    1: "u04formv3a_direct_authored_form01.json",
    2: "u04formv3a_direct_authored_form02.json",
    3: "u04formv3a_direct_authored_form03.json",
    4: "u04formv3a_direct_authored_form04.json",
}
FORM_ASSET_STATUS = "GPT5_6_DIRECT_AUTHORED_STATIC_FORM"
EXPECTED_FORMS = (1, 2, 3, 4)
SECTION_FOR_NUMBER = {
    **{n: "A" for n in range(1, 7)},
    **{n: "B" for n in range(7, 17)},
    **{n: "C" for n in range(17, 27)},
    **{n: "D" for n in range(27, 35)},
    **{n: "E" for n in range(35, 41)},
}
SLOT_ALLOWED_SECTIONS = {
    slot: set(spec["sections"]) for slot, spec in contract.CONTEXT_SLOT_CONTRACT.items()
}


class Unit04FormV3AError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _load_asset(root: Path, form_number: int) -> dict[str, Any]:
    path = root / "product" / "a1fs_v1_2_1" / FORM_ASSET_NAMES[form_number]
    if not path.is_file():
        raise Unit04FormV3AError(f"FORM_ASSET_MISSING:F{form_number:02d}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != "a1fs.v1.u04.formv3a.direct_authored_form.v1":
        raise Unit04FormV3AError(f"FORM_SCHEMA_DRIFT:F{form_number:02d}")
    if payload.get("task_id") != TASK_ID:
        raise Unit04FormV3AError(f"FORM_TASK_ID_DRIFT:F{form_number:02d}")
    if payload.get("status") != FORM_ASSET_STATUS:
        raise Unit04FormV3AError(f"FORM_STATUS_DRIFT:F{form_number:02d}")
    provenance = payload.get("authoring_provenance") or {}
    if provenance.get("learner_content_author") != "GPT-5.6_SOL_DIRECT_AUTHORING":
        raise Unit04FormV3AError(f"LEARNER_AUTHOR_DRIFT:F{form_number:02d}")
    for key in (
        "python_learner_content_authoring_used",
        "current360_passage_mutation_used",
        "legacy_python_task_builder_used",
    ):
        if provenance.get(key) is not False:
            raise Unit04FormV3AError(f"FORBIDDEN_AUTHORING_ROLE:{form_number}:{key}")
    if provenance.get("semantic_review") != "GPT-5.6_SOL_SECOND_PASS_COMPLETE":
        raise Unit04FormV3AError(f"SEMANTIC_REVIEW_STATUS_DRIFT:F{form_number:02d}")
    return payload


def _current360_by_id() -> dict[str, dict[str, Any]]:
    report = current360.build_unit04_neb02_natural_episode_bank_360()
    if report.get("status") != current360.STATUS:
        raise Unit04FormV3AError("CURRENT360_SOURCE_NOT_PASS")
    rows = {str(row["episode_id"]): dict(row) for row in report.get("effective_episodes") or []}
    if len(rows) != 360:
        raise Unit04FormV3AError(f"CURRENT360_COUNT_DRIFT:{len(rows)}")
    return rows


def _validate_form(
    payload: dict[str, Any],
    *,
    expected_form_number: int,
    current_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    form = payload.get("form") or {}
    if form.get("form_number") != expected_form_number:
        raise Unit04FormV3AError(f"FORM_NUMBER_DRIFT:F{expected_form_number:02d}")
    if form.get("form_id") != f"U04-FORMV3-F{expected_form_number:02d}":
        raise Unit04FormV3AError(f"FORM_ID_DRIFT:F{expected_form_number:02d}")
    if form.get("stage") != "GUIDED":
        raise Unit04FormV3AError(f"FORM_STAGE_DRIFT:F{expected_form_number:02d}")

    contexts = list(form.get("contexts") or [])
    if len(contexts) != contract.CONTEXT_SLOTS_PER_FORM:
        raise Unit04FormV3AError(
            f"CONTEXT_COUNT_DRIFT:F{expected_form_number:02d}:{len(contexts)}"
        )
    context_by_slot = {str(row.get("slot")): dict(row) for row in contexts}
    if set(context_by_slot) != set(contract.CONTEXT_SLOT_CONTRACT):
        raise Unit04FormV3AError(f"CONTEXT_SLOT_DRIFT:F{expected_form_number:02d}")
    if len(context_by_slot) != len(contexts):
        raise Unit04FormV3AError(f"CONTEXT_SLOT_DUPLICATE:F{expected_form_number:02d}")

    episode_ids: list[str] = []
    target_relation_coverage: set[str] = set()
    for slot, row in context_by_slot.items():
        episode_id = str(row.get("episode_id") or "")
        source = current_rows.get(episode_id)
        if source is None:
            raise Unit04FormV3AError(
                f"CURRENT360_EPISODE_UNKNOWN:F{expected_form_number:02d}:{slot}:{episode_id}"
            )
        if str(row.get("passage") or "") != str(source.get("passage") or ""):
            raise Unit04FormV3AError(
                f"CURRENT360_PASSAGE_NOT_EXACT:F{expected_form_number:02d}:{slot}:{episode_id}"
            )
        episode_ids.append(episode_id)
        passage = str(row["passage"])
        target_relation_coverage.update(
            relation for relation in contract.TARGET_RELATIONS if _contains_surface(passage, relation)
        )
    if len(episode_ids) != len(set(episode_ids)):
        raise Unit04FormV3AError(f"WITHIN_FORM_EPISODE_REUSE:F{expected_form_number:02d}")

    questions = list(form.get("questions") or [])
    if len(questions) != contract.QUESTIONS_PER_FORM:
        raise Unit04FormV3AError(
            f"QUESTION_COUNT_DRIFT:F{expected_form_number:02d}:{len(questions)}"
        )

    section_counts: Counter[str] = Counter()
    family_counts: dict[str, Counter[str]] = {
        section: Counter() for section in contract.SECTION_ORDER
    }
    slot_load: dict[str, Counter[str]] = {
        slot: Counter() for slot in contract.CONTEXT_SLOT_CONTRACT
    }
    select_positions: list[int] = []
    select_sequence: list[int] = []
    family_sequence: list[str] = []
    prompts: list[str] = []
    question_ids: set[str] = set()

    for expected_number, item in enumerate(questions, start=1):
        qid = str(item.get("question_id") or "")
        if qid != f"U04-FORMV3-F{expected_form_number:02d}-Q{expected_number:02d}":
            raise Unit04FormV3AError(
                f"QUESTION_ID_DRIFT:F{expected_form_number:02d}:Q{expected_number:02d}:{qid}"
            )
        if qid in question_ids:
            raise Unit04FormV3AError(f"QUESTION_ID_DUPLICATE:{qid}")
        question_ids.add(qid)
        if item.get("question_number") != expected_number:
            raise Unit04FormV3AError(f"QUESTION_NUMBER_DRIFT:{qid}")

        section = str(item.get("section") or "")
        if section != SECTION_FOR_NUMBER[expected_number]:
            raise Unit04FormV3AError(f"QUESTION_SECTION_DRIFT:{qid}:{section}")
        section_counts[section] += 1

        slot = str(item.get("context_slot") or "")
        if slot not in SLOT_ALLOWED_SECTIONS or section not in SLOT_ALLOWED_SECTIONS[slot]:
            raise Unit04FormV3AError(f"CONTEXT_SLOT_SECTION_MISMATCH:{qid}:{slot}:{section}")
        slot_load[slot][section] += 1

        family = str(item.get("family") or "")
        family_counts[section][family] += 1
        family_sequence.append(family)

        prompt = str(item.get("prompt") or "").strip()
        reference = str(item.get("reference_answer") or "").strip()
        if not prompt or not reference:
            raise Unit04FormV3AError(f"PROMPT_OR_REFERENCE_EMPTY:{qid}")
        prompts.append(prompt)
        visible = prompt
        options = item.get("options")
        if options is not None:
            visible += " " + " ".join(str(v) for v in options)
        visible_lower = visible.casefold()
        for phrase in contract.LEARNER_LANGUAGE_FORBIDDEN_PHRASES:
            if phrase.casefold() in visible_lower:
                raise Unit04FormV3AError(f"FORBIDDEN_LEARNER_LANGUAGE:{qid}:{phrase}")

        response_mode = item.get("response_mode")
        if response_mode == "select_one":
            if not isinstance(options, list) or len(options) != 4:
                raise Unit04FormV3AError(f"SELECT_OPTION_COUNT_INVALID:{qid}")
            if len({_normalized(str(value)) for value in options}) != 4:
                raise Unit04FormV3AError(f"SELECT_OPTION_DUPLICATE:{qid}")
            correct = item.get("correct_option_index")
            if not isinstance(correct, int) or correct not in range(4):
                raise Unit04FormV3AError(f"SELECT_CORRECT_INDEX_INVALID:{qid}")
            if str(options[correct]).strip() != reference:
                raise Unit04FormV3AError(f"SELECT_REFERENCE_MISMATCH:{qid}")
            select_positions.append(correct)
            select_sequence.append(correct)
        elif response_mode == "short_text":
            if "correct_option_index" in item or "options" in item:
                raise Unit04FormV3AError(f"SHORT_TEXT_SELECT_FIELDS_PRESENT:{qid}")
            if item.get("modality") not in {"WRITTEN", "ORAL"}:
                raise Unit04FormV3AError(f"SHORT_TEXT_MODALITY_INVALID:{qid}")
        else:
            raise Unit04FormV3AError(f"RESPONSE_MODE_INVALID:{qid}:{response_mode}")

        if family == "MEANING_BASED_RECONSTRUCTION":
            passage = str(context_by_slot[slot]["passage"])
            if _normalized(reference) in _normalized(passage):
                raise Unit04FormV3AError(f"RECONSTRUCTION_REFERENCE_VERBATIM_LEAK:{qid}")

    if dict(section_counts) != contract.SECTION_COUNTS:
        raise Unit04FormV3AError(
            f"SECTION_COUNTS_DRIFT:F{expected_form_number:02d}:{dict(section_counts)}"
        )

    expected_quotas = contract.STAGE_FAMILY_QUOTAS["GUIDED"]
    for section in contract.SECTION_ORDER:
        if dict(family_counts[section]) != expected_quotas[section]:
            raise Unit04FormV3AError(
                f"FAMILY_QUOTA_DRIFT:F{expected_form_number:02d}:{section}:"
                f"{dict(family_counts[section])}"
            )

    for slot, expected in contract.CONTEXT_SLOT_CONTRACT.items():
        if dict(slot_load[slot]) != dict(expected["question_load"]):
            raise Unit04FormV3AError(
                f"CONTEXT_LOAD_DRIFT:F{expected_form_number:02d}:{slot}:{dict(slot_load[slot])}"
            )

    position_counts = Counter(select_positions)
    if set(position_counts) != {0, 1, 2, 3}:
        raise Unit04FormV3AError(
            f"SELECT_POSITION_COVERAGE_DRIFT:F{expected_form_number:02d}:{dict(position_counts)}"
        )
    if max(position_counts.values()) - min(position_counts.values()) > (
        contract.ANSWER_DIVERSITY_CONTRACT["per_form_select_one_position_max_delta"]
    ):
        raise Unit04FormV3AError(
            f"SELECT_POSITION_IMBALANCE:F{expected_form_number:02d}:{dict(position_counts)}"
        )
    if target_relation_coverage != set(contract.TARGET_RELATIONS):
        raise Unit04FormV3AError(
            f"TARGET_RELATION_COVERAGE_DRIFT:F{expected_form_number:02d}:"
            f"{sorted(target_relation_coverage)}"
        )

    return {
        "form_number": expected_form_number,
        "form_id": form["form_id"],
        "stage": form["stage"],
        "context_count": len(contexts),
        "question_count": len(questions),
        "section_counts": dict(section_counts),
        "family_counts": {
            section: dict(family_counts[section]) for section in contract.SECTION_ORDER
        },
        "select_one_count": len(select_positions),
        "correct_option_position_counts": dict(sorted(position_counts.items())),
        "correct_option_position_max_delta": max(position_counts.values()) - min(position_counts.values()),
        "target_relation_coverage": sorted(target_relation_coverage),
        "episode_ids": episode_ids,
        "select_answer_sequence": select_sequence,
        "family_sequence": family_sequence,
        "prompts": prompts,
    }


def build_unit04_formv3a_validation(repo_root: Path | str | None = None) -> dict[str, Any]:
    contract_report = contract.validate_contract()
    if contract_report.get("status") != contract.STATUS:
        raise Unit04FormV3AError("FORMV3_CONTRACT_NOT_PASS")

    root = _root(repo_root)
    current_rows = _current360_by_id()
    form_reports = [
        _validate_form(
            _load_asset(root, form_number),
            expected_form_number=form_number,
            current_rows=current_rows,
        )
        for form_number in EXPECTED_FORMS
    ]

    all_episode_ids = [episode_id for report in form_reports for episode_id in report["episode_ids"]]
    if len(all_episode_ids) != 24 or len(set(all_episode_ids)) != 24:
        raise Unit04FormV3AError(
            f"CROSS_FORM_EPISODE_REUSE:{len(all_episode_ids)}:{len(set(all_episode_ids))}"
        )

    select_sequences = {tuple(report["select_answer_sequence"]) for report in form_reports}
    if len(select_sequences) != len(form_reports):
        raise Unit04FormV3AError("IDENTICAL_SELECT_ANSWER_SEQUENCE_ACROSS_FORMS")

    family_sequences = {tuple(report["family_sequence"]) for report in form_reports}
    if len(family_sequences) != len(form_reports):
        raise Unit04FormV3AError("IDENTICAL_FAMILY_SEQUENCE_ACROSS_FORMS")

    all_prompts = [prompt for report in form_reports for prompt in report["prompts"]]
    normalized_prompts = [_normalized(prompt) for prompt in all_prompts]
    exact_prompt_duplicate_count = len(normalized_prompts) - len(set(normalized_prompts))
    if exact_prompt_duplicate_count:
        raise Unit04FormV3AError(f"EXACT_PROMPT_DUPLICATE_COUNT:{exact_prompt_duplicate_count}")

    forms = [_load_asset(root, form_number)["form"] for form_number in EXPECTED_FORMS]
    for question_number in range(1, contract.QUESTIONS_PER_FORM + 1):
        items = [form["questions"][question_number - 1] for form in forms]
        if all(item["response_mode"] == "select_one" for item in items):
            indices = {int(item["correct_option_index"]) for item in items}
            if len(indices) == 1:
                raise Unit04FormV3AError(
                    f"FIXED_SELECT_POSITION_ACROSS_ALL_FOUR_FORMS:Q{question_number:02d}"
                )

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_authority": {
            "formv3_contract": contract.TASK_ID,
            "current360": current360.TASK_ID,
        },
        "form_count": len(form_reports),
        "question_count": sum(report["question_count"] for report in form_reports),
        "distinct_current360_episode_count": len(set(all_episode_ids)),
        "cross_form_episode_reuse_count": 0,
        "exact_prompt_duplicate_count": exact_prompt_duplicate_count,
        "python_learner_content_authoring_used": False,
        "legacy_python_task_builder_used": False,
        "current360_passage_mutation_used": False,
        "forms": [
            {
                key: value
                for key, value in report.items()
                if key not in {"prompts", "select_answer_sequence", "family_sequence"}
            }
            for report in form_reports
        ],
        "answer_diversity": {
            "identical_select_answer_sequence_across_forms": False,
            "identical_family_sequence_across_forms": False,
            "fixed_select_position_across_all_four_forms": False,
            "python_post_authoring_shuffle_used": False,
        },
        "activation": {
            "formv3_pilot_active_runtime": False,
            "legacy_fsv2_remains_active": True,
            "parallel_form_runtime_created": False,
        },
        "scope_safety": {
            "current360_modified": False,
            "listening_modified": False,
            "a2_a2plus_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    report = build_unit04_formv3a_validation()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
