#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extract_cambridge_a2_key_vocabulary.py

Purpose:
    Extract Cambridge A2 Key / A2 Key for Schools vocabulary PDF into
    raw + normalized JSON artifacts.

Scope:
    - Text-layer PDF extraction only.
    - No OCR.
    - No ULGA graph mutation.
    - No learner-facing content generation.
    - Parses the alphabetical vocabulary list only by default.
    - Excludes Appendix 1 word sets and Appendix 2 topic lists by default.
    - v2 FullFix repairs multiword slash phrase variants and flags known source POS anomalies.

Expected input:
    a2-key-2020-vocabulary-list.pdf
    Note: the currently observed PDF content is August 2025 even if the file name says 2020.

Outputs:
    cambridge_a2_key_vocabulary_raw.json
    cambridge_a2_key_vocabulary_normalized.json
    cambridge_a2_key_vocabulary_summary.json
    cambridge_a2_key_vocabulary_errors.json

Example:
    python extract_cambridge_a2_key_vocabulary.py ^
      --pdf "G:/HomeWork/English_Learning_DB/data_sources/vocabulary_authority/raw/a2-key-2020-vocabulary-list.pdf" ^
      --out-dir "G:/HomeWork/English_Learning_DB/output/cambridge_a2_key_vocab"

Install:
    pip install pymupdf
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

SPACE_RE = re.compile(r"\s+")
SECTION_RE = re.compile(r"^[A-Z]$")
BULLET_RE = re.compile(r"^\s*[•\u2022\-]\s*")

SOURCE_ID_DEFAULT = "cambridge_a2_key_2025"
SOURCE_LEVEL = "A2_Key"
CANONICAL_LEVEL = "A2"
CEFR_ESTIMATE = "A2"
AUTHORITY_VERSION = "cambridge_a2_key_vocabulary_raw_v2_fullfix"

# Default page range is one-indexed and follows the observed 2025 A2 Key PDF:
# pages 4-23 are the A-Z vocabulary list; page 24 onward is appendix/topic lists.
DEFAULT_PAGE_START = 4
DEFAULT_PAGE_END = 23

POS_SHORT_TO_FULL = {
    "abbrev": "abbreviation",
    "adj": "adjective",
    "adv": "adverb",
    "av": "auxiliary_verb",
    "conj": "conjunction",
    "det": "determiner",
    "exclam": "exclamation",
    "mv": "modal_verb",
    "n": "noun",
    "phr v": "phrasal_verb",
    "prep": "preposition",
    "prep phr": "prepositional_phrase",
    "pron": "pronoun",
    "v": "verb",
}

POS_ALIASES = {
    "verb": "v",
    "noun": "n",
    "modal verb": "mv",
    "auxiliary verb": "av",
    "phrasal verb": "phr v",
    "prepositional phrase": "prep phr",
}

POS_TOKEN_PATTERN = re.compile(
    r"\b(?:abbrev|adj|adv|av|conj|det|exclam|mv|n|phr\s+v|pl|prep\s+phr|prep|pron|sing|unc|v)\b",
    flags=re.IGNORECASE,
)

POS_GROUP_HINT_RE = re.compile(
    r"\((?:[^()]*)\b(?:abbrev|adj|adv|av|conj|det|exclam|mv|n|phr\s+v|pl|prep\s+phr|prep|pron|sing|unc|v)(?:[^()]*)\)",
    flags=re.IGNORECASE,
)

HEADER_EXACT = {
    "Vocabulary List",
    "Key and Key for Schools",
    "A2 Key and Key for Schools",
    "A2 Key",
    "A2 Key for Schools",
}

HEADER_PREFIXES = (
    "© UCLES",
    "Page ",
    "VOCABULARY LIST",
    "Introduction to",
    "Background to",
    "How the list is updated",
    "Organisation of the list",
    "Summary of points",
    "Abbreviations",
    "Appendix 1",
    "Appendix 2",
    "Topic Lists",
)

DIALECT_LABELS = {"Br Eng", "Am Eng", "British English", "American English"}

GUIDE_PARENTHESES_KEYWORDS = {
    "planning",
    "process",
    "drawing",
    "entertain",
    "entertainment",
    "social media",
    "not artificial",
    "become happy",
    "transitive and intransitive",
    "clever",
    "stylish",
    "for colours",
    "sport",
    "exercise",
}

PRE_POS_ALT_HINTS = {
    "tv",
    "kg",
    "km",
    "cm",
    "computer",
    "phone",
    "station",
    "personal computer",
}

HARD_RISK_FLAGS = {
    "pos_parse_failed",
    "empty_word_part",
    "unmatched_parentheses_entry_excluded",
    "starts_with_pos_entry_excluded",
}

ACCEPTED_REVIEW_RISK_FLAGS = {
    "capitalized_or_acronym_entry_needs_review",
    "slash_variant_normalized",
    "inline_parenthetical_variant_normalized",
    "dialect_variant_normalized",
    "guide_note_present",
    "example_lines_present",
    "same_lemma_pos_duplicate_needs_review",
    "appendix_scope_excluded",
    "semantic_fragment_alt_form_dropped",
    "source_pos_semantic_review",
}

# Known source-level POS anomalies in the 2025 A2 Key PDF.
# Keep the source POS unchanged for evidence fidelity, but flag these entries so
# downstream authority/import layers do not treat the source POS as clean.
KNOWN_SOURCE_POS_SEMANTIC_REVIEWS = {
    ("unfortunately", ("adjective",)): {
        "expected_pos_hint": ["adverb"],
        "reason": "source_pdf_lists_unfortunately_as_adj",
    },
    ("unhappy", ("noun",)): {
        "expected_pos_hint": ["adjective"],
        "reason": "source_pdf_lists_unhappy_as_n",
    },
}



@dataclass
class RawEntry:
    raw_id: str
    source_id: str
    source_file: str
    source_page: int
    raw_section: Optional[str]
    raw_entry: str
    example_lines: List[str]
    raw_text_span: str
    extraction_method: str
    extraction_confidence: str
    parser_rule: str
    page_line_index: int


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
    grammar_features: List[str]

    raw_entry: str
    raw_section: Optional[str]
    example_lines: List[str]

    is_multiword: bool
    variant_uk: Optional[str]
    variant_us: Optional[str]
    dialect_labels: List[str]
    alt_forms: List[str]
    guide_note: Optional[str]
    grammar_note: Optional[str]

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
class ParentheticalGroup:
    start: int
    end: int
    inner: str


