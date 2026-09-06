#!/usr/bin/env python3
"""Repair Unit04 Q10R2 actual-PDF pagination without changing learner content.

This successor adapter consumes the already accepted Q10R2 materializer and
adds print-only pagination guards around the existing learner HTML. It does not
change any of the 800 learner activities, QuestionBank/runtime/candidate/item
identities, answers, sentence/scene evidence, relation authority, or scoring.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as u04r1,
)
from product.a1fs_v1_2_1 import (
    u04q10r2_unit04_learner_pdf_materialization_and_visual_acceptance as base,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "PDF-only pagination adapter over the merged Unit04 Q10R2 materializer. "
    "It injects print CSS that keeps each existing learner activity together "
    "and keeps section headings with following content. It authors no learner "
    "content and changes no QuestionBank/runtime/item/candidate/sentence/scene/"
    "relation/scoring identity."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U04Q10R2R1_Unit04ActualPdfPaginationRepair"
PASS_STATUS = "PASS_A1FS_V1_U04Q10R2R1_UNIT04_ACTUAL_PDF_PAGINATION_REPAIR"
NEXT_SHORT_STEP = (
    "A1FS-V1-U04Q10R2R1_Unit04ActualPdfHumanVisualPedagogicalAcceptance"
)

FORM_COUNT = base.FORM_COUNT
TOTAL_ACTIVITIES = base.TOTAL_ACTIVITIES
DEFAULT_OUTPUT_ROOT = base.DEFAULT_OUTPUT_ROOT
MANIFEST_NAME = base.MANIFEST_NAME

PDF_PAGINATION_STYLE_ID = "u04-q10r2r1-pdf-pagination"
PDF_PAGINATION_STYLE = f"""<style id=\"{PDF_PAGINATION_STYLE_ID}\">
@media print {{
  .unit04-section > h2 {{ break-after: avoid; page-break-after: avoid; }}
  article.activity {{ break-inside: avoid; page-break-inside: avoid; }}
  .activity-heading {{ break-after: avoid; page-break-after: avoid; }}
  .stimulus, .prompt, .choices {{ break-inside: avoid; page-break-inside: avoid; }}
}}
</style>"""

_ORIGINAL_RENDER_FORM_HTML = u04r1.render_form_html


class Unit04PdfPaginationRepairError(ValueError):
    """Fail-closed PDF pagination repair error."""


def inject_pdf_pagination_guards(rendered_html: str) -> str:
    """Inject print-only pagination CSS while preserving all learner text/markup."""
    html = str(rendered_html)
    if PDF_PAGINATION_STYLE_ID in html:
        raise Unit04PdfPaginationRepairError("PAGINATION_STYLE_ALREADY_PRESENT")
    marker = "</head>"
    if html.count(marker) != 1:
        raise Unit04PdfPaginationRepairError(
            f"HTML_HEAD_BOUNDARY_INVALID:{html.count(marker)}"
        )
    repaired = html.replace(marker, PDF_PAGINATION_STYLE + marker, 1)
    if repaired.count('<article class="activity">') != html.count(
        '<article class="activity">'
    ):
        raise Unit04PdfPaginationRepairError("ACTIVITY_MARKUP_MUTATED")
    if repaired.replace(PDF_PAGINATION_STYLE, "", 1) != html:
        raise Unit04PdfPaginationRepairError("NON_STYLE_HTML_MUTATED")
    return repaired


def render_form_html_for_pdf(form: Mapping[str, Any]) -> str:
    return inject_pdf_pagination_guards(_ORIGINAL_RENDER_FORM_HTML(form))


def materialize_twenty_form_pdfs(
    *,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    source_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Delegate to Q10R2 while temporarily adapting only its PDF HTML projection."""
    prior_renderer = u04r1.render_form_html
    if prior_renderer is not _ORIGINAL_RENDER_FORM_HTML:
        raise Unit04PdfPaginationRepairError("SOURCE_RENDERER_ALREADY_PATCHED")
    u04r1.render_form_html = render_form_html_for_pdf
    try:
        manifest = base.materialize_twenty_form_pdfs(
            output_root=output_root,
            chromium_path=chromium_path,
            browser_runner=browser_runner,
            pdf_page_counter=pdf_page_counter,
            source_report=source_report,
        )
    finally:
        u04r1.render_form_html = prior_renderer

    if int(manifest.get("form_count", -1)) != FORM_COUNT:
        raise Unit04PdfPaginationRepairError("FORM_COUNT_DRIFT")
    if int(manifest.get("materialized_activity_count", -1)) != TOTAL_ACTIVITIES:
        raise Unit04PdfPaginationRepairError("ACTIVITY_COUNT_DRIFT")
    if bool(manifest.get("source_800_runtime_rows_mutated")):
        raise Unit04PdfPaginationRepairError("SOURCE_RUNTIME_MUTATED")
    if bool(manifest.get("source_selected_item_identities_mutated")):
        raise Unit04PdfPaginationRepairError("SOURCE_ITEM_IDENTITY_MUTATED")

    manifest["pagination_repair_task_id"] = TASK_ID
    manifest["pagination_repair_status"] = PASS_STATUS
    manifest["pdf_pagination_guard_form_count"] = FORM_COUNT
    manifest["pdf_pagination_guard_activity_count"] = TOTAL_ACTIVITIES
    manifest["pdf_pagination_policy"] = {
        "activity_break_inside": "avoid",
        "section_heading_break_after": "avoid",
        "print_only": True,
        "learner_text_mutated": False,
        "learner_activity_markup_mutated": False,
    }
    manifest["next_short_step"] = NEXT_SHORT_STEP
    base.u01_pdf._atomic_json(Path(output_root).resolve() / MANIFEST_NAME, manifest)
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
    print(f"PAGINATION_GUARD_FORMS={manifest['pdf_pagination_guard_form_count']}")
    print(f"PAGINATION_GUARD_ACTIVITIES={manifest['pdf_pagination_guard_activity_count']}")
    print(f"HUMAN_ACCEPTANCE={manifest['unit04_form01_20_human_acceptance']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
