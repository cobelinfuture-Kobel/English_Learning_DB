#!/usr/bin/env python3
"""Materialize accepted Unit03 Forms01..20 as learner-safe Chromium PDFs.

U03SCFV2R2 is a product-level delivery consumer over the already-accepted
U03SCFV2R1 learner-facing Forms01..20 projection. It does not regenerate or
reselect the locked 800 runtime rows and does not author or mutate QuestionBank
items, SentenceAssets, Q6/Q9/Q10 authority, selectors, learner state, or scoring.
Unit03 learner HTML remains owned by U03SCFV2R1; PDF rendering reuses the
accepted Unit01 headerless Chromium runner and PDF page counter.

Machine acceptance proves the exact 20 x 40 learner-facing denominator, source
identity preservation, output identity, and PDF readability. Actual human visual
and pedagogical acceptance remains SHA-bound and explicitly pending until the
locally rendered PDFs are returned for review.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from product.a1fs_v1_2_1 import (
    u03scfv2r1_unit03_twenty_form_learner_facing_acceptance as u03r1,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_acceptance,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only product PDF materialization consumer over already-accepted "
    "U03SCFV2R1 Forms01-20. It reuses the accepted Unit03 learner HTML renderer "
    "and Unit01 headerless Chromium runner, preserves the locked 800 runtime, "
    "selected-item and candidate identities, and creates no QuestionBank item, "
    "SentenceAsset, Q6/Q9/Q10 authority, selector, runtime/state/scoring authority, "
    "Unit04-24 content, or A2 authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U03SCFV2R2_"
    "Unit03Form01To20LearnerPdfMaterializationAndVisualAcceptance"
)
SCHEMA_VERSION = "a1fs.v1.u03scfv2r2.form01_20_learner_pdf_materialization.v1"
PASS_STATUS = (
    "PASS_A1FS_V1_U03SCFV2R2_"
    "UNIT03_FORM01_20_LEARNER_PDF_MATERIALIZATION"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U03SCFV2R2R1_"
    "Unit03Form01To20ActualPdfHumanVisualPedagogicalAcceptance"
)

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
REFERENCE_CHAIN_FIX_COUNT = 80
REFERENT_DEDUP_FIX_COUNT = 35
MANIFEST_NAME = "unit03_form01_20_pdf_materialization_manifest.private.json"
DEFAULT_OUTPUT_ROOT = Path(
    ".local/a1fs_v1/review/unit03_forms01_20_pdf_materialization"
)
UNIT01_HEADERLESS_BROWSER_RUNNER = u01_pdf._run_pdf_browser_headerless
UNIT01_PDF_PAGE_COUNTER = chromium_acceptance._pdf_page_count


class Unit03PdfMaterializationError(ValueError):
    """Fail-closed Unit03 PDF materialization or learner-facing defect."""


def _file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _validate_source(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if str(report.get("validation_status") or "") != u03r1.PASS_STATUS:
        raise Unit03PdfMaterializationError(
            f"U03SCFV2R1_SOURCE_STATUS_INVALID:{report.get('validation_status')}"
        )

    acceptance = dict(report.get("acceptance") or {})
    expected = {
        "form_count": FORM_COUNT,
        "activity_count": TOTAL_ACTIVITIES,
        "rendered_activity_count": TOTAL_ACTIVITIES,
    }
    for key, value in expected.items():
        if int(acceptance.get(key, -1)) != value:
            raise Unit03PdfMaterializationError(
                f"U03SCFV2R1_ACCEPTANCE_DRIFT:{key}:{acceptance.get(key)}:{value}"
            )
    if int(report.get("html_form_count", -1)) != FORM_COUNT:
        raise Unit03PdfMaterializationError("U03SCFV2R1_HTML_FORM_COUNT_DRIFT")
    if int(report.get("html_activity_count", -1)) != TOTAL_ACTIVITIES:
        raise Unit03PdfMaterializationError("U03SCFV2R1_HTML_ACTIVITY_COUNT_DRIFT")

    fixes = dict(report.get("presentation_fixes") or {})
    expected_fixes = {
        "reference_chain_answer_leak_fixes": REFERENCE_CHAIN_FIX_COUNT,
        "referent_semantic_duplicate_fixes": REFERENT_DEDUP_FIX_COUNT,
    }
    if fixes != expected_fixes:
        raise Unit03PdfMaterializationError(
            f"U03SCFV2R1_PRESENTATION_FIX_DRIFT:{fixes}:{expected_fixes}"
        )

    source_package_sha = str(report.get("source_package_sha256") or "")
    runtime_identity_sha = str(report.get("source_runtime_identity_sha256") or "")
    if not source_package_sha or not runtime_identity_sha:
        raise Unit03PdfMaterializationError("U03SCFV2R1_SOURCE_IDENTITY_MISSING")

    boundaries = dict(report.get("claim_boundaries") or {})
    forbidden_true = (
        "source_800_runtime_rows_mutated",
        "source_selected_item_identities_mutated",
        "source_candidate_identities_mutated",
        "source_questionbank_items_mutated",
        "source_sentence_assets_mutated",
        "q6_redone",
        "q9_redone",
        "q10_redone",
        "second_questionbank_authority_created",
        "second_selector_created",
        "second_renderer_created",
        "parallel_sentence_asset_schema_created",
        "learner_state_mutated",
        "scoring_authority_mutated",
        "a2_unlocked",
    )
    if any(boundaries.get(key) is not False for key in forbidden_true):
        raise Unit03PdfMaterializationError("U03SCFV2R1_CLAIM_BOUNDARY_DRIFT")

    forms = list(report.get("learner_forms") or [])
    if len(forms) != FORM_COUNT:
        raise Unit03PdfMaterializationError(
            f"SOURCE_FORM_COUNT_INVALID:{len(forms)}:{FORM_COUNT}"
        )
    ordinals = [int(form.get("form_ordinal", -1)) for form in forms]
    if ordinals != list(range(1, FORM_COUNT + 1)):
        raise Unit03PdfMaterializationError(
            f"SOURCE_FORM_SEQUENCE_INVALID:{ordinals}"
        )
    for ordinal, form in enumerate(forms, start=1):
        if int(form.get("learner_visible_activity_count", -1)) != ACTIVITIES_PER_FORM:
            raise Unit03PdfMaterializationError(
                f"SOURCE_ACTIVITY_COUNT_INVALID:F{ordinal:02d}"
            )
        # U03SCFV2R1 owns learner-safe HTML, presentation fixes, and leak guards.
        u03r1.render_form_html(form)
    return forms


def materialize_twenty_form_pdfs(
    *,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    source_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report = dict(source_report or u03r1.build_acceptance_report())
    forms = _validate_source(report)
    output_root = Path(output_root).resolve()
    html_root = output_root / "html"
    pdf_root = output_root / "pdf"
    html_root.mkdir(parents=True, exist_ok=True)
    pdf_root.mkdir(parents=True, exist_ok=True)

    chromium = (
        Path(chromium_path).resolve(strict=True)
        if chromium_path is not None
        else chromium_acceptance.discover_chromium()
    )
    run_browser = browser_runner or UNIT01_HEADERLESS_BROWSER_RUNNER
    count_pages = pdf_page_counter or UNIT01_PDF_PAGE_COUNTER

    artifacts: list[dict[str, Any]] = []
    for ordinal, form in enumerate(forms, start=1):
        html_path = html_root / f"Form{ordinal:02d}.html"
        pdf_path = pdf_root / f"Form{ordinal:02d}.pdf"
        rendered_html = u03r1.render_form_html(form)
        u01_pdf._atomic_text(html_path, rendered_html)
        html_identity = _file_identity(html_path)
        render_result = dict(
            run_browser(
                chromium,
                source_html=html_path,
                output_path=pdf_path,
                mode="PDF",
            )
        )
        if not pdf_path.is_file():
            raise Unit03PdfMaterializationError(
                f"PDF_OUTPUT_MISSING:F{ordinal:02d}"
            )
        pdf_identity = _file_identity(pdf_path)
        if pdf_identity["bytes"] < 1024:
            raise Unit03PdfMaterializationError(
                f"PDF_OUTPUT_TOO_SMALL:F{ordinal:02d}:{pdf_identity['bytes']}"
            )
        page_count = int(count_pages(pdf_path))
        if page_count < 1:
            raise Unit03PdfMaterializationError(
                f"PDF_PAGE_COUNT_INVALID:F{ordinal:02d}:{page_count}"
            )
        artifacts.append(
            {
                "form_id": str(form.get("form_id") or f"UNIT03_FORM_{ordinal:02d}"),
                "form_ordinal": ordinal,
                "progression_stage": str(form.get("progression_stage") or ""),
                "html_relative_path": f"html/Form{ordinal:02d}.html",
                "pdf_relative_path": f"pdf/Form{ordinal:02d}.pdf",
                "html_bytes": html_identity["bytes"],
                "html_sha256": html_identity["sha256"],
                "pdf_bytes": pdf_identity["bytes"],
                "pdf_sha256": pdf_identity["sha256"],
                "page_count": page_count,
                "learner_visible_activity_count": ACTIVITIES_PER_FORM,
                "machine_preflight": "PASS",
                "learner_facing_machine_acceptance": "PASS",
                "human_visual_review": "PENDING",
                "human_pedagogical_review": "PENDING",
                "browser_render": {
                    key: value
                    for key, value in render_result.items()
                    if key not in {"source_path", "output_path"}
                },
            }
        )

    if len(artifacts) != FORM_COUNT:
        raise Unit03PdfMaterializationError(
            f"MATERIALIZED_PDF_COUNT_INVALID:{len(artifacts)}:{FORM_COUNT}"
        )
    pdf_hashes = [row["pdf_sha256"] for row in artifacts]
    if len(set(pdf_hashes)) != FORM_COUNT:
        raise Unit03PdfMaterializationError(
            f"PDF_SHA256_NOT_DISTINCT:{len(set(pdf_hashes))}:{FORM_COUNT}"
        )

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_u03scfv2r1_task_id": str(report.get("task_id") or ""),
        "source_u03scfv2r1_status": str(report.get("validation_status") or ""),
        "source_u03scfv2_task_id": str(report.get("source_task_id") or ""),
        "source_u03scfv2_status": str(report.get("source_status") or ""),
        "source_package_sha256": str(report.get("source_package_sha256") or ""),
        "source_runtime_identity_sha256": str(
            report.get("source_runtime_identity_sha256") or ""
        ),
        "presentation_fixes": dict(report.get("presentation_fixes") or {}),
        "stage_activity_counts": dict(
            (report.get("acceptance") or {}).get("stage_activity_counts") or {}
        ),
        "form_count": FORM_COUNT,
        "materialized_html_count": FORM_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "materialized_activity_count": TOTAL_ACTIVITIES,
        "machine_preflight_pass_count": FORM_COUNT,
        "learner_facing_machine_acceptance_pass_count": FORM_COUNT,
        "human_visual_review_pending_count": FORM_COUNT,
        "human_pedagogical_review_pending_count": FORM_COUNT,
        "unit03_form01_20_pdf_machine_acceptance": (
            "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
        ),
        "unit03_form01_20_human_acceptance": (
            "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
        ),
        "source_800_runtime_rows_mutated": False,
        "source_selected_item_identities_mutated": False,
        "source_candidate_identities_mutated": False,
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "sentence_assets_modified": False,
        "q6_redone": False,
        "q9_redone": False,
        "q10_redone": False,
        "second_questionbank_authority_created": False,
        "second_selector_created": False,
        "second_renderer_created": False,
        "parallel_sentence_asset_schema_created": False,
        "runtime_authority_modified": False,
        "learner_state_modified": False,
        "scoring_authority_modified": False,
        "unit04_to_unit24_modified": False,
        "a2_unlocked": False,
        "artifacts": artifacts,
        "next_short_step": NEXT_SHORT_STEP,
    }
    u01_pdf._atomic_json(output_root / MANIFEST_NAME, manifest)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--chromium", type=Path)
    args = parser.parse_args(argv)
    manifest = materialize_twenty_form_pdfs(
        output_root=args.output_root,
        chromium_path=args.chromium,
    )
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={manifest['form_count']}")
    print(f"PDFS={manifest['materialized_pdf_count']}")
    print(f"ACTIVITIES={manifest['materialized_activity_count']}")
    print(
        "MACHINE_LEARNER_FACING_ACCEPTANCE="
        f"{manifest['unit03_form01_20_pdf_machine_acceptance']}"
    )
    print(
        "HUMAN_ACCEPTANCE="
        f"{manifest['unit03_form01_20_human_acceptance']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
