from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FAR5 validator only verifies already operator-accepted GPT-5.6 learner-facing "
    "pilot content, source lineage, answerability metadata, asset gates, and productive "
    "scaffold contracts. It does not generate, rewrite, repair, or select learner-facing English."
)

TASK_ID = "A1FS-V1-U05FAR5_GPT56LearnerFacingPracticePilot46"
STATUS = "PASS_A1FS_V1_U05FAR5_GPT56_LEARNER_FACING_PRACTICE_PILOT46_OPERATOR_ACCEPTED"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR5_Pilot46ValidatorAndFocusedCI"

REPO_ROOT = Path(__file__).resolve().parents[2]
FAR3_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_learner_facing_practice_materialization_contract.json"
FAR4_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_gpt56_practice_materialization_preflight.json"
PILOT_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_gpt56_practice_pilot46.json"
CURRENT_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_current360_360.json"
SPOKEN_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_spoken360_360.json"
PATTERN_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_pattern360_360.json"

EXPECTED_REVIEW_KEYS = (
    "gpt56_semantic_review",
    "gpt56_pedagogical_review",
    "gpt56_source_grounding_review",
    "gpt56_unit05_scope_review",
    "gpt56_answerability_review",
)
EXPECTED_CORE_FRAMES = {
    "U05-BF-NP-AFF",
    "U05-BF-NP-NEG",
    "U05-BF-ADJ-AFF",
    "U05-BF-ADJ-NEG",
    "U05-BF-PLACE-AFF",
    "U05-BF-PLACE-NEG",
}
PRODUCTIVE_MODES = {"RUBRIC_CONTENT_POINTS", "ORAL_RUBRIC"}
ASSET_PENDING_STATUS = "NOT_EXECUTABLE_ASSET_PENDING"
TEXT_STATUS = "EXECUTABLE_TEXT_ONLY"


