#!/usr/bin/env python3
"""Materialize Unit02 Forms01..16 as learner-safe Chromium PDFs.

U02FORM02 is a product-level consumer over the already-approved U02FORM01
student_form materialization. It does not select or author questions and does
not create a second runtime, renderer, scene authority, learner-state authority,
or scoring authority. Unit02 HTML remains owned by U02FORM01; PDF rendering
reuses the accepted Unit01 headerless Chromium runner and PDF page counter.

Machine acceptance proves the exact 16 x 40 learner-facing denominator, output
identity, page readability, and learner answer/private-field boundary. Human
visual and pedagogical review remains SHA-bound and explicitly pending.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_acceptance,
)
from ulga.builders import (
    build_a1fs_v1_u02form01_unit02_existing_learner_renderer_reuse_and_16x40_deterministic_form_materialization
    as u02form01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Product-level PDF consumer over already-approved U02FORM01 student forms; reuses accepted Unit01 headerless Chromium rendering and creates no QuestionBank item, SentenceAsset, canonical scene, selector, runtime/state/scoring authority, Unit03-24 content, audio/Speaking score, or A2 authority."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02FORM02_Unit02Form01To16ChromiumPdfMaterializationAndLearnerFacingAcceptance"
SCHEMA_VERSION = "a1fs.v1.u02form02.chromium_pdf_materialization_learner_acceptance.v1"
PASS_STATUS = "PASS_A1FS_V1_U02FORM02_UNIT02_FORM01_16_CHROMIUM_PDF_MATERIALIZATION_AND_LEARNER_FACING_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-U02FORM03_Unit02Form01To16HumanVisualPedagogicalAcceptance"

FORM_COUNT = 16
SCENE_COUNT = 4
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = FORM_COUNT * ACTIVITIES_PER_FORM
EXPECTED_SKILL_COUNTS = {"READING": 16, "WRITING": 24}
MANIFEST_NAME = "unit02_form01_16_pdf_materialization_manifest.private.json"
DEFAULT_OUTPUT_ROOT = Path(".local/a1fs_v1/review/unit02_forms01_16_pdf_materialization")
UNIT01_HEADERLESS_BROWSER_RUNNER = u01_pdf._run_pdf_browser_headerless
UNIT01_PDF_PAGE_COUNTER = chromium_acceptance._pdf_page_count


class Unit02PdfMaterializationError(ValueError):
    """Fail-closed Unit02 PDF materialization or learner-facing acceptance defect."""


def _file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _validate_source(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if str(payload.get("status") or "") != u02form01.PASS_STATUS:
        raise Unit02PdfMaterializationError(
            f"U02FORM01_SOURCE_STATUS_INVALID:{payload.get('status')}"
        )
    contract = payload.get("form_contract") or {}
    expected = {
        "form_count": FORM_COUNT,
        "scene_slots_per_form": SCENE_COUNT,
        "task_family_count": 10,
        "activities_per_scene": 10,
        "activities_per_form": ACTIVITIES_PER_FORM,
        "materialized_activity_count": TOTAL_ACTIVITIES,
    }
    for key, value in expected.items():
        if int(contract.get(key, -1)) != value:
            raise Unit02PdfMaterializationError(
                f"U02FORM01_CONTRACT_DRIFT:{key}:{contract.get(key)}:{value}"
            )
    if contract.get("q10_selection_recomputed") is not False:
        raise Unit02PdfMaterializationError("U02FORM01_Q10_SELECTION_RECOMPUTED")
    if contract.get("q10_selected_item_identity_mutated") is not False:
        raise Unit02PdfMaterializationError("U02FORM01_SELECTED_IDENTITY_MUTATED")

    forms = list(payload.get("student_forms") or [])
    if len(forms) != FORM_COUNT:
        raise Unit02PdfMaterializationError(
            f"SOURCE_FORM_COUNT_INVALID:{len(forms)}:{FORM_COUNT}"
        )
    ordinals = [int(form.get("form_ordinal", -1)) for form in forms]
    if ordinals != list(range(1, FORM_COUNT + 1)):
        raise Unit02PdfMaterializationError(f"SOURCE_FORM_SEQUENCE_INVALID:{ordinals}")
    for ordinal, form in enumerate(forms, start=1):
        if int(form.get("scene_count", -1)) != SCENE_COUNT:
            raise Unit02PdfMaterializationError(
                f"SOURCE_SCENE_COUNT_INVALID:F{ordinal:02d}"
            )
        if int(form.get("learner_visible_activity_count", -1)) != ACTIVITIES_PER_FORM:
            raise Unit02PdfMaterializationError(
                f"SOURCE_ACTIVITY_COUNT_INVALID:F{ordinal:02d}"
            )
        if dict(form.get("skill_counts") or {}) != EXPECTED_SKILL_COUNTS:
            raise Unit02PdfMaterializationError(
                f"SOURCE_SKILL_COUNTS_INVALID:F{ordinal:02d}"
            )
        # Source builder owns learner-safe HTML validation and answer/private guards.
        u02form01.render_form_html(form)
    return forms


def materialize_sixteen_form_pdfs(
    *,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    source_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(source_payload or u02form01.build_materialization())
    forms = _validate_source(payload)
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
        rendered_html = u02form01.render_form_html(form)
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
            raise Unit02PdfMaterializationError(
                f"PDF_OUTPUT_MISSING:F{ordinal:02d}"
            )
        pdf_identity = _file_identity(pdf_path)
        if pdf_identity["bytes"] < 1024:
            raise Unit02PdfMaterializationError(
                f"PDF_OUTPUT_TOO_SMALL:F{ordinal:02d}:{pdf_identity['bytes']}"
            )
        page_count = int(count_pages(pdf_path))
        if page_count < 1:
            raise Unit02PdfMaterializationError(
                f"PDF_PAGE_COUNT_INVALID:F{ordinal:02d}:{page_count}"
            )
        artifacts.append(
            {
                "form_id": str(form["form_id"]),
                "form_ordinal": ordinal,
                "progression_stage": str(form["progression_stage"]),
                "html_relative_path": f"html/Form{ordinal:02d}.html",
                "pdf_relative_path": f"pdf/Form{ordinal:02d}.pdf",
                "html_bytes": html_identity["bytes"],
                "html_sha256": html_identity["sha256"],
                "pdf_bytes": pdf_identity["bytes"],
                "pdf_sha256": pdf_identity["sha256"],
                "page_count": page_count,
                "scene_count": SCENE_COUNT,
                "learner_visible_activity_count": ACTIVITIES_PER_FORM,
                "skill_counts": dict(EXPECTED_SKILL_COUNTS),
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
        raise Unit02PdfMaterializationError(
            f"MATERIALIZED_PDF_COUNT_INVALID:{len(artifacts)}:{FORM_COUNT}"
        )
    pdf_hashes = [row["pdf_sha256"] for row in artifacts]
    if len(set(pdf_hashes)) != FORM_COUNT:
        raise Unit02PdfMaterializationError(
            f"PDF_SHA256_NOT_DISTINCT:{len(set(pdf_hashes))}:{FORM_COUNT}"
        )

    runtime_proof = dict(payload.get("runtime_proof") or {})
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_u02form01_task_id": str(payload.get("task_id") or ""),
        "source_u02form01_status": str(payload.get("status") or ""),
        "source_selection_identity_sha256": str(
            runtime_proof.get("source_selection_identity_sha256") or ""
        ),
        "form_count": FORM_COUNT,
        "materialized_html_count": FORM_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "materialized_activity_count": TOTAL_ACTIVITIES,
        "machine_preflight_pass_count": FORM_COUNT,
        "learner_facing_machine_acceptance_pass_count": FORM_COUNT,
        "human_visual_review_pending_count": FORM_COUNT,
        "human_pedagogical_review_pending_count": FORM_COUNT,
        "unit02_form01_16_pdf_machine_acceptance": "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE",
        "unit02_form01_16_human_acceptance": "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW",
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "sentence_assets_modified": False,
        "canonical_scene_authority_modified": False,
        "selector_modified": False,
        "runtime_authority_modified": False,
        "learner_state_modified": False,
        "scoring_authority_modified": False,
        "unit03_to_unit24_modified": False,
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
    manifest = materialize_sixteen_form_pdfs(
        output_root=args.output_root,
        chromium_path=args.chromium,
    )
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={manifest['form_count']}")
    print(f"PDFS={manifest['materialized_pdf_count']}")
    print(f"ACTIVITIES={manifest['materialized_activity_count']}")
    print(
        "MACHINE_LEARNER_FACING_ACCEPTANCE="
        f"{manifest['unit02_form01_16_pdf_machine_acceptance']}"
    )
    print(
        "HUMAN_ACCEPTANCE="
        f"{manifest['unit02_form01_16_human_acceptance']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())