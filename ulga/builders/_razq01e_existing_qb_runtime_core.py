#!/usr/bin/env python3
"""Materialize approved Unit01 content through the existing U01QB runtime and renderer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as content_builder,
)
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as bank,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import u01qb03_renderer_runtime_impl as renderer

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-RAZQ01E_"
    "Unit01ApprovedContentExistingQBMaterializationAndLearnerStimulusRuntimeIntegration"
)
SCHEMA_VERSION = "a1fs.v1.razq01e.unit01_existing_qb_content_runtime.v1"
SAFE_SCHEMA_VERSION = "a1fs.v1.razq01e.unit01_existing_qb_content_runtime_safe.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01E_UNIT01_EXISTING_QB_CONTENT_RUNTIME"
DECISION_REF = "AUTOMATED_POLICY:2026-07-31:RAZQ01E"
MIN_CONTENT_ITEMS_PER_SESSION = 2
REPLACEABLE_REASONS = frozenset(
    {"TRANSFER", "GUIDED_EXTENSION", "NEW_OR_UNSEEN", "FALLBACK"}
)

OUTPUT_CANDIDATE = Path(
    "ulga/private/a1fs_v1_razq01e_unit01_existing_qb_content_extension.candidate.private.json"
)
OUTPUT_APPROVED = Path(
    "ulga/private/a1fs_v1_razq01e_unit01_existing_qb_content_extension.approved.private.json"
)
OUTPUT_SAFE = Path(
    "ulga/reports/a1fs_v1_razq01e_unit01_existing_qb_content_extension_readback.json"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-RAZQ01E_"
    "LocalPrivateExistingQBContentRuntimeCanaryAndUnit01Readback"
)

EXTENSION_SQL = """
CREATE TABLE IF NOT EXISTS razq01e_metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS razq01e_extension_items(
  item_id TEXT PRIMARY KEY REFERENCES u01qb02_item_catalog(item_id),
  content_asset_id TEXT NOT NULL,
  skill TEXT NOT NULL CHECK(skill IN ('READING','WRITING','SPEAKING')),
  pattern_family_id TEXT NOT NULL,
  approved_extension_artifact_sha256 TEXT NOT NULL,
  extension_item_sha256 TEXT NOT NULL UNIQUE,
  UNIQUE(content_asset_id, skill)
);
CREATE INDEX IF NOT EXISTS razq01e_extension_skill
ON razq01e_extension_items(skill, content_asset_id);
"""


class ContentRuntimeBuildError(ValueError):
    """Fail-closed RAZQ01E build or runtime integration error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContentRuntimeBuildError("json_object_required")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _approved_content_assets(approved_content: Mapping[str, Any]) -> list[dict[str, Any]]:
    from ulga.validators import (
        validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
        as content_validator,
    )

    policy_artifact.verify_artifact_digest(approved_content)
    if (
        approved_content.get("artifact_role") != policy_artifact.APPROVED_ROLE
        or approved_content.get("producer_id") != content_builder.TASK_ID
        or approved_content.get("level_scope") != ["A1"]
        or approved_content.get("learner_facing") is not False
        or (approved_content.get("admission") or {}).get("status") != "APPROVED"
    ):
        raise ContentRuntimeBuildError("approved_content_artifact_invalid")
    content_validator.validate_payload(approved_content.get("payload") or {})
    assets = approved_content.get("payload", {}).get("content_assets")
    if not isinstance(assets, list) or len(assets) < MIN_CONTENT_ITEMS_PER_SESSION:
        raise ContentRuntimeBuildError("approved_content_assets_insufficient")
    return [deepcopy(dict(row)) for row in assets]


def _content_text(asset: Mapping[str, Any]) -> str:
    content = asset.get("content") or {}
    sentences = [str(value).strip() for value in content.get("sentences") or []]
    turns = [
        f"{str(row.get('speaker_id') or '').strip()}: {str(row.get('utterance') or '').strip()}"
        for row in content.get("dialogue_turns") or []
        if str(row.get("speaker_id") or "").strip()
        and str(row.get("utterance") or "").strip()
    ]
    value = " ".join([*sentences, *turns]).strip()
    if not value:
        raise ContentRuntimeBuildError(
            f"approved_content_text_missing:{asset.get('content_asset_id')}"
        )
    if digest(content) != asset.get("content_sha256"):
        raise ContentRuntimeBuildError(
            f"approved_content_digest_invalid:{asset.get('content_asset_id')}"
        )
    return value


