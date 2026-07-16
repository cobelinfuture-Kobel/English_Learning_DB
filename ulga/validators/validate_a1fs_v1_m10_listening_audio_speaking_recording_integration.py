#!/usr/bin/env python3
"""Validate A1FS V1 M10 private WAV media registry and manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import wave
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M10_ListeningAudioAndSpeakingRecordingIntegration"
STATUS = "PASS_A1FS_V1_M10_LISTENING_AUDIO_SPEAKING_RECORDING_INTEGRATION"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def validate(database: Path, manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"manifest_unreadable:{exc}"]}
    if manifest.get("task_id") != TASK_ID or manifest.get("validation_status") != STATUS:
        errors.append("manifest_identity_invalid")
    expected_boundaries = {
        "a2_media_enabled": False,
        "public_upload": False,
        "media_committed_to_repository": False,
        "human_pilot_claimed": False,
    }
    if manifest.get("claim_boundaries") != expected_boundaries:
        errors.append("claim_boundaries_invalid")
    root = Path(manifest.get("media_root", "")).resolve()
    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        connection = None
        errors.append(f"database_unreadable:{exc}")
    if connection:
        metadata = dict(connection.execute("SELECT key,value FROM m10_metadata"))
        if metadata.get("validation_status") != STATUS or Path(metadata.get("media_root", "")).resolve() != root:
            errors.append("m10_metadata_invalid")
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM private_media_assets ORDER BY media_kind,lesson_id,asset_key,attempt_id"
            )
        ]
        if rows != manifest.get("records"):
            errors.append("manifest_database_projection_drift")
        for row in rows:
            path = Path(row["stored_path"])
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
            except Exception:
                errors.append(f"media_outside_root:{row['media_id']}")
                continue
            if path.is_symlink() or not path.is_file():
                errors.append(f"media_file_invalid:{row['media_id']}")
                continue
            if os.name != "nt" and path.stat().st_mode & 0o077:
                errors.append(f"media_permissions_too_open:{row['media_id']}")
            raw = path.read_bytes()
            if digest(raw) != row["source_sha256"]:
                errors.append(f"media_digest_mismatch:{row['media_id']}")
            try:
                with wave.open(str(path), "rb") as wav_file:
                    actual = (
                        wav_file.getnchannels(),
                        wav_file.getframerate(),
                        wav_file.getsampwidth(),
                        wav_file.getnframes(),
                        round(wav_file.getnframes() * 1000 / wav_file.getframerate()),
                    )
            except Exception:
                errors.append(f"wav_unreadable:{row['media_id']}")
                continue
            expected = (
                row["channels"],
                row["sample_rate"],
                row["sample_width_bytes"],
                row["frame_count"],
                row["duration_ms"],
            )
            if actual != expected:
                errors.append(f"wav_metadata_drift:{row['media_id']}")
            asset = connection.execute(
                """SELECT a.role,l.skill,l.level FROM lesson_assets a
                JOIN lesson_catalog l USING(lesson_id) WHERE a.asset_key=?""",
                (row["asset_key"],),
            ).fetchone()
            if not asset or asset["level"] not in {"A1", "A1+"}:
                errors.append(f"asset_mapping_invalid:{row['media_id']}")
            elif row["media_kind"] == "LISTENING_AUDIO":
                if (
                    asset["skill"] != "LISTENING"
                    or asset["role"] != "AUD"
                    or row["learner_id"] is not None
                    or row["attempt_id"] is not None
                ):
                    errors.append(f"listening_mapping_invalid:{row['media_id']}")
            elif row["media_kind"] == "SPEAKING_RECORDING":
                attempt = connection.execute(
                    """SELECT a.learner_id,s.scoring_mode,s.outcome FROM response_attempts a
                    JOIN scoring_results s USING(attempt_id) WHERE a.attempt_id=?""",
                    (row["attempt_id"],),
                ).fetchone()
                if (
                    asset["skill"] != "SPEAKING"
                    or asset["role"] not in {"PRD", "XFR", "EVD"}
                    or not attempt
                    or attempt["learner_id"] != row["learner_id"]
                    or attempt["scoring_mode"] != "FEATURE_RUBRIC"
                    or not row["consent_granted"]
                ):
                    errors.append(f"recording_mapping_invalid:{row['media_id']}")
        required = connection.execute(
            """SELECT COUNT(*) FROM lesson_assets a JOIN lesson_catalog l USING(lesson_id)
            WHERE l.skill='LISTENING' AND l.level IN('A1','A1+') AND a.role='AUD'"""
        ).fetchone()[0]
        registered = connection.execute(
            "SELECT COUNT(DISTINCT asset_key) FROM private_media_assets WHERE media_kind='LISTENING_AUDIO'"
        ).fetchone()[0]
        expected_complete = required > 0 and required == registered
        expected_listening = {
            "required_aud_asset_count": required,
            "registered_aud_asset_count": registered,
            "complete": expected_complete,
        }
        if manifest.get("listening_audio") != expected_listening:
            errors.append("listening_completion_drift")
        speaking = manifest.get("speaking_recording", {})
        if (
            speaking.get("stt_enabled") is not False
            or speaking.get("automatic_scoring_enabled") is not False
            or speaking.get("human_review_only") is not True
            or speaking.get("consent_required") is not True
        ):
            errors.append("speaking_boundary_invalid")
        stored = connection.execute(
            "SELECT 1 FROM media_manifest_exports WHERE manifest_digest=?",
            (digest(manifest),),
        ).fetchone()
        if not stored:
            errors.append("manifest_export_receipt_missing")
        connection.close()
    return {
        "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M10_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "next_short_step": manifest.get("next_short_step") if not errors else TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.database, args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["error_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
