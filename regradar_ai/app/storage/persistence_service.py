"""Small integration helpers keeping storage concerns out of the AI pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..ai.schemas import AnalysisMetadata, DocumentChunkForAI, RegulatoryEventCard
from . import document_repository, event_repository


@dataclass
class PersistenceResult:
    document_saved: bool = False
    chunks_saved: int = 0
    event_saved: bool = False
    warnings: list[str] = field(default_factory=list)


def persist_document(
    *,
    document_id: str,
    version_id: str,
    text: str,
    chunks: list[DocumentChunkForAI],
    filename: str | None = None,
    content_type: str | None = None,
    source_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PersistenceResult:
    result = PersistenceResult()
    document = document_repository.DocumentRecord(
        document_id=document_id,
        version_id=version_id,
        filename=filename,
        content_type=content_type,
        source_url=source_url,
        text_hash=document_repository.text_hash(text),
        extracted_text_length=len(text),
        chunks_count=len(chunks),
        metadata=metadata or {},
    )
    result.document_saved = document_repository.save_document(document)
    if not result.document_saved:
        result.warnings.append("persistence warning: document was not saved")

    chunk_records = [
        document_repository.ChunkRecord(
            document_id=document_id,
            version_id=version_id,
            chunk_id=chunk.chunk_id,
            order=max(chunk.order_index, 0),
            text=chunk.text,
            text_hash=document_repository.text_hash(chunk.text),
            metadata={
                "section_title": chunk.section_title,
                "page_number": chunk.page_number,
            },
        )
        for chunk in chunks
    ]
    result.chunks_saved = document_repository.save_chunks(
        document_id,
        version_id,
        chunk_records,
    )
    if result.chunks_saved != len(chunk_records):
        result.warnings.append(
            "persistence warning: not all document chunks were saved"
        )
    return result


def persist_event(
    event_card: RegulatoryEventCard,
    document_id: str,
    version_id: str,
) -> PersistenceResult:
    result = PersistenceResult()
    event_card.analysis_metadata.event_saved = True
    result.event_saved = event_repository.save_event_card(
        event_card,
        document_id,
        version_id,
    )
    if not result.event_saved:
        event_card.analysis_metadata.event_saved = False
        result.warnings.append("persistence warning: event card was not saved")
    return result


def apply_persistence_metadata(
    analysis_metadata: AnalysisMetadata,
    *results: PersistenceResult,
) -> None:
    for result in results:
        analysis_metadata.document_saved = (
            analysis_metadata.document_saved or result.document_saved
        )
        analysis_metadata.chunks_saved = max(
            analysis_metadata.chunks_saved,
            result.chunks_saved,
        )
        analysis_metadata.event_saved = (
            analysis_metadata.event_saved or result.event_saved
        )
        analysis_metadata.warnings.extend(
            warning
            for warning in result.warnings
            if warning not in analysis_metadata.warnings
        )
