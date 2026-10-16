#!/usr/bin/env python3
"""
Local PDF extractor for Research to Jupyter.

Order:
1) Docling  (OCR + layout + formula enrichment)
2) pymupdf4llm (Markdown, great for digital PDFs)
3) PyMuPDF (fitz) text + optional Tesseract OCR for scans
4) pypdf (last resort)

Writes only the extracted content to stdout.
All info/warnings go to stderr.
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
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        v = value.get("text") or value.get("markdown") or value.get("content")
        return v if isinstance(v, str) else ""
    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            t = to_text(item)
            if t and t.strip():
                parts.append(t.strip())
        return "\n\n".join(parts)
    return ""


def extract_with_docling(pdf_path: Path) -> str:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = True
    opts.do_table_structure = True
    if hasattr(opts, "do_formula_enrichment"):
        opts.do_formula_enrichment = True
    if hasattr(opts, "generate_picture_images"):
        opts.generate_picture_images = False
    if hasattr(opts, "generate_page_images"):
        opts.generate_page_images = False

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )
    res = converter.convert(str(pdf_path))
    doc = getattr(res, "document", None)
    if doc is None:
        raise RuntimeError("Docling returned no document")

    for name in ("export_to_markdown", "export_to_text"):
        fn = getattr(doc, name, None)
        if callable(fn):
            txt = to_text(fn())
            if txt.strip():
                return txt.strip() + "\n"
    raise RuntimeError("Docling produced empty output")


def extract_with_pymupdf4llm(pdf_path: Path) -> str:
    import pymupdf4llm

    md = pymupdf4llm.to_markdown(str(pdf_path))
    txt = to_text(md)
    if not txt.strip():
        raise RuntimeError("pymupdf4llm returned empty text")
    return txt.strip() + "\n"


def _import_fitz():
    try:
        import pymupdf as fitz
        return fitz
    except Exception:
        import fitz
        return fitz


def extract_with_pymupdf(pdf_path: Path) -> str:
    fitz = _import_fitz()
    doc = fitz.open(str(pdf_path))
    out = []
    has_tess = shutil.which("tesseract") is not None
    warned = False
    try:
        for i, page in enumerate(doc, start=1):
            try:
                text = page.get_text("text", sort=True) or ""
            except TypeError:
                try:
                    text = page.get_text("text") or ""
                except Exception:
                    text = ""
            if not text.strip() and has_tess:
                try:
                    tp = page.get_textpage_ocr(language="eng", dpi=300, full=True)
                    text = page.get_text("text", textpage=tp) or ""
                except Exception as ex:
                    if not warned:
                        eprint(f"[warn] Tesseract OCR fallback failed: {ex}")
                        warned = True
            if text.strip():
                out.append(f"<!-- PAGE {i} -->\n\n{text.strip()}")
        if not out:
            if not has_tess:
                eprint("[info] No Tesseract on PATH. Image-only PDFs work best with Docling.")
            raise RuntimeError("PyMuPDF found no readable text")
        return "\n\n".join(out).strip() + "\n"
    finally:
        try:
            doc.close()
        except Exception:
            pass


def extract_with_pypdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
        except Exception as ex:
            raise RuntimeError("pypdf/PyPDF2 not installed") from ex

    reader = PdfReader(str(pdf_path), strict=False)
    if getattr(reader, "is_encrypted", False):
        try:
            ok = reader.decrypt("")
            if ok == 0:
                raise RuntimeError("PDF is password protected")
        except Exception as ex:
            raise RuntimeError(f"Encrypted PDF: {ex}") from ex

    parts = []
    for i, pg in enumerate(getattr(reader, "pages", []), start=1):
        try:
            t = pg.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            parts.append(f"<!-- PAGE {i} -->\n\n{t.strip()}")
    if not parts:
        raise RuntimeError("pypdf extracted nothing")
    return "\n\n".join(parts).strip() + "\n"


def extract(pdf_path: Path) -> str:
    errs = []
    steps = [
        ("Docling", extract_with_docling),
        ("pymupdf4llm", extract_with_pymupdf4llm),
        ("PyMuPDF", extract_with_pymupdf),
        ("pypdf", extract_with_pypdf),
    ]
    for name, fn in steps:
        try:
            eprint(f"[extract] trying {name}")
            txt = fn(pdf_path)
            if txt and txt.strip():
                eprint(f"[extract] {name} OK ({len(txt):,} chars)")
                return txt
            errs.append(f"{name}: empty")
        except Exception as ex:
            m = str(ex).strip()
            errs.append(f"{name}: {m}")
            eprint(f"[extract] {name} failed -> {m}")
    raise RuntimeError("All extractors failed. " + " | ".join(errs))


def main() -> int:
    configure_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", dest="pdf_opt")
    ap.add_argument("pdf_pos", nargs="?")
    args = ap.parse_args()
    target = args.pdf_opt or args.pdf_pos
    if not target:
        eprint("Usage: extract_pdf.py --pdf <file.pdf>")
        return 2
    p = Path(target).expanduser()
    try:
        p = p.resolve(strict=True)
    except Exception:
        eprint(f"[error] file not found: {target}")
        return 2
    if p.suffix.lower() != ".pdf":
        eprint("[error] only .pdf supported")
        return 2
    try:
        sys.stdout.write(extract(p))
        sys.stdout.flush()
        return 0
    except Exception:
        eprint(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())