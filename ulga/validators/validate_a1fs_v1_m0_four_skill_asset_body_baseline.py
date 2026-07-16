#!/usr/bin/env python3
"""Independent validator for the A1FS-V1 M0 four-skill baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

EXPECTED = {
    "WRITING": (88, 440, 88),
    "READING": (101, 1010, 101),
    "SPEAKING": (95, 570, 95),
    "LISTENING": (130, 1300, 130),
}
STATUS = "PASS_A1FS_V1_M0_FOUR_SKILL_ASSET_BODY_BASELINE_FROZEN"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(baseline_path: Path, packages: dict[str, Path]) -> dict:
    errors: list[str] = []
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"baseline_unreadable:{exc}"]}
    rows = baseline.get("packages", [])
    by_skill = {row.get("skill"): row for row in rows if isinstance(row, dict)}
    if set(by_skill) != set(EXPECTED):
        errors.append("skill_set_mismatch")
    if len(rows) != 4:
        errors.append("package_count_not_four")
    for skill, expected in EXPECTED.items():
        row = by_skill.get(skill, {})
        path = packages.get(skill)
        if path is None or not path.is_file():
            errors.append(f"package_missing:{skill}")
            continue
        try:
            with ZipFile(path) as archive:
                bad = archive.testzip()
                entries = archive.namelist()
        except (OSError, BadZipFile) as exc:
            errors.append(f"zip_unreadable:{skill}:{exc}")
            continue
        if bad:
            errors.append(f"zip_crc_failure:{skill}:{bad}")
        if row.get("source_sha256") != _sha256(path):
            errors.append(f"hash_mismatch:{skill}")
        if row.get("zip_entry_count") != len(entries):
            errors.append(f"entry_count_mismatch:{skill}")
        counts = row.get("counts", {})
        actual = (counts.get("lessons"), counts.get("asset_bodies"), counts.get("teacher_guides"))
        if actual != expected:
            errors.append(f"count_mismatch:{skill}:{actual!r}")
        boundary = row.get("release_boundary", {})
        if boundary.get("learner_release_ready") != 0:
            errors.append(f"premature_learner_release:{skill}")
        if boundary.get("audio_deferred") is not (skill == "LISTENING"):
            errors.append(f"audio_boundary_mismatch:{skill}")
    expected_totals = {
        "lessons": sum(value[0] for value in EXPECTED.values()),
        "asset_bodies": sum(value[1] for value in EXPECTED.values()),
        "teacher_guides": sum(value[2] for value in EXPECTED.values()),
    }
    if baseline.get("totals") != expected_totals:
        errors.append("aggregate_totals_mismatch")
    boundaries = baseline.get("claim_boundaries", {})
    for field in ("learner_release_approved", "human_pilot_claimed", "listening_audio_complete", "a2_unlocked", "mastery_claimed"):
        if boundaries.get(field) is not False:
            errors.append(f"claim_boundary_invalid:{field}")
    if baseline.get("validation_status") != STATUS:
        errors.append("baseline_status_mismatch")
    return {
        "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M0_BASELINE_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "checked_package_count": len(EXPECTED),
        "totals": expected_totals if not errors else baseline.get("totals"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--ketw", type=Path, required=True)
    parser.add_argument("--ketr", type=Path, required=True)
    parser.add_argument("--kets", type=Path, required=True)
    parser.add_argument("--ketl", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args()
    result = validate(args.baseline, {
        "WRITING": args.ketw, "READING": args.ketr,
        "SPEAKING": args.kets, "LISTENING": args.ketl,
    })
    if args.validation_report:
        args.validation_report.parent.mkdir(parents=True, exist_ok=True)
        args.validation_report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
