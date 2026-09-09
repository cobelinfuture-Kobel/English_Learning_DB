from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04neb01_natural_episode_authority_cutover_108 as neb01


TASK_ID = "A1FS-V1-U04NEB01R1_StrictA1A1PlusGrammarVocabularyBoundaryAudit108"
STATUS = "PASS_A1FS_V1_U04NEB01R1_STRICT_A1A1PLUS_GRAMMAR_VOCABULARY_BOUNDARY_AUDIT_108"
REVISION = "GPT5_6_SOL_UNIT04_A1A1PLUS_BOUNDARY_R1"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Loads the merged NEB01 GPT-authored bank and a separately authored GPT-5.6 Sol "
    "boundary-rewrite overlay. Python only applies the fixed overlay and validates "
    "Unit04/A1/A1+ language-boundary invariants; it does not compose learner language."
)

OVERLAY_PATH = "product/a1fs_v1_2_1/u04neb01r1_strict_a1_boundary_overlay_108.tsv"
OVERLAY_HEADERS = ("episode_id", "boundary_action", "revised_passage")
EXPECTED_REWRITE_COUNT = 76

# These are deliberately not the whole English language. They encode only the
# constructions found in NEB01 that exceed the approved Unit04/A1/A1+ passage boundary.
BLOCKED_PATTERNS = {
    "A2_TIME_SUBORDINATOR_WHILE": r"\bwhile\b",
    "B1_TIME_SUBORDINATOR_UNTIL": r"\buntil\b",
    "A2_DEGREE_ADVERB_ALMOST": r"\balmost\b",
    "A2_TIME_ADVERB_ALREADY": r"\balready\b",
    "B1_NEARBY_ADVERB": r"\bnearby\b",
    "EMBEDDED_WH_WHERE_CLAUSE": r"\bwhere\b",
    "EMBEDDED_WH_INFINITIVE_WHAT_TO": r"\bwhat\s+to\b",
    "CONTENT_THAT_COMPLEMENT": r"\b(?:check|checks|remember|remembers|know|knows)\b[^.?!]{0,60}\bthat\b",
    "OUT_OF_SCOPE_DIRECTIONAL_INTO": r"\binto\b",
    "OUT_OF_SCOPE_DIRECTIONAL_FROM": r"\bfrom\b",
    "OUT_OF_SCOPE_ACROSS": r"\bacross\b",
    "B1_LOOK_AROUND": r"\blooks?\s+around\b",
    "UNNEEDED_NOTICE_VERB": r"\bnotices?\b",
    "UNNEEDED_PLACE_VERB": r"\bplaces?\b",
    "UNNEEDED_DECIDE_VERB": r"\bdecides?\b",
    "REDUCED_CLOSING_PARTICIPLE": r"\bclosing\b",
    "NON_TARGET_NOT_FAR_FROM": r"\bnot\s+far\s+from\b",
    "NOUN_TIME_TO_COMPLEMENT": r"\btime\s+to\b",
    "NOUN_PLACE_TO_COMPLEMENT": r"\bplace\s+to\b",
}

# Approved learner-visible support. These are not Unit04 teaching or assessment targets.
# "so/also/still" are retained only as low-complexity support language because the
# Natural Episode design explicitly classifies them as learner-visible support.
CONTROLLED_SUPPORT_SURFACES = (
    "and", "but", "or", "because", "so", "then", "also", "still", "first",
    "before", "after", "next to", "in front of",
)

# Proven higher-than-A1 lexical surfaces that remain because they carry concrete
# scene meaning. They are receptive/exposure lexis only, never promoted to Unit04 target.
KNOWN_SCENE_REQUIRED_LEXICAL_EXPOSURE = {
    "clinic": "B1",
    "statue": "B1",
    "trolley": "B2",
    "magazine": "A2",
    "puzzle": "A2",
}

TARGET_RELATIONS = neb01.TARGET_RELATIONS