def normalize_spaces(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\u00a0", " ")
    text = text.replace("’", "'")
    text = text.replace("‘", "'")
    text = text.replace("“", '"')
    text = text.replace("”", '"')
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    return SPACE_RE.sub(" ", text).strip()


def stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length].upper()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def uniq_preserve_order(values: Iterable[Any]) -> List[Any]:
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalized_string_list(values: Iterable[Any]) -> List[str]:
    return uniq_preserve_order(
        normalize_spaces(value).lower()
        for value in values
        if normalize_spaces(value)
    )


def make_raw_id(source_id: str, page: int, index: int, raw_entry: str) -> str:
    digest = stable_hash(f"{source_id}|{page}|{index}|{raw_entry}", 8)
    return f"RAW_{source_id.upper()}_{page:03d}_{index:04d}_{digest}"


def make_entry_id(source_id: str, lemma: str, pos: List[str], raw_id: str) -> str:
    digest = stable_hash(f"{source_id}|{lemma}|{'|'.join(pos)}|{raw_id}", 10)
    return f"VOCAB_{source_id.upper()}_{digest}"


def resolve_pdf_path(pdf_path: Path, search_roots: Optional[Iterable[Path]] = None) -> Path:
    if pdf_path.exists():
        return pdf_path.resolve()

    search_root_list = list(search_roots or []) + [Path(__file__).resolve().parent, Path.cwd()]
    matches: List[Path] = []
    for root in search_root_list:
        try:
            root = root.resolve()
        except OSError:
            continue
        if not root.exists() or not root.is_dir():
            continue
        matches.extend(path.resolve() for path in root.rglob(pdf_path.name) if path.is_file())
    matches = list(dict.fromkeys(matches))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise FileNotFoundError(f"PDF not found by path, but multiple matches for {pdf_path.name}: {matches[:3]}")
    raise FileNotFoundError(f"PDF not found: {pdf_path}")


def has_unmatched_parentheses(text: str) -> bool:
    bal = 0
    for ch in normalize_spaces(text):
        if ch == "(":
            bal += 1
        elif ch == ")":
            bal -= 1
        if bal < 0:
            return True
    return bal != 0


def extract_parenthetical_groups(text: str) -> List[ParentheticalGroup]:
    groups: List[ParentheticalGroup] = []
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
                    groups.append(ParentheticalGroup(start=start, end=idx + 1, inner=text[start + 1:idx]))
                    start = None
    return groups


def is_header_or_footer(line: str) -> bool:
    text = normalize_spaces(line)
    if not text:
        return True
    if text in HEADER_EXACT:
        return True
    if any(text.startswith(prefix) for prefix in HEADER_PREFIXES):
        return True
    if re.fullmatch(r"Page \d+ of \d+.*", text):
        return True
    if re.fullmatch(r"© UCLES \d{4} Page \d+ of \d+.*", text):
        return True
    if "Vocabulary List" == text:
        return True
    return False


def is_section_header(line: str) -> bool:
    return bool(SECTION_RE.fullmatch(normalize_spaces(line)))


def split_bullet_tail(line: str) -> Tuple[str, Optional[str]]:
    text = normalize_spaces(line)
    if "•" not in text:
        return text, None
    before, after = text.split("•", 1)
    return normalize_spaces(before), normalize_spaces(after)


def contains_pos_group(line: str) -> bool:
    return bool(POS_GROUP_HINT_RE.search(normalize_spaces(line)))


def is_entry_line(line: str) -> bool:
    text = normalize_spaces(line)
    if not text or is_header_or_footer(text) or is_section_header(text):
        return False
    return contains_pos_group(text)


def is_pos_parenthetical_only_line(line: str) -> bool:
    text = normalize_spaces(line)
    return bool(re.fullmatch(r"\([^()]*\b(?:abbrev|adj|adv|av|conj|det|exclam|mv|n|phr\s+v|pl|prep\s+phr|prep|pron|sing|unc|v)[^()]*\)", text, flags=re.IGNORECASE))



def extract_page_words(page: Any) -> List[Tuple[float, float, float, float, str]]:
    words: List[Tuple[float, float, float, float, str]] = []
    for word in page.get_text("words", sort=True):
        x0, y0, x1, y1, text = word[:5]
        text = normalize_spaces(text)
        if text:
            words.append((float(x0), float(y0), float(x1), float(y1), text))
    return words


def cluster_rows(words: List[Tuple[float, float, float, float, str]], y_tolerance: float = 3.0) -> List[List[Tuple[float, float, float, float, str]]]:
    rows: List[List[Tuple[float, float, float, float, str]]] = []
    for word in sorted(words, key=lambda w: (w[1], w[0])):
        placed = False
        for row in rows:
            row_y = sum(w[1] for w in row) / len(row)
            if abs(row_y - word[1]) <= y_tolerance:
                row.append(word)
                placed = True
                break
        if not placed:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w[0])
    rows.sort(key=lambda r: (min(w[1] for w in r), min(w[0] for w in r)))
    return rows


def split_row_into_columns(
    row: List[Tuple[float, float, float, float, str]],
    page_width: float,
    page_no: int,
    line_idx_base: int,
) -> List[Tuple[int, int, str]]:
    """Return visual row-column text segments for the A2 two-column layout.

    PyMuPDF plain text often merges the left and right vocabulary columns into
    one row, e.g. "a/an (det) all the time (det)". The A2 parser needs one
    segment per visual column, so entries and examples remain local.
    """
    # A2 Key list pages use two text columns. The gutter is near the physical
    # page center, so a midpoint boundary is stable for this document family.
    boundary = page_width / 2.0
    grouped: Dict[int, List[Tuple[float, float, float, float, str]]] = defaultdict(list)
    for word in row:
        x0, y0, x1, y1, text = word
        col = 0 if x0 < boundary else 1
        grouped[col].append(word)

    segments: List[Tuple[int, int, str]] = []
    for col in sorted(grouped):
        col_words = sorted(grouped[col], key=lambda w: w[0])
        text = normalize_spaces(" ".join(w[4] for w in col_words))
        if text:
            segments.append((page_no, col * 10000 + line_idx_base, text))
    return segments


