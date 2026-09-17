from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb02

TASK_ID = "A1FS-V1-U04SP03_Current360SpokenAndProductionPackAcceptance"
STATUS = "PASS_A1FS_V1_U04SP03_CURRENT360_SPOKEN_PRODUCTION_PACKS_36_PATTERN_A_G"
REVISION = "CURRENT360_36_MICRO_SCENE_SPOKEN_PRODUCTION_ACCEPTANCE_V1"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates fixed GPT-5.6-authored learner-facing Spoken/Production Pack assets against "
    "Current360. Python validates identity, lineage, coverage, and progression only; it "
    "does not compose, repair, or paraphrase learner-facing English."
)

SPOKEN_ASSET = "product/a1fs_v1_2_1/u04sp03_current360_spoken_packs_36.json"
PRODUCTION_ASSET = "product/a1fs_v1_2_1/u04pp01_current360_production_packs_pattern_a_g_36.json"
EXPECTED_SCENES = tuple(f"U04-NEB-MS{n:02d}" for n in range(1, 37))
EXPECTED_PATTERNS = tuple("ABCDEFG")
EXPECTED_PATTERN_NAMES = {
    "A": "BASIC_DESCRIPTION",
    "B": "POSSESSIVE_DESCRIPTION",
    "C": "WHERE_QA",
    "D": "CONFIRMATION_QA",
    "E": "UNCERTAINTY",
    "F": "ACTION_PLUS_LOCATION",
    "G": "CHOICE_COMPARISON",
}
EXPECTED_STAGES = ("GUIDED_DIALOGUE", "FOLLOW_UP_PROMPT", "ERROR_REPAIR", "TRANSFER_PROMPT")
EXPECTED_MODES = ("LOCATION_QA", "DIALOGUE_FOLLOW_UP", "REPAIR_CLARIFY", "TRANSFER_CHANGED_LOCATION")


