#!/usr/bin/env python3
"""Materialize the accepted Unit04 Current360 / Spoken360 / Pattern360 readers as PDFs.

This is a read-only delivery consumer over the merged Reader360 final acceptance.
It does not author learner-facing English, mutate Current360, integrate Unit04
runtime/baseline, create worksheet questions, or unlock Unit05+/A2.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb02
from product.a1fs_v1_2_1 import u04r360_b01_reader_acceptance as reader
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_acceptance,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only PDF projection over merged GPT-5.6-authored Current360, Spoken360, "
    "and Pattern360 sources. Python renders validated source text and static UI "
    "labels only; it does not compose or repair learner-facing English."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U04R360-FULL360_CurrentSpokenPatternJsonPdfMaterialization"
SCHEMA_VERSION = "a1fs.v1.u04.reader360.json_pdf_materialization.v2"
PASS_STATUS = "PASS_A1FS_V1_U04R360_THREE_READER_JSON_PDF_MATERIALIZATION"
NEXT_SHORT_STEP = (
    "U04_READER360_FULL360_ThreePDFActualVisualPedagogicalAcceptance"
)

SPOKEN_PATH = Path(reader.SPOKEN_PATH)
PATTERN_PATH = Path(reader.PATTERN_PATH)
DEFAULT_OUTPUT_ROOT = Path(
    ".local/a1fs_v1/review/u04_reader360_three_pdf_materialization"
)
MANIFEST_NAME = "unit04_reader360_three_pdf_materialization_manifest.private.json"

OUTPUTS = {
    "current360": {
        "json": "Unit04_Current360_360.json",
        "html": "Unit04_Current360_ReadAloud_360.html",
        "pdf": "Unit04_Current360_ReadAloud_360.pdf",
        "title": "Unit 04 Current360",
        "subtitle": "Read-Aloud Reader",
    },
    "spoken360": {
        "json": "Unit04_Spoken360_360.json",
        "html": "Unit04_Spoken360_DialogueReader_360.html",
        "pdf": "Unit04_Spoken360_DialogueReader_360.pdf",
        "title": "Unit 04 Spoken360",
        "subtitle": "Dialogue Reader",
    },
    "pattern360": {
        "json": "Unit04_Pattern360_360.json",
        "html": "Unit04_Pattern360_SentenceFamilyReader_360.html",
        "pdf": "Unit04_Pattern360_SentenceFamilyReader_360.pdf",
        "title": "Unit 04 Pattern360",
        "subtitle": "Sentence-Family Reader A-G",
    },
}

UNIT01_HEADERLESS_BROWSER_RUNNER = u01_pdf._run_pdf_browser_headerless
UNIT01_PDF_PAGE_COUNTER = chromium_acceptance._pdf_page_count


class Reader360PdfMaterializationError(ValueError):
    """Fail-closed Reader360 PDF source or output defect."""


def _root(repo_root: Path | str | None) -> Path:
    return (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(value, encoding="utf-8")
    temp.replace(path)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _file_identity(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _semantic_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Reader360PdfMaterializationError(f"SOURCE_JSON_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Reader360PdfMaterializationError(
            f"SOURCE_JSON_OBJECT_REQUIRED:{path}"
        )
    return value


def _episode_number(episode_id: str) -> int:
    try:
        return int(episode_id.rsplit("E", 1)[1])
    except (IndexError, ValueError) as exc:
        raise Reader360PdfMaterializationError(
            f"INVALID_EPISODE_ID:{episode_id}"
        ) from exc


def _group_by_scene(
    rows: Sequence[Mapping[str, Any]],
) -> list[tuple[str, list[Mapping[str, Any]]]]:
    scene_order: list[str] = []
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        scene_id = str(row.get("micro_scene_id") or "")
        if not scene_id:
            raise Reader360PdfMaterializationError("MISSING_MICRO_SCENE_ID")
        if scene_id not in grouped:
            scene_order.append(scene_id)
        grouped[scene_id].append(row)
    return [(scene_id, grouped[scene_id]) for scene_id in scene_order]


def _validate_sources(
    *,
    root: Path,
    acceptance_report: Mapping[str, Any] | None = None,
    current_report: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    accepted = dict(acceptance_report or reader.build_acceptance_report(root))
    if accepted.get("status") != reader.STATUS:
        raise Reader360PdfMaterializationError(
            f"READER_ACCEPTANCE_STATUS_INVALID:{accepted.get('status')}"
        )

    exact = {
        "source_current360_episode_count": 360,
        "materialized_episode_count": 360,
        "spoken_entry_count": 360,
        "pattern_entry_count": 360,
        "current360_passage_alignment_count": 720,
        "current360_metadata_alignment_count": 720,
        "spoken_relation_alignment_count": 360,
        "pattern_family_semantic_count": 2520,
        "spoken_dialogue_duplicate_count": 0,
        "pattern_bundle_duplicate_count": 0,
        "a1_boundary_blocked_surface_count": 0,
    }
    for key, expected in exact.items():
        actual = accepted.get(key)
        if actual != expected:
            raise Reader360PdfMaterializationError(
                f"READER_ACCEPTANCE_DRIFT:{key}:{actual}:{expected}"
            )

    safety = dict(accepted.get("scope_safety") or {})
    if safety != {
        "pdf_materialized": False,
        "unit04_baseline_integrated": False,
        "current360_mutated": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
    }:
        raise Reader360PdfMaterializationError(
            f"READER_SCOPE_SAFETY_DRIFT:{safety}"
        )

    current = dict(
        current_report or neb02.build_unit04_neb02_natural_episode_bank_360(root)
    )
    if current.get("status") != neb02.STATUS:
        raise Reader360PdfMaterializationError(
            f"CURRENT360_STATUS_INVALID:{current.get('status')}"
        )
    current_rows = list(current.get("effective_episodes") or [])
    if len(current_rows) != 360:
        raise Reader360PdfMaterializationError(
            f"CURRENT360_COUNT_INVALID:{len(current_rows)}"
        )
    if len({str(row.get("episode_id") or "") for row in current_rows}) != 360:
        raise Reader360PdfMaterializationError("CURRENT360_IDENTITY_DUPLICATE")

    spoken = _load_json(root / SPOKEN_PATH)
    pattern = _load_json(root / PATTERN_PATH)
    srows = list(spoken.get("entries") or [])
    prows = list(pattern.get("entries") or [])
    if len(srows) != 360 or len(prows) != 360:
        raise Reader360PdfMaterializationError(
            f"READER_ROW_COUNT_INVALID:{len(srows)}:{len(prows)}"
        )

    expected_ids = [f"U04-NEB-E{i:03d}" for i in range(1, 361)]
    current_ids = sorted(
        (str(row.get("episode_id") or "") for row in current_rows),
        key=_episode_number,
    )
    spoken_ids = [str(row.get("source_episode_id") or "") for row in srows]
    pattern_ids = [str(row.get("source_episode_id") or "") for row in prows]
    if current_ids != expected_ids:
        raise Reader360PdfMaterializationError("CURRENT360_ID_RANGE_DRIFT")
    if spoken_ids != expected_ids or pattern_ids != expected_ids:
        raise Reader360PdfMaterializationError("READER_ID_RANGE_DRIFT")
    if spoken_ids != pattern_ids:
        raise Reader360PdfMaterializationError("CROSS_READER_ID_DRIFT")

    return accepted, current, spoken, pattern


def _base_css() -> str:
    return """
