from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04neb01_natural_episode_authority_cutover_108 as neb01
from product.a1fs_v1_2_1 import u04neb01r1_strict_a1_boundary_audit_108 as r1


TASK_ID = "A1FS-V1-U04NEB02_NaturalEpisodeBank360"
STATUS = "PASS_A1FS_V1_U04NEB02_NATURAL_EPISODE_BANK_360"
REVISION = "GPT5_6_SOL_M2_CURRENT360_OPERATOR_REPAIRED_V1"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Consumes the merged GPT-5.6-authored effective NEB01R1 108 bank plus a fixed "
    "GPT-5.6-authored 252-episode extension. Python only loads, joins, validates, "
    "deduplicates, measures diversity, and reports coverage; it does not compose "
    "or repair learner-facing English."
)

EXTENSION_PATH = "product/a1fs_v1_2_1/u04neb02_natural_episode_extension_252.tsv.gz"
EXTENSION_HEADERS = (
    "episode_id",
    "micro_scene_id",
    "life_domain",
    "governed_scene_family",
    "discourse_family",
    "five_w_one_h",
    "target_relations",
    "support_language",
    "review_status",
    "source_fact_lineage",
    "passage",
)
EXPECTED_EXTENSION_COUNT = 252
EXPECTED_TOTAL_COUNT = 360
EXPECTED_SCENE_COUNT = 36
EXPECTED_EPISODES_PER_SCENE = 10
EXPECTED_DOMAIN_COUNT = 12
EXPECTED_EPISODES_PER_DOMAIN = 30
EXPECTED_EXTENSION_SHA256 = "764405f8b567087fec56984233d79e5581395152f776323f8f8255f668df10d7"

OPERATOR_APPROVED_REPAIR_IDS = frozenset(
    {
        "U04-NEB-E137", "U04-NEB-E151", "U04-NEB-E160", "U04-NEB-E162",
        "U04-NEB-E172", "U04-NEB-E183", "U04-NEB-E186", "U04-NEB-E191",
        "U04-NEB-E197", "U04-NEB-E204", "U04-NEB-E211", "U04-NEB-E214",
        "U04-NEB-E218", "U04-NEB-E225", "U04-NEB-E232", "U04-NEB-E239",
        "U04-NEB-E242", "U04-NEB-E246", "U04-NEB-E248", "U04-NEB-E249",
        "U04-NEB-E253", "U04-NEB-E254", "U04-NEB-E255", "U04-NEB-E260",
        "U04-NEB-E263", "U04-NEB-E267", "U04-NEB-E270", "U04-NEB-E274",
        "U04-NEB-E281", "U04-NEB-E288", "U04-NEB-E291", "U04-NEB-E295",
        "U04-NEB-E298", "U04-NEB-E302", "U04-NEB-E309", "U04-NEB-E319",
        "U04-NEB-E323", "U04-NEB-E330", "U04-NEB-E335", "U04-NEB-E337",
        "U04-NEB-E339", "U04-NEB-E351", "U04-NEB-E358",
    }
)

TARGET_RELATIONS = r1.TARGET_RELATIONS
BLOCKED_PATTERNS = r1.BLOCKED_PATTERNS


class NaturalEpisodeBank360Error(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _normalized_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _sentence_count(passage: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?])\s+", passage.strip()) if part.strip()])


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _episode_number(episode_id: str) -> int:
    match = re.fullmatch(r"U04-NEB-E(\d{3})", episode_id)
    if not match:
        raise NaturalEpisodeBank360Error(f"invalid_episode_id:{episode_id}")
    return int(match.group(1))


def _scene_number(scene_id: str) -> int:
    match = re.fullmatch(r"U04-NEB-MS(\d{2})", scene_id)
    if not match:
        raise NaturalEpisodeBank360Error(f"invalid_micro_scene_id:{scene_id}")
    return int(match.group(1))


