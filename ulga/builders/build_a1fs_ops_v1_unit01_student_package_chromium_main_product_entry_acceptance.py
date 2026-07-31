#!/usr/bin/env python3
"""Accept the Unit01 student package in a disposable authenticated product.

The accepted learner package is rebuilt from the existing 474-item authority,
then copied into the disposable product's existing secure-static root. The main
learner page receives authenticated links to Pre-learning and QuestionBank.
Chromium renders the full seven-page Pre-learning package and a seven-stage
QuestionBank sample derived from the real learner-safe questions. The immutable
source product and both teacher-private files remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as master,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
)
from ulga.builders import (
    build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Rebuilds the accepted learner-only Unit01 package from the existing 474-item "
    "authority, copies only learner-safe HTML/CSS/JS into an already disposable "
    "authenticated product, and renders deterministic Chromium QA artifacts. It "
    "creates no question, answer, bank, planner, learner state, score, renderer "
    "authority, teacher output, audio, A2 content, or Unit02-Unit24 artifact."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = (
    "A1FS-OPS-V1_"
    "Unit01StudentPackageChromiumPrintAndMainProductEntryAcceptance"
)
SCHEMA_VERSION = "a1fs.ops.v1.unit01_student_chromium_main_entry.v1"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_STUDENT_CHROMIUM_MAIN_ENTRY"
REPORT_NAME = "unit01_student_chromium_main_entry.safe.json"
ENTRY_DIRECTORY = "unit01-student"
ENTRY_PANEL_ID = "unit01-student-package-entry"
EXPECTED_PRODUCT_VERSION = "1.2.1"
EXPECTED_PRELEARNING_PAGES = 7
EXPECTED_SAMPLE_PAGES = 7
NEXT_SHORT_STEP = (
    "A1FS-OPS-V1_"
    "Unit01StudentPackageLocalPrivateMaterializationAndOperatorReadback"
)

ENTRY_PANEL = f'''<section id="{ENTRY_PANEL_ID}" class="panel unit01-student-entry">
  <div class="section-heading"><h2>Unit 01｜Pre-learning與QuestionBank</h2></div>
  <p>先完成片語預習，再進入完整句子與連接句練習。</p>
  <p class="unit01-student-actions">
    <a href="/{ENTRY_DIRECTORY}/prelearning.html">開始Pre-learning</a>
    <a href="/{ENTRY_DIRECTORY}/questionbank.html">開啟QuestionBank</a>
  </p>
</section>
'''

ENTRY_CSS = """
.unit01-student-entry{border-width:2px}.unit01-student-actions{display:flex;gap:12px;flex-wrap:wrap}.unit01-student-actions a{display:inline-block;padding:9px 13px;border:1px solid #40556b;border-radius:6px;font-weight:700;text-decoration:none}
"""


class StudentEntryAcceptanceError(ValueError):
    """Fail-closed student-package entry or Chromium acceptance error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StudentEntryAcceptanceError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise StudentEntryAcceptanceError(f"json_object_required:{path}")
    return value


def atomic_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    atomic_text(path, json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n")


def file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _product_static_root(disposable_product_root: Path) -> tuple[str, Path]:
    root = Path(disposable_product_root).resolve()
    version, manifest, _bundles, _sequence = r01._load_product(root)
    if version != EXPECTED_PRODUCT_VERSION:
        raise StudentEntryAcceptanceError(
            f"disposable_product_version_invalid:{version}"
        )
    static_root = r01._resolve(root, str(manifest["secure_static_root"]))
    if not static_root.is_dir():
        raise StudentEntryAcceptanceError("secure_static_root_missing")
    return version, static_root


def _copy_learner_entry(package_root: Path, secure_static_root: Path) -> Path:
    source = Path(package_root) / "learner"
    target = Path(secure_static_root) / ENTRY_DIRECTORY
    required = (
        "index.html",
        "prelearning.html",
        "questionbank.html",
        "student.css",
        "student.js",
    )
    if not all((source / name).is_file() for name in required):
        raise StudentEntryAcceptanceError("learner_entry_source_incomplete")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in required:
        shutil.copy2(source / name, target / name)
    return target


def _patch_main_entry(secure_static_root: Path) -> dict[str, Any]:
    index_path = Path(secure_static_root) / "index.html"
    css_path = Path(secure_static_root) / "styles.css"
    if not index_path.is_file() or not css_path.is_file():
        raise StudentEntryAcceptanceError("main_static_files_missing")
    index_before = file_identity(index_path)
    index = index_path.read_text(encoding="utf-8")
    if ENTRY_PANEL_ID not in index:
        marker = "</main>" if "</main>" in index else "</body>"
        if marker not in index:
            raise StudentEntryAcceptanceError("main_entry_insertion_marker_missing")
        index = index.replace(marker, ENTRY_PANEL + marker, 1)
        atomic_text(index_path, index)
    css = css_path.read_text(encoding="utf-8")
    if ".unit01-student-entry" not in css:
        atomic_text(css_path, css + "\n" + ENTRY_CSS)
    result = validate_main_entry(secure_static_root)
    result["main_index_before"] = index_before
    result["main_index_after"] = file_identity(index_path)
    return result


def validate_main_entry(secure_static_root: Path) -> dict[str, Any]:
    root = Path(secure_static_root)
    index = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "styles.css").read_text(encoding="utf-8")
    entry = root / ENTRY_DIRECTORY
    checks = {
        "entry_panel_present": ENTRY_PANEL_ID in index,
        "prelearning_link_present": f"/{ENTRY_DIRECTORY}/prelearning.html" in index,
        "questionbank_link_present": f"/{ENTRY_DIRECTORY}/questionbank.html" in index,
        "entry_styles_present": ".unit01-student-entry" in css,
        "learner_index_present": (entry / "index.html").is_file(),
        "prelearning_present": (entry / "prelearning.html").is_file(),
        "questionbank_present": (entry / "questionbank.html").is_file(),
        "student_css_present": (entry / "student.css").is_file(),
        "student_js_present": (entry / "student.js").is_file(),
        "teacher_private_link_absent": "teacher/index.private.html" not in index
        and all(
            "teacher/index.private.html"
            not in (entry / name).read_text(encoding="utf-8")
            for name in ("index.html", "prelearning.html", "questionbank.html")
        ),
    }
    failed = [key for key, value in checks.items() if value is not True]
    if failed:
        raise StudentEntryAcceptanceError(
            "main_entry_validation_failed:" + ",".join(failed)
        )
    return {"validation_status": PASS_STATUS, **checks}


def _acceptance_sample_html(student: Mapping[str, Any]) -> str:
    questions = student.get("questions")
    if not isinstance(questions, list) or len(questions) != master.EXPECTED_RUNTIME_ITEMS:
        raise StudentEntryAcceptanceError("student_question_authority_invalid")
    sections: list[str] = []
    for stage_id, title, _families in student_builder.STAGE_DEFINITIONS:
        rows = [row for row in questions if row.get("layout_stage_id") == stage_id]
        if not rows:
            raise StudentEntryAcceptanceError(f"sample_stage_missing:{stage_id}")
        selected = rows[:2]
        sections.append(
            '<section class="print-page">'
            f'<h1>{html.escape(title)}</h1>'
            f'<p class="muted">Chromium layout acceptance｜{len(rows)}題中的代表樣張</p>'
            + "".join(student_builder._question_card(row) for row in selected)
            + "</section>"
        )
    return f"""<!doctype html><html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unit 01 QuestionBank Chromium Acceptance</title>
<link rel="stylesheet" href="student.css"></head><body>
{''.join(sections)}</body></html>"""


def discover_chromium(explicit: Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    configured = os.environ.get("A1FS_CHROMIUM_PATH", "").strip()
    if configured:
        candidates.append(Path(configured))
    for name in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
        "msedge",
    ):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for variable, relative in (
        ("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"),
        ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe"),
        ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe"),
        ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
        ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
    ):
        base = os.environ.get(variable, "").strip()
        if base:
            candidates.append(Path(base) / relative)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise StudentEntryAcceptanceError("chromium_executable_missing")


def _run_browser(
    chromium: Path,
    *,
    source_html: Path,
    output_path: Path,
    mode: str,
) -> dict[str, Any]:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="a1fs-chromium-") as profile:
        common = [
            str(chromium),
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--allow-file-access-from-files",
            "--run-all-compositor-stages-before-draw",
            f"--user-data-dir={profile}",
        ]
        if mode == "PDF":
            command = [
                *common,
                "--print-to-pdf-no-header",
                f"--print-to-pdf={output_path}",
                source_html.resolve().as_uri(),
            ]
        elif mode == "PNG":
            command = [
                *common,
                "--hide-scrollbars",
                "--window-size=1440,1200",
                f"--screenshot={output_path}",
                source_html.resolve().as_uri(),
            ]
        else:
            raise StudentEntryAcceptanceError(f"browser_mode_invalid:{mode}")
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
    if result.returncode != 0 or not output_path.is_file():
        raise StudentEntryAcceptanceError(
            f"chromium_render_failed:{mode}:{result.returncode}:"
            f"{result.stderr[-1000:]}"
        )
    identity = file_identity(output_path)
    if identity["bytes"] < 1024:
        raise StudentEntryAcceptanceError(f"chromium_output_too_small:{mode}")
    return {
        "mode": mode,
        "source_html": str(source_html),
        "output_path": str(output_path),
        **identity,
    }


