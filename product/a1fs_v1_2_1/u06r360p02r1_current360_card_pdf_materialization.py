#!/usr/bin/env python3
"""Unit06 Current360 R2 card-PDF validator/builder contract."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U06R360P02R2_Current360CardPDF60P"
STATUS = "PASS_A1FS_V1_U06_CURRENT360_R2_CARD_PDF_60P"
LAYOUT = "A4_PORTRAIT_2_COLUMNS_X_3_ROWS_6_CARDS_PER_PAGE"
ROOT = Path(__file__).resolve().parents[2]
SHARDS = tuple(
    ROOT / f"product/a1fs_v1_2_1/data/u06r360p02_current360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)
OUTPUT_PDF = ROOT / "product/a1fs_v1_2_1/pdf/unit06/unit06_current360_cards_60p.pdf"

CARDS_PER_PAGE = 6
TOTAL_PAGES = 60
BODY_SIZE = 13.5
BODY_LEADING = 16.0
MAX_APPROX_CHARS_PER_LINE = 43


class U06Current360CardPdfError(ValueError):
    pass


def _load_episodes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in SHARDS:
        value = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(dict(x) for x in value.get("episodes") or [])
    if len(rows) != 360:
        raise U06Current360CardPdfError(f"EPISODE_COUNT_DRIFT:{len(rows)}")
    expected = [f"U06-NEB-E{i:03d}" for i in range(1, 361)]
    if [str(x.get("episode_id") or "") for x in rows] != expected:
        raise U06Current360CardPdfError("EPISODE_ID_ORDER_DRIFT")
    return rows


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[^.!?]+[.!?]", text))


def _wrap(text: str) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if not line or len(candidate) <= MAX_APPROX_CHARS_PER_LINE:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def build_report() -> dict[str, Any]:
    episodes = _load_episodes()
    line_counts = [len(_wrap(str(row["paragraph"]))) for row in episodes]
    sentence_counts = [_sentence_count(str(row["paragraph"])) for row in episodes]
    if min(sentence_counts) < 6 or max(sentence_counts) > 8:
        raise U06Current360CardPdfError(
            f"SENTENCE_RANGE_DRIFT:{min(sentence_counts)}:{max(sentence_counts)}"
        )
    if max(line_counts) > 8:
        raise U06Current360CardPdfError(f"PDF_WRAP_DENSITY_RISK:{max(line_counts)}")
    return {
        "schema_version": "a1fs.v1.u06.current360.card_pdf.v3",
        "task_id": TASK_ID,
        "status": STATUS,
        "layout": LAYOUT,
        "source_episode_count": 360,
        "cards_per_page": CARDS_PER_PAGE,
        "page_count": TOTAL_PAGES,
        "max_body_line_count": max(line_counts),
        "body_pt": BODY_SIZE,
        "body_leading_pt": BODY_LEADING,
        "first_episode_id": episodes[0]["episode_id"],
        "last_episode_id": episodes[-1]["episode_id"],
        "learner_facing_source_text_rewritten_by_pdf_builder": False,
        "q01_q10_modified": False,
        "pattern360_modified": False,
        "a2_a2plus_unlocked": False,
    }


def main() -> int:
    r = build_report()
    for key in (
        "status", "layout", "source_episode_count", "cards_per_page",
        "page_count", "max_body_line_count"
    ):
        print(f"{key.upper()}={r[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
