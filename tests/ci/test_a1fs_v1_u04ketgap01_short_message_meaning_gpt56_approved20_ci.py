from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "product/a1fs_v1_2_1/u04ketgap01_short_message_meaning_gpt56_approved20.json"
BASE108 = ROOT / "product/a1fs_v1_2_1/u04neb01_natural_episode_authority_108.tsv"


def _load() -> dict:
    return json.loads(ASSET.read_text(encoding="utf-8"))


def _visible_texts(payload: dict) -> list[str]:
    rows: list[str] = []
    for item in payload["items"]:
        rows.extend([item["message"], item["question"], *item["options"]])
    return rows


def test_u04ketgap01_contract_and_operator_approval_are_exact() -> None:
    payload = _load()
    assert payload["schema"] == "a1fs.v1.u04.ket_gap.short_message_meaning.approved20.v1"
    assert payload["status"] == "HUMAN_PDF_APPROVED_PENDING_RUNTIME_BINDING"
    assert payload["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    assert payload["source_authorities"] == {
        "ket_s3_profile": "KET_S2_TASK_001",
        "ket_task_family": "SHORT_MESSAGE_MEANING",
        "response_mode": "SELECT",
        "stimulus_modality": "TEXT",
        "assessment_capability": "INFER_COMMUNICATIVE_PURPOSE",
        "response_format": "SINGLE_CHOICE",
        "current360_authority": "A1FS-V1-U04NEB02_NaturalEpisodeBank360",
    }
    assert payload["operator_acceptance"]["operator_status"] == "APPROVED"
    assert (
        payload["operator_acceptance"]["review_artifact_candidate_sha256"]
        == "74336940910fb5e8ccfdbd1e7229adda3453e80db4e1b18695c5dfbd812cdd32"
    )
    assert payload["operator_acceptance"]["runtime_binding_approved"] is True


def test_u04ketgap01_preserves_s8_s9_origin_and_model_authorship_boundaries() -> None:
    payload = _load()
    provenance = payload["generation_provenance"]
    assert provenance == {
        "task_origin": "A1FS_DERIVED",
        "generation_model": "GPT-5.6",
        "generation_method": "MODEL_AUTHORED",
        "source_task_copied": False,
        "source_wording_copied": False,
        "authority_validation": "REQUIRED",
        "live_model_call_in_ci": False,
    }


def test_u04ketgap01_has_exactly_one_approved_d05_q31_item_per_form() -> None:
    payload = _load()
    policy = payload["runtime_binding_policy"]
    assert policy["form_count"] == 20
    assert policy["slot_per_form"] == "D05"
    assert policy["learner_question_number"] == "Q31"
    assert policy["replace_task_variant"] == "READING_SIMPLE_GIST_SEED"
    assert policy["new_task_variant"] == "SHORT_MESSAGE_MEANING"
    assert policy["forms_remain_20_x_40"] is True
    assert policy["parallel_runtime_allowed"] is False
    assert policy["stage_exposure_must_be_preserved"] is True
    assert policy["context_binding"] == "SAME_MICRO_SCENE_STAGE_RESERVOIR"
    assert policy["shared_d_e_context_must_be_preserved"] is True
    assert policy["existing_location_extraction_tasks_unchanged"] is True

    items = payload["items"]
    assert len(items) == 20
    assert [row["form_number"] for row in items] == list(range(1, 21))
    assert len({row["authoring_source_episode_id"] for row in items}) == 20
    assert len({row["micro_scene_id"] for row in items}) == 20
    assert Counter(row["progression_stage"] for row in items) == {
        "GUIDED": 4,
        "REDUCED_SUPPORT": 4,
        "INDEPENDENT": 4,
        "TRANSFER": 4,
        "RETENTION": 4,
    }


def test_u04ketgap01_hard_blocks_relative_clauses_at_this_unit04_level() -> None:
    payload = _load()
    ceiling = payload["language_ceiling"]
    assert ceiling["relative_clauses_allowed"] is False
    assert ceiling["zero_relative_clauses_allowed"] is False

    visible = _visible_texts(payload)
    relativizer = re.compile(r"\b(who|whom|whose|which|that)\b", flags=re.I)
    assert not [text for text in visible if relativizer.search(text)]
    assert not [text for text in visible if "the dictionary you need" in text.casefold()]
    assert not [text for text in visible if re.search(r"\bwhere to\s+\w+", text, flags=re.I)]


def test_u04ketgap01_every_item_is_single_choice_with_one_private_key() -> None:
    payload = _load()
    for item in payload["items"]:
        assert item["message"].strip()
        assert item["question"].strip()
        assert len(item["options"]) == 3
        assert len(set(item["options"])) == 3
        assert item["correct_option_index"] in {0, 1, 2}
        assert item["options"][item["correct_option_index"]].strip()


def test_u04ketgap01_authoring_sources_exist_in_current360_base_authority() -> None:
    payload = _load()
    with BASE108.open("r", encoding="utf-8", newline="") as handle:
        rows = {row["episode_id"]: row for row in csv.DictReader(handle, delimiter="\t")}

    for item in payload["items"]:
        source = rows[item["authoring_source_episode_id"]]
        assert source["micro_scene_id"] == item["micro_scene_id"]
        assert source["review_status"].startswith("PASS_GPT5_6_SOL")
        assert source["source_fact_lineage"].strip()
        assert source["passage"].strip()
