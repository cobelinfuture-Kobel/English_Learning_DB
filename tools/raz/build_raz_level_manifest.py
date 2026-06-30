import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


MANIFEST_SHEET_NAME = "books_manifest"
REQUIRED_COLUMNS = [
    "book_id",
    "raz_level",
    "book_no",
    "book_title",
    "pdf_file",
    "audio_file",
    "source_note",
]
OPTIONAL_COLUMNS = [
    "pdf_source_status",
    "preprocess_method",
    "file_hash",
    "page_count",
    "extractable_text_chars",
    "manifest_notes",
]
TITLE_SUFFIX_PATTERNS = [
    r"_Password_Removed",
    r"Password Removed",
    r"_text_layer",
    r"text layer",
    r"_TEXTLAYER",
    r"OCR",
]


class ManifestBuildError(RuntimeError):
    pass


def get_base_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_run_id() -> str:
    return datetime.now(timezone.utc).strftime("RUN_%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a RAZ level manifest from one PDF folder."
    )
    parser.add_argument("--level", default="A", help="RAZ level, default: A")
    parser.add_argument("--pdf-dir", help="PDF directory, default: input/pdf/<lowercase level>")
    parser.add_argument(
        "--output",
        help="Excel manifest output path, default: input/manifest/raz_<LEVEL>_books_manifest.xlsx",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing manifest output if it already exists.",
    )
    return parser.parse_args()


def normalize_level(value: str) -> str:
    level = str(value or "").strip().upper()
    if not level:
        raise ManifestBuildError("Level must not be empty.")
    return level


def resolve_paths(args: argparse.Namespace, base_dir: Path) -> Tuple[str, Path, Path, Path]:
    level = normalize_level(args.level)
    pdf_dir = base_dir / args.pdf_dir if args.pdf_dir else base_dir / "input" / "pdf" / level.lower()
    output_path = (
        base_dir / args.output
        if args.output
        else base_dir / "input" / "manifest" / f"raz_{level}_books_manifest.xlsx"
    )
    report_path = base_dir / "output" / "manifest_reports" / f"raz_{level}_manifest_report.json"
    return level, pdf_dir.resolve(), output_path.resolve(), report_path.resolve()


def ensure_safe_output(output_path: Path, overwrite: bool) -> None:
    if output_path.exists() and not overwrite:
        raise ManifestBuildError(
            f"Output already exists: {output_path}. Re-run with --overwrite to replace it."
        )


