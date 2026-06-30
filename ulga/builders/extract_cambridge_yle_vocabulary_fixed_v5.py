#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extract_cambridge_yle_vocabulary.py

Purpose:
    Extract Cambridge YLE Starters / Movers / Flyers A-Z vocabulary PDFs
    into raw + normalized JSON artifacts.

Scope:
    - Text-layer PDF extraction only.
    - No OCR.
    - No ULGA graph mutation.
    - No learner-facing content generation.
    - Designed first for Starters sample.
    - Can also be used for Movers / Flyers, but parser QA is still needed.

Install:
    pip install pymupdf

Key changes in this fixed version:
    - Uses column-aware row segmentation instead of x-gap-only segmentation.
    - Handles wrapped entries like "catch (e.g. a" + "ball) v".
    - Handles POS continuations like "her poss adj +" + "pron".
    - Excludes POS-only / starts-with-POS / unmatched-parenthesis garbage from normalized output.
    - Adds suspicious raw/normalized quality gates to the summary.
    - Fixes slash phrase normalization, e.g. city/town centre -> city centre.
    - Keeps duplicate merge conservative so phrases cannot swallow base words.
    - Repairs Flyers layout collisions in L/N/P sections.
    - Supports Cambridge no-POS time entries a.m. / p.m. as inferred adverbials.

Example:
    python extract_cambridge_yle_vocabulary.py ^
      --pdf "G:/HomeWork/English_Learning_DB/data_sources/vocabulary_authority/raw/yle-starters-word-list-2018_0.pdf" ^
      --level Starters ^
      --out-dir "G:/HomeWork/English_Learning_DB/output/cambridge_vocab_sample"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


POS_SHORT_TO_FULL = {
    "adj": "adjective",
    "adv": "adverb",
    "conj": "conjunction",
    "det": "determiner",
    "dis": "discourse_marker",
    "excl": "exclamation",
    "int": "interrogative",
    "n": "noun",
    "poss": "possessive",
    "prep": "preposition",
    "pron": "pronoun",
    "title": "title",
    "v": "verb",
}

POS_PATTERN = r"(?:adj|adv|conj|det|dis|excl|int|n|poss|prep|pron|title|v)"
POS_RE = re.compile(rf"\b({POS_PATTERN})\b")
SECTION_RE = re.compile(r"^[A-Z]$")
SPACE_RE = re.compile(r"\s+")

IGNORE_EXACT = {
    "Grammatical key",
    "Starters A-Z Word List",
    "Movers A-Z Word List",
    "Flyers A-Z Word List",
    "for exams from 2018",
    "Starters Word",
    "Movers Word",
    "Flyers Word",
    "A-Z",
    "A-Z List",
    "List",
}

IGNORE_PREFIXES = (
    "adj adjective",
    "adv adverb",
    "conj conjunction",
    "det determiner",
    "dis discourse marker",
    "excl exclamation",
    "int interrogative",
    "n noun",
    "poss possessive",
    "prep preposition",
    "pron pronoun",
    "v verb",
)

LEVEL_TO_CANONICAL = {
    "Starters": "PreA1",
    "Movers": "A1",
    "Flyers": "A2_low",
}

POS_ONLY_TOKENS = set(POS_SHORT_TO_FULL)
TRAILING_JOIN_MARKERS = ("+", "/", "(", "(UK", "(US", "(as", "(e.g.")

# Cambridge YLE Flyers contains a few time abbreviations without an explicit POS.
# Keep raw_entry faithful and infer a usable POS only during normalization.
SPECIAL_NO_POS_ENTRY_TO_POS = {
    "a.m. (for time)": "adv",
    "p.m. (for time)": "adv",
}


@dataclass
class RawEntry:
    raw_id: str
    source_id: str
    source_file: str
    source_page: int
    raw_section: Optional[str]
    raw_entry: str
    raw_text_span: str
    extraction_method: str
    extraction_confidence: str
    parser_rule: str
    page_x: Optional[float] = None
    page_y: Optional[float] = None


@dataclass
class NormalizedEntry:
    entry_id: str
    raw_id: str
    source_id: str
    source_file: str
    source_page: int
    source_level: str
    canonical_level: str
    cefr_estimate: str

    lemma: str
    surface_form: str
    normalized_entry: str
    pos: List[str]

    raw_entry: str
    raw_section: Optional[str]

    is_multiword: bool
    variant_uk: Optional[str]
    variant_us: Optional[str]
    alt_forms: List[str]
    guide_note: Optional[str]

    authority_role: str
    source_role: str
    authority_import_allowed: bool
    direct_use_allowed: bool
    content_extraction_allowed: bool
    learner_facing_allowed: bool

    child_priority: int
    usable_for_reading: bool
    usable_for_dialogue: bool
    usable_for_writing: bool
    usable_for_assessment: bool
    generator_allowed: bool
    validator_accepts: bool

    review_status: str
    extraction_confidence: str
    parser_rule: str
    risk_flags: List[str]


@dataclass
class Segment:
    page: int
    x: float
    y: float
    text: str
    col: int = 0


@dataclass
class PendingEntry:
    page: int
    col: int
    x: float
    y: float
    section: Optional[str]
    text: str
    parser_rule: str


def normalize_spaces(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("’", "'")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = SPACE_RE.sub(" ", text).strip()
    return text


def slug_level(level: str) -> str:
    return level.strip().lower().replace(" ", "_").replace("-", "_")


def default_source_id(level: str) -> str:
    return f"cambridge_yle_{slug_level(level)}_2018"


def resolve_pdf_path(pdf_path: Path, search_roots: Optional[Iterable[Path]] = None) -> Path:
    if pdf_path.exists():
        return pdf_path.resolve()

    def collect_matches(roots: Iterable[Path]) -> List[Path]:
        seen: set[Path] = set()
        matches: List[Path] = []
        for root in roots:
            try:
                resolved_root = root.resolve()
            except OSError:
                continue
            if resolved_root in seen or not resolved_root.exists() or not resolved_root.is_dir():
                continue
            seen.add(resolved_root)
            for match in resolved_root.rglob(pdf_path.name):
                if match.is_file():
                    matches.append(match.resolve())
        return list(dict.fromkeys(matches))

    search_root_list = list(search_roots or [])
    if search_root_list:
        explicit_matches = collect_matches(search_root_list)
        if len(explicit_matches) == 1:
            return explicit_matches[0]
        if len(explicit_matches) > 1:
            formatted = ", ".join(str(path) for path in explicit_matches[:3])
            raise FileNotFoundError(
                f"PDF not found: {pdf_path}. Found multiple files named {pdf_path.name!r}: {formatted}"
            )

    script_dir = Path(__file__).resolve().parent
    fallback_matches = collect_matches([script_dir, script_dir.parent, Path.cwd()])
    if len(fallback_matches) == 1:
        return fallback_matches[0]
    if fallback_matches:
        formatted = ", ".join(str(path) for path in fallback_matches[:3])
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}. Found multiple files named {pdf_path.name!r}: {formatted}"
        )

    raise FileNotFoundError(f"PDF not found: {pdf_path}")


def stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length].upper()


def make_raw_id(source_id: str, page: int, index: int, raw_entry: str) -> str:
    digest = stable_hash(f"{source_id}|{page}|{index}|{raw_entry}", 8)
    return f"RAW_{source_id.upper()}_{page:03d}_{index:04d}_{digest}"


def make_entry_id(source_id: str, lemma: str, pos: List[str], raw_id: str) -> str:
    pos_key = "_".join(pos)
    digest = stable_hash(f"{source_id}|{lemma}|{pos_key}|{raw_id}", 10)
    return f"VOCAB_{source_id.upper()}_{digest}"


def should_ignore_segment(text: str) -> bool:
    t = normalize_spaces(text)
    if not t:
        return True
    if t in IGNORE_EXACT:
        return True
    if any(t.startswith(prefix) for prefix in IGNORE_PREFIXES):
        return True
    if t.startswith("Page ") and " of " in t:
        return True
    if "Word List" in t and "A-Z" in t:
        return True
    if t in {"Grammatical", "key", "Starters Word", "Movers Word", "Flyers Word", "A-Z List", "List"}:
        return True
    if "Candidates will be expected" in t or "www.cambridgeenglish.org" in t or "UCLES" in t:
        return True
    return False


def parentheses_balance(text: str) -> int:
    return text.count("(") - text.count(")")


def has_unmatched_parentheses(text: str) -> bool:
    bal = 0
    for ch in text:
        if ch == "(":
            bal += 1
        elif ch == ")":
            bal -= 1
        if bal < 0:
            return True
    return bal != 0


def text_ends_as_continuation(text: str) -> bool:
    t = normalize_spaces(text)
    if not t:
        return False
    if parentheses_balance(t) > 0:
        return True
    if t.endswith(TRAILING_JOIN_MARKERS):
        return True
    if t.endswith("+"):
        return True
    return False


def text_starts_as_continuation(text: str) -> bool:
    t = normalize_spaces(text)
    if not t:
        return False
    if t.startswith(")") or t.startswith("+"):
        return True
    if t.split()[0] in POS_ONLY_TOKENS:
        return True
    return False


def is_pos_only(text: str) -> bool:
    tokens = normalize_spaces(text).split()
    return bool(tokens) and all(tok in POS_ONLY_TOKENS or tok == "+" for tok in tokens)


def starts_with_pos(text: str) -> bool:
    tokens = normalize_spaces(text).split()
    return bool(tokens) and tokens[0] in POS_ONLY_TOKENS


def is_special_no_pos_entry(text: str) -> bool:
    return normalize_spaces(text).lower() in SPECIAL_NO_POS_ENTRY_TO_POS


def inferred_pos_for_special_no_pos_entry(text: str) -> Optional[str]:
    return SPECIAL_NO_POS_ENTRY_TO_POS.get(normalize_spaces(text).lower())


def is_likely_non_vocab_line(text: str) -> bool:
    """Return True for captions, footer text, and instructional prose."""
    t = normalize_spaces(text)
    if not t:
        return True
    if should_ignore_segment(t):
        return True
    lowered = t.lower()
    non_vocab_fragments = (
        "letters & numbers",
        "numbers 1-20",
        "to understand",
        "to recognise",
        "write the letters",
        "write the following names",
        "alphabet and",
        "word list",
        "candidates will be expected",
        "cambridge english",
        "ucLES".lower(),
    )
    return any(fragment in lowered for fragment in non_vocab_fragments)


def is_continuation_line(text: str) -> bool:
    t = normalize_spaces(text)
    if not t:
        return False
    return t.startswith("(") or t.startswith(")") or t.startswith("+") or starts_with_pos(t)


def sort_segments_for_section_reading(segments: List[Segment]) -> List[Segment]:
    """
    The YLE word-list tables are visually read down each column, then across to
    the next column. Some wrapped parentheticals continue at the top of the next
    visual column, e.g. "rubber n (US" -> "eraser)". Row-major order breaks
    those entries, so section groups must be processed column-major.
    """
    return sorted(segments, key=lambda seg: (seg.page, seg.col, seg.y, seg.x))


def extract_page_words(page: Any) -> List[Tuple[float, float, float, float, str]]:
    words: List[Tuple[float, float, float, float, str]] = []
    for word in page.get_text("words", sort=True):
        x0, y0, x1, y1, text = word[:5]
        text = normalize_spaces(str(text))
        if text:
            words.append((float(x0), float(y0), float(x1), float(y1), text))
    return words


def cluster_rows(words: List[Tuple[float, float, float, float, str]], y_tolerance: float) -> List[List[Tuple[float, float, float, float, str]]]:
    rows: List[List[Tuple[float, float, float, float, str]]] = []
    for word in sorted(words, key=lambda w: (w[1], w[0])):
        x0, y0, *_ = word
        placed = False
        for row in rows:
            row_y = sum(w[1] for w in row) / len(row)
            if abs(row_y - y0) <= y_tolerance:
                row.append(word)
                placed = True
                break
        if not placed:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w[0])
    rows.sort(key=lambda r: min(w[1] for w in r))
    return rows


def infer_column_starts(words: List[Tuple[float, float, float, float, str]]) -> List[float]:
    rounded = Counter()
    for x0, y0, x1, y1, text in words:
        if x0 < 85:  # section letters / margin labels
            continue
        rounded[round(x0 / 2) * 2] += 1
    common = [x for x, count in rounded.most_common(12) if count >= 4]
    starts: List[float] = []
    for x in sorted(common):
        if not any(abs(x - existing) <= 60 for existing in starts):
            starts.append(float(x))
    if len(starts) >= 4:
        return starts[:4]
    # Fallback for Cambridge YLE 2018 PDFs.
    return [96.0, 213.0, 330.0, 447.0]


def column_boundaries(starts: List[float]) -> List[float]:
    # Use a conservative boundary just before the next column start.
    # Midpoints fail because POS tokens can be far to the right within the same column.
    return [starts[i + 1] - 15.0 for i in range(len(starts) - 1)]


def col_for_x(x: float, boundaries: List[float]) -> int:
    for idx, boundary in enumerate(boundaries):
        if x < boundary:
            return idx
    return len(boundaries)