class U05FAR5Error(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR5Error(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05FAR5Error(f"NOT_OBJECT:{path}")
    return value


def _flatten_strings(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, str):
        result.append(value)
    elif isinstance(value, list):
        for item in value:
            result.extend(_flatten_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(_flatten_strings(item))
    return result


def _visible_signature(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("instruction_template_id") or ""),
        str(item.get("prompt") or ""),
        json.dumps(item.get("stimulus"), ensure_ascii=False, sort_keys=True),
        json.dumps(item.get("response_contract"), ensure_ascii=False, sort_keys=True),
    ]
    return "\n".join(parts).strip().casefold()


def build_report() -> dict[str, Any]:
    far3 = _load(FAR3_PATH)
    far4 = _load(FAR4_PATH)
    pilot = _load(PILOT_PATH)
    current = _load(CURRENT_PATH)
    spoken = _load(SPOKEN_PATH)
    pattern = _load(PATTERN_PATH)

    if pilot.get("task_id") != TASK_ID:
        raise U05FAR5Error("TASK_ID_DRIFT")
    if pilot.get("status") != STATUS:
        raise U05FAR5Error("OPERATOR_ACCEPTED_STATUS_DRIFT")
    qa = pilot.get("pilot_qa", {})
    if qa.get("status") != "PASS_OPERATOR_ACCEPTED_READY_FOR_VALIDATOR_CI":
        raise U05FAR5Error("OPERATOR_GATE_NOT_ACCEPTED")
    if qa.get("ci_run_allowed") is not True or qa.get("pr_allowed") is not True:
        raise U05FAR5Error("CI_OR_PR_GATE_NOT_AUTHORIZED")
    if pilot.get("next_short_step") != NEXT_SHORT_STEP:
        raise U05FAR5Error("NEXT_SHORT_STEP_DRIFT")

    authorship = pilot["authorship"]
    if authorship["learner_facing_author_model"] != "GPT-5.6 Sol":
        raise U05FAR5Error("AUTHOR_MODEL_DRIFT")
    if authorship["semantic_reviewer_model"] != "GPT-5.6 Sol":
        raise U05FAR5Error("REVIEWER_MODEL_DRIFT")
    if authorship["python_generated_or_rewrote_learner_facing_english"] is not False:
        raise U05FAR5Error("PYTHON_LEARNER_AUTHORING_UNLOCKED")
    if authorship["source_refs_read_before_authoring"] is not True:
        raise U05FAR5Error("SOURCE_READ_GATE_DRIFT")

    items = list(pilot["items"])
    if len(items) != 46:
        raise U05FAR5Error(f"ITEM_COUNT_DRIFT:{len(items)}")
    ids = [row["practice_id"] for row in items]
    if ids != [f"U05-FAR5-P{i:02d}" for i in range(1, 47)]:
        raise U05FAR5Error("PRACTICE_ID_SEQUENCE_DRIFT")
    if len({row["pilot_id"] for row in items}) != 46:
        raise U05FAR5Error("PILOT_ID_COLLISION")
    if len({row["source_slot_id"] for row in items}) != 46:
        raise U05FAR5Error("SOURCE_SLOT_COLLISION")

    category_counts = Counter(row["slot_category"] for row in items)
    if category_counts != Counter({"KET_ADAPTED": 28, "CORE_GRAMMAR": 12, "DELAYED_DICTATION": 6}):
        raise U05FAR5Error(f"CATEGORY_COUNT_DRIFT:{dict(category_counts)}")
    execution_counts = Counter(row["execution_status"] for row in items)
    if execution_counts != Counter({TEXT_STATUS: 26, ASSET_PENDING_STATUS: 20}):
        raise U05FAR5Error(f"EXECUTION_COUNT_DRIFT:{dict(execution_counts)}")

    far4_rows = {row["pilot_id"]: row for row in far4["pilot_slots"]}
    if len(far4_rows) != 46:
        raise U05FAR5Error("FAR4_PILOT_DENOMINATOR_DRIFT")
    for row in items:
        source = far4_rows.get(row["pilot_id"])
        if source is None:
            raise U05FAR5Error(f"FAR4_PILOT_ID_MISSING:{row['pilot_id']}")
        for key in ("source_slot_id", "practice_set_id", "stage", "episode_id"):
            if row[key] != source[key]:
                raise U05FAR5Error(f"FAR4_LINEAGE_DRIFT:{row['practice_id']}:{key}")

    core = [row for row in items if row["slot_category"] == "CORE_GRAMMAR"]
    core_frames = Counter(row["frame_id"] for row in core)
    if set(core_frames) != EXPECTED_CORE_FRAMES or set(core_frames.values()) != {2}:
        raise U05FAR5Error(f"CORE_FRAME_DRIFT:{dict(core_frames)}")
    for frame in EXPECTED_CORE_FRAMES:
        stages = {row["stage"] for row in core if row["frame_id"] == frame}
        if stages != {"GUIDED", "UNSEEN_TRANSFER"}:
            raise U05FAR5Error(f"CORE_STAGE_DRIFT:{frame}:{stages}")

    ket = [row for row in items if row["slot_category"] == "KET_ADAPTED"]
    far3_families = {
        row["task_family"]
        for row in far3["ket_adapted_materialization_contract"]["task_family_contracts"]
    }
    ket_families = Counter(row["task_family"] for row in ket)
    if set(ket_families) != far3_families or set(ket_families.values()) != {2}:
        raise U05FAR5Error(f"KET_FAMILY_DRIFT:{dict(ket_families)}")

    for row in items:
        if row.get("author_model") != "GPT-5.6 Sol":
            raise U05FAR5Error(f"ITEM_AUTHOR_DRIFT:{row['practice_id']}")
        for key in EXPECTED_REVIEW_KEYS:
            if row.get(key) != "PASS":
                raise U05FAR5Error(f"REVIEW_NOT_PASS:{row['practice_id']}:{key}")
        if not row.get("reader_source_refs"):
            raise U05FAR5Error(f"EMPTY_READER_SOURCE_REFS:{row['practice_id']}")
        if row["execution_status"] == ASSET_PENDING_STATUS:
            if not row.get("asset_preconditions"):
                raise U05FAR5Error(f"ASSET_PENDING_WITHOUT_PRECONDITION:{row['practice_id']}")
        elif row["execution_status"] == TEXT_STATUS:
            if row.get("asset_preconditions"):
                raise U05FAR5Error(f"TEXT_ITEM_HAS_ASSET_PRECONDITION:{row['practice_id']}")
        else:
            raise U05FAR5Error(f"INVALID_EXECUTION_STATUS:{row['practice_id']}")

    deterministic_modes = {
        "SINGLE_CORRECT_OPTION",
        "EXACT_ONE_WORD_OR_APPROVED_VARIANTS",
        "EXACT_CORRECTED_SENTENCE_OR_APPROVED_VARIANTS",
        "MATCHING_KEY",
        "EXACT_ONE_WORD_NUMBER_OR_APPROVED_VARIANTS",
        "DICTATION_EXACT_OR_NORMALIZED_TRANSCRIPT",
    }
    for row in items:
        mode = row["answer_mode"]
        answer = row["answer_binding_or_rubric"]
        if mode == "SINGLE_CORRECT_OPTION":
            if not (answer.get("correct_option_id") or answer.get("correct_option")):
                raise U05FAR5Error(f"MISSING_SINGLE_ANSWER:{row['practice_id']}")
        elif mode == "EXACT_ONE_WORD_OR_APPROVED_VARIANTS":
            values = answer.get("accepted_answers", [])
            if not values or any(" " in str(v).strip() for v in values):
                raise U05FAR5Error(f"ONE_WORD_ANSWER_DRIFT:{row['practice_id']}")
        elif mode == "EXACT_CORRECTED_SENTENCE_OR_APPROVED_VARIANTS":
            if not answer.get("accepted_full_answers"):
                raise U05FAR5Error(f"CORRECTED_SENTENCE_ANSWER_MISSING:{row['practice_id']}")
        elif mode == "MATCHING_KEY":
            if not answer.get("matches"):
                raise U05FAR5Error(f"MATCHING_KEY_MISSING:{row['practice_id']}")
        elif mode == "EXACT_ONE_WORD_NUMBER_OR_APPROVED_VARIANTS":
            if not answer.get("answers"):
                raise U05FAR5Error(f"STRUCTURED_ANSWER_MISSING:{row['practice_id']}")
        elif mode == "DICTATION_EXACT_OR_NORMALIZED_TRANSCRIPT":
            if not answer.get("target_transcript") or not answer.get("source_turns"):
                raise U05FAR5Error(f"DICTATION_BINDING_MISSING:{row['practice_id']}")
        elif mode in PRODUCTIVE_MODES:
            rubric_keys = set(answer)
            if not ({"rubric_dimensions", "content_points"} & rubric_keys):
                raise U05FAR5Error(f"PRODUCTIVE_RUBRIC_MISSING:{row['practice_id']}")
        else:
            raise U05FAR5Error(f"UNKNOWN_ANSWER_MODE:{row['practice_id']}:{mode}")

    if not deterministic_modes.issubset({row["answer_mode"] for row in items}):
        raise U05FAR5Error("DETERMINISTIC_MODE_COVERAGE_DRIFT")

    multi_sentence_productive = []
    for row in items:
        if row["answer_mode"] not in PRODUCTIVE_MODES:
            continue
        rc = row["response_contract"]
        output_level = rc.get("output_level")
        if output_level in {
            "O2_TWO_CONNECTED_SENTENCES",
            "O3_THREE_TO_FOUR_CONNECTED_SENTENCES",
            "O4_A1_COMMUNICATIVE_OUTPUT",
        }:
            multi_sentence_productive.append(row)
    expected_integrated_ids = {
        "U05-FAR5-P23",
        "U05-FAR5-P24",
        "U05-FAR5-P38",
        "U05-FAR5-P40",
    }
    actual_integrated_ids = {row["practice_id"] for row in multi_sentence_productive}
    if actual_integrated_ids != expected_integrated_ids:
        raise U05FAR5Error(f"FINAL_INTEGRATION_ITEM_SET_DRIFT:{sorted(actual_integrated_ids)}")
    for row in multi_sentence_productive:
        rc = row["response_contract"]
        if rc.get("final_integration_required") is not True:
            raise U05FAR5Error(f"FINAL_INTEGRATION_NOT_REQUIRED:{row['practice_id']}")
        if rc.get("final_integration_mode") not in {"WRITE_COMPLETE_VERSION", "SAY_COMPLETE_VERSION"}:
            raise U05FAR5Error(f"FINAL_INTEGRATION_MODE_DRIFT:{row['practice_id']}")
        stimulus = row.get("stimulus") or {}
        if not stimulus.get("final_integration"):
            raise U05FAR5Error(f"FINAL_INTEGRATION_PROMPT_MISSING:{row['practice_id']}")
        if not row["answer_binding_or_rubric"].get("final_integrated_model"):
            raise U05FAR5Error(f"FINAL_INTEGRATED_MODEL_MISSING:{row['practice_id']}")

    scaffold = far3["productive_scaffold_contract"]
    if scaffold["core_sequence"][-2:] != ["FINAL_INTEGRATED_VERSION", "CONNECTED_WRITING_OR_SPEAKING"]:
        raise U05FAR5Error("PRODUCTIVE_SCAFFOLD_FINAL_SEQUENCE_DRIFT")
    integration = scaffold["final_integration_contract"]
    if integration["required_for_output_of_two_or_more_sentences"] is not True:
        raise U05FAR5Error("FINAL_INTEGRATION_CONTRACT_NOT_REQUIRED")
    if integration.get("validator_ci_gate_authorized") is not True:
        raise U05FAR5Error("FINAL_INTEGRATION_OPERATOR_GATE_NOT_AUTHORIZED")

    current_ids = {row["episode_id"] for row in current["episodes"]}
    spoken_entries = {row["reader_entry_id"]: row for row in spoken["entries"]}
    spoken_episode_ids = {row["source_episode_id"] for row in spoken["entries"]}
    pattern_ids = {row["reader_entry_id"] for row in pattern["entries"]}
    for row in items:
        for ref in row["reader_source_refs"]:
            if ref.startswith("U05-NEB-"):
                if ref not in current_ids:
                    raise U05FAR5Error(f"CURRENT_REF_MISSING:{row['practice_id']}:{ref}")
            elif ref.startswith("U05-SPOKEN360-"):
                if ref not in spoken_entries:
                    raise U05FAR5Error(f"SPOKEN_REF_MISSING:{row['practice_id']}:{ref}")
            elif ref.startswith("U05-PATTERN360-"):
                if ref not in pattern_ids:
                    raise U05FAR5Error(f"PATTERN_REF_MISSING:{row['practice_id']}:{ref}")
            else:
                raise U05FAR5Error(f"UNKNOWN_READER_REF:{row['practice_id']}:{ref}")
        if row["episode_id"] not in current_ids or row["episode_id"] not in spoken_episode_ids:
            raise U05FAR5Error(f"EPISODE_TRIAD_LINEAGE_MISSING:{row['practice_id']}")

    dictation = [row for row in items if row["slot_category"] == "DELAYED_DICTATION"]
    if Counter(row["dictation_pass"] for row in dictation) != Counter({"D1": 4, "D2": 2}):
        raise U05FAR5Error("DICTATION_PASS_COUNT_DRIFT")
    d1_ids = {row["episode_id"] for row in dictation if row["dictation_pass"] == "D1"}
    for row in dictation:
        if row["execution_status"] != ASSET_PENDING_STATUS:
            raise U05FAR5Error(f"DICTATION_PREMATURELY_EXECUTABLE:{row['practice_id']}")
        if row.get("preferred_form_position") != "FINAL_RETENTION_SECTION":
            raise U05FAR5Error(f"DICTATION_NOT_FINAL_SECTION:{row['practice_id']}")
        if row.get("deferred_until_required_assets_ready") is not True:
            raise U05FAR5Error(f"DICTATION_NOT_DEFERRED:{row['practice_id']}")
        if row["dictation_pass"] == "D2" and row["episode_id"] not in d1_ids:
            raise U05FAR5Error(f"D2_WITHOUT_PILOT_D1:{row['practice_id']}")
        source_ref = row["reader_source_refs"][0]
        source_entry = spoken_entries[source_ref]
        source_turn_texts = [turn["text"] for turn in source_entry["dialogue_turns"]]
        for turn in row["answer_binding_or_rubric"]["source_turns"]:
            if turn["text"] not in source_turn_texts:
                raise U05FAR5Error(f"DICTATION_TRANSCRIPT_NOT_EXACT_SOURCE:{row['practice_id']}:{turn['text']}")
        flow = row["response_contract"].get("learner_flow", [])
        if flow != [
            "LISTEN_WITHOUT_TRANSCRIPT",
            "WRITE",
            "CHECK_AFTER_ATTEMPT",
            "LISTEN_AGAIN",
            "SAY_ALOUD",
        ]:
            raise U05FAR5Error(f"DICTATION_FLOW_DRIFT:{row['practice_id']}")

    for row in items:
        if row["practice_id"] in {f"U05-FAR5-P{i:02d}" for i in range(25, 37)} | {"U05-FAR5-P39", "U05-FAR5-P40"}:
            if row.get("preferred_form_position") != "LATE_ASSET_DEPENDENT_SECTION":
                raise U05FAR5Error(f"ASSET_TASK_NOT_LATE:{row['practice_id']}")
            if row.get("deferred_until_required_assets_ready") is not True:
                raise U05FAR5Error(f"ASSET_TASK_NOT_DEFERRED:{row['practice_id']}")

    non_retention = [row for row in items if row["slot_category"] != "DELAYED_DICTATION"]
    signatures = Counter(_visible_signature(row) for row in non_retention)
    dupes = [sig for sig, count in signatures.items() if sig and count > 1]
    if dupes:
        raise U05FAR5Error(f"DUPLICATE_VISIBLE_NON_RETENTION_ITEM_COUNT:{len(dupes)}")

    forbidden = [
        "native 25-word minimum",
        "native 35-word minimum",
    ]
    all_text = "\n".join(_flatten_strings(items)).casefold()
    if any(term in all_text for term in forbidden):
        raise U05FAR5Error("A2_NATIVE_WORD_FLOOR_LEAKAGE")

    safety = pilot["scope_safety"]
    for key in (
        "full_1632_materialization_started",
        "reader360_modified",
        "audio_generated",
        "visual_asset_generated",
        "pdf_materialized",
        "a2_grammar_unlocked",
        "a2_native_word_floor_unlocked",
        "python_learner_facing_authoring",
        "other_units_modified",
    ):
        if safety.get(key) is not False:
            raise U05FAR5Error(f"SCOPE_SAFETY_DRIFT:{key}")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "item_count": len(items),
        "core_count": category_counts["CORE_GRAMMAR"],
        "ket_count": category_counts["KET_ADAPTED"],
        "dictation_count": category_counts["DELAYED_DICTATION"],
        "text_executable_count": execution_counts[TEXT_STATUS],
        "asset_pending_count": execution_counts[ASSET_PENDING_STATUS],
        "review_pass_count": sum(
            all(row.get(key) == "PASS" for key in EXPECTED_REVIEW_KEYS) for row in items
        ),
        "final_integrated_productive_count": len(multi_sentence_productive),
        "ket_family_count": len(ket_families),
        "core_frame_count": len(core_frames),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