def _load_extension(root: Path) -> tuple[list[dict[str, str]], str]:
    path = root / EXTENSION_PATH
    if not path.is_file():
        raise NaturalEpisodeBank360Error("u04neb02_extension_missing")

    with gzip.open(path, "rb") as raw_handle:
        decompressed = raw_handle.read()
    digest = hashlib.sha256(decompressed).hexdigest()
    if digest != EXPECTED_EXTENSION_SHA256:
        raise NaturalEpisodeBank360Error(f"u04neb02_extension_sha256_drift:{digest}")

    text = decompressed.decode("utf-8")
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    if tuple(reader.fieldnames or ()) != EXTENSION_HEADERS:
        raise NaturalEpisodeBank360Error("u04neb02_extension_header_drift")
    rows = [dict(row) for row in reader]

    if len(rows) != EXPECTED_EXTENSION_COUNT:
        raise NaturalEpisodeBank360Error(f"u04neb02_extension_count_invalid:{len(rows)}")

    ids = [row["episode_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise NaturalEpisodeBank360Error("u04neb02_extension_duplicate_episode_id")
    if sorted(_episode_number(value) for value in ids) != list(range(109, 361)):
        raise NaturalEpisodeBank360Error("u04neb02_extension_episode_id_range_drift")

    scene_counts = Counter(row["micro_scene_id"] for row in rows)
    if len(scene_counts) != EXPECTED_SCENE_COUNT:
        raise NaturalEpisodeBank360Error(f"u04neb02_extension_scene_count_invalid:{len(scene_counts)}")
    if set(_scene_number(value) for value in scene_counts) != set(range(1, 37)):
        raise NaturalEpisodeBank360Error("u04neb02_extension_scene_identity_drift")
    if set(scene_counts.values()) != {7}:
        raise NaturalEpisodeBank360Error(f"u04neb02_extension_per_scene_count_drift:{dict(scene_counts)}")

    repaired = {
        row["episode_id"]
        for row in rows
        if row["review_status"] == "PASS_GPT5_6_SOL_M2_OPERATOR_APPROVED_REPAIR"
    }
    if repaired != OPERATOR_APPROVED_REPAIR_IDS:
        raise NaturalEpisodeBank360Error(
            "u04neb02_operator_repair_identity_drift:"
            + json.dumps(sorted(repaired), ensure_ascii=False)
        )

    for row in rows:
        for field in (
            "life_domain",
            "governed_scene_family",
            "discourse_family",
            "five_w_one_h",
            "source_fact_lineage",
            "passage",
        ):
            if not row[field].strip():
                raise NaturalEpisodeBank360Error(f"{field}_missing:{row['episode_id']}")

    return rows, digest


def _load_effective_base_rows(root: Path, r1_report: dict[str, Any]) -> list[dict[str, Any]]:
    canonical_rows = [dict(row) for row in neb01._load_bank(root)]
    effective_projection = {
        str(row["episode_id"]): dict(row)
        for row in r1_report["effective_episodes"]
    }

    if len(canonical_rows) != 108 or len(effective_projection) != 108:
        raise NaturalEpisodeBank360Error("effective_base_count_invalid")

    base_rows: list[dict[str, Any]] = []
    for canonical in canonical_rows:
        episode_id = str(canonical["episode_id"])
        effective = effective_projection.get(episode_id)
        if effective is None:
            raise NaturalEpisodeBank360Error(f"effective_base_episode_missing:{episode_id}")

        for field in (
            "micro_scene_id",
            "life_domain",
            "discourse_family",
            "target_relations",
            "source_fact_lineage",
        ):
            if str(effective[field]) != str(canonical[field]):
                raise NaturalEpisodeBank360Error(
                    f"effective_base_metadata_drift:{episode_id}:{field}"
                )

        row = dict(canonical)
        row["passage"] = str(effective["passage"])
        row["boundary_action"] = str(effective.get("boundary_action", ""))
        base_rows.append(row)

    return base_rows


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.casefold())


def _tfidf_pairs(rows: list[dict[str, Any]], threshold: float = 0.80) -> list[dict[str, Any]]:
    docs = [_tokenize(str(row["passage"])) for row in rows]
    n_docs = len(docs)
    document_frequency: Counter[str] = Counter()
    for tokens in docs:
        document_frequency.update(set(tokens))

    idf = {
        term: math.log((1.0 + n_docs) / (1.0 + document_frequency[term])) + 1.0
        for term in document_frequency
    }

    vectors: list[dict[str, float]] = []
    norms: list[float] = []
    for tokens in docs:
        counts = Counter(tokens)
        vector = {term: count * idf[term] for term, count in counts.items()}
        vectors.append(vector)
        norms.append(math.sqrt(sum(value * value for value in vector.values())))

    pairs: list[dict[str, Any]] = []
    for left in range(n_docs):
        for right in range(left + 1, n_docs):
            a = vectors[left]
            b = vectors[right]
            if len(a) > len(b):
                a, b = b, a
            dot = sum(value * b.get(term, 0.0) for term, value in a.items())
            denom = norms[left] * norms[right]
            similarity = dot / denom if denom else 0.0
            if similarity >= threshold:
                pairs.append(
                    {
                        "left_episode_id": rows[left]["episode_id"],
                        "right_episode_id": rows[right]["episode_id"],
                        "left_scene_id": rows[left]["micro_scene_id"],
                        "right_scene_id": rows[right]["micro_scene_id"],
                        "similarity": round(similarity, 6),
                    }
                )
    return pairs


def _validate_combined(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != EXPECTED_TOTAL_COUNT:
        raise NaturalEpisodeBank360Error(f"combined_episode_count_invalid:{len(rows)}")

    ids = [str(row["episode_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise NaturalEpisodeBank360Error("combined_duplicate_episode_id")
    if sorted(_episode_number(value) for value in ids) != list(range(1, 361)):
        raise NaturalEpisodeBank360Error("combined_episode_identity_range_drift")

    exact_seen: set[str] = set()
    normalized_seen: set[str] = set()
    relation_counts: Counter[str] = Counter()
    scene_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    discourse_by_scene: dict[str, set[str]] = defaultdict(set)
    five_w_one_h_counts: Counter[str] = Counter()
    sentence_counts: Counter[int] = Counter()
    blocked_hits: dict[str, list[str]] = {}

    for row in rows:
        episode_id = str(row["episode_id"])
        passage = str(row["passage"]).strip()

        sentence_count = _sentence_count(passage)
        if sentence_count < 2 or sentence_count > 5:
            raise NaturalEpisodeBank360Error(
                f"sentence_count_out_of_range:{episode_id}:{sentence_count}"
            )
        sentence_counts[sentence_count] += 1

        if passage in exact_seen:
            raise NaturalEpisodeBank360Error(f"exact_passage_duplicate:{episode_id}")
        exact_seen.add(passage)

        normalized = _normalized_text(passage)
        if normalized in normalized_seen:
            raise NaturalEpisodeBank360Error(f"normalized_passage_duplicate:{episode_id}")
        normalized_seen.add(normalized)

        for pattern_id, pattern in BLOCKED_PATTERNS.items():
            if re.search(pattern, passage, flags=re.I):
                blocked_hits.setdefault(pattern_id, []).append(episode_id)

        declared = [part.strip() for part in str(row["target_relations"]).split(",") if part.strip()]
        if not declared or not set(declared).issubset(TARGET_RELATIONS):
            raise NaturalEpisodeBank360Error(
                f"declared_target_relation_drift:{episode_id}:{declared}"
            )

        passage_relations = [
            relation for relation in TARGET_RELATIONS if _contains_surface(passage, relation)
        ]
        if not passage_relations:
            raise NaturalEpisodeBank360Error(
                f"no_unit04_spatial_relation_in_passage:{episode_id}"
            )
        relation_counts.update(passage_relations)

        scene_id = str(row["micro_scene_id"])
        scene_counts[scene_id] += 1
        domain_counts[str(row["life_domain"])] += 1
        discourse_by_scene[scene_id].add(str(row["discourse_family"]))

        for tag in [part.strip() for part in str(row["five_w_one_h"]).split(",") if part.strip()]:
            five_w_one_h_counts[tag] += 1

    if blocked_hits:
        raise NaturalEpisodeBank360Error(
            "blocked_language_boundary_hits:"
            + json.dumps(blocked_hits, ensure_ascii=False, sort_keys=True)
        )

    if set(relation_counts) != set(TARGET_RELATIONS):
        raise NaturalEpisodeBank360Error(
            f"target_relation_bank_coverage_drift:{dict(relation_counts)}"
        )

    if len(scene_counts) != EXPECTED_SCENE_COUNT or set(scene_counts.values()) != {EXPECTED_EPISODES_PER_SCENE}:
        raise NaturalEpisodeBank360Error(f"scene_distribution_drift:{dict(scene_counts)}")

    if len(domain_counts) != EXPECTED_DOMAIN_COUNT or set(domain_counts.values()) != {EXPECTED_EPISODES_PER_DOMAIN}:
        raise NaturalEpisodeBank360Error(f"domain_distribution_drift:{dict(domain_counts)}")

    bad_discourse = {
        scene_id: len(values)
        for scene_id, values in discourse_by_scene.items()
        if len(values) != EXPECTED_EPISODES_PER_SCENE
    }
    if bad_discourse:
        raise NaturalEpisodeBank360Error(
            "per_scene_raw_discourse_diversity_drift:"
            + json.dumps(bad_discourse, sort_keys=True)
        )

    near_pairs = _tfidf_pairs(rows, threshold=0.80)
    cross_scene_near_pairs = [
        pair for pair in near_pairs if pair["left_scene_id"] != pair["right_scene_id"]
    ]
    if cross_scene_near_pairs:
        raise NaturalEpisodeBank360Error(
            "cross_scene_tfidf_near_duplicate_detected:"
            + json.dumps(cross_scene_near_pairs[:20], ensure_ascii=False, sort_keys=True)
        )

    return {
        "episode_count": EXPECTED_TOTAL_COUNT,
        "micro_scene_count": len(scene_counts),
        "episodes_per_micro_scene": EXPECTED_EPISODES_PER_SCENE,
        "life_domain_count": len(domain_counts),
        "episodes_per_life_domain": EXPECTED_EPISODES_PER_DOMAIN,
        "exact_duplicate_count": 0,
        "normalized_duplicate_count": 0,
        "blocked_pattern_count": 0,
        "sentence_count_distribution": dict(sorted(sentence_counts.items())),
        "target_relation_distribution": dict(relation_counts),
        "five_w_one_h_distribution": dict(five_w_one_h_counts),
        "raw_discourse_family_count": len({str(row["discourse_family"]) for row in rows}),
        "per_scene_raw_discourse_family_count": {
            scene_id: len(values) for scene_id, values in sorted(discourse_by_scene.items())
        },
        "tfidf_similarity_threshold": 0.80,
        "tfidf_near_pair_count": len(near_pairs),
        "tfidf_cross_scene_near_pair_count": len(cross_scene_near_pairs),
        "tfidf_near_pairs_are_same_scene_only": True,
    }


def build_unit04_neb02_natural_episode_bank_360(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    root = _root(repo_root)

    r1_report = r1.build_unit04_neb01r1_strict_a1_boundary_audit_108(root)
    if r1_report.get("status") != r1.STATUS:
        raise NaturalEpisodeBank360Error("u04neb01r1_status_drift")

    base_rows = _load_effective_base_rows(root, r1_report)
    extension_rows, extension_digest = _load_extension(root)
    combined = base_rows + [dict(row) for row in extension_rows]
    summary = _validate_combined(combined)

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "authority_contract": {
            "base_effective_108_source": "U04NEB01R1_MERGED_EFFECTIVE_BANK_WITH_NEB01_CANONICAL_METADATA",
            "extension_252_source": EXTENSION_PATH,
            "extension_sha256": extension_digest,
            "gpt_authored_learner_language": True,
            "python_sentence_composer_used": False,
            "operator_approved_repair_count": len(OPERATOR_APPROVED_REPAIR_IDS),
            "operator_approved_repair_ids": sorted(OPERATOR_APPROVED_REPAIR_IDS),
            "semantic_near_duplicate_policy": (
                "TFIDF_GE_0_80_DIAGNOSTIC_ALLOWED_WITHIN_SAME_SOURCE_MICRO_SCENE;"
                "CROSS_SCENE_GE_0_80_FAILS_CLOSED"
            ),
        },
        "summary": summary,
        "effective_episodes": combined,
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
            "additional_episode_generation_performed": False,
        },
    }


def main() -> int:
    report = build_unit04_neb02_natural_episode_bank_360()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