class StrictBoundaryAuditError(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _normalized_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _sentence_count(passage: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?])\s+", passage.strip()) if part.strip()])


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _load_overlay(root: Path) -> dict[str, dict[str, str]]:
    path = root / OVERLAY_PATH
    if not path.is_file():
        raise StrictBoundaryAuditError("strict_a1_boundary_overlay_missing")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != OVERLAY_HEADERS:
            raise StrictBoundaryAuditError("strict_a1_boundary_overlay_header_drift")
        rows = [dict(row) for row in reader]

    if len(rows) != EXPECTED_REWRITE_COUNT:
        raise StrictBoundaryAuditError(f"strict_a1_boundary_rewrite_count_invalid:{len(rows)}")

    overlay: dict[str, dict[str, str]] = {}
    for row in rows:
        episode_id = row["episode_id"]
        if episode_id in overlay:
            raise StrictBoundaryAuditError(f"duplicate_overlay_episode_id:{episode_id}")
        if row["boundary_action"] != "REWRITE_TO_UNIT04_A1A1PLUS_BOUNDARY":
            raise StrictBoundaryAuditError(f"overlay_action_invalid:{episode_id}")
        if not row["revised_passage"].strip():
            raise StrictBoundaryAuditError(f"overlay_passage_empty:{episode_id}")
        overlay[episode_id] = row
    return overlay


