from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_razq01b2_unit01_v2_approval_replay_consumer_reconciliation as reconciliation
from ulga.validators import validate_a1fs_v1_razq01b2_unit01_v2_approval_replay_consumer_reconciliation as validator


def _runtime(root: Path) -> None:
    runtime = root / "product" / "a1fs_v1_2_1" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "sequence.json").write_text(
        json.dumps({
            "GRAMMAR_ARTICLES_BASIC": 1,
            "GRAMMAR_REGULAR_PLURAL_NOUNS": 2,
        }),
        encoding="utf-8",
    )
    bundles = {
        "A1FS:GRAMMAR_ARTICLES_BASIC:READING": {
            "lesson": {"skill": "READING", "level": "A1"},
            "assets": [{
                "learner_payload": {
                    "prompt": "Choose a, an, or the.",
                    "response_mode": "select_one",
                    "context": {
                        "communicative_goal": "introduce one item",
                        "grammar_clue": "Use a, an, or the.",
                    },
                    "target_refs": {
                        "target_evp_sense_ids": [
                            "vocabulary:apple:v1",
                            "vocabulary:cat:v1",
                        ],
                        "target_egp_row_ids": ["egp-article"],
                        "target_chunk_ids": ["chunk:ice_cream"],
                        "target_pattern_ids": ["SP_ARTICLE"],
                    },
                }
            }],
        },
        "A1FS:GRAMMAR_REGULAR_PLURAL_NOUNS:READING": {
            "lesson": {"skill": "READING", "level": "A1"},
            "assets": [{
                "learner_payload": {
                    "prompt": "Write cats.",
                    "response_mode": "text",
                }
            }],
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
            "text": "An old book is on the desk.",
            "reusability_tags": ["grammar_pattern_seed", "listening_audio_seed"],
        },
        {
            "source_level": "A",
            "source_type": "normalized_reading_unit",
            "text": "An old book is on the desk.",
            "reusability_tags": [],
        },
        {
            "source_record_id": "r2",
            "source_level": "A",
            "source_type": "page_unit",
            "text": "A old book is on the desk.",
            "reusability_tags": ["exercise_seed"],
        },
        {
            "source_record_id": "r3",
            "source_level": "J",
            "source_type": "reuse_unit_candidate",
            "text": "A red book is on the desk.",
            "reusability_tags": ["dialogue_rewrite_seed"],
        },
        {
            "source_record_id": "r4",
            "source_level": "A",
            "source_type": "page_unit",
            "text": "A red nose is here.",
            "reusability_tags": ["exercise_seed"],
        },
    ]


def _baseline() -> dict:
    return {
        "inputs": {
            "approved_contract_sha256": (
                reconciliation.LEGACY_APPROVED_CONTRACT_SHA256
            )
        },
        "unit": {
            "filter_funnel": {
                "pass_count": 2,
                "borderline_count": 1,
                "reject_count": 1,
            },
            "strict_skill_capacity": {
                "READING_SOURCE_ELIGIBLE": 2,
                "SPEAKING_PROMPT_ELIGIBLE": 1,
                "WRITING_SEED_ELIGIBLE": 2,
            },
            "rewrite_skill_capacity": {
                "READING_REWRITE_CANDIDATE": 1,
                "WRITING_REWRITE_CANDIDATE": 1,
            },
        },
    }


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    contract_path = tmp_path / "contract.json"
    approval_path = tmp_path / "approval.json"
    index_path = tmp_path / "index.json"
    baseline_path = tmp_path / "baseline.json"
    contract_path.write_text(
        json.dumps(contract_builder.build_contract()),
        encoding="utf-8",
    )
    approval_path.write_text(
        json.dumps(reconciliation.build_operator_approval()),
        encoding="utf-8",
    )
    index_path.write_text(json.dumps({"items": _records()}), encoding="utf-8")
    baseline_path.write_text(json.dumps(_baseline()), encoding="utf-8")
    return contract_path, approval_path, index_path, baseline_path


def test_v2_approval_is_exactly_bound_and_supersedes_v1() -> None:
    contract = contract_builder.build_contract()
    approval = reconciliation.build_operator_approval()
    summary = reconciliation.verify_operator_approval(contract, approval)
    assert contract["contract_sha256"] == reconciliation.APPROVED_CONTRACT_SHA256
    assert (
        approval["approved_dimensions"]
        == contract["operator_review"]["review_dimensions"]
    )
    assert (
        approval["supersedes_contract_sha256"]
        == reconciliation.LEGACY_APPROVED_CONTRACT_SHA256
    )
    assert summary["approved_dimension_count"] == 7
    assert summary["legacy_contract_superseded"] is True