def extract_text_lines(pdf_path: Path, page_start: int, page_end: int) -> List[Tuple[int, int, str]]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed. Install with: pip install pymupdf")
    doc = fitz.open(str(pdf_path))
    if page_start < 1 or page_end < page_start or page_end > len(doc):
        raise ValueError(f"Invalid page range {page_start}-{page_end}; PDF has {len(doc)} pages.")

    lines: List[Tuple[int, int, str]] = []
    for page_no in range(page_start, page_end + 1):
        page = doc[page_no - 1]
        words = extract_page_words(page)
        rows = cluster_rows(words)
        synthetic_idx = 1
        page_segments: List[Tuple[int, int, str]] = []
        for row in rows:
            for segment in split_row_into_columns(row, float(page.rect.width), page_no, synthetic_idx):
                _page, _idx, text = segment
                if text and not is_header_or_footer(text):
                    page_segments.append(segment)
            synthetic_idx += 2
        # Read down the left visual column, then down the right visual column.
        # This preserves wrapped dialect continuations that would otherwise be
        # interrupted by the neighbouring column in row-major order.
        lines.extend(sorted(page_segments, key=lambda item: item[1]))
    return lines

def append_example(raw_entries: List[RawEntry], line: str) -> None:
    if not raw_entries:
        return
    text = normalize_spaces(BULLET_RE.sub("", line))
    if not text:
        return
    # If the previous example is very likely wrapped, join; otherwise append.
    if raw_entries[-1].example_lines and raw_entries[-1].example_lines[-1].endswith((",", "and", "the", "from", "on", "to")):
        raw_entries[-1].example_lines[-1] = normalize_spaces(raw_entries[-1].example_lines[-1] + " " + text)
    else:
        raw_entries[-1].example_lines.append(text)


def build_raw_entries(lines: List[Tuple[int, int, str]], source_id: str, source_file: str) -> List[RawEntry]:
    raw_entries: List[RawEntry] = []
    current_section: Optional[str] = None
    pending: Optional[Tuple[int, int, str, Optional[str]]] = None
    pending_bullet: Optional[str] = None

    def emit(page: int, line_idx: int, section: Optional[str], raw_text: str, parser_rule: str, example_tail: Optional[str] = None) -> None:
        raw_text = normalize_spaces(raw_text)
        if not raw_text or is_header_or_footer(raw_text) or is_section_header(raw_text):
            return
        raw_id = make_raw_id(source_id, page, len(raw_entries) + 1, raw_text)
        examples = [example_tail] if example_tail else []
        raw_entries.append(
            RawEntry(
                raw_id=raw_id,
                source_id=source_id,
                source_file=source_file,
                source_page=page,
                raw_section=section,
                raw_entry=raw_text,
                example_lines=examples,
                raw_text_span=raw_text,
                extraction_method="pymupdf_text_layer_sorted_lines",
                extraction_confidence="medium",
                parser_rule=parser_rule,
                page_line_index=line_idx,
            )
        )

    for page, line_idx, line in lines:
        text = normalize_spaces(line)
        if not text:
            continue
        if is_header_or_footer(text):
            continue
        if text.startswith("Appendix "):
            break
        if is_section_header(text):
            current_section = text
            continue

        if pending is not None:
            p_page, p_line_idx, p_text, p_section = pending
            if BULLET_RE.match(text):
                # A bullet may belong to the entry immediately above in the opposite
                # column while the current pending entry is waiting for a wrapped
                # dialect continuation on the next visual line, e.g.
                # "kilogramme ... (Am Eng:" + "kilogram)". Do not merge the
                # bullet text into the pending entry.
                if not has_unmatched_parentheses(p_text) and contains_pos_group(p_text):
                    emit(p_page, p_line_idx, p_section, p_text, "wrapped_line_entry", pending_bullet)
                    pending = None
                    pending_bullet = None
                append_example(raw_entries, text)
                continue
            joined = normalize_spaces(p_text + " " + text)
            if has_unmatched_parentheses(joined) or not contains_pos_group(joined):
                pending = (p_page, p_line_idx, joined, p_section)
                continue
            raw_text, bullet_tail = split_bullet_tail(joined)
            emit(p_page, p_line_idx, p_section, raw_text, "wrapped_line_entry", bullet_tail or pending_bullet)
            pending = None
            pending_bullet = None
            continue

        if BULLET_RE.match(text):
            append_example(raw_entries, text)
            continue

        if is_pos_parenthetical_only_line(text):
            # Example continuation such as a wrapped "(adv)" should not become a raw entry.
            if raw_entries and raw_entries[-1].example_lines:
                raw_entries[-1].example_lines[-1] = normalize_spaces(raw_entries[-1].example_lines[-1] + " " + text)
            continue

        if is_entry_line(text):
            raw_text, bullet_tail = split_bullet_tail(text)
            if has_unmatched_parentheses(raw_text):
                pending = (page, line_idx, raw_text, current_section)
                pending_bullet = bullet_tail
                continue
            emit(page, line_idx, current_section, raw_text, "sorted_line_entry", bullet_tail)
            continue

        # Non-entry continuation: usually example wrapping. Attach only when the
        # previous raw entry already has examples, otherwise ignore as prose/noise.
        if raw_entries and raw_entries[-1].example_lines:
            raw_entries[-1].example_lines[-1] = normalize_spaces(raw_entries[-1].example_lines[-1] + " " + text)

    if pending is not None:
        p_page, p_line_idx, p_text, p_section = pending
        emit(p_page, p_line_idx, p_section, p_text, "wrapped_line_entry_unclosed", pending_bullet)

    return raw_entries


def normalize_dialect_text(text: str) -> str:
    text = normalize_spaces(text)
    text = re.sub(r"^(Am Eng|Br Eng)\s*:\s*", "", text, flags=re.IGNORECASE)
    return normalize_spaces(text).lower()