def _projection(asset: Mapping[str, Any], skill: str) -> dict[str, Any]:
    matches = [
        dict(row)
        for row in asset.get("skill_projections") or []
        if row.get("skill") == skill
    ]
    if len(matches) != 1:
        raise ContentRuntimeBuildError(
            f"content_skill_projection_invalid:{asset.get('content_asset_id')}:{skill}"
        )
    projection = matches[0]
    if (
        projection.get("existing_question_bank_id") != bank.BANK_ID
        or projection.get("existing_question_bank_version") != bank.BANK_VERSION
        or projection.get("projection_mode")
        != "REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK"
        or projection.get("projection_status")
        != "READY_FOR_EXISTING_QB_MATERIALIZATION"
    ):
        raise ContentRuntimeBuildError(
            f"content_projection_authority_invalid:{asset.get('content_asset_id')}:{skill}"
        )
    return projection


def _lexical_lookups() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    return (
        {row["lemma"]: row for row in bank.nouns()},
        {row["lemma"]: row for row in bank.adjectives()},
    )


def _structure(asset: Mapping[str, Any]) -> tuple[str, dict[str, str], dict[str, str] | None]:
    noun_lookup, adjective_lookup = _lexical_lookups()
    alignment = asset.get("target_alignment") or {}
    nouns = [str(value) for value in alignment.get("active_nouns") or []]
    adjectives = [str(value) for value in alignment.get("active_adjectives") or []]
    noun = next((noun_lookup[value] for value in nouns if value in noun_lookup), None)
    adjective = next(
        (adjective_lookup[value] for value in adjectives if value in adjective_lookup),
        None,
    )
    if noun is None:
        raise ContentRuntimeBuildError(
            f"content_active_noun_required:{asset.get('content_asset_id')}"
        )
    frame_ids = set(alignment.get("sentence_frame_ids") or [])
    if "U01-AF03" in frame_ids and adjective is not None:
        return "VERY", noun, adjective
    if adjective is not None:
        return "ADJECTIVE", noun, adjective
    return "NOUN", noun, None


def _tokens(
    structure: str,
    noun: Mapping[str, str],
    adjective: Mapping[str, str] | None,
) -> list[str]:
    if structure == "NOUN":
        return [bank.article(noun["lemma"]), noun["lemma"]]
    if structure == "ADJECTIVE" and adjective is not None:
        return [bank.article(adjective["lemma"]), adjective["lemma"], noun["lemma"]]
    if structure == "VERY" and adjective is not None:
        return ["a", "very", adjective["lemma"], noun["lemma"]]
    raise ContentRuntimeBuildError("content_structure_invalid")


def _family_for(skill: str, structure: str) -> str:
    if skill == "READING":
        return "U01-PF04-FIRST-MENTION-CONTEXT"
    if skill == "WRITING":
        return "U01-PF07-WORD-ORDER"
    return {
        "NOUN": "U01-PF10-SPEAK-NOUN",
        "ADJECTIVE": "U01-PF11-SPEAK-ADJ-NOUN",
        "VERY": "U01-PF12-SPEAK-VERY-ADJ-NOUN",
    }[structure]


