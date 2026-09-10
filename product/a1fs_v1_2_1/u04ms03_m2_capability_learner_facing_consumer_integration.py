from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    STATUS as M2A_STATUS,
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)
from product.a1fs_v1_2_1.u04ms02c_ket_four_skill_task_assessment_projection import (
    STATUS as M2C_STATUS,
    build_unit04_ket_four_skill_task_assessment_projection,
)
from product.a1fs_v1_2_1.u04neb02_natural_episode_bank_360 import (
    STATUS as CURRENT360_STATUS,
    build_unit04_neb02_natural_episode_bank_360,
)

TASK_ID = "A1FS-V1-U04NEB_Current360_DownstreamConsumerCutover"
STATUS = "PASS_A1FS_V1_U04NEB_CURRENT360_DOWNSTREAM_CONSUMER_CUTOVER"
REVISION = "CURRENT360_RSW_CUTOVER_LISTENING_KEEP_R2"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Existing Unit04 learner-facing consumer cutover only. Reading, Speaking, and Writing "
    "consume already-authored and validated Current360 passages while preserving the independent "
    "Q07/M2-A fact trace. Listening keeps its pre-existing Q07/M2-A task projection exactly. "
    "This consumer does not compose, rewrite, or canonically promote learner-facing English."
)

CURRENT360_AUTHORITY = "UNIT04_CURRENT360_PASSAGE_AUTHORITY"
UPSTREAM_Q07_M2A_AUTHORITY = "UNIT04_Q07_VIA_M2A"
RSW_SKILLS = ("READING", "SPEAKING", "WRITING")
LISTENING_SKILL = "LISTENING"
SKILL_OFFSETS = {"READING": 0, "SPEAKING": 1, "WRITING": 2}
SUPPORT_RELATIONS = ("next to", "in front of")

CURRENT360_REF = "product/a1fs_v1_2_1/u04neb02_natural_episode_bank_360.py"
M2A_REF = "product/a1fs_v1_2_1/u04ms02a_raz_aw_multi_sentence_micro_scene_capability.py"
M2C_REF = "product/a1fs_v1_2_1/u04ms02c_ket_four_skill_task_assessment_projection.py"
Q07_REF = "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"


class DownstreamConsumerCutoverError(ValueError):
    pass


