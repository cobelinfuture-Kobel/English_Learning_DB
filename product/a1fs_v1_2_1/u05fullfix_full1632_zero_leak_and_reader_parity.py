from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "VALIDATOR_ONLY"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FullFix closeout validator only. It verifies zero irregular-plural leakage, "
    "Reader360 consolidated/shard parity, Full1632 identity denominators, and "
    "Dictation480 exact Spoken360 lineage. It does not author learner-facing English."
)

TASK_ID = "A1FS-V1-U05FULLFIX_Full1632ZeroLeakValidationAndFinalReaderShardParityRecheck"
STATUS = "PASS_A1FS_V1_U05FULLFIX_FULL1632_ZERO_LEAK_AND_READER_SHARD_PARITY"
NEXT_SHORT_STEP = "A1FS-V1-U05FULLFIX_CompactPDFRegeneration"

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "product/a1fs_v1_2_1/data"

CURRENT = DATA / "unit05_current360_360.json"
SPOKEN = DATA / "unit05_spoken360_360.json"
PATTERN = DATA / "unit05_pattern360_360.json"
CORE = DATA / "unit05_core_practice_480.json"
KET = DATA / "unit05_ket_adapted_practice_672.json"
DICTATION = DATA / "unit05_dictation_practice_480.json"

CURRENT_SHARDS = tuple(
    DATA / f"u05r360p02_current360_gpt56_{suffix}.json"
    for suffix in (
        "e001_e060", "e061_e120", "e121_e180",
        "e181_e240", "e241_e300", "e301_e360",
    )
)
SPOKEN_SHARDS = tuple(
    DATA / f"u05r360p03_spoken360_gpt56_{suffix}.json"
    for suffix in (
        "e001_e060", "e061_e120", "e121_e180",
        "e181_e240", "e241_e300", "e301_e360",
    )
)
PATTERN_SHARDS = tuple(
    DATA / f"u05r360p04_pattern360_gpt56_{suffix}.json"
    for suffix in (
        "e001_e030", "e031_e060", "e061_e090", "e091_e120",
        "e121_e150", "e151_e180", "e181_e210", "e211_e240",
        "e241_e270", "e271_e300", "e301_e330", "e331_e360",
    )
)

BANNED_IRREGULAR_PLURAL_TOKENS = ("children", "people", "feet", "men", "women")
TOKEN_RE = re.compile(r"[A-Za-z']+")