def test_v2_approval_fails_closed_on_contract_or_boundary_drift() -> None:
    contract = contract_builder.build_contract()
    approval = reconciliation.build_operator_approval()
    drifted = deepcopy(contract)
    drifted["material_contract"]["window_gate"]["word_count_max"] = 46
    core = {
        key: deepcopy(value)
        for key, value in drifted.items()
        if key != "contract_sha256"
    }
    drifted["contract_sha256"] = contract_builder.digest(core)
    with pytest.raises(
        reconciliation.replay.ReplayError,
        match="APPROVED_V2_CONTRACT_DIGEST_MISMATCH",
    ):
        reconciliation.verify_operator_approval(drifted, approval)
    bad = deepcopy(approval)
    bad["boundaries"]["a2_unlocked"] = True
    with pytest.raises(
        reconciliation.replay.ReplayError,
        match="MANIFEST_INVALID",
    ):
        reconciliation.verify_operator_approval(contract, bad)


def test_profile_and_lexicon_consume_v2_authorities(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles, runtime_lexicon = reconciliation.fullfix.build_unit_profiles(
        tmp_path,
        limit=1,
    )
    contract = contract_builder.build_contract()
    profile = reconciliation._contract_profile(profiles[0], contract)
    cues = set(profile.cues)
    assert {
        "apple",
        "cat",
        "big",
        "old",
        "a red book",
        "a very old book",
        "living room",
    } <= cues
    assert "ice cream" not in cues
    assert "UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT_V2" in profile.authority_sources
    assert "vocabulary:old:v_6073" in profile.evp_ids
    assert "EVP_CHUNK_000054" not in profile.chunk_ids
    lexicon = reconciliation._contract_lexicon(runtime_lexicon, contract)
    assert {"big", "old", "ice", "cream"} <= lexicon
    assert "toy" not in lexicon


def test_v2_replay_outputs_capacity_delta_and_article_sound_gate(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    contract_path, approval_path, index_path, baseline_path = _inputs(tmp_path)
    report = reconciliation.run_replay(
        repo_root=tmp_path,
        index_path=index_path,
        output_dir=tmp_path / "out",
        contract_path=contract_path,
        approval_path=approval_path,
        baseline_report_path=baseline_path,
        sample_limit=30,
        progress_every=0,
    )
    assert report["status"] == reconciliation.PASS_STATUS
    assert report["validation"]["active_memorization_count"] == 22
    assert report["validation"]["article_sound_gate_applied"] is True
    assert (
        report["validation"]["listening_product_boundary"]
        == "DEFERRED_NO_LISTENING_LESSON_IN_UNIT01_RUNTIME"
    )
    assert report["capacity_delta"]["baseline_supplied"] is True
    assert (
        report["capacity_delta"]["baseline_contract_sha256"]
        == reconciliation.LEGACY_APPROVED_CONTRACT_SHA256
    )
    assert isinstance(report["capacity_delta"]["delta_v2_minus_v1"], dict)
    samples = report["unit"]["samples"]
    assert any(
        "an old book" in row["contract_gate"]["adjective_noun_phrases"]
        for row in samples["PASS"]
    )
    assert any(
        "INDEFINITE_ARTICLE_SOUND_MISMATCH" in row["reasons"]
        for row in samples["REJECT"]
    )
    result = validator.validate_report(
        report,
        contract_builder.build_contract(),
        reconciliation.build_operator_approval(),
        require_baseline=True,
    )
    assert result["validation_status"] == validator.PASS_STATUS


def test_invalid_v1_baseline_digest_fails_closed(tmp_path: Path) -> None:
    _runtime(tmp_path)
    contract_path, approval_path, index_path, baseline_path = _inputs(tmp_path)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["inputs"]["approved_contract_sha256"] = "0" * 64
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        reconciliation.replay.ReplayError,
        match="V1_BASELINE_CONTRACT_DIGEST_INVALID",
    ):
        reconciliation.run_replay(
            repo_root=tmp_path,
            index_path=index_path,
            output_dir=tmp_path / "out",
            contract_path=contract_path,
            approval_path=approval_path,
            baseline_report_path=baseline_path,
            progress_every=0,
        )
