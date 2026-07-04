#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "ulga/listening/policies/e4s_p5_audio_voice_storage_policy_v1.json"
PACKAGE = ROOT / "ulga/listening/candidates/e4s_listening_candidate_package.json"
REPORT = ROOT / "ulga/listening/reports/e4s_listening_audio_policy_validator_report.json"
TASK_ID = "E4S-P5-I8_ListeningAudioVoiceStoragePolicySchemaAndValidatorImplementation"
POLICY_ID = "E4S_P5_AUDIO_VOICE_STORAGE_POLICY_V1"
POLICY_SCHEMA = "E4S_P5_AUDIO_VOICE_STORAGE_POLICY_SCHEMA_V1"
AUDIO_PREFIX = "ulga/listening/audio_internal/"
TIMING_PREFIX = "ulga/listening/timing_internal/"
PUBLIC_VALUES = {"public", "allowed", "public_allowed", "cleared", "public_distribution_allowed"}
LEARNER_VALUES = {"student_facing", "learner_facing", "approved", "allowed", "public"}
OFF_VALUES = {"forbidden", "blocked", "not_allowed", "forbidden_until_later_approval", "not_created", None}


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{label} must be an object")
    return data


def issue(code: str, field: str, msg: str, cid: str | None = None, sev: str = "error") -> dict[str, Any]:
    return {"code": code, "severity": sev, "candidate_id": cid, "field": field, "message": msg}


