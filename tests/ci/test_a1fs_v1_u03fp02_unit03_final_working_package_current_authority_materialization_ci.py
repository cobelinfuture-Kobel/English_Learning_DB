import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from ulga.builders import (
    build_a1fs_v1_u03fp02_unit03_final_working_package_current_authority_materialization as b,
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fixture"])
        writer.writerow(["ok"])


def _fixture_handoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "handoff"
    root.mkdir()

    _write_json(
        root / "Unit03_Q01_Grammar.json",
        {
            "sha256": b.Q1_SHA,
            "grammar_scope": {"pronoun_inventory_denominator": 7},
            "target_egp_rows": [{"egp_row_id": "1741163713868x463659211645272000"}],
        },
    )
    _write_json(
        root / "Unit03_Q02_Vocabulary.json",
        {
            "row_count": 40,
            "rows": [{"resource_id": f"VR-{i:03d}"} for i in range(40)],
            "scope_summary": {"unit03_definitely_new_vocabulary_claimed": False},
        },
    )
    _write_json(
        root / "Unit03_Q03_Pronoun_Forms.json",
        {
            "sha256": b.Q3_SHA,
            "coverage_denominators": {
                "closed_subject_pronoun_form_count": 7,
                "generated_inflection_count": 0,
            },
            "rows": [{"surface": value} for value in ("i", "you", "he", "she", "it", "we", "they")],
        },
    )
    _write_json(
        root / "Unit03_Q04_Chunks.json",
        {
            "sha256": b.Q4_SHA,
            "coverage_denominators": {
                "cumulative_distinct_surface_rows": 50,
                "unit03_native_surface_rows": 0,
            },
            "rows": [{"surface": "a book"}],
        },
    )

    q6_path = root / "Unit03_Q06_Sentence_Assets.json"
    _write_json(q6_path, {"fixture": True, "note": "no real/private sentence payload in CI fixture"})
    q6_digest = hashlib.sha256(q6_path.read_bytes()).hexdigest()
    monkeypatch.setattr(b, "Q6_SHA", q6_digest)
    _write_csv(root / "Unit03_Q06_Sentence_Assets.csv")

    _write_json(
        root / "Unit03_Q07_MicroScene_Coverage.json",
        {
            "coverage_denominators": {
                "subject_pronoun_scene_covered_count": 7,
                "unit03_structural_pronoun_projection_row_count": 540,
                "unit03_new_canonical_scene_count": 0,
            },
            "pronoun_coverage": [{"subject_pronoun": p, "coverage_status": "COVERED"} for p in ("i", "you", "he", "she", "it", "we", "they")],
        },
    )
    _write_csv(root / "Unit03_Q07_Canonical_Scene_Reuse.csv")
    _write_csv(root / "Unit03_Q07_Structural_Scene_Projections.csv")

    _write_json(
        root / "Unit03_Q08_Communicative_Functions.json",
        {
            "sha256": b.Q8_SHA,
            "functions": [{"function": value} for value in b.fp01.Q8_FUNCTIONS],
            "claim_boundaries": {
                "communicative_function_is_not_sentence_pattern_authority": True,
                "q9_not_materialized": True,
                "q10_not_materialized": True,
                "a2_unlocked": False,
            },
        },
    )
    return root


def test_materializes_complete_q01_q10_current_working_package(tmp_path, monkeypatch):
    handoff = _fixture_handoff(tmp_path, monkeypatch)
    output = tmp_path / "out"
    zip_output = tmp_path / "Unit03_Final_Working_Package.zip"

    manifest = b.materialize(handoff, output, zip_output)

    assert manifest["status"] == b.PASS_STATUS
    assert manifest["downstream_readiness"]["q1_q10_roles_present"] is True
    assert manifest["downstream_readiness"]["form_production_input_ready"] is True
    assert manifest["stale_replacements"]["old_q05_eight_family_handoff_replaced"] is True
    assert manifest["stale_replacements"]["old_q09_q10_files_replaced"] is True
    assert manifest["stale_replacements"]["historical_640_runtime_current"] is False
    assert manifest["stale_replacements"]["current_successor_runtime_occurrences"] == 800
    assert list(manifest["q01_q10_map"]) == [f"Q{i:02d}" for i in range(1, 11)]
    assert all(manifest["role_file_map"][f"Q{i:02d}"] for i in range(1, 11))

    assert (output / "Unit03_Q06_Sentence_Assets.json").read_bytes() == (handoff / "Unit03_Q06_Sentence_Assets.json").read_bytes()
    assert (output / b.fp01.Q09_JSON).is_file()
    assert (output / b.fp01.Q10I_JSON).is_file()
    assert (output / b.fp01.Q10R_JSON).is_file()
    assert (output / b.MANIFEST_NAME).is_file()

    current_q5 = json.loads((output / b.CURRENT_Q05_FILES[0]).read_text(encoding="utf-8"))
    assert current_q5["pedagogical_pattern_families"]["cumulative_pattern_family_count"] == 7
    assert current_q5["pedagogical_pattern_families"]["unit03_new_canonical_pattern_family_count"] == 0
    assert current_q5["exact_sentence_frames"]["cumulative_exact_frame_count"] == 15
    assert current_q5["supersedes_old_eight_family_working_handoff"] is True

    current_q8 = json.loads((output / "Unit03_Q08_Communicative_Functions.json").read_text(encoding="utf-8"))
    assert current_q8["source_snapshot_claim_boundaries"]["q9_not_materialized"] is True
    assert current_q8["source_snapshot_claim_boundaries"]["q10_not_materialized"] is True
    assert "q9_not_materialized" not in current_q8["claim_boundaries"]
    assert "q10_not_materialized" not in current_q8["claim_boundaries"]
    assert current_q8["current_package_reconciliation"]["q09_current_successor_materialized"] is True
    assert current_q8["current_package_reconciliation"]["q10_current_successor_materialized"] is True

    current_q10 = json.loads((output / b.fp01.Q10R_JSON).read_text(encoding="utf-8"))
    assert current_q10["form_count"] == 20
    assert current_q10["activities_per_form"] == 40
    assert current_q10["runtime_occurrence_count"] == 800
    assert current_q10["section_counts_per_form"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}

    assert zip_output.is_file()
    with zipfile.ZipFile(zip_output) as archive:
        names = set(archive.namelist())
    assert f"Unit03_Final_Working_Package/{b.MANIFEST_NAME}" in names
    assert f"Unit03_Final_Working_Package/{b.fp01.Q10R_JSON}" in names


def test_missing_required_handoff_file_fails_closed(tmp_path, monkeypatch):
    handoff = _fixture_handoff(tmp_path, monkeypatch)
    (handoff / "Unit03_Q07_Structural_Scene_Projections.csv").unlink()
    with pytest.raises(b.U03FP02MaterializationError, match="MISSING_HANDOFF_FILES"):
        b.materialize(handoff, tmp_path / "out")


def test_current_q05_is_generated_from_git_authority_not_old_handoff(tmp_path, monkeypatch):
    handoff = _fixture_handoff(tmp_path, monkeypatch)
    _write_json(handoff / "Q05_Sentence_Patterns.json", {"stale": True, "pattern_family_count": 8})
    output = tmp_path / "out"

    b.materialize(handoff, output)

    current_q5 = json.loads((output / b.CURRENT_Q05_FILES[0]).read_text(encoding="utf-8"))
    assert "stale" not in current_q5
    assert current_q5["pedagogical_pattern_families"]["cumulative_pattern_family_count"] == 7
    assert (output / b.CURRENT_Q05_FILES[0]).is_file()
