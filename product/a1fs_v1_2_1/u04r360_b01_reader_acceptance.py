from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb02

TASK_ID = "A1FS-V1-U04R360-B02_Reader360E031E060CumulativeAcceptance"
STATUS = "PASS_A1FS_V1_U04R360_B02_E031_E060_CUMULATIVE_E004_E060"
SPOKEN_PATH = "product/a1fs_v1_2_1/u04reader360_spoken_dialogue_reader_partial.json"
PATTERN_PATH = "product/a1fs_v1_2_1/u04reader360_pattern_sentence_family_reader_partial.json"
EXPECTED_IDS = tuple(f"U04-NEB-E{i:03d}" for i in range(4, 61))
LATEST_BATCH_IDS = tuple(f"U04-NEB-E{i:03d}" for i in range(31, 61))
EXPECTED_FAMILIES = tuple("ABCDEFG")
BLOCKED_LEARNER_SURFACES = (
    r"\bwhile\b", r"\balmost\b", r"\balready\b", r"\bmust\b",
    r"\bshould\b", r"\bwill\b", r"\bnearly\b", r"\buntil\b",
    r"\bacross\b", r"\binto\b", r"\bremembers where\b", r"\blooks?\s+around\b",
)
PERSONAL_OR_POSSESSIVE = re.compile(
    r"(?:\bi\b|\byou\b|\bhe\b|\bshe\b|\bit\b|\bwe\b|\bthey\b|"
    r"\bmy\b|\byour\b|\bhis\b|\bher\b|\bour\b|\btheir\b|\bits\b|['’]s\b)",
    flags=re.I,
)
ACTION_SURFACE = re.compile(
    r"\b(?:put|puts|reach|reaches|look|looks|wait|waits|leave|leaves|keep|keeps|"
    r"check|checks|point|points|move|moves|walk|walks|stand|stands|ask|asks|"
    r"read|reads|find|finds|see|sees|get|gets|take|takes|sit|sits|stay|stays|"
    r"lift|lifts|open|opens|show|shows|play|plays|pick|picks|remember|remembers)\b",
    flags=re.I,
)

class Reader360BatchAcceptanceError(ValueError):
    pass

def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]