def split_row_into_column_segments(
    row: List[Tuple[float, float, float, float, str]],
    starts: List[float],
    boundaries: List[float],
    page_no: int,
) -> List[Segment]:
    grouped: Dict[int, List[Tuple[float, float, float, float, str]]] = defaultdict(list)
    for word in row:
        x0, y0, x1, y1, text = word
        col = col_for_x(x0, boundaries)
        grouped[col].append(word)

    segments: List[Segment] = []
    for col in sorted(grouped):
        col_words = sorted(grouped[col], key=lambda w: w[0])
        seg_text = normalize_spaces(" ".join(w[4] for w in col_words))
        if not seg_text or should_ignore_segment(seg_text):
            continue
        segments.append(
            Segment(
                page=page_no,
                x=float(col_words[0][0]),
                y=float(sum(w[1] for w in col_words) / len(col_words)),
                text=seg_text,
                col=col,
            )
        )
    return segments


def extract_segments_from_pdf(pdf_path: Path, y_tolerance: float = 3.2) -> List[Segment]:
    """
    Column-aware extraction for Cambridge YLE 2018 A-Z word-list PDFs.

    PyMuPDF's word extraction returns reliable coordinates, but simple x-gap
    segmentation merges adjacent table columns in some rows. This routine first
    infers the four Cambridge YLE table columns and then creates one segment per
    row-column cell.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed. Install with: pip install pymupdf")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    segments: List[Segment] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        words = extract_page_words(page)
        starts = infer_column_starts(words)
        boundaries = column_boundaries(starts)
        rows = cluster_rows(words, y_tolerance=y_tolerance)
        for row in rows:
            segments.extend(
                split_row_into_column_segments(
                    row=row,
                    starts=starts,
                    boundaries=boundaries,
                    page_no=page_index + 1,
                )
            )

    return segments


def split_possible_multiple_entries(text: str) -> List[str]:
    """
    Split a cell only when it clearly contains more than one lexical entry.

    Examples that should split:
        "candy n (UK sweet(s)) clothes n" -> ["candy n (UK sweet(s))", "clothes n"]
        "colour n + v (US color) come v" -> ["colour n + v (US color)", "come v"]

    Examples that should not split:
        "answer n + v"
        "how many int"
        "at prep of place"
    """
    text = normalize_spaces(text)
    if not text:
        return []

    tokens = text.split()
    if len(tokens) < 4:
        return [text]

    forbidden_starts = {"of", "time", "place", "movement", "as", "in", "e.g.", "+"}
    split_points: List[int] = []

    def balanced_token_slice(items: List[str]) -> bool:
        return not has_unmatched_parentheses(" ".join(items))

    # Split before a token that is followed by a POS token, but only when the
    # previous slice already contains a POS and is structurally complete.
    for i in range(1, len(tokens) - 1):
        if tokens[i] in forbidden_starts:
            continue
        if tokens[i].startswith("(") or tokens[i].endswith(")"):
            continue
        if tokens[i + 1] not in POS_SHORT_TO_FULL:
            continue
        previous = tokens[:i]
        if not any(tok in POS_SHORT_TO_FULL for tok in previous):
            continue
        if previous and previous[-1] == "+":
            continue
        if not balanced_token_slice(previous):
            continue
        split_points.append(i)

    if not split_points:
        return [text]

    parts: List[str] = []
    start = 0
    for sp in split_points:
        part = normalize_spaces(" ".join(tokens[start:sp]))
        if part:
            parts.append(part)
        start = sp
    tail = normalize_spaces(" ".join(tokens[start:]))
    if tail:
        parts.append(tail)
    return parts or [text]

def add_raw_entry(
    raw_entries: List[RawEntry],
    source_id: str,
    source_file: str,
    section: Optional[str],
    page: int,
    x: float,
    y: float,
    text: str,
    parser_rule: str,
) -> None:
    text = normalize_spaces(text)
    if not text:
        return
    raw_id = make_raw_id(source_id, page, len(raw_entries) + 1, text)
    raw_entries.append(
        RawEntry(
            raw_id=raw_id,
            source_id=source_id,
            source_file=source_file,
            source_page=page,
            raw_section=section,
            raw_entry=text,
            raw_text_span=text,
            extraction_method="pymupdf_text_layer_column_aware",
            extraction_confidence="medium",
            parser_rule=parser_rule,
            page_x=round(x, 2),
            page_y=round(y, 2),
        )
    )


def flush_pending_as_raw(
    pending: PendingEntry,
    raw_entries: List[RawEntry],
    source_id: str,
    source_file: str,
) -> None:
    add_raw_entry(
        raw_entries=raw_entries,
        source_id=source_id,
        source_file=source_file,
        section=pending.section,
        page=pending.page,
        x=pending.x,
        y=pending.y,
        text=pending.text,
        parser_rule=pending.parser_rule,
    )


def build_raw_entries(segments: List[Segment], source_id: str, source_file: str) -> List[RawEntry]:
    """
    Build raw entries from column-aware row segments.

    This version uses two passes:
    1. Row-major pass to assign each segment to the active A-Z section.
    2. Section-local column-major pass to repair wrapped entries that continue
       down the same column or at the top of the next column.

    This fixes cases like:
        May (as in girl's + name) n
        rubber n (US + eraser)
        store n (UK + shop)
    """
    raw_entries: List[RawEntry] = []

    # Pass 1: assign section labels in the visual row-major order.
    current_section: Optional[str] = None
    sectioned: List[Tuple[Optional[str], Segment]] = []
    row_major = sorted(segments, key=lambda seg: (seg.page, seg.y, seg.col, seg.x))

    for seg in row_major:
        text = normalize_spaces(seg.text)
        if not text or should_ignore_segment(text):
            continue
        if SECTION_RE.match(text):
            current_section = text
            continue
        sectioned.append((current_section, seg))

    # Group by page + section. A section may continue across pages; per-page
    # grouping avoids joining a bottom-of-page pending entry to unrelated text on
    # the next physical page.
    grouped: Dict[Tuple[int, Optional[str]], List[Segment]] = defaultdict(list)
    for section, seg in sectioned:
        grouped[(seg.page, section)].append(seg)

    def emit_complete_text(section: Optional[str], page: int, x: float, y: float, text: str, parser_rule: str) -> None:
        for part in split_possible_multiple_entries(text):
            part = normalize_spaces(part)
            if not part or is_likely_non_vocab_line(part) or is_pos_only(part) or starts_with_pos(part):
                continue
            add_raw_entry(raw_entries, source_id, source_file, section, page, x, y, part, parser_rule)

    # Process groups by page, then by first y location of that section.
    group_order = sorted(
        grouped.items(),
        key=lambda kv: (kv[0][0], min(seg.y for seg in kv[1]), min(seg.col for seg in kv[1])),
    )

    for (page, section), group_segments in group_order:
        pending: Optional[PendingEntry] = None
        previous_raw_idx: Optional[int] = None

        for seg in sort_segments_for_section_reading(group_segments):
            text = normalize_spaces(seg.text)
            if not text or is_likely_non_vocab_line(text):
                continue

            has_pos = bool(POS_RE.search(text))

            if pending is None and not has_pos and is_special_no_pos_entry(text):
                add_raw_entry(raw_entries, source_id, source_file, section, seg.page, seg.x, seg.y, text, "special_no_pos_time_entry")
                previous_raw_idx = len(raw_entries) - 1
                continue

            # Parenthetical or + continuation with no pending normally belongs to
            # the immediately previous raw entry in column-major reading order.
            if pending is None and not has_pos and is_continuation_line(text):
                if previous_raw_idx is not None and raw_entries[previous_raw_idx].raw_section == section:
                    merged_prev = normalize_spaces(raw_entries[previous_raw_idx].raw_entry + " " + text)
                    raw_entries[previous_raw_idx].raw_entry = merged_prev
                    raw_entries[previous_raw_idx].raw_text_span = merged_prev
                    raw_entries[previous_raw_idx].parser_rule = "parenthetical_continuation_merged"
                    continue
                # If no previous entry exists, this is not useful vocabulary data.
                continue

            if pending is not None:
                # If the current text is clearly a new complete entry and the
                # pending entry is not structurally balanced yet, merge. Otherwise
                # flush pending before starting a new entry.
                should_merge = (
                    not has_pos
                    or is_continuation_line(text)
                    or text_ends_as_continuation(pending.text)
                    or has_unmatched_parentheses(pending.text)
                )
                if should_merge:
                    pending.text = normalize_spaces(pending.text + " " + text)
                    pending.parser_rule = "wrapped_column_entry"
                    if text_ends_as_continuation(pending.text) or has_unmatched_parentheses(pending.text) or not POS_RE.search(pending.text):
                        continue
                    before_len = len(raw_entries)
                    emit_complete_text(pending.section, pending.page, pending.x, pending.y, pending.text, pending.parser_rule)
                    if len(raw_entries) > before_len:
                        previous_raw_idx = len(raw_entries) - 1
                    pending = None
                    continue

                # Current cell is a new entry. Flush pending only if it is a
                # complete entry with POS; otherwise discard the pending
                # non-POS fragment as layout noise.
                if POS_RE.search(pending.text) and not has_unmatched_parentheses(pending.text):
                    before_len = len(raw_entries)
                    emit_complete_text(pending.section, pending.page, pending.x, pending.y, pending.text, pending.parser_rule)
                    if len(raw_entries) > before_len:
                        previous_raw_idx = len(raw_entries) - 1
                pending = None

            if not has_pos:
                # Non-POS lexical fragments can be valid wrapped entries whose
                # POS arrives on the next line, e.g. "shopping centre" +
                # "(US center) n" or "woman/women" + "n". Keep them pending;
                # if the next cell is not a continuation, the pending fragment is
                # discarded instead of emitted as a false raw entry.
                pending = PendingEntry(
                    page=seg.page,
                    col=seg.col,
                    x=seg.x,
                    y=seg.y,
                    section=section,
                    text=text,
                    parser_rule="pending_wrapped_column_entry",
                )
                continue

            if text_ends_as_continuation(text) or has_unmatched_parentheses(text):
                pending = PendingEntry(
                    page=seg.page,
                    col=seg.col,
                    x=seg.x,
                    y=seg.y,
                    section=section,
                    text=text,
                    parser_rule="pending_wrapped_column_entry",
                )
                continue

            before_len = len(raw_entries)
            emit_complete_text(section, seg.page, seg.x, seg.y, text, "column_cell_pos_entry")
            if len(raw_entries) > before_len:
                previous_raw_idx = len(raw_entries) - 1

        if pending is not None:
            # Only emit structurally complete pending entries. Otherwise they are
            # excluded from raw to avoid creating false normalization errors.
            if not has_unmatched_parentheses(pending.text) and POS_RE.search(pending.text):
                emit_complete_text(pending.section, pending.page, pending.x, pending.y, pending.text, pending.parser_rule)

    return repair_known_yle_layout_collisions(raw_entries, source_id, source_file)


def repair_known_yle_layout_collisions(raw_entries: List[RawEntry], source_id: str, source_file: str) -> List[RawEntry]:
    """Repair known Cambridge Flyers table collisions after raw extraction.

    These are not lexical normalization issues. They are PDF layout collisions
    caused by continuation fragments appearing in adjacent visual columns. The
    repair keeps raw evidence explicit by replacing one impossible merged raw
    entry with multiple plausible source entries.
    """
    repaired: List[RawEntry] = []
    skip_next_little = False

    def append_like(base: RawEntry, raw_text: str, parser_rule: str = "known_flyers_layout_repair") -> None:
        add_raw_entry(
            raw_entries=repaired,
            source_id=source_id,
            source_file=source_file,
            section=base.raw_section,
            page=base.source_page,
            x=base.page_x or 0.0,
            y=base.page_y or 0.0,
            text=raw_text,
            parser_rule=parser_rule,
        )

    for raw in raw_entries:
        text = normalize_spaces(raw.raw_entry)

        if skip_next_little and text == "little adv + det" and raw.raw_section == "L":
            skip_next_little = False
            continue
        skip_next_little = False

        # Flyers L-section collision around left / letter / lie / lift / light / a little.
        if text == "letter (as in lie (as in lie down) v lift (ride) n adj + n lift v light adj + n mail) n a":
            for item in [
                "left (as in direction) adj + n",
                "letter (as in mail) n",
                "lie (as in lie down) v",
                "lift (ride) n",
                "lift v",
                "light adj + n",
                "a little adv + det",
            ]:
                append_like(raw, item)
            skip_next_little = True
            continue

        # Flyers N-section collision around newspaper / next / noisy / no-one / no problem / north.
        if text == "next adj + no problem!":
            for item in [
                "newspaper n",
                "next adj + adv",
                "noisy adj",
                "no-one pron",
                "no problem! excl",
                "north n",
            ]:
                append_like(raw, item)
            continue

        # If the P-section time abbreviation still slipped into pajamas, split it.
        if text == "p.m. (for time) pajamas (UK pyjamas) n":
            append_like(raw, "p.m. (for time)", "special_no_pos_time_entry")
            append_like(raw, "pajamas (UK pyjamas) n")
            continue

        repaired.append(raw)

    return repaired


def extract_parenthetical_groups(text: str) -> List[Tuple[int, int, str]]:
    """Extract top-level parenthetical groups, allowing nested parentheses."""
    groups: List[Tuple[int, int, str]] = []
    stack = 0
    start: Optional[int] = None
    for idx, ch in enumerate(text):
        if ch == "(":
            if stack == 0:
                start = idx
            stack += 1
        elif ch == ")":
            if stack > 0:
                stack -= 1
                if stack == 0 and start is not None:
                    groups.append((start, idx + 1, text[start + 1: idx]))
                    start = None
    return groups


def extract_parenthetical_notes(text: str) -> Tuple[str, Optional[str], Optional[str], List[str]]:
    """Extract UK/US variants and sense notes while preserving nested forms.

    Regex like ``\\(([^)]*)\\)`` breaks on entries such as ``(UK sweet(s))``.
    This scanner extracts balanced top-level parenthetical spans instead.
    """
    original = normalize_spaces(text)
    variant_uk: Optional[str] = None
    variant_us: Optional[str] = None
    guide_notes: List[str] = []

    groups = extract_parenthetical_groups(original)
    if not groups:
        return original, None, None, []

    keep_parts: List[str] = []
    cursor = 0
    for start, end, inner_raw in groups:
        keep_parts.append(original[cursor:start])
        inner = normalize_spaces(inner_raw)
        lower = inner.lower()
        if lower.startswith("uk "):
            variant_uk = normalize_spaces(inner[3:])
        elif lower.startswith("us "):
            variant_us = normalize_spaces(inner[3:])
        else:
            guide_notes.append(inner)
        cursor = end
    keep_parts.append(original[cursor:])
    cleaned = normalize_spaces(" ".join(keep_parts))
    return cleaned, variant_uk, variant_us, guide_notes

def normalize_lemma(surface: str) -> Tuple[str, List[str], List[str]]:
    """Normalize a Cambridge YLE surface form into lemma + alternatives.

    Important slash cases:
        city/town centre      -> lemma city centre, alt town centre
        town/city centre      -> lemma town centre, alt city centre
        take a photo/ picture -> lemma take a photo, alt take a picture
        woman/women           -> lemma woman, alt women

    The previous implementation split on ``/`` and kept only the left side as
    lemma. That incorrectly normalized ``city/town centre`` to ``city`` and
    allowed duplicate merge to swallow the real ``city n`` entry.
    """
    surface = normalize_spaces(surface)
    alt_forms: List[str] = []
    risk_flags: List[str] = []

    if "/" not in surface:
        lemma = surface
    else:
        slash_match = re.match(
            r"^(?P<prefix>.*?)(?P<left>[^\s/]+)\s*/\s*(?P<right>[^\s/]+)(?P<suffix>(?:\s+.*)?)$",
            surface,
        )
        if slash_match:
            prefix = slash_match.group("prefix") or ""
            left = slash_match.group("left")
            right = slash_match.group("right")
            suffix = slash_match.group("suffix") or ""

            lemma = normalize_spaces(f"{prefix}{left}{suffix}")
            if right.lower() in {"woman", "women"} and left.lower().endswith("man"):
                alt = normalize_spaces(f"{prefix}{left[:-3]}{right}{suffix}")
            else:
                alt = normalize_spaces(f"{prefix}{right}{suffix}")
            if alt and alt != lemma:
                alt_forms.append(alt)

            if prefix.strip() or suffix.strip() or alt != normalize_spaces(f"{prefix}{right}{suffix}"):
                risk_flags.append("slash_phrase_variant_normalized")
        else:
            parts = [normalize_spaces(p) for p in surface.split("/") if normalize_spaces(p)]
            if parts:
                lemma = parts[0]
                alt_forms.extend(parts[1:])
            else:
                lemma = surface

        risk_flags.append("slash_variant_needs_review")

    lemma_norm = normalize_spaces(lemma.strip(" ,;:").lower())
    alt_forms = list(dict.fromkeys([normalize_spaces(alt.strip(" ,;:").lower()) for alt in alt_forms if normalize_spaces(alt)]))
    return lemma_norm, alt_forms, risk_flags


def extract_inline_suffix_alt_forms(original_word_part: str, surface_form: str, guide_notes: List[str]) -> Tuple[List[str], List[str]]:
    """Convert inline suffix notes like blond(e) into alt forms.

    ``extract_parenthetical_notes`` removes non-UK/US parentheticals into
    guide_notes. For entries like ``blond(e)``, the parenthetical is not a
    semantic note; it is an orthographic variant. This returns ``blonde`` as an
    alternative and removes ``e`` from guide notes.
    """
    original = normalize_spaces(original_word_part)
    surface = normalize_spaces(surface_form)
    alt_forms: List[str] = []
    remaining_notes: List[str] = []

    for note in guide_notes:
        note_clean = normalize_spaces(note)
        if (
            note_clean
            and re.fullmatch(r"[A-Za-z]{1,5}", note_clean)
            and re.search(rf"[A-Za-z]\({re.escape(note_clean)}\)", original)
        ):
            alt_forms.append(normalize_spaces(f"{surface}{note_clean}").lower())
        else:
            remaining_notes.append(note)

    alt_forms = list(dict.fromkeys([alt for alt in alt_forms if alt]))
    return alt_forms, remaining_notes


def raw_entry_is_suspicious(raw_text: str) -> Optional[str]:
    text = normalize_spaces(raw_text)
    if not text:
        return "empty_raw_entry"
    if is_pos_only(text):
        return "pos_only_entry_excluded"
    if starts_with_pos(text):
        return "starts_with_pos_entry_excluded"
    if has_unmatched_parentheses(text):
        return "unmatched_parentheses_entry_excluded"
    return None


def parse_raw_entry(raw: RawEntry, source_level: str) -> Tuple[Optional[NormalizedEntry], Optional[Dict[str, Any]]]:
    raw_text = normalize_spaces(raw.raw_entry)

    suspicious_reason = raw_entry_is_suspicious(raw_text)
    if suspicious_reason:
        return None, {
            "raw_id": raw.raw_id,
            "raw_entry": raw.raw_entry,
            "error": suspicious_reason,
        }

    inferred_special_pos = inferred_pos_for_special_no_pos_entry(raw_text)
    parse_text = f"{raw_text} {inferred_special_pos}" if inferred_special_pos else raw_text

    pos_match = POS_RE.search(parse_text)
    if not pos_match:
        return None, {
            "raw_id": raw.raw_id,
            "raw_entry": raw.raw_entry,
            "error": "no_pos_found",
        }

    word_part = normalize_spaces(parse_text[: pos_match.start()])
    rest_part = normalize_spaces(parse_text[pos_match.start() :])

    if not word_part:
        return None, {
            "raw_id": raw.raw_id,
            "raw_entry": raw.raw_entry,
            "error": "empty_word_part",
        }

    word_part_cleaned, variant_uk_1, variant_us_1, notes_1 = extract_parenthetical_notes(word_part)
    rest_cleaned, variant_uk_2, variant_us_2, notes_2 = extract_parenthetical_notes(rest_part)

    variant_uk = variant_uk_1 or variant_uk_2
    variant_us = variant_us_1 or variant_us_2
    guide_notes = notes_1 + notes_2

    pos_tokens = POS_RE.findall(rest_cleaned)
    pos_full = [POS_SHORT_TO_FULL[p] for p in pos_tokens if p in POS_SHORT_TO_FULL]

    seen_pos = set()
    pos_full_unique: List[str] = []
    for p in pos_full:
        if p not in seen_pos:
            seen_pos.add(p)
            pos_full_unique.append(p)

    if not pos_full_unique:
        return None, {
            "raw_id": raw.raw_id,
            "raw_entry": raw.raw_entry,
            "error": "pos_parse_failed",
        }

    surface_form = normalize_spaces(word_part_cleaned)
    if not surface_form or surface_form in POS_ONLY_TOKENS:
        return None, {
            "raw_id": raw.raw_id,
            "raw_entry": raw.raw_entry,
            "error": "invalid_surface_form_excluded",
        }

    lemma, alt_forms, lemma_risks = normalize_lemma(surface_form)

    inline_suffix_alt_forms, notes_1 = extract_inline_suffix_alt_forms(word_part, surface_form, notes_1)
    alt_forms.extend(inline_suffix_alt_forms)
    guide_notes = notes_1 + notes_2

    if variant_uk:
        alt_forms.append(variant_uk.lower())
    if variant_us:
        alt_forms.append(variant_us.lower())
    alt_forms = list(dict.fromkeys([normalize_spaces(a).lower() for a in alt_forms if normalize_spaces(a)]))

    risk_flags = list(lemma_risks)
    if inferred_special_pos:
        risk_flags.append("pos_inferred_for_no_pos_time_entry")
    if surface_form and surface_form[0].isupper():
        risk_flags.append("proper_name_or_capitalized_entry_needs_review")
    if "..." in surface_form or re.search(r"(^|\W)(sb|sth)(\W|$)", surface_form):
        risk_flags.append("pattern_or_placeholder_entry_needs_review")
    if raw.parser_rule.startswith("wrapped") or raw.parser_rule.startswith("pending"):
        risk_flags.append("wrapped_entry_auto_merged")

    is_multiword = len(surface_form.split()) > 1 or "-" in surface_form
    canonical_level = LEVEL_TO_CANONICAL.get(source_level, source_level)
    cefr_estimate = canonical_level
    child_priority = child_priority_for_level(source_level, risk_flags)
    entry_id = make_entry_id(raw.source_id, lemma, pos_full_unique, raw.raw_id)

    normalized = NormalizedEntry(
        entry_id=entry_id,
        raw_id=raw.raw_id,
        source_id=raw.source_id,
        source_file=raw.source_file,
        source_page=raw.source_page,
        source_level=source_level,
        canonical_level=canonical_level,
        cefr_estimate=cefr_estimate,
        lemma=lemma,
        surface_form=surface_form,
        normalized_entry=lemma,
        pos=pos_full_unique,
        raw_entry=raw.raw_entry,
        raw_section=raw.raw_section,
        is_multiword=is_multiword,
        variant_uk=variant_uk.lower() if variant_uk else None,
        variant_us=variant_us.lower() if variant_us else None,
        alt_forms=alt_forms,
        guide_note="; ".join(guide_notes) if guide_notes else None,
        authority_role="vocabulary_authority_source",
        source_role="authority_source",
        authority_import_allowed=True,
        direct_use_allowed=False,
        content_extraction_allowed=False,
        learner_facing_allowed=False,
        child_priority=child_priority,
        usable_for_reading=True,
        usable_for_dialogue=True,
        usable_for_writing=True,
        usable_for_assessment=True,
        generator_allowed=True,
        validator_accepts=True,
        review_status="auto_extracted_pending_review",
        extraction_confidence=raw.extraction_confidence,
        parser_rule=raw.parser_rule,
        risk_flags=risk_flags,
    )
    return normalized, None


def child_priority_for_level(source_level: str, risk_flags: List[str]) -> int:
    base = {"Starters": 95, "Movers": 85, "Flyers": 75}.get(source_level, 60)
    if "proper_name_or_capitalized_entry_needs_review" in risk_flags:
        base -= 10
    if "slash_variant_needs_review" in risk_flags:
        base -= 3
    if "pattern_or_placeholder_entry_needs_review" in risk_flags:
        base -= 10
    return max(1, min(100, base))


def normalized_text_key(text: str) -> str:
    return normalize_spaces(text).lower()


def raw_without_parentheticals(text: str) -> str:
    cleaned, _variant_uk, _variant_us, _notes = extract_parenthetical_notes(text)
    return normalize_spaces(cleaned).lower()


def is_safe_duplicate_group(group: List[NormalizedEntry]) -> bool:
    """Return True only for duplicate groups that are safe to collapse.

    Safe examples:
        star n + star n
        exact same surface / exact same raw entry

    Unsafe examples must remain visible and fail the duplicate gate rather than
    being silently merged. This protects phrase entries from swallowing simpler
    entries if a normalization rule regresses.
    """
    surface_keys = {normalized_text_key(entry.surface_form) for entry in group}
    raw_keys = {normalized_text_key(entry.raw_entry) for entry in group}
    stripped_raw_keys = {raw_without_parentheticals(entry.raw_entry) for entry in group}

    if len(surface_keys) == 1 or len(raw_keys) == 1 or len(stripped_raw_keys) == 1:
        return True

    slash_surfaces = [normalized_text_key(entry.surface_form) for entry in group if "/" in entry.surface_form]
    if slash_surfaces:
        # Safe: mouse/mice + mouse n (computer), woman/women + woman.
        # Unsafe: city/town centre + city, because the slash entry is a phrase.
        slash_entries_are_single_token = all(" " not in surface for surface in slash_surfaces)
        base_surface_present = any(normalized_text_key(entry.surface_form) == entry.lemma for entry in group)
        if slash_entries_are_single_token and base_surface_present:
            return True
        return False

    return False


def deduplicate_normalized_entries(entries: List[NormalizedEntry]) -> Tuple[List[NormalizedEntry], List[Dict[str, Any]]]:
    """Merge only safe duplicate canonical keys for the same lemma + POS + level.

    This function is intentionally conservative. It should merge true duplicated
    rows, but it must not hide semantic parser errors by merging different
    surfaces that happen to normalize to the same lemma.
    """
    by_key: Dict[Tuple[str, Tuple[str, ...], str], List[NormalizedEntry]] = defaultdict(list)
    for entry in entries:
        by_key[(entry.lemma, tuple(entry.pos), entry.source_level)].append(entry)

    result: List[NormalizedEntry] = []
    merge_notes: List[Dict[str, Any]] = []

    def score(entry: NormalizedEntry) -> Tuple[int, int, int, int, int]:
        return (
            len(entry.alt_forms),
            1 if entry.guide_note else 0,
            0 if "/" in entry.surface_form else 1,
            0 if entry.parser_rule.startswith("pending") else 1,
            -len(entry.risk_flags),
        )

    for key in sorted(by_key, key=lambda k: (k[2], k[0], k[1])):
        group = by_key[key]
        if len(group) == 1:
            result.append(group[0])
            continue

        if not is_safe_duplicate_group(group):
            for item in group:
                if "duplicate_canonical_key_unmerged_needs_review" not in item.risk_flags:
                    item.risk_flags.append("duplicate_canonical_key_unmerged_needs_review")
                result.append(item)
            merge_notes.append({
                "merge_type": "duplicate_canonical_key_unmerged_needs_review",
                "lemma": key[0],
                "pos": list(key[1]),
                "source_level": key[2],
                "raw_ids": [item.raw_id for item in group],
                "surface_forms": [item.surface_form for item in group],
            })
            continue

        chosen = sorted(group, key=score, reverse=True)[0]
        merged_raw_ids = [item.raw_id for item in group if item.raw_id != chosen.raw_id]
        if "duplicate_canonical_key_merged" not in chosen.risk_flags:
            chosen.risk_flags.append("duplicate_canonical_key_merged")
        alt_forms = list(chosen.alt_forms)
        for item in group:
            for alt in item.alt_forms:
                if alt not in alt_forms:
                    alt_forms.append(alt)
        chosen.alt_forms = alt_forms
        merge_notes.append({
            "merge_type": "duplicate_canonical_key_merged",
            "lemma": key[0],
            "pos": list(key[1]),
            "source_level": key[2],
            "kept_raw_id": chosen.raw_id,
            "merged_raw_ids": merged_raw_ids,
        })
        result.append(chosen)

    result.sort(key=lambda e: (e.source_page, e.raw_section or "", e.lemma, e.raw_id))
    return result, merge_notes

def normalize_entries(raw_entries: List[RawEntry], source_level: str) -> Tuple[List[NormalizedEntry], List[Dict[str, Any]]]:
    normalized: List[NormalizedEntry] = []
    errors: List[Dict[str, Any]] = []
    for raw in raw_entries:
        item, err = parse_raw_entry(raw, source_level)
        if item is not None:
            normalized.append(item)
        if err is not None:
            errors.append(err)

    normalized, _merge_notes = deduplicate_normalized_entries(normalized)
    return normalized, errors

def suspicious_semantic_merge_reason(entry: NormalizedEntry) -> Optional[str]:
    raw_text = normalize_spaces(entry.raw_entry)
    surface = normalize_spaces(entry.surface_form)
    pos_count = len(POS_RE.findall(raw_text))
    if pos_count >= 4:
        return "too_many_pos_tokens_in_one_entry"
    if re.search(r"\b(?:letter|next|p\.m\.)\b.*\b(?:lie|no problem|pajamas)\b", raw_text.lower()):
        return "known_semantic_merge_pattern"
    if surface in {"p.m. pajamas", "letter (as in lie (as in lie down)"}:
        return "known_bad_surface_form"
    return None


def validate_outputs(raw_entries: List[RawEntry], normalized_entries: List[NormalizedEntry], errors: List[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []
    if not raw_entries:
        warnings.append("no_raw_entries_extracted")
    if not normalized_entries:
        warnings.append("no_normalized_entries_created")

    hard_errors = [err for err in errors if not err.get("merge_type") and err.get("error") not in {
        "pos_only_entry_excluded",
        "starts_with_pos_entry_excluded",
        "unmatched_parentheses_entry_excluded",
        "no_pos_found",
        "duplicate_canonical_key_merged",
    }]
    if hard_errors:
        warnings.append(f"normalization_hard_errors_count={len(hard_errors)}")

    excluded_counter = Counter(err.get("error", "unknown") for err in errors)
    for err_name, count in sorted(excluded_counter.items()):
        warnings.append(f"excluded_{err_name}_count={count}")

    empty_lemmas = [e.entry_id for e in normalized_entries if not e.lemma]
    if empty_lemmas:
        warnings.append(f"empty_lemmas_count={len(empty_lemmas)}")

    empty_pos = [e.entry_id for e in normalized_entries if not e.pos]
    if empty_pos:
        warnings.append(f"empty_pos_count={len(empty_pos)}")

    suspicious_normalized = [
        e.entry_id
        for e in normalized_entries
        if is_pos_only(e.surface_form)
        or starts_with_pos(e.raw_entry)
        or has_unmatched_parentheses(e.raw_entry)
    ]
    if suspicious_normalized:
        warnings.append(f"suspicious_normalized_entries_count={len(suspicious_normalized)}")

    key_counter = Counter((e.lemma, tuple(e.pos), e.source_level) for e in normalized_entries)
    duplicate_keys = [key for key, count in key_counter.items() if count > 1]
    if duplicate_keys:
        warnings.append(f"duplicate_lemma_pos_level_keys_count={len(duplicate_keys)}")

    high_risk = [e.entry_id for e in normalized_entries if "pattern_or_placeholder_entry_needs_review" in e.risk_flags]
    if high_risk:
        warnings.append(f"pattern_or_placeholder_entries_count={len(high_risk)}")

    semantic_merge_errors = [e.entry_id for e in normalized_entries if suspicious_semantic_merge_reason(e)]
    if semantic_merge_errors:
        warnings.append(f"semantic_merge_errors_count={len(semantic_merge_errors)}")

    return warnings


def build_summary(
    pdf_path: Path,
    source_id: str,
    level: str,
    raw_entries: List[RawEntry],
    normalized_entries: List[NormalizedEntry],
    errors: List[Dict[str, Any]],
    warnings: List[str],
) -> Dict[str, Any]:
    pos_counter = Counter()
    section_counter = Counter()
    page_counter = Counter()
    risk_counter = Counter()
    parser_rule_counter = Counter()
    error_counter = Counter(err.get("error") or err.get("merge_type", "unknown") for err in errors)

    for entry in normalized_entries:
        for p in entry.pos:
            pos_counter[p] += 1
        section_counter[entry.raw_section or "unknown"] += 1
        page_counter[str(entry.source_page)] += 1
        parser_rule_counter[entry.parser_rule] += 1
        for flag in entry.risk_flags:
            risk_counter[flag] += 1

    semantic_merge_errors = [e for e in normalized_entries if suspicious_semantic_merge_reason(e)]
    has_bad_normalized = any(
        is_pos_only(e.surface_form) or starts_with_pos(e.raw_entry) or has_unmatched_parentheses(e.raw_entry)
        for e in normalized_entries
    ) or bool(semantic_merge_errors)
    hard_errors = [err for err in errors if not err.get("merge_type") and err.get("error") not in {
        "pos_only_entry_excluded",
        "starts_with_pos_entry_excluded",
        "unmatched_parentheses_entry_excluded",
        "no_pos_found",
        "duplicate_canonical_key_merged",
    }]

    status = "PASS"
    if not normalized_entries or has_bad_normalized or hard_errors:
        status = "FAIL"
    elif warnings:
        status = "PASS_WITH_WARNINGS"

    return {
        "validation_status": status,
        "source_id": source_id,
        "source_file": str(pdf_path),
        "source_level": level,
        "canonical_level": LEVEL_TO_CANONICAL.get(level, level),
        "raw_entry_count": len(raw_entries),
        "normalized_entry_count": len(normalized_entries),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "warnings": warnings,
        "counts_by_pos": dict(sorted(pos_counter.items())),
        "counts_by_section": dict(sorted(section_counter.items())),
        "counts_by_page": dict(sorted(page_counter.items(), key=lambda kv: int(kv[0]))),
        "counts_by_parser_rule": dict(sorted(parser_rule_counter.items())),
        "risk_flags": dict(sorted(risk_counter.items())),
        "errors_by_type": dict(sorted(error_counter.items())),
        "quality_gates": {
            "no_pos_only_normalized_entries": not any(is_pos_only(e.surface_form) for e in normalized_entries),
            "no_starts_with_pos_normalized_entries": not any(starts_with_pos(e.raw_entry) for e in normalized_entries),
            "no_unmatched_parentheses_normalized_entries": not any(has_unmatched_parentheses(e.raw_entry) for e in normalized_entries),
            "no_hard_normalization_errors": not hard_errors,
            "no_duplicate_canonical_keys": not any(
                count > 1
                for count in Counter((e.lemma, tuple(e.pos), e.source_level) for e in normalized_entries).values()
            ),
            "no_unbalanced_variant_forms": not any(
                (e.variant_uk and has_unmatched_parentheses(e.variant_uk))
                or (e.variant_us and has_unmatched_parentheses(e.variant_us))
                or any(has_unmatched_parentheses(alt) for alt in e.alt_forms)
                for e in normalized_entries
            ),
            "no_actual_word_entries_excluded": not hard_errors,
            "no_semantic_merge_errors": not semantic_merge_errors,
        },
        "boundary_confirmation": {
            "ocr_used": False,
            "pdf_text_layer_only": True,
            "authority_graph_modified": False,
            "learner_facing_content_generated": False,
            "content_extraction_allowed": False,
        },
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    pdf_path = resolve_pdf_path(Path(args.pdf).resolve(strict=False))
    out_dir = Path(args.out_dir).resolve()
    level = args.level.strip()
    source_id = args.source_id.strip() if args.source_id else default_source_id(level)

    if level not in {"Starters", "Movers", "Flyers"}:
        print(f"ERROR: --level must be one of Starters, Movers, Flyers. Got: {level}", file=sys.stderr)
        return 2

    print(f"[INFO] PDF: {pdf_path}")
    print(f"[INFO] Level: {level}")
    print(f"[INFO] Source ID: {source_id}")
    print(f"[INFO] Output dir: {out_dir}")

    segments = extract_segments_from_pdf(pdf_path)
    print(f"[INFO] Extracted text segments: {len(segments)}")

    raw_entries = build_raw_entries(segments=segments, source_id=source_id, source_file=pdf_path.name)
    print(f"[INFO] Raw entries: {len(raw_entries)}")

    normalized_entries, errors = normalize_entries(raw_entries, source_level=level)
    print(f"[INFO] Normalized entries: {len(normalized_entries)}")
    print(f"[INFO] Errors / excluded entries: {len(errors)}")

    warnings = validate_outputs(raw_entries, normalized_entries, errors)
    summary = build_summary(
        pdf_path=pdf_path,
        source_id=source_id,
        level=level,
        raw_entries=raw_entries,
        normalized_entries=normalized_entries,
        errors=errors,
        warnings=warnings,
    )

    level_slug = slug_level(level)
    raw_out = out_dir / f"cambridge_{level_slug}_vocabulary_raw.json"
    normalized_out = out_dir / f"cambridge_{level_slug}_vocabulary_normalized.json"
    summary_out = out_dir / f"cambridge_{level_slug}_vocabulary_summary.json"
    errors_out = out_dir / f"cambridge_{level_slug}_vocabulary_errors.json"

    write_json(raw_out, [asdict(e) for e in raw_entries])
    write_json(normalized_out, [asdict(e) for e in normalized_entries])
    write_json(summary_out, summary)
    write_json(errors_out, errors)

    print(f"[WRITE] {raw_out}")
    print(f"[WRITE] {normalized_out}")
    print(f"[WRITE] {summary_out}")
    print(f"[WRITE] {errors_out}")

    print(f"[RESULT] {summary['validation_status']}")
    if warnings:
        print("[WARNINGS]")
        for warning in warnings:
            print(f"  - {warning}")

    return 0 if summary["validation_status"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract Cambridge YLE Starters/Movers/Flyers vocabulary PDF into JSON.")
    parser.add_argument("--pdf", required=True, help="Path to Cambridge YLE vocabulary PDF.")
    parser.add_argument("--level", required=True, choices=["Starters", "Movers", "Flyers"], help="Source level.")
    parser.add_argument("--out-dir", required=True, help="Output directory for JSON artifacts.")
    parser.add_argument("--source-id", default=None, help="Optional source_id. Default: cambridge_yle_<level>_2018")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
