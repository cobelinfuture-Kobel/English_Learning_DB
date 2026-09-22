from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U05R360P04H1_Spoken360AndPattern360ConsolidatedJSONHandoff"
STATUS = "PASS_A1FS_V1_U05_R360_P04H1_CONSOLIDATED_JSON_HANDOFF"
NEXT_SHORT_STEP = "A1FS-V1-U05R360P05_ContextualActiveRuntimeCutover"

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "product/a1fs_v1_2_1/data"

CURRENT_PATH = DATA_DIR / "unit05_current360_360.json"
SPOKEN_PATH = DATA_DIR / "unit05_spoken360_360.json"
PATTERN_PATH = DATA_DIR / "unit05_pattern360_360.json"

SPOKEN_SHARDS = tuple(
    DATA_DIR / f"u05r360p03_spoken360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)
PATTERN_SHARDS = tuple(
    DATA_DIR / f"u05r360p04_pattern360_gpt56_e{start:03d}_e{start+29:03d}.json"
    for start in range(1, 361, 30)
)


class U05R360ConsolidatedHandoffError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05R360ConsolidatedHandoffError(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05R360ConsolidatedHandoffError(f"NOT_OBJECT:{path}")
    return value


def _concat_entries(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(list(_load(path).get("entries") or []))
    return rows


def build_report() -> dict[str, Any]:
    current = _load(CURRENT_PATH)
    spoken = _load(SPOKEN_PATH)
    pattern = _load(PATTERN_PATH)

    current_entries = list(current.get("episodes") or [])
    spoken_entries = list(spoken.get("entries") or [])
    pattern_entries = list(pattern.get("entries") or [])

    shard_spoken = _concat_entries(SPOKEN_SHARDS)
    shard_pattern = _concat_entries(PATTERN_SHARDS)

    if len(current_entries) != 360:
        raise U05R360ConsolidatedHandoffError(f"CURRENT_COUNT:{len(current_entries)}")
    if len(spoken_entries) != 360:
        raise U05R360ConsolidatedHandoffError(f"SPOKEN_COUNT:{len(spoken_entries)}")
    if len(pattern_entries) != 360:
        raise U05R360ConsolidatedHandoffError(f"PATTERN_COUNT:{len(pattern_entries)}")

    if spoken_entries != shard_spoken:
        raise U05R360ConsolidatedHandoffError("SPOKEN_CONSOLIDATED_DIFFERS_FROM_SHARDS")
    if pattern_entries != shard_pattern:
        raise U05R360ConsolidatedHandoffError("PATTERN_CONSOLIDATED_DIFFERS_FROM_SHARDS")

    for index, row in enumerate(spoken_entries, start=1):
        suffix = f"{index:03d}"
        if row["reader_entry_id"] != f"U05-SPOKEN360-E{suffix}":
            raise U05R360ConsolidatedHandoffError(
                f"SPOKEN_ID_ORDER:{row['reader_entry_id']}"
            )
        if row["source_episode_id"] != f"U05-NEB-E{suffix}":
            raise U05R360ConsolidatedHandoffError(
                f"SPOKEN_SOURCE_ORDER:{row['source_episode_id']}"
            )

    for index, row in enumerate(pattern_entries, start=1):
        suffix = f"{index:03d}"
        if row["reader_entry_id"] != f"U05-PATTERN360-E{suffix}":
            raise U05R360ConsolidatedHandoffError(
                f"PATTERN_ID_ORDER:{row['reader_entry_id']}"
            )
        if row["source_episode_id"] != f"U05-NEB-E{suffix}":
            raise U05R360ConsolidatedHandoffError(
                f"PATTERN_SOURCE_ORDER:{row['source_episode_id']}"
            )

    example_count = sum(
        len(family["examples"])
        for row in pattern_entries
        for family in row["families"].values()
    )
    if example_count != pattern.get("example_count"):
        raise U05R360ConsolidatedHandoffError(
            f"PATTERN_EXAMPLE_COUNT_DRIFT:{example_count}:{pattern.get('example_count')}"
        )

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "current360_count": len(current_entries),
        "spoken360_count": len(spoken_entries),
        "pattern360_count": len(pattern_entries),
        "pattern360_example_count": example_count,
        "spoken_exact_shard_equality": True,
        "pattern_exact_shard_equality": True,
        "learner_facing_language_rewritten_during_consolidation": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    report = build_report()
    for key, value in report.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
