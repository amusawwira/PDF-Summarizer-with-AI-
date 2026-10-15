"""Utility helpers for PDF extraction, chunking and (optional) OCR."""
from __future__ import annotations

import hashlib
from typing import Any


def _page_text(page) -> str:
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


def extract_pdf(uploaded_file) -> dict[str, Any]:
    """Extract text (and per-page text) from an uploaded PDF.

    Returns a dict with keys: ok, name, text, pages, page_count, word_count, error.
    """
    name = getattr(uploaded_file, "name", "document.pdf")
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "name": name, "text": "", "pages": [], "page_count": 0,
                "word_count": 0, "error": f"pypdf unavailable: {exc}"}

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    try:
        reader = PdfReader(uploaded_file)
    except Exception as exc:
        return {"ok": False, "name": name, "text": "", "pages": [], "page_count": 0,
                "word_count": 0, "error": f"Could not read PDF: {exc}"}

    pages: list[dict[str, Any]] = []
    for i, page in enumerate(reader.pages, start=1):
        pages.append({"page": i, "text": _page_text(page)})

    text = "\n\n".join(p["text"] for p in pages).strip()
    word_count = len(text.split())

    if not text or word_count < 20:
        # Possibly scanned/image-only PDF.
        ocr_text, ocr_err = _try_ocr(uploaded_file)
        if ocr_text:
            # Rebuild pages best-effort: split by form feed if present else keep as one.
            pages = [{"page": i + 1, "text": t} for i, t in enumerate(ocr_text.split("\f"))]
            text = "\n\n".join(p["text"] for p in pages).strip()
            word_count = len(text.split())
            return {"ok": True, "name": name, "text": text, "pages": pages,
                    "page_count": len(pages), "word_count": word_count, "error": None,
                    "ocr": True}
        return {"ok": False, "name": name, "text": "", "pages": pages,
                "page_count": len(pages), "word_count": word_count,
                "error": ocr_err or "No extractable text found (scanned PDF?)."}

    return {"ok": True, "name": name, "text": text, "pages": pages,
            "page_count": len(pages), "word_count": word_count, "error": None,
            "ocr": False}


def _try_ocr(uploaded_file) -> (str | None, str | None):
    try:
        import pdf2image
        import pytesseract
    except Exception:
        return None, ("No text extracted. Install OCR extras "
                     "(`pip install pdf2image pytesseract pdfplumber`) and system "
                     "poppler/tesseract to handle scanned PDFs.")
    try:
        uploaded_file.seek(0)
        data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        images = pdf2image.convert_from_bytes(data)
    except Exception as exc:
        return None, f"OCR conversion failed: {exc}"
    try:
        parts = [pytesseract.image_to_string(img) for img in images]
        return "\f".join(parts), None
    except Exception as exc:
        return None, f"OCR failed: {exc}"


def file_hash(uploaded_file) -> str:
    try:
        uploaded_file.seek(0)
        data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        return hashlib.sha256(data).hexdigest()[:16]
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    """Simple character-based chunker with overlap."""
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    step = max(1, chunk_size - overlap)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end >= n:
            break
        start += step
    return chunks
