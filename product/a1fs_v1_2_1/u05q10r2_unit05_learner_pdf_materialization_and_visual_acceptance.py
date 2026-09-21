#!/usr/bin/env python3
"""Materialize accepted Unit05 Q10R1 Forms01..20 as learner-safe Chromium PDFs.

Unit05 Q10R2 is a read-only delivery consumer over the merged Unit05 Q10R1
learner-facing projection. Unit05 Q10R1 remains the sole direct content source.
Unit04 is not imported as content authority; only already-proven generic
presentation lessons are reflected here (20x40 denominator, identity
immutability, learner-safe rendering, and print-only pagination guards).

Machine acceptance proves the exact 20 x 40 denominator, source identity
preservation, output identity, PDF readability, and print-pagination guards.
Actual human visual and pedagogical review remains SHA-bound and pending until
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
    u05q10r1_unit05_learner_facing_pedagogical_acceptance as u05r1,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_acceptance,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only PDF materialization consumer over merged Unit05 Q10R1 learner "
    "forms. Unit05 Q10R1 is the sole direct content source. This module reuses "
    "the generic Unit01 headerless Chromium runner and injects print-only "
    "pagination CSS without changing learner text or activity markup. It creates "
    "no QuestionBank item, grammar, vocabulary, sentence, scene, function, "
    "selector, runtime, scoring, Reader360, Unit06, A2 or A2+ authority. Unit04 "
    "is comparison/alignment evidence only and is not consumed as Unit05 content."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U05Q10R2_Unit05LearnerPDFMaterializationAndVisualAcceptance"
SCHEMA_VERSION = "a1fs.v1.u05.q10r2.learner_pdf_materialization.v1"
PASS_STATUS = "PASS_A1FS_V1_U05Q10R2_UNIT05_LEARNER_PDF_MATERIALIZATION"
NEXT_SHORT_STEP = (
    "A1FS-V1-U05Q10R2R1_Unit05ActualPdfHumanVisualPedagogicalAcceptance"
)

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
ANSWER_KEY_BINDINGS = 800
CONTEXT_BOUND_COUNT = 578
STANDALONE_COUNT = 222
MANIFEST_NAME = "unit05_form01_20_pdf_materialization_manifest.private.json"
DEFAULT_OUTPUT_ROOT = Path(
    ".local/a1fs_v1/review/unit05_forms01_20_pdf_materialization"
)
UNIT01_HEADERLESS_BROWSER_RUNNER = u01_pdf._run_pdf_browser_headerless
UNIT01_PDF_PAGE_COUNTER = chromium_acceptance._pdf_page_count

PDF_PAGINATION_STYLE_ID = "u05-q10r2-pdf-pagination"
PDF_PAGINATION_STYLE = f"""<style id="{PDF_PAGINATION_STYLE_ID}">
@media print {{
  .unit05-section > h2 {{ break-after: avoid; page-break-after: avoid; }}
  article.activity {{ break-inside: avoid; page-break-inside: avoid; }}
  .activity-heading {{ break-after: avoid; page-break-after: avoid; }}
  .stimulus, .prompt, .choices {{ break-inside: avoid; page-break-inside: avoid; }}
}}
</style>"""


class Unit05PdfMaterializationError(ValueError):
    """Fail-closed Unit05 PDF materialization or learner-facing defect."""


def _file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inject_pdf_pagination_guards(rendered_html: str) -> str:
    """Inject print-only CSS while preserving all learner text and markup."""
    html = str(rendered_html)
    if PDF_PAGINATION_STYLE_ID in html:
        raise Unit05PdfMaterializationError("PAGINATION_STYLE_ALREADY_PRESENT")
    marker = "</head>"
    if html.count(marker) != 1:
        raise Unit05PdfMaterializationError(
            f"HTML_HEAD_BOUNDARY_INVALID:{html.count(marker)}"
        )
    repaired = html.replace(marker, PDF_PAGINATION_STYLE + marker, 1)
    if repaired.count('<article class="activity">') != html.count(
        '<article class="activity">'
    ):
        raise Unit05PdfMaterializationError("ACTIVITY_MARKUP_MUTATED")
    if repaired.replace(PDF_PAGINATION_STYLE, "", 1) != html:
        raise Unit05PdfMaterializationError("NON_STYLE_HTML_MUTATED")
    return repaired


def render_form_html_for_pdf(form: Mapping[str, Any]) -> str:
    return inject_pdf_pagination_guards(u05r1.render_form_html(form))


def _validate_source(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if str(report.get("status") or "") != u05r1.PASS_STATUS:
        raise Unit05PdfMaterializationError(
            f"SOURCE_STATUS_INVALID:{report.get('status')}"
        )
    if str(report.get("task_id") or "") != u05r1.TASK_ID:
        raise Unit05PdfMaterializationError(
            f"SOURCE_TASK_INVALID:{report.get('task_id')}"
        )
    if str(report.get("next_short_step") or "") != TASK_ID:
        raise Unit05PdfMaterializationError(
            f"SOURCE_NEXT_STEP_INVALID:{report.get('next_short_step')}"
        )

    acceptance = dict(report.get("acceptance") or {})
    expected_counts = {
        "form_count": FORM_COUNT,
        "activity_count": TOTAL_ACTIVITIES,
        "rendered_activity_count": TOTAL_ACTIVITIES,
        "answer_key_binding_count": ANSWER_KEY_BINDINGS,
        "context_bound_activity_count": CONTEXT_BOUND_COUNT,
        "standalone_activity_count": STANDALONE_COUNT,
        "within_form_exact_duplicate_count": 0,
        "within_form_normalized_duplicate_count": 0,
        "engineering_marker_visible_count": 0,
        "unit04_content_authority_consumed_count": 0,
    }
    for key, value in expected_counts.items():
        if int(acceptance.get(key, -1)) != value:
            raise Unit05PdfMaterializationError(
                f"SOURCE_ACCEPTANCE_DRIFT:{key}:{acceptance.get(key)}:{value}"
            )

    expected_coverage = {
        "task_family_coverage": "10/10",
        "communicative_function_coverage": "7/7",
        "frame_coverage": "6/6",
        "subject_class_coverage": "9/9",
    }
    for key, value in expected_coverage.items():
        if acceptance.get(key) != value:
            raise Unit05PdfMaterializationError(
                f"SOURCE_COVERAGE_DRIFT:{key}:{acceptance.get(key)}:{value}"
            )

    if int(report.get("html_form_count", -1)) != FORM_COUNT:
        raise Unit05PdfMaterializationError("SOURCE_HTML_FORM_COUNT_DRIFT")
    if int(report.get("html_activity_count", -1)) != TOTAL_ACTIVITIES:
        raise Unit05PdfMaterializationError("SOURCE_HTML_ACTIVITY_COUNT_DRIFT")
    if len(list(report.get("answer_key_bindings") or [])) != ANSWER_KEY_BINDINGS:
        raise Unit05PdfMaterializationError("SOURCE_ANSWER_KEY_BINDING_DRIFT")

    runtime_identity = str(report.get("source_runtime_identity_sha256") or "")
    item_identity = str(report.get("source_item_identity_sha256") or "")
    if not runtime_identity or not item_identity:
        raise Unit05PdfMaterializationError("SOURCE_IDENTITY_MISSING")

    alignment = dict(report.get("alignment_reference") or {})
    if alignment.get("unit04_role") != "COMPARISON_AND_ACCEPTANCE_PATTERN_ALIGNMENT_ONLY":
        raise Unit05PdfMaterializationError("UNIT04_ALIGNMENT_ROLE_DRIFT")
    if alignment.get("unit04_content_authority_consumed") is not False:
        raise Unit05PdfMaterializationError("UNIT04_CONTENT_AUTHORITY_CONSUMED")
    if alignment.get("unit05_q10_is_sole_direct_content_source") is not True:
        raise Unit05PdfMaterializationError("UNIT05_Q10_NOT_SOLE_DIRECT_CONTENT_SOURCE")

    boundaries = dict(report.get("claim_boundaries") or {})
    if not boundaries or any(value is not False for value in boundaries.values()):
        raise Unit05PdfMaterializationError("SOURCE_CLAIM_BOUNDARY_DRIFT")

    forms = list(report.get("learner_forms") or [])
    if len(forms) != FORM_COUNT:
        raise Unit05PdfMaterializationError(
            f"SOURCE_FORM_COUNT_INVALID:{len(forms)}:{FORM_COUNT}"
        )
    ordinals = [int(form.get("form_ordinal", -1)) for form in forms]
    if ordinals != list(range(1, FORM_COUNT + 1)):
        raise Unit05PdfMaterializationError(
            f"SOURCE_FORM_SEQUENCE_INVALID:{ordinals}"
        )
    for ordinal, form in enumerate(forms, start=1):
        activities = list(form.get("activities") or [])
        if len(activities) != ACTIVITIES_PER_FORM:
            raise Unit05PdfMaterializationError(
                f"SOURCE_ACTIVITY_COUNT_INVALID:F{ordinal:02d}:{len(activities)}"
            )
        # Q10R1 owns learner text, answerability, duplicate guards and progression.
        u05r1.render_form_html(form)
    return forms


def materialize_twenty_form_pdfs(
    *,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    source_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report = dict(source_report or u05r1.build_acceptance_report())
    forms = _validate_source(report)
    acceptance = dict(report["acceptance"])

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
        rendered_html = render_form_html_for_pdf(form)
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
            raise Unit05PdfMaterializationError(
                f"PDF_OUTPUT_MISSING:F{ordinal:02d}"
            )
        pdf_identity = _file_identity(pdf_path)
        if pdf_identity["bytes"] < 1024:
            raise Unit05PdfMaterializationError(
                f"PDF_OUTPUT_TOO_SMALL:F{ordinal:02d}:{pdf_identity['bytes']}"
            )
        page_count = int(count_pages(pdf_path))
        if page_count < 1:
            raise Unit05PdfMaterializationError(
                f"PDF_PAGE_COUNT_INVALID:F{ordinal:02d}:{page_count}"
            )

        artifacts.append(
            {
                "form_id": str(form.get("form_id") or f"UNIT05_FORM_{ordinal:02d}"),
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
                "pagination_guard": "PASS",
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
        raise Unit05PdfMaterializationError(
            f"MATERIALIZED_PDF_COUNT_INVALID:{len(artifacts)}:{FORM_COUNT}"
        )
    pdf_hashes = [row["pdf_sha256"] for row in artifacts]
    if len(set(pdf_hashes)) != FORM_COUNT:
        raise Unit05PdfMaterializationError(
            f"PDF_SHA256_NOT_DISTINCT:{len(set(pdf_hashes))}:{FORM_COUNT}"
        )

    source_readback = {
        "answer_key_binding_count": acceptance["answer_key_binding_count"],
        "task_family_coverage": acceptance["task_family_coverage"],
        "communicative_function_coverage": acceptance[
            "communicative_function_coverage"
        ],
        "frame_coverage": acceptance["frame_coverage"],
        "subject_class_coverage": acceptance["subject_class_coverage"],
        "context_bound_activity_count": acceptance["context_bound_activity_count"],
        "standalone_activity_count": acceptance["standalone_activity_count"],
        "within_form_exact_duplicate_count": acceptance[
            "within_form_exact_duplicate_count"
        ],
        "within_form_normalized_duplicate_count": acceptance[
            "within_form_normalized_duplicate_count"
        ],
        "engineering_marker_visible_count": acceptance[
            "engineering_marker_visible_count"
        ],
        "unit04_content_authority_consumed_count": acceptance[
            "unit04_content_authority_consumed_count"
        ],
    }

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_u05q10r1_task_id": str(report.get("task_id") or ""),
        "source_u05q10r1_status": str(report.get("status") or ""),
        "source_q10_task_id": str(report.get("source_task_id") or ""),
        "source_q10_status": str(report.get("source_status") or ""),
        "source_runtime_identity_sha256": str(
            report.get("source_runtime_identity_sha256") or ""
        ),
        "source_item_identity_sha256": str(
            report.get("source_item_identity_sha256") or ""
        ),
        "source_acceptance_readback": source_readback,
        "presentation_fixes": dict(report.get("presentation_fixes") or {}),
        "stage_activity_counts": dict(
            acceptance.get("stage_activity_counts") or {}
        ),
        "alignment_reference": {
            "unit04_role": "COMPARISON_AND_ACCEPTANCE_PATTERN_ALIGNMENT_ONLY",
            "unit04_content_authority_consumed": False,
            "unit05_q10r1_is_sole_direct_content_source": True,
            "print_pagination_guard_alignment_only": True,
        },
        "pdf_pagination_policy": {
            "activity_break_inside": "avoid",
            "section_heading_break_after": "avoid",
            "print_only": True,
            "learner_text_mutated": False,
            "learner_activity_markup_mutated": False,
        },
        "form_count": FORM_COUNT,
        "materialized_html_count": FORM_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "materialized_activity_count": TOTAL_ACTIVITIES,
        "pdf_pagination_guard_form_count": FORM_COUNT,
        "pdf_pagination_guard_activity_count": TOTAL_ACTIVITIES,
        "machine_preflight_pass_count": FORM_COUNT,
        "learner_facing_machine_acceptance_pass_count": FORM_COUNT,
        "human_visual_review_pending_count": FORM_COUNT,
        "human_pedagogical_review_pending_count": FORM_COUNT,
        "unit05_form01_20_pdf_machine_acceptance": (
            "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
        ),
        "unit05_form01_20_human_acceptance": (
            "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
        ),
        "unit04_used_as_unit05_content_authority": False,
        "source_800_runtime_rows_mutated": False,
        "source_selected_item_identities_mutated": False,
        "source_candidate_identities_mutated": False,
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "sentence_assets_modified": False,
        "scene_authority_modified": False,
        "communicative_function_authority_modified": False,
        "task_pedagogical_contract_modified": False,
        "q10_redone": False,
        "second_questionbank_authority_created": False,
        "second_selector_created": False,
        "second_renderer_created": False,
        "runtime_authority_modified": False,
        "learner_state_modified": False,
        "scoring_authority_modified": False,
        "unit05_current360_materialized": False,
        "unit05_spoken360_materialized": False,
        "unit05_pattern360_materialized": False,
        "be_interrogative_mastery_activated": False,
        "past_be_activated": False,
        "existential_there_be_activated": False,
        "present_continuous_mastery_activated": False,
        "a2_a2plus_unlocked": False,
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
        "PAGINATION_GUARD_FORMS="
        f"{manifest['pdf_pagination_guard_form_count']}"
    )
    print(
        "MACHINE_LEARNER_FACING_ACCEPTANCE="
        f"{manifest['unit05_form01_20_pdf_machine_acceptance']}"
    )
    print(
        "HUMAN_ACCEPTANCE="
        f"{manifest['unit05_form01_20_human_acceptance']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