def is_pos_group(inner: str) -> bool:
    return bool(POS_TOKEN_PATTERN.search(normalize_spaces(inner)))


def split_pos_and_notes(inner: str) -> Tuple[List[str], List[str], List[str]]:
    """Return (pos_full, grammar_features, leftover_notes) for one POS parenthetical."""
    text = normalize_spaces(inner).lower()
    # Normalize punctuation and conjunction separators while preserving multi-token POS phrases.
    text = text.replace("&", ",")
    text = text.replace("/", ",")
    text = re.sub(r"\band\b", ",", text)
    text = text.replace(";", ",")

    pos_found: List[str] = []
    features: List[str] = []

    # Longest patterns first.
    long_patterns = ["prep phr", "phr v", "unc n", "n pl", "n sing"]
    for pattern in long_patterns:
        if re.search(rf"\b{re.escape(pattern)}\b", text):
            if pattern == "prep phr":
                pos_found.append("prepositional_phrase")
            elif pattern == "phr v":
                pos_found.append("phrasal_verb")
            elif pattern == "unc n":
                pos_found.append("noun")
                features.append("uncountable")
            elif pattern == "n pl":
                pos_found.append("noun")
                features.append("plural")
            elif pattern == "n sing":
                pos_found.append("noun")
                features.append("singular")
            text = re.sub(rf"\b{re.escape(pattern)}\b", " ", text)

    for match in POS_TOKEN_PATTERN.finditer(text):
        token = normalize_spaces(match.group(0).lower())
        if token in {"pl", "sing", "unc"}:
            feature = {"pl": "plural", "sing": "singular", "unc": "uncountable"}[token]
            features.append(feature)
            continue
        full = POS_SHORT_TO_FULL.get(token)
        if full:
            pos_found.append(full)

    # Remaining non-POS text in a POS group is a guide note, e.g. "adj - for colours".
    leftover = POS_TOKEN_PATTERN.sub(" ", normalize_spaces(inner))
    leftover = re.sub(r"^[\s,;&/\-]+|[\s,;&/\-]+$", "", leftover)
    leftover_notes = [normalize_spaces(leftover)] if leftover else []

    return uniq_preserve_order(pos_found), uniq_preserve_order(features), leftover_notes


def is_dialect_group(inner: str) -> bool:
    text = normalize_spaces(inner)
    return bool(re.match(r"^(Br Eng|Am Eng)(\s*:.*)?$", text, flags=re.IGNORECASE))


def classify_pre_pos_group(inner: str) -> str:
    text = normalize_spaces(inner)
    lower = text.lower()
    if lower in GUIDE_PARENTHESES_KEYWORDS or "as in" in lower or "e.g." in lower:
        return "guide"
    if lower in PRE_POS_ALT_HINTS:
        return "alt"
    if re.fullmatch(r"[A-Z]{2,5}", text) or re.fullmatch(r"'[a-z]{1,3}", lower):
        return "alt"
    # Single word in lowercase in phrase context may be an optional expansion:
    # railway (station), mobile (phone), laptop (computer).
    if re.fullmatch(r"[a-z]+", lower) and lower in {"station", "phone", "computer", "tub", "graph"}:
        return "alt"
    return "guide"


def expand_inline_parenthetical_token(text: str) -> Tuple[str, List[str], List[Dict[str, str]]]:
    """Expand no-space inline parentheticals inside words: blond(e), yog(h)urt, photo(graph)."""
    notes: List[Dict[str, str]] = []
    alt_forms: List[str] = []
    output = normalize_spaces(text)

    pattern = re.compile(r"(?P<prefix>[A-Za-z]+)\((?P<inside>[A-Za-z']+)\)(?P<suffix>[A-Za-z]*)")
    while True:
        match = pattern.search(output)
        if not match:
            break
        full = match.group(0)
        base = f"{match.group('prefix')}{match.group('suffix')}"
        alt = f"{match.group('prefix')}{match.group('inside')}{match.group('suffix')}"
        output = normalize_spaces(output[:match.start()] + base + output[match.end():])
        if alt.lower() != base.lower():
            alt_forms.append(alt.lower())
            notes.append({"type": "inline_parenthetical_variant_expanded", "raw": full, "base": base.lower(), "alt": alt.lower()})
    return output, uniq_preserve_order(alt_forms), notes


def expand_space_parenthetical_alt(surface: str, inner: str) -> Optional[str]:
    base = normalize_spaces(surface)
    value = normalize_spaces(inner)
    if not base or not value:
        return None
    lower = value.lower()
    if lower in PRE_POS_ALT_HINTS or re.fullmatch(r"[A-Z]{2,5}", value) or re.fullmatch(r"'[a-z]{1,3}", lower):
        # Acronym entries like PC (personal computer) should use the expanded
        # phrase itself as the alternative, not "pc personal computer".
        if base.isupper() or re.fullmatch(r"[A-Z]{2,5}", base):
            return lower
        return normalize_spaces(f"{base} {value}").lower() if len(value) > 4 else value.lower()
    if lower in {"station", "phone", "computer", "tub", "graph"}:
        return normalize_spaces(f"{base} {lower}").lower()
    return None


def compact_variant_key(text: str) -> str:
    return re.sub(r"[^a-z0-9@]+", "", normalize_spaces(text).lower())


