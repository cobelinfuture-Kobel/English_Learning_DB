from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FAR6 is a full-1632 production preflight. It revalidates FAR2 slot identity, "
    "Reader360 lineage, FAR3 asset gates, and FAR5 operator-accepted pilot rules. "
    "It does not author learner-facing English, answers, audio, visuals, or PDFs."
)

TASK_ID = "A1FS-V1-U05FAR6_Full1632LearnerFacingPracticeMaterializationPreflight"
STATUS = "PASS_A1FS_V1_U05FAR6_FULL1632_MATERIALIZATION_PREFLIGHT"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR7_Full1632LearnerFacingPracticeMaterializationImplementation"

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "product/a1fs_v1_2_1/data"
FAR2_PATH = DATA / "unit05_coverage_driven_practice_slots.json"
FAR3_PATH = DATA / "unit05_learner_facing_practice_materialization_contract.json"
FAR4_PATH = DATA / "unit05_gpt56_practice_materialization_preflight.json"
FAR5_PATH = DATA / "unit05_gpt56_practice_pilot46.json"
FAR6_PATH = DATA / "unit05_full1632_materialization_preflight.json"
CURRENT_PATH = DATA / "unit05_current360_360.json"
SPOKEN_PATH = DATA / "unit05_spoken360_360.json"
PATTERN_PATH = DATA / "unit05_pattern360_360.json"

MULTI_SOURCE_FAMILIES = {"PERSON_TEXT_DETAIL_MATCHING", "AUDIO_LIST_MATCHING"}


