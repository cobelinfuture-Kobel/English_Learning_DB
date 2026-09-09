from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from product.a1fs_v1_2_1 import u04neb01_natural_episode_authority_cutover_108 as neb01


def test_u04neb01_materializes_exact_36x3_gpt_authored_natural_episode_bank() -> None:
    report = neb01.build_unit04_natural_episode_authority_cutover_108()
    assert report["status"] == neb01.STATUS
    assert report["revision"] == "GPT5_6_SOL_DIRECT_AUTHORED_108_V1"

    summary = report["summary"]
    assert summary["episode_count"] == 108
    assert summary["micro_scene_count"] == 36
    assert summary["episodes_per_micro_scene"] == 3
    assert summary["life_domain_count"] == 12
    assert summary["life_domain_distribution"] == {domain: 9 for domain in neb01.LIFE_DOMAINS}
    assert summary["semantic_review_pass_count"] == 108
    assert summary["exact_duplicate_count"] == 0
    assert summary["normalized_duplicate_count"] == 0
    assert summary["discourse_family_count"] >= 12
    assert set(summary["target_relation_distribution"]) == set(neb01.TARGET_RELATIONS)

    five_w = summary["five_w_one_h_distribution"]
    assert five_w["WHO"] == 108
    assert five_w["WHAT"] == 108
    assert five_w["WHERE"] == 108
    assert min(five_w["WHEN"], five_w["WHY"], five_w["HOW"]) >= 18


def test_u04neb01_is_static_authored_content_not_a_python_sentence_composer() -> None:
    source = Path(neb01.__file__).read_text(encoding="utf-8")
    assert "def _natural_passage" not in source
    assert "def _compose" not in source
    assert "fact1 +" not in source
    assert "GPT-5.6_SOL_DIRECT_SEMANTIC_COMPOSITION" in source

    bank = Path(neb01.__file__).resolve().parents[2] / neb01.BANK_PATH
    lines = bank.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 109
    assert sum(neb01.REVIEW_STATUS in line for line in lines[1:]) == 108

    report = neb01.build_unit04_natural_episode_authority_cutover_108()
    contract = report["authorship_contract"]
    assert contract["natural_language_authored_by"] == "GPT-5.6_SOL_DIRECT_SEMANTIC_COMPOSITION"
    assert contract["python_sentence_composer_used"] is False
    assert contract["python_role"] == "LOAD_VALIDATE_DEDUP_COVERAGE_AND_RUNTIME_PROOF_ONLY"
    assert contract["five_w_one_h_is_distributional_not_mandatory_full_template"] is True
    assert contract["support_exposure_language_promoted_to_unit04_target"] is False
    assert contract["support_relations_promoted_to_q03_target"] is False


def test_u04neb01_preserves_m2_source_evidence_and_does_not_mutate_q10_or_canonical_authority() -> None:
    report = neb01.build_unit04_natural_episode_authority_cutover_108()
    m2 = report["m2_source_chain"]
    assert m2["m2a_capability_count"] == 36
    assert m2["m2b_overlay_count"] == 36
    assert m2["m2c_task_projection_count"] == 144
    assert m2["language_generation_role"] == "EVIDENCE_AND_STRUCTURE_ONLY_NOT_SENTENCE_COMPOSER"

    q10 = report["q10_infrastructure_proof"]
    assert q10["source_form_count"] == 20
    assert q10["source_activity_count"] == 800
    assert q10["forms_mutated"] is False
    assert q10["activities_mutated"] is False
    assert q10["prompt_wording_reused_for_neb01"] is False
    assert q10["existing_assessment_item_reused_for_neb01"] is False

    safety = report["scope_safety"]
    assert safety == {
        "q03_relation_authority_modified": False,
        "q07_semantic_authority_modified": False,
        "q10_form01_20_modified": False,
        "q10_800_activities_modified": False,
        "canonical_grammar_modified": False,
        "canonical_vocabulary_modified": False,
        "canonical_chunk_modified": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
        "listening_materialized": False,
    }


def test_u04neb01_ci_readback_exposes_real_natural_passages_for_semantic_review() -> None:
    report = neb01.build_unit04_natural_episode_authority_cutover_108()
    samples = report["sample_episodes_one_per_domain"]
    assert len(samples) == 12
    assert {row["life_domain"] for row in samples} == set(neb01.LIFE_DOMAINS)
    assert all(len(row["passage"].split()) >= 18 for row in samples)

    readback = {
        "status": report["status"],
        "revision": report["revision"],
        "summary": report["summary"],
        "authorship_contract": report["authorship_contract"],
        "m2_source_chain": report["m2_source_chain"],
        "q10_infrastructure_proof": report["q10_infrastructure_proof"],
        "scope_safety": report["scope_safety"],
        "sample_episodes_one_per_domain": samples,
        "projection_sha256": report["projection_sha256"],
    }
    print("U04NEB01_NATURAL_EPISODE_READBACK=" + json.dumps(readback, ensure_ascii=False, sort_keys=True))
