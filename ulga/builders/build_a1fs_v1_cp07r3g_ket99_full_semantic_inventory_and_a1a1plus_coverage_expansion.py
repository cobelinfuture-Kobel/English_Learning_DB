#!/usr/bin/env python3
"""Build a precision-guarded KET99 semantic inventory and A1/A1+ lesson overlay.

The builder consumes existing CP07B evidence metadata and private M1/M2 identities.
Only exact identities, exact normalized phrases, and closed taxonomy intersections are
admitted. It never copies transcript prose or private payloads into the output, mutates
M1, selects lessons, or unlocks A2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b  # noqa: E402
from ulga.builders import build_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as r3e  # noqa: E402
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only precision-guarded KET99 semantic inventory and optional lesson-reference expansion over existing CP07B, M1, M2, and R3E identities; no transcript text, private payload, prompt, answer, score, learner response, media, hard edge, lesson selection, mastery, retention, or A2 payload is produced."

TASK_ID = "A1FS-V1-CP07F-R3G_KET99FullSemanticInventoryAndA1A1PlusCoverageExpansion"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3g.ket99_full_semantic_inventory_a1a1plus_coverage_expansion.v1"
PASS_STATUS = "PASS_CP07F_R3G_KET99_FULL_SEMANTIC_INVENTORY_AND_A1A1PLUS_COVERAGE_EXPANSION_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R3H_KET99CoverageConsumerRefresh"
HUMAN_RESOLUTION_STEP = "A1FS-V1-CP07F-R3G1_KET99HumanEvidenceResolutionBatch"
PRECISION_REVISION = "R3G_PRECISION_PRIVATE_RECOVERY_V2"

DEFAULT_M1 = r3e.DEFAULT_M1
DEFAULT_M2 = r3e.DEFAULT_M2
DEFAULT_CP07B = r3e.DEFAULT_CP07B
DEFAULT_R3E = r3e.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r3g/ket99_full_semantic_inventory_and_coverage_expansion.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r3g/ket99_full_semantic_inventory_and_coverage_expansion.validation.json"
DEFAULT_KET99_CONSUMER_LOCATOR = (
    REPO_ROOT
    / "ulga/reports/ket_comp_transcript_final_consolidation/consumer_input_locator.json"
)
KET99_TASK_ID = "KET99-SRC-V1_FullP004P102OneShotNormalizationValidationAndPublication"
KET99_PRIVATE_LOCATOR = "private://ket99/p004-p102/normalized-transcripts-v1"
KET99_VALIDATION_STATUS = "PASS_KET99_P004_P102_ONE_SHOT_CORPUS_VALIDATION"

SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
LEVELS = {"A1", "A1+"}
DISPOSITIONS = (
    "USED_FOR_A1_A1PLUS",
    "A2_ONLY",
    "NO_RELEVANT_PEDAGOGICAL_CONTENT",
    "HUMAN_EVIDENCE_REQUIRED",
)
REQUIRED_HUMAN_RESOLUTION_IDS = {"P008", "P026"}
CONTROLLED_HUMAN_RESOLUTION_RULES: dict[str, dict[str, frozenset[str]]] = {
    "P008": {
        "allowed_skills": frozenset({"READING"}),
        "required_domains": frozenset({"READING_DETAIL_LOCATION"}),
    },
    "P026": {
        "allowed_skills": frozenset(SKILLS),
        "required_domains": frozenset({"DESCRIPTIVE_ADJECTIVES", "SHOPPING_AND_CLOTHES"}),
    },
}
MAX_REFERENCES_PER_LESSON = 12
MAX_REFERENCES_PER_TRANSCRIPT_PER_LESSON = 2

FORBIDDEN_KEYS = {
    "payload",
    "source_content",
    "text",
    "prompt",
    "scoring_contract",
    "correct_answer",
    "answer_key",
    "learner_response",
    "transcript_text",
    "speaker_turns",
    "audio_bytes",
    "recording",
    "evidence_item",
}

DOMAIN_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PERSONAL_INFORMATION", re.compile(r"(^|_)(name|age|origin|personal_information|nice_to_meet_you|introduce)(_|$)")),
    ("FAMILY_RELATIONSHIPS", re.compile(r"(^|_)(family|aunt|brother|cousin|daughter|son|mother|father|parent|grand)(_|$)")),
    ("NUMBERS_TIME_DATE", re.compile(r"(^|_)(number|date|time|clock|quarter|half|thirteen|thirty|fourteen|forty|fifteen|fifty|sixteen|sixty|seventeen|seventy)(_|$)")),
    ("HOME_AND_PLACES", re.compile(r"(^|_)(home|house|villa|flat|apartment|room|place|location)(_|$)")),
    ("FOOD_AND_DRINK", re.compile(r"(^|_)(food|drink|cereal|sausage|egg|cheese|cake|restaurant)(_|$)")),
    ("SHOPPING_AND_CLOTHES", re.compile(r"(^|_)(shop|shopping|clothing|clothes|fashion|changing_room|fitting_room|expensive|cheap)(_|$)")),
    ("DESCRIPTIVE_ADJECTIVES", re.compile(r"(^|_)(dirty|clean|expensive|cheap|light|heavy|big|small|old|new|long|short)(_|$)")),
    ("DAILY_ROUTINE_AND_FREQUENCY", re.compile(r"(^|_)(daily|routine|frequency|always|usually|often|sometimes|never)(_|$)")),
    ("MESSAGES_AND_NOTICES", re.compile(r"(^|_)(email|message|text_message|notice|note|invitation|party_message)(_|$)")),
    ("READING_DETAIL_LOCATION", re.compile(r"((^|_)(keyword|paragraph|detail|location|cloze|gap|article|multiple_choice|single_best_answer|sequential_question)(_|$)|閱讀|審題|關鍵詞|原文定位|同義改寫|排除錯誤人物)")),
    ("LISTENING_DETAIL_EXTRACTION", re.compile(r"(^|_)(listen|audio|sound|speaker|monologue|gap_completion|information_form|matching_people)(_|$)")),
    ("SPEAKING_INTERACTION", re.compile(r"(^|_)(paired|interaction|discussion|opinion|examiner|full_sentence|answer_expansion|shared_question)(_|$)")),
    ("WRITING_PRODUCTION", re.compile(r"(^|_)(write|writing|email_register|full_sentence|give_three|answer_topic)(_|$)")),
    ("ERROR_REPAIR", re.compile(r"(^|_)(error|incorrect|correction|correct|negative_then_positive|discrimination)(_|$)")),
    ("PRONUNCIATION", re.compile(r"(^|_)(pronunciation|sound|stress|syllable)(_|$)")),
    ("QUESTION_AND_ANSWER", re.compile(r"(^|_)(ask|answer|question|short_answer|yes_no)(_|$)")),
)

A2_ONLY_RULES = (
    re.compile(r"(^|_)(present_perfect|past_continuous|first_conditional|relative_clause|passive_voice)(_|$)"),
)

TOPIC_DOMAINS = {
    "PERSONAL_INFORMATION",
    "FAMILY_RELATIONSHIPS",
    "NUMBERS_TIME_DATE",
    "HOME_AND_PLACES",
    "FOOD_AND_DRINK",
    "SHOPPING_AND_CLOTHES",
    "DESCRIPTIVE_ADJECTIVES",
    "DAILY_ROUTINE_AND_FREQUENCY",
    "MESSAGES_AND_NOTICES",
}

STRATEGY_DOMAIN = {
    "LISTENING": "LISTENING_DETAIL_EXTRACTION",
    "SPEAKING": "SPEAKING_INTERACTION",
    "READING": "READING_DETAIL_LOCATION",
    "WRITING": "WRITING_PRODUCTION",
}

BASIS_PRIORITY = {
    "BASELINE_R3E_REFERENCE": 1000,
    "EXACT_CP07B_M1_NODE_TARGET": 900,
    "EXACT_NORMALIZED_SEMANTIC_ATOM": 800,
    "CONTROLLED_CANONICAL_GRAMMAR_IDENTITY": 700,
    "CONTROLLED_HUMAN_EVIDENCE_RESOLUTION": 650,
    "CONTROLLED_TOPIC_DOMAIN_AND_SKILL": 500,
    "CONTROLLED_STRATEGY_DOMAIN_INTERSECTION": 450,
}


class R3GError(ValueError):
    """Fail-closed source identity or semantic inventory error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise R3GError(f"json_object_required:{path}")
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repository_path(value: Any) -> Path:
    relative = Path(str(value or ""))
    if relative.is_absolute():
        raise R3GError("ket99_absolute_repository_locator_forbidden")
    resolved = (REPO_ROOT / relative).resolve()
    if not resolved.is_relative_to(REPO_ROOT.resolve()):
        raise R3GError("ket99_repository_locator_escape")
    return resolved


