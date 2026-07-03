"""Document text extraction for PDF / DOCX / TXT payloads.

A document is routed to the text + authenticity engines after its text is
extracted here (PRD §5 supported file types). PDFs additionally keep their raw
bytes so image/metadata checks can run later if desired.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger("investwall.extract")


def extract_document_text(data: bytes, filename: str | None) -> str:
    name = (filename or "").lower()
    if name.endswith(".txt") or _looks_like_text(data):
        return _decode_text(data)
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        return _extract_pdf(data)
    if name.endswith(".docx") or data[:4] == b"PK\x03\x04":
        return _extract_docx(data)
    return _decode_text(data)


def _looks_like_text(data: bytes) -> bool:
    sample = data[:512]
    if not sample:
        return False
    printable = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126)
    return printable / len(sample) > 0.9


def _decode_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "ignore")


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("PDF extraction failed: %s", exc)
        return ""


def _extract_docx(data: bytes) -> str:
    try:
        import docx

        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("DOCX extraction failed: %s", exc)
        return ""
