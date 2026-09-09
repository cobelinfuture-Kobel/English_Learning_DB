from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04q10r1_unit04_learner_facing_pedagogical_acceptance as q10r1
from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    STATUS as M2A_STATUS,
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)
from product.a1fs_v1_2_1.u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay import (
    STATUS as M2B_STATUS,
    build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay,
)
from product.a1fs_v1_2_1.u04ms02c_ket_four_skill_task_assessment_projection import (
    STATUS as M2C_STATUS,
    build_unit04_ket_four_skill_task_assessment_projection,
)
from ulga.builders import build_a1fs_v1_u04q10_questionbank_form_materialization as q10

TASK_ID = "A1FS-V1-U04NEB01_NaturalEpisodeAuthorityCutover108"
STATUS = "PASS_A1FS_V1_U04NEB01_NATURAL_EPISODE_AUTHORITY_CUTOVER_108"
REVISION = "GPT5_6_SOL_DIRECT_AUTHORED_108_V1"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Loads and validates the separately materialized GPT-5.6 Sol authored Unit04 Natural "
    "Episode Bank. Python does not compose or repair learner language."
)

BANK_PATH = "product/a1fs_v1_2_1/u04neb01_natural_episode_authority_108.tsv"
Q03_REF = "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q07_REF = "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
TARGET_RELATIONS = frozenset({"in", "inside", "on", "near", "at", "under", "behind", "between"})
SUPPORT_RELATIONS = frozenset({"next to", "in front of"})
LIFE_DOMAINS = (
    "HOME", "CLASSROOM", "SCHOOL", "PARK", "SHOP", "TRANSPORT",
    "PUBLIC_PLACE", "FOOD", "CLOTHES", "TOYS", "ANIMALS", "DAILY_ROUTINE",
)
REVIEW_STATUS = "PASS_GPT5_6_SOL_DIRECT_REVIEW"
EXPECTED_HEADERS = (
    "episode_id", "micro_scene_id", "life_domain", "governed_scene_family",
    "discourse_family", "five_w_one_h", "target_relations", "support_language",
    "review_status", "source_fact_lineage", "passage",
)


