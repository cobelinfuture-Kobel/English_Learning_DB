from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as proposal
from ulga.builders import build_a1fs_v1_razq01b_unit01_contract_aware_replay as replay
from ulga.validators import validate_a1fs_v1_razq01b_unit01_contract_aware_replay as validator


def _runtime(root: Path) -> None:
    runtime = root / "product" / "a1fs_v1_2_1" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "sequence.json").write_text(
        json.dumps({"GRAMMAR_ARTICLES_BASIC": 1, "GRAMMAR_REGULAR_PLURAL_NOUNS": 2}),
        encoding="utf-8",
    )
    bundles = {
        "A1FS:GRAMMAR_ARTICLES_BASIC:READING": {
            "lesson": {"skill": "READING", "level": "A1"},
            "assets": [
                {
                    "learner_payload": {
                        "prompt": "Choose a, an, or the.",
                        "response_mode": "select_one",
                        "context": {
                            "communicative_goal": "introduce one item",
                            "grammar_clue": "Use a, an, or the.",
                        },
                        "target_refs": {
                            "target_evp_sense_ids": ["vocabulary:apple:v1", "vocabulary:cat:v1"],
                            "target_egp_row_ids": ["egp-article"],
                            "target_chunk_ids": ["chunk:ice_cream"],
                            "target_pattern_ids": ["SP_ARTICLE"],
                        },
                    }
                }
            ],
        },
        "A1FS:GRAMMAR_REGULAR_PLURAL_NOUNS:READING": {
            "lesson": {"skill": "READING", "level": "A1"},
            "assets": [
                {
                    "learner_payload": {
                        "prompt": "Write cats.",
                        "response_mode": "text",
                    }
                }
            ],
        },
    }
    (runtime / "bundles.json").write_text(json.dumps(bundles), encoding="utf-8")
    (runtime / "graph.json").write_text(json.dumps({"edges": []}), encoding="utf-8")


def _records() -> list[dict]:
    return [
        {
            "source_record_id": "r1",
            "source_level": "A",
            "source_type": "enriched_reading_unit",
            "text": "A cat has an apple. The cat is near the door.",
            "reusability_tags": ["grammar_pattern_seed", "listening_audio_seed"],
        },
        {
            "source_level": "A",
            "source_type": "normalized_reading_unit",
            "text": "A cat has an apple. The cat is near the door.",
            "reusability_tags": [],
        },
        {
            "source_record_id": "r2",
            "source_level": "A",
            "source_type": "page_unit",
            "text": "A friend is here.",
            "reusability_tags": ["exercise_seed"],
        },
        {
            "source_record_id": "r3",
            "source_level": "J",
            "source_type": "reuse_unit_candidate",
            "text": "A cat is near the door.",
            "reusability_tags": ["dialogue_rewrite_seed"],
        },
        {
            "source_record_id": "r4",
            "source_level": "A",
            "source_type": "page_unit",
            "text": "A cat was called a predator.",
            "reusability_tags": ["exercise_seed"],
        },
    ]


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    contract_path = tmp_path / "contract.json"
    approval_path = tmp_path / "approval.json"
    index_path = tmp_path / "index.json"
    contract_path.write_text(json.dumps(proposal.build_contract()), encoding="utf-8")
    approval_path.write_text(json.dumps(replay.build_operator_approval()), encoding="utf-8")
    index_path.write_text(json.dumps({"items": _records()}), encoding="utf-8")
    return contract_path, approval_path, index_path


def test_committed_approval_is_hash_bound_and_deterministic() -> None:
    root = Path(__file__).resolve().parents[2]
    committed = json.loads((root / replay.DEFAULT_APPROVAL).read_text(encoding="utf-8"))
    assert committed == replay.build_operator_approval()
    contract = proposal.build_contract()
    summary = replay.verify_operator_approval(contract, committed)
    assert summary["operator_approval_verified"] is True
    assert summary["approved_contract_sha256"] == replay.APPROVED_CONTRACT_SHA256
    assert contract["contract_sha256"] == replay.APPROVED_CONTRACT_SHA256


