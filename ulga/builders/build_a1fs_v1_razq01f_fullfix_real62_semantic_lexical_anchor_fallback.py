#!/usr/bin/env python3
"""Apply the Real62 lexical-anchor FullFix to the existing RAZQ01F pipeline.

The merged RAZQ01F composition remains the only multi-session pipeline. This
module patches its shared RAZQ01E compatibility function so a base Unit01 task
may use an approved content asset when the task's complete lexical anchor is
present in that asset, even when the task family itself is not listed in the
asset projection. The asset must still have an approved projection for the
same skill. Missing or contradictory noun/adjective anchors remain fail-closed.
"""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_admitted_content_asset_qb_consumer_workbench
    as binding_consumer,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_unit01_real_content_multi_session_diversity_learner_use_acceptance
    as _core,
)

# Preserve the existing RAZQ01F implementation as the sole runtime pipeline.
for _name in dir(_core):
    if _name not in {"__name__", "__loader__", "__package__", "__spec__"}:
        globals()[_name] = getattr(_core, _name)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Thin compatibility FullFix for the existing RAZQ01F composition; it creates no content, bank, planner, renderer, database, runtime table, response capture, scoring authority, audio, A2, or Unit02-Unit24 artifact and only permits same-skill approved assets whose complete Unit01 noun/adjective lexical anchor matches the existing task."
FULLFIX_TASK_ID = (
    "A1FS-V1-RAZQ01F-FULLFIX_"
    "Real62SemanticLexicalAnchorCompatibilityFallback"
)
FULLFIX_PASS_STATUS = (
    "PASS_A1FS_V1_RAZQ01F_FULLFIX_REAL62_SEMANTIC_LEXICAL_ANCHOR_FALLBACK"
)
FULLFIX_NEXT_SHORT_STEP = (
    "A1FS-V1-RAZQ01F_"
    "LocalPrivateReal62MultiSessionDiversityAndLearnerUseReadbackRetry"
)

if not hasattr(binding_consumer, "_razq01f_pre_fullfix_compatibility"):
    binding_consumer._razq01f_pre_fullfix_compatibility = (
        binding_consumer.compatibility
    )

_ORIGINAL_COMPATIBILITY = binding_consumer._razq01f_pre_fullfix_compatibility


def semantic_lexical_anchor_compatibility(
    learner_item: Mapping[str, Any],
    private_item: Mapping[str, Any],
    asset: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return existing compatibility or a strict same-skill lexical fallback.

    Fallback admission requires:

    * one approved projection for the exact learner skill;
    * a non-empty task noun that exactly matches the asset active noun set;
    * when the task has an adjective, that adjective must also exactly match;
    * no family or Unit01 pattern authority is invented.

    This admits the real ``PF06 VERY-BIG-BOX`` task against an approved
    ``big + box`` content asset while still rejecting partial-topic matches.
    """

    existing = _ORIGINAL_COMPATIBILITY(learner_item, private_item, asset)
    if existing is not None:
        return existing

    skill = str(learner_item.get("skill") or "")
    projection = binding_consumer._projection(asset, skill)
    if projection is None:
        return None

    lexical = private_item.get("lexical_slots") or {}
    noun = str(lexical.get("noun") or "").strip().casefold()
    adjective = str(lexical.get("adjective") or "").strip().casefold()
    if not noun:
        return None

    alignment = asset.get("target_alignment") or {}
    asset_nouns = {
        str(value).strip().casefold()
        for value in alignment.get("active_nouns") or []
        if str(value).strip()
    }
    asset_adjectives = {
        str(value).strip().casefold()
        for value in alignment.get("active_adjectives") or []
        if str(value).strip()
    }

    noun_match = noun in asset_nouns
    adjective_match = not adjective or adjective in asset_adjectives
    if not noun_match or not adjective_match:
        return None

    return {
        "mode": "SEMANTIC_LEXICAL_ANCHOR_EXACT",
        "score": 80 + (20 if adjective else 0),
        "exact_family": False,
        "pattern_match": False,
        "noun_match": True,
        "adjective_match": True,
        "projection": dict(projection),
        "semantic_anchor_fallback": True,
    }


def install_fullfix() -> None:
    """Install the compatibility override on the shared RAZQ01E module."""

    binding_consumer.compatibility = semantic_lexical_anchor_compatibility


def build_workbench(*args, **kwargs):
    """Build through the existing core with the FullFix freshly installed.

    The repository test surface contains compatibility fixtures that may restore
    the pre-FullFix function between calls. Reinstalling at this governed entry
    keeps later release-candidate builds deterministic without creating another
    renderer or multi-session pipeline.
    """

    install_fullfix()
    return _core.build_workbench(*args, **kwargs)


install_fullfix()


def main(argv=None) -> int:
    install_fullfix()
    result = _core.main(argv)
    if result == 0:
        print(f"FULLFIX_STATUS={FULLFIX_PASS_STATUS}")
        print(f"FULLFIX_NEXT_SHORT_STEP={FULLFIX_NEXT_SHORT_STEP}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
