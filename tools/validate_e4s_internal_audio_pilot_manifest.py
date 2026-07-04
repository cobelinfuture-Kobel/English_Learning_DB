#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ulga/listening/audio_manifests/e4s_p5_seed_batch_001_internal_audio_pilot_manifest.json"
PACKAGE = ROOT / "ulga/listening/candidates/e4s_listening_candidate_package.json"
REPORT = ROOT / "ulga/listening/reports/e4s_internal_audio_pilot_manifest_validator_report.json"
TASK_ID = "E4S-P5-I11_InternalAudioPilotManifestSchemaImplementation"
SCHEMA = "E4S_P5_INTERNAL_AUDIO_PILOT_MANIFEST_V1"
PILOT_ID = "e4s_p5_seed_batch_001_internal_audio_pilot_v1"
AUDIO_PREFIX = "ulga/listening/audio_internal/"
SITE_PREFIX = "site/listening/"
ALLOWED_SELECTED = {"p5_sentence_parent_functional_sentence_corpus_reference_p5_sentence_002"}
PUBLIC_VALUES = {"public", "allowed", "public_allowed", "cleared", "public_distribution_allowed"}
LEARNER_VALUES = {"student_facing", "learner_facing", "approved", "allowed", "public"}


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


def item(code: str, field: str, msg: str, sev: str = "error") -> dict[str, str]:
    return {"code": code, "severity": sev, "field": field, "message": msg}


def validate(manifest: dict[str, Any], package: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if manifest.get("schema_version") != SCHEMA:
        out.append(item("P5_AUDIO_PILOT_BAD_SCHEMA", "$.schema_version", "schema mismatch"))
    if manifest.get("pilot_id") != PILOT_ID:
        out.append(item("P5_AUDIO_PILOT_BAD_ID", "$.pilot_id", "pilot id mismatch"))
    if manifest.get("pilot_status") != "DESIGN_ONLY_NOT_GENERATED":
        out.append(item("P5_AUDIO_PILOT_GENERATION_STATUS_OPEN", "$.pilot_status", "pilot must remain design-only"))
    for field in ("public_distribution_status", "learner_facing_status"):
        if manifest.get(field) != "blocked":
            out.append(item("P5_AUDIO_PILOT_PUBLIC_OR_LEARNER_OPEN", f"$.{field}", "pilot must stay blocked"))

    package_ids = {c.get("candidate_id") for c in package.get("candidates", []) if isinstance(c, dict)}
    selected = manifest.get("selected_candidates")
    if not isinstance(selected, list) or not selected:
        out.append(item("P5_AUDIO_PILOT_NO_SELECTED_CANDIDATE", "$.selected_candidates", "selected candidate required"))
    else:
        for idx, rec in enumerate(selected):
            cid = rec.get("candidate_id") if isinstance(rec, dict) else None
            if cid not in package_ids:
                out.append(item("P5_AUDIO_PILOT_UNKNOWN_CANDIDATE", f"$.selected_candidates[{idx}].candidate_id", "candidate missing from package"))
            if cid not in ALLOWED_SELECTED:
                out.append(item("P5_AUDIO_PILOT_UNAPPROVED_CANDIDATE", f"$.selected_candidates[{idx}].candidate_id", "candidate not approved for first pilot"))

    storage = manifest.get("storage_policy") if isinstance(manifest.get("storage_policy"), dict) else {}
    if not storage or not str(storage.get("allowed_audio_path_prefix", "")).startswith(AUDIO_PREFIX):
        out.append(item("P5_AUDIO_PILOT_STORAGE_POLICY_INVALID", "$.storage_policy.allowed_audio_path_prefix", "internal audio path required"))

    assets = manifest.get("audio_assets")
    if not isinstance(assets, list):
        out.append(item("P5_AUDIO_PILOT_ASSETS_NOT_LIST", "$.audio_assets", "audio_assets must be a list"))
    else:
        for idx, asset in enumerate(assets):
            validate_asset(asset, idx, package_ids, out)
    return sorted(out, key=lambda x: (x["severity"], x["code"], x["field"]))


def validate_asset(asset: Any, idx: int, package_ids: set[Any], out: list[dict[str, str]]) -> None:
    path = f"$.audio_assets[{idx}]"
    if not isinstance(asset, dict):
        out.append(item("P5_AUDIO_PILOT_ASSET_BAD_SHAPE", path, "asset must be object"))
        return
    cid = asset.get("candidate_id")
    if cid not in package_ids:
        out.append(item("P5_AUDIO_PILOT_UNKNOWN_CANDIDATE", f"{path}.candidate_id", "candidate missing from package"))
    if cid not in ALLOWED_SELECTED:
        out.append(item("P5_AUDIO_PILOT_UNAPPROVED_CANDIDATE", f"{path}.candidate_id", "asset candidate not approved"))
    apath = asset.get("audio_asset_path")
    if not isinstance(apath, str) or not apath.startswith(AUDIO_PREFIX) or apath.startswith(SITE_PREFIX):
        out.append(item("P5_AUDIO_PILOT_ASSET_PATH_INVALID", f"{path}.audio_asset_path", "asset path must be internal"))
    if asset.get("public_distribution_status") in PUBLIC_VALUES or asset.get("learner_facing_status") in LEARNER_VALUES:
        out.append(item("P5_AUDIO_PILOT_PUBLIC_OR_LEARNER_OPEN", path, "asset must stay non-public and non-learner-facing"))
    if asset.get("audio_generation_status") not in {"planned_not_generated", "not_generated"}:
        out.append(item("P5_AUDIO_PILOT_AUDIO_GENERATED", f"{path}.audio_generation_status", "I11 cannot contain generated audio"))


def build_report(manifest: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
    errors = [x for x in issues if x["severity"] == "error"]
    warnings = [x for x in issues if x["severity"] == "warning"]
    assets = manifest.get("audio_assets") if isinstance(manifest.get("audio_assets"), list) else []
    public_assets = [a for a in assets if isinstance(a, dict) and a.get("public_distribution_status") in PUBLIC_VALUES]
    learner_assets = [a for a in assets if isinstance(a, dict) and a.get("learner_facing_status") in LEARNER_VALUES]
    status = "FAIL_BLOCKING_ERRORS" if errors else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    return {
        "schema_version": "E4S_P5_INTERNAL_AUDIO_PILOT_MANIFEST_VALIDATION_REPORT_V1",
        "pilot_id": manifest.get("pilot_id"),
        "task_id": TASK_ID,
        "status": status,
        "blocking_issue_count": len(errors),
        "warning_count": len(warnings),
        "selected_candidate_count": len(manifest.get("selected_candidates", [])) if isinstance(manifest.get("selected_candidates"), list) else 0,
        "audio_asset_count": len(assets),
        "internal_audio_asset_count": len(assets) - len(public_assets) - len(learner_assets),
        "public_audio_asset_count": len(public_assets),
        "learner_facing_audio_count": len(learner_assets),
        "issues": errors,
        "warnings": warnings,
        "next_shortest_step": "E4S-P5-I11_TestEvidenceReadback" if status == "PASS" else "FIX_E4S_P5_INTERNAL_AUDIO_PILOT_MANIFEST",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate E4S P5 internal audio pilot manifest.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--candidate-package", type=Path, default=PACKAGE)
    parser.add_argument("--report-output", type=Path, default=REPORT)
    args = parser.parse_args()
    manifest = load_json(args.manifest, "manifest")
    package = load_json(args.candidate_package, "candidate package")
    issues = validate(manifest, package)
    report = build_report(manifest, issues)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
