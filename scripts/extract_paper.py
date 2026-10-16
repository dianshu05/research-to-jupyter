#!/usr/bin/env python3
"""
Local PDF text, layout, and equation extractor.

Tries, in order:
1. Docling: local layout/OCR; formula enrichment when supported.
2. PyMuPDF4LLM: Markdown extraction.
3. PyMuPDF: text extraction, with optional Tesseract OCR for image-only pages.
4. pypdf: final text-only fallback.

Warnings go to stderr; extracted content goes to stdout so the Tauri app
can capture it safely.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any


def configure_stdio() -> None:
    """Use UTF-8 for captured output, including on Windows."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _to_text(value: Any) -> str:
    """Convert common extractor return types to text."""
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        text = value.get("text") or value.get("markdown")
        return text if isinstance(text, str) else ""

    if isinstance(value, (list, tuple)):
        pieces: list[str] = []
        for item in value:
            text = _to_text(item)
            if text.strip():
                pieces.append(text)
        return "\n\n".join(pieces)

    return ""


def extract_with_docling(pdf_path: Path) -> str:
    """Extract with Docling, including OCR and formula enrichment if available."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = True
    options.do_table_structure = True

    # This option is not present in every Docling version.
    if hasattr(options, "do_formula_enrichment"):
        options.do_formula_enrichment = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options)
        }
    )

    result = converter.convert(str(pdf_path))
    document = getattr(result, "document", None)
    if document is None:
        raise RuntimeError("Docling did not return a document")

    for method_name in ("export_to_markdown", "export_to_text"):
        exporter = getattr(document, method_name, None)
        if callable(exporter):
            text = _to_text(exporter())
            if text.strip():
                return text

    raise RuntimeError("Docling returned no extractable text")


def extract_with_pymupdf4llm(pdf_path: Path) -> str:
    """Extract PDF content as Markdown using PyMuPDF4LLM."""
    import pymupdf4llm

    result = pymupdf4llm.to_markdown(str(pdf_path))
    text = _to_text(result)

    if not text.strip():
        raise RuntimeError("PyMuPDF4LLM returned empty content")

    return text


def _open_pymupdf():
    """Support both modern and legacy PyMuPDF import names."""
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        import fitz
        return fitz


def extract_with_pymupdf(pdf_path: Path) -> str:
    """Extract page text; try Tesseract OCR on pages without usable text."""
    fitz = _open_pymupdf()
    document = fitz.open(str(pdf_path))
    pages: list[str] = []
    tesseract_available = shutil.which("tesseract") is not None
    ocr_warning_logged = False

    try:
        for page_number, page in enumerate(document, start=1):
            try:
                text = page.get_text("text", sort=True)
            except TypeError:
                # Compatibility with older PyMuPDF versions.
                text = page.get_text("text")

            text = text or ""

            if not text.strip() and tesseract_available:
                try:
                    text_page = page.get_textpage_ocr(
                        language="eng",
                        dpi=300,
                        full=True,
                    )
                    text = page.get_text("text", textpage=text_page) or ""
                except Exception as exc:
                    if not ocr_warning_logged:
                        log(f"[WARN] PyMuPDF Tesseract OCR failed: {exc}")
                        ocr_warning_logged = True

            if text.strip():
                pages.append(
                    f"\n\n<!-- PAGE {page_number} -->\n\n{text.strip()}"
                )

    finally:
        document.close()

    combined = "\n".join(pages).strip()
    if not combined:
        if not tesseract_available:
            log(
                "[INFO] Tesseract is not on PATH. Scanned PDFs may need "
                "Docling or a Tesseract installation."
            )
        raise RuntimeError("PyMuPDF returned no extractable page text")

    return combined


def extract_with_pypdf(pdf_path: Path) -> str:
    """Text-only fallback. pypdf does not perform OCR."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path), strict=False)

    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception as exc:
            raise RuntimeError(f"PDF is encrypted: {exc}") from exc

        if not unlocked:
            raise RuntimeError("PDF is encrypted and requires a password")

    pages: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(
                f"\n\n<!-- PAGE {page_number} -->\n\n{text.strip()}"
            )

    combined = "\n".join(pages).strip()
    if not combined:
        raise RuntimeError("pypdf returned no extractable text")

    return combined


def validate_pdf_path(raw_path: str) -> Path:
    if not raw_path.strip():
        raise ValueError("No PDF path was provided")

    path = Path(raw_path).expanduser()

    try:
        path = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"PDF file not found: {raw_path}") from exc

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.name}")

    return path


def extract_pdf_to_markdown_math(pdf_path: str | Path) -> str:
    """
    Extract PDF content using available local extractors.

    The function preserves extractor output instead of guessing that ordinary
    text is LaTeX. OCR and PDF text extraction can still misread equations;
    verify important equations against the original paper.
    """
    path = validate_pdf_path(str(pdf_path))

    extractors = [
        ("Docling", extract_with_docling),
        ("PyMuPDF4LLM", extract_with_pymupdf4llm),
        ("PyMuPDF", extract_with_pymupdf),
        ("pypdf", extract_with_pypdf),
    ]
    errors: list[str] = []

    for name, extractor in extractors:
        try:
            log(f"[INFO] Trying {name}…")
            text = extractor(path)

            if text and text.strip():
                log(f"[INFO] {name} extraction succeeded")
                return text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"

            errors.append(f"{name}: returned empty content")
            log(f"[WARN] {name} returned empty content")

        except Exception as exc:
            detail = " ".join(str(exc).split())
            errors.append(f"{name}: {detail}")
            log(f"[WARN] {name} extraction failed: {detail}")

    summary = "; ".join(errors)
    raise RuntimeError(f"All available extractors failed. {summary}")


def main() -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(
        description="Extract text and equations from a research paper PDF."
    )
    parser.add_argument(
        "--pdf",
        dest="pdf_option",
        help="PDF file path (used by the Tauri app)",
    )
    parser.add_argument(
        "pdf_positional",
        nargs="?",
        help="PDF file path (positional form, for manual testing)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed error tracebacks",
    )
    args = parser.parse_args()

    if args.pdf_option and args.pdf_positional:
        parser.error("Provide the PDF path either positionally or with --pdf, not both")

    target_pdf = args.pdf_option or args.pdf_positional
    if not target_pdf:
        parser.error("A PDF path is required; use --pdf PATH")

    try:
        sys.stdout.write(extract_pdf_to_markdown_math(target_pdf))
        sys.stdout.flush()
        return 0
    except Exception as exc:
        log(f"[ERROR] Extraction failed: {exc}")
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())