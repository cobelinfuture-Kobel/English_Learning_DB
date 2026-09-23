from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FAR5 validates GPT-5.6-authored learner-facing pilot content, lineage, "
    "operator-approved scaffolds, asset gating, and retention metadata. "
    "Python does not generate, rewrite, repair, paraphrase, or semantically "
    "decide learner-facing English."
)

TASK_ID = "A1FS-V1-U05FAR5_GPT56LearnerFacingPracticePilot46"
STATUS = "PASS_A1FS_V1_U05FAR5_GPT56_LEARNER_FACING_PRACTICE_PILOT46_OPERATOR_ACCEPTED"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR5_Pilot46PRGateMergePostMergeReadback"

REPO_ROOT = Path(__file__).resolve().parents[2]
FAR3_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_learner_facing_practice_materialization_contract.json"
FAR4_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_gpt56_practice_materialization_preflight.json"
PILOT_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_gpt56_practice_pilot46.json"

EXPECTED_FAMILIES = {
    "SHORT_MESSAGE_MEANING",
    "PERSON_TEXT_DETAIL_MATCHING",
    "LONG_TEXT_DETAIL_INFERENCE",
    "LEXICAL_CLOZE",
    "OPEN_CLOZE",
    "SHORT_COMMUNICATIVE_EMAIL",
    "PICTURE_SEQUENCE_STORY",
    "AUDIO_PICTURE_DETAIL_SELECTION",
    "AUDIO_NOTE_COMPLETION",
    "AUDIO_CONVERSATION_DETAIL",
    "SHORT_AUDIO_GIST_INTENT_DETAIL",
    "AUDIO_LIST_MATCHING",
    "PERSONAL_INTERVIEW",
    "COLLABORATIVE_VISUAL_DISCUSSION",
}
EXPECTED_FRAMES = {
    "U05-BF-NP-AFF",
    "U05-BF-NP-NEG",
    "U05-BF-ADJ-AFF",
    "U05-BF-ADJ-NEG",
    "U05-BF-PLACE-AFF",
    "U05-BF-PLACE-NEG",
}
REVIEW_KEYS = (
    "gpt56_semantic_review",
    "gpt56_pedagogical_review",
    "gpt56_source_grounding_review",
    "gpt56_unit05_scope_review",
    "gpt56_answerability_review",
)
RETENTION_FLOW = [
    "LISTEN_WITHOUT_TRANSCRIPT",
    "WRITE",
    "CHECK_AFTER_ATTEMPT",
    "LISTEN_AGAIN",
    "SAY_ALOUD",
]