def _materialize_item(
    asset: Mapping[str, Any],
    *,
    skill: str,
    approved_content_sha256: str,
) -> dict[str, Any]:
    content_asset_id = str(asset.get("content_asset_id") or "")
    if not content_asset_id:
        raise ContentRuntimeBuildError("content_asset_id_required")
    structure, noun, adjective = _structure(asset)
    tokens = _tokens(structure, noun, adjective)
    phrase = " ".join(tokens)
    family_id = _family_for(skill, structure)
    projection = _projection(asset, skill)
    if family_id not in set(projection.get("existing_family_ids") or []):
        raise ContentRuntimeBuildError(
            f"content_family_projection_missing:{content_asset_id}:{skill}:{family_id}"
        )
    source_text = _content_text(asset)
    token = f"RAZQ01E-{skill}-{content_asset_id}"

    if skill == "READING":
        prompt = "Choose the correct article for the target phrase in this scene."
        stimulus = f"{source_text} Target phrase: ___ {' '.join(tokens[1:])}."
        options: Sequence[str] = ["a", "an", "the"]
        correct_answer: Any = tokens[0]
        accepted_answers: Sequence[str] = [tokens[0]]
        scoring_mode = "EXACT_OPTION"
    elif skill == "WRITING":
        prompt = "Put the target phrase in the correct order."
        stimulus = f"{source_text} Target phrase: {phrase}."
        options = list(reversed(tokens))
        correct_answer = tokens
        accepted_answers = []
        scoring_mode = "EXACT_SEQUENCE"
    else:
        prompt = "Say the target phrase for this scene."
        stimulus = f"{source_text} Speaking cue: {phrase}."
        options = []
        correct_answer = None
        accepted_answers = [phrase]
        scoring_mode = "FEATURE_RUBRIC"

    item = bank.make_item(
        family_id=family_id,
        token=token,
        structure=structure,
        noun=noun,
        adjective_row=adjective,
        context_id=None,
        prompt=prompt,
        stimulus=stimulus,
        options=options,
        correct_answer=correct_answer,
        accepted_answers=accepted_answers,
        scoring_mode=scoring_mode,
        support_level="GUIDED_EXTENSION",
        approved=True,
        reason="RAZQ01D_APPROVED_CONTENT_EXISTING_FAMILY_MATERIALIZATION",
    )
    item["item_id"] = f"U01QB01-RAZQ01E-{skill}-{bank.slug(content_asset_id)}"
    item["learner_delivery_status"] = "READY_FOR_EXISTING_U01QB02_RUNTIME"
    item["transfer_eligible"] = skill != "SPEAKING"
    item["assessment_eligible"] = skill != "SPEAKING"
    item["reassessment_eligible"] = skill != "SPEAKING"
    item["runtime_generation_used"] = False
    item["content_asset_id"] = content_asset_id
    item["content_kind"] = asset.get("content_kind")
    item["content_sha256"] = asset.get("content_sha256")
    item["content_lineage_mode"] = (asset.get("source_lineage") or {}).get(
        "lineage_mode"
    )
    item["content_extension_task_id"] = TASK_ID
    item["source_refs"].append(
        {
            "source_type": "RAZQ01D_APPROVED_CONTENT_ASSET",
            "task_id": content_builder.TASK_ID,
            "approved_content_artifact_sha256": approved_content_sha256,
            "content_asset_id": content_asset_id,
            "content_sha256": asset.get("content_sha256"),
            "lineage_mode": item["content_lineage_mode"],
        }
    )
    item["semantic_signature"] = digest(
        {
            "existing_bank_id": bank.BANK_ID,
            "existing_bank_version": bank.BANK_VERSION,
            "content_asset_id": content_asset_id,
            "content_sha256": asset.get("content_sha256"),
            "skill": skill,
            "family_id": family_id,
            "structure": structure,
            "prompt": prompt,
            "stimulus": stimulus,
            "answer": correct_answer,
        }
    )
    return item


