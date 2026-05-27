"""PDF → pages → chunks.

No AI here. Pure text wrangling. This is the first stage of the RAG pipeline.
"""

import pdfplumber

from .config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_pages(pdf_file) -> list[dict]:
    """Read a PDF and return a list of non-empty pages.

    Each entry: {"page": int (1-indexed), "text": str}.
    Pages with no extractable text (e.g. pure images) are skipped.
    """
    pages = []
    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({"page": i, "text": text})
    return pages


def chunk_pages(pages: list[dict]) -> list[dict]:
    """Slide a window across each page's text, keeping page numbers for citations.

    Why per-page chunking?  Because we want every chunk to carry exactly one
    page number, so when we cite (p. 7) we know it really was on page 7.
    """
    chunks = []
    for p in pages:
        text = p["text"]
        if len(text) <= CHUNK_SIZE:
            chunks.append({"page": p["page"], "text": text})
            continue

        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            chunks.append({"page": p["page"], "text": text[start:end]})
            if end == len(text):
                break
            start = end - CHUNK_OVERLAP
    return chunks
