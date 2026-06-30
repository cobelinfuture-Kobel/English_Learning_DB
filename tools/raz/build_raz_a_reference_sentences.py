import json
import logging
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


MANIFEST_RELATIVE_PATH = Path("input") / "manifest" / "raz_a_books_manifest.xlsx"
MANIFEST_SHEET = "books_manifest"
PDF_DIR_RELATIVE_PATH = Path("input") / "pdf"
OUTPUT_EXCEL_RELATIVE_PATH = Path("output") / "excel" / "raz_a_reference_sentences.xlsx"
OUTPUT_JSON_DIR_RELATIVE_PATH = Path("output") / "json"
OUTPUT_LOG_RELATIVE_PATH = Path("output") / "logs" / "extraction_log.txt"

REQUIRED_MANIFEST_COLUMNS = [
    "book_id",
    "raz_level",
    "book_no",
    "book_title",
    "pdf_file",
    "audio_file",
    "source_note",
]

PAGES_RAW_COLUMNS = [
    "page_id",
    "book_id",
    "raz_level",
    "book_title",
    "pdf_file",
    "page_no",
    "raw_page_text",
    "clean_page_text",
    "text_source",
    "extractor",
    "page_text_status",
    "extraction_confidence",
    "needs_manual_review",
    "notes",
]

SENTENCE_COLUMNS = [
    "sentence_id",
    "book_id",
    "raz_level",
    "book_title",
    "pdf_file",
    "page_no",
    "sentence_order_in_book",
    "sentence_order_on_page",
    "raw_text",
    "clean_text",
    "normalized_text",
    "word_count",
    "unique_word_count",
    "char_count",
    "text_source",
    "extractor",
    "extraction_confidence",
    "sentence_boundary_status",
    "sentence_role",
    "text_direction_status",
    "directionality_confidence",
    "directionality_reason",
    "include_in_reference",
    "reference_text_key",
    "reference_group_id",
    "reference_occurrence_index",
    "reference_occurrence_count",
    "is_reference_canonical",
    "include_in_unique_reference",
    "duplicate_reference_status",
    "duplicate_reason",
    "exclude_reason",
    "punctuation_status",
    "review_status",
    "copyright_flag",
    "notes",
]

SENTENCE_QC_COLUMNS = [
    "qc_id",
    "issue_type",
    "qc_action",
    "reviewer",
    "review_status",
    "qc_notes",
] + SENTENCE_COLUMNS

REFERENCE_DUPLICATE_GROUP_COLUMNS = [
    "reference_group_id",
    "book_id",
    "raz_level",
    "book_title",
    "reference_text_key",
    "canonical_sentence_id",
    "occurrence_count",
    "page_span",
    "first_page_no",
    "last_page_no",
    "sentence_ids",
    "duplicate_reason",
    "include_in_unique_reference",
]

BOOK_SUMMARY_COLUMNS = [
    "book_id",
    "book_title",
    "raz_level",
    "sentence_count",
    "word_count_total",
    "avg_sentence_length",
    "min_sentence_length",
    "max_sentence_length",
    "unique_word_count",
    "page_count",
    "valid_page_count",
    "needs_review_sentence_count",
    "reference_sentence_count",
    "excluded_sentence_count",
    "unique_reference_sentence_count",
    "duplicate_reference_sentence_count",
    "reference_duplicate_group_count",
    "max_reference_occurrence_count",
    "extraction_status",
    "qa_status",
]

EXTRACTION_REPORT_COLUMNS = [
    "run_id",
    "created_at",
    "input_pdf_count",
    "processed_pdf_count",
    "failed_pdf_count",
    "total_books",
    "total_pages",
    "total_sentences",
    "reference_sentence_count",
    "excluded_sentence_count",
    "unique_reference_sentence_count",
    "duplicate_reference_sentence_count",
    "reference_duplicate_group_count",
    "max_reference_occurrence_count",
    "avg_sentences_per_book",
    "avg_words_per_sentence",
    "image_pdf_count",
    "needs_review_sentence_count",
    "output_excel",
    "status",
    "reference_safety_status",
    "bad_reference_count",
    "recoverable_unknown_candidate_count",
    "abnormal_text_layer_artifact_count",
]

NON_CLEAN_STATUSES = {
    "medium_review",
    "needs_review",
    "non_sentence",
    "too_short",
    "too_long",
    "missing_punctuation",
}

TERMINAL_PUNCTUATION = {".": "period", "?": "question", "!": "exclamation"}
TOKEN_STRIP_CHARS = ".,?!"
URL_MARKERS = ("www", "readinga-z", ".com")
PHOTO_CREDIT_MARKERS = (
    "photo credits",
    "front cover",
    "back cover",
    "title page",
    "123rf",
    "istockphoto",
    "shutterstock",
    "getty",
    "photo",
)
COPYRIGHT_MARKERS = (
    "©",
    "穢",
    "copyright",
    "all rights reserved",
    "written by",
    "learning a-z",
    "fountas",
    "pinnell",
    "reading recovery",
    "dra",
)
BENCHMARK_MARKERS = (
    "benchmark",
    "level a",
    "level b",
    "level c",
    "word count",
    "correlation",
    "reading a-z level",
)
LAYOUT_NOISE_MARKERS = (
    "benchmark",
    "level",
    "word count",
    "page ",
    "photo credits",
    "written by",
    "correlation",
    "www",
    ".com",
    "readinga-z",
)
MIRRORED_ROLE = "mirrored_text_artifact"
MIRRORED_EXCLUDE_REASON = "mirrored_or_rotated_text"
TITLE_CONTAMINATION_ROLE = "title_contamination_artifact"
TITLE_CONTAMINATION_EXCLUDE_REASON = "front_back_matter_title_contamination"
MIXED_DIRECTION_ROLE = "mixed_direction_text_artifact"
MIXED_DIRECTION_EXCLUDE_REASON = "mixed_direction_body_text"
ABNORMAL_TEXT_LAYER_ROLE = "text_layer_artifact"
ABNORMAL_TEXT_LAYER_EXCLUDE_REASON = "abnormal_text_layer_artifact"
FRONT_BACK_MATTER_MARKERS = (
    "photo credits",
    "front cover",
    "back cover",
    "title page",
    "correlation",
    "fountas",
    "pinnell",
    "reading recovery",
    "dra",
    "all rights reserved",
    "written by",
    "illustrated by",
    "learning a-z",
    "copyright",
    "©",
    "穢",
    "word count",
    "benchmark",
    "leveled book",
    "level a",
    "reading a-z",
    "readinga-z",
    "www",
    ".com",
    "123rf",
    "istockphoto",
)
MIRRORED_MARKERS = (
    "z-agnidaer",
    "agnidaer",
    "moc",
    "koob",
    "kramhcneb",
    "gnidaer",
    "gnidaer",
    "tnuoc drow",
    "tnuoc",
    "detartsulli",
    "yb nettirw",
    "slairetam",
    "skoob",
    "sdnasuoht",
    "tisiv",
    "devreser sthgir lla",
)
MIRRORED_COMMON_WORDS = (
    "slairetam",
    "dna",
    "skoob",
    "fo",
    "sdnasuoht",
    "rof",
    "moc",
    "gnidaer",
    "koob",
    "kramhcneb",
)
KNOWN_FORWARD_WORDS = {
    "reading",
    "book",
    "benchmark",
    "materials",
    "books",
    "count",
    "word",
    "illustrated",
    "written",
    "visit",
    "home",
    "goes",
    "bird",
    "vegetables",
    "learning",
    "leveled",
}
FORWARD_FUNCTION_WORDS = {
    "i",
    "my",
    "the",
    "this",
    "these",
    "is",
    "are",
    "go",
    "goes",
    "can",
    "has",
    "have",
    "to",
    "in",
    "out",
    "on",
    "over",
    "under",
    "a",
    "an",
    "he",
    "she",
    "it",
}
AMBIGUOUS_REVERSED_TOKENS = {"a", "i", "ot", "ni", "na", "no", "si"}
TEXT_DIRECTION_STATUSES_UNSAFE = {
    "reversed_text",
    "mixed_direction",
    "rotated_or_mirrored",
    "reading_order_interleaved",
    "unknown_direction",
}


class ExtractionError(RuntimeError):
    pass


def build_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("raz_reference_builder")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def close_logger(logger: logging.Logger) -> None:
    handlers = list(logger.handlers)
    for handler in handlers:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def get_base_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id_from_now() -> str:
    return datetime.now(timezone.utc).strftime("RUN_%Y%m%d_%H%M%S")


