#!/usr/bin/env python3
"""
Fast-First PDF text & math extractor for Research to Jupyter.

Order of operations:
1. PyMuPDF (fitz) fast digital extraction (~0.2 - 1.5s for 99% of papers).
2. PyMuPDF4LLM markdown table/layout extraction (only if requested or small).
3. pypdf fallback for digital text.
4. Docling heavy OCR (ONLY if the PDF is a scanned image with almost no text).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def configure_stdio() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _open_pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        import fitz
        return fitz


def extract_with_pymupdf_fast(pdf_path: Path) -> tuple[str, int]:
    """
    Ultra-fast digital text & math symbol extraction (~0.5s for a 20-page paper).
    Returns (extracted_text, page_count).
    """
    fitz = _open_pymupdf()
    doc = fitz.open(str(pdf_path))
    pages: list[str] = []
    page_count = len(doc)

    try:
        for page_number, page in enumerate(doc, start=1):
            try:
                text = page.get_text("text", sort=True)
            except TypeError:
                text = page.get_text("text")

            text = (text or "").strip()
            if text:
                pages.append(f"<!-- PAGE {page_number} -->\n\n{text}")
    finally:
        doc.close()

    return "\n\n".join(pages).strip(), page_count


def extract_with_pymupdf4llm(pdf_path: Path) -> str:
    """Markdown extraction for short/medium digital PDFs."""
    import pymupdf4llm

    md = pymupdf4llm.to_markdown(str(pdf_path), write_images=False)
    if isinstance(md, str) and md.strip():
        return md.strip()
    raise RuntimeError("PyMuPDF4LLM returned empty content")


def extract_with_pypdf(pdf_path: Path) -> str:
    """Lightweight pure-Python fallback."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path), strict=False)
    pages: list[str] = []
    for idx, page in enumerate(reader.pages, start=1):
        txt = (page.extract_text() or "").strip()
        if txt:
            pages.append(f"<!-- PAGE {idx} -->\n\n{txt}")

    combined = "\n\n".join(pages).strip()
    if not combined:
        raise RuntimeError("pypdf found no digital text")
    return combined


def extract_with_docling_ocr(pdf_path: Path) -> str:
    """Heavy OCR fallback — used ONLY when the PDF is a scanned image."""
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = getattr(result, "document", None)
    if doc is None:
        raise RuntimeError("Docling returned no document")

    md = doc.export_to_markdown()
    if isinstance(md, str) and md.strip():
        return md.strip()
    raise RuntimeError("Docling returned empty text")


def validate_pdf_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError(f"Invalid PDF file: {path}")
    return path


def extract_pdf_to_markdown_math(
    pdf_path: str | Path,
    mode: str = "fast",
) -> str:
    path = validate_pdf_path(str(pdf_path))

    # 1. FAST DIGITAL PASS (PyMuPDF) — finishes in < 1 second
    try:
        log("[INFO] Trying PyMuPDF (fast digital pass)…")
        text, page_count = extract_with_pymupdf_fast(path)
        avg_chars_per_page = len(text) / max(1, page_count)

        # If the PDF has real selectable text (>= 120 chars/page on average),
        # return immediately without running slow OCR!
        if avg_chars_per_page >= 120:
            if mode == "markdown" and page_count <= 25:
                try:
                    log("[INFO] Enhancing layout with PyMuPDF4LLM…")
                    md_text = extract_with_pymupdf4llm(path)
                    if len(md_text) >= len(text) * 0.5:
                        log("[INFO] PyMuPDF4LLM extraction succeeded")
                        return md_text + "\n"
                except Exception as exc:
                    log(f"[WARN] PyMuPDF4LLM skipped: {exc}")

            log("[INFO] PyMuPDF extraction succeeded")
            return text + "\n"

        log(
            f"[WARN] PDF looks scanned ({int(avg_chars_per_page)} chars/page). "
            "Falling back to deeper extractors…"
        )
    except Exception as exc:
        log(f"[WARN] PyMuPDF failed: {exc}")

    # 2. pypdf fallback for digital PDFs if PyMuPDF wasn't installed
    try:
        log("[INFO] Trying pypdf…")
        text = extract_with_pypdf(path)
        if len(text) >= 200:
            log("[INFO] pypdf extraction succeeded")
            return text + "\n"
    except Exception as exc:
        log(f"[WARN] pypdf failed: {exc}")

    # 3. Heavy Docling OCR — ONLY reached if the PDF has no selectable text
    try:
        log("[INFO] Running Docling OCR for scanned PDF (this may take a few minutes)…")
        text = extract_with_docling_ocr(path)
        log("[INFO] Docling extraction succeeded")
        return text + "\n"
    except Exception as exc:
        log(f"[WARN] Docling failed: {exc}")

    raise RuntimeError(
        "Could not extract text from PDF. Install PyMuPDF with: "
        "python -m pip install pymupdf"
    )


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Fast PDF extractor")
    parser.add_argument("--pdf", dest="pdf_option", help="PDF path")
    parser.add_argument("pdf_positional", nargs="?", help="PDF path")
    parser.add_argument(
        "--mode",
        choices=["fast", "markdown"],
        default="fast",
        help="fast = instant PyMuPDF (default), markdown = PyMuPDF4LLM",
    )
    args = parser.parse_args()

    target = args.pdf_option or args.pdf_positional
    if not target:
        parser.error("Provide a PDF path")

    try:
        output = extract_pdf_to_markdown_math(target, mode=args.mode)
        sys.stdout.write(output)
        sys.stdout.flush()
        return 0
    except Exception as exc:
        log(f"[ERROR] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())