class U05FullFixCloseoutError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FullFixCloseoutError(f"MISSING:{path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise U05FullFixCloseoutError(f"NOT_OBJECT:{path}")
    return obj


def _req(ok: bool, code: str) -> None:
    if not ok:
        raise U05FullFixCloseoutError(code)


def _concat(paths: tuple[Path, ...], key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        obj = _load(path)
        part = obj.get(key)
        _req(isinstance(part, list), f"SHARD_ROWS_NOT_LIST:{path.name}:{key}")
        rows.extend(part)
    return rows


def _leak_tokens(obj: Any) -> list[str]:
    tokens = set(TOKEN_RE.findall(json.dumps(obj, ensure_ascii=False).lower()))
    return [token for token in BANNED_IRREGULAR_PLURAL_TOKENS if token in tokens]


def build_report() -> dict[str, Any]:
    current = _load(CURRENT)
    spoken = _load(SPOKEN)
    pattern = _load(PATTERN)
    core = _load(CORE)
    ket = _load(KET)
    dictation = _load(DICTATION)

    current_rows = list(current.get("episodes") or [])
    spoken_rows = list(spoken.get("entries") or [])
    pattern_rows = list(pattern.get("entries") or [])

    current_shard_rows = _concat(CURRENT_SHARDS, "episodes")
    spoken_shard_rows = _concat(SPOKEN_SHARDS, "entries")
    pattern_shard_rows = _concat(PATTERN_SHARDS, "entries")

    _req(len(current_rows) == 360, f"CURRENT360_COUNT:{len(current_rows)}")
    _req(len(spoken_rows) == 360, f"SPOKEN360_COUNT:{len(spoken_rows)}")
    _req(len(pattern_rows) == 360, f"PATTERN360_COUNT:{len(pattern_rows)}")
    _req(current_rows == current_shard_rows, "CURRENT360_CONSOLIDATED_DIFFERS_FROM_SHARDS")
    _req(spoken_rows == spoken_shard_rows, "SPOKEN360_CONSOLIDATED_DIFFERS_FROM_SHARDS")
    _req(pattern_rows == pattern_shard_rows, "PATTERN360_CONSOLIDATED_DIFFERS_FROM_SHARDS")

    _req(core.get("item_count") == 480 and len(core.get("items") or []) == 480, "CORE480_DENOMINATOR_DRIFT")
    _req(core.get("authored_item_count") == 480, "CORE480_AUTHORING_DRIFT")
    _req(ket.get("item_count") == 672 and len(ket.get("items") or []) == 672, "KET672_DENOMINATOR_DRIFT")
    _req(ket.get("authored_item_count") == 672, "KET672_AUTHORING_DRIFT")
    _req(ket.get("executable_text_only_count") == 336, "KET672_TEXT_EXECUTABLE_DRIFT")
    _req(ket.get("asset_pending_count") == 336, "KET672_MEDIA_PENDING_DRIFT")
    _req(dictation.get("item_count") == 480 and len(dictation.get("items") or []) == 480, "DICTATION480_DENOMINATOR_DRIFT")
    _req(dictation.get("authored_item_count") == 480, "DICTATION480_AUTHORING_DRIFT")
    _req(dictation.get("d1_authored_count") == 360 and dictation.get("d2_authored_count") == 120, "DICTATION_D1_D2_DRIFT")
    _req(dictation.get("executable_count") == 0 and dictation.get("asset_pending_count") == 480, "DICTATION_ASSET_BOUNDARY_DRIFT")

    all_items = list(core["items"]) + list(ket["items"]) + list(dictation["items"])
    _req(len(all_items) == 1632, "FULL1632_DENOMINATOR_DRIFT")
    _req(len({row["practice_id"] for row in all_items}) == 1632, "PRACTICE_ID_COLLISION")
    _req(len({row["source_slot_id"] for row in all_items}) == 1632, "SOURCE_SLOT_COLLISION")

    core_archetypes = Counter(row["target_archetype"] for row in core["items"])
    _req(len(core_archetypes) == 6 and set(core_archetypes.values()) == {80}, f"CORE_ARCHETYPE_BALANCE_DRIFT:{dict(core_archetypes)}")
    ket_families = Counter(row["task_family"] for row in ket["items"])
    _req(len(ket_families) == 14 and set(ket_families.values()) == {48}, f"KET_FAMILY_BALANCE_DRIFT:{dict(ket_families)}")

    scan_artifacts: list[tuple[str, Any]] = [
        ("current360", current),
        ("spoken360", spoken),
        ("pattern360", pattern),
        ("core480", core),
        ("ket672", ket),
        ("dictation480", dictation),
    ]
    scan_artifacts.extend((path.name, _load(path)) for path in CURRENT_SHARDS)
    scan_artifacts.extend((path.name, _load(path)) for path in SPOKEN_SHARDS)
    scan_artifacts.extend((path.name, _load(path)) for path in PATTERN_SHARDS)

    leak_by_artifact: dict[str, list[str]] = {}
    for name, obj in scan_artifacts:
        hits = _leak_tokens(obj)
        if hits:
            leak_by_artifact[name] = hits
    _req(not leak_by_artifact, f"IRREGULAR_PLURAL_LEAK:{leak_by_artifact}")

    spoken_by_ref = {row["reader_entry_id"]: row for row in spoken_rows}
    d1_by_episode = {
        row["episode_id"]: row
        for row in dictation["items"]
        if row["dictation_pass"] == "D1"
    }

    source_mismatches: list[str] = []
    retention_mismatches: list[str] = []
    for row in dictation["items"]:
        practice_id = row["practice_id"]
        entry = spoken_by_ref.get(row["spoken360_ref"])
        if entry is None:
            source_mismatches.append(f"{practice_id}:SPOKEN_REF_MISSING")
            continue
        indexes = row["selected_segment"]["source_turn_indexes"]
        if not all(isinstance(i, int) and 0 <= i < len(entry["dialogue_turns"]) for i in indexes):
            source_mismatches.append(f"{practice_id}:TURN_INDEX_INVALID")
            continue
        exact_turns = [entry["dialogue_turns"][i] for i in indexes]
        answer = row["answer_binding_or_rubric"]
        if answer["source_turns"] != exact_turns:
            source_mismatches.append(f"{practice_id}:SOURCE_TURNS")
        if answer["target_transcript"] != " ".join(turn["text"] for turn in exact_turns):
            source_mismatches.append(f"{practice_id}:TARGET_TRANSCRIPT")
        core_index = row["selected_segment"]["core_d1_turn_index"]
        if entry["dialogue_turns"][core_index]["text"] != row["selected_segment"]["core_d1_target_text"]:
            source_mismatches.append(f"{practice_id}:CORE_D1_TARGET")

        if row["dictation_pass"] == "D2":
            d1 = d1_by_episode.get(row["episode_id"])
            if d1 is None:
                retention_mismatches.append(f"{practice_id}:D1_EPISODE_MISSING")
                continue
            if row["retention_source_slot_id"] != d1["source_slot_id"]:
                retention_mismatches.append(f"{practice_id}:RETENTION_SLOT")
            if row["response_contract"]["retention_source_practice_id"] != d1["practice_id"]:
                retention_mismatches.append(f"{practice_id}:RETENTION_PRACTICE")
            if row["selected_segment"]["core_d1_target_text"] != d1["selected_segment"]["core_d1_target_text"]:
                retention_mismatches.append(f"{practice_id}:CORE_TARGET")
            if row["selected_segment"]["core_d1_turn_index"] != d1["selected_segment"]["core_d1_turn_index"]:
                retention_mismatches.append(f"{practice_id}:CORE_TURN")
            if d1["answer_binding_or_rubric"]["target_transcript"] not in answer["target_transcript"]:
                retention_mismatches.append(f"{practice_id}:D1_TRANSCRIPT_NOT_RETAINED")

    _req(not source_mismatches, f"DICTATION_SPOKEN360_MISMATCH:{source_mismatches[:10]}")
    _req(not retention_mismatches, f"DICTATION_D2_LINEAGE_MISMATCH:{retention_mismatches[:10]}")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "reader_counts": {"current360": 360, "spoken360": 360, "pattern360": 360},
        "current_exact_shard_equality": True,
        "spoken_exact_shard_equality": True,
        "pattern_exact_shard_equality": True,
        "full1632_count": 1632,
        "unique_practice_id_count": 1632,
        "unique_source_slot_id_count": 1632,
        "core_archetype_counts": dict(core_archetypes),
        "ket_family_counts": dict(ket_families),
        "banned_irregular_plural_tokens": list(BANNED_IRREGULAR_PLURAL_TOKENS),
        "zero_leak_artifact_count": len(scan_artifacts),
        "zero_leak_violation_count": 0,
        "dictation_spoken360_mismatch_count": 0,
        "dictation_d2_lineage_mismatch_count": 0,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
