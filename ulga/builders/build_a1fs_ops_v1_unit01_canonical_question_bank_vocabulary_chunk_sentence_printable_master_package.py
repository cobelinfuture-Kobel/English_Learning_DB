#!/usr/bin/env python3
"""Build a canonical Unit01 printable master package from the accepted 474-item runtime."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as bank,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as integration,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads the accepted Unit01 474-item SQLite authority, the approved Unit01 "
    "vocabulary/chunk/sentence-frame contract, and the already approved Real62 "
    "content artifact to produce deterministic learner-safe and teacher-private "
    "print views. It creates no item, answer, scoring rule, learner state, content "
    "authority, second bank, planner, audio, A2 unlock, or Unit02-Unit24 artifact."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = (
    "A1FS-OPS-V1_"
    "Unit01CanonicalQuestionBankVocabularyChunkSentencePrintableMasterPackage"
)
SCHEMA_VERSION = "a1fs.ops.v1.unit01_printable_master_package.v1"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_PRINTABLE_MASTER_PACKAGE"
REPORT_NAME = "unit01_printable_master_package.safe.json"
MANIFEST_NAME = "unit01_print_manifest.json"
DEFAULT_RELATIVE_OUTPUT = Path("shared/print_packages/unit01")
EXPECTED_RUNTIME_ITEMS = 474
EXPECTED_BASE_ITEMS = 288
EXPECTED_EXTENSION_ITEMS = 186
EXPECTED_ACTIVE_VOCABULARY = 22
EXPECTED_CANONICAL_CHUNKS = 3
EXPECTED_INSTRUCTIONAL_PHRASES = 21
EXPECTED_SENTENCE_FRAMES = 11
NEXT_SHORT_STEP = (
    "A1FS-OPS-V1_"
    "Unit01PrintableMasterPackageMainProductPrintButtonIntegrationAcceptance"
)
FORBIDDEN_LEARNER_MARKERS = (
    "correct_answer",
    "accepted_answers",
    "response_contract",
    "source_record_id",
    "semantic_identity",
    "raw_raz",
    "private_item_json",
    "accepted_texts",
    "accepted_sequence",
)


class PrintablePackageError(ValueError):
    """Fail-closed Unit01 printable-package error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrintablePackageError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise PrintablePackageError(f"json_object_required:{path}")
    return value