def _pdf_page_count(path: Path) -> int:
    raw = Path(path).read_bytes()
    if not raw.startswith(b"%PDF"):
        raise StudentEntryAcceptanceError(f"pdf_signature_invalid:{path.name}")
    count = len(re.findall(rb"/Type\s*/Page\b", raw))
    if count <= 0:
        raise StudentEntryAcceptanceError(f"pdf_page_count_unreadable:{path.name}")
    return count


def _png_valid(path: Path) -> bool:
    return Path(path).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def build_acceptance(
    *,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    chromium_path: Path | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    disposable_product_root = Path(disposable_product_root).resolve()
    integration_report = master._integration_report(disposable_product_root)
    source_root = Path(str(integration_report["source_product_root"])).resolve()
    source_before = master.integration._product_identity(source_root)

    student_result = student_builder.build_student_package(
        disposable_product_root=disposable_product_root,
        approved_content=approved_content,
        output_root=output_root,
    )
    package_root = Path(str(student_result["output_root"])).resolve()
    package_report = master.load(package_root / master.REPORT_NAME)
    teacher_before = dict(package_report.get("teacher_file_identities") or {})
    if len(teacher_before) != 2:
        raise StudentEntryAcceptanceError("teacher_identity_contract_missing")

    product_version, secure_static_root = _product_static_root(
        disposable_product_root
    )
    entry_root = _copy_learner_entry(package_root, secure_static_root)
    entry_result = _patch_main_entry(secure_static_root)

    acceptance_root = package_root / "acceptance"
    if acceptance_root.exists():
        shutil.rmtree(acceptance_root)
    acceptance_root.mkdir(parents=True)
    shutil.copy2(package_root / "learner/student.css", acceptance_root / "student.css")
    student = master.load(
        package_root / "learner" / student_builder.STUDENT_DATA_NAME
    )
    sample_path = acceptance_root / "questionbank_stage_sample.html"
    atomic_text(sample_path, _acceptance_sample_html(student))

    chromium = discover_chromium(chromium_path)
    version_probe = subprocess.run(
        [str(chromium), "--version"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if version_probe.returncode != 0:
        raise StudentEntryAcceptanceError("chromium_version_probe_failed")
    prelearning_pdf = acceptance_root / "unit01_prelearning_chromium.pdf"
    sample_pdf = acceptance_root / "unit01_questionbank_stage_sample_chromium.pdf"
    prelearning_png = acceptance_root / "unit01_prelearning_chromium.png"
    sample_png = acceptance_root / "unit01_questionbank_stage_sample_chromium.png"
    renders = [
        _run_browser(
            chromium,
            source_html=package_root / "learner/prelearning.html",
            output_path=prelearning_pdf,
            mode="PDF",
        ),
        _run_browser(
            chromium,
            source_html=sample_path,
            output_path=sample_pdf,
            mode="PDF",
        ),
        _run_browser(
            chromium,
            source_html=package_root / "learner/prelearning.html",
            output_path=prelearning_png,
            mode="PNG",
        ),
        _run_browser(
            chromium,
            source_html=sample_path,
            output_path=sample_png,
            mode="PNG",
        ),
    ]
    prelearning_pages = _pdf_page_count(prelearning_pdf)
    sample_pages = _pdf_page_count(sample_pdf)
    if prelearning_pages < EXPECTED_PRELEARNING_PAGES:
        raise StudentEntryAcceptanceError(
            f"prelearning_pdf_page_count_invalid:{prelearning_pages}"
        )
    if sample_pages < EXPECTED_SAMPLE_PAGES:
        raise StudentEntryAcceptanceError(
            f"questionbank_sample_pdf_page_count_invalid:{sample_pages}"
        )
    if not _png_valid(prelearning_png) or not _png_valid(sample_png):
        raise StudentEntryAcceptanceError("chromium_png_signature_invalid")

    teacher_after = {
        name: master.file_identity(package_root / name)
        for name in teacher_before
    }
    if teacher_after != teacher_before:
        raise StudentEntryAcceptanceError("teacher_files_changed")
    source_after = master.integration._product_identity(source_root)
    if source_after != source_before:
        raise StudentEntryAcceptanceError("source_product_identity_changed")

    files = {
        str(path.relative_to(package_root)).replace("\\", "/"): file_identity(path)
        for path in (
            sample_path,
            acceptance_root / "student.css",
            prelearning_pdf,
            sample_pdf,
            prelearning_png,
            sample_png,
            entry_root / "index.html",
            entry_root / "prelearning.html",
            entry_root / "questionbank.html",
            entry_root / "student.css",
            entry_root / "student.js",
        )
    }
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "product_version": product_version,
        "runtime_item_count": student_result["runtime_item_count"],
        "student_package_artifact_sha256": student_result["artifact_sha256"],
        "chromium_executable": str(chromium),
        "chromium_version": version_probe.stdout.strip()
        or version_probe.stderr.strip(),
        "chromium_render_count": len(renders),
        "chromium_renders": renders,
        "prelearning_pdf_page_count": prelearning_pages,
        "questionbank_sample_pdf_page_count": sample_pages,
        "prelearning_pdf_pass": True,
        "questionbank_stage_sample_pdf_pass": True,
        "chromium_screenshot_pass": True,
        "main_product_entry": entry_result,
        "main_product_entry_integrated_in_disposable": True,
        "authenticated_static_boundary_required": True,
        "teacher_files_unchanged": True,
        "teacher_file_identities": teacher_before,
        "source_product_root_unchanged": True,
        "second_question_bank_created": False,
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "files": files,
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**core, "readback_sha256": digest(core)}
    report_path = package_root / REPORT_NAME
    atomic_json(report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disposable-product-root", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, required=True)
    parser.add_argument("--chromium-path", type=Path)
    parser.add_argument("--output-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_acceptance(
        disposable_product_root=args.disposable_product_root,
        approved_content=master.load(args.approved_content),
        chromium_path=args.chromium_path,
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"STATUS={result['status']}")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