@page { size: A4; margin: 14mm 14mm 15mm; }
* { box-sizing: border-box; }
html, body { font-family: Arial, "Noto Sans", sans-serif; color: #111; }
body { font-size: 11.2pt; line-height: 1.48; margin: 0; }
.cover {
  min-height: 245mm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  break-after: page;
  page-break-after: always;
}
h1 { font-size: 26pt; margin: 0 0 4mm; }
h2 { font-size: 16pt; margin: 0 0 2mm; }
.sub { font-size: 15pt; margin-bottom: 8mm; }
.cover-meta { font-size: 11pt; line-height: 1.6; }
.scene-header {
  border-bottom: 1px solid #777;
  padding-bottom: 2mm;
  margin-bottom: 4mm;
}
.scene-title { font-size: 16pt; font-weight: 700; }
.scene-sub { font-size: 9pt; color: #555; margin-top: 1mm; }
.current-page {
  break-after: page;
  page-break-after: always;
}
.scene {
  break-before: page;
  page-break-before: always;
}
.episode {
  break-inside: avoid;
  page-break-inside: avoid;
  margin: 0 0 5mm;
}
.episode-id {
  font-weight: 700;
  font-size: 12pt;
  margin-bottom: 1.5mm;
}
.passage { margin: 1.2mm 0 2.4mm; }
.section-label {
  font-size: 8.8pt;
  font-weight: 700;
  letter-spacing: .4px;
  color: #555;
  margin: 1.8mm 0 .8mm;
}
.dialogue { margin: 1mm 0 0 3mm; }
.turn { margin: 1mm 0; }
.speaker { font-weight: 700; }
.pattern-page {
  break-after: page;
  page-break-after: always;
}
.family {
  margin: 2mm 0 2.4mm 2mm;
  break-inside: avoid;
  page-break-inside: avoid;
}
.family-name { font-weight: 700; }
.model { margin: .8mm 0 0 4mm; }
"""

def _doc(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        f"<style>{_base_css()}</style></head><body>{body}</body></html>"
    )


def _cover(*, title: str, subtitle: str, purpose: str) -> str:
    return f"""
<section class="cover">
  <h1>{html.escape(title)}</h1>
  <div class="sub">{html.escape(subtitle)}</div>
  <div class="cover-meta">
    <div>Unit 04 | A1/A1+</div>
    <div>360 episodes | 36 scenes | 12 life domains</div>
    <div>{html.escape(purpose)}</div>
  </div>
</section>
"""

def _scene_header(
    scene_id: str,
    first: Mapping[str, Any],
    *,
    continued: bool = False,
) -> str:
    scene_number = int(scene_id.rsplit("MS", 1)[1])
    domain = str(first.get("life_domain") or "").replace("_", " ").title()
    family = str(first.get("governed_scene_family") or "").replace("_", " ").title()
    suffix = " (continued)" if continued else ""
    return f"""
<div class="scene-header">
  <div class="scene-title">Scene {scene_number} - {html.escape(domain)}{suffix}</div>
  <div class="scene-sub">{html.escape(family)}</div>
</div>
"""


def _episode_label(episode_id: str) -> str:
    return f"E{_episode_number(episode_id):03d}"


def _chunks(rows: Sequence[Mapping[str, Any]], size: int) -> list[list[Mapping[str, Any]]]:
    return [list(rows[index:index + size]) for index in range(0, len(rows), size)]

def _tracking(row: Mapping[str, Any], id_key: str) -> str:
    relations = row.get("target_relations") or ""
    if isinstance(relations, list):
        relations = ",".join(str(value) for value in relations)
    return (
        f"{html.escape(str(row.get(id_key) or ''))}"
        f" | {html.escape(str(row.get('discourse_family') or ''))}"
        f" | Relations: {html.escape(str(relations))}"
    )


def _render_current_html(current: Mapping[str, Any]) -> str:
    rows = list(current["effective_episodes"])
    groups = _group_by_scene(rows)
    parts = [
        _cover(
            title=OUTPUTS["current360"]["title"],
            subtitle=OUTPUTS["current360"]["subtitle"],
            purpose="Read short connected contexts aloud and understand location meaning.",
        )
    ]
    for scene_id, scene_rows in groups:
        first = scene_rows[0]
        for page_index, page_rows in enumerate(_chunks(scene_rows, 5)):
            chunks = [
                '<section class="current-page">',
                _scene_header(scene_id, first, continued=page_index > 0),
            ]
            for row in page_rows:
                chunks.append(
                    '<article class="episode">'
                    f'<div class="episode-id">{_episode_label(str(row.get("episode_id") or ""))}</div>'
                    f'<div class="passage">{html.escape(str(row.get("passage") or ""))}</div>'
                    "</article>"
                )
            chunks.append("</section>")
            parts.append("".join(chunks))
    return _doc("Unit04 Current360 Read-Aloud Reader", "".join(parts))

def _render_spoken_html(spoken: Mapping[str, Any]) -> str:
    rows = list(spoken["entries"])
    groups = _group_by_scene(rows)
    parts = [
        _cover(
            title=OUTPUTS["spoken360"]["title"],
            subtitle=OUTPUTS["spoken360"]["subtitle"],
            purpose="Read the context, then practise the dialogue with a partner.",
        )
    ]
    for scene_id, scene_rows in groups:
        first = scene_rows[0]
        chunks = [f'<section class="scene">{_scene_header(scene_id, first)}']
        for row in scene_rows:
            chunks.append(
                '<article class="episode">'
                f'<div class="episode-id">{_episode_label(str(row.get("source_episode_id") or ""))}</div>'
                '<div class="section-label">READ</div>'
                f'<div class="passage">{html.escape(str(row.get("passage") or ""))}</div>'
                '<div class="section-label">SPEAK</div><div class="dialogue">'
            )
            for turn in list(row.get("dialogue_turns") or []):
                chunks.append(
                    '<div class="turn">'
                    f'<span class="speaker">{html.escape(str(turn.get("speaker") or ""))}:</span> '
                    f'{html.escape(str(turn.get("text") or ""))}'
                    "</div>"
                )
            chunks.append("</div></article>")
        chunks.append("</section>")
        parts.append("".join(chunks))
    return _doc("Unit04 Spoken360 Dialogue Reader", "".join(parts))

def _render_pattern_html(pattern: Mapping[str, Any]) -> str:
    rows = list(pattern["entries"])
    definitions = dict(
        pattern.get("pattern_definitions")
        or pattern.get("family_definitions")
        or {}
    )
    groups = _group_by_scene(rows)
    parts = [
        _cover(
            title=OUTPUTS["pattern360"]["title"],
            subtitle=OUTPUTS["pattern360"]["subtitle"],
            purpose="Use the same context to practise sentence families A-G.",
        )
    ]
    for scene_id, scene_rows in groups:
        first = scene_rows[0]
        for row in scene_rows:
            chunks = [
                '<section class="pattern-page">',
                _scene_header(scene_id, first),
                '<article class="episode">',
                f'<div class="episode-id">{_episode_label(str(row.get("source_episode_id") or ""))}</div>',
                '<div class="section-label">CONTEXT</div>',
                f'<div class="passage">{html.escape(str(row.get("passage") or ""))}</div>',
            ]
            families = dict(row.get("families") or {})
            for family in "ABCDEFG":
                definition = dict(definitions.get(family) or {})
                raw_name = str(definition.get("name") or f"PATTERN_{family}")
                name = raw_name.replace("_", " ").title()
                chunks.append(
                    '<div class="family">'
                    f'<div class="family-name">{family} - {html.escape(name)}</div>'
                )
                for model in list(families.get(family) or []):
                    chunks.append(
                        f'<div class="model">{html.escape(str(model))}</div>'
                    )
                chunks.append("</div>")
            chunks.append("</article></section>")
            parts.append("".join(chunks))
    return _doc("Unit04 Pattern360 Sentence-Family Reader", "".join(parts))


def _current360_delivery_json(current: Mapping[str, Any]) -> dict[str, Any]:
    entries = sorted(
        [dict(row) for row in list(current.get("effective_episodes") or [])],
        key=lambda row: _episode_number(str(row.get("episode_id") or "")),
    )
    return {
        "schema_version": "a1fs.v1.u04.reader360.current360.delivery.v1",
        "task_id": "U04_READER360_Current360_FullJSONMaterialization",
        "status": "FULL_DELIVERY_E001_E360",
        "revision": current.get("revision"),
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "source_ref": "product/a1fs_v1_2_1/u04neb02_natural_episode_bank_360.py",
        "coverage": {
            "materialized_episode_start": "U04-NEB-E001",
            "materialized_episode_end": "U04-NEB-E360",
            "materialized_count": len(entries),
            "target_total": 360,
        },
        "authority_contract": dict(current.get("authority_contract") or {}),
        "summary": dict(current.get("summary") or {}),
        "entries": entries,
    }

def materialize_three_reader_pdfs(
    *,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    repo_root: Path | str | None = None,
    acceptance_report: Mapping[str, Any] | None = None,
    current_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = _root(repo_root)
    accepted, current, spoken, pattern = _validate_sources(
        root=root,
        acceptance_report=acceptance_report,
        current_report=current_report,
    )

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    chromium = (
        Path(chromium_path).resolve(strict=True)
        if chromium_path is not None
        else chromium_acceptance.discover_chromium()
    )
    run_browser = browser_runner or UNIT01_HEADERLESS_BROWSER_RUNNER
    count_pages = pdf_page_counter or UNIT01_PDF_PAGE_COUNTER

    rendered = {
        "current360": _render_current_html(current),
        "spoken360": _render_spoken_html(spoken),
        "pattern360": _render_pattern_html(pattern),
    }
    delivery_json = {
        "current360": _current360_delivery_json(current),
        "spoken360": spoken,
        "pattern360": pattern,
    }

    artifacts: list[dict[str, Any]] = []
    for reader_id in ("current360", "spoken360", "pattern360"):
        spec = OUTPUTS[reader_id]
        json_path = output_root / spec["json"]
        html_path = output_root / spec["html"]
        pdf_path = output_root / spec["pdf"]
        if reader_id == "current360":
            _atomic_json(json_path, delivery_json[reader_id])
        elif reader_id == "spoken360":
            _atomic_text(json_path, (root / SPOKEN_PATH).read_text(encoding="utf-8"))
        else:
            _atomic_text(json_path, (root / PATTERN_PATH).read_text(encoding="utf-8"))
        _atomic_text(html_path, rendered[reader_id])
        json_identity = _file_identity(json_path)
        html_identity = _file_identity(html_path)
        browser_result = dict(
            run_browser(
                chromium,
                source_html=html_path,
                output_path=pdf_path,
                mode="PDF",
            )
        )
        if not pdf_path.is_file():
            raise Reader360PdfMaterializationError(
                f"PDF_OUTPUT_MISSING:{reader_id}"
            )
        pdf_identity = _file_identity(pdf_path)
        if pdf_identity["bytes"] < 1024:
            raise Reader360PdfMaterializationError(
                f"PDF_OUTPUT_TOO_SMALL:{reader_id}:{pdf_identity['bytes']}"
            )
        pages = int(count_pages(pdf_path))
        if pages < 1:
            raise Reader360PdfMaterializationError(
                f"PDF_PAGE_COUNT_INVALID:{reader_id}:{pages}"
            )
        artifacts.append(
            {
                "reader_id": reader_id,
                "json_file": spec["json"],
                "html_file": spec["html"],
                "pdf_file": spec["pdf"],
                "json_bytes": json_identity["bytes"],
                "json_sha256": json_identity["sha256"],
                "html_bytes": html_identity["bytes"],
                "html_sha256": html_identity["sha256"],
                "pdf_bytes": pdf_identity["bytes"],
                "pdf_sha256": pdf_identity["sha256"],
                "page_count": pages,
                "machine_acceptance": "PASS",
                "human_visual_review": "PENDING",
                "human_pedagogical_review": "PENDING",
                "browser_render": {
                    key: value
                    for key, value in browser_result.items()
                    if key not in {"source_path", "output_path"}
                },
            }
        )

    if len({row["pdf_sha256"] for row in artifacts}) != 3:
        raise Reader360PdfMaterializationError("PDF_SHA256_NOT_DISTINCT")
    if len({row["json_sha256"] for row in artifacts}) != 3:
        raise Reader360PdfMaterializationError("JSON_SHA256_NOT_DISTINCT")

    source_identities = {
        "reader_acceptance_status": accepted["status"],
        "current360_revision": current["revision"],
        "current360_effective_episode_semantic_sha256": _semantic_sha256(
            current["effective_episodes"]
        ),
        "current360_extension_sha256": current["authority_contract"][
            "extension_sha256"
        ],
        "spoken360_json": _file_identity(root / SPOKEN_PATH),
        "pattern360_json": _file_identity(root / PATTERN_PATH),
    }

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_final_acceptance_task_id": accepted["task_id"],
        "source_final_acceptance_status": accepted["status"],
        "source_identities": source_identities,
        "source_counts": {
            "current360": 360,
            "spoken360": 360,
            "pattern360": 360,
            "pattern_family_semantic_checks": 2520,
            "cross_reader_passage_alignments": 720,
            "cross_reader_metadata_alignments": 720,
        },
        "materialized_json_count": 3,
        "materialized_html_count": 3,
        "materialized_pdf_count": 3,
        "delivery_file_count": 6,
        "machine_acceptance_pass_count": 3,
        "human_visual_review_pending_count": 3,
        "human_pedagogical_review_pending_count": 3,
        "current360_mutated": False,
        "spoken360_mutated": False,
        "pattern360_mutated": False,
        "questionbank_modified": False,
        "forms_modified": False,
        "unit04_baseline_integrated": False,
        "unit04_runtime_integrated": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
        "second_pdf_renderer_created": False,
        "pdf_renderer_reused": (
            "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization"
            "._run_pdf_browser_headerless"
        ),
        "artifacts": artifacts,
        "next_short_step": NEXT_SHORT_STEP,
    }
    _atomic_json(output_root / MANIFEST_NAME, manifest)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--chromium", type=Path)
    args = parser.parse_args(argv)
    manifest = materialize_three_reader_pdfs(
        output_root=args.output_root,
        chromium_path=args.chromium,
    )
    print(f"STATUS={PASS_STATUS}")
    print(f"JSONS={manifest['materialized_json_count']}")
    print(f"PDFS={manifest['materialized_pdf_count']}")
    print(f"DELIVERY_FILES={manifest['delivery_file_count']}")
    print(f"MACHINE_ACCEPTANCE={manifest['machine_acceptance_pass_count']}/3")
    print(f"HUMAN_VISUAL_REVIEW=PENDING_{manifest['human_visual_review_pending_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
