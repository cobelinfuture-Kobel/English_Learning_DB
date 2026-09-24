from __future__ import annotations

import json
import re
from pathlib import Path

from product.a1fs_v1_2_1 import (
    u05far7_core480_gpt56_materialization as core,
    u05far7_dictation480_gpt56_materialization as dictation,
    u05far7_ket_media336_gpt56_materialization as ket_media,
    u05far7_ket_text336_gpt56_materialization as ket_text,
    u05fullfix_full1632_zero_leak_and_reader_parity as fullfix,
)

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "product"
    / "a1fs_v1_2_1"
    / "release_evidence"
    / "u05final_unit05_closeout.safe.json"
)
PRACTICE_PDF = ROOT / "product/a1fs_v1_2_1/pdf/unit05/unit05_executable_practice_816.pdf"
ANSWER_PDF = ROOT / "product/a1fs_v1_2_1/pdf/unit05/unit05_answer_key_816.pdf"


def _load() -> dict:
    value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _page_count(raw: bytes) -> int:
    return len(re.findall(rb"/Type /Page\\b", raw))


def test_u05final_closeout_evidence_is_explicit_and_fail_closed() -> None:
    value = _load()
    assert value["task_id"] == (
        "A1FS-V1-U05FINAL_CanonicalJSONToPDFMaterialization_"
        "SingleAcceptance_SinglePRCI_Unit05Closeout"
    )
    assert value["validation_status"] == (
        "PASS_A1FS_V1_U05FINAL_UNIT05_TEXT_FIRST_CLOSEOUT_MEDIA_DEFERRED"
    )
    assert value["source_main_sha"] == "93729ee5299e470e13fdbc769cc2122b99ecb4ef"

    closeout = value["closeout_assertions"]
    for key in (
        "unit05_closeout_complete",
        "core480_closed",
        "guided_context_leakage_closed",
        "ket_text336_closed",
        "full1632_authoring_closed",
        "final_pdf816_closed",
        "reader360_preserved",
        "deferred_media_contract_preserved",
        "unit06_planning_allowed",
    ):
        assert closeout[key] is True

    for key in (
        "media_release_complete",
        "a2_a2plus_unlocked",
        "unit06_implementation_allowed",
    ):
        assert closeout[key] is False

    assert value["next_short_step"] == (
        "A1FS-V1-U06Q00_Unit05SuccessorBaselinePreflight"
    )
    assert value["next_short_step_scope"] == "UNIT06_PLANNING_ONLY"


def test_u05final_closeout_revalidates_current_far7_authorities() -> None:
    value = _load()

    core_report = core.build_report()
    assert core_report["core_authored_count"] == 480
    assert core_report["unique_target_sentence_count"] == 480
    assert core_report["unique_activity_signature_count"] == 480
    assert core_report["guided_context_answer_leakage_count"] == 0
    assert core_report["guided_current360_context_count"] == 97
    assert core_report["guided_controlled_context_count"] == 23

    ket_text_report = ket_text.build_report()
    assert ket_text_report["ket_text_authored_count"] == 336
    assert ket_text_report["ket_media_pending_count"] == 336

    ket_media_report = ket_media.build_report()
    assert ket_media_report["ket_authored_count"] == 672
    assert ket_media_report["text_executable_count"] == 336
    assert ket_media_report["media_asset_pending_count"] == 336
    assert ket_media_report["actual_media_assets_generated"] == 0

    dictation_report = dictation.build_report()
    assert dictation_report["dictation_authored_count"] == 480
    assert dictation_report["d1_count"] == 360
    assert dictation_report["d2_count"] == 120
    assert dictation_report["executable_count"] == 0
    assert dictation_report["asset_pending_count"] == 480

    fullfix_report = fullfix.build_report()
    assert fullfix_report["reader_counts"] == {
        "current360": 360,
        "spoken360": 360,
        "pattern360": 360,
    }
    assert fullfix_report["full1632_count"] == 1632
    assert fullfix_report["unique_practice_id_count"] == 1632
    assert fullfix_report["unique_source_slot_id_count"] == 1632
    assert fullfix_report["zero_leak_violation_count"] == 0

    authored = value["far7_authoring_acceptance"]
    assert authored["executable_text_activity_count"] == 816
    assert authored["external_asset_pending_activity_count"] == 816


def test_u05final_closeout_committed_pdf_delivery_is_still_current() -> None:
    value = _load()
    pdf = value["final_pdf_acceptance"]
    for path in (PRACTICE_PDF, ANSWER_PDF):
        assert path.is_file()
        raw = path.read_bytes()
        assert raw.startswith(b"%PDF-1.")
        assert raw.rstrip().endswith(b"%%EOF")
        assert len(raw) > 100_000

    assert pdf["learner_visible_activity_count"] == 816
    assert pdf["answer_key_activity_count"] == 816

    sample = pdf["visual_sample_acceptance"]
    assert sample["status"] == "PASS"
    assert sample["sample_question_ids"] == ["Q001", "Q002", "Q004"]
    assert sample["clipping_or_overlap_observed"] is False
    assert sample["guided_answer_leakage_observed"] is False


def test_u05final_closeout_does_not_fake_media_completion() -> None:
    value = _load()
    boundary = value["deferred_media_boundary"]
    assert boundary == {
        "audio_assets_generated": False,
        "visual_assets_generated": False,
        "ket_media336_execution_complete": False,
        "dictation480_execution_complete": False,
        "deferred_media_blocks_text_first_unit05_closeout": False,
        "deferred_media_must_remain_visible": True,
    }
