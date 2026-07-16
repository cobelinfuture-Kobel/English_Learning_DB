#!/usr/bin/env python3
"""Independent output and disclosure validator for the M5 learner UI."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M5_FourSkillRendererAndLearnerUI"
STATUS = "PASS_A1FS_V1_M5_FOUR_SKILL_RENDERER_LEARNER_UI_READY"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
PLANNER_STATUS = "PASS_A1FS_V1_M4_LESSON_PLANNER_AND_A2_LOCK_READY"
NEXT_SHORT_STEP = "A1FS-V1-M6_ResponseCaptureScoringAndM12Evidence"
BLOCKED_KEY = re.compile(r"(?:answer|rationale|decisive_evidence|acceptance|critical_failure|diagnostic|provenance|automated|sha256|teacher_delivery|release_status)", re.I)


def _sha(value: bytes) -> str: return hashlib.sha256(value).hexdigest()


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(tmp, path)


def _blocked_keys(value: Any, path: str = "$") -> list[str]:
    errors = []
    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{path}.{key}"
            if BLOCKED_KEY.search(str(key)) or str(key) in {"transcript", "speaker_turns"}: errors.append(current)
            errors.extend(_blocked_keys(item, current))
    elif isinstance(value, list):
        for index, item in enumerate(value): errors.extend(_blocked_keys(item, f"{path}[{index}]"))
    return errors


def validate(output_root: Path, consumer_path: Path, plan_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        consumer_raw = consumer_path.read_bytes(); consumer = json.loads(consumer_raw)
        plan_raw = plan_path.read_bytes(); plan = json.loads(plan_raw)
        manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
        bundle = json.loads((output_root / "lesson.private.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"validation_status": "FAIL_A1FS_V1_M5", "error_count": 1, "errors": [f"output_unreadable:{exc}"]}
    if consumer.get("validation_status") != CONSUMER_STATUS: errors.append("consumer_status_invalid")
    if plan.get("validation_status") != PLANNER_STATUS: errors.append("plan_status_invalid")
    if manifest.get("validation_status") != STATUS or bundle.get("validation_status") != STATUS: errors.append("render_status_invalid")
    if bundle.get("source_consumer_sha256") != _sha(consumer_raw): errors.append("consumer_hash_mismatch")
    if bundle.get("source_plan_sha256") != _sha(plan_raw): errors.append("plan_hash_mismatch")
    lesson = bundle.get("lesson") or {}
    if lesson.get("level") not in {"A1", "A1+"}: errors.append("a2_content_rendered")
    if lesson.get("lesson_id") != (plan.get("selected_lesson") or {}).get("lesson_id"): errors.append("plan_lesson_mismatch")
    source_assets = {row["asset_key"]: row for row in consumer.get("asset_records", []) if row.get("lesson_id") == lesson.get("lesson_id")}
    rendered = bundle.get("assets") or []; rendered_keys = [row.get("asset_key") for row in rendered]
    if len(rendered_keys) != len(set(rendered_keys)) or set(rendered_keys) != set(source_assets): errors.append("rendered_asset_set_mismatch")
    for row in rendered:
        source = source_assets.get(row.get("asset_key"), {})
        if row.get("content_digest") != source.get("content_digest") or row.get("role") != source.get("role"): errors.append(f'rendered_asset_identity_mismatch:{row.get("asset_key")}')
        for blocked in _blocked_keys(row.get("learner_payload")): errors.append(f"educator_key_disclosed:{blocked}")
        if lesson.get("skill") == "LISTENING" and row.get("role") == "AUD":
            text = json.dumps(row.get("learner_payload"), ensure_ascii=False)
            if "speaker_turns" in text or "transcript" in text: errors.append("listening_script_disclosed_before_attempt")
    subtitle = bundle.get("subtitle_contract") or {}
    if subtitle.get("actual_srt_loaded") is not False or subtitle.get("audio_synchronized") is not False or subtitle.get("timed_cues") != []: errors.append("subtitle_or_audio_completion_overclaimed")
    capabilities = bundle.get("capabilities") or {}
    for key in ("response_capture_enabled", "scoring_enabled", "audio_playback_enabled", "speaking_recording_enabled", "a2_content_included"):
        if capabilities.get(key) is not False: errors.append(f"capability_boundary_invalid:{key}")
    if manifest.get("private_localhost_only") is not True or manifest.get("learner_release_approved") is not False: errors.append("release_boundary_invalid")
    for name in ("lesson.private.json", "index.html", "styles.css", "app.js"):
        path = output_root / name; expected = (manifest.get("files") or {}).get(name, {})
        if not path.is_file() or expected.get("sha256") != _sha(path.read_bytes()) or expected.get("bytes") != len(path.read_bytes()): errors.append(f"file_manifest_mismatch:{name}")
    try:
        html = (output_root / "index.html").read_text(encoding="utf-8"); js = (output_root / "app.js").read_text(encoding="utf-8")
        for token in ("Content-Security-Policy", "app.js", "styles.css", "aria-live"):
            if token not in html: errors.append(f"ui_contract_token_missing:{token}")
        if "innerHTML" in js or "eval(" in js: errors.append("unsafe_dom_rendering_present")
        if "textContent" not in js or "ArrowRight" not in js or "ArrowLeft" not in js: errors.append("ui_accessibility_contract_missing")
    except OSError as exc: errors.append(f"ui_file_unreadable:{exc}")
    return {"task_id": TASK_ID, "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M5_FOUR_SKILL_RENDERER_LEARNER_UI",
            "error_count": len(errors), "errors": errors, "checked_skill": lesson.get("skill"),
            "checked_lesson_id": lesson.get("lesson_id"), "checked_asset_count": len(rendered),
            "next_short_step": NEXT_SHORT_STEP if not errors else TASK_ID}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output-root", type=Path, required=True); parser.add_argument("--consumer", type=Path, required=True); parser.add_argument("--plan", type=Path, required=True); parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(); report = validate(args.output_root, args.consumer, args.plan); _atomic(args.validation_report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if not report["errors"] else 1


if __name__ == "__main__": raise SystemExit(main())