def load_ket99_contract(
    locator_path: Path,
    *,
    private_body_path: Path | None = None,
) -> dict[str, Any]:
    locator = read(locator_path)
    if locator.get("task_id") != KET99_TASK_ID:
        raise R3GError("ket99_consumer_locator_task_invalid")
    if locator.get("schema_version") != "ket99.srt.consumer_input_locator.v1":
        raise R3GError("ket99_consumer_locator_schema_invalid")
    if locator.get("private_body") != KET99_PRIVATE_LOCATOR:
        raise R3GError("ket99_private_locator_invalid")

    r3g_locator = locator.get("r3g")
    if not isinstance(r3g_locator, Mapping) or r3g_locator.get("upstream_consumer") != "CP07B":
        raise R3GError("ket99_r3g_locator_invalid")
    manifest_path = _repository_path(r3g_locator.get("source_manifest"))
    resolution_path = _repository_path(r3g_locator.get("evidence_resolution"))
    artifact_index_path = locator_path.parent / "artifact_index.json"
    validation_path = locator_path.parent / "final_validation_result.json"
    manifest = read(manifest_path)
    resolution = read(resolution_path)
    artifact_index = read(artifact_index_path)
    validation = read(validation_path)

    indexed = {
        str(row.get("path") or ""): row
        for row in artifact_index.get("artifacts", [])
        if isinstance(row, Mapping)
    }
    for path in (manifest_path, resolution_path):
        index_row = indexed.get(path.name)
        if not isinstance(index_row, Mapping):
            raise R3GError(f"ket99_artifact_index_entry_missing:{path.name}")
        if index_row.get("sha256") != _sha256_file(path):
            raise R3GError(f"ket99_artifact_index_digest_mismatch:{path.name}")
    private_row = indexed.get(KET99_PRIVATE_LOCATOR)
    if not isinstance(private_row, Mapping):
        raise R3GError("ket99_private_artifact_index_entry_missing")
    private_sha256 = str(private_row.get("sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", private_sha256):
        raise R3GError("ket99_private_artifact_digest_invalid")
    if private_row.get("repository_export_allowed") is not False:
        raise R3GError("ket99_private_artifact_export_policy_invalid")
    if private_body_path is not None and _sha256_file(private_body_path) != private_sha256:
        raise R3GError("ket99_private_body_digest_mismatch")
    if validation.get("validation_status") != KET99_VALIDATION_STATUS:
        raise R3GError("ket99_validation_status_invalid")
    if validation.get("error_count") != 0:
        raise R3GError("ket99_validation_errors_present")
    if validation.get("deterministic_rebuild_status") != "PASS":
        raise R3GError("ket99_deterministic_rebuild_not_passed")
    return {
        "consumer_locator": locator,
        "source_manifest": manifest,
        "evidence_resolution": resolution,
        "artifact_index": artifact_index,
        "validation_result": validation,
        "private_body_locator": KET99_PRIVATE_LOCATOR,
        "private_body_sha256": private_sha256,
        "private_body_verified": private_body_path is not None,
    }


def verify_ket99_contract(
    contract: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    locator = contract.get("consumer_locator")
    manifest = contract.get("source_manifest")
    resolution = contract.get("evidence_resolution")
    validation = contract.get("validation_result")
    if not all(isinstance(value, Mapping) for value in (locator, manifest, resolution, validation)):
        raise R3GError("ket99_contract_documents_missing")
    if locator.get("task_id") != KET99_TASK_ID or locator.get("private_body") != KET99_PRIVATE_LOCATOR:
        raise R3GError("ket99_contract_locator_invalid")
    if manifest.get("task_id") != KET99_TASK_ID:
        raise R3GError("ket99_manifest_task_invalid")
    if manifest.get("source_count") != 99 or manifest.get("source_range") != ["P004", "P102"]:
        raise R3GError("ket99_manifest_scope_invalid")
    if manifest.get("raw_srt_committed") is not False:
        raise R3GError("ket99_raw_export_policy_invalid")
    if validation.get("validation_status") != KET99_VALIDATION_STATUS or validation.get("error_count") != 0:
        raise R3GError("ket99_validation_not_passed")
    if contract.get("private_body_locator") != KET99_PRIVATE_LOCATOR:
        raise R3GError("ket99_private_locator_binding_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(contract.get("private_body_sha256") or "")):
        raise R3GError("ket99_private_digest_binding_invalid")
    if contract.get("private_body_verified") is not True:
        raise R3GError("ket99_private_body_not_verified")

    manifest_sources = {
        str(row.get("transcript_id") or ""): row
        for row in manifest.get("sources", [])
        if isinstance(row, Mapping)
    }
    expected_ids = {f"P{number:03d}" for number in range(4, 103)}
    if set(manifest_sources) != expected_ids:
        raise R3GError("ket99_manifest_transcript_identity_invalid")
    overlay_sources = {
        str(row.get("transcript_id") or ""): str(
            row.get("source_lineage", {}).get("source_evidence_sha256") or ""
        )
        for row in overlay.get("transcript_overlays", [])
        if isinstance(row, Mapping)
    }
    if set(overlay_sources) != expected_ids:
        raise R3GError("ket99_cp07b_transcript_identity_invalid")
    for transcript_id, source in manifest_sources.items():
        if source.get("sha256") != overlay_sources[transcript_id]:
            raise R3GError(f"ket99_cp07b_source_digest_mismatch:{transcript_id}")

    results = {
        str(row.get("transcript_id") or ""): row
        for row in resolution.get("results", [])
        if isinstance(row, Mapping)
    }
    if set(results) != REQUIRED_HUMAN_RESOLUTION_IDS:
        raise R3GError("ket99_resolution_identity_invalid")
    normalized: dict[str, dict[str, Any]] = {}
    for transcript_id in sorted(REQUIRED_HUMAN_RESOLUTION_IDS):
        row = results[transcript_id]
        if row.get("resolution_status") != "RESOLVED":
            raise R3GError(f"ket99_resolution_not_resolved:{transcript_id}")
        if row.get("source_sha256") != manifest_sources[transcript_id].get("sha256"):
            raise R3GError(f"ket99_resolution_source_digest_mismatch:{transcript_id}")
        anchors = row.get("evidence_anchors")
        if not isinstance(anchors, list) or not anchors:
            raise R3GError(f"ket99_resolution_anchors_missing:{transcript_id}")
        anchor_hashes = sorted(
            {
                str(anchor.get("normalized_cue_sha256") or "")
                for anchor in anchors
                if isinstance(anchor, Mapping)
            }
        )
        if len(anchor_hashes) != len(anchors) or any(
            not re.fullmatch(r"[0-9a-f]{64}", value) for value in anchor_hashes
        ):
            raise R3GError(f"ket99_resolution_anchor_digest_invalid:{transcript_id}")
        if row.get("raw_text_included") is not False:
            raise R3GError(f"ket99_resolution_raw_text_policy_invalid:{transcript_id}")
        semantic_atoms = sorted(
            {normalize(value) for value in row.get("semantic_atoms", []) if normalize(value)}
        )
        domains = sorted(
            {
                domain
                for atom in semantic_atoms
                for domain in lexical_domains(atom)
            }
        )
        required_domains = set(
            CONTROLLED_HUMAN_RESOLUTION_RULES[transcript_id]["required_domains"]
        )
        if not required_domains & set(domains):
            raise R3GError(f"ket99_resolution_domain_invalid:{transcript_id}")
        normalized[transcript_id] = {
            "source_sha256": str(row["source_sha256"]),
            "resolution_status": "RESOLVED",
            "resolution_basis": str(row.get("resolution_basis") or ""),
            "semantic_atoms": semantic_atoms,
            "semantic_domains": domains,
            "anchor_sha256s": anchor_hashes,
        }
    return normalized


def write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def normalize(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("’", "'").replace("can't", "cant")
    text = re.sub(r"[↔→←–—/\\+&]+", "_", text)
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def tokens(value: str) -> set[str]:
    return {token for token in value.split("_") if len(token) >= 3}


def lexical_domains(normalized: str) -> set[str]:
    result: set[str] = set()
    for domain, pattern in DOMAIN_RULES:
        if pattern.search(normalized):
            result.add(domain)
    return result


def eligible_skills(content_roles: Sequence[str]) -> set[str]:
    return {str(role).upper() for role in content_roles if str(role).upper() in SKILLS}


def walk_scalars(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, Mapping):
        for child in value.values():
            result.extend(walk_scalars(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(walk_scalars(child))
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value).strip()
        if text:
            result.append(text)
    return result


def verify_sources(
    graph: Mapping[str, Any],
    consumer: Mapping[str, Any],
    overlay: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if graph.get("task_id") != m1.TASK_ID or graph.get("schema_version") != m1.SCHEMA_VERSION:
        raise R3GError("m1_contract_invalid")
    if graph.get("validation_status") != m1.STATUS or graph.get("errors") != []:
        raise R3GError("m1_not_passed")
    if graph.get("a2_lock_contract", {}).get("state") != "LOCKED_BY_DESIGN":
        raise R3GError("m1_a2_lock_invalid")

    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise R3GError("m2_contract_invalid")
    if consumer.get("validation_status") != m2.STATUS or consumer.get("errors") != []:
        raise R3GError("m2_not_passed")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise R3GError("m2_a2_lock_invalid")

    if overlay.get("task_id") != cp07b.TASK_ID or overlay.get("schema_version") != cp07b.SCHEMA_VERSION:
        raise R3GError("cp07b_contract_invalid")
    if overlay.get("stop_reason") != "NONE" or overlay.get("errors") != []:
        raise R3GError("cp07b_not_passed")
    if overlay.get("coverage_summary", {}).get("transcript_count") != 99:
        raise R3GError("cp07b_transcript_count_not_99")
    if overlay.get("source_identity", {}).get("m1_hard_graph_sha256") != digest(graph):
        raise R3GError("cp07b_m1_binding_invalid")

    if baseline.get("task_id") != r3e.TASK_ID or baseline.get("schema_version") != r3e.SCHEMA_VERSION:
        raise R3GError("r3e_contract_invalid")
    if baseline.get("validation_status") != r3e.PASS_STATUS or baseline.get("stop_reason") != "NONE" or baseline.get("errors") != []:
        raise R3GError("r3e_not_passed")
    expected = {
        "m1_hard_graph_sha256": digest(graph),
        "m2_consumer_sha256": digest(consumer),
        "cp07b_instructional_overlay_sha256": digest(overlay),
    }
    for key, value in expected.items():
        if baseline.get("source_identity", {}).get(key) != value:
            raise R3GError(f"r3e_source_identity_mismatch:{key}")

    lessons = [
        row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and row.get("level") in LEVELS
    ]
    if len(lessons) != consumer.get("counts", {}).get("learning_lesson_count"):
        raise R3GError("learning_lesson_count_mismatch")
    lesson_ids = [str(row.get("lesson_id") or "") for row in lessons]
    if any(not value for value in lesson_ids) or len(set(lesson_ids)) != len(lesson_ids):
        raise R3GError("lesson_identity_invalid")

    nodes = {
        str(row.get("node_id") or ""): row
        for row in graph.get("nodes", [])
        if isinstance(row, Mapping) and str(row.get("node_id") or "")
    }
    assets = {
        str(row.get("asset_key") or ""): row
        for row in consumer.get("asset_records", [])
        if isinstance(row, Mapping) and str(row.get("asset_key") or "")
    }
    if len(assets) != len(consumer.get("asset_records", [])):
        raise R3GError("m2_asset_identity_invalid")
    return lessons, nodes, assets


def lesson_profiles(
    lessons: Sequence[Mapping[str, Any]],
    nodes: Mapping[str, Mapping[str, Any]],
    assets: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for lesson in lessons:
        lesson_id = str(lesson["lesson_id"])
        exact_atoms: set[str] = set()
        semantic_domains: set[str] = set()
        grammar_ids: set[str] = set()
        requirement_ids = sorted({str(value) for value in lesson.get("requirement_node_ids", []) if str(value)})

        for requirement_id in requirement_ids:
            node = nodes.get(requirement_id)
            if node is None:
                raise R3GError(f"lesson_requirement_node_missing:{lesson_id}:{requirement_id}")
            normalized = normalize(node.get("source_ref"))
            if normalized:
                exact_atoms.add(normalized)
                semantic_domains.update(lexical_domains(normalized))
                if normalized.startswith("grammar_"):
                    grammar_ids.add(normalized)

        for asset_key in lesson.get("asset_keys", []):
            asset = assets.get(str(asset_key))
            if asset is None:
                raise R3GError(f"lesson_asset_missing:{lesson_id}:{asset_key}")
            for scalar in walk_scalars(asset.get("payload")):
                normalized = normalize(scalar)
                if not normalized:
                    continue
                exact_atoms.add(normalized)
                semantic_domains.update(lexical_domains(normalized))
                if normalized.startswith("grammar_"):
                    grammar_ids.add(normalized)

        result[lesson_id] = {
            "skill": str(lesson["skill"]),
            "exact_atoms": exact_atoms,
            "semantic_domains": semantic_domains,
            "grammar_ids": grammar_ids,
            "requirement_node_ids": requirement_ids,
        }
    return result


def baseline_references(baseline: Mapping[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    result: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for lesson in baseline.get("lesson_instructional_references", []):
        if not isinstance(lesson, Mapping):
            continue
        lesson_id = str(lesson.get("lesson_id") or "")
        for reference in lesson.get("instructional_references", []):
            if not isinstance(reference, Mapping):
                continue
            occurrence_id = str(reference.get("evidence_occurrence_id") or "")
            result[lesson_id][occurrence_id] = {
                "evidence_occurrence_id": occurrence_id,
                "transcript_id": str(reference.get("transcript_id") or ""),
                "source_evidence_sha256": str(reference.get("source_evidence_sha256") or ""),
                "instructional_roles": sorted({str(value) for value in reference.get("instructional_roles", []) if str(value)}),
                "canonical_target_refs": sorted(
                    [
                        {
                            "target_type": str(target.get("target_type") or ""),
                            "target_id": str(target.get("target_id") or ""),
                        }
                        for target in reference.get("canonical_target_refs", [])
                        if isinstance(target, Mapping)
                        and str(target.get("target_type") or "")
                        and str(target.get("target_id") or "")
                    ],
                    key=lambda target: (target["target_type"], target["target_id"]),
                ),
                "semantic_domains": [],
                "mapping_basis": ["BASELINE_R3E_REFERENCE"],
                "runtime_effect": "OPTIONAL_TEACHING_REFERENCE_ONLY",
                "admission_score": BASIS_PRIORITY["BASELINE_R3E_REFERENCE"],
                "pinned_baseline": True,
            }
    return dict(result)


def candidate_score(bases: set[str]) -> int:
    return max(BASIS_PRIORITY[basis] for basis in bases) + 5 * (len(bases) - 1)


def select_references(
    baseline_rows: Mapping[str, Mapping[str, Any]],
    candidate_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    selected = [dict(value) for _, value in sorted(baseline_rows.items())]
    selected_ids = {str(row["evidence_occurrence_id"]) for row in selected}
    per_transcript = Counter(str(row["transcript_id"]) for row in selected)

    ranked = sorted(
        (
            dict(value)
            for key, value in candidate_rows.items()
            if key not in selected_ids
        ),
        key=lambda row: (
            -int(row["admission_score"]),
            str(row["transcript_id"]),
            str(row["evidence_occurrence_id"]),
        ),
    )
    for row in ranked:
        if len(selected) >= MAX_REFERENCES_PER_LESSON:
            break
        transcript_id = str(row["transcript_id"])
        if per_transcript[transcript_id] >= MAX_REFERENCES_PER_TRANSCRIPT_PER_LESSON:
            continue
        selected.append(row)
        per_transcript[transcript_id] += 1

    selected.sort(
        key=lambda row: (
            -int(row["admission_score"]),
            str(row["transcript_id"]),
            str(row["evidence_occurrence_id"]),
        )
    )
    for rank, row in enumerate(selected, start=1):
        row["admission_rank"] = rank
    return selected, max(0, len(set(candidate_rows) | set(baseline_rows)) - len(selected))


def build_artifact(
    graph: Mapping[str, Any],
    consumer: Mapping[str, Any],
    overlay: Mapping[str, Any],
    baseline: Mapping[str, Any],
    ket99_contract: Mapping[str, Any],
) -> dict[str, Any]:
    lessons, nodes, assets = verify_sources(graph, consumer, overlay, baseline)
    ket99_resolutions = verify_ket99_contract(ket99_contract, overlay)
    profiles = lesson_profiles(lessons, nodes, assets)
    baseline_by_lesson = baseline_references(baseline)
    candidate_by_lesson: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    inventory: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    transcript_rows = overlay.get("transcript_overlays")
    if not isinstance(transcript_rows, list) or len(transcript_rows) != 99:
        raise R3GError("cp07b_transcript_rows_not_99")

    for transcript in sorted(transcript_rows, key=lambda row: str(row.get("transcript_id") or "")):
        if not isinstance(transcript, Mapping):
            raise R3GError("cp07b_transcript_row_invalid")
        transcript_id = str(transcript.get("transcript_id") or "")
        roles = sorted({str(value) for value in transcript.get("content_roles", []) if str(value)})
        skills = eligible_skills(roles)
        risk_flags = sorted({str(value) for value in transcript.get("risk_flags", []) if str(value)})
        source_sha = str(transcript.get("source_lineage", {}).get("source_evidence_sha256") or "")
        transcript_domains: set[str] = set()
        exact_atom_hashes: set[str] = set()
        review_count = 0
        support_count = 0
        a2_only_count = 0
        occurrence_count = 0
        resolution_applied = False

        for occurrence in transcript.get("evidence_occurrences", []):
            if not isinstance(occurrence, Mapping):
                raise R3GError(f"cp07b_occurrence_invalid:{transcript_id}")
            occurrence_id = str(occurrence.get("evidence_occurrence_id") or "")
            normalized = normalize(occurrence.get("normalized_evidence_item"))
            if not occurrence_id or not normalized:
                raise R3GError(f"cp07b_occurrence_identity_invalid:{transcript_id}")
            occurrence_count += 1
            domain_set = lexical_domains(normalized)
            resolution = ket99_resolutions.get(transcript_id)
            resolution_anchor_sha256s: list[str] = []
            if resolution is not None and not resolution_applied:
                domain_set.update(resolution["semantic_domains"])
                resolution_anchor_sha256s = list(resolution["anchor_sha256s"])
                resolution_applied = True
            target_refs = sorted(
                [
                    {
                        "target_type": str(target.get("target_type") or ""),
                        "target_id": str(target.get("target_id") or ""),
                    }
                    for target in occurrence.get("canonical_targets", [])
                    if isinstance(target, Mapping)
                    and str(target.get("target_type") or "")
                    and str(target.get("target_id") or "")
                ],
                key=lambda target: (target["target_type"], target["target_id"]),
            )
            disposition = str(occurrence.get("disposition") or "")
            review_count += int(disposition == "REVIEW_REQUIRED")
            support_count += int(disposition == "INSTRUCTIONAL_SUPPORT_ONLY")
            a2_only_count += int(any(pattern.search(normalized) for pattern in A2_ONLY_RULES))
            transcript_domains.update(domain_set)
            exact_atom_hashes.add(digest(normalized))
            occurrences.append(
                {
                    "evidence_occurrence_id": occurrence_id,
                    "transcript_id": transcript_id,
                    "source_evidence_sha256": source_sha,
                    "normalized": normalized,
                    "normalized_semantic_atom_sha256": digest(normalized),
                    "semantic_domains": sorted(domain_set),
                    "eligible_skills": sorted(skills),
                    "canonical_target_refs": target_refs,
                    "instructional_roles": sorted(
                        {str(value) for value in occurrence.get("instructional_roles", []) if str(value)}
                    ),
                    "ket99_resolution_anchor_sha256s": resolution_anchor_sha256s,
                }
            )

        inventory.append(
            {
                "transcript_id": transcript_id,
                "content_unit_id": str(transcript.get("content_unit_id") or ""),
                "unit_id": str(transcript.get("unit_id") or ""),
                "lesson_role": str(transcript.get("lesson_role") or ""),
                "content_roles": roles,
                "risk_flags": risk_flags,
                "source_evidence_sha256": source_sha,
                "semantic_domains": sorted(transcript_domains),
                "exact_semantic_atom_count": len(exact_atom_hashes),
                "evidence_occurrence_count": occurrence_count,
                "review_required_evidence_count": review_count,
                "instructional_support_evidence_count": support_count,
                "a2_only_evidence_count": a2_only_count,
            }
        )

    for occurrence in occurrences:
        exact_atom = str(occurrence["normalized"])
        domain_set = set(occurrence["semantic_domains"])
        eligible = set(occurrence["eligible_skills"])
        resolution_rule = CONTROLLED_HUMAN_RESOLUTION_RULES.get(str(occurrence["transcript_id"]))
        m1_targets = {
            target["target_id"]
            for target in occurrence["canonical_target_refs"]
            if target["target_type"] == "M1_NODE"
        }
        grammar_targets = {
            normalize(target["target_id"])
            for target in occurrence["canonical_target_refs"]
            if target["target_type"] == "GRAMMAR_UNIT"
        }

        for lesson_id, profile in profiles.items():
            bases: set[str] = set()
            profile_atoms = set(profile["exact_atoms"])
            profile_domains = set(profile["semantic_domains"])
            skill = str(profile["skill"])

            if m1_targets & set(profile["requirement_node_ids"]):
                bases.add("EXACT_CP07B_M1_NODE_TARGET")
            if grammar_targets & (set(profile["grammar_ids"]) | profile_atoms):
                bases.add("CONTROLLED_CANONICAL_GRAMMAR_IDENTITY")
            if exact_atom in profile_atoms:
                bases.add("EXACT_NORMALIZED_SEMANTIC_ATOM")

            if (
                resolution_rule is not None
                and occurrence["ket99_resolution_anchor_sha256s"]
            ):
                allowed_skills = set(resolution_rule["allowed_skills"])
                required_domains = set(resolution_rule["required_domains"])
                if skill in allowed_skills and required_domains & domain_set & profile_domains:
                    bases.add("CONTROLLED_HUMAN_EVIDENCE_RESOLUTION")

            shared_topics = domain_set & profile_domains & TOPIC_DOMAINS
            if shared_topics and skill in eligible:
                bases.add("CONTROLLED_TOPIC_DOMAIN_AND_SKILL")

            strategy = STRATEGY_DOMAIN[skill]
            if strategy in domain_set and strategy in profile_domains and skill in eligible:
                bases.add("CONTROLLED_STRATEGY_DOMAIN_INTERSECTION")

            if not bases:
                continue

            occurrence_id = str(occurrence["evidence_occurrence_id"])
            current = candidate_by_lesson[lesson_id].get(occurrence_id)
            compatible_domains = sorted(domain_set & profile_domains)
            if current is None:
                candidate_by_lesson[lesson_id][occurrence_id] = {
                    "evidence_occurrence_id": occurrence_id,
                    "transcript_id": str(occurrence["transcript_id"]),
                    "source_evidence_sha256": str(occurrence["source_evidence_sha256"]),
                    "instructional_roles": list(occurrence["instructional_roles"]),
                    "canonical_target_refs": list(occurrence["canonical_target_refs"]),
                    "semantic_domains": compatible_domains,
                    "mapping_basis": sorted(bases),
                    "runtime_effect": "OPTIONAL_TEACHING_REFERENCE_ONLY",
                    "admission_score": candidate_score(bases),
                    "pinned_baseline": False,
                    "ket99_resolution_anchor_sha256s": list(
                        occurrence["ket99_resolution_anchor_sha256s"]
                    ),
                }
            else:
                merged_bases = set(current["mapping_basis"]) | bases
                current["mapping_basis"] = sorted(merged_bases)
                current["semantic_domains"] = sorted(set(current.get("semantic_domains", [])) | set(compatible_domains))
                current["admission_score"] = candidate_score(merged_bases)

    references: dict[str, list[dict[str, Any]]] = {}
    total_candidate_count = 0
    total_pruned_count = 0
    basis_counts: Counter[str] = Counter()
    transcript_lessons: defaultdict[str, set[str]] = defaultdict(set)

    for lesson in lessons:
        lesson_id = str(lesson["lesson_id"])
        baseline_rows = baseline_by_lesson.get(lesson_id, {})
        candidates = candidate_by_lesson.get(lesson_id, {})
        total_candidate_count += len(set(baseline_rows) | set(candidates))
        selected, pruned = select_references(baseline_rows, candidates)
        total_pruned_count += pruned
        references[lesson_id] = selected
        for reference in selected:
            transcript_lessons[str(reference["transcript_id"])].add(lesson_id)
            basis_counts.update(str(value) for value in reference.get("mapping_basis", []))

    disposition_counts: Counter[str] = Counter()
    resolved_human_ids: list[str] = []
    unresolved_human_ids: list[str] = []
    for row in inventory:
        transcript_id = str(row["transcript_id"])
        lesson_ids = sorted(transcript_lessons.get(transcript_id, set()))
        if lesson_ids:
            disposition = "USED_FOR_A1_A1PLUS"
        elif row["exact_semantic_atom_count"] == 0:
            disposition = "NO_RELEVANT_PEDAGOGICAL_CONTENT"
        elif row["evidence_occurrence_count"] > 0 and row["a2_only_evidence_count"] == row["evidence_occurrence_count"]:
            disposition = "A2_ONLY"
        else:
            disposition = "HUMAN_EVIDENCE_REQUIRED"
        row["disposition"] = disposition
        row["referenced_lesson_count"] = len(lesson_ids)
        row["referenced_skills"] = sorted({profiles[lesson_id]["skill"] for lesson_id in lesson_ids})
        row["human_resolution_status"] = (
            "CONTROLLED_EVIDENCE_RULE_RESOLVED"
            if transcript_id in REQUIRED_HUMAN_RESOLUTION_IDS and lesson_ids
            else "NOT_REQUIRED"
            if transcript_id not in REQUIRED_HUMAN_RESOLUTION_IDS
            else "UNRESOLVED"
        )
        if transcript_id in REQUIRED_HUMAN_RESOLUTION_IDS:
            if lesson_ids:
                resolved_human_ids.append(transcript_id)
            else:
                unresolved_human_ids.append(transcript_id)
        disposition_counts[disposition] += 1

    skill_summary = {
        skill: {
            "lesson_count": 0,
            "referenced_lesson_count": 0,
            "unreferenced_lesson_count": 0,
            "instructional_reference_count": 0,
        }
        for skill in SKILLS
    }
    lesson_rows: list[dict[str, Any]] = []
    for lesson in sorted(
        lessons,
        key=lambda row: (
            str(row.get("skill") or ""),
            str(row.get("level") or ""),
            str(row.get("lesson_id") or ""),
        ),
    ):
        lesson_id = str(lesson["lesson_id"])
        skill = str(lesson["skill"])
        lesson_refs = references[lesson_id]
        skill_summary[skill]["lesson_count"] += 1
        skill_summary[skill]["referenced_lesson_count"] += int(bool(lesson_refs))
        skill_summary[skill]["unreferenced_lesson_count"] += int(not lesson_refs)
        skill_summary[skill]["instructional_reference_count"] += len(lesson_refs)
        lesson_rows.append(
            {
                "lesson_id": lesson_id,
                "lesson_node_id": str(lesson.get("lesson_node_id") or ""),
                "skill": skill,
                "level": str(lesson.get("level") or ""),
                "requirement_node_ids": sorted(
                    {str(value) for value in lesson.get("requirement_node_ids", []) if str(value)}
                ),
                "reference_status": "REFERENCED" if lesson_refs else "NO_EXACT_OR_CONTROLLED_KET99_REFERENCE",
                "instructional_references": lesson_refs,
                "delivery_blocked_by_missing_reference": False,
                "hard_lesson_selection_changed": False,
            }
        )

    referenced_lessons = sum(bool(row["instructional_references"]) for row in lesson_rows)
    referenced_transcripts = sum(row["disposition"] == "USED_FOR_A1_A1PLUS" for row in inventory)
    admitted_reference_count = sum(len(row["instructional_references"]) for row in lesson_rows)
    max_reference_count = max((len(row["instructional_references"]) for row in lesson_rows), default=0)
    baseline_summary = baseline.get("coverage_summary", {})
    coverage_summary = {
        "learning_lesson_count": len(lesson_rows),
        "referenced_lesson_count": referenced_lessons,
        "unreferenced_lesson_count": len(lesson_rows) - referenced_lessons,
        "instructional_reference_count": admitted_reference_count,
        "transcript_count": len(inventory),
        "referenced_transcript_count": referenced_transcripts,
        "unused_transcript_count": len(inventory) - referenced_transcripts,
        "transcript_disposition_counts": {value: disposition_counts[value] for value in DISPOSITIONS},
        "baseline_referenced_lesson_count": int(baseline_summary.get("referenced_lesson_count", 0)),
        "baseline_referenced_transcript_count": int(baseline_summary.get("referenced_transcript_count", 0)),
        "referenced_lesson_delta": referenced_lessons - int(baseline_summary.get("referenced_lesson_count", 0)),
        "referenced_transcript_delta": referenced_transcripts - int(baseline_summary.get("referenced_transcript_count", 0)),
        "hard_graph_edge_delta": 0,
        "blocked_lesson_count": 0,
    }

    precision_summary = {
        "precision_revision": PRECISION_REVISION,
        "candidate_reference_count": total_candidate_count,
        "admitted_reference_count": admitted_reference_count,
        "pruned_reference_count": total_pruned_count,
        "maximum_reference_count_per_lesson": max_reference_count,
        "configured_maximum_reference_count_per_lesson": MAX_REFERENCES_PER_LESSON,
        "configured_maximum_reference_count_per_transcript_per_lesson": MAX_REFERENCES_PER_TRANSCRIPT_PER_LESSON,
        "average_reference_count_per_lesson": round(admitted_reference_count / len(lesson_rows), 6),
        "mapping_basis_counts": {basis: basis_counts[basis] for basis in BASIS_PRIORITY},
        "token_only_mapping_allowed": False,
        "exact_full_normalized_phrase_required": True,
        "strategy_requires_lesson_domain_intersection": True,
        "precision_gate_passed": max_reference_count <= MAX_REFERENCES_PER_LESSON,
    }

    next_short_step = NEXT_SHORT_STEP if not unresolved_human_ids else HUMAN_RESOLUTION_STEP
    artifact = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "metadata_only_ket99_full_semantic_inventory_and_a1a1plus_coverage_expansion",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "m1_hard_graph_sha256": digest(graph),
            "m2_consumer_sha256": digest(consumer),
            "cp07b_instructional_overlay_sha256": digest(overlay),
            "r3e_baseline_sha256": digest(baseline),
            "ket99_consumer_locator_sha256": digest(
                ket99_contract["consumer_locator"]
            ),
            "ket99_source_manifest_sha256": digest(
                ket99_contract["source_manifest"]
            ),
            "ket99_evidence_resolution_sha256": digest(
                ket99_contract["evidence_resolution"]
            ),
            "ket99_private_body_sha256": ket99_contract["private_body_sha256"],
        },
        "authority_contract": {
            "source_role": "NON_AUTHORITATIVE_KET_TEACHER_DELIVERY_REFERENCE",
            "mapping_model": "CONTROLLED_MULTI_DOMAIN_EXACT_TAXONOMY_WITH_DENSITY_GUARD_V2",
            "free_form_fuzzy_matching_allowed": False,
            "token_only_mapping_allowed": False,
            "generic_teacher_delivery_role_sufficient_for_mapping": False,
            "hard_graph_mutation_allowed": False,
            "hard_lesson_selection_allowed": False,
            "mastery_gate_creation_allowed": False,
            "delivery_block_on_missing_reference_allowed": False,
            "a2_a2plus_status": "LOCKED",
        },
        "human_evidence_resolution_summary": {
            "requested_transcript_ids": sorted(REQUIRED_HUMAN_RESOLUTION_IDS),
            "resolved_transcript_ids": sorted(resolved_human_ids),
            "unresolved_transcript_ids": sorted(unresolved_human_ids),
            "resolution_basis": {
                "P008": "CONTROLLED_READING_STRATEGY_LEXICON",
                "P026": "CONTROLLED_DESCRIPTIVE_ADJECTIVE_AND_SHOPPING_LEXICON",
            },
            "source_contract": "KET99_PR308_RESOLVED_EVIDENCE_ANCHORS",
            "resolution_usage": {
                transcript_id: {
                    "resolution_status": ket99_resolutions[transcript_id][
                        "resolution_status"
                    ],
                    "source_sha256": ket99_resolutions[transcript_id][
                        "source_sha256"
                    ],
                    "evidence_anchor_sha256s": ket99_resolutions[transcript_id][
                        "anchor_sha256s"
                    ],
                    "used": transcript_id in resolved_human_ids,
                }
                for transcript_id in sorted(REQUIRED_HUMAN_RESOLUTION_IDS)
            },
        },
        "private_source_contract": {
            "private_body_locator": ket99_contract["private_body_locator"],
            "private_body_sha256": ket99_contract["private_body_sha256"],
            "private_body_verified": bool(
                ket99_contract.get("private_body_verified")
            ),
            "private_body_included": False,
        },
        "transcript_semantic_inventory": inventory,
        "lesson_instructional_references": lesson_rows,
        "skill_coverage_summary": skill_summary,
        "coverage_summary": coverage_summary,
        "precision_summary": precision_summary,
        "claim_boundaries": {
            "transcript_text_included": False,
            "private_payload_included": False,
            "new_canonical_authority_created": False,
            "hard_prerequisite_changed": False,
            "lesson_selection_changed": False,
            "mastery_or_retention_claimed": False,
            "learner_delivery_completed": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": next_short_step,
    }
    walk_forbidden(artifact)
    return artifact


def walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise R3GError(f"private_or_text_key_forbidden:{path}.{key}")
            walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_forbidden(child, f"{path}[{index}]")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1-graph", type=Path, default=DEFAULT_M1)
    parser.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    parser.add_argument("--cp07b-overlay", type=Path, default=DEFAULT_CP07B)
    parser.add_argument("--r3e-baseline", type=Path, default=DEFAULT_R3E)
    parser.add_argument(
        "--ket99-consumer-locator",
        type=Path,
        default=DEFAULT_KET99_CONSUMER_LOCATOR,
    )
    parser.add_argument("--ket99-private-body", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        graph, consumer = read(args.m1_graph), read(args.m2_consumer)
        overlay, baseline = read(args.cp07b_overlay), read(args.r3e_baseline)
        ket99_contract = load_ket99_contract(
            args.ket99_consumer_locator,
            private_body_path=args.ket99_private_body,
        )
        artifact = build_artifact(
            graph, consumer, overlay, baseline, ket99_contract
        )
        from ulga.validators import validate_a1fs_v1_cp07r3g_ket99_full_semantic_inventory_and_a1a1plus_coverage_expansion as validator

        report = validator.validate_artifact(
            artifact,
            m1_graph=graph,
            m2_consumer=consumer,
            cp07b_overlay=overlay,
            r3e_baseline=baseline,
            ket99_contract=ket99_contract,
        )
        write(args.output, artifact)
        write(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (R3GError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
