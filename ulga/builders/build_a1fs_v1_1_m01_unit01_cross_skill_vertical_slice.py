#!/usr/bin/env python3
"""Build the A1FS V1.1 Unit 01 cross-skill learner-content vertical slice.

This milestone keeps the existing 24-unit curriculum, lesson identities, learner
state, M6 scoring contracts, dashboard, and no-audio boundaries. It replaces only
the learner-visible payload for Unit 01 Reading, Writing, and Speaking practice
with one connected classroom situation.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime as s17,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

PROGRAM_ID = "A1FS-ONLINE-V1.1"
TASK_ID = (
    "A1FS-ONLINE-V1.1-M01_"
    "Unit01RealReadingContextualWritingSpeakingCrossSkillVerticalSlice"
)
SCHEMA_VERSION = "a1fs.online.v1_1.m01.unit01_cross_skill_vertical_slice.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_1_M01_UNIT01_CROSS_SKILL_VERTICAL_SLICE"
PRODUCT_STATUS = "A1FS_V1_1_UNIT01_CROSS_SKILL_VERTICAL_SLICE_READY"
PRODUCT_VERSION = "1.1.0-dev-m01"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.1-M02_"
    "Unit01LocalProductAcceptanceAndV1_1ReleasePackaging"
)

UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
LEARNING_UNIT_LABEL = "01. 冠詞：a、an、the"
DECISION_REF = "OPERATOR_APPROVAL:2026-07-28:M01A-M01D"
LESSON_IDS = {
    "READING": f"A1FS_ONLINE_V1:{UNIT_ID}:READING",
    "WRITING": f"A1FS_ONLINE_V1:{UNIT_ID}:WRITING",
    "SPEAKING": f"A1FS_ONLINE_V1:{UNIT_ID}:SPEAKING",
}
EXPECTED_LANE_COUNTS = {"READING": 4, "WRITING": 4, "SPEAKING": 3}

PASSAGE_TITLE = "Mia's classroom bag"
PASSAGE = (
    "Mia is in a classroom. She has a bag and a book. "
    "There is an apple in the bag. A cat is near the door. "
    "Mia puts the book on the desk. Later, she eats the apple."
)

READING_SPECS = (
    {
        "spec_id": "M01A-R01",
        "role": "PRD",
        "accepted_text": "a cat",
        "prompt": "Which animal is near the door?",
        "support": "Find the sentence about the animal near the door.",
        "comprehension_dimension": "EXPLICIT_INFORMATION",
    },
    {
        "spec_id": "M01A-R02",
        "role": "PRD",
        "accepted_text": "the book",
        "prompt": "What does Mia put on the desk?",
        "support": "Read the fifth sentence.",
        "comprehension_dimension": "EXPLICIT_INFORMATION",
    },
    {
        "spec_id": "M01A-R03",
        "role": "PRD",
        "accepted_text": "an apple",
        "prompt": "What is in Mia's bag?",
        "support": "Read the third sentence.",
        "comprehension_dimension": "EXPLICIT_INFORMATION",
    },
    {
        "spec_id": "M01A-R04",
        "role": "CHK",
        "accepted_text": "a cat",
        "prompt": "Which option correctly names the new animal in the passage?",
        "support": "Use a or an when something is mentioned as one new item.",
        "comprehension_dimension": "GRAMMAR_IN_CONTEXT_CHECKPOINT",
    },
)

SPEAKING_SPECS = (
    {
        "spec_id": "M01C-S01",
        "prompt": "Look at the classroom situation. Say what Mia has.",
        "model": "Mia has a bag and a book.",
        "frame": "Mia has a ___ and a ___.",
        "communicative_goal": "NAME_PERSONAL_OBJECTS",
    },
    {
        "spec_id": "M01C-S02",
        "prompt": "Say what is inside the bag.",
        "model": "There is an apple in the bag.",
        "frame": "There is an ___ in the ___.",
        "communicative_goal": "DESCRIBE_CONTENTS",
    },
    {
        "spec_id": "M01C-S03",
        "prompt": "Say where the cat is.",
        "model": "A cat is near the door.",
        "frame": "A ___ is near the ___.",
        "communicative_goal": "DESCRIBE_LOCATION",
    },
)


class Unit01SliceError(ValueError):
    """Fail-closed Unit 01 content, projection, or runtime-overlay error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return policy_artifact.digest(value)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Unit01SliceError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise Unit01SliceError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def candidate_payload() -> dict[str, Any]:
    """Return the operator-approved, project-authored Unit 01 content candidate."""
    return {
        "content_id": "A1FS_V1_1_UNIT01_CLASSROOM_ARTICLES_SLICE",
        "unit_id": UNIT_ID,
        "learner_label": LEARNING_UNIT_LABEL,
        "level_scope": ["A1"],
        "grammar_targets": ["a + singular countable noun", "an + vowel sound", "the + known noun"],
        "shared_situation": {
            "title": PASSAGE_TITLE,
            "setting": "CLASSROOM",
            "passage": PASSAGE,
            "sentence_count": 6,
        },
        "shared_language_assets": {
            "vocabulary": ["classroom", "bag", "book", "apple", "cat", "door", "desk"],
            "chunks": ["in the bag", "near the door", "on the desk", "later"],
            "core_sentences": [
                "Mia has a bag and a book.",
                "There is an apple in the bag.",
                "A cat is near the door.",
                "Mia puts the book on the desk.",
            ],
        },
        "reading": {
            "lesson_id": LESSON_IDS["READING"],
            "activity_count": 4,
            "specs": [deepcopy(row) for row in READING_SPECS],
            "real_passage_required": True,
            "cross_sentence_reading_present": True,
        },
        "writing": {
            "lesson_id": LESSON_IDS["WRITING"],
            "activity_count": 4,
            "progression": [
                "CONTROLLED_PHRASE",
                "CONTROLLED_SEQUENCE",
                "GUIDED_CONTEXTUAL_SENTENCE",
                "CONTEXTUAL_CHECKPOINT",
            ],
            "context": "Write about the same classroom situation used in Reading.",
        },
        "speaking": {
            "lesson_id": LESSON_IDS["SPEAKING"],
            "activity_count": 3,
            "practice_only": True,
            "recording_enabled": False,
            "scoring_enabled": False,
            "specs": [deepcopy(row) for row in SPEAKING_SPECS],
        },
        "cross_skill_reconciliation": {
            "shared_grammar_target": True,
            "shared_vocabulary": True,
            "shared_situation": True,
            "reading_to_writing_transfer": True,
            "reading_to_speaking_transfer": True,
            "parallel_curriculum_created": False,
        },
        "source_policy": {
            "content_origin": "PROJECT_AUTHORED",
            "ket_asset_body_role": "SKILL_STRUCTURE_AND_TASK_SHAPE_REFERENCE",
            "raz_role": "SOURCE_GROUNDING_AND_A1_CONTEXT_SUITABILITY",
            "raw_ket_text_copied": False,
            "raw_raz_text_copied": False,
            "canonical_grammar_authority_replaced": False,
        },
        "boundaries": {
            "unit02_or_later_modified": False,
            "lesson_identity_changed": False,
            "asset_identity_changed": False,
            "scoring_authority_changed": False,
            "learner_state_authority_changed": False,
            "listening_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
    }


def build_candidate(source_bindings: Mapping[str, Any]) -> dict[str, Any]:
    """Build policy-bound candidate JSON; it is not learner-facing."""
    return policy_artifact.build_candidate(
        payload=candidate_payload(),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings=dict(source_bindings),
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and admit the candidate into approved canonical JSON."""
    from ulga.validators import (
        validate_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as validator,
    )

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def _projection_payload(
    *,
    skill: str,
    approved: Mapping[str, Any],
    prompt: str,
    response_mode: str,
    scoring_contract: Mapping[str, Any],
    evidence_level: str,
) -> dict[str, Any]:
    payload = approved["payload"]
    return {
        "skill": skill,
        "prompt": prompt,
        "response_mode": response_mode,
        "support_level": "A1_GUIDED",
        "initiative_level": "CONTROLLED_TO_GUIDED",
        "scoring_contract": dict(scoring_contract),
        "evidence_level": evidence_level,
        "source_bindings": {
            "approved_content_sha256": approved["artifact_sha256"],
            "grammar_unit_id": UNIT_ID,
            "ket_asset_body_role": payload["source_policy"]["ket_asset_body_role"],
            "raz_role": payload["source_policy"]["raz_role"],
        },
        "content_identity": {
            "content_id": payload["content_id"],
            "unit_id": UNIT_ID,
            "lesson_id": LESSON_IDS[skill],
            "product_version": PRODUCT_VERSION,
        },
    }


def build_projections(approved: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Build the three governed learner-facing skill projections."""
    specs = {
        "READING": _projection_payload(
            skill="READING",
            approved=approved,
            prompt="Read the classroom passage and answer four questions.",
            response_mode="SELECT_ONE",
            scoring_contract={"authority": "EXISTING_M6_CONTRACTS", "mode": "PRESERVE_PER_ASSET"},
            evidence_level="SCORED_READING_RESPONSE",
        ),
        "WRITING": _projection_payload(
            skill="WRITING",
            approved=approved,
            prompt="Write about the classroom passage using a, an, and the.",
            response_mode="TEXT_OR_SEQUENCE",
            scoring_contract={
                "authority": "EXISTING_M6_CONTRACTS",
                "mode": "PRESERVE_DETERMINISTIC_OR_HUMAN_REVIEW",
            },
            evidence_level="SCORED_OR_HUMAN_REVIEWED_WRITING_RESPONSE",
        ),
        "SPEAKING": _projection_payload(
            skill="SPEAKING",
            approved=approved,
            prompt="Say three sentences about the classroom situation.",
            response_mode="ORAL_PRACTICE_NO_CAPTURE",
            scoring_contract={"authority": "NONE", "practice_only": True},
            evidence_level="EXPOSURE_ONLY_NO_MASTERY",
        ),
    }
    return {
        skill: policy_artifact.build_four_skill_projection(
            approved,
            skill=skill,
            projection_payload=payload,
            producer_id=TASK_ID,
        )
        for skill, payload in specs.items()
    }


def _contracts_for_lessons(
    database: Path,
    lesson_ids: Sequence[str],
) -> dict[str, dict[str, Any]]:
    placeholders = ",".join("?" for _ in lesson_ids)
    query = (
        "SELECT lesson_id,asset_key,role,capture_enabled,contract_json "
        f"FROM response_contracts WHERE lesson_id IN ({placeholders})"
    )
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, tuple(lesson_ids)).fetchall()
    contracts: dict[str, dict[str, Any]] = {}
    for row in rows:
        contract = json.loads(str(row["contract_json"]))
        if not isinstance(contract, dict):
            raise Unit01SliceError(f"response_contract_not_object:{row['asset_key']}")
        contract.update(
            {
                "lesson_id": str(row["lesson_id"]),
                "asset_key": str(row["asset_key"]),
                "role": str(row["role"]),
                "capture_enabled": bool(row["capture_enabled"]),
            }
        )
        contracts[str(row["asset_key"])] = contract
    return contracts


def _role_matches(asset: Mapping[str, Any], expected: str) -> bool:
    return str(asset.get("role") or "").upper() == expected


def _accepted_values(contract: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("accepted_texts", "accepted_sequence"):
        raw = contract.get(key)
        if isinstance(raw, list):
            if key == "accepted_sequence":
                values.append(" ".join(str(row) for row in raw))
            else:
                values.extend(str(row) for row in raw)
    return [value.strip() for value in values if value.strip()]


def assign_reading_specs(
    assets: Sequence[Mapping[str, Any]],
    contracts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    """Match Reading specs to existing asset identities and hidden scoring answers."""
    if len(assets) != EXPECTED_LANE_COUNTS["READING"]:
        raise Unit01SliceError("unit01_reading_asset_count_not_4")
    unassigned = list(READING_SPECS)
    assignments: dict[str, Mapping[str, Any]] = {}
    for asset in assets:
        key = str(asset.get("asset_key") or "")
        contract = contracts.get(key)
        if not key or not isinstance(contract, Mapping):
            raise Unit01SliceError(f"reading_contract_missing:{key}")
        accepted = {value.casefold() for value in _accepted_values(contract)}
        matches = [
            spec
            for spec in unassigned
            if _role_matches(asset, str(spec["role"]))
            and str(spec["accepted_text"]).casefold() in accepted
        ]
        if len(matches) != 1:
            raise Unit01SliceError(f"reading_spec_match_invalid:{key}:{len(matches)}")
        spec = matches[0]
        assignments[key] = spec
        unassigned.remove(spec)
    if unassigned:
        raise Unit01SliceError("reading_specs_unassigned")
    return assignments


def writing_spec_for_contract(
    *,
    asset: Mapping[str, Any],
    contract: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    """Create a contextual prompt that preserves the existing M6 answer contract."""
    mode = str(contract.get("scoring_mode") or "")
    role = str(asset.get("role") or "").upper()
    values = _accepted_values(contract)
    if mode == "EXACT_SEQUENCE" and values:
        target = values[0]
        tokens = list(contract.get("accepted_sequence") or target.split())
        return {
            "spec_id": f"M01B-W{index:02d}",
            "prompt": "Put the supplied words in order to name the known classroom object.",
            "support": f"Words: {' / '.join(str(row) for row in reversed(tokens))}",
            "model": None,
            "writing_stage": "CONTROLLED_SEQUENCE",
        }
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"} and values:
        target = values[0]
        clue = "Copy the matching noun phrase from the passage."
        folded = target.casefold()
        if "cat" in folded:
            clue = "Find the noun phrase about the animal near the door."
        elif "book" in folded:
            clue = "Find the noun phrase for the known object on the desk."
        elif "apple" in folded:
            clue = "Find the noun phrase for the fruit in the bag."
        return {
            "spec_id": f"M01B-W{index:02d}",
            "prompt": "Write the exact noun phrase from the passage that matches this item.",
            "support": clue,
            "model": None,
            "writing_stage": "CONTROLLED_PHRASE" if role == "PRD" else "CONTROLLED_CHECKPOINT",
        }
    if mode == "FEATURE_RUBRIC":
        prompt = (
            "Write one complete A1 sentence about Mia's classroom. "
            "Use a, an, or the correctly."
        )
        if role == "CHK":
            prompt = (
                "Write one new complete sentence about the classroom passage. "
                "Use at least one correct article."
            )
        return {
            "spec_id": f"M01B-W{index:02d}",
            "prompt": prompt,
            "support": "You may use: bag, book, apple, cat, door, desk.",
            "model": "There is an apple in the bag.",
            "writing_stage": "GUIDED_CONTEXTUAL_SENTENCE" if role == "PRD" else "CONTEXTUAL_CHECKPOINT",
        }
    raise Unit01SliceError(f"writing_scoring_mode_unsupported:{asset.get('asset_key')}:{mode}")


def overlay_bundles(
    *,
    bundles: Mapping[str, Mapping[str, Any]],
    approved: Mapping[str, Any],
    contracts: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Overlay only Unit 01 learner payloads while preserving identities/contracts."""
    result = deepcopy(dict(bundles))
    if set(LESSON_IDS.values()) - set(result):
        raise Unit01SliceError("unit01_lesson_bundle_missing")
    reading_assets = result[LESSON_IDS["READING"]].get("assets", [])
    writing_assets = result[LESSON_IDS["WRITING"]].get("assets", [])
    speaking_assets = result[LESSON_IDS["SPEAKING"]].get("assets", [])
    if not all(isinstance(rows, list) for rows in (reading_assets, writing_assets, speaking_assets)):
        raise Unit01SliceError("unit01_asset_rows_invalid")

    reading_assignments = assign_reading_specs(reading_assets, contracts)
    for asset in reading_assets:
        key = str(asset["asset_key"])
        spec = reading_assignments[key]
        payload = asset.get("learner_payload")
        if not isinstance(payload, dict):
            raise Unit01SliceError(f"learner_payload_invalid:{key}")
        payload.update(
            {
                "prompt": spec["prompt"],
                "stimulus": {"title": PASSAGE_TITLE, "body": PASSAGE, "kind": "CONNECTED_PASSAGE"},
                "support_text": spec["support"],
                "content_identity": {
                    "approved_content_sha256": approved["artifact_sha256"],
                    "spec_id": spec["spec_id"],
                    "unit_id": UNIT_ID,
                },
                "source_roles": {
                    "ket_asset_body": "SKILL_STRUCTURE_AND_TASK_SHAPE_REFERENCE",
                    "raz": "SOURCE_GROUNDING_CONTEXT_ONLY_NO_RAW_TEXT_COPY",
                },
            }
        )

    if len(writing_assets) != EXPECTED_LANE_COUNTS["WRITING"]:
        raise Unit01SliceError("unit01_writing_asset_count_not_4")
    for index, asset in enumerate(sorted(writing_assets, key=lambda row: str(row["asset_key"])), start=1):
        key = str(asset["asset_key"])
        contract = contracts.get(key)
        if not isinstance(contract, Mapping):
            raise Unit01SliceError(f"writing_contract_missing:{key}")
        spec = writing_spec_for_contract(asset=asset, contract=contract, index=index)
        payload = asset.get("learner_payload")
        if not isinstance(payload, dict):
            raise Unit01SliceError(f"learner_payload_invalid:{key}")
        payload.update(
            {
                "prompt": spec["prompt"],
                "stimulus": {"title": PASSAGE_TITLE, "body": PASSAGE, "kind": "SHARED_READING_CONTEXT"},
                "support_text": spec["support"],
                "writing_stage": spec["writing_stage"],
                "content_identity": {
                    "approved_content_sha256": approved["artifact_sha256"],
                    "spec_id": spec["spec_id"],
                    "unit_id": UNIT_ID,
                },
            }
        )
        if spec["model"]:
            payload["model_language"] = spec["model"]
        else:
            payload.pop("model_language", None)

    if len(speaking_assets) != EXPECTED_LANE_COUNTS["SPEAKING"]:
        raise Unit01SliceError("unit01_speaking_asset_count_not_3")
    for asset, spec in zip(
        sorted(speaking_assets, key=lambda row: str(row["asset_key"])),
        SPEAKING_SPECS,
        strict=True,
    ):
        key = str(asset["asset_key"])
        payload = asset.get("learner_payload")
        if not isinstance(payload, dict):
            raise Unit01SliceError(f"learner_payload_invalid:{key}")
        payload.update(
            {
                "prompt": spec["prompt"],
                "stimulus": {"title": PASSAGE_TITLE, "body": PASSAGE, "kind": "SHARED_ORAL_CONTEXT"},
                "model_language": spec["model"],
                "sentence_frame": spec["frame"],
                "communicative_goal": spec["communicative_goal"],
                "content_identity": {
                    "approved_content_sha256": approved["artifact_sha256"],
                    "spec_id": spec["spec_id"],
                    "unit_id": UNIT_ID,
                },
                "response_capture_enabled": False,
                "recording_capture_required": False,
                "evidence_policy": "EXPOSURE_ONLY_NO_SCORING_NO_MASTERY",
            }
        )
    return result


def patch_static(source_root: Path, target_root: Path) -> None:
    """Copy the current secure UI and render stimulus/support fields."""
    source_root = Path(source_root)
    target_root = Path(target_root)
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)
    app_path = target_root / "app.js"
    css_path = target_root / "styles.css"
    app = app_path.read_text(encoding="utf-8")
    marker = "card.append(prompt);const options=asset.learner_payload.options||[];"
    replacement = (
        "card.append(prompt);"
        "const stimulus=asset.learner_payload.stimulus;"
        "if(stimulus&&stimulus.body){const block=document.createElement('section');"
        "block.className='stimulus';const title=document.createElement('h4');"
        "text(title,stimulus.title||'閱讀內容');const body=document.createElement('p');"
        "text(body,stimulus.body);block.append(title,body);card.append(block);}"
        "const support=asset.learner_payload.support_text;"
        "if(support){const note=document.createElement('p');note.className='support-text';"
        "text(note,support);card.append(note);}"
        "const model=asset.learner_payload.model_language;"
        "if(model){const note=document.createElement('p');note.className='model-language';"
        "text(note,`示例：${model}`);card.append(note);}"
        "const frame=asset.learner_payload.sentence_frame;"
        "if(frame){const note=document.createElement('p');note.className='sentence-frame';"
        "text(note,`句型：${frame}`);card.append(note);}"
        "const options=asset.learner_payload.options||[];"
    )
    if marker not in app:
        raise Unit01SliceError("learner_static_render_marker_missing")
    app_path.write_text(app.replace(marker, replacement, 1), encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    css += (
        "\n.stimulus{margin:.75rem 0;padding:1rem;border-left:4px solid #40556b;"
        "background:#f7f9fb}.stimulus h4{margin:0 0 .5rem}.stimulus p{line-height:1.65;"
        "margin:0}.support-text,.model-language,.sentence-frame{padding:.6rem .75rem;"
        "background:#f2f5f7;border-radius:8px}\n"
    )
    css_path.write_text(css, encoding="utf-8")


def materialize(*, s17_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create an isolated V1.1 Unit 01 runtime overlay over the S17 authority."""
    (
        s17_receipt,
        database,
        auth_state,
        bundles,
        sequence,
        graph_path,
        state_root,
        secure_static,
    ) = s17._load_runtime(Path(s17_receipt_path).resolve())
    if len(bundles) != 72 or len(sequence) != 24:
        raise Unit01SliceError("s17_runtime_denominator_invalid")

    source_bindings = {
        "s17_receipt_sha256": digest(s17_receipt),
        "grammar_unit_id": UNIT_ID,
        "lesson_ids": dict(LESSON_IDS),
        "existing_bundle_digest": digest(bundles),
        "operator_decision_ref": DECISION_REF,
    }
    candidate = build_candidate(source_bindings)
    approved = admit_candidate(candidate)
    projections = build_projections(approved)
    contracts = _contracts_for_lessons(database, list(LESSON_IDS.values()))
    overlaid = overlay_bundles(
        bundles=bundles,
        approved=approved,
        contracts=contracts,
    )

    root = Path(output_root).resolve() / "unit01_cross_skill_vertical_slice"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    artifact_root = root / "content"
    runtime_root = root / "runtime"
    artifact_root.mkdir()
    runtime_root.mkdir()
    candidate_path = artifact_root / "unit01.candidate.private.json"
    approved_path = artifact_root / "unit01.approved.private.json"
    projections_path = artifact_root / "unit01.projections.private.json"
    bundles_path = runtime_root / "bundles.private.json"
    static_root = runtime_root / "secure_static"
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(projections_path, projections, private=True)
    write_json(bundles_path, overlaid, private=True)
    patch_static(secure_static, static_root)

    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "product_version": PRODUCT_VERSION,
        "source_identity": {
            "s17_receipt_sha256": digest(s17_receipt),
            "source_bundle_sha256": digest(bundles),
            "approved_content_sha256": approved["artifact_sha256"],
        },
        "runtime_outputs": {
            "root": str(root),
            "source_s17_receipt_path": str(Path(s17_receipt_path).resolve()),
            "source_database_path": str(database),
            "source_auth_state_path": str(auth_state),
            "source_graph_path": str(graph_path),
            "source_state_root": str(state_root),
            "bundles_path": str(bundles_path),
            "secure_static_root": str(static_root),
            "candidate_path": str(candidate_path),
            "approved_path": str(approved_path),
            "projections_path": str(projections_path),
        },
        "milestone_summary": {
            "unit_id": UNIT_ID,
            "modified_lesson_count": 3,
            "reading_activity_count": 4,
            "writing_activity_count": 4,
            "speaking_practice_count": 3,
            "real_reading_passage_present": True,
            "shared_cross_skill_context_present": True,
            "existing_asset_identities_preserved": True,
            "existing_scoring_contracts_preserved": True,
            "other_unit_bundles_preserved": True,
        },
        "boundaries": {
            "parallel_curriculum_created": False,
            "learner_state_migrated": False,
            "learner_state_authority_changed": False,
            "scoring_authority_changed": False,
            "dashboard_authority_changed": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "product_version": PRODUCT_VERSION,
        "milestone_summary": deepcopy(receipt_core["milestone_summary"]),
        "boundaries": deepcopy(receipt_core["boundaries"]),
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    return receipt, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    build = command.add_parser("materialize")
    build.add_argument("--s17", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt, safe = materialize(
            s17_receipt_path=args.s17,
            output_root=args.output.parent,
        )
        from ulga.validators import (
            validate_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as validator,
        )

        report = validator.validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
        )
        if report["error_count"]:
            raise Unit01SliceError(
                "validation_failed:" + "|".join(report["errors"])
            )
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        Unit01SliceError,
        policy_artifact.ContentPolicyBuildError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