def build_payload(approved_content: Mapping[str, Any]) -> dict[str, Any]:
    assets = _approved_content_assets(approved_content)
    approved_content_sha256 = str(approved_content["artifact_sha256"])
    items = [
        _materialize_item(
            asset,
            skill=skill,
            approved_content_sha256=approved_content_sha256,
        )
        for asset in assets
        for skill in content_builder.SKILLS
    ]
    item_ids = [row["item_id"] for row in items]
    signatures = [row["semantic_signature"] for row in items]
    if len(item_ids) != len(set(item_ids)):
        raise ContentRuntimeBuildError("extension_item_id_duplicate")
    if len(signatures) != len(set(signatures)):
        raise ContentRuntimeBuildError("extension_semantic_signature_duplicate")
    skill_counts = dict(sorted(Counter(row["skill"] for row in items).items()))
    expected_skill_counts = {skill: len(assets) for skill in content_builder.SKILLS}
    if skill_counts != expected_skill_counts:
        raise ContentRuntimeBuildError("extension_skill_distribution_invalid")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "scope": {
            "allowed_units": [content_builder.UNIT_ID],
            "existing_question_bank_id": bank.BANK_ID,
            "existing_question_bank_version": bank.BANK_VERSION,
            "extension_mode": "APPEND_VALIDATED_ITEMS_TO_EXISTING_BANK_RUNTIME",
            "second_question_bank_created": False,
            "parallel_planner_created": False,
            "parallel_learner_database_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "unit02_to_unit24_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_status": "LOCKED",
            "runtime_free_generation_allowed": False,
        },
        "source_bindings": {
            "approved_content_task_id": content_builder.TASK_ID,
            "approved_content_artifact_sha256": approved_content_sha256,
            "approved_content_asset_count": len(assets),
            "base_question_bank_task_id": bank.TASK_ID,
            "base_question_bank_id": bank.BANK_ID,
            "base_question_bank_version": bank.BANK_VERSION,
            "base_approved_item_count": bank.EXPECTED_APPROVED_COUNT,
            "runtime_task_id": qb02.TASK_ID,
            "renderer_task_id": renderer.TASK_ID,
        },
        "extension_items": items,
        "materialization_readback": {
            "approved_content_asset_count": len(assets),
            "extension_item_count": len(items),
            "items_per_content_asset": len(content_builder.SKILLS),
            "skill_distribution": skill_counts,
            "combined_runtime_item_count": bank.EXPECTED_APPROVED_COUNT
            + len(items),
            "minimum_content_items_per_session": MIN_CONTENT_ITEMS_PER_SESSION,
        },
        "count_semantics": {
            "content_asset_count_is_not_task_count": True,
            "extension_task_count_is_not_runtime_variant_count": True,
            "runtime_variant_count": 0,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_candidate(approved_content: Mapping[str, Any]) -> dict[str, Any]:
    return policy_artifact.build_candidate(
        payload=build_payload(approved_content),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "approved_content_task_id": content_builder.TASK_ID,
            "approved_content_artifact_sha256": approved_content["artifact_sha256"],
            "existing_question_bank_id": bank.BANK_ID,
            "existing_question_bank_version": bank.BANK_VERSION,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
        as validator,
    )

    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[validator.validate_candidate(candidate)],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def build_safe_readback(
    approved: Mapping[str, Any],
    *,
    runtime_readback: Mapping[str, Any] | None = None,
    workbench_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(approved)
    payload = approved.get("payload") or {}
    core = {
        "schema_version": SAFE_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "approved_extension_artifact_sha256": approved["artifact_sha256"],
        "content_governance": deepcopy(approved.get("content_governance")),
        "source_bindings": deepcopy(payload.get("source_bindings")),
        "materialization_readback": deepcopy(
            payload.get("materialization_readback")
        ),
        "extension_item_hashes": [
            {
                "item_id": row["item_id"],
                "content_asset_id": row["content_asset_id"],
                "skill": row["skill"],
                "pattern_family_id": row["pattern_family_id"],
                "item_sha256": digest(row),
            }
            for row in payload.get("extension_items") or []
        ],
        "runtime_readback": deepcopy(dict(runtime_readback or {})),
        "workbench_manifest": deepcopy(dict(workbench_manifest or {})),
        "boundaries": deepcopy(payload.get("scope")),
        "next_short_step": NEXT_SHORT_STEP,
    }
    return {**core, "readback_sha256": digest(core)}


def _register_item(
    connection: sqlite3.Connection,
    item: Mapping[str, Any],
    *,
    approved_extension_sha256: str,
) -> None:
    item_id = str(item["item_id"])
    skill = str(item["skill"])
    lesson_id = qb02.UNIT01_LESSONS[skill]
    key = qb02.asset_key(item_id)
    item_digest = qb02.digest(item)
    role = qb02.item_role(item)
    response = qb02.m6_contract(item, lesson_id=lesson_id, key=key)
    contract_json = qb02.m6.canonical(response)
    contract_digest = qb02.m6.sha(response)

    existing_asset = connection.execute(
        "SELECT asset_id,lesson_id,content_digest FROM lesson_assets WHERE asset_key=?",
        (key,),
    ).fetchone()
    if existing_asset and (
        existing_asset["asset_id"] != item_id
        or existing_asset["lesson_id"] != lesson_id
        or existing_asset["content_digest"] != item_digest
    ):
        raise ContentRuntimeBuildError(f"extension_lesson_asset_drift:{item_id}")
    connection.execute(
        "INSERT OR IGNORE INTO lesson_assets(asset_key,asset_id,lesson_id,role,content_digest) VALUES(?,?,?,?,?)",
        (key, item_id, lesson_id, role, item_digest),
    )

    existing_contract = connection.execute(
        "SELECT lesson_id,contract_digest FROM response_contracts WHERE asset_key=?",
        (key,),
    ).fetchone()
    if existing_contract and (
        existing_contract["lesson_id"] != lesson_id
        or existing_contract["contract_digest"] != contract_digest
    ):
        raise ContentRuntimeBuildError(f"extension_response_contract_drift:{item_id}")
    connection.execute(
        """INSERT OR IGNORE INTO response_contracts
        (asset_key,lesson_id,skill,role,contract_json,contract_digest,capture_enabled)
        VALUES(?,?,?,?,?,?,?)""",
        (
            key,
            lesson_id,
            skill,
            role,
            contract_json,
            contract_digest,
            int(response["capture_enabled"]),
        ),
    )

    existing_item = connection.execute(
        "SELECT item_digest FROM u01qb02_item_catalog WHERE item_id=?", (item_id,)
    ).fetchone()
    if existing_item and existing_item["item_digest"] != item_digest:
        raise ContentRuntimeBuildError(f"extension_item_catalog_drift:{item_id}")
    connection.execute(
        """INSERT OR IGNORE INTO u01qb02_item_catalog
        (item_id,asset_key,lesson_id,skill,pattern_family_id,unit_pattern_id,support_level,
         assessment_eligible,transfer_eligible,capture_enabled,private_item_json,item_digest)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item_id,
            key,
            lesson_id,
            skill,
            item["pattern_family_id"],
            item["unit_pattern_ids"][0],
            item["support_level"],
            int(item["assessment_eligible"]),
            int(item["transfer_eligible"]),
            int(response["capture_enabled"]),
            canonical(item),
            item_digest,
        ),
    )
    connection.execute(
        """INSERT OR IGNORE INTO razq01e_extension_items
        (item_id,content_asset_id,skill,pattern_family_id,
         approved_extension_artifact_sha256,extension_item_sha256)
        VALUES(?,?,?,?,?,?)""",
        (
            item_id,
            item["content_asset_id"],
            skill,
            item["pattern_family_id"],
            approved_extension_sha256,
            item_digest,
        ),
    )


def materialize_runtime(
    database: Path, approved_extension: Mapping[str, Any]
) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
        as validator,
    )

    validator.validate_approved(approved_extension)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(database))
    items = approved_extension.get("payload", {}).get("extension_items") or []
    extension_sha = str(approved_extension["artifact_sha256"])

    existing_extension: dict[str, str] = {}
    with runtime.connect() as connection:
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='razq01e_metadata'"
        ).fetchone():
            existing_extension = dict(
                connection.execute("SELECT key,value FROM razq01e_metadata")
            )
    if existing_extension:
        if (
            existing_extension.get("validation_status") != PASS_STATUS
            or existing_extension.get("approved_extension_artifact_sha256")
            != extension_sha
        ):
            raise ContentRuntimeBuildError("existing_razq01e_runtime_identity_drift")
        base = {
            "validation_status": qb02.PASS_STATUS,
            "registered_item_count": bank.EXPECTED_APPROVED_COUNT,
            "response_contract_count": bank.EXPECTED_APPROVED_COUNT,
            "existing_materialization_reused": True,
        }
    else:
        base = runtime.initialize()

    with runtime.write() as connection:
        connection.executescript(EXTENSION_SQL)
        metadata = dict(connection.execute("SELECT key,value FROM u01qb02_metadata"))
        base_sha = metadata.get("base_source_bank_artifact_sha256") or metadata.get(
            "source_bank_artifact_sha256"
        )
        if not isinstance(base_sha, str) or len(base_sha) != 64:
            raise ContentRuntimeBuildError("base_bank_sha256_invalid")
        for item in items:
            _register_item(
                connection,
                item,
                approved_extension_sha256=extension_sha,
            )
        combined_sha = digest(
            {
                "base_question_bank_artifact_sha256": base_sha,
                "content_extension_artifact_sha256": extension_sha,
            }
        )
        extension_count = connection.execute(
            "SELECT COUNT(*) FROM razq01e_extension_items"
        ).fetchone()[0]
        combined_count = connection.execute(
            "SELECT COUNT(*) FROM u01qb02_item_catalog"
        ).fetchone()[0]
        expected_extension_count = len(items)
        expected_combined_count = bank.EXPECTED_APPROVED_COUNT + len(items)
        if (
            extension_count != expected_extension_count
            or combined_count != expected_combined_count
        ):
            raise ContentRuntimeBuildError(
                f"runtime_extension_count_invalid:{extension_count}:{combined_count}"
            )
        metadata_values = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "approved_extension_artifact_sha256": extension_sha,
            "approved_content_artifact_sha256": approved_extension["payload"][
                "source_bindings"
            ]["approved_content_artifact_sha256"],
            "extension_item_count": str(extension_count),
            "base_item_count": str(bank.EXPECTED_APPROVED_COUNT),
            "combined_runtime_item_count": str(combined_count),
            "minimum_content_items_per_session": str(
                MIN_CONTENT_ITEMS_PER_SESSION
            ),
            "existing_u01qb02_runtime_reused": "true",
            "existing_u01qb03_renderer_reused": "true",
            "parallel_question_bank_created": "false",
            "parallel_runtime_created": "false",
            "a2_unlocked": "false",
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            "INSERT OR REPLACE INTO razq01e_metadata(key,value) VALUES(?,?)",
            metadata_values.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "base_source_bank_artifact_sha256": base_sha,
                "source_bank_artifact_sha256": combined_sha,
                "razq01e_extension_artifact_sha256": extension_sha,
                "razq01e_extension_item_count": str(extension_count),
                "razq01e_combined_runtime_item_count": str(combined_count),
            }.items(),
        )
    return {
        "validation_status": PASS_STATUS,
        "base_runtime_readback": base,
        "extension_item_count": len(items),
        "combined_runtime_item_count": bank.EXPECTED_APPROVED_COUNT + len(items),
        "combined_source_bank_sha256": combined_sha,
        "existing_u01qb02_runtime_reused": True,
        "parallel_runtime_created": False,
        "a2_unlocked": False,
    }


def _compatible_reason(row: Mapping[str, Any], reason: str) -> bool:
    if reason in {"NEW_OR_UNSEEN", "FALLBACK"}:
        return True
    if reason == "TRANSFER":
        return bool(row.get("transfer_eligible"))
    if reason == "GUIDED_EXTENSION":
        return row.get("support_level") == "GUIDED_EXTENSION"
    return False


def _recompute_plan_digest(
    connection: sqlite3.Connection, session_id: str, source_bank_sha256: str
) -> str:
    plan = connection.execute(
        "SELECT * FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
    ).fetchone()
    if not plan:
        raise ContentRuntimeBuildError("session_plan_missing")
    rows = connection.execute(
        "SELECT item_position,item_id,selection_reason FROM u01qb02_session_items WHERE session_id=? ORDER BY item_position",
        (session_id,),
    ).fetchall()
    core = {
        "session_id": session_id,
        "learner_id": plan["learner_id"],
        "lesson_id": plan["lesson_id"],
        "skill": plan["skill"],
        "selected_at": plan["selected_at"],
        "recent_exposure_window": plan["recent_exposure_window"],
        "items": [
            {
                "position": row["item_position"],
                "item_id": row["item_id"],
                "reason": row["selection_reason"],
            }
            for row in rows
        ],
        "source_bank_sha256": source_bank_sha256,
    }
    value = qb02.digest(core)
    connection.execute(
        "UPDATE u01qb02_session_plans SET source_bank_sha256=?,plan_digest=? WHERE session_id=?",
        (source_bank_sha256, value, session_id),
    )
    return value


def assemble_session_with_content(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    minimum_content_items: int = MIN_CONTENT_ITEMS_PER_SESSION,
) -> dict[str, Any]:
    if minimum_content_items < 1 or minimum_content_items > qb02.SESSION_SIZE:
        raise ContentRuntimeBuildError("minimum_content_items_invalid")
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(database))
    runtime.assemble_session(learner_id=learner_id, session_id=session_id)
    with runtime.write() as connection:
        metadata = dict(connection.execute("SELECT key,value FROM razq01e_metadata"))
        if metadata.get("validation_status") != PASS_STATUS:
            raise ContentRuntimeBuildError("razq01e_runtime_not_materialized")
        if connection.execute(
            "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?",
            (session_id,),
        ).fetchone()[0]:
            current = connection.execute(
                """SELECT COUNT(*) FROM u01qb02_session_items s
                JOIN razq01e_extension_items e USING(item_id)
                WHERE s.session_id=?""",
                (session_id,),
            ).fetchone()[0]
            if current < minimum_content_items:
                raise ContentRuntimeBuildError(
                    "content_quota_must_be_applied_before_exposure"
                )
        plan = connection.execute(
            "SELECT learner_id,lesson_id,skill FROM u01qb02_session_plans WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not plan or plan["learner_id"] != learner_id:
            raise ContentRuntimeBuildError("content_plan_identity_invalid")
        selected = connection.execute(
            """SELECT s.item_position,s.item_id,s.selection_reason,
            CASE WHEN e.item_id IS NULL THEN 0 ELSE 1 END AS is_extension
            FROM u01qb02_session_items s
            LEFT JOIN razq01e_extension_items e USING(item_id)
            WHERE s.session_id=? ORDER BY s.item_position""",
            (session_id,),
        ).fetchall()
        extension_count = sum(int(row["is_extension"]) for row in selected)
        selected_ids = {row["item_id"] for row in selected}
        needed = max(0, minimum_content_items - extension_count)
        if needed:
            recent = {
                row[0]
                for row in connection.execute(
                    "SELECT item_id FROM u01qb02_item_exposures WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?",
                    (learner_id, qb02.RECENT_EXPOSURE_WINDOW),
                )
            }
            candidates = [
                dict(row)
                for row in connection.execute(
                    """SELECT c.*,e.content_asset_id
                    FROM u01qb02_item_catalog c
                    JOIN razq01e_extension_items e USING(item_id)
                    WHERE c.lesson_id=? ORDER BY c.item_id""",
                    (plan["lesson_id"],),
                )
                if row["item_id"] not in selected_ids and row["item_id"] not in recent
            ]
            positions = [
                dict(row)
                for row in reversed(selected)
                if not row["is_extension"]
                and row["selection_reason"] in REPLACEABLE_REASONS
            ]
            for position in positions:
                if needed == 0:
                    break
                compatible = [
                    row
                    for row in candidates
                    if _compatible_reason(row, position["selection_reason"])
                ]
                compatible.sort(
                    key=lambda row: (
                        hashlib.sha256(
                            f"{learner_id}|{session_id}|{position['selection_reason']}|{row['item_id']}".encode(
                                "utf-8"
                            )
                        ).hexdigest(),
                        row["item_id"],
                    )
                )
                if not compatible:
                    continue
                replacement = compatible[0]
                connection.execute(
                    "UPDATE u01qb02_session_items SET item_id=? WHERE session_id=? AND item_position=?",
                    (replacement["item_id"], session_id, position["item_position"]),
                )
                candidates = [
                    row
                    for row in candidates
                    if row["item_id"] != replacement["item_id"]
                ]
                selected_ids.add(replacement["item_id"])
                needed -= 1
            if needed:
                raise ContentRuntimeBuildError(
                    f"content_quota_materialization_incomplete:{needed}"
                )
        combined_sha = dict(
            connection.execute("SELECT key,value FROM u01qb02_metadata")
        ).get("source_bank_artifact_sha256")
        if not isinstance(combined_sha, str) or len(combined_sha) != 64:
            raise ContentRuntimeBuildError("combined_source_bank_sha256_invalid")
        _recompute_plan_digest(connection, session_id, combined_sha)
    plan_payload = runtime.assemble_session(
        learner_id=learner_id, session_id=session_id
    )
    with sqlite3.connect(Path(database)) as connection:
        extension_ids = {
            row[0]
            for row in connection.execute(
                "SELECT item_id FROM razq01e_extension_items"
            )
        }
    content_item_ids = [
        row["item_id"]
        for row in plan_payload["items"]
        if row["item_id"] in extension_ids
    ]
    content_count = len(content_item_ids)
    if content_count < minimum_content_items:
        raise ContentRuntimeBuildError("content_session_quota_not_met")
    return {
        **plan_payload,
        "content_extension_item_count": content_count,
        "content_extension_item_ids": content_item_ids,
        "minimum_content_extension_item_count": minimum_content_items,
        "content_extension_task_id": TASK_ID,
    }


def build_workbench_with_content(
    *,
    database: Path,
    learner_id: str,
    session_id: str,
    output_root: Path,
) -> dict[str, Any]:
    plan = assemble_session_with_content(
        database,
        learner_id=learner_id,
        session_id=session_id,
    )
    manifest = renderer.build_workbench(
        database=Path(database),
        learner_id=learner_id,
        session_id=session_id,
        output_root=Path(output_root),
    )
    output_root = Path(output_root)
    bundle_path = output_root / "session.private.json"
    manifest_path = output_root / "manifest.json"
    bundle = load(bundle_path)
    with sqlite3.connect(Path(database)) as connection:
        connection.row_factory = sqlite3.Row
        extension_rows = {
            row["item_id"]: dict(row)
            for row in connection.execute(
                """SELECT e.item_id,e.content_asset_id,c.private_item_json
                FROM razq01e_extension_items e
                JOIN u01qb02_item_catalog c USING(item_id)
                WHERE e.item_id IN (
                  SELECT item_id FROM u01qb02_session_items WHERE session_id=?
                )""",
                (session_id,),
            )
        }
    for item in bundle.get("items") or []:
        extension = extension_rows.get(item.get("item_id"))
        if not extension:
            continue
        private_item = json.loads(extension["private_item_json"])
        item["content_asset_id"] = extension["content_asset_id"]
        item["content_kind"] = private_item.get("content_kind")
        item["content_lineage_mode"] = private_item.get("content_lineage_mode")
        item["content_extension_task_id"] = TASK_ID
    renderer._assert_safe(bundle)
    renderer.atomic(
        bundle_path, json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    )
    raw = bundle_path.read_bytes()
    manifest = load(manifest_path)
    manifest["files"]["session.private.json"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    manifest["content_extension_item_count"] = len(extension_rows)
    manifest["minimum_content_extension_item_count"] = MIN_CONTENT_ITEMS_PER_SESSION
    manifest["content_extension_task_id"] = TASK_ID
    manifest["existing_u01qb03_renderer_reused"] = True
    renderer.atomic(
        manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    bundle_extension_ids = set(extension_rows)
    if len(bundle_extension_ids) < MIN_CONTENT_ITEMS_PER_SESSION:
        raise ContentRuntimeBuildError("workbench_content_quota_not_met")
    if set(plan["content_extension_item_ids"]) != bundle_extension_ids:
        raise ContentRuntimeBuildError("workbench_content_plan_drift")
    return {
        **manifest,
        "content_extension_item_count": len(bundle_extension_ids),
        "minimum_content_extension_item_count": MIN_CONTENT_ITEMS_PER_SESSION,
        "content_extension_task_id": TASK_ID,
        "existing_u01qb03_renderer_reused": True,
    }


def build_extension_package(
    approved_content: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate(approved_content)
    approved = admit_candidate(candidate)
    safe = build_safe_readback(approved)
    return candidate, approved, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_cmd = commands.add_parser("build")
    runtime_cmd = commands.add_parser("runtime")
    for command in (build_cmd, runtime_cmd):
        command.add_argument("--approved-content", type=Path, required=True)
        command.add_argument("--candidate-output", type=Path, default=OUTPUT_CANDIDATE)
        command.add_argument("--approved-output", type=Path, default=OUTPUT_APPROVED)
        command.add_argument("--safe-output", type=Path, default=OUTPUT_SAFE)
        command.add_argument("--expected-content-assets", type=int, default=62)
    runtime_cmd.add_argument("--database", type=Path, required=True)
    runtime_cmd.add_argument("--learner-id", required=True)
    runtime_cmd.add_argument("--session-id", required=True)
    runtime_cmd.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)

    approved_content = load(args.approved_content)
    candidate, approved, safe = build_extension_package(approved_content)
    actual_assets = approved["payload"]["source_bindings"][
        "approved_content_asset_count"
    ]
    if actual_assets != args.expected_content_assets:
        raise ContentRuntimeBuildError(
            f"approved_content_asset_count_invalid:{actual_assets}:{args.expected_content_assets}"
        )
    runtime_readback: dict[str, Any] = {}
    manifest: dict[str, Any] = {}
    if args.command == "runtime":
        runtime_readback = materialize_runtime(args.database, approved)
        manifest = build_workbench_with_content(
            database=args.database,
            learner_id=args.learner_id,
            session_id=args.session_id,
            output_root=args.output_root,
        )
        safe = build_safe_readback(
            approved,
            runtime_readback=runtime_readback,
            workbench_manifest=manifest,
        )
    write_json(args.candidate_output, candidate, private=True)
    write_json(args.approved_output, approved, private=True)
    write_json(args.safe_output, safe)
    print(f"STATUS={PASS_STATUS}")
    print(f"APPROVED_CONTENT_ASSETS={actual_assets}")
    print(
        f"EXISTING_QB_EXTENSION_ITEMS={approved['payload']['materialization_readback']['extension_item_count']}"
    )
    if runtime_readback:
        print(
            f"COMBINED_RUNTIME_ITEMS={runtime_readback['combined_runtime_item_count']}"
        )
        print(
            f"SESSION_CONTENT_EXTENSION_ITEMS={manifest['content_extension_item_count']}"
        )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