class U05FAR5Error(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR5Error(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05FAR5Error(f"NOT_OBJECT:{path}")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise U05FAR5Error(code)


def build_report() -> dict[str, Any]:
    far3 = _load(FAR3_PATH)
    far4 = _load(FAR4_PATH)
    pilot = _load(PILOT_PATH)

    _require(pilot.get("task_id") == TASK_ID, "TASK_ID_DRIFT")
    _require(pilot.get("status") == STATUS, "STATUS_DRIFT")
    disposition = pilot.get("operator_review_disposition", {})
    _require(disposition.get("status") == "PASS", "OPERATOR_REVIEW_NOT_PASS")
    _require(disposition.get("final_integrated_version_review") == "PASS", "FINAL_INTEGRATION_REVIEW_NOT_PASS")
    _require(disposition.get("learner_facing_changes_required_before_ci") is False, "CONTENT_CHANGE_STILL_REQUIRED")
    _require(disposition.get("validator_ci_pr_merge_authorized") is True, "CI_NOT_AUTHORIZED")

    items = list(pilot.get("items", []))
    _require(len(items) == 46, "PILOT_ITEM_COUNT_DRIFT")
    _require(len({row["practice_id"] for row in items}) == 46, "PRACTICE_ID_COLLISION")
    _require(len({row["pilot_id"] for row in items}) == 46, "PILOT_ID_COLLISION")
    _require(len({row["source_slot_id"] for row in items}) == 46, "SOURCE_SLOT_COLLISION")

    category_counts = Counter(row["slot_category"] for row in items)
    _require(category_counts == {
        "CORE_GRAMMAR": 12,
        "KET_ADAPTED": 28,
        "DELAYED_DICTATION": 6,
    }, f"CATEGORY_COUNT_DRIFT:{dict(category_counts)}")

    execution_counts = Counter(row["execution_status"] for row in items)
    _require(execution_counts == {
        "EXECUTABLE_TEXT_ONLY": 26,
        "NOT_EXECUTABLE_ASSET_PENDING": 20,
    }, f"EXECUTION_COUNT_DRIFT:{dict(execution_counts)}")

    for row in items:
        _require(row.get("author_model") == "GPT-5.6 Sol", f"AUTHOR_MODEL_DRIFT:{row['practice_id']}")
        for key in REVIEW_KEYS:
            _require(row.get(key) == "PASS", f"REVIEW_DRIFT:{row['practice_id']}:{key}")

    # FAR4 exact pilot identity / lineage remains authoritative.
    far4_rows = {row["pilot_id"]: row for row in far4["pilot_slots"]}
    _require(set(far4_rows) == {row["pilot_id"] for row in items}, "FAR4_PILOT_ID_SET_DRIFT")
    for row in items:
        source = far4_rows[row["pilot_id"]]
        _require(row["source_slot_id"] == source["source_slot_id"], f"SLOT_LINEAGE_DRIFT:{row['pilot_id']}")
        _require(row["practice_set_id"] == source["practice_set_id"], f"SET_LINEAGE_DRIFT:{row['pilot_id']}")
        _require(row["stage"] == source["stage"], f"STAGE_LINEAGE_DRIFT:{row['pilot_id']}")
        _require(row["episode_id"] == source["episode_id"], f"EPISODE_LINEAGE_DRIFT:{row['pilot_id']}")

    core = [row for row in items if row["slot_category"] == "CORE_GRAMMAR"]
    ket = [row for row in items if row["slot_category"] == "KET_ADAPTED"]
    dictation = [row for row in items if row["slot_category"] == "DELAYED_DICTATION"]

    frame_counts = Counter(row["frame_id"] for row in core)
    _require(set(frame_counts) == EXPECTED_FRAMES, "CORE_FRAME_SET_DRIFT")
    _require(set(frame_counts.values()) == {2}, f"CORE_FRAME_COUNT_DRIFT:{dict(frame_counts)}")

    family_counts = Counter(row["task_family"] for row in ket)
    _require(set(family_counts) == EXPECTED_FAMILIES, "KET_FAMILY_SET_DRIFT")
    _require(set(family_counts.values()) == {2}, f"KET_FAMILY_COUNT_DRIFT:{dict(family_counts)}")

    by_id = {row["practice_id"]: row for row in items}

    # Operator review fixes: P10/P11.
    p10 = by_id["U05-FAR5-P10"]
    _require(p10["prompt"] == "The bags ___ under the chairs.", "P10_PROMPT_DRIFT")
    _require("children" not in p10["prompt"].lower(), "P10_IRREGULAR_PLURAL_REINTRODUCED")
    _require(p10["answer_binding_or_rubric"]["accepted_answers"] == ["are"], "P10_ANSWER_DRIFT")

    p11 = by_id["U05-FAR5-P11"]
    _require(p11["stimulus"]["type"] == "SOURCE_CONTEXT_AND_SENTENCE_PLAN", "P11_CONTEXT_MISSING")
    _require(p11["stimulus"]["sentence_plan"][0]["cue"] == "Who + not where?", "P11_NEGATIVE_CUE_DRIFT")
    _require(
        p11["answer_binding_or_rubric"]["model_response_example"] == "Ben is not at the library now.",
        "P11_MODEL_DRIFT",
    )

    # Context-dependent KET reading/cloze fixes.
    for pid in ("U05-FAR5-P19", "U05-FAR5-P20"):
        row = by_id[pid]
        _require(row["stimulus"]["type"] == "CONNECTED_SOURCE_CONTEXT", f"{pid}_CONTEXT_MISSING")
        _require(len(row["stimulus"]["text"].split()) >= 8, f"{pid}_CONTEXT_TOO_THIN")

    p21 = by_id["U05-FAR5-P21"]
    _require(p21["stimulus"]["type"] == "CONNECTED_SOURCE_CONTEXT", "P21_CONTEXT_MISSING")
    _require(p21["prompt"] == "They ___ brothers.", "P21_PROMPT_DRIFT")
    _require(p21["answer_binding_or_rubric"]["accepted_answers"] == ["are"], "P21_ANSWER_DRIFT")

    # Productive scaffold + mandatory final integrated version.
    scaffold = far3["productive_scaffold_contract"]
    _require(
        "FINAL_INTEGRATED_VERSION" in scaffold["core_sequence"],
        "FAR3_FINAL_INTEGRATION_SEQUENCE_MISSING",
    )
    fic = scaffold["final_integration_contract"]
    _require(fic["required_for_output_of_two_or_more_sentences"] is True, "FINAL_INTEGRATION_NOT_REQUIRED")
    _require(fic["operator_review_status"] == "PASS", "FINAL_INTEGRATION_OPERATOR_REVIEW_DRIFT")
    _require(fic["validator_ci_gate_authorized"] is True, "FINAL_INTEGRATION_CI_GATE_NOT_AUTHORIZED")
    _require(
        "MULTI_SENTENCE_PRODUCTIVE_TASKS_MUST_END_WITH_A_FINAL_INTEGRATED_VERSION"
        in scaffold["hard_rules"],
        "FINAL_INTEGRATION_HARD_RULE_MISSING",
    )

    productive_expectations = {
        "U05-FAR5-P23": (2, "WRITE_COMPLETE_VERSION"),
        "U05-FAR5-P24": (3, "WRITE_COMPLETE_VERSION"),
        "U05-FAR5-P38": (4, "SAY_COMPLETE_VERSION"),
        "U05-FAR5-P40": (4, "SAY_COMPLETE_VERSION"),
    }
    for pid, (plan_count, final_mode) in productive_expectations.items():
        row = by_id[pid]
        _require(len(row["stimulus"]["sentence_plan"]) == plan_count, f"{pid}_PLAN_COUNT_DRIFT")
        _require(row["stimulus"]["final_integration"]["label"] == "Final version", f"{pid}_FINAL_LABEL_DRIFT")
        _require(row["response_contract"]["final_integration_required"] is True, f"{pid}_FINAL_NOT_REQUIRED")
        _require(row["response_contract"]["final_integration_mode"] == final_mode, f"{pid}_FINAL_MODE_DRIFT")
        _require(bool(row["answer_binding_or_rubric"]["final_integrated_model"]), f"{pid}_FINAL_MODEL_MISSING")

    _require(
        by_id["U05-FAR5-P23"]["answer_binding_or_rubric"]["final_integrated_model"]
        == "Ben is in the living room. He is rested and cheerful.",
        "P23_FINAL_MODEL_DRIFT",
    )
    _require(
        by_id["U05-FAR5-P24"]["answer_binding_or_rubric"]["final_integrated_model"]
        == "Ben and Mia are at school. Ben is near the window, and Mia is at her desk. Their bags are under the chairs.",
        "P24_FINAL_MODEL_DRIFT",
    )

    # Asset-dependent tasks occur late; visual discussion stays descriptive, not opinion-heavy.
    for n in range(25, 37):
        row = by_id[f"U05-FAR5-P{n:02d}"]
        _require(row.get("preferred_form_position") == "LATE_ASSET_DEPENDENT_SECTION", f"P{n:02d}_LATE_POSITION_MISSING")
        _require(row.get("deferred_until_required_assets_ready") is True, f"P{n:02d}_ASSET_DEFER_MISSING")

    for pid in ("U05-FAR5-P39", "U05-FAR5-P40"):
        row = by_id[pid]
        _require(row.get("preferred_form_position") == "LATE_ASSET_DEPENDENT_SECTION", f"{pid}_LATE_POSITION_MISSING")
        _require(row.get("deferred_until_required_assets_ready") is True, f"{pid}_ASSET_DEFER_MISSING")
        lowered = row["prompt"].lower()
        _require("best place" not in lowered and "good for" not in lowered, f"{pid}_OPINION_HEAVY_PROMPT_REINTRODUCED")

    # Delayed dictation is a final retention flow, never an ordinary immediate exercise.
    _require(Counter(row["dictation_pass"] for row in dictation) == {"D1": 4, "D2": 2}, "DICTATION_PASS_COUNT_DRIFT")
    for row in dictation:
        _require(row.get("preferred_form_position") == "FINAL_RETENTION_SECTION", f"{row['practice_id']}_NOT_FINAL")
        _require(row.get("deferred_until_required_assets_ready") is True, f"{row['practice_id']}_AUDIO_DEFER_MISSING")
        _require(row["response_contract"]["learner_flow"] == RETENTION_FLOW, f"{row['practice_id']}_RETENTION_FLOW_DRIFT")
        expected_schedule = "D_PLUS_2_TO_D_PLUS_5" if row["dictation_pass"] == "D1" else "D_PLUS_7_TO_D_PLUS_14"
        _require(row["response_contract"]["retention_schedule"] == expected_schedule, f"{row['practice_id']}_SCHEDULE_DRIFT")
        _require(row["execution_status"] == "NOT_EXECUTABLE_ASSET_PENDING", f"{row['practice_id']}_EXECUTION_UNLOCKED")
        _require(row["asset_binding"].get("audio_asset_ref") is None, f"{row['practice_id']}_FAKE_AUDIO_REF")

    # Corrected-sentence answer mode remains explicitly supported by FAR3.
    deterministic_modes = far3["answerability_contract"]["deterministic_response_modes"]["answer_modes"]
    _require(
        "EXACT_CORRECTED_SENTENCE_OR_APPROVED_VARIANTS" in deterministic_modes,
        "CORRECTED_SENTENCE_ANSWER_MODE_MISSING",
    )

    # Production scope remains bounded.
    safety = pilot["scope_safety"]
    _require(safety["full_1632_materialization_started"] is False, "FULL_1632_STARTED_DURING_PILOT")
    _require(safety["reader360_modified"] is False, "READER360_MODIFIED")
    _require(safety["far2_modified"] is False, "FAR2_MODIFIED")
    _require(safety["audio_generated"] is False, "AUDIO_PREMATURELY_GENERATED")
    _require(safety["visual_asset_generated"] is False, "VISUAL_PREMATURELY_GENERATED")
    _require(safety["pdf_materialized"] is False, "PDF_PREMATURELY_MATERIALIZED")
    _require(safety["a2_grammar_unlocked"] is False, "A2_GRAMMAR_UNLOCKED")
    _require(safety["a2_native_word_floor_unlocked"] is False, "A2_NATIVE_WORD_FLOOR_UNLOCKED")
    _require(safety["python_learner_facing_authoring"] is False, "PYTHON_LEARNER_AUTHORING_UNLOCKED")
    _require(safety["other_units_modified"] is False, "OTHER_UNIT_MODIFIED")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "pilot_item_count": len(items),
        "core_count": len(core),
        "ket_count": len(ket),
        "dictation_count": len(dictation),
        "text_executable_count": execution_counts["EXECUTABLE_TEXT_ONLY"],
        "asset_pending_count": execution_counts["NOT_EXECUTABLE_ASSET_PENDING"],
        "ket_family_count": len(family_counts),
        "core_frame_count": len(frame_counts),
        "final_integrated_productive_item_count": len(productive_expectations),
        "late_asset_dependent_item_count": 14,
        "final_retention_item_count": len(dictation),
        "operator_review": "PASS",
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