def validate(policy: dict[str, Any], package: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if policy.get("schema_version") != POLICY_SCHEMA or policy.get("policy_id") != POLICY_ID:
        out.append(issue("P5_AUDIO_POLICY_VERSION_MISSING", "$.policy_id", "policy schema/id mismatch"))
    paths = policy.get("allowed_internal_paths")
    if not isinstance(paths, dict) or paths.get("audio_internal_prefix") != AUDIO_PREFIX or paths.get("timing_internal_prefix") != TIMING_PREFIX:
        out.append(issue("P5_STORAGE_POLICY_MISSING", "$.allowed_internal_paths", "internal path policy mismatch"))
    candidates = package.get("candidates")
    if not isinstance(candidates, list):
        out.append(issue("P5_AUDIO_POLICY_MISSING", "$.candidates", "candidates must be a list"))
        return sorted(out, key=_sort_key)
    for index, cand in enumerate(candidates):
        validate_candidate(cand, f"$.candidates[{index}]", out)
    return sorted(out, key=_sort_key)


def validate_candidate(cand: Any, path: str, out: list[dict[str, Any]]) -> None:
    if not isinstance(cand, dict):
        out.append(issue("P5_AUDIO_POLICY_MISSING", path, "candidate must be an object"))
        return
    cid = cand.get("candidate_id") if isinstance(cand.get("candidate_id"), str) else None
    ctype = cand.get("candidate_type")
    audio = cand.get("audio_policy") if isinstance(cand.get("audio_policy"), dict) else {}
    tts = cand.get("tts_policy") if isinstance(cand.get("tts_policy"), dict) else {}
    voice = cand.get("voice_policy") if isinstance(cand.get("voice_policy"), dict) else {}
    storage = cand.get("storage_policy") if isinstance(cand.get("storage_policy"), dict) else {}
    timing = cand.get("timing_policy") if isinstance(cand.get("timing_policy"), dict) else {}
    pub = cand.get("public_distribution_policy") if isinstance(cand.get("public_distribution_policy"), dict) else {}
    listen = cand.get("listening_policy") if isinstance(cand.get("listening_policy"), dict) else {}
    trace = cand.get("source_trace") if isinstance(cand.get("source_trace"), dict) else {}

    if not audio or not audio.get("audio_policy_version"):
        out.append(issue("P5_AUDIO_POLICY_VERSION_MISSING", f"{path}.audio_policy", "audio policy/version required", cid))
    if not voice or not voice.get("voice_policy_status"):
        out.append(issue("P5_VOICE_POLICY_MISSING", f"{path}.voice_policy", "voice policy required", cid))
    if not storage or not storage.get("storage_policy_status"):
        out.append(issue("P5_STORAGE_POLICY_MISSING", f"{path}.storage_policy", "storage policy required", cid))

    asset_path = audio.get("audio_asset_path")
    has_asset = bool(audio.get("audio_asset_id") or asset_path)
    if has_asset:
        if not isinstance(asset_path, str) or not asset_path.startswith(AUDIO_PREFIX):
            out.append(issue("P5_AUDIO_ASSET_PATH_NOT_INTERNAL", f"{path}.audio_policy.audio_asset_path", "audio path must be internal", cid))
        if pub.get("public_distribution_status") in PUBLIC_VALUES:
            out.append(issue("P5_AUDIO_PUBLIC_DISTRIBUTION_ATTEMPT", f"{path}.public_distribution_policy.public_distribution_status", "public audio not approved", cid))
        if listen.get("student_facing_status") in LEARNER_VALUES:
            out.append(issue("P5_LEARNER_FACING_AUDIO_ATTEMPT", f"{path}.listening_policy.student_facing_status", "learner-facing audio not approved", cid))
        if ctype == "dialogue_listening_candidate" and voice.get("speaker_role_mapping_status") not in {"defined", "reviewed", "approved"}:
            out.append(issue("P5_DIALOGUE_VOICE_MAPPING_MISSING", f"{path}.voice_policy.speaker_role_mapping_status", "dialogue audio needs speaker mapping", cid))
        if audio.get("human_audio_permission_status") in {"approved", "allowed"} and not audio.get("human_audio_permission_ref"):
            out.append(issue("P5_HUMAN_AUDIO_PERMISSION_MISSING", f"{path}.audio_policy.human_audio_permission_ref", "human audio permission ref required", cid))

    tts_on = tts.get("tts_generation_status") not in OFF_VALUES or bool(tts.get("tts_provider") or tts.get("tts_voice_id"))
    if tts_on and tts.get("tts_scope") != "internal_only_test_asset":
        out.append(issue("P5_TTS_SCOPE_NOT_INTERNAL_ONLY", f"{path}.tts_policy.tts_scope", "tts scope must be internal-only", cid))

    timing_path = timing.get("timing_metadata_path")
    if timing_path:
        if not has_asset:
            out.append(issue("P5_TIMING_WITHOUT_AUDIO_ASSET", f"{path}.timing_policy.timing_metadata_path", "timing needs audio asset", cid))
        if not isinstance(timing_path, str) or not timing_path.startswith(TIMING_PREFIX):
            out.append(issue("P5_AUDIO_ASSET_PATH_NOT_INTERNAL", f"{path}.timing_policy.timing_metadata_path", "timing path must be internal", cid))
    else:
        out.append(issue("P5_WARN_TIMING_NOT_CREATED", f"{path}.timing_policy.timing_metadata_path", "timing not created", cid, "warning"))
    if voice.get("voice_policy_status") in {"required_future", "placeholder"}:
        out.append(issue("P5_WARN_VOICE_POLICY_PLACEHOLDER", f"{path}.voice_policy.voice_policy_status", "voice policy placeholder", cid, "warning"))
    if trace.get("license_status") == "restricted_reference_only" and pub.get("public_distribution_status") in {"blocked", "internal_only", "forbidden"}:
        out.append(issue("P5_WARN_RESTRICTED_SOURCE_AUDIO_INTERNAL_ONLY", f"{path}.source_trace.license_status", "restricted source stays internal", cid, "warning"))


def build_report(policy: dict[str, Any], package: dict[str, Any], issues: list[dict[str, Any]], strict_mode: bool = False) -> dict[str, Any]:
    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    candidates = [c for c in package.get("candidates", []) if isinstance(c, dict)]
    status = "FAIL_BLOCKING_ERRORS" if errors or (strict_mode and warnings) else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    asset_count = sum(1 for c in candidates if isinstance(c.get("audio_policy"), dict) and (c["audio_policy"].get("audio_asset_id") or c["audio_policy"].get("audio_asset_path")))
    return {
        "schema_version": "E4S_P5_AUDIO_POLICY_VALIDATION_REPORT_V1",
        "policy_id": policy.get("policy_id"),
        "task_id": TASK_ID,
        "status": status,
        "issue_count": len(issues),
        "blocking_issue_count": len(errors) + (len(warnings) if strict_mode else 0),
        "warning_count": len(warnings),
        "candidate_count": len(candidates),
        "audio_policy_status": gate(issues, "P5_AUDIO_POLICY_MISSING", "P5_AUDIO_POLICY_VERSION_MISSING"),
        "voice_policy_status": gate(issues, "P5_VOICE_POLICY_MISSING", "P5_DIALOGUE_VOICE_MAPPING_MISSING"),
        "storage_policy_status": gate(issues, "P5_STORAGE_POLICY_MISSING", "P5_AUDIO_ASSET_PATH_NOT_INTERNAL"),
        "timing_policy_status": gate(issues, "P5_TIMING_WITHOUT_AUDIO_ASSET", "P5_TIMING_SEGMENT_ORDER_INVALID"),
        "audio_asset_count": asset_count,
        "internal_audio_asset_count": asset_count,
        "public_audio_asset_count": count_public(candidates),
        "learner_facing_audio_count": count_learner(candidates),
        "issues": errors,
        "warnings": warnings,
        "next_shortest_step": "E4S-P5-I8_TestEvidenceReadback" if status in {"PASS", "PASS_WITH_WARNINGS"} else "FIX_E4S_P5_AUDIO_POLICY_METADATA",
    }


def gate(issues: list[dict[str, Any]], *codes: str) -> str:
    errors = {item["code"] for item in issues if item["severity"] == "error"}
    return "FAIL" if any(code in errors for code in codes) else "PASS"


def count_public(candidates: list[dict[str, Any]]) -> int:
    return sum(1 for c in candidates if isinstance(c.get("public_distribution_policy"), dict) and c["public_distribution_policy"].get("public_distribution_status") in PUBLIC_VALUES)


def count_learner(candidates: list[dict[str, Any]]) -> int:
    return sum(1 for c in candidates if isinstance(c.get("listening_policy"), dict) and c["listening_policy"].get("student_facing_status") in LEARNER_VALUES)


def _sort_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (item.get("candidate_id") or "", item["severity"], item["code"], item["field"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate E4S P5 listening audio policy metadata.")
    parser.add_argument("--policy", type=Path, default=POLICY)
    parser.add_argument("--candidate-package", type=Path, default=PACKAGE)
    parser.add_argument("--report-output", type=Path, default=REPORT)
    parser.add_argument("--strict-mode", action="store_true")
    args = parser.parse_args()
    policy = load_json(args.policy, "policy")
    package = load_json(args.candidate_package, "candidate package")
    issues = validate(policy, package)
    report = build_report(policy, package, issues, strict_mode=args.strict_mode)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
