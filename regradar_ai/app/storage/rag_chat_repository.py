"""Persisted RAG exchange history without multi-turn prompt memory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .jsonl_repository import append_jsonl, read_jsonl_reverse
from .paths import storage_dir


STORAGE_DIR = storage_dir()
RAG_CHATS_PATH = STORAGE_DIR / "rag_chats.jsonl"


class RagChatRecord(BaseModel):
    chat_id: str
    message_id: str
    document_id: str
    version_id: str = "v1"
    question: str
    answer: str
    audience: str
    no_data: bool
    source_chunk_ids: list[str] = Field(default_factory=list)
    llm_call_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


def save_rag_exchange(record: RagChatRecord) -> bool:
    return append_jsonl(RAG_CHATS_PATH, record.model_dump(mode="json"))


def list_rag_history(
    document_id: str,
    version_id: str = "v1",
    limit: int = 20,
) -> list[dict[str, Any]]:
    return [
        record
        for record in read_jsonl_reverse(RAG_CHATS_PATH, limit=2_000_000_000)
        if record.get("document_id") == document_id
        and record.get("version_id") == version_id
    ][:max(limit, 0)]


def get_recent_rag_chats(limit: int = 50) -> list[dict[str, Any]]:
    return read_jsonl_reverse(RAG_CHATS_PATH, limit=limit)