def test_approval_fails_closed_on_contract_or_manifest_drift() -> None:
    contract = proposal.build_contract()
    approval = replay.build_operator_approval()
    drifted = deepcopy(contract)
    drifted["material_contract"]["window_gate"]["word_count_max"] = 46
    core = {
        key: deepcopy(value)
        for key, value in drifted.items()
        if key != "contract_sha256"
    }
    drifted["contract_sha256"] = proposal.digest(core)
    with pytest.raises(replay.ReplayError, match="APPROVED_CONTRACT_DIGEST_MISMATCH"):
        replay.verify_operator_approval(drifted, approval)
    bad_approval = deepcopy(approval)
    bad_approval["boundaries"]["a2_unlocked"] = True
    with pytest.raises(replay.ReplayError, match="OPERATOR_APPROVAL_MANIFEST_INVALID"):
        replay.verify_operator_approval(contract, bad_approval)


def test_contract_profile_uses_approved_unit01_authorities(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles, lexicon = replay.fullfix.build_unit_profiles(tmp_path, limit=1)
    contract = proposal.build_contract()
    profile = replay._contract_profile(profiles[0], contract)
    effective = set(profile.cues)
    assert profile.unit_id == "GRAMMAR_ARTICLES_BASIC"
    assert {"apple", "cat", "home", "a bag", "living room"}.issubset(effective)
    assert "toy" not in effective
    assert "UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT" in profile.authority_sources
    assert set(profile.egp_ids) == set(proposal.CORE_EGP_ROWS) | set(proposal.GUIDED_EGP_ROWS)
    assert "vocabulary:home:v_3704" not in profile.evp_ids
    assert "home" in replay._contract_lexicon(lexicon, contract)
    assert "toy" not in replay._contract_lexicon(lexicon, contract)


def test_contract_aware_replay_outputs_unit01_only_capacity(tmp_path: Path) -> None:
    _runtime(tmp_path)
    contract_path, approval_path, index_path = _inputs(tmp_path)
    out = tmp_path / "out"
    report = replay.run_replay(
        repo_root=tmp_path,
        index_path=index_path,
        output_dir=out,
        contract_path=contract_path,
        approval_path=approval_path,
        sample_limit=30,
        progress_every=0,
    )
    assert report["status"] == replay.PASS_STATUS
    assert report["scope"]["allowed_units"] == ["GRAMMAR_ARTICLES_BASIC"]
    assert report["scope"]["blocked_units"] == "UNIT_02_TO_UNIT_24"
    assert report["validation"]["operator_approval_verified"] is True
    assert report["validation"]["contract_profile_overlay_applied"] is True
    funnel = report["unit"]["filter_funnel"]
    assert funnel["pass_count"] >= 1
    assert funnel["borderline_count"] >= 1
    assert funnel["reject_count"] >= 1
    assert funnel["lineage_group_recovered_count"] >= 1
    samples = report["unit"]["samples"]
    assert any(row["contract_gate"]["active_vocabulary_hits"] for row in samples["PASS"])
    assert any(
        "ACTIVE_VOCABULARY_HIT_MISSING" in row["reasons"]
        for row in samples["REJECT"]
    )
    assert sorted(path.name for path in out.iterdir()) == sorted(
        [replay.OUTPUT_REPORT, replay.OUTPUT_VALIDATION, replay.OUTPUT_MATRIX]
    )
    with (out / replay.OUTPUT_MATRIX).open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["unit_id"] == "GRAMMAR_ARTICLES_BASIC"
    validated = validator.validate_report(
        report,
        proposal.build_contract(),
        replay.build_operator_approval(),
    )
    assert validated["validation_status"] == validator.PASS_STATUS


def test_cli_fails_closed_without_approved_manifest(tmp_path: Path) -> None:
    _runtime(tmp_path)
    contract_path, approval_path, index_path = _inputs(tmp_path)
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval["approved_contract_sha256"] = "0" * 64
    approval_path.write_text(json.dumps(approval), encoding="utf-8")
    code = replay.main(
        [
            "--repo-root",
            str(tmp_path),
            "--index-path",
            str(index_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--contract",
            str(contract_path),
            "--approval",
            str(approval_path),
            "--progress-every",
            "0",
        ]
    )
    assert code == 1
