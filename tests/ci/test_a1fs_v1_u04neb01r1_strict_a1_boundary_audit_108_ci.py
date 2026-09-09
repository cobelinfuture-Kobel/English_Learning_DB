from __future__ import annotations

from pathlib import Path

from product.a1fs_v1_2_1 import u04neb01r1_strict_a1_boundary_audit_108 as r1


def _episodes_by_id(report):
    return {row["episode_id"]: row for row in report["effective_episodes"]}


def test_u04neb01r1_materializes_108_with_76_bounded_rewrites() -> None:
    report = r1.build_unit04_neb01r1_strict_a1_boundary_audit_108()
    assert report["status"] == r1.STATUS
    assert report["revision"] == "GPT5_6_SOL_UNIT04_A1A1PLUS_BOUNDARY_R1"

    summary = report["summary"]
    assert summary["effective_episode_count"] == 108
    assert summary["rewritten_episode_count"] == 76
    assert summary["unchanged_episode_count"] == 32
    assert summary["blocked_pattern_count"] == 0
    assert summary["exact_duplicate_count"] == 0
    assert summary["normalized_duplicate_count"] == 0
    assert set(summary["unit04_target_relation_distribution"]) == set(r1.TARGET_RELATIONS)


def test_u04neb01r1_fixes_operator_identified_and_systematic_boundary_leaks() -> None:
    report = r1.build_unit04_neb01r1_strict_a1_boundary_audit_108()
    episodes = _episodes_by_id(report)

    e027 = episodes["U04-NEB-E027"]["passage"]
    assert "where the art things are" not in e027
    assert "shows the art things to a friend" in e027
    assert "inside the cup" in e027
    assert "on the table" in e027
    assert "under the table" in e027

    e030 = episodes["U04-NEB-E030"]["passage"]
    assert "almost" not in e030.casefold()
    assert "time to" not in e030.casefold()
    assert "leave the playground soon" in e030

    for row in report["effective_episodes"]:
        text = row["passage"].casefold()
        assert " while " not in f" {text} "
        assert " until " not in f" {text} "
        assert " into " not in f" {text} "
        assert " from " not in f" {text} "
        assert " where " not in f" {text} "
        assert " nearby" not in text


def test_u04neb01r1_preserves_unit04_relation_and_semantic_lineage_metadata() -> None:
    report = r1.build_unit04_neb01r1_strict_a1_boundary_audit_108()
    for row in report["effective_episodes"]:
        assert row["source_fact_lineage"]
        assert row["target_relations"]
        assert row["micro_scene_id"].startswith("U04-NEB-MS")
        assert row["life_domain"]
        assert row["discourse_family"]

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


def test_u04neb01r1_keeps_basic_support_language_non_target_and_reports_scene_lexis() -> None:
    report = r1.build_unit04_neb01r1_strict_a1_boundary_audit_108()
    contract = report["language_boundary_contract"]
    assert contract["teaching_target"] == "UNIT04_PLACE_SPATIAL_RELATIONS_ONLY"
    assert contract["productive_grammar_ceiling"] == "A1_A1PLUS"
    assert contract["basic_connectors_allowed"] is True
    assert contract["controlled_support_is_teaching_target"] is False
    assert contract["controlled_support_is_assessment_target"] is False
    assert contract["a2_grammar_productive_use_allowed"] is False
    assert contract["b1_plus_grammar_allowed"] is False
    assert contract["scene_required_higher_lexis_policy"] == "RECEPTIVE_EXPOSURE_ONLY_NO_CANONICAL_PROMOTION"

    support = report["summary"]["controlled_support_distribution"]
    assert support.get("and", 0) > 0
    assert support.get("but", 0) > 0
    assert support.get("first", 0) > 0
    assert support.get("then", 0) > 0

    exposures = report["summary"]["known_scene_required_lexical_exposure_distribution"]
    assert exposures.get("clinic:B1", 0) > 0
    assert exposures.get("statue:B1", 0) > 0
    assert exposures.get("trolley:B2", 0) > 0
    assert exposures.get("magazine:A2", 0) > 0
    assert exposures.get("puzzle:A2", 0) > 0


def test_u04neb01r1_remains_static_gpt_authored_content_not_python_composition() -> None:
    source = Path(r1.__file__).read_text(encoding="utf-8")
    assert "def _compose" not in source
    assert "def _natural_passage" not in source
    report_contract = r1.build_unit04_neb01r1_strict_a1_boundary_audit_108()["language_boundary_contract"]
    assert report_contract["python_sentence_composer_used"] is False
    assert report_contract["gpt_authored_rewrite_overlay_used"] is True