def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Reader360BatchAcceptanceError(f"missing_reader_json:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Reader360BatchAcceptanceError(f"reader_json_object_required:{path}")
    return value

def _rels(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(",") if part.strip()]

def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

def _check_text(text: str, ref: str) -> None:
    value = text.strip()
    if not value:
        raise Reader360BatchAcceptanceError(f"empty_learner_text:{ref}")
    if "___" in value or "[...]" in value or "{blank}" in value.casefold():
        raise Reader360BatchAcceptanceError(f"worksheet_blank_leaked:{ref}")
    for pattern in BLOCKED_LEARNER_SURFACES:
        if re.search(pattern, value, flags=re.I):
            raise Reader360BatchAcceptanceError(f"a1_boundary_surface:{ref}:{pattern}:{value}")

def _relations_in_text(text: str) -> set[str]:
    found: set[str] = set()
    for relation in neb02.TARGET_RELATIONS:
        if relation == "in":
            pattern = r"(?<!\w)in(?!\w)(?!\s+front\s+of)"
        else:
            pattern = rf"(?<!\w){re.escape(relation)}(?!\w)"
        if re.search(pattern, text, flags=re.I):
            found.add(relation)
    return found

def _location_surfaces(text: str) -> set[str]:
    found = set(_relations_in_text(text))
    for support in ("next to", "in front of"):
        if re.search(rf"(?<!\w){re.escape(support)}(?!\w)", text, flags=re.I):
            found.add(support)
    return found

def _check_contract(payload: dict[str, Any], label: str) -> None:
    if payload.get("approved_sample_e001_e003", {}) != {
        "status": "APPROVED_PREEXISTING_NOT_REWRITTEN_IN_THIS_BATCH",
        "included_in_this_file": False,
    }:
        raise Reader360BatchAcceptanceError(f"{label}_approved_sample_contract_drift")
    contract = payload.get("authoring_contract", {})
    required_false = (
        "python_may_compose_learner_facing_english", "reader_is_question_worksheet",
        "pdf_materialized", "unit04_baseline_integrated", "a2_a2plus_unlocked",
    )
    if contract.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise Reader360BatchAcceptanceError(f"{label}_author_role_drift")
    if any(contract.get(key) is not False for key in required_false):
        raise Reader360BatchAcceptanceError(f"{label}_scope_contract_drift")
    if contract.get("current360_passage_preserved") is not True:
        raise Reader360BatchAcceptanceError(f"{label}_passage_preservation_contract_missing")

def _check_pattern_family(episode_id: str, family: str, models: list[Any]) -> None:
    if not isinstance(models, list) or not models:
        raise Reader360BatchAcceptanceError(f"pattern_family_empty:{episode_id}:{family}")
    texts = [str(value) for value in models]
    for idx, value in enumerate(texts, 1):
        _check_text(value, f"{episode_id}:pattern:{family}:{idx}")
    joined = " ".join(texts)
    relations = _location_surfaces(joined)
    if family == "A":
        if not relations or "?" in joined:
            raise Reader360BatchAcceptanceError(f"pattern_A_scene_description_drift:{episode_id}")
    elif family == "B":
        if not relations or not PERSONAL_OR_POSSESSIVE.search(joined):
            raise Reader360BatchAcceptanceError(f"pattern_B_personal_possessive_drift:{episode_id}")
    elif family == "C":
        if "?" not in joined or not re.search(r"\bwhere\b", joined, flags=re.I) or not relations:
            raise Reader360BatchAcceptanceError(f"pattern_C_where_qa_drift:{episode_id}")
    elif family == "D":
        if "?" not in joined or not re.search(r"\b(?:yes|no)\b", joined, flags=re.I) or not relations:
            raise Reader360BatchAcceptanceError(f"pattern_D_confirmation_qa_drift:{episode_id}")
    elif family == "E":
        if not re.search(r"\b(?:i think|maybe|perhaps)\b", joined, flags=re.I) or not relations:
            raise Reader360BatchAcceptanceError(f"pattern_E_thought_location_drift:{episode_id}")
    elif family == "F":
        if not relations or not ACTION_SURFACE.search(joined):
            raise Reader360BatchAcceptanceError(f"pattern_F_action_location_drift:{episode_id}")
    elif family == "G":
        if not relations or not re.search(r"\b(?:and|but|or)\b", joined, flags=re.I):
            raise Reader360BatchAcceptanceError(f"pattern_G_contrast_comparison_drift:{episode_id}")

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
    if len(s_entries) != len(EXPECTED_IDS) or len(p_entries) != len(EXPECTED_IDS):
        raise Reader360BatchAcceptanceError("reader_entry_count_drift")
    if tuple(s_ids[-len(LATEST_BATCH_IDS):]) != LATEST_BATCH_IDS:
        raise Reader360BatchAcceptanceError("latest_batch_identity_drift")

    passage_alignment_count = 0
    pattern_family_semantic_count = 0
    spoken_relation_alignment_count = 0
    spoken_dialogue_norms: set[str] = set()
    pattern_bundle_norms: set[str] = set()

    for srow, prow in zip(s_entries, p_entries, strict=True):
        episode_id = str(srow["source_episode_id"])
        source = sources[episode_id]
        declared_relations = set(_rels(source["target_relations"]))
        for row, label in ((srow, "spoken"), (prow, "pattern")):
            if row["micro_scene_id"] != source["micro_scene_id"]:
                raise Reader360BatchAcceptanceError(f"{label}_scene_drift:{episode_id}")
            if row["life_domain"] != source["life_domain"]:
                raise Reader360BatchAcceptanceError(f"{label}_domain_drift:{episode_id}")
            if row["source_fact_lineage"] != source["source_fact_lineage"]:
                raise Reader360BatchAcceptanceError(f"{label}_fact_lineage_drift:{episode_id}")
            if row["target_relations"] != _rels(source["target_relations"]):
                raise Reader360BatchAcceptanceError(f"{label}_relation_drift:{episode_id}")
            if row.get("passage") != source["passage"]:
                raise Reader360BatchAcceptanceError(f"{label}_passage_drift:{episode_id}")
            passage_alignment_count += 1

        turns = srow.get("dialogue_turns", [])
        if len(turns) < 5:
            raise Reader360BatchAcceptanceError(f"spoken_turn_count_low:{episode_id}")
        spoken_texts: list[str] = []
        for idx, turn in enumerate(turns, 1):
            if not str(turn.get("speaker", "")).strip():
                raise Reader360BatchAcceptanceError(f"spoken_speaker_missing:{episode_id}:{idx}")
            text = str(turn.get("text", ""))
            _check_text(text, f"{episode_id}:spoken:{idx}")
            spoken_texts.append(text)
        factual_spoken_text = " ".join(text for text in spoken_texts if "?" not in text)
        spoken_relations = _relations_in_text(factual_spoken_text)
        undeclared = sorted(spoken_relations - declared_relations)
        if undeclared:
            raise Reader360BatchAcceptanceError(f"spoken_undeclared_target_relation:{episode_id}:{undeclared}")
        if not spoken_relations:
            raise Reader360BatchAcceptanceError(f"spoken_no_unit04_relation:{episode_id}")
        spoken_relation_alignment_count += 1
        spoken_norm = _norm(" ".join(spoken_texts))
        if spoken_norm in spoken_dialogue_norms:
            raise Reader360BatchAcceptanceError(f"spoken_dialogue_duplicate:{episode_id}")
        spoken_dialogue_norms.add(spoken_norm)

        families = prow.get("families", {})
        if tuple(families.keys()) != EXPECTED_FAMILIES:
            raise Reader360BatchAcceptanceError(f"pattern_family_drift:{episode_id}")
        family_texts: list[str] = []
        for family in EXPECTED_FAMILIES:
            _check_pattern_family(episode_id, family, families[family])
            family_texts.extend(str(value) for value in families[family])
            pattern_family_semantic_count += 1
        pattern_norm = _norm(" ".join(family_texts))
        if pattern_norm in pattern_bundle_norms:
            raise Reader360BatchAcceptanceError(f"pattern_bundle_duplicate:{episode_id}")
        pattern_bundle_norms.add(pattern_norm)

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "source_current360_episode_count": 360,
        "materialized_start": EXPECTED_IDS[0],
        "materialized_end": EXPECTED_IDS[-1],
        "materialized_episode_count": len(EXPECTED_IDS),
        "latest_batch_start": LATEST_BATCH_IDS[0],
        "latest_batch_end": LATEST_BATCH_IDS[-1],
        "latest_batch_episode_count": len(LATEST_BATCH_IDS),
        "spoken_entry_count": len(s_entries),
        "pattern_entry_count": len(p_entries),
        "pattern_families_per_entry": 7,
        "source_lineage_alignment_count": len(EXPECTED_IDS),
        "cross_reader_episode_alignment_count": len(EXPECTED_IDS),
        "current360_passage_alignment_count": passage_alignment_count,
        "spoken_relation_alignment_count": spoken_relation_alignment_count,
        "pattern_family_semantic_count": pattern_family_semantic_count,
        "spoken_dialogue_duplicate_count": 0,
        "pattern_bundle_duplicate_count": 0,
        "approved_e001_e003_rewritten": False,
        "a1_boundary_blocked_surface_count": 0,
        "scope_safety": {
            "pdf_materialized": False, "unit04_baseline_integrated": False,
            "current360_mutated": False, "unit05_plus_opened": False,
            "a2_a2plus_unlocked": False,
        },
    }

def main() -> int:
    print(json.dumps(build_acceptance_report(), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
