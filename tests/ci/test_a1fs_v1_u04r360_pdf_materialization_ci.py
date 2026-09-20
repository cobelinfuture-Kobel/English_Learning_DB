from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import u04r360_b01_reader_acceptance as reader
from product.a1fs_v1_2_1 import u04r360_pdf_materialization as pdfs


def _fake_browser_runner(
    chromium: Path,
    *,
    source_html: Path,
    output_path: Path,
    mode: str,
):
    assert chromium.is_file()
    assert source_html.is_file()
    assert mode == "PDF"
    marker = source_html.stem.encode("utf-8")
    payload = b"%PDF-1.4\n" + marker + b"\n" + (marker * 180) + b"\n%%EOF\n"
    output_path.write_bytes(payload)
    return {
        "returncode": 0,
        "mode": mode,
        "browser": str(chromium),
        "source_path": str(source_html),
        "output_path": str(output_path),
    }


def _fake_page_counter(path: Path) -> int:
    assert path.is_file()
    return 42


def _materialize(tmp_path: Path, acceptance_report=None):
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake")
    return pdfs.materialize_three_reader_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        acceptance_report=acceptance_report,
    )


def test_u04_reader360_three_pdf_materialization_preserves_accepted_sources(
    tmp_path: Path,
) -> None:
    manifest = _materialize(tmp_path)
    out = tmp_path / "out"

    assert manifest["validation_status"] == pdfs.PASS_STATUS
    assert manifest["source_final_acceptance_status"] == reader.STATUS
    assert manifest["source_counts"] == {
        "current360": 360,
        "spoken360": 360,
        "pattern360": 360,
        "pattern_family_semantic_checks": 2520,
        "cross_reader_passage_alignments": 720,
        "cross_reader_metadata_alignments": 720,
    }
    assert manifest["materialized_json_count"] == 3
    assert manifest["materialized_html_count"] == 3
    assert manifest["materialized_pdf_count"] == 3
    assert manifest["delivery_file_count"] == 6
    assert manifest["machine_acceptance_pass_count"] == 3
    assert manifest["human_visual_review_pending_count"] == 3
    assert manifest["human_pedagogical_review_pending_count"] == 3
    assert manifest["next_short_step"] == pdfs.NEXT_SHORT_STEP

    artifacts = manifest["artifacts"]
    assert [row["reader_id"] for row in artifacts] == [
        "current360",
        "spoken360",
        "pattern360",
    ]
    assert len({row["pdf_sha256"] for row in artifacts}) == 3
    assert len({row["json_sha256"] for row in artifacts}) == 3
    assert all(row["page_count"] == 42 for row in artifacts)
    assert all(row["machine_acceptance"] == "PASS" for row in artifacts)
    assert all(row["human_visual_review"] == "PENDING" for row in artifacts)
    assert all(row["human_pedagogical_review"] == "PENDING" for row in artifacts)

    current_html = (
        out / pdfs.OUTPUTS["current360"]["html"]
    ).read_text(encoding="utf-8")
    spoken_html = (
        out / pdfs.OUTPUTS["spoken360"]["html"]
    ).read_text(encoding="utf-8")
    pattern_html = (
        out / pdfs.OUTPUTS["pattern360"]["html"]
    ).read_text(encoding="utf-8")

    assert current_html.count('class="episode"') == 360
    assert spoken_html.count('class="episode"') == 360
    assert pattern_html.count('class="episode"') == 360
    assert spoken_html.count('class="turn"') >= 1800
    assert pattern_html.count('class="family"') == 2520
    assert '<div class="episode-id">E001</div>' in current_html
    assert '<div class="episode-id">E360</div>' in current_html
    assert '<div class="episode-id">E001</div>' in spoken_html
    assert '<div class="episode-id">E360</div>' in spoken_html
    assert '<div class="episode-id">E001</div>' in pattern_html
    assert '<div class="episode-id">E360</div>' in pattern_html
    assert current_html.count('class="current-page"') == 72
    assert spoken_html.count('class="scene"') == 36
    assert pattern_html.count('class="pattern-page"') == 360
    assert "Relations:" not in current_html
    assert "Relations:" not in spoken_html
    assert "Relations:" not in pattern_html
    assert "Source passage" not in spoken_html
    assert "Source passage" not in pattern_html
    assert ">READ<" in spoken_html
    assert ">SPEAK<" in spoken_html
    assert ">CONTEXT<" in pattern_html
    assert "___" not in current_html
    assert "___" not in spoken_html
    assert "___" not in pattern_html

    current_json = json.loads(
        (out / pdfs.OUTPUTS["current360"]["json"]).read_text(encoding="utf-8")
    )
    spoken_json = json.loads(
        (out / pdfs.OUTPUTS["spoken360"]["json"]).read_text(encoding="utf-8")
    )
    pattern_json = json.loads(
        (out / pdfs.OUTPUTS["pattern360"]["json"]).read_text(encoding="utf-8")
    )
    assert current_json["status"] == "FULL_DELIVERY_E001_E360"
    assert len(current_json["entries"]) == 360
    assert current_json["entries"][0]["episode_id"] == "U04-NEB-E001"
    assert current_json["entries"][-1]["episode_id"] == "U04-NEB-E360"
    assert len(spoken_json["entries"]) == 360
    assert spoken_json["entries"][0]["source_episode_id"] == "U04-NEB-E001"
    assert spoken_json["entries"][-1]["source_episode_id"] == "U04-NEB-E360"
    assert len(pattern_json["entries"]) == 360
    assert pattern_json["entries"][0]["source_episode_id"] == "U04-NEB-E001"
    assert pattern_json["entries"][-1]["source_episode_id"] == "U04-NEB-E360"

    manifest_path = out / pdfs.MANIFEST_NAME
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest

    for key in (
        "current360_mutated",
        "spoken360_mutated",
        "pattern360_mutated",
        "questionbank_modified",
        "forms_modified",
        "unit04_baseline_integrated",
        "unit04_runtime_integrated",
        "unit05_plus_opened",
        "a2_a2plus_unlocked",
        "second_pdf_renderer_created",
    ):
        assert manifest[key] is False


def test_u04_reader360_pdf_materialization_fails_closed_on_acceptance_status_drift(
    tmp_path: Path,
) -> None:
    accepted = deepcopy(reader.build_acceptance_report())
    accepted["status"] = "FAIL"
    with pytest.raises(
        pdfs.Reader360PdfMaterializationError,
        match="READER_ACCEPTANCE_STATUS_INVALID",
    ):
        _materialize(tmp_path, accepted)


def test_u04_reader360_pdf_materialization_fails_closed_on_alignment_drift(
    tmp_path: Path,
) -> None:
    accepted = deepcopy(reader.build_acceptance_report())
    accepted["current360_passage_alignment_count"] = 719
    with pytest.raises(
        pdfs.Reader360PdfMaterializationError,
        match="READER_ACCEPTANCE_DRIFT:current360_passage_alignment_count",
    ):
        _materialize(tmp_path, accepted)
