from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_razq01a_unit01_unit02_authority_aware_windowed_filter_fullfix as fullfix


def _runtime(root: Path) -> None:
    runtime = root / "product" / "a1fs_v1_2_1" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "sequence.json").write_text(json.dumps({"GRAMMAR_ARTICLES_BASIC": 1, "GRAMMAR_REGULAR_PLURAL_NOUNS": 2, "OTHER": 3}), encoding="utf-8")
    bundles = {
        "A1FS:GRAMMAR_ARTICLES_BASIC:READING": {
            "lesson": {"skill": "READING", "level": "A1"},
            "assets": [{"learner_payload": {"prompt": "Choose a or an.", "response_mode": "select_one",
                "context": {"communicative_goal": "introduce one item", "grammar_clue": "Use a or an."},
                "target_refs": {"target_evp_sense_ids": ["vocabulary:apple:v1", "vocabulary:cat:v1"],
                    "target_egp_row_ids": ["egp-article"], "target_chunk_ids": ["chunk:ice_cream"],
                    "target_pattern_ids": ["SP_ARTICLE"]}}}]},
        "A1FS:GRAMMAR_REGULAR_PLURAL_NOUNS:READING": {
            "lesson": {"skill": "READING", "level": "A1"},
            "assets": [{"learner_payload": {"prompt": "Write the regular plural form of \"cat\".", "response_mode": "select_one",
                "context": {"communicative_goal": "refer to more than one item", "grammar_clue": "Use regular -s or -es."},
                "options": ["cats", "boxes", "buses", "children"], "supplied_morphemes": ["box", "es"]}}]},
    }
    (runtime / "bundles.json").write_text(json.dumps(bundles), encoding="utf-8")
    (runtime / "graph.json").write_text(json.dumps({"edges": []}), encoding="utf-8")


def _records() -> list[dict]:
    return [
        {"source_record_id": "r1", "source_level": "A", "source_type": "enriched_reading_unit", "text": "A cat has an apple. The cat is near the door.", "reusability_tags": ["grammar_pattern_seed", "listening_audio_seed"]},
        {"source_level": "A", "source_type": "normalized_reading_unit", "text": "A cat has an apple. The cat is near the door.", "reusability_tags": []},
        {"source_record_id": "r2", "source_level": "B", "source_type": "page_unit", "text": "Two cats are by three boxes.", "reusability_tags": ["grammar_pattern_seed", "picture_prompt_seed"]},
        {"source_record_id": "r3", "source_level": "J", "source_type": "reuse_unit_candidate", "text": "A long difficult introduction. Many cats are in boxes. The rest of this text is difficult and was written for older students.", "reusability_tags": ["dialogue_rewrite_seed"]},
        {"source_record_id": "r4", "source_level": "A", "source_type": "page_unit", "text": "A lioness was called an important predator.", "reusability_tags": ["exercise_seed"]},
        {"source_record_id": "r5", "source_level": "A", "source_type": "page_unit", "text": "A xylophonist sees a quasiperiodic artifact.", "reusability_tags": ["exercise_seed"]},
    ]


def _index(path: Path, envelope: str = "object") -> None:
    payload = {"builder_task": "RAZ-S11", "items": _records()} if envelope == "object" else _records()
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_profiles_use_runtime_authority_and_unit02_fallback(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles, lexicon = fullfix.build_unit_profiles(tmp_path)
    assert [p.unit_id for p in profiles] == ["GRAMMAR_ARTICLES_BASIC", "GRAMMAR_REGULAR_PLURAL_NOUNS"]
    unit2 = profiles[1]
    assert "RUNTIME_LEARNER_PAYLOAD_FALLBACK" in unit2.authority_sources
    assert {"cat", "box", "bus"}.issubset(set(unit2.cues))
    assert "response_mode:select_one" in unit2.question_types
    assert {"apple", "cat", "box"}.issubset(lexicon)


def test_long_source_is_split_into_local_target_windows(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles, _ = fullfix.build_unit_profiles(tmp_path)
    windows = fullfix.candidate_windows(_records()[3]["text"], profiles[1])
    assert any("Many cats are in boxes." in window for window in windows)
    assert all(len(fullfix._sentences(window)) <= 3 for window in windows)


def test_semantic_group_recovers_missing_lineage(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles, lexicon = fullfix.build_unit_profiles(tmp_path)
    acc = fullfix.Accumulator(profiles[0], lexicon, 20)
    for record in _records()[:2]:
        for window in fullfix.candidate_windows(record["text"], profiles[0]):
            acc.add(fullfix._result(record, record["text"], window, profiles[0], lexicon))
    acc.finish()
    assert acc.counts["lineage_group_recovered_count"] >= 1
    assert acc.counts["pass_count"] >= 1


def test_vocab_and_blocked_grammar_prevent_false_pass(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles, lexicon = fullfix.build_unit_profiles(tmp_path)
    blocked = fullfix._result(_records()[4], _records()[4]["text"], _records()[4]["text"], profiles[0], lexicon)
    unknown = fullfix._result(_records()[5], _records()[5]["text"], _records()[5]["text"], profiles[0], lexicon)
    assert fullfix._classify(blocked)[0] != "PASS"
    assert "past_simple" in blocked["blocked_grammar_features"] or "passive" in blocked["blocked_grammar_features"]
    assert fullfix._classify(unknown)[0] != "PASS"
    assert not unknown["vocabulary_gate"]["safe"]


def test_strict_skills_are_not_inferred_from_grammar_alone(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles, lexicon = fullfix.build_unit_profiles(tmp_path)
    record = {"source_record_id": "x", "source_level": "A", "source_type": "page_unit", "text": "A cat is here.", "reusability_tags": []}
    row = fullfix._result(record, record["text"], record["text"], profiles[0], lexicon)
    assert row["skill_eligibility"] == ["READING_SOURCE_ELIGIBLE"]
    assert "SPEAKING_PROMPT_ELIGIBLE" not in row["skill_eligibility"]
    assert "WRITING_SEED_ELIGIBLE" not in row["skill_eligibility"]


@pytest.mark.parametrize("envelope", ["array", "object"])
def test_fullfix_outputs_same_three_artifacts(tmp_path: Path, envelope: str) -> None:
    _runtime(tmp_path); index = tmp_path / "index.json"; out = tmp_path / "out"; _index(index, envelope)
    report = fullfix.run_calibration(repo_root=tmp_path, index_path=index, output_dir=out, sample_limit=20, progress_every=0)
    assert report["status"] == fullfix.PASS_STATUS
    assert report["validation"]["unit02_runtime_fallback_authority_used"]
    assert report["validation"]["strict_skill_eligibility_applied"]
    assert sorted(p.name for p in out.iterdir()) == [
        "a1fs_v1_razq01a_unit01_unit02_distinct_capacity_matrix.csv",
        "a1fs_v1_razq01a_unit01_unit02_filter_calibration.json",
        "a1fs_v1_razq01a_unit01_unit02_filter_validation.json",
    ]
    with (out / "a1fs_v1_razq01a_unit01_unit02_distinct_capacity_matrix.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert "lineage_group_recovered_count" in rows[0]
    assert "reading_source_eligible_capacity" in rows[0]


def test_cli_canary_exit_code(tmp_path: Path) -> None:
    _runtime(tmp_path); index = tmp_path / "index.json"; _index(index)
    code = fullfix.main(["--repo-root", str(tmp_path), "--index-path", str(index), "--output-dir", str(tmp_path / "out"), "--max-records", "4", "--progress-every", "0"])
    assert code == 0
