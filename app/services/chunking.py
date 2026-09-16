"""Two selectable chunking strategies for ingested documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings

ChunkingStrategy = Literal["fixed_size", "sentence_window"]
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str


def chunk_text(text: str, strategy: ChunkingStrategy, settings: Settings) -> list[TextChunk]:
    if strategy == "fixed_size":
        parts = _fixed_size(text, settings.chunk_size, settings.chunk_overlap)
    else:
        parts = _sentence_window(
            text,
            settings.sentence_window_size,
            settings.sentence_window_overlap,
        )
    return [TextChunk(index=i, text=part) for i, part in enumerate(parts) if part.strip()]


def _fixed_size(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Character windows with overlap. Prefer splitting on whitespace near the boundary."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _sentence_window(text: str, window_size: int, overlap: int) -> list[str]:
    """Sliding windows over sentence tokens."""
    if window_size <= 0:
        raise ValueError("sentence_window_size must be positive")
    if overlap >= window_size:
        raise ValueError("sentence_window_overlap must be smaller than sentence_window_size")

    sentences = [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    step = window_size - overlap
    for i in range(0, len(sentences), step):
        window = sentences[i : i + window_size]
        if not window:
            break
        chunks.append(" ".join(window))
        if i + window_size >= len(sentences):
            break
    return chunks