def normalize_slash_surface(surface: str) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """Normalize slash alternatives without creating semantic fragments.

    Required A2 cases:
        give somebody a call/ring -> lemma give somebody a call, alt give somebody a ring
        prefer / would prefer     -> lemma prefer, alt would prefer
        lots / a lot              -> lemma lots, alt a lot
        poor thing/you            -> lemma poor thing, alt poor you
        all right/alright         -> lemma all right, alt alright
        driving/driver's licence  -> lemma driving licence, alt driver's licence
    """
    surface = normalize_spaces(surface)
    notes: List[Dict[str, Any]] = []
    if "/" not in surface:
        return surface.lower(), [], notes

    # Explicit phrase alternatives separated by a spaced slash should be kept
    # as whole alternatives. Do not reconstruct them token-wise, otherwise
    # "prefer / would prefer" can become "prefer prefer".
    if re.search(r"\s+/\s+", surface):
        parts = [normalize_spaces(part).lower() for part in re.split(r"\s+/\s*", surface) if normalize_spaces(part)]
        if parts:
            lemma = parts[0]
            alts = [part for part in parts[1:] if part != lemma]
            notes.append({"type": "slash_variant_normalized", "surface": surface, "lemma": lemma, "alt_forms": alts})
            return lemma, alts, notes

    # Inline slash inside one token of a phrase. Reconstruct the right-hand
    # alternative with the same prefix/suffix unless the right side is already a
    # collapsed full-form spelling of the left phrase (all right/alright).
    match = re.match(
        r"^(?P<prefix>.*?)(?P<left>[^\s/]+)\s*/\s*(?P<right>[^\s/]+)(?P<suffix>(?:\s+.*)?)$",
        surface,
    )
    if match:
        prefix = match.group("prefix") or ""
        left = match.group("left")
        right = match.group("right")
        suffix = match.group("suffix") or ""

        lemma = normalize_spaces(f"{prefix}{left}{suffix}").lower()
        reconstructed = normalize_spaces(f"{prefix}{right}{suffix}").lower()
        right_only = normalize_spaces(right).lower()

        # all right/alright: compact("all right") == compact("alright"), so
        # use the right-only spelling instead of "all alright".
        if (
            prefix.strip()
            and not suffix.strip()
            and (
                compact_variant_key(prefix + left) == compact_variant_key(right)
                or right_only in {"alright"}
            )
        ):
            alt = right_only
        else:
            alt = reconstructed

        alts = [alt] if alt and alt != lemma else []
        notes.append({"type": "slash_variant_normalized", "surface": surface, "lemma": lemma, "alt_forms": alts})
        return lemma, alts, notes

    # Fallback: preserve whole slash parts rather than raw fragments.
    parts = [normalize_spaces(part).lower() for part in re.split(r"\s*/\s*", surface) if normalize_spaces(part)]
    if not parts:
        return surface.lower(), [], notes
    notes.append({"type": "slash_variant_normalized", "surface": surface, "lemma": parts[0], "alt_forms": parts[1:]})
    return parts[0], parts[1:], notes


def is_single_token_alt_allowed_for_multiword_lemma(lemma: str, alt: str) -> bool:
    lemma_key = compact_variant_key(lemma)
    alt_key = compact_variant_key(alt)
    if not lemma_key or not alt_key:
        return False
    # all right -> alright is a legitimate single-token collapsed spelling.
    if lemma_key == alt_key or (lemma == "all right" and alt == "alright"):
        return True
    # Short symbolic alternatives are legitimate, e.g. at -> @. This is mostly
    # defensive; the semantic-fragment rule only applies to multiword lemmas.
    if alt in {"@", "tv", "pc", "cd", "dvd", "kg", "km", "cm"}:
        return True
    return False


