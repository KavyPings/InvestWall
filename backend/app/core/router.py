"""Content Router — determine the modality of an incoming piece of content.

Mirrors PRD §7 "Content Router → Determine Content Type". Routing is by explicit
filename/mime hints first, then by content sniffing of magic bytes, finally
falling back to TEXT when a text payload is present.
"""
from __future__ import annotations

import os

from app.core.evidence import Modality

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
DOCUMENT_EXT = {".pdf", ".docx", ".txt", ".doc", ".rtf"}

_MIME_PREFIX = {
    "image/": Modality.IMAGE,
    "video/": Modality.VIDEO,
    "audio/": Modality.AUDIO,
}
_MIME_DOC = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}


def _sniff(data: bytes) -> Modality:
    """Best-effort magic-byte sniffing for common formats."""
    if len(data) < 12:
        return Modality.UNKNOWN
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return Modality.IMAGE
    if data[:3] == b"\xff\xd8\xff":
        return Modality.IMAGE
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return Modality.IMAGE
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return Modality.IMAGE
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return Modality.AUDIO
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return Modality.AUDIO
    if data[4:8] == b"ftyp":
        # ISO base media — could be mp4 video or m4a audio.
        brand = data[8:12]
        if brand[:1] == b"M" and b"A" in brand:  # M4A, M4B ...
            return Modality.AUDIO
        return Modality.VIDEO
    if data[:4] == b"%PDF":
        return Modality.DOCUMENT
    if data[:4] == b"PK\x03\x04":  # zip container (docx/xlsx)
        return Modality.DOCUMENT
    return Modality.UNKNOWN


class ContentRouter:
    """Resolve the modality for text payloads and uploaded files."""

    @staticmethod
    def route_text(text: str | None) -> Modality:
        return Modality.TEXT if (text and text.strip()) else Modality.UNKNOWN

    @staticmethod
    def route_file(
        filename: str | None,
        content_type: str | None,
        data: bytes | None = None,
    ) -> Modality:
        ext = os.path.splitext(filename or "")[1].lower()
        if ext in IMAGE_EXT:
            return Modality.IMAGE
        if ext in VIDEO_EXT:
            return Modality.VIDEO
        if ext in AUDIO_EXT:
            return Modality.AUDIO
        if ext in DOCUMENT_EXT:
            return Modality.DOCUMENT

        ct = (content_type or "").lower().split(";")[0].strip()
        if ct in _MIME_DOC:
            return Modality.DOCUMENT
        for prefix, modality in _MIME_PREFIX.items():
            if ct.startswith(prefix):
                return modality
        if ct == "text/plain":
            return Modality.DOCUMENT

        if data:
            sniffed = ContentRouter._sniff_safe(data)
            if sniffed is not Modality.UNKNOWN:
                return sniffed
        return Modality.UNKNOWN

    @staticmethod
    def _sniff_safe(data: bytes) -> Modality:
        try:
            return _sniff(data)
        except Exception:  # pragma: no cover - defensive
            return Modality.UNKNOWN