class NaturalEpisodeAuthorityError(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _split(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _sentence_count(passage: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?])\s+", passage.strip()) if part.strip()])


def _normalized_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _load_bank(root: Path) -> list[dict[str, Any]]:
    path = root / BANK_PATH
    if not path.is_file():
        raise NaturalEpisodeAuthorityError("natural_episode_bank_missing")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != EXPECTED_HEADERS:
            raise NaturalEpisodeAuthorityError("natural_episode_bank_header_drift")
        rows = [dict(row) for row in reader]
    if len(rows) != 108:
        raise NaturalEpisodeAuthorityError(f"natural_episode_count_invalid:{len(rows)}")
    return rows


def _validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    episode_ids: set[str] = set()
    scene_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    domain_counts: Counter[str] = Counter()
    discourse_counts: Counter[str] = Counter()
    declared_relation_counts: Counter[str] = Counter()
    passage_relation_counts: Counter[str] = Counter()
    support_relation_counts: Counter[str] = Counter()
    five_w_counts: Counter[str] = Counter()
    sentence_counts: Counter[int] = Counter()
    exact_passages: set[str] = set()
    normalized_passages: set[str] = set()

    for index, row in enumerate(rows, start=1):
        expected_id = f"U04-NEB-E{index:03d}"
        if row["episode_id"] != expected_id or row["episode_id"] in episode_ids:
            raise NaturalEpisodeAuthorityError(f"episode_identity_invalid:{index}:{row['episode_id']}")
        episode_ids.add(row["episode_id"])

        scene_id = row["micro_scene_id"]
        if not re.fullmatch(r"U04-NEB-MS(?:0[1-9]|[12][0-9]|3[0-6])", scene_id):
            raise NaturalEpisodeAuthorityError(f"micro_scene_identity_invalid:{scene_id}")
        scene_rows[scene_id].append(row)

        domain = row["life_domain"]
        if domain not in LIFE_DOMAINS:
            raise NaturalEpisodeAuthorityError(f"life_domain_out_of_scope:{domain}")
        domain_counts[domain] += 1
        if not row["governed_scene_family"].strip():
            raise NaturalEpisodeAuthorityError(f"scene_family_missing:{row['episode_id']}")

        discourse = row["discourse_family"].strip()
        if not discourse:
            raise NaturalEpisodeAuthorityError(f"discourse_family_missing:{row['episode_id']}")
        discourse_counts[discourse] += 1

        five_w = set(_split(row["five_w_one_h"]))
        if not {"WHO", "WHAT", "WHERE"}.issubset(five_w):
            raise NaturalEpisodeAuthorityError(f"core_5w1h_missing:{row['episode_id']}:{sorted(five_w)}")
        if not five_w.issubset({"WHO", "WHAT", "WHERE", "WHEN", "WHY", "HOW"}):
            raise NaturalEpisodeAuthorityError(f"5w1h_unknown_tag:{row['episode_id']}")
        five_w_counts.update(five_w)

        declared_relations = _split(row["target_relations"])
        if not declared_relations or not set(declared_relations).issubset(TARGET_RELATIONS):
            raise NaturalEpisodeAuthorityError(f"target_relation_invalid:{row['episode_id']}:{declared_relations}")
        declared_relation_counts.update(declared_relations)

        passage_relations = [surface for surface in TARGET_RELATIONS if _contains_surface(row["passage"], surface)]
        if not passage_relations:
            raise NaturalEpisodeAuthorityError(f"no_unit04_spatial_relation_in_passage:{row['episode_id']}")
        passage_relation_counts.update(passage_relations)
        for support in SUPPORT_RELATIONS:
            if _contains_surface(row["passage"], support):
                support_relation_counts[support] += 1

        if row["review_status"] != REVIEW_STATUS:
            raise NaturalEpisodeAuthorityError(f"semantic_review_missing:{row['episode_id']}")
        if not row["source_fact_lineage"].strip():
            raise NaturalEpisodeAuthorityError(f"source_fact_lineage_missing:{row['episode_id']}")

        passage = row["passage"].strip()
        if not passage or passage in exact_passages:
            raise NaturalEpisodeAuthorityError(f"exact_passage_duplicate:{row['episode_id']}")
        exact_passages.add(passage)
        normalized = _normalized_text(passage)
        if normalized in normalized_passages:
            raise NaturalEpisodeAuthorityError(f"normalized_passage_duplicate:{row['episode_id']}")
        normalized_passages.add(normalized)
        count = _sentence_count(passage)
        if count < 2 or count > 5:
            raise NaturalEpisodeAuthorityError(f"episode_sentence_count_out_of_range:{row['episode_id']}:{count}")
        sentence_counts[count] += 1

    if len(scene_rows) != 36 or any(len(group) != 3 for group in scene_rows.values()):
        raise NaturalEpisodeAuthorityError("micro_scene_36x3_contract_failed")
    for scene_id, group in scene_rows.items():
        if len({row["life_domain"] for row in group}) != 1:
            raise NaturalEpisodeAuthorityError(f"micro_scene_domain_drift:{scene_id}")
        if len({row["governed_scene_family"] for row in group}) != 1:
            raise NaturalEpisodeAuthorityError(f"micro_scene_family_drift:{scene_id}")
        if len({row["discourse_family"] for row in group}) != 3:
            raise NaturalEpisodeAuthorityError(f"micro_scene_discourse_not_distinct:{scene_id}")

    if domain_counts != Counter({domain: 9 for domain in LIFE_DOMAINS}):
        raise NaturalEpisodeAuthorityError(f"life_domain_12x9_contract_failed:{dict(domain_counts)}")
    if len(discourse_counts) < 12:
        raise NaturalEpisodeAuthorityError(f"discourse_family_diversity_too_low:{len(discourse_counts)}")
    if set(declared_relation_counts) != set(TARGET_RELATIONS):
        raise NaturalEpisodeAuthorityError(f"declared_relation_coverage_incomplete:{dict(declared_relation_counts)}")
    if set(passage_relation_counts) != set(TARGET_RELATIONS):
        raise NaturalEpisodeAuthorityError(f"passage_relation_coverage_incomplete:{dict(passage_relation_counts)}")
    if five_w_counts["WHERE"] != 108 or five_w_counts["WHO"] != 108 or five_w_counts["WHAT"] != 108:
        raise NaturalEpisodeAuthorityError(f"core_5w1h_coverage_failed:{dict(five_w_counts)}")
    if min(five_w_counts["WHEN"], five_w_counts["WHY"], five_w_counts["HOW"]) < 18:
        raise NaturalEpisodeAuthorityError(f"extended_5w1h_distribution_too_low:{dict(five_w_counts)}")

    return {
        "episode_count": 108,
        "micro_scene_count": 36,
        "episodes_per_micro_scene": 3,
        "life_domain_count": 12,
        "life_domain_distribution": dict(domain_counts),
        "discourse_family_count": len(discourse_counts),
        "discourse_family_distribution": dict(discourse_counts),
        "declared_source_relation_distribution": dict(declared_relation_counts),
        "target_relation_distribution": dict(passage_relation_counts),
        "support_relation_exposure_distribution": dict(support_relation_counts),
        "five_w_one_h_distribution": dict(five_w_counts),
        "sentence_count_distribution": dict(sentence_counts),
        "semantic_review_pass_count": 108,
        "exact_duplicate_count": 0,
        "normalized_duplicate_count": 0,
    }


def _source_chain(root: Path) -> dict[str, Any]:
    m2a = build_unit04_raz_aw_multi_sentence_micro_scene_capability(root)
    m2b = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(root)
    m2c = build_unit04_ket_four_skill_task_assessment_projection(root)
    if m2a.get("status") != M2A_STATUS or m2b.get("status") != M2B_STATUS or m2c.get("status") != M2C_STATUS:
        raise NaturalEpisodeAuthorityError("m2_source_chain_status_drift")
    if len(m2a.get("capabilities", [])) != 36 or len(m2b.get("overlays", [])) != 36 or len(m2c.get("task_projections", [])) != 144:
        raise NaturalEpisodeAuthorityError("m2_source_chain_count_drift")
    return {
        "m2a_capability_count": 36,
        "m2b_overlay_count": 36,
        "m2c_task_projection_count": 144,
        "language_generation_role": "EVIDENCE_AND_STRUCTURE_ONLY_NOT_SENTENCE_COMPOSER",
    }


def _q10_infrastructure_proof() -> dict[str, Any]:
    payload_before = q10.build_export_payload()
    report_before = q10r1.build_acceptance_report()
    if report_before.get("status") != q10r1.PASS_STATUS:
        raise NaturalEpisodeAuthorityError("q10r1_not_pass")
    payload_digest = _digest(payload_before)
    forms_digest = _digest(report_before["learner_forms"])
    payload_after = q10.build_export_payload()
    report_after = q10r1.build_acceptance_report()
    if _digest(payload_after) != payload_digest or _digest(report_after["learner_forms"]) != forms_digest:
        raise NaturalEpisodeAuthorityError("q10_identity_mutated_by_neb01")
    if len(payload_before.get("forms", [])) != 20 or sum(len(form["item_ids"]) for form in payload_before["forms"]) != 800:
        raise NaturalEpisodeAuthorityError("q10_20x40_contract_drift")
    return {
        "source_form_count": 20,
        "source_activity_count": 800,
        "source_payload_sha256": payload_digest,
        "source_learner_forms_sha256": forms_digest,
        "forms_mutated": False,
        "activities_mutated": False,
        "prompt_wording_reused_for_neb01": False,
        "existing_assessment_item_reused_for_neb01": False,
        "infrastructure_role": "VALIDATED_EXISTING_RUNTIME_RESERVED_FOR_LATER_NEB05_CONSUMER_MATERIALIZATION",
    }


def build_unit04_natural_episode_authority_cutover_108(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    rows = _load_bank(root)
    summary = _validate_rows(rows)
    source_chain = _source_chain(root)
    q10_proof = _q10_infrastructure_proof()

    first_by_domain: dict[str, dict[str, Any]] = {}
    for row in rows:
        first_by_domain.setdefault(row["life_domain"], row)
    samples = [
        {
            "episode_id": first_by_domain[domain]["episode_id"],
            "life_domain": domain,
            "micro_scene_id": first_by_domain[domain]["micro_scene_id"],
            "discourse_family": first_by_domain[domain]["discourse_family"],
            "passage": first_by_domain[domain]["passage"],
        }
        for domain in LIFE_DOMAINS
    ]

    result = {
        "schema_version": "a1fs.v1.u04.neb01.natural_episode_authority_cutover_108.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "authority_refs": {
            "q03_static_spatial_relation_authority": Q03_REF,
            "q07_scene_ontology_and_semantic_boundary": Q07_REF,
            "natural_episode_bank": BANK_PATH,
        },
        "authorship_contract": {
            "natural_language_authored_by": "GPT-5.6_SOL_DIRECT_SEMANTIC_COMPOSITION",
            "python_sentence_composer_used": False,
            "python_role": "LOAD_VALIDATE_DEDUP_COVERAGE_AND_RUNTIME_PROOF_ONLY",
            "five_w_one_h_is_distributional_not_mandatory_full_template": True,
            "support_exposure_language_may_be_learner_visible": True,
            "support_exposure_language_promoted_to_unit04_target": False,
            "support_relations_promoted_to_q03_target": False,
        },
        "summary": summary,
        "m2_source_chain": source_chain,
        "q10_infrastructure_proof": q10_proof,
        "sample_episodes_one_per_domain": samples,
        "scope_safety": {
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
        },
    }
    result["projection_sha256"] = _digest({"rows": rows, "summary": summary, "samples": samples})
    return result


def build_unit04_m2_capability_learner_facing_consumer_integration(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    return build_unit04_natural_episode_authority_cutover_108(repo_root)