class U05FAR6Error(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR6Error(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05FAR6Error(f"NOT_OBJECT:{path}")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise U05FAR6Error(code)


def _reader_sets(current: dict[str, Any], spoken: dict[str, Any], pattern: dict[str, Any]):
    return (
        {row["episode_id"] for row in current["episodes"]},
        {row["reader_entry_id"] for row in spoken["entries"]},
        {row["reader_entry_id"] for row in pattern["entries"]},
    )


def _reader_ref_resolves(mode: str | None, ref: str | None, current_ids: set[str], spoken_ids: set[str], pattern_ids: set[str]) -> bool:
    if mode is None:
        return ref is None
    if ref is None:
        return False
    if mode == "CURRENT360":
        return ref in current_ids
    if mode == "SPOKEN360":
        return ref in spoken_ids
    if mode == "PATTERN360":
        return ref in pattern_ids
    return False


def build_report() -> dict[str, Any]:
    far2 = _load(FAR2_PATH)
    far3 = _load(FAR3_PATH)
    far4 = _load(FAR4_PATH)
    far5 = _load(FAR5_PATH)
    far6 = _load(FAR6_PATH)
    current = _load(CURRENT_PATH)
    spoken = _load(SPOKEN_PATH)
    pattern = _load(PATTERN_PATH)

    _require(far6.get("task_id") == TASK_ID, "TASK_ID_DRIFT")
    _require(far6.get("status") == STATUS, "STATUS_DRIFT")
    _require(far6.get("next_short_step") == NEXT_SHORT_STEP, "NEXT_SHORT_STEP_DRIFT")

    # FAR5 is the release gate that unlocks full production.
    _require(far5["closeout"]["status"] == "PASS_A1FS_V1_U05FAR5_CLOSEOUT", "FAR5_CLOSEOUT_NOT_PASS")
    _require(far5["pilot_contract"]["item_count"] == 46, "FAR5_PILOT_COUNT_DRIFT")
    _require(far5["operator_review_disposition"]["status"] == "PASS", "FAR5_OPERATOR_REVIEW_NOT_PASS")
    _require(far5["pilot_contract"]["full_1632_materialization_unlocked"] is True, "FULL_1632_NOT_UNLOCKED")
    _require(far5["scope_safety"]["full_1632_materialization_started"] is False, "FULL_1632_ALREADY_STARTED")

    core = list(far2["core_grammar_slots"])
    ket = list(far2["ket_adapted_slots"])
    dictation = list(far2["delayed_dictation_slots"])
    all_slots = core + ket + dictation

    _require(len(core) == 480, "CORE_DENOMINATOR_DRIFT")
    _require(len(ket) == 672, "KET_DENOMINATOR_DRIFT")
    _require(len(dictation) == 480, "DICTATION_DENOMINATOR_DRIFT")
    _require(len(all_slots) == 1632, "TOTAL_DENOMINATOR_DRIFT")
    _require(len({row["slot_id"] for row in all_slots}) == 1632, "SLOT_ID_COLLISION")
    _require(len({row["practice_set_id"] for row in all_slots}) == 97, "PRACTICE_SET_COUNT_DRIFT")
    _require(
        Counter(row["materialization_state"] for row in all_slots)
        == {"SLOT_ONLY_NO_LEARNER_FACING_TEXT": 1632},
        "PREMATURE_MATERIALIZATION_STATE",
    )

    stage_counts = Counter(row["stage"] for row in all_slots)
    expected_stages = {
        "GUIDED": 288,
        "REDUCED_SUPPORT": 288,
        "INDEPENDENT": 288,
        "UNSEEN_TRANSFER": 144,
        "DELAYED_RETENTION": 624,
    }
    _require(dict(stage_counts) == expected_stages, f"STAGE_COUNT_DRIFT:{dict(stage_counts)}")

    current_ids, spoken_ids, pattern_ids = _reader_sets(current, spoken, pattern)
    _require(len(current_ids) == 360, "CURRENT360_COUNT_DRIFT")
    _require(len(spoken_ids) == 360, "SPOKEN360_COUNT_DRIFT")
    _require(len(pattern_ids) == 360, "PATTERN360_COUNT_DRIFT")

    for row in core:
        _require(
            _reader_ref_resolves(row["primary_reader_mode"], row["reader_ref"], current_ids, spoken_ids, pattern_ids),
            f"CORE_READER_REF_MISSING:{row['slot_id']}",
        )
    for row in ket:
        _require(
            _reader_ref_resolves(row["primary_reader_mode"], row["primary_reader_ref"], current_ids, spoken_ids, pattern_ids),
            f"KET_PRIMARY_READER_REF_MISSING:{row['slot_id']}",
        )
        _require(
            _reader_ref_resolves(row["companion_reader_mode"], row["companion_reader_ref"], current_ids, spoken_ids, pattern_ids),
            f"KET_COMPANION_READER_REF_MISSING:{row['slot_id']}",
        )
    for row in dictation:
        _require(row["spoken360_ref"] in spoken_ids, f"DICTATION_SPOKEN_REF_MISSING:{row['slot_id']}")

    companion_count = sum(row["companion_reader_ref"] is not None for row in ket)
    _require(companion_count == 288, "KET_COMPANION_COUNT_DRIFT")

    all_ids = {row["slot_id"] for row in all_slots}
    for row in all_slots:
        retention = row.get("retention_source_slot_id")
        if retention is not None:
            _require(retention in all_ids, f"RETENTION_SOURCE_MISSING:{row['slot_id']}")

    family_contracts = {
        row["task_family"]: row
        for row in far3["ket_adapted_materialization_contract"]["task_family_contracts"]
    }
    _require(len(family_contracts) == 14, "KET_FAMILY_CONTRACT_COUNT_DRIFT")
    _require(Counter(row["task_family"] for row in ket) == {name: 48 for name in family_contracts}, "KET_FAMILY_SLOT_DRIFT")

    media = Counter({"NO_EXTERNAL_MEDIA": len(core)})
    for row in ket:
        preconditions = set(family_contracts[row["task_family"]]["executable_preconditions"])
        audio = "AUDIO_ASSET_BOUND" in preconditions
        visual = "VISUAL_ASSET_BOUND" in preconditions
        if audio and visual:
            media["AUDIO_AND_VISUAL"] += 1
        elif audio:
            media["AUDIO_ONLY"] += 1
        elif visual:
            media["VISUAL_ONLY"] += 1
        else:
            media["NO_EXTERNAL_MEDIA"] += 1
    media["AUDIO_ONLY"] += len(dictation)
    expected_media = {
        "NO_EXTERNAL_MEDIA": 816,
        "VISUAL_ONLY": 96,
        "AUDIO_ONLY": 672,
        "AUDIO_AND_VISUAL": 48,
    }
    _require(dict(media) == expected_media, f"MEDIA_MATRIX_DRIFT:{dict(media)}")

    multi = [row for row in ket if row["task_family"] in MULTI_SOURCE_FAMILIES]
    _require(len(multi) == 96, "MULTI_SOURCE_SLOT_COUNT_DRIFT")

    # FAR4 predicted the same production surface before pilot; FAR5 must have validated it.
    readiness = far4["full_production_readiness"]
    _require(readiness["all_slots_gpt56_authoring_or_binding_ready"] is True, "FAR4_AUTHORING_READINESS_DRIFT")
    _require(readiness["external_asset_binding_required_before_executable_count"] == 816, "FAR4_ASSET_PENDING_DRIFT")
    _require(readiness["external_asset_free_slot_count"] == 816, "FAR4_ASSET_FREE_DRIFT")
    _require(readiness["multi_source_bundle_review_required_count"] == 96, "FAR4_MULTI_SOURCE_DRIFT")

    # Operator-approved pilot findings are now full-production rules.
    promoted = set(far6["far5_pilot_rules_promoted_to_full_materialization"])
    required_rules = {
        "SENTENCE_CORRECTION_USES_EXACT_CORRECTED_SENTENCE_OR_APPROVED_VARIANTS",
        "LEXICAL_CLOZE_REQUIRES_CONNECTED_CONTEXT",
        "OPEN_CLOZE_REQUIRES_CONNECTED_CONTEXT",
        "MULTI_SENTENCE_PRODUCTIVE_TASKS_REQUIRE_FINAL_INTEGRATED_VERSION",
        "PICTURE_AND_AUDIO_TASKS_REMAIN_LATE_WHILE_ASSET_PENDING",
        "VISUAL_SPEAKING_STAYS_UNIT05_DESCRIPTION_NOT_OPINION_HEAVY",
        "DELAYED_DICTATION_STAYS_FINAL_RETENTION_LISTEN_WRITE_CHECK_LISTEN_SPEAK",
        "DO_NOT_REINTRODUCE_OUT_OF_SCOPE_PREREQUISITES_SUCH_AS_UNCONTROLLED_IRREGULAR_PLURAL_DEMAND",
    }
    _require(promoted == required_rules, "PROMOTED_PILOT_RULE_SET_DRIFT")

    tx = far6["implementation_transaction_contract"]
    _require(tx["next_milestone_must_materialize_all_1632_slot_identities"] is True, "FULL_DENOMINATOR_NOT_REQUIRED")
    _require(tx["one_milestone_not_one_pr_per_practice_set"] is True, "PR_FRAGMENTATION_UNLOCKED")
    _require(tx["final_authority_file_count"] == 3, "FINAL_AUTHORITY_FILE_COUNT_DRIFT")
    _require(
        tx["final_authority_files"]
        == [
            "product/a1fs_v1_2_1/data/unit05_core_practice_480.json",
            "product/a1fs_v1_2_1/data/unit05_ket_adapted_practice_672.json",
            "product/a1fs_v1_2_1/data/unit05_dictation_practice_480.json",
        ],
        "FINAL_AUTHORITY_PATH_DRIFT",
    )
    _require(tx["python_may_author_rewrite_paraphrase_repair_or_choose_semantic_answers"] is False, "PYTHON_AUTHORING_UNLOCKED")
    _require(tx["learner_facing_author_and_semantic_reviewer"] == "GPT-5.6 Sol", "AUTHOR_MODEL_DRIFT")

    safety = far6["scope_safety"]
    _require(safety["learner_facing_items_materialized_in_far6"] == 0, "FAR6_PREMATURE_LEARNER_CONTENT")
    for key in (
        "reader360_modified",
        "far2_modified",
        "far3_modified",
        "far4_modified",
        "far5_modified",
        "audio_generated",
        "visual_assets_generated",
        "pdf_materialized",
        "a2_grammar_unlocked",
        "a2_native_task_demand_unlocked",
        "other_units_modified",
    ):
        _require(safety[key] is False, f"FAR6_SCOPE_SAFETY_DRIFT:{key}")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "practice_slot_denominator": 1632,
        "unique_slot_id_count": 1632,
        "practice_set_count": 97,
        "gpt56_authoring_ready_slot_count": 1632,
        "external_asset_free_after_authoring_count": 816,
        "external_asset_required_for_execution_count": 816,
        "multi_source_bundle_review_required_count": 96,
        "reader_lineage_missing_count": 0,
        "learner_facing_items_materialized_in_far6": 0,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
