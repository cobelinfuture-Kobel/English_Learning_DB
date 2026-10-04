#!/usr/bin/env python3
"""Materialize Unit06 Current360 as Unit05-style card PDF, adapted to 8 cards/page.

Read-only presentation projection over merged GPT-5.6-authored Current360.
It does not rewrite learner-facing English, mutate Q01-Q10, create Spoken360/
Pattern360, or unlock later grammar.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U06R360P02R1_Current360Unit05CardMode8PerPage"
STATUS = "PASS_A1FS_V1_U06_CURRENT360_CARD_PDF_45P"
LAYOUT = "A4_PORTRAIT_2_COLUMNS_X_4_ROWS_8_CARDS_PER_PAGE"
ROOT = Path(__file__).resolve().parents[2]
SHARDS = tuple(
    ROOT / "product/a1fs_v1_2_1/data" / name
    for name in (
        "u06r360p02_current360_gpt56_e001_e060.json",
        "u06r360p02_current360_gpt56_e061_e120.json",
        "u06r360p02_current360_gpt56_e121_e180.json",
        "u06r360p02_current360_gpt56_e181_e240.json",
        "u06r360p02_current360_gpt56_e241_e300.json",
        "u06r360p02_current360_gpt56_e301_e360.json",
    )
)
OUTPUT_PDF = ROOT / "product/a1fs_v1_2_1/pdf/unit06/unit06_current360_cards_45p.pdf"

W, H = 595, 842
MX, MT, MB, HEADER_H = 24, 28, 24, 24
COL_GAP, ROW_GAP = 8, 8
CARD_W = (W - 2 * MX - COL_GAP) / 2
CARD_H = (H - MT - MB - HEADER_H - 3 * ROW_GAP) / 4
CARDS_PER_PAGE = 8
TOTAL_PAGES = 45

# Human-approved 8-card typography (2026-10-04).
PAD = 9.0
ID_SIZE = 9.4
TARGET_SIZE = 10.2
BODY_SIZE = 13.5
BODY_LEADING = 16.0
FOOTER_SIZE = 7.5
HEADER_SIZE = 11.5
SUBTITLE_SIZE = 7.8

# Standard Helvetica AFM widths in 1/1000 em. This keeps wrapping deterministic
# without adding a PDF/font dependency to CI.
HELVETICA_WIDTHS = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667,
    "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278, "0": 556, "1": 556, "2": 556, "3": 556, "4": 556,
    "5": 556, "6": 556, "7": 556, "8": 556, "9": 556, ":": 278, ";": 278,
    "<": 584, "=": 584, ">": 584, "?": 556, "@": 1015, "A": 667, "B": 667,
    "C": 722, "D": 722, "E": 667, "F": 611, "G": 778, "H": 722, "I": 278,
    "J": 500, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778, "P": 667,
    "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611, "[": 278, "\\": 278, "]": 278, "^": 469,
    "_": 556, "`": 333, "a": 556, "b": 556, "c": 500, "d": 556, "e": 556,
    "f": 278, "g": 556, "h": 556, "i": 222, "j": 222, "k": 500, "l": 222,
    "m": 833, "n": 556, "o": 556, "p": 556, "q": 556, "r": 333, "s": 500,
    "t": 278, "u": 556, "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
    "{": 334, "|": 260, "}": 334, "~": 584,
}


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
    actual = [str(x.get("episode_id") or "") for x in rows]
    if actual != expected:
        raise U06Current360CardPdfError("EPISODE_ID_ORDER_DRIFT")
    for row in rows:
        eid = str(row["episode_id"])
        if row.get("gpt56_semantic_review") != "PASS":
            raise U06Current360CardPdfError(f"SEMANTIC_REVIEW_NOT_PASS:{eid}")
        if row.get("natural_style_review") != "PASS":
            raise U06Current360CardPdfError(f"NATURAL_STYLE_NOT_PASS:{eid}")
        fields = [
            eid,
            str(row.get("episode_slot_id") or ""),
            *(str(x) for x in (row.get("target_chunk_surfaces") or [])),
            str(row.get("paragraph") or ""),
        ]
        if any(any(ord(ch) > 127 for ch in field) for field in fields):
            raise U06Current360CardPdfError(f"NON_ASCII_SOURCE_REQUIRES_FONT_POLICY:{eid}")
    return rows


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[^.!?]+[.!?]", text))


def _string_width(text: str, size: float) -> float:
    return sum(HELVETICA_WIDTHS.get(ch, 556) for ch in text) * size / 1000.0


def _wrap(
    text: str,
    font_size: float = BODY_SIZE,
    max_width: float = CARD_W - 2 * PAD,
) -> list[str]:
    words = text.strip().split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if not line or _string_width(candidate, font_size) <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _num(value: float | int) -> str:
    return f"{float(value):.1f}"


def _text(font: str, size: float, x: float, y: float, text: str, gray: float | None = None) -> str:
    prefix = f"{gray} g\n" if gray is not None else ""
    suffix = "0 g\n" if gray is not None else ""
    return (
        prefix
        + f"BT /{font} {_num(size)} Tf {_num(x)} {_num(y)} Td ({_escape_pdf_text(text)}) Tj ET\n"
        + suffix
    )


def _page_stream(rows: list[dict[str, Any]], page_no: int) -> str:
    out = ""
    out += _text(
        "F2",
        HEADER_SIZE,
        MX,
        H - 22,
        f"Unit 06 Current360 - Card Reader - Page {page_no} / {TOTAL_PAGES}",
    )
    out += _text(
        "F1",
        SUBTITLE_SIZE,
        MX,
        H - 34,
        "Affirmative ability CAN | scene-first support | 360 episodes | 8 cards/page",
        0.35,
    )
    for idx, row in enumerate(rows):
        grid_row, col = divmod(idx, 2)
        x = MX + col * (CARD_W + COL_GAP)
        top = H - MT - HEADER_H - grid_row * (CARD_H + ROW_GAP)
        y = top - CARD_H
        out += f"q 0.78 G 0.45 w {_num(x)} {_num(y)} {_num(CARD_W)} {_num(CARD_H)} re S Q\n"

        tx = x + PAD
        text_top = top - PAD - 1
        out += _text("F2", ID_SIZE, tx, text_top - ID_SIZE, f"{row['episode_id']} | {row['episode_slot_id']}")

        target = " / ".join(str(x) for x in row.get("target_chunk_surfaces") or [])
        out += _text("F2", TARGET_SIZE, tx, text_top - ID_SIZE - 16, f"Target: {target}")

        body_y = text_top - ID_SIZE - 38
        lines = _wrap(str(row["paragraph"]))
        for line in lines:
            out += _text("F1", BODY_SIZE, tx, body_y, line)
            body_y -= BODY_LEADING

        if body_y <= y + 24:
            raise U06Current360CardPdfError(
                f"CARD_TEXT_FOOTER_COLLISION:{row['episode_id']}:{len(lines)}"
            )

        out += _text(
            "F1",
            FOOTER_SIZE,
            tx,
            y + 9,
            f"{_sentence_count(str(row['paragraph']))} sentences | semantic PASS | natural-style PASS",
            0.35,
        )
    return out


def build_pdf_bytes(episodes: list[dict[str, Any]] | None = None) -> bytes:
    episodes = list(episodes or _load_episodes())
    if len(episodes) != 360:
        raise U06Current360CardPdfError(f"EPISODE_COUNT_DRIFT:{len(episodes)}")

    objects: list[str | None] = [None]
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{5 + p * 2} 0 R" for p in range(TOTAL_PAGES))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {TOTAL_PAGES} >>")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    for p in range(TOTAL_PAGES):
        page_obj = 5 + p * 2
        content_obj = 6 + p * 2
        while len(objects) <= content_obj:
            objects.append(None)
        objects[page_obj] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_obj} 0 R >>"
        )
        stream = _page_stream(episodes[p * 8 : p * 8 + 8], p + 1)
        objects[content_obj] = f"<< /Length {len(stream)} >>\nstream\n{stream}endstream"

    pdf = "%PDF-1.4\n%CARD\n"
    offsets = [0] * len(objects)
    for i in range(1, len(objects)):
        obj = objects[i]
        if obj is None:
            raise U06Current360CardPdfError(f"PDF_OBJECT_MISSING:{i}")
        offsets[i] = len(pdf)
        pdf += f"{i} 0 obj\n{obj}\nendobj\n"

    xref = len(pdf)
    pdf += f"xref\n0 {len(objects)}\n"
    pdf += "0000000000 65535 f \n"
    for i in range(1, len(objects)):
        pdf += f"{offsets[i]:010d} 00000 n \n"
    pdf += f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return pdf.encode("ascii")


def build_report() -> dict[str, Any]:
    episodes = _load_episodes()
    pdf = build_pdf_bytes(episodes)
    page_count = len(re.findall(rb"/Type /Page\b", pdf))
    return {
        "schema_version": "a1fs.v1.u06.current360.card_pdf.v2",
        "task_id": TASK_ID,
        "status": STATUS,
        "layout": LAYOUT,
        "source_episode_count": len(episodes),
        "cards_per_page": CARDS_PER_PAGE,
        "page_count": page_count,
        "typography": {
            "episode_id_pt": ID_SIZE,
            "target_pt": TARGET_SIZE,
            "body_pt": BODY_SIZE,
            "body_leading_pt": BODY_LEADING,
            "footer_pt": FOOTER_SIZE,
        },
        "first_episode_id": episodes[0]["episode_id"],
        "last_episode_id": episodes[-1]["episode_id"],
        "learner_facing_source_text_rewritten": False,
        "spoken360_modified": False,
        "pattern360_modified": False,
        "q01_q10_modified": False,
        "a2_a2plus_unlocked": False,
    }


def materialize(output_pdf: Path = OUTPUT_PDF) -> dict[str, Any]:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    raw = build_pdf_bytes()
    output_pdf.write_bytes(raw)
    report = build_report()
    report["pdf_path"] = str(output_pdf.relative_to(ROOT)).replace("\\", "/")
    report["pdf_size_bytes"] = len(raw)
    return report


def main() -> int:
    report = materialize()
    for key in ("status", "layout", "source_episode_count", "cards_per_page", "page_count", "pdf_path"):
        print(f"{key.upper()}={report[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
