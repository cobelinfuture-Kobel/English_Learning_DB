#!/usr/bin/env python3
"""Register private WAV media for A1FS V1 listening and speaking evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-M10_ListeningAudioAndSpeakingRecordingIntegration"
SCHEMA_VERSION = "a1fs.v1.m10.private_media.v1"
STATUS = "PASS_A1FS_V1_M10_LISTENING_AUDIO_SPEAKING_RECORDING_INTEGRATION"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
M9_STATUS = "PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT"
NEXT_SHORT_STEP = "A1FS-V1-M11_HumanPilotExecutionAndEvidenceReview"
MAX_BYTES = 25 * 1024 * 1024
MIN_MS = 200
MAX_MS = 180000


class MediaIntegrationError(ValueError):
    """Fail-closed M10 error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def timestamp(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise MediaIntegrationError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except Exception as exc:
        raise MediaIntegrationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise MediaIntegrationError(f"{code}_not_object")
    return value, raw


def wav_info(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise MediaIntegrationError("media_symlink_forbidden")
    try:
        size = path.stat().st_size
        if size <= 0 or size > MAX_BYTES:
            raise MediaIntegrationError("media_size_invalid")
        with wave.open(str(path), "rb") as wav_file:
            if wav_file.getcomptype() != "NONE":
                raise MediaIntegrationError("compressed_wav_forbidden")
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()
    except (OSError, wave.Error, EOFError) as exc:
        raise MediaIntegrationError(f"wav_invalid:{exc}") from exc
    duration_ms = round(frame_count * 1000 / sample_rate) if sample_rate else 0
    if (
        channels not in {1, 2}
        or not 8000 <= sample_rate <= 48000
        or sample_width not in {1, 2, 3, 4}
        or not MIN_MS <= duration_ms <= MAX_MS
    ):
        raise MediaIntegrationError("wav_metadata_out_of_bounds")
    raw = path.read_bytes()
    return {
        "sha256": digest(raw),
        "size_bytes": size,
        "mime_type": "audio/wav",
        "channels": channels,
        "sample_rate": sample_rate,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_ms": duration_ms,
    }


def copy_private(source: Path, root: Path, kind: str, sha256: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    folder = root / kind.lower()
    folder.mkdir(exist_ok=True)
    os.chmod(folder, 0o700)
    target = folder / f"{sha256}.wav"
    if not target.exists():
        temporary = target.with_suffix(".tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    os.chmod(target, 0o600)
    if digest(target.read_bytes()) != sha256:
        raise MediaIntegrationError("stored_media_digest_mismatch")
    return target.resolve()


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


SQL = """
CREATE TABLE IF NOT EXISTS m10_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS private_media_assets(
  media_id TEXT PRIMARY KEY,
  media_kind TEXT NOT NULL CHECK(media_kind IN('LISTENING_AUDIO','SPEAKING_RECORDING')),
  learner_id TEXT,
  lesson_id TEXT NOT NULL,
  asset_key TEXT NOT NULL,
  attempt_id TEXT,
  source_sha256 TEXT NOT NULL,
  stored_path TEXT NOT NULL UNIQUE,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  channels INTEGER NOT NULL,
  sample_rate INTEGER NOT NULL,
  sample_width_bytes INTEGER NOT NULL,
  frame_count INTEGER NOT NULL,
  duration_ms INTEGER NOT NULL,
  consent_required INTEGER NOT NULL CHECK(consent_required IN(0,1)),
  consent_granted INTEGER NOT NULL CHECK(consent_granted IN(0,1)),
  created_at TEXT NOT NULL,
  media_digest TEXT NOT NULL UNIQUE,
  UNIQUE(media_kind,asset_key,attempt_id)
);
CREATE TABLE IF NOT EXISTS media_manifest_exports(
  export_id TEXT PRIMARY KEY,
  exported_at TEXT NOT NULL,
  manifest_digest TEXT NOT NULL UNIQUE
);
"""


class PrivateMediaRegistry:
    def __init__(self, *, database_path: Path, consumer_path: Path, media_root: Path):
        self.database_path = Path(database_path)
        self.consumer_path = Path(consumer_path)
        self.media_root = Path(media_root)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def sources(self) -> tuple[dict[str, Any], bytes]:
        consumer, raw = load(self.consumer_path, "consumer")
        if consumer.get("validation_status") != CONSUMER_STATUS:
            raise MediaIntegrationError("consumer_status_invalid")
        return consumer, raw

    def initialize(self) -> dict[str, Any]:
        _, raw = self.sources()
        with self.connect() as connection:
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            m9 = dict(connection.execute("SELECT key,value FROM m9_metadata"))
            if metadata.get("consumer_sha256") != digest(raw):
                raise MediaIntegrationError("database_consumer_binding_mismatch")
            if m9.get("validation_status") != M9_STATUS:
                raise MediaIntegrationError("m9_status_invalid")
            connection.executescript(SQL)
            values = {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": STATUS,
                "consumer_sha256": digest(raw),
                "media_root": str(self.media_root.resolve()),
                "stt_enabled": "false",
                "automatic_speaking_score_enabled": "false",
                "a2_media_enabled": "false",
                "next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO m10_metadata VALUES(?,?)", values.items())
            connection.commit()
        return {"validation_status": STATUS, "next_short_step": NEXT_SHORT_STEP}

    def asset(self, connection: sqlite3.Connection, asset_key: str) -> sqlite3.Row:
        row = connection.execute(
            """SELECT a.asset_key,a.asset_id,a.lesson_id,a.role,l.skill,l.level
            FROM lesson_assets a JOIN lesson_catalog l USING(lesson_id)
            WHERE a.asset_key=?""",
            (asset_key,),
        ).fetchone()
        if not row:
            raise MediaIntegrationError("asset_not_found")
        if row["level"] not in {"A1", "A1+"}:
            raise MediaIntegrationError("A2_MEDIA_LOCKED")
        return row

    def register_listening(
        self,
        *,
        asset_key: str,
        wav_path: Path,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        created_at = timestamp(created_at)
        info = wav_info(Path(wav_path))
        with self.connect() as connection:
            row = self.asset(connection, asset_key)
            if row["skill"] != "LISTENING" or row["role"] != "AUD":
                raise MediaIntegrationError("listening_audio_requires_aud_asset")
            stored = copy_private(Path(wav_path), self.media_root, "LISTENING_AUDIO", info["sha256"])
            core = {
                "media_kind": "LISTENING_AUDIO",
                "lesson_id": row["lesson_id"],
                "asset_key": asset_key,
                "source_sha256": info["sha256"],
                "stored_path": str(stored),
                "created_at": created_at,
            }
            media_id = f"M10_MEDIA:{digest(core)[:24]}"
            connection.execute(
                "INSERT OR REPLACE INTO private_media_assets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    media_id,
                    "LISTENING_AUDIO",
                    None,
                    row["lesson_id"],
                    asset_key,
                    None,
                    info["sha256"],
                    str(stored),
                    info["mime_type"],
                    info["size_bytes"],
                    info["channels"],
                    info["sample_rate"],
                    info["sample_width_bytes"],
                    info["frame_count"],
                    info["duration_ms"],
                    0,
                    0,
                    created_at,
                    digest({**core, **info}),
                ),
            )
            connection.commit()
        return {
            "validation_status": STATUS,
            "media_id": media_id,
            "asset_key": asset_key,
            "duration_ms": info["duration_ms"],
            "next_short_step": NEXT_SHORT_STEP,
        }

    def register_recording(
        self,
        *,
        learner_id: str,
        attempt_id: str,
        wav_path: Path,
        consent_granted: bool,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        if consent_granted is not True:
            raise MediaIntegrationError("speaking_recording_consent_required")
        created_at = timestamp(created_at)
        info = wav_info(Path(wav_path))
        with self.connect() as connection:
            attempt = connection.execute(
                """SELECT a.learner_id,a.lesson_id,a.asset_key,s.scoring_mode,s.outcome
                FROM response_attempts a JOIN scoring_results s USING(attempt_id)
                WHERE a.attempt_id=?""",
                (attempt_id,),
            ).fetchone()
            if not attempt:
                raise MediaIntegrationError("attempt_not_found")
            if attempt["learner_id"] != learner_id:
                raise MediaIntegrationError("attempt_learner_mismatch")
            row = self.asset(connection, attempt["asset_key"])
            if row["skill"] != "SPEAKING" or row["role"] not in {"PRD", "XFR", "EVD"}:
                raise MediaIntegrationError("recording_requires_productive_speaking_asset")
            if (
                attempt["scoring_mode"] != "FEATURE_RUBRIC"
                or attempt["outcome"] not in {
                    "PENDING_HUMAN_REVIEW",
                    "HUMAN_APPROVE",
                    "HUMAN_REJECT",
                    "HUMAN_DEFER",
                }
            ):
                raise MediaIntegrationError("recording_requires_human_review_scoring")
            stored = copy_private(Path(wav_path), self.media_root, "SPEAKING_RECORDING", info["sha256"])
            core = {
                "media_kind": "SPEAKING_RECORDING",
                "learner_id": learner_id,
                "lesson_id": attempt["lesson_id"],
                "asset_key": attempt["asset_key"],
                "attempt_id": attempt_id,
                "source_sha256": info["sha256"],
                "stored_path": str(stored),
                "created_at": created_at,
            }
            media_id = f"M10_MEDIA:{digest(core)[:24]}"
            connection.execute(
                "INSERT OR REPLACE INTO private_media_assets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    media_id,
                    "SPEAKING_RECORDING",
                    learner_id,
                    attempt["lesson_id"],
                    attempt["asset_key"],
                    attempt_id,
                    info["sha256"],
                    str(stored),
                    info["mime_type"],
                    info["size_bytes"],
                    info["channels"],
                    info["sample_rate"],
                    info["sample_width_bytes"],
                    info["frame_count"],
                    info["duration_ms"],
                    1,
                    1,
                    created_at,
                    digest({**core, **info, "consent_granted": True}),
                ),
            )
            connection.commit()
        return {
            "validation_status": STATUS,
            "media_id": media_id,
            "attempt_id": attempt_id,
            "human_review_required": True,
            "automatic_score_written": False,
            "next_short_step": NEXT_SHORT_STEP,
        }

    def export(self, *, output_root: Path, exported_at: str | None = None) -> dict[str, Any]:
        _, raw = self.sources()
        exported_at = timestamp(exported_at)
        with self.connect() as connection:
            records = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM private_media_assets ORDER BY media_kind,lesson_id,asset_key,attempt_id"
                )
            ]
            required = connection.execute(
                """SELECT COUNT(*) FROM lesson_assets a JOIN lesson_catalog l USING(lesson_id)
                WHERE l.skill='LISTENING' AND l.level IN('A1','A1+') AND a.role='AUD'"""
            ).fetchone()[0]
            registered = connection.execute(
                "SELECT COUNT(DISTINCT asset_key) FROM private_media_assets WHERE media_kind='LISTENING_AUDIO'"
            ).fetchone()[0]
        manifest = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": STATUS,
            "private_local_only": True,
            "consumer_sha256": digest(raw),
            "media_root": str(self.media_root.resolve()),
            "listening_audio": {
                "required_aud_asset_count": required,
                "registered_aud_asset_count": registered,
                "complete": required > 0 and required == registered,
            },
            "speaking_recording": {
                "capture_enabled": True,
                "recording_count": sum(row["media_kind"] == "SPEAKING_RECORDING" for row in records),
                "consent_required": True,
                "human_review_only": True,
                "stt_enabled": False,
                "automatic_scoring_enabled": False,
            },
            "records": records,
            "claim_boundaries": {
                "a2_media_enabled": False,
                "public_upload": False,
                "media_committed_to_repository": False,
                "human_pilot_claimed": False,
            },
            "next_short_step": NEXT_SHORT_STEP,
        }
        path = Path(output_root) / "a1fs_v1_m10_private_media_manifest.json"
        write_private(path, manifest)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO media_manifest_exports VALUES(?,?,?)",
                (str(uuid.uuid4()), exported_at, digest(manifest)),
            )
            connection.commit()
        return {
            "validation_status": STATUS,
            "manifest_path": str(path),
            "manifest_sha256": digest(manifest),
            "listening_audio_complete": manifest["listening_audio"]["complete"],
            "next_short_step": NEXT_SHORT_STEP,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "register-listening", "register-recording", "export"):
        command = subcommands.add_parser(name)
        command.add_argument("--database", type=Path, required=True)
        command.add_argument("--consumer", type=Path, required=True)
        command.add_argument("--media-root", type=Path, required=True)
        if name == "register-listening":
            command.add_argument("--asset-key", required=True)
            command.add_argument("--wav", type=Path, required=True)
        if name == "register-recording":
            command.add_argument("--learner-id", required=True)
            command.add_argument("--attempt-id", required=True)
            command.add_argument("--wav", type=Path, required=True)
            command.add_argument("--consent-granted", action="store_true")
        if name == "export":
            command.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    registry = PrivateMediaRegistry(
        database_path=args.database,
        consumer_path=args.consumer,
        media_root=args.media_root,
    )
    if args.command == "init":
        result = registry.initialize()
    elif args.command == "register-listening":
        result = registry.register_listening(asset_key=args.asset_key, wav_path=args.wav)
    elif args.command == "register-recording":
        result = registry.register_recording(
            learner_id=args.learner_id,
            attempt_id=args.attempt_id,
            wav_path=args.wav,
            consent_granted=args.consent_granted,
        )
    else:
        result = registry.export(output_root=args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