class Unit04SP03Error(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Unit04SP03Error(f"required_asset_missing:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Unit04SP03Error(f"json_object_required:{path}")
    return value


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise Unit04SP03Error(f"nonempty_text_required:{label}")
    return text


def _contains(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _authoring(asset: dict[str, Any], kind: str, count_key: str) -> None:
    contract = asset.get("authoring_contract")
    if not isinstance(contract, dict):
        raise Unit04SP03Error(f"{kind}_authoring_contract_missing")
    expected = {
        "learner_facing_language_author": "GPT-5.6 Sol",
        "python_may_compose_learner_facing_english": False,
        "current360_narrative_mutated": False,
        "current360_episode_count": 360,
        "current360_micro_scene_count": 36,
        count_key: 36,
        "a2_a2plus_unlocked": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise Unit04SP03Error(f"{kind}_authoring_contract_drift:{key}:{contract.get(key)}")


def _current360() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    report = neb02.build_unit04_neb02_natural_episode_bank_360()
    if report.get("status") != neb02.STATUS:
        raise Unit04SP03Error("current360_not_pass")
    rows = report.get("effective_episodes")
    if not isinstance(rows, list) or len(rows) != 360:
        raise Unit04SP03Error("current360_episode_supply_invalid")
    by_id = {str(row.get("episode_id") or ""): dict(row) for row in rows if isinstance(row, dict)}
    if len(by_id) != 360:
        raise Unit04SP03Error("current360_episode_identity_invalid")
    if report.get("summary", {}).get("micro_scene_count") != 36:
        raise Unit04SP03Error("current360_micro_scene_count_drift")
    return by_id, report


def _binding(row: dict[str, Any], by_id: dict[str, dict[str, Any]], scene: str, label: str) -> tuple[str, str]:
    if row.get("micro_scene_id") != scene:
        raise Unit04SP03Error(f"{label}_scene_order_drift:{row.get('micro_scene_id')}:{scene}")
    episode_id = _text(row.get("source_episode_id"), f"{label}.source_episode_id")
    source = by_id.get(episode_id)
    if source is None or str(source.get("micro_scene_id") or "") != scene:
        raise Unit04SP03Error(f"{label}_source_episode_scene_mismatch:{episode_id}")
    if str(source.get("life_domain") or "") != str(row.get("life_domain") or ""):
        raise Unit04SP03Error(f"{label}_life_domain_mismatch:{episode_id}")
    focus = _text(row.get("focus_relation"), f"{label}.focus_relation")
    if focus not in neb02.TARGET_RELATIONS:
        raise Unit04SP03Error(f"{label}_focus_not_unit04_target:{focus}")
    declared = {part.strip() for part in str(source.get("target_relations") or "").split(",") if part.strip()}
    if focus not in declared:
        raise Unit04SP03Error(f"{label}_focus_not_declared_by_source:{episode_id}:{focus}")
    _text(row.get("source_fact_anchor"), f"{label}.source_fact_anchor")
    return episode_id, focus


def _spoken(asset: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, int]:
    if asset.get("schema_version") != "a1fs.v1.u04.current360.spoken_packs.v1":
        raise Unit04SP03Error("spoken_schema_drift")
    if asset.get("status") != "GPT5_6_SOL_STATIC_LEARNER_FACING_ASSET":
        raise Unit04SP03Error("spoken_status_drift")
    _authoring(asset, "spoken", "spoken_pack_count")
    progression = asset.get("progression")
    if not isinstance(progression, dict):
        raise Unit04SP03Error("spoken_progression_missing")
    if tuple(progression.get("stages") or ()) != EXPECTED_STAGES:
        raise Unit04SP03Error("spoken_stage_drift")
    if tuple(progression.get("modes") or ()) != EXPECTED_MODES:
        raise Unit04SP03Error("spoken_mode_drift")
    if progression.get("scoring_mode") != "HUMAN_OR_SEMANTIC_REVIEW":
        raise Unit04SP03Error("spoken_scoring_mode_drift")
    rows = asset.get("spoken_packs")
    if not isinstance(rows, list) or len(rows) != 36:
        raise Unit04SP03Error("spoken_pack_count_drift")
    source_ids, pack_ids = set(), set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise Unit04SP03Error(f"spoken_pack_not_object:{i}")
        episode_id, focus = _binding(row, by_id, EXPECTED_SCENES[i], f"spoken[{i}]")
        if episode_id in source_ids:
            raise Unit04SP03Error(f"spoken_source_duplicate:{episode_id}")
        source_ids.add(episode_id)
        pack_id = _text(row.get("pack_id"), f"spoken[{i}].pack_id")
        if pack_id in pack_ids:
            raise Unit04SP03Error(f"spoken_pack_id_duplicate:{pack_id}")
        pack_ids.add(pack_id)
        dialogue = row.get("dialogue")
        if not isinstance(dialogue, list) or len(dialogue) != 4:
            raise Unit04SP03Error(f"spoken_dialogue_turn_count_drift:{EXPECTED_SCENES[i]}")
        dialogue_text = " ".join(_text(value, f"spoken[{i}].dialogue") for value in dialogue)
        if not _contains(dialogue_text, focus):
            raise Unit04SP03Error(f"spoken_focus_not_practised:{EXPECTED_SCENES[i]}:{focus}")
        for key in ("follow_up", "repair", "transfer"):
            _text(row.get(key), f"spoken[{i}].{key}")
    return {
        "spoken_pack_count": len(rows),
        "spoken_micro_scene_count": len({row["micro_scene_id"] for row in rows}),
        "spoken_source_episode_count": len(source_ids),
        "spoken_dialogue_turn_count": sum(len(row["dialogue"]) for row in rows),
    }


def _production(asset: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, int]:
    if asset.get("schema_version") != "a1fs.v1.u04.current360.production_packs.v1":
        raise Unit04SP03Error("production_schema_drift")
    if asset.get("status") != "GPT5_6_SOL_STATIC_LEARNER_FACING_ASSET":
        raise Unit04SP03Error("production_status_drift")
    _authoring(asset, "production", "production_pack_count")
    if asset.get("authoring_contract", {}).get("patterns_per_pack") != 7:
        raise Unit04SP03Error("production_patterns_per_pack_drift")
    definitions = asset.get("pattern_definitions")
    if not isinstance(definitions, dict) or tuple(definitions) != EXPECTED_PATTERNS:
        raise Unit04SP03Error("production_pattern_definition_identity_drift")
    for pid, name in EXPECTED_PATTERN_NAMES.items():
        definition = definitions.get(pid)
        if not isinstance(definition, dict) or definition.get("name") != name:
            raise Unit04SP03Error(f"production_pattern_name_drift:{pid}")
        _text(definition.get("purpose"), f"pattern_definition.{pid}.purpose")
        _text(definition.get("model_shape"), f"pattern_definition.{pid}.model_shape")
    rows = asset.get("production_packs")
    if not isinstance(rows, list) or len(rows) != 36:
        raise Unit04SP03Error("production_pack_count_drift")
    source_ids, pack_ids, model_count = set(), set(), 0
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise Unit04SP03Error(f"production_pack_not_object:{i}")
        episode_id, focus = _binding(row, by_id, EXPECTED_SCENES[i], f"production[{i}]")
        if episode_id in source_ids:
            raise Unit04SP03Error(f"production_source_duplicate:{episode_id}")
        source_ids.add(episode_id)
        pack_id = _text(row.get("pack_id"), f"production[{i}].pack_id")
        if pack_id in pack_ids:
            raise Unit04SP03Error(f"production_pack_id_duplicate:{pack_id}")
        pack_ids.add(pack_id)
        models = row.get("models")
        if not isinstance(models, dict) or tuple(models) != EXPECTED_PATTERNS:
            raise Unit04SP03Error(f"production_pattern_set_drift:{EXPECTED_SCENES[i]}")
        for pid in EXPECTED_PATTERNS:
            model = _text(models.get(pid), f"production[{i}].{pid}")
            if not _contains(model, focus):
                raise Unit04SP03Error(f"production_focus_missing:{EXPECTED_SCENES[i]}:{pid}:{focus}")
            model_count += 1
    return {
        "production_pack_count": len(rows),
        "production_micro_scene_count": len({row["micro_scene_id"] for row in rows}),
        "production_source_episode_count": len(source_ids),
        "production_pattern_model_count": model_count,
        "patterns_per_pack": 7,
    }


def build_unit04_sp03_current360_spoken_production_pack_acceptance(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    by_id, current360 = _current360()
    spoken_asset = _load(root / SPOKEN_ASSET)
    production_asset = _load(root / PRODUCTION_ASSET)
    spoken_summary = _spoken(spoken_asset, by_id)
    production_summary = _production(production_asset, by_id)
    spoken_rows = spoken_asset["spoken_packs"]
    production_rows = production_asset["production_packs"]
    if [row["micro_scene_id"] for row in spoken_rows] != [row["micro_scene_id"] for row in production_rows]:
        raise Unit04SP03Error("surface_micro_scene_alignment_drift")
    if [row["source_episode_id"] for row in spoken_rows] != [row["source_episode_id"] for row in production_rows]:
        raise Unit04SP03Error("surface_source_episode_alignment_drift")
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "surface_contract": {
            "surface_1_current360_narrative_episode_count": 360,
            "surface_1_current360_narrative_modified": False,
            "surface_2_spoken_pack_count": 36,
            "surface_3_production_pack_count": 36,
            "production_patterns": list(EXPECTED_PATTERNS),
            "python_sentence_composer_used": False,
        },
        "spoken_summary": spoken_summary,
        "production_summary": production_summary,
        "current360_summary": {
            "episode_count": current360["summary"]["episode_count"],
            "micro_scene_count": current360["summary"]["micro_scene_count"],
            "episodes_per_micro_scene": current360["summary"]["episodes_per_micro_scene"],
        },
        "scope_safety": {
            "current360_narrative_modified": False,
            "q03_relation_authority_modified": False,
            "q07_semantic_authority_modified": False,
            "q10_form01_20_modified": False,
            "canonical_grammar_modified": False,
            "canonical_vocabulary_modified": False,
            "canonical_chunk_modified": False,
            "unit05_plus_opened": False,
            "a2_a2plus_unlocked": False,
        },
    }


def main() -> int:
    print(json.dumps(build_unit04_sp03_current360_spoken_production_pack_acceptance(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