def _split_csv(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _episode_relation_surfaces(episode: dict[str, Any]) -> list[str]:
    surfaces = set(_split_csv(episode.get("target_relations")))
    passage = str(episode.get("passage") or "")
    for surface in SUPPORT_RELATIONS:
        if _contains_surface(passage, surface):
            surfaces.add(surface)
    return sorted(surfaces)


def _validate_current360(report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("status") != CURRENT360_STATUS:
        raise DownstreamConsumerCutoverError("current360_not_pass")
    summary = report.get("summary")
    episodes = report.get("effective_episodes")
    if not isinstance(summary, dict) or not isinstance(episodes, list):
        raise DownstreamConsumerCutoverError("current360_structure_invalid")
    if summary.get("episode_count") != 360 or len(episodes) != 360:
        raise DownstreamConsumerCutoverError("current360_episode_count_invalid")
    if summary.get("micro_scene_count") != 36:
        raise DownstreamConsumerCutoverError("current360_micro_scene_count_invalid")
    safety = report.get("scope_safety", {})
    if safety.get("q10_form01_20_modified") is not False:
        raise DownstreamConsumerCutoverError("current360_q10_scope_drift")
    if safety.get("a2_a2plus_unlocked") is not False:
        raise DownstreamConsumerCutoverError("current360_a2_scope_drift")

    seen: set[str] = set()
    for row in episodes:
        if not isinstance(row, dict):
            raise DownstreamConsumerCutoverError("current360_episode_row_invalid")
        episode_id = str(row.get("episode_id") or "")
        if not episode_id or episode_id in seen:
            raise DownstreamConsumerCutoverError("current360_episode_identity_invalid")
        seen.add(episode_id)
        for field in (
            "micro_scene_id",
            "life_domain",
            "governed_scene_family",
            "discourse_family",
            "target_relations",
            "source_fact_lineage",
            "passage",
        ):
            if not str(row.get(field) or "").strip():
                raise DownstreamConsumerCutoverError(
                    f"current360_episode_lineage_missing:{episode_id}:{field}"
                )
        if not _episode_relation_surfaces(row):
            raise DownstreamConsumerCutoverError(
                f"current360_visible_relation_surface_missing:{episode_id}"
            )
    return episodes


def _validate_upstream(
    m2a: dict[str, Any],
    m2c: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if m2a.get("status") != M2A_STATUS:
        raise DownstreamConsumerCutoverError("m2a_not_pass")
    if m2c.get("status") != M2C_STATUS:
        raise DownstreamConsumerCutoverError("m2c_not_pass")
    capabilities = m2a.get("capabilities")
    tasks = m2c.get("task_projections")
    if not isinstance(capabilities, list) or len(capabilities) != 36:
        raise DownstreamConsumerCutoverError("m2a_capability_count_invalid")
    if not isinstance(tasks, list) or len(tasks) != 144:
        raise DownstreamConsumerCutoverError("m2c_task_projection_count_invalid")

    by_id: dict[str, dict[str, Any]] = {}
    for capability in capabilities:
        if not isinstance(capability, dict):
            raise DownstreamConsumerCutoverError("m2a_capability_row_invalid")
        capability_id = str(capability.get("capability_id") or "")
        if not capability_id or capability_id in by_id:
            raise DownstreamConsumerCutoverError("m2a_capability_identity_invalid")
        for key in (
            "scene_family",
            "unit04_scene_ref_ids",
            "unit04_sentence_ids",
            "unit04_sentence_texts",
            "relation_surfaces",
        ):
            if not capability.get(key):
                raise DownstreamConsumerCutoverError(
                    f"m2a_fact_lineage_missing:{capability_id}:{key}"
                )
        by_id[capability_id] = capability

    expected_distribution = Counter(
        {"READING": 36, "LISTENING": 36, "SPEAKING": 36, "WRITING": 36}
    )
    if Counter(str(row.get("skill") or "") for row in tasks) != expected_distribution:
        raise DownstreamConsumerCutoverError("m2c_skill_distribution_invalid")
    if any(str(row.get("unit04_capability_id") or "") not in by_id for row in tasks):
        raise DownstreamConsumerCutoverError("m2c_capability_lineage_invalid")
    return by_id, tasks


def _relation_overlap(
    episode: dict[str, Any],
    capability: dict[str, Any],
) -> list[str]:
    episode_relations = set(_episode_relation_surfaces(episode))
    capability_relations = {
        str(value) for value in capability.get("relation_surfaces", []) if str(value)
    }
    return sorted(episode_relations.intersection(capability_relations))


def _candidate_pool(
    episodes: list[dict[str, Any]],
    episodes_by_family: dict[str, list[dict[str, Any]]],
    capability: dict[str, Any],
) -> tuple[list[dict[str, Any]], str, bool]:
    family = str(capability["scene_family"])
    family_rows = episodes_by_family.get(family, [])
    exact_family_relation_rows = [
        row for row in family_rows if _relation_overlap(row, capability)
    ]
    if exact_family_relation_rows:
        return (
            sorted(
                exact_family_relation_rows,
                key=lambda row: (-len(_relation_overlap(row, capability)), str(row["episode_id"])),
            ),
            "EXACT_GOVERNED_FAMILY_AND_VISIBLE_RELATION_SURFACE",
            True,
        )

    # Q07/M2-A uses a broader 17-family ontology than Current360's passage-world
    # family coverage. A missing exact family must not be repaired by inventing a
    # family equivalence. The only permitted fallback is a relation surface that is
    # actually visible in the Current360 passage, including approved support exposure
    # relations next to / in front of.
    relation_rows = [row for row in episodes if _relation_overlap(row, capability)]
    if not relation_rows:
        raise DownstreamConsumerCutoverError(
            f"current360_visible_relation_compatible_passage_missing:{capability['capability_id']}:{family}"
        )
    return (
        sorted(
            relation_rows,
            key=lambda row: (-len(_relation_overlap(row, capability)), str(row["episode_id"])),
        ),
        "VISIBLE_RELATION_SURFACE_FALLBACK_NO_FAMILY_EQUIVALENCE_CLAIM",
        False,
    )


def _select_current360_episode(
    episodes: list[dict[str, Any]],
    episodes_by_family: dict[str, list[dict[str, Any]]],
    capability: dict[str, Any],
    skill: str,
) -> tuple[dict[str, Any], str, bool]:
    pool, basis, exact_family = _candidate_pool(episodes, episodes_by_family, capability)
    seed = int(
        hashlib.sha256(str(capability["capability_id"]).encode("utf-8")).hexdigest()[:12],
        16,
    )
    index = (seed + SKILL_OFFSETS[skill]) % len(pool)
    return pool[index], basis, exact_family


def _lineage(
    episode: dict[str, Any],
    capability: dict[str, Any],
    alignment_basis: str,
    exact_family_match: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    overlap = _relation_overlap(episode, capability)
    if not overlap:
        raise DownstreamConsumerCutoverError(
            f"current360_visible_relation_overlap_missing:{capability['capability_id']}:{episode['episode_id']}"
        )
    current360 = {
        "episode_id": episode["episode_id"],
        "micro_scene_id": episode["micro_scene_id"],
        "life_domain": episode["life_domain"],
        "governed_scene_family": episode["governed_scene_family"],
        "discourse_family": episode["discourse_family"],
        "five_w_one_h": _split_csv(episode["five_w_one_h"]),
        "target_relations": _split_csv(episode["target_relations"]),
        "visible_relation_surfaces": _episode_relation_surfaces(episode),
        "support_language": _split_csv(episode.get("support_language")),
        "review_status": episode["review_status"],
        "source_fact_lineage": episode["source_fact_lineage"],
        "passage": episode["passage"],
    }
    q07_m2a = {
        "unit04_capability_id": capability["capability_id"],
        "scene_family": capability["scene_family"],
        "medium_setting": capability.get("medium_setting"),
        "unit04_scene_ref_ids": list(capability["unit04_scene_ref_ids"]),
        "unit04_sentence_ids": list(capability["unit04_sentence_ids"]),
        "unit04_sentence_texts": list(capability["unit04_sentence_texts"]),
        "relation_surfaces": [str(value) for value in capability["relation_surfaces"]],
    }
    alignment = {
        "basis": alignment_basis,
        "shared_visible_relation_surfaces": overlap,
        "exact_governed_scene_family_match": exact_family_match,
        "current360_governed_scene_family": episode["governed_scene_family"],
        "q07_m2a_scene_family": capability["scene_family"],
        "same_scene_claimed": False,
        "same_source_fact_claimed": False,
        "family_equivalence_claimed": False,
    }
    return current360, q07_m2a, alignment


def _cutover_task(
    upstream: dict[str, Any],
    capability: dict[str, Any],
    episode: dict[str, Any],
    alignment_basis: str,
    exact_family_match: bool,
) -> dict[str, Any]:
    skill = str(upstream["skill"])
    task = dict(upstream)
    boundary = dict(upstream.get("authority_boundary", {}))
    current360_lineage, q07_m2a_lineage, alignment = _lineage(
        episode, capability, alignment_basis, exact_family_match
    )
    task["upstream_response_authority"] = upstream.get("response_authority")
    task["upstream_assessment_operation"] = upstream.get("assessment_operation")
    task["response_authority"] = CURRENT360_AUTHORITY
    task["resource_mode"] = "CURRENT360_PASSAGE_AUTHORITY_WITH_INDEPENDENT_Q07_M2A_FACT_TRACE"
    if skill == "READING":
        task["assessment_operation"] = "EXTRACT_LOCATION_RELATION_FROM_CURRENT360_PASSAGE"
    elif skill == "SPEAKING":
        task["assessment_operation"] = (
            "LOCATION_QA_SCENE_DESCRIPTION_AND_TRANSFER_FROM_CURRENT360_PASSAGE"
        )
    elif skill == "WRITING":
        task["assessment_operation"] = "WRITE_SHORT_LOCATION_DESCRIPTION_FROM_CURRENT360_PASSAGE"
    else:
        raise DownstreamConsumerCutoverError(f"unexpected_rsw_skill:{skill}")
    task["current360_episode_lineage"] = current360_lineage
    task["q07_m2a_fact_lineage"] = q07_m2a_lineage
    task["lineage_alignment"] = alignment
    boundary["learner_language_authority"] = CURRENT360_AUTHORITY
    boundary["upstream_q07_m2a_fact_lineage_preserved"] = True
    boundary["current360_episode_lineage_preserved"] = True
    boundary["q07_m2a_and_current360_same_scene_claimed"] = False
    boundary["family_equivalence_claimed"] = False
    boundary["new_learner_facing_wording_authored"] = False
    boundary["a2_unlocked"] = False
    task["authority_boundary"] = boundary
    return task


def build_unit04_m2_capability_learner_facing_consumer_integration(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    current360_report = build_unit04_neb02_natural_episode_bank_360(root)
    episodes = _validate_current360(current360_report)
    m2a = build_unit04_raz_aw_multi_sentence_micro_scene_capability(root)
    m2c = build_unit04_ket_four_skill_task_assessment_projection(root)
    capability_by_id, upstream_tasks = _validate_upstream(m2a, m2c)

    episodes_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        episodes_by_family[str(episode["governed_scene_family"])].append(episode)
    for rows in episodes_by_family.values():
        rows.sort(key=lambda row: str(row["episode_id"]))

    downstream_tasks: list[dict[str, Any]] = []
    selected_episode_ids: set[str] = set()
    listening_upstream: list[dict[str, Any]] = []
    listening_downstream: list[dict[str, Any]] = []
    alignment_basis_counts: Counter[str] = Counter()
    fallback_families: set[str] = set()

    for upstream in upstream_tasks:
        skill = str(upstream["skill"])
        if skill == LISTENING_SKILL:
            task = dict(upstream)
            listening_upstream.append(upstream)
            listening_downstream.append(task)
        else:
            capability = capability_by_id[str(upstream["unit04_capability_id"])]
            episode, basis, exact_family = _select_current360_episode(
                episodes, episodes_by_family, capability, skill
            )
            task = _cutover_task(upstream, capability, episode, basis, exact_family)
            selected_episode_ids.add(str(episode["episode_id"]))
            alignment_basis_counts[basis] += 1
            if not exact_family:
                fallback_families.add(str(capability["scene_family"]))
        downstream_tasks.append(task)

    if listening_downstream != listening_upstream:
        raise DownstreamConsumerCutoverError("listening_task_projection_changed")
    if len(downstream_tasks) != 144:
        raise DownstreamConsumerCutoverError("downstream_task_projection_count_invalid")

    skill_counts = Counter(str(row["skill"]) for row in downstream_tasks)
    rsw_rows = [row for row in downstream_tasks if row["skill"] in RSW_SKILLS]
    listening_rows = [row for row in downstream_tasks if row["skill"] == LISTENING_SKILL]
    if len(rsw_rows) != 108 or len(listening_rows) != 36:
        raise DownstreamConsumerCutoverError("downstream_skill_cutover_count_invalid")
    if any(not row.get("current360_episode_lineage") for row in rsw_rows):
        raise DownstreamConsumerCutoverError("current360_episode_lineage_missing")
    if any(not row.get("q07_m2a_fact_lineage") for row in rsw_rows):
        raise DownstreamConsumerCutoverError("q07_m2a_fact_lineage_missing")
    if any(
        not row.get("lineage_alignment", {}).get("shared_visible_relation_surfaces")
        for row in rsw_rows
    ):
        raise DownstreamConsumerCutoverError("rsw_visible_relation_alignment_missing")
    if any(row.get("response_authority") != CURRENT360_AUTHORITY for row in rsw_rows):
        raise DownstreamConsumerCutoverError("rsw_current360_authority_cutover_incomplete")
    if any(
        row.get("response_authority") != UPSTREAM_Q07_M2A_AUTHORITY
        for row in listening_rows
    ):
        raise DownstreamConsumerCutoverError("listening_authority_drift")

    fallback_key = "VISIBLE_RELATION_SURFACE_FALLBACK_NO_FAMILY_EQUIVALENCE_CLAIM"
    fallback_task_count = alignment_basis_counts[fallback_key]
    return {
        "schema_version": "a1fs.v1.u04.neb.current360.downstream_consumer_cutover.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "source_refs": {
            "current360_passage_authority": CURRENT360_REF,
            "q07_fact_authority": Q07_REF,
            "m2a_fact_projection": M2A_REF,
            "m2c_four_skill_upstream": M2C_REF,
        },
        "scope": {
            "existing_consumer_path_reused": True,
            "parallel_consumer_created": False,
            "reading_current360_cutover": True,
            "speaking_current360_cutover": True,
            "writing_current360_cutover": True,
            "listening_keep": True,
            "current360_content_modified": False,
            "q07_modified": False,
            "m2a_fact_lineage_modified": False,
            "q10_modified": False,
            "a2_a2plus_unlocked": False,
        },
        "consumer_summary": {
            "upstream_task_projection_count": len(upstream_tasks),
            "downstream_task_projection_count": len(downstream_tasks),
            "skill_distribution": {
                skill: skill_counts[skill]
                for skill in ("READING", "LISTENING", "SPEAKING", "WRITING")
            },
            "current360_episode_bank_count": len(episodes),
            "current360_rsw_bound_task_count": len(rsw_rows),
            "current360_selected_distinct_episode_count": len(selected_episode_ids),
            "current360_unselected_reservoir_count": len(episodes) - len(selected_episode_ids),
            "current360_missing_binding_count": 0,
            "q07_m2a_fact_lineage_missing_count": 0,
            "rsw_visible_relation_alignment_missing_count": 0,
            "alignment_basis_counts": dict(alignment_basis_counts),
            "family_fallback_task_count": fallback_task_count,
            "family_fallback_families": sorted(fallback_families),
            "listening_keep_task_count": len(listening_rows),
            "listening_changed_task_count": 0,
        },
        "task_projections": downstream_tasks,
        "post_cutover_gap_recheck": {
            "rsw_current360_passage_authority_missing": 0,
            "rsw_current360_episode_lineage_missing": 0,
            "rsw_q07_m2a_fact_lineage_missing": 0,
            "rsw_visible_relation_surface_alignment_missing": 0,
            "family_ontology_exact_match_fallback_task_count": fallback_task_count,
            "family_ontology_exact_match_fallback_families": sorted(fallback_families),
            "listening_authority_changes": 0,
            "q10_changes": 0,
            "a2_a2plus_unlock_count": 0,
        },
        "safety": {
            "current360_episode_content_mutated": False,
            "q07_semantic_authority_mutated": False,
            "m2a_fact_lineage_mutated": False,
            "q10_mutated": False,
            "new_learner_facing_wording_authored": False,
            "listening_kept_on_q07_m2a": True,
            "reading_speaking_writing_use_current360": True,
            "current360_episode_lineage_preserved": True,
            "q07_m2a_fact_lineage_preserved": True,
            "q07_m2a_and_current360_same_scene_claimed": False,
            "family_equivalence_claimed": False,
            "a2_a2plus_unlocked": False,
        },
    }


def compact_readback(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report["status"],
        "revision": report["revision"],
        "consumer_summary": report["consumer_summary"],
        "post_cutover_gap_recheck": report["post_cutover_gap_recheck"],
        "scope": report["scope"],
    }