def sanitize_manifest_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def load_manifest(manifest_path: Path) -> pd.DataFrame:
    if not manifest_path.exists():
        raise ExtractionError(
            f"Missing required manifest: {manifest_path}. "
            "Expected input/manifest/raz_a_books_manifest.xlsx."
        )

    df = pd.read_excel(manifest_path, sheet_name=MANIFEST_SHEET)
    df.columns = [str(column).strip() for column in df.columns]

    missing_columns = [column for column in REQUIRED_MANIFEST_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ExtractionError(
            "Manifest is missing required columns: " + ", ".join(missing_columns)
        )

    return df[REQUIRED_MANIFEST_COLUMNS].copy()


def resolve_pdf_extractor() -> Tuple[str, Any]:
    try:
        import pdfplumber  # type: ignore

        return "pdfplumber_v0.1", pdfplumber
    except ModuleNotFoundError:
        pass

    try:
        import pypdf  # type: ignore

        return "pypdf_v0.1", pypdf
    except ModuleNotFoundError:
        pass

    raise ExtractionError(
        "No supported PDF text-layer extractor is available. "
        "Install pdfplumber or pypdf. OCR is intentionally disabled."
    )


def clean_page_text(raw_text: str) -> str:
    lines: List[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"\d+", stripped):
            continue
        normalized = re.sub(r"\s+", " ", stripped)
        lines.append(normalized)
    return "\n".join(lines).strip()


def count_valid_characters(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def split_sentences(clean_text: str) -> List[str]:
    flattened = re.sub(r"\s+", " ", clean_text.replace("\r", " ").replace("\n", " ")).strip()
    if not flattened:
        return []

    matches = re.findall(r"[^.?!]+[.?!]|[^.?!]+$", flattened)
    return [match.strip() for match in matches if match and match.strip()]


def normalize_sentence_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()


def tokenize_sentence(clean_text: str) -> List[str]:
    tokens: List[str] = []
    for token in clean_text.split(" "):
        stripped = token.strip().strip(TOKEN_STRIP_CHARS)
        if stripped:
            tokens.append(stripped)
    return tokens


def tokenize_alpha_words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)?", text.lower())


def check_reversed_word_anomaly(text: str, valid_words: set) -> bool:
    words = [w for w in tokenize_alpha_words(text) if len(w) >= 3]
    for w in words:
        if w not in valid_words:
            rev_w = w[::-1]
            if rev_w in valid_words:
                return True
    return False


def has_abnormal_reference_text(clean_text: str) -> bool:
    if not clean_text:
        return False
    # 1. Replacement char, backslash, angle brackets, bullet
    if any(char in clean_text for char in ("\ufffd", "\\", "<", ">", "•")):
        return True
    
    # 2. -- prefix
    if clean_text.strip().startswith("--"):
        return True
    
    # 3. Known split-token artifacts (case-insensitive substring/word check)
    lower_text = clean_text.lower()
    if "sle ep" in lower_text:
        return True
    if "a le" in lower_text:
        return True
    if "bi rd" in lower_text:
        return True
    if "this 1s" in lower_text:
        return True
    if "r •" in lower_text:
        return True
    
    # For cherr: check as a word boundary
    if re.search(r"\bcherr\b", lower_text):
        return True
        
    # 4. Digit-letter confusion: e.g., 1s, lit1g
    if re.search(r"\b(?:\d+[a-zA-Z]|[a-zA-Z]+\d)[a-zA-Z0-9]*\b", lower_text):
        return True
        
    # 5. Symbol-only rows
    if not any(char.isalnum() for char in clean_text):
        return True
        
    # 6. High symbol density (non-alphanumeric ratio > 0.15)
    symbol_count = sum(1 for char in clean_text if not char.isalnum() and not char.isspace())
    if symbol_count / max(len(clean_text), 1) > 0.15:
        return True
        
    return False


A_LEVEL_BODY_PATTERNS = [
    # 1. Subject pronoun patterns
    r"^i\s+(?:see|can|go|like|love|have|dream|draw|set|save|am|hide)\b",
    r"^we\s+(?:see|can|go|like|love|have|make|pack|buy|learn|do|bake|give|draw|count)\b",
    r"^you\s+(?:can|see|like|have|go|do|want|dance)\b",
    r"^(?:he|she|it)\s+(?:has|is|can|goes|runs|sees|likes|counts|loves|sleeps|fly|flies|walk|walks|swim|swims|climb|climbs|jump|jumps|eat|eats|hide|hides|find|finds|looks|feels|tastes|smells|sounds|bakes|makes|plays)\b",
    r"^they\s+(?:are|can|see|like|have|go|do|want)\b",
    
    # 2. Demonstratives and determiners
    r"^this\s+(?:is|looks|feels|smells|tastes|sounds|insect|lizard)\b",
    r"^these\s+(?:are|shoes)\b",
    r"^here\s+(?:is|are)\b",
    r"^there\s+(?:is|are)\b",
    
    # 3. Simple noun phrase starts (e.g. animal names, mom, dad, grandparents, baby, etc.)
    r"^(?:raccoon|butterfly|bird|dog|cat|rabbit|fish|lizard|hamster|baby|grandparents|animals)\s+(?:is|are|goes|go|has|have|runs|run|sees|see|likes|like|can|lives|live|flies|fly|looks|feels|tastes|smells|sounds|sleeps|hide|hides|full|happy)\b",
    r"^(?:mom|dad)\s+(?:and|is|has|can|likes|loves|sees|goes)\b",
    
    # 4. Names
    r"^carlos\s+(?:has|goes|counts|is|can)\b",
    r"^maria\s+(?:goes|counts|has|is|can|and)\b",
    
    # 5. Adverbs and questions
    r"^now\s+we\s+[a-z]+\b",
    r"^who\s+(?:has|runs|wants|stole)\b",
    r"^(?:what|where|who|how|when|why)\s+(?:is|are|lives|goes|has|can|do|does|we|to)\b",
    
    # 6. General Subject + Verb pattern (Noun/name + action verb)
    r"^[a-z]+\s+(?:is|are|has|have|goes|go|can|runs|run|sees|see|likes|like|counts|count|loves|love|sleeps|sleep|fly|flies|walk|walks|swim|swims|climb|climbs|jump|jumps|eat|eats|hide|hides|find|finds|looks|feels|tastes|smells|sounds|bakes|makes|plays)\b",
]


def matches_a_level_body_pattern(clean_text: str, normalized_text: str) -> bool:
    stripped_text = re.sub(r"[.?!]+$", "", normalized_text.lower()).strip()
    for pattern in A_LEVEL_BODY_PATTERNS:
        if re.search(pattern, stripped_text):
            return True
    return False


def load_valid_words(logger: logging.Logger) -> set:
    logger.info("Loading vocabulary wordlists for reversed-word anomaly detection...")
    valid_words = set()
    base_dir = get_base_dir()
    
    # Define fallbacks
    fallback_words = {
        "turtle", "turtles", "worm", "worms", "see", "five", "four", "fish", "bird", "birds",
        "dog", "dogs", "cat", "cats", "rabbit", "rabbits", "animal", "animals", "bear", "bears",
        "home", "goes", "vegetables", "learning", "leveled", "benchmark", "materials", "books"
    }
    fallback_words.update(KNOWN_FORWARD_WORDS)
    fallback_words.update(FORWARD_FUNCTION_WORDS)
    
    # 1. Load vocabulary.json
    vocab_json_path = base_dir / "vocabulary" / "json" / "vocabulary.json"
    if vocab_json_path.exists():
        try:
            with open(vocab_json_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                for r in records:
                    word = r.get("word")
                    if word:
                        valid_words.add(word.lower().strip())
            logger.info("Loaded %d words from vocabulary.json", len(records))
        except Exception as e:
            logger.error("Failed to load vocabulary.json: %s", e)
            
    # 2. Load NGSL+with+SFI+(31K).xlsx
    ngsl_path = base_dir / "vocabulary" / "source" / "NGSL+with+SFI+(31K).xlsx"
    if ngsl_path.exists():
        try:
            df = pd.read_excel(ngsl_path)
            if "Lemma" in df.columns:
                lemmas = df["Lemma"].dropna().astype(str).str.lower().str.strip()
                valid_words.update(lemmas)
            logger.info("Loaded words from NGSL+with+SFI+(31K).xlsx. Total unique vocabulary: %d", len(valid_words))
        except Exception as e:
            logger.error("Failed to load NGSL+with+SFI+(31K).xlsx: %s", e)
            
    # 3. Load English Vocabulary Profile Online.xlsx
    evp_path = base_dir / "vocabulary" / "source" / "English Vocabulary Profile Online.xlsx"
    if evp_path.exists():
        try:
            df = pd.read_excel(evp_path)
            if "Base Word" in df.columns:
                words = df["Base Word"].dropna().astype(str).str.lower().str.strip()
                valid_words.update(words)
            logger.info("Loaded words from English Vocabulary Profile Online.xlsx. Total unique vocabulary: %d", len(valid_words))
        except Exception as e:
            logger.error("Failed to load English Vocabulary Profile Online.xlsx: %s", e)
            
    if not valid_words:
        logger.warning("All vocabulary files failed to load. Using localized fallback set.")
        valid_words = fallback_words.copy()
    else:
        valid_words.update(fallback_words)
        
    # Generate common inflections (plurals and simple verb endings) to ensure coverage
    inflections = set()
    for word in valid_words:
        if len(word) >= 3:
            inflections.add(word + "s")
            inflections.add(word + "es")
            if word.endswith("y"):
                inflections.add(word[:-1] + "ies")
            inflections.add(word + "ed")
            inflections.add(word + "ing")
            if word.endswith("e"):
                inflections.add(word + "d")
                
    valid_words.update(inflections)
    logger.info("Total validated vocabulary set size (including inflections): %d", len(valid_words))
    return valid_words


def reverse_token(token: str) -> str:
    return token[::-1]


def is_body_page(page_no: int, page_count: int) -> bool:
    return 3 <= page_no <= max(page_count - 2, 2)


def token_has_leading_punctuation(token: str) -> bool:
    return bool(re.match(r"^[.?!][A-Za-z]+", token))


def score_forward_text(clean_text: str, normalized_text: str, book_title: str) -> float:
    del book_title
    tokens = tokenize_alpha_words(normalized_text)
    token_set = set(tokens)
    score = 0.0

    score += sum(1.0 for token in tokens if token in FORWARD_FUNCTION_WORDS)
    if clean_text.endswith((".", "?", "!")) and not clean_text.startswith((".", "?", "!")):
        score += 1.0

    forward_patterns = (
        r"\bi go\b",
        r"\bi can\b",
        r"\bthis is\b",
        r"\bthese are\b",
        r"\bthe [a-z]+ goes\b",
        r"\bmy [a-z]+ is\b",
        r"\bhe [a-z]+\b",
        r"\bshe [a-z]+\b",
    )
    score += sum(1.5 for pattern in forward_patterns if re.search(pattern, normalized_text))

    if tokens[:1] and tokens[0] in {"i", "my", "the", "this", "these", "he", "she", "it"}:
        score += 1.0

    if len(token_set.intersection(KNOWN_FORWARD_WORDS)) >= 2:
        score += 1.0

    return score


def score_reversed_text(clean_text: str, normalized_text: str, book_title: str) -> float:
    tokens = tokenize_alpha_words(normalized_text)
    score = 0.0

    if clean_text.startswith((".", "?", "!")):
        score += 2.0
    if any(token_has_leading_punctuation(token) for token in normalized_text.split()):
        score += 1.5

    reversed_function_hits = 0
    reversed_forward_hits = 0
    title_tokens = [token for token in tokenize_alpha_words(book_title) if len(token) >= 3]
    reversed_title_tokens = {reverse_token(token) for token in title_tokens}

    for token in tokens:
        if len(token) >= 3 and token in MIRRORED_COMMON_WORDS:
            score += 1.5
        if len(token) >= 3 and reverse_token(token) in FORWARD_FUNCTION_WORDS:
            reversed_function_hits += 1
        if len(token) >= 4 and reverse_token(token) in KNOWN_FORWARD_WORDS:
            reversed_forward_hits += 1
        if token in reversed_title_tokens:
            score += 1.5

    score += reversed_function_hits * 1.0
    score += reversed_forward_hits * 1.5

    if reversed_function_hits >= 2:
        score += 1.0

    return score


def is_reversed_body_text(clean_text: str, normalized_text: str, book_title: str) -> bool:
    reverse_score = score_reversed_text(clean_text, normalized_text, book_title)
    forward_score = score_forward_text(clean_text, normalized_text, book_title)
    tokens = tokenize_alpha_words(normalized_text)
    strong_reversed_prefix = len(tokens) >= 3 and sum(
        1 for token in tokens[:3] if len(token) >= 3 and reverse_token(token) in FORWARD_FUNCTION_WORDS.union(KNOWN_FORWARD_WORDS)
    ) >= 2
    return clean_text.startswith((".", "?", "!")) or strong_reversed_prefix or (
        reverse_score >= 4.0 and forward_score <= 2.0
    )


def has_mixed_direction_pattern(clean_text: str, normalized_text: str, book_title: str) -> bool:
    tokens = tokenize_alpha_words(normalized_text)
    if len(tokens) < 4:
        return False

    reversed_flags = [
        len(token) >= 3
        and token not in AMBIGUOUS_REVERSED_TOKENS
        and (
            reverse_token(token) in FORWARD_FUNCTION_WORDS
            or reverse_token(token) in KNOWN_FORWARD_WORDS
            or token in {reverse_token(title_token) for title_token in tokenize_alpha_words(book_title) if len(title_token) >= 3}
        )
        for token in tokens
    ]
    forward_flags = [token in FORWARD_FUNCTION_WORDS or token in KNOWN_FORWARD_WORDS for token in tokens]

    if any(forward_flags) and any(reversed_flags):
        prefix_reversed = sum(1 for flag in reversed_flags[:4] if flag) >= 2 and sum(1 for flag in forward_flags[-4:] if flag) >= 2
        suffix_reversed = sum(1 for flag in forward_flags[:4] if flag) >= 2 and sum(1 for flag in reversed_flags[-4:] if flag) >= 2
        interleaved = any(
            forward_flags[index] and reversed_flags[index + 1]
            or reversed_flags[index] and forward_flags[index + 1]
            for index in range(len(tokens) - 1)
        )
        return prefix_reversed or suffix_reversed or interleaved

    return False


def classify_line_direction(clean_line_text: str, book_title: str) -> str:
    normalized_text = normalize_sentence_text(clean_line_text).lower()
    tokens = tokenize_alpha_words(normalized_text)
    if len(tokens) < 2 or has_url_like_fragment(normalized_text) or contains_any_marker(normalized_text, COPYRIGHT_MARKERS):
        return "noise_line"
    if is_mirrored_text_artifact(clean_line_text, normalized_text, book_title):
        return "reversed_line"

    forward_score = score_forward_text(clean_line_text, normalized_text, book_title)
    reverse_score = score_reversed_text(clean_line_text, normalized_text, book_title)
    if has_mixed_direction_pattern(clean_line_text, normalized_text, book_title):
        return "mixed_line"
    if reverse_score >= 4.0 and forward_score <= 2.0:
        return "reversed_line"
    if forward_score >= 3.0 and reverse_score <= 1.0:
        return "forward_line"
    if forward_score >= 2.0 and reverse_score >= 2.0:
        return "mixed_line"
    if not tokens:
        return "noise_line"
    return "unknown_line"


def scan_page_line_directions(
    clean_page_text: str,
    book_title: str,
    page_no: int,
    page_count: int,
) -> Dict[str, Any]:
    counts = {
        "forward_line_count": 0,
        "reversed_line_count": 0,
        "mixed_line_count": 0,
        "noise_line_count": 0,
        "unknown_line_count": 0,
        "has_interleaving": False,
    }

    for raw_line in clean_page_text.splitlines():
        line_text = normalize_sentence_text(raw_line)
        if not line_text:
            continue
        line_status = classify_line_direction(line_text, book_title)
        counts[f"{line_status.replace('_line', '')}_line_count"] += 1

    counts["has_interleaving"] = (
        is_body_page(page_no, page_count)
        and counts["forward_line_count"] >= 1
        and (counts["reversed_line_count"] >= 1 or counts["mixed_line_count"] >= 1)
    )
    return counts


def detect_text_direction_status(
    clean_text: str,
    normalized_text: str,
    book_title: str,
    page_no: int,
    page_count: int,
    page_context: str,
    tokens: List[str],
    page_direction_context: Dict[str, Any],
) -> Tuple[str, float, str]:
    if not tokens:
        return "not_applicable", 0.0, "not_applicable_non_reference"

    if is_mirrored_text_artifact(clean_text, normalized_text, book_title):
        return "rotated_or_mirrored", 1.0, "rotated_or_mirrored_marker"

    if has_url_like_fragment(normalized_text):
        return "not_applicable", 0.0, "not_applicable_non_reference"
    if contains_any_marker(normalized_text, COPYRIGHT_MARKERS) or contains_any_marker(normalized_text, PHOTO_CREDIT_MARKERS):
        return "not_applicable", 0.0, "not_applicable_non_reference"
    layout_like_non_reference = (
        contains_any_marker(normalized_text, BENCHMARK_MARKERS)
        or len(re.findall(r"\d+", normalized_text)) >= 2
    )
    if layout_like_non_reference:
        return "not_applicable", 0.0, "not_applicable_non_reference"
    if is_title_contamination_artifact(
        clean_text=clean_text,
        normalized_text=normalized_text,
        book_title=book_title,
        page_no=page_no,
        page_count=page_count,
        page_context=page_context,
        word_count=len(tokens),
        tokens=tokens,
    ):
        return "not_applicable", 0.0, "not_applicable_non_reference"

    forward_score = score_forward_text(clean_text, normalized_text, book_title)
    reverse_score = score_reversed_text(clean_text, normalized_text, book_title)
    mixed_pattern = has_mixed_direction_pattern(clean_text, normalized_text, book_title)
    reversed_title = has_reversed_title_token(normalized_text, book_title)
    tokens_alpha = tokenize_alpha_words(normalized_text)
    reversed_evidence_flags = [
        len(token) >= 3
        and token not in AMBIGUOUS_REVERSED_TOKENS
        and (
            reverse_token(token) in FORWARD_FUNCTION_WORDS
            or reverse_token(token) in KNOWN_FORWARD_WORDS
            or reverse_token(token) in tokenize_alpha_words(book_title)
        )
        for token in tokens_alpha
    ]
    forward_evidence_flags = [token in FORWARD_FUNCTION_WORDS or token in KNOWN_FORWARD_WORDS for token in tokens_alpha]
    suspicious_short_reversed = any(
        len(token) >= 2 and len(token) <= 3 and token not in AMBIGUOUS_REVERSED_TOKENS and reverse_token(token) in FORWARD_FUNCTION_WORDS
        for token in tokens_alpha
    )

    if is_reversed_body_text(clean_text, normalized_text, book_title):
        reason = "explicit_reversed_marker" if clean_text.startswith((".", "?", "!")) else "reversed_body_pattern"
        return "reversed_text", 1.0, reason

    prefix_reversed = sum(1 for flag in reversed_evidence_flags[:4] if flag) >= 2 and sum(1 for flag in forward_evidence_flags[-4:] if flag) >= 2
    suffix_reversed = sum(1 for flag in forward_evidence_flags[:4] if flag) >= 2 and sum(1 for flag in reversed_evidence_flags[-4:] if flag) >= 2

    if reversed_title and forward_score >= 3.0 and reverse_score >= 1.0:
        return "mixed_direction", 0.9, "mixed_forward_and_reversed_scores"

    if mixed_pattern or prefix_reversed or suffix_reversed or (forward_score >= 3.0 and reverse_score >= 3.0):
        if reversed_title and forward_score >= 3.0:
            return "mixed_direction", 0.9, "mixed_forward_and_reversed_scores"
        if prefix_reversed and forward_score >= 3.0:
            return "mixed_direction", 0.9, "mixed_reversed_prefix_forward_suffix"
        if suffix_reversed and forward_score >= 3.0:
            return "mixed_direction", 0.9, "mixed_forward_prefix_reversed_suffix"
        return "mixed_direction", 0.9, "mixed_forward_and_reversed_scores"

    if (
        page_direction_context.get("has_interleaving")
        and reverse_score >= 1.0
        and forward_score >= 2.0
        and is_body_page(page_no, page_count)
    ):
        return "reading_order_interleaved", 0.8, "line_level_interleaving"

    if forward_score >= 3.0 and reverse_score <= 1.0 and not reversed_title:
        return "forward_clean", 1.0, "forward_clean_pattern"

    if reverse_score >= 2.5 and forward_score <= 2.0:
        reason = "reversed_title_token" if reversed_title else "reversed_body_pattern"
        return "reversed_text", 0.8, reason

    if is_body_page(page_no, page_count) and (
        page_direction_context.get("has_interleaving")
        or page_direction_context.get("mixed_line_count", 0) >= 1
        or page_direction_context.get("reversed_line_count", 0) >= 1
    ):
        if suspicious_short_reversed or reversed_title or reverse_score > 0:
            return "unknown_direction", 0.6, "unknown_direction_safety_exclusion"

    return "not_applicable", 0.0, "not_applicable_non_reference"


def get_punctuation_status(clean_text: str) -> str:
    if not clean_text:
        return "none"
    return TERMINAL_PUNCTUATION.get(clean_text[-1], "none")


def determine_sentence_status(clean_text: str, tokens: List[str]) -> Tuple[str, str]:
    punctuation_status = get_punctuation_status(clean_text)
    if punctuation_status == "none":
        return "missing_punctuation", punctuation_status

    if not tokens:
        return "non_sentence", punctuation_status

    joined_alpha = "".join(tokens)
    if not re.search(r"[A-Za-z]", joined_alpha):
        return "non_sentence", punctuation_status

    word_count = len(tokens)
    if word_count == 1:
        return "too_short", punctuation_status
    if word_count <= 8:
        return "clean", punctuation_status
    if word_count <= 12:
        return "medium_review", punctuation_status
    return "too_long", punctuation_status


def contains_any_marker(normalized_text: str, markers: Tuple[str, ...]) -> bool:
    return any(marker in normalized_text for marker in markers)


def has_url_like_fragment(normalized_text: str) -> bool:
    if contains_any_marker(normalized_text, URL_MARKERS):
        return True
    if re.search(r"\bcom\b", normalized_text):
        return True
    if re.search(r"\bww\s*w\b", normalized_text):
        return True
    return False


def normalize_title(book_title: str) -> str:
    return normalize_sentence_text(book_title).lower()


def canonicalize_reference_text(clean_text: str) -> str:
    normalized = normalize_sentence_text(clean_text).lower()
    normalized = re.sub(r"[.?!]+$", "", normalized).strip()
    return normalized


def is_front_back_matter_page(page_no: int, page_count: int) -> bool:
    return page_no <= 2 or (page_count > 0 and page_no >= page_count - 1)


def page_has_front_back_matter_context(page_text: str) -> bool:
    normalized_page_text = normalize_sentence_text(page_text).lower()
    return any(marker in normalized_page_text for marker in FRONT_BACK_MATTER_MARKERS)


def has_reversed_title_token(normalized_text: str, book_title: str) -> bool:
    title_tokens = [token for token in tokenize_alpha_words(book_title) if len(token) >= 2]
    reversed_title_tokens = {reverse_token(token) for token in title_tokens}
    normalized_tokens = set(tokenize_alpha_words(normalized_text))
    return any(token in normalized_tokens for token in reversed_title_tokens)


def count_mirrored_common_markers(normalized_text: str) -> int:
    return sum(1 for marker in MIRRORED_COMMON_WORDS if marker in normalized_text)


def is_mirrored_text_artifact(clean_text: str, normalized_text: str, book_title: str) -> bool:
    normalized_tokens = tokenize_alpha_words(normalized_text)
    standalone_number_count = len(re.findall(r"\b\d+\b", normalized_text))
    has_reversed_title = has_reversed_title_token(normalized_text, book_title)
    has_reversed_url = (
        "z-agnidaer" in normalized_text
        or normalized_text.strip(" .?!") == "moc"
        or ("moc" in normalized_text and count_mirrored_common_markers(normalized_text) >= 2)
        or (("www" in normalized_text or "ww w" in normalized_text) and any(marker in normalized_text for marker in MIRRORED_MARKERS))
    )
    has_reversed_benchmark = (
        ("koob" in normalized_text or "kramhcneb" in normalized_text or "gnidaer" in normalized_text)
        and ("level" in normalized_text or "level a" in normalized_text or "level b" in normalized_text or "level c" in normalized_text)
    )
    has_reversed_credit = (
        "detartsulli" in normalized_text
        or "yb nettirw" in normalized_text
        or "nworb" in normalized_text
        or "aicilef" in normalized_text
        or "artsmak" in normalized_text
        or "alegna" in normalized_text
    )
    has_reversed_footer = (
        standalone_number_count >= 1
        and "koob" in normalized_text
        and "kramhcneb" in normalized_text
        and has_reversed_title
    )
    has_reversed_sentence_like = count_mirrored_common_markers(normalized_text) >= 2
    reversed_to_forward_hits = sum(
        1 for token in normalized_tokens if len(token) >= 4 and reverse_token(token) in KNOWN_FORWARD_WORDS
    )
    mixed_forward_reversed_footer = has_reversed_title and (
        "level" in normalized_text or "benchmark" in normalized_text or "book" in normalized_text
    )

    return any(
        [
            has_reversed_url,
            has_reversed_benchmark,
            has_reversed_credit,
            has_reversed_footer,
            has_reversed_sentence_like,
            reversed_to_forward_hits >= 2,
            mixed_forward_reversed_footer,
        ]
    )


def has_layout_noise_indicators(normalized_text: str, book_title: str) -> bool:
    book_title_normalized = normalize_title(book_title)
    return (
        contains_any_marker(normalized_text, LAYOUT_NOISE_MARKERS)
        or book_title_normalized in normalized_text
        or len(re.findall(r"\d+", normalized_text)) >= 2
    )


def title_case_ratio(clean_text: str) -> float:
    tokens = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", clean_text)
    if not tokens:
        return 0.0
    title_case_count = sum(1 for token in tokens if token[:1].isupper())
    return title_case_count / len(tokens)


def is_title_contamination_artifact(
    clean_text: str,
    normalized_text: str,
    book_title: str,
    page_no: int,
    page_count: int,
    page_context: str,
    word_count: int,
    tokens: List[str],
) -> bool:
    if not is_front_back_matter_page(page_no, page_count):
        return False
    if not page_has_front_back_matter_context(page_context):
        return False
    if not 2 <= word_count <= 8:
        return False
    if not any(re.search(r"[A-Za-z]", token) for token in tokens):
        return False
    if has_url_like_fragment(normalized_text):
        return False
    if contains_any_marker(normalized_text, COPYRIGHT_MARKERS):
        return False
    if is_mirrored_text_artifact(clean_text, normalized_text, book_title):
        return False

    book_title_normalized = normalize_title(book_title)
    title_like_question = clean_text.strip().endswith("?")
    strong_title_case = title_case_ratio(clean_text) >= 0.8
    starts_with_book_title = bool(book_title_normalized) and normalized_text.startswith(book_title_normalized + " ")
    exact_or_prefixed_title = normalized_text == book_title_normalized or starts_with_book_title
    very_short_fragment = word_count <= 5 and strong_title_case

    return title_like_question or exact_or_prefixed_title or very_short_fragment


def heavy_symbol_density(clean_text: str) -> bool:
    if not clean_text:
        return False
    symbol_count = sum(1 for char in clean_text if not char.isalnum() and not char.isspace())
    return symbol_count / max(len(clean_text), 1) > 0.2


def mostly_numbers(tokens: List[str]) -> bool:
    if not tokens:
        return False
    numeric_tokens = sum(1 for token in tokens if re.fullmatch(r"\d+", token))
    return numeric_tokens >= max(2, math.ceil(len(tokens) * 0.5))


def classify_sentence_role(
    clean_text: str,
    normalized_text: str,
    book_title: str,
    page_no: int,
    page_count: int,
    sentence_boundary_status: str,
    word_count: int,
    tokens: List[str],
    duplicate_count: int,
    page_context: str,
    page_direction_context: Dict[str, Any],
    valid_words: set,
) -> Tuple[str, bool, str, str, float, str]:
    if has_abnormal_reference_text(clean_text):
        return (
            ABNORMAL_TEXT_LAYER_ROLE,
            False,
            ABNORMAL_TEXT_LAYER_EXCLUDE_REASON,
            "not_applicable",
            0.0,
            "not_applicable_non_reference",
        )

    if check_reversed_word_anomaly(clean_text, valid_words):
        return (
            MIXED_DIRECTION_ROLE,
            False,
            "reversed_word_token_anomaly",
            "mixed_direction_text_artifact",
            0.0,
            "reversed_word_token_anomaly",
        )
    book_title_normalized = normalize_title(book_title)
    standalone_number_count = len(re.findall(r"\b\d+\b", normalized_text))
    has_alpha = any(re.search(r"[A-Za-z]", token) for token in tokens)
    has_benchmark_marker = contains_any_marker(normalized_text, BENCHMARK_MARKERS)
    has_url_marker = has_url_like_fragment(normalized_text)
    has_credit_marker = contains_any_marker(normalized_text, PHOTO_CREDIT_MARKERS)
    has_copyright_marker = contains_any_marker(normalized_text, COPYRIGHT_MARKERS)
    has_mirrored_text = is_mirrored_text_artifact(clean_text, normalized_text, book_title)
    has_title_contamination = is_title_contamination_artifact(
        clean_text=clean_text,
        normalized_text=normalized_text,
        book_title=book_title,
        page_no=page_no,
        page_count=page_count,
        page_context=page_context,
        word_count=word_count,
        tokens=tokens,
    )
    layout_noise = has_layout_noise_indicators(normalized_text, book_title)

    default_direction = ("not_applicable", 0.0, "not_applicable_non_reference")

    if has_url_marker:
        return "url_fragment", False, "url_fragment", *default_direction

    if has_mirrored_text:
        return MIRRORED_ROLE, False, MIRRORED_EXCLUDE_REASON, "rotated_or_mirrored", 1.0, "rotated_or_mirrored_marker"

    if has_title_contamination:
        return TITLE_CONTAMINATION_ROLE, False, TITLE_CONTAMINATION_EXCLUDE_REASON, *default_direction

    if has_credit_marker:
        if page_no <= 2:
            return "front_matter", False, "photo_credit", *default_direction
        if page_count and page_no >= page_count - 1:
            return "back_matter", False, "back_matter_or_credits", *default_direction
        return "credit", False, "photo_credit", *default_direction

    if has_copyright_marker:
        return "copyright_notice", False, "copyright_notice", *default_direction

    if (
        standalone_number_count >= 2
        and book_title_normalized
        and book_title_normalized in normalized_text
        and ("benchmark" in normalized_text or "level" in normalized_text)
    ):
        exclude_reason = "duplicate_layout_text" if duplicate_count > 1 else "page_number_or_layout_marker"
        return "layout_artifact", False, exclude_reason, *default_direction

    if page_no <= 2 and has_benchmark_marker and book_title_normalized in normalized_text:
        return "front_matter", False, "cover_or_front_matter", *default_direction

    if page_count and page_no >= page_count - 1 and has_benchmark_marker and book_title_normalized in normalized_text:
        return "back_matter", False, "back_matter_or_credits", *default_direction

    if has_benchmark_marker:
        return "header_footer", False, "benchmark_or_level_label", *default_direction

    if sentence_boundary_status in {"non_sentence", "missing_punctuation"} and layout_noise:
        return "non_sentence_artifact", False, "not_sentence_like", *default_direction

    direction_status, direction_confidence, direction_reason = detect_text_direction_status(
        clean_text=clean_text,
        normalized_text=normalized_text,
        book_title=book_title,
        page_no=page_no,
        page_count=page_count,
        page_context=page_context,
        tokens=tokens,
        page_direction_context=page_direction_context,
    )

    if direction_status in TEXT_DIRECTION_STATUSES_UNSAFE:
        sentence_role = MIRRORED_ROLE if direction_status in {"reversed_text", "rotated_or_mirrored"} else MIXED_DIRECTION_ROLE
        exclude_reason = MIRRORED_EXCLUDE_REASON if direction_status in {"reversed_text", "rotated_or_mirrored"} else MIXED_DIRECTION_EXCLUDE_REASON
        return sentence_role, False, exclude_reason, direction_status, direction_confidence, direction_reason

    if (
        get_punctuation_status(clean_text) != "none"
        and 2 <= word_count <= 8
        and has_alpha
        and not has_url_marker
        and not has_credit_marker
        and not has_copyright_marker
        and not has_benchmark_marker
        and not has_mirrored_text
        and direction_status == "forward_clean"
        and matches_a_level_body_pattern(clean_text, normalized_text)
    ):
        return "body_text", True, "none", direction_status, direction_confidence, direction_reason

    # Controlled A-level body pattern rescue
    # Allow unknown rescue only if:
    # - sentence_boundary_status == clean
    # - body page
    # - matches_a_level_body_pattern(clean_text, normalized_text)
    # - no abnormal reference text (already checked at the top of the function, but good to ensure)
    if (
        sentence_boundary_status == "clean"
        and is_body_page(page_no, page_count)
        and matches_a_level_body_pattern(clean_text, normalized_text)
        and not has_abnormal_reference_text(clean_text)
    ):
        return (
            "body_text",
            True,
            "none",
            "forward_clean",
            1.0,
            "rescued_a_level_body_pattern",
        )

    if (
        sentence_boundary_status in {"too_long", "too_short", "non_sentence", "missing_punctuation"}
        or heavy_symbol_density(clean_text)
        or mostly_numbers(tokens)
        or not has_alpha
    ):
        return "unknown", False, "unknown_noise", direction_status, direction_confidence, direction_reason

    if direction_status == "forward_clean":
        return "unknown", False, "unknown_noise", direction_status, direction_confidence, direction_reason

    if direction_status == "not_applicable":
        return "unknown", False, "unknown_noise", direction_status, direction_confidence, direction_reason

    return MIXED_DIRECTION_ROLE, False, MIXED_DIRECTION_EXCLUDE_REASON, "unknown_direction", 0.6, "unknown_direction_safety_exclusion"


def apply_sentence_filters(
    sentences_v01: List[Dict[str, Any]],
    book_title: str,
    page_count: int,
    page_context_by_page_no: Dict[int, str],
    page_direction_context_by_page_no: Dict[int, Dict[str, Any]],
    valid_words: set,
) -> None:
    normalized_counts = Counter(sentence["normalized_text"] for sentence in sentences_v01)
    for sentence in sentences_v01:
        tokens = tokenize_sentence(sentence["clean_text"])
        sentence_role, include_in_reference, exclude_reason, direction_status, direction_confidence, direction_reason = classify_sentence_role(
            clean_text=sentence["clean_text"],
            normalized_text=sentence["normalized_text"],
            book_title=book_title,
            page_no=sentence["page_no"],
            page_count=page_count,
            sentence_boundary_status=sentence["sentence_boundary_status"],
            word_count=sentence["word_count"],
            tokens=tokens,
            duplicate_count=normalized_counts.get(sentence["normalized_text"], 0),
            page_context=page_context_by_page_no.get(sentence["page_no"], ""),
            page_direction_context=page_direction_context_by_page_no.get(sentence["page_no"], {}),
            valid_words=valid_words,
        )
        sentence["sentence_role"] = sentence_role
        sentence["text_direction_status"] = direction_status
        sentence["directionality_confidence"] = direction_confidence
        sentence["directionality_reason"] = direction_reason
        sentence["include_in_reference"] = include_in_reference
        sentence["exclude_reason"] = exclude_reason
        
        # Enforce strict gatekeeping rules
        is_anomaly = check_reversed_word_anomaly(sentence["clean_text"], valid_words)
        is_abnormal = has_abnormal_reference_text(sentence["clean_text"])
        if (
            sentence["text_direction_status"] != "forward_clean"
            or sentence["directionality_confidence"] < 1.0
            or is_anomaly
            or is_abnormal
        ):
            sentence["include_in_reference"] = False
            sentence["include_in_unique_reference"] = False
            sentence["review_status"] = "pending_review"
            if is_abnormal:
                sentence["sentence_role"] = ABNORMAL_TEXT_LAYER_ROLE
                sentence["exclude_reason"] = ABNORMAL_TEXT_LAYER_EXCLUDE_REASON
                sentence["text_direction_status"] = "not_applicable"
                sentence["directionality_confidence"] = 0.0
                sentence["directionality_reason"] = "not_applicable_non_reference"
        else:
            sentence["review_status"] = (
                "pending_review"
                if sentence["sentence_boundary_status"] in NON_CLEAN_STATUSES or not include_in_reference
                else "not_required"
            )


def mark_as_title_contamination(sentence: Dict[str, Any]) -> None:
    sentence["sentence_role"] = TITLE_CONTAMINATION_ROLE
    sentence["text_direction_status"] = "not_applicable"
    sentence["directionality_confidence"] = 0.0
    sentence["directionality_reason"] = "not_applicable_non_reference"
    sentence["include_in_reference"] = False
    sentence["exclude_reason"] = TITLE_CONTAMINATION_EXCLUDE_REASON
    sentence["review_status"] = "pending_review"
    sentence["reference_text_key"] = ""
    sentence["reference_group_id"] = ""
    sentence["reference_occurrence_index"] = 0
    sentence["reference_occurrence_count"] = 0
    sentence["is_reference_canonical"] = False
    sentence["include_in_unique_reference"] = False
    sentence["duplicate_reference_status"] = "non_reference"
    sentence["duplicate_reason"] = "non_reference"


def apply_front_back_matter_reference_suppression(
    sentences_v01: List[Dict[str, Any]],
    book_title: str,
    page_count: int,
    page_context_by_page_no: Dict[int, str],
) -> None:
    reference_candidates = [sentence for sentence in sentences_v01 if sentence.get("include_in_reference") is True]
    grouped_rows: Dict[str, List[Dict[str, Any]]] = {}
    for sentence in reference_candidates:
        grouped_rows.setdefault(canonicalize_reference_text(sentence["clean_text"]), []).append(sentence)

    for sentence in reference_candidates:
        if sentence.get("include_in_reference") is not True:
            continue
        if is_title_contamination_artifact(
            clean_text=sentence["clean_text"],
            normalized_text=sentence["normalized_text"],
            book_title=book_title,
            page_no=sentence["page_no"],
            page_count=page_count,
            page_context=page_context_by_page_no.get(sentence["page_no"], ""),
            word_count=sentence["word_count"],
            tokens=tokenize_sentence(sentence["clean_text"]),
        ):
            mark_as_title_contamination(sentence)

    for group_rows in grouped_rows.values():
        surviving_rows = [row for row in group_rows if row.get("include_in_reference") is True]
        if len(surviving_rows) < 2:
            continue
        all_front_back = all(is_front_back_matter_page(row["page_no"], page_count) for row in surviving_rows)
        no_body_pages = all(not (3 <= row["page_no"] <= max(page_count - 2, 2)) for row in surviving_rows)
        all_context_noise = all(
            page_has_front_back_matter_context(page_context_by_page_no.get(row["page_no"], ""))
            for row in surviving_rows
        )
        if all_front_back and no_body_pages and all_context_noise:
            for row in surviving_rows:
                mark_as_title_contamination(row)


def initialize_reference_defaults(sentence: Dict[str, Any]) -> None:
    sentence["reference_text_key"] = ""
    sentence["reference_group_id"] = ""
    sentence["reference_occurrence_index"] = 0
    sentence["reference_occurrence_count"] = 0
    sentence["is_reference_canonical"] = False
    sentence["include_in_unique_reference"] = False
    sentence["duplicate_reference_status"] = "non_reference"
    sentence["duplicate_reason"] = "non_reference"


def apply_reference_duplicate_policy(sentences_v01: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped_rows: Dict[str, List[Dict[str, Any]]] = {}
    reference_rows: List[Dict[str, Any]] = []

    for sentence in sentences_v01:
        initialize_reference_defaults(sentence)
        
        # Second safety pass before duplicate grouping:
        # If include_in_reference is true but has_abnormal_reference_text(clean_text), force it back to non-reference.
        if sentence.get("include_in_reference") is True and has_abnormal_reference_text(sentence["clean_text"]):
            sentence["include_in_reference"] = False
            sentence["include_in_unique_reference"] = False
            sentence["review_status"] = "pending_review"
            sentence["sentence_role"] = ABNORMAL_TEXT_LAYER_ROLE
            sentence["exclude_reason"] = ABNORMAL_TEXT_LAYER_EXCLUDE_REASON
            sentence["text_direction_status"] = "not_applicable"
            sentence["directionality_confidence"] = 0.0
            sentence["directionality_reason"] = "not_applicable_non_reference"
            
        if sentence.get("include_in_reference") is not True:
            continue
        if (
            sentence.get("text_direction_status") != "forward_clean"
            or sentence.get("directionality_confidence", 0.0) < 1.0
        ):
            sentence["include_in_reference"] = False
            sentence["include_in_unique_reference"] = False
            sentence["review_status"] = "pending_review"
            sentence["duplicate_reference_status"] = "non_reference"
            sentence["duplicate_reason"] = "non_reference"
            continue
        sentence["reference_text_key"] = canonicalize_reference_text(sentence["clean_text"])
        grouped_rows.setdefault(sentence["reference_text_key"], []).append(sentence)
        reference_rows.append(sentence)

    reference_duplicate_groups: List[Dict[str, Any]] = []
    group_index = 0
    for sentence in reference_rows:
        group_rows = grouped_rows.get(sentence["reference_text_key"], [])
        if not group_rows or group_rows[0]["sentence_id"] != sentence["sentence_id"]:
            continue

        group_index += 1
        reference_group_id = f"{sentence['book_id']}_REFG_{group_index:04d}"
        occurrence_count = len(group_rows)
        distinct_pages = sorted({row["page_no"] for row in group_rows})
        duplicate_reason = "none"
        if occurrence_count > 1:
            duplicate_reason = (
                "booklet_layout_duplicate_candidate"
                if len(distinct_pages) > 1
                else "exact_normalized_text_duplicate"
            )

        for occurrence_index, row in enumerate(group_rows, start=1):
            row["reference_group_id"] = reference_group_id
            row["reference_occurrence_index"] = occurrence_index
            row["reference_occurrence_count"] = occurrence_count
            row["is_reference_canonical"] = occurrence_index == 1
            row["include_in_unique_reference"] = occurrence_index == 1

            if occurrence_count == 1:
                row["duplicate_reference_status"] = "unique_reference"
                row["duplicate_reason"] = "none"
            elif occurrence_index == 1:
                row["duplicate_reference_status"] = "canonical_duplicate_group"
                row["duplicate_reason"] = duplicate_reason
            else:
                row["duplicate_reference_status"] = "duplicate_instance"
                row["duplicate_reason"] = duplicate_reason

        reference_duplicate_groups.append(
            {
                "reference_group_id": reference_group_id,
                "book_id": sentence["book_id"],
                "raz_level": sentence["raz_level"],
                "book_title": sentence["book_title"],
                "reference_text_key": sentence["reference_text_key"],
                "canonical_sentence_id": group_rows[0]["sentence_id"],
                "occurrence_count": occurrence_count,
                "page_span": len(distinct_pages),
                "first_page_no": min(distinct_pages) if distinct_pages else 0,
                "last_page_no": max(distinct_pages) if distinct_pages else 0,
                "sentence_ids": "|".join(row["sentence_id"] for row in group_rows),
                "duplicate_reason": duplicate_reason,
                "include_in_unique_reference": True,
            }
        )

    return reference_duplicate_groups


def build_qc_rows(sentences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    qc_rows: List[Dict[str, Any]] = []
    for index, sentence in enumerate(sentences, start=1):
        status = sentence["sentence_boundary_status"]
        if status not in NON_CLEAN_STATUSES and sentence.get("include_in_reference", True):
            continue
        issue_type = status if status != "clean" else sentence.get("exclude_reason", "unknown_noise")
        qc_rows.append(
            {
                "qc_id": f"QC_{index:06d}",
                "issue_type": issue_type,
                "qc_action": "manual_review_required",
                "reviewer": "",
                "review_status": "pending_review",
                "qc_notes": sentence.get("notes", ""),
                **sentence,
            }
        )
    return qc_rows


def run_final_reference_safety_audit(sentences_v01: List[Dict[str, Any]]) -> Tuple[str, int]:
    bad_reference_count = 0
    for sentence in sentences_v01:
        if sentence.get("include_in_reference") is True:
            is_bad = False
            if sentence.get("sentence_role") != "body_text":
                is_bad = True
            if sentence.get("sentence_boundary_status") != "clean":
                is_bad = True
            if sentence.get("exclude_reason") != "none":
                is_bad = True
            if sentence.get("text_direction_status") != "forward_clean":
                is_bad = True
            if sentence.get("directionality_confidence", 0.0) < 1.0:
                is_bad = True
            if has_abnormal_reference_text(sentence.get("clean_text", "")):
                is_bad = True
                
            if is_bad:
                bad_reference_count += 1
                
    status = "FAIL" if bad_reference_count > 0 else "PASS"
    return status, bad_reference_count


def extract_pages_with_pdfplumber(pdf_path: Path, pdfplumber_module: Any) -> List[Tuple[int, str, str]]:
    pages: List[Tuple[int, str, str]] = []
    with pdfplumber_module.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            try:
                raw_text = page.extract_text() or ""
                pages.append((page_no, raw_text, ""))
            except Exception as exc:  # pragma: no cover
                pages.append((page_no, "", f"{exc.__class__.__name__}: {exc}"))
    return pages


def extract_pages_with_pypdf(pdf_path: Path, pypdf_module: Any) -> List[Tuple[int, str, str]]:
    pages: List[Tuple[int, str, str]] = []
    reader = pypdf_module.PdfReader(str(pdf_path))
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
            pages.append((page_no, raw_text, ""))
        except Exception as exc:  # pragma: no cover
            pages.append((page_no, "", f"{exc.__class__.__name__}: {exc}"))
    return pages


def extract_pdf_pages(pdf_path: Path, extractor_name: str, extractor_module: Any) -> List[Tuple[int, str, str]]:
    if extractor_name == "pdfplumber_v0.1":
        return extract_pages_with_pdfplumber(pdf_path, extractor_module)
    if extractor_name == "pypdf_v0.1":
        return extract_pages_with_pypdf(pdf_path, extractor_module)
    raise ExtractionError(f"Unsupported extractor configured: {extractor_name}")


def process_book(
    row: pd.Series,
    pdf_dir: Path,
    extractor_name: str,
    extractor_module: Any,
    logger: logging.Logger,
    valid_words: set,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], bool, List[Dict[str, Any]]]:
    book_id = sanitize_manifest_value(row["book_id"])
    raz_level = sanitize_manifest_value(row["raz_level"])
    book_title = sanitize_manifest_value(row["book_title"])
    pdf_file = sanitize_manifest_value(row["pdf_file"])
    pdf_path = pdf_dir / pdf_file

    logger.info("Processing book_id=%s pdf=%s", book_id, pdf_file)

    if not pdf_file:
        return [], [], build_failed_summary(book_id, book_title, raz_level, "failed"), False, []
    if not pdf_path.exists():
        logger.error("PDF not found for %s: %s", book_id, pdf_path)
        return [], [], build_failed_summary(book_id, book_title, raz_level, "failed"), False, []

    try:
        extracted_pages = extract_pdf_pages(pdf_path, extractor_name, extractor_module)
    except Exception:
        logger.exception("Failed to extract PDF %s", pdf_path)
        return [], [], build_failed_summary(book_id, book_title, raz_level, "failed"), False, []

    pages_raw: List[Dict[str, Any]] = []
    sentences_v01: List[Dict[str, Any]] = []
    page_context_by_page_no: Dict[int, str] = {}
    page_direction_context_by_page_no: Dict[int, Dict[str, Any]] = {}
    sentence_order_in_book = 0
    pdf_valid_char_count = 0
    extraction_error_count = 0

    for page_no, raw_text, extraction_error in extracted_pages:
        clean_text = clean_page_text(raw_text)
        valid_char_count = count_valid_characters(clean_text)
        pdf_valid_char_count += valid_char_count

        page_text_status = "valid_text"
        notes = ""
        extraction_confidence = 1.0
        needs_manual_review = False

        if extraction_error:
            page_text_status = "extraction_error"
            notes = extraction_error
            extraction_confidence = 0.0
            needs_manual_review = True
            extraction_error_count += 1
        elif valid_char_count < 5:
            page_text_status = "empty_or_image"
            extraction_confidence = 0.2 if clean_text else 0.0
            needs_manual_review = True

        page_record = {
            "page_id": f"{book_id}_P{page_no:03d}",
            "book_id": book_id,
            "raz_level": raz_level,
            "book_title": book_title,
            "pdf_file": pdf_file,
            "page_no": page_no,
            "raw_page_text": raw_text,
            "clean_page_text": clean_text,
            "text_source": "pdf_text_layer",
            "extractor": extractor_name,
            "page_text_status": page_text_status,
            "extraction_confidence": extraction_confidence,
            "needs_manual_review": needs_manual_review,
            "notes": notes,
        }
        pages_raw.append(page_record)
        page_context_by_page_no[page_no] = clean_text.lower()
        page_direction_context_by_page_no[page_no] = scan_page_line_directions(
            clean_page_text=clean_text,
            book_title=book_title,
            page_no=page_no,
            page_count=len(extracted_pages),
        )

        if page_text_status == "extraction_error" or not clean_text:
            continue

        sentence_segments = split_sentences(clean_text)
        for sentence_order_on_page, segment in enumerate(sentence_segments, start=1):
            sentence_order_in_book += 1
            clean_sentence = normalize_sentence_text(segment)
            tokens = tokenize_sentence(clean_sentence)
            boundary_status, punctuation_status = determine_sentence_status(clean_sentence, tokens)

            sentence_record = {
                "sentence_id": f"{book_id}_P{page_no:03d}_S{sentence_order_on_page:03d}",
                "book_id": book_id,
                "raz_level": raz_level,
                "book_title": book_title,
                "pdf_file": pdf_file,
                "page_no": page_no,
                "sentence_order_in_book": sentence_order_in_book,
                "sentence_order_on_page": sentence_order_on_page,
                "raw_text": segment,
                "clean_text": clean_sentence,
                "normalized_text": clean_sentence.lower(),
                "word_count": len(tokens),
                "unique_word_count": len({token.lower() for token in tokens}),
                "char_count": len(clean_sentence),
                "text_source": "pdf_text_layer",
                "extractor": extractor_name,
                "extraction_confidence": page_record["extraction_confidence"],
                "sentence_boundary_status": boundary_status,
                "sentence_role": "unknown",
                "text_direction_status": "not_applicable",
                "directionality_confidence": 0.0,
                "directionality_reason": "not_applicable_non_reference",
                "include_in_reference": False,
                "reference_text_key": "",
                "reference_group_id": "",
                "reference_occurrence_index": 0,
                "reference_occurrence_count": 0,
                "is_reference_canonical": False,
                "include_in_unique_reference": False,
                "duplicate_reference_status": "non_reference",
                "duplicate_reason": "non_reference",
                "exclude_reason": "unknown_noise",
                "punctuation_status": punctuation_status,
                "review_status": "pending_review" if boundary_status in NON_CLEAN_STATUSES else "not_required",
                "copyright_flag": "reference_only",
                "notes": page_record["notes"],
            }
            sentences_v01.append(sentence_record)

    apply_sentence_filters(
        sentences_v01=sentences_v01,
        book_title=book_title,
        page_count=len(pages_raw),
        page_context_by_page_no=page_context_by_page_no,
        page_direction_context_by_page_no=page_direction_context_by_page_no,
        valid_words=valid_words,
    )
    apply_front_back_matter_reference_suppression(
        sentences_v01=sentences_v01,
        book_title=book_title,
        page_count=len(pages_raw),
        page_context_by_page_no=page_context_by_page_no,
    )
    reference_duplicate_groups = apply_reference_duplicate_policy(sentences_v01)

    summary = build_book_summary(
        book_id=book_id,
        book_title=book_title,
        raz_level=raz_level,
        pages_raw=pages_raw,
        sentences_v01=sentences_v01,
        reference_duplicate_groups=reference_duplicate_groups,
        pdf_valid_char_count=pdf_valid_char_count,
        extraction_error_count=extraction_error_count,
    )
    return pages_raw, sentences_v01, summary, True, reference_duplicate_groups


def build_failed_summary(book_id: str, book_title: str, raz_level: str, extraction_status: str) -> Dict[str, Any]:
    return {
        "book_id": book_id,
        "book_title": book_title,
        "raz_level": raz_level,
        "sentence_count": 0,
        "word_count_total": 0,
        "avg_sentence_length": 0.0,
        "min_sentence_length": 0,
        "max_sentence_length": 0,
        "unique_word_count": 0,
        "page_count": 0,
        "valid_page_count": 0,
        "needs_review_sentence_count": 0,
        "reference_sentence_count": 0,
        "excluded_sentence_count": 0,
        "unique_reference_sentence_count": 0,
        "duplicate_reference_sentence_count": 0,
        "reference_duplicate_group_count": 0,
        "max_reference_occurrence_count": 0,
        "extraction_status": extraction_status,
        "qa_status": "pending",
    }


def build_book_summary(
    book_id: str,
    book_title: str,
    raz_level: str,
    pages_raw: List[Dict[str, Any]],
    sentences_v01: List[Dict[str, Any]],
    reference_duplicate_groups: List[Dict[str, Any]],
    pdf_valid_char_count: int,
    extraction_error_count: int,
) -> Dict[str, Any]:
    word_counts = [sentence["word_count"] for sentence in sentences_v01]
    all_tokens = [
        token.lower()
        for sentence in sentences_v01
        for token in tokenize_sentence(sentence["clean_text"])
    ]
    needs_review_count = sum(
        1 for sentence in sentences_v01 if sentence["sentence_boundary_status"] in NON_CLEAN_STATUSES
    )
    reference_sentence_count = sum(1 for sentence in sentences_v01 if sentence.get("include_in_reference") is True)
    excluded_sentence_count = sum(1 for sentence in sentences_v01 if sentence.get("include_in_reference") is False)
    unique_reference_sentence_count = sum(
        1 for sentence in sentences_v01 if sentence.get("include_in_unique_reference") is True
    )
    duplicate_reference_sentence_count = sum(
        1
        for sentence in sentences_v01
        if sentence.get("include_in_reference") is True and sentence.get("include_in_unique_reference") is False
    )
    reference_duplicate_group_count = sum(
        1 for group in reference_duplicate_groups if group["occurrence_count"] > 1
    )
    max_reference_occurrence_count = max(
        (group["occurrence_count"] for group in reference_duplicate_groups),
        default=0,
    )
    valid_page_count = sum(1 for page in pages_raw if page["page_text_status"] == "valid_text")

    if pdf_valid_char_count < 100:
        extraction_status = "image_pdf_needs_ocr"
    elif extraction_error_count and valid_page_count == 0:
        extraction_status = "failed"
    elif extraction_error_count:
        extraction_status = "partial"
    elif sentences_v01 and needs_review_count / len(sentences_v01) > 0.25:
        extraction_status = "needs_review"
    else:
        extraction_status = "done"

    return {
        "book_id": book_id,
        "book_title": book_title,
        "raz_level": raz_level,
        "sentence_count": len(sentences_v01),
        "word_count_total": sum(word_counts),
        "avg_sentence_length": round(sum(word_counts) / len(word_counts), 4) if word_counts else 0.0,
        "min_sentence_length": min(word_counts) if word_counts else 0,
        "max_sentence_length": max(word_counts) if word_counts else 0,
        "unique_word_count": len(set(all_tokens)),
        "page_count": len(pages_raw),
        "valid_page_count": valid_page_count,
        "needs_review_sentence_count": needs_review_count,
        "reference_sentence_count": reference_sentence_count,
        "excluded_sentence_count": excluded_sentence_count,
        "unique_reference_sentence_count": unique_reference_sentence_count,
        "duplicate_reference_sentence_count": duplicate_reference_sentence_count,
        "reference_duplicate_group_count": reference_duplicate_group_count,
        "max_reference_occurrence_count": max_reference_occurrence_count,
        "extraction_status": extraction_status,
        "qa_status": "pending",
    }


def build_readme_rows(run_id: str, created_at: str) -> List[Dict[str, str]]:
    return [
        {"field": "run_id", "value": run_id},
        {"field": "created_at", "value": created_at},
        {"field": "source_corpus", "value": "RAZ"},
        {"field": "source_role", "value": "external_reference_only"},
        {"field": "direct_use_allowed", "value": "false"},
        {"field": "copyright_flag", "value": "reference_only"},
        {"field": "usage_note_1", "value": "This is RAZ A Reference Corpus output."},
        {"field": "usage_note_2", "value": "Data is external_reference_only."},
        {"field": "usage_note_3", "value": "Data is not for direct reuse."},
        {
            "field": "usage_note_4",
            "value": "This workbook is for sentence length calibration, repetition pattern analysis, page-level density analysis, and system benchmark comparison only.",
        },
        {"field": "usage_note_5", "value": "total_sentences includes all extracted sentence-like segments."},
        {"field": "usage_note_6", "value": "reference_sentence_count includes all body-text occurrences."},
        {"field": "usage_note_7", "value": "unique_reference_sentence_count includes only canonical reference sentences."},
        {"field": "usage_note_8", "value": "Excluded rows are preserved for audit but must not be used for sentence length calibration or pattern analysis."},
        {"field": "usage_note_9", "value": "duplicate_reference_sentence_count counts repeated body-text rows after the canonical occurrence."},
        {"field": "usage_note_10", "value": "Use include_in_unique_reference = true for sentence length calibration."},
        {"field": "usage_note_11", "value": "Use include_in_reference = true plus duplicate groups for repetition analysis."},
        {"field": "usage_note_12", "value": "Duplicate rows are not automatically excluded because early-reader repetition may be pedagogically meaningful."},
        {"field": "usage_note_13", "value": "Front/back matter title-contamination rows are preserved for audit but excluded from reference use."},
        {"field": "usage_note_14", "value": "Directionally unsafe rows are preserved for audit and QC but never allowed into reference grouping."},
    ]


def build_decision_rules_rows() -> List[Dict[str, str]]:
    return [
        {"rule": "pdf_character_threshold", "value": "< 100 => image_pdf_needs_ocr"},
        {"rule": "page_character_threshold", "value": "< 5 => empty_or_image"},
        {"rule": "sentence_splitting", "value": "Split only on ., ?, ! and keep terminal punctuation"},
        {"rule": "newline_handling", "value": "Treat line breaks as spaces, not sentence boundaries"},
        {"rule": "sentence_boundary_status_logic", "value": "1 word=too_short; 2-8=clean; 9-12=medium_review; >12=too_long; malformed=non_sentence; no terminal punctuation=missing_punctuation"},
        {"rule": "url_filter", "value": "Rows containing www, readinga-z, .com, or broken URL fragments are excluded"},
        {"rule": "mirrored_text_filter", "value": "Rows containing mirrored or reversed booklet text are excluded as mirrored_text_artifact"},
        {"rule": "front_back_matter_title_filter", "value": "Short title-like rows on strong front/back matter pages are excluded as title_contamination_artifact"},
        {"rule": "photo_credit_filter", "value": "Rows containing photo-credit markers are excluded"},
        {"rule": "copyright_filter", "value": "Rows containing copyright/publisher markers are excluded"},
        {"rule": "benchmark_level_filter", "value": "Rows containing benchmark/level labels are excluded"},
        {"rule": "layout_artifact_filter", "value": "Rows with repeated page-number/layout markers are excluded"},
        {"rule": "directionality_filter", "value": "Reference rows must have text_direction_status = forward_clean; reversed, mixed, interleaved, mirrored, and unknown-direction rows are excluded"},
        {"rule": "page_line_direction_scan", "value": "Each cleaned page is scanned for forward, reversed, mixed, noise, and unknown line evidence before sentence-level inclusion"},
        {"rule": "include_in_reference", "value": "Only likely body-text rows with include_in_reference = true are reference-usable"},
        {"rule": "reference_text_key", "value": "Lowercase, trim, collapse spaces, and strip sentence-final punctuation only"},
        {"rule": "canonical_occurrence", "value": "First occurrence in each reference_text_key group is canonical"},
        {"rule": "duplicate_group_assignment", "value": "reference_group_id is assigned by first occurrence order among reference rows"},
        {"rule": "include_in_unique_reference", "value": "True only for canonical reference rows"},
        {"rule": "duplicate_reference_status", "value": "non_reference, unique_reference, canonical_duplicate_group, duplicate_instance"},
        {"rule": "duplicate_reason", "value": "none, exact_normalized_text_duplicate, booklet_layout_duplicate_candidate, non_reference"},
        {"rule": "downstream_reference_usage", "value": "Use unique reference rows for calibration and all reference rows for repetition analysis"},
        {"rule": "front_back_only_group_suppression", "value": "Reference groups found only on front/back matter pages with strong page-noise context are removed from reference use"},
        {"rule": "sentence_qc_inclusion", "value": "Rows enter sentence_qc if sentence_boundary_status != clean or include_in_reference = false"},
        {"rule": "abnormal_text_layer_filter", "value": "Rows containing replacement chars, bullets, backslashes, angle brackets, split tokens, digit-letter confusion, or symbol-only rows are excluded"},
        {"rule": "a_level_body_pattern_filter", "value": "Reference rows must match a-level body pattern. Recoverable clean body page sentences can be rescued if matching matches_a_level_body_pattern"},
        {"rule": "ocr", "value": "disabled"},
        {"rule": "audio_transcription", "value": "disabled"},
        {"rule": "direct_content_reuse", "value": "disabled"},
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)


def dataframe_with_columns(rows: List[Dict[str, Any]], columns: List[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)


def write_excel_workbook(
    output_path: Path,
    readme_rows: List[Dict[str, Any]],
    books_df: pd.DataFrame,
    pages_raw: List[Dict[str, Any]],
    sentences_v01: List[Dict[str, Any]],
    sentence_qc: List[Dict[str, Any]],
    reference_duplicate_groups: List[Dict[str, Any]],
    book_summary: List[Dict[str, Any]],
    extraction_report: Dict[str, Any],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        dataframe_with_columns(readme_rows, ["field", "value"]).to_excel(writer, sheet_name="README", index=False)
        books_df.to_excel(writer, sheet_name="books", index=False)
        dataframe_with_columns(pages_raw, PAGES_RAW_COLUMNS).to_excel(writer, sheet_name="pages_raw", index=False)
        dataframe_with_columns(sentences_v01, SENTENCE_COLUMNS).to_excel(writer, sheet_name="sentences_v01", index=False)
        dataframe_with_columns(sentence_qc, SENTENCE_QC_COLUMNS).to_excel(writer, sheet_name="sentence_qc", index=False)
        dataframe_with_columns(reference_duplicate_groups, REFERENCE_DUPLICATE_GROUP_COLUMNS).to_excel(
            writer,
            sheet_name="reference_duplicate_groups",
            index=False,
        )
        dataframe_with_columns(book_summary, BOOK_SUMMARY_COLUMNS).to_excel(writer, sheet_name="book_summary", index=False)
        dataframe_with_columns([extraction_report], EXTRACTION_REPORT_COLUMNS).to_excel(
            writer, sheet_name="extraction_report", index=False
        )
        dataframe_with_columns(build_decision_rules_rows(), ["rule", "value"]).to_excel(
            writer, sheet_name="decision_rules", index=False
        )


def build_extraction_report(
    run_id: str,
    created_at: str,
    books_df: pd.DataFrame,
    pages_raw: List[Dict[str, Any]],
    sentences_v01: List[Dict[str, Any]],
    reference_duplicate_groups: List[Dict[str, Any]],
    book_summary: List[Dict[str, Any]],
    output_excel: Path,
) -> Dict[str, Any]:
    processed_pdf_count = sum(1 for item in book_summary if item["page_count"] > 0)
    failed_pdf_count = sum(1 for item in book_summary if item["extraction_status"] == "failed")
    image_pdf_count = sum(1 for item in book_summary if item["extraction_status"] == "image_pdf_needs_ocr")
    needs_review_sentence_count = sum(
        1 for sentence in sentences_v01 if sentence["sentence_boundary_status"] in NON_CLEAN_STATUSES
    )
    reference_sentence_count = sum(1 for sentence in sentences_v01 if sentence.get("include_in_reference") is True)
    excluded_sentence_count = sum(1 for sentence in sentences_v01 if sentence.get("include_in_reference") is False)
    unique_reference_sentence_count = sum(
        1 for sentence in sentences_v01 if sentence.get("include_in_unique_reference") is True
    )
    duplicate_reference_sentence_count = sum(
        1
        for sentence in sentences_v01
        if sentence.get("include_in_reference") is True and sentence.get("include_in_unique_reference") is False
    )
    reference_duplicate_group_count = sum(
        1 for group in reference_duplicate_groups if group["occurrence_count"] > 1
    )
    max_reference_occurrence_count = max(
        (group["occurrence_count"] for group in reference_duplicate_groups),
        default=0,
    )
    total_words = sum(sentence["word_count"] for sentence in sentences_v01)

    if failed_pdf_count == len(book_summary) and len(book_summary) > 0:
        status = "failed"
    elif failed_pdf_count > 0 or image_pdf_count > 0 or needs_review_sentence_count > 0:
        status = "completed_with_warnings"
    else:
        status = "completed"

    safety_status, bad_ref_count = run_final_reference_safety_audit(sentences_v01)
    recoverable_count = sum(1 for s in sentences_v01 if s.get("directionality_reason") == "rescued_a_level_body_pattern")
    abnormal_count = sum(1 for s in sentences_v01 if s.get("sentence_role") == "text_layer_artifact")

    return {
        "run_id": run_id,
        "created_at": created_at,
        "input_pdf_count": len(books_df),
        "processed_pdf_count": processed_pdf_count,
        "failed_pdf_count": failed_pdf_count,
        "total_books": len(books_df),
        "total_pages": len(pages_raw),
        "total_sentences": len(sentences_v01),
        "reference_sentence_count": reference_sentence_count,
        "excluded_sentence_count": excluded_sentence_count,
        "unique_reference_sentence_count": unique_reference_sentence_count,
        "duplicate_reference_sentence_count": duplicate_reference_sentence_count,
        "reference_duplicate_group_count": reference_duplicate_group_count,
        "max_reference_occurrence_count": max_reference_occurrence_count,
        "avg_sentences_per_book": round(len(sentences_v01) / len(books_df), 4) if len(books_df) else 0.0,
        "avg_words_per_sentence": round(total_words / len(sentences_v01), 4) if sentences_v01 else 0.0,
        "image_pdf_count": image_pdf_count,
        "needs_review_sentence_count": needs_review_sentence_count,
        "output_excel": str(output_excel),
        "status": status,
        "reference_safety_status": safety_status,
        "bad_reference_count": bad_ref_count,
        "recoverable_unknown_candidate_count": recoverable_count,
        "abnormal_text_layer_artifact_count": abnormal_count,
    }


def main() -> int:
    base_dir = get_base_dir()
    manifest_path = base_dir / MANIFEST_RELATIVE_PATH
    pdf_dir = base_dir / PDF_DIR_RELATIVE_PATH
    output_excel_path = base_dir / OUTPUT_EXCEL_RELATIVE_PATH
    output_json_dir = base_dir / OUTPUT_JSON_DIR_RELATIVE_PATH
    log_path = base_dir / OUTPUT_LOG_RELATIVE_PATH

    logger = build_logger(log_path)
    run_id = run_id_from_now()
    created_at = now_utc_iso()

    try:
        logger.info("Starting RAZ A reference sentence builder")
        books_df = load_manifest(manifest_path)
        valid_words = load_valid_words(logger)

        pages_raw: List[Dict[str, Any]] = []
        sentences_v01: List[Dict[str, Any]] = []
        reference_duplicate_groups: List[Dict[str, Any]] = []
        book_summary: List[Dict[str, Any]] = []

        if not books_df.empty:
            extractor_name, extractor_module = resolve_pdf_extractor()
            for _, row in books_df.iterrows():
                page_rows, sentence_rows, summary_row, _, duplicate_group_rows = process_book(
                    row=row,
                    pdf_dir=pdf_dir,
                    extractor_name=extractor_name,
                    extractor_module=extractor_module,
                    logger=logger,
                    valid_words=valid_words,
                )
                pages_raw.extend(page_rows)
                sentences_v01.extend(sentence_rows)
                reference_duplicate_groups.extend(duplicate_group_rows)
                book_summary.append(summary_row)

        sentence_qc = build_qc_rows(sentences_v01)
        
        # Run final reference safety audit
        safety_status, bad_ref_count = run_final_reference_safety_audit(sentences_v01)
        if safety_status == "FAIL":
            raise ExtractionError(f"Final reference safety audit FAILED: found {bad_ref_count} bad reference rows!")

        extraction_report = build_extraction_report(
            run_id=run_id,
            created_at=created_at,
            books_df=books_df,
            pages_raw=pages_raw,
            sentences_v01=sentences_v01,
            reference_duplicate_groups=reference_duplicate_groups,
            book_summary=book_summary,
            output_excel=output_excel_path,
        )

        write_json(output_json_dir / "pages_raw.json", pages_raw)
        write_json(output_json_dir / "sentences_v01.json", sentences_v01)
        write_json(output_json_dir / "reference_duplicate_groups.json", reference_duplicate_groups)
        write_json(output_json_dir / "extraction_report.json", extraction_report)
        write_excel_workbook(
            output_path=output_excel_path,
            readme_rows=build_readme_rows(run_id, created_at),
            books_df=books_df,
            pages_raw=pages_raw,
            sentences_v01=sentences_v01,
            sentence_qc=sentence_qc,
            reference_duplicate_groups=reference_duplicate_groups,
            book_summary=book_summary,
            extraction_report=extraction_report,
        )

        logger.info(
            "Completed run_id=%s books=%s pages=%s sentences=%s status=%s",
            run_id,
            len(books_df),
            len(pages_raw),
            len(sentences_v01),
            extraction_report["status"],
        )
        return 0
    except ExtractionError as exc:
        logger.error(str(exc))
        return 1
    except Exception as exc:  # pragma: no cover
        logger.exception("Unhandled builder failure: %s", exc)
        return 1
    finally:
        close_logger(logger)


if __name__ == "__main__":
    raise SystemExit(main())
