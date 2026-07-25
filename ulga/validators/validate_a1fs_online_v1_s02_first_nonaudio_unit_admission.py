#!/usr/bin/env python3
"""Independent validator for A1FS-ONLINE-V1 S02 first non-audio unit admission."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"not_object:{path}")
    return value


def _append(errors: list[str], condition: bool, code: str) -> None:
    if not condition:
        errors.append(code)


def _m03_index(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = artifact.get("shared_items", [])
    return {
        str(row.get("shared_item_id") or ""): row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("shared_item_id") or "")
    }


def validate_artifact(
    artifact: Mapping[str, Any],
    cp01_artifact: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    _append(errors, artifact.get("task_id") == s02.TASK_ID, "task_id_invalid")
    _append(errors, artifact.get("program_id") == s02.PROGRAM_ID, "program_id_invalid")
    _append(errors, artifact.get("schema_version") == s02.SCHEMA_VERSION, "schema_version_invalid")
    _append(errors, artifact.get("validation_status") == s02.PASS_STATUS, "validation_status_invalid")
    _append(errors, artifact.get("scope") == "A1_A1_PLUS_ONLY", "scope_invalid")
    _append(errors, artifact.get("release_profile") == s02.RELEASE_PROFILE, "release_profile_invalid")
    _append(errors, artifact.get("stop_reason") == "NONE", "stop_reason_invalid")
    _append(errors, artifact.get("next_short_step") == s02.NEXT_SHORT_STEP, "next_short_step_invalid")

    core = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    _append(errors, artifact.get("artifact_sha256") == s02.digest(core), "artifact_digest_invalid")

    source = artifact.get("source_identity", {})
    _append(errors, source.get("cp01_task_id") == cp01_artifact.get("task_id"), "cp01_task_binding_invalid")
    _append(errors, source.get("cp01_sha256") == s02.digest(cp01_artifact), "cp01_digest_binding_invalid")
    _append(errors, source.get("cp04_task_id") == cp04_artifact.get("task_id"), "cp04_task_binding_invalid")
    _append(errors, source.get("cp04_sha256") == s02.digest(cp04_artifact), "cp04_digest_binding_invalid")
    _append(errors, source.get("m03_task_id") == m03_artifact.get("task_id"), "m03_task_binding_invalid")
    _append(errors, source.get("m03_sha256") == s02.digest(m03_artifact), "m03_digest_binding_invalid")

    selection = artifact.get("selection_contract", {})
    _append(errors, selection.get("course_container") == "EXISTING_24_CANONICAL_UNITS_ONLY", "course_container_invalid")
    _append(errors, selection.get("required_prelaunch_lanes") == list(s02.REQUIRED_LANES), "required_lane_contract_invalid")
    _append(errors, selection.get("audio_deferred_lanes") == list(s02.AUDIO_DEFERRED_LANES), "audio_deferred_lane_contract_invalid")
    _append(errors, selection.get("new_unit_creation_allowed") is False, "new_unit_creation_not_blocked")
    _append(errors, selection.get("listening_without_playable_audio_allowed") is False, "text_only_listening_not_blocked")
    _append(errors, selection.get("speaking_capture_or_scoring_claim_allowed") is False, "speaking_claim_not_blocked")

    selected = artifact.get("selected_unit")
    if not isinstance(selected, Mapping):
        errors.append("selected_unit_missing")
        selected = {}
    grammar_id = str(selected.get("grammar_unit_id") or "")
    learning_id = str(selected.get("learning_unit_id") or "")

    cp01_rows = {
        str(row.get("grammar_unit_id") or ""): row
        for row in cp01_artifact.get("learning_units", [])
        if isinstance(row, Mapping)
    }
    cp04_rows = {
        str(row.get("grammar_unit_id") or ""): row
        for row in cp04_artifact.get("learning_units", [])
        if isinstance(row, Mapping)
    }
    curriculum = cp01_rows.get(grammar_id)
    envelope = cp04_rows.get(grammar_id)
    _append(errors, curriculum is not None and envelope is not None, "selected_unit_not_in_existing_24")
    if curriculum is not None and envelope is not None:
        _append(errors, curriculum.get("learning_unit_id") == learning_id, "selected_learning_unit_identity_invalid")
        _append(errors, envelope.get("learning_unit_id") == learning_id, "selected_cp04_identity_invalid")
        _append(errors, selected.get("sequence_index") == curriculum.get("sequence_index"), "selected_sequence_invalid")
        _append(errors, selected.get("canonical_egp_row_ids") == curriculum.get("canonical_egp_row_ids"), "selected_egp_rows_invalid")
        _append(errors, curriculum.get("prerequisite_unit_ids") == [], "selected_unit_not_prerequisite_free")
        _append(errors, selected.get("prerequisite_unit_ids") == [], "selected_prerequisite_projection_invalid")

    lanes = selected.get("admitted_lanes", {}) if isinstance(selected, Mapping) else {}
    _append(errors, isinstance(lanes, Mapping) and set(lanes) == set(s02.REQUIRED_LANES), "admitted_lane_set_invalid")
    item_index = _m03_index(m03_artifact)
    all_ids: list[str] = []
    for skill in s02.REQUIRED_LANES:
        lane = lanes.get(skill, {}) if isinstance(lanes, Mapping) else {}
        ids = lane.get("item_ids")
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            errors.append(f"lane_item_ids_invalid:{skill}")
            ids = []
        _append(errors, lane.get("item_count") == len(ids), f"lane_item_count_invalid:{skill}")
        _append(errors, lane.get("admission_status") == "ADMITTED_FOR_AUDIO_DEFERRED_ONLINE_RELEASE", f"lane_admission_status_invalid:{skill}")
        if skill == "speaking":
            _append(errors, lane.get("delivery_mode") == "ORAL_PRACTICE_CARD_NO_CAPTURE", "speaking_delivery_mode_invalid")
            _append(errors, lane.get("evidence_policy") == "NO_SCORING_NO_MASTERY_EVIDENCE", "speaking_evidence_policy_invalid")
        else:
            _append(errors, lane.get("delivery_mode") == "INTERACTIVE_TEXT_ITEM", f"text_delivery_mode_invalid:{skill}")
        for item_id in ids:
            item = item_index.get(str(item_id))
            if item is None:
                errors.append(f"m03_item_missing:{skill}:{item_id}")
                continue
            _append(errors, item.get("grammar_unit_id") == grammar_id, f"item_unit_mismatch:{skill}:{item_id}")
            _append(errors, item.get("skill") == skill, f"item_skill_mismatch:{skill}:{item_id}")
            if skill == "speaking":
                _append(errors, item.get("item_role") == "practice", f"speaking_assessment_admitted:{item_id}")
        all_ids.extend(str(item_id) for item_id in ids)
    _append(errors, len(all_ids) == len(set(all_ids)), "admitted_item_identity_collision")

    if envelope is not None:
        ready_refs: dict[str, set[str]] = {"reading": set(), "writing": set()}
        for row in envelope.get("exercise_candidates", []):
            if not isinstance(row, Mapping):
                continue
            lanes_value = row.get("target_skill_lanes")
            if (
                row.get("source_kind") == "M11B_REVIEWED_SHARED_ITEM"
                and row.get("candidate_state") == "READY_FOR_PRIVATE_POPULATION"
                and isinstance(lanes_value, list)
                and len(lanes_value) == 1
                and lanes_value[0] in ready_refs
            ):
                ready_refs[lanes_value[0]].add(str(row.get("source_ref") or ""))
        for skill in ("reading", "writing"):
            ids = set(lanes.get(skill, {}).get("item_ids", [])) if isinstance(lanes, Mapping) else set()
            _append(errors, ids <= ready_refs[skill], f"unreviewed_cp04_item_admitted:{skill}")

    deferred = selected.get("deferred_lanes", {}) if isinstance(selected, Mapping) else {}
    listening = deferred.get("listening", {}) if isinstance(deferred, Mapping) else {}
    speaking_assessment = deferred.get("speaking_assessment", {}) if isinstance(deferred, Mapping) else {}
    _append(errors, listening.get("status") == "DEFERRED_POST_LAUNCH_AUDIO", "listening_not_deferred")
    _append(errors, listening.get("item_ids") == [], "listening_item_admitted")
    _append(errors, speaking_assessment.get("status") == "DEFERRED_POST_LAUNCH_AUDIO", "speaking_assessment_not_deferred")
    for item_id in speaking_assessment.get("item_ids", []):
        item = item_index.get(str(item_id))
        _append(errors, item is not None and item.get("skill") == "speaking" and item.get("item_role") == "assessment", f"speaking_deferred_identity_invalid:{item_id}")

    summary = artifact.get("admission_summary", {})
    _append(errors, summary.get("admitted_unit_count") == 1, "admitted_unit_count_invalid")
    _append(errors, summary.get("reading_item_count") == len(lanes.get("reading", {}).get("item_ids", [])), "reading_summary_invalid")
    _append(errors, summary.get("writing_item_count") == len(lanes.get("writing", {}).get("item_ids", [])), "writing_summary_invalid")
    _append(errors, summary.get("speaking_practice_card_count") == len(lanes.get("speaking", {}).get("item_ids", [])), "speaking_summary_invalid")
    _append(errors, summary.get("listening_item_count") == 0, "listening_summary_not_zero")
    _append(errors, summary.get("speaking_assessment_item_count") == 0, "speaking_assessment_summary_not_zero")
    _append(errors, summary.get("admitted_nonaudio_item_count") == len(all_ids), "admitted_item_total_invalid")

    boundaries = artifact.get("claim_boundaries", {})
    for key in (
        "canonical_unit_identity_changed",
        "new_curriculum_created",
        "new_learner_content_authored",
        "listening_complete",
        "speaking_recording_complete",
        "speaking_assessment_evidence_claimed",
        "complete_four_skill_product_claimed",
        "online_usable_claimed",
        "learner_mastery_claimed",
        "retention_confirmed",
        "a2_a2plus_in_scope",
        "a2_unlocked",
    ):
        _append(errors, boundaries.get(key) is False, f"claim_boundary_invalid:{key}")
    _append(errors, artifact.get("product_status") == "INCOMPLETE_NOT_ONLINE_USABLE", "product_status_invalid")

    try:
        s02.safe_scan(artifact)
    except s02.FirstUnitAdmissionError as exc:
        errors.append(str(exc))

    return {
        "task_id": s02.TASK_ID,
        "schema_version": s02.SCHEMA_VERSION,
        "validation_status": s02.PASS_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S02_FIRST_NONAUDIO_UNIT_ADMISSION",
        "error_count": len(errors),
        "errors": errors,
        "selected_learning_unit_id": learning_id or None,
        "selected_grammar_unit_id": grammar_id or None,
        "admitted_nonaudio_item_count": len(all_ids),
        "listening_item_count": int(summary.get("listening_item_count") or 0),
        "next_short_step": s02.NEXT_SHORT_STEP if not errors else s02.TASK_ID,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--cp01", type=Path, default=s02.CP01_PATH)
    parser.add_argument("--cp04", type=Path, default=s02.CP04_PATH)
    parser.add_argument("--m03", type=Path, default=s02.M03_PATH)
    args = parser.parse_args(argv)
    try:
        report = validate_artifact(
            _read(args.artifact),
            _read(args.cp01),
            _read(args.cp04),
            _read(args.m03),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "task_id": s02.TASK_ID,
            "validation_status": "FAIL_A1FS_ONLINE_V1_S02_FIRST_NONAUDIO_UNIT_ADMISSION",
            "error_count": 1,
            "errors": [f"source_unreadable:{exc}"],
            "next_short_step": s02.TASK_ID,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
