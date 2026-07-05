"""Deterministic, lightweight chunking for the in-memory document MVP."""

import re

from ..ai.schemas import DocumentChunkForAI


DEFAULT_CHUNK_SIZE = 1500
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def chunk_text_for_document(
    text: str,
    max_chars: int = DEFAULT_CHUNK_SIZE,
) -> list[DocumentChunkForAI]:
    """Group paragraphs/sentences into stable, non-empty document chunks."""
    if max_chars < 1:
        raise ValueError("max_chars must be greater than zero")

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    units: list[tuple[str, str]] = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        paragraph_separator = "\n\n" if paragraph_index else ""
        if len(paragraph) <= max_chars:
            units.append((paragraph, paragraph_separator))
            continue

        sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(paragraph)]
        for sentence_index, sentence in enumerate(sentences):
            if sentence:
                units.append(
                    (
                        sentence,
                        paragraph_separator if sentence_index == 0 else " ",
                    )
                )

    chunk_texts: list[str] = []
    current: list[str] = []
    current_length = 0
    for unit, preferred_separator in units:
        separator = preferred_separator if current else ""
        if current and current_length + len(separator) + len(unit) > max_chars:
            chunk_texts.append("".join(current))
            current = []
            current_length = 0
            separator = ""
        current.extend((separator, unit))
        current_length += len(separator) + len(unit)

    if current:
        chunk_texts.append("".join(current))

    return [
        DocumentChunkForAI(
            chunk_id=f"chunk_{index}",
            text=chunk_text,
            order_index=index - 1,
        )
        for index, chunk_text in enumerate(chunk_texts, start=1)
    ]
