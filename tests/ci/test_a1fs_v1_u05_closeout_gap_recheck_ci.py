from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "product/a1fs_v1_2_1/release_evidence/u05closeout_gap_recheck.safe.json"
Q04 = ROOT / "ulga/reports/a1fs_v1_u05_q04_scene_functional_chunk_usage.json"
Q05 = ROOT / "ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json"
Q06 = ROOT / "ulga/contracts/a1fs_v1_u05_q06_sentence_assets.json"
CURRENT = ROOT / "product/a1fs_v1_2_1/data/unit05_current360_360.json"
SPOKEN = ROOT / "product/a1fs_v1_2_1/data/unit05_spoken360_360.json"
PATTERN = ROOT / "product/a1fs_v1_2_1/data/unit05_pattern360_360.json"


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _pdf_page_count(raw: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b", raw))


def test_q04_functional_candidate_actual_usage_reconciliation_is_zero_and_explicit() -> None:
    q04 = _json(Q04)
    q05 = _json(Q05)
    q06 = _json(Q06)
    ev = _json(EVIDENCE)["q04_functional_chunk_reconciliation"]

    assert q04["summary"]["unique_functional_candidate_count"] == 874
    assert q04["summary"]["extracted_occurrence_count"] == 2246
    assert q04["downstream_usage_recording_contract"]["required"] is True
    assert q04["downstream_usage_recording_contract"]["actual_q05_q06_usage_not_yet_materialized"] is True

    proj = q05["scene_functional_evidence_projection"]
    assert proj["individual_functional_candidate_promoted_to_q05_frame_authority_count"] == 0
    assert proj["q05_actual_functional_candidate_usage_record_count"] == 0

    gen = q06["generation_authority"]
    assert gen["scene_functional_candidate_promoted_count"] == 0
    assert gen["functional_candidate_usage_ledger_entry_count"] == 0

    assert ev["q05_individual_candidate_promoted_count"] == 0
    assert ev["q05_actual_usage_record_count"] == 0
    assert ev["q06_scene_functional_candidate_promoted_count"] == 0
    assert ev["q06_functional_candidate_usage_ledger_entry_count"] == 0
    assert ev["reconciliation_result"] == "ZERO_Q05_Q06_DOWNSTREAM_CONSUMPTION_PROVEN"

    for path in (CURRENT, SPOKEN, PATTERN):
        assert "U05-FC-" not in path.read_text(encoding="utf-8")


def test_reader360_sources_remain_exact_and_complete() -> None:
    current = _json(CURRENT)
    spoken = _json(SPOKEN)
    pattern = _json(PATTERN)
    assert current["episode_count"] == 360
    assert len(current["episodes"]) == 360
    assert spoken["entry_count"] == 360
    assert len(spoken["entries"]) == 360
    assert pattern["entry_count"] == 360
    assert len(pattern["entries"]) == 360
    assert pattern["family_group_count"] == 2520
    assert pattern["example_count"] == 4675


def test_reader360_three_pdf_formal_handoff_is_exact_60_pages_each() -> None:
    ev = _json(EVIDENCE)["reader360_pdf_handoff"]
    assert ev["layout"] == "A4_PORTRAIT_2_COLUMNS_X_3_ROWS_6_CARDS_PER_PAGE"
    for key in ("current360", "spoken360", "pattern360"):
        row = ev[key]
        path = ROOT / row["pdf_path"]
        raw = path.read_bytes()
        assert raw.startswith(b"%PDF-1.4")
        assert raw.rstrip().endswith(b"%%EOF")
        assert len(raw) == row["pdf_size_bytes"]
        assert _git_blob_sha(raw) == row["pdf_blob_sha"]
        assert _pdf_page_count(raw) == 60
        assert row["page_count"] == 60
        assert row["cards_per_page"] == 6
        assert b"E001" in raw
        assert b"E360" in raw

    assert ev["current360"]["source_json_blob_sha"] == "2d96bbd71f454cf963a037f7817f7dfff087a4a1"
    assert ev["spoken360"]["source_json_blob_sha"] == "8722efd96358742f2d76041312876bfaa31dbaa0"
    assert ev["pattern360"]["source_json_blob_sha"] == "28cbd4df1a5fa0d9dbcc0d34c6437339078561c1"
    assert ev["pattern360"]["example_count"] == 4675
    assert ev["learner_facing_source_text_rewritten"] is False
    assert ev["python_or_code_authored_new_learner_english"] is False


def test_closeout_gap_recheck_preserves_deferred_media_boundary() -> None:
    value = _json(EVIDENCE)
    assert value["scope"]["media_pending_816_touched"] is False
    assert value["scope"]["a2_a2plus_unlocked"] is False
    assert value["deferred_media_boundary"] == {
        "executable_text_activity_count": 816,
        "external_asset_pending_activity_count": 816,
        "media_assets_generated": False,
        "media_execution_changed": False,
    }
