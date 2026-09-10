from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1.u04ms03_m2_capability_learner_facing_consumer_integration import (
    CURRENT360_AUTHORITY,
    STATUS as MS03_STATUS,
    build_unit04_m2_capability_learner_facing_consumer_integration,
)

TASK_ID = "A1FS-V1-U04SP01_Current360SpeakingLayer1Layer2Acceptance"
STATUS = "PASS_A1FS_V1_U04SP01_CURRENT360_SPEAKING_LAYER1_LAYER2_ACCEPTANCE"
REVISION = "UNIT04_ATOMIC_PLUS_CURRENT360_CONNECTED_V1"
NEXT_SHORT_STEP = "A1FS-V1-U04SP02_SpeakingPrintBrowserVisualAcceptance"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit04 speaking materializer over already-admitted Q06/Q07 cumulative "
    "sentence evidence and the merged MS03 Current360 speaking consumer. It authors no "
    "learner wording and creates no second sentence, scene, grammar, vocabulary, chunk, "
    "QuestionBank, scoring, or A2 authority."
)

Q06_REF = "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"
Q07_REF = "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
REPAIR_REF = "ulga/contracts/a1fs_v1_u04_q07_q09_r1_reuse_only_relation_evidence_gap_fix.json"

TARGET_RELATIONS = ("in", "inside", "on", "near", "at", "under", "behind", "between")
SUPPORT_RELATIONS = ("next to", "in front of")
EXPECTED_TARGET_DISTRIBUTION = {
    "in": 8,
    "inside": 16,
    "on": 3,
    "near": 8,
    "at": 6,
    "under": 16,
    "behind": 16,
    "between": 16,
}
EXPECTED_SUPPORT_DISTRIBUTION = {"next to": 16, "in front of": 16}


class Unit04SpeakingLayerAcceptanceError(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )


def _load(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise Unit04SpeakingLayerAcceptanceError(f"required_source_missing:{relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Unit04SpeakingLayerAcceptanceError(f"required_source_not_object:{relative}")
    return value


def _normalise_sentence(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9']+", " ", text.casefold()).split())


def _split_utterances(passage: str) -> list[str]:
    text = " ".join(str(passage or "").split())
    if not text:
        return []
    rows = [row.strip() for row in re.split(r"(?<=[.!?])\s+", text) if row.strip()]
    return rows


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_sources(
    q06: dict[str, Any], q07: dict[str, Any], repair: dict[str, Any]
) -> dict[str, str]:
    if q06.get("status") != "PASS_Q06_UNIT04_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION":
        raise Unit04SpeakingLayerAcceptanceError("q06_not_pass")
    if q07.get("status") != "PASS_Q07_UNIT04_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING":
        raise Unit04SpeakingLayerAcceptanceError("q07_not_pass")
    if repair.get("status") != "PASS_Q07_Q09_R1_REUSE_ONLY_AT_RELATION_EVIDENCE_GAP_FULL_FIX":
        raise Unit04SpeakingLayerAcceptanceError("reuse_repair_not_pass")
    assets = q06.get("assets")
    scenes = q07.get("micro_scenes")
    if not isinstance(assets, list) or len(assets) != 96:
        raise Unit04SpeakingLayerAcceptanceError("q06_asset_count_invalid")
    if not isinstance(scenes, list) or len(scenes) != 96:
        raise Unit04SpeakingLayerAcceptanceError("q07_scene_count_invalid")
    scene_by_sentence: dict[str, str] = {}
    for row in scenes:
        sid = str(row.get("bound_sentence_id") or "")
        scene = str(row.get("scene_ref_id") or "")
        if not sid or not scene or sid in scene_by_sentence:
            raise Unit04SpeakingLayerAcceptanceError("q07_sentence_scene_binding_invalid")
        scene_by_sentence[sid] = scene
    if {str(row.get("sentence_id") or "") for row in assets} != set(scene_by_sentence):
        raise Unit04SpeakingLayerAcceptanceError("q06_q07_sentence_binding_not_exact")
    return scene_by_sentence


def _build_layer1(
    q06: dict[str, Any],
    repair: dict[str, Any],
    scene_by_sentence: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for asset in q06["assets"]:
        relation = str(asset.get("relation_surface") or "")
        if relation not in TARGET_RELATIONS + SUPPORT_RELATIONS:
            raise Unit04SpeakingLayerAcceptanceError(f"q06_relation_out_of_scope:{relation}")
        sid = str(asset.get("sentence_id") or "")
        text = str(asset.get("text") or "").strip()
        if not sid or not text or sid not in scene_by_sentence:
            raise Unit04SpeakingLayerAcceptanceError("q06_layer1_lineage_invalid")
        rows.append(
            {
                "atomic_id": sid,
                "text": text,
                "relation_surface": relation,
                "role": "TARGET" if relation in TARGET_RELATIONS else "SUPPORT",
                "source_class": "UNIT04_Q06_ADMITTED_SENTENCE_ASSET",
                "scene_ref_ids": [scene_by_sentence[sid]],
                "reference_mode": "UNIT04_Q07_SCENE_BOUND",
            }
        )

    resolved = repair.get("resolved_existing_sentence_scene_evidence")
    at_rows = repair.get("at_text_bound_admitted_sentence_evidence")
    if not isinstance(resolved, list) or len(resolved) != 19:
        raise Unit04SpeakingLayerAcceptanceError("reuse_scene_bound_supply_invalid")
    if not isinstance(at_rows, list) or len(at_rows) != 6:
        raise Unit04SpeakingLayerAcceptanceError("reuse_at_supply_invalid")

    for item in resolved:
        relation = str(item.get("relation_surface") or "")
        refs = [str(value) for value in item.get("source_scene_refs") or [] if str(value)]
        if relation not in {"in", "near", "on"} or not refs:
            raise Unit04SpeakingLayerAcceptanceError("reuse_scene_bound_row_invalid")
        rows.append(
            {
                "atomic_id": str(item["sentence_id"]),
                "text": str(item["text"]).strip(),
                "relation_surface": relation,
                "role": "TARGET",
                "source_class": "ADMITTED_CUMULATIVE_REUSE_SENTENCE",
                "scene_ref_ids": refs,
                "reference_mode": "EXISTING_SCENE_BOUND_REUSE",
            }
        )

    for item in at_rows:
        if str(item.get("relation_surface") or "") != "at":
            raise Unit04SpeakingLayerAcceptanceError("at_text_bound_relation_invalid")
        rows.append(
            {
                "atomic_id": str(item["sentence_id"]),
                "text": str(item["text"]).strip(),
                "relation_surface": "at",
                "role": "TARGET",
                "source_class": "ADMITTED_CUMULATIVE_REUSE_SENTENCE",
                "scene_ref_ids": [],
                "reference_mode": "TEXT_BOUND_POINT_PLACE",
            }
        )

    if any(not row["atomic_id"] or not row["text"] for row in rows):
        raise Unit04SpeakingLayerAcceptanceError("layer1_empty_identity_or_text")
    if len({row["atomic_id"] for row in rows}) != len(rows):
        raise Unit04SpeakingLayerAcceptanceError("layer1_atomic_identity_duplicate")
    normalized = [_normalise_sentence(row["text"]) for row in rows]
    if any(not value for value in normalized):
        raise Unit04SpeakingLayerAcceptanceError("layer1_normalized_sentence_empty")
    if len(set(normalized)) != len(normalized):
        raise Unit04SpeakingLayerAcceptanceError("layer1_exact_visible_sentence_duplicate")

    target_counts = Counter(
        row["relation_surface"] for row in rows if row["role"] == "TARGET"
    )
    support_counts = Counter(
        row["relation_surface"] for row in rows if row["role"] == "SUPPORT"
    )
    if dict(target_counts) != EXPECTED_TARGET_DISTRIBUTION:
        raise Unit04SpeakingLayerAcceptanceError(
            f"layer1_target_distribution_invalid:{dict(target_counts)}"
        )
    if dict(support_counts) != EXPECTED_SUPPORT_DISTRIBUTION:
        raise Unit04SpeakingLayerAcceptanceError(
            f"layer1_support_distribution_invalid:{dict(support_counts)}"
        )

    summary = {
        "atomic_sentence_count": len(rows),
        "target_atomic_sentence_count": sum(target_counts.values()),
        "support_atomic_sentence_count": sum(support_counts.values()),
        "exact_unique_sentence_count": len(set(normalized)),
        "exact_duplicate_occurrences": len(rows) - len(set(normalized)),
        "source_lineage_validity": "PASS",
        "grammar_target_form_coverage": "8/8",
        "target_relation_distribution": {key: target_counts[key] for key in TARGET_RELATIONS},
        "support_relation_distribution": {key: support_counts[key] for key in SUPPORT_RELATIONS},
        "reference_mode_counts": dict(Counter(row["reference_mode"] for row in rows)),
    }
    return rows, summary


def _lexical_metrics(utterances: list[str]) -> dict[str, Any]:
    words = [
        token.casefold()
        for text in utterances
        for token in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
    ]
    counts = Counter(words)
    total = sum(counts.values())
    ordered = [count for _, count in counts.most_common()]
    def share(n: int) -> float:
        return round(sum(ordered[:n]) / total, 6) if total else 0.0
    return {
        "distinct_lexical_payload_word_forms": len(counts),
        "top1_lexical_payload_share": share(1),
        "top10_lexical_payload_concentration": share(10),
        "top20_lexical_payload_concentration": share(20),
    }


def _build_layer2(
    ms03: dict[str, Any], layer1: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if ms03.get("status") != MS03_STATUS:
        raise Unit04SpeakingLayerAcceptanceError("ms03_not_pass")
    speaking = [
        row for row in ms03.get("task_projections", []) if row.get("skill") == "SPEAKING"
    ]
    if len(speaking) != 36:
        raise Unit04SpeakingLayerAcceptanceError(
            f"speaking_projection_count_invalid:{len(speaking)}"
        )

    atomic_by_relation: dict[str, list[str]] = {}
    for relation in TARGET_RELATIONS + SUPPORT_RELATIONS:
        atomic_by_relation[relation] = [
            row["atomic_id"] for row in layer1 if row["relation_surface"] == relation
        ]
        if not atomic_by_relation[relation]:
            raise Unit04SpeakingLayerAcceptanceError(
                f"layer1_relation_lineage_missing:{relation}"
            )

    sets: list[dict[str, Any]] = []
    all_utterances: list[str] = []
    relation_counts: Counter[str] = Counter()
    missing_dual_lineage = 0
    missing_atomic_relation_lineage = 0
    incomplete_utterance_count = 0
    family_equivalence_claim_count = 0

    for task in speaking:
        if task.get("response_authority") != CURRENT360_AUTHORITY:
            raise Unit04SpeakingLayerAcceptanceError("speaking_current360_authority_drift")
        episode = dict(task.get("current360_episode_lineage") or {})
        fact = dict(task.get("q07_m2a_fact_lineage") or {})
        alignment = dict(task.get("lineage_alignment") or {})
        shared = [str(value) for value in alignment.get("shared_visible_relation_surfaces") or []]
        utterances = _split_utterances(str(episode.get("passage") or ""))
        if not episode or not fact:
            missing_dual_lineage += 1
        if len(utterances) < 2:
            incomplete_utterance_count += 1
        atomic_lineage = {
            relation: list(atomic_by_relation.get(relation, [])) for relation in shared
        }
        if not shared or any(not ids for ids in atomic_lineage.values()):
            missing_atomic_relation_lineage += 1
        if alignment.get("family_equivalence_claimed") is not False:
            family_equivalence_claim_count += 1
        for relation in shared:
            relation_counts[relation] += 1
        all_utterances.extend(utterances)
        sets.append(
            {
                "connected_set_id": str(task.get("task_projection_id") or ""),
                "current360_episode_id": str(episode.get("episode_id") or ""),
                "current360_micro_scene_id": str(episode.get("micro_scene_id") or ""),
                "life_domain": str(episode.get("life_domain") or ""),
                "model_utterances": utterances,
                "shared_visible_relation_surfaces": shared,
                "atomic_relation_lineage": atomic_lineage,
                "current360_episode_lineage": episode,
                "q07_m2a_fact_lineage": fact,
                "lineage_alignment": alignment,
                "response_authority": CURRENT360_AUTHORITY,
            }
        )

    anomaly_counts = {
        "missing_dual_lineage_count": missing_dual_lineage,
        "missing_atomic_relation_lineage_count": missing_atomic_relation_lineage,
        "incomplete_connected_set_count": incomplete_utterance_count,
        "family_equivalence_claim_count": family_equivalence_claim_count,
    }
    if any(anomaly_counts.values()):
        raise Unit04SpeakingLayerAcceptanceError(
            "layer2_semantic_lineage_anomaly:" + json.dumps(anomaly_counts, sort_keys=True)
        )
    normalized = [_normalise_sentence(text) for text in all_utterances]
    exact_repeat = len(normalized) - len(set(normalized))
    metrics = {
        "connected_set_count": len(sets),
        "utterance_count": len(all_utterances),
        "exact_sentence_repeat_occurrences": exact_repeat,
        "exact_sentence_repeat_rate": round(exact_repeat / len(normalized), 6) if normalized else 0.0,
        **_lexical_metrics(all_utterances),
        "selected_distinct_np_surfaces": len(
            {
                text.casefold()
                for row in layer1
                for text in re.findall(r"\b(?:a|an|the)\s+[A-Za-z]+(?:\s+[A-Za-z]+)?", row["text"], flags=re.I)
            }
        ),
        "scene_coverage": {
            "task_projection_count": len(sets),
            "distinct_current360_episode_count": len({row["current360_episode_id"] for row in sets}),
            "distinct_current360_micro_scene_count": len({row["current360_micro_scene_id"] for row in sets}),
            "distinct_life_domain_count": len({row["life_domain"] for row in sets}),
        },
        "predicate_distribution": dict(relation_counts),
        "semantic_anomaly_zero_counts": anomaly_counts,
    }
    if not all(row["connected_set_id"] and row["current360_episode_id"] for row in sets):
        raise Unit04SpeakingLayerAcceptanceError("layer2_identity_missing")
    if metrics["utterance_count"] < metrics["connected_set_count"] * 2:
        raise Unit04SpeakingLayerAcceptanceError("layer2_connected_utterance_supply_too_small")
    return sets, metrics


def build_unit04_current360_speaking_layer_acceptance(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    root = _root(repo_root)
    q06 = _load(root, Q06_REF)
    q07 = _load(root, Q07_REF)
    repair = _load(root, REPAIR_REF)
    scene_by_sentence = _validate_sources(q06, q07, repair)
    layer1, layer1_summary = _build_layer1(q06, repair, scene_by_sentence)
    ms03 = build_unit04_m2_capability_learner_facing_consumer_integration(root)
    layer2, layer2_summary = _build_layer2(ms03, layer1)

    result: dict[str, Any] = {
        "schema_version": "a1fs.v1.u04.sp01.current360_speaking_layer_acceptance.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "source_refs": {
            "q06_sentence_authority": Q06_REF,
            "q07_scene_authority": Q07_REF,
            "reuse_evidence": REPAIR_REF,
            "current360_speaking_consumer": "product/a1fs_v1_2_1/u04ms03_m2_capability_learner_facing_consumer_integration.py",
        },
        "layer1_atomic_speaking_pool": layer1,
        "layer1_acceptance": layer1_summary,
        "layer2_connected_speaking": layer2,
        "layer2_acceptance": layer2_summary,
        "scope_safety": {
            "q01_q10_modified": False,
            "q06_sentence_authority_modified": False,
            "q07_scene_authority_modified": False,
            "current360_episode_content_modified": False,
            "ms03_consumer_modified": False,
            "new_learner_facing_wording_authored": False,
            "second_sentence_authority_created": False,
            "second_scene_authority_created": False,
            "listening_modified": False,
            "a2_a2plus_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    result["acceptance_sha256"] = _digest(
        {
            "layer1_acceptance": result["layer1_acceptance"],
            "layer2_acceptance": result["layer2_acceptance"],
            "scope_safety": result["scope_safety"],
            "layer1_ids": [row["atomic_id"] for row in layer1],
            "layer2_ids": [row["connected_set_id"] for row in layer2],
        }
    )
    return result


def compact_readback(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report["status"],
        "revision": report["revision"],
        "layer1_acceptance": report["layer1_acceptance"],
        "layer2_acceptance": report["layer2_acceptance"],
        "scope_safety": report["scope_safety"],
        "acceptance_sha256": report["acceptance_sha256"],
        "next_short_step": report["next_short_step"],
    }
