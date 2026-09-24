#!/usr/bin/env python3
"""Materialize accepted Unit04 Q10R1 Forms01..20 as learner-safe Chromium PDFs.

Q10R2 is a read-only delivery consumer over the merged Unit04 Q10R1
learner-facing projection. It preserves the locked Q10 runtime, selected item,
candidate, QuestionBank, sentence, scene, learner-state, and scoring identities.
Learner HTML stays owned by Q10R1; PDF rendering reuses the accepted Unit01
headerless Chromium runner and PDF page counter. Q10R2 adds print-only
pagination safety to its disposable local HTML derivative so one learner
activity is never split across PDF pages.

Machine acceptance proves the exact 20 x 40 denominator, answer-key binding,
Unit04 evidence constraints, output identity, and PDF readability. Actual human
visual and pedagogical review remains SHA-bound and pending until locally
rendered PDFs are returned for review.
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
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as u04r1,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_acceptance,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only PDF materialization consumer over merged Unit04 Q10R1 learner "
    "forms. Reuses the accepted Unit04 learner HTML projection and Unit01 "
    "headerless Chromium runner; adds only print pagination safety to disposable "
    "PDF-derivative HTML and creates no QuestionBank item, sentence, scene, "
    "selector, runtime, learner-state, scoring, Unit05, A2, or relation authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U04Q10R2_Unit04LearnerPDFMaterializationAndVisualAcceptance"
SCHEMA_VERSION = "a1fs.v1.u04.q10r2.learner_pdf_materialization.v1"
PASS_STATUS = "PASS_A1FS_V1_U04Q10R2_UNIT04_LEARNER_PDF_MATERIALIZATION"
NEXT_SHORT_STEP = (
    "A1FS-V1-U04Q10R2R1_Unit04ActualPdfHumanVisualPedagogicalAcceptance"
)

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
ANSWER_KEY_BINDINGS = 800
SCENE_BOUND_COUNT = 760
AT_TEXT_BOUND_COUNT = 40
MANIFEST_NAME = "unit04_form01_20_pdf_materialization_manifest.private.json"
DEFAULT_OUTPUT_ROOT = Path(
    ".local/a1fs_v1/review/unit04_forms01_20_pdf_materialization"
)
UNIT01_HEADERLESS_BROWSER_RUNNER = u01_pdf._run_pdf_browser_headerless
UNIT01_PDF_PAGE_COUNTER = chromium_acceptance._pdf_page_count
PDF_PRINT_SAFETY_STYLE_ID = "u04-q10r2-print-safety"
PDF_PRINT_SAFETY_STYLE = f"""
<style id="{PDF_PRINT_SAFETY_STYLE_ID}">
@media print {{
  article.activity {{
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .activity-heading,
  section.unit04-section > h2 {{
    break-after: avoid;
    page-break-after: avoid;
  }}
}}
</style>
""".strip()


class Unit04PdfMaterializationError(ValueError):
    """Fail-closed Unit04 PDF materialization or learner-facing defect."""


def _file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _pdf_safe_html(rendered_html: str) -> str:
    """Add print-only pagination safety without changing Q10R1 learner content."""
    head_close = "</head>"
    if head_close not in rendered_html:
        raise Unit04PdfMaterializationError("LEARNER_HTML_HEAD_MISSING")
    if PDF_PRINT_SAFETY_STYLE_ID in rendered_html:
        raise Unit04PdfMaterializationError("PDF_PRINT_SAFETY_ALREADY_PRESENT")
    return rendered_html.replace(
        head_close,
        f"{PDF_PRINT_SAFETY_STYLE}\n{head_close}",
        1,
    )


def _validate_source(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if str(report.get("status") or "") != u04r1.PASS_STATUS:
        raise Unit04PdfMaterializationError(
            f"SOURCE_STATUS_INVALID:{report.get('status')}"
        )
    if str(report.get("task_id") or "") != u04r1.TASK_ID:
        raise Unit04PdfMaterializationError(
            f"SOURCE_TASK_INVALID:{report.get('task_id')}"
        )
    if str(report.get("next_short_step") or "") != TASK_ID:
        raise Unit04PdfMaterializationError(
            f"SOURCE_NEXT_STEP_INVALID:{report.get('next_short_step')}"
        )

    acceptance = dict(report.get("acceptance") or {})
    expected_counts = {
        "form_count": FORM_COUNT,
        "activity_count": TOTAL_ACTIVITIES,
        "rendered_activity_count": TOTAL_ACTIVITIES,
        "answer_key_binding_count": ANSWER_KEY_BINDINGS,
        "scene_bound_evidence_activity_count": SCENE_BOUND_COUNT,
        "at_text_bound_activity_count": AT_TEXT_BOUND_COUNT,
        "at_scene_ref_render_count": 0,
        "fabricated_scene_ref_count": 0,
        "semantic_equivalent_distractor_count": 0,
        "duplicate_learner_visible_choice_count": 0,
        "selected_relation_answer_leak_count": 0,
        "within_form_exact_duplicate_count": 0,
        "within_form_normalized_duplicate_count": 0,
    }
    for key, value in expected_counts.items():
        if int(acceptance.get(key, -1)) != value:
            raise Unit04PdfMaterializationError(
                f"SOURCE_ACCEPTANCE_DRIFT:{key}:{acceptance.get(key)}:{value}"
            )
    if acceptance.get("task_family_coverage") != "10/10":
        raise Unit04PdfMaterializationError("SOURCE_TASK_FAMILY_COVERAGE_DRIFT")
    if acceptance.get("target_relation_coverage") != "8/8":
        raise Unit04PdfMaterializationError("SOURCE_RELATION_COVERAGE_DRIFT")
    if acceptance.get("communicative_function_coverage") != "6/6":
        raise Unit04PdfMaterializationError("SOURCE_FUNCTION_COVERAGE_DRIFT")
    if int(report.get("html_form_count", -1)) != FORM_COUNT:
        raise Unit04PdfMaterializationError("SOURCE_HTML_FORM_COUNT_DRIFT")
    if int(report.get("html_activity_count", -1)) != TOTAL_ACTIVITIES:
        raise Unit04PdfMaterializationError("SOURCE_HTML_ACTIVITY_COUNT_DRIFT")
    if len(list(report.get("answer_key_bindings") or [])) != ANSWER_KEY_BINDINGS:
        raise Unit04PdfMaterializationError("SOURCE_ANSWER_KEY_BINDING_DRIFT")

    runtime_identity = str(report.get("source_runtime_identity_sha256") or "")
    item_identity = str(report.get("source_item_identity_sha256") or "")
    if not runtime_identity or not item_identity:
        raise Unit04PdfMaterializationError("SOURCE_IDENTITY_MISSING")

    boundaries = dict(report.get("claim_boundaries") or {})
    if not boundaries or any(value is not False for value in boundaries.values()):
        raise Unit04PdfMaterializationError("SOURCE_CLAIM_BOUNDARY_DRIFT")

    forms = list(report.get("learner_forms") or [])
    if len(forms) != FORM_COUNT:
        raise Unit04PdfMaterializationError(
            f"SOURCE_FORM_COUNT_INVALID:{len(forms)}:{FORM_COUNT}"
        )
    ordinals = [int(form.get("form_ordinal", -1)) for form in forms]
    if ordinals != list(range(1, FORM_COUNT + 1)):
        raise Unit04PdfMaterializationError(
            f"SOURCE_FORM_SEQUENCE_INVALID:{ordinals}"
        )
    for ordinal, form in enumerate(forms, start=1):
        activities = list(form.get("activities") or [])
        if len(activities) != ACTIVITIES_PER_FORM:
            raise Unit04PdfMaterializationError(
                f"SOURCE_ACTIVITY_COUNT_INVALID:F{ordinal:02d}:{len(activities)}"
            )
        # Q10R1 owns learner-safe HTML, evidence projection, leak guards, and TF07 repair.
        u04r1.render_form_html(form)
    return forms


def materialize_twenty_form_pdfs(
    *,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    source_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report = dict(source_report or u04r1.build_acceptance_report())
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
        rendered_html = _pdf_safe_html(u04r1.render_form_html(form))
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
            raise Unit04PdfMaterializationError(
                f"PDF_OUTPUT_MISSING:F{ordinal:02d}"
            )
        pdf_identity = _file_identity(pdf_path)
        if pdf_identity["bytes"] < 1024:
            raise Unit04PdfMaterializationError(
                f"PDF_OUTPUT_TOO_SMALL:F{ordinal:02d}:{pdf_identity['bytes']}"
            )
        page_count = int(count_pages(pdf_path))
        if page_count < 1:
            raise Unit04PdfMaterializationError(
                f"PDF_PAGE_COUNT_INVALID:F{ordinal:02d}:{page_count}"
            )
        artifacts.append(
            {
                "form_id": str(form.get("form_id") or f"UNIT04_FORM_{ordinal:02d}"),
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
        raise Unit04PdfMaterializationError(
            f"MATERIALIZED_PDF_COUNT_INVALID:{len(artifacts)}:{FORM_COUNT}"
        )
    pdf_hashes = [row["pdf_sha256"] for row in artifacts]
    if len(set(pdf_hashes)) != FORM_COUNT:
        raise Unit04PdfMaterializationError(
            f"PDF_SHA256_NOT_DISTINCT:{len(set(pdf_hashes))}:{FORM_COUNT}"
        )

    source_readback = {
        "answer_key_binding_count": acceptance["answer_key_binding_count"],
        "task_family_coverage": acceptance["task_family_coverage"],
        "target_relation_coverage": acceptance["target_relation_coverage"],
        "communicative_function_coverage": acceptance["communicative_function_coverage"],
        "scene_bound_evidence_activity_count": acceptance[
            "scene_bound_evidence_activity_count"
        ],
        "at_text_bound_activity_count": acceptance["at_text_bound_activity_count"],
        "fabricated_scene_ref_count": acceptance["fabricated_scene_ref_count"],
        "selected_relation_answer_leak_count": acceptance[
            "selected_relation_answer_leak_count"
        ],
        "within_form_exact_duplicate_count": acceptance[
            "within_form_exact_duplicate_count"
        ],
        "within_form_normalized_duplicate_count": acceptance[
            "within_form_normalized_duplicate_count"
        ],
        "learner_visible_exact_duplicate_count": acceptance[
            "learner_visible_exact_duplicate_count"
        ],
        "learner_visible_normalized_duplicate_count": acceptance[
            "learner_visible_normalized_duplicate_count"
        ],
    }

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_u04q10r1_task_id": str(report.get("task_id") or ""),
        "source_u04q10r1_status": str(report.get("status") or ""),
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
        "stage_activity_counts": dict(acceptance.get("stage_activity_counts") or {}),
        "form_count": FORM_COUNT,
        "materialized_html_count": FORM_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "materialized_activity_count": TOTAL_ACTIVITIES,
        "machine_preflight_pass_count": FORM_COUNT,
        "learner_facing_machine_acceptance_pass_count": FORM_COUNT,
        "human_visual_review_pending_count": FORM_COUNT,
        "human_pedagogical_review_pending_count": FORM_COUNT,
        "unit04_form01_20_pdf_machine_acceptance": (
            "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
        ),
        "unit04_form01_20_human_acceptance": (
            "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
        ),
        "source_800_runtime_rows_mutated": False,
        "source_selected_item_identities_mutated": False,
        "source_candidate_identities_mutated": False,
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "sentence_assets_modified": False,
        "scene_authority_modified": False,
        "q03_redone": False,
        "q07_redone": False,
        "q08_redone": False,
        "q09_redone": False,
        "q10_redone": False,
        "second_questionbank_authority_created": False,
        "second_selector_created": False,
        "second_renderer_created": False,
        "runtime_authority_modified": False,
        "learner_state_modified": False,
        "scoring_authority_modified": False,
        "unit05_to_unit24_modified": False,
        "motion_directional_from_into_to_activated": False,
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
        f"{manifest['unit04_form01_20_pdf_machine_acceptance']}"
    )
    print(
        "HUMAN_ACCEPTANCE="
        f"{manifest['unit04_form01_20_human_acceptance']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
