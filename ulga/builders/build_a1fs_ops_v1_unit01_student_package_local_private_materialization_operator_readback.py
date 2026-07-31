#!/usr/bin/env python3
"""Materialize the accepted Unit01 learner package in a local private disposable product.

This operator executor reuses the merged Chromium/authenticated-entry acceptance,
discovers the approved Unit01 content artifact by its hash when an explicit path is
not supplied, and writes a local-safe operator readback. It never mutates the
production product root or activates a release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as integration,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as acceptance,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reuses the merged Unit01 learner package and authenticated Chromium acceptance "
    "inside an existing disposable product, discovers only the already approved "
    "content artifact by its authoritative digest, and writes a local-safe operator "
    "readback. It creates no content, question, answer, bank, planner, renderer, "
    "learner state authority, scoring authority, audio, A2 content, Unit02-24 "
    "artifact, production activation, or public delivery."
)

PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = (
    "A1FS-OPS-V1_"
    "Unit01StudentPackageLocalPrivateMaterializationAndOperatorReadback"
)
SCHEMA_VERSION = "a1fs.ops.v1.unit01_student_local_private_operator_readback.v1"
PASS_STATUS = (
    "PASS_A1FS_OPS_V1_UNIT01_STUDENT_LOCAL_PRIVATE_OPERATOR_READBACK"
)
REPORT_NAME = "unit01_student_local_private_operator_readback.safe.json"
NEXT_SHORT_STEP = (
    "A1FS-OPS-V1_"
    "Unit01StudentPackageOperatorVisualAcceptanceAndV122ReleaseDecision"
)
MAX_DISCOVERY_FILE_BYTES = 64 * 1024 * 1024
DEFAULT_JSON_PATTERNS = (
    "*approved*.json",
    "*canonical*.json",
    "*content*.json",
    "*.json",
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class LocalPrivateOperatorError(ValueError):
    """Fail-closed local-private materialization or discovery error."""


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalPrivateOperatorError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise LocalPrivateOperatorError(f"json_object_required:{path}")
    return value


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _integration_report(disposable_product_root: Path) -> dict[str, Any]:
    path = (
        Path(disposable_product_root).resolve()
        / "shared"
        / "reports"
        / integration.REPORT_NAME
    )
    report = load(path)
    core = {
        key: value
        for key, value in report.items()
        if key != "readback_sha256"
    }
    if report.get("readback_sha256") != integration.digest(core):
        raise LocalPrivateOperatorError("integration_readback_digest_invalid")
    if report.get("status") != integration.PASS_STATUS:
        raise LocalPrivateOperatorError("integration_readback_status_invalid")
    if report.get("combined_runtime_item_count") != 474:
        raise LocalPrivateOperatorError("integration_runtime_item_count_invalid")
    expected_sha = str(report.get("approved_content_artifact_sha256") or "")
    if len(expected_sha) != 64:
        raise LocalPrivateOperatorError(
            "integration_approved_content_artifact_sha256_invalid"
        )
    return report


def _candidate_json_paths(root: Path) -> Iterable[Path]:
    root = Path(root).resolve()
    if root.is_file():
        if root.suffix.casefold() == ".json":
            yield root
        return
    if not root.is_dir():
        return
    seen: set[Path] = set()
    for pattern in DEFAULT_JSON_PATTERNS:
        for path in root.rglob(pattern):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if not resolved.is_file():
                continue
            try:
                if resolved.stat().st_size > MAX_DISCOVERY_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield resolved


def _artifact_matches(path: Path, expected_sha: str) -> bool:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(value, dict)
        and str(value.get("artifact_sha256") or "") == expected_sha
    )


def discover_approved_content(
    *,
    expected_sha: str,
    explicit_path: Path | None = None,
    search_roots: Sequence[Path] = (),
) -> tuple[Path, str]:
    if explicit_path is not None:
        path = Path(explicit_path).resolve()
        if not path.is_file():
            raise LocalPrivateOperatorError(
                f"approved_content_explicit_path_missing:{path}"
            )
        if not _artifact_matches(path, expected_sha):
            raise LocalPrivateOperatorError(
                "approved_content_explicit_identity_mismatch"
            )
        return path, "EXPLICIT_PATH"

    configured = os.environ.get("A1FS_UNIT01_APPROVED_CONTENT", "").strip()
    if configured:
        path = Path(configured).resolve()
        if not path.is_file() or not _artifact_matches(path, expected_sha):
            raise LocalPrivateOperatorError(
                "approved_content_environment_identity_mismatch"
            )
        return path, "ENVIRONMENT_PATH"

    matches: list[Path] = []
    seen: set[Path] = set()
    for root in search_roots:
        for candidate in _candidate_json_paths(Path(root)):
            if candidate in seen:
                continue
            seen.add(candidate)
            if _artifact_matches(candidate, expected_sha):
                matches.append(candidate)
    matches.sort(key=lambda row: str(row).casefold())
    if not matches:
        raise LocalPrivateOperatorError(
            "approved_content_not_found:"
            "pass --approved-content or --search-root, or set "
            "A1FS_UNIT01_APPROVED_CONTENT"
        )
    if len(matches) != 1:
        names = ",".join(path.name for path in matches[:10])
        raise LocalPrivateOperatorError(
            f"approved_content_ambiguous:{len(matches)}:{names}"
        )
    return matches[0], "ARTIFACT_SHA_DISCOVERY"


def _default_search_roots(disposable_product_root: Path) -> list[Path]:
    report = _integration_report(disposable_product_root)
    roots = [
        REPO_ROOT,
        Path(disposable_product_root).resolve(),
        Path(str(report["source_product_root"])).resolve(),
    ]
    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        unique.append(root)
    return unique


def materialize_operator_readback(
    *,
    disposable_product_root: Path,
    approved_content_path: Path | None = None,
    search_roots: Sequence[Path] = (),
    chromium_path: Path | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    disposable_product_root = Path(disposable_product_root).resolve()
    integration_report = _integration_report(disposable_product_root)
    expected_sha = str(
        integration_report["approved_content_artifact_sha256"]
    )
    roots = list(search_roots) or _default_search_roots(
        disposable_product_root
    )
    approved_path, discovery_mode = discover_approved_content(
        expected_sha=expected_sha,
        explicit_path=approved_content_path,
        search_roots=roots,
    )
    approved_content = load(approved_path)

    acceptance_report = acceptance.build_acceptance(
        disposable_product_root=disposable_product_root,
        approved_content=approved_content,
        chromium_path=chromium_path,
        output_root=output_root,
    )
    package_root = (
        Path(output_root).resolve()
        if output_root is not None
        else disposable_product_root
        / "shared"
        / "print_packages"
        / "unit01"
    )
    relative_outputs = {
        "learner_launcher": "learner/index.html",
        "prelearning_html": "learner/prelearning.html",
        "questionbank_html": "learner/questionbank.html",
        "prelearning_pdf": "acceptance/unit01_prelearning_chromium.pdf",
        "questionbank_sample_pdf": (
            "acceptance/unit01_questionbank_stage_sample_chromium.pdf"
        ),
        "prelearning_png": "acceptance/unit01_prelearning_chromium.png",
        "questionbank_sample_png": (
            "acceptance/unit01_questionbank_stage_sample_chromium.png"
        ),
    }
    for name in relative_outputs.values():
        if not (package_root / name).is_file():
            raise LocalPrivateOperatorError(
                f"operator_output_missing:{name}"
            )

    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "product_version": acceptance_report["product_version"],
        "runtime_item_count": acceptance_report["runtime_item_count"],
        "approved_content_artifact_sha256": expected_sha,
        "approved_content_discovery_mode": discovery_mode,
        "approved_content_file_name": approved_path.name,
        "chromium_executable_name": acceptance_report[
            "chromium_executable_name"
        ],
        "chromium_version": acceptance_report["chromium_version"],
        "chromium_render_count": acceptance_report[
            "chromium_render_count"
        ],
        "prelearning_pdf_page_count": acceptance_report[
            "prelearning_pdf_page_count"
        ],
        "questionbank_sample_pdf_page_count": acceptance_report[
            "questionbank_sample_pdf_page_count"
        ],
        "unauthenticated_prelearning_status": acceptance_report[
            "authenticated_http_readback"
        ]["unauthenticated_prelearning_status"],
        "authenticated_prelearning_status": acceptance_report[
            "authenticated_http_readback"
        ]["authenticated_prelearning_status"],
        "authenticated_questionbank_status": acceptance_report[
            "authenticated_http_readback"
        ]["authenticated_questionbank_status"],
        "teacher_files_unchanged": acceptance_report[
            "teacher_files_unchanged"
        ],
        "source_product_root_unchanged": acceptance_report[
            "source_product_root_unchanged"
        ],
        "disposable_release_checksums_refreshed": acceptance_report[
            "disposable_release_checksums_refreshed"
        ],
        "package_relative_outputs": relative_outputs,
        "operator_visual_confirmation_required": True,
        "operator_visual_confirmation_completed": False,
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**core, "readback_sha256": digest(core)}
    report_path = (
        disposable_product_root
        / "shared"
        / "reports"
        / REPORT_NAME
    )
    atomic_json(report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--disposable-product-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--approved-content", type=Path)
    parser.add_argument(
        "--search-root",
        action="append",
        default=[],
        type=Path,
    )
    parser.add_argument("--chromium-path", type=Path)
    parser.add_argument("--output-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = materialize_operator_readback(
        disposable_product_root=args.disposable_product_root,
        approved_content_path=args.approved_content,
        search_roots=args.search_root,
        chromium_path=args.chromium_path,
        output_root=args.output_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"STATUS={report['status']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
