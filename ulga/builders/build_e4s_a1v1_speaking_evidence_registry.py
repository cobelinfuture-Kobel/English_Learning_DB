#!/usr/bin/env python3
"""Assemble browser-downloaded Speaking captures into the full private M06 evidence registry.

The local recorder intentionally exports a small capture draft and an audio file.
This helper verifies those inputs, copies audio under the approved `.local` capture
root, computes integrity metadata, materializes the complete fail-closed attempt
contract, and runs the existing M06 private review-bank builder.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_speaking_v1 as speaking  # noqa: E402

TASK_ID = "E4S-A1V1-M06_SpeakingV1BrowserEvidenceRegistryFullFix"
PASS_STATUS = "PASS_M06_BROWSER_EVIDENCE_REGISTRY_MATERIALIZED"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/speaking/m06"
MIME_BY_SUFFIX = {
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
}


class EvidenceRegistryError(ValueError):
    """Fail-closed browser-capture assembly error."""


def _read_draft(path: Path) -> dict[str, Any]:
    try:
        value = speaking.read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise EvidenceRegistryError(f"capture_draft_unreadable:{path}:{exc}") from exc
    required = {"shared_item_id", "activity_id", "attempt_sequence", "manual_transcript"}
    missing = sorted(required - set(value))
    if missing:
        raise EvidenceRegistryError(
            f"capture_draft_fields_missing:{path.name}:{','.join(missing)}"
        )
    if set(value) - required:
        raise EvidenceRegistryError(
            f"capture_draft_unknown_fields:{path.name}:"
            + ",".join(sorted(set(value) - required))
        )
    if not isinstance(value["shared_item_id"], str) or not value["shared_item_id"]:
        raise EvidenceRegistryError(f"capture_draft_shared_item_invalid:{path.name}")
    if not isinstance(value["activity_id"], str) or not value["activity_id"]:
        raise EvidenceRegistryError(f"capture_draft_activity_invalid:{path.name}")
    if not isinstance(value["attempt_sequence"], int) or value["attempt_sequence"] < 1:
        raise EvidenceRegistryError(f"capture_draft_attempt_sequence_invalid:{path.name}")
    if value["manual_transcript"] is not None and not isinstance(
        value["manual_transcript"], str
    ):
        raise EvidenceRegistryError(f"capture_draft_manual_transcript_invalid:{path.name}")
    return value


def _queue_index(output_root: Path) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    queue = speaking.read_json(output_root / "speaking_capture_queue.private.json")
    rows = queue.get("items")
    if not isinstance(rows, list) or len(rows) != 96:
        raise EvidenceRegistryError("capture_queue_not_96")
    index = {str(row.get("shared_item_id")): row for row in rows if isinstance(row, Mapping)}
    if len(index) != 96:
        raise EvidenceRegistryError("capture_queue_duplicate_or_missing_identity")
    return queue, index


def _find_audio(audio_source_dir: Path, activity_id: str) -> Path:
    if not audio_source_dir.is_dir():
        raise EvidenceRegistryError(f"audio_source_dir_missing:{audio_source_dir}")
    matches = sorted(
        path
        for path in audio_source_dir.iterdir()
        if path.is_file()
        and path.stem == activity_id
        and path.suffix.casefold() in MIME_BY_SUFFIX
    )
    if not matches:
        raise EvidenceRegistryError(f"capture_audio_missing:{activity_id}")
    if len(matches) != 1:
        raise EvidenceRegistryError(f"capture_audio_ambiguous:{activity_id}:{len(matches)}")
    return matches[0]


def _copy_audio(output_root: Path, source: Path) -> tuple[Path, str]:
    capture_root = output_root / "captures"
    capture_root.mkdir(parents=True, exist_ok=True)
    destination = capture_root / source.name
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)
    relative = destination.relative_to(output_root).as_posix()
    speaking.inspect_capture(destination, MIME_BY_SUFFIX[destination.suffix.casefold()])
    return destination, relative


def _base_registry(output_root: Path, queue: Mapping[str, Any]) -> dict[str, Any]:
    existing = output_root / "speaking_evidence_input.private.json"
    template = output_root / "speaking_evidence_input.template.json"
    path = existing if existing.exists() else template
    registry = speaking.read_json(path)
    if registry.get("capture_queue_sha256") != speaking.sha256_value(queue):
        raise EvidenceRegistryError("existing_registry_queue_hash_drift")
    attempts = registry.get("attempts")
    if not isinstance(attempts, list):
        raise EvidenceRegistryError("existing_registry_attempts_not_array")
    return registry


def _attempt_from_draft(
    draft: Mapping[str, Any],
    *,
    learner_ref: str,
    audio_path: Path,
    audio_relative_path: str,
) -> dict[str, Any]:
    manual = draft.get("manual_transcript")
    manual_text = manual.strip() if isinstance(manual, str) else ""
    return {
        "evidence_id": (
            f"M06_EVIDENCE:{draft['activity_id']}:{draft['attempt_sequence']}"
        ),
        "shared_item_id": draft["shared_item_id"],
        "activity_id": draft["activity_id"],
        "learner_ref": learner_ref,
        "attempt_sequence": draft["attempt_sequence"],
        "audio_relative_path": audio_relative_path,
        "audio_sha256": speaking.sha256_file(audio_path),
        "audio_size_bytes": audio_path.stat().st_size,
        "audio_mime_type": MIME_BY_SUFFIX[audio_path.suffix.casefold()],
        "manual_transcript_status": "PROVIDED" if manual_text else "NOT_PROVIDED",
        "manual_transcript": manual_text if manual_text else None,
        "asr_status": "DISABLED",
        "asr_transcript": None,
        "review_decision": "PENDING",
        "reviewer_id": None,
        "reviewed_at": None,
        "grammar_score": None,
        "task_fulfillment_score": None,
        "failure_domain": "none",
        "grammar_error_tags": [],
        "operator_notes": None,
    }


def assemble_registry(
    output_root: Path,
    capture_drafts: list[Path],
    audio_source_dir: Path,
    learner_ref: str,
) -> dict[str, Any]:
    output_root = speaking._safe_output_root(output_root)
    if not learner_ref.strip():
        raise EvidenceRegistryError("learner_ref_empty")
    if not capture_drafts:
        raise EvidenceRegistryError("capture_drafts_empty")

    queue, queue_index = _queue_index(output_root)
    registry = _base_registry(output_root, queue)
    existing_attempts = list(registry["attempts"])
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    evidence_ids: set[str] = set()
    for row in existing_attempts:
        if not isinstance(row, dict):
            raise EvidenceRegistryError("existing_registry_row_not_object")
        key = (str(row.get("shared_item_id")), int(row.get("attempt_sequence", 0)))
        evidence_id = str(row.get("evidence_id"))
        if key in by_key or not evidence_id or evidence_id in evidence_ids:
            raise EvidenceRegistryError("existing_registry_duplicate_identity")
        by_key[key] = row
        evidence_ids.add(evidence_id)

    draft_identities: set[tuple[str, int]] = set()
    imported = 0
    for draft_path in capture_drafts:
        draft = _read_draft(draft_path)
        shared_id = draft["shared_item_id"]
        expected = queue_index.get(shared_id)
        if expected is None:
            raise EvidenceRegistryError(f"capture_draft_unknown_shared_item:{shared_id}")
        if draft["activity_id"] != expected.get("activity_id"):
            raise EvidenceRegistryError(f"capture_draft_activity_join_drift:{shared_id}")
        key = (shared_id, draft["attempt_sequence"])
        if key in draft_identities:
            raise EvidenceRegistryError(
                f"capture_draft_duplicate_identity:{shared_id}:{draft['attempt_sequence']}"
            )
        draft_identities.add(key)

        source_audio = _find_audio(audio_source_dir, draft["activity_id"])
        destination, relative = _copy_audio(output_root, source_audio)
        attempt = _attempt_from_draft(
            draft,
            learner_ref=learner_ref,
            audio_path=destination,
            audio_relative_path=relative,
        )
        if key in by_key:
            if by_key[key] != attempt:
                raise EvidenceRegistryError(
                    f"existing_attempt_conflict:{shared_id}:{draft['attempt_sequence']}"
                )
            continue
        if attempt["evidence_id"] in evidence_ids:
            raise EvidenceRegistryError(
                f"evidence_id_conflict:{attempt['evidence_id']}"
            )
        by_key[key] = attempt
        evidence_ids.add(attempt["evidence_id"])
        imported += 1

    attempts = sorted(
        by_key.values(),
        key=lambda row: (
            str(row["activity_id"]),
            int(row["attempt_sequence"]),
            str(row["evidence_id"]),
        ),
    )
    registry = {
        "task_id": speaking.TASK_ID,
        "schema_version": "e4s.a1v1.speaking_evidence_input.v1",
        "private_local_only": True,
        "capture_queue_sha256": speaking.sha256_value(queue),
        "attempts": attempts,
    }
    registry_path = output_root / "speaking_evidence_input.private.json"
    speaking.write_json_atomic(registry_path, registry)
    materialized = speaking.materialize_evidence(output_root, registry_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "imported_attempt_count": imported,
        "total_attempt_count": len(attempts),
        "captured_audio_count": materialized["bank"]["evidence_count"],
        "reviewed_item_count": materialized["bank"]["reviewed_count"],
        "safe_validation_status": materialized["safe_report"]["validation_status"],
        "next_resume_task": speaking.NEXT_RESUME_TASK,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--capture-draft", type=Path, nargs="+", required=True)
    parser.add_argument("--audio-source-dir", type=Path, required=True)
    parser.add_argument("--learner-ref", default="learner-local-01")
    args = parser.parse_args(argv)
    try:
        result = assemble_registry(
            args.output_root,
            args.capture_draft,
            args.audio_source_dir,
            args.learner_ref,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (EvidenceRegistryError, speaking.SpeakingBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