def clean_semantic_fragment_alt_forms(
    lemma: str,
    alt_forms: List[str],
    protected_alt_forms: Optional[Iterable[str]] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Drop single-token fragments for multiword lemmas when they are unsafe.

    Authority/query alt forms should be full alternatives, not fragments.
    Example: give somebody a call/ring should not produce alt_forms=["ring"].

    Dialect variants from explicit Br Eng / Am Eng groups are protected.
    Example: French fries (Am Eng) (Br Eng: chips) must keep chips.
    """
    lemma_norm = normalize_spaces(lemma).lower()
    protected = set(normalized_string_list(protected_alt_forms or []))
    cleaned: List[str] = []
    notes: List[Dict[str, Any]] = []
    lemma_is_multiword = len(lemma_norm.split()) > 1 or "-" in lemma_norm

    for alt in normalized_string_list(alt_forms):
        alt_norm = normalize_spaces(alt).lower()
        if alt_norm in protected:
            cleaned.append(alt_norm)
            continue
        if (
            lemma_is_multiword
            and len(alt_norm.split()) == 1
            and not is_single_token_alt_allowed_for_multiword_lemma(lemma_norm, alt_norm)
        ):
            notes.append({
                "type": "semantic_fragment_alt_form_dropped",
                "lemma": lemma_norm,
                "alt_form": alt_norm,
                "reason": "single_token_fragment_of_multiword_variant",
            })
            continue
        cleaned.append(alt_norm)
    return uniq_preserve_order(cleaned), notes


def semantic_fragment_alt_form_residuals(entry: NormalizedEntry) -> List[str]:
    lemma = normalize_spaces(entry.lemma).lower()
    if not lemma or not (len(lemma.split()) > 1 or "-" in lemma):
        return []
    protected = set(normalized_string_list([entry.variant_uk, entry.variant_us]))
    residuals: List[str] = []
    for alt in entry.alt_forms:
        alt_norm = normalize_spaces(alt).lower()
        if alt_norm in protected:
            continue
        if len(alt_norm.split()) == 1 and not is_single_token_alt_allowed_for_multiword_lemma(lemma, alt_norm):
            residuals.append(alt_norm)
    return residuals


def source_pos_semantic_review_info(lemma: str, pos: List[str]) -> Optional[Dict[str, Any]]:
    return KNOWN_SOURCE_POS_SEMANTIC_REVIEWS.get((normalize_spaces(lemma).lower(), tuple(pos)))


def extract_dialect_variants(groups_after_pos: List[str]) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
    variant_uk: Optional[str] = None
    variant_us: Optional[str] = None
    dialect_labels: List[str] = []
    guide_notes: List[str] = []

    for inner in groups_after_pos:
        text = normalize_spaces(inner)
        if not text:
            continue
        m = re.match(r"^(Br Eng|Am Eng)(?:\s*:\s*(.+))?$", text, flags=re.IGNORECASE)
        if m:
            label = "Br Eng" if m.group(1).lower().startswith("br") else "Am Eng"
            dialect_labels.append(label)
            form = normalize_spaces(m.group(2) or "")
            if form:
                if label == "Br Eng":
                    variant_uk = form.lower()
                else:
                    variant_us = form.lower()
            continue
        guide_notes.append(text)

    return variant_uk, variant_us, uniq_preserve_order(dialect_labels), guide_notes


def parse_raw_entry(raw: RawEntry) -> Tuple[Optional[NormalizedEntry], Optional[Dict[str, Any]]]:
    raw_text = normalize_spaces(raw.raw_entry)
    if not raw_text:
        return None, {"raw_id": raw.raw_id, "raw_entry": raw.raw_entry, "error": "empty_raw_entry"}
    if has_unmatched_parentheses(raw_text):
        return None, {"raw_id": raw.raw_id, "raw_entry": raw.raw_entry, "error": "unmatched_parentheses_entry_excluded"}

    groups = extract_parenthetical_groups(raw_text)
    pos_group_index: Optional[int] = None
    for i, group in enumerate(groups):
        if is_pos_group(group.inner):
            pos_group_index = i
            break

    if pos_group_index is None:
        return None, {"raw_id": raw.raw_id, "raw_entry": raw.raw_entry, "error": "no_pos_group_found"}

    pos_group = groups[pos_group_index]
    word_part_raw = normalize_spaces(raw_text[:pos_group.start])
    after_pos_raw = normalize_spaces(raw_text[pos_group.end:])

    if not word_part_raw:
        return None, {"raw_id": raw.raw_id, "raw_entry": raw.raw_entry, "error": "empty_word_part"}

    pos, grammar_features, pos_leftover_notes = split_pos_and_notes(pos_group.inner)
    if not pos:
        return None, {"raw_id": raw.raw_id, "raw_entry": raw.raw_entry, "error": "pos_parse_failed", "pos_group": pos_group.inner}

    pre_pos_groups = groups[:pos_group_index]
    post_pos_groups = [g.inner for g in groups[pos_group_index + 1:]]
    variant_uk, variant_us, dialect_labels, post_guide_notes = extract_dialect_variants(post_pos_groups)

    # Remove pre-POS parenthetical groups from the surface, classifying them as guide or variant.
    surface_builder_parts: List[str] = []
    cursor = 0
    guide_notes: List[str] = []
    alt_candidates: List[str] = []
    cleanup_notes: List[Dict[str, Any]] = []

    for group in pre_pos_groups:
        # No-space parentheticals are part of an orthographic variant token,
        # e.g. photo(graph), yog(h)urt, blond(e). Keep them in the surface so
        # expand_inline_parenthetical_token() can produce photograph/yoghurt/blonde.
        if group.start > 0 and word_part_raw[group.start - 1] not in {" ", "	"}:
            surface_builder_parts.append(word_part_raw[cursor:group.end])
            cursor = group.end
            continue

        surface_builder_parts.append(word_part_raw[cursor:group.start])
        inner = normalize_spaces(group.inner)
        group_class = classify_pre_pos_group(inner)
        if group_class == "alt":
            # Space parenthetical alternative: mobile (phone), television (TV), PC (personal computer).
            provisional_surface = normalize_spaces("".join(surface_builder_parts))
            expanded = expand_space_parenthetical_alt(provisional_surface, inner)
            if expanded:
                alt_candidates.append(expanded)
                cleanup_notes.append({"type": "space_parenthetical_variant_normalized", "raw": inner, "alt": expanded})
            else:
                alt_candidates.append(inner.lower())
        else:
            guide_notes.append(inner)
        cursor = group.end
    surface_builder_parts.append(word_part_raw[cursor:])

    surface_form = normalize_spaces("".join(surface_builder_parts))
    surface_form, inline_alts, inline_notes = expand_inline_parenthetical_token(surface_form)
    alt_candidates.extend(inline_alts)
    cleanup_notes.extend(inline_notes)

    if not surface_form:
        return None, {"raw_id": raw.raw_id, "raw_entry": raw.raw_entry, "error": "empty_surface_after_parenthetical_cleanup"}

    lemma, slash_alts, slash_notes = normalize_slash_surface(surface_form)
    alt_candidates.extend(slash_alts)
    cleanup_notes.extend(slash_notes)

    protected_alt_forms: List[str] = []
    if variant_uk:
        alt_candidates.append(variant_uk)
        protected_alt_forms.append(variant_uk)
    if variant_us:
        alt_candidates.append(variant_us)
        protected_alt_forms.append(variant_us)

    alt_forms = normalized_string_list(alt for alt in alt_candidates if normalize_spaces(alt).lower() != lemma)
    alt_forms, semantic_cleanup_notes = clean_semantic_fragment_alt_forms(
        lemma,
        alt_forms,
        protected_alt_forms=protected_alt_forms,
    )
    cleanup_notes.extend(semantic_cleanup_notes)

    grammar_note = None
    trailing_after_parentheticals = normalize_spaces(re.sub(r"\([^()]*\)", " ", after_pos_raw))
    if trailing_after_parentheticals:
        grammar_note = trailing_after_parentheticals

    guide_all = guide_notes + post_guide_notes + pos_leftover_notes
    guide_note = "; ".join(uniq_preserve_order(normalize_spaces(note) for note in guide_all if normalize_spaces(note))) or None

    risk_flags: List[str] = []
    if any(note.get("type") == "slash_variant_normalized" for note in cleanup_notes):
        risk_flags.append("slash_variant_normalized")
    if any("parenthetical_variant" in note.get("type", "") for note in cleanup_notes):
        risk_flags.append("inline_parenthetical_variant_normalized")
    if any(note.get("type") == "semantic_fragment_alt_form_dropped" for note in cleanup_notes):
        risk_flags.append("semantic_fragment_alt_form_dropped")
    if variant_uk or variant_us or dialect_labels:
        risk_flags.append("dialect_variant_normalized")
    if guide_note:
        risk_flags.append("guide_note_present")
    if source_pos_semantic_review_info(lemma, pos):
        risk_flags.append("source_pos_semantic_review")
    if raw.example_lines:
        risk_flags.append("example_lines_present")
    if surface_form and (surface_form[0].isupper() or surface_form.isupper()) and not surface_form.lower() in {"i", "ok"}:
        risk_flags.append("capitalized_or_acronym_entry_needs_review")

    is_multiword = len(lemma.split()) > 1 or "-" in lemma
    child_priority = 75
    if risk_flags:
        child_priority -= min(20, 3 * len(risk_flags))
    child_priority = max(1, child_priority)

    entry_id = make_entry_id(raw.source_id, lemma, pos, raw.raw_id)
    normalized = NormalizedEntry(
        entry_id=entry_id,
        raw_id=raw.raw_id,
        source_id=raw.source_id,
        source_file=raw.source_file,
        source_page=raw.source_page,
        source_level=SOURCE_LEVEL,
        canonical_level=CANONICAL_LEVEL,
        cefr_estimate=CEFR_ESTIMATE,
        lemma=lemma,
        surface_form=surface_form,
        normalized_entry=lemma,
        pos=pos,
        grammar_features=grammar_features,
        raw_entry=raw.raw_entry,
        raw_section=raw.raw_section,
        example_lines=raw.example_lines,
        is_multiword=is_multiword,
        variant_uk=variant_uk,
        variant_us=variant_us,
        dialect_labels=dialect_labels,
        alt_forms=alt_forms,
        guide_note=guide_note,
        grammar_note=grammar_note,
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
        review_status="auto_extracted_pending_review" if risk_flags else "auto_extracted_clean",
        extraction_confidence=raw.extraction_confidence,
        parser_rule=raw.parser_rule,
        risk_flags=risk_flags,
    )
    return normalized, None


def normalize_entries(raw_entries: List[RawEntry]) -> Tuple[List[NormalizedEntry], List[Dict[str, Any]]]:
    normalized: List[NormalizedEntry] = []
    errors: List[Dict[str, Any]] = []
    for raw in raw_entries:
        item, err = parse_raw_entry(raw)
        if item is not None:
            normalized.append(item)
        if err is not None:
            errors.append(err)

    # Keep duplicate lemma+POS entries. A2 Key has intentional sense-constrained
    # duplicates such as design (PLANNING)/(PROCESS)/(DRAWING), smart (stylish)/(clever).
    key_counter = Counter((item.lemma, tuple(item.pos)) for item in normalized)
    for item in normalized:
        if key_counter[(item.lemma, tuple(item.pos))] > 1:
            if "same_lemma_pos_duplicate_needs_review" not in item.risk_flags:
                item.risk_flags.append("same_lemma_pos_duplicate_needs_review")
            item.review_status = "auto_extracted_pending_review"

    return normalized, errors


def suspicious_normalized_reason(entry: NormalizedEntry) -> Optional[str]:
    if not entry.lemma:
        return "empty_lemma"
    if not entry.pos:
        return "empty_pos"
    if has_unmatched_parentheses(entry.raw_entry):
        return "unmatched_parentheses"
    if entry.lemma in {"v", "n", "adj", "adv", "prep", "pron", "det"} and entry.surface_form == entry.lemma:
        return "pos_only_surface"
    if any("/" in alt for alt in entry.alt_forms):
        return "slash_residual_in_alt_forms"
    if semantic_fragment_alt_form_residuals(entry):
        return "semantic_fragment_alt_form_residual"
    return None


def validate_outputs(raw_entries: List[RawEntry], normalized_entries: List[NormalizedEntry], errors: List[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []
    if not raw_entries:
        warnings.append("no_raw_entries_extracted")
    if not normalized_entries:
        warnings.append("no_normalized_entries_created")

    hard_errors = [err for err in errors if err.get("error") not in {"no_pos_group_found"}]
    if hard_errors:
        warnings.append(f"normalization_hard_errors_count={len(hard_errors)}")

    error_counter = Counter(err.get("error", "unknown") for err in errors)
    for err_name, count in sorted(error_counter.items()):
        warnings.append(f"excluded_{err_name}_count={count}")

    duplicate_key_count = sum(1 for _key, count in Counter((e.lemma, tuple(e.pos)) for e in normalized_entries).items() if count > 1)
    if duplicate_key_count:
        warnings.append(f"same_lemma_pos_duplicate_review_count={duplicate_key_count}")

    suspicious = [(e.entry_id, suspicious_normalized_reason(e)) for e in normalized_entries if suspicious_normalized_reason(e)]
    if suspicious:
        warnings.append(f"suspicious_normalized_entries_count={len(suspicious)}")

    source_pos_reviews = [e for e in normalized_entries if "source_pos_semantic_review" in e.risk_flags]
    if source_pos_reviews:
        warnings.append(f"source_pos_semantic_review_count={len(source_pos_reviews)}")

    return warnings


def build_summary(
    pdf_path: Path,
    source_id: str,
    page_start: int,
    page_end: int,
    raw_entries: List[RawEntry],
    normalized_entries: List[NormalizedEntry],
    errors: List[Dict[str, Any]],
    warnings: List[str],
) -> Dict[str, Any]:
    pos_counter = Counter(pos for entry in normalized_entries for pos in entry.pos)
    feature_counter = Counter(feature for entry in normalized_entries for feature in entry.grammar_features)
    section_counter = Counter(entry.raw_section or "unknown" for entry in normalized_entries)
    page_counter = Counter(str(entry.source_page) for entry in normalized_entries)
    risk_counter = Counter(flag for entry in normalized_entries for flag in entry.risk_flags)
    parser_rule_counter = Counter(entry.parser_rule for entry in normalized_entries)
    error_counter = Counter(err.get("error", "unknown") for err in errors)
    duplicate_key_counter = Counter((e.lemma, tuple(e.pos)) for e in normalized_entries)
    duplicate_key_count = sum(1 for _key, count in duplicate_key_counter.items() if count > 1)
    hard_errors = [err for err in errors if err.get("error") not in {"no_pos_group_found"}]
    suspicious_entries = [e for e in normalized_entries if suspicious_normalized_reason(e)]
    semantic_fragment_residual_entries = [e for e in normalized_entries if semantic_fragment_alt_form_residuals(e)]
    source_pos_review_entries = [e for e in normalized_entries if "source_pos_semantic_review" in e.risk_flags]
    known_source_pos_items = [e for e in normalized_entries if source_pos_semantic_review_info(e.lemma, e.pos)]
    unflagged_known_source_pos_items = [e for e in known_source_pos_items if "source_pos_semantic_review" not in e.risk_flags]

    validation_status = "PASS"
    if not normalized_entries or hard_errors or suspicious_entries:
        validation_status = "FAIL"
    elif warnings:
        validation_status = "PASS_WITH_WARNINGS"

    return {
        "validation_status": validation_status,
        "source_id": source_id,
        "source_file": str(pdf_path),
        "source_level": SOURCE_LEVEL,
        "canonical_level": CANONICAL_LEVEL,
        "cefr_estimate": CEFR_ESTIMATE,
        "parser_name": "extract_cambridge_a2_key_vocabulary.py",
        "parser_policy_version": "a2_key_textline_parser_v2_fullfix",
        "page_scope": {
            "scope": "alphabetical_vocabulary_list_only",
            "page_start": page_start,
            "page_end": page_end,
            "appendices_excluded": True,
        },
        "raw_entry_count": len(raw_entries),
        "normalized_entry_count": len(normalized_entries),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "warnings": warnings,
        "same_lemma_pos_duplicate_review_count": duplicate_key_count,
        "counts_by_pos": dict(sorted(pos_counter.items())),
        "counts_by_grammar_feature": dict(sorted(feature_counter.items())),
        "counts_by_section": dict(sorted(section_counter.items())),
        "counts_by_page": dict(sorted(page_counter.items(), key=lambda kv: int(kv[0]))),
        "counts_by_parser_rule": dict(sorted(parser_rule_counter.items())),
        "risk_flags": dict(sorted(risk_counter.items())),
        "errors_by_type": dict(sorted(error_counter.items())),
        "alt_form_cleanup": {
            "policy_version": "a2_key_clean_alt_forms_v2",
            "semantic_fragment_alt_form_residual_count": len(semantic_fragment_residual_entries),
            "sample_semantic_fragment_alt_form_residuals": [
                {"entry_id": e.entry_id, "lemma": e.lemma, "alt_forms": semantic_fragment_alt_form_residuals(e)}
                for e in semantic_fragment_residual_entries[:10]
            ],
        },
        "source_pos_semantic_review": {
            "known_review_policy_version": "a2_key_source_pos_review_v1",
            "source_pos_semantic_review_count": len(source_pos_review_entries),
            "unflagged_known_source_pos_semantic_review_count": len(unflagged_known_source_pos_items),
            "samples": [
                {
                    "entry_id": e.entry_id,
                    "lemma": e.lemma,
                    "pos": e.pos,
                    "review": source_pos_semantic_review_info(e.lemma, e.pos),
                }
                for e in source_pos_review_entries[:10]
            ],
        },
        "quality_gates": {
            "no_empty_raw_entries": bool(raw_entries),
            "no_empty_normalized_entries": bool(normalized_entries),
            "no_hard_normalization_errors": not hard_errors,
            "no_suspicious_normalized_entries": not suspicious_entries,
            "no_unmatched_parentheses_normalized_entries": not any(has_unmatched_parentheses(e.raw_entry) for e in normalized_entries),
            "no_slash_residual_in_alt_forms": not any("/" in alt for e in normalized_entries for alt in e.alt_forms),
            "no_semantic_fragment_alt_forms": not semantic_fragment_residual_entries,
            "known_source_pos_semantic_items_flagged": not unflagged_known_source_pos_items,
            "source_pos_semantic_review_is_non_blocking": True,
            "appendices_excluded": True,
            "ulga_graph_modified": False,
            "learner_facing_content_generated": False,
        },
        "boundary_confirmation": {
            "ocr_used": False,
            "pdf_text_layer_only": True,
            "authority_graph_modified": False,
            "learner_facing_content_generated": False,
            "content_extraction_allowed": False,
        },
    }


def run(args: argparse.Namespace) -> int:
    pdf_path = resolve_pdf_path(Path(args.pdf).resolve(strict=False))
    out_dir = Path(args.out_dir).resolve()
    source_id = args.source_id.strip() if args.source_id else SOURCE_ID_DEFAULT
    page_start = int(args.page_start)
    page_end = int(args.page_end)

    print(f"[INFO] PDF: {pdf_path}")
    print(f"[INFO] Source ID: {source_id}")
    print(f"[INFO] Page scope: {page_start}-{page_end} (A-Z alphabetical list only)")
    print(f"[INFO] Output dir: {out_dir}")

    lines = extract_text_lines(pdf_path, page_start=page_start, page_end=page_end)
    print(f"[INFO] Extracted text lines: {len(lines)}")

    raw_entries = build_raw_entries(lines, source_id=source_id, source_file=pdf_path.name)
    print(f"[INFO] Raw entries: {len(raw_entries)}")

    normalized_entries, errors = normalize_entries(raw_entries)
    print(f"[INFO] Normalized entries: {len(normalized_entries)}")
    print(f"[INFO] Errors / excluded entries: {len(errors)}")

    warnings = validate_outputs(raw_entries, normalized_entries, errors)
    summary = build_summary(
        pdf_path=pdf_path,
        source_id=source_id,
        page_start=page_start,
        page_end=page_end,
        raw_entries=raw_entries,
        normalized_entries=normalized_entries,
        errors=errors,
        warnings=warnings,
    )

    raw_out = out_dir / "cambridge_a2_key_vocabulary_raw.json"
    normalized_out = out_dir / "cambridge_a2_key_vocabulary_normalized.json"
    summary_out = out_dir / "cambridge_a2_key_vocabulary_summary.json"
    errors_out = out_dir / "cambridge_a2_key_vocabulary_errors.json"

    write_json(raw_out, [asdict(item) for item in raw_entries])
    write_json(normalized_out, [asdict(item) for item in normalized_entries])
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
    parser = argparse.ArgumentParser(description="Extract Cambridge A2 Key vocabulary PDF into JSON artifacts.")
    parser.add_argument("--pdf", required=True, help="Path to Cambridge A2 Key vocabulary PDF.")
    parser.add_argument("--out-dir", required=True, help="Output directory for JSON artifacts.")
    parser.add_argument("--source-id", default=None, help=f"Optional source_id. Default: {SOURCE_ID_DEFAULT}")
    parser.add_argument("--page-start", default=DEFAULT_PAGE_START, type=int, help="One-indexed first page of the A-Z vocabulary list. Default: 4")
    parser.add_argument("--page-end", default=DEFAULT_PAGE_END, type=int, help="One-indexed last page of the A-Z vocabulary list. Default: 23")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
