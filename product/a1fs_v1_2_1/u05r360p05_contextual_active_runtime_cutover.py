from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from product.a1fs_v1_2_1 import (
    u05q10r1_unit05_learner_facing_pedagogical_acceptance as legacy_q10r1,
)
from ulga.builders import (
    build_a1fs_v1_u05q10_questionbank_form_materialization as q10,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Runtime routing-only consumer. It binds the already approved Unit05 Q10/Q10R1 "
    "slot identities to the already GPT-5.6-authored Current360, Spoken360, and "
    "Pattern360 consolidated corpora. Python may route, index, count, and validate "
    "existing learner-facing text but may not generate, rewrite, paraphrase, or "
    "repair learner-facing English."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_PRESENT_BE_IDENTITY_DESCRIPTION_STATE_LOCATION"
TASK_ID = "A1FS-V1-U05R360P05_ContextualActiveRuntimeCutover"
STATUS = "PASS_A1FS_V1_U05R360P05_CONTEXTUAL_ACTIVE_RUNTIME_CUTOVER"
REVISION = "UNIT05_READER360_TRIAD_CONTEXTUAL_ACTIVE_RUNTIME_V1"
NEXT_SHORT_STEP = "A1FS-V1-U05R360P06_ThreeReaderFormalPDFMaterialization"

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
SECTION_COUNTS = {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
PRIMARY_MODE_BY_SECTION = {
    "A": "PATTERN360",
    "B": "CURRENT360",
    "C": "PATTERN360",
    "D": "CURRENT360",
    "E": "SPOKEN360",
}
AVAILABLE_READER_MODES = ("CURRENT360", "SPOKEN360", "PATTERN360")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "product/a1fs_v1_2_1/data"
CURRENT360_PATH = DATA_DIR / "unit05_current360_360.json"
SPOKEN360_PATH = DATA_DIR / "unit05_spoken360_360.json"
PATTERN360_PATH = DATA_DIR / "unit05_pattern360_360.json"


class Unit05R360P05Error(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Unit05R360P05Error(f"MISSING_READER_AUTHORITY:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Unit05R360P05Error(f"READER_AUTHORITY_NOT_OBJECT:{path}")
    return value


def _reader_authorities() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    current = _load_json(CURRENT360_PATH)
    spoken = _load_json(SPOKEN360_PATH)
    pattern = _load_json(PATTERN360_PATH)

    if current.get("episode_count") != 360 or len(current.get("episodes") or []) != 360:
        raise Unit05R360P05Error("CURRENT360_COUNT_DRIFT")
    if spoken.get("entry_count") != 360 or len(spoken.get("entries") or []) != 360:
        raise Unit05R360P05Error("SPOKEN360_COUNT_DRIFT")
    if pattern.get("entry_count") != 360 or len(pattern.get("entries") or []) != 360:
        raise Unit05R360P05Error("PATTERN360_COUNT_DRIFT")

    current_ids = [str(row["episode_id"]) for row in current["episodes"]]
    spoken_ids = [str(row["source_episode_id"]) for row in spoken["entries"]]
    pattern_ids = [str(row["source_episode_id"]) for row in pattern["entries"]]
    expected = [f"U05-NEB-E{i:03d}" for i in range(1, 361)]
    if current_ids != expected or spoken_ids != expected or pattern_ids != expected:
        raise Unit05R360P05Error("READER360_EPISODE_ALIGNMENT_DRIFT")

    return current, spoken, pattern


def _episode_number(form_number: int, activity_ordinal: int) -> int:
    if not 1 <= form_number <= FORM_COUNT:
        raise Unit05R360P05Error(f"FORM_OUT_OF_RANGE:{form_number}")
    if not 1 <= activity_ordinal <= ACTIVITIES_PER_FORM:
        raise Unit05R360P05Error(f"ACTIVITY_OUT_OF_RANGE:{activity_ordinal}")

    global_index = (form_number - 1) * ACTIVITIES_PER_FORM + activity_ordinal
    if form_number <= 12:
        return 1 + ((global_index - 1) % 216)
    transfer_index = global_index - (12 * ACTIVITIES_PER_FORM)
    return 217 + ((transfer_index - 1) % 144)


def _legacy_activity_index(report: Mapping[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    index: dict[tuple[int, int], dict[str, Any]] = {}
    for form in report.get("learner_forms") or []:
        form_number = int(form["form_ordinal"])
        activities = list(form.get("activities") or [])
        if len(activities) != ACTIVITIES_PER_FORM:
            raise Unit05R360P05Error(
                f"LEGACY_FORM_ACTIVITY_COUNT_DRIFT:F{form_number:02d}:{len(activities)}"
            )
        for ordinal, activity in enumerate(activities, start=1):
            index[(form_number, ordinal)] = dict(activity)
    if len(index) != TOTAL_ACTIVITIES:
        raise Unit05R360P05Error(f"LEGACY_ACTIVITY_INDEX_DRIFT:{len(index)}")
    return index


def build_unit05_r360_p05_contextual_active_runtime_cutover() -> dict[str, Any]:
    source = q10.build_export_payload()
    if source.get("status") != q10.PASS_STATUS:
        raise Unit05R360P05Error("Q10_SOURCE_NOT_PASS")
    if len(source.get("runtime_bindings") or []) != TOTAL_ACTIVITIES:
        raise Unit05R360P05Error("Q10_RUNTIME_COUNT_DRIFT")
    if len(source.get("questionbank_items") or []) != TOTAL_ACTIVITIES:
        raise Unit05R360P05Error("Q10_ITEM_COUNT_DRIFT")

    legacy = legacy_q10r1.build_acceptance_report(source)
    if legacy.get("status") != legacy_q10r1.PASS_STATUS:
        raise Unit05R360P05Error("Q10R1_SOURCE_NOT_PASS")
    legacy_activity = _legacy_activity_index(legacy)

    current, spoken, pattern = _reader_authorities()
    current_index = {str(row["episode_id"]): row for row in current["episodes"]}
    spoken_index = {str(row["source_episode_id"]): row for row in spoken["entries"]}
    pattern_index = {str(row["source_episode_id"]): row for row in pattern["entries"]}
    item_index = {str(row["item_id"]): row for row in source["questionbank_items"]}

    runtime_bindings: list[dict[str, Any]] = []
    active_items: list[dict[str, Any]] = []
    forms: list[dict[str, Any]] = []
    section_ordinal: Counter[str] = Counter()
    primary_mode_counts: Counter[str] = Counter()
    episode_counts: Counter[str] = Counter()
    seen_episode_ids: set[str] = set()
    unseen_episode_ids: set[str] = set()

    for runtime_position, source_runtime in enumerate(source["runtime_bindings"], start=1):
        form_number = int(source_runtime["form_number"])
        section = str(source_runtime["section"])
        ordinal_in_form = ((runtime_position - 1) % ACTIVITIES_PER_FORM) + 1
        section_ordinal[section] += 1

        expected_section_count = SECTION_COUNTS.get(section)
        if expected_section_count is None:
            raise Unit05R360P05Error(f"UNKNOWN_SECTION:{section}")

        episode_number = _episode_number(form_number, ordinal_in_form)
        episode_id = f"U05-NEB-E{episode_number:03d}"
        current_row = current_index[episode_id]
        spoken_row = spoken_index[episode_id]
        pattern_row = pattern_index[episode_id]
        primary_mode = PRIMARY_MODE_BY_SECTION[section]

        if form_number <= 12:
            seen_episode_ids.add(episode_id)
        else:
            unseen_episode_ids.add(episode_id)
        episode_counts[episode_id] += 1
        primary_mode_counts[primary_mode] += 1

        selected_item_id = str(source_runtime["selected_item_id"])
        source_item = item_index[selected_item_id]
        activity = legacy_activity[(form_number, ordinal_in_form)]

        triad = {
            "source_episode_id": episode_id,
            "current360_ref": str(current_row["episode_id"]),
            "spoken360_ref": str(spoken_row["reader_entry_id"]),
            "pattern360_ref": str(pattern_row["reader_entry_id"]),
        }
        identity = {
            "slot_id": str(source_runtime["slot_id"]),
            "selected_item_id": selected_item_id,
            "episode_id": episode_id,
            "primary_mode": primary_mode,
            "revision": REVISION,
        }
        active_item_id = (
            f"U05R360P05-F{form_number:02d}-{section}{int(source_item['section_activity_ordinal']):02d}-"
            f"{_digest(identity)[:12].upper()}"
        )

        runtime_bindings.append({
            "active_item_id": active_item_id,
            "slot_id": str(source_runtime["slot_id"]),
            "form_number": form_number,
            "section": section,
            "section_activity_ordinal": int(source_item["section_activity_ordinal"]),
            "primary_reader_mode": primary_mode,
            "available_reader_modes": list(AVAILABLE_READER_MODES),
            "reader_triad": triad,
            "source_q10_lineage": {
                "selected_item_id": selected_item_id,
                "candidate_ids": list(source_runtime["candidate_ids"]),
                "task_family_id": str(source_runtime["task_family_id"]),
                "selection_policy": str(source_runtime["selection_policy"]),
            },
        })
        active_items.append({
            "active_item_id": active_item_id,
            "form_number": form_number,
            "section": section,
            "section_activity_ordinal": int(source_item["section_activity_ordinal"]),
            "progression_stage": str(
                source["forms"][form_number - 1]["progression_role"]
            ),
            "primary_reader_mode": primary_mode,
            "available_reader_modes": list(AVAILABLE_READER_MODES),
            "learner_activity_shell": activity,
            "reader_triad": triad,
            "source_q10_item_id": selected_item_id,
            "reader_payload_refs": {
                "current360_episode_id": str(current_row["episode_id"]),
                "spoken360_reader_entry_id": str(spoken_row["reader_entry_id"]),
                "pattern360_reader_entry_id": str(pattern_row["reader_entry_id"]),
            },
        })

    if len(runtime_bindings) != TOTAL_ACTIVITIES or len(active_items) != TOTAL_ACTIVITIES:
        raise Unit05R360P05Error("ACTIVE_RUNTIME_DENOMINATOR_DRIFT")
    if len({row["active_item_id"] for row in active_items}) != TOTAL_ACTIVITIES:
        raise Unit05R360P05Error("ACTIVE_ITEM_ID_COLLISION")
    if seen_episode_ids & unseen_episode_ids:
        raise Unit05R360P05Error("SEEN_UNSEEN_EPISODE_OVERLAP")
    if seen_episode_ids != {f"U05-NEB-E{i:03d}" for i in range(1, 217)}:
        raise Unit05R360P05Error("SEEN_EPISODE_POOL_DRIFT")
    if unseen_episode_ids != {f"U05-NEB-E{i:03d}" for i in range(217, 361)}:
        raise Unit05R360P05Error("UNSEEN_EPISODE_POOL_DRIFT")
    if set(episode_counts) != {f"U05-NEB-E{i:03d}" for i in range(1, 361)}:
        raise Unit05R360P05Error("FULL360_RUNTIME_EPISODE_COVERAGE_DRIFT")

    for form_number in range(1, FORM_COUNT + 1):
        rows = [
            row for row in active_items
            if int(row["form_number"]) == form_number
        ]
        if len(rows) != ACTIVITIES_PER_FORM:
            raise Unit05R360P05Error(f"FORM_RUNTIME_COUNT_DRIFT:F{form_number:02d}")
        counts = Counter(str(row["section"]) for row in rows)
        if dict(counts) != SECTION_COUNTS:
            raise Unit05R360P05Error(
                f"FORM_SECTION_COUNT_DRIFT:F{form_number:02d}:{dict(counts)}"
            )
        forms.append({
            "form_number": form_number,
            "form_id": f"U05R360P05-F{form_number:02d}",
            "progression_stage": str(source["forms"][form_number - 1]["progression_role"]),
            "activity_count": len(rows),
            "section_counts": dict(counts),
            "active_item_ids": [str(row["active_item_id"]) for row in rows],
        })

    current_rows = list(current["episodes"])
    spoken_rows = list(spoken["entries"])
    pattern_rows = list(pattern["entries"])

    report = {
        "schema_version": "a1fs.v1.u05.r360.p05.contextual_active_runtime_cutover.v1",
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_authority": {
            "q10_task_id": q10.TASK_ID,
            "q10_status": q10.PASS_STATUS,
            "legacy_q10r1_task_id": legacy_q10r1.TASK_ID,
            "legacy_q10r1_status": legacy_q10r1.PASS_STATUS,
            "current360": "product/a1fs_v1_2_1/data/unit05_current360_360.json",
            "spoken360": "product/a1fs_v1_2_1/data/unit05_spoken360_360.json",
            "pattern360": "product/a1fs_v1_2_1/data/unit05_pattern360_360.json",
        },
        "cutover_contract": {
            "active_contextual_runtime_authority": TASK_ID,
            "parallel_active_contextual_runtime_allowed": False,
            "q10_role": "ITEM_CANDIDATE_AND_SLOT_LINEAGE_ONLY",
            "legacy_q10r1_role": "SUPERSEDED_AS_ACTIVE_CONTEXTUAL_RUNTIME_LEARNER_SHELL_REUSED",
            "reader360_role": "ACTIVE_CONTEXTUAL_CONTENT_AUTHORITY",
            "current360_role": "CONNECTED_READING_CONTEXT_AUTHORITY",
            "spoken360_role": "INTERACTION_CONTEXT_AUTHORITY",
            "pattern360_role": "SENTENCE_FAMILY_AND_GRAMMAR_TRANSFER_AUTHORITY",
            "reader_triad_episode_alignment_required": True,
            "reader_content_rewrite_allowed": False,
        },
        "materialization_contract": {
            "form_count": FORM_COUNT,
            "activities_per_form": ACTIVITIES_PER_FORM,
            "activity_count": TOTAL_ACTIVITIES,
            "section_counts_per_form": dict(SECTION_COUNTS),
            "available_reader_modes": list(AVAILABLE_READER_MODES),
            "primary_mode_by_section": dict(PRIMARY_MODE_BY_SECTION),
            "current360_authority_count": len(current_rows),
            "spoken360_authority_count": len(spoken_rows),
            "pattern360_authority_count": len(pattern_rows),
            "runtime_distinct_episode_count": len(episode_counts),
            "seen_episode_count": len(seen_episode_ids),
            "unseen_episode_count": len(unseen_episode_ids),
        },
        "coverage": {
            "reader360_episode_coverage": "360/360",
            "current360_runtime_reachable_episode_count": len(episode_counts),
            "spoken360_runtime_reachable_episode_count": len(episode_counts),
            "pattern360_runtime_reachable_episode_count": len(episode_counts),
            "seen_unseen_overlap_count": len(seen_episode_ids & unseen_episode_ids),
            "primary_mode_counts": dict(primary_mode_counts),
            "episode_runtime_occurrence_min": min(episode_counts.values()),
            "episode_runtime_occurrence_max": max(episode_counts.values()),
        },
        "reader_authorities": {
            "current360": current_rows,
            "spoken360": spoken_rows,
            "pattern360": pattern_rows,
        },
        "forms": forms,
        "active_items": active_items,
        "runtime_bindings": runtime_bindings,
        "safety": {
            "q10_source_modified": False,
            "q10r1_source_modified": False,
            "current360_modified": False,
            "spoken360_modified": False,
            "pattern360_modified": False,
            "python_generated_or_rewrote_reader_english": False,
            "parallel_runtime_created": False,
            "pdf_materialized": False,
            "be_interrogative_mastery_unlocked": False,
            "past_be_unlocked": False,
            "present_continuous_unlocked": False,
            "existential_there_be_unlocked": False,
            "a2_a2plus_unlocked": False,
            "other_units_modified": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report["deterministic_runtime_sha256"] = _digest({
        "forms": forms,
        "active_items": active_items,
        "runtime_bindings": runtime_bindings,
    })
    return report


def compact_readback(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": report["task_id"],
        "status": report["status"],
        "revision": report["revision"],
        "forms": report["materialization_contract"]["form_count"],
        "activities": report["materialization_contract"]["activity_count"],
        "reader360_episode_coverage": report["coverage"]["reader360_episode_coverage"],
        "primary_mode_counts": report["coverage"]["primary_mode_counts"],
        "seen_episode_count": report["materialization_contract"]["seen_episode_count"],
        "unseen_episode_count": report["materialization_contract"]["unseen_episode_count"],
        "next_short_step": report["next_short_step"],
    }


def main() -> int:
    report = build_unit05_r360_p05_contextual_active_runtime_cutover()
    print(json.dumps(compact_readback(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