def atomic_text(path: Path, text: str, *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def atomic_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    atomic_text(
        path,
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        private=private,
    )


def file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _integration_report(disposable_root: Path) -> dict[str, Any]:
    report_path = (
        Path(disposable_root)
        / "shared/reports"
        / integration.REPORT_NAME
    )
    report = load(report_path)
    core = {key: value for key, value in report.items() if key != "readback_sha256"}
    if report.get("readback_sha256") != integration.digest(core):
        raise PrintablePackageError("integration_readback_digest_invalid")
    expected = {
        "status": integration.PASS_STATUS,
        "source_product_version": "1.2.1",
        "source_product_root_unchanged": True,
        "disposable_copy_validated": True,
        "base_runtime_item_count": EXPECTED_BASE_ITEMS,
        "extension_item_count": EXPECTED_EXTENSION_ITEMS,
        "combined_runtime_item_count": EXPECTED_RUNTIME_ITEMS,
        "idempotent_materialization_reused": True,
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise PrintablePackageError(f"integration_readback_{key}_invalid")
    return report


def _approved_contract() -> dict[str, Any]:
    value = contract_builder.build_contract()
    contract_builder.verify_contract_digest(value)
    if value.get("contract_sha256") != bank.APPROVED_CONTRACT_SHA256:
        raise PrintablePackageError("unit01_approved_contract_identity_invalid")
    vocabulary = value.get("vocabulary_contract") or {}
    chunk = value.get("chunk_contract") or {}
    frames = value.get("sentence_frame_contract") or {}
    if (
        int(vocabulary.get("active_memorization_count") or 0)
        != EXPECTED_ACTIVE_VOCABULARY
        or len(chunk.get("canonical_chunks") or []) != EXPECTED_CANONICAL_CHUNKS
        or (
            len(chunk.get("instructional_phrases") or [])
            + len(chunk.get("adjective_instructional_phrases") or [])
        )
        != EXPECTED_INSTRUCTIONAL_PHRASES
        or (
            len(frames.get("core_frames") or [])
            + len(frames.get("adjective_expansion_frames") or [])
            + len(frames.get("scaffold_only_frames") or [])
        )
        != EXPECTED_SENTENCE_FRAMES
    ):
        raise PrintablePackageError("unit01_contract_denominator_invalid")
    return value


def _approved_content_assets(approved_content: Mapping[str, Any]) -> list[dict[str, Any]]:
    from ulga.builders import (
        build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
        as razq01e,
    )

    assets = razq01e._approved_content_assets(approved_content)
    if len(assets) != 62:
        raise PrintablePackageError(f"approved_content_asset_count_invalid:{len(assets)}")
    return assets


def _runtime_items(database: Path) -> tuple[list[dict[str, Any]], set[str]]:
    with sqlite3.connect(Path(database)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT item_id,skill,pattern_family_id,unit_pattern_id,
                      support_level,assessment_eligible,transfer_eligible,
                      capture_enabled,private_item_json
               FROM u01qb02_item_catalog
               ORDER BY skill,pattern_family_id,item_id"""
        ).fetchall()
        extension_ids = {
            str(row[0])
            for row in connection.execute(
                "SELECT item_id FROM razq01e_extension_items ORDER BY item_id"
            ).fetchall()
        }
    items: list[dict[str, Any]] = []
    for row in rows:
        private_item = json.loads(str(row["private_item_json"]))
        if not isinstance(private_item, dict):
            raise PrintablePackageError(f"private_item_not_object:{row['item_id']}")
        if str(private_item.get("item_id") or "") != str(row["item_id"]):
            raise PrintablePackageError(f"private_item_identity_invalid:{row['item_id']}")
        items.append(
            {
                "item_id": str(row["item_id"]),
                "skill": str(row["skill"]),
                "pattern_family_id": str(row["pattern_family_id"]),
                "unit_pattern_id": str(row["unit_pattern_id"]),
                "support_level": str(row["support_level"]),
                "assessment_eligible": bool(row["assessment_eligible"]),
                "transfer_eligible": bool(row["transfer_eligible"]),
                "capture_enabled": bool(row["capture_enabled"]),
                "private": private_item,
            }
        )
    if len(items) != EXPECTED_RUNTIME_ITEMS:
        raise PrintablePackageError(f"runtime_item_count_invalid:{len(items)}")
    if len(extension_ids) != EXPECTED_EXTENSION_ITEMS:
        raise PrintablePackageError(f"extension_item_count_invalid:{len(extension_ids)}")
    if not extension_ids.issubset({row["item_id"] for row in items}):
        raise PrintablePackageError("extension_item_identity_not_in_runtime")
    return items, extension_ids


def _model_sentences(assets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for asset in assets:
        content_asset_id = str(asset.get("content_asset_id") or "")
        content = asset.get("content") or {}
        values: list[tuple[str, str]] = []
        for sentence in content.get("sentences") or []:
            values.append(("SENTENCE", str(sentence).strip()))
        for turn in content.get("dialogue_turns") or []:
            utterance = str((turn or {}).get("utterance") or "").strip()
            if utterance:
                values.append(("DIALOGUE_UTTERANCE", utterance))
        for kind, text in values:
            normalized = " ".join(text.split())
            if not normalized or normalized.casefold() in seen:
                continue
            seen.add(normalized.casefold())
            rows.append(
                {
                    "model_sentence_no": len(rows) + 1,
                    "text": normalized,
                    "kind": kind,
                    "content_asset_id": content_asset_id,
                }
            )
    if not rows:
        raise PrintablePackageError("model_sentences_missing")
    return rows


def _learner_item(
    row: Mapping[str, Any],
    *,
    position: int,
    extension_ids: set[str],
) -> dict[str, Any]:
    item = row["private"]
    return {
        "print_item_no": position,
        "skill": row["skill"],
        "question_type": str(item.get("question_type") or ""),
        "prompt": str(item.get("prompt") or ""),
        "stimulus": str(item.get("stimulus") or ""),
        "options": [str(value) for value in item.get("options") or []],
        "support_level": row["support_level"],
        "assessment_eligible": row["assessment_eligible"],
        "practice_only": row["skill"] == "SPEAKING",
        "content_origin": (
            "REAL62_APPROVED_EXTENSION"
            if row["item_id"] in extension_ids
            else "UNIT01_CANONICAL_BASE"
        ),
    }


def _teacher_item(
    row: Mapping[str, Any],
    *,
    position: int,
    extension_ids: set[str],
) -> dict[str, Any]:
    item = row["private"]
    response = item.get("response_contract") or {}
    return {
        "print_item_no": position,
        "item_id": row["item_id"],
        "skill": row["skill"],
        "pattern_family_id": row["pattern_family_id"],
        "unit_pattern_id": row["unit_pattern_id"],
        "question_type": str(item.get("question_type") or ""),
        "prompt": str(item.get("prompt") or ""),
        "stimulus": str(item.get("stimulus") or ""),
        "options": [str(value) for value in item.get("options") or []],
        "correct_answer": item.get("correct_answer"),
        "accepted_answers": list(item.get("accepted_answers") or []),
        "scoring_mode": str(item.get("scoring_mode") or response.get("scoring_mode") or ""),
        "accepted_texts": list(response.get("accepted_texts") or []),
        "accepted_sequence": list(response.get("accepted_sequence") or []),
        "lexical_slots": dict(item.get("lexical_slots") or {}),
        "support_level": row["support_level"],
        "assessment_eligible": row["assessment_eligible"],
        "transfer_eligible": row["transfer_eligible"],
        "capture_enabled": row["capture_enabled"],
        "content_origin": (
            "REAL62_APPROVED_EXTENSION"
            if row["item_id"] in extension_ids
            else "UNIT01_CANONICAL_BASE"
        ),
        "content_asset_id": (
            str(item.get("content_asset_id") or "")
            if row["item_id"] in extension_ids
            else None
        ),
    }


def _render_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return " / ".join(str(row) for row in value) if value else "—"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _section_controls() -> str:
    return """<div class="controls no-print">
<button type="button" onclick="window.print()">列印／另存 PDF</button>
<label><input type="checkbox" data-section="vocabulary" checked>Vocabulary</label>
<label><input type="checkbox" data-section="chunks" checked>Chunks</label>
<label><input type="checkbox" data-section="frames" checked>Sentence Frames</label>
<label><input type="checkbox" data-section="sentences" checked>Model Sentences</label>
<label><input type="checkbox" data-section="questions" checked>Question Bank</label>
</div>"""


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    head = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(_render_value(value))}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _questions_html(items: Sequence[Mapping[str, Any]], *, teacher: bool) -> str:
    groups: list[str] = []
    for skill in ("READING", "WRITING", "SPEAKING"):
        cards: list[str] = []
        for row in items:
            if row["skill"] != skill:
                continue
            options = ""
            if row.get("options"):
                options = "<ol class=\"options\">" + "".join(
                    f"<li>{html.escape(str(value))}</li>"
                    for value in row["options"]
                ) + "</ol>"
            answer = ""
            if teacher:
                answer = (
                    "<div class=\"answer\"><strong>Answer:</strong> "
                    + html.escape(
                        _render_value(
                            row.get("correct_answer")
                            or row.get("accepted_answers")
                            or row.get("accepted_texts")
                            or row.get("accepted_sequence")
                        )
                    )
                    + "</div>"
                )
            meta = ""
            if teacher:
                meta = (
                    "<div class=\"meta\">"
                    + html.escape(
                        f"{row['item_id']} | {row['pattern_family_id']} | "
                        f"{row['content_origin']} | {row['scoring_mode']}"
                    )
                    + "</div>"
                )
            cards.append(
                "<article class=\"question-card\">"
                f"<h4>{row['print_item_no']}. {html.escape(str(row['question_type']))}</h4>"
                f"<p class=\"prompt\">{html.escape(str(row['prompt']))}</p>"
                f"<p>{html.escape(str(row['stimulus']))}</p>"
                f"{options}{answer}{meta}"
                "</article>"
            )
        groups.append(
            f"<section class=\"skill-group\"><h3>{skill} ({len(cards)})</h3>"
            + "".join(cards)
            + "</section>"
        )
    return "".join(groups)


def _render_page(
    *,
    title: str,
    manifest: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    chunks: Mapping[str, Any],
    frames: Mapping[str, Any],
    sentences: Sequence[Mapping[str, Any]],
    questions: Sequence[Mapping[str, Any]],
    teacher: bool,
) -> str:
    vocab_rows = [
        (
            row.get("lemma"),
            row.get("part_of_speech"),
            row.get("zh_tw_gloss"),
            row.get("memory_form_indefinite") or row.get("memory_phrase"),
            row.get("memory_form_definite"),
        )
        for row in [
            *(vocabulary.get("active_vocabulary") or []),
            *(vocabulary.get("active_adjectives") or []),
        ]
    ]
    canonical_chunk_rows = [
        (
            row.get("chunk_id"),
            row.get("surface_form"),
            row.get("cefr_level"),
            row.get("chunk_type"),
        )
        for row in chunks.get("canonical_chunks") or []
    ]
    instructional = [
        (
            row.get("surface_form"),
            row.get("authority_role") or row.get("usage_role") or row.get("egp_role"),
            "PROJECT_AUTHORED_INSTRUCTIONAL_PHRASE",
        )
        for row in [
            *(chunks.get("instructional_phrases") or []),
            *(chunks.get("adjective_instructional_phrases") or []),
        ]
    ]
    frame_rows = [
        (
            row.get("frame_id"),
            row.get("template"),
            row.get("communicative_goal") or row.get("external_grammar_ref"),
            row.get("support_level") or row.get("role"),
        )
        for row in [
            *(frames.get("core_frames") or []),
            *(frames.get("adjective_expansion_frames") or []),
            *(frames.get("scaffold_only_frames") or []),
        ]
    ]
    sentence_rows = [
        (row["model_sentence_no"], row["text"], row["kind"])
        for row in sentences
    ]
    teacher_note = (
        "<p class=\"warning\">Private teacher edition: contains answer and scoring data.</p>"
        if teacher
        else "<p>Learner edition: answer keys and private source identities are excluded.</p>"
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="../styles.css">
</head>
<body>
<header>
<h1>{html.escape(title)}</h1>
<p>Unit 01｜a, an, the｜Runtime items: {manifest['runtime_item_count']}</p>
{teacher_note}
{_section_controls()}
</header>
<main>
<section data-print-section="vocabulary"><h2>Vocabulary ({manifest['active_vocabulary_count']})</h2>
{_table(("Word","Part of speech","繁中","Memory form","Definite form"), vocab_rows)}
</section>
<section data-print-section="chunks"><h2>Chunks and instructional phrases</h2>
<h3>EVP canonical chunks ({manifest['canonical_chunk_count']})</h3>
{_table(("ID","Chunk","CEFR","Type"), canonical_chunk_rows)}
<h3>Project-authored instructional phrases ({manifest['instructional_phrase_count']})</h3>
{_table(("Phrase","Role","Authority class"), instructional)}
</section>
<section data-print-section="frames"><h2>Sentence Frames ({manifest['sentence_frame_count']})</h2>
{_table(("ID","Template","Goal/grammar","Support"), frame_rows)}
</section>
<section data-print-section="sentences"><h2>Approved model sentences ({manifest['model_sentence_count']})</h2>
{_table(("No.","Sentence","Kind"), sentence_rows)}
</section>
<section data-print-section="questions"><h2>Question Bank ({manifest['runtime_item_count']})</h2>
{_questions_html(questions, teacher=teacher)}
</section>
</main>
<script src="../print.js"></script>
</body>
</html>
"""


STYLES = """
:root{font-family:Arial,"Noto Sans TC",sans-serif;color:#1b1f23;background:#f5f6f7}
body{max-width:1120px;margin:auto;padding:24px;background:white}
h1,h2,h3,h4{page-break-after:avoid}h2{border-bottom:2px solid #333;padding-bottom:6px}
.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center;padding:12px;border:1px solid #bbb}
button{font-size:1rem;padding:8px 14px}.warning{font-weight:700}
table{width:100%;border-collapse:collapse;margin:12px 0 24px;font-size:.92rem}
th,td{border:1px solid #aaa;padding:6px;vertical-align:top}th{background:#eee}
.question-card{border:1px solid #aaa;border-radius:6px;padding:10px;margin:10px 0;break-inside:avoid}
.prompt{font-weight:700}.options{columns:2}.answer{margin-top:8px;padding:6px;background:#f0f0f0}
.meta{font-size:.76rem;color:#555;margin-top:6px;overflow-wrap:anywhere}
.skill-group{break-before:page}
@media print{
  :root{background:white}body{max-width:none;padding:0}.no-print{display:none!important}
  section[data-print-section][hidden]{display:none!important}
  a{color:inherit;text-decoration:none}
  @page{size:A4;margin:12mm}
}
"""


PRINT_JS = """
document.querySelectorAll('input[data-section]').forEach(input=>{
  input.addEventListener('change',()=>{
    const key=input.dataset.section;
    document.querySelectorAll(`[data-print-section="${key}"]`).forEach(section=>{
      section.hidden=!input.checked;
    });
  });
});
"""


def build_package(
    *,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    output_root: Path | None = None,
) -> dict[str, Any]:
    disposable_product_root = Path(disposable_product_root).resolve()
    report = _integration_report(disposable_product_root)
    integration._product_identity(disposable_product_root)
    source_root = Path(str(report["source_product_root"])).resolve()
    source_before = integration._product_identity(source_root)
    database = disposable_product_root / "shared/database/learner_runtime.sqlite3"
    if not database.is_file():
        raise PrintablePackageError("disposable_runtime_database_missing")
    contract = _approved_contract()
    assets = _approved_content_assets(approved_content)
    items, extension_ids = _runtime_items(database)
    sentences = _model_sentences(assets)
    vocabulary = dict(contract["vocabulary_contract"])
    chunks = dict(contract["chunk_contract"])
    frames = dict(contract["sentence_frame_contract"])
    learner_items = [
        _learner_item(row, position=index, extension_ids=extension_ids)
        for index, row in enumerate(items, 1)
    ]
    teacher_items = [
        _teacher_item(row, position=index, extension_ids=extension_ids)
        for index, row in enumerate(items, 1)
    ]
    learner_text = canonical(learner_items).casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in learner_text:
            raise PrintablePackageError(f"learner_private_marker_exposed:{marker}")
    skill_counts = dict(sorted(Counter(row["skill"] for row in items).items()))
    output_root = (
        Path(output_root).resolve()
        if output_root is not None
        else disposable_product_root / DEFAULT_RELATIVE_OUTPUT
    )
    if output_root.exists():
        import shutil
        shutil.rmtree(output_root)
    (output_root / "learner").mkdir(parents=True)
    (output_root / "teacher").mkdir(parents=True)

    manifest_core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": contract_builder.UNIT_ID,
        "product_version": "1.2.1",
        "integration_readback_sha256": report["readback_sha256"],
        "approved_content_artifact_sha256": approved_content["artifact_sha256"],
        "approved_contract_sha256": bank.APPROVED_CONTRACT_SHA256,
        "runtime_item_count": len(items),
        "base_item_count": len(items) - len(extension_ids),
        "extension_item_count": len(extension_ids),
        "skill_item_counts": skill_counts,
        "active_vocabulary_count": int(vocabulary["active_memorization_count"]),
        "active_noun_count": int(vocabulary["active_noun_memorization_count"]),
        "active_adjective_count": int(vocabulary["active_adjective_memorization_count"]),
        "receptive_vocabulary_count": len(vocabulary.get("receptive_vocabulary") or []),
        "canonical_chunk_count": len(chunks.get("canonical_chunks") or []),
        "instructional_phrase_count": (
            len(chunks.get("instructional_phrases") or [])
            + len(chunks.get("adjective_instructional_phrases") or [])
        ),
        "sentence_frame_count": (
            len(frames.get("core_frames") or [])
            + len(frames.get("adjective_expansion_frames") or [])
            + len(frames.get("scaffold_only_frames") or [])
        ),
        "model_sentence_count": len(sentences),
        "content_asset_count": len(assets),
        "learner_answer_leakage_count": 0,
        "raw_raz_identity_leakage_count": 0,
        "browser_print_available": True,
        "browser_save_as_pdf_available": True,
        "main_product_print_button_integrated": False,
        "teacher_edition_private": True,
        "formal_production_activation_approved": False,
        "public_delivery": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    manifest = {**manifest_core, "manifest_sha256": digest(manifest_core)}

    learner_data = {
        "manifest_sha256": manifest["manifest_sha256"],
        "vocabulary": vocabulary,
        "chunks": chunks,
        "sentence_frames": frames,
        "model_sentences": sentences,
        "questions": learner_items,
    }
    teacher_data = {
        "manifest_sha256": manifest["manifest_sha256"],
        "vocabulary": vocabulary,
        "chunks": chunks,
        "sentence_frames": frames,
        "model_sentences": sentences,
        "questions": teacher_items,
    }
    atomic_json(output_root / MANIFEST_NAME, manifest)
    atomic_json(output_root / "learner/unit01_learner_print_data.json", learner_data)
    atomic_json(
        output_root / "teacher/unit01_teacher_print_data.private.json",
        teacher_data,
        private=True,
    )
    atomic_text(
        output_root / "learner/index.html",
        _render_page(
            title="Unit 01 Printable Master — Learner Edition",
            manifest=manifest,
            vocabulary=vocabulary,
            chunks=chunks,
            frames=frames,
            sentences=sentences,
            questions=learner_items,
            teacher=False,
        ),
    )
    atomic_text(
        output_root / "teacher/index.private.html",
        _render_page(
            title="Unit 01 Printable Master — Teacher Edition",
            manifest=manifest,
            vocabulary=vocabulary,
            chunks=chunks,
            frames=frames,
            sentences=sentences,
            questions=teacher_items,
            teacher=True,
        ),
        private=True,
    )
    atomic_text(output_root / "styles.css", STYLES)
    atomic_text(output_root / "print.js", PRINT_JS)
    launcher = """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unit 01 列印／匯出</title><link rel="stylesheet" href="styles.css"></head>
<body><main><h1>Unit 01 列印／匯出</h1>
<p>選擇版本後，在頁面按「列印／另存 PDF」。</p>
<p><a class="button" href="learner/index.html">開啟學習者版</a></p>
<p><a class="button" href="teacher/index.private.html">開啟教師私有版</a></p>
<p>正式產品首頁按鈕尚未啟用；下一里程碑會把此入口接入既有A1FS UI。</p>
</main></body></html>"""
    atomic_text(output_root / "index.html", launcher)

    file_names = (
        MANIFEST_NAME,
        "index.html",
        "styles.css",
        "print.js",
        "learner/index.html",
        "learner/unit01_learner_print_data.json",
        "teacher/index.private.html",
        "teacher/unit01_teacher_print_data.private.json",
    )
    files = {name: file_identity(output_root / name) for name in file_names}
    source_after = integration._product_identity(source_root)
    if source_after != source_before:
        raise PrintablePackageError("source_product_identity_changed")
    report_core = {
        **manifest,
        "output_root": str(output_root),
        "source_product_root_unchanged": True,
        "files": files,
    }
    final = {**report_core, "readback_sha256": digest(report_core)}
    atomic_json(output_root / REPORT_NAME, final)
    return final


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disposable-product-root", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_package(
        disposable_product_root=args.disposable_product_root,
        approved_content=load(args.approved_content),
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"STATUS={result['status']}")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
