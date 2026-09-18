from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb02

TASK_ID = "A1FS-V1-U04R360-B01_Reader360E004E030Acceptance"
STATUS = "PASS_A1FS_V1_U04R360_B01_E004_E030"
SPOKEN_PATH = "product/a1fs_v1_2_1/u04reader360_spoken_dialogue_reader_partial.json"
PATTERN_PATH = "product/a1fs_v1_2_1/u04reader360_pattern_sentence_family_reader_partial.json"
EXPECTED_IDS = tuple(f"U04-NEB-E{i:03d}" for i in range(4, 31))
EXPECTED_FAMILIES = tuple("ABCDEFG")
BLOCKED_LEARNER_SURFACES = (
    r"\bwhile\b",
    r"\balmost\b",
    r"\balready\b",
    r"\bmust\b",
    r"\bshould\b",
    r"\bwill\b",
    r"\bnearly\b",
    r"\buntil\b",
    r"\bacross\b",
    r"\binto\b",
    r"\bremembers where\b",
)

class Reader360BatchAcceptanceError(ValueError):
    pass

def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]

def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Reader360BatchAcceptanceError(f"missing_reader_json:{path}")
    return json.loads(path.read_text(encoding="utf-8"))

def _rels(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(",") if part.strip()]

def _check_text(text: str, ref: str) -> None:
    value = text.strip()
    if not value:
        raise Reader360BatchAcceptanceError(f"empty_learner_text:{ref}")
    if "___" in value or "[...]" in value or "{blank}" in value.casefold():
        raise Reader360BatchAcceptanceError(f"worksheet_blank_leaked:{ref}")
    for pattern in BLOCKED_LEARNER_SURFACES:
        if re.search(pattern, value, flags=re.I):
            raise Reader360BatchAcceptanceError(f"a1_boundary_surface:{ref}:{pattern}:{value}")

def _check_contract(payload: dict[str, Any], label: str) -> None:
    approved = payload.get("approved_sample_e001_e003", {})
    if approved != {
        "status": "APPROVED_PREEXISTING_NOT_REWRITTEN_IN_THIS_BATCH",
        "included_in_this_file": False,
    }:
        raise Reader360BatchAcceptanceError(f"{label}_approved_sample_contract_drift")
    contract = payload.get("authoring_contract", {})
    required_false = (
        "python_may_compose_learner_facing_english",
        "reader_is_question_worksheet",
        "pdf_materialized",
        "unit04_baseline_integrated",
        "a2_a2plus_unlocked",
    )
    if contract.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise Reader360BatchAcceptanceError(f"{label}_author_role_drift")
    if any(contract.get(key) is not False for key in required_false):
        raise Reader360BatchAcceptanceError(f"{label}_scope_contract_drift")

def build_acceptance_report(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    spoken = _load(root / SPOKEN_PATH)
    pattern = _load(root / PATTERN_PATH)
    _check_contract(spoken, "spoken")
    _check_contract(pattern, "pattern")

    current = neb02.build_unit04_neb02_natural_episode_bank_360(root)
    if current.get("status") != neb02.STATUS:
        raise Reader360BatchAcceptanceError("current360_source_status_drift")
    sources = {str(row["episode_id"]): row for row in current["effective_episodes"]}
    if len(sources) != 360:
        raise Reader360BatchAcceptanceError("current360_source_count_drift")

    s_entries = list(spoken.get("entries", []))
    p_entries = list(pattern.get("entries", []))
    s_ids = tuple(str(row.get("source_episode_id", "")) for row in s_entries)
    p_ids = tuple(str(row.get("source_episode_id", "")) for row in p_entries)
    if s_ids != EXPECTED_IDS or p_ids != EXPECTED_IDS or s_ids != p_ids:
        raise Reader360BatchAcceptanceError("reader_episode_alignment_drift")
    if len(s_entries) != 27 or len(p_entries) != 27:
        raise Reader360BatchAcceptanceError("reader_entry_count_drift")

    for srow, prow in zip(s_entries, p_entries, strict=True):
        episode_id = str(srow["source_episode_id"])
        source = sources[episode_id]
        for row, label in ((srow, "spoken"), (prow, "pattern")):
            if row["micro_scene_id"] != source["micro_scene_id"]:
                raise Reader360BatchAcceptanceError(f"{label}_scene_drift:{episode_id}")
            if row["life_domain"] != source["life_domain"]:
                raise Reader360BatchAcceptanceError(f"{label}_domain_drift:{episode_id}")
            if row["source_fact_lineage"] != source["source_fact_lineage"]:
                raise Reader360BatchAcceptanceError(f"{label}_fact_lineage_drift:{episode_id}")
            if row["target_relations"] != _rels(source["target_relations"]):
                raise Reader360BatchAcceptanceError(f"{label}_relation_drift:{episode_id}")

        turns = srow.get("dialogue_turns", [])
        if len(turns) < 5:
            raise Reader360BatchAcceptanceError(f"spoken_turn_count_low:{episode_id}")
        for idx, turn in enumerate(turns, 1):
            if not str(turn.get("speaker", "")).strip():
                raise Reader360BatchAcceptanceError(f"spoken_speaker_missing:{episode_id}:{idx}")
            _check_text(str(turn.get("text", "")), f"{episode_id}:spoken:{idx}")

        families = prow.get("families", {})
        if tuple(families.keys()) != EXPECTED_FAMILIES:
            raise Reader360BatchAcceptanceError(f"pattern_family_drift:{episode_id}")
        for family in EXPECTED_FAMILIES:
            models = families[family]
            if not isinstance(models, list) or not models:
                raise Reader360BatchAcceptanceError(f"pattern_family_empty:{episode_id}:{family}")
            for idx, text in enumerate(models, 1):
                _check_text(str(text), f"{episode_id}:pattern:{family}:{idx}")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "source_current360_episode_count": 360,
        "batch_start": EXPECTED_IDS[0],
        "batch_end": EXPECTED_IDS[-1],
        "batch_episode_count": 27,
        "spoken_entry_count": 27,
        "pattern_entry_count": 27,
        "pattern_families_per_entry": 7,
        "source_lineage_alignment_count": 27,
        "cross_reader_episode_alignment_count": 27,
        "approved_e001_e003_rewritten": False,
        "a1_boundary_blocked_surface_count": 0,
        "scope_safety": {
            "pdf_materialized": False,
            "unit04_baseline_integrated": False,
            "current360_mutated": False,
            "unit05_plus_opened": False,
            "a2_a2plus_unlocked": False,
        },
    }

def main() -> int:
    print(json.dumps(build_acceptance_report(), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