def _effective_rows(root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    base_rows = neb01._load_bank(root)
    overlay = _load_overlay(root)
    base_ids = {row["episode_id"] for row in base_rows}
    if not set(overlay).issubset(base_ids):
        raise StrictBoundaryAuditError(
            f"overlay_unknown_episode_ids:{sorted(set(overlay) - base_ids)}"
        )

    effective: list[dict[str, Any]] = []
    for base in base_rows:
        row = dict(base)
        patch = overlay.get(row["episode_id"])
        if patch is not None:
            row["passage"] = patch["revised_passage"].strip()
            row["boundary_action"] = patch["boundary_action"]
        else:
            row["boundary_action"] = "KEEP_SEMANTICALLY_APPROVED_BASE_PASSAGE"
        effective.append(row)
    return effective, overlay


def _validate_effective_rows(
    rows: list[dict[str, Any]],
    overlay: dict[str, dict[str, str]],
) -> dict[str, Any]:
    if len(rows) != 108:
        raise StrictBoundaryAuditError(f"effective_episode_count_invalid:{len(rows)}")

    exact: set[str] = set()
    normalized: set[str] = set()
    blocked_hits: dict[str, list[str]] = {}
    support_counts: Counter[str] = Counter()
    exposure_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()

    for row in rows:
        episode_id = row["episode_id"]
        passage = row["passage"].strip()

        count = _sentence_count(passage)
        if count < 2 or count > 5:
            raise StrictBoundaryAuditError(
                f"effective_sentence_count_out_of_range:{episode_id}:{count}"
            )

        if passage in exact:
            raise StrictBoundaryAuditError(f"effective_exact_duplicate:{episode_id}")
        exact.add(passage)
        norm = _normalized_text(passage)
        if norm in normalized:
            raise StrictBoundaryAuditError(f"effective_normalized_duplicate:{episode_id}")
        normalized.add(norm)

        for pattern_id, pattern in BLOCKED_PATTERNS.items():
            if re.search(pattern, passage, flags=re.I):
                blocked_hits.setdefault(pattern_id, []).append(episode_id)

        # Preserve declared relation metadata unchanged, while matching NEB01 passage semantics:
        # each effective passage must expose at least one Unit04 spatial relation.
        declared = [part.strip() for part in row["target_relations"].split(",") if part.strip()]
        if not declared or not set(declared).issubset(TARGET_RELATIONS):
            raise StrictBoundaryAuditError(
                f"declared_target_relation_drift:{episode_id}:{declared}"
            )

        passage_relations = [
            relation for relation in TARGET_RELATIONS if _contains_surface(passage, relation)
        ]
        if not passage_relations:
            raise StrictBoundaryAuditError(
                f"no_unit04_spatial_relation_in_effective_passage:{episode_id}"
            )
        relation_counts.update(passage_relations)

        for surface in CONTROLLED_SUPPORT_SURFACES:
            if _contains_surface(passage, surface):
                support_counts[surface] += 1

        for surface, level in KNOWN_SCENE_REQUIRED_LEXICAL_EXPOSURE.items():
            if _contains_surface(passage, surface) or _contains_surface(passage, f"{surface}s"):
                exposure_counts[f"{surface}:{level}"] += 1

    if blocked_hits:
        raise StrictBoundaryAuditError(
            "blocked_language_boundary_hits:"
            + json.dumps(blocked_hits, ensure_ascii=False, sort_keys=True)
        )

    if set(relation_counts) != set(TARGET_RELATIONS):
        raise StrictBoundaryAuditError(
            f"unit04_target_relation_coverage_drift:{dict(relation_counts)}"
        )

    changed_ids = [row["episode_id"] for row in rows if row["episode_id"] in overlay]
    unchanged_ids = [row["episode_id"] for row in rows if row["episode_id"] not in overlay]

    return {
        "effective_episode_count": 108,
        "rewritten_episode_count": len(changed_ids),
        "unchanged_episode_count": len(unchanged_ids),
        "rewritten_episode_ids": changed_ids,
        "blocked_pattern_count": 0,
        "exact_duplicate_count": 0,
        "normalized_duplicate_count": 0,
        "unit04_target_relation_distribution": dict(relation_counts),
        "controlled_support_distribution": dict(support_counts),
        "known_scene_required_lexical_exposure_distribution": dict(exposure_counts),
    }


def build_unit04_neb01r1_strict_a1_boundary_audit_108(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    root = _root(repo_root)
    base_report = neb01.build_unit04_natural_episode_authority_cutover_108(root)
    if base_report.get("status") != neb01.STATUS:
        raise StrictBoundaryAuditError("neb01_base_status_drift")

    rows, overlay = _effective_rows(root)
    summary = _validate_effective_rows(rows, overlay)

    # Base-row metadata is copied, not regenerated. Q03/Q07/Q10/canonical authority stay unchanged.
    base_identity = {
        row["episode_id"]: {
            "micro_scene_id": row["micro_scene_id"],
            "life_domain": row["life_domain"],
            "governed_scene_family": row["governed_scene_family"],
            "discourse_family": row["discourse_family"],
            "five_w_one_h": row["five_w_one_h"],
            "target_relations": row["target_relations"],
            "source_fact_lineage": row["source_fact_lineage"],
        }
        for row in neb01._load_bank(root)
    }
    for row in rows:
        now = {
            "micro_scene_id": row["micro_scene_id"],
            "life_domain": row["life_domain"],
            "governed_scene_family": row["governed_scene_family"],
            "discourse_family": row["discourse_family"],
            "five_w_one_h": row["five_w_one_h"],
            "target_relations": row["target_relations"],
            "source_fact_lineage": row["source_fact_lineage"],
        }
        if now != base_identity[row["episode_id"]]:
            raise StrictBoundaryAuditError(f"semantic_lineage_metadata_mutated:{row['episode_id']}")

    effective_payload = [
        {
            "episode_id": row["episode_id"],
            "micro_scene_id": row["micro_scene_id"],
            "life_domain": row["life_domain"],
            "discourse_family": row["discourse_family"],
            "target_relations": row["target_relations"],
            "source_fact_lineage": row["source_fact_lineage"],
            "boundary_action": row["boundary_action"],
            "passage": row["passage"],
        }
        for row in rows
    ]
    projection_sha256 = hashlib.sha256(
        json.dumps(
            effective_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": "a1fs.v1.u04.neb01r1.strict_a1_a1plus_boundary_audit_108.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "base_neb01_status": base_report["status"],
        "language_boundary_contract": {
            "teaching_target": "UNIT04_PLACE_SPATIAL_RELATIONS_ONLY",
            "productive_grammar_ceiling": "A1_A1PLUS",
            "basic_connectors_allowed": True,
            "controlled_support_is_teaching_target": False,
            "controlled_support_is_assessment_target": False,
            "a2_grammar_productive_use_allowed": False,
            "b1_plus_grammar_allowed": False,
            "scene_required_higher_lexis_policy": "RECEPTIVE_EXPOSURE_ONLY_NO_CANONICAL_PROMOTION",
            "python_sentence_composer_used": False,
            "gpt_authored_rewrite_overlay_used": True,
        },
        "summary": summary,
        "effective_episodes": effective_payload,
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
        "projection_sha256": projection_sha256,
    }
