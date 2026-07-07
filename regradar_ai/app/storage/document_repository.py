"""Document and chunk repository backed by replaceable JSONL primitives."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .jsonl_repository import append_jsonl, find_latest_by_fields, read_jsonl_reverse
from .paths import storage_dir


STORAGE_DIR = storage_dir()
DOCUMENTS_PATH = STORAGE_DIR / "documents.jsonl"
CHUNKS_PATH = STORAGE_DIR / "chunks.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_document_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    forbidden = {"text", "document_text", "extracted_text", "chunks", "content"}

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): clean(child)
                for key, child in value.items()
                if str(key).casefold() not in forbidden
            }
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        return value

    return clean(metadata)


class DocumentRecord(BaseModel):
    document_id: str
    version_id: str = "v1"
    filename: str | None = None
    content_type: str | None = None
    source_url: str | None = None
    text_hash: str
    extracted_text_length: int = Field(ge=0)
    chunks_count: int = Field(ge=0)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def strip_full_text(cls, value: Any) -> dict[str, Any]:
        return _safe_document_metadata(value if isinstance(value, dict) else {})


class ChunkRecord(BaseModel):
    document_id: str
    version_id: str = "v1"
    chunk_id: str
    order: int = Field(ge=0)
    text: str = Field(min_length=1)
    text_hash: str
    created_at: str = Field(default_factory=_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


def save_document(record: DocumentRecord) -> bool:
    return append_jsonl(DOCUMENTS_PATH, record.model_dump(mode="json"))


def save_chunks(
    document_id: str,
    version_id: str,
    chunks: list[ChunkRecord],
) -> int:
    existing = {
        (chunk.chunk_id, chunk.text_hash)
        for chunk in get_chunks(document_id, version_id)
    }
    saved = 0
    for chunk in chunks:
        if chunk.document_id != document_id or chunk.version_id != version_id:
            continue
        if (chunk.chunk_id, chunk.text_hash) in existing:
            saved += 1
            continue
        if append_jsonl(CHUNKS_PATH, chunk.model_dump(mode="json")):
            saved += 1
    return saved


def get_document(
    document_id: str,
    version_id: str = "v1",
) -> DocumentRecord | None:
    value = find_latest_by_fields(
        DOCUMENTS_PATH,
        {"document_id": document_id, "version_id": version_id},
    )
    return DocumentRecord.model_validate(value) if value else None


def get_chunks(
    document_id: str,
    version_id: str = "v1",
) -> list[ChunkRecord]:
    latest: dict[str, ChunkRecord] = {}
    for value in read_jsonl_reverse(CHUNKS_PATH, limit=2_000_000_000):
        if value.get("document_id") != document_id or value.get("version_id") != version_id:
            continue
        chunk_id = str(value.get("chunk_id", ""))
        if chunk_id and chunk_id not in latest:
            latest[chunk_id] = ChunkRecord.model_validate(value)
    return sorted(latest.values(), key=lambda chunk: chunk.order)


def list_documents(limit: int = 50) -> list[DocumentRecord]:
    if limit <= 0:
        return []
    latest: dict[tuple[str, str], DocumentRecord] = {}
    for value in read_jsonl_reverse(DOCUMENTS_PATH, limit=2_000_000_000):
        key = (str(value.get("document_id", "")), str(value.get("version_id", "v1")))
        if key[0] and key not in latest:
            latest[key] = DocumentRecord.model_validate(value)
        if len(latest) >= max(limit, 0):
            break
    return list(latest.values())