def natural_sort_key(value: str) -> List[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def list_pdf_files(pdf_dir: Path) -> List[Path]:
    if not pdf_dir.exists():
        raise ManifestBuildError(f"PDF directory does not exist: {pdf_dir}")
    if not pdf_dir.is_dir():
        raise ManifestBuildError(f"PDF directory is not a directory: {pdf_dir}")

    pdf_files = [path for path in pdf_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"]
    pdf_files.sort(key=lambda path: natural_sort_key(path.name))
    return pdf_files


def extract_leading_book_no(filename_stem: str) -> Optional[int]:
    match = re.match(r"^(?:[A-Za-z])?(\d+)(?:[_\s-]|$)", filename_stem)
    if not match:
        return None
    return int(match.group(1))


def infer_book_title(filename: str) -> str:
    title = Path(filename).stem
    title = re.sub(r"^(?:[A-Za-z])?\d+(?:[_\s-]+)", "", title)
    for pattern in TITLE_SUFFIX_PATTERNS:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)
    title = title.replace("_", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title


def compute_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_extractable_text(pdf_path: Path, extractor_name: Optional[str]) -> Tuple[str, int, int]:
    if extractor_name is None:
        return "unchecked_no_extractor", 0, 0

    try:
        if extractor_name == "pypdf":
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(pdf_path))
            page_count = len(reader.pages)
            extractable_text_chars = 0
            for page in reader.pages:
                page_text = page.extract_text() or ""
                extractable_text_chars += sum(1 for char in page_text if not char.isspace())
        elif extractor_name == "pdfplumber":
            import pdfplumber  # type: ignore

            extractable_text_chars = 0
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    extractable_text_chars += sum(1 for char in page_text if not char.isspace())
        else:
            raise ManifestBuildError(f"Unsupported extractor: {extractor_name}")
    except Exception:
        return "OPEN_ERROR", 0, 0

    if extractable_text_chars >= 100:
        status = "PASS_TEXT_LAYER"
    elif extractable_text_chars >= 1:
        status = "PARTIAL_TEXT_LAYER"
    elif page_count > 0:
        status = "IMAGE_ONLY_PDF_NEEDS_OCR"
    else:
        status = "OPEN_ERROR"

    return status, page_count, extractable_text_chars


def resolve_extractor_name() -> Optional[str]:
    try:
        import pypdf  # type: ignore  # noqa: F401

        return "pypdf"
    except ModuleNotFoundError:
        pass

    try:
        import pdfplumber  # type: ignore  # noqa: F401

        return "pdfplumber"
    except ModuleNotFoundError:
        pass

    return None


def to_forward_slash_path(path: Path) -> str:
    return path.as_posix()


def build_pdf_file_value(pdf_path: Path, input_pdf_root: Path, pdf_dir: Path) -> str:
    try:
        relative = pdf_path.relative_to(input_pdf_root)
    except ValueError:
        relative = pdf_path.relative_to(pdf_dir)
    return to_forward_slash_path(relative)


def build_manifest_rows(level: str, pdf_dir: Path, pdf_files: List[Path]) -> Tuple[List[Dict[str, Any]], Counter]:
    input_pdf_root = (get_base_dir() / "input" / "pdf").resolve()
    extractor_name = resolve_extractor_name()
    rows: List[Dict[str, Any]] = []
    status_counts: Counter = Counter()

    for sorted_index, pdf_path in enumerate(pdf_files, start=1):
        filename_stem = pdf_path.stem
        explicit_book_no = extract_leading_book_no(filename_stem)
        book_no = explicit_book_no if explicit_book_no is not None else sorted_index
        manifest_notes = ""
        if explicit_book_no is None:
            manifest_notes = "book_no_inferred_from_sort_order"

        pdf_source_status, page_count, extractable_text_chars = count_extractable_text(
            pdf_path=pdf_path,
            extractor_name=extractor_name,
        )
        status_counts[pdf_source_status] += 1

        row = {
            "book_id": f"RAZ_{level}_{book_no:03d}",
            "raz_level": level,
            "book_no": book_no,
            "book_title": infer_book_title(pdf_path.name),
            "pdf_file": build_pdf_file_value(pdf_path=pdf_path, input_pdf_root=input_pdf_root, pdf_dir=pdf_dir),
            "audio_file": "",
            "source_note": "reference_only",
            "pdf_source_status": pdf_source_status,
            "preprocess_method": "none",
            "file_hash": compute_sha256(pdf_path),
            "page_count": page_count,
            "extractable_text_chars": extractable_text_chars,
            "manifest_notes": manifest_notes,
        }
        rows.append(row)

    return rows, status_counts


def write_excel(output_path: Path, rows: List[Dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    df = pd.DataFrame(rows, columns=columns)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=MANIFEST_SHEET_NAME, index=False)


def write_json_report(
    report_path: Path,
    run_id: str,
    created_at: str,
    level: str,
    pdf_dir: Path,
    output_manifest: Path,
    rows: List[Dict[str, Any]],
    status_counts: Counter,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "created_at": created_at,
        "level": level,
        "pdf_dir": str(pdf_dir),
        "output_manifest": str(output_manifest),
        "total_pdf_count": len(rows),
        "status_counts": dict(status_counts),
        "rows": rows,
    }
    with report_path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)


def print_summary(
    level: str,
    pdf_dir: Path,
    output_path: Path,
    total_pdf_count: int,
    status_counts: Counter,
) -> None:
    print(f"level: {level}")
    print(f"pdf_dir: {pdf_dir}")
    print(f"output_path: {output_path}")
    print(f"total_pdf_count: {total_pdf_count}")
    print(f"PASS_TEXT_LAYER: {status_counts.get('PASS_TEXT_LAYER', 0)}")
    print(f"PARTIAL_TEXT_LAYER: {status_counts.get('PARTIAL_TEXT_LAYER', 0)}")
    print(f"IMAGE_ONLY_PDF_NEEDS_OCR: {status_counts.get('IMAGE_ONLY_PDF_NEEDS_OCR', 0)}")
    print(f"OPEN_ERROR: {status_counts.get('OPEN_ERROR', 0)}")


def main() -> int:
    try:
        args = parse_args()
        base_dir = get_base_dir()
        level, pdf_dir, output_path, report_path = resolve_paths(args=args, base_dir=base_dir)
        ensure_safe_output(output_path=output_path, overwrite=args.overwrite)

        pdf_files = list_pdf_files(pdf_dir)
        rows, status_counts = build_manifest_rows(level=level, pdf_dir=pdf_dir, pdf_files=pdf_files)

        run_id = build_run_id()
        created_at = now_utc_iso()
        write_excel(output_path=output_path, rows=rows)
        write_json_report(
            report_path=report_path,
            run_id=run_id,
            created_at=created_at,
            level=level,
            pdf_dir=pdf_dir,
            output_manifest=output_path,
            rows=rows,
            status_counts=status_counts,
        )
        print_summary(
            level=level,
            pdf_dir=pdf_dir,
            output_path=output_path,
            total_pdf_count=len(rows),
            status_counts=status_counts,
        )
        return 0
    except ManifestBuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"UNHANDLED_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